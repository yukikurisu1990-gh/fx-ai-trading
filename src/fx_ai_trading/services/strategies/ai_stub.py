"""AIStrategyStub — fixed-confidence AI strategy placeholder (D3 §2.4.1 / M9).

Invariants:
  - Always returns the configured fixed_signal (default 'long').
  - confidence is fixed at construction time.
  - No DB access, no random state, no clock usage.
  - ev_after_cost is set to ev_before_cost (EVEstimator fills the real value later).

Phase 7: Replace body with real model inference via ModelRegistry / Predictor.
"""

from __future__ import annotations

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal

_STRATEGY_TYPE = "ai_stub"
_STRATEGY_VERSION = "v0"


class AIStrategyStub:
    """Fixed-confidence AI strategy stub for paper-mode pipeline testing.

    Args:
        strategy_id: Unique ID for this strategy instance.
        fixed_signal: Signal to return on every call ('long' | 'short' | 'no_trade').
        confidence: Fixed confidence value in [0, 1].
        tp: Fixed take-profit distance (price units).
        sl: Fixed stop-loss distance (price units).
        holding_time_seconds: Fixed expected holding duration.
    """

    def __init__(
        self,
        strategy_id: str,
        fixed_signal: str = "long",
        confidence: float = 0.5,
        tp: float = 0.01,
        sl: float = 0.005,
        holding_time_seconds: int = 3600,
    ) -> None:
        self._strategy_id = strategy_id
        self._fixed_signal = fixed_signal
        self._confidence = confidence
        self._tp = tp
        self._sl = sl
        self._holding_time_seconds = holding_time_seconds

    def evaluate(
        self,
        instrument: str,
        features: FeatureSet,
        context: StrategyContext,
    ) -> StrategySignal:
        """Return a fixed signal regardless of features."""
        ev_before = self._confidence * self._tp - (1 - self._confidence) * self._sl
        return StrategySignal(
            strategy_id=self._strategy_id,
            strategy_type=_STRATEGY_TYPE,
            strategy_version=_STRATEGY_VERSION,
            signal=self._fixed_signal,
            confidence=self._confidence,
            ev_before_cost=round(ev_before, 8),
            ev_after_cost=round(ev_before, 8),
            tp=self._tp,
            sl=self._sl,
            holding_time_seconds=self._holding_time_seconds,
            enabled=True,
        )
