"""Unit tests for Stage 27.0d-β S-E Regression-on-Realised-PnL eval.

~55-60 tests across 15 groups (per implementation plan):
- Group 1 — S-E score formula (4)
- Group 2 — LightGBMRegressor pipeline (5)
- Group 3 — Target preprocessing — D-W3 / D-J4 (4)
- Group 4 — 5-fold OOF protocol DIAGNOSTIC-ONLY (4)
- Group 5 — Cell construction (4)
- Group 6 — S-B raw baseline replica (3)
- Group 7 — BaselineMismatchError HALT (4)
- Group 8 — D10 amendment 2-artifact form (3)
- Group 9 — Diagnostic-only enforcement (5)
- Group 10 — Class index mapping (2)
- Group 11 — Sanity probe extensions (4)
- Group 12 — Module docstring + clauses + D-1 binding (4)
- Group 13 — Huber loss specifics (3)
- Group 14 — Sub-phase naming (2)
- Group 15 — Inheritance from 27.0c (4)

NEW 27.0d-specific tests flagged [27.0d NEW].
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

s27d = importlib.import_module("stage27_0d_s_e_regression_eval")


# ===========================================================================
# Group 1 — S-E score formula (4 NEW)
# ===========================================================================


# [27.0d NEW]
def test_s_e_score_is_regressor_predict_passthrough():
    """S-E(X) returns regressor.predict(X) as float64 numpy array."""

    class StubRegressor:
        def predict(self, x):
            return np.array([1.1, -2.5, 3.7])

    out = s27d.compute_picker_score_s_e(StubRegressor(), pd.DataFrame({"x": [0, 0, 0]}))
    np.testing.assert_array_almost_equal(out, np.array([1.1, -2.5, 3.7]), decimal=12)
    assert out.dtype == np.float64


# [27.0d NEW]
def test_s_e_score_no_clip_no_sign_flip_no_reshape():
    """S-E does not clip / sign-flip / reshape predictions."""
    src = inspect.getsource(s27d.compute_picker_score_s_e)
    # Strip docstring (function body must not call clipping / sign-flips)
    body = src.split('"""')[2] if src.count('"""') >= 2 else src
    assert "np.clip" not in body
    assert "-pred" not in body
    assert "reshape" not in body


# [27.0d NEW]
def test_s_e_score_handles_empty_input():
    class StubRegressor:
        def predict(self, x):
            return np.array([])

    out = s27d.compute_picker_score_s_e(StubRegressor(), pd.DataFrame({"x": []}))
    assert len(out) == 0
    assert out.dtype == np.float64


# [27.0d NEW]
def test_s_e_score_vectorised_not_per_row_loop():
    """Source has no per-row loop pattern."""
    src = inspect.getsource(s27d.compute_picker_score_s_e)
    body = src.split('"""')[2] if src.count('"""') >= 2 else src
    assert "for " not in body  # no loops in function body


# ===========================================================================
# Group 2 — LightGBMRegressor pipeline (5 NEW)
# ===========================================================================


# [27.0d NEW]
def test_lightgbm_regression_config_drops_multiclass_keys():
    """objective / num_class / class_weight removed from inherited config."""
    assert "num_class" not in s27d.LIGHTGBM_REGRESSION_CONFIG
    assert "class_weight" not in s27d.LIGHTGBM_REGRESSION_CONFIG
    # objective must be re-set to 'huber' (not 'multiclass')
    assert s27d.LIGHTGBM_REGRESSION_CONFIG.get("objective") == "huber"


# [27.0d NEW]
def test_lightgbm_regression_config_has_huber_alpha():
    """D-W2: alpha=0.9 Huber breakpoint."""
    assert s27d.LIGHTGBM_REGRESSION_CONFIG["alpha"] == 0.9
    assert s27d.HUBER_ALPHA == 0.9


# [27.0d NEW]
def test_lightgbm_regression_config_metric_is_huber():
    assert s27d.LIGHTGBM_REGRESSION_CONFIG.get("metric") == "huber"


# [27.0d NEW]
def test_lightgbm_regression_config_inherits_multiclass_hyperparams():
    """D-J2: n_estimators / learning_rate / max_depth / num_leaves / min_child_samples /
    subsample / colsample_bytree / random_state carried over verbatim."""
    mc_config = s27d.LIGHTGBM_MULTICLASS_CONFIG
    reg_config = s27d.LIGHTGBM_REGRESSION_CONFIG
    for key in (
        "n_estimators",
        "learning_rate",
        "max_depth",
        "num_leaves",
        "min_child_samples",
        "subsample",
        "colsample_bytree",
        "random_state",
    ):
        if key in mc_config:
            assert reg_config[key] == mc_config[key], f"key {key} not inherited verbatim"


# [27.0d NEW]
def test_build_pipeline_lightgbm_regression_widened_returns_pipeline_with_reg_step():
    pipe = s27d.build_pipeline_lightgbm_regression_widened()
    step_names = [name for name, _ in pipe.steps]
    assert "pre" in step_names
    # Step name is "clf" (cosmetic misnomer) for compatibility with the
    # inherited compute_feature_importance_diagnostic helper from stage26_0d,
    # which hard-codes pipeline.named_steps["clf"]. The actual step is an
    # LGBMRegressor (verified below).
    assert "clf" in step_names
    last_step = pipe.steps[-1][1]
    assert type(last_step).__name__ == "LGBMRegressor"


# ===========================================================================
# Group 3 — Target preprocessing — D-W3 / D-J4 (4 NEW)
# ===========================================================================


# [27.0d NEW]
def test_no_winsorisation_in_main():
    """D-W3: target preprocessing is NONE; main must not call winsorise / clip on PnL target."""
    src = inspect.getsource(s27d.main)
    assert "winsorise" not in src.lower()
    assert "winsorize" not in src.lower()
    # Specifically check no clipping applied to pnl_train_full / pnl_train_for_reg
    assert "pnl_train_full = np.clip" not in src
    assert "pnl_train_for_reg = np.clip" not in src


# [27.0d NEW]
def test_nan_pnl_train_threshold_constant_is_0_001():
    """D-J12: 0.1% of n_train HALT threshold."""
    assert s27d.NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD == 0.001


# [27.0d NEW]
def test_nan_pnl_main_drops_rows_not_imputed():
    """Main filters NaN-PnL rows from regressor training; no imputation."""
    src = inspect.getsource(s27d.main)
    # train_df_for_reg = train_df.loc[~nan_pnl_mask] — drop, not impute
    assert "nan_pnl_mask" in src
    assert "imput" not in src.lower()
    assert "fillna" not in src
    assert "np.nan_to_num" not in src


# [27.0d NEW]
def test_d1_binding_target_is_realised_barrier_pnl():
    """target(row) MUST be precompute_realised_pnl_per_row (D-1 bid/ask harness)."""
    src = inspect.getsource(s27d.main)
    assert "precompute_realised_pnl_per_row(train_df" in src
    # No mid-to-mid PnL used as target
    assert (
        "compute_mid_to_mid_pnl_diagnostic"
        not in src.split("regressor.fit")[0].split("pnl_train_for_reg")[-1]
    )


# ===========================================================================
# Group 4 — 5-fold OOF protocol DIAGNOSTIC-ONLY (4 NEW)
# ===========================================================================


# [27.0d NEW]
def test_oof_constants_inherited_from_27_0c():
    assert s27d.OOF_N_FOLDS == 5
    assert s27d.OOF_SEED == 42


# [27.0d NEW]
def test_make_oof_fold_assignment_inherited_from_27_0c():
    """REUSE 27.0c helper verbatim (per D-J5)."""
    s27c = importlib.import_module("stage27_0c_s_d_calibrated_ev_eval")
    assert s27d.make_oof_fold_assignment is s27c.make_oof_fold_assignment


# [27.0d NEW]
def test_fit_oof_regression_returns_predictions_for_every_train_row():
    rng = np.random.default_rng(7)
    n = 200
    x = pd.DataFrame(
        {
            "pair": ["USD_JPY"] * n,
            "direction": (["long", "short"] * (n // 2))[:n],
            "atr_at_signal_pip": rng.uniform(1, 10, n),
            "spread_at_signal_pip": rng.uniform(0.5, 5, n),
        }
    )
    y = rng.normal(0.0, 2.0, n)
    fold_idx = s27d.make_oof_fold_assignment(n, n_folds=5, seed=42)
    oof = s27d.fit_oof_regression_diagnostic(x, y, fold_idx, n_folds=5)
    assert len(oof) == n
    assert np.all(np.isfinite(oof))


# [27.0d NEW]
def test_oof_correlation_diagnostic_returns_per_fold_and_aggregate():
    rng = np.random.default_rng(11)
    n = 500
    y = rng.normal(0.0, 1.0, n)
    pred = y + rng.normal(0.0, 0.5, n)  # correlated with y
    fold_idx = s27d.make_oof_fold_assignment(n, n_folds=5, seed=42)
    diag = s27d.compute_oof_correlation_diagnostic(pred, y, fold_idx)
    assert "per_fold" in diag
    assert len(diag["per_fold"]) == 5
    assert "aggregate_pearson" in diag
    assert "aggregate_spearman" in diag
    assert "n_folds_pearson_positive" in diag


# ===========================================================================
# Group 5 — Cell construction (4 NEW)
# ===========================================================================


# [27.0d NEW]
def test_build_s_e_cells_returns_two_cells():
    cells = s27d.build_s_e_cells()
    assert len(cells) == 2


# [27.0d NEW]
def test_build_s_e_cells_has_c_se_and_c_sb_baseline_with_correct_score_types():
    cells = s27d.build_s_e_cells()
    by_id = {c["id"]: c for c in cells}
    assert "C-se" in by_id
    assert "C-sb-baseline" in by_id
    assert by_id["C-se"]["score_type"] == "s_e"
    assert by_id["C-sb-baseline"]["score_type"] == "s_b_raw"


# [27.0d NEW]
def test_build_s_e_cells_has_no_other_cells():
    """D-J7 / 27.0d-α §7.6: no within-β estimation-variant sweep."""
    cells = s27d.build_s_e_cells()
    ids = {c["id"] for c in cells}
    assert ids == {"C-se", "C-sb-baseline"}


# [27.0d NEW]
def test_build_s_e_cells_picker_strings_distinguish_score_objectives():
    cells = s27d.build_s_e_cells()
    by_id = {c["id"]: c for c in cells}
    assert "S-E" in by_id["C-se"]["picker"] or "regressor" in by_id["C-se"]["picker"]
    assert "S-B" in by_id["C-sb-baseline"]["picker"]


# ===========================================================================
# Group 6 — S-B raw baseline replica (3 NEW)
# ===========================================================================


# [27.0d NEW]
def test_compute_picker_score_s_b_raw_inherited_from_27_0c():
    s27c = importlib.import_module("stage27_0c_s_d_calibrated_ev_eval")
    assert s27d.compute_picker_score_s_b_raw is s27c.compute_picker_score_s_b_raw


# [27.0d NEW]
def test_c_sb_baseline_uses_raw_probs_not_calibrated_in_main():
    """C-sb-baseline scoring uses raw multiclass probs (NOT isotonic-calibrated)."""
    src = inspect.getsource(s27d.main)
    # NO isotonic calibration in 27.0d (no fit_isotonic / apply_isotonic invocations)
    assert "fit_isotonic_calibrators_per_class" not in src
    assert "apply_isotonic_and_renormalise" not in src


# [27.0d NEW]
def test_c_sb_baseline_score_is_raw_p_tp_minus_p_sl():
    """The C-sb-baseline branch in main uses compute_picker_score_s_b_raw."""
    src = inspect.getsource(s27d.main)
    assert "compute_picker_score_s_b_raw(val_raw_probs)" in src
    assert "compute_picker_score_s_b_raw(test_raw_probs)" in src


# ===========================================================================
# Group 7 — BaselineMismatchError HALT (4 NEW)
# ===========================================================================


# [27.0d NEW]
def test_baseline_mismatch_error_is_runtime_error_subclass():
    assert issubclass(s27d.BaselineMismatchError, RuntimeError)


# [27.0d NEW]
def test_check_c_sb_baseline_match_passes_at_exact_baseline():
    fake = {
        "test_realised_metrics": {
            "n_trades": s27d.BASELINE_27_0B_C_ALPHA0_N_TRADES,
            "sharpe": s27d.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s27d.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    report = s27d.check_c_sb_baseline_match(fake)
    assert report["all_match"] is True


# [27.0d NEW]
def test_check_c_sb_baseline_match_halts_on_n_trades_drift():
    fake = {
        "test_realised_metrics": {
            "n_trades": s27d.BASELINE_27_0B_C_ALPHA0_N_TRADES + 1,
            "sharpe": s27d.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s27d.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    with pytest.raises(s27d.BaselineMismatchError, match=r"n_trades"):
        s27d.check_c_sb_baseline_match(fake)


# [27.0d NEW]
def test_check_c_sb_baseline_match_halts_on_sharpe_drift():
    fake = {
        "test_realised_metrics": {
            "n_trades": s27d.BASELINE_27_0B_C_ALPHA0_N_TRADES,
            "sharpe": s27d.BASELINE_27_0B_C_ALPHA0_SHARPE - 0.01,
            "annual_pnl": s27d.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    with pytest.raises(s27d.BaselineMismatchError, match=r"Sharpe"):
        s27d.check_c_sb_baseline_match(fake)


# ===========================================================================
# Group 8 — D10 amendment 2-artifact form (3 NEW)
# ===========================================================================


# [27.0d NEW]
def test_d10_amendment_2_artifact_form_documented():
    doc = s27d.__doc__ or ""
    # Normalise whitespace (line wraps in docstrings)
    doc_flat = " ".join(doc.split())
    assert "D10 amendment" in doc_flat
    assert "2-artifact" in doc_flat or "ONE regressor" in doc_flat


# [27.0d NEW]
def test_no_per_cell_refit_in_evaluate_cell_27_0d():
    """evaluate_cell_27_0d receives precomputed scores and does NOT refit."""
    src = inspect.getsource(s27d.evaluate_cell_27_0d)
    assert "pipeline.fit" not in src
    assert "regressor.fit" not in src


# [27.0d NEW]
def test_main_fits_each_artifact_exactly_once():
    """One regressor.fit + one multiclass_pipeline.fit in main (excluding OOF folds)."""
    src = inspect.getsource(s27d.main)
    # `regressor.fit(...)` appears exactly once (not counting OOF fold fits in
    # fit_oof_regression_diagnostic which uses different variable name)
    assert src.count("regressor.fit(") == 1
    assert src.count("multiclass_pipeline.fit(") == 1


# ===========================================================================
# Group 9 — Diagnostic-only enforcement (5 NEW)
# ===========================================================================


# [27.0d NEW]
def test_clause_2_extension_mentions_regressor_feature_importance_diagnostic_only():
    doc = s27d.__doc__ or ""
    # Normalise whitespace (line wraps in docstrings)
    doc_flat = " ".join(doc.lower().split())
    assert "regressor feature importance" in doc_flat


# [27.0d NEW]
def test_clause_2_extension_mentions_predicted_vs_realised_correlation_diagnostic_only():
    doc = s27d.__doc__ or ""
    doc_flat = " ".join(doc.lower().split())
    assert "predicted-vs-realised" in doc_flat or "predicted vs realised" in doc_flat


# [27.0d NEW]
def test_clause_2_extension_mentions_r2_mae_predicted_distribution():
    doc = s27d.__doc__ or ""
    doc_flat = " ".join(doc.split())
    assert "R²" in doc_flat or "R2" in doc_flat.upper()
    assert "MAE" in doc_flat.upper()
    doc_flat_lower = " ".join(doc.lower().split())
    assert "predicted-pnl distribution" in doc_flat_lower


# [27.0d NEW]
def test_compute_regression_diagnostic_returns_diag_dict():
    """Returns MAE / R² / Pearson / Spearman; not used in formal verdict path."""
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0])
    pred = y + 0.1
    out = s27d.compute_regression_diagnostic(y, pred)
    assert "mae" in out
    assert "r2" in out
    assert "pearson" in out
    assert "spearman" in out
    assert out["mae"] > 0
    assert out["r2"] > 0.99


# [27.0d NEW]
def test_oof_correlation_pathology_is_warn_only_not_halt():
    """D-J6: OOF correlation < 0 majority folds → WARN only, not raise."""
    src = inspect.getsource(s27d.run_sanity_probe_27_0d)
    # The pathology branch uses warnings.warn, not raise SanityProbeError
    assert "warnings.warn" in src
    # And it sets oof_correlation_pathology_warn rather than raising
    assert "oof_correlation_pathology_warn" in src


# ===========================================================================
# Group 10 — Class index mapping (2 NEW)
# ===========================================================================


# [27.0d NEW]
def test_class_index_mapping_consistent_with_inherited():
    s27c = importlib.import_module("stage27_0c_s_d_calibrated_ev_eval")
    s27b = importlib.import_module("stage27_0b_s_c_time_penalty_eval")
    assert s27d.LABEL_TP == s27c.LABEL_TP == s27b.LABEL_TP
    assert s27d.LABEL_SL == s27c.LABEL_SL == s27b.LABEL_SL
    assert s27d.LABEL_TIME == s27c.LABEL_TIME == s27b.LABEL_TIME
    assert s27d.NUM_CLASSES == 3


# [27.0d NEW]
def test_num_classes_is_three_for_baseline_replica_only():
    """L-1 ternary classes used only for sanity probe + C-sb-baseline; NOT for S-E target."""
    assert s27d.NUM_CLASSES == 3


# ===========================================================================
# Group 11 — Sanity probe extensions (4 NEW)
# ===========================================================================


# [27.0d NEW]
def test_sanity_probe_signature_accepts_new_27_0d_params():
    sig = inspect.signature(s27d.run_sanity_probe_27_0d)
    params = set(sig.parameters)
    # New 27.0d-specific params per design memo §10
    assert "pnl_train_full" in params
    assert "oof_corr_diag" in params
    assert "train_reg_diag" in params
    assert "val_reg_diag" in params
    assert "test_reg_diag" in params
    assert "regressor_feature_importance" in params
    assert "train_drop_for_nan_pnl_count" in params


# [27.0d NEW]
def test_sanity_probe_no_halt_on_new_items_per_d_j11():
    """D-J11: NEW items 7-11 are DIAGNOSTIC-ONLY; no HALT."""
    src = inspect.getsource(s27d.run_sanity_probe_27_0d)
    # The new items appear AFTER the HALT block (or HALTs are limited to inherited)
    # Inherited HALTs include class_share / per_pair_TIME / NaN / positivity / NaN-PnL
    # NEW items 7-11 must not raise SanityProbeError directly
    assert "raise SanityProbeError" in src  # at least the inherited HALTs are there
    # Items 7-11 specifically should not have their own HALT branches
    new_item_keywords = [
        "target_pnl_distribution_train",
        "predicted_pnl_distribution",
        "regression_diagnostic",
        "regressor_feature_importance",
    ]
    for kw in new_item_keywords:
        # No raise SanityProbeError tied to these new items
        idx = src.find(kw)
        if idx > 0:
            # Look in a 200-char window AFTER the keyword for a raise statement
            snippet = src[idx : idx + 200]
            assert "raise SanityProbeError" not in snippet, (
                f"NEW item {kw} should not HALT (DIAGNOSTIC-ONLY per D-J11)"
            )


# [27.0d NEW]
def test_sanity_probe_halts_on_nan_pnl_train_drop_above_threshold():
    """D-J12: NaN-PnL train rows > 0.1% triggers SanityProbeError."""
    src = inspect.getsource(s27d.run_sanity_probe_27_0d)
    assert "train_drop_for_nan_pnl_count" in src
    assert "NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD" in src
    assert "SanityProbeError" in src


# [27.0d NEW]
def test_sanity_probe_main_halts_on_nan_pnl_above_threshold():
    """Main also enforces D-J12 HALT before regressor fit."""
    src = inspect.getsource(s27d.main)
    assert "NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD" in src
    assert "SanityProbeError" in src


# ===========================================================================
# Group 12 — Module docstring + clauses + D-1 binding (4 NEW)
# ===========================================================================


# [27.0d NEW]
def test_module_docstring_includes_all_six_mandatory_clauses():
    doc = s27d.__doc__ or ""
    for marker in [
        "1. Phase framing",
        "2. Diagnostic columns prohibition",
        "3. γ closure preservation",
        "4. Production-readiness preservation",
        "5. NG#10 / NG#11 not relaxed",
        "6. Phase 27 scope",
    ]:
        assert marker in doc, f"clause marker missing: {marker!r}"


# [27.0d NEW]
def test_module_docstring_documents_2_layer_selection_overfit_guard():
    """Per 27.0d-α §13 verbatim binding."""
    doc = s27d.__doc__ or ""
    assert "2-LAYER" in doc or "2-layer" in doc
    assert "train-only" in doc.lower()
    assert "cutoff selection" in doc.lower()


# [27.0d NEW]
def test_d1_binding_documented_in_module_docstring():
    doc = s27d.__doc__ or ""
    assert "D-1 BINDING" in doc or "D-1 binding" in doc
    assert "_compute_realised_barrier_pnl" in doc
    assert "bid/ask" in doc


# [27.0d NEW]
def test_baseline_reference_values_match_27_0c():
    """D-J10: identical numeric values as 27.0c per 27.0d-α §7.3 / D-W7."""
    s27c = importlib.import_module("stage27_0c_s_d_calibrated_ev_eval")
    assert s27d.BASELINE_27_0B_C_ALPHA0_N_TRADES == s27c.BASELINE_27_0B_C_ALPHA0_N_TRADES == 34626
    assert s27d.BASELINE_27_0B_C_ALPHA0_SHARPE == s27c.BASELINE_27_0B_C_ALPHA0_SHARPE == -0.1732
    assert s27d.BASELINE_27_0B_C_ALPHA0_ANN_PNL == s27c.BASELINE_27_0B_C_ALPHA0_ANN_PNL == -204664.4


# ===========================================================================
# Group 13 — Huber loss specifics (3 NEW)
# ===========================================================================


# [27.0d NEW]
def test_huber_alpha_default_is_0_9():
    assert s27d.HUBER_ALPHA == 0.9
    assert s27d.LIGHTGBM_REGRESSION_CONFIG["alpha"] == 0.9


# [27.0d NEW]
def test_no_mse_l1_tweedie_default_within_27_0d_beta():
    """D-J2 / D-W2: Huber is the only default loss; no MSE / L1 / Tweedie sweep."""
    config = s27d.LIGHTGBM_REGRESSION_CONFIG
    assert config["objective"] == "huber"
    assert config["objective"] != "regression"  # not MSE
    assert config["objective"] != "regression_l1"  # not L1
    assert config["objective"] != "tweedie"


# [27.0d NEW]
def test_objective_metric_match():
    """Both objective and metric set to 'huber' for consistent training/evaluation."""
    assert s27d.LIGHTGBM_REGRESSION_CONFIG["objective"] == "huber"
    assert s27d.LIGHTGBM_REGRESSION_CONFIG["metric"] == "huber"


# ===========================================================================
# Group 14 — Sub-phase naming (2 NEW)
# ===========================================================================


# [27.0d NEW]
def test_artifact_root_is_stage27_0d():
    assert s27d.ARTIFACT_ROOT.name == "stage27_0d"


# [27.0d NEW]
def test_module_docstring_names_sub_phase_27_0d_not_27_0e_or_0f():
    doc = s27d.__doc__ or ""
    assert "27.0d-β" in doc
    # Avoid claims it is named 27.0e or 27.0f
    assert "27.0e-β" not in doc
    assert "27.0f-β" not in doc


# ===========================================================================
# Group 15 — Inheritance from 27.0c (4 NEW)
# ===========================================================================


# [27.0d NEW]
def test_inherits_make_oof_fold_assignment_from_27_0c():
    s27c = importlib.import_module("stage27_0c_s_d_calibrated_ev_eval")
    assert s27d.make_oof_fold_assignment is s27c.make_oof_fold_assignment


# [27.0d NEW]
def test_inherits_compute_per_pair_sharpe_contribution_from_27_0b():
    s27b = importlib.import_module("stage27_0b_s_c_time_penalty_eval")
    assert s27d.compute_per_pair_sharpe_contribution is s27b.compute_per_pair_sharpe_contribution


# [27.0d NEW]
def test_inherits_select_cell_validation_only_and_assign_verdict():
    s26c = importlib.import_module("stage26_0c_l1_eval")
    assert s27d.select_cell_validation_only is s26c.select_cell_validation_only
    assert s27d.assign_verdict is s26c.assign_verdict
    assert s27d.aggregate_cross_cell_verdict is s26c.aggregate_cross_cell_verdict


# [27.0d NEW]
def test_inherits_build_pipeline_lightgbm_multiclass_widened_from_26_0d():
    """C-sb-baseline uses the inherited multiclass pipeline verbatim."""
    s26d = importlib.import_module("stage26_0d_r6_new_a_eval")
    assert (
        s27d.build_pipeline_lightgbm_multiclass_widened
        is s26d.build_pipeline_lightgbm_multiclass_widened
    )
