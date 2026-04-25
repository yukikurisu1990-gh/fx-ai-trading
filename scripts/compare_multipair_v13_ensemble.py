"""compare_multipair_v13_ensemble.py - Phase 9.17 multi-strategy ensemble.

Successor to v9 / v12. Identical load + features + cross-pair + train
pipeline; the difference is at SELECTOR time — eval-time
**(pair x strategy)** picker.

Phase 9.17 strategies (eval-time, no model retraining):
  - lgbm:     LightGBM 3-class TB classifier (Phase 9.6 baseline)
  - mr:       MeanReversionStrategy (combined RSI+Bollinger AND).
              long: rsi_14 <= 30 AND bb_pct_b <= 0.10
              short: rsi_14 >= 70 AND bb_pct_b >= 0.90
  - bo:       BreakoutStrategy (Bollinger break + EMA trend).
              long: last_close > bb_upper AND ema_12 > ema_26
              short: last_close < bb_lower AND ema_12 < ema_26

Each strategy emits per-bar (signal, confidence). PnL is computed using
the same triple-barrier mid-bucket label (TP=1.5 / SL=1.0 x ATR) for
ALL strategies — design memo §13 default 4 (apples-to-apples PnL).

SELECTOR per bar = argmax(confidence) over active (pair, strategy)
candidates. Strategies that emit no_trade for a bar drop out of the
candidate pool.

Cells (internal sweep, default = all 4):
  - lgbm_only    : only LightGBM signals participate (= v9 baseline)
  - lgbm+mr      : LightGBM + MeanReversion
  - lgbm+bo      : LightGBM + Breakout
  - lgbm+mr+bo   : all three (full ensemble)

Inter-strategy correlation matrix is printed in the summary, computed
from per-bar PnL series (NaN where the strategy did not trade).

CLI
---
    --ensemble-cells LIST   # comma-separated cells for internal sweep
                            # default: 'lgbm_only,lgbm+mr,lgbm+bo,lgbm+mr+bo'

Phase 9.17 verdict gates (PnL-priority + correlation gate):
  GO          - PnL >= 1.10 x baseline AND rho <= 0.4 AND Sharpe >= baseline
                AND DD%PnL <= 5%
  PARTIAL GO  - PnL >= 1.05 x baseline AND Sharpe >= baseline (rho 0.4-0.6)
  STRETCH GO  - any cell Sharpe >= 0.18 (unblocks Phase 9.11)
  NO ADOPT    - PnL < baseline OR DD%PnL > 5% OR rho > 0.6

Baseline = Phase 9.16 production default (20-pair v9 spread bundle,
SELECTOR Sharpe 0.160, PnL 8,157 pip, DD%PnL 2.5%). The lgbm_only cell
must reproduce this exactly.

Requires data/candles_<pair>_M1_365d_BA.jsonl (same as v9).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
LABEL_COLUMN = "label_tb"
_LABEL_ENCODE = {-1: 0, 0: 1, 1: 2}

# Phase 9.16 production default: 20-pair universe.
DEFAULT_PAIRS = [
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
DEFAULT_PARAMS = {
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_child_samples": 50,
    "reg_alpha": 0.1,
    "reg_lambda": 0.1,
    "random_state": 42,
    "n_jobs": 1,
}

# Phase 9.17: per-strategy identifiers.
_STRATEGY_LGBM = "lgbm"
_STRATEGY_MR = "mr"
_STRATEGY_BO = "bo"
_ALL_STRATEGIES = (_STRATEGY_LGBM, _STRATEGY_MR, _STRATEGY_BO)

# Cell -> set of strategies enabled in that cell.
_CELL_LGBM_ONLY = "lgbm_only"
_CELL_LGBM_MR = "lgbm+mr"
_CELL_LGBM_BO = "lgbm+bo"
_CELL_LGBM_MR_BO = "lgbm+mr+bo"
_CELL_STRATEGY_SETS: dict[str, frozenset[str]] = {
    _CELL_LGBM_ONLY: frozenset({_STRATEGY_LGBM}),
    _CELL_LGBM_MR: frozenset({_STRATEGY_LGBM, _STRATEGY_MR}),
    _CELL_LGBM_BO: frozenset({_STRATEGY_LGBM, _STRATEGY_BO}),
    _CELL_LGBM_MR_BO: frozenset({_STRATEGY_LGBM, _STRATEGY_MR, _STRATEGY_BO}),
}
_DEFAULT_CELLS = (_CELL_LGBM_ONLY, _CELL_LGBM_MR, _CELL_LGBM_BO, _CELL_LGBM_MR_BO)

# Phase 9.17 G-1 MeanReversionStrategy thresholds (combined-AND).
_MR_RSI_OVERSOLD = 30.0
_MR_RSI_OVERBOUGHT = 70.0
_MR_BB_LOWER = 0.10
_MR_BB_UPPER = 0.90

# Phase 9.17 G-2 BreakoutStrategy: ATR multiples beyond band that
# saturate confidence to 1.0.
_BO_STRENGTH_FULL_ATR = 0.5


def _pip_size(instrument: str) -> float:
    return 0.01 if instrument.endswith("_JPY") else 0.0001


# ---------------------------------------------------------------------------
# Data loading (identical to v3)
# ---------------------------------------------------------------------------


def _parse_oanda_ts(s: str) -> datetime:
    s2 = s.replace("Z", "+00:00")
    if "." in s2:
        head, rest = s2.split(".", 1)
        tz_idx = max(rest.find("+"), rest.find("-"))
        s2 = head + "." + rest[:tz_idx][:6].ljust(6, "0") + rest[tz_idx:]
    return datetime.fromisoformat(s2)


def _load_mid(path: Path) -> pd.DataFrame:
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            raw = json.loads(line)
            rows.append(
                {
                    "timestamp": _parse_oanda_ts(raw["time"]),
                    "open": float(raw["o"]),
                    "high": float(raw["h"]),
                    "low": float(raw["l"]),
                    "close": float(raw["c"]),
                    "volume": int(raw.get("volume", 0)),
                }
            )
    df = pd.DataFrame(rows).set_index("timestamp")
    df.index = pd.DatetimeIndex(df.index, tz=UTC)
    return df


def _load_ba(path: Path) -> pd.DataFrame:
    """Load BA-mode JSONL keeping the full bid/ask OHLC for label computation.

    Mid OHLC is synthesized as (bid + ask) / 2 for feature computation;
    the bid_o/h/l/c and ask_o/h/l/c columns are retained so v5's bid/ask-
    aware label function can fire long TP from bid_h, short TP from ask_l,
    etc.
    """
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            raw = json.loads(line)
            bid_o = float(raw["bid_o"])
            bid_h = float(raw["bid_h"])
            bid_l = float(raw["bid_l"])
            bid_c = float(raw["bid_c"])
            ask_o = float(raw["ask_o"])
            ask_h = float(raw["ask_h"])
            ask_l = float(raw["ask_l"])
            ask_c = float(raw["ask_c"])
            rows.append(
                {
                    "timestamp": _parse_oanda_ts(raw["time"]),
                    "open": (bid_o + ask_o) / 2.0,
                    "high": (bid_h + ask_h) / 2.0,
                    "low": (bid_l + ask_l) / 2.0,
                    "close": (bid_c + ask_c) / 2.0,
                    "bid_o": bid_o,
                    "bid_h": bid_h,
                    "bid_l": bid_l,
                    "bid_c": bid_c,
                    "ask_o": ask_o,
                    "ask_h": ask_h,
                    "ask_l": ask_l,
                    "ask_c": ask_c,
                    "volume": int(raw.get("volume", 0)),
                }
            )
    df = pd.DataFrame(rows).set_index("timestamp")
    df.index = pd.DatetimeIndex(df.index, tz=UTC)
    return df


def _pick_file(pair: str) -> tuple[Path, str]:
    ba_path = DATA_DIR / f"candles_{pair}_M1_365d_BA.jsonl"
    m_path = DATA_DIR / f"candles_{pair}_M1_365d.jsonl"
    if ba_path.exists():
        return ba_path, "BA"
    if m_path.exists():
        return m_path, "M"
    raise FileNotFoundError(f"no candle file for {pair} under {DATA_DIR}")


# ---------------------------------------------------------------------------
# Features (identical to v3 — required for apples-to-apples)
# ---------------------------------------------------------------------------


def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False).mean()


def _rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, float("nan"))
    return 100 - (100 / (1 + rs))


def _add_m1_features(df: pd.DataFrame) -> pd.DataFrame:
    c, h, lo = df["close"], df["high"], df["low"]
    ema12 = _ema(c, 12)
    ema26 = _ema(c, 26)
    macd_line = ema12 - ema26
    macd_sig = _ema(macd_line, 9)
    sma20 = c.rolling(20).mean()
    sma50 = c.rolling(50).mean()
    rsi14 = _rsi(c, 14)
    bb_std = c.rolling(20).std(ddof=0)
    bb_up = sma20 + 2 * bb_std
    bb_lo = sma20 - 2 * bb_std
    bb_wi = bb_up - bb_lo
    bb_pb = (c - bb_lo) / bb_wi.replace(0, float("nan"))
    pc = c.shift(1)
    tr = pd.concat([h - lo, (h - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1)
    df = df.copy()
    df["ema_12"] = ema12
    df["ema_26"] = ema26
    df["macd_line"] = macd_line
    df["macd_signal"] = macd_sig
    df["macd_histogram"] = macd_line - macd_sig
    df["sma_20"] = sma20
    df["sma_50"] = sma50
    df["rsi_14"] = rsi14
    df["bb_middle"] = sma20
    df["bb_upper"] = bb_up
    df["bb_lower"] = bb_lo
    df["bb_width"] = bb_wi
    df["bb_pct_b"] = bb_pb
    df["atr_14"] = tr.rolling(14).mean()
    df["last_close"] = c
    return df


def _add_upper_tf(df_m1: pd.DataFrame, rule: str, prefix: str) -> pd.DataFrame:
    idx = df_m1.index
    ohlc = (
        df_m1[["open", "high", "low", "close"]]
        .resample(rule)
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna(how="all")
    )
    c = ohlc["close"]
    ret1 = c.pct_change(1)
    ret3 = c.pct_change(3)
    vol = ret1.rolling(5, min_periods=2).std(ddof=0)
    rsi14 = _rsi(c, 14)
    sma5 = c.rolling(5).mean()
    sma5_slope = sma5.diff(1) / sma5.shift(1)
    bb_std = c.rolling(20).std(ddof=0)
    bb_mid = c.rolling(20).mean()
    bb_lo = bb_mid - 2 * bb_std
    bb_wi = (4 * bb_std).replace(0, float("nan"))
    bb_pct = (c - bb_lo) / bb_wi
    trend_slope = c.pct_change(5)
    trend_dir = np.sign(c.diff(3))
    raw = pd.DataFrame(
        {
            f"{prefix}_return_1": ret1,
            f"{prefix}_return_3": ret3,
            f"{prefix}_volatility": vol,
            f"{prefix}_rsi_14": rsi14,
            f"{prefix}_ma_slope": sma5_slope,
            f"{prefix}_bb_pct_b": bb_pct,
            f"{prefix}_trend_slope": trend_slope,
            f"{prefix}_trend_dir": trend_dir,
        },
        index=ohlc.index,
    )
    aligned = raw.shift(1).reindex(idx, method="ffill")
    result = df_m1.copy()
    for col in aligned.columns:
        result[col] = aligned[col].values
    return result


# ---------------------------------------------------------------------------
# B-2: bid/ask-aware triple-barrier labelling (the actual change vs v4)
# ---------------------------------------------------------------------------


def _first_hit_idx(mask: np.ndarray) -> int:
    """Return the smallest index where mask is True, or -1 if none."""
    if not mask.any():
        return -1
    return int(np.argmax(mask))


def _add_labels_bidask(
    df: pd.DataFrame, horizon: int, tp_mult: float, sl_mult: float
) -> pd.DataFrame:
    """Bid/ask-aware ATR triple-barrier label (Phase 9.12/B-2).

    Computes both directions:

      Long: entry at next bar's ask_o; TP fires when bid_h reaches
            entry + tp_mult*ATR within horizon; SL when bid_l reaches
            entry - sl_mult*ATR.
      Short: entry at next bar's bid_o; TP when ask_l reaches
             entry - tp_mult*ATR; SL when ask_h reaches
             entry + sl_mult*ATR.

    Per-bar label semantics (compatible with v3/v4's encoding):
      +1 = long TP fires before long SL AND (short TP doesn't beat it)
      -1 = short TP fires before short SL AND (long TP doesn't beat it)
       0 = neither direction's TP fires before its SL within horizon
           (or no labelable bar)

    Bars without ATR(14), without ask_o/bid_o at i+1, or with i+horizon
    out of range get label=None.

    Writes the result to the column named by LABEL_COLUMN ("label_tb")
    so downstream code (folds, train, eval) sees the same shape as v9.
    """
    if "bid_o" not in df.columns or "ask_o" not in df.columns:
        raise ValueError(
            "v5 bid/ask labels require BA mode candles "
            "(bid_o/h/l/c and ask_o/h/l/c columns). "
            "Run fetch_oanda_candles --price BA to produce them."
        )

    n = len(df)
    bid_h = df["bid_h"].to_numpy(dtype=np.float64)
    bid_l = df["bid_l"].to_numpy(dtype=np.float64)
    ask_h = df["ask_h"].to_numpy(dtype=np.float64)
    ask_l = df["ask_l"].to_numpy(dtype=np.float64)
    ask_o = df["ask_o"].to_numpy(dtype=np.float64)
    bid_o = df["bid_o"].to_numpy(dtype=np.float64)
    atrs = df["atr_14"].to_numpy(dtype=np.float64)

    labels: list[int | None] = [None] * n
    for i in range(n - horizon - 1):
        atr_i = atrs[i]
        if not np.isfinite(atr_i) or atr_i <= 0:
            continue
        entry_long = ask_o[i + 1]
        entry_short = bid_o[i + 1]
        if not (np.isfinite(entry_long) and np.isfinite(entry_short)):
            continue
        tp = tp_mult * atr_i
        sl = sl_mult * atr_i

        # Window covers bars i+1 .. i+horizon (length = horizon)
        long_bh = bid_h[i + 1 : i + 1 + horizon]
        long_bl = bid_l[i + 1 : i + 1 + horizon]
        short_al = ask_l[i + 1 : i + 1 + horizon]
        short_ah = ask_h[i + 1 : i + 1 + horizon]

        long_tp_idx = _first_hit_idx(long_bh >= entry_long + tp)
        long_sl_idx = _first_hit_idx(long_bl <= entry_long - sl)
        short_tp_idx = _first_hit_idx(short_al <= entry_short - tp)
        short_sl_idx = _first_hit_idx(short_ah >= entry_short + sl)

        # Did each direction's TP fire before its own SL?
        long_clears = long_tp_idx >= 0 and (long_sl_idx < 0 or long_tp_idx < long_sl_idx)
        short_clears = short_tp_idx >= 0 and (short_sl_idx < 0 or short_tp_idx < short_sl_idx)

        if long_clears and not short_clears:
            labels[i] = 1
        elif short_clears and not long_clears:
            labels[i] = -1
        elif long_clears and short_clears:
            # Both directions cleared TP — pick the earlier
            labels[i] = 1 if long_tp_idx <= short_tp_idx else -1
        else:
            labels[i] = 0
    df = df.copy()
    df[LABEL_COLUMN] = labels
    return df


def _add_labels_atr(df: pd.DataFrame, horizon: int, tp_mult: float, sl_mult: float) -> pd.DataFrame:
    """Triple-barrier labels with TP/SL scaled by ATR(14) at entry bar.

    Returns label in {-1, 0, 1} = {SL hit first, timeout, TP hit first}.
    Bars whose ATR is NaN or non-positive get label=None and are dropped
    from the train set (consistent with v2/v3's NA handling).
    """
    closes = df["close"].to_numpy(dtype=np.float64)
    atrs = df["atr_14"].to_numpy(dtype=np.float64)
    n = len(closes)
    labels: list[int | None] = [None] * n
    for i in range(n - horizon):
        atr_i = atrs[i]
        if not np.isfinite(atr_i) or atr_i <= 0:
            continue
        tp = tp_mult * atr_i
        sl = sl_mult * atr_i
        window = closes[i + 1 : i + horizon + 1]
        tp_m = window >= closes[i] + tp
        sl_m = window <= closes[i] - sl
        if not tp_m.any() and not sl_m.any():
            labels[i] = 0
        elif tp_m.any() and not sl_m.any():
            labels[i] = 1
        elif sl_m.any() and not tp_m.any():
            labels[i] = -1
        else:
            labels[i] = 1 if int(np.argmax(tp_m)) < int(np.argmax(sl_m)) else -1
    df = df.copy()
    df[LABEL_COLUMN] = labels
    return df


# Phase 9.15/F-1: orthogonal feature columns by group, used both for
# computation toggling and for feature_cols subset selection in main().
_ORTHO_COLS_SPREAD: tuple[str, ...] = (
    "spread_now_pip",
    "spread_ma_ratio_20",
    "spread_zscore_50",
)
_ORTHO_COLS_TIME: tuple[str, ...] = (
    "hour_sin",
    "hour_cos",
    "is_asian",
    "is_london",
    "is_overlap",
    "day_of_week_sin",
)
_ORTHO_COLS_VOLUME: tuple[str, ...] = (
    "volume_pct_100",
    "volume_zscore_50",
)
_ORTHO_COLS_REGIME: tuple[str, ...] = (
    "regime_trend",
    "regime_range",
    "regime_high_vol",
)
_ORTHO_COLS_ALL: tuple[str, ...] = (
    _ORTHO_COLS_SPREAD + _ORTHO_COLS_TIME + _ORTHO_COLS_VOLUME + _ORTHO_COLS_REGIME
)


def _add_orthogonal_features(df: pd.DataFrame, instrument: str) -> pd.DataFrame:
    """Phase 9.15/F-1: 12 orthogonal features (vectorised).

    Adds all 12 columns regardless of bundle — the bundle flag in main()
    selects which to *expose* as model inputs at fold-eval time. Adding
    everything here keeps the feature DataFrame schema stable across
    ablation cells.
    """
    pip = _pip_size(instrument)
    df = df.copy()

    if "ask_o" in df.columns and "bid_o" in df.columns:
        spread = (df["ask_o"] - df["bid_o"]) / pip
    else:
        # Mid-only fallback: spread feature is identically NaN.
        spread = pd.Series(np.nan, index=df.index)

    # Group 1: spread (3)
    df["spread_now_pip"] = spread
    spread_ma_20 = spread.rolling(20, min_periods=5).mean()
    df["spread_ma_ratio_20"] = spread / spread_ma_20.replace(0, np.nan)
    spread_mean_50 = spread.rolling(50, min_periods=10).mean()
    spread_std_50 = spread.rolling(50, min_periods=10).std(ddof=0)
    df["spread_zscore_50"] = (spread - spread_mean_50) / spread_std_50.replace(0, np.nan)

    # Group 2: time-of-day (6) — index is tz-aware UTC at this point.
    idx = df.index
    if isinstance(idx, pd.DatetimeIndex):
        hour = idx.hour
        dow = idx.dayofweek
    else:
        hour = pd.DatetimeIndex(idx).hour
        dow = pd.DatetimeIndex(idx).dayofweek
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    df["is_asian"] = ((hour >= 0) & (hour < 7)).astype(np.int8)
    df["is_london"] = ((hour >= 7) & (hour < 12)).astype(np.int8)
    df["is_overlap"] = ((hour >= 12) & (hour < 16)).astype(np.int8)
    df["day_of_week_sin"] = np.sin(2 * np.pi * dow / 7)

    # Group 3: volume (2)
    vol = df["volume"].astype(np.float64)
    df["volume_pct_100"] = vol.rolling(100, min_periods=20).rank(pct=True)
    vol_mean_50 = vol.rolling(50, min_periods=10).mean()
    vol_std_50 = vol.rolling(50, min_periods=10).std(ddof=0)
    df["volume_zscore_50"] = (vol - vol_mean_50) / vol_std_50.replace(0, np.nan)

    # Group 4: regime (3 one-hot)
    atr = df["atr_14"]
    atr_pct = atr.rolling(200, min_periods=50).rank(pct=True)
    df["regime_trend"] = (atr_pct < 0.4).astype(np.int8)
    df["regime_range"] = ((atr_pct >= 0.4) & (atr_pct < 0.7)).astype(np.int8)
    df["regime_high_vol"] = (atr_pct >= 0.7).astype(np.int8)

    return df


def _build_pair_features(
    df_m1: pd.DataFrame, horizon: int, tp_mult: float, sl_mult: float, instrument: str
) -> pd.DataFrame:
    df = _add_m1_features(df_m1)
    df = _add_upper_tf(df, "5min", "m5")
    df = _add_upper_tf(df, "15min", "m15")
    df = _add_upper_tf(df, "1h", "h1")
    # Phase 9.15/F-1: orthogonal features (added BEFORE labels so the
    # feature columns reference current-bar OHLC, not future bars).
    df = _add_orthogonal_features(df, instrument)
    # Phase 9.17: single bid/ask-aware label at the global mid bucket
    # (1.5 / 1.0 ATR). Used for both training AND eval-time PnL
    # computation across all strategies (apples-to-apples PnL — design
    # memo §13 default 4).
    df = _add_labels_bidask(df, horizon, tp_mult, sl_mult)
    df = df.iloc[50:].copy()
    df = df.reset_index()
    return df


def _build_cross_pair_features(
    feat_dfs: dict[str, pd.DataFrame],
    ref_pair: str = "EUR_USD",
    corr_window: int = 20,
) -> dict[str, pd.DataFrame]:
    ref_ts_series = feat_dfs[ref_pair].set_index("timestamp")
    ret_map: dict[str, pd.Series] = {}
    rsi_map: dict[str, pd.Series] = {}
    for pair, df in feat_dfs.items():
        aligned = df.set_index("timestamp").reindex(ref_ts_series.index, method="ffill")
        ret_map[pair] = aligned["last_close"].pct_change(1)
        rsi_map[pair] = aligned["rsi_14"]
    ret_df = pd.DataFrame(ret_map)
    rsi_df = pd.DataFrame(rsi_map)
    basket_ret = ret_df.mean(axis=1)
    result: dict[str, pd.DataFrame] = {}
    for pair, df in feat_dfs.items():
        ret_rank = ret_df.rank(axis=1, pct=True, na_option="keep")[pair]
        rsi_rank = rsi_df.rank(axis=1, pct=True, na_option="keep")[pair]
        basket_corr = ret_df[pair].rolling(corr_window, min_periods=5).corr(basket_ret)
        xp = pd.DataFrame(
            {
                "xp_ret_rank": ret_rank,
                "xp_rsi_rank": rsi_rank,
                "xp_basket_corr": basket_corr,
            },
            index=ref_ts_series.index,
        )
        xp_shifted = xp.shift(1)
        df_ts = df.set_index("timestamp")
        merged = df_ts.join(xp_shifted, how="left")
        result[pair] = merged.reset_index()
    return result


# ---------------------------------------------------------------------------
# Folds / training (same as v3)
# ---------------------------------------------------------------------------


def _generate_folds(
    ts_series: pd.Series,
    train_days: int = 90,
    test_days: int = 7,
    step_days: int = 7,
    min_train_bars: int = 5000,
    min_test_bars: int = 100,
) -> list[dict]:
    t_min = ts_series.min()
    t_max = ts_series.max()
    folds: list[dict] = []
    test_start = t_min + pd.Timedelta(days=train_days)
    fold_id = 0
    while True:
        test_end = test_start + pd.Timedelta(days=test_days)
        if test_end > t_max:
            break
        train_start = test_start - pd.Timedelta(days=train_days)
        tr_mask = (ts_series >= train_start) & (ts_series < test_start)
        te_mask = (ts_series >= test_start) & (ts_series < test_end)
        if tr_mask.sum() >= min_train_bars and te_mask.sum() >= min_test_bars:
            folds.append(
                {
                    "fold_id": fold_id,
                    "train_start": train_start,
                    "train_end": test_start,
                    "test_start": test_start,
                    "test_end": test_end,
                }
            )
            fold_id += 1
        test_start += pd.Timedelta(days=step_days)
    return folds


def _compute_retrain_schedule(folds: list[dict], retrain_interval_days: int) -> list[int]:
    if not folds:
        return []
    retrain_folds = [0]
    last_retrain_ts = folds[0]["test_start"]
    for i, fold in enumerate(folds[1:], 1):
        elapsed = (fold["test_start"] - last_retrain_ts).days
        if elapsed >= retrain_interval_days:
            retrain_folds.append(i)
            last_retrain_ts = fold["test_start"]
    return retrain_folds


def _train(
    train_df: pd.DataFrame, feature_cols: list[str], n_estimators: int
) -> lgb.LGBMClassifier:
    labeled = train_df.dropna(subset=[LABEL_COLUMN])
    x = labeled[feature_cols].fillna(0).values.tolist()
    y = [_LABEL_ENCODE[int(v)] for v in labeled[LABEL_COLUMN]]
    params = {**DEFAULT_PARAMS, "n_estimators": n_estimators, "verbose": -1}
    model = lgb.LGBMClassifier(**params)
    model.fit(x, y)
    return model


def _get_ev(
    model: lgb.LGBMClassifier,
    row: pd.Series,
    feature_cols: list[str],
    threshold: float,
) -> tuple[str, float]:
    x = [[float(row.get(c) or 0.0) for c in feature_cols]]
    proba = model.predict_proba(x)[0]
    p_tp = float(proba[2])
    p_sl = float(proba[0])
    conf = max(p_tp, p_sl)
    if p_tp >= threshold and p_tp >= p_sl:
        return "long", conf
    if p_sl >= threshold:
        return "short", conf
    return "no_trade", conf


# ---------------------------------------------------------------------------
# B-1: ATR-based PnL (variable per-trade size)
# ---------------------------------------------------------------------------


def _gross_pnl_pips_atr(
    sig: str,
    label: int,
    tp_mult: float,
    sl_mult: float,
    atr_at_entry: float,
    pip_size: float,
) -> float | None:
    """Per-trade PnL in pips, scaled by ATR at the entry bar.

    Same shape as v3's ``_gross_pnl_pips`` but the TP / SL pip values
    differ per bar — high-vol bars produce wider winners and losers
    than low-vol bars.
    """
    if sig == "no_trade":
        return None
    if not np.isfinite(atr_at_entry) or atr_at_entry <= 0:
        return None
    tp_pip = (tp_mult * atr_at_entry) / pip_size
    sl_pip = (sl_mult * atr_at_entry) / pip_size
    if sig == "long":
        return tp_pip if label == 1 else (-sl_pip if label == -1 else 0.0)
    return tp_pip if label == -1 else (-sl_pip if label == 1 else 0.0)


def _net_pnl_pips(gross: float | None, spread_pip: float) -> float | None:
    if gross is None:
        return None
    return gross - spread_pip


def _classify_vec(p_tp: np.ndarray, p_sl: np.ndarray, threshold: float) -> np.ndarray:
    """Vectorised version of v3's _get_ev classifier.

    Returns an int8 array: +1 = long, -1 = short, 0 = no_trade.
    """
    long_mask = (p_tp >= threshold) & (p_tp >= p_sl)
    short_mask = (~long_mask) & (p_sl >= threshold)
    out = np.zeros(p_tp.shape, dtype=np.int8)
    out[long_mask] = 1
    out[short_mask] = -1
    return out


def _compute_pnl_vec(
    sig: np.ndarray,
    label: np.ndarray,
    tp_pip: np.ndarray,
    sl_pip: np.ndarray,
    traded: np.ndarray,
) -> np.ndarray:
    """Per-bar gross PnL given signal, label, and TP/SL pip arrays.

    long  + label==+1 -> +tp_pip
    long  + label==-1 -> -sl_pip
    short + label==-1 -> +tp_pip
    short + label==+1 -> -sl_pip
    timeout / no_trade -> 0
    """
    pnl = np.zeros_like(tp_pip)
    long_mask = traded & (sig == 1)
    short_mask = traded & (sig == -1)
    pnl = np.where(long_mask & (label == 1), tp_pip, pnl)
    pnl = np.where(long_mask & (label == -1), -sl_pip, pnl)
    pnl = np.where(short_mask & (label == -1), tp_pip, pnl)
    pnl = np.where(short_mask & (label == 1), -sl_pip, pnl)
    return pnl


def _mr_signal_vec(rsi: np.ndarray, bb_pct_b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Phase 9.17 G-1 MeanReversionStrategy — vectorised.

    Combined-AND logic:
      long  : rsi <= 30 AND bb_pct_b <= 0.10
      short : rsi >= 70 AND bb_pct_b >= 0.90

    Confidence = mean of normalised RSI- and BB-distances from threshold.
    Mirrors `MeanReversionStrategy.evaluate` in
    src/fx_ai_trading/services/strategies/mean_reversion.py.
    """
    long_mask = (rsi <= _MR_RSI_OVERSOLD) & (bb_pct_b <= _MR_BB_LOWER)
    short_mask = (rsi >= _MR_RSI_OVERBOUGHT) & (bb_pct_b >= _MR_BB_UPPER)

    sig = np.zeros(rsi.shape, dtype=np.int8)
    sig[long_mask] = 1
    sig[short_mask] = -1

    rsi_long_conf = np.clip((_MR_RSI_OVERSOLD - rsi) / _MR_RSI_OVERSOLD, 0.0, 1.0)
    bb_long_conf = np.clip((_MR_BB_LOWER - bb_pct_b) / _MR_BB_LOWER, 0.0, 1.0)
    long_conf = (rsi_long_conf + bb_long_conf) / 2.0

    rsi_short_denom = 100.0 - _MR_RSI_OVERBOUGHT
    bb_short_denom = 1.0 - _MR_BB_UPPER
    rsi_short_conf = np.clip(
        (rsi - _MR_RSI_OVERBOUGHT) / rsi_short_denom if rsi_short_denom > 0 else 1.0,
        0.0,
        1.0,
    )
    bb_short_conf = np.clip(
        (bb_pct_b - _MR_BB_UPPER) / bb_short_denom if bb_short_denom > 0 else 1.0,
        0.0,
        1.0,
    )
    short_conf = (rsi_short_conf + bb_short_conf) / 2.0

    conf = np.zeros(rsi.shape, dtype=np.float64)
    conf = np.where(long_mask, long_conf, conf)
    conf = np.where(short_mask, short_conf, conf)
    return sig, conf


def _bo_signal_vec(
    last_close: np.ndarray,
    bb_upper: np.ndarray,
    bb_lower: np.ndarray,
    ema_12: np.ndarray,
    ema_26: np.ndarray,
    atr: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Phase 9.17 G-2 BreakoutStrategy — vectorised.

    Range break + EMA trend confirmation:
      long  : last_close > bb_upper AND ema_12 > ema_26
      short : last_close < bb_lower AND ema_12 < ema_26

    Confidence = ATR-normalised distance from broken band, capped at
    1.0 at `_BO_STRENGTH_FULL_ATR`. Mirrors `BreakoutStrategy.evaluate`
    in src/fx_ai_trading/services/strategies/breakout.py.
    """
    valid_atr = np.isfinite(atr) & (atr > 0)
    long_break = last_close > bb_upper
    short_break = last_close < bb_lower
    trend_up = ema_12 > ema_26
    trend_down = ema_12 < ema_26
    long_mask = long_break & trend_up & valid_atr
    short_mask = short_break & trend_down & valid_atr

    sig = np.zeros(last_close.shape, dtype=np.int8)
    sig[long_mask] = 1
    sig[short_mask] = -1

    safe_atr = np.where(valid_atr, atr, 1.0)
    long_strength = np.where(long_mask, (last_close - bb_upper) / safe_atr, 0.0)
    short_strength = np.where(short_mask, (bb_lower - last_close) / safe_atr, 0.0)
    if _BO_STRENGTH_FULL_ATR > 0:
        long_conf = np.clip(long_strength / _BO_STRENGTH_FULL_ATR, 0.0, 1.0)
        short_conf = np.clip(short_strength / _BO_STRENGTH_FULL_ATR, 0.0, 1.0)
    else:
        long_conf = np.where(long_mask, 1.0, 0.0)
        short_conf = np.where(short_mask, 1.0, 0.0)

    conf = np.zeros(last_close.shape, dtype=np.float64)
    conf = np.where(long_mask, long_conf, conf)
    conf = np.where(short_mask, short_conf, conf)
    return sig, conf


def _eval_fold(
    pair_models: dict[str, lgb.LGBMClassifier],
    pair_test_dfs: dict[str, pd.DataFrame],
    base_pair: str,
    feature_cols: list[str],
    ml_threshold: float,
    spread_pip: float,
    tp_mult: float,
    sl_mult: float,
    rng: random.Random,
    cell_strategies: frozenset[str] = frozenset({_STRATEGY_LGBM}),
) -> tuple[dict, dict[str, int], dict[str, int], dict[str, list[float]]]:
    """Phase 9.17 multi-strategy ensemble per-fold evaluation.

    Computes per-pair per-strategy signals, then runs SELECTOR over the
    cartesian (pair x strategy) candidate space (only strategies in
    `cell_strategies` are eligible).

    All strategies use the same triple-barrier mid-bucket label
    (TP=tp_mult x ATR / SL=sl_mult x ATR) for PnL — design memo §13
    default 4 (apples-to-apples PnL across the cell).

    Returns
    -------
    results : dict
        Per-strategy summary keyed by EURUSD_ML / SELECTOR / EQUAL_AVG / RANDOM.
    pair_select_counts : dict[str, int]
        How many bars SELECTOR picked each pair.
    strategy_select_counts : dict[str, int]
        How many bars SELECTOR picked each strategy (mr / bo / lgbm).
    per_strategy_pnl_series : dict[str, list[float]]
        Per-bar mean gross PnL across pairs that traded under each strategy.
        NaN where the strategy did not trade. Used to compute the
        inter-strategy correlation matrix.
    """
    base_df = pair_test_dfs[base_pair].dropna(subset=[LABEL_COLUMN]).reset_index(drop=True)
    all_pairs = list(pair_models.keys())
    strats = ["EURUSD_ML", "SELECTOR", "EQUAL_AVG", "RANDOM"]
    pair_select_counts: dict[str, int] = {p: 0 for p in all_pairs}
    strategy_select_counts: dict[str, int] = {s: 0 for s in cell_strategies}
    per_strategy_pnl_series: dict[str, list[float]] = {s: [] for s in cell_strategies}

    if base_df.empty:
        empty = {
            s: {
                "gross_sharpe": 0.0,
                "net_sharpe": 0.0,
                "gross_pnl": 0.0,
                "net_pnl": 0.0,
                "hit_rate": 0.0,
                "total_trades": 0,
                "signal_rate": 0.0,
                "net_pnls": [],
                "n_labeled": 0,
            }
            for s in strats
        }
        return empty, pair_select_counts, strategy_select_counts, per_strategy_pnl_series

    base_ts = base_df["timestamp"].to_numpy()
    n_lab = len(base_ts)

    # Pre-compute per-pair arrays aligned to base timestamp grid.
    pair_arrays: dict[str, dict[str, np.ndarray]] = {}
    pair_pip: dict[str, float] = {p: _pip_size(p) for p in all_pairs}

    for pair in all_pairs:
        pdf = pair_test_dfs[pair]
        if pdf.empty:
            zeros = np.zeros(n_lab, dtype=np.float64)
            ints = np.zeros(n_lab, dtype=np.int8)
            empty_bool = np.zeros(n_lab, dtype=bool)
            pair_arrays[pair] = {
                "p_tp": zeros.copy(),
                "p_sl": zeros.copy(),
                "label": ints.copy(),
                "atr": zeros.copy(),
                "rsi": np.full(n_lab, 50.0),
                "bb_pct_b": np.full(n_lab, 0.5),
                "last_close": zeros.copy(),
                "bb_upper": np.full(n_lab, np.inf),
                "bb_lower": np.full(n_lab, -np.inf),
                "ema_12": zeros.copy(),
                "ema_26": zeros.copy(),
                "present": empty_bool,
            }
            continue

        pdf_indexed = pdf.set_index("timestamp")
        aligned = pdf_indexed.reindex(base_ts)
        present = aligned[LABEL_COLUMN].notna().to_numpy()

        # LightGBM probabilities (only when this strategy is in the cell).
        if _STRATEGY_LGBM in cell_strategies:
            feat_arr = aligned[feature_cols].fillna(0.0).to_numpy(dtype=np.float64)
            if present.any():
                proba = pair_models[pair].predict_proba(feat_arr)  # (n_lab, 3)
                p_tp = proba[:, 2].astype(np.float64)
                p_sl = proba[:, 0].astype(np.float64)
            else:
                p_tp = np.zeros(n_lab, dtype=np.float64)
                p_sl = np.zeros(n_lab, dtype=np.float64)
        else:
            p_tp = np.zeros(n_lab, dtype=np.float64)
            p_sl = np.zeros(n_lab, dtype=np.float64)

        label = aligned[LABEL_COLUMN].fillna(0).to_numpy(dtype=np.int8)
        atr_arr = aligned["atr_14"].fillna(0.0).to_numpy(dtype=np.float64)

        # Features for MR / BO. Defaults map to neutral (no-trade).
        rsi_arr = aligned["rsi_14"].fillna(50.0).to_numpy(dtype=np.float64)
        bb_pct_b_arr = aligned["bb_pct_b"].fillna(0.5).to_numpy(dtype=np.float64)
        last_close_arr = aligned["last_close"].fillna(0.0).to_numpy(dtype=np.float64)
        bb_upper_arr = aligned["bb_upper"].fillna(np.inf).to_numpy(dtype=np.float64)
        bb_lower_arr = aligned["bb_lower"].fillna(-np.inf).to_numpy(dtype=np.float64)
        ema_12_arr = aligned["ema_12"].fillna(0.0).to_numpy(dtype=np.float64)
        ema_26_arr = aligned["ema_26"].fillna(0.0).to_numpy(dtype=np.float64)

        pair_arrays[pair] = {
            "p_tp": p_tp,
            "p_sl": p_sl,
            "label": label,
            "atr": atr_arr,
            "rsi": rsi_arr,
            "bb_pct_b": bb_pct_b_arr,
            "last_close": last_close_arr,
            "bb_upper": bb_upper_arr,
            "bb_lower": bb_lower_arr,
            "ema_12": ema_12_arr,
            "ema_26": ema_26_arr,
            "present": present,
        }

    # Per (pair, strategy): signals, confidence, gross PnL, traded mask.
    pair_strat_sig: dict[tuple[str, str], np.ndarray] = {}
    pair_strat_conf: dict[tuple[str, str], np.ndarray] = {}
    pair_strat_gross: dict[tuple[str, str], np.ndarray] = {}
    pair_strat_traded: dict[tuple[str, str], np.ndarray] = {}

    for pair in all_pairs:
        pa = pair_arrays[pair]
        atr = pa["atr"]
        valid_atr = np.isfinite(atr) & (atr > 0)
        present = pa["present"]
        pip = pair_pip[pair]
        label = pa["label"].astype(np.int64)
        tp_pip = (tp_mult * atr) / pip
        sl_pip = (sl_mult * atr) / pip

        if _STRATEGY_LGBM in cell_strategies:
            sig_l = _classify_vec(pa["p_tp"], pa["p_sl"], ml_threshold)
            sig_l = np.where(present, sig_l, 0).astype(np.int8)
            conf_l = np.maximum(pa["p_tp"], pa["p_sl"])
            traded_l = (sig_l != 0) & valid_atr
            gross_l = _compute_pnl_vec(sig_l, label, tp_pip, sl_pip, traded_l)
            pair_strat_sig[(pair, _STRATEGY_LGBM)] = sig_l
            pair_strat_conf[(pair, _STRATEGY_LGBM)] = conf_l
            pair_strat_gross[(pair, _STRATEGY_LGBM)] = gross_l
            pair_strat_traded[(pair, _STRATEGY_LGBM)] = traded_l

        if _STRATEGY_MR in cell_strategies:
            sig_m, conf_m = _mr_signal_vec(pa["rsi"], pa["bb_pct_b"])
            sig_m = np.where(present, sig_m, 0).astype(np.int8)
            conf_m = np.where(present, conf_m, 0.0)
            traded_m = (sig_m != 0) & valid_atr
            gross_m = _compute_pnl_vec(sig_m, label, tp_pip, sl_pip, traded_m)
            pair_strat_sig[(pair, _STRATEGY_MR)] = sig_m
            pair_strat_conf[(pair, _STRATEGY_MR)] = conf_m
            pair_strat_gross[(pair, _STRATEGY_MR)] = gross_m
            pair_strat_traded[(pair, _STRATEGY_MR)] = traded_m

        if _STRATEGY_BO in cell_strategies:
            sig_b, conf_b = _bo_signal_vec(
                pa["last_close"],
                pa["bb_upper"],
                pa["bb_lower"],
                pa["ema_12"],
                pa["ema_26"],
                atr,
            )
            sig_b = np.where(present, sig_b, 0).astype(np.int8)
            conf_b = np.where(present, conf_b, 0.0)
            traded_b = (sig_b != 0) & valid_atr
            gross_b = _compute_pnl_vec(sig_b, label, tp_pip, sl_pip, traded_b)
            pair_strat_sig[(pair, _STRATEGY_BO)] = sig_b
            pair_strat_conf[(pair, _STRATEGY_BO)] = conf_b
            pair_strat_gross[(pair, _STRATEGY_BO)] = gross_b
            pair_strat_traded[(pair, _STRATEGY_BO)] = traded_b

    # ----- EURUSD_ML baseline (always lgbm if available, else first strat) ---
    base_strat = (
        _STRATEGY_LGBM if _STRATEGY_LGBM in cell_strategies else next(iter(cell_strategies))
    )
    eu_traded_arr = pair_strat_traded[(base_pair, base_strat)]
    eu_gross_full = pair_strat_gross[(base_pair, base_strat)]
    eu_gross = eu_gross_full[eu_traded_arr]
    eu_net = eu_gross - spread_pip

    # ----- SELECTOR over (pair, strategy) -----
    candidates: list[tuple[str, str]] = [(p, s) for p in all_pairs for s in cell_strategies]
    conf_mat = np.stack([pair_strat_conf[c] for c in candidates], axis=0)
    gross_mat = np.stack([pair_strat_gross[c] for c in candidates], axis=0)
    traded_mat = np.stack([pair_strat_traded[c] for c in candidates], axis=0)

    active_any = np.any(traded_mat, axis=0)
    conf_for_pick = np.where(traded_mat, conf_mat, -1.0)
    sel_cand_idx = np.argmax(conf_for_pick, axis=0)
    sel_gross_all = gross_mat[sel_cand_idx, np.arange(n_lab)]
    sel_gross = sel_gross_all[active_any]
    sel_net = sel_gross - spread_pip

    for i in range(n_lab):
        if active_any[i]:
            cidx = sel_cand_idx[i]
            picked_pair, picked_strat = candidates[cidx]
            pair_select_counts[picked_pair] += 1
            strategy_select_counts[picked_strat] += 1

    # ----- EQUAL_AVG: mean of all (pair, strategy) gross PnLs per bar -----
    masked = np.where(traded_mat, gross_mat, np.nan)
    mean_per_bar = np.nanmean(masked, axis=0)  # NaN where nothing traded
    eq_active = ~np.isnan(mean_per_bar)
    eq_gross = mean_per_bar[eq_active]
    eq_net = eq_gross - spread_pip

    # ----- RANDOM: pick a random pair regardless of trading; use base_strat -
    pair_idx_list = list(all_pairs)
    present_mat = np.stack([pair_arrays[p]["present"] for p in pair_idx_list], axis=0)
    any_present = np.any(present_mat, axis=0)
    rd_gross_list: list[float] = []
    for i in range(n_lab):
        if not any_present[i]:
            continue
        eligible = [j for j in range(len(pair_idx_list)) if present_mat[j, i]]
        chosen_pair = pair_idx_list[rng.choice(eligible)]
        if pair_strat_traded[(chosen_pair, base_strat)][i]:
            rd_gross_list.append(float(pair_strat_gross[(chosen_pair, base_strat)][i]))
    rd_gross = np.asarray(rd_gross_list, dtype=np.float64)
    rd_net = rd_gross - spread_pip

    # ----- Per-strategy PnL series for inter-strategy correlation matrix ----
    # For each strategy, compute the per-bar mean gross PnL across pairs that
    # traded under that strategy. NaN where the strategy didn't trade in
    # the bar. Used downstream by `_compute_correlation_matrix`.
    for strat in cell_strategies:
        traded_strat_mat = np.stack([pair_strat_traded[(p, strat)] for p in all_pairs], axis=0)
        gross_strat_mat = np.stack([pair_strat_gross[(p, strat)] for p in all_pairs], axis=0)
        masked_strat = np.where(traded_strat_mat, gross_strat_mat, np.nan)
        mean_strat = np.nanmean(masked_strat, axis=0)
        per_strategy_pnl_series[strat] = mean_strat.tolist()

    # ----- Result dicts -----
    def _series_summary(net: np.ndarray, gross: np.ndarray) -> dict:
        wins = int((net > 0).sum())
        losses = int((net < 0).sum())
        ties = int((net == 0).sum())
        total = wins + losses + ties
        hit = wins / (wins + losses) if (wins + losses) > 0 else 0.0
        return {
            "gross_sharpe": _sharpe(gross.tolist()),
            "net_sharpe": _sharpe(net.tolist()),
            "gross_pnl": float(gross.sum()),
            "net_pnl": float(net.sum()),
            "hit_rate": hit,
            "total_trades": total,
            "signal_rate": total / n_lab if n_lab > 0 else 0.0,
            "net_pnls": net.tolist(),
            "n_labeled": n_lab,
        }

    results = {
        "EURUSD_ML": _series_summary(eu_net, eu_gross),
        "SELECTOR": _series_summary(sel_net, sel_gross),
        "EQUAL_AVG": _series_summary(eq_net, eq_gross),
        "RANDOM": _series_summary(rd_net, rd_gross),
    }
    return results, pair_select_counts, strategy_select_counts, per_strategy_pnl_series


def _sharpe(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    return (mu / math.sqrt(var)) if var > 0 else 0.0


def _max_drawdown(pnl_series: list[float]) -> float:
    """Max drawdown of the cumulative pnl curve, in pip units (>= 0).

    Computed as max(running_peak - cumulative). Equivalent to the worst
    peak-to-trough fall on the per-trade equity curve.
    """
    if not pnl_series:
        return 0.0
    arr = np.asarray(pnl_series, dtype=np.float64)
    cum = np.cumsum(arr)
    peak = np.maximum.accumulate(cum)
    dd = peak - cum  # >= 0
    return float(dd.max())


# ---------------------------------------------------------------------------
# Aggregate / report (same shape as v3)
# ---------------------------------------------------------------------------


def _aggregate(fold_results: list[dict]) -> dict:
    agg: dict[str, dict] = {}
    strats = ["EURUSD_ML", "SELECTOR", "EQUAL_AVG", "RANDOM"]
    for s in strats:
        all_net: list[float] = []
        for fr in fold_results:
            all_net.extend(fr[s]["net_pnls"])
        gross_pnl = sum(fr[s]["gross_pnl"] for fr in fold_results)
        net_pnl = sum(fr[s]["net_pnl"] for fr in fold_results)
        total_tr = sum(fr[s]["total_trades"] for fr in fold_results)
        mean_sh = float(np.mean([fr[s]["net_sharpe"] for fr in fold_results]))
        med_sh = float(np.median([fr[s]["net_sharpe"] for fr in fold_results]))
        std_sh = float(np.std([fr[s]["net_sharpe"] for fr in fold_results]))
        mean_gross = float(np.mean([fr[s]["gross_sharpe"] for fr in fold_results]))
        win_fold = sum(1 for fr in fold_results if fr[s]["net_sharpe"] > 0)
        sig_rates = [fr[s]["signal_rate"] for fr in fold_results]
        # Phase 9.15/F-1+: max drawdown across the concatenated per-trade
        # equity curve (peak-to-trough on cumulative net pnl).
        max_dd = _max_drawdown(all_net)
        # DD as % of net PnL — interpretable "what fraction of gains can be
        # lost mid-run". Capped at 999% for cosmetic display.
        dd_pct_of_pnl = min(999.0, 100.0 * max_dd / net_pnl) if net_pnl > 0 else 999.0
        agg[s] = {
            "overall_sharpe_net": _sharpe(all_net),
            "mean_fold_net_sharpe": mean_sh,
            "median_fold_net_sharpe": med_sh,
            "std_fold_net_sharpe": std_sh,
            "overall_gross_sharpe": mean_gross,
            "win_fold_pct": win_fold / len(fold_results) if fold_results else 0.0,
            "gross_pnl": gross_pnl,
            "net_pnl": net_pnl,
            "total_trades": total_tr,
            "signal_rate_mean": float(np.mean(sig_rates)),
            "max_drawdown_pip": max_dd,
            "max_dd_pct_of_pnl": dd_pct_of_pnl,
        }
    return agg


def _hdr(title: str) -> None:
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100)


def _print_comparison(agg: dict[str, dict], spread_pip: float, cell_name: str) -> None:
    _hdr(
        f"COMPARISON SUMMARY (cell={cell_name!r}  "
        f"slippage={spread_pip:.2f}pip; bid/ask spread already in labels)"
    )
    print(
        f"  {'Strategy':<12} {'NetSharpe':>10} "
        f"{'NetPnL(pip)':>13} {'MaxDD(pip)':>11} {'DD%PnL':>8} "
        f"{'WinFold%':>9} {'SigRate':>9} {'Trades':>10}"
    )
    print("  " + "-" * 100)
    for s, v in agg.items():
        print(
            f"  {s:<12} {v['overall_sharpe_net']:>10.3f} "
            f"{v['net_pnl']:>13.1f} {v['max_drawdown_pip']:>11.1f} "
            f"{v['max_dd_pct_of_pnl']:>7.1f}% "
            f"{v['win_fold_pct'] * 100:>8.0f}% {v['signal_rate_mean'] * 100:>8.1f}% "
            f"{v['total_trades']:>10,}"
        )


def _print_strategy_breakdown(strategy_select_totals: dict[str, int], cell_name: str) -> None:
    """Phase 9.17: per-strategy share of SELECTOR picks within a cell."""
    _hdr(f"STRATEGY SHARE IN SELECTOR (cell={cell_name!r})")
    grand = sum(strategy_select_totals.values())
    print(f"  {'Strategy':<10} {'Picks':>10} {'Share':>8}")
    print("  " + "-" * 32)
    for strat, count in sorted(strategy_select_totals.items(), key=lambda kv: -kv[1]):
        share = count / grand * 100 if grand > 0 else 0.0
        print(f"  {strat:<10} {count:>10,} {share:>7.1f}%")


def _compute_correlation_matrix(
    pnl_series_by_strat: dict[str, list[float]],
) -> dict[tuple[str, str], float]:
    """Pairwise Pearson correlation between per-bar strategy PnL series.

    Each input series is the per-bar mean gross PnL across pairs that
    traded under the strategy (NaN where the strategy did not trade).
    Correlation is computed over bars where BOTH strategies traded; if
    fewer than 5 such bars exist, returns 0.0 (insufficient sample).
    """
    out: dict[tuple[str, str], float] = {}
    keys = list(pnl_series_by_strat.keys())
    arrs = {k: np.asarray(pnl_series_by_strat[k], dtype=np.float64) for k in keys}
    for i, a in enumerate(keys):
        for b in keys[i:]:
            xa = arrs[a]
            xb = arrs[b]
            mask = np.isfinite(xa) & np.isfinite(xb)
            if mask.sum() < 5:
                out[(a, b)] = 0.0
                continue
            xa_m = xa[mask]
            xb_m = xb[mask]
            if xa_m.std() == 0 or xb_m.std() == 0:
                out[(a, b)] = 0.0
                continue
            rho = float(np.corrcoef(xa_m, xb_m)[0, 1])
            if not np.isfinite(rho):
                rho = 0.0
            out[(a, b)] = rho
    return out


def _print_correlation_matrix(rho_pairs: dict[tuple[str, str], float]) -> None:
    """Print the inter-strategy correlation matrix as a square table."""
    strats = sorted({a for (a, _b) in rho_pairs} | {b for (_a, b) in rho_pairs})
    if len(strats) < 2:
        return
    _hdr("INTER-STRATEGY CORRELATION (Pearson on per-bar mean gross PnL)")
    header = "  " + " " * 6 + "  ".join(f"{s:>8}" for s in strats)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for a in strats:
        row = [f"  {a:<6}"]
        for b in strats:
            key = (a, b) if (a, b) in rho_pairs else (b, a)
            row.append(f"{rho_pairs.get(key, 0.0):>+8.3f}")
        print("  ".join(row))


def _print_verdict(
    agg: dict[str, dict],
    spread_pip: float,
    cell_name: str,
    rho_pairs: dict[tuple[str, str], float],
    baseline_pnl: float | None,
) -> None:
    """Phase 9.17 verdict using PnL-priority + correlation gate."""
    _hdr(f"PHASE 9.17 VERDICT (cell={cell_name!r}; slippage={spread_pip:.2f}pip)")
    baseline = agg["EURUSD_ML"]
    selector = agg["SELECTOR"]
    sh = selector["overall_sharpe_net"]
    pnl = selector["net_pnl"]
    dd_pct = selector["max_dd_pct_of_pnl"]

    # Max non-self correlation in this cell.
    max_rho = 0.0
    for (a, b), v in rho_pairs.items():
        if a != b:
            max_rho = max(max_rho, abs(v))

    sh_delta = sh - baseline["overall_sharpe_net"]
    pnl_delta = pnl - baseline["net_pnl"]
    print(
        f"  EURUSD_ML  Sharpe={baseline['overall_sharpe_net']:.3f}  "
        f"PnL={baseline['net_pnl']:.0f} pip  "
        f"DD={baseline['max_drawdown_pip']:.0f} pip ({baseline['max_dd_pct_of_pnl']:.0f}% of PnL)"
    )
    print(
        f"  SELECTOR   Sharpe={sh:.3f}  PnL={pnl:.0f} pip  "
        f"DD={selector['max_drawdown_pip']:.0f} pip ({dd_pct:.0f}% of PnL)  "
        f"(vs EU: Sh {sh_delta:+.3f}, PnL {pnl_delta:+.0f})"
    )
    if baseline_pnl is not None and baseline_pnl > 0:
        ratio = pnl / baseline_pnl
        print(f"  vs Phase 9.16 baseline (lgbm_only PnL={baseline_pnl:.0f}): ratio={ratio:.2f}x")
    print(f"  Max inter-strategy rho (this cell): {max_rho:.3f}")
    print("")
    print("  [PnL-priority + correlation gate -- per docs/design/phase9_17_design_memo.md sec.5]")

    # Phase 9.17 verdict gates.
    pnl_ratio = pnl / baseline_pnl if (baseline_pnl is not None and baseline_pnl > 0) else 0.0
    if sh >= 0.20 and pnl > 0:
        print(f"  [LEGACY GO] SELECTOR Sharpe>=0.20 AND PnL>0 at spread={spread_pip:.2f}")
    elif (
        baseline_pnl is not None
        and pnl_ratio >= 1.10
        and dd_pct <= 5.0
        and sh >= baseline["overall_sharpe_net"]
        and max_rho <= 0.4
    ):
        print(
            f"  [GO] PnL>=1.10x baseline AND rho<=0.4 AND Sharpe>=baseline AND DD%PnL<=5% "
            f"(rho={max_rho:.3f})"
        )
    elif (
        baseline_pnl is not None
        and pnl_ratio >= 1.05
        and dd_pct <= 5.0
        and sh >= baseline["overall_sharpe_net"]
        and 0.4 < max_rho <= 0.6
    ):
        print(
            f"  [PARTIAL GO] PnL>=1.05x baseline AND Sharpe>=baseline; "
            f"rho={max_rho:.3f} drags expected lift"
        )
    elif sh >= 0.18:
        print("  [STRETCH GO] SELECTOR Sharpe>=0.18 - unblocks Phase 9.11")
    else:
        print(
            f"  [NO ADOPT] PnL<baseline OR DD%PnL>5% OR rho>0.6 "
            f"(rho={max_rho:.3f}, ratio={pnl_ratio:.2f}x, DD%PnL={dd_pct:.1f}%)"
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="compare_multipair_v13_ensemble",
        description="Phase 9.17 multi-strategy ensemble backtest.",
    )
    parser.add_argument("--pairs", default=",".join(DEFAULT_PAIRS))
    parser.add_argument("--base-pair", default="EUR_USD")
    parser.add_argument("--tp-mult", type=float, default=1.5)
    parser.add_argument("--sl-mult", type=float, default=1.0)
    parser.add_argument("--horizon", type=int, default=20)
    parser.add_argument("--conf-threshold", type=float, default=0.50)
    parser.add_argument(
        "--slippage-pip",
        type=float,
        default=0.0,
        dest="spread_pip",
        help=(
            "Per-trade slippage in pips deducted on top of the bid/ask-aware "
            "label PnL. Default 0.0 (no additional cost - bid/ask is already "
            "embedded in the label)."
        ),
    )
    parser.add_argument(
        "--ensemble-cells",
        default=",".join(_DEFAULT_CELLS),
        help=(
            "Phase 9.17 internal sweep. Comma-separated cells. "
            f"Default: {','.join(_DEFAULT_CELLS)}. "
            "lgbm_only reproduces v9 baseline; +mr / +bo add Mean reversion / "
            "Breakout strategies; lgbm+mr+bo runs the full ensemble. "
            "Loads + features + train run ONCE per fold and are SHARED across "
            "cells; only the eval loop runs per cell."
        ),
    )
    parser.add_argument("--retrain-interval-days", type=int, default=90)
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]
    base_pair = args.base_pair
    if base_pair not in pairs:
        print(f"ERROR: base-pair {base_pair!r} not in pairs list", file=sys.stderr)
        return 2

    cell_specs = [c.strip() for c in args.ensemble_cells.split(",") if c.strip()]
    for c in cell_specs:
        if c not in _CELL_STRATEGY_SETS:
            print(
                f"ERROR: invalid cell {c!r} (valid: {tuple(_CELL_STRATEGY_SETS.keys())})",
                file=sys.stderr,
            )
            return 2

    print(f"Pairs ({len(pairs)}): {', '.join(pairs)}")
    print(
        f"Base: {base_pair} | training_label TP/SL = {args.tp_mult}/{args.sl_mult} xATR | "
        f"horizon={args.horizon} | conf>={args.conf_threshold} | "
        f"slippage={args.spread_pip}pip | "
        f"retrain every {args.retrain_interval_days}d"
    )
    print(f"Ensemble cells ({len(cell_specs)}): {', '.join(cell_specs)}\n")

    print("Loading candles ...")
    mid_dfs: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        path, mode = _pick_file(pair)
        df = _load_ba(path) if mode == "BA" else _load_mid(path)
        mid_dfs[pair] = df
        print(
            f"  {pair}: {len(df):>7,} bars  ({mode} mode)  "
            f"{df.index.min().date()} -> {df.index.max().date()}"
        )

    print("\nBuilding features (per pair, mid-bucket bid/ask label + orthogonal features) ...")
    feat_dfs: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        feat = _build_pair_features(
            mid_dfs[pair], args.horizon, args.tp_mult, args.sl_mult, instrument=pair
        )
        feat_dfs[pair] = feat
        print(f"  {pair}: {len(feat):>7,} rows  {feat[LABEL_COLUMN].notna().sum():>7,} labeled")
    feat_dfs = _build_cross_pair_features(feat_dfs, ref_pair=base_pair)

    sample = feat_dfs[base_pair]
    folds = _generate_folds(feat_dfs[base_pair]["timestamp"])
    retrain_schedule = _compute_retrain_schedule(folds, args.retrain_interval_days)
    print(f"\nFolds: {len(folds)}  retrains at: {retrain_schedule}")

    # Phase 9.17 reuses the Phase 9.16 production feature column set
    # (spread bundle, no time/volume/regime). Per Phase 9.15/F-1 closure,
    # the spread bundle alone outperforms 'all'.
    raw_exclude = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "bid_o",
        "bid_h",
        "bid_l",
        "bid_c",
        "ask_o",
        "ask_h",
        "ask_l",
        "ask_c",
        LABEL_COLUMN,
    }
    ortho_drop = set(_ORTHO_COLS_TIME) | set(_ORTHO_COLS_VOLUME) | set(_ORTHO_COLS_REGIME)
    full_exclude = raw_exclude | ortho_drop
    feature_cols = [c for c in sample.columns if c not in full_exclude]
    print(f"Feature columns ({len(feature_cols)}): spread bundle (Phase 9.15/F-1 winner)\n")

    # Train ONCE per fold. Eval runs N times (one per cell) reusing the
    # same trained models. This is the internal-sweep advantage.
    pair_models: dict[str, lgb.LGBMClassifier] = {}
    rng = random.Random(args.seed)

    # Per-cell accumulators.
    fold_results_by_cell: dict[str, list[dict]] = {c: [] for c in cell_specs}
    pair_select_totals_by_cell: dict[str, dict[str, int]] = {
        c: {pair: 0 for pair in pairs} for c in cell_specs
    }
    strategy_select_totals_by_cell: dict[str, dict[str, int]] = {
        c: {s: 0 for s in _CELL_STRATEGY_SETS[c]} for c in cell_specs
    }
    # Concatenated per-bar PnL series across folds, per cell, per strategy.
    pnl_series_by_cell: dict[str, dict[str, list[float]]] = {
        c: {s: [] for s in _CELL_STRATEGY_SETS[c]} for c in cell_specs
    }

    print("Running folds (train once -> eval per cell) ...")
    for fid, fold in enumerate(folds):
        if fid in retrain_schedule:
            for pair in pairs:
                ts = feat_dfs[pair]["timestamp"]
                tr_mask = (ts >= fold["train_start"]) & (ts < fold["train_end"])
                pair_models[pair] = _train(feat_dfs[pair][tr_mask], feature_cols, args.n_estimators)
        pair_test_dfs: dict[str, pd.DataFrame] = {}
        for pair in pairs:
            ts = feat_dfs[pair]["timestamp"]
            te_mask = (ts >= fold["test_start"]) & (ts < fold["test_end"])
            pair_test_dfs[pair] = feat_dfs[pair][te_mask].reset_index(drop=True)

        retrain_marker = "*" if fid in retrain_schedule else " "
        sharpe_strs: list[str] = []
        for cell_name in cell_specs:
            cell_strategies = _CELL_STRATEGY_SETS[cell_name]
            results, pair_counts, strat_counts, pnl_series = _eval_fold(
                pair_models,
                pair_test_dfs,
                base_pair,
                feature_cols,
                args.conf_threshold,
                args.spread_pip,
                args.tp_mult,
                args.sl_mult,
                rng,
                cell_strategies=cell_strategies,
            )
            fold_results_by_cell[cell_name].append(results)
            for pair, cnt in pair_counts.items():
                pair_select_totals_by_cell[cell_name][pair] += cnt
            for strat, cnt in strat_counts.items():
                strategy_select_totals_by_cell[cell_name][strat] += cnt
            for strat, series in pnl_series.items():
                pnl_series_by_cell[cell_name][strat].extend(series)
            sharpe_strs.append(f"{cell_name[:11]}={results['SELECTOR']['net_sharpe']:>5.2f}")
        print(f"  Fold{fid:>3}{retrain_marker} SEL Sharpe: " + "  ".join(sharpe_strs))

    # Per-cell summaries. Find lgbm_only baseline PnL (if present) for ratio.
    cell_summaries: list[tuple[str, dict, dict[tuple[str, str], float]]] = []
    baseline_cell_pnl: float | None = None
    for cell_name in cell_specs:
        agg = _aggregate(fold_results_by_cell[cell_name])
        if cell_name == _CELL_LGBM_ONLY:
            baseline_cell_pnl = agg["SELECTOR"]["net_pnl"]

    for cell_name in cell_specs:
        agg = _aggregate(fold_results_by_cell[cell_name])
        rho_pairs = _compute_correlation_matrix(pnl_series_by_cell[cell_name])
        _print_comparison(agg, args.spread_pip, cell_name)
        _print_strategy_breakdown(strategy_select_totals_by_cell[cell_name], cell_name)
        if len(_CELL_STRATEGY_SETS[cell_name]) > 1:
            _print_correlation_matrix(rho_pairs)
        _print_verdict(agg, args.spread_pip, cell_name, rho_pairs, baseline_cell_pnl)
        cell_summaries.append((cell_name, agg, rho_pairs))

    # Cross-cell summary.
    if len(cell_summaries) > 1:
        _hdr("MULTI-CELL ENSEMBLE SUMMARY (SELECTOR)")
        print(
            f"  {'Cell':<14} {'NetSharpe':>10} {'NetPnL(pip)':>13} "
            f"{'MaxDD(pip)':>11} {'DD%PnL':>8} {'MaxRho':>8} {'Trades':>10}"
        )
        print("  " + "-" * 95)
        for spec, agg, rho_pairs in cell_summaries:
            sel = agg["SELECTOR"]
            max_rho = 0.0
            for (a, b), v in rho_pairs.items():
                if a != b:
                    max_rho = max(max_rho, abs(v))
            ratio = (
                f"  ({sel['net_pnl'] / baseline_cell_pnl:.2f}x)"
                if baseline_cell_pnl and baseline_cell_pnl > 0 and spec != _CELL_LGBM_ONLY
                else ""
            )
            print(
                f"  {spec:<14} {sel['overall_sharpe_net']:>10.3f} "
                f"{sel['net_pnl']:>13.1f} {sel['max_drawdown_pip']:>11.1f} "
                f"{sel['max_dd_pct_of_pnl']:>7.1f}% {max_rho:>8.3f} "
                f"{sel['total_trades']:>10,}{ratio}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
