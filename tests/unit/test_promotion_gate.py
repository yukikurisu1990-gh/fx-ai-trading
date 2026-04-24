"""Unit tests: PromotionGate (Phase 9.8) — pure, no DB."""

from __future__ import annotations

import math

import pytest

from fx_ai_trading.services.promotion_gate import (
    NO_CHAMPION_STATS,
    ChallengerStats,
    ChampionStats,
    PromotionCriteria,
    PromotionGate,
)


def _challenger(
    paper_days: int = 20,
    trade_count: int = 150,
    sharpe: float = 1.0,
    max_drawdown: float = 0.05,
    model_id: str = "m1",
    training_run_id: str = "run1",
) -> ChallengerStats:
    return ChallengerStats(
        model_id=model_id,
        training_run_id=training_run_id,
        paper_days=paper_days,
        trade_count=trade_count,
        sharpe=sharpe,
        max_drawdown=max_drawdown,
    )


def _champion(
    sharpe: float = 0.7,
    max_drawdown: float = 0.06,
    model_id: str = "champ",
    training_run_id: str = "run0",
) -> ChampionStats:
    return ChampionStats(
        model_id=model_id,
        training_run_id=training_run_id,
        sharpe=sharpe,
        max_drawdown=max_drawdown,
    )


class TestPromotionGate:
    def test_all_criteria_met_promotes(self) -> None:
        gate = PromotionGate()
        # challenger: 20 days, 150 trades, sharpe 1.0, dd 0.05
        # champion: sharpe 0.7, dd 0.06 → required sharpe ≥ 0.9; dd ≤ 0.072
        decision = gate.evaluate(_challenger(), _champion())
        assert decision.promoted is True
        assert decision.reason == "all_criteria_met"

    def test_insufficient_days_blocks(self) -> None:
        gate = PromotionGate()
        decision = gate.evaluate(_challenger(paper_days=10), _champion())
        assert decision.promoted is False
        assert "min_days" in decision.reason

    def test_insufficient_trades_blocks(self) -> None:
        gate = PromotionGate()
        decision = gate.evaluate(_challenger(trade_count=50), _champion())
        assert decision.promoted is False
        assert "min_trades" in decision.reason

    def test_sharpe_below_threshold_blocks(self) -> None:
        gate = PromotionGate()
        # champion sharpe 0.7, required ≥ 0.9; challenger 0.8 fails
        decision = gate.evaluate(_challenger(sharpe=0.8), _champion(sharpe=0.7))
        assert decision.promoted is False
        assert "sharpe_margin" in decision.reason

    def test_max_dd_exceeded_blocks(self) -> None:
        gate = PromotionGate()
        # champion dd 0.05, budget = 0.05 * 1.2 = 0.06; challenger dd 0.08 fails
        decision = gate.evaluate(_challenger(max_drawdown=0.08), _champion(max_drawdown=0.05))
        assert decision.promoted is False
        assert "max_dd_ratio" in decision.reason

    def test_multiple_failures_reason_contains_all(self) -> None:
        gate = PromotionGate()
        decision = gate.evaluate(
            _challenger(paper_days=5, trade_count=10, sharpe=0.0, max_drawdown=0.5),
            _champion(),
        )
        assert decision.promoted is False
        for key in ("min_days", "min_trades", "sharpe_margin", "max_dd_ratio"):
            assert key in decision.reason

    def test_criteria_dict_contains_all_keys(self) -> None:
        gate = PromotionGate()
        decision = gate.evaluate(_challenger(), _champion())
        assert set(decision.criteria.keys()) == {
            "min_days",
            "min_trades",
            "sharpe_margin",
            "max_dd_ratio",
        }

    def test_challenger_and_champion_stats_in_decision(self) -> None:
        gate = PromotionGate()
        chal = _challenger()
        champ = _champion()
        decision = gate.evaluate(chal, champ)
        assert decision.challenger_stats is chal
        assert decision.champion_stats is champ

    def test_no_champion_uses_zero_sharpe_baseline(self) -> None:
        gate = PromotionGate()
        # sharpe_margin = 0.2; challenger needs sharpe ≥ 0.0 + 0.2 = 0.2
        decision = gate.evaluate(_challenger(sharpe=0.5), NO_CHAMPION_STATS)
        assert decision.promoted is True

    def test_no_champion_dd_check_always_passes(self) -> None:
        gate = PromotionGate()
        # NO_CHAMPION_STATS.max_drawdown = inf → dd budget = inf → always passes
        decision = gate.evaluate(_challenger(max_drawdown=999.0), NO_CHAMPION_STATS)
        assert decision.criteria["max_dd_ratio"] is True

    def test_custom_criteria(self) -> None:
        criteria = PromotionCriteria(min_days=5, min_trades=20, sharpe_margin=0.0, max_dd_ratio=2.0)
        gate = PromotionGate(criteria)
        decision = gate.evaluate(_challenger(paper_days=5, trade_count=20), _champion())
        assert decision.promoted is True

    def test_exact_boundary_promotes(self) -> None:
        # All criteria exactly at threshold — should promote
        gate = PromotionGate()
        # champion: sharpe=0.7, dd=0.06 → required: sharpe≥0.9, dd≤0.072
        decision = gate.evaluate(
            _challenger(paper_days=14, trade_count=100, sharpe=0.9, max_drawdown=0.072),
            _champion(sharpe=0.7, max_drawdown=0.06),
        )
        assert decision.promoted is True

    def test_dd_ratio_exact_boundary_promotes(self) -> None:
        # dd_budget = 0.05 * 1.2 = 0.06; challenger dd = 0.06 → passes (<=)
        gate = PromotionGate()
        decision = gate.evaluate(
            _challenger(max_drawdown=0.06),
            _champion(max_drawdown=0.05),
        )
        assert decision.criteria["max_dd_ratio"] is True

    def test_default_criteria_values(self) -> None:
        criteria = PromotionCriteria()
        assert criteria.min_days == 14
        assert criteria.min_trades == 100
        assert criteria.sharpe_margin == pytest.approx(0.2)
        assert criteria.max_dd_ratio == pytest.approx(1.2)

    def test_no_champion_stats_is_sentinel(self) -> None:
        assert NO_CHAMPION_STATS.training_run_id is None
        assert NO_CHAMPION_STATS.sharpe == 0.0
        assert math.isinf(NO_CHAMPION_STATS.max_drawdown)
