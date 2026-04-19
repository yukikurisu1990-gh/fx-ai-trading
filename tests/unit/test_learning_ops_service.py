"""Unit tests: LearningOps service (M21 / M-LRN-1).

Uses a real in-memory SQLite with system_jobs and training_runs tables.
No Streamlit, no mocks on the DB layer.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.services import dashboard_query_service
from fx_ai_trading.services.learning_ops import LearningOps

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


def _jobs(eng) -> list[dict]:
    with eng.connect() as conn:
        rows = conn.execute(text("SELECT * FROM system_jobs ORDER BY created_at")).mappings().all()
    return [dict(r) for r in rows]


def _runs(eng) -> list[dict]:
    with eng.connect() as conn:
        rows = (
            conn.execute(text("SELECT * FROM training_runs ORDER BY created_at")).mappings().all()
        )
    return [dict(r) for r in rows]


class TestLearningOpsEnqueue:
    def test_enqueue_returns_string_job_id(self, engine) -> None:
        ops = LearningOps()
        job_id = ops.enqueue(engine)
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    def test_enqueue_inserts_row(self, engine) -> None:
        ops = LearningOps()
        ops.enqueue(engine)
        rows = _jobs(engine)
        assert len(rows) == 1

    def test_enqueue_status_is_pending(self, engine) -> None:
        ops = LearningOps()
        ops.enqueue(engine)
        rows = _jobs(engine)
        assert rows[0]["status"] == "pending"

    def test_enqueue_job_type_is_training(self, engine) -> None:
        ops = LearningOps()
        ops.enqueue(engine)
        rows = _jobs(engine)
        assert rows[0]["job_type"] == "training"

    def test_enqueue_returns_id_matching_row(self, engine) -> None:
        ops = LearningOps()
        job_id = ops.enqueue(engine)
        rows = _jobs(engine)
        assert rows[0]["system_job_id"] == job_id

    def test_enqueue_multiple_jobs(self, engine) -> None:
        ops = LearningOps()
        id1 = ops.enqueue(engine)
        id2 = ops.enqueue(engine)
        assert id1 != id2
        assert len(_jobs(engine)) == 2

    def test_enqueue_with_input_params(self, engine) -> None:
        ops = LearningOps()
        ops.enqueue(engine, input_params={"epochs": 10})
        rows = _jobs(engine)
        assert "epochs" in rows[0]["input_params"]


class TestLearningOpsExecuteStub:
    def test_execute_stub_sets_status_success(self, engine) -> None:
        ops = LearningOps()
        job_id = ops.enqueue(engine)
        ops.execute_stub(engine, job_id)
        rows = _jobs(engine)
        assert rows[0]["status"] == "success"

    def test_execute_stub_sets_started_at(self, engine) -> None:
        ops = LearningOps()
        job_id = ops.enqueue(engine)
        ops.execute_stub(engine, job_id)
        rows = _jobs(engine)
        assert rows[0]["started_at"] is not None

    def test_execute_stub_sets_ended_at(self, engine) -> None:
        ops = LearningOps()
        job_id = ops.enqueue(engine)
        ops.execute_stub(engine, job_id)
        rows = _jobs(engine)
        assert rows[0]["ended_at"] is not None

    def test_execute_stub_inserts_training_run(self, engine) -> None:
        ops = LearningOps()
        job_id = ops.enqueue(engine)
        ops.execute_stub(engine, job_id)
        runs = _runs(engine)
        assert len(runs) == 1

    def test_execute_stub_training_run_status_success(self, engine) -> None:
        ops = LearningOps()
        job_id = ops.enqueue(engine)
        ops.execute_stub(engine, job_id)
        runs = _runs(engine)
        assert runs[0]["status"] == "success"

    def test_execute_stub_experiment_id_contains_job_prefix(self, engine) -> None:
        ops = LearningOps()
        job_id = ops.enqueue(engine)
        ops.execute_stub(engine, job_id)
        runs = _runs(engine)
        assert job_id[:8] in runs[0]["experiment_id"]


class TestGetLearningJobs:
    def test_returns_empty_when_no_engine(self) -> None:
        result = dashboard_query_service.get_learning_jobs(None)
        assert result == []

    def test_returns_empty_when_no_jobs(self, engine) -> None:
        result = dashboard_query_service.get_learning_jobs(engine)
        assert result == []

    def test_returns_training_jobs(self, engine) -> None:
        ops = LearningOps()
        ops.enqueue(engine)
        result = dashboard_query_service.get_learning_jobs(engine)
        assert len(result) == 1
        assert result[0]["job_type"] == "training"

    def test_filters_by_job_type_training(self, engine) -> None:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO system_jobs"
                    " (system_job_id, job_type, status, created_at)"
                    " VALUES ('x1','aggregation','pending','2026-01-01')"
                )
            )
        ops = LearningOps()
        ops.enqueue(engine)
        result = dashboard_query_service.get_learning_jobs(engine)
        assert all(r["job_type"] == "training" for r in result)
        assert len(result) == 1

    def test_fail_open_on_bad_engine(self) -> None:
        from sqlalchemy import create_engine as ce

        bad = ce("sqlite:///:memory:")
        bad.dispose()
        result = dashboard_query_service.get_learning_jobs(bad)
        assert result == []
