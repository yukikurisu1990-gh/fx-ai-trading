"""Stage 28.0b-β A4 Monetisation-Aware Selection eval (second Phase 28 sub-phase).

Implements PR #341 (Phase 28.0b-α design memo) under PR #340 (A4 non-quantile
cell shapes scope amendment) + PR #339 (post-28.0a routing review primary
recommendation) + PR #335 (Phase 28 kickoff).

Mission (PR #341 §1):
  Score-half of monetisation is solved (S-E +0.438, L2 +0.466, L3 +0.459).
  Selection-rule-half is not (6/6 val-selector-picks-baseline pattern).
  A4 fixes the score to S-E and redesigns the rule.

Closed 4-rule allowlist (α-fixed numerics per PR #341 §4; NG#A4-1):
  R1 absolute-threshold (non-quantile per PR #340): trade if S-E score > c;
    c = per-pair val-median (deterministic)
  R2 middle-bulk (quantile range): trade if percentile ∈ [40, 60] global
  R3 per-pair quantile: trade if S-E score >= per-pair 95th percentile
    (top 5% per pair; deterministic)
  R4 top-K per bar (non-quantile per PR #340): at each M5 bar (signal_ts),
    argmax(S-E score); K = 1

Fixed S-E score source (PR #341 §5; NG#A4-1):
  - LightGBM regressor on R7-A; symmetric Huber α=0.9; sample_weight=1
  - Reproduces 27.0d C-se / 27.0f C-se-r7a-replica / 28.0a C-a1-se-r7a-replica
  - L2/L3 NOT admissible

6-cell structure (PR #341 §7; NG#A4-3 mandatory C-a4-top-q-control):
  C-a4-R1, C-a4-R2, C-a4-R3, C-a4-R4 — 4 rule variants (single cell each)
  C-a4-top-q-control — rule-axis null; quantile family {5, 10, 20, 30, 40}
  C-sb-baseline — multiclass S-B; §10 baseline reproduction FAIL-FAST;
    quantile family {5, 10, 20, 30, 40}

D10 single-score-artifact form (PR #341 §7.1; extension of 28.0a 4-artifact):
  1 S-E regressor + 1 C-sb multiclass head = 2 artifacts total.
  Selection rules R1/R2/R3/R4 are deterministic post-fit operations on the
  shared S-E score; no per-rule artifact.

R-T1 formal absorption under A4 frame (PR #341 §3):
  R-T1 carry-forward (PR #334 §11) is absorbed into A4 by PR #341 merge.
  H-C2 = R-T1 elevation under A4 frame resolution.
  No independent R-T1 elevation PR.

H-C2 4-outcome ladder per rule (PR #341 §10.2; precedence row 4 > 1 > 2 > 3):
  Row 4 PARTIAL_DRIFT_TOPQ_REPLICA (checked FIRST per NG#A4-3): C-a4-Rx ≈
    C-a4-top-q-control within tolerance (n_trades ±100 / Sharpe ±5e-3 /
    ann_pnl ±0.5%). Rule had zero effect on monetization.
  Row 1 PASS: H2 PASS (val Sharpe lift ≥ +0.05) AND H1m ≥ +0.30 AND
    H3 ≥ 20,000 trades AND C-sb-baseline reproduction PASS
  Row 2 PARTIAL_SUPPORT: val Sharpe lift ∈ [+0.02, +0.05); others intact
  Row 3 FALSIFIED_RULE_INSUFFICIENT (default): val Sharpe lift < +0.02 OR
    other H-C2 conditions fail

C-sb-baseline reproduction (FAIL-FAST; inherited from 27.0c-α §7.3):
  n_trades=34,626 exact; Sharpe ±1e-4; ann_pnl ±0.5 pip. HALT with
  BaselineMismatchError.

C-a4-top-q-control drift check vs 27.0d C-se / 28.0a control:
  DIAGNOSTIC-ONLY WARN (NOT HALT); inherited tolerances n_trades ±100 /
  Sharpe ±5e-3 / ann_pnl ±0.5% magnitude (PR #341 §9).

Anti-collapse guards (PR #341 §6):
  NG#A4-1: closed 4-rule allowlist; no grid sweep within rule; S-E score
    fixed (no L2/L3 substitution)
  NG#A4-2: per-rule verdict required; aggregate-only not admissible
  NG#A4-3: C-a4-top-q-control control cell mandatory

Row-set policy (A4-specific):
  All 6 cells share R7-A-clean parent row-set (no R7-C row-drop in this
  sub-phase). Fix A row-set isolation contract not exercised.

MANDATORY CLAUSES (1-5 verbatim from 28.0a-β; clause 6 = PR #335 §3 verbatim
+ PR #341 §3 R-T1 absorption note):

1. Phase framing. ADOPT requires H2 PASS + full 8-gate A0-A5 harness.
   H2 PASS = PROMISING_BUT_NEEDS_OOS only; ADOPT_CANDIDATE wall preserved.
2. Diagnostic columns prohibition. Calibration / threshold-sweep /
   directional-comparison / classification-quality / feature-importance /
   per-pair-Sharpe-contribution columns are diagnostic-only. 28.0b
   extension: per-rule traded_mask distribution, R1 c_per_pair / R2
   cutoffs / R3 cutoff_per_pair / R4 per-bar trade count distributions,
   within-eval drift vs top-q control, top-tail regime audit
   (spread_at_signal_pip only; R7-C features NOT computed) are
   diagnostic-only.
3. γ closure preservation. PR #279 is unmodified.
4. Production-readiness preservation. X-v2 OOS gating remains required.
   v9 20-pair (Phase 9.12 tip 79ed1e8) untouched. Phase 22 frozen-OOS
   contract preserved.
5. NG#10 / NG#11 not relaxed.
6. Phase 28 scope. Phase 28 is a structural rebase opened at PR #335
   after R-E routing decision. A0/A1/A2/A3/A4 admissible at kickoff. A1
   exhausted by 28.0a-β closed 3-loss allowlist (PR #338) with revival
   gated by scope amendment. A4 admissible non-quantile cell shapes
   admitted under PR #340 Clause 2 update (R1 absolute-threshold + R4
   top-K per bar). R-T1 carry-forward (PR #334 §11) is formally absorbed
   under A4 sub-phase scope per PR #341 §3; H-C2 = R-T1 elevation under
   A4 frame resolution. R-B / R-T3 carry-forward unaffected. Phase 27
   inertia routes (S-C/S-D/S-E score-axis micro-redesign; R-T2 quantile
   trim alone; R7-C-style regime-statistic-only widening; C-sb-baseline-
   anchored score-only sweeps; R-T1/R-B as Phase 27 extensions) NOT
   admissible. 28.0b sub-phase tests A4 only per PR #339 routing review.

PRODUCTION-MISUSE GUARDS (inherited verbatim):
GUARD 1 — research-not-production: 28.0b features stay in scripts/.
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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage28_0b"
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

# §10 baseline val Sharpe (immutable reference for H-C2 H2 lift threshold)
SECTION_10_BASELINE_VAL_SHARPE = -0.1863  # from PR #335 §10 (verbatim)

NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD = stage27_0d.NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD


# ---------------------------------------------------------------------------
# NEW Phase 28.0b constants (closed 4-rule allowlist; α-fixed per PR #341 §4)
# ---------------------------------------------------------------------------

# R1 absolute-threshold (PR #341 §4.1; per-pair val-median; NG#A4-1)
R1_FIT_PERCENTILE = 50.0  # per-pair val-median

# R2 middle-bulk (PR #341 §4.2; global [40, 60] percentile; NG#A4-1)
R2_PERCENTILE_LO = 40.0
R2_PERCENTILE_HI = 60.0

# R3 per-pair quantile (PR #341 §4.3; top 5% per pair; NG#A4-1)
R3_Q_PER_PAIR = 5.0  # top 5% per pair (np.percentile per pair at 95.0)
R3_FIT_PERCENTILE = 100.0 - R3_Q_PER_PAIR  # 95.0

# R4 top-K per bar (PR #341 §4.4; K=1; NG#A4-1)
R4_K_PER_BAR = 1

# Quantile family for top-q-control + baseline (PR #341 §7; inherited)
QUANTILE_PERCENTS_28_0B: tuple[float, ...] = (5.0, 10.0, 20.0, 30.0, 40.0)

# H-C2 thresholds (PR #341 §10.1)
H2_LIFT_THRESHOLD_PASS = 0.05
H2_LIFT_THRESHOLD_PARTIAL_SUPPORT_LO = 0.02
H1M_PRESERVE_THRESHOLD = 0.30
H3_TRADE_COUNT_THRESHOLD = 20000

# H-C2 outcome labels (PR #341 §10.2)
H_C2_OUTCOME_PASS = "PASS"
H_C2_OUTCOME_PARTIAL_SUPPORT = "PARTIAL_SUPPORT"
H_C2_OUTCOME_FALSIFIED_RULE_INSUFFICIENT = "FALSIFIED_RULE_INSUFFICIENT"
H_C2_OUTCOME_PARTIAL_DRIFT_TOPQ_REPLICA = "PARTIAL_DRIFT_TOPQ_REPLICA"
H_C2_OUTCOME_NEEDS_REVIEW = "NEEDS_REVIEW"

# C-a4-top-q-control drift tolerances vs 27.0d C-se (PR #341 §9; inherited from 27.0f D-AA10)
TOPQ_CONTROL_DRIFT_N_TRADES_TOLERANCE = 100
TOPQ_CONTROL_DRIFT_SHARPE_TOLERANCE = 5e-3
TOPQ_CONTROL_DRIFT_ANN_PNL_FRAC_TOLERANCE = 0.005

# Within-eval drift tolerances (PR #341 §6.3 NG#A4-3; same as top-q control)
WITHIN_EVAL_DRIFT_N_TRADES_TOLERANCE = 100
WITHIN_EVAL_DRIFT_SHARPE_TOLERANCE = 5e-3
WITHIN_EVAL_DRIFT_ANN_PNL_FRAC_TOLERANCE = 0.005

# Top-tail regime audit q values (PR #341 §14 §18; spread_at_signal_pip only)
TOP_TAIL_AUDIT_Q_PERCENTS: tuple[float, ...] = (10.0, 20.0)

# Trade-count budget audit (inherited from 27.0e)
VAL_BASELINE_N_TRADES_AT_Q5 = stage27_0e.VAL_BASELINE_N_TRADES_AT_Q5
TRADE_COUNT_INFLATION_WARN_THRESHOLD = stage27_0e.TRADE_COUNT_INFLATION_WARN_THRESHOLD


# ---------------------------------------------------------------------------
# NEW exceptions
# ---------------------------------------------------------------------------


class BaselineMismatchError(RuntimeError):
    """Raised when C-sb-baseline fails to reproduce 27.0b C-alpha0 baseline.

    Per PR #341 §8 inheritance from 27.0c-α §7.3. FAIL-FAST HALT.
    """


# ---------------------------------------------------------------------------
# R1 / R3 per-pair fit + apply (NEW 28.0b)
# ---------------------------------------------------------------------------


def fit_r1_threshold_per_pair(
    val_df: pd.DataFrame,
    val_score: np.ndarray,
    fit_percentile: float = R1_FIT_PERCENTILE,
) -> dict[str, float]:
    """R1: c = per-pair val-median (deterministic; NG#A4-1).

    Per PR #341 §4.1: trade if S-E score > c where c is the val-fit per-pair
    median (np.percentile at 50.0 per pair). Deterministic; no grid sweep.

    Returns dict[pair_str, c_value] with all 20 pairs filled.
    """
    pair_arr = val_df["pair"].to_numpy()
    score_arr = np.asarray(val_score, dtype=np.float64)
    if len(pair_arr) != len(score_arr):
        raise ValueError(
            f"fit_r1_threshold_per_pair: val_df rows {len(pair_arr)} != "
            f"val_score length {len(score_arr)}"
        )
    c_per_pair: dict[str, float] = {}
    unique_pairs = sorted(set(pair_arr.tolist()))
    for pair in unique_pairs:
        mask = pair_arr == pair
        if mask.sum() == 0:
            c_per_pair[str(pair)] = float("nan")
            continue
        pair_score = score_arr[mask]
        finite_score = pair_score[np.isfinite(pair_score)]
        if len(finite_score) == 0:
            c_per_pair[str(pair)] = float("nan")
            continue
        c_per_pair[str(pair)] = float(np.percentile(finite_score, fit_percentile))
    return c_per_pair


def apply_r1_threshold(
    eval_df: pd.DataFrame,
    eval_score: np.ndarray,
    c_per_pair: dict[str, float],
) -> np.ndarray:
    """R1: trade if eval_score > c_per_pair[pair] (per-row inequality)."""
    pair_arr = eval_df["pair"].to_numpy()
    thresholds = np.array(
        [c_per_pair.get(str(p), float("inf")) for p in pair_arr], dtype=np.float64
    )
    eval_score_arr = np.asarray(eval_score, dtype=np.float64)
    finite_mask = np.isfinite(eval_score_arr) & np.isfinite(thresholds)
    traded_mask = np.zeros(len(eval_score_arr), dtype=bool)
    traded_mask[finite_mask] = eval_score_arr[finite_mask] > thresholds[finite_mask]
    return traded_mask


def fit_r2_middle_bulk_cutoffs(
    val_score: np.ndarray,
    p_lo: float = R2_PERCENTILE_LO,
    p_hi: float = R2_PERCENTILE_HI,
) -> tuple[float, float]:
    """R2: [p_lo, p_hi] = [40, 60] global percentile (deterministic; NG#A4-1)."""
    score_arr = np.asarray(val_score, dtype=np.float64)
    finite_score = score_arr[np.isfinite(score_arr)]
    if len(finite_score) == 0:
        raise ValueError("fit_r2_middle_bulk_cutoffs: no finite val_score values")
    cutoffs = np.percentile(finite_score, [p_lo, p_hi])
    return (float(cutoffs[0]), float(cutoffs[1]))


def apply_r2_middle_bulk(
    eval_score: np.ndarray,
    cutoffs: tuple[float, float],
) -> np.ndarray:
    """R2: trade if cutoffs[0] <= eval_score <= cutoffs[1] (per-row range)."""
    lo, hi = cutoffs
    score_arr = np.asarray(eval_score, dtype=np.float64)
    finite_mask = np.isfinite(score_arr)
    traded_mask = np.zeros(len(score_arr), dtype=bool)
    traded_mask[finite_mask] = (score_arr[finite_mask] >= lo) & (score_arr[finite_mask] <= hi)
    return traded_mask


def fit_r3_per_pair_q95(
    val_df: pd.DataFrame,
    val_score: np.ndarray,
    fit_percentile: float = R3_FIT_PERCENTILE,
) -> dict[str, float]:
    """R3: cutoff = per-pair 95th percentile (top 5% per pair; NG#A4-1)."""
    pair_arr = val_df["pair"].to_numpy()
    score_arr = np.asarray(val_score, dtype=np.float64)
    if len(pair_arr) != len(score_arr):
        raise ValueError(
            f"fit_r3_per_pair_q95: val_df rows {len(pair_arr)} != val_score length {len(score_arr)}"
        )
    cutoff_per_pair: dict[str, float] = {}
    unique_pairs = sorted(set(pair_arr.tolist()))
    for pair in unique_pairs:
        mask = pair_arr == pair
        if mask.sum() == 0:
            cutoff_per_pair[str(pair)] = float("nan")
            continue
        pair_score = score_arr[mask]
        finite_score = pair_score[np.isfinite(pair_score)]
        if len(finite_score) == 0:
            cutoff_per_pair[str(pair)] = float("nan")
            continue
        cutoff_per_pair[str(pair)] = float(np.percentile(finite_score, fit_percentile))
    return cutoff_per_pair


def apply_r3_per_pair_q95(
    eval_df: pd.DataFrame,
    eval_score: np.ndarray,
    cutoff_per_pair: dict[str, float],
) -> np.ndarray:
    """R3: trade if eval_score >= per-pair 95th percentile."""
    pair_arr = eval_df["pair"].to_numpy()
    thresholds = np.array(
        [cutoff_per_pair.get(str(p), float("inf")) for p in pair_arr], dtype=np.float64
    )
    eval_score_arr = np.asarray(eval_score, dtype=np.float64)
    finite_mask = np.isfinite(eval_score_arr) & np.isfinite(thresholds)
    traded_mask = np.zeros(len(eval_score_arr), dtype=bool)
    traded_mask[finite_mask] = eval_score_arr[finite_mask] >= thresholds[finite_mask]
    return traded_mask


def apply_r4_top_k_per_bar(
    eval_df: pd.DataFrame,
    eval_score: np.ndarray,
    k: int = R4_K_PER_BAR,
) -> np.ndarray:
    """R4: at each unique signal_ts (M5 bar), select K=1 highest-score row.

    Per PR #341 §4.4: argmax per signal_ts (K=1; α-fixed; NG#A4-1).
    """
    eval_score_arr = np.asarray(eval_score, dtype=np.float64)
    traded_mask = np.zeros(len(eval_df), dtype=bool)
    if k != 1:
        raise ValueError(f"apply_r4_top_k_per_bar: K={k} != 1 violates NG#A4-1 (α-fixed K=1)")
    # Use pandas groupby idxmax fast path for K=1 (D-BB5)
    df_tmp = pd.DataFrame(
        {
            "signal_ts": eval_df["signal_ts"].to_numpy(),
            "score": eval_score_arr,
            "orig_idx": np.arange(len(eval_df), dtype=np.int64),
        }
    )
    # Exclude rows with non-finite score (cannot argmax)
    df_tmp = df_tmp[np.isfinite(df_tmp["score"])]
    if len(df_tmp) == 0:
        return traded_mask
    # idxmax per group (stable; deterministic on ties via first-seen index)
    winner_indices = df_tmp.loc[
        df_tmp.groupby("signal_ts", sort=False)["score"].idxmax(), "orig_idx"
    ]
    traded_mask[winner_indices.to_numpy()] = True
    return traded_mask


# ---------------------------------------------------------------------------
# Cell construction (PR #341 §7; 6 cells)
# ---------------------------------------------------------------------------


def build_a4_cells() -> list[dict]:
    """28.0b-β formal grid: 6 cells per PR #341 §7.

    NG#A4-3 mandates C-a4-top-q-control as within-eval ablation control.
    Deterministic order per D-BB9: R1 → R2 → R3 → R4 → top-q-control → baseline.
    """
    return [
        {
            "id": "C-a4-R1",
            "picker": "S-E + R1(absolute_threshold_per_pair_median)",
            "score_type": "s_e_r1",
            "feature_set": "r7a",
            "rule": "r1_absolute_threshold",
            "rule_kind": "non_quantile",
            "quantile_percents": (),  # single-cell; no quantile sweep
        },
        {
            "id": "C-a4-R2",
            "picker": "S-E + R2(middle_bulk_40_60)",
            "score_type": "s_e_r2",
            "feature_set": "r7a",
            "rule": "r2_middle_bulk",
            "rule_kind": "quantile_range",
            "quantile_percents": (),
        },
        {
            "id": "C-a4-R3",
            "picker": "S-E + R3(per_pair_q95)",
            "score_type": "s_e_r3",
            "feature_set": "r7a",
            "rule": "r3_per_pair_quantile",
            "rule_kind": "quantile_per_pair",
            "quantile_percents": (),
        },
        {
            "id": "C-a4-R4",
            "picker": "S-E + R4(top_k_per_bar_k1)",
            "score_type": "s_e_r4",
            "feature_set": "r7a",
            "rule": "r4_top_k_per_bar",
            "rule_kind": "non_quantile",
            "quantile_percents": (),
        },
        {
            "id": "C-a4-top-q-control",
            "picker": "S-E(regressor_pred; top-q vanilla)",
            "score_type": "s_e_topq",
            "feature_set": "r7a",
            "rule": "top_q_vanilla",
            "rule_kind": "quantile_topq",
            "quantile_percents": QUANTILE_PERCENTS_28_0B,
        },
        {
            "id": "C-sb-baseline",
            "picker": "S-B(raw_p_tp_minus_p_sl)",
            "score_type": "s_b_raw",
            "feature_set": "r7a",
            "rule": "top_q_baseline",
            "rule_kind": "quantile_topq",
            "quantile_percents": QUANTILE_PERCENTS_28_0B,
        },
    ]


# ---------------------------------------------------------------------------
# C-sb-baseline mismatch check (FAIL-FAST; inherited)
# ---------------------------------------------------------------------------


def check_c_sb_baseline_match(c_sb_baseline_result: dict) -> dict:
    """Validate C-sb-baseline reproduces 27.0b C-alpha0 baseline.

    Per PR #341 §8 inheritance from 27.0c-α §7.3. FAIL-FAST HALT.
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
            "PR #341 §8; failures: " + "; ".join(failures)
        )
    return report


# ---------------------------------------------------------------------------
# C-a4-top-q-control drift check vs 27.0d C-se (DIAGNOSTIC-ONLY WARN)
# ---------------------------------------------------------------------------


def compute_c_a4_top_q_control_drift_check(c_a4_top_q_result: dict) -> dict:
    """DIAGNOSTIC-ONLY WARN; NOT HALT.

    Compares C-a4-top-q-control val-selected test metrics vs 27.0d C-se
    (PR #341 §9). C-a4-top-q-control reproduces 27.0d's C-se with
    sample_weight=1 (D10 single-score-artifact form per α §7.1).
    """
    rm = c_a4_top_q_result.get("test_realised_metrics", {})
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
        abs(baseline_ann_pnl) * TOPQ_CONTROL_DRIFT_ANN_PNL_FRAC_TOLERANCE
        if baseline_ann_pnl is not None and np.isfinite(baseline_ann_pnl)
        else None
    )

    n_trades_within = (
        abs(n_trades_delta) <= TOPQ_CONTROL_DRIFT_N_TRADES_TOLERANCE
        if n_trades_delta is not None
        else False
    )
    sharpe_within = (
        abs(sharpe_delta) <= TOPQ_CONTROL_DRIFT_SHARPE_TOLERANCE
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
# Within-eval drift check per rule (PARTIAL_DRIFT_TOPQ_REPLICA detection)
# ---------------------------------------------------------------------------


def compute_within_eval_topq_drift_check(
    c_a4_rx_result: dict,
    c_a4_top_q_control_result: dict,
) -> dict:
    """Compare a rule cell vs C-a4-top-q-control at val-selected configuration.

    Per PR #341 §10.2 row 4 + NG#A4-3: if C-a4-Rx ≈ C-a4-top-q-control within
    tolerance, flag PARTIAL_DRIFT_TOPQ_REPLICA. Rule change had zero effect.
    """
    if c_a4_rx_result.get("h_state") != "OK" or c_a4_top_q_control_result.get("h_state") != "OK":
        return {
            "all_within_tolerance": False,
            "warn": True,
            "note": "rule cell or top-q-control h_state != OK",
        }
    rm_rx = c_a4_rx_result.get("test_realised_metrics", {})
    rm_ctl = c_a4_top_q_control_result.get("test_realised_metrics", {})
    n_rx = int(rm_rx.get("n_trades", 0))
    n_ctl = int(rm_ctl.get("n_trades", 0))
    sh_rx = float(rm_rx.get("sharpe", float("nan")))
    sh_ctl = float(rm_ctl.get("sharpe", float("nan")))
    ap_rx = float(rm_rx.get("annual_pnl", float("nan")))
    ap_ctl = float(rm_ctl.get("annual_pnl", float("nan")))

    n_trades_delta = n_rx - n_ctl
    sharpe_delta = sh_rx - sh_ctl if (np.isfinite(sh_rx) and np.isfinite(sh_ctl)) else float("nan")
    ann_pnl_delta = ap_rx - ap_ctl if (np.isfinite(ap_rx) and np.isfinite(ap_ctl)) else float("nan")

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
        "n_trades_candidate": int(n_rx),
        "n_trades_control": int(n_ctl),
        "n_trades_delta": int(n_trades_delta),
        "n_trades_within_tolerance": bool(n_trades_within),
        "sharpe_candidate": float(sh_rx),
        "sharpe_control": float(sh_ctl),
        "sharpe_delta": float(sharpe_delta) if np.isfinite(sharpe_delta) else float("nan"),
        "sharpe_within_tolerance": bool(sharpe_within),
        "ann_pnl_candidate": float(ap_rx),
        "ann_pnl_control": float(ap_ctl),
        "ann_pnl_delta": float(ann_pnl_delta) if np.isfinite(ann_pnl_delta) else float("nan"),
        "ann_pnl_tolerance_abs": ann_pnl_tolerance_abs,
        "ann_pnl_within_tolerance": bool(ann_pnl_within),
        "all_within_tolerance": all_within,
        "warn": all_within,  # WARN means "zero effect detected"
    }


# ---------------------------------------------------------------------------
# H-C2 4-outcome ladder resolver (PR #341 §10.2; precedence row 4 first)
# ---------------------------------------------------------------------------


def compute_h_c2_outcome_per_rule(
    c_a4_rx_result: dict,
    baseline_match_report: dict,
    topq_drift_report_vs_control: dict,
) -> dict:
    """Resolve 1 of 4 H-C2 outcomes per rule (precedence row 4 > 1 > 2 > 3).

    PARTIAL_DRIFT_TOPQ_REPLICA checked first per NG#A4-3.
    """
    cell_id = c_a4_rx_result.get("cell", {}).get("id", "unknown")
    if c_a4_rx_result.get("h_state") != "OK":
        return {
            "cell_id": cell_id,
            "outcome": H_C2_OUTCOME_NEEDS_REVIEW,
            "row_matched": 0,
            "reason": f"h_state={c_a4_rx_result.get('h_state')}",
        }

    # Row 4 precedence: PARTIAL_DRIFT_TOPQ_REPLICA
    drift_within = topq_drift_report_vs_control.get("all_within_tolerance", False)
    if drift_within:
        return {
            "cell_id": cell_id,
            "outcome": H_C2_OUTCOME_PARTIAL_DRIFT_TOPQ_REPLICA,
            "row_matched": 4,
            "reason": (
                "rule change had zero effect on monetization (drift vs top-q-control "
                "within tolerance); analogous to 27.0f H-B6 / 28.0a PARTIAL_DRIFT_R7A_REPLICA"
            ),
            "evidence": {
                "drift_n_trades_delta": topq_drift_report_vs_control.get("n_trades_delta"),
                "drift_sharpe_delta": topq_drift_report_vs_control.get("sharpe_delta"),
                "drift_ann_pnl_delta": topq_drift_report_vs_control.get("ann_pnl_delta"),
            },
        }

    val_sharpe = float(c_a4_rx_result.get("val_realised_sharpe", float("nan")))
    val_n = int(c_a4_rx_result.get("val_n_trades", 0))
    # Cell-level Spearman (val); fallback to test_formal_spearman
    qb = c_a4_rx_result.get("quantile_best", {}) or {}
    cell_spearman_val = qb.get("val", {}).get("spearman_score_vs_pnl", float("nan"))
    if not np.isfinite(cell_spearman_val):
        cell_spearman_val = float(c_a4_rx_result.get("val_cell_spearman", float("nan")))
    if not np.isfinite(cell_spearman_val):
        cell_spearman_val = float(c_a4_rx_result.get("test_formal_spearman", float("nan")))

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

    # Row 1 PASS
    if h1m_pass and h2_pass and h3_pass and baseline_pass:
        return {
            "cell_id": cell_id,
            "outcome": H_C2_OUTCOME_PASS,
            "row_matched": 1,
            "reason": "all four H-C2 conditions satisfied",
            "evidence": evidence,
        }

    # Row 2 PARTIAL_SUPPORT
    h2_partial = (
        np.isfinite(sharpe_lift)
        and H2_LIFT_THRESHOLD_PARTIAL_SUPPORT_LO <= sharpe_lift < H2_LIFT_THRESHOLD_PASS
    )
    if h2_partial and h1m_pass and h3_pass and baseline_pass:
        return {
            "cell_id": cell_id,
            "outcome": H_C2_OUTCOME_PARTIAL_SUPPORT,
            "row_matched": 2,
            "reason": (
                f"val Sharpe lift {sharpe_lift:+.4f} in [+0.02, +0.05); other H-C2 "
                "conditions intact"
            ),
            "evidence": evidence,
        }

    # Row 3 FALSIFIED_RULE_INSUFFICIENT (default)
    return {
        "cell_id": cell_id,
        "outcome": H_C2_OUTCOME_FALSIFIED_RULE_INSUFFICIENT,
        "row_matched": 3,
        "reason": (f"val Sharpe lift {sharpe_lift:+.4f} < +0.02 OR other H-C2 conditions failed"),
        "evidence": evidence,
    }


def compute_h_c2_aggregate_verdict(per_rule_outcomes: list[dict]) -> dict:
    """Aggregate H-C2 verdict per PR #341 §10.3 (R-T1 absorption resolution)."""
    outcomes = [o.get("outcome") for o in per_rule_outcomes]
    has_pass = H_C2_OUTCOME_PASS in outcomes
    has_partial_support = H_C2_OUTCOME_PARTIAL_SUPPORT in outcomes
    all_partial_drift = all(o == H_C2_OUTCOME_PARTIAL_DRIFT_TOPQ_REPLICA for o in outcomes)
    all_falsified = all(
        o
        in {
            H_C2_OUTCOME_FALSIFIED_RULE_INSUFFICIENT,
            H_C2_OUTCOME_PARTIAL_DRIFT_TOPQ_REPLICA,
        }
        for o in outcomes
    )

    if has_pass:
        verdict = "SPLIT_VERDICT_ROUTE_TO_REVIEW"
        routing = (
            "1+ rule produced H-C2 PASS at the C-a4-Rx cell; PROMISING_BUT_NEEDS_OOS "
            "candidate. ADOPT_CANDIDATE wall preserved (H2 PASS ≤ PROMISING_BUT_NEEDS_OOS "
            "per Clause 1). R-T1 elevated and supported under A4 frame resolution."
        )
    elif has_partial_support:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        routing = (
            "1+ rule PARTIAL_SUPPORT (sub-threshold Sharpe lift); no rule PASS. "
            "Route to A0 (architecture redesign) OR A2 (target redesign). "
            "R-T1 partially elevated under A4 frame."
        )
    elif all_partial_drift:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        routing = (
            "All 4 rules PARTIAL_DRIFT_TOPQ_REPLICA — rule change does not move the "
            "score regardless of structural difference. Strong support for H-B9 (seam "
            "exhausted at this architecture). Route to A0 architecture redesign. "
            "R-T1 falsified under A4 absorption."
        )
    elif all_falsified:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        routing = (
            "All 4 rules FALSIFIED_RULE_INSUFFICIENT or PARTIAL_DRIFT — selection-rule "
            "axis exhausted. Route to A0 architecture redesign. R-T1 falsified under "
            "A4 absorption."
        )
    else:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        routing = (
            "no rule produced PASS or PARTIAL_SUPPORT; route to A0 / A2. R-T1 "
            "falsified under A4 absorption."
        )

    return {
        "aggregate_verdict": verdict,
        "routing_implication": routing,
        "per_rule_outcomes": [
            {
                "cell_id": o.get("cell_id"),
                "outcome": o.get("outcome"),
                "row_matched": o.get("row_matched"),
            }
            for o in per_rule_outcomes
        ],
        "has_pass": bool(has_pass),
        "has_partial_support": bool(has_partial_support),
        "all_partial_drift": bool(all_partial_drift),
        "r_t1_absorption_status": (
            "PASS_under_A4"
            if has_pass
            else "PARTIAL_under_A4"
            if has_partial_support
            else "FALSIFIED_under_A4"
        ),
    }


# ---------------------------------------------------------------------------
# Top-tail regime audit (DIAGNOSTIC-ONLY; spread_at_signal_pip only)
# ---------------------------------------------------------------------------


def compute_top_tail_regime_audit_for_a4(
    val_score: np.ndarray,
    val_features: pd.DataFrame,
    q_list: tuple[float, ...] = TOP_TAIL_AUDIT_Q_PERCENTS,
) -> dict:
    """DIAGNOSTIC-ONLY; top-tail audit on val using spread_at_signal_pip.

    R7-C features (f5a / f5b / f5c) NOT computed (out of scope per Clause 6).
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
        top_mask = val_score >= cutoff
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
# Per-rule mask-based evaluation (NEW dispatcher; rule cells use traded_mask)
# ---------------------------------------------------------------------------


def evaluate_rule_cell_28_0b(
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
    traded_mask_val: np.ndarray,
    traded_mask_test: np.ndarray,
    selected_cutoff_repr: object,
    feature_importance_diag: dict,
) -> dict:
    """Evaluate a rule cell (R1/R2/R3/R4) given pre-computed traded_masks.

    PR #341 §7: rule cells are single-configuration (no quantile sweep).
    Returns a dict matching evaluate_cell_28_0a shape with quantile_all=[].
    """
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

    # Val metrics under the rule mask (use inherited compute_8_gate_from_pnls for
    # annualisation consistency with quantile cells / evaluate_quantile_family_custom)
    valid_pnl_mask_val = np.isfinite(pnl_val_full)
    traded_val = traded_mask_val & valid_pnl_mask_val
    val_traded_pnl = pnl_val_full[traded_val]
    val_n_trades = int(traded_val.sum())
    val_gate_block = compute_8_gate_from_pnls(val_traded_pnl)
    val_block = val_gate_block["metrics"]

    # Cell-level Spearman on val (over the cell's traded rows; informative for H1m check)
    if val_n_trades >= 2:
        val_score_traded = val_score[traded_val]
        from scipy.stats import spearmanr  # local import; matches 26.0c usage

        sp_val_result = spearmanr(val_score_traded, val_traded_pnl, nan_policy="omit")
        val_cell_spearman = (
            float(sp_val_result.correlation)
            if hasattr(sp_val_result, "correlation")
            else float(sp_val_result.statistic)
        )
        if not np.isfinite(val_cell_spearman):
            val_cell_spearman = float("nan")
    else:
        val_cell_spearman = float("nan")

    # Test metrics under the rule mask (test touched once)
    valid_pnl_mask_test = np.isfinite(pnl_test_full)
    traded_test = traded_mask_test & valid_pnl_mask_test
    test_traded_pnl = pnl_test_full[traded_test]
    gate_block = compute_8_gate_from_pnls(test_traded_pnl)

    # Classification diag uses test_score against test_label (DIAGNOSTIC-ONLY)
    cls_diag = compute_classification_diagnostics(
        test_label, test_raw_probs, test_score, pnl_test_full
    )
    formal_spearman = cls_diag.get("spearman_score_vs_pnl", float("nan"))

    # Pair / direction breakdown on test under rule mask
    test_df_aligned = test_df.reset_index(drop=True)
    val_df_aligned = val_df.reset_index(drop=True)
    in_trade = traded_test
    by_pair: dict[str, int] = {}
    by_direction: dict[str, int] = {"long": 0, "short": 0}
    for i in np.flatnonzero(in_trade):
        p = str(test_df_aligned["pair"].iloc[i])
        d = str(test_df_aligned["direction"].iloc[i])
        by_pair[p] = by_pair.get(p, 0) + 1
        by_direction[d] = by_direction.get(d, 0) + 1

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

    # selected_q_percent: rule cells are non-quantile; use numeric sentinel 0.0 so the
    # inherited select_cell_validation_only (which does `-q` in its sort key) accepts
    # the value. The actual selection driver is sharpe / annual_pnl, not q.
    rule_q_sentinel = 0.0
    return {
        "cell": cell,
        "score_type": score_type,
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
        "quantile_all": [],  # rule cells have no quantile sweep
        "quantile_best": {
            "q_percent": rule_q_sentinel,
            "cutoff": selected_cutoff_repr,
            "val": {**val_block, "spearman_score_vs_pnl": val_cell_spearman},
            "test": {k: v for k, v in gate_block["metrics"].items() if k != "realised_pnls"},
        },
        "selected_q_percent": rule_q_sentinel,
        "selected_cutoff": (
            float(selected_cutoff_repr) if isinstance(selected_cutoff_repr, (int, float)) else None
        ),
        "val_realised_sharpe": float(val_block["sharpe"]),
        "val_realised_annual_pnl": float(val_block["annual_pnl"]),
        "val_n_trades": int(val_n_trades),
        "val_max_dd": float(val_block["max_dd"]),
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


def _compute_realised_metrics_from_pnls(pnls: np.ndarray, span_years: float) -> dict:
    """Compute realised metrics (sharpe / annual_pnl / max_dd / n_trades) from a PnL array."""
    pnls_arr = np.asarray(pnls, dtype=np.float64)
    pnls_arr = pnls_arr[np.isfinite(pnls_arr)]
    n = int(len(pnls_arr))
    if n == 0:
        return {
            "sharpe": float("nan"),
            "annual_pnl": float("nan"),
            "max_dd": float("nan"),
            "n_trades": 0,
        }
    mean_pnl = float(pnls_arr.mean())
    std_pnl = float(pnls_arr.std(ddof=0))
    annual_pnl = mean_pnl * n / max(span_years, 1e-9)
    # Sharpe approximated as mean / std × sqrt(n_per_year)
    if std_pnl > 0 and span_years > 0:
        sharpe = (mean_pnl / std_pnl) * np.sqrt(n / span_years)
    else:
        sharpe = float("nan")
    cumsum = np.cumsum(pnls_arr)
    peak = np.maximum.accumulate(cumsum)
    drawdown = cumsum - peak
    max_dd = float(drawdown.min()) if len(drawdown) > 0 else 0.0
    return {
        "sharpe": float(sharpe),
        "annual_pnl": float(annual_pnl),
        "max_dd": float(max_dd),
        "n_trades": int(n),
    }


# ---------------------------------------------------------------------------
# Quantile cell evaluation (inherited shape from 28.0a; for top-q-control + baseline)
# ---------------------------------------------------------------------------


def evaluate_quantile_cell_28_0b(
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
    """Evaluate a quantile cell (top-q-control / baseline) — inherited from 28.0a shape."""
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

    quantile_percents = tuple(cell.get("quantile_percents", QUANTILE_PERCENTS_28_0B))
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
    traded_mask_test = test_score >= best_q_record["cutoff"]
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
    traded_mask_val = val_score >= best_q_record["cutoff"]
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
            "val": {k: v for k, v in best_q_record["val"].items() if k != "realised_pnls"},
            "test": {k: v for k, v in best_q_record["test"].items() if k != "realised_pnls"},
        },
        "selected_q_percent": float(best_q_record["q_percent"]),
        "selected_cutoff": float(best_q_record["cutoff"]),
        "val_realised_sharpe": float(best_q_record["val"]["sharpe"]),
        "val_realised_annual_pnl": float(best_q_record["val"]["annual_pnl"]),
        "val_n_trades": int(best_q_record["val"]["n_trades"]),
        "val_max_dd": float(best_q_record["val"]["max_dd"]),
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
    keys = ("id", "picker", "score_type", "feature_set", "rule")
    return " ".join(f"{k}={cell.get(k)}" for k in keys)


# ---------------------------------------------------------------------------
# Per-pair runtime (inherited from 28.0a; pip + bid/ask arrays)
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
# SanityProbe (items 1-6 inherited; NEW items 7-10 for 4 rules)
# ---------------------------------------------------------------------------


def run_sanity_probe_28_0b(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    pairs: list[str],
    days: int = SPAN_DAYS,
    pnl_train_full: np.ndarray | None = None,
    r1_c_per_pair: dict[str, float] | None = None,
    r2_cutoffs: tuple[float, float] | None = None,
    r3_cutoff_per_pair: dict[str, float] | None = None,
    r4_traded_mask_val: np.ndarray | None = None,
    r4_n_unique_signal_ts_val: int | None = None,
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
    top_tail_regime_audit_per_rule: dict[str, dict] | None = None,
    cell_definitions: list[dict] | None = None,
    trade_count_budget_audit_top_q: list[dict] | None = None,
) -> dict:
    """28.0b SanityProbe (items 1-6 inherited; items 7-10 NEW for rules)."""
    print("\n=== 28.0b SANITY PROBE (per PR #341 §14 §15.5) ===")
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
            print(
                f"    {name}: n={stats['n']} mean={stats['mean']:+.3f} "
                f"p5={stats['p5']:+.3f} p50={stats['p50']:+.3f} p95={stats['p95']:+.3f}"
            )

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
            print(f"    {name}.{col}: n={n} NaN={nan_n} ({rate:.3%})")
    out["r7a_new_feature_nan_rate"] = nan_rate_diag

    # Item 6: R7-A positivity check
    print("  R7-A positivity check on TRAIN:")
    positivity_diag: dict = {}
    for col in NUMERIC_FEATURES_R7A:
        arr = train_df[col].to_numpy(dtype=np.float64)
        finite = arr[np.isfinite(arr)]
        if len(finite) == 0:
            continue
        stats = {
            "n": int(len(finite)),
            "mean": float(finite.mean()),
            "p5": float(np.quantile(finite, 0.05)),
            "p50": float(np.quantile(finite, 0.5)),
            "p95": float(np.quantile(finite, 0.95)),
            "min": float(finite.min()),
            "max": float(finite.max()),
        }
        positivity_diag[col] = stats
        print(
            f"    {col}: n={stats['n']} mean={stats['mean']:+.3f} "
            f"p5={stats['p5']:+.3f} p50={stats['p50']:+.3f} p95={stats['p95']:+.3f} "
            f"min={stats['min']:+.3f} max={stats['max']:+.3f}"
        )
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

    # Item 7 NEW: R1 c_per_pair distribution
    if r1_c_per_pair is not None:
        out["r1_c_per_pair"] = {p: float(v) for p, v in r1_c_per_pair.items()}
        missing_pairs = [p for p in pairs if p not in r1_c_per_pair]
        if missing_pairs:
            raise SanityProbeError(
                f"R1 c_per_pair missing pairs: {missing_pairs[:5]} (NG#A4-1; expected 20 pairs)"
            )
        non_finite_pairs = [p for p, v in r1_c_per_pair.items() if not np.isfinite(v)]
        if non_finite_pairs:
            raise SanityProbeError(f"R1 c_per_pair non-finite for pairs: {non_finite_pairs[:5]}")
        c_values = np.array(list(r1_c_per_pair.values()), dtype=np.float64)
        print(
            f"  R1 c_per_pair (val-median): n_pairs={len(c_values)} "
            f"mean={c_values.mean():+.4f} p5={np.quantile(c_values, 0.05):+.4f} "
            f"p95={np.quantile(c_values, 0.95):+.4f}"
        )

    # Item 8 NEW: R2 cutoffs sanity
    if r2_cutoffs is not None:
        lo, hi = r2_cutoffs
        if not (np.isfinite(lo) and np.isfinite(hi) and lo < hi):
            raise SanityProbeError(
                f"R2 cutoffs invalid: lo={lo} hi={hi} (expected finite and lo < hi)"
            )
        out["r2_cutoffs"] = {"lo": float(lo), "hi": float(hi)}
        print(f"  R2 cutoffs (global [40, 60] percentile): lo={lo:+.4f} hi={hi:+.4f}")

    # Item 9 NEW: R3 cutoff_per_pair distribution
    if r3_cutoff_per_pair is not None:
        out["r3_cutoff_per_pair"] = {p: float(v) for p, v in r3_cutoff_per_pair.items()}
        missing_pairs = [p for p in pairs if p not in r3_cutoff_per_pair]
        if missing_pairs:
            raise SanityProbeError(
                f"R3 cutoff_per_pair missing pairs: {missing_pairs[:5]} (NG#A4-1)"
            )
        non_finite_pairs = [p for p, v in r3_cutoff_per_pair.items() if not np.isfinite(v)]
        if non_finite_pairs:
            raise SanityProbeError(
                f"R3 cutoff_per_pair non-finite for pairs: {non_finite_pairs[:5]}"
            )
        cutoff_values = np.array(list(r3_cutoff_per_pair.values()), dtype=np.float64)
        print(
            f"  R3 cutoff_per_pair (val-percentile 95.0): n_pairs={len(cutoff_values)} "
            f"mean={cutoff_values.mean():+.4f} p5={np.quantile(cutoff_values, 0.05):+.4f} "
            f"p95={np.quantile(cutoff_values, 0.95):+.4f}"
        )

    # Item 10 NEW: R4 K=1 verification on val
    if r4_traded_mask_val is not None and r4_n_unique_signal_ts_val is not None:
        n_traded_val = int(np.asarray(r4_traded_mask_val).sum())
        if n_traded_val != r4_n_unique_signal_ts_val:
            raise SanityProbeError(
                f"R4 K=1 verification failed: traded_mask sum={n_traded_val} != "
                f"n_unique_signal_ts={r4_n_unique_signal_ts_val} (NG#A4-1; expected K=1 "
                "to produce exactly n_unique_signal_ts trades)"
            )
        out["r4_k1_verification"] = {
            "n_traded_val": n_traded_val,
            "n_unique_signal_ts_val": r4_n_unique_signal_ts_val,
            "pass": True,
        }
        print(
            f"  R4 K=1 verification: traded_mask sum = n_unique_signal_ts = {n_traded_val} (PASS)"
        )

    # Top-tail audit per rule
    if top_tail_regime_audit_per_rule is not None:
        out["top_tail_regime_audit_per_rule"] = top_tail_regime_audit_per_rule
        print("  top-tail regime audit (spread_at_signal_pip only; DIAGNOSTIC-ONLY):")
        for rname, audit in top_tail_regime_audit_per_rule.items():
            for per_q in audit.get("per_q", []):
                print(
                    f"    {rname} q={per_q['q_percent']:.1f}: "
                    f"mean_spread={per_q['top_mean_spread']:+.3f} "
                    f"(Δ vs pop {per_q['delta_mean_vs_population']:+.3f}); "
                    f"n_top={per_q['n_top']}"
                )

    # OOF + regression diagnostic (S-E only; single)
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

    if trade_count_budget_audit_top_q is not None:
        out["trade_count_budget_audit_top_q"] = trade_count_budget_audit_top_q

    if cell_definitions is not None:
        out["cell_definitions"] = [{k: v for k, v in c.items()} for c in cell_definitions]

    print("=== SANITY PROBE: PASS ===")
    return out


# ---------------------------------------------------------------------------
# Eval report writer (25 sections; inherited from 28.0a-α §11 + A4 adaptations)
# ---------------------------------------------------------------------------


def write_eval_report_28_0b(
    report_path: Path,
    cell_results: list[dict],
    val_select: dict,
    verdict_info: dict,
    aggregate_info: dict,
    baseline_match_report: dict,
    top_q_control_drift_report: dict,
    h_c2_per_rule: list[dict],
    h_c2_aggregate: dict,
    within_eval_drift_per_rule: dict[str, dict],
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
    top_tail_regime_audit_per_rule: dict[str, dict],
    r1_c_per_pair_summary: dict | None,
    r2_cutoffs: tuple[float, float] | None,
    r3_cutoff_per_pair_summary: dict | None,
    r4_k1_verification: dict | None,
    trade_count_budget_audit_top_q: list[dict] | None,
) -> None:
    """Write 25-section eval_report.md (inherited shape; PR #341 §14)."""
    lines: list[str] = []
    t_min, t70, t85, t_max = t_range
    lines.append("# Phase 28.0b-β — A4 Monetisation-Aware Selection eval report")
    lines.append("")
    lines.append("**Sub-phase**: 28.0b-β")
    lines.append(
        "**Design memo**: PR #341 "
        "(`phase28_0b_alpha_a4_monetisation_aware_selection_design_memo.md`)"
    )
    lines.append(
        "**Scope amendment**: PR #340 (`phase28_scope_amendment_a4_non_quantile_cells.md`)"
    )
    lines.append("**Routing**: PR #339 (post-28.0a routing review; A4 primary)")
    lines.append("")
    # §1 Executive summary
    lines.append("## 1. Executive summary")
    lines.append("")
    lines.append("Per-rule H-C2 outcome ladder (PR #341 §10.2; precedence row 4 > 1 > 2 > 3):")
    lines.append("")
    lines.append("| Rule | Outcome | Row | Reason |")
    lines.append("|---|---|---|---|")
    for o in h_c2_per_rule:
        lines.append(
            f"| {o.get('cell_id', '-')} | {o.get('outcome', '-')} | "
            f"{o.get('row_matched', '-')} | "
            f"{o.get('reason', '-')[:90]} |"
        )
    lines.append("")
    lines.append(f"**Aggregate verdict**: {h_c2_aggregate.get('aggregate_verdict')}")
    lines.append(f"**Routing implication**: {h_c2_aggregate.get('routing_implication')}")
    lines.append(
        f"**R-T1 absorption status under A4**: {h_c2_aggregate.get('r_t1_absorption_status')}"
    )
    lines.append("")
    lines.append(
        f"**C-sb-baseline reproduction**: "
        f"{'PASS' if baseline_match_report.get('all_match') else 'FAIL'}"
    )
    lines.append(
        f"**C-a4-top-q-control drift vs 27.0d C-se**: "
        f"all_within_tolerance={top_q_control_drift_report.get('all_within_tolerance')} "
        f"(warn={top_q_control_drift_report.get('warn')}; DIAGNOSTIC-ONLY)"
    )
    lines.append("")

    # §2 Cells overview
    lines.append("## 2. Cells overview")
    lines.append("")
    lines.append("| Cell | Picker | Score | Feature set | Rule | Rule kind |")
    lines.append("|---|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        lines.append(
            f"| {cell['id']} | {cell.get('picker', '-')} | {cell.get('score_type', '-')} | "
            f"{cell.get('feature_set', '-')} | {cell.get('rule', '-')} | "
            f"{cell.get('rule_kind', '-')} |"
        )
    lines.append("")

    # §3 Row-set / drop stats
    lines.append("## 3. Row-set policy / drop stats")
    lines.append("")
    lines.append(
        "**A4-specific row-set policy** (PR #341 §7.2): all 6 cells share the "
        "R7-A-clean parent row-set; no R7-C row-drop is applied in this sub-phase. "
        "Fix A row-set isolation contract is not exercised here. PR #340 Clause 2 "
        "amendment admits non-quantile cells (R1 / R4) within A4 scope."
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
    if r1_c_per_pair_summary:
        lines.append(
            f"- R1 c_per_pair (val-median): n_pairs={r1_c_per_pair_summary.get('n_pairs')} "
            f"mean={r1_c_per_pair_summary.get('mean', float('nan')):+.4f}"
        )
    if r2_cutoffs:
        lo, hi = r2_cutoffs
        lines.append(f"- R2 cutoffs (global [40, 60]): lo={lo:+.4f} hi={hi:+.4f}")
    if r3_cutoff_per_pair_summary:
        lines.append(
            f"- R3 cutoff_per_pair (val-percentile 95): "
            f"n_pairs={r3_cutoff_per_pair_summary.get('n_pairs')} "
            f"mean={r3_cutoff_per_pair_summary.get('mean', float('nan')):+.4f}"
        )
    if r4_k1_verification:
        lines.append(
            f"- R4 K=1 verification: traded_mask sum = n_unique_signal_ts = "
            f"{r4_k1_verification.get('n_traded_val')} (PASS)"
        )
    lines.append("")

    # §5 OOF correlation diagnostic
    lines.append("## 5. OOF correlation diagnostic — S-E only (DIAGNOSTIC-ONLY)")
    lines.append("")
    if oof_corr_diag_s_e:
        p = oof_corr_diag_s_e.get("aggregate_pearson", float("nan"))
        sp = oof_corr_diag_s_e.get("aggregate_spearman", float("nan"))
        lines.append(f"- S-E aggregate: pearson={p:+.4f} spearman={sp:+.4f}")
        lines.append(
            "- Rule cells (R1/R2/R3/R4) share the same S-E score; per-rule OOF is "
            "irrelevant (rules are deterministic post-fit operations)."
        )
    lines.append("")

    # §6 Regression diagnostic — S-E only
    lines.append("## 6. Regression diagnostic — S-E only (DIAGNOSTIC-ONLY)")
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

    # §7 Quantile-family per cell (top-q-control + baseline only; rules are single)
    lines.append("## 7. Per-cell results")
    lines.append("")
    for c in cell_results:
        cell = c["cell"]
        lines.append(f"### {cell['id']} ({cell.get('picker', '-')})")
        lines.append("")
        if cell.get("rule_kind", "").startswith("quantile_topq"):
            lines.append(
                "| q% | cutoff | val_sharpe | val_n | test_sharpe | test_n | test_ann_pnl |"
            )
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
        else:
            qb = c.get("quantile_best", {}) or {}
            vv = qb.get("val", {})
            tt = qb.get("test", {})
            cell_sp = vv.get("spearman_score_vs_pnl", float("nan"))
            lines.append(f"- val Sharpe={vv.get('sharpe', float('nan')):+.4f}")
            lines.append(f"- val n_trades={vv.get('n_trades', 0)}")
            lines.append(f"- val cell Spearman(score, pnl)={cell_sp:+.4f}")
            lines.append(f"- test Sharpe={tt.get('sharpe', float('nan')):+.4f}")
            lines.append(f"- test n_trades={tt.get('n_trades', 0)}")
            lines.append(f"- test ann_pnl={tt.get('annual_pnl', float('nan')):+.1f}")
        lines.append("")

    # §8 Val-selection
    lines.append("## 8. Val-selection (cell\\*, q\\* or rule-cell\\*)")
    lines.append("")
    sel = val_select.get("selected")
    if sel is None:
        lines.append("no valid val-selected cell")
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
    lines.append("## 11. Within-eval ablation drift (per rule vs C-a4-top-q-control)")
    lines.append("")
    lines.append(
        "| Rule | n_trades Δ | within | Sharpe Δ | within | ann_pnl Δ | within | all_within |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for rname, d in (within_eval_drift_per_rule or {}).items():
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
            f"| {rname} | {n_d} | {n_w} | {sh_d_str} | {sh_w} | {ap_d_str} | {ap_w} | {all_w} |"
        )
    lines.append("")

    # §11b C-a4-top-q-control drift vs 27.0d C-se (DIAGNOSTIC-ONLY)
    lines.append("## 11b. C-a4-top-q-control drift vs 27.0d C-se (DIAGNOSTIC-ONLY WARN)")
    lines.append("")
    cd = top_q_control_drift_report
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
    lines.append("## 12. Feature importance — S-E regressor (DIAGNOSTIC-ONLY)")
    lines.append("")
    if isinstance(feature_importance_s_e, dict) and "items" in feature_importance_s_e:
        for item in feature_importance_s_e["items"]:
            lines.append(
                f"- {item.get('feature', '-')}: gain={item.get('gain', float('nan')):+.1f}"
            )
    else:
        lines.append(f"(unavailable: {feature_importance_s_e})")
    lines.append("")

    # §13 H-C2 outcome row binding per rule (= R-T1 elevation under A4 frame resolution)
    lines.append(
        "## 13. H-C2 outcome row binding per rule (= R-T1 elevation under A4 frame resolution)"
    )
    lines.append("")
    lines.append(
        "Per PR #341 §3 / §10 / §14: H-C2 = R-T1 elevation under A4 frame. The "
        "per-rule outcomes below resolve the R-T1 carry-forward inside Phase 28."
    )
    lines.append("")
    lines.append(
        "| Rule | Outcome | Row | Sharpe lift vs §10 | val Sharpe | val n | cell Spearman | Notes |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for o in h_c2_per_rule:
        ev = o.get("evidence", {}) if isinstance(o.get("evidence"), dict) else {}
        lift = ev.get("sharpe_lift_absolute", float("nan"))
        vs = ev.get("val_sharpe", float("nan"))
        vn = ev.get("val_n_trades", "-")
        sp = ev.get("cell_spearman_val", float("nan"))
        lift_str = f"{lift:+.4f}" if isinstance(lift, float) and np.isfinite(lift) else str(lift)
        vs_str = f"{vs:+.4f}" if isinstance(vs, float) and np.isfinite(vs) else str(vs)
        sp_str = f"{sp:+.4f}" if isinstance(sp, float) and np.isfinite(sp) else str(sp)
        lines.append(
            f"| {o.get('cell_id', '-')} | {o.get('outcome', '-')} | "
            f"{o.get('row_matched', '-')} | "
            f"{lift_str} | {vs_str} | {vn} | {sp_str} | "
            f"{o.get('reason', '-')[:60]} |"
        )
    lines.append("")
    lines.append(f"**Aggregate H-C2 verdict**: {h_c2_aggregate.get('aggregate_verdict')}")
    lines.append(f"**Routing**: {h_c2_aggregate.get('routing_implication')}")
    lines.append(f"**R-T1 absorption status**: {h_c2_aggregate.get('r_t1_absorption_status')}")
    lines.append("")

    # §14 Trade-count budget audit
    lines.append("## 14. Trade-count budget audit — C-a4-top-q-control")
    lines.append("")
    if trade_count_budget_audit_top_q:
        lines.append("| q% | n_trades | inflation |")
        lines.append("|---|---|---|")
        for item in trade_count_budget_audit_top_q:
            lines.append(
                f"| {item.get('q_percent', float('nan')):.1f} | "
                f"{item.get('n_trades', 0)} | "
                f"{item.get('inflation_factor', float('nan')):.3f}x |"
            )
    lines.append("")
    lines.append(
        "Note: rule cells (R1 / R2 / R3 / R4) are single-cell; n_trades is reported "
        "directly in §7 above."
    )
    lines.append("")

    # §15 Pair concentration per cell
    lines.append("## 15. Pair concentration per cell (val-selected)")
    lines.append("")
    lines.append("| Cell | val top-3 pairs | val Herfindahl | test top-3 | test Herfindahl |")
    lines.append("|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        vc = c.get("val_concentration", {}) or {}
        tc = c.get("test_concentration", {}) or {}
        vc_top = vc.get("top_pairs", "-")
        vc_h = vc.get("herfindahl", float("nan"))
        tc_top = tc.get("top_pairs", "-")
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

    # §18 Top-tail regime audit per rule (DIAGNOSTIC-ONLY)
    lines.append(
        "## 18. Top-tail regime audit per rule (DIAGNOSTIC-ONLY; spread_at_signal_pip only)"
    )
    lines.append("")
    lines.append(
        "**Note**: R7-C f5a/f5b/f5c features are NOT computed in this sub-phase "
        "(out of scope per Clause 6). Audit uses `spread_at_signal_pip` (R7-A) only."
    )
    lines.append("")
    for rname, audit in (top_tail_regime_audit_per_rule or {}).items():
        pop = audit.get("population", {})
        lines.append(f"### {rname}")
        lines.append(
            f"- population mean spread = "
            f"{pop.get('mean_spread_at_signal_pip', float('nan')):+.3f} "
            f"(p50 {pop.get('p50_spread_at_signal_pip', float('nan')):+.3f})"
        )
        for per_q in audit.get("per_q", []):
            lines.append(
                f"- q={per_q['q_percent']:.1f}: top mean="
                f"{per_q['top_mean_spread']:+.3f} "
                f"(Δ {per_q['delta_mean_vs_population']:+.3f}); "
                f"n_top={per_q['n_top']}"
            )
        lines.append("")

    # §19 R7-A new-feature NaN check
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

    # §20 Realised-PnL distribution by class on TRAIN
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

    # §21 Predicted PnL distribution — S-E
    lines.append("## 21. Predicted PnL distribution — S-E (DIAGNOSTIC)")
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
    lines.append("- PR #339 — Phase 28 post-28.0a routing review (A4 primary)")
    lines.append("- PR #340 — Phase 28 scope amendment A4 non-quantile cells")
    lines.append("- PR #341 — Phase 28.0b-α A4 design memo (this sub-phase α)")
    lines.append("- PR #325 — Phase 27.0d-β S-E regression (score backbone source)")
    lines.append("- PR #332 — Phase 27.0f-β (within-eval ablation template)")
    lines.append("- PR #334 — Phase 27 closure memo (R-T1 carry-forward source)")
    lines.append("- PR #338 — Phase 28.0a-β A1 objective redesign (6-eval picture)")
    lines.append("- PR #279 — γ closure")
    lines.append("- Phase 22 frozen-OOS contract")
    lines.append("- Phase 9.12 production v9 tip 79ed1e8 (untouched)")
    lines.append("")

    # §23 Caveats
    lines.append("## 23. Caveats")
    lines.append("")
    lines.append(
        "- All test-set metrics outside the val-selected per-cell configuration are "
        "DIAGNOSTIC-ONLY and excluded from the formal H-C2 verdict."
    )
    lines.append(
        "- H2 PASS = PROMISING_BUT_NEEDS_OOS only. ADOPT_CANDIDATE wall preserved per "
        "Clause 1. NG#10 / NG#11 not relaxed."
    )
    lines.append(
        "- R-T1 absorption: per PR #341 §3, R-T1 carry-forward is formally absorbed "
        "under A4 sub-phase scope. §13 outcome row binding = R-T1 elevation "
        "resolution. No independent R-T1 elevation."
    )
    lines.append(
        "- S-E score source fixed per NG#A4-1; L2 / L3 NOT admissible. Score-axis "
        "variation requires memo amendment to revive A1."
    )
    lines.append(
        "- Top-tail regime audit uses `spread_at_signal_pip` only; R7-C features "
        "are out of scope per Clause 6."
    )
    lines.append("")

    # §24 Cross-validation re-fits diagnostic
    lines.append("## 24. Cross-validation re-fits diagnostic (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append(
        "5-fold OOF (seed=42) on S-E score backbone (inherited from 27.0d). Rule "
        "cells (R1/R2/R3/R4) are deterministic post-fit operations and share the "
        "same OOF diagnostic via S-E. Aggregate Pearson / Spearman are reported in §5."
    )
    lines.append("")

    # §25 Sub-phase verdict snapshot
    lines.append("## 25. Sub-phase verdict snapshot")
    lines.append("")
    lines.append("- per-rule outcomes:")
    for o in h_c2_per_rule:
        cid = o.get("cell_id", "-")
        oc = o.get("outcome", "-")
        rm = o.get("row_matched", "-")
        lines.append(f"  - {cid}: {oc} (row {rm})")
    lines.append(f"- aggregate verdict: {h_c2_aggregate.get('aggregate_verdict')}")
    lines.append(f"- routing implication: {h_c2_aggregate.get('routing_implication')}")
    lines.append(
        f"- R-T1 absorption status under A4: {h_c2_aggregate.get('r_t1_absorption_status')}"
    )
    lines.append(
        f"- C-sb-baseline reproduction: "
        f"{'PASS' if baseline_match_report.get('all_match') else 'FAIL'}"
    )
    lines.append(
        f"- C-a4-top-q-control drift vs 27.0d C-se: "
        f"all_within_tolerance={top_q_control_drift_report.get('all_within_tolerance')} "
        f"(WARN-only)"
    )
    lines.append("")
    lines.append("*End of `artifacts/stage28_0b/eval_report.md`.*")
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

    print(f"=== Stage 28.0b-β A4 Monetisation-Aware Selection eval ({len(args.pairs)} pairs) ===")
    print(
        f"K_FAV={K_FAV} K_ADV={K_ADV} H_M1={H_M1_BARS} | "
        f"top-q-control quantile_percents={list(QUANTILE_PERCENTS_28_0B)}"
    )
    print(f"R7-A FIXED (4 features): {list(ALL_FEATURES_R7A)}")
    print(
        f"Closed 4-rule allowlist (α-fixed; NG#A4-1): "
        f"R1 c=per-pair val-{R1_FIT_PERCENTILE}th-pct, "
        f"R2 [{R2_PERCENTILE_LO},{R2_PERCENTILE_HI}] global, "
        f"R3 top {R3_Q_PER_PAIR}% per pair, "
        f"R4 K={R4_K_PER_BAR}/bar"
    )
    print(f"Fixed S-E score: symmetric Huber α={HUBER_ALPHA} on R7-A; sample_weight=1 (NG#A4-1)")
    print(f"OOF (DIAGNOSTIC-ONLY): {OOF_N_FOLDS} folds, seed={OOF_SEED}")

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

    # 5. Sanity probe (pre-fit; items 1-6 only; rule items 7-10 deferred)
    sanity = run_sanity_probe_28_0b(
        train_df,
        val_df,
        test_df,
        pair_runtime_map,
        args.pairs,
        days=args.days,
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
    print("Precomputing realised PnL per row on R7-A-clean parent (train + val + test)...")
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

    # 8. Build labels
    train_label = build_l1_labels_for_dataframe(train_df).to_numpy()
    val_label = build_l1_labels_for_dataframe(val_df).to_numpy()
    test_label = build_l1_labels_for_dataframe(test_df).to_numpy()

    # 9. 5-fold OOF on S-E score (DIAGNOSTIC-ONLY; single)
    print("Running 5-fold OOF regression on S-E (DIAGNOSTIC-ONLY; seed=42)...")
    fold_idx = make_oof_fold_assignment(len(pnl_train_for_reg), n_folds=OOF_N_FOLDS, seed=OOF_SEED)
    x_train_r7a = train_df_for_reg[list(ALL_FEATURES_R7A)]
    t0 = time.time()
    oof_preds_s_e = fit_oof_regression_diagnostic(x_train_r7a, pnl_train_for_reg, fold_idx)
    oof_corr_diag_s_e = compute_oof_correlation_diagnostic(
        oof_preds_s_e, pnl_train_for_reg, fold_idx
    )
    print(
        f"  OOF (S-E): pearson={oof_corr_diag_s_e['aggregate_pearson']:+.4f} "
        f"spearman={oof_corr_diag_s_e['aggregate_spearman']:+.4f} ({time.time() - t0:.1f}s)"
    )

    # 10. Fit S-E regressor + multiclass head (D10 single-score-artifact form)
    print(
        "Fitting S-E regressor (R7-A; symmetric Huber α=0.9; sample_weight=1; "
        "shared across 4 rules + top-q-control)..."
    )
    t0 = time.time()
    regressor_se = build_pipeline_lightgbm_regression_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        regressor_se.fit(x_train_r7a, pnl_train_for_reg)
    val_pred_se = compute_picker_score_s_e(regressor_se, val_df[list(ALL_FEATURES_R7A)])
    test_pred_se = compute_picker_score_s_e(regressor_se, test_df[list(ALL_FEATURES_R7A)])
    train_pred_se = compute_picker_score_s_e(regressor_se, x_train_r7a)
    fi_s_e = compute_feature_importance_diagnostic(regressor_se)
    print(f"  S-E regressor fit + predict: {time.time() - t0:.1f}s")

    print("Fitting C-sb-baseline multiclass head (R7-A only)...")
    t0 = time.time()
    multiclass_pipeline = build_pipeline_lightgbm_multiclass_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        multiclass_pipeline.fit(x_train_r7a, train_label[~nan_pnl_mask])
    final_step = multiclass_pipeline.steps[-1][1]
    classes = np.asarray(getattr(final_step, "classes_", np.arange(NUM_CLASSES)))
    val_raw_probs_native = multiclass_pipeline.predict_proba(val_df[list(ALL_FEATURES_R7A)])
    test_raw_probs_native = multiclass_pipeline.predict_proba(test_df[list(ALL_FEATURES_R7A)])
    val_raw_probs = np.zeros((len(val_raw_probs_native), NUM_CLASSES), dtype=np.float64)
    test_raw_probs = np.zeros((len(test_raw_probs_native), NUM_CLASSES), dtype=np.float64)
    for col_idx, cls in enumerate(classes):
        cls_int = int(cls)
        val_raw_probs[:, cls_int] = val_raw_probs_native[:, col_idx]
        test_raw_probs[:, cls_int] = test_raw_probs_native[:, col_idx]
    print(f"  multiclass fit + predict_proba: {time.time() - t0:.1f}s")

    # 11. Regression diagnostic for S-E
    train_reg_diag_s_e = compute_regression_diagnostic(pnl_train_for_reg, train_pred_se)
    val_reg_diag_s_e = compute_regression_diagnostic(pnl_val_full, val_pred_se)
    test_reg_diag_s_e = compute_regression_diagnostic(pnl_test_full, test_pred_se)

    # 12. Compute val_score / test_score (S-E for all 4 rules + top-q-control)
    val_score_se = val_pred_se
    test_score_se = test_pred_se
    val_score_s_b_raw = compute_picker_score_s_b_raw(val_raw_probs)
    test_score_s_b_raw = compute_picker_score_s_b_raw(test_raw_probs)

    # 13. Fit + apply 4 rules on S-E score
    print("Fitting + applying 4-rule allowlist on S-E score...")
    t0 = time.time()

    # R1: per-pair val-median
    r1_c_per_pair = fit_r1_threshold_per_pair(val_df, val_score_se)
    mask_val_r1 = apply_r1_threshold(val_df, val_score_se, r1_c_per_pair)
    mask_test_r1 = apply_r1_threshold(test_df, test_score_se, r1_c_per_pair)

    # R2: global [40, 60]
    r2_cutoffs = fit_r2_middle_bulk_cutoffs(val_score_se)
    mask_val_r2 = apply_r2_middle_bulk(val_score_se, r2_cutoffs)
    mask_test_r2 = apply_r2_middle_bulk(test_score_se, r2_cutoffs)

    # R3: per-pair top 5%
    r3_cutoff_per_pair = fit_r3_per_pair_q95(val_df, val_score_se)
    mask_val_r3 = apply_r3_per_pair_q95(val_df, val_score_se, r3_cutoff_per_pair)
    mask_test_r3 = apply_r3_per_pair_q95(test_df, test_score_se, r3_cutoff_per_pair)

    # R4: top-K=1 per signal_ts
    mask_val_r4 = apply_r4_top_k_per_bar(val_df, val_score_se, k=R4_K_PER_BAR)
    mask_test_r4 = apply_r4_top_k_per_bar(test_df, test_score_se, k=R4_K_PER_BAR)
    r4_n_unique_signal_ts_val = int(val_df["signal_ts"].nunique())
    print(
        f"  rules fit + apply: {time.time() - t0:.1f}s "
        f"(R1 n_trades_val={int(mask_val_r1.sum())} test={int(mask_test_r1.sum())}; "
        f"R2 val={int(mask_val_r2.sum())} test={int(mask_test_r2.sum())}; "
        f"R3 val={int(mask_val_r3.sum())} test={int(mask_test_r3.sum())}; "
        f"R4 val={int(mask_val_r4.sum())} test={int(mask_test_r4.sum())})"
    )

    # 14. Top-tail regime audit per rule (DIAGNOSTIC-ONLY; spread only)
    print("Computing top-tail regime audit per rule (DIAGNOSTIC-ONLY)...")
    top_tail_regime_audit_per_rule = {
        "R1": compute_top_tail_regime_audit_for_a4(val_score_se, val_df, TOP_TAIL_AUDIT_Q_PERCENTS),
        "R2": compute_top_tail_regime_audit_for_a4(val_score_se, val_df, TOP_TAIL_AUDIT_Q_PERCENTS),
        "R3": compute_top_tail_regime_audit_for_a4(val_score_se, val_df, TOP_TAIL_AUDIT_Q_PERCENTS),
        "R4": compute_top_tail_regime_audit_for_a4(val_score_se, val_df, TOP_TAIL_AUDIT_Q_PERCENTS),
        "top_q_control": compute_top_tail_regime_audit_for_a4(
            val_score_se, val_df, TOP_TAIL_AUDIT_Q_PERCENTS
        ),
    }

    # Trade-count budget audit on top-q-control
    trade_count_budget_audit_top_q = compute_trade_count_budget_audit(
        val_score_se, QUANTILE_PERCENTS_28_0B
    )

    # Predicted PnL distribution for S-E (DIAGNOSTIC)
    predicted_pnl_distribution_s_e: dict[str, dict] = {}
    for split_name, pred in [
        ("train", train_pred_se),
        ("val", val_pred_se),
        ("test", test_pred_se),
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

    # 15. Build cells
    cells = build_a4_cells()

    # 16. Updated sanity probe with post-fit info (items 7-10)
    sanity_post = run_sanity_probe_28_0b(
        train_df,
        val_df,
        test_df,
        pair_runtime_map,
        args.pairs,
        days=args.days,
        pnl_train_full=pnl_train_full,
        r1_c_per_pair=r1_c_per_pair,
        r2_cutoffs=r2_cutoffs,
        r3_cutoff_per_pair=r3_cutoff_per_pair,
        r4_traded_mask_val=mask_val_r4,
        r4_n_unique_signal_ts_val=r4_n_unique_signal_ts_val,
        val_pred_s_e=val_pred_se,
        test_pred_s_e=test_pred_se,
        train_pred_s_e=train_pred_se,
        fold_idx=fold_idx,
        oof_corr_diag_s_e=oof_corr_diag_s_e,
        train_reg_diag_s_e=train_reg_diag_s_e,
        val_reg_diag_s_e=val_reg_diag_s_e,
        test_reg_diag_s_e=test_reg_diag_s_e,
        feature_importance_s_e=fi_s_e,
        train_drop_for_nan_pnl_count=nan_pnl_count,
        top_tail_regime_audit_per_rule=top_tail_regime_audit_per_rule,
        cell_definitions=cells,
        trade_count_budget_audit_top_q=trade_count_budget_audit_top_q,
    )
    sanity = sanity_post

    # 17. Per-cell evaluation (deterministic order per D-BB9)
    print("Per-cell evaluation...")
    n_cells_run = len(cells)
    cell_results: list[dict] = []
    for i, cell in enumerate(cells):
        t_cell = time.time()
        score_type = cell["score_type"]
        if score_type == "s_e_r1":
            result = evaluate_rule_cell_28_0b(
                cell,
                train_df,
                val_df,
                test_df,
                train_label,
                val_label,
                test_label,
                val_raw_probs,
                test_raw_probs,
                val_score_se,
                test_score_se,
                pnl_val_full,
                pnl_test_full,
                mask_val_r1,
                mask_test_r1,
                selected_cutoff_repr=f"per_pair_val_median (n_pairs={len(r1_c_per_pair)})",
                feature_importance_diag=fi_s_e,
            )
        elif score_type == "s_e_r2":
            result = evaluate_rule_cell_28_0b(
                cell,
                train_df,
                val_df,
                test_df,
                train_label,
                val_label,
                test_label,
                val_raw_probs,
                test_raw_probs,
                val_score_se,
                test_score_se,
                pnl_val_full,
                pnl_test_full,
                mask_val_r2,
                mask_test_r2,
                selected_cutoff_repr=f"global_[{r2_cutoffs[0]:.4f},{r2_cutoffs[1]:.4f}]",
                feature_importance_diag=fi_s_e,
            )
        elif score_type == "s_e_r3":
            result = evaluate_rule_cell_28_0b(
                cell,
                train_df,
                val_df,
                test_df,
                train_label,
                val_label,
                test_label,
                val_raw_probs,
                test_raw_probs,
                val_score_se,
                test_score_se,
                pnl_val_full,
                pnl_test_full,
                mask_val_r3,
                mask_test_r3,
                selected_cutoff_repr=(
                    f"per_pair_val_pctile_{R3_FIT_PERCENTILE} (n_pairs={len(r3_cutoff_per_pair)})"
                ),
                feature_importance_diag=fi_s_e,
            )
        elif score_type == "s_e_r4":
            result = evaluate_rule_cell_28_0b(
                cell,
                train_df,
                val_df,
                test_df,
                train_label,
                val_label,
                test_label,
                val_raw_probs,
                test_raw_probs,
                val_score_se,
                test_score_se,
                pnl_val_full,
                pnl_test_full,
                mask_val_r4,
                mask_test_r4,
                selected_cutoff_repr=f"top_K{R4_K_PER_BAR}_per_signal_ts",
                feature_importance_diag=fi_s_e,
            )
        elif score_type == "s_e_topq":
            result = evaluate_quantile_cell_28_0b(
                cell,
                train_df,
                val_df,
                test_df,
                train_label,
                val_label,
                test_label,
                val_raw_probs,
                test_raw_probs,
                val_score_se,
                test_score_se,
                pnl_val_full,
                pnl_test_full,
                fi_s_e,
            )
        elif score_type == "s_b_raw":
            result = evaluate_quantile_cell_28_0b(
                cell,
                train_df,
                val_df,
                test_df,
                train_label,
                val_label,
                test_label,
                val_raw_probs,
                test_raw_probs,
                val_score_s_b_raw,
                test_score_s_b_raw,
                pnl_val_full,
                pnl_test_full,
                compute_feature_importance_diagnostic(multiclass_pipeline),
            )
        else:
            raise ValueError(f"Unknown score_type: {score_type}")

        cell_results.append(result)
        rm = result.get("test_realised_metrics", {})
        sp = result.get("test_formal_spearman", float("nan"))
        sq = result.get("selected_q_percent")
        sq_str = f"q*={sq}" if sq is not None else "single-cell"
        print(
            f"  cell {i + 1}/{n_cells_run} {cell['id']} | {sq_str} | "
            f"val_sharpe={result.get('val_realised_sharpe', float('nan')):+.3f} "
            f"val_n={result.get('val_n_trades', 0):>6} | "
            f"test_sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"test_n={rm.get('n_trades', 0):>6} "
            f"test_sp={sp:+.4f} | ({time.time() - t_cell:.1f}s)"
        )

    # 18. C-sb-baseline match check (FAIL-FAST per PR #341 §8)
    print("\n=== C-sb-baseline match check (per PR #341 §8) ===")
    c_sb_baseline = next((c for c in cell_results if c["cell"]["id"] == "C-sb-baseline"), None)
    if c_sb_baseline is None:
        raise BaselineMismatchError("C-sb-baseline result not present — wiring failure")
    if c_sb_baseline.get("h_state") != "OK":
        raise BaselineMismatchError(
            f"C-sb-baseline did not produce OK result: h_state={c_sb_baseline.get('h_state')}"
        )
    baseline_match_report = check_c_sb_baseline_match(c_sb_baseline)
    print(f"  baseline match: {baseline_match_report['all_match']}")
    for key in ("n_trades", "sharpe", "ann_pnl"):
        print(
            f"    {key}: observed={baseline_match_report[f'{key}_observed']} "
            f"baseline={baseline_match_report[f'{key}_baseline']} "
            f"delta={baseline_match_report[f'{key}_delta']:+.6g} "
            f"match={baseline_match_report[f'{key}_match']}"
        )

    # 19. C-a4-top-q-control drift vs 27.0d C-se (DIAGNOSTIC-ONLY WARN)
    print("\n=== C-a4-top-q-control drift check vs 27.0d C-se (DIAGNOSTIC-ONLY WARN) ===")
    c_a4_top_q_control = next(
        (c for c in cell_results if c["cell"]["id"] == "C-a4-top-q-control"), None
    )
    if c_a4_top_q_control is None or c_a4_top_q_control.get("h_state") != "OK":
        top_q_control_drift_report = {
            "source": "n/a",
            "warn": True,
            "all_within_tolerance": False,
            "note": "C-a4-top-q-control not present or h_state != OK",
        }
    else:
        top_q_control_drift_report = compute_c_a4_top_q_control_drift_check(c_a4_top_q_control)
        if top_q_control_drift_report["warn"]:
            warnings.warn(
                f"C-a4-top-q-control drift vs 27.0d C-se exceeds tolerance "
                f"(n_trades={top_q_control_drift_report.get('n_trades_within_tolerance')}, "
                f"Sharpe={top_q_control_drift_report.get('sharpe_within_tolerance')}, "
                f"ann_pnl={top_q_control_drift_report.get('ann_pnl_within_tolerance')}); "
                "DIAGNOSTIC-ONLY WARN per PR #341 §9 (NOT HALT)",
                UserWarning,
                stacklevel=2,
            )
        print(f"  drift WARN: {top_q_control_drift_report.get('warn')}")
        print(f"  all_within_tolerance: {top_q_control_drift_report.get('all_within_tolerance')}")

    # 20. Within-eval drift per rule (PARTIAL_DRIFT_TOPQ_REPLICA detection)
    print("\n=== Within-eval ablation drift per rule (vs C-a4-top-q-control) ===")
    within_eval_drift_per_rule: dict[str, dict] = {}
    for rname, cell_id in [
        ("R1", "C-a4-R1"),
        ("R2", "C-a4-R2"),
        ("R3", "C-a4-R3"),
        ("R4", "C-a4-R4"),
    ]:
        rule_cell = next((c for c in cell_results if c["cell"]["id"] == cell_id), None)
        if rule_cell is None or c_a4_top_q_control is None:
            within_eval_drift_per_rule[rname] = {
                "all_within_tolerance": False,
                "warn": True,
                "note": "rule cell or top-q-control missing",
            }
        else:
            within_eval_drift_per_rule[rname] = compute_within_eval_topq_drift_check(
                rule_cell, c_a4_top_q_control
            )
        d = within_eval_drift_per_rule[rname]
        nd = d.get("n_trades_delta", "-")
        shd = d.get("sharpe_delta", float("nan"))
        apd = d.get("ann_pnl_delta", float("nan"))
        shd_str = f"{shd:+.4e}" if isinstance(shd, float) and np.isfinite(shd) else str(shd)
        apd_str = f"{apd:+.3f}" if isinstance(apd, float) and np.isfinite(apd) else str(apd)
        print(
            f"  {rname}: all_within_tolerance={d.get('all_within_tolerance')} "
            f"(n_trades_Δ={nd}, Sharpe_Δ={shd_str}, ann_pnl_Δ={apd_str})"
        )

    # 21. Val-selection + cross-cell verdict
    val_select = select_cell_validation_only(cell_results)
    verdict_info = assign_verdict(val_select.get("selected"))
    aggregate_info = aggregate_cross_cell_verdict(cell_results)

    print("")
    print("=== Val-selected (cell*, q* or rule-cell*) ===")
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

    print("")
    print(f"=== Cross-cell aggregate: {aggregate_info['aggregate_verdict']} ===")

    # 22. H-C2 4-outcome per rule
    print("\n=== H-C2 4-outcome ladder per rule ===")
    h_c2_per_rule: list[dict] = []
    for rname, cell_id in [
        ("R1", "C-a4-R1"),
        ("R2", "C-a4-R2"),
        ("R3", "C-a4-R3"),
        ("R4", "C-a4-R4"),
    ]:
        rule_cell = next((c for c in cell_results if c["cell"]["id"] == cell_id), None)
        if rule_cell is None:
            h_c2_per_rule.append(
                {
                    "cell_id": cell_id,
                    "outcome": H_C2_OUTCOME_NEEDS_REVIEW,
                    "row_matched": 0,
                    "reason": "cell missing",
                }
            )
            continue
        outcome = compute_h_c2_outcome_per_rule(
            rule_cell, baseline_match_report, within_eval_drift_per_rule.get(rname, {})
        )
        h_c2_per_rule.append(outcome)
        print(
            f"  {rname}: {outcome.get('outcome')} (row {outcome.get('row_matched')}) "
            f"— {outcome.get('reason', '-')[:80]}"
        )

    # 23. Aggregate H-C2 verdict (R-T1 absorption resolution)
    h_c2_aggregate = compute_h_c2_aggregate_verdict(h_c2_per_rule)
    print(f"\n=== Aggregate H-C2 verdict: {h_c2_aggregate.get('aggregate_verdict')} ===")
    print(f"=== Routing implication: {h_c2_aggregate.get('routing_implication')} ===")
    print(
        f"=== R-T1 absorption status under A4: {h_c2_aggregate.get('r_t1_absorption_status')} ==="
    )

    if args.no_write:
        print("\n--no-write set; skipping artifact write.")
        return 0

    target_pnl_distribution = sanity.get("target_pnl_distribution_train", {})

    # 24. Sanity probe summaries for eval_report
    r1_c_summary: dict | None = None
    if r1_c_per_pair:
        c_values = np.array(list(r1_c_per_pair.values()), dtype=np.float64)
        r1_c_summary = {
            "n_pairs": int(len(c_values)),
            "mean": float(c_values.mean()),
            "p5": float(np.quantile(c_values, 0.05)),
            "p95": float(np.quantile(c_values, 0.95)),
        }
    r3_cutoff_summary: dict | None = None
    if r3_cutoff_per_pair:
        c_values = np.array(list(r3_cutoff_per_pair.values()), dtype=np.float64)
        r3_cutoff_summary = {
            "n_pairs": int(len(c_values)),
            "mean": float(c_values.mean()),
            "p5": float(np.quantile(c_values, 0.05)),
            "p95": float(np.quantile(c_values, 0.95)),
        }
    r4_verif = sanity.get("r4_k1_verification")

    # 25. Write 25-section eval report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report_28_0b(
        report_path,
        cell_results,
        val_select,
        verdict_info,
        aggregate_info,
        baseline_match_report,
        top_q_control_drift_report,
        h_c2_per_rule,
        h_c2_aggregate,
        within_eval_drift_per_rule,
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
        top_tail_regime_audit_per_rule,
        r1_c_summary,
        r2_cutoffs,
        r3_cutoff_summary,
        r4_verif,
        trade_count_budget_audit_top_q,
    )
    print(f"\nReport: {report_path}")

    # 26. Persist artifacts
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
                "rule": cell.get("rule", "-"),
                "rule_kind": cell.get("rule_kind", "-"),
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
    aggregate["top_q_control_drift_report"] = top_q_control_drift_report
    aggregate["within_eval_drift_per_rule"] = within_eval_drift_per_rule
    aggregate["n_cells_run"] = n_cells_run
    aggregate["regression_diagnostic_s_e"] = {
        "train": train_reg_diag_s_e,
        "val": val_reg_diag_s_e,
        "test": test_reg_diag_s_e,
    }
    aggregate["oof_correlation_diagnostic_s_e"] = oof_corr_diag_s_e
    aggregate["h_c2_per_rule"] = h_c2_per_rule
    aggregate["h_c2_aggregate"] = h_c2_aggregate
    aggregate["top_tail_regime_audit_per_rule"] = top_tail_regime_audit_per_rule
    aggregate["closed_rule_allowlist"] = {
        "R1": {"name": "absolute_threshold_per_pair_median", "percentile": R1_FIT_PERCENTILE},
        "R2": {
            "name": "middle_bulk_global",
            "percentile_lo": R2_PERCENTILE_LO,
            "percentile_hi": R2_PERCENTILE_HI,
        },
        "R3": {"name": "per_pair_top_q", "q_per_pair": R3_Q_PER_PAIR},
        "R4": {"name": "top_k_per_bar", "k": R4_K_PER_BAR},
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
