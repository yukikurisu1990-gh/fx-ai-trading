"""Unit tests for Stage 28.0b-β A4 Monetisation-Aware Selection eval.

~65-75 tests across 17 groups (per implementation plan):
- Group 1 — Rule numerics / closed allowlist constants (4)
- Group 2 — R1 fit_r1_threshold_per_pair (4)
- Group 3 — R2 fit_r2_middle_bulk_cutoffs (4)
- Group 4 — R3 fit_r3_per_pair_q95 (4)
- Group 5 — R4 apply_r4_top_k_per_bar (5)
- Group 6 — build_a4_cells structure (5)
- Group 7 — evaluate_rule_cell vs evaluate_quantile_cell dispatch (4)
- Group 8 — D10 single-score-artifact form (3)
- Group 9 — BaselineMismatchError HALT (4)
- Group 10 — H-C2 4-outcome ladder resolver (8)
- Group 11 — within-eval topq drift check (4)
- Group 12 — C-a4-top-q-control drift vs 27.0d C-se WARN (3)
- Group 13 — Sanity probe extensions (5)
- Group 14 — Module docstring + clauses + R-T1 absorption note (5)
- Group 15 — Sub-phase naming + inheritance assertions (3)
- Group 16 — NG#A4-1/2/3 enforcement (4)
- Group 17 — α-fixed numerics validation (4)

NEW 28.0b-specific tests flagged [28.0b NEW].
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

s28b = importlib.import_module("stage28_0b_a4_monetisation_aware_selection_eval")


# ===========================================================================
# Group 1 — Rule numerics / closed allowlist constants (4 NEW; NG#A4-1)
# ===========================================================================


# [28.0b NEW]
def test_r1_fit_percentile_is_50():
    assert s28b.R1_FIT_PERCENTILE == 50.0


# [28.0b NEW]
def test_r2_percentile_cutoffs_are_40_60():
    assert s28b.R2_PERCENTILE_LO == 40.0
    assert s28b.R2_PERCENTILE_HI == 60.0


# [28.0b NEW]
def test_r3_q_per_pair_is_5_percent():
    assert s28b.R3_Q_PER_PAIR == 5.0
    assert s28b.R3_FIT_PERCENTILE == 95.0


# [28.0b NEW]
def test_r4_k_per_bar_is_1():
    assert s28b.R4_K_PER_BAR == 1


# ===========================================================================
# Group 2 — R1 fit_r1_threshold_per_pair (4 NEW)
# ===========================================================================


def _make_pair_score_df(n_per_pair: int = 100) -> tuple[pd.DataFrame, np.ndarray]:
    """Build a synthetic (df, score) pair for rule fit testing."""
    pairs = ["USD_JPY", "EUR_USD", "GBP_JPY"]
    rows = []
    scores = []
    rng = np.random.RandomState(42)
    for p in pairs:
        rows.extend([{"pair": p, "direction": "long", "signal_ts": i} for i in range(n_per_pair)])
        scores.extend(rng.randn(n_per_pair).tolist())
    return pd.DataFrame(rows), np.array(scores, dtype=np.float64)


# [28.0b NEW]
def test_r1_fits_per_pair_median():
    df, score = _make_pair_score_df(n_per_pair=100)
    c_per_pair = s28b.fit_r1_threshold_per_pair(df, score)
    assert set(c_per_pair.keys()) == {"USD_JPY", "EUR_USD", "GBP_JPY"}
    # Verify each c is approximately the median
    for p in c_per_pair:
        mask = df["pair"].to_numpy() == p
        expected_median = np.percentile(score[mask], 50.0)
        assert abs(c_per_pair[p] - expected_median) < 1e-9


# [28.0b NEW]
def test_r1_apply_threshold_returns_bool_mask():
    df, score = _make_pair_score_df(n_per_pair=100)
    c_per_pair = s28b.fit_r1_threshold_per_pair(df, score)
    mask = s28b.apply_r1_threshold(df, score, c_per_pair)
    assert mask.dtype == bool
    assert len(mask) == len(df)
    # Approximately 50% of rows traded (since c = median per pair)
    fraction = mask.sum() / len(mask)
    assert 0.40 < fraction < 0.60


# [28.0b NEW]
def test_r1_raises_on_row_count_mismatch():
    df, score = _make_pair_score_df(n_per_pair=100)
    with pytest.raises(ValueError):
        s28b.fit_r1_threshold_per_pair(df, score[:50])


# [28.0b NEW]
def test_r1_handles_unknown_pair_at_apply():
    df, score = _make_pair_score_df(n_per_pair=100)
    c_per_pair = s28b.fit_r1_threshold_per_pair(df, score)
    # Apply to a row with a pair NOT in the fit dict
    eval_df = pd.DataFrame({"pair": ["UNKNOWN_PAIR"], "direction": ["long"]})
    eval_score = np.array([100.0])
    mask = s28b.apply_r1_threshold(eval_df, eval_score, c_per_pair)
    # Unknown pair → threshold is inf → no trade
    assert mask.sum() == 0


# ===========================================================================
# Group 3 — R2 fit_r2_middle_bulk_cutoffs (4 NEW)
# ===========================================================================


# [28.0b NEW]
def test_r2_fits_global_40_60_percentiles():
    score = np.linspace(0, 100, 1001)  # uniform; 40th=40, 60th=60
    lo, hi = s28b.fit_r2_middle_bulk_cutoffs(score)
    assert abs(lo - 40.0) < 1.0
    assert abs(hi - 60.0) < 1.0
    assert lo < hi


# [28.0b NEW]
def test_r2_apply_middle_bulk_traded_fraction():
    score = np.linspace(0, 100, 1001)
    cutoffs = s28b.fit_r2_middle_bulk_cutoffs(score)
    mask = s28b.apply_r2_middle_bulk(score, cutoffs)
    # ~20% should be in [40, 60] range
    fraction = mask.sum() / len(mask)
    assert 0.15 < fraction < 0.25


# [28.0b NEW]
def test_r2_raises_on_no_finite_score():
    score = np.array([np.nan, np.inf, -np.inf])
    with pytest.raises(ValueError):
        s28b.fit_r2_middle_bulk_cutoffs(score)


# [28.0b NEW]
def test_r2_uses_default_cutoffs_40_60():
    score = np.linspace(0, 100, 1001)
    cutoffs_default = s28b.fit_r2_middle_bulk_cutoffs(score)
    cutoffs_explicit = s28b.fit_r2_middle_bulk_cutoffs(
        score, p_lo=s28b.R2_PERCENTILE_LO, p_hi=s28b.R2_PERCENTILE_HI
    )
    assert cutoffs_default == cutoffs_explicit


# ===========================================================================
# Group 4 — R3 fit_r3_per_pair_q95 (4 NEW)
# ===========================================================================


# [28.0b NEW]
def test_r3_fits_per_pair_95th_percentile():
    df, score = _make_pair_score_df(n_per_pair=200)
    cutoff_per_pair = s28b.fit_r3_per_pair_q95(df, score)
    assert set(cutoff_per_pair.keys()) == {"USD_JPY", "EUR_USD", "GBP_JPY"}
    # Each cutoff is the per-pair 95th percentile
    for p in cutoff_per_pair:
        mask = df["pair"].to_numpy() == p
        expected_p95 = np.percentile(score[mask], 95.0)
        assert abs(cutoff_per_pair[p] - expected_p95) < 1e-9


# [28.0b NEW]
def test_r3_apply_per_pair_q95_traded_fraction():
    df, score = _make_pair_score_df(n_per_pair=200)
    cutoff_per_pair = s28b.fit_r3_per_pair_q95(df, score)
    mask = s28b.apply_r3_per_pair_q95(df, score, cutoff_per_pair)
    # Approximately 5% per pair → 5% global
    fraction = mask.sum() / len(mask)
    assert 0.02 < fraction < 0.08


# [28.0b NEW]
def test_r3_fit_percentile_is_95_not_5():
    """NG#A4-1: top 5% per pair = np.percentile(score, 95) not 5"""
    assert s28b.R3_FIT_PERCENTILE == 95.0
    assert s28b.R3_FIT_PERCENTILE == 100.0 - s28b.R3_Q_PER_PAIR


# [28.0b NEW]
def test_r3_unknown_pair_at_apply():
    df, score = _make_pair_score_df(n_per_pair=200)
    cutoff_per_pair = s28b.fit_r3_per_pair_q95(df, score)
    eval_df = pd.DataFrame({"pair": ["UNKNOWN_PAIR"]})
    eval_score = np.array([100.0])
    mask = s28b.apply_r3_per_pair_q95(eval_df, eval_score, cutoff_per_pair)
    assert mask.sum() == 0


# ===========================================================================
# Group 5 — R4 apply_r4_top_k_per_bar (5 NEW)
# ===========================================================================


# [28.0b NEW]
def test_r4_k1_selects_one_per_bar():
    eval_df = pd.DataFrame(
        {
            "signal_ts": [1, 1, 1, 2, 2, 3],
            "pair": ["A", "B", "C", "A", "B", "A"],
        }
    )
    score = np.array([0.5, 0.9, 0.1, 0.3, 0.8, 0.6])
    mask = s28b.apply_r4_top_k_per_bar(eval_df, score, k=1)
    # Per signal_ts: bar 1 → idx 1 (score 0.9); bar 2 → idx 4 (score 0.8); bar 3 → idx 5 (score 0.6)
    assert mask.tolist() == [False, True, False, False, True, True]


# [28.0b NEW]
def test_r4_k1_traded_count_equals_n_unique_signal_ts():
    eval_df = pd.DataFrame(
        {
            "signal_ts": [1, 1, 1, 2, 2, 3, 4, 4],
            "pair": ["A", "B", "C", "A", "B", "A", "A", "B"],
        }
    )
    score = np.random.RandomState(0).randn(len(eval_df))
    mask = s28b.apply_r4_top_k_per_bar(eval_df, score, k=1)
    assert mask.sum() == eval_df["signal_ts"].nunique()


# [28.0b NEW]
def test_r4_raises_on_k_not_1():
    """NG#A4-1: K is α-fixed at 1; K != 1 violates the closed allowlist."""
    eval_df = pd.DataFrame({"signal_ts": [1, 1, 2], "pair": ["A", "B", "A"]})
    score = np.array([0.1, 0.2, 0.3])
    with pytest.raises(ValueError):
        s28b.apply_r4_top_k_per_bar(eval_df, score, k=2)


# [28.0b NEW]
def test_r4_handles_nan_scores():
    eval_df = pd.DataFrame({"signal_ts": [1, 1, 2], "pair": ["A", "B", "A"]})
    score = np.array([np.nan, 0.5, 0.3])
    mask = s28b.apply_r4_top_k_per_bar(eval_df, score, k=1)
    # bar 1 → idx 1 (only finite); bar 2 → idx 2
    assert mask.tolist() == [False, True, True]


# [28.0b NEW]
def test_r4_default_k_is_1():
    eval_df = pd.DataFrame({"signal_ts": [1, 1, 2], "pair": ["A", "B", "A"]})
    score = np.array([0.1, 0.5, 0.3])
    mask_default = s28b.apply_r4_top_k_per_bar(eval_df, score)
    mask_explicit = s28b.apply_r4_top_k_per_bar(eval_df, score, k=1)
    assert (mask_default == mask_explicit).all()


# ===========================================================================
# Group 6 — build_a4_cells structure (5 NEW)
# ===========================================================================


# [28.0b NEW]
def test_a4_cells_6_total():
    cells = s28b.build_a4_cells()
    assert len(cells) == 6


# [28.0b NEW]
def test_a4_cells_deterministic_order():
    """D-BB9: R1 → R2 → R3 → R4 → top-q-control → baseline"""
    cells = s28b.build_a4_cells()
    cell_ids = [c["id"] for c in cells]
    assert cell_ids == [
        "C-a4-R1",
        "C-a4-R2",
        "C-a4-R3",
        "C-a4-R4",
        "C-a4-top-q-control",
        "C-sb-baseline",
    ]


# [28.0b NEW]
def test_a4_cells_all_r7a_feature_set():
    cells = s28b.build_a4_cells()
    for c in cells:
        assert c["feature_set"] == "r7a"


# [28.0b NEW; NG#A4-3]
def test_a4_top_q_control_cell_present():
    cells = s28b.build_a4_cells()
    cell_ids = [c["id"] for c in cells]
    assert "C-a4-top-q-control" in cell_ids


# [28.0b NEW]
def test_a4_cells_quantile_family_assignments():
    """Rule cells have empty quantile_percents; top-q-control and baseline have {5,10,20,30,40}."""
    cells = s28b.build_a4_cells()
    cell_map = {c["id"]: c for c in cells}
    assert tuple(cell_map["C-a4-R1"]["quantile_percents"]) == ()
    assert tuple(cell_map["C-a4-R2"]["quantile_percents"]) == ()
    assert tuple(cell_map["C-a4-R3"]["quantile_percents"]) == ()
    assert tuple(cell_map["C-a4-R4"]["quantile_percents"]) == ()
    assert tuple(cell_map["C-a4-top-q-control"]["quantile_percents"]) == (
        5.0,
        10.0,
        20.0,
        30.0,
        40.0,
    )
    assert tuple(cell_map["C-sb-baseline"]["quantile_percents"]) == (5.0, 10.0, 20.0, 30.0, 40.0)


# ===========================================================================
# Group 7 — evaluate_rule_cell vs evaluate_quantile_cell dispatch (4 NEW)
# ===========================================================================


# [28.0b NEW]
def test_main_dispatches_s_e_r1_to_rule_cell_evaluator():
    src = inspect.getsource(s28b.main)
    assert 'score_type == "s_e_r1"' in src
    assert "evaluate_rule_cell_28_0b" in src


# [28.0b NEW]
def test_main_dispatches_s_e_topq_to_quantile_cell_evaluator():
    src = inspect.getsource(s28b.main)
    assert 'score_type == "s_e_topq"' in src
    assert "evaluate_quantile_cell_28_0b" in src


# [28.0b NEW]
def test_main_dispatches_s_b_raw_to_quantile_cell_evaluator():
    src = inspect.getsource(s28b.main)
    assert 'score_type == "s_b_raw"' in src


# [28.0b NEW]
def test_rule_cell_quantile_all_is_empty_list():
    """Rule cells have no quantile sweep; quantile_all should be []."""
    src = inspect.getsource(s28b.evaluate_rule_cell_28_0b)
    assert '"quantile_all": []' in src


# ===========================================================================
# Group 8 — D10 single-score-artifact form (3 NEW; NG#A4-2)
# ===========================================================================


# [28.0b NEW]
def test_d10_single_se_regressor_fitted():
    """PR #341 §7.1: 1 S-E regressor + 1 multiclass head = 2 artifacts total."""
    src = inspect.getsource(s28b.main)
    assert "regressor_se = build_pipeline_lightgbm_regression_widened()" in src
    assert "multiclass_pipeline = build_pipeline_lightgbm_multiclass_widened()" in src


# [28.0b NEW]
def test_no_per_rule_regressor_fit():
    """Rules are deterministic post-fit operations; no per-rule regressor."""
    src = inspect.getsource(s28b.main)
    assert "regressor_r1" not in src
    assert "regressor_r2" not in src
    assert "regressor_r3" not in src
    assert "regressor_r4" not in src


# [28.0b NEW]
def test_se_score_fit_with_no_sample_weight():
    """NG#A4-1: S-E uses sample_weight=1 (no kwarg passed; default behavior)."""
    src = inspect.getsource(s28b.main)
    idx = src.find("regressor_se.fit")
    assert idx > 0
    fit_slice = src[idx : idx + 200]
    assert "sample_weight" not in fit_slice, (
        "S-E regressor must NOT pass sample_weight (NG#A4-1; symmetric Huber backbone)"
    )


# ===========================================================================
# Group 9 — BaselineMismatchError HALT (4 NEW; FAIL-FAST inheritance)
# ===========================================================================


# [28.0b NEW]
def test_baseline_mismatch_error_inherits_runtime_error():
    assert issubclass(s28b.BaselineMismatchError, RuntimeError)


# [28.0b NEW]
def test_check_c_sb_baseline_match_raises_on_n_trades_mismatch():
    fake_result = {
        "test_realised_metrics": {
            "n_trades": 34000,  # ≠ 34626
            "sharpe": s28b.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s28b.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    with pytest.raises(s28b.BaselineMismatchError):
        s28b.check_c_sb_baseline_match(fake_result)


# [28.0b NEW]
def test_check_c_sb_baseline_match_passes_on_exact():
    fake_result = {
        "test_realised_metrics": {
            "n_trades": s28b.BASELINE_27_0B_C_ALPHA0_N_TRADES,
            "sharpe": s28b.BASELINE_27_0B_C_ALPHA0_SHARPE,
            "annual_pnl": s28b.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
        }
    }
    report = s28b.check_c_sb_baseline_match(fake_result)
    assert report["all_match"] is True


# [28.0b NEW]
def test_baseline_tolerances_inherited_verbatim():
    """n_trades exact / Sharpe ±1e-4 / ann_pnl ±0.5 pip (inherited from 27.0c-α §7.3)."""
    assert s28b.BASELINE_MATCH_N_TRADES_TOLERANCE == 0
    assert s28b.BASELINE_MATCH_SHARPE_ABS_TOLERANCE == 1e-4
    assert s28b.BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE == 0.5


# ===========================================================================
# Group 10 — H-C2 4-outcome ladder resolver (8 NEW; precedence row 4 first)
# ===========================================================================


def _make_rule_cell_result(
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
        "val_cell_spearman": cell_spearman_val,
        "test_formal_spearman": cell_spearman_val,
        "quantile_best": {"val": {"spearman_score_vs_pnl": cell_spearman_val}},
    }


# [28.0b NEW]
def test_h_c2_partial_drift_topq_replica_takes_precedence():
    """Row 4 (PARTIAL_DRIFT_TOPQ_REPLICA) checked first per NG#A4-3."""
    cell_result = _make_rule_cell_result(
        "C-a4-R1", val_sharpe=-0.05, val_n=30000, cell_spearman_val=0.4
    )
    baseline_match = {"all_match": True}
    drift = {"all_within_tolerance": True}  # within → PARTIAL_DRIFT
    out = s28b.compute_h_c2_outcome_per_rule(cell_result, baseline_match, drift)
    assert out["outcome"] == s28b.H_C2_OUTCOME_PARTIAL_DRIFT_TOPQ_REPLICA
    assert out["row_matched"] == 4


# [28.0b NEW]
def test_h_c2_pass_outcome():
    cell_result = _make_rule_cell_result(
        "C-a4-R1", val_sharpe=-0.05, val_n=30000, cell_spearman_val=0.4
    )
    baseline_match = {"all_match": True}
    drift = {"all_within_tolerance": False}
    out = s28b.compute_h_c2_outcome_per_rule(cell_result, baseline_match, drift)
    assert out["outcome"] == s28b.H_C2_OUTCOME_PASS
    assert out["row_matched"] == 1


# [28.0b NEW]
def test_h_c2_partial_support_outcome():
    """Sharpe lift ∈ [+0.02, +0.05) → PARTIAL_SUPPORT"""
    # baseline val sharpe = -0.1863; +0.03 lift → val sharpe = -0.1563
    cell_result = _make_rule_cell_result(
        "C-a4-R1", val_sharpe=-0.1563, val_n=30000, cell_spearman_val=0.4
    )
    baseline_match = {"all_match": True}
    drift = {"all_within_tolerance": False}
    out = s28b.compute_h_c2_outcome_per_rule(cell_result, baseline_match, drift)
    assert out["outcome"] == s28b.H_C2_OUTCOME_PARTIAL_SUPPORT
    assert out["row_matched"] == 2


# [28.0b NEW]
def test_h_c2_falsified_outcome():
    cell_result = _make_rule_cell_result(
        "C-a4-R1",
        val_sharpe=-0.30,  # lift = -0.30 - (-0.1863) = -0.114 < +0.02
        val_n=30000,
        cell_spearman_val=0.4,
    )
    baseline_match = {"all_match": True}
    drift = {"all_within_tolerance": False}
    out = s28b.compute_h_c2_outcome_per_rule(cell_result, baseline_match, drift)
    assert out["outcome"] == s28b.H_C2_OUTCOME_FALSIFIED_RULE_INSUFFICIENT
    assert out["row_matched"] == 3


# [28.0b NEW]
def test_h_c2_h1m_fail_falls_to_falsified():
    cell_result = _make_rule_cell_result(
        "C-a4-R1",
        val_sharpe=-0.05,
        val_n=30000,
        cell_spearman_val=0.10,  # below 0.30
    )
    baseline_match = {"all_match": True}
    drift = {"all_within_tolerance": False}
    out = s28b.compute_h_c2_outcome_per_rule(cell_result, baseline_match, drift)
    assert out["outcome"] == s28b.H_C2_OUTCOME_FALSIFIED_RULE_INSUFFICIENT


# [28.0b NEW]
def test_h_c2_aggregate_split_verdict_on_any_pass():
    per_rule = [
        {"cell_id": "C-a4-R1", "outcome": s28b.H_C2_OUTCOME_PASS, "row_matched": 1},
        {
            "cell_id": "C-a4-R2",
            "outcome": s28b.H_C2_OUTCOME_FALSIFIED_RULE_INSUFFICIENT,
            "row_matched": 3,
        },
        {
            "cell_id": "C-a4-R3",
            "outcome": s28b.H_C2_OUTCOME_FALSIFIED_RULE_INSUFFICIENT,
            "row_matched": 3,
        },
        {
            "cell_id": "C-a4-R4",
            "outcome": s28b.H_C2_OUTCOME_FALSIFIED_RULE_INSUFFICIENT,
            "row_matched": 3,
        },
    ]
    agg = s28b.compute_h_c2_aggregate_verdict(per_rule)
    assert agg["aggregate_verdict"] == "SPLIT_VERDICT_ROUTE_TO_REVIEW"
    assert agg["has_pass"] is True
    assert agg["r_t1_absorption_status"] == "PASS_under_A4"


# [28.0b NEW]
def test_h_c2_aggregate_reject_on_all_partial_drift():
    per_rule = [
        {
            "cell_id": f"C-a4-R{i}",
            "outcome": s28b.H_C2_OUTCOME_PARTIAL_DRIFT_TOPQ_REPLICA,
            "row_matched": 4,
        }
        for i in range(1, 5)
    ]
    agg = s28b.compute_h_c2_aggregate_verdict(per_rule)
    assert agg["aggregate_verdict"] == "REJECT_NON_DISCRIMINATIVE"
    assert agg["all_partial_drift"] is True
    assert agg["r_t1_absorption_status"] == "FALSIFIED_under_A4"


# [28.0b NEW]
def test_h_c2_aggregate_reject_on_all_falsified():
    per_rule = [
        {
            "cell_id": f"C-a4-R{i}",
            "outcome": s28b.H_C2_OUTCOME_FALSIFIED_RULE_INSUFFICIENT,
            "row_matched": 3,
        }
        for i in range(1, 5)
    ]
    agg = s28b.compute_h_c2_aggregate_verdict(per_rule)
    assert agg["aggregate_verdict"] == "REJECT_NON_DISCRIMINATIVE"
    assert agg["r_t1_absorption_status"] == "FALSIFIED_under_A4"


# ===========================================================================
# Group 11 — within-eval topq drift check (4 NEW)
# ===========================================================================


# [28.0b NEW]
def test_within_eval_topq_drift_within_tolerance():
    candidate = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 184700, "sharpe": -0.483, "annual_pnl": -999800.0},
    }
    control = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 184703, "sharpe": -0.4831, "annual_pnl": -999830.0},
    }
    d = s28b.compute_within_eval_topq_drift_check(candidate, control)
    assert d["all_within_tolerance"] is True


# [28.0b NEW]
def test_within_eval_topq_drift_outside_tolerance_n_trades():
    candidate = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 180000, "sharpe": -0.483, "annual_pnl": -999800.0},
    }
    control = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 184703, "sharpe": -0.4831, "annual_pnl": -999830.0},
    }
    d = s28b.compute_within_eval_topq_drift_check(candidate, control)
    assert d["all_within_tolerance"] is False


# [28.0b NEW]
def test_within_eval_topq_drift_outside_tolerance_sharpe():
    candidate = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 184700, "sharpe": -0.30, "annual_pnl": -999800.0},
    }
    control = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 184703, "sharpe": -0.483, "annual_pnl": -999830.0},
    }
    d = s28b.compute_within_eval_topq_drift_check(candidate, control)
    assert d["all_within_tolerance"] is False


# [28.0b NEW]
def test_within_eval_topq_drift_missing_h_state():
    candidate = {"h_state": "ERROR"}
    control = {
        "h_state": "OK",
        "test_realised_metrics": {"n_trades": 1, "sharpe": 0.0, "annual_pnl": 0.0},
    }
    d = s28b.compute_within_eval_topq_drift_check(candidate, control)
    assert d["all_within_tolerance"] is False


# ===========================================================================
# Group 12 — C-a4-top-q-control drift vs 27.0d C-se WARN (3 NEW)
# ===========================================================================


# [28.0b NEW]
def test_c_a4_top_q_control_drift_returns_diagnostic_only():
    """Drift check returns dict with 'warn' flag; DOES NOT raise (DIAGNOSTIC-ONLY WARN)."""
    fake_result = {
        "test_realised_metrics": {
            "n_trades": 184703,
            "sharpe": -0.4831,
            "annual_pnl": -999830.0,
        }
    }
    report = s28b.compute_c_a4_top_q_control_drift_check(fake_result)
    assert "warn" in report
    assert "all_within_tolerance" in report


# [28.0b NEW]
def test_topq_control_drift_tolerances():
    """Per PR #341 §9 / 27.0f D-AA10: n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%."""
    assert s28b.TOPQ_CONTROL_DRIFT_N_TRADES_TOLERANCE == 100
    assert s28b.TOPQ_CONTROL_DRIFT_SHARPE_TOLERANCE == 5e-3
    assert s28b.TOPQ_CONTROL_DRIFT_ANN_PNL_FRAC_TOLERANCE == 0.005


# [28.0b NEW]
def test_within_eval_drift_tolerances_match_topq_control():
    """Within-eval drift uses same tolerances as top-q-control drift."""
    assert s28b.WITHIN_EVAL_DRIFT_N_TRADES_TOLERANCE == s28b.TOPQ_CONTROL_DRIFT_N_TRADES_TOLERANCE
    assert s28b.WITHIN_EVAL_DRIFT_SHARPE_TOLERANCE == s28b.TOPQ_CONTROL_DRIFT_SHARPE_TOLERANCE
    assert (
        s28b.WITHIN_EVAL_DRIFT_ANN_PNL_FRAC_TOLERANCE
        == s28b.TOPQ_CONTROL_DRIFT_ANN_PNL_FRAC_TOLERANCE
    )


# ===========================================================================
# Group 13 — Sanity probe extensions (5 NEW)
# ===========================================================================


def _make_synthetic_label_df(n: int = 100) -> pd.DataFrame:
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


# [28.0b NEW]
def test_sanity_probe_raises_on_r1_missing_pair():
    train_df = _make_synthetic_label_df(100)
    val_df = _make_synthetic_label_df(100)
    test_df = _make_synthetic_label_df(100)
    # USD_JPY missing from c_per_pair
    bad_c = {"EUR_USD": 0.5}
    with pytest.raises(s28b.SanityProbeError):
        s28b.run_sanity_probe_28_0b(
            train_df,
            val_df,
            test_df,
            {},
            ["USD_JPY"],
            r1_c_per_pair=bad_c,
        )


# [28.0b NEW]
def test_sanity_probe_raises_on_r2_cutoffs_invalid():
    train_df = _make_synthetic_label_df(100)
    val_df = _make_synthetic_label_df(100)
    test_df = _make_synthetic_label_df(100)
    bad_cutoffs = (0.6, 0.4)  # lo > hi
    with pytest.raises(s28b.SanityProbeError):
        s28b.run_sanity_probe_28_0b(
            train_df,
            val_df,
            test_df,
            {},
            ["USD_JPY"],
            r2_cutoffs=bad_cutoffs,
        )


# [28.0b NEW]
def test_sanity_probe_raises_on_r3_missing_pair():
    train_df = _make_synthetic_label_df(100)
    val_df = _make_synthetic_label_df(100)
    test_df = _make_synthetic_label_df(100)
    bad_cutoff = {"EUR_USD": 0.95}
    with pytest.raises(s28b.SanityProbeError):
        s28b.run_sanity_probe_28_0b(
            train_df,
            val_df,
            test_df,
            {},
            ["USD_JPY"],
            r3_cutoff_per_pair=bad_cutoff,
        )


# [28.0b NEW]
def test_sanity_probe_raises_on_r4_k1_violation():
    """R4 K=1 verification: traded_mask sum must equal n_unique_signal_ts."""
    train_df = _make_synthetic_label_df(100)
    val_df = _make_synthetic_label_df(100)
    test_df = _make_synthetic_label_df(100)
    bad_mask = np.zeros(100, dtype=bool)
    bad_mask[:10] = True  # 10 trades but assume 50 unique signal_ts
    with pytest.raises(s28b.SanityProbeError):
        s28b.run_sanity_probe_28_0b(
            train_df,
            val_df,
            test_df,
            {},
            ["USD_JPY"],
            r4_traded_mask_val=bad_mask,
            r4_n_unique_signal_ts_val=50,
        )


# [28.0b NEW]
def test_sanity_probe_reports_rule_summaries():
    train_df = _make_synthetic_label_df(100)
    val_df = _make_synthetic_label_df(100)
    test_df = _make_synthetic_label_df(100)
    good_r1 = {"USD_JPY": 0.5}
    good_r2 = (0.4, 0.6)
    good_r3 = {"USD_JPY": 0.95}
    good_mask = np.ones(100, dtype=bool)
    out = s28b.run_sanity_probe_28_0b(
        train_df,
        val_df,
        test_df,
        {},
        ["USD_JPY"],
        r1_c_per_pair=good_r1,
        r2_cutoffs=good_r2,
        r3_cutoff_per_pair=good_r3,
        r4_traded_mask_val=good_mask,
        r4_n_unique_signal_ts_val=100,
    )
    assert "r1_c_per_pair" in out
    assert "r2_cutoffs" in out
    assert "r3_cutoff_per_pair" in out
    assert "r4_k1_verification" in out
    assert out["r4_k1_verification"]["pass"] is True


# ===========================================================================
# Group 14 — Module docstring + clauses + R-T1 absorption (5 NEW)
# ===========================================================================


# [28.0b NEW]
def test_module_docstring_mentions_closed_4_rule_allowlist():
    doc = s28b.__doc__ or ""
    assert "Closed 4-rule allowlist" in doc
    assert "R1 absolute-threshold" in doc
    assert "R2 middle-bulk" in doc
    assert "R3 per-pair quantile" in doc
    assert "R4 top-K per bar" in doc


# [28.0b NEW]
def test_module_docstring_declares_r_t1_absorption():
    doc = s28b.__doc__ or ""
    assert "R-T1 formal absorption" in doc
    assert "H-C2 = R-T1 elevation under A4 frame resolution" in doc


# [28.0b NEW]
def test_module_docstring_declares_se_score_fixed():
    doc = s28b.__doc__ or ""
    assert "Fixed S-E score source" in doc
    assert "L2/L3 NOT admissible" in doc


# [28.0b NEW]
def test_clause_3_gamma_closure_preserved():
    doc = s28b.__doc__ or ""
    assert "γ closure preservation" in doc
    assert "PR #279" in doc


# [28.0b NEW]
def test_clause_5_ng_10_ng_11_not_relaxed():
    doc = s28b.__doc__ or ""
    assert "NG#10 / NG#11 not relaxed" in doc


# ===========================================================================
# Group 15 — Sub-phase naming + inheritance (3 NEW)
# ===========================================================================


# [28.0b NEW]
def test_artifact_root_points_to_stage28_0b():
    assert s28b.ARTIFACT_ROOT.name == "stage28_0b"


# [28.0b NEW]
def test_no_l1_l2_l3_imports_from_28_0a():
    """28.0b inherits from 28.0a structure but NOT the L1/L2/L3 loss variant logic."""
    src = inspect.getsource(s28b)
    # asymmetric_huber_objective belongs to 28.0a-β only
    assert "asymmetric_huber_objective" not in src
    assert "L2_DELTA_POS" not in src
    assert "L2_DELTA_NEG" not in src
    assert "L2_HESS_EPS" not in src


# [28.0b NEW]
def test_huber_alpha_inherited_from_27_0d():
    """S-E backbone uses symmetric Huber α=0.9 inherited verbatim."""
    assert s28b.HUBER_ALPHA == 0.9


# ===========================================================================
# Group 16 — NG#A4-1 / NG#A4-2 / NG#A4-3 enforcement (4 NEW)
# ===========================================================================


# [28.0b NEW; NG#A4-1]
def test_no_grid_sweep_constants_present():
    """NG#A4-1: no grid sweep within rule; no constants like R1_C_GRID."""
    forbidden = (
        "R1_C_GRID",
        "R2_PERCENTILE_GRID",
        "R3_Q_GRID",
        "R4_K_GRID",
        "FIFTH_RULE",
    )
    for name in forbidden:
        assert not hasattr(s28b, name), f"{name} would violate NG#A4-1"


# [28.0b NEW; NG#A4-1]
def test_no_alternate_score_source():
    """NG#A4-1: no L2/L3 score variants in 28.0b."""
    src = inspect.getsource(s28b)
    # L1/L2/L3 sample_weight or asymmetric obj should NOT appear
    assert "build_l1_sample_weight" not in src
    assert "build_l3_sample_weight" not in src
    assert "asymmetric_huber_objective" not in src


# [28.0b NEW; NG#A4-2]
def test_per_rule_verdict_aggregation():
    """NG#A4-2: per-rule verdicts recorded separately."""
    src = inspect.getsource(s28b.main)
    assert "h_c2_per_rule: list[dict] = []" in src
    # Per-rule loop iterates over all 4 rules deterministically
    assert '("R1", "C-a4-R1")' in src
    assert '("R2", "C-a4-R2")' in src
    assert '("R3", "C-a4-R3")' in src
    assert '("R4", "C-a4-R4")' in src


# [28.0b NEW; NG#A4-3]
def test_c_a4_top_q_control_mandatory_in_cell_list():
    """NG#A4-3: C-a4-top-q-control must be in the cell list."""
    cells = s28b.build_a4_cells()
    cell_ids = [c["id"] for c in cells]
    assert "C-a4-top-q-control" in cell_ids


# ===========================================================================
# Group 17 — α-fixed numerics validation (4 NEW; PR #341 §4)
# ===========================================================================


# [28.0b NEW]
def test_r1_c_fit_method_is_per_pair_median():
    """PR #341 §4.1: R1 c = per-pair val-median (percentile 50)"""
    assert s28b.R1_FIT_PERCENTILE == 50.0


# [28.0b NEW]
def test_r2_global_percentile_cutoffs_40_60():
    """PR #341 §4.2: R2 [p_lo, p_hi] = [40, 60]"""
    assert s28b.R2_PERCENTILE_LO == 40.0
    assert s28b.R2_PERCENTILE_HI == 60.0


# [28.0b NEW]
def test_r3_q_per_pair_5_percent():
    """PR #341 §4.3: R3 q_per_pair = 5% top per pair"""
    assert s28b.R3_Q_PER_PAIR == 5.0


# [28.0b NEW]
def test_r4_k_per_bar_1():
    """PR #341 §4.4: R4 K = 1 per signal_ts"""
    assert s28b.R4_K_PER_BAR == 1
