"""Stage 27.0c-β S-D Calibrated EV eval (second Phase 27 sub-phase).

Implements the binding contract from PR #320 (Phase 27.0c-α design memo)
under the Phase 27 scope from PR #316 (clause 6 NEW for Phase 27).
Selected via post-27.0b routing review #319 R-A — targets the H-B3
hypothesis (structural mis-alignment of multiclass head with realised PnL).

R7-A feature family FIXED:
  pair + direction + atr_at_signal_pip + spread_at_signal_pip

S-D score-objective (per 27.0c-α §3.1):
  S-D(row) = P_cal(TP|row) · Ê[PnL|TP]
          + P_cal(SL|row) · Ê[PnL|SL]
          + P_cal(TIME|row) · Ê[PnL|TIME]

Where:
  - P_cal(c|row) = isotonic-calibrated, per-row sum-to-1 renormalised
    class probability (calibration policy §5)
  - Ê[PnL|c] = constant per-class conditional-PnL estimator from train-only
    realised PnL (estimation policy §4)
  - PnL throughout = inherited _compute_realised_barrier_pnl (D-1 binding;
    bid/ask executable)

5-fold OOF protocol (per 27.0c-α §4.3):
  1. Deterministic 5-fold split on train via np.random.default_rng(42)
     permutation + np.array_split (no stratification per D-I2)
  2. For each fold f: fit fold-f head on (train \\ fold f); predict on
     fold f → OOF probabilities
  3. After all 5 folds: every train row has OOF (P(TP), P(SL), P(TIME))
  4. Fit isotonic per class on (OOF P(c), 1{realised=c}) — sklearn
     IsotonicRegression(out_of_bounds='clip', y_min=0.0, y_max=1.0) per D-I3
  5. Compute Ê[PnL|c] = mean realised PnL of full-train rows where
     realised class = c (full-train per design memo §4.3 step 4)
  6. Diagnostic OOF Ê[PnL|c]: mean over OOF-fold-aggregated rows by
     realised class (DIAGNOSTIC-ONLY; §10 sanity probe)
  7. Refit multiclass head on full train (production head for val/test)

Cells (per 27.0c-α §7.1; D-I8):
  - C-sd: S-D calibrated EV (substantive cell)
  - C-sb-baseline: S-B = P(TP) - P(SL) on the SAME refit-on-full-train
    head (raw probs; NOT calibrated) — inheritance-chain sanity check
    reproducing 27.0b C-alpha0 / R6-new-A C02 baseline

C-sb-baseline must reproduce 27.0b C-alpha0 baseline within tolerance OR
HALT with BaselineMismatchError before C-sd verdict assignment (per D-I9):
  - n_trades=34,626 (exact match required)
  - Sharpe=-0.1732 (|delta| ≤ 1e-4)
  - ann_pnl=-204,664.4 (|delta| ≤ 0.5 pip)

D10 amendment (per 27.0c-α §7.5): "single model fit" now means
ONE multiclass head + ONE isotonic triple + ONE estimator triple,
shared across both cells. No per-cell re-fit.

3-LAYER SELECTION-OVERFIT GUARD (per 27.0c-α §13 verbatim binding):
  S-D's three trainable artifacts (multiclass head P, isotonic calibrators
  per class, conditional-PnL constants Ê[PnL|class]) are ALL fit on
  train-only data, using a single 5-fold OOF assignment that is reused
  across all three artifacts. Val data is used ONLY for cutoff selection
  (quantile-of-val q* per cell). Test data is touched exactly once at the
  val-selected (cell*, q*). Any deviation is a NG#10 violation.

D-1 BINDING (inherited): formal realised-PnL = _compute_realised_barrier_pnl
(bid/ask executable). Mid-to-mid PnL appears in sanity probe only.

MANDATORY CLAUSES (clauses 1-5 verbatim; clause 6 = Phase 27 kickoff §8 verbatim):

1. Phase framing. ADOPT requires both H2 PASS and the full 8-gate A0-A5
   harness.
2. Diagnostic columns prohibition. Calibration / threshold-sweep /
   directional-comparison / classification-quality / feature-importance /
   per-pair-Sharpe-contribution columns are diagnostic-only. ADOPT_CANDIDATE
   routing must not depend on any single one of them. *[27.0c extends:
   conditional-PnL estimator constants and calibration reliability diagrams
   are diagnostic-only]*
3. γ closure preservation. Phase 24 γ hard-close (PR #279) is unmodified.
4. Production-readiness preservation. X-v2 OOS gating remains required
   before any production deployment. Production v9 20-pair (Phase 9.12
   closure tip 79ed1e8) remains untouched. Phase 22 frozen-OOS contract
   remains required for any ADOPT_CANDIDATE → production transition.
5. NG#10 / NG#11 not relaxed.
6. Phase 27 scope. Phase 27's primary axes are (a) feature widening
   beyond the Phase 26 R6-new-A 2-feature allowlist via per-family
   closed allowlists and (b) score-objective redesign beyond P(TP) /
   P(TP)-P(SL). Phase 27 is NOT a Phase 25 feature-axis sweep revival.
   R7-A (inherited from PR #311) is admissible at kickoff; R7-B / R7-C
   each require a SEPARATE Phase 27 scope-amendment PR; R7-D and
   R7-Other are NOT admissible under any Phase 27 scope amendment
   currently on the table. Score-objectives S-A / S-B / S-C are
   admissible at kickoff for formal evaluation. S-D (calibrated EV) is
   admissible in principle but deferred — it requires its own design memo
   specifying per-class conditional-PnL estimation, calibration policy,
   and selection-overfit handling before any formal eval. S-E
   (regression-on-realised-PnL) requires a SEPARATE scope-amendment PR
   (model-class change). S-Other is NOT admissible. Phase 26 deferred-
   not-foreclosed items (L-4 / R6-new-B / R6-new-C / Phase 25 F4 / F6 /
   F5-d / F5-e) are NOT subsumed by Phase 27; they remain under their
   original phase semantics.

PRODUCTION-MISUSE GUARDS (inherited verbatim from 26.0a-α §5.1):
GUARD 1 — research-not-production: 27.0c features stay in scripts/.
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
from datetime import UTC, datetime
from pathlib import Path

# Windows console may default to cp932; force UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage27_0c"
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

# Inherited constants
PAIRS_20 = stage23_0a.PAIRS_20
load_m1_ba = stage23_0a.load_m1_ba
pip_size_for = stage23_0a.pip_size_for

_compute_realised_barrier_pnl = stage25_0b._compute_realised_barrier_pnl
compute_8_gate_metrics = stage25_0b.compute_8_gate_metrics
gate_matrix = stage25_0b.gate_matrix
PROHIBITED_DIAGNOSTIC_COLUMNS = stage25_0b.PROHIBITED_DIAGNOSTIC_COLUMNS
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
compute_picker_score_diff = stage26_0c.compute_picker_score_diff
evaluate_quantile_family = stage26_0c.evaluate_quantile_family
compute_8_gate_from_pnls = stage26_0c.compute_8_gate_from_pnls
compute_classification_diagnostics = stage26_0c.compute_classification_diagnostics
compute_mid_to_mid_pnl_diagnostic = stage26_0c.compute_mid_to_mid_pnl_diagnostic
assign_verdict = stage26_0c.assign_verdict
aggregate_cross_cell_verdict = stage26_0c.aggregate_cross_cell_verdict
select_cell_validation_only = stage26_0c.select_cell_validation_only
SanityProbeError = stage26_0c.SanityProbeError
_eval_threshold_mask = stage26_0c._eval_threshold_mask

build_pipeline_lightgbm_multiclass_widened = stage26_0d.build_pipeline_lightgbm_multiclass_widened
drop_rows_with_missing_new_features = stage26_0d.drop_rows_with_missing_new_features
compute_feature_importance_diagnostic = stage26_0d.compute_feature_importance_diagnostic

compute_per_pair_sharpe_contribution = stage27_0b.compute_per_pair_sharpe_contribution


# ---------------------------------------------------------------------------
# Binding constants (per 27.0c-α)
# ---------------------------------------------------------------------------

# Barrier geometry (inherited)
K_FAV = stage25_0b.K_FAV  # 1.5
K_ADV = stage25_0b.K_ADV  # 1.0
H_M1_BARS = stage25_0b.H_M1_BARS  # 60

# L-1 class encoding (inherited)
LABEL_TP = stage26_0c.LABEL_TP
LABEL_SL = stage26_0c.LABEL_SL
LABEL_TIME = stage26_0c.LABEL_TIME
NUM_CLASSES = stage26_0c.NUM_CLASSES

# Threshold family (inherited)
THRESHOLDS_QUANTILE_PERCENTS = stage26_0c.THRESHOLDS_QUANTILE_PERCENTS

# LightGBM config (inherited; FIXED for 27.0c per design memo §2)
LIGHTGBM_FIXED_CONFIG = dict(stage26_0d.LIGHTGBM_FIXED_CONFIG)

# H1/H2/H3/H4 thresholds (inherited; FIXED)
H1_WEAK_THRESHOLD = stage26_0c.H1_WEAK_THRESHOLD
H1_MEANINGFUL_THRESHOLD = stage26_0c.H1_MEANINGFUL_THRESHOLD
H3_REFERENCE_SHARPE = stage26_0c.H3_REFERENCE_SHARPE

# Diagnostic constants
CONCENTRATION_HIGH_THRESHOLD = stage26_0c.CONCENTRATION_HIGH_THRESHOLD

# R7-A feature family (FIXED)
NUMERIC_FEATURES = stage26_0d.NUMERIC_FEATURES
ALL_FEATURES = stage26_0d.ALL_FEATURES
CATEGORICAL_COLS = stage26_0d.CATEGORICAL_COLS

# Sanity probe thresholds (inherited)
SANITY_MIN_CLASS_SHARE = stage26_0c.SANITY_MIN_CLASS_SHARE
SANITY_MAX_PER_PAIR_TIME_SHARE = stage26_0c.SANITY_MAX_PER_PAIR_TIME_SHARE
SANITY_MAX_NEW_FEATURE_NAN_RATE = stage26_0d.SANITY_MAX_NEW_FEATURE_NAN_RATE
SANITY_MAX_POSITIVITY_VIOLATION_RATE = stage26_0d.SANITY_MAX_POSITIVITY_VIOLATION_RATE

# Span budgets
TEST_SPAN_YEARS = SPAN_YEARS * (1.0 - TRAIN_FRAC - VAL_FRAC)
VAL_SPAN_YEARS = SPAN_YEARS * VAL_FRAC


# ---------------------------------------------------------------------------
# NEW Phase 27.0c constants
# ---------------------------------------------------------------------------

# 5-fold OOF protocol parameters (per 27.0c-α §4.3 / D-I1, D-I2)
OOF_N_FOLDS = 5
OOF_SEED = 42

# Isotonic clip bounds (per D-I3)
ISOTONIC_Y_MIN = 0.0
ISOTONIC_Y_MAX = 1.0

# OOF-vs-full-train divergence flag threshold (per design memo §4.3 step 6 / D-I6)
ESTIMATOR_DIVERGENCE_FRAC_THRESHOLD = 0.10
ESTIMATOR_DIVERGENCE_DENOM_EPS = 1e-9

# Baseline reference values for C-sb-baseline (per D-I10; from PR #318 §10)
# C-sb-baseline must reproduce 27.0b C-alpha0 = R6-new-A C02 baseline
BASELINE_27_0B_C_ALPHA0_N_TRADES = 34626
BASELINE_27_0B_C_ALPHA0_SHARPE = -0.1732
BASELINE_27_0B_C_ALPHA0_ANN_PNL = -204664.4

# Tolerances (inherited verbatim from 27.0b-α §12.2)
BASELINE_MATCH_N_TRADES_TOLERANCE = 0  # exact
BASELINE_MATCH_SHARPE_ABS_TOLERANCE = 1e-4
BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE = 0.5  # pip


# ---------------------------------------------------------------------------
# NEW exception (per 27.0c-α §7.3 / D-I9)
# ---------------------------------------------------------------------------


class BaselineMismatchError(RuntimeError):
    """Raised when C-sb-baseline fails to reproduce 27.0b C-alpha0 baseline.

    Per 27.0c-α §7.3 / D-I9. C-sb-baseline uses raw `P(TP) - P(SL)` on the
    refit-on-full-train multiclass head — the SAME head as 27.0b. With
    R7-A held fixed, L-1 label fixed, model class fixed, dataset / split /
    harness inherited unchanged, val-selected C-sb-baseline metrics MUST
    coincide with 27.0b C-alpha0 (= R6-new-A C02) exactly (n_trades;
    ≤ 1e-4 on Sharpe; ≤ 0.5 pip on ann_pnl). If they don't, something
    in the inheritance chain has drifted and S-D verdict assignment is
    unsafe.
    """


# ---------------------------------------------------------------------------
# 5-fold OOF assignment helper (per D-I1 + D-I2)
# ---------------------------------------------------------------------------


def make_oof_fold_assignment(
    n_rows: int, n_folds: int = OOF_N_FOLDS, seed: int = OOF_SEED
) -> np.ndarray:
    """Deterministic 5-fold assignment via permutation + array_split.

    Returns:
        fold_idx: np.ndarray of shape (n_rows,) dtype int64; fold_idx[i] ∈ [0, n_folds)

    Per D-I2: no stratification; same fold assignment reused across
    estimator and calibration artifacts.
    """
    if n_rows <= 0:
        raise ValueError(f"n_rows must be positive; got {n_rows}")
    if n_folds < 2:
        raise ValueError(f"n_folds must be ≥ 2; got {n_folds}")
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n_rows)
    splits = np.array_split(perm, n_folds)
    fold_idx = np.zeros(n_rows, dtype=np.int64)
    for f, idx_in_fold in enumerate(splits):
        fold_idx[idx_in_fold] = f
    return fold_idx


# ---------------------------------------------------------------------------
# 5-fold OOF protocol (per 27.0c-α §4.3 steps 1-3)
# ---------------------------------------------------------------------------


def fit_oof_multiclass_head(
    x_train: pd.DataFrame,
    train_label: np.ndarray,
    fold_idx: np.ndarray,
    n_folds: int = OOF_N_FOLDS,
) -> np.ndarray:
    """Fit fold-wise heads; return OOF probabilities for all train rows.

    For each fold f: fit a multiclass head on (train \\ fold f); predict on
    fold f → OOF probabilities. Aggregated: oof_probs[i, c] = predicted
    P(c | row_i) by the fold-fit head that did NOT see row_i during fitting.

    Returns:
        oof_probs: np.ndarray of shape (n_train, NUM_CLASSES) dtype float64
    """
    n_train = len(train_label)
    if len(x_train) != n_train:
        raise ValueError(f"x_train rows {len(x_train)} != train_label {n_train}")
    if len(fold_idx) != n_train:
        raise ValueError(f"fold_idx rows {len(fold_idx)} != train_label {n_train}")

    oof_probs = np.full((n_train, NUM_CLASSES), np.nan, dtype=np.float64)
    x_train_reset = x_train.reset_index(drop=True)

    for f in range(n_folds):
        in_fold = fold_idx == f
        not_in_fold = ~in_fold
        n_in = int(in_fold.sum())
        if n_in == 0:
            continue
        t0 = time.time()
        x_tr = x_train_reset.loc[not_in_fold].reset_index(drop=True)
        y_tr = train_label[not_in_fold]
        x_pred = x_train_reset.loc[in_fold].reset_index(drop=True)
        pipeline_f = build_pipeline_lightgbm_multiclass_widened()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pipeline_f.fit(x_tr, y_tr)
        probs_f = pipeline_f.predict_proba(x_pred)
        # sklearn classes_ may differ from our LABEL_TP/SL/TIME indexing.
        # Use the trained pipeline's class ordering to map back.
        final_step = pipeline_f.steps[-1][1]
        classes = np.asarray(getattr(final_step, "classes_", np.arange(NUM_CLASSES)))
        for col_idx, cls in enumerate(classes):
            cls_int = int(cls)
            oof_probs[in_fold, cls_int] = probs_f[:, col_idx]
        print(
            f"    OOF fold {f + 1}/{n_folds}: train_n={int(not_in_fold.sum())} "
            f"oof_n={n_in} ({time.time() - t0:.1f}s)"
        )

    # Sanity: every row should have OOF probs (no NaN)
    if not np.all(np.isfinite(oof_probs)):
        nan_rows = int((~np.isfinite(oof_probs)).any(axis=1).sum())
        raise RuntimeError(
            f"OOF protocol produced NaN probabilities for {nan_rows} train rows "
            "(fold assignment gap or fit failure)"
        )

    return oof_probs


# ---------------------------------------------------------------------------
# Isotonic calibration (per 27.0c-α §5; D-I3, D-I4)
# ---------------------------------------------------------------------------


def fit_isotonic_calibrators_per_class(
    oof_probs: np.ndarray, train_label: np.ndarray
) -> list[IsotonicRegression]:
    """Fit one-vs-rest isotonic regression per class on OOF predictions.

    Per design memo §5 / D-I3:
      g_c = IsotonicRegression(out_of_bounds='clip', y_min=0.0, y_max=1.0)
      Fit on (oof_p_c, 1{realised=c}) pairs

    Returns:
        list of NUM_CLASSES IsotonicRegression objects indexed by class.
    """
    if oof_probs.shape[0] != len(train_label):
        raise ValueError(f"oof_probs rows {oof_probs.shape[0]} != train_label {len(train_label)}")
    if oof_probs.shape[1] != NUM_CLASSES:
        raise ValueError(f"oof_probs must have {NUM_CLASSES} columns; got {oof_probs.shape[1]}")
    calibrators: list[IsotonicRegression] = []
    for c in range(NUM_CLASSES):
        p_oof_c = oof_probs[:, c].astype(np.float64)
        y_indicator = (train_label == c).astype(np.float64)
        iso = IsotonicRegression(out_of_bounds="clip", y_min=ISOTONIC_Y_MIN, y_max=ISOTONIC_Y_MAX)
        iso.fit(p_oof_c, y_indicator)
        calibrators.append(iso)
    return calibrators


def apply_isotonic_and_renormalise(
    raw_probs: np.ndarray, calibrators: list[IsotonicRegression]
) -> tuple[np.ndarray, int]:
    """Apply isotonic per class then per-row sum-to-1 renormalisation.

    Per design memo §5 + D-I4:
      P_tilde[c] = g_c(raw_probs[c])
      P_cal[c] = P_tilde[c] / sum_{c'} P_tilde[c']

    Edge case: if sum_{c'} P_tilde[c'] = 0 for a row, fall back to raw_probs
    for that row (renormalised). Counter is reported (DIAGNOSTIC-ONLY;
    expected 0; pathology flag if > 0).

    Returns:
        (P_cal, zero_sum_row_fallback_count)
    """
    if raw_probs.ndim != 2 or raw_probs.shape[1] != NUM_CLASSES:
        raise ValueError(f"raw_probs must have shape (N, {NUM_CLASSES}); got {raw_probs.shape}")
    if len(calibrators) != NUM_CLASSES:
        raise ValueError(f"calibrators must have {NUM_CLASSES} entries; got {len(calibrators)}")
    p_tilde = np.zeros_like(raw_probs, dtype=np.float64)
    for c in range(NUM_CLASSES):
        p_tilde[:, c] = calibrators[c].predict(raw_probs[:, c].astype(np.float64))
    row_sums = p_tilde.sum(axis=1)
    zero_sum_mask = row_sums <= 0.0
    n_zero_sum = int(zero_sum_mask.sum())
    p_cal = np.zeros_like(p_tilde)
    nonzero_mask = ~zero_sum_mask
    if nonzero_mask.any():
        p_cal[nonzero_mask] = p_tilde[nonzero_mask] / row_sums[nonzero_mask, np.newaxis]
    if n_zero_sum > 0:
        # Fallback: use raw probs (already sum-to-1) for those rows
        raw_row_sums = raw_probs[zero_sum_mask].sum(axis=1)
        raw_row_sums = np.where(raw_row_sums > 0.0, raw_row_sums, 1.0)
        p_cal[zero_sum_mask] = raw_probs[zero_sum_mask] / raw_row_sums[:, np.newaxis]
    return p_cal, n_zero_sum


def compute_calibration_diagnostic(
    calibrators: list[IsotonicRegression], oof_probs: np.ndarray
) -> dict:
    """Diagnostic summary per isotonic map.

    DIAGNOSTIC-ONLY (clause 2 extension per 27.0c-α §11.18).
    """
    diag: dict = {}
    for c in range(NUM_CLASSES):
        iso = calibrators[c]
        # Breakpoint count: sklearn IsotonicRegression exposes X_thresholds_ / y_thresholds_
        x_thr = getattr(iso, "X_thresholds_", None)
        y_thr = getattr(iso, "y_thresholds_", None)
        breakpoint_count = int(len(x_thr)) if x_thr is not None else -1
        raw = oof_probs[:, c]
        cal = iso.predict(raw)
        mean_shift = float(np.mean(cal - raw))
        mean_abs_shift = float(np.mean(np.abs(cal - raw)))
        diag[c] = {
            "breakpoint_count": breakpoint_count,
            "mean_shift": mean_shift,
            "mean_abs_shift": mean_abs_shift,
            "x_thresholds": x_thr.tolist() if x_thr is not None else None,
            "y_thresholds": y_thr.tolist() if y_thr is not None else None,
        }
    return diag


def compute_reliability_diagram_per_class(
    raw_probs: np.ndarray,
    cal_probs: np.ndarray,
    realised_label: np.ndarray,
    n_bins: int = 10,
) -> dict:
    """Per-class reliability diagram (pre- vs post-isotonic).

    DIAGNOSTIC-ONLY (clause 2 extension per 27.0c-α §11.18).
    For each class c and each bin of predicted probability:
      - bin_center: midpoint of bin
      - bin_count: number of rows in bin
      - bin_freq_actual: fraction of bin rows where realised_label == c
      - bin_mean_pred_raw: mean of raw P(c) within bin
      - bin_mean_pred_cal: mean of cal P(c) within bin
    """
    diag: dict[int, list[dict]] = {}
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    for c in range(NUM_CLASSES):
        raw_c = raw_probs[:, c]
        cal_c = cal_probs[:, c]
        is_c = (realised_label == c).astype(np.float64)
        bins_data: list[dict] = []
        for b in range(n_bins):
            lo, hi = bin_edges[b], bin_edges[b + 1]
            mask = (cal_c >= lo) & (cal_c < hi if b < n_bins - 1 else cal_c <= hi)
            n_b = int(mask.sum())
            if n_b == 0:
                bins_data.append(
                    {
                        "bin_lo": float(lo),
                        "bin_hi": float(hi),
                        "bin_count": 0,
                        "bin_freq_actual": float("nan"),
                        "bin_mean_pred_raw": float("nan"),
                        "bin_mean_pred_cal": float("nan"),
                    }
                )
                continue
            bins_data.append(
                {
                    "bin_lo": float(lo),
                    "bin_hi": float(hi),
                    "bin_count": n_b,
                    "bin_freq_actual": float(is_c[mask].mean()),
                    "bin_mean_pred_raw": float(raw_c[mask].mean()),
                    "bin_mean_pred_cal": float(cal_c[mask].mean()),
                }
            )
        diag[c] = bins_data
    return diag


# ---------------------------------------------------------------------------
# Conditional-PnL estimator (per 27.0c-α §4; D-I1, D-I2, D-I4, D-I5, D-I6)
# ---------------------------------------------------------------------------


def compute_class_conditional_pnl(
    train_label: np.ndarray, train_pnl: np.ndarray
) -> dict[int, float]:
    """Constant per-class conditional-PnL on full train.

    Per D-I1 / D-I4: realised PnL uses inherited _compute_realised_barrier_pnl
    (D-1 binding). Per D-I5: empty class raises ValueError; no imputation.

    Returns:
        {LABEL_TP: Ê[PnL|TP], LABEL_SL: Ê[PnL|SL], LABEL_TIME: Ê[PnL|TIME]}
    """
    if len(train_label) != len(train_pnl):
        raise ValueError(f"train_label rows {len(train_label)} != train_pnl rows {len(train_pnl)}")
    out: dict[int, float] = {}
    valid_pnl_mask = np.isfinite(train_pnl)
    for c in range(NUM_CLASSES):
        cls_mask = (train_label == c) & valid_pnl_mask
        n_c = int(cls_mask.sum())
        if n_c == 0:
            raise ValueError(
                f"class {c} has 0 rows with finite PnL in train (per D-I5; no imputation)"
            )
        out[c] = float(train_pnl[cls_mask].mean())
    return out


def compute_oof_class_conditional_pnl(
    train_label: np.ndarray, train_pnl: np.ndarray, fold_idx: np.ndarray
) -> dict[int, dict]:
    """OOF version (per design memo §4.3 step 3 + step 6).

    DIAGNOSTIC-ONLY: compares per-fold per-class means vs aggregated mean.
    Aggregated = unweighted mean of per-fold means (for equal-size folds,
    this equals the pooled mean = full-train mean).
    """
    if len(train_label) != len(train_pnl):
        raise ValueError("len mismatch")
    if len(fold_idx) != len(train_pnl):
        raise ValueError("fold_idx len mismatch")
    n_folds = int(fold_idx.max()) + 1
    out: dict[int, dict] = {}
    valid_pnl_mask = np.isfinite(train_pnl)
    for c in range(NUM_CLASSES):
        per_fold_means: list[float] = []
        per_fold_counts: list[int] = []
        for f in range(n_folds):
            mask = (train_label == c) & (fold_idx == f) & valid_pnl_mask
            n_f = int(mask.sum())
            if n_f == 0:
                per_fold_means.append(float("nan"))
                per_fold_counts.append(0)
                continue
            per_fold_means.append(float(train_pnl[mask].mean()))
            per_fold_counts.append(n_f)
        finite_means = [m for m in per_fold_means if np.isfinite(m)]
        unweighted_aggregate = float(np.mean(finite_means)) if finite_means else float("nan")
        out[c] = {
            "per_fold_mean": per_fold_means,
            "per_fold_count": per_fold_counts,
            "oof_aggregate_mean": unweighted_aggregate,
        }
    return out


def compute_estimator_divergence_flag(
    full_train: dict[int, float], oof: dict[int, dict]
) -> dict[int, dict]:
    """Per-class divergence flag: |OOF - full_train| / |full_train| > 10%.

    Per D-I6: if |full_train| < 1e-9, suppress flag (report value only).
    """
    out: dict[int, dict] = {}
    for c in range(NUM_CLASSES):
        ft = full_train.get(c, float("nan"))
        oof_agg = oof.get(c, {}).get("oof_aggregate_mean", float("nan"))
        if not np.isfinite(ft) or not np.isfinite(oof_agg):
            out[c] = {
                "full_train": ft,
                "oof_aggregate": oof_agg,
                "delta": float("nan"),
                "rel_delta": float("nan"),
                "divergence_flag": False,
                "suppressed_div_by_zero": False,
            }
            continue
        delta = oof_agg - ft
        if abs(ft) < ESTIMATOR_DIVERGENCE_DENOM_EPS:
            rel_delta = float("nan")
            flag = False
            suppressed = True
        else:
            rel_delta = delta / abs(ft)
            flag = abs(rel_delta) > ESTIMATOR_DIVERGENCE_FRAC_THRESHOLD
            suppressed = False
        out[c] = {
            "full_train": float(ft),
            "oof_aggregate": float(oof_agg),
            "delta": float(delta),
            "rel_delta": float(rel_delta) if np.isfinite(rel_delta) else float("nan"),
            "divergence_flag": bool(flag),
            "suppressed_div_by_zero": bool(suppressed),
        }
    return out


# ---------------------------------------------------------------------------
# S-D score formula (per 27.0c-α §3.1; D-I7)
# ---------------------------------------------------------------------------


def compute_picker_score_s_d(p_cal: np.ndarray, e_pnl_per_class: dict[int, float]) -> np.ndarray:
    """S-D(row) = Σ_c P_cal(c|row) · Ê[PnL|c].

    Per 27.0c-α §3.1 / D-I7: numpy-vectorised; no per-row loop.
    """
    if p_cal.ndim != 2 or p_cal.shape[1] != NUM_CLASSES:
        raise ValueError(f"p_cal must have shape (N, {NUM_CLASSES}); got {p_cal.shape}")
    if set(e_pnl_per_class.keys()) != {LABEL_TP, LABEL_SL, LABEL_TIME}:
        raise ValueError(
            f"e_pnl_per_class keys must be {{{LABEL_TP}, {LABEL_SL}, {LABEL_TIME}}}; "
            f"got {set(e_pnl_per_class.keys())}"
        )
    e_vec = np.array(
        [e_pnl_per_class[LABEL_TP], e_pnl_per_class[LABEL_SL], e_pnl_per_class[LABEL_TIME]],
        dtype=np.float64,
    )
    return (p_cal @ e_vec).astype(np.float64)


def compute_picker_score_s_b_raw(raw_probs: np.ndarray) -> np.ndarray:
    """S-B(row) = P(TP) - P(SL) on RAW (uncalibrated) refit-on-full-train probs.

    Per D-I8: C-sb-baseline uses raw probs to exactly reproduce 27.0b
    C-alpha0 inheritance-chain baseline.
    """
    if raw_probs.ndim != 2 or raw_probs.shape[1] != NUM_CLASSES:
        raise ValueError(f"raw_probs must have shape (N, {NUM_CLASSES}); got {raw_probs.shape}")
    return (raw_probs[:, LABEL_TP] - raw_probs[:, LABEL_SL]).astype(np.float64)


# ---------------------------------------------------------------------------
# Formal cells (per 27.0c-α §7.1; D-I8)
# ---------------------------------------------------------------------------


def build_s_d_cells() -> list[dict]:
    """27.0c formal grid: 2 cells per design memo §7.1.

    - C-sd: S-D calibrated EV (substantive)
    - C-sb-baseline: S-B raw probs (inheritance-chain check)
    """
    return [
        {"id": "C-sd", "picker": "S-D(calibrated_ev)", "score_type": "s_d"},
        {"id": "C-sb-baseline", "picker": "S-B(raw_p_tp_minus_p_sl)", "score_type": "s_b_raw"},
    ]


# ---------------------------------------------------------------------------
# C-sb-baseline mismatch check (per 27.0c-α §7.3; D-I9, D-I10)
# ---------------------------------------------------------------------------


def check_c_sb_baseline_match(c_sb_baseline_result: dict) -> dict:
    """Validate C-sb-baseline reproduces 27.0b C-alpha0 baseline.

    Per 27.0c-α §7.3 + D-I9 (fail-fast): HALT with BaselineMismatchError on
    mismatch. Tolerances inherited from 27.0b-α §12.2.
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
                f"ann_pnl: observed={ann_pnl:+.3f} baseline={BASELINE_27_0B_C_ALPHA0_ANN_PNL:+.3f} "
                f"delta={ann_pnl_delta:+.3f} (tolerance ±{BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE})"
            )
        raise BaselineMismatchError(
            "C-sb-baseline failed to reproduce 27.0b C-alpha0 / R6-new-A C02 baseline per "
            "27.0c-α §7.3; failures: " + "; ".join(failures)
        )
    return report


# ---------------------------------------------------------------------------
# Sanity probe (extends 27.0b probe with NEW S-D-specific items per §10)
# ---------------------------------------------------------------------------


def run_sanity_probe_27_0c(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    pairs: list[str],
    oof_probs: np.ndarray | None = None,
    val_p_cal: np.ndarray | None = None,
    test_p_cal: np.ndarray | None = None,
    val_score_s_d: np.ndarray | None = None,
    test_score_s_d: np.ndarray | None = None,
    train_score_s_d: np.ndarray | None = None,
    fold_idx: np.ndarray | None = None,
    e_pnl_full_train: dict[int, float] | None = None,
    e_pnl_oof_diag: dict[int, dict] | None = None,
    divergence_flags: dict[int, dict] | None = None,
    calibration_diag: dict | None = None,
    zero_sum_row_count_val: int | None = None,
    zero_sum_row_count_test: int | None = None,
) -> dict:
    """27.0c sanity probe per design memo §10.

    Inherited HALT checks (1-6 from 27.0b §11):
      1. Class priors per split — HALT if class < 1%
      2. Per-pair TIME share — HALT if pair > 99% TIME
      3. Realised-PnL cache basis confirmed (D-1 binding)
      4. Mid-to-mid PnL distribution per class (diagnostic-only)
      5. R7-A new-feature NaN rate per split — HALT > 5%
      6. R7-A positivity assertions — HALT > 1% violation

    NEW 27.0c items per design memo §10 (per D-I11 HALT conditions):
      7. OOF assignment determinism check (fold sizes)
      8. Conditional-PnL estimator constants disclosure
      9. Calibration-map summary per class
      10. Zero-sum-row fallback counter (HALT > 0 per D-I11)
      11. S-D distribution diagnostic on train / val / test
    """
    print("\n=== 27.0c SANITY PROBE (per 27.0c-α §10) ===")
    out: dict = {}

    # 1. Class priors per split
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

    # 2. Per-pair TIME share on train
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

    # 3. Realised-PnL cache basis check (D-1 binding)
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
    out["realised_pnl_cache_basis"] = "inherited_compute_realised_barrier_pnl_bid_ask_executable"
    print("    OK: bid/ask executable treatment confirmed")

    # 4. Mid-to-mid PnL distribution per class on train (DIAGNOSTIC-ONLY)
    print("  mid-to-mid PnL distribution per class on TRAIN (diagnostic; NOT formal):")
    mid_train = compute_mid_to_mid_pnl_diagnostic(train_df, pair_runtime_map)
    out["mid_to_mid_per_class_train"] = {}
    for cls, name in [(LABEL_TP, "TP"), (LABEL_SL, "SL"), (LABEL_TIME, "TIME")]:
        mask = (train_label == cls) & np.isfinite(mid_train)
        if mask.sum() == 0:
            out["mid_to_mid_per_class_train"][name] = {"n": 0}
            print(f"    {name}: n=0")
            continue
        vals = mid_train[mask]
        stats = {
            "n": int(mask.sum()),
            "mean": float(vals.mean()),
            "p5": float(np.quantile(vals, 0.05)),
            "p50": float(np.quantile(vals, 0.50)),
            "p95": float(np.quantile(vals, 0.95)),
        }
        out["mid_to_mid_per_class_train"][name] = stats
        print(
            f"    {name}: n={stats['n']} mean={stats['mean']:+.3f} "
            f"p5={stats['p5']:+.3f} p50={stats['p50']:+.3f} p95={stats['p95']:+.3f}"
        )

    # 5. R7-A new-feature NaN rate per split
    print("  R7-A new-feature NaN-rate check:")
    out["new_feature_nan_rate"] = {}
    nan_violations: list[tuple[str, str, float]] = []
    for split_name, df in splits.items():
        per_feature: dict[str, dict] = {}
        for feat in NUMERIC_FEATURES:
            col = df[feat].to_numpy(dtype=np.float64)
            n = len(col)
            nan_count = int((~np.isfinite(col)).sum())
            nan_rate = nan_count / n if n > 0 else float("nan")
            per_feature[feat] = {"n": n, "nan_count": nan_count, "nan_rate": nan_rate}
            print(f"    {split_name}.{feat}: n={n} NaN={nan_count} ({nan_rate:.3%})")
            if np.isfinite(nan_rate) and nan_rate > SANITY_MAX_NEW_FEATURE_NAN_RATE:
                nan_violations.append((split_name, feat, nan_rate))
        out["new_feature_nan_rate"][split_name] = per_feature

    # 6. Positivity assertions
    print("  R7-A positivity check on TRAIN:")
    out["new_feature_distribution_train"] = {}
    positivity_violations: list[tuple[str, str, float]] = []
    for feat in NUMERIC_FEATURES:
        col = train_df[feat].to_numpy(dtype=np.float64)
        finite_mask = np.isfinite(col)
        finite = col[finite_mask]
        if len(finite) == 0:
            out["new_feature_distribution_train"][feat] = {"n_finite": 0}
            continue
        stats = {
            "n_finite": int(len(finite)),
            "mean": float(finite.mean()),
            "p5": float(np.quantile(finite, 0.05)),
            "p50": float(np.quantile(finite, 0.50)),
            "p95": float(np.quantile(finite, 0.95)),
            "min": float(finite.min()),
            "max": float(finite.max()),
        }
        if feat == "atr_at_signal_pip":
            violation_mask = finite <= 0
            violation_rate = int(violation_mask.sum()) / len(finite)
            if violation_rate > SANITY_MAX_POSITIVITY_VIOLATION_RATE:
                positivity_violations.append((feat, "<=0", violation_rate))
            stats["positivity_violation_rate"] = violation_rate
        elif feat == "spread_at_signal_pip":
            violation_mask = finite < 0
            violation_rate = int(violation_mask.sum()) / len(finite)
            if violation_rate > SANITY_MAX_POSITIVITY_VIOLATION_RATE:
                positivity_violations.append((feat, "<0", violation_rate))
            stats["positivity_violation_rate"] = violation_rate
        out["new_feature_distribution_train"][feat] = stats
        print(
            f"    {feat}: n={stats['n_finite']} mean={stats['mean']:+.3f} "
            f"p5={stats['p5']:+.3f} p50={stats['p50']:+.3f} p95={stats['p95']:+.3f} "
            f"min={stats['min']:+.3f} max={stats['max']:+.3f}"
        )

    # 7. NEW 27.0c: OOF fold sizes (per design memo §10 NEW item 1)
    print("  OOF assignment determinism check (5-fold; seed=42):")
    if fold_idx is not None:
        fold_sizes = [int((fold_idx == f).sum()) for f in range(OOF_N_FOLDS)]
        max_size_delta = max(fold_sizes) - min(fold_sizes)
        out["oof_fold_sizes"] = {
            "seed": OOF_SEED,
            "n_folds": OOF_N_FOLDS,
            "fold_sizes": fold_sizes,
            "max_size_delta": max_size_delta,
        }
        print(f"    seed={OOF_SEED} folds={fold_sizes} max_size_delta={max_size_delta}")
    else:
        out["oof_fold_sizes"] = {"status": "deferred (OOF not yet computed at probe-only stage)"}
        print("    deferred (OOF not computed at probe-only stage)")

    # 8. NEW 27.0c: Conditional-PnL estimator constants disclosure
    print("  conditional-PnL estimator constants (NEW; DIAGNOSTIC-ONLY):")
    if e_pnl_full_train is not None:
        e_pnl_block = {
            "full_train": {
                "TP": float(e_pnl_full_train.get(LABEL_TP, float("nan"))),
                "SL": float(e_pnl_full_train.get(LABEL_SL, float("nan"))),
                "TIME": float(e_pnl_full_train.get(LABEL_TIME, float("nan"))),
            }
        }
        if e_pnl_oof_diag is not None:
            e_pnl_block["oof_aggregate"] = {
                "TP": float(
                    e_pnl_oof_diag.get(LABEL_TP, {}).get("oof_aggregate_mean", float("nan"))
                ),
                "SL": float(
                    e_pnl_oof_diag.get(LABEL_SL, {}).get("oof_aggregate_mean", float("nan"))
                ),
                "TIME": float(
                    e_pnl_oof_diag.get(LABEL_TIME, {}).get("oof_aggregate_mean", float("nan"))
                ),
            }
        if divergence_flags is not None:
            e_pnl_block["divergence_flags"] = {str(k): v for k, v in divergence_flags.items()}
        out["conditional_pnl_estimator"] = e_pnl_block
        print(
            f"    TP: full_train={e_pnl_block['full_train']['TP']:+.4f} "
            f"oof={e_pnl_block.get('oof_aggregate', {}).get('TP', float('nan')):+.4f}"
        )
        print(
            f"    SL: full_train={e_pnl_block['full_train']['SL']:+.4f} "
            f"oof={e_pnl_block.get('oof_aggregate', {}).get('SL', float('nan')):+.4f}"
        )
        print(
            f"    TIME: full_train={e_pnl_block['full_train']['TIME']:+.4f} "
            f"oof={e_pnl_block.get('oof_aggregate', {}).get('TIME', float('nan')):+.4f}"
        )
        if divergence_flags is not None:
            any_flag = any(v.get("divergence_flag", False) for v in divergence_flags.values())
            print(f"    divergence_flag (>10% rel): {any_flag}")
        if e_pnl_full_train.get(LABEL_TP, 0.0) <= 0.0:
            warnings.warn(
                f"Ê[PnL|TP] <= 0 ({e_pnl_full_train.get(LABEL_TP, 0.0):+.4f}); "
                "warn-only per D-I11 (does NOT HALT)",
                UserWarning,
                stacklevel=2,
            )
            out["estimator_warn_e_pnl_tp_nonpositive"] = True
        else:
            out["estimator_warn_e_pnl_tp_nonpositive"] = False
    else:
        out["conditional_pnl_estimator"] = {
            "status": "deferred (estimator not yet computed at probe-only stage)"
        }
        print("    deferred (estimator not computed at probe-only stage)")

    # 9. NEW 27.0c: Calibration-map summary per class
    print("  calibration-map summary per class (NEW; DIAGNOSTIC-ONLY):")
    if calibration_diag is not None:
        cal_summary = {}
        for c in range(NUM_CLASSES):
            d = calibration_diag.get(c, {})
            name = {LABEL_TP: "TP", LABEL_SL: "SL", LABEL_TIME: "TIME"}[c]
            cal_summary[name] = {
                "breakpoint_count": d.get("breakpoint_count", -1),
                "mean_shift": d.get("mean_shift", float("nan")),
                "mean_abs_shift": d.get("mean_abs_shift", float("nan")),
            }
            print(
                f"    {name}: breakpoints={cal_summary[name]['breakpoint_count']} "
                f"mean_shift={cal_summary[name]['mean_shift']:+.4e} "
                f"mean_abs_shift={cal_summary[name]['mean_abs_shift']:.4e}"
            )
        out["calibration_map_summary"] = cal_summary
    else:
        out["calibration_map_summary"] = {
            "status": "deferred (calibrators not yet fit at probe-only stage)"
        }
        print("    deferred (calibrators not fit at probe-only stage)")

    # 10. NEW 27.0c: Zero-sum-row fallback counter (HALT > 0 per D-I11)
    if zero_sum_row_count_val is not None or zero_sum_row_count_test is not None:
        out["zero_sum_row_fallback"] = {
            "val": int(zero_sum_row_count_val) if zero_sum_row_count_val is not None else None,
            "test": int(zero_sum_row_count_test) if zero_sum_row_count_test is not None else None,
        }
        print(
            f"  zero-sum-row fallback (NEW; HALT > 0): val={zero_sum_row_count_val} "
            f"test={zero_sum_row_count_test}"
        )
    else:
        out["zero_sum_row_fallback"] = {
            "status": "deferred (calibrators not yet applied at probe-only stage)"
        }
        print("  zero-sum-row fallback: deferred (calibrators not applied at probe-only stage)")

    # 11. NEW 27.0c: S-D distribution on train / val / test
    print("  S-D distribution diagnostic (NEW; DIAGNOSTIC-ONLY):")
    if val_score_s_d is not None and test_score_s_d is not None and train_score_s_d is not None:
        s_d_dist = {}
        for split_name, scores in [
            ("train", train_score_s_d),
            ("val", val_score_s_d),
            ("test", test_score_s_d),
        ]:
            finite = scores[np.isfinite(scores)]
            if len(finite) == 0:
                s_d_dist[split_name] = {"n_finite": 0}
                continue
            stats = {
                "n_finite": int(len(finite)),
                "p5": float(np.quantile(finite, 0.05)),
                "p25": float(np.quantile(finite, 0.25)),
                "p50": float(np.quantile(finite, 0.50)),
                "p75": float(np.quantile(finite, 0.75)),
                "p95": float(np.quantile(finite, 0.95)),
                "mean": float(finite.mean()),
            }
            s_d_dist[split_name] = stats
            print(
                f"    {split_name}: n={stats['n_finite']} "
                f"p5={stats['p5']:+.4f} p50={stats['p50']:+.4f} p95={stats['p95']:+.4f} "
                f"mean={stats['mean']:+.4f}"
            )
        out["s_d_distribution"] = s_d_dist
    else:
        out["s_d_distribution"] = {"status": "deferred (S-D not yet computed at probe-only stage)"}
        print("    deferred (S-D not computed at probe-only stage)")

    # Inherited HALT conditions
    train_shares = out["class_priors"]["train"]["shares"]
    halt_class_shares = {
        k: v for k, v in train_shares.items() if np.isfinite(v) and v < SANITY_MIN_CLASS_SHARE
    }
    if halt_class_shares:
        raise SanityProbeError(
            f"class share below {SANITY_MIN_CLASS_SHARE:.0%}: {halt_class_shares}"
        )
    if over_99_pairs:
        raise SanityProbeError(
            f"{len(over_99_pairs)} pair(s) over {SANITY_MAX_PER_PAIR_TIME_SHARE:.0%} TIME: "
            f"{over_99_pairs[:5]}"
        )
    if nan_violations:
        raise SanityProbeError(
            f"new-feature NaN rate over {SANITY_MAX_NEW_FEATURE_NAN_RATE:.0%}: {nan_violations[:5]}"
        )
    if positivity_violations:
        raise SanityProbeError(
            f"new-feature positivity violated over "
            f"{SANITY_MAX_POSITIVITY_VIOLATION_RATE:.0%}: {positivity_violations[:5]}"
        )

    # NEW 27.0c HALT (per D-I11): zero-sum-row fallback count > 0
    if zero_sum_row_count_val is not None and zero_sum_row_count_val > 0:
        raise SanityProbeError(
            f"zero-sum-row fallback count on val = {zero_sum_row_count_val} > 0 "
            "(per D-I11; isotonic clipped entire row to 0 — pathology)"
        )
    if zero_sum_row_count_test is not None and zero_sum_row_count_test > 0:
        raise SanityProbeError(
            f"zero-sum-row fallback count on test = {zero_sum_row_count_test} > 0 "
            "(per D-I11; isotonic clipped entire row to 0 — pathology)"
        )

    print("=== SANITY PROBE: PASS ===\n")
    out["status"] = "PASS"
    return out


# ---------------------------------------------------------------------------
# Per-cell evaluation (per 27.0c-α §7; D10 amended single-fit)
# ---------------------------------------------------------------------------


def evaluate_cell_27_0c(
    cell: dict,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    train_label: np.ndarray,
    val_label: np.ndarray,
    test_label: np.ndarray,
    val_raw_probs: np.ndarray,
    test_raw_probs: np.ndarray,
    val_p_cal: np.ndarray,
    test_p_cal: np.ndarray,
    val_score: np.ndarray,
    test_score: np.ndarray,
    pnl_val_full: np.ndarray,
    pnl_test_full: np.ndarray,
    feature_importance_diag: dict,
) -> dict:
    """27.0c cell evaluation.

    Differs from 26.0d-β only in: picker score is precomputed (S-D for
    C-sd; raw S-B for C-sb-baseline) and passed in. All cells share the
    SAME refit-on-full-train head (D10 amendment per 27.0c-α §7.5).

    For classification-quality diagnostics, calibrated probs are used for
    C-sd and raw probs for C-sb-baseline (matches the score function each
    cell uses).
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

    # PRIMARY family: quantile-of-val (inherited)
    quantile_results = evaluate_quantile_family(
        val_score,
        pnl_val_full,
        test_score,
        pnl_test_full,
        VAL_SPAN_YEARS,
        TEST_SPAN_YEARS,
    )

    def _q_sort_key(r: dict) -> tuple:
        v = r["val"]
        s = v["sharpe"] if np.isfinite(v["sharpe"]) else -np.inf
        return (s, v["annual_pnl"], v["n_trades"], -r["q_percent"])

    best_q_record = max(quantile_results, key=_q_sort_key)

    test_realised = best_q_record["test"]["realised_pnls"]
    gate_block = compute_8_gate_from_pnls(test_realised)

    # Classification diagnostic on probs used by this score
    probs_for_diag = test_p_cal if score_type == "s_d" else test_raw_probs
    cls_diag = compute_classification_diagnostics(
        test_label, probs_for_diag, test_score, pnl_test_full
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
        "selected_q_percent": int(best_q_record["q_percent"]),
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


# ---------------------------------------------------------------------------
# Report writer (21 sections per 27.0c-α §11)
# ---------------------------------------------------------------------------


def _cell_signature(cell: dict) -> str:
    return f"id={cell['id']} picker={cell['picker']} score_type={cell.get('score_type', '-')}"


def write_eval_report_27_0c(
    out_path: Path,
    cell_results: list[dict],
    val_select: dict,
    verdict_info: dict,
    aggregate_info: dict,
    baseline_match_report: dict,
    sanity: dict,
    drop_stats: dict,
    split_dates: tuple,
    preflight_diag: dict,
    n_cells_run: int,
    e_pnl_full_train: dict[int, float],
    e_pnl_oof_diag: dict[int, dict],
    divergence_flags: dict[int, dict],
    calibration_diag: dict,
    reliability_diagram: dict,
    s_d_distribution: dict,
) -> None:
    t_min, t70, t85, t_max = split_dates
    lines: list[str] = []
    lines.append("# Stage 27.0c-β — S-D Calibrated EV Eval Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append(
        "Design contract: `docs/design/phase27_0c_alpha_s_d_calibrated_ev_design_memo.md` "
        "(PR #320) under Phase 27 kickoff (PR #316), post-27.0b routing review (PR #319), "
        "and inherited Phase 26 framework (PR #311 / PR #313)."
    )
    lines.append("")
    # §1
    lines.append("## 1. Mandatory clauses (clauses 1-5 verbatim; clause 6 = Phase 27 kickoff §8)")
    lines.append("")
    lines.append(
        "**1. Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness."
    )
    lines.append("")
    lines.append(
        "**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / "
        "directional-comparison / classification-quality / feature-importance / "
        "per-pair-Sharpe-contribution columns are diagnostic-only. 27.0c extends: "
        "conditional-PnL estimator constants and calibration reliability diagrams are "
        "diagnostic-only."
    )
    lines.append("")
    lines.append("**3. γ closure preservation.** PR #279 is unmodified.")
    lines.append("")
    lines.append(
        "**4. Production-readiness preservation.** X-v2 OOS gating remains required. "
        "v9 20-pair (Phase 9.12) untouched. Phase 22 frozen-OOS contract preserved."
    )
    lines.append("")
    lines.append("**5. NG#10 / NG#11 not relaxed.**")
    lines.append("")
    lines.append(
        "**6. Phase 27 scope.** R7-A admissible at kickoff; R7-B/C require separate "
        "scope amendments; R7-D NOT admissible. S-A/S-B/S-C formal at kickoff; S-D "
        "promoted to formal at 27.0c-β per kickoff §5 / PR #320; S-E requires separate "
        "amendment; S-Other NOT admissible. Phase 26 deferred items NOT subsumed."
    )
    lines.append("")
    # §2
    lines.append("## 2. D-1 binding (formal realised-PnL = inherited harness)")
    lines.append("")
    lines.append(
        "Formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask "
        "executable). Mid-to-mid PnL appears in sanity probe only. Conditional-PnL "
        "estimator Ê[PnL|c] uses the SAME bid/ask executable harness on train rows."
    )
    lines.append("")
    # §3
    lines.append("## 3. R7-A feature set (FIXED per Phase 27.0c-α §2)")
    lines.append("")
    lines.append(f"- ADMITTED: {list(ALL_FEATURES)}")
    lines.append("- NO new feature additions in 27.0c.")
    lines.append("")
    # §4
    lines.append("## 4. S-D + S-B-baseline cell definitions (per 27.0c-α §7.1)")
    lines.append("")
    lines.append("- C-sd: S-D(row) = Σ_c P_cal(c|row) · Ê[PnL|c] (calibrated EV)")
    lines.append("- C-sb-baseline: S-B(row) = raw P(TP) - P(SL) on refit-on-full-train head")
    lines.append("- 5-fold OOF protocol (seed=42); isotonic per class + per-row sum-to-1")
    lines.append(
        "- C-sb-baseline must reproduce 27.0b C-alpha0 (n_trades=34,626 / Sharpe=-0.1732 / "
        "ann_pnl=-204,664.4) or HALT with BaselineMismatchError"
    )
    lines.append("")
    # §5
    lines.append("## 5. Sanity probe (per 27.0c-α §10)")
    lines.append("")
    lines.append(f"- status: **{sanity.get('status', 'unknown')}**")
    cp_train = sanity.get("class_priors", {}).get("train", {})
    counts = cp_train.get("counts", {})
    shares = cp_train.get("shares", {})
    for cls, name in [(LABEL_TP, "TP"), (LABEL_SL, "SL"), (LABEL_TIME, "TIME")]:
        c = counts.get(cls, 0)
        s = shares.get(cls, float("nan"))
        lines.append(f"  - {name}: {c} ({s:.3%})")
    fold_block = sanity.get("oof_fold_sizes", {})
    if "fold_sizes" in fold_block:
        lines.append(
            f"- OOF fold sizes (seed={fold_block.get('seed')}): {fold_block.get('fold_sizes')} "
            f"max_delta={fold_block.get('max_size_delta')}"
        )
    zsr = sanity.get("zero_sum_row_fallback", {})
    if isinstance(zsr, dict) and ("val" in zsr or "test" in zsr):
        lines.append(
            f"- zero-sum-row fallback: val={zsr.get('val')} test={zsr.get('test')} "
            "(HALT > 0 per D-I11)"
        )
    lines.append("")
    # §6
    lines.append("## 6. Pre-flight diagnostics + row-drop + split dates")
    lines.append(f"- label rows (pre-drop): {preflight_diag.get('label_rows', 'n/a')}")
    lines.append(f"- pairs: {preflight_diag.get('pairs', 'n/a')}")
    lines.append(f"- LightGBM: {preflight_diag.get('lightgbm_available', 'n/a')}")
    lines.append(f"- formal cells run: {n_cells_run}")
    lines.append("Row-drop policy (R7-A inherited):")
    for split_name in ("train", "val", "test"):
        ds = drop_stats.get(split_name, {})
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
    # §7
    lines.append("## 7. All formal cells — primary quantile-family summary")
    lines.append("")
    lines.append(
        "| cell | picker | q% | cutoff | val_sharpe | val_ann_pnl | val_n | "
        "test_sharpe | test_ann_pnl | test_n | test_spearman | h_state |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        rm = c.get("test_realised_metrics", {})
        sp = c.get("test_formal_spearman", float("nan"))
        lines.append(
            f"| {cell['id']} | {cell['picker']} | {c.get('selected_q_percent', '-')} | "
            f"{c.get('selected_cutoff', float('nan')):+.4f} | "
            f"{c.get('val_realised_sharpe', float('nan')):.4f} | "
            f"{c.get('val_realised_annual_pnl', 0.0):+.1f} | "
            f"{c.get('val_n_trades', 0)} | "
            f"{rm.get('sharpe', float('nan')):.4f} | "
            f"{rm.get('annual_pnl', 0.0):+.1f} | "
            f"{rm.get('n_trades', 0)} | "
            f"{sp:.4f} | "
            f"{c.get('h_state', '-')} |"
        )
    lines.append("")
    # §8
    lines.append("## 8. Val-selected (cell\\*, q\\*) — FORMAL verdict source")
    lines.append("")
    sel = val_select.get("selected")
    if sel is None:
        lines.append("- no valid cell")
    else:
        cell = sel["cell"]
        rm = sel.get("test_realised_metrics", {})
        lines.append(f"- cell: {_cell_signature(cell)}")
        lines.append(f"- selected q%: {sel.get('selected_q_percent')}")
        lines.append(f"- selected cutoff: {sel.get('selected_cutoff'):+.6f}")
        lines.append(
            f"- val: n_trades={sel.get('val_n_trades')}, "
            f"Sharpe={sel.get('val_realised_sharpe', float('nan')):.4f}, "
            f"ann_pnl={sel.get('val_realised_annual_pnl', 0.0):+.1f}"
        )
        lines.append(
            f"- test: n_trades={rm.get('n_trades', 0)}, "
            f"Sharpe={rm.get('sharpe', float('nan')):.4f}, "
            f"ann_pnl={rm.get('annual_pnl', 0.0):+.1f}"
        )
        lines.append(
            f"- FORMAL Spearman(score, realised_pnl) on test: "
            f"{sel.get('test_formal_spearman', float('nan')):.4f}"
        )
    lines.append("")
    # §9
    lines.append("## 9. Aggregate H1 / H2 / H3 / H4 outcome")
    lines.append("")
    lines.append(f"- H1-weak (> {H1_WEAK_THRESHOLD}): **{verdict_info.get('h1_weak_pass')}**")
    lines.append(
        f"- H1-meaningful (≥ {H1_MEANINGFUL_THRESHOLD}): "
        f"**{verdict_info.get('h1_meaningful_pass')}**"
    )
    lines.append(f"- H2: **{verdict_info.get('h2_pass')}**")
    lines.append(f"- H3 (> {H3_REFERENCE_SHARPE}): **{verdict_info.get('h3_pass')}**")
    lines.append(f"- H4 (≥ 0): **{verdict_info.get('h4_pass')}**")
    lines.append("")
    lines.append(f"### Verdict: **{verdict_info.get('verdict')}** ({verdict_info.get('h_state')})")
    lines.append("")
    lines.append(
        "**Note**: 27.0c-β cannot mint ADOPT_CANDIDATE. H2 PASS → PROMISING_BUT_NEEDS_OOS."
    )
    lines.append("")
    # §10
    lines.append("## 10. Cross-cell verdict aggregation (per 26.0c-α §7.2)")
    lines.append(f"- per-cell branches: {aggregate_info.get('branches', [])}")
    lines.append(f"- cells agree: **{aggregate_info.get('agree')}**")
    lines.append(f"- aggregate verdict: **{aggregate_info.get('aggregate_verdict')}**")
    for pc in aggregate_info.get("per_cell", []):
        vi = pc["verdict_info"]
        lines.append(f"- {pc['cell_id']} ({pc['picker']}): {vi['verdict']} ({vi['h_state']})")
    lines.append("")
    # §11
    lines.append("## 11. MANDATORY: Baseline comparison (per 27.0c-α §11.11)")
    lines.append("")
    if sel is None:
        sig = "n/a"
        r6 = (float("nan"), float("nan"), 0, float("nan"))
    else:
        rm = sel.get("test_realised_metrics", {})
        sig = _cell_signature(sel["cell"])
        r6 = (
            rm.get("sharpe", float("nan")),
            rm.get("annual_pnl", float("nan")),
            rm.get("n_trades", 0),
            sel.get("test_formal_spearman", float("nan")),
        )
    lines.append(
        "| Aspect | 26.0c L-1 C02 (#309) | 26.0d R6-new-A C02 (#313) | "
        "27.0b C-alpha0 / S-B (#318) | 27.0c val-selected |"
    )
    lines.append("|---|---|---|---|---|")
    lines.append(
        "| Feature set | pair + direction | + atr + spread (R7-A) | + atr + spread (R7-A) | "
        "+ atr + spread (R7-A) |"
    )
    lines.append("| Score objective | S-B | S-B | S-B (≡ α=0.0 of S-C) | S-D or S-B per val-sel |")
    lines.append(
        f"| Cell signature | C02 P(TP)-P(SL) | C02 P(TP)-P(SL) | C-alpha0 (α=0.0) | {sig} |"
    )
    lines.append(f"| Test n_trades | 42,150 | 34,626 | 34,626 | {r6[2]} |")
    lines.append(f"| Test Sharpe | -0.2232 | -0.1732 | -0.1732 | {r6[0]:.4f} |")
    lines.append(f"| Test ann_pnl | -237,310.8 | -204,664.4 | -204,664.4 | {r6[1]:+.1f} |")
    lines.append(f"| Test Spearman | -0.1077 | -0.1535 | -0.1535 | {r6[3]:.4f} |")
    lines.append(
        f"| Verdict | REJECT | REJECT (+ YES_IMPROVED) | REJECT_NON_DISCRIMINATIVE | "
        f"{verdict_info.get('verdict')} |"
    )
    lines.append("")
    # §12
    lines.append("## 12. MANDATORY: C-sb-baseline reproduction check (per 27.0c-α §7.3)")
    lines.append("")
    b = baseline_match_report
    lines.append(
        f"- n_trades: observed={b.get('n_trades_observed', 0)} "
        f"baseline={b.get('n_trades_baseline', 0)} "
        f"delta={b.get('n_trades_delta', 0):+d} "
        f"match=**{b.get('n_trades_match')}**"
    )
    lines.append(
        f"- Sharpe: observed={b.get('sharpe_observed', float('nan')):.6f} "
        f"baseline={b.get('sharpe_baseline', float('nan')):.6f} "
        f"delta={b.get('sharpe_delta', float('nan')):+.6f} "
        f"(tolerance ±{BASELINE_MATCH_SHARPE_ABS_TOLERANCE}) "
        f"match=**{b.get('sharpe_match')}**"
    )
    lines.append(
        f"- ann_pnl: observed={b.get('ann_pnl_observed', float('nan')):+.3f} "
        f"baseline={b.get('ann_pnl_baseline', float('nan')):+.3f} "
        f"delta={b.get('ann_pnl_delta', float('nan')):+.3f} "
        f"(tolerance ±{BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE}) "
        f"match=**{b.get('ann_pnl_match')}**"
    )
    lines.append(f"- **all_match: {b.get('all_match')}**")
    lines.append("")
    # §13
    lines.append("## 13. MANDATORY: Per-pair Sharpe contribution table (val-selected; D4 sort)")
    lines.append("")
    if sel is None:
        lines.append("- no valid cell")
    else:
        pp = sel.get("per_pair_sharpe_contribution", {})
        rows = pp.get("per_pair", [])
        lines.append("| pair | n_trades | sharpe | share_of_total_pnl | share_of_total_trades |")
        lines.append("|---|---|---|---|---|")
        for r in rows:
            sharpe_str = f"{r['sharpe']:.4f}" if np.isfinite(r["sharpe"]) else "nan"
            lines.append(
                f"| {r['pair']} | {r['n_trades']} | {sharpe_str} | "
                f"{r['share_of_total_pnl']:+.4f} | {r['share_of_total_trades']:.4f} |"
            )
        lines.append(
            f"- total_n_trades: {pp.get('total_n_trades', 0)}; "
            f"total_pnl: {pp.get('total_pnl', 0.0):+.2f}"
        )
    lines.append("")
    # §14
    lines.append("## 14. MANDATORY: Pair concentration per cell")
    lines.append("")
    lines.append(
        "| cell | q% | val_top_pair | val_top_share | val_conc_high | "
        "test_top_pair | test_top_share |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        val_con = c.get("val_concentration", {})
        test_con = c.get("test_concentration", {})
        lines.append(
            f"| {cell['id']} | {c.get('selected_q_percent', '-')} | "
            f"{val_con.get('top_pair', '-')} | "
            f"{val_con.get('top_pair_share', float('nan')):.4f} | "
            f"{val_con.get('concentration_high', False)} | "
            f"{test_con.get('top_pair', '-')} | "
            f"{test_con.get('top_pair_share', float('nan')):.4f} |"
        )
    lines.append("")
    # §15
    lines.append("## 15. Classification-quality diagnostics (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| cell | AUC(P(TP)) | Cohen κ | logloss |")
    lines.append("|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        d = c.get("test_classification_diag", {})
        lines.append(
            f"| {cell['id']} | "
            f"{d.get('auc_tp_ovr', float('nan')):.4f} | "
            f"{d.get('cohen_kappa', float('nan')):.4f} | "
            f"{d.get('multiclass_logloss', float('nan')):.4f} |"
        )
    lines.append("")
    # §16
    lines.append("## 16. Feature importance (4-bucket; DIAGNOSTIC-ONLY)")
    lines.append("")
    fi_sel = sel.get("feature_importance", {}) if sel else {}
    b = fi_sel.get("buckets", {})
    bn = fi_sel.get("buckets_normalised", {})
    lines.append(
        f"- pair (gain): {b.get('pair', float('nan')):.1f} ({bn.get('pair', float('nan')):.3f})"
    )
    lines.append(
        f"- direction (gain): {b.get('direction', float('nan')):.1f} "
        f"({bn.get('direction', float('nan')):.3f})"
    )
    lines.append(
        f"- atr_at_signal_pip (gain): {b.get('atr_at_signal_pip', float('nan')):.1f} "
        f"({bn.get('atr_at_signal_pip', float('nan')):.3f})"
    )
    lines.append(
        f"- spread_at_signal_pip (gain): {b.get('spread_at_signal_pip', float('nan')):.1f} "
        f"({bn.get('spread_at_signal_pip', float('nan')):.3f})"
    )
    lines.append("")
    # §17 NEW
    lines.append("## 17. NEW: S-D distribution diagnostic (train/val/test; DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| split | n_finite | p5 | p25 | p50 | p75 | p95 | mean |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for split_name in ("train", "val", "test"):
        s = s_d_distribution.get(split_name, {})
        if "p50" not in s:
            lines.append(f"| {split_name} | - | - | - | - | - | - | - |")
            continue
        lines.append(
            f"| {split_name} | {s.get('n_finite', 0)} | "
            f"{s.get('p5', float('nan')):+.4f} | "
            f"{s.get('p25', float('nan')):+.4f} | "
            f"{s.get('p50', float('nan')):+.4f} | "
            f"{s.get('p75', float('nan')):+.4f} | "
            f"{s.get('p95', float('nan')):+.4f} | "
            f"{s.get('mean', float('nan')):+.4f} |"
        )
    lines.append("")
    # §18 NEW
    lines.append("## 18. NEW: Calibration reliability diagram per class (DIAGNOSTIC-ONLY)")
    lines.append("")
    for c in range(NUM_CLASSES):
        name = {LABEL_TP: "TP", LABEL_SL: "SL", LABEL_TIME: "TIME"}[c]
        lines.append(f"### Class {name}")
        lines.append("")
        lines.append(
            "| bin_lo | bin_hi | bin_count | mean_pred_raw | mean_pred_cal | freq_actual |"
        )
        lines.append("|---|---|---|---|---|---|")
        for b in reliability_diagram.get(c, []):
            lo_str = f"{b['bin_lo']:.2f}"
            hi_str = f"{b['bin_hi']:.2f}"
            count_str = f"{b['bin_count']}"
            if b["bin_count"] == 0:
                lines.append(f"| {lo_str} | {hi_str} | {count_str} | - | - | - |")
                continue
            lines.append(
                f"| {lo_str} | {hi_str} | {count_str} | "
                f"{b['bin_mean_pred_raw']:.4f} | "
                f"{b['bin_mean_pred_cal']:.4f} | "
                f"{b['bin_freq_actual']:.4f} |"
            )
        lines.append("")
    # §19 NEW
    lines.append("## 19. NEW: Conditional-PnL estimator constants (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| class | full_train Ê[PnL\\|c] | oof_aggregate | delta | rel_delta | flag |")
    lines.append("|---|---|---|---|---|---|")
    for c in range(NUM_CLASSES):
        name = {LABEL_TP: "TP", LABEL_SL: "SL", LABEL_TIME: "TIME"}[c]
        flag_block = divergence_flags.get(c, {})
        ft = flag_block.get("full_train", float("nan"))
        oof = flag_block.get("oof_aggregate", float("nan"))
        delta = flag_block.get("delta", float("nan"))
        rel = flag_block.get("rel_delta", float("nan"))
        flag = flag_block.get("divergence_flag", False)
        supp = flag_block.get("suppressed_div_by_zero", False)
        flag_str = f"{flag} (suppressed)" if supp else f"{flag}"
        rel_str = f"{rel:+.4f}" if np.isfinite(rel) else "n/a"
        lines.append(f"| {name} | {ft:+.4f} | {oof:+.4f} | {delta:+.4f} | {rel_str} | {flag_str} |")
    lines.append("")
    lines.append(
        f"Divergence threshold: |rel_delta| > {ESTIMATOR_DIVERGENCE_FRAC_THRESHOLD:.0%} "
        f"(suppressed when |full_train| < {ESTIMATOR_DIVERGENCE_DENOM_EPS:.0e}). "
        "DIAGNOSTIC-ONLY; not in formal verdict."
    )
    lines.append("")
    # §20
    lines.append("## 20. Multiple-testing caveat")
    lines.append(
        f"{n_cells_run} formal cells × {len(THRESHOLDS_QUANTILE_PERCENTS)} quantile = "
        f"{n_cells_run * len(THRESHOLDS_QUANTILE_PERCENTS)} (cell, q) pairs. "
        "PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE are hypothesis-generating only."
    )
    lines.append("")
    # §21
    lines.append(
        f"## 21. Verdict statement: **{verdict_info.get('verdict')}** "
        f"(C-sb-baseline match: {baseline_match_report.get('all_match')})"
    )
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _build_pair_runtime(pair: str, days: int) -> dict:
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_20)
    parser.add_argument("--days", type=int, default=SPAN_DAYS)
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument(
        "--sanity-probe-only",
        action="store_true",
        help="Run sanity probe and exit (no full sweep).",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Dry-run: skip writing artifacts.",
    )
    parser.add_argument(
        "--quick-mode",
        action="store_true",
        help="500 rows × 20 pairs subsample for smoke.",
    )
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 27.0c-β S-D calibrated EV eval ({len(args.pairs)} pairs) ===")
    print(
        f"K_FAV={K_FAV} K_ADV={K_ADV} H_M1={H_M1_BARS} | "
        f"quantile candidates={THRESHOLDS_QUANTILE_PERCENTS}"
    )
    print(f"R7-A FIXED: {list(ALL_FEATURES)}")
    print(f"OOF: {OOF_N_FOLDS} folds, seed={OOF_SEED}")

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

    # 5. Sanity probe (probe-only stage; OOF/cal/estimator deferred)
    sanity = run_sanity_probe_27_0c(train_df, val_df, test_df, pair_runtime_map, args.pairs)

    if args.sanity_probe_only:
        print("\n--sanity-probe-only set; exiting after probe.")
        if not args.no_write:
            (args.out_dir / "sanity_probe.json").write_text(
                json.dumps(sanity, indent=2, default=str), encoding="utf-8"
            )
            print(f"sanity probe results: {args.out_dir / 'sanity_probe.json'}")
        return 0

    # 6. Row-drop (R7-A inherited)
    print("Dropping rows with missing/non-finite R7-A new features...")
    train_df, train_drop = drop_rows_with_missing_new_features(train_df)
    val_df, val_drop = drop_rows_with_missing_new_features(val_df)
    test_df, test_drop = drop_rows_with_missing_new_features(test_df)
    drop_stats = {"train": train_drop, "val": val_drop, "test": test_drop}
    for name, ds in drop_stats.items():
        print(
            f"  {name}: n_input={ds['n_input']} n_kept={ds['n_kept']} n_dropped={ds['n_dropped']}"
        )

    # 7. Precompute realised PnL for train + val + test (D-1 binding)
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

    # 8. Build labels
    train_label = build_l1_labels_for_dataframe(train_df).to_numpy()
    val_label = build_l1_labels_for_dataframe(val_df).to_numpy()
    test_label = build_l1_labels_for_dataframe(test_df).to_numpy()

    # 9. Conditional-PnL estimator constants from train (D-1 binding)
    print("Computing conditional-PnL estimator constants from full train...")
    e_pnl_full_train = compute_class_conditional_pnl(train_label, pnl_train_full)
    print(
        f"  Ê[PnL|TP]={e_pnl_full_train[LABEL_TP]:+.4f}, "
        f"Ê[PnL|SL]={e_pnl_full_train[LABEL_SL]:+.4f}, "
        f"Ê[PnL|TIME]={e_pnl_full_train[LABEL_TIME]:+.4f}"
    )

    # 10. 5-fold OOF protocol (D10 amendment: single shared fold assignment)
    print("Running 5-fold OOF protocol (seed=42)...")
    fold_idx = make_oof_fold_assignment(len(train_label), n_folds=OOF_N_FOLDS, seed=OOF_SEED)
    x_train_all = train_df[list(ALL_FEATURES)]
    t0 = time.time()
    oof_probs = fit_oof_multiclass_head(x_train_all, train_label, fold_idx)
    print(f"  OOF protocol completed ({time.time() - t0:.1f}s; n_train={len(train_label)})")

    # 11. OOF diagnostic estimator + divergence flags
    e_pnl_oof_diag = compute_oof_class_conditional_pnl(train_label, pnl_train_full, fold_idx)
    divergence_flags = compute_estimator_divergence_flag(e_pnl_full_train, e_pnl_oof_diag)
    for c in range(NUM_CLASSES):
        name = {LABEL_TP: "TP", LABEL_SL: "SL", LABEL_TIME: "TIME"}[c]
        d = divergence_flags[c]
        rel = d.get("rel_delta", float("nan"))
        print(
            f"  {name}: full={d['full_train']:+.4f} oof_agg={d['oof_aggregate']:+.4f} "
            f"rel_delta={rel:+.4%} flag={d['divergence_flag']}"
        )

    # 12. Fit isotonic calibrators per class on OOF (calibration boundary = train OOF only)
    print("Fitting isotonic calibrators per class on OOF predictions...")
    t0 = time.time()
    calibrators = fit_isotonic_calibrators_per_class(oof_probs, train_label)
    print(f"  calibrators fit ({time.time() - t0:.1f}s)")
    calibration_diag = compute_calibration_diagnostic(calibrators, oof_probs)
    for c in range(NUM_CLASSES):
        name = {LABEL_TP: "TP", LABEL_SL: "SL", LABEL_TIME: "TIME"}[c]
        d = calibration_diag[c]
        print(
            f"  {name}: breakpoints={d['breakpoint_count']} "
            f"mean_shift={d['mean_shift']:+.4e} mean_abs_shift={d['mean_abs_shift']:.4e}"
        )

    # 13. Refit head on full train (production head for val/test scoring)
    print("Refitting multiclass head on full train (production head)...")
    t0 = time.time()
    pipeline = build_pipeline_lightgbm_multiclass_widened()
    x_val = val_df[list(ALL_FEATURES)]
    x_test = test_df[list(ALL_FEATURES)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipeline.fit(x_train_all, train_label)
    # Capture raw probs; map columns to LABEL_TP/SL/TIME indexing
    final_step = pipeline.steps[-1][1]
    classes = np.asarray(getattr(final_step, "classes_", np.arange(NUM_CLASSES)))
    val_raw_probs_native = pipeline.predict_proba(x_val)
    test_raw_probs_native = pipeline.predict_proba(x_test)
    train_raw_probs_native = pipeline.predict_proba(x_train_all)
    val_raw_probs = np.zeros((len(val_raw_probs_native), NUM_CLASSES), dtype=np.float64)
    test_raw_probs = np.zeros((len(test_raw_probs_native), NUM_CLASSES), dtype=np.float64)
    train_raw_probs = np.zeros((len(train_raw_probs_native), NUM_CLASSES), dtype=np.float64)
    for col_idx, cls in enumerate(classes):
        cls_int = int(cls)
        val_raw_probs[:, cls_int] = val_raw_probs_native[:, col_idx]
        test_raw_probs[:, cls_int] = test_raw_probs_native[:, col_idx]
        train_raw_probs[:, cls_int] = train_raw_probs_native[:, col_idx]
    feature_importance_diag = compute_feature_importance_diagnostic(pipeline)
    print(f"  refit + predict_proba: {time.time() - t0:.1f}s")
    print(
        f"  feature importance gain: "
        f"pair={feature_importance_diag['buckets'].get('pair', 0):.1f}, "
        f"direction={feature_importance_diag['buckets'].get('direction', 0):.1f}, "
        f"atr={feature_importance_diag['buckets'].get('atr_at_signal_pip', 0):.1f}, "
        f"spread={feature_importance_diag['buckets'].get('spread_at_signal_pip', 0):.1f}"
    )

    # 14. Apply isotonic + renormalise on val/test/train probs
    print("Applying isotonic calibration + per-row sum-to-1...")
    val_p_cal, n_zero_val = apply_isotonic_and_renormalise(val_raw_probs, calibrators)
    test_p_cal, n_zero_test = apply_isotonic_and_renormalise(test_raw_probs, calibrators)
    train_p_cal, n_zero_train = apply_isotonic_and_renormalise(train_raw_probs, calibrators)
    print(
        f"  zero-sum-row fallback counts: train={n_zero_train} val={n_zero_val} test={n_zero_test}"
    )

    # 15. Score S-D (C-sd) and S-B raw (C-sb-baseline)
    print("Scoring S-D + S-B (raw) on val/test...")
    val_score_s_d = compute_picker_score_s_d(val_p_cal, e_pnl_full_train)
    test_score_s_d = compute_picker_score_s_d(test_p_cal, e_pnl_full_train)
    train_score_s_d = compute_picker_score_s_d(train_p_cal, e_pnl_full_train)
    val_score_s_b_raw = compute_picker_score_s_b_raw(val_raw_probs)
    test_score_s_b_raw = compute_picker_score_s_b_raw(test_raw_probs)

    # 16. Reliability diagram on test (DIAGNOSTIC-ONLY)
    reliability_diagram = compute_reliability_diagram_per_class(
        test_raw_probs, test_p_cal, test_label
    )

    # 17. Update sanity probe with post-fit S-D/calibration info
    sanity["oof_fold_sizes"] = {
        "seed": OOF_SEED,
        "n_folds": OOF_N_FOLDS,
        "fold_sizes": [int((fold_idx == f).sum()) for f in range(OOF_N_FOLDS)],
        "max_size_delta": int(
            max([int((fold_idx == f).sum()) for f in range(OOF_N_FOLDS)])
            - min([int((fold_idx == f).sum()) for f in range(OOF_N_FOLDS)])
        ),
    }
    sanity["conditional_pnl_estimator"] = {
        "full_train": {
            "TP": float(e_pnl_full_train[LABEL_TP]),
            "SL": float(e_pnl_full_train[LABEL_SL]),
            "TIME": float(e_pnl_full_train[LABEL_TIME]),
        },
        "oof_aggregate": {
            "TP": float(e_pnl_oof_diag[LABEL_TP]["oof_aggregate_mean"]),
            "SL": float(e_pnl_oof_diag[LABEL_SL]["oof_aggregate_mean"]),
            "TIME": float(e_pnl_oof_diag[LABEL_TIME]["oof_aggregate_mean"]),
        },
        "divergence_flags": {str(k): v for k, v in divergence_flags.items()},
    }
    sanity["estimator_warn_e_pnl_tp_nonpositive"] = e_pnl_full_train[LABEL_TP] <= 0.0
    sanity["calibration_map_summary"] = {
        {LABEL_TP: "TP", LABEL_SL: "SL", LABEL_TIME: "TIME"}[c]: {
            "breakpoint_count": calibration_diag[c]["breakpoint_count"],
            "mean_shift": calibration_diag[c]["mean_shift"],
            "mean_abs_shift": calibration_diag[c]["mean_abs_shift"],
        }
        for c in range(NUM_CLASSES)
    }
    sanity["zero_sum_row_fallback"] = {"val": int(n_zero_val), "test": int(n_zero_test)}
    # S-D distribution
    s_d_dist: dict[str, dict] = {}
    for split_name, scores in [
        ("train", train_score_s_d),
        ("val", val_score_s_d),
        ("test", test_score_s_d),
    ]:
        finite = scores[np.isfinite(scores)]
        if len(finite) == 0:
            s_d_dist[split_name] = {"n_finite": 0}
            continue
        s_d_dist[split_name] = {
            "n_finite": int(len(finite)),
            "p5": float(np.quantile(finite, 0.05)),
            "p25": float(np.quantile(finite, 0.25)),
            "p50": float(np.quantile(finite, 0.50)),
            "p75": float(np.quantile(finite, 0.75)),
            "p95": float(np.quantile(finite, 0.95)),
            "mean": float(finite.mean()),
        }
    sanity["s_d_distribution"] = s_d_dist
    print(
        f"  S-D val: mean={s_d_dist.get('val', {}).get('mean', float('nan')):+.4f} "
        f"p50={s_d_dist.get('val', {}).get('p50', float('nan')):+.4f}"
    )
    print(
        f"  S-D test: mean={s_d_dist.get('test', {}).get('mean', float('nan')):+.4f} "
        f"p50={s_d_dist.get('test', {}).get('p50', float('nan')):+.4f}"
    )

    # NEW 27.0c HALT (per D-I11): zero-sum-row fallback count > 0
    if n_zero_val > 0:
        raise SanityProbeError(f"zero-sum-row fallback count on val = {n_zero_val} > 0 (per D-I11)")
    if n_zero_test > 0:
        raise SanityProbeError(
            f"zero-sum-row fallback count on test = {n_zero_test} > 0 (per D-I11)"
        )

    # 18. Build cells + evaluate
    cells = build_s_d_cells()
    n_cells_run = len(cells)
    cell_results: list[dict] = []
    for i, cell in enumerate(cells):
        t_cell = time.time()
        if cell["score_type"] == "s_d":
            val_score, test_score = val_score_s_d, test_score_s_d
        elif cell["score_type"] == "s_b_raw":
            val_score, test_score = val_score_s_b_raw, test_score_s_b_raw
        else:
            raise ValueError(f"Unknown score_type: {cell['score_type']}")
        try:
            result = evaluate_cell_27_0c(
                cell,
                train_df,
                val_df,
                test_df,
                train_label,
                val_label,
                test_label,
                val_raw_probs,
                test_raw_probs,
                val_p_cal,
                test_p_cal,
                val_score,
                test_score,
                pnl_val_full,
                pnl_test_full,
                feature_importance_diag,
            )
        except Exception as exc:
            print(f"  cell {i + 1}/{n_cells_run} FAILED: {exc!r}")
            result = {
                "cell": cell,
                "verdict": "REJECT_NON_DISCRIMINATIVE",
                "h_state": f"ERROR: {type(exc).__name__}",
                "low_power": True,
            }
        cell_results.append(result)
        rm = result.get("test_realised_metrics", {})
        sp = result.get("test_formal_spearman", float("nan"))
        print(
            f"  cell {i + 1}/{n_cells_run} {cell['id']} ({cell['picker']}) | "
            f"q={result.get('selected_q_percent', '-')} "
            f"val_sharpe={result.get('val_realised_sharpe', float('nan')):+.3f} "
            f"val_n={result.get('val_n_trades', 0):>6} | "
            f"test_sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"test_n={rm.get('n_trades', 0):>6} "
            f"test_sp={sp:+.4f} | ({time.time() - t_cell:.1f}s)"
        )

    # 19. C-sb-baseline match check (FAIL-FAST per D-I9)
    print("\n=== C-sb-baseline match check (per 27.0c-α §7.3 / D-I9) ===")
    c_sb_baseline = next((c for c in cell_results if c["cell"]["id"] == "C-sb-baseline"), None)
    if c_sb_baseline is None:
        raise BaselineMismatchError(
            "C-sb-baseline result not present in cell_results — wiring failure"
        )
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

    # 20. Val-selection + verdict + cross-cell aggregation
    val_select = select_cell_validation_only(cell_results)
    verdict_info = assign_verdict(val_select.get("selected"))
    aggregate_info = aggregate_cross_cell_verdict(cell_results)

    print("")
    print("=== Val-selected (cell*, q*) ===")
    sel = val_select.get("selected")
    if sel is None:
        print("  no valid cell")
    else:
        print(f"  cell: {_cell_signature(sel['cell'])}")
        rm = sel.get("test_realised_metrics", {})
        sp = sel.get("test_formal_spearman", float("nan"))
        print(f"  q*={sel.get('selected_q_percent')}, cutoff={sel.get('selected_cutoff'):+.6f}")
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
    print(f"=== Verdict: {verdict_info['verdict']} ({verdict_info['h_state']}) ===")
    print(f"=== Cross-cell aggregate: {aggregate_info['aggregate_verdict']} ===")

    if args.no_write:
        print("\n--no-write set; skipping artifact write.")
        return 0

    # 21. Write 21-section eval report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report_27_0c(
        report_path,
        cell_results,
        val_select,
        verdict_info,
        aggregate_info,
        baseline_match_report,
        sanity,
        drop_stats,
        (t_min, t70, t85, t_max),
        preflight_diag,
        n_cells_run,
        e_pnl_full_train,
        e_pnl_oof_diag,
        divergence_flags,
        calibration_diag,
        reliability_diagram,
        s_d_dist,
    )
    print(f"\nReport: {report_path}")

    # 22. Persist artifacts
    summary_rows: list[dict] = []
    for c in cell_results:
        cell = c["cell"]
        rm = c.get("test_realised_metrics", {})
        sp = c.get("test_formal_spearman", float("nan"))
        cd = c.get("test_classification_diag", {})
        summary_rows.append(
            {
                "cell_id": cell["id"],
                "picker_name": cell["picker"],
                "score_type": cell.get("score_type", "-"),
                "n_train": c.get("n_train", 0),
                "n_val": c.get("n_val", 0),
                "n_test": c.get("n_test", 0),
                "selected_q_percent": c.get("selected_q_percent", -1),
                "selected_cutoff": c.get("selected_cutoff", float("nan")),
                "val_realised_sharpe": c.get("val_realised_sharpe", float("nan")),
                "val_realised_annual_pnl": c.get("val_realised_annual_pnl", float("nan")),
                "val_n_trades": c.get("val_n_trades", 0),
                "val_max_dd": c.get("val_max_dd", float("nan")),
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
    summary_df.to_parquet(args.out_dir / "sweep_results.parquet")
    summary_df.to_json(args.out_dir / "sweep_results.json", orient="records", indent=2)

    aggregate = dict(verdict_info)
    aggregate["cross_cell"] = {
        "agree": aggregate_info["agree"],
        "branches": aggregate_info["branches"],
        "aggregate_verdict": aggregate_info["aggregate_verdict"],
    }
    aggregate["baseline_match_report"] = baseline_match_report
    aggregate["n_cells_run"] = n_cells_run
    aggregate["e_pnl_full_train"] = {
        "TP": float(e_pnl_full_train[LABEL_TP]),
        "SL": float(e_pnl_full_train[LABEL_SL]),
        "TIME": float(e_pnl_full_train[LABEL_TIME]),
    }
    aggregate["divergence_flags"] = {str(k): v for k, v in divergence_flags.items()}
    if val_select.get("selected") is not None:
        sel = val_select["selected"]
        sel_lite = {
            "cell": dict(sel["cell"]),
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
