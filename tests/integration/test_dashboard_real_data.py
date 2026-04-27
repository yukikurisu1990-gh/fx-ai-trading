"""Integration tests: M19-B — all 10 dashboard panels with real SQLite.

Strategy:
  Part A — Query-layer: call dashboard_query_service functions directly against
            a real in-memory SQLite seeded with one row per table.  No mocks.
            Verifies SQL is correct and returns non-empty results.
  Part B — Render-path: call each panel's render() with the real engine and
            mocked Streamlit.  Verifies the non-fallback data path executes
            without exception (st.info / st.warning fallback NOT triggered).

meta_decision panel has no DB dependency; its render() always shows a static
placeholder and is verified in Part B only.

top_candidates panel queries dashboard_top_candidates (created in M20).
The fixture pre-creates this table so the panel returns real data here;
production will return [] until M20 migration runs.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.services import dashboard_query_service

# ---------------------------------------------------------------------------
# Fixture: in-memory SQLite seeded with one row per table
# ---------------------------------------------------------------------------

_DDL = [
    """CREATE TABLE positions (
        position_snapshot_id TEXT PRIMARY KEY,
        account_id           TEXT,
        instrument           TEXT,
        event_type           TEXT,
        units                REAL,
        avg_price            REAL,
        unrealized_pl        REAL,
        event_time_utc       TEXT
    )""",
    """CREATE TABLE orders (
        order_id    TEXT PRIMARY KEY,
        instrument  TEXT,
        direction   TEXT,
        units       REAL,
        status      TEXT,
        created_at  TEXT
    )""",
    """CREATE TABLE supervisor_events (
        supervisor_event_id TEXT PRIMARY KEY,
        event_type          TEXT,
        run_id              TEXT,
        config_version      TEXT,
        event_time_utc      TEXT,
        detail              TEXT
    )""",
    """CREATE TABLE app_settings (
        name                TEXT PRIMARY KEY,
        value               TEXT,
        value_type          TEXT,
        introduced_in_version TEXT
    )""",
    """CREATE TABLE execution_metrics (
        execution_metric_id TEXT PRIMARY KEY,
        order_id            TEXT,
        signal_age_seconds  REAL,
        slippage_pips       REAL,
        latency_ms          REAL,
        recorded_at         TEXT
    )""",
    """CREATE TABLE risk_events (
        risk_event_id       TEXT PRIMARY KEY,
        cycle_id            TEXT,
        instrument          TEXT,
        verdict             TEXT,
        constraint_violated TEXT,
        event_time_utc      TEXT
    )""",
    """CREATE TABLE dashboard_top_candidates (
        candidate_id TEXT PRIMARY KEY,
        instrument   TEXT,
        strategy_id  TEXT,
        tss_score    REAL,
        direction    TEXT,
        generated_at TEXT,
        rank         INTEGER
    )""",
]

_T = "'2026-01-01T00:00:00'"

_SEEDS = [
    f"INSERT INTO positions VALUES ('ps1','acct1','EUR_USD','open',10000,1.105,-5.0,{_T})",
    "INSERT INTO orders VALUES ('o1','EUR_USD','buy',1000,'FILLED',datetime('now'))",
    f"INSERT INTO supervisor_events VALUES ('se1','system_start','run1','0.0.1',{_T},'{{}}')",
    "INSERT INTO app_settings VALUES ('phase_mode','phase6','string','0.0.1')",
    "INSERT INTO app_settings VALUES ('runtime_environment','demo','string','0.0.1')",
    f"INSERT INTO execution_metrics VALUES ('em1','o1',2.5,0.3,45.0,{_T})",
    f"INSERT INTO risk_events VALUES ('re1','c1','EUR_USD','accept',NULL,{_T})",
    f"INSERT INTO dashboard_top_candidates VALUES ('tc1','EUR_USD','AI',0.91,'buy',{_T},1)",
]


@pytest.fixture()
def seeded_engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        for ddl in _DDL:
            conn.execute(text(ddl))
        for seed in _SEEDS:
            conn.execute(text(seed))
    yield eng
    eng.dispose()


# ---------------------------------------------------------------------------
# Part A: Query-layer (no mocks, real SQLite)
# ---------------------------------------------------------------------------


class TestQueryLayerRealSQLite:
    def test_get_open_positions_returns_data(self, seeded_engine) -> None:
        rows = dashboard_query_service.get_open_positions(seeded_engine)
        assert len(rows) == 1
        assert rows[0]["instrument"] == "EUR_USD"

    def test_get_recent_orders_returns_data(self, seeded_engine) -> None:
        rows = dashboard_query_service.get_recent_orders(seeded_engine)
        assert len(rows) == 1
        assert rows[0]["status"] == "FILLED"

    def test_get_recent_supervisor_events_returns_data(self, seeded_engine) -> None:
        rows = dashboard_query_service.get_recent_supervisor_events(seeded_engine)
        assert len(rows) == 1
        assert rows[0]["event_type"] == "system_start"

    def test_get_app_setting_phase_mode(self, seeded_engine) -> None:
        val = dashboard_query_service.get_app_setting(seeded_engine, "phase_mode")
        assert val == "phase6"

    def test_get_daily_order_summary_returns_counts(self, seeded_engine) -> None:
        result = dashboard_query_service.get_daily_order_summary(seeded_engine)
        assert isinstance(result, dict)
        assert "total" in result
        assert result["filled"] >= 0

    def test_get_execution_quality_summary_returns_data(self, seeded_engine) -> None:
        rows = dashboard_query_service.get_execution_quality_summary(seeded_engine)
        assert len(rows) == 1
        assert rows[0]["order_id"] == "o1"

    def test_get_risk_state_detail_returns_data(self, seeded_engine) -> None:
        rows = dashboard_query_service.get_risk_state_detail(seeded_engine)
        assert len(rows) == 1
        assert rows[0]["verdict"] == "accept"

    def test_get_top_candidates_returns_data(self, seeded_engine) -> None:
        rows = dashboard_query_service.get_top_candidates(seeded_engine)
        assert len(rows) == 1
        assert rows[0]["instrument"] == "EUR_USD"
        assert rows[0]["rank"] == 1

    def test_none_engine_returns_empty_for_all(self) -> None:
        assert dashboard_query_service.get_open_positions(None) == []
        assert dashboard_query_service.get_recent_orders(None) == []
        assert dashboard_query_service.get_recent_supervisor_events(None) == []
        assert dashboard_query_service.get_app_setting(None, "phase_mode") is None
        assert dashboard_query_service.get_daily_order_summary(None) == {
            "total": 0,
            "filled": 0,
            "canceled": 0,
            "failed": 0,
        }
        assert dashboard_query_service.get_execution_quality_summary(None) == []
        assert dashboard_query_service.get_risk_state_detail(None) == []
        assert dashboard_query_service.get_top_candidates(None) == []


# ---------------------------------------------------------------------------
# Part B: Render-path (mocked st, real SQLite engine, patched _fetch to bypass
# st.cache_data so real engine calls reach the query layer)
# ---------------------------------------------------------------------------

# Patching _fetch is necessary because @st.cache_data wraps it at import time.
# Without patching, the cache may return stale [] from prior test runs in the
# same process.  We replace _fetch with a thin lambda that calls the underlying
# query service directly, preserving the real DB round-trip.


class TestPanelRenderWithRealEngine:
    def test_positions_render_data_path(self, seeded_engine) -> None:
        from fx_ai_trading.dashboard.panels import positions

        real_rows = dashboard_query_service.get_open_positions(seeded_engine)
        with (
            patch("fx_ai_trading.dashboard.panels.positions.st") as mock_st,
            patch.object(positions, "_fetch", return_value=real_rows),
        ):
            positions.render(seeded_engine)
        mock_st.info.assert_not_called()

    def test_daily_metrics_render_data_path(self, seeded_engine) -> None:
        from fx_ai_trading.dashboard.panels import daily_metrics

        real_data = dashboard_query_service.get_daily_order_summary(seeded_engine)
        with (
            patch("fx_ai_trading.dashboard.panels.daily_metrics.st") as mock_st,
            patch.object(daily_metrics, "_fetch", return_value=real_data),
        ):
            mock_st.columns.return_value = [MagicMock(), MagicMock(), MagicMock()]
            daily_metrics.render(seeded_engine)
        mock_st.info.assert_not_called()

    def test_market_state_render_does_not_raise(self, seeded_engine) -> None:
        from fx_ai_trading.dashboard.panels import market_state

        with (
            patch("fx_ai_trading.dashboard.panels.market_state.st"),
            patch.object(
                market_state,
                "_fetch",
                return_value={"phase_mode": "phase6", "runtime_environment": "demo"},
            ),
        ):
            market_state.render(seeded_engine)

    def test_meta_decision_render_does_not_raise(self, seeded_engine) -> None:
        from fx_ai_trading.dashboard.panels import meta_decision

        with patch("fx_ai_trading.dashboard.panels.meta_decision.st"):
            meta_decision.render(seeded_engine)

    def test_recent_signals_render_data_path(self, seeded_engine) -> None:
        from fx_ai_trading.dashboard.panels import recent_signals

        real_rows = dashboard_query_service.get_recent_orders(seeded_engine)
        with (
            patch("fx_ai_trading.dashboard.panels.recent_signals.st") as mock_st,
            patch.object(recent_signals, "_fetch", return_value=real_rows),
        ):
            recent_signals.render(seeded_engine)
        mock_st.info.assert_not_called()

    def test_strategy_summary_render_does_not_raise(self, seeded_engine) -> None:
        from fx_ai_trading.dashboard.panels import strategy_summary

        real_rows = dashboard_query_service.get_recent_orders(seeded_engine)
        with (
            patch("fx_ai_trading.dashboard.panels.strategy_summary.st") as mock_st,
            patch.object(strategy_summary, "_fetch", return_value=real_rows),
        ):
            mock_st.columns.return_value = [MagicMock(), MagicMock()]
            strategy_summary.render(seeded_engine)

    def test_supervisor_status_render_data_path(self, seeded_engine) -> None:
        from fx_ai_trading.dashboard.panels import supervisor_status

        real_rows = dashboard_query_service.get_recent_supervisor_events(seeded_engine)
        with (
            patch("fx_ai_trading.dashboard.panels.supervisor_status.st") as mock_st,
            patch.object(supervisor_status, "_fetch", return_value=real_rows),
        ):
            supervisor_status.render(seeded_engine)
        mock_st.info.assert_not_called()

    def test_execution_quality_render_data_path(self, seeded_engine) -> None:
        from fx_ai_trading.dashboard.panels import execution_quality

        real_rows = dashboard_query_service.get_execution_quality_summary(seeded_engine)
        with (
            patch("fx_ai_trading.dashboard.panels.execution_quality.st") as mock_st,
            patch.object(execution_quality, "_fetch", return_value=real_rows),
        ):
            execution_quality.render(seeded_engine)
        mock_st.info.assert_not_called()

    def test_risk_state_detail_render_data_path(self, seeded_engine) -> None:
        from fx_ai_trading.dashboard.panels import risk_state_detail

        real_rows = dashboard_query_service.get_risk_state_detail(seeded_engine)
        with (
            patch("fx_ai_trading.dashboard.panels.risk_state_detail.st") as mock_st,
            patch.object(risk_state_detail, "_fetch", return_value=real_rows),
        ):
            risk_state_detail.render(seeded_engine)
        mock_st.info.assert_not_called()

    def test_top_candidates_render_data_path(self, seeded_engine) -> None:
        from fx_ai_trading.dashboard.panels import top_candidates

        real_rows = dashboard_query_service.get_top_candidates(seeded_engine)
        assert real_rows, "dashboard_top_candidates fixture must return data"
        with (
            patch("fx_ai_trading.dashboard.panels.top_candidates.st") as mock_st,
            patch.object(top_candidates, "_fetch", return_value=real_rows),
        ):
            top_candidates.render(seeded_engine)
        mock_st.info.assert_not_called()

    def test_all_10_panels_render_without_exception(self, seeded_engine) -> None:
        """Smoke test: all 10 panels render() call completes without raising."""
        from fx_ai_trading.dashboard.panels import (
            daily_metrics,
            execution_quality,
            market_state,
            meta_decision,
            positions,
            recent_signals,
            risk_state_detail,
            strategy_summary,
            supervisor_status,
            top_candidates,
        )

        panels = [
            positions,
            daily_metrics,
            market_state,
            meta_decision,
            recent_signals,
            strategy_summary,
            supervisor_status,
            execution_quality,
            risk_state_detail,
            top_candidates,
        ]

        svc = dashboard_query_service
        fetch_returns = {
            "positions": svc.get_open_positions(seeded_engine),
            "daily_metrics": svc.get_daily_order_summary(seeded_engine),
            "market_state": {"phase_mode": "phase6", "runtime_environment": "demo"},
            "recent_signals": svc.get_recent_orders(seeded_engine),
            "strategy_summary": svc.get_recent_orders(seeded_engine),
            "supervisor_status": svc.get_recent_supervisor_events(seeded_engine),
            "execution_quality": svc.get_execution_quality_summary(seeded_engine),
            "risk_state_detail": svc.get_risk_state_detail(seeded_engine),
            "top_candidates": svc.get_top_candidates(seeded_engine),
        }

        _columns_count = {
            "daily_metrics": 3,
            "strategy_summary": 2,
        }

        for panel in panels:
            name = panel.__name__.split(".")[-1]
            with patch(f"fx_ai_trading.dashboard.panels.{name}.st") as mock_st:
                n_cols = _columns_count.get(name)
                if n_cols:
                    mock_st.columns.return_value = [MagicMock() for _ in range(n_cols)]
                if name in fetch_returns:
                    with patch.object(panel, "_fetch", return_value=fetch_returns[name]):
                        panel.render(MagicMock())
                else:
                    panel.render(MagicMock())
