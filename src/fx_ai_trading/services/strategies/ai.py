"""MLDirectionStrategy — LightGBM-backed StrategyEvaluator (Phase 9.6).

Replaces AIStrategyStub with a real model-backed strategy.
Implements the StrategyEvaluator Protocol (domain/strategy.py).

Signal logic:
  - Compute P(long), P(short), P(timeout) via MLInferenceService.
  - If P(long)  >= threshold → signal='long'
  - If P(short) >= threshold → signal='short'
  - Otherwise                → signal='no_trade'
  - confidence = max(P(long), P(short), P(timeout))
"""

from __future__ import annotations

from pathlib import Path

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal
from fx_ai_trading.services.ml.inference import MLInferenceService

_STRATEGY_TYPE = "ml_direction"
_STRATEGY_VERSION = "v1"


class MLDirectionStrategy:
    """LightGBM triple-barrier direction strategy.

    Args:
        strategy_id: Unique ID for this strategy instance.
        model_dir: Path to a directory produced by model_store.save_model().
        threshold: Minimum class probability to emit a directional signal.
        tp: Fixed take-profit distance (price units).
        sl: Fixed stop-loss distance (price units).
        holding_time_seconds: Fixed expected holding duration.
    """

    def __init__(
        self,
        strategy_id: str,
        model_dir: str | Path,
        threshold: float = 0.6,
        tp: float = 0.01,
        sl: float = 0.005,
        holding_time_seconds: int = 3600,
    ) -> None:
        self._strategy_id = strategy_id
        self._threshold = threshold
        self._tp = tp
        self._sl = sl
        self._holding_time_seconds = holding_time_seconds
        self._inference = MLInferenceService(Path(model_dir))

    def evaluate(
        self,
        instrument: str,
        features: FeatureSet,
        context: StrategyContext,
    ) -> StrategySignal:
        proba = self._inference.predict_proba_all(features.feature_stats)
        p_long = proba.get(1, 0.0)
        p_short = proba.get(-1, 0.0)
        confidence = max(proba.values()) if proba else 0.0

        if p_long >= self._threshold:
            signal = "long"
        elif p_short >= self._threshold:
            signal = "short"
        else:
            signal = "no_trade"

        ev = confidence * self._tp - (1 - confidence) * self._sl

        return StrategySignal(
            strategy_id=self._strategy_id,
            strategy_type=_STRATEGY_TYPE,
            strategy_version=_STRATEGY_VERSION,
            signal=signal,
            confidence=confidence,
            ev_before_cost=ev,
            ev_after_cost=ev,
            tp=self._tp,
            sl=self._sl,
            holding_time_seconds=self._holding_time_seconds,
            enabled=True,
        )


__all__ = ["MLDirectionStrategy"]
