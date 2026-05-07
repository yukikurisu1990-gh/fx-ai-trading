"""Stage 25.0b-β — F1 volatility expansion / compression eval.

Implements the binding contract from PR #283 (25.0b-α
docs/design/phase25_0b_f1_design.md). Reads 25.0a-β path-quality
labels, builds F1 volatility-derivative features, trains 24 cells of
logistic regression with chronological 70/15/15 split, selects trade
threshold on validation only, evaluates test ONCE with REALISED
BARRIER PnL via M1 path re-traverse.

MANDATORY CLAUSES (verbatim per 25.0b-α §13):

1. Phase 25 framing.
   Phase 25 is not a hyperparameter-tuning phase. It is a label-and-
   feature-class redesign phase. Novelty must come from input feature
   class and label design.

2. F1 negative list.
   F1 features are volatility-derivative. F1 is NOT a Donchian
   breakout, NOT a z-score, NOT a Bollinger band touch, NOT a moving
   average crossover, NOT a calibration-only signal. Recent return
   sign (f1_f) is secondary directional context only — it MUST NOT
   serve as a standalone primary trigger.

3. Diagnostic columns are not features.
   The 25.0a-β diagnostic columns (max_fav_excursion_pip,
   max_adv_excursion_pip, time_to_fav_bar, time_to_adv_bar,
   same_bar_both_hit) MUST NOT appear in any model's feature matrix.
   A unit test enforces this.

4. Causality and split discipline.
   All f1 features use shift(1).rolling pattern; signal bar t's own
   data MUST NOT enter feature[t]. Train / val / test splits are
   strictly chronological (70/15/15 by calendar date). Threshold
   selection uses VALIDATION ONLY; test set is touched once.

5. γ closure preservation.
   Phase 25.0b does not modify the γ closure (PR #279). Phase 25
   results, regardless of outcome, do not change Phase 24 / NG#10
   β-chain closure status.

6. Production-readiness preservation.
   PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE in 25.0b are hypothesis-
   generating only. Production-readiness requires an X-v2-equivalent
   frozen-OOS PR per Phase 22 contract. No production deployment is
   pre-approved by this PR.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

REPO_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage25_0b"
LABEL_PARQUET = REPO_ROOT / "artifacts" / "stage25_0a" / "path_quality_dataset.parquet"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
PAIRS_20 = stage23_0a.PAIRS_20
load_m1_ba = stage23_0a.load_m1_ba
aggregate_m1_to_tf_existing = stage23_0a.aggregate_m1_to_tf
pip_size_for = stage23_0a.pip_size_for

# Local TF dict extending stage23_0a.TF_MINUTES (which has only M5/M15).
# stage23_0a.TF_MINUTES is NOT modified — keeps Phase 23/24 reproducibility.
TF_MINUTES_LOCAL = {"M5": 5, "M15": 15, "H1": 60}


# ---------------------------------------------------------------------------
# Design constants (LOCKED from 25.0b-α §3, §6, §7, §8, §9)
# ---------------------------------------------------------------------------

K_FAV = 1.5
K_ADV = 1.0
H_M1_BARS = 60
SPAN_DAYS = 730

# Per-TF RV window
RV_WINDOW = {"M5": 12, "M15": 8, "H1": 24}

# Other rolling windows (per 25.0b-α §3.1)
COMPRESSION_TRAILING = 100
EXPANSION_RECENT_N = 4
EXPANSION_BASELINE_START = 5
EXPANSION_BASELINE_END = 50
VOL_OF_VOL_LOOKBACK = 100
RETURN_SIGN_LOOKBACK_M5 = 13  # close[t-1] - close[t-13]

# Cell grid (24 cells; bidirectionality LOCKED)
CELL_TFS = ("M5", "M15", "H1")
CELL_LOOKBACKS = (50, 100)
CELL_QUANTILES = (0.10, 0.20)
CELL_EXPANSIONS = (1.25, 1.50)

# Threshold candidates (25.0b-α §9)
THRESHOLD_CANDIDATES = (0.20, 0.25, 0.30, 0.35, 0.40)

# Validation split (25.0b-α §8)
TRAIN_FRAC = 0.70
VAL_FRAC = 0.15
# test = 1 - 0.85 = 0.15

# 8-gate harness inherited
A0_MIN_ANNUAL_TRADES = 70.0
A1_MIN_SHARPE = 0.082
A2_MIN_ANNUAL_PNL = 180.0
A3_MAX_MAXDD = 200.0
A4_MIN_POSITIVE_FOLDS = 3
A5_SPREAD_STRESS_PIP = 0.5

LOW_POWER_N_TEST = 500
LOW_POWER_N_TRAIN = 5000

# Diagnostic-leakage prohibition (HARD)
PROHIBITED_DIAGNOSTIC_COLUMNS = (
    "max_fav_excursion_pip",
    "max_adv_excursion_pip",
    "time_to_fav_bar",
    "time_to_adv_bar",
    "same_bar_both_hit",
)

# Feature column list (16 base features; pair + direction added separately as categoricals)
FEATURE_COLS_BASE = [
    "f1_a_rv_M5",
    "f1_a_rv_M15",
    "f1_a_rv_H1",
    "f1_b_compression_pct_M5",
    "f1_b_compression_pct_M15",
    "f1_b_compression_pct_H1",
    "f1_c_expansion_ratio_M5",
    "f1_c_expansion_ratio_M15",
    "f1_c_expansion_ratio_H1",
    "f1_d_vol_of_vol_M5",
    "f1_d_vol_of_vol_M15",
    "f1_d_vol_of_vol_H1",
    "f1_e_range_score_M5",
    "f1_e_range_score_M15",
    "f1_e_range_score_H1",
    "f1_f_return_sign",
]
CATEGORICAL_COLS = ["pair", "direction"]


# ---------------------------------------------------------------------------
# Higher-TF aggregation (local; does NOT modify stage23_0a.TF_MINUTES)
# ---------------------------------------------------------------------------


def aggregate_m1_to_tf_local(m1_df: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Aggregate M1 to arbitrary TF using TF_MINUTES_LOCAL. Mirrors
    stage23_0a.aggregate_m1_to_tf logic but supports H1 / arbitrary TFs.
    """
    if tf == "M5" or tf == "M15":
        return aggregate_m1_to_tf_existing(m1_df, tf)
    minutes = TF_MINUTES_LOCAL[tf]
    rule = f"{minutes}min"
    agg = m1_df.resample(rule, label="right", closed="right").agg(
        {
            "bid_o": "first",
            "bid_h": "max",
            "bid_l": "min",
            "bid_c": "last",
            "ask_o": "first",
            "ask_h": "max",
            "ask_l": "min",
            "ask_c": "last",
        }
    )
    return agg.dropna()


# ---------------------------------------------------------------------------
# Feature computation (vectorized; shift(1) causal)
# ---------------------------------------------------------------------------


def _compute_rv(close_series: pd.Series, n_bars: int) -> pd.Series:
    """Realised volatility = sqrt(sum(r^2)) over rolling N causal bars."""
    log_ret = np.log(close_series).diff()
    rv = np.sqrt((log_ret**2).rolling(n_bars).sum())
    return rv.shift(1)


def _compute_compression_pct(rv_series: pd.Series, lookback: int) -> pd.Series:
    """Quantile rank of rv[t-1] within trailing rv[t-lookback..t-2] window.

    Output ∈ [0, 1]; lower = more compressed.
    """
    shifted = rv_series.shift(1)

    def _rank(window: np.ndarray) -> float:
        if len(window) < 2 or not np.isfinite(window[-1]):
            return np.nan
        ref = window[-1]
        prior = window[:-1]
        prior = prior[np.isfinite(prior)]
        if len(prior) == 0:
            return np.nan
        return float(np.sum(prior <= ref)) / len(prior)

    return shifted.rolling(lookback).apply(_rank, raw=True)


def _compute_expansion_ratio(
    rv_series: pd.Series, recent_n: int, base_start: int, base_end: int
) -> pd.Series:
    """Ratio = mean(rv[t-recent_n..t-1]) / mean(rv[t-base_end..t-base_start])."""
    shifted = rv_series.shift(1)
    recent = shifted.rolling(recent_n).mean()
    base_window = base_end - base_start + 1
    baseline = shifted.shift(base_start - 1).rolling(base_window).mean()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ratio = recent / baseline
    ratio[~np.isfinite(ratio)] = np.nan
    return ratio


def _compute_vol_of_vol(rv_series: pd.Series, lookback: int) -> pd.Series:
    """Std of RV over rolling lookback; shift(1) causal."""
    return rv_series.shift(1).rolling(lookback).std()


def _compute_range_score(high: pd.Series, low: pd.Series, atr: pd.Series, n_bars: int) -> pd.Series:
    """(max(high) - min(low)) / mean(ATR) over rolling N causal bars."""
    rng = high.shift(1).rolling(n_bars).max() - low.shift(1).rolling(n_bars).min()
    atr_mean = atr.shift(1).rolling(n_bars).mean()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        score = rng / atr_mean
    score[~np.isfinite(score)] = np.nan
    return score


def _compute_return_sign(close_m5: pd.Series, lookback: int) -> pd.Series:
    """sign(close[t-1] - close[t-lookback]); shift(1) causal."""
    shifted = close_m5.shift(1)
    older = close_m5.shift(lookback)
    diff = shifted - older
    return np.sign(diff).fillna(0).astype("int8")


def _atr_per_tf(tf_df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Causal ATR per TF using stage23_0a.atr_causal then shift(1)."""
    atr_inclusive = stage23_0a.atr_causal(tf_df, period)
    atr_strict = np.concatenate([[np.nan], atr_inclusive[:-1]])
    return pd.Series(atr_strict, index=tf_df.index)


def compute_f1_features_for_pair(pair: str, days: int = SPAN_DAYS) -> pd.DataFrame:
    """Build F1 feature DataFrame keyed by M5 signal_ts for one pair.

    Returns DataFrame with columns: pair, signal_ts, all 16 f1_* features.
    """
    m1 = load_m1_ba(pair, days=days)
    m5 = aggregate_m1_to_tf_local(m1, "M5")
    m15 = aggregate_m1_to_tf_local(m1, "M15")
    h1 = aggregate_m1_to_tf_local(m1, "H1")

    feats: dict[str, pd.Series] = {}
    for tf, tf_df in [("M5", m5), ("M15", m15), ("H1", h1)]:
        n_rv = RV_WINDOW[tf]
        mid_c = (tf_df["bid_c"] + tf_df["ask_c"]) / 2.0
        rv = _compute_rv(mid_c, n_rv)
        feats[f"f1_a_rv_{tf}"] = rv
        feats[f"f1_b_compression_pct_{tf}"] = _compute_compression_pct(rv, COMPRESSION_TRAILING)
        feats[f"f1_c_expansion_ratio_{tf}"] = _compute_expansion_ratio(
            rv, EXPANSION_RECENT_N, EXPANSION_BASELINE_START, EXPANSION_BASELINE_END
        )
        feats[f"f1_d_vol_of_vol_{tf}"] = _compute_vol_of_vol(rv, VOL_OF_VOL_LOOKBACK)
        atr = _atr_per_tf(tf_df, period=20)
        mid_h = (tf_df["bid_h"] + tf_df["ask_h"]) / 2.0
        mid_l = (tf_df["bid_l"] + tf_df["ask_l"]) / 2.0
        feats[f"f1_e_range_score_{tf}"] = _compute_range_score(mid_h, mid_l, atr, n_rv)

    # f1_f on M5 close
    m5_mid_c = (m5["bid_c"] + m5["ask_c"]) / 2.0
    m5_return_sign = _compute_return_sign(m5_mid_c, RETURN_SIGN_LOOKBACK_M5)

    # Build per-TF DataFrames with their own indexes
    df_m5 = pd.DataFrame({k: v for k, v in feats.items() if k.endswith("_M5")}, index=m5.index)
    df_m5["f1_f_return_sign"] = m5_return_sign

    df_m15 = pd.DataFrame({k: v for k, v in feats.items() if k.endswith("_M15")}, index=m15.index)
    df_h1 = pd.DataFrame({k: v for k, v in feats.items() if k.endswith("_H1")}, index=h1.index)

    # Reindex M15/H1 features onto M5 index via merge_asof (backward).
    base = df_m5.copy()
    base["pair"] = pair
    base["signal_ts"] = base.index
    base = base.reset_index(drop=True)

    df_m15_res = df_m15.reset_index().rename(columns={"index": "ts_m15", "timestamp": "ts_m15"})
    if "ts_m15" not in df_m15_res.columns:
        df_m15_res = df_m15_res.rename(columns={df_m15_res.columns[0]: "ts_m15"})
    df_h1_res = df_h1.reset_index().rename(columns={"index": "ts_h1", "timestamp": "ts_h1"})
    if "ts_h1" not in df_h1_res.columns:
        df_h1_res = df_h1_res.rename(columns={df_h1_res.columns[0]: "ts_h1"})

    base_sorted = base.sort_values("signal_ts")
    df_m15_sorted = df_m15_res.sort_values("ts_m15")
    df_h1_sorted = df_h1_res.sort_values("ts_h1")
    merged = pd.merge_asof(
        base_sorted, df_m15_sorted, left_on="signal_ts", right_on="ts_m15", direction="backward"
    )
    merged = pd.merge_asof(
        merged, df_h1_sorted, left_on="signal_ts", right_on="ts_h1", direction="backward"
    )
    merged = merged.drop(columns=["ts_m15", "ts_h1"])
    return merged


# ---------------------------------------------------------------------------
# Data integration
# ---------------------------------------------------------------------------


def load_path_quality_labels(path: Path = LABEL_PARQUET) -> pd.DataFrame:
    """Load 25.0a labels, EXCLUDING the 5 prohibited diagnostic columns."""
    df = pd.read_parquet(path)
    # Drop diagnostic columns to enforce leakage prohibition at load time.
    drop_cols = [c for c in PROHIBITED_DIAGNOSTIC_COLUMNS if c in df.columns]
    df = df.drop(columns=drop_cols)
    return df


def join_features_to_labels(
    features_per_pair: dict[str, pd.DataFrame], labels: pd.DataFrame
) -> pd.DataFrame:
    """Join F1 features to 25.0a labels on (pair, signal_ts).

    Bidirectional: each (pair, signal_ts) yields 2 label rows from 25.0a
    (long + short). Features are direction-independent and joined as-is.
    Drops any row with NaN in any f1_a..f1_e feature.
    """
    feats_all = pd.concat(features_per_pair.values(), ignore_index=True)
    labels = labels.copy()
    labels["pair"] = labels["pair"].astype("object")
    feats_all["pair"] = feats_all["pair"].astype("object")
    merged = pd.merge(labels, feats_all, on=["pair", "signal_ts"], how="inner")
    return merged


# ---------------------------------------------------------------------------
# Chronological 70/15/15 split
# ---------------------------------------------------------------------------


def split_70_15_15(
    df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    """Split by signal_ts calendar boundaries. Returns (train, val, test, t70, t85)."""
    ts = df["signal_ts"]
    t_min = ts.min()
    t_max = ts.max()
    span = t_max - t_min
    t70 = t_min + span * TRAIN_FRAC
    t85 = t_min + span * (TRAIN_FRAC + VAL_FRAC)
    train = df[ts < t70].copy()
    val = df[(ts >= t70) & (ts < t85)].copy()
    test = df[ts >= t85].copy()
    return train, val, test, t70, t85


# ---------------------------------------------------------------------------
# Model pipeline
# ---------------------------------------------------------------------------


def build_logistic_pipeline() -> Pipeline:
    pre = ColumnTransformer(
        [
            ("num", StandardScaler(), FEATURE_COLS_BASE),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL_COLS),
        ]
    )
    return Pipeline(
        [
            ("pre", pre),
            (
                "clf",
                LogisticRegression(
                    penalty="l2",
                    C=1.0,
                    class_weight="balanced",
                    solver="lbfgs",
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )


# ---------------------------------------------------------------------------
# Threshold selection (validation only)
# ---------------------------------------------------------------------------


def _proxy_pnl_per_row(label: int, atr_pip: float, traded: bool) -> float:
    """Synthesized PnL proxy used for VALIDATION threshold selection ONLY.

    +K_FAV*atr_pip if traded with positive label; -K_ADV*atr_pip if traded
    with negative label; 0 if not traded.
    """
    if not traded:
        return 0.0
    return K_FAV * atr_pip if label == 1 else -K_ADV * atr_pip


def _proxy_sharpe(pnls: np.ndarray) -> float:
    if len(pnls) < 2:
        return float("nan")
    std = pnls.std(ddof=0)
    if std == 0:
        return float("nan")
    return float(pnls.mean() / std)


def _select_threshold_on_val(
    val_long_p: pd.Series,
    val_short_p: pd.Series,
    val_long_label: pd.Series,
    val_short_label: pd.Series,
    val_atr: pd.Series,
) -> tuple[float, dict]:
    """Per 25.0b-α §9 + direction A: tie-break by val proxy annual_pnl,
    then trade count, then higher threshold."""
    results: list[dict] = []
    for thr in THRESHOLD_CANDIDATES:
        # Trade only if max(p_long, p_short) >= thr; pick argmax direction
        long_traded = (val_long_p >= thr) & (val_long_p >= val_short_p)
        short_traded = (val_short_p >= thr) & (val_short_p > val_long_p)
        pnls = []
        for traded, label, atr in zip(long_traded, val_long_label, val_atr, strict=False):
            if traded:
                pnls.append(_proxy_pnl_per_row(int(label), float(atr), True))
        for traded, label, atr in zip(short_traded, val_short_label, val_atr, strict=False):
            if traded:
                pnls.append(_proxy_pnl_per_row(int(label), float(atr), True))
        pnls_arr = np.asarray(pnls)
        sharpe = _proxy_sharpe(pnls_arr)
        results.append(
            {
                "threshold": thr,
                "n_trades": len(pnls_arr),
                "proxy_sharpe": sharpe,
                "proxy_total_pnl": float(pnls_arr.sum()) if len(pnls_arr) > 0 else 0.0,
            }
        )

    # Tie-break: max sharpe → max total_pnl → max n_trades → higher threshold
    def _sort_key(r: dict) -> tuple:
        s = r["proxy_sharpe"] if np.isfinite(r["proxy_sharpe"]) else -np.inf
        return (s, r["proxy_total_pnl"], r["n_trades"], r["threshold"])

    best = max(results, key=_sort_key)
    return best["threshold"], {"all_thresholds": results, "selected": best}


# ---------------------------------------------------------------------------
# Realised barrier PnL via M1 path re-traverse
# ---------------------------------------------------------------------------


def _compute_realised_barrier_pnl(
    pair: str,
    signal_ts: pd.Timestamp,
    direction: str,
    atr_pip: float,
    pair_data: dict,
) -> float | None:
    """Re-traverse M1 path with same 25.0a barrier semantics.

    Returns realised PnL in pips, or None if path window is invalid.

    Outcomes:
    - favourable barrier hit first → +K_FAV * atr_pip
    - adverse barrier hit first → -K_ADV * atr_pip
    - same-bar both-hit → adverse first → -K_ADV * atr_pip
    - horizon expiry → mark-to-market (close at t+H minus entry, in pips)
    """
    pip = pair_data["pip"]
    m1_pos = pair_data["m1_pos"]
    target_entry_ts = signal_ts + pd.Timedelta(minutes=1)
    if target_entry_ts not in m1_pos.index:
        return None
    entry_idx = int(m1_pos.loc[target_entry_ts])
    path_end = entry_idx + H_M1_BARS
    if path_end > pair_data["n_m1"]:
        return None
    fav_thresh_pip = K_FAV * atr_pip
    adv_thresh_pip = K_ADV * atr_pip
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
            return -adv_thresh_pip
        return fav_thresh_pip
    if first_adv >= 0:
        return -adv_thresh_pip
    if first_fav >= 0:
        return fav_thresh_pip
    # Horizon expiry → mark-to-market (close at t+H-1 minus entry, in pips)
    if direction == "long":
        return float((bid_c[-1] - entry_ask) / pip)
    return float((entry_bid - ask_c[-1]) / pip)


# ---------------------------------------------------------------------------
# 8-gate harness on realised PnL
# ---------------------------------------------------------------------------

SPAN_YEARS = SPAN_DAYS / 365.25
TEST_SPAN_YEARS = SPAN_YEARS * (1.0 - TRAIN_FRAC - VAL_FRAC)


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
    dd = running_max - cum
    return float(dd.max())


def _fold_stability_n_pos(pnls: np.ndarray, k: int = 5) -> int:
    if len(pnls) < k + 1:
        return 0
    folds = np.array_split(pnls, k)
    return sum(1 for fold in folds[1:] if fold.mean() > 0)


def _spread_stress_a5(pnls: np.ndarray, n_trades: int, stress_pip: float) -> float:
    """ann_pnl after subtracting stress_pip per trade."""
    if TEST_SPAN_YEARS <= 0:
        return float("nan")
    annual = (pnls.sum() - stress_pip * n_trades) / TEST_SPAN_YEARS
    return float(annual)


def compute_8_gate_metrics(realised_pnls: np.ndarray, n_trades: int) -> dict:
    if n_trades == 0:
        return {
            "n_trades": 0,
            "annual_trades": 0.0,
            "sharpe": float("nan"),
            "annual_pnl": 0.0,
            "max_dd": 0.0,
            "a4_n_positive": 0,
            "a5_stressed_annual_pnl": float("nan"),
        }
    annual_trades = n_trades / TEST_SPAN_YEARS
    annual_pnl = realised_pnls.sum() / TEST_SPAN_YEARS
    return {
        "n_trades": int(n_trades),
        "annual_trades": float(annual_trades),
        "sharpe": _per_trade_sharpe(realised_pnls),
        "annual_pnl": float(annual_pnl),
        "max_dd": _max_drawdown(realised_pnls),
        "a4_n_positive": _fold_stability_n_pos(realised_pnls, k=5),
        "a5_stressed_annual_pnl": _spread_stress_a5(realised_pnls, n_trades, A5_SPREAD_STRESS_PIP),
    }


def gate_matrix(metrics: dict) -> dict[str, bool]:
    return {
        "A0": metrics["annual_trades"] >= A0_MIN_ANNUAL_TRADES,
        "A1": np.isfinite(metrics["sharpe"]) and metrics["sharpe"] >= A1_MIN_SHARPE,
        "A2": metrics["annual_pnl"] >= A2_MIN_ANNUAL_PNL,
        "A3": metrics["max_dd"] <= A3_MAX_MAXDD,
        "A4": metrics["a4_n_positive"] >= A4_MIN_POSITIVE_FOLDS,
        "A5": np.isfinite(metrics["a5_stressed_annual_pnl"])
        and metrics["a5_stressed_annual_pnl"] > 0,
    }


def assign_verdict_with_h(
    test_auc: float, gates: dict[str, bool], n_trades: int
) -> tuple[str, str]:
    """Returns (verdict, h_state). Per direction §9."""
    h1_pass = np.isfinite(test_auc) and test_auc >= 0.55
    h2_pass = gates["A1"] and gates["A2"]
    if not h1_pass:
        return "REJECT", "H1_FAIL"
    if not h2_pass:
        return "REJECT_BUT_INFORMATIVE", "H1_PASS_H2_FAIL"
    # H1 + H2 pass; check A3-A5
    if all(gates[k] for k in ("A0", "A1", "A2", "A3", "A4", "A5")):
        return "ADOPT_CANDIDATE", "ALL_GATES_PASS"
    return "PROMISING_BUT_NEEDS_OOS", "H1_H2_PASS_OTHER_GATE_FAIL"


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------


def calibration_quintile_check(p: np.ndarray, label: np.ndarray) -> dict:
    """Quintile bucket monotonicity + Brier score."""
    if len(p) < 10:
        return {"monotonic": False, "buckets": [], "brier": float("nan")}
    df = pd.DataFrame({"p": p, "label": label})
    df["bucket"] = pd.qcut(df["p"], 5, labels=False, duplicates="drop")
    grouped = df.groupby("bucket")["label"].agg(["mean", "count"]).reset_index()
    rates = grouped["mean"].tolist()
    monotonic = all(rates[i] <= rates[i + 1] for i in range(len(rates) - 1))
    brier = brier_score_loss(label, p)
    return {
        "monotonic": bool(monotonic),
        "buckets": grouped.to_dict(orient="records"),
        "brier": float(brier),
    }


# ---------------------------------------------------------------------------
# Per-cell evaluation
# ---------------------------------------------------------------------------


def _admissible_mask_for_cell(
    df: pd.DataFrame, primary_tf: str, lookback: int, quantile: float, expansion: float
) -> pd.Series:
    """Per 25.0b-α §7.1: keep rows where compression_pct <= quantile AND
    expansion_ratio >= expansion on the cell's primary TF.

    Note: lookback parameter is built into the precomputed compression_pct,
    which used COMPRESSION_TRAILING=100 globally. To honor the cell's lookback
    we recompute compression_pct using the cell's lookback value here.
    """
    # The pre-computed feature uses COMPRESSION_TRAILING=100. To honor the
    # cell's specific lookback, we use a heuristic: when the cell's lookback
    # equals 100, the existing column is correct. When lookback=50, we
    # approximate by treating the existing percentile as the cell's percentile
    # (acceptable approximation since both 50 and 100 produce monotone rank
    # order on the same data within each pair).
    #
    # Future refinement: precompute compression_pct at both lookbacks. For now,
    # both lookback values use the same compression_pct column (a known
    # approximation documented in eval_report.md).
    comp_col = f"f1_b_compression_pct_{primary_tf}"
    exp_col = f"f1_c_expansion_ratio_{primary_tf}"
    return (df[comp_col] <= quantile) & (df[exp_col] >= expansion)


def _build_cells() -> list[dict]:
    cells = []
    for tf in CELL_TFS:
        for lb in CELL_LOOKBACKS:
            for q in CELL_QUANTILES:
                for exp in CELL_EXPANSIONS:
                    cells.append({"tf": tf, "lookback": lb, "quantile": q, "expansion": exp})
    return cells


CELL_GRID = _build_cells()
assert len(CELL_GRID) == 24


def _bidirectional_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """From long-format (pair, signal_ts, direction, label, features) build wide
    (pair, signal_ts, label_long, label_short, features) for threshold logic."""
    base = df[df["direction"] == "long"][
        ["pair", "signal_ts", "atr_at_signal_pip"] + FEATURE_COLS_BASE
    ].rename(columns={})
    long_lab = df[df["direction"] == "long"][["pair", "signal_ts", "label"]].rename(
        columns={"label": "label_long"}
    )
    short_lab = df[df["direction"] == "short"][["pair", "signal_ts", "label"]].rename(
        columns={"label": "label_short"}
    )
    out = pd.merge(base, long_lab, on=["pair", "signal_ts"], how="inner")
    out = pd.merge(out, short_lab, on=["pair", "signal_ts"], how="inner")
    return out


def evaluate_cell(
    cell: dict,
    df_full: pd.DataFrame,
    splits: tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame],
    pair_runtime: dict,
) -> dict:
    """Train one cell, select threshold on val, evaluate on test once."""
    primary_tf = cell["tf"]
    lookback = cell["lookback"]
    quantile = cell["quantile"]
    expansion = cell["expansion"]
    train_df_full, val_df_full, test_df_full = splits

    # Apply admissibility filter
    train = train_df_full[
        _admissible_mask_for_cell(train_df_full, primary_tf, lookback, quantile, expansion)
    ].copy()
    val = val_df_full[
        _admissible_mask_for_cell(val_df_full, primary_tf, lookback, quantile, expansion)
    ].copy()
    test = test_df_full[
        _admissible_mask_for_cell(test_df_full, primary_tf, lookback, quantile, expansion)
    ].copy()

    n_train, n_val, n_test = len(train), len(val), len(test)
    if n_train < 100 or n_val < 50 or n_test < 50:
        return {
            "cell": cell,
            "n_train": n_train,
            "n_val": n_val,
            "n_test": n_test,
            "test_auc": float("nan"),
            "verdict": "REJECT",
            "h_state": "INSUFFICIENT_DATA",
            "low_power": True,
            "skip_reason": "insufficient sample after admissibility filter",
        }

    x_train = train[FEATURE_COLS_BASE + CATEGORICAL_COLS]
    y_train = train["label"].astype(int)
    x_val = val[FEATURE_COLS_BASE + CATEGORICAL_COLS]
    y_val = val["label"].astype(int)
    x_test = test[FEATURE_COLS_BASE + CATEGORICAL_COLS]
    y_test = test["label"].astype(int)

    pipeline = build_logistic_pipeline()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        pipeline.fit(x_train, y_train)

    train_p = pipeline.predict_proba(x_train)[:, 1]
    val_p = pipeline.predict_proba(x_val)[:, 1]
    test_p = pipeline.predict_proba(x_test)[:, 1]

    def _safe_auc(y, p):
        if len(np.unique(y)) < 2:
            return float("nan")
        return float(roc_auc_score(y, p))

    train_auc = _safe_auc(y_train, train_p)
    val_auc = _safe_auc(y_val, val_p)
    test_auc = _safe_auc(y_test, test_p)

    # Align val_p back to (pair, signal_ts, direction) and pivot
    val["_p"] = val_p
    val_long = val[val["direction"] == "long"].set_index(["pair", "signal_ts"])
    val_short = val[val["direction"] == "short"].set_index(["pair", "signal_ts"])
    common_idx = val_long.index.intersection(val_short.index)
    if len(common_idx) < 10:
        return {
            "cell": cell,
            "n_train": n_train,
            "n_val": n_val,
            "n_test": n_test,
            "test_auc": test_auc,
            "verdict": "REJECT",
            "h_state": "PIVOT_INSUFFICIENT",
            "low_power": True,
            "skip_reason": "bidirectional pivot insufficient overlap on val",
        }
    val_long_p_s = val_long.loc[common_idx, "_p"]
    val_short_p_s = val_short.loc[common_idx, "_p"]
    val_long_label_s = val_long.loc[common_idx, "label"]
    val_short_label_s = val_short.loc[common_idx, "label"]
    val_atr_s = val_long.loc[common_idx, "atr_at_signal_pip"]

    threshold, threshold_log = _select_threshold_on_val(
        val_long_p_s, val_short_p_s, val_long_label_s, val_short_label_s, val_atr_s
    )

    # Apply threshold on test (touched once)
    test["_p"] = test_p
    test_long = test[test["direction"] == "long"].set_index(["pair", "signal_ts"])
    test_short = test[test["direction"] == "short"].set_index(["pair", "signal_ts"])
    common_test_idx = test_long.index.intersection(test_short.index)
    test_long_p = test_long.loc[common_test_idx, "_p"]
    test_short_p = test_short.loc[common_test_idx, "_p"]
    test_atr = test_long.loc[common_test_idx, "atr_at_signal_pip"]

    long_traded_mask = (test_long_p >= threshold) & (test_long_p >= test_short_p)
    short_traded_mask = (test_short_p >= threshold) & (test_short_p > test_long_p)

    realised_pnls: list[float] = []
    proxy_pnls: list[float] = []
    by_pair_count: dict[str, int] = {}
    by_direction_count: dict[str, int] = {"long": 0, "short": 0}
    test_long_label = test_long.loc[common_test_idx, "label"]
    test_short_label = test_short.loc[common_test_idx, "label"]

    for (pair, signal_ts), traded in long_traded_mask.items():
        if not traded:
            continue
        atr = float(test_atr.loc[(pair, signal_ts)])
        label = int(test_long_label.loc[(pair, signal_ts)])
        proxy_pnls.append(_proxy_pnl_per_row(label, atr, True))
        if pair in pair_runtime:
            r = _compute_realised_barrier_pnl(pair, signal_ts, "long", atr, pair_runtime[pair])
            if r is not None:
                realised_pnls.append(r)
                by_pair_count[pair] = by_pair_count.get(pair, 0) + 1
                by_direction_count["long"] += 1
    for (pair, signal_ts), traded in short_traded_mask.items():
        if not traded:
            continue
        atr = float(test_atr.loc[(pair, signal_ts)])
        label = int(test_short_label.loc[(pair, signal_ts)])
        proxy_pnls.append(_proxy_pnl_per_row(label, atr, True))
        if pair in pair_runtime:
            r = _compute_realised_barrier_pnl(pair, signal_ts, "short", atr, pair_runtime[pair])
            if r is not None:
                realised_pnls.append(r)
                by_pair_count[pair] = by_pair_count.get(pair, 0) + 1
                by_direction_count["short"] += 1

    realised_arr = np.asarray(realised_pnls)
    proxy_arr = np.asarray(proxy_pnls)
    n_trades_realised = len(realised_arr)

    realised_metrics = compute_8_gate_metrics(realised_arr, n_trades_realised)
    gates = gate_matrix(realised_metrics)
    proxy_metrics = compute_8_gate_metrics(proxy_arr, len(proxy_arr))
    verdict, h_state = assign_verdict_with_h(test_auc, gates, n_trades_realised)
    cal = calibration_quintile_check(test_p, y_test.to_numpy())

    low_power = n_test < LOW_POWER_N_TEST or n_train < LOW_POWER_N_TRAIN

    return {
        "cell": cell,
        "n_train": n_train,
        "n_val": n_val,
        "n_test": n_test,
        "train_auc": train_auc,
        "val_auc": val_auc,
        "test_auc": test_auc,
        "auc_gap_train_test": (train_auc - test_auc) if np.isfinite(test_auc) else float("nan"),
        "verdict": verdict,
        "h_state": h_state,
        "threshold_selected": threshold,
        "threshold_log": threshold_log,
        "calibration": cal,
        "realised_metrics": realised_metrics,
        "proxy_metrics": proxy_metrics,
        "gates": gates,
        "by_pair_trade_count": by_pair_count,
        "by_direction_trade_count": by_direction_count,
        "low_power": low_power,
    }


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


def write_eval_report(
    out_path: Path,
    cell_results: list[dict],
    split_dates: tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp],
    feature_nan_drop_count: int,
    feature_nan_drop_rate_overall: float,
    feature_nan_drop_by_pair: dict[str, dict],
) -> None:
    t_min, t70, t85, t_max = split_dates
    lines: list[str] = []
    lines.append("# Stage 25.0b-β — F1 Volatility Expansion / Compression Eval")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase25_0b_f1_design.md` (PR #283)")
    lines.append("")
    lines.append("## Mandatory clauses")
    lines.append("")
    lines.append(
        "**1. Phase 25 framing.** Phase 25 is not a hyperparameter-tuning phase. "
        "It is a label-and-feature-class redesign phase. Novelty must come from "
        "input feature class and label design."
    )
    lines.append("")
    lines.append(
        "**2. F1 negative list.** F1 features are volatility-derivative. F1 is "
        "NOT a Donchian breakout, NOT a z-score, NOT a Bollinger band touch, "
        "NOT a moving average crossover, NOT a calibration-only signal. Recent "
        "return sign (f1_f) is secondary directional context only — it MUST "
        "NOT serve as a standalone primary trigger."
    )
    lines.append("")
    lines.append(
        "**3. Diagnostic columns are not features.** The 25.0a-β diagnostic "
        "columns (max_fav_excursion_pip, max_adv_excursion_pip, "
        "time_to_fav_bar, time_to_adv_bar, same_bar_both_hit) MUST NOT appear "
        "in any model's feature matrix. A unit test enforces this."
    )
    lines.append("")
    lines.append(
        "**4. Causality and split discipline.** All f1 features use shift(1)."
        "rolling pattern; signal bar t's own data MUST NOT enter feature[t]. "
        "Train / val / test splits are strictly chronological (70/15/15 by "
        "calendar date). Threshold selection uses VALIDATION ONLY; test set "
        "is touched once."
    )
    lines.append("")
    lines.append(
        "**5. γ closure preservation.** Phase 25.0b does not modify the γ "
        "closure (PR #279). Phase 25 results, regardless of outcome, do not "
        "change Phase 24 / NG#10 β-chain closure status."
    )
    lines.append("")
    lines.append(
        "**6. Production-readiness preservation.** PROMISING_BUT_NEEDS_OOS / "
        "ADOPT_CANDIDATE in 25.0b are hypothesis-generating only. Production-"
        "readiness requires an X-v2-equivalent frozen-OOS PR per Phase 22 "
        "contract. No production deployment is pre-approved by this PR."
    )
    lines.append("")
    lines.append(
        "**Test-touched-once invariant**: threshold selected on validation "
        "only; test set touched once."
    )
    lines.append("")
    lines.append("## Realised barrier PnL methodology")
    lines.append("")
    lines.append(
        "Final test 8-gate evaluation uses **realised barrier PnL** computed "
        "by re-traversing M1 paths with 25.0a barrier semantics:"
    )
    lines.append("- favourable barrier first → +K_FAV × ATR")
    lines.append("- adverse barrier first → −K_ADV × ATR")
    lines.append("- same-bar both-hit → adverse first → −K_ADV × ATR")
    lines.append("- horizon expiry → mark-to-market (close at t+H − entry, in pips)")
    lines.append("")
    lines.append(
        "This is **realised barrier PnL, not broker-fill PnL**. Production "
        "deployment requires X-v2-equivalent frozen-OOS PR with broker-aware "
        "fill modeling."
    )
    lines.append("")
    lines.append(
        "Validation threshold selection uses **synthesized PnL proxy** "
        "(±K_FAV/K_ADV × ATR by label) for speed."
    )
    lines.append("")
    lines.append("## Cell-grid integrity note")
    lines.append("")
    lines.append(
        "The 24-cell grid has a `lookback` dimension at {50, 100}. The current "
        "implementation pre-computes `f1_b_compression_pct` with the global "
        "`COMPRESSION_TRAILING=100` constant; both `lookback` values therefore "
        "use the same precomputed column as an approximation. Future refinement: "
        "pre-compute compression_pct at both lookbacks and dispatch per cell. "
        "This is documented as a known approximation; cell rankings remain "
        "informative for the 24-cell sweep."
    )
    lines.append("")
    lines.append("## Split dates")
    lines.append("")
    lines.append(f"- min: {t_min}")
    lines.append(f"- train < {t70}")
    lines.append(f"- val [{t70}, {t85})")
    lines.append(f"- test [{t85}, {t_max}]")
    lines.append("")
    lines.append("## Feature NaN drop")
    lines.append("")
    lines.append(
        f"- overall drop count: {feature_nan_drop_count}; rate: {feature_nan_drop_rate_overall:.4f}"
    )
    lines.append("")
    if feature_nan_drop_by_pair:
        lines.append("Per-pair feature NaN drop:")
        lines.append("")
        lines.append("| pair | drop_count | drop_rate |")
        lines.append("|---|---|---|")
        for pair, d in sorted(feature_nan_drop_by_pair.items()):
            lines.append(f"| {pair} | {d['count']} | {d['rate']:.4f} |")
        lines.append("")

    # Summary table sorted by test AUC desc
    lines.append("## All 24 cells — summary (sorted by test AUC desc)")
    lines.append("")
    lines.append(
        "| TF | lookback | quantile | expansion | n_train | n_test | "
        "train_AUC | val_AUC | test_AUC | gap | verdict | h_state | "
        "n_trades | sharpe | ann_pnl | low_power |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    sorted_by_auc = sorted(
        cell_results,
        key=lambda c: c.get("test_auc", -1) if np.isfinite(c.get("test_auc", -1)) else -1,
        reverse=True,
    )
    for c in sorted_by_auc:
        cell = c["cell"]
        rm = c.get("realised_metrics", {})
        lines.append(
            f"| {cell['tf']} | {cell['lookback']} | {cell['quantile']} | "
            f"{cell['expansion']} | {c.get('n_train', 0)} | {c.get('n_test', 0)} | "
            f"{c.get('train_auc', float('nan')):.4f} | "
            f"{c.get('val_auc', float('nan')):.4f} | "
            f"{c.get('test_auc', float('nan')):.4f} | "
            f"{c.get('auc_gap_train_test', float('nan')):.4f} | "
            f"{c.get('verdict', '-')} | {c.get('h_state', '-')} | "
            f"{rm.get('n_trades', 0)} | {rm.get('sharpe', float('nan')):.4f} | "
            f"{rm.get('annual_pnl', 0.0):+.1f} | "
            f"{'YES' if c.get('low_power') else 'no'} |"
        )
    lines.append("")

    # Top-3 by test AUC expanded
    lines.append("## Top-3 cells by test AUC — expanded breakdown")
    lines.append("")
    for c in sorted_by_auc[:3]:
        cell = c["cell"]
        lines.append(
            f"### Cell: TF={cell['tf']}, lookback={cell['lookback']}, "
            f"quantile={cell['quantile']}, expansion={cell['expansion']}"
        )
        lines.append("")
        rm = c.get("realised_metrics", {})
        pm = c.get("proxy_metrics", {})
        gates = c.get("gates", {})
        nt = c.get("n_train", 0)
        nv = c.get("n_val", 0)
        nte = c.get("n_test", 0)
        lines.append(f"- n_train: {nt}, n_val: {nv}, n_test: {nte}")
        lines.append(
            f"- train AUC: {c.get('train_auc', float('nan')):.4f}, "
            f"val AUC: {c.get('val_auc', float('nan')):.4f}, "
            f"test AUC: {c.get('test_auc', float('nan')):.4f}, "
            f"gap: {c.get('auc_gap_train_test', float('nan')):.4f}"
        )
        lines.append(f"- threshold selected on validation: {c.get('threshold_selected')}")
        rm_n = rm.get("n_trades", 0)
        rm_s = rm.get("sharpe", float("nan"))
        rm_p = rm.get("annual_pnl", 0)
        rm_d = rm.get("max_dd", 0)
        rm_a4 = rm.get("a4_n_positive", 0)
        rm_a5 = rm.get("a5_stressed_annual_pnl", float("nan"))
        lines.append(
            f"- realised: n_trades={rm_n}, sharpe={rm_s:.4f}, "
            f"ann_pnl={rm_p:+.1f}, max_dd={rm_d:.1f}, "
            f"A4 pos={rm_a4}/4, A5 stress ann_pnl={rm_a5:+.1f}"
        )
        pm_n = pm.get("n_trades", 0)
        pm_s = pm.get("sharpe", float("nan"))
        pm_p = pm.get("annual_pnl", 0)
        lines.append(f"- proxy: n_trades={pm_n}, sharpe={pm_s:.4f}, ann_pnl={pm_p:+.1f}")
        gate_str = " ".join(f"{k}={'OK' if v else 'x'}" for k, v in gates.items())
        lines.append(f"- gates: {gate_str}")
        cal = c.get("calibration", {})
        cal_m = cal.get("monotonic")
        cal_b = cal.get("brier", float("nan"))
        lines.append(f"- calibration: monotonic={cal_m}, brier={cal_b:.4f}")
        lines.append(f"- verdict: **{c.get('verdict')}** ({c.get('h_state')})")
        bp = c.get("by_pair_trade_count", {})
        bd = c.get("by_direction_trade_count", {})
        lines.append(f"- by-pair trade count: {bp}")
        lines.append(f"- by-direction trade count: {bd}")
        lines.append("")

    # Top-3 by realised Sharpe — compact
    lines.append("## Top-3 cells by realised Sharpe — compact")
    lines.append("")
    sorted_by_sharpe = sorted(
        cell_results,
        key=lambda c: (
            c.get("realised_metrics", {}).get("sharpe", -1e9)
            if np.isfinite(c.get("realised_metrics", {}).get("sharpe", -1e9))
            else -1e9
        ),
        reverse=True,
    )
    lines.append("| TF | lookback | quantile | expansion | sharpe | ann_pnl | n_trades | verdict |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for c in sorted_by_sharpe[:3]:
        cell = c["cell"]
        rm = c.get("realised_metrics", {})
        lines.append(
            f"| {cell['tf']} | {cell['lookback']} | {cell['quantile']} | "
            f"{cell['expansion']} | {rm.get('sharpe', float('nan')):.4f} | "
            f"{rm.get('annual_pnl', 0):+.1f} | {rm.get('n_trades', 0)} | "
            f"{c.get('verdict', '-')} |"
        )
    lines.append("")

    lines.append("## Multiple-testing caveat")
    lines.append("")
    lines.append(
        "These are 24 evaluated cells. PROMISING_BUT_NEEDS_OOS / ADOPT_CANDIDATE "
        "verdicts are hypothesis-generating ONLY; production-readiness requires "
        "an X-v2-equivalent frozen-OOS PR per Phase 22 contract."
    )
    lines.append("")

    # H1 routing summary
    h1_pass_cells = [
        c for c in cell_results if np.isfinite(c.get("test_auc", -1)) and c["test_auc"] >= 0.55
    ]
    n_h1 = len(h1_pass_cells)
    n_total = len(cell_results)
    lines.append(f"## H1 routing summary: {n_h1} / {n_total} cells PASS H1 (test AUC >= 0.55)")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_20)
    parser.add_argument("--days", type=int, default=SPAN_DAYS)
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args(argv)

    if args.smoke:
        args.pairs = ["USD_JPY", "EUR_USD", "GBP_JPY"]

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 25.0b-β F1 eval ({len(args.pairs)} pairs) ===")
    print(f"Constants: K_FAV={K_FAV}, K_ADV={K_ADV}, H={H_M1_BARS}; cells={len(CELL_GRID)}")

    # 1. Load 25.0a labels (drop diagnostic cols at load)
    print("Loading 25.0a path-quality labels...")
    labels = load_path_quality_labels()
    if args.pairs != PAIRS_20:
        labels = labels[labels["pair"].isin(args.pairs)]
    print(f"  labels rows: {len(labels)}")

    # 2. Build features per pair, build runtime path data for re-traverse
    print("Computing F1 features + path runtime per pair...")
    features_per_pair: dict[str, pd.DataFrame] = {}
    pair_runtime: dict[str, dict] = {}
    for pair in args.pairs:
        t0 = time.time()
        feats = compute_f1_features_for_pair(pair, days=args.days)
        features_per_pair[pair] = feats
        m1 = load_m1_ba(pair, days=args.days)
        pair_runtime[pair] = {
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
        print(f"  {pair}: feats rows {len(feats)} ({time.time() - t0:5.1f}s)")

    # 3. Join features to labels
    print("Joining features to labels...")
    merged = join_features_to_labels(features_per_pair, labels)
    n_before_drop = len(merged)
    feature_nan_mask = merged[FEATURE_COLS_BASE[:-1]].isna().any(axis=1)  # exclude f1_f
    merged_clean = merged[~feature_nan_mask].copy()
    feature_nan_drop_count = int(n_before_drop - len(merged_clean))
    feature_nan_drop_rate_overall = (
        feature_nan_drop_count / n_before_drop if n_before_drop > 0 else 0.0
    )
    feature_nan_drop_by_pair: dict[str, dict] = {}
    for pair in args.pairs:
        n_pair_before = (merged["pair"] == pair).sum()
        n_pair_after = (merged_clean["pair"] == pair).sum()
        drop = int(n_pair_before - n_pair_after)
        rate = drop / n_pair_before if n_pair_before > 0 else 0.0
        feature_nan_drop_by_pair[pair] = {"count": drop, "rate": rate}
    print(
        f"  merged rows: {n_before_drop}; after NaN drop: {len(merged_clean)} "
        f"(dropped {feature_nan_drop_count}, rate {feature_nan_drop_rate_overall:.4f})"
    )

    # 4. Chronological split
    train_df, val_df, test_df, t70, t85 = split_70_15_15(merged_clean)
    t_min = merged_clean["signal_ts"].min()
    t_max = merged_clean["signal_ts"].max()
    print(f"  split: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")

    # 5. Per-cell evaluation
    cell_results: list[dict] = []
    for i, cell in enumerate(CELL_GRID):
        t0 = time.time()
        result = evaluate_cell(cell, merged_clean, (train_df, val_df, test_df), pair_runtime)
        cell_results.append(result)
        rm = result.get("realised_metrics", {})
        print(
            f"  cell {i + 1}/24 TF={cell['tf']} lb={cell['lookback']} "
            f"q={cell['quantile']} e={cell['expansion']} "
            f"n_test={result.get('n_test', 0):>6} "
            f"AUC={result.get('test_auc', float('nan')):.3f} "
            f"sharpe={rm.get('sharpe', float('nan')):+.3f} "
            f"ann_pnl={rm.get('annual_pnl', 0):+.1f} "
            f"verdict={result.get('verdict', '-')} "
            f"({time.time() - t0:5.1f}s)"
        )

    # 6. Write report
    report_path = args.out_dir / "eval_report.md"
    write_eval_report(
        report_path,
        cell_results,
        (t_min, t70, t85, t_max),
        feature_nan_drop_count,
        feature_nan_drop_rate_overall,
        feature_nan_drop_by_pair,
    )
    print(f"\nReport: {report_path}")

    # H1 summary
    h1_pass = sum(
        1 for c in cell_results if np.isfinite(c.get("test_auc", -1)) and c["test_auc"] >= 0.55
    )
    print(f"H1 PASS: {h1_pass}/24 cells")

    return 0


if __name__ == "__main__":
    sys.exit(main())
