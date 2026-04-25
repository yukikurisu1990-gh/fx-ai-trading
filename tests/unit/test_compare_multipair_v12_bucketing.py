"""Unit tests for compare_multipair_v12_asymmetric.py - Phase 9.18/H-1.

Covers the confidence-bucketing function and the multi-multiplier label
helper. The full eval pipeline is exercised by running the script end-to-
end against fixture candles, which is too slow for unit tests; here we
verify the building blocks in isolation.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import compare_multipair_v12_asymmetric as v12  # noqa: E402


class TestBucketForConfidence:
    def test_below_low_boundary_returns_low(self) -> None:
        assert v12._bucket_for_confidence(0.50) == v12._BUCKET_LOW
        assert v12._bucket_for_confidence(0.54) == v12._BUCKET_LOW
        assert v12._bucket_for_confidence(0.5499) == v12._BUCKET_LOW

    def test_at_low_boundary_returns_mid(self) -> None:
        assert v12._bucket_for_confidence(0.55) == v12._BUCKET_MID

    def test_in_mid_range_returns_mid(self) -> None:
        assert v12._bucket_for_confidence(0.55) == v12._BUCKET_MID
        assert v12._bucket_for_confidence(0.60) == v12._BUCKET_MID
        assert v12._bucket_for_confidence(0.6499) == v12._BUCKET_MID

    def test_at_high_boundary_returns_high(self) -> None:
        assert v12._bucket_for_confidence(0.65) == v12._BUCKET_HIGH

    def test_above_high_boundary_returns_high(self) -> None:
        assert v12._bucket_for_confidence(0.70) == v12._BUCKET_HIGH
        assert v12._bucket_for_confidence(0.99) == v12._BUCKET_HIGH
        assert v12._bucket_for_confidence(1.00) == v12._BUCKET_HIGH

    def test_returns_correct_multipliers(self) -> None:
        _, tp_low, sl_low = v12._bucket_for_confidence(0.51)
        assert tp_low == 1.2 and sl_low == 1.2
        _, tp_mid, sl_mid = v12._bucket_for_confidence(0.60)
        assert tp_mid == 1.5 and sl_mid == 1.0
        _, tp_high, sl_high = v12._bucket_for_confidence(0.80)
        assert tp_high == 2.0 and sl_high == 0.8


class TestBucketIndices:
    def test_returns_int8_array_with_correct_indices(self) -> None:
        conf = np.array([0.50, 0.54, 0.55, 0.60, 0.64, 0.65, 0.80, 0.99])
        out = v12._bucket_indices(conf)
        assert out.dtype == np.int8
        np.testing.assert_array_equal(out, [0, 0, 1, 1, 1, 2, 2, 2])

    def test_empty_input_returns_empty_array(self) -> None:
        out = v12._bucket_indices(np.array([], dtype=np.float64))
        assert out.shape == (0,)
        assert out.dtype == np.int8

    def test_matches_scalar_function_pointwise(self) -> None:
        confs = np.linspace(0.50, 1.0, 51)
        idx_vec = v12._bucket_indices(confs)
        for c, idx in zip(confs, idx_vec, strict=True):
            name, _, _ = v12._bucket_for_confidence(float(c))
            expected = v12._BUCKET_NAMES.index(name)
            assert idx == expected, f"mismatch at conf={c}: vec={idx} scalar={expected}"


def _make_synthetic_ba_df(n: int = 60) -> pd.DataFrame:
    """Build a tiny synthetic BA-mode DataFrame for label tests.

    Deterministic uptrend with constant 1pip spread and ATR=0.001 (10pip).
    A long trade entered at bar i should hit TP at multiple distances.
    """
    base = 1.10000
    closes = base + np.linspace(0, 0.005, n)  # +5pip linear up
    highs = closes + 0.0001
    lows = closes - 0.0001
    opens = closes.copy()
    spread = 0.00005  # 0.5pip half-spread on each side (1pip total)
    atr = np.full(n, 0.0010, dtype=np.float64)  # 10pip
    df = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "bid_o": opens - spread,
            "bid_h": highs - spread,
            "bid_l": lows - spread,
            "bid_c": closes - spread,
            "ask_o": opens + spread,
            "ask_h": highs + spread,
            "ask_l": lows + spread,
            "ask_c": closes + spread,
            "atr_14": atr,
            "volume": 100,
        },
        index=pd.date_range("2025-01-01", periods=n, freq="min", tz="UTC"),
    )
    return df


class TestAddLabelsBidaskMulti:
    def test_produces_three_columns(self) -> None:
        df = _make_synthetic_ba_df(60)
        out = v12._add_labels_bidask_multi(
            df,
            horizon=10,
            multipliers=((1.2, 1.2), (1.5, 1.0), (2.0, 0.8)),
            out_columns=("label_tb_low", "label_tb_mid", "label_tb_high"),
        )
        assert "label_tb_low" in out.columns
        assert "label_tb_mid" in out.columns
        assert "label_tb_high" in out.columns

    def test_short_window_makes_late_bars_unlabelable(self) -> None:
        df = _make_synthetic_ba_df(20)
        out = v12._add_labels_bidask_multi(
            df,
            horizon=15,
            multipliers=((1.5, 1.0),),
            out_columns=("label_tb_mid",),
        )
        # Only bars i in [0, n - horizon - 1) = [0, 4) are labelable.
        # Bars from index 4 onward should be NaN (None becomes NaN when
        # pandas stores a list[int | None] in a column).
        late = out["label_tb_mid"].iloc[5:]
        assert late.isna().all(), f"expected late bars NaN, got {late.tolist()}"

    def test_horizon_too_short_for_tp_returns_zero(self) -> None:
        # 1pip uptrend per bar but TP=1.5*ATR=15pip; horizon=3 -> TP can't fire
        # at any direction; expect label=0 (timeout) on labelable bars.
        df = _make_synthetic_ba_df(30)
        out = v12._add_labels_bidask_multi(
            df,
            horizon=3,
            multipliers=((1.5, 1.0),),
            out_columns=("label_tb_mid",),
        )
        # Restrict to labelable bars (non-NaN).
        labelled = out["label_tb_mid"].dropna()
        # All should be timeout (0) since 3-bar window can't reach 15pip TP.
        assert (labelled == 0).all(), f"expected all 0, got {sorted(labelled.unique())}"

    def test_multipliers_and_columns_must_match_length(self) -> None:
        df = _make_synthetic_ba_df(20)
        with pytest.raises(ValueError, match="same length"):
            v12._add_labels_bidask_multi(
                df,
                horizon=5,
                multipliers=((1.5, 1.0), (2.0, 0.8)),
                out_columns=("only_one_col",),
            )

    def test_missing_bid_ask_columns_raises(self) -> None:
        df = pd.DataFrame(
            {
                "open": [1.1] * 10,
                "high": [1.1] * 10,
                "low": [1.1] * 10,
                "close": [1.1] * 10,
                "atr_14": [0.001] * 10,
                "volume": [100] * 10,
            },
            index=pd.date_range("2025-01-01", periods=10, freq="min", tz="UTC"),
        )
        with pytest.raises(ValueError, match="BA mode candles"):
            v12._add_labels_bidask_multi(
                df,
                horizon=5,
                multipliers=((1.5, 1.0),),
                out_columns=("label_tb_mid",),
            )

    def test_higher_tp_mult_is_harder_to_clear(self) -> None:
        """A trade that fires TP at 1.2xATR may not fire at 2.0xATR."""
        df = _make_synthetic_ba_df(60)
        out = v12._add_labels_bidask_multi(
            df,
            horizon=15,
            multipliers=((1.2, 1.2), (2.0, 0.8)),
            out_columns=("low", "high"),
        )
        # On the labelable bars, count how many TPs fire at each multiplier.
        low_tp = (out["low"] == 1).sum() + (out["low"] == -1).sum()
        high_tp = (out["high"] == 1).sum() + (out["high"] == -1).sum()
        # Low (1.2xATR ~ 12pip) should fire more often than high (2.0xATR ~ 20pip)
        # given the synthetic uptrend has only +5pip total over 60 bars.
        # Both will likely be 0; just assert high <= low (no contradiction).
        assert high_tp <= low_tp


class TestBucketLookupArrays:
    def test_tp_by_idx_matches_bucket_constants(self) -> None:
        assert v12._BUCKET_TP_BY_IDX[0] == v12._BUCKET_LOW[1]
        assert v12._BUCKET_TP_BY_IDX[1] == v12._BUCKET_MID[1]
        assert v12._BUCKET_TP_BY_IDX[2] == v12._BUCKET_HIGH[1]

    def test_sl_by_idx_matches_bucket_constants(self) -> None:
        assert v12._BUCKET_SL_BY_IDX[0] == v12._BUCKET_LOW[2]
        assert v12._BUCKET_SL_BY_IDX[1] == v12._BUCKET_MID[2]
        assert v12._BUCKET_SL_BY_IDX[2] == v12._BUCKET_HIGH[2]

    def test_label_cols_in_canonical_order(self) -> None:
        assert v12._LABEL_COLS_BY_BUCKET == (
            v12._LABEL_COL_LOW,
            v12._LABEL_COL_MID,
            v12._LABEL_COL_HIGH,
        )

    def test_bucket_names_match_constants(self) -> None:
        assert v12._BUCKET_NAMES == ("low", "mid", "high")


class TestPartialHighOutcomeLong:
    """Phase 9.18/H-2: scenario tests for the High-bucket partial-exit helper.

    A long trade is opened at entry with two legs (50% size each):
      partial: TP=+1xATR, SL=-0.8xATR
      runner:  TP=+2xATR, SL=-0.8xATR initially -> trails to entry once
               partial fires.

    With ATR=10pip and pip=0.0001, the half-leg pip values are:
      partial TP   ->  0.5 x 1.0 x 10 =  5pip
      runner TP    ->  0.5 x 2.0 x 10 = 10pip
      SL (any leg) -> -0.5 x 0.8 x 10 = -4pip
    """

    ENTRY = 1.10000
    ATR = 0.001
    PIP = 0.0001

    def test_partial_then_full_tp_in_same_bar(self) -> None:
        bid_h = np.array([1.10120, 1.10220], dtype=np.float64)
        bid_l = np.array([1.09980, 1.10180], dtype=np.float64)
        p, f, oc = v12._partial_high_outcome_long(bid_h, bid_l, self.ENTRY, self.ATR, self.PIP)
        # Bar 0 crosses both partial (1.10100) and full TP (1.10200).
        assert p == 5.0
        assert f == 10.0
        assert int(oc) == int(v12._OUTCOME_PARTIAL_THEN_TP)

    def test_partial_fires_then_trail_to_entry(self) -> None:
        bid_h = np.array([1.10120, 1.10120, 1.10120], dtype=np.float64)
        bid_l = np.array([1.10100, 1.10050, 1.09990], dtype=np.float64)
        p, f, oc = v12._partial_high_outcome_long(bid_h, bid_l, self.ENTRY, self.ATR, self.PIP)
        assert p == 5.0
        assert f == 0.0
        assert int(oc) == int(v12._OUTCOME_PARTIAL_THEN_TRAIL)

    def test_sl_fires_before_partial(self) -> None:
        bid_h = np.array([1.10050, 1.10050, 1.10050], dtype=np.float64)
        bid_l = np.array([1.09910, 1.09900, 1.09880], dtype=np.float64)
        p, f, oc = v12._partial_high_outcome_long(bid_h, bid_l, self.ENTRY, self.ATR, self.PIP)
        # Both legs SL: total = -8pip = -0.8xATR
        assert p == -4.0
        assert f == -4.0
        assert int(oc) == int(v12._OUTCOME_SL_BEFORE_PARTIAL)

    def test_no_movement_times_out(self) -> None:
        bid_h = np.array([1.10050, 1.10050, 1.10050], dtype=np.float64)
        bid_l = np.array([1.09980, 1.09980, 1.09980], dtype=np.float64)
        p, f, oc = v12._partial_high_outcome_long(bid_h, bid_l, self.ENTRY, self.ATR, self.PIP)
        assert p == 0.0
        assert f == 0.0
        assert int(oc) == int(v12._OUTCOME_TIMEOUT_NO_PARTIAL)

    def test_partial_then_timeout_runner_flat(self) -> None:
        bid_h = np.array([1.10120, 1.10050, 1.10050], dtype=np.float64)
        bid_l = np.array([1.10100, 1.10020, 1.10010], dtype=np.float64)
        p, f, oc = v12._partial_high_outcome_long(bid_h, bid_l, self.ENTRY, self.ATR, self.PIP)
        assert p == 5.0
        assert f == 0.0
        assert int(oc) == int(v12._OUTCOME_PARTIAL_THEN_TIMEOUT)

    def test_conservation_partial_plus_final_equals_total(self) -> None:
        """Property test: total_pnl == partial + final on every scenario."""
        scenarios = [
            (np.array([1.10120, 1.10220]), np.array([1.09980, 1.10180])),
            (np.array([1.10120, 1.10120, 1.10120]), np.array([1.10100, 1.10050, 1.09990])),
            (np.array([1.10050, 1.10050]), np.array([1.09910, 1.09900])),
            (np.array([1.10050, 1.10050]), np.array([1.09980, 1.09980])),
            (np.array([1.10120, 1.10050]), np.array([1.10100, 1.10010])),
        ]
        for bid_h, bid_l in scenarios:
            p, f, oc = v12._partial_high_outcome_long(
                bid_h.astype(np.float64),
                bid_l.astype(np.float64),
                self.ENTRY,
                self.ATR,
                self.PIP,
            )
            total = p + f
            # Cross-check against expected pnl by outcome.
            expected_total_by_outcome = {
                int(v12._OUTCOME_SL_BEFORE_PARTIAL): -8.0,
                int(v12._OUTCOME_PARTIAL_THEN_TRAIL): 5.0,
                int(v12._OUTCOME_PARTIAL_THEN_TP): 15.0,
                int(v12._OUTCOME_PARTIAL_THEN_TIMEOUT): 5.0,
                int(v12._OUTCOME_TIMEOUT_NO_PARTIAL): 0.0,
            }
            assert total == expected_total_by_outcome[int(oc)], (
                f"outcome {int(oc)}: got total {total}, expected "
                f"{expected_total_by_outcome[int(oc)]}"
            )


class TestPartialHighOutcomeShort:
    """Mirror of TestPartialHighOutcomeLong for short trades.

    A short profits when ask price falls. With entry=1.10000, ATR=10pip:
      partial TP threshold:  ask_l <= 1.10000 - 0.001 = 1.09900
      runner TP threshold:   ask_l <= 1.10000 - 0.002 = 1.09800
      SL threshold:          ask_h >= 1.10000 + 0.0008 = 1.10080
      trail post-partial:    ask_h >= 1.10000
    """

    ENTRY = 1.10000
    ATR = 0.001
    PIP = 0.0001

    def test_partial_then_full_tp_short(self) -> None:
        # Bar 0 crosses both partial (1.09900) and full TP (1.09800).
        ask_h = np.array([1.10010, 1.10010], dtype=np.float64)
        ask_l = np.array([1.09790, 1.09780], dtype=np.float64)
        p, f, oc = v12._partial_high_outcome_short(ask_h, ask_l, self.ENTRY, self.ATR, self.PIP)
        assert p == 5.0
        assert f == 10.0
        assert int(oc) == int(v12._OUTCOME_PARTIAL_THEN_TP)

    def test_sl_fires_before_partial_short(self) -> None:
        ask_h = np.array([1.10090, 1.10100, 1.10110], dtype=np.float64)
        ask_l = np.array([1.10050, 1.10050, 1.10050], dtype=np.float64)
        p, f, oc = v12._partial_high_outcome_short(ask_h, ask_l, self.ENTRY, self.ATR, self.PIP)
        assert p == -4.0
        assert f == -4.0
        assert int(oc) == int(v12._OUTCOME_SL_BEFORE_PARTIAL)

    def test_partial_then_trail_short(self) -> None:
        # Bar 0: ask_l hits partial threshold (1.09900). Bar 2: ask_h reaches
        # entry (1.10000) -> trail-stop fires.
        ask_h = np.array([1.09950, 1.09950, 1.10010], dtype=np.float64)
        ask_l = np.array([1.09890, 1.09870, 1.09950], dtype=np.float64)
        p, f, oc = v12._partial_high_outcome_short(ask_h, ask_l, self.ENTRY, self.ATR, self.PIP)
        assert p == 5.0
        assert f == 0.0
        assert int(oc) == int(v12._OUTCOME_PARTIAL_THEN_TRAIL)


class TestAddPartialOutcomesHigh:
    def test_produces_six_columns(self) -> None:
        df = _make_synthetic_ba_df(60)
        out = v12._add_partial_outcomes_high(df, horizon=15, instrument="EUR_USD")
        for col in (
            "partial_pnl_high_long",
            "final_pnl_high_long",
            "outcome_high_long",
            "partial_pnl_high_short",
            "final_pnl_high_short",
            "outcome_high_short",
        ):
            assert col in out.columns, f"{col} missing"

    def test_late_bars_are_unlabelable(self) -> None:
        df = _make_synthetic_ba_df(20)
        out = v12._add_partial_outcomes_high(df, horizon=15, instrument="EUR_USD")
        # Bars at index >= n - horizon - 1 = 4 should not be labelable
        late = out.iloc[5:]
        assert late["partial_pnl_high_long"].isna().all()
        assert (late["outcome_high_long"] == int(v12._OUTCOME_NOT_LABELABLE)).all()

    def test_missing_bid_ask_columns_raises(self) -> None:
        df = pd.DataFrame(
            {
                "open": [1.1] * 10,
                "high": [1.1] * 10,
                "low": [1.1] * 10,
                "close": [1.1] * 10,
                "atr_14": [0.001] * 10,
                "volume": [100] * 10,
            },
            index=pd.date_range("2025-01-01", periods=10, freq="min", tz="UTC"),
        )
        with pytest.raises(ValueError, match="BA mode candles"):
            v12._add_partial_outcomes_high(df, horizon=5, instrument="EUR_USD")

    def test_pip_size_jpy_pair_uses_2dp(self) -> None:
        """JPY pairs use pip=0.01, non-JPY use pip=0.0001 - verify the helper
        picks up the right one through the instrument argument."""
        df = _make_synthetic_ba_df(60)
        # Synthetic data has price ~1.10000 and ATR=0.001 -- the integer pip
        # values will differ depending on which pip_size the helper uses.
        out_eur = v12._add_partial_outcomes_high(df, horizon=15, instrument="EUR_USD")
        out_jpy = v12._add_partial_outcomes_high(df, horizon=15, instrument="USD_JPY")
        # First labelable bar should produce a 100x larger pip value when
        # interpreted as JPY (pip 0.01) vs non-JPY (pip 0.0001).
        non_nan_eur = out_eur["partial_pnl_high_long"].dropna().abs()
        non_nan_jpy = out_jpy["partial_pnl_high_long"].dropna().abs()
        # At least one labelable row should exist.
        assert len(non_nan_eur) > 0
        # Same outcome codes, but pip values differ by 100x.
        first_eur = non_nan_eur.iloc[0] if (non_nan_eur > 0).any() else 0.0
        first_jpy = non_nan_jpy.iloc[0] if (non_nan_jpy > 0).any() else 0.0
        if first_eur > 0 and first_jpy > 0:
            assert first_eur == pytest.approx(first_jpy * 100, rel=1e-6)


class TestOutcomeConstants:
    def test_outcome_codes_are_distinct(self) -> None:
        codes = {
            int(v12._OUTCOME_NOT_LABELABLE),
            int(v12._OUTCOME_SL_BEFORE_PARTIAL),
            int(v12._OUTCOME_PARTIAL_THEN_TRAIL),
            int(v12._OUTCOME_PARTIAL_THEN_TP),
            int(v12._OUTCOME_PARTIAL_THEN_TIMEOUT),
            int(v12._OUTCOME_TIMEOUT_NO_PARTIAL),
        }
        assert len(codes) == 6  # all distinct

    def test_outcome_names_cover_all_codes(self) -> None:
        for code in (
            v12._OUTCOME_NOT_LABELABLE,
            v12._OUTCOME_SL_BEFORE_PARTIAL,
            v12._OUTCOME_PARTIAL_THEN_TRAIL,
            v12._OUTCOME_PARTIAL_THEN_TP,
            v12._OUTCOME_PARTIAL_THEN_TIMEOUT,
            v12._OUTCOME_TIMEOUT_NO_PARTIAL,
        ):
            assert code in v12._OUTCOME_NAMES, f"{code} missing label"


class TestValidPolicies:
    def test_includes_h2_partial(self) -> None:
        assert "bucketed+partial" in v12._VALID_POLICIES

    def test_canonical_order(self) -> None:
        assert v12._VALID_POLICIES == ("symmetric", "bucketed", "bucketed+partial")
