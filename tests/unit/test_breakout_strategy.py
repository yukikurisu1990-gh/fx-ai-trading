"""Unit tests: BreakoutStrategy (Phase 9.17 G-2)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext
from fx_ai_trading.services.strategies.breakout import BreakoutStrategy

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
# Long path (band break + trend up)
# ---------------------------------------------------------------------------


class TestBreakoutLong:
    def test_upper_break_with_uptrend_emits_long(self) -> None:
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.115, bb_upper=1.11, ema_12=1.105, ema_26=1.100),
            _CTX,
        )
        assert sig.signal == "long"
        assert sig.confidence > 0.0

    def test_upper_break_without_uptrend_no_trade(self) -> None:
        # Price breaks upper band but EMAs are downtrend → no_trade
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.115, bb_upper=1.11, ema_12=1.095, ema_26=1.100),
            _CTX,
        )
        assert sig.signal == "no_trade"

    def test_uptrend_without_break_no_trade(self) -> None:
        # EMAs trend up but no band break → no_trade
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.105, bb_upper=1.11, ema_12=1.105, ema_26=1.100),
            _CTX,
        )
        assert sig.signal == "no_trade"


# ---------------------------------------------------------------------------
# Short path (band break + trend down)
# ---------------------------------------------------------------------------


class TestBreakoutShort:
    def test_lower_break_with_downtrend_emits_short(self) -> None:
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.085, bb_lower=1.09, ema_12=1.095, ema_26=1.100),
            _CTX,
        )
        assert sig.signal == "short"
        assert sig.confidence > 0.0

    def test_lower_break_without_downtrend_no_trade(self) -> None:
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.085, bb_lower=1.09, ema_12=1.105, ema_26=1.100),
            _CTX,
        )
        assert sig.signal == "no_trade"

    def test_downtrend_without_break_no_trade(self) -> None:
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.095, bb_lower=1.09, ema_12=1.095, ema_26=1.100),
            _CTX,
        )
        assert sig.signal == "no_trade"


# ---------------------------------------------------------------------------
# No-trade
# ---------------------------------------------------------------------------


class TestBreakoutNoTrade:
    def test_neutral_emits_no_trade(self) -> None:
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.signal == "no_trade"
        assert sig.confidence == 0.0

    def test_zero_atr_no_trade(self) -> None:
        # atr=0 makes confidence undefined; force no_trade
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.115,
                bb_upper=1.11,
                ema_12=1.105,
                ema_26=1.100,
                atr_14=0.0,
            ),
            _CTX,
        )
        assert sig.signal == "no_trade"

    def test_equal_emas_no_trade_in_long_setup(self) -> None:
        # EMAs equal → trend_up=False → no_trade
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.115, bb_upper=1.11, ema_12=1.100, ema_26=1.100),
            _CTX,
        )
        assert sig.signal == "no_trade"


# ---------------------------------------------------------------------------
# Confidence behaviour (ATR-scaled)
# ---------------------------------------------------------------------------


class TestBreakoutConfidence:
    def test_confidence_saturates_at_full_strength(self) -> None:
        # close=1.116, bb_upper=1.11, atr=0.012 → strength = 0.006/0.012 = 0.5
        # default full_atr=0.5 → confidence saturates at 1.0
        bo = BreakoutStrategy("bo_1", breakout_strength_full_atr=0.5)
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.116,
                bb_upper=1.11,
                ema_12=1.105,
                ema_26=1.100,
                atr_14=0.012,
            ),
            _CTX,
        )
        assert sig.confidence == pytest.approx(1.0, abs=1e-4)

    def test_confidence_scales_linearly_below_full(self) -> None:
        # close=1.114, bb_upper=1.11, atr=0.020 → strength = 0.004/0.020 = 0.2
        # full_atr=0.5 → confidence = 0.2/0.5 = 0.4
        bo = BreakoutStrategy("bo_1", breakout_strength_full_atr=0.5)
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.114,
                bb_upper=1.11,
                ema_12=1.105,
                ema_26=1.100,
                atr_14=0.020,
            ),
            _CTX,
        )
        assert sig.confidence == pytest.approx(0.4, abs=1e-4)

    def test_confidence_increases_with_break_strength(self) -> None:
        # Use atr=0.020 so break strengths sit below saturation:
        # shallow: 0.001/0.020 = 0.05 ATR / 0.5 full = 0.10
        # deep:    0.005/0.020 = 0.25 ATR / 0.5 full = 0.50
        bo = BreakoutStrategy("bo_1")
        shallow = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.111,
                bb_upper=1.110,
                ema_12=1.105,
                ema_26=1.100,
                atr_14=0.020,
            ),
            _CTX,
        )
        deep = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.115,
                bb_upper=1.110,
                ema_12=1.105,
                ema_26=1.100,
                atr_14=0.020,
            ),
            _CTX,
        )
        assert deep.confidence > shallow.confidence

    def test_short_confidence_symmetric_to_long(self) -> None:
        # close=1.084, bb_lower=1.09, atr=0.012 → strength = 0.006/0.012 = 0.5
        bo = BreakoutStrategy("bo_1", breakout_strength_full_atr=0.5)
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.084,
                bb_lower=1.09,
                ema_12=1.095,
                ema_26=1.100,
                atr_14=0.012,
            ),
            _CTX,
        )
        assert sig.signal == "short"
        assert sig.confidence == pytest.approx(1.0, abs=1e-4)


# ---------------------------------------------------------------------------
# TP/SL/EV plumbing
# ---------------------------------------------------------------------------


class TestBreakoutTpSl:
    def test_tp_sl_use_atr(self) -> None:
        bo = BreakoutStrategy("bo_1", tp_atr_multiplier=2.0, sl_atr_multiplier=1.0)
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.115,
                bb_upper=1.11,
                ema_12=1.105,
                ema_26=1.100,
                atr_14=0.002,
            ),
            _CTX,
        )
        assert sig.tp == pytest.approx(0.002 * 2.0)
        assert sig.sl == pytest.approx(0.002 * 1.0)

    def test_default_tp_sl_match_lgbm_baseline(self) -> None:
        # Default 1.5 / 1.0 must match LightGBM triple-barrier baseline
        # for ensemble PnL comparability.
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.115,
                bb_upper=1.11,
                ema_12=1.105,
                ema_26=1.100,
                atr_14=0.001,
            ),
            _CTX,
        )
        assert sig.tp == pytest.approx(0.001 * 1.5)
        assert sig.sl == pytest.approx(0.001 * 1.0)

    def test_no_trade_has_zero_ev(self) -> None:
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.ev_before_cost == 0.0
        assert sig.ev_after_cost == 0.0


# ---------------------------------------------------------------------------
# DTO fields
# ---------------------------------------------------------------------------


class TestBreakoutDTO:
    def test_strategy_id_propagated(self) -> None:
        bo = BreakoutStrategy("my_bo")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.115, bb_upper=1.11, ema_12=1.105, ema_26=1.100),
            _CTX,
        )
        assert sig.strategy_id == "my_bo"

    def test_strategy_type(self) -> None:
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.115, bb_upper=1.11, ema_12=1.105, ema_26=1.100),
            _CTX,
        )
        assert sig.strategy_type == "breakout"

    def test_strategy_version(self) -> None:
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.115, bb_upper=1.11, ema_12=1.105, ema_26=1.100),
            _CTX,
        )
        assert sig.strategy_version == "v1"

    def test_enabled_is_true(self) -> None:
        bo = BreakoutStrategy("bo_1")
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.115, bb_upper=1.11, ema_12=1.105, ema_26=1.100),
            _CTX,
        )
        assert sig.enabled is True

    def test_holding_time_propagated(self) -> None:
        bo = BreakoutStrategy("bo_1", holding_time_seconds=7200)
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(last_close=1.115, bb_upper=1.11, ema_12=1.105, ema_26=1.100),
            _CTX,
        )
        assert sig.holding_time_seconds == 7200


# ---------------------------------------------------------------------------
# Custom thresholds
# ---------------------------------------------------------------------------


class TestBreakoutCustomThresholds:
    def test_lower_full_atr_yields_higher_confidence(self) -> None:
        # Same break but lower full_atr means we hit confidence=1.0 sooner
        loose = BreakoutStrategy("bo_loose", breakout_strength_full_atr=1.0)
        tight = BreakoutStrategy("bo_tight", breakout_strength_full_atr=0.2)
        features = _make_features(
            last_close=1.114,
            bb_upper=1.11,
            ema_12=1.105,
            ema_26=1.100,
            atr_14=0.020,
        )
        sig_loose = loose.evaluate("EUR_USD", features, _CTX)
        sig_tight = tight.evaluate("EUR_USD", features, _CTX)
        assert sig_tight.confidence > sig_loose.confidence


# ---------------------------------------------------------------------------
# Phase 9.17b/I-1 confidence_threshold post-filter
# ---------------------------------------------------------------------------


class TestBreakoutConfidenceThreshold:
    def test_default_threshold_preserves_phase9_17_behavior(self) -> None:
        # Default 0.0 → all rule-met breakouts fire (Phase 9.17 G-2 contract)
        bo_default = BreakoutStrategy("bo_default")
        bo_explicit = BreakoutStrategy("bo_explicit", confidence_threshold=0.0)
        features = _make_features(
            last_close=1.111,
            bb_upper=1.110,
            ema_12=1.105,
            ema_26=1.100,
            atr_14=0.020,
        )
        sig_d = bo_default.evaluate("EUR_USD", features, _CTX)
        sig_e = bo_explicit.evaluate("EUR_USD", features, _CTX)
        assert sig_d.signal == "long"
        assert sig_e.signal == "long"
        assert sig_d.confidence == sig_e.confidence

    def test_threshold_suppresses_weak_breakout(self) -> None:
        # Tiny break: close=1.111, upper=1.110 → break = 0.001
        # atr=0.020 → strength = 0.001/0.020 = 0.05 ATR
        # full_atr=0.5 default → confidence = 0.05/0.5 = 0.10 → below 0.5
        bo = BreakoutStrategy("bo_high", confidence_threshold=0.5)
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.111,
                bb_upper=1.110,
                ema_12=1.105,
                ema_26=1.100,
                atr_14=0.020,
            ),
            _CTX,
        )
        assert sig.signal == "no_trade"
        assert sig.confidence == 0.0
        assert sig.ev_before_cost == 0.0

    def test_threshold_admits_strong_breakout(self) -> None:
        # Strong break: close=1.116, upper=1.110 → break=0.006
        # atr=0.012 → strength=0.5 ATR → confidence=1.0 (saturated)
        bo = BreakoutStrategy("bo_high", confidence_threshold=0.5)
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.116,
                bb_upper=1.110,
                ema_12=1.105,
                ema_26=1.100,
                atr_14=0.012,
            ),
            _CTX,
        )
        assert sig.signal == "long"
        assert sig.confidence == pytest.approx(1.0, abs=1e-4)

    def test_threshold_at_exact_boundary_admits(self) -> None:
        # confidence == threshold → admitted (uses `<` filter)
        # close=1.114, upper=1.110 → break=0.004; atr=0.020 → 0.20 ATR
        # full_atr=0.4 → confidence = 0.20/0.4 = 0.5
        bo = BreakoutStrategy(
            "bo_boundary",
            breakout_strength_full_atr=0.4,
            confidence_threshold=0.5,
        )
        sig = bo.evaluate(
            "EUR_USD",
            _make_features(
                last_close=1.114,
                bb_upper=1.110,
                ema_12=1.105,
                ema_26=1.100,
                atr_14=0.020,
            ),
            _CTX,
        )
        assert sig.signal == "long"
        assert sig.confidence == pytest.approx(0.5, abs=1e-4)

    def test_threshold_does_not_affect_no_trade_state(self) -> None:
        bo = BreakoutStrategy("bo_high", confidence_threshold=0.9)
        sig = bo.evaluate("EUR_USD", _make_features(), _CTX)  # neutral state
        assert sig.signal == "no_trade"
        assert sig.confidence == 0.0
