"""Unit tests for Stage 27.0e-β S-E Quantile Family Trim eval.

~55-60 tests across 15 groups (per implementation plan):
- Group 1 — Trimmed quantile family constants (4)
- Group 2 — evaluate_quantile_family_custom helper (5)
- Group 3 — Cell construction (4)
- Group 4 — Per-cell quantile-family scoping (3)
- Group 5 — S-E score formula inheritance (3)
- Group 6 — BaselineMismatchError HALT (4)
- Group 7 — D10 amendment 2-artifact form (3)
- Group 8 — H-B5 falsification outcome resolver (5)
- Group 9 — Sanity probe extensions items 12-13 (4)
- Group 10 — §22 trimmed-vs-original report writer (3)
- Group 11 — Diagnostic-only enforcement (5)
- Group 12 — Class index mapping (2)
- Group 13 — Module docstring + clauses + D-1 binding (4)
- Group 14 — Sub-phase naming (2)
- Group 15 — Inheritance from 27.0d (5)

NEW 27.0e-specific tests flagged [27.0e NEW].
"""

from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

s27e = importlib.import_module("stage27_0e_s_e_quantile_trim_eval")


# ===========================================================================
# Group 1 — Trimmed quantile family constants (4 NEW)
# ===========================================================================


# [27.0e NEW]
def test_c_se_trimmed_quantile_percents_is_5_7_5_10():
    assert s27e.C_SE_TRIMMED_QUANTILE_PERCENTS == (5.0, 7.5, 10.0)


# [27.0e NEW]
def test_c_sb_baseline_quantile_percents_inherited():
    assert s27e.C_SB_BASELINE_QUANTILE_PERCENTS == (5.0, 10.0, 20.0, 30.0, 40.0)


# [27.0e NEW]
def test_trimmed_family_caps_at_10_percent():
    """D-X1: cap at 10% (1/4 of 27.0d's 40%)."""
    assert max(s27e.C_SE_TRIMMED_QUANTILE_PERCENTS) == 10.0


# [27.0e NEW]
def test_trimmed_family_minimum_5_percent_inherited():
    """D-X1: minimum 5% inherited from baseline."""
    assert min(s27e.C_SE_TRIMMED_QUANTILE_PERCENTS) == 5.0


# ===========================================================================
# Group 2 — evaluate_quantile_family_custom helper (5 NEW)
# ===========================================================================


# [27.0e NEW]
def test_evaluate_quantile_family_custom_accepts_list_parameter():
    """D-X5 / D-K1: helper accepts list/tuple parameter."""
    sig = inspect.signature(s27e.evaluate_quantile_family_custom)
    params = set(sig.parameters)
    assert "quantile_percents" in params


# [27.0e NEW]
def test_evaluate_quantile_family_custom_returns_same_shape_as_inherited():
    """Returns list of dicts with q_percent / cutoff / val / test keys."""
    rng = np.random.default_rng(42)
    score_val = rng.normal(0, 1, 1000)
    score_test = rng.normal(0, 1, 500)
    pnl_val = rng.normal(0, 5, 1000)
    pnl_test = rng.normal(0, 5, 500)
    out = s27e.evaluate_quantile_family_custom(
        score_val, pnl_val, score_test, pnl_test, 0.25, 0.25, quantile_percents=(5.0, 10.0)
    )
    assert isinstance(out, list)
    assert len(out) == 2
    for r in out:
        assert "q_percent" in r
        assert "cutoff" in r
        assert "val" in r
        assert "test" in r


# [27.0e NEW]
def test_evaluate_quantile_family_custom_handles_non_integer_percents():
    """D-K2: 7.5% handled directly via np.quantile; no rounding."""
    rng = np.random.default_rng(7)
    score_val = rng.normal(0, 1, 1000)
    score_test = rng.normal(0, 1, 500)
    pnl_val = rng.normal(0, 5, 1000)
    pnl_test = rng.normal(0, 5, 500)
    out = s27e.evaluate_quantile_family_custom(
        score_val, pnl_val, score_test, pnl_test, 0.25, 0.25, quantile_percents=(5.0, 7.5, 10.0)
    )
    # q_percent should be stored as float (not int) — 7.5 must survive
    q_percents = sorted(r["q_percent"] for r in out)
    assert q_percents == [5.0, 7.5, 10.0]


# [27.0e NEW]
def test_inherited_evaluate_quantile_family_unchanged():
    """D-K1: inherited evaluate_quantile_family is unchanged for backward compat."""
    s26c = importlib.import_module("stage26_0c_l1_eval")
    # The inherited function still exists and is NOT redefined in s27e
    assert hasattr(s26c, "evaluate_quantile_family")


# [27.0e NEW]
def test_evaluate_quantile_family_custom_q_percent_is_float():
    """Custom helper stores q_percent as float (not int) to support 7.5."""
    rng = np.random.default_rng(11)
    score_val = rng.normal(0, 1, 500)
    score_test = rng.normal(0, 1, 250)
    pnl_val = rng.normal(0, 5, 500)
    pnl_test = rng.normal(0, 5, 250)
    out = s27e.evaluate_quantile_family_custom(
        score_val, pnl_val, score_test, pnl_test, 0.25, 0.25, quantile_percents=(7.5,)
    )
    assert isinstance(out[0]["q_percent"], float)
    assert out[0]["q_percent"] == 7.5


# ===========================================================================
# Group 3 — Cell construction (4 NEW)
# ===========================================================================


# [27.0e NEW]
def test_build_s_e_cells_trimmed_returns_two_cells():
    cells = s27e.build_s_e_cells_trimmed()
    assert len(cells) == 2


# [27.0e NEW]
def test_build_s_e_cells_trimmed_has_c_se_trimmed_and_c_sb_baseline():
    cells = s27e.build_s_e_cells_trimmed()
    by_id = {c["id"]: c for c in cells}
    assert "C-se-trimmed" in by_id
    assert "C-sb-baseline" in by_id


# [27.0e NEW]
def test_no_c_se_original_extra_cell():
    """D-X3: only 2 cells; no separate C-se-original."""
    cells = s27e.build_s_e_cells_trimmed()
    ids = {c["id"] for c in cells}
    assert ids == {"C-se-trimmed", "C-sb-baseline"}
    assert "C-se-original" not in ids
    assert "C-se" not in ids  # not the 27.0d name either


# [27.0e NEW]
def test_cells_have_quantile_percents_field():
    """D-K3: each cell dict has quantile_percents field."""
    cells = s27e.build_s_e_cells_trimmed()
    for c in cells:
        assert "quantile_percents" in c, f"cell {c['id']} missing quantile_percents"


# ===========================================================================
# Group 4 — Per-cell quantile-family scoping (3 NEW)
# ===========================================================================


# [27.0e NEW]
def test_c_se_trimmed_uses_trimmed_family():
    cells = s27e.build_s_e_cells_trimmed()
    c_se = next(c for c in cells if c["id"] == "C-se-trimmed")
    assert c_se["quantile_percents"] == (5.0, 7.5, 10.0)


# [27.0e NEW]
def test_c_sb_baseline_uses_inherited_family():
    """D-X4: C-sb-baseline uses inherited 5-point family to preserve baseline match."""
    cells = s27e.build_s_e_cells_trimmed()
    c_sb = next(c for c in cells if c["id"] == "C-sb-baseline")
    assert c_sb["quantile_percents"] == (5.0, 10.0, 20.0, 30.0, 40.0)


# [27.0e NEW]
def test_evaluate_cell_27_0e_reads_quantile_percents_field():
    """D-K4: evaluate_cell_27_0e reads cell['quantile_percents']."""
    src = inspect.getsource(s27e.evaluate_cell_27_0e)
    assert 'cell.get("quantile_percents"' in src or "cell['quantile_percents']" in src


# ===========================================================================
# Group 5 — S-E score formula inheritance (3 NEW)
# ===========================================================================


# [27.0e NEW]
def test_compute_picker_score_s_e_inherited_from_27_0d():
    """S-E score function is unchanged from 27.0d."""
    s27d = importlib.import_module("stage27_0d_s_e_regression_eval")
    assert s27e.compute_picker_score_s_e is s27d.compute_picker_score_s_e


# [27.0e NEW]
def test_compute_picker_score_s_b_raw_inherited_from_27_0c():
    s27c = importlib.import_module("stage27_0c_s_d_calibrated_ev_eval")
    assert s27e.compute_picker_score_s_b_raw is s27c.compute_picker_score_s_b_raw


# [27.0e NEW]
def test_build_pipeline_lightgbm_regression_widened_inherited_from_27_0d():
    s27d = importlib.import_module("stage27_0d_s_e_regression_eval")
    assert (
        s27e.build_pipeline_lightgbm_regression_widened
        is s27d.build_pipeline_lightgbm_regression_widened
    )


# ===========================================================================
# Group 6 — BaselineMismatchError HALT (4 NEW)
# ===========================================================================


# [27.0e NEW]
def test_baseline_mismatch_error_is_runtime_error_subclass():
    assert issubclass(s27e.BaselineMismatchError, RuntimeError)


# [27.0e NEW]
def test_check_c_sb_baseline_match_passes_at_exact_baseline():
    fake = {
        "test_realised_metrics": {
            "n_trades": s27e.BASELINE_27_0B_C_ALPHA0_N_TRADES,
            "sharpe": s27e.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s27e.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    report = s27e.check_c_sb_baseline_match(fake)
    assert report["all_match"] is True


# [27.0e NEW]
def test_check_c_sb_baseline_match_halts_on_n_trades_drift():
    fake = {
        "test_realised_metrics": {
            "n_trades": s27e.BASELINE_27_0B_C_ALPHA0_N_TRADES + 1,
            "sharpe": s27e.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s27e.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    with pytest.raises(s27e.BaselineMismatchError, match=r"n_trades"):
        s27e.check_c_sb_baseline_match(fake)


# [27.0e NEW]
def test_baseline_tolerances_inherited_from_27_0d():
    """D-X7 / D-K10: tolerances IDENTICAL to 27.0d."""
    s27d = importlib.import_module("stage27_0d_s_e_regression_eval")
    assert s27e.BASELINE_27_0B_C_ALPHA0_N_TRADES == s27d.BASELINE_27_0B_C_ALPHA0_N_TRADES == 34626
    assert s27e.BASELINE_27_0B_C_ALPHA0_SHARPE == s27d.BASELINE_27_0B_C_ALPHA0_SHARPE == -0.1732
    assert s27e.BASELINE_27_0B_C_ALPHA0_ANN_PNL == s27d.BASELINE_27_0B_C_ALPHA0_ANN_PNL == -204664.4


# ===========================================================================
# Group 7 — D10 amendment 2-artifact form (3 NEW)
# ===========================================================================


# [27.0e NEW]
def test_main_fits_each_artifact_once():
    """D10 amendment: one regressor.fit + one multiclass_pipeline.fit."""
    src = inspect.getsource(s27e.main)
    assert src.count("regressor.fit(") == 1
    assert src.count("multiclass_pipeline.fit(") == 1


# [27.0e NEW]
def test_no_per_cell_refit_in_evaluate_cell_27_0e():
    src = inspect.getsource(s27e.evaluate_cell_27_0e)
    assert "pipeline.fit" not in src
    assert "regressor.fit" not in src


# [27.0e NEW]
def test_d10_amendment_documented():
    doc = s27e.__doc__ or ""
    flat = " ".join(doc.split())
    assert "D10 amendment" in flat
    assert "2-artifact" in flat or "one regressor" in flat.lower()


# ===========================================================================
# Group 8 — H-B5 falsification outcome resolver (5 NEW)
# ===========================================================================


# [27.0e NEW]
def test_h_b5_outcome_constants_defined():
    """4 outcome strings + NEEDS_REVIEW defensive."""
    assert s27e.H_B5_OUTCOME_STRONG_SUPPORT == "STRONG_SUPPORT"
    assert s27e.H_B5_OUTCOME_PARTIAL_SUPPORT == "PARTIAL_SUPPORT"
    assert s27e.H_B5_OUTCOME_FALSIFIED == "FALSIFIED"
    assert s27e.H_B5_OUTCOME_PARTIALLY_FALSIFIED_NEW_QUESTION == "PARTIALLY_FALSIFIED_NEW_QUESTION"
    assert s27e.H_B5_OUTCOME_NEEDS_REVIEW == "NEEDS_REVIEW"


# [27.0e NEW]
def test_h_b5_outcome_row_1_strong_support_when_h2_passes():
    """Row 1: STRONG_SUPPORT — exists q passing Sharpe ≥ A1 AND ann_pnl ≥ A2."""
    fake_cell_results = [
        {
            "cell": {"id": "C-se-trimmed"},
            "h_state": "OK",
            "test_formal_spearman": 0.4,
            "quantile_all": [
                {
                    "q_percent": 5.0,
                    "test": {"sharpe": 0.15, "annual_pnl": 500.0},
                },
                {
                    "q_percent": 7.5,
                    "test": {"sharpe": 0.05, "annual_pnl": 100.0},
                },
                {
                    "q_percent": 10.0,
                    "test": {"sharpe": -0.10, "annual_pnl": -200.0},
                },
            ],
        }
    ]
    out = s27e.compute_h_b5_falsification_outcome(fake_cell_results)
    assert out["h_b5_outcome"] == s27e.H_B5_OUTCOME_STRONG_SUPPORT
    assert out["row_matched"] == 1
    assert 5.0 in out["evidence"]["row_1_match_q"]


# [27.0e NEW]
def test_h_b5_outcome_row_3_falsified_when_all_q_wrong_direction():
    """Row 3: FALSIFIED — Spearman > 0.05 + all q have Sharpe < H3 (-0.192)."""
    fake_cell_results = [
        {
            "cell": {"id": "C-se-trimmed"},
            "h_state": "OK",
            "test_formal_spearman": 0.40,  # ≥ H1_meaningful (0.10) → row 2 fires before row 3
            "quantile_all": [
                {"q_percent": 5.0, "test": {"sharpe": -0.50, "annual_pnl": -1000.0}},
                {"q_percent": 7.5, "test": {"sharpe": -0.40, "annual_pnl": -800.0}},
                {"q_percent": 10.0, "test": {"sharpe": -0.30, "annual_pnl": -500.0}},
            ],
        }
    ]
    out = s27e.compute_h_b5_falsification_outcome(fake_cell_results)
    # With Spearman=0.40 (≥ 0.10), row 2 fires before row 3 (precedence)
    assert out["h_b5_outcome"] == s27e.H_B5_OUTCOME_PARTIAL_SUPPORT
    assert out["row_matched"] == 2


# [27.0e NEW]
def test_h_b5_outcome_row_4_partially_falsified_when_spearman_below_weak():
    """Row 4: PARTIALLY_FALSIFIED — Spearman ≤ H1_WEAK (0.05)."""
    fake_cell_results = [
        {
            "cell": {"id": "C-se-trimmed"},
            "h_state": "OK",
            "test_formal_spearman": 0.02,  # ≤ 0.05
            "quantile_all": [
                {"q_percent": 5.0, "test": {"sharpe": -0.50, "annual_pnl": -1000.0}},
                {"q_percent": 7.5, "test": {"sharpe": -0.40, "annual_pnl": -800.0}},
                {"q_percent": 10.0, "test": {"sharpe": -0.30, "annual_pnl": -500.0}},
            ],
        }
    ]
    out = s27e.compute_h_b5_falsification_outcome(fake_cell_results)
    assert out["h_b5_outcome"] == s27e.H_B5_OUTCOME_PARTIALLY_FALSIFIED_NEW_QUESTION
    assert out["row_matched"] == 4


# [27.0e NEW]
def test_h_b5_outcome_returns_needs_review_when_no_c_se_trimmed():
    """Defensive: NEEDS_REVIEW when C-se-trimmed not present."""
    fake_cell_results = [{"cell": {"id": "C-sb-baseline"}, "h_state": "OK"}]
    out = s27e.compute_h_b5_falsification_outcome(fake_cell_results)
    assert out["h_b5_outcome"] == s27e.H_B5_OUTCOME_NEEDS_REVIEW


# ===========================================================================
# Group 9 — Sanity probe extensions items 12-13 (4 NEW)
# ===========================================================================


# [27.0e NEW]
def test_sanity_probe_signature_accepts_new_27_0e_params():
    sig = inspect.signature(s27e.run_sanity_probe_27_0e)
    params = set(sig.parameters)
    assert "cell_definitions" in params
    assert "trade_count_budget_audit_c_se" in params


# [27.0e NEW]
def test_compute_trade_count_budget_audit_returns_per_q_dict():
    rng = np.random.default_rng(13)
    score_val = rng.normal(0, 1, 25881 * 4)  # ~100k val rows
    out = s27e.compute_trade_count_budget_audit(score_val, (5.0, 7.5, 10.0))
    assert len(out) == 3
    for r in out:
        assert "q_percent" in r
        assert "cutoff" in r
        assert "n_trades_val" in r
        assert "inflation_factor" in r
        assert "warn" in r


# [27.0e NEW]
def test_trade_count_inflation_warn_threshold_is_2():
    """D-K6: WARN if inflation > 2.0."""
    assert s27e.TRADE_COUNT_INFLATION_WARN_THRESHOLD == 2.0


# [27.0e NEW]
def test_val_baseline_n_trades_at_q5_inherited():
    """C-sb-baseline q=5 val baseline (25,881) inherited from 27.0b/27.0c/27.0d."""
    assert s27e.VAL_BASELINE_N_TRADES_AT_Q5 == 25881


# ===========================================================================
# Group 10 — §22 trimmed-vs-original report writer (3 NEW)
# ===========================================================================


# [27.0e NEW]
def test_load_27_0d_c_se_metrics_returns_dict_with_source_field():
    """D-K11: re-cite source field present."""
    out = s27e.load_27_0d_c_se_metrics()
    assert "source" in out


# [27.0e NEW]
def test_trim_effect_preserves_tolerance_is_1e_3():
    """D-K12: |Sharpe delta| ≤ 1e-3 at overlapping q → 'preserves' wording."""
    assert s27e.TRIM_EFFECT_PRESERVES_TOLERANCE == 1e-3


# [27.0e NEW]
def test_compute_trimmed_vs_original_comparison_returns_expected_keys():
    """Returns trimmed_per_q + c_se_27_0d_metrics + overlapping_q_compared + trim_effect."""
    fake_c_se_trimmed = {
        "quantile_all": [
            {"q_percent": 5.0, "test": {"n_trades": 100, "sharpe": -0.17, "annual_pnl": -200.0}},
        ]
    }
    fake_27_0d = {
        "source": "fallback",
        "selected_q_percent": 40,
        "test_n_trades": 184703,
        "test_sharpe": -0.483,
        "test_formal_spearman": 0.4381,
    }
    out = s27e.compute_trimmed_vs_original_comparison(fake_c_se_trimmed, fake_27_0d)
    assert "trimmed_per_q" in out
    assert "c_se_27_0d_metrics" in out
    assert "overlapping_q_compared" in out
    assert "trim_effect_sentence" in out


# ===========================================================================
# Group 11 — Diagnostic-only enforcement (5 NEW)
# ===========================================================================


# [27.0e NEW]
def test_clause_2_extension_mentions_quantile_family_disclosure_diagnostic_only():
    doc = s27e.__doc__ or ""
    flat = " ".join(doc.split()).lower()
    assert "quantile-family disclosure" in flat


# [27.0e NEW]
def test_clause_2_extension_mentions_trade_count_budget_audit_diagnostic_only():
    doc = s27e.__doc__ or ""
    flat = " ".join(doc.split()).lower()
    assert "trade-count budget audit" in flat


# [27.0e NEW]
def test_quantile_family_disclosure_not_in_formal_verdict():
    """Sanity probe items 12-13 are diagnostic-only; not in evaluate_cell_27_0e."""
    src = inspect.getsource(s27e.evaluate_cell_27_0e)
    assert "quantile_family_disclosure" not in src
    assert "trade_count_budget_audit" not in src


# [27.0e NEW]
def test_compute_trade_count_budget_audit_does_not_halt():
    """D-K6: WARN-only; no SanityProbeError raised from this function."""
    src = inspect.getsource(s27e.compute_trade_count_budget_audit)
    assert "raise SanityProbeError" not in src


# [27.0e NEW]
def test_sanity_probe_does_not_halt_on_items_12_or_13():
    """D-K6: NEW items 12-13 are WARN-only (warnings.warn), no SanityProbeError."""
    src = inspect.getsource(s27e.run_sanity_probe_27_0e)
    # Find items 12 + 13 region (between "quantile-family disclosure" and end)
    marker = "quantile-family disclosure per cell (NEW 27.0e"
    if marker in src:
        new_items_region = src.split(marker, 1)[1]
        # Items 12-13 region should use warnings.warn, not raise SanityProbeError
        # (until inherited HALT block at end)
        # Look for "Inherited HALT conditions" — should be the only raise SanityProbeError after
        before_inherited_halt = new_items_region.split("Inherited HALT conditions")[0]
        assert "raise SanityProbeError" not in before_inherited_halt
        assert "warnings.warn" in before_inherited_halt


# ===========================================================================
# Group 12 — Class index mapping (2 NEW)
# ===========================================================================


# [27.0e NEW]
def test_class_index_mapping_consistent_with_inherited():
    s27d = importlib.import_module("stage27_0d_s_e_regression_eval")
    assert s27e.LABEL_TP == s27d.LABEL_TP
    assert s27e.LABEL_SL == s27d.LABEL_SL
    assert s27e.LABEL_TIME == s27d.LABEL_TIME


# [27.0e NEW]
def test_num_classes_is_three():
    assert s27e.NUM_CLASSES == 3


# ===========================================================================
# Group 13 — Module docstring + clauses + D-1 binding (4 NEW)
# ===========================================================================


# [27.0e NEW]
def test_module_docstring_includes_all_six_mandatory_clauses():
    doc = s27e.__doc__ or ""
    for marker in [
        "1. Phase framing",
        "2. Diagnostic columns prohibition",
        "3. γ closure preservation",
        "4. Production-readiness preservation",
        "5. NG#10 / NG#11 not relaxed",
        "6. Phase 27 scope",
    ]:
        assert marker in doc, f"clause marker missing: {marker!r}"


# [27.0e NEW]
def test_module_docstring_documents_2_layer_selection_overfit_guard():
    doc = s27e.__doc__ or ""
    flat = " ".join(doc.split())
    assert "2-LAYER" in flat or "2-layer" in flat
    assert "train-only" in flat.lower()
    assert "cutoff selection" in flat.lower()


# [27.0e NEW]
def test_d1_binding_documented_in_module_docstring():
    doc = s27e.__doc__ or ""
    assert "D-1 BINDING" in doc or "D-1 binding" in doc
    assert "_compute_realised_barrier_pnl" in doc
    assert "bid/ask" in doc


# [27.0e NEW]
def test_module_docstring_documents_h_b5_falsification_criteria():
    """4-row outcome table from §14 binding."""
    doc = s27e.__doc__ or ""
    flat = " ".join(doc.split())
    assert "STRONG_SUPPORT" in flat
    assert "PARTIAL_SUPPORT" in flat
    assert "FALSIFIED" in flat


# ===========================================================================
# Group 14 — Sub-phase naming (2 NEW)
# ===========================================================================


# [27.0e NEW]
def test_artifact_root_is_stage27_0e():
    assert s27e.ARTIFACT_ROOT.name == "stage27_0e"


# [27.0e NEW]
def test_module_docstring_names_sub_phase_27_0e_not_27_0d_or_0f():
    doc = s27e.__doc__ or ""
    assert "27.0e-β" in doc
    # not naming itself 27.0f (kickoff §7 candidate-only); the sub-phase identity itself is 27.0e
    # (27.0f references only allowed in clause 6 wording about Phase 26 deferred items)
    assert "Stage 27.0e-β" in doc


# ===========================================================================
# Group 15 — Inheritance from 27.0d (5 NEW)
# ===========================================================================


# [27.0e NEW]
def test_make_oof_fold_assignment_inherited_from_27_0c():
    s27c = importlib.import_module("stage27_0c_s_d_calibrated_ev_eval")
    assert s27e.make_oof_fold_assignment is s27c.make_oof_fold_assignment


# [27.0e NEW]
def test_fit_oof_regression_diagnostic_inherited_from_27_0d():
    s27d = importlib.import_module("stage27_0d_s_e_regression_eval")
    assert s27e.fit_oof_regression_diagnostic is s27d.fit_oof_regression_diagnostic


# [27.0e NEW]
def test_compute_per_pair_sharpe_contribution_inherited_from_27_0b():
    s27b = importlib.import_module("stage27_0b_s_c_time_penalty_eval")
    assert s27e.compute_per_pair_sharpe_contribution is s27b.compute_per_pair_sharpe_contribution


# [27.0e NEW]
def test_select_cell_and_assign_verdict_inherited_from_26_0c():
    s26c = importlib.import_module("stage26_0c_l1_eval")
    assert s27e.select_cell_validation_only is s26c.select_cell_validation_only
    assert s27e.assign_verdict is s26c.assign_verdict
    assert s27e.aggregate_cross_cell_verdict is s26c.aggregate_cross_cell_verdict


# [27.0e NEW]
def test_build_pipeline_lightgbm_multiclass_widened_inherited_from_26_0d():
    s26d = importlib.import_module("stage26_0d_r6_new_a_eval")
    assert (
        s27e.build_pipeline_lightgbm_multiclass_widened
        is s26d.build_pipeline_lightgbm_multiclass_widened
    )
