"""MeanReversionStrategy — combined RSI/Bollinger mean-reversion (Phase 9.17 G-1).

Signal logic (require BOTH RSI and Bollinger to agree):
  - rsi_14 <= rsi_oversold AND bb_pct_b <= bb_lower
        → 'long'   (both signals say oversold → revert up)
  - rsi_14 >= rsi_overbought AND bb_pct_b >= bb_upper
        → 'short'  (both signals say overbought → revert down)
  - Otherwise → 'no_trade'

Why combined-AND vs Phase 9.4 single-indicator strategies:
  - Single RSI/Bollinger strategies fire on common setups that LightGBM
    likely already captures via its 15-feature set (rsi_14, bb_pct_b,
    macd, ema, etc. all present in the model's feature space).
  - Requiring BOTH extremes to agree filters down to the *strongest*
    mean-reversion setups, which (a) reduces trade count, (b) increases
    per-trade quality, and (c) targets the regime where LightGBM's
    trend-coded signal is most reluctant — improving orthogonality.

Confidence:
  - long:  mean of (rsi_long_conf, bb_long_conf)
  - short: mean of (rsi_short_conf, bb_short_conf)
  - 'no_trade' → 0.0

Phase 9.17b: confidence_threshold post-filter.
  - When confidence < threshold AFTER it would otherwise be a signal,
    the trade is suppressed (signal becomes 'no_trade', confidence 0.0).
  - Default 0.0 preserves Phase 9.17 behavior. Closure memo §5
    identified MR's lack of LGBM-style threshold as the cause of trade-
    rate explosion (15× higher than LGBM).

TP/SL: 1.5 / 1.0 × ATR by default — matches LightGBM triple-barrier
baseline so PnL is directly comparable in the v13 ensemble eval.

Invariants:
  - Pure functional: no DB access, no random, no clock.
  - feature_stats keys 'rsi_14', 'bb_pct_b', 'atr_14' must be present;
    defaults 50.0 / 0.5 / 0.0 mean 'no_trade'.
  - ev_after_cost = ev_before_cost (placeholder; EVEstimator corrects later).
"""

from __future__ import annotations

from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategySignal

_STRATEGY_TYPE = "mean_reversion"
_STRATEGY_VERSION = "v1"


class MeanReversionStrategy:
    """Combined RSI/Bollinger mean-reversion strategy.

    Phase 9.17 G-1; confidence_threshold added in 9.17b/I-1.

    Args:
        strategy_id: Unique ID for this strategy instance.
        rsi_oversold: RSI level below which oversold (default 30.0).
        rsi_overbought: RSI level above which overbought (default 70.0).
        bb_lower: %B level below which lower-band touch (default 0.10).
        bb_upper: %B level above which upper-band touch (default 0.90).
        confidence_threshold: Minimum mean(rsi_conf, bb_conf) required to
            emit a signal. Trades below this are suppressed to 'no_trade'.
            Default 0.0 preserves Phase 9.17 G-1 behavior.
        tp_atr_multiplier: TP = atr_14 * multiplier (default 1.5).
        sl_atr_multiplier: SL = atr_14 * multiplier (default 1.0).
        holding_time_seconds: Expected holding duration.
    """

    def __init__(
        self,
        strategy_id: str,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        bb_lower: float = 0.10,
        bb_upper: float = 0.90,
        confidence_threshold: float = 0.0,
        tp_atr_multiplier: float = 1.5,
        sl_atr_multiplier: float = 1.0,
        holding_time_seconds: int = 3600,
    ) -> None:
        self._strategy_id = strategy_id
        self._rsi_oversold = rsi_oversold
        self._rsi_overbought = rsi_overbought
        self._bb_lower = bb_lower
        self._bb_upper = bb_upper
        self._conf_threshold = confidence_threshold
        self._tp_mult = tp_atr_multiplier
        self._sl_mult = sl_atr_multiplier
        self._holding_time_seconds = holding_time_seconds

    def evaluate(
        self,
        instrument: str,
        features: FeatureSet,
        context: StrategyContext,
    ) -> StrategySignal:
        """Generate a signal from combined RSI + Bollinger %B."""
        stats = features.feature_stats
        rsi: float = stats.get("rsi_14", 50.0)
        pct_b: float = stats.get("bb_pct_b", 0.5)
        atr: float = stats.get("atr_14", 0.0)

        long_ok = rsi <= self._rsi_oversold and pct_b <= self._bb_lower
        short_ok = rsi >= self._rsi_overbought and pct_b >= self._bb_upper

        if long_ok:
            signal = "long"
            rsi_conf = (
                min((self._rsi_oversold - rsi) / self._rsi_oversold, 1.0)
                if self._rsi_oversold > 0
                else 1.0
            )
            bb_conf = (
                min((self._bb_lower - pct_b) / self._bb_lower, 1.0) if self._bb_lower > 0 else 1.0
            )
            confidence = (rsi_conf + bb_conf) / 2.0
        elif short_ok:
            signal = "short"
            rsi_denom = 100.0 - self._rsi_overbought
            bb_denom = 1.0 - self._bb_upper
            rsi_conf = min((rsi - self._rsi_overbought) / rsi_denom, 1.0) if rsi_denom > 0 else 1.0
            bb_conf = min((pct_b - self._bb_upper) / bb_denom, 1.0) if bb_denom > 0 else 1.0
            confidence = (rsi_conf + bb_conf) / 2.0
        else:
            signal = "no_trade"
            confidence = 0.0

        if signal != "no_trade" and confidence < self._conf_threshold:
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
