"""Integration tests: LearningOps challenger/champion promotion flow (Phase 9.8).

Uses a real in-memory SQLite.  No mocks on the DB layer.
"""

from __future__ import annotations

import json

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.services.learning_ops import LearningOps

_TRAINING_RUNS_DDL = """
CREATE TABLE training_runs (
    training_run_id TEXT PRIMARY KEY,
    experiment_id   TEXT,
    model_id        TEXT,
    status          TEXT NOT NULL DEFAULT 'pending',
    started_at      TEXT,
    ended_at        TEXT,
    input_params    TEXT,
    artifact_path   TEXT,
    created_at      TEXT NOT NULL
)
"""


@pytest.fixture()
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_TRAINING_RUNS_DDL))
    yield eng
    eng.dispose()


@pytest.fixture()
def ops(engine):
    from datetime import UTC, datetime

    svc = LearningOps(clock=FixedClock(datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)))
    svc.ensure_promotion_schema(engine)
    return svc


def _paper_stats(
    paper_days: int = 20,
    trade_count: int = 150,
    sharpe: float = 1.0,
    max_drawdown: float = 0.05,
) -> dict:
    return {
        "paper_days": paper_days,
        "trade_count": trade_count,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
    }


class TestRegisterChallenger:
    def test_inserts_challenger_row(self, engine, ops) -> None:
        run_id = ops.register_challenger(engine, model_id="m1", paper_stats=_paper_stats())
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT status, model_id FROM training_runs WHERE training_run_id = :rid"),
                {"rid": run_id},
            ).fetchone()
        assert row is not None
        assert row.status == "challenger"
        assert row.model_id == "m1"

    def test_paper_stats_stored_as_json(self, engine, ops) -> None:
        stats = _paper_stats(sharpe=0.9)
        run_id = ops.register_challenger(engine, model_id="m2", paper_stats=stats)
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT input_params FROM training_runs WHERE training_run_id = :rid"),
                {"rid": run_id},
            ).fetchone()
        loaded = json.loads(row.input_params)
        assert loaded["sharpe"] == pytest.approx(0.9)

    def test_artifact_path_stored(self, engine, ops) -> None:
        run_id = ops.register_challenger(engine, model_id="m3", artifact_path="/models/m3")
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT artifact_path FROM training_runs WHERE training_run_id = :rid"),
                {"rid": run_id},
            ).fetchone()
        assert row.artifact_path == "/models/m3"


class TestGetChampion:
    def test_returns_none_when_no_champion(self, engine, ops) -> None:
        assert ops.get_champion(engine) is None

    def test_returns_champion_row(self, engine, ops) -> None:
        run_id = ops.register_challenger(engine, model_id="m1")
        ops.promote(engine, run_id)
        champion = ops.get_champion(engine)
        assert champion is not None
        assert champion["training_run_id"] == run_id

    def test_returns_most_recent_when_multiple(self, engine, ops) -> None:
        from datetime import UTC, datetime

        r1 = ops.register_challenger(engine, model_id="m1")
        ops.promote(engine, r1)
        # promote a second challenger — first should become retired
        ops2 = LearningOps(clock=FixedClock(datetime(2024, 6, 2, 0, 0, 0, tzinfo=UTC)))
        r2 = ops2.register_challenger(engine, model_id="m2")
        ops2.promote(engine, r2)
        champion = ops.get_champion(engine)
        assert champion["training_run_id"] == r2


class TestPromote:
    def test_challenger_becomes_champion(self, engine, ops) -> None:
        run_id = ops.register_challenger(engine, model_id="m1")
        ops.promote(engine, run_id)
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT status FROM training_runs WHERE training_run_id = :rid"),
                {"rid": run_id},
            ).fetchone()
        assert row.status == "champion"

    def test_previous_champion_retired(self, engine, ops) -> None:
        r1 = ops.register_challenger(engine, model_id="m1")
        ops.promote(engine, r1)
        r2 = ops.register_challenger(engine, model_id="m2")
        ops.promote(engine, r2)
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT status FROM training_runs WHERE training_run_id = :rid"),
                {"rid": r1},
            ).fetchone()
        assert row.status == "retired"

    def test_only_one_champion_at_a_time(self, engine, ops) -> None:
        r1 = ops.register_challenger(engine, model_id="m1")
        ops.promote(engine, r1)
        r2 = ops.register_challenger(engine, model_id="m2")
        ops.promote(engine, r2)
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM training_runs WHERE status = 'champion'")
            ).scalar()
        assert count == 1


class TestLogPromotionDecision:
    def test_inserts_decision_row(self, engine, ops) -> None:
        run_id = ops.register_challenger(engine, model_id="m1")
        decision_id = ops.log_promotion_decision(
            engine,
            challenger_run_id=run_id,
            champion_run_id=None,
            promoted=True,
            reason="all_criteria_met",
            criteria_met={
                "min_days": True,
                "min_trades": True,
                "sharpe_margin": True,
                "max_dd_ratio": True,
            },
        )
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT promoted, reason FROM promotion_decisions WHERE decision_id = :did"),
                {"did": decision_id},
            ).fetchone()
        assert row is not None
        assert row.promoted == 1
        assert row.reason == "all_criteria_met"

    def test_rejected_decision_stored(self, engine, ops) -> None:
        run_id = ops.register_challenger(engine, model_id="m1")
        decision_id = ops.log_promotion_decision(
            engine,
            challenger_run_id=run_id,
            champion_run_id=None,
            promoted=False,
            reason="min_days|min_trades",
            criteria_met={
                "min_days": False,
                "min_trades": False,
                "sharpe_margin": True,
                "max_dd_ratio": True,
            },
        )
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT promoted, criteria_met FROM promotion_decisions"
                    " WHERE decision_id = :did"
                ),
                {"did": decision_id},
            ).fetchone()
        assert row.promoted == 0
        criteria = json.loads(row.criteria_met)
        assert criteria["min_days"] is False

    def test_criteria_met_stored_as_json(self, engine, ops) -> None:
        run_id = ops.register_challenger(engine, model_id="m1")
        criteria = {
            "min_days": True,
            "min_trades": False,
            "sharpe_margin": True,
            "max_dd_ratio": True,
        }
        decision_id = ops.log_promotion_decision(
            engine,
            challenger_run_id=run_id,
            champion_run_id=None,
            promoted=False,
            reason="min_trades",
            criteria_met=criteria,
        )
        with engine.connect() as conn:
            raw = conn.execute(
                text("SELECT criteria_met FROM promotion_decisions WHERE decision_id = :did"),
                {"did": decision_id},
            ).scalar()
        assert json.loads(raw) == criteria


class TestFullPromotionFlow:
    def test_register_evaluate_promote_log(self, engine, ops) -> None:
        from fx_ai_trading.services.promotion_gate import (
            NO_CHAMPION_STATS,
            ChallengerStats,
            PromotionGate,
        )

        # 1. Register challenger with qualifying stats
        stats = _paper_stats(paper_days=20, trade_count=150, sharpe=1.0, max_drawdown=0.04)
        run_id = ops.register_challenger(engine, model_id="ml_v2", paper_stats=stats)

        # 2. No champion → evaluate vs NO_CHAMPION_STATS
        challenger = ChallengerStats(
            model_id="ml_v2",
            training_run_id=run_id,
            **stats,
        )
        gate = PromotionGate()
        decision = gate.evaluate(challenger, NO_CHAMPION_STATS)
        assert decision.promoted is True

        # 3. Promote
        ops.promote(engine, run_id)

        # 4. Log audit
        ops.log_promotion_decision(
            engine,
            challenger_run_id=run_id,
            champion_run_id=None,
            promoted=decision.promoted,
            reason=decision.reason,
            criteria_met=decision.criteria,
        )

        # 5. Verify champion
        champion = ops.get_champion(engine)
        assert champion is not None
        assert champion["training_run_id"] == run_id

        # 6. Verify audit log
        with engine.connect() as conn:
            count = conn.execute(
                text("SELECT COUNT(*) FROM promotion_decisions WHERE promoted = 1")
            ).scalar()
        assert count == 1
