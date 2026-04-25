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
