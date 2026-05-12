"""Stage 26.0c-β L-1 ternary classification eval.

Implements the binding contract from PR #308 (26.0c-α L-1 design memo).

Reads 25.0a-β path-quality labels, encodes the triple-barrier outcome as
a ternary class label {TP, SL, TIME} = {0, 1, 2}, trains a multiclass
LightGBM with class_weight=balanced on the minimum feature set
(pair + direction), and runs 2 formal cells:
  C01 picker = P(TP)
  C02 picker = P(TP) - P(SL)

raw probabilities only; isotonic calibration is deferred (diagnostic
stub raising NotImplementedError per 26.0c-α §4.3).

Performs validation-only cell+threshold selection on the PRIMARY
quantile-of-val family {5, 10, 20, 30, 40}%. Evaluates test ONCE on the
val-selected (cell, q) pair using realised barrier PnL via inherited
M1 path re-traverse (`_compute_realised_barrier_pnl` from
stage25_0b — bid/ask executable treatment).

D-1 BINDING (per user correction on implementation plan):
  - L-1 LABEL ASSIGNMENT uses TP / SL / TIME classes.
  - FORMAL realised-PnL scoring uses the inherited
    `_compute_realised_barrier_pnl` (bid/ask executable; same harness
    as L-2 / L-3), NOT mid-to-mid PnL.
  - mid-to-mid PnL may appear in the sanity probe / label diagnostic
    but is NEVER used as the formal realised-PnL metric.

VERDICT WORDING (per user correction):
  - 26.0c-β cannot mint ADOPT_CANDIDATE; full A0-A5 is a separate PR.
  - H2 PASS path resolves to "PROMISING_BUT_NEEDS_OOS" (aligned with
    Phase 26 existing verdict tree wording).

MANDATORY CLAUSES (verbatim per 26.0c-α §12, inherited unchanged from
#299 §7 / 26.0a-α §9 / rev1 §11 / 26.0b-α §9 / 26.0b post-routing-review §12):

1. Phase 26 framing.
   Phase 26 is the entry-side return on alternative label / target
   designs on the 20-pair canonical universe. ADOPT requires both H2
   PASS and the full 8-gate A0-A5 harness.

2. Diagnostic columns prohibition.
   Calibration / threshold-sweep / directional-comparison /
   classification-quality columns are diagnostic-only.
   ADOPT_CANDIDATE routing must not depend on any single one of them.

3. γ closure preservation.
   Phase 24 γ hard-close (PR #279) is unmodified.

4. Production-readiness preservation.
   X-v2 OOS gating remains required before any production deployment.
   Production v9 20-pair (Phase 9.12 closure) remains untouched.

5. NG#10 / NG#11 not relaxed.

6. Phase 26 scope.
   Phase 26 is NOT a continuation of Phase 25's feature-axis sweep.
   F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed. (R6-new in
   post-26.0b routing review §6 still requires explicit scope
   amendment.)

PRODUCTION-MISUSE GUARDS (verbatim per 26.0a-α §5.1):

GUARD 1 — research-not-production: L-1 features stay in scripts/; not
auto-routed to feature_service.py.
GUARD 2 — threshold-sweep-diagnostic: any threshold sweep here is
diagnostic-only.
GUARD 3 — directional-comparison-diagnostic: any long/short
decomposition is diagnostic-only.
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
from scipy.stats import spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    cohen_kappa_score,
    confusion_matrix,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage26_0c"
DATA_DIR = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage25_0b = importlib.import_module("stage25_0b_f1_volatility_expansion_eval")
stage26_0b = importlib.import_module("stage26_0b_l2_eval")

PAIRS_20 = stage23_0a.PAIRS_20
load_m1_ba = stage23_0a.load_m1_ba
pip_size_for = stage23_0a.pip_size_for

load_path_quality_labels = stage25_0b.load_path_quality_labels
split_70_15_15 = stage25_0b.split_70_15_15
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

# Inherited from L-2 (stage26_0b) — cell-independent realised PnL cache
precompute_realised_pnl_per_row = stage26_0b.precompute_realised_pnl_per_row
compute_pair_concentration = stage26_0b.compute_pair_concentration
_derive_outcomes_vectorised = stage26_0b._derive_outcomes_vectorised
determine_barrier_outcome = stage26_0b.determine_barrier_outcome
verify_l3_preflight = stage26_0b.verify_l3_preflight
L3PreflightError = stage26_0b.L3PreflightError
REQUIRED_LABEL_COLUMNS = stage26_0b.REQUIRED_LABEL_COLUMNS


# ---------------------------------------------------------------------------
# Binding constants (per 26.0c-α)
# ---------------------------------------------------------------------------

# D-3: barrier geometry inherited unchanged from L-2 / L-3
K_FAV = stage25_0b.K_FAV  # 1.5
K_ADV = stage25_0b.K_ADV  # 1.0
H_M1_BARS = stage25_0b.H_M1_BARS  # 60

# Class encoding (3 disjoint classes per Decision A1)
LABEL_TP = 0
LABEL_SL = 1
LABEL_TIME = 2
NUM_CLASSES = 3

# Picker IDs (Decision B1 + B2)
PICKER_PTP = "P(TP)"
PICKER_DIFF = "P(TP)-P(SL)"
FORMAL_PICKERS = (PICKER_PTP, PICKER_DIFF)

# Threshold family (Decision C + F) — quantile-of-val is the formal verdict basis
THRESHOLDS_QUANTILE_PERCENTS = (5, 10, 20, 30, 40)

# Diagnostic-only absolute probability thresholds (NOT formal cell dimension)
ABSOLUTE_THRESHOLDS_PTP = (0.30, 0.40, 0.45, 0.50)
ABSOLUTE_THRESHOLDS_DIFF = (0.0, 0.05, 0.10, 0.15)

# 26.0c-α §4.1 binding fixed conservative LightGBM multiclass config
LIGHTGBM_FIXED_CONFIG = dict(
    objective="multiclass",
    num_class=NUM_CLASSES,
    n_estimators=200,
    learning_rate=0.03,
    num_leaves=31,
    max_depth=4,
    min_child_samples=100,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    class_weight="balanced",
)

# H1 two-tier thresholds — formal H1 = Spearman(score, realised_pnl)
H1_WEAK_THRESHOLD = 0.05
H1_MEANINGFUL_THRESHOLD = 0.10

# H3 reference (Phase 25 F1 best realised Sharpe; Decision G1 unchanged)
H3_REFERENCE_SHARPE = -0.192

# 26.0b-α §4.1 binding: CONCENTRATION_HIGH flag at >= 80% single-pair share.
# Diagnostic-only — NOT consulted by select_cell_validation_only or assign_verdict.
CONCENTRATION_HIGH_THRESHOLD = 0.80

# Sanity probe thresholds (Decision D6 + D7)
SANITY_MIN_CLASS_SHARE = 0.01
SANITY_MAX_PER_PAIR_TIME_SHARE = 0.99

# Span budgets
TEST_SPAN_YEARS = SPAN_YEARS * (1.0 - TRAIN_FRAC - VAL_FRAC)
VAL_SPAN_YEARS = SPAN_YEARS * VAL_FRAC

CATEGORICAL_COLS = ["pair", "direction"]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class SanityProbeError(RuntimeError):
    """Raised when the L-1 sanity probe halts (class share or pair degeneracy)."""


# ---------------------------------------------------------------------------
# L-1 label construction (3 disjoint classes per Decision A1)
# ---------------------------------------------------------------------------


def build_l1_labels_for_dataframe(df: pd.DataFrame) -> pd.Series:
    """Vectorised L-1 ternary label construction.

    Per 26.0c-α §2.3 binding:
      outcome ∈ {TP, SL, TIME} from triple-barrier inputs
      label = 0 (TP) | 1 (SL) | 2 (TIME)

    No spread subtraction at label construction (D-4 omitted, same as L-2).
    No continuous magnitude (class label only).
    """
    outcome = _derive_outcomes_vectorised(df).to_numpy()
    label = np.full(len(df), LABEL_TIME, dtype=np.int64)
    label[outcome == "TP"] = LABEL_TP
    label[outcome == "SL"] = LABEL_SL
    label[outcome == "TIME"] = LABEL_TIME
    return pd.Series(label, index=df.index, name="label_l1")


# ---------------------------------------------------------------------------
# Mid-to-mid base PnL — DIAGNOSTIC ONLY (sanity probe; NOT formal scoring)
# ---------------------------------------------------------------------------


def compute_mid_to_mid_pnl_diagnostic(
    df: pd.DataFrame, pair_runtime_map: dict[str, dict]
) -> np.ndarray:
    """Compute mid-to-mid PnL per row for diagnostic / sanity-probe use ONLY.

    D-1 BINDING: this is NOT the formal realised-PnL metric. The formal
    metric is `precompute_realised_pnl_per_row` (inherited harness).
    """
    outcome = _derive_outcomes_vectorised(df).to_numpy()
    atr_pip = df["atr_at_signal_pip"].to_numpy(dtype=np.float64)
    base = np.where(
        outcome == "TP",
        K_FAV * atr_pip,
        np.where(outcome == "SL", -K_ADV * atr_pip, np.nan),
    )
    time_mask = outcome == "TIME"
    if time_mask.any():
        time_rows = df.loc[time_mask, ["pair", "signal_ts", "direction", "entry_ask", "entry_bid"]]
        time_vals = np.full(int(time_mask.sum()), np.nan, dtype=np.float64)
        for i, (_, row) in enumerate(time_rows.iterrows()):
            pr = pair_runtime_map.get(row["pair"])
            if pr is None:
                continue
            val = stage26_0b._compute_time_outcome_base_pnl(
                row["pair"],
                row["signal_ts"],
                row["direction"],
                float(row["entry_ask"]),
                float(row["entry_bid"]),
                pr,
            )
            if val is not None:
                time_vals[i] = val
        base[time_mask] = time_vals
    return base


# ---------------------------------------------------------------------------
# Multiclass LightGBM pipeline (Decision E: raw probabilities only)
# ---------------------------------------------------------------------------


def build_pipeline_lightgbm_multiclass() -> Pipeline:
    """Multiclass LightGBM pipeline; class_weight=balanced; no tuning."""
    import lightgbm as lgb

    pre = ColumnTransformer(
        [
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_COLS,
            )
        ]
    )
    return Pipeline(
        [
            ("pre", pre),
            (
                "clf",
                lgb.LGBMClassifier(**LIGHTGBM_FIXED_CONFIG, verbose=-1),
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Formal cell grid (2 cells; Decision E)
# ---------------------------------------------------------------------------


def build_cells() -> list[dict]:
    """L-1 formal grid: 2 cells = 2 pickers × raw probability only.

    Per 26.0c-α §7 binding: NO isotonic, NO absolute thresholds in
    formal cell dimensions. Each cell sweeps quantile-of-val
    {5, 10, 20, 30, 40}% as the formal verdict basis.
    """
    return [
        {"id": "C01", "picker": PICKER_PTP},
        {"id": "C02", "picker": PICKER_DIFF},
    ]


# ---------------------------------------------------------------------------
# Picker score functions (Decision B1 + B2)
# ---------------------------------------------------------------------------


def compute_picker_score_ptp(probs: np.ndarray) -> np.ndarray:
    """Picker C01: raw P(TP) probability."""
    if probs.ndim != 2 or probs.shape[1] != NUM_CLASSES:
        raise ValueError(f"probs must have shape (N, {NUM_CLASSES}); got {probs.shape}")
    return probs[:, LABEL_TP].astype(np.float64)


def compute_picker_score_diff(probs: np.ndarray) -> np.ndarray:
    """Picker C02: P(TP) - P(SL)."""
    if probs.ndim != 2 or probs.shape[1] != NUM_CLASSES:
        raise ValueError(f"probs must have shape (N, {NUM_CLASSES}); got {probs.shape}")
    return (probs[:, LABEL_TP] - probs[:, LABEL_SL]).astype(np.float64)


def compute_picker_score(picker: str, probs: np.ndarray) -> np.ndarray:
    if picker == PICKER_PTP:
        return compute_picker_score_ptp(probs)
    if picker == PICKER_DIFF:
        return compute_picker_score_diff(probs)
    raise ValueError(f"unknown picker: {picker}")


# ---------------------------------------------------------------------------
# Isotonic calibration — DIAGNOSTIC-ONLY STUB (Decision F; 26.0c-α §4.3)
# ---------------------------------------------------------------------------


def compute_isotonic_diagnostic_appendix(*args, **kwargs):
    """Isotonic calibration is deferred per 26.0c-α §4.3.

    Documented reason: fitting isotonic on val AND using the same val
    to select the quantile cutoff introduces selection-overfit risk.
    The first L-1 eval tests the L-1 ternary label structure cleanly.
    """
    raise NotImplementedError(
        "isotonic deferred per 26.0c-α §4.3 (selection-overfit risk; "
        "diagnostic-only / not used in formal verdict)"
    )


# ---------------------------------------------------------------------------
# Threshold evaluation primitives (quantile primary; inherited from L-2 module)
# ---------------------------------------------------------------------------


def _per_trade_sharpe(pnls: np.ndarray) -> float:
    if len(pnls) < 2:
        return float("nan")
    std = pnls.std(ddof=0)
    return float(pnls.mean() / std) if std > 0 else float("nan")


def _max_drawdown(pnls: np.ndarray) -> float:
    if len(pnls) == 0:
        return 0.0
    cum = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cum)
    return float((running_max - cum).max())


def _annual_pnl(pnls: np.ndarray, span_years: float) -> float:
    if span_years <= 0 or len(pnls) == 0:
        return 0.0
    return float(pnls.sum() / span_years)


def _eval_threshold_mask(
    pnl_per_row: np.ndarray,
    score: np.ndarray,
    threshold: float,
    span_years: float,
) -> dict:
    """Apply a scalar threshold to picker scores; compute realised metrics
    using the INHERITED harness PnL cache (D-1: NOT mid-to-mid)."""
    traded_mask = score >= threshold
    traded_pnl = pnl_per_row[traded_mask]
    finite = np.isfinite(traded_pnl)
    realised = traded_pnl[finite]
    n_trades = int(len(realised))
    sharpe = _per_trade_sharpe(realised)
    annual_pnl = _annual_pnl(realised, span_years)
    max_dd = _max_drawdown(realised)
    return {
        "threshold": float(threshold),
        "n_trades": n_trades,
        "n_traded_above_threshold": int(traded_mask.sum()),
        "n_invalid_path": int(traded_mask.sum() - n_trades),
        "sharpe": sharpe,
        "annual_pnl": annual_pnl,
        "max_dd": max_dd,
        "realised_pnls": realised,
    }


def fit_quantile_cutoff_on_val(pred_val: np.ndarray, q_percent: int) -> float:
    """Fit the top-q% cutoff on validation predictions ONLY.

    Per 26.0c-α §7.1 binding: val ONLY; scalar cutoff applied to test.
    """
    finite = pred_val[np.isfinite(pred_val)]
    if len(finite) < 10:
        return float("inf")
    return float(np.quantile(finite, 1.0 - q_percent / 100.0))


def evaluate_quantile_family(
    score_val: np.ndarray,
    pnl_val_per_row: np.ndarray,
    score_test: np.ndarray,
    pnl_test_per_row: np.ndarray,
    span_years_val: float,
    span_years_test: float,
) -> list[dict]:
    """PRIMARY family — per 26.0c-α §4.1 / §7."""
    results: list[dict] = []
    for q_pct in THRESHOLDS_QUANTILE_PERCENTS:
        cutoff = fit_quantile_cutoff_on_val(score_val, q_pct)
        val_res = _eval_threshold_mask(pnl_val_per_row, score_val, cutoff, span_years_val)
        test_res = _eval_threshold_mask(pnl_test_per_row, score_test, cutoff, span_years_test)
        results.append(
            {
                "q_percent": int(q_pct),
                "cutoff": float(cutoff),
                "val": val_res,
                "test": test_res,
            }
        )
    return results


def _candidates_absolute_for_picker(picker: str) -> tuple[float, ...]:
    return ABSOLUTE_THRESHOLDS_DIFF if picker == PICKER_DIFF else ABSOLUTE_THRESHOLDS_PTP


def evaluate_absolute_family(
    score_val: np.ndarray,
    pnl_val_per_row: np.ndarray,
    score_test: np.ndarray,
    pnl_test_per_row: np.ndarray,
    picker: str,
    span_years_val: float,
    span_years_test: float,
) -> list[dict]:
    """SECONDARY DIAGNOSTIC family — per 26.0c-α §4.2 / §9.4.

    Diagnostic-only; NEVER used for verdict.
    """
    candidates = _candidates_absolute_for_picker(picker)
    results: list[dict] = []
    for thr in candidates:
        val_res = _eval_threshold_mask(pnl_val_per_row, score_val, thr, span_years_val)
        test_res = _eval_threshold_mask(pnl_test_per_row, score_test, thr, span_years_test)
        results.append({"threshold": float(thr), "val": val_res, "test": test_res})
    return results


# ---------------------------------------------------------------------------
# 8-gate metrics on a realised-PnL array (inherited)
# ---------------------------------------------------------------------------


def compute_8_gate_from_pnls(pnls: np.ndarray) -> dict:
    n_trades = len(pnls)
    metrics = compute_8_gate_metrics(pnls, n_trades)
    gates = gate_matrix(metrics)
    return {"metrics": metrics, "gates": gates}


# ---------------------------------------------------------------------------
# Classification-quality diagnostics — DIAGNOSTIC-ONLY (per 26.0c-α §9.3)
# ---------------------------------------------------------------------------


def compute_classification_diagnostics(
    y_true: np.ndarray, probs: np.ndarray, score: np.ndarray, score_pnl: np.ndarray
) -> dict:
    """AUC / κ / multiclass logloss / confusion matrix / per-class accuracy.

    Per 26.0c-α §6.1 / §9.3 binding: ALL diagnostic-only. None enter
    formal verdict routing.
    """
    diag: dict = {}
    # Spearman(score, realised_pnl) — the FORMAL H1 signal
    finite = np.isfinite(score) & np.isfinite(score_pnl)
    if finite.sum() >= 10 and np.std(score[finite]) > 0 and np.std(score_pnl[finite]) > 0:
        diag["spearman_score_vs_pnl"] = float(spearmanr(score[finite], score_pnl[finite]).statistic)
    else:
        diag["spearman_score_vs_pnl"] = float("nan")

    if len(y_true) == 0 or probs.size == 0:
        diag.update(
            {
                "auc_tp_ovr": float("nan"),
                "cohen_kappa": float("nan"),
                "multiclass_logloss": float("nan"),
                "confusion_matrix": [[0] * NUM_CLASSES for _ in range(NUM_CLASSES)],
                "per_class_accuracy": {
                    LABEL_TP: float("nan"),
                    LABEL_SL: float("nan"),
                    LABEL_TIME: float("nan"),
                },
                "n": 0,
            }
        )
        return diag

    pred_class = np.argmax(probs, axis=1)
    diag["n"] = int(len(y_true))
    # AUC of P(TP) one-vs-rest
    try:
        y_tp = (y_true == LABEL_TP).astype(int)
        if y_tp.sum() > 0 and y_tp.sum() < len(y_tp):
            diag["auc_tp_ovr"] = float(roc_auc_score(y_tp, probs[:, LABEL_TP]))
        else:
            diag["auc_tp_ovr"] = float("nan")
    except ValueError:
        diag["auc_tp_ovr"] = float("nan")
    try:
        diag["cohen_kappa"] = float(cohen_kappa_score(y_true, pred_class))
    except ValueError:
        diag["cohen_kappa"] = float("nan")
    try:
        diag["multiclass_logloss"] = float(log_loss(y_true, probs, labels=list(range(NUM_CLASSES))))
    except ValueError:
        diag["multiclass_logloss"] = float("nan")
    try:
        cm = confusion_matrix(y_true, pred_class, labels=list(range(NUM_CLASSES)))
        diag["confusion_matrix"] = cm.tolist()
        per_class_acc: dict = {}
        for cls in range(NUM_CLASSES):
            total = int(cm[cls].sum())
            per_class_acc[cls] = float(cm[cls, cls] / total) if total > 0 else float("nan")
        diag["per_class_accuracy"] = per_class_acc
    except ValueError:
        diag["confusion_matrix"] = [[0] * NUM_CLASSES for _ in range(NUM_CLASSES)]
        diag["per_class_accuracy"] = {cls: float("nan") for cls in range(NUM_CLASSES)}
    return diag


# ---------------------------------------------------------------------------
# Sanity probe (per 26.0c-α §10; halts on failure)
# ---------------------------------------------------------------------------


def run_sanity_probe(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    pairs: list[str],
) -> dict:
    """Per 26.0c-α §10 binding — halt if class / pair degeneracy detected.

    Confirms:
      1. TP / SL / TIME class shares overall and per pair
      2. No single pair has > 99% TIME-class share
      3. Each class > 1% of total rows
      4. Realised-PnL cache uses inherited harness basis (not mid-to-mid)
    """
    print("\n=== L-1 SANITY PROBE (per 26.0c-α §10) ===")
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

    # 2. Per-pair TIME-class share on train (degeneracy check)
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
    for p, s in over_99_pairs:
        print(f"    {p}: TIME share = {s:.4f}")

    # 3. Mid-to-mid PnL distribution per class on train (label/probe diagnostic ONLY)
    print("  mid-to-mid PnL distribution per class on TRAIN (diagnostic; NOT formal):")
    mid_train = compute_mid_to_mid_pnl_diagnostic(train_df, pair_runtime_map)
    out["mid_to_mid_per_class_train"] = {}
    for cls, name in [(LABEL_TP, "TP"), (LABEL_SL, "SL"), (LABEL_TIME, "TIME")]:
        mask = (train_label == cls) & np.isfinite(mid_train)
        if mask.sum() == 0:
            out["mid_to_mid_per_class_train"][name] = {"n": 0}
            print(f"    {name}: n=0 (no valid mid-to-mid pnl)")
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

    # 4. Confirm realised PnL cache uses inherited harness basis (NOT mid-to-mid)
    print("  realised-PnL cache basis check (per D-1 binding):")
    pnl_cache_sig = inspect.signature(precompute_realised_pnl_per_row)
    if "spread_factor" in pnl_cache_sig.parameters or "mid_to_mid" in pnl_cache_sig.parameters:
        raise SanityProbeError(
            "precompute_realised_pnl_per_row signature exposes spread_factor / mid_to_mid — "
            "inherited harness basis violated"
        )
    barrier_pnl_src = inspect.getsource(_compute_realised_barrier_pnl)
    # Inherited harness must reference bid_h / ask_l / ask_h / bid_l (executable bid/ask)
    if not all(tok in barrier_pnl_src for tok in ["bid_h", "ask_l", "ask_h", "bid_l"]):
        raise SanityProbeError(
            "_compute_realised_barrier_pnl does not reference bid_h/ask_l/ask_h/bid_l — "
            "executable bid/ask treatment cannot be confirmed"
        )
    out["realised_pnl_cache_basis"] = "inherited_compute_realised_barrier_pnl_bid_ask_executable"
    print("    OK: bid/ask executable treatment confirmed in inherited harness")

    # Halt conditions
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
            f"{len(over_99_pairs)} pair(s) have TIME-share over "
            f"{SANITY_MAX_PER_PAIR_TIME_SHARE:.0%}: {over_99_pairs[:5]}"
        )

    print("=== SANITY PROBE: PASS ===\n")
    out["status"] = "PASS"
    return out


# ---------------------------------------------------------------------------
# Per-cell evaluation
# ---------------------------------------------------------------------------


def evaluate_cell(
    cell: dict,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    train_label: np.ndarray,
    val_label: np.ndarray,
    test_label: np.ndarray,
    train_probs: np.ndarray | None,
    val_probs: np.ndarray,
    test_probs: np.ndarray,
    pnl_val_full: np.ndarray,
    pnl_test_full: np.ndarray,
) -> dict:
    """Evaluate one L-1 cell (picker × quantile family).

    Per 26.0c-α §7.1: A0-prefilter + tie-breakers on val realised PnL.
    Per 26.0c-α §9.4: absolute thresholds reported but NOT verdict basis.
    Per D-1: realised-PnL cache uses inherited harness (NOT mid-to-mid).
    """
    picker = cell["picker"]

    score_val = compute_picker_score(picker, val_probs)
    score_test = compute_picker_score(picker, test_probs)

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
            "skip_reason": "insufficient sample after label-NaN drop",
        }

    # PRIMARY family: quantile-of-val
    quantile_results = evaluate_quantile_family(
        score_val,
        pnl_val_full,
        score_test,
        pnl_test_full,
        VAL_SPAN_YEARS,
        TEST_SPAN_YEARS,
    )

    # SECONDARY DIAGNOSTIC family: absolute thresholds
    absolute_results = evaluate_absolute_family(
        score_val,
        pnl_val_full,
        score_test,
        pnl_test_full,
        picker,
        VAL_SPAN_YEARS,
        TEST_SPAN_YEARS,
    )

    # Pick best q on val by realised Sharpe; tie-breakers per 26.0c-α §7.1
    def _q_sort_key(r: dict) -> tuple:
        v = r["val"]
        s = v["sharpe"] if np.isfinite(v["sharpe"]) else -np.inf
        return (s, v["annual_pnl"], v["n_trades"], -r["q_percent"])

    best_q_record = max(quantile_results, key=_q_sort_key)

    # Test 8-gate metrics for the best quantile (formal verdict source)
    test_realised = best_q_record["test"]["realised_pnls"]
    gate_block = compute_8_gate_from_pnls(test_realised)

    # Classification diagnostics on test (diagnostic-only, includes Spearman(score, pnl))
    cls_diag = compute_classification_diagnostics(test_label, test_probs, score_test, pnl_test_full)
    # Formal H1 = Spearman(score, realised_pnl) on test set
    formal_spearman = cls_diag.get("spearman_score_vs_pnl", float("nan"))

    # Per-pair / per-direction trade count on val-selected (cell, q) on test
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

    # Pair concentration (DIAGNOSTIC-ONLY per 26.0c-α §9.2)
    valid_pnl_mask_val = np.isfinite(pnl_val_full)
    traded_mask_val = score_val >= best_q_record["cutoff"]
    val_concentration = compute_pair_concentration(
        val_df_aligned, traded_mask_val, valid_pnl_mask_val
    )
    test_concentration = compute_pair_concentration(
        test_df_aligned, traded_mask_test, valid_pnl_mask_test
    )

    # Best absolute (diagnostic only)
    def _abs_sort_key(r: dict) -> tuple:
        v = r["val"]
        s = v["sharpe"] if np.isfinite(v["sharpe"]) else -np.inf
        return (s, v["annual_pnl"], v["n_trades"], r["threshold"])

    best_abs_record = max(absolute_results, key=_abs_sort_key)

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
        # Formal H1 source: Spearman(score, realised_pnl) on test
        "test_formal_spearman": float(formal_spearman),
        # Pair concentration (DIAGNOSTIC-ONLY)
        "val_concentration": val_concentration,
        "test_concentration": test_concentration,
        # Classification quality diagnostics (DIAGNOSTIC-ONLY)
        "test_classification_diag": cls_diag,
        # Absolute family (DIAGNOSTIC-ONLY)
        "absolute_all": [
            {
                "threshold": r["threshold"],
                "val": {k: v for k, v in r["val"].items() if k != "realised_pnls"},
                "test": {k: v for k, v in r["test"].items() if k != "realised_pnls"},
            }
            for r in absolute_results
        ],
        "absolute_best": {
            "threshold": best_abs_record["threshold"],
            "val": {k: v for k, v in best_abs_record["val"].items() if k != "realised_pnls"},
            "test": {k: v for k, v in best_abs_record["test"].items() if k != "realised_pnls"},
        },
        "by_pair_trade_count": by_pair,
        "by_direction_trade_count": by_direction,
        "low_power": low_power,
        "h_state": "OK",
    }


# ---------------------------------------------------------------------------
# Cell selection (validation-only; per 26.0c-α §7.1)
# ---------------------------------------------------------------------------


def select_cell_validation_only(cell_results: list[dict]) -> dict:
    """Pick the val-selected cell by max val Sharpe under A0-equivalent prefilter.

    Tie-breakers (per 26.0c-α §7.1):
      1. max val realised Sharpe
      2. max val annual_pnl
      3. max val Spearman (NOTE: actually val_n_trades here as tie-breaker; Spearman is test-side)
      4. smaller quantile (more selective)
    """
    a0_min_val_trades = A0_MIN_ANNUAL_TRADES * VAL_SPAN_YEARS

    valid = [
        c
        for c in cell_results
        if c.get("h_state") == "OK" and np.isfinite(c.get("val_realised_sharpe", float("nan")))
    ]
    if not valid:
        return {
            "selected": None,
            "reason": "no valid cell",
            "low_val_trades_flag": False,
        }

    eligible = [c for c in valid if c.get("val_n_trades", 0) >= a0_min_val_trades]
    low_val_trades_flag = False
    if eligible:
        candidates = eligible
    else:
        candidates = valid
        low_val_trades_flag = True

    def _key(c: dict) -> tuple:
        sharpe = c["val_realised_sharpe"]
        annual_pnl = c["val_realised_annual_pnl"]
        max_dd = c["val_max_dd"]
        q = c.get("selected_q_percent", 99)
        return (sharpe, annual_pnl, -max_dd, -q)

    best = max(candidates, key=_key)
    return {
        "selected": best,
        "reason": (
            "selected by max val realised Sharpe under A0-equivalent prefilter"
            if not low_val_trades_flag
            else "fallback selection (no candidate met A0-equivalent)"
        ),
        "low_val_trades_flag": low_val_trades_flag,
        "a0_min_val_trades": float(a0_min_val_trades),
    }


# ---------------------------------------------------------------------------
# Cross-cell verdict aggregation (per 26.0c-α §7.2)
# ---------------------------------------------------------------------------


def aggregate_cross_cell_verdict(cell_results: list[dict]) -> dict:
    """Per 26.0c-α §7.2: agree → single verdict; disagree → report each
    cell's branch separately (NO auto-resolution; routes to routing review).
    """
    per_cell_verdicts: list[dict] = []
    for c in cell_results:
        if c.get("h_state") != "OK":
            per_cell_verdicts.append(
                {
                    "picker": c["cell"]["picker"],
                    "cell_id": c["cell"]["id"],
                    "verdict_info": assign_verdict(None),
                }
            )
            continue
        v = assign_verdict(c)
        per_cell_verdicts.append(
            {
                "picker": c["cell"]["picker"],
                "cell_id": c["cell"]["id"],
                "verdict_info": v,
            }
        )

    branches = {pv["verdict_info"]["verdict"] for pv in per_cell_verdicts}
    agree = len(branches) == 1
    return {
        "per_cell": per_cell_verdicts,
        "agree": agree,
        "branches": sorted(branches),
        "aggregate_verdict": (
            per_cell_verdicts[0]["verdict_info"]["verdict"]
            if agree
            else "SPLIT_VERDICT_ROUTE_TO_REVIEW"
        ),
    }


# ---------------------------------------------------------------------------
# Verdict tree (per 26.0c-α §6; H1 = Spearman(score, realised_pnl))
# ---------------------------------------------------------------------------


def assign_verdict(val_selected: dict | None) -> dict:
    """Verdict tree per 26.0c-α §6 + user wording correction:
    H2 PASS path → PROMISING_BUT_NEEDS_OOS (NOT ADOPT_CANDIDATE;
    A0-A5 8-gate harness is a separate PR).
    """
    if val_selected is None:
        return {
            "verdict": "REJECT_NON_DISCRIMINATIVE",
            "h_state": "NO_VALID_CELL",
            "h1_weak_pass": False,
            "h1_meaningful_pass": False,
            "h2_pass": False,
            "h3_pass": False,
            "h4_pass": False,
        }
    spearman = val_selected.get("test_formal_spearman", float("nan"))
    gates = val_selected.get("test_gates", {})
    metrics = val_selected.get("test_realised_metrics", {})
    test_sharpe = metrics.get("sharpe", float("nan"))

    h1_weak = np.isfinite(spearman) and spearman > H1_WEAK_THRESHOLD
    h1_meaningful = np.isfinite(spearman) and spearman >= H1_MEANINGFUL_THRESHOLD
    h2_pass = gates.get("A1", False) and gates.get("A2", False)
    h3_pass = np.isfinite(test_sharpe) and test_sharpe > H3_REFERENCE_SHARPE
    h4_pass = np.isfinite(test_sharpe) and test_sharpe >= 0.0

    if not h1_weak:
        verdict, h_state = "REJECT_NON_DISCRIMINATIVE", "H1_WEAK_FAIL"
    elif not h1_meaningful:
        verdict, h_state = "REJECT_WEAK_SIGNAL_ONLY", "H1_WEAK_PASS_ONLY"
    elif not h2_pass:
        if h3_pass:
            verdict, h_state = "REJECT_BUT_INFORMATIVE_IMPROVED", "H1m_PASS_H2_FAIL_H3_PASS"
        else:
            verdict, h_state = "REJECT_BUT_INFORMATIVE_FLAT", "H1m_PASS_H2_FAIL_H3_FAIL"
    else:
        # H2 PASS path — 26.0c-β cannot mint ADOPT_CANDIDATE; A0-A5 is separate.
        # Aligned with Phase 26 verdict tree wording: PROMISING_BUT_NEEDS_OOS.
        verdict, h_state = "PROMISING_BUT_NEEDS_OOS", "H2_PASS_AWAITS_A0_A5"
    return {
        "verdict": verdict,
        "h_state": h_state,
        "h1_weak_pass": bool(h1_weak),
        "h1_meaningful_pass": bool(h1_meaningful),
        "h2_pass": bool(h2_pass),
        "h3_pass": bool(h3_pass),
        "h4_pass": bool(h4_pass),
        "h3_reference_sharpe": H3_REFERENCE_SHARPE,
    }


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def _cell_signature(cell: dict) -> str:
    return f"id={cell['id']} picker={cell['picker']}"


def write_eval_report(
    out_path: Path,
    cell_results: list[dict],
    val_select: dict,
    verdict_info: dict,
    aggregate_info: dict,
    sanity: dict,
    split_dates: tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp],
    preflight_diag: dict,
    n_cells_run: int,
) -> None:
    t_min, t70, t85, t_max = split_dates
    lines: list[str] = []
    lines.append("# Stage 26.0c-β — L-1 Ternary Classification Eval")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase26_0c_alpha_l1_design_memo.md` (PR #308).")
    lines.append("")
    lines.append(
        "L-1 = ternary classification {TP=0, SL=1, TIME=2}. Multiclass LightGBM with "
        "class_weight=balanced on the minimum feature set (pair + direction). "
        "Two formal cells: picker = P(TP) and P(TP)-P(SL); raw probabilities only "
        "(isotonic deferred per §4.3). Quantile-of-val {5,10,20,30,40}% is the "
        "PRIMARY (formal) verdict basis. Absolute probability thresholds and "
        "classification diagnostics (AUC / κ / logloss / confusion matrix / "
        "per-class accuracy) are DIAGNOSTIC-ONLY. Formal H1 = Spearman(picker score, "
        "realised PnL via inherited M1 path harness)."
    )
    lines.append("")
    lines.append("## Mandatory clauses (verbatim per 26.0c-α §12)")
    lines.append("")
    lines.append(
        "**1. Phase 26 framing.** Phase 26 is the entry-side return on alternative "
        "label / target designs on the 20-pair canonical universe. ADOPT requires "
        "both H2 PASS and the full 8-gate A0-A5 harness."
    )
    lines.append("")
    lines.append(
        "**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / "
        "directional-comparison / classification-quality columns are diagnostic-only. "
        "ADOPT_CANDIDATE routing must not depend on any single one of them."
    )
    lines.append("")
    lines.append("**3. γ closure preservation.** PR #279 is unmodified.")
    lines.append("")
    lines.append(
        "**4. Production-readiness preservation.** X-v2 OOS gating remains required "
        "before any production deployment. v9 20-pair (Phase 9.12) remains untouched."
    )
    lines.append("")
    lines.append("**5. NG#10 / NG#11 not relaxed.**")
    lines.append("")
    lines.append(
        "**6. Phase 26 scope.** Phase 26 is NOT a continuation of Phase 25's "
        "feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed. "
        "R6-new requires explicit scope amendment."
    )
    lines.append("")
    lines.append("## D-1 binding (formal realised-PnL = inherited harness)")
    lines.append("")
    lines.append(
        "L-1 LABEL ASSIGNMENT uses TP / SL / TIME classes, but FORMAL realised-PnL "
        "scoring uses inherited `_compute_realised_barrier_pnl` (bid/ask executable; "
        "same harness as L-2 / L-3). mid-to-mid PnL appears in the sanity probe / "
        "label diagnostic ONLY and is NEVER the formal realised-PnL metric."
    )
    lines.append("")
    lines.append("## Production-misuse guards")
    lines.append("")
    lines.append("**GUARD 1**: research-not-production.")
    lines.append("")
    lines.append("**GUARD 2**: threshold-sweep-diagnostic.")
    lines.append("")
    lines.append("**GUARD 3**: directional-comparison-diagnostic.")
    lines.append("")
    lines.append("## Sanity probe results (per 26.0c-α §10)")
    lines.append("")
    lines.append(f"- status: **{sanity.get('status', 'unknown')}**")
    lines.append("- class priors (train):")
    cp_train = sanity.get("class_priors", {}).get("train", {})
    counts = cp_train.get("counts", {})
    shares = cp_train.get("shares", {})
    for cls, name in [(LABEL_TP, "TP"), (LABEL_SL, "SL"), (LABEL_TIME, "TIME")]:
        c = counts.get(cls, 0)
        s = shares.get(cls, float("nan"))
        lines.append(f"  - {name}: {c} ({s:.3%})")
    over_pairs = [
        p
        for p, v in sanity.get("per_pair_time_share", {}).items()
        if np.isfinite(v.get("time_share", float("nan")))
        and v["time_share"] > SANITY_MAX_PER_PAIR_TIME_SHARE
    ]
    lines.append(
        f"- per-pair TIME-share > {SANITY_MAX_PER_PAIR_TIME_SHARE:.0%} pairs: {over_pairs}"
    )
    lines.append(f"- realised-PnL cache basis: {sanity.get('realised_pnl_cache_basis', 'unknown')}")
    lines.append("")
    lines.append("## Pre-flight diagnostics")
    lines.append("")
    lines.append(f"- label rows: {preflight_diag['label_rows']}")
    lines.append(f"- horizon_bars (M1): {preflight_diag['horizon_bars']}")
    lines.append(f"- pairs: {preflight_diag['pairs']}")
    lines.append(f"- LightGBM available: {preflight_diag['lightgbm_available']}")
    if preflight_diag.get("lightgbm_version"):
        lines.append(f"- LightGBM version: {preflight_diag['lightgbm_version']}")
    lines.append(f"- formal cells run: {n_cells_run}")
    lines.append("")
    lines.append("## Validation-only cell + quantile selection (per 26.0c-α §7.1)")
    lines.append("")
    lines.append(
        "Pre-filter: candidates with `val_n_trades >= A0-equivalent`. "
        "If none, LOW_VAL_TRADES flag is set; fallback to all valid."
    )
    lines.append("")
    lines.append("Tie-breakers (deterministic):")
    lines.append("1. max val realised Sharpe (primary)")
    lines.append("2. max val annual_pnl")
    lines.append("3. lower val MaxDD")
    lines.append("4. smaller q% (more selective; final deterministic tie-breaker)")
    lines.append("")
    lines.append(
        f"- A0-equivalent val trade threshold: {val_select.get('a0_min_val_trades', 0):.1f}"
    )
    lines.append(f"- LOW_VAL_TRADES flag: {val_select.get('low_val_trades_flag', False)}")
    lines.append("")
    lines.append("## Split dates")
    lines.append("")
    lines.append(f"- min: {t_min}")
    lines.append(f"- train < {t70}")
    lines.append(f"- val [{t70}, {t85})")
    lines.append(f"- test [{t85}, {t_max}]")
    lines.append("")

    # Cell results table (primary quantile family)
    lines.append("## All formal cells — primary quantile-family summary")
    lines.append("")
    lines.append(
        "| cell | picker | q% | cutoff | val_sharpe | val_ann_pnl | val_n | "
        "test_sharpe | test_ann_pnl | test_n | test_spearman | A4 | A5_ann | h_state |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
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
            f"{rm.get('a4_n_positive', 0)} | "
            f"{rm.get('a5_stressed_annual_pnl', float('nan')):+.1f} | "
            f"{c.get('h_state', '-')} |"
        )
    lines.append("")

    # Val-selected cell (formal verdict source)
    lines.append("## Val-selected (cell*, q*) — FORMAL verdict source (test touched once)")
    lines.append("")
    sel = val_select.get("selected")
    if sel is None:
        lines.append("- no valid cell")
    else:
        cell = sel["cell"]
        lines.append(f"- cell: {_cell_signature(cell)}")
        lines.append(f"- selected q%: {sel.get('selected_q_percent')}")
        lines.append(f"- selected cutoff (val-fit scalar): {sel.get('selected_cutoff'):+.6f}")
        lines.append(
            f"- val: n_trades={sel.get('val_n_trades')}, "
            f"Sharpe={sel.get('val_realised_sharpe', float('nan')):.4f}, "
            f"ann_pnl={sel.get('val_realised_annual_pnl', 0.0):+.1f}, "
            f"MaxDD={sel.get('val_max_dd', 0.0):.1f}"
        )
        rm = sel.get("test_realised_metrics", {})
        gates = sel.get("test_gates", {})
        lines.append(
            f"- test: n_trades={rm.get('n_trades', 0)}, "
            f"Sharpe={rm.get('sharpe', float('nan')):.4f}, "
            f"ann_pnl={rm.get('annual_pnl', 0.0):+.1f}, "
            f"MaxDD={rm.get('max_dd', 0.0):.1f}, "
            f"A4_pos={rm.get('a4_n_positive', 0)}/4, "
            f"A5_stress_ann_pnl={rm.get('a5_stressed_annual_pnl', float('nan')):+.1f}"
        )
        gate_str = " ".join(f"{k}={'OK' if v else 'x'}" for k, v in gates.items())
        lines.append(f"- gates: {gate_str}")
        lines.append(
            f"- FORMAL Spearman(score, realised_pnl) on test: "
            f"{sel.get('test_formal_spearman', float('nan')):.4f}"
        )
        lines.append(f"- by-pair trade count: {sel.get('by_pair_trade_count', {})}")
        lines.append(f"- by-direction trade count: {sel.get('by_direction_trade_count', {})}")
    lines.append("")

    # Aggregate H1/H2/H3/H4 + verdict
    lines.append("## Aggregate H1 / H2 / H3 / H4 outcome (val-selected (cell*, q*) on test)")
    lines.append("")
    lines.append(
        f"- H1-weak (Spearman > {H1_WEAK_THRESHOLD}): **{verdict_info.get('h1_weak_pass')}**"
    )
    lines.append(
        f"- H1-meaningful (Spearman >= {H1_MEANINGFUL_THRESHOLD}): "
        f"**{verdict_info.get('h1_meaningful_pass')}**"
    )
    lines.append(
        f"- H2 (A1 Sharpe >= {A1_MIN_SHARPE} AND A2 ann_pnl >= {A2_MIN_ANNUAL_PNL}): "
        f"**{verdict_info.get('h2_pass')}**"
    )
    lines.append(
        f"- H3 (realised Sharpe > Phase 25 best F1 {H3_REFERENCE_SHARPE}): "
        f"**{verdict_info.get('h3_pass')}**"
    )
    lines.append(
        f"- H4 (realised Sharpe >= 0; structural-gap escape): **{verdict_info.get('h4_pass')}**"
    )
    lines.append("")
    lines.append(f"### Verdict: **{verdict_info.get('verdict')}** ({verdict_info.get('h_state')})")
    lines.append("")
    lines.append(
        "**Note**: 26.0c-β cannot mint ADOPT_CANDIDATE. H2 PASS path resolves to "
        "PROMISING_BUT_NEEDS_OOS pending the separate A0-A5 8-gate harness PR."
    )
    lines.append("")

    # Cross-cell verdict aggregation (per 26.0c-α §7.2)
    lines.append("## Cross-cell verdict aggregation (per 26.0c-α §7.2)")
    lines.append("")
    lines.append(f"- per-cell branches: {aggregate_info.get('branches', [])}")
    lines.append(f"- cells agree: **{aggregate_info.get('agree')}**")
    lines.append(f"- aggregate verdict: **{aggregate_info.get('aggregate_verdict')}**")
    lines.append("")
    for pc in aggregate_info.get("per_cell", []):
        vi = pc["verdict_info"]
        lines.append(f"- {pc['cell_id']} ({pc['picker']}): {vi['verdict']} ({vi['h_state']})")
    lines.append("")

    # L-1 vs L-2 vs L-3 comparison (MANDATORY per 26.0c-α §9.6)
    lines.append("## L-1 vs L-2 vs L-3 comparison (mandatory section per 26.0c-α §9.6)")
    lines.append("")
    lines.append(
        "L-3 and L-2 reference values are from PR #303 (26.0a-β rev1) and PR #306 "
        "(26.0b-β) eval reports respectively. They are FIXED and do NOT recompute."
    )
    lines.append("")
    # L-3 / L-2 reference baseline (fixed)
    l3_val_sharpe = -0.2232
    l3_val_ann_pnl = -237310.8
    l3_val_n_trades = 42150
    l3_test_spearman = -0.1419

    l2_val_sharpe = -0.2232
    l2_val_ann_pnl = -237310.8
    l2_val_n_trades = 42150
    l2_test_spearman = -0.1139

    if sel is None:
        l1_val_sharpe = float("nan")
        l1_val_ann_pnl = float("nan")
        l1_val_n_trades = 0
        l1_test_spearman = float("nan")
        l1_cell_signature = "n/a"
    else:
        rm = sel.get("test_realised_metrics", {})
        l1_val_sharpe = rm.get("sharpe", float("nan"))
        l1_val_ann_pnl = rm.get("annual_pnl", float("nan"))
        l1_val_n_trades = rm.get("n_trades", 0)
        l1_test_spearman = sel.get("test_formal_spearman", float("nan"))
        l1_cell_signature = _cell_signature(sel["cell"])

    lines.append("| Aspect | L-3 (PR #303) | L-2 (PR #306) | L-1 (this PR) |")
    lines.append("|---|---|---|---|")
    sel_q_pct = sel.get("selected_q_percent") if sel else "-"
    lines.append(
        f"| Val-selected cell signature | atr_normalised / Linear / q*=5% | "
        f"atr_normalised / Linear / q*=5% | {l1_cell_signature} / q*={sel_q_pct} |"
    )
    lines.append(
        f"| Val-selected test realised Sharpe | {l3_val_sharpe:.4f} | "
        f"{l2_val_sharpe:.4f} | {l1_val_sharpe:.4f} |"
    )
    lines.append(
        f"| Val-selected test ann_pnl (pip) | {l3_val_ann_pnl:+.1f} | "
        f"{l2_val_ann_pnl:+.1f} | {l1_val_ann_pnl:+.1f} |"
    )
    lines.append(
        f"| Val-selected test n_trades | {l3_val_n_trades} | "
        f"{l2_val_n_trades} | {l1_val_n_trades} |"
    )
    lines.append(
        f"| Test Spearman (formal H1 signal) | {l3_test_spearman:+.4f} | "
        f"{l2_test_spearman:+.4f} | {l1_test_spearman:+.4f} |"
    )
    lines.append("")
    lines.append("**Interpretation guide**:")
    lines.append(
        "- If L-1 val-selected Sharpe >> L-2/L-3 → L-1 ternary classification "
        "structure breaks the structural-gap pattern that continuous-regression "
        "labels could not."
    )
    lines.append(
        "- If L-1 val-selected Sharpe ≈ L-2/L-3 → continuous-vs-classification axis "
        "is NOT the binding constraint at the minimum feature set; supports the "
        "leading hypothesis from post-26.0b routing review §3 / §4 (minimum-feature-"
        "set is binding)."
    )
    lines.append(
        "- If L-1 test Spearman ≥ +0.05 → ranking signal exists; subsequent gating "
        "behaviour depends on realised PnL conversion at the selected quantile cutoff."
    )
    lines.append("")

    # Pair concentration (diagnostic-only)
    lines.append("## Pair concentration per cell (DIAGNOSTIC-ONLY; per 26.0c-α §9.2)")
    lines.append("")
    lines.append(
        f"CONCENTRATION_HIGH fires when val top-pair share >= {CONCENTRATION_HIGH_THRESHOLD}. "
        "NOT consulted by `select_cell_validation_only` or `assign_verdict`."
    )
    lines.append("")
    lines.append(
        "| cell | picker | q% | val_top_pair | val_top_share | "
        "val_concentration_high | test_top_pair | test_top_share |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        val_con = c.get("val_concentration", {})
        test_con = c.get("test_concentration", {})
        lines.append(
            f"| {cell['id']} | {cell['picker']} | {c.get('selected_q_percent', '-')} | "
            f"{val_con.get('top_pair', '-')} | "
            f"{val_con.get('top_pair_share', float('nan')):.4f} | "
            f"{val_con.get('concentration_high', False)} | "
            f"{test_con.get('top_pair', '-')} | "
            f"{test_con.get('top_pair_share', float('nan')):.4f} |"
        )
    lines.append("")

    # Classification-quality diagnostics (diagnostic-only)
    lines.append("## Classification-quality diagnostics (DIAGNOSTIC-ONLY; per 26.0c-α §9.3)")
    lines.append("")
    lines.append(
        "AUC of P(TP) one-vs-rest / Cohen's κ / multiclass logloss / confusion "
        "matrix / per-class accuracy on test. NOT formal H1; NOT used in formal "
        "verdict routing per §6.1 binding."
    )
    lines.append("")
    lines.append("| cell | picker | AUC(P(TP)) | Cohen κ | logloss | per-class acc (TP/SL/TIME) |")
    lines.append("|---|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        d = c.get("test_classification_diag", {})
        pca = d.get("per_class_accuracy", {})
        lines.append(
            f"| {cell['id']} | {cell['picker']} | "
            f"{d.get('auc_tp_ovr', float('nan')):.4f} | "
            f"{d.get('cohen_kappa', float('nan')):.4f} | "
            f"{d.get('multiclass_logloss', float('nan')):.4f} | "
            f"{pca.get(LABEL_TP, float('nan')):.3f} / "
            f"{pca.get(LABEL_SL, float('nan')):.3f} / "
            f"{pca.get(LABEL_TIME, float('nan')):.3f} |"
        )
    lines.append("")

    # Absolute thresholds (diagnostic-only)
    lines.append(
        "## Diagnostic absolute-probability thresholds (DIAGNOSTIC-ONLY; per 26.0c-α §9.4)"
    )
    lines.append("")
    lines.append(
        f"P(TP) candidates: {ABSOLUTE_THRESHOLDS_PTP}. "
        f"P(TP)-P(SL) candidates: {ABSOLUTE_THRESHOLDS_DIFF}. "
        "Reported per cell; NOT used in formal verdict routing."
    )
    lines.append("")
    lines.append("| cell | picker | abs_thr | val_sharpe | val_n | test_sharpe | test_n |")
    lines.append("|---|---|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        for r in c.get("absolute_all", []):
            lines.append(
                f"| {cell['id']} | {cell['picker']} | {r['threshold']:+.4f} | "
                f"{r['val'].get('sharpe', float('nan')):.4f} | "
                f"{r['val'].get('n_trades', 0)} | "
                f"{r['test'].get('sharpe', float('nan')):.4f} | "
                f"{r['test'].get('n_trades', 0)} |"
            )
    lines.append("")

    # Isotonic appendix (OMITTED per 26.0c-α §9.5)
    lines.append("## Isotonic-calibration appendix — OMITTED")
    lines.append("")
    lines.append(
        "Per 26.0c-α §4.3 / §9.5 binding: isotonic calibration is deferred. "
        "Fitting isotonic on val AND using the same val to select the quantile "
        "cutoff introduces selection-overfit risk. The 26.0c-β stub raises "
        "`NotImplementedError`. Deferred to a later sub-phase or diagnostic-only "
        "appendix."
    )
    lines.append("")

    # Multiple-testing caveat
    lines.append("## Multiple-testing caveat")
    lines.append("")
    lines.append(
        f"{n_cells_run} formal cells × {len(THRESHOLDS_QUANTILE_PERCENTS)} quantile "
        f"candidates = {n_cells_run * len(THRESHOLDS_QUANTILE_PERCENTS)} primary "
        "(cell, q) pairs evaluated. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE "
        "verdicts are hypothesis-generating ONLY; production-readiness requires "
        "an X-v2-equivalent frozen-OOS PR per Phase 22 contract."
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
        help="Dry-run: skip writing artifacts to disk.",
    )
    parser.add_argument(
        "--quick-mode",
        action="store_true",
        help="500-row × 20-pair subsample for smoke (no formal verdict).",
    )
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 26.0c-beta L-1 ternary classification eval ({len(args.pairs)} pairs) ===")
    print(
        f"K_FAV={K_FAV} K_ADV={K_ADV} H_M1={H_M1_BARS} | "
        f"H1-weak>{H1_WEAK_THRESHOLD} H1-meaningful>={H1_MEANINGFUL_THRESHOLD} | "
        f"H3 ref={H3_REFERENCE_SHARPE} | quantile candidates={THRESHOLDS_QUANTILE_PERCENTS}"
    )

    # 1. Load labels
    print("Loading 25.0a-beta path-quality labels...")
    raw_label_path = REPO_ROOT / "artifacts" / "stage25_0a" / "path_quality_dataset.parquet"
    raw_labels = pd.read_parquet(raw_label_path)
    if args.pairs != PAIRS_20:
        raw_labels = raw_labels[raw_labels["pair"].isin(args.pairs)]
    print(f"  labels rows: {len(raw_labels)}")

    # 2. Pre-flight
    print("Running pre-flight...")
    t0 = time.time()
    try:
        preflight_diag = verify_l3_preflight(raw_labels, args.pairs)
    except L3PreflightError as exc:
        print(f"PRE-FLIGHT FAILED: {exc}")
        return 2
    print(
        f"  Pre-flight passed: {preflight_diag['label_rows']} rows; "
        f"LightGBM={preflight_diag['lightgbm_available']} "
        f"({preflight_diag.get('lightgbm_version')}) "
        f"({time.time() - t0:.1f}s)"
    )

    if not preflight_diag["lightgbm_available"]:
        print("LightGBM is REQUIRED for L-1 multiclass eval; halting.")
        return 2

    # 3. Build M1 pair runtime
    print("Building M1 path runtime per pair...")
    pair_runtime_map: dict[str, dict] = {}
    for pair in args.pairs:
        t_pair = time.time()
        pair_runtime_map[pair] = _build_pair_runtime(pair, days=args.days)
        print(f"  {pair}: m1 rows {pair_runtime_map[pair]['n_m1']} ({time.time() - t_pair:5.1f}s)")

    # 4. Chronological split
    train_df, val_df, test_df, t70, t85 = split_70_15_15(raw_labels)
    t_min = raw_labels["signal_ts"].min()
    t_max = raw_labels["signal_ts"].max()
    print(f"  split: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")

    if args.quick_mode:
        n_per_pair = 500
        sub_idx_train = train_df.groupby("pair").head(n_per_pair).index
        sub_idx_val = val_df.groupby("pair").head(n_per_pair).index
        sub_idx_test = test_df.groupby("pair").head(n_per_pair).index
        train_df = train_df.loc[sub_idx_train].reset_index(drop=True)
        val_df = val_df.loc[sub_idx_val].reset_index(drop=True)
        test_df = test_df.loc[sub_idx_test].reset_index(drop=True)
        print(
            f"  QUICK-MODE: subsampled train={len(train_df)}, val={len(val_df)}, "
            f"test={len(test_df)} — formal verdict NOT valid in quick mode"
        )

    # 5. Sanity probe (HALTS on failure per §10)
    sanity = run_sanity_probe(train_df, val_df, test_df, pair_runtime_map, args.pairs)

    if args.sanity_probe_only:
        print("\n--sanity-probe-only set; exiting after probe.")
        if not args.no_write:
            (args.out_dir / "sanity_probe.json").write_text(
                json.dumps(sanity, indent=2, default=str), encoding="utf-8"
            )
            print(f"sanity probe results: {args.out_dir / 'sanity_probe.json'}")
        return 0

    # 6. PRECOMPUTE realised PnL per row for val + test (cell-independent; inherited harness)
    print("Precomputing realised PnL per row via inherited harness (val + test)...")
    t0 = time.time()
    pnl_val_full = precompute_realised_pnl_per_row(val_df, pair_runtime_map)
    print(
        f"  val: {len(pnl_val_full)} rows, "
        f"valid PnLs = {int(np.isfinite(pnl_val_full).sum())} "
        f"({time.time() - t0:.1f}s)"
    )
    t0 = time.time()
    pnl_test_full = precompute_realised_pnl_per_row(test_df, pair_runtime_map)
    print(
        f"  test: {len(pnl_test_full)} rows, "
        f"valid PnLs = {int(np.isfinite(pnl_test_full).sum())} "
        f"({time.time() - t0:.1f}s)"
    )

    # 7. Build labels
    print("Building L-1 ternary labels...")
    train_label = build_l1_labels_for_dataframe(train_df).to_numpy()
    val_label = build_l1_labels_for_dataframe(val_df).to_numpy()
    test_label = build_l1_labels_for_dataframe(test_df).to_numpy()

    # 8. Fit ONCE multiclass LightGBM; predict on val and test
    print("Fitting multiclass LightGBM (single fit for both cells)...")
    t0 = time.time()
    pipeline = build_pipeline_lightgbm_multiclass()
    x_train = train_df[CATEGORICAL_COLS]
    x_val = val_df[CATEGORICAL_COLS]
    x_test = test_df[CATEGORICAL_COLS]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipeline.fit(x_train, train_label)
    val_probs = pipeline.predict_proba(x_val)
    test_probs = pipeline.predict_proba(x_test)
    print(f"  multiclass LGBM fit + predict_proba: ({time.time() - t0:.1f}s)")
    print(f"  val_probs shape={val_probs.shape}; test_probs shape={test_probs.shape}")

    # 9. Per-cell evaluation
    cells = build_cells()
    n_cells_run = len(cells)
    cell_results: list[dict] = []
    for i, cell in enumerate(cells):
        t_cell = time.time()
        try:
            result = evaluate_cell(
                cell,
                train_df,
                val_df,
                test_df,
                train_label,
                val_label,
                test_label,
                None,  # train_probs not used downstream
                val_probs,
                test_probs,
                pnl_val_full,
                pnl_test_full,
            )
        except Exception as exc:
            print(f"  cell {i + 1}/{n_cells_run} FAILED: {exc!r}")
            result = {
                "cell": cell,
                "n_train": 0,
                "n_val": 0,
                "n_test": 0,
                "verdict": "REJECT_NON_DISCRIMINATIVE",
                "h_state": f"ERROR: {type(exc).__name__}",
                "low_power": True,
            }
        cell_results.append(result)
        rm = result.get("test_realised_metrics", {})
        sp = result.get("test_formal_spearman", float("nan"))
        print(
            f"  cell {i + 1}/{n_cells_run} {cell['id']} {cell['picker']:14} | "
            f"q={result.get('selected_q_percent', '-')} "
            f"val_sharpe={result.get('val_realised_sharpe', float('nan')):+.3f} "
            f"val_n={result.get('val_n_trades', 0):>6} | "
            f"test_sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"test_n={rm.get('n_trades', 0):>6} "
            f"test_sp={sp:+.4f} | "
            f"({time.time() - t_cell:5.1f}s)"
        )

    # 10. Validation-only cell selection
    val_select = select_cell_validation_only(cell_results)
    verdict_info = assign_verdict(val_select.get("selected"))
    aggregate_info = aggregate_cross_cell_verdict(cell_results)

    print("")
    print("=== Val-selected (cell*, q*) (FORMAL verdict source; test touched once) ===")
    sel = val_select.get("selected")
    if sel is None:
        print("  no valid cell")
    else:
        print(f"  cell: {_cell_signature(sel['cell'])}")
        print(
            f"  q* = {sel.get('selected_q_percent')}%, cutoff = {sel.get('selected_cutoff'):+.6f}"
        )
        print(
            f"  val Sharpe = {sel.get('val_realised_sharpe', float('nan')):.4f} "
            f"(n_trades = {sel.get('val_n_trades')})"
        )
        rm = sel.get("test_realised_metrics", {})
        sp = sel.get("test_formal_spearman", float("nan"))
        print(
            f"  test Sharpe = {rm.get('sharpe', float('nan')):.4f}; "
            f"test ann_pnl = {rm.get('annual_pnl', 0.0):+.1f}; "
            f"test n_trades = {rm.get('n_trades', 0)}; "
            f"test FORMAL Spearman(score, realised_pnl) = {sp:.4f}"
        )
    print("")
    print(f"=== Verdict: {verdict_info['verdict']} ({verdict_info['h_state']}) ===")
    print(
        f"=== Cross-cell aggregate: {aggregate_info['aggregate_verdict']} "
        f"(branches={aggregate_info['branches']}) ==="
    )

    if args.no_write:
        print("\n--no-write set; skipping artifact write.")
        return 0

    # 11. Write report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report(
        report_path,
        cell_results,
        val_select,
        verdict_info,
        aggregate_info,
        sanity,
        (t_min, t70, t85, t_max),
        preflight_diag,
        n_cells_run,
    )
    print(f"\nReport: {report_path}")

    # 12. Persist artifacts (gitignored)
    summary_rows: list[dict] = []
    for c in cell_results:
        cell = c["cell"]
        rm = c.get("test_realised_metrics", {})
        sp = c.get("test_formal_spearman", float("nan"))
        ab = c.get("absolute_best", {})
        cd = c.get("test_classification_diag", {})
        summary_rows.append(
            {
                "cell_id": cell["id"],
                "picker": cell["picker"],
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
                "test_a4": rm.get("a4_n_positive", 0),
                "test_a5_stress": rm.get("a5_stressed_annual_pnl", float("nan")),
                "test_formal_spearman": sp,
                "test_auc_tp": cd.get("auc_tp_ovr", float("nan")),
                "test_kappa": cd.get("cohen_kappa", float("nan")),
                "test_logloss": cd.get("multiclass_logloss", float("nan")),
                "abs_best_threshold": ab.get("threshold", float("nan")),
                "abs_best_val_sharpe": ab.get("val", {}).get("sharpe", float("nan")),
                "abs_best_test_sharpe": ab.get("test", {}).get("sharpe", float("nan")),
                "h_state": c.get("h_state"),
                "low_power": c.get("low_power", False),
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
    aggregate["n_cells_run"] = n_cells_run
    if val_select.get("selected") is not None:
        sel_lite = {
            "cell": dict(val_select["selected"]["cell"]),
            "selected_q_percent": val_select["selected"]["selected_q_percent"],
            "selected_cutoff": val_select["selected"]["selected_cutoff"],
            "val_realised_sharpe": val_select["selected"]["val_realised_sharpe"],
            "val_realised_annual_pnl": val_select["selected"]["val_realised_annual_pnl"],
            "val_n_trades": val_select["selected"]["val_n_trades"],
            "test_realised_metrics": val_select["selected"].get("test_realised_metrics", {}),
            "test_gates": val_select["selected"].get("test_gates", {}),
            "test_formal_spearman": val_select["selected"].get(
                "test_formal_spearman", float("nan")
            ),
        }
        aggregate["val_selected"] = sel_lite
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
