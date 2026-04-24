"""inference — LightGBM model inference service (Phase 9.6).

Loads a model from disk (model_store) and exposes predict() for use by
MLDirectionStrategy.  Latency SLA: log a warning if inference exceeds 200ms.

Label encoding is the inverse of training.py's _LABEL_ENCODE:
  encoded 0 → original -1 (short wins)
  encoded 1 → original  0 (timeout)
  encoded 2 → original +1 (long wins)
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from fx_ai_trading.services.ml.model_store import ModelMetadata, load_model

if TYPE_CHECKING:
    pass

_log = logging.getLogger(__name__)

_LATENCY_WARN_MS = 200.0

# Encoded class index → original triple-barrier label.
_DECODE = {0: -1, 1: 0, 2: 1}


class MLInferenceService:
    """Thin wrapper around a loaded LightGBM model.

    Args:
        model_dir: Path to a directory produced by model_store.save_model().
    """

    def __init__(self, model_dir: Path) -> None:
        self._model, self._metadata = load_model(model_dir)
        self._feature_columns = self._metadata.feature_columns

    @property
    def metadata(self) -> ModelMetadata:
        return self._metadata

    def predict(self, features: dict[str, float]) -> tuple[int, float]:
        """Return (predicted_label, max_class_probability).

        Args:
            features: Dict keyed by feature name.  Missing keys default to 0.0.

        Returns:
            (label, probability) where label ∈ {-1, 0, 1} and probability ∈ [0, 1].
        """
        row = [[features.get(col, 0.0) for col in self._feature_columns]]

        t0 = time.perf_counter()
        proba = self._model.predict_proba(row)[0]
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if elapsed_ms > _LATENCY_WARN_MS:
            _log.warning("MLInferenceService: inference took %.1f ms (SLA=200ms)", elapsed_ms)

        best_idx = int(proba.argmax())
        return _DECODE[best_idx], float(proba[best_idx])

    def predict_proba_all(self, features: dict[str, float]) -> dict[int, float]:
        """Return probability for each label class.

        Returns dict {-1: p_short, 0: p_timeout, 1: p_long}.
        """
        row = [[features.get(col, 0.0) for col in self._feature_columns]]
        proba = self._model.predict_proba(row)[0]
        return {_DECODE[i]: float(p) for i, p in enumerate(proba)}


def load_inference_service(model_dir: str | Path) -> MLInferenceService:
    """Convenience factory for scripts and tests."""
    return MLInferenceService(Path(model_dir))


__all__ = ["MLInferenceService", "load_inference_service"]
