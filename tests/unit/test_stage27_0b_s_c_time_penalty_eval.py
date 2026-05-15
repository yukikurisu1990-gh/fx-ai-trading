"""Unit tests for Stage 27.0b-β S-C TIME penalty eval.

~42 tests covering:
- α grid closed-set enforcement (5; 2 NEW)
- S-C score formula (5; 3 NEW)
- α=0.0 baseline-mismatch HALT (4; 2 NEW)
- picker / threshold family (4 inherited)
- verdict routing (5 inherited)
- diagnostic-only prohibition (6; 2 NEW)
- sanity probe (4; 1 NEW)
- per-pair Sharpe contribution (3; 1 NEW)
- end-to-end + α-monotonicity diagnostic (4; 1 NEW)
- additional invariant guards (~5)

12+ NEW 27.0b-specific tests flagged [27.0b NEW].
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

s27 = importlib.import_module("stage27_0b_s_c_time_penalty_eval")


# ===========================================================================
# Group 1 — α grid closed-set enforcement (5 tests; 2 NEW)
# ===========================================================================


def test_alpha_grid_has_4_points():
    assert s27.ALPHA_GRID == (0.0, 0.3, 0.5, 1.0)
    assert len(s27.ALPHA_GRID) == 4


# [27.0b NEW]
def test_alpha_grid_closed_no_intermediate_alphas():
    """No 0.1 / 0.2 / 0.4 / 0.6 / 0.7 / 0.8 / 0.9 / 1.5 / 2.0 etc. in formal grid."""
    excluded = {0.1, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 1.5, 2.0}
    grid_set = set(s27.ALPHA_GRID)
    assert grid_set.isdisjoint(excluded)


# [27.0b NEW]
def test_alpha_grid_closed_no_negative_no_above_one():
    for a in s27.ALPHA_GRID:
        assert 0.0 <= a <= 1.0


def test_build_alpha_cells_returns_4_cells_with_correct_ids():
    cells = s27.build_alpha_cells()
    assert len(cells) == 4
    ids = {c["id"] for c in cells}
    assert ids == {"C-alpha0", "C-alpha03", "C-alpha05", "C-alpha10"}


def test_build_alpha_cells_alpha_values_match_grid():
    cells = s27.build_alpha_cells()
    alphas = tuple(sorted(c["alpha"] for c in cells))
    assert alphas == s27.ALPHA_GRID


# ===========================================================================
# Group 2 — S-C score formula (5 tests; 3 NEW)
# ===========================================================================


# [27.0b NEW]
def test_compute_picker_score_s_c_alpha_zero_equals_s_b():
    """For α=0.0, S-C(probs) == P(TP) - P(SL) (S-B equivalence)."""
    probs = np.array([[0.3, 0.5, 0.2], [0.7, 0.2, 0.1], [0.1, 0.6, 0.3]])
    s_c_alpha_0 = s27.compute_picker_score_s_c(probs, 0.0)
    s_b = probs[:, s27.LABEL_TP] - probs[:, s27.LABEL_SL]
    np.testing.assert_array_almost_equal(s_c_alpha_0, s_b, decimal=12)


# [27.0b NEW]
def test_compute_picker_score_s_c_alpha_one_equals_two_ptp_minus_one():
    """For α=1.0, S-C(probs) == 2·P(TP) - 1 (monotone transform of P(TP))."""
    probs = np.array([[0.3, 0.5, 0.2], [0.7, 0.2, 0.1], [0.1, 0.6, 0.3]])
    s_c_alpha_1 = s27.compute_picker_score_s_c(probs, 1.0)
    expected = 2.0 * probs[:, s27.LABEL_TP] - 1.0
    np.testing.assert_array_almost_equal(s_c_alpha_1, expected, decimal=12)


# [27.0b NEW]
def test_compute_picker_score_s_c_formula_correctness_alpha_03_05():
    """Explicit row-by-row formula verification for α=0.3 and α=0.5."""
    probs = np.array([[0.3, 0.5, 0.2], [0.4, 0.4, 0.2]])
    s_c_03 = s27.compute_picker_score_s_c(probs, 0.3)
    expected_03 = probs[:, 0] - probs[:, 1] - 0.3 * probs[:, 2]
    np.testing.assert_array_almost_equal(s_c_03, expected_03, decimal=12)

    s_c_05 = s27.compute_picker_score_s_c(probs, 0.5)
    expected_05 = probs[:, 0] - probs[:, 1] - 0.5 * probs[:, 2]
    np.testing.assert_array_almost_equal(s_c_05, expected_05, decimal=12)


def test_compute_picker_score_s_c_validates_shape():
    with pytest.raises(ValueError):
        s27.compute_picker_score_s_c(np.zeros((5, 2)), 0.3)  # not 3 classes


def test_compute_picker_score_s_c_returns_float64():
    probs = np.array([[0.3, 0.5, 0.2]], dtype=np.float32)
    score = s27.compute_picker_score_s_c(probs, 0.5)
    assert score.dtype == np.float64


# ===========================================================================
# Group 3 — α=0.0 baseline-mismatch HALT (4 tests; 2 NEW)
# ===========================================================================


# [27.0b NEW]
def test_baseline_mismatch_error_raised_on_n_trades_diff():
    """Per D-T3 binding: n_trades exact-match tolerance; mismatch raises."""
    bad = {
        "test_realised_metrics": {
            "n_trades": s27.BASELINE_R6_NEW_A_C02_N_TRADES - 1,
            "sharpe": s27.BASELINE_R6_NEW_A_C02_SHARPE,
            "annual_pnl": s27.BASELINE_R6_NEW_A_C02_ANN_PNL,
        }
    }
    with pytest.raises(s27.BaselineMismatchError) as exc:
        s27.check_alpha_zero_baseline_match(bad)
    assert "n_trades" in str(exc.value)


# [27.0b NEW]
def test_baseline_mismatch_error_raised_on_sharpe_diff_above_tolerance():
    """Per D-T3 binding: Sharpe abs diff > 1e-4 raises."""
    bad = {
        "test_realised_metrics": {
            "n_trades": s27.BASELINE_R6_NEW_A_C02_N_TRADES,
            "sharpe": s27.BASELINE_R6_NEW_A_C02_SHARPE + 5e-4,  # > 1e-4 tolerance
            "annual_pnl": s27.BASELINE_R6_NEW_A_C02_ANN_PNL,
        }
    }
    with pytest.raises(s27.BaselineMismatchError) as exc:
        s27.check_alpha_zero_baseline_match(bad)
    assert "Sharpe" in str(exc.value)


def test_baseline_mismatch_check_passes_on_exact_baseline_metrics():
    good = {
        "test_realised_metrics": {
            "n_trades": s27.BASELINE_R6_NEW_A_C02_N_TRADES,
            "sharpe": s27.BASELINE_R6_NEW_A_C02_SHARPE,
            "annual_pnl": s27.BASELINE_R6_NEW_A_C02_ANN_PNL,
        }
    }
    report = s27.check_alpha_zero_baseline_match(good)
    assert report["all_match"] is True
    assert report["n_trades_match"] is True
    assert report["sharpe_match"] is True
    assert report["ann_pnl_match"] is True


def test_baseline_match_tolerance_constants():
    """Tolerance constants must equal §12.2 spec."""
    assert s27.BASELINE_MATCH_N_TRADES_TOLERANCE == 0
    assert s27.BASELINE_MATCH_SHARPE_ABS_TOLERANCE == 1e-4
    assert s27.BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE == 0.5
    # Baseline values match #313 R6-new-A C02
    assert s27.BASELINE_R6_NEW_A_C02_N_TRADES == 34626
    assert s27.BASELINE_R6_NEW_A_C02_SHARPE == -0.1732
    assert s27.BASELINE_R6_NEW_A_C02_ANN_PNL == -204664.4


# ===========================================================================
# Group 4 — Picker / threshold family (4 inherited)
# ===========================================================================


def test_quantile_threshold_family_has_5_candidates():
    assert s27.THRESHOLDS_QUANTILE_PERCENTS == (5, 10, 20, 30, 40)


def test_select_quantile_cutoff_returns_top_q_percent():
    rng = np.random.default_rng(0)
    pred_val = rng.uniform(0, 1, size=1000)
    cutoff = s27.fit_quantile_cutoff_on_val(pred_val, 10)
    n_above = int((pred_val >= cutoff).sum())
    assert 80 <= n_above <= 120


def test_quantile_cutoff_scalar_applied_to_test_unchanged():
    rng = np.random.default_rng(7)
    score_val = rng.normal(0.0, 0.1, size=500)
    pnl_val = rng.normal(0.0, 1.0, size=500)
    score_test = rng.normal(0.0, 0.1, size=300)
    pnl_test = rng.normal(0.0, 1.0, size=300)
    res_a = s27.evaluate_quantile_family(score_val, pnl_val, score_test, pnl_test, 0.1, 0.1)
    score_test_perturbed = score_test + 100.0
    res_b = s27.evaluate_quantile_family(
        score_val, pnl_val, score_test_perturbed, pnl_test, 0.1, 0.1
    )
    for ra, rb in zip(res_a, res_b, strict=True):
        assert ra["cutoff"] == pytest.approx(rb["cutoff"], abs=1e-12)


def test_a0_prefilter_drops_quantiles_below_200_trades():
    a0_min = s27.A0_MIN_ANNUAL_TRADES * s27.VAL_SPAN_YEARS
    cells = [
        {
            "cell": {"id": "C-alpha0", "alpha": 0.0, "picker": "S-C(α=0.0)"},
            "selected_q_percent": 5,
            "val_realised_sharpe": 0.50,
            "val_realised_annual_pnl": 200.0,
            "val_n_trades": int(a0_min) - 1,
            "val_max_dd": 10.0,
            "h_state": "OK",
        },
        {
            "cell": {"id": "C-alpha03", "alpha": 0.3, "picker": "S-C(α=0.3)"},
            "selected_q_percent": 10,
            "val_realised_sharpe": 0.20,
            "val_realised_annual_pnl": 100.0,
            "val_n_trades": int(a0_min) + 100,
            "val_max_dd": 8.0,
            "h_state": "OK",
        },
    ]
    res = s27.select_cell_validation_only(cells)
    assert res["selected"]["cell"]["id"] == "C-alpha03"


# ===========================================================================
# Group 5 — Verdict routing (5 inherited)
# ===========================================================================


def test_h1_weak_pass_when_test_spearman_above_005():
    val_selected = {
        "test_formal_spearman": 0.06,
        "test_gates": {},
        "test_realised_metrics": {"sharpe": float("nan")},
    }
    res = s27.assign_verdict(val_selected)
    assert res["h1_weak_pass"] is True


def test_h1_weak_fail_when_test_spearman_at_or_below_005():
    val_selected = {
        "test_formal_spearman": 0.05,
        "test_gates": {},
        "test_realised_metrics": {"sharpe": float("nan")},
    }
    res = s27.assign_verdict(val_selected)
    assert res["h1_weak_pass"] is False
    assert res["verdict"] == "REJECT_NON_DISCRIMINATIVE"


def test_h2_requires_both_sharpe_and_ann_pnl():
    val_selected = {
        "test_formal_spearman": 0.20,
        "test_gates": {"A1": True, "A2": False, "A0": True, "A3": True, "A4": True, "A5": True},
        "test_realised_metrics": {"sharpe": 0.10},
    }
    res = s27.assign_verdict(val_selected)
    assert res["h2_pass"] is False


def test_h3_uses_neg_0192_baseline():
    assert pytest.approx(-0.192) == s27.H3_REFERENCE_SHARPE


def test_h2_pass_alone_does_not_yield_adopt_candidate_in_27_0b_beta():
    val_selected = {
        "test_formal_spearman": 0.20,
        "test_gates": {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True},
        "test_realised_metrics": {"sharpe": 0.10},
    }
    res = s27.assign_verdict(val_selected)
    assert res["h2_pass"] is True
    assert res["verdict"] == "PROMISING_BUT_NEEDS_OOS"
    assert res["verdict"] != "ADOPT_CANDIDATE"


# ===========================================================================
# Group 6 — Diagnostic-only prohibition (6 tests; 2 NEW)
# ===========================================================================


def test_concentration_high_flag_is_diagnostic_only():
    sel_src = inspect.getsource(s27.select_cell_validation_only)
    assert "concentration_high" not in sel_src
    verdict_src = inspect.getsource(s27.assign_verdict)
    assert "concentration_high" not in verdict_src


def test_absolute_thresholds_excluded_from_cell_selection():
    src = inspect.getsource(s27.select_cell_validation_only)
    assert "absolute_best" not in src
    assert "absolute_all" not in src


def test_classification_diagnostics_not_used_in_h1():
    src = inspect.getsource(s27.assign_verdict)
    assert "test_formal_spearman" in src
    assert "auc_tp_ovr" not in src
    assert "cohen_kappa" not in src


def test_isotonic_appendix_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        s27.compute_isotonic_diagnostic_appendix()


# [27.0b NEW]
def test_alpha_monotonicity_diagnostic_not_used_in_verdict():
    """α-monotonicity diagnostic NEVER enters formal verdict routing."""
    verdict_src = inspect.getsource(s27.assign_verdict)
    sel_src = inspect.getsource(s27.select_cell_validation_only)
    for src in (verdict_src, sel_src):
        assert "monotonic_test_sharpe" not in src
        assert "monotonic_val_sharpe" not in src
        assert "alpha_monotonicity" not in src


# [27.0b NEW]
def test_per_pair_sharpe_contribution_not_used_in_verdict():
    """Per-pair Sharpe contribution NEVER enters formal verdict routing."""
    verdict_src = inspect.getsource(s27.assign_verdict)
    sel_src = inspect.getsource(s27.select_cell_validation_only)
    for src in (verdict_src, sel_src):
        assert "per_pair_sharpe_contribution" not in src


# ===========================================================================
# Group 7 — Sanity probe (4 tests; 1 NEW)
# ===========================================================================


def test_sanity_probe_inherits_r7_a_nan_threshold():
    assert s27.SANITY_MAX_NEW_FEATURE_NAN_RATE == 0.05


def test_sanity_probe_inherits_class_share_threshold():
    assert s27.SANITY_MIN_CLASS_SHARE == 0.01
    assert s27.SANITY_MAX_PER_PAIR_TIME_SHARE == 0.99


# [27.0b NEW]
def test_sanity_probe_includes_p_time_distribution_diagnostic():
    """Per D-T5: P(TIME) distribution diagnostic included; report-only."""
    src = inspect.getsource(s27.run_sanity_probe_27_0b)
    assert "P(TIME)" in src
    assert "report-only" in src.lower() or "deferred" in src.lower()
    # Verify P(TIME) block itself is report-only (no HALT threshold): the
    # p_time_distribution dict is populated but no raise depends on its values.
    # Find the slice between "P(TIME) distribution diagnostic" and the next
    # HALT-conditions section.
    start = src.find("P(TIME) distribution diagnostic")
    end = src.find("# Inherited HALT conditions")
    assert start >= 0 and end >= 0 and start < end
    p_time_block = src[start:end]
    assert "raise SanityProbeError" not in p_time_block


def test_sanity_probe_realised_pnl_cache_basis_check_present():
    src = inspect.getsource(s27.run_sanity_probe_27_0b)
    assert "_compute_realised_barrier_pnl" in src
    assert "bid_h" in src
    assert "ask_l" in src


# ===========================================================================
# Group 8 — Per-pair Sharpe contribution (3 tests; 1 NEW)
# ===========================================================================


# [27.0b NEW]
def test_per_pair_sharpe_contribution_returns_required_keys():
    """Per D-T7: per-pair output has n_trades, sharpe, share_of_total_pnl, share_of_total_trades."""
    df = pd.DataFrame(
        {
            "pair": ["EUR_USD"] * 5 + ["USD_JPY"] * 3,
            "direction": ["long"] * 8,
        }
    )
    rng = np.random.default_rng(0)
    pnl = rng.normal(0.0, 1.0, size=8)
    traded_mask = np.ones(8, dtype=bool)
    result = s27.compute_per_pair_sharpe_contribution(df, traded_mask, pnl)
    assert "per_pair" in result
    for row in result["per_pair"]:
        assert "pair" in row
        assert "n_trades" in row
        assert "sharpe" in row
        assert "share_of_total_pnl" in row
        assert "share_of_total_trades" in row


def test_per_pair_sharpe_contribution_handles_empty_traded_mask():
    df = pd.DataFrame({"pair": ["EUR_USD"] * 5, "direction": ["long"] * 5})
    pnl = np.array([0.1, -0.2, 0.3, -0.4, 0.5])
    traded_mask = np.zeros(5, dtype=bool)
    result = s27.compute_per_pair_sharpe_contribution(df, traded_mask, pnl)
    assert result["per_pair"] == []
    assert result["total_n_trades"] == 0


def test_per_pair_sharpe_contribution_sorted_by_share_of_pnl_descending():
    """Per D4 binding: sort by share_of_total_pnl descending."""
    df = pd.DataFrame(
        {
            "pair": ["A"] * 3 + ["B"] * 3 + ["C"] * 3,
            "direction": ["long"] * 9,
        }
    )
    # Construct PnL so that pair C has highest share, then A, then B
    pnl = np.array([1.0, 1.0, 1.0, 0.1, 0.1, 0.1, 5.0, 5.0, 5.0])
    traded_mask = np.ones(9, dtype=bool)
    result = s27.compute_per_pair_sharpe_contribution(df, traded_mask, pnl)
    pairs_ordered = [row["pair"] for row in result["per_pair"]]
    assert pairs_ordered == ["C", "A", "B"]


# ===========================================================================
# Group 9 — End-to-end + α-monotonicity diagnostic (4 tests; 1 NEW)
# ===========================================================================


def test_formal_grid_has_four_cells():
    cells = s27.build_alpha_cells()
    assert len(cells) == 4


# [27.0b NEW]
def test_alpha_monotonicity_diagnostic_emits_per_alpha_series():
    """Per D-T6: α-monotonicity diagnostic returns per-α series + classification."""
    cell_results = [
        {
            "cell": {"id": "C-alpha0", "alpha": 0.0, "picker": "S-C(α=0.0)"},
            "val_realised_sharpe": -0.18,
            "val_realised_annual_pnl": -210000.0,
            "test_realised_metrics": {"sharpe": -0.17, "annual_pnl": -200000.0},
            "test_formal_spearman": -0.15,
        },
        {
            "cell": {"id": "C-alpha03", "alpha": 0.3, "picker": "S-C(α=0.3)"},
            "val_realised_sharpe": -0.21,
            "val_realised_annual_pnl": -220000.0,
            "test_realised_metrics": {"sharpe": -0.20, "annual_pnl": -210000.0},
            "test_formal_spearman": -0.11,
        },
        {
            "cell": {"id": "C-alpha05", "alpha": 0.5, "picker": "S-C(α=0.5)"},
            "val_realised_sharpe": -0.22,
            "val_realised_annual_pnl": -230000.0,
            "test_realised_metrics": {"sharpe": -0.22, "annual_pnl": -220000.0},
            "test_formal_spearman": -0.08,
        },
        {
            "cell": {"id": "C-alpha10", "alpha": 1.0, "picker": "S-C(α=1.0)"},
            "val_realised_sharpe": -0.24,
            "val_realised_annual_pnl": -240000.0,
            "test_realised_metrics": {"sharpe": -0.25, "annual_pnl": -230000.0},
            "test_formal_spearman": 0.02,
        },
    ]
    diag = s27.compute_alpha_monotonicity_diagnostic(cell_results)
    assert len(diag["per_alpha"]) == 4
    assert diag["alpha_order"] == [0.0, 0.3, 0.5, 1.0]
    # Strict decreasing val Sharpe
    assert diag["monotonic_val_sharpe"] == "decreasing"
    # Strict decreasing test Sharpe
    assert diag["monotonic_test_sharpe"] == "decreasing"
    # Strict increasing test Spearman
    assert diag["monotonic_test_spearman"] == "increasing"


def test_alpha_monotonicity_strict_classification_no_epsilon_tolerance():
    """Per D5 binding: strict monotonic or mixed; no ε-tolerance."""
    # Constant series → diff=0 → mixed (not 'increasing' or 'decreasing')
    cell_results = [
        {
            "cell": {"id": f"C-alpha{i}", "alpha": float(a), "picker": "x"},
            "val_realised_sharpe": -0.20,  # constant
            "val_realised_annual_pnl": 0.0,
            "test_realised_metrics": {"sharpe": -0.20, "annual_pnl": 0.0},
            "test_formal_spearman": 0.0,
        }
        for i, a in enumerate([0.0, 0.3, 0.5, 1.0])
    ]
    diag = s27.compute_alpha_monotonicity_diagnostic(cell_results)
    # Constant → diff=0 → mixed
    assert diag["monotonic_val_sharpe"] == "mixed"


def test_eval_report_writer_includes_baseline_comparison_table():
    src = inspect.getsource(s27.write_eval_report_27_0b)
    assert "Baseline comparison" in src
    assert "27.0b-α §12.1" in src
    # Inherited baselines must appear
    assert "34,626" in src or "34626" in src
    assert "-0.1732" in src
    assert "-0.2232" in src
    assert "42,150" in src or "42150" in src


def test_eval_report_writer_includes_alpha_zero_sanity_check_section():
    src = inspect.getsource(s27.write_eval_report_27_0b)
    assert "α=0.0 sanity-check declaration" in src
    assert "27.0b-α §12.2" in src


# ===========================================================================
# Additional invariant guards
# ===========================================================================


def test_lightgbm_config_inherited_from_l1():
    """27.0b holds model class fixed; config identical to #309 / #313."""
    assert s27.LIGHTGBM_FIXED_CONFIG["objective"] == "multiclass"
    assert s27.LIGHTGBM_FIXED_CONFIG["num_class"] == 3
    assert s27.LIGHTGBM_FIXED_CONFIG["class_weight"] == "balanced"
    assert s27.LIGHTGBM_FIXED_CONFIG["random_state"] == 42


def test_r7_a_feature_set_unchanged_from_phase_26():
    assert s27.ALL_FEATURES == ("pair", "direction", "atr_at_signal_pip", "spread_at_signal_pip")
    assert s27.NUMERIC_FEATURES == ("atr_at_signal_pip", "spread_at_signal_pip")
    assert s27.CATEGORICAL_COLS == ["pair", "direction"]


def test_no_diagnostic_columns_in_feature_set():
    prohibited = set(s27.PROHIBITED_DIAGNOSTIC_COLUMNS)
    feature_cols = set(s27.ALL_FEATURES)
    assert prohibited.isdisjoint(feature_cols)


def test_amended_clause_6_referenced_in_module_docstring():
    doc = s27.__doc__ or ""
    doc_compact = " ".join(doc.split())
    assert "Phase 27 scope" in doc_compact
    assert "R7-A" in doc_compact
    assert "S-C" in doc_compact
    # S-C formula must be documented (allow [row] indexing or not)
    assert "P(TP)" in doc_compact and "P(SL)" in doc_compact and "P(TIME)" in doc_compact


def test_realised_pnl_cache_inherited_from_l2_module():
    """D-1 binding: cache function imported from stage26_0b_l2_eval."""
    assert s27.precompute_realised_pnl_per_row.__module__ == "stage26_0b_l2_eval"


def test_no_pair_concentration_formal_selection_in_27_0b():
    """27.0b does NOT opt-in per-pair-share regularised cell selection."""
    sel_src = inspect.getsource(s27.select_cell_validation_only)
    assert "per_pair" not in sel_src or "per_pair_sharpe_contribution" not in sel_src


def test_single_model_fit_shared_across_alpha_cells():
    """Per D10 binding: single pipeline.fit + single predict_proba; α cells use cached probs."""
    main_src = inspect.getsource(s27.main)
    # Only ONE pipeline.fit call
    assert main_src.count("pipeline.fit") == 1
    # Only ONE predict_proba for val and ONE for test
    assert main_src.count("predict_proba(x_val)") == 1
    assert main_src.count("predict_proba(x_test)") == 1


def test_baseline_mismatch_error_is_runtime_error_subclass():
    assert issubclass(s27.BaselineMismatchError, RuntimeError)
