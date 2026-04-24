"""RSIStrategy — RSI-14 mean-reversion strategy (Phase 9.4).

Signal logic:
  - rsi_14 <= oversold_threshold (default 30) → 'long'   (oversold → revert up)
  - rsi_14 >= overbought_threshold (default 70) → 'short' (overbought → revert down)
  - Otherwise → 'no_trade'

Confidence: normalised distance from the threshold.
  long:  (oversold_threshold - rsi_14) / oversold_threshold  (capped at 1.0)
  short: (rsi_14 - overbought_threshold) / (100 - overbought_threshold)

Invariants:
  - Pure functional: no DB access, no random, no clock.
  - feature_stats key 'rsi_14' must be present; defaults to 50.0 (no_trade).
  - ev_after_cost = ev_before_cost (placeholder; EVEstimator corrects later).
"""

from __future__ import annotations

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal

_STRATEGY_TYPE = "rsi_reversion"
_STRATEGY_VERSION = "v1"


class RSIStrategy:
    """RSI-14 mean-reversion strategy.

    Args:
        strategy_id: Unique ID for this strategy instance.
        oversold_threshold: RSI level below which to go long (default 30).
        overbought_threshold: RSI level above which to go short (default 70).
        tp_atr_multiplier: TP = atr_14 * multiplier (default 1.5).
        sl_atr_multiplier: SL = atr_14 * multiplier (default 1.0).
        holding_time_seconds: Expected holding duration.
    """

    def __init__(
        self,
        strategy_id: str,
        oversold_threshold: float = 30.0,
        overbought_threshold: float = 70.0,
        tp_atr_multiplier: float = 1.5,
        sl_atr_multiplier: float = 1.0,
        holding_time_seconds: int = 3600,
    ) -> None:
        self._strategy_id = strategy_id
        self._oversold = oversold_threshold
        self._overbought = overbought_threshold
        self._tp_mult = tp_atr_multiplier
        self._sl_mult = sl_atr_multiplier
        self._holding_time_seconds = holding_time_seconds

    def evaluate(
        self,
        instrument: str,
        features: FeatureSet,
        context: StrategyContext,
    ) -> StrategySignal:
        """Generate a signal from RSI-14."""
        stats = features.feature_stats
        rsi: float = stats.get("rsi_14", 50.0)
        atr: float = stats.get("atr_14", 0.0)

        if rsi <= self._oversold:
            signal = "long"
            confidence = min((self._oversold - rsi) / self._oversold, 1.0)
        elif rsi >= self._overbought:
            signal = "short"
            confidence = min((rsi - self._overbought) / (100.0 - self._overbought), 1.0)
        else:
            signal = "no_trade"
            confidence = 0.0

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
