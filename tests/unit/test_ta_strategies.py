"""Unit tests: RSIStrategy, MACDStrategy, BollingerStrategy (Phase 9.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext
from fx_ai_trading.services.strategies.bollinger import BollingerStrategy
from fx_ai_trading.services.strategies.macd import MACDStrategy
from fx_ai_trading.services.strategies.rsi import RSIStrategy

_CTX = StrategyContext(cycle_id=str(uuid4()), account_id="acc001", config_version="v1")


def _make_features(**kwargs: float) -> FeatureSet:
    defaults = {
        "atr_14": 0.001,
        "bb_lower": 1.09,
        "bb_middle": 1.10,
        "bb_pct_b": 0.5,
        "bb_upper": 1.11,
        "bb_width": 0.018,
        "ema_12": 1.10,
        "ema_26": 1.10,
        "last_close": 1.10,
        "macd_histogram": 0.0,
        "macd_line": 0.0,
        "macd_signal": 0.0,
        "rsi_14": 50.0,
        "sma_20": 1.10,
        "sma_50": 1.10,
    }
    defaults.update(kwargs)
    return FeatureSet(
        feature_version="v2",
        feature_hash="test",
        feature_stats=defaults,
        sampled_features=defaults,
        computed_at=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# RSIStrategy
# ---------------------------------------------------------------------------


class TestRSIStrategy:
    def test_oversold_emits_long(self) -> None:
        rsi = RSIStrategy("rsi_1")
        sig = rsi.evaluate("EUR_USD", _make_features(rsi_14=20.0), _CTX)
        assert sig.signal == "long"
        assert sig.confidence > 0.0

    def test_overbought_emits_short(self) -> None:
        rsi = RSIStrategy("rsi_1")
        sig = rsi.evaluate("EUR_USD", _make_features(rsi_14=80.0), _CTX)
        assert sig.signal == "short"
        assert sig.confidence > 0.0

    def test_neutral_emits_no_trade(self) -> None:
        rsi = RSIStrategy("rsi_1")
        sig = rsi.evaluate("EUR_USD", _make_features(rsi_14=50.0), _CTX)
        assert sig.signal == "no_trade"
        assert sig.confidence == 0.0

    def test_at_oversold_threshold_emits_long(self) -> None:
        rsi = RSIStrategy("rsi_1", oversold_threshold=30.0)
        sig = rsi.evaluate("EUR_USD", _make_features(rsi_14=30.0), _CTX)
        assert sig.signal == "long"

    def test_at_overbought_threshold_emits_short(self) -> None:
        rsi = RSIStrategy("rsi_1", overbought_threshold=70.0)
        sig = rsi.evaluate("EUR_USD", _make_features(rsi_14=70.0), _CTX)
        assert sig.signal == "short"

    def test_confidence_increases_deeper_in_zone(self) -> None:
        rsi = RSIStrategy("rsi_1")
        sig_shallow = rsi.evaluate("EUR_USD", _make_features(rsi_14=28.0), _CTX)
        sig_deep = rsi.evaluate("EUR_USD", _make_features(rsi_14=10.0), _CTX)
        assert sig_deep.confidence > sig_shallow.confidence

    def test_strategy_id_propagated(self) -> None:
        rsi = RSIStrategy("my_rsi")
        sig = rsi.evaluate("EUR_USD", _make_features(rsi_14=20.0), _CTX)
        assert sig.strategy_id == "my_rsi"

    def test_strategy_type(self) -> None:
        rsi = RSIStrategy("rsi_1")
        sig = rsi.evaluate("EUR_USD", _make_features(rsi_14=20.0), _CTX)
        assert sig.strategy_type == "rsi_reversion"

    def test_tp_sl_use_atr(self) -> None:
        rsi = RSIStrategy("rsi_1", tp_atr_multiplier=2.0, sl_atr_multiplier=1.0)
        sig = rsi.evaluate("EUR_USD", _make_features(rsi_14=20.0, atr_14=0.002), _CTX)
        assert sig.tp == pytest.approx(0.002 * 2.0)
        assert sig.sl == pytest.approx(0.002 * 1.0)

    def test_ev_zero_on_no_trade(self) -> None:
        rsi = RSIStrategy("rsi_1")
        sig = rsi.evaluate("EUR_USD", _make_features(rsi_14=50.0), _CTX)
        assert sig.ev_before_cost == 0.0
        assert sig.ev_after_cost == 0.0

    def test_custom_thresholds(self) -> None:
        rsi = RSIStrategy("rsi_1", oversold_threshold=40.0, overbought_threshold=60.0)
        assert rsi.evaluate("EUR_USD", _make_features(rsi_14=35.0), _CTX).signal == "long"
        assert rsi.evaluate("EUR_USD", _make_features(rsi_14=65.0), _CTX).signal == "short"
        assert rsi.evaluate("EUR_USD", _make_features(rsi_14=50.0), _CTX).signal == "no_trade"


# ---------------------------------------------------------------------------
# MACDStrategy
# ---------------------------------------------------------------------------


class TestMACDStrategy:
    def test_bullish_histogram_emits_long(self) -> None:
        macd = MACDStrategy("macd_1")
        sig = macd.evaluate(
            "EUR_USD",
            _make_features(macd_histogram=0.0002, macd_line=0.0005, macd_signal=0.0003),
            _CTX,
        )
        assert sig.signal == "long"
        assert sig.confidence > 0.0

    def test_bearish_histogram_emits_short(self) -> None:
        macd = MACDStrategy("macd_1")
        sig = macd.evaluate(
            "EUR_USD",
            _make_features(macd_histogram=-0.0002, macd_line=-0.0005, macd_signal=-0.0003),
            _CTX,
        )
        assert sig.signal == "short"

    def test_zero_histogram_emits_no_trade(self) -> None:
        macd = MACDStrategy("macd_1")
        sig = macd.evaluate(
            "EUR_USD",
            _make_features(macd_histogram=0.0, macd_line=0.0, macd_signal=0.0),
            _CTX,
        )
        assert sig.signal == "no_trade"

    def test_histogram_positive_but_line_below_signal_no_trade(self) -> None:
        """Both conditions must hold: histogram > 0 AND macd_line > signal_line."""
        macd = MACDStrategy("macd_1")
        sig = macd.evaluate(
            "EUR_USD",
            _make_features(macd_histogram=0.0002, macd_line=-0.0001, macd_signal=0.0003),
            _CTX,
        )
        assert sig.signal == "no_trade"

    def test_strategy_type(self) -> None:
        macd = MACDStrategy("macd_1")
        sig = macd.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.strategy_type == "macd_trend"

    def test_strategy_id_propagated(self) -> None:
        macd = MACDStrategy("my_macd")
        sig = macd.evaluate(
            "EUR_USD",
            _make_features(macd_histogram=0.001, macd_line=0.002, macd_signal=0.001),
            _CTX,
        )
        assert sig.strategy_id == "my_macd"

    def test_tp_sl_use_atr(self) -> None:
        macd = MACDStrategy("macd_1", tp_atr_multiplier=2.0, sl_atr_multiplier=1.0)
        sig = macd.evaluate(
            "EUR_USD",
            _make_features(macd_histogram=0.001, macd_line=0.002, macd_signal=0.001, atr_14=0.003),
            _CTX,
        )
        assert sig.tp == pytest.approx(0.003 * 2.0)
        assert sig.sl == pytest.approx(0.003 * 1.0)


# ---------------------------------------------------------------------------
# BollingerStrategy
# ---------------------------------------------------------------------------


class TestBollingerStrategy:
    def test_near_lower_band_emits_long(self) -> None:
        bb = BollingerStrategy("bb_1")
        sig = bb.evaluate("EUR_USD", _make_features(bb_pct_b=0.02), _CTX)
        assert sig.signal == "long"
        assert sig.confidence > 0.0

    def test_near_upper_band_emits_short(self) -> None:
        bb = BollingerStrategy("bb_1")
        sig = bb.evaluate("EUR_USD", _make_features(bb_pct_b=0.97), _CTX)
        assert sig.signal == "short"

    def test_middle_range_emits_no_trade(self) -> None:
        bb = BollingerStrategy("bb_1")
        sig = bb.evaluate("EUR_USD", _make_features(bb_pct_b=0.5), _CTX)
        assert sig.signal == "no_trade"

    def test_at_lower_threshold_emits_long(self) -> None:
        bb = BollingerStrategy("bb_1", lower_threshold=0.05)
        sig = bb.evaluate("EUR_USD", _make_features(bb_pct_b=0.05), _CTX)
        assert sig.signal == "long"

    def test_at_upper_threshold_emits_short(self) -> None:
        bb = BollingerStrategy("bb_1", upper_threshold=0.95)
        sig = bb.evaluate("EUR_USD", _make_features(bb_pct_b=0.95), _CTX)
        assert sig.signal == "short"

    def test_strategy_type(self) -> None:
        bb = BollingerStrategy("bb_1")
        sig = bb.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.strategy_type == "bollinger_reversion"

    def test_strategy_id_propagated(self) -> None:
        bb = BollingerStrategy("my_bb")
        sig = bb.evaluate("EUR_USD", _make_features(bb_pct_b=0.02), _CTX)
        assert sig.strategy_id == "my_bb"

    def test_tp_sl_use_atr(self) -> None:
        bb = BollingerStrategy("bb_1", tp_atr_multiplier=1.5, sl_atr_multiplier=0.75)
        sig = bb.evaluate("EUR_USD", _make_features(bb_pct_b=0.02, atr_14=0.002), _CTX)
        assert sig.tp == pytest.approx(0.002 * 1.5)
        assert sig.sl == pytest.approx(0.002 * 0.75)

    def test_custom_thresholds(self) -> None:
        bb = BollingerStrategy("bb_1", lower_threshold=0.1, upper_threshold=0.9)
        assert bb.evaluate("EUR_USD", _make_features(bb_pct_b=0.05), _CTX).signal == "long"
        assert bb.evaluate("EUR_USD", _make_features(bb_pct_b=0.95), _CTX).signal == "short"
        assert bb.evaluate("EUR_USD", _make_features(bb_pct_b=0.5), _CTX).signal == "no_trade"
