"""Unit tests for Stage 26.0c-β L-1 ternary classification eval.

35 tests covering:
- Label construction (8)
- Picker scores (6)
- Quantile cutoff selection (8)
- Verdict routing (5)
- Diagnostic-only column prohibition (4)
- End-to-end + comparison (4)

3 NEW L-1-specific tests are flagged with comment '[L-1 NEW]':
  - test_l1_class_set_disjointness_invariant
  - test_picker_diff_monotonic_in_ptp_with_psl_fixed
  - test_multiclass_probability_sum_to_one_invariance
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

l1 = importlib.import_module("stage26_0c_l1_eval")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_row(
    pair: str = "EUR_USD",
    signal_ts: str = "2024-04-30 12:30:00+00:00",
    direction: str = "long",
    entry_ask: float = 1.07238,
    entry_bid: float = 1.07223,
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
                "signal_ts": pd.Timestamp(signal_ts),
                "horizon_bars": 60,
                "direction": direction,
                "entry_ask": entry_ask,
                "entry_bid": entry_bid,
                "atr_at_signal_pip": atr_at_signal_pip,
                "spread_at_signal_pip": spread_at_signal_pip,
                "time_to_fav_bar": time_to_fav_bar,
                "time_to_adv_bar": time_to_adv_bar,
                "same_bar_both_hit": same_bar_both_hit,
            }
        ]
    )


# ===========================================================================
# Group 1 — Label construction (8 tests)
# ===========================================================================


# Test 1
def test_build_l1_labels_assigns_disjoint_classes():
    """Every row gets exactly one of {0, 1, 2} (LABEL_TP / LABEL_SL / LABEL_TIME)."""
    rows = []
    for tf, ta in [(20, -1), (-1, 30), (-1, -1), (5, 10), (10, 5)]:
        rows.append(
            _make_row(time_to_fav_bar=tf, time_to_adv_bar=ta, same_bar_both_hit=False).iloc[0]
        )
    df = pd.DataFrame(rows)
    label = l1.build_l1_labels_for_dataframe(df)
    assert set(label.unique()).issubset({l1.LABEL_TP, l1.LABEL_SL, l1.LABEL_TIME})


# Test 2
def test_l1_long_tp_hit_first_returns_label_0():
    df = _make_row(direction="long", time_to_fav_bar=20, time_to_adv_bar=-1)
    label = l1.build_l1_labels_for_dataframe(df)
    assert label.iloc[0] == l1.LABEL_TP


# Test 3
def test_l1_long_sl_hit_first_returns_label_1():
    df = _make_row(direction="long", time_to_fav_bar=-1, time_to_adv_bar=30)
    label = l1.build_l1_labels_for_dataframe(df)
    assert label.iloc[0] == l1.LABEL_SL


# Test 4
def test_l1_neither_barrier_hit_returns_label_2_time_exit():
    df = _make_row(time_to_fav_bar=-1, time_to_adv_bar=-1)
    label = l1.build_l1_labels_for_dataframe(df)
    assert label.iloc[0] == l1.LABEL_TIME


# Test 5
def test_l1_short_tp_at_barrier_below_entry_returns_label_0():
    df = _make_row(direction="short", time_to_fav_bar=15, time_to_adv_bar=-1)
    label = l1.build_l1_labels_for_dataframe(df)
    assert label.iloc[0] == l1.LABEL_TP


# Test 6
def test_l1_short_sl_at_barrier_above_entry_returns_label_1():
    df = _make_row(direction="short", time_to_fav_bar=-1, time_to_adv_bar=15)
    label = l1.build_l1_labels_for_dataframe(df)
    assert label.iloc[0] == l1.LABEL_SL


# Test 7
def test_l1_simultaneous_barrier_break_tie_breaks_to_sl():
    """Same-bar both-hit per 26.0c-α §2.3: SL precedes TP (conservative)."""
    df = _make_row(time_to_fav_bar=10, time_to_adv_bar=10, same_bar_both_hit=True)
    label = l1.build_l1_labels_for_dataframe(df)
    assert label.iloc[0] == l1.LABEL_SL


# Test 8 — [L-1 NEW] class-set disjointness invariant
def test_l1_class_set_disjointness_invariant():
    """For any (path, atr, direction), exactly one of TP/SL/TIME fires; sum = total."""
    rng = np.random.default_rng(42)
    n = 500
    rows = []
    for _ in range(n):
        tf = int(rng.integers(-1, 60)) if rng.random() < 0.5 else -1
        ta = int(rng.integers(-1, 60)) if rng.random() < 0.5 else -1
        sb = bool(rng.random() < 0.1)
        rows.append(_make_row(time_to_fav_bar=tf, time_to_adv_bar=ta, same_bar_both_hit=sb).iloc[0])
    df = pd.DataFrame(rows)
    label = l1.build_l1_labels_for_dataframe(df)
    # Every row gets exactly one of {0, 1, 2}
    counts = {
        l1.LABEL_TP: int((label == l1.LABEL_TP).sum()),
        l1.LABEL_SL: int((label == l1.LABEL_SL).sum()),
        l1.LABEL_TIME: int((label == l1.LABEL_TIME).sum()),
    }
    assert sum(counts.values()) == n, "disjoint partition: sum must equal total"
    assert all(v >= 0 for v in counts.values())


# ===========================================================================
# Group 2 — Picker scores (6 tests)
# ===========================================================================


# Test 9
def test_picker_ptp_returns_first_column_of_probs():
    probs = np.array([[0.1, 0.5, 0.4], [0.7, 0.2, 0.1]])
    score = l1.compute_picker_score_ptp(probs)
    np.testing.assert_array_almost_equal(score, [0.1, 0.7])


# Test 10
def test_picker_diff_returns_first_minus_second_column():
    probs = np.array([[0.5, 0.3, 0.2], [0.1, 0.8, 0.1]])
    score = l1.compute_picker_score_diff(probs)
    np.testing.assert_array_almost_equal(score, [0.5 - 0.3, 0.1 - 0.8])


# Test 11
def test_picker_ptp_range_0_to_1():
    probs = np.array([[0.0, 0.5, 0.5], [1.0, 0.0, 0.0], [0.33, 0.33, 0.34]])
    score = l1.compute_picker_score_ptp(probs)
    assert score.min() >= 0.0
    assert score.max() <= 1.0


# Test 12
def test_picker_diff_range_minus_1_to_1():
    probs = np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.5, 0.5, 0.0]])
    score = l1.compute_picker_score_diff(probs)
    assert score.min() >= -1.0
    assert score.max() <= 1.0


# Test 13 — [L-1 NEW] P(TP)-P(SL) monotonic in P(TP) at fixed P(SL)
def test_picker_diff_monotonic_in_ptp_with_psl_fixed():
    """Increasing P(TP) at fixed P(SL) ⇒ increasing diff."""
    p_sl = 0.30
    # Sequence with increasing P(TP) and matching decrease in P(TIME)
    ptp_seq = [0.10, 0.20, 0.30, 0.40, 0.50]
    probs = np.array([[ptp, p_sl, 1.0 - ptp - p_sl] for ptp in ptp_seq])
    diff = l1.compute_picker_score_diff(probs)
    assert np.all(np.diff(diff) > 0), "diff must be strictly increasing in P(TP) at fixed P(SL)"


# Test 14 — [L-1 NEW] multiclass probability sum-to-1 invariance
def test_multiclass_probability_sum_to_one_invariance():
    """LightGBM multiclass predict_proba rows sum to 1.0 (LightGBM contract)."""
    # Synthetic probs that obey sum-to-1
    probs = np.array(
        [
            [0.1, 0.5, 0.4],
            [0.7, 0.2, 0.1],
            [0.33, 0.33, 0.34],
            [0.0, 0.0, 1.0],
        ]
    )
    sums = probs.sum(axis=1)
    np.testing.assert_array_almost_equal(sums, np.ones(len(probs)), decimal=10)
    # Both pickers operate on this normalised probability matrix
    score_ptp = l1.compute_picker_score_ptp(probs)
    score_diff = l1.compute_picker_score_diff(probs)
    # P(TP) ranges within [0, 1]
    assert score_ptp.min() >= 0 and score_ptp.max() <= 1
    # diff ranges within [-1, 1]
    assert score_diff.min() >= -1 and score_diff.max() <= 1


# ===========================================================================
# Group 3 — Quantile cutoff selection (8 tests)
# ===========================================================================


# Test 15
def test_select_quantile_cutoff_returns_top_q_percent_indices():
    rng = np.random.default_rng(0)
    pred_val = rng.uniform(0, 1, size=1000)
    cutoff = l1.fit_quantile_cutoff_on_val(pred_val, 10)
    n_above = int((pred_val >= cutoff).sum())
    # Approximately 10% of 1000
    assert 80 <= n_above <= 120


# Test 16
def test_select_quantile_cutoff_q5_more_selective_than_q40():
    rng = np.random.default_rng(0)
    pred_val = rng.normal(0, 1, size=2000)
    c5 = l1.fit_quantile_cutoff_on_val(pred_val, 5)
    c40 = l1.fit_quantile_cutoff_on_val(pred_val, 40)
    assert c5 > c40, "smaller q% must yield higher cutoff (more selective)"


# Test 17
def test_a0_prefilter_drops_quantiles_below_200_trades():
    """A0-equivalent prefilter uses VAL_SPAN_YEARS × A0_MIN_ANNUAL_TRADES."""
    a0_min = l1.A0_MIN_ANNUAL_TRADES * l1.VAL_SPAN_YEARS
    cells = [
        {
            "cell": {"id": "C01", "picker": l1.PICKER_PTP},
            "selected_q_percent": 5,
            "val_realised_sharpe": 0.50,  # higher Sharpe but below A0
            "val_realised_annual_pnl": 200.0,
            "val_n_trades": int(a0_min) - 1,
            "val_max_dd": 10.0,
            "h_state": "OK",
        },
        {
            "cell": {"id": "C02", "picker": l1.PICKER_DIFF},
            "selected_q_percent": 10,
            "val_realised_sharpe": 0.20,  # lower Sharpe but A0-eligible
            "val_realised_annual_pnl": 100.0,
            "val_n_trades": int(a0_min) + 100,
            "val_max_dd": 8.0,
            "h_state": "OK",
        },
    ]
    res = l1.select_cell_validation_only(cells)
    assert res["selected"]["cell"]["id"] == "C02"
    assert res["low_val_trades_flag"] is False


# Test 18
def test_a0_prefilter_keeps_quantile_at_exactly_200():
    a0_min = l1.A0_MIN_ANNUAL_TRADES * l1.VAL_SPAN_YEARS
    cells = [
        {
            "cell": {"id": "C01", "picker": l1.PICKER_PTP},
            "selected_q_percent": 5,
            "val_realised_sharpe": 0.30,
            "val_realised_annual_pnl": 150.0,
            "val_n_trades": int(np.ceil(a0_min)),  # exactly A0-equivalent
            "val_max_dd": 10.0,
            "h_state": "OK",
        }
    ]
    res = l1.select_cell_validation_only(cells)
    assert res["selected"] is not None
    assert res["low_val_trades_flag"] is False


# Test 19
def test_tie_breaker_ann_pnl_resolves_sharpe_tie():
    cells = [
        {
            "cell": {"id": "C01", "picker": l1.PICKER_PTP},
            "selected_q_percent": 5,
            "val_realised_sharpe": 0.10,
            "val_realised_annual_pnl": 50.0,
            "val_n_trades": 5000,
            "val_max_dd": 10.0,
            "h_state": "OK",
        },
        {
            "cell": {"id": "C02", "picker": l1.PICKER_DIFF},
            "selected_q_percent": 10,
            "val_realised_sharpe": 0.10,  # same Sharpe
            "val_realised_annual_pnl": 100.0,  # higher annual_pnl
            "val_n_trades": 5000,
            "val_max_dd": 10.0,
            "h_state": "OK",
        },
    ]
    res = l1.select_cell_validation_only(cells)
    assert res["selected"]["cell"]["id"] == "C02"


# Test 20
def test_tie_breaker_max_dd_resolves_ann_pnl_tie():
    cells = [
        {
            "cell": {"id": "C01", "picker": l1.PICKER_PTP},
            "selected_q_percent": 5,
            "val_realised_sharpe": 0.10,
            "val_realised_annual_pnl": 100.0,
            "val_n_trades": 5000,
            "val_max_dd": 50.0,  # larger DD
            "h_state": "OK",
        },
        {
            "cell": {"id": "C02", "picker": l1.PICKER_DIFF},
            "selected_q_percent": 10,
            "val_realised_sharpe": 0.10,
            "val_realised_annual_pnl": 100.0,
            "val_n_trades": 5000,
            "val_max_dd": 30.0,  # smaller DD
            "h_state": "OK",
        },
    ]
    res = l1.select_cell_validation_only(cells)
    assert res["selected"]["cell"]["id"] == "C02"


# Test 21
def test_tie_breaker_smaller_quantile_resolves_max_dd_tie():
    cells = [
        {
            "cell": {"id": "C01", "picker": l1.PICKER_PTP},
            "selected_q_percent": 5,  # smaller q
            "val_realised_sharpe": 0.10,
            "val_realised_annual_pnl": 100.0,
            "val_n_trades": 5000,
            "val_max_dd": 30.0,
            "h_state": "OK",
        },
        {
            "cell": {"id": "C02", "picker": l1.PICKER_DIFF},
            "selected_q_percent": 40,  # larger q
            "val_realised_sharpe": 0.10,
            "val_realised_annual_pnl": 100.0,
            "val_n_trades": 5000,
            "val_max_dd": 30.0,
            "h_state": "OK",
        },
    ]
    res = l1.select_cell_validation_only(cells)
    assert res["selected"]["cell"]["id"] == "C01", "smaller q% wins on final tie-breaker"


# Test 22
def test_quantile_cutoff_scalar_applied_to_test_unchanged():
    """The val-fit cutoff is applied to test as a scalar; perturbing test
    predictions does NOT change the val-fit cutoff.
    """
    rng = np.random.default_rng(7)
    score_val = rng.normal(0.0, 0.1, size=500)
    pnl_val = rng.normal(0.0, 1.0, size=500)
    score_test = rng.normal(0.0, 0.1, size=300)
    pnl_test = rng.normal(0.0, 1.0, size=300)
    res_a = l1.evaluate_quantile_family(score_val, pnl_val, score_test, pnl_test, 0.1, 0.1)
    # Perturb test predictions massively — val-fit cutoff must still be the same
    score_test_perturbed = score_test + 100.0
    res_b = l1.evaluate_quantile_family(
        score_val, pnl_val, score_test_perturbed, pnl_test, 0.1, 0.1
    )
    for ra, rb in zip(res_a, res_b, strict=True):
        assert ra["cutoff"] == pytest.approx(rb["cutoff"], abs=1e-12), (
            "val-fit cutoff must be invariant under test-prediction perturbation"
        )


# ===========================================================================
# Group 4 — Verdict routing (5 tests)
# ===========================================================================


# Test 23
def test_h1_weak_pass_when_test_spearman_above_005():
    val_selected = {
        "test_formal_spearman": 0.06,
        "test_gates": {},
        "test_realised_metrics": {"sharpe": float("nan")},
    }
    res = l1.assign_verdict(val_selected)
    assert res["h1_weak_pass"] is True
    assert res["verdict"] == "REJECT_WEAK_SIGNAL_ONLY"


# Test 24
def test_h1_weak_fail_when_test_spearman_at_or_below_005():
    val_selected = {
        "test_formal_spearman": 0.05,  # at threshold, must use strict >
        "test_gates": {},
        "test_realised_metrics": {"sharpe": float("nan")},
    }
    res = l1.assign_verdict(val_selected)
    assert res["h1_weak_pass"] is False
    assert res["verdict"] == "REJECT_NON_DISCRIMINATIVE"


# Test 25
def test_h2_requires_both_sharpe_and_ann_pnl():
    val_selected = {
        "test_formal_spearman": 0.20,
        "test_gates": {"A1": True, "A2": False, "A0": True, "A3": True, "A4": True, "A5": True},
        "test_realised_metrics": {"sharpe": 0.10},
    }
    res = l1.assign_verdict(val_selected)
    assert res["h2_pass"] is False


# Test 26
def test_h3_uses_neg_0192_baseline():
    assert pytest.approx(-0.192) == l1.H3_REFERENCE_SHARPE
    val_selected = {
        "test_formal_spearman": 0.20,
        "test_gates": {"A1": False, "A2": False},
        "test_realised_metrics": {"sharpe": -0.10},
    }
    res = l1.assign_verdict(val_selected)
    assert res["h3_pass"] is True, "Sharpe -0.10 > -0.192 → H3 PASS"


# Test 27 — 26.0c-β cannot mint ADOPT_CANDIDATE
def test_h2_pass_alone_does_not_yield_adopt_candidate_in_26_0c_beta():
    """26.0c-β cannot mint ADOPT_CANDIDATE; full A0-A5 is a separate PR.
    H2 PASS path resolves to PROMISING_BUT_NEEDS_OOS.
    """
    val_selected = {
        "test_formal_spearman": 0.20,
        "test_gates": {"A0": True, "A1": True, "A2": True, "A3": True, "A4": True, "A5": True},
        "test_realised_metrics": {"sharpe": 0.10},
    }
    res = l1.assign_verdict(val_selected)
    assert res["h2_pass"] is True
    assert res["verdict"] != "ADOPT_CANDIDATE"
    assert res["verdict"] == "PROMISING_BUT_NEEDS_OOS"
    assert res["h_state"] == "H2_PASS_AWAITS_A0_A5"


# ===========================================================================
# Group 5 — Diagnostic-only column prohibition (4 tests)
# ===========================================================================


# Test 28
def test_concentration_high_flag_is_diagnostic_only():
    """26.0c-α §9.2 binding: CONCENTRATION_HIGH flag NOT consulted by
    select_cell_validation_only or assign_verdict.
    """
    sel_src = inspect.getsource(l1.select_cell_validation_only)
    assert "concentration_high" not in sel_src
    assert "top_pair_share" not in sel_src

    verdict_src = inspect.getsource(l1.assign_verdict)
    assert "concentration_high" not in verdict_src
    assert "top_pair_share" not in verdict_src

    # Sanity: the flag itself fires correctly on a synthetic input
    df = pd.DataFrame({"pair": ["USD_JPY"] * 90 + ["EUR_USD"] * 10})
    traded_mask = np.ones(100, dtype=bool)
    result = l1.compute_pair_concentration(df, traded_mask)
    assert result["concentration_high"] is True

    df_balanced = pd.DataFrame({"pair": [f"P_{i % 10}" for i in range(100)]})
    res2 = l1.compute_pair_concentration(df_balanced, traded_mask)
    assert res2["concentration_high"] is False


# Test 29
def test_absolute_threshold_results_excluded_from_cell_selection():
    """absolute_best / absolute_all must NOT enter select_cell_validation_only."""
    src = inspect.getsource(l1.select_cell_validation_only)
    assert "absolute_best" not in src
    assert "absolute_all" not in src
    # Sanity: absolute candidates are defined for both pickers
    assert l1.ABSOLUTE_THRESHOLDS_PTP == (0.30, 0.40, 0.45, 0.50)
    assert l1.ABSOLUTE_THRESHOLDS_DIFF == (0.0, 0.05, 0.10, 0.15)


# Test 30
def test_classification_diagnostics_not_used_in_h1():
    """H1 binding (26.0c-α §6.1) = Spearman(score, realised_pnl), NOT AUC/κ/logloss."""
    src = inspect.getsource(l1.assign_verdict)
    # H1 must reference test_formal_spearman, NOT AUC / cohen_kappa / multiclass_logloss
    assert "test_formal_spearman" in src
    assert "auc_tp_ovr" not in src
    assert "cohen_kappa" not in src
    assert "multiclass_logloss" not in src
    assert "per_class_accuracy" not in src
    assert "confusion_matrix" not in src


# Test 31
def test_isotonic_appendix_raises_not_implemented_by_default():
    """Per 26.0c-α §4.3: isotonic stub raises NotImplementedError with binding rationale."""
    with pytest.raises(NotImplementedError) as exc_info:
        l1.compute_isotonic_diagnostic_appendix()
    msg = str(exc_info.value).lower()
    assert "deferred" in msg
    assert "26.0c-" in str(exc_info.value)


# ===========================================================================
# Group 6 — End-to-end + comparison (4 tests)
# ===========================================================================


# Test 32
def test_formal_grid_has_two_cells_two_pickers_raw_only():
    """26.0c-α §7 binding: 2 formal cells, 2 pickers, raw probabilities only."""
    cells = l1.build_cells()
    assert len(cells) == 2
    pickers = {c["picker"] for c in cells}
    assert pickers == {l1.PICKER_PTP, l1.PICKER_DIFF}
    cell_ids = {c["id"] for c in cells}
    assert cell_ids == {"C01", "C02"}
    # No isotonic / calibration field in formal cells
    for c in cells:
        assert "calibration" not in c
        assert "isotonic" not in c


# Test 33
def test_eval_report_writer_includes_l1_vs_l2_vs_l3_section(tmp_path):
    """write_eval_report includes the mandatory L-1 vs L-2 vs L-3 comparison section."""
    src = inspect.getsource(l1.write_eval_report)
    assert "L-1 vs L-2 vs L-3 comparison" in src
    assert "26.0c-α §9.6" in src
    # The L-3 baseline must reference PR #303 fixed values
    assert "-0.2232" in src or "l3_val_sharpe" in src


# Test 34
def test_realised_pnl_cache_is_cell_independent_and_inherited():
    """D-1 binding: realised-PnL cache uses inherited harness; not mid-to-mid;
    cache does not depend on picker / cutoff / calibration.
    """
    sig = inspect.signature(l1.precompute_realised_pnl_per_row)
    param_names = set(sig.parameters.keys())
    # Cache function takes only df + pair_runtime_map (cell-independent)
    assert "picker" not in param_names
    assert "cutoff" not in param_names
    assert "calibration" not in param_names
    # And does NOT expose mid_to_mid / spread_factor knobs
    assert "mid_to_mid" not in param_names
    assert "spread_factor" not in param_names
    # The cache must reference the inherited L-2 / 25.0b module
    cache_src = inspect.getsource(l1.precompute_realised_pnl_per_row)
    assert "_compute_realised_barrier_pnl" in cache_src


# Test 35 — sanity probe halt path
def test_sanity_probe_class_share_threshold_and_pair_threshold_constants():
    """Sanity-probe halt thresholds match the design memo §10 binding."""
    assert l1.SANITY_MIN_CLASS_SHARE == 0.01
    assert l1.SANITY_MAX_PER_PAIR_TIME_SHARE == 0.99


# ===========================================================================
# Additional invariants (not in 35-test plan but useful guards)
# ===========================================================================


def test_lightgbm_uses_multiclass_balanced_config():
    cfg = l1.LIGHTGBM_FIXED_CONFIG
    assert cfg["objective"] == "multiclass"
    assert cfg["num_class"] == 3
    assert cfg["class_weight"] == "balanced"
    assert cfg["n_estimators"] == 200
    assert cfg["learning_rate"] == 0.03
    assert cfg["num_leaves"] == 31
    assert cfg["max_depth"] == 4
    assert cfg["min_child_samples"] == 100
    assert cfg["subsample"] == 0.8
    assert cfg["colsample_bytree"] == 0.8
    assert cfg["random_state"] == 42


def test_quantile_threshold_family_has_5_candidates():
    assert l1.THRESHOLDS_QUANTILE_PERCENTS == (5, 10, 20, 30, 40)
    assert len(l1.THRESHOLDS_QUANTILE_PERCENTS) == 5


def test_no_diagnostic_columns_in_feature_set():
    prohibited = set(l1.PROHIBITED_DIAGNOSTIC_COLUMNS)
    feature_cols = set(l1.CATEGORICAL_COLS)
    assert prohibited.isdisjoint(feature_cols)
    assert set(l1.CATEGORICAL_COLS) == {"pair", "direction"}


def test_picker_ptp_validates_shape():
    with pytest.raises(ValueError):
        l1.compute_picker_score_ptp(np.zeros((5, 2)))  # not 3 classes


def test_picker_diff_validates_shape():
    with pytest.raises(ValueError):
        l1.compute_picker_score_diff(np.zeros((5, 2)))


def test_aggregate_cross_cell_no_auto_resolve_when_disagree():
    """Per 26.0c-α §7.2 binding: cells disagree → split (no auto-resolve)."""
    # Two cells with deliberately different verdicts (one H1 PASS, one H1 FAIL)
    cell_a = {
        "cell": {"id": "C01", "picker": l1.PICKER_PTP},
        "h_state": "OK",
        "test_formal_spearman": 0.20,
        "test_gates": {"A1": False, "A2": False},
        "test_realised_metrics": {"sharpe": -0.05},
    }
    cell_b = {
        "cell": {"id": "C02", "picker": l1.PICKER_DIFF},
        "h_state": "OK",
        "test_formal_spearman": 0.02,
        "test_gates": {},
        "test_realised_metrics": {"sharpe": -0.25},
    }
    agg = l1.aggregate_cross_cell_verdict([cell_a, cell_b])
    assert agg["agree"] is False
    assert len(agg["branches"]) == 2
    assert agg["aggregate_verdict"] == "SPLIT_VERDICT_ROUTE_TO_REVIEW"


def test_aggregate_cross_cell_agree_returns_shared_verdict():
    """When both cells produce the same verdict, aggregate equals that verdict."""
    cell_a = {
        "cell": {"id": "C01", "picker": l1.PICKER_PTP},
        "h_state": "OK",
        "test_formal_spearman": 0.02,
        "test_gates": {},
        "test_realised_metrics": {"sharpe": -0.25},
    }
    cell_b = {
        "cell": {"id": "C02", "picker": l1.PICKER_DIFF},
        "h_state": "OK",
        "test_formal_spearman": 0.01,
        "test_gates": {},
        "test_realised_metrics": {"sharpe": -0.30},
    }
    agg = l1.aggregate_cross_cell_verdict([cell_a, cell_b])
    assert agg["agree"] is True
    assert agg["aggregate_verdict"] == "REJECT_NON_DISCRIMINATIVE"


def test_h3_baseline_constant_phase25_best_minus_0192():
    assert pytest.approx(-0.192) == l1.H3_REFERENCE_SHARPE


def test_lightgbm_pipeline_categorical_only_features():
    """Minimum feature set per 26.0c-α §1: pair + direction only."""
    pipe = l1.build_pipeline_lightgbm_multiclass()
    transformer = pipe.named_steps["pre"]
    cat_cols = transformer.transformers[0][2]
    assert cat_cols == ["pair", "direction"]


def test_mid_to_mid_pnl_is_diagnostic_only_not_used_in_evaluate_cell():
    """D-1 binding: mid-to-mid PnL is NEVER the formal realised-PnL metric.

    evaluate_cell must consume pnl_val_full and pnl_test_full (inherited harness
    cache), NOT compute_mid_to_mid_pnl_diagnostic.
    """
    src = inspect.getsource(l1.evaluate_cell)
    assert "compute_mid_to_mid_pnl_diagnostic" not in src
    # The cache used in evaluate_cell must be the inherited harness output
    assert "pnl_val_full" in src
    assert "pnl_test_full" in src
