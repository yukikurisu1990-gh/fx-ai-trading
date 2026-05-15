"""Stage 27.0f-β S-E + R7-C Regime/Context Feature eval (fifth Phase 27 sub-phase).

Implements PR #331 (Phase 27.0f-α design memo) under PR #330 (R7-C scope
amendment) + PR #323 (S-E scope amendment) + PR #316 (Phase 27 kickoff).

Selected via R-C route from post-27.0e routing review PR #329. Targets
H-B6 (top-tail adversarial selection / regime confound in regressor
confidence) directly + H-B2 (R7-A too narrow) implicitly.

R7-A FIXED subset:
  pair + direction + atr_at_signal_pip + spread_at_signal_pip
R7-C ADDITIVE closed allowlist (per PR #330 §3.1):
  f5a_spread_z_50 + f5b_volume_z_50 + f5c_high_spread_low_vol_50
R7-A + R7-C = 7 features total.

R7-C construction (per 27.0f-α §3 / Phase 25.0f-α §2.4 / §2.5 / §2.6):
  - shift(1) BEFORE rolling (CAUSAL; non-negotiable; NG#11 violation if reversed)
  - lookback 50; min_periods 50
  - dedup to (pair, signal_ts) for spread; broadcast back to direction axis
  - M5-aggregated volume from M1 BA (right-closed / right-labeled)
  - illiquid-stress flag = (f5a > 1.0) AND (f5b < -1.0)

Volume pre-flight (per 27.0f-α §4.1; D-Z3.a) HALTs with R7CPreflightError on:
  - volume column missing in ≥ 1 row
  - non-null fraction < 0.99 per pair
  - M1 → M5 aggregation not strictly non-decreasing
  - volume < 0

R7-C feature NaN row-drop policy (per 27.0f-α §4.2 / §4.3 / D-Z3.b / D-Z3.c):
  - drop rows with NaN in any R7-C feature
  - HALT if split-level drop > 1% (SanityProbeError)

Cell structure (per 27.0f-α §6.1 / D-Z5; 3 cells; D10 amended 3-artifact form):
  - C-se-rcw: S-E on R7-A + R7-C (substantive; tests H-B6 + H-B2)
  - C-se-r7a-replica: S-E on R7-A only (within-eval ablation control;
    DIAGNOSTIC-ONLY drift WARN vs 27.0d C-se; NOT HALT)
  - C-sb-baseline: raw P(TP) - P(SL) on multiclass head (inheritance
    chain; FAIL-FAST HALT on mismatch)

3 cells × 5 quantiles = 15 (cell, q) pairs. Quantile family = {5, 10,
20, 30, 40} for ALL cells (per 27.0f-α §5 / D-Z4; NOT 27.0e trimmed —
clean Channel A isolation).

D10 amendment 3-artifact form (per 27.0f-α §6.2):
  - one LightGBMRegressor + Huber on R7-A + R7-C
  - one LightGBMRegressor + Huber on R7-A only
  - one LightGBM multiclass head on R7-A only
Each fit ONCE on full train; no per-cell re-fit.

H-B6 falsification criteria (per 27.0f-α §7 / D-Z7; binding 4-row outcome
table; row precedence 1 > 2 > 3 > 4):
  Row 1 STRONG_SUPPORT: C-se-rcw H2 PASS at some q → PROMISING_BUT_NEEDS_OOS
  Row 2 PARTIAL_SUPPORT: C-se-rcw H1m PASS AND max-q delta-Sharpe vs
        C-se-r7a-replica > 0.05 → route R-T1 / R-B
  Row 3 FALSIFIED_R7C_INSUFFICIENT: C-se-rcw H1m PASS AND max-q
        abs delta-Sharpe ≤ 0.05 → route R-B / R-T1 / R-T3 / R-E
  Row 4 PARTIALLY_FALSIFIED_NEW_QUESTION: C-se-rcw H1-weak FAIL → route R-T1 / R-E

Secondary discriminator (per D-Z7 / D-AA7): C-se-rcw vs C-se-r7a-replica
delta-Sharpe at matched q (per-q + max-q).

Top-tail regime audit (per 27.0f-α §10 item 19 / D-AA9; DIAGNOSTIC-ONLY):
For q ∈ {10, 20}, report mean f5a / mean f5b / f5c activation rate in
C-se-rcw top-q val rows vs population means → H-B6 mechanism diagnosis.

C-se-r7a-replica drift check (per 27.0f-α §6.1 / D-Z6 / D-AA10 / D-AA11):
Compares C-se-r7a-replica val-selected metrics vs 27.0d C-se. DIAGNOSTIC-
ONLY WARN; NOT HALT. Tolerances: n_trades ±100, Sharpe ±5e-3, ann_pnl
±0.5% of magnitude.

C-sb-baseline match (inherited from 27.0c §7.3 / 27.0d / 27.0e):
  n_trades=34,626 (exact); Sharpe=-0.1732 (±1e-4); ann_pnl=-204,664.4
  (±0.5 pip). HALT with BaselineMismatchError FAIL-FAST before H-B6
  outcome computation.

D-1 BINDING: formal realised PnL + S-E regression target = inherited
_compute_realised_barrier_pnl (bid/ask executable).

MANDATORY CLAUSES (1-5 verbatim; clause 6 = PR #330 §6 verbatim — the
canonical R7-C-updated wording):

1. Phase framing. ADOPT requires H2 PASS + full 8-gate A0-A5 harness.
2. Diagnostic columns prohibition. Calibration / threshold-sweep /
   directional-comparison / classification-quality / feature-importance /
   per-pair-Sharpe-contribution columns are diagnostic-only.
   27.0c extension: conditional-PnL estimator constants + calibration
   reliability diagrams are diagnostic-only. 27.0d extension: regressor
   feature importance, predicted-vs-realised correlation, R², MAE,
   predicted-PnL distribution are diagnostic-only. 27.0e extension:
   quantile-family disclosure + trade-count budget audit are
   diagnostic-only. 27.0f extension: R7-C feature distribution +
   per-pair R7-C stats + top-tail regime audit + C-se-r7a-replica
   drift are diagnostic-only.
3. γ closure preservation. PR #279 is unmodified.
4. Production-readiness preservation. X-v2 OOS gating remains required.
   v9 20-pair (Phase 9.12 tip 79ed1e8) untouched. Phase 22 frozen-OOS
   contract preserved.
5. NG#10 / NG#11 not relaxed.
6. Phase 27 scope. Phase 27's primary axes are (a) feature widening
   beyond the Phase 26 R6-new-A 2-feature allowlist via per-family
   closed allowlists and (b) score-objective redesign beyond P(TP) /
   P(TP)-P(SL). Phase 27 is NOT a Phase 25 feature-axis sweep revival.
   R7-A (inherited from PR #311) is admissible at kickoff. R7-C (Phase
   25 F5 regime/context closed allowlist) was promoted from "requires
   SEPARATE Phase 27 scope-amendment PR" to "admissible at 27.0f-α
   design memo" via Phase 27 R7-C scope-amendment PR #330. The R7-C
   closed allowlist is [f5a_spread_z_50, f5b_volume_z_50,
   f5c_high_spread_low_vol_50] (3 features; additive to R7-A; constructed
   per Phase 25.0f-α §2.4 / §2.5 / §2.6 causal rules; pre-flight HALT
   if M1 volume missing/corrupt). R7-B remains admissible only after
   its own separate scope amendment. R7-D and R7-Other remain NOT
   admissible. Score-objectives S-A / S-B / S-C are admissible at
   kickoff for formal evaluation. S-D was promoted from
   admissible-but-deferred to formal at 27.0c-β via PR #320. S-E was
   promoted from "requires scope amendment" to "admissible at 27.0d-α
   design memo" via PR #323; on PR #324 merge S-E became formal at
   27.0d-β. 27.0e R-T2 trimmed-quantile policy admissible under existing
   clause 6 + clause 2 (per PR #327 §0.1); on PR #327 merge became
   formal at 27.0e-β. S-Other NOT admissible. Phase 26 deferred-not-
   foreclosed items NOT subsumed.

PRODUCTION-MISUSE GUARDS (inherited verbatim):
GUARD 1 — research-not-production: 27.0f features stay in scripts/.
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

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage27_0f"
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

# Inherited constants
PAIRS_20 = stage23_0a.PAIRS_20
load_m1_ba = stage23_0a.load_m1_ba
pip_size_for = stage23_0a.pip_size_for
TF_MINUTES = stage23_0a.TF_MINUTES

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
# Binding constants
# ---------------------------------------------------------------------------

# Barrier geometry (inherited)
K_FAV = stage25_0b.K_FAV
K_ADV = stage25_0b.K_ADV
H_M1_BARS = stage25_0b.H_M1_BARS

# L-1 class encoding (inherited; preserved for sanity probe / C-sb-baseline only)
LABEL_TP = stage26_0c.LABEL_TP
LABEL_SL = stage26_0c.LABEL_SL
LABEL_TIME = stage26_0c.LABEL_TIME
NUM_CLASSES = stage26_0c.NUM_CLASSES

# R7-A feature family (FIXED; inherited)
NUMERIC_FEATURES_R7A = stage26_0d.NUMERIC_FEATURES
ALL_FEATURES_R7A = stage26_0d.ALL_FEATURES  # 4 features: pair + direction + atr + spread
CATEGORICAL_COLS = stage26_0d.CATEGORICAL_COLS

# Regression config (inherited from 27.0d)
LIGHTGBM_REGRESSION_CONFIG = stage27_0d.LIGHTGBM_REGRESSION_CONFIG
HUBER_ALPHA = stage27_0d.HUBER_ALPHA
LIGHTGBM_MULTICLASS_CONFIG = stage27_0d.LIGHTGBM_MULTICLASS_CONFIG

# H1/H2/H3/H4 thresholds (inherited)
H1_WEAK_THRESHOLD = stage26_0c.H1_WEAK_THRESHOLD
H1_MEANINGFUL_THRESHOLD = stage26_0c.H1_MEANINGFUL_THRESHOLD
H3_REFERENCE_SHARPE = stage26_0c.H3_REFERENCE_SHARPE
A1_MIN_SHARPE = stage25_0b.A1_MIN_SHARPE
A2_MIN_ANNUAL_PNL = stage25_0b.A2_MIN_ANNUAL_PNL

# Diagnostic / sanity probe thresholds (inherited)
CONCENTRATION_HIGH_THRESHOLD = stage26_0c.CONCENTRATION_HIGH_THRESHOLD
SANITY_MIN_CLASS_SHARE = stage26_0c.SANITY_MIN_CLASS_SHARE
SANITY_MAX_PER_PAIR_TIME_SHARE = stage26_0c.SANITY_MAX_PER_PAIR_TIME_SHARE
SANITY_MAX_NEW_FEATURE_NAN_RATE = stage26_0d.SANITY_MAX_NEW_FEATURE_NAN_RATE
SANITY_MAX_POSITIVITY_VIOLATION_RATE = stage26_0d.SANITY_MAX_POSITIVITY_VIOLATION_RATE

# Span budgets
TEST_SPAN_YEARS = SPAN_YEARS * (1.0 - TRAIN_FRAC - VAL_FRAC)
VAL_SPAN_YEARS = SPAN_YEARS * VAL_FRAC

# OOF protocol (DIAGNOSTIC-ONLY; reused)
OOF_N_FOLDS = stage27_0c.OOF_N_FOLDS
OOF_SEED = stage27_0c.OOF_SEED

# Baseline reference values (inherited verbatim)
BASELINE_27_0B_C_ALPHA0_N_TRADES = stage27_0d.BASELINE_27_0B_C_ALPHA0_N_TRADES
BASELINE_27_0B_C_ALPHA0_SHARPE = stage27_0d.BASELINE_27_0B_C_ALPHA0_SHARPE
BASELINE_27_0B_C_ALPHA0_ANN_PNL = stage27_0d.BASELINE_27_0B_C_ALPHA0_ANN_PNL
BASELINE_MATCH_N_TRADES_TOLERANCE = stage27_0d.BASELINE_MATCH_N_TRADES_TOLERANCE
BASELINE_MATCH_SHARPE_ABS_TOLERANCE = stage27_0d.BASELINE_MATCH_SHARPE_ABS_TOLERANCE
BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE = stage27_0d.BASELINE_MATCH_ANN_PNL_ABS_TOLERANCE

# NaN-PnL train-row HALT threshold (inherited)
NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD = stage27_0d.NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD


# ---------------------------------------------------------------------------
# NEW Phase 27.0f constants
# ---------------------------------------------------------------------------

# R7-C closed allowlist (per PR #330 §3.1 / 27.0f-α §3)
R7_C_FEATURES = ("f5a_spread_z_50", "f5b_volume_z_50", "f5c_high_spread_low_vol_50")
ALL_FEATURES_R7AC = tuple(list(ALL_FEATURES_R7A) + list(R7_C_FEATURES))  # 7 features total

# R7-C construction parameters (per 27.0f-α §3 / Phase 25.0f-α §2)
R7_C_ROLLING_WINDOW = 50
R7_C_HIGH_SPREAD_THRESHOLD = 1.0  # z-score threshold for f5c
R7_C_LOW_VOLUME_THRESHOLD = -1.0  # z-score threshold for f5c
R7_C_TF = "M5"

# R7-C row-drop HALT threshold (per 27.0f-α §4.3 / D-Z3.c / D-AA3)
R7_C_ROW_DROP_HALT_FRAC = 0.01  # 1% of split rows

# Volume pre-flight thresholds (per Phase 25.0f-α §2.5.1 / D-AA12)
VOLUME_PREFLIGHT_NON_NULL_FRAC = 0.99

# Per-cell quantile family (per 27.0f-α §5 / D-Z4)
QUANTILE_PERCENTS_27_0F: tuple[float, ...] = (5.0, 10.0, 20.0, 30.0, 40.0)

# Quantile family for C-sb-baseline (inherited from 27.0e)
C_SB_BASELINE_QUANTILE_PERCENTS = stage27_0e.C_SB_BASELINE_QUANTILE_PERCENTS

# H-B6 falsification thresholds (per 27.0f-α §7 / D-Z7 / D-AA7)
H_B6_DELTA_SHARPE_PARTIAL_SUPPORT = 0.05  # row 2 vs row 3 cutoff
H_B6_OUTCOME_STRONG_SUPPORT = "STRONG_SUPPORT"
H_B6_OUTCOME_PARTIAL_SUPPORT = "PARTIAL_SUPPORT"
H_B6_OUTCOME_FALSIFIED_R7C_INSUFFICIENT = "FALSIFIED_R7C_INSUFFICIENT"
H_B6_OUTCOME_PARTIALLY_FALSIFIED_NEW_QUESTION = "PARTIALLY_FALSIFIED_NEW_QUESTION"
H_B6_OUTCOME_NEEDS_REVIEW = "NEEDS_REVIEW"

# Top-tail regime audit q values (per 27.0f-α §10 item 19 / D-AA9)
TOP_TAIL_AUDIT_Q_PERCENTS: tuple[float, ...] = (10.0, 20.0)

# C-se-r7a-replica drift tolerances (per 27.0f-α §6.1 / D-AA10; WARN-only)
R7A_REPLICA_DRIFT_N_TRADES_TOLERANCE = 100  # ±100 vs 27.0d n=184,703 (~0.05%)
R7A_REPLICA_DRIFT_SHARPE_TOLERANCE = 5e-3
R7A_REPLICA_DRIFT_ANN_PNL_FRAC_TOLERANCE = 0.005  # ±0.5% of magnitude

# Trade-count budget audit threshold (inherited from 27.0e)
VAL_BASELINE_N_TRADES_AT_Q5 = stage27_0e.VAL_BASELINE_N_TRADES_AT_Q5
TRADE_COUNT_INFLATION_WARN_THRESHOLD = stage27_0e.TRADE_COUNT_INFLATION_WARN_THRESHOLD


# ---------------------------------------------------------------------------
# NEW exceptions
# ---------------------------------------------------------------------------


class R7CPreflightError(RuntimeError):
    """Raised when M1 BA volume pre-flight fails (per 27.0f-α §4.1 / D-Z3.a).

    Failure modes:
      - volume column missing in ≥ 1 row
      - non-null fraction < 0.99 per pair across eval span
      - M1 → M5 aggregation produces non-monotonic index
      - volume values < 0
    """


class BaselineMismatchError(RuntimeError):
    """Raised when C-sb-baseline fails to reproduce 27.0b C-alpha0 baseline.

    Per 27.0f-α §7.3 inheritance from 27.0c-α §7.3 / 27.0d / 27.0e.
    Tolerances inherited verbatim.
    """


# ---------------------------------------------------------------------------
# Volume series loader (per 27.0f-α §3.2 / D-Z1 / D-AA1)
# ---------------------------------------------------------------------------


def load_m1_volume_series(pair: str, days: int = SPAN_DAYS) -> pd.Series:
    """Load M1 volume series from existing M1 BA jsonl file.

    Returns a pd.Series indexed by UTC timestamp with int volume values.
    No new data extension required (per PR #330 §2 + 27.0f-α §3.2 inheritance);
    the volume column already exists in the M1 BA jsonl files.
    """
    path = DATA_DIR / f"candles_{pair}_M1_{days}d_BA.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[tuple] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            raw = json.loads(line)
            rows.append((stage23_0a._parse_oanda_ts(raw["time"]), int(raw["volume"])))
    if not rows:
        raise R7CPreflightError(f"no rows loaded from {path}")
    ts, vol = zip(*rows, strict=True)
    series = pd.Series(list(vol), index=pd.DatetimeIndex(ts, tz=UTC), name="volume")
    series = series[~series.index.duplicated(keep="first")].sort_index()
    return series


def aggregate_m1_volume_to_m5(volume_series: pd.Series) -> pd.Series:
    """M1 → M5 aggregation, right-closed / right-labeled (matches stage23_0a).

    Per 27.0f-α §3.2 / Phase 25.0f-α §2.5 / D-AA1.
    """
    minutes = TF_MINUTES[R7_C_TF]
    rule = f"{minutes}min"
    agg = volume_series.resample(rule, label="right", closed="right").sum()
    return agg.dropna()


# ---------------------------------------------------------------------------
# Volume pre-flight (per 27.0f-α §4.1 / D-Z3.a / D-AA12)
# ---------------------------------------------------------------------------


def verify_volume_preflight(pairs: list[str], days: int = SPAN_DAYS) -> dict:
    """HALT with R7CPreflightError on failure (per 27.0f-α §4.1).

    Checks per Phase 25.0f-α §2.5.1:
      - volume column present in every loaded row (load_m1_volume_series
        will raise R7CPreflightError if rows are empty / file missing)
      - non-null fraction ≥ 0.99 per pair (NaN check on int64 → no NaN
        possible; we check len > 0 and non-null after the load)
      - M1 → M5 aggregation produces strictly non-decreasing index
      - volume values non-negative
    """
    print(f"=== R7-C volume pre-flight (per 27.0f-α §4.1) on {len(pairs)} pairs ===")
    out: dict = {"per_pair": {}, "status": "PENDING"}
    failures: list[str] = []
    for pair in pairs:
        per_pair: dict = {}
        try:
            vol = load_m1_volume_series(pair, days=days)
        except (FileNotFoundError, R7CPreflightError) as exc:
            per_pair["error"] = repr(exc)
            failures.append(f"{pair}: load failed: {exc!r}")
            out["per_pair"][pair] = per_pair
            continue
        n_total = int(len(vol))
        n_finite = int(vol.notna().sum())
        non_null_frac = n_finite / n_total if n_total > 0 else 0.0
        per_pair["m1_rows"] = n_total
        per_pair["non_null_frac"] = float(non_null_frac)
        per_pair["min_volume"] = int(vol.min()) if n_total > 0 else None
        if non_null_frac < VOLUME_PREFLIGHT_NON_NULL_FRAC:
            failures.append(
                f"{pair}: non_null_frac={non_null_frac:.4f} < "
                f"{VOLUME_PREFLIGHT_NON_NULL_FRAC} (Phase 25.0f-α §2.5.1)"
            )
        if per_pair["min_volume"] is not None and per_pair["min_volume"] < 0:
            failures.append(f"{pair}: min_volume={per_pair['min_volume']} < 0")
        # M5 aggregation index monotonicity
        m5_vol = aggregate_m1_volume_to_m5(vol)
        is_monotonic = bool(m5_vol.index.is_monotonic_increasing)
        per_pair["m5_rows"] = int(len(m5_vol))
        per_pair["m5_index_monotonic"] = is_monotonic
        if not is_monotonic:
            failures.append(f"{pair}: M5 aggregation index not strictly non-decreasing")
        out["per_pair"][pair] = per_pair
        print(
            f"  {pair}: m1_rows={n_total} non_null_frac={non_null_frac:.4f} "
            f"min_vol={per_pair['min_volume']} m5_rows={len(m5_vol)} "
            f"monotonic={is_monotonic}"
        )
    if failures:
        out["status"] = "FAIL"
        out["failures"] = failures
        raise R7CPreflightError(
            f"Volume pre-flight failed for {len(failures)} pair(s): " + "; ".join(failures[:5])
        )
    out["status"] = "PASS"
    print("=== Volume pre-flight: PASS ===\n")
    return out


# ---------------------------------------------------------------------------
# R7-C feature builder (per 27.0f-α §3 / D-Z1 / D-Z2 / D-AA1)
# ---------------------------------------------------------------------------


def _build_pair_spread_z(spread_series: pd.Series, window: int = R7_C_ROLLING_WINDOW) -> pd.Series:
    """Per-pair: shift(1) BEFORE rolling; z-score over rolling window.

    Per 27.0f-α §3.1 (CAUSAL; non-negotiable).

    Returns pd.Series indexed by signal_ts with NaN where rolling_std is
    0 or NaN.
    """
    causal = spread_series.shift(1)
    rolling = causal.rolling(window=window, min_periods=window)
    mean = rolling.mean()
    std = rolling.std()
    # NaN where std is 0 or NaN
    z = (spread_series - mean) / std
    z = z.where(std > 0)
    return z


def _build_pair_volume_z(
    pair: str,
    signal_ts_series: pd.Series,
    days: int = SPAN_DAYS,
    window: int = R7_C_ROLLING_WINDOW,
) -> pd.Series:
    """Per-pair: M1 volume → M5 aggregate → shift(1) → rolling z-score.

    Per 27.0f-α §3.2 (CAUSAL; non-negotiable).

    Returns pd.Series indexed by signal_ts (looked up from M5 z-score
    series via merge_asof on signal_ts).
    """
    m1_vol = load_m1_volume_series(pair, days=days)
    m5_vol = aggregate_m1_volume_to_m5(m1_vol)
    causal_vol = m5_vol.shift(1)
    rolling = causal_vol.rolling(window=window, min_periods=window)
    mean = rolling.mean()
    std = rolling.std()
    z = (m5_vol - mean) / std
    z = z.where(std > 0)
    z = z.rename("f5b_volume_z_50")
    z_df = z.reset_index().rename(columns={"index": "m5_ts"})
    z_df.columns = ["m5_ts", "f5b_volume_z_50"]
    # Look up per signal_ts via merge_asof (signal_ts ≤ m5_ts; backward;
    # since M5 right-label matches the bar end, signal_ts at bar end IS
    # the M5 timestamp).
    # Align tz dtype: path_quality_dataset signal_ts is naive datetime64[us];
    # M5 index from load_m1_volume_series is UTC-aware. Strip tz from M5
    # index for the merge (both naive UTC-equivalent).
    signal_df = pd.DataFrame({"signal_ts": signal_ts_series})
    if pd.api.types.is_datetime64tz_dtype(signal_df["signal_ts"]):
        signal_df["signal_ts"] = signal_df["signal_ts"].dt.tz_convert(None)
    signal_df = signal_df.sort_values("signal_ts").reset_index(drop=False)
    if pd.api.types.is_datetime64tz_dtype(z_df["m5_ts"]):
        z_df["m5_ts"] = z_df["m5_ts"].dt.tz_convert(None)
    z_df = z_df.sort_values("m5_ts").reset_index(drop=True)
    merged = pd.merge_asof(
        signal_df,
        z_df,
        left_on="signal_ts",
        right_on="m5_ts",
        direction="backward",
    )
    merged = merged.set_index("index").sort_index()
    return merged["f5b_volume_z_50"]


def build_r7_c_features(df: pd.DataFrame, days: int = SPAN_DAYS) -> pd.DataFrame:
    """Add 3 R7-C features to df; causal shift(1) BEFORE rolling.

    Per 27.0f-α §3.1 / §3.2 / §3.3 / D-AA1 / D-AA2:
      - per-pair groupby
      - dedup to (pair, signal_ts) for spread (drop direction axis;
        spread is direction-independent)
      - shift(1) BEFORE rolling for both spread + volume
      - re-attach to direction axis via broadcast

    Returns a copy of df with 3 NEW columns added:
      f5a_spread_z_50, f5b_volume_z_50, f5c_high_spread_low_vol_50
    """
    out = df.copy()
    n = len(out)
    f5a = np.full(n, np.nan, dtype=np.float64)
    f5b = np.full(n, np.nan, dtype=np.float64)
    pairs = out["pair"].to_numpy()
    signal_ts = out["signal_ts"]
    spread = out["spread_at_signal_pip"].astype(np.float64).to_numpy()

    for pair in sorted(set(pairs)):
        mask = pairs == pair
        if not mask.any():
            continue
        # Dedup to (pair, signal_ts) for spread (direction-independent)
        pair_indices = np.flatnonzero(mask)
        pair_spread = pd.Series(
            spread[pair_indices],
            index=signal_ts.iloc[pair_indices].values,
            name="spread",
        )
        # Sort by signal_ts (and deduplicate by keeping first)
        pair_spread_sorted = pair_spread.sort_index()
        pair_spread_dedup = pair_spread_sorted[~pair_spread_sorted.index.duplicated(keep="first")]
        # Compute z-score on deduped series (causal)
        z_spread = _build_pair_spread_z(pair_spread_dedup, window=R7_C_ROLLING_WINDOW)
        # Broadcast back via merge_asof on signal_ts. Manual dict lookup
        # would fail because pair_spread.index was constructed via .values
        # (drops tz info), but signal_ts.iloc[i] returns a tz-aware Timestamp;
        # the two hash differently. merge_asof aligns tz dtypes safely.
        z_spread_df = pd.DataFrame(
            {
                "signal_ts": pd.Series(z_spread.index),
                "f5a_spread_z_50": z_spread.values,
            }
        )
        if pd.api.types.is_datetime64tz_dtype(z_spread_df["signal_ts"]):
            z_spread_df["signal_ts"] = z_spread_df["signal_ts"].dt.tz_convert(None)
        pair_signal_ts = signal_ts.iloc[pair_indices].copy()
        if pd.api.types.is_datetime64tz_dtype(pair_signal_ts):
            pair_signal_ts = pair_signal_ts.dt.tz_convert(None)
        pair_signal_df = pd.DataFrame(
            {"signal_ts": pair_signal_ts.values, "orig_idx": pair_indices}
        )
        pair_signal_df = pair_signal_df.sort_values("signal_ts").reset_index(drop=True)
        z_spread_df = z_spread_df.sort_values("signal_ts").reset_index(drop=True)
        merged_a = pd.merge_asof(
            pair_signal_df,
            z_spread_df,
            on="signal_ts",
            direction="backward",
            allow_exact_matches=True,
        )
        for _, row in merged_a.iterrows():
            f5a[int(row["orig_idx"])] = row["f5a_spread_z_50"]
        # Volume z-score (uses M1 volume; loads from jsonl)
        signal_ts_for_pair = pd.Series(signal_ts.iloc[pair_indices].values, index=pair_indices)
        z_volume = _build_pair_volume_z(
            pair, signal_ts_for_pair, days=days, window=R7_C_ROLLING_WINDOW
        )
        f5b[pair_indices] = z_volume.reindex(pair_indices).to_numpy()

    out["f5a_spread_z_50"] = f5a
    out["f5b_volume_z_50"] = f5b
    out["f5c_high_spread_low_vol_50"] = (
        np.where(
            np.isnan(f5a) | np.isnan(f5b),
            False,
            (f5a > R7_C_HIGH_SPREAD_THRESHOLD) & (f5b < R7_C_LOW_VOLUME_THRESHOLD),
        )
    ).astype(np.float64)
    # NaN propagation: f5c = NaN if EITHER input is NaN
    f5c_nan_mask = np.isnan(f5a) | np.isnan(f5b)
    out.loc[f5c_nan_mask, "f5c_high_spread_low_vol_50"] = np.nan
    return out


# ---------------------------------------------------------------------------
# R7-C feature NaN row-drop (per 27.0f-α §4.2 / §4.3 / D-Z3.b / D-AA2 / D-AA3)
# ---------------------------------------------------------------------------


def drop_rows_with_missing_r7_c_features(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, dict, np.ndarray]:
    """Drop rows where ANY R7-C feature is NaN; return (df_kept, drop_stats, keep_mask).

    Per 27.0f-α §4.2 / §4.3 / D-AA2. Split-level HALT decision is made
    by the caller (compares drop_count to R7_C_ROW_DROP_HALT_FRAC * n_input).

    Per Fix A row-set isolation: the returned `keep_mask` lets the caller subset
    PnL / labels / scores aligned to the R7-A-clean parent frame so the C-se-rcw
    cell sees R7-C-clean rows while C-se-r7a-replica and C-sb-baseline keep the
    full R7-A-clean row-set (preserves 27.0b baseline reproduction).
    """
    n_input = int(len(df))
    nan_mask = np.zeros(n_input, dtype=bool)
    for col in R7_C_FEATURES:
        if col not in df.columns:
            raise SanityProbeError(f"R7-C feature column missing: {col}")
        col_arr = df[col].to_numpy(dtype=np.float64)
        nan_mask = nan_mask | ~np.isfinite(col_arr)
    keep_mask = ~nan_mask
    n_dropped = int(nan_mask.sum())
    n_kept = n_input - n_dropped
    drop_stats = {
        "n_input": n_input,
        "n_kept": n_kept,
        "n_dropped": n_dropped,
        "drop_frac": float(n_dropped / n_input) if n_input > 0 else 0.0,
    }
    out = df.loc[keep_mask].reset_index(drop=True)
    return out, drop_stats, keep_mask


# ---------------------------------------------------------------------------
# Cell construction (per 27.0f-α §6 / D-Z5 / D-AA5)
# ---------------------------------------------------------------------------


def build_s_e_r7_c_cells() -> list[dict]:
    """27.0f formal grid: 3 cells per design memo §6.1."""
    return [
        {
            "id": "C-se-rcw",
            "picker": "S-E(regressor_pred_r7a+r7c)",
            "score_type": "s_e_r7ac",
            "feature_set": "r7a+r7c",
            "quantile_percents": QUANTILE_PERCENTS_27_0F,
        },
        {
            "id": "C-se-r7a-replica",
            "picker": "S-E(regressor_pred_r7a_only)",
            "score_type": "s_e_r7a",
            "feature_set": "r7a",
            "quantile_percents": QUANTILE_PERCENTS_27_0F,
        },
        {
            "id": "C-sb-baseline",
            "picker": "S-B(raw_p_tp_minus_p_sl)",
            "score_type": "s_b_raw",
            "feature_set": "r7a",
            "quantile_percents": QUANTILE_PERCENTS_27_0F,
        },
    ]


# ---------------------------------------------------------------------------
# C-sb-baseline mismatch check (FAIL-FAST per inheritance)
# ---------------------------------------------------------------------------


def check_c_sb_baseline_match(c_sb_baseline_result: dict) -> dict:
    """Validate C-sb-baseline reproduces 27.0b C-alpha0 baseline.

    Per 27.0f-α §7.1 inheritance from 27.0c-α §7.3. FAIL-FAST HALT
    with BaselineMismatchError on mismatch.

    Fix A row-set isolation: this check is evaluated against the C-sb-baseline
    cell result computed on the R7-A-clean parent row-set (NOT the R7-C-clean
    subset). C-sb-baseline does not reference any R7-C feature, so applying
    R7-C row-drop to it would invalidate baseline reproduction by definition.
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
            "27.0f-α §7.1; failures: " + "; ".join(failures)
        )
    return report


# ---------------------------------------------------------------------------
# C-se-r7a-replica drift check (per 27.0f-α §6.1 / D-AA10 / D-AA11; WARN-only)
# ---------------------------------------------------------------------------


def compute_c_se_r7a_replica_drift_check(c_se_r7a_replica_result: dict) -> dict:
    """DIAGNOSTIC-ONLY WARN; NOT HALT.

    Compares C-se-r7a-replica val-selected test metrics vs 27.0d C-se
    (from artifacts/stage27_0d/sweep_results.json; fallback to PR #325
    constants via load_27_0d_c_se_metrics inherited from 27.0e).

    Fix A row-set isolation: C-se-r7a-replica is evaluated on the R7-A-clean
    parent row-set so this drift check operates on the same row-set as
    27.0d's C-se cell. R7-C drop is NOT applied here.
    """
    rm = c_se_r7a_replica_result.get("test_realised_metrics", {})
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

    # ann_pnl tolerance is fractional of magnitude
    ann_pnl_tolerance_abs = (
        abs(baseline_ann_pnl) * R7A_REPLICA_DRIFT_ANN_PNL_FRAC_TOLERANCE
        if baseline_ann_pnl is not None and np.isfinite(baseline_ann_pnl)
        else None
    )

    n_trades_within = (
        abs(n_trades_delta) <= R7A_REPLICA_DRIFT_N_TRADES_TOLERANCE
        if n_trades_delta is not None
        else False
    )
    sharpe_within = (
        abs(sharpe_delta) <= R7A_REPLICA_DRIFT_SHARPE_TOLERANCE
        if sharpe_delta is not None
        else False
    )
    ann_pnl_within = (
        abs(ann_pnl_delta) <= ann_pnl_tolerance_abs
        if ann_pnl_delta is not None and ann_pnl_tolerance_abs is not None
        else False
    )

    all_within = bool(n_trades_within and sharpe_within and ann_pnl_within)

    report = {
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
    return report


# ---------------------------------------------------------------------------
# H-B6 falsification outcome resolver (per 27.0f-α §7 / D-Z7 / D-AA7 / D-AA8)
# ---------------------------------------------------------------------------


def compute_h_b6_falsification_outcome(cell_results: list[dict]) -> dict:
    """Pick 1 of 4 rows from 27.0f-α §7 (design-memo binding).

    Row precedence: 1 > 2 > 3 > 4. Strict thresholds; no ε.
    Secondary discriminator: C-se-rcw vs C-se-r7a-replica delta-Sharpe at
    matched q (per-q + max-q).

    Per D-AA8: NEEDS_REVIEW if C-se-r7a-replica h_state != OK (defensive).
    """
    c_se_rcw = next((c for c in cell_results if c.get("cell", {}).get("id") == "C-se-rcw"), None)
    c_se_r7a = next(
        (c for c in cell_results if c.get("cell", {}).get("id") == "C-se-r7a-replica"), None
    )
    if c_se_rcw is None or c_se_rcw.get("h_state") != "OK":
        return {
            "h_b6_outcome": H_B6_OUTCOME_NEEDS_REVIEW,
            "row_matched": 0,
            "routing_implication": "C-se-rcw not present or h_state != OK; review wiring",
            "evidence": {"reason": "no C-se-rcw result available"},
        }
    if c_se_r7a is None or c_se_r7a.get("h_state") != "OK":
        return {
            "h_b6_outcome": H_B6_OUTCOME_NEEDS_REVIEW,
            "row_matched": 0,
            "routing_implication": (
                "C-se-r7a-replica not OK; within-eval ablation control required "
                "for Rows 2/3 disambiguation (D-AA8)"
            ),
            "evidence": {"reason": "no C-se-r7a-replica result available"},
        }

    # Per-q evidence
    per_q_rcw: list[dict] = []
    for q_record in c_se_rcw.get("quantile_all", []):
        q_pct = float(q_record.get("q_percent", float("nan")))
        test_block = q_record.get("test", {})
        per_q_rcw.append(
            {
                "q_percent": q_pct,
                "test_sharpe": float(test_block.get("sharpe", float("nan"))),
                "test_annual_pnl": float(test_block.get("annual_pnl", float("nan"))),
            }
        )
    per_q_r7a: list[dict] = []
    for q_record in c_se_r7a.get("quantile_all", []):
        q_pct = float(q_record.get("q_percent", float("nan")))
        test_block = q_record.get("test", {})
        per_q_r7a.append(
            {
                "q_percent": q_pct,
                "test_sharpe": float(test_block.get("sharpe", float("nan"))),
                "test_annual_pnl": float(test_block.get("annual_pnl", float("nan"))),
            }
        )

    # Cell-level Spearman (from val-selected cell of each)
    cell_spearman_rcw = float(c_se_rcw.get("test_formal_spearman", float("nan")))

    # Delta-Sharpe per matched q + max-q
    rcw_by_q = {r["q_percent"]: r["test_sharpe"] for r in per_q_rcw}
    r7a_by_q = {r["q_percent"]: r["test_sharpe"] for r in per_q_r7a}
    matched_qs = sorted(set(rcw_by_q.keys()) & set(r7a_by_q.keys()))
    delta_per_q = []
    for q in matched_qs:
        rcw_s = rcw_by_q[q]
        r7a_s = r7a_by_q[q]
        if np.isfinite(rcw_s) and np.isfinite(r7a_s):
            delta_per_q.append({"q_percent": q, "delta_sharpe": float(rcw_s - r7a_s)})
        else:
            delta_per_q.append({"q_percent": q, "delta_sharpe": float("nan")})
    finite_deltas = [d["delta_sharpe"] for d in delta_per_q if np.isfinite(d["delta_sharpe"])]
    max_q_delta = float(max(finite_deltas)) if finite_deltas else float("nan")
    max_abs_delta = float(max(abs(d) for d in finite_deltas)) if finite_deltas else float("nan")

    evidence = {
        "per_q_c_se_rcw": per_q_rcw,
        "per_q_c_se_r7a_replica": per_q_r7a,
        "delta_sharpe_per_q": delta_per_q,
        "max_q_delta_sharpe": max_q_delta,
        "max_abs_delta_sharpe": max_abs_delta,
        "cell_spearman_c_se_rcw": cell_spearman_rcw,
    }

    # Row 1: STRONG_SUPPORT — exists q in C-se-rcw passing H2
    row_1_match_q: list[float] = []
    for r in per_q_rcw:
        if (
            np.isfinite(r["test_sharpe"])
            and np.isfinite(r["test_annual_pnl"])
            and r["test_sharpe"] >= A1_MIN_SHARPE
            and r["test_annual_pnl"] >= A2_MIN_ANNUAL_PNL
        ):
            row_1_match_q.append(r["q_percent"])
    if row_1_match_q:
        evidence["row_1_match_q"] = row_1_match_q
        return {
            "h_b6_outcome": H_B6_OUTCOME_STRONG_SUPPORT,
            "row_matched": 1,
            "routing_implication": (
                "PROMISING_BUT_NEEDS_OOS branch triggered → separate A0-A5 8-gate PR. "
                "H-B6 elevated to load-bearing. Phase 27's first PROMISING outcome."
            ),
            "evidence": evidence,
        }

    # Row 2: PARTIAL_SUPPORT — C-se-rcw H1m PASS AND max-q delta-Sharpe > 0.05
    h1m_pass = np.isfinite(cell_spearman_rcw) and cell_spearman_rcw >= H1_MEANINGFUL_THRESHOLD
    if h1m_pass and np.isfinite(max_q_delta) and max_q_delta > H_B6_DELTA_SHARPE_PARTIAL_SUPPORT:
        return {
            "h_b6_outcome": H_B6_OUTCOME_PARTIAL_SUPPORT,
            "row_matched": 2,
            "routing_implication": (
                "regime features help directionally but not enough; route to R-T1 "
                "(further selection-rule revision) OR R-B (microstructure feature widening)"
            ),
            "evidence": evidence,
        }

    # Row 3: FALSIFIED_R7C_INSUFFICIENT — H1m PASS AND max-q delta-Sharpe ≤ ±0.05
    if (
        h1m_pass
        and np.isfinite(max_abs_delta)
        and max_abs_delta <= H_B6_DELTA_SHARPE_PARTIAL_SUPPORT
    ):
        return {
            "h_b6_outcome": H_B6_OUTCOME_FALSIFIED_R7C_INSUFFICIENT,
            "row_matched": 3,
            "routing_implication": (
                "regime features don't help; bottleneck is elsewhere; route to R-B "
                "(different feature axis) OR R-T1 / R-T3 / R-E"
            ),
            "evidence": evidence,
        }

    # Row 4: PARTIALLY_FALSIFIED — C-se-rcw H1-weak FAIL (Spearman ≤ 0.05)
    if np.isfinite(cell_spearman_rcw) and cell_spearman_rcw <= H1_WEAK_THRESHOLD:
        return {
            "h_b6_outcome": H_B6_OUTCOME_PARTIALLY_FALSIFIED_NEW_QUESTION,
            "row_matched": 4,
            "routing_implication": (
                "adding R7-C destroyed ranking signal — sub-question whether R7-A's "
                "clean ranking was load-bearing for feature interaction. Route to "
                "R-T1 OR R-E"
            ),
            "evidence": evidence,
        }

    # Default: NEEDS_REVIEW
    return {
        "h_b6_outcome": H_B6_OUTCOME_NEEDS_REVIEW,
        "row_matched": 0,
        "routing_implication": (
            "no row matched — defensive fallback; review per-q evidence manually"
        ),
        "evidence": evidence,
    }


# ---------------------------------------------------------------------------
# Top-tail regime audit (per 27.0f-α §10 item 19 / D-AA9)
# ---------------------------------------------------------------------------


def compute_top_tail_regime_audit(
    val_score_c_se_rcw: np.ndarray,
    val_features: pd.DataFrame,
    q_list: tuple[float, ...] = TOP_TAIL_AUDIT_Q_PERCENTS,
) -> dict:
    """DIAGNOSTIC-ONLY; H-B6 mechanism diagnosis (per 27.0f-α §10 item 19).

    For each q in q_list, report mean f5a / mean f5b / fraction f5c=True
    in C-se-rcw top-q val rows vs population means.
    """
    out: dict = {"per_q": [], "population": {}}

    f5a = val_features["f5a_spread_z_50"].astype(np.float64).to_numpy()
    f5b = val_features["f5b_volume_z_50"].astype(np.float64).to_numpy()
    f5c = val_features["f5c_high_spread_low_vol_50"].astype(np.float64).to_numpy()

    # Population means
    finite_a = f5a[np.isfinite(f5a)]
    finite_b = f5b[np.isfinite(f5b)]
    finite_c = f5c[np.isfinite(f5c)]
    pop_mean_a = float(finite_a.mean()) if len(finite_a) > 0 else float("nan")
    pop_mean_b = float(finite_b.mean()) if len(finite_b) > 0 else float("nan")
    pop_frac_c_true = float(finite_c.mean()) if len(finite_c) > 0 else float("nan")
    out["population"] = {
        "n_finite_f5a": int(len(finite_a)),
        "mean_f5a_spread_z_50": pop_mean_a,
        "n_finite_f5b": int(len(finite_b)),
        "mean_f5b_volume_z_50": pop_mean_b,
        "fraction_f5c_true": pop_frac_c_true,
    }

    for q_pct in q_list:
        cutoff = fit_quantile_cutoff_on_val(val_score_c_se_rcw, q_pct)
        top_mask = val_score_c_se_rcw >= cutoff
        n_top = int(top_mask.sum())
        top_a = f5a[top_mask]
        top_b = f5b[top_mask]
        top_c = f5c[top_mask]
        top_a_finite = top_a[np.isfinite(top_a)]
        top_b_finite = top_b[np.isfinite(top_b)]
        top_c_finite = top_c[np.isfinite(top_c)]
        mean_a_top = float(top_a_finite.mean()) if len(top_a_finite) > 0 else float("nan")
        mean_b_top = float(top_b_finite.mean()) if len(top_b_finite) > 0 else float("nan")
        frac_c_top = float(top_c_finite.mean()) if len(top_c_finite) > 0 else float("nan")
        out["per_q"].append(
            {
                "q_percent": float(q_pct),
                "cutoff": float(cutoff),
                "n_trades_val": n_top,
                "mean_f5a_spread_z_50": mean_a_top,
                "mean_f5b_volume_z_50": mean_b_top,
                "fraction_f5c_true": frac_c_top,
                "delta_mean_f5a_vs_pop": mean_a_top - pop_mean_a,
                "delta_mean_f5b_vs_pop": mean_b_top - pop_mean_b,
                "delta_frac_f5c_vs_pop": frac_c_top - pop_frac_c_true,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Sanity probe (extends 27.0e probe with NEW items 14-19)
# ---------------------------------------------------------------------------


def run_sanity_probe_27_0f(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    pairs: list[str],
    days: int = SPAN_DAYS,
    # Post-fit deferred items
    pnl_train_full: np.ndarray | None = None,
    val_pred_rcw: np.ndarray | None = None,
    test_pred_rcw: np.ndarray | None = None,
    train_pred_rcw: np.ndarray | None = None,
    fold_idx: np.ndarray | None = None,
    oof_corr_diag: dict | None = None,
    train_reg_diag: dict | None = None,
    val_reg_diag: dict | None = None,
    test_reg_diag: dict | None = None,
    regressor_feature_importance_rcw: dict | None = None,
    regressor_feature_importance_r7a: dict | None = None,
    train_drop_for_nan_pnl_count: int | None = None,
    r7_c_drop_stats: dict | None = None,
    r7_c_feature_distribution_train: dict | None = None,
    per_pair_r7_c_stats: dict | None = None,
    top_tail_regime_audit: dict | None = None,
    volume_preflight_diag: dict | None = None,
    cell_definitions: list[dict] | None = None,
    trade_count_budget_audit_c_se_rcw: list[dict] | None = None,
) -> dict:
    """27.0f sanity probe per design memo §10.

    Inherited items 1-13 (from 27.0e); NEW items 14-19 (per 27.0f-α §10).
    """
    print("\n=== 27.0f SANITY PROBE (per 27.0f-α §10) ===")
    out: dict = {}

    # Item 14 (volume pre-flight) is reported here if it was run early
    if volume_preflight_diag is not None:
        out["volume_preflight"] = volume_preflight_diag
        print(f"  R7-C volume pre-flight: status={volume_preflight_diag.get('status')}")

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

    # 4. Mid-to-mid PnL distribution per class (DIAGNOSTIC-ONLY)
    print("  mid-to-mid PnL distribution per class on TRAIN (diagnostic):")
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

    # 5. R7-A new-feature NaN rate
    print("  R7-A new-feature NaN-rate check:")
    out["new_feature_nan_rate"] = {}
    nan_violations: list[tuple[str, str, float]] = []
    for split_name, df in splits.items():
        per_feature: dict[str, dict] = {}
        for feat in NUMERIC_FEATURES_R7A:
            col = df[feat].to_numpy(dtype=np.float64)
            n = len(col)
            nan_count = int((~np.isfinite(col)).sum())
            nan_rate = nan_count / n if n > 0 else float("nan")
            per_feature[feat] = {"n": n, "nan_count": nan_count, "nan_rate": nan_rate}
            print(f"    {split_name}.{feat}: n={n} NaN={nan_count} ({nan_rate:.3%})")
            if np.isfinite(nan_rate) and nan_rate > SANITY_MAX_NEW_FEATURE_NAN_RATE:
                nan_violations.append((split_name, feat, nan_rate))
        out["new_feature_nan_rate"][split_name] = per_feature

    # 6. R7-A positivity check (inherited)
    print("  R7-A positivity check on TRAIN:")
    out["new_feature_distribution_train"] = {}
    positivity_violations: list[tuple[str, str, float]] = []
    for feat in NUMERIC_FEATURES_R7A:
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

    # 7-13 deferred items (inherited from 27.0d / 27.0e; report if available)
    # Item 7: Target distribution
    if pnl_train_full is not None:
        finite = pnl_train_full[np.isfinite(pnl_train_full)]
        if len(finite) > 0:
            out["target_pnl_distribution_train"] = {
                "n_finite": int(len(finite)),
                "mean": float(finite.mean()),
                "std": float(finite.std()),
                "p5": float(np.quantile(finite, 0.05)),
                "p50": float(np.quantile(finite, 0.50)),
                "p95": float(np.quantile(finite, 0.95)),
            }
    else:
        out["target_pnl_distribution_train"] = {"status": "deferred"}

    # Item 8: Predicted PnL distribution
    if train_pred_rcw is not None and val_pred_rcw is not None and test_pred_rcw is not None:
        pred_dist: dict[str, dict] = {}
        for split_name, pred in [
            ("train", train_pred_rcw),
            ("val", val_pred_rcw),
            ("test", test_pred_rcw),
        ]:
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
        out["predicted_pnl_distribution"] = pred_dist
    else:
        out["predicted_pnl_distribution"] = {"status": "deferred"}

    # Item 9: OOF correlation
    if oof_corr_diag is not None:
        out["oof_correlation_diagnostic"] = oof_corr_diag

    # Item 10: regression diagnostic
    if train_reg_diag is not None and val_reg_diag is not None and test_reg_diag is not None:
        out["regression_diagnostic"] = {
            "train": train_reg_diag,
            "val": val_reg_diag,
            "test": test_reg_diag,
        }

    # Item 11: regressor feature importance (both)
    if regressor_feature_importance_rcw is not None:
        out["regressor_feature_importance_rcw"] = regressor_feature_importance_rcw
    if regressor_feature_importance_r7a is not None:
        out["regressor_feature_importance_r7a"] = regressor_feature_importance_r7a

    # NaN-PnL train-row HALT
    if train_drop_for_nan_pnl_count is not None:
        out["train_drop_for_nan_pnl_count"] = int(train_drop_for_nan_pnl_count)

    # NEW item 15 + 16: R7-C feature NaN + row-drop count
    if r7_c_drop_stats is not None:
        out["r7_c_drop_stats"] = r7_c_drop_stats
        for split_name, ds in r7_c_drop_stats.items():
            print(
                f"  R7-C drop {split_name}: n_input={ds['n_input']} "
                f"n_dropped={ds['n_dropped']} drop_frac={ds['drop_frac']:.3%}"
            )

    # NEW item 17: R7-C feature distribution on train
    if r7_c_feature_distribution_train is not None:
        out["r7_c_feature_distribution_train"] = r7_c_feature_distribution_train
        print("  R7-C feature distribution on TRAIN (NEW 27.0f; DIAGNOSTIC-ONLY):")
        for feat, stats in r7_c_feature_distribution_train.items():
            print(
                f"    {feat}: mean={stats.get('mean', float('nan')):+.4f} "
                f"p5={stats.get('p5', float('nan')):+.4f} "
                f"p50={stats.get('p50', float('nan')):+.4f} "
                f"p95={stats.get('p95', float('nan')):+.4f}"
            )

    # NEW item 18: per-pair R7-C stats
    if per_pair_r7_c_stats is not None:
        out["per_pair_r7_c_stats"] = per_pair_r7_c_stats

    # NEW item 19: top-tail regime audit
    if top_tail_regime_audit is not None:
        out["top_tail_regime_audit"] = top_tail_regime_audit
        print("  top-tail regime audit (NEW 27.0f; DIAGNOSTIC-ONLY; H-B6 mechanism diagnosis):")
        for r in top_tail_regime_audit.get("per_q", []):
            print(
                f"    q={r['q_percent']:.1f}: "
                f"f5a={r['mean_f5a_spread_z_50']:+.3f}(Δ{r['delta_mean_f5a_vs_pop']:+.3f}) "
                f"f5b={r['mean_f5b_volume_z_50']:+.3f}(Δ{r['delta_mean_f5b_vs_pop']:+.3f}) "
                f"f5c%={r['fraction_f5c_true']:.1%}(Δ{r['delta_frac_f5c_vs_pop']:+.1%})"
            )

    # Quantile-family disclosure (inherited from 27.0e)
    if cell_definitions is not None:
        disclosure: dict[str, dict] = {}
        for cell in cell_definitions:
            cell_id = cell.get("id", "?")
            disclosure[cell_id] = {
                "quantile_percents": list(cell.get("quantile_percents", ())),
                "feature_set": cell.get("feature_set", "?"),
            }
        out["quantile_family_disclosure"] = disclosure

    # Trade-count budget audit (inherited from 27.0e)
    if trade_count_budget_audit_c_se_rcw is not None:
        out["trade_count_budget_audit_c_se_rcw"] = trade_count_budget_audit_c_se_rcw

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
            f"{len(over_99_pairs)} pair(s) over {SANITY_MAX_PER_PAIR_TIME_SHARE:.0%} TIME"
        )
    if nan_violations:
        raise SanityProbeError(
            f"R7-A NaN rate over {SANITY_MAX_NEW_FEATURE_NAN_RATE:.0%}: {nan_violations[:5]}"
        )
    if positivity_violations:
        raise SanityProbeError(
            f"R7-A positivity violated over {SANITY_MAX_POSITIVITY_VIOLATION_RATE:.0%}: "
            f"{positivity_violations[:5]}"
        )

    # NEW 27.0f HALT (item 16; D-AA12): R7-C row-drop > 1% per split (C-se-rcw row-set)
    if r7_c_drop_stats is not None:
        for split_name, ds in r7_c_drop_stats.items():
            if ds["drop_frac"] > R7_C_ROW_DROP_HALT_FRAC:
                raise SanityProbeError(
                    f"R7-C row-drop (C-se-rcw row-set) on {split_name} = "
                    f"{ds['drop_frac']:.3%} > {R7_C_ROW_DROP_HALT_FRAC:.1%} "
                    "(per D-AA3 / D-Z3.c)"
                )

    # NaN-PnL HALT (inherited from 27.0d D-J12)
    if train_drop_for_nan_pnl_count is not None and pnl_train_full is not None:
        n_train_for_threshold = len(pnl_train_full)
        threshold = NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD * n_train_for_threshold
        if train_drop_for_nan_pnl_count > threshold:
            raise SanityProbeError(
                f"train rows with NaN PnL = {train_drop_for_nan_pnl_count} > "
                f"{NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD:.1%} of n_train"
            )

    print("=== SANITY PROBE: PASS ===\n")
    out["status"] = "PASS"
    return out


# ---------------------------------------------------------------------------
# Per-cell evaluation (per 27.0f-α §6.2; D-AA5)
# ---------------------------------------------------------------------------


def evaluate_cell_27_0f(
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
    """27.0f cell evaluation. Mirrors 27.0e shape; reads cell['feature_set']."""
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

    quantile_percents = tuple(cell.get("quantile_percents", QUANTILE_PERCENTS_27_0F))
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
    probs_for_diag = test_raw_probs
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


# ---------------------------------------------------------------------------
# Report writer (25 sections per 27.0f-α §11; D-AA14)
# ---------------------------------------------------------------------------


def _cell_signature(cell: dict) -> str:
    return (
        f"id={cell['id']} picker={cell['picker']} "
        f"score_type={cell.get('score_type', '-')} feature_set={cell.get('feature_set', '?')}"
    )


def write_eval_report_27_0f(
    out_path: Path,
    cell_results: list[dict],
    val_select: dict,
    verdict_info: dict,
    aggregate_info: dict,
    baseline_match_report: dict,
    r7a_replica_drift_report: dict,
    sanity: dict,
    drop_stats_r7a: dict,
    drop_stats_r7c: dict,
    split_dates: tuple,
    preflight_diag: dict,
    n_cells_run: int,
    regressor_feature_importance_rcw: dict,
    regressor_feature_importance_r7a: dict,
    train_reg_diag_rcw: dict,
    val_reg_diag_rcw: dict,
    test_reg_diag_rcw: dict,
    oof_corr_diag_rcw: dict,
    target_pnl_distribution: dict,
    predicted_pnl_distribution_rcw: dict,
    h_b6_outcome: dict,
    top_tail_regime_audit: dict,
) -> None:
    t_min, t70, t85, t_max = split_dates
    lines: list[str] = []
    lines.append("# Stage 27.0f-β — S-E + R7-C Regime/Context Feature Eval Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append(
        "Design contract: "
        "`docs/design/phase27_0f_alpha_s_e_r7_c_regime_context_design_memo.md` "
        "(PR #331) under PR #330 (R7-C scope amendment), PR #323 (S-E scope amendment), "
        "Phase 27 kickoff (PR #316), and inherited Phase 26 framework (PR #311 / #313)."
    )
    lines.append("")
    # §1
    lines.append("## 1. Mandatory clauses (clauses 1-5 verbatim; clause 6 = PR #330 §6 verbatim)")
    lines.append("")
    lines.append(
        "**1. Phase framing.** ADOPT requires both H2 PASS and the full 8-gate A0-A5 harness."
    )
    lines.append("")
    lines.append(
        "**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / "
        "directional-comparison / classification-quality / feature-importance / "
        "per-pair-Sharpe-contribution columns are diagnostic-only. 27.0c-27.0e extensions "
        "preserved. 27.0f extension: R7-C feature distribution + per-pair R7-C stats + "
        "top-tail regime audit + C-se-r7a-replica drift are diagnostic-only."
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
        "**6. Phase 27 scope.** R7-A admissible at kickoff. R7-C promoted from "
        "'requires SEPARATE scope-amendment PR' to 'admissible at 27.0f-α design memo' "
        "via PR #330; on PR #331 merge the S-E + R7-C 3-cell structure became formal "
        "at 27.0f-β. Closed allowlist: [f5a_spread_z_50, f5b_volume_z_50, "
        "f5c_high_spread_low_vol_50]. R7-B requires its own scope amendment. R7-D / "
        "R7-Other NOT admissible. S-A/S-B/S-C admissible at kickoff; S-D 27.0c-β via "
        "PR #320; S-E 27.0d-β via PR #323; 27.0e R-T2 formal via PR #327. Phase 26 "
        "deferred items NOT subsumed."
    )
    lines.append("")
    # §2
    lines.append("## 2. D-1 binding (formal realised-PnL = inherited harness)")
    lines.append("")
    lines.append(
        "Formal realised-PnL uses inherited `_compute_realised_barrier_pnl` (bid/ask "
        "executable). Mid-to-mid PnL appears in sanity probe only. S-E regression "
        "target uses the SAME bid/ask harness."
    )
    lines.append("")
    # §3
    lines.append("## 3. R7-A + R7-C feature set (FIXED per 27.0f-α §2; 7 features total)")
    lines.append("")
    lines.append(f"- R7-A (4 features; FIXED): {list(ALL_FEATURES_R7A)}")
    lines.append(f"- R7-C (3 features; ADDITIVE; PR #330): {list(R7_C_FEATURES)}")
    lines.append(f"- R7-A + R7-C union (7 features): {list(ALL_FEATURES_R7AC)}")
    lines.append(
        "- R7-C construction per Phase 25.0f-α §2.4 / §2.5 / §2.6 "
        "(shift(1) BEFORE rolling; lookback 50)."
    )
    lines.append("")
    # §4
    lines.append("## 4. 3-cell definitions (per 27.0f-α §6.1)")
    lines.append("")
    lines.append("- C-se-rcw: S-E on R7-A + R7-C (7 features); LightGBMRegressor + Huber α=0.9")
    lines.append("- C-se-r7a-replica: S-E on R7-A only (4 features); within-eval ablation control")
    lines.append("- C-sb-baseline: raw P(TP) - P(SL) on multiclass head; inheritance-chain check")
    lines.append("- Quantile family for ALL 3 cells: {5, 10, 20, 30, 40}")
    lines.append(
        "- D10 amendment 3-artifact form: 1 regressor on R7-A+R7-C + "
        "1 regressor on R7-A + 1 multiclass head"
    )
    lines.append("")
    # §5
    lines.append("## 5. Sanity probe (per 27.0f-α §10)")
    lines.append("")
    lines.append(f"- status: **{sanity.get('status', 'unknown')}**")
    vol_pf = sanity.get("volume_preflight", {})
    lines.append(f"- R7-C volume pre-flight: {vol_pf.get('status', 'unknown')}")
    cp_train = sanity.get("class_priors", {}).get("train", {})
    counts = cp_train.get("counts", {})
    shares = cp_train.get("shares", {})
    for cls, name in [(LABEL_TP, "TP"), (LABEL_SL, "SL"), (LABEL_TIME, "TIME")]:
        c = counts.get(cls, 0)
        s = shares.get(cls, float("nan"))
        lines.append(f"  - {name}: {c} ({s:.3%})")
    if "r7_c_drop_stats" in sanity:
        for split_name, ds in sanity["r7_c_drop_stats"].items():
            lines.append(
                f"- R7-C drop {split_name}: n_dropped={ds['n_dropped']} ({ds['drop_frac']:.3%})"
            )
    lines.append("")
    # §6
    lines.append("## 6. Pre-flight diagnostics + row-drop + split dates")
    lines.append(f"- label rows (pre-drop): {preflight_diag.get('label_rows', 'n/a')}")
    lines.append(f"- pairs: {preflight_diag.get('pairs', 'n/a')}")
    lines.append(f"- LightGBM: {preflight_diag.get('lightgbm_available', 'n/a')}")
    lines.append(f"- formal cells run: {n_cells_run}")
    lines.append("R7-A row-drop policy:")
    for split_name in ("train", "val", "test"):
        ds = drop_stats_r7a.get(split_name, {})
        lines.append(
            f"- {split_name}: n_input={ds.get('n_input', 0)} "
            f"n_kept={ds.get('n_kept', 0)} n_dropped={ds.get('n_dropped', 0)}"
        )
    lines.append(
        "R7-C row-drop policy (Fix A: applied to C-se-rcw row-set ONLY; "
        "C-se-r7a-replica and C-sb-baseline evaluate on R7-A-clean parent):"
    )
    for split_name in ("train", "val", "test"):
        ds = drop_stats_r7c.get(split_name, {})
        lines.append(
            f"- {split_name}: n_input={ds.get('n_input', 0)} "
            f"n_kept={ds.get('n_kept', 0)} n_dropped={ds.get('n_dropped', 0)} "
            f"drop_frac={ds.get('drop_frac', 0.0):.3%} (C-se-rcw only)"
        )
    lines.append("Split dates:")
    lines.append(f"- min: {t_min}")
    lines.append(f"- train < {t70}")
    lines.append(f"- val [{t70}, {t85})")
    lines.append(f"- test [{t85}, {t_max}]")
    lines.append("")
    # §7
    lines.append(
        "## 7. All formal cells — primary quantile-family summary "
        "(3 cells × 5 q = 15 (cell, q) pairs)"
    )
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
        "**Note**: 27.0f-β cannot mint ADOPT_CANDIDATE. H2 PASS → PROMISING_BUT_NEEDS_OOS."
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
    # §11 — 6-column baseline comparison
    lines.append("## 11. MANDATORY: Baseline comparison (per 27.0f-α §11.11; 6-column)")
    lines.append("")
    if sel is None:
        sig = "n/a"
        r27f = (float("nan"), float("nan"), 0, float("nan"))
    else:
        rm = sel.get("test_realised_metrics", {})
        sig = _cell_signature(sel["cell"])
        r27f = (
            rm.get("sharpe", float("nan")),
            rm.get("annual_pnl", float("nan")),
            rm.get("n_trades", 0),
            sel.get("test_formal_spearman", float("nan")),
        )
    lines.append(
        "| Aspect | 26.0d R6-new-A C02 | 27.0b C-alpha0 / S-B | 27.0c C-sd / S-D | "
        "27.0d C-se / S-E q=40 | 27.0e C-se-trimmed q=10 | 27.0f val-selected |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    lines.append(
        "| Feature set | R7-A | R7-A | R7-A | R7-A | R7-A | R7-A or R7-A+R7-C per val-sel |"
    )
    lines.append("| Score | S-B | S-B | S-D | S-E | S-E (trimmed q) | S-E or S-B per val-sel |")
    lines.append(f"| Cell signature | C02 | C-alpha0 | C-sd | C-se | C-se-trimmed | {sig} |")
    lines.append(f"| Test n_trades | 34,626 | 34,626 | 32,324 | 184,703 | 35,439 | {r27f[2]} |")
    lines.append(
        f"| Test Sharpe | -0.1732 | -0.1732 | -0.1760 | -0.4830 | -0.7670 | {r27f[0]:.4f} |"
    )
    lines.append(
        f"| Test Spearman | -0.1535 | -0.1535 | -0.1060 | +0.4381 | +0.4381 | {r27f[3]:.4f} |"
    )
    lines.append(
        "| Verdict | REJECT (+ YES_IMPROVED) | REJECT_ND | REJECT_ND | "
        "SPLIT_VERDICT | SPLIT_VERDICT | " + str(verdict_info.get("verdict")) + " |"
    )
    lines.append("")
    # §12 — C-sb-baseline reproduction check
    lines.append("## 12. MANDATORY: C-sb-baseline reproduction check (per 27.0f-α §7.1)")
    lines.append("")
    b = baseline_match_report
    lines.append(
        f"- n_trades: observed={b.get('n_trades_observed', 0)} "
        f"baseline={b.get('n_trades_baseline', 0)} "
        f"delta={b.get('n_trades_delta', 0):+d} match=**{b.get('n_trades_match')}**"
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
    # §13 — C-se-r7a-replica drift check (NEW)
    lines.append(
        "## 13. MANDATORY: C-se-r7a-replica reproduction check vs 27.0d C-se (DIAGNOSTIC-ONLY WARN)"
    )
    lines.append("")
    d = r7a_replica_drift_report
    lines.append(f"- source: `{d.get('source', '?')}`")
    lines.append(
        f"- n_trades: observed={d.get('n_trades_observed')} "
        f"27.0d_baseline={d.get('n_trades_baseline_27_0d')} "
        f"delta={d.get('n_trades_delta')} "
        f"within_tolerance={d.get('n_trades_within_tolerance')}"
    )
    lines.append(
        f"- Sharpe: observed={d.get('sharpe_observed', float('nan')):.6f} "
        f"27.0d_baseline={d.get('sharpe_baseline_27_0d')} "
        f"delta={d.get('sharpe_delta')} "
        f"within_tolerance={d.get('sharpe_within_tolerance')}"
    )
    lines.append(
        f"- ann_pnl: observed={d.get('ann_pnl_observed', float('nan')):+.3f} "
        f"27.0d_baseline={d.get('ann_pnl_baseline_27_0d')} "
        f"delta={d.get('ann_pnl_delta')} "
        f"within_tolerance={d.get('ann_pnl_within_tolerance')}"
    )
    lines.append(f"- all_within_tolerance: {d.get('all_within_tolerance')}")
    lines.append(f"- **drift WARN: {d.get('warn')}** (DIAGNOSTIC-ONLY; not HALT)")
    lines.append("")
    # §14
    lines.append("## 14. MANDATORY: Per-pair Sharpe contribution table (val-selected; D4 sort)")
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
    # §15
    lines.append("## 15. MANDATORY: Pair concentration per cell")
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
    # §16
    lines.append("## 16. Classification-quality diagnostics on multiclass head (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| cell | AUC(P(TP)) | Cohen κ | logloss |")
    lines.append("|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        cd = c.get("test_classification_diag", {})
        lines.append(
            f"| {cell['id']} | "
            f"{cd.get('auc_tp_ovr', float('nan')):.4f} | "
            f"{cd.get('cohen_kappa', float('nan')):.4f} | "
            f"{cd.get('multiclass_logloss', float('nan')):.4f} |"
        )
    lines.append("")
    # §17 — regressor feature importance (BOTH)
    lines.append("## 17. Regressor feature importance (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("### C-se-rcw (R7-A + R7-C; 7 features)")
    fi = regressor_feature_importance_rcw
    b = fi.get("buckets", {})
    bn = fi.get("buckets_normalised", {})
    for feat in ALL_FEATURES_R7AC:
        lines.append(f"- {feat} (gain): {b.get(feat, 0.0):.1f} ({bn.get(feat, 0.0):.3f})")
    lines.append("")
    lines.append("### C-se-r7a-replica (R7-A only; 4 features)")
    fi = regressor_feature_importance_r7a
    b = fi.get("buckets", {})
    bn = fi.get("buckets_normalised", {})
    for feat in ALL_FEATURES_R7A:
        lines.append(f"- {feat} (gain): {b.get(feat, 0.0):.1f} ({bn.get(feat, 0.0):.3f})")
    lines.append("")
    # §18-20 (predicted PnL distribution, OOF correlation, MAE/R²) — abbreviated for brevity
    lines.append("## 18. Predicted-PnL distribution train/val/test for C-se-rcw (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| split | n_finite | p5 | p50 | p95 | mean |")
    lines.append("|---|---|---|---|---|---|")
    for split_name in ("train", "val", "test"):
        s = predicted_pnl_distribution_rcw.get(split_name, {})
        if "p50" not in s:
            lines.append(f"| {split_name} | - | - | - | - | - |")
            continue
        lines.append(
            f"| {split_name} | {s.get('n_finite', 0)} | "
            f"{s.get('p5', float('nan')):+.4f} | "
            f"{s.get('p50', float('nan')):+.4f} | "
            f"{s.get('p95', float('nan')):+.4f} | "
            f"{s.get('mean', float('nan')):+.4f} |"
        )
    lines.append("")
    lines.append("## 19. Predicted-vs-realised correlation (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| split | n | Pearson | Spearman |")
    lines.append("|---|---|---|---|")
    oof_agg_row = {
        "n": "n/a",
        "pearson": oof_corr_diag_rcw.get("aggregate_pearson", float("nan")),
        "spearman": oof_corr_diag_rcw.get("aggregate_spearman", float("nan")),
    }
    for label, dd in [
        ("OOF aggregate", oof_agg_row),
        ("train (refit)", train_reg_diag_rcw),
        ("val", val_reg_diag_rcw),
        ("test", test_reg_diag_rcw),
    ]:
        n_str = str(dd.get("n", "-"))
        p_val = dd.get("pearson", float("nan"))
        s_val = dd.get("spearman", float("nan"))
        lines.append(f"| {label} | {n_str} | {p_val:+.4f} | {s_val:+.4f} |")
    lines.append("")
    lines.append("## 20. Regressor MAE + R² (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| split | n | MAE | R² |")
    lines.append("|---|---|---|---|")
    for label, dd in [
        ("train", train_reg_diag_rcw),
        ("val", val_reg_diag_rcw),
        ("test", test_reg_diag_rcw),
    ]:
        lines.append(
            f"| {label} | {dd.get('n', 0)} | "
            f"{dd.get('mae', float('nan')):.4f} | "
            f"{dd.get('r2', float('nan')):+.4f} |"
        )
    lines.append("")
    # §21
    lines.append("## 21. Multiple-testing caveat")
    lines.append(
        f"{n_cells_run} formal cells × per-cell quantile counts (sum) = "
        f"{sum(len(c['cell'].get('quantile_percents', ())) for c in cell_results)} "
        "(cell, q) pairs (up from 10 in 27.0e → §22 H-B6 outcome row pre-stated to "
        "mitigate exposure). PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE are "
        "hypothesis-generating only."
    )
    lines.append("")
    # §22 — H-B6 outcome (NEW; binding per §7)
    lines.append("## 22. H-B6 falsification outcome (per 27.0f-α §7; design-memo binding)")
    lines.append("")
    lines.append(f"- **outcome: {h_b6_outcome.get('h_b6_outcome')}**")
    lines.append(f"- row matched: {h_b6_outcome.get('row_matched')}")
    lines.append(f"- routing implication: {h_b6_outcome.get('routing_implication')}")
    ev = h_b6_outcome.get("evidence", {})
    if "cell_spearman_c_se_rcw" in ev:
        lines.append(f"- C-se-rcw cell Spearman: {ev['cell_spearman_c_se_rcw']:+.4f}")
    if "max_q_delta_sharpe" in ev:
        lines.append(
            f"- max-q delta-Sharpe (C-se-rcw - C-se-r7a-replica): {ev['max_q_delta_sharpe']:+.4f}"
        )
    if "max_abs_delta_sharpe" in ev:
        lines.append(f"- max abs delta-Sharpe: {ev['max_abs_delta_sharpe']:+.4f}")
    if "delta_sharpe_per_q" in ev:
        lines.append("- Per-q delta-Sharpe:")
        for r in ev["delta_sharpe_per_q"]:
            lines.append(f"  - q={r['q_percent']:.1f}: delta_sharpe={r['delta_sharpe']:+.4f}")
    lines.append("")
    # §23 — top-tail regime audit (NEW; DIAGNOSTIC-ONLY)
    lines.append("## 23. NEW: Top-tail regime audit (DIAGNOSTIC-ONLY; H-B6 mechanism diagnosis)")
    lines.append("")
    pop = top_tail_regime_audit.get("population", {})
    pop_f5a = pop.get("mean_f5a_spread_z_50", float("nan"))
    pop_f5b = pop.get("mean_f5b_volume_z_50", float("nan"))
    pop_f5c = pop.get("fraction_f5c_true", float("nan"))
    lines.append(
        f"Population: f5a={pop_f5a:+.4f}, f5b={pop_f5b:+.4f}, f5c activation={pop_f5c:.1%}"
    )
    lines.append("")
    lines.append(
        "| q% | n_trades_val | mean_f5a | Δpop_f5a | mean_f5b | Δpop_f5b | f5c_true % | Δpop_f5c |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for r in top_tail_regime_audit.get("per_q", []):
        lines.append(
            f"| {r['q_percent']:.1f} | {r['n_trades_val']} | "
            f"{r['mean_f5a_spread_z_50']:+.4f} | {r['delta_mean_f5a_vs_pop']:+.4f} | "
            f"{r['mean_f5b_volume_z_50']:+.4f} | {r['delta_mean_f5b_vs_pop']:+.4f} | "
            f"{r['fraction_f5c_true']:.1%} | {r['delta_frac_f5c_vs_pop']:+.1%} |"
        )
    lines.append("")
    # §24 — C-se-r7a-replica vs 27.0d delta (NEW)
    lines.append("## 24. NEW: C-se-r7a-replica vs 27.0d C-se delta (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append(f"- source: `{r7a_replica_drift_report.get('source', '?')}`")
    lines.append(
        f"- n_trades delta: {r7a_replica_drift_report.get('n_trades_delta')} "
        f"(tolerance ±{R7A_REPLICA_DRIFT_N_TRADES_TOLERANCE})"
    )
    lines.append(
        f"- Sharpe delta: {r7a_replica_drift_report.get('sharpe_delta')} "
        f"(tolerance ±{R7A_REPLICA_DRIFT_SHARPE_TOLERANCE})"
    )
    lines.append(
        f"- ann_pnl delta: {r7a_replica_drift_report.get('ann_pnl_delta')} "
        f"(tolerance ±{R7A_REPLICA_DRIFT_ANN_PNL_FRAC_TOLERANCE:.1%} of magnitude)"
    )
    lines.append(f"- all_within_tolerance: {r7a_replica_drift_report.get('all_within_tolerance')}")
    lines.append("")
    # §25 — Verdict statement
    lines.append(
        f"## 25. Verdict statement: **{verdict_info.get('verdict')}** "
        f"(C-sb-baseline match: {baseline_match_report.get('all_match')}; "
        f"H-B6 outcome: {h_b6_outcome.get('h_b6_outcome')})"
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


def _compute_r7_c_feature_distribution_train(train_df: pd.DataFrame) -> dict:
    """NEW item 17: R7-C feature distribution on train (DIAGNOSTIC-ONLY)."""
    out: dict = {}
    for feat in R7_C_FEATURES:
        if feat not in train_df.columns:
            out[feat] = {"status": "missing"}
            continue
        col = train_df[feat].to_numpy(dtype=np.float64)
        finite = col[np.isfinite(col)]
        if len(finite) == 0:
            out[feat] = {"n_finite": 0}
            continue
        out[feat] = {
            "n_finite": int(len(finite)),
            "mean": float(finite.mean()),
            "std": float(finite.std()),
            "p5": float(np.quantile(finite, 0.05)),
            "p50": float(np.quantile(finite, 0.50)),
            "p95": float(np.quantile(finite, 0.95)),
            "min": float(finite.min()),
            "max": float(finite.max()),
        }
    return out


def _compute_per_pair_r7_c_stats(train_df: pd.DataFrame, pairs: list[str]) -> dict:
    """NEW item 18: per-pair R7-C stats (DIAGNOSTIC-ONLY)."""
    out: dict = {}
    train_pairs = train_df["pair"].to_numpy()
    for pair in pairs:
        mask = train_pairs == pair
        n = int(mask.sum())
        if n == 0:
            out[pair] = {"n": 0}
            continue
        f5a = train_df.loc[mask, "f5a_spread_z_50"].to_numpy(dtype=np.float64)
        f5b = train_df.loc[mask, "f5b_volume_z_50"].to_numpy(dtype=np.float64)
        f5c = train_df.loc[mask, "f5c_high_spread_low_vol_50"].to_numpy(dtype=np.float64)
        f5a_finite = f5a[np.isfinite(f5a)]
        f5b_finite = f5b[np.isfinite(f5b)]
        f5c_finite = f5c[np.isfinite(f5c)]
        out[pair] = {
            "n": n,
            "f5a_p50": float(np.quantile(f5a_finite, 0.50))
            if len(f5a_finite) > 0
            else float("nan"),
            "f5b_p50": float(np.quantile(f5b_finite, 0.50))
            if len(f5b_finite) > 0
            else float("nan"),
            "f5c_activation_rate": float(f5c_finite.mean())
            if len(f5c_finite) > 0
            else float("nan"),
        }
    return out


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

    print(f"=== Stage 27.0f-β S-E + R7-C regime/context eval ({len(args.pairs)} pairs) ===")
    print(
        f"K_FAV={K_FAV} K_ADV={K_ADV} H_M1={H_M1_BARS} | "
        f"quantile_percents={list(QUANTILE_PERCENTS_27_0F)}"
    )
    print(f"R7-A FIXED (4 features): {list(ALL_FEATURES_R7A)}")
    print(f"R7-C ADDITIVE (3 features): {list(R7_C_FEATURES)}")
    print(f"R7-A + R7-C union (7 features): {list(ALL_FEATURES_R7AC)}")
    print(
        f"Regressor: LightGBMRegressor objective='huber' alpha={HUBER_ALPHA} "
        f"(inherited from 27.0d / 27.0e)"
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

    # 3. NEW: Volume pre-flight (run early per D-AA13)
    volume_preflight_diag = verify_volume_preflight(args.pairs, days=args.days)

    # 4. M1 runtime
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
            f"test={len(test_df)} — formal verdict NOT valid in quick mode"
        )

    # 6. Sanity probe (probe-only stage; items 14 done; items 15-19 deferred)
    sanity = run_sanity_probe_27_0f(
        train_df,
        val_df,
        test_df,
        pair_runtime_map,
        args.pairs,
        days=args.days,
        volume_preflight_diag=volume_preflight_diag,
    )

    if args.sanity_probe_only:
        print("\n--sanity-probe-only set; exiting after probe.")
        if not args.no_write:
            (args.out_dir / "sanity_probe.json").write_text(
                json.dumps(sanity, indent=2, default=str), encoding="utf-8"
            )
            print(f"sanity probe results: {args.out_dir / 'sanity_probe.json'}")
        return 0

    # 7. R7-A row-drop (inherited)
    print("R7-A row-drop...")
    train_df, train_drop = drop_rows_with_missing_new_features(train_df)
    val_df, val_drop = drop_rows_with_missing_new_features(val_df)
    test_df, test_drop = drop_rows_with_missing_new_features(test_df)
    drop_stats_r7a = {"train": train_drop, "val": val_drop, "test": test_drop}
    for name, ds in drop_stats_r7a.items():
        print(
            f"  {name}: n_input={ds['n_input']} n_kept={ds['n_kept']} n_dropped={ds['n_dropped']}"
        )

    # 8. NEW: Build R7-C features per split
    print("Building R7-C features (causal shift(1) before rolling)...")
    t0 = time.time()
    train_df = build_r7_c_features(train_df, days=args.days)
    val_df = build_r7_c_features(val_df, days=args.days)
    test_df = build_r7_c_features(test_df, days=args.days)
    print(f"  R7-C feature build: {time.time() - t0:.1f}s")

    # 9. NEW: R7-C row-drop — Fix A: row-set isolation
    #    R7-C-clean row-set is C-se-rcw ONLY. C-se-r7a-replica and C-sb-baseline
    #    use the parent R7-A-clean row-set so 27.0b baseline reproduction is preserved.
    print("R7-C row-drop (C-se-rcw ONLY; C-se-r7a-replica/C-sb-baseline use R7-A-clean)...")
    train_df_rcw, train_drop_r7c, train_r7c_keep = drop_rows_with_missing_r7_c_features(train_df)
    val_df_rcw, val_drop_r7c, val_r7c_keep = drop_rows_with_missing_r7_c_features(val_df)
    test_df_rcw, test_drop_r7c, test_r7c_keep = drop_rows_with_missing_r7_c_features(test_df)
    drop_stats_r7c = {"train": train_drop_r7c, "val": val_drop_r7c, "test": test_drop_r7c}
    for name, ds in drop_stats_r7c.items():
        print(
            f"  {name}: n_input={ds['n_input']} n_kept={ds['n_kept']} "
            f"n_dropped={ds['n_dropped']} drop_frac={ds['drop_frac']:.3%} (C-se-rcw row-set)"
        )
    # HALT if > 1% on the C-se-rcw row-set (D-AA3); parent R7-A-clean row-set unaffected.
    for split_name, ds in drop_stats_r7c.items():
        if ds["drop_frac"] > R7_C_ROW_DROP_HALT_FRAC:
            raise SanityProbeError(
                f"R7-C row-drop (C-se-rcw row-set) on {split_name} = "
                f"{ds['drop_frac']:.3%} > {R7_C_ROW_DROP_HALT_FRAC:.1%} "
                "(per D-AA3 / D-Z3.c)"
            )

    # 10. Precompute realised PnL on R7-A-clean parent frames (D-1 binding)
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

    # 10b. Subset to R7-C-clean (C-se-rcw) via keep_mask
    pnl_train_rcw = pnl_train_full[train_r7c_keep]
    pnl_val_rcw = pnl_val_full[val_r7c_keep]
    pnl_test_rcw = pnl_test_full[test_r7c_keep]

    # NaN-PnL train-row check (D-J12 inherited) on R7-A-clean parent
    nan_pnl_mask = ~np.isfinite(pnl_train_full)
    nan_pnl_count = int(nan_pnl_mask.sum())
    threshold_count = NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD * len(pnl_train_full)
    print(f"  NaN-PnL train rows: {nan_pnl_count} (HALT > {int(threshold_count)})")
    if nan_pnl_count > threshold_count:
        raise SanityProbeError(
            f"train rows with NaN PnL = {nan_pnl_count} > {NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD:.1%}"
        )

    # R7-A-clean for-reg subset (drops NaN PnL only)
    train_df_for_reg_r7a = train_df.loc[~nan_pnl_mask].reset_index(drop=True)
    pnl_train_for_reg_r7a = pnl_train_full[~nan_pnl_mask]

    # R7-C-clean for-reg subset (NaN PnL on the rcw row-set)
    nan_pnl_mask_rcw = ~np.isfinite(pnl_train_rcw)
    train_df_for_reg_rcw = train_df_rcw.loc[~nan_pnl_mask_rcw].reset_index(drop=True)
    pnl_train_for_reg_rcw = pnl_train_rcw[~nan_pnl_mask_rcw]

    # 11. Build labels on both row-sets
    train_label_r7a = build_l1_labels_for_dataframe(train_df).to_numpy()
    val_label_r7a = build_l1_labels_for_dataframe(val_df).to_numpy()
    test_label_r7a = build_l1_labels_for_dataframe(test_df).to_numpy()
    train_label_rcw = build_l1_labels_for_dataframe(train_df_rcw).to_numpy()
    val_label_rcw = build_l1_labels_for_dataframe(val_df_rcw).to_numpy()
    test_label_rcw = build_l1_labels_for_dataframe(test_df_rcw).to_numpy()

    # 12. 5-fold OOF regression on R7-A + R7-C (DIAGNOSTIC-ONLY) — uses C-se-rcw train
    print("Running 5-fold OOF regression on R7-A + R7-C (DIAGNOSTIC-ONLY; seed=42)...")
    fold_idx = make_oof_fold_assignment(
        len(pnl_train_for_reg_rcw), n_folds=OOF_N_FOLDS, seed=OOF_SEED
    )
    x_train_rcw = train_df_for_reg_rcw[list(ALL_FEATURES_R7AC)]
    x_train_r7a = train_df_for_reg_r7a[list(ALL_FEATURES_R7A)]
    t0 = time.time()
    oof_preds = fit_oof_regression_diagnostic(x_train_rcw, pnl_train_for_reg_rcw, fold_idx)
    print(f"  OOF regression on R7-A+R7-C: {time.time() - t0:.1f}s")
    oof_corr_diag_rcw = compute_oof_correlation_diagnostic(
        oof_preds, pnl_train_for_reg_rcw, fold_idx
    )
    print(
        f"  OOF pearson={oof_corr_diag_rcw['aggregate_pearson']:+.4f} "
        f"spearman={oof_corr_diag_rcw['aggregate_spearman']:+.4f}"
    )

    # 13. Fit 3 production artifacts (D10 amendment) — each on its own row-set per Fix A
    print("Fitting production regressor on R7-A + R7-C (C-se-rcw head; R7-C-clean train)...")
    t0 = time.time()
    regressor_rcw = build_pipeline_lightgbm_regression_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        regressor_rcw.fit(x_train_rcw, pnl_train_for_reg_rcw)
    val_pred_rcw = compute_picker_score_s_e(regressor_rcw, val_df_rcw[list(ALL_FEATURES_R7AC)])
    test_pred_rcw = compute_picker_score_s_e(regressor_rcw, test_df_rcw[list(ALL_FEATURES_R7AC)])
    train_pred_rcw = compute_picker_score_s_e(regressor_rcw, x_train_rcw)
    regressor_feature_importance_rcw = compute_feature_importance_diagnostic(regressor_rcw)
    print(f"  C-se-rcw fit + predict: {time.time() - t0:.1f}s")

    print("Fitting production regressor on R7-A only (C-se-r7a-replica head; R7-A-clean train)...")
    t0 = time.time()
    regressor_r7a = build_pipeline_lightgbm_regression_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        regressor_r7a.fit(x_train_r7a, pnl_train_for_reg_r7a)
    val_pred_r7a = compute_picker_score_s_e(regressor_r7a, val_df[list(ALL_FEATURES_R7A)])
    test_pred_r7a = compute_picker_score_s_e(regressor_r7a, test_df[list(ALL_FEATURES_R7A)])
    regressor_feature_importance_r7a = compute_feature_importance_diagnostic(regressor_r7a)
    print(f"  C-se-r7a-replica fit + predict: {time.time() - t0:.1f}s")

    print(
        "Fitting production multiclass head on R7-A only (C-sb-baseline head; R7-A-clean train)..."
    )
    t0 = time.time()
    multiclass_pipeline = build_pipeline_lightgbm_multiclass_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        multiclass_pipeline.fit(x_train_r7a, train_label_r7a[~nan_pnl_mask])
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

    # Regression diagnostics (C-se-rcw on the R7-C-clean row-set)
    train_reg_diag_rcw = compute_regression_diagnostic(pnl_train_for_reg_rcw, train_pred_rcw)
    val_reg_diag_rcw = compute_regression_diagnostic(pnl_val_rcw, val_pred_rcw)
    test_reg_diag_rcw = compute_regression_diagnostic(pnl_test_rcw, test_pred_rcw)

    # Score per cell
    val_score_s_e_rcw = val_pred_rcw
    test_score_s_e_rcw = test_pred_rcw
    val_score_s_e_r7a = val_pred_r7a
    test_score_s_e_r7a = test_pred_r7a
    val_score_s_b_raw = compute_picker_score_s_b_raw(val_raw_probs)
    test_score_s_b_raw = compute_picker_score_s_b_raw(test_raw_probs)

    # Top-tail regime audit on val rcw (DIAGNOSTIC-ONLY)
    print("Computing top-tail regime audit (NEW 27.0f; DIAGNOSTIC-ONLY)...")
    top_tail_regime_audit = compute_top_tail_regime_audit(
        val_score_s_e_rcw,
        val_df_rcw[list(R7_C_FEATURES)],
        q_list=TOP_TAIL_AUDIT_Q_PERCENTS,
    )

    # NEW item 17 + 18 — on R7-C-clean train (C-se-rcw row-set; clean R7-C feature dist)
    r7_c_feature_distribution_train = _compute_r7_c_feature_distribution_train(train_df_rcw)
    per_pair_r7_c_stats = _compute_per_pair_r7_c_stats(train_df_rcw, args.pairs)

    # Trade-count budget audit on C-se-rcw row-set
    trade_count_budget_audit_c_se_rcw = compute_trade_count_budget_audit(
        val_score_s_e_rcw, QUANTILE_PERCENTS_27_0F
    )

    # Build cells
    cells = build_s_e_r7_c_cells()

    # Update sanity probe with post-fit + NEW 27.0f items (R7-C-clean for rcw artifacts)
    sanity_post = run_sanity_probe_27_0f(
        train_df_rcw,
        val_df_rcw,
        test_df_rcw,
        pair_runtime_map,
        args.pairs,
        days=args.days,
        pnl_train_full=pnl_train_rcw,
        val_pred_rcw=val_pred_rcw,
        test_pred_rcw=test_pred_rcw,
        train_pred_rcw=train_pred_rcw,
        fold_idx=fold_idx,
        oof_corr_diag=oof_corr_diag_rcw,
        train_reg_diag=train_reg_diag_rcw,
        val_reg_diag=val_reg_diag_rcw,
        test_reg_diag=test_reg_diag_rcw,
        regressor_feature_importance_rcw=regressor_feature_importance_rcw,
        regressor_feature_importance_r7a=regressor_feature_importance_r7a,
        train_drop_for_nan_pnl_count=nan_pnl_count,
        r7_c_drop_stats=drop_stats_r7c,
        r7_c_feature_distribution_train=r7_c_feature_distribution_train,
        per_pair_r7_c_stats=per_pair_r7_c_stats,
        top_tail_regime_audit=top_tail_regime_audit,
        volume_preflight_diag=volume_preflight_diag,
        cell_definitions=cells,
        trade_count_budget_audit_c_se_rcw=trade_count_budget_audit_c_se_rcw,
    )
    sanity = sanity_post

    # Per-cell evaluation — Fix A: each cell on its own row-set
    n_cells_run = len(cells)
    cell_results: list[dict] = []
    # Pre-compute rcw-aligned raw probs (multiclass trained on R7-A-clean; subset for rcw cell
    # diagnostics so cls_diag aligns with rcw row-set).
    val_raw_probs_rcw = val_raw_probs[val_r7c_keep]
    test_raw_probs_rcw = test_raw_probs[test_r7c_keep]
    for i, cell in enumerate(cells):
        t_cell = time.time()
        if cell["score_type"] == "s_e_r7ac":
            # C-se-rcw — R7-C-clean row-set
            td, vd, ttd = train_df_rcw, val_df_rcw, test_df_rcw
            tl, vl, ttl = train_label_rcw, val_label_rcw, test_label_rcw
            vp, tp = val_raw_probs_rcw, test_raw_probs_rcw
            val_score, test_score = val_score_s_e_rcw, test_score_s_e_rcw
            pnl_v, pnl_t = pnl_val_rcw, pnl_test_rcw
            fi = regressor_feature_importance_rcw
        elif cell["score_type"] == "s_e_r7a":
            # C-se-r7a-replica — R7-A-clean row-set
            td, vd, ttd = train_df, val_df, test_df
            tl, vl, ttl = train_label_r7a, val_label_r7a, test_label_r7a
            vp, tp = val_raw_probs, test_raw_probs
            val_score, test_score = val_score_s_e_r7a, test_score_s_e_r7a
            pnl_v, pnl_t = pnl_val_full, pnl_test_full
            fi = regressor_feature_importance_r7a
        elif cell["score_type"] == "s_b_raw":
            # C-sb-baseline — R7-A-clean row-set (preserves 27.0b reproduction)
            td, vd, ttd = train_df, val_df, test_df
            tl, vl, ttl = train_label_r7a, val_label_r7a, test_label_r7a
            vp, tp = val_raw_probs, test_raw_probs
            val_score, test_score = val_score_s_b_raw, test_score_s_b_raw
            pnl_v, pnl_t = pnl_val_full, pnl_test_full
            fi = compute_feature_importance_diagnostic(multiclass_pipeline)
        else:
            raise ValueError(f"Unknown score_type: {cell['score_type']}")
        try:
            result = evaluate_cell_27_0f(
                cell,
                td,
                vd,
                ttd,
                tl,
                vl,
                ttl,
                vp,
                tp,
                val_score,
                test_score,
                pnl_v,
                pnl_t,
                fi,
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
            f"  cell {i + 1}/{n_cells_run} {cell['id']} | "
            f"q*={result.get('selected_q_percent', '-')} "
            f"val_sharpe={result.get('val_realised_sharpe', float('nan')):+.3f} "
            f"val_n={result.get('val_n_trades', 0):>6} | "
            f"test_sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"test_n={rm.get('n_trades', 0):>6} "
            f"test_sp={sp:+.4f} | ({time.time() - t_cell:.1f}s)"
        )

    # C-sb-baseline match check (FAIL-FAST per inheritance)
    print("\n=== C-sb-baseline match check (per 27.0f-α §7.1) ===")
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

    # C-se-r7a-replica drift check (DIAGNOSTIC-ONLY WARN; NOT HALT)
    print("\n=== C-se-r7a-replica drift check vs 27.0d C-se (DIAGNOSTIC-ONLY WARN) ===")
    c_se_r7a_replica = next(
        (c for c in cell_results if c["cell"]["id"] == "C-se-r7a-replica"), None
    )
    if c_se_r7a_replica is None or c_se_r7a_replica.get("h_state") != "OK":
        r7a_replica_drift_report = {
            "source": "n/a",
            "warn": True,
            "all_within_tolerance": False,
            "note": "C-se-r7a-replica not present or h_state != OK",
        }
    else:
        r7a_replica_drift_report = compute_c_se_r7a_replica_drift_check(c_se_r7a_replica)
        if r7a_replica_drift_report["warn"]:
            warnings.warn(
                f"C-se-r7a-replica drift vs 27.0d C-se exceeds tolerance "
                f"(n_trades={r7a_replica_drift_report.get('n_trades_within_tolerance')}, "
                f"Sharpe={r7a_replica_drift_report.get('sharpe_within_tolerance')}, "
                f"ann_pnl={r7a_replica_drift_report.get('ann_pnl_within_tolerance')}); "
                "DIAGNOSTIC-ONLY WARN per D-AA11 (NOT HALT)",
                UserWarning,
                stacklevel=2,
            )
        print(f"  drift WARN: {r7a_replica_drift_report.get('warn')}")
        print(f"  all_within_tolerance: {r7a_replica_drift_report.get('all_within_tolerance')}")

    # Val-selection + verdict + cross-cell
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

    # H-B6 falsification outcome
    h_b6_outcome = compute_h_b6_falsification_outcome(cell_results)
    print(
        f"=== H-B6 outcome: {h_b6_outcome['h_b6_outcome']} (row {h_b6_outcome['row_matched']}) ==="
    )
    print(f"=== Routing implication: {h_b6_outcome['routing_implication']} ===")

    if args.no_write:
        print("\n--no-write set; skipping artifact write.")
        return 0

    # Predicted PnL distribution for C-se-rcw
    predicted_pnl_distribution_rcw: dict[str, dict] = {}
    for split_name, pred in [
        ("train", train_pred_rcw),
        ("val", val_pred_rcw),
        ("test", test_pred_rcw),
    ]:
        finite = pred[np.isfinite(pred)]
        if len(finite) == 0:
            predicted_pnl_distribution_rcw[split_name] = {"n_finite": 0}
            continue
        predicted_pnl_distribution_rcw[split_name] = {
            "n_finite": int(len(finite)),
            "mean": float(finite.mean()),
            "p5": float(np.quantile(finite, 0.05)),
            "p50": float(np.quantile(finite, 0.50)),
            "p95": float(np.quantile(finite, 0.95)),
        }

    target_pnl_distribution = sanity.get("target_pnl_distribution_train", {})

    # Write 25-section eval report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report_27_0f(
        report_path,
        cell_results,
        val_select,
        verdict_info,
        aggregate_info,
        baseline_match_report,
        r7a_replica_drift_report,
        sanity,
        drop_stats_r7a,
        drop_stats_r7c,
        (t_min, t70, t85, t_max),
        preflight_diag,
        n_cells_run,
        regressor_feature_importance_rcw,
        regressor_feature_importance_r7a,
        train_reg_diag_rcw,
        val_reg_diag_rcw,
        test_reg_diag_rcw,
        oof_corr_diag_rcw,
        target_pnl_distribution,
        predicted_pnl_distribution_rcw,
        h_b6_outcome,
        top_tail_regime_audit,
    )
    print(f"\nReport: {report_path}")

    # Persist artifacts
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
                "feature_set": cell.get("feature_set", "-"),
                "quantile_percents": list(cell.get("quantile_percents", ())),
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
    aggregate["r7a_replica_drift_report"] = r7a_replica_drift_report
    aggregate["n_cells_run"] = n_cells_run
    aggregate["regression_diagnostic_rcw"] = {
        "train": train_reg_diag_rcw,
        "val": val_reg_diag_rcw,
        "test": test_reg_diag_rcw,
    }
    aggregate["oof_correlation_diagnostic_rcw"] = oof_corr_diag_rcw
    aggregate["h_b6_outcome"] = h_b6_outcome
    aggregate["top_tail_regime_audit"] = top_tail_regime_audit
    aggregate["c_se_rcw_quantile_percents"] = list(QUANTILE_PERCENTS_27_0F)
    aggregate["c_se_r7a_replica_quantile_percents"] = list(QUANTILE_PERCENTS_27_0F)
    aggregate["c_sb_baseline_quantile_percents"] = list(QUANTILE_PERCENTS_27_0F)
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
