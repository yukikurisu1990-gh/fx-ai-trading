"""ATRStrategy — ATR-based directional strategy (D3 §2.4.1 / M9).

Signal logic:
  - If atr_14 == 0 → 'no_trade' (no price movement data).
  - last_close > sma_20 → 'long'
  - last_close < sma_20 → 'short'
  - last_close == sma_20 → 'no_trade'

Confidence: min(|last_close - sma_20| / atr_14 * 0.1, 1.0)
  — distance from mean relative to volatility, scaled by 0.1.

Invariants:
  - Pure functional: no DB access, no random, no clock.
  - ev_after_cost = ev_before_cost (placeholder; EVEstimator corrects later).
"""

from __future__ import annotations

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal

_STRATEGY_TYPE = "atr_directional"
_STRATEGY_VERSION = "v1"


class ATRStrategy:
    """ATR-based directional strategy.

    Args:
        strategy_id: Unique ID for this strategy instance.
        tp_atr_multiplier: TP = atr_14 * multiplier (default 2.0).
        sl_atr_multiplier: SL = atr_14 * multiplier (default 1.0).
        confidence_scale: Scales confidence = distance/ATR * scale (default 0.1).
        holding_time_seconds: Expected holding duration.
    """

    def __init__(
        self,
        strategy_id: str,
        tp_atr_multiplier: float = 2.0,
        sl_atr_multiplier: float = 1.0,
        confidence_scale: float = 0.1,
        holding_time_seconds: int = 1800,
    ) -> None:
        self._strategy_id = strategy_id
        self._tp_mult = tp_atr_multiplier
        self._sl_mult = sl_atr_multiplier
        self._confidence_scale = confidence_scale
        self._holding_time_seconds = holding_time_seconds

    def evaluate(
        self,
        instrument: str,
        features: FeatureSet,
        context: StrategyContext,
    ) -> StrategySignal:
        """Generate a signal based on ATR-relative price position."""
        stats = features.feature_stats
        atr_14: float = stats.get("atr_14", 0.0)
        last_close: float = stats.get("last_close", 0.0)
        sma_20: float = stats.get("sma_20", 0.0)

        if atr_14 == 0.0:
            return StrategySignal(
                strategy_id=self._strategy_id,
                strategy_type=_STRATEGY_TYPE,
                strategy_version=_STRATEGY_VERSION,
                signal="no_trade",
                confidence=0.0,
                ev_before_cost=0.0,
                ev_after_cost=0.0,
                tp=0.0,
                sl=0.0,
                holding_time_seconds=self._holding_time_seconds,
                enabled=True,
            )

        if last_close > sma_20:
            signal = "long"
        elif last_close < sma_20:
            signal = "short"
        else:
            signal = "no_trade"

        distance = abs(last_close - sma_20)
        confidence = (
            min(distance / atr_14 * self._confidence_scale, 1.0) if signal != "no_trade" else 0.0
        )

        tp = atr_14 * self._tp_mult
        sl = atr_14 * self._sl_mult
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
