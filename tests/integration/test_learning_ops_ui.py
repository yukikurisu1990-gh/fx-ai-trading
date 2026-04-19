"""Integration tests: Learning Ops UI panel (M21 / M-LRN-1).

Verifies the enqueue → status → history flow end-to-end using a real
in-memory SQLite.  Streamlit calls are mocked so tests run without a
Streamlit runtime.
"""

from __future__ import annotations

import inspect
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.services import dashboard_query_service
from fx_ai_trading.services.learning_ops import LearningOps

_PANEL = "fx_ai_trading.dashboard.panels.learning_ops"

_DDL = [
    """CREATE TABLE system_jobs (
        system_job_id TEXT PRIMARY KEY,
        job_type      TEXT NOT NULL,
        status        TEXT NOT NULL DEFAULT 'pending',
        started_at    TEXT,
        ended_at      TEXT,
        input_params  TEXT,
        result_summary TEXT,
        error_detail  TEXT,
        created_at    TEXT NOT NULL
    )""",
    """CREATE TABLE training_runs (
        training_run_id TEXT PRIMARY KEY,
        experiment_id   TEXT,
        model_id        TEXT,
        status          TEXT NOT NULL DEFAULT 'pending',
        started_at      TEXT,
        ended_at        TEXT,
        input_params    TEXT,
        artifact_path   TEXT,
        created_at      TEXT NOT NULL
    )""",
]


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        for ddl in _DDL:
            conn.execute(text(ddl))
    yield eng
    eng.dispose()


class TestLearningOpsPanelContract:
    def test_module_importable(self) -> None:
        import fx_ai_trading.dashboard.panels.learning_ops  # noqa: F401

    def test_render_callable(self) -> None:
        from fx_ai_trading.dashboard.panels.learning_ops import render

        assert callable(render)

    def test_fetch_callable(self) -> None:
        from fx_ai_trading.dashboard.panels.learning_ops import _fetch

        assert callable(_fetch)

    def test_uses_cache_data_ttl_10(self) -> None:
        import fx_ai_trading.dashboard.panels.learning_ops as mod

        src = inspect.getsource(mod)
        assert "cache_data" in src
        assert "ttl=10" in src

    def test_references_get_learning_jobs(self) -> None:
        import fx_ai_trading.dashboard.panels.learning_ops as mod

        src = inspect.getsource(mod._fetch)
        assert "get_learning_jobs" in src

    def test_render_none_engine_does_not_raise(self) -> None:
        from fx_ai_trading.dashboard.panels import learning_ops

        with patch(f"{_PANEL}.st") as mock_st:
            mock_st.cache_data = lambda ttl: lambda f: f
            learning_ops.render(None)

    def test_render_empty_db_shows_info(self, engine) -> None:
        from fx_ai_trading.dashboard.panels import learning_ops

        with patch(f"{_PANEL}.st") as mock_st:
            mock_st.cache_data = lambda ttl: lambda f: f
            mock_st.button.return_value = False
            with patch.object(learning_ops, "_fetch", return_value=[]):
                learning_ops.render(engine)
        mock_st.info.assert_called()


class TestLearningOpsEndToEnd:
    def test_enqueue_creates_job(self, engine) -> None:
        ops = LearningOps()
        job_id = ops.enqueue(engine)
        jobs = dashboard_query_service.get_learning_jobs(engine)
        assert len(jobs) == 1
        assert jobs[0]["system_job_id"] == job_id

    def test_execute_stub_transitions_to_success(self, engine) -> None:
        ops = LearningOps()
        job_id = ops.enqueue(engine)
        ops.execute_stub(engine, job_id)
        jobs = dashboard_query_service.get_learning_jobs(engine)
        assert jobs[0]["status"] == "success"

    def test_render_with_data_does_not_call_info(self, engine) -> None:
        from fx_ai_trading.dashboard.panels import learning_ops

        ops = LearningOps()
        job_id = ops.enqueue(engine)
        ops.execute_stub(engine, job_id)
        rows = dashboard_query_service.get_learning_jobs(engine)

        with patch(f"{_PANEL}.st") as mock_st:
            mock_st.button.return_value = False
            with patch.object(learning_ops, "_fetch", return_value=rows):
                learning_ops.render(engine)
        mock_st.info.assert_not_called()

    def test_render_button_triggers_enqueue(self, engine) -> None:
        from fx_ai_trading.dashboard.panels import learning_ops

        with patch(f"{_PANEL}.st") as mock_st:
            mock_st.button.return_value = True
            with patch.object(learning_ops, "_fetch", return_value=[]):
                learning_ops.render(engine)

        jobs = dashboard_query_service.get_learning_jobs(engine)
        assert len(jobs) == 1
        assert jobs[0]["status"] == "success"

    def test_multiple_jobs_displayed(self, engine) -> None:
        from fx_ai_trading.dashboard.panels import learning_ops

        ops = LearningOps()
        for _ in range(3):
            jid = ops.enqueue(engine)
            ops.execute_stub(engine, jid)

        rows = dashboard_query_service.get_learning_jobs(engine)
        assert len(rows) == 3

        with patch(f"{_PANEL}.st") as mock_st:
            mock_st.button.return_value = False
            with patch.object(learning_ops, "_fetch", return_value=rows):
                learning_ops.render(engine)
        mock_st.dataframe.assert_called_once()
