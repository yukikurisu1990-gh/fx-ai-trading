"""Stage 22.0e Meta-Labeling on Donchian-immediate primary signal.

Trains a LightGBM binary classifier per (N, horizon, exit_rule, fold) cell
on causal context features, then sweeps confidence thresholds to filter
trades. Verdict via eight gates A0..A5 + S0 (shuffled-target sanity) + S1
(train-test parity).

Audit-mandated constraints (PR #258):
- MAIN_FEATURE_COLS excludes is_week_open_window, hour_utc, dow,
  and all forward-looking outcome columns.
- hour_utc / dow appear only in the Ablation-A / Ablation-B diagnostic
  paths (not headline verdict).
- y depends on the cell's exit_rule (tb_pnl-cell uses tb_pnl sign;
  time_exit_pnl-cell uses time_exit_pnl sign).
- Early-stopping validation uses the time-ordered last 20% of the train
  range (NOT random split) to avoid future leakage.

Touches NO src/ files, NO scripts/run_*.py, NO DB schema. 20-pair
canonical universe; no time-of-day or pair filter.
"""

from __future__ import annotations

import argparse
import sys
import time
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

warnings.filterwarnings(
    "ignore",
    message="no explicit representation of timezones available for np.datetime64",
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
LABEL_DIR = REPO_ROOT / "artifacts" / "stage22_0a" / "labels"
OUT_DIR = REPO_ROOT / "artifacts" / "stage22_0e"

PAIRS_CANONICAL_20 = [
    "EUR_USD",
    "GBP_USD",
    "AUD_USD",
    "NZD_USD",
    "USD_CHF",
    "USD_CAD",
    "EUR_GBP",
    "USD_JPY",
    "EUR_JPY",
    "GBP_JPY",
    "AUD_JPY",
    "NZD_JPY",
    "CHF_JPY",
    "EUR_CHF",
    "EUR_AUD",
    "EUR_CAD",
    "AUD_NZD",
    "AUD_CAD",
    "GBP_AUD",
    "GBP_CHF",
]

# Sweep dimensions
N_DONCHIAN_VALUES: tuple[int, ...] = (20, 50)
CONF_THRESHOLDS: tuple[float, ...] = (0.50, 0.55, 0.60, 0.65)
HORIZONS: tuple[int, ...] = (10, 20, 40)
EXIT_RULES: tuple[str, ...] = ("tb_pnl", "time_exit_pnl")

# Audit allowlist (PR #258 §10)
MAIN_FEATURE_COLS: tuple[str, ...] = (
    "cost_ratio",
    "atr_at_entry",
    "spread_entry",
    "z_score_10",
    "z_score_20",
    "z_score_50",
    "z_score_100",
    "donchian_position",
    "breakout_age_M5_bars",
    "pair",
    "direction",
)

# Forbidden in main (asserted by tests)
FORBIDDEN_FEATURES: frozenset[str] = frozenset(
    {
        # User-modified policy
        "is_week_open_window",
        "hour_utc",
        "dow",
        # Forward-looking outcome columns
        "mfe_after_cost",
        "mae_after_cost",
        "best_possible_pnl",
        "time_exit_pnl",
        "tb_pnl",
        "tb_outcome",
        "time_to_tp",
        "time_to_sl",
        "same_bar_tp_sl_ambiguous",
        "path_shape_class",
        "exit_bid_close",
        "exit_ask_close",
        "valid_label",
        "gap_affected_forward_window",
    }
)

# Ablation extras (diagnostic only)
ABLATION_A_EXTRA: tuple[str, ...] = ("hour_utc",)
ABLATION_B_EXTRA: tuple[str, ...] = ("hour_utc", "dow")
ABLATION_LIFT_THRESHOLD = 0.05

# Walk-forward
N_OOS_FOLDS = 4  # k=1..4 (k=0 dropped)
EARLY_STOP_VAL_FRAC = 0.20  # time-ordered last 20% of train as ES validation

# Standard
N_FOLDS_FOR_DISPLAY = 4
SPREAD_STRESS_PIPS: tuple[float, ...] = (0.0, 0.2, 0.5)
EVAL_SPAN_YEARS_DEFAULT = 730.0 / 365.25
MIN_TRADES_FOR_RANKING = 30

# ADOPT gates
ADOPT_MIN_TRADES = 70
OVERTRADE_WARN_TRADES = 1000
ADOPT_MIN_SHARPE = 0.082
ADOPT_MIN_PNL = 180.0
ADOPT_MAX_DD = 200.0
ADOPT_MIN_FOLD_POSNEG = (3, 1)  # 4 OOS folds → 3/1
S0_HARD_GATE = 0.10
S0_DIAGNOSTIC = 0.05
S1_MAX_TRAIN_TEST_GAP = 0.30

# LightGBM hyperparameters
LGBM_PARAMS = {
    "objective": "binary",
    "metric": "binary_logloss",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "n_estimators": 200,
    "min_data_in_leaf": 100,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.9,
    "bagging_freq": 5,
    "verbose": -1,
}


# ---------------------------------------------------------------------------
# pip helper
# ---------------------------------------------------------------------------


def pip_size_for(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------


def load_m1_ba(pair: str, days: int = 730) -> pd.DataFrame:
    path = DATA_DIR / f"candles_{pair}_M1_{days}d_BA.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_json(path, lines=True)
    df["timestamp"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    keep = ["bid_o", "bid_h", "bid_l", "bid_c", "ask_o", "ask_h", "ask_l", "ask_c"]
    return df[keep].astype(np.float64)


def aggregate_m1_to_m5_mid(m1: pd.DataFrame) -> pd.DataFrame:
    mid_h = (m1["bid_h"] + m1["ask_h"]) / 2.0
    mid_l = (m1["bid_l"] + m1["ask_l"]) / 2.0
    mid_c = (m1["bid_c"] + m1["ask_c"]) / 2.0
    return pd.DataFrame(
        {
            "mid_h": mid_h.resample("5min", closed="right", label="right").max(),
            "mid_l": mid_l.resample("5min", closed="right", label="right").min(),
            "mid_c": mid_c.resample("5min", closed="right", label="right").last(),
        }
    ).dropna(how="all")


def causal_zscore(mid: pd.Series, n: int) -> pd.Series:
    mu = mid.rolling(n, min_periods=n).mean()
    sigma = mid.rolling(n, min_periods=n).std(ddof=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        return (mid - mu) / sigma.where(sigma > 0, np.nan)


def detect_donchian_breakouts(m5: pd.DataFrame, n: int) -> pd.DataFrame:
    """Causal Donchian (shift(1)) breakout detection."""
    hi = m5["mid_h"].shift(1).rolling(n, min_periods=n).max()
    lo = m5["mid_l"].shift(1).rolling(n, min_periods=n).min()
    long_break = m5["mid_c"] > hi
    short_break = m5["mid_c"] < lo
    longs = pd.DataFrame(
        {
            "signal_ts_M5": m5.index[long_break],
            "direction": "long",
            "break_level": hi[long_break].values,
            "mid_close": m5["mid_c"][long_break].values,
        }
    )
    shorts = pd.DataFrame(
        {
            "signal_ts_M5": m5.index[short_break],
            "direction": "short",
            "break_level": lo[short_break].values,
            "mid_close": m5["mid_c"][short_break].values,
        }
    )
    return (
        pd.concat([longs, shorts], ignore_index=True)
        .sort_values("signal_ts_M5")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Per-pair signal dataset construction
# ---------------------------------------------------------------------------


_LABEL_COLS = (
    "entry_ts",
    "horizon_bars",
    "direction",
    "valid_label",
    "gap_affected_forward_window",
    "tb_pnl",
    "time_exit_pnl",
    "spread_entry",
    "cost_ratio",
    "atr_at_entry",
    "hour_utc",
    "dow",  # for ablations and diagnostics; never in main features
)


def build_signal_dataset(pair: str, n_donchian: int, days: int = 730) -> pd.DataFrame:
    """Construct one row per (Donchian breakout × horizon × exit_rule) for a pair.

    Returns a DataFrame with columns: entry_ts, pair, direction, horizon_bars,
    plus all MAIN_FEATURE_COLS, hour_utc, dow (for ablation), and the per-cell
    PnL columns tb_pnl / time_exit_pnl.
    """
    m1 = load_m1_ba(pair, days=days)
    label_path = LABEL_DIR / f"labels_{pair}.parquet"
    if not label_path.exists():
        raise FileNotFoundError(label_path)
    labels = pd.read_parquet(label_path, columns=list(_LABEL_COLS))
    labels = labels[labels["valid_label"] & ~labels["gap_affected_forward_window"]]
    if not pd.api.types.is_datetime64_any_dtype(labels["entry_ts"]):
        labels["entry_ts"] = pd.to_datetime(labels["entry_ts"], utc=True)

    # Donchian breakouts on M1->M5 aggregation
    m5 = aggregate_m1_to_m5_mid(m1)
    breakouts = detect_donchian_breakouts(m5, n_donchian)
    if breakouts.empty:
        return pd.DataFrame()

    # Causal z-score series on M1 mid_close
    mid_m1 = (m1["bid_c"] + m1["ask_c"]) / 2.0
    z_series = {n: causal_zscore(mid_m1, n) for n in (10, 20, 50, 100)}

    # entry_ts = first M1 bar with timestamp > signal_ts_M5
    m1_ts_int = m1.index.values.astype("datetime64[ns]").view("int64")
    sig_ts_int = breakouts["signal_ts_M5"].values.astype("datetime64[ns]").view("int64")
    entry_idx = np.searchsorted(m1_ts_int, sig_ts_int, side="right")
    valid_entry = entry_idx < len(m1)
    breakouts = breakouts[valid_entry].copy()
    entry_idx = entry_idx[valid_entry]
    # Use the tz-aware DatetimeIndex (m1.index[entry_idx]) — m1.index.values
    # returns a tz-naive numpy array, which would not match the tz-aware
    # entry_ts in the labels parquet.
    breakouts["entry_ts"] = m1.index[entry_idx]

    # Per-direction breakout age (M5 bars since previous same-direction breakout)
    breakouts = breakouts.sort_values("signal_ts_M5").reset_index(drop=True)
    age_arr = np.full(len(breakouts), 1000, dtype=np.int32)  # cap at 1000
    last_long_idx = -1
    last_short_idx = -1
    m5_index_int = m5.index.values.astype("datetime64[ns]").view("int64")
    sig_m5_int = breakouts["signal_ts_M5"].values.astype("datetime64[ns]").view("int64")
    sig_m5_pos = np.searchsorted(m5_index_int, sig_m5_int)
    for k in range(len(breakouts)):
        d = breakouts.iloc[k]["direction"]
        cur = sig_m5_pos[k]
        if d == "long":
            if last_long_idx >= 0:
                age_arr[k] = min(1000, cur - last_long_idx)
            last_long_idx = cur
        else:
            if last_short_idx >= 0:
                age_arr[k] = min(1000, cur - last_short_idx)
            last_short_idx = cur
    breakouts["breakout_age_M5_bars"] = age_arr

    # z-score features at signal_ts_M5 (M1 bar at the M5 close)
    # The signal_ts_M5 timestamp aligns with M1 timestamps (5-min boundaries are M1 ts)
    for n in (10, 20, 50, 100):
        z_at_sig = z_series[n].reindex(breakouts["signal_ts_M5"].values).to_numpy()
        breakouts[f"z_score_{n}"] = z_at_sig

    # Now produce one row per (breakout, horizon) by joining against labels parquet
    sub_per_horizon: dict[int, pd.DataFrame] = {}
    for h in HORIZONS:
        sub = labels[(labels["horizon_bars"] == h)]
        sub = sub.set_index(["entry_ts", "direction"])
        sub_per_horizon[h] = sub

    rows: list[pd.DataFrame] = []
    # Build join keys using tz-aware Timestamps (NOT numpy datetime64, which
    # strips the timezone and breaks the multiindex match against the
    # tz-aware labels parquet).
    entry_ts_list = list(breakouts["entry_ts"])  # list[pd.Timestamp]
    dir_list = list(breakouts["direction"])
    join_keys = list(zip(entry_ts_list, dir_list, strict=True))
    for h in HORIZONS:
        sub = sub_per_horizon[h]
        try:
            joined = sub.reindex(join_keys)
        except Exception:
            joined = pd.DataFrame()
        if joined.empty:
            continue
        joined_arr = joined.reset_index(drop=True)
        block = breakouts.copy()
        block["horizon_bars"] = h
        # Bring in the per-row PnL columns and context
        for col in (
            "tb_pnl",
            "time_exit_pnl",
            "spread_entry",
            "cost_ratio",
            "atr_at_entry",
            "hour_utc",
            "dow",
        ):
            block[col] = joined_arr[col].values
        # Drop rows where the join failed (NaN in any required column)
        block = block.dropna(subset=["tb_pnl", "time_exit_pnl", "atr_at_entry", "spread_entry"])
        if block.empty:
            continue
        # donchian_position: signed distance from break level / atr_at_entry
        # For long: (mid_close - hi_N) / atr  (positive when above breakout)
        # For short: (lo_N - mid_close) / atr  (positive when below breakout)
        pip = pip_size_for(pair)
        atr_price = block["atr_at_entry"].astype(np.float64) * pip  # pip → price
        long_mask = block["direction"] == "long"
        short_mask = block["direction"] == "short"
        pos = np.zeros(len(block), dtype=np.float64)
        with np.errstate(divide="ignore", invalid="ignore"):
            pos[long_mask] = (
                block.loc[long_mask, "mid_close"] - block.loc[long_mask, "break_level"]
            ).to_numpy() / atr_price[long_mask].to_numpy()
            pos[short_mask] = (
                block.loc[short_mask, "break_level"] - block.loc[short_mask, "mid_close"]
            ).to_numpy() / atr_price[short_mask].to_numpy()
        block["donchian_position"] = pos
        block["pair"] = pair
        rows.append(block)

    if not rows:
        return pd.DataFrame()
    out = pd.concat(rows, ignore_index=True)
    return out


# ---------------------------------------------------------------------------
# Walk-forward folds
# ---------------------------------------------------------------------------


def walk_forward_oos_folds(entry_ts: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    """Time-ordered 5 quintiles. Yield 4 OOS folds (k=1..4); k=0 dropped.

    Each fold: train_indices = all rows with entry_ts <= edges[k];
               test_indices  = rows in (edges[k], edges[k+1]].
    """
    if entry_ts.size < 5:
        return []
    sorted_ts = np.sort(entry_ts)
    n = sorted_ts.size
    # 6 edges: [edges[0], ..., edges[5]] dividing the data into 5 quintiles.
    # Use min(idx, n-1) to clip the right-edge to the last sample.
    edges = [sorted_ts[min(int(n * i / 5), n - 1)] for i in range(6)]
    folds: list[tuple[np.ndarray, np.ndarray]] = []
    for k in range(1, 5):
        train_mask = entry_ts <= edges[k]
        if k < 4:
            test_mask = (entry_ts > edges[k]) & (entry_ts <= edges[k + 1])
        else:
            test_mask = (entry_ts > edges[k]) & (entry_ts <= edges[5])
        folds.append((np.where(train_mask)[0], np.where(test_mask)[0]))
    return folds


def early_stopping_split(
    train_ts: np.ndarray, frac: float = EARLY_STOP_VAL_FRAC
) -> tuple[np.ndarray, np.ndarray]:
    """Time-ordered last `frac` of the train range as validation.

    Returns (fit_indices_in_train, val_indices_in_train).
    """
    if train_ts.size == 0:
        return np.array([], dtype=int), np.array([], dtype=int)
    val_cut = np.quantile(train_ts, 1.0 - frac)
    fit_mask = train_ts <= val_cut
    val_mask = train_ts > val_cut
    return np.where(fit_mask)[0], np.where(val_mask)[0]


# ---------------------------------------------------------------------------
# LightGBM training
# ---------------------------------------------------------------------------


def _categorical_columns(features: list[str]) -> list[str]:
    return [c for c in ("pair", "direction") if c in features]


def _prepare_lgbm_frame(df: pd.DataFrame, features: list[str]) -> pd.DataFrame:
    """Cast categorical columns; ensure dtype consistency for LightGBM."""
    out = df[features].copy()
    for c in _categorical_columns(features):
        out[c] = out[c].astype("category")
    return out


def train_model(
    X_fit: pd.DataFrame,  # noqa: N803  - sklearn convention
    y_fit: np.ndarray,
    X_val: pd.DataFrame,  # noqa: N803  - sklearn convention
    y_val: np.ndarray,
    features: list[str],
) -> lgb.Booster:
    cats = _categorical_columns(features)
    train_set = lgb.Dataset(X_fit, label=y_fit, categorical_feature=cats)
    val_set = lgb.Dataset(X_val, label=y_val, categorical_feature=cats, reference=train_set)
    booster = lgb.train(
        params={k: v for k, v in LGBM_PARAMS.items() if k != "n_estimators"},
        train_set=train_set,
        num_boost_round=LGBM_PARAMS["n_estimators"],
        valid_sets=[val_set],
        callbacks=[
            lgb.early_stopping(stopping_rounds=20, verbose=False),
            lgb.log_evaluation(period=0),
        ],
    )
    return booster


# ---------------------------------------------------------------------------
# Cell evaluation
# ---------------------------------------------------------------------------


@dataclass
class CellResult:
    cell_key: tuple[int, float, int, str]
    feature_set_label: str
    n_oos_trades: int = 0
    annual_trades: float = 0.0
    annual_pnl: float = 0.0
    sharpe: float = 0.0
    max_dd: float = 0.0
    dd_pct: float = 0.0
    annual_pnl_stress_02: float = 0.0
    annual_pnl_stress_05: float = 0.0
    fold_pnls: list[float] = field(default_factory=list)
    fold_ns: list[int] = field(default_factory=list)
    fold_pos: int = 0
    fold_neg: int = 0
    fold_pnl_cv: float = 0.0
    fold_concentration_top: float = 0.0
    train_sharpes: list[float] = field(default_factory=list)
    test_sharpes: list[float] = field(default_factory=list)
    train_test_gap: float = 0.0
    shuffled_sharpe: float = 0.0
    feature_importance: dict[str, float] = field(default_factory=dict)


def _per_trade_sharpe(pnl: np.ndarray) -> float:
    if pnl.size < 2:
        return 0.0
    mean = float(np.mean(pnl))
    var = float(np.var(pnl, ddof=0))
    if var <= 0:
        return 0.0
    return mean / np.sqrt(var)


def _annualize(total: float, span_years: float = EVAL_SPAN_YEARS_DEFAULT) -> float:
    return 0.0 if span_years <= 0 else total / span_years


def _max_drawdown(pnl: np.ndarray) -> float:
    if pnl.size == 0:
        return 0.0
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    return float((peak - eq).max())


def evaluate_cell(
    df: pd.DataFrame,
    n_donchian: int,
    horizon: int,
    exit_rule: str,
    conf_threshold: float,
    features: list[str],
    feature_set_label: str,
    shuffle_y: bool = False,
) -> CellResult:
    """Train walk-forward 4-fold on (n_donchian, horizon, exit_rule) and apply
    conf_threshold post-prediction.
    """
    cell_key = (n_donchian, conf_threshold, horizon, exit_rule)
    sub = df[(df["horizon_bars"] == horizon) & (df["n_donchian"] == n_donchian)]
    if sub.empty:
        return CellResult(cell_key=cell_key, feature_set_label=feature_set_label)
    sub = sub.sort_values("entry_ts").reset_index(drop=True)
    entry_ts = sub["entry_ts"].values.astype("datetime64[ns]").view("int64")
    y_full = (sub[exit_rule].to_numpy() > 0).astype(np.int8)
    pnl_full = sub[exit_rule].to_numpy(dtype=np.float64)
    rng = np.random.default_rng(0)

    folds = walk_forward_oos_folds(entry_ts)
    if not folds:
        return CellResult(cell_key=cell_key, feature_set_label=feature_set_label)

    pooled_test_pnl: list[np.ndarray] = []
    pooled_test_pred: list[np.ndarray] = []
    train_sharpes: list[float] = []
    test_sharpes: list[float] = []
    fold_test_pnls: list[float] = []
    fold_test_ns: list[int] = []
    fold_importance: dict[str, float] = {f: 0.0 for f in features if f not in ("pair", "direction")}

    for _k, (train_idx, test_idx) in enumerate(folds):
        if test_idx.size == 0 or train_idx.size < 200:
            fold_test_pnls.append(0.0)
            fold_test_ns.append(0)
            train_sharpes.append(0.0)
            test_sharpes.append(0.0)
            continue

        # In-train time-ordered early-stopping split
        train_ts_arr = entry_ts[train_idx]
        order = np.argsort(train_ts_arr)
        train_idx_sorted = train_idx[order]
        train_ts_sorted = train_ts_arr[order]
        fit_local, val_local = early_stopping_split(train_ts_sorted)
        if fit_local.size == 0 or val_local.size == 0:
            fold_test_pnls.append(0.0)
            fold_test_ns.append(0)
            train_sharpes.append(0.0)
            test_sharpes.append(0.0)
            continue
        fit_idx = train_idx_sorted[fit_local]
        val_idx = train_idx_sorted[val_local]

        y_train = y_full.copy()
        if shuffle_y:
            # Within-fold shuffle of the train labels only
            shuffled = y_train[train_idx].copy()
            rng.shuffle(shuffled)
            y_train[train_idx] = shuffled

        X_fit = _prepare_lgbm_frame(sub.iloc[fit_idx], features)  # noqa: N806  - sklearn convention
        X_val = _prepare_lgbm_frame(sub.iloc[val_idx], features)  # noqa: N806
        X_train_all = _prepare_lgbm_frame(sub.iloc[train_idx], features)  # noqa: N806
        X_test = _prepare_lgbm_frame(sub.iloc[test_idx], features)  # noqa: N806
        y_fit = y_train[fit_idx]
        y_val = y_train[val_idx]

        booster = train_model(X_fit, y_fit, X_val, y_val, features)

        # Importance accumulation (numeric features only)
        for fname, gain in zip(
            booster.feature_name(), booster.feature_importance(importance_type="gain"), strict=False
        ):
            if fname in fold_importance:
                fold_importance[fname] += float(gain)

        # Train-set predictions (filtered) — for S1 train_sharpe
        train_pred = booster.predict(X_train_all)
        train_keep = train_pred >= conf_threshold
        if train_keep.any():
            train_sharpes.append(_per_trade_sharpe(pnl_full[train_idx][train_keep]))
        else:
            train_sharpes.append(0.0)

        # Test-set predictions (filtered) — OOS Sharpe
        test_pred = booster.predict(X_test)
        test_keep = test_pred >= conf_threshold
        if test_keep.any():
            test_pnl_kept = pnl_full[test_idx][test_keep]
            test_sharpes.append(_per_trade_sharpe(test_pnl_kept))
            pooled_test_pnl.append(test_pnl_kept)
            pooled_test_pred.append(test_pred[test_keep])
            fold_test_pnls.append(float(test_pnl_kept.sum()))
            fold_test_ns.append(int(test_keep.sum()))
        else:
            test_sharpes.append(0.0)
            fold_test_pnls.append(0.0)
            fold_test_ns.append(0)

    if not pooled_test_pnl:
        return CellResult(
            cell_key=cell_key,
            feature_set_label=feature_set_label,
            fold_pnls=fold_test_pnls,
            fold_ns=fold_test_ns,
            train_sharpes=train_sharpes,
            test_sharpes=test_sharpes,
        )

    flat_pnl = np.concatenate(pooled_test_pnl)
    n_oos = flat_pnl.size
    annual_pnl = _annualize(float(flat_pnl.sum()))
    sharpe = _per_trade_sharpe(flat_pnl)
    dd = _max_drawdown(flat_pnl)
    dd_pct = (dd / abs(annual_pnl)) * 100.0 if abs(annual_pnl) > 1e-9 else float("inf")
    annual_pnl_stress_02 = _annualize(float((flat_pnl - 0.2).sum()))
    annual_pnl_stress_05 = _annualize(float((flat_pnl - 0.5).sum()))

    fold_pos = sum(1 for v in fold_test_pnls if v > 0)
    fold_neg = sum(1 for v in fold_test_pnls if v < 0)
    arr = np.asarray(fold_test_pnls)
    cv = (arr.std(ddof=0) / abs(arr.mean())) if abs(arr.mean()) > 1e-9 else float("inf")
    total_abs = float(np.abs(arr).sum())
    top = float(np.abs(arr).max() / total_abs) if total_abs > 0 else 0.0

    train_test_gap = (
        float(np.mean(np.array(train_sharpes) - np.array(test_sharpes))) if train_sharpes else 0.0
    )

    return CellResult(
        cell_key=cell_key,
        feature_set_label=feature_set_label,
        n_oos_trades=n_oos,
        annual_trades=n_oos / EVAL_SPAN_YEARS_DEFAULT,
        annual_pnl=annual_pnl,
        sharpe=sharpe,
        max_dd=dd,
        dd_pct=dd_pct,
        annual_pnl_stress_02=annual_pnl_stress_02,
        annual_pnl_stress_05=annual_pnl_stress_05,
        fold_pnls=fold_test_pnls,
        fold_ns=fold_test_ns,
        fold_pos=fold_pos,
        fold_neg=fold_neg,
        fold_pnl_cv=cv,
        fold_concentration_top=top,
        train_sharpes=train_sharpes,
        test_sharpes=test_sharpes,
        train_test_gap=train_test_gap,
        feature_importance=fold_importance,
    )


# ---------------------------------------------------------------------------
# Verdict
# ---------------------------------------------------------------------------


def classify_cell(cr: CellResult) -> tuple[str, list[str]]:
    """Eight-gate classification."""
    failed: list[str] = []
    if cr.annual_trades < ADOPT_MIN_TRADES:
        return "REJECT", [f"A0: annual_trades {cr.annual_trades:.0f} < {ADOPT_MIN_TRADES}"]
    if cr.sharpe < ADOPT_MIN_SHARPE:
        return "REJECT", [f"A1: sharpe {cr.sharpe:.4f} < {ADOPT_MIN_SHARPE}"]
    if cr.annual_pnl < ADOPT_MIN_PNL:
        return "REJECT", [f"A2: annual_pnl {cr.annual_pnl:.1f} < {ADOPT_MIN_PNL}"]
    # Hard meta-specific gates fail → REJECT
    if abs(cr.shuffled_sharpe) >= S0_HARD_GATE:
        return "REJECT", [f"S0: |shuffled_sharpe| {abs(cr.shuffled_sharpe):.4f} >= {S0_HARD_GATE}"]
    if cr.train_test_gap > S1_MAX_TRAIN_TEST_GAP:
        return "REJECT", [f"S1: train_test_gap {cr.train_test_gap:.4f} > {S1_MAX_TRAIN_TEST_GAP}"]
    # Soft gates → can land in PROMISING_BUT_NEEDS_OOS
    if cr.max_dd > ADOPT_MAX_DD:
        failed.append(f"A3: MaxDD {cr.max_dd:.1f} > {ADOPT_MAX_DD}")
    if not (cr.fold_pos >= ADOPT_MIN_FOLD_POSNEG[0] and cr.fold_neg <= ADOPT_MIN_FOLD_POSNEG[1]):
        failed.append(
            f"A4: fold pos/neg {cr.fold_pos}/{cr.fold_neg} not >= "
            f"{ADOPT_MIN_FOLD_POSNEG[0]}/{ADOPT_MIN_FOLD_POSNEG[1]}"
        )
    if cr.annual_pnl_stress_05 <= 0:
        failed.append(f"A5: stress +0.5pip annual_pnl {cr.annual_pnl_stress_05:.1f} <= 0")
    if not failed:
        return "ADOPT", []
    return "PROMISING_BUT_NEEDS_OOS", failed


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run_sweep(
    df: pd.DataFrame,
    feature_set_label: str,
    extra_features: tuple[str, ...] = (),
) -> tuple[list[CellResult], list[CellResult]]:
    """Run main sweep and shuffled-target sweep.

    Returns (real_results, shuffled_results) lists, one per cell.
    """
    features = list(MAIN_FEATURE_COLS) + list(extra_features)
    real_results: list[CellResult] = []
    shuffled_results: list[CellResult] = []
    for n in N_DONCHIAN_VALUES:
        for h in HORIZONS:
            for er in EXIT_RULES:
                for ct in CONF_THRESHOLDS:
                    real = evaluate_cell(
                        df, n, h, er, ct, features, feature_set_label, shuffle_y=False
                    )
                    shuf = evaluate_cell(
                        df, n, h, er, ct, features, feature_set_label, shuffle_y=True
                    )
                    real.shuffled_sharpe = shuf.sharpe
                    real_results.append(real)
                    shuffled_results.append(shuf)
    return real_results, shuffled_results


def write_report(
    main_results: list[CellResult],
    ablation_a_results: list[CellResult] | None,
    ablation_b_results: list[CellResult] | None,
    out_dir: Path,
    pairs_used: list[str],
    pairs_missing: list[str],
) -> Path:
    p = out_dir / "eval_report.md"
    lines: list[str] = []
    lines.append("# Stage 22.0e Meta-Labeling — Evaluation Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase22_0e_meta_labeling.md`.")
    lines.append("")
    lines.append(
        "> ⚠ **Multiple testing caveat**: 48 cells were searched on the Donchian-immediate"
    )
    lines.append(
        "> primary signal, against OOS predictions over 4 walk-forward folds. The reported"
    )
    lines.append(
        "> best cell's metrics are *in-sample search results on OOS predictions*. Production"
    )
    lines.append(
        "> migration of any ADOPT cell requires independent OOS validation (held-out future"
    )
    lines.append("> time slice, paper-run, or fresh data fetch).")
    lines.append("")
    lines.append("## Pair coverage")
    lines.append("")
    lines.append(
        f"- Active pairs: {len(pairs_used)} / 20 canonical "
        f"(missing: {', '.join(pairs_missing) if pairs_missing else 'none'})"
    )
    lines.append("")

    # Verdict on best main cell
    lines.append("## Verdict (main feature set)")
    lines.append("")
    eligible = [r for r in main_results if r.n_oos_trades >= MIN_TRADES_FOR_RANKING]
    if not eligible:
        lines.append("**NO_DATA** — no cell with sufficient trades.")
        verdict_cr = None
    else:
        eligible.sort(key=lambda r: (r.sharpe, r.annual_pnl, r.n_oos_trades), reverse=True)
        verdict_cr = eligible[0]
        verdict, failed = classify_cell(verdict_cr)
        n, ct, h, er = verdict_cr.cell_key
        lines.append(f"### **{verdict}**")
        lines.append("")
        lines.append(f"- Best cell: N={n}, conf={ct:.2f}, horizon={h}, exit={er}")
        a0_pass = verdict_cr.annual_trades >= ADOPT_MIN_TRADES
        a1_pass = verdict_cr.sharpe >= ADOPT_MIN_SHARPE
        a2_pass = verdict_cr.annual_pnl >= ADOPT_MIN_PNL
        a3_pass = verdict_cr.max_dd <= ADOPT_MAX_DD
        a4_pass = (
            verdict_cr.fold_pos >= ADOPT_MIN_FOLD_POSNEG[0]
            and verdict_cr.fold_neg <= ADOPT_MIN_FOLD_POSNEG[1]
        )
        a5_pass = verdict_cr.annual_pnl_stress_05 > 0
        s0_pass = abs(verdict_cr.shuffled_sharpe) < S0_HARD_GATE
        s0_diag_pass = abs(verdict_cr.shuffled_sharpe) < S0_DIAGNOSTIC
        s1_pass = verdict_cr.train_test_gap <= S1_MAX_TRAIN_TEST_GAP
        v = verdict_cr  # alias for shorter f-strings below
        lines.append(
            f"- A0 annual_trades={v.annual_trades:.0f} >= {ADOPT_MIN_TRADES}: "
            f"**{'PASS' if a0_pass else 'FAIL'}**"
        )
        lines.append(
            f"- A1 sharpe={v.sharpe:.4f} >= {ADOPT_MIN_SHARPE}: "
            f"**{'PASS' if a1_pass else 'FAIL'}**"
        )
        lines.append(
            f"- A2 annual_pnl={v.annual_pnl:.1f} >= {ADOPT_MIN_PNL}: "
            f"**{'PASS' if a2_pass else 'FAIL'}**"
        )
        lines.append(
            f"- A3 MaxDD={v.max_dd:.1f} <= {ADOPT_MAX_DD}: "
            f"**{'PASS' if a3_pass else 'FAIL'}**"
        )
        lines.append(
            f"- A4 OOS fold pos/neg={v.fold_pos}/{v.fold_neg} >= "
            f"{ADOPT_MIN_FOLD_POSNEG[0]}/{ADOPT_MIN_FOLD_POSNEG[1]}: "
            f"**{'PASS' if a4_pass else 'FAIL'}**"
        )
        lines.append(
            f"- A5 stress +0.5pip annual_pnl={v.annual_pnl_stress_05:.1f} > 0: "
            f"**{'PASS' if a5_pass else 'FAIL'}**"
        )
        lines.append(
            f"- S0 hard gate |shuffled_sharpe|={abs(v.shuffled_sharpe):.4f} < "
            f"{S0_HARD_GATE}: **{'PASS' if s0_pass else 'FAIL'}** "
            f"(diagnostic <{S0_DIAGNOSTIC}: "
            f"{'pass' if s0_diag_pass else 'fail'})"
        )
        lines.append(
            f"- S1 train_test_gap={v.train_test_gap:.4f} <= {S1_MAX_TRAIN_TEST_GAP}: "
            f"**{'PASS' if s1_pass else 'FAIL'}**"
        )
        if failed:
            lines.append("")
            lines.append("**Gates that failed**:")
            for f in failed:
                lines.append(f"- {f}")
        if v.annual_trades > OVERTRADE_WARN_TRADES:
            lines.append("")
            lines.append(
                f"⚠ Overtrading warning: annual_trades = "
                f"{v.annual_trades:.0f} > {OVERTRADE_WARN_TRADES}."
            )
        lines.append("")

    # Top-10 cells (main)
    lines.append("## Top-10 cells (main feature set, by Sharpe)")
    lines.append("")
    lines.append(
        "| rank | N | conf | h | exit | n/yr | PnL/yr | Sharpe | MaxDD | DD%PnL"
        " | fold ± | +0.5 stress | shuffled | gap |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, r in enumerate(eligible[:10], 1):
        n, ct, h, er = r.cell_key
        lines.append(
            f"| {i} | {n} | {ct:.2f} | {h} | {er} | {r.annual_trades:.0f} | "
            f"{r.annual_pnl:.1f} | {r.sharpe:.4f} | {r.max_dd:.1f} | {r.dd_pct:.1f}% | "
            f"{r.fold_pos}/{r.fold_neg} | {r.annual_pnl_stress_05:.1f} | "
            f"{r.shuffled_sharpe:.4f} | {r.train_test_gap:.4f} |"
        )
    lines.append("")

    # Per-fold table for top-10
    if eligible:
        lines.append("## Top-10 OOS per-fold PnL")
        lines.append("")
        lines.append("| rank | f1 | f2 | f3 | f4 | CV | top conc |")
        lines.append("|---|---|---|---|---|---|---|")
        for i, r in enumerate(eligible[:10], 1):
            fps = r.fold_pnls + [0.0] * (4 - len(r.fold_pnls))
            lines.append(
                f"| {i} | {fps[0]:.1f} | {fps[1]:.1f} | {fps[2]:.1f} | {fps[3]:.1f} | "
                f"{r.fold_pnl_cv:.2f} | {r.fold_concentration_top:.1%} |"
            )
        lines.append("")

    # Train-test parity
    lines.append("## Train-test parity (S1) for top-10")
    lines.append("")
    lines.append("| rank | train_sharpe (per fold) | test_sharpe (per fold) | gap |")
    lines.append("|---|---|---|---|")
    for i, r in enumerate(eligible[:10], 1):
        ts = " / ".join(f"{x:.3f}" for x in r.train_sharpes) or "—"
        es = " / ".join(f"{x:.3f}" for x in r.test_sharpes) or "—"
        lines.append(f"| {i} | {ts} | {es} | {r.train_test_gap:.4f} |")
    lines.append("")

    # Feature importance for top-10
    lines.append("## Feature importance (LightGBM gain, summed across folds) — top-10 cells")
    lines.append("")
    for i, r in enumerate(eligible[:10], 1):
        n, ct, h, er = r.cell_key
        lines.append(f"### Rank {i}: N={n}, conf={ct:.2f}, h={h}, exit={er}")
        lines.append("")
        if not r.feature_importance:
            lines.append("(no importance recorded)")
            lines.append("")
            continue
        items = sorted(r.feature_importance.items(), key=lambda kv: kv[1], reverse=True)
        lines.append("| feature | gain |")
        lines.append("|---|---|")
        for feat, gain in items:
            lines.append(f"| {feat} | {gain:.0f} |")
        lines.append("")

    # Ablation diagnostics
    lines.append("## Ablation-A diagnostic (main + hour_utc) — DIAGNOSTIC ONLY, NOT verdict")
    lines.append("")
    if ablation_a_results:
        a_eligible = [r for r in ablation_a_results if r.n_oos_trades >= MIN_TRADES_FOR_RANKING]
        a_eligible.sort(key=lambda r: r.sharpe, reverse=True)
        if a_eligible:
            best_a = a_eligible[0]
            best_main_sharpe = eligible[0].sharpe if eligible else 0.0
            lift = best_a.sharpe - best_main_sharpe
            lines.append(
                f"- Best Ablation-A cell Sharpe: {best_a.sharpe:.4f} "
                f"(main best: {best_main_sharpe:.4f})"
            )
            lines.append(f"- Δ Sharpe lift = {lift:+.4f}")
            if lift >= ABLATION_LIFT_THRESHOLD:
                lines.append(f"- Lift ≥ {ABLATION_LIFT_THRESHOLD} — flagged for Ablation-B")
            else:
                lines.append(f"- Lift < {ABLATION_LIFT_THRESHOLD} — Ablation-B NOT triggered")
        else:
            lines.append("(no eligible Ablation-A cell)")
    else:
        lines.append("(Ablation-A not run)")
    lines.append("")

    lines.append("## Ablation-B diagnostic (main + hour_utc + dow) — DIAGNOSTIC ONLY")
    lines.append("")
    if ablation_b_results:
        b_eligible = [r for r in ablation_b_results if r.n_oos_trades >= MIN_TRADES_FOR_RANKING]
        b_eligible.sort(key=lambda r: r.sharpe, reverse=True)
        if b_eligible:
            best_b = b_eligible[0]
            lines.append(f"- Best Ablation-B cell Sharpe: {best_b.sharpe:.4f}")
        else:
            lines.append("(no eligible Ablation-B cell)")
    else:
        lines.append("(Ablation-B not triggered — Ablation-A lift below threshold or not run)")
    lines.append("")

    # NG list compliance
    lines.append("## NG list compliance (postmortem §4)")
    lines.append("")
    lines.append("- NG#1 pair filter: 20-pair universe, no cell-level pair drop ✓")
    lines.append("- NG#2 train-side time-of-day filter: not applied; Donchian uses all bars ✓")
    lines.append("- NG#3 test-side filter improvement claim: verdict on OOS predictions only ✓")
    lines.append(
        "- NG#4 WeekOpen-aware sample weighting: none; is_week_open_window excluded entirely ✓"
    )
    lines.append("- NG#5 universe-restricted cross-pair feature: none ✓")
    lines.append("")

    # Audit-mandated feature constraints
    lines.append("## Feature allowlist compliance (audit PR #258)")
    lines.append("")
    lines.append(f"- MAIN_FEATURE_COLS = {list(MAIN_FEATURE_COLS)}")
    iwow_in = "is_week_open_window" in MAIN_FEATURE_COLS
    lines.append(
        f"- is_week_open_window in MAIN: {iwow_in}  (must be False)"
    )
    lines.append(f"- hour_utc in MAIN: {('hour_utc' in MAIN_FEATURE_COLS)}  (must be False)")
    lines.append(f"- dow in MAIN: {('dow' in MAIN_FEATURE_COLS)}  (must be False)")
    forbidden_in_main = set(MAIN_FEATURE_COLS) & FORBIDDEN_FEATURES
    lines.append(f"- forbidden ∩ main: {sorted(forbidden_in_main)} (must be empty)")
    lines.append("")

    p.write_text("\n".join(lines), encoding="utf-8")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_CANONICAL_20)
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument(
        "--smoke", action="store_true", help="Smoke run on USD_JPY, EUR_USD, GBP_JPY only."
    )
    parser.add_argument(
        "--skip-ablation", action="store_true", help="Skip Ablation-A (and B). Headline only."
    )
    args = parser.parse_args(argv)

    pairs = ["USD_JPY", "EUR_USD", "GBP_JPY"] if args.smoke else args.pairs
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 22.0e Meta-Labeling ({len(pairs)} pairs) ===")
    pairs_used: list[str] = []
    pairs_missing: list[str] = []
    per_pair_dfs: list[pd.DataFrame] = []
    for i, pair in enumerate(pairs, 1):
        for n in N_DONCHIAN_VALUES:
            t0 = time.time()
            try:
                df = build_signal_dataset(pair, n, days=args.days)
            except FileNotFoundError as exc:
                if pair not in pairs_missing:
                    pairs_missing.append(pair)
                print(f"[{i:2d}/{len(pairs)}] {pair} N={n}: SKIP ({exc})")
                continue
            if df.empty:
                continue
            df["n_donchian"] = n
            per_pair_dfs.append(df)
            elapsed = time.time() - t0
            print(f"[{i:2d}/{len(pairs)}] {pair} N={n}: {len(df):>7} signals ({elapsed:5.1f}s)")
        if pair not in pairs_missing and pair not in pairs_used:
            pairs_used.append(pair)

    if not per_pair_dfs:
        print("ERROR: no signal data produced")
        return 1
    full_df = pd.concat(per_pair_dfs, ignore_index=True)
    full_df = full_df.sort_values("entry_ts").reset_index(drop=True)
    print(f"Total signals: {len(full_df):,}")

    print("\n[main] running 48-cell sweep + shuffled-target sanity ...")
    t0 = time.time()
    main_real, _ = run_sweep(full_df, "main")
    print(f"     done ({time.time() - t0:5.1f}s)")

    ablation_a: list[CellResult] | None = None
    ablation_b: list[CellResult] | None = None
    if not args.skip_ablation:
        print("\n[ablation A] main + hour_utc ...")
        t0 = time.time()
        ablation_a, _ = run_sweep(full_df, "ablation_a", extra_features=ABLATION_A_EXTRA)
        print(f"     done ({time.time() - t0:5.1f}s)")
        # Conditional Ablation-B
        a_eligible = [r for r in ablation_a if r.n_oos_trades >= MIN_TRADES_FOR_RANKING]
        m_eligible = [r for r in main_real if r.n_oos_trades >= MIN_TRADES_FOR_RANKING]
        if a_eligible and m_eligible:
            a_eligible.sort(key=lambda r: r.sharpe, reverse=True)
            m_eligible.sort(key=lambda r: r.sharpe, reverse=True)
            lift = a_eligible[0].sharpe - m_eligible[0].sharpe
            if lift >= ABLATION_LIFT_THRESHOLD:
                print(
                    f"\n[ablation B] triggered (Ablation-A lift "
                    f"{lift:+.4f}); main + hour_utc + dow ..."
                )
                t0 = time.time()
                ablation_b, _ = run_sweep(full_df, "ablation_b", extra_features=ABLATION_B_EXTRA)
                print(f"     done ({time.time() - t0:5.1f}s)")

    # Save sweep_results
    sweep_rows = []
    for r in main_real:
        n, ct, h, er = r.cell_key
        sweep_rows.append(
            {
                "feature_set": r.feature_set_label,
                "N": n,
                "conf_threshold": ct,
                "horizon_bars": h,
                "exit_rule": er,
                "n_oos_trades": r.n_oos_trades,
                "annual_trades": r.annual_trades,
                "annual_pnl": r.annual_pnl,
                "sharpe": r.sharpe,
                "max_dd": r.max_dd,
                "dd_pct": r.dd_pct,
                "annual_pnl_stress_+0.2": r.annual_pnl_stress_02,
                "annual_pnl_stress_+0.5": r.annual_pnl_stress_05,
                "fold_pos": r.fold_pos,
                "fold_neg": r.fold_neg,
                "fold_pnl_cv": r.fold_pnl_cv,
                "fold_concentration_top": r.fold_concentration_top,
                "shuffled_sharpe": r.shuffled_sharpe,
                "train_test_gap": r.train_test_gap,
            }
        )
    sweep_df = pd.DataFrame(sweep_rows)
    sweep_path = args.out_dir / "sweep_results.parquet"
    sweep_df.to_parquet(sweep_path, compression="snappy")
    print(f"\nSweep results: {sweep_path}")

    report_path = write_report(
        main_real, ablation_a, ablation_b, args.out_dir, pairs_used, pairs_missing
    )
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
