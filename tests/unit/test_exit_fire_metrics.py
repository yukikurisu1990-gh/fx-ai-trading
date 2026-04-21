"""Unit tests: ExitFireMetricsService (Cycle 6.9b).

Pure unit tests using MagicMock engine — no DATABASE_URL required.
Verifies:
  - Constructor validation (engine required, Clock default)
  - Aggregation result shape for count_by_reason / pnl_summary / summary
  - Window filter is wired through Clock.now() into the :since SQL param
  - NULL-pnl rows surface as None (not 0.0)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.common.clock import FixedClock, WallClock
from fx_ai_trading.services.exit_fire_metrics import ExitFireMetricsService

_FIXED_NOW = datetime(2026, 4, 21, 12, 0, 0, tzinfo=UTC)


def _make_engine_returning(rows: list[tuple]) -> tuple[MagicMock, MagicMock]:
    """Build a MagicMock Engine whose connect()→execute() yields *rows*.

    Returns (engine, conn) so tests can assert on the captured execute call.
    """
    engine = MagicMock()
    conn = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = cm
    result = MagicMock()
    result.fetchall.return_value = rows
    result.fetchone.return_value = rows[0] if rows else None
    conn.execute.return_value = result
    return engine, conn


class TestConstructor:
    def test_constructor_rejects_none_engine(self) -> None:
        with pytest.raises(ValueError):
            ExitFireMetricsService(engine=None)  # type: ignore[arg-type]

    def test_clock_defaults_to_wallclock_when_not_provided(self) -> None:
        engine, _ = _make_engine_returning([])
        svc = ExitFireMetricsService(engine=engine)
        assert isinstance(svc._clock, WallClock)


class TestCountByReason:
    def test_count_by_reason_aggregates_by_primary_reason_code(self) -> None:
        engine, _ = _make_engine_returning([("tp", 7), ("sl", 3), ("time_exit", 1)])
        svc = ExitFireMetricsService(engine=engine, clock=FixedClock(_FIXED_NOW))
        assert svc.count_by_reason() == {"tp": 7, "sl": 3, "time_exit": 1}

    def test_count_by_reason_filters_by_window_using_clock_now(self) -> None:
        engine, conn = _make_engine_returning([])
        svc = ExitFireMetricsService(engine=engine, clock=FixedClock(_FIXED_NOW))
        svc.count_by_reason(window=timedelta(hours=1))
        sql_arg, params = conn.execute.call_args[0]
        assert "WHERE closed_at >= :since" in str(sql_arg)
        assert params["since"] == _FIXED_NOW - timedelta(hours=1)

    def test_count_by_reason_empty_returns_empty_dict(self) -> None:
        engine, _ = _make_engine_returning([])
        svc = ExitFireMetricsService(engine=engine, clock=FixedClock(_FIXED_NOW))
        assert svc.count_by_reason() == {}


class TestPnlSummaryByReason:
    def test_pnl_summary_handles_all_null_pnl_returns_none(self) -> None:
        # Cycle 6.7c E3: pnl_realized is always NULL today. SUM/AVG return
        # NULL for all-NULL groups; service must surface that as Python None
        # (not coerce to 0.0).
        engine, _ = _make_engine_returning([("tp", 4, None, None)])
        svc = ExitFireMetricsService(engine=engine, clock=FixedClock(_FIXED_NOW))
        assert svc.pnl_summary_by_reason() == {"tp": {"count": 4, "pnl_sum": None, "pnl_avg": None}}

    def test_pnl_summary_handles_mixed_null_pnl(self) -> None:
        # Mixed-NULL behaviour is observably identical to all-real at the
        # Python boundary: SQL SUM/AVG ignore NULLs and the row shape from
        # the DB is the same. The unit test pins the conversion of real
        # numeric values; integration tests cover the SQL semantic itself.
        engine, _ = _make_engine_returning([("tp", 2, 10.5, 5.25), ("sl", 1, -3.0, -3.0)])
        svc = ExitFireMetricsService(engine=engine, clock=FixedClock(_FIXED_NOW))
        result = svc.pnl_summary_by_reason()
        assert result["tp"] == {"count": 2, "pnl_sum": 10.5, "pnl_avg": 5.25}
        assert result["sl"] == {"count": 1, "pnl_sum": -3.0, "pnl_avg": -3.0}


class TestSummary:
    def test_summary_zero_rows_returns_zero_shape(self) -> None:
        engine, _ = _make_engine_returning([(0, 0, None, None)])
        svc = ExitFireMetricsService(engine=engine, clock=FixedClock(_FIXED_NOW))
        assert svc.summary() == {
            "total_fires": 0,
            "distinct_reasons": 0,
            "span_start_utc": None,
            "span_end_utc": None,
        }
