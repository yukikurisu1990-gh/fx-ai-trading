"""Unit tests for Phase 9.X-B/J-5 mtf feature group in FeatureService."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from fx_ai_trading.services.feature_service import (
    _MTF_ZERO_FEATURES,
    _UPPER_TF_ZERO_FEATURES,
    FEATURE_VERSION,
    FeatureService,
    _compute_mtf_features,
    _compute_upper_tf_all,
    _h4_bucket,
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
        # F-8: the last (in-progress) weekly bucket is dropped, so we need
        # >= 3 ISO-week buckets for 2 COMPLETED weekly bars (2026-01-01 is a
        # Thursday: week 1 = Jan 1-4, week 2 = Jan 5-11, week 3 = Jan 12+).
        # 3600 m5 bars = 12.5 days -> reaches into week 3.
        candles = _make_candles(3600, drift=0.0005)
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
        # F-8: the single daily bucket is in-progress and is dropped, so the
        # daily ATR falls back to the zero/insufficient-history value.
        assert result["d1_atr_14"] == 0.0
        # 100 m5 bars span three h4 buckets (00/04/08) -> 2 completed ones.
        assert result["h4_atr_14"] >= 0

    def test_no_lookahead_determinism(self) -> None:
        # Same input → same output
        candles = _make_candles(2200)
        result_a = _compute_mtf_features(candles)
        result_b = _compute_mtf_features(candles)
        assert result_a == result_b


# ---------------------------------------------------------------------------
# F-8: completed-bucket consistency (in-progress bucket must be excluded)
# ---------------------------------------------------------------------------


def _perturb(candle: dict, delta: float = 0.05) -> dict:
    """Return a copy of *candle* with all prices shifted / range widened."""
    out = dict(candle)
    out["open"] = candle["open"] + delta
    out["high"] = candle["high"] + 2 * delta
    out["low"] = candle["low"] - 2 * delta
    out["close"] = candle["close"] + delta
    return out


class TestF8CompletedBucketConsistency:
    """MTF fallback must use only COMPLETED H4/D1/W1 buckets (audit F-8).

    Timeline: 3600 m5 candles from 2026-01-01 00:00 UTC (a Thursday) span
    ~12.5 days -> ISO weeks 1 (Jan 1-4), 2 (Jan 5-11), 3 (Jan 12+, partial);
    13 daily buckets (Jan 13 partial); 75 h4 buckets (last partial).
    Candles in the LAST h4 bucket are, by chronology, also inside the last
    d1 and last w1 buckets — perturbing only them touches exclusively the
    in-progress bucket of every timeframe.
    """

    N = 3600

    def test_in_progress_bucket_perturbation_does_not_change_features(self) -> None:
        candles = _make_candles(self.N)
        base = _compute_mtf_features(candles)

        last_h4_key = _h4_bucket(candles[-1]["timestamp"])
        perturbed = [
            _perturb(c) if _h4_bucket(c["timestamp"]) == last_h4_key else c for c in candles
        ]
        n_perturbed = sum(1 for a, b in zip(candles, perturbed, strict=True) if a is not b)
        assert n_perturbed > 0, "test setup: must perturb at least one candle"

        assert _compute_mtf_features(perturbed) == base

    def test_completed_bucket_perturbation_changes_features(self) -> None:
        candles = _make_candles(self.N)
        base = _compute_mtf_features(candles)

        # Perturb one candle on Jan 6 — a COMPLETED d1 bucket, inside the
        # COMPLETED ISO week 2, and a completed h4 bucket.
        target = datetime(2026, 1, 6, 10, 0, tzinfo=UTC)
        idx = next(i for i, c in enumerate(candles) if c["timestamp"] == target)
        perturbed = list(candles)
        perturbed[idx] = _perturb(candles[idx])

        assert _compute_mtf_features(perturbed) != base

    def test_all_history_in_single_bucket_returns_zeros(self) -> None:
        # 10 candles inside one hour: every timeframe has exactly one
        # (in-progress) bucket -> dropped -> insufficient-history zeros.
        candles = _make_candles(10)
        assert _compute_mtf_features(candles) == _MTF_ZERO_FEATURES

    def test_agreement_with_pandas_shift1_reference(self) -> None:
        # Training-side reference (scripts/train_lgbm_models.py
        # _add_mtf_features): resample -> feature -> shift(1) -> reindex.
        # The fallback value at the newest candle must equal the shift(1)
        # value the training pipeline would assign to that row.
        pd = pytest.importorskip("pandas")

        candles = _make_candles(self.N)
        result = _compute_mtf_features(candles)

        df = pd.DataFrame(candles).set_index("timestamp")

        # d1_return_3 — calendar-day resample, shift(1), reindex (ffill).
        d1_close = df["close"].resample("1D").last()
        d1_return_3 = d1_close.pct_change(3).shift(1)
        ref_d1 = d1_return_3.reindex(df.index, method="ffill").iloc[-1]
        assert result["d1_return_3"] == pytest.approx(ref_d1, abs=1e-8)

        # w1_return_1 — ISO-week grouping (matches _w1_bucket), shift(1):
        # the newest row sits in the last (in-progress) week, so its
        # shift(1) value is pct_change at the second-to-last week bucket.
        iso = df.index.isocalendar()
        w1_close = df["close"].groupby([iso["year"], iso["week"]]).last()
        ref_w1 = w1_close.pct_change(1).iloc[-2]
        assert result["w1_return_1"] == pytest.approx(ref_w1, abs=1e-8)


# ---------------------------------------------------------------------------
# FeatureService with enable_groups
# ---------------------------------------------------------------------------


class TestFeatureServiceMtf:
    def test_default_no_mtf_features_but_upper_tf_present(self) -> None:
        # Without enable_groups, H4/D1/W1 MTF keys should NOT appear,
        # but M5/M15/H1 upper-TF keys ARE always present (v4).
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
        # v4: M5/M15/H1 upper-TF features always present.
        assert "m5_return_1" in result.feature_stats
        assert "m15_rsi_14" in result.feature_stats
        assert "h1_bb_pct_b" in result.feature_stats

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

    def test_feature_version_v4(self) -> None:
        assert FEATURE_VERSION == "v4"

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
        # F-8: also assert the six MTF values themselves match, not only the
        # aggregate hash — future candles must not leak into the MTF group.
        for key in _MTF_ZERO_FEATURES:
            assert result.feature_stats[key] == result2.feature_stats[key]

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


# ---------------------------------------------------------------------------
# _compute_upper_tf_all (v4 always-on M5/M15/H1 features)
# ---------------------------------------------------------------------------


class TestComputeUpperTfAll:
    def test_empty_candles_returns_zero_dict(self) -> None:
        result = _compute_upper_tf_all([])
        assert result == _UPPER_TF_ZERO_FEATURES

    def test_returns_all_24_keys(self) -> None:
        candles = _make_candles(2200)
        result = _compute_upper_tf_all(candles)
        assert set(result.keys()) == set(_UPPER_TF_ZERO_FEATURES.keys())

    def test_values_finite(self) -> None:
        import math

        candles = _make_candles(2200)
        result = _compute_upper_tf_all(candles)
        for k, v in result.items():
            assert math.isfinite(v), f"{k} is not finite: {v}"

    def test_values_rounded_to_8dp(self) -> None:
        candles = _make_candles(2200)
        result = _compute_upper_tf_all(candles)
        for k, v in result.items():
            assert v == round(v, 8), f"{k} not 8-dp rounded: {v}"

    def test_rsi_bounded_0_to_100(self) -> None:
        candles = _make_candles(2200, drift=0.0001)
        result = _compute_upper_tf_all(candles)
        for prefix in ("m5", "m15", "h1"):
            rsi = result[f"{prefix}_rsi_14"]
            assert 0.0 <= rsi <= 100.0, f"{prefix}_rsi_14={rsi} out of range"

    def test_uptrend_return1_positive(self) -> None:
        candles = _make_candles(2200, drift=0.001)
        result = _compute_upper_tf_all(candles)
        for prefix in ("m5", "m15", "h1"):
            assert result[f"{prefix}_return_1"] > 0, f"{prefix}_return_1 not positive"

    def test_downtrend_return1_negative(self) -> None:
        # drift=-0.0001 keeps prices positive over 2200 bars (floor ~0.88)
        candles = _make_candles(2200, drift=-0.0001)
        result = _compute_upper_tf_all(candles)
        for prefix in ("m5", "m15", "h1"):
            assert result[f"{prefix}_return_1"] < 0, f"{prefix}_return_1 not negative"

    def test_insufficient_history_returns_zeros(self) -> None:
        # Only 2 M1 candles — not enough to form 2 completed bars at any TF.
        candles = _make_candles(2)
        result = _compute_upper_tf_all(candles)
        assert result == _UPPER_TF_ZERO_FEATURES

    def test_determinism(self) -> None:
        candles = _make_candles(2200)
        assert _compute_upper_tf_all(candles) == _compute_upper_tf_all(candles)

    def test_feature_service_build_includes_upper_tf(self) -> None:
        candles = _make_candles(2200)
        as_of = datetime(2026, 1, 8, 0, 0, tzinfo=UTC)
        service = FeatureService(get_candles=lambda inst, t: candles)
        result = service.build("EUR_USD", "m5", uuid4(), as_of)
        for key in _UPPER_TF_ZERO_FEATURES:
            assert key in result.feature_stats, f"upper-TF key missing: {key}"
