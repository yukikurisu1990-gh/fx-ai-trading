"""Unit tests for Phase 9.X-B amendment vol feature group in FeatureService."""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from fx_ai_trading.services.feature_service import (
    _VOL_ZERO_FEATURES,
    FEATURE_VERSION,
    FeatureService,
    _compute_vol_features,
)


def _make_candles(
    n: int,
    *,
    start_close: float = 1.10,
    drift: float = 0.0001,
) -> list[dict]:
    """Build n m5 candles spaced 5 minutes apart with a small drift."""
    base_ts = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    candles: list[dict] = []
    close = start_close
    for i in range(n):
        ts = base_ts + timedelta(minutes=5 * i)
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
# _compute_vol_features
# ---------------------------------------------------------------------------


class TestComputeVolFeatures:
    def test_empty_candles_returns_zeros(self) -> None:
        result = _compute_vol_features([])
        assert result == _VOL_ZERO_FEATURES

    def test_single_candle_returns_zeros(self) -> None:
        candles = _make_candles(1)
        result = _compute_vol_features(candles)
        assert result == _VOL_ZERO_FEATURES

    def test_returns_all_six_keys(self) -> None:
        candles = _make_candles(500)
        result = _compute_vol_features(candles)
        expected_keys = {
            "real_var_5",
            "real_var_20",
            "vol_of_vol_20",
            "var_ratio_5_20",
            "ewma_var_30",
            "ewma_var_60",
        }
        assert set(result.keys()) == expected_keys

    def test_values_are_finite(self) -> None:
        candles = _make_candles(500)
        result = _compute_vol_features(candles)
        for k, v in result.items():
            assert math.isfinite(v), f"{k} is not finite: {v}"

    def test_values_rounded_to_8dp(self) -> None:
        candles = _make_candles(500)
        result = _compute_vol_features(candles)
        for k, v in result.items():
            assert v == round(v, 8), f"{k} is not 8-dp rounded: {v}"

    def test_real_var_nonneg(self) -> None:
        candles = _make_candles(500)
        result = _compute_vol_features(candles)
        assert result["real_var_5"] >= 0
        assert result["real_var_20"] >= 0
        assert result["ewma_var_30"] >= 0
        assert result["ewma_var_60"] >= 0
        assert result["vol_of_vol_20"] >= 0

    def test_constant_price_yields_zero_variance(self) -> None:
        # drift=0 plus same OHLC gives no log-returns to speak of
        candles = _make_candles(500, drift=0.0)
        result = _compute_vol_features(candles)
        # log-returns are computed from closes only; with drift=0 the
        # close is constant ⇒ all variance terms are exactly zero.
        assert result["real_var_5"] == 0.0
        assert result["real_var_20"] == 0.0
        assert result["ewma_var_30"] == 0.0

    def test_higher_drift_yields_higher_variance(self) -> None:
        small = _compute_vol_features(_make_candles(500, drift=0.0001))
        large = _compute_vol_features(_make_candles(500, drift=0.0010))
        assert large["real_var_20"] > small["real_var_20"]

    def test_var_ratio_zero_when_rv20_zero(self) -> None:
        candles = _make_candles(500, drift=0.0)
        result = _compute_vol_features(candles)
        assert result["var_ratio_5_20"] == 0.0

    def test_insufficient_history_for_ewma_60(self) -> None:
        # min_periods=20 for ewma_var_60 — should return 0 if fewer.
        candles = _make_candles(15)  # < 20 squared returns
        result = _compute_vol_features(candles)
        assert result["ewma_var_60"] == 0.0

    def test_determinism(self) -> None:
        candles = _make_candles(500)
        a = _compute_vol_features(candles)
        b = _compute_vol_features(candles)
        assert a == b


# ---------------------------------------------------------------------------
# FeatureService with enable_groups={"vol"}
# ---------------------------------------------------------------------------


class TestFeatureServiceVol:
    def test_default_no_vol_features(self) -> None:
        candles = _make_candles(500)
        service = FeatureService(get_candles=lambda inst, t: candles)
        result = service.build(
            instrument="EUR_USD",
            tier="m5",
            cycle_id=uuid4(),
            as_of_time=datetime(2026, 1, 8, 0, 0, tzinfo=UTC),
        )
        assert "real_var_5" not in result.feature_stats
        assert "ewma_var_60" not in result.feature_stats
        # Baseline still present.
        assert "atr_14" in result.feature_stats

    def test_vol_enabled_adds_six_features(self) -> None:
        candles = _make_candles(500)
        service = FeatureService(
            get_candles=lambda inst, t: candles,
            enable_groups=frozenset({"vol"}),
        )
        result = service.build(
            instrument="EUR_USD",
            tier="m5",
            cycle_id=uuid4(),
            as_of_time=datetime(2026, 1, 8, 0, 0, tzinfo=UTC),
        )
        for key in (
            "real_var_5",
            "real_var_20",
            "vol_of_vol_20",
            "var_ratio_5_20",
            "ewma_var_30",
            "ewma_var_60",
        ):
            assert key in result.feature_stats, f"missing {key}"
        assert "atr_14" in result.feature_stats

    def test_vol_and_mtf_can_coexist(self) -> None:
        candles = _make_candles(2200)
        service = FeatureService(
            get_candles=lambda inst, t: candles,
            enable_groups=frozenset({"vol", "mtf"}),
        )
        result = service.build(
            instrument="EUR_USD",
            tier="m5",
            cycle_id=uuid4(),
            as_of_time=datetime(2026, 1, 8, 0, 0, tzinfo=UTC),
        )
        # Both groups' keys present.
        assert "real_var_5" in result.feature_stats
        assert "h4_atr_14" in result.feature_stats

    def test_invalid_group_still_rejected(self) -> None:
        with pytest.raises(ValueError, match="invalid feature group"):
            FeatureService(
                get_candles=lambda inst, t: [],
                enable_groups=frozenset({"garbage"}),
            )

    def test_feature_version_unchanged(self) -> None:
        # Adding a new opt-in group does NOT change FEATURE_VERSION.
        # Default behaviour (enable_groups=frozenset()) stays v3.
        assert FEATURE_VERSION == "v3"

    def test_feature_hash_changes_with_vol(self) -> None:
        candles = _make_candles(500)
        as_of = datetime(2026, 1, 8, 0, 0, tzinfo=UTC)
        cycle = uuid4()

        service_no = FeatureService(get_candles=lambda inst, t: candles)
        service_vol = FeatureService(
            get_candles=lambda inst, t: candles,
            enable_groups=frozenset({"vol"}),
        )
        result_no = service_no.build("EUR_USD", "m5", cycle, as_of)
        result_vol = service_vol.build("EUR_USD", "m5", cycle, as_of)
        assert result_no.feature_hash != result_vol.feature_hash

    def test_no_lookahead_filter(self) -> None:
        candles = _make_candles(500)
        as_of = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        future = [c for c in candles if c["timestamp"] >= as_of]
        assert len(future) > 0

        service = FeatureService(
            get_candles=lambda inst, t: candles,
            enable_groups=frozenset({"vol"}),
        )
        result = service.build("EUR_USD", "m5", uuid4(), as_of)

        past = [c for c in candles if c["timestamp"] < as_of]
        service2 = FeatureService(
            get_candles=lambda inst, t: past,
            enable_groups=frozenset({"vol"}),
        )
        result2 = service2.build("EUR_USD", "m5", uuid4(), as_of)
        assert result.feature_hash == result2.feature_hash

    def test_determinism_same_candles_same_hash(self) -> None:
        candles = _make_candles(500)
        as_of = datetime(2026, 1, 8, 0, 0, tzinfo=UTC)
        service = FeatureService(
            get_candles=lambda inst, t: candles,
            enable_groups=frozenset({"vol"}),
        )
        h1 = service.build("EUR_USD", "m5", uuid4(), as_of).feature_hash
        h2 = service.build("EUR_USD", "m5", uuid4(), as_of).feature_hash
        assert h1 == h2
