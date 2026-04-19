"""ProjectionService — periodic snapshot of supervisor_events to secondary DB (M23).

Iteration 2 scope: snapshot supervisor_events only.  Other tables
(positions, close_events, orders) are Phase 7 scope — see
iteration2_implementation_plan.md §6.11 and §10.1.

Design:
  - due()    → bool: True if 5-minute interval has elapsed since last snapshot.
  - snapshot() → int: reads supervisor_events from primary DB, upserts to transport.
  - Fail-open: any DB read error returns 0 (logged); transport errors are
    handled inside SupabaseProjectionTransport.upsert().
  - No DELETE is issued (Projector is read/upsert only; primary-DB append-only
    model is not affected).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import Engine, text

from fx_ai_trading.adapters.projector.supabase import SupabaseProjectionTransport
from fx_ai_trading.common.clock import Clock, WallClock

_log = logging.getLogger(__name__)

_SUPERVISOR_EVENTS_TABLE = "supervisor_events"
_INTERVAL_SECONDS: int = 300


class ProjectionService:
    """Periodic projector for supervisor_events (D3 §2.19 / M23).

    Args:
        engine: Primary SQLAlchemy engine (read-only access).
        transport: ProjectionTransport implementation (SupabaseProjectionTransport
                   in production, mock in tests).
        clock: Clock for interval checks.  Defaults to WallClock.

    Phase 7 extension: add positions / close_events / orders tables;
    add retry_events queue for failed upserts.
    """

    INTERVAL_SECONDS: int = _INTERVAL_SECONDS

    def __init__(
        self,
        engine: Engine,
        transport: SupabaseProjectionTransport,
        clock: Clock | None = None,
    ) -> None:
        self._engine = engine
        self._transport = transport
        self._clock: Clock = clock or WallClock()
        self._last_snapshot = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def due(self) -> bool:
        """Return True if a snapshot is due (interval elapsed or first run)."""
        if self._last_snapshot is None:
            return True
        elapsed = (self._clock.now() - self._last_snapshot).total_seconds()
        return elapsed >= self.INTERVAL_SECONDS

    def snapshot(self) -> int:
        """Read supervisor_events and upsert to transport.

        Returns the number of rows upserted.  On read error returns 0.
        Updates _last_snapshot even on partial failure so the interval
        is not violated (avoids thundering-herd retry storms).
        """
        rows = self._read_supervisor_events()
        count = self._transport.upsert(_SUPERVISOR_EVENTS_TABLE, rows)
        self._last_snapshot = self._clock.now()
        _log.info("ProjectionService.snapshot: upserted %d supervisor_events rows", count)
        return count

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _read_supervisor_events(self) -> list[dict[str, Any]]:
        """Read all supervisor_events rows from the primary DB.

        Returns [] on any error (fail-open).
        """
        try:
            with self._engine.connect() as conn:
                rows = (
                    conn.execute(
                        text(
                            "SELECT supervisor_event_id, event_type, run_id,"
                            " config_version, source_breakdown, detail, event_time_utc"
                            " FROM supervisor_events"
                            " ORDER BY event_time_utc ASC"
                        )
                    )
                    .mappings()
                    .all()
                )
            return [_serialize_row(dict(r)) for r in rows]
        except Exception as exc:
            _log.warning("ProjectionService._read_supervisor_events: failed: %s", exc)
            return []


def _serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Convert non-JSON-serializable values to strings for transport."""
    return {
        k: (str(v) if v is not None and not isinstance(v, (str, int, float, bool)) else v)
        for k, v in row.items()
    }
