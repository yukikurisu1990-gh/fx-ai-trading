"""model_store — LightGBM model persistence (Phase 9.6).

Saves and loads a trained LightGBM model together with a YAML metadata
file that satisfies Phase 1 §4.13.3 lifecycle requirements.

Directory layout (one dir per model):
    models/ml_baseline_<timestamp>/
        model.pkl          — joblib-serialised LightGBM Booster
        metadata.yaml      — lifecycle fields (see ModelMetadata)
"""

from __future__ import annotations

import pickle
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ModelMetadata:
    """Phase 1 §4.13.3 required fields + training provenance."""

    model_id: str
    created_at: str  # ISO-8601 UTC
    feature_version: str
    feature_columns: list[str]
    label_column: str
    train_cutoff: str  # ISO-8601 UTC — last timestamp in training set
    val_cutoff: str  # ISO-8601 UTC — last timestamp in validation set
    n_train_rows: int
    n_val_rows: int
    metrics: dict[str, float]
    hyperparams: dict[str, Any]


def save_model(model: Any, metadata: ModelMetadata, output_dir: Path) -> Path:
    """Persist *model* + *metadata* under *output_dir*.

    Returns the directory path (created if needed).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "model.pkl").open("wb") as fh:
        pickle.dump(model, fh, protocol=5)
    with (output_dir / "metadata.yaml").open("w", encoding="utf-8") as fh:
        yaml.dump(asdict(metadata), fh, allow_unicode=True, sort_keys=True)
    return output_dir


def load_model(model_dir: Path) -> tuple[Any, ModelMetadata]:
    """Load model + metadata from *model_dir*.

    Returns (model, metadata).
    """
    with (model_dir / "model.pkl").open("rb") as fh:
        model = pickle.load(fh)  # noqa: S301
    with (model_dir / "metadata.yaml").open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    metadata = ModelMetadata(**raw)
    return model, metadata


def model_dir_name(now: datetime) -> str:
    """Return a timestamped directory name for a new model."""
    return f"ml_baseline_{now.strftime('%Y%m%dT%H%M%S')}"


__all__ = ["ModelMetadata", "load_model", "model_dir_name", "save_model"]
