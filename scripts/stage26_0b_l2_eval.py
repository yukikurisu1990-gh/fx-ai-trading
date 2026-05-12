"""Stage 26.0b-β L-2 generic path-quality regression eval.

Implements the binding contract from PR #301 (26.0a-α design memo) plus
PR #302 (26.0a-α-rev1 threshold-selection design revision).

Reads 25.0a-β path-quality labels, constructs L-3 EV targets per the
26.0a-α §3 / §3.1 binding rules (mid-to-mid base PnL, spread subtracted
exactly once, optional ATR normalisation, optional winsorisation),
trains 24 cells of regression with chronological 70/15/15 split,
performs validation-only cell+threshold selection on the PRIMARY
quantile family, evaluates test ONCE on the val-selected (cell, q)
pair using realised barrier PnL via M1 path re-traverse. Secondary
absolute-threshold family (with negative candidates per rev1 §5) is
reported as diagnostic-only.

MANDATORY CLAUSES (verbatim per 26.0a-α §9 + rev1 §11; carried forward):

1. Phase 26 framing.
   Phase 26 is the entry-side return on alternative label / target
   designs on the 20-pair canonical universe. ADOPT requires both H2
   PASS and the full 8-gate A0-A5 harness.

2. Diagnostic columns prohibition.
   Calibration / threshold-sweep / directional-comparison columns are
   diagnostic-only. ADOPT_CANDIDATE routing must not depend on any
   single one of them.

3. γ closure preservation.
   Phase 24 γ hard-close (PR #279) is unmodified.

4. Production-readiness preservation.
   X-v2 OOS gating remains required before any production deployment.
   Production v9 20-pair (Phase 9.12 closure) remains untouched.

5. NG#10 / NG#11 not relaxed.

6. Phase 26 scope.
   Phase 26 is NOT a continuation of Phase 25's feature-axis sweep.
   F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed.

PRODUCTION-MISUSE GUARDS (verbatim per 26.0a-α §5.1):

GUARD 1 — research-not-production: L-3 features stay in scripts/; not
auto-routed to feature_service.py.
GUARD 2 — threshold-sweep-diagnostic: any threshold sweep here is
diagnostic-only.
GUARD 3 — directional-comparison-diagnostic: any long/short
decomposition is diagnostic-only.

REV1 KEY POINTS:

- PRIMARY threshold family: quantile-based, top q% of validation
  predictions, q in {5, 10, 20, 30, 40}. Cutoff is fit on val ONLY and
  applied as a scalar to test predictions. NO full-sample qcut.
- SECONDARY DIAGNOSTIC threshold family: negative absolute candidates
  ({-5, -3, -1, 0, +1} pip for raw; {-0.5, -0.3, -0.1, 0.0, +0.1} for
  ATR-normalised). NOT used for verdict.
- Cell-and-threshold selection uses the PRIMARY (cell, q) pairs.
- Test set is touched once per cell — on the val-selected (cell*, q*)
  pair using its val-fit cutoff scalar.
- Verdict tree inherits original 26.0a-α §7 unchanged: H2 PASS alone is
  NOT ADOPT_CANDIDATE.

H1 two-tier (inherited from original §6):
- H1-weak: test Spearman ρ > 0.05
- H1-meaningful: test Spearman ρ ≥ 0.10 (formal H1 PASS)

H3 baseline: Phase 25 F1 best realised Sharpe = -0.192.

PERFORMANCE NOTE:
Realised barrier PnL is precomputed ONCE per split (val and test) and
cached as a per-row array. All threshold evaluations are array-filter
operations on the cache. This avoids recomputing M1 path traversal for
each (cell, threshold) pair.
"""

from __future__ import annotations

import argparse
import importlib
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
from scipy.stats import pearsonr, spearmanr
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage26_0b"
DATA_DIR = REPO_ROOT / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage25_0b = importlib.import_module("stage25_0b_f1_volatility_expansion_eval")

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


# ---------------------------------------------------------------------------
# Binding constants (per 26.0a-α + 26.0a-α-rev1)
# ---------------------------------------------------------------------------

# D-3: barrier geometry inherited unchanged
K_FAV = stage25_0b.K_FAV  # 1.5
K_ADV = stage25_0b.K_ADV  # 1.0
H_M1_BARS = stage25_0b.H_M1_BARS  # 60

# D-5: target scale sweep knob
TARGET_SCALES = ("raw_pip", "atr_normalised")

# D-6: outlier clipping sweep knob
CLIP_MODES = ("none", "q01_q99")

# Model dimension
MODEL_NAMES = ("LinearRegression", "Ridge", "LightGBM")
RIDGE_ALPHA = 1.0  # Ridge is deterministic without random_state

# 26.0a-α §4.1 binding fixed conservative LightGBM config
LIGHTGBM_FIXED_CONFIG = dict(
    n_estimators=200,
    learning_rate=0.03,
    num_leaves=31,
    max_depth=4,
    min_child_samples=100,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
)

# === REV1: PRIMARY threshold family — quantile-based (top q% of val) ===
THRESHOLDS_QUANTILE_PERCENTS = (5, 10, 20, 30, 40)

# === REV1: SECONDARY DIAGNOSTIC threshold family — negative absolute candidates ===
NEG_THRESHOLDS_RAW_PIP = (-5.0, -3.0, -1.0, 0.0, 1.0)
NEG_THRESHOLDS_ATR = (-0.5, -0.3, -0.1, 0.0, 0.1)

# D-6 winsorisation quantiles
WINSORISE_LO_Q = 0.01
WINSORISE_HI_Q = 0.99

# H1 two-tier thresholds (26.0a-α §6, inherited)
H1_WEAK_THRESHOLD = 0.05
H1_MEANINGFUL_THRESHOLD = 0.10

# H3 reference (Phase 25 F1 best realised Sharpe per #284; Decision B inherited)
H3_REFERENCE_SHARPE = -0.192

# 26.0b-α §4.1 binding: CONCENTRATION_HIGH flag at >= 80% single-pair share on val.
# Diagnostic-only — NOT consulted by select_cell_validation_only or assign_verdict.
CONCENTRATION_HIGH_THRESHOLD = 0.80

# Span budgets
TEST_SPAN_YEARS = SPAN_YEARS * (1.0 - TRAIN_FRAC - VAL_FRAC)
VAL_SPAN_YEARS = SPAN_YEARS * VAL_FRAC

CATEGORICAL_COLS = ["pair", "direction"]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class L3PreflightError(RuntimeError):
    """Raised when 26.0a-β pre-flight contract fails (halt-and-report)."""


REQUIRED_LABEL_COLUMNS = (
    "pair",
    "signal_ts",
    "direction",
    "horizon_bars",
    "entry_ask",
    "entry_bid",
    "spread_at_signal_pip",
    "atr_at_signal_pip",
    "time_to_fav_bar",
    "time_to_adv_bar",
    "same_bar_both_hit",
    "label",
)


def verify_l3_preflight(labels: pd.DataFrame, pairs: list[str]) -> dict:
    """Halt-and-report if required dataset columns are missing or invalid."""
    missing = [c for c in REQUIRED_LABEL_COLUMNS if c not in labels.columns]
    if missing:
        raise L3PreflightError(f"labels missing required columns: {missing}")

    h_uniq = labels["horizon_bars"].unique()
    if len(h_uniq) != 1 or int(h_uniq[0]) != H_M1_BARS:
        raise L3PreflightError(
            f"horizon_bars expected constant {H_M1_BARS}; got {sorted(h_uniq.tolist())}"
        )

    for pair in pairs:
        path = DATA_DIR / f"candles_{pair}_M1_{SPAN_DAYS}d_BA.jsonl"
        if not path.exists():
            raise L3PreflightError(f"{pair}: M1 BA jsonl missing at {path}")

    diag = {
        "label_rows": int(len(labels)),
        "horizon_bars": int(H_M1_BARS),
        "pairs": len(pairs),
        "required_columns_ok": True,
    }
    try:
        import lightgbm  # noqa: F401

        diag["lightgbm_available"] = True
        diag["lightgbm_version"] = lightgbm.__version__
    except ImportError:
        diag["lightgbm_available"] = False
        diag["lightgbm_version"] = None
    return diag


# ---------------------------------------------------------------------------
# Barrier outcome derivation
# ---------------------------------------------------------------------------


def determine_barrier_outcome(time_to_fav: int, time_to_adv: int, same_bar_both: bool) -> str:
    """Return 'TP', 'SL', or 'TIME' per 25.0a-β same-bar-SL-first semantics."""
    tf = int(time_to_fav)
    ta = int(time_to_adv)
    sb = bool(same_bar_both)
    if tf >= 0 and ta >= 0:
        if sb or ta <= tf:
            return "SL"
        return "TP"
    if ta >= 0:
        return "SL"
    if tf >= 0:
        return "TP"
    return "TIME"


def _derive_outcomes_vectorised(df: pd.DataFrame) -> pd.Series:
    tf = df["time_to_fav_bar"].astype("int64").to_numpy()
    ta = df["time_to_adv_bar"].astype("int64").to_numpy()
    sb = df["same_bar_both_hit"].to_numpy().astype(bool)
    outcome = np.full(len(df), "TIME", dtype=object)
    both_hit = (tf >= 0) & (ta >= 0)
    only_adv = (ta >= 0) & ~both_hit
    only_fav = (tf >= 0) & ~both_hit
    sl_when_both = both_hit & (sb | (ta <= tf))
    tp_when_both = both_hit & ~sl_when_both
    outcome[sl_when_both] = "SL"
    outcome[tp_when_both] = "TP"
    outcome[only_adv] = "SL"
    outcome[only_fav] = "TP"
    return pd.Series(outcome, index=df.index)


# ---------------------------------------------------------------------------
# L-3 label construction (binding per 26.0a-α §3 / §3.1)
# ---------------------------------------------------------------------------


def compute_time_outcome_mid_exit(
    pair: str,
    signal_ts: pd.Timestamp,
    pair_runtime: dict,
) -> float | None:
    """For TIME outcome, look up M1 mid close at entry_idx + H_M1_BARS - 1."""
    m1_pos = pair_runtime["m1_pos"]
    target_entry_ts = signal_ts + pd.Timedelta(minutes=1)
    if target_entry_ts not in m1_pos.index:
        return None
    entry_idx = int(m1_pos.loc[target_entry_ts])
    exit_idx = entry_idx + H_M1_BARS - 1
    if exit_idx >= pair_runtime["n_m1"]:
        return None
    bid_c = pair_runtime["bid_c"][exit_idx]
    ask_c = pair_runtime["ask_c"][exit_idx]
    return float((bid_c + ask_c) / 2.0)


def _compute_time_outcome_base_pnl(
    pair: str,
    signal_ts: pd.Timestamp,
    direction: str,
    entry_ask: float,
    entry_bid: float,
    pair_runtime: dict,
) -> float | None:
    mid_exit = compute_time_outcome_mid_exit(pair, signal_ts, pair_runtime)
    if mid_exit is None:
        return None
    mid_entry = (entry_ask + entry_bid) / 2.0
    pip = pair_runtime["pip"]
    if direction == "long":
        return (mid_exit - mid_entry) / pip
    return (mid_entry - mid_exit) / pip


def build_l2_labels_for_dataframe(
    df: pd.DataFrame,
    pair_runtime_map: dict[str, dict],
    target_scale: str,
) -> pd.Series:
    """Vectorised L-2 label construction.

    Per 26.0b-α §3.1 binding (L-2 vs L-3 single-axis change):
      base_pnl    = mid-to-mid PnL (deterministic for TP/SL; M1 lookup for TIME)
      label_pre   = base_pnl                          # NO D-4 spread subtraction
      label       = label_pre / atr_at_signal_pip if 'atr_normalised' (D-5)
                  = label_pre                      if 'raw_pip'        (D-5)
    """
    if target_scale not in TARGET_SCALES:
        raise ValueError(f"invalid target_scale: {target_scale}")
    outcome = _derive_outcomes_vectorised(df)
    atr_pip = df["atr_at_signal_pip"].to_numpy(dtype=np.float64)

    base_pnl = np.where(
        outcome.to_numpy() == "TP",
        K_FAV * atr_pip,
        np.where(outcome.to_numpy() == "SL", -K_ADV * atr_pip, np.nan),
    )

    time_mask = outcome.to_numpy() == "TIME"
    if time_mask.any():
        time_rows = df.loc[time_mask, ["pair", "signal_ts", "direction", "entry_ask", "entry_bid"]]
        time_base_pnl = np.full(time_mask.sum(), np.nan, dtype=np.float64)
        for i, (_, row) in enumerate(time_rows.iterrows()):
            pr = pair_runtime_map.get(row["pair"])
            if pr is None:
                continue
            val = _compute_time_outcome_base_pnl(
                row["pair"],
                row["signal_ts"],
                row["direction"],
                float(row["entry_ask"]),
                float(row["entry_bid"]),
                pr,
            )
            if val is not None:
                time_base_pnl[i] = val
        base_pnl[time_mask] = time_base_pnl

    # L-2: NO D-4 spread subtraction. label_pre = base_pnl directly.
    label_pre = base_pnl

    # D-5: target scale
    if target_scale == "atr_normalised":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            label = label_pre / atr_pip
        label[~np.isfinite(label)] = np.nan
        return pd.Series(label, index=df.index)
    return pd.Series(label_pre, index=df.index)


# ---------------------------------------------------------------------------
# Winsorisation (D-6; train-only-fit; harness PnL NEVER touched)
# ---------------------------------------------------------------------------


def fit_winsorise_train(
    train_y: pd.Series, q_low: float = WINSORISE_LO_Q, q_high: float = WINSORISE_HI_Q
) -> tuple[float, float]:
    finite = train_y.dropna()
    if len(finite) < 30:
        return (float("-inf"), float("inf"))
    return (float(finite.quantile(q_low)), float(finite.quantile(q_high)))


def apply_winsorise(y: pd.Series, lo: float, hi: float) -> pd.Series:
    return y.clip(lower=lo, upper=hi)


# ---------------------------------------------------------------------------
# Regression model builders
# ---------------------------------------------------------------------------


def build_pipeline_ridge() -> Pipeline:
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS)])
    return Pipeline([("pre", pre), ("reg", Ridge(alpha=RIDGE_ALPHA))])


def build_pipeline_linear() -> Pipeline:
    pre = ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS)])
    return Pipeline([("pre", pre), ("reg", LinearRegression())])


def build_pipeline_lightgbm() -> Pipeline:
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
                "reg",
                lgb.LGBMRegressor(**LIGHTGBM_FIXED_CONFIG, verbose=-1),
            ),
        ]
    )


def build_pipeline(model_name: str) -> Pipeline:
    if model_name == "Ridge":
        return build_pipeline_ridge()
    if model_name == "LinearRegression":
        return build_pipeline_linear()
    if model_name == "LightGBM":
        return build_pipeline_lightgbm()
    raise ValueError(f"unknown model: {model_name}")


# ---------------------------------------------------------------------------
# Sweep grid (24 cells; 16 if LightGBM unavailable)
# ---------------------------------------------------------------------------


def build_cells(include_lightgbm: bool = True) -> list[dict]:
    """L-2 sweep grid: 12 cells (Decision A; no spread / pair-set knobs).

    2 (target_scale) × 2 (clip) × 3 (model) = 12 cells (or 8 if LightGBM unavailable).
    """
    cells: list[dict] = []
    models = MODEL_NAMES if include_lightgbm else ("LinearRegression", "Ridge")
    for scale in TARGET_SCALES:
        for clip_mode in CLIP_MODES:
            for model in models:
                cells.append(
                    {
                        "scale": scale,
                        "clip": clip_mode,
                        "model": model,
                    }
                )
    return cells


# ---------------------------------------------------------------------------
# Realised PnL precomputation (per row, cached across cells)
# ---------------------------------------------------------------------------


def precompute_realised_pnl_per_row(
    df: pd.DataFrame, pair_runtime_map: dict[str, dict]
) -> np.ndarray:
    """Compute realised barrier PnL for EVERY row of df.

    Returns np.ndarray of length len(df). NaN where path window is invalid.

    Realised PnL depends only on (pair, signal_ts, direction, atr_at_signal_pip)
    and the M1 path data — NOT on label-class, threshold, model, or any cell
    parameter. So it can be precomputed once per split and reused across all
    24 cells. This is the rev1 optimisation that makes quantile-family
    evaluation tractable (quantile=40% would otherwise require ~10s × 5
    quantiles × 24 cells of redundant M1 path traversal per split).
    """
    n = len(df)
    out = np.full(n, np.nan, dtype=np.float64)
    pairs = df["pair"].to_numpy()
    signal_ts = df["signal_ts"].to_numpy()
    directions = df["direction"].to_numpy()
    atrs = df["atr_at_signal_pip"].to_numpy(dtype=np.float64)
    for i in range(n):
        pr = pair_runtime_map.get(str(pairs[i]))
        if pr is None:
            continue
        r = _compute_realised_barrier_pnl(
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
# Threshold evaluation primitives (quantile + absolute families)
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
    pred: np.ndarray,
    threshold: float,
    span_years: float,
) -> dict:
    """Apply a scalar threshold to predictions; compute realised metrics.

    pnl_per_row: precomputed realised PnL per row (NaN where invalid).
    pred:        predictions aligned with pnl_per_row.
    """
    traded_mask = pred >= threshold
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
        "realised_pnls": realised,  # kept for 8-gate computation downstream
    }


def fit_quantile_cutoff_on_val(pred_val: np.ndarray, q_percent: int) -> float:
    """Fit the top-q% cutoff on validation predictions only.

    Returns the scalar cutoff c such that predictions >= c are the top
    q% of pred_val by predicted EV. Per rev1 §4 binding: val ONLY.
    """
    finite = pred_val[np.isfinite(pred_val)]
    if len(finite) < 10:
        return float("inf")  # degenerate: no trades fire downstream
    return float(np.quantile(finite, 1.0 - q_percent / 100.0))


def evaluate_quantile_family(
    pred_val: np.ndarray,
    pnl_val_per_row: np.ndarray,
    pred_test: np.ndarray,
    pnl_test_per_row: np.ndarray,
    span_years_val: float,
    span_years_test: float,
) -> list[dict]:
    """PRIMARY family — per rev1 §3.

    For each q in {5, 10, 20, 30, 40}:
      1. Fit cutoff_q on val predictions ONLY.
      2. Evaluate val realised PnL (for threshold selection).
      3. Evaluate test realised PnL using the SAME scalar cutoff_q.

    Returns list of dicts with val/test metrics per q.
    """
    results: list[dict] = []
    for q_pct in THRESHOLDS_QUANTILE_PERCENTS:
        cutoff = fit_quantile_cutoff_on_val(pred_val, q_pct)
        val_res = _eval_threshold_mask(pnl_val_per_row, pred_val, cutoff, span_years_val)
        test_res = _eval_threshold_mask(pnl_test_per_row, pred_test, cutoff, span_years_test)
        results.append(
            {
                "q_percent": int(q_pct),
                "cutoff": float(cutoff),
                "val": val_res,
                "test": test_res,
            }
        )
    return results


def _candidates_absolute_for_scale(scale: str) -> tuple[float, ...]:
    return NEG_THRESHOLDS_ATR if scale == "atr_normalised" else NEG_THRESHOLDS_RAW_PIP


def evaluate_absolute_family(
    pred_val: np.ndarray,
    pnl_val_per_row: np.ndarray,
    pred_test: np.ndarray,
    pnl_test_per_row: np.ndarray,
    scale: str,
    span_years_val: float,
    span_years_test: float,
) -> list[dict]:
    """SECONDARY DIAGNOSTIC family — per rev1 §5.

    Negative absolute thresholds per target scale. NOT used for verdict.
    """
    candidates = _candidates_absolute_for_scale(scale)
    results: list[dict] = []
    for thr in candidates:
        val_res = _eval_threshold_mask(pnl_val_per_row, pred_val, thr, span_years_val)
        test_res = _eval_threshold_mask(pnl_test_per_row, pred_test, thr, span_years_test)
        results.append(
            {
                "threshold": float(thr),
                "val": val_res,
                "test": test_res,
            }
        )
    return results


# ---------------------------------------------------------------------------
# Pair concentration (per 26.0b-α §4.1; diagnostic-only)
# ---------------------------------------------------------------------------


def compute_pair_concentration(
    df_clean: pd.DataFrame,
    traded_mask: np.ndarray,
    valid_pnl_mask: np.ndarray | None = None,
) -> dict:
    """Per-pair share of selected trades on a split.

    Per 26.0b-α §4.1 binding: this is DIAGNOSTIC-ONLY. The returned
    `concentration_high` flag MUST NOT be consulted by
    `select_cell_validation_only` or `assign_verdict` (test #26 enforces).

    Args:
        df_clean: label-NaN-dropped DataFrame aligned to traded_mask.
        traded_mask: boolean mask of length len(df_clean) — rows where
                     pred >= cutoff_q.
        valid_pnl_mask: optional boolean mask — rows where realised PnL
                        was computable (e.g., M1 path window valid). If
                        None, all traded rows count.

    Returns:
        dict with:
            by_pair: {pair: count} for traded rows
            by_pair_share: {pair: share in (0, 1]} for traded rows
            top_pair: pair with the highest count (or None)
            top_pair_share: top_pair's share (or NaN)
            concentration_high: True iff top_pair_share >= 0.80
            n_traded_used: total traded count used in shares
    """
    eff_mask = traded_mask & valid_pnl_mask if valid_pnl_mask is not None else traded_mask
    n_used = int(eff_mask.sum())
    if n_used == 0:
        return {
            "by_pair": {},
            "by_pair_share": {},
            "top_pair": None,
            "top_pair_share": float("nan"),
            "concentration_high": False,
            "n_traded_used": 0,
        }
    pairs = df_clean["pair"].to_numpy()
    by_pair: dict[str, int] = {}
    for i in np.flatnonzero(eff_mask):
        p = str(pairs[i])
        by_pair[p] = by_pair.get(p, 0) + 1
    by_pair_share = {p: c / n_used for p, c in by_pair.items()}
    top_pair = max(by_pair, key=by_pair.get)
    top_pair_share = by_pair_share[top_pair]
    return {
        "by_pair": by_pair,
        "by_pair_share": by_pair_share,
        "top_pair": top_pair,
        "top_pair_share": float(top_pair_share),
        "concentration_high": bool(top_pair_share >= CONCENTRATION_HIGH_THRESHOLD),
        "n_traded_used": n_used,
    }


# ---------------------------------------------------------------------------
# 8-gate metrics on a realised-PnL array
# ---------------------------------------------------------------------------


def compute_8_gate_from_pnls(pnls: np.ndarray) -> dict:
    """Wraps stage25_0b.compute_8_gate_metrics + gate_matrix."""
    n_trades = len(pnls)
    metrics = compute_8_gate_metrics(pnls, n_trades)
    gates = gate_matrix(metrics)
    return {"metrics": metrics, "gates": gates}


# ---------------------------------------------------------------------------
# Regression diagnostics (diagnostic-only)
# ---------------------------------------------------------------------------


def regression_diagnostics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    finite = np.isfinite(y_true) & np.isfinite(y_pred)
    yt = y_true[finite]
    yp = y_pred[finite]
    if len(yt) < 10:
        return {
            "n": int(len(yt)),
            "r2": float("nan"),
            "pearson": float("nan"),
            "spearman": float("nan"),
            "mae": float("nan"),
            "rmse": float("nan"),
            "low_n_flag": True,
        }
    r2 = float(r2_score(yt, yp))
    p_corr = float(pearsonr(yt, yp).statistic) if np.std(yp) > 0 else float("nan")
    sp_corr = float(spearmanr(yt, yp).statistic) if np.std(yp) > 0 else float("nan")
    mae = float(mean_absolute_error(yt, yp))
    rmse = float(np.sqrt(mean_squared_error(yt, yp)))
    return {
        "n": int(len(yt)),
        "r2": r2,
        "pearson": p_corr,
        "spearman": sp_corr,
        "mae": mae,
        "rmse": rmse,
        "low_n_flag": bool(len(yt) < 100),
    }


def decile_reliability(y_pred: np.ndarray, y_realised_pnl: np.ndarray) -> dict:
    finite = np.isfinite(y_pred) & np.isfinite(y_realised_pnl)
    if finite.sum() < 30:
        return {"buckets": [], "low_n_flag": True}
    df = pd.DataFrame({"pred": y_pred[finite], "realised": y_realised_pnl[finite]})
    try:
        df["bucket"] = pd.qcut(df["pred"], 10, labels=False, duplicates="drop")
    except ValueError:
        return {"buckets": [], "low_n_flag": True}
    rows: list[dict] = []
    for bucket_id, sub in df.groupby("bucket"):
        rows.append(
            {
                "bucket": int(bucket_id),
                "pred_mean": float(sub["pred"].mean()),
                "realised_mean": float(sub["realised"].mean()),
                "n": int(len(sub)),
            }
        )
    return {"buckets": rows, "low_n_flag": False}


# ---------------------------------------------------------------------------
# Per-cell evaluation (rev1; quantile primary + absolute diagnostic)
# ---------------------------------------------------------------------------


def evaluate_cell(
    cell: dict,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    pair_runtime_map: dict,
    pnl_val_full: np.ndarray,
    pnl_test_full: np.ndarray,
) -> dict:
    """Evaluate one cell across the quantile (primary) + absolute (diagnostic) families.

    pnl_val_full and pnl_test_full are precomputed per-row realised PnL arrays
    aligned with val_df / test_df positionally (NOT label-NaN-dropped).
    """
    scale = cell["scale"]
    clip_mode = cell["clip"]
    model_name = cell["model"]

    # Label construction (L-2: no spread_factor)
    train_y = build_l2_labels_for_dataframe(train_df, pair_runtime_map, scale)
    val_y = build_l2_labels_for_dataframe(val_df, pair_runtime_map, scale)
    test_y = build_l2_labels_for_dataframe(test_df, pair_runtime_map, scale)

    train_mask = train_y.notna()
    val_mask = val_y.notna()
    test_mask = test_y.notna()

    n_train, n_val, n_test = int(train_mask.sum()), int(val_mask.sum()), int(test_mask.sum())
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

    x_train = train_df.loc[train_mask, CATEGORICAL_COLS]
    x_val = val_df.loc[val_mask, CATEGORICAL_COLS]
    x_test = test_df.loc[test_mask, CATEGORICAL_COLS]
    train_y_clean = train_y[train_mask]

    # D-6 winsorisation: training-y only (harness PnL never touched)
    if clip_mode == "q01_q99":
        clip_lo, clip_hi = fit_winsorise_train(train_y_clean)
        train_y_for_fit = apply_winsorise(train_y_clean, clip_lo, clip_hi)
    else:
        clip_lo, clip_hi = float("-inf"), float("inf")
        train_y_for_fit = train_y_clean

    # Fit
    pipeline = build_pipeline(model_name)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipeline.fit(x_train, train_y_for_fit.to_numpy())

    # Predict (aligned to label-NaN-dropped views)
    pred_val = pipeline.predict(x_val)
    pred_test = pipeline.predict(x_test)

    # Align precomputed PnL arrays to label-NaN-dropped masks
    val_mask_np = val_mask.to_numpy()
    test_mask_np = test_mask.to_numpy()
    pnl_val_clean = pnl_val_full[val_mask_np]
    pnl_test_clean = pnl_test_full[test_mask_np]

    # Sanity: must align positionally
    if len(pnl_val_clean) != len(pred_val):
        raise RuntimeError(f"val PnL/pred length mismatch: {len(pnl_val_clean)} vs {len(pred_val)}")
    if len(pnl_test_clean) != len(pred_test):
        raise RuntimeError(
            f"test PnL/pred length mismatch: {len(pnl_test_clean)} vs {len(pred_test)}"
        )

    # PRIMARY family: quantile-of-val
    quantile_results = evaluate_quantile_family(
        pred_val,
        pnl_val_clean,
        pred_test,
        pnl_test_clean,
        VAL_SPAN_YEARS,
        TEST_SPAN_YEARS,
    )

    # SECONDARY DIAGNOSTIC family: absolute (negative-spanning) candidates
    absolute_results = evaluate_absolute_family(
        pred_val,
        pnl_val_clean,
        pred_test,
        pnl_test_clean,
        scale,
        VAL_SPAN_YEARS,
        TEST_SPAN_YEARS,
    )

    # Pick best q on val by realised Sharpe; tie-break by val annual_pnl
    def _q_sort_key(r: dict) -> tuple:
        v = r["val"]
        s = v["sharpe"] if np.isfinite(v["sharpe"]) else -np.inf
        return (s, v["annual_pnl"], v["n_trades"], r["q_percent"])

    best_q_record = max(quantile_results, key=_q_sort_key)

    # Test 8-gate metrics for the best quantile (formal verdict source)
    test_realised = best_q_record["test"]["realised_pnls"]
    gate_block = compute_8_gate_from_pnls(test_realised)

    # Regression diagnostics on test (predicted vs realised) — diagnostic-only
    diag = regression_diagnostics(pnl_test_clean, pred_test)
    decile = decile_reliability(pred_test, pnl_test_clean)

    # Per-pair / per-direction trade count for the val-selected (cell, q) on test
    test_df_clean = test_df.loc[test_mask].reset_index(drop=True)
    val_df_clean = val_df.loc[val_mask].reset_index(drop=True)
    traded_mask_test = pred_test >= best_q_record["cutoff"]
    valid_pnl_mask_test = np.isfinite(pnl_test_clean)
    in_trade = traded_mask_test & valid_pnl_mask_test
    by_pair: dict[str, int] = {}
    by_direction: dict[str, int] = {"long": 0, "short": 0}
    for i in np.flatnonzero(in_trade):
        p = str(test_df_clean["pair"].iloc[i])
        d = str(test_df_clean["direction"].iloc[i])
        by_pair[p] = by_pair.get(p, 0) + 1
        by_direction[d] = by_direction.get(d, 0) + 1

    # Pair concentration (per 26.0b-α §4.1; DIAGNOSTIC-ONLY).
    # Computed on val_selected (cell, q) on VAL (the same cutoff used to fit).
    # NOT consulted by select_cell_validation_only or assign_verdict.
    valid_pnl_mask_val = np.isfinite(pnl_val_clean)
    traded_mask_val = pred_val >= best_q_record["cutoff"]
    val_concentration = compute_pair_concentration(
        val_df_clean, traded_mask_val, valid_pnl_mask_val
    )
    test_concentration = compute_pair_concentration(
        test_df_clean, traded_mask_test, valid_pnl_mask_test
    )

    # Best absolute (for cell-level diagnostic only)
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
        # PRIMARY (quantile family) — used for verdict
        "quantile_all": [
            {
                k: (v if k != "val" and k != "test" else {**v, "realised_pnls": None})
                for k, v in r.items()
            }
            for r in quantile_results
        ],  # serialisable view (drop arrays)
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
        # Pair concentration (per 26.0b-α §4.1; DIAGNOSTIC-ONLY).
        # MUST NOT be consulted by select_cell_validation_only or assign_verdict.
        "val_concentration": val_concentration,
        "test_concentration": test_concentration,
        # SECONDARY DIAGNOSTIC (absolute family) — informational only
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
        # Regression diagnostics (independent of threshold)
        "test_regression_diag": diag,
        "test_decile_reliability": decile,
        "by_pair_trade_count": by_pair,
        "by_direction_trade_count": by_direction,
        "winsorise_lo": clip_lo,
        "winsorise_hi": clip_hi,
        "low_power": low_power,
        "h_state": "OK",
    }


# ---------------------------------------------------------------------------
# Cell selection (validation-only; per 26.0a-α §5.3 — applies to (cell, q) pairs)
# ---------------------------------------------------------------------------


_MODEL_SIMPLICITY_RANK = {"LinearRegression": 0, "Ridge": 1, "LightGBM": 2}


def select_cell_validation_only(cell_results: list[dict]) -> dict:
    """Pick the val-selected cell per original 26.0a-α §5.3, applied to
    (cell, q) primary-quantile pairs.

    Priority order:
      Pre-filter: val_n_trades >= A0-equivalent
      Tie-breakers (deterministic):
        1. max val realised Sharpe
        2. max val annual_pnl
        3. lower val MaxDD
        4. simpler model class (LinearRegression > Ridge > LightGBM;
           deterministic final tie-breaker only, NOT a model preference)
    """
    a0_min_val_trades = A0_MIN_ANNUAL_TRADES * VAL_SPAN_YEARS

    valid = [
        c
        for c in cell_results
        if c.get("h_state") == "OK"
        and "val_realised_sharpe" in c
        and np.isfinite(c.get("val_realised_sharpe", float("nan")))
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
        model = c["cell"]["model"]
        model_rank = _MODEL_SIMPLICITY_RANK.get(model, 99)
        return (sharpe, annual_pnl, -max_dd, -model_rank)

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
# Verdict tree (per 26.0a-α §7, inherited unchanged)
# ---------------------------------------------------------------------------


def assign_verdict(val_selected: dict | None) -> dict:
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
    diag = val_selected.get("test_regression_diag", {})
    spearman = diag.get("spearman", float("nan"))
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
        all_keys = ("A0", "A1", "A2", "A3", "A4", "A5")
        if all(gates.get(k, False) for k in all_keys):
            verdict, h_state = "ADOPT_CANDIDATE", "ALL_GATES_PASS"
        elif any(gates.get(k, False) for k in ("A3", "A4", "A5")):
            verdict, h_state = "PROMISING_BUT_NEEDS_OOS", "A3_A5_PARTIAL"
        else:
            verdict, h_state = "REJECT", "A3_A5_FAIL"
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
# Diagnostic-only selectors (NOT used for verdict)
# ---------------------------------------------------------------------------


def select_best_by_test_spearman(cell_results: list[dict]) -> dict | None:
    valid = [
        c
        for c in cell_results
        if c.get("h_state") == "OK"
        and np.isfinite(c.get("test_regression_diag", {}).get("spearman", float("nan")))
    ]
    if not valid:
        return None
    return max(valid, key=lambda c: c["test_regression_diag"]["spearman"])


def select_best_by_test_sharpe(cell_results: list[dict]) -> dict | None:
    valid = [
        c
        for c in cell_results
        if c.get("h_state") == "OK"
        and np.isfinite(c.get("test_realised_metrics", {}).get("sharpe", float("nan")))
    ]
    if not valid:
        return None
    return max(valid, key=lambda c: c["test_realised_metrics"]["sharpe"])


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def _cell_signature(cell: dict) -> str:
    return f"scale={cell['scale']:14} clip={cell['clip']:7} model={cell['model']:16}"


def write_eval_report(
    out_path: Path,
    cell_results: list[dict],
    val_select: dict,
    verdict_info: dict,
    diag_best_spearman: dict | None,
    diag_best_sharpe: dict | None,
    split_dates: tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp],
    preflight_diag: dict,
    n_cells_run: int,
    lightgbm_deferred: bool,
) -> None:
    t_min, t70, t85, t_max = split_dates
    lines: list[str] = []
    lines.append("# Stage 26.0a-β — L-3 EV Regression Eval (rev1)")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append(
        "Design contract: `docs/design/phase26_0a_alpha_l3_design.md` (PR #301) + "
        "`docs/design/phase26_0a_alpha_rev1.md` (PR #302)."
    )
    lines.append("")
    lines.append(
        "L-2 = generic continuous path-quality regression (parent family of L-3). "
        "**L-2 target excludes spread at label construction.** The 8-gate realised "
        "PnL still includes executable bid/ask spread/cost via inherited M1 path "
        "re-traverse. L-2 tests whether a generic continuous path-quality target "
        "ranks opportunities better without embedding spread into the training "
        "target. Quantile-of-val threshold family is the PRIMARY verdict basis; "
        "negative absolute thresholds are SECONDARY DIAGNOSTIC."
    )
    lines.append("")
    lines.append("## Mandatory clauses (verbatim per 26.0a-α §9 + rev1 §11)")
    lines.append("")
    lines.append(
        "**1. Phase 26 framing.** Phase 26 is the entry-side return on alternative "
        "label / target designs on the 20-pair canonical universe. ADOPT requires "
        "both H2 PASS and the full 8-gate A0-A5 harness."
    )
    lines.append("")
    lines.append(
        "**2. Diagnostic columns prohibition.** Calibration / threshold-sweep / "
        "directional-comparison columns are diagnostic-only. ADOPT_CANDIDATE "
        "routing must not depend on any single one of them."
    )
    lines.append("")
    lines.append("**3. γ closure preservation.** PR #279 is unmodified.")
    lines.append("")
    lines.append(
        "**4. Production-readiness preservation.** X-v2 OOS gating remains "
        "required before any production deployment. v9 20-pair (Phase 9.12) "
        "remains untouched."
    )
    lines.append("")
    lines.append("**5. NG#10 / NG#11 not relaxed.**")
    lines.append("")
    lines.append(
        "**6. Phase 26 scope.** Phase 26 is NOT a continuation of Phase 25's "
        "feature-axis sweep. F4 / F6 / F5-d / F5-e remain deferred-not-foreclosed."
    )
    lines.append("")
    lines.append("## Production-misuse guards (verbatim per 26.0a-α §5.1)")
    lines.append("")
    lines.append("**GUARD 1**: research-not-production.")
    lines.append("")
    lines.append("**GUARD 2**: threshold-sweep-diagnostic.")
    lines.append("")
    lines.append("**GUARD 3**: directional-comparison-diagnostic.")
    lines.append("")
    lines.append("## L-2 vs L-3 boundary (per 26.0b-α §1.1 / §3.1)")
    lines.append("")
    lines.append(
        "**L-2 vs L-3 single-axis change**: L-3 (PR #301) embedded spread cost "
        "in the target at construction time (D-4: `label_pre = base_mid_pnl − "
        "spread_at_signal_pip × spread_factor`). L-2 OMITS D-4 entirely "
        "(`label_pre = base_mid_pnl`). Spread cost surfaces ONLY at 8-gate "
        "realised-PnL scoring stage via inherited `_compute_realised_barrier_pnl` "
        "(ask/bid path with original cost model — UNCHANGED from L-3). The L-2 "
        "no-double-counting clause is held VACUOUSLY because the L-2 target "
        "subtracts spread zero times (instead of one)."
    )
    lines.append("")
    lines.append("## Causality + no-double-counting notes (per 26.0a-α §3.1)")
    lines.append("")
    lines.append(
        "Spread cost is subtracted EXACTLY ONCE during label construction (D-4). "
        "Base PnL is mid-to-mid. Realised PnL fed to the 8-gate harness uses "
        "25.0a-β `_compute_realised_barrier_pnl` (ask/bid path with original cost "
        "model) unchanged. Winsorisation (D-6) applies only to the training "
        "target y; harness realised PnL is NEVER winsorised."
    )
    lines.append("")
    lines.append("## Threshold-selection design (per rev1 §3 / §4)")
    lines.append("")
    lines.append(
        "**PRIMARY family (formal verdict basis)**: quantile-of-val, top q% per "
        "candidate `{5, 10, 20, 30, 40}`. Cutoff is fit on val predictions ONLY "
        "(scalar value), then applied to test predictions as the same scalar. "
        "NO full-sample qcut; NO peeking at test predictions."
    )
    lines.append("")
    lines.append(
        "**SECONDARY DIAGNOSTIC family**: negative-spanning absolute candidates "
        f"raw_pip {list(NEG_THRESHOLDS_RAW_PIP)} / ATR-normalised "
        f"{list(NEG_THRESHOLDS_ATR)}. Reported per cell but NOT used for verdict."
    )
    lines.append("")
    lines.append("## Pre-flight diagnostics")
    lines.append("")
    lines.append(f"- label rows: {preflight_diag['label_rows']}")
    lines.append(f"- horizon_bars (M1): {preflight_diag['horizon_bars']}")
    lines.append(f"- pairs: {preflight_diag['pairs']}")
    lines.append(f"- LightGBM available: {preflight_diag['lightgbm_available']}")
    if preflight_diag.get("lightgbm_version"):
        lines.append(f"- LightGBM version: {preflight_diag['lightgbm_version']}")
    lines.append(f"- cells run in this sweep: {n_cells_run}")
    if lightgbm_deferred:
        lines.append("- **LightGBM cells deferred** (16 cells, Ridge + LinearRegression only)")
    lines.append("")
    lines.append("## Validation-only cell + quantile selection (per 26.0a-α §5.3)")
    lines.append("")
    lines.append(
        "Pre-filter: candidates with `val_n_trades >= A0-equivalent` are "
        "eligible. If none, LOW_VAL_TRADES flag is set and fallback to all valid "
        "candidates."
    )
    lines.append("")
    lines.append("Tie-breaker order (deterministic):")
    lines.append("1. max val realised Sharpe (primary)")
    lines.append("2. max val annual_pnl")
    lines.append("3. lower val MaxDD")
    lines.append(
        "4. simpler model class (LinearRegression > Ridge > LightGBM) — final "
        "deterministic tie-breaker only, NOT a model preference"
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

    # Sort cells by val Sharpe (primary family)
    def _val_sharpe(c: dict) -> float:
        v = c.get("val_realised_sharpe", float("-inf"))
        return v if np.isfinite(v) else -1e18

    sorted_cells = sorted(cell_results, key=_val_sharpe, reverse=True)

    # Section 1: all 24 cells primary-quantile summary
    lines.append(
        "## All cells — primary quantile-family summary (sorted by VAL realised Sharpe desc)"
    )
    lines.append("")
    lines.append(
        "| scale | clip | model | q% | cutoff | val_sharpe | val_ann_pnl | "
        "val_n | test_sharpe | test_ann_pnl | test_n | test_spearman | A4 | A5_ann | h_state |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c in sorted_cells:
        cell = c["cell"]
        rm = c.get("test_realised_metrics", {})
        diag = c.get("test_regression_diag", {})
        lines.append(
            f"| {cell['scale']} | {cell['clip']} | "
            f"{cell['model']} | {c.get('selected_q_percent', '-')} | "
            f"{c.get('selected_cutoff', float('nan')):+.4f} | "
            f"{c.get('val_realised_sharpe', float('nan')):.4f} | "
            f"{c.get('val_realised_annual_pnl', 0.0):+.1f} | "
            f"{c.get('val_n_trades', 0)} | "
            f"{rm.get('sharpe', float('nan')):.4f} | "
            f"{rm.get('annual_pnl', 0.0):+.1f} | "
            f"{rm.get('n_trades', 0)} | "
            f"{diag.get('spearman', float('nan')):.4f} | "
            f"{rm.get('a4_n_positive', 0)} | "
            f"{rm.get('a5_stressed_annual_pnl', float('nan')):+.1f} | "
            f"{c.get('h_state', '-')} |"
        )
    lines.append("")

    # Section 2: val-selected cell (formal verdict source)
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
        diag = sel.get("test_regression_diag", {})
        lines.append(
            f"- regression diagnostics on test (diagnostic-only): "
            f"R²={diag.get('r2', float('nan')):.4f}, "
            f"Pearson={diag.get('pearson', float('nan')):.4f}, "
            f"Spearman={diag.get('spearman', float('nan')):.4f}, "
            f"MAE={diag.get('mae', float('nan')):.4f}, "
            f"RMSE={diag.get('rmse', float('nan')):.4f}, "
            f"n={diag.get('n', 0)}"
        )
        lines.append(f"- by-pair trade count: {sel.get('by_pair_trade_count', {})}")
        lines.append(f"- by-direction trade count: {sel.get('by_direction_trade_count', {})}")
    lines.append("")

    # Section 3: best by test Spearman (diagnostic-only)
    lines.append("## Best cell by TEST Spearman (diagnostic-only; NOT used for verdict)")
    lines.append("")
    if diag_best_spearman is None:
        lines.append("- no valid cell")
    else:
        cell = diag_best_spearman["cell"]
        diag = diag_best_spearman.get("test_regression_diag", {})
        rm = diag_best_spearman.get("test_realised_metrics", {})
        lines.append(f"- cell: {_cell_signature(cell)}")
        lines.append(
            f"- test Spearman: {diag.get('spearman', float('nan')):.4f} "
            f"(R²={diag.get('r2', float('nan')):.4f}, "
            f"Pearson={diag.get('pearson', float('nan')):.4f})"
        )
        lines.append(
            f"- test realised at primary q*: "
            f"Sharpe={rm.get('sharpe', float('nan')):.4f}, "
            f"ann_pnl={rm.get('annual_pnl', 0.0):+.1f}, "
            f"n_trades={rm.get('n_trades', 0)}"
        )
        lines.append("- **Diagnostic only; not used for verdict.**")
    lines.append("")

    # Section 4: best by test realised Sharpe (diagnostic-only)
    lines.append("## Best cell by TEST realised Sharpe (diagnostic-only; NOT used for verdict)")
    lines.append("")
    if diag_best_sharpe is None:
        lines.append("- no valid cell")
    else:
        cell = diag_best_sharpe["cell"]
        rm = diag_best_sharpe.get("test_realised_metrics", {})
        diag = diag_best_sharpe.get("test_regression_diag", {})
        lines.append(f"- cell: {_cell_signature(cell)}")
        lines.append(
            f"- test realised Sharpe: {rm.get('sharpe', float('nan')):.4f} "
            f"(ann_pnl={rm.get('annual_pnl', 0.0):+.1f}, "
            f"n_trades={rm.get('n_trades', 0)})"
        )
        lines.append(f"- test Spearman: {diag.get('spearman', float('nan')):.4f}")
        lines.append("- **Diagnostic only; not used for verdict.**")
    lines.append("")

    # Section 5: secondary diagnostic absolute-family per cell
    lines.append(
        "## Secondary DIAGNOSTIC absolute-threshold family (per cell; NOT used for verdict)"
    )
    lines.append("")
    lines.append(
        "Per-cell best absolute-threshold result. Reported for reference only; "
        "the formal verdict basis is the primary quantile family above."
    )
    lines.append("")
    lines.append("| scale | clip | model | abs_thr | val_sharpe | val_n | test_sharpe | test_n |")
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for c in sorted_cells:
        cell = c["cell"]
        ab = c.get("absolute_best", {})
        if not ab:
            continue
        lines.append(
            f"| {cell['scale']} | {cell['clip']} | "
            f"{cell['model']} | {ab.get('threshold', float('nan')):+.4f} | "
            f"{ab.get('val', {}).get('sharpe', float('nan')):.4f} | "
            f"{ab.get('val', {}).get('n_trades', 0)} | "
            f"{ab.get('test', {}).get('sharpe', float('nan')):.4f} | "
            f"{ab.get('test', {}).get('n_trades', 0)} |"
        )
    lines.append("")
    lines.append(
        "**Selected threshold family declaration**: the formal verdict basis is the "
        "quantile-family val-selected (cell*, q*) pair."
    )
    lines.append("")

    # Section 6: ranking-monetisation narrative
    lines.append("## Whether ranking signal monetises in top predicted-EV buckets (narrative)")
    lines.append("")
    if sel is None:
        lines.append("- val-selected cell unavailable; ranking-monetisation narrative skipped")
    else:
        diag = sel.get("test_regression_diag", {})
        sp = diag.get("spearman", float("nan"))
        rm = sel.get("test_realised_metrics", {})
        sharpe = rm.get("sharpe", float("nan"))
        ann = rm.get("annual_pnl", float("nan"))
        lines.append(
            f"- val-selected cell has test Spearman = {sp:.4f} (ranking-quality "
            f"signal between predicted EV and realised pip PnL on test)."
        )
        lines.append(
            f"- At the val-selected q* = {sel.get('selected_q_percent')}% cutoff, test "
            f"realised Sharpe = {sharpe:.4f} and annual pip PnL = {ann:+.1f}."
        )
        if np.isfinite(sharpe) and sharpe >= 0:
            lines.append(
                "- The ranking signal monetises positively at the selected quantile "
                "cutoff. H4 (structural-gap escape) PASS."
            )
        else:
            lines.append(
                "- The ranking signal does NOT monetise at the selected quantile "
                "cutoff (realised Sharpe < 0). H4 FAIL: structural-gap signature "
                "persists at this label / barrier / spread-cost combination."
            )
    lines.append("")

    # Section 7: aggregate H1 / H2 / H3 / H4 + verdict
    # ---- L-2 vs L-3 comparison (mandatory per 26.0b-α §3 user directive #2) ----
    lines.append("## L-2 vs L-3 comparison (mandatory section)")
    lines.append("")
    lines.append(
        "L-3 reference values are from PR #303 26.0a-β rev1 eval (fixed, do NOT recompute):"
    )
    lines.append("")
    lines.append("| Aspect | L-3 (PR #303) | L-2 (this PR) |")
    lines.append("|---|---|---|")
    # L-3 baseline (hardcoded from PR #303 eval_report)
    l3_val_sharpe = -0.2232
    l3_formal_spearman = -0.1419
    l3_best_raw_pip_spearman = 0.3836  # from PR #303 §"Best cell by TEST Spearman"
    l3_best_test_sharpe = -0.2232  # PR #303 same val-selected cell happens to be best-by-Sharpe too

    sel = val_select.get("selected")
    if sel is None:
        l2_val_sharpe = float("nan")
        l2_formal_spearman = float("nan")
    else:
        l2_val_sharpe = sel.get("test_realised_metrics", {}).get("sharpe", float("nan"))
        l2_formal_spearman = sel.get("test_regression_diag", {}).get("spearman", float("nan"))
    l2_best_spearman_record = diag_best_spearman
    l2_best_sharpe_record = diag_best_sharpe
    l2_best_test_spearman = (
        l2_best_spearman_record["test_regression_diag"]["spearman"]
        if l2_best_spearman_record
        else float("nan")
    )
    l2_best_test_sharpe = (
        l2_best_sharpe_record["test_realised_metrics"]["sharpe"]
        if l2_best_sharpe_record
        else float("nan")
    )

    lines.append(
        f"| Val-selected test realised Sharpe | {l3_val_sharpe:.4f} | {l2_val_sharpe:.4f} |"
    )
    lines.append(
        f"| Val-selected test Spearman (formal) | {l3_formal_spearman:.4f} | "
        f"{l2_formal_spearman:.4f} |"
    )
    lines.append(
        f"| Best-by-test-Spearman diagnostic | +{l3_best_raw_pip_spearman:.4f} "
        f"(raw_pip / LightGBM cell) | {l2_best_test_spearman:+.4f} |"
    )
    lines.append(
        f"| Best-by-test-Sharpe diagnostic | {l3_best_test_sharpe:.4f} | "
        f"{l2_best_test_sharpe:.4f} |"
    )
    lines.append("")
    lines.append("**Interpretation guide**:")
    lines.append(
        "- If L-2 val-selected Sharpe > L-3 val-selected Sharpe → L-3 spread-"
        "embedding step harmed realised PnL conversion."
    )
    lines.append(
        "- If L-2 val-selected Sharpe ≈ L-3 val-selected Sharpe → continuous-"
        "target labelling at minimum feature set is the binding issue regardless "
        "of spread embedding."
    )
    lines.append(
        "- If L-2 best-by-Spearman > L-3's +0.3836 → L-2 ranking signal is "
        "stronger; if ≈ similar → L-3's ranking signal was not spread-driven."
    )
    lines.append("")
    # ---- Pair concentration table (per 26.0b-α §4.1; diagnostic-only) ----
    lines.append(
        "## Pair concentration per cell (per 26.0b-α §4.1; diagnostic-only; NOT used for verdict)"
    )
    lines.append("")
    lines.append(
        "Val concentration = top-pair share among traded rows at the val-fit "
        "cutoff. CONCENTRATION_HIGH flag fires when val top-pair share >= "
        f"{CONCENTRATION_HIGH_THRESHOLD}."
    )
    lines.append("")
    lines.append(
        "| scale | clip | model | q% | val_top_pair | val_top_share | "
        "val_concentration_high | test_top_pair | test_top_share |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for c in sorted_cells:
        cell = c["cell"]
        val_con = c.get("val_concentration", {})
        test_con = c.get("test_concentration", {})
        lines.append(
            f"| {cell['scale']} | {cell['clip']} | {cell['model']} | "
            f"{c.get('selected_q_percent', '-')} | "
            f"{val_con.get('top_pair', '-')} | "
            f"{val_con.get('top_pair_share', float('nan')):.4f} | "
            f"{val_con.get('concentration_high', False)} | "
            f"{test_con.get('top_pair', '-')} | "
            f"{test_con.get('top_pair_share', float('nan')):.4f} |"
        )
    lines.append("")
    lines.append(
        "**Diagnostic only; not used for verdict.** The CONCENTRATION_HIGH flag "
        "is NOT consulted by `select_cell_validation_only` or `assign_verdict`."
    )
    lines.append("")
    lines.append("## Aggregate H1 / H2 / H3 / H4 outcome (val-selected (cell*, q*) on test)")
    lines.append("")
    lines.append(
        f"- H1-weak (Spearman > {H1_WEAK_THRESHOLD}): **{verdict_info.get('h1_weak_pass')}**"
    )
    lines.append(
        f"- H1-meaningful (Spearman >= {H1_MEANINGFUL_THRESHOLD}; formal H1 PASS): "
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

    lines.append("## Multiple-testing caveat")
    lines.append("")
    lines.append(
        f"{n_cells_run} cells × 5 quantile candidates = {n_cells_run * 5} primary "
        "(cell, q) pairs evaluated. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE "
        "verdicts are hypothesis-generating ONLY; production-readiness requires an "
        "X-v2-equivalent frozen-OOS PR per Phase 22 contract."
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
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(
        f"=== Stage 26.0b-beta L-2 generic path-quality regression eval "
        f"({len(args.pairs)} pairs) ==="
    )
    print(
        f"K_FAV={K_FAV} K_ADV={K_ADV} H_M1={H_M1_BARS} | "
        f"H1-weak>{H1_WEAK_THRESHOLD} H1-meaningful>={H1_MEANINGFUL_THRESHOLD} | "
        f"H3 ref={H3_REFERENCE_SHARPE} | quantile candidates={THRESHOLDS_QUANTILE_PERCENTS}"
    )

    # 1. Load 25.0a-beta labels
    print("Loading 25.0a-beta path-quality labels (full + raw — keep diagnostic cols)...")
    raw_label_path = REPO_ROOT / "artifacts" / "stage25_0a" / "path_quality_dataset.parquet"
    raw_labels = pd.read_parquet(raw_label_path)
    if args.pairs != PAIRS_20:
        raw_labels = raw_labels[raw_labels["pair"].isin(args.pairs)]
    print(f"  labels rows: {len(raw_labels)}")

    # 2. Pre-flight
    print("Running L-3 pre-flight...")
    t0 = time.time()
    try:
        preflight_diag = verify_l3_preflight(raw_labels, args.pairs)
    except L3PreflightError as exc:
        print(f"L-3 PRE-FLIGHT FAILED: {exc}")
        return 2
    print(
        f"  Pre-flight passed: {preflight_diag['label_rows']} rows; "
        f"LightGBM={preflight_diag['lightgbm_available']} "
        f"({preflight_diag.get('lightgbm_version')}) "
        f"({time.time() - t0:.1f}s)"
    )

    lightgbm_available = preflight_diag["lightgbm_available"]
    cells = build_cells(include_lightgbm=lightgbm_available)
    n_cells_run = len(cells)
    print(
        f"  cell grid: {n_cells_run} cells "
        f"({'LightGBM included' if lightgbm_available else 'LightGBM DEFERRED'})"
    )

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

    # 5. PRECOMPUTE realised PnL per row for val + test (cell-independent)
    print("Precomputing realised PnL per row (val + test; cell-independent cache)...")
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

    # 6. Per-cell sweep
    cell_results: list[dict] = []
    for i, cell in enumerate(cells):
        t_cell = time.time()
        try:
            result = evaluate_cell(
                cell, train_df, val_df, test_df, pair_runtime_map, pnl_val_full, pnl_test_full
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
        diag = result.get("test_regression_diag", {})
        print(
            f"  cell {i + 1}/{n_cells_run} "
            f"sc={cell['scale']:14} cl={cell['clip']:7} m={cell['model']:16} | "
            f"q={result.get('selected_q_percent', '-')} "
            f"val_sharpe={result.get('val_realised_sharpe', float('nan')):+.3f} "
            f"val_n={result.get('val_n_trades', 0):>6} | "
            f"test_sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"test_n={rm.get('n_trades', 0):>6} "
            f"test_sp={diag.get('spearman', float('nan')):+.4f} | "
            f"({time.time() - t_cell:5.1f}s)"
        )

    # 7. Validation-only cell selection
    val_select = select_cell_validation_only(cell_results)
    verdict_info = assign_verdict(val_select.get("selected"))
    diag_best_spearman = select_best_by_test_spearman(cell_results)
    diag_best_sharpe = select_best_by_test_sharpe(cell_results)

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
        diag = sel.get("test_regression_diag", {})
        print(
            f"  test Sharpe = {rm.get('sharpe', float('nan')):.4f}; "
            f"test ann_pnl = {rm.get('annual_pnl', 0.0):+.1f}; "
            f"test n_trades = {rm.get('n_trades', 0)}; "
            f"test Spearman = {diag.get('spearman', float('nan')):.4f}"
        )
    print("")
    print(f"=== Verdict: {verdict_info['verdict']} ({verdict_info['h_state']}) ===")

    # 8. Write report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report(
        report_path,
        cell_results,
        val_select,
        verdict_info,
        diag_best_spearman,
        diag_best_sharpe,
        (t_min, t70, t85, t_max),
        preflight_diag,
        n_cells_run,
        lightgbm_deferred=not lightgbm_available,
    )
    print(f"\nReport: {report_path}")

    # 9. Persist artifacts (gitignored)
    summary_rows: list[dict] = []
    for c in cell_results:
        cell = c["cell"]
        rm = c.get("test_realised_metrics", {})
        diag = c.get("test_regression_diag", {})
        ab = c.get("absolute_best", {})
        summary_rows.append(
            {
                "scale": cell["scale"],
                "clip": cell["clip"],
                "model": cell["model"],
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
                "test_r2": diag.get("r2", float("nan")),
                "test_pearson": diag.get("pearson", float("nan")),
                "test_spearman": diag.get("spearman", float("nan")),
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
    aggregate["lightgbm_deferred"] = not lightgbm_available
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
        }
        aggregate["val_selected"] = sel_lite
    (args.out_dir / "aggregate_summary.json").write_text(
        json.dumps(aggregate, indent=2, default=str), encoding="utf-8"
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
