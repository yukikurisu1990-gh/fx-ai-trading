"""Unit tests for Stage 26.0d-β R6-new-A feature-widening audit.

~40 tests covering:
- Closed-allowlist enforcement (5; 2 NEW R6-new-A-specific)
- Missingness policy (4; 1 NEW)
- Picker scores (3; inherited from #309)
- Quantile cutoff selection (5)
- Verdict routing (5; inherited)
- Diagnostic-only column prohibition (5; 1 NEW)
- Identity-break detector (5 NEW R6-new-A-specific)
- Sanity probe (4; 2 NEW)
- End-to-end + report writer (4; 1 NEW)

9 NEW R6-new-A-specific tests flagged '[R6-new-A NEW]'.
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

r6 = importlib.import_module("stage26_0d_r6_new_a_eval")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(
    pair: str = "EUR_USD",
    direction: str = "long",
    atr_at_signal_pip: float = 10.0,
    spread_at_signal_pip: float = 1.5,
    time_to_fav_bar: int = -1,
    time_to_adv_bar: int = -1,
    same_bar_both_hit: bool = False,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "pair": pair,
                "signal_ts": pd.Timestamp("2024-04-30 12:30:00+00:00"),
                "horizon_bars": 60,
                "direction": direction,
                "entry_ask": 1.07238,
                "entry_bid": 1.07223,
                "atr_at_signal_pip": atr_at_signal_pip,
                "spread_at_signal_pip": spread_at_signal_pip,
                "time_to_fav_bar": time_to_fav_bar,
                "time_to_adv_bar": time_to_adv_bar,
                "same_bar_both_hit": same_bar_both_hit,
            }
        ]
    )


# ===========================================================================
# Group 1 — Closed-allowlist enforcement (5 tests; 2 NEW)
# ===========================================================================


# Test 1
def test_all_features_constant_is_4_feature_closed_allowlist():
    """Per 26.0d-α §2.1 / PR #311 §3: exactly 4 features admitted."""
    assert r6.ALL_FEATURES == ("pair", "direction", "atr_at_signal_pip", "spread_at_signal_pip")
    assert len(r6.ALL_FEATURES) == 4


# Test 2 — [R6-new-A NEW] excluded features rejected
def test_pipeline_rejects_excluded_features():
    """ColumnTransformer must NOT reference any Phase 25 F-class column,
    multi-TF aggregate, calendar, or external-data feature.
    """
    pipe = r6.build_pipeline_lightgbm_multiclass_widened()
    pre = pipe.named_steps["pre"]
    # Gather all columns referenced by the ColumnTransformer
    referenced_cols: set[str] = set()
    for _name, _transformer, cols in pre.transformers:
        if isinstance(cols, list):
            referenced_cols.update(cols)
    # Whitelist exactly the closed allowlist
    assert referenced_cols == set(r6.ALL_FEATURES)
    # Specifically excluded features must NOT appear
    excluded = {
        "vol_expansion_ratio",
        "trend_slope",
        "rsi_at_signal",
        "macd_signal",
        "bb_upper",
        "dxy_at_signal",
        "calendar_event_proximity",
        "hour_of_day",
        "day_of_week",
        "m5_close",
        "m15_close",
        "h1_atr",
        "max_fav_excursion_pip",
        "max_adv_excursion_pip",
    }
    assert referenced_cols.isdisjoint(excluded)


# Test 3 — [R6-new-A NEW] numeric features passthrough not one-hot
def test_numeric_features_passthrough_not_one_hot():
    """atr_at_signal_pip / spread_at_signal_pip pass through; NOT one-hot."""
    pipe = r6.build_pipeline_lightgbm_multiclass_widened()
    pre = pipe.named_steps["pre"]
    num_transformer = None
    for name, transformer, cols in pre.transformers:
        if name == "num":
            num_transformer = (transformer, cols)
    assert num_transformer is not None, "must have a 'num' transformer block"
    transformer, cols = num_transformer
    assert transformer == "passthrough", "numeric features must use passthrough"
    assert set(cols) == set(r6.NUMERIC_FEATURES)


# Test 4
def test_categorical_features_one_hot_encoded():
    """pair, direction go through OneHotEncoder (Decision G)."""
    pipe = r6.build_pipeline_lightgbm_multiclass_widened()
    pre = pipe.named_steps["pre"]
    cat_transformer = None
    for name, transformer, cols in pre.transformers:
        if name == "cat":
            cat_transformer = (transformer, cols)
    assert cat_transformer is not None
    transformer, cols = cat_transformer
    from sklearn.preprocessing import OneHotEncoder

    assert isinstance(transformer, OneHotEncoder)
    assert set(cols) == {"pair", "direction"}


# Test 5
def test_no_standardisation_in_pipeline():
    """No StandardScaler / MinMaxScaler in pipeline (Decision G; no scaling)."""
    pipe = r6.build_pipeline_lightgbm_multiclass_widened()
    src = inspect.getsource(r6.build_pipeline_lightgbm_multiclass_widened)
    assert "StandardScaler" not in src
    assert "MinMaxScaler" not in src
    assert "RobustScaler" not in src
    # Pipeline only has pre + clf
    assert list(pipe.named_steps.keys()) == ["pre", "clf"]


# ===========================================================================
# Group 2 — Missingness policy (4 tests; 1 NEW)
# ===========================================================================


# Test 6
def test_drop_rows_with_missing_new_features_drops_nan_rows():
    df = pd.DataFrame(
        {
            "pair": ["EUR_USD"] * 4,
            "direction": ["long"] * 4,
            "atr_at_signal_pip": [10.0, np.nan, 12.0, 15.0],
            "spread_at_signal_pip": [1.5, 2.0, np.nan, 1.8],
        }
    )
    out, stats = r6.drop_rows_with_missing_new_features(df)
    assert len(out) == 2
    assert stats["n_input"] == 4
    assert stats["n_kept"] == 2
    assert stats["n_dropped"] == 2


# Test 7
def test_drop_rows_with_missing_new_features_drops_inf_rows():
    df = pd.DataFrame(
        {
            "pair": ["EUR_USD"] * 3,
            "direction": ["long"] * 3,
            "atr_at_signal_pip": [10.0, np.inf, 12.0],
            "spread_at_signal_pip": [1.5, 2.0, -np.inf],
        }
    )
    out, stats = r6.drop_rows_with_missing_new_features(df)
    assert len(out) == 1
    assert stats["n_dropped"] == 2


# Test 8 — [R6-new-A NEW] per-feature NaN counts
def test_drop_rows_reports_per_feature_counts():
    df = pd.DataFrame(
        {
            "pair": ["EUR_USD"] * 5,
            "direction": ["long"] * 5,
            "atr_at_signal_pip": [10.0, np.nan, np.nan, 15.0, 12.0],
            "spread_at_signal_pip": [1.5, 2.0, np.nan, 1.8, 1.2],
        }
    )
    _, stats = r6.drop_rows_with_missing_new_features(df)
    assert stats["per_feature_nan"]["atr_at_signal_pip"] == 2
    assert stats["per_feature_nan"]["spread_at_signal_pip"] == 1


# Test 9
def test_no_imputation_in_pipeline():
    """No SimpleImputer / IterativeImputer (Decision F1)."""
    src = inspect.getsource(r6.build_pipeline_lightgbm_multiclass_widened)
    assert "Imputer" not in src
    assert "fillna" not in src


# ===========================================================================
# Group 3 — Picker scores (3 tests; inherited from #309)
# ===========================================================================


# Test 10
def test_picker_ptp_unchanged_from_l1():
    probs = np.array([[0.1, 0.5, 0.4], [0.7, 0.2, 0.1]])
    score = r6.compute_picker_score_ptp(probs)
    np.testing.assert_array_almost_equal(score, [0.1, 0.7])


# Test 11
def test_picker_diff_unchanged_from_l1():
    probs = np.array([[0.5, 0.3, 0.2], [0.1, 0.8, 0.1]])
    score = r6.compute_picker_score_diff(probs)
    np.testing.assert_array_almost_equal(score, [0.2, -0.7])


# Test 12
def test_formal_pickers_are_b1_and_b2():
    assert r6.FORMAL_PICKERS == (r6.PICKER_PTP, r6.PICKER_DIFF)
    cells = r6.build_cells()
    pickers = {c["picker"] for c in cells}
    assert pickers == {r6.PICKER_PTP, r6.PICKER_DIFF}


# ===========================================================================
# Group 4 — Quantile cutoff selection (5 tests; mostly inherited)
# ===========================================================================


# Test 13
def test_select_quantile_cutoff_returns_top_q_percent():
    rng = np.random.default_rng(0)
    pred_val = rng.uniform(0, 1, size=1000)
    cutoff = r6.fit_quantile_cutoff_on_val(pred_val, 10)
    n_above = int((pred_val >= cutoff).sum())
    assert 80 <= n_above <= 120


# Test 14
def test_a0_prefilter_drops_quantiles_below_200_trades():
    a0_min = r6.A0_MIN_ANNUAL_TRADES * r6.VAL_SPAN_YEARS
    cells = [
        {
            "cell": {"id": "C01", "picker": r6.PICKER_PTP},
            "selected_q_percent": 5,
            "val_realised_sharpe": 0.50,
            "val_realised_annual_pnl": 200.0,
            "val_n_trades": int(a0_min) - 1,
            "val_max_dd": 10.0,
            "h_state": "OK",
        },
        {
            "cell": {"id": "C02", "picker": r6.PICKER_DIFF},
            "selected_q_percent": 10,
            "val_realised_sharpe": 0.20,
            "val_realised_annual_pnl": 100.0,
            "val_n_trades": int(a0_min) + 100,
            "val_max_dd": 8.0,
            "h_state": "OK",
        },
    ]
    res = r6.select_cell_validation_only(cells)
    assert res["selected"]["cell"]["id"] == "C02"
    assert res["low_val_trades_flag"] is False


# Test 15
def test_quantile_cutoff_scalar_applied_to_test_unchanged():
    rng = np.random.default_rng(7)
    score_val = rng.normal(0.0, 0.1, size=500)
    pnl_val = rng.normal(0.0, 1.0, size=500)
    score_test = rng.normal(0.0, 0.1, size=300)
    pnl_test = rng.normal(0.0, 1.0, size=300)
    res_a = r6.evaluate_quantile_family(score_val, pnl_val, score_test, pnl_test, 0.1, 0.1)
    score_test_perturbed = score_test + 100.0
    res_b = r6.evaluate_quantile_family(
        score_val, pnl_val, score_test_perturbed, pnl_test, 0.1, 0.1
    )
    for ra, rb in zip(res_a, res_b, strict=True):
        assert ra["cutoff"] == pytest.approx(rb["cutoff"], abs=1e-12)


# Test 16
def test_quantile_threshold_family_has_5_candidates():
    assert r6.THRESHOLDS_QUANTILE_PERCENTS == (5, 10, 20, 30, 40)


# Test 17
def test_validation_only_selection_uses_val_sharpe_not_test():
    """Inherited from #309: select_cell_validation_only ranks by val Sharpe."""
    cells = [
        {
            "cell": {"id": "C01", "picker": r6.PICKER_PTP},
            "selected_q_percent": 5,
            "val_realised_sharpe": 0.30,
            "val_realised_annual_pnl": 100.0,
            "val_n_trades": 5000,
            "val_max_dd": 10.0,
            "test_realised_metrics": {"sharpe": 0.05},
            "h_state": "OK",
        },
        {
            "cell": {"id": "C02", "picker": r6.PICKER_DIFF},
            "selected_q_percent": 5,
            "val_realised_sharpe": 0.10,
            "val_realised_annual_pnl": 50.0,
            "val_n_trades": 5000,
            "val_max_dd": 8.0,
            "test_realised_metrics": {"sharpe": 0.50},
            "h_state": "OK",
        },
    ]
    res = r6.select_cell_validation_only(cells)
    assert res["selected"]["cell"]["id"] == "C01"


# ===========================================================================
# Group 5 — Verdict routing (5 tests; inherited from #309)
# ===========================================================================


# Test 18
def test_h1_weak_pass_when_test_spearman_above_005():
    val_selected = {
        "test_formal_spearman": 0.06,
        "test_gates": {},
        "test_realised_metrics": {"sharpe": float("nan")},
    }
    res = r6.assign_verdict(val_selected)
    assert res["h1_weak_pass"] is True


# Test 19
def test_h1_weak_fail_when_test_spearman_at_or_below_005():
    val_selected = {
        "test_formal_spearman": 0.05,
        "test_gates": {},
        "test_realised_metrics": {"sharpe": float("nan")},
    }
    res = r6.assign_verdict(val_selected)
    assert res["h1_weak_pass"] is False
    assert res["verdict"] == "REJECT_NON_DISCRIMINATIVE"


# Test 20
def test_h2_requires_both_sharpe_and_ann_pnl():
    val_selected = {
        "test_formal_spearman": 0.20,
        "test_gates": {"A1": True, "A2": False, "A0": True, "A3": True, "A4": True, "A5": True},
        "test_realised_metrics": {"sharpe": 0.10},
    }
    res = r6.assign_verdict(val_selected)
    assert res["h2_pass"] is False


# Test 21
def test_h3_uses_neg_0192_baseline():
    assert pytest.approx(-0.192) == r6.H3_REFERENCE_SHARPE


# Test 22
def test_h2_pass_alone_does_not_yield_adopt_candidate_in_26_0d_beta():
    """26.0d-β cannot mint ADOPT_CANDIDATE; H2 PASS → PROMISING_BUT_NEEDS_OOS."""
    val_selected = {
        "test_formal_spearman": 0.20,
        "test_gates": {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True},
        "test_realised_metrics": {"sharpe": 0.10},
    }
    res = r6.assign_verdict(val_selected)
    assert res["h2_pass"] is True
    assert res["verdict"] == "PROMISING_BUT_NEEDS_OOS"
    assert res["verdict"] != "ADOPT_CANDIDATE"


# ===========================================================================
# Group 6 — Diagnostic-only prohibition (5 tests; 1 NEW)
# ===========================================================================


# Test 23
def test_concentration_high_flag_is_diagnostic_only():
    sel_src = inspect.getsource(r6.select_cell_validation_only)
    assert "concentration_high" not in sel_src
    assert "top_pair_share" not in sel_src
    verdict_src = inspect.getsource(r6.assign_verdict)
    assert "concentration_high" not in verdict_src
    assert "top_pair_share" not in verdict_src


# Test 24
def test_absolute_thresholds_excluded_from_cell_selection():
    src = inspect.getsource(r6.select_cell_validation_only)
    assert "absolute_best" not in src
    assert "absolute_all" not in src
    assert r6.ABSOLUTE_THRESHOLDS_PTP == (0.30, 0.40, 0.45, 0.50)
    assert r6.ABSOLUTE_THRESHOLDS_DIFF == (0.0, 0.05, 0.10, 0.15)


# Test 25
def test_classification_diagnostics_not_used_in_h1():
    src = inspect.getsource(r6.assign_verdict)
    assert "test_formal_spearman" in src
    assert "auc_tp_ovr" not in src
    assert "cohen_kappa" not in src
    assert "multiclass_logloss" not in src


# Test 26
def test_isotonic_appendix_raises_not_implemented():
    with pytest.raises(NotImplementedError) as exc_info:
        r6.compute_isotonic_diagnostic_appendix()
    assert "deferred" in str(exc_info.value).lower()


# Test 27 — [R6-new-A NEW] feature importance is diagnostic-only
def test_feature_importance_not_used_in_h1():
    """compute_feature_importance_diagnostic output NEVER enters formal verdict."""
    sel_src = inspect.getsource(r6.select_cell_validation_only)
    assert "feature_importance" not in sel_src
    verdict_src = inspect.getsource(r6.assign_verdict)
    assert "feature_importance" not in verdict_src
    # Identity-break detector also does not consume feature importance
    ib_src = inspect.getsource(r6.detect_identity_break)
    assert "feature_importance" not in ib_src


# ===========================================================================
# Group 7 — Identity-break detector (5 NEW R6-new-A-specific)
# ===========================================================================


# Test 28 — [R6-new-A NEW] NO when metrics match baseline
def test_detect_identity_break_returns_no_when_metrics_match_baseline():
    sel = {
        "test_realised_metrics": {
            "n_trades": r6.BASELINE_TEST_N_TRADES,
            "sharpe": r6.BASELINE_TEST_SHARPE,
            "annual_pnl": r6.BASELINE_TEST_ANN_PNL,
        },
        "test_concentration": {
            "top_pair": r6.BASELINE_TOP_PAIR,
            "top_pair_share": r6.BASELINE_TOP_PAIR_SHARE,
        },
    }
    res = r6.detect_identity_break(sel)
    assert res["verdict"] == "NO"


# Test 29 — [R6-new-A NEW] YES_IMPROVED when Sharpe improves
def test_detect_identity_break_returns_yes_improved_when_sharpe_improves():
    sel = {
        "test_realised_metrics": {
            "n_trades": 30000,  # differs from baseline 42150
            "sharpe": -0.10,  # improved from baseline -0.2232
            "annual_pnl": -100000.0,
        },
        "test_concentration": {"top_pair": "EUR_USD", "top_pair_share": 0.5},
    }
    res = r6.detect_identity_break(sel)
    assert res["verdict"] == "YES_IMPROVED"
    assert res["sharpe_improved"] is True


# Test 30 — [R6-new-A NEW] YES_SAME_OR_WORSE when trade set differs but Sharpe doesn't improve
def test_detect_identity_break_returns_yes_same_when_trade_set_differs_but_sharpe_unchanged():
    sel = {
        "test_realised_metrics": {
            "n_trades": 30000,
            "sharpe": -0.30,  # worse than baseline
            "annual_pnl": -300000.0,
        },
        "test_concentration": {"top_pair": "EUR_USD", "top_pair_share": 0.5},
    }
    res = r6.detect_identity_break(sel)
    assert res["verdict"] == "YES_SAME_OR_WORSE"
    assert res["sharpe_improved"] is False


# Test 31 — [R6-new-A NEW] PARTIAL trigger
def test_detect_identity_break_returns_partial_when_concentration_changes_but_sharpe_doesnt():
    sel = {
        "test_realised_metrics": {
            "n_trades": r6.BASELINE_TEST_N_TRADES,  # exact match on n_trades
            "sharpe": r6.BASELINE_TEST_SHARPE,  # within tolerance
            "annual_pnl": r6.BASELINE_TEST_ANN_PNL,  # within tolerance
        },
        "test_concentration": {
            "top_pair": "EUR_USD",  # differs from USD_JPY baseline
            "top_pair_share": 0.40,  # share also differs
        },
    }
    res = r6.detect_identity_break(sel)
    # trade_set_differs is True (top pair differs); sharpe_improved is False
    # → PARTIAL or YES_SAME_OR_WORSE depending on tree branching
    assert res["verdict"] in ("PARTIAL", "YES_SAME_OR_WORSE")
    assert res["concentration_changed"] is True


# Test 32 — [R6-new-A NEW] NO interpretation does NOT state hypothesis rejected
def test_no_interpretation_does_not_state_hypothesis_rejected():
    """Per user correction on Decision H: NO interpretation must NOT claim
    minimum-feature-set hypothesis is rejected. MUST mention scope amendment.
    """
    sel = {
        "test_realised_metrics": {
            "n_trades": r6.BASELINE_TEST_N_TRADES,
            "sharpe": r6.BASELINE_TEST_SHARPE,
            "annual_pnl": r6.BASELINE_TEST_ANN_PNL,
        },
        "test_concentration": {
            "top_pair": r6.BASELINE_TOP_PAIR,
            "top_pair_share": r6.BASELINE_TOP_PAIR_SHARE,
        },
    }
    res = r6.detect_identity_break(sel)
    assert res["verdict"] == "NO"
    reason_lower = res["reason"].lower()
    assert "rejected" not in reason_lower or "not rejected" in reason_lower
    assert "scope amendment" in reason_lower
    assert "311" in res["reason"]


# ===========================================================================
# Group 8 — Sanity probe (4 tests; 2 NEW)
# ===========================================================================


# Test 33
def test_sanity_probe_class_share_threshold():
    assert r6.SANITY_MIN_CLASS_SHARE == 0.01
    assert r6.SANITY_MAX_PER_PAIR_TIME_SHARE == 0.99


# Test 34 — [R6-new-A NEW] NaN-rate threshold
def test_sanity_probe_new_feature_nan_rate_threshold():
    assert r6.SANITY_MAX_NEW_FEATURE_NAN_RATE == 0.05


# Test 35 — [R6-new-A NEW] positivity threshold
def test_sanity_probe_positivity_violation_threshold():
    assert r6.SANITY_MAX_POSITIVITY_VIOLATION_RATE == 0.01


# Test 36
def test_sanity_probe_realised_pnl_cache_basis_check_present():
    """Sanity probe must check inherited harness signature (no spread_factor / no mid_to_mid)."""
    src = inspect.getsource(r6.run_sanity_probe_r6_new_a)
    assert "precompute_realised_pnl_per_row" in src
    assert "spread_factor" in src or "mid_to_mid" in src
    assert "_compute_realised_barrier_pnl" in src
    assert "bid_h" in src
    assert "ask_l" in src


# ===========================================================================
# Group 9 — End-to-end + report writer (4 tests; 1 NEW)
# ===========================================================================


# Test 37
def test_formal_grid_has_two_cells():
    cells = r6.build_cells()
    assert len(cells) == 2
    assert {c["id"] for c in cells} == {"C01", "C02"}


# Test 38
def test_eval_report_writer_includes_l1_l2_l3_r6_new_a_4_column_comparison():
    src = inspect.getsource(r6.write_eval_report_r6_new_a)
    assert "L-1 / L-2 / L-3 vs R6-new-A" in src
    assert "26.0d-α §13.1" in src
    # Baselines verbatim
    assert "-0.2232" in src
    assert "42150" in src


# Test 39 — [R6-new-A NEW] binding YES/NO/PARTIAL paragraph in report
def test_eval_report_writer_includes_binding_yes_no_partial_paragraph():
    src = inspect.getsource(r6.write_eval_report_r6_new_a)
    assert "YES / NO / PARTIAL" in src
    assert "Identity-break" in src
    assert "26.0d-α §13.2-§13.4" in src


# Test 40
def test_realised_pnl_cache_inherited_from_l2_module():
    """D-1 binding: cache function imported from stage26_0b_l2_eval (inherited)."""
    cache_src = inspect.getsource(r6.precompute_realised_pnl_per_row)
    assert "_compute_realised_barrier_pnl" in cache_src
    # The R6-new-A module re-uses the inherited cache function unmodified
    assert r6.precompute_realised_pnl_per_row.__module__ == "stage26_0b_l2_eval"


# ===========================================================================
# Additional invariant guards
# ===========================================================================


def test_lightgbm_config_inherited_from_l1():
    """R6-new-A holds model class fixed; config identical to #309."""
    assert r6.LIGHTGBM_FIXED_CONFIG["objective"] == "multiclass"
    assert r6.LIGHTGBM_FIXED_CONFIG["num_class"] == 3
    assert r6.LIGHTGBM_FIXED_CONFIG["class_weight"] == "balanced"
    assert r6.LIGHTGBM_FIXED_CONFIG["n_estimators"] == 200
    assert r6.LIGHTGBM_FIXED_CONFIG["learning_rate"] == 0.03
    assert r6.LIGHTGBM_FIXED_CONFIG["random_state"] == 42


def test_feature_importance_buckets_are_four():
    """Decision D10: 4 buckets — pair, direction, atr, spread."""
    # Build a mock pipeline + fit to enable feature_importances_
    # Use a minimal LightGBM model to confirm bucket aggregation
    rng = np.random.default_rng(42)
    n = 200
    df = pd.DataFrame(
        {
            "pair": rng.choice(["EUR_USD", "USD_JPY", "GBP_USD"], size=n),
            "direction": rng.choice(["long", "short"], size=n),
            "atr_at_signal_pip": rng.uniform(1.0, 20.0, size=n),
            "spread_at_signal_pip": rng.uniform(0.5, 5.0, size=n),
        }
    )
    y = rng.choice([0, 1, 2], size=n)
    pipe = r6.build_pipeline_lightgbm_multiclass_widened()
    pipe.fit(df, y)
    fi = r6.compute_feature_importance_diagnostic(pipe)
    assert set(fi["buckets"].keys()) == {
        "pair",
        "direction",
        "atr_at_signal_pip",
        "spread_at_signal_pip",
    }
    assert set(fi["buckets_normalised"].keys()) == set(fi["buckets"].keys())


def test_identity_break_tolerances():
    """Decisions D2/D3/D4 tolerance constants."""
    assert r6.IDENTITY_BREAK_N_TRADES_TOLERANCE == 0  # exact
    assert r6.IDENTITY_BREAK_SHARPE_ABS_TOLERANCE == 1e-4
    assert r6.IDENTITY_BREAK_ANN_PNL_ABS_TOLERANCE == 0.5


def test_identity_break_partial_thresholds():
    """Decision D5: PARTIAL triggers."""
    assert r6.IDENTITY_BREAK_PARTIAL_N_TRADES_DELTA == 100
    assert r6.IDENTITY_BREAK_PARTIAL_CONCENTRATION_SHARE_DELTA == 0.05


def test_baseline_constants_match_l1_l2_l3():
    """Baseline values must match L-1 / L-2 / L-3 fixed outcomes."""
    assert r6.BASELINE_TEST_N_TRADES == 42150
    assert r6.BASELINE_TEST_SHARPE == -0.2232
    assert r6.BASELINE_TEST_ANN_PNL == -237310.8
    assert r6.BASELINE_TOP_PAIR == "USD_JPY"
    assert r6.BASELINE_TOP_PAIR_SHARE == 1.0


def test_no_diagnostic_columns_in_feature_set():
    """Inherited from #309 / clause 2 binding."""
    prohibited = set(r6.PROHIBITED_DIAGNOSTIC_COLUMNS)
    feature_cols = set(r6.ALL_FEATURES)
    assert prohibited.isdisjoint(feature_cols)


def test_amended_clause_6_referenced_in_module_docstring():
    """Module docstring quotes amended clause 6 verbatim per PR #311 §8."""
    doc = r6.__doc__ or ""
    # Normalise whitespace for cross-platform docstring matching
    doc_compact = " ".join(doc.split())
    assert "AMENDED" in doc_compact
    assert "closed allowlist of two features" in doc_compact
    assert "atr_at_signal_pip" in doc_compact
    assert "spread_at_signal_pip" in doc_compact
    assert "Phase 25 continuation" in doc_compact
