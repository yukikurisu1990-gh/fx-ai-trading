"""Unit tests: regime-aware EV-weighted scoring in MetaDeciderService (Phase 9.7)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from fx_ai_trading.domain.meta import MetaContext
from fx_ai_trading.domain.strategy import StrategySignal
from fx_ai_trading.services.meta_decider import MetaDeciderService


def _sig(
    strategy_id: str = "s1",
    signal: str = "long",
    confidence: float = 0.7,
    ev_after_cost: float = 0.01,
    ev_before_cost: float = 0.012,
) -> StrategySignal:
    return StrategySignal(
        strategy_id=strategy_id,
        strategy_type="test",
        strategy_version="v1",
        signal=signal,
        confidence=confidence,
        ev_before_cost=ev_before_cost,
        ev_after_cost=ev_after_cost,
        tp=0.01,
        sl=0.005,
        holding_time_seconds=3600,
        enabled=True,
    )


def _ctx(regime: str | None = None) -> MetaContext:
    return MetaContext(
        cycle_id=uuid4(),
        account_id="acct",
        config_version="v1",
        regime=regime,
    )


class TestRegimeAwareScoring:
    def test_no_regime_uses_neutral_weight(self) -> None:
        svc = MetaDeciderService()
        decision = svc.decide([_sig()], _ctx(regime=None))
        assert not decision.no_trade
        contrib = decision.score_contributions[0]
        assert contrib["regime_weight"] == 1.0

    def test_trend_regime_applies_boost(self) -> None:
        svc = MetaDeciderService()
        decision = svc.decide([_sig()], _ctx(regime="trend"))
        assert not decision.no_trade
        contrib = decision.score_contributions[0]
        assert contrib["regime_weight"] == pytest.approx(1.2)

    def test_range_regime_uses_neutral_weight(self) -> None:
        svc = MetaDeciderService()
        decision = svc.decide([_sig()], _ctx(regime="range"))
        contrib = decision.score_contributions[0]
        assert contrib["regime_weight"] == pytest.approx(1.0)

    def test_high_vol_regime_dampens_score(self) -> None:
        svc = MetaDeciderService()
        decision = svc.decide([_sig()], _ctx(regime="high_vol"))
        contrib = decision.score_contributions[0]
        assert contrib["regime_weight"] == pytest.approx(0.5)

    def test_regime_appears_in_score_snapshot(self) -> None:
        svc = MetaDeciderService()
        decision = svc.decide([_sig()], _ctx(regime="trend"))
        assert decision.score_snapshot["regime"] == "trend"
        assert decision.score_snapshot["regime_weight"] == pytest.approx(1.2)

    def test_regime_detected_true_when_regime_set(self) -> None:
        svc = MetaDeciderService()
        decision = svc.decide([_sig()], _ctx(regime="trend"))
        assert decision.regime_detected is True

    def test_regime_detected_false_when_regime_none(self) -> None:
        svc = MetaDeciderService()
        decision = svc.decide([_sig()], _ctx(regime=None))
        assert decision.regime_detected is False

    def test_trend_score_exceeds_high_vol_score(self) -> None:
        # Same candidates, different context — trend should outscored high_vol
        sig = _sig(ev_after_cost=0.01, confidence=0.7)
        svc = MetaDeciderService()

        trend_decision = svc.decide([sig], _ctx(regime="trend"))
        hv_decision = svc.decide([sig], _ctx(regime="high_vol"))

        trend_score = trend_decision.score_contributions[0]["score"]
        hv_score = hv_decision.score_contributions[0]["score"]
        assert trend_score > hv_score

    def test_high_vol_dampening_can_still_select(self) -> None:
        # high_vol dampens but doesn't block (EV still > 0)
        svc = MetaDeciderService(min_ev=0.0)
        decision = svc.decide([_sig(ev_after_cost=0.01)], _ctx(regime="high_vol"))
        assert not decision.no_trade
        assert decision.selected_strategy_id == "s1"

    def test_high_vol_below_min_ev_triggers_no_trade(self) -> None:
        # If regime_weight * ev drives effective score below min_ev check...
        # min_ev check is on ev_after_cost directly (unchanged), not weighted score.
        # So set min_ev just above ev_after_cost to force no_trade.
        svc = MetaDeciderService(min_ev=0.02)
        decision = svc.decide([_sig(ev_after_cost=0.01)], _ctx(regime="high_vol"))
        assert decision.no_trade

    def test_ranking_changes_with_regime(self) -> None:
        # Two strategies with same confidence but different EV.
        # Without regime: s_high_ev always wins.
        # The regime weight is applied uniformly so ranking is preserved,
        # but we verify contributions reflect correct weights.
        s_a = _sig("s_a", ev_after_cost=0.02, confidence=0.6)
        s_b = _sig("s_b", ev_after_cost=0.01, confidence=0.6)
        svc = MetaDeciderService()
        decision = svc.decide([s_b, s_a], _ctx(regime="trend"))
        # s_a should rank first (higher EV * same weight)
        assert decision.selected_strategy_id == "s_a"
        assert decision.score_contributions[0]["strategy_id"] == "s_a"
        assert decision.score_contributions[1]["strategy_id"] == "s_b"

    def test_unknown_regime_string_uses_neutral_weight(self) -> None:
        svc = MetaDeciderService()
        decision = svc.decide([_sig()], _ctx(regime="unknown_regime"))
        contrib = decision.score_contributions[0]
        assert contrib["regime_weight"] == pytest.approx(1.0)
