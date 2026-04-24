"""Unit tests: ATRRegimeClassifier (Phase 9.7)."""

from __future__ import annotations

import pytest

from fx_ai_trading.services.regime.atr_regime import (
    REGIME_HIGH_VOL,
    REGIME_RANGE,
    REGIME_TREND,
    ATRRegimeClassifier,
    _compute_atr,
    _raw_regime,
)


def _make_candles(n: int, high: float = 1.01, low: float = 0.99, close: float = 1.0) -> list[dict]:
    """Return *n* synthetic flat OHLC candles."""
    return [{"open": close, "high": high, "low": low, "close": close} for _ in range(n)]


def _make_candles_with_spike(n_normal: int, spike_factor: float = 4.0) -> list[dict]:
    """Normal candles + a single spike candle at the end."""
    candles = _make_candles(n_normal)
    spike_range = (1.01 - 0.99) * spike_factor
    mid = 1.0
    candles.append(
        {"open": mid, "high": mid + spike_range / 2, "low": mid - spike_range / 2, "close": mid}
    )
    return candles


# ---------------------------------------------------------------------------
# _compute_atr
# ---------------------------------------------------------------------------


class TestComputeATR:
    def test_too_few_candles_returns_empty(self) -> None:
        candles = _make_candles(3)
        result = _compute_atr(candles, period=5)
        assert result == []

    def test_exact_minimum_returns_one_value(self) -> None:
        candles = _make_candles(5)  # period=4 → needs 5 candles
        result = _compute_atr(candles, period=4)
        assert len(result) == 1
        assert result[0] > 0.0

    def test_length_matches_candles_minus_period(self) -> None:
        candles = _make_candles(20)
        result = _compute_atr(candles, period=14)
        assert len(result) == 20 - 14

    def test_constant_candles_produce_constant_atr(self) -> None:
        candles = _make_candles(20)
        result = _compute_atr(candles, period=14)
        assert all(abs(v - result[0]) < 1e-10 for v in result)


# ---------------------------------------------------------------------------
# _raw_regime (no hysteresis)
# ---------------------------------------------------------------------------


class TestRawRegime:
    def test_insufficient_candles_returns_none(self) -> None:
        candles = _make_candles(14)  # need >= period + 2 = 16
        result = _raw_regime(candles, 14, 1.5, 0.7)
        assert result is None

    def test_flat_market_returns_trend(self) -> None:
        # 30 identical candles → current ATR == baseline ATR → ratio 1.0 → trend
        candles = _make_candles(30)
        result = _raw_regime(candles, 14, 1.5, 0.7)
        assert result == REGIME_TREND

    def test_high_vol_spike_detected(self) -> None:
        # Many normal candles then one giant candle → ratio >> 1.5
        candles = _make_candles_with_spike(50, spike_factor=10.0)
        result = _raw_regime(candles, 14, 1.5, 0.7)
        assert result == REGIME_HIGH_VOL

    def test_range_regime_when_all_tiny(self) -> None:
        # Flat candles where range shrinks at the end: simulate by large baseline
        # Build: first 30 wide candles, then 14 tiny candles at the end
        wide = [{"open": 1.0, "high": 1.05, "low": 0.95, "close": 1.0} for _ in range(30)]
        tiny = [{"open": 1.0, "high": 1.001, "low": 0.999, "close": 1.0} for _ in range(14)]
        candles = wide + tiny
        result = _raw_regime(candles, 14, 1.5, 0.7)
        assert result == REGIME_RANGE


# ---------------------------------------------------------------------------
# ATRRegimeClassifier (with hysteresis)
# ---------------------------------------------------------------------------


class TestATRRegimeClassifier:
    def test_returns_none_before_enough_data(self) -> None:
        clf = ATRRegimeClassifier(atr_period=14, hysteresis_periods=3)
        candles = _make_candles(10)
        regime = clf.update(candles)
        assert regime is None
        assert clf.regime is None

    def test_returns_none_before_hysteresis_threshold(self) -> None:
        clf = ATRRegimeClassifier(atr_period=14, hysteresis_periods=3)
        candles = _make_candles(30)
        # First two updates don't confirm yet
        clf.update(candles)
        clf.update(candles)
        assert clf.regime is None

    def test_regime_confirmed_after_hysteresis(self) -> None:
        clf = ATRRegimeClassifier(atr_period=14, hysteresis_periods=3)
        candles = _make_candles(30)
        for _ in range(3):
            clf.update(candles)
        assert clf.regime == REGIME_TREND

    def test_hysteresis_prevents_single_spike_switch(self) -> None:
        clf = ATRRegimeClassifier(atr_period=14, hysteresis_periods=3)
        # Establish trend regime
        normal = _make_candles(30)
        for _ in range(3):
            clf.update(normal)
        assert clf.regime == REGIME_TREND

        # One spike update → should not switch yet
        spiked = _make_candles_with_spike(50, spike_factor=10.0)
        clf.update(spiked)
        assert clf.regime == REGIME_TREND  # still trend (hysteresis blocks switch)

    def test_high_vol_confirmed_after_hysteresis(self) -> None:
        clf = ATRRegimeClassifier(atr_period=14, hysteresis_periods=3)
        spiked = _make_candles_with_spike(50, spike_factor=10.0)
        for _ in range(3):
            clf.update(spiked)
        assert clf.regime == REGIME_HIGH_VOL

    def test_regime_property_equals_update_return(self) -> None:
        clf = ATRRegimeClassifier(atr_period=14, hysteresis_periods=3)
        candles = _make_candles(30)
        returned = None
        for _ in range(3):
            returned = clf.update(candles)
        assert returned == clf.regime

    def test_invalid_atr_period_raises(self) -> None:
        with pytest.raises(ValueError):
            ATRRegimeClassifier(atr_period=0)

    def test_invalid_hysteresis_raises(self) -> None:
        with pytest.raises(ValueError):
            ATRRegimeClassifier(hysteresis_periods=0)

    def test_hysteresis_one_confirms_immediately(self) -> None:
        clf = ATRRegimeClassifier(atr_period=14, hysteresis_periods=1)
        candles = _make_candles(30)
        regime = clf.update(candles)
        assert regime == REGIME_TREND
