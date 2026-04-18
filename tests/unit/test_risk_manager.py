"""Unit tests: RiskManagerService 4-constraint gating (D3 §2.5.2 / M10).

Invariants:
  - 4 constraints evaluated in order C1 → C2 → C3 → C4.
  - First violation causes immediate Reject with the corresponding reason code.
  - accept=True → exposure_after has concurrent_positions + 1.
  - accept() never raises.
"""

from __future__ import annotations

from fx_ai_trading.domain.risk import Exposure
from fx_ai_trading.services.risk_manager import RiskManagerService


def _clean_exposure(concurrent: int = 0) -> Exposure:
    return Exposure(
        per_currency={},
        per_direction={},
        total_risk_correlation_adjusted=0.0,
        concurrent_positions=concurrent,
    )


def _mgr(**kwargs) -> RiskManagerService:
    return RiskManagerService(**kwargs)


class TestRiskManagerC1Concurrent:
    def test_accept_when_below_limit(self) -> None:
        mgr = _mgr(max_concurrent_positions=5)
        result = mgr.accept(None, _clean_exposure(concurrent=4))
        assert result.accepted is True

    def test_reject_at_limit(self) -> None:
        mgr = _mgr(max_concurrent_positions=5)
        result = mgr.accept(None, _clean_exposure(concurrent=5))
        assert result.accepted is False
        assert result.reject_reason == "risk.concurrent_limit"

    def test_reject_above_limit(self) -> None:
        mgr = _mgr(max_concurrent_positions=3)
        result = mgr.accept(None, _clean_exposure(concurrent=10))
        assert result.reject_reason == "risk.concurrent_limit"

    def test_accept_zero_positions(self) -> None:
        mgr = _mgr(max_concurrent_positions=5)
        result = mgr.accept(None, _clean_exposure(concurrent=0))
        assert result.accepted is True

    def test_exposure_after_incremented_on_accept(self) -> None:
        mgr = _mgr(max_concurrent_positions=5)
        result = mgr.accept(None, _clean_exposure(concurrent=2))
        assert result.accepted is True
        assert result.exposure_after is not None
        assert result.exposure_after.concurrent_positions == 3


class TestRiskManagerC2SingleCurrency:
    def test_reject_when_currency_at_cap(self) -> None:
        mgr = _mgr(max_single_currency_exposure_pct=30.0)
        exposure = Exposure(
            per_currency={"EUR": 30.0},
            per_direction={},
            total_risk_correlation_adjusted=0.0,
            concurrent_positions=0,
        )
        result = mgr.accept(None, exposure)
        assert result.accepted is False
        assert result.reject_reason == "risk.single_currency_exposure"

    def test_accept_when_currency_below_cap(self) -> None:
        mgr = _mgr(max_single_currency_exposure_pct=30.0)
        exposure = Exposure(
            per_currency={"EUR": 29.9},
            per_direction={},
            total_risk_correlation_adjusted=0.0,
            concurrent_positions=0,
        )
        result = mgr.accept(None, exposure)
        assert result.accepted is True

    def test_c1_fires_before_c2(self) -> None:
        """C1 violation takes precedence over C2."""
        mgr = _mgr(max_concurrent_positions=1, max_single_currency_exposure_pct=10.0)
        exposure = Exposure(
            per_currency={"EUR": 50.0},
            per_direction={},
            total_risk_correlation_adjusted=0.0,
            concurrent_positions=1,
        )
        result = mgr.accept(None, exposure)
        assert result.reject_reason == "risk.concurrent_limit"


class TestRiskManagerC3NetDirectional:
    def test_reject_when_direction_at_cap(self) -> None:
        mgr = _mgr(max_net_directional_exposure_per_currency_pct=40.0)
        exposure = Exposure(
            per_currency={},
            per_direction={"EUR": {"long": 40.0}},
            total_risk_correlation_adjusted=0.0,
            concurrent_positions=0,
        )
        result = mgr.accept(None, exposure)
        assert result.accepted is False
        assert result.reject_reason == "risk.net_directional_exposure"

    def test_accept_when_direction_below_cap(self) -> None:
        mgr = _mgr(max_net_directional_exposure_per_currency_pct=40.0)
        exposure = Exposure(
            per_currency={},
            per_direction={"EUR": {"long": 39.9}},
            total_risk_correlation_adjusted=0.0,
            concurrent_positions=0,
        )
        result = mgr.accept(None, exposure)
        assert result.accepted is True

    def test_c2_fires_before_c3(self) -> None:
        """C2 violation takes precedence over C3."""
        mgr = _mgr(
            max_single_currency_exposure_pct=30.0,
            max_net_directional_exposure_per_currency_pct=40.0,
        )
        exposure = Exposure(
            per_currency={"EUR": 30.0},
            per_direction={"EUR": {"long": 50.0}},
            total_risk_correlation_adjusted=0.0,
            concurrent_positions=0,
        )
        result = mgr.accept(None, exposure)
        assert result.reject_reason == "risk.single_currency_exposure"


class TestRiskManagerC4TotalRisk:
    def test_reject_when_total_risk_at_cap(self) -> None:
        mgr = _mgr(total_risk_cap_pct=10.0)
        exposure = Exposure(
            per_currency={},
            per_direction={},
            total_risk_correlation_adjusted=10.0,
            concurrent_positions=0,
        )
        result = mgr.accept(None, exposure)
        assert result.accepted is False
        assert result.reject_reason == "risk.total_risk"

    def test_accept_when_total_risk_below_cap(self) -> None:
        mgr = _mgr(total_risk_cap_pct=10.0)
        exposure = Exposure(
            per_currency={},
            per_direction={},
            total_risk_correlation_adjusted=9.99,
            concurrent_positions=0,
        )
        result = mgr.accept(None, exposure)
        assert result.accepted is True

    def test_c3_fires_before_c4(self) -> None:
        """C3 violation takes precedence over C4."""
        mgr = _mgr(
            max_net_directional_exposure_per_currency_pct=40.0,
            total_risk_cap_pct=10.0,
        )
        exposure = Exposure(
            per_currency={},
            per_direction={"USD": {"short": 50.0}},
            total_risk_correlation_adjusted=15.0,
            concurrent_positions=0,
        )
        result = mgr.accept(None, exposure)
        assert result.reject_reason == "risk.net_directional_exposure"

    def test_all_constraints_pass_returns_accepted(self) -> None:
        mgr = _mgr(
            max_concurrent_positions=5,
            max_single_currency_exposure_pct=30.0,
            max_net_directional_exposure_per_currency_pct=40.0,
            total_risk_cap_pct=10.0,
        )
        exposure = Exposure(
            per_currency={"EUR": 10.0},
            per_direction={"EUR": {"long": 10.0}},
            total_risk_correlation_adjusted=2.0,
            concurrent_positions=2,
        )
        result = mgr.accept(None, exposure)
        assert result.accepted is True
        assert result.reject_reason is None
        assert result.exposure_after is not None
        assert result.exposure_after.concurrent_positions == 3
