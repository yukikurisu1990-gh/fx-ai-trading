"""MAStrategy — moving-average crossover strategy (D3 §2.4.1 / M9).

Signal logic:
  - sma_20 > sma_50 → 'long'
  - sma_20 < sma_50 → 'short'
  - sma_20 == sma_50 (or sma_50 == 0) → 'no_trade'

Confidence: min(|sma_20 - sma_50| / sma_50, 1.0) — normalized divergence.

Invariants:
  - Pure functional: no DB access, no random, no clock.
  - ev_after_cost = ev_before_cost (placeholder; EVEstimator corrects later).
  - feature_stats keys 'sma_20', 'sma_50', 'atr_14' must be present; defaults to 0.
"""

from __future__ import annotations

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal

_STRATEGY_TYPE = "ma_crossover"
_STRATEGY_VERSION = "v1"


class MAStrategy:
    """Moving-average crossover strategy (SMA20 / SMA50).

    Args:
        strategy_id: Unique ID for this strategy instance.
        tp_atr_multiplier: TP = atr_14 * multiplier (default 2.0).
        sl_atr_multiplier: SL = atr_14 * multiplier (default 1.0).
        holding_time_seconds: Expected holding duration.
    """

    def __init__(
        self,
        strategy_id: str,
        tp_atr_multiplier: float = 2.0,
        sl_atr_multiplier: float = 1.0,
        holding_time_seconds: int = 3600,
    ) -> None:
        self._strategy_id = strategy_id
        self._tp_mult = tp_atr_multiplier
        self._sl_mult = sl_atr_multiplier
        self._holding_time_seconds = holding_time_seconds

    def evaluate(
        self,
        instrument: str,
        features: FeatureSet,
        context: StrategyContext,
    ) -> StrategySignal:
        """Generate a signal from SMA20/SMA50 crossover."""
        stats = features.feature_stats
        sma_20: float = stats.get("sma_20", 0.0)
        sma_50: float = stats.get("sma_50", 0.0)
        atr_14: float = stats.get("atr_14", 0.0)

        if sma_50 == 0.0 or sma_20 == sma_50:
            signal = "no_trade"
            confidence = 0.0
        elif sma_20 > sma_50:
            signal = "long"
            confidence = min((sma_20 - sma_50) / sma_50, 1.0)
        else:
            signal = "short"
            confidence = min((sma_50 - sma_20) / sma_50, 1.0)

        tp = atr_14 * self._tp_mult if atr_14 > 0 else 0.01
        sl = atr_14 * self._sl_mult if atr_14 > 0 else 0.005

        ev_before = confidence * tp - (1 - confidence) * sl if signal != "no_trade" else 0.0
        return StrategySignal(
            strategy_id=self._strategy_id,
            strategy_type=_STRATEGY_TYPE,
            strategy_version=_STRATEGY_VERSION,
            signal=signal,
            confidence=round(confidence, 8),
            ev_before_cost=round(ev_before, 8),
            ev_after_cost=round(ev_before, 8),
            tp=round(tp, 8),
            sl=round(sl, 8),
            holding_time_seconds=self._holding_time_seconds,
            enabled=True,
        )
