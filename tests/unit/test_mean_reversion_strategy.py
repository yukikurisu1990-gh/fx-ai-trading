"""Unit tests: MeanReversionStrategy (Phase 9.17 G-1)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext
from fx_ai_trading.services.strategies.mean_reversion import MeanReversionStrategy

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
# Long path (both RSI and BB must be oversold)
# ---------------------------------------------------------------------------


class TestMeanReversionLong:
    def test_both_oversold_emits_long(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=20.0, bb_pct_b=0.05), _CTX)
        assert sig.signal == "long"
        assert sig.confidence > 0.0

    def test_rsi_oversold_only_no_trade(self) -> None:
        # RSI below threshold but bb_pct_b in neutral zone → no_trade (AND logic)
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=20.0, bb_pct_b=0.5), _CTX)
        assert sig.signal == "no_trade"
        assert sig.confidence == 0.0

    def test_bb_oversold_only_no_trade(self) -> None:
        # bb_pct_b below threshold but RSI neutral → no_trade (AND logic)
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=50.0, bb_pct_b=0.05), _CTX)
        assert sig.signal == "no_trade"
        assert sig.confidence == 0.0

    def test_at_long_thresholds_emits_long(self) -> None:
        mr = MeanReversionStrategy("mr_1", rsi_oversold=30.0, bb_lower=0.10)
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=30.0, bb_pct_b=0.10), _CTX)
        assert sig.signal == "long"


# ---------------------------------------------------------------------------
# Short path (both RSI and BB must be overbought)
# ---------------------------------------------------------------------------


class TestMeanReversionShort:
    def test_both_overbought_emits_short(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=80.0, bb_pct_b=0.95), _CTX)
        assert sig.signal == "short"
        assert sig.confidence > 0.0

    def test_rsi_overbought_only_no_trade(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=80.0, bb_pct_b=0.5), _CTX)
        assert sig.signal == "no_trade"

    def test_bb_overbought_only_no_trade(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=50.0, bb_pct_b=0.95), _CTX)
        assert sig.signal == "no_trade"

    def test_at_short_thresholds_emits_short(self) -> None:
        mr = MeanReversionStrategy("mr_1", rsi_overbought=70.0, bb_upper=0.90)
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=70.0, bb_pct_b=0.90), _CTX)
        assert sig.signal == "short"


# ---------------------------------------------------------------------------
# No-trade
# ---------------------------------------------------------------------------


class TestMeanReversionNoTrade:
    def test_neutral_emits_no_trade(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=50.0, bb_pct_b=0.5), _CTX)
        assert sig.signal == "no_trade"
        assert sig.confidence == 0.0

    def test_conflicting_signals_no_trade(self) -> None:
        # RSI oversold but BB at upper band — conflict → no_trade
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=20.0, bb_pct_b=0.95), _CTX)
        assert sig.signal == "no_trade"

    def test_missing_features_default_to_neutral(self) -> None:
        # No rsi_14 / bb_pct_b → defaults 50.0 / 0.5 → no_trade
        mr = MeanReversionStrategy("mr_1")
        features = FeatureSet(
            feature_version="v2",
            feature_hash="test",
            feature_stats={"atr_14": 0.001},
            sampled_features={"atr_14": 0.001},
            computed_at=datetime(2024, 6, 1, 12, 0, tzinfo=UTC),
        )
        sig = mr.evaluate("EUR_USD", features, _CTX)
        assert sig.signal == "no_trade"


# ---------------------------------------------------------------------------
# Confidence behaviour
# ---------------------------------------------------------------------------


class TestMeanReversionConfidence:
    def test_confidence_is_average_of_rsi_and_bb_long(self) -> None:
        # rsi=15 → rsi_conf = (30-15)/30 = 0.5
        # bb_pct_b=0.05 → bb_conf = (0.10-0.05)/0.10 = 0.5
        # avg = 0.5
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=15.0, bb_pct_b=0.05), _CTX)
        assert sig.confidence == pytest.approx(0.5, abs=1e-4)

    def test_confidence_is_average_of_rsi_and_bb_short(self) -> None:
        # rsi=85 → rsi_conf = (85-70)/30 = 0.5
        # bb_pct_b=0.95 → bb_conf = (0.95-0.90)/0.10 = 0.5
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=85.0, bb_pct_b=0.95), _CTX)
        assert sig.confidence == pytest.approx(0.5, abs=1e-4)

    def test_confidence_increases_deeper_in_long_zone(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        shallow = mr.evaluate("EUR_USD", _make_features(rsi_14=28.0, bb_pct_b=0.08), _CTX)
        deep = mr.evaluate("EUR_USD", _make_features(rsi_14=10.0, bb_pct_b=0.02), _CTX)
        assert deep.confidence > shallow.confidence

    def test_confidence_capped_at_1(self) -> None:
        # Extreme oversold → both conf saturate at 1.0 → average 1.0
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=0.0, bb_pct_b=0.0), _CTX)
        assert sig.confidence == pytest.approx(1.0, abs=1e-4)


# ---------------------------------------------------------------------------
# TP/SL/EV plumbing
# ---------------------------------------------------------------------------


class TestMeanReversionTpSl:
    def test_tp_sl_use_atr(self) -> None:
        mr = MeanReversionStrategy("mr_1", tp_atr_multiplier=2.0, sl_atr_multiplier=1.0)
        sig = mr.evaluate(
            "EUR_USD",
            _make_features(rsi_14=20.0, bb_pct_b=0.05, atr_14=0.002),
            _CTX,
        )
        assert sig.tp == pytest.approx(0.002 * 2.0)
        assert sig.sl == pytest.approx(0.002 * 1.0)

    def test_default_tp_sl_match_lgbm_baseline(self) -> None:
        # Default 1.5 / 1.0 must match LightGBM triple-barrier baseline
        # for ensemble PnL comparability (design memo §13 default 4).
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate(
            "EUR_USD",
            _make_features(rsi_14=20.0, bb_pct_b=0.05, atr_14=0.001),
            _CTX,
        )
        assert sig.tp == pytest.approx(0.001 * 1.5)
        assert sig.sl == pytest.approx(0.001 * 1.0)

    def test_no_trade_has_zero_ev(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=50.0, bb_pct_b=0.5), _CTX)
        assert sig.ev_before_cost == 0.0
        assert sig.ev_after_cost == 0.0


# ---------------------------------------------------------------------------
# DTO fields
# ---------------------------------------------------------------------------


class TestMeanReversionDTO:
    def test_strategy_id_propagated(self) -> None:
        mr = MeanReversionStrategy("my_mr")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=20.0, bb_pct_b=0.05), _CTX)
        assert sig.strategy_id == "my_mr"

    def test_strategy_type(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=20.0, bb_pct_b=0.05), _CTX)
        assert sig.strategy_type == "mean_reversion"

    def test_strategy_version(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=20.0, bb_pct_b=0.05), _CTX)
        assert sig.strategy_version == "v1"

    def test_enabled_is_true(self) -> None:
        mr = MeanReversionStrategy("mr_1")
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=20.0, bb_pct_b=0.05), _CTX)
        assert sig.enabled is True

    def test_holding_time_propagated(self) -> None:
        mr = MeanReversionStrategy("mr_1", holding_time_seconds=7200)
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=20.0, bb_pct_b=0.05), _CTX)
        assert sig.holding_time_seconds == 7200


# ---------------------------------------------------------------------------
# Custom thresholds
# ---------------------------------------------------------------------------


class TestMeanReversionCustomThresholds:
    def test_custom_rsi_thresholds_respected(self) -> None:
        mr = MeanReversionStrategy(
            "mr_1",
            rsi_oversold=25.0,
            rsi_overbought=75.0,
        )
        # rsi=27 < default 30 but > custom 25 → no_trade
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=27.0, bb_pct_b=0.05), _CTX)
        assert sig.signal == "no_trade"
        # rsi=24 < custom 25 → long (with bb confirmation)
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=24.0, bb_pct_b=0.05), _CTX)
        assert sig.signal == "long"

    def test_custom_bb_thresholds_respected(self) -> None:
        mr = MeanReversionStrategy("mr_1", bb_lower=0.05, bb_upper=0.95)
        # bb_pct_b=0.08 > custom 0.05 → no_trade
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=20.0, bb_pct_b=0.08), _CTX)
        assert sig.signal == "no_trade"
        # bb_pct_b=0.04 < custom 0.05 → long
        sig = mr.evaluate("EUR_USD", _make_features(rsi_14=20.0, bb_pct_b=0.04), _CTX)
        assert sig.signal == "long"
