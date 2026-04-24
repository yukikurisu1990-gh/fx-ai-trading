"""Unit tests: Phase 9.4 TA feature computation (_rsi, _ema, _macd, _bollinger)."""

from __future__ import annotations

import pytest

from fx_ai_trading.services.feature_service import (
    _bollinger,
    _compute_features,
    _ema,
    _macd,
    _rsi,
)


def _candles(closes: list[float]) -> list[dict]:
    return [
        {"timestamp": i, "open": c, "high": c + 0.001, "low": c - 0.001, "close": c, "volume": 100}
        for i, c in enumerate(closes)
    ]


class TestEMA:
    def test_single_value_returns_itself(self) -> None:
        assert _ema([5.0], 5) == pytest.approx(5.0)

    def test_empty_returns_zero(self) -> None:
        assert _ema([], 5) == pytest.approx(0.0)

    def test_constant_series_returns_constant(self) -> None:
        assert _ema([2.0] * 20, 5) == pytest.approx(2.0)

    def test_ema_smooths_towards_recent_values(self) -> None:
        # Rising series: EMA should trail below latest close.
        closes = list(range(1, 30))
        ema = _ema([float(c) for c in closes], 12)
        assert ema < closes[-1]
        assert ema > closes[0]

    def test_longer_period_lags_more(self) -> None:
        closes = [float(i) for i in range(1, 30)]
        ema_fast = _ema(closes, 5)
        ema_slow = _ema(closes, 26)
        # Fast EMA is closer to latest value on uptrend.
        assert ema_fast > ema_slow


class TestRSI:
    def test_returns_50_on_no_change(self) -> None:
        rsi = _rsi([1.0] * 20, 14)
        assert rsi == pytest.approx(50.0)

    def test_returns_100_on_all_gains(self) -> None:
        # Monotonically rising series → avg_loss = 0 → RSI = 100.
        closes = [float(i) for i in range(1, 20)]
        rsi = _rsi(closes, 14)
        assert rsi == pytest.approx(100.0)

    def test_returns_0_on_all_losses(self) -> None:
        closes = [float(i) for i in range(20, 0, -1)]
        rsi = _rsi(closes, 14)
        assert rsi == pytest.approx(0.0)

    def test_bounded_0_to_100(self) -> None:
        import random

        random.seed(42)
        closes = [random.uniform(0.5, 2.0) for _ in range(50)]
        rsi = _rsi(closes, 14)
        assert 0.0 <= rsi <= 100.0

    def test_fewer_than_2_bars_returns_50(self) -> None:
        assert _rsi([], 14) == pytest.approx(50.0)
        assert _rsi([1.5], 14) == pytest.approx(50.0)

    def test_oversold_below_30(self) -> None:
        # Steadily declining series → RSI should be < 30.
        closes = [1.0 - 0.04 * i for i in range(25)]
        rsi = _rsi(closes, 14)
        assert rsi < 30.0

    def test_overbought_above_70(self) -> None:
        # Steadily rising series → RSI should be > 70.
        closes = [0.1 + 0.1 * i for i in range(25)]
        rsi = _rsi(closes, 14)
        assert rsi > 70.0


class TestMACD:
    def test_zero_on_constant_series(self) -> None:
        closes = [1.0] * 30
        macd_line, signal_line, histogram = _macd(closes, 12, 26, 9)
        assert macd_line == pytest.approx(0.0, abs=1e-10)
        assert signal_line == pytest.approx(0.0, abs=1e-10)
        assert histogram == pytest.approx(0.0, abs=1e-10)

    def test_returns_zeros_when_insufficient_bars(self) -> None:
        closes = [1.0] * 10  # < slow=26
        macd_line, signal_line, histogram = _macd(closes, 12, 26, 9)
        assert macd_line == 0.0
        assert signal_line == 0.0
        assert histogram == 0.0

    def test_rising_series_positive_macd(self) -> None:
        closes = [float(i) for i in range(1, 50)]
        macd_line, signal_line, histogram = _macd(closes, 12, 26, 9)
        # Fast EMA > Slow EMA on uptrend → MACD > 0.
        assert macd_line > 0.0

    def test_histogram_equals_macd_minus_signal(self) -> None:
        closes = [float(i) for i in range(1, 50)]
        macd_line, signal_line, histogram = _macd(closes, 12, 26, 9)
        assert histogram == pytest.approx(macd_line - signal_line, rel=1e-9)


class TestBollinger:
    def test_empty_returns_zeros(self) -> None:
        upper, middle, lower = _bollinger([], 20, 2.0)
        assert upper == 0.0
        assert middle == 0.0
        assert lower == 0.0

    def test_constant_series_zero_width(self) -> None:
        closes = [1.10] * 20
        upper, middle, lower = _bollinger(closes, 20, 2.0)
        assert middle == pytest.approx(1.10)
        assert upper == pytest.approx(1.10)
        assert lower == pytest.approx(1.10)

    def test_upper_above_lower(self) -> None:
        import random

        random.seed(7)
        closes = [1.0 + random.uniform(-0.01, 0.01) for _ in range(30)]
        upper, middle, lower = _bollinger(closes, 20, 2.0)
        assert upper > lower

    def test_middle_is_sma(self) -> None:
        closes = [float(i) for i in range(1, 21)]
        _, middle, _ = _bollinger(closes, 20, 2.0)
        expected_sma = sum(closes) / 20
        assert middle == pytest.approx(expected_sma)

    def test_num_std_scales_bands(self) -> None:
        closes = [1.0 + 0.01 * i for i in range(20)]
        _, _, lower_1 = _bollinger(closes, 20, 1.0)
        _, middle, lower_2 = _bollinger(closes, 20, 2.0)
        # 2σ band is twice as far from middle as 1σ band.
        assert (middle - lower_2) == pytest.approx(2 * (middle - lower_1), rel=1e-9)


class TestComputeFeaturesTAFields:
    def test_all_ta_keys_present_on_empty(self) -> None:
        result = _compute_features([])
        for key in (
            "rsi_14",
            "macd_line",
            "macd_signal",
            "macd_histogram",
            "bb_upper",
            "bb_middle",
            "bb_lower",
            "bb_pct_b",
            "bb_width",
            "ema_12",
            "ema_26",
        ):
            assert key in result, f"Missing key: {key}"

    def test_rsi_defaults_0_on_empty(self) -> None:
        assert _compute_features([])["rsi_14"] == pytest.approx(0.0)

    def test_bb_pct_b_defaults_0_on_empty(self) -> None:
        assert _compute_features([])["bb_pct_b"] == pytest.approx(0.0)

    def test_rsi_populated_on_sufficient_data(self) -> None:
        candles = _candles([float(i) for i in range(1, 40)])
        result = _compute_features(candles)
        assert 0.0 <= result["rsi_14"] <= 100.0

    def test_macd_populated_on_sufficient_data(self) -> None:
        candles = _candles([float(i) for i in range(1, 50)])
        result = _compute_features(candles)
        assert result["macd_line"] != 0.0 or result["macd_histogram"] == 0.0

    def test_feature_version_v2(self) -> None:
        from fx_ai_trading.services.feature_service import FEATURE_VERSION

        assert FEATURE_VERSION == "v2"
