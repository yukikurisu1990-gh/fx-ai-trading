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
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime
from uuid import UUID

from fx_ai_trading.domain.feature import FeatureSet

# Bump this constant when feature computation logic changes.
FEATURE_VERSION = "v1"


class FeatureService:
    """Deterministic FeatureBuilder implementation for M9.

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


def _compute_features(candles: list[dict]) -> dict:
    """Compute deterministic feature_stats from *candles*.

    Returns a dict with float values rounded to 8 decimal places for hash stability.
    """
    if not candles:
        return {
            "sma_20": 0.0,
            "sma_50": 0.0,
            "atr_14": 0.0,
            "last_close": 0.0,
        }

    closes = [c["close"] for c in candles]

    sma_20 = _sma(closes, 20)
    sma_50 = _sma(closes, 50)
    atr_14 = _atr(candles, 14)
    last_close = closes[-1]

    return {
        "atr_14": round(atr_14, 8),
        "last_close": round(last_close, 8),
        "sma_20": round(sma_20, 8),
        "sma_50": round(sma_50, 8),
    }


def _sma(values: list[float], period: int) -> float:
    """Simple moving average of the last *period* values."""
    if not values:
        return 0.0
    window = values[-period:] if len(values) >= period else values
    return sum(window) / len(window)


def _atr(candles: list[dict], period: int) -> float:
    """Average True Range over the last *period* bars."""
    if len(candles) < 2:
        if candles:
            return round(candles[0]["high"] - candles[0]["low"], 8)
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
