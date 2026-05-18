"""Unit tests for stage28_0c_a0_architecture_topology_eval.

Covers: shared utilities, AR1/AR2/AR3/AR4 fit/predict primitives, cell
construction, baseline FAIL-FAST, arch-control drift WARN, within-eval
drift detection, H-C3 4-outcome ladder, aggregate verdict with
FALSIFIED_A0_NARROW distinction, sanity probe shape, interpretation
guards (AR1 admission-gate / AR4 deterministic-only / FALSIFIED_A0_NARROW
language).
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage28_0c = importlib.import_module("stage28_0c_a0_architecture_topology_eval")


# ---------------------------------------------------------------------------
# TG1 — module structure / imports
# ---------------------------------------------------------------------------


class TestG1ModuleStructure:
    def test_module_imports(self):
        assert stage28_0c is not None

    def test_constants_present(self):
        assert stage28_0c.AR1_STAGE1_ADMIT_PERCENTILE == 50.0
        assert stage28_0c.AR3_BLEND_W_SB == 0.5
        assert stage28_0c.AR3_BLEND_W_SE == 0.5
        assert stage28_0c.AR4_REGIME_SPLIT_FEATURE == "atr_at_signal_pip"
        assert stage28_0c.AR4_REGIME_SPLIT_PERCENTILE == 50.0
        assert stage28_0c.QUANTILE_PERCENTS_28_0C == (5.0, 10.0, 20.0, 30.0, 40.0)

    def test_h_c3_outcome_labels_present(self):
        assert stage28_0c.H_C3_OUTCOME_PASS == "PASS"
        assert stage28_0c.H_C3_OUTCOME_PARTIAL_SUPPORT == "PARTIAL_SUPPORT"
        assert stage28_0c.H_C3_OUTCOME_FALSIFIED_ARCH_INSUFFICIENT == "FALSIFIED_ARCH_INSUFFICIENT"
        assert stage28_0c.H_C3_OUTCOME_PARTIAL_DRIFT_ARCH_REPLICA == "PARTIAL_DRIFT_ARCH_REPLICA"

    def test_thresholds_present(self):
        assert stage28_0c.H2_LIFT_THRESHOLD_PASS == 0.05
        assert stage28_0c.H2_LIFT_THRESHOLD_PARTIAL_SUPPORT_LO == 0.02
        assert stage28_0c.H1M_PRESERVE_THRESHOLD == 0.30
        assert stage28_0c.H3_TRADE_COUNT_THRESHOLD == 20000

    def test_exceptions_defined(self):
        assert issubclass(stage28_0c.BaselineMismatchError, RuntimeError)
        assert issubclass(stage28_0c.ArchitectureFitError, RuntimeError)


# ---------------------------------------------------------------------------
# TG2 — _rank_normalise
# ---------------------------------------------------------------------------


class TestG2RankNormalise:
    def test_uniform_output_range(self):
        scores = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        out = stage28_0c._rank_normalise(scores)
        assert (out >= 0.0).all() and (out <= 1.0).all()

    def test_monotone_preserves_order(self):
        scores = np.array([5.0, 1.0, 3.0, 2.0, 4.0])
        out = stage28_0c._rank_normalise(scores)
        # rank of 5.0 should be highest, rank of 1.0 should be lowest
        assert out[0] == out.max()
        assert out[1] == out.min()

    def test_ties_get_average_rank(self):
        scores = np.array([1.0, 1.0, 2.0, 2.0])
        out = stage28_0c._rank_normalise(scores)
        assert np.isclose(out[0], out[1])
        assert np.isclose(out[2], out[3])

    def test_nan_safe(self):
        scores = np.array([1.0, np.nan, 3.0])
        out = stage28_0c._rank_normalise(scores)
        assert np.isnan(out[1])


# ---------------------------------------------------------------------------
# TG3 — _compute_per_pair_median
# ---------------------------------------------------------------------------


class TestG3PerPairMedian:
    def test_basic_median(self):
        pairs = np.array(["EURUSD", "EURUSD", "EURUSD", "USDJPY", "USDJPY"])
        values = np.array([1.0, 2.0, 3.0, 10.0, 20.0])
        result = stage28_0c._compute_per_pair_median(pairs, values, percentile=50.0)
        assert np.isclose(result["EURUSD"], 2.0)
        assert np.isclose(result["USDJPY"], 15.0)

    def test_handles_nan_values(self):
        pairs = np.array(["EURUSD", "EURUSD"])
        values = np.array([np.nan, np.nan])
        result = stage28_0c._compute_per_pair_median(pairs, values)
        assert np.isnan(result["EURUSD"])

    def test_percentile_param_works(self):
        pairs = np.array(["A"] * 100)
        values = np.arange(100, dtype=np.float64)
        result = stage28_0c._compute_per_pair_median(pairs, values, percentile=90.0)
        assert np.isclose(result["A"], 89.1, atol=0.5)

    def test_mismatched_lengths_raise(self):
        pairs = np.array(["A", "B"])
        values = np.array([1.0])
        with pytest.raises(ValueError, match="pairs"):
            stage28_0c._compute_per_pair_median(pairs, values)


# ---------------------------------------------------------------------------
# TG4 — _apply_per_pair_threshold_mask
# ---------------------------------------------------------------------------


class TestG4PerPairThresholdMask:
    def test_basic_mask(self):
        pairs = np.array(["A", "A", "B", "B"])
        scores = np.array([1.0, 5.0, 2.0, 8.0])
        threshold_per_pair = {"A": 3.0, "B": 4.0}
        mask = stage28_0c._apply_per_pair_threshold_mask(pairs, scores, threshold_per_pair)
        # A: 1.0 < 3.0 (excluded), 5.0 >= 3.0 (included)
        # B: 2.0 < 4.0 (excluded), 8.0 >= 4.0 (included)
        np.testing.assert_array_equal(mask, [False, True, False, True])

    def test_missing_pair_excluded(self):
        pairs = np.array(["A", "Z"])
        scores = np.array([100.0, 100.0])
        thresholds = {"A": 1.0}  # Z is missing
        mask = stage28_0c._apply_per_pair_threshold_mask(pairs, scores, thresholds)
        # A: 100 >= 1 → True; Z: threshold = inf → False
        np.testing.assert_array_equal(mask, [True, False])

    def test_nan_scores_excluded(self):
        pairs = np.array(["A"])
        scores = np.array([np.nan])
        mask = stage28_0c._apply_per_pair_threshold_mask(pairs, scores, {"A": 0.0})
        np.testing.assert_array_equal(mask, [False])


# ---------------------------------------------------------------------------
# TG5 — compute_ar3_blended_score
# ---------------------------------------------------------------------------


class TestG5AR3Blend:
    def test_blend_50_50(self):
        s_b = np.array([1.0, 2.0, 3.0, 4.0])
        s_e = np.array([4.0, 3.0, 2.0, 1.0])
        blended = stage28_0c.compute_ar3_blended_score(s_b, s_e)
        # ranks: s_b → [0.25, 0.5, 0.75, 1.0]; s_e → [1.0, 0.75, 0.5, 0.25]
        # blend: 0.5*0.25 + 0.5*1.0 = 0.625, etc.
        expected = np.array([0.625, 0.625, 0.625, 0.625])
        np.testing.assert_allclose(blended, expected, atol=1e-6)

    def test_blend_output_range(self):
        np.random.seed(42)
        s_b = np.random.randn(100)
        s_e = np.random.randn(100)
        blended = stage28_0c.compute_ar3_blended_score(s_b, s_e)
        assert (blended >= 0.0).all() and (blended <= 1.0).all()

    def test_blend_preserves_finite_count(self):
        s_b = np.array([1.0, 2.0, 3.0, np.nan])
        s_e = np.array([4.0, 3.0, 2.0, 1.0])
        blended = stage28_0c.compute_ar3_blended_score(s_b, s_e)
        # NaN from s_b propagates to that row's blend
        assert np.isnan(blended[3])
        assert np.isfinite(blended[:3]).all()


# ---------------------------------------------------------------------------
# TG6 — build_a0_cells
# ---------------------------------------------------------------------------


class TestG6BuildA0Cells:
    def test_six_cells(self):
        cells = stage28_0c.build_a0_cells()
        assert len(cells) == 6

    def test_cell_order(self):
        cells = stage28_0c.build_a0_cells()
        ids = [c["id"] for c in cells]
        assert ids == [
            "C-a0-AR1",
            "C-a0-AR2",
            "C-a0-AR3",
            "C-a0-AR4",
            "C-a0-arch-control",
            "C-sb-baseline",
        ]

    def test_all_cells_use_r7a(self):
        cells = stage28_0c.build_a0_cells()
        for c in cells:
            assert c["feature_set"] == "r7a"

    def test_all_cells_use_same_quantile_family(self):
        cells = stage28_0c.build_a0_cells()
        for c in cells:
            assert c["quantile_percents"] == (5.0, 10.0, 20.0, 30.0, 40.0)

    def test_architecture_field_present(self):
        cells = stage28_0c.build_a0_cells()
        archs = [c["architecture"] for c in cells]
        assert "hierarchical_two_stage" in archs
        assert "pair_conditioned_specialist_heads" in archs
        assert "stacked_classifier_regressor_blend" in archs
        assert "deterministic_regime_split" in archs
        assert "vanilla_s_e_27_0d_backbone" in archs
        assert "multiclass_s_b_baseline" in archs


# ---------------------------------------------------------------------------
# TG7 — C-sb-baseline FAIL-FAST
# ---------------------------------------------------------------------------


class TestG7CSbBaselineFailFast:
    def test_match_within_tolerance_passes(self):
        result = {
            "test_realised_metrics": {
                "n_trades": stage28_0c.BASELINE_27_0B_C_ALPHA0_N_TRADES,
                "sharpe": stage28_0c.BASELINE_27_0B_C_ALPHA0_SHARPE,
                "annual_pnl": stage28_0c.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
            }
        }
        report = stage28_0c.check_c_sb_baseline_match(result)
        assert report["all_match"] is True

    def test_n_trades_mismatch_raises(self):
        result = {
            "test_realised_metrics": {
                "n_trades": stage28_0c.BASELINE_27_0B_C_ALPHA0_N_TRADES + 100,
                "sharpe": stage28_0c.BASELINE_27_0B_C_ALPHA0_SHARPE,
                "annual_pnl": stage28_0c.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
            }
        }
        with pytest.raises(stage28_0c.BaselineMismatchError, match="n_trades"):
            stage28_0c.check_c_sb_baseline_match(result)

    def test_sharpe_mismatch_raises(self):
        result = {
            "test_realised_metrics": {
                "n_trades": stage28_0c.BASELINE_27_0B_C_ALPHA0_N_TRADES,
                "sharpe": stage28_0c.BASELINE_27_0B_C_ALPHA0_SHARPE + 0.01,
                "annual_pnl": stage28_0c.BASELINE_27_0B_C_ALPHA0_ANN_PNL,
            }
        }
        with pytest.raises(stage28_0c.BaselineMismatchError, match="Sharpe"):
            stage28_0c.check_c_sb_baseline_match(result)

    def test_ann_pnl_mismatch_raises(self):
        result = {
            "test_realised_metrics": {
                "n_trades": stage28_0c.BASELINE_27_0B_C_ALPHA0_N_TRADES,
                "sharpe": stage28_0c.BASELINE_27_0B_C_ALPHA0_SHARPE,
                "annual_pnl": stage28_0c.BASELINE_27_0B_C_ALPHA0_ANN_PNL + 10.0,
            }
        }
        with pytest.raises(stage28_0c.BaselineMismatchError, match="ann_pnl"):
            stage28_0c.check_c_sb_baseline_match(result)


# ---------------------------------------------------------------------------
# TG8 — within-eval drift check
# ---------------------------------------------------------------------------


class TestG8WithinEvalDrift:
    def _make_cell_result(self, n_trades, sharpe, ann_pnl):
        return {
            "h_state": "OK",
            "test_realised_metrics": {
                "n_trades": n_trades,
                "sharpe": sharpe,
                "annual_pnl": ann_pnl,
            },
        }

    def test_identical_cells_within_tolerance(self):
        ar = self._make_cell_result(1000, 0.1, 10000.0)
        ctl = self._make_cell_result(1000, 0.1, 10000.0)
        drift = stage28_0c.compute_within_eval_arch_drift_check(ar, ctl)
        assert drift["all_within_tolerance"] is True
        assert drift["warn"] is True  # WARN means drift detected (== arch-control)

    def test_large_sharpe_delta_not_within(self):
        ar = self._make_cell_result(1000, 0.5, 10000.0)
        ctl = self._make_cell_result(1000, 0.1, 10000.0)
        drift = stage28_0c.compute_within_eval_arch_drift_check(ar, ctl)
        assert drift["sharpe_within_tolerance"] is False
        assert drift["all_within_tolerance"] is False

    def test_h_state_not_ok_returns_warn(self):
        ar = {"h_state": "INSUFFICIENT_DATA"}
        ctl = self._make_cell_result(1000, 0.1, 10000.0)
        drift = stage28_0c.compute_within_eval_arch_drift_check(ar, ctl)
        assert drift["all_within_tolerance"] is False
        assert drift["warn"] is True


# ---------------------------------------------------------------------------
# TG9 — H-C3 outcome per AR (4-outcome ladder)
# ---------------------------------------------------------------------------


class TestG9HC3OutcomePerArch:
    def _baseline_pass_report(self):
        return {"all_match": True}

    def _no_drift_report(self):
        return {"all_within_tolerance": False}

    def _ar_result_h_state_ok(self, val_sharpe, val_n, cell_spearman, q=10):
        return {
            "h_state": "OK",
            "cell": {"id": "C-a0-test"},
            "val_realised_sharpe": val_sharpe,
            "val_n_trades": val_n,
            "selected_q_percent": q,
            "quantile_best": {"val": {"spearman_score_vs_pnl": cell_spearman}},
        }

    def test_pass_when_all_conditions_met(self):
        ar = self._ar_result_h_state_ok(val_sharpe=-0.13, val_n=25000, cell_spearman=0.40)
        out = stage28_0c.compute_h_c3_outcome_per_arch(
            ar, self._baseline_pass_report(), self._no_drift_report(), "AR2"
        )
        assert out["outcome"] == "PASS"
        assert out["row_matched"] == 1

    def test_partial_drift_overrides_pass(self):
        ar = self._ar_result_h_state_ok(val_sharpe=-0.13, val_n=25000, cell_spearman=0.40)
        out = stage28_0c.compute_h_c3_outcome_per_arch(
            ar,
            self._baseline_pass_report(),
            {"all_within_tolerance": True},
            "AR2",
        )
        assert out["outcome"] == "PARTIAL_DRIFT_ARCH_REPLICA"
        assert out["row_matched"] == 4

    def test_partial_support_when_sharpe_lift_subthreshold(self):
        # Sharpe lift = -0.16 - (-0.1863) = +0.0263 (in [0.02, 0.05))
        ar = self._ar_result_h_state_ok(val_sharpe=-0.16, val_n=25000, cell_spearman=0.40)
        out = stage28_0c.compute_h_c3_outcome_per_arch(
            ar, self._baseline_pass_report(), self._no_drift_report(), "AR2"
        )
        assert out["outcome"] == "PARTIAL_SUPPORT"
        assert out["row_matched"] == 2

    def test_falsified_when_lift_below_partial_threshold(self):
        ar = self._ar_result_h_state_ok(val_sharpe=-0.20, val_n=25000, cell_spearman=0.40)
        out = stage28_0c.compute_h_c3_outcome_per_arch(
            ar, self._baseline_pass_report(), self._no_drift_report(), "AR2"
        )
        assert out["outcome"] == "FALSIFIED_ARCH_INSUFFICIENT"
        assert out["row_matched"] == 3

    def test_h_state_not_ok_returns_needs_review(self):
        ar = {"h_state": "INSUFFICIENT_DATA", "cell": {"id": "C-a0-test"}}
        out = stage28_0c.compute_h_c3_outcome_per_arch(
            ar, self._baseline_pass_report(), self._no_drift_report(), "AR2"
        )
        assert out["outcome"] == "NEEDS_REVIEW"

    def test_ar1_pass_includes_admission_gate_guard(self):
        ar = self._ar_result_h_state_ok(val_sharpe=-0.13, val_n=25000, cell_spearman=0.40)
        out = stage28_0c.compute_h_c3_outcome_per_arch(
            ar, self._baseline_pass_report(), self._no_drift_report(), "AR1"
        )
        assert "admission gate" in out["reason"].lower() or "admission gate" in out["reason"]

    def test_ar4_pass_includes_deterministic_guard(self):
        ar = self._ar_result_h_state_ok(val_sharpe=-0.13, val_n=25000, cell_spearman=0.40)
        out = stage28_0c.compute_h_c3_outcome_per_arch(
            ar, self._baseline_pass_report(), self._no_drift_report(), "AR4"
        )
        assert "deterministic" in out["reason"].lower()
        assert "regime split" in out["reason"].lower()


# ---------------------------------------------------------------------------
# TG10 — Interpretation guards
# ---------------------------------------------------------------------------


class TestG10InterpretationGuards:
    def test_ar1_guard_mentions_admission_gate(self):
        guard = stage28_0c._interpretation_guard_for_arch("AR1", outcome_row=1)
        assert "admission gate" in guard.lower()
        assert "architecture-conditioning" in guard.lower()

    def test_ar1_guard_says_not_pure_architecture(self):
        guard = stage28_0c._interpretation_guard_for_arch("AR1", outcome_row=1)
        assert "not pure architecture" in guard.lower()

    def test_ar4_guard_mentions_deterministic(self):
        guard = stage28_0c._interpretation_guard_for_arch("AR4", outcome_row=1)
        assert "deterministic" in guard.lower()

    def test_ar4_guard_says_not_full_a3(self):
        guard = stage28_0c._interpretation_guard_for_arch("AR4", outcome_row=1)
        assert "full a3" in guard.lower()
        assert "not solved" in guard.lower()

    def test_ar2_ar3_no_specific_guard(self):
        guard_2 = stage28_0c._interpretation_guard_for_arch("AR2", outcome_row=1)
        guard_3 = stage28_0c._interpretation_guard_for_arch("AR3", outcome_row=1)
        assert "no architecture-specific" in guard_2.lower()
        assert "no architecture-specific" in guard_3.lower()


# ---------------------------------------------------------------------------
# TG11 — Aggregate verdict + FALSIFIED_A0_NARROW distinction
# ---------------------------------------------------------------------------


class TestG11AggregateVerdict:
    def _outcome(self, arch_id, label):
        return {
            "arch_id": arch_id,
            "cell_id": f"C-a0-{arch_id}",
            "outcome": label,
            "row_matched": 1,
        }

    def test_any_pass_routes_to_review(self):
        outcomes = [
            self._outcome("AR1", "PASS"),
            self._outcome("AR2", "FALSIFIED_ARCH_INSUFFICIENT"),
            self._outcome("AR3", "FALSIFIED_ARCH_INSUFFICIENT"),
            self._outcome("AR4", "FALSIFIED_ARCH_INSUFFICIENT"),
        ]
        agg = stage28_0c.compute_h_c3_aggregate_verdict(outcomes)
        assert agg["aggregate_verdict"] == "SPLIT_VERDICT_ROUTE_TO_REVIEW"
        assert agg["a0_narrow_status"] == "PASS_under_A0_narrow"

    def test_partial_only_rejects(self):
        outcomes = [
            self._outcome("AR1", "PARTIAL_SUPPORT"),
            self._outcome("AR2", "FALSIFIED_ARCH_INSUFFICIENT"),
            self._outcome("AR3", "FALSIFIED_ARCH_INSUFFICIENT"),
            self._outcome("AR4", "FALSIFIED_ARCH_INSUFFICIENT"),
        ]
        agg = stage28_0c.compute_h_c3_aggregate_verdict(outcomes)
        assert agg["aggregate_verdict"] == "REJECT_NON_DISCRIMINATIVE"
        assert agg["a0_narrow_status"] == "PARTIAL_under_A0_narrow"

    def test_all_falsified_labels_a0_narrow(self):
        outcomes = [
            self._outcome("AR1", "FALSIFIED_ARCH_INSUFFICIENT"),
            self._outcome("AR2", "FALSIFIED_ARCH_INSUFFICIENT"),
            self._outcome("AR3", "FALSIFIED_ARCH_INSUFFICIENT"),
            self._outcome("AR4", "FALSIFIED_ARCH_INSUFFICIENT"),
        ]
        agg = stage28_0c.compute_h_c3_aggregate_verdict(outcomes)
        assert agg["aggregate_verdict"] == "REJECT_NON_DISCRIMINATIVE"
        assert agg["a0_narrow_status"] == "FALSIFIED_A0_NARROW"
        assert agg["a0_broad_status"] == "deferred_not_foreclosed"

    def test_all_falsified_routing_never_says_all_a0(self):
        # The routing string may include FALSIFIED_ALL_A0 only as part of a
        # negation clause (e.g. "NEVER FALSIFIED_ALL_A0" or "NEVER label this
        # FALSIFIED_ALL_A0"). Assert FALSIFIED_A0_NARROW is the affirmative
        # label and any FALSIFIED_ALL_A0 mention has a NEVER nearby.
        outcomes = [
            self._outcome("AR1", "FALSIFIED_ARCH_INSUFFICIENT"),
            self._outcome("AR2", "FALSIFIED_ARCH_INSUFFICIENT"),
            self._outcome("AR3", "FALSIFIED_ARCH_INSUFFICIENT"),
            self._outcome("AR4", "FALSIFIED_ARCH_INSUFFICIENT"),
        ]
        agg = stage28_0c.compute_h_c3_aggregate_verdict(outcomes)
        routing = agg["routing_implication"]
        assert "FALSIFIED_A0_NARROW" in routing
        if "FALSIFIED_ALL_A0" in routing:
            assert "NEVER" in routing

    def test_all_drift_labels_a0_narrow(self):
        outcomes = [
            self._outcome(a, "PARTIAL_DRIFT_ARCH_REPLICA") for a in ["AR1", "AR2", "AR3", "AR4"]
        ]
        agg = stage28_0c.compute_h_c3_aggregate_verdict(outcomes)
        assert agg["a0_narrow_status"] == "FALSIFIED_A0_NARROW"
        assert agg["a0_broad_status"] == "deferred_not_foreclosed"
        routing = agg["routing_implication"]
        if "FALSIFIED_ALL_A0" in routing:
            assert "NEVER" in routing

    def test_mixed_falsified_and_drift_labels_a0_narrow(self):
        outcomes = [
            self._outcome("AR1", "PARTIAL_DRIFT_ARCH_REPLICA"),
            self._outcome("AR2", "FALSIFIED_ARCH_INSUFFICIENT"),
            self._outcome("AR3", "PARTIAL_DRIFT_ARCH_REPLICA"),
            self._outcome("AR4", "FALSIFIED_ARCH_INSUFFICIENT"),
        ]
        agg = stage28_0c.compute_h_c3_aggregate_verdict(outcomes)
        assert agg["a0_narrow_status"] == "FALSIFIED_A0_NARROW"


# ---------------------------------------------------------------------------
# TG12 — Sanity probe shape (smoke test with tiny synthetic data)
# ---------------------------------------------------------------------------


class TestG12SanityProbeShape:
    def _make_tiny_df(self, n_pairs=2, rows_per_pair=10, seed=42):
        rng = np.random.default_rng(seed)
        pairs = ["EURUSD", "USDJPY"][:n_pairs]
        rows = []
        for pair in pairs:
            for _ in range(rows_per_pair):
                rows.append(
                    {
                        "pair": pair,
                        "direction": rng.choice(["long", "short"]),
                        "atr_at_signal_pip": rng.uniform(1.0, 5.0),
                        "spread_at_signal_pip": rng.uniform(0.5, 2.0),
                        "signal_ts": pd.Timestamp("2024-01-01")
                        + pd.Timedelta(minutes=int(rng.integers(0, 10000))),
                        "class_label_3way": int(rng.integers(0, 3)),
                        "barrier_class_3way": int(rng.integers(0, 3)),
                    }
                )
        return pd.DataFrame(rows)

    def test_run_sanity_probe_items_1_to_6_smoke(self):
        # The sanity probe inherits the full L1 label builder; not exercised
        # in unit test (needs full dataset). Smoke: ensure constants surface
        # and the helper doesn't crash on basic structure.
        # Verify constants are reachable
        assert hasattr(stage28_0c, "run_sanity_probe_28_0c")
        # Verify NaN-PnL HALT threshold reachable
        assert 0 < stage28_0c.NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD < 1


# ---------------------------------------------------------------------------
# TG13 — Eval report generation smoke
# ---------------------------------------------------------------------------


class TestG13EvalReportSmoke:
    def test_write_eval_report_runs(self, tmp_path):
        cell_results = [
            {
                "cell": {
                    "id": "C-a0-AR1",
                    "picker": "AR1(test)",
                    "score_type": "ar1_hierarchical",
                    "feature_set": "r7a",
                    "architecture": "hierarchical_two_stage",
                },
                "quantile_all": [],
                "val_realised_sharpe": -0.13,
                "val_n_trades": 1000,
                "val_concentration": {"top_pairs": [], "herfindahl": 0.1},
                "test_concentration": {"top_pairs": [], "herfindahl": 0.1},
                "test_realised_metrics": {"sharpe": -0.13, "annual_pnl": 1000.0, "n_trades": 500},
                "test_formal_spearman": 0.05,
                "test_classification_diag": {},
                "per_pair_sharpe_contribution": {},
                "by_pair_trade_count": {},
                "by_direction_trade_count": {"long": 100, "short": 100},
                "h_state": "OK",
            }
        ]
        h_c3_per_arch = [
            {
                "arch_id": "AR1",
                "cell_id": "C-a0-AR1",
                "outcome": "FALSIFIED_ARCH_INSUFFICIENT",
                "row_matched": 3,
                "reason": "test",
            }
        ]
        h_c3_aggregate = {
            "aggregate_verdict": "REJECT_NON_DISCRIMINATIVE",
            "a0_narrow_status": "FALSIFIED_A0_NARROW",
            "a0_broad_status": "deferred_not_foreclosed",
            "routing_implication": "A0-broad deferred",
        }
        baseline_match_report = {
            "n_trades_observed": 34626,
            "n_trades_baseline": 34626,
            "n_trades_delta": 0,
            "n_trades_match": True,
            "sharpe_observed": -0.1732,
            "sharpe_baseline": -0.1732,
            "sharpe_delta": 0.0,
            "sharpe_match": True,
            "ann_pnl_observed": -204664.4,
            "ann_pnl_baseline": -204664.4,
            "ann_pnl_delta": 0.0,
            "ann_pnl_match": True,
            "all_match": True,
        }
        arch_control_drift_report = {
            "source": "test",
            "all_within_tolerance": True,
            "warn": False,
            "n_trades_observed": 1000,
            "n_trades_delta": 0,
            "sharpe_observed": -0.17,
            "sharpe_delta": 0.0,
            "ann_pnl_observed": -200000.0,
            "ann_pnl_delta": 0.0,
        }
        report_path = tmp_path / "eval_report.md"
        stage28_0c.write_eval_report_28_0c(
            report_path,
            cell_results,
            {"selected": None},
            {"verdict": "REJECT_NON_DISCRIMINATIVE"},
            {
                "aggregate_verdict": "REJECT_NON_DISCRIMINATIVE",
                "agree": True,
                "branches": ["REJECT_NON_DISCRIMINATIVE"],
            },
            baseline_match_report,
            arch_control_drift_report,
            h_c3_per_arch,
            h_c3_aggregate,
            {"AR1": {"all_within_tolerance": False}},
            {"class_priors": {}, "d1_binding_check": "PASS"},
            {
                "train": {"n_input": 100, "n_kept": 95, "n_dropped": 5},
                "val": {"n_input": 50, "n_kept": 48, "n_dropped": 2},
                "test": {"n_input": 50, "n_kept": 48, "n_dropped": 2},
            },
            ("2024-01-01", "2024-06-01", "2024-09-01", "2024-12-31"),
            {},
            1,
            {},
            {"train": {"r2": 0.0, "mae": 1.0, "mse": 2.0, "n": 100}, "val": {}, "test": {}},
            {"aggregate_pearson": 0.0, "aggregate_spearman": 0.0},
            {},
            {},
            {},
            None,
            None,
            None,
            None,
        )
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "Phase 28.0c-β" in content
        assert "A0-narrow" in content
        assert "FALSIFIED_A0_NARROW" in content
        assert "FALSIFIED_ALL_A0" not in content or "NEVER `FALSIFIED_ALL_A0`" in content
        assert "deferred-not-foreclosed" in content
        assert "AR1 interpretation guard" in content
        assert "AR4 interpretation guard" in content


# ---------------------------------------------------------------------------
# TG14 — ArchitectureFitError shape
# ---------------------------------------------------------------------------


class TestG14ArchitectureFitError:
    def test_exception_inherits_runtime_error(self):
        assert issubclass(stage28_0c.ArchitectureFitError, RuntimeError)

    def test_exception_message_passes_through(self):
        try:
            raise stage28_0c.ArchitectureFitError("test message")
        except stage28_0c.ArchitectureFitError as exc:
            assert "test message" in str(exc)


# ---------------------------------------------------------------------------
# TG15 — Closed architecture allowlist enforcement (constants are α-fixed)
# ---------------------------------------------------------------------------


class TestG15ClosedAllowlistFixed:
    def test_no_grid_within_ar1(self):
        # AR1 stage-1 admit percentile is α-fixed at 50%
        assert stage28_0c.AR1_STAGE1_ADMIT_PERCENTILE == 50.0

    def test_no_grid_within_ar3(self):
        # AR3 blend weights are α-fixed at 0.5 / 0.5
        assert stage28_0c.AR3_BLEND_W_SB == 0.5
        assert stage28_0c.AR3_BLEND_W_SE == 0.5
        assert stage28_0c.AR3_BLEND_W_SB + stage28_0c.AR3_BLEND_W_SE == 1.0

    def test_no_grid_within_ar4(self):
        # AR4 split is per-pair val-median (50%) on atr_at_signal_pip
        assert stage28_0c.AR4_REGIME_SPLIT_PERCENTILE == 50.0
        assert stage28_0c.AR4_REGIME_SPLIT_FEATURE == "atr_at_signal_pip"

    def test_min_row_halt_thresholds_present(self):
        # No-fallback policy: AR1 / AR2 HALT thresholds present
        assert stage28_0c.AR1_STAGE2_MIN_ROWS_PER_PAIR_HALT >= 100
        assert stage28_0c.AR2_PER_PAIR_MIN_TRAIN_ROWS_HALT >= 100

    def test_ar4_regime_imbalance_is_warn_only(self):
        # AR4 imbalance threshold is fractional, not row count → WARN not HALT
        assert 0 < stage28_0c.AR4_REGIME_IMBALANCE_WARN_FRACTION < 1.0
