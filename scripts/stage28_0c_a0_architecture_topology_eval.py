"""Stage 28.0c-β A0-narrow Tabular Architecture-Topology Audit eval.

Implements PR #344 (Phase 28.0c-α design memo) under PR #343 (post-28.0b
routing review primary recommendation) + PR #335 (Phase 28 kickoff).

Mission (PR #344 §1):
  Phase 28.0c is an A0-narrow tabular architecture-topology audit, NOT
  the full A0-broad sequence/NN redesign. A negative result falsifies
  A0-narrow, not all possible A0. A0-broad remains deferred-not-foreclosed.

Closed 4-architecture allowlist (α-fixed numerics per PR #344 §4; NG#A0-1):
  AR1 hierarchical two-stage: stage-1 LightGBMClassifier (S-B) → top 50%
    per-pair val-median admission → stage-2 LightGBMRegressor (S-E)
    trained on admitted-train.
  AR2 pair-conditioned specialists: 20 per-pair LightGBMRegressors with
    27.0d S-E backbone verbatim (NO per-pair hyperparameter tuning).
  AR3 stacked S-B/S-E blend: score = 0.5·rank_norm(S-B raw) +
    0.5·rank_norm(S-E); fixed blend weight; no β-time grid sweep.
  AR4 deterministic regime split: 2 LightGBMRegressors (high-vol /
    low-vol) routed by per-pair val-median atr_at_signal_pip.

Fixed feature / target / rule / loss (PR #344 §5; NG#A0-1):
  - R7-A only (4 features: pair, direction, atr_at_signal_pip,
    spread_at_signal_pip)
  - Triple-barrier realised PnL (K_FAV=1.5×ATR; K_ADV=1.0×ATR; H_M1=60)
  - Top-q on score with quantile family {5, 10, 20, 30, 40}
  - Symmetric Huber α=0.9; sample_weight=1 (inherited from 27.0d S-E)

6-cell structure (PR #344 §9; NG#A0-3 mandatory C-a0-arch-control):
  C-a0-AR1, C-a0-AR2, C-a0-AR3, C-a0-AR4 — 4 architecture variants
  C-a0-arch-control — architecture-axis null; rule-axis null;
    reproduces 27.0d C-se / 27.0f r7a-replica / 28.0a r7a-replica /
    28.0b top-q-control with sample_weight=1
  C-sb-baseline — multiclass S-B; §10 baseline FAIL-FAST

H-C3 4-outcome ladder per AR (PR #344 §12.3; precedence row 4 > 1 > 2 > 3):
  Row 4 PARTIAL_DRIFT_ARCH_REPLICA (checked FIRST per NG#A0-3): C-a0-ARx
    ≈ C-a0-arch-control at val-selected q* within tolerance
    (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%). Architecture had
    zero effect.
  Row 1 PASS: H2 PASS (val Sharpe lift ≥ +0.05) AND H1m ≥ +0.30 AND
    H3 ≥ 20,000 trades AND C-sb-baseline reproduction PASS.
  Row 2 PARTIAL_SUPPORT: val Sharpe lift ∈ [+0.02, +0.05); others intact.
  Row 3 FALSIFIED_ARCH_INSUFFICIENT (default): val Sharpe lift < +0.02 OR
    other H-C3 conditions fail.

Aggregate verdict (PR #344 §12.4; FALSIFIED_A0_NARROW distinction):
  any AR PASS → SPLIT_VERDICT_ROUTE_TO_REVIEW
  0 PASS + 1+ PARTIAL_SUPPORT → REJECT_NON_DISCRIMINATIVE (sub-threshold)
  all 4 FALSIFIED or PARTIAL_DRIFT → REJECT_NON_DISCRIMINATIVE +
    diagnostic note FALSIFIED_A0_NARROW (NEVER FALSIFIED_ALL_A0;
    A0-broad sequence/NN remains deferred-not-foreclosed)

Interpretation guards (PR #344 §3 §4 §12; user-pre-stated at β kickoff):
  AR1: stage-1 admission threshold resembles 28.0b R1 (A4 selection-like
    behavior). Admitted under A0-narrow as architecture-conditioning
    (stage-2 training set), NOT final selection rule. PASS/PARTIAL_SUPPORT
    reasons MUST use "architecture-topology with embedded admission gate".
  AR4: deterministic regime split is A3-boundary-sensitive. Admitted
    under A0-narrow because routing is deterministic (no learned gating /
    MoE / adaptive weights). A3 elevation requires separate scope
    amendment. PASS/PARTIAL_SUPPORT reasons MUST use "deterministic
    tabular regime split helped" (NOT "full A3 solved").

No-fallback policy (PR #344 §6 NG#A0-1):
  AR1 admitted-train shortage, AR2 per-pair fit failure, AR4 regime
  imbalance: HALT (or WARN-only diagnostic for AR4). No fallback to
  global model / hyperparameter tuning / threshold adjustment.

Row-set policy (A0-narrow):
  All 6 cells share R7-A-clean parent row-set. Fix A row-set isolation
  contract not exercised. No R7-C drop.

MANDATORY CLAUSES (inherited verbatim from 28.0b-β; Clause 6 updated):
1. Phase framing. ADOPT requires H2 PASS + full 8-gate A0-A5 harness.
   H2 PASS = PROMISING_BUT_NEEDS_OOS only; ADOPT_CANDIDATE wall preserved.
2. Diagnostic columns prohibition. Calibration / threshold-sweep /
   directional-comparison / classification-quality / feature-importance /
   per-pair-Sharpe-contribution columns are diagnostic-only. 28.0c
   extension: per-AR artifact-count audit, per-AR within-eval drift vs
   arch-control, AR1 stage-1 threshold distribution, AR2 per-pair train
   row count distribution, AR3 blend rank distribution, AR4 regime split
   distribution, top-tail regime audit (spread_at_signal_pip only;
   R7-C features NOT computed) are diagnostic-only.
3. γ closure preservation. PR #279 is unmodified.
4. Production-readiness preservation. X-v2 OOS gating remains required.
   v9 20-pair (Phase 9.12 tip 79ed1e8) untouched. Phase 22 frozen-OOS
   contract preserved.
5. NG#10 / NG#11 not relaxed.
6. Phase 28 scope. Phase 28 is a structural rebase opened at PR #335
   after R-E routing decision. A0/A1/A2/A3/A4 admissible at kickoff. A1
   exhausted by 28.0a-β (PR #338). A4 exhausted by 28.0b-β (PR #342);
   R-T1 absorbed and FALSIFIED_under_A4. A0-narrow is tested by this
   sub-phase per PR #343 routing review. A0-broad (sequence / NN model
   classes) is deferred-not-foreclosed per PR #344 §7.2; admissible via
   separate scope amendment if Path A all-FALSIFIED triggers post-28.0c
   re-routing.

PRODUCTION-MISUSE GUARDS (inherited verbatim):
GUARD 1 — research-not-production: 28.0c features stay in scripts/.
GUARD 2 — threshold-sweep-diagnostic.
GUARD 3 — directional-comparison-diagnostic.
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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage28_0c"
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

# Inherited constants and helpers
PAIRS_20 = stage23_0a.PAIRS_20
load_m1_ba = stage23_0a.load_m1_ba
pip_size_for = stage23_0a.pip_size_for

_compute_realised_barrier_pnl = stage25_0b._compute_realised_barrier_pnl
compute_8_gate_metrics = stage25_0b.compute_8_gate_metrics
gate_matrix = stage25_0b.gate_matrix
LOW_POWER_N_TEST = stage25_0b.LOW_POWER_N_TEST
LOW_POWER_N_TRAIN = stage25_0b.LOW_POWER_N_TRAIN
SPAN_DAYS = stage25_0b.SPAN_DAYS
SPAN_YEARS = SPAN_DAYS / 365.25
TRAIN_FRAC = stage25_0b.TRAIN_FRAC
VAL_FRAC = stage25_0b.VAL_FRAC
split_70_15_15 = stage25_0b.split_70_15_15

precompute_realised_pnl_per_row = stage26_0b.precompute_realised_pnl_per_row
compute_pair_concentration = stage26_0b.compute_pair_concentration
verify_l3_preflight = stage26_0b.verify_l3_preflight
L3PreflightError = stage26_0b.L3PreflightError

build_l1_labels_for_dataframe = stage26_0c.build_l1_labels_for_dataframe
compute_8_gate_from_pnls = stage26_0c.compute_8_gate_from_pnls
compute_classification_diagnostics = stage26_0c.compute_classification_diagnostics
compute_mid_to_mid_pnl_diagnostic = stage26_0c.compute_mid_to_mid_pnl_diagnostic
assign_verdict = stage26_0c.assign_verdict
aggregate_cross_cell_verdict = stage26_0c.aggregate_cross_cell_verdict
select_cell_validation_only = stage26_0c.select_cell_validation_only
SanityProbeError = stage26_0c.SanityProbeError
fit_quantile_cutoff_on_val = stage26_0c.fit_quantile_cutoff_on_val
_eval_threshold_mask = stage26_0c._eval_threshold_mask

build_pipeline_lightgbm_multiclass_widened = stage26_0d.build_pipeline_lightgbm_multiclass_widened
drop_rows_with_missing_new_features = stage26_0d.drop_rows_with_missing_new_features
compute_feature_importance_diagnostic = stage26_0d.compute_feature_importance_diagnostic

compute_per_pair_sharpe_contribution = stage27_0b.compute_per_pair_sharpe_contribution
make_oof_fold_assignment = stage27_0c.make_oof_fold_assignment
compute_picker_score_s_b_raw = stage27_0c.compute_picker_score_s_b_raw

build_pipeline_lightgbm_regression_widened = stage27_0d.build_pipeline_lightgbm_regression_widened
fit_oof_regression_diagnostic = stage27_0d.fit_oof_regression_diagnostic
compute_oof_correlation_diagnostic = stage27_0d.compute_oof_correlation_diagnostic
compute_regression_diagnostic = stage27_0d.compute_regression_diagnostic
compute_picker_score_s_e = stage27_0d.compute_picker_score_s_e

evaluate_quantile_family_custom = stage27_0e.evaluate_quantile_family_custom
compute_trade_count_budget_audit = stage27_0e.compute_trade_count_budget_audit
load_27_0d_c_se_metrics = stage27_0e.load_27_0d_c_se_metrics


# ---------------------------------------------------------------------------
# Binding constants (inherited)
# ---------------------------------------------------------------------------

K_FAV = stage25_0b.K_FAV
K_ADV = stage25_0b.K_ADV
H_M1_BARS = stage25_0b.H_M1_BARS

LABEL_TP = stage26_0c.LABEL_TP
LABEL_SL = stage26_0c.LABEL_SL
LABEL_TIME = stage26_0c.LABEL_TIME
NUM_CLASSES = stage26_0c.NUM_CLASSES

NUMERIC_FEATURES_R7A = stage26_0d.NUMERIC_FEATURES
ALL_FEATURES_R7A = stage26_0d.ALL_FEATURES  # 4 features: pair + direction + atr + spread
CATEGORICAL_COLS = stage26_0d.CATEGORICAL_COLS

LIGHTGBM_REGRESSION_CONFIG = stage27_0d.LIGHTGBM_REGRESSION_CONFIG
HUBER_ALPHA = stage27_0d.HUBER_ALPHA  # 0.9 (symmetric Huber backbone for S-E)
LIGHTGBM_MULTICLASS_CONFIG = stage27_0d.LIGHTGBM_MULTICLASS_CONFIG

H1_WEAK_THRESHOLD = stage26_0c.H1_WEAK_THRESHOLD
H1_MEANINGFUL_THRESHOLD = stage26_0c.H1_MEANINGFUL_THRESHOLD
H3_REFERENCE_SHARPE = stage26_0c.H3_REFERENCE_SHARPE
A1_MIN_SHARPE = stage25_0b.A1_MIN_SHARPE
A2_MIN_ANNUAL_PNL = stage25_0b.A2_MIN_ANNUAL_PNL

CONCENTRATION_HIGH_THRESHOLD = stage26_0c.CONCENTRATION_HIGH_THRESHOLD
SANITY_MIN_CLASS_SHARE = stage26_0c.SANITY_MIN_CLASS_SHARE
SANITY_MAX_PER_PAIR_TIME_SHARE = stage26_0c.SANITY_MAX_PER_PAIR_TIME_SHARE
SANITY_MAX_NEW_FEATURE_NAN_RATE = stage26_0d.SANITY_MAX_NEW_FEATURE_NAN_RATE
SANITY_MAX_POSITIVITY_VIOLATION_RATE = stage26_0d.SANITY_MAX_POSITIVITY_VIOLATION_RATE

TEST_SPAN_YEARS = SPAN_YEARS * (1.0 - TRAIN_FRAC - VAL_FRAC)
VAL_SPAN_YEARS = SPAN_YEARS * VAL_FRAC

OOF_N_FOLDS = stage27_0c.OOF_N_FOLDS
OOF_SEED = stage27_0c.OOF_SEED

# §10 baseline reference (PR #335 §10; immutable)
BASELINE_27_0B_C_ALPHA0_N_TRADES = stage27_0d.BASELINE_27_0B_C_ALPHA0_N_TRADES
BASELINE_27_0B_C_ALPHA0_SHARPE = stage27_0d.BASELINE_27_0B_C_ALPHA0_SHARPE
BASELINE_27_0B_C_ALPHA0_ANN_PNL = stage27_0d.BASELINE_27_0B_C_ALPHA0_ANN_PNL
BASELINE_MATCH_N_TRADES_TOLERANCE = stage27_0d.BASELINE_MATCH_N_TRADES_TOLERANCE
BASELINE_MATCH_SHARPE_ABS_TOLERANCE = stage27_0d.BASELINE_MATCH_SHARPE_ABS_TOLERANCE
BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE = stage27_0d.BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE

# §10 baseline val Sharpe (immutable reference for H-C3 H2 lift threshold)
SECTION_10_BASELINE_VAL_SHARPE = -0.1863  # from PR #335 §10 (verbatim)

NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD = stage27_0d.NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD


# ---------------------------------------------------------------------------
# NEW Phase 28.0c constants (closed 4-architecture allowlist; α-fixed per
# PR #344 §4; NG#A0-1)
# ---------------------------------------------------------------------------

# AR1 stage-1 admission threshold (PR #344 §4.1; top 50% per-pair val-median)
AR1_STAGE1_ADMIT_PERCENTILE = 50.0  # per-pair val-median; top 50% admitted

# AR1 stage-2 admitted-train minimum rows per pair (no-fallback HALT trigger)
AR1_STAGE2_MIN_ROWS_PER_PAIR_HALT = 200

# AR2 per-pair minimum train rows (no-fallback HALT trigger)
AR2_PER_PAIR_MIN_TRAIN_ROWS_HALT = 200

# AR3 blend weight (PR #344 §4.3; 0.5 / 0.5 fixed; NG#A0-1)
AR3_BLEND_W_SB = 0.5
AR3_BLEND_W_SE = 0.5

# AR4 regime split (PR #344 §4.4; per-pair val-median atr_at_signal_pip)
AR4_REGIME_SPLIT_FEATURE = "atr_at_signal_pip"
AR4_REGIME_SPLIT_PERCENTILE = 50.0  # per-pair val-median

# AR4 regime imbalance WARN threshold (5% min per regime; below = WARN only)
AR4_REGIME_IMBALANCE_WARN_FRACTION = 0.05

# Quantile family for all 6 cells (PR #344 §9; inherited)
QUANTILE_PERCENTS_28_0C: tuple[float, ...] = (5.0, 10.0, 20.0, 30.0, 40.0)

# H-C3 thresholds (PR #344 §12.1)
H2_LIFT_THRESHOLD_PASS = 0.05
H2_LIFT_THRESHOLD_PARTIAL_SUPPORT_LO = 0.02
H1M_PRESERVE_THRESHOLD = 0.30
H3_TRADE_COUNT_THRESHOLD = 20000

# H-C3 outcome labels (PR #344 §12.3)
H_C3_OUTCOME_PASS = "PASS"
H_C3_OUTCOME_PARTIAL_SUPPORT = "PARTIAL_SUPPORT"
H_C3_OUTCOME_FALSIFIED_ARCH_INSUFFICIENT = "FALSIFIED_ARCH_INSUFFICIENT"
H_C3_OUTCOME_PARTIAL_DRIFT_ARCH_REPLICA = "PARTIAL_DRIFT_ARCH_REPLICA"
H_C3_OUTCOME_NEEDS_REVIEW = "NEEDS_REVIEW"

# C-a0-arch-control drift tolerances vs 27.0d C-se (PR #344 §11; inherited)
ARCH_CONTROL_DRIFT_N_TRADES_TOLERANCE = 100
ARCH_CONTROL_DRIFT_SHARPE_TOLERANCE = 5e-3
ARCH_CONTROL_DRIFT_ANN_PNL_FRAC_TOLERANCE = 0.005

# Within-eval drift tolerances (PR #344 §6 NG#A0-3; same as arch-control)
WITHIN_EVAL_DRIFT_N_TRADES_TOLERANCE = 100
WITHIN_EVAL_DRIFT_SHARPE_TOLERANCE = 5e-3
WITHIN_EVAL_DRIFT_ANN_PNL_FRAC_TOLERANCE = 0.005

# Top-tail regime audit q values (PR #344 §15 §18; spread_at_signal_pip only)
TOP_TAIL_AUDIT_Q_PERCENTS: tuple[float, ...] = (10.0, 20.0)


# ---------------------------------------------------------------------------
# NEW exceptions
# ---------------------------------------------------------------------------


class BaselineMismatchError(RuntimeError):
    """Raised when C-sb-baseline fails to reproduce 27.0b C-alpha0 baseline.

    Per PR #344 §10 inheritance from 27.0c-α §7.3. FAIL-FAST HALT.
    """


class ArchitectureFitError(RuntimeError):
    """Raised when an AR variant fit fails the no-fallback policy.

    Per PR #344 §14 NG#A0-1: AR1 admitted-train shortage / AR2 per-pair
    fit failure → HALT (no fallback to global model / hyperparameter
    tuning / threshold adjustment).
    """


# ---------------------------------------------------------------------------
# Shared utilities (rank-normalise; per-pair median; class-prob extractor)
# ---------------------------------------------------------------------------


def _rank_normalise(scores: np.ndarray) -> np.ndarray:
    """Rank-normalise scores to uniform[0, 1] using pandas method='average'.

    Per PR #344 §4.3: deterministic on ties; NaN-safe (NaN → NaN; not ranked).
    Used by AR3 to combine S-B raw and S-E scores on the same scale.
    """
    arr = np.asarray(scores, dtype=np.float64)
    return pd.Series(arr).rank(pct=True, method="average").to_numpy()


def _compute_per_pair_median(
    pairs: np.ndarray, values: np.ndarray, percentile: float = 50.0
) -> dict[str, float]:
    """Compute per-pair quantile threshold (default median).

    Returns dict {pair_str: threshold}. Pairs with all-NaN values get NaN.
    """
    pair_arr = np.asarray(pairs)
    val_arr = np.asarray(values, dtype=np.float64)
    if len(pair_arr) != len(val_arr):
        raise ValueError(
            f"_compute_per_pair_median: pairs {len(pair_arr)} != values {len(val_arr)}"
        )
    out: dict[str, float] = {}
    for pair in sorted(set(pair_arr.tolist())):
        mask = pair_arr == pair
        finite = val_arr[mask & np.isfinite(val_arr)]
        if len(finite) == 0:
            out[str(pair)] = float("nan")
            continue
        out[str(pair)] = float(np.percentile(finite, percentile))
    return out


def _multiclass_to_class_probs(
    multiclass_pipeline, x: pd.DataFrame, num_classes: int
) -> np.ndarray:
    """Predict probabilities and re-order columns to [TP, SL, TIME] indexing."""
    raw_native = multiclass_pipeline.predict_proba(x)
    final_step = multiclass_pipeline.steps[-1][1]
    classes = np.asarray(getattr(final_step, "classes_", np.arange(num_classes)))
    out = np.zeros((len(raw_native), num_classes), dtype=np.float64)
    for col_idx, cls in enumerate(classes):
        cls_int = int(cls)
        out[:, cls_int] = raw_native[:, col_idx]
    return out


def _apply_per_pair_threshold_mask(
    pairs: np.ndarray, scores: np.ndarray, threshold_per_pair: dict[str, float]
) -> np.ndarray:
    """Return mask: row admitted if score >= threshold_per_pair[pair]."""
    pair_arr = np.asarray(pairs)
    score_arr = np.asarray(scores, dtype=np.float64)
    if len(pair_arr) != len(score_arr):
        raise ValueError(
            f"_apply_per_pair_threshold_mask: pairs {len(pair_arr)} != scores {len(score_arr)}"
        )
    thresholds = np.array(
        [threshold_per_pair.get(str(p), float("inf")) for p in pair_arr], dtype=np.float64
    )
    finite = np.isfinite(score_arr) & np.isfinite(thresholds)
    mask = np.zeros(len(score_arr), dtype=bool)
    mask[finite] = score_arr[finite] >= thresholds[finite]
    return mask


# ---------------------------------------------------------------------------
# AR1 — Hierarchical two-stage (PR #344 §4.1)
# ---------------------------------------------------------------------------


def fit_ar1_hierarchical(
    x_train_r7a: pd.DataFrame,
    train_label_clean: np.ndarray,
    train_pair_clean: np.ndarray,
    pnl_train_for_reg: np.ndarray,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict:
    """Fit AR1 hierarchical two-stage architecture (PR #344 §4.1).

    Stage 1: LightGBMClassifier (S-B multiclass on R7-A) fit on full
      R7-A-clean train. Score = P(TP) - P(SL) raw.
    Stage-1 admission threshold: per-pair val-median of stage-1 score
      (top 50%; alpha-fixed; NG#A0-1).
    Stage 2: LightGBMRegressor (S-E backbone) trained ONLY on
      stage-1-admitted train rows.

    No-fallback (NG#A0-1): if any pair has < AR1_STAGE2_MIN_ROWS_PER_PAIR_HALT
    admitted train rows, raise ArchitectureFitError.

    Interpretation guard (PR #344 §2.2 caveat): stage-1 admission threshold
    resembles A4 R1; admitted under A0-narrow as architecture-conditioning
    (stage-2 training set), NOT final selection rule.
    """
    stage1 = build_pipeline_lightgbm_multiclass_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stage1.fit(x_train_r7a, train_label_clean)

    val_x_r7a = val_df[list(ALL_FEATURES_R7A)]
    val_stage1_probs = _multiclass_to_class_probs(stage1, val_x_r7a, NUM_CLASSES)
    val_stage1_score = compute_picker_score_s_b_raw(val_stage1_probs)

    val_pair_arr = val_df["pair"].to_numpy()
    per_pair_threshold = _compute_per_pair_median(
        val_pair_arr, val_stage1_score, percentile=AR1_STAGE1_ADMIT_PERCENTILE
    )

    train_stage1_probs = _multiclass_to_class_probs(stage1, x_train_r7a, NUM_CLASSES)
    train_stage1_score = compute_picker_score_s_b_raw(train_stage1_probs)
    admitted_train_mask = _apply_per_pair_threshold_mask(
        train_pair_clean, train_stage1_score, per_pair_threshold
    )

    admitted_train_per_pair: dict[str, int] = {}
    for pair in sorted(set(train_pair_clean.tolist())):
        n = int(((train_pair_clean == pair) & admitted_train_mask).sum())
        admitted_train_per_pair[str(pair)] = n
    insufficient_pairs = [
        (p, n) for p, n in admitted_train_per_pair.items() if n < AR1_STAGE2_MIN_ROWS_PER_PAIR_HALT
    ]
    if insufficient_pairs:
        raise ArchitectureFitError(
            f"AR1 admitted-train shortage (NG#A0-1; no-fallback HALT): "
            f"{len(insufficient_pairs)} pair(s) with < "
            f"{AR1_STAGE2_MIN_ROWS_PER_PAIR_HALT} admitted train rows: "
            f"{insufficient_pairs[:5]}"
        )

    n_admitted_train = int(admitted_train_mask.sum())
    x_admitted_train = x_train_r7a.loc[admitted_train_mask].reset_index(drop=True)
    pnl_admitted_train = pnl_train_for_reg[admitted_train_mask]
    stage2 = build_pipeline_lightgbm_regression_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stage2.fit(x_admitted_train, pnl_admitted_train)

    val_stage2_score = compute_picker_score_s_e(stage2, val_x_r7a)
    test_x_r7a = test_df[list(ALL_FEATURES_R7A)]
    test_stage1_probs = _multiclass_to_class_probs(stage1, test_x_r7a, NUM_CLASSES)
    test_stage1_score = compute_picker_score_s_b_raw(test_stage1_probs)
    test_stage2_score = compute_picker_score_s_e(stage2, test_x_r7a)

    test_pair_arr = test_df["pair"].to_numpy()
    val_admit_mask = _apply_per_pair_threshold_mask(
        val_pair_arr, val_stage1_score, per_pair_threshold
    )
    test_admit_mask = _apply_per_pair_threshold_mask(
        test_pair_arr, test_stage1_score, per_pair_threshold
    )

    val_score_final = np.where(val_admit_mask, val_stage2_score, -np.inf).astype(np.float64)
    test_score_final = np.where(test_admit_mask, test_stage2_score, -np.inf).astype(np.float64)

    stage1_dist: dict[str, dict] = {}
    for pair in sorted(set(val_pair_arr.tolist())):
        mask = val_pair_arr == pair
        finite = val_stage1_score[mask][np.isfinite(val_stage1_score[mask])]
        if len(finite) == 0:
            stage1_dist[str(pair)] = {"n": 0}
            continue
        stage1_dist[str(pair)] = {
            "n": int(len(finite)),
            "p5": float(np.quantile(finite, 0.05)),
            "p50": float(np.quantile(finite, 0.50)),
            "p95": float(np.quantile(finite, 0.95)),
            "threshold": float(per_pair_threshold.get(str(pair), float("nan"))),
        }

    return {
        "stage1": stage1,
        "stage2": stage2,
        "per_pair_threshold": per_pair_threshold,
        "val_score": val_score_final,
        "test_score": test_score_final,
        "n_admitted_train": n_admitted_train,
        "admitted_train_per_pair": admitted_train_per_pair,
        "stage1_score_val_distribution": stage1_dist,
        "val_admit_mask": val_admit_mask,
        "test_admit_mask": test_admit_mask,
    }


# ---------------------------------------------------------------------------
# AR2 — Pair-conditioned specialist heads (PR #344 §4.2)
# ---------------------------------------------------------------------------


def fit_ar2_pair_specialists(
    x_train_r7a: pd.DataFrame,
    pnl_train_for_reg: np.ndarray,
    train_pair_clean: np.ndarray,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pairs: list[str],
) -> dict:
    """Fit AR2 pair-conditioned specialist heads (PR #344 §4.2).

    20 per-pair LightGBMRegressors with 27.0d S-E backbone verbatim.
    NO per-pair hyperparameter tuning (NG#A0-1).

    No-fallback (NG#A0-1): if any pair has < AR2_PER_PAIR_MIN_TRAIN_ROWS_HALT
    train rows, raise ArchitectureFitError.
    """
    train_pair_arr = np.asarray(train_pair_clean)
    train_rows_per_pair: dict[str, int] = {}
    for pair in pairs:
        train_rows_per_pair[pair] = int((train_pair_arr == pair).sum())
    insufficient_pairs = [
        (p, n) for p, n in train_rows_per_pair.items() if n < AR2_PER_PAIR_MIN_TRAIN_ROWS_HALT
    ]
    if insufficient_pairs:
        raise ArchitectureFitError(
            f"AR2 per-pair train shortage (NG#A0-1; no-fallback HALT): "
            f"{len(insufficient_pairs)} pair(s) with < "
            f"{AR2_PER_PAIR_MIN_TRAIN_ROWS_HALT} train rows: "
            f"{insufficient_pairs[:5]}"
        )

    specialists: dict[str, object] = {}
    for pair in pairs:
        pair_mask = train_pair_arr == pair
        x_pair = x_train_r7a.loc[pair_mask].reset_index(drop=True)
        y_pair = pnl_train_for_reg[pair_mask]
        regressor = build_pipeline_lightgbm_regression_widened()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            regressor.fit(x_pair, y_pair)
        specialists[pair] = regressor

    def _route_predict(df: pd.DataFrame) -> np.ndarray:
        pair_arr = df["pair"].to_numpy()
        scores = np.full(len(df), float("nan"), dtype=np.float64)
        x_full = df[list(ALL_FEATURES_R7A)].reset_index(drop=True)
        for pair, regressor in specialists.items():
            mask = pair_arr == pair
            if mask.sum() == 0:
                continue
            x_subset = x_full.loc[mask].reset_index(drop=True)
            pred = compute_picker_score_s_e(regressor, x_subset)
            scores[mask] = pred
        return scores

    val_score = _route_predict(val_df)
    test_score = _route_predict(test_df)

    return {
        "specialists": specialists,
        "val_score": val_score,
        "test_score": test_score,
        "train_rows_per_pair": train_rows_per_pair,
    }


# ---------------------------------------------------------------------------
# AR3 — Stacked classifier+regressor blend (PR #344 §4.3)
# ---------------------------------------------------------------------------


def compute_ar3_blended_score(s_b_raw: np.ndarray, s_e: np.ndarray) -> np.ndarray:
    """AR3 stacked blend: 0.5*rank_norm(S-B raw) + 0.5*rank_norm(S-E).

    Per PR #344 §4.3 / D-BC4: fixed 0.5/0.5 blend; rank_normalise via
    pandas pct=True method='average'; no β-time grid sweep (NG#A0-1).
    """
    rn_s_b = _rank_normalise(s_b_raw)
    rn_s_e = _rank_normalise(s_e)
    return AR3_BLEND_W_SB * rn_s_b + AR3_BLEND_W_SE * rn_s_e


# ---------------------------------------------------------------------------
# AR4 — Deterministic regime split (PR #344 §4.4)
# ---------------------------------------------------------------------------


def fit_ar4_regime_split(
    x_train_r7a: pd.DataFrame,
    pnl_train_for_reg: np.ndarray,
    train_pair_clean: np.ndarray,
    train_df_for_reg: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
) -> dict:
    """Fit AR4 deterministic regime split architecture (PR #344 §4.4).

    Per-pair val-median atr_at_signal_pip → regime threshold.
    High-vol regime: train rows where atr > threshold (per pair).
    Low-vol regime: train rows where atr <= threshold (per pair).
    2 LightGBMRegressors fit on respective row sets.
    Inference: route each val/test row by its pair's threshold.

    Interpretation guard (PR #344 §3.2 caveat): deterministic regime
    split; NOT learned gating / MoE / adaptive weights. A3 elevation
    requires separate scope amendment.

    No HALT for regime imbalance; WARN-only.
    """
    val_pair_arr = val_df["pair"].to_numpy()
    val_atr = val_df[AR4_REGIME_SPLIT_FEATURE].to_numpy(dtype=np.float64)
    regime_threshold_per_pair = _compute_per_pair_median(
        val_pair_arr, val_atr, percentile=AR4_REGIME_SPLIT_PERCENTILE
    )

    train_pair_arr = np.asarray(train_pair_clean)
    train_atr = train_df_for_reg[AR4_REGIME_SPLIT_FEATURE].to_numpy(dtype=np.float64)
    train_thresholds = np.array(
        [regime_threshold_per_pair.get(str(p), float("inf")) for p in train_pair_arr],
        dtype=np.float64,
    )
    high_mask_train = (
        np.isfinite(train_atr) & np.isfinite(train_thresholds) & (train_atr > train_thresholds)
    )
    low_mask_train = np.isfinite(train_atr) & np.isfinite(train_thresholds) & ~high_mask_train

    regime_balance: dict[str, dict] = {}
    imbalance_warn_pairs: list[str] = []
    for pair in sorted(set(train_pair_arr.tolist())):
        pair_mask = train_pair_arr == pair
        n_pair = int(pair_mask.sum())
        n_high = int((pair_mask & high_mask_train).sum())
        n_low = int((pair_mask & low_mask_train).sum())
        high_frac = n_high / max(n_pair, 1)
        low_frac = n_low / max(n_pair, 1)
        regime_balance[str(pair)] = {
            "n_pair": n_pair,
            "n_high": n_high,
            "n_low": n_low,
            "high_frac": high_frac,
            "low_frac": low_frac,
        }
        if (
            high_frac < AR4_REGIME_IMBALANCE_WARN_FRACTION
            or low_frac < AR4_REGIME_IMBALANCE_WARN_FRACTION
        ):
            imbalance_warn_pairs.append(str(pair))

    if imbalance_warn_pairs:
        warnings.warn(
            f"AR4 regime imbalance WARN (DIAGNOSTIC-ONLY; no-fallback per "
            f"NG#A0-1): {len(imbalance_warn_pairs)} pair(s) have < "
            f"{AR4_REGIME_IMBALANCE_WARN_FRACTION:.0%} in one regime: "
            f"{imbalance_warn_pairs[:5]}",
            UserWarning,
            stacklevel=2,
        )

    x_high = x_train_r7a.loc[high_mask_train].reset_index(drop=True)
    y_high = pnl_train_for_reg[high_mask_train]
    high_vol_regressor = build_pipeline_lightgbm_regression_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        high_vol_regressor.fit(x_high, y_high)

    x_low = x_train_r7a.loc[low_mask_train].reset_index(drop=True)
    y_low = pnl_train_for_reg[low_mask_train]
    low_vol_regressor = build_pipeline_lightgbm_regression_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        low_vol_regressor.fit(x_low, y_low)

    def _route_predict(df: pd.DataFrame) -> np.ndarray:
        pair_arr = df["pair"].to_numpy()
        atr_arr = df[AR4_REGIME_SPLIT_FEATURE].to_numpy(dtype=np.float64)
        thresholds = np.array(
            [regime_threshold_per_pair.get(str(p), float("inf")) for p in pair_arr],
            dtype=np.float64,
        )
        high_mask = np.isfinite(atr_arr) & np.isfinite(thresholds) & (atr_arr > thresholds)
        low_mask = np.isfinite(atr_arr) & np.isfinite(thresholds) & ~high_mask
        scores = np.full(len(df), float("nan"), dtype=np.float64)
        x_full = df[list(ALL_FEATURES_R7A)].reset_index(drop=True)
        if high_mask.sum() > 0:
            x_h = x_full.loc[high_mask].reset_index(drop=True)
            scores[high_mask] = compute_picker_score_s_e(high_vol_regressor, x_h)
        if low_mask.sum() > 0:
            x_l = x_full.loc[low_mask].reset_index(drop=True)
            scores[low_mask] = compute_picker_score_s_e(low_vol_regressor, x_l)
        return scores

    val_score = _route_predict(val_df)
    test_score = _route_predict(test_df)

    return {
        "regime_threshold_per_pair": regime_threshold_per_pair,
        "high_vol_regressor": high_vol_regressor,
        "low_vol_regressor": low_vol_regressor,
        "val_score": val_score,
        "test_score": test_score,
        "regime_balance": regime_balance,
        "imbalance_warn_pairs": imbalance_warn_pairs,
        "high_train_rows": int(high_mask_train.sum()),
        "low_train_rows": int(low_mask_train.sum()),
    }


# ---------------------------------------------------------------------------
# Cell construction (PR #344 §9; 6 cells)
# ---------------------------------------------------------------------------


def build_a0_cells() -> list[dict]:
    """28.0c-β formal grid: 6 cells per PR #344 §9.

    NG#A0-3 mandates C-a0-arch-control. Deterministic order:
    AR1 → AR2 → AR3 → AR4 → arch-control → baseline.
    """
    return [
        {
            "id": "C-a0-AR1",
            "picker": "AR1(stage1_S-B → admit50%-per-pair-val-median → stage2_S-E)",
            "score_type": "ar1_hierarchical",
            "feature_set": "r7a",
            "architecture": "hierarchical_two_stage",
            "quantile_percents": QUANTILE_PERCENTS_28_0C,
        },
        {
            "id": "C-a0-AR2",
            "picker": "AR2(20 per-pair S-E specialists; 27.0d backbone verbatim)",
            "score_type": "ar2_pair_specialist",
            "feature_set": "r7a",
            "architecture": "pair_conditioned_specialist_heads",
            "quantile_percents": QUANTILE_PERCENTS_28_0C,
        },
        {
            "id": "C-a0-AR3",
            "picker": "AR3(0.5·rank(S-B raw) + 0.5·rank(S-E))",
            "score_type": "ar3_stacked_blend",
            "feature_set": "r7a",
            "architecture": "stacked_classifier_regressor_blend",
            "quantile_percents": QUANTILE_PERCENTS_28_0C,
        },
        {
            "id": "C-a0-AR4",
            "picker": "AR4(deterministic regime split: per-pair val-median atr)",
            "score_type": "ar4_regime_split",
            "feature_set": "r7a",
            "architecture": "deterministic_regime_split",
            "quantile_percents": QUANTILE_PERCENTS_28_0C,
        },
        {
            "id": "C-a0-arch-control",
            "picker": "S-E(vanilla regressor; sample_weight=1; arch-axis null)",
            "score_type": "arch_control",
            "feature_set": "r7a",
            "architecture": "vanilla_s_e_27_0d_backbone",
            "quantile_percents": QUANTILE_PERCENTS_28_0C,
        },
        {
            "id": "C-sb-baseline",
            "picker": "S-B(raw_p_tp_minus_p_sl)",
            "score_type": "s_b_raw",
            "feature_set": "r7a",
            "architecture": "multiclass_s_b_baseline",
            "quantile_percents": QUANTILE_PERCENTS_28_0C,
        },
    ]


# ---------------------------------------------------------------------------
# C-sb-baseline mismatch check (FAIL-FAST; inherited)
# ---------------------------------------------------------------------------


def check_c_sb_baseline_match(c_sb_baseline_result: dict) -> dict:
    """Validate C-sb-baseline reproduces 27.0b C-alpha0 baseline.

    Per PR #344 §10 inheritance from 27.0c-α §7.3. FAIL-FAST HALT.
    """
    rm = c_sb_baseline_result.get("test_realised_metrics", {})
    n_trades = int(rm.get("n_trades", 0))
    sharpe = float(rm.get("sharpe", float("nan")))
    ann_pnl = float(rm.get("annual_pnl", float("nan")))

    n_trades_delta = n_trades - BASELINE_27_0B_C_ALPHA0_N_TRADES
    sharpe_delta = sharpe - BASELINE_27_0B_C_ALPHA0_SHARPE if np.isfinite(sharpe) else float("nan")
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
        failures: list[str] = []
        if not n_trades_match:
            failures.append(
                f"n_trades: observed={n_trades} baseline={BASELINE_27_0B_C_ALPHA0_N_TRADES} "
                f"delta={n_trades_delta} (tolerance ±{BASELINE_MATCH_N_TRADES_TOLERANCE})"
            )
        if not sharpe_match:
            failures.append(
                f"Sharpe: observed={sharpe:.6f} baseline={BASELINE_27_0B_C_ALPHA0_SHARPE:.6f} "
                f"delta={sharpe_delta:+.6f} (tolerance ±{BASELINE_MATCH_SHARPE_ABS_TOLERANCE})"
            )
        if not ann_pnl_match:
            failures.append(
                f"ann_pnl: observed={ann_pnl:+.3f} "
                f"baseline={BASELINE_27_0B_C_ALPHA0_ANN_PNL:+.3f} "
                f"delta={ann_pnl_delta:+.3f} (tolerance ±{BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE})"
            )
        raise BaselineMismatchError(
            "C-sb-baseline failed to reproduce 27.0b C-alpha0 baseline per "
            "PR #344 §10; failures: " + "; ".join(failures)
        )
    return report


# ---------------------------------------------------------------------------
# C-a0-arch-control drift check vs 27.0d C-se (DIAGNOSTIC-ONLY WARN)
# ---------------------------------------------------------------------------


def compute_c_a0_arch_control_drift_check(c_a0_arch_control_result: dict) -> dict:
    """DIAGNOSTIC-ONLY WARN; NOT HALT.

    Per PR #344 §11: C-a0-arch-control reproduces 27.0d C-se with
    sample_weight=1 (5th bit-tight reproduction in the inheritance chain:
    27.0d → 27.0f r7a-replica → 28.0a r7a-replica → 28.0b top-q-control →
    28.0c arch-control).
    """
    rm = c_a0_arch_control_result.get("test_realised_metrics", {})
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
# Within-eval drift check per AR (PARTIAL_DRIFT_ARCH_REPLICA detection)
# ---------------------------------------------------------------------------


def compute_within_eval_arch_drift_check(
    c_a0_arx_result: dict,
    c_a0_arch_control_result: dict,
) -> dict:
    """Compare an AR cell vs C-a0-arch-control at val-selected configuration.

    Per PR #344 §12.3 row 4 + NG#A0-3: if C-a0-ARx ≈ C-a0-arch-control
    within tolerance, flag PARTIAL_DRIFT_ARCH_REPLICA. Architecture
    change had zero effect on monetization.
    """
    if c_a0_arx_result.get("h_state") != "OK" or c_a0_arch_control_result.get("h_state") != "OK":
        return {
            "all_within_tolerance": False,
            "warn": True,
            "note": "AR cell or arch-control h_state != OK",
        }
    rm_ar = c_a0_arx_result.get("test_realised_metrics", {})
    rm_ctl = c_a0_arch_control_result.get("test_realised_metrics", {})
    n_ar = int(rm_ar.get("n_trades", 0))
    n_ctl = int(rm_ctl.get("n_trades", 0))
    sh_ar = float(rm_ar.get("sharpe", float("nan")))
    sh_ctl = float(rm_ctl.get("sharpe", float("nan")))
    ap_ar = float(rm_ar.get("annual_pnl", float("nan")))
    ap_ctl = float(rm_ctl.get("annual_pnl", float("nan")))

    n_trades_delta = n_ar - n_ctl
    sharpe_delta = sh_ar - sh_ctl if (np.isfinite(sh_ar) and np.isfinite(sh_ctl)) else float("nan")
    ann_pnl_delta = ap_ar - ap_ctl if (np.isfinite(ap_ar) and np.isfinite(ap_ctl)) else float("nan")

    ann_pnl_tolerance_abs = (
        abs(ap_ctl) * WITHIN_EVAL_DRIFT_ANN_PNL_FRAC_TOLERANCE if np.isfinite(ap_ctl) else None
    )

    n_trades_within = abs(n_trades_delta) <= WITHIN_EVAL_DRIFT_N_TRADES_TOLERANCE
    sharpe_within = (
        np.isfinite(sharpe_delta) and abs(sharpe_delta) <= WITHIN_EVAL_DRIFT_SHARPE_TOLERANCE
    )
    ann_pnl_within = (
        np.isfinite(ann_pnl_delta)
        and ann_pnl_tolerance_abs is not None
        and abs(ann_pnl_delta) <= ann_pnl_tolerance_abs
    )
    all_within = bool(n_trades_within and sharpe_within and ann_pnl_within)
    return {
        "n_trades_candidate": int(n_ar),
        "n_trades_control": int(n_ctl),
        "n_trades_delta": int(n_trades_delta),
        "n_trades_within_tolerance": bool(n_trades_within),
        "sharpe_candidate": float(sh_ar),
        "sharpe_control": float(sh_ctl),
        "sharpe_delta": float(sharpe_delta) if np.isfinite(sharpe_delta) else float("nan"),
        "sharpe_within_tolerance": bool(sharpe_within),
        "ann_pnl_candidate": float(ap_ar),
        "ann_pnl_control": float(ap_ctl),
        "ann_pnl_delta": float(ann_pnl_delta) if np.isfinite(ann_pnl_delta) else float("nan"),
        "ann_pnl_tolerance_abs": ann_pnl_tolerance_abs,
        "ann_pnl_within_tolerance": bool(ann_pnl_within),
        "all_within_tolerance": all_within,
        "warn": all_within,
    }


# ---------------------------------------------------------------------------
# H-C3 4-outcome ladder resolver per AR (PR #344 §12.3; precedence row 4 > 1 > 2 > 3)
# ---------------------------------------------------------------------------


def compute_h_c3_outcome_per_arch(
    c_a0_arx_result: dict,
    baseline_match_report: dict,
    arch_drift_report_vs_control: dict,
    arch_id: str,
) -> dict:
    """Resolve 1 of 4 H-C3 outcomes per AR (precedence row 4 > 1 > 2 > 3).

    PARTIAL_DRIFT_ARCH_REPLICA checked first per NG#A0-3.

    Interpretation guards embedded in reason strings:
      AR1 PASS/PARTIAL: "architecture-topology with embedded admission gate"
      AR4 PASS/PARTIAL: "deterministic tabular regime split helped"
    """
    cell_id = c_a0_arx_result.get("cell", {}).get("id", "unknown")
    if c_a0_arx_result.get("h_state") != "OK":
        return {
            "cell_id": cell_id,
            "arch_id": arch_id,
            "outcome": H_C3_OUTCOME_NEEDS_REVIEW,
            "row_matched": 0,
            "reason": f"h_state={c_a0_arx_result.get('h_state')}",
        }

    drift_within = arch_drift_report_vs_control.get("all_within_tolerance", False)
    if drift_within:
        return {
            "cell_id": cell_id,
            "arch_id": arch_id,
            "outcome": H_C3_OUTCOME_PARTIAL_DRIFT_ARCH_REPLICA,
            "row_matched": 4,
            "reason": (
                f"{arch_id} architecture had zero effect on monetization (drift vs "
                "C-a0-arch-control within tolerance); analogous to 27.0f H-B6 / "
                "28.0a H-C1 row 4 / 28.0b H-C2 row 4"
            ),
            "evidence": {
                "drift_n_trades_delta": arch_drift_report_vs_control.get("n_trades_delta"),
                "drift_sharpe_delta": arch_drift_report_vs_control.get("sharpe_delta"),
                "drift_ann_pnl_delta": arch_drift_report_vs_control.get("ann_pnl_delta"),
            },
        }

    val_sharpe = float(c_a0_arx_result.get("val_realised_sharpe", float("nan")))
    val_n = int(c_a0_arx_result.get("val_n_trades", 0))
    qb = c_a0_arx_result.get("quantile_best", {}) or {}
    cell_spearman_val = qb.get("val", {}).get("spearman_score_vs_pnl", float("nan"))
    if not np.isfinite(cell_spearman_val):
        cell_spearman_val = float(c_a0_arx_result.get("val_cell_spearman", float("nan")))
    if not np.isfinite(cell_spearman_val):
        cell_spearman_val = float(c_a0_arx_result.get("test_formal_spearman", float("nan")))

    sharpe_lift = (
        float(val_sharpe - SECTION_10_BASELINE_VAL_SHARPE)
        if np.isfinite(val_sharpe)
        else float("nan")
    )

    baseline_pass = bool(baseline_match_report.get("all_match", False))
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
        "baseline_pass": bool(baseline_pass),
    }

    interp_guard = _interpretation_guard_for_arch(arch_id, outcome_row=1)

    if h1m_pass and h2_pass and h3_pass and baseline_pass:
        return {
            "cell_id": cell_id,
            "arch_id": arch_id,
            "outcome": H_C3_OUTCOME_PASS,
            "row_matched": 1,
            "reason": f"all four H-C3 conditions satisfied; {interp_guard}",
            "evidence": evidence,
        }

    h2_partial = (
        np.isfinite(sharpe_lift)
        and H2_LIFT_THRESHOLD_PARTIAL_SUPPORT_LO <= sharpe_lift < H2_LIFT_THRESHOLD_PASS
    )
    interp_guard_partial = _interpretation_guard_for_arch(arch_id, outcome_row=2)
    if h2_partial and h1m_pass and h3_pass and baseline_pass:
        return {
            "cell_id": cell_id,
            "arch_id": arch_id,
            "outcome": H_C3_OUTCOME_PARTIAL_SUPPORT,
            "row_matched": 2,
            "reason": (
                f"val Sharpe lift {sharpe_lift:+.4f} in [+0.02, +0.05); other H-C3 "
                f"conditions intact; {interp_guard_partial}"
            ),
            "evidence": evidence,
        }

    return {
        "cell_id": cell_id,
        "arch_id": arch_id,
        "outcome": H_C3_OUTCOME_FALSIFIED_ARCH_INSUFFICIENT,
        "row_matched": 3,
        "reason": (f"val Sharpe lift {sharpe_lift:+.4f} < +0.02 OR other H-C3 conditions failed"),
        "evidence": evidence,
    }


def _interpretation_guard_for_arch(arch_id: str, outcome_row: int) -> str:
    """Return interpretation guard string for AR1 / AR4 PASS/PARTIAL outcomes.

    Per PR #344 §3 §4 §12 and user-pre-stated guards at β kickoff:
      AR1: stage-1 admission threshold is architecture-conditioning, NOT
        final selection rule. PASS/PARTIAL is "architecture-topology with
        embedded admission gate", not "pure architecture-only success".
      AR4: deterministic regime split. PASS/PARTIAL is "deterministic
        tabular regime split helped", NOT "full A3 regime-conditioned
        modeling is solved". A3 elevation requires separate scope
        amendment.
    """
    if arch_id == "AR1":
        return (
            "INTERPRETATION GUARD: architecture-topology with embedded admission "
            "gate (stage-1 threshold resembles 28.0b R1 selection-like behavior; "
            "admitted under A0-narrow as architecture-conditioning of stage 2's "
            "training set, NOT final selection rule). NOT pure architecture-only "
            "success."
        )
    if arch_id == "AR4":
        return (
            "INTERPRETATION GUARD: deterministic tabular regime split helped "
            "(deterministic routing only; NO learned gating / MoE / adaptive "
            "weights). Full A3 regime-conditioned modeling is NOT solved by "
            "this result; A3 elevation requires separate scope amendment."
        )
    return "no architecture-specific interpretation guard"


def compute_h_c3_aggregate_verdict(per_arch_outcomes: list[dict]) -> dict:
    """Aggregate H-C3 verdict per PR #344 §12.4.

    All-fail case explicitly labeled FALSIFIED_A0_NARROW, NEVER
    FALSIFIED_ALL_A0. A0-broad sequence/NN remains deferred-not-foreclosed.
    """
    outcomes = [o.get("outcome") for o in per_arch_outcomes]
    has_pass = H_C3_OUTCOME_PASS in outcomes
    has_partial_support = H_C3_OUTCOME_PARTIAL_SUPPORT in outcomes
    all_partial_drift = len(outcomes) > 0 and all(
        o == H_C3_OUTCOME_PARTIAL_DRIFT_ARCH_REPLICA for o in outcomes
    )
    all_falsified = len(outcomes) > 0 and all(
        o
        in {
            H_C3_OUTCOME_FALSIFIED_ARCH_INSUFFICIENT,
            H_C3_OUTCOME_PARTIAL_DRIFT_ARCH_REPLICA,
        }
        for o in outcomes
    )

    if has_pass:
        verdict = "SPLIT_VERDICT_ROUTE_TO_REVIEW"
        routing = (
            "1+ AR variant produced H-C3 PASS at the C-a0-ARx cell; "
            "PROMISING_BUT_NEEDS_OOS candidate. ADOPT_CANDIDATE wall preserved "
            "per Clause 1. Interpretation guards apply: AR1 PASS = "
            "architecture-topology with embedded admission gate (NOT pure "
            "architecture); AR4 PASS = deterministic tabular regime split "
            "helped (NOT full A3 solved)."
        )
        a0_narrow_status = "PASS_under_A0_narrow"
    elif has_partial_support:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        routing = (
            "1+ AR variant PARTIAL_SUPPORT (sub-threshold Sharpe lift); no AR "
            "PASS. Route to post-28.0c routing review for Path B (A0-broad "
            "sequence/NN scope amendment) vs Phase 28 closure / Phase 29 "
            "rebase comparison."
        )
        a0_narrow_status = "PARTIAL_under_A0_narrow"
    elif all_partial_drift:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        routing = (
            "All 4 AR variants PARTIAL_DRIFT_ARCH_REPLICA — architecture "
            "change does not move the score regardless of topology. Strong "
            "FALSIFIED_A0_NARROW signal; A0-broad sequence/NN remains "
            "deferred-not-foreclosed (PR #344 §7.2 / §12.2). Post-28.0c "
            "routing review MUST compare Path B vs Phase 28 closure / Phase "
            "29 rebase. NEVER label this FALSIFIED_ALL_A0."
        )
        a0_narrow_status = "FALSIFIED_A0_NARROW"
    elif all_falsified:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        routing = (
            "All 4 AR variants FALSIFIED_ARCH_INSUFFICIENT or "
            "PARTIAL_DRIFT_ARCH_REPLICA — A0-narrow tabular topology axis "
            "exhausted. Result is FALSIFIED_A0_NARROW (NEVER "
            "FALSIFIED_ALL_A0). A0-broad sequence/NN remains "
            "deferred-not-foreclosed (PR #344 §7.2 / §12.2). Post-28.0c "
            "routing review MUST compare Path B (A0-broad scope amendment) "
            "vs Phase 28 closure / Phase 29 rebase."
        )
        a0_narrow_status = "FALSIFIED_A0_NARROW"
    else:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        routing = (
            "no AR variant produced PASS or PARTIAL_SUPPORT; route to "
            "post-28.0c routing review. A0-broad deferred-not-foreclosed."
        )
        a0_narrow_status = "INCONCLUSIVE_under_A0_narrow"

    return {
        "aggregate_verdict": verdict,
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
        "has_partial_support": bool(has_partial_support),
        "all_partial_drift": bool(all_partial_drift),
        "a0_narrow_status": a0_narrow_status,
        "a0_broad_status": "deferred_not_foreclosed",
    }


# ---------------------------------------------------------------------------
# Top-tail regime audit (DIAGNOSTIC-ONLY; spread_at_signal_pip only)
# ---------------------------------------------------------------------------


def compute_top_tail_regime_audit_for_a0(
    val_score: np.ndarray,
    val_features: pd.DataFrame,
    q_list: tuple[float, ...] = TOP_TAIL_AUDIT_Q_PERCENTS,
) -> dict:
    """DIAGNOSTIC-ONLY; top-tail audit on val using spread_at_signal_pip.

    R7-C features NOT computed (out of scope per Clause 6).
    """
    out: dict = {"per_q": [], "population": {}}
    spread = val_features["spread_at_signal_pip"].astype(np.float64).to_numpy()
    finite_spread = spread[np.isfinite(spread)]
    pop_mean_spread = float(finite_spread.mean()) if len(finite_spread) > 0 else float("nan")
    pop_p50_spread = (
        float(np.quantile(finite_spread, 0.5)) if len(finite_spread) > 0 else float("nan")
    )
    out["population"] = {
        "n_finite_spread": int(len(finite_spread)),
        "mean_spread_at_signal_pip": pop_mean_spread,
        "p50_spread_at_signal_pip": pop_p50_spread,
    }

    for q_pct in q_list:
        cutoff = fit_quantile_cutoff_on_val(val_score, q_pct)
        top_mask = np.isfinite(val_score) & (val_score >= cutoff)
        n_top = int(top_mask.sum())
        top_spread = spread[top_mask]
        top_finite = top_spread[np.isfinite(top_spread)]
        if len(top_finite) > 0:
            top_mean = float(top_finite.mean())
            top_p50 = float(np.quantile(top_finite, 0.5))
        else:
            top_mean = float("nan")
            top_p50 = float("nan")
        out["per_q"].append(
            {
                "q_percent": float(q_pct),
                "cutoff": float(cutoff),
                "n_top": n_top,
                "top_mean_spread": top_mean,
                "top_p50_spread": top_p50,
                "delta_mean_vs_population": (
                    top_mean - pop_mean_spread
                    if np.isfinite(top_mean) and np.isfinite(pop_mean_spread)
                    else float("nan")
                ),
            }
        )
    return out


# ---------------------------------------------------------------------------
# Per-cell quantile evaluation (inherited shape from 28.0b)
# ---------------------------------------------------------------------------


def evaluate_quantile_cell_28_0c(
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
    pnl_val_full: np.ndarray,
    pnl_test_full: np.ndarray,
    feature_importance_diag: dict,
) -> dict:
    """Evaluate a quantile cell — inherited from 28.0b shape."""
    score_type = str(cell.get("score_type", "unknown"))

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

    quantile_percents = tuple(cell.get("quantile_percents", QUANTILE_PERCENTS_28_0C))
    quantile_results = evaluate_quantile_family_custom(
        val_score,
        pnl_val_full,
        test_score,
        pnl_test_full,
        VAL_SPAN_YEARS,
        TEST_SPAN_YEARS,
        quantile_percents=quantile_percents,
    )

    def _q_sort_key(r: dict) -> tuple:
        v = r["val"]
        s = v["sharpe"] if np.isfinite(v["sharpe"]) else -np.inf
        return (s, v["annual_pnl"], v["n_trades"], -r["q_percent"])

    best_q_record = max(quantile_results, key=_q_sort_key)
    test_realised = best_q_record["test"]["realised_pnls"]
    gate_block = compute_8_gate_from_pnls(test_realised)

    cls_diag = compute_classification_diagnostics(
        test_label, test_raw_probs, test_score, pnl_test_full
    )
    formal_spearman = cls_diag.get("spearman_score_vs_pnl", float("nan"))

    test_df_aligned = test_df.reset_index(drop=True)
    val_df_aligned = val_df.reset_index(drop=True)
    traded_mask_test = np.isfinite(test_score) & (test_score >= best_q_record["cutoff"])
    valid_pnl_mask_test = np.isfinite(pnl_test_full)
    in_trade = traded_mask_test & valid_pnl_mask_test
    by_pair: dict[str, int] = {}
    by_direction: dict[str, int] = {"long": 0, "short": 0}
    for i in np.flatnonzero(in_trade):
        p = str(test_df_aligned["pair"].iloc[i])
        d = str(test_df_aligned["direction"].iloc[i])
        by_pair[p] = by_pair.get(p, 0) + 1
        by_direction[d] = by_direction.get(d, 0) + 1

    valid_pnl_mask_val = np.isfinite(pnl_val_full)
    traded_mask_val = np.isfinite(val_score) & (val_score >= best_q_record["cutoff"])
    val_concentration = compute_pair_concentration(
        val_df_aligned, traded_mask_val, valid_pnl_mask_val
    )
    test_concentration = compute_pair_concentration(
        test_df_aligned, traded_mask_test, valid_pnl_mask_test
    )
    per_pair_sharpe = compute_per_pair_sharpe_contribution(
        test_df_aligned, traded_mask_test, pnl_test_full
    )
    low_power = n_test < LOW_POWER_N_TEST or n_train < LOW_POWER_N_TRAIN

    # Cell-level Spearman on val (over traded rows)
    if int(traded_mask_val.sum()) >= 2:
        from scipy.stats import spearmanr

        val_traded_pnl = pnl_val_full[traded_mask_val & valid_pnl_mask_val]
        val_traded_score = val_score[traded_mask_val & valid_pnl_mask_val]
        sp_val_result = spearmanr(val_traded_score, val_traded_pnl, nan_policy="omit")
        val_cell_spearman = (
            float(sp_val_result.correlation)
            if hasattr(sp_val_result, "correlation")
            else float(sp_val_result.statistic)
        )
        if not np.isfinite(val_cell_spearman):
            val_cell_spearman = float("nan")
    else:
        val_cell_spearman = float("nan")

    return {
        "cell": cell,
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


def _cell_signature(cell: dict) -> str:
    keys = ("id", "picker", "score_type", "feature_set", "architecture")
    return " ".join(f"{k}={cell.get(k)}" for k in keys)


# ---------------------------------------------------------------------------
# Per-pair runtime (inherited from 28.0b)
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


# ---------------------------------------------------------------------------
# Sanity probe (items 1-6 inherited; items 7-10 NEW for 4 AR variants)
# ---------------------------------------------------------------------------


def run_sanity_probe_28_0c(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    pairs: list[str],
    days: int = SPAN_DAYS,
    pnl_train_full: np.ndarray | None = None,
    ar1_info: dict | None = None,
    ar2_info: dict | None = None,
    ar3_blend_summary: dict | None = None,
    ar4_info: dict | None = None,
    val_pred_s_e: np.ndarray | None = None,
    test_pred_s_e: np.ndarray | None = None,
    train_pred_s_e: np.ndarray | None = None,
    fold_idx: np.ndarray | None = None,
    oof_corr_diag_s_e: dict | None = None,
    train_reg_diag_s_e: dict | None = None,
    val_reg_diag_s_e: dict | None = None,
    test_reg_diag_s_e: dict | None = None,
    feature_importance_s_e: dict | None = None,
    train_drop_for_nan_pnl_count: int | None = None,
    top_tail_regime_audit_per_arch: dict[str, dict] | None = None,
    cell_definitions: list[dict] | None = None,
) -> dict:
    """28.0c-β SanityProbe (items 1-6 inherited; items 7-10 NEW for AR variants)."""
    print("\n=== 28.0c-β SANITY PROBE (per PR #344 §14 §15.4) ===")
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
    out["per_pair_time_share"] = {}
    over_99_pairs: list[tuple[str, float]] = []
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
            over_99_pairs.append((pair, share))
    print(
        f"  per-pair TIME-share check: {len(over_99_pairs)} pair(s) over "
        f"{SANITY_MAX_PER_PAIR_TIME_SHARE:.0%}"
    )

    # Item 3: D-1 binding check
    print("  realised-PnL cache basis check (per D-1 binding):")
    pnl_cache_sig = inspect.signature(precompute_realised_pnl_per_row)
    if "spread_factor" in pnl_cache_sig.parameters or "mid_to_mid" in pnl_cache_sig.parameters:
        raise SanityProbeError(
            "precompute_realised_pnl_per_row signature exposes spread_factor / mid_to_mid"
        )
    barrier_pnl_src = inspect.getsource(_compute_realised_barrier_pnl)
    if not all(tok in barrier_pnl_src for tok in ["bid_h", "ask_l", "ask_h", "bid_l"]):
        raise SanityProbeError(
            "_compute_realised_barrier_pnl does not reference bid_h/ask_l/ask_h/bid_l"
        )
    out["d1_binding_check"] = "PASS"
    print("    OK: bid/ask executable treatment confirmed")

    # Item 4: realised-PnL distribution per class on train (DIAGNOSTIC)
    if pnl_train_full is not None:
        mid_train = np.asarray(pnl_train_full, dtype=np.float64)
        out["target_pnl_distribution_train"] = {}
        print("  realised-PnL distribution per class on TRAIN (diagnostic):")
        label_names = [(LABEL_TP, "TP"), (LABEL_SL, "SL"), (LABEL_TIME, "TIME")]
        for cls, name in label_names:
            mask = (train_label == cls) & np.isfinite(mid_train)
            if mask.sum() == 0:
                continue
            data = mid_train[mask]
            stats = {
                "n": int(mask.sum()),
                "mean": float(data.mean()),
                "p5": float(np.quantile(data, 0.05)),
                "p50": float(np.quantile(data, 0.5)),
                "p95": float(np.quantile(data, 0.95)),
            }
            out["target_pnl_distribution_train"][name] = stats

    # Item 5: R7-A NaN-rate check
    print("  R7-A new-feature NaN-rate check:")
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
    print("  R7-A positivity check on TRAIN:")
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

    # NaN-PnL HALT
    if train_drop_for_nan_pnl_count is not None and pnl_train_full is not None:
        n_train_for_threshold = len(pnl_train_full)
        threshold = NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD * n_train_for_threshold
        if train_drop_for_nan_pnl_count > threshold:
            raise SanityProbeError(
                f"train rows with NaN PnL = {train_drop_for_nan_pnl_count} > "
                f"{NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD:.1%} of n_train"
            )

    # Item 7 NEW: AR1 stage-1 threshold distribution per pair
    if ar1_info is not None:
        ppt = ar1_info.get("per_pair_threshold", {})
        atpp = ar1_info.get("admitted_train_per_pair", {})
        out["ar1_per_pair_threshold"] = {p: float(v) for p, v in ppt.items()}
        out["ar1_admitted_train_per_pair"] = {p: int(v) for p, v in atpp.items()}
        out["ar1_stage1_score_val_distribution"] = ar1_info.get("stage1_score_val_distribution", {})
        out["ar1_n_admitted_train"] = int(ar1_info.get("n_admitted_train", 0))
        missing = [p for p in pairs if p not in ppt]
        if missing:
            raise SanityProbeError(
                f"AR1 per_pair_threshold missing pairs: {missing[:5]} (NG#A0-1; expected 20)"
            )
        non_finite = [p for p, v in ppt.items() if not np.isfinite(v)]
        if non_finite:
            raise SanityProbeError(f"AR1 per_pair_threshold non-finite for pairs: {non_finite[:5]}")
        admit_counts = np.array(list(atpp.values()), dtype=np.float64)
        print(
            f"  AR1 admitted-train per pair: n_pairs={len(admit_counts)} "
            f"mean={admit_counts.mean():.0f} p5={np.quantile(admit_counts, 0.05):.0f} "
            f"p95={np.quantile(admit_counts, 0.95):.0f} total={int(admit_counts.sum())}"
        )

    # Item 8 NEW: AR2 per-pair training row count
    if ar2_info is not None:
        trpp = ar2_info.get("train_rows_per_pair", {})
        out["ar2_train_rows_per_pair"] = {p: int(v) for p, v in trpp.items()}
        rows = np.array(list(trpp.values()), dtype=np.float64)
        print(
            f"  AR2 train rows per pair: n_pairs={len(rows)} "
            f"mean={rows.mean():.0f} p5={np.quantile(rows, 0.05):.0f} "
            f"p95={np.quantile(rows, 0.95):.0f}"
        )
        below_halt = [p for p, n in trpp.items() if n < AR2_PER_PAIR_MIN_TRAIN_ROWS_HALT]
        if below_halt:
            raise SanityProbeError(
                f"AR2 train_rows_per_pair below HALT threshold "
                f"({AR2_PER_PAIR_MIN_TRAIN_ROWS_HALT}): {below_halt[:5]}"
            )

    # Item 9 NEW: AR3 blend summary (rank distribution check)
    if ar3_blend_summary is not None:
        out["ar3_blend_summary"] = ar3_blend_summary
        print(
            f"  AR3 blend summary: w_S-B={AR3_BLEND_W_SB} w_S-E={AR3_BLEND_W_SE} "
            f"rank_norm method=pandas.rank(pct=True, method=average)"
        )

    # Item 10 NEW: AR4 regime split + balance
    if ar4_info is not None:
        rtpp = ar4_info.get("regime_threshold_per_pair", {})
        rb = ar4_info.get("regime_balance", {})
        out["ar4_regime_threshold_per_pair"] = {p: float(v) for p, v in rtpp.items()}
        out["ar4_regime_balance"] = rb
        out["ar4_imbalance_warn_pairs"] = ar4_info.get("imbalance_warn_pairs", [])
        out["ar4_high_train_rows"] = int(ar4_info.get("high_train_rows", 0))
        out["ar4_low_train_rows"] = int(ar4_info.get("low_train_rows", 0))
        missing = [p for p in pairs if p not in rtpp]
        if missing:
            raise SanityProbeError(
                f"AR4 regime_threshold_per_pair missing pairs: {missing[:5]} (NG#A0-1)"
            )
        non_finite = [p for p, v in rtpp.items() if not np.isfinite(v)]
        if non_finite:
            raise SanityProbeError(
                f"AR4 regime_threshold_per_pair non-finite for pairs: {non_finite[:5]}"
            )
        print(
            f"  AR4 regime split: high_train={ar4_info.get('high_train_rows', 0)} "
            f"low_train={ar4_info.get('low_train_rows', 0)} "
            f"imbalance_warn_pairs={len(ar4_info.get('imbalance_warn_pairs', []))}"
        )

    # Top-tail audit per arch
    if top_tail_regime_audit_per_arch is not None:
        out["top_tail_regime_audit_per_arch"] = top_tail_regime_audit_per_arch

    # OOF + regression diagnostic (S-E control only)
    if oof_corr_diag_s_e is not None:
        out["oof_correlation_s_e"] = oof_corr_diag_s_e
    if train_reg_diag_s_e is not None:
        out["regression_diag_s_e"] = {
            "train": train_reg_diag_s_e,
            "val": val_reg_diag_s_e,
            "test": test_reg_diag_s_e,
        }
    if feature_importance_s_e is not None:
        out["feature_importance_s_e"] = feature_importance_s_e

    if cell_definitions is not None:
        out["cell_definitions"] = [{k: v for k, v in c.items()} for c in cell_definitions]

    print("=== SANITY PROBE: PASS ===")
    return out


# ---------------------------------------------------------------------------
# Eval report writer (25 sections; inherited from 28.0b + A0-narrow adaptations)
# ---------------------------------------------------------------------------


def write_eval_report_28_0c(
    report_path: Path,
    cell_results: list[dict],
    val_select: dict,
    verdict_info: dict,
    aggregate_info: dict,
    baseline_match_report: dict,
    arch_control_drift_report: dict,
    h_c3_per_arch: list[dict],
    h_c3_aggregate: dict,
    within_eval_drift_per_arch: dict[str, dict],
    sanity: dict,
    drop_stats_r7a: dict,
    t_range: tuple,
    preflight_diag: dict,
    n_cells_run: int,
    feature_importance_s_e: dict,
    regression_diag_s_e: dict,
    oof_corr_diag_s_e: dict,
    target_pnl_distribution: dict,
    predicted_pnl_distribution_s_e: dict,
    top_tail_regime_audit_per_arch: dict[str, dict],
    ar1_info_summary: dict | None,
    ar2_info_summary: dict | None,
    ar3_blend_summary: dict | None,
    ar4_info_summary: dict | None,
) -> None:
    """Write 25-section eval_report.md (A0-narrow adaptation of 28.0b shape)."""
    lines: list[str] = []
    t_min, t70, t85, t_max = t_range
    lines.append("# Phase 28.0c-β — A0-narrow Tabular Architecture-Topology Audit eval report")
    lines.append("")
    lines.append("**Sub-phase**: 28.0c-β")
    lines.append(
        "**Design memo**: PR #344 (`phase28_0c_alpha_a0_architecture_redesign_design_memo.md`)"
    )
    lines.append("**Routing**: PR #343 (post-28.0b routing review; A0 primary)")
    lines.append(
        "**Scope**: A0-narrow tabular topology audit (NOT full A0-broad sequence/NN redesign)"
    )
    lines.append("")
    lines.append(
        "**INTERPRETATION**: A negative result falsifies A0-narrow, not all possible A0. "
        "A0-broad (sequence / NN model classes) remains deferred-not-foreclosed per "
        "PR #344 §7.2."
    )
    lines.append("")

    # §1 Executive summary
    lines.append("## 1. Executive summary")
    lines.append("")
    lines.append("Per-AR H-C3 outcome ladder (PR #344 §12.3; precedence row 4 > 1 > 2 > 3):")
    lines.append("")
    lines.append("| AR | Cell | Outcome | Row | Reason |")
    lines.append("|---|---|---|---|---|")
    for o in h_c3_per_arch:
        lines.append(
            f"| {o.get('arch_id', '-')} | {o.get('cell_id', '-')} | "
            f"{o.get('outcome', '-')} | {o.get('row_matched', '-')} | "
            f"{o.get('reason', '-')[:100]} |"
        )
    lines.append("")
    lines.append(f"**Aggregate verdict**: {h_c3_aggregate.get('aggregate_verdict')}")
    lines.append(f"**A0-narrow status**: {h_c3_aggregate.get('a0_narrow_status')}")
    lines.append(f"**A0-broad status**: {h_c3_aggregate.get('a0_broad_status')}")
    lines.append(f"**Routing implication**: {h_c3_aggregate.get('routing_implication')}")
    lines.append("")
    if h_c3_aggregate.get("a0_narrow_status") == "FALSIFIED_A0_NARROW":
        lines.append(
            "> **EXPLICIT LABEL**: this result is `FALSIFIED_A0_NARROW`, NEVER "
            "`FALSIFIED_ALL_A0`. A0-broad sequence / NN model classes remain "
            "deferred-not-foreclosed; post-28.0c routing review MUST compare Path B "
            "(A0-broad scope amendment) vs Phase 28 closure / Phase 29 rebase."
        )
        lines.append("")
    lines.append(
        f"**C-sb-baseline reproduction**: "
        f"{'PASS' if baseline_match_report.get('all_match') else 'FAIL'}"
    )
    lines.append(
        f"**C-a0-arch-control drift vs 27.0d C-se**: "
        f"all_within_tolerance={arch_control_drift_report.get('all_within_tolerance')} "
        f"(warn={arch_control_drift_report.get('warn')}; DIAGNOSTIC-ONLY)"
    )
    lines.append("")

    # §2 Cells overview
    lines.append("## 2. Cells overview")
    lines.append("")
    lines.append("| Cell | Picker | Score | Architecture |")
    lines.append("|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        lines.append(
            f"| {cell['id']} | {cell.get('picker', '-')[:60]} | {cell.get('score_type', '-')} | "
            f"{cell.get('architecture', '-')} |"
        )
    lines.append("")

    # §3 Row-set / drop stats
    lines.append("## 3. Row-set policy / drop stats")
    lines.append("")
    lines.append(
        "**A0-narrow row-set policy** (PR #344 §9.2): all 6 cells share the R7-A-clean "
        "parent row-set; no R7-C row-drop. Fix A row-set isolation contract not exercised."
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
    lines.append("## 4. Sanity probe results")
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
    if ar1_info_summary:
        lines.append(
            f"- AR1 admitted-train: total={ar1_info_summary.get('n_admitted_train', 0)} "
            f"(per-pair mean≈{ar1_info_summary.get('admitted_train_mean', float('nan')):.0f})"
        )
    if ar2_info_summary:
        lines.append(
            f"- AR2 per-pair train rows: mean={ar2_info_summary.get('mean', float('nan')):.0f} "
            f"p5={ar2_info_summary.get('p5', float('nan')):.0f} "
            f"p95={ar2_info_summary.get('p95', float('nan')):.0f}"
        )
    if ar3_blend_summary:
        lines.append(
            f"- AR3 blend: w_S-B={ar3_blend_summary.get('w_s_b', AR3_BLEND_W_SB)} "
            f"w_S-E={ar3_blend_summary.get('w_s_e', AR3_BLEND_W_SE)} (α-fixed; NG#A0-1)"
        )
    if ar4_info_summary:
        lines.append(
            f"- AR4 regime split: high_train={ar4_info_summary.get('high_train_rows', 0)} "
            f"low_train={ar4_info_summary.get('low_train_rows', 0)} "
            f"imbalance_warn_pairs={ar4_info_summary.get('n_imbalance_warn_pairs', 0)}"
        )
    lines.append("")

    # §5 OOF correlation diagnostic
    lines.append("## 5. OOF correlation diagnostic — S-E control only (DIAGNOSTIC-ONLY)")
    lines.append("")
    if oof_corr_diag_s_e:
        p = oof_corr_diag_s_e.get("aggregate_pearson", float("nan"))
        sp = oof_corr_diag_s_e.get("aggregate_spearman", float("nan"))
        lines.append(f"- S-E control aggregate: pearson={p:+.4f} spearman={sp:+.4f}")
        lines.append(
            "- Per-AR OOF not run (impractical for AR2 with 20 specialists × 5 folds). "
            "S-E control OOF is the NG#A0-3 anchor; rule-axis + architecture-axis null."
        )
    lines.append("")

    # §6 Regression diagnostic
    lines.append("## 6. Regression diagnostic — S-E control (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| Split | n | R² | MAE | MSE |")
    lines.append("|---|---|---|---|---|")
    for split_name in ("train", "val", "test"):
        blk = (regression_diag_s_e or {}).get(split_name, {})
        lines.append(
            f"| {split_name} | {blk.get('n', '-')} | "
            f"{blk.get('r2', float('nan')):+.4f} | "
            f"{blk.get('mae', float('nan')):+.3f} | "
            f"{blk.get('mse', float('nan')):+.3f} |"
        )
    lines.append("")

    # §7 Per-cell quantile family results
    lines.append("## 7. Per-cell quantile family results")
    lines.append("")
    for c in cell_results:
        cell = c["cell"]
        lines.append(f"### {cell['id']} ({cell.get('picker', '-')[:70]})")
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

    # §8 Val-selected per cell
    lines.append("## 8. Val-selected (cell*, q*) cross-cell")
    lines.append("")
    sel = val_select.get("selected")
    if sel is None:
        lines.append("- no valid cell")
    else:
        lines.append(f"- cell: {_cell_signature(sel['cell'])}")
        sq = sel.get("selected_q_percent")
        sc = sel.get("selected_cutoff")
        lines.append(f"- q*={sq} cutoff={sc}")
        lines.append(
            f"- val Sharpe={sel.get('val_realised_sharpe', float('nan')):+.4f} "
            f"(n={sel.get('val_n_trades')})"
        )
        rm = sel.get("test_realised_metrics", {})
        lines.append(
            f"- test Sharpe={rm.get('sharpe', float('nan')):+.4f} "
            f"ann_pnl={rm.get('annual_pnl', float('nan')):+.1f} "
            f"n={rm.get('n_trades', 0)} "
            f"FORMAL Spearman={sel.get('test_formal_spearman', float('nan')):+.4f}"
        )
    lines.append("")

    # §9 Cross-cell aggregate
    lines.append("## 9. Cross-cell aggregate verdict")
    lines.append("")
    lines.append(f"- aggregate verdict: {aggregate_info.get('aggregate_verdict')}")
    lines.append(f"- agree: {aggregate_info.get('agree')}")
    lines.append(f"- branches: {aggregate_info.get('branches')}")
    lines.append("")

    # §10 §10-baseline reproduction
    lines.append("## 10. §10 baseline reproduction (FAIL-FAST)")
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

    # §11 Within-eval ablation drift
    lines.append("## 11. Within-eval ablation drift (per AR vs C-a0-arch-control)")
    lines.append("")
    lines.append(
        "| AR | n_trades Δ | within | Sharpe Δ | within | ann_pnl Δ | within | all_within |"
    )
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

    # §11b arch-control drift vs prior phases
    lines.append("## 11b. C-a0-arch-control drift vs 27.0d C-se (DIAGNOSTIC-ONLY WARN)")
    lines.append("")
    lines.append(
        "**5-phase bit-reproduction chain**: 27.0d C-se → 27.0f r7a-replica → "
        "28.0a r7a-replica → 28.0b top-q-control → 28.0c arch-control."
    )
    lines.append("")
    cd = arch_control_drift_report
    lines.append(f"- source: {cd.get('source', '-')}")
    lines.append(
        f"- n_trades: observed={cd.get('n_trades_observed')} "
        f"baseline_27_0d={cd.get('n_trades_baseline_27_0d')} "
        f"delta={cd.get('n_trades_delta')} "
        f"within={cd.get('n_trades_within_tolerance')}"
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

    # §12 Feature importance
    lines.append("## 12. Feature importance — S-E control regressor (DIAGNOSTIC-ONLY)")
    lines.append("")
    if isinstance(feature_importance_s_e, dict) and "items" in feature_importance_s_e:
        for item in feature_importance_s_e["items"]:
            lines.append(
                f"- {item.get('feature', '-')}: gain={item.get('gain', float('nan')):+.1f}"
            )
    else:
        lines.append(f"(unavailable: {feature_importance_s_e})")
    lines.append("")

    # §13 H-C3 outcome row binding per AR
    lines.append(
        "## 13. H-C3 outcome row binding per AR (A0-narrow scope; interpretation guards embedded)"
    )
    lines.append("")
    lines.append(
        "Per PR #344 §12: H-C3 = A0-narrow tabular topology audit. Failure of all "
        "AR variants is `FALSIFIED_A0_NARROW`, NEVER `FALSIFIED_ALL_A0`. A0-broad "
        "sequence/NN model classes remain deferred-not-foreclosed per §7.2."
    )
    lines.append("")
    lines.append(
        "| AR | Cell | Outcome | Row | Sharpe lift | val Sharpe | val n | cell Spearman | Notes |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for o in h_c3_per_arch:
        ev = o.get("evidence", {}) if isinstance(o.get("evidence"), dict) else {}
        lift = ev.get("sharpe_lift_absolute", float("nan"))
        vs = ev.get("val_sharpe", float("nan"))
        vn = ev.get("val_n_trades", "-")
        sp = ev.get("cell_spearman_val", float("nan"))
        lift_str = f"{lift:+.4f}" if isinstance(lift, float) and np.isfinite(lift) else str(lift)
        vs_str = f"{vs:+.4f}" if isinstance(vs, float) and np.isfinite(vs) else str(vs)
        sp_str = f"{sp:+.4f}" if isinstance(sp, float) and np.isfinite(sp) else str(sp)
        lines.append(
            f"| {o.get('arch_id', '-')} | {o.get('cell_id', '-')} | "
            f"{o.get('outcome', '-')} | {o.get('row_matched', '-')} | "
            f"{lift_str} | {vs_str} | {vn} | {sp_str} | "
            f"{o.get('reason', '-')[:80]} |"
        )
    lines.append("")
    lines.append(f"**Aggregate H-C3 verdict**: {h_c3_aggregate.get('aggregate_verdict')}")
    lines.append(f"**A0-narrow status**: {h_c3_aggregate.get('a0_narrow_status')}")
    lines.append(f"**A0-broad status**: {h_c3_aggregate.get('a0_broad_status')}")
    lines.append(f"**Routing**: {h_c3_aggregate.get('routing_implication')}")
    lines.append("")

    # §14 Trade-count budget audit
    lines.append("## 14. Trade-count budget audit — per AR + arch-control")
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
    lines.append("| Cell | val top-3 pairs | val Herfindahl | test top-3 | test Herfindahl |")
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
    lines.append("## 16. Direction balance per cell (val-selected on test)")
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

    # §18 Top-tail regime audit per arch
    lines.append("## 18. Top-tail regime audit per AR (DIAGNOSTIC-ONLY; spread_at_signal_pip only)")
    lines.append("")
    lines.append("**Note**: R7-C f5a/f5b/f5c features NOT computed (out of scope per Clause 6).")
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

    # §19 R7-A NaN-rate
    lines.append("## 19. R7-A new-feature NaN-rate check (sanity probe item)")
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

    # §20 Realised-PnL distribution by class
    lines.append("## 20. Realised-PnL distribution by class on TRAIN (DIAGNOSTIC)")
    lines.append("")
    if target_pnl_distribution:
        lines.append("| Class | n | mean | p5 | p50 | p95 |")
        lines.append("|---|---|---|---|---|---|")
        for cname, stats in target_pnl_distribution.items():
            lines.append(
                f"| {cname} | {stats.get('n', 0)} | "
                f"{stats.get('mean', float('nan')):+.3f} | "
                f"{stats.get('p5', float('nan')):+.3f} | "
                f"{stats.get('p50', float('nan')):+.3f} | "
                f"{stats.get('p95', float('nan')):+.3f} |"
            )
    lines.append("")

    # §21 Predicted PnL distribution
    lines.append("## 21. Predicted PnL distribution — S-E control (DIAGNOSTIC)")
    lines.append("")
    lines.append("| Split | n | mean | p5 | p50 | p95 |")
    lines.append("|---|---|---|---|---|---|")
    for split_name, stats in (predicted_pnl_distribution_s_e or {}).items():
        lines.append(
            f"| {split_name} | {stats.get('n_finite', 0)} | "
            f"{stats.get('mean', float('nan')):+.3f} | "
            f"{stats.get('p5', float('nan')):+.3f} | "
            f"{stats.get('p50', float('nan')):+.3f} | "
            f"{stats.get('p95', float('nan')):+.3f} |"
        )
    lines.append("")

    # §22 References
    lines.append("## 22. References")
    lines.append("")
    lines.append("- PR #335 — Phase 28 kickoff")
    lines.append("- PR #336 — Phase 28 first-mover routing review")
    lines.append("- PR #339 — Phase 28 post-28.0a routing review")
    lines.append("- PR #341 — Phase 28.0b-α A4 design memo")
    lines.append("- PR #342 — Phase 28.0b-β A4 eval (R-T1 = FALSIFIED_under_A4)")
    lines.append("- PR #343 — Phase 28 post-28.0b routing review (A0 primary)")
    lines.append("- PR #344 — Phase 28.0c-α A0-narrow design memo (this sub-phase α)")
    lines.append("- PR #325 — Phase 27.0d-β S-E regression (score backbone source)")
    lines.append("- PR #332 — Phase 27.0f-β (within-eval ablation template)")
    lines.append("- PR #334 — Phase 27 closure memo")
    lines.append("- PR #279 — γ closure")
    lines.append("- Phase 22 frozen-OOS contract")
    lines.append("- Phase 9.12 production v9 tip 79ed1e8 (untouched)")
    lines.append("")

    # §23 Caveats
    lines.append("## 23. Caveats")
    lines.append("")
    lines.append(
        "- All test-set metrics outside the val-selected per-cell configuration are "
        "DIAGNOSTIC-ONLY and excluded from the formal H-C3 verdict."
    )
    lines.append(
        "- H2 PASS = PROMISING_BUT_NEEDS_OOS only. ADOPT_CANDIDATE wall preserved per "
        "Clause 1. NG#10 / NG#11 not relaxed."
    )
    lines.append(
        "- **AR1 interpretation guard**: stage-1 admission threshold resembles 28.0b R1 "
        "selection-like behavior. Admitted under A0-narrow as architecture-conditioning "
        "of stage 2's training set, NOT final selection rule. PASS/PARTIAL_SUPPORT "
        "outcomes are 'architecture-topology with embedded admission gate', NOT 'pure "
        "architecture-only success'. NG#A0-1 enforces."
    )
    lines.append(
        "- **AR4 interpretation guard**: deterministic regime split is A3-boundary-"
        "sensitive but admitted under A0-narrow because routing is deterministic (no "
        "learned gating / MoE / adaptive weights). PASS/PARTIAL_SUPPORT outcomes are "
        "'deterministic tabular regime split helped', NOT 'full A3 regime-conditioned "
        "modeling is solved'. A3 elevation requires separate scope amendment."
    )
    lines.append(
        "- **A0-narrow vs A0-broad distinction**: all 4 AR variants remain within "
        "tabular LightGBM. Failure of all 4 is `FALSIFIED_A0_NARROW`, NEVER "
        "`FALSIFIED_ALL_A0`. A0-broad sequence/NN model classes remain deferred-not-"
        "foreclosed per PR #344 §7.2."
    )
    lines.append(
        "- Top-tail regime audit uses `spread_at_signal_pip` only; R7-C features are "
        "out of scope per Clause 6."
    )
    lines.append(
        "- No fallback policy (NG#A0-1): AR1 admitted-train shortage / AR2 per-pair "
        "fit failure → HALT; AR4 regime imbalance → WARN-only. No fallback to global "
        "model / hyperparameter tuning / threshold adjustment."
    )
    lines.append("")

    # §24 Cross-validation re-fits diagnostic
    lines.append("## 24. Cross-validation re-fits diagnostic (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append(
        "5-fold OOF (seed=42) on S-E control backbone (inherited from 27.0d). Per-AR "
        "OOF not run (impractical for AR2 with 20 specialists). Aggregate Pearson / "
        "Spearman reported in §5."
    )
    lines.append("")

    # §25 Sub-phase verdict snapshot
    lines.append("## 25. Sub-phase verdict snapshot")
    lines.append("")
    lines.append("- per-AR outcomes:")
    for o in h_c3_per_arch:
        aid = o.get("arch_id", "-")
        cid = o.get("cell_id", "-")
        oc = o.get("outcome", "-")
        rm = o.get("row_matched", "-")
        lines.append(f"  - {aid} ({cid}): {oc} (row {rm})")
    lines.append(f"- aggregate verdict: {h_c3_aggregate.get('aggregate_verdict')}")
    lines.append(f"- A0-narrow status: {h_c3_aggregate.get('a0_narrow_status')}")
    lines.append(f"- A0-broad status: {h_c3_aggregate.get('a0_broad_status')} (PR #344 §7.2)")
    lines.append(f"- routing implication: {h_c3_aggregate.get('routing_implication')}")
    lines.append(
        f"- C-sb-baseline reproduction: "
        f"{'PASS' if baseline_match_report.get('all_match') else 'FAIL'}"
    )
    lines.append(
        f"- C-a0-arch-control drift vs 27.0d C-se: "
        f"all_within_tolerance={arch_control_drift_report.get('all_within_tolerance')} "
        f"(WARN-only)"
    )
    lines.append("")
    lines.append("*End of `artifacts/stage28_0c/eval_report.md`.*")
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
    parser.add_argument("--quick-mode", action="store_true")
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"=== Stage 28.0c-β A0-narrow Tabular Architecture-Topology Audit "
        f"({len(args.pairs)} pairs) ==="
    )
    print(
        f"K_FAV={K_FAV} K_ADV={K_ADV} H_M1={H_M1_BARS} | "
        f"quantile_percents={list(QUANTILE_PERCENTS_28_0C)}"
    )
    print(f"R7-A FIXED (4 features): {list(ALL_FEATURES_R7A)}")
    print(
        f"Closed 4-architecture allowlist (α-fixed; NG#A0-1): "
        f"AR1 stage-1 top {AR1_STAGE1_ADMIT_PERCENTILE:.0f}% per-pair val-median admission, "
        f"AR2 20 per-pair specialists, "
        f"AR3 blend w_S-B={AR3_BLEND_W_SB}/w_S-E={AR3_BLEND_W_SE}, "
        f"AR4 per-pair val-median atr_at_signal_pip regime split"
    )
    print(f"Fixed loss: symmetric Huber α={HUBER_ALPHA} (NG#A0-1; no β-time grid; no 5th variant)")
    print(f"OOF (DIAGNOSTIC-ONLY): {OOF_N_FOLDS} folds, seed={OOF_SEED} (S-E control only)")
    print(
        "INTERPRETATION: A0-narrow tabular topology audit; A0-broad sequence/NN "
        "deferred-not-foreclosed per PR #344 §7.2"
    )

    # 1. Load labels
    raw_label_path = REPO_ROOT / "artifacts" / "stage25_0a" / "path_quality_dataset.parquet"
    raw_labels = pd.read_parquet(raw_label_path)
    if args.pairs != PAIRS_20:
        raw_labels = raw_labels[raw_labels["pair"].isin(args.pairs)]
    print(f"  labels rows: {len(raw_labels)}")

    # 2. Pre-flight
    print("Running pre-flight...")
    try:
        preflight_diag = verify_l3_preflight(raw_labels, args.pairs)
    except L3PreflightError as exc:
        print(f"PRE-FLIGHT FAILED: {exc}")
        return 2
    if not preflight_diag["lightgbm_available"]:
        print("LightGBM required; halting.")
        return 2

    # 3. M1 runtime
    pair_runtime_map: dict[str, dict] = {}
    for pair in args.pairs:
        t_pair = time.time()
        pair_runtime_map[pair] = _build_pair_runtime(pair, days=args.days)
        print(f"  {pair}: m1 rows {pair_runtime_map[pair]['n_m1']} ({time.time() - t_pair:5.1f}s)")

    # 4. Split
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
            f"test={len(test_df)} — formal verdict NOT valid in quick mode"
        )

    # 5. Sanity probe (pre-fit; items 1-6 only)
    sanity = run_sanity_probe_28_0c(
        train_df, val_df, test_df, pair_runtime_map, args.pairs, days=args.days
    )

    if args.sanity_probe_only:
        print("\n--sanity-probe-only set; exiting after probe.")
        if not args.no_write:
            (args.out_dir / "sanity_probe.json").write_text(
                json.dumps(sanity, indent=2, default=str), encoding="utf-8"
            )
            print(f"sanity probe results: {args.out_dir / 'sanity_probe.json'}")
        return 0

    # 6. R7-A row-drop
    print("R7-A row-drop...")
    train_df, train_drop = drop_rows_with_missing_new_features(train_df)
    val_df, val_drop = drop_rows_with_missing_new_features(val_df)
    test_df, test_drop = drop_rows_with_missing_new_features(test_df)
    drop_stats_r7a = {"train": train_drop, "val": val_drop, "test": test_drop}
    for name, ds in drop_stats_r7a.items():
        print(
            f"  {name}: n_input={ds['n_input']} n_kept={ds['n_kept']} n_dropped={ds['n_dropped']}"
        )

    # 7. Precompute realised PnL
    print("Precomputing realised PnL per row (train + val + test)...")
    t0 = time.time()
    pnl_train_full = precompute_realised_pnl_per_row(train_df, pair_runtime_map)
    print(f"  train: {len(pnl_train_full)} rows ({time.time() - t0:.1f}s)")
    t0 = time.time()
    pnl_val_full = precompute_realised_pnl_per_row(val_df, pair_runtime_map)
    print(f"  val: {len(pnl_val_full)} rows ({time.time() - t0:.1f}s)")
    t0 = time.time()
    pnl_test_full = precompute_realised_pnl_per_row(test_df, pair_runtime_map)
    print(f"  test: {len(pnl_test_full)} rows ({time.time() - t0:.1f}s)")

    nan_pnl_mask = ~np.isfinite(pnl_train_full)
    nan_pnl_count = int(nan_pnl_mask.sum())
    threshold_count = NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD * len(pnl_train_full)
    print(f"  NaN-PnL train rows: {nan_pnl_count} (HALT > {int(threshold_count)})")
    if nan_pnl_count > threshold_count:
        raise SanityProbeError(
            f"train rows with NaN PnL = {nan_pnl_count} > {NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD:.1%}"
        )

    train_df_for_reg = train_df.loc[~nan_pnl_mask].reset_index(drop=True)
    pnl_train_for_reg = pnl_train_full[~nan_pnl_mask]
    train_pair_clean = train_df_for_reg["pair"].to_numpy()

    # 8. Build labels
    train_label = build_l1_labels_for_dataframe(train_df).to_numpy()
    val_label = build_l1_labels_for_dataframe(val_df).to_numpy()
    test_label = build_l1_labels_for_dataframe(test_df).to_numpy()
    train_label_clean = train_label[~nan_pnl_mask]

    # 9. 5-fold OOF on S-E control score (DIAGNOSTIC-ONLY)
    print("Running 5-fold OOF regression on S-E control (DIAGNOSTIC-ONLY; seed=42)...")
    fold_idx = make_oof_fold_assignment(len(pnl_train_for_reg), n_folds=OOF_N_FOLDS, seed=OOF_SEED)
    x_train_r7a = train_df_for_reg[list(ALL_FEATURES_R7A)]
    t0 = time.time()
    oof_preds_s_e = fit_oof_regression_diagnostic(x_train_r7a, pnl_train_for_reg, fold_idx)
    oof_corr_diag_s_e = compute_oof_correlation_diagnostic(
        oof_preds_s_e, pnl_train_for_reg, fold_idx
    )
    print(
        f"  OOF (S-E control): pearson={oof_corr_diag_s_e['aggregate_pearson']:+.4f} "
        f"spearman={oof_corr_diag_s_e['aggregate_spearman']:+.4f} ({time.time() - t0:.1f}s)"
    )

    # 10. Fit shared backbones: S-E control regressor + S-B multiclass head
    print("Fitting S-E control regressor (R7-A; symmetric Huber α=0.9)...")
    t0 = time.time()
    regressor_se_control = build_pipeline_lightgbm_regression_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        regressor_se_control.fit(x_train_r7a, pnl_train_for_reg)
    val_pred_se_control = compute_picker_score_s_e(
        regressor_se_control, val_df[list(ALL_FEATURES_R7A)]
    )
    test_pred_se_control = compute_picker_score_s_e(
        regressor_se_control, test_df[list(ALL_FEATURES_R7A)]
    )
    train_pred_se_control = compute_picker_score_s_e(regressor_se_control, x_train_r7a)
    fi_s_e = compute_feature_importance_diagnostic(regressor_se_control)
    print(f"  S-E control regressor fit + predict: {time.time() - t0:.1f}s")

    print("Fitting S-B multiclass head (R7-A; shared across baseline + AR1 stage-1 + AR3)...")
    t0 = time.time()
    multiclass_pipeline = build_pipeline_lightgbm_multiclass_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        multiclass_pipeline.fit(x_train_r7a, train_label_clean)
    val_raw_probs = _multiclass_to_class_probs(
        multiclass_pipeline, val_df[list(ALL_FEATURES_R7A)], NUM_CLASSES
    )
    test_raw_probs = _multiclass_to_class_probs(
        multiclass_pipeline, test_df[list(ALL_FEATURES_R7A)], NUM_CLASSES
    )
    print(f"  multiclass fit + predict_proba: {time.time() - t0:.1f}s")

    # 11. Regression diagnostic for S-E control
    train_reg_diag_s_e = compute_regression_diagnostic(pnl_train_for_reg, train_pred_se_control)
    val_reg_diag_s_e = compute_regression_diagnostic(pnl_val_full, val_pred_se_control)
    test_reg_diag_s_e = compute_regression_diagnostic(pnl_test_full, test_pred_se_control)

    # 12. Compute S-B raw scores (for baseline + AR1 stage-1 + AR3 S-B branch)
    val_score_s_b_raw = compute_picker_score_s_b_raw(val_raw_probs)
    test_score_s_b_raw = compute_picker_score_s_b_raw(test_raw_probs)

    # 13. Fit AR1
    print("Fitting AR1 hierarchical two-stage...")
    t0 = time.time()
    ar1_info = fit_ar1_hierarchical(
        x_train_r7a,
        train_label_clean,
        train_pair_clean,
        pnl_train_for_reg,
        val_df,
        test_df,
    )
    val_score_ar1 = ar1_info["val_score"]
    test_score_ar1 = ar1_info["test_score"]
    print(
        f"  AR1 fit + predict: {time.time() - t0:.1f}s "
        f"(n_admitted_train={ar1_info['n_admitted_train']}, "
        f"val_finite={int(np.isfinite(val_score_ar1).sum())}, "
        f"test_finite={int(np.isfinite(test_score_ar1).sum())})"
    )

    # 14. Fit AR2
    print("Fitting AR2 pair-conditioned specialists (20 per-pair regressors)...")
    t0 = time.time()
    ar2_info = fit_ar2_pair_specialists(
        x_train_r7a, pnl_train_for_reg, train_pair_clean, val_df, test_df, args.pairs
    )
    val_score_ar2 = ar2_info["val_score"]
    test_score_ar2 = ar2_info["test_score"]
    print(
        f"  AR2 fit + predict: {time.time() - t0:.1f}s "
        f"(n_specialists={len(ar2_info['specialists'])})"
    )

    # 15. Compute AR3 stacked blend (uses already-fit S-B + S-E control)
    print("Computing AR3 stacked blend (0.5·rank(S-B raw) + 0.5·rank(S-E))...")
    t0 = time.time()
    val_score_ar3 = compute_ar3_blended_score(val_score_s_b_raw, val_pred_se_control)
    test_score_ar3 = compute_ar3_blended_score(test_score_s_b_raw, test_pred_se_control)
    ar3_blend_summary = {
        "w_s_b": AR3_BLEND_W_SB,
        "w_s_e": AR3_BLEND_W_SE,
        "rank_method": "pandas.rank(pct=True, method=average)",
        "val_finite": int(np.isfinite(val_score_ar3).sum()),
        "test_finite": int(np.isfinite(test_score_ar3).sum()),
    }
    print(f"  AR3 blend: {time.time() - t0:.2f}s")

    # 16. Fit AR4
    print("Fitting AR4 deterministic regime split (high-vol / low-vol specialists)...")
    t0 = time.time()
    ar4_info = fit_ar4_regime_split(
        x_train_r7a, pnl_train_for_reg, train_pair_clean, train_df_for_reg, val_df, test_df
    )
    val_score_ar4 = ar4_info["val_score"]
    test_score_ar4 = ar4_info["test_score"]
    print(
        f"  AR4 fit + predict: {time.time() - t0:.1f}s "
        f"(high_train={ar4_info['high_train_rows']}, low_train={ar4_info['low_train_rows']}, "
        f"imbalance_warn_pairs={len(ar4_info['imbalance_warn_pairs'])})"
    )

    # 17. Top-tail regime audit per AR (DIAGNOSTIC-ONLY)
    print("Computing top-tail regime audit per AR...")
    top_tail_regime_audit_per_arch = {
        "AR1": compute_top_tail_regime_audit_for_a0(val_score_ar1, val_df),
        "AR2": compute_top_tail_regime_audit_for_a0(val_score_ar2, val_df),
        "AR3": compute_top_tail_regime_audit_for_a0(val_score_ar3, val_df),
        "AR4": compute_top_tail_regime_audit_for_a0(val_score_ar4, val_df),
        "arch_control": compute_top_tail_regime_audit_for_a0(val_pred_se_control, val_df),
    }

    # Predicted PnL distribution for S-E control (DIAGNOSTIC)
    predicted_pnl_distribution_s_e: dict[str, dict] = {}
    for split_name, pred in [
        ("train", train_pred_se_control),
        ("val", val_pred_se_control),
        ("test", test_pred_se_control),
    ]:
        finite = pred[np.isfinite(pred)]
        if len(finite) == 0:
            predicted_pnl_distribution_s_e[split_name] = {"n_finite": 0}
            continue
        predicted_pnl_distribution_s_e[split_name] = {
            "n_finite": int(len(finite)),
            "mean": float(finite.mean()),
            "p5": float(np.quantile(finite, 0.05)),
            "p50": float(np.quantile(finite, 0.50)),
            "p95": float(np.quantile(finite, 0.95)),
        }

    # 18. Build cells
    cells = build_a0_cells()

    # 19. Updated sanity probe with post-fit info
    sanity_post = run_sanity_probe_28_0c(
        train_df,
        val_df,
        test_df,
        pair_runtime_map,
        args.pairs,
        days=args.days,
        pnl_train_full=pnl_train_full,
        ar1_info=ar1_info,
        ar2_info=ar2_info,
        ar3_blend_summary=ar3_blend_summary,
        ar4_info=ar4_info,
        val_pred_s_e=val_pred_se_control,
        test_pred_s_e=test_pred_se_control,
        train_pred_s_e=train_pred_se_control,
        fold_idx=fold_idx,
        oof_corr_diag_s_e=oof_corr_diag_s_e,
        train_reg_diag_s_e=train_reg_diag_s_e,
        val_reg_diag_s_e=val_reg_diag_s_e,
        test_reg_diag_s_e=test_reg_diag_s_e,
        feature_importance_s_e=fi_s_e,
        train_drop_for_nan_pnl_count=nan_pnl_count,
        top_tail_regime_audit_per_arch=top_tail_regime_audit_per_arch,
        cell_definitions=cells,
    )
    sanity = sanity_post

    # 20. Per-cell evaluation
    print("Per-cell evaluation...")
    score_by_id = {
        "C-a0-AR1": (val_score_ar1, test_score_ar1),
        "C-a0-AR2": (val_score_ar2, test_score_ar2),
        "C-a0-AR3": (val_score_ar3, test_score_ar3),
        "C-a0-AR4": (val_score_ar4, test_score_ar4),
        "C-a0-arch-control": (val_pred_se_control, test_pred_se_control),
        "C-sb-baseline": (val_score_s_b_raw, test_score_s_b_raw),
    }
    cell_results: list[dict] = []
    n_cells_run = len(cells)
    for i, cell in enumerate(cells):
        t_cell = time.time()
        cell_id = cell["id"]
        if cell_id not in score_by_id:
            raise ValueError(f"Unknown cell id: {cell_id}")
        v_score, t_score = score_by_id[cell_id]
        result = evaluate_quantile_cell_28_0c(
            cell,
            train_df,
            val_df,
            test_df,
            train_label,
            val_label,
            test_label,
            val_raw_probs,
            test_raw_probs,
            v_score,
            t_score,
            pnl_val_full,
            pnl_test_full,
            fi_s_e
            if cell_id != "C-sb-baseline"
            else compute_feature_importance_diagnostic(multiclass_pipeline),
        )
        cell_results.append(result)
        rm = result.get("test_realised_metrics", {})
        sp = result.get("test_formal_spearman", float("nan"))
        sq = result.get("selected_q_percent")
        print(
            f"  cell {i + 1}/{n_cells_run} {cell['id']} | q*={sq} | "
            f"val_sharpe={result.get('val_realised_sharpe', float('nan')):+.3f} "
            f"val_n={result.get('val_n_trades', 0):>6} | "
            f"test_sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"test_n={rm.get('n_trades', 0):>6} test_sp={sp:+.4f} ({time.time() - t_cell:.1f}s)"
        )

    # 21. C-sb-baseline match check (FAIL-FAST)
    print("\n=== C-sb-baseline match check (per PR #344 §10) ===")
    c_sb_baseline = next((c for c in cell_results if c["cell"]["id"] == "C-sb-baseline"), None)
    if c_sb_baseline is None or c_sb_baseline.get("h_state") != "OK":
        raise BaselineMismatchError("C-sb-baseline missing or h_state != OK")
    baseline_match_report = check_c_sb_baseline_match(c_sb_baseline)
    print(f"  baseline match: {baseline_match_report['all_match']}")
    for key in ("n_trades", "sharpe", "ann_pnl"):
        print(
            f"    {key}: observed={baseline_match_report[f'{key}_observed']} "
            f"baseline={baseline_match_report[f'{key}_baseline']} "
            f"delta={baseline_match_report[f'{key}_delta']:+.6g} "
            f"match={baseline_match_report[f'{key}_match']}"
        )

    # 22. C-a0-arch-control drift vs 27.0d C-se (DIAGNOSTIC-ONLY WARN)
    print("\n=== C-a0-arch-control drift check vs 27.0d C-se (DIAGNOSTIC-ONLY WARN) ===")
    c_a0_arch_control = next(
        (c for c in cell_results if c["cell"]["id"] == "C-a0-arch-control"), None
    )
    if c_a0_arch_control is None or c_a0_arch_control.get("h_state") != "OK":
        arch_control_drift_report = {
            "source": "n/a",
            "warn": True,
            "all_within_tolerance": False,
            "note": "C-a0-arch-control not present or h_state != OK",
        }
    else:
        arch_control_drift_report = compute_c_a0_arch_control_drift_check(c_a0_arch_control)
        if arch_control_drift_report["warn"]:
            warnings.warn(
                f"C-a0-arch-control drift vs 27.0d C-se exceeds tolerance "
                f"(n_trades={arch_control_drift_report.get('n_trades_within_tolerance')}, "
                f"Sharpe={arch_control_drift_report.get('sharpe_within_tolerance')}, "
                f"ann_pnl={arch_control_drift_report.get('ann_pnl_within_tolerance')}); "
                "DIAGNOSTIC-ONLY WARN per PR #344 §11 (NOT HALT)",
                UserWarning,
                stacklevel=2,
            )
        print(f"  drift WARN: {arch_control_drift_report.get('warn')}")
        print(f"  all_within_tolerance: {arch_control_drift_report.get('all_within_tolerance')}")

    # 23. Within-eval drift per AR (PARTIAL_DRIFT_ARCH_REPLICA detection)
    print("\n=== Within-eval ablation drift per AR (vs C-a0-arch-control) ===")
    within_eval_drift_per_arch: dict[str, dict] = {}
    for arch_id, cell_id in [
        ("AR1", "C-a0-AR1"),
        ("AR2", "C-a0-AR2"),
        ("AR3", "C-a0-AR3"),
        ("AR4", "C-a0-AR4"),
    ]:
        ar_cell = next((c for c in cell_results if c["cell"]["id"] == cell_id), None)
        if ar_cell is None or c_a0_arch_control is None:
            within_eval_drift_per_arch[arch_id] = {
                "all_within_tolerance": False,
                "warn": True,
                "note": "AR cell or arch-control missing",
            }
        else:
            within_eval_drift_per_arch[arch_id] = compute_within_eval_arch_drift_check(
                ar_cell, c_a0_arch_control
            )
        d = within_eval_drift_per_arch[arch_id]
        nd = d.get("n_trades_delta", "-")
        shd = d.get("sharpe_delta", float("nan"))
        apd = d.get("ann_pnl_delta", float("nan"))
        shd_str = f"{shd:+.4e}" if isinstance(shd, float) and np.isfinite(shd) else str(shd)
        apd_str = f"{apd:+.3f}" if isinstance(apd, float) and np.isfinite(apd) else str(apd)
        print(
            f"  {arch_id}: all_within_tolerance={d.get('all_within_tolerance')} "
            f"(n_trades_Δ={nd}, Sharpe_Δ={shd_str}, ann_pnl_Δ={apd_str})"
        )

    # 24. Val-selection + cross-cell verdict
    val_select = select_cell_validation_only(cell_results)
    verdict_info = assign_verdict(val_select.get("selected"))
    aggregate_info = aggregate_cross_cell_verdict(cell_results)

    print("\n=== Val-selected (cell*, q*) ===")
    sel = val_select.get("selected")
    if sel is None:
        print("  no valid cell")
    else:
        print(f"  cell: {_cell_signature(sel['cell'])}")
        rm = sel.get("test_realised_metrics", {})
        sp = sel.get("test_formal_spearman", float("nan"))
        sq = sel.get("selected_q_percent")
        sc = sel.get("selected_cutoff")
        print(f"  q*={sq}, cutoff={sc}")
        print(
            f"  val Sharpe={sel.get('val_realised_sharpe', float('nan')):.4f} "
            f"(n_trades={sel.get('val_n_trades')})"
        )
        print(
            f"  test Sharpe={rm.get('sharpe', float('nan')):.4f}; "
            f"ann_pnl={rm.get('annual_pnl', 0.0):+.1f}; "
            f"n_trades={rm.get('n_trades', 0)}; "
            f"FORMAL Spearman={sp:.4f}"
        )

    print(f"\n=== Cross-cell aggregate: {aggregate_info['aggregate_verdict']} ===")

    # 25. H-C3 4-outcome per AR
    print("\n=== H-C3 4-outcome ladder per AR ===")
    h_c3_per_arch: list[dict] = []
    for arch_id, cell_id in [
        ("AR1", "C-a0-AR1"),
        ("AR2", "C-a0-AR2"),
        ("AR3", "C-a0-AR3"),
        ("AR4", "C-a0-AR4"),
    ]:
        ar_cell = next((c for c in cell_results if c["cell"]["id"] == cell_id), None)
        if ar_cell is None:
            h_c3_per_arch.append(
                {
                    "cell_id": cell_id,
                    "arch_id": arch_id,
                    "outcome": H_C3_OUTCOME_NEEDS_REVIEW,
                    "row_matched": 0,
                    "reason": "cell missing",
                }
            )
            continue
        outcome = compute_h_c3_outcome_per_arch(
            ar_cell,
            baseline_match_report,
            within_eval_drift_per_arch.get(arch_id, {}),
            arch_id,
        )
        h_c3_per_arch.append(outcome)
        print(
            f"  {arch_id}: {outcome.get('outcome')} (row {outcome.get('row_matched')}) "
            f"— {outcome.get('reason', '-')[:80]}"
        )

    # 26. Aggregate H-C3 verdict
    h_c3_aggregate = compute_h_c3_aggregate_verdict(h_c3_per_arch)
    print(f"\n=== Aggregate H-C3 verdict: {h_c3_aggregate.get('aggregate_verdict')} ===")
    print(f"=== A0-narrow status: {h_c3_aggregate.get('a0_narrow_status')} ===")
    print(f"=== A0-broad status: {h_c3_aggregate.get('a0_broad_status')} ===")
    print(f"=== Routing implication: {h_c3_aggregate.get('routing_implication')} ===")

    if args.no_write:
        print("\n--no-write set; skipping artifact write.")
        return 0

    target_pnl_distribution = sanity.get("target_pnl_distribution_train", {})

    # Summaries for eval report
    ar1_info_summary = None
    if ar1_info is not None:
        atpp = ar1_info.get("admitted_train_per_pair", {})
        vals = np.array(list(atpp.values()), dtype=np.float64) if atpp else np.array([0.0])
        ar1_info_summary = {
            "n_admitted_train": ar1_info.get("n_admitted_train", 0),
            "admitted_train_mean": float(vals.mean()),
        }
    ar2_info_summary = None
    if ar2_info is not None:
        trpp = ar2_info.get("train_rows_per_pair", {})
        rows = np.array(list(trpp.values()), dtype=np.float64) if trpp else np.array([0.0])
        ar2_info_summary = {
            "mean": float(rows.mean()),
            "p5": float(np.quantile(rows, 0.05)),
            "p95": float(np.quantile(rows, 0.95)),
        }
    ar4_info_summary = None
    if ar4_info is not None:
        ar4_info_summary = {
            "high_train_rows": ar4_info.get("high_train_rows", 0),
            "low_train_rows": ar4_info.get("low_train_rows", 0),
            "n_imbalance_warn_pairs": len(ar4_info.get("imbalance_warn_pairs", [])),
        }

    # Write 25-section eval report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report_28_0c(
        report_path,
        cell_results,
        val_select,
        verdict_info,
        aggregate_info,
        baseline_match_report,
        arch_control_drift_report,
        h_c3_per_arch,
        h_c3_aggregate,
        within_eval_drift_per_arch,
        sanity,
        drop_stats_r7a,
        (t_min, t70, t85, t_max),
        preflight_diag,
        n_cells_run,
        fi_s_e,
        {
            "train": train_reg_diag_s_e,
            "val": val_reg_diag_s_e,
            "test": test_reg_diag_s_e,
        },
        oof_corr_diag_s_e,
        target_pnl_distribution,
        predicted_pnl_distribution_s_e,
        top_tail_regime_audit_per_arch,
        ar1_info_summary,
        ar2_info_summary,
        ar3_blend_summary,
        ar4_info_summary,
    )
    print(f"\nReport: {report_path}")

    # Persist artifacts
    summary_rows: list[dict] = []
    for c in cell_results:
        cell = c["cell"]
        rm = c.get("test_realised_metrics", {})
        sp = c.get("test_formal_spearman", float("nan"))
        cd = c.get("test_classification_diag", {})
        sq = c.get("selected_q_percent")
        sq_serialised = float(sq) if sq is not None else -1
        sc = c.get("selected_cutoff")
        sc_serialised = float(sc) if isinstance(sc, (int, float)) else float("nan")
        summary_rows.append(
            {
                "cell_id": cell["id"],
                "picker_name": cell["picker"],
                "score_type": cell.get("score_type", "-"),
                "feature_set": cell.get("feature_set", "-"),
                "architecture": cell.get("architecture", "-"),
                "quantile_percents": list(cell.get("quantile_percents", ())),
                "n_train": c.get("n_train", 0),
                "n_val": c.get("n_val", 0),
                "n_test": c.get("n_test", 0),
                "selected_q_percent": sq_serialised,
                "selected_cutoff": sc_serialised,
                "val_realised_sharpe": c.get("val_realised_sharpe", float("nan")),
                "val_realised_annual_pnl": c.get("val_realised_annual_pnl", float("nan")),
                "val_n_trades": c.get("val_n_trades", 0),
                "val_max_dd": c.get("val_max_dd", float("nan")),
                "val_cell_spearman": c.get("val_cell_spearman", float("nan")),
                "test_sharpe": rm.get("sharpe", float("nan")),
                "test_annual_pnl": rm.get("annual_pnl", float("nan")),
                "test_n_trades": rm.get("n_trades", 0),
                "test_max_dd": rm.get("max_dd", float("nan")),
                "test_formal_spearman": sp,
                "test_auc_tp": cd.get("auc_tp_ovr", float("nan")),
                "test_kappa": cd.get("cohen_kappa", float("nan")),
                "h_state": c.get("h_state"),
            }
        )
    summary_df = pd.DataFrame(summary_rows)
    summary_df_for_parquet = summary_df.copy()
    summary_df_for_parquet["quantile_percents"] = summary_df_for_parquet["quantile_percents"].apply(
        lambda x: json.dumps(x)
    )
    summary_df_for_parquet.to_parquet(args.out_dir / "sweep_results.parquet")
    summary_df.to_json(args.out_dir / "sweep_results.json", orient="records", indent=2)

    aggregate = dict(verdict_info)
    aggregate["cross_cell"] = {
        "agree": aggregate_info["agree"],
        "branches": aggregate_info["branches"],
        "aggregate_verdict": aggregate_info["aggregate_verdict"],
    }
    aggregate["baseline_match_report"] = baseline_match_report
    aggregate["arch_control_drift_report"] = arch_control_drift_report
    aggregate["within_eval_drift_per_arch"] = within_eval_drift_per_arch
    aggregate["n_cells_run"] = n_cells_run
    aggregate["regression_diagnostic_s_e"] = {
        "train": train_reg_diag_s_e,
        "val": val_reg_diag_s_e,
        "test": test_reg_diag_s_e,
    }
    aggregate["oof_correlation_diagnostic_s_e"] = oof_corr_diag_s_e
    aggregate["h_c3_per_arch"] = h_c3_per_arch
    aggregate["h_c3_aggregate"] = h_c3_aggregate
    aggregate["top_tail_regime_audit_per_arch"] = top_tail_regime_audit_per_arch
    aggregate["closed_architecture_allowlist"] = {
        "AR1": {
            "name": "hierarchical_two_stage",
            "stage1_admit_percentile_per_pair_val_median": AR1_STAGE1_ADMIT_PERCENTILE,
        },
        "AR2": {"name": "pair_conditioned_specialist_heads", "n_specialists": 20},
        "AR3": {
            "name": "stacked_classifier_regressor_blend",
            "w_s_b": AR3_BLEND_W_SB,
            "w_s_e": AR3_BLEND_W_SE,
        },
        "AR4": {
            "name": "deterministic_regime_split",
            "split_feature": AR4_REGIME_SPLIT_FEATURE,
            "split_percentile_per_pair_val": AR4_REGIME_SPLIT_PERCENTILE,
        },
    }
    if val_select.get("selected") is not None:
        sel = val_select["selected"]
        sel_lite = {
            "cell": {k: (list(v) if isinstance(v, tuple) else v) for k, v in sel["cell"].items()},
            "selected_q_percent": sel["selected_q_percent"],
            "selected_cutoff": sel["selected_cutoff"],
            "val_realised_sharpe": sel["val_realised_sharpe"],
            "val_n_trades": sel["val_n_trades"],
            "test_realised_metrics": sel.get("test_realised_metrics", {}),
            "test_formal_spearman": sel.get("test_formal_spearman", float("nan")),
        }
        aggregate["val_selected"] = sel_lite
    (args.out_dir / "aggregate_summary.json").write_text(
        json.dumps(aggregate, indent=2, default=str), encoding="utf-8"
    )
    (args.out_dir / "val_selected_cell.json").write_text(
        json.dumps(aggregate.get("val_selected", {}), indent=2, default=str),
        encoding="utf-8",
    )
    (args.out_dir / "sanity_probe.json").write_text(
        json.dumps(sanity, indent=2, default=str), encoding="utf-8"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
