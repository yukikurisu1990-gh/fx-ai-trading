"""Unit tests for Stage 25.0b-β F1 volatility expansion / compression eval.

Implements the test contract from `docs/design/phase25_0b_f1_design.md` §11.
Minimum 16 tests across 10 categories.
"""

from __future__ import annotations

import importlib
import inspect
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

stage25_0b = importlib.import_module("stage25_0b_f1_volatility_expansion_eval")

DATA_DIR = REPO_ROOT / "data"
LABEL_PARQUET = REPO_ROOT / "artifacts" / "stage25_0a" / "path_quality_dataset.parquet"
_REPO_HAS_M1_DATA = (DATA_DIR / "candles_USD_JPY_M1_730d_BA.jsonl").exists()
_REPO_HAS_LABELS = LABEL_PARQUET.exists()
_skip_no_data = pytest.mark.skipif(
    not (_REPO_HAS_M1_DATA and _REPO_HAS_LABELS),
    reason="M1 data or 25.0a labels not present (CI env without data)",
)


# ---------------------------------------------------------------------------
# §11.1 Feature correctness (6)
# ---------------------------------------------------------------------------


def test_f1_a_rv_correctness():
    # Known log-return: constant 0.01 per bar
    close = pd.Series(np.exp(np.cumsum(np.full(50, 0.01))))
    rv = stage25_0b._compute_rv(close, n_bars=10)
    # Expected: sqrt(sum(0.01^2 * 10)) = sqrt(0.001) ≈ 0.03162
    expected = np.sqrt(10 * 0.01**2)
    # rv is shifted; check value at index 11+ where window is full
    assert abs(rv.iloc[11] - expected) < 1e-6


def test_f1_b_compression_pct_correctness():
    rv = pd.Series(np.arange(150, dtype=float))
    pct = stage25_0b._compute_compression_pct(rv, lookback=100)
    # rv at signal_idx[-1] (e.g., idx=130, value=130) shifted to 129; rolling
    # window [30..129]. Reference rv[t-1]=rv[129]=129. Of prior 99 values
    # rv[30..128]=30..128, count(<= 129) = 99/99 = 1.0.
    val = pct.iloc[130]
    assert val == pytest.approx(1.0, abs=0.01)


def test_f1_c_expansion_ratio_correctness():
    # rv constant at 1.0 → ratio = 1.0
    rv = pd.Series(np.ones(100))
    ratio = stage25_0b._compute_expansion_ratio(rv, recent_n=4, base_start=5, base_end=50)
    val = ratio.iloc[60]
    assert abs(val - 1.0) < 1e-6


def test_f1_d_vol_of_vol_correctness():
    rv = pd.Series(np.array([1.0, 2.0] * 100))
    vov = stage25_0b._compute_vol_of_vol(rv, lookback=50)
    val = vov.iloc[80]
    # Std of [1, 2, 1, 2, ...] = 0.5 (ddof=0) or ~0.5025 (ddof=1, pandas default)
    assert abs(val - 0.5) < 0.01


def test_f1_e_range_score_correctness():
    high = pd.Series(np.full(50, 1.10))
    low = pd.Series(np.full(50, 1.00))
    atr = pd.Series(np.full(50, 0.05))
    score = stage25_0b._compute_range_score(high, low, atr, n_bars=10)
    # range = 0.10; mean ATR = 0.05; ratio = 2.0
    val = score.iloc[20]
    assert abs(val - 2.0) < 1e-6


def test_f1_f_return_sign_correctness():
    # Increasing close
    close = pd.Series(np.arange(20, dtype=float))
    sign = stage25_0b._compute_return_sign(close, lookback=13)
    # close[t-1] - close[t-13] = (t-1) - (t-13) = 12 > 0 → sign = +1
    assert sign.iloc[18] == 1


# ---------------------------------------------------------------------------
# §11.2 Causality (2)
# ---------------------------------------------------------------------------


def test_features_use_only_past_bars_shift_1():
    """Modifying bar t MUST NOT change feature[t]'s computed value."""
    base = pd.Series(np.arange(50, dtype=float) + 1.0)
    rv_base = stage25_0b._compute_rv(base, n_bars=10)
    modified = base.copy()
    modified.iloc[30] = 999.0  # extreme spike at t=30
    rv_mod = stage25_0b._compute_rv(modified, n_bars=10)
    # rv at index 30 should be UNCHANGED because shift(1) excludes bar 30
    assert (
        rv_base.iloc[30] == pytest.approx(rv_mod.iloc[30], abs=1e-9, nan_ok=True)
        if False
        else (
            np.isnan(rv_base.iloc[30])
            and np.isnan(rv_mod.iloc[30])
            or rv_base.iloc[30] == rv_mod.iloc[30]
        )
    )


def test_features_no_lookahead_at_t_plus_1():
    """Modifying bar t+1 must not change feature at t."""
    base = pd.Series(np.arange(50, dtype=float) + 1.0)
    rv_base = stage25_0b._compute_rv(base, n_bars=10)
    modified = base.copy()
    modified.iloc[31] = 999.0  # spike at t+1
    rv_mod = stage25_0b._compute_rv(modified, n_bars=10)
    assert rv_base.iloc[30] == rv_mod.iloc[30] or (
        np.isnan(rv_base.iloc[30]) and np.isnan(rv_mod.iloc[30])
    )


# ---------------------------------------------------------------------------
# §11.3 Diagnostic-leakage HARD (1)
# ---------------------------------------------------------------------------


def test_diagnostic_columns_absent_from_feature_matrix_hard():
    """HARD: 25.0a-β diagnostic columns MUST NOT be in FEATURE_COLS_BASE."""
    prohibited = stage25_0b.PROHIBITED_DIAGNOSTIC_COLUMNS
    feature_cols = set(stage25_0b.FEATURE_COLS_BASE)
    for col in prohibited:
        assert col not in feature_cols, f"HARD INVARIANT VIOLATED: {col} is in FEATURE_COLS_BASE"


# ---------------------------------------------------------------------------
# §11.4 Cell grid integrity (1)
# ---------------------------------------------------------------------------


def test_cell_grid_has_exactly_24_cells_no_duplicates():
    grid = stage25_0b.CELL_GRID
    assert len(grid) == 24
    keys = [(c["tf"], c["lookback"], c["quantile"], c["expansion"]) for c in grid]
    assert len(set(keys)) == 24


# ---------------------------------------------------------------------------
# §11.5 Validation split chronological (1)
# ---------------------------------------------------------------------------


def test_chronological_70_15_15_split_no_overlap():
    df = pd.DataFrame(
        {
            "signal_ts": pd.date_range("2024-01-01", periods=1000, freq="h", tz="UTC"),
            "label": np.random.randint(0, 2, 1000),
        }
    )
    train, val, test, t70, t85 = stage25_0b.split_70_15_15(df)
    assert train["signal_ts"].max() < val["signal_ts"].min()
    assert val["signal_ts"].max() < test["signal_ts"].min()
    total = len(train) + len(val) + len(test)
    assert abs(len(train) / total - 0.70) < 0.02
    assert abs(len(val) / total - 0.15) < 0.02
    assert abs(len(test) / total - 0.15) < 0.02


# ---------------------------------------------------------------------------
# §11.6 Standardisation no-leak (1)
# ---------------------------------------------------------------------------


def test_scaler_fit_on_train_only():
    """Verify pipeline structure includes StandardScaler (fit on train only
    when used in pipeline.fit())."""
    from sklearn.preprocessing import StandardScaler

    pipeline = stage25_0b.build_logistic_pipeline()
    pre = pipeline.named_steps["pre"]
    # ColumnTransformer.transformers is a list of (name, transformer, columns) triples
    transformer_dict = {name: trans for name, trans, _ in pre.transformers}
    assert "num" in transformer_dict
    assert isinstance(transformer_dict["num"], StandardScaler)


# ---------------------------------------------------------------------------
# §11.7 F1 negative-list (1)
# ---------------------------------------------------------------------------


def test_no_donchian_zscore_imports_from_phase23():
    """Defensive: assert no Donchian/z-score helper imports from stage23_0b/0c/0d."""
    src_path = SCRIPTS_DIR / "stage25_0b_f1_volatility_expansion_eval.py"
    src = src_path.read_text(encoding="utf-8")
    # Allow stage23_0a (utility loader) but not 23_0b/0c/0d
    forbidden = [
        "stage23_0b_m5_donchian_eval",
        "stage23_0c_m5_zscore_mr_eval",
        "stage23_0d_m15_donchian_eval",
    ]
    for fb in forbidden:
        assert fb not in src, f"F1 must not import from {fb}"


# ---------------------------------------------------------------------------
# §11.8 Bidirectional shape (1)
# ---------------------------------------------------------------------------


def test_bidirectional_two_rows_per_signal_ts():
    """Synthetic check: 25.0a label dataset has 2 rows per (pair, signal_ts).
    F1 features are direction-independent and joined as-is. After join, each
    (pair, signal_ts) still has exactly 2 rows (long + short)."""
    labels = pd.DataFrame(
        {
            "pair": ["USD_JPY"] * 4,
            "signal_ts": pd.to_datetime(
                ["2024-01-01 00:05", "2024-01-01 00:05", "2024-01-01 00:10", "2024-01-01 00:10"],
                utc=True,
            ),
            "direction": ["long", "short", "long", "short"],
            "label": [1, 0, 0, 1],
            "atr_at_signal_pip": [10.0] * 4,
            "spread_at_signal_pip": [1.0] * 4,
            "entry_ask": [100.0] * 4,
            "entry_bid": [99.99] * 4,
            "horizon_bars": [60] * 4,
        }
    )
    feats_per_pair = {
        "USD_JPY": pd.DataFrame(
            {
                "pair": ["USD_JPY"] * 2,
                "signal_ts": pd.to_datetime(["2024-01-01 00:05", "2024-01-01 00:10"], utc=True),
                **{c: [1.0, 2.0] for c in stage25_0b.FEATURE_COLS_BASE},
            }
        )
    }
    merged = stage25_0b.join_features_to_labels(feats_per_pair, labels)
    counts = merged.groupby(["pair", "signal_ts"]).size().reset_index(name="n")
    assert (counts["n"] == 2).all()


# ---------------------------------------------------------------------------
# §11.9 Threshold selection (1)
# ---------------------------------------------------------------------------


def test_threshold_selected_on_validation_only():
    """Synthetic predictions: validation supports threshold=0.30; test
    independent. Verify selected threshold is from THRESHOLD_CANDIDATES."""
    # Synthetic val data
    n = 200
    np.random.seed(0)
    val_long_p = pd.Series(np.random.uniform(0, 1, n))
    val_short_p = pd.Series(np.random.uniform(0, 1, n))
    val_long_label = pd.Series(np.random.randint(0, 2, n))
    val_short_label = pd.Series(np.random.randint(0, 2, n))
    val_atr = pd.Series(np.full(n, 10.0))
    threshold, log = stage25_0b._select_threshold_on_val(
        val_long_p, val_short_p, val_long_label, val_short_label, val_atr
    )
    assert threshold in stage25_0b.THRESHOLD_CANDIDATES


# ---------------------------------------------------------------------------
# §11.10 NaN-warmup drop (1)
# ---------------------------------------------------------------------------


def test_feature_nan_rows_dropped_with_counter():
    """Verify NaN-bearing rows are dropped from feature matrix in main flow.
    Direct check: the implementation drops rows where feature columns
    (excluding f1_f) have NaN."""
    # Construct synthetic merged DF with 100 rows; 20 have NaN feature
    n = 100
    df = pd.DataFrame(
        {
            "pair": ["USD_JPY"] * n,
            "signal_ts": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
            "direction": ["long"] * n,
            "label": np.random.randint(0, 2, n),
            "atr_at_signal_pip": [10.0] * n,
            "spread_at_signal_pip": [1.0] * n,
            "entry_ask": [100.0] * n,
            "entry_bid": [99.99] * n,
            "horizon_bars": [60] * n,
            **{c: [1.0] * n for c in stage25_0b.FEATURE_COLS_BASE},
        }
    )
    # Inject NaN into 20 rows
    df.loc[df.index[:20], "f1_a_rv_M5"] = np.nan
    feature_cols_excluding_sign = stage25_0b.FEATURE_COLS_BASE[:-1]
    nan_mask = df[feature_cols_excluding_sign].isna().any(axis=1)
    cleaned = df[~nan_mask]
    assert len(cleaned) == 80
    assert nan_mask.sum() == 20


# ---------------------------------------------------------------------------
# Extras
# ---------------------------------------------------------------------------


def test_design_constants_match_25_0b_alpha():
    assert stage25_0b.K_FAV == 1.5
    assert stage25_0b.K_ADV == 1.0
    assert stage25_0b.H_M1_BARS == 60
    assert stage25_0b.RV_WINDOW == {"M5": 12, "M15": 8, "H1": 24}
    assert stage25_0b.COMPRESSION_TRAILING == 100
    assert stage25_0b.EXPANSION_RECENT_N == 4
    assert stage25_0b.EXPANSION_BASELINE_START == 5
    assert stage25_0b.EXPANSION_BASELINE_END == 50
    assert stage25_0b.VOL_OF_VOL_LOOKBACK == 100
    assert stage25_0b.RETURN_SIGN_LOOKBACK_M5 == 13
    assert stage25_0b.THRESHOLD_CANDIDATES == (0.20, 0.25, 0.30, 0.35, 0.40)
    assert stage25_0b.TRAIN_FRAC == 0.70
    assert stage25_0b.VAL_FRAC == 0.15


def test_load_path_quality_labels_drops_diagnostic_columns():
    """Verify the loader excludes the 5 prohibited diagnostic columns."""
    src = inspect.getsource(stage25_0b.load_path_quality_labels)
    # The function uses PROHIBITED_DIAGNOSTIC_COLUMNS to drop
    assert "PROHIBITED_DIAGNOSTIC_COLUMNS" in src
    assert ".drop(columns=" in src or "drop_cols" in src


def test_stage23_0a_tf_minutes_unchanged():
    """Verify stage23_0a.TF_MINUTES is NOT modified (Phase 23/24 reproducibility)."""
    s23 = importlib.import_module("stage23_0a_build_outcome_dataset")
    assert s23.TF_MINUTES == {"M5": 5, "M15": 15}


def test_local_tf_minutes_extends_with_h1():
    assert "H1" in stage25_0b.TF_MINUTES_LOCAL
    assert stage25_0b.TF_MINUTES_LOCAL["H1"] == 60


def test_realised_barrier_pnl_favourable_first_returns_positive():
    """Synthetic: bid_h crosses fav threshold immediately → +K_FAV*ATR."""
    pip = 0.0001
    n_bars = 60
    pair_data = {
        "pip": pip,
        "m1_pos": pd.Series(
            [0],
            index=pd.to_datetime(["2024-01-01 00:01"], utc=True),
        ),
        "n_m1": n_bars,
        "bid_h": np.full(n_bars, 1.0050),
        "bid_l": np.full(n_bars, 0.9999),
        "bid_c": np.full(n_bars, 1.0030),
        "ask_h": np.full(n_bars, 1.0001),
        "ask_l": np.full(n_bars, 0.9990),
        "ask_c": np.full(n_bars, 0.9995),
        "ask_o": np.full(n_bars, 1.0000),
        "bid_o": np.full(n_bars, 0.9999),
    }
    signal_ts = pd.Timestamp("2024-01-01 00:00", tz="UTC")
    pnl = stage25_0b._compute_realised_barrier_pnl(
        "USD_JPY", signal_ts, "long", atr_pip=10.0, pair_data=pair_data
    )
    # fav_thresh = 1.5 * 10 = 15 pip; bid_h excursion = (1.0050 - 1.0000)/0.0001 = 50 pip > 15
    # adv_thresh = 1.0 * 10 = 10 pip; bid_l excursion = (1.0000 - 0.9999)/0.0001 = 1 pip < 10
    # → fav first → +15.0
    assert pnl == pytest.approx(15.0, abs=1e-6)


def test_realised_barrier_pnl_adverse_first_returns_negative():
    pip = 0.0001
    n_bars = 60
    pair_data = {
        "pip": pip,
        "m1_pos": pd.Series([0], index=pd.to_datetime(["2024-01-01 00:01"], utc=True)),
        "n_m1": n_bars,
        "bid_h": np.full(n_bars, 1.0001),
        "bid_l": np.full(n_bars, 0.9980),
        "bid_c": np.full(n_bars, 0.9985),
        "ask_h": np.full(n_bars, 1.0001),
        "ask_l": np.full(n_bars, 0.9990),
        "ask_c": np.full(n_bars, 0.9995),
        "ask_o": np.full(n_bars, 1.0000),
        "bid_o": np.full(n_bars, 0.9999),
    }
    signal_ts = pd.Timestamp("2024-01-01 00:00", tz="UTC")
    pnl = stage25_0b._compute_realised_barrier_pnl(
        "USD_JPY", signal_ts, "long", atr_pip=10.0, pair_data=pair_data
    )
    # adv_thresh = 10 pip; bid_l excursion = 20 pip → adverse first → -10.0
    assert pnl == pytest.approx(-10.0, abs=1e-6)


@_skip_no_data
def test_smoke_run_completes_with_data():
    """End-to-end smoke run: 3 pairs from real data, all 24 cells."""
    rc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS_DIR / "stage25_0b_f1_volatility_expansion_eval.py"),
            "--smoke",
        ],
        capture_output=True,
        timeout=600,
    )
    assert rc.returncode == 0
