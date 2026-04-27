"""Unit tests: ExposureComputer (compute_exposure helper)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from fx_ai_trading.domain.state import OpenPositionInfo
from fx_ai_trading.services.exposure_computer import compute_exposure

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _pos(instrument: str, side: str, units: int = 10_000) -> OpenPositionInfo:
    return OpenPositionInfo(
        instrument=instrument,
        order_id="ord-1",
        units=units,
        avg_price=1.1,
        open_time_utc=_NOW,
        side=side,
    )


class TestEmptyPositions:
    def test_no_positions_returns_zero_exposure(self) -> None:
        e = compute_exposure([])
        assert e.concurrent_positions == 0
        assert e.per_currency == {}
        assert e.per_direction == {}
        assert e.total_risk_correlation_adjusted == 0.0


class TestConcurrentPositions:
    def test_single_position_concurrent_one(self) -> None:
        e = compute_exposure([_pos("EUR_USD", "long")])
        assert e.concurrent_positions == 1

    def test_three_positions_concurrent_three(self) -> None:
        positions = [
            _pos("EUR_USD", "long"),
            _pos("USD_JPY", "short"),
            _pos("GBP_USD", "long"),
        ]
        e = compute_exposure(positions)
        assert e.concurrent_positions == 3


class TestPerCurrency:
    def test_eur_usd_long_charges_both_currencies(self) -> None:
        e = compute_exposure([_pos("EUR_USD", "long")], risk_pct=1.0)
        assert e.per_currency["EUR"] == pytest.approx(1.0)
        assert e.per_currency["USD"] == pytest.approx(1.0)

    def test_two_eur_positions_double_eur_exposure(self) -> None:
        positions = [_pos("EUR_USD", "long"), _pos("EUR_GBP", "long")]
        e = compute_exposure(positions, risk_pct=1.0)
        assert e.per_currency["EUR"] == pytest.approx(2.0)
        assert e.per_currency["USD"] == pytest.approx(1.0)
        assert e.per_currency["GBP"] == pytest.approx(1.0)

    def test_usd_jpy_charges_usd_and_jpy(self) -> None:
        e = compute_exposure([_pos("USD_JPY", "short")], risk_pct=2.0)
        assert e.per_currency["USD"] == pytest.approx(2.0)
        assert e.per_currency["JPY"] == pytest.approx(2.0)

    def test_invalid_instrument_skipped(self) -> None:
        bad = OpenPositionInfo(
            instrument="EURUSD",  # no underscore
            order_id="o1",
            units=1000,
            avg_price=1.1,
            open_time_utc=_NOW,
            side="long",
        )
        e = compute_exposure([bad], risk_pct=1.0)
        assert e.per_currency == {}
        assert e.concurrent_positions == 1


class TestPerDirection:
    def test_long_eur_usd_long_in_per_direction(self) -> None:
        e = compute_exposure([_pos("EUR_USD", "long")], risk_pct=1.0)
        assert e.per_direction["EUR"]["long"] == pytest.approx(1.0)
        assert e.per_direction["USD"]["long"] == pytest.approx(1.0)
        assert e.per_direction["EUR"].get("short", 0.0) == 0.0

    def test_mixed_sides_tracked_separately(self) -> None:
        positions = [
            _pos("EUR_USD", "long"),
            _pos("EUR_GBP", "short"),
        ]
        e = compute_exposure(positions, risk_pct=1.0)
        assert e.per_direction["EUR"]["long"] == pytest.approx(1.0)
        assert e.per_direction["EUR"]["short"] == pytest.approx(1.0)

    def test_two_long_eur_positions_accumulate(self) -> None:
        positions = [_pos("EUR_USD", "long"), _pos("EUR_JPY", "long")]
        e = compute_exposure(positions, risk_pct=1.5)
        assert e.per_direction["EUR"]["long"] == pytest.approx(3.0)


class TestTotalRisk:
    def test_total_risk_always_zero_mvp(self) -> None:
        positions = [_pos("EUR_USD", "long"), _pos("USD_JPY", "short")]
        e = compute_exposure(positions, risk_pct=5.0)
        assert e.total_risk_correlation_adjusted == 0.0


class TestRiskManagerIntegration:
    def test_accept_passes_when_under_thresholds(self) -> None:
        from fx_ai_trading.services.risk_manager import RiskManagerService

        rm = RiskManagerService(
            max_concurrent_positions=5,
            max_single_currency_exposure_pct=30.0,
        )
        positions = [_pos("EUR_USD", "long")]
        exposure = compute_exposure(positions, risk_pct=1.0)
        result = rm.accept(None, exposure)
        assert result.accepted is True

    def test_accept_rejects_on_concurrent_limit(self) -> None:
        from fx_ai_trading.services.risk_manager import RiskManagerService

        rm = RiskManagerService(max_concurrent_positions=2)
        positions = [_pos("EUR_USD", "long"), _pos("USD_JPY", "short")]
        exposure = compute_exposure(positions, risk_pct=1.0)
        result = rm.accept(None, exposure)
        assert result.accepted is False
        assert result.reject_reason == "risk.concurrent_limit"

    def test_accept_rejects_on_single_currency_cap(self) -> None:
        from fx_ai_trading.services.risk_manager import RiskManagerService

        rm = RiskManagerService(
            max_concurrent_positions=10,
            max_single_currency_exposure_pct=5.0,
        )
        # 6 EUR positions × 1% = 6% → exceeds 5% cap
        positions = [
            _pos("EUR_USD", "long")
            for _ in range(6)  # noqa: F601
        ]
        exposure = compute_exposure(positions, risk_pct=1.0)
        result = rm.accept(None, exposure)
        assert result.accepted is False
        assert result.reject_reason == "risk.single_currency_exposure"
