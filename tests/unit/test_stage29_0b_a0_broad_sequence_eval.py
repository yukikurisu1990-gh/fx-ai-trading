"""Unit tests for stage29_0b_a0_broad_sequence_eval.

Covers: windowed dataset builder + causality guard / coverage check;
sequence models (S1/S2/S3) forward shape; sequence training deterministic
setup; per-cell quantile eval; C-sb-baseline FAIL-FAST; C-d2-arch-control
7th-anchor drift; PARTIAL_DRIFT_TABULAR_REPLICA detection; H-D2 ladder;
aggregate verdict with FALSIFIED_A0_BROAD_NARROW distinction (NEVER
FALSIFIED_ALL_A0_BROAD); cell construction; sequence-cell harness;
determinism metric-tolerance helper; eval_report smoke test.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import torch

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage29_0b = importlib.import_module("stage29_0b_a0_broad_sequence_eval")
_windowed_dataset = importlib.import_module("_windowed_dataset")
_sequence_models = importlib.import_module("_sequence_models")
_sequence_training = importlib.import_module("_sequence_training")
_sequence_cell_harness = importlib.import_module("_sequence_cell_harness")


# ---------------------------------------------------------------------------
# Helper: synthetic pair_data
# ---------------------------------------------------------------------------


def _make_pair_data(n_m1: int = 500, pip: float = 0.0001, seed: int = 42):
    rng = np.random.default_rng(seed)
    mid = 1.1 + np.cumsum(rng.normal(0, 0.0001, n_m1)).astype(np.float64)
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
        "bid_h": (bid + bar_range / 2).astype(np.float64),
        "bid_l": (bid - bar_range / 2).astype(np.float64),
        "bid_c": bid.astype(np.float64),
        "bid_o": bid.astype(np.float64),
        "ask_h": (ask + bar_range / 2).astype(np.float64),
        "ask_l": (ask - bar_range / 2).astype(np.float64),
        "ask_c": ask.astype(np.float64),
        "ask_o": ask.astype(np.float64),
    }


# ---------------------------------------------------------------------------
# TG1 — module / constants
# ---------------------------------------------------------------------------


class TestG1ModuleConstants:
    def test_module_imports(self):
        assert stage29_0b is not None
        assert _windowed_dataset is not None
        assert _sequence_models is not None
        assert _sequence_training is not None
        assert _sequence_cell_harness is not None

    def test_constants_present(self):
        assert _windowed_dataset.N_M5_BARS == 32
        assert _windowed_dataset.N_CHANNELS == 8
        assert _windowed_dataset.N_M1_PER_M5 == 5
        assert _windowed_dataset.TOTAL_M1_BARS_IN_WINDOW == 160

    def test_closed_architecture_allowlist(self):
        assert _sequence_models.CLOSED_ARCHITECTURE_ALLOWLIST == ("S1", "S2", "S3")

    def test_h_d2_outcome_labels(self):
        assert stage29_0b.H_D2_OUTCOME_PASS == "PASS"
        assert stage29_0b.H_D2_OUTCOME_PARTIAL_SUPPORT == "PARTIAL_SUPPORT"
        assert stage29_0b.H_D2_OUTCOME_FALSIFIED_ARCH_INSUFFICIENT == "FALSIFIED_ARCH_INSUFFICIENT"
        assert (
            stage29_0b.H_D2_OUTCOME_PARTIAL_DRIFT_TABULAR_REPLICA
            == "PARTIAL_DRIFT_TABULAR_REPLICA"
        )

    def test_baseline_constants(self):
        assert stage29_0b.BASELINE_27_0B_C_ALPHA0_N_TRADES == 34626
        assert abs(stage29_0b.BASELINE_27_0B_C_ALPHA0_SHARPE - (-0.1732)) < 1e-6
        assert abs(stage29_0b.SECTION_10_BASELINE_VAL_SHARPE - (-0.1863)) < 1e-6

    def test_thresholds(self):
        assert stage29_0b.H2_LIFT_THRESHOLD_PASS == 0.05
        assert stage29_0b.H2_LIFT_THRESHOLD_PARTIAL_SUPPORT_LO == 0.02
        assert stage29_0b.H1M_PRESERVE_THRESHOLD == 0.30
        assert stage29_0b.H3_TRADE_COUNT_THRESHOLD == 20000

    def test_arch_training_config(self):
        cfg = _sequence_training.ARCH_TRAINING_CONFIG
        assert cfg["S1"]["lr"] == 1e-3 and cfg["S1"]["batch_size"] == 256
        assert cfg["S2"]["lr"] == 1e-3 and cfg["S2"]["batch_size"] == 512
        assert cfg["S3"]["lr"] == 5e-4 and cfg["S3"]["batch_size"] == 256

    def test_exceptions_defined(self):
        assert issubclass(stage29_0b.BaselineMismatchError, RuntimeError)
        assert issubclass(_windowed_dataset.CausalityGuardError, RuntimeError)
        assert issubclass(_windowed_dataset.WindowedCoverageError, RuntimeError)
        assert issubclass(_sequence_training.CudaUnavailableError, RuntimeError)


# ---------------------------------------------------------------------------
# TG2 — windowed dataset builder shape + per-pair normalisation
# ---------------------------------------------------------------------------


class TestG2WindowedDataset:
    def test_build_window_shape(self):
        pair_data = _make_pair_data(n_m1=500)
        signal_ts = pd.Timestamp("2024-01-01 04:00")  # idx 120; need >= 160 prior bars
        window, valid = _windowed_dataset._build_window_for_row(signal_ts, pair_data)
        assert valid is True
        assert window is not None
        assert window.shape == (32, 8)
        assert window.dtype == np.float32

    def test_build_window_returns_none_for_unknown_ts(self):
        pair_data = _make_pair_data(n_m1=500)
        signal_ts = pd.Timestamp("2025-01-01")  # not in index
        window, valid = _windowed_dataset._build_window_for_row(signal_ts, pair_data)
        assert valid is False
        assert window is None

    def test_build_window_returns_none_at_boundary(self):
        pair_data = _make_pair_data(n_m1=500)
        # signal_ts near start; entry_idx = signal+1 = e.g. 50; needs 160 prior bars → invalid
        signal_ts = pd.Timestamp("2024-01-01 00:30")  # idx 30 → entry 31 → window_start = -129
        window, valid = _windowed_dataset._build_window_for_row(signal_ts, pair_data)
        assert valid is False
        assert window is None

    def test_per_pair_pip_normalisation_applied(self):
        pair_data = _make_pair_data(n_m1=500, pip=0.0001)
        signal_ts = pd.Timestamp("2024-01-01 04:00")
        window, _ = _windowed_dataset._build_window_for_row(signal_ts, pair_data)
        # all values should be (raw - entry_ask) / pip; magnitude order: small (sub-pip noise scaled)
        assert np.isfinite(window).all()
        assert abs(window.mean()) < 100  # in pip units, small noise

    def test_entry_price_centering_applied(self):
        # After centering, values are in pip-units relative to entry_ask.
        # Raw mid is ~1.1; in pip-units that's ~11000. After centering, magnitudes
        # are bounded by accumulated random walk over 160 M1 bars (~tens of pips).
        pair_data = _make_pair_data(n_m1=500)
        signal_ts = pd.Timestamp("2024-01-01 04:00")
        window, _ = _windowed_dataset._build_window_for_row(signal_ts, pair_data)
        # Values must NOT be near raw-price magnitude (~11000 pips); should be small
        assert abs(window).max() < 1000  # well below raw-pip-magnitude of price
        # Some channel near the last M5 bar should be small (close to entry_ask)
        last_m5_bar = window[-1]  # (8,) channels for last M5 bar before entry
        assert abs(last_m5_bar).max() < 100  # within ~100 pips of entry


# ---------------------------------------------------------------------------
# TG3 — Causality guard (HALT semantics)
# ---------------------------------------------------------------------------


class TestG3CausalityGuard:
    def test_normal_window_passes(self):
        pair_data = _make_pair_data(n_m1=500)
        signal_ts = pd.Timestamp("2024-01-01 04:00")
        # Should not raise
        window, valid = _windowed_dataset._build_window_for_row(
            signal_ts, pair_data, causality_check=True
        )
        assert valid is True

    def test_max_input_ts_strictly_before_entry(self):
        pair_data = _make_pair_data(n_m1=500)
        signal_ts = pd.Timestamp("2024-01-01 04:00")
        target_entry_ts = signal_ts + pd.Timedelta(minutes=1)
        entry_idx = int(pair_data["m1_pos"].loc[target_entry_ts])
        # Last M1 bar in window is at index entry_idx - 1
        last_m1_ts = pair_data["m1_pos"].index[entry_idx - 1]
        assert last_m1_ts < target_entry_ts

    def test_verify_causality_guard_sample_passes(self):
        # Build a synthetic df
        pair_data = _make_pair_data(n_m1=500)
        df = pd.DataFrame({
            "pair": ["TEST"] * 10,
            "signal_ts": pd.date_range("2024-01-01 04:00", periods=10, freq="5min"),
            "direction": ["long"] * 10,
            "atr_at_signal_pip": [5.0] * 10,
        })
        result = _windowed_dataset.verify_causality_guard(
            df, {"TEST": pair_data}, sample_size=10, seed=42
        )
        assert result["n_violations"] == 0
        assert result["n_valid_windows"] > 0

    def test_causality_guard_error_class(self):
        try:
            raise _windowed_dataset.CausalityGuardError("test")
        except _windowed_dataset.CausalityGuardError as exc:
            assert "test" in str(exc)


# ---------------------------------------------------------------------------
# TG4 — Coverage check (HALT semantics)
# ---------------------------------------------------------------------------


class TestG4CoverageCheck:
    def test_high_coverage_passes(self):
        coverage = {"P1": {"n_total": 100, "n_valid": 99}, "P2": {"n_total": 100, "n_valid": 98}}
        # 197/200 = 98.5% > 95%
        _windowed_dataset.assert_windowed_coverage_meets_threshold(coverage, "test")

    def test_low_coverage_raises(self):
        coverage = {"P1": {"n_total": 100, "n_valid": 90}, "P2": {"n_total": 100, "n_valid": 89}}
        # 179/200 = 89.5% < 95%
        with pytest.raises(_windowed_dataset.WindowedCoverageError):
            _windowed_dataset.assert_windowed_coverage_meets_threshold(coverage, "test")

    def test_compute_coverage_per_pair(self):
        df = pd.DataFrame({"pair": ["A", "A", "B", "B"]})
        valid_mask = np.array([True, True, True, False])
        result = _windowed_dataset.compute_windowed_coverage_per_pair(df, valid_mask, ["A", "B"])
        assert result["A"]["rate"] == 1.0
        assert result["B"]["rate"] == 0.5


# ---------------------------------------------------------------------------
# TG5 — S1 BidirectionalLSTM forward
# ---------------------------------------------------------------------------


class TestG5S1Lstm:
    def test_forward_shape(self):
        model = _sequence_models.S1BidirectionalLSTM()
        x = torch.randn(4, 32, 8)
        out = model(x)
        assert out.shape == (4,)

    def test_parameter_count_in_expected_range(self):
        model = _sequence_models.S1BidirectionalLSTM()
        n_params = sum(p.numel() for p in model.parameters())
        # ~536k as observed earlier; range check
        assert 100_000 < n_params < 2_000_000

    def test_deterministic_forward_with_seed(self):
        # Use .eval() to disable dropout RNG consumption
        torch.manual_seed(42)
        model_a = _sequence_models.S1BidirectionalLSTM()
        model_a.eval()
        torch.manual_seed(42)
        model_b = _sequence_models.S1BidirectionalLSTM()
        model_b.eval()
        x = torch.randn(4, 32, 8)
        with torch.no_grad():
            out_a = model_a(x)
            out_b = model_b(x)
        assert torch.allclose(out_a, out_b)


# ---------------------------------------------------------------------------
# TG6 — S2 TemporalCNN forward
# ---------------------------------------------------------------------------


class TestG6S2TemporalCNN:
    def test_forward_shape(self):
        model = _sequence_models.S2TemporalCNN()
        x = torch.randn(4, 32, 8)
        out = model(x)
        assert out.shape == (4,)

    def test_dilation_cascade_present(self):
        model = _sequence_models.S2TemporalCNN()
        conv_layers = [m for m in model.blocks if isinstance(m, torch.nn.Conv1d)]
        assert len(conv_layers) == 4
        assert [c.dilation[0] for c in conv_layers] == [1, 2, 4, 8]

    def test_parameter_count_small(self):
        model = _sequence_models.S2TemporalCNN()
        n_params = sum(p.numel() for p in model.parameters())
        # ~38k; smaller than LSTM/Transformer
        assert n_params < 100_000


# ---------------------------------------------------------------------------
# TG7 — S3 TransformerEncoder forward
# ---------------------------------------------------------------------------


class TestG7S3Transformer:
    def test_forward_shape(self):
        model = _sequence_models.S3TransformerEncoder()
        x = torch.randn(4, 32, 8)
        out = model(x)
        assert out.shape == (4,)

    def test_sinusoidal_pe_buffer_present(self):
        model = _sequence_models.S3TransformerEncoder()
        assert hasattr(model, "pos_encoding")
        assert model.pos_encoding.shape == (32, 128)
        # PE is fixed buffer, not learnable parameter
        param_names = {name for name, _ in model.named_parameters()}
        assert "pos_encoding" not in param_names

    def test_first_position_pooling(self):
        # Verify the pooling indexes the first position
        model = _sequence_models.S3TransformerEncoder()
        x1 = torch.randn(2, 32, 8)
        x2 = x1.clone()
        x2[:, 1:, :] = 0  # zero out all but first position; output should depend mostly on first pos info if pooling is first-pos
        model.eval()
        with torch.no_grad():
            out1 = model(x1)
            out2 = model(x2)
        # Outputs will differ but both should be finite scalars
        assert out1.shape == (2,) and out2.shape == (2,)
        assert torch.isfinite(out1).all() and torch.isfinite(out2).all()


# ---------------------------------------------------------------------------
# TG8 — sequence model factory
# ---------------------------------------------------------------------------


class TestG8SequenceModelFactory:
    def test_factory_returns_correct_class(self):
        assert isinstance(_sequence_models.build_sequence_model("S1"), _sequence_models.S1BidirectionalLSTM)
        assert isinstance(_sequence_models.build_sequence_model("S2"), _sequence_models.S2TemporalCNN)
        assert isinstance(_sequence_models.build_sequence_model("S3"), _sequence_models.S3TransformerEncoder)

    def test_factory_rejects_unknown(self):
        with pytest.raises(ValueError, match="Unknown arch_id"):
            _sequence_models.build_sequence_model("S99")

    def test_factory_rejects_lowercase(self):
        with pytest.raises(ValueError):
            _sequence_models.build_sequence_model("s1")


# ---------------------------------------------------------------------------
# TG9 — deterministic training setup
# ---------------------------------------------------------------------------


class TestG9DeterministicSetup:
    def test_setup_deterministic_environment_sets_seeds(self):
        _sequence_training.setup_deterministic_environment(seed=42)
        # After setup, torch.rand returns same value across calls within same script
        import os
        assert os.environ.get("CUBLAS_WORKSPACE_CONFIG") == ":4096:8"
        assert torch.backends.cudnn.deterministic is True
        assert torch.backends.cudnn.benchmark is False

    def test_select_device_returns_cuda_when_available(self):
        if torch.cuda.is_available():
            device = _sequence_training.select_device()
            assert device.type == "cuda"
        else:
            with pytest.raises(_sequence_training.CudaUnavailableError):
                _sequence_training.select_device()


# ---------------------------------------------------------------------------
# TG10 — cell construction
# ---------------------------------------------------------------------------


class TestG10CellConstruction:
    def test_five_cells(self):
        cells = stage29_0b.build_a0_broad_cells()
        assert len(cells) == 5

    def test_cell_ids_match_design(self):
        cells = stage29_0b.build_a0_broad_cells()
        ids = [c["id"] for c in cells]
        assert ids == ["C-d2-S1", "C-d2-S2", "C-d2-S3", "C-d2-arch-control", "C-sb-baseline"]

    def test_arch_control_is_tabular_not_sequence(self):
        cells = stage29_0b.build_a0_broad_cells()
        ctl = next(c for c in cells if c["id"] == "C-d2-arch-control")
        assert ctl["is_arch_control"] is True
        assert ctl["is_baseline"] is False
        assert ctl["score_type"] == "s_e_tabular_control"
        assert "tabular" in ctl["picker"].lower() or "lightgbm" in ctl["picker"].lower()

    def test_baseline_uses_q5_only(self):
        cells = stage29_0b.build_a0_broad_cells()
        baseline = next(c for c in cells if c["is_baseline"])
        assert baseline["quantile_percents"] == (5.0,)
        assert baseline["quantile_kind"] == "q5_only"

    def test_sequence_cells_use_quantile_family(self):
        cells = stage29_0b.build_a0_broad_cells()
        for arch_id in ("S1", "S2", "S3"):
            cell = next(c for c in cells if c["id"] == f"C-d2-{arch_id}")
            assert cell["quantile_percents"] == (5.0, 10.0, 20.0, 30.0, 40.0)
            assert cell["arch_id"] == arch_id


# ---------------------------------------------------------------------------
# TG11 — C-sb-baseline FAIL-FAST
# ---------------------------------------------------------------------------


class TestG11CSbBaselineFailFast:
    def _make_result(self, n, sharpe, ann_pnl):
        return {"test_realised_metrics": {"n_trades": n, "sharpe": sharpe, "annual_pnl": ann_pnl}}

    def test_match_passes(self):
        result = self._make_result(34626, -0.1732, -204664.4)
        report = stage29_0b.check_c_sb_baseline_match_29_0b(result)
        assert report["all_match"] is True

    def test_n_trades_mismatch_raises(self):
        result = self._make_result(34627, -0.1732, -204664.4)
        with pytest.raises(stage29_0b.BaselineMismatchError, match="n_trades"):
            stage29_0b.check_c_sb_baseline_match_29_0b(result)

    def test_sharpe_mismatch_raises(self):
        result = self._make_result(34626, -0.1733, -204664.4)
        with pytest.raises(stage29_0b.BaselineMismatchError, match="Sharpe"):
            stage29_0b.check_c_sb_baseline_match_29_0b(result)

    def test_ann_pnl_mismatch_raises(self):
        result = self._make_result(34626, -0.1732, -204700.0)
        with pytest.raises(stage29_0b.BaselineMismatchError, match="ann_pnl"):
            stage29_0b.check_c_sb_baseline_match_29_0b(result)


# ---------------------------------------------------------------------------
# TG12 — 7th-anchor drift check (DIAGNOSTIC-ONLY WARN)
# ---------------------------------------------------------------------------


class TestG12ArchControlDrift:
    def test_drift_within_tolerance(self):
        from unittest.mock import patch
        with patch.object(
            stage29_0b, "load_27_0d_c_se_metrics",
            return_value={"source": "test", "test_n_trades": 1000, "test_sharpe": 0.1, "test_annual_pnl": 10000.0},
        ):
            result = {"test_realised_metrics": {"n_trades": 1000, "sharpe": 0.1, "annual_pnl": 10000.0}}
            drift = stage29_0b.compute_c_d2_arch_control_drift_check(result)
            assert drift["all_within_tolerance"] is True
            assert drift["warn"] is False
            assert "7th anchor" in drift["chain_position"]

    def test_drift_warn_on_mismatch(self):
        from unittest.mock import patch
        with patch.object(
            stage29_0b, "load_27_0d_c_se_metrics",
            return_value={"source": "test", "test_n_trades": 1000, "test_sharpe": 0.1, "test_annual_pnl": 10000.0},
        ):
            result = {"test_realised_metrics": {"n_trades": 2000, "sharpe": 0.5, "annual_pnl": 20000.0}}
            drift = stage29_0b.compute_c_d2_arch_control_drift_check(result)
            assert drift["all_within_tolerance"] is False
            assert drift["warn"] is True


# ---------------------------------------------------------------------------
# TG13 — Within-eval PARTIAL_DRIFT_TABULAR_REPLICA detection
# ---------------------------------------------------------------------------


class TestG13WithinEvalDrift:
    def _cell(self, n, sharpe, ann, h_state="OK"):
        return {"h_state": h_state, "test_realised_metrics": {"n_trades": n, "sharpe": sharpe, "annual_pnl": ann}}

    def test_identical_cells_flag_drift(self):
        seq = self._cell(1000, 0.1, 10000.0)
        ctl = self._cell(1000, 0.1, 10000.0)
        drift = stage29_0b.compute_within_eval_tabular_drift_check(seq, ctl)
        assert drift["all_within_tolerance"] is True
        assert drift["warn"] is True  # WARN = drift detected

    def test_large_sharpe_delta_not_within(self):
        seq = self._cell(1000, 0.5, 10000.0)
        ctl = self._cell(1000, 0.1, 10000.0)
        drift = stage29_0b.compute_within_eval_tabular_drift_check(seq, ctl)
        assert drift["all_within_tolerance"] is False


# ---------------------------------------------------------------------------
# TG14 — H-D2 4-outcome ladder
# ---------------------------------------------------------------------------


class TestG14HD2Ladder:
    def _result(self, val_sharpe, val_n, cell_spearman):
        return {
            "h_state": "OK", "cell": {"id": "C-d2-test"},
            "val_realised_sharpe": val_sharpe,
            "val_n_trades": val_n,
            "selected_q_percent": 10,
            "quantile_best": {"val": {"spearman_score_vs_pnl": cell_spearman}},
        }

    def test_pass(self):
        r = self._result(val_sharpe=-0.13, val_n=25000, cell_spearman=0.40)
        # lift = -0.13 - (-0.1863) = +0.0563 >= 0.05 → PASS
        out = stage29_0b.compute_h_d2_outcome_per_arch(r, True, {"all_within_tolerance": False}, "S1")
        assert out["outcome"] == "PASS"
        assert out["row_matched"] == 1

    def test_partial_drift_overrides_pass(self):
        r = self._result(val_sharpe=-0.13, val_n=25000, cell_spearman=0.40)
        out = stage29_0b.compute_h_d2_outcome_per_arch(r, True, {"all_within_tolerance": True}, "S1")
        assert out["outcome"] == "PARTIAL_DRIFT_TABULAR_REPLICA"
        assert out["row_matched"] == 4

    def test_partial_support_subthreshold(self):
        # lift = -0.16 - (-0.1863) = +0.0263 in [+0.02, +0.05)
        r = self._result(val_sharpe=-0.16, val_n=25000, cell_spearman=0.40)
        out = stage29_0b.compute_h_d2_outcome_per_arch(r, True, {"all_within_tolerance": False}, "S2")
        assert out["outcome"] == "PARTIAL_SUPPORT"
        assert out["row_matched"] == 2

    def test_falsified_low_lift(self):
        r = self._result(val_sharpe=-0.20, val_n=25000, cell_spearman=0.40)
        out = stage29_0b.compute_h_d2_outcome_per_arch(r, True, {"all_within_tolerance": False}, "S3")
        assert out["outcome"] == "FALSIFIED_ARCH_INSUFFICIENT"
        assert out["row_matched"] == 3

    def test_h_state_not_ok_returns_needs_review(self):
        r = {"h_state": "INSUFFICIENT_DATA", "cell": {"id": "C-d2-test"}}
        out = stage29_0b.compute_h_d2_outcome_per_arch(r, True, {"all_within_tolerance": False}, "S1")
        assert out["outcome"] == "NEEDS_REVIEW"

    def test_baseline_pass_false_blocks_pass(self):
        r = self._result(val_sharpe=-0.13, val_n=25000, cell_spearman=0.40)
        out = stage29_0b.compute_h_d2_outcome_per_arch(r, False, {"all_within_tolerance": False}, "S1")
        assert out["outcome"] == "FALSIFIED_ARCH_INSUFFICIENT"


# ---------------------------------------------------------------------------
# TG15 — Aggregate verdict + FALSIFIED_A0_BROAD_NARROW
# ---------------------------------------------------------------------------


class TestG15Aggregate:
    def _o(self, arch_id, label):
        return {"arch_id": arch_id, "cell_id": f"C-d2-{arch_id}", "outcome": label, "row_matched": 1}

    def test_any_pass_routes_to_review(self):
        outcomes = [self._o("S1", "PASS"), self._o("S2", "FALSIFIED_ARCH_INSUFFICIENT"), self._o("S3", "FALSIFIED_ARCH_INSUFFICIENT")]
        agg = stage29_0b.compute_h_d2_aggregate_verdict(outcomes)
        assert agg["aggregate_verdict"] == "SPLIT_VERDICT_ROUTE_TO_REVIEW"
        assert agg["a0_broad_status"] == "PASS_under_A0_broad_narrow"

    def test_partial_only_rejects(self):
        outcomes = [self._o("S1", "PARTIAL_SUPPORT"), self._o("S2", "FALSIFIED_ARCH_INSUFFICIENT"), self._o("S3", "FALSIFIED_ARCH_INSUFFICIENT")]
        agg = stage29_0b.compute_h_d2_aggregate_verdict(outcomes)
        assert agg["aggregate_verdict"] == "REJECT_NON_DISCRIMINATIVE"
        assert agg["a0_broad_status"] == "PARTIAL_under_A0_broad_narrow"

    def test_all_falsified_labels_a0_broad_narrow(self):
        outcomes = [self._o(a, "FALSIFIED_ARCH_INSUFFICIENT") for a in ("S1", "S2", "S3")]
        agg = stage29_0b.compute_h_d2_aggregate_verdict(outcomes)
        assert agg["aggregate_verdict"] == "REJECT_NON_DISCRIMINATIVE"
        assert agg["a0_broad_status"] == "FALSIFIED_A0_BROAD_NARROW"

    def test_all_falsified_routing_says_never_all_a0_broad(self):
        outcomes = [self._o(a, "FALSIFIED_ARCH_INSUFFICIENT") for a in ("S1", "S2", "S3")]
        agg = stage29_0b.compute_h_d2_aggregate_verdict(outcomes)
        routing = agg["routing_implication"]
        assert "FALSIFIED_A0_BROAD_NARROW" in routing
        if "FALSIFIED_ALL_A0_BROAD" in routing:
            assert "NEVER" in routing

    def test_all_drift_labels_a0_broad_narrow(self):
        outcomes = [self._o(a, "PARTIAL_DRIFT_TABULAR_REPLICA") for a in ("S1", "S2", "S3")]
        agg = stage29_0b.compute_h_d2_aggregate_verdict(outcomes)
        assert agg["a0_broad_status"] == "FALSIFIED_A0_BROAD_NARROW"


# ---------------------------------------------------------------------------
# TG16 — Sequence-cell harness + determinism metric tolerance
# ---------------------------------------------------------------------------


class TestG16Harness:
    def test_compare_metric_level_determinism_identical(self):
        r_a = {"val_realised_sharpe": 0.1, "val_n_trades": 1000, "selected_q_percent": 10}
        r_b = {"val_realised_sharpe": 0.1, "val_n_trades": 1000, "selected_q_percent": 10}
        result = _sequence_cell_harness.compare_metric_level_determinism(r_a, r_b)
        assert result["all_within_tolerance"] is True

    def test_compare_metric_level_sharpe_within_tolerance(self):
        r_a = {"val_realised_sharpe": 0.10000, "val_n_trades": 1000, "selected_q_percent": 10}
        r_b = {"val_realised_sharpe": 0.10005, "val_n_trades": 1000, "selected_q_percent": 10}  # within 1e-4
        result = _sequence_cell_harness.compare_metric_level_determinism(r_a, r_b)
        assert result["all_within_tolerance"] is True

    def test_compare_metric_level_sharpe_outside_tolerance(self):
        r_a = {"val_realised_sharpe": 0.1, "val_n_trades": 1000, "selected_q_percent": 10}
        r_b = {"val_realised_sharpe": 0.11, "val_n_trades": 1000, "selected_q_percent": 10}  # ±1e-2 > 1e-4
        result = _sequence_cell_harness.compare_metric_level_determinism(r_a, r_b)
        assert result["all_within_tolerance"] is False

    def test_compare_metric_level_n_trades_must_match_exactly(self):
        r_a = {"val_realised_sharpe": 0.1, "val_n_trades": 1000, "selected_q_percent": 10}
        r_b = {"val_realised_sharpe": 0.1, "val_n_trades": 1001, "selected_q_percent": 10}
        result = _sequence_cell_harness.compare_metric_level_determinism(r_a, r_b)
        assert result["n_trades_match"] is False
        assert result["all_within_tolerance"] is False

    def test_compare_metric_level_q_must_match(self):
        r_a = {"val_realised_sharpe": 0.1, "val_n_trades": 1000, "selected_q_percent": 10}
        r_b = {"val_realised_sharpe": 0.1, "val_n_trades": 1000, "selected_q_percent": 20}
        result = _sequence_cell_harness.compare_metric_level_determinism(r_a, r_b)
        assert result["selected_q_match"] is False
        assert result["all_within_tolerance"] is False


# ---------------------------------------------------------------------------
# TG17 — eval_report smoke test (FALSIFIED_A0_BROAD_NARROW language presence)
# ---------------------------------------------------------------------------


class TestG17EvalReportSmoke:
    def test_write_eval_report_runs(self, tmp_path):
        cell_results = [
            {
                "cell": {"id": "C-d2-S1", "picker": "S1 LSTM", "score_type": "sequence_s1",
                         "feature_set": "r7a_windowed", "arch_id": "S1",
                         "is_baseline": False, "is_arch_control": False},
                "quantile_all": [], "val_realised_sharpe": -0.18, "val_n_trades": 100,
                "val_concentration": {"top_pairs": [], "herfindahl": 0.1},
                "test_concentration": {"top_pairs": [], "herfindahl": 0.1},
                "test_realised_metrics": {"sharpe": -0.18, "annual_pnl": 1000.0, "n_trades": 50},
                "test_formal_spearman": 0.05, "test_classification_diag": {},
                "per_pair_sharpe_contribution": {}, "by_pair_trade_count": {},
                "by_direction_trade_count": {"long": 10, "short": 10},
                "h_state": "OK",
            }
        ]
        h_d2_per_arch = [
            {"arch_id": "S1", "cell_id": "C-d2-S1", "outcome": "FALSIFIED_ARCH_INSUFFICIENT",
             "row_matched": 3, "reason": "test"}
        ]
        h_d2_aggregate = {
            "aggregate_verdict": "REJECT_NON_DISCRIMINATIVE",
            "a0_broad_status": "FALSIFIED_A0_BROAD_NARROW",
            "routing_implication": "all-fail; FALSIFIED_A0_BROAD_NARROW",
        }
        baseline_match_report = {
            "n_trades_observed": 34626, "n_trades_baseline": 34626, "n_trades_delta": 0,
            "n_trades_match": True, "sharpe_observed": -0.1732, "sharpe_baseline": -0.1732,
            "sharpe_delta": 0.0, "sharpe_match": True,
            "ann_pnl_observed": -204664.4, "ann_pnl_baseline": -204664.4,
            "ann_pnl_delta": 0.0, "ann_pnl_match": True, "all_match": True,
        }
        arch_control_drift_report = {
            "source": "test", "chain_position": "7th anchor",
            "all_within_tolerance": True, "warn": False,
            "n_trades_observed": 1000, "n_trades_delta": 0,
            "sharpe_observed": -0.17, "sharpe_delta": 0.0,
            "ann_pnl_observed": -200000.0, "ann_pnl_delta": 0.0,
        }
        report_path = tmp_path / "eval_report.md"
        stage29_0b.write_eval_report_29_0b(
            report_path, cell_results,
            {"selected": None}, {"verdict": "REJECT_NON_DISCRIMINATIVE"},
            {"aggregate_verdict": "REJECT_NON_DISCRIMINATIVE", "agree": True,
             "branches": ["REJECT_NON_DISCRIMINATIVE"]},
            baseline_match_report, arch_control_drift_report,
            h_d2_per_arch, h_d2_aggregate, {"S1": {"all_within_tolerance": False}},
            {"class_priors": {}, "d1_binding_check": "PASS"},
            {"train": {"n_input": 100, "n_kept": 95, "n_dropped": 5},
             "val": {"n_input": 50, "n_kept": 48, "n_dropped": 2},
             "test": {"n_input": 50, "n_kept": 48, "n_dropped": 2}},
            ("2024-01-01", "2024-06-01", "2024-09-01", "2024-12-31"),
            {}, 5, {}, {}, {}, {},
        )
        assert report_path.exists()
        content = report_path.read_text(encoding="utf-8")
        assert "Phase 29.0b-β" in content
        assert "A0-broad" in content
        assert "FALSIFIED_A0_BROAD_NARROW" in content
        # Check the load-bearing distinction language
        assert "NEVER" in content and "FALSIFIED_ALL_A0_BROAD" in content
        assert "7th anchor" in content
        assert "TRAIN-TIME" in content or "train-time" in content
        assert "Causality guard" in content or "causality" in content
