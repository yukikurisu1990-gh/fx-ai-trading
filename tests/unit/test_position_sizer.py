"""Unit tests: PositionSizerService minimum-lot boundary (D3 §2.5.1 / M10).

Invariants:
  - size_units is always a multiple of min_trade_units, or 0.
  - sl_pips <= 0 → SizeResult(0, 'InvalidSL').
  - raw_units < min_trade_units → SizeResult(0, 'SizeUnderMin').
  - No DB, no clock, no randomness.
"""

from __future__ import annotations

import pytest

from fx_ai_trading.domain.risk import Instrument
from fx_ai_trading.services.position_sizer import PositionSizerService


def _instrument(min_trade_units: int = 1000) -> Instrument:
    return Instrument(
        instrument="EUR_USD",
        base_currency="EUR",
        quote_currency="USD",
        pip_location=-4,
        min_trade_units=min_trade_units,
    )


def _sizer(risk_pct: float = 1.0) -> PositionSizerService:
    return PositionSizerService(risk_pct=risk_pct)


class TestPositionSizerInvalidInputs:
    def test_zero_sl_returns_invalid_sl(self) -> None:
        sizer = _sizer()
        result = sizer.size(10_000.0, 1.0, 0.0, _instrument())
        assert result.size_units == 0
        assert result.reason == "InvalidSL"

    def test_negative_sl_returns_invalid_sl(self) -> None:
        sizer = _sizer()
        result = sizer.size(10_000.0, 1.0, -0.001, _instrument())
        assert result.size_units == 0
        assert result.reason == "InvalidSL"

    def test_invalid_risk_pct_raises(self) -> None:
        with pytest.raises(ValueError):
            PositionSizerService(risk_pct=0.0)

    def test_risk_pct_over_100_raises(self) -> None:
        with pytest.raises(ValueError):
            PositionSizerService(risk_pct=101.0)

    def test_zero_risk_pct_in_size_returns_invalid(self) -> None:
        """Passing risk_pct=0 to size() must return InvalidRiskPct (not silently use default)."""
        sizer = _sizer(risk_pct=1.0)
        result = sizer.size(100_000.0, 0.0, 0.001, _instrument())
        assert result.size_units == 0
        assert result.reason == "InvalidRiskPct"

    def test_negative_risk_pct_in_size_returns_invalid(self) -> None:
        """Passing negative risk_pct to size() must return InvalidRiskPct."""
        sizer = _sizer(risk_pct=1.0)
        result = sizer.size(100_000.0, -1.0, 0.001, _instrument())
        assert result.size_units == 0
        assert result.reason == "InvalidRiskPct"


class TestPositionSizerMinLotBoundary:
    def test_size_under_min_returns_zero(self) -> None:
        """Small account / large sl → raw_units < min_lot → SizeUnderMin."""
        sizer = _sizer()
        # risk=1% of 100 = 1.0; sl_pips=0.01 → raw=100; min_lot=1000 → under
        result = sizer.size(100.0, 1.0, 0.01, _instrument(min_trade_units=1000))
        assert result.size_units == 0
        assert result.reason == "SizeUnderMin"

    def test_size_exactly_at_min_lot(self) -> None:
        """Exactly one min_lot → size=min_lot."""
        sizer = _sizer()
        # risk=1% of 100_000 = 1000; sl_pips=1.0 → raw=1000; min_lot=1000 → 1000
        result = sizer.size(100_000.0, 1.0, 1.0, _instrument(min_trade_units=1000))
        assert result.size_units == 1000
        assert result.reason is None

    def test_size_is_multiple_of_min_lot(self) -> None:
        """raw_units = 2500 with min_lot=1000 → floor(2.5)×1000 = 2000."""
        sizer = _sizer()
        # risk=1% of 250_000 = 2500; sl_pips=1.0 → raw=2500; min_lot=1000 → 2000
        result = sizer.size(250_000.0, 1.0, 1.0, _instrument(min_trade_units=1000))
        assert result.size_units == 2000
        assert result.size_units % 1000 == 0

    def test_size_always_multiple_of_min_lot(self) -> None:
        """Any result must satisfy size_units % min_lot == 0 (or size_units==0)."""
        sizer = _sizer()
        instrument = _instrument(min_trade_units=500)
        for balance in (1_000.0, 10_000.0, 100_000.0, 500_000.0):
            result = sizer.size(balance, 1.0, 0.5, instrument)
            if result.size_units > 0:
                assert result.size_units % 500 == 0, (
                    f"balance={balance}: size={result.size_units} not multiple of 500"
                )

    def test_min_trade_units_1_allows_any_positive(self) -> None:
        """With min_trade_units=1, any risk > 0 produces a valid size."""
        sizer = _sizer()
        result = sizer.size(1_000.0, 1.0, 0.001, _instrument(min_trade_units=1))
        assert result.size_units > 0
        assert result.reason is None

    def test_large_balance_large_size(self) -> None:
        """Large balance → large size, still a multiple of min_lot."""
        sizer = _sizer()
        result = sizer.size(10_000_000.0, 2.0, 0.01, _instrument(min_trade_units=1000))
        assert result.size_units > 0
        assert result.size_units % 1000 == 0


class TestPositionSizerRiskPct:
    def test_higher_risk_pct_gives_larger_size(self) -> None:
        """2% risk produces larger size than 1% risk."""
        instrument = _instrument(min_trade_units=1000)
        s1 = _sizer(risk_pct=1.0).size(100_000.0, 1.0, 0.5, instrument)
        s2 = _sizer(risk_pct=2.0).size(100_000.0, 2.0, 0.5, instrument)
        assert s2.size_units >= s1.size_units

    def test_deterministic(self) -> None:
        """Same inputs always produce the same result."""
        sizer = _sizer()
        instrument = _instrument()
        r1 = sizer.size(50_000.0, 1.5, 0.5, instrument)
        r2 = sizer.size(50_000.0, 1.5, 0.5, instrument)
        assert r1 == r2
