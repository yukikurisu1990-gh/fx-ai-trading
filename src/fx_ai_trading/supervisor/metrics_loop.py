"""MetricsLoop — single-shot 9-item metric recorder (M16 / M-METRIC-1).

Records one `supervisor_events(event_type=metric_sample)` row per call.
The 60-second cadence is owned by the caller (Supervisor Step 14); this
class is single-shot to comply with CLAUDE.md §14 (no while loops).

9 metric items (operations.md §6.2):
  cpu_percent                      — process CPU %
  memory_rss_mb                    — Resident Set Size in MB
  db_connections_count             — active pool connections (estimate)
  cycle_duration_seconds           — last trading-cycle duration (caller-supplied)
  outbox_pending_count             — outbox_events with status=pending
  notification_outbox_pending_count — notification_outbox with status=pending
  stream_heartbeat_age_seconds     — seconds since last heartbeat (caller-supplied)
  active_positions_count           — open positions in DB
  concurrent_orders_pending_count  — orders with status=PENDING

Fail-open: DB write failures are logged at WARNING; the loop continues.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime

from sqlalchemy import Engine, text

from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.supervisor_events import SupervisorEventsRepository

_log = logging.getLogger(__name__)

_ALL_METRIC_KEYS = (
    "cpu_percent",
    "memory_rss_mb",
    "db_connections_count",
    "cycle_duration_seconds",
    "outbox_pending_count",
    "notification_outbox_pending_count",
    "stream_heartbeat_age_seconds",
    "active_positions_count",
    "concurrent_orders_pending_count",
)

try:
    import psutil as _psutil

    _PSUTIL_PROCESS = _psutil.Process(os.getpid())
    _HAS_PSUTIL = True
except Exception:  # noqa: BLE001
    _psutil = None  # type: ignore[assignment]
    _PSUTIL_PROCESS = None
    _HAS_PSUTIL = False


class MetricsCollector:
    """Collects the 9 metric items defined in operations.md §6.2.

    Args:
        engine: SQLAlchemy Engine used for DB-count queries.
               If None, DB counts are recorded as None.
    """

    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine

    def collect(
        self,
        *,
        cycle_duration_seconds: float | None = None,
        stream_heartbeat_age_seconds: float | None = None,
    ) -> dict:
        """Return a dict with all 9 metric keys.

        Caller-supplied metrics (cycle_duration_seconds and
        stream_heartbeat_age_seconds) are passed through unchanged.
        DB-count metrics are None when engine is not available.
        """
        return {
            "cpu_percent": self._cpu_percent(),
            "memory_rss_mb": self._memory_rss_mb(),
            "db_connections_count": self._db_connections_count(),
            "cycle_duration_seconds": cycle_duration_seconds,
            "outbox_pending_count": self._count_pending_rows("outbox_events"),
            "notification_outbox_pending_count": self._count_pending_rows("notification_outbox"),
            "stream_heartbeat_age_seconds": stream_heartbeat_age_seconds,
            "active_positions_count": self._count_rows("positions"),
            "concurrent_orders_pending_count": self._count_pending_orders(),
        }

    # ------------------------------------------------------------------
    # Process metrics
    # ------------------------------------------------------------------

    def _cpu_percent(self) -> float | None:
        if not _HAS_PSUTIL:
            return None
        try:
            return _PSUTIL_PROCESS.cpu_percent(interval=None)
        except Exception:  # noqa: BLE001
            return None

    def _memory_rss_mb(self) -> float | None:
        if not _HAS_PSUTIL:
            return None
        try:
            return _PSUTIL_PROCESS.memory_info().rss / (1024 * 1024)
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # DB metrics — each returns None if engine is unavailable or query fails
    # ------------------------------------------------------------------

    def _db_connections_count(self) -> int | None:
        if self._engine is None:
            return None
        try:
            pool = self._engine.pool
            return pool.checkedout()  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            return None

    def _count_pending_rows(self, table: str) -> int | None:
        if self._engine is None:
            return None
        try:
            with self._engine.connect() as conn:
                row = conn.execute(
                    text(f"SELECT COUNT(*) FROM {table} WHERE status = 'pending'")  # noqa: S608
                ).fetchone()
            return int(row[0]) if row else None
        except Exception:  # noqa: BLE001
            return None

    def _count_rows(self, table: str) -> int | None:
        if self._engine is None:
            return None
        try:
            with self._engine.connect() as conn:
                row = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).fetchone()  # noqa: S608
            return int(row[0]) if row else None
        except Exception:  # noqa: BLE001
            return None

    def _count_pending_orders(self) -> int | None:
        if self._engine is None:
            return None
        try:
            with self._engine.connect() as conn:
                row = conn.execute(
                    text("SELECT COUNT(*) FROM orders WHERE status = 'PENDING'")
                ).fetchone()
            return int(row[0]) if row else None
        except Exception:  # noqa: BLE001
            return None


class MetricsLoop:
    """Single-shot metric recorder — one call writes one metric_sample row.

    The 60-second cadence is owned by the Supervisor (caller).
    DB write failures are logged at WARNING and do not raise (fail-open).

    Args:
        collector: MetricsCollector instance.
        repo: SupervisorEventsRepository for writing metric_sample events.
        context: CommonKeysContext for Common Keys propagation.
    """

    METRIC_EVENT_TYPE = "metric_sample"

    def __init__(
        self,
        collector: MetricsCollector,
        repo: SupervisorEventsRepository,
        context: CommonKeysContext,
    ) -> None:
        self._collector = collector
        self._repo = repo
        self._context = context

    def record(
        self,
        event_time_utc: datetime,
        *,
        cycle_duration_seconds: float | None = None,
        stream_heartbeat_age_seconds: float | None = None,
    ) -> bool:
        """Collect metrics and write one metric_sample row.

        Returns True on success, False on DB write failure (fail-open).

        Args:
            event_time_utc: UTC-aware timestamp for the event row.
            cycle_duration_seconds: Duration of the most recent trading cycle.
            stream_heartbeat_age_seconds: Seconds since last stream heartbeat.
        """
        try:
            metrics = self._collector.collect(
                cycle_duration_seconds=cycle_duration_seconds,
                stream_heartbeat_age_seconds=stream_heartbeat_age_seconds,
            )
            self._repo.insert_event(
                event_type=self.METRIC_EVENT_TYPE,
                event_time_utc=event_time_utc,
                context=self._context,
                detail=metrics,
            )
            _log.debug("MetricsLoop.record: metric_sample written at %s", event_time_utc)
            return True
        except Exception as exc:  # noqa: BLE001
            _log.warning("MetricsLoop.record: DB write failed (fail-open): %s", exc)
            return False
