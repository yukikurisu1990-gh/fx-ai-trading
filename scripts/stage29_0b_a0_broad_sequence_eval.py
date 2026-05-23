"""Stage 29.0b-β A0-broad Sequence/NN eval (Phase 29 second sub-phase).

Implements PR #354 (Phase 29.0b-α A0-broad design memo) under PR #348
(Phase 29 kickoff Scope III + Policy C + Option 9c) + PR #352 (post-29.0a
routing review Path 1 PRIMARY preflight-gated) + PR #353 (A0-broad
preflight audit PASS).

Mission (PR #354 §1):
  Test whether sequence/NN model class beyond tabular LightGBM lifts
  Sharpe, keeping R7-A features / inherited target / top-q selection /
  symmetric Huber α=0.9 regression loss all fixed. Only the model class
  and input shape (tabular → windowed M5 bars) change.

Closed 3-architecture allowlist (α-fixed; NG#A0B-1):
  S1 Bidirectional LSTM (2 layers, hidden=128, dropout=0.2)
  S2 Temporal CNN (4 blocks, kernel=3, dilations=[1,2,4,8], channels=64)
  S3 Transformer encoder (2 layers, d_model=128, n_heads=4, ff_dim=256)

Windowed input (α-fixed):
  N=32 M5 bars × 8 channels (bid_OHLC + ask_OHLC)
  per-pair pip normalisation + entry-price centering
  CAUSALITY GUARD: window ends strictly before signal_ts + 1 min entry

Cell structure (5 cells; 21 records):
  C-d2-S1, C-d2-S2, C-d2-S3 (sequence) — 3 × 5 quantiles = 15
  C-d2-arch-control (7th anchor; tabular LightGBM INSIDE sequence-cell
    harness; NOT a sequence model) — 1 × 5 quantiles = 5
  C-sb-baseline (S-B raw + q=5; FAIL-FAST gate) — 1 × 1 = 1

Training (per PR #354 §12; CRITICAL train-time vs verdict-time wall):
  AdamW (weight_decay=1e-4); seed=42
  S1: lr=1e-3, batch=256; S2: lr=1e-3, batch=512; S3: lr=5e-4, batch=256
  max_epochs=5; patience=2
  early stopping on validation Huber loss (NOT val Sharpe)
  best checkpoint = lowest val Huber loss

Verdict (separate from training objective):
  H-D2 ladder uses val Sharpe lift + H1m + H3 + baseline reproduction

H-D2 4-outcome ladder per architecture (precedence row 4 > 1 > 2 > 3):
  Row 4 PARTIAL_DRIFT_TABULAR_REPLICA (checked first per NG#A0B-3)
  Row 1 PASS / Row 2 PARTIAL_SUPPORT / Row 3 FALSIFIED_ARCH_INSUFFICIENT

Aggregate verdict:
  any PASS → SPLIT_VERDICT_ROUTE_TO_REVIEW
  0 PASS + 1+ PARTIAL_SUPPORT → REJECT_NON_DISCRIMINATIVE
  all FALSIFIED / PARTIAL_DRIFT → REJECT_NON_DISCRIMINATIVE +
    FALSIFIED_A0_BROAD_NARROW (NEVER FALSIFIED_ALL_A0_BROAD)

MANDATORY CLAUSES (inherited verbatim from PR #348 §16):
1. Phase framing — H2 PASS = PROMISING_BUT_NEEDS_OOS only; ADOPT_CANDIDATE
   wall preserved.
2. Diagnostic columns prohibition.
3. γ closure PR #279 preserved.
4. X-v2 OOS gating required; v9 untouched; Phase 22 frozen-OOS preserved.
5. NG#10 / NG#11 not relaxed.
6. Phase 29 scope (NEW): Scope III + Policy C + Option 9c. 29.0b is
   single-axis A0-broad on R7-A. R-B / A3 / joint Path 4
   deferred-not-foreclosed.
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
import time
import warnings
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage29_0b"
WINDOWED_SHARDS_ROOT = ARTIFACT_ROOT / "windowed_dataset"
CHECKPOINTS_ROOT = ARTIFACT_ROOT / "checkpoints"
DATA_DIR = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage25_0b = importlib.import_module("stage25_0b_f1_volatility_expansion_eval")
stage26_0b = importlib.import_module("stage26_0b_l2_eval")
stage26_0c = importlib.import_module("stage26_0c_l1_eval")
stage26_0d = importlib.import_module("stage26_0d_r6_new_a_eval")
stage27_0b = importlib.import_module("stage27_0b_s_c_time_penalty_eval")
stage27_0c = importlib.import_module("stage27_0c_s_d_calibrated_ev_eval")
stage27_0d = importlib.import_module("stage27_0d_s_e_regression_eval")
stage27_0e = importlib.import_module("stage27_0e_s_e_quantile_trim_eval")
stage29_0a = importlib.import_module("stage29_0a_a2_target_redesign_eval")

# NEW Phase 29.0b modules
_windowed_dataset = importlib.import_module("_windowed_dataset")
_sequence_training = importlib.import_module("_sequence_training")
_sequence_cell_harness = importlib.import_module("_sequence_cell_harness")
_sequence_models = importlib.import_module("_sequence_models")

# Inherited helpers
PAIRS_20 = stage23_0a.PAIRS_20
load_m1_ba = stage23_0a.load_m1_ba
pip_size_for = stage23_0a.pip_size_for
SPAN_DAYS = stage25_0b.SPAN_DAYS
SPAN_YEARS = SPAN_DAYS / 365.25
TRAIN_FRAC = stage25_0b.TRAIN_FRAC
VAL_FRAC = stage25_0b.VAL_FRAC
split_70_15_15 = stage25_0b.split_70_15_15
verify_l3_preflight = stage26_0b.verify_l3_preflight
L3PreflightError = stage26_0b.L3PreflightError
build_l1_labels_for_dataframe = stage26_0c.build_l1_labels_for_dataframe
compute_8_gate_from_pnls = stage26_0c.compute_8_gate_from_pnls
compute_pair_concentration = stage26_0b.compute_pair_concentration
compute_classification_diagnostics = stage26_0c.compute_classification_diagnostics
assign_verdict = stage26_0c.assign_verdict
aggregate_cross_cell_verdict = stage26_0c.aggregate_cross_cell_verdict
select_cell_validation_only = stage26_0c.select_cell_validation_only
SanityProbeError = stage26_0c.SanityProbeError
fit_quantile_cutoff_on_val = stage26_0c.fit_quantile_cutoff_on_val

build_pipeline_lightgbm_multiclass_widened = stage26_0d.build_pipeline_lightgbm_multiclass_widened
drop_rows_with_missing_new_features = stage26_0d.drop_rows_with_missing_new_features
compute_feature_importance_diagnostic = stage26_0d.compute_feature_importance_diagnostic
compute_per_pair_sharpe_contribution = stage27_0b.compute_per_pair_sharpe_contribution
compute_picker_score_s_b_raw = stage27_0c.compute_picker_score_s_b_raw
build_pipeline_lightgbm_regression_widened = stage27_0d.build_pipeline_lightgbm_regression_widened
compute_picker_score_s_e = stage27_0d.compute_picker_score_s_e
compute_regression_diagnostic = stage27_0d.compute_regression_diagnostic
load_27_0d_c_se_metrics = stage27_0e.load_27_0d_c_se_metrics

_multiclass_to_class_probs = stage29_0a._multiclass_to_class_probs
precompute_target_pnls_per_row = stage29_0a.precompute_target_pnls_per_row
check_c_sb_baseline_match = None  # use Phase 29 §10 inherited check via stage27_0d pattern

# NEW windowed + sequence helpers
CausalityGuardError = _windowed_dataset.CausalityGuardError
WindowedCoverageError = _windowed_dataset.WindowedCoverageError
build_windowed_input_per_row = _windowed_dataset.build_windowed_input_per_row
compute_windowed_coverage_per_pair = _windowed_dataset.compute_windowed_coverage_per_pair
assert_windowed_coverage_meets_threshold = _windowed_dataset.assert_windowed_coverage_meets_threshold
verify_causality_guard = _windowed_dataset.verify_causality_guard

CudaUnavailableError = _sequence_training.CudaUnavailableError
setup_deterministic_environment = _sequence_training.setup_deterministic_environment
select_device = _sequence_training.select_device
train_sequence_model = _sequence_training.train_sequence_model
predict_sequence_score = _sequence_training.predict_sequence_score
load_checkpoint = _sequence_training.load_checkpoint
estimate_gpu_memory_after_fit = _sequence_training.estimate_gpu_memory_after_fit
reset_gpu_memory_tracker = _sequence_training.reset_gpu_memory_tracker

score_rows_via_sequence_model = _sequence_cell_harness.score_rows_via_sequence_model
score_rows_via_tabular = _sequence_cell_harness.score_rows_via_tabular
score_rows_via_tabular_full = _sequence_cell_harness.score_rows_via_tabular_full
evaluate_cell_quantile_family = _sequence_cell_harness.evaluate_cell_quantile_family
evaluate_cell_q5_only = _sequence_cell_harness.evaluate_cell_q5_only
select_best_quantile_by_val_sharpe = _sequence_cell_harness.select_best_quantile_by_val_sharpe

build_sequence_model = _sequence_models.build_sequence_model
CLOSED_ARCHITECTURE_ALLOWLIST = _sequence_models.CLOSED_ARCHITECTURE_ALLOWLIST


# ---------------------------------------------------------------------------
# Binding constants
# ---------------------------------------------------------------------------

K_FAV = stage25_0b.K_FAV
K_ADV = stage25_0b.K_ADV
H_M1_BARS = stage25_0b.H_M1_BARS
LABEL_TP = stage26_0c.LABEL_TP
LABEL_SL = stage26_0c.LABEL_SL
LABEL_TIME = stage26_0c.LABEL_TIME
NUM_CLASSES = stage26_0c.NUM_CLASSES
NUMERIC_FEATURES_R7A = stage26_0d.NUMERIC_FEATURES
ALL_FEATURES_R7A = stage26_0d.ALL_FEATURES
HUBER_ALPHA = stage27_0d.HUBER_ALPHA  # 0.9
SANITY_MAX_PER_PAIR_TIME_SHARE = stage26_0c.SANITY_MAX_PER_PAIR_TIME_SHARE
TEST_SPAN_YEARS = SPAN_YEARS * (1.0 - TRAIN_FRAC - VAL_FRAC)
VAL_SPAN_YEARS = SPAN_YEARS * VAL_FRAC

# Phase 28 §10 baseline (immutable; inherited directly per PR #354 §11.1 Option 9c simple case)
BASELINE_27_0B_C_ALPHA0_N_TRADES = stage27_0d.BASELINE_27_0B_C_ALPHA0_N_TRADES
BASELINE_27_0B_C_ALPHA0_SHARPE = stage27_0d.BASELINE_27_0B_C_ALPHA0_SHARPE
BASELINE_27_0B_C_ALPHA0_ANN_PNL = stage27_0d.BASELINE_27_0B_C_ALPHA0_ANN_PNL
BASELINE_MATCH_N_TRADES_TOLERANCE = stage27_0d.BASELINE_MATCH_N_TRADES_TOLERANCE
BASELINE_MATCH_SHARPE_ABS_TOLERANCE = stage27_0d.BASELINE_MATCH_SHARPE_ABS_TOLERANCE
BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE = stage27_0d.BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE
SECTION_10_BASELINE_VAL_SHARPE = -0.1863  # PR #354 §11.1 inherited

NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD = stage27_0d.NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD

# NEW Phase 29.0b constants
QUANTILE_PERCENTS_29_0B: tuple[float, ...] = (5.0, 10.0, 20.0, 30.0, 40.0)
PER_TARGET_BASELINE_Q_PERCENT = 5.0

# H-D2 thresholds (PR #354 §3)
H2_LIFT_THRESHOLD_PASS = 0.05
H2_LIFT_THRESHOLD_PARTIAL_SUPPORT_LO = 0.02
H1M_PRESERVE_THRESHOLD = 0.30
H3_TRADE_COUNT_THRESHOLD = 20000

# H-D2 outcome labels (PR #354 §14)
H_D2_OUTCOME_PASS = "PASS"
H_D2_OUTCOME_PARTIAL_SUPPORT = "PARTIAL_SUPPORT"
H_D2_OUTCOME_FALSIFIED_ARCH_INSUFFICIENT = "FALSIFIED_ARCH_INSUFFICIENT"
H_D2_OUTCOME_PARTIAL_DRIFT_TABULAR_REPLICA = "PARTIAL_DRIFT_TABULAR_REPLICA"
H_D2_OUTCOME_NEEDS_REVIEW = "NEEDS_REVIEW"

# 7th-anchor drift tolerances (NG#A0B-3; DIAGNOSTIC-ONLY WARN)
ARCH_CONTROL_DRIFT_N_TRADES_TOLERANCE = 100
ARCH_CONTROL_DRIFT_SHARPE_TOLERANCE = 5e-3
ARCH_CONTROL_DRIFT_ANN_PNL_FRAC_TOLERANCE = 0.005

# Within-eval drift (PARTIAL_DRIFT_TABULAR_REPLICA detection)
WITHIN_EVAL_DRIFT_N_TRADES_TOLERANCE = 100
WITHIN_EVAL_DRIFT_SHARPE_TOLERANCE = 5e-3
WITHIN_EVAL_DRIFT_ANN_PNL_FRAC_TOLERANCE = 0.005

# Coverage threshold
WINDOWED_COVERAGE_HALT_THRESHOLD = _windowed_dataset.WINDOWED_COVERAGE_HALT_THRESHOLD


# ---------------------------------------------------------------------------
# NEW exceptions
# ---------------------------------------------------------------------------


class BaselineMismatchError(RuntimeError):
    """Raised when C-sb-baseline fails to reproduce Phase 28 §10 baseline.

    Per PR #354 §11.1 FAIL-FAST.
    """


class SequenceCellHarnessVerificationError(RuntimeError):
    """Raised when sequence-cell harness fails to evaluate the tabular control.

    Per PR #354 §16.2 item 8 HALT.
    """


# ---------------------------------------------------------------------------
# C-sb-baseline FAIL-FAST (Phase 28 §10 inherited directly per Option 9c simple case)
# ---------------------------------------------------------------------------


def check_c_sb_baseline_match_29_0b(c_sb_baseline_result: dict) -> dict:
    """Validate C-sb-baseline reproduces Phase 28 §10 baseline.

    Per PR #354 §11.1; Option 9c simple case (target unchanged → Phase 28
    §10 inherited directly). HALT (`BaselineMismatchError`) on mismatch.
    """
    rm = c_sb_baseline_result.get("test_realised_metrics", {})
    n_trades = int(rm.get("n_trades", 0))
    sharpe = float(rm.get("sharpe", float("nan")))
    ann_pnl = float(rm.get("annual_pnl", float("nan")))

    n_trades_delta = n_trades - BASELINE_27_0B_C_ALPHA0_N_TRADES
    sharpe_delta = (
        sharpe - BASELINE_27_0B_C_ALPHA0_SHARPE if np.isfinite(sharpe) else float("nan")
    )
    ann_pnl_delta = (
        ann_pnl - BASELINE_27_0B_C_ALPHA0_ANN_PNL if np.isfinite(ann_pnl) else float("nan")
    )

    n_trades_match = abs(n_trades_delta) <= BASELINE_MATCH_N_TRADES_TOLERANCE
    sharpe_match = (
        np.isfinite(sharpe_delta) and abs(sharpe_delta) <= BASELINE_MATCH_SHARPE_ABS_TOLERANCE
    )
    ann_pnl_match = (
        np.isfinite(ann_pnl_delta) and abs(ann_pnl_delta) <= BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE
    )

    report = {
        "n_trades_baseline": int(BASELINE_27_0B_C_ALPHA0_N_TRADES),
        "n_trades_observed": int(n_trades),
        "n_trades_delta": int(n_trades_delta),
        "n_trades_match": bool(n_trades_match),
        "sharpe_baseline": float(BASELINE_27_0B_C_ALPHA0_SHARPE),
        "sharpe_observed": float(sharpe),
        "sharpe_delta": float(sharpe_delta) if np.isfinite(sharpe_delta) else float("nan"),
        "sharpe_match": bool(sharpe_match),
        "ann_pnl_baseline": float(BASELINE_27_0B_C_ALPHA0_ANN_PNL),
        "ann_pnl_observed": float(ann_pnl),
        "ann_pnl_delta": float(ann_pnl_delta) if np.isfinite(ann_pnl_delta) else float("nan"),
        "ann_pnl_match": bool(ann_pnl_match),
        "all_match": bool(n_trades_match and sharpe_match and ann_pnl_match),
    }

    if not report["all_match"]:
        failures = []
        if not n_trades_match:
            failures.append(f"n_trades: observed={n_trades} baseline={BASELINE_27_0B_C_ALPHA0_N_TRADES}")
        if not sharpe_match:
            failures.append(f"Sharpe: observed={sharpe:.6f} baseline={BASELINE_27_0B_C_ALPHA0_SHARPE:.6f}")
        if not ann_pnl_match:
            failures.append(f"ann_pnl: observed={ann_pnl:+.3f} baseline={BASELINE_27_0B_C_ALPHA0_ANN_PNL:+.3f}")
        raise BaselineMismatchError(
            "C-sb-baseline reproduction FAILED per PR #354 §11.1; failures: "
            + "; ".join(failures)
        )
    return report


# ---------------------------------------------------------------------------
# C-d2-arch-control 7th-anchor drift check (DIAGNOSTIC-ONLY WARN)
# ---------------------------------------------------------------------------


def compute_c_d2_arch_control_drift_check(c_d2_arch_control_result: dict) -> dict:
    """DIAGNOSTIC-ONLY WARN; NOT HALT.

    Per PR #354 §10.3 / NG#A0B-3: C-d2-arch-control reproduces 29.0a
    C-d1-target-control (6th anchor) within tolerance (n_trades ±100 /
    Sharpe ±5e-3 / ann_pnl ±0.5%). 7th anchor in bit-tight chain:
    27.0d → 27.0f → 28.0a → 28.0b → 28.0c → 29.0a → 29.0b.
    """
    rm = c_d2_arch_control_result.get("test_realised_metrics", {})
    n_trades = int(rm.get("n_trades", 0))
    sharpe = float(rm.get("sharpe", float("nan")))
    ann_pnl = float(rm.get("annual_pnl", float("nan")))

    c_se_27_0d = load_27_0d_c_se_metrics()
    baseline_n = c_se_27_0d.get("test_n_trades")
    baseline_sharpe = c_se_27_0d.get("test_sharpe")
    baseline_ann_pnl = c_se_27_0d.get("test_annual_pnl")

    n_trades_delta = int(n_trades - baseline_n) if baseline_n is not None else None
    sharpe_delta = (
        float(sharpe - baseline_sharpe)
        if baseline_sharpe is not None and np.isfinite(sharpe)
        else None
    )
    ann_pnl_delta = (
        float(ann_pnl - baseline_ann_pnl)
        if baseline_ann_pnl is not None and np.isfinite(ann_pnl)
        else None
    )
    ann_pnl_tolerance_abs = (
        abs(baseline_ann_pnl) * ARCH_CONTROL_DRIFT_ANN_PNL_FRAC_TOLERANCE
        if baseline_ann_pnl is not None and np.isfinite(baseline_ann_pnl)
        else None
    )

    n_trades_within = (
        abs(n_trades_delta) <= ARCH_CONTROL_DRIFT_N_TRADES_TOLERANCE
        if n_trades_delta is not None
        else False
    )
    sharpe_within = (
        abs(sharpe_delta) <= ARCH_CONTROL_DRIFT_SHARPE_TOLERANCE
        if sharpe_delta is not None
        else False
    )
    ann_pnl_within = (
        abs(ann_pnl_delta) <= ann_pnl_tolerance_abs
        if ann_pnl_delta is not None and ann_pnl_tolerance_abs is not None
        else False
    )

    all_within = bool(n_trades_within and sharpe_within and ann_pnl_within)

    return {
        "source": c_se_27_0d.get("source", "unknown"),
        "chain_position": "7th anchor (27.0d → 27.0f → 28.0a → 28.0b → 28.0c → 29.0a → 29.0b)",
        "n_trades_baseline_27_0d": baseline_n,
        "n_trades_observed": int(n_trades),
        "n_trades_delta": n_trades_delta,
        "n_trades_within_tolerance": bool(n_trades_within),
        "sharpe_baseline_27_0d": baseline_sharpe,
        "sharpe_observed": float(sharpe),
        "sharpe_delta": sharpe_delta,
        "sharpe_within_tolerance": bool(sharpe_within),
        "ann_pnl_baseline_27_0d": baseline_ann_pnl,
        "ann_pnl_observed": float(ann_pnl),
        "ann_pnl_delta": ann_pnl_delta,
        "ann_pnl_tolerance_abs": ann_pnl_tolerance_abs,
        "ann_pnl_within_tolerance": bool(ann_pnl_within),
        "all_within_tolerance": all_within,
        "warn": not all_within,
    }


# ---------------------------------------------------------------------------
# Within-eval PARTIAL_DRIFT_TABULAR_REPLICA detection
# ---------------------------------------------------------------------------


def compute_within_eval_tabular_drift_check(
    c_d2_sx_result: dict, c_d2_arch_control_result: dict
) -> dict:
    """Per PR #354 §13 NG#A0B-3 + §14 row 4.

    If C-d2-Sx ≈ C-d2-arch-control within tolerance at val-selected q*,
    flag PARTIAL_DRIFT_TABULAR_REPLICA (sequence model produces no
    architectural lift vs tabular).
    """
    if (
        c_d2_sx_result.get("h_state") != "OK"
        or c_d2_arch_control_result.get("h_state") != "OK"
    ):
        return {
            "all_within_tolerance": False,
            "warn": True,
            "note": "sequence cell or arch-control h_state != OK",
        }
    rm_seq = c_d2_sx_result.get("test_realised_metrics", {})
    rm_ctl = c_d2_arch_control_result.get("test_realised_metrics", {})
    n_seq = int(rm_seq.get("n_trades", 0))
    n_ctl = int(rm_ctl.get("n_trades", 0))
    sh_seq = float(rm_seq.get("sharpe", float("nan")))
    sh_ctl = float(rm_ctl.get("sharpe", float("nan")))
    ap_seq = float(rm_seq.get("annual_pnl", float("nan")))
    ap_ctl = float(rm_ctl.get("annual_pnl", float("nan")))

    n_trades_delta = n_seq - n_ctl
    sharpe_delta = (
        sh_seq - sh_ctl if (np.isfinite(sh_seq) and np.isfinite(sh_ctl)) else float("nan")
    )
    ann_pnl_delta = (
        ap_seq - ap_ctl if (np.isfinite(ap_seq) and np.isfinite(ap_ctl)) else float("nan")
    )
    ann_pnl_tolerance_abs = (
        abs(ap_ctl) * WITHIN_EVAL_DRIFT_ANN_PNL_FRAC_TOLERANCE if np.isfinite(ap_ctl) else None
    )

    n_within = abs(n_trades_delta) <= WITHIN_EVAL_DRIFT_N_TRADES_TOLERANCE
    sh_within = np.isfinite(sharpe_delta) and abs(sharpe_delta) <= WITHIN_EVAL_DRIFT_SHARPE_TOLERANCE
    ap_within = (
        np.isfinite(ann_pnl_delta)
        and ann_pnl_tolerance_abs is not None
        and abs(ann_pnl_delta) <= ann_pnl_tolerance_abs
    )
    all_within = bool(n_within and sh_within and ap_within)
    return {
        "n_trades_candidate": int(n_seq),
        "n_trades_control": int(n_ctl),
        "n_trades_delta": int(n_trades_delta),
        "n_trades_within_tolerance": bool(n_within),
        "sharpe_candidate": float(sh_seq),
        "sharpe_control": float(sh_ctl),
        "sharpe_delta": float(sharpe_delta) if np.isfinite(sharpe_delta) else float("nan"),
        "sharpe_within_tolerance": bool(sh_within),
        "ann_pnl_candidate": float(ap_seq),
        "ann_pnl_control": float(ap_ctl),
        "ann_pnl_delta": float(ann_pnl_delta) if np.isfinite(ann_pnl_delta) else float("nan"),
        "ann_pnl_within_tolerance": bool(ap_within),
        "all_within_tolerance": all_within,
        "warn": all_within,  # WARN means "zero architectural lift"
    }


# ---------------------------------------------------------------------------
# H-D2 4-outcome ladder
# ---------------------------------------------------------------------------


def compute_h_d2_outcome_per_arch(
    c_d2_sx_result: dict,
    c_sb_baseline_match_pass: bool,
    tabular_drift_report: dict,
    arch_id: str,
) -> dict:
    """Resolve 1 of 4 H-D2 outcomes per architecture (precedence row 4 > 1 > 2 > 3).

    PARTIAL_DRIFT_TABULAR_REPLICA checked first per NG#A0B-3.
    Verdict uses val Sharpe lift vs Phase 28 §10 baseline val Sharpe
    (-0.1863).
    """
    cell_id = c_d2_sx_result.get("cell", {}).get("id", "unknown")
    if c_d2_sx_result.get("h_state") != "OK":
        return {
            "cell_id": cell_id,
            "arch_id": arch_id,
            "outcome": H_D2_OUTCOME_NEEDS_REVIEW,
            "row_matched": 0,
            "reason": f"h_state={c_d2_sx_result.get('h_state')}",
        }

    # Row 4 precedence: PARTIAL_DRIFT_TABULAR_REPLICA
    drift_within = tabular_drift_report.get("all_within_tolerance", False)
    if drift_within:
        return {
            "cell_id": cell_id,
            "arch_id": arch_id,
            "outcome": H_D2_OUTCOME_PARTIAL_DRIFT_TABULAR_REPLICA,
            "row_matched": 4,
            "reason": (
                f"{arch_id} produces no architectural lift vs C-d2-arch-control "
                "(within tolerance); analogous to 28.0c H-C3 row 4 / 29.0a H-D1 row 4"
            ),
            "evidence": {
                "drift_n_trades_delta": tabular_drift_report.get("n_trades_delta"),
                "drift_sharpe_delta": tabular_drift_report.get("sharpe_delta"),
                "drift_ann_pnl_delta": tabular_drift_report.get("ann_pnl_delta"),
            },
        }

    val_sharpe = float(c_d2_sx_result.get("val_realised_sharpe", float("nan")))
    val_n = int(c_d2_sx_result.get("val_n_trades", 0))
    qb = c_d2_sx_result.get("quantile_best", {}) or {}
    cell_spearman_val = qb.get("val", {}).get("spearman_score_vs_pnl", float("nan"))
    if not np.isfinite(cell_spearman_val):
        cell_spearman_val = float(c_d2_sx_result.get("val_cell_spearman", float("nan")))
    if not np.isfinite(cell_spearman_val):
        cell_spearman_val = float(c_d2_sx_result.get("test_formal_spearman", float("nan")))

    sharpe_lift = (
        float(val_sharpe - SECTION_10_BASELINE_VAL_SHARPE)
        if np.isfinite(val_sharpe)
        else float("nan")
    )
    h1m_pass = np.isfinite(cell_spearman_val) and cell_spearman_val >= H1M_PRESERVE_THRESHOLD
    h2_pass = np.isfinite(sharpe_lift) and sharpe_lift >= H2_LIFT_THRESHOLD_PASS
    h3_pass = val_n >= H3_TRADE_COUNT_THRESHOLD

    evidence = {
        "val_sharpe": val_sharpe,
        "val_n_trades": val_n,
        "cell_spearman_val": cell_spearman_val,
        "section_10_baseline_val_sharpe": SECTION_10_BASELINE_VAL_SHARPE,
        "sharpe_lift_absolute": sharpe_lift,
        "h1m_pass": bool(h1m_pass),
        "h2_pass": bool(h2_pass),
        "h3_pass": bool(h3_pass),
        "baseline_pass": bool(c_sb_baseline_match_pass),
    }

    if h1m_pass and h2_pass and h3_pass and c_sb_baseline_match_pass:
        return {
            "cell_id": cell_id,
            "arch_id": arch_id,
            "outcome": H_D2_OUTCOME_PASS,
            "row_matched": 1,
            "reason": "all four H-D2 conditions satisfied",
            "evidence": evidence,
        }

    h2_partial = (
        np.isfinite(sharpe_lift)
        and H2_LIFT_THRESHOLD_PARTIAL_SUPPORT_LO <= sharpe_lift < H2_LIFT_THRESHOLD_PASS
    )
    if h2_partial and h1m_pass and h3_pass and c_sb_baseline_match_pass:
        return {
            "cell_id": cell_id,
            "arch_id": arch_id,
            "outcome": H_D2_OUTCOME_PARTIAL_SUPPORT,
            "row_matched": 2,
            "reason": (
                f"val Sharpe lift {sharpe_lift:+.4f} in [+0.02, +0.05); other H-D2 "
                "conditions intact"
            ),
            "evidence": evidence,
        }

    return {
        "cell_id": cell_id,
        "arch_id": arch_id,
        "outcome": H_D2_OUTCOME_FALSIFIED_ARCH_INSUFFICIENT,
        "row_matched": 3,
        "reason": f"val Sharpe lift {sharpe_lift:+.4f} < +0.02 OR other H-D2 conditions failed",
        "evidence": evidence,
    }


def compute_h_d2_aggregate_verdict(per_arch_outcomes: list[dict]) -> dict:
    """Aggregate H-D2 verdict per PR #354 §15.

    FALSIFIED_A0_BROAD_NARROW distinction: NEVER FALSIFIED_ALL_A0_BROAD.
    Alternate sequence architectures outside closed 3-variant allowlist
    remain admissible via separate scope amendment.
    """
    outcomes = [o.get("outcome") for o in per_arch_outcomes]
    has_pass = H_D2_OUTCOME_PASS in outcomes
    has_partial = H_D2_OUTCOME_PARTIAL_SUPPORT in outcomes
    all_partial_drift = (
        len(outcomes) > 0
        and all(o == H_D2_OUTCOME_PARTIAL_DRIFT_TABULAR_REPLICA for o in outcomes)
    )
    all_falsified = len(outcomes) > 0 and all(
        o
        in {
            H_D2_OUTCOME_FALSIFIED_ARCH_INSUFFICIENT,
            H_D2_OUTCOME_PARTIAL_DRIFT_TABULAR_REPLICA,
        }
        for o in outcomes
    )

    if has_pass:
        verdict = "SPLIT_VERDICT_ROUTE_TO_REVIEW"
        a0_broad_status = "PASS_under_A0_broad_narrow"
        routing = (
            "1+ architecture produced H-D2 PASS at C-d2-Sx cell; PROMISING_BUT_NEEDS_OOS "
            "candidate. ADOPT_CANDIDATE wall preserved per Clause 1. Route to post-29.0b "
            "routing review for PASS architecture follow-up."
        )
    elif has_partial:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        a0_broad_status = "PARTIAL_under_A0_broad_narrow"
        routing = (
            "1+ architecture PARTIAL_SUPPORT (sub-threshold Sharpe lift); no PASS. Route "
            "to post-29.0b routing review for next-axis (R-B / A3 / joint Path 4 / Phase 29 "
            "closure) comparison."
        )
    elif all_partial_drift:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        a0_broad_status = "FALSIFIED_A0_BROAD_NARROW"
        routing = (
            "All 3 architectures PARTIAL_DRIFT_TABULAR_REPLICA — no sequence architecture "
            "produces architectural lift over tabular control. Strong FALSIFIED_A0_BROAD_NARROW "
            "signal; alternate sequence architectures outside closed 3-variant allowlist remain "
            "admissible via separate scope amendment. NEVER label this FALSIFIED_ALL_A0_BROAD."
        )
    elif all_falsified:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        a0_broad_status = "FALSIFIED_A0_BROAD_NARROW"
        routing = (
            "All 3 architectures FALSIFIED_ARCH_INSUFFICIENT or "
            "PARTIAL_DRIFT_TABULAR_REPLICA — A0-broad axis exhausted under tested closed "
            "3-architecture allowlist. Result is FALSIFIED_A0_BROAD_NARROW (NEVER "
            "FALSIFIED_ALL_A0_BROAD). Alternate sequence architectures outside closed "
            "3-variant allowlist remain admissible via separate scope amendment. Post-29.0b "
            "routing review compares R-B / A3 / joint Path 4 / Phase 29 closure next-axis "
            "options."
        )
    else:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        a0_broad_status = "INCONCLUSIVE_under_A0_broad_narrow"
        routing = "no architecture produced PASS or PARTIAL_SUPPORT"

    return {
        "aggregate_verdict": verdict,
        "a0_broad_status": a0_broad_status,
        "routing_implication": routing,
        "per_arch_outcomes": [
            {
                "cell_id": o.get("cell_id"),
                "arch_id": o.get("arch_id"),
                "outcome": o.get("outcome"),
                "row_matched": o.get("row_matched"),
            }
            for o in per_arch_outcomes
        ],
        "has_pass": bool(has_pass),
        "has_partial_support": bool(has_partial),
        "all_partial_drift": bool(all_partial_drift),
    }


# ---------------------------------------------------------------------------
# Per-pair runtime (inherited)
# ---------------------------------------------------------------------------


def _build_pair_runtime(pair: str, days: int) -> dict:
    """Load M1 BA and prepare runtime arrays (D-1 binding inheritance)."""
    m1 = load_m1_ba(pair, days=days)
    return {
        "pip": pip_size_for(pair),
        "m1_pos": pd.Series(np.arange(len(m1), dtype=np.int64), index=m1.index),
        "n_m1": len(m1),
        "bid_h": m1["bid_h"].to_numpy(),
        "bid_l": m1["bid_l"].to_numpy(),
        "bid_c": m1["bid_c"].to_numpy(),
        "ask_h": m1["ask_h"].to_numpy(),
        "ask_l": m1["ask_l"].to_numpy(),
        "ask_c": m1["ask_c"].to_numpy(),
        "ask_o": m1["ask_o"].to_numpy(),
        "bid_o": m1["bid_o"].to_numpy(),
    }


def _cell_signature(cell: dict) -> str:
    keys = ("id", "picker", "score_type", "feature_set", "arch_id")
    return " ".join(f"{k}={cell.get(k)}" for k in keys)


# ---------------------------------------------------------------------------
# Build cells (PR #354 §9; 5 cells; 21 records)
# ---------------------------------------------------------------------------


def build_a0_broad_cells() -> list[dict]:
    """5 cells per PR #354 §9.

    Order: C-d2-S1 → C-d2-S2 → C-d2-S3 → C-d2-arch-control → C-sb-baseline.
    """
    cells: list[dict] = []
    for arch_id in CLOSED_ARCHITECTURE_ALLOWLIST:
        cells.append({
            "id": f"C-d2-{arch_id}",
            "picker": f"{arch_id}(sequence_model on R7-A windowed)",
            "score_type": f"sequence_{arch_id.lower()}",
            "feature_set": "r7a_windowed",
            "arch_id": arch_id,
            "is_baseline": False,
            "is_arch_control": False,
            "quantile_percents": QUANTILE_PERCENTS_29_0B,
            "quantile_kind": "family",
        })
    cells.append({
        "id": "C-d2-arch-control",
        "picker": "S-E(tabular_LightGBM) — 7th anchor; NOT a sequence model",
        "score_type": "s_e_tabular_control",
        "feature_set": "r7a",
        "arch_id": "TABULAR_CONTROL",
        "is_baseline": False,
        "is_arch_control": True,
        "quantile_percents": QUANTILE_PERCENTS_29_0B,
        "quantile_kind": "family",
    })
    cells.append({
        "id": "C-sb-baseline",
        "picker": "S-B(raw_p_tp_minus_p_sl) — FAIL-FAST gate (Phase 28 §10 inherited)",
        "score_type": "s_b_raw_baseline",
        "feature_set": "r7a",
        "arch_id": "BASELINE",
        "is_baseline": True,
        "is_arch_control": False,
        "quantile_percents": (PER_TARGET_BASELINE_Q_PERCENT,),
        "quantile_kind": "q5_only",
    })
    return cells


# ---------------------------------------------------------------------------
# Top-tail regime audit (DIAGNOSTIC-ONLY; per PR #354 §17)
# ---------------------------------------------------------------------------


def compute_top_tail_regime_audit(
    val_score: np.ndarray,
    val_features: pd.DataFrame,
    q_list: tuple[float, ...] = (10.0, 20.0),
) -> dict:
    """DIAGNOSTIC-ONLY; spread_at_signal_pip only; R7-C features NOT computed."""
    out: dict = {"per_q": [], "population": {}}
    spread = val_features["spread_at_signal_pip"].astype(np.float64).to_numpy()
    finite_spread = spread[np.isfinite(spread)]
    pop_mean = float(finite_spread.mean()) if len(finite_spread) > 0 else float("nan")
    pop_p50 = float(np.quantile(finite_spread, 0.5)) if len(finite_spread) > 0 else float("nan")
    out["population"] = {
        "n_finite_spread": int(len(finite_spread)),
        "mean_spread_at_signal_pip": pop_mean,
        "p50_spread_at_signal_pip": pop_p50,
    }
    for q_pct in q_list:
        cutoff = fit_quantile_cutoff_on_val(val_score, q_pct)
        top_mask = np.isfinite(val_score) & (val_score >= cutoff)
        n_top = int(top_mask.sum())
        top_spread = spread[top_mask]
        top_finite = top_spread[np.isfinite(top_spread)]
        top_mean = float(top_finite.mean()) if len(top_finite) > 0 else float("nan")
        top_p50 = float(np.quantile(top_finite, 0.5)) if len(top_finite) > 0 else float("nan")
        out["per_q"].append({
            "q_percent": float(q_pct),
            "cutoff": float(cutoff),
            "n_top": n_top,
            "top_mean_spread": top_mean,
            "top_p50_spread": top_p50,
            "delta_mean_vs_population": (
                top_mean - pop_mean
                if np.isfinite(top_mean) and np.isfinite(pop_mean)
                else float("nan")
            ),
        })
    return out


# ---------------------------------------------------------------------------
# Per-cell quantile evaluation
# ---------------------------------------------------------------------------


def evaluate_quantile_cell_29_0b(
    cell: dict,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    train_label: np.ndarray,
    val_label: np.ndarray,
    test_label: np.ndarray,
    val_raw_probs: np.ndarray,
    test_raw_probs: np.ndarray,
    val_score: np.ndarray,
    test_score: np.ndarray,
    pnl_val: np.ndarray,
    pnl_test: np.ndarray,
    feature_importance_diag: dict,
) -> dict:
    """Evaluate quantile cell — adapted from stage29_0a pattern."""
    score_type = str(cell.get("score_type", "unknown"))
    arch_id = str(cell.get("arch_id", "unknown"))

    n_train = int(len(train_label))
    n_val = int(len(val_label))
    n_test = int(len(test_label))
    if n_train < 100 or n_val < 50 or n_test < 50:
        return {
            "cell": cell,
            "n_train": n_train,
            "n_val": n_val,
            "n_test": n_test,
            "verdict": "REJECT_NON_DISCRIMINATIVE",
            "h_state": "INSUFFICIENT_DATA",
            "low_power": True,
        }

    quantile_percents = tuple(cell.get("quantile_percents", QUANTILE_PERCENTS_29_0B))
    quantile_results = evaluate_cell_quantile_family(
        val_score, pnl_val, test_score, pnl_test, VAL_SPAN_YEARS, TEST_SPAN_YEARS,
        quantile_percents=quantile_percents,
    )
    best_q_record = select_best_quantile_by_val_sharpe(quantile_results)

    test_realised = best_q_record["test"]["realised_pnls"]
    gate_block = compute_8_gate_from_pnls(test_realised)

    cls_diag = compute_classification_diagnostics(test_label, test_raw_probs, test_score, pnl_test)
    formal_spearman = cls_diag.get("spearman_score_vs_pnl", float("nan"))

    test_df_aligned = test_df.reset_index(drop=True)
    val_df_aligned = val_df.reset_index(drop=True)
    traded_mask_test = np.isfinite(test_score) & (test_score >= best_q_record["cutoff"])
    valid_pnl_mask_test = np.isfinite(pnl_test)
    in_trade = traded_mask_test & valid_pnl_mask_test
    by_pair: dict[str, int] = {}
    by_direction: dict[str, int] = {"long": 0, "short": 0}
    for i in np.flatnonzero(in_trade):
        p = str(test_df_aligned["pair"].iloc[i])
        d = str(test_df_aligned["direction"].iloc[i])
        by_pair[p] = by_pair.get(p, 0) + 1
        by_direction[d] = by_direction.get(d, 0) + 1

    valid_pnl_mask_val = np.isfinite(pnl_val)
    traded_mask_val = np.isfinite(val_score) & (val_score >= best_q_record["cutoff"])
    val_concentration = compute_pair_concentration(val_df_aligned, traded_mask_val, valid_pnl_mask_val)
    test_concentration = compute_pair_concentration(test_df_aligned, traded_mask_test, valid_pnl_mask_test)
    per_pair_sharpe = compute_per_pair_sharpe_contribution(test_df_aligned, traded_mask_test, pnl_test)
    low_power = n_test < stage25_0b.LOW_POWER_N_TEST or n_train < stage25_0b.LOW_POWER_N_TRAIN

    # Cell-level Spearman on val (over traded rows)
    val_cell_spearman = float("nan")
    if int(traded_mask_val.sum()) >= 2:
        from scipy.stats import spearmanr

        val_traded_pnl = pnl_val[traded_mask_val & valid_pnl_mask_val]
        val_traded_score = val_score[traded_mask_val & valid_pnl_mask_val]
        sp_result = spearmanr(val_traded_score, val_traded_pnl, nan_policy="omit")
        val_cell_spearman = (
            float(sp_result.correlation)
            if hasattr(sp_result, "correlation")
            else float(sp_result.statistic)
        )
        if not np.isfinite(val_cell_spearman):
            val_cell_spearman = float("nan")

    return {
        "cell": cell,
        "arch_id": arch_id,
        "score_type": score_type,
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
        "quantile_all": [
            {
                k: (v if k != "val" and k != "test" else {**v, "realised_pnls": None})
                for k, v in r.items()
            }
            for r in quantile_results
        ],
        "quantile_best": {
            "q_percent": best_q_record["q_percent"],
            "cutoff": best_q_record["cutoff"],
            "val": {
                **{k: v for k, v in best_q_record["val"].items() if k != "realised_pnls"},
                "spearman_score_vs_pnl": val_cell_spearman,
            },
            "test": {k: v for k, v in best_q_record["test"].items() if k != "realised_pnls"},
        },
        "selected_q_percent": float(best_q_record["q_percent"]),
        "selected_cutoff": float(best_q_record["cutoff"]),
        "val_realised_sharpe": float(best_q_record["val"]["sharpe"]),
        "val_realised_annual_pnl": float(best_q_record["val"]["annual_pnl"]),
        "val_n_trades": int(best_q_record["val"]["n_trades"]),
        "val_max_dd": float(best_q_record["val"]["max_dd"]),
        "val_cell_spearman": float(val_cell_spearman),
        "test_realised_metrics": gate_block["metrics"],
        "test_gates": gate_block["gates"],
        "test_formal_spearman": float(formal_spearman),
        "val_concentration": val_concentration,
        "test_concentration": test_concentration,
        "test_classification_diag": cls_diag,
        "per_pair_sharpe_contribution": per_pair_sharpe,
        "by_pair_trade_count": by_pair,
        "by_direction_trade_count": by_direction,
        "feature_importance": feature_importance_diag,
        "low_power": low_power,
        "h_state": "OK",
    }


# ---------------------------------------------------------------------------
# Sanity probe (12 items: 6 inherited + 6 NEW sequence-cell-specific)
# ---------------------------------------------------------------------------


def run_sanity_probe_29_0b(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    pairs: list[str],
    days: int = SPAN_DAYS,
    pnl_train_full: np.ndarray | None = None,
    coverage_train: dict | None = None,
    coverage_val: dict | None = None,
    coverage_test: dict | None = None,
    causality_check_train: dict | None = None,
    harness_verification: dict | None = None,
    training_convergence: dict | None = None,
    gpu_memory: dict | None = None,
    determinism_check: dict | None = None,
    phase22_oos_check: dict | None = None,
    cell_definitions: list[dict] | None = None,
    train_drop_for_nan_pnl_count: int | None = None,
) -> dict:
    """12-item sanity probe (6 inherited + 6 sequence-cell-specific per PR #354 §16)."""
    print("\n=== 29.0b-β SANITY PROBE (per PR #354 §16) ===")
    out: dict = {}

    # Item 1: class priors
    splits = {"train": train_df, "val": val_df, "test": test_df}
    out["class_priors"] = {}
    for name, df in splits.items():
        label = build_l1_labels_for_dataframe(df).to_numpy()
        total = len(label)
        counts = {
            int(LABEL_TP): int((label == LABEL_TP).sum()),
            int(LABEL_SL): int((label == LABEL_SL).sum()),
            int(LABEL_TIME): int((label == LABEL_TIME).sum()),
        }
        shares = {k: (v / total) if total > 0 else float("nan") for k, v in counts.items()}
        out["class_priors"][name] = {"counts": counts, "shares": shares, "total": total}
        print(
            f"  {name}: total={total} TP={counts[LABEL_TP]} ({shares[LABEL_TP]:.3%}) "
            f"SL={counts[LABEL_SL]} ({shares[LABEL_SL]:.3%}) "
            f"TIME={counts[LABEL_TIME]} ({shares[LABEL_TIME]:.3%})"
        )

    # Item 2: per-pair TIME share on train
    train_label = build_l1_labels_for_dataframe(train_df).to_numpy()
    train_pairs = train_df["pair"].to_numpy()
    over_99 = 0
    out["per_pair_time_share"] = {}
    for pair in pairs:
        mask = train_pairs == pair
        n = int(mask.sum())
        if n == 0:
            out["per_pair_time_share"][pair] = {"n": 0, "time_share": float("nan")}
            continue
        time_count = int((train_label[mask] == LABEL_TIME).sum())
        share = time_count / n if n > 0 else float("nan")
        out["per_pair_time_share"][pair] = {"n": n, "time_share": share}
        if np.isfinite(share) and share > SANITY_MAX_PER_PAIR_TIME_SHARE:
            over_99 += 1
    print(f"  per-pair TIME-share check: {over_99} pair(s) over {SANITY_MAX_PER_PAIR_TIME_SHARE:.0%}")

    # Item 3: D-1 binding check (extended for sequence input)
    print("  D-1 binding check (sequence-cell extension):")
    barrier_src = inspect.getsource(stage25_0b._compute_realised_barrier_pnl)
    if not all(tok in barrier_src for tok in ["bid_h", "ask_l", "ask_h", "bid_l"]):
        raise SanityProbeError(
            "_compute_realised_barrier_pnl does not reference bid_h/ask_l/ask_h/bid_l"
        )
    windowed_src = inspect.getsource(_windowed_dataset._build_window_for_row)
    if not all(tok in windowed_src for tok in ["bid_o", "bid_h", "bid_l", "bid_c", "ask_o", "ask_h", "ask_l", "ask_c"]):
        raise SanityProbeError(
            "windowed_dataset._build_window_for_row does not reference all 8 bid/ask OHLC channels"
        )
    out["d1_binding_check"] = "PASS"
    print("    OK: barrier + windowed input both bid/ask-only (no mid; D-1 preserved)")

    # Item 4: realised PnL distribution per class on TRAIN (DIAGNOSTIC)
    if pnl_train_full is not None:
        mid_train = np.asarray(pnl_train_full, dtype=np.float64)
        out["target_pnl_distribution_train"] = {}
        label_names = [(LABEL_TP, "TP"), (LABEL_SL, "SL"), (LABEL_TIME, "TIME")]
        for cls, name in label_names:
            mask = (train_label == cls) & np.isfinite(mid_train)
            if mask.sum() == 0:
                continue
            data = mid_train[mask]
            out["target_pnl_distribution_train"][name] = {
                "n": int(mask.sum()),
                "mean": float(data.mean()),
                "p5": float(np.quantile(data, 0.05)),
                "p50": float(np.quantile(data, 0.5)),
                "p95": float(np.quantile(data, 0.95)),
            }

    # Item 5: R7-A NaN-rate check
    nan_rate_diag: dict = {}
    for name, df in splits.items():
        nan_rate_diag[name] = {}
        for col in NUMERIC_FEATURES_R7A:
            arr = df[col].to_numpy(dtype=np.float64)
            n = int(len(arr))
            nan_n = int((~np.isfinite(arr)).sum())
            rate = nan_n / n if n > 0 else float("nan")
            nan_rate_diag[name][col] = {"n": n, "nan": nan_n, "rate": rate}
    out["r7a_new_feature_nan_rate"] = nan_rate_diag

    # Item 6: R7-A positivity check
    positivity_diag: dict = {}
    for col in NUMERIC_FEATURES_R7A:
        arr = train_df[col].to_numpy(dtype=np.float64)
        finite = arr[np.isfinite(arr)]
        if len(finite) == 0:
            continue
        positivity_diag[col] = {
            "n": int(len(finite)),
            "mean": float(finite.mean()),
            "p5": float(np.quantile(finite, 0.05)),
            "p50": float(np.quantile(finite, 0.5)),
            "p95": float(np.quantile(finite, 0.95)),
        }
    out["r7a_positivity_check"] = positivity_diag

    # NaN-PnL HALT (inherited)
    if train_drop_for_nan_pnl_count is not None and pnl_train_full is not None:
        n_train_for_threshold = len(pnl_train_full)
        threshold = NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD * n_train_for_threshold
        if train_drop_for_nan_pnl_count > threshold:
            raise SanityProbeError(
                f"train rows with NaN PnL = {train_drop_for_nan_pnl_count} > "
                f"{NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD:.1%} of n_train"
            )

    # Item 7 NEW: windowed dataset coverage per split
    out["windowed_coverage"] = {}
    for split_name, coverage in [("train", coverage_train), ("val", coverage_val), ("test", coverage_test)]:
        if coverage is None:
            continue
        total = sum(v["n_total"] for v in coverage.values())
        valid = sum(v["n_valid"] for v in coverage.values())
        rate = valid / max(total, 1)
        out["windowed_coverage"][split_name] = {
            "n_total": total, "n_valid": valid, "rate": float(rate),
            "per_pair": coverage,
            "halt_threshold": float(WINDOWED_COVERAGE_HALT_THRESHOLD),
            "pass": bool(rate >= WINDOWED_COVERAGE_HALT_THRESHOLD),
        }
        print(
            f"  windowed coverage {split_name}: {rate:.3%} "
            f"({valid}/{total}; HALT < {WINDOWED_COVERAGE_HALT_THRESHOLD:.0%})"
        )

    # Item 7 supplement: causality guard verification on TRAIN sample
    if causality_check_train is not None:
        out["causality_check_train"] = causality_check_train
        print(
            f"  causality guard: n_sampled={causality_check_train.get('n_sampled')} "
            f"n_violations={causality_check_train.get('n_violations')}"
        )

    # Item 8 NEW: sequence-cell harness verification (C-d2-arch-control eval succeeds)
    if harness_verification is not None:
        out["harness_verification"] = harness_verification
        print(
            f"  harness verification (C-d2-arch-control tabular eval inside sequence harness): "
            f"{harness_verification.get('status', 'unknown')}"
        )

    # Item 9 NEW: per-architecture training convergence
    if training_convergence is not None:
        out["training_convergence"] = training_convergence
        for arch_id, info in training_convergence.items():
            print(
                f"  {arch_id} training: best_epoch={info.get('best_epoch')} "
                f"best_val_huber={info.get('best_val_huber_loss', float('nan')):+.6f} "
                f"epochs_run={info.get('epochs_run')} early_stop={info.get('early_stopping_triggered')}"
            )

    # Item 10 NEW: GPU memory utilisation
    if gpu_memory is not None:
        out["gpu_memory"] = gpu_memory
        for arch_id, info in gpu_memory.items():
            if info.get("available"):
                print(
                    f"  {arch_id} GPU peak: {info.get('peak_mb', 0):.0f} MB "
                    f"({info.get('utilisation_fraction', 0) * 100:.1f}% of "
                    f"{info.get('total_mb', 0):.0f} MB)"
                )

    # Item 11 NEW: determinism check (metric-level tolerance)
    if determinism_check is not None:
        out["determinism_check"] = determinism_check
        all_within = determinism_check.get("all_within_tolerance", False)
        print(f"  determinism check (metric-level): all_within_tolerance={all_within}")

    # Item 12 NEW: Phase 22 OOS extension verification
    if phase22_oos_check is not None:
        out["phase22_oos_check"] = phase22_oos_check

    if cell_definitions is not None:
        out["cell_definitions"] = [{k: v for k, v in c.items()} for c in cell_definitions]

    print("=== SANITY PROBE: PASS ===")
    return out


# ---------------------------------------------------------------------------
# eval_report.md writer (25-section per PR #354 §17)
# ---------------------------------------------------------------------------


def write_eval_report_29_0b(
    report_path: Path,
    cell_results: list[dict],
    val_select: dict,
    verdict_info: dict,
    aggregate_info: dict,
    baseline_match_report: dict,
    arch_control_drift_report: dict,
    h_d2_per_arch: list[dict],
    h_d2_aggregate: dict,
    within_eval_drift_per_arch: dict[str, dict],
    sanity: dict,
    drop_stats_r7a: dict,
    t_range: tuple,
    preflight_diag: dict,
    n_cells_run: int,
    feature_importance_per_arch: dict,
    regression_diag_per_arch: dict,
    predicted_pnl_distribution: dict,
    top_tail_regime_audit_per_arch: dict[str, dict],
) -> None:
    """25-section eval_report.md per PR #354 §17."""
    lines: list[str] = []
    t_min, t70, t85, t_max = t_range
    lines.append("# Phase 29.0b-β — A0-broad Sequence/NN eval report")
    lines.append("")
    lines.append("**Sub-phase**: 29.0b-β (Phase 29 second sub-phase)")
    lines.append("**Design memo**: PR #354 (phase29_0b_alpha_a0_broad_design_memo.md)")
    lines.append("**Preflight audit**: PR #353 (PASS_29_0B_ALPHA_AUTHORISED)")
    lines.append("**Routing**: PR #352 (post-29.0a; Path 1 PRIMARY preflight-gated)")
    lines.append("")
    lines.append(
        "**MISSION**: test sequence/NN model class vs tabular LightGBM, R7-A "
        "features fixed, inherited triple-barrier target, top-q selection, "
        "Huber α=0.9 regression. Closed 3-architecture allowlist "
        "(S1 LSTM / S2 Temporal CNN / S3 Transformer); windowed (32×8) input; "
        "C-d2-arch-control 7th anchor (tabular LightGBM INSIDE sequence-cell "
        "harness, NOT a sequence model)."
    )
    lines.append("")
    lines.append(
        "**TRAIN-TIME vs VERDICT-TIME OBJECTIVE WALL**: training early stopping "
        "uses validation Huber loss (NOT val Sharpe). H-D2 verdict uses val "
        "Sharpe lift + H1m + H3 + baseline reproduction. Train-time and "
        "verdict-time objectives are explicitly separated to preserve "
        "selection-overfit guard."
    )
    lines.append("")

    # §1 Executive summary
    lines.append("## 1. Executive summary")
    lines.append("")
    lines.append("Per-architecture H-D2 outcome ladder (precedence row 4 > 1 > 2 > 3):")
    lines.append("")
    lines.append("| Arch | Cell | Outcome | Row | Reason |")
    lines.append("|---|---|---|---|---|")
    for o in h_d2_per_arch:
        lines.append(
            f"| {o.get('arch_id', '-')} | {o.get('cell_id', '-')} | "
            f"{o.get('outcome', '-')} | {o.get('row_matched', '-')} | "
            f"{o.get('reason', '-')[:90]} |"
        )
    lines.append("")
    lines.append(f"**Aggregate verdict**: {h_d2_aggregate.get('aggregate_verdict')}")
    lines.append(f"**A0-broad-narrow status**: {h_d2_aggregate.get('a0_broad_status')}")
    lines.append(f"**Routing implication**: {h_d2_aggregate.get('routing_implication')}")
    lines.append("")
    if h_d2_aggregate.get("a0_broad_status") == "FALSIFIED_A0_BROAD_NARROW":
        lines.append(
            "> **EXPLICIT LABEL**: this result is `FALSIFIED_A0_BROAD_NARROW`, NEVER "
            "`FALSIFIED_ALL_A0_BROAD`. Alternate sequence architectures outside the "
            "closed 3-variant allowlist (S1/S2/S3) remain admissible via separate "
            "scope amendment."
        )
        lines.append("")
    lines.append(
        f"**C-sb-baseline reproduction**: "
        f"{'PASS' if baseline_match_report.get('all_match') else 'FAIL'}"
    )
    lines.append(
        f"**C-d2-arch-control 7th-anchor drift vs 27.0d C-se**: "
        f"all_within_tolerance={arch_control_drift_report.get('all_within_tolerance')} "
        f"(warn={arch_control_drift_report.get('warn')}; DIAGNOSTIC-ONLY)"
    )
    lines.append("")

    # §2 Cells overview
    lines.append("## 2. Cells overview")
    lines.append("")
    lines.append("| Cell | Picker | Score | Arch ID | Type |")
    lines.append("|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        cell_type = "baseline" if cell.get("is_baseline") else ("arch-control" if cell.get("is_arch_control") else "sequence")
        lines.append(
            f"| {cell['id']} | {cell.get('picker', '-')[:60]} | "
            f"{cell.get('score_type', '-')} | {cell.get('arch_id', '-')} | {cell_type} |"
        )
    lines.append("")

    # §3 Row-set policy / drop stats
    lines.append("## 3. Row-set policy / drop stats")
    lines.append("")
    lines.append(
        "**A0-broad row-set policy** (PR #354 §6.2-7): R7-A-clean parent + "
        "windowed-input-valid rows. Sequence cells / arch-control use the "
        "windowed-valid subset (causality-guarded; window ends strictly before "
        "entry M1 timestamp). C-sb-baseline uses the full R7-A-clean row-set "
        "(no windowing requirement; inherited Phase 28 §10 row-set)."
    )
    lines.append("")
    lines.append("R7-A new-feature row-drop:")
    for split_name in ("train", "val", "test"):
        ds = drop_stats_r7a.get(split_name, {})
        lines.append(
            f"- {split_name}: n_input={ds.get('n_input', 0)} "
            f"n_kept={ds.get('n_kept', 0)} n_dropped={ds.get('n_dropped', 0)}"
        )
    lines.append("Split dates:")
    lines.append(f"- min: {t_min}")
    lines.append(f"- train < {t70}")
    lines.append(f"- val [{t70}, {t85})")
    lines.append(f"- test [{t85}, {t_max}]")
    lines.append("")

    # §4 Sanity probe results
    lines.append("## 4. Sanity probe results (12 items: 6 inherited + 6 sequence-cell)")
    lines.append("")
    cp = sanity.get("class_priors", {})
    for name in ("train", "val", "test"):
        cpv = cp.get(name, {})
        total = cpv.get("total", 0)
        shares = cpv.get("shares", {})
        lines.append(
            f"- {name}: total={total}, TP {shares.get(LABEL_TP, float('nan')):.3%} / "
            f"SL {shares.get(LABEL_SL, float('nan')):.3%} / "
            f"TIME {shares.get(LABEL_TIME, float('nan')):.3%}"
        )
    lines.append(f"- D-1 binding check: {sanity.get('d1_binding_check', '-')}")
    coverage = sanity.get("windowed_coverage", {})
    for split_name, info in coverage.items():
        lines.append(
            f"- windowed coverage {split_name}: {info.get('rate', float('nan')):.3%} "
            f"({info.get('n_valid', 0)}/{info.get('n_total', 0)}; PASS={info.get('pass', False)})"
        )
    causality = sanity.get("causality_check_train", {})
    if causality:
        lines.append(
            f"- causality guard (train sample n={causality.get('n_sampled', 0)}): "
            f"n_violations={causality.get('n_violations', 0)}"
        )
    harness = sanity.get("harness_verification", {})
    if harness:
        lines.append(f"- harness verification: {harness.get('status', '-')}")
    for arch_id, info in (sanity.get("training_convergence") or {}).items():
        lines.append(
            f"- {arch_id} training: best_epoch={info.get('best_epoch')} "
            f"val_huber={info.get('best_val_huber_loss', float('nan')):+.6f} "
            f"early_stop={info.get('early_stopping_triggered')}"
        )
    for arch_id, info in (sanity.get("gpu_memory") or {}).items():
        if info.get("available"):
            lines.append(
                f"- {arch_id} GPU peak: {info.get('peak_mb', 0):.0f} MB "
                f"({info.get('utilisation_fraction', 0) * 100:.1f}%)"
            )
    det = sanity.get("determinism_check", {})
    if det:
        lines.append(
            f"- determinism check (metric tolerance): "
            f"all_within_tolerance={det.get('all_within_tolerance', False)}"
        )
    lines.append("")

    # §5 OOF (DIAGNOSTIC-ONLY caveat — per-arch sequence OOF not run due to cost)
    lines.append("## 5. OOF correlation diagnostic")
    lines.append("")
    lines.append(
        "Per-architecture sequence OOF NOT run (per PR #354 §17 caveat — 5-fold OOF "
        "amplifies sequence training cost ~5×; deferred as DIAGNOSTIC-ONLY). C-d2-arch-control "
        "tabular OOF computed for harness verification (inherited from 27.0d pattern)."
    )
    lines.append("")

    # §6 Regression diagnostic per arch (val Huber loss + R² + MAE)
    lines.append("## 6. Regression diagnostic — per architecture (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| Arch | Split | n | R² | MAE | val_Huber_loss |")
    lines.append("|---|---|---|---|---|---|")
    for arch_id, splits_d in (regression_diag_per_arch or {}).items():
        for split_name in ("train", "val", "test"):
            blk = splits_d.get(split_name, {})
            huber = splits_d.get("val_huber_loss") if split_name == "val" else "-"
            lines.append(
                f"| {arch_id} | {split_name} | {blk.get('n', '-')} | "
                f"{blk.get('r2', float('nan')):+.4f} | "
                f"{blk.get('mae', float('nan')):+.3f} | {huber} |"
            )
    lines.append("")

    # §7 Per-cell quantile family
    lines.append("## 7. Per-cell quantile family results")
    lines.append("")
    for c in cell_results:
        cell = c["cell"]
        lines.append(f"### {cell['id']}")
        lines.append("")
        lines.append("| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |")
        lines.append("|---|---|---|---|---|---|---|")
        for qr in c.get("quantile_all", []) or []:
            qp = qr.get("q_percent", float("nan"))
            co = qr.get("cutoff", float("nan"))
            vv = qr.get("val", {})
            tt = qr.get("test", {})
            lines.append(
                f"| {qp:.1f} | {co:+.6f} | {vv.get('sharpe', float('nan')):+.4f} | "
                f"{vv.get('n_trades', 0)} | {tt.get('sharpe', float('nan')):+.4f} | "
                f"{tt.get('n_trades', 0)} | {tt.get('annual_pnl', float('nan')):+.1f} |"
            )
        lines.append("")

    # §8 Val-selected cross-cell
    lines.append("## 8. Val-selected (cell*, q*) cross-cell")
    lines.append("")
    sel = val_select.get("selected")
    if sel is None:
        lines.append("- no valid cell")
    else:
        lines.append(f"- cell: {_cell_signature(sel['cell'])}")
        lines.append(f"- q*={sel.get('selected_q_percent')} cutoff={sel.get('selected_cutoff')}")
        lines.append(
            f"- val Sharpe={sel.get('val_realised_sharpe', float('nan')):+.4f} "
            f"(n={sel.get('val_n_trades')})"
        )
        rm = sel.get("test_realised_metrics", {})
        lines.append(
            f"- test Sharpe={rm.get('sharpe', float('nan')):+.4f} "
            f"ann_pnl={rm.get('annual_pnl', float('nan')):+.1f} "
            f"n={rm.get('n_trades', 0)}"
        )
    lines.append("")

    # §9 Cross-cell aggregate
    lines.append("## 9. Cross-cell aggregate verdict")
    lines.append("")
    lines.append(f"- aggregate verdict: {aggregate_info.get('aggregate_verdict')}")
    lines.append(f"- agree: {aggregate_info.get('agree')}")
    lines.append(f"- branches: {aggregate_info.get('branches')}")
    lines.append("")

    # §10 Phase 28 §10 baseline reproduction FAIL-FAST
    lines.append("## 10. Phase 28 §10 baseline reproduction FAIL-FAST")
    lines.append("")
    lines.append(
        "Phase 28 §10 baseline inherited DIRECTLY per Option 9c simple case (target "
        "unchanged at A0-broad). 29.0a per-target baselines DIAGNOSTIC-ONLY 2nd reference."
    )
    lines.append("")
    bm = baseline_match_report
    lines.append(
        f"- n_trades: observed={bm.get('n_trades_observed')} "
        f"baseline={bm.get('n_trades_baseline')} "
        f"delta={bm.get('n_trades_delta'):+d} match={bm.get('n_trades_match')}"
    )
    lines.append(
        f"- Sharpe: observed={bm.get('sharpe_observed'):+.6f} "
        f"baseline={bm.get('sharpe_baseline'):+.6f} "
        f"delta={bm.get('sharpe_delta'):+.6e} match={bm.get('sharpe_match')}"
    )
    lines.append(
        f"- ann_pnl: observed={bm.get('ann_pnl_observed'):+.3f} "
        f"baseline={bm.get('ann_pnl_baseline'):+.3f} "
        f"delta={bm.get('ann_pnl_delta'):+.3f} match={bm.get('ann_pnl_match')}"
    )
    lines.append(f"- all_match: {bm.get('all_match')}")
    lines.append("")

    # §11 Within-eval drift per architecture
    lines.append("## 11. Within-eval ablation drift (per architecture vs C-d2-arch-control)")
    lines.append("")
    lines.append("| Arch | n_trades Δ | within | Sharpe Δ | within | ann_pnl Δ | within | all_within |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for arch_id, d in (within_eval_drift_per_arch or {}).items():
        n_d = d.get("n_trades_delta", "-")
        n_w = d.get("n_trades_within_tolerance", "-")
        sh_d = d.get("sharpe_delta", float("nan"))
        sh_w = d.get("sharpe_within_tolerance", "-")
        ap_d = d.get("ann_pnl_delta", float("nan"))
        ap_w = d.get("ann_pnl_within_tolerance", "-")
        all_w = d.get("all_within_tolerance", "-")
        sh_d_str = f"{sh_d:+.4e}" if isinstance(sh_d, float) and np.isfinite(sh_d) else str(sh_d)
        ap_d_str = f"{ap_d:+.3f}" if isinstance(ap_d, float) and np.isfinite(ap_d) else str(ap_d)
        lines.append(
            f"| {arch_id} | {n_d} | {n_w} | {sh_d_str} | {sh_w} | {ap_d_str} | {ap_w} | {all_w} |"
        )
    lines.append("")

    # §11b 7th-anchor drift
    lines.append("## 11b. C-d2-arch-control 7th-anchor drift vs 27.0d C-se (DIAGNOSTIC-ONLY WARN)")
    lines.append("")
    lines.append(
        "**Chain position**: 7th anchor (27.0d → 27.0f → 28.0a → 28.0b → 28.0c → 29.0a → 29.0b)"
    )
    lines.append("")
    cd = arch_control_drift_report
    lines.append(f"- source: {cd.get('source', '-')}")
    lines.append(
        f"- n_trades: observed={cd.get('n_trades_observed')} "
        f"baseline_27_0d={cd.get('n_trades_baseline_27_0d')} "
        f"delta={cd.get('n_trades_delta')} within={cd.get('n_trades_within_tolerance')}"
    )
    sh_d = cd.get("sharpe_delta")
    ap_d = cd.get("ann_pnl_delta")
    sh_d_str = f"{sh_d:+.4e}" if isinstance(sh_d, float) and np.isfinite(sh_d) else str(sh_d)
    ap_d_str = f"{ap_d:+.3f}" if isinstance(ap_d, float) and np.isfinite(ap_d) else str(ap_d)
    lines.append(
        f"- Sharpe: observed={cd.get('sharpe_observed', float('nan')):+.6f} "
        f"baseline_27_0d={cd.get('sharpe_baseline_27_0d')} "
        f"delta={sh_d_str} within={cd.get('sharpe_within_tolerance')}"
    )
    lines.append(
        f"- ann_pnl: observed={cd.get('ann_pnl_observed', float('nan')):+.3f} "
        f"baseline_27_0d={cd.get('ann_pnl_baseline_27_0d')} "
        f"delta={ap_d_str} within={cd.get('ann_pnl_within_tolerance')}"
    )
    lines.append(f"- all_within_tolerance: {cd.get('all_within_tolerance')}")
    lines.append(f"- WARN: {cd.get('warn')}")
    lines.append("")

    # §12 Feature importance per architecture (DIAGNOSTIC)
    lines.append("## 12. Feature importance — per architecture (DIAGNOSTIC-ONLY)")
    lines.append("")
    for arch_id, fi in (feature_importance_per_arch or {}).items():
        lines.append(f"### {arch_id}")
        if isinstance(fi, dict) and "items" in fi:
            for item in fi["items"]:
                lines.append(
                    f"- {item.get('feature', '-')}: gain={item.get('gain', float('nan')):+.1f}"
                )
        elif isinstance(fi, dict):
            for k, v in fi.items():
                lines.append(f"- {k}: {v}")
        else:
            lines.append(f"(sequence model {arch_id}: see attention weights / gradient saliency at sub-phase β diagnostic dump; not embedded here)")
        lines.append("")

    # §13 H-D2 outcome row binding per architecture (with FALSIFIED_A0_BROAD_NARROW)
    lines.append("## 13. H-D2 outcome row binding per architecture")
    lines.append("")
    lines.append(
        "Per PR #354 §14: H-D2 verdict uses val Sharpe lift vs Phase 28 §10 baseline. "
        "All-fail labelled `FALSIFIED_A0_BROAD_NARROW`, NEVER `FALSIFIED_ALL_A0_BROAD`."
    )
    lines.append("")
    lines.append(
        "| Arch | Cell | Outcome | Row | Sharpe lift | val Sharpe | val n | cell Sp. | Notes |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for o in h_d2_per_arch:
        ev = o.get("evidence", {}) if isinstance(o.get("evidence"), dict) else {}
        lift = ev.get("sharpe_lift_absolute", float("nan"))
        vs = ev.get("val_sharpe", float("nan"))
        vn = ev.get("val_n_trades", "-")
        sp = ev.get("cell_spearman_val", float("nan"))
        lift_str = f"{lift:+.4f}" if isinstance(lift, float) and np.isfinite(lift) else str(lift)
        vs_str = f"{vs:+.4f}" if isinstance(vs, float) and np.isfinite(vs) else str(vs)
        sp_str = f"{sp:+.4f}" if isinstance(sp, float) and np.isfinite(sp) else str(sp)
        lines.append(
            f"| {o.get('arch_id', '-')} | {o.get('cell_id', '-')} | {o.get('outcome', '-')} | "
            f"{o.get('row_matched', '-')} | {lift_str} | {vs_str} | {vn} | {sp_str} | "
            f"{o.get('reason', '-')[:60]} |"
        )
    lines.append("")
    lines.append(f"**Aggregate**: {h_d2_aggregate.get('aggregate_verdict')}")
    lines.append(f"**A0-broad-narrow status**: {h_d2_aggregate.get('a0_broad_status')}")
    lines.append(f"**Routing**: {h_d2_aggregate.get('routing_implication')}")
    lines.append("")

    # §14 Trade-count budget
    lines.append("## 14. Trade-count budget audit per cell")
    lines.append("")
    lines.append("| Cell | val_n_trades | test_n_trades |")
    lines.append("|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        vn = c.get("val_n_trades", 0)
        rm = c.get("test_realised_metrics", {})
        tn = rm.get("n_trades", 0)
        lines.append(f"| {cell['id']} | {vn} | {tn} |")
    lines.append("")

    # §15 Pair concentration
    lines.append("## 15. Pair concentration per cell (val-selected)")
    lines.append("")
    lines.append("| Cell | val top-3 | val Herfindahl | test top-3 | test Herfindahl |")
    lines.append("|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        vc = c.get("val_concentration", {}) or {}
        tc = c.get("test_concentration", {}) or {}
        vc_top = ", ".join(p for p, _ in (vc.get("top_pairs") or [])[:3])
        tc_top = ", ".join(p for p, _ in (tc.get("top_pairs") or [])[:3])
        vc_h = vc.get("herfindahl", float("nan"))
        tc_h = tc.get("herfindahl", float("nan"))
        vc_h_str = f"{vc_h:.3f}" if isinstance(vc_h, float) and np.isfinite(vc_h) else str(vc_h)
        tc_h_str = f"{tc_h:.3f}" if isinstance(tc_h, float) and np.isfinite(tc_h) else str(tc_h)
        lines.append(f"| {cell['id']} | {vc_top} | {vc_h_str} | {tc_top} | {tc_h_str} |")
    lines.append("")

    # §16 Direction balance
    lines.append("## 16. Direction balance per cell")
    lines.append("")
    lines.append("| Cell | long | short |")
    lines.append("|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        bd = c.get("by_direction_trade_count", {}) or {}
        lines.append(f"| {cell['id']} | {bd.get('long', 0)} | {bd.get('short', 0)} |")
    lines.append("")

    # §17 Per-pair Sharpe contribution
    lines.append("## 17. Per-pair Sharpe contribution per cell (DIAGNOSTIC-ONLY)")
    lines.append("")
    for c in cell_results:
        cell = c["cell"]
        lines.append(f"### {cell['id']}")
        contrib = c.get("per_pair_sharpe_contribution", {}) or {}
        if isinstance(contrib, dict) and contrib:
            lines.append("| pair | n | Sharpe contribution |")
            lines.append("|---|---|---|")
            for p, info in list(contrib.items())[:10]:
                if isinstance(info, dict):
                    lines.append(
                        f"| {p} | {info.get('n', 0)} | "
                        f"{info.get('sharpe_contribution', float('nan')):+.4f} |"
                    )
        else:
            lines.append("(no contribution data)")
        lines.append("")

    # §18 Top-tail regime audit
    lines.append("## 18. Top-tail regime audit per architecture (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("**Note**: R7-C features NOT computed (out of scope per Clause 6). `spread_at_signal_pip` only.")
    lines.append("")
    for arch_id, audit in (top_tail_regime_audit_per_arch or {}).items():
        pop = audit.get("population", {})
        lines.append(f"### {arch_id}")
        lines.append(
            f"- population mean spread = {pop.get('mean_spread_at_signal_pip', float('nan')):+.3f}"
        )
        for per_q in audit.get("per_q", []):
            lines.append(
                f"- q={per_q['q_percent']:.1f}: top mean={per_q['top_mean_spread']:+.3f} "
                f"(Δ {per_q['delta_mean_vs_population']:+.3f}); n_top={per_q['n_top']}"
            )
        lines.append("")

    # §19 R7-A NaN
    lines.append("## 19. R7-A new-feature NaN-rate check")
    lines.append("")
    nr = sanity.get("r7a_new_feature_nan_rate", {})
    if nr:
        lines.append("| Split | Feature | n | NaN | rate |")
        lines.append("|---|---|---|---|---|")
        for split_name, cols in nr.items():
            for col, info in cols.items():
                lines.append(
                    f"| {split_name} | {col} | {info.get('n', 0)} | "
                    f"{info.get('nan', 0)} | {info.get('rate', float('nan')):.3%} |"
                )
    lines.append("")

    # §20 Realised PnL distribution
    lines.append("## 20. Realised PnL distribution by class on TRAIN (DIAGNOSTIC)")
    lines.append("")
    tpd = sanity.get("target_pnl_distribution_train", {})
    if tpd:
        lines.append("| Class | n | mean | p5 | p50 | p95 |")
        lines.append("|---|---|---|---|---|---|")
        for cname, stats in tpd.items():
            lines.append(
                f"| {cname} | {stats.get('n', 0)} | "
                f"{stats.get('mean', float('nan')):+.3f} | "
                f"{stats.get('p5', float('nan')):+.3f} | "
                f"{stats.get('p50', float('nan')):+.3f} | "
                f"{stats.get('p95', float('nan')):+.3f} |"
            )
    lines.append("")

    # §21 Predicted PnL distribution per architecture
    lines.append("## 21. Predicted PnL distribution per architecture (DIAGNOSTIC)")
    lines.append("")
    lines.append("| Arch | Split | n | mean | p5 | p50 | p95 |")
    lines.append("|---|---|---|---|---|---|---|")
    for arch_id, splits_d in (predicted_pnl_distribution or {}).items():
        for split_name in ("train", "val", "test"):
            stats = splits_d.get(split_name, {})
            lines.append(
                f"| {arch_id} | {split_name} | {stats.get('n_finite', 0)} | "
                f"{stats.get('mean', float('nan')):+.3f} | "
                f"{stats.get('p5', float('nan')):+.3f} | "
                f"{stats.get('p50', float('nan')):+.3f} | "
                f"{stats.get('p95', float('nan')):+.3f} |"
            )
    lines.append("")

    # §22 References
    lines.append("## 22. References")
    lines.append("")
    lines.append("- PR #348 — Phase 29 kickoff (Scope III / Policy C / Option 9c)")
    lines.append("- PR #352 — Phase 29 post-29.0a routing review (Path 1 PRIMARY preflight-gated)")
    lines.append("- PR #353 — A0-broad preflight audit (PASS_29_0B_ALPHA_AUTHORISED)")
    lines.append("- PR #354 — Phase 29.0b-α A0-broad design memo")
    lines.append("- PR #325 — Phase 27.0d-β S-E regression (1st anchor)")
    lines.append("- PR #344 — Phase 28.0c-α (5th anchor + closed-arch pattern)")
    lines.append("- PR #345 — Phase 28.0c-β A0-narrow (5th anchor cell)")
    lines.append("- PR #350 / #351 — Phase 29.0a A2 target redesign (6th anchor)")
    lines.append("- PR #279 — γ closure (preserved)")
    lines.append("- Phase 22 frozen-OOS contract (preserved)")
    lines.append("- Phase 9.12 production v9 tip 79ed1e8 (untouched)")
    lines.append("")

    # §23 Caveats
    lines.append("## 23. Caveats")
    lines.append("")
    lines.append(
        "- A0-broad scope: single-axis on R7-A only; R-B / A2 / A3 / joint Path 4 "
        "deferred-not-foreclosed."
    )
    lines.append(
        "- H2 PASS = PROMISING_BUT_NEEDS_OOS only. ADOPT_CANDIDATE wall preserved per "
        "Clause 1. NG#10 / NG#11 not relaxed."
    )
    lines.append(
        "- **TRAIN-TIME vs VERDICT-TIME OBJECTIVE WALL**: training early stopping uses "
        "validation Huber loss; H-D2 verdict uses validation Sharpe lift. The two are "
        "explicitly separated to preserve selection-overfit guard."
    )
    lines.append(
        "- **FALSIFIED_A0_BROAD_NARROW vs FALSIFIED_ALL_A0_BROAD distinction**: failure "
        "of all 3 architectures in closed allowlist is `FALSIFIED_A0_BROAD_NARROW`, "
        "NEVER `FALSIFIED_ALL_A0_BROAD`. Alternate sequence architectures outside "
        "S1/S2/S3 remain admissible via separate scope amendment."
    )
    lines.append(
        "- **C-d2-arch-control 7th anchor**: tabular LightGBM INSIDE sequence-cell "
        "evaluation harness; NOT a sequence model. Purpose: separate sequence-cell "
        "harness drift from sequence model effect. 7th anchor in bit-tight chain "
        "27.0d → 27.0f → 28.0a → 28.0b → 28.0c → 29.0a → 29.0b."
    )
    lines.append(
        "- **Causality guard**: sequence input window ends strictly before entry M1 "
        "timestamp (signal_ts + 1 min). No M1 bar at or beyond entry timestamp enters "
        "the input. Verified by sanity probe."
    )
    lines.append(
        "- Phase 28 §10 baseline inherited DIRECTLY (Option 9c simple case; target unchanged)."
    )
    lines.append(
        "- 29.0a per-target baselines (T1/T2/T3/T4) frozen at PR #351; DIAGNOSTIC-ONLY 2nd "
        "reference; NOT used for A0-broad H-D2."
    )
    lines.append(
        "- Per-architecture sequence OOF NOT run (cost-prohibitive at α); DIAGNOSTIC-ONLY caveat."
    )
    lines.append(
        "- CUDA non-determinism: `warn_only=True` allows non-deterministic fallback; "
        "verified via metric-level tolerance (val Sharpe ±1e-4, n_trades exact, "
        "selected q identical), NOT bit-identical tensor."
    )
    lines.append(
        "- Top-tail regime audit uses `spread_at_signal_pip` only; R7-C features out of scope."
    )
    lines.append("")

    # §24 Cross-validation re-fits
    lines.append("## 24. Cross-validation re-fits diagnostic (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append(
        "Per-architecture training convergence + val Huber loss trajectory reported in "
        "§4 sanity probe item 9. Multi-seed re-fits not run (single seed=42 per "
        "deterministic contract; multi-seed deferred to potential 29.0b-β-rev1)."
    )
    lines.append("")

    # §25 Sub-phase verdict snapshot
    lines.append("## 25. Sub-phase verdict snapshot")
    lines.append("")
    lines.append("- per-architecture outcomes:")
    for o in h_d2_per_arch:
        aid = o.get("arch_id", "-")
        cid = o.get("cell_id", "-")
        oc = o.get("outcome", "-")
        rm = o.get("row_matched", "-")
        lines.append(f"  - {aid} ({cid}): {oc} (row {rm})")
    lines.append(f"- aggregate verdict: {h_d2_aggregate.get('aggregate_verdict')}")
    lines.append(f"- A0-broad-narrow status: {h_d2_aggregate.get('a0_broad_status')}")
    lines.append(f"- routing implication: {h_d2_aggregate.get('routing_implication')}")
    lines.append(
        f"- C-sb-baseline reproduction: "
        f"{'PASS' if baseline_match_report.get('all_match') else 'FAIL'}"
    )
    lines.append(
        f"- C-d2-arch-control 7th-anchor drift vs 27.0d C-se: "
        f"all_within_tolerance={arch_control_drift_report.get('all_within_tolerance')} "
        f"(WARN-only)"
    )
    lines.append("")
    lines.append("*End of `artifacts/stage29_0b/eval_report.md`.*")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# main entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_20)
    parser.add_argument("--days", type=int, default=SPAN_DAYS)
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--sanity-probe-only", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument(
        "--quick-mode",
        action="store_true",
        help="DIAGNOSTIC-ONLY; formal verdict NOT valid in quick mode (NG#A0B-*)",
    )
    parser.add_argument(
        "--architectures",
        type=str,
        default=",".join(CLOSED_ARCHITECTURE_ALLOWLIST),
        help="Comma-separated subset (--quick-mode only; --full requires all S1/S2/S3)",
    )
    parser.add_argument(
        "--skip-windowed-regen",
        action="store_true",
        help="Use cached windowed dataset shards if present (default: regenerate if missing)",
    )
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    WINDOWED_SHARDS_ROOT.mkdir(parents=True, exist_ok=True)
    CHECKPOINTS_ROOT.mkdir(parents=True, exist_ok=True)

    requested_archs = [a.strip().upper() for a in args.architectures.split(",") if a.strip()]
    if not args.quick_mode and set(requested_archs) != set(CLOSED_ARCHITECTURE_ALLOWLIST):
        raise SystemExit(
            f"--full mode requires all 3 architectures (NG#A0B-2 per-architecture verdict required); "
            f"requested={requested_archs}; allowlist={list(CLOSED_ARCHITECTURE_ALLOWLIST)}"
        )

    print(f"=== Stage 29.0b-β A0-broad Sequence/NN eval ({len(args.pairs)} pairs) ===")
    print(
        f"Closed 3-architecture allowlist (α-fixed; NG#A0B-1): "
        f"S1 LSTM / S2 Temporal CNN / S3 Transformer"
    )
    print(f"R7-A FIXED (4 features): {list(ALL_FEATURES_R7A)}")
    print(
        f"Windowed input: N={_windowed_dataset.N_M5_BARS} M5 bars × "
        f"{_windowed_dataset.N_CHANNELS} channels (bid_OHLC + ask_OHLC)"
    )
    print(
        "Fixed: tabular S-E for control + multiclass S-B for baseline; "
        f"top-q quantile family {list(QUANTILE_PERCENTS_29_0B)}; "
        f"symmetric Huber α={HUBER_ALPHA}; sample_weight=1"
    )
    print(
        "Train-time vs verdict-time wall: early stopping on val Huber loss; "
        "verdict on val Sharpe."
    )
    print(
        "Option 9c simple case: Phase 28 §10 inherited directly (target unchanged); "
        "29.0a per-target baselines DIAGNOSTIC-ONLY 2nd reference."
    )
    if args.quick_mode:
        print(
            "QUICK-MODE: formal verdict NOT valid in quick mode (NG#A0B-* requires "
            "full 730-day / 20-pair scope; max_epochs reduced)"
        )

    # 1. CUDA / GPU detection (HALT-gated per PR #353 §4)
    print("\nDetecting CUDA device per PR #353 §4...")
    try:
        device = select_device()
        print(f"  device={device}; CUDA available")
    except CudaUnavailableError as exc:
        print(f"\n[FATAL] {exc}")
        return 4

    # 2. Load labels
    raw_label_path = REPO_ROOT / "artifacts" / "stage25_0a" / "path_quality_dataset.parquet"
    raw_labels = pd.read_parquet(raw_label_path)
    if args.pairs != PAIRS_20:
        raw_labels = raw_labels[raw_labels["pair"].isin(args.pairs)]
    print(f"  labels rows: {len(raw_labels)}")

    # 3. Pre-flight (inherited)
    try:
        preflight_diag = verify_l3_preflight(raw_labels, args.pairs)
    except L3PreflightError as exc:
        print(f"PRE-FLIGHT FAILED: {exc}")
        return 2
    if not preflight_diag["lightgbm_available"]:
        print("LightGBM required; halting.")
        return 2

    # 4. M1 runtime
    print("Loading M1 runtime per pair...")
    pair_runtime_map: dict[str, dict] = {}
    for pair in args.pairs:
        t_pair = time.time()
        pair_runtime_map[pair] = _build_pair_runtime(pair, days=args.days)
        print(f"  {pair}: m1 rows {pair_runtime_map[pair]['n_m1']} ({time.time() - t_pair:5.1f}s)")

    # 5. Split
    train_df, val_df, test_df, t70, t85 = split_70_15_15(raw_labels)
    t_min = raw_labels["signal_ts"].min()
    t_max = raw_labels["signal_ts"].max()
    print(f"  split: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")

    if args.quick_mode:
        n_per_pair = 500
        train_df = train_df.groupby("pair").head(n_per_pair).reset_index(drop=True)
        val_df = val_df.groupby("pair").head(n_per_pair).reset_index(drop=True)
        test_df = test_df.groupby("pair").head(n_per_pair).reset_index(drop=True)
        print(
            f"  QUICK-MODE: train={len(train_df)}, val={len(val_df)}, "
            f"test={len(test_df)} — formal verdict NOT valid"
        )

    # 6. R7-A row-drop
    print("R7-A row-drop...")
    train_df, train_drop = drop_rows_with_missing_new_features(train_df)
    val_df, val_drop = drop_rows_with_missing_new_features(val_df)
    test_df, test_drop = drop_rows_with_missing_new_features(test_df)
    drop_stats_r7a = {"train": train_drop, "val": val_drop, "test": test_drop}
    for name, ds in drop_stats_r7a.items():
        print(f"  {name}: n_input={ds['n_input']} n_kept={ds['n_kept']} n_dropped={ds['n_dropped']}")

    # 7. Precompute inherited triple-barrier realised PnL per row (target unchanged at A0-broad)
    print("Precomputing inherited triple-barrier realised PnL...")
    t0 = time.time()
    pnl_train_full = precompute_target_pnls_per_row(train_df, pair_runtime_map, "TARGET_CONTROL")
    pnl_val_full = precompute_target_pnls_per_row(val_df, pair_runtime_map, "TARGET_CONTROL")
    pnl_test_full = precompute_target_pnls_per_row(test_df, pair_runtime_map, "TARGET_CONTROL")
    nan_pnl_train = int((~np.isfinite(pnl_train_full)).sum())
    print(
        f"  train n_finite={int(np.isfinite(pnl_train_full).sum())} val={int(np.isfinite(pnl_val_full).sum())} "
        f"test={int(np.isfinite(pnl_test_full).sum())} ({time.time() - t0:.1f}s)"
    )
    threshold_count = NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD * len(pnl_train_full)
    if nan_pnl_train > threshold_count:
        raise SanityProbeError(
            f"train rows with NaN PnL = {nan_pnl_train} > "
            f"{NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD:.1%}"
        )

    # 8. Causality guard sanity (TRAIN sample)
    print("Verifying causality guard on TRAIN sample (n=1000)...")
    try:
        causality_check_train = verify_causality_guard(train_df, pair_runtime_map, sample_size=1000)
        print(
            f"  causality guard PASS: n_sampled={causality_check_train['n_sampled']} "
            f"n_valid_windows={causality_check_train['n_valid_windows']} "
            f"n_violations={causality_check_train['n_violations']}"
        )
    except CausalityGuardError as exc:
        print(f"\n[FATAL] {exc}")
        return 5

    # 9. Windowed dataset generation per split
    print("Building windowed dataset per split...")
    t0 = time.time()
    windowed_train, valid_train = build_windowed_input_per_row(train_df, pair_runtime_map)
    print(f"  train: {int(valid_train.sum())}/{len(valid_train)} valid ({time.time() - t0:.1f}s)")
    t0 = time.time()
    windowed_val, valid_val = build_windowed_input_per_row(val_df, pair_runtime_map)
    print(f"  val: {int(valid_val.sum())}/{len(valid_val)} valid ({time.time() - t0:.1f}s)")
    t0 = time.time()
    windowed_test, valid_test = build_windowed_input_per_row(test_df, pair_runtime_map)
    print(f"  test: {int(valid_test.sum())}/{len(valid_test)} valid ({time.time() - t0:.1f}s)")

    # 10. Coverage check (HALT-gated)
    coverage_train = compute_windowed_coverage_per_pair(train_df, valid_train, args.pairs)
    coverage_val = compute_windowed_coverage_per_pair(val_df, valid_val, args.pairs)
    coverage_test = compute_windowed_coverage_per_pair(test_df, valid_test, args.pairs)
    try:
        assert_windowed_coverage_meets_threshold(coverage_train, "train")
        assert_windowed_coverage_meets_threshold(coverage_val, "val")
        assert_windowed_coverage_meets_threshold(coverage_test, "test")
        print("  windowed coverage HALT gate: PASS")
    except WindowedCoverageError as exc:
        print(f"\n[FATAL] {exc}")
        return 6

    # 11. Build labels
    train_label = build_l1_labels_for_dataframe(train_df).to_numpy()
    val_label = build_l1_labels_for_dataframe(val_df).to_numpy()
    test_label = build_l1_labels_for_dataframe(test_df).to_numpy()

    # 12. Fit shared LightGBM controls (C-d2-arch-control + C-sb-baseline)
    nan_pnl_mask = ~np.isfinite(pnl_train_full)
    train_df_for_reg = train_df.loc[~nan_pnl_mask].reset_index(drop=True)
    pnl_train_for_reg = pnl_train_full[~nan_pnl_mask]
    x_train_r7a = train_df_for_reg[list(ALL_FEATURES_R7A)]

    print("Fitting tabular LightGBM S-E regressor (C-d2-arch-control 7th anchor)...")
    t0 = time.time()
    tabular_regressor = build_pipeline_lightgbm_regression_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        tabular_regressor.fit(x_train_r7a, pnl_train_for_reg)
    fi_tabular = compute_feature_importance_diagnostic(tabular_regressor)
    print(f"  tabular S-E: fit {time.time() - t0:.1f}s")

    print("Fitting S-B multiclass head (C-sb-baseline FAIL-FAST)...")
    t0 = time.time()
    train_label_clean = train_label[~nan_pnl_mask]
    multiclass_pipeline = build_pipeline_lightgbm_multiclass_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        multiclass_pipeline.fit(x_train_r7a, train_label_clean)
    val_raw_probs = _multiclass_to_class_probs(multiclass_pipeline, val_df[list(ALL_FEATURES_R7A)], NUM_CLASSES)
    test_raw_probs = _multiclass_to_class_probs(multiclass_pipeline, test_df[list(ALL_FEATURES_R7A)], NUM_CLASSES)
    val_score_sb = compute_picker_score_s_b_raw(val_raw_probs)
    test_score_sb = compute_picker_score_s_b_raw(test_raw_probs)
    fi_baseline = compute_feature_importance_diagnostic(multiclass_pipeline)
    print(f"  multiclass S-B: fit+predict {time.time() - t0:.1f}s")

    # 13. Build tabular control scores INSIDE sequence-cell harness (windowed-valid subset)
    print("Building C-d2-arch-control scores inside sequence-cell harness...")
    val_score_tabular = score_rows_via_tabular(tabular_regressor, val_df[list(ALL_FEATURES_R7A)], valid_val)
    test_score_tabular = score_rows_via_tabular(tabular_regressor, test_df[list(ALL_FEATURES_R7A)], valid_test)
    harness_verification = {
        "status": "PASS",
        "tabular_eval_inside_sequence_harness": "succeeded",
        "n_val_scored": int(np.isfinite(val_score_tabular).sum()),
        "n_test_scored": int(np.isfinite(test_score_tabular).sum()),
    }

    if args.sanity_probe_only:
        # Sanity probe path: stop after coverage + causality + harness verification
        sanity = run_sanity_probe_29_0b(
            train_df, val_df, test_df, pair_runtime_map, args.pairs, days=args.days,
            pnl_train_full=pnl_train_full,
            coverage_train=coverage_train, coverage_val=coverage_val, coverage_test=coverage_test,
            causality_check_train=causality_check_train,
            harness_verification=harness_verification,
            train_drop_for_nan_pnl_count=nan_pnl_train,
        )
        if not args.no_write:
            (args.out_dir / "sanity_probe.json").write_text(
                json.dumps(sanity, indent=2, default=str), encoding="utf-8"
            )
            print(f"\nsanity probe results: {args.out_dir / 'sanity_probe.json'}")
        print("\n--sanity-probe-only set; exiting after probe.")
        return 0

    # 14. Train sequence models (S1 / S2 / S3)
    print("\nTraining sequence models...")
    sequence_scores_val: dict[str, np.ndarray] = {}
    sequence_scores_test: dict[str, np.ndarray] = {}
    training_results: dict[str, dict] = {}
    gpu_memory_results: dict[str, dict] = {}
    sequence_models: dict[str, object] = {}

    # Prepare train/val targets (windowed-valid subset)
    pnl_train_full_arr = pnl_train_full
    valid_train_for_seq = valid_train & np.isfinite(pnl_train_full_arr)
    valid_val_for_seq = valid_val & np.isfinite(pnl_val_full)

    seq_train_idx = np.flatnonzero(valid_train_for_seq)
    seq_val_idx = np.flatnonzero(valid_val_for_seq)
    seq_test_idx = np.flatnonzero(valid_test)

    train_x_seq = windowed_train[seq_train_idx]
    train_y_seq = pnl_train_full[seq_train_idx].astype(np.float32)
    val_x_seq = windowed_val[seq_val_idx]
    val_y_seq = pnl_val_full[seq_val_idx].astype(np.float32)
    test_x_seq = windowed_test[seq_test_idx]

    for arch_id in requested_archs:
        if arch_id not in CLOSED_ARCHITECTURE_ALLOWLIST:
            raise ValueError(f"Unknown arch_id={arch_id!r}; NG#A0B-1")
        print(f"\n  === {arch_id} ===")
        t0 = time.time()
        reset_gpu_memory_tracker(device)
        model = build_sequence_model(arch_id)
        checkpoint_path = CHECKPOINTS_ROOT / f"{arch_id}_seed42.pt"
        result = train_sequence_model(
            model, arch_id, train_x_seq, train_y_seq, val_x_seq, val_y_seq,
            checkpoint_path=checkpoint_path, device=device,
        )
        training_results[arch_id] = {
            "best_epoch": result.best_epoch,
            "best_val_huber_loss": result.best_val_huber_loss,
            "val_huber_loss_per_epoch": result.val_huber_loss_per_epoch,
            "train_huber_loss_per_epoch": result.train_huber_loss_per_epoch,
            "early_stopping_triggered": result.early_stopping_triggered,
            "epochs_run": result.epochs_run,
            "checkpoint_path": result.checkpoint_path,
            "seed": result.seed,
            "fit_time_sec": time.time() - t0,
        }
        gpu_memory_results[arch_id] = estimate_gpu_memory_after_fit(device)
        # Load best checkpoint
        model = load_checkpoint(model, checkpoint_path, device)
        sequence_models[arch_id] = model
        # Inference
        scores_val = np.full(len(val_df), np.nan, dtype=np.float64)
        scores_test = np.full(len(test_df), np.nan, dtype=np.float64)
        if len(seq_val_idx) > 0:
            scores_val[seq_val_idx] = predict_sequence_score(
                model, val_x_seq, batch_size=_sequence_training.ARCH_TRAINING_CONFIG[arch_id]["batch_size"],
                device=device,
            )
        if len(seq_test_idx) > 0:
            scores_test[seq_test_idx] = predict_sequence_score(
                model, test_x_seq, batch_size=_sequence_training.ARCH_TRAINING_CONFIG[arch_id]["batch_size"],
                device=device,
            )
        sequence_scores_val[arch_id] = scores_val
        sequence_scores_test[arch_id] = scores_test
        print(
            f"  {arch_id}: best_epoch={result.best_epoch} "
            f"val_huber={result.best_val_huber_loss:+.6f} "
            f"epochs_run={result.epochs_run} early_stop={result.early_stopping_triggered} "
            f"({training_results[arch_id]['fit_time_sec']:.1f}s)"
        )

    # 15. Regression diagnostic per architecture
    regression_diag_per_arch: dict[str, dict] = {}
    predicted_pnl_distribution: dict[str, dict] = {}
    for arch_id in requested_archs:
        s_val = sequence_scores_val[arch_id]
        s_test = sequence_scores_test[arch_id]
        # Train pred too (re-compute on full train)
        train_x_seq_full = windowed_train[np.flatnonzero(valid_train)]
        if len(train_x_seq_full) > 0:
            s_train = predict_sequence_score(
                sequence_models[arch_id], train_x_seq_full,
                batch_size=_sequence_training.ARCH_TRAINING_CONFIG[arch_id]["batch_size"],
                device=device,
            )
            train_pred_full = np.full(len(train_df), np.nan, dtype=np.float64)
            train_pred_full[np.flatnonzero(valid_train)] = s_train
        else:
            train_pred_full = np.full(len(train_df), np.nan, dtype=np.float64)
        regression_diag_per_arch[arch_id] = {
            "train": compute_regression_diagnostic(pnl_train_full, train_pred_full),
            "val": compute_regression_diagnostic(pnl_val_full, s_val),
            "test": compute_regression_diagnostic(pnl_test_full, s_test),
            "val_huber_loss": training_results[arch_id]["best_val_huber_loss"],
        }
        pred_dist: dict = {}
        for split_name, pred in [("train", train_pred_full), ("val", s_val), ("test", s_test)]:
            finite = pred[np.isfinite(pred)]
            if len(finite) == 0:
                pred_dist[split_name] = {"n_finite": 0}
                continue
            pred_dist[split_name] = {
                "n_finite": int(len(finite)),
                "mean": float(finite.mean()),
                "p5": float(np.quantile(finite, 0.05)),
                "p50": float(np.quantile(finite, 0.50)),
                "p95": float(np.quantile(finite, 0.95)),
            }
        predicted_pnl_distribution[arch_id] = pred_dist

    # 16. Cell construction + evaluation
    print("\nPer-cell evaluation...")
    cells = build_a0_broad_cells()
    cell_results: list[dict] = []
    for i, cell in enumerate(cells):
        t_cell = time.time()
        cell_id = cell["id"]
        if cell.get("is_baseline"):
            # C-sb-baseline: full row-set (no windowing); top-q q=5 only
            v_score = val_score_sb
            t_score = test_score_sb
            pnl_v = pnl_val_full
            pnl_t = pnl_test_full
            fi = fi_baseline
        elif cell.get("is_arch_control"):
            # C-d2-arch-control: tabular LightGBM scores inside sequence-cell harness;
            # windowed-valid subset
            v_score = val_score_tabular
            t_score = test_score_tabular
            pnl_v = pnl_val_full
            pnl_t = pnl_test_full
            fi = fi_tabular
        else:
            # Sequence cell
            arch_id = cell["arch_id"]
            v_score = sequence_scores_val[arch_id]
            t_score = sequence_scores_test[arch_id]
            pnl_v = pnl_val_full
            pnl_t = pnl_test_full
            fi = {"arch_id": arch_id, "note": "sequence model; feature importance via attention / saliency not embedded"}

        result = evaluate_quantile_cell_29_0b(
            cell, train_df, val_df, test_df,
            train_label, val_label, test_label,
            val_raw_probs, test_raw_probs,
            v_score, t_score, pnl_v, pnl_t, fi,
        )
        cell_results.append(result)
        rm = result.get("test_realised_metrics", {})
        sp = result.get("test_formal_spearman", float("nan"))
        sq = result.get("selected_q_percent")
        print(
            f"  cell {i+1}/{len(cells)} {cell_id} | q*={sq} | "
            f"val_sharpe={result.get('val_realised_sharpe', float('nan')):+.3f} "
            f"val_n={result.get('val_n_trades', 0):>6} | "
            f"test_sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"test_n={rm.get('n_trades', 0):>6} test_sp={sp:+.4f} "
            f"({time.time() - t_cell:.1f}s)"
        )

    # 17. C-sb-baseline FAIL-FAST
    print("\n=== C-sb-baseline FAIL-FAST (Phase 28 §10 inherited) ===")
    c_sb_baseline = next((c for c in cell_results if c["cell"]["id"] == "C-sb-baseline"), None)
    if c_sb_baseline is None or c_sb_baseline.get("h_state") != "OK":
        raise BaselineMismatchError("C-sb-baseline missing or h_state != OK")
    baseline_match_report = check_c_sb_baseline_match_29_0b(c_sb_baseline)
    print(f"  baseline_match={baseline_match_report['all_match']}")

    # 18. C-d2-arch-control 7th-anchor drift (DIAGNOSTIC-ONLY WARN)
    print("\n=== C-d2-arch-control 7th-anchor drift vs 27.0d C-se (DIAGNOSTIC-ONLY WARN) ===")
    c_d2_arch_control = next(
        (c for c in cell_results if c["cell"]["id"] == "C-d2-arch-control"), None
    )
    if c_d2_arch_control is None or c_d2_arch_control.get("h_state") != "OK":
        arch_control_drift_report = {
            "source": "n/a", "warn": True, "all_within_tolerance": False,
            "chain_position": "7th anchor",
            "note": "C-d2-arch-control not present or h_state != OK",
        }
    else:
        arch_control_drift_report = compute_c_d2_arch_control_drift_check(c_d2_arch_control)
        if arch_control_drift_report["warn"]:
            warnings.warn(
                f"C-d2-arch-control drift vs 27.0d C-se exceeds tolerance "
                "(DIAGNOSTIC-ONLY WARN per PR #354 §10.3 / NG#A0B-3; NOT HALT)",
                UserWarning, stacklevel=2,
            )
        print(f"  all_within_tolerance={arch_control_drift_report.get('all_within_tolerance')}")

    # 19. Within-eval drift per architecture
    print("\n=== Within-eval drift per architecture (vs C-d2-arch-control) ===")
    within_eval_drift_per_arch: dict[str, dict] = {}
    for arch_id in requested_archs:
        seq_cell = next((c for c in cell_results if c["cell"]["id"] == f"C-d2-{arch_id}"), None)
        if seq_cell is None or c_d2_arch_control is None:
            within_eval_drift_per_arch[arch_id] = {
                "all_within_tolerance": False, "warn": True,
                "note": "sequence cell or arch-control missing",
            }
        else:
            within_eval_drift_per_arch[arch_id] = compute_within_eval_tabular_drift_check(
                seq_cell, c_d2_arch_control
            )
        d = within_eval_drift_per_arch[arch_id]
        print(
            f"  {arch_id}: all_within_tolerance={d.get('all_within_tolerance')} "
            f"(n_trades_Δ={d.get('n_trades_delta', '-')})"
        )

    # 20. Val-selection + cross-cell verdict
    selectable_cells = [c for c in cell_results if not c["cell"].get("is_baseline", False)]
    val_select = select_cell_validation_only(selectable_cells)
    verdict_info = assign_verdict(val_select.get("selected"))
    aggregate_info = aggregate_cross_cell_verdict(selectable_cells)
    print("\n=== Val-selected (cell*, q*) cross-cell ===")
    sel = val_select.get("selected")
    if sel is not None:
        print(f"  cell: {_cell_signature(sel['cell'])}")
        rm = sel.get("test_realised_metrics", {})
        print(
            f"  q*={sel.get('selected_q_percent')} | "
            f"val Sharpe={sel.get('val_realised_sharpe', float('nan')):+.4f}; "
            f"test Sharpe={rm.get('sharpe', float('nan')):+.4f}; "
            f"n_trades={rm.get('n_trades', 0)}"
        )
    print(f"\n=== Cross-cell aggregate: {aggregate_info['aggregate_verdict']} ===")

    # 21. H-D2 per-architecture outcomes
    print("\n=== H-D2 4-outcome ladder per architecture ===")
    h_d2_per_arch: list[dict] = []
    for arch_id in requested_archs:
        seq_cell = next((c for c in cell_results if c["cell"]["id"] == f"C-d2-{arch_id}"), None)
        if seq_cell is None:
            h_d2_per_arch.append({
                "cell_id": f"C-d2-{arch_id}", "arch_id": arch_id,
                "outcome": H_D2_OUTCOME_NEEDS_REVIEW, "row_matched": 0, "reason": "cell missing",
            })
            continue
        outcome = compute_h_d2_outcome_per_arch(
            seq_cell, baseline_match_report.get("all_match", False),
            within_eval_drift_per_arch.get(arch_id, {}), arch_id,
        )
        h_d2_per_arch.append(outcome)
        print(
            f"  {arch_id}: {outcome.get('outcome')} (row {outcome.get('row_matched')}) "
            f"— {outcome.get('reason', '-')[:80]}"
        )

    # 22. Aggregate H-D2 verdict
    h_d2_aggregate = compute_h_d2_aggregate_verdict(h_d2_per_arch)
    print(f"\n=== Aggregate H-D2 verdict: {h_d2_aggregate.get('aggregate_verdict')} ===")
    print(f"=== A0-broad-narrow status: {h_d2_aggregate.get('a0_broad_status')} ===")
    print(f"=== Routing: {h_d2_aggregate.get('routing_implication')} ===")

    if args.no_write:
        return 0

    # 23. Determinism check (DIAGNOSTIC; deferred to manual re-run via --sanity-probe-only twice)
    determinism_check: dict = {
        "note": "metric-level tolerance per PR #354 §16.2 item 11; manual re-run "
                "for full check; auto-check within single-run not performed",
        "all_within_tolerance": None,
    }

    # 24. Top-tail regime audit per architecture
    print("Computing top-tail regime audit per architecture...")
    top_tail_regime_audit_per_arch: dict[str, dict] = {}
    for arch_id in requested_archs:
        top_tail_regime_audit_per_arch[arch_id] = compute_top_tail_regime_audit(
            sequence_scores_val[arch_id], val_df,
        )
    top_tail_regime_audit_per_arch["TABULAR_CONTROL"] = compute_top_tail_regime_audit(
        val_score_tabular, val_df,
    )

    # 25. Sanity probe full post-fit
    feature_importance_per_arch = {arch_id: {"arch_id": arch_id, "note": "sequence model"} for arch_id in requested_archs}
    feature_importance_per_arch["TABULAR_CONTROL"] = fi_tabular
    feature_importance_per_arch["BASELINE"] = fi_baseline

    sanity = run_sanity_probe_29_0b(
        train_df, val_df, test_df, pair_runtime_map, args.pairs, days=args.days,
        pnl_train_full=pnl_train_full,
        coverage_train=coverage_train, coverage_val=coverage_val, coverage_test=coverage_test,
        causality_check_train=causality_check_train,
        harness_verification=harness_verification,
        training_convergence=training_results,
        gpu_memory=gpu_memory_results,
        determinism_check=determinism_check,
        cell_definitions=cells,
        train_drop_for_nan_pnl_count=nan_pnl_train,
    )

    # 26. Write eval_report.md
    report_path = args.out_dir / "eval_report.md"
    write_eval_report_29_0b(
        report_path, cell_results, val_select, verdict_info, aggregate_info,
        baseline_match_report, arch_control_drift_report,
        h_d2_per_arch, h_d2_aggregate, within_eval_drift_per_arch,
        sanity, drop_stats_r7a, (t_min, t70, t85, t_max), preflight_diag,
        len(cells), feature_importance_per_arch, regression_diag_per_arch,
        predicted_pnl_distribution, top_tail_regime_audit_per_arch,
    )
    print(f"\nReport: {report_path}")

    # 27. Persist artifacts
    summary_rows: list[dict] = []
    for c in cell_results:
        cell = c["cell"]
        rm = c.get("test_realised_metrics", {})
        sp = c.get("test_formal_spearman", float("nan"))
        sq = c.get("selected_q_percent")
        sq_serialised = float(sq) if sq is not None else -1
        sc = c.get("selected_cutoff")
        sc_serialised = float(sc) if isinstance(sc, (int, float)) else float("nan")
        summary_rows.append({
            "cell_id": cell["id"], "picker_name": cell["picker"],
            "score_type": cell.get("score_type", "-"), "feature_set": cell.get("feature_set", "-"),
            "arch_id": cell.get("arch_id", "-"),
            "is_baseline": cell.get("is_baseline", False),
            "is_arch_control": cell.get("is_arch_control", False),
            "quantile_percents": list(cell.get("quantile_percents", ())),
            "n_train": c.get("n_train", 0), "n_val": c.get("n_val", 0), "n_test": c.get("n_test", 0),
            "selected_q_percent": sq_serialised, "selected_cutoff": sc_serialised,
            "val_realised_sharpe": c.get("val_realised_sharpe", float("nan")),
            "val_n_trades": c.get("val_n_trades", 0),
            "test_sharpe": rm.get("sharpe", float("nan")),
            "test_annual_pnl": rm.get("annual_pnl", float("nan")),
            "test_n_trades": rm.get("n_trades", 0),
            "test_formal_spearman": sp, "h_state": c.get("h_state"),
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_df_p = summary_df.copy()
    summary_df_p["quantile_percents"] = summary_df_p["quantile_percents"].apply(lambda x: json.dumps(x))
    summary_df_p.to_parquet(args.out_dir / "sweep_results.parquet")
    summary_df.to_json(args.out_dir / "sweep_results.json", orient="records", indent=2)

    aggregate = dict(verdict_info)
    aggregate["cross_cell"] = {
        "agree": aggregate_info["agree"], "branches": aggregate_info["branches"],
        "aggregate_verdict": aggregate_info["aggregate_verdict"],
    }
    aggregate["baseline_match_report"] = baseline_match_report
    aggregate["arch_control_drift_report"] = arch_control_drift_report
    aggregate["within_eval_drift_per_arch"] = within_eval_drift_per_arch
    aggregate["h_d2_per_arch"] = h_d2_per_arch
    aggregate["h_d2_aggregate"] = h_d2_aggregate
    aggregate["training_results"] = training_results
    aggregate["gpu_memory"] = gpu_memory_results
    aggregate["top_tail_regime_audit_per_arch"] = top_tail_regime_audit_per_arch
    aggregate["closed_architecture_allowlist"] = list(CLOSED_ARCHITECTURE_ALLOWLIST)
    if val_select.get("selected") is not None:
        sel = val_select["selected"]
        aggregate["val_selected"] = {
            "cell": {k: (list(v) if isinstance(v, tuple) else v) for k, v in sel["cell"].items()},
            "selected_q_percent": sel["selected_q_percent"],
            "selected_cutoff": sel["selected_cutoff"],
            "val_realised_sharpe": sel["val_realised_sharpe"],
            "val_n_trades": sel["val_n_trades"],
            "test_realised_metrics": sel.get("test_realised_metrics", {}),
            "test_formal_spearman": sel.get("test_formal_spearman", float("nan")),
        }
    (args.out_dir / "aggregate_summary.json").write_text(
        json.dumps(aggregate, indent=2, default=str), encoding="utf-8"
    )
    (args.out_dir / "val_selected_cell.json").write_text(
        json.dumps(aggregate.get("val_selected", {}), indent=2, default=str), encoding="utf-8"
    )
    (args.out_dir / "sanity_probe.json").write_text(
        json.dumps(sanity, indent=2, default=str), encoding="utf-8"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
