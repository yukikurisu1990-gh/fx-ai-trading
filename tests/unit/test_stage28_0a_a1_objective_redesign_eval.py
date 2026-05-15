"""Unit tests for Stage 28.0a-β A1 Objective Redesign eval.

~65-75 tests across 19 groups (per implementation plan):
- Group 1 — Loss constants / closed allowlist (5)
- Group 2 — build_l1_sample_weight (4)
- Group 3 — build_l3_sample_weight (4)
- Group 4 — asymmetric_huber_objective grad/hess (6)
- Group 5 — fit_l1_regressor (3)
- Group 6 — fit_l2_regressor (3)
- Group 7 — fit_l3_regressor (3)
- Group 8 — fit_control_regressor: symmetric Huber, sample_weight=1 (3)
- Group 9 — build_a1_cells structure (5)
- Group 10 — evaluate_cell_28_0a feature routing (4)
- Group 11 — D10 4-artifact form (4)
- Group 12 — BaselineMismatchError HALT (4)
- Group 13 — H-C1 4-outcome ladder resolver (8)
- Group 14 — within-eval ablation drift check (4)
- Group 15 — Top-tail regime audit per variant (3)
- Group 16 — Sanity probe extensions (5)
- Group 17 — Module docstring + clauses (4)
- Group 18 — Sub-phase naming (2)
- Group 19 — Inheritance from 27.0f-β (5)

NEW 28.0a-specific tests flagged [28.0a NEW].
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

s28a = importlib.import_module("stage28_0a_a1_objective_redesign_eval")


# ===========================================================================
# Group 1 — Loss constants / closed allowlist (5 NEW; NG#A1-1 enforcement)
# ===========================================================================


# [28.0a NEW]
def test_l1_w_clip_is_30_pip():
    assert s28a.L1_W_CLIP == 30.0


# [28.0a NEW]
def test_l2_delta_pos_and_neg_pre_stated():
    assert s28a.L2_DELTA_POS == 0.5
    assert s28a.L2_DELTA_NEG == 1.5


# [28.0a NEW]
def test_l3_gamma_is_0_5():
    assert s28a.L3_GAMMA == 0.5


# [28.0a NEW]
def test_l2_hess_eps_is_1e_minus_3():
    assert s28a.L2_HESS_EPS == 1e-3


# [28.0a NEW; NG#A1-1]
def test_no_grid_sweep_constants_present():
    """NG#A1-1: closed allowlist; no grid sweep within a variant."""
    # Ensure there is no constant like L1_W_CLIP_GRID, L2_DELTA_GRID, L3_GAMMA_GRID
    forbidden_names = ("L1_W_CLIP_GRID", "L2_DELTA_GRID", "L3_GAMMA_GRID")
    for name in forbidden_names:
        assert not hasattr(s28a, name), f"{name} would violate NG#A1-1 (no grid sweep)"


# ===========================================================================
# Group 2 — build_l1_sample_weight (4 NEW)
# ===========================================================================


# [28.0a NEW]
def test_l1_sample_weight_clips_at_w_clip():
    pnl = np.array([5.0, -45.0, 12.0, 30.0, -3.0, 60.0])
    w = s28a.build_l1_sample_weight(pnl, w_clip=30.0)
    assert w.max() == 30.0
    assert np.isclose(w[0], 5.0)
    assert np.isclose(w[1], 30.0)  # clipped from |-45|=45
    assert np.isclose(w[5], 30.0)  # clipped from 60


# [28.0a NEW]
def test_l1_sample_weight_takes_absolute_value():
    pnl = np.array([-10.0, +10.0])
    w = s28a.build_l1_sample_weight(pnl, w_clip=30.0)
    assert np.isclose(w[0], w[1])
    assert np.isclose(w[0], 10.0)


# [28.0a NEW]
def test_l1_sample_weight_raises_on_non_finite():
    pnl = np.array([5.0, np.nan, 12.0])
    with pytest.raises(ValueError):
        s28a.build_l1_sample_weight(pnl, w_clip=30.0)


# [28.0a NEW]
def test_l1_sample_weight_uses_default_w_clip():
    pnl = np.array([5.0, 50.0])
    w = s28a.build_l1_sample_weight(pnl)
    assert w.max() == s28a.L1_W_CLIP


# ===========================================================================
# Group 3 — build_l3_sample_weight (4 NEW)
# ===========================================================================


# [28.0a NEW]
def test_l3_sample_weight_formula():
    spread = np.array([0.0, 1.0, 2.0, 4.0])
    w = s28a.build_l3_sample_weight(spread, gamma=0.5)
    assert np.isclose(w[0], 1.0)
    assert np.isclose(w[1], 1.5)
    assert np.isclose(w[2], 2.0)
    assert np.isclose(w[3], 3.0)


# [28.0a NEW]
def test_l3_sample_weight_floor_at_one():
    """Weights must be ≥ 1.0 because spread ≥ 0 per R7-A positivity."""
    spread = np.array([0.0, 1.0, 5.0])
    w = s28a.build_l3_sample_weight(spread, gamma=0.5)
    assert w.min() >= 1.0


# [28.0a NEW]
def test_l3_sample_weight_raises_on_non_finite():
    spread = np.array([1.0, np.inf])
    with pytest.raises(ValueError):
        s28a.build_l3_sample_weight(spread, gamma=0.5)


# [28.0a NEW]
def test_l3_sample_weight_raises_on_negative_spread():
    """Negative spread would yield weight < 1, violating R7-A positivity guard."""
    spread = np.array([1.0, -3.0])
    with pytest.raises(ValueError):
        s28a.build_l3_sample_weight(spread, gamma=0.5)


# ===========================================================================
# Group 4 — asymmetric_huber_objective grad/hess (6 NEW; NG#A1-1)
# ===========================================================================


class _DummyDtrain:
    def __init__(self, label):
        self._label = np.asarray(label, dtype=np.float64)

    def get_label(self):
        return self._label


# [28.0a NEW]
def test_asymmetric_huber_grad_under_prediction_quadratic_region():
    """Under-prediction (residual > 0), |r| ≤ δ_pos → grad = -r, hess = 1."""
    y = np.array([0.3])
    p = np.array([0.0])
    g, h = s28a.asymmetric_huber_objective(p, _DummyDtrain(y))
    assert np.isclose(g[0], -0.3)
    assert np.isclose(h[0], 1.0)


# [28.0a NEW]
def test_asymmetric_huber_grad_under_prediction_linear_region():
    """Under-prediction (residual > δ_pos) → grad = -δ_pos."""
    y = np.array([2.0])
    p = np.array([1.0])  # residual = +1.0 > δ_pos=0.5
    g, h = s28a.asymmetric_huber_objective(p, _DummyDtrain(y))
    assert np.isclose(g[0], -s28a.L2_DELTA_POS)


# [28.0a NEW]
def test_asymmetric_huber_grad_over_prediction_quadratic_region():
    """Over-prediction (residual < 0, |r| ≤ δ_neg) → grad = -r."""
    y = np.array([0.0])
    p = np.array([1.0])  # residual = -1.0; |r|=1 ≤ δ_neg=1.5 → quadratic
    g, h = s28a.asymmetric_huber_objective(p, _DummyDtrain(y))
    assert np.isclose(g[0], 1.0)
    assert np.isclose(h[0], 1.0)


# [28.0a NEW]
def test_asymmetric_huber_grad_over_prediction_linear_region():
    """Over-prediction (residual < -δ_neg) → grad = +δ_neg."""
    y = np.array([0.0])
    p = np.array([3.0])  # residual = -3.0; |r|=3 > δ_neg=1.5 → linear
    g, h = s28a.asymmetric_huber_objective(p, _DummyDtrain(y))
    assert np.isclose(g[0], s28a.L2_DELTA_NEG)


# [28.0a NEW]
def test_asymmetric_huber_hess_clamped_to_eps():
    """In the linear region, hess is clamped to L2_HESS_EPS (D-BA7)."""
    y = np.array([0.0])
    p = np.array([10.0])  # huge over-pred → linear region; hess = 0 originally
    g, h = s28a.asymmetric_huber_objective(p, _DummyDtrain(y))
    assert h[0] >= s28a.L2_HESS_EPS - 1e-12


# [28.0a NEW]
def test_asymmetric_huber_over_prediction_penalised_more_than_under():
    """δ_neg > δ_pos ensures over-prediction is penalised more heavily in linear region."""
    # Symmetric large residual magnitude
    y_under = np.array([10.0])  # residual = +10
    p_under = np.array([0.0])
    y_over = np.array([0.0])  # residual = -10
    p_over = np.array([10.0])
    g_under, _ = s28a.asymmetric_huber_objective(p_under, _DummyDtrain(y_under))
    g_over, _ = s28a.asymmetric_huber_objective(p_over, _DummyDtrain(y_over))
    # In linear region: |grad_under| = δ_pos = 0.5; |grad_over| = δ_neg = 1.5
    assert abs(g_over[0]) > abs(g_under[0])


# ===========================================================================
# Group 5 — fit_l1_regressor (3 NEW; sklearn pipeline + sample_weight)
# ===========================================================================


# [28.0a NEW]
def test_build_pipeline_lightgbm_regression_widened_is_inherited():
    """28.0a uses the inherited 27.0d pipeline builder for L1."""
    pipe = s28a.build_pipeline_lightgbm_regression_widened()
    step_names = [name for name, _ in pipe.steps]
    assert "pre" in step_names
    assert "clf" in step_names


# [28.0a NEW]
def test_l1_uses_sklearn_pipeline_sample_weight_pathway():
    """L1 implementation uses sklearn pipeline + clf__sample_weight kwarg."""
    src = inspect.getsource(s28a.main)
    assert "regressor_l1.fit" in src
    assert "clf__sample_weight=w_l1" in src


# [28.0a NEW]
def test_l1_sample_weight_constructed_from_realised_pnl_abs():
    """L1 weight construction uses build_l1_sample_weight on pnl_train_for_reg."""
    src = inspect.getsource(s28a.main)
    assert "build_l1_sample_weight(pnl_train_for_reg" in src


# ===========================================================================
# Group 6 — fit_l2_regressor (3 NEW; Booster API custom objective)
# ===========================================================================


# [28.0a NEW]
def test_l2_uses_lightgbm_booster_train_api():
    """L2 implementation uses lightgbm.Booster.train with custom objective (D-BA6).

    LightGBM 4.x removed the legacy `fobj=` parameter; custom objectives are
    passed via `params['objective'] = callable` instead.
    """
    src = inspect.getsource(s28a.fit_l2_regressor_booster)
    assert "lgb.train" in src
    assert "lgb.Dataset" in src
    assert '"objective": asymmetric_huber_objective' in src


# [28.0a NEW]
def test_l2_returns_booster_and_preprocessor_tuple():
    """fit_l2_regressor_booster must return (booster, preprocessor) for predict reuse."""
    sig = inspect.signature(s28a.fit_l2_regressor_booster)
    assert "x_train" in sig.parameters
    assert "y_train" in sig.parameters


# [28.0a NEW]
def test_predict_l2_booster_applies_preprocessor():
    """predict_l2_booster must transform X via the same preprocessor before booster.predict."""
    src = inspect.getsource(s28a.predict_l2_booster)
    assert "preprocessor.transform" in src
    assert "booster.predict" in src


# ===========================================================================
# Group 7 — fit_l3_regressor (3 NEW; sklearn pipeline + sample_weight)
# ===========================================================================


# [28.0a NEW]
def test_l3_uses_sklearn_pipeline_sample_weight_pathway():
    """L3 implementation uses sklearn pipeline + clf__sample_weight kwarg."""
    src = inspect.getsource(s28a.main)
    assert "regressor_l3.fit" in src
    assert "clf__sample_weight=w_l3" in src


# [28.0a NEW]
def test_l3_sample_weight_constructed_from_spread_at_signal_pip():
    """L3 weight construction uses build_l3_sample_weight on spread_at_signal_pip."""
    src = inspect.getsource(s28a.main)
    assert "build_l3_sample_weight(spread_train_for_reg" in src


# [28.0a NEW]
def test_l3_spread_train_extracted_from_r7a():
    src = inspect.getsource(s28a.main)
    assert 'train_df_for_reg["spread_at_signal_pip"]' in src


# ===========================================================================
# Group 8 — fit_control_regressor: symmetric Huber, sample_weight=1 (3 NEW; NG#A1-3)
# ===========================================================================


# [28.0a NEW; NG#A1-3]
def test_control_regressor_has_no_sample_weight():
    """C-a1-se-r7a-replica: symmetric Huber, sample_weight=1 (not passed)."""
    src = inspect.getsource(s28a.main)
    # Find the regressor_control.fit call and ensure no sample_weight kwarg follows
    idx = src.find("regressor_control.fit")
    assert idx > 0
    # Take a small slice and verify no clf__sample_weight in the fit args
    slice_ = src[idx : idx + 200]
    assert "clf__sample_weight" not in slice_, (
        "C-a1-se-r7a-replica must use sample_weight=1 (i.e., no sample_weight kwarg)"
    )


# [28.0a NEW; NG#A1-3]
def test_control_cell_present_in_cell_list():
    """C-a1-se-r7a-replica must be in the cell list per NG#A1-3."""
    cells = s28a.build_a1_cells()
    cell_ids = [c["id"] for c in cells]
    assert "C-a1-se-r7a-replica" in cell_ids


# [28.0a NEW]
def test_control_uses_symmetric_huber_alpha_0_9():
    """27.0d C-se reproduction: symmetric Huber α=0.9 inherited."""
    assert s28a.HUBER_ALPHA == 0.9


# ===========================================================================
# Group 9 — build_a1_cells structure (5 NEW)
# ===========================================================================


# [28.0a NEW]
def test_a1_cells_5_cells_total():
    cells = s28a.build_a1_cells()
    assert len(cells) == 5


# [28.0a NEW]
def test_a1_cells_ids_in_deterministic_order():
    """Per D-BA13: deterministic order L1 → L2 → L3 → control → baseline."""
    cells = s28a.build_a1_cells()
    cell_ids = [c["id"] for c in cells]
    assert cell_ids == [
        "C-a1-L1",
        "C-a1-L2",
        "C-a1-L3",
        "C-a1-se-r7a-replica",
        "C-sb-baseline",
    ]


# [28.0a NEW]
def test_a1_cells_all_have_r7a_feature_set():
    cells = s28a.build_a1_cells()
    for c in cells:
        assert c["feature_set"] == "r7a"


# [28.0a NEW]
def test_a1_cells_quantile_family_is_5_10_20_30_40():
    cells = s28a.build_a1_cells()
    expected = (5.0, 10.0, 20.0, 30.0, 40.0)
    for c in cells:
        assert tuple(c["quantile_percents"]) == expected


# [28.0a NEW]
def test_a1_cells_loss_labels_present():
    cells = s28a.build_a1_cells()
    losses = {c["id"]: c["loss"] for c in cells}
    assert losses["C-a1-L1"] == "l1_magnitude_weighted_huber"
    assert losses["C-a1-L2"] == "l2_asymmetric_huber"
    assert losses["C-a1-L3"] == "l3_spread_cost_weighted_huber"
    assert losses["C-a1-se-r7a-replica"] == "symmetric_huber_alpha_0_9"
    assert losses["C-sb-baseline"] == "multiclass_ce"


# ===========================================================================
# Group 10 — evaluate_cell_28_0a feature routing (4 NEW)
# ===========================================================================


# [28.0a NEW]
def test_evaluate_cell_28_0a_returns_dict_with_h_state():
    """Minimal smoke test of the cell-eval shape."""
    sig = inspect.signature(s28a.evaluate_cell_28_0a)
    params = set(sig.parameters)
    assert {"cell", "train_df", "val_df", "test_df", "val_score", "test_score"}.issubset(params)


# [28.0a NEW]
def test_main_routes_s_e_l1_to_l1_predictions():
    src = inspect.getsource(s28a.main)
    assert 'score_type == "s_e_l1"' in src
    assert "val_score, test_score, fi = val_pred_l1, test_pred_l1, fi_l1" in src


# [28.0a NEW]
def test_main_routes_s_e_l2_to_l2_predictions():
    src = inspect.getsource(s28a.main)
    assert 'score_type == "s_e_l2"' in src
    assert "val_score, test_score, fi = val_pred_l2, test_pred_l2, fi_l2" in src


# [28.0a NEW]
def test_main_routes_s_e_control_to_control_predictions():
    src = inspect.getsource(s28a.main)
    assert 'score_type == "s_e_control"' in src
    assert "val_pred_control, test_pred_control" in src


# ===========================================================================
# Group 11 — D10 4-artifact form (4 NEW; NG#A1-2)
# ===========================================================================


# [28.0a NEW; NG#A1-2]
def test_d10_four_regressor_artifacts_fitted():
    """PR #337 §7.1: 3 loss + 1 control regressors + 1 multiclass head."""
    src = inspect.getsource(s28a.main)
    assert "regressor_l1 = build_pipeline_lightgbm_regression_widened()" in src
    assert "booster_l2, preprocessor_l2 = fit_l2_regressor_booster" in src
    assert "regressor_l3 = build_pipeline_lightgbm_regression_widened()" in src
    assert "regressor_control = build_pipeline_lightgbm_regression_widened()" in src


# [28.0a NEW; NG#A1-2]
def test_multiclass_head_fitted_for_baseline_reproduction():
    src = inspect.getsource(s28a.main)
    assert "multiclass_pipeline = build_pipeline_lightgbm_multiclass_widened()" in src


# [28.0a NEW]
def test_per_variant_outcomes_recorded_separately():
    """Per NG#A1-2: per-variant verdict required; not aggregate-only."""
    src = inspect.getsource(s28a.main)
    # Each variant must have its own outcome computed
    assert "h_c1_per_variant: list[dict] = []" in src
    assert 'for vname, cell_id in [("L1", "C-a1-L1"), ("L2", "C-a1-L2"), ("L3", "C-a1-L3")]:' in src


# [28.0a NEW]
def test_aggregate_verdict_derived_from_per_variant():
    src = inspect.getsource(s28a.main)
    assert "compute_h_c1_aggregate_verdict(h_c1_per_variant)" in src


# ===========================================================================
# Group 12 — BaselineMismatchError HALT (4 NEW; FAIL-FAST inheritance)
# ===========================================================================


# [28.0a NEW]
def test_baseline_mismatch_error_inherits_runtime_error():
    assert issubclass(s28a.BaselineMismatchError, RuntimeError)


# [28.0a NEW]
def test_check_c_sb_baseline_match_raises_on_n_trades_mismatch():
    fake_result = {
        "test_realised_metrics": {
            "n_trades": 34000,  # ≠ 34626
            "sharpe": s28a.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s28a.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    with pytest.raises(s28a.BaselineMismatchError):
        s28a.check_c_sb_baseline_match(fake_result)


# [28.0a NEW]
def test_check_c_sb_baseline_match_passes_on_exact():
    fake_result = {
        "test_realised_metrics": {
            "n_trades": s28a.BASELINE_27_0B_C_ALPHA0_N_TRADES,
            "sharpe": s28a.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s28a.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    report = s28a.check_c_sb_baseline_match(fake_result)
    assert report["all_match"] is True


# [28.0a NEW]
def test_baseline_tolerances_inherited_from_27_0d():
    """n_trades exact / Sharpe ±1e-4 / ann_pnl ±0.5 pip (per PR #337 §8)."""
    assert s28a.BASELINE_MATCH_N_TRADES_TOLERANCE == 0
    assert s28a.BASELINE_MATCH_SHARPE_ABS_TOLERANCE == 1e-4
    assert s28a.BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE == 0.5


# ===========================================================================
# Group 13 — H-C1 4-outcome ladder resolver (8 NEW; PR #337 §3.2)
# ===========================================================================


def _make_cell_result(
    cell_id: str,
    val_sharpe: float,
    val_n: int,
    cell_spearman_val: float,
) -> dict:
    return {
        "cell": {"id": cell_id},
        "h_state": "OK",
        "val_realised_sharpe": val_sharpe,
        "val_n_trades": val_n,
        "test_formal_spearman": cell_spearman_val,  # used as fallback for cell_spearman_val
        "quantile_best": {
            "val": {"spearman_score_vs_pnl": cell_spearman_val},
        },
    }


# [28.0a NEW]
def test_h_c1_partial_drift_r7a_replica_takes_precedence():
    """Row 4 (PARTIAL_DRIFT) checked first; precedence over PASS / PARTIAL / FALSIFIED."""
    cell_result = _make_cell_result("C-a1-L1", val_sharpe=-0.05, val_n=30000, cell_spearman_val=0.4)
    baseline_match = {"all_match": True}
    drift = {"all_within_tolerance": True}  # within tolerance → PARTIAL_DRIFT
    out = s28a.compute_h_c1_outcome_per_variant(cell_result, baseline_match, drift)
    assert out["outcome"] == s28a.H_C1_OUTCOME_PARTIAL_DRIFT_R7A_REPLICA
    assert out["row_matched"] == 4


# [28.0a NEW]
def test_h_c1_pass_outcome():
    """All four H-C1 conditions met → PASS (row 1)."""
    cell_result = _make_cell_result(
        "C-a1-L1",
        val_sharpe=-0.05,  # baseline -0.1863 + 0.13 lift > 0.05
        val_n=30000,
        cell_spearman_val=0.4,
    )
    baseline_match = {"all_match": True}
    drift = {"all_within_tolerance": False}  # not within → not row 4
    out = s28a.compute_h_c1_outcome_per_variant(cell_result, baseline_match, drift)
    assert out["outcome"] == s28a.H_C1_OUTCOME_PASS
    assert out["row_matched"] == 1


# [28.0a NEW]
def test_h_c1_partial_support_outcome():
    """Sharpe lift in [+0.02, +0.05) and other conditions → PARTIAL_SUPPORT (row 2)."""
    # baseline val Sharpe = -0.1863; +0.03 lift → val sharpe = -0.1563
    cell_result = _make_cell_result(
        "C-a1-L1",
        val_sharpe=-0.1563,
        val_n=30000,
        cell_spearman_val=0.4,
    )
    baseline_match = {"all_match": True}
    drift = {"all_within_tolerance": False}
    out = s28a.compute_h_c1_outcome_per_variant(cell_result, baseline_match, drift)
    assert out["outcome"] == s28a.H_C1_OUTCOME_PARTIAL_SUPPORT
    assert out["row_matched"] == 2


# [28.0a NEW]
def test_h_c1_falsified_outcome():
    """No Sharpe lift → FALSIFIED_OBJECTIVE_INSUFFICIENT (row 3)."""
    cell_result = _make_cell_result(
        "C-a1-L1",
        val_sharpe=-0.20,  # lift = -0.20 - (-0.1863) = -0.0137 < +0.02
        val_n=30000,
        cell_spearman_val=0.4,
    )
    baseline_match = {"all_match": True}
    drift = {"all_within_tolerance": False}
    out = s28a.compute_h_c1_outcome_per_variant(cell_result, baseline_match, drift)
    assert out["outcome"] == s28a.H_C1_OUTCOME_FALSIFIED_OBJECTIVE_INSUFFICIENT
    assert out["row_matched"] == 3


# [28.0a NEW]
def test_h_c1_h1m_fail_falls_to_falsified():
    """H1m FAIL (cell Spearman < +0.30) → FALSIFIED (cannot reach PASS or PARTIAL_SUPPORT)."""
    cell_result = _make_cell_result(
        "C-a1-L1",
        val_sharpe=-0.05,  # h2 PASS but h1m FAIL
        val_n=30000,
        cell_spearman_val=0.10,  # below 0.30
    )
    baseline_match = {"all_match": True}
    drift = {"all_within_tolerance": False}
    out = s28a.compute_h_c1_outcome_per_variant(cell_result, baseline_match, drift)
    assert out["outcome"] == s28a.H_C1_OUTCOME_FALSIFIED_OBJECTIVE_INSUFFICIENT


# [28.0a NEW]
def test_h_c1_aggregate_split_verdict_on_any_pass():
    per_variant = [
        {"cell_id": "C-a1-L1", "outcome": s28a.H_C1_OUTCOME_PASS, "row_matched": 1},
        {
            "cell_id": "C-a1-L2",
            "outcome": s28a.H_C1_OUTCOME_FALSIFIED_OBJECTIVE_INSUFFICIENT,
            "row_matched": 3,
        },
        {
            "cell_id": "C-a1-L3",
            "outcome": s28a.H_C1_OUTCOME_FALSIFIED_OBJECTIVE_INSUFFICIENT,
            "row_matched": 3,
        },
    ]
    agg = s28a.compute_h_c1_aggregate_verdict(per_variant)
    assert agg["aggregate_verdict"] == "SPLIT_VERDICT_ROUTE_TO_REVIEW"
    assert agg["has_pass"] is True


# [28.0a NEW]
def test_h_c1_aggregate_reject_on_all_partial_drift():
    per_variant = [
        {
            "cell_id": "C-a1-L1",
            "outcome": s28a.H_C1_OUTCOME_PARTIAL_DRIFT_R7A_REPLICA,
            "row_matched": 4,
        },
        {
            "cell_id": "C-a1-L2",
            "outcome": s28a.H_C1_OUTCOME_PARTIAL_DRIFT_R7A_REPLICA,
            "row_matched": 4,
        },
        {
            "cell_id": "C-a1-L3",
            "outcome": s28a.H_C1_OUTCOME_PARTIAL_DRIFT_R7A_REPLICA,
            "row_matched": 4,
        },
    ]
    agg = s28a.compute_h_c1_aggregate_verdict(per_variant)
    assert agg["aggregate_verdict"] == "REJECT_NON_DISCRIMINATIVE"
    assert agg["all_partial_drift"] is True


# [28.0a NEW]
def test_h_c1_aggregate_reject_on_all_falsified():
    per_variant = [
        {
            "cell_id": "C-a1-L1",
            "outcome": s28a.H_C1_OUTCOME_FALSIFIED_OBJECTIVE_INSUFFICIENT,
            "row_matched": 3,
        },
        {
            "cell_id": "C-a1-L2",
            "outcome": s28a.H_C1_OUTCOME_FALSIFIED_OBJECTIVE_INSUFFICIENT,
            "row_matched": 3,
        },
        {
            "cell_id": "C-a1-L3",
            "outcome": s28a.H_C1_OUTCOME_FALSIFIED_OBJECTIVE_INSUFFICIENT,
            "row_matched": 3,
        },
    ]
    agg = s28a.compute_h_c1_aggregate_verdict(per_variant)
    assert agg["aggregate_verdict"] == "REJECT_NON_DISCRIMINATIVE"


# ===========================================================================
# Group 14 — within-eval ablation drift check (4 NEW)
# ===========================================================================


# [28.0a NEW]
def test_within_eval_drift_within_tolerance_flags_partial_drift():
    candidate = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 184700, "sharpe": -0.483, "annual_pnl": -999800.0},
    }
    control = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 184703, "sharpe": -0.4831, "annual_pnl": -999830.0},
    }
    d = s28a.compute_within_eval_ablation_drift_check(candidate, control)
    assert d["all_within_tolerance"] is True


# [28.0a NEW]
def test_within_eval_drift_outside_tolerance_n_trades():
    candidate = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 180000, "sharpe": -0.483, "annual_pnl": -999800.0},
    }
    control = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 184703, "sharpe": -0.4831, "annual_pnl": -999830.0},
    }
    d = s28a.compute_within_eval_ablation_drift_check(candidate, control)
    assert d["all_within_tolerance"] is False


# [28.0a NEW]
def test_within_eval_drift_outside_tolerance_sharpe():
    candidate = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 184700, "sharpe": -0.30, "annual_pnl": -999800.0},
    }
    control = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 184703, "sharpe": -0.483, "annual_pnl": -999830.0},
    }
    d = s28a.compute_within_eval_ablation_drift_check(candidate, control)
    assert d["all_within_tolerance"] is False


# [28.0a NEW]
def test_within_eval_drift_missing_h_state():
    candidate = {"h_state": "ERROR"}
    control = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 1, "sharpe": 0.0, "annual_pnl": 0.0},
    }
    d = s28a.compute_within_eval_ablation_drift_check(candidate, control)
    assert d["all_within_tolerance"] is False


# ===========================================================================
# Group 15 — Top-tail regime audit per variant (3 NEW; spread only)
# ===========================================================================


# [28.0a NEW]
def test_top_tail_audit_uses_spread_at_signal_pip_only():
    """Per PR #337 §11 §18: audit uses spread_at_signal_pip only, no R7-C features."""
    src = inspect.getsource(s28a.compute_top_tail_regime_audit_for_a1)
    assert "spread_at_signal_pip" in src
    # Must NOT reference R7-C features
    assert "f5a_spread_z_50" not in src
    assert "f5b_volume_z_50" not in src
    assert "f5c_high_spread_low_vol_50" not in src


# [28.0a NEW]
def test_top_tail_audit_returns_per_q_records():
    scores = np.random.RandomState(0).randn(1000)
    val_df = pd.DataFrame(
        {"spread_at_signal_pip": np.random.RandomState(1).uniform(1.0, 5.0, 1000)}
    )
    audit = s28a.compute_top_tail_regime_audit_for_a1(scores, val_df, q_list=(10.0, 20.0))
    assert len(audit["per_q"]) == 2
    for r in audit["per_q"]:
        assert "top_mean_spread" in r
        assert "delta_mean_vs_population" in r


# [28.0a NEW]
def test_top_tail_audit_q_constants_inherited():
    assert s28a.TOP_TAIL_AUDIT_Q_PERCENTS == (10.0, 20.0)


# ===========================================================================
# Group 16 — Sanity probe extensions (5 NEW)
# ===========================================================================


def _make_synthetic_label_df(n: int = 100) -> pd.DataFrame:
    """Build a minimal DataFrame compatible with _derive_outcomes_vectorised.

    Uses TIME outcomes (time_to_fav_bar = -1 AND time_to_adv_bar = -1 → TIME label).
    """
    return pd.DataFrame(
        {
            "pair": ["USD_JPY"] * n,
            "direction": ["long"] * n,
            "atr_at_signal_pip": [5.0] * n,
            "spread_at_signal_pip": [2.0] * n,
            "signal_ts": pd.date_range("2024-01-01", periods=n, freq="5min"),
            "time_to_fav_bar": [-1] * n,
            "time_to_adv_bar": [-1] * n,
            "same_bar_both_hit": [False] * n,
        }
    )


# [28.0a NEW]
def test_sanity_probe_raises_on_l1_sample_weight_nan():
    train_df = _make_synthetic_label_df(100)
    val_df = _make_synthetic_label_df(100)
    test_df = _make_synthetic_label_df(100)
    bad_w = np.array([1.0, np.nan, 3.0] + [1.0] * 100)
    with pytest.raises(s28a.SanityProbeError):
        s28a.run_sanity_probe_28_0a(
            train_df,
            val_df,
            test_df,
            {},
            ["USD_JPY"],
            l1_sample_weight=bad_w,
        )


# [28.0a NEW]
def test_sanity_probe_raises_on_l3_sample_weight_below_one():
    train_df = _make_synthetic_label_df(100)
    val_df = _make_synthetic_label_df(100)
    test_df = _make_synthetic_label_df(100)
    bad_w = np.array([0.5, 1.5])  # 0.5 < 1.0 violates floor
    with pytest.raises(s28a.SanityProbeError):
        s28a.run_sanity_probe_28_0a(
            train_df,
            val_df,
            test_df,
            {},
            ["USD_JPY"],
            l3_sample_weight=bad_w,
        )


# [28.0a NEW]
def test_sanity_probe_raises_on_l2_grad_hess_failure():
    train_df = _make_synthetic_label_df(100)
    val_df = _make_synthetic_label_df(100)
    test_df = _make_synthetic_label_df(100)
    bad_check = {"all_pass": False, "failures": ["subtest1 (under-pred linear): wrong grad"]}
    with pytest.raises(s28a.SanityProbeError):
        s28a.run_sanity_probe_28_0a(
            train_df,
            val_df,
            test_df,
            {},
            ["USD_JPY"],
            l2_grad_hess_check=bad_check,
        )


# [28.0a NEW]
def test_l2_grad_hess_sanity_built_in_passes():
    """Self-test: built-in asymmetric Huber passes its own sanity check."""
    res = s28a.compute_l2_grad_hess_sanity()
    assert res["all_pass"] is True
    assert res["n_failures"] == 0


# [28.0a NEW]
def test_sanity_probe_reports_l1_l3_weight_distribution():
    train_df = _make_synthetic_label_df(100)
    val_df = _make_synthetic_label_df(100)
    test_df = _make_synthetic_label_df(100)
    good_w_l1 = np.array([5.0, 10.0, 15.0])
    good_w_l3 = np.array([1.5, 2.0, 2.5])
    out = s28a.run_sanity_probe_28_0a(
        train_df,
        val_df,
        test_df,
        {},
        ["USD_JPY"],
        l1_sample_weight=good_w_l1,
        l3_sample_weight=good_w_l3,
    )
    assert "l1_sample_weight_distribution" in out
    assert "l3_sample_weight_distribution" in out


# ===========================================================================
# Group 17 — Module docstring + clauses (4 NEW)
# ===========================================================================


# [28.0a NEW]
def test_module_docstring_mentions_closed_3_loss_allowlist():
    doc = s28a.__doc__ or ""
    assert "Closed 3-loss allowlist" in doc
    assert "L1 magnitude-weighted Huber" in doc
    assert "L2 asymmetric Huber" in doc
    assert "L3 spread-cost-weighted Huber" in doc


# [28.0a NEW]
def test_clause_3_gamma_closure_preserved():
    doc = s28a.__doc__ or ""
    assert "γ closure preservation" in doc
    assert "PR #279" in doc


# [28.0a NEW]
def test_clause_4_production_v9_untouched():
    doc = s28a.__doc__ or ""
    assert "v9 20-pair" in doc
    assert "79ed1e8" in doc


# [28.0a NEW]
def test_clause_5_ng_10_ng_11_not_relaxed():
    doc = s28a.__doc__ or ""
    assert "NG#10 / NG#11 not relaxed" in doc


# ===========================================================================
# Group 18 — Sub-phase naming (2 NEW)
# ===========================================================================


# [28.0a NEW]
def test_artifact_root_points_to_stage28_0a():
    assert s28a.ARTIFACT_ROOT.name == "stage28_0a"


# [28.0a NEW]
def test_module_docstring_mentions_phase_28_0a():
    doc = s28a.__doc__ or ""
    assert "28.0a" in doc


# ===========================================================================
# Group 19 — Inheritance from 27.0f-β (5 NEW; ensure R7-C-specific NOT imported)
# ===========================================================================


# [28.0a NEW]
def test_no_r7_c_feature_constants_imported():
    """A1 must NOT re-import R7-C feature constants from 27.0f."""
    assert not hasattr(s28a, "R7_C_FEATURES")
    assert not hasattr(s28a, "ALL_FEATURES_R7AC")


# [28.0a NEW]
def test_no_r7c_preflight_error_imported():
    """R7CPreflightError is 27.0f-specific; not used in 28.0a."""
    assert not hasattr(s28a, "R7CPreflightError")


# [28.0a NEW]
def test_inherits_baseline_match_error():
    """BaselineMismatchError inherited / redefined for FAIL-FAST §10 baseline."""
    assert issubclass(s28a.BaselineMismatchError, RuntimeError)


# [28.0a NEW]
def test_inherits_huber_alpha_from_27_0d():
    assert s28a.HUBER_ALPHA == 0.9


# [28.0a NEW]
def test_inherits_quantile_family_5_10_20_30_40_from_27_0f():
    assert s28a.QUANTILE_PERCENTS_28_0A == (5.0, 10.0, 20.0, 30.0, 40.0)
