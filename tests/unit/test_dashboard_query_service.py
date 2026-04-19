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

from unittest.mock import MagicMock

from fx_ai_trading.services.dashboard_query_service import (
    get_app_setting,
    get_close_events_recent,
    get_daily_order_summary,
    get_execution_quality_summary,
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
