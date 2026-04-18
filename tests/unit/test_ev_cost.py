"""Unit tests: EVEstimatorService and CostModelService (D3 §2.4.2-3 / M9).

Invariants:
  - EVEstimatorService: no_trade → value=0.0, CI=(0.0, 0.0)
  - EVEstimatorService: value = p_win*tp - (1-p_win)*sl - cost.total
  - EVEstimatorService: CI = ±20% of |value|
  - CostModelService: total = 1.5 × spread
  - CostModelService: known instruments use table spread; unknown → default
"""

from __future__ import annotations

from fx_ai_trading.domain.ev import Cost
from fx_ai_trading.domain.strategy import StrategySignal
from fx_ai_trading.services.cost_model import _DEFAULT_SPREAD, CostModelService
from fx_ai_trading.services.ev_estimator import EVEstimatorService


def _make_signal(
    signal: str = "long",
    confidence: float = 0.6,
    tp: float = 0.01,
    sl: float = 0.005,
) -> StrategySignal:
    return StrategySignal(
        strategy_id="test_strat",
        strategy_type="test",
        strategy_version="v1",
        signal=signal,
        confidence=confidence,
        ev_before_cost=0.0,
        ev_after_cost=0.0,
        tp=tp,
        sl=sl,
        holding_time_seconds=3600,
        enabled=True,
    )


def _zero_cost() -> Cost:
    return Cost(spread=0.0, slippage_expected=0.0, commission=0.0, swap_rate_per_day=0.0, total=0.0)


class TestEVEstimatorService:
    def test_no_trade_returns_zero_value(self) -> None:
        svc = EVEstimatorService()
        est = svc.estimate(_make_signal(signal="no_trade"), _zero_cost())
        assert est.value == 0.0

    def test_no_trade_returns_zero_ci(self) -> None:
        svc = EVEstimatorService()
        est = svc.estimate(_make_signal(signal="no_trade"), _zero_cost())
        assert est.confidence_interval == (0.0, 0.0)

    def test_formula_correctness_long(self) -> None:
        """value = p_win*tp - (1-p_win)*sl - cost.total."""
        svc = EVEstimatorService()
        sig = _make_signal(signal="long", confidence=0.6, tp=0.01, sl=0.005)
        cost = Cost(
            spread=0.0, slippage_expected=0.0, commission=0.0, swap_rate_per_day=0.0, total=0.001
        )
        est = svc.estimate(sig, cost)
        expected = round(0.6 * 0.01 - 0.4 * 0.005 - 0.001, 8)
        assert est.value == expected

    def test_ci_is_twenty_percent_of_abs_value(self) -> None:
        svc = EVEstimatorService()
        sig = _make_signal(signal="long", confidence=0.8, tp=0.01, sl=0.005)
        est = svc.estimate(sig, _zero_cost())
        ci_lo, ci_hi = est.confidence_interval
        half = abs(est.value) * 0.20
        assert abs(ci_lo - (est.value - half)) < 1e-9
        assert abs(ci_hi - (est.value + half)) < 1e-9

    def test_deterministic(self) -> None:
        svc = EVEstimatorService()
        sig = _make_signal()
        cost = _zero_cost()
        assert svc.estimate(sig, cost) == svc.estimate(sig, cost)

    def test_negative_ev_allowed(self) -> None:
        """Negative EV is valid — MetaDecider gates, not EVEstimator."""
        svc = EVEstimatorService()
        sig = _make_signal(signal="long", confidence=0.1, tp=0.001, sl=0.01)
        est = svc.estimate(sig, _zero_cost())
        assert est.value < 0.0

    def test_components_present_for_non_no_trade(self) -> None:
        svc = EVEstimatorService()
        est = svc.estimate(_make_signal(signal="short"), _zero_cost())
        assert "p_win" in est.components
        assert "avg_win" in est.components
        assert "avg_loss" in est.components
        assert "cost_total" in est.components


class TestCostModelService:
    def test_total_is_one_point_five_times_spread(self) -> None:
        """total = spread + 0.5*spread = 1.5 * spread (commission=swap=0)."""
        svc = CostModelService()
        cost = svc.compute("EUR_USD", None)
        assert abs(cost.total - cost.spread * 1.5) < 1e-10

    def test_known_instrument_uses_table_spread(self) -> None:
        svc = CostModelService()
        cost = svc.compute("EUR_USD", None)
        assert cost.spread == 0.00015

    def test_unknown_instrument_uses_default_spread(self) -> None:
        svc = CostModelService()
        cost = svc.compute("XYZ_ABC", None)
        assert cost.spread == _DEFAULT_SPREAD

    def test_commission_and_swap_are_zero(self) -> None:
        svc = CostModelService()
        cost = svc.compute("GBP_USD", None)
        assert cost.commission == 0.0
        assert cost.swap_rate_per_day == 0.0

    def test_slippage_is_half_spread(self) -> None:
        svc = CostModelService()
        cost = svc.compute("USD_JPY", None)
        assert abs(cost.slippage_expected - cost.spread * 0.5) < 1e-10

    def test_spread_override_applies(self) -> None:
        svc = CostModelService(spread_overrides={"EUR_USD": 0.0001})
        cost = svc.compute("EUR_USD", None)
        assert cost.spread == 0.0001

    def test_all_major_pairs_have_costs(self) -> None:
        svc = CostModelService()
        pairs = [
            "EUR_USD",
            "GBP_USD",
            "USD_JPY",
            "USD_CHF",
            "AUD_USD",
            "USD_CAD",
            "NZD_USD",
            "EUR_GBP",
            "EUR_JPY",
            "GBP_JPY",
        ]
        for pair in pairs:
            cost = svc.compute(pair, None)
            assert cost.total > 0.0, f"{pair} should have positive total cost"
