"""Stage 27.0d-β S-E Regression-on-Realised-PnL eval (third Phase 27 sub-phase).

Implements the binding contract from PR #324 (Phase 27.0d-α design memo)
under PR #323 (Phase 27 S-E scope amendment), Phase 27 kickoff (PR #316),
and inherited Phase 26 framework (PR #311 / PR #313).

Selected via post-27.0c routing review #322 R-S-E: classification-head-
derived score modifications produced wrong-direction Sharpe in both
27.0b (S-C TIME penalty) and 27.0c (S-D calibrated EV); next test
leaves the classification head and targets realised PnL directly.

R7-A feature family FIXED:
  pair + direction + atr_at_signal_pip + spread_at_signal_pip

S-E score-objective (per 27.0d-α §3.1):
  target(row) = _compute_realised_barrier_pnl(row)   # D-1 binding
  S-E(row)    = regressor.predict(row)               # predicted realised PnL

Score sign: higher predicted PnL = better. Quantile-of-val picks top-(q/100)
val rows by S-E score.

LightGBMRegressor config (per 27.0d-α §4 / D-W1):
  - Inherits multiclass-head shape (LIGHTGBM_FIXED_CONFIG) minus
    multiclass-specific keys (objective, num_class, class_weight).
  - objective='huber', alpha=0.9, metric='huber' (per D-W2).
  - Categorical handling: same OneHotEncoder for pair / direction.

Target preprocessing (per D-W3): NONE. Raw realised PnL from inherited
bid/ask harness used directly. Winsorisation / clipping NOT admitted
under D-1 binding.

OOF protocol (per D-W4): 5-fold OOF on train, seed=42, DIAGNOSTIC-ONLY.
Single train-fit regressor is used for formal val/test scoring; OOF
predictions feed only the predicted-vs-realised correlation / MAE / R²
diagnostics in the sanity probe + eval report.

Cells (per 27.0d-α §7.1; D-W5):
  - C-se: S-E substantive regression cell
  - C-sb-baseline: S-B = raw P(TP)-P(SL) on a SEPARATELY-FIT multiclass
    head — inheritance-chain sanity check reproducing 27.0b C-alpha0 /
    R6-new-A C02 baseline (n_trades=34,626 / Sharpe=-0.1732 /
    ann_pnl=-204,664.4 within inherited tolerances).

D10 amendment for 27.0d (per 27.0d-α §7.5): single model fit = ONE
regressor + ONE multiclass head; each fit ONCE on full train; no
per-cell re-fit.

C-sb-baseline mismatch HALTs the eval with BaselineMismatchError
FAIL-FAST before C-se verdict assignment (per D-I9 / D-W7 / D-J9).

2-LAYER SELECTION-OVERFIT GUARD (per 27.0d-α §13 verbatim binding):
  S-E's two trainable artifacts (LightGBMRegressor for C-se; LightGBM
  multiclass head for C-sb-baseline) are BOTH fit on train-only data.
  Val data is used ONLY for cutoff selection (quantile-of-val q* per
  cell). Test data is touched exactly once at the val-selected
  (cell*, q*). 5-fold OOF (if computed) is DIAGNOSTIC-ONLY and does
  NOT enter formal verdict routing. Any deviation is a NG#10 violation.

D-1 BINDING (inherited): formal realised-PnL uses
_compute_realised_barrier_pnl (bid/ask executable). Mid-to-mid PnL
appears in sanity probe only. The regression target uses the SAME
bid/ask harness.

MANDATORY CLAUSES (clauses 1-5 verbatim; clause 6 = PR #323 §7
verbatim — the canonical S-E-updated wording from PR #323 forward):

1. Phase framing. ADOPT requires both H2 PASS and the full 8-gate A0-A5
   harness.
2. Diagnostic columns prohibition. Calibration / threshold-sweep /
   directional-comparison / classification-quality / feature-importance /
   per-pair-Sharpe-contribution columns are diagnostic-only. ADOPT_CANDIDATE
   routing must not depend on any single one of them. 27.0c extension
   preserved: conditional-PnL estimator constants and calibration
   reliability diagrams are diagnostic-only. 27.0d extends: regressor
   feature importance, predicted-vs-realised correlation, R², MAE, and
   predicted-PnL distribution are diagnostic-only.
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
   admissible at kickoff for formal evaluation. S-D (calibrated EV) was
   promoted from admissible-but-deferred to formal at sub-phase 27.0c-β
   via PR #320. S-E (regression-on-realised-PnL) was promoted from
   "requires scope amendment" to "admissible at 27.0d-α design memo"
   via Phase 27 S-E scope-amendment PR #323. S-E uses realised barrier
   PnL (inherited bid/ask executable, D-1 binding) as the per-row
   regression target under the FIXED R7-A feature family; LightGBM
   regression is the default model class but the 27.0d-α design memo
   may specify alternatives within the regression family. S-Other
   (quantile regression / ordinal / learn-to-rank) remains NOT
   admissible. R7-D and R7-Other remain NOT admissible. R7-B / R7-C
   remain admissible only after their own separate scope amendments.
   Phase 26 deferred-not-foreclosed items (L-4 / R6-new-B / R6-new-C /
   Phase 25 F4 / F6 / F5-d / F5-e) are NOT subsumed by Phase 27; they
   remain under their original phase semantics.

PRODUCTION-MISUSE GUARDS (inherited verbatim from 26.0a-α §5.1):
GUARD 1 — research-not-production: 27.0d features stay in scripts/.
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

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage27_0d"
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
evaluate_quantile_family = stage26_0c.evaluate_quantile_family
compute_8_gate_from_pnls = stage26_0c.compute_8_gate_from_pnls
compute_classification_diagnostics = stage26_0c.compute_classification_diagnostics
compute_mid_to_mid_pnl_diagnostic = stage26_0c.compute_mid_to_mid_pnl_diagnostic
assign_verdict = stage26_0c.assign_verdict
aggregate_cross_cell_verdict = stage26_0c.aggregate_cross_cell_verdict
select_cell_validation_only = stage26_0c.select_cell_validation_only
SanityProbeError = stage26_0c.SanityProbeError

build_pipeline_lightgbm_multiclass_widened = stage26_0d.build_pipeline_lightgbm_multiclass_widened
drop_rows_with_missing_new_features = stage26_0d.drop_rows_with_missing_new_features
compute_feature_importance_diagnostic = stage26_0d.compute_feature_importance_diagnostic

compute_per_pair_sharpe_contribution = stage27_0b.compute_per_pair_sharpe_contribution
make_oof_fold_assignment = stage27_0c.make_oof_fold_assignment
compute_picker_score_s_b_raw = stage27_0c.compute_picker_score_s_b_raw


# ---------------------------------------------------------------------------
# Binding constants (per 27.0d-α)
# ---------------------------------------------------------------------------

# Barrier geometry (inherited)
K_FAV = stage25_0b.K_FAV
K_ADV = stage25_0b.K_ADV
H_M1_BARS = stage25_0b.H_M1_BARS

# L-1 class encoding (inherited; preserved for sanity probe / C-sb-baseline only;
# NOT used as S-E regression target per D-W3)
LABEL_TP = stage26_0c.LABEL_TP
LABEL_SL = stage26_0c.LABEL_SL
LABEL_TIME = stage26_0c.LABEL_TIME
NUM_CLASSES = stage26_0c.NUM_CLASSES

# Threshold family (inherited)
THRESHOLDS_QUANTILE_PERCENTS = stage26_0c.THRESHOLDS_QUANTILE_PERCENTS

# Multiclass head config (inherited; FIXED for C-sb-baseline)
LIGHTGBM_MULTICLASS_CONFIG = dict(stage26_0d.LIGHTGBM_FIXED_CONFIG)

# R7-A feature family (FIXED)
NUMERIC_FEATURES = stage26_0d.NUMERIC_FEATURES
ALL_FEATURES = stage26_0d.ALL_FEATURES
CATEGORICAL_COLS = stage26_0d.CATEGORICAL_COLS

# H1/H2/H3/H4 thresholds (inherited; FIXED)
H1_WEAK_THRESHOLD = stage26_0c.H1_WEAK_THRESHOLD
H1_MEANINGFUL_THRESHOLD = stage26_0c.H1_MEANINGFUL_THRESHOLD
H3_REFERENCE_SHARPE = stage26_0c.H3_REFERENCE_SHARPE

# Diagnostic constants
CONCENTRATION_HIGH_THRESHOLD = stage26_0c.CONCENTRATION_HIGH_THRESHOLD

# Sanity probe thresholds (inherited)
SANITY_MIN_CLASS_SHARE = stage26_0c.SANITY_MIN_CLASS_SHARE
SANITY_MAX_PER_PAIR_TIME_SHARE = stage26_0c.SANITY_MAX_PER_PAIR_TIME_SHARE
SANITY_MAX_NEW_FEATURE_NAN_RATE = stage26_0d.SANITY_MAX_NEW_FEATURE_NAN_RATE
SANITY_MAX_POSITIVITY_VIOLATION_RATE = stage26_0d.SANITY_MAX_POSITIVITY_VIOLATION_RATE

# Span budgets
TEST_SPAN_YEARS = SPAN_YEARS * (1.0 - TRAIN_FRAC - VAL_FRAC)
VAL_SPAN_YEARS = SPAN_YEARS * VAL_FRAC


# ---------------------------------------------------------------------------
# NEW Phase 27.0d constants
# ---------------------------------------------------------------------------

# Huber regression config (per 27.0d-α §4 / §5.1; D-W1 + D-W2)
HUBER_ALPHA = 0.9

# Build the regression hyperparameter dict by stripping multiclass-specific
# keys (objective / num_class / class_weight) and adding Huber-specific keys.
# Per D-J2: inherited values verbatim; if inappropriate, HALT and route to
# 27.0d-α-rev1 (no per-script overrides).
_REGRESSION_DROP_KEYS = ("objective", "num_class", "class_weight")
LIGHTGBM_REGRESSION_CONFIG = {
    k: v for k, v in LIGHTGBM_MULTICLASS_CONFIG.items() if k not in _REGRESSION_DROP_KEYS
}
LIGHTGBM_REGRESSION_CONFIG.update(
    objective="huber",
    alpha=HUBER_ALPHA,
    metric="huber",
)

# OOF protocol (DIAGNOSTIC-ONLY; reused from 27.0c per D-J5)
OOF_N_FOLDS = stage27_0c.OOF_N_FOLDS
OOF_SEED = stage27_0c.OOF_SEED

# Baseline reference values for C-sb-baseline (per D-J10; identical to 27.0c)
BASELINE_27_0B_C_ALPHA0_N_TRADES = 34626
BASELINE_27_0B_C_ALPHA0_SHARPE = -0.1732
BASELINE_27_0B_C_ALPHA0_ANN_PNL = -204664.4

# Tolerances (inherited verbatim from 27.0b §12.2 / 27.0c §7.3)
BASELINE_MATCH_N_TRADES_TOLERANCE = 0
BASELINE_MATCH_SHARPE_ABS_TOLERANCE = 1e-4
BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE = 0.5

# NaN-PnL train-row HALT threshold (per D-J12)
NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD = 0.001  # 0.1% of n_train

# OOF correlation pathology threshold (per D-J6; WARN-only)
OOF_CORRELATION_PATHOLOGY_THRESHOLD = 0.0  # < 0 on majority folds → warn


# ---------------------------------------------------------------------------
# NEW exception (per 27.0d-α §7.3 / D-J9)
# ---------------------------------------------------------------------------


class BaselineMismatchError(RuntimeError):
    """Raised when C-sb-baseline fails to reproduce 27.0b C-alpha0 baseline.

    Per 27.0d-α §7.3 / D-J9. C-sb-baseline uses raw `P(TP) - P(SL)` on a
    SEPARATELY-FIT multiclass head trained on the same train data with
    `random_state=42`. With R7-A held fixed, L-1 label fixed, model class
    fixed, dataset / split / harness inherited unchanged, val-selected
    C-sb-baseline metrics MUST coincide with 27.0b C-alpha0 / R6-new-A C02
    exactly (n_trades; ≤ 1e-4 on Sharpe; ≤ 0.5 pip on ann_pnl). If they
    don't, something in the inheritance chain has drifted and S-E verdict
    assignment is unsafe.
    """


# ---------------------------------------------------------------------------
# LightGBMRegressor pipeline (per 27.0d-α §4; D-J1)
# ---------------------------------------------------------------------------


def build_pipeline_lightgbm_regression_widened() -> Pipeline:
    """LightGBM regression pipeline with R7-A 4-feature allowlist.

    Per 27.0d-α §4 / D-W1 / D-J1:
      - Mirrors `build_pipeline_lightgbm_multiclass_widened` structure
        exactly (ColumnTransformer with OneHotEncoder + numeric passthrough;
        no standardisation; no imputation)
      - LGBMClassifier → LGBMRegressor; num_class dropped; class_weight dropped
      - objective='huber' (D-W2), alpha=0.9, metric='huber'
      - Other hyperparameters inherited from LIGHTGBM_MULTICLASS_CONFIG verbatim
    """
    import lightgbm as lgb

    pre = ColumnTransformer(
        [
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_COLS,
            ),
            ("num", "passthrough", list(NUMERIC_FEATURES)),
        ]
    )
    return Pipeline(
        [
            ("pre", pre),
            # NOTE: step name kept as "clf" (rather than "reg") for compatibility
            # with the inherited compute_feature_importance_diagnostic helper from
            # stage26_0d, which hard-codes pipeline.named_steps["clf"]. Cosmetic
            # misnomer; the step is in fact an LGBMRegressor (per LIGHTGBM_REGRESSION_CONFIG).
            (
                "clf",
                lgb.LGBMRegressor(**LIGHTGBM_REGRESSION_CONFIG, verbose=-1),
            ),
        ]
    )


# ---------------------------------------------------------------------------
# OOF protocol (DIAGNOSTIC-ONLY; per 27.0d-α §6.2 / D-J5)
# ---------------------------------------------------------------------------


def fit_oof_regression_diagnostic(
    x_train: pd.DataFrame,
    y_train: np.ndarray,
    fold_idx: np.ndarray,
    n_folds: int = OOF_N_FOLDS,
) -> np.ndarray:
    """Fit fold-wise regressors on train; return OOF predictions per train row.

    DIAGNOSTIC-ONLY (per D-W4 / D-J5): the production scoring path uses a
    single train-fit regressor, NOT the OOF predictions. OOF outputs feed
    only the predicted-vs-realised correlation / MAE / R² diagnostics.

    Returns:
        oof_preds: np.ndarray of shape (n_train,) dtype float64
    """
    n_train = len(y_train)
    if len(x_train) != n_train:
        raise ValueError(f"x_train rows {len(x_train)} != y_train {n_train}")
    if len(fold_idx) != n_train:
        raise ValueError(f"fold_idx rows {len(fold_idx)} != y_train {n_train}")

    oof_preds = np.full(n_train, np.nan, dtype=np.float64)
    x_train_reset = x_train.reset_index(drop=True)

    for f in range(n_folds):
        in_fold = fold_idx == f
        not_in_fold = ~in_fold
        n_in = int(in_fold.sum())
        if n_in == 0:
            continue
        t0 = time.time()
        x_tr = x_train_reset.loc[not_in_fold].reset_index(drop=True)
        y_tr = y_train[not_in_fold]
        x_pred = x_train_reset.loc[in_fold].reset_index(drop=True)
        pipeline_f = build_pipeline_lightgbm_regression_widened()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pipeline_f.fit(x_tr, y_tr)
        oof_preds[in_fold] = pipeline_f.predict(x_pred)
        print(
            f"    OOF reg fold {f + 1}/{n_folds}: train_n={int(not_in_fold.sum())} "
            f"oof_n={n_in} ({time.time() - t0:.1f}s)"
        )

    if not np.all(np.isfinite(oof_preds)):
        nan_rows = int((~np.isfinite(oof_preds)).sum())
        raise RuntimeError(f"OOF regression produced NaN predictions for {nan_rows} train rows")

    return oof_preds


def compute_oof_correlation_diagnostic(
    oof_preds: np.ndarray, y_train: np.ndarray, fold_idx: np.ndarray
) -> dict:
    """Per-fold Pearson + Spearman; aggregate Pearson + Spearman.

    DIAGNOSTIC-ONLY per clause 2 27.0d extension; not in formal verdict.
    """
    n_folds = int(fold_idx.max()) + 1
    per_fold: list[dict] = []
    for f in range(n_folds):
        mask = fold_idx == f
        p = oof_preds[mask]
        y = y_train[mask]
        finite = np.isfinite(p) & np.isfinite(y)
        n_f = int(finite.sum())
        if n_f < 10:
            per_fold.append(
                {"fold": f, "n": n_f, "pearson": float("nan"), "spearman": float("nan")}
            )
            continue
        pearson_r, _ = pearsonr(p[finite], y[finite])
        spearman_r, _ = spearmanr(p[finite], y[finite])
        per_fold.append(
            {"fold": f, "n": n_f, "pearson": float(pearson_r), "spearman": float(spearman_r)}
        )
    finite = np.isfinite(oof_preds) & np.isfinite(y_train)
    if int(finite.sum()) >= 10:
        agg_p, _ = pearsonr(oof_preds[finite], y_train[finite])
        agg_s, _ = spearmanr(oof_preds[finite], y_train[finite])
    else:
        agg_p, agg_s = float("nan"), float("nan")
    pos_folds = sum(1 for r in per_fold if np.isfinite(r["pearson"]) and r["pearson"] > 0.0)
    return {
        "per_fold": per_fold,
        "aggregate_pearson": float(agg_p) if np.isfinite(agg_p) else float("nan"),
        "aggregate_spearman": float(agg_s) if np.isfinite(agg_s) else float("nan"),
        "n_folds_pearson_positive": pos_folds,
        "n_folds": n_folds,
    }


def compute_regression_diagnostic(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """MAE + R² + Pearson + Spearman on a single split.

    DIAGNOSTIC-ONLY per clause 2 27.0d extension.
    """
    finite = np.isfinite(y_true) & np.isfinite(y_pred)
    n = int(finite.sum())
    if n < 10:
        return {
            "n": n,
            "mae": float("nan"),
            "r2": float("nan"),
            "pearson": float("nan"),
            "spearman": float("nan"),
        }
    yt = y_true[finite]
    yp = y_pred[finite]
    pearson_r, _ = pearsonr(yp, yt)
    spearman_r, _ = spearmanr(yp, yt)
    return {
        "n": n,
        "mae": float(mean_absolute_error(yt, yp)),
        "r2": float(r2_score(yt, yp)),
        "pearson": float(pearson_r) if np.isfinite(pearson_r) else float("nan"),
        "spearman": float(spearman_r) if np.isfinite(spearman_r) else float("nan"),
    }


# ---------------------------------------------------------------------------
# S-E score formula (per 27.0d-α §3.1; D-J3)
# ---------------------------------------------------------------------------


def compute_picker_score_s_e(regressor: Pipeline, x: pd.DataFrame) -> np.ndarray:
    """S-E(row) = regressor.predict(row).

    Per 27.0d-α §3.1 / D-J3: numpy passthrough; no per-row loop; no reshape /
    clip / sign flip. Higher predicted PnL = better.
    """
    pred = regressor.predict(x)
    return np.asarray(pred, dtype=np.float64)


# ---------------------------------------------------------------------------
# Formal cells (per 27.0d-α §7.1; D-J7)
# ---------------------------------------------------------------------------


def build_s_e_cells() -> list[dict]:
    """27.0d formal grid: 2 cells per design memo §7.1.

    - C-se: S-E substantive regression cell
    - C-sb-baseline: S-B raw P(TP) - P(SL) on separately-fit multiclass head
    """
    return [
        {"id": "C-se", "picker": "S-E(regressor_pred)", "score_type": "s_e"},
        {"id": "C-sb-baseline", "picker": "S-B(raw_p_tp_minus_p_sl)", "score_type": "s_b_raw"},
    ]


# ---------------------------------------------------------------------------
# C-sb-baseline mismatch check (per 27.0d-α §7.3 / D-J9)
# ---------------------------------------------------------------------------


def check_c_sb_baseline_match(c_sb_baseline_result: dict) -> dict:
    """Validate C-sb-baseline reproduces 27.0b C-alpha0 baseline.

    Per 27.0d-α §7.3 + D-J9 (fail-fast). HALTs with BaselineMismatchError
    on mismatch BEFORE C-se verdict assignment.
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
            "27.0d-α §7.3; failures: " + "; ".join(failures)
        )
    return report


# ---------------------------------------------------------------------------
# Sanity probe (extends 27.0c probe with S-E-specific items per §10)
# ---------------------------------------------------------------------------


def run_sanity_probe_27_0d(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    pairs: list[str],
    pnl_train_full: np.ndarray | None = None,
    val_pred: np.ndarray | None = None,
    test_pred: np.ndarray | None = None,
    train_pred: np.ndarray | None = None,
    oof_preds: np.ndarray | None = None,
    fold_idx: np.ndarray | None = None,
    oof_corr_diag: dict | None = None,
    train_reg_diag: dict | None = None,
    val_reg_diag: dict | None = None,
    test_reg_diag: dict | None = None,
    regressor_feature_importance: dict | None = None,
    train_drop_for_nan_pnl_count: int | None = None,
) -> dict:
    """27.0d sanity probe per design memo §10.

    Inherited HALT checks (1-6 from 27.0c §10):
      1. Class priors per split — HALT if class < 1%
      2. Per-pair TIME share — HALT if pair > 99% TIME
      3. Realised-PnL cache basis (D-1 binding) confirmed
      4. Mid-to-mid PnL distribution per class (diagnostic-only)
      5. R7-A new-feature NaN rate per split — HALT > 5%
      6. R7-A positivity assertions — HALT > 1% violation

    NEW 27.0d items per design memo §10 (DIAGNOSTIC-ONLY per D-J11):
      7. Target (realised PnL) distribution on train
      8. Predicted PnL distribution on val/test
      9. OOF predicted-vs-realised correlation
      10. Regressor MAE + R² on train / val / test
      11. Regressor feature importance (4-bucket)

    Plus D-J12 HALT: NaN-PnL train rows > 0.1% of n_train.
    """
    print("\n=== 27.0d SANITY PROBE (per 27.0d-α §10) ===")
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

    # 7. NEW 27.0d: Target (realised PnL) distribution on train
    print("  target (realised PnL) distribution on TRAIN (NEW; DIAGNOSTIC-ONLY):")
    if pnl_train_full is not None:
        finite = pnl_train_full[np.isfinite(pnl_train_full)]
        if len(finite) > 0:
            stats = {
                "n_finite": int(len(finite)),
                "mean": float(finite.mean()),
                "std": float(finite.std()),
                "p5": float(np.quantile(finite, 0.05)),
                "p25": float(np.quantile(finite, 0.25)),
                "p50": float(np.quantile(finite, 0.50)),
                "p75": float(np.quantile(finite, 0.75)),
                "p95": float(np.quantile(finite, 0.95)),
                "min": float(finite.min()),
                "max": float(finite.max()),
            }
            out["target_pnl_distribution_train"] = stats
            print(
                f"    n={stats['n_finite']} mean={stats['mean']:+.4f} std={stats['std']:.4f} "
                f"p5={stats['p5']:+.4f} p50={stats['p50']:+.4f} p95={stats['p95']:+.4f}"
            )
        else:
            out["target_pnl_distribution_train"] = {"n_finite": 0}
    else:
        out["target_pnl_distribution_train"] = {
            "status": "deferred (PnL not yet computed at probe-only stage)"
        }
        print("    deferred (PnL not computed at probe-only stage)")

    # 8. NEW 27.0d: Predicted PnL distribution
    print("  predicted PnL distribution (NEW; DIAGNOSTIC-ONLY):")
    if train_pred is not None and val_pred is not None and test_pred is not None:
        pred_dist = {}
        for split_name, pred in [("train", train_pred), ("val", val_pred), ("test", test_pred)]:
            finite = pred[np.isfinite(pred)]
            if len(finite) == 0:
                pred_dist[split_name] = {"n_finite": 0}
                continue
            stats = {
                "n_finite": int(len(finite)),
                "mean": float(finite.mean()),
                "p5": float(np.quantile(finite, 0.05)),
                "p25": float(np.quantile(finite, 0.25)),
                "p50": float(np.quantile(finite, 0.50)),
                "p75": float(np.quantile(finite, 0.75)),
                "p95": float(np.quantile(finite, 0.95)),
            }
            pred_dist[split_name] = stats
            print(
                f"    {split_name}: n={stats['n_finite']} mean={stats['mean']:+.4f} "
                f"p5={stats['p5']:+.4f} p50={stats['p50']:+.4f} p95={stats['p95']:+.4f}"
            )
        out["predicted_pnl_distribution"] = pred_dist
    else:
        out["predicted_pnl_distribution"] = {
            "status": "deferred (regressor not yet fit at probe-only stage)"
        }
        print("    deferred (regressor not fit at probe-only stage)")

    # 9. NEW 27.0d: OOF predicted-vs-realised correlation
    print("  OOF predicted-vs-realised correlation (NEW; DIAGNOSTIC-ONLY):")
    if oof_corr_diag is not None:
        out["oof_correlation_diagnostic"] = oof_corr_diag
        print(
            f"    aggregate: pearson={oof_corr_diag.get('aggregate_pearson', float('nan')):+.4f} "
            f"spearman={oof_corr_diag.get('aggregate_spearman', float('nan')):+.4f} "
            f"(positive folds: {oof_corr_diag.get('n_folds_pearson_positive', 0)}/"
            f"{oof_corr_diag.get('n_folds', 0)})"
        )
        # WARN-only per D-J6: if majority folds have non-positive correlation, warn
        n_folds = int(oof_corr_diag.get("n_folds", 0))
        n_pos = int(oof_corr_diag.get("n_folds_pearson_positive", 0))
        if n_folds > 0 and n_pos < (n_folds / 2.0):
            warnings.warn(
                f"OOF Pearson positive on only {n_pos}/{n_folds} folds; "
                "fitting-pathology flag (WARN-only per D-J6)",
                UserWarning,
                stacklevel=2,
            )
            out["oof_correlation_pathology_warn"] = True
        else:
            out["oof_correlation_pathology_warn"] = False
    else:
        out["oof_correlation_diagnostic"] = {
            "status": "deferred (OOF not computed at probe-only stage)"
        }
        print("    deferred (OOF not computed at probe-only stage)")

    # 10. NEW 27.0d: Regressor MAE + R² per split
    print("  regressor MAE + R² per split (NEW; DIAGNOSTIC-ONLY):")
    if train_reg_diag is not None and val_reg_diag is not None and test_reg_diag is not None:
        out["regression_diagnostic"] = {
            "train": train_reg_diag,
            "val": val_reg_diag,
            "test": test_reg_diag,
        }
        for split_name, d in [
            ("train", train_reg_diag),
            ("val", val_reg_diag),
            ("test", test_reg_diag),
        ]:
            print(
                f"    {split_name}: n={d['n']} MAE={d['mae']:.4f} R²={d['r2']:+.4f} "
                f"pearson={d['pearson']:+.4f} spearman={d['spearman']:+.4f}"
            )
    else:
        out["regression_diagnostic"] = {
            "status": "deferred (regressor not fit / predicted at probe-only stage)"
        }
        print("    deferred (regressor not fit at probe-only stage)")

    # 11. NEW 27.0d: Regressor feature importance (4-bucket gain)
    print("  regressor feature importance (NEW; DIAGNOSTIC-ONLY):")
    if regressor_feature_importance is not None:
        out["regressor_feature_importance"] = regressor_feature_importance
        b = regressor_feature_importance.get("buckets", {})
        print(
            f"    pair={b.get('pair', 0):.1f} direction={b.get('direction', 0):.1f} "
            f"atr={b.get('atr_at_signal_pip', 0):.1f} spread={b.get('spread_at_signal_pip', 0):.1f}"
        )
    else:
        out["regressor_feature_importance"] = {
            "status": "deferred (regressor not fit at probe-only stage)"
        }
        print("    deferred (regressor not fit at probe-only stage)")

    # Train drop-for-NaN-PnL diagnostic (D-J12 HALT trigger)
    if train_drop_for_nan_pnl_count is not None:
        out["train_drop_for_nan_pnl_count"] = int(train_drop_for_nan_pnl_count)

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

    # NEW 27.0d HALT (per D-J12): NaN-PnL train rows > 0.1% of n_train
    if train_drop_for_nan_pnl_count is not None and pnl_train_full is not None:
        n_train_for_threshold = len(pnl_train_full)
        threshold = NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD * n_train_for_threshold
        if train_drop_for_nan_pnl_count > threshold:
            raise SanityProbeError(
                f"train rows with NaN PnL = {train_drop_for_nan_pnl_count} > "
                f"{NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD:.1%} of n_train "
                f"({int(threshold)}); regressor fit unsafe per D-J12"
            )

    print("=== SANITY PROBE: PASS ===\n")
    out["status"] = "PASS"
    return out


# ---------------------------------------------------------------------------
# Per-cell evaluation (per 27.0d-α §7; D10 amended 2-artifact form)
# ---------------------------------------------------------------------------


def evaluate_cell_27_0d(
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
    """27.0d cell evaluation.

    Both cells share the SAME production regressor and the SAME production
    multiclass head (D10 amendment per 27.0d-α §7.5). Picker score is
    precomputed and passed in. For classification-quality diagnostics
    (on C-sb-baseline only), the raw multiclass probs are used. C-se's
    classification diagnostic is reported with the same probs but the
    score is regressor.predict (not from probs).
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
# Report writer (21 sections per 27.0d-α §11)
# ---------------------------------------------------------------------------


def _cell_signature(cell: dict) -> str:
    return f"id={cell['id']} picker={cell['picker']} score_type={cell.get('score_type', '-')}"


def write_eval_report_27_0d(
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
    regressor_feature_importance: dict,
    train_reg_diag: dict,
    val_reg_diag: dict,
    test_reg_diag: dict,
    oof_corr_diag: dict,
    target_pnl_distribution: dict,
    predicted_pnl_distribution: dict,
) -> None:
    t_min, t70, t85, t_max = split_dates
    lines: list[str] = []
    lines.append("# Stage 27.0d-β — S-E Regression-on-Realised-PnL Eval Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append(
        "Design contract: "
        "`docs/design/phase27_0d_alpha_s_e_regression_on_realised_pnl_design_memo.md` "
        "(PR #324) under Phase 27 S-E scope amendment (PR #323), Phase 27 kickoff (PR #316), "
        "post-27.0c routing review (PR #322), and inherited Phase 26 framework "
        "(PR #311 / PR #313)."
    )
    lines.append("")
    # §1
    lines.append("## 1. Mandatory clauses (clauses 1-5 verbatim; clause 6 = PR #323 §7 verbatim)")
    lines.append("")
    lines.append(
        "**1. Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness."
    )
    lines.append("")
    lines.append(
        "**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / "
        "directional-comparison / classification-quality / feature-importance / "
        "per-pair-Sharpe-contribution columns are diagnostic-only. 27.0c extension "
        "preserved: conditional-PnL estimator constants and calibration reliability "
        "diagrams are diagnostic-only. 27.0d extends: regressor feature importance, "
        "predicted-vs-realised correlation, R², MAE, and predicted-PnL distribution are "
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
        "scope amendments; R7-D/Other NOT admissible. S-A/S-B/S-C formal at kickoff. "
        "S-D promoted to formal at 27.0c-β via PR #320. S-E promoted from 'requires "
        "scope amendment' to 'admissible at 27.0d-α design memo' via PR #323; on PR "
        "#324 merge S-E became formal at 27.0d-β. S-Other NOT admissible. Phase 26 "
        "deferred items NOT subsumed."
    )
    lines.append("")
    # §2
    lines.append("## 2. D-1 binding (formal realised-PnL = inherited harness)")
    lines.append("")
    lines.append(
        "Formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask "
        "executable). Mid-to-mid PnL appears in sanity probe only. The S-E regression "
        "target uses the SAME bid/ask executable harness on a per-row basis."
    )
    lines.append("")
    # §3
    lines.append("## 3. R7-A feature set (FIXED per Phase 27.0d-α §2)")
    lines.append("")
    lines.append(f"- ADMITTED: {list(ALL_FEATURES)}")
    lines.append("- NO new feature additions in 27.0d.")
    lines.append("")
    # §4
    lines.append("## 4. S-E + S-B-baseline cell definitions (per 27.0d-α §7.1)")
    lines.append("")
    lines.append("- C-se: S-E(row) = regressor.predict(row); LightGBM Huber regression")
    lines.append("- C-sb-baseline: S-B = raw P(TP) - P(SL); separately-fit multiclass head")
    lines.append("- 5-fold OOF protocol (seed=42); DIAGNOSTIC-ONLY (not in formal scoring)")
    lines.append(
        "- C-sb-baseline must reproduce 27.0b C-alpha0 (n_trades=34,626 / Sharpe=-0.1732 / "
        "ann_pnl=-204,664.4) or HALT with BaselineMismatchError"
    )
    lines.append("")
    # §5
    lines.append("## 5. Sanity probe (per 27.0d-α §10)")
    lines.append("")
    lines.append(f"- status: **{sanity.get('status', 'unknown')}**")
    cp_train = sanity.get("class_priors", {}).get("train", {})
    counts = cp_train.get("counts", {})
    shares = cp_train.get("shares", {})
    for cls, name in [(LABEL_TP, "TP"), (LABEL_SL, "SL"), (LABEL_TIME, "TIME")]:
        c = counts.get(cls, 0)
        s = shares.get(cls, float("nan"))
        lines.append(f"  - {name}: {c} ({s:.3%})")
    tgt = sanity.get("target_pnl_distribution_train", {})
    if "p50" in tgt:
        lines.append(
            f"- target PnL train: n={tgt.get('n_finite', 0)} "
            f"mean={tgt.get('mean', float('nan')):+.4f} "
            f"std={tgt.get('std', float('nan')):.4f} "
            f"p5={tgt.get('p5', float('nan')):+.4f} p50={tgt.get('p50', float('nan')):+.4f} "
            f"p95={tgt.get('p95', float('nan')):+.4f}"
        )
    drop_count = sanity.get("train_drop_for_nan_pnl_count", -1)
    lines.append(
        f"- NaN-PnL train rows dropped: {drop_count} (HALT > "
        f"{NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD:.1%} of n_train per D-J12)"
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
        "**Note**: 27.0d-β cannot mint ADOPT_CANDIDATE. H2 PASS → PROMISING_BUT_NEEDS_OOS."
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
    # §11 — 4-column baseline comparison
    lines.append("## 11. MANDATORY: Baseline comparison (per 27.0d-α §11.11)")
    lines.append("")
    if sel is None:
        sig = "n/a"
        r27d = (float("nan"), float("nan"), 0, float("nan"))
    else:
        rm = sel.get("test_realised_metrics", {})
        sig = _cell_signature(sel["cell"])
        r27d = (
            rm.get("sharpe", float("nan")),
            rm.get("annual_pnl", float("nan")),
            rm.get("n_trades", 0),
            sel.get("test_formal_spearman", float("nan")),
        )
    lines.append(
        "| Aspect | 26.0d R6-new-A C02 (#313) | 27.0b C-alpha0 / S-B (#318) | "
        "27.0c C-sd / S-D (#321) | 27.0d val-selected |"
    )
    lines.append("|---|---|---|---|---|")
    lines.append("| Feature set | R7-A | R7-A | R7-A | R7-A |")
    lines.append(
        "| Score objective | S-B | S-B (≡ α=0.0) | S-D calibrated EV | S-E or S-B per val-sel |"
    )
    lines.append(f"| Cell signature | C02 P(TP)-P(SL) | C-alpha0 (α=0.0) | C-sd | {sig} |")
    lines.append(f"| Test n_trades | 34,626 | 34,626 | 32,324 | {r27d[2]} |")
    lines.append(f"| Test Sharpe | -0.1732 | -0.1732 | -0.1760 | {r27d[0]:.4f} |")
    lines.append(f"| Test ann_pnl | -204,664.4 | -204,664.4 | (per #321) | {r27d[1]:+.1f} |")
    lines.append(f"| Test Spearman | -0.1535 | -0.1535 | -0.1060 | {r27d[3]:.4f} |")
    lines.append(
        f"| Verdict | REJECT (+ YES_IMPROVED) | REJECT_NON_DISCRIMINATIVE | "
        f"REJECT_NON_DISCRIMINATIVE | {verdict_info.get('verdict')} |"
    )
    lines.append("")
    # §12 — C-sb-baseline reproduction check
    lines.append("## 12. MANDATORY: C-sb-baseline reproduction check (per 27.0d-α §7.3)")
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
    # §13 — per-pair Sharpe contribution
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
    # §14 — pair concentration per cell
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
    # §15 — classification-quality (multiclass head only)
    lines.append("## 15. Classification-quality diagnostics on multiclass head (DIAGNOSTIC-ONLY)")
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
    # §16 — regressor feature importance
    lines.append("## 16. Regressor feature importance (4-bucket; DIAGNOSTIC-ONLY)")
    lines.append("")
    fi = regressor_feature_importance
    b = fi.get("buckets", {})
    bn = fi.get("buckets_normalised", {})
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
    # §17 — predicted-PnL distribution
    lines.append("## 17. NEW: Predicted-PnL distribution train/val/test (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| split | n_finite | p5 | p25 | p50 | p75 | p95 | mean |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for split_name in ("train", "val", "test"):
        s = predicted_pnl_distribution.get(split_name, {})
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
    # §18 — predicted-vs-realised correlation
    lines.append("## 18. NEW: Predicted-vs-realised correlation diagnostic (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| split / source | n | Pearson | Spearman |")
    lines.append("|---|---|---|---|")
    oof_agg_row = {
        "n": "n/a",
        "pearson": oof_corr_diag.get("aggregate_pearson", float("nan")),
        "spearman": oof_corr_diag.get("aggregate_spearman", float("nan")),
    }
    for label, d in [
        ("OOF aggregate", oof_agg_row),
        ("train (refit)", train_reg_diag),
        ("val", val_reg_diag),
        ("test", test_reg_diag),
    ]:
        n_str = str(d.get("n", "-"))
        p_val = d.get("pearson", float("nan"))
        s_val = d.get("spearman", float("nan"))
        lines.append(f"| {label} | {n_str} | {p_val:+.4f} | {s_val:+.4f} |")
    pos_f = oof_corr_diag.get("n_folds_pearson_positive", 0)
    tot_f = oof_corr_diag.get("n_folds", 0)
    lines.append(f"- OOF positive-Pearson folds: {pos_f}/{tot_f}")
    lines.append("")
    # §19 — regressor MAE + R²
    lines.append("## 19. NEW: Regressor MAE + R² on train/val/test (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| split | n | MAE | R² |")
    lines.append("|---|---|---|---|")
    for label, d in [("train", train_reg_diag), ("val", val_reg_diag), ("test", test_reg_diag)]:
        lines.append(
            f"| {label} | {d.get('n', 0)} | "
            f"{d.get('mae', float('nan')):.4f} | {d.get('r2', float('nan')):+.4f} |"
        )
    lines.append("")
    # §20 — multiple-testing caveat
    lines.append("## 20. Multiple-testing caveat")
    lines.append(
        f"{n_cells_run} formal cells × {len(THRESHOLDS_QUANTILE_PERCENTS)} quantile = "
        f"{n_cells_run * len(THRESHOLDS_QUANTILE_PERCENTS)} (cell, q) pairs. "
        "PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE are hypothesis-generating only."
    )
    lines.append("")
    # §21 — verdict statement
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

    print(f"=== Stage 27.0d-β S-E regression eval ({len(args.pairs)} pairs) ===")
    print(
        f"K_FAV={K_FAV} K_ADV={K_ADV} H_M1={H_M1_BARS} | "
        f"quantile candidates={THRESHOLDS_QUANTILE_PERCENTS}"
    )
    print(f"R7-A FIXED: {list(ALL_FEATURES)}")
    print(
        f"Regressor: LightGBMRegressor objective='huber' alpha={HUBER_ALPHA} "
        f"(inherited shape from multiclass head)"
    )
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

    # 5. Sanity probe (probe-only stage; train PnL / regressor / OOF deferred)
    sanity = run_sanity_probe_27_0d(train_df, val_df, test_df, pair_runtime_map, args.pairs)

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

    # 7. Precompute realised PnL for train + val + test (D-1 binding; target source)
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

    # NaN-PnL train-row check (D-J12 HALT)
    nan_pnl_mask = ~np.isfinite(pnl_train_full)
    nan_pnl_count = int(nan_pnl_mask.sum())
    threshold_count = NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD * len(pnl_train_full)
    print(f"  NaN-PnL train rows: {nan_pnl_count} (HALT > {int(threshold_count)} per D-J12)")
    if nan_pnl_count > threshold_count:
        raise SanityProbeError(
            f"train rows with NaN PnL = {nan_pnl_count} > "
            f"{NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD:.1%} of n_train "
            f"({int(threshold_count)}); regressor fit unsafe per D-J12"
        )

    # Filter NaN-PnL rows for regressor target (preserve full PnL vector for sanity probe)
    train_df_for_reg = train_df.loc[~nan_pnl_mask].reset_index(drop=True)
    pnl_train_for_reg = pnl_train_full[~nan_pnl_mask]

    # 8. Build labels (used for sanity probe + C-sb-baseline only)
    train_label = build_l1_labels_for_dataframe(train_df).to_numpy()
    val_label = build_l1_labels_for_dataframe(val_df).to_numpy()
    test_label = build_l1_labels_for_dataframe(test_df).to_numpy()

    # 9. 5-fold OOF regression (DIAGNOSTIC-ONLY per D-W4 / D-J5)
    print("Running 5-fold OOF regression (DIAGNOSTIC-ONLY; seed=42)...")
    fold_idx = make_oof_fold_assignment(len(pnl_train_for_reg), n_folds=OOF_N_FOLDS, seed=OOF_SEED)
    x_train_all = train_df_for_reg[list(ALL_FEATURES)]
    t0 = time.time()
    oof_preds = fit_oof_regression_diagnostic(x_train_all, pnl_train_for_reg, fold_idx)
    print(f"  OOF regression completed ({time.time() - t0:.1f}s; n={len(pnl_train_for_reg)})")
    oof_corr_diag = compute_oof_correlation_diagnostic(oof_preds, pnl_train_for_reg, fold_idx)
    print(
        f"  OOF pearson={oof_corr_diag['aggregate_pearson']:+.4f} "
        f"spearman={oof_corr_diag['aggregate_spearman']:+.4f} "
        f"(positive folds: {oof_corr_diag['n_folds_pearson_positive']}/{oof_corr_diag['n_folds']})"
    )

    # 10. Fit production regressor on full train (Huber loss)
    print("Fitting production regressor on full train (Huber loss)...")
    t0 = time.time()
    regressor = build_pipeline_lightgbm_regression_widened()
    x_val = val_df[list(ALL_FEATURES)]
    x_test = test_df[list(ALL_FEATURES)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        regressor.fit(x_train_all, pnl_train_for_reg)
    train_pred = compute_picker_score_s_e(regressor, x_train_all)
    val_pred = compute_picker_score_s_e(regressor, x_val)
    test_pred = compute_picker_score_s_e(regressor, x_test)
    regressor_feature_importance = compute_feature_importance_diagnostic(regressor)
    print(f"  fit + predict: {time.time() - t0:.1f}s")
    print(
        f"  regressor feature importance gain: "
        f"pair={regressor_feature_importance['buckets'].get('pair', 0):.1f}, "
        f"direction={regressor_feature_importance['buckets'].get('direction', 0):.1f}, "
        f"atr={regressor_feature_importance['buckets'].get('atr_at_signal_pip', 0):.1f}, "
        f"spread={regressor_feature_importance['buckets'].get('spread_at_signal_pip', 0):.1f}"
    )

    # Regression diagnostics per split (DIAGNOSTIC-ONLY)
    train_reg_diag = compute_regression_diagnostic(pnl_train_for_reg, train_pred)
    val_reg_diag = compute_regression_diagnostic(pnl_val_full, val_pred)
    test_reg_diag = compute_regression_diagnostic(pnl_test_full, test_pred)
    print(
        f"  regression diagnostics — train: MAE={train_reg_diag['mae']:.4f} "
        f"R²={train_reg_diag['r2']:+.4f}"
    )
    print(
        f"  regression diagnostics — val: MAE={val_reg_diag['mae']:.4f} "
        f"R²={val_reg_diag['r2']:+.4f} pearson={val_reg_diag['pearson']:+.4f}"
    )
    print(
        f"  regression diagnostics — test: MAE={test_reg_diag['mae']:.4f} "
        f"R²={test_reg_diag['r2']:+.4f} pearson={test_reg_diag['pearson']:+.4f}"
    )

    # 11. Fit production multiclass head on full train (C-sb-baseline only)
    print("Fitting production multiclass head on full train (C-sb-baseline only)...")
    t0 = time.time()
    multiclass_pipeline = build_pipeline_lightgbm_multiclass_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        multiclass_pipeline.fit(x_train_all, train_label[~nan_pnl_mask])
    final_step = multiclass_pipeline.steps[-1][1]
    classes = np.asarray(getattr(final_step, "classes_", np.arange(NUM_CLASSES)))
    val_raw_probs_native = multiclass_pipeline.predict_proba(x_val)
    test_raw_probs_native = multiclass_pipeline.predict_proba(x_test)
    val_raw_probs = np.zeros((len(val_raw_probs_native), NUM_CLASSES), dtype=np.float64)
    test_raw_probs = np.zeros((len(test_raw_probs_native), NUM_CLASSES), dtype=np.float64)
    for col_idx, cls in enumerate(classes):
        cls_int = int(cls)
        val_raw_probs[:, cls_int] = val_raw_probs_native[:, col_idx]
        test_raw_probs[:, cls_int] = test_raw_probs_native[:, col_idx]
    print(f"  multiclass fit + predict_proba: {time.time() - t0:.1f}s")

    # 12. Update sanity probe with post-fit diagnostics
    sanity["target_pnl_distribution_train"] = {
        "n_finite": int(np.isfinite(pnl_train_full).sum()),
        "mean": float(np.mean(pnl_train_full[np.isfinite(pnl_train_full)])),
        "std": float(np.std(pnl_train_full[np.isfinite(pnl_train_full)])),
        "p5": float(np.quantile(pnl_train_full[np.isfinite(pnl_train_full)], 0.05)),
        "p25": float(np.quantile(pnl_train_full[np.isfinite(pnl_train_full)], 0.25)),
        "p50": float(np.quantile(pnl_train_full[np.isfinite(pnl_train_full)], 0.50)),
        "p75": float(np.quantile(pnl_train_full[np.isfinite(pnl_train_full)], 0.75)),
        "p95": float(np.quantile(pnl_train_full[np.isfinite(pnl_train_full)], 0.95)),
        "min": float(np.min(pnl_train_full[np.isfinite(pnl_train_full)])),
        "max": float(np.max(pnl_train_full[np.isfinite(pnl_train_full)])),
    }
    predicted_pnl_distribution: dict[str, dict] = {}
    for split_name, pred in [("train", train_pred), ("val", val_pred), ("test", test_pred)]:
        finite = pred[np.isfinite(pred)]
        if len(finite) == 0:
            predicted_pnl_distribution[split_name] = {"n_finite": 0}
            continue
        predicted_pnl_distribution[split_name] = {
            "n_finite": int(len(finite)),
            "mean": float(finite.mean()),
            "p5": float(np.quantile(finite, 0.05)),
            "p25": float(np.quantile(finite, 0.25)),
            "p50": float(np.quantile(finite, 0.50)),
            "p75": float(np.quantile(finite, 0.75)),
            "p95": float(np.quantile(finite, 0.95)),
        }
    sanity["predicted_pnl_distribution"] = predicted_pnl_distribution
    sanity["oof_correlation_diagnostic"] = oof_corr_diag
    sanity["regression_diagnostic"] = {
        "train": train_reg_diag,
        "val": val_reg_diag,
        "test": test_reg_diag,
    }
    sanity["regressor_feature_importance"] = regressor_feature_importance
    sanity["train_drop_for_nan_pnl_count"] = nan_pnl_count

    # 13. Score per cell + per quantile + cell evaluation
    # C-se: regressor predictions; C-sb-baseline: raw P(TP) - P(SL) from multiclass head
    val_score_s_b_raw = compute_picker_score_s_b_raw(val_raw_probs)
    test_score_s_b_raw = compute_picker_score_s_b_raw(test_raw_probs)
    val_score_s_e = val_pred
    test_score_s_e = test_pred

    cells = build_s_e_cells()
    n_cells_run = len(cells)
    cell_results: list[dict] = []
    for i, cell in enumerate(cells):
        t_cell = time.time()
        if cell["score_type"] == "s_e":
            val_score, test_score = val_score_s_e, test_score_s_e
        elif cell["score_type"] == "s_b_raw":
            val_score, test_score = val_score_s_b_raw, test_score_s_b_raw
        else:
            raise ValueError(f"Unknown score_type: {cell['score_type']}")
        try:
            result = evaluate_cell_27_0d(
                cell,
                train_df,
                val_df,
                test_df,
                train_label,
                val_label,
                test_label,
                val_raw_probs,
                test_raw_probs,
                val_score,
                test_score,
                pnl_val_full,
                pnl_test_full,
                regressor_feature_importance
                if cell["score_type"] == "s_e"
                else compute_feature_importance_diagnostic(multiclass_pipeline),
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

    # 14. C-sb-baseline match check (FAIL-FAST per D-J9)
    print("\n=== C-sb-baseline match check (per 27.0d-α §7.3 / D-J9) ===")
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

    # 15. Val-selection + verdict + cross-cell aggregation
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

    # 16. Write 21-section eval report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report_27_0d(
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
        regressor_feature_importance,
        train_reg_diag,
        val_reg_diag,
        test_reg_diag,
        oof_corr_diag,
        sanity["target_pnl_distribution_train"],
        predicted_pnl_distribution,
    )
    print(f"\nReport: {report_path}")

    # 17. Persist artifacts
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
    aggregate["regression_diagnostic"] = sanity["regression_diagnostic"]
    aggregate["oof_correlation_diagnostic"] = oof_corr_diag
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
