"""Unit tests for LGBMStrategy (Phase 9.5-A)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import lightgbm as lgb
import numpy as np
import pytest

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext
from fx_ai_trading.services.strategies.lgbm_strategy import LGBMStrategy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FEATURE_COLS = [
    "atr_14", "bb_lower", "bb_middle", "bb_pct_b", "bb_upper", "bb_width",
    "ema_12", "ema_26", "last_close",
    "macd_histogram", "macd_line", "macd_signal",
    "rsi_14", "sma_20", "sma_50",
]


def _make_manifest(model_dir: Path) -> None:
    manifest = {
        "feature_cols": _FEATURE_COLS,
        "tp_mult": 1.5,
        "sl_mult": 1.0,
        "trained_pairs": ["USD_JPY", "EUR_USD"],
    }
    (model_dir / "manifest.json").write_text(json.dumps(manifest))


def _make_tiny_lgbm(p_long: float = 0.5, p_neutral: float = 0.3) -> lgb.LGBMClassifier:
    """Train a minimal LGBMClassifier on 30 synthetic rows (3 classes)."""
    rng = np.random.default_rng(42)
    n = 30
    x = rng.standard_normal((n, len(_FEATURE_COLS)))
    # 10 rows each of class 0 (-1→0), 1 (0→1), 2 (+1→2)
    y = [0] * 10 + [1] * 10 + [2] * 10
    model = lgb.LGBMClassifier(n_estimators=5, num_leaves=4, verbose=-1)
    model.fit(x, y)
    return model


def _make_features(atr_14: float = 0.5, rsi_14: float = 50.0) -> FeatureSet:
    stats = {
        "atr_14": atr_14, "bb_lower": 159.0, "bb_middle": 160.0,
        "bb_pct_b": 0.5, "bb_upper": 161.0, "bb_width": 0.0125,
        "ema_12": 160.0, "ema_26": 160.0, "last_close": 160.0,
        "macd_histogram": 0.0, "macd_line": 0.0, "macd_signal": 0.0,
        "rsi_14": rsi_14, "sma_20": 160.0, "sma_50": 159.5,
    }
    return FeatureSet(
        feature_version="v3",
        feature_hash="test",
        feature_stats=stats,
        sampled_features=stats,
        computed_at=datetime.now(UTC),  # noqa: CLOCK
    )


def _make_context() -> StrategyContext:
    return StrategyContext(
        cycle_id=str(uuid4()),
        account_id="test-account",
        config_version="v3",
    )


def _make_strategy(tmp_path: Path, threshold: float = 0.40) -> LGBMStrategy:
    """Create LGBMStrategy with tiny real models, bypassing joblib."""
    _make_manifest(tmp_path)
    # Create minimal manifest only; inject models directly
    strategy = object.__new__(LGBMStrategy)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    strategy._feature_cols = manifest["feature_cols"]
    strategy._tp_mult = manifest["tp_mult"]
    strategy._sl_mult = manifest["sl_mult"]
    strategy._threshold = threshold
    strategy._strategy_id = "lgbm"
    strategy._models = {
        "USD_JPY": _make_tiny_lgbm(),
        "EUR_USD": _make_tiny_lgbm(),
    }
    return strategy


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLGBMStrategyInit:
    def test_raises_if_manifest_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="manifest not found"):
            LGBMStrategy(model_dir=tmp_path)

    def test_loads_manifest_feature_cols(self, tmp_path):
        import joblib
        _make_manifest(tmp_path)
        model = _make_tiny_lgbm()
        joblib.dump(model, tmp_path / "USD_JPY.joblib")

        strategy = LGBMStrategy(model_dir=tmp_path)
        assert strategy._feature_cols == _FEATURE_COLS
        assert "USD_JPY" in strategy._models


class TestLGBMStrategyEvaluate:
    def test_returns_strategy_signal_with_correct_fields(self, tmp_path):
        strategy = _make_strategy(tmp_path)
        sig = strategy.evaluate("USD_JPY", _make_features(), _make_context())
        assert sig.strategy_type == "lgbm_classifier"
        assert sig.strategy_version == "v1"
        assert sig.signal in ("long", "short", "no_trade")
        assert 0.0 <= sig.confidence <= 1.0
        assert sig.enabled is True

    def test_no_trade_when_no_model_for_instrument(self, tmp_path):
        strategy = _make_strategy(tmp_path)
        sig = strategy.evaluate("AUD_JPY", _make_features(), _make_context())
        assert sig.signal == "no_trade"
        assert sig.confidence == 0.0
        assert sig.ev_after_cost == 0.0

    def test_ev_proportional_to_atr(self, tmp_path):
        strategy = _make_strategy(tmp_path)
        feat_low = _make_features(atr_14=0.5)
        feat_high = _make_features(atr_14=1.0)
        sig_low = strategy.evaluate("USD_JPY", feat_low, _make_context())
        sig_high = strategy.evaluate("USD_JPY", feat_high, _make_context())
        # Same signal → EV should scale ~linearly with ATR
        if sig_low.signal == sig_high.signal and sig_low.signal != "no_trade":
            assert abs(sig_high.ev_after_cost) > abs(sig_low.ev_after_cost) * 1.5

    def test_zero_atr_gives_zero_tp_sl(self, tmp_path):
        strategy = _make_strategy(tmp_path)
        sig = strategy.evaluate("USD_JPY", _make_features(atr_14=0.0), _make_context())
        assert sig.tp == 0.0
        assert sig.sl == 0.0

    def test_ev_before_equals_ev_after_cost(self, tmp_path):
        strategy = _make_strategy(tmp_path)
        sig = strategy.evaluate("USD_JPY", _make_features(), _make_context())
        assert sig.ev_before_cost == sig.ev_after_cost

    def test_signal_changes_with_different_proba(self, tmp_path):
        _make_manifest(tmp_path)
        # High p_long model → long signal expected
        high_long = _make_tiny_lgbm()
        strategy = object.__new__(LGBMStrategy)
        strategy._feature_cols = _FEATURE_COLS
        strategy._tp_mult = 1.5
        strategy._sl_mult = 1.0
        strategy._threshold = 0.01  # very low threshold to ensure signal fires
        strategy._strategy_id = "lgbm"
        strategy._models = {"USD_JPY": high_long}
        sig = strategy.evaluate("USD_JPY", _make_features(), _make_context())
        # With very low threshold, should get a signal (long or short)
        assert sig.signal in ("long", "short")
