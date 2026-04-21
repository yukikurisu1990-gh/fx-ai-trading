"""ReconciliationEventsRepository — append-only write for reconciliation_events (D1 §2.1.G #31).

reconciliation_events is APPEND_ONLY (Reconciler Action Matrix execution records).
One row per reconcile decision that changed state, plus aggregated outbox_stale signals.
No UPDATE, no DELETE.

Schema (migration 0007):
  reconciliation_event_id  TEXT PK
  trigger_reason           TEXT NOT NULL  ('startup'|'midrun_heartbeat_gap'
                                            |'periodic_drift_check'|'outbox_stale')
  action_taken             TEXT NOT NULL  ('MARK_SUBMITTED'|'MARK_FILLED'|...
                                            |'outbox_stale_detected')
  order_id                 TEXT nullable
  position_snapshot_id     TEXT nullable  (Phase 6: always None)
  detail                   JSON nullable
  event_time_utc           TIMESTAMPTZ NOT NULL
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import text

from fx_ai_trading.repositories.base import RepositoryBase


class ReconciliationEventsRepository(RepositoryBase):
    """Write-only repository for reconciliation_events (APPEND_ONLY).

    insert() is the only mutation.  Caller supplies trigger_reason /
    action_taken / event_time_utc; reconciliation_event_id is auto-generated
    when not provided.
    """

    def insert(
        self,
        *,
        trigger_reason: str,
        action_taken: str,
        event_time_utc: datetime,
        order_id: str | None = None,
        position_snapshot_id: str | None = None,
        detail: dict | None = None,
        reconciliation_event_id: str | None = None,
    ) -> str:
        """Insert a single reconciliation_events row and return its ID."""
        event_id = reconciliation_event_id or str(uuid.uuid4())
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO reconciliation_events"
                    " (reconciliation_event_id, trigger_reason, action_taken,"
                    "  order_id, position_snapshot_id, detail, event_time_utc)"
                    " VALUES"
                    " (:reconciliation_event_id, :trigger_reason, :action_taken,"
                    "  :order_id, :position_snapshot_id, :detail, :event_time_utc)"
                ),
                {
                    "reconciliation_event_id": event_id,
                    "trigger_reason": trigger_reason,
                    "action_taken": action_taken,
                    "order_id": order_id,
                    "position_snapshot_id": position_snapshot_id,
                    "detail": json.dumps(detail) if detail is not None else None,
                    "event_time_utc": event_time_utc,
                },
            )
        return event_id
