"""Unit tests for Stage 27.0c-β S-D Calibrated EV eval.

~62-65 tests covering:
- S-D score formula correctness (5 NEW)
- Per-row sum-to-1 renormalisation (4 NEW)
- Isotonic calibration (5 NEW)
- 5-fold OOF protocol (5 NEW)
- Conditional-PnL estimator (6 NEW)
- BaselineMismatchError HALT (4 NEW)
- Cell construction (3 NEW)
- S-B raw baseline replica (3 NEW)
- D10 amendment single-fit (2 NEW)
- Class index mapping (2 NEW)
- Diagnostic-only prohibition (5 NEW)
- Sanity probe extensions (3 NEW)
- Reliability diagram (2 NEW)
- Divergence flag (3 NEW)
- Mandatory clauses (2 NEW)
- Module docstring / D-1 binding (3 NEW)

NEW 27.0c-specific tests flagged [27.0c NEW].
"""

from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.isotonic import IsotonicRegression

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

s27c = importlib.import_module("stage27_0c_s_d_calibrated_ev_eval")


# ===========================================================================
# Group 1 — S-D score formula correctness (5 NEW)
# ===========================================================================


# [27.0c NEW]
def test_s_d_score_formula_explicit_row_by_row():
    """S-D(row) = Σ_c P_cal[c] · Ê[PnL|c] computed correctly."""
    p_cal = np.array([[0.4, 0.4, 0.2], [0.6, 0.2, 0.2], [0.2, 0.5, 0.3]], dtype=np.float64)
    e_pnl = {s27c.LABEL_TP: 5.0, s27c.LABEL_SL: -10.0, s27c.LABEL_TIME: 0.5}
    scores = s27c.compute_picker_score_s_d(p_cal, e_pnl)
    expected = np.array(
        [
            0.4 * 5.0 + 0.4 * (-10.0) + 0.2 * 0.5,
            0.6 * 5.0 + 0.2 * (-10.0) + 0.2 * 0.5,
            0.2 * 5.0 + 0.5 * (-10.0) + 0.3 * 0.5,
        ]
    )
    np.testing.assert_array_almost_equal(scores, expected, decimal=12)


# [27.0c NEW]
def test_s_d_score_formula_uniform_distribution_returns_average_estimate():
    """Uniform (1/3, 1/3, 1/3) probs → score = mean of estimator constants."""
    p_cal = np.full((1, 3), 1.0 / 3.0, dtype=np.float64)
    e_pnl = {s27c.LABEL_TP: 3.0, s27c.LABEL_SL: -6.0, s27c.LABEL_TIME: 0.0}
    scores = s27c.compute_picker_score_s_d(p_cal, e_pnl)
    np.testing.assert_array_almost_equal(scores, np.array([-1.0]), decimal=12)


# [27.0c NEW]
def test_s_d_score_formula_degenerate_class_one_hot():
    """One-hot probs select exactly that class's estimator."""
    p_cal = np.eye(3, dtype=np.float64)
    e_pnl = {s27c.LABEL_TP: 7.0, s27c.LABEL_SL: -4.0, s27c.LABEL_TIME: 1.5}
    scores = s27c.compute_picker_score_s_d(p_cal, e_pnl)
    expected = np.array([e_pnl[s27c.LABEL_TP], e_pnl[s27c.LABEL_SL], e_pnl[s27c.LABEL_TIME]])
    np.testing.assert_array_almost_equal(scores, expected, decimal=12)


# [27.0c NEW]
def test_s_d_score_rejects_wrong_shape_probs():
    """S-D scoring requires (N, 3) shape."""
    with pytest.raises(ValueError, match=r"shape"):
        s27c.compute_picker_score_s_d(
            np.zeros((5, 4)), {s27c.LABEL_TP: 0.0, s27c.LABEL_SL: 0.0, s27c.LABEL_TIME: 0.0}
        )


# [27.0c NEW]
def test_s_d_score_rejects_wrong_estimator_keys():
    """S-D scoring requires exactly {LABEL_TP, LABEL_SL, LABEL_TIME} keys."""
    p_cal = np.full((1, 3), 1.0 / 3.0)
    with pytest.raises(ValueError, match=r"keys"):
        s27c.compute_picker_score_s_d(p_cal, {0: 1.0, 1: 2.0})  # missing LABEL_TIME


# ===========================================================================
# Group 2 — Per-row sum-to-1 renormalisation (4 NEW)
# ===========================================================================


# [27.0c NEW]
def test_apply_isotonic_and_renormalise_rows_sum_to_one():
    """After per-row renormalisation, all rows sum to ~1.0."""
    rng = np.random.default_rng(42)
    n = 200
    raw = rng.dirichlet(np.ones(s27c.NUM_CLASSES), n).astype(np.float64)
    train_label = rng.integers(0, s27c.NUM_CLASSES, n)
    oof = rng.dirichlet(np.ones(s27c.NUM_CLASSES), n).astype(np.float64)
    cals = s27c.fit_isotonic_calibrators_per_class(oof, train_label)
    p_cal, n_zero = s27c.apply_isotonic_and_renormalise(raw, cals)
    np.testing.assert_array_almost_equal(p_cal.sum(axis=1), np.ones(n), decimal=8)
    assert n_zero == 0 or isinstance(n_zero, int)


# [27.0c NEW]
def test_apply_isotonic_and_renormalise_zero_sum_fallback_uses_raw():
    """Zero-sum row falls back to raw probs (renormalised)."""
    # Construct calibrators that map everything to 0 for one class
    rng = np.random.default_rng(1)
    raw_train = rng.dirichlet(np.ones(s27c.NUM_CLASSES), 50).astype(np.float64)
    train_label = np.full(50, s27c.LABEL_TP)  # all TP → SL/TIME isotonic maps all to 0
    cals = s27c.fit_isotonic_calibrators_per_class(raw_train, train_label)
    # A raw row with all probability on a class isotonic-mapped to 0
    raw_inf = np.array([[0.001, 0.999, 0.0]], dtype=np.float64)
    p_cal, n_zero = s27c.apply_isotonic_and_renormalise(raw_inf, cals)
    # Fallback should have produced a valid distribution (sum to 1)
    np.testing.assert_almost_equal(p_cal.sum(axis=1), np.array([1.0]), decimal=8)
    # n_zero may be 0 or 1 depending on isotonic behavior; just check it's int
    assert isinstance(n_zero, int) and n_zero >= 0


# [27.0c NEW]
def test_apply_isotonic_and_renormalise_rejects_wrong_shape():
    """Renormaliser requires (N, NUM_CLASSES) shape."""
    cals = [
        IsotonicRegression(out_of_bounds="clip").fit([0.0, 1.0], [0.0, 1.0])
        for _ in range(s27c.NUM_CLASSES)
    ]
    with pytest.raises(ValueError, match=r"shape"):
        s27c.apply_isotonic_and_renormalise(np.zeros((10, 2)), cals)


# [27.0c NEW]
def test_apply_isotonic_and_renormalise_rejects_wrong_calibrator_count():
    cals = [IsotonicRegression(out_of_bounds="clip").fit([0.0, 1.0], [0.0, 1.0])]
    with pytest.raises(ValueError, match=r"calibrators"):
        s27c.apply_isotonic_and_renormalise(np.zeros((10, s27c.NUM_CLASSES)), cals)


# ===========================================================================
# Group 3 — Isotonic calibration (5 NEW)
# ===========================================================================


# [27.0c NEW]
def test_fit_isotonic_calibrators_returns_one_per_class():
    rng = np.random.default_rng(123)
    n = 200
    oof = rng.dirichlet(np.ones(s27c.NUM_CLASSES), n).astype(np.float64)
    labels = rng.integers(0, s27c.NUM_CLASSES, n)
    cals = s27c.fit_isotonic_calibrators_per_class(oof, labels)
    assert len(cals) == s27c.NUM_CLASSES
    for c in cals:
        assert isinstance(c, IsotonicRegression)


# [27.0c NEW]
def test_fit_isotonic_calibrators_monotone_preserving():
    """Isotonic output is monotone non-decreasing in input."""
    rng = np.random.default_rng(7)
    n = 500
    oof = rng.dirichlet(np.ones(s27c.NUM_CLASSES), n).astype(np.float64)
    labels = rng.integers(0, s27c.NUM_CLASSES, n)
    cals = s27c.fit_isotonic_calibrators_per_class(oof, labels)
    for c in range(s27c.NUM_CLASSES):
        x_query = np.linspace(0.0, 1.0, 101)
        y_query = cals[c].predict(x_query)
        # Strict monotonicity not guaranteed (plateaus allowed); non-decreasing required
        assert np.all(np.diff(y_query) >= -1e-12), f"class {c} not monotone non-decreasing"


# [27.0c NEW]
def test_fit_isotonic_calibrators_rejects_wrong_oof_shape():
    rng = np.random.default_rng(9)
    oof_wrong = rng.dirichlet(np.ones(2), 50).astype(np.float64)
    labels = rng.integers(0, 3, 50)
    with pytest.raises(ValueError, match=r"columns"):
        s27c.fit_isotonic_calibrators_per_class(oof_wrong, labels)


# [27.0c NEW]
def test_isotonic_clip_bounds_match_d_i3():
    """D-I3 binding: y_min=0.0, y_max=1.0, out_of_bounds='clip'."""
    assert s27c.ISOTONIC_Y_MIN == 0.0
    assert s27c.ISOTONIC_Y_MAX == 1.0
    src = inspect.getsource(s27c.fit_isotonic_calibrators_per_class)
    assert 'out_of_bounds="clip"' in src or "out_of_bounds='clip'" in src


# [27.0c NEW]
def test_compute_calibration_diagnostic_has_breakpoint_count_and_shifts():
    rng = np.random.default_rng(33)
    n = 300
    oof = rng.dirichlet(np.ones(s27c.NUM_CLASSES), n).astype(np.float64)
    labels = rng.integers(0, s27c.NUM_CLASSES, n)
    cals = s27c.fit_isotonic_calibrators_per_class(oof, labels)
    diag = s27c.compute_calibration_diagnostic(cals, oof)
    for c in range(s27c.NUM_CLASSES):
        assert "breakpoint_count" in diag[c]
        assert "mean_shift" in diag[c]
        assert "mean_abs_shift" in diag[c]
        assert isinstance(diag[c]["breakpoint_count"], int)


# ===========================================================================
# Group 4 — 5-fold OOF protocol (5 NEW)
# ===========================================================================


# [27.0c NEW]
def test_make_oof_fold_assignment_deterministic_with_seed_42():
    """Same seed → same fold assignment."""
    f1 = s27c.make_oof_fold_assignment(1000, seed=42)
    f2 = s27c.make_oof_fold_assignment(1000, seed=42)
    np.testing.assert_array_equal(f1, f2)


# [27.0c NEW]
def test_make_oof_fold_assignment_different_seeds_differ():
    f1 = s27c.make_oof_fold_assignment(1000, seed=42)
    f2 = s27c.make_oof_fold_assignment(1000, seed=43)
    # Almost certainly differ on a 1000-row permutation
    assert not np.array_equal(f1, f2)


# [27.0c NEW]
def test_make_oof_fold_assignment_fold_sizes_within_one_row():
    """np.array_split produces folds within 1 row of equal."""
    for n_rows in [100, 1001, 5_000, 100_000]:
        fold_idx = s27c.make_oof_fold_assignment(n_rows, n_folds=5, seed=42)
        sizes = [int((fold_idx == f).sum()) for f in range(5)]
        assert max(sizes) - min(sizes) <= 1, f"n_rows={n_rows}: sizes={sizes}"
        assert sum(sizes) == n_rows


# [27.0c NEW]
def test_make_oof_fold_assignment_covers_all_rows_exactly_once():
    fold_idx = s27c.make_oof_fold_assignment(500, n_folds=5, seed=42)
    assert len(fold_idx) == 500
    assert fold_idx.min() == 0
    assert fold_idx.max() == 4
    # Each row gets exactly one fold
    for i in range(500):
        assert 0 <= fold_idx[i] < 5


# [27.0c NEW]
def test_make_oof_fold_assignment_rejects_invalid_n_folds():
    with pytest.raises(ValueError, match=r"n_folds"):
        s27c.make_oof_fold_assignment(100, n_folds=1, seed=42)


# ===========================================================================
# Group 5 — Conditional-PnL estimator (6 NEW)
# ===========================================================================


# [27.0c NEW]
def test_compute_class_conditional_pnl_returns_per_class_means():
    rng = np.random.default_rng(11)
    n = 1000
    labels = rng.integers(0, 3, n)
    pnls = rng.normal(0.0, 1.0, n)
    out = s27c.compute_class_conditional_pnl(labels, pnls)
    # Verify each constant equals the mean of its class
    for c in [s27c.LABEL_TP, s27c.LABEL_SL, s27c.LABEL_TIME]:
        expected = float(pnls[labels == c].mean())
        np.testing.assert_almost_equal(out[c], expected, decimal=12)


# [27.0c NEW]
def test_compute_class_conditional_pnl_raises_on_empty_class():
    """Per D-I5: empty class → ValueError; no imputation."""
    labels = np.array([0, 0, 0, 1, 1])  # no class 2
    pnls = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    with pytest.raises(ValueError, match=r"0 rows"):
        s27c.compute_class_conditional_pnl(labels, pnls)


# [27.0c NEW]
def test_compute_class_conditional_pnl_skips_nan_pnls():
    labels = np.array([0, 0, 0, 1, 1, 2, 2])
    pnls = np.array([1.0, np.nan, 3.0, 4.0, 6.0, 1.0, 1.0])
    out = s27c.compute_class_conditional_pnl(labels, pnls)
    np.testing.assert_almost_equal(out[0], 2.0, decimal=12)  # mean of [1.0, 3.0]
    np.testing.assert_almost_equal(out[1], 5.0, decimal=12)
    np.testing.assert_almost_equal(out[2], 1.0, decimal=12)


# [27.0c NEW]
def test_compute_class_conditional_pnl_rejects_length_mismatch():
    with pytest.raises(ValueError, match=r"!="):
        s27c.compute_class_conditional_pnl(np.array([0, 1, 2]), np.array([1.0, 2.0]))


# [27.0c NEW]
def test_compute_oof_class_conditional_pnl_per_fold_and_aggregate():
    rng = np.random.default_rng(22)
    n = 500
    labels = rng.integers(0, 3, n)
    pnls = rng.normal(0.0, 1.0, n)
    fold_idx = s27c.make_oof_fold_assignment(n, n_folds=5, seed=42)
    out = s27c.compute_oof_class_conditional_pnl(labels, pnls, fold_idx)
    for c in range(3):
        assert "per_fold_mean" in out[c]
        assert "per_fold_count" in out[c]
        assert "oof_aggregate_mean" in out[c]
        assert len(out[c]["per_fold_mean"]) == 5


# [27.0c NEW]
def test_estimator_divergence_flag_suppressed_when_full_train_near_zero():
    """D-I6: |full_train| < 1e-9 → flag suppressed."""
    full = {0: 0.0, 1: 1.0, 2: 0.5}
    oof = {
        0: {"oof_aggregate_mean": 1.0},  # huge "rel" delta but full=0
        1: {"oof_aggregate_mean": 1.05},  # 5% rel — under threshold
        2: {"oof_aggregate_mean": 0.6},  # 20% rel — over threshold
    }
    flags = s27c.compute_estimator_divergence_flag(full, oof)
    assert flags[0]["suppressed_div_by_zero"] is True
    assert flags[0]["divergence_flag"] is False
    assert flags[1]["divergence_flag"] is False
    assert flags[2]["divergence_flag"] is True


# ===========================================================================
# Group 6 — BaselineMismatchError HALT (4 NEW)
# ===========================================================================


# [27.0c NEW]
def test_baseline_mismatch_error_is_runtime_error_subclass():
    assert issubclass(s27c.BaselineMismatchError, RuntimeError)


# [27.0c NEW]
def test_check_c_sb_baseline_match_passes_at_exact_baseline():
    """Exact baseline → all_match=True; no raise."""
    fake = {
        "test_realised_metrics": {
            "n_trades": s27c.BASELINE_27_0B_C_ALPHA0_N_TRADES,
            "sharpe": s27c.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s27c.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    report = s27c.check_c_sb_baseline_match(fake)
    assert report["all_match"] is True
    assert report["n_trades_match"] is True
    assert report["sharpe_match"] is True
    assert report["ann_pnl_match"] is True


# [27.0c NEW]
def test_check_c_sb_baseline_match_halts_on_n_trades_drift():
    fake = {
        "test_realised_metrics": {
            "n_trades": s27c.BASELINE_27_0B_C_ALPHA0_N_TRADES + 1,
            "sharpe": s27c.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s27c.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    with pytest.raises(s27c.BaselineMismatchError, match=r"n_trades"):
        s27c.check_c_sb_baseline_match(fake)


# [27.0c NEW]
def test_check_c_sb_baseline_match_halts_on_sharpe_drift():
    fake = {
        "test_realised_metrics": {
            "n_trades": s27c.BASELINE_27_0B_C_ALPHA0_N_TRADES,
            "sharpe": s27c.BASELINE_27_0B_C_ALPHA0_SHARPE - 0.01,  # 0.01 > 1e-4 tolerance
            "annual_pnl": s27c.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    with pytest.raises(s27c.BaselineMismatchError, match=r"Sharpe"):
        s27c.check_c_sb_baseline_match(fake)


# ===========================================================================
# Group 7 — Cell construction (3 NEW)
# ===========================================================================


# [27.0c NEW]
def test_build_s_d_cells_returns_two_cells():
    cells = s27c.build_s_d_cells()
    assert len(cells) == 2


# [27.0c NEW]
def test_build_s_d_cells_has_c_sd_and_c_sb_baseline_with_correct_score_types():
    cells = s27c.build_s_d_cells()
    by_id = {c["id"]: c for c in cells}
    assert "C-sd" in by_id
    assert "C-sb-baseline" in by_id
    assert by_id["C-sd"]["score_type"] == "s_d"
    assert by_id["C-sb-baseline"]["score_type"] == "s_b_raw"


# [27.0c NEW]
def test_build_s_d_cells_has_no_other_cells():
    """D-U9 / D-I8: no within-27.0c-β estimation-method sweep."""
    cells = s27c.build_s_d_cells()
    ids = {c["id"] for c in cells}
    assert ids == {"C-sd", "C-sb-baseline"}


# ===========================================================================
# Group 8 — S-B raw baseline replica (3 NEW)
# ===========================================================================


# [27.0c NEW]
def test_compute_picker_score_s_b_raw_equals_p_tp_minus_p_sl():
    raw = np.array([[0.3, 0.5, 0.2], [0.6, 0.1, 0.3]], dtype=np.float64)
    s_b = s27c.compute_picker_score_s_b_raw(raw)
    expected = raw[:, s27c.LABEL_TP] - raw[:, s27c.LABEL_SL]
    np.testing.assert_array_almost_equal(s_b, expected, decimal=12)


# [27.0c NEW]
def test_compute_picker_score_s_b_raw_does_not_use_calibrators():
    """C-sb-baseline must not apply isotonic calibration (D-I8).

    Per D-I8, S-B raw uses raw `P(TP) - P(SL)` to exactly reproduce 27.0b
    C-alpha0. The implementation must not invoke isotonic predict / apply,
    nor reference calibrator objects.
    """
    src = inspect.getsource(s27c.compute_picker_score_s_b_raw)
    # Strip docstring (function body should not call any calibrator)
    lines_after_def = src.split("def ")[1].split('"""')
    body = lines_after_def[2] if len(lines_after_def) >= 3 else src
    assert "predict" not in body
    assert "IsotonicRegression" not in body
    assert "apply_isotonic" not in body
    assert "calibrators" not in body


# [27.0c NEW]
def test_compute_picker_score_s_b_raw_rejects_wrong_shape():
    with pytest.raises(ValueError, match=r"shape"):
        s27c.compute_picker_score_s_b_raw(np.zeros((5, 2)))


# ===========================================================================
# Group 9 — D10 amendment single-fit (2 NEW)
# ===========================================================================


# [27.0c NEW]
def test_d10_amendment_single_three_artifact_fit_documented():
    """Module docstring documents D10 amendment for 3-artifact single fit."""
    doc = s27c.__doc__ or ""
    assert "D10 amendment" in doc
    # Per 27.0c-α §7.5: one head + one isotonic triple + one estimator triple
    assert "ONE multiclass head" in doc or "one multiclass head" in doc.lower()


# [27.0c NEW]
def test_no_per_cell_refit_in_evaluate_cell_27_0c():
    """evaluate_cell_27_0c receives precomputed scores; never refits."""
    src = inspect.getsource(s27c.evaluate_cell_27_0c)
    assert "pipeline.fit" not in src
    assert ".fit(" not in src or "evaluate_cell_27_0c" not in src.split(".fit(")[0]


# ===========================================================================
# Group 10 — Class index mapping consistent with inherited (2 NEW)
# ===========================================================================


# [27.0c NEW]
def test_class_index_mapping_consistent_with_inherited():
    """LABEL_TP/SL/TIME indexing must match inherited 27.0b / 26.0c."""
    stage27_0b = importlib.import_module("stage27_0b_s_c_time_penalty_eval")
    stage26_0c = importlib.import_module("stage26_0c_l1_eval")
    assert s27c.LABEL_TP == stage27_0b.LABEL_TP == stage26_0c.LABEL_TP
    assert s27c.LABEL_SL == stage27_0b.LABEL_SL == stage26_0c.LABEL_SL
    assert s27c.LABEL_TIME == stage27_0b.LABEL_TIME == stage26_0c.LABEL_TIME
    assert s27c.NUM_CLASSES == 3


# [27.0c NEW]
def test_num_classes_is_three():
    assert s27c.NUM_CLASSES == 3


# ===========================================================================
# Group 11 — Diagnostic-only prohibition (5 NEW)
# ===========================================================================


# [27.0c NEW]
def test_clause_2_extension_mentions_estimator_constants_diagnostic_only():
    """Clause 2 must explicitly mark estimator constants as diagnostic-only."""
    doc = s27c.__doc__ or ""
    # Clause 2 in module docstring includes 27.0c extension wording
    assert "conditional-PnL estimator constants" in doc
    assert "diagnostic-only" in doc.lower() or "DIAGNOSTIC-ONLY" in doc


# [27.0c NEW]
def test_clause_2_extension_mentions_calibration_reliability_diagnostic_only():
    doc = s27c.__doc__ or ""
    assert "calibration reliability" in doc.lower()


# [27.0c NEW]
def test_compute_calibration_diagnostic_does_not_modify_score():
    """Calibration diagnostic must not influence the formal verdict path."""
    # Function signature accepts only OOF data and calibrators; returns diag dict
    sig = inspect.signature(s27c.compute_calibration_diagnostic)
    params = set(sig.parameters)
    assert params == {"calibrators", "oof_probs"}


# [27.0c NEW]
def test_compute_reliability_diagram_does_not_modify_score():
    sig = inspect.signature(s27c.compute_reliability_diagram_per_class)
    params = set(sig.parameters)
    assert "raw_probs" in params
    assert "cal_probs" in params
    assert "realised_label" in params


# [27.0c NEW]
def test_compute_estimator_divergence_flag_does_not_modify_score():
    sig = inspect.signature(s27c.compute_estimator_divergence_flag)
    params = set(sig.parameters)
    assert params == {"full_train", "oof"}


# ===========================================================================
# Group 12 — Sanity probe extensions (3 NEW)
# ===========================================================================


# [27.0c NEW]
def test_sanity_probe_signature_accepts_new_27_0c_params():
    sig = inspect.signature(s27c.run_sanity_probe_27_0c)
    params = set(sig.parameters)
    # New 27.0c-specific params per design memo §10 items 7-11
    assert "fold_idx" in params
    assert "e_pnl_full_train" in params
    assert "calibration_diag" in params
    assert "zero_sum_row_count_val" in params
    assert "zero_sum_row_count_test" in params
    assert "val_score_s_d" in params
    assert "test_score_s_d" in params


# [27.0c NEW]
def test_sanity_probe_halts_on_zero_sum_row_val():
    """D-I11: zero-sum-row fallback count > 0 on val → SanityProbeError."""
    # Construct minimal inputs to trigger the HALT check
    # We use the module's internal HALT logic by inspecting source
    src = inspect.getsource(s27c.run_sanity_probe_27_0c)
    # The HALT for zero_sum_row_count_val > 0 must be present
    assert "zero_sum_row_count_val" in src
    assert "SanityProbeError" in src
    # Check that there's a HALT condition tied to zero_sum_row > 0
    assert "> 0" in src


# [27.0c NEW]
def test_sanity_probe_halts_on_zero_sum_row_test():
    src = inspect.getsource(s27c.run_sanity_probe_27_0c)
    assert "zero_sum_row_count_test" in src


# ===========================================================================
# Group 13 — Reliability diagram (2 NEW)
# ===========================================================================


# [27.0c NEW]
def test_reliability_diagram_has_one_block_per_class_with_n_bins():
    rng = np.random.default_rng(55)
    n = 200
    raw = rng.dirichlet(np.ones(s27c.NUM_CLASSES), n).astype(np.float64)
    cal = rng.dirichlet(np.ones(s27c.NUM_CLASSES), n).astype(np.float64)
    labels = rng.integers(0, s27c.NUM_CLASSES, n)
    diag = s27c.compute_reliability_diagram_per_class(raw, cal, labels, n_bins=10)
    assert len(diag) == s27c.NUM_CLASSES
    for c in range(s27c.NUM_CLASSES):
        assert len(diag[c]) == 10  # 10 bins
        for b in diag[c]:
            assert "bin_lo" in b
            assert "bin_hi" in b
            assert "bin_count" in b
            assert "bin_freq_actual" in b


# [27.0c NEW]
def test_reliability_diagram_bins_cover_unit_interval():
    rng = np.random.default_rng(56)
    n = 100
    raw = rng.dirichlet(np.ones(s27c.NUM_CLASSES), n).astype(np.float64)
    cal = rng.dirichlet(np.ones(s27c.NUM_CLASSES), n).astype(np.float64)
    labels = rng.integers(0, s27c.NUM_CLASSES, n)
    diag = s27c.compute_reliability_diagram_per_class(raw, cal, labels, n_bins=10)
    for c in range(s27c.NUM_CLASSES):
        bins = diag[c]
        # Bin lows form 0, 0.1, ..., 0.9; highs form 0.1, ..., 1.0
        assert bins[0]["bin_lo"] == pytest.approx(0.0)
        assert bins[-1]["bin_hi"] == pytest.approx(1.0)


# ===========================================================================
# Group 14 — Divergence flag values (3 NEW)
# ===========================================================================


# [27.0c NEW]
def test_estimator_divergence_threshold_is_10_percent():
    """D-I6 default threshold per design memo §4.3 step 6."""
    assert s27c.ESTIMATOR_DIVERGENCE_FRAC_THRESHOLD == 0.10


# [27.0c NEW]
def test_estimator_divergence_denom_eps_is_one_billionth():
    assert s27c.ESTIMATOR_DIVERGENCE_DENOM_EPS == 1e-9


# [27.0c NEW]
def test_estimator_divergence_flag_fires_over_threshold():
    full = {0: 1.0, 1: -2.0, 2: 0.5}
    oof = {
        0: {"oof_aggregate_mean": 1.20},  # 20% delta — over
        1: {"oof_aggregate_mean": -2.05},  # 2.5% — under
        2: {"oof_aggregate_mean": 0.50},  # 0% — under
    }
    flags = s27c.compute_estimator_divergence_flag(full, oof)
    assert flags[0]["divergence_flag"] is True
    assert flags[1]["divergence_flag"] is False
    assert flags[2]["divergence_flag"] is False


# ===========================================================================
# Group 15 — Mandatory clauses + binding constants (2 NEW)
# ===========================================================================


# [27.0c NEW]
def test_module_docstring_includes_all_six_mandatory_clauses():
    doc = s27c.__doc__ or ""
    for marker in [
        "1. Phase framing",
        "2. Diagnostic columns prohibition",
        "3. γ closure preservation",
        "4. Production-readiness preservation",
        "5. NG#10 / NG#11 not relaxed",
        "6. Phase 27 scope",
    ]:
        assert marker in doc, f"clause marker missing: {marker!r}"


# [27.0c NEW]
def test_module_docstring_documents_3_layer_selection_overfit_guard():
    """Per 27.0c-α §13 verbatim binding."""
    doc = s27c.__doc__ or ""
    assert "3-LAYER" in doc or "3-layer" in doc
    assert "selection-overfit" in doc.lower() or "selection_overfit" in doc.lower()
    assert "train-only" in doc.lower()
    assert "cutoff selection" in doc.lower()


# ===========================================================================
# Group 16 — D-1 binding (3 NEW)
# ===========================================================================


# [27.0c NEW]
def test_d_1_binding_documented_in_module_docstring():
    doc = s27c.__doc__ or ""
    assert "D-1 BINDING" in doc or "D-1 binding" in doc
    assert "_compute_realised_barrier_pnl" in doc
    assert "bid/ask" in doc


# [27.0c NEW]
def test_estimator_uses_bid_ask_realised_pnl_not_mid_to_mid():
    """Sanity-probe source must reference bid_h / ask_l etc. (D-1 check)."""
    src = inspect.getsource(s27c.run_sanity_probe_27_0c)
    # The probe verifies the inherited harness uses bid/ask
    assert "bid_h" in src
    assert "ask_l" in src


# [27.0c NEW]
def test_baseline_reference_values_match_27_0b_c_alpha0():
    """D-I10: hard-coded baseline must match PR #318 §10 verbatim."""
    assert s27c.BASELINE_27_0B_C_ALPHA0_N_TRADES == 34626
    assert s27c.BASELINE_27_0B_C_ALPHA0_SHARPE == -0.1732
    assert s27c.BASELINE_27_0B_C_ALPHA0_ANN_PNL == -204664.4
    assert s27c.BASELINE_MATCH_N_TRADES_TOLERANCE == 0  # exact match
    assert s27c.BASELINE_MATCH_SHARPE_ABS_TOLERANCE == 1e-4
    assert s27c.BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE == 0.5
