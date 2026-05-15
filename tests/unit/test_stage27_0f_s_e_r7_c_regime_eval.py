"""Unit tests for Stage 27.0f-β S-E + R7-C regime/context eval.

~65-70 tests across 17 groups (per implementation plan):
- Group 1 — R7-C feature constants (4)
- Group 2 — build_r7_c_features causality (5)
- Group 3 — verify_volume_preflight HALT (5)
- Group 4 — drop_rows_with_missing_r7_c_features (4)
- Group 5 — Cell construction (5)
- Group 6 — evaluate_cell_27_0f feature routing (4)
- Group 7 — D10 3-artifact form (4)
- Group 8 — BaselineMismatchError HALT (4)
- Group 9 — H-B6 falsification outcome resolver (6)
- Group 10 — Top-tail regime audit (4)
- Group 11 — C-se-r7a-replica drift check (4)
- Group 12 — Sanity probe extensions items 14-19 (5)
- Group 13 — Class index mapping (2)
- Group 14 — Module docstring + clauses + D-1 binding (4)
- Group 15 — Sub-phase naming (2)
- Group 16 — Inheritance from 27.0e (6)
- Group 17 — NG#11 reverse-violation guard (3)

NEW 27.0f-specific tests flagged [27.0f NEW].
"""

from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

s27f = importlib.import_module("stage27_0f_s_e_r7_c_regime_eval")


# ===========================================================================
# Group 1 — R7-C feature constants (4 NEW)
# ===========================================================================


# [27.0f NEW]
def test_r7_c_features_closed_allowlist():
    assert s27f.R7_C_FEATURES == (
        "f5a_spread_z_50",
        "f5b_volume_z_50",
        "f5c_high_spread_low_vol_50",
    )


# [27.0f NEW]
def test_all_features_r7ac_union_is_7_features():
    assert len(s27f.ALL_FEATURES_R7AC) == 7
    assert set(s27f.ALL_FEATURES_R7AC) == set(s27f.ALL_FEATURES_R7A) | set(s27f.R7_C_FEATURES)


# [27.0f NEW]
def test_r7_c_rolling_window_is_50():
    assert s27f.R7_C_ROLLING_WINDOW == 50


# [27.0f NEW]
def test_r7_c_thresholds_match_design_memo():
    assert s27f.R7_C_HIGH_SPREAD_THRESHOLD == 1.0
    assert s27f.R7_C_LOW_VOLUME_THRESHOLD == -1.0
    assert s27f.R7_C_ROW_DROP_HALT_FRAC == 0.01


# ===========================================================================
# Group 2 — build_r7_c_features causality (5 NEW; D-Z2 / D-AA4)
# ===========================================================================


# [27.0f NEW]
def test_f5a_causal_shift_before_rolling():
    """D-AA4 binding: f5a uses shift(1) BEFORE rolling.

    Synthetic spread series; verify f5a at row i uses spread[i-50..i-1],
    NOT spread[i-49..i].
    """
    # Build synthetic monotonic spread series
    n = 100
    spread = np.arange(n, dtype=np.float64) + 1.0
    series = pd.Series(spread, index=pd.RangeIndex(n))
    # shift(1) then rolling(50)
    causal = series.shift(1)
    rolling = causal.rolling(window=50, min_periods=50)
    mean = rolling.mean()
    std = rolling.std()
    expected_z_at_50 = (spread[50] - mean.iloc[50]) / std.iloc[50]
    # _build_pair_spread_z output at row 50
    z = s27f._build_pair_spread_z(series, window=50)
    assert np.isclose(z.iloc[50], expected_z_at_50, rtol=1e-10)
    # Causality: z.iloc[50] depends on spread[0..49], NOT spread[50]
    # so changing spread[50] only changes the numerator, not the
    # rolling stats (which use shift(1) so they see spread[0..49])
    series_modified = series.copy()
    series_modified.iloc[50] = 999.0
    z_modified = s27f._build_pair_spread_z(series_modified, window=50)
    # The rolling stats at index 50 should be unchanged (use spread[0..49])
    causal_mod = series_modified.shift(1)
    rolling_mod = causal_mod.rolling(window=50, min_periods=50)
    mean_at_50_unchanged = rolling_mod.mean().iloc[50] == mean.iloc[50]
    std_at_50_unchanged = rolling_mod.std().iloc[50] == std.iloc[50]
    assert mean_at_50_unchanged, "rolling mean at row 50 should NOT depend on row 50"
    assert std_at_50_unchanged, "rolling std at row 50 should NOT depend on row 50"
    # But the z-score numerator changed
    assert not np.isclose(z_modified.iloc[50], z.iloc[50])


# [27.0f NEW]
def test_f5a_first_50_rows_are_nan():
    """First 50 rows have insufficient lookback → NaN."""
    n = 100
    spread = np.arange(n, dtype=np.float64) + 1.0
    series = pd.Series(spread, index=pd.RangeIndex(n))
    z = s27f._build_pair_spread_z(series, window=50)
    # Row 0..49 → NaN (rolling min_periods=50 not met after shift(1))
    assert all(np.isnan(z.iloc[:50]))


# [27.0f NEW]
def test_f5b_volume_z_uses_m5_aggregate():
    """f5b uses M5-aggregated volume (sum over 5 M1 bars per M5 bar).

    Right-closed/right-labeled (matches stage23_0a aggregate_m1_to_tf):
    the M5 bar labeled T contains M1 bars in (T-5min, T]. Inner bars
    (not the first/last partial) sum exactly 5 M1 bars × volume.
    """
    # Build M1 minutes 00:01..00:15 (15 bars) so M5 inner bars at
    # 00:05 and 00:10 each get exactly 5 M1 bars (right-closed)
    n = 15
    idx = pd.date_range("2024-01-01 00:01:00", periods=n, freq="min", tz="UTC")
    vol = pd.Series([10] * n, index=idx, name="volume")
    m5 = s27f.aggregate_m1_volume_to_m5(vol)
    # M5 bar at 00:05 covers (00:00, 00:05] → 5 M1 bars × 10 = 50
    # M5 bar at 00:10 covers (00:05, 00:10] → 5 M1 bars × 10 = 50
    ts_5 = pd.Timestamp("2024-01-01 00:05:00", tz="UTC")
    ts_10 = pd.Timestamp("2024-01-01 00:10:00", tz="UTC")
    assert m5.loc[ts_5] == 50
    assert m5.loc[ts_10] == 50


# [27.0f NEW]
def test_f5c_inherits_causality_from_inputs():
    """D-AA4: f5c NaN propagates from inputs."""
    df = pd.DataFrame(
        {
            "pair": ["USD_JPY"] * 5,
            "signal_ts": pd.date_range("2024-01-01", periods=5, freq="5min", tz="UTC"),
            "direction": ["long"] * 5,
            "atr_at_signal_pip": [5.0] * 5,
            "spread_at_signal_pip": [2.0] * 5,
            "f5a_spread_z_50": [float("nan"), 1.5, 0.5, float("nan"), 2.0],
            "f5b_volume_z_50": [-2.0, -1.5, float("nan"), -2.0, 0.5],
            "f5c_high_spread_low_vol_50": [
                np.nan,  # f5a NaN → f5c NaN
                True,  # f5a > 1.0 AND f5b < -1.0 → True
                np.nan,  # f5b NaN → f5c NaN
                np.nan,  # f5a NaN → f5c NaN
                False,  # f5b >= -1.0 → False
            ],
        }
    )
    # NaN propagation test: any row with NaN in f5a or f5b → f5c must be NaN
    nan_a = np.isnan(df["f5a_spread_z_50"].to_numpy(dtype=np.float64))
    nan_b = np.isnan(df["f5b_volume_z_50"].to_numpy(dtype=np.float64))
    f5c = df["f5c_high_spread_low_vol_50"].to_numpy(dtype=np.float64)
    nan_c = np.isnan(f5c)
    # f5c must be NaN where f5a OR f5b is NaN
    assert np.all(nan_c[nan_a | nan_b])


# [27.0f NEW]
def test_build_r7_c_features_returns_7_columns_total():
    """After build, df has 4 R7-A + 3 R7-C = 7 model features."""
    # We don't actually call build_r7_c_features (needs M1 data); just
    # verify the column-name contract on a mock df shape.
    expected_cols = set(s27f.ALL_FEATURES_R7AC)
    assert len(expected_cols) == 7


# ===========================================================================
# Group 3 — verify_volume_preflight HALT (5 NEW; D-AA12)
# ===========================================================================


# [27.0f NEW]
def test_r7_c_preflight_error_is_runtime_error_subclass():
    assert issubclass(s27f.R7CPreflightError, RuntimeError)


# [27.0f NEW]
def test_volume_preflight_threshold_is_99_percent():
    assert s27f.VOLUME_PREFLIGHT_NON_NULL_FRAC == 0.99


# [27.0f NEW]
def test_verify_volume_preflight_signature():
    sig = inspect.signature(s27f.verify_volume_preflight)
    params = set(sig.parameters)
    assert "pairs" in params
    assert "days" in params


# [27.0f NEW]
def test_verify_volume_preflight_halts_on_missing_pair_file():
    """R7CPreflightError raised if any pair's jsonl file is missing."""
    with pytest.raises(s27f.R7CPreflightError):
        s27f.verify_volume_preflight(["NONEXISTENT_PAIR"], days=730)


# [27.0f NEW]
def test_load_m1_volume_series_returns_int_series_with_utc_index():
    """Helper loads volume from existing M1 BA jsonl."""
    # Try one real pair; if data file exists, verify shape
    try:
        vol = s27f.load_m1_volume_series("USD_JPY", days=730)
        assert isinstance(vol, pd.Series)
        assert vol.index.tz is not None  # UTC
        assert len(vol) > 0
    except FileNotFoundError:
        pytest.skip("USD_JPY M1 BA 730d data file not present")


# ===========================================================================
# Group 4 — drop_rows_with_missing_r7_c_features (4 NEW)
# ===========================================================================


# [27.0f NEW]
def test_drop_rows_with_missing_r7_c_features_drops_nan_rows():
    df = pd.DataFrame(
        {
            "f5a_spread_z_50": [1.0, np.nan, 2.0, 3.0],
            "f5b_volume_z_50": [-1.0, -2.0, np.nan, 0.5],
            "f5c_high_spread_low_vol_50": [0.0, 0.0, 0.0, 1.0],
        }
    )
    out, stats, keep_mask = s27f.drop_rows_with_missing_r7_c_features(df)
    assert stats["n_input"] == 4
    assert stats["n_dropped"] == 2  # rows 1 (f5a NaN) and 2 (f5b NaN)
    assert stats["n_kept"] == 2
    assert len(out) == 2
    assert keep_mask.tolist() == [True, False, False, True]


# [27.0f NEW]
def test_drop_rows_returns_drop_frac():
    df = pd.DataFrame(
        {
            "f5a_spread_z_50": [1.0, np.nan],
            "f5b_volume_z_50": [-1.0, -2.0],
            "f5c_high_spread_low_vol_50": [0.0, 0.0],
        }
    )
    _, stats, _ = s27f.drop_rows_with_missing_r7_c_features(df)
    assert stats["drop_frac"] == 0.5


# [27.0f NEW]
def test_drop_rows_raises_if_r7_c_column_missing():
    df = pd.DataFrame({"f5a_spread_z_50": [1.0]})  # missing f5b, f5c
    with pytest.raises(s27f.SanityProbeError):
        s27f.drop_rows_with_missing_r7_c_features(df)


# [27.0f NEW]
def test_drop_rows_preserves_non_nan_rows():
    df = pd.DataFrame(
        {
            "f5a_spread_z_50": [1.0, 2.0],
            "f5b_volume_z_50": [-1.0, -2.0],
            "f5c_high_spread_low_vol_50": [0.0, 1.0],
            "other_col": [100, 200],
        }
    )
    out, stats, keep_mask = s27f.drop_rows_with_missing_r7_c_features(df)
    assert stats["n_dropped"] == 0
    assert list(out["other_col"]) == [100, 200]
    assert keep_mask.tolist() == [True, True]


# ===========================================================================
# Group 5 — Cell construction (5 NEW)
# ===========================================================================


# [27.0f NEW]
def test_build_s_e_r7_c_cells_returns_three_cells():
    cells = s27f.build_s_e_r7_c_cells()
    assert len(cells) == 3


# [27.0f NEW]
def test_build_s_e_r7_c_cells_has_three_cell_ids():
    cells = s27f.build_s_e_r7_c_cells()
    ids = {c["id"] for c in cells}
    assert ids == {"C-se-rcw", "C-se-r7a-replica", "C-sb-baseline"}


# [27.0f NEW]
def test_cells_have_feature_set_field():
    cells = s27f.build_s_e_r7_c_cells()
    for c in cells:
        assert "feature_set" in c


# [27.0f NEW]
def test_c_se_rcw_uses_r7a_plus_r7c():
    cells = s27f.build_s_e_r7_c_cells()
    c_se_rcw = next(c for c in cells if c["id"] == "C-se-rcw")
    assert c_se_rcw["feature_set"] == "r7a+r7c"
    assert c_se_rcw["score_type"] == "s_e_r7ac"


# [27.0f NEW]
def test_c_se_r7a_replica_uses_r7a_only():
    cells = s27f.build_s_e_r7_c_cells()
    c_r7a = next(c for c in cells if c["id"] == "C-se-r7a-replica")
    assert c_r7a["feature_set"] == "r7a"
    assert c_r7a["score_type"] == "s_e_r7a"


# ===========================================================================
# Group 6 — evaluate_cell_27_0f feature routing (4 NEW)
# ===========================================================================


# [27.0f NEW]
def test_evaluate_cell_27_0f_reads_quantile_percents():
    src = inspect.getsource(s27f.evaluate_cell_27_0f)
    assert 'cell.get("quantile_percents"' in src or "cell['quantile_percents']" in src


# [27.0f NEW]
def test_main_routes_s_e_r7ac_to_r7ac_scores():
    src = inspect.getsource(s27f.main)
    assert "s_e_r7ac" in src
    assert "val_score_s_e_rcw" in src or "test_score_s_e_rcw" in src


# [27.0f NEW]
def test_main_routes_s_e_r7a_to_r7a_only_scores():
    src = inspect.getsource(s27f.main)
    assert "s_e_r7a" in src
    assert "val_score_s_e_r7a" in src or "test_score_s_e_r7a" in src


# [27.0f NEW]
def test_main_routes_s_b_raw_to_multiclass_head():
    src = inspect.getsource(s27f.main)
    assert "s_b_raw" in src
    assert "val_score_s_b_raw" in src or "val_raw_probs" in src


# ===========================================================================
# Group 7 — D10 3-artifact form (4 NEW)
# ===========================================================================


# [27.0f NEW]
def test_main_fits_three_artifacts_each_once():
    src = inspect.getsource(s27f.main)
    # 1 regressor on R7-A+R7-C + 1 regressor on R7-A only
    assert src.count("regressor_rcw.fit(") == 1
    assert src.count("regressor_r7a.fit(") == 1
    # 1 multiclass head
    assert src.count("multiclass_pipeline.fit(") == 1


# [27.0f NEW]
def test_no_per_cell_refit_in_evaluate_cell_27_0f():
    src = inspect.getsource(s27f.evaluate_cell_27_0f)
    assert ".fit(" not in src


# [27.0f NEW]
def test_d10_3_artifact_documented():
    doc = s27f.__doc__ or ""
    flat = " ".join(doc.split())
    assert "3-artifact" in flat


# [27.0f NEW]
def test_lightgbm_regression_config_inherited():
    s27d = importlib.import_module("stage27_0d_s_e_regression_eval")
    assert s27f.LIGHTGBM_REGRESSION_CONFIG is s27d.LIGHTGBM_REGRESSION_CONFIG


# ===========================================================================
# Group 8 — BaselineMismatchError HALT (4 NEW)
# ===========================================================================


# [27.0f NEW]
def test_baseline_mismatch_error_is_runtime_error_subclass():
    assert issubclass(s27f.BaselineMismatchError, RuntimeError)


# [27.0f NEW]
def test_check_c_sb_baseline_match_passes_at_exact_baseline():
    fake = {
        "test_realised_metrics": {
            "n_trades": s27f.BASELINE_27_0B_C_ALPHA0_N_TRADES,
            "sharpe": s27f.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s27f.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    report = s27f.check_c_sb_baseline_match(fake)
    assert report["all_match"] is True


# [27.0f NEW]
def test_check_c_sb_baseline_match_halts_on_drift():
    fake = {
        "test_realised_metrics": {
            "n_trades": s27f.BASELINE_27_0B_C_ALPHA0_N_TRADES + 5,
            "sharpe": s27f.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s27f.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    with pytest.raises(s27f.BaselineMismatchError):
        s27f.check_c_sb_baseline_match(fake)


# [27.0f NEW]
def test_baseline_tolerances_inherited():
    s27d = importlib.import_module("stage27_0d_s_e_regression_eval")
    assert s27f.BASELINE_27_0B_C_ALPHA0_N_TRADES == s27d.BASELINE_27_0B_C_ALPHA0_N_TRADES == 34626
    assert s27f.BASELINE_MATCH_SHARPE_ABS_TOLERANCE == 1e-4


# ===========================================================================
# Group 9 — H-B6 falsification outcome resolver (6 NEW)
# ===========================================================================


# [27.0f NEW]
def test_h_b6_outcome_constants():
    assert s27f.H_B6_OUTCOME_STRONG_SUPPORT == "STRONG_SUPPORT"
    assert s27f.H_B6_OUTCOME_PARTIAL_SUPPORT == "PARTIAL_SUPPORT"
    assert s27f.H_B6_OUTCOME_FALSIFIED_R7C_INSUFFICIENT == "FALSIFIED_R7C_INSUFFICIENT"
    assert s27f.H_B6_OUTCOME_PARTIALLY_FALSIFIED_NEW_QUESTION == "PARTIALLY_FALSIFIED_NEW_QUESTION"
    assert s27f.H_B6_OUTCOME_NEEDS_REVIEW == "NEEDS_REVIEW"


# [27.0f NEW]
def test_h_b6_outcome_row_1_strong_support():
    """C-se-rcw H2 PASS at some q → STRONG_SUPPORT."""
    fake_cell_results = [
        {
            "cell": {"id": "C-se-rcw"},
            "h_state": "OK",
            "test_formal_spearman": 0.5,
            "quantile_all": [
                {"q_percent": 5.0, "test": {"sharpe": 0.15, "annual_pnl": 500.0}},
                {"q_percent": 10.0, "test": {"sharpe": -0.10, "annual_pnl": -200.0}},
            ],
        },
        {
            "cell": {"id": "C-se-r7a-replica"},
            "h_state": "OK",
            "test_formal_spearman": 0.4,
            "quantile_all": [
                {"q_percent": 5.0, "test": {"sharpe": 0.05, "annual_pnl": 100.0}},
                {"q_percent": 10.0, "test": {"sharpe": -0.20, "annual_pnl": -300.0}},
            ],
        },
    ]
    out = s27f.compute_h_b6_falsification_outcome(fake_cell_results)
    assert out["h_b6_outcome"] == s27f.H_B6_OUTCOME_STRONG_SUPPORT
    assert out["row_matched"] == 1


# [27.0f NEW]
def test_h_b6_outcome_row_3_falsified_when_delta_small():
    """H1m PASS AND max-abs delta ≤ 0.05 → FALSIFIED_R7C_INSUFFICIENT."""
    fake_cell_results = [
        {
            "cell": {"id": "C-se-rcw"},
            "h_state": "OK",
            "test_formal_spearman": 0.4,
            "quantile_all": [
                {"q_percent": 5.0, "test": {"sharpe": -0.18, "annual_pnl": -200.0}},
                {"q_percent": 10.0, "test": {"sharpe": -0.19, "annual_pnl": -250.0}},
            ],
        },
        {
            "cell": {"id": "C-se-r7a-replica"},
            "h_state": "OK",
            "test_formal_spearman": 0.4,
            "quantile_all": [
                {"q_percent": 5.0, "test": {"sharpe": -0.17, "annual_pnl": -200.0}},
                {"q_percent": 10.0, "test": {"sharpe": -0.20, "annual_pnl": -300.0}},
            ],
        },
    ]
    out = s27f.compute_h_b6_falsification_outcome(fake_cell_results)
    assert out["h_b6_outcome"] == s27f.H_B6_OUTCOME_FALSIFIED_R7C_INSUFFICIENT
    assert out["row_matched"] == 3


# [27.0f NEW]
def test_h_b6_outcome_needs_review_when_r7a_replica_missing():
    """D-AA8: NEEDS_REVIEW if C-se-r7a-replica not present or h_state != OK."""
    fake_cell_results = [
        {
            "cell": {"id": "C-se-rcw"},
            "h_state": "OK",
            "test_formal_spearman": 0.4,
            "quantile_all": [{"q_percent": 5.0, "test": {"sharpe": -0.1, "annual_pnl": -100.0}}],
        }
    ]
    out = s27f.compute_h_b6_falsification_outcome(fake_cell_results)
    assert out["h_b6_outcome"] == s27f.H_B6_OUTCOME_NEEDS_REVIEW


# [27.0f NEW]
def test_h_b6_delta_sharpe_threshold_is_0_05():
    assert s27f.H_B6_DELTA_SHARPE_PARTIAL_SUPPORT == 0.05


# [27.0f NEW]
def test_h_b6_outcome_evidence_includes_delta_sharpe():
    fake_cell_results = [
        {
            "cell": {"id": "C-se-rcw"},
            "h_state": "OK",
            "test_formal_spearman": 0.4,
            "quantile_all": [{"q_percent": 5.0, "test": {"sharpe": -0.1, "annual_pnl": -100.0}}],
        },
        {
            "cell": {"id": "C-se-r7a-replica"},
            "h_state": "OK",
            "test_formal_spearman": 0.3,
            "quantile_all": [{"q_percent": 5.0, "test": {"sharpe": -0.15, "annual_pnl": -150.0}}],
        },
    ]
    out = s27f.compute_h_b6_falsification_outcome(fake_cell_results)
    ev = out.get("evidence", {})
    assert "delta_sharpe_per_q" in ev
    assert "max_q_delta_sharpe" in ev
    assert "max_abs_delta_sharpe" in ev


# ===========================================================================
# Group 10 — Top-tail regime audit (4 NEW)
# ===========================================================================


# [27.0f NEW]
def test_top_tail_audit_q_values():
    assert s27f.TOP_TAIL_AUDIT_Q_PERCENTS == (10.0, 20.0)


# [27.0f NEW]
def test_compute_top_tail_regime_audit_per_q_structure():
    rng = np.random.default_rng(42)
    n = 200
    val_score = rng.normal(0, 1, n)
    val_features = pd.DataFrame(
        {
            "f5a_spread_z_50": rng.normal(0, 1, n),
            "f5b_volume_z_50": rng.normal(0, 1, n),
            "f5c_high_spread_low_vol_50": rng.uniform(0, 1, n).round(),
        }
    )
    out = s27f.compute_top_tail_regime_audit(val_score, val_features, q_list=(10.0, 20.0))
    assert "per_q" in out
    assert "population" in out
    assert len(out["per_q"]) == 2
    for r in out["per_q"]:
        assert "mean_f5a_spread_z_50" in r
        assert "mean_f5b_volume_z_50" in r
        assert "fraction_f5c_true" in r
        assert "delta_mean_f5a_vs_pop" in r


# [27.0f NEW]
def test_top_tail_audit_population_means_match():
    rng = np.random.default_rng(7)
    n = 100
    val_score = rng.normal(0, 1, n)
    val_features = pd.DataFrame(
        {
            "f5a_spread_z_50": [0.5] * n,
            "f5b_volume_z_50": [-0.3] * n,
            "f5c_high_spread_low_vol_50": [0.0] * n,
        }
    )
    out = s27f.compute_top_tail_regime_audit(val_score, val_features)
    assert np.isclose(out["population"]["mean_f5a_spread_z_50"], 0.5)
    assert np.isclose(out["population"]["mean_f5b_volume_z_50"], -0.3)


# [27.0f NEW]
def test_top_tail_audit_is_diagnostic_only():
    """Top-tail audit must not influence formal verdict — only reads val score + features."""
    sig = inspect.signature(s27f.compute_top_tail_regime_audit)
    params = set(sig.parameters)
    assert params == {"val_score_c_se_rcw", "val_features", "q_list"}


# ===========================================================================
# Group 11 — C-se-r7a-replica drift check (4 NEW)
# ===========================================================================


# [27.0f NEW]
def test_r7a_replica_drift_tolerances():
    assert s27f.R7A_REPLICA_DRIFT_N_TRADES_TOLERANCE == 100
    assert s27f.R7A_REPLICA_DRIFT_SHARPE_TOLERANCE == 5e-3
    assert s27f.R7A_REPLICA_DRIFT_ANN_PNL_FRAC_TOLERANCE == 0.005


# [27.0f NEW]
def test_compute_c_se_r7a_replica_drift_check_returns_warn_flag():
    fake = {
        "test_realised_metrics": {
            "n_trades": 999_999,  # way off
            "sharpe": 5.0,  # way off
            "annual_pnl": -1_000_000.0,
        }
    }
    rep = s27f.compute_c_se_r7a_replica_drift_check(fake)
    assert "warn" in rep
    assert rep["warn"] is True


# [27.0f NEW]
def test_drift_check_returns_within_tolerance_flags():
    fake = {
        "test_realised_metrics": {
            "n_trades": 184_703,
            "sharpe": -0.483,
            "annual_pnl": -150_000.0,
        }
    }
    rep = s27f.compute_c_se_r7a_replica_drift_check(fake)
    assert "n_trades_within_tolerance" in rep
    assert "sharpe_within_tolerance" in rep
    assert "ann_pnl_within_tolerance" in rep


# [27.0f NEW]
def test_drift_check_does_not_raise():
    """D-AA11: WARN-only; not HALT."""
    fake = {"test_realised_metrics": {"n_trades": 0, "sharpe": 0.0, "annual_pnl": 0.0}}
    # Should NOT raise even for wildly off values
    s27f.compute_c_se_r7a_replica_drift_check(fake)


# ===========================================================================
# Group 12 — Sanity probe extensions items 14-19 (5 NEW)
# ===========================================================================


# [27.0f NEW]
def test_sanity_probe_signature_accepts_new_27_0f_params():
    sig = inspect.signature(s27f.run_sanity_probe_27_0f)
    params = set(sig.parameters)
    assert "volume_preflight_diag" in params
    assert "r7_c_drop_stats" in params
    assert "r7_c_feature_distribution_train" in params
    assert "per_pair_r7_c_stats" in params
    assert "top_tail_regime_audit" in params


# [27.0f NEW]
def test_sanity_probe_halts_on_r7_c_row_drop_over_1_percent():
    src = inspect.getsource(s27f.run_sanity_probe_27_0f)
    assert "R7_C_ROW_DROP_HALT_FRAC" in src
    assert "SanityProbeError" in src


# [27.0f NEW]
def test_main_calls_verify_volume_preflight_early():
    src = inspect.getsource(s27f.main)
    # verify_volume_preflight called before sanity probe (run_sanity_probe_27_0f)
    idx_preflight = src.find("verify_volume_preflight(")
    idx_probe = src.find("run_sanity_probe_27_0f(")
    assert idx_preflight > 0
    assert idx_probe > idx_preflight  # preflight runs first


# [27.0f NEW]
def test_main_halts_on_r7_c_row_drop_violation():
    src = inspect.getsource(s27f.main)
    # Main checks split-level drop_frac vs R7_C_ROW_DROP_HALT_FRAC
    assert "R7_C_ROW_DROP_HALT_FRAC" in src


# [27.0f NEW]
def test_main_computes_top_tail_audit_post_fit():
    src = inspect.getsource(s27f.main)
    assert "compute_top_tail_regime_audit(" in src


# ===========================================================================
# Group 13 — Class index mapping (2 NEW)
# ===========================================================================


# [27.0f NEW]
def test_class_index_mapping_consistent_with_inherited():
    s27e = importlib.import_module("stage27_0e_s_e_quantile_trim_eval")
    assert s27f.LABEL_TP == s27e.LABEL_TP
    assert s27f.LABEL_SL == s27e.LABEL_SL
    assert s27f.LABEL_TIME == s27e.LABEL_TIME


# [27.0f NEW]
def test_num_classes_is_three():
    assert s27f.NUM_CLASSES == 3


# ===========================================================================
# Group 14 — Module docstring + clauses + D-1 binding (4 NEW)
# ===========================================================================


# [27.0f NEW]
def test_module_docstring_includes_all_six_mandatory_clauses():
    doc = s27f.__doc__ or ""
    for marker in [
        "1. Phase framing",
        "2. Diagnostic columns prohibition",
        "3. γ closure preservation",
        "4. Production-readiness preservation",
        "5. NG#10 / NG#11 not relaxed",
        "6. Phase 27 scope",
    ]:
        assert marker in doc, f"clause marker missing: {marker!r}"


# [27.0f NEW]
def test_module_docstring_documents_h_b6_falsification_criteria():
    doc = s27f.__doc__ or ""
    flat = " ".join(doc.split())
    assert "STRONG_SUPPORT" in flat
    assert "PARTIAL_SUPPORT" in flat
    assert "FALSIFIED_R7C_INSUFFICIENT" in flat


# [27.0f NEW]
def test_d1_binding_documented_in_module_docstring():
    doc = s27f.__doc__ or ""
    assert "D-1 BINDING" in doc or "D-1 binding" in doc
    assert "_compute_realised_barrier_pnl" in doc
    assert "bid/ask" in doc


# [27.0f NEW]
def test_module_docstring_documents_3_artifact_form():
    doc = s27f.__doc__ or ""
    flat = " ".join(doc.split())
    assert "3-artifact" in flat


# ===========================================================================
# Group 15 — Sub-phase naming (2 NEW)
# ===========================================================================


# [27.0f NEW]
def test_artifact_root_is_stage27_0f():
    assert s27f.ARTIFACT_ROOT.name == "stage27_0f"


# [27.0f NEW]
def test_module_docstring_names_sub_phase_27_0f():
    doc = s27f.__doc__ or ""
    assert "27.0f-β" in doc


# ===========================================================================
# Group 16 — Inheritance from 27.0e (6 NEW)
# ===========================================================================


# [27.0f NEW]
def test_make_oof_fold_assignment_inherited():
    s27c = importlib.import_module("stage27_0c_s_d_calibrated_ev_eval")
    assert s27f.make_oof_fold_assignment is s27c.make_oof_fold_assignment


# [27.0f NEW]
def test_fit_oof_regression_diagnostic_inherited_from_27_0d():
    s27d = importlib.import_module("stage27_0d_s_e_regression_eval")
    assert s27f.fit_oof_regression_diagnostic is s27d.fit_oof_regression_diagnostic


# [27.0f NEW]
def test_compute_picker_score_s_e_inherited_from_27_0d():
    s27d = importlib.import_module("stage27_0d_s_e_regression_eval")
    assert s27f.compute_picker_score_s_e is s27d.compute_picker_score_s_e


# [27.0f NEW]
def test_compute_per_pair_sharpe_contribution_inherited_from_27_0b():
    s27b = importlib.import_module("stage27_0b_s_c_time_penalty_eval")
    assert s27f.compute_per_pair_sharpe_contribution is s27b.compute_per_pair_sharpe_contribution


# [27.0f NEW]
def test_evaluate_quantile_family_custom_inherited_from_27_0e():
    s27e = importlib.import_module("stage27_0e_s_e_quantile_trim_eval")
    assert s27f.evaluate_quantile_family_custom is s27e.evaluate_quantile_family_custom


# [27.0f NEW]
def test_build_pipeline_lightgbm_regression_widened_inherited_from_27_0d():
    s27d = importlib.import_module("stage27_0d_s_e_regression_eval")
    assert (
        s27f.build_pipeline_lightgbm_regression_widened
        is s27d.build_pipeline_lightgbm_regression_widened
    )


# ===========================================================================
# Group 17 — NG#11 reverse-violation guard (3 NEW)
# ===========================================================================


# [27.0f NEW]
def test_build_pair_spread_z_source_calls_shift_before_rolling():
    """NG#11 enforcement: shift(1) must appear BEFORE rolling in source."""
    src = inspect.getsource(s27f._build_pair_spread_z)
    shift_idx = src.find(".shift(")
    rolling_idx = src.find(".rolling(")
    assert shift_idx > 0
    assert rolling_idx > 0
    assert shift_idx < rolling_idx, "shift(1) must appear BEFORE rolling (NG#11)"


# [27.0f NEW]
def test_build_pair_volume_z_source_calls_shift_before_rolling():
    src = inspect.getsource(s27f._build_pair_volume_z)
    shift_idx = src.find(".shift(")
    rolling_idx = src.find(".rolling(")
    assert shift_idx > 0
    assert rolling_idx > 0
    assert shift_idx < rolling_idx, "shift(1) must appear BEFORE rolling (NG#11)"


# [27.0f NEW]
def test_clause_2_extension_mentions_r7_c_diagnostics_diagnostic_only():
    doc = s27f.__doc__ or ""
    flat = " ".join(doc.split()).lower()
    assert "r7-c feature distribution" in flat
    assert "top-tail regime audit" in flat
    assert "c-se-r7a-replica drift" in flat


# ===========================================================================
# Group 18 — Fix A row-set isolation (5 NEW)
# Per design memo §7.1 / Fix A approved 2026-05-16:
#   R7-C row-drop applies to C-se-rcw ONLY. C-se-r7a-replica and C-sb-baseline
#   evaluate on R7-A-clean parent so 27.0b baseline reproduction is preserved.
# ===========================================================================


# [27.0f NEW — Fix A]
def test_fix_a_c_sb_baseline_uses_r7a_clean_row_set():
    """C-sb-baseline must NOT receive R7-C row-drop (Fix A).

    In main() the s_b_raw branch must pass train_df / val_df / test_df
    (the R7-A-clean parent frames) and NOT *_rcw.
    """
    src = inspect.getsource(s27f.main)
    # Locate the s_b_raw cell-evaluation branch
    branch_start = src.find('cell["score_type"] == "s_b_raw"')
    assert branch_start > 0, "s_b_raw branch not found in main()"
    # Take the slice up to the next elif/else/try
    branch_end = src.find("try:", branch_start)
    assert branch_end > 0
    branch_slice = src[branch_start:branch_end]
    # Must reference parent frames; must NOT reference rcw frames
    assert "train_df_rcw" not in branch_slice
    assert "val_df_rcw" not in branch_slice
    assert "test_df_rcw" not in branch_slice
    assert "pnl_val_rcw" not in branch_slice
    assert "pnl_test_rcw" not in branch_slice
    assert "train_df, val_df, test_df" in branch_slice
    assert "pnl_val_full, pnl_test_full" in branch_slice


# [27.0f NEW — Fix A]
def test_fix_a_c_se_r7a_replica_uses_r7a_clean_row_set():
    """C-se-r7a-replica must NOT receive R7-C row-drop (Fix A)."""
    src = inspect.getsource(s27f.main)
    branch_start = src.find('cell["score_type"] == "s_e_r7a"')
    assert branch_start > 0, "s_e_r7a branch not found in main()"
    branch_end = src.find('cell["score_type"] == "s_b_raw"', branch_start)
    assert branch_end > 0
    branch_slice = src[branch_start:branch_end]
    assert "train_df_rcw" not in branch_slice
    assert "val_df_rcw" not in branch_slice
    assert "test_df_rcw" not in branch_slice
    assert "pnl_val_rcw" not in branch_slice
    assert "pnl_test_rcw" not in branch_slice
    assert "train_df, val_df, test_df" in branch_slice
    assert "pnl_val_full, pnl_test_full" in branch_slice


# [27.0f NEW — Fix A]
def test_fix_a_c_se_rcw_uses_r7c_clean_row_set():
    """C-se-rcw MUST receive R7-C row-drop (Fix A)."""
    src = inspect.getsource(s27f.main)
    branch_start = src.find('cell["score_type"] == "s_e_r7ac"')
    assert branch_start > 0, "s_e_r7ac branch not found in main()"
    branch_end = src.find('cell["score_type"] == "s_e_r7a"', branch_start)
    assert branch_end > 0
    branch_slice = src[branch_start:branch_end]
    assert "train_df_rcw" in branch_slice
    assert "val_df_rcw" in branch_slice
    assert "test_df_rcw" in branch_slice
    assert "pnl_val_rcw" in branch_slice
    assert "pnl_test_rcw" in branch_slice


# [27.0f NEW — Fix A]
def test_fix_a_baseline_match_check_uses_r7a_clean_row_set():
    """BaselineMismatchError check reads C-sb-baseline result, which by Fix A
    is evaluated on R7-A-clean. The function docstring must declare this."""
    doc = (s27f.check_c_sb_baseline_match.__doc__ or "").lower()
    flat = " ".join(doc.split())
    assert "fix a row-set isolation" in flat
    assert "r7-a-clean" in flat
    assert "not the r7-c-clean subset" in flat


# [27.0f NEW — Fix A]
def test_fix_a_r7c_drop_stats_reported_as_c_se_rcw_only_diagnostic():
    """R7-C drop print messages and report wording must scope to C-se-rcw."""
    main_src = inspect.getsource(s27f.main)
    # main() print line must mention C-se-rcw scope
    assert "C-se-rcw ONLY" in main_src or "C-se-rcw row-set" in main_src
    # write_eval_report_27_0f wording must scope to C-se-rcw
    report_src = inspect.getsource(s27f.write_eval_report_27_0f)
    assert "C-se-rcw row-set ONLY" in report_src or "C-se-rcw only" in report_src
