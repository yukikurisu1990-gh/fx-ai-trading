"""SupervisorEventsRepository — insert-only access to supervisor_events (M7).

supervisor_events records all Supervisor lifecycle events:
  - startup step completions
  - safe_stop triggers
  - config_version computations
  - account_type verifications
  - health check results

Schema (migration 0009):
  supervisor_event_id  TEXT PK
  event_type           TEXT NOT NULL
  run_id               TEXT (nullable)
  config_version       TEXT (nullable)
  source_breakdown     JSON (nullable)
  detail               JSON (nullable)
  event_time_utc       TIMESTAMPTZ NOT NULL

Common Keys: run_id and config_version are present; other keys are not
yet columns in this table (D1 M5 state).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from sqlalchemy import text

from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.base import RepositoryBase


class SupervisorEventsRepository(RepositoryBase):
    """Insert-only repository for supervisor_events."""

    def insert_event(
        self,
        event_type: str,
        event_time_utc: datetime,
        context: CommonKeysContext,
        detail: dict | None = None,
        source_breakdown: dict | None = None,
    ) -> None:
        """Append a supervisor lifecycle event row.

        Args:
            event_type: Machine-readable event code (e.g. 'account_type_verified').
            event_time_utc: UTC-aware datetime of the event.
            context: Common Keys context (run_id, config_version propagated).
            detail: Optional free-form payload (stored as JSON text).
            source_breakdown: Optional structured breakdown (e.g. config diff).

        The insert is committed immediately (auto-begin / auto-commit).
        Callers must NOT use this inside an outer transaction that they
        own — supervisor events are always standalone commits.
        """
        event_id = str(uuid.uuid4())
        detail_json = json.dumps(detail, default=str) if detail is not None else None
        breakdown_json = (
            json.dumps(source_breakdown, default=str) if source_breakdown is not None else None
        )
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO supervisor_events"
                    " (supervisor_event_id, event_type, run_id, config_version,"
                    "  event_time_utc, detail, source_breakdown)"
                    " VALUES (:supervisor_event_id, :event_type, :run_id, :config_version,"
                    "  :event_time_utc, :detail, :source_breakdown)"
                ),
                {
                    "supervisor_event_id": event_id,
                    "event_type": event_type,
                    "run_id": context.run_id,
                    "config_version": context.config_version,
                    "event_time_utc": event_time_utc,
                    "detail": detail_json,
                    "source_breakdown": breakdown_json,
                },
            )
