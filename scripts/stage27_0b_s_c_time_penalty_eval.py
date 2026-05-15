"""Stage 27.0b-β S-C TIME penalty eval (first substantive Phase 27 sub-phase).

Implements the binding contract from PR #317 (Phase 27.0b-α design memo)
under the Phase 27 scope from PR #316 (clause 6 NEW for Phase 27).

R7-A feature family FIXED:
  pair + direction + atr_at_signal_pip + spread_at_signal_pip

S-C score-objective with closed 4-point α sweep:
  S-C(row, α) = P(TP)[row] - P(SL)[row] - α · P(TIME)[row]
  α ∈ {0.0, 0.3, 0.5, 1.0}

Boundary observations:
  α = 0.0 reduces to S-B (≡ Phase 26 C02 picker). Sanity-check cell:
    must reproduce R6-new-A C02 (PR #313) val-selected metrics within
    tolerance, OR HALT with BaselineMismatchError.
  α = 1.0 reduces to 2·P(TP) - 1, a monotone transform of P(TP)
    (≡ Phase 26 C01 picker). Same val-selected ranking as S-A.

Single model fit shared across α cells (per D10 binding): one
pipeline.fit + one predict_proba; 4 α cells compute scores from cached
probs.

D-1 BINDING (inherited from Phase 26 #309 / #313): formal realised-PnL
scoring uses the inherited _compute_realised_barrier_pnl (bid/ask
executable). Mid-to-mid PnL appears in sanity probe / label diagnostic
only and is NEVER the formal realised-PnL metric.

MANDATORY CLAUSES (clauses 1-5 verbatim; clause 6 = Phase 27 kickoff
§8 verbatim — PR #316 remains the canonical source-of-truth):

1. Phase framing. ADOPT requires both H2 PASS and the full 8-gate A0-A5
   harness.
2. Diagnostic columns prohibition. Calibration / threshold-sweep /
   directional-comparison / classification-quality / feature-importance /
   per-pair-Sharpe-contribution / α-monotonicity columns are diagnostic-
   only. ADOPT_CANDIDATE routing must not depend on any single one of them.
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
   admissible in principle but deferred. S-E (regression-on-realised-
   PnL) requires a SEPARATE scope-amendment PR (model-class change).
   S-Other is NOT admissible. Phase 26 deferred-not-foreclosed items
   (L-4 / R6-new-B / R6-new-C / Phase 25 F4 / F6 / F5-d / F5-e) are
   NOT subsumed by Phase 27; they remain under their original phase
   semantics.

PRODUCTION-MISUSE GUARDS (inherited verbatim from 26.0a-α §5.1):
GUARD 1 — research-not-production: 27.0b features stay in scripts/.
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

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage27_0b"
DATA_DIR = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage25_0b = importlib.import_module("stage25_0b_f1_volatility_expansion_eval")
stage26_0b = importlib.import_module("stage26_0b_l2_eval")
stage26_0c = importlib.import_module("stage26_0c_l1_eval")
stage26_0d = importlib.import_module("stage26_0d_r6_new_a_eval")

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
A0_MIN_ANNUAL_TRADES = stage25_0b.A0_MIN_ANNUAL_TRADES
A1_MIN_SHARPE = stage25_0b.A1_MIN_SHARPE
A2_MIN_ANNUAL_PNL = stage25_0b.A2_MIN_ANNUAL_PNL
A5_SPREAD_STRESS_PIP = stage25_0b.A5_SPREAD_STRESS_PIP
SPAN_DAYS = stage25_0b.SPAN_DAYS
SPAN_YEARS = SPAN_DAYS / 365.25
TRAIN_FRAC = stage25_0b.TRAIN_FRAC
VAL_FRAC = stage25_0b.VAL_FRAC
split_70_15_15 = stage25_0b.split_70_15_15

precompute_realised_pnl_per_row = stage26_0b.precompute_realised_pnl_per_row
compute_pair_concentration = stage26_0b.compute_pair_concentration
verify_l3_preflight = stage26_0b.verify_l3_preflight
L3PreflightError = stage26_0b.L3PreflightError

# Inherited L-1 logic
build_l1_labels_for_dataframe = stage26_0c.build_l1_labels_for_dataframe
compute_picker_score_ptp = stage26_0c.compute_picker_score_ptp
compute_picker_score_diff = stage26_0c.compute_picker_score_diff
fit_quantile_cutoff_on_val = stage26_0c.fit_quantile_cutoff_on_val
evaluate_quantile_family = stage26_0c.evaluate_quantile_family
compute_8_gate_from_pnls = stage26_0c.compute_8_gate_from_pnls
compute_classification_diagnostics = stage26_0c.compute_classification_diagnostics
compute_mid_to_mid_pnl_diagnostic = stage26_0c.compute_mid_to_mid_pnl_diagnostic
assign_verdict = stage26_0c.assign_verdict
aggregate_cross_cell_verdict = stage26_0c.aggregate_cross_cell_verdict
select_cell_validation_only = stage26_0c.select_cell_validation_only
compute_isotonic_diagnostic_appendix = stage26_0c.compute_isotonic_diagnostic_appendix
SanityProbeError = stage26_0c.SanityProbeError
_eval_threshold_mask = stage26_0c._eval_threshold_mask

# Inherited R6-new-A (R7-A) pipeline + missingness + feature importance
build_pipeline_lightgbm_multiclass_widened = stage26_0d.build_pipeline_lightgbm_multiclass_widened
drop_rows_with_missing_new_features = stage26_0d.drop_rows_with_missing_new_features
compute_feature_importance_diagnostic = stage26_0d.compute_feature_importance_diagnostic


# ---------------------------------------------------------------------------
# Binding constants (per 27.0b-α)
# ---------------------------------------------------------------------------

# Barrier geometry (inherited unchanged)
K_FAV = stage25_0b.K_FAV  # 1.5
K_ADV = stage25_0b.K_ADV  # 1.0
H_M1_BARS = stage25_0b.H_M1_BARS  # 60

# L-1 class encoding
LABEL_TP = stage26_0c.LABEL_TP
LABEL_SL = stage26_0c.LABEL_SL
LABEL_TIME = stage26_0c.LABEL_TIME
NUM_CLASSES = stage26_0c.NUM_CLASSES

# Threshold family (inherited)
THRESHOLDS_QUANTILE_PERCENTS = stage26_0c.THRESHOLDS_QUANTILE_PERCENTS

# LightGBM config (inherited; held FIXED in 27.0b)
LIGHTGBM_FIXED_CONFIG = dict(stage26_0d.LIGHTGBM_FIXED_CONFIG)

# H1/H2/H3/H4 thresholds (inherited unchanged)
H1_WEAK_THRESHOLD = stage26_0c.H1_WEAK_THRESHOLD
H1_MEANINGFUL_THRESHOLD = stage26_0c.H1_MEANINGFUL_THRESHOLD
H3_REFERENCE_SHARPE = stage26_0c.H3_REFERENCE_SHARPE

# Diagnostic constants
CONCENTRATION_HIGH_THRESHOLD = stage26_0c.CONCENTRATION_HIGH_THRESHOLD

# R7-A feature family (fixed per Phase 27.0b-α §2 / kickoff §4)
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
# NEW Phase 27.0b constants (the α sweep delta)
# ---------------------------------------------------------------------------

# Closed 4-point α grid (per 27.0b-α §4 / Decision D-T1)
ALPHA_GRID = (0.0, 0.3, 0.5, 1.0)

# α=0.0 baseline-mismatch HALT (per 27.0b-α §12.2 / Decisions D-T3 + D2)
# Baseline = Phase 26 R6-new-A C02 val-selected metrics (PR #313)
BASELINE_R6_NEW_A_C02_N_TRADES = 34626
BASELINE_R6_NEW_A_C02_SHARPE = -0.1732
BASELINE_R6_NEW_A_C02_ANN_PNL = -204664.4
BASELINE_MATCH_N_TRADES_TOLERANCE = 0  # exact match per D-T3
BASELINE_MATCH_SHARPE_ABS_TOLERANCE = 1e-4
BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE = 0.5  # pip

# Absolute-threshold diagnostic candidates per α (per 27.0b-α §6.3; diagnostic-only)
ABSOLUTE_THRESHOLDS_BY_ALPHA = {
    0.0: (0.0, 0.05, 0.10, 0.15),  # ≡ S-B inherited
    0.3: (-0.10, -0.05, 0.0, 0.05, 0.10),
    0.5: (-0.15, -0.10, -0.05, 0.0, 0.05),
    1.0: (-0.40, -0.20, -0.10, 0.0),  # ≡ S-A inherited via 2·P(TP)-1 transform
}


# ---------------------------------------------------------------------------
# NEW exception (per 27.0b-α §12.2 + D2 binding)
# ---------------------------------------------------------------------------


class BaselineMismatchError(RuntimeError):
    """Raised when C-α0 (α=0.0) fails to reproduce R6-new-A C02 baseline
    within tolerance per 27.0b-α §12.2 / D-T3.

    With α=0.0, S-C = P(TP) - P(SL) ≡ S-B ≡ Phase 26 R6-new-A C02 picker.
    With R7-A held fixed, L-1 label held fixed, model class held fixed,
    dataset / split / harness all inherited unchanged, the val-selected
    metrics on C-α0 must coincide with R6-new-A C02 exactly (n_trades;
    ≤ 1e-4 on Sharpe; ≤ 0.5 pip on ann_pnl). If they do not, something
    in the inheritance chain has drifted.
    """


# ---------------------------------------------------------------------------
# S-C picker formula (the new Phase 27.0b score-objective)
# ---------------------------------------------------------------------------


def compute_picker_score_s_c(probs: np.ndarray, alpha: float) -> np.ndarray:
    """S-C(row, α) = P(TP)[row] - P(SL)[row] - α · P(TIME)[row].

    Per 27.0b-α §3:
      - α=0.0 → equals S-B (P(TP) - P(SL))
      - α=1.0 → 2·P(TP) - 1 (monotone transform of P(TP); ≡ S-A ranking)
    """
    if probs.ndim != 2 or probs.shape[1] != NUM_CLASSES:
        raise ValueError(f"probs must have shape (N, {NUM_CLASSES}); got {probs.shape}")
    return (probs[:, LABEL_TP] - probs[:, LABEL_SL] - alpha * probs[:, LABEL_TIME]).astype(
        np.float64
    )


# ---------------------------------------------------------------------------
# Formal cell grid (per 27.0b-α §7; 4 α cells)
# ---------------------------------------------------------------------------


def build_alpha_cells() -> list[dict]:
    """27.0b formal grid: 4 cells = 1 picker (S-C) × 4 α values × raw probability.

    Per 27.0b-α §7 / D-T2: single picker per α (no companion pickers).
    """
    return [
        {"id": "C-alpha0", "alpha": 0.0, "picker": "S-C(α=0.0)"},
        {"id": "C-alpha03", "alpha": 0.3, "picker": "S-C(α=0.3)"},
        {"id": "C-alpha05", "alpha": 0.5, "picker": "S-C(α=0.5)"},
        {"id": "C-alpha10", "alpha": 1.0, "picker": "S-C(α=1.0)"},
    ]


# ---------------------------------------------------------------------------
# Absolute-threshold family (DIAGNOSTIC-ONLY per 27.0b-α §6.3)
# ---------------------------------------------------------------------------


def evaluate_absolute_family_alpha(
    score_val: np.ndarray,
    pnl_val_per_row: np.ndarray,
    score_test: np.ndarray,
    pnl_test_per_row: np.ndarray,
    alpha: float,
    span_years_val: float,
    span_years_test: float,
) -> list[dict]:
    """Per-α absolute-threshold sweep.

    DIAGNOSTIC-ONLY per 27.0b-α §6.3; NEVER enters formal verdict routing.
    """
    candidates = ABSOLUTE_THRESHOLDS_BY_ALPHA.get(alpha, ())
    results: list[dict] = []
    for thr in candidates:
        val_res = _eval_threshold_mask(pnl_val_per_row, score_val, thr, span_years_val)
        test_res = _eval_threshold_mask(pnl_test_per_row, score_test, thr, span_years_test)
        results.append({"threshold": float(thr), "val": val_res, "test": test_res})
    return results


# ---------------------------------------------------------------------------
# Per-pair Sharpe contribution table (per 27.0b-α §12.4 / D-T7; D4 sort)
# ---------------------------------------------------------------------------


def compute_per_pair_sharpe_contribution(
    df_test_aligned: pd.DataFrame,
    traded_mask: np.ndarray,
    pnl_test_full: np.ndarray,
) -> dict:
    """Per-pair: n_trades, Sharpe, share_of_total_pnl, share_of_total_trades.

    Per Decision D-T7 + D4: sort by share_of_total_pnl descending.
    DIAGNOSTIC-ONLY per 27.0b-α §10.
    """
    valid_pnl_mask = np.isfinite(pnl_test_full)
    eff_mask = traded_mask & valid_pnl_mask
    total_n_trades = int(eff_mask.sum())
    if total_n_trades == 0:
        return {"per_pair": [], "total_n_trades": 0, "total_pnl": 0.0}
    pnls = pnl_test_full[eff_mask]
    total_pnl = float(np.sum(pnls))
    pairs = df_test_aligned["pair"].to_numpy()[eff_mask]
    unique_pairs = sorted(set(map(str, pairs)))
    per_pair_rows: list[dict] = []
    for p in unique_pairs:
        pair_mask = pairs == p
        pair_pnls = pnls[pair_mask]
        n_trades_p = int(len(pair_pnls))
        sum_pnl_p = float(pair_pnls.sum())
        if n_trades_p >= 2 and pair_pnls.std(ddof=0) > 0:
            sharpe_p = float(pair_pnls.mean() / pair_pnls.std(ddof=0))
        else:
            sharpe_p = float("nan")
        share_of_pnl_p = sum_pnl_p / total_pnl if total_pnl != 0.0 else float("nan")
        share_of_trades_p = n_trades_p / total_n_trades
        per_pair_rows.append(
            {
                "pair": p,
                "n_trades": n_trades_p,
                "sharpe": sharpe_p,
                "sum_pnl": sum_pnl_p,
                "share_of_total_pnl": share_of_pnl_p,
                "share_of_total_trades": share_of_trades_p,
            }
        )
    # Sort by share_of_total_pnl descending (D4 binding; NaN-safe)
    per_pair_rows.sort(
        key=lambda r: r["share_of_total_pnl"] if np.isfinite(r["share_of_total_pnl"]) else -np.inf,
        reverse=True,
    )
    return {
        "per_pair": per_pair_rows,
        "total_n_trades": total_n_trades,
        "total_pnl": total_pnl,
    }


# ---------------------------------------------------------------------------
# α-monotonicity diagnostic (per 27.0b-α §12.3 / D-T6; D5 strict-monotonic)
# ---------------------------------------------------------------------------


def _classify_monotonicity_strict(values: list[float]) -> str:
    """Strict monotonic / mixed classification (per D5 binding; no ε-tolerance).

    Returns:
        "increasing" if all Δ > 0 (strict)
        "decreasing" if all Δ < 0 (strict)
        "non-monotonic" if Δ values have inconsistent signs (mixed)
        "mixed" if any Δ is NaN or 0 (cannot classify strictly)
    """
    arr = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(arr)):
        return "mixed"
    diffs = np.diff(arr)
    if len(diffs) == 0:
        return "mixed"
    if np.all(diffs > 0):
        return "increasing"
    if np.all(diffs < 0):
        return "decreasing"
    if np.any(diffs == 0):
        return "mixed"
    return "non-monotonic"


def compute_alpha_monotonicity_diagnostic(cell_results: list[dict]) -> dict:
    """For each α in ALPHA_GRID order: val/test Sharpe, ann_pnl, Spearman.

    DIAGNOSTIC-ONLY per 27.0b-α §12.3 + Decision D-T6. NOT consulted by
    select_cell_validation_only or assign_verdict.

    D5 binding: strict monotonic or mixed classification only; no
    ε-tolerance.
    """
    # Order by alpha ascending
    ordered = sorted(cell_results, key=lambda c: c["cell"]["alpha"])
    per_alpha: list[dict] = []
    for c in ordered:
        rm = c.get("test_realised_metrics", {})
        per_alpha.append(
            {
                "alpha": float(c["cell"]["alpha"]),
                "cell_id": c["cell"]["id"],
                "val_realised_sharpe": float(c.get("val_realised_sharpe", float("nan"))),
                "val_realised_annual_pnl": float(c.get("val_realised_annual_pnl", float("nan"))),
                "test_realised_sharpe": float(rm.get("sharpe", float("nan"))),
                "test_realised_annual_pnl": float(rm.get("annual_pnl", float("nan"))),
                "test_formal_spearman": float(c.get("test_formal_spearman", float("nan"))),
            }
        )
    val_sharpes = [r["val_realised_sharpe"] for r in per_alpha]
    test_sharpes = [r["test_realised_sharpe"] for r in per_alpha]
    test_ann = [r["test_realised_annual_pnl"] for r in per_alpha]
    test_sp = [r["test_formal_spearman"] for r in per_alpha]
    return {
        "per_alpha": per_alpha,
        "alpha_order": [r["alpha"] for r in per_alpha],
        "monotonic_val_sharpe": _classify_monotonicity_strict(val_sharpes),
        "monotonic_test_sharpe": _classify_monotonicity_strict(test_sharpes),
        "monotonic_test_ann_pnl": _classify_monotonicity_strict(test_ann),
        "monotonic_test_spearman": _classify_monotonicity_strict(test_sp),
    }


# ---------------------------------------------------------------------------
# α=0.0 baseline-mismatch check (per 27.0b-α §12.2 / D2)
# ---------------------------------------------------------------------------


def check_alpha_zero_baseline_match(c_alpha_0_result: dict) -> dict:
    """Validate that C-α0 reproduces R6-new-A C02 baseline within tolerance.

    Per 27.0b-α §12.2 / D-T3 + D2: HALT with BaselineMismatchError on
    mismatch.

    Returns a dict reporting baseline / observed / delta / status per
    metric for inclusion in the eval report §14.
    """
    rm = c_alpha_0_result.get("test_realised_metrics", {})
    n_trades = int(rm.get("n_trades", 0))
    sharpe = float(rm.get("sharpe", float("nan")))
    ann_pnl = float(rm.get("annual_pnl", float("nan")))

    n_trades_delta = n_trades - BASELINE_R6_NEW_A_C02_N_TRADES
    sharpe_delta = sharpe - BASELINE_R6_NEW_A_C02_SHARPE if np.isfinite(sharpe) else float("nan")
    ann_pnl_delta = (
        ann_pnl - BASELINE_R6_NEW_A_C02_ANN_PNL if np.isfinite(ann_pnl) else float("nan")
    )

    n_trades_match = abs(n_trades_delta) <= BASELINE_MATCH_N_TRADES_TOLERANCE
    sharpe_match = (
        np.isfinite(sharpe_delta) and abs(sharpe_delta) <= BASELINE_MATCH_SHARPE_ABS_TOLERANCE
    )
    ann_pnl_match = (
        np.isfinite(ann_pnl_delta) and abs(ann_pnl_delta) <= BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE
    )

    report = {
        "n_trades_baseline": int(BASELINE_R6_NEW_A_C02_N_TRADES),
        "n_trades_observed": int(n_trades),
        "n_trades_delta": int(n_trades_delta),
        "n_trades_match": bool(n_trades_match),
        "sharpe_baseline": float(BASELINE_R6_NEW_A_C02_SHARPE),
        "sharpe_observed": float(sharpe),
        "sharpe_delta": float(sharpe_delta) if np.isfinite(sharpe_delta) else float("nan"),
        "sharpe_match": bool(sharpe_match),
        "ann_pnl_baseline": float(BASELINE_R6_NEW_A_C02_ANN_PNL),
        "ann_pnl_observed": float(ann_pnl),
        "ann_pnl_delta": float(ann_pnl_delta) if np.isfinite(ann_pnl_delta) else float("nan"),
        "ann_pnl_match": bool(ann_pnl_match),
        "all_match": bool(n_trades_match and sharpe_match and ann_pnl_match),
    }

    if not report["all_match"]:
        failures: list[str] = []
        if not n_trades_match:
            failures.append(
                f"n_trades: observed={n_trades} baseline={BASELINE_R6_NEW_A_C02_N_TRADES} "
                f"delta={n_trades_delta} (tolerance ±{BASELINE_MATCH_N_TRADES_TOLERANCE})"
            )
        if not sharpe_match:
            failures.append(
                f"Sharpe: observed={sharpe:.6f} baseline={BASELINE_R6_NEW_A_C02_SHARPE:.6f} "
                f"delta={sharpe_delta:+.6f} (tolerance ±{BASELINE_MATCH_SHARPE_ABS_TOLERANCE})"
            )
        if not ann_pnl_match:
            failures.append(
                f"ann_pnl: observed={ann_pnl:+.3f} baseline={BASELINE_R6_NEW_A_C02_ANN_PNL:+.3f} "
                f"delta={ann_pnl_delta:+.3f} (tolerance ±{BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE})"
            )
        raise BaselineMismatchError(
            "C-alpha0 failed to reproduce Phase 26 R6-new-A C02 baseline per "
            "27.0b-α §12.2; failures: " + "; ".join(failures)
        )
    return report


# ---------------------------------------------------------------------------
# Sanity probe (extends 26.0c-α §10 + #313 §12.2 with NEW P(TIME) diagnostic)
# ---------------------------------------------------------------------------


def run_sanity_probe_27_0b(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    pairs: list[str],
    val_probs: np.ndarray | None = None,
    test_probs: np.ndarray | None = None,
) -> dict:
    """27.0b sanity probe per 27.0b-α §11.

    Inherited HALT checks (from 26.0c-α §10 / #313 §12.2):
      1. Class priors per split — HALT if class < 1%
      2. Per-pair TIME share — HALT if pair > 99% TIME
      3. Realised-PnL cache basis (bid/ask executable confirmed)
      4. Mid-to-mid PnL distribution per class on train (diagnostic)
      5. R7-A new-feature NaN rate per split — HALT > 5%
      6. R7-A positivity assertions — HALT > 1% violation

    NEW 27.0b-α §11 check (per D-T5; report-only, no HALT threshold):
      7. P(TIME) distribution per pair on val + test (only emitted after
         a model fit is available; otherwise reported as "deferred")
    """
    print("\n=== 27.0b SANITY PROBE (per 27.0b-α §11) ===")
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

    # 3. Mid-to-mid PnL distribution per class on train (diagnostic-only)
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

    # 4. Realised-PnL cache basis check (D-1 binding)
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

    # 7. NEW Phase 27.0b: P(TIME) distribution diagnostic (report-only per D-T5)
    print("  P(TIME) distribution diagnostic (NEW Phase 27.0b; report-only):")
    out["p_time_distribution"] = {}
    if val_probs is not None and test_probs is not None:
        for split_name, probs in [("val", val_probs), ("test", test_probs)]:
            p_time = probs[:, LABEL_TIME]
            finite = p_time[np.isfinite(p_time)]
            if len(finite) == 0:
                out["p_time_distribution"][split_name] = {"n_finite": 0}
                continue
            stats = {
                "n_finite": int(len(finite)),
                "mean": float(finite.mean()),
                "p5": float(np.quantile(finite, 0.05)),
                "p50": float(np.quantile(finite, 0.50)),
                "p95": float(np.quantile(finite, 0.95)),
            }
            out["p_time_distribution"][split_name] = stats
            print(
                f"    {split_name}.P(TIME): n={stats['n_finite']} "
                f"mean={stats['mean']:.4f} p5={stats['p5']:.4f} "
                f"p50={stats['p50']:.4f} p95={stats['p95']:.4f}"
            )
    else:
        out["p_time_distribution"]["status"] = "deferred (probs not yet computed)"
        print("    deferred (probs not yet computed at sanity-probe-only stage)")

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

    print("=== SANITY PROBE: PASS ===\n")
    out["status"] = "PASS"
    return out


# ---------------------------------------------------------------------------
# Per-cell evaluation (per 27.0b-α §7)
# ---------------------------------------------------------------------------


def evaluate_cell_27_0b(
    cell: dict,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    train_label: np.ndarray,
    val_label: np.ndarray,
    test_label: np.ndarray,
    val_probs: np.ndarray,
    test_probs: np.ndarray,
    pnl_val_full: np.ndarray,
    pnl_test_full: np.ndarray,
    feature_importance_diag: dict,
) -> dict:
    """27.0b cell evaluation.

    Differs from 26.0d-β evaluate_cell only in: picker is S-C(α) instead
    of P(TP) or P(TP)-P(SL); absolute thresholds are per-α (diagnostic-
    only); all other logic inherited.
    """
    alpha = float(cell["alpha"])

    score_val = compute_picker_score_s_c(val_probs, alpha)
    score_test = compute_picker_score_s_c(test_probs, alpha)

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
        score_val,
        pnl_val_full,
        score_test,
        pnl_test_full,
        VAL_SPAN_YEARS,
        TEST_SPAN_YEARS,
    )

    # SECONDARY DIAGNOSTIC family: per-α absolute thresholds
    absolute_results = evaluate_absolute_family_alpha(
        score_val,
        pnl_val_full,
        score_test,
        pnl_test_full,
        alpha,
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

    cls_diag = compute_classification_diagnostics(test_label, test_probs, score_test, pnl_test_full)
    formal_spearman = cls_diag.get("spearman_score_vs_pnl", float("nan"))

    test_df_aligned = test_df.reset_index(drop=True)
    val_df_aligned = val_df.reset_index(drop=True)
    traded_mask_test = score_test >= best_q_record["cutoff"]
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
    traded_mask_val = score_val >= best_q_record["cutoff"]
    val_concentration = compute_pair_concentration(
        val_df_aligned, traded_mask_val, valid_pnl_mask_val
    )
    test_concentration = compute_pair_concentration(
        test_df_aligned, traded_mask_test, valid_pnl_mask_test
    )

    # Per-pair Sharpe contribution table (per 27.0b-α §12.4 / D4)
    per_pair_sharpe = compute_per_pair_sharpe_contribution(
        test_df_aligned, traded_mask_test, pnl_test_full
    )

    def _abs_sort_key(r: dict) -> tuple:
        v = r["val"]
        s = v["sharpe"] if np.isfinite(v["sharpe"]) else -np.inf
        return (s, v["annual_pnl"], v["n_trades"], r["threshold"])

    best_abs_record = max(absolute_results, key=_abs_sort_key) if absolute_results else None

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
        "absolute_all": [
            {
                "threshold": r["threshold"],
                "val": {k: v for k, v in r["val"].items() if k != "realised_pnls"},
                "test": {k: v for k, v in r["test"].items() if k != "realised_pnls"},
            }
            for r in absolute_results
        ],
        "absolute_best": (
            {
                "threshold": best_abs_record["threshold"],
                "val": {k: v for k, v in best_abs_record["val"].items() if k != "realised_pnls"},
                "test": {k: v for k, v in best_abs_record["test"].items() if k != "realised_pnls"},
            }
            if best_abs_record
            else None
        ),
        "by_pair_trade_count": by_pair,
        "by_direction_trade_count": by_direction,
        "feature_importance": feature_importance_diag,
        "low_power": low_power,
        "h_state": "OK",
    }


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def _cell_signature(cell: dict) -> str:
    return f"id={cell['id']} alpha={cell['alpha']} picker={cell['picker']}"


def write_eval_report_27_0b(
    out_path: Path,
    cell_results: list[dict],
    val_select: dict,
    verdict_info: dict,
    aggregate_info: dict,
    baseline_match_report: dict,
    alpha_monotonicity: dict,
    sanity: dict,
    drop_stats: dict,
    split_dates: tuple,
    preflight_diag: dict,
    n_cells_run: int,
) -> None:
    t_min, t70, t85, t_max = split_dates
    lines: list[str] = []
    lines.append("# Stage 27.0b-β — S-C TIME Penalty Eval Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append(
        "Design contract: `docs/design/phase27_0b_alpha_s_c_time_penalty_design_memo.md` "
        "(PR #317) under Phase 27 kickoff (PR #316) and inherited Phase 26 framework "
        "(PR #311 / PR #313)."
    )
    lines.append("")
    lines.append("## 1. Mandatory clauses (clauses 1-5 verbatim; clause 6 = Phase 27 kickoff §8)")
    lines.append("")
    lines.append(
        "**1. Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness."
    )
    lines.append("")
    lines.append(
        "**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / "
        "directional-comparison / classification-quality / feature-importance / "
        "per-pair-Sharpe-contribution / α-monotonicity columns are diagnostic-only."
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
        "deferred; S-E requires separate amendment; S-Other NOT admissible. Phase 26 "
        "deferred items NOT subsumed."
    )
    lines.append("")
    lines.append("## 2. D-1 binding (formal realised-PnL = inherited harness)")
    lines.append("")
    lines.append(
        "Formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask "
        "executable). Mid-to-mid PnL appears in sanity probe only."
    )
    lines.append("")
    lines.append("## 3. R7-A feature set (FIXED per Phase 27.0b-α §2)")
    lines.append("")
    lines.append(f"- ADMITTED: {list(ALL_FEATURES)}")
    lines.append("- NO new feature additions in 27.0b.")
    lines.append("")
    lines.append("## 4. S-C score-objective + α grid (per 27.0b-α §3 / §4)")
    lines.append("")
    lines.append("- S-C(row, α) = P(TP)[row] - P(SL)[row] - α · P(TIME)[row]")
    lines.append(f"- closed α grid: {list(ALPHA_GRID)}")
    lines.append("- α=0.0 ≡ S-B (Phase 26 C02 picker)")
    lines.append("- α=1.0 ≡ 2·P(TP) - 1 (monotone transform of P(TP))")
    lines.append("")
    lines.append("## 5. Sanity probe (per 27.0b-α §11)")
    lines.append("")
    lines.append(f"- status: **{sanity.get('status', 'unknown')}**")
    cp_train = sanity.get("class_priors", {}).get("train", {})
    counts = cp_train.get("counts", {})
    shares = cp_train.get("shares", {})
    for cls, name in [(LABEL_TP, "TP"), (LABEL_SL, "SL"), (LABEL_TIME, "TIME")]:
        c = counts.get(cls, 0)
        s = shares.get(cls, float("nan"))
        lines.append(f"  - {name}: {c} ({s:.3%})")
    lines.append("- P(TIME) distribution (NEW; report-only per D-T5):")
    p_time = sanity.get("p_time_distribution", {})
    for split_name in ("val", "test"):
        s = p_time.get(split_name, {})
        if "mean" in s:
            lines.append(
                f"  - {split_name}: mean={s.get('mean', float('nan')):.4f} "
                f"p5={s.get('p5', float('nan')):.4f} "
                f"p50={s.get('p50', float('nan')):.4f} "
                f"p95={s.get('p95', float('nan')):.4f}"
            )
    lines.append("")
    lines.append("## 6. Pre-flight diagnostics")
    lines.append(f"- label rows (pre-drop): {preflight_diag.get('label_rows', 'n/a')}")
    lines.append(f"- pairs: {preflight_diag.get('pairs', 'n/a')}")
    lines.append(f"- LightGBM: {preflight_diag.get('lightgbm_available', 'n/a')}")
    lines.append(f"- formal cells run: {n_cells_run}")
    lines.append("")
    lines.append("## 7. Row-drop policy (R7-A inherited)")
    for split_name in ("train", "val", "test"):
        ds = drop_stats.get(split_name, {})
        lines.append(
            f"- {split_name}: n_input={ds.get('n_input', 0)} "
            f"n_kept={ds.get('n_kept', 0)} n_dropped={ds.get('n_dropped', 0)}"
        )
    lines.append("")
    lines.append("## 8. Split dates")
    lines.append(f"- min: {t_min}")
    lines.append(f"- train < {t70}")
    lines.append(f"- val [{t70}, {t85})")
    lines.append(f"- test [{t85}, {t_max}]")
    lines.append("")

    lines.append("## 9. All formal cells — primary quantile-family summary")
    lines.append("")
    lines.append(
        "| cell | α | q% | cutoff | val_sharpe | val_ann_pnl | val_n | "
        "test_sharpe | test_ann_pnl | test_n | test_spearman | h_state |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in sorted(cell_results, key=lambda c: c["cell"]["alpha"]):
        cell = c["cell"]
        rm = c.get("test_realised_metrics", {})
        sp = c.get("test_formal_spearman", float("nan"))
        lines.append(
            f"| {cell['id']} | {cell['alpha']} | {c.get('selected_q_percent', '-')} | "
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

    lines.append("## 10. Val-selected (cell\\*, α\\*, q\\*) — FORMAL verdict source")
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

    lines.append("## 11. Aggregate H1 / H2 / H3 / H4 outcome")
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
        "**Note**: 27.0b-β cannot mint ADOPT_CANDIDATE. H2 PASS → PROMISING_BUT_NEEDS_OOS."
    )
    lines.append("")

    lines.append("## 12. Cross-cell verdict aggregation (per 26.0c-α §7.2)")
    lines.append(f"- per-cell branches: {aggregate_info.get('branches', [])}")
    lines.append(f"- cells agree: **{aggregate_info.get('agree')}**")
    lines.append(f"- aggregate verdict: **{aggregate_info.get('aggregate_verdict')}**")
    for pc in aggregate_info.get("per_cell", []):
        vi = pc["verdict_info"]
        lines.append(f"- {pc['cell_id']} ({pc['picker']}): {vi['verdict']} ({vi['h_state']})")
    lines.append("")

    # MANDATORY §13 baseline comparison
    lines.append("## 13. MANDATORY: Baseline comparison (per 27.0b-α §12.1)")
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
        "| Aspect | Phase 26 L-1 C02 (#309) | Phase 26 R6-new-A C02 (#313) | "
        "Phase 27 27.0b val-selected |"
    )
    lines.append("|---|---|---|---|")
    lines.append(
        "| Feature set | pair + direction | + atr + spread (R7-A) | + atr + spread (R7-A fixed) |"
    )
    lines.append("| Score objective | S-B | S-B | S-C(α\\*) per val-selection |")
    lines.append(f"| Cell signature | C02 P(TP)-P(SL) | C02 P(TP)-P(SL) | {sig} |")
    lines.append(f"| Test n_trades | 42,150 | 34,626 | {r6[2]} |")
    lines.append(f"| Test Sharpe | -0.2232 | -0.1732 | {r6[0]:.4f} |")
    lines.append(f"| Test ann_pnl | -237,310.8 | -204,664.4 | {r6[1]:+.1f} |")
    lines.append(f"| Test Spearman | -0.1077 | -0.1535 | {r6[3]:.4f} |")
    lines.append(f"| Verdict | REJECT | REJECT (+ YES_IMPROVED) | {verdict_info.get('verdict')} |")
    lines.append("")

    # MANDATORY §14 α=0.0 sanity-check declaration
    lines.append("## 14. MANDATORY: α=0.0 sanity-check declaration (per 27.0b-α §12.2)")
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

    # MANDATORY §15 α-monotonicity diagnostic
    lines.append("## 15. MANDATORY: α-monotonicity diagnostic (per 27.0b-α §12.3)")
    lines.append("")
    lines.append("DIAGNOSTIC-ONLY; strict monotonic or mixed (per D-T6 + D5 binding).")
    lines.append("")
    lines.append("| α | val_sharpe | val_ann_pnl | test_sharpe | test_ann_pnl | test_spearman |")
    lines.append("|---|---|---|---|---|---|")
    for r in alpha_monotonicity.get("per_alpha", []):
        lines.append(
            f"| {r['alpha']} | {r['val_realised_sharpe']:.4f} | "
            f"{r['val_realised_annual_pnl']:+.1f} | "
            f"{r['test_realised_sharpe']:.4f} | "
            f"{r['test_realised_annual_pnl']:+.1f} | "
            f"{r['test_formal_spearman']:.4f} |"
        )
    lines.append("")
    lines.append(f"- monotonic val Sharpe: **{alpha_monotonicity.get('monotonic_val_sharpe')}**")
    lines.append(f"- monotonic test Sharpe: **{alpha_monotonicity.get('monotonic_test_sharpe')}**")
    lines.append(
        f"- monotonic test ann_pnl: **{alpha_monotonicity.get('monotonic_test_ann_pnl')}**"
    )
    lines.append(
        f"- monotonic test Spearman: **{alpha_monotonicity.get('monotonic_test_spearman')}**"
    )
    lines.append("")

    # MANDATORY §16 per-pair Sharpe contribution table
    lines.append("## 16. MANDATORY: Per-pair Sharpe contribution table (per 27.0b-α §12.4)")
    lines.append("")
    lines.append("DIAGNOSTIC-ONLY; sorted by share_of_total_pnl descending (per D4).")
    lines.append("Computed on val-selected (cell\\*, α\\*, q\\*) on test.")
    lines.append("")
    if sel is None:
        lines.append("- no valid cell; per-pair contribution unavailable")
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

    # Diagnostic appendices
    lines.append("## 17. Pair concentration per cell (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append(
        "| cell | α | q% | val_top_pair | val_top_share | val_conc_high | "
        "test_top_pair | test_top_share |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for c in sorted(cell_results, key=lambda c: c["cell"]["alpha"]):
        cell = c["cell"]
        val_con = c.get("val_concentration", {})
        test_con = c.get("test_concentration", {})
        lines.append(
            f"| {cell['id']} | {cell['alpha']} | {c.get('selected_q_percent', '-')} | "
            f"{val_con.get('top_pair', '-')} | "
            f"{val_con.get('top_pair_share', float('nan')):.4f} | "
            f"{val_con.get('concentration_high', False)} | "
            f"{test_con.get('top_pair', '-')} | "
            f"{test_con.get('top_pair_share', float('nan')):.4f} |"
        )
    lines.append("")

    lines.append("## 18. Classification-quality diagnostics (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| cell | α | AUC(P(TP)) | Cohen κ | logloss |")
    lines.append("|---|---|---|---|---|")
    for c in sorted(cell_results, key=lambda c: c["cell"]["alpha"]):
        cell = c["cell"]
        d = c.get("test_classification_diag", {})
        lines.append(
            f"| {cell['id']} | {cell['alpha']} | "
            f"{d.get('auc_tp_ovr', float('nan')):.4f} | "
            f"{d.get('cohen_kappa', float('nan')):.4f} | "
            f"{d.get('multiclass_logloss', float('nan')):.4f} |"
        )
    lines.append("")

    lines.append("## 19. Feature importance (4-bucket; DIAGNOSTIC-ONLY)")
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

    lines.append("## 20. Absolute-threshold sweep per α (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| cell | α | abs_thr | val_sharpe | val_n | test_sharpe | test_n |")
    lines.append("|---|---|---|---|---|---|---|")
    for c in sorted(cell_results, key=lambda c: c["cell"]["alpha"]):
        cell = c["cell"]
        for r in c.get("absolute_all", []):
            lines.append(
                f"| {cell['id']} | {cell['alpha']} | {r['threshold']:+.4f} | "
                f"{r['val'].get('sharpe', float('nan')):.4f} | "
                f"{r['val'].get('n_trades', 0)} | "
                f"{r['test'].get('sharpe', float('nan')):.4f} | "
                f"{r['test'].get('n_trades', 0)} |"
            )
    lines.append("")

    lines.append("## 21. Isotonic-calibration appendix — OMITTED per 26.0c-α §4.3")
    lines.append("")

    lines.append("## 22. Multiple-testing caveat")
    lines.append(
        f"{n_cells_run} formal cells × {len(THRESHOLDS_QUANTILE_PERCENTS)} quantile = "
        f"{n_cells_run * len(THRESHOLDS_QUANTILE_PERCENTS)} (cell, q) pairs. "
        "PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE are hypothesis-generating only."
    )
    lines.append("")

    lines.append(
        f"## 23. Verdict statement: **{verdict_info.get('verdict')}** "
        f"(α-monotonicity test Sharpe: {alpha_monotonicity.get('monotonic_test_sharpe')}; "
        f"α=0.0 baseline match: {baseline_match_report.get('all_match')})"
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

    print(f"=== Stage 27.0b-β S-C TIME penalty eval ({len(args.pairs)} pairs) ===")
    print(
        f"K_FAV={K_FAV} K_ADV={K_ADV} H_M1={H_M1_BARS} | "
        f"α grid={list(ALPHA_GRID)} | quantile candidates={THRESHOLDS_QUANTILE_PERCENTS}"
    )
    print(f"R7-A FIXED: {list(ALL_FEATURES)}")

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

    # 5. Sanity probe (HALTS on failure; per D1)
    # At sanity-probe-only stage we don't have val_probs/test_probs yet;
    # the P(TIME) distribution diagnostic will be deferred. After full
    # sweep, we re-emit the probe results including P(TIME) distribution.
    sanity = run_sanity_probe_27_0b(train_df, val_df, test_df, pair_runtime_map, args.pairs)

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

    # 7. Precompute realised PnL (inherited harness; cell-independent)
    print("Precomputing realised PnL per row...")
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

    # 9. SINGLE model fit shared across α cells (per D10 binding)
    print("Fitting multiclass LightGBM ONCE (shared across α cells per D10)...")
    t0 = time.time()
    pipeline = build_pipeline_lightgbm_multiclass_widened()
    x_train = train_df[list(ALL_FEATURES)]
    x_val = val_df[list(ALL_FEATURES)]
    x_test = test_df[list(ALL_FEATURES)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipeline.fit(x_train, train_label)
    val_probs = pipeline.predict_proba(x_val)
    test_probs = pipeline.predict_proba(x_test)
    feature_importance_diag = compute_feature_importance_diagnostic(pipeline)
    print(f"  fit + predict_proba: {time.time() - t0:.1f}s")
    print(
        f"  feature importance gain: "
        f"pair={feature_importance_diag['buckets'].get('pair', 0):.1f}, "
        f"direction={feature_importance_diag['buckets'].get('direction', 0):.1f}, "
        f"atr={feature_importance_diag['buckets'].get('atr_at_signal_pip', 0):.1f}, "
        f"spread={feature_importance_diag['buckets'].get('spread_at_signal_pip', 0):.1f}"
    )

    # 10. Re-emit sanity with P(TIME) distribution now that probs are available
    p_time_extra = {}
    for split_name, probs in [("val", val_probs), ("test", test_probs)]:
        p_time = probs[:, LABEL_TIME]
        finite = p_time[np.isfinite(p_time)]
        if len(finite) > 0:
            p_time_extra[split_name] = {
                "n_finite": int(len(finite)),
                "mean": float(finite.mean()),
                "p5": float(np.quantile(finite, 0.05)),
                "p50": float(np.quantile(finite, 0.50)),
                "p95": float(np.quantile(finite, 0.95)),
            }
            print(
                f"  P(TIME) {split_name}: n={len(finite)} "
                f"mean={p_time_extra[split_name]['mean']:.4f} "
                f"p50={p_time_extra[split_name]['p50']:.4f}"
            )
    sanity["p_time_distribution"] = p_time_extra

    # 11. Per-cell evaluation (4 α cells)
    cells = build_alpha_cells()
    n_cells_run = len(cells)
    cell_results: list[dict] = []
    for i, cell in enumerate(cells):
        t_cell = time.time()
        try:
            result = evaluate_cell_27_0b(
                cell,
                train_df,
                val_df,
                test_df,
                train_label,
                val_label,
                test_label,
                val_probs,
                test_probs,
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
            f"  cell {i + 1}/{n_cells_run} {cell['id']} α={cell['alpha']} | "
            f"q={result.get('selected_q_percent', '-')} "
            f"val_sharpe={result.get('val_realised_sharpe', float('nan')):+.3f} "
            f"val_n={result.get('val_n_trades', 0):>6} | "
            f"test_sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"test_n={rm.get('n_trades', 0):>6} "
            f"test_sp={sp:+.4f} | ({time.time() - t_cell:.1f}s)"
        )

    # 12. α=0.0 baseline-match check (per 27.0b-α §12.2 / D2)
    print("\n=== α=0.0 baseline-match check (per 27.0b-α §12.2 / D2) ===")
    c_alpha_0 = next((c for c in cell_results if c["cell"]["alpha"] == 0.0), None)
    if c_alpha_0 is None:
        raise BaselineMismatchError("C-alpha0 result not present in cell_results — wiring failure")
    if c_alpha_0.get("h_state") != "OK":
        raise BaselineMismatchError(
            f"C-alpha0 did not produce OK result: h_state={c_alpha_0.get('h_state')}"
        )
    baseline_match_report = check_alpha_zero_baseline_match(c_alpha_0)
    print(f"  baseline match: {baseline_match_report['all_match']}")
    for key in ("n_trades", "sharpe", "ann_pnl"):
        print(
            f"    {key}: observed={baseline_match_report[f'{key}_observed']} "
            f"baseline={baseline_match_report[f'{key}_baseline']} "
            f"delta={baseline_match_report[f'{key}_delta']:+.6g} "
            f"match={baseline_match_report[f'{key}_match']}"
        )

    # 13. Val-selection + verdict + cross-cell + α-monotonicity
    val_select = select_cell_validation_only(cell_results)
    verdict_info = assign_verdict(val_select.get("selected"))
    aggregate_info = aggregate_cross_cell_verdict(cell_results)
    alpha_monotonicity = compute_alpha_monotonicity_diagnostic(cell_results)

    print("")
    print("=== Val-selected (cell*, α*, q*) ===")
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
    print(
        f"=== α-monotonicity: val_sharpe={alpha_monotonicity['monotonic_val_sharpe']}, "
        f"test_sharpe={alpha_monotonicity['monotonic_test_sharpe']}, "
        f"test_spearman={alpha_monotonicity['monotonic_test_spearman']} ==="
    )

    if args.no_write:
        print("\n--no-write set; skipping artifact write.")
        return 0

    # 14. Write report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report_27_0b(
        report_path,
        cell_results,
        val_select,
        verdict_info,
        aggregate_info,
        baseline_match_report,
        alpha_monotonicity,
        sanity,
        drop_stats,
        (t_min, t70, t85, t_max),
        preflight_diag,
        n_cells_run,
    )
    print(f"\nReport: {report_path}")

    # 15. Persist artifacts
    summary_rows: list[dict] = []
    for c in cell_results:
        cell = c["cell"]
        rm = c.get("test_realised_metrics", {})
        sp = c.get("test_formal_spearman", float("nan"))
        cd = c.get("test_classification_diag", {})
        summary_rows.append(
            {
                "cell_id": cell["id"],
                "alpha": cell["alpha"],
                "picker_name": cell["picker"],
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
    aggregate["alpha_monotonicity"] = alpha_monotonicity
    aggregate["baseline_match_report"] = baseline_match_report
    aggregate["n_cells_run"] = n_cells_run
    aggregate["alpha_grid"] = list(ALPHA_GRID)
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
