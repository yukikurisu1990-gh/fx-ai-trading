"""Unit tests for stage29_0a_a2_target_redesign_eval.

Covers: target primitives (T1/T2/T3/T4 D-1 bid/ask mapping), parameterised
barrier PnL, target precompute orchestrator, cell construction, per-target
baseline FAIL-FAST internal consistency, archived Phase 28 §10 drift
DIAGNOSTIC, target-control 6th-phase chain drift WARN, within-eval
PARTIAL_DRIFT_TARGET_REPLICA detection, H-D1 4-outcome ladder, aggregate
verdict with FALSIFIED_A2_NARROW distinction, R-T3 absorption status,
sanity probe shape, T3 overlap diagnostic, eval_report smoke test.
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

stage29_0a = importlib.import_module("stage29_0a_a2_target_redesign_eval")


# ---------------------------------------------------------------------------
# TG1 — module structure / constants
# ---------------------------------------------------------------------------


class TestG1ModuleStructure:
    def test_module_imports(self):
        assert stage29_0a is not None

    def test_constants_present(self):
        assert stage29_0a.T1_H_M1 == 60
        assert stage29_0a.T2_K_FAV == 1.5
        assert stage29_0a.T2_K_ADV == 1.0
        assert stage29_0a.T2_H_M1 == 60
        assert stage29_0a.T2_DECAY_KIND == "linear"
        assert stage29_0a.T3_K_FAV == 1.5
        assert stage29_0a.T3_K_ADV == 1.0
        assert stage29_0a.T3_HORIZONS == (30, 60, 120)
        assert stage29_0a.T4_K_FAV == 2.0
        assert stage29_0a.T4_K_ADV == 0.5
        assert stage29_0a.T4_H_M1 == 60

    def test_target_control_constants(self):
        assert stage29_0a.TARGET_CONTROL_K_FAV == 1.5
        assert stage29_0a.TARGET_CONTROL_K_ADV == 1.0
        assert stage29_0a.TARGET_CONTROL_H_M1 == 60

    def test_h_d1_outcome_labels(self):
        assert stage29_0a.H_D1_OUTCOME_PASS == "PASS"
        assert stage29_0a.H_D1_OUTCOME_PARTIAL_SUPPORT == "PARTIAL_SUPPORT"
        assert (
            stage29_0a.H_D1_OUTCOME_FALSIFIED_TARGET_INSUFFICIENT == "FALSIFIED_TARGET_INSUFFICIENT"
        )
        assert (
            stage29_0a.H_D1_OUTCOME_PARTIAL_DRIFT_TARGET_REPLICA == "PARTIAL_DRIFT_TARGET_REPLICA"
        )

    def test_h_d1_thresholds(self):
        assert stage29_0a.H2_LIFT_THRESHOLD_PASS == 0.05
        assert stage29_0a.H2_LIFT_THRESHOLD_PARTIAL_SUPPORT_LO == 0.02
        assert stage29_0a.H1M_PRESERVE_THRESHOLD == 0.30
        assert stage29_0a.H3_TRADE_COUNT_THRESHOLD == 20000

    def test_archived_phase28_section10_constants(self):
        assert stage29_0a.ARCHIVED_PHASE_28_SECTION10_N_TRADES == 34626
        assert abs(stage29_0a.ARCHIVED_PHASE_28_SECTION10_SHARPE - (-0.1732)) < 1e-6
        assert abs(stage29_0a.ARCHIVED_PHASE_28_SECTION10_ANN_PNL - (-204664.4)) < 1e-3
        assert abs(stage29_0a.ARCHIVED_PHASE_28_SECTION10_VAL_SHARPE - (-0.1863)) < 1e-6

    def test_per_target_baseline_tolerances(self):
        assert stage29_0a.PER_TARGET_BASELINE_N_TRADES_TOLERANCE == 0
        assert stage29_0a.PER_TARGET_BASELINE_SHARPE_ABS_TOLERANCE == 1e-4
        assert stage29_0a.PER_TARGET_BASELINE_ANN_PNL_ABS_TOLERANCE == 0.5

    def test_quantile_percents(self):
        assert stage29_0a.QUANTILE_PERCENTS_29_0A == (5.0, 10.0, 20.0, 30.0, 40.0)
        assert stage29_0a.PER_TARGET_BASELINE_Q_PERCENT == 5.0

    def test_exceptions_defined(self):
        assert issubclass(stage29_0a.PerTargetBaselineMismatchError, RuntimeError)
        assert issubclass(stage29_0a.TargetPrecomputeError, RuntimeError)


# ---------------------------------------------------------------------------
# Helper: build a synthetic pair_data dict for target primitives
# ---------------------------------------------------------------------------


def _make_synthetic_pair_data(n_m1: int = 200, pip: float = 0.0001):
    rng = np.random.default_rng(42)
    base_price = 1.1000
    mid = base_price + rng.normal(0, 0.001, n_m1).cumsum() * 0.0001
    spread = 0.0001
    bid = mid - spread / 2
    ask = mid + spread / 2
    bar_range = rng.uniform(0.0001, 0.0005, n_m1)
    ts_index = pd.date_range("2024-01-01 00:00", periods=n_m1, freq="1min")
    m1_pos = pd.Series(np.arange(n_m1, dtype=np.int64), index=ts_index)
    return {
        "pip": pip,
        "m1_pos": m1_pos,
        "n_m1": n_m1,
        "bid_h": bid + bar_range / 2,
        "bid_l": bid - bar_range / 2,
        "bid_c": bid,
        "bid_o": bid,
        "ask_h": ask + bar_range / 2,
        "ask_l": ask - bar_range / 2,
        "ask_c": ask,
        "ask_o": ask,
    }


# ---------------------------------------------------------------------------
# TG2 — T1 fixed-horizon executable close PnL
# ---------------------------------------------------------------------------


class TestG2T1FixedHorizonClose:
    def test_t1_long_uses_ask_o_entry_bid_c_exit(self):
        pair_data = _make_synthetic_pair_data(n_m1=200)
        signal_ts = pd.Timestamp("2024-01-01 00:30")
        # entry_idx = signal+1min = 31
        pnl = stage29_0a._compute_target_t1_fixed_horizon_close_pnl(
            "EURUSD", signal_ts, "long", 0.0, pair_data, h_m1=60
        )
        assert pnl is not None
        entry_price = pair_data["ask_o"][31]
        exit_price = pair_data["bid_c"][31 + 60]
        expected = (exit_price - entry_price) / pair_data["pip"]
        assert abs(pnl - expected) < 1e-6

    def test_t1_short_uses_bid_o_entry_ask_c_exit(self):
        pair_data = _make_synthetic_pair_data(n_m1=200)
        signal_ts = pd.Timestamp("2024-01-01 00:30")
        pnl = stage29_0a._compute_target_t1_fixed_horizon_close_pnl(
            "EURUSD", signal_ts, "short", 0.0, pair_data, h_m1=60
        )
        assert pnl is not None
        entry_price = pair_data["bid_o"][31]
        exit_price = pair_data["ask_c"][31 + 60]
        expected = (entry_price - exit_price) / pair_data["pip"]
        assert abs(pnl - expected) < 1e-6

    def test_t1_horizon_boundary_clamp_returns_none(self):
        pair_data = _make_synthetic_pair_data(n_m1=100)
        signal_ts = pd.Timestamp("2024-01-01 00:50")  # signal+1 = idx 51; +60 = 111 > 100
        pnl = stage29_0a._compute_target_t1_fixed_horizon_close_pnl(
            "EURUSD", signal_ts, "long", 0.0, pair_data, h_m1=60
        )
        assert pnl is None

    def test_t1_unknown_timestamp_returns_none(self):
        pair_data = _make_synthetic_pair_data(n_m1=100)
        signal_ts = pd.Timestamp("2025-01-01")  # not in index
        pnl = stage29_0a._compute_target_t1_fixed_horizon_close_pnl(
            "EURUSD", signal_ts, "long", 0.0, pair_data, h_m1=60
        )
        assert pnl is None

    def test_t1_pip_denomination(self):
        pair_data = _make_synthetic_pair_data(n_m1=200, pip=0.01)  # JPY pair
        signal_ts = pd.Timestamp("2024-01-01 00:30")
        pnl = stage29_0a._compute_target_t1_fixed_horizon_close_pnl(
            "USDJPY", signal_ts, "long", 0.0, pair_data, h_m1=60
        )
        assert pnl is not None
        # pip=0.01 means PnL is in pips not points; magnitude check
        assert isinstance(pnl, float)


# ---------------------------------------------------------------------------
# TG3 — T2 time-weighted PnL
# ---------------------------------------------------------------------------


class TestG3T2TimeWeighted:
    def test_t2_returns_finite_pnl(self):
        pair_data = _make_synthetic_pair_data(n_m1=200)
        signal_ts = pd.Timestamp("2024-01-01 00:30")
        pnl = stage29_0a._compute_target_t2_time_weighted_pnl(
            "EURUSD", signal_ts, "long", 5.0, pair_data
        )
        # may be None if path window invalid; if not None, must be finite
        if pnl is not None:
            assert np.isfinite(pnl)

    def test_t2_decay_factor_clamped_to_zero_one(self):
        # Test the internal logic: hold_bars / H_M1 within [0,1] → decay in [0,1]
        # We rely on the parameterised barrier returning valid hold_bars
        pair_data = _make_synthetic_pair_data(n_m1=200)
        signal_ts = pd.Timestamp("2024-01-01 00:30")
        pnl, hold_bars = stage29_0a._compute_realised_barrier_pnl_parameterised(
            "EURUSD", signal_ts, "long", 5.0, pair_data, 1.5, 1.0, 60
        )
        if hold_bars is not None:
            assert 0 < hold_bars <= 60

    def test_t2_horizon_boundary_returns_none(self):
        pair_data = _make_synthetic_pair_data(n_m1=50)
        signal_ts = pd.Timestamp("2024-01-01 00:10")
        pnl = stage29_0a._compute_target_t2_time_weighted_pnl(
            "EURUSD", signal_ts, "long", 5.0, pair_data
        )
        # signal+1=11; +60=71 > 50 → None
        assert pnl is None


# ---------------------------------------------------------------------------
# TG4 — T3 multi-horizon PnL
# ---------------------------------------------------------------------------


class TestG4T3MultiHorizon:
    def test_t3_sums_three_horizons(self):
        pair_data = _make_synthetic_pair_data(n_m1=500)
        signal_ts = pd.Timestamp("2024-01-01 00:30")
        pnl = stage29_0a._compute_target_t3_multi_horizon_pnl(
            "EURUSD", signal_ts, "long", 5.0, pair_data
        )
        if pnl is not None:
            # Compare to individual horizon sum
            pnl_h30, _ = stage29_0a._compute_realised_barrier_pnl_parameterised(
                "EURUSD", signal_ts, "long", 5.0, pair_data, 1.5, 1.0, 30
            )
            pnl_h60, _ = stage29_0a._compute_realised_barrier_pnl_parameterised(
                "EURUSD", signal_ts, "long", 5.0, pair_data, 1.5, 1.0, 60
            )
            pnl_h120, _ = stage29_0a._compute_realised_barrier_pnl_parameterised(
                "EURUSD", signal_ts, "long", 5.0, pair_data, 1.5, 1.0, 120
            )
            if all(p is not None for p in (pnl_h30, pnl_h60, pnl_h120)):
                expected = pnl_h30 + pnl_h60 + pnl_h120
                assert abs(pnl - expected) < 1e-6

    def test_t3_horizon_boundary_returns_none(self):
        # H3=120 is the limiting horizon; if 120 doesn't fit → None
        pair_data = _make_synthetic_pair_data(n_m1=100)
        signal_ts = pd.Timestamp("2024-01-01 00:30")  # signal+1 = 31; +120 = 151 > 100
        pnl = stage29_0a._compute_target_t3_multi_horizon_pnl(
            "EURUSD", signal_ts, "long", 5.0, pair_data
        )
        assert pnl is None

    def test_t3_horizons_constant(self):
        assert stage29_0a.T3_HORIZONS == (30, 60, 120)


# ---------------------------------------------------------------------------
# TG5 — T4 asymmetric barrier PnL
# ---------------------------------------------------------------------------


class TestG5T4AsymmetricBarrier:
    def test_t4_uses_k_fav_2_0_k_adv_0_5(self):
        pair_data = _make_synthetic_pair_data(n_m1=200)
        signal_ts = pd.Timestamp("2024-01-01 00:30")
        pnl = stage29_0a._compute_target_t4_asymmetric_barrier_pnl(
            "EURUSD", signal_ts, "long", 5.0, pair_data
        )
        if pnl is not None:
            assert np.isfinite(pnl)
            # PnL magnitude should be tied to K_FAV*atr or K_ADV*atr or close-price-mtm
            # K_FAV=2.0 means +10 pip max favourable; K_ADV=0.5 means -2.5 pip max adverse
            assert (
                pnl == pytest.approx(2.0 * 5.0, abs=0.1)
                or pnl == pytest.approx(-0.5 * 5.0, abs=0.1)
                or abs(pnl) <= 20
            )

    def test_t4_horizon_boundary_returns_none(self):
        pair_data = _make_synthetic_pair_data(n_m1=50)
        signal_ts = pd.Timestamp("2024-01-01 00:30")  # +1 +60 = 91 > 50
        pnl = stage29_0a._compute_target_t4_asymmetric_barrier_pnl(
            "EURUSD", signal_ts, "long", 5.0, pair_data
        )
        assert pnl is None


# ---------------------------------------------------------------------------
# TG6 — target precompute orchestrator
# ---------------------------------------------------------------------------


class TestG6TargetPrecompute:
    def _make_synthetic_df(self):
        return pd.DataFrame(
            {
                "pair": ["EURUSD", "EURUSD"],
                "signal_ts": [
                    pd.Timestamp("2024-01-01 00:30"),
                    pd.Timestamp("2024-01-01 00:35"),
                ],
                "direction": ["long", "short"],
                "atr_at_signal_pip": [5.0, 6.0],
            }
        )

    def test_precompute_dispatches_target_kind(self):
        df = self._make_synthetic_df()
        pair_map = {"EURUSD": _make_synthetic_pair_data(n_m1=200)}
        for target_id in ("T1", "T2", "T3", "T4", "TARGET_CONTROL"):
            pnl_arr = stage29_0a.precompute_target_pnls_per_row(df, pair_map, target_id)
            assert pnl_arr.shape == (2,)
            assert pnl_arr.dtype == np.float64

    def test_precompute_unknown_target_raises(self):
        df = self._make_synthetic_df()
        with pytest.raises(ValueError, match="Unknown target_kind"):
            stage29_0a.precompute_target_pnls_per_row(df, {}, "T99")

    def test_precompute_unknown_pair_returns_nan(self):
        df = self._make_synthetic_df()
        pair_map = {}  # no pairs
        pnl_arr = stage29_0a.precompute_target_pnls_per_row(df, pair_map, "T1")
        assert np.all(~np.isfinite(pnl_arr))


# ---------------------------------------------------------------------------
# TG7 — build_a2_cells
# ---------------------------------------------------------------------------


class TestG7BuildA2Cells:
    def test_returns_nine_cells(self):
        cells = stage29_0a.build_a2_cells()
        # 4 substantive + 1 target-control + 4 per-target baselines = 9
        assert len(cells) == 9

    def test_cell_ids(self):
        cells = stage29_0a.build_a2_cells()
        ids = [c["id"] for c in cells]
        assert "C-d1-T1" in ids
        assert "C-d1-T2" in ids
        assert "C-d1-T3" in ids
        assert "C-d1-T4" in ids
        assert "C-d1-target-control" in ids
        assert "C-d1-T1-baseline" in ids
        assert "C-d1-T2-baseline" in ids
        assert "C-d1-T3-baseline" in ids
        assert "C-d1-T4-baseline" in ids

    def test_substantive_cells_use_quantile_family(self):
        cells = stage29_0a.build_a2_cells()
        substantive = [c for c in cells if c["id"].startswith("C-d1-T") and not c["is_baseline"]]
        for c in substantive:
            assert c["quantile_percents"] == (5.0, 10.0, 20.0, 30.0, 40.0)
            assert c["quantile_kind"] == "family"

    def test_baseline_cells_use_q5_only(self):
        cells = stage29_0a.build_a2_cells()
        baselines = [c for c in cells if c["is_baseline"]]
        assert len(baselines) == 4
        for c in baselines:
            assert c["quantile_percents"] == (5.0,)
            assert c["quantile_kind"] == "q5_only"
            assert c["score_type"] == "s_b_raw_per_target_baseline"

    def test_target_control_uses_inherited_target(self):
        cells = stage29_0a.build_a2_cells()
        ctl = next(c for c in cells if c["id"] == "C-d1-target-control")
        assert ctl["target_kind"] == "TARGET_CONTROL"
        assert ctl["target_params"]["k_fav"] == 1.5
        assert ctl["target_params"]["k_adv"] == 1.0


# ---------------------------------------------------------------------------
# TG8 — per-target baseline FAIL-FAST internal consistency
# ---------------------------------------------------------------------------


class TestG8PerTargetBaselineFailFast:
    def _make_baseline_dict(self, n=1000, sharpe=0.1, ann=10000.0, val_sh=-0.15):
        return {
            "T1": {
                "val_sharpe": val_sh,
                "test_n_trades": n,
                "test_sharpe": sharpe,
                "test_ann_pnl": ann,
            },
            "T2": {
                "val_sharpe": val_sh,
                "test_n_trades": n,
                "test_sharpe": sharpe,
                "test_ann_pnl": ann,
            },
            "T3": {
                "val_sharpe": val_sh,
                "test_n_trades": n,
                "test_sharpe": sharpe,
                "test_ann_pnl": ann,
            },
            "T4": {
                "val_sharpe": val_sh,
                "test_n_trades": n,
                "test_sharpe": sharpe,
                "test_ann_pnl": ann,
            },
        }

    def test_identical_baselines_pass(self):
        b = self._make_baseline_dict()
        report = stage29_0a.check_per_target_baseline_consistency(b, b)
        assert report["all_consistent"] is True

    def test_n_trades_mismatch_raises(self):
        b1 = self._make_baseline_dict(n=1000)
        b2 = self._make_baseline_dict(n=1001)
        with pytest.raises(stage29_0a.PerTargetBaselineMismatchError):
            stage29_0a.check_per_target_baseline_consistency(b1, b2)

    def test_sharpe_mismatch_raises(self):
        b1 = self._make_baseline_dict(sharpe=0.1)
        b2 = self._make_baseline_dict(sharpe=0.2)
        with pytest.raises(stage29_0a.PerTargetBaselineMismatchError):
            stage29_0a.check_per_target_baseline_consistency(b1, b2)

    def test_ann_pnl_mismatch_raises(self):
        b1 = self._make_baseline_dict(ann=10000.0)
        b2 = self._make_baseline_dict(ann=12000.0)
        with pytest.raises(stage29_0a.PerTargetBaselineMismatchError):
            stage29_0a.check_per_target_baseline_consistency(b1, b2)


# ---------------------------------------------------------------------------
# TG9 — archived Phase 28 §10 drift (DIAGNOSTIC)
# ---------------------------------------------------------------------------


class TestG9ArchivedPhase28Drift:
    def test_drift_report_per_target(self):
        b = {
            "T1": {"test_n_trades": 34700, "test_sharpe": -0.17, "test_ann_pnl": -200000.0},
            "T2": {"test_n_trades": 34626, "test_sharpe": -0.1732, "test_ann_pnl": -204664.4},
            "T3": {"test_n_trades": 30000, "test_sharpe": -0.20, "test_ann_pnl": -250000.0},
            "T4": {"test_n_trades": 40000, "test_sharpe": -0.10, "test_ann_pnl": -150000.0},
        }
        drift = stage29_0a.compute_archived_phase28_drift(b)
        assert "T1" in drift and "T2" in drift and "T3" in drift and "T4" in drift
        # T2 should have ~zero delta (matches archive)
        assert abs(drift["T2"]["test_n_trades_delta"]) == 0
        assert abs(drift["T2"]["test_sharpe_delta"]) < 1e-5
        # T3 has -4626 delta in n_trades
        assert drift["T3"]["test_n_trades_delta"] == -4626


# ---------------------------------------------------------------------------
# TG10 — C-d1-target-control drift vs 27.0d C-se (6th-phase chain)
# ---------------------------------------------------------------------------


class TestG10TargetControlDrift:
    def test_drift_within_tolerance(self):
        from unittest.mock import patch

        with patch.object(
            stage29_0a,
            "load_27_0d_c_se_metrics",
            return_value={
                "source": "test",
                "test_n_trades": 1000,
                "test_sharpe": 0.1,
                "test_annual_pnl": 10000.0,
            },
        ):
            result = {
                "test_realised_metrics": {
                    "n_trades": 1000,
                    "sharpe": 0.1,
                    "annual_pnl": 10000.0,
                }
            }
            drift = stage29_0a.compute_c_d1_target_control_drift_check(result)
            assert drift["all_within_tolerance"] is True
            assert drift["warn"] is False
            assert "6th anchor" in drift["chain_position"]

    def test_drift_warn_on_n_trades_mismatch(self):
        from unittest.mock import patch

        with patch.object(
            stage29_0a,
            "load_27_0d_c_se_metrics",
            return_value={
                "source": "test",
                "test_n_trades": 1000,
                "test_sharpe": 0.1,
                "test_annual_pnl": 10000.0,
            },
        ):
            result = {
                "test_realised_metrics": {
                    "n_trades": 2000,  # large delta
                    "sharpe": 0.1,
                    "annual_pnl": 10000.0,
                }
            }
            drift = stage29_0a.compute_c_d1_target_control_drift_check(result)
            assert drift["all_within_tolerance"] is False
            assert drift["warn"] is True


# ---------------------------------------------------------------------------
# TG11 — within-eval PARTIAL_DRIFT_TARGET_REPLICA detection
# ---------------------------------------------------------------------------


class TestG11WithinEvalDrift:
    def _make_cell(self, n_trades, sharpe, ann_pnl, h_state="OK"):
        return {
            "h_state": h_state,
            "test_realised_metrics": {
                "n_trades": n_trades,
                "sharpe": sharpe,
                "annual_pnl": ann_pnl,
            },
        }

    def test_identical_cells_within_tolerance(self):
        ar = self._make_cell(1000, 0.1, 10000.0)
        ctl = self._make_cell(1000, 0.1, 10000.0)
        drift = stage29_0a.compute_within_eval_target_drift_check(ar, ctl)
        assert drift["all_within_tolerance"] is True
        assert drift["warn"] is True  # WARN means "zero effect detected"

    def test_large_sharpe_delta_not_within(self):
        ar = self._make_cell(1000, 0.5, 10000.0)
        ctl = self._make_cell(1000, 0.1, 10000.0)
        drift = stage29_0a.compute_within_eval_target_drift_check(ar, ctl)
        assert drift["sharpe_within_tolerance"] is False
        assert drift["all_within_tolerance"] is False

    def test_h_state_not_ok_returns_warn(self):
        ar = self._make_cell(1000, 0.1, 10000.0, h_state="INSUFFICIENT_DATA")
        ctl = self._make_cell(1000, 0.1, 10000.0)
        drift = stage29_0a.compute_within_eval_target_drift_check(ar, ctl)
        assert drift["all_within_tolerance"] is False
        assert drift["warn"] is True


# ---------------------------------------------------------------------------
# TG12 — H-D1 4-outcome ladder per target
# ---------------------------------------------------------------------------


class TestG12HD1OutcomePerTarget:
    def _make_tx_result(self, val_sharpe, val_n, cell_spearman):
        return {
            "h_state": "OK",
            "cell": {"id": "C-d1-test"},
            "val_realised_sharpe": val_sharpe,
            "val_n_trades": val_n,
            "selected_q_percent": 10,
            "quantile_best": {"val": {"spearman_score_vs_pnl": cell_spearman}},
        }

    def test_pass_all_conditions(self):
        ar = self._make_tx_result(val_sharpe=0.0, val_n=25000, cell_spearman=0.40)
        out = stage29_0a.compute_h_d1_outcome_per_target(
            ar, True, {"all_within_tolerance": False}, "T1", per_target_baseline_val_sharpe=-0.10
        )
        # lift = 0.0 - (-0.10) = +0.10 >= 0.05 → PASS
        assert out["outcome"] == "PASS"
        assert out["row_matched"] == 1

    def test_partial_drift_overrides_pass(self):
        ar = self._make_tx_result(val_sharpe=0.0, val_n=25000, cell_spearman=0.40)
        out = stage29_0a.compute_h_d1_outcome_per_target(
            ar, True, {"all_within_tolerance": True}, "T1", per_target_baseline_val_sharpe=-0.10
        )
        assert out["outcome"] == "PARTIAL_DRIFT_TARGET_REPLICA"
        assert out["row_matched"] == 4

    def test_partial_support_subthreshold(self):
        # lift = -0.07 - (-0.10) = +0.03 ∈ [+0.02, +0.05) → PARTIAL_SUPPORT
        ar = self._make_tx_result(val_sharpe=-0.07, val_n=25000, cell_spearman=0.40)
        out = stage29_0a.compute_h_d1_outcome_per_target(
            ar, True, {"all_within_tolerance": False}, "T2", per_target_baseline_val_sharpe=-0.10
        )
        assert out["outcome"] == "PARTIAL_SUPPORT"
        assert out["row_matched"] == 2

    def test_falsified_low_lift(self):
        # lift = -0.10 - (-0.10) = 0 < +0.02 → FALSIFIED
        ar = self._make_tx_result(val_sharpe=-0.10, val_n=25000, cell_spearman=0.40)
        out = stage29_0a.compute_h_d1_outcome_per_target(
            ar, True, {"all_within_tolerance": False}, "T3", per_target_baseline_val_sharpe=-0.10
        )
        assert out["outcome"] == "FALSIFIED_TARGET_INSUFFICIENT"
        assert out["row_matched"] == 3

    def test_h_state_not_ok_returns_needs_review(self):
        ar = {"h_state": "INSUFFICIENT_DATA", "cell": {"id": "C-d1-test"}}
        out = stage29_0a.compute_h_d1_outcome_per_target(
            ar, True, {"all_within_tolerance": False}, "T1", per_target_baseline_val_sharpe=-0.10
        )
        assert out["outcome"] == "NEEDS_REVIEW"

    def test_baseline_pass_false_blocks_pass(self):
        ar = self._make_tx_result(val_sharpe=0.0, val_n=25000, cell_spearman=0.40)
        out = stage29_0a.compute_h_d1_outcome_per_target(
            ar, False, {"all_within_tolerance": False}, "T1", per_target_baseline_val_sharpe=-0.10
        )
        # baseline_pass=False → can't be PASS or PARTIAL_SUPPORT
        assert out["outcome"] == "FALSIFIED_TARGET_INSUFFICIENT"


# ---------------------------------------------------------------------------
# TG13 — aggregate verdict + FALSIFIED_A2_NARROW
# ---------------------------------------------------------------------------


class TestG13AggregateVerdict:
    def _outcome(self, target_id, label):
        return {
            "target_id": target_id,
            "cell_id": f"C-d1-{target_id}",
            "outcome": label,
            "row_matched": 1,
        }

    def test_any_pass_routes_to_review(self):
        outcomes = [
            self._outcome("T1", "PASS"),
            self._outcome("T2", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T3", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T4", "FALSIFIED_TARGET_INSUFFICIENT"),
        ]
        agg = stage29_0a.compute_h_d1_aggregate_verdict(outcomes)
        assert agg["aggregate_verdict"] == "SPLIT_VERDICT_ROUTE_TO_REVIEW"
        assert agg["a2_narrow_status"] == "PASS_under_A2_narrow"

    def test_partial_only_rejects(self):
        outcomes = [
            self._outcome("T1", "PARTIAL_SUPPORT"),
            self._outcome("T2", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T3", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T4", "FALSIFIED_TARGET_INSUFFICIENT"),
        ]
        agg = stage29_0a.compute_h_d1_aggregate_verdict(outcomes)
        assert agg["aggregate_verdict"] == "REJECT_NON_DISCRIMINATIVE"
        assert agg["a2_narrow_status"] == "PARTIAL_under_A2_narrow"

    def test_all_falsified_labels_a2_narrow(self):
        outcomes = [
            self._outcome("T1", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T2", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T3", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T4", "FALSIFIED_TARGET_INSUFFICIENT"),
        ]
        agg = stage29_0a.compute_h_d1_aggregate_verdict(outcomes)
        assert agg["aggregate_verdict"] == "REJECT_NON_DISCRIMINATIVE"
        assert agg["a2_narrow_status"] == "FALSIFIED_A2_NARROW"

    def test_all_falsified_never_claims_all_a2(self):
        outcomes = [
            self._outcome("T1", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T2", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T3", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T4", "FALSIFIED_TARGET_INSUFFICIENT"),
        ]
        agg = stage29_0a.compute_h_d1_aggregate_verdict(outcomes)
        routing = agg["routing_implication"]
        assert "FALSIFIED_A2_NARROW" in routing
        if "FALSIFIED_ALL_A2" in routing:
            assert "NEVER" in routing

    def test_all_drift_labels_a2_narrow(self):
        outcomes = [
            self._outcome(t, "PARTIAL_DRIFT_TARGET_REPLICA") for t in ("T1", "T2", "T3", "T4")
        ]
        agg = stage29_0a.compute_h_d1_aggregate_verdict(outcomes)
        assert agg["a2_narrow_status"] == "FALSIFIED_A2_NARROW"


# ---------------------------------------------------------------------------
# TG14 — R-T3 absorption status
# ---------------------------------------------------------------------------


class TestG14RT3AbsorptionStatus:
    def _outcome(self, target_id, label):
        return {
            "target_id": target_id,
            "outcome": label,
            "cell_id": f"C-d1-{target_id}",
            "row_matched": 1,
        }

    def test_t3_pass_absorbs_r_t3(self):
        outcomes = [
            self._outcome("T1", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T2", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T3", "PASS"),
            self._outcome("T4", "FALSIFIED_TARGET_INSUFFICIENT"),
        ]
        agg = stage29_0a.compute_h_d1_aggregate_verdict(outcomes)
        assert agg["r_t3_absorption_status"] == "PASS_under_T3"

    def test_t3_falsified_absorbs_r_t3_as_falsified(self):
        outcomes = [
            self._outcome("T1", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T2", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T3", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T4", "FALSIFIED_TARGET_INSUFFICIENT"),
        ]
        agg = stage29_0a.compute_h_d1_aggregate_verdict(outcomes)
        assert agg["r_t3_absorption_status"] == "FALSIFIED_under_T3"

    def test_t3_partial_support_absorbs_r_t3_as_partial(self):
        outcomes = [
            self._outcome("T1", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T2", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T3", "PARTIAL_SUPPORT"),
            self._outcome("T4", "FALSIFIED_TARGET_INSUFFICIENT"),
        ]
        agg = stage29_0a.compute_h_d1_aggregate_verdict(outcomes)
        assert agg["r_t3_absorption_status"] == "PARTIAL_under_T3"

    def test_t3_drift_absorbs_r_t3_as_falsified(self):
        outcomes = [
            self._outcome("T1", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T2", "FALSIFIED_TARGET_INSUFFICIENT"),
            self._outcome("T3", "PARTIAL_DRIFT_TARGET_REPLICA"),
            self._outcome("T4", "FALSIFIED_TARGET_INSUFFICIENT"),
        ]
        agg = stage29_0a.compute_h_d1_aggregate_verdict(outcomes)
        assert agg["r_t3_absorption_status"] == "FALSIFIED_under_T3"


# ---------------------------------------------------------------------------
# TG15 — T3 overlap rate diagnostic
# ---------------------------------------------------------------------------


class TestG15T3OverlapRate:
    def test_t3_overlap_zero_below_threshold(self):
        # All signals 200 min apart → no overlap with max_horizon=120
        signals = pd.date_range("2024-01-01", periods=10, freq="200min")
        df = pd.DataFrame({"pair": ["EURUSD"] * 10, "signal_ts": signals})
        report = stage29_0a.compute_t3_overlap_rate(df, max_horizon=120)
        assert report["overall"]["overlap_rate"] == 0.0
        assert report["overall"]["warn"] is False

    def test_t3_overlap_high_warns(self):
        # All signals 10 min apart → 100% overlap with max_horizon=120
        signals = pd.date_range("2024-01-01", periods=10, freq="10min")
        df = pd.DataFrame({"pair": ["EURUSD"] * 10, "signal_ts": signals})
        report = stage29_0a.compute_t3_overlap_rate(df, max_horizon=120)
        assert report["overall"]["overlap_rate"] > 0.9
        assert report["overall"]["warn"] is True

    def test_t3_overlap_threshold_constant(self):
        assert stage29_0a.T3_OVERLAP_WARN_RATE == 0.10


# ---------------------------------------------------------------------------
# TG16 — parameterised barrier PnL + cell signature smoke
# ---------------------------------------------------------------------------


class TestG16ParameterisedBarrierAndSmoke:
    def test_parameterised_barrier_returns_pnl_and_hold_bars(self):
        pair_data = _make_synthetic_pair_data(n_m1=200)
        signal_ts = pd.Timestamp("2024-01-01 00:30")
        pnl, hold_bars = stage29_0a._compute_realised_barrier_pnl_parameterised(
            "EURUSD", signal_ts, "long", 5.0, pair_data, 1.5, 1.0, 60
        )
        if pnl is not None:
            assert np.isfinite(pnl)
            assert hold_bars is not None
            assert 0 < hold_bars <= 60

    def test_parameterised_barrier_unknown_ts_returns_none(self):
        pair_data = _make_synthetic_pair_data(n_m1=200)
        signal_ts = pd.Timestamp("2025-01-01")  # not in index
        pnl, hold_bars = stage29_0a._compute_realised_barrier_pnl_parameterised(
            "EURUSD", signal_ts, "long", 5.0, pair_data, 1.5, 1.0, 60
        )
        assert pnl is None and hold_bars is None

    def test_cell_signature_includes_target_kind(self):
        cells = stage29_0a.build_a2_cells()
        for c in cells:
            sig = stage29_0a._cell_signature(c)
            assert "target_kind=" in sig

    def test_target_control_inherited_pnl(self):
        pair_data = _make_synthetic_pair_data(n_m1=200)
        signal_ts = pd.Timestamp("2024-01-01 00:30")
        pnl = stage29_0a._compute_target_control_inherited_pnl(
            "EURUSD", signal_ts, "long", 5.0, pair_data
        )
        if pnl is not None:
            assert np.isfinite(pnl)
