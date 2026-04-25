"""BreakoutStrategy — Bollinger range-exit follow with EMA trend confirmation (Phase 9.17 G-2).

Signal logic (require BOTH range break AND trend confirmation):
  - last_close > bb_upper AND ema_12 > ema_26
        → 'long'   (upper-band break in uptrend → follow the move)
  - last_close < bb_lower AND ema_12 < ema_26
        → 'short'  (lower-band break in downtrend → follow the move)
  - Otherwise → 'no_trade'

Why range-break + trend-confirmation vs simple band-touch:
  - Phase 9.17's orthogonality requirement (design memo §3, §4): the
    strategy must fire in regimes where LightGBM's signal is reluctant.
  - Pure band-break without trend filter has high false-breakout rate
    in chop and overlaps with mean-reversion setups (the same band
    edges).
  - EMA-trend confirmation gates breakout to *post-consolidation*
    follow-through: range broken + trend already established → high
    probability of continuation, low probability that LightGBM's
    confidence-saturated signal already captured the move.

Confidence: ATR-normalized distance from the broken band.
  - long:  (last_close - bb_upper) / atr_14, capped at 1.0 at full_atr
  - short: (bb_lower - last_close) / atr_14, capped at 1.0 at full_atr
  - 'no_trade' → 0.0

Default `breakout_strength_full_atr=0.5`: a 0.5×ATR push beyond the
band yields full confidence. Smaller breaks scale linearly down.

TP/SL: 1.5 / 1.0 × ATR by default — matches LightGBM triple-barrier
baseline for ensemble PnL comparability (design memo §13 default 4).

Invariants:
  - Pure functional: no DB access, no random, no clock.
  - feature_stats keys 'last_close', 'bb_upper', 'bb_lower',
    'ema_12', 'ema_26', 'atr_14' must be present; defaults give
    'no_trade'.
  - ev_after_cost = ev_before_cost (placeholder; EVEstimator corrects later).
"""

from __future__ import annotations

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal

_STRATEGY_TYPE = "breakout"
_STRATEGY_VERSION = "v1"


class BreakoutStrategy:
    """Bollinger range-exit + EMA trend-confirmed breakout strategy (Phase 9.17 G-2).

    Args:
        strategy_id: Unique ID for this strategy instance.
        breakout_strength_full_atr: ATR multiples beyond the band that
            saturate confidence to 1.0 (default 0.5).
        tp_atr_multiplier: TP = atr_14 * multiplier (default 1.5).
        sl_atr_multiplier: SL = atr_14 * multiplier (default 1.0).
        holding_time_seconds: Expected holding duration.
    """

    def __init__(
        self,
        strategy_id: str,
        breakout_strength_full_atr: float = 0.5,
        tp_atr_multiplier: float = 1.5,
        sl_atr_multiplier: float = 1.0,
        holding_time_seconds: int = 3600,
    ) -> None:
        self._strategy_id = strategy_id
        self._strength_full = breakout_strength_full_atr
        self._tp_mult = tp_atr_multiplier
        self._sl_mult = sl_atr_multiplier
        self._holding_time_seconds = holding_time_seconds

    def evaluate(
        self,
        instrument: str,
        features: FeatureSet,
        context: StrategyContext,
    ) -> StrategySignal:
        """Generate a signal from band-break + EMA trend confirmation."""
        stats = features.feature_stats
        close: float = stats.get("last_close", 0.0)
        bb_upper: float = stats.get("bb_upper", close)
        bb_lower: float = stats.get("bb_lower", close)
        ema_12: float = stats.get("ema_12", 0.0)
        ema_26: float = stats.get("ema_26", 0.0)
        atr: float = stats.get("atr_14", 0.0)

        long_break = close > bb_upper
        short_break = close < bb_lower
        trend_up = ema_12 > ema_26
        trend_down = ema_12 < ema_26

        if long_break and trend_up and atr > 0.0:
            signal = "long"
            strength = (close - bb_upper) / atr
            confidence = (
                min(strength / self._strength_full, 1.0) if self._strength_full > 0 else 1.0
            )
        elif short_break and trend_down and atr > 0.0:
            signal = "short"
            strength = (bb_lower - close) / atr
            confidence = (
                min(strength / self._strength_full, 1.0) if self._strength_full > 0 else 1.0
            )
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
