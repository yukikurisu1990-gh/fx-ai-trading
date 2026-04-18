"""Contract tests: FeatureService determinism (D3 §2.2.1 / 6.10 / M9).

Invariant: same inputs + same FEATURE_VERSION → byte-equal feature_hash.

Tests:
  1. Identical calls produce identical feature_hash.
  2. Different candle data produces different feature_hash.
  3. feature_version matches the module constant.
  4. feature_stats contains required keys with float values.
  5. computed_at equals as_of_time (no internal clock call).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from fx_ai_trading.services.feature_service import FEATURE_VERSION, FeatureService


def _make_candles(n: int, base_price: float = 1.1000) -> list[dict]:
    """Create *n* synthetic candles ending before a fixed as_of_time."""
    start = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
    candles = []
    for i in range(n):
        ts = start + timedelta(minutes=i)
        close = base_price + i * 0.0001
        candles.append(
            {
                "timestamp": ts,
                "open": close - 0.00005,
                "high": close + 0.0001,
                "low": close - 0.0001,
                "close": close,
                "volume": 1000.0,
            }
        )
    return candles


_AS_OF = datetime(2024, 1, 1, 2, 0, 0, tzinfo=UTC)  # after all candles
_CANDLES = _make_candles(100)


@pytest.fixture()
def service() -> FeatureService:
    return FeatureService(get_candles=lambda inst, t: _CANDLES)


class TestFeatureDeterminism:
    def test_same_input_produces_same_hash(self, service: FeatureService) -> None:
        """Same inputs → same feature_hash (core determinism contract)."""
        fs1 = service.build("EUR_USD", "m1", uuid4(), _AS_OF)
        fs2 = service.build("EUR_USD", "m1", uuid4(), _AS_OF)
        assert fs1.feature_hash == fs2.feature_hash

    def test_different_candles_produce_different_hash(self) -> None:
        """Different candle data → different feature_hash."""
        svc_a = FeatureService(get_candles=lambda i, t: _make_candles(100, 1.1000))
        svc_b = FeatureService(get_candles=lambda i, t: _make_candles(100, 1.2000))
        fs_a = svc_a.build("EUR_USD", "m1", uuid4(), _AS_OF)
        fs_b = svc_b.build("EUR_USD", "m1", uuid4(), _AS_OF)
        assert fs_a.feature_hash != fs_b.feature_hash

    def test_feature_version_matches_constant(self, service: FeatureService) -> None:
        """feature_version in output must equal module FEATURE_VERSION constant."""
        fs = service.build("EUR_USD", "m1", uuid4(), _AS_OF)
        assert fs.feature_version == FEATURE_VERSION
        assert service.get_feature_version() == FEATURE_VERSION

    def test_required_feature_keys_present(self, service: FeatureService) -> None:
        """feature_stats must contain sma_20, sma_50, atr_14, last_close."""
        fs = service.build("EUR_USD", "m1", uuid4(), _AS_OF)
        required = {"sma_20", "sma_50", "atr_14", "last_close"}
        assert required <= set(fs.feature_stats.keys())

    def test_feature_stats_values_are_floats(self, service: FeatureService) -> None:
        """All feature_stats values must be float."""
        fs = service.build("EUR_USD", "m1", uuid4(), _AS_OF)
        for key, val in fs.feature_stats.items():
            assert isinstance(val, float), f"{key} is not float: {type(val)}"

    def test_computed_at_equals_as_of_time(self, service: FeatureService) -> None:
        """computed_at must equal as_of_time — no internal clock usage."""
        fs = service.build("EUR_USD", "m1", uuid4(), _AS_OF)
        assert fs.computed_at == _AS_OF

    def test_hash_is_16_hex_chars(self, service: FeatureService) -> None:
        """feature_hash must be a 16-character hex string (SHA256[:16])."""
        fs = service.build("EUR_USD", "m1", uuid4(), _AS_OF)
        assert len(fs.feature_hash) == 16
        assert all(c in "0123456789abcdef" for c in fs.feature_hash)

    def test_cycle_id_does_not_affect_hash(self, service: FeatureService) -> None:
        """Different cycle_ids with same candles must produce the same feature_hash."""
        fs1 = service.build("EUR_USD", "m1", uuid4(), _AS_OF)
        fs2 = service.build("EUR_USD", "m1", uuid4(), _AS_OF)
        assert fs1.feature_hash == fs2.feature_hash

    def test_empty_candles_returns_zero_features(self) -> None:
        """Empty candle list → all feature values are 0.0."""
        svc = FeatureService(get_candles=lambda i, t: [])
        fs = svc.build("EUR_USD", "m1", uuid4(), _AS_OF)
        for val in fs.feature_stats.values():
            assert val == 0.0
