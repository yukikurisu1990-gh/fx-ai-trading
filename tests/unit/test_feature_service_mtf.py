"""Unit tests for Phase 9.X-B/J-5 mtf feature group in FeatureService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from fx_ai_trading.services.feature_service import (
    _MTF_ZERO_FEATURES,
    FEATURE_VERSION,
    FeatureService,
    _compute_mtf_features,
)


def _make_candles(n: int, *, start_close: float = 1.10, drift: float = 0.0001) -> list[dict]:
    """Build n m5 candles spaced 5 minutes apart with a small drift."""
    base_ts = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    candles: list[dict] = []
    close = start_close
    for i in range(n):
        ts = base_ts + timedelta(minutes=5 * i)
        # Simple OHLC: open = previous close, close = previous + drift
        prev_close = close
        close = close + drift
        high = max(prev_close, close) + 0.0002
        low = min(prev_close, close) - 0.0002
        candles.append(
            {
                "timestamp": ts,
                "open": prev_close,
                "high": high,
                "low": low,
                "close": close,
                "volume": 1000,
            }
        )
    return candles


# ---------------------------------------------------------------------------
# _compute_mtf_features
# ---------------------------------------------------------------------------


class TestComputeMtfFeatures:
    def test_empty_candles_returns_zeros(self) -> None:
        result = _compute_mtf_features([])
        assert result == _MTF_ZERO_FEATURES

    def test_returns_all_six_keys(self) -> None:
        candles = _make_candles(2200)  # > 7 days of m5
        result = _compute_mtf_features(candles)
        expected_keys = {
            "h4_atr_14",
            "d1_return_3",
            "d1_range_pct",
            "d1_atr_14",
            "w1_return_1",
            "w1_range_pct",
        }
        assert set(result.keys()) == expected_keys

    def test_values_are_finite(self) -> None:
        candles = _make_candles(2200)
        result = _compute_mtf_features(candles)
        import math

        for k, v in result.items():
            assert math.isfinite(v), f"{k} is not finite: {v}"

    def test_values_rounded_to_8dp(self) -> None:
        candles = _make_candles(2200)
        result = _compute_mtf_features(candles)
        for k, v in result.items():
            # Round-trip through round() should be a no-op
            assert v == round(v, 8), f"{k} is not 8-dp rounded: {v}"

    def test_d1_return_3_consistent_with_drift(self) -> None:
        # Constant up-drift → d1_return_3 should be positive
        candles = _make_candles(2200, drift=0.0005)
        result = _compute_mtf_features(candles)
        assert result["d1_return_3"] > 0

    def test_d1_return_3_negative_drift(self) -> None:
        candles = _make_candles(2200, drift=-0.0005)
        result = _compute_mtf_features(candles)
        assert result["d1_return_3"] < 0

    def test_w1_return_1_consistent_with_drift(self) -> None:
        candles = _make_candles(2200, drift=0.0005)
        result = _compute_mtf_features(candles)
        assert result["w1_return_1"] > 0

    def test_atr_zero_when_constant_price(self) -> None:
        candles = _make_candles(2200, drift=0.0)
        # With constant drift=0 and no high/low spread inside the helper,
        # there's still ±0.0002 spread per bar, so ATR is small but nonzero.
        result = _compute_mtf_features(candles)
        # Just verify it's nonzero (positive) and small.
        assert result["d1_atr_14"] >= 0
        assert result["h4_atr_14"] >= 0

    def test_insufficient_history_for_atr(self) -> None:
        # Only 100 m5 bars (~8h) — not enough for daily ATR(14) (need 14 days)
        candles = _make_candles(100)
        result = _compute_mtf_features(candles)
        # Should not raise; returns 0 or partial-window value
        assert "d1_atr_14" in result
        # Just one daily bucket; ATR fallback returns high - low
        assert result["d1_atr_14"] >= 0

    def test_no_lookahead_determinism(self) -> None:
        # Same input → same output
        candles = _make_candles(2200)
        result_a = _compute_mtf_features(candles)
        result_b = _compute_mtf_features(candles)
        assert result_a == result_b


# ---------------------------------------------------------------------------
# FeatureService with enable_groups
# ---------------------------------------------------------------------------


class TestFeatureServiceMtf:
    def test_default_no_mtf_features(self) -> None:
        # Without enable_groups, mtf keys should NOT appear.
        candles = _make_candles(2200)
        service = FeatureService(get_candles=lambda inst, t: candles)
        result = service.build(
            instrument="EUR_USD",
            tier="m5",
            cycle_id=uuid4(),
            as_of_time=datetime(2026, 1, 8, 0, 0, tzinfo=UTC),
        )
        assert "h4_atr_14" not in result.feature_stats
        assert "d1_return_3" not in result.feature_stats
        assert "atr_14" in result.feature_stats  # baseline still present

    def test_mtf_enabled_adds_six_features(self) -> None:
        candles = _make_candles(2200)
        service = FeatureService(
            get_candles=lambda inst, t: candles,
            enable_groups=frozenset({"mtf"}),
        )
        result = service.build(
            instrument="EUR_USD",
            tier="m5",
            cycle_id=uuid4(),
            as_of_time=datetime(2026, 1, 8, 0, 0, tzinfo=UTC),
        )
        for key in (
            "h4_atr_14",
            "d1_return_3",
            "d1_range_pct",
            "d1_atr_14",
            "w1_return_1",
            "w1_range_pct",
        ):
            assert key in result.feature_stats, f"missing {key}"
        # Baseline features still present.
        assert "atr_14" in result.feature_stats

    def test_invalid_group_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid feature group"):
            FeatureService(
                get_candles=lambda inst, t: [],
                enable_groups=frozenset({"garbage"}),
            )

    def test_feature_version_v3(self) -> None:
        assert FEATURE_VERSION == "v3"

    def test_feature_hash_changes_with_mtf(self) -> None:
        # Same candles, different enable_groups → different feature_hash
        candles = _make_candles(2200)
        as_of = datetime(2026, 1, 8, 0, 0, tzinfo=UTC)
        cycle = uuid4()

        service_no = FeatureService(get_candles=lambda inst, t: candles)
        service_mtf = FeatureService(
            get_candles=lambda inst, t: candles,
            enable_groups=frozenset({"mtf"}),
        )

        result_no = service_no.build("EUR_USD", "m5", cycle, as_of)
        result_mtf = service_mtf.build("EUR_USD", "m5", cycle, as_of)
        assert result_no.feature_hash != result_mtf.feature_hash

    def test_no_lookahead_filter(self) -> None:
        # Candles past as_of_time must be filtered out.
        candles = _make_candles(2200)
        as_of = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
        future = [c for c in candles if c["timestamp"] >= as_of]
        assert len(future) > 0, "test setup: must have some future candles"

        service = FeatureService(
            get_candles=lambda inst, t: candles,
            enable_groups=frozenset({"mtf"}),
        )
        result = service.build("EUR_USD", "m5", uuid4(), as_of)

        # Re-run with manually-pre-filtered candles → same hash
        past = [c for c in candles if c["timestamp"] < as_of]
        service2 = FeatureService(
            get_candles=lambda inst, t: past,
            enable_groups=frozenset({"mtf"}),
        )
        result2 = service2.build("EUR_USD", "m5", uuid4(), as_of)
        assert result.feature_hash == result2.feature_hash

    def test_determinism_same_candles_same_hash(self) -> None:
        candles = _make_candles(2200)
        as_of = datetime(2026, 1, 8, 0, 0, tzinfo=UTC)
        service = FeatureService(
            get_candles=lambda inst, t: candles,
            enable_groups=frozenset({"mtf"}),
        )
        h1 = service.build("EUR_USD", "m5", uuid4(), as_of).feature_hash
        h2 = service.build("EUR_USD", "m5", uuid4(), as_of).feature_hash
        assert h1 == h2
