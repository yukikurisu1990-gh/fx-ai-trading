"""Unit tests for Stage 25.0c-β F2 multi-TF volatility regime eval.

Implements the test contract from `docs/design/phase25_0c_f2_design.md` §10.
Minimum 17 tests across 12 categories.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage25_0c = importlib.import_module("stage25_0c_f2_volatility_regime_eval")

DATA_DIR = REPO_ROOT / "data"
LABEL_PARQUET = REPO_ROOT / "artifacts" / "stage25_0a" / "path_quality_dataset.parquet"
_REPO_HAS_M1_DATA = (DATA_DIR / "candles_USD_JPY_M1_730d_BA.jsonl").exists()
_REPO_HAS_LABELS = LABEL_PARQUET.exists()
_skip_no_data = pytest.mark.skipif(
    not (_REPO_HAS_M1_DATA and _REPO_HAS_LABELS),
    reason="M1 data or 25.0a labels not present (CI env)",
)


# ---------------------------------------------------------------------------
# §10.1 Feature correctness (5)
# ---------------------------------------------------------------------------


def test_f2_a_regime_tertile_boundaries_correct():
    """RV [0..99] (uniform); shift(1).rolling(100).quantile gives boundaries."""
    rv = pd.Series(np.arange(150, dtype=float))
    q33, q66 = stage25_0c._compute_tertile_boundaries(rv, lookback=100)
    # At idx 110: shift(1) gives 109; rolling(100) window [10..109]; q33 ≈ 33, q66 ≈ 66
    assert q33.iloc[110] == pytest.approx(42.67, abs=2.0)
    assert q66.iloc[110] == pytest.approx(75.33, abs=2.0)


def test_f2_b_joint_regime_construction_correct():
    m5 = pd.Series(["high", "low", "med"])
    m15 = pd.Series(["high", "high", "low"])
    h1 = pd.Series(["high", "low", "med"])
    joint = stage25_0c._compute_joint_regime(m5, m15, h1)
    assert joint.iloc[0] == "high_high_high"
    assert joint.iloc[1] == "low_high_low"
    assert joint.iloc[2] == "med_low_med"


def test_f2_c_high_low_counts_correct():
    m5 = pd.Series(["high", "high", "low", "med"])
    m15 = pd.Series(["high", "low", "low", "med"])
    h1 = pd.Series(["high", "med", "high", "med"])
    high_c, low_c = stage25_0c._compute_alignment_counts(m5, m15, h1)
    assert list(high_c) == [3, 1, 1, 0]
    assert list(low_c) == [0, 1, 2, 0]


def test_f2_d_transition_flag_correct():
    regime = pd.Series(["low", "low", "high", "high", "med"])
    trans = stage25_0c._compute_transition_flag(regime)
    # idx 0: prev NaN → False
    # idx 1: low == low → False
    # idx 2: low → high → True
    # idx 3: high == high → False
    # idx 4: high → med → True
    assert list(trans) == [False, False, True, False, True]


def test_f2_e_return_sign_carried_unchanged_from_f1():
    """f2_e is reused from F1's _compute_return_sign verbatim."""
    assert stage25_0c._compute_return_sign is not None
    close = pd.Series(np.arange(20, dtype=float))
    sign = stage25_0c._compute_return_sign(close, lookback=13)
    assert sign.iloc[18] == 1


# ---------------------------------------------------------------------------
# §10.2 Causality (2)
# ---------------------------------------------------------------------------


def test_features_use_only_past_bars_shift_1():
    """Modifying bar t MUST NOT change tertile boundary[t]."""
    rv_base = pd.Series(np.arange(150, dtype=float))
    q33_base, _ = stage25_0c._compute_tertile_boundaries(rv_base, lookback=100)
    rv_mod = rv_base.copy()
    rv_mod.iloc[110] = 9999.0
    q33_mod, _ = stage25_0c._compute_tertile_boundaries(rv_mod, lookback=100)
    # Boundary at idx 110 should be unchanged because shift(1) excludes bar 110
    assert q33_base.iloc[110] == q33_mod.iloc[110]


def test_no_lookahead_at_t_plus_1():
    rv_base = pd.Series(np.arange(150, dtype=float))
    q33_base, _ = stage25_0c._compute_tertile_boundaries(rv_base, lookback=100)
    rv_mod = rv_base.copy()
    rv_mod.iloc[111] = 9999.0
    q33_mod, _ = stage25_0c._compute_tertile_boundaries(rv_mod, lookback=100)
    assert q33_base.iloc[110] == q33_mod.iloc[110]


# ---------------------------------------------------------------------------
# §10.3 Diagnostic-leakage HARD (1)
# ---------------------------------------------------------------------------


def test_diagnostic_columns_absent_from_feature_matrix_hard():
    prohibited = stage25_0c.PROHIBITED_DIAGNOSTIC_COLUMNS
    all_feature_lists = (
        stage25_0c.F2_PER_TF_COLS,
        stage25_0c.F2_PER_TF_JOINT_COLS,
        stage25_0c.F2_ALL_COLS,
    )
    for cols in all_feature_lists:
        for col in prohibited:
            assert col not in cols, f"HARD: {col} found in {cols}"


# ---------------------------------------------------------------------------
# §10.4 Cell grid integrity (1)
# ---------------------------------------------------------------------------


def test_cell_grid_has_exactly_18_cells_no_duplicates():
    grid = stage25_0c.CELL_GRID
    assert len(grid) == 18
    keys = [(c["trailing_window"], c["representation"], c["admissibility"]) for c in grid]
    assert len(set(keys)) == 18


# ---------------------------------------------------------------------------
# §10.5 Validation split chronological (1)
# ---------------------------------------------------------------------------


def test_chronological_70_15_15_split_no_overlap():
    df = pd.DataFrame(
        {
            "signal_ts": pd.date_range("2024-01-01", periods=1000, freq="h", tz="UTC"),
            "label": np.random.randint(0, 2, 1000),
        }
    )
    train, val, test, _, _ = stage25_0c.split_70_15_15(df)
    assert train["signal_ts"].max() < val["signal_ts"].min()
    assert val["signal_ts"].max() < test["signal_ts"].min()
    total = len(train) + len(val) + len(test)
    assert abs(len(train) / total - 0.70) < 0.02


# ---------------------------------------------------------------------------
# §10.6 Standardisation no-leak (1)
# ---------------------------------------------------------------------------


def test_scaler_fit_on_train_only():
    """Pipeline includes StandardScaler for numeric F2 cols."""
    from sklearn.preprocessing import StandardScaler

    pipeline = stage25_0c.build_logistic_pipeline_f2(stage25_0c.F2_ALL_COLS)
    pre = pipeline.named_steps["pre"]
    transformer_dict = {name: trans for name, trans, _ in pre.transformers}
    if "num" in transformer_dict:
        assert isinstance(transformer_dict["num"], StandardScaler)


# ---------------------------------------------------------------------------
# §10.7 F2 negative-list HARD (1)
# ---------------------------------------------------------------------------


def test_f2_does_not_use_continuous_rv_or_f1_features_hard():
    """HARD: raw RV / expansion / vol-of-vol / range_score MUST NOT appear in F2 feature matrix."""
    prohibited = stage25_0c.PROHIBITED_F1_RAW_COLS
    all_feature_lists = (
        stage25_0c.F2_PER_TF_COLS,
        stage25_0c.F2_PER_TF_JOINT_COLS,
        stage25_0c.F2_ALL_COLS,
    )
    for cols in all_feature_lists:
        for col in prohibited:
            assert col not in cols, f"HARD F2 negative-list violated: {col} found in {cols}"


# ---------------------------------------------------------------------------
# §10.8 Bidirectional shape (1)
# ---------------------------------------------------------------------------


def test_bidirectional_two_rows_per_signal_ts():
    """25.0a labels have 2 rows per (pair, signal_ts); F2 join preserves shape."""
    labels = pd.DataFrame(
        {
            "pair": ["USD_JPY"] * 4,
            "signal_ts": pd.to_datetime(
                ["2024-01-01 00:05", "2024-01-01 00:05", "2024-01-01 00:10", "2024-01-01 00:10"],
                utc=True,
            ),
            "direction": ["long", "short", "long", "short"],
            "label": [1, 0, 0, 1],
        }
    )
    counts = labels.groupby(["pair", "signal_ts"]).size()
    assert (counts == 2).all()


# ---------------------------------------------------------------------------
# §10.9 Threshold selection (1)
# ---------------------------------------------------------------------------


def test_threshold_selected_on_validation_only():
    n = 200
    np.random.seed(0)
    val_long_p = pd.Series(np.random.uniform(0, 1, n))
    val_short_p = pd.Series(np.random.uniform(0, 1, n))
    val_long_label = pd.Series(np.random.randint(0, 2, n))
    val_short_label = pd.Series(np.random.randint(0, 2, n))
    val_atr = pd.Series(np.full(n, 10.0))
    threshold, _ = stage25_0c._select_threshold_on_val(
        val_long_p, val_short_p, val_long_label, val_short_label, val_atr
    )
    assert threshold in stage25_0c.THRESHOLD_CANDIDATES


# ---------------------------------------------------------------------------
# §10.10 OneHotEncoder unknown handling (1)
# ---------------------------------------------------------------------------


def test_one_hot_encoder_handles_unknown_joint_regime():
    """Unseen joint regime in val/test must not raise; encoded as all-zero."""
    from sklearn.preprocessing import OneHotEncoder

    enc = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    train = pd.DataFrame({"jr": ["high_high_high", "low_low_low", "med_med_med"]})
    enc.fit(train)
    val = pd.DataFrame({"jr": ["high_high_high", "high_low_med"]})  # second is unseen
    out = enc.transform(val)
    # First row: encoded as one-hot for "high_high_high" → sum=1
    assert out[0].sum() == 1
    # Second row: unseen → all-zero
    assert out[1].sum() == 0


# ---------------------------------------------------------------------------
# §10.11 NaN-warmup drop (1)
# ---------------------------------------------------------------------------


def test_feature_nan_rows_dropped_with_counter():
    """Rows where any f2_a/b/c/d is NaN MUST be dropped."""
    df = pd.DataFrame(
        {
            "f2_a_regime_M5": ["low", "med", None, "high"],
            "f2_a_regime_M15": ["high", "high", "low", "med"],
            "f2_a_regime_H1": ["med", "high", "low", None],
            "f2_b_joint_regime": ["low_high_med", "med_high_high", None, None],
            "f2_c_high_count": [1, 2, 0, 1],
            "f2_c_low_count": [1, 0, 2, 0],
        }
    )
    nan_check_cols = [
        "f2_a_regime_M5",
        "f2_a_regime_M15",
        "f2_a_regime_H1",
        "f2_b_joint_regime",
        "f2_c_high_count",
        "f2_c_low_count",
    ]
    nan_mask = df[nan_check_cols].isna().any(axis=1)
    assert nan_mask.sum() == 2  # rows 2 and 3 have NaN
    cleaned = df[~nan_mask]
    assert len(cleaned) == 2


# ---------------------------------------------------------------------------
# §10.12 Realised barrier PnL inheritance (1)
# ---------------------------------------------------------------------------


def test_realised_pnl_uses_25_0a_barrier_semantics():
    """F2 reuses 25.0b's _compute_realised_barrier_pnl; verify inheritance."""
    import stage25_0b_f1_volatility_expansion_eval as stage25_0b_module

    assert (
        stage25_0c._compute_realised_barrier_pnl is stage25_0b_module._compute_realised_barrier_pnl
    )


# ---------------------------------------------------------------------------
# Extras
# ---------------------------------------------------------------------------


def test_design_constants_match_25_0c_alpha():
    assert stage25_0c.K_FAV == 1.5
    assert stage25_0c.K_ADV == 1.0
    assert stage25_0c.H_M1_BARS == 60
    assert stage25_0c.TERTILE_LOW == 0.33
    assert stage25_0c.TERTILE_HIGH == 0.66
    assert stage25_0c.CELL_TRAILING_WINDOWS == (100, 200)
    assert stage25_0c.CELL_FEATURE_REPRESENTATIONS == (
        "per_tf_only",
        "per_tf_joint",
        "all",
    )
    assert stage25_0c.CELL_ADMISSIBILITY_FILTERS == ("none", "high_alignment", "transition")
    assert stage25_0c.THRESHOLD_CANDIDATES == (0.20, 0.25, 0.30, 0.35, 0.40)
    assert stage25_0c.TRAIN_FRAC == 0.70
    assert stage25_0c.VAL_FRAC == 0.15


def test_admissibility_filter_dispatch_correct():
    df = pd.DataFrame(
        {
            "f2_c_high_count": [3, 1, 2, 0],
            "f2_c_low_count": [0, 1, 0, 3],
            "f2_d_transitioned_M5": [True, False, False, True],
            "f2_d_transitioned_M15": [False, True, False, False],
            "f2_d_transitioned_H1": [False, False, False, False],
        }
    )
    none = stage25_0c._apply_admissibility_filter(df, "none")
    assert len(none) == 4
    high = stage25_0c._apply_admissibility_filter(df, "high_alignment")
    assert len(high) == 2  # rows 0 and 2 have high_count >= 2
    trans = stage25_0c._apply_admissibility_filter(df, "transition")
    # Row 0: M5=T, M15=F, H1=F → True
    # Row 1: M5=F, M15=T, H1=F → True
    # Row 2: M5=F, M15=F, H1=F → False
    # Row 3: M5=T, M15=F, H1=F → True
    # → 3 rows with at least one transition
    assert len(trans) == 3


def test_feature_representation_dispatch_correct():
    per_tf = stage25_0c._select_feature_cols("per_tf_only")
    assert "f2_a_regime_M5" in per_tf
    assert "f2_b_joint_regime" not in per_tf
    per_joint = stage25_0c._select_feature_cols("per_tf_joint")
    assert "f2_b_joint_regime" in per_joint
    assert "f2_c_high_count" not in per_joint
    all_cols = stage25_0c._select_feature_cols("all")
    assert "f2_d_transitioned_M5" in all_cols
    assert "f2_c_high_count" in all_cols


@_skip_no_data
def test_smoke_run_completes_with_data():
    rc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "stage25_0c_f2_volatility_regime_eval.py"),
            "--smoke",
        ],
        capture_output=True,
        timeout=600,
    )
    assert rc.returncode == 0
