"""Contract tests: FeatureService no-lookahead invariant (D3 §2.2.1 / M9).

Invariant: data at or after as_of_time must never influence feature_hash or
feature_stats. The FeatureService filters candles to timestamp < as_of_time.

Tests:
  1. Adding a future candle does not change feature_hash.
  2. A candle at exactly as_of_time is excluded.
  3. Only future candles → zero feature values (same as empty).
  4. Boundary: candle at as_of_time - 1s is included; at as_of_time is not.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fx_ai_trading.services.feature_service import FeatureService


def _make_candle(ts: datetime, close: float = 1.1000) -> dict:
    return {
        "timestamp": ts,
        "open": close - 0.00005,
        "high": close + 0.0001,
        "low": close - 0.0001,
        "close": close,
        "volume": 1000.0,
    }


_AS_OF = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)

# Historical candles — all before as_of_time
_PAST_CANDLES = [
    _make_candle(_AS_OF - timedelta(minutes=i), 1.1000 + i * 0.0001) for i in range(100, 0, -1)
]

# One candle exactly at as_of_time (should be excluded)
_AT_CANDLE = _make_candle(_AS_OF, close=1.9999)

# One candle after as_of_time (should be excluded)
_FUTURE_CANDLE = _make_candle(_AS_OF + timedelta(minutes=1), close=1.9999)


class TestNoLookahead:
    def test_future_candle_does_not_change_hash(self) -> None:
        """Adding a future candle must not affect feature_hash (no-lookahead)."""
        svc_clean = FeatureService(get_candles=lambda i, t: list(_PAST_CANDLES))
        svc_polluted = FeatureService(
            get_candles=lambda i, t: list(_PAST_CANDLES) + [_FUTURE_CANDLE]
        )

        fs_clean = svc_clean.build("EUR_USD", "m1", uuid4(), _AS_OF)
        fs_polluted = svc_polluted.build("EUR_USD", "m1", uuid4(), _AS_OF)

        assert fs_clean.feature_hash == fs_polluted.feature_hash, (
            "Future candle must not affect feature_hash"
        )

    def test_candle_at_as_of_time_excluded(self) -> None:
        """A candle with timestamp == as_of_time must be excluded (strict <)."""
        svc_clean = FeatureService(get_candles=lambda i, t: list(_PAST_CANDLES))
        svc_at = FeatureService(get_candles=lambda i, t: list(_PAST_CANDLES) + [_AT_CANDLE])

        fs_clean = svc_clean.build("EUR_USD", "m1", uuid4(), _AS_OF)
        fs_at = svc_at.build("EUR_USD", "m1", uuid4(), _AS_OF)

        assert fs_clean.feature_hash == fs_at.feature_hash, "Candle at as_of_time must be excluded"

    def test_only_future_candles_produces_zero_features(self) -> None:
        """If only future candles exist, feature_stats must equal zero values."""
        svc = FeatureService(get_candles=lambda i, t: [_FUTURE_CANDLE, _AT_CANDLE])
        fs = svc.build("EUR_USD", "m1", uuid4(), _AS_OF)

        for key, val in fs.feature_stats.items():
            assert val == 0.0, f"{key} should be 0.0 when all candles are future, got {val}"

    def test_last_historical_candle_included(self) -> None:
        """Candle at as_of_time - 1s must be included in computation."""
        last_candle = _make_candle(_AS_OF - timedelta(seconds=1), close=1.5000)
        svc_with = FeatureService(get_candles=lambda i, t: [last_candle])
        svc_without = FeatureService(get_candles=lambda i, t: [])

        fs_with = svc_with.build("EUR_USD", "m1", uuid4(), _AS_OF)
        fs_without = svc_without.build("EUR_USD", "m1", uuid4(), _AS_OF)

        assert fs_with.feature_hash != fs_without.feature_hash, (
            "Candle 1s before as_of_time must be included"
        )
        assert fs_with.feature_stats["last_close"] == 1.5000

    def test_multiple_future_candles_same_as_empty(self) -> None:
        """Multiple future candles produce same hash as empty candle list."""
        future_candles = [_make_candle(_AS_OF + timedelta(minutes=i), 2.0) for i in range(1, 10)]
        svc_future = FeatureService(get_candles=lambda i, t: future_candles)
        svc_empty = FeatureService(get_candles=lambda i, t: [])

        fs_future = svc_future.build("EUR_USD", "m1", uuid4(), _AS_OF)
        fs_empty = svc_empty.build("EUR_USD", "m1", uuid4(), _AS_OF)

        assert fs_future.feature_hash == fs_empty.feature_hash
