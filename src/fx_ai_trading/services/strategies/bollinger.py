"""BollingerStrategy — Bollinger Bands(20, 2σ) mean-reversion strategy (Phase 9.4).

Signal logic (mean-reversion):
  - bb_pct_b <= lower_threshold (default 0.05) → 'long'   (near lower band → revert up)
  - bb_pct_b >= upper_threshold (default 0.95) → 'short'  (near upper band → revert down)
  - Otherwise → 'no_trade'

%B = (close - lower_band) / (upper_band - lower_band)
  0.0 = at lower band, 1.0 = at upper band, 0.5 = at middle.

Confidence:
  long:  (lower_threshold - bb_pct_b) / lower_threshold  (capped at 1.0)
  short: (bb_pct_b - upper_threshold) / (1.0 - upper_threshold)

Invariants:
  - Pure functional: no DB access, no random, no clock.
  - feature_stats keys 'bb_pct_b', 'atr_14' must be present; defaults to 0.5 / 0.0.
  - ev_after_cost = ev_before_cost (placeholder; EVEstimator corrects later).
"""

from __future__ import annotations

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal

_STRATEGY_TYPE = "bollinger_reversion"
_STRATEGY_VERSION = "v1"


class BollingerStrategy:
    """Bollinger Bands(20, 2σ) mean-reversion strategy.

    Args:
        strategy_id: Unique ID for this strategy instance.
        lower_threshold: %B below which to go long (default 0.05).
        upper_threshold: %B above which to go short (default 0.95).
        tp_atr_multiplier: TP = atr_14 * multiplier (default 1.5).
        sl_atr_multiplier: SL = atr_14 * multiplier (default 0.75).
        holding_time_seconds: Expected holding duration.
    """

    def __init__(
        self,
        strategy_id: str,
        lower_threshold: float = 0.05,
        upper_threshold: float = 0.95,
        tp_atr_multiplier: float = 1.5,
        sl_atr_multiplier: float = 0.75,
        holding_time_seconds: int = 3600,
    ) -> None:
        self._strategy_id = strategy_id
        self._lower = lower_threshold
        self._upper = upper_threshold
        self._tp_mult = tp_atr_multiplier
        self._sl_mult = sl_atr_multiplier
        self._holding_time_seconds = holding_time_seconds

    def evaluate(
        self,
        instrument: str,
        features: FeatureSet,
        context: StrategyContext,
    ) -> StrategySignal:
        """Generate a signal from Bollinger %B."""
        stats = features.feature_stats
        pct_b: float = stats.get("bb_pct_b", 0.5)
        atr: float = stats.get("atr_14", 0.0)

        if pct_b <= self._lower:
            signal = "long"
            confidence = min((self._lower - pct_b) / self._lower if self._lower > 0 else 1.0, 1.0)
        elif pct_b >= self._upper:
            signal = "short"
            denom = 1.0 - self._upper
            confidence = min((pct_b - self._upper) / denom if denom > 0 else 1.0, 1.0)
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
