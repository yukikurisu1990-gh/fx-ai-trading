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
FEATURE_VERSION = "v2"


class FeatureService:
    """Deterministic FeatureBuilder implementation for M9/Phase 9.4.

    Args:
        get_candles: Callable(instrument, as_of_time) → list of candle dicts.
            Each candle must have keys: timestamp (datetime), open, high, low,
            close (float), volume (float).
            May include data up to or past as_of_time; build() will filter.
    """

    def __init__(
        self,
        get_candles: Callable[[str, datetime], list[dict]],
    ) -> None:
        self._get_candles = get_candles

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
    "bb_pct_b": 0.5,
    "bb_upper": 0.0,
    "bb_width": 0.0,
    "ema_12": 0.0,
    "ema_26": 0.0,
    "last_close": 0.0,
    "macd_histogram": 0.0,
    "macd_line": 0.0,
    "macd_signal": 0.0,
    "rsi_14": 50.0,
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


def _hash_features(feature_stats: dict) -> str:
    """SHA256[:16] of canonical JSON representation.

    sort_keys=True ensures key-order independence.
    Values must be pre-rounded before calling this function.
    """
    canonical = json.dumps(feature_stats, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
