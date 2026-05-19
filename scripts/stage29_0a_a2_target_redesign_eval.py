"""Stage 29.0a-β A2 Target Redesign eval (Phase 29 first sub-phase).

Implements PR #350 (Phase 29.0a-α A2 design memo) under PR #348 (Phase 29
kickoff Scope III + Policy C + Option 9c) + PR #349 (post-kickoff routing
review primary recommendation: Path 2 A2 alone).

Mission (PR #350 §1):
  Phase 29.0a tests A2 (target redesign) as the Phase 29 first sub-phase.
  The hypothesis is that the triple-barrier realised-PnL target's
  specification (K_FAV=1.5/K_ADV=1.0/H_M1=60) is the binding constraint
  on Sharpe lift across the 8-eval picture.

Closed 4-target allowlist (α-fixed per PR #350 §4; NG#A2-1; all D-1 PASS):
  T1 fixed-horizon executable close PnL (H_M1=60; no TP/SL barrier;
    long entry=ask_o + exit=bid_c; short entry=bid_o + exit=ask_c)
  T2 time-weighted realised PnL (linear decay (1 - hold_bars / H_M1);
    K_FAV=1.5/K_ADV=1.0/H_M1=60 inherited)
  T3 multi-horizon realised PnL (horizons {30, 60, 120};
    K_FAV=1.5/K_ADV=1.0 unchanged; absorbs R-T3 carry-forward)
  T4 asymmetric barrier PnL (K_FAV=2.0/K_ADV=0.5/H_M1=60)

Fixed non-target axes (NG#A2-1):
  - R7-A feature surface (4 features)
  - tabular LightGBM single regressor (27.0d C-se backbone)
  - top-q on score selection (quantile family {5,10,20,30,40})
  - symmetric Huber α=0.9 loss
  - sample_weight=1

6-cell structure (PR #350 §7; NG#A2-3 mandatory C-d1-target-control):
  C-d1-T1, C-d1-T2, C-d1-T3, C-d1-T4 — 4 substantive A2 cells
  C-d1-target-control — target-axis null; reproduces 27.0d C-se on
    inherited triple-barrier 1.5/1.0 target (6th anchor in bit-tight
    reproduction chain: 27.0d → 27.0f → 28.0a → 28.0b → 28.0c → 29.0a)
  C-d1-Tx-baseline (×4) — Phase 29 §10 per-target baseline; S-B raw +
    top-q q=5 + target Tx-specific realised PnL

H-D1 4-outcome ladder per target (PR #350 §10; precedence row 4 > 1 > 2 > 3):
  Row 4 PARTIAL_DRIFT_TARGET_REPLICA (checked FIRST per NG#A2-3):
    C-d1-Tx ≈ C-d1-target-control (val-selected q*) within tolerance
    (n_trades ±100 / Sharpe ±5e-3 / ann_pnl ±0.5%); target had zero
    effect vs inherited triple-barrier
  Row 1 PASS: H2 PASS (val Sharpe lift ≥ +0.05 vs Phase 29 §10 per-target
    baseline) AND H1m ≥ +0.30 AND H3 ≥ 20,000 trades AND
    per-target baseline FAIL-FAST internal-consistency PASS
  Row 2 PARTIAL_SUPPORT: val Sharpe lift ∈ [+0.02, +0.05); others intact
  Row 3 FALSIFIED_TARGET_INSUFFICIENT (default): val Sharpe lift < +0.02
    OR other H-D1 conditions fail

Aggregate verdict (PR #350 §11; FALSIFIED_A2_NARROW distinction):
  any AR PASS → SPLIT_VERDICT_ROUTE_TO_REVIEW
  0 PASS + 1+ PARTIAL_SUPPORT → REJECT_NON_DISCRIMINATIVE (sub-threshold)
  all 4 FALSIFIED or PARTIAL_DRIFT → REJECT_NON_DISCRIMINATIVE +
    diagnostic FALSIFIED_A2_NARROW (NEVER FALSIFIED_ALL_A2; alternate
    target framings outside closed 4-target allowlist remain admissible
    via separate scope amendment)

R-T3 absorption (PR #350 §2.5): T3 multi-horizon variant absorbs the
long-standing R-T3 carry-forward (Phase 27 §11 / PR #347 §12). R-T3
standalone elevation NOT admissible.

Phase 29 §10 baseline reference policy (PR #350 §8; Option 9c):
  - Phase 28 §10 numeric (n=34626 / Sharpe -0.1732 / ann_pnl -204664.4 /
    val Sharpe -0.1863) immutable; never retroactively modified;
    inherited as DIAGNOSTIC-ONLY 2nd reference
  - Phase 29 §10 baseline reference defined per target Tx via
    C-d1-Tx-baseline cell (S-B raw + top-q q=5 + target Tx-specific
    realised PnL); persisted to
    artifacts/stage29_0a/phase29_section10_per_target_baseline.json
  - FAIL-FAST = internal-consistency check (per-target baseline
    consistency); n_trades exact / Sharpe ±1e-4 / ann_pnl ±0.5 pip
  - External comparison vs archived Phase 28 §10 = DIAGNOSTIC-ONLY only

Anti-collapse guards (PR #350 §9):
  NG#A2-1: closed 4-target allowlist; no 5th; no numeric grid within
    variant; fixed non-target axes; no joint admission; no DIAGNOSTIC-ONLY
    variants
  NG#A2-2: per-target verdict required; aggregate-only NOT admissible
  NG#A2-3: C-d1-target-control mandatory; 6-phase bit-tight reproduction
    chain extension

MANDATORY CLAUSES (inherited verbatim from PR #348 §16; Clause 6 = Phase 29
scope):

1. Phase framing — ADOPT requires H2 PASS + full 8-gate A0-A5 harness.
   H2 PASS = PROMISING_BUT_NEEDS_OOS only; ADOPT_CANDIDATE wall preserved.
2. Diagnostic columns prohibition — calibration / threshold-sweep /
   directional-comparison / classification-quality / feature-importance /
   per-pair-Sharpe-contribution columns are diagnostic-only. 29.0a
   extension: per-target distribution diagnostics, T3 overlap rate
   (WARN-only), within-eval drift vs target-control, top-tail regime
   audit (spread_at_signal_pip only).
3. γ closure PR #279 preserved.
4. Production-readiness preservation — X-v2 OOS gating required; v9
   20-pair (Phase 9.12 tip 79ed1e8) untouched; Phase 22 frozen-OOS
   contract preserved.
5. NG#10 / NG#11 not relaxed.
6. Phase 29 scope (NEW for Phase 29) — Phase 29 is a structural rebase
   opened after Phase 28 closure (PR #347). Phase 29 admissibility =
   Scope III (A0-broad / A2 / R-B / A3 all admissible at kickoff;
   PR #348 §6). Joint-axis = Policy C hybrid (single-axis default;
   PR #348 §7). Baseline reference = Option 9c dual reference
   (PR #348 §9; Phase 28 §10 archived immutable; Phase 29 may define
   new per sub-phase α). Phase 27/28 inertia routes NOT admissible
   without explicit scope amendment (PR #348 §11). 29.0a-β tests A2
   only per PR #349 routing review primary recommendation.

PRODUCTION-MISUSE GUARDS (inherited verbatim):
GUARD 1 — research-not-production: 29.0a features stay in scripts/.
GUARD 2 — threshold-sweep-diagnostic.
GUARD 3 — directional-comparison-diagnostic.

QUICK-MODE WARNING:
  --quick-mode reduces row count for fast iteration; formal verdict
  NOT valid in quick mode (NG#A2-* enforcement requires full 730-day /
  20-pair scope).
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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage29_0a"
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
stage28_0c = importlib.import_module("stage28_0c_a0_architecture_topology_eval")

# Inherited constants and helpers
PAIRS_20 = stage23_0a.PAIRS_20
load_m1_ba = stage23_0a.load_m1_ba
pip_size_for = stage23_0a.pip_size_for

_compute_realised_barrier_pnl_inherited = stage25_0b._compute_realised_barrier_pnl
compute_8_gate_metrics = stage25_0b.compute_8_gate_metrics
gate_matrix = stage25_0b.gate_matrix
LOW_POWER_N_TEST = stage25_0b.LOW_POWER_N_TEST
LOW_POWER_N_TRAIN = stage25_0b.LOW_POWER_N_TRAIN
SPAN_DAYS = stage25_0b.SPAN_DAYS
SPAN_YEARS = SPAN_DAYS / 365.25
TRAIN_FRAC = stage25_0b.TRAIN_FRAC
VAL_FRAC = stage25_0b.VAL_FRAC
split_70_15_15 = stage25_0b.split_70_15_15

precompute_realised_pnl_per_row_inherited = stage26_0b.precompute_realised_pnl_per_row
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

_multiclass_to_class_probs = stage28_0c._multiclass_to_class_probs


# ---------------------------------------------------------------------------
# Inherited binding constants
# ---------------------------------------------------------------------------

K_FAV_INHERITED = stage25_0b.K_FAV  # 1.5
K_ADV_INHERITED = stage25_0b.K_ADV  # 1.0
H_M1_BARS_INHERITED = stage25_0b.H_M1_BARS  # 60

LABEL_TP = stage26_0c.LABEL_TP
LABEL_SL = stage26_0c.LABEL_SL
LABEL_TIME = stage26_0c.LABEL_TIME
NUM_CLASSES = stage26_0c.NUM_CLASSES

NUMERIC_FEATURES_R7A = stage26_0d.NUMERIC_FEATURES
ALL_FEATURES_R7A = stage26_0d.ALL_FEATURES  # 4 features: pair + direction + atr + spread
CATEGORICAL_COLS = stage26_0d.CATEGORICAL_COLS

LIGHTGBM_REGRESSION_CONFIG = stage27_0d.LIGHTGBM_REGRESSION_CONFIG
HUBER_ALPHA = stage27_0d.HUBER_ALPHA  # 0.9
LIGHTGBM_MULTICLASS_CONFIG = stage27_0d.LIGHTGBM_MULTICLASS_CONFIG

H1_WEAK_THRESHOLD = stage26_0c.H1_WEAK_THRESHOLD
H1_MEANINGFUL_THRESHOLD = stage26_0c.H1_MEANINGFUL_THRESHOLD
H3_REFERENCE_SHARPE = stage26_0c.H3_REFERENCE_SHARPE

CONCENTRATION_HIGH_THRESHOLD = stage26_0c.CONCENTRATION_HIGH_THRESHOLD
SANITY_MIN_CLASS_SHARE = stage26_0c.SANITY_MIN_CLASS_SHARE
SANITY_MAX_PER_PAIR_TIME_SHARE = stage26_0c.SANITY_MAX_PER_PAIR_TIME_SHARE
SANITY_MAX_NEW_FEATURE_NAN_RATE = stage26_0d.SANITY_MAX_NEW_FEATURE_NAN_RATE
SANITY_MAX_POSITIVITY_VIOLATION_RATE = stage26_0d.SANITY_MAX_POSITIVITY_VIOLATION_RATE

TEST_SPAN_YEARS = SPAN_YEARS * (1.0 - TRAIN_FRAC - VAL_FRAC)
VAL_SPAN_YEARS = SPAN_YEARS * VAL_FRAC

OOF_N_FOLDS = stage27_0c.OOF_N_FOLDS
OOF_SEED = stage27_0c.OOF_SEED

# Archived Phase 28 §10 baseline reference (immutable; DIAGNOSTIC-ONLY 2nd reference per Option 9c)
ARCHIVED_PHASE_28_SECTION10_N_TRADES = stage27_0d.BASELINE_27_0B_C_ALPHA0_N_TRADES  # 34626
ARCHIVED_PHASE_28_SECTION10_SHARPE = stage27_0d.BASELINE_27_0B_C_ALPHA0_SHARPE  # -0.1732
ARCHIVED_PHASE_28_SECTION10_ANN_PNL = stage27_0d.BASELINE_27_0B_C_ALPHA0_ANN_PNL  # -204664.4
ARCHIVED_PHASE_28_SECTION10_VAL_SHARPE = -0.1863  # PR #335 §10 verbatim

# Per-target baseline FAIL-FAST tolerances (inherited; internal consistency check only)
PER_TARGET_BASELINE_N_TRADES_TOLERANCE = 0  # exact
PER_TARGET_BASELINE_SHARPE_ABS_TOLERANCE = 1e-4
PER_TARGET_BASELINE_ANN_PNL_ABS_TOLERANCE = 0.5

NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD = stage27_0d.NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD


# ---------------------------------------------------------------------------
# NEW Phase 29.0a-β constants (closed 4-target allowlist; α-fixed per PR #350 §4)
# ---------------------------------------------------------------------------

# T1 fixed-horizon executable close PnL (PR #350 §4.1)
T1_H_M1 = 60  # α-fixed; no horizon grid

# T2 time-weighted realised PnL (PR #350 §4.2)
T2_K_FAV = 1.5  # inherited
T2_K_ADV = 1.0  # inherited
T2_H_M1 = 60  # α-fixed
T2_DECAY_KIND = "linear"  # α-fixed; no decay-shape grid

# T3 multi-horizon realised PnL (PR #350 §4.3; absorbs R-T3)
T3_K_FAV = 1.5  # inherited
T3_K_ADV = 1.0  # inherited
T3_HORIZONS: tuple[int, ...] = (30, 60, 120)  # α-fixed; no horizon-set grid
T3_OVERLAP_WARN_RATE = 0.10  # DIAGNOSTIC-ONLY WARN if overlap rate > 10%

# T4 asymmetric K_FAV / K_ADV (PR #350 §4.4)
T4_K_FAV = 2.0  # α-fixed
T4_K_ADV = 0.5  # α-fixed
T4_H_M1 = 60  # α-fixed

# Target-control inherited (NG#A2-3; reproduces 27.0d C-se baseline target)
TARGET_CONTROL_K_FAV = K_FAV_INHERITED  # 1.5
TARGET_CONTROL_K_ADV = K_ADV_INHERITED  # 1.0
TARGET_CONTROL_H_M1 = H_M1_BARS_INHERITED  # 60

# Quantile family (PR #350 §7; inherited)
QUANTILE_PERCENTS_29_0A: tuple[float, ...] = (5.0, 10.0, 20.0, 30.0, 40.0)
PER_TARGET_BASELINE_Q_PERCENT = 5.0  # α-fixed q=5 for per-target baselines

# H-D1 thresholds (PR #350 §10)
H2_LIFT_THRESHOLD_PASS = 0.05
H2_LIFT_THRESHOLD_PARTIAL_SUPPORT_LO = 0.02
H1M_PRESERVE_THRESHOLD = 0.30
H3_TRADE_COUNT_THRESHOLD = 20000

# H-D1 outcome labels (PR #350 §10)
H_D1_OUTCOME_PASS = "PASS"
H_D1_OUTCOME_PARTIAL_SUPPORT = "PARTIAL_SUPPORT"
H_D1_OUTCOME_FALSIFIED_TARGET_INSUFFICIENT = "FALSIFIED_TARGET_INSUFFICIENT"
H_D1_OUTCOME_PARTIAL_DRIFT_TARGET_REPLICA = "PARTIAL_DRIFT_TARGET_REPLICA"
H_D1_OUTCOME_NEEDS_REVIEW = "NEEDS_REVIEW"

# C-d1-target-control drift vs 27.0d C-se tolerances (DIAGNOSTIC-ONLY WARN)
TARGET_CONTROL_DRIFT_N_TRADES_TOLERANCE = 100
TARGET_CONTROL_DRIFT_SHARPE_TOLERANCE = 5e-3
TARGET_CONTROL_DRIFT_ANN_PNL_FRAC_TOLERANCE = 0.005

# Within-eval drift tolerances (NG#A2-3; same as target-control)
WITHIN_EVAL_DRIFT_N_TRADES_TOLERANCE = 100
WITHIN_EVAL_DRIFT_SHARPE_TOLERANCE = 5e-3
WITHIN_EVAL_DRIFT_ANN_PNL_FRAC_TOLERANCE = 0.005

# Top-tail regime audit q values (spread_at_signal_pip only)
TOP_TAIL_AUDIT_Q_PERCENTS: tuple[float, ...] = (10.0, 20.0)


# ---------------------------------------------------------------------------
# NEW exceptions
# ---------------------------------------------------------------------------


class PerTargetBaselineMismatchError(RuntimeError):
    """Raised when per-target baseline internal-consistency check fails.

    Per PR #350 §8.4. FAIL-FAST HALT.
    """


class TargetPrecomputeError(RuntimeError):
    """Raised when a per-target PnL precompute fails (excessive NaN-PnL).

    Per PR #350 §16 NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD inheritance.
    """


# ---------------------------------------------------------------------------
# Parameterised barrier PnL (for T2 / T3 / T4 / target-control)
# ---------------------------------------------------------------------------


def _compute_realised_barrier_pnl_parameterised(
    pair: str,
    signal_ts: pd.Timestamp,
    direction: str,
    atr_pip: float,
    pair_data: dict,
    k_fav: float,
    k_adv: float,
    h_m1: int,
) -> tuple[float | None, int | None]:
    """Parameterised barrier PnL with explicit K_FAV / K_ADV / H_M1.

    Per PR #350 §3 target primitives. Mirrors stage25_0b._compute_realised_
    barrier_pnl semantics with K_FAV / K_ADV / H_M1 as explicit parameters
    rather than module-level constants. Returns (pnl_pip, hold_bars) where
    hold_bars is the M1-bar count from entry to barrier resolution (TP / SL
    / TIME), or (None, None) if path window is invalid.

    Used by T2 (decay factor = 1 - hold_bars / H_M1), T3 (per-horizon sum;
    hold_bars discarded; pnl summed), T4 (K_FAV=2.0 / K_ADV=0.5), and
    target-control (K_FAV=1.5 / K_ADV=1.0 / H_M1=60 inherited).
    """
    pip = pair_data["pip"]
    m1_pos = pair_data["m1_pos"]
    target_entry_ts = signal_ts + pd.Timedelta(minutes=1)
    if target_entry_ts not in m1_pos.index:
        return None, None
    entry_idx = int(m1_pos.loc[target_entry_ts])
    path_end = entry_idx + h_m1
    if path_end > pair_data["n_m1"]:
        return None, None
    fav_thresh_pip = k_fav * atr_pip
    adv_thresh_pip = k_adv * atr_pip
    if direction == "long":
        entry_ask = float(pair_data["ask_o"][entry_idx])
        bid_h = pair_data["bid_h"][entry_idx:path_end]
        bid_l = pair_data["bid_l"][entry_idx:path_end]
        bid_c = pair_data["bid_c"][entry_idx:path_end]
        fav_excursion_pip = (bid_h - entry_ask) / pip
        adv_excursion_pip = (entry_ask - bid_l) / pip
    else:
        entry_bid = float(pair_data["bid_o"][entry_idx])
        ask_h = pair_data["ask_h"][entry_idx:path_end]
        ask_l = pair_data["ask_l"][entry_idx:path_end]
        ask_c = pair_data["ask_c"][entry_idx:path_end]
        fav_excursion_pip = (entry_bid - ask_l) / pip
        adv_excursion_pip = (ask_h - entry_bid) / pip
    fav_hit = fav_excursion_pip >= fav_thresh_pip
    adv_hit = adv_excursion_pip >= adv_thresh_pip
    first_fav = int(np.argmax(fav_hit)) if bool(fav_hit.any()) else -1
    first_adv = int(np.argmax(adv_hit)) if bool(adv_hit.any()) else -1
    if first_fav >= 0 and first_adv >= 0:
        if first_adv <= first_fav:  # same-bar => adverse first; or strict adverse-first
            return -adv_thresh_pip, int(first_adv + 1)
        return fav_thresh_pip, int(first_fav + 1)
    if first_adv >= 0:
        return -adv_thresh_pip, int(first_adv + 1)
    if first_fav >= 0:
        return fav_thresh_pip, int(first_fav + 1)
    # Horizon expiry → mark-to-market (close at t+H-1 minus entry, in pips)
    if direction == "long":
        return float((bid_c[-1] - entry_ask) / pip), int(h_m1)
    return float((entry_bid - ask_c[-1]) / pip), int(h_m1)


# ---------------------------------------------------------------------------
# T1 — Fixed-horizon executable close PnL (PR #350 §4.1)
# ---------------------------------------------------------------------------


def _compute_target_t1_fixed_horizon_close_pnl(
    pair: str,
    signal_ts: pd.Timestamp,
    direction: str,
    atr_pip: float,
    pair_data: dict,
    h_m1: int = T1_H_M1,
) -> float | None:
    """T1: fixed-horizon executable close PnL (no TP/SL barrier).

    Per PR #350 §4.1:
      - Entry at signal_ts + 1 minute, using D-1 executable side
        (long entry = ask_o; short entry = bid_o)
      - Exit at entry + H_M1 = 60 M1 bars (no path-dependent early exit;
        no barrier)
      - Exit price (D-1 executable):
        long exit = bid_c (long exit hits the bid)
        short exit = ask_c (short exit pays the ask)
      - PnL pip-denominated per pair

    Returns scalar pnl_t1, or None if path window is invalid.
    """
    pip = pair_data["pip"]
    m1_pos = pair_data["m1_pos"]
    target_entry_ts = signal_ts + pd.Timedelta(minutes=1)
    if target_entry_ts not in m1_pos.index:
        return None
    entry_idx = int(m1_pos.loc[target_entry_ts])
    exit_idx = entry_idx + h_m1
    if exit_idx >= pair_data["n_m1"]:
        return None
    if direction == "long":
        entry_price = float(pair_data["ask_o"][entry_idx])
        exit_price = float(pair_data["bid_c"][exit_idx])
        return float((exit_price - entry_price) / pip)
    # short
    entry_price = float(pair_data["bid_o"][entry_idx])
    exit_price = float(pair_data["ask_c"][exit_idx])
    return float((entry_price - exit_price) / pip)


# ---------------------------------------------------------------------------
# T2 — Time-weighted realised PnL (PR #350 §4.2)
# ---------------------------------------------------------------------------


def _compute_target_t2_time_weighted_pnl(
    pair: str,
    signal_ts: pd.Timestamp,
    direction: str,
    atr_pip: float,
    pair_data: dict,
    k_fav: float = T2_K_FAV,
    k_adv: float = T2_K_ADV,
    h_m1: int = T2_H_M1,
) -> float | None:
    """T2: inherited triple-barrier PnL × linear decay factor.

    Per PR #350 §4.2:
      pnl_t2 = pnl_barrier × (1 - hold_bars / H_M1)
    where pnl_barrier is the inherited K_FAV=1.5 / K_ADV=1.0 / H_M1=60
    triple-barrier executable PnL and hold_bars is the M1-bar count from
    entry to barrier resolution. Decay factor clamped to [0, 1].

    Returns scalar pnl_t2, or None if path window is invalid.
    """
    pnl_barrier, hold_bars = _compute_realised_barrier_pnl_parameterised(
        pair, signal_ts, direction, atr_pip, pair_data, k_fav, k_adv, h_m1
    )
    if pnl_barrier is None or hold_bars is None:
        return None
    decay_factor = 1.0 - (hold_bars / h_m1)
    if decay_factor < 0.0:
        decay_factor = 0.0
    elif decay_factor > 1.0:
        decay_factor = 1.0
    return float(pnl_barrier * decay_factor)


# ---------------------------------------------------------------------------
# T3 — Multi-horizon realised PnL (PR #350 §4.3; absorbs R-T3)
# ---------------------------------------------------------------------------


def _compute_target_t3_multi_horizon_pnl(
    pair: str,
    signal_ts: pd.Timestamp,
    direction: str,
    atr_pip: float,
    pair_data: dict,
    horizons: tuple[int, ...] = T3_HORIZONS,
    k_fav: float = T3_K_FAV,
    k_adv: float = T3_K_ADV,
) -> float | None:
    """T3: multi-horizon realised PnL summed across {30, 60, 120}.

    Per PR #350 §4.3:
      pnl_t3 = pnl_H_30 + pnl_H_60 + pnl_H_120
    where each pnl_H_i is the inherited K_FAV=1.5 / K_ADV=1.0 / H_M1=H_i
    triple-barrier executable PnL.

    Returns scalar pnl_t3 (sum), or None if any horizon's path window is
    invalid (the longest horizon H=120 is the limiting factor).
    """
    total = 0.0
    for h_i in horizons:
        pnl_h_i, _ = _compute_realised_barrier_pnl_parameterised(
            pair, signal_ts, direction, atr_pip, pair_data, k_fav, k_adv, h_i
        )
        if pnl_h_i is None:
            return None
        total += pnl_h_i
    return float(total)


# ---------------------------------------------------------------------------
# T4 — Asymmetric K_FAV / K_ADV barrier PnL (PR #350 §4.4)
# ---------------------------------------------------------------------------


def _compute_target_t4_asymmetric_barrier_pnl(
    pair: str,
    signal_ts: pd.Timestamp,
    direction: str,
    atr_pip: float,
    pair_data: dict,
    k_fav: float = T4_K_FAV,
    k_adv: float = T4_K_ADV,
    h_m1: int = T4_H_M1,
) -> float | None:
    """T4: asymmetric K_FAV=2.0 / K_ADV=0.5 triple-barrier executable PnL.

    Per PR #350 §4.4:
      Same harness as 27.0d; different barrier multipliers.

    Returns scalar pnl_t4, or None if path window is invalid.
    """
    pnl, _ = _compute_realised_barrier_pnl_parameterised(
        pair, signal_ts, direction, atr_pip, pair_data, k_fav, k_adv, h_m1
    )
    if pnl is None:
        return None
    return float(pnl)


# ---------------------------------------------------------------------------
# Target-control: inherited triple-barrier 1.5/1.0 PnL (NG#A2-3)
# ---------------------------------------------------------------------------


def _compute_target_control_inherited_pnl(
    pair: str,
    signal_ts: pd.Timestamp,
    direction: str,
    atr_pip: float,
    pair_data: dict,
    k_fav: float = TARGET_CONTROL_K_FAV,
    k_adv: float = TARGET_CONTROL_K_ADV,
    h_m1: int = TARGET_CONTROL_H_M1,
) -> float | None:
    """Target-control: inherited K_FAV=1.5 / K_ADV=1.0 / H_M1=60 PnL.

    Reproduces 27.0d C-se / 27.0f r7a-replica / 28.0a r7a-replica / 28.0b
    top-q-control / 28.0c arch-control as the 6th anchor in the bit-tight
    reproduction chain (PR #350 §6 / §9.3 NG#A2-3).
    """
    pnl, _ = _compute_realised_barrier_pnl_parameterised(
        pair, signal_ts, direction, atr_pip, pair_data, k_fav, k_adv, h_m1
    )
    if pnl is None:
        return None
    return float(pnl)


# ---------------------------------------------------------------------------
# Shared target precompute orchestrator
# ---------------------------------------------------------------------------


def precompute_target_pnls_per_row(
    df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    target_kind: str,
) -> np.ndarray:
    """Compute per-row PnL for a specific target variant.

    target_kind ∈ {"T1", "T2", "T3", "T4", "TARGET_CONTROL"}.

    Returns np.ndarray of length len(df); NaN where path window is invalid.
    """
    n = len(df)
    out = np.full(n, np.nan, dtype=np.float64)
    pairs = df["pair"].to_numpy()
    signal_ts = df["signal_ts"].to_numpy()
    directions = df["direction"].to_numpy()
    atrs = df["atr_at_signal_pip"].to_numpy(dtype=np.float64)

    target_func = {
        "T1": _compute_target_t1_fixed_horizon_close_pnl,
        "T2": _compute_target_t2_time_weighted_pnl,
        "T3": _compute_target_t3_multi_horizon_pnl,
        "T4": _compute_target_t4_asymmetric_barrier_pnl,
        "TARGET_CONTROL": _compute_target_control_inherited_pnl,
    }.get(target_kind)
    if target_func is None:
        raise ValueError(
            f"Unknown target_kind: {target_kind}; must be one of T1 / T2 / T3 / T4 / TARGET_CONTROL"
        )

    for i in range(n):
        pr = pair_runtime_map.get(str(pairs[i]))
        if pr is None:
            continue
        r = target_func(
            str(pairs[i]),
            pd.Timestamp(signal_ts[i]),
            str(directions[i]),
            float(atrs[i]),
            pr,
        )
        if r is not None:
            out[i] = r
    return out


# ---------------------------------------------------------------------------
# Per-pair runtime (inherited from 28.0c)
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
# Cell construction (PR #350 §7; 6 cells: 4 substantive + 1 target-control + 4 per-target baselines)
# ---------------------------------------------------------------------------


def build_a2_cells() -> list[dict]:
    """29.0a-β formal grid: 6 cell types per PR #350 §7.

    NG#A2-3 mandates C-d1-target-control. Per-target baseline cells
    (C-d1-Tx-baseline) are mandatory and provide the Phase 29 §10
    per-target baseline reference per Option 9c.

    Deterministic order:
      C-d1-T1 → C-d1-T2 → C-d1-T3 → C-d1-T4 → C-d1-target-control
      → C-d1-T1-baseline → C-d1-T2-baseline → C-d1-T3-baseline →
      C-d1-T4-baseline
    """
    return [
        {
            "id": "C-d1-T1",
            "picker": "S-E(per_target_regressor) on T1 fixed-horizon executable close PnL",
            "score_type": "s_e_per_target",
            "feature_set": "r7a",
            "target_kind": "T1",
            "target_params": {"h_m1": T1_H_M1, "no_barrier": True},
            "quantile_percents": QUANTILE_PERCENTS_29_0A,
            "quantile_kind": "family",
            "is_baseline": False,
        },
        {
            "id": "C-d1-T2",
            "picker": "S-E(per_target_regressor) on T2 time-weighted PnL (linear decay)",
            "score_type": "s_e_per_target",
            "feature_set": "r7a",
            "target_kind": "T2",
            "target_params": {
                "k_fav": T2_K_FAV,
                "k_adv": T2_K_ADV,
                "h_m1": T2_H_M1,
                "decay": "linear",
            },
            "quantile_percents": QUANTILE_PERCENTS_29_0A,
            "quantile_kind": "family",
            "is_baseline": False,
        },
        {
            "id": "C-d1-T3",
            "picker": "S-E(per_target_regressor) on T3 multi-horizon PnL (H={30,60,120}); R-T3",
            "score_type": "s_e_per_target",
            "feature_set": "r7a",
            "target_kind": "T3",
            "target_params": {"horizons": list(T3_HORIZONS), "k_fav": T3_K_FAV, "k_adv": T3_K_ADV},
            "quantile_percents": QUANTILE_PERCENTS_29_0A,
            "quantile_kind": "family",
            "is_baseline": False,
        },
        {
            "id": "C-d1-T4",
            "picker": "S-E(per_target_regressor) on T4 asymmetric (K_FAV=2.0/K_ADV=0.5)",
            "score_type": "s_e_per_target",
            "feature_set": "r7a",
            "target_kind": "T4",
            "target_params": {"k_fav": T4_K_FAV, "k_adv": T4_K_ADV, "h_m1": T4_H_M1},
            "quantile_percents": QUANTILE_PERCENTS_29_0A,
            "quantile_kind": "family",
            "is_baseline": False,
        },
        {
            "id": "C-d1-target-control",
            "picker": "S-E(target_control_regressor) on inherited triple-barrier 1.5/1.0",
            "score_type": "s_e_target_control",
            "feature_set": "r7a",
            "target_kind": "TARGET_CONTROL",
            "target_params": {
                "k_fav": TARGET_CONTROL_K_FAV,
                "k_adv": TARGET_CONTROL_K_ADV,
                "h_m1": TARGET_CONTROL_H_M1,
            },
            "quantile_percents": QUANTILE_PERCENTS_29_0A,
            "quantile_kind": "family",
            "is_baseline": False,
        },
        {
            "id": "C-d1-T1-baseline",
            "picker": "S-B raw P(TP)-P(SL) + top-q q=5 on T1 PnL",
            "score_type": "s_b_raw_per_target_baseline",
            "feature_set": "r7a",
            "target_kind": "T1",
            "target_params": {"h_m1": T1_H_M1, "no_barrier": True},
            "quantile_percents": (PER_TARGET_BASELINE_Q_PERCENT,),
            "quantile_kind": "q5_only",
            "is_baseline": True,
        },
        {
            "id": "C-d1-T2-baseline",
            "picker": "S-B raw P(TP)-P(SL) + top-q q=5 on T2 PnL",
            "score_type": "s_b_raw_per_target_baseline",
            "feature_set": "r7a",
            "target_kind": "T2",
            "target_params": {
                "k_fav": T2_K_FAV,
                "k_adv": T2_K_ADV,
                "h_m1": T2_H_M1,
                "decay": "linear",
            },
            "quantile_percents": (PER_TARGET_BASELINE_Q_PERCENT,),
            "quantile_kind": "q5_only",
            "is_baseline": True,
        },
        {
            "id": "C-d1-T3-baseline",
            "picker": "S-B raw P(TP)-P(SL) + top-q q=5 on T3 PnL",
            "score_type": "s_b_raw_per_target_baseline",
            "feature_set": "r7a",
            "target_kind": "T3",
            "target_params": {"horizons": list(T3_HORIZONS), "k_fav": T3_K_FAV, "k_adv": T3_K_ADV},
            "quantile_percents": (PER_TARGET_BASELINE_Q_PERCENT,),
            "quantile_kind": "q5_only",
            "is_baseline": True,
        },
        {
            "id": "C-d1-T4-baseline",
            "picker": "S-B raw P(TP)-P(SL) + top-q q=5 on T4 PnL",
            "score_type": "s_b_raw_per_target_baseline",
            "feature_set": "r7a",
            "target_kind": "T4",
            "target_params": {"k_fav": T4_K_FAV, "k_adv": T4_K_ADV, "h_m1": T4_H_M1},
            "quantile_percents": (PER_TARGET_BASELINE_Q_PERCENT,),
            "quantile_kind": "q5_only",
            "is_baseline": True,
        },
    ]


# ---------------------------------------------------------------------------
# Per-target baseline FAIL-FAST (internal consistency; PR #350 §8.4)
# ---------------------------------------------------------------------------


def check_per_target_baseline_consistency(
    per_target_baseline_first: dict,
    per_target_baseline_second: dict,
) -> dict:
    """Internal-consistency check: two computations of the same per-target
    baseline must agree within tolerance (n_trades exact / Sharpe ±1e-4 /
    ann_pnl ±0.5 pip).

    Per PR #350 §8.4. FAIL-FAST HALT on mismatch.

    Note: this is an INTERNAL consistency check (same baseline computed
    twice within the same β-eval run). External comparison vs archived
    Phase 28 §10 is DIAGNOSTIC-ONLY (see compute_archived_phase28_drift).
    """
    report: dict = {"per_target": {}, "all_consistent": True}
    for target in ("T1", "T2", "T3", "T4"):
        first = per_target_baseline_first.get(target, {})
        second = per_target_baseline_second.get(target, {})
        n_first = int(first.get("test_n_trades", 0))
        n_second = int(second.get("test_n_trades", 0))
        sh_first = float(first.get("test_sharpe", float("nan")))
        sh_second = float(second.get("test_sharpe", float("nan")))
        ap_first = float(first.get("test_ann_pnl", float("nan")))
        ap_second = float(second.get("test_ann_pnl", float("nan")))
        n_match = abs(n_first - n_second) <= PER_TARGET_BASELINE_N_TRADES_TOLERANCE
        sh_delta = (
            sh_first - sh_second
            if (np.isfinite(sh_first) and np.isfinite(sh_second))
            else float("nan")
        )
        sh_match = (
            np.isfinite(sh_delta) and abs(sh_delta) <= PER_TARGET_BASELINE_SHARPE_ABS_TOLERANCE
        )
        ap_delta = (
            ap_first - ap_second
            if (np.isfinite(ap_first) and np.isfinite(ap_second))
            else float("nan")
        )
        ap_match = (
            np.isfinite(ap_delta) and abs(ap_delta) <= PER_TARGET_BASELINE_ANN_PNL_ABS_TOLERANCE
        )
        all_match = bool(n_match and sh_match and ap_match)
        if not all_match:
            report["all_consistent"] = False
        report["per_target"][target] = {
            "n_trades_first": n_first,
            "n_trades_second": n_second,
            "n_trades_match": bool(n_match),
            "sharpe_first": sh_first,
            "sharpe_second": sh_second,
            "sharpe_delta": float(sh_delta) if np.isfinite(sh_delta) else float("nan"),
            "sharpe_match": bool(sh_match),
            "ann_pnl_first": ap_first,
            "ann_pnl_second": ap_second,
            "ann_pnl_delta": float(ap_delta) if np.isfinite(ap_delta) else float("nan"),
            "ann_pnl_match": bool(ap_match),
            "all_match": all_match,
        }
    if not report["all_consistent"]:
        failures = [
            f"{t}: n_match={d['n_trades_match']} sharpe_match={d['sharpe_match']} "
            f"ann_pnl_match={d['ann_pnl_match']}"
            for t, d in report["per_target"].items()
            if not d["all_match"]
        ]
        raise PerTargetBaselineMismatchError(
            "Per-target baseline internal consistency check FAILED per PR #350 §8.4; "
            "failures: " + "; ".join(failures)
        )
    return report


def compute_archived_phase28_drift(per_target_baseline: dict) -> dict:
    """DIAGNOSTIC-ONLY drift signal vs archived Phase 28 §10 reference.

    Per PR #350 §8.5. External comparison; NOT a FAIL-FAST trigger.
    Reports how much each target variant changes the baseline numeric
    from the inherited triple-barrier 1.5/1.0 reference.
    """
    out: dict = {}
    for target in ("T1", "T2", "T3", "T4"):
        b = per_target_baseline.get(target, {})
        n = int(b.get("test_n_trades", 0))
        sh = float(b.get("test_sharpe", float("nan")))
        ap = float(b.get("test_ann_pnl", float("nan")))
        out[target] = {
            "test_n_trades_per_target": n,
            "test_n_trades_archived_phase28": int(ARCHIVED_PHASE_28_SECTION10_N_TRADES),
            "test_n_trades_delta": int(n - ARCHIVED_PHASE_28_SECTION10_N_TRADES),
            "test_sharpe_per_target": sh,
            "test_sharpe_archived_phase28": float(ARCHIVED_PHASE_28_SECTION10_SHARPE),
            "test_sharpe_delta": (
                float(sh - ARCHIVED_PHASE_28_SECTION10_SHARPE) if np.isfinite(sh) else float("nan")
            ),
            "test_ann_pnl_per_target": ap,
            "test_ann_pnl_archived_phase28": float(ARCHIVED_PHASE_28_SECTION10_ANN_PNL),
            "test_ann_pnl_delta": (
                float(ap - ARCHIVED_PHASE_28_SECTION10_ANN_PNL) if np.isfinite(ap) else float("nan")
            ),
        }
    return out


# ---------------------------------------------------------------------------
# C-d1-target-control drift check vs 27.0d C-se (DIAGNOSTIC-ONLY WARN; 6th-phase chain)
# ---------------------------------------------------------------------------


def compute_c_d1_target_control_drift_check(c_d1_target_control_result: dict) -> dict:
    """DIAGNOSTIC-ONLY WARN; NOT HALT.

    Per PR #350 §9.3 (NG#A2-3): C-d1-target-control reproduces 27.0d C-se
    with sample_weight=1 (6th bit-tight reproduction in the inheritance
    chain: 27.0d → 27.0f → 28.0a → 28.0b → 28.0c → 29.0a target-control).
    """
    rm = c_d1_target_control_result.get("test_realised_metrics", {})
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
        abs(baseline_ann_pnl) * TARGET_CONTROL_DRIFT_ANN_PNL_FRAC_TOLERANCE
        if baseline_ann_pnl is not None and np.isfinite(baseline_ann_pnl)
        else None
    )

    n_trades_within = (
        abs(n_trades_delta) <= TARGET_CONTROL_DRIFT_N_TRADES_TOLERANCE
        if n_trades_delta is not None
        else False
    )
    sharpe_within = (
        abs(sharpe_delta) <= TARGET_CONTROL_DRIFT_SHARPE_TOLERANCE
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
        "chain_position": "6th anchor (27.0d -> 27.0f -> 28.0a -> 28.0b -> 28.0c -> 29.0a)",
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
# Within-eval drift per target (PARTIAL_DRIFT_TARGET_REPLICA detection; NG#A2-3)
# ---------------------------------------------------------------------------


def compute_within_eval_target_drift_check(
    c_d1_tx_result: dict,
    c_d1_target_control_result: dict,
) -> dict:
    """Compare a per-target cell vs C-d1-target-control at val-selected
    configuration.

    Per PR #350 §10 row 4 + NG#A2-3: if C-d1-Tx ≈ C-d1-target-control
    within tolerance, flag PARTIAL_DRIFT_TARGET_REPLICA. Target redesign
    had zero effect on monetization vs inherited triple-barrier.
    """
    if c_d1_tx_result.get("h_state") != "OK" or c_d1_target_control_result.get("h_state") != "OK":
        return {
            "all_within_tolerance": False,
            "warn": True,
            "note": "per-target cell or target-control h_state != OK",
        }
    rm_tx = c_d1_tx_result.get("test_realised_metrics", {})
    rm_ctl = c_d1_target_control_result.get("test_realised_metrics", {})
    n_tx = int(rm_tx.get("n_trades", 0))
    n_ctl = int(rm_ctl.get("n_trades", 0))
    sh_tx = float(rm_tx.get("sharpe", float("nan")))
    sh_ctl = float(rm_ctl.get("sharpe", float("nan")))
    ap_tx = float(rm_tx.get("annual_pnl", float("nan")))
    ap_ctl = float(rm_ctl.get("annual_pnl", float("nan")))

    n_trades_delta = n_tx - n_ctl
    sharpe_delta = sh_tx - sh_ctl if (np.isfinite(sh_tx) and np.isfinite(sh_ctl)) else float("nan")
    ann_pnl_delta = ap_tx - ap_ctl if (np.isfinite(ap_tx) and np.isfinite(ap_ctl)) else float("nan")

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
        "n_trades_candidate": int(n_tx),
        "n_trades_control": int(n_ctl),
        "n_trades_delta": int(n_trades_delta),
        "n_trades_within_tolerance": bool(n_trades_within),
        "sharpe_candidate": float(sh_tx),
        "sharpe_control": float(sh_ctl),
        "sharpe_delta": float(sharpe_delta) if np.isfinite(sharpe_delta) else float("nan"),
        "sharpe_within_tolerance": bool(sharpe_within),
        "ann_pnl_candidate": float(ap_tx),
        "ann_pnl_control": float(ap_ctl),
        "ann_pnl_delta": float(ann_pnl_delta) if np.isfinite(ann_pnl_delta) else float("nan"),
        "ann_pnl_tolerance_abs": ann_pnl_tolerance_abs,
        "ann_pnl_within_tolerance": bool(ann_pnl_within),
        "all_within_tolerance": all_within,
        "warn": all_within,  # WARN means "zero effect detected"
    }


# ---------------------------------------------------------------------------
# H-D1 4-outcome ladder resolver per target (PR #350 §10; precedence row 4 > 1 > 2 > 3)
# ---------------------------------------------------------------------------


def compute_h_d1_outcome_per_target(
    c_d1_tx_result: dict,
    per_target_baseline_pass: bool,
    target_drift_report_vs_control: dict,
    target_id: str,
    per_target_baseline_val_sharpe: float,
) -> dict:
    """Resolve 1 of 4 H-D1 outcomes per target (precedence row 4 > 1 > 2 > 3).

    PARTIAL_DRIFT_TARGET_REPLICA checked first per NG#A2-3.
    """
    cell_id = c_d1_tx_result.get("cell", {}).get("id", "unknown")
    if c_d1_tx_result.get("h_state") != "OK":
        return {
            "cell_id": cell_id,
            "target_id": target_id,
            "outcome": H_D1_OUTCOME_NEEDS_REVIEW,
            "row_matched": 0,
            "reason": f"h_state={c_d1_tx_result.get('h_state')}",
        }

    # Row 4 precedence: PARTIAL_DRIFT_TARGET_REPLICA
    drift_within = target_drift_report_vs_control.get("all_within_tolerance", False)
    if drift_within:
        return {
            "cell_id": cell_id,
            "target_id": target_id,
            "outcome": H_D1_OUTCOME_PARTIAL_DRIFT_TARGET_REPLICA,
            "row_matched": 4,
            "reason": (
                f"{target_id} target had zero effect on monetization (drift vs "
                "C-d1-target-control within tolerance); analogous to 27.0f H-B6 / "
                "28.0a H-C1 row 4 / 28.0b H-C2 row 4 / 28.0c H-C3 row 4"
            ),
            "evidence": {
                "drift_n_trades_delta": target_drift_report_vs_control.get("n_trades_delta"),
                "drift_sharpe_delta": target_drift_report_vs_control.get("sharpe_delta"),
                "drift_ann_pnl_delta": target_drift_report_vs_control.get("ann_pnl_delta"),
            },
        }

    val_sharpe = float(c_d1_tx_result.get("val_realised_sharpe", float("nan")))
    val_n = int(c_d1_tx_result.get("val_n_trades", 0))
    qb = c_d1_tx_result.get("quantile_best", {}) or {}
    cell_spearman_val = qb.get("val", {}).get("spearman_score_vs_pnl", float("nan"))
    if not np.isfinite(cell_spearman_val):
        cell_spearman_val = float(c_d1_tx_result.get("val_cell_spearman", float("nan")))
    if not np.isfinite(cell_spearman_val):
        cell_spearman_val = float(c_d1_tx_result.get("test_formal_spearman", float("nan")))

    sharpe_lift = (
        float(val_sharpe - per_target_baseline_val_sharpe)
        if (np.isfinite(val_sharpe) and np.isfinite(per_target_baseline_val_sharpe))
        else float("nan")
    )

    h1m_pass = np.isfinite(cell_spearman_val) and cell_spearman_val >= H1M_PRESERVE_THRESHOLD
    h2_pass = np.isfinite(sharpe_lift) and sharpe_lift >= H2_LIFT_THRESHOLD_PASS
    h3_pass = val_n >= H3_TRADE_COUNT_THRESHOLD

    evidence = {
        "val_sharpe": val_sharpe,
        "val_n_trades": val_n,
        "cell_spearman_val": cell_spearman_val,
        "per_target_baseline_val_sharpe": per_target_baseline_val_sharpe,
        "sharpe_lift_absolute": sharpe_lift,
        "h1m_pass": bool(h1m_pass),
        "h2_pass": bool(h2_pass),
        "h3_pass": bool(h3_pass),
        "per_target_baseline_pass": bool(per_target_baseline_pass),
    }

    # Row 1 PASS
    if h1m_pass and h2_pass and h3_pass and per_target_baseline_pass:
        return {
            "cell_id": cell_id,
            "target_id": target_id,
            "outcome": H_D1_OUTCOME_PASS,
            "row_matched": 1,
            "reason": "all four H-D1 conditions satisfied",
            "evidence": evidence,
        }

    # Row 2 PARTIAL_SUPPORT
    h2_partial = (
        np.isfinite(sharpe_lift)
        and H2_LIFT_THRESHOLD_PARTIAL_SUPPORT_LO <= sharpe_lift < H2_LIFT_THRESHOLD_PASS
    )
    if h2_partial and h1m_pass and h3_pass and per_target_baseline_pass:
        return {
            "cell_id": cell_id,
            "target_id": target_id,
            "outcome": H_D1_OUTCOME_PARTIAL_SUPPORT,
            "row_matched": 2,
            "reason": (
                f"val Sharpe lift {sharpe_lift:+.4f} in [+0.02, +0.05); other H-D1 "
                "conditions intact"
            ),
            "evidence": evidence,
        }

    # Row 3 FALSIFIED_TARGET_INSUFFICIENT (default)
    return {
        "cell_id": cell_id,
        "target_id": target_id,
        "outcome": H_D1_OUTCOME_FALSIFIED_TARGET_INSUFFICIENT,
        "row_matched": 3,
        "reason": (f"val Sharpe lift {sharpe_lift:+.4f} < +0.02 OR other H-D1 conditions failed"),
        "evidence": evidence,
    }


def compute_h_d1_aggregate_verdict(per_target_outcomes: list[dict]) -> dict:
    """Aggregate H-D1 verdict per PR #350 §11.

    All-fail labelled FALSIFIED_A2_NARROW, NEVER FALSIFIED_ALL_A2.
    Alternate target framings outside closed 4-target allowlist remain
    admissible via separate scope amendment.
    """
    outcomes = [o.get("outcome") for o in per_target_outcomes]
    has_pass = H_D1_OUTCOME_PASS in outcomes
    has_partial_support = H_D1_OUTCOME_PARTIAL_SUPPORT in outcomes
    all_partial_drift = len(outcomes) > 0 and all(
        o == H_D1_OUTCOME_PARTIAL_DRIFT_TARGET_REPLICA for o in outcomes
    )
    all_falsified = len(outcomes) > 0 and all(
        o
        in {
            H_D1_OUTCOME_FALSIFIED_TARGET_INSUFFICIENT,
            H_D1_OUTCOME_PARTIAL_DRIFT_TARGET_REPLICA,
        }
        for o in outcomes
    )

    if has_pass:
        verdict = "SPLIT_VERDICT_ROUTE_TO_REVIEW"
        a2_narrow_status = "PASS_under_A2_narrow"
        routing = (
            "1+ target produced H-D1 PASS at the C-d1-Tx cell; "
            "PROMISING_BUT_NEEDS_OOS candidate. ADOPT_CANDIDATE wall preserved per "
            "Clause 1. Phase 29 §10 per-target baseline reference frozen for the "
            "PASS target; routing review for next axis."
        )
    elif has_partial_support:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        a2_narrow_status = "PARTIAL_under_A2_narrow"
        routing = (
            "1+ target PARTIAL_SUPPORT (sub-threshold Sharpe lift); no target PASS. "
            "Route to post-29.0a routing review for A0-broad / R-B / A3 next-axis "
            "comparison."
        )
    elif all_partial_drift:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        a2_narrow_status = "FALSIFIED_A2_NARROW"
        routing = (
            "All 4 targets PARTIAL_DRIFT_TARGET_REPLICA — target redesign does not "
            "move the score regardless of variant. Strong FALSIFIED_A2_NARROW "
            "signal; alternate target framings outside closed 4-target allowlist "
            "remain admissible via separate scope amendment. Route to post-29.0a "
            "routing review for A0-broad / R-B / A3 next-axis comparison. NEVER "
            "label this FALSIFIED_ALL_A2."
        )
    elif all_falsified:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        a2_narrow_status = "FALSIFIED_A2_NARROW"
        routing = (
            "All 4 targets FALSIFIED_TARGET_INSUFFICIENT or "
            "PARTIAL_DRIFT_TARGET_REPLICA — A2 axis exhausted under tested closed "
            "4-target allowlist. Result is FALSIFIED_A2_NARROW (NEVER "
            "FALSIFIED_ALL_A2). Alternate target framings outside closed 4-target "
            "allowlist remain admissible via separate scope amendment. Post-29.0a "
            "routing review compares A0-broad / R-B / A3 next-axis options."
        )
    else:
        verdict = "REJECT_NON_DISCRIMINATIVE"
        a2_narrow_status = "INCONCLUSIVE_under_A2_narrow"
        routing = "no target produced PASS or PARTIAL_SUPPORT; route to post-29.0a routing review"

    # R-T3 absorption status (T3-specific)
    t3_outcome = next(
        (o.get("outcome") for o in per_target_outcomes if o.get("target_id") == "T3"), None
    )
    if t3_outcome == H_D1_OUTCOME_PASS:
        r_t3_status = "PASS_under_T3"
    elif t3_outcome == H_D1_OUTCOME_PARTIAL_SUPPORT:
        r_t3_status = "PARTIAL_under_T3"
    elif t3_outcome in (
        H_D1_OUTCOME_FALSIFIED_TARGET_INSUFFICIENT,
        H_D1_OUTCOME_PARTIAL_DRIFT_TARGET_REPLICA,
    ):
        r_t3_status = "FALSIFIED_under_T3"
    else:
        r_t3_status = "INCONCLUSIVE_under_T3"

    return {
        "aggregate_verdict": verdict,
        "a2_narrow_status": a2_narrow_status,
        "routing_implication": routing,
        "per_target_outcomes": [
            {
                "cell_id": o.get("cell_id"),
                "target_id": o.get("target_id"),
                "outcome": o.get("outcome"),
                "row_matched": o.get("row_matched"),
            }
            for o in per_target_outcomes
        ],
        "has_pass": bool(has_pass),
        "has_partial_support": bool(has_partial_support),
        "all_partial_drift": bool(all_partial_drift),
        "r_t3_absorption_status": r_t3_status,
    }


# ---------------------------------------------------------------------------
# Top-tail regime audit (DIAGNOSTIC-ONLY; spread_at_signal_pip only; per target)
# ---------------------------------------------------------------------------


def compute_top_tail_regime_audit_for_a2(
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
        top_mean = float(top_finite.mean()) if len(top_finite) > 0 else float("nan")
        top_p50 = float(np.quantile(top_finite, 0.5)) if len(top_finite) > 0 else float("nan")
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
# T3 overlap rate diagnostic (DIAGNOSTIC-ONLY WARN; PR #350 §13 item 9)
# ---------------------------------------------------------------------------


def compute_t3_overlap_rate(df: pd.DataFrame, max_horizon: int = max(T3_HORIZONS)) -> dict:
    """Per-pair count of signal rows where next_signal_ts - signal_ts < max_horizon M1 bars.

    DIAGNOSTIC-ONLY; WARN-only if overall overlap rate > T3_OVERLAP_WARN_RATE (10%).
    """
    out: dict = {"per_pair": {}, "overall": {}}
    df_sorted = df.sort_values(["pair", "signal_ts"]).reset_index(drop=True)
    pairs = df_sorted["pair"].to_numpy()
    signal_ts = df_sorted["signal_ts"].to_numpy()
    total_overlap = 0
    total_signals = 0
    for pair in sorted(set(pairs.tolist())):
        pair_mask = pairs == pair
        pair_ts = pd.to_datetime(signal_ts[pair_mask])
        if len(pair_ts) < 2:
            out["per_pair"][pair] = {
                "n_signals": int(len(pair_ts)),
                "n_overlap": 0,
                "overlap_rate": float("nan"),
            }
            continue
        diffs_minutes = (pair_ts[1:] - pair_ts[:-1]).total_seconds() / 60.0
        n_overlap = int((diffs_minutes < max_horizon).sum())
        overlap_rate = n_overlap / max(len(pair_ts) - 1, 1)
        out["per_pair"][pair] = {
            "n_signals": int(len(pair_ts)),
            "n_overlap": n_overlap,
            "overlap_rate": float(overlap_rate),
        }
        total_overlap += n_overlap
        total_signals += len(pair_ts) - 1
    overall_rate = total_overlap / max(total_signals, 1)
    out["overall"] = {
        "n_signals": total_signals,
        "n_overlap": total_overlap,
        "overlap_rate": float(overall_rate),
        "max_horizon_m1_bars": int(max_horizon),
        "warn_threshold": float(T3_OVERLAP_WARN_RATE),
        "warn": bool(overall_rate > T3_OVERLAP_WARN_RATE),
    }
    return out


# ---------------------------------------------------------------------------
# Per-cell quantile evaluation (inherited shape from 28.0c)
# ---------------------------------------------------------------------------


def evaluate_quantile_cell_29_0a(
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
    pnl_val_target: np.ndarray,
    pnl_test_target: np.ndarray,
    feature_importance_diag: dict,
) -> dict:
    """Evaluate a quantile cell — inherited from 28.0c shape; per-target PnL."""
    score_type = str(cell.get("score_type", "unknown"))
    target_id = str(cell.get("target_kind", "unknown"))

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

    quantile_percents = tuple(cell.get("quantile_percents", QUANTILE_PERCENTS_29_0A))
    quantile_results = evaluate_quantile_family_custom(
        val_score,
        pnl_val_target,
        test_score,
        pnl_test_target,
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
        test_label, test_raw_probs, test_score, pnl_test_target
    )
    formal_spearman = cls_diag.get("spearman_score_vs_pnl", float("nan"))

    test_df_aligned = test_df.reset_index(drop=True)
    val_df_aligned = val_df.reset_index(drop=True)
    traded_mask_test = np.isfinite(test_score) & (test_score >= best_q_record["cutoff"])
    valid_pnl_mask_test = np.isfinite(pnl_test_target)
    in_trade = traded_mask_test & valid_pnl_mask_test
    by_pair: dict[str, int] = {}
    by_direction: dict[str, int] = {"long": 0, "short": 0}
    for i in np.flatnonzero(in_trade):
        p = str(test_df_aligned["pair"].iloc[i])
        d = str(test_df_aligned["direction"].iloc[i])
        by_pair[p] = by_pair.get(p, 0) + 1
        by_direction[d] = by_direction.get(d, 0) + 1

    valid_pnl_mask_val = np.isfinite(pnl_val_target)
    traded_mask_val = np.isfinite(val_score) & (val_score >= best_q_record["cutoff"])
    val_concentration = compute_pair_concentration(
        val_df_aligned, traded_mask_val, valid_pnl_mask_val
    )
    test_concentration = compute_pair_concentration(
        test_df_aligned, traded_mask_test, valid_pnl_mask_test
    )
    per_pair_sharpe = compute_per_pair_sharpe_contribution(
        test_df_aligned, traded_mask_test, pnl_test_target
    )
    low_power = n_test < LOW_POWER_N_TEST or n_train < LOW_POWER_N_TRAIN

    # Cell-level Spearman on val (over traded rows)
    if int(traded_mask_val.sum()) >= 2:
        from scipy.stats import spearmanr

        val_traded_pnl = pnl_val_target[traded_mask_val & valid_pnl_mask_val]
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
        "target_id": target_id,
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
    keys = ("id", "picker", "score_type", "feature_set", "target_kind", "is_baseline")
    return " ".join(f"{k}={cell.get(k)}" for k in keys)


# ---------------------------------------------------------------------------
# Sanity probe (items 1-6 inherited; NEW items 7-10 per-target)
# ---------------------------------------------------------------------------


def run_sanity_probe_29_0a(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    pairs: list[str],
    days: int = SPAN_DAYS,
    pnl_train_full_per_target: dict[str, np.ndarray] | None = None,
    t1_distribution: dict | None = None,
    t2_distribution: dict | None = None,
    t3_distribution: dict | None = None,
    t3_overlap_report: dict | None = None,
    t4_distribution: dict | None = None,
    val_pred_per_target: dict[str, np.ndarray] | None = None,
    test_pred_per_target: dict[str, np.ndarray] | None = None,
    oof_corr_diag_per_target: dict | None = None,
    feature_importance_per_target: dict | None = None,
    train_drop_for_nan_pnl_per_target: dict[str, int] | None = None,
    cell_definitions: list[dict] | None = None,
) -> dict:
    """29.0a-β SanityProbe (items 1-6 inherited; items 7-10 NEW per-target)."""
    print("\n=== 29.0a-β SANITY PROBE (per PR #350 §13) ===")
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
    over_99 = 0
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
    print(
        f"  per-pair TIME-share check: {over_99} pair(s) over {SANITY_MAX_PER_PAIR_TIME_SHARE:.0%}"
    )

    # Item 3: D-1 binding check (parameterised barrier sources bid_h/ask_l/ask_h/bid_l)
    print("  realised-PnL cache basis check (per D-1 binding):")
    barrier_param_src = inspect.getsource(_compute_realised_barrier_pnl_parameterised)
    if not all(tok in barrier_param_src for tok in ["bid_h", "ask_l", "ask_h", "bid_l"]):
        raise SanityProbeError(
            "_compute_realised_barrier_pnl_parameterised does not reference bid_h/ask_l/ask_h/bid_l"
        )
    t1_src = inspect.getsource(_compute_target_t1_fixed_horizon_close_pnl)
    if not all(tok in t1_src for tok in ["ask_o", "bid_c", "bid_o", "ask_c"]):
        raise SanityProbeError(
            "_compute_target_t1_fixed_horizon_close_pnl missing required bid/ask side mapping "
            "(long entry=ask_o, long exit=bid_c, short entry=bid_o, short exit=ask_c)"
        )
    out["d1_binding_check"] = "PASS"
    print("    OK: bid/ask executable treatment confirmed for parameterised barrier + T1")

    # Item 4-6: NaN-rate / positivity check on R7-A
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

    # NaN-PnL HALT per target (Item 4-6 continued)
    if train_drop_for_nan_pnl_per_target is not None and pnl_train_full_per_target is not None:
        out["nan_pnl_per_target"] = {}
        for target_id, nan_count in train_drop_for_nan_pnl_per_target.items():
            n_train_target = len(pnl_train_full_per_target.get(target_id, []))
            threshold = NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD * n_train_target
            out["nan_pnl_per_target"][target_id] = {
                "n_train": n_train_target,
                "nan_pnl_count": int(nan_count),
                "threshold": float(threshold),
                "pass": bool(nan_count <= threshold),
            }
            if nan_count > threshold:
                raise TargetPrecomputeError(
                    f"Target {target_id}: train rows with NaN PnL = {nan_count} > "
                    f"{NAN_PNL_TRAIN_DROP_FRAC_THRESHOLD:.1%} of n_train={n_train_target}"
                )
            print(f"  NaN-PnL {target_id}: {nan_count} train rows (HALT > {int(threshold)}) — PASS")

    # Item 7 NEW: T1 distribution sanity
    if t1_distribution is not None:
        out["t1_distribution"] = t1_distribution
        print(
            f"  T1 fixed-horizon executable close PnL: "
            f"n_finite={t1_distribution.get('n_finite_train', 0)} "
            f"mean={t1_distribution.get('mean_train', float('nan')):+.3f} "
            f"p5={t1_distribution.get('p5_train', float('nan')):+.3f} "
            f"p95={t1_distribution.get('p95_train', float('nan')):+.3f}"
        )

    # Item 8 NEW: T2 distribution sanity (hold_bars + decay factor)
    if t2_distribution is not None:
        out["t2_distribution"] = t2_distribution
        print(
            f"  T2 time-weighted PnL: "
            f"n_finite={t2_distribution.get('n_finite_train', 0)} "
            f"mean={t2_distribution.get('mean_train', float('nan')):+.3f} "
            f"mean_decay_factor={t2_distribution.get('mean_decay_factor', float('nan')):.3f}"
        )

    # Item 9 NEW: T3 distribution sanity + overlap
    if t3_distribution is not None:
        out["t3_distribution"] = t3_distribution
        print(
            f"  T3 multi-horizon PnL: "
            f"n_finite={t3_distribution.get('n_finite_train', 0)} "
            f"mean={t3_distribution.get('mean_train', float('nan')):+.3f}"
        )
    if t3_overlap_report is not None:
        out["t3_overlap_report"] = t3_overlap_report
        overall = t3_overlap_report.get("overall", {})
        warn = overall.get("warn", False)
        print(
            f"  T3 overlap rate (DIAGNOSTIC-ONLY WARN if >{T3_OVERLAP_WARN_RATE:.0%}): "
            f"{overall.get('overlap_rate', float('nan')):.3%} "
            f"({overall.get('n_overlap', 0)}/{overall.get('n_signals', 0)} signals); "
            f"WARN={warn}"
        )

    # Item 10 NEW: T4 distribution sanity
    if t4_distribution is not None:
        out["t4_distribution"] = t4_distribution
        print(
            f"  T4 asymmetric barrier PnL: "
            f"n_finite={t4_distribution.get('n_finite_train', 0)} "
            f"mean={t4_distribution.get('mean_train', float('nan')):+.3f}"
        )

    if oof_corr_diag_per_target is not None:
        out["oof_correlation_per_target"] = oof_corr_diag_per_target
    if feature_importance_per_target is not None:
        out["feature_importance_per_target"] = feature_importance_per_target

    if cell_definitions is not None:
        out["cell_definitions"] = [{k: v for k, v in c.items()} for c in cell_definitions]

    print("=== SANITY PROBE: PASS ===")
    return out


def _compute_target_distribution_stats(pnl_arr: np.ndarray, label: str = "train") -> dict:
    """Compute mean / p5 / p50 / p95 for a target PnL distribution.

    Used by sanity probe items 7-10.
    """
    finite = pnl_arr[np.isfinite(pnl_arr)]
    if len(finite) == 0:
        return {f"n_finite_{label}": 0}
    return {
        f"n_finite_{label}": int(len(finite)),
        f"mean_{label}": float(finite.mean()),
        f"p5_{label}": float(np.quantile(finite, 0.05)),
        f"p50_{label}": float(np.quantile(finite, 0.5)),
        f"p95_{label}": float(np.quantile(finite, 0.95)),
    }


# ---------------------------------------------------------------------------
# Eval report writer (25-section pattern; A2 + Option 9c adaptations)
# ---------------------------------------------------------------------------


def write_eval_report_29_0a(
    report_path: Path,
    cell_results: list[dict],
    val_select: dict,
    verdict_info: dict,
    aggregate_info: dict,
    phase29_section10_per_target_baseline: dict,
    per_target_baseline_consistency_report: dict,
    archived_phase28_drift_report: dict,
    target_control_drift_report: dict,
    h_d1_per_target: list[dict],
    h_d1_aggregate: dict,
    within_eval_drift_per_target: dict[str, dict],
    sanity: dict,
    drop_stats_r7a: dict,
    t_range: tuple,
    preflight_diag: dict,
    n_cells_run: int,
    feature_importance_per_target: dict,
    regression_diag_per_target: dict,
    oof_corr_diag_per_target: dict,
    predicted_pnl_distribution_per_target: dict,
    top_tail_regime_audit_per_target: dict[str, dict],
    t3_overlap_report: dict,
) -> None:
    """Write 25-section eval_report.md (A2 + Option 9c adaptation of 28.0c shape)."""
    lines: list[str] = []
    t_min, t70, t85, t_max = t_range
    lines.append("# Phase 29.0a-β — A2 Target Redesign eval report")
    lines.append("")
    lines.append("**Sub-phase**: 29.0a-β (Phase 29 first sub-phase)")
    lines.append("**Design memo**: PR #350 (`phase29_0a_alpha_a2_target_redesign_design_memo.md`)")
    lines.append("**Kickoff**: PR #348 (Scope III / Policy C / Option 9c)")
    lines.append("**Routing**: PR #349 (post-kickoff routing review; Path 2 A2 PRIMARY)")
    lines.append("")
    lines.append(
        "**MISSION**: Phase 29.0a tests A2 (target redesign) as the Phase 29 first sub-phase. "
        "Closed 4-target allowlist (T1 fixed-horizon executable close / T2 time-weighted / "
        "T3 multi-horizon / T4 asymmetric K_FAV/K_ADV); all D-1 PASS; fixed non-target axes "
        "(R7-A / tabular LightGBM / top-q / Huber α=0.9 / sample_weight=1). Option 9c dual "
        "baseline reference policy exercised."
    )
    lines.append("")

    # §1 Executive summary
    lines.append("## 1. Executive summary")
    lines.append("")
    lines.append("Per-target H-D1 outcome ladder (PR #350 §10; precedence row 4 > 1 > 2 > 3):")
    lines.append("")
    lines.append("| Target | Cell | Outcome | Row | Reason |")
    lines.append("|---|---|---|---|---|")
    for o in h_d1_per_target:
        lines.append(
            f"| {o.get('target_id', '-')} | {o.get('cell_id', '-')} | "
            f"{o.get('outcome', '-')} | {o.get('row_matched', '-')} | "
            f"{o.get('reason', '-')[:100]} |"
        )
    lines.append("")
    lines.append(f"**Aggregate verdict**: {h_d1_aggregate.get('aggregate_verdict')}")
    lines.append(f"**A2-narrow status**: {h_d1_aggregate.get('a2_narrow_status')}")
    lines.append(
        f"**R-T3 absorption status under T3**: {h_d1_aggregate.get('r_t3_absorption_status')}"
    )
    lines.append(f"**Routing implication**: {h_d1_aggregate.get('routing_implication')}")
    lines.append("")
    if h_d1_aggregate.get("a2_narrow_status") == "FALSIFIED_A2_NARROW":
        lines.append(
            "> **EXPLICIT LABEL**: this result is `FALSIFIED_A2_NARROW`, NEVER "
            "`FALSIFIED_ALL_A2`. Alternate target framings outside the tested closed "
            "4-target allowlist (T1/T2/T3/T4) remain admissible via separate scope "
            "amendment PR. Post-29.0a routing review compares A0-broad / R-B / A3 "
            "next-axis options."
        )
        lines.append("")
    lines.append(
        f"**Per-target baseline FAIL-FAST (internal consistency)**: "
        f"all_consistent={per_target_baseline_consistency_report.get('all_consistent', False)}"
    )
    lines.append(
        f"**C-d1-target-control drift vs 27.0d C-se**: "
        f"all_within_tolerance={target_control_drift_report.get('all_within_tolerance')} "
        f"(WARN={target_control_drift_report.get('warn')}; DIAGNOSTIC-ONLY; 6th-phase chain)"
    )
    lines.append("")

    # §2 Cells overview
    lines.append("## 2. Cells overview")
    lines.append("")
    lines.append("| Cell | Picker | Score | Target | Baseline |")
    lines.append("|---|---|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        lines.append(
            f"| {cell['id']} | {cell.get('picker', '-')[:60]} | "
            f"{cell.get('score_type', '-')} | {cell.get('target_kind', '-')} | "
            f"{cell.get('is_baseline', False)} |"
        )
    lines.append("")

    # §3 Row-set policy / drop stats
    lines.append("## 3. Row-set policy / drop stats")
    lines.append("")
    lines.append(
        "**A2 row-set policy**: R7-A-clean parent row-set unchanged. No R7-C drop. "
        "Per-target NaN-PnL drop applied separately for each target Tx regressor fit. "
        "Cross-target row-set is NOT unified; per-target row-set comparison is the "
        "monetisation claim."
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
    nan_pnl = sanity.get("nan_pnl_per_target", {})
    for target_id, info in nan_pnl.items():
        lines.append(
            f"- NaN-PnL {target_id}: {info.get('nan_pnl_count', 0)} train rows "
            f"(threshold {int(info.get('threshold', 0))}) PASS={info.get('pass', False)}"
        )
    for target_id in ("T1", "T2", "T3", "T4"):
        dist = sanity.get(f"{target_id.lower()}_distribution", {})
        if dist:
            lines.append(
                f"- {target_id} train distribution: n_finite={dist.get('n_finite_train', 0)} "
                f"mean={dist.get('mean_train', float('nan')):+.3f}"
            )
    if t3_overlap_report:
        overall = t3_overlap_report.get("overall", {})
        lines.append(
            f"- T3 overlap rate: {overall.get('overlap_rate', float('nan')):.3%} "
            f"(WARN if > {T3_OVERLAP_WARN_RATE:.0%}; warn={overall.get('warn', False)})"
        )
    lines.append("")

    # §5 OOF correlation diagnostic — per target
    lines.append("## 5. OOF correlation diagnostic — per target (DIAGNOSTIC-ONLY)")
    lines.append("")
    if oof_corr_diag_per_target:
        lines.append("| Target | aggregate Pearson | aggregate Spearman |")
        lines.append("|---|---|---|")
        for target_id, d in oof_corr_diag_per_target.items():
            p = d.get("aggregate_pearson", float("nan"))
            sp = d.get("aggregate_spearman", float("nan"))
            lines.append(f"| {target_id} | {p:+.4f} | {sp:+.4f} |")
    lines.append("")

    # §6 Regression diagnostic — per target
    lines.append("## 6. Regression diagnostic — per target (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append("| Target | Split | n | R² | MAE |")
    lines.append("|---|---|---|---|---|")
    for target_id, d in (regression_diag_per_target or {}).items():
        for split_name in ("train", "val", "test"):
            blk = d.get(split_name, {})
            lines.append(
                f"| {target_id} | {split_name} | {blk.get('n', '-')} | "
                f"{blk.get('r2', float('nan')):+.4f} | "
                f"{blk.get('mae', float('nan')):+.3f} |"
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

    # §10 Phase 29 §10 per-target baseline FAIL-FAST (NEW Phase 29 pattern)
    lines.append("## 10. Phase 29 §10 per-target baseline (Option 9c)")
    lines.append("")
    lines.append(
        "**Internal-consistency FAIL-FAST per PR #350 §8.4**: per-target baseline "
        "computed twice must agree within tolerance (n_trades exact / Sharpe ±1e-4 / "
        "ann_pnl ±0.5 pip). Phase 28 §10 archived as DIAGNOSTIC-ONLY 2nd reference."
    )
    lines.append("")
    lines.append("| Target | test_n_trades | test_Sharpe | test_ann_pnl | val_Sharpe |")
    lines.append("|---|---|---|---|---|")
    for target_id in ("T1", "T2", "T3", "T4"):
        b = phase29_section10_per_target_baseline.get(target_id, {})
        lines.append(
            f"| {target_id} | {b.get('test_n_trades', '-')} | "
            f"{b.get('test_sharpe', float('nan')):+.4f} | "
            f"{b.get('test_ann_pnl', float('nan')):+.1f} | "
            f"{b.get('val_sharpe', float('nan')):+.4f} |"
        )
    lines.append("")
    lines.append("**Archived Phase 28 §10 reference (immutable; DIAGNOSTIC-ONLY 2nd reference)**:")
    lines.append(
        f"- n_trades={ARCHIVED_PHASE_28_SECTION10_N_TRADES} | "
        f"Sharpe={ARCHIVED_PHASE_28_SECTION10_SHARPE:+.4f} | "
        f"ann_pnl={ARCHIVED_PHASE_28_SECTION10_ANN_PNL:+.1f} | "
        f"val_Sharpe={ARCHIVED_PHASE_28_SECTION10_VAL_SHARPE:+.4f}"
    )
    lines.append("")
    lines.append("**Per-target baseline drift vs archived Phase 28 §10 (DIAGNOSTIC-ONLY)**:")
    for target_id in ("T1", "T2", "T3", "T4"):
        d = archived_phase28_drift_report.get(target_id, {})
        n_d = d.get("test_n_trades_delta", "-")
        sh_d = d.get("test_sharpe_delta", float("nan"))
        ap_d = d.get("test_ann_pnl_delta", float("nan"))
        sh_d_str = f"{sh_d:+.4f}" if isinstance(sh_d, float) and np.isfinite(sh_d) else str(sh_d)
        ap_d_str = f"{ap_d:+.1f}" if isinstance(ap_d, float) and np.isfinite(ap_d) else str(ap_d)
        lines.append(
            f"- {target_id}: n_trades Δ={n_d} | Sharpe Δ={sh_d_str} | ann_pnl Δ={ap_d_str}"
        )
    lines.append("")
    lines.append(
        f"**FAIL-FAST consistency**: all_consistent="
        f"{per_target_baseline_consistency_report.get('all_consistent', False)}"
    )
    lines.append("")

    # §11 Within-eval drift per target (PARTIAL_DRIFT_TARGET_REPLICA detection)
    lines.append("## 11. Within-eval ablation drift per target (vs C-d1-target-control)")
    lines.append("")
    lines.append(
        "| Target | n_trades Δ | within | Sharpe Δ | within | ann_pnl Δ | within | all_within |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for target_id, d in (within_eval_drift_per_target or {}).items():
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
            f"| {target_id} | {n_d} | {n_w} | {sh_d_str} | {sh_w} | {ap_d_str} | {ap_w} | {all_w} |"
        )
    lines.append("")

    # §11b C-d1-target-control drift vs 27.0d C-se (6th-phase chain)
    lines.append(
        "## 11b. C-d1-target-control drift vs 27.0d C-se (DIAGNOSTIC-ONLY WARN; 6th-phase chain)"
    )
    lines.append("")
    lines.append(f"**Chain position**: {target_control_drift_report.get('chain_position', '-')}")
    lines.append("")
    cd = target_control_drift_report
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

    # §12 Feature importance per target regressor
    lines.append("## 12. Feature importance — per target regressor (DIAGNOSTIC-ONLY)")
    lines.append("")
    for target_id, fi in (feature_importance_per_target or {}).items():
        lines.append(f"### {target_id}")
        if isinstance(fi, dict) and "items" in fi:
            for item in fi["items"]:
                lines.append(
                    f"- {item.get('feature', '-')}: gain={item.get('gain', float('nan')):+.1f}"
                )
        else:
            lines.append(f"(unavailable: {fi})")
        lines.append("")

    # §13 H-D1 outcome row binding per target
    lines.append(
        "## 13. H-D1 outcome row binding per target (A2 closed allowlist; interpretation guards)"
    )
    lines.append("")
    lines.append(
        "Per PR #350 §10: H-D1 = A2 target redesign axis. Failure of all 4 targets is "
        "`FALSIFIED_A2_NARROW`, NEVER `FALSIFIED_ALL_A2`. Alternate target framings "
        "outside closed 4-target allowlist remain admissible via separate scope "
        "amendment. R-T3 absorbed under T3 multi-horizon variant."
    )
    lines.append("")
    lines.append("| Target | Cell | Outcome | Row | Lift | val Sharpe | val n | cell Sp. | Notes |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for o in h_d1_per_target:
        ev = o.get("evidence", {}) if isinstance(o.get("evidence"), dict) else {}
        lift = ev.get("sharpe_lift_absolute", float("nan"))
        vs = ev.get("val_sharpe", float("nan"))
        vn = ev.get("val_n_trades", "-")
        sp = ev.get("cell_spearman_val", float("nan"))
        lift_str = f"{lift:+.4f}" if isinstance(lift, float) and np.isfinite(lift) else str(lift)
        vs_str = f"{vs:+.4f}" if isinstance(vs, float) and np.isfinite(vs) else str(vs)
        sp_str = f"{sp:+.4f}" if isinstance(sp, float) and np.isfinite(sp) else str(sp)
        lines.append(
            f"| {o.get('target_id', '-')} | {o.get('cell_id', '-')} | "
            f"{o.get('outcome', '-')} | {o.get('row_matched', '-')} | "
            f"{lift_str} | {vs_str} | {vn} | {sp_str} | "
            f"{o.get('reason', '-')[:80]} |"
        )
    lines.append("")
    lines.append(f"**Aggregate H-D1 verdict**: {h_d1_aggregate.get('aggregate_verdict')}")
    lines.append(f"**A2-narrow status**: {h_d1_aggregate.get('a2_narrow_status')}")
    lines.append(f"**R-T3 absorption status**: {h_d1_aggregate.get('r_t3_absorption_status')}")
    lines.append(f"**Routing**: {h_d1_aggregate.get('routing_implication')}")
    lines.append("")

    # §14-25: remaining sections
    lines.append("## 14. Trade-count budget audit per target")
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

    lines.append("## 16. Direction balance per cell (val-selected on test)")
    lines.append("")
    lines.append("| Cell | long | short |")
    lines.append("|---|---|---|")
    for c in cell_results:
        cell = c["cell"]
        bd = c.get("by_direction_trade_count", {}) or {}
        lines.append(f"| {cell['id']} | {bd.get('long', 0)} | {bd.get('short', 0)} |")
    lines.append("")

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

    lines.append(
        "## 18. Top-tail regime audit per target (DIAGNOSTIC-ONLY; spread_at_signal_pip only)"
    )
    lines.append("")
    lines.append("**Note**: R7-C f5a/f5b/f5c features NOT computed (out of scope per Clause 6).")
    lines.append("")
    for target_id, audit in (top_tail_regime_audit_per_target or {}).items():
        pop = audit.get("population", {})
        lines.append(f"### {target_id}")
        lines.append(
            f"- population mean spread = {pop.get('mean_spread_at_signal_pip', float('nan')):+.3f}"
        )
        for per_q in audit.get("per_q", []):
            lines.append(
                f"- q={per_q['q_percent']:.1f}: top mean={per_q['top_mean_spread']:+.3f} "
                f"(Δ {per_q['delta_mean_vs_population']:+.3f}); n_top={per_q['n_top']}"
            )
        lines.append("")
    if t3_overlap_report:
        overall = t3_overlap_report.get("overall", {})
        lines.append(f"### T3 overlap rate (DIAGNOSTIC-ONLY WARN if > {T3_OVERLAP_WARN_RATE:.0%})")
        lines.append(
            f"- overall: {overall.get('overlap_rate', float('nan')):.3%} "
            f"({overall.get('n_overlap', 0)}/{overall.get('n_signals', 0)} signals); "
            f"warn={overall.get('warn', False)}"
        )
        lines.append("")

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

    lines.append("## 20. Realised PnL distribution per target on TRAIN (DIAGNOSTIC)")
    lines.append("")
    for target_id in ("T1", "T2", "T3", "T4"):
        dist = sanity.get(f"{target_id.lower()}_distribution", {})
        if dist:
            lines.append(
                f"- {target_id}: n_finite={dist.get('n_finite_train', 0)} "
                f"mean={dist.get('mean_train', float('nan')):+.3f} "
                f"p5={dist.get('p5_train', float('nan')):+.3f} "
                f"p50={dist.get('p50_train', float('nan')):+.3f} "
                f"p95={dist.get('p95_train', float('nan')):+.3f}"
            )
    lines.append("")

    lines.append("## 21. Predicted PnL distribution per target (DIAGNOSTIC)")
    lines.append("")
    lines.append("| Target | Split | n | mean | p5 | p50 | p95 |")
    lines.append("|---|---|---|---|---|---|---|")
    for target_id, splits_d in (predicted_pnl_distribution_per_target or {}).items():
        for split_name in ("train", "val", "test"):
            stats = splits_d.get(split_name, {})
            lines.append(
                f"| {target_id} | {split_name} | {stats.get('n_finite', 0)} | "
                f"{stats.get('mean', float('nan')):+.3f} | "
                f"{stats.get('p5', float('nan')):+.3f} | "
                f"{stats.get('p50', float('nan')):+.3f} | "
                f"{stats.get('p95', float('nan')):+.3f} |"
            )
    lines.append("")

    lines.append("## 22. References")
    lines.append("")
    lines.append("- PR #348 — Phase 29 kickoff (Scope III / Policy C / Option 9c)")
    lines.append("- PR #349 — Phase 29 first-mover routing review (Path 2 A2 PRIMARY)")
    lines.append("- PR #350 — Phase 29.0a-α A2 design memo (this sub-phase α)")
    lines.append("- PR #325 — Phase 27.0d-β S-E regression (score backbone)")
    lines.append("- PR #344 — Phase 28.0c-α A0-narrow design memo (25-section pattern source)")
    lines.append("- PR #347 — Phase 28 closure memo (Phase 28 §10 archived reference)")
    lines.append("- PR #334 — Phase 27 closure memo (R-T3 carry-forward source)")
    lines.append("- PR #279 — γ closure")
    lines.append("- Phase 22 frozen-OOS contract")
    lines.append("- Phase 9.12 production v9 tip 79ed1e8 (untouched)")
    lines.append("")

    lines.append("## 23. Caveats")
    lines.append("")
    lines.append(
        "- All test-set metrics outside the val-selected per-cell configuration are "
        "DIAGNOSTIC-ONLY and excluded from the formal H-D1 verdict."
    )
    lines.append(
        "- H2 PASS = PROMISING_BUT_NEEDS_OOS only. ADOPT_CANDIDATE wall preserved per "
        "Clause 1. NG#10 / NG#11 not relaxed."
    )
    lines.append(
        "- All 4 target variants (T1/T2/T3/T4) are D-1 executable and "
        "ADOPT_CANDIDATE-eligible. No DIAGNOSTIC-ONLY target variants in the closed "
        "allowlist (NG#A2-1)."
    )
    lines.append(
        "- **A2-narrow vs A2-broad distinction**: failure of all 4 targets in the closed "
        "allowlist is `FALSIFIED_A2_NARROW`, NEVER `FALSIFIED_ALL_A2`. Alternate target "
        "framings outside the 4-target allowlist remain admissible via separate scope "
        "amendment."
    )
    lines.append(
        "- **R-T3 absorbed under T3** (multi-horizon variant; PR #347 §12). R-T3 "
        "standalone elevation NOT admissible."
    )
    lines.append(
        "- **Phase 28 §10 archived as DIAGNOSTIC-ONLY 2nd reference per Option 9c**; "
        "Phase 29 §10 per-target baseline reference is the formal FAIL-FAST gate."
    )
    lines.append(
        "- T3 overlap with next signal_ts (DIAGNOSTIC-ONLY WARN if > 10%); reported in §18."
    )
    lines.append(
        "- Top-tail regime audit uses `spread_at_signal_pip` only; R7-C features out "
        "of scope per Clause 6."
    )
    lines.append("")

    lines.append("## 24. Cross-validation re-fits diagnostic (DIAGNOSTIC-ONLY)")
    lines.append("")
    lines.append(
        "5-fold OOF (seed=42) per-target on S-E backbone. Aggregate Pearson / Spearman "
        "per target reported in §5."
    )
    lines.append("")

    lines.append("## 25. Sub-phase verdict snapshot")
    lines.append("")
    lines.append("- per-target outcomes:")
    for o in h_d1_per_target:
        aid = o.get("target_id", "-")
        cid = o.get("cell_id", "-")
        oc = o.get("outcome", "-")
        rm = o.get("row_matched", "-")
        lines.append(f"  - {aid} ({cid}): {oc} (row {rm})")
    lines.append(f"- aggregate verdict: {h_d1_aggregate.get('aggregate_verdict')}")
    lines.append(f"- A2-narrow status: {h_d1_aggregate.get('a2_narrow_status')}")
    lines.append(f"- R-T3 absorption status: {h_d1_aggregate.get('r_t3_absorption_status')}")
    lines.append(f"- routing implication: {h_d1_aggregate.get('routing_implication')}")
    lines.append(
        f"- per-target baseline FAIL-FAST internal consistency: "
        f"{per_target_baseline_consistency_report.get('all_consistent', False)}"
    )
    lines.append(
        f"- C-d1-target-control drift vs 27.0d C-se: "
        f"all_within_tolerance={target_control_drift_report.get('all_within_tolerance')} "
        f"(6th-phase chain; WARN-only)"
    )
    lines.append("")
    lines.append("*End of `artifacts/stage29_0a/eval_report.md`.*")
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
        help="DIAGNOSTIC-ONLY; formal verdict NOT valid in quick mode (NG#A2-*)",
    )
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 29.0a-β A2 Target Redesign eval ({len(args.pairs)} pairs) ===")
    print(
        f"Closed 4-target allowlist (α-fixed; NG#A2-1; all D-1 PASS): "
        f"T1 fixed-horizon close (H_M1={T1_H_M1}); "
        f"T2 time-weighted (linear; H_M1={T2_H_M1}); "
        f"T3 multi-horizon (H={list(T3_HORIZONS)}); "
        f"T4 asymmetric (K_FAV={T4_K_FAV}/K_ADV={T4_K_ADV}; H_M1={T4_H_M1})"
    )
    print(f"R7-A FIXED (4 features): {list(ALL_FEATURES_R7A)}")
    print(
        f"Fixed non-target axes: tabular LightGBM single regressor; "
        f"top-q quantile family {list(QUANTILE_PERCENTS_29_0A)}; "
        f"symmetric Huber α={HUBER_ALPHA}; sample_weight=1"
    )
    print(f"OOF (DIAGNOSTIC-ONLY): {OOF_N_FOLDS} folds, seed={OOF_SEED} (per-target)")
    print("Option 9c: Phase 28 §10 archived (immutable); Phase 29 §10 baseline per-target")
    if args.quick_mode:
        print(
            "QUICK-MODE: formal verdict NOT valid in quick mode (NG#A2-* requires full "
            "730-day / 20-pair scope)"
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
            f"test={len(test_df)} — formal verdict NOT valid"
        )

    # 5. Pre-fit sanity probe (items 1-3 only; items 4-10 deferred to post-precompute)
    # Note: items 4-10 require precompute; --sanity-probe-only continues to precompute pass.
    run_sanity_probe_29_0a(train_df, val_df, test_df, pair_runtime_map, args.pairs)

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

    # 7. T3 overlap rate diagnostic (DIAGNOSTIC-ONLY WARN)
    print("Computing T3 overlap rate diagnostic...")
    t3_overlap_train = compute_t3_overlap_rate(train_df)
    if t3_overlap_train["overall"]["warn"]:
        warnings.warn(
            f"T3 overlap rate on train = "
            f"{t3_overlap_train['overall']['overlap_rate']:.3%} "
            f"> {T3_OVERLAP_WARN_RATE:.0%} (DIAGNOSTIC-ONLY WARN; NOT HALT)",
            UserWarning,
            stacklevel=2,
        )
    print(f"  T3 overlap rate on train: {t3_overlap_train['overall']['overlap_rate']:.3%}")

    # 8. Precompute per-target PnL for train + val + test
    print("Precomputing per-target PnL for train + val + test...")
    pnl_per_target_train: dict[str, np.ndarray] = {}
    pnl_per_target_val: dict[str, np.ndarray] = {}
    pnl_per_target_test: dict[str, np.ndarray] = {}
    for target_id in ("T1", "T2", "T3", "T4", "TARGET_CONTROL"):
        t0 = time.time()
        pnl_per_target_train[target_id] = precompute_target_pnls_per_row(
            train_df, pair_runtime_map, target_id
        )
        pnl_per_target_val[target_id] = precompute_target_pnls_per_row(
            val_df, pair_runtime_map, target_id
        )
        pnl_per_target_test[target_id] = precompute_target_pnls_per_row(
            test_df, pair_runtime_map, target_id
        )
        n_finite_test = int(np.isfinite(pnl_per_target_test[target_id]).sum())
        print(
            f"  {target_id}: train n_finite="
            f"{int(np.isfinite(pnl_per_target_train[target_id]).sum())} | "
            f"val n_finite={int(np.isfinite(pnl_per_target_val[target_id]).sum())} | "
            f"test n_finite={n_finite_test} ({time.time() - t0:.1f}s)"
        )

    # 9. Per-target NaN-PnL HALT check
    train_drop_for_nan_pnl_per_target: dict[str, int] = {}
    for target_id in ("T1", "T2", "T3", "T4"):
        pnl_arr = pnl_per_target_train[target_id]
        nan_count = int((~np.isfinite(pnl_arr)).sum())
        train_drop_for_nan_pnl_per_target[target_id] = nan_count

    # 10. Compute target distribution sanity (items 7-10)
    t1_dist = _compute_target_distribution_stats(pnl_per_target_train["T1"], "train")
    t4_dist = _compute_target_distribution_stats(pnl_per_target_train["T4"], "train")
    t2_dist = _compute_target_distribution_stats(pnl_per_target_train["T2"], "train")
    t3_dist = _compute_target_distribution_stats(pnl_per_target_train["T3"], "train")
    # T2 decay factor mean (DIAGNOSTIC; recompute hold_bars distribution by inspecting
    # parameterised barrier — sample 1000 rows for speed)
    t2_decay_sample_size = min(1000, len(train_df))
    sample_idx = np.random.RandomState(42).choice(
        len(train_df), t2_decay_sample_size, replace=False
    )
    decay_factors = []
    train_pair_arr = train_df["pair"].to_numpy()
    train_signal_ts_arr = train_df["signal_ts"].to_numpy()
    train_direction_arr = train_df["direction"].to_numpy()
    train_atr_arr = train_df["atr_at_signal_pip"].to_numpy(dtype=np.float64)
    for i in sample_idx:
        pr = pair_runtime_map.get(str(train_pair_arr[i]))
        if pr is None:
            continue
        _, hold_bars = _compute_realised_barrier_pnl_parameterised(
            str(train_pair_arr[i]),
            pd.Timestamp(train_signal_ts_arr[i]),
            str(train_direction_arr[i]),
            float(train_atr_arr[i]),
            pr,
            T2_K_FAV,
            T2_K_ADV,
            T2_H_M1,
        )
        if hold_bars is not None:
            df = 1.0 - (hold_bars / T2_H_M1)
            decay_factors.append(max(0.0, min(1.0, df)))
    t2_dist["mean_decay_factor"] = float(np.mean(decay_factors)) if decay_factors else float("nan")

    # 11. Sanity probe post-precompute
    sanity = run_sanity_probe_29_0a(
        train_df,
        val_df,
        test_df,
        pair_runtime_map,
        args.pairs,
        days=args.days,
        pnl_train_full_per_target=pnl_per_target_train,
        t1_distribution=t1_dist,
        t2_distribution=t2_dist,
        t3_distribution=t3_dist,
        t3_overlap_report=t3_overlap_train,
        t4_distribution=t4_dist,
        train_drop_for_nan_pnl_per_target=train_drop_for_nan_pnl_per_target,
    )

    if args.sanity_probe_only:
        print("\n--sanity-probe-only set; exiting after probe.")
        if not args.no_write:
            (args.out_dir / "sanity_probe.json").write_text(
                json.dumps(sanity, indent=2, default=str), encoding="utf-8"
            )
            print(f"sanity probe results: {args.out_dir / 'sanity_probe.json'}")
        return 0

    # 12. Build feature matrices on train (NaN-PnL-filtered per target)
    train_label = build_l1_labels_for_dataframe(train_df).to_numpy()
    val_label = build_l1_labels_for_dataframe(val_df).to_numpy()
    test_label = build_l1_labels_for_dataframe(test_df).to_numpy()

    x_train_r7a = train_df[list(ALL_FEATURES_R7A)]
    x_val_r7a = val_df[list(ALL_FEATURES_R7A)]
    x_test_r7a = test_df[list(ALL_FEATURES_R7A)]

    # 13. 5-fold OOF + S-E regressor per target (DIAGNOSTIC + production score)
    print("Fitting 5 S-E regressors (4 per-target + 1 target-control) + OOF...")
    regressors: dict[str, object] = {}
    val_pred_per_target: dict[str, np.ndarray] = {}
    test_pred_per_target: dict[str, np.ndarray] = {}
    train_pred_per_target: dict[str, np.ndarray] = {}
    oof_corr_diag_per_target: dict[str, dict] = {}
    regression_diag_per_target: dict[str, dict] = {}
    feature_importance_per_target: dict[str, dict] = {}
    predicted_pnl_distribution_per_target: dict[str, dict] = {}

    for target_id in ("T1", "T2", "T3", "T4", "TARGET_CONTROL"):
        t0 = time.time()
        pnl_target = pnl_per_target_train[target_id]
        nan_mask = ~np.isfinite(pnl_target)
        x_train_clean = x_train_r7a.loc[~nan_mask].reset_index(drop=True)
        pnl_train_clean = pnl_target[~nan_mask]

        # OOF diag
        fold_idx = make_oof_fold_assignment(
            len(pnl_train_clean), n_folds=OOF_N_FOLDS, seed=OOF_SEED
        )
        oof_preds = fit_oof_regression_diagnostic(x_train_clean, pnl_train_clean, fold_idx)
        oof_corr_diag_per_target[target_id] = compute_oof_correlation_diagnostic(
            oof_preds, pnl_train_clean, fold_idx
        )

        # Production fit
        reg = build_pipeline_lightgbm_regression_widened()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reg.fit(x_train_clean, pnl_train_clean)
        regressors[target_id] = reg

        # Predict on train/val/test
        train_pred_per_target[target_id] = compute_picker_score_s_e(reg, x_train_r7a)
        val_pred_per_target[target_id] = compute_picker_score_s_e(reg, x_val_r7a)
        test_pred_per_target[target_id] = compute_picker_score_s_e(reg, x_test_r7a)

        # Regression diagnostic
        regression_diag_per_target[target_id] = {
            "train": compute_regression_diagnostic(
                pnl_per_target_train[target_id], train_pred_per_target[target_id]
            ),
            "val": compute_regression_diagnostic(
                pnl_per_target_val[target_id], val_pred_per_target[target_id]
            ),
            "test": compute_regression_diagnostic(
                pnl_per_target_test[target_id], test_pred_per_target[target_id]
            ),
        }
        feature_importance_per_target[target_id] = compute_feature_importance_diagnostic(reg)

        # Predicted PnL distribution
        pred_dist: dict = {}
        for split_name, pred in [
            ("train", train_pred_per_target[target_id]),
            ("val", val_pred_per_target[target_id]),
            ("test", test_pred_per_target[target_id]),
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
        predicted_pnl_distribution_per_target[target_id] = pred_dist
        print(f"  {target_id}: fit+predict {time.time() - t0:.1f}s")

    # 14. Fit shared S-B multiclass head for per-target baselines
    print("Fitting shared S-B multiclass head (R7-A) for per-target baselines...")
    t0 = time.time()
    target_for_multiclass = pnl_per_target_train[
        "TARGET_CONTROL"
    ]  # use control target's drop pattern
    nan_mask_multiclass = ~np.isfinite(target_for_multiclass)
    x_train_clean_mc = x_train_r7a.loc[~nan_mask_multiclass].reset_index(drop=True)
    train_label_clean_mc = train_label[~nan_mask_multiclass]
    multiclass_pipeline = build_pipeline_lightgbm_multiclass_widened()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        multiclass_pipeline.fit(x_train_clean_mc, train_label_clean_mc)
    val_raw_probs = _multiclass_to_class_probs(multiclass_pipeline, x_val_r7a, NUM_CLASSES)
    test_raw_probs = _multiclass_to_class_probs(multiclass_pipeline, x_test_r7a, NUM_CLASSES)
    val_score_s_b_raw = compute_picker_score_s_b_raw(val_raw_probs)
    test_score_s_b_raw = compute_picker_score_s_b_raw(test_raw_probs)
    print(f"  multiclass: fit+predict {time.time() - t0:.1f}s")

    # 15. Build cells
    cells = build_a2_cells()
    print(f"Built {len(cells)} cells")

    # 16. Per-cell evaluation
    print("Per-cell evaluation...")
    cell_results: list[dict] = []
    for i, cell in enumerate(cells):
        t_cell = time.time()
        target_id = cell["target_kind"]
        pnl_val = pnl_per_target_val[target_id]
        pnl_test = pnl_per_target_test[target_id]
        score_type = cell["score_type"]
        if score_type == "s_e_per_target":
            v_score = val_pred_per_target[target_id]
            t_score = test_pred_per_target[target_id]
            fi = feature_importance_per_target[target_id]
        elif score_type == "s_e_target_control":
            v_score = val_pred_per_target["TARGET_CONTROL"]
            t_score = test_pred_per_target["TARGET_CONTROL"]
            fi = feature_importance_per_target["TARGET_CONTROL"]
        elif score_type == "s_b_raw_per_target_baseline":
            v_score = val_score_s_b_raw
            t_score = test_score_s_b_raw
            fi = compute_feature_importance_diagnostic(multiclass_pipeline)
        else:
            raise ValueError(f"Unknown score_type: {score_type}")

        result = evaluate_quantile_cell_29_0a(
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
            pnl_val,
            pnl_test,
            fi,
        )
        cell_results.append(result)
        rm = result.get("test_realised_metrics", {})
        sp = result.get("test_formal_spearman", float("nan"))
        sq = result.get("selected_q_percent")
        print(
            f"  cell {i + 1}/{len(cells)} {cell['id']} | q*={sq} | "
            f"val_sharpe={result.get('val_realised_sharpe', float('nan')):+.3f} "
            f"val_n={result.get('val_n_trades', 0):>6} | "
            f"test_sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"test_n={rm.get('n_trades', 0):>6} test_sp={sp:+.4f} "
            f"({time.time() - t_cell:.1f}s)"
        )

    # 17. Build Phase 29 §10 per-target baseline JSON
    print("\n=== Phase 29 §10 per-target baseline (Option 9c) ===")
    phase29_section10_per_target_baseline: dict[str, dict] = {}
    for target_id in ("T1", "T2", "T3", "T4"):
        baseline_cell_id = f"C-d1-{target_id}-baseline"
        baseline_cell = next((c for c in cell_results if c["cell"]["id"] == baseline_cell_id), None)
        if baseline_cell is None or baseline_cell.get("h_state") != "OK":
            print(f"  WARN: {baseline_cell_id} missing or h_state != OK")
            phase29_section10_per_target_baseline[target_id] = {
                "val_sharpe": float("nan"),
                "test_n_trades": 0,
                "test_sharpe": float("nan"),
                "test_ann_pnl": float("nan"),
            }
            continue
        rm = baseline_cell.get("test_realised_metrics", {})
        phase29_section10_per_target_baseline[target_id] = {
            "val_sharpe": baseline_cell.get("val_realised_sharpe", float("nan")),
            "test_n_trades": int(rm.get("n_trades", 0)),
            "test_sharpe": float(rm.get("sharpe", float("nan"))),
            "test_ann_pnl": float(rm.get("annual_pnl", float("nan"))),
        }
        print(
            f"  {target_id}: n_trades={int(rm.get('n_trades', 0))}, "
            f"Sharpe={float(rm.get('sharpe', float('nan'))):+.4f}, "
            f"ann_pnl={float(rm.get('annual_pnl', float('nan'))):+.1f}"
        )

    # 18. Per-target baseline FAIL-FAST (internal consistency; compute twice and compare)
    # For FAIL-FAST, we compute baselines a second time and verify match
    print("\n=== Per-target baseline FAIL-FAST (internal consistency) ===")
    phase29_section10_per_target_baseline_second: dict[str, dict] = {}
    for target_id in ("T1", "T2", "T3", "T4"):
        baseline_cell_id = f"C-d1-{target_id}-baseline"
        baseline_cell = next((c for c in cell_results if c["cell"]["id"] == baseline_cell_id), None)
        if baseline_cell is None:
            phase29_section10_per_target_baseline_second[target_id] = {
                "val_sharpe": float("nan"),
                "test_n_trades": 0,
                "test_sharpe": float("nan"),
                "test_ann_pnl": float("nan"),
            }
            continue
        # Re-evaluate the baseline cell using the same inputs (deterministic check)
        pnl_val = pnl_per_target_val[target_id]
        pnl_test = pnl_per_target_test[target_id]
        cutoff_val = fit_quantile_cutoff_on_val(val_score_s_b_raw, PER_TARGET_BASELINE_Q_PERCENT)
        traded_val = np.isfinite(val_score_s_b_raw) & (val_score_s_b_raw >= cutoff_val)
        traded_test = np.isfinite(test_score_s_b_raw) & (test_score_s_b_raw >= cutoff_val)
        finite_val_pnl = pnl_val[traded_val & np.isfinite(pnl_val)]
        finite_test_pnl = pnl_test[traded_test & np.isfinite(pnl_test)]
        val_metrics = compute_8_gate_from_pnls(finite_val_pnl)["metrics"]
        test_metrics = compute_8_gate_from_pnls(finite_test_pnl)["metrics"]
        phase29_section10_per_target_baseline_second[target_id] = {
            "val_sharpe": float(val_metrics.get("sharpe", float("nan"))),
            "test_n_trades": int(test_metrics.get("n_trades", 0)),
            "test_sharpe": float(test_metrics.get("sharpe", float("nan"))),
            "test_ann_pnl": float(test_metrics.get("annual_pnl", float("nan"))),
        }
    try:
        per_target_baseline_consistency_report = check_per_target_baseline_consistency(
            phase29_section10_per_target_baseline,
            phase29_section10_per_target_baseline_second,
        )
        print(f"  all_consistent={per_target_baseline_consistency_report['all_consistent']}")
    except PerTargetBaselineMismatchError as exc:
        print(f"  HALT: {exc}")
        return 3

    # 19. Archived Phase 28 §10 drift (DIAGNOSTIC-ONLY)
    archived_phase28_drift_report = compute_archived_phase28_drift(
        phase29_section10_per_target_baseline
    )
    print("\n=== Archived Phase 28 §10 drift (DIAGNOSTIC-ONLY) ===")
    for target_id, d in archived_phase28_drift_report.items():
        print(
            f"  {target_id}: n_trades Δ={d.get('test_n_trades_delta')}, "
            f"Sharpe Δ={d.get('test_sharpe_delta', float('nan')):+.4f}, "
            f"ann_pnl Δ={d.get('test_ann_pnl_delta', float('nan')):+.1f}"
        )

    # 20. C-d1-target-control drift vs 27.0d C-se (DIAGNOSTIC-ONLY WARN; 6th-phase chain)
    print("\n=== C-d1-target-control drift vs 27.0d C-se (6th-phase chain; DIAGNOSTIC WARN) ===")
    c_d1_target_control_cell = next(
        (c for c in cell_results if c["cell"]["id"] == "C-d1-target-control"), None
    )
    if c_d1_target_control_cell is None or c_d1_target_control_cell.get("h_state") != "OK":
        target_control_drift_report = {
            "source": "n/a",
            "warn": True,
            "all_within_tolerance": False,
            "note": "C-d1-target-control missing or h_state != OK",
            "chain_position": "6th anchor",
        }
    else:
        target_control_drift_report = compute_c_d1_target_control_drift_check(
            c_d1_target_control_cell
        )
        if target_control_drift_report["warn"]:
            warnings.warn(
                "C-d1-target-control drift vs 27.0d C-se exceeds tolerance "
                "(DIAGNOSTIC-ONLY WARN per PR #350 §9.3 NG#A2-3; NOT HALT)",
                UserWarning,
                stacklevel=2,
            )
        print(
            f"  all_within_tolerance={target_control_drift_report.get('all_within_tolerance')} "
            f"(WARN={target_control_drift_report.get('warn')})"
        )

    # 21. Within-eval drift per target (PARTIAL_DRIFT_TARGET_REPLICA detection)
    print("\n=== Within-eval ablation drift per target (vs C-d1-target-control) ===")
    within_eval_drift_per_target: dict[str, dict] = {}
    for target_id in ("T1", "T2", "T3", "T4"):
        target_cell_id = f"C-d1-{target_id}"
        target_cell = next((c for c in cell_results if c["cell"]["id"] == target_cell_id), None)
        if target_cell is None or c_d1_target_control_cell is None:
            within_eval_drift_per_target[target_id] = {
                "all_within_tolerance": False,
                "warn": True,
                "note": "per-target cell or target-control missing",
            }
        else:
            within_eval_drift_per_target[target_id] = compute_within_eval_target_drift_check(
                target_cell, c_d1_target_control_cell
            )
        d = within_eval_drift_per_target[target_id]
        nd = d.get("n_trades_delta", "-")
        shd = d.get("sharpe_delta", float("nan"))
        apd = d.get("ann_pnl_delta", float("nan"))
        shd_str = f"{shd:+.4e}" if isinstance(shd, float) and np.isfinite(shd) else str(shd)
        apd_str = f"{apd:+.3f}" if isinstance(apd, float) and np.isfinite(apd) else str(apd)
        print(
            f"  {target_id}: all_within={d.get('all_within_tolerance')} "
            f"(n_trades_Δ={nd}, Sharpe_Δ={shd_str}, ann_pnl_Δ={apd_str})"
        )

    # 22. Val-selection + cross-cell verdict
    # NOTE: per-target baseline cells excluded from val-selection pool (NG#A2-3)
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
            f"val Sharpe={sel.get('val_realised_sharpe', float('nan')):+.4f}"
        )
        print(
            f"  test Sharpe={rm.get('sharpe', float('nan')):+.4f}; "
            f"ann_pnl={rm.get('annual_pnl', 0.0):+.1f}; "
            f"n_trades={rm.get('n_trades', 0)}"
        )
    print(f"\n=== Cross-cell aggregate: {aggregate_info['aggregate_verdict']} ===")

    # 23. H-D1 per-target outcomes
    print("\n=== H-D1 4-outcome ladder per target ===")
    h_d1_per_target: list[dict] = []
    for target_id in ("T1", "T2", "T3", "T4"):
        target_cell_id = f"C-d1-{target_id}"
        target_cell = next((c for c in cell_results if c["cell"]["id"] == target_cell_id), None)
        if target_cell is None:
            h_d1_per_target.append(
                {
                    "cell_id": target_cell_id,
                    "target_id": target_id,
                    "outcome": H_D1_OUTCOME_NEEDS_REVIEW,
                    "row_matched": 0,
                    "reason": "cell missing",
                }
            )
            continue
        per_target_baseline_val_sharpe = float(
            phase29_section10_per_target_baseline.get(target_id, {}).get("val_sharpe", float("nan"))
        )
        per_target_baseline_consistent = bool(
            per_target_baseline_consistency_report["per_target"]
            .get(target_id, {})
            .get("all_match", False)
        )
        outcome = compute_h_d1_outcome_per_target(
            target_cell,
            per_target_baseline_consistent,
            within_eval_drift_per_target.get(target_id, {}),
            target_id,
            per_target_baseline_val_sharpe,
        )
        h_d1_per_target.append(outcome)
        print(
            f"  {target_id}: {outcome.get('outcome')} (row {outcome.get('row_matched')}) "
            f"— {outcome.get('reason', '-')[:80]}"
        )

    # 24. Aggregate H-D1 verdict
    h_d1_aggregate = compute_h_d1_aggregate_verdict(h_d1_per_target)
    print(f"\n=== Aggregate H-D1 verdict: {h_d1_aggregate.get('aggregate_verdict')} ===")
    print(f"=== A2-narrow status: {h_d1_aggregate.get('a2_narrow_status')} ===")
    print(f"=== R-T3 absorption status: {h_d1_aggregate.get('r_t3_absorption_status')} ===")
    print(f"=== Routing: {h_d1_aggregate.get('routing_implication')} ===")

    if args.no_write:
        return 0

    # 25. Top-tail regime audit per target
    top_tail_regime_audit_per_target: dict[str, dict] = {}
    for target_id in ("T1", "T2", "T3", "T4", "TARGET_CONTROL"):
        top_tail_regime_audit_per_target[target_id] = compute_top_tail_regime_audit_for_a2(
            val_pred_per_target[target_id], val_df
        )

    # 26. Write Phase 29 §10 per-target baseline JSON
    phase29_baseline_json = {
        "phase29_section10_per_target_baseline": phase29_section10_per_target_baseline,
        "archived_phase28_section10": {
            "test_n_trades": int(ARCHIVED_PHASE_28_SECTION10_N_TRADES),
            "test_sharpe": float(ARCHIVED_PHASE_28_SECTION10_SHARPE),
            "test_ann_pnl": float(ARCHIVED_PHASE_28_SECTION10_ANN_PNL),
            "val_sharpe": float(ARCHIVED_PHASE_28_SECTION10_VAL_SHARPE),
        },
        "fail_fast_consistency_report": per_target_baseline_consistency_report,
        "archived_phase28_drift_diagnostic": archived_phase28_drift_report,
    }
    (args.out_dir / "phase29_section10_per_target_baseline.json").write_text(
        json.dumps(phase29_baseline_json, indent=2, default=str), encoding="utf-8"
    )

    # 27. Write 25-section eval_report.md
    report_path = args.out_dir / "eval_report.md"
    write_eval_report_29_0a(
        report_path,
        cell_results,
        val_select,
        verdict_info,
        aggregate_info,
        phase29_section10_per_target_baseline,
        per_target_baseline_consistency_report,
        archived_phase28_drift_report,
        target_control_drift_report,
        h_d1_per_target,
        h_d1_aggregate,
        within_eval_drift_per_target,
        sanity,
        drop_stats_r7a,
        (t_min, t70, t85, t_max),
        preflight_diag,
        len(cells),
        feature_importance_per_target,
        regression_diag_per_target,
        oof_corr_diag_per_target,
        predicted_pnl_distribution_per_target,
        top_tail_regime_audit_per_target,
        t3_overlap_train,
    )
    print(f"\nReport: {report_path}")

    # 28. Persist sweep + aggregate artifacts
    summary_rows: list[dict] = []
    for c in cell_results:
        cell = c["cell"]
        rm = c.get("test_realised_metrics", {})
        sp = c.get("test_formal_spearman", float("nan"))
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
                "target_kind": cell.get("target_kind", "-"),
                "is_baseline": cell.get("is_baseline", False),
                "quantile_percents": list(cell.get("quantile_percents", ())),
                "n_train": c.get("n_train", 0),
                "n_val": c.get("n_val", 0),
                "n_test": c.get("n_test", 0),
                "selected_q_percent": sq_serialised,
                "selected_cutoff": sc_serialised,
                "val_realised_sharpe": c.get("val_realised_sharpe", float("nan")),
                "val_n_trades": c.get("val_n_trades", 0),
                "test_sharpe": rm.get("sharpe", float("nan")),
                "test_annual_pnl": rm.get("annual_pnl", float("nan")),
                "test_n_trades": rm.get("n_trades", 0),
                "test_formal_spearman": sp,
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
    aggregate["phase29_section10_per_target_baseline"] = phase29_section10_per_target_baseline
    aggregate["per_target_baseline_consistency_report"] = per_target_baseline_consistency_report
    aggregate["archived_phase28_drift_diagnostic"] = archived_phase28_drift_report
    aggregate["target_control_drift_report"] = target_control_drift_report
    aggregate["within_eval_drift_per_target"] = within_eval_drift_per_target
    aggregate["h_d1_per_target"] = h_d1_per_target
    aggregate["h_d1_aggregate"] = h_d1_aggregate
    aggregate["top_tail_regime_audit_per_target"] = top_tail_regime_audit_per_target
    aggregate["closed_target_allowlist"] = {
        "T1": {"name": "fixed_horizon_executable_close_pnl", "h_m1": T1_H_M1, "no_barrier": True},
        "T2": {
            "name": "time_weighted_linear_decay",
            "k_fav": T2_K_FAV,
            "k_adv": T2_K_ADV,
            "h_m1": T2_H_M1,
        },
        "T3": {"name": "multi_horizon_sum", "horizons": list(T3_HORIZONS)},
        "T4": {"name": "asymmetric_barrier", "k_fav": T4_K_FAV, "k_adv": T4_K_ADV, "h_m1": T4_H_M1},
    }
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
