"""OutboxEventsRepository — read/write access to the outbox_events table (M8).

outbox_events stores pending order dispatch requests for the Outbox Pattern (D1 §6.6).

Status FSM:
  pending → dispatching → acked
                        → failed

Atomicity invariant (D1 §6.6):
  The initial INSERT (status='pending') MUST happen in the same transaction as
  the corresponding orders INSERT.  Use OrderLifecycleService.place_order_with_outbox()
  for this — do NOT use OutboxEventsRepository.insert_pending() directly for new orders.

OutboxEventsRepository methods are for the OutboxProcessor dispatch flow only
(status updates: pending→dispatching→acked/failed), which are separate transactions.
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import text

from fx_ai_trading.common.exceptions import RepositoryError
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.base import RepositoryBase

_STATUS_PENDING = "pending"
_STATUS_DISPATCHING = "dispatching"
_STATUS_ACKED = "acked"
_STATUS_FAILED = "failed"

_VALID_DISPATCH_TRANSITIONS: dict[str, set[str]] = {
    _STATUS_PENDING: {_STATUS_DISPATCHING},
    _STATUS_DISPATCHING: {_STATUS_ACKED, _STATUS_FAILED},
    _STATUS_ACKED: set(),
    _STATUS_FAILED: set(),
}

_COLUMNS = (
    "outbox_event_id",
    "order_id",
    "event_type",
    "status",
    "payload",
    "dispatch_attempts",
    "last_attempted_at",
    "created_at",
)


class OutboxEventsRepository(RepositoryBase):
    """Read/write interface for the outbox_events table.

    Methods in this class are for the OutboxProcessor dispatch flow.
    For the atomic order-creation write, use OrderLifecycleService.place_order_with_outbox().
    """

    def get_pending(self, limit: int = 100) -> list[dict]:
        """Return up to *limit* outbox events with status 'pending', ordered by created_at."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT outbox_event_id, order_id, event_type, status,"
                    " payload, dispatch_attempts, last_attempted_at, created_at"
                    " FROM outbox_events"
                    " WHERE status = 'pending'"
                    " ORDER BY created_at ASC"
                    " LIMIT :limit"
                ),
                {"limit": limit},
            ).fetchall()
        return [dict(zip(_COLUMNS, row, strict=True)) for row in rows]

    def get_by_id(self, outbox_event_id: str) -> dict | None:
        """Return the outbox event row for *outbox_event_id*, or None if not found."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT outbox_event_id, order_id, event_type, status,"
                    " payload, dispatch_attempts, last_attempted_at, created_at"
                    " FROM outbox_events WHERE outbox_event_id = :id"
                ),
                {"id": outbox_event_id},
            ).fetchone()
        if row is None:
            return None
        return dict(zip(_COLUMNS, row, strict=True))

    def mark_dispatching(
        self,
        outbox_event_id: str,
        attempted_at: datetime,
        context: CommonKeysContext,
    ) -> None:
        """Transition outbox event to 'dispatching' and increment dispatch_attempts.

        Raises RepositoryError if the event is not in 'pending' status.
        """
        self._with_common_keys({}, context)
        with self._engine.begin() as conn:
            row = conn.execute(
                text("SELECT status FROM outbox_events WHERE outbox_event_id = :id"),
                {"id": outbox_event_id},
            ).fetchone()
            if row is None:
                raise RepositoryError(f"outbox_event {outbox_event_id!r} not found")
            current = row[0]
            if _STATUS_DISPATCHING not in _VALID_DISPATCH_TRANSITIONS.get(current, set()):
                raise RepositoryError(
                    f"Invalid outbox status transition: {current!r} → 'dispatching'"
                )
            conn.execute(
                text(
                    "UPDATE outbox_events"
                    " SET status = 'dispatching',"
                    "     dispatch_attempts = dispatch_attempts + 1,"
                    "     last_attempted_at = :attempted_at"
                    " WHERE outbox_event_id = :id"
                ),
                {"id": outbox_event_id, "attempted_at": attempted_at},
            )

    def mark_acked(
        self,
        outbox_event_id: str,
        context: CommonKeysContext,
    ) -> None:
        """Transition outbox event from 'dispatching' to 'acked'."""
        self._update_dispatch_status(outbox_event_id, _STATUS_ACKED, context)

    def mark_failed(
        self,
        outbox_event_id: str,
        context: CommonKeysContext,
    ) -> None:
        """Transition outbox event from 'dispatching' to 'failed'."""
        self._update_dispatch_status(outbox_event_id, _STATUS_FAILED, context)

    def _update_dispatch_status(
        self,
        outbox_event_id: str,
        new_status: str,
        context: CommonKeysContext,
    ) -> None:
        self._with_common_keys({}, context)
        with self._engine.begin() as conn:
            row = conn.execute(
                text("SELECT status FROM outbox_events WHERE outbox_event_id = :id"),
                {"id": outbox_event_id},
            ).fetchone()
            if row is None:
                raise RepositoryError(f"outbox_event {outbox_event_id!r} not found")
            current = row[0]
            allowed = _VALID_DISPATCH_TRANSITIONS.get(current, set())
            if new_status not in allowed:
                raise RepositoryError(
                    f"Invalid outbox status transition: {current!r} → {new_status!r}"
                )
            conn.execute(
                text("UPDATE outbox_events SET status = :status WHERE outbox_event_id = :id"),
                {"status": new_status, "id": outbox_event_id},
            )

    @staticmethod
    def build_payload_json(payload: dict | None) -> str | None:
        """Serialize *payload* dict to JSON text for storage."""
        if payload is None:
            return None
        return json.dumps(payload, default=str)
