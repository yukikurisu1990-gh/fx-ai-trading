"""Stage 26.0d-β R6-new-A feature-widening audit eval.

Implements the binding contract from PR #312 (26.0d-α R6-new-A design memo)
under the scope amendment from PR #311 (Phase 26 mandatory clause 6 AMENDED).

R6-new-A is a FEATURE-WIDENING AUDIT, NOT a model-class comparison:
  - The tested intervention is the closed two-feature allowlist
    (atr_at_signal_pip + spread_at_signal_pip) added on top of the Phase 26
    minimum feature set (pair + direction).
  - The model class is held fixed at the conservative LightGBM multiclass
    configuration inherited from 26.0c-β (PR #309). No model selection,
    no calibration tuning, no hyperparameter search is part of this audit.

Inherits label class (L-1 ternary {TP=0, SL=1, TIME=2}), pickers (P(TP),
P(TP)-P(SL)), threshold family (quantile-of-val {5,10,20,30,40}%),
verdict tree, realised-PnL cache (bid/ask executable; D-1 binding), and
sanity-probe scaffolding from 26.0c-β. Adds:

  - Widened pipeline (4-feature ColumnTransformer: pair/direction one-hot
    + atr_at_signal_pip/spread_at_signal_pip numeric passthrough)
  - Row-drop missingness policy for the new features
  - Sanity-probe extensions (NaN rate + positivity assertions)
  - Identity-break detector (YES / NO / PARTIAL) per 26.0d-α §13
  - Feature-importance diagnostic (4-bucket aggregation)
  - Mandatory L-1 / L-2 / L-3 vs R6-new-A 4-column comparison section
    in eval_report.md

MANDATORY CLAUSES (clause 6 AMENDED per PR #311 §8; clauses 1-5 verbatim
unchanged from #299 §7 / 26.0a-α §9 / 26.0b-α §9 / 26.0c-α §12 / 26.0d-α §16):

1. Phase 26 framing. Phase 26 is the entry-side return on alternative
   label / target designs on the 20-pair canonical universe. ADOPT
   requires both H2 PASS and the full 8-gate A0-A5 harness.
2. Diagnostic columns prohibition. Calibration / threshold-sweep /
   directional-comparison / classification-quality / feature-importance
   columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend
   on any single one of them.
3. γ closure preservation. Phase 24 γ hard-close (PR #279) is unmodified.
4. Production-readiness preservation. X-v2 OOS gating remains required
   before any production deployment. Production v9 20-pair (Phase 9.12
   closure) remains untouched.
5. NG#10 / NG#11 not relaxed.
6. Phase 26 scope (AMENDED). Phase 26's primary axis is label / target
   redesign on the 20-pair canonical universe. Phase 26 is NOT a revival
   of Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain
   deferred-not-foreclosed under Phase 25 semantics. A narrow
   feature-widening audit (R6-new-A) is authorised under the scope
   amendment in PR #311 with a closed allowlist of two features
   (atr_at_signal_pip, spread_at_signal_pip); all other features are
   out of scope until a further scope amendment. R6-new-A is a Phase 26
   audit of the minimum-feature-set hypothesis; it is NOT a Phase 25
   continuation.

PRODUCTION-MISUSE GUARDS (verbatim per 26.0a-α §5.1):

GUARD 1 — research-not-production: R6-new-A features stay in scripts/;
not auto-routed to feature_service.py.
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
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage26_0d"
DATA_DIR = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage25_0b = importlib.import_module("stage25_0b_f1_volatility_expansion_eval")
stage26_0b = importlib.import_module("stage26_0b_l2_eval")
stage26_0c = importlib.import_module("stage26_0c_l1_eval")

# Inherited constants and harness functions
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

# Inherited L-1 functions
build_l1_labels_for_dataframe = stage26_0c.build_l1_labels_for_dataframe
compute_picker_score_ptp = stage26_0c.compute_picker_score_ptp
compute_picker_score_diff = stage26_0c.compute_picker_score_diff
compute_picker_score = stage26_0c.compute_picker_score
fit_quantile_cutoff_on_val = stage26_0c.fit_quantile_cutoff_on_val
evaluate_quantile_family = stage26_0c.evaluate_quantile_family
evaluate_absolute_family = stage26_0c.evaluate_absolute_family
compute_8_gate_from_pnls = stage26_0c.compute_8_gate_from_pnls
compute_classification_diagnostics = stage26_0c.compute_classification_diagnostics
compute_mid_to_mid_pnl_diagnostic = stage26_0c.compute_mid_to_mid_pnl_diagnostic
assign_verdict = stage26_0c.assign_verdict
aggregate_cross_cell_verdict = stage26_0c.aggregate_cross_cell_verdict
select_cell_validation_only = stage26_0c.select_cell_validation_only
compute_isotonic_diagnostic_appendix = stage26_0c.compute_isotonic_diagnostic_appendix
SanityProbeError = stage26_0c.SanityProbeError


# ---------------------------------------------------------------------------
# Binding constants (per 26.0d-α / inherited from 26.0c-α)
# ---------------------------------------------------------------------------

# Barrier geometry (inherited unchanged from L-1/L-2/L-3)
K_FAV = stage25_0b.K_FAV  # 1.5
K_ADV = stage25_0b.K_ADV  # 1.0
H_M1_BARS = stage25_0b.H_M1_BARS  # 60

# L-1 class encoding (inherited from 26.0c-α §2.3)
LABEL_TP = stage26_0c.LABEL_TP
LABEL_SL = stage26_0c.LABEL_SL
LABEL_TIME = stage26_0c.LABEL_TIME
NUM_CLASSES = stage26_0c.NUM_CLASSES

# Picker IDs (inherited B1+B2 from 26.0c-α §3)
PICKER_PTP = stage26_0c.PICKER_PTP
PICKER_DIFF = stage26_0c.PICKER_DIFF
FORMAL_PICKERS = stage26_0c.FORMAL_PICKERS

# Threshold family (inherited from 26.0c-α §4)
THRESHOLDS_QUANTILE_PERCENTS = stage26_0c.THRESHOLDS_QUANTILE_PERCENTS
ABSOLUTE_THRESHOLDS_PTP = stage26_0c.ABSOLUTE_THRESHOLDS_PTP
ABSOLUTE_THRESHOLDS_DIFF = stage26_0c.ABSOLUTE_THRESHOLDS_DIFF

# 26.0c-α §4.1 binding fixed conservative LightGBM multiclass config
# (re-declared here to enable signature/identity checks in tests)
LIGHTGBM_FIXED_CONFIG = dict(stage26_0c.LIGHTGBM_FIXED_CONFIG)

# H1 two-tier thresholds — formal H1 = Spearman(score, realised_pnl)
H1_WEAK_THRESHOLD = stage26_0c.H1_WEAK_THRESHOLD
H1_MEANINGFUL_THRESHOLD = stage26_0c.H1_MEANINGFUL_THRESHOLD

# H3 reference (Phase 25 F1 best realised Sharpe; unchanged per Decision G)
H3_REFERENCE_SHARPE = stage26_0c.H3_REFERENCE_SHARPE

# Concentration diagnostic threshold (inherited; diagnostic-only)
CONCENTRATION_HIGH_THRESHOLD = stage26_0c.CONCENTRATION_HIGH_THRESHOLD

# Sanity probe thresholds (inherited)
SANITY_MIN_CLASS_SHARE = stage26_0c.SANITY_MIN_CLASS_SHARE
SANITY_MAX_PER_PAIR_TIME_SHARE = stage26_0c.SANITY_MAX_PER_PAIR_TIME_SHARE

# Span budgets (inherited from L-1/L-2/L-3)
TEST_SPAN_YEARS = SPAN_YEARS * (1.0 - TRAIN_FRAC - VAL_FRAC)
VAL_SPAN_YEARS = SPAN_YEARS * VAL_FRAC

# ---------------------------------------------------------------------------
# NEW R6-new-A constants (the feature-widening delta)
# ---------------------------------------------------------------------------

# Closed allowlist (verbatim from PR #311 §3.1)
CATEGORICAL_COLS = ["pair", "direction"]
NUMERIC_FEATURES = ("atr_at_signal_pip", "spread_at_signal_pip")
ALL_FEATURES = ("pair", "direction", "atr_at_signal_pip", "spread_at_signal_pip")

# Sanity probe — new-feature missingness threshold (per 26.0d-α §12.2 / Decision F)
SANITY_MAX_NEW_FEATURE_NAN_RATE = 0.05

# Sanity probe — new-feature positivity violation threshold
SANITY_MAX_POSITIVITY_VIOLATION_RATE = 0.01

# Identity-break detector tolerances (per Decisions D2/D3/D4)
IDENTITY_BREAK_N_TRADES_TOLERANCE = 0  # exact match
IDENTITY_BREAK_SHARPE_ABS_TOLERANCE = 1e-4
IDENTITY_BREAK_ANN_PNL_ABS_TOLERANCE = 0.5  # pip

# Identity-break PARTIAL triggers (per Decision D5)
IDENTITY_BREAK_PARTIAL_N_TRADES_DELTA = 100
IDENTITY_BREAK_PARTIAL_CONCENTRATION_SHARE_DELTA = 0.05

# Baseline values (from L-1 / L-2 / L-3 val-selected outcome; fixed)
BASELINE_TEST_N_TRADES = 42150
BASELINE_TEST_SHARPE = -0.2232
BASELINE_TEST_ANN_PNL = -237310.8
BASELINE_TOP_PAIR = "USD_JPY"
BASELINE_TOP_PAIR_SHARE = 1.0


# ---------------------------------------------------------------------------
# Missingness policy (per Decision F; per 26.0d-α §5.2)
# ---------------------------------------------------------------------------


def drop_rows_with_missing_new_features(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict]:
    """Drop rows where any of the NEW R6-new-A features is NaN or non-finite.

    Per 26.0d-α §5.2 / Decision F1 binding: NO imputation; pure row-drop.

    Returns (df_filtered, drop_stats) where drop_stats records per-feature counts.
    """
    n_input = len(df)
    if n_input == 0:
        return df.copy(), {"n_input": 0, "n_kept": 0, "n_dropped": 0, "per_feature_nan": {}}
    per_feature_nan: dict[str, int] = {}
    keep_mask = np.ones(n_input, dtype=bool)
    for feat in NUMERIC_FEATURES:
        col = df[feat].to_numpy(dtype=np.float64)
        nan_mask = ~np.isfinite(col)
        per_feature_nan[feat] = int(nan_mask.sum())
        keep_mask &= ~nan_mask
    df_filtered = df.loc[keep_mask].reset_index(drop=True)
    return df_filtered, {
        "n_input": int(n_input),
        "n_kept": int(len(df_filtered)),
        "n_dropped": int(n_input - len(df_filtered)),
        "per_feature_nan": per_feature_nan,
    }


# ---------------------------------------------------------------------------
# Widened pipeline (per Decision G / 26.0d-α §5.1)
# ---------------------------------------------------------------------------


def build_pipeline_lightgbm_multiclass_widened() -> Pipeline:
    """Multiclass LightGBM pipeline with the CLOSED 4-feature allowlist.

    Per 26.0d-α §5.1 binding:
      - pair + direction: one-hot encoded
      - atr_at_signal_pip + spread_at_signal_pip: numeric passthrough
      - NO standardisation (LightGBM scale-invariant; per Decision G)
      - NO imputation (row-drop handles missingness; per Decision F)

    R6-new-A is a feature-widening audit: the model class is held fixed
    at the conservative LightGBM configuration inherited from #309. The
    only delta vs #309 is the widened feature set.
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
            (
                "clf",
                lgb.LGBMClassifier(**LIGHTGBM_FIXED_CONFIG, verbose=-1),
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Formal cell grid (per Decision E / 26.0d-α §10)
# ---------------------------------------------------------------------------


def build_cells() -> list[dict]:
    """R6-new-A formal grid: 2 cells = 2 pickers × raw probability only.

    Per 26.0d-α §10 binding: identical grid shape to 26.0c-β (#309). The
    only delta is the input feature set (handled at the pipeline level).
    """
    return [
        {"id": "C01", "picker": PICKER_PTP},
        {"id": "C02", "picker": PICKER_DIFF},
    ]


# ---------------------------------------------------------------------------
# Feature importance diagnostic (per Decision D10 / 26.0d-α §11.4)
# ---------------------------------------------------------------------------


def compute_feature_importance_diagnostic(pipeline: Pipeline) -> dict:
    """LightGBM gain importance aggregated into 4 buckets.

    Per Decision D10 binding:
      - pair: aggregate over all pair_* one-hots
      - direction: aggregate over all direction_* one-hots
      - atr_at_signal_pip: individual
      - spread_at_signal_pip: individual

    DIAGNOSTIC-ONLY per 26.0d-α §11.4; NEVER used in formal verdict
    routing (clause 2 binding).
    """
    clf = pipeline.named_steps["clf"]
    pre = pipeline.named_steps["pre"]
    feature_names = list(pre.get_feature_names_out())
    importances = np.asarray(clf.feature_importances_, dtype=np.float64)
    if len(feature_names) != len(importances):
        return {
            "buckets": {
                "pair": float("nan"),
                "direction": float("nan"),
                "atr_at_signal_pip": float("nan"),
                "spread_at_signal_pip": float("nan"),
            },
            "buckets_normalised": {
                "pair": float("nan"),
                "direction": float("nan"),
                "atr_at_signal_pip": float("nan"),
                "spread_at_signal_pip": float("nan"),
            },
            "total": 0.0,
            "warning": (
                f"length mismatch between feature_names ({len(feature_names)}) "
                f"and importances ({len(importances)})"
            ),
        }
    buckets = {
        "pair": 0.0,
        "direction": 0.0,
        "atr_at_signal_pip": 0.0,
        "spread_at_signal_pip": 0.0,
    }
    for name, imp in zip(feature_names, importances, strict=True):
        imp_f = float(imp)
        if "atr_at_signal_pip" in name:
            buckets["atr_at_signal_pip"] += imp_f
        elif "spread_at_signal_pip" in name:
            buckets["spread_at_signal_pip"] += imp_f
        elif "pair" in name:
            buckets["pair"] += imp_f
        elif "direction" in name:
            buckets["direction"] += imp_f
    total = sum(buckets.values())
    buckets_normalised = (
        {k: (v / total if total > 0 else float("nan")) for k, v in buckets.items()}
        if total > 0
        else {k: float("nan") for k in buckets}
    )
    return {
        "buckets": buckets,
        "buckets_normalised": buckets_normalised,
        "total": float(total),
    }


# ---------------------------------------------------------------------------
# Identity-break detector (per Decision H / 26.0d-α §13.2-§13.4)
# ---------------------------------------------------------------------------


def detect_identity_break(r6_val_selected: dict | None) -> dict:
    """Compare R6-new-A val-selected (cell*, q*) vs L-1/L-2/L-3 baseline.

    Per 26.0d-α §13.2-§13.4 binding:
      - Baseline: n_trades=42150, Sharpe=-0.2232, ann_pnl=-237310.8,
        top_pair=USD_JPY share=1.0
      - YES (improved):  trade set differs + Sharpe improves
      - YES (same/worse): trade set differs + Sharpe does NOT improve
      - NO (identity persists): all 4 metrics match within tolerance
      - PARTIAL: n_trades or concentration changes meaningfully + Sharpe
        does NOT improve

    Critical wording (per user correction on Decision H):
      The NO interpretation MUST state: "closed two-feature allowlist
      did NOT break the identity; this does NOT prove feature widening
      cannot help; further feature widening would require a separate
      scope amendment." It MUST NOT state "minimum-feature-set
      hypothesis is rejected."
    """
    if r6_val_selected is None:
        return {
            "verdict": "NO_VAL_SELECTED",
            "trade_set_differs": False,
            "sharpe_improved": None,
            "ann_pnl_improved": None,
            "concentration_changed": False,
            "reason": "no valid val-selected cell to compare against baseline",
        }
    rm = r6_val_selected.get("test_realised_metrics", {})
    n_trades = int(rm.get("n_trades", 0))
    sharpe = float(rm.get("sharpe", float("nan")))
    ann_pnl = float(rm.get("annual_pnl", float("nan")))
    conc = r6_val_selected.get("test_concentration", {})
    top_pair = conc.get("top_pair")
    top_pair_share = float(conc.get("top_pair_share", float("nan")))

    n_trades_delta = n_trades - BASELINE_TEST_N_TRADES
    sharpe_delta = sharpe - BASELINE_TEST_SHARPE
    ann_pnl_delta = ann_pnl - BASELINE_TEST_ANN_PNL
    concentration_share_delta = (
        top_pair_share - BASELINE_TOP_PAIR_SHARE if np.isfinite(top_pair_share) else float("nan")
    )

    n_trades_matches = abs(n_trades_delta) <= IDENTITY_BREAK_N_TRADES_TOLERANCE
    sharpe_matches = (
        np.isfinite(sharpe) and abs(sharpe_delta) <= IDENTITY_BREAK_SHARPE_ABS_TOLERANCE
    )
    ann_pnl_matches = (
        np.isfinite(ann_pnl) and abs(ann_pnl_delta) <= IDENTITY_BREAK_ANN_PNL_ABS_TOLERANCE
    )
    top_pair_matches = (
        top_pair == BASELINE_TOP_PAIR
        and np.isfinite(top_pair_share)
        and abs(concentration_share_delta) <= IDENTITY_BREAK_PARTIAL_CONCENTRATION_SHARE_DELTA
    )

    identity_holds = n_trades_matches and sharpe_matches and ann_pnl_matches and top_pair_matches

    trade_set_differs = not (n_trades_matches and top_pair_matches)
    sharpe_improved = np.isfinite(sharpe) and (sharpe - BASELINE_TEST_SHARPE) > 1e-6
    ann_pnl_improved = np.isfinite(ann_pnl) and (ann_pnl - BASELINE_TEST_ANN_PNL) > 1e-6
    concentration_changed = (top_pair != BASELINE_TOP_PAIR) or (
        np.isfinite(concentration_share_delta)
        and abs(concentration_share_delta) > IDENTITY_BREAK_PARTIAL_CONCENTRATION_SHARE_DELTA
    )

    # Verdict tree (per 26.0d-α §13.3)
    if identity_holds:
        verdict = "NO"
        reason = (
            "Closed two-feature allowlist did NOT break the identity. "
            "Val-selected test n_trades, Sharpe, ann_pnl, and pair concentration "
            "all match the L-1 / L-2 / L-3 baseline within tolerance. "
            "This does NOT prove feature widening cannot help; it says only that "
            "this specific minimal allowlist did not change the val-selected "
            "ranking at the fixed model class. Further feature widening "
            "(R6-new-B / R6-new-C / R6-new-D, multi-TF, calendar, external-data) "
            "would require a separate scope amendment per PR #311 §3.2. "
            "The minimum-feature-set hypothesis is NOT rejected; it is "
            "NOT supported either under this narrow allowlist."
        )
    elif trade_set_differs and sharpe_improved:
        verdict = "YES_IMPROVED"
        reason = (
            "Val-selected trade set differs from baseline AND test Sharpe "
            f"improved by {sharpe_delta:+.4f}. The closed two-feature allowlist "
            "broke the identity and improved realised PnL. The minimum-feature-"
            "set hypothesis (post-26.0c §3 / §4) is SUPPORTED as binding at "
            "this closed allowlist. Routes to H1/H2/H3 ladder per design "
            "memo §9."
        )
    elif trade_set_differs and not sharpe_improved:
        verdict = "YES_SAME_OR_WORSE"
        reason = (
            "Val-selected trade set differs from baseline but test Sharpe did "
            f"NOT improve (delta={sharpe_delta:+.4f}). Feature widening changed "
            "selection but did NOT improve realised PnL at this allowlist. "
            "Supports the minimum-feature-set hypothesis being binding even "
            "at this widened allowlist — the audit confirms feature widening "
            "at this closed allowlist is not the right lever."
        )
    else:
        # PARTIAL: n_trades or concentration changes but neither full identity
        # nor decisive trade-set differentiation
        n_trades_partial = abs(n_trades_delta) > IDENTITY_BREAK_PARTIAL_N_TRADES_DELTA
        concentration_partial = (
            np.isfinite(concentration_share_delta)
            and abs(concentration_share_delta) > IDENTITY_BREAK_PARTIAL_CONCENTRATION_SHARE_DELTA
        )
        if (n_trades_partial or concentration_partial) and not sharpe_improved:
            verdict = "PARTIAL"
            reason = (
                "Val-selected n_trades or pair-concentration top-share changed "
                "meaningfully versus baseline, but test Sharpe did NOT improve. "
                "The ranking mechanism is partially sensitive to the new features "
                "(selection changes), but realised PnL does not improve. Routes "
                "to post-26.0d routing review for next-step framing."
            )
        else:
            # Edge case: small numeric drift below thresholds; treat as NO
            verdict = "NO"
            reason = (
                "Metrics differ marginally from baseline but within identity-"
                "break tolerances. Treated as NO (identity persists). Same "
                "wording binding as NO: closed two-feature allowlist did not "
                "break the identity; further feature widening would require a "
                "separate scope amendment per PR #311 §3.2."
            )

    return {
        "verdict": verdict,
        "trade_set_differs": bool(trade_set_differs),
        "sharpe_improved": bool(sharpe_improved),
        "ann_pnl_improved": bool(ann_pnl_improved),
        "concentration_changed": bool(concentration_changed),
        "n_trades_observed": int(n_trades),
        "n_trades_baseline": int(BASELINE_TEST_N_TRADES),
        "n_trades_delta": int(n_trades_delta),
        "sharpe_observed": float(sharpe),
        "sharpe_baseline": float(BASELINE_TEST_SHARPE),
        "sharpe_delta": float(sharpe_delta),
        "ann_pnl_observed": float(ann_pnl),
        "ann_pnl_baseline": float(BASELINE_TEST_ANN_PNL),
        "ann_pnl_delta": float(ann_pnl_delta),
        "top_pair_observed": top_pair,
        "top_pair_baseline": BASELINE_TOP_PAIR,
        "top_pair_share_observed": float(top_pair_share)
        if np.isfinite(top_pair_share)
        else float("nan"),
        "top_pair_share_baseline": float(BASELINE_TOP_PAIR_SHARE),
        "top_pair_share_delta": float(concentration_share_delta)
        if np.isfinite(concentration_share_delta)
        else float("nan"),
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Sanity probe (extends 26.0c-α §10 with 2 new checks; per 26.0d-α §12)
# ---------------------------------------------------------------------------


def run_sanity_probe_r6_new_a(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    pairs: list[str],
) -> dict:
    """R6-new-A sanity probe (per 26.0d-α §12).

    Inherited checks from 26.0c-α §10:
      1. Class priors (TP / SL / TIME) per split — HALT if any class < 1%
      2. Per-pair TIME-class share — HALT if any pair > 99% TIME share
      3. Realised-PnL cache basis check (inherited bid/ask harness)
      4. Mid-to-mid PnL distribution per class on TRAIN (diagnostic-only)

    NEW R6-new-A checks (per 26.0d-α §12.2):
      5. new-feature NaN rate <= 5% per split (HALT otherwise)
      6. new-feature distribution snapshot per pair + positivity assertions
         (HALT if positivity violated on >= 1% of rows)
    """
    print("\n=== R6-new-A SANITY PROBE (per 26.0d-α §12) ===")
    out: dict = {}

    # 1. Class priors per split (inherited from 26.0c-α §10)
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

    # 2. Per-pair TIME-class share on train (inherited from 26.0c-α §10)
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

    # 3. Mid-to-mid PnL distribution per class on train (inherited; diagnostic-only)
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

    # 4. Inherited realised-PnL harness basis check (inherited from 26.0c-α §10)
    print("  realised-PnL cache basis check (per D-1 binding):")
    pnl_cache_sig = inspect.signature(precompute_realised_pnl_per_row)
    if "spread_factor" in pnl_cache_sig.parameters or "mid_to_mid" in pnl_cache_sig.parameters:
        raise SanityProbeError(
            "precompute_realised_pnl_per_row signature exposes spread_factor / mid_to_mid — "
            "inherited harness basis violated"
        )
    barrier_pnl_src = inspect.getsource(_compute_realised_barrier_pnl)
    if not all(tok in barrier_pnl_src for tok in ["bid_h", "ask_l", "ask_h", "bid_l"]):
        raise SanityProbeError(
            "_compute_realised_barrier_pnl does not reference bid_h/ask_l/ask_h/bid_l — "
            "executable bid/ask treatment cannot be confirmed"
        )
    out["realised_pnl_cache_basis"] = "inherited_compute_realised_barrier_pnl_bid_ask_executable"
    print("    OK: bid/ask executable treatment confirmed in inherited harness")

    # 5. NEW: new-feature NaN rate per split (per 26.0d-α §12.2)
    print("  new-feature NaN-rate check (per 26.0d-α §12.2):")
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

    # 6. NEW: new-feature distribution snapshot + positivity assertions
    print("  new-feature distribution snapshot on TRAIN (per 26.0d-α §12.2):")
    out["new_feature_distribution_train"] = {}
    positivity_violations: list[tuple[str, str, float]] = []
    for feat in NUMERIC_FEATURES:
        col = train_df[feat].to_numpy(dtype=np.float64)
        finite_mask = np.isfinite(col)
        finite = col[finite_mask]
        if len(finite) == 0:
            out["new_feature_distribution_train"][feat] = {"n_finite": 0}
            print(f"    {feat}: n=0 (no finite values)")
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
        out["new_feature_distribution_train"][feat] = stats
        print(
            f"    {feat}: n={stats['n_finite']} mean={stats['mean']:+.3f} "
            f"p5={stats['p5']:+.3f} p50={stats['p50']:+.3f} "
            f"p95={stats['p95']:+.3f} min={stats['min']:+.3f} max={stats['max']:+.3f}"
        )
        # Positivity assertions
        if feat == "atr_at_signal_pip":
            violation_mask = finite <= 0
            violation_rate = int(violation_mask.sum()) / len(finite) if len(finite) > 0 else 0.0
            if violation_rate > SANITY_MAX_POSITIVITY_VIOLATION_RATE:
                positivity_violations.append((feat, "<=0", violation_rate))
            stats["positivity_violation_rate"] = violation_rate
        elif feat == "spread_at_signal_pip":
            violation_mask = finite < 0
            violation_rate = int(violation_mask.sum()) / len(finite) if len(finite) > 0 else 0.0
            if violation_rate > SANITY_MAX_POSITIVITY_VIOLATION_RATE:
                positivity_violations.append((feat, "<0", violation_rate))
            stats["positivity_violation_rate"] = violation_rate

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
    if nan_violations:
        raise SanityProbeError(
            f"new-feature NaN rate over {SANITY_MAX_NEW_FEATURE_NAN_RATE:.0%} "
            f"on {len(nan_violations)} (split, feature) pair(s): {nan_violations[:5]}"
        )
    if positivity_violations:
        raise SanityProbeError(
            f"new-feature positivity violated on >{SANITY_MAX_POSITIVITY_VIOLATION_RATE:.0%} "
            f"of rows: {positivity_violations[:5]}"
        )

    print("=== SANITY PROBE: PASS ===\n")
    out["status"] = "PASS"
    return out


# ---------------------------------------------------------------------------
# Per-cell evaluation (per 26.0d-α §10)
# ---------------------------------------------------------------------------


def evaluate_cell_r6_new_a(
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
    """R6-new-A cell evaluation.

    Differs from 26.0c-β `evaluate_cell` only in:
      - widened feature set (handled at pipeline level upstream)
      - feature-importance diagnostic attached to the cell result
      - all other logic inherited unchanged from 26.0c-β
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

    # PRIMARY family: quantile-of-val (inherited from 26.0c-β)
    quantile_results = evaluate_quantile_family(
        score_val,
        pnl_val_full,
        score_test,
        pnl_test_full,
        VAL_SPAN_YEARS,
        TEST_SPAN_YEARS,
    )

    # SECONDARY DIAGNOSTIC family: absolute thresholds (inherited; diagnostic-only)
    absolute_results = evaluate_absolute_family(
        score_val,
        pnl_val_full,
        score_test,
        pnl_test_full,
        picker,
        VAL_SPAN_YEARS,
        TEST_SPAN_YEARS,
    )

    # Pick best q on val by realised Sharpe (inherited tie-breaker chain)
    def _q_sort_key(r: dict) -> tuple:
        v = r["val"]
        s = v["sharpe"] if np.isfinite(v["sharpe"]) else -np.inf
        return (s, v["annual_pnl"], v["n_trades"], -r["q_percent"])

    best_q_record = max(quantile_results, key=_q_sort_key)

    test_realised = best_q_record["test"]["realised_pnls"]
    gate_block = compute_8_gate_from_pnls(test_realised)

    # Classification diagnostics on test (diagnostic-only, includes Spearman(score, pnl))
    cls_diag = compute_classification_diagnostics(test_label, test_probs, score_test, pnl_test_full)
    formal_spearman = cls_diag.get("spearman_score_vs_pnl", float("nan"))

    # Per-pair / per-direction trade count for the val-selected (cell, q) on test
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

    # Pair concentration (DIAGNOSTIC-ONLY)
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
        "test_formal_spearman": float(formal_spearman),
        "val_concentration": val_concentration,
        "test_concentration": test_concentration,
        "test_classification_diag": cls_diag,
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
        "feature_importance": feature_importance_diag,
        "low_power": low_power,
        "h_state": "OK",
    }


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def _cell_signature(cell: dict) -> str:
    return f"id={cell['id']} picker={cell['picker']}"


def write_eval_report_r6_new_a(
    out_path: Path,
    cell_results: list[dict],
    val_select: dict,
    verdict_info: dict,
    aggregate_info: dict,
    identity_break: dict,
    sanity: dict,
    drop_stats: dict,
    split_dates: tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp],
    preflight_diag: dict,
    n_cells_run: int,
) -> None:
    t_min, t70, t85, t_max = split_dates
    lines: list[str] = []
    lines.append("# Stage 26.0d-β — R6-new-A Feature-Widening Audit Eval Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append(
        "Design contract: `docs/design/phase26_0d_alpha_r6_new_a_design_memo.md` (PR #312) "
        "under scope amendment `docs/design/phase26_scope_amendment_feature_widening.md` (PR #311)."
    )
    lines.append("")
    lines.append(
        "R6-new-A is a feature-widening AUDIT, NOT a model-class comparison. The tested "
        "intervention is the closed two-feature allowlist (`atr_at_signal_pip`, "
        "`spread_at_signal_pip`) added to the Phase 26 minimum feature set "
        "(`pair + direction`). Model class is held fixed at the conservative "
        "LightGBM multiclass configuration inherited from 26.0c-β (PR #309)."
    )
    lines.append("")
    lines.append("## Mandatory clauses (clause 6 AMENDED per PR #311 §8)")
    lines.append("")
    lines.append(
        "**1. Phase 26 framing.** Phase 26 is the entry-side return on alternative "
        "label / target designs on the 20-pair canonical universe. ADOPT requires "
        "both H2 PASS and the full 8-gate A0-A5 harness."
    )
    lines.append("")
    lines.append(
        "**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / "
        "directional-comparison / classification-quality / feature-importance "
        "columns are diagnostic-only. ADOPT_CANDIDATE routing must not depend on "
        "any single one of them."
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
        "**6. Phase 26 scope (AMENDED).** Phase 26's primary axis is label / target "
        "redesign on the 20-pair canonical universe. Phase 26 is NOT a revival of "
        "Phase 25's feature-axis sweep. F4 / F6 / F5-d / F5-e remain "
        "deferred-not-foreclosed under Phase 25 semantics. A narrow feature-"
        "widening audit (R6-new-A) is authorised under the scope amendment in PR #311 "
        "with a closed allowlist of two features (`atr_at_signal_pip`, "
        "`spread_at_signal_pip`); all other features are out of scope until a "
        "further scope amendment. R6-new-A is a Phase 26 audit of the minimum-"
        "feature-set hypothesis; it is NOT a Phase 25 continuation."
    )
    lines.append("")
    lines.append("## D-1 binding (formal realised-PnL = inherited harness)")
    lines.append("")
    lines.append(
        "Formal realised-PnL scoring uses the inherited "
        "`_compute_realised_barrier_pnl` (bid/ask executable; same harness as "
        "L-2 / L-3 / L-1). Mid-to-mid PnL appears in the sanity probe / label "
        "diagnostic only and is NEVER the formal realised-PnL metric."
    )
    lines.append("")
    lines.append("## Closed feature allowlist (per PR #311 §3 / 26.0d-α §2)")
    lines.append("")
    lines.append(
        f"- ADMITTED: {list(ALL_FEATURES)} "
        f"(pair + direction one-hot; atr_at_signal_pip + spread_at_signal_pip numeric passthrough)"
    )
    lines.append(
        "- NOT ADMITTED: Phase 25 F1/F2/F3/F5 full feature sets; "
        "F4/F6/F5-d/F5-e (Phase 25 deferred-not-foreclosed); multi-TF; "
        "calendar; external-data. (Each excluded class requires a separate "
        "scope amendment.)"
    )
    lines.append("")
    lines.append("## Sanity probe results (per 26.0d-α §12)")
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
    lines.append("- new-feature NaN rate per split:")
    for split_name in ("train", "val", "test"):
        per_feat = sanity.get("new_feature_nan_rate", {}).get(split_name, {})
        for feat in NUMERIC_FEATURES:
            s = per_feat.get(feat, {})
            lines.append(
                f"  - {split_name}.{feat}: {s.get('nan_count', 0)} / {s.get('n', 0)} "
                f"({s.get('nan_rate', float('nan')):.3%})"
            )
    lines.append("- new-feature distribution on TRAIN:")
    for feat in NUMERIC_FEATURES:
        s = sanity.get("new_feature_distribution_train", {}).get(feat, {})
        if "mean" in s:
            lines.append(
                f"  - {feat}: n={s.get('n_finite', 0)} "
                f"mean={s.get('mean', float('nan')):+.3f} "
                f"p5={s.get('p5', float('nan')):+.3f} "
                f"p50={s.get('p50', float('nan')):+.3f} "
                f"p95={s.get('p95', float('nan')):+.3f} "
                f"min={s.get('min', float('nan')):+.3f} "
                f"max={s.get('max', float('nan')):+.3f}"
            )
    lines.append("")
    lines.append("## Row-drop policy (per Decision F; 26.0d-α §5.2)")
    lines.append("")
    for split_name in ("train", "val", "test"):
        ds = drop_stats.get(split_name, {})
        lines.append(
            f"- {split_name}: n_input={ds.get('n_input', 0)} "
            f"n_kept={ds.get('n_kept', 0)} n_dropped={ds.get('n_dropped', 0)}; "
            f"per-feature NaN: {ds.get('per_feature_nan', {})}"
        )
    lines.append("")
    lines.append("## Pre-flight diagnostics")
    lines.append("")
    lines.append(f"- label rows (pre-drop): {preflight_diag['label_rows']}")
    lines.append(f"- horizon_bars (M1): {preflight_diag['horizon_bars']}")
    lines.append(f"- pairs: {preflight_diag['pairs']}")
    lines.append(f"- LightGBM available: {preflight_diag['lightgbm_available']}")
    if preflight_diag.get("lightgbm_version"):
        lines.append(f"- LightGBM version: {preflight_diag['lightgbm_version']}")
    lines.append(f"- formal cells run: {n_cells_run}")
    lines.append("")
    lines.append("## Validation-only cell + quantile selection")
    lines.append("")
    lines.append(
        "Pre-filter: candidates with `val_n_trades >= A0-equivalent`. "
        "Tie-breakers: max val Sharpe → max val ann_pnl → lower val MaxDD → smaller q%."
    )
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

    # Cell results table
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

    # Val-selected cell
    lines.append("## Val-selected (cell*, q*) — FORMAL verdict source")
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
    lines.append("## Aggregate H1 / H2 / H3 / H4 outcome")
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
        "**Note**: 26.0d-β cannot mint ADOPT_CANDIDATE. H2 PASS path resolves to "
        "PROMISING_BUT_NEEDS_OOS pending the separate A0-A5 8-gate harness PR."
    )
    lines.append("")

    # Cross-cell verdict aggregation
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

    # MANDATORY L-1 / L-2 / L-3 vs R6-new-A comparison (per 26.0d-α §13.1)
    lines.append(
        "## MANDATORY: L-1 / L-2 / L-3 vs R6-new-A 4-column comparison (per 26.0d-α §13.1)"
    )
    lines.append("")
    lines.append(
        "L-3 / L-2 / L-1 reference values from PR #303 / #306 / #309. FIXED; do NOT recompute."
    )
    lines.append("")
    if sel is None:
        r6_sharpe = float("nan")
        r6_ann_pnl = float("nan")
        r6_n_trades = 0
        r6_spearman = float("nan")
        r6_sig = "n/a"
        r6_concentration = "n/a"
    else:
        rm = sel.get("test_realised_metrics", {})
        r6_sharpe = rm.get("sharpe", float("nan"))
        r6_ann_pnl = rm.get("annual_pnl", float("nan"))
        r6_n_trades = rm.get("n_trades", 0)
        r6_spearman = sel.get("test_formal_spearman", float("nan"))
        r6_sig = _cell_signature(sel["cell"])
        tc = sel.get("test_concentration", {})
        r6_concentration = f"{tc.get('top_pair', '-')} {tc.get('top_pair_share', 0.0) * 100:.1f}%"
    lines.append("| Aspect | L-3 (PR #303) | L-2 (PR #306) | L-1 (PR #309) | R6-new-A (this PR) |")
    lines.append("|---|---|---|---|---|")
    lines.append(
        "| Label class | continuous regression (spread-embedded) | "
        "continuous regression (mid-to-mid) | ternary classification | "
        "ternary classification (inherited from L-1) |"
    )
    lines.append(
        "| Feature set | pair + direction | pair + direction | pair + direction | "
        "pair + direction + atr_at_signal_pip + spread_at_signal_pip |"
    )
    lines.append(
        f"| Val-selected cell signature | atr_normalised / Linear / q*=5% | "
        f"atr_normalised / Linear / q*=5% | C01 P(TP) / q*=5% | "
        f"{r6_sig} / q*={sel.get('selected_q_percent') if sel else '-'} |"
    )
    lines.append(
        f"| Val-selected test realised Sharpe | -0.2232 | -0.2232 | -0.2232 | {r6_sharpe:.4f} |"
    )
    lines.append(
        f"| Val-selected test ann_pnl (pip) | -237310.8 | -237310.8 | -237310.8 | "
        f"{r6_ann_pnl:+.1f} |"
    )
    lines.append(f"| Val-selected test n_trades | 42150 | 42150 | 42150 | {r6_n_trades} |")
    lines.append(
        f"| Test Spearman (formal H1) | -0.1419 | -0.1139 | -0.0505 (C01) / -0.1077 (C02) | "
        f"{r6_spearman:.4f} |"
    )
    lines.append(
        f"| Pair concentration on test | 100% USD_JPY | 100% USD_JPY | 100% USD_JPY | "
        f"{r6_concentration} |"
    )
    lines.append(
        f"| Verdict | REJECT_NON_DISCRIMINATIVE | REJECT_NON_DISCRIMINATIVE | "
        f"REJECT_NON_DISCRIMINATIVE | {verdict_info.get('verdict', '-')} |"
    )
    lines.append("")

    # MANDATORY YES / NO / PARTIAL paragraph (per 26.0d-α §13.2-§13.4)
    lines.append(
        "## MANDATORY: Identity-break YES / NO / PARTIAL paragraph (per 26.0d-α §13.2-§13.4)"
    )
    lines.append("")
    ib = identity_break
    lines.append(
        f"**Did the closed two-feature allowlist (`atr_at_signal_pip`, "
        f"`spread_at_signal_pip`) change the val-selected trade set away from "
        f"the L-1 / L-2 / L-3 identity outcome (n_trades=42,150 ; Sharpe=-0.2232 ; "
        f"ann_pnl=-237,310.8 ; 100% USD_JPY)? **{ib.get('verdict', 'unknown')}**.**"
    )
    lines.append("")
    lines.append(
        f"- n_trades observed: {ib.get('n_trades_observed', 0)} (baseline 42,150 ; "
        f"delta {ib.get('n_trades_delta', 0):+d})"
    )
    lines.append(
        f"- Sharpe observed: {ib.get('sharpe_observed', float('nan')):.4f} "
        f"(baseline -0.2232 ; delta {ib.get('sharpe_delta', float('nan')):+.4f})"
    )
    lines.append(
        f"- ann_pnl observed: {ib.get('ann_pnl_observed', float('nan')):+.1f} "
        f"(baseline -237,310.8 ; delta {ib.get('ann_pnl_delta', float('nan')):+.1f})"
    )
    lines.append(
        f"- top pair observed: {ib.get('top_pair_observed')} share "
        f"{ib.get('top_pair_share_observed', float('nan')):.3f} "
        f"(baseline USD_JPY 1.000 ; delta {ib.get('top_pair_share_delta', float('nan')):+.3f})"
    )
    lines.append("")
    lines.append(f"**Interpretation**: {ib.get('reason', '-')}")
    lines.append("")

    # Pair concentration (diagnostic-only)
    lines.append("## Pair concentration per cell (DIAGNOSTIC-ONLY; per 26.0c-α §9.2)")
    lines.append("")
    lines.append(
        f"CONCENTRATION_HIGH fires when val top-pair share >= "
        f"{CONCENTRATION_HIGH_THRESHOLD}. NOT consulted by "
        "`select_cell_validation_only` or `assign_verdict`."
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

    # Classification diagnostics
    lines.append("## Classification-quality diagnostics (DIAGNOSTIC-ONLY)")
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

    # NEW: Feature importance (DIAGNOSTIC-ONLY; 4-bucket aggregation)
    lines.append("## Feature importance (DIAGNOSTIC-ONLY; per 26.0d-α §11.4 / Decision D10)")
    lines.append("")
    lines.append(
        "LightGBM gain importance aggregated into 4 buckets (`pair_*` one-hots → "
        "`pair`; `direction_*` one-hots → `direction`; `atr_at_signal_pip` and "
        "`spread_at_signal_pip` individually). DIAGNOSTIC-ONLY; NOT used in formal "
        "verdict routing."
    )
    lines.append("")
    lines.append(
        "| cell | picker | pair (gain) | direction (gain) | atr_at_signal_pip (gain) | "
        "spread_at_signal_pip (gain) | pair (%) | direction (%) | atr (%) | spread (%) |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        fi = c.get("feature_importance", {})
        b = fi.get("buckets", {})
        bn = fi.get("buckets_normalised", {})
        lines.append(
            f"| {cell['id']} | {cell['picker']} | "
            f"{b.get('pair', float('nan')):.1f} | "
            f"{b.get('direction', float('nan')):.1f} | "
            f"{b.get('atr_at_signal_pip', float('nan')):.1f} | "
            f"{b.get('spread_at_signal_pip', float('nan')):.1f} | "
            f"{bn.get('pair', float('nan')):.3f} | "
            f"{bn.get('direction', float('nan')):.3f} | "
            f"{bn.get('atr_at_signal_pip', float('nan')):.3f} | "
            f"{bn.get('spread_at_signal_pip', float('nan')):.3f} |"
        )
    lines.append("")

    # Absolute thresholds
    lines.append("## Diagnostic absolute-probability thresholds (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append(
        f"P(TP) candidates: {ABSOLUTE_THRESHOLDS_PTP}. P(TP)-P(SL) candidates: "
        f"{ABSOLUTE_THRESHOLDS_DIFF}. NOT used in formal verdict routing."
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

    # Isotonic appendix
    lines.append("## Isotonic-calibration appendix — OMITTED per 26.0c-α §4.3 (preserved)")
    lines.append("")
    lines.append(
        "Fitting isotonic on val AND using the same val to select the quantile "
        "cutoff introduces selection-overfit risk. `compute_isotonic_diagnostic_"
        "appendix` stub raises `NotImplementedError`. Deferred to later sub-phase."
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
        help="Run sanity probe and exit (no full sweep). Per D1.",
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Dry-run: skip writing artifacts. Per D9.",
    )
    parser.add_argument(
        "--quick-mode",
        action="store_true",
        help="500 rows × 20 pairs subsample for smoke. Per D6.",
    )
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 26.0d-beta R6-new-A feature-widening audit ({len(args.pairs)} pairs) ===")
    print(
        f"K_FAV={K_FAV} K_ADV={K_ADV} H_M1={H_M1_BARS} | "
        f"H1-weak>{H1_WEAK_THRESHOLD} H1-meaningful>={H1_MEANINGFUL_THRESHOLD} | "
        f"H3 ref={H3_REFERENCE_SHARPE} | quantile candidates={THRESHOLDS_QUANTILE_PERCENTS}"
    )
    print(f"Closed feature allowlist: {list(ALL_FEATURES)}")

    # 1. Load labels
    print("Loading 25.0a-beta path-quality labels...")
    raw_label_path = REPO_ROOT / "artifacts" / "stage25_0a" / "path_quality_dataset.parquet"
    raw_labels = pd.read_parquet(raw_label_path)
    if args.pairs != PAIRS_20:
        raw_labels = raw_labels[raw_labels["pair"].isin(args.pairs)]
    print(f"  labels rows (pre-drop): {len(raw_labels)}")

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
        print("LightGBM is REQUIRED for R6-new-A multiclass eval; halting.")
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

    # 5. SANITY PROBE (HALTS on failure; per Decision D1)
    sanity = run_sanity_probe_r6_new_a(train_df, val_df, test_df, pair_runtime_map, args.pairs)

    if args.sanity_probe_only:
        print("\n--sanity-probe-only set; exiting after probe.")
        if not args.no_write:
            (args.out_dir / "sanity_probe.json").write_text(
                json.dumps(sanity, indent=2, default=str), encoding="utf-8"
            )
            print(f"sanity probe results: {args.out_dir / 'sanity_probe.json'}")
        return 0

    # 6. Row-drop for new-feature missingness (per Decision F)
    print("Dropping rows with missing/non-finite new features...")
    train_df, train_drop = drop_rows_with_missing_new_features(train_df)
    val_df, val_drop = drop_rows_with_missing_new_features(val_df)
    test_df, test_drop = drop_rows_with_missing_new_features(test_df)
    drop_stats = {"train": train_drop, "val": val_drop, "test": test_drop}
    for name, ds in drop_stats.items():
        print(
            f"  {name}: n_input={ds['n_input']} n_kept={ds['n_kept']} "
            f"n_dropped={ds['n_dropped']} per_feature_nan={ds['per_feature_nan']}"
        )

    # 7. PRECOMPUTE realised PnL per row (cell-independent; inherited harness)
    print("Precomputing realised PnL per row via inherited harness...")
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

    # 8. Build labels
    print("Building L-1 ternary labels...")
    train_label = build_l1_labels_for_dataframe(train_df).to_numpy()
    val_label = build_l1_labels_for_dataframe(val_df).to_numpy()
    test_label = build_l1_labels_for_dataframe(test_df).to_numpy()

    # 9. Fit ONCE multiclass LightGBM with WIDENED feature set
    print("Fitting multiclass LightGBM with widened 4-feature allowlist...")
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
    print(f"  multiclass LGBM fit + predict_proba: ({time.time() - t0:.1f}s)")
    print(f"  val_probs shape={val_probs.shape}; test_probs shape={test_probs.shape}")
    print(
        f"  feature importance (4-bucket; gain): "
        f"pair={feature_importance_diag['buckets'].get('pair', float('nan')):.1f}, "
        f"direction={feature_importance_diag['buckets'].get('direction', float('nan')):.1f}, "
        f"atr={feature_importance_diag['buckets'].get('atr_at_signal_pip', float('nan')):.1f}, "
        f"spread={feature_importance_diag['buckets'].get('spread_at_signal_pip', float('nan')):.1f}"
    )

    # 10. Per-cell evaluation
    cells = build_cells()
    n_cells_run = len(cells)
    cell_results: list[dict] = []
    for i, cell in enumerate(cells):
        t_cell = time.time()
        try:
            result = evaluate_cell_r6_new_a(
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

    # 11. Validation-only cell selection + verdict + cross-cell + identity-break
    val_select = select_cell_validation_only(cell_results)
    verdict_info = assign_verdict(val_select.get("selected"))
    aggregate_info = aggregate_cross_cell_verdict(cell_results)
    identity_break = detect_identity_break(val_select.get("selected"))

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
    print(f"=== Identity-break: {identity_break['verdict']} ===")
    print(f"    reason: {identity_break['reason']}")

    if args.no_write:
        print("\n--no-write set; skipping artifact write.")
        return 0

    # 12. Write report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report_r6_new_a(
        report_path,
        cell_results,
        val_select,
        verdict_info,
        aggregate_info,
        identity_break,
        sanity,
        drop_stats,
        (t_min, t70, t85, t_max),
        preflight_diag,
        n_cells_run,
    )
    print(f"\nReport: {report_path}")

    # 13. Persist artifacts (gitignored)
    summary_rows: list[dict] = []
    for c in cell_results:
        cell = c["cell"]
        rm = c.get("test_realised_metrics", {})
        sp = c.get("test_formal_spearman", float("nan"))
        ab = c.get("absolute_best", {})
        cd = c.get("test_classification_diag", {})
        fi = c.get("feature_importance", {}).get("buckets", {})
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
                "fi_pair": fi.get("pair", float("nan")),
                "fi_direction": fi.get("direction", float("nan")),
                "fi_atr_at_signal_pip": fi.get("atr_at_signal_pip", float("nan")),
                "fi_spread_at_signal_pip": fi.get("spread_at_signal_pip", float("nan")),
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
    aggregate["identity_break"] = identity_break
    aggregate["n_cells_run"] = n_cells_run
    aggregate["feature_allowlist"] = list(ALL_FEATURES)
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
            "feature_importance": val_select["selected"].get("feature_importance", {}),
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
