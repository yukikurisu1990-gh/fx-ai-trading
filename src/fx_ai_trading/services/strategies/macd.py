"""MACDStrategy — MACD(12,26,9) trend-following strategy (Phase 9.4).

Signal logic:
  - macd_histogram > 0 AND macd_line > macd_signal → 'long'  (bullish crossover)
  - macd_histogram < 0 AND macd_line < macd_signal → 'short' (bearish crossover)
  - Otherwise → 'no_trade'

Confidence: |macd_histogram| / (|macd_line| + epsilon), capped at 1.0.
  Measures how far the histogram is relative to the MACD magnitude.

Invariants:
  - Pure functional: no DB access, no random, no clock.
  - feature_stats keys 'macd_line', 'macd_signal', 'macd_histogram' must be present.
  - ev_after_cost = ev_before_cost (placeholder; EVEstimator corrects later).
"""

from __future__ import annotations

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal

_STRATEGY_TYPE = "macd_trend"
_STRATEGY_VERSION = "v1"
_EPSILON = 1e-10


class MACDStrategy:
    """MACD(12,26,9) trend-following strategy.

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
        holding_time_seconds: int = 7200,
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
        """Generate a signal from MACD histogram."""
        stats = features.feature_stats
        macd_line: float = stats.get("macd_line", 0.0)
        macd_signal: float = stats.get("macd_signal", 0.0)
        macd_histogram: float = stats.get("macd_histogram", 0.0)
        atr: float = stats.get("atr_14", 0.0)

        if macd_histogram > 0 and macd_line > macd_signal:
            signal = "long"
        elif macd_histogram < 0 and macd_line < macd_signal:
            signal = "short"
        else:
            signal = "no_trade"

        confidence = 0.0
        if signal != "no_trade":
            confidence = min(abs(macd_histogram) / (abs(macd_line) + _EPSILON), 1.0)

        tp = atr * self._tp_mult
        sl = atr * self._sl_mult
        ev = tp * confidence * 0.5 if signal != "no_trade" else 0.0

        return StrategySignal(
            strategy_id=self._strategy_id,
            strategy_type=_STRATEGY_TYPE,
            strategy_version=_STRATEGY_VERSION,
            signal=signal,
            confidence=round(confidence, 6),
            ev_before_cost=round(ev, 8),
            ev_after_cost=round(ev, 8),
            tp=round(tp, 8),
            sl=round(sl, 8),
            holding_time_seconds=self._holding_time_seconds,
            enabled=True,
        )
