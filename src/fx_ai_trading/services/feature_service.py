"""FeatureService — deterministic feature computation (D3 §2.2.1 / M9).

Implements the FeatureBuilder Protocol.

Determinism invariants (6.10):
  - FEATURE_VERSION is a module constant — change it when feature logic changes.
  - feature_hash = SHA256[:16] of canonical JSON (sort_keys=True, values rounded to 8dp).
  - No datetime.now() — computed_at is set to as_of_time.
  - No unfixed random state.

No-lookahead invariant:
  - get_candles callable is called with (instrument, as_of_time).
  - build() filters the result again: timestamp < as_of_time (strict).
  - Future data cannot affect feature_stats or feature_hash.

Phase 9.4 additions:
  - ema_12, ema_26: EMA for MACD computation.
  - macd_line, macd_signal, macd_histogram: MACD(12, 26, 9).
  - rsi_14: RSI over 14 bars.
  - bb_upper, bb_middle, bb_lower, bb_pct_b, bb_width: Bollinger Bands(20, 2σ).

Phase 9.X-B/J-5 additions (opt-in via enable_groups):
  - Group "mtf" (multi-timeframe extension): h4_atr_14, d1_return_3,
    d1_range_pct, d1_atr_14, w1_return_1, w1_range_pct. Backtest-validated
    Sharpe 0.174 / PnL 1.85x baseline at K=3 (Phase 9.X-B closure memo).
  - Activating mtf bumps FEATURE_VERSION v2 → v3 (schema change).
  - mtf requires ≥ 7 days of history (~2,016 m5 bars for weekly stats);
    callers must size the rolling buffer accordingly.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from fx_ai_trading.domain.feature import FeatureSet

# Bump this constant when feature computation logic changes.
# v3 (2026-04-26) — Phase 9.X-B/J-5: opt-in mtf feature group.
#                    Phase 9.X-B amendment: opt-in vol feature group also added.
# When enable_groups is empty, behaviour identical to v2; the version stays
# v3 because adding a new opt-in group does not change the default schema.
# FeatureService(enable_groups=frozenset({"mtf"})) or frozenset({"vol"}).
FEATURE_VERSION = "v3"

# Phase 9.X-B/J-5: opt-in feature groups.
# - "mtf"  — multi-timeframe extension (4h / daily / weekly stats)
# - "vol"  — volatility-clustering features (GARCH-like dynamics)
ENABLE_GROUPS_DEFAULT: frozenset[str] = frozenset()
_VALID_GROUPS: frozenset[str] = frozenset({"mtf", "vol"})


class FeatureService:
    """Deterministic FeatureBuilder implementation for M9/Phase 9.4.

    Args:
        get_candles: Callable(instrument, as_of_time) → list of candle dicts.
            Each candle must have keys: timestamp (datetime), open, high, low,
            close (float), volume (float).
            May include data up to or past as_of_time; build() will filter.
        enable_groups: Phase 9.X-B/J-5 opt-in feature groups. Currently
            supports "mtf" (multi-timeframe extension: 4h/daily/weekly stats).
            Default empty preserves Phase 9.16 baseline behaviour.
    """

    def __init__(
        self,
        get_candles: Callable[[str, datetime], list[dict]],
        enable_groups: frozenset[str] = ENABLE_GROUPS_DEFAULT,
    ) -> None:
        self._get_candles = get_candles
        invalid = enable_groups - _VALID_GROUPS
        if invalid:
            raise ValueError(
                f"FeatureService: invalid feature group(s) {sorted(invalid)} "
                f"(valid: {sorted(_VALID_GROUPS)})"
            )
        self._enable_groups = enable_groups

    def get_feature_version(self) -> str:
        """Return the deterministic feature version string (6.10)."""
        return FEATURE_VERSION

    def build(
        self,
        instrument: str,
        tier: str,
        cycle_id: UUID,
        as_of_time: datetime,
    ) -> FeatureSet:
        """Compute and return features strictly as of *as_of_time*.

        No data at or after as_of_time is included (no-lookahead invariant).
        Same inputs + FEATURE_VERSION → byte-equal feature_hash (determinism invariant).

        Returns:
            FeatureSet with feature_version, feature_hash, and computed statistics.
        """
        raw_candles = self._get_candles(instrument, as_of_time)

        # Strict no-lookahead: exclude candles at or after as_of_time
        candles = [c for c in raw_candles if c["timestamp"] < as_of_time]

        feature_stats = _compute_features(candles)
        if "mtf" in self._enable_groups:
            feature_stats.update(_compute_mtf_features(candles))
        if "vol" in self._enable_groups:
            feature_stats.update(_compute_vol_features(candles))
        feature_hash = _hash_features(feature_stats)

        return FeatureSet(
            feature_version=FEATURE_VERSION,
            feature_hash=feature_hash,
            feature_stats=feature_stats,
            sampled_features=feature_stats,
            computed_at=as_of_time,
        )


# ---------------------------------------------------------------------------
# Internal helpers (pure functions, no side effects)
# ---------------------------------------------------------------------------

_ZERO_FEATURES: dict[str, float] = {
    "atr_14": 0.0,
    "bb_lower": 0.0,
    "bb_middle": 0.0,
    "bb_pct_b": 0.0,
    "bb_upper": 0.0,
    "bb_width": 0.0,
    "ema_12": 0.0,
    "ema_26": 0.0,
    "last_close": 0.0,
    "macd_histogram": 0.0,
    "macd_line": 0.0,
    "macd_signal": 0.0,
    "rsi_14": 0.0,
    "sma_20": 0.0,
    "sma_50": 0.0,
}


def _compute_features(candles: list[dict]) -> dict:
    """Compute deterministic feature_stats from *candles*.

    Returns a dict with float values rounded to 8 decimal places for hash stability.
    All keys are always present (zero/neutral defaults when data is insufficient).
    """
    if not candles:
        return dict(_ZERO_FEATURES)

    closes = [c["close"] for c in candles]

    sma_20 = _sma(closes, 20)
    sma_50 = _sma(closes, 50)
    atr_14 = _atr(candles, 14)
    last_close = closes[-1]

    ema_12 = _ema(closes, 12)
    ema_26 = _ema(closes, 26)
    macd_line, macd_signal, macd_histogram = _macd(closes, 12, 26, 9)

    rsi_14 = _rsi(closes, 14)

    bb_upper, bb_middle, bb_lower = _bollinger(closes, 20, 2.0)
    bb_width = (bb_upper - bb_lower) / bb_middle if bb_middle != 0.0 else 0.0
    bb_range = bb_upper - bb_lower
    bb_pct_b = (last_close - bb_lower) / bb_range if bb_range != 0.0 else 0.5

    return {
        "atr_14": round(atr_14, 8),
        "bb_lower": round(bb_lower, 8),
        "bb_middle": round(bb_middle, 8),
        "bb_pct_b": round(bb_pct_b, 8),
        "bb_upper": round(bb_upper, 8),
        "bb_width": round(bb_width, 8),
        "ema_12": round(ema_12, 8),
        "ema_26": round(ema_26, 8),
        "last_close": round(last_close, 8),
        "macd_histogram": round(macd_histogram, 8),
        "macd_line": round(macd_line, 8),
        "macd_signal": round(macd_signal, 8),
        "rsi_14": round(rsi_14, 8),
        "sma_20": round(sma_20, 8),
        "sma_50": round(sma_50, 8),
    }


def compute_features_from_candles(candles: list[dict]) -> dict[str, float]:
    """Public entry point for batch feature computation (Phase 9.5 feature store).

    Computes features from *all* candles in the list with no time filtering.
    Callers are responsible for passing only candles up to (and including)
    the bar of interest to preserve the no-lookahead invariant.

    Args:
        candles: List of candle dicts with keys: timestamp, open, high, low,
            close (float), volume (float).

    Returns:
        Dict with all feature keys (float values rounded to 8 dp).
    """
    return _compute_features(candles)


def _sma(values: list[float], period: int) -> float:
    """Simple moving average of the last *period* values."""
    if not values:
        return 0.0
    window = values[-period:] if len(values) >= period else values
    return sum(window) / len(window)


def _ema(values: list[float], period: int) -> float:
    """Exponential moving average (Wilder-style seed from SMA of first window).

    Uses alpha = 2 / (period + 1).  Returns 0.0 if values is empty.
    """
    if not values:
        return 0.0
    alpha = 2.0 / (period + 1)
    # Seed from SMA of first min(period, len) values.
    seed_window = values[:period] if len(values) >= period else values
    ema = sum(seed_window) / len(seed_window)
    # Apply EMA from the point after the seed window.
    for price in values[len(seed_window) :]:
        ema = alpha * price + (1 - alpha) * ema
    return ema


def _macd(
    closes: list[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[float, float, float]:
    """Return (macd_line, signal_line, histogram).

    All zeros when insufficient data.
    """
    if len(closes) < slow:
        return 0.0, 0.0, 0.0

    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = ema_fast - ema_slow

    # Compute rolling MACD values for signal EMA.
    macd_values: list[float] = []
    for i in range(slow, len(closes) + 1):
        window = closes[:i]
        ef = _ema(window, fast)
        es = _ema(window, slow)
        macd_values.append(ef - es)

    if not macd_values:
        return macd_line, 0.0, macd_line

    signal_line = _ema(macd_values, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _rsi(closes: list[float], period: int = 14) -> float:
    """Wilder RSI over the last *period* bars.  Returns 50.0 if insufficient data."""
    if len(closes) < 2:
        return 50.0

    changes = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(c, 0.0) for c in changes]
    losses = [abs(min(c, 0.0)) for c in changes]

    if len(gains) < period:
        avg_gain = sum(gains) / len(gains) if gains else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
    else:
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0.0:
        return 100.0 if avg_gain > 0.0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def _bollinger(
    closes: list[float],
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[float, float, float]:
    """Return (upper_band, middle_band, lower_band).

    middle = SMA(period), upper/lower = middle ± num_std * std(period).
    Returns (0, 0, 0) if insufficient data.
    """
    if not closes:
        return 0.0, 0.0, 0.0
    window = closes[-period:] if len(closes) >= period else closes
    middle = sum(window) / len(window)
    variance = sum((x - middle) ** 2 for x in window) / len(window)
    std = math.sqrt(variance)
    upper = middle + num_std * std
    lower = middle - num_std * std
    return upper, middle, lower


def _atr(candles: list[dict], period: int) -> float:
    """Average True Range over the last *period* bars."""
    if len(candles) < 2:
        if candles:
            return candles[0]["high"] - candles[0]["low"]
        return 0.0

    true_ranges: list[float] = []
    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)

    window = true_ranges[-period:] if len(true_ranges) >= period else true_ranges
    return sum(window) / len(window)


# ---------------------------------------------------------------------------
# Phase 9.X-B/J-5 mtf feature group (opt-in).
# ---------------------------------------------------------------------------

_MTF_ZERO_FEATURES: dict[str, float] = {
    "h4_atr_14": 0.0,
    "d1_return_3": 0.0,
    "d1_range_pct": 0.0,
    "d1_atr_14": 0.0,
    "w1_return_1": 0.0,
    "w1_range_pct": 0.0,
}


def _compute_mtf_features(candles: list[dict]) -> dict[str, float]:
    """Phase 9.X-B/J-5 — multi-timeframe extension (4h / daily / weekly).

    Resamples the m5 input candles to 4h, daily, and weekly bars, then
    computes ATR(14) on 4h, return-3 / range-pct / ATR(14) on daily,
    return-1 / range-pct on weekly.

    Pure function. No-lookahead preserved (candles already filtered by
    build() to timestamp < as_of_time before this is called).

    All-zero output if insufficient history (e.g., fewer than 14 daily
    bars to compute ATR).
    """
    if not candles:
        return dict(_MTF_ZERO_FEATURES)

    # Resampling buckets keyed by (year, month, day, hour-bucket).
    h4_bars = _resample_ohlc(candles, _h4_bucket)
    d1_bars = _resample_ohlc(candles, _d1_bucket)
    w1_bars = _resample_ohlc(candles, _w1_bucket)

    h4_atr_14 = _atr_from_bars(h4_bars, 14)
    d1_atr_14 = _atr_from_bars(d1_bars, 14)
    d1_return_3 = _return_at_lag(d1_bars, 3)
    d1_range_pct = _range_pct_last(d1_bars)
    w1_return_1 = _return_at_lag(w1_bars, 1)
    w1_range_pct = _range_pct_last(w1_bars)

    return {
        "h4_atr_14": round(h4_atr_14, 8),
        "d1_return_3": round(d1_return_3, 8),
        "d1_range_pct": round(d1_range_pct, 8),
        "d1_atr_14": round(d1_atr_14, 8),
        "w1_return_1": round(w1_return_1, 8),
        "w1_range_pct": round(w1_range_pct, 8),
    }


def _h4_bucket(ts: datetime) -> tuple[int, int, int, int]:
    """4-hour bucket key — UTC-aligned at 0/4/8/12/16/20."""
    return (ts.year, ts.month, ts.day, (ts.hour // 4) * 4)


def _d1_bucket(ts: datetime) -> tuple[int, int, int]:
    """Daily bucket key — UTC midnight aligned."""
    return (ts.year, ts.month, ts.day)


def _w1_bucket(ts: datetime) -> tuple[int, int]:
    """ISO-calendar week bucket — (iso_year, iso_week)."""
    iso_year, iso_week, _iso_weekday = ts.isocalendar()
    return (iso_year, iso_week)


def _resample_ohlc(candles: list[dict], bucket_fn: Callable[[datetime], tuple]) -> list[dict]:
    """Resample m5 OHLC to a coarser cadence using `bucket_fn(timestamp)`.

    Each output bar takes:
      open  — first candle's open in the bucket
      high  — max of all highs
      low   — min of all lows
      close — last candle's close in the bucket
    Bars are returned in chronological order.
    """
    buckets: dict[tuple, dict] = {}
    bucket_order: list[tuple] = []
    for c in candles:
        key = bucket_fn(c["timestamp"])
        if key not in buckets:
            buckets[key] = {
                "open": c["open"],
                "high": c["high"],
                "low": c["low"],
                "close": c["close"],
            }
            bucket_order.append(key)
        else:
            b = buckets[key]
            b["high"] = max(b["high"], c["high"])
            b["low"] = min(b["low"], c["low"])
            b["close"] = c["close"]  # candles arrive in time order; last wins
    return [buckets[k] for k in bucket_order]


def _atr_from_bars(bars: list[dict], period: int) -> float:
    """ATR over the last *period* bars."""
    if len(bars) < 2:
        if bars:
            return bars[0]["high"] - bars[0]["low"]
        return 0.0
    true_ranges: list[float] = []
    for i in range(1, len(bars)):
        h = bars[i]["high"]
        lo = bars[i]["low"]
        prev_c = bars[i - 1]["close"]
        true_ranges.append(max(h - lo, abs(h - prev_c), abs(lo - prev_c)))
    window = true_ranges[-period:] if len(true_ranges) >= period else true_ranges
    return sum(window) / len(window)


def _return_at_lag(bars: list[dict], lag: int) -> float:
    """Close-to-close pct change at lag bars. 0.0 if insufficient history."""
    if len(bars) < lag + 1:
        return 0.0
    last = bars[-1]["close"]
    prior = bars[-1 - lag]["close"]
    if prior == 0.0:
        return 0.0
    return (last - prior) / prior


def _range_pct_last(bars: list[dict]) -> float:
    """High-Low range / close for the most recent bar. 0.0 if no data."""
    if not bars:
        return 0.0
    last = bars[-1]
    if last["close"] == 0.0:
        return 0.0
    return (last["high"] - last["low"]) / last["close"]


# ---------------------------------------------------------------------------
# Phase 9.X-B amendment — vol-clustering feature group (opt-in).
# ---------------------------------------------------------------------------

_VOL_ZERO_FEATURES: dict[str, float] = {
    "real_var_5": 0.0,
    "real_var_20": 0.0,
    "vol_of_vol_20": 0.0,
    "var_ratio_5_20": 0.0,
    "ewma_var_30": 0.0,
    "ewma_var_60": 0.0,
}


def _compute_vol_features(candles: list[dict]) -> dict[str, float]:
    """Phase 9.X-B amendment — volatility-clustering features.

    Captures GARCH-like dynamics that the static rolling ATR_14 does not
    encode. All from close-to-close log-returns; OHLC-only.

    - real_var_5 / real_var_20 — sum of squared log-returns.
    - vol_of_vol_20 — rolling std of real_var_5.
    - var_ratio_5_20 — Lo-MacKinlay short/long variance ratio.
    - ewma_var_30 / ewma_var_60 — EWMA of squared log-returns.

    Pure function. No-lookahead preserved (candles already filtered by
    build() to timestamp < as_of_time before this is called).

    All-zero output if insufficient history.
    """
    if not candles or len(candles) < 2:
        return dict(_VOL_ZERO_FEATURES)

    closes = [c["close"] for c in candles]
    log_returns: list[float] = [0.0]  # placeholder for index 0
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        cur = closes[i]
        if prev <= 0.0 or cur <= 0.0:
            log_returns.append(0.0)
        else:
            log_returns.append(math.log(cur / prev))

    # log_return^2 series, skipping the placeholder at index 0.
    sq = [r * r for r in log_returns[1:]]
    if not sq:
        return dict(_VOL_ZERO_FEATURES)

    # Rolling sums of sq over the last N values (N <= len(sq)).
    real_var_5 = sum(sq[-5:]) if len(sq) >= 2 else 0.0
    real_var_20 = sum(sq[-20:]) if len(sq) >= 5 else 0.0

    # vol_of_vol_20: rolling std of the trailing real_var_5 window over
    # the last 20 bars. Compute the rolling rv5 series first.
    rv5_series: list[float] = []
    for end in range(2, len(sq) + 1):  # need at least 2 points for rv5
        start = max(0, end - 5)
        rv5_series.append(sum(sq[start:end]))
    if len(rv5_series) >= 5:
        window = rv5_series[-20:]
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        vol_of_vol_20 = math.sqrt(variance)
    else:
        vol_of_vol_20 = 0.0

    # var_ratio_5_20 = (rv5 / 5) / (rv20 / 20). Requires rv20 > 0.
    var_ratio_5_20 = (real_var_5 / 5.0) / (real_var_20 / 20.0) if real_var_20 > 0.0 else 0.0

    # EWMA of sq with given half-life. min_periods is a soft floor —
    # computed when there's enough series to be statistically meaningful.
    def _ewma(series: list[float], halflife: int, min_periods: int) -> float:
        if len(series) < min_periods:
            return 0.0
        alpha = 1.0 - 0.5 ** (1.0 / halflife)
        ewm = series[0]
        for v in series[1:]:
            ewm = alpha * v + (1.0 - alpha) * ewm
        return ewm

    ewma_var_30 = _ewma(sq, halflife=30, min_periods=10)
    ewma_var_60 = _ewma(sq, halflife=60, min_periods=20)

    return {
        "real_var_5": round(real_var_5, 8),
        "real_var_20": round(real_var_20, 8),
        "vol_of_vol_20": round(vol_of_vol_20, 8),
        "var_ratio_5_20": round(var_ratio_5_20, 8),
        "ewma_var_30": round(ewma_var_30, 8),
        "ewma_var_60": round(ewma_var_60, 8),
    }


def _hash_features(feature_stats: dict) -> str:
    """SHA256[:16] of canonical JSON representation.

    sort_keys=True ensures key-order independence.
    Values must be pre-rounded before calling this function.
    """
    canonical = json.dumps(feature_stats, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
