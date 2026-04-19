"""CloseEventsRepository — append-only write for the close_events table (D3 §2.14).

close_events is EXECUTION_PERMANENT (retention_policy §3.1 #23) — never deleted.
One row per position close event.  Reasons stored as JSON list in priority order.

Schema (migration 0006):
  close_event_id         TEXT PK
  order_id               TEXT FK → orders.order_id   (entry order being closed)
  position_snapshot_id   TEXT FK → positions (nullable)
  reasons                JSON  [{priority, reason_code, detail}]
  primary_reason_code    TEXT
  closed_at              TIMESTAMPTZ
  pnl_realized           NUMERIC(18,8) nullable
  correlation_id         TEXT nullable
"""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import text

from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.base import RepositoryBase

_COLUMNS = (
    "close_event_id",
    "order_id",
    "position_snapshot_id",
    "reasons",
    "primary_reason_code",
    "closed_at",
    "pnl_realized",
    "correlation_id",
)


class CloseEventsRepository(RepositoryBase):
    """Write-only repository for close_events (EXECUTION_PERMANENT).

    insert() is the only mutation — no update, no delete (6.14 / retention §3.1 #23).
    """

    def insert(
        self,
        close_event_id: str,
        order_id: str,
        primary_reason_code: str,
        reasons: list[dict],
        closed_at: datetime,
        position_snapshot_id: str | None = None,
        pnl_realized: float | None = None,
        correlation_id: str | None = None,
        context: CommonKeysContext | None = None,
    ) -> None:
        """Insert a single close_event row.

        Args:
            close_event_id: Unique event identifier (ULID recommended).
            order_id: FK to orders.order_id (entry order being closed).
            primary_reason_code: Highest-priority exit reason code.
            reasons: JSON payload [{priority, reason_code, detail}, ...].
            closed_at: TZ-aware UTC timestamp of the close decision.
            position_snapshot_id: FK to positions (optional).
            pnl_realized: Realized P&L at close (optional).
            correlation_id: Cross-table trace key (optional).
            context: CommonKeysContext (accepted for contract compliance).
        """
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO close_events"
                    " (close_event_id, order_id, position_snapshot_id, reasons,"
                    "  primary_reason_code, closed_at, pnl_realized, correlation_id)"
                    " VALUES"
                    " (:close_event_id, :order_id, :position_snapshot_id, :reasons,"
                    "  :primary_reason_code, :closed_at, :pnl_realized, :correlation_id)"
                ),
                {
                    "close_event_id": close_event_id,
                    "order_id": order_id,
                    "position_snapshot_id": position_snapshot_id,
                    "reasons": json.dumps(reasons),
                    "primary_reason_code": primary_reason_code,
                    "closed_at": closed_at,
                    "pnl_realized": pnl_realized,
                    "correlation_id": correlation_id,
                },
            )

    def get_by_id(self, close_event_id: str) -> dict | None:
        """Return a close_event row by ID, or None if not found."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT close_event_id, order_id, position_snapshot_id, reasons,"
                    "  primary_reason_code, closed_at, pnl_realized, correlation_id"
                    " FROM close_events WHERE close_event_id = :id"
                ),
                {"id": close_event_id},
            ).fetchone()
        if row is None:
            return None
        result = dict(zip(_COLUMNS, row, strict=True))
        if isinstance(result["reasons"], str):
            result["reasons"] = json.loads(result["reasons"])
        return result

    def get_recent(self, limit: int = 50) -> list[dict]:
        """Return the *limit* most recent close_events, newest first."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT close_event_id, order_id, position_snapshot_id, reasons,"
                    "  primary_reason_code, closed_at, pnl_realized, correlation_id"
                    " FROM close_events ORDER BY closed_at DESC LIMIT :limit"
                ),
                {"limit": limit},
            ).fetchall()
        results = []
        for row in rows:
            d = dict(zip(_COLUMNS, row, strict=True))
            if isinstance(d["reasons"], str):
                d["reasons"] = json.loads(d["reasons"])
            results.append(d)
        return results
