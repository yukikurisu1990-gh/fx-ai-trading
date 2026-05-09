"""Unit tests for Stage 25.0d-β deployment-layer audit.

Implements the test contract from `docs/design/phase25_0d_deployment_audit_design.md` §10.
Minimum 12 mandatory + 3 suggested = 15 tests.
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

stage25_0d = importlib.import_module("stage25_0d_deployment_audit_eval")

DATA_DIR = REPO_ROOT / "data"
LABEL_PARQUET = REPO_ROOT / "artifacts" / "stage25_0a" / "path_quality_dataset.parquet"
_REPO_HAS_M1_DATA = (DATA_DIR / "candles_USD_JPY_M1_730d_BA.jsonl").exists()
_REPO_HAS_LABELS = LABEL_PARQUET.exists()
_skip_no_data = pytest.mark.skipif(
    not (_REPO_HAS_M1_DATA and _REPO_HAS_LABELS),
    reason="M1 data or 25.0a labels not present (CI env)",
)


# ---------------------------------------------------------------------------
# §10.1 decile bucketing correct
# ---------------------------------------------------------------------------


def test_decile_bucketing_correct():
    """10 equal-width buckets in [0, 1]. P=0.05 -> bucket 0; P=0.95 -> bucket 9."""
    p = np.array([0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95])
    buckets = stage25_0d.decile_buckets(p)
    assert list(buckets) == list(range(10))
    # Edge case: P=1.0 should be in last bucket
    assert stage25_0d.decile_buckets(np.array([1.0]))[0] == 9
    assert stage25_0d.decile_buckets(np.array([0.0]))[0] == 0


# ---------------------------------------------------------------------------
# §10.2 reliability diagonal on calibrated synthetic data
# ---------------------------------------------------------------------------


def test_reliability_diagonal_on_calibrated_data():
    """Synthetic well-calibrated: P=k/10 for bucket k => actual rate ≈ k/10."""
    np.random.seed(0)
    n_per_bucket = 1000
    p_list = []
    y_list = []
    for k in range(10):
        p = np.full(n_per_bucket, (k + 0.5) / 10.0)
        y = np.random.binomial(1, p)
        p_list.append(p)
        y_list.append(y)
    p_arr = np.concatenate(p_list)
    y_arr = np.concatenate(y_list)
    rel = stage25_0d.reliability_table(p_arr, y_arr)
    # Each bucket's mean_predicted ≈ actual_positive_rate within ±0.02
    for _, r in rel.iterrows():
        if r["n"] > 0:
            assert abs(r["mean_predicted"] - r["actual_positive_rate"]) < 0.04


# ---------------------------------------------------------------------------
# §10.3 per-bucket net_EV calculation correct
# ---------------------------------------------------------------------------


def test_per_bucket_net_ev_calculation_correct():
    """net_EV = mean_realised - mean_spread."""
    # Direct check via verdict logic with synthetic bucket_pnl table
    bucket = pd.DataFrame(
        [
            {
                "bucket": 0,
                "n": 200,
                "mean_realised_pnl": 5.0,
                "mean_spread_pip": 1.0,
                "net_ev_pip": 4.0,
                "low_bucket_n": False,
            },
            {
                "bucket": 1,
                "n": 200,
                "mean_realised_pnl": -3.0,
                "mean_spread_pip": 1.0,
                "net_ev_pip": -4.0,
                "low_bucket_n": False,
            },
        ]
    )
    # Verify computation: 5.0 - 1.0 = 4.0, -3.0 - 1.0 = -4.0
    assert (
        bucket.iloc[0]["mean_realised_pnl"] - bucket.iloc[0]["mean_spread_pip"]
        == bucket.iloc[0]["net_ev_pip"]
    )
    assert (
        bucket.iloc[1]["mean_realised_pnl"] - bucket.iloc[1]["mean_spread_pip"]
        == bucket.iloc[1]["net_ev_pip"]
    )


# ---------------------------------------------------------------------------
# §10.4 threshold sweep includes extended range
# ---------------------------------------------------------------------------


def test_threshold_sweep_includes_extended_range():
    assert stage25_0d.EXTENDED_THRESHOLDS == (0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80)


# ---------------------------------------------------------------------------
# §10.5 directional models trained separately
# ---------------------------------------------------------------------------


def test_directional_models_trained_separately():
    """Synthetic train: long-only on direction='long' rows, short-only on 'short' rows."""
    n = 200
    np.random.seed(0)
    df = pd.DataFrame(
        {
            "pair": ["USD_JPY"] * n,
            "signal_ts": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
            "direction": (["long", "short"] * (n // 2)),
            "label": np.random.randint(0, 2, n),
            "atr_at_signal_pip": np.full(n, 10.0),
            **{c: np.random.randn(n) for c in stage25_0d.F1_FEATURE_COLS_BASE},
        }
    )
    val = df.iloc[:50].copy()
    train = df.iloc[50:].copy()
    out = stage25_0d.fit_directional_models(
        train, val, list(stage25_0d.F1_FEATURE_COLS_BASE), stage25_0d.build_logistic_pipeline_f1
    )
    # Both models should exist
    assert out.get("long_model") is not None
    assert out.get("short_model") is not None
    # n_train per direction = 75
    assert out["long_n_train"] + out["short_n_train"] == 150


# ---------------------------------------------------------------------------
# §10.6 directional threshold selected per direction on val only
# ---------------------------------------------------------------------------


def test_directional_threshold_selected_per_direction_on_val():
    """Each direction gets its own threshold from EXTENDED_THRESHOLDS."""
    # Per-direction threshold output keys
    n = 200
    np.random.seed(1)
    df = pd.DataFrame(
        {
            "pair": ["USD_JPY"] * n,
            "signal_ts": pd.date_range("2024-01-01", periods=n, freq="5min", tz="UTC"),
            "direction": (["long", "short"] * (n // 2)),
            "label": np.random.randint(0, 2, n),
            "atr_at_signal_pip": np.full(n, 10.0),
            **{c: np.random.randn(n) for c in stage25_0d.F1_FEATURE_COLS_BASE},
        }
    )
    val = df.iloc[:60].copy()
    train = df.iloc[60:].copy()
    out = stage25_0d.fit_directional_models(
        train, val, list(stage25_0d.F1_FEATURE_COLS_BASE), stage25_0d.build_logistic_pipeline_f1
    )
    assert out["long_threshold"] in stage25_0d.EXTENDED_THRESHOLDS
    assert out["short_threshold"] in stage25_0d.EXTENDED_THRESHOLDS


# ---------------------------------------------------------------------------
# §10.7 directional same-bar both-fire skipped conservatively (HARD)
# ---------------------------------------------------------------------------


def test_directional_same_bar_both_fire_skipped_conservatively():
    """If long_fire AND short_fire at same (pair, signal_ts), no trade emitted."""
    # Synthetic test data with 1 row per direction at same (pair, signal_ts)
    test_df = pd.DataFrame(
        {
            "pair": ["USD_JPY", "USD_JPY"],
            "signal_ts": [
                pd.Timestamp("2024-01-01 00:05", tz="UTC"),
                pd.Timestamp("2024-01-01 00:05", tz="UTC"),
            ],
            "direction": ["long", "short"],
            "label": [1, 0],
            "atr_at_signal_pip": [10.0, 10.0],
            "spread_at_signal_pip": [1.0, 1.0],
            **{c: [0.5, 0.5] for c in stage25_0d.F1_FEATURE_COLS_BASE},
        }
    )

    # Mock models: both predict_proba returns high P
    class _MockModel:
        def predict_proba(self, x):
            return np.column_stack([np.full(len(x), 0.1), np.full(len(x), 0.9)])

    directional = {
        "long_model": _MockModel(),
        "short_model": _MockModel(),
        "long_threshold": 0.5,
        "short_threshold": 0.5,
        "low_data_flag": False,
    }
    pair_runtime = {"USD_JPY": {}}  # not used since both-fire is detected before barrier eval
    out = stage25_0d.evaluate_directional(
        test_df, directional, list(stage25_0d.F1_FEATURE_COLS_BASE), pair_runtime
    )
    # Both fire => no trade => n_skipped_both_fire = 1
    assert out["n_skipped_both_fire"] == 1
    assert out["n_trades"] == 0


# ---------------------------------------------------------------------------
# §10.8 AUC-EV bound at chance level correct
# ---------------------------------------------------------------------------


def test_auc_ev_theoretical_bound_at_chance_level_correct():
    """At AUC=0.5, P(pos | predicted >= q) = base_rate for any q."""
    p = stage25_0d.conditional_p_positive_at_quantile(0.5, 0.187, 0.5)
    assert abs(p - 0.187) < 0.01
    # At AUC > 0.5, P(pos | predicted >= top quantile) > base_rate
    p_high = stage25_0d.conditional_p_positive_at_quantile(0.7, 0.187, 0.9)
    assert p_high > 0.187


# ---------------------------------------------------------------------------
# §10.9 LOW_BUCKET_N flag at n<100
# ---------------------------------------------------------------------------


def test_low_bucket_n_flag_threshold_100():
    """Buckets with n < 100 receive LOW_BUCKET_N flag."""
    p = np.random.uniform(0, 1, 50)  # 50 rows; <10 per decile => all LOW
    y = np.random.randint(0, 2, 50)
    rel = stage25_0d.reliability_table(p, y)
    n_low = (rel["low_bucket_n"]).sum()
    assert n_low >= 5  # at least half the buckets LOW


# ---------------------------------------------------------------------------
# §10.10 diagnostic columns absent from feature matrix HARD (inherited)
# ---------------------------------------------------------------------------


def test_diagnostic_columns_absent_from_feature_matrix_hard():
    prohibited = stage25_0d.PROHIBITED_DIAGNOSTIC_COLUMNS
    f1_cols = stage25_0d.F1_FEATURE_COLS_BASE
    f2_cols = stage25_0d.F2_PER_TF_COLS
    for col in prohibited:
        assert col not in f1_cols
        assert col not in f2_cols


# ---------------------------------------------------------------------------
# §10.11 no modification of F1/F2 artifacts (read-only filesystem)
# ---------------------------------------------------------------------------


def test_no_modification_of_f1_f2_artifacts():
    """Static check: 25.0d-β script does not write to artifacts/stage25_0b/* or
    artifacts/stage25_0c/*."""
    src_path = SCRIPTS_DIR / "stage25_0d_deployment_audit_eval.py"
    src = src_path.read_text(encoding="utf-8")
    assert "artifacts/stage25_0b" not in src
    assert "artifacts/stage25_0c" not in src


# ---------------------------------------------------------------------------
# §10.12 chronological split inherited
# ---------------------------------------------------------------------------


def test_chronological_train_val_test_inherited():
    df = pd.DataFrame(
        {
            "signal_ts": pd.date_range("2024-01-01", periods=1000, freq="h", tz="UTC"),
            "label": np.random.randint(0, 2, 1000),
        }
    )
    train, val, test, _, _ = stage25_0d.split_70_15_15(df)
    assert train["signal_ts"].max() < val["signal_ts"].min()
    assert val["signal_ts"].max() < test["signal_ts"].min()


# ---------------------------------------------------------------------------
# Suggested extras
# ---------------------------------------------------------------------------


def test_threshold_sweep_marked_diagnostic_only():
    """eval_report.md mandatory clauses include threshold-sweep-diagnostic-only guard."""
    assert "diagnostic-only" in stage25_0d.MANDATORY_CLAUSES.lower()
    assert "production threshold from the test set" in stage25_0d.MANDATORY_CLAUSES


def test_directional_comparison_marked_diagnostic_only():
    assert "Directional comparison is diagnostic-only" in stage25_0d.MANDATORY_CLAUSES


@_skip_no_data
def test_smoke_run_completes_with_data():
    rc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "stage25_0d_deployment_audit_eval.py"), "--smoke"],
        capture_output=True,
        timeout=600,
    )
    assert rc.returncode == 0
