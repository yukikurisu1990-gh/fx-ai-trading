"""Contract tests: M19-A panel structural contracts.

Verifies for each of the 3 new panels (top_candidates, execution_quality,
risk_state_detail):
  1. Module is importable.
  2. render() function exists and is callable.
  3. _fetch() function exists and is callable.
  4. render(engine=None) does not raise (graceful fallback when no DB).
  5. render(engine, rows) does not raise (data path).
  6. The panel module references the correct dashboard_query_service attribute.

Streamlit calls are mocked so these tests run without a Streamlit runtime.
Note: _fetch is decorated with @st.cache_data — delegation is verified via
module attribute inspection rather than live call tracing.
"""

from __future__ import annotations

import inspect
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _patch_st(panel_module_path: str):
    """Return a context manager patching the st module in *panel_module_path*."""
    return patch(f"{panel_module_path}.st")


# ---------------------------------------------------------------------------
# top_candidates
# ---------------------------------------------------------------------------

_TOP = "fx_ai_trading.dashboard.panels.top_candidates"


class TestTopCandidatesPanel:
    def test_module_importable(self) -> None:
        import fx_ai_trading.dashboard.panels.top_candidates  # noqa: F401

    def test_render_is_callable(self) -> None:
        from fx_ai_trading.dashboard.panels.top_candidates import render

        assert callable(render)

    def test_fetch_is_callable(self) -> None:
        from fx_ai_trading.dashboard.panels.top_candidates import _fetch

        assert callable(_fetch)

    def test_render_none_engine_does_not_raise(self) -> None:
        from fx_ai_trading.dashboard.panels import top_candidates

        with _patch_st(_TOP) as mock_st:
            mock_st.cache_data = lambda ttl: lambda f: f
            top_candidates.render(None)

    def test_render_with_rows_does_not_raise(self) -> None:
        from fx_ai_trading.dashboard.panels import top_candidates

        rows = [
            {
                "instrument": "EUR_USD",
                "strategy_id": "AI",
                "tss_score": 0.9,
                "direction": "buy",
                "rank": 1,
                "generated_at": "2026-01-01",
            }
        ]
        with _patch_st(_TOP) as mock_st:
            mock_st.cache_data = lambda ttl: lambda f: f
            with patch(f"{_TOP}.dashboard_query_service") as mock_svc:
                mock_svc.get_top_candidates.return_value = rows
                top_candidates.render(MagicMock())

    def test_panel_references_get_top_candidates(self) -> None:
        """Verify _fetch source calls get_top_candidates (not another service fn)."""
        import fx_ai_trading.dashboard.panels.top_candidates as mod

        src = inspect.getsource(mod._fetch)
        assert "get_top_candidates" in src

    def test_panel_uses_cache_data_ttl_5(self) -> None:
        import fx_ai_trading.dashboard.panels.top_candidates as mod

        src = inspect.getsource(mod)
        assert "cache_data" in src
        assert "ttl=5" in src


# ---------------------------------------------------------------------------
# execution_quality
# ---------------------------------------------------------------------------

_EXEC = "fx_ai_trading.dashboard.panels.execution_quality"


class TestExecutionQualityPanel:
    def test_module_importable(self) -> None:
        import fx_ai_trading.dashboard.panels.execution_quality  # noqa: F401

    def test_render_is_callable(self) -> None:
        from fx_ai_trading.dashboard.panels.execution_quality import render

        assert callable(render)

    def test_fetch_is_callable(self) -> None:
        from fx_ai_trading.dashboard.panels.execution_quality import _fetch

        assert callable(_fetch)

    def test_render_none_engine_does_not_raise(self) -> None:
        from fx_ai_trading.dashboard.panels import execution_quality

        with _patch_st(_EXEC) as mock_st:
            mock_st.cache_data = lambda ttl: lambda f: f
            execution_quality.render(None)

    def test_render_with_rows_does_not_raise(self) -> None:
        from fx_ai_trading.dashboard.panels import execution_quality

        rows = [
            {
                "order_id": "o1",
                "instrument": "EUR_USD",
                "signal_age_seconds": 3.0,
                "slippage_pips": 0.2,
                "fill_latency_ms": 45,
                "created_at": "2026-01-01",
            }
        ]
        with _patch_st(_EXEC) as mock_st:
            mock_st.cache_data = lambda ttl: lambda f: f
            with patch(f"{_EXEC}.dashboard_query_service") as mock_svc:
                mock_svc.get_execution_quality_summary.return_value = rows
                execution_quality.render(MagicMock())

    def test_panel_references_get_execution_quality_summary(self) -> None:
        import fx_ai_trading.dashboard.panels.execution_quality as mod

        src = inspect.getsource(mod._fetch)
        assert "get_execution_quality_summary" in src

    def test_panel_uses_cache_data_ttl_5(self) -> None:
        import fx_ai_trading.dashboard.panels.execution_quality as mod

        src = inspect.getsource(mod)
        assert "cache_data" in src
        assert "ttl=5" in src


# ---------------------------------------------------------------------------
# risk_state_detail
# ---------------------------------------------------------------------------

_RISK = "fx_ai_trading.dashboard.panels.risk_state_detail"


class TestRiskStateDetailPanel:
    def test_module_importable(self) -> None:
        import fx_ai_trading.dashboard.panels.risk_state_detail  # noqa: F401

    def test_render_is_callable(self) -> None:
        from fx_ai_trading.dashboard.panels.risk_state_detail import render

        assert callable(render)

    def test_fetch_is_callable(self) -> None:
        from fx_ai_trading.dashboard.panels.risk_state_detail import _fetch

        assert callable(_fetch)

    def test_render_none_engine_does_not_raise(self) -> None:
        from fx_ai_trading.dashboard.panels import risk_state_detail

        with _patch_st(_RISK) as mock_st:
            mock_st.cache_data = lambda ttl: lambda f: f
            risk_state_detail.render(None)

    def test_render_with_rejects_does_not_raise(self) -> None:
        from fx_ai_trading.dashboard.panels import risk_state_detail

        rows = [
            {
                "risk_event_id": "r1",
                "cycle_id": "c1",
                "instrument": "EUR_USD",
                "decision": "reject",
                "reason_codes": ["drawdown"],
                "event_time_utc": "2026-01-01",
            }
        ]
        with _patch_st(_RISK) as mock_st:
            mock_st.cache_data = lambda ttl: lambda f: f
            with patch(f"{_RISK}.dashboard_query_service") as mock_svc:
                mock_svc.get_risk_state_detail.return_value = rows
                risk_state_detail.render(MagicMock())

    def test_render_with_accepts_does_not_raise(self) -> None:
        from fx_ai_trading.dashboard.panels import risk_state_detail

        rows = [
            {
                "risk_event_id": "r2",
                "cycle_id": "c2",
                "instrument": "USD_JPY",
                "decision": "accept",
                "reason_codes": None,
                "event_time_utc": "2026-01-01",
            }
        ]
        with _patch_st(_RISK) as mock_st:
            mock_st.cache_data = lambda ttl: lambda f: f
            with patch(f"{_RISK}.dashboard_query_service") as mock_svc:
                mock_svc.get_risk_state_detail.return_value = rows
                risk_state_detail.render(MagicMock())

    def test_panel_references_get_risk_state_detail(self) -> None:
        import fx_ai_trading.dashboard.panels.risk_state_detail as mod

        src = inspect.getsource(mod._fetch)
        assert "get_risk_state_detail" in src

    def test_panel_uses_cache_data_ttl_5(self) -> None:
        import fx_ai_trading.dashboard.panels.risk_state_detail as mod

        src = inspect.getsource(mod)
        assert "cache_data" in src
        assert "ttl=5" in src
