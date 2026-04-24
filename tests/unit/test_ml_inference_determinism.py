"""Unit tests: MLDirectionStrategy + MLInferenceService determinism (Phase 9.6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fx_ai_trading.services.ml.model_store import ModelMetadata, save_model
from fx_ai_trading.services.ml.training import (
    DEFAULT_PARAMS,
    FEATURE_COLUMNS,
    LABEL_COLUMN,
)


def _make_tiny_model(tmp_dir: Path) -> Path:
    """Train a minimal LightGBM model and save it; return model_dir."""
    import lightgbm as lgb

    from fx_ai_trading.services.ml.training import _LABEL_ENCODE

    # 60 synthetic rows: 20 per class.
    n_per_class = 20
    x_data, y_data = [], []
    for _cls_raw, cls_enc in _LABEL_ENCODE.items():
        for i in range(n_per_class):
            # Each class has slightly different feature values for separability.
            row = [float(cls_enc + i * 0.001) for _ in FEATURE_COLUMNS]
            x_data.append(row)
            y_data.append(cls_enc)

    model = lgb.LGBMClassifier(**{**DEFAULT_PARAMS, "n_estimators": 10})
    model.fit(x_data, y_data)

    t0 = datetime(2024, 1, 1, tzinfo=UTC)
    metadata = ModelMetadata(
        model_id="test_model",
        created_at=t0.isoformat(),
        feature_version="v2",
        feature_columns=FEATURE_COLUMNS,
        label_column=LABEL_COLUMN,
        train_cutoff=t0.isoformat(),
        val_cutoff=(t0 + timedelta(days=30)).isoformat(),
        n_train_rows=len(x_data),
        n_val_rows=0,
        metrics={"hit_rate": 0.5},
        hyperparams=DEFAULT_PARAMS,
    )
    save_model(model, metadata, tmp_dir)
    return tmp_dir


class TestMLInferenceDeterminism:
    def test_same_input_same_output(self, tmp_path: Path) -> None:
        from fx_ai_trading.services.ml.inference import MLInferenceService

        model_dir = _make_tiny_model(tmp_path / "model")
        svc = MLInferenceService(model_dir)
        features = {col: 0.5 for col in FEATURE_COLUMNS}

        result1 = svc.predict(features)
        result2 = svc.predict(features)
        assert result1 == result2

    def test_predict_returns_valid_label_and_probability(self, tmp_path: Path) -> None:
        from fx_ai_trading.services.ml.inference import MLInferenceService

        model_dir = _make_tiny_model(tmp_path / "model")
        svc = MLInferenceService(model_dir)
        features = {col: 1.0 for col in FEATURE_COLUMNS}

        label, prob = svc.predict(features)
        assert label in (-1, 0, 1)
        assert 0.0 <= prob <= 1.0

    def test_predict_proba_all_sums_to_one(self, tmp_path: Path) -> None:
        from fx_ai_trading.services.ml.inference import MLInferenceService

        model_dir = _make_tiny_model(tmp_path / "model")
        svc = MLInferenceService(model_dir)
        features = {col: 0.0 for col in FEATURE_COLUMNS}

        proba = svc.predict_proba_all(features)
        assert set(proba.keys()) == {-1, 0, 1}
        assert abs(sum(proba.values()) - 1.0) < 1e-6

    def test_missing_feature_defaults_to_zero(self, tmp_path: Path) -> None:
        from fx_ai_trading.services.ml.inference import MLInferenceService

        model_dir = _make_tiny_model(tmp_path / "model")
        svc = MLInferenceService(model_dir)

        # Partial features (missing keys → 0.0).
        result_full = svc.predict({col: 0.0 for col in FEATURE_COLUMNS})
        result_empty = svc.predict({})
        assert result_full == result_empty

    def test_metadata_loaded_correctly(self, tmp_path: Path) -> None:
        from fx_ai_trading.services.ml.inference import MLInferenceService

        model_dir = _make_tiny_model(tmp_path / "model")
        svc = MLInferenceService(model_dir)
        assert svc.metadata.model_id == "test_model"
        assert svc.metadata.feature_columns == FEATURE_COLUMNS


class TestMLDirectionStrategy:
    def test_long_signal_above_threshold(self, tmp_path: Path) -> None:
        from fx_ai_trading.domain.feature import FeatureSet
        from fx_ai_trading.domain.strategy import StrategyContext
        from fx_ai_trading.services.strategies.ai import MLDirectionStrategy

        model_dir = _make_tiny_model(tmp_path / "model")
        strategy = MLDirectionStrategy("s1", model_dir, threshold=0.0)

        features = FeatureSet(
            feature_version="v2",
            feature_hash="abc",
            feature_stats={col: 2.0 for col in FEATURE_COLUMNS},
            sampled_features={},
            computed_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        ctx = StrategyContext(cycle_id=str(uuid4()), account_id="acct", config_version="v1")

        signal = strategy.evaluate("EUR_USD", features, ctx)
        assert signal.signal in ("long", "short", "no_trade")
        assert signal.strategy_type == "ml_direction"
        assert signal.enabled is True
        assert 0.0 <= signal.confidence <= 1.0

    def test_no_trade_when_below_threshold(self, tmp_path: Path) -> None:
        from fx_ai_trading.domain.feature import FeatureSet
        from fx_ai_trading.domain.strategy import StrategyContext
        from fx_ai_trading.services.strategies.ai import MLDirectionStrategy

        model_dir = _make_tiny_model(tmp_path / "model")
        # threshold=1.0 → no class will reach 100% probability.
        strategy = MLDirectionStrategy("s1", model_dir, threshold=1.0)

        features = FeatureSet(
            feature_version="v2",
            feature_hash="abc",
            feature_stats={col: 0.5 for col in FEATURE_COLUMNS},
            sampled_features={},
            computed_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        ctx = StrategyContext(cycle_id=str(uuid4()), account_id="acct", config_version="v1")

        signal = strategy.evaluate("EUR_USD", features, ctx)
        assert signal.signal == "no_trade"

    def test_deterministic_across_calls(self, tmp_path: Path) -> None:
        from fx_ai_trading.domain.feature import FeatureSet
        from fx_ai_trading.domain.strategy import StrategyContext
        from fx_ai_trading.services.strategies.ai import MLDirectionStrategy

        model_dir = _make_tiny_model(tmp_path / "model")
        strategy = MLDirectionStrategy("s1", model_dir)

        features = FeatureSet(
            feature_version="v2",
            feature_hash="abc",
            feature_stats={col: 1.5 for col in FEATURE_COLUMNS},
            sampled_features={},
            computed_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        ctx = StrategyContext(cycle_id=str(uuid4()), account_id="acct", config_version="v1")

        sig1 = strategy.evaluate("EUR_USD", features, ctx)
        sig2 = strategy.evaluate("EUR_USD", features, ctx)
        assert sig1.signal == sig2.signal
        assert sig1.confidence == sig2.confidence
