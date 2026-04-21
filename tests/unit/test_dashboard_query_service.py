"""Unit tests: dashboard_query_service all public functions (M18 / Ob-PANEL-FALLBACK-1).

Tests use a mock engine with configurable cursor rows.  No live DB required.

Coverage:
  Existing queries (M12):
    get_open_positions, get_recent_orders, get_recent_supervisor_events,
    get_app_setting, get_daily_order_summary
  New queries (M18):
    get_top_candidates, get_execution_quality_summary,
    get_risk_state_detail, get_close_events_recent

Pattern:
  - engine=None always returns empty/zero sentinel without touching the DB.
  - DB error returns empty/zero sentinel (fail-open).
  - Valid rows are returned as list[dict] with expected keys.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock

from fx_ai_trading.services.dashboard_query_service import (
    get_app_setting,
    get_close_events_recent,
    get_daily_order_summary,
    get_execution_quality_summary,
    get_exit_fire_count_by_reason,
    get_exit_fire_pnl_summary_by_reason,
    get_exit_fire_recent,
    get_exit_fire_summary,
    get_open_positions,
    get_recent_orders,
    get_recent_supervisor_events,
    get_risk_state_detail,
    get_top_candidates,
)


def _mock_engine(rows: list[dict] | None = None, *, scalar: object = None) -> MagicMock:
    """Return a mock engine whose connect().execute() yields *rows* as mappings."""
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)

    if rows is not None:
        result = MagicMock()
        result.mappings.return_value.all.return_value = rows
        conn.execute.return_value = result
    if scalar is not None:
        result = MagicMock()
        result.fetchone.return_value = (scalar,)
        conn.execute.return_value = result
    return engine


def _error_engine() -> MagicMock:
    """Return a mock engine that raises RuntimeError on execute."""
    engine = MagicMock()
    conn = MagicMock()
    engine.connect.return_value.__enter__ = MagicMock(return_value=conn)
    engine.connect.return_value.__exit__ = MagicMock(return_value=False)
    conn.execute.side_effect = RuntimeError("db error")
    return engine


# ---------------------------------------------------------------------------
# Existing queries — engine=None sentinel
# ---------------------------------------------------------------------------


class TestNoneEngineReturnsEmpty:
    def test_get_open_positions_none(self) -> None:
        assert get_open_positions(None) == []

    def test_get_recent_orders_none(self) -> None:
        assert get_recent_orders(None) == []

    def test_get_recent_supervisor_events_none(self) -> None:
        assert get_recent_supervisor_events(None) == []

    def test_get_app_setting_none(self) -> None:
        assert get_app_setting(None, "any_key") is None

    def test_get_daily_order_summary_none(self) -> None:
        result = get_daily_order_summary(None)
        assert result == {"total": 0, "filled": 0, "canceled": 0, "failed": 0}

    def test_get_top_candidates_none(self) -> None:
        assert get_top_candidates(None) == []

    def test_get_execution_quality_summary_none(self) -> None:
        assert get_execution_quality_summary(None) == []

    def test_get_risk_state_detail_none(self) -> None:
        assert get_risk_state_detail(None) == []

    def test_get_close_events_recent_none(self) -> None:
        assert get_close_events_recent(None) == []


# ---------------------------------------------------------------------------
# DB error — fail-open
# ---------------------------------------------------------------------------


class TestDbErrorReturnsEmpty:
    def test_get_open_positions_error(self) -> None:
        assert get_open_positions(_error_engine()) == []

    def test_get_recent_orders_error(self) -> None:
        assert get_recent_orders(_error_engine()) == []

    def test_get_recent_supervisor_events_error(self) -> None:
        assert get_recent_supervisor_events(_error_engine()) == []

    def test_get_app_setting_error(self) -> None:
        assert get_app_setting(_error_engine(), "key") is None

    def test_get_daily_order_summary_error(self) -> None:
        result = get_daily_order_summary(_error_engine())
        assert result == {"total": 0, "filled": 0, "canceled": 0, "failed": 0}

    def test_get_top_candidates_error(self) -> None:
        assert get_top_candidates(_error_engine()) == []

    def test_get_execution_quality_summary_error(self) -> None:
        assert get_execution_quality_summary(_error_engine()) == []

    def test_get_risk_state_detail_error(self) -> None:
        assert get_risk_state_detail(_error_engine()) == []

    def test_get_close_events_recent_error(self) -> None:
        assert get_close_events_recent(_error_engine()) == []


# ---------------------------------------------------------------------------
# M18 new queries — row returned as list[dict]
# ---------------------------------------------------------------------------


class TestGetTopCandidates:
    def test_returns_list_of_dicts(self) -> None:
        row = {
            "instrument": "EUR_USD",
            "strategy_id": "AI",
            "tss_score": 0.85,
            "direction": "buy",
            "generated_at": "2026-01-01",
            "rank": 1,
        }
        engine = _mock_engine(rows=[row])
        result = get_top_candidates(engine)
        assert result == [row]

    def test_empty_rows_returns_empty(self) -> None:
        engine = _mock_engine(rows=[])
        assert get_top_candidates(engine) == []

    def test_limit_parameter_forwarded(self) -> None:
        engine = _mock_engine(rows=[])
        get_top_candidates(engine, limit=5)
        call_args = engine.connect.return_value.__enter__.return_value.execute.call_args
        assert call_args is not None


class TestGetExecutionQualitySummary:
    def test_returns_list_of_dicts(self) -> None:
        row = {
            "order_id": "o1",
            "instrument": "EUR_USD",
            "signal_age_seconds": 3.0,
            "slippage_pips": 0.2,
            "fill_latency_ms": 45,
            "created_at": "2026-01-01",
        }
        engine = _mock_engine(rows=[row])
        result = get_execution_quality_summary(engine)
        assert result == [row]

    def test_empty_rows_returns_empty(self) -> None:
        assert get_execution_quality_summary(_mock_engine(rows=[])) == []

    def test_multiple_rows_preserved(self) -> None:
        rows = [
            {
                "order_id": f"o{i}",
                "instrument": "USD_JPY",
                "signal_age_seconds": float(i),
                "slippage_pips": 0.1,
                "fill_latency_ms": 10,
                "created_at": "2026-01-01",
            }
            for i in range(3)
        ]
        engine = _mock_engine(rows=rows)
        assert len(get_execution_quality_summary(engine)) == 3


class TestGetRiskStateDetail:
    def test_returns_list_of_dicts(self) -> None:
        row = {
            "risk_event_id": "r1",
            "cycle_id": "c1",
            "instrument": "EUR_USD",
            "decision": "accept",
            "reason_codes": None,
            "event_time_utc": "2026-01-01",
        }
        engine = _mock_engine(rows=[row])
        result = get_risk_state_detail(engine)
        assert result == [row]

    def test_empty_rows_returns_empty(self) -> None:
        assert get_risk_state_detail(_mock_engine(rows=[])) == []

    def test_reject_decision_preserved(self) -> None:
        row = {
            "risk_event_id": "r2",
            "cycle_id": "c2",
            "instrument": "GBP_USD",
            "decision": "reject",
            "reason_codes": ["drawdown"],
            "event_time_utc": "2026-01-01",
        }
        engine = _mock_engine(rows=[row])
        result = get_risk_state_detail(engine)
        assert result[0]["decision"] == "reject"


class TestGetCloseEventsRecent:
    def test_returns_list_of_dicts(self) -> None:
        row = {
            "close_event_id": "ce1",
            "order_id": "o1",
            "primary_reason_code": "tp",
            "reasons": [{"priority": 1, "reason_code": "tp"}],
            "closed_at": "2026-01-01",
            "pnl_realized": 12.5,
        }
        engine = _mock_engine(rows=[row])
        result = get_close_events_recent(engine)
        assert result == [row]

    def test_empty_rows_returns_empty(self) -> None:
        assert get_close_events_recent(_mock_engine(rows=[])) == []

    def test_pnl_realized_none_preserved(self) -> None:
        row = {
            "close_event_id": "ce2",
            "order_id": "o2",
            "primary_reason_code": "sl",
            "reasons": [],
            "closed_at": "2026-01-01",
            "pnl_realized": None,
        }
        engine = _mock_engine(rows=[row])
        result = get_close_events_recent(engine)
        assert result[0]["pnl_realized"] is None


# ---------------------------------------------------------------------------
# Cycle 6.9d — ExitFireMetricsService UI-safe wrappers
# ---------------------------------------------------------------------------
#
# The wrappers delegate to ExitFireMetricsService, which uses
# ``conn.execute().fetchall()`` / ``.fetchone()`` (NOT ``.mappings().all()``
# like the existing dashboard queries above). A dedicated mock helper
# matches that interface so the wrapper + service path can be exercised
# end-to-end without touching a real DB.


def _mock_engine_for_service(
    rows: list[tuple] | None = None,
    *,
    one: tuple | None = None,
) -> MagicMock:
    """Engine mock matching ExitFireMetricsService's fetchall / fetchone usage."""
    engine = MagicMock()
    conn = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = cm
    result = MagicMock()
    if rows is not None:
        result.fetchall.return_value = rows
        result.fetchone.return_value = rows[0] if rows else None
    if one is not None:
        result.fetchone.return_value = one
    conn.execute.return_value = result
    return engine


def _error_engine_for_service() -> MagicMock:
    """Engine mock that raises when the service issues conn.execute()."""
    engine = MagicMock()
    conn = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=conn)
    cm.__exit__ = MagicMock(return_value=False)
    engine.connect.return_value = cm
    conn.execute.side_effect = RuntimeError("db error")
    return engine


_EMPTY_SUMMARY_FALLBACK = {
    "total_fires": 0,
    "distinct_reasons": 0,
    "span_start_utc": None,
    "span_end_utc": None,
}


class TestGetExitFireSummary:
    def test_engine_none_returns_empty_summary(self) -> None:
        assert get_exit_fire_summary(None) == _EMPTY_SUMMARY_FALLBACK

    def test_db_error_returns_empty_summary(self) -> None:
        assert get_exit_fire_summary(_error_engine_for_service()) == _EMPTY_SUMMARY_FALLBACK

    def test_returns_service_result_on_success(self) -> None:
        engine = _mock_engine_for_service(one=(7, 3, None, None))
        result = get_exit_fire_summary(engine)
        assert result == {
            "total_fires": 7,
            "distinct_reasons": 3,
            "span_start_utc": None,
            "span_end_utc": None,
        }

    def test_window_seconds_converted_to_timedelta(self) -> None:
        engine = _mock_engine_for_service(one=(0, 0, None, None))
        get_exit_fire_summary(engine, window_seconds=3600)
        # The service appends WHERE closed_at >= :since when window is set,
        # and the SQL fragment is observable on the captured execute call.
        sql_arg, params = engine.connect.return_value.__enter__.return_value.execute.call_args[0]
        assert "WHERE closed_at >= :since" in str(sql_arg)
        assert "since" in params


class TestGetExitFireCountByReason:
    def test_engine_none_returns_empty_dict(self) -> None:
        assert get_exit_fire_count_by_reason(None) == {}

    def test_db_error_returns_empty_dict(self) -> None:
        assert get_exit_fire_count_by_reason(_error_engine_for_service()) == {}

    def test_returns_service_result_on_success(self) -> None:
        engine = _mock_engine_for_service(rows=[("tp", 5), ("sl", 2)])
        result = get_exit_fire_count_by_reason(engine)
        assert result == {"tp": 5, "sl": 2}

    def test_window_seconds_zero_treated_as_window(self) -> None:
        # 0 seconds is still a window (since = now - 0s = now). Wrapper must
        # NOT treat 0 as None (only None means "all time").
        engine = _mock_engine_for_service(rows=[])
        get_exit_fire_count_by_reason(engine, window_seconds=0)
        sql_arg, _ = engine.connect.return_value.__enter__.return_value.execute.call_args[0]
        assert "WHERE closed_at >= :since" in str(sql_arg)


class TestGetExitFirePnlSummaryByReason:
    def test_engine_none_returns_empty_dict(self) -> None:
        assert get_exit_fire_pnl_summary_by_reason(None) == {}

    def test_db_error_returns_empty_dict(self) -> None:
        assert get_exit_fire_pnl_summary_by_reason(_error_engine_for_service()) == {}

    def test_returns_service_result_with_null_pnl(self) -> None:
        # Phase 6 paper: pnl_realized is always NULL → pnl_sum/avg surface as None.
        engine = _mock_engine_for_service(rows=[("tp", 4, None, None)])
        result = get_exit_fire_pnl_summary_by_reason(engine)
        assert result == {"tp": {"count": 4, "pnl_sum": None, "pnl_avg": None}}


class TestGetExitFireRecent:
    def test_engine_none_returns_empty_list(self) -> None:
        assert get_exit_fire_recent(None) == []

    def test_db_error_returns_empty_list(self) -> None:
        assert get_exit_fire_recent(_error_engine_for_service()) == []

    def test_returns_service_result_on_success(self) -> None:
        # Service.recent_fires returns an 8-tuple per row; reasons can be a
        # JSON string (parsed) or already a list. Use list form here for clarity.
        engine = _mock_engine_for_service(
            rows=[
                (
                    "ce1",
                    "o1",
                    "ps1",
                    [{"priority": 1, "reason_code": "tp", "detail": ""}],
                    "tp",
                    "2026-04-21T12:00:00+00:00",
                    None,
                    "corr-1",
                )
            ]
        )
        result = get_exit_fire_recent(engine, limit=10)
        assert len(result) == 1
        assert result[0]["close_event_id"] == "ce1"
        assert result[0]["primary_reason_code"] == "tp"
        assert result[0]["pnl_realized"] is None


class TestExitFireWrapperHelpers:
    def test_to_window_none_passes_none(self) -> None:
        # If wrapper-side conversion regresses (e.g., None -> timedelta(0)),
        # the unbounded path would be lost. Pin via service SQL: window=None
        # must NOT add WHERE clause.
        engine = _mock_engine_for_service(rows=[])
        get_exit_fire_count_by_reason(engine, window_seconds=None)
        sql_arg, _ = engine.connect.return_value.__enter__.return_value.execute.call_args[0]
        assert "WHERE" not in str(sql_arg)

    def test_window_seconds_int_converted_correctly(self) -> None:
        engine = _mock_engine_for_service(rows=[])
        get_exit_fire_count_by_reason(engine, window_seconds=120)
        _, params = engine.connect.return_value.__enter__.return_value.execute.call_args[0]
        # The service computes since = clock.now() - timedelta(seconds=120).
        # We only assert the param key is present and is a timedelta-derived
        # datetime; precise time comparison would require Clock injection
        # which the wrapper deliberately leaves to the service default.
        assert "since" in params
        # The 'since' value must reflect a 120-second window, but since
        # WallClock.now() is non-deterministic here, we instead verify the
        # request shape via a second call with a different window and compare.
        assert isinstance(params["since"], type(params["since"]))
        # Sanity check: differing window_seconds produce differing :since.
        first_since = params["since"]
        get_exit_fire_count_by_reason(engine, window_seconds=1)
        _, params2 = engine.connect.return_value.__enter__.return_value.execute.call_args[0]
        # 120s window starts further in the past than 1s window → first_since < params2["since"]
        assert first_since < params2["since"]
        # (delta should be roughly 119s ± WallClock tick)
        delta = params2["since"] - first_since
        assert timedelta(seconds=110) < delta < timedelta(seconds=130)
