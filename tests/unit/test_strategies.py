"""Unit tests: AIStrategyStub, MAStrategy, ATRStrategy (D3 §2.4.1 / M9).

Invariants:
  - signal ∈ {'long', 'short', 'no_trade'}
  - confidence ∈ [0.0, 1.0]
  - enabled == True (disabled strategies pre-filtered by engine, not tested here)
  - No DB access, no random, no clock (pure functions)
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext
from fx_ai_trading.services.strategies.ai_stub import AIStrategyStub
from fx_ai_trading.services.strategies.atr import ATRStrategy
from fx_ai_trading.services.strategies.ma import MAStrategy

_VALID_SIGNALS = {"long", "short", "no_trade"}


def _make_features(
    sma_20: float = 1.1010,
    sma_50: float = 1.1000,
    atr_14: float = 0.0010,
    last_close: float = 1.1015,
) -> FeatureSet:
    stats = {
        "sma_20": sma_20,
        "sma_50": sma_50,
        "atr_14": atr_14,
        "last_close": last_close,
    }
    return FeatureSet(
        feature_version="v1",
        feature_hash="aabbccdd11223344",
        feature_stats=stats,
        sampled_features=stats,
        computed_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


_CTX = StrategyContext(
    cycle_id=str(uuid4()),
    account_id="acc001",
    config_version="test-v1",
)


class TestAIStrategyStub:
    def test_returns_configured_signal(self) -> None:
        stub = AIStrategyStub("ai_stub_1", fixed_signal="long")
        sig = stub.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.signal == "long"

    def test_returns_short_when_configured(self) -> None:
        stub = AIStrategyStub("ai_stub_1", fixed_signal="short")
        sig = stub.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.signal == "short"

    def test_confidence_is_fixed(self) -> None:
        stub = AIStrategyStub("ai_stub_1", confidence=0.7)
        sig = stub.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.confidence == 0.7

    def test_enabled_is_true(self) -> None:
        stub = AIStrategyStub("ai_stub_1")
        sig = stub.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.enabled is True

    def test_strategy_type_and_version(self) -> None:
        stub = AIStrategyStub("ai_stub_1")
        sig = stub.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.strategy_type == "ai_stub"
        assert sig.strategy_version == "v0"

    def test_signal_is_valid(self) -> None:
        for s in ("long", "short", "no_trade"):
            stub = AIStrategyStub("ai_stub_1", fixed_signal=s)
            sig = stub.evaluate("EUR_USD", _make_features(), _CTX)
            assert sig.signal in _VALID_SIGNALS

    def test_deterministic_same_features(self) -> None:
        stub = AIStrategyStub("ai_stub_1")
        features = _make_features()
        sig1 = stub.evaluate("EUR_USD", features, _CTX)
        sig2 = stub.evaluate("EUR_USD", features, _CTX)
        assert sig1 == sig2


class TestMAStrategy:
    def test_long_when_sma20_above_sma50(self) -> None:
        ma = MAStrategy("ma_1")
        sig = ma.evaluate("EUR_USD", _make_features(sma_20=1.1010, sma_50=1.1000), _CTX)
        assert sig.signal == "long"

    def test_short_when_sma20_below_sma50(self) -> None:
        ma = MAStrategy("ma_1")
        sig = ma.evaluate("EUR_USD", _make_features(sma_20=1.0990, sma_50=1.1000), _CTX)
        assert sig.signal == "short"

    def test_no_trade_when_sma50_is_zero(self) -> None:
        ma = MAStrategy("ma_1")
        sig = ma.evaluate("EUR_USD", _make_features(sma_20=0.0, sma_50=0.0), _CTX)
        assert sig.signal == "no_trade"

    def test_no_trade_when_sma20_equals_sma50(self) -> None:
        ma = MAStrategy("ma_1")
        sig = ma.evaluate("EUR_USD", _make_features(sma_20=1.1000, sma_50=1.1000), _CTX)
        assert sig.signal == "no_trade"

    def test_confidence_in_range(self) -> None:
        ma = MAStrategy("ma_1")
        for sma_20 in (1.0, 1.1, 1.5, 2.0):
            sig = ma.evaluate("EUR_USD", _make_features(sma_20=sma_20, sma_50=1.1000), _CTX)
            assert 0.0 <= sig.confidence <= 1.0, f"confidence={sig.confidence} out of range"

    def test_tp_sl_are_positive_when_atr_positive(self) -> None:
        ma = MAStrategy("ma_1")
        sig = ma.evaluate("EUR_USD", _make_features(atr_14=0.001), _CTX)
        if sig.signal != "no_trade":
            assert sig.tp > 0
            assert sig.sl > 0

    def test_strategy_type(self) -> None:
        ma = MAStrategy("ma_1")
        sig = ma.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.strategy_type == "ma_crossover"

    def test_deterministic(self) -> None:
        ma = MAStrategy("ma_1")
        features = _make_features()
        sig1 = ma.evaluate("EUR_USD", features, _CTX)
        sig2 = ma.evaluate("EUR_USD", features, _CTX)
        assert sig1 == sig2


class TestATRStrategy:
    def test_no_trade_when_atr_is_zero(self) -> None:
        atr = ATRStrategy("atr_1")
        sig = atr.evaluate("EUR_USD", _make_features(atr_14=0.0), _CTX)
        assert sig.signal == "no_trade"
        assert sig.confidence == 0.0

    def test_long_when_close_above_sma20(self) -> None:
        atr = ATRStrategy("atr_1")
        sig = atr.evaluate(
            "EUR_USD",
            _make_features(last_close=1.1015, sma_20=1.1000, atr_14=0.001),
            _CTX,
        )
        assert sig.signal == "long"

    def test_short_when_close_below_sma20(self) -> None:
        atr = ATRStrategy("atr_1")
        sig = atr.evaluate(
            "EUR_USD",
            _make_features(last_close=1.0985, sma_20=1.1000, atr_14=0.001),
            _CTX,
        )
        assert sig.signal == "short"

    def test_no_trade_when_close_equals_sma20(self) -> None:
        atr = ATRStrategy("atr_1")
        sig = atr.evaluate(
            "EUR_USD",
            _make_features(last_close=1.1000, sma_20=1.1000, atr_14=0.001),
            _CTX,
        )
        assert sig.signal == "no_trade"

    def test_confidence_in_range(self) -> None:
        atr = ATRStrategy("atr_1")
        for close in (1.0, 1.1, 1.5, 2.0):
            sig = atr.evaluate(
                "EUR_USD",
                _make_features(last_close=close, sma_20=1.1000, atr_14=0.001),
                _CTX,
            )
            assert 0.0 <= sig.confidence <= 1.0

    def test_strategy_type(self) -> None:
        atr = ATRStrategy("atr_1")
        sig = atr.evaluate("EUR_USD", _make_features(), _CTX)
        assert sig.strategy_type == "atr_directional"

    def test_deterministic(self) -> None:
        atr = ATRStrategy("atr_1")
        features = _make_features()
        sig1 = atr.evaluate("EUR_USD", features, _CTX)
        sig2 = atr.evaluate("EUR_USD", features, _CTX)
        assert sig1 == sig2

    def test_signal_is_valid(self) -> None:
        atr = ATRStrategy("atr_1")
        for close in (0.5, 1.1000, 1.5):
            sig = atr.evaluate(
                "EUR_USD",
                _make_features(last_close=close, sma_20=1.1000, atr_14=0.001),
                _CTX,
            )
            assert sig.signal in _VALID_SIGNALS
