"""compare_multipair_v7_kelly.py — Phase 9.13/C-1 Kelly position sizing.

Successor to v5 (`compare_multipair_v5_bidask.py`). Same bid/ask-aware
labels and vectorised eval; the only change is *how big each trade is*.

Where v5 booked every signal at 1 unit, v7 sizes each trade by
fractional Kelly using Layer 1's predict_proba as the win probability:

    p_win = max(p_tp, p_sl)
    b     = TP_mult / SL_mult                       (= 1.5 at defaults)
    kelly = (p_win * b - (1 - p_win)) / b
    size  = max(0, kelly_fraction * kelly)

The per-trade pip pnl is then ``size * gross_pip``. Because Sharpe is
computed on the per-trade pnl series, sizes that proportionally favour
high-confidence bars amplify the average without adding variance — so
Sharpe rises **iff Layer 1 is calibrated**. If the model says 0.65
probability on bars that hit only 50%, Kelly amplifies miscalibration
and Sharpe drops. The grid sweep on ``--kelly-fraction`` will surface
either way.

CLI
---
    --kelly-fraction 0.25     # f ∈ {0.10, 0.25, 0.50, 1.00} for sweep
    --no-kelly                # uniform 1-unit sizing (reproduces v5)

Phase 9.13 plan: C-1 alone first; C-2 (correlation cluster cap) and
C-3 (kill switches) are layered on top in subsequent PRs. Closure
verdict (C-4) compares the full stack to v5's SOFT GO 0.160 baseline.

Requires data/candles_<pair>_M1_365d_BA.jsonl (mid-only files cannot
satisfy bid/ask labels — same constraint as v5).
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


def _build_pair_features(
    df_m1: pd.DataFrame, horizon: int, tp_mult: float, sl_mult: float
) -> pd.DataFrame:
    df = _add_m1_features(df_m1)
    df = _add_upper_tf(df, "5min", "m5")
    df = _add_upper_tf(df, "15min", "m15")
    df = _add_upper_tf(df, "1h", "h1")
    # Phase 9.12/B-2: switch to bid/ask-aware labels.
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


# ---------------------------------------------------------------------------
# C-1: fractional Kelly position sizing
# ---------------------------------------------------------------------------


def _kelly_size_vec(p_win: np.ndarray, b: float, fraction: float) -> np.ndarray:
    """Fractional Kelly per-bar size in [0, +inf), vectorised.

    p_win = Layer 1 confidence on the chosen direction (max(p_tp, p_sl))
    b     = TP_mult / SL_mult (win/loss payoff ratio)
    fraction = Kelly fraction multiplier (0.25 = quarter Kelly)

    Negative Kelly (model says edge is negative on this bar) clamps to 0
    so the trade is not booked.
    """
    if fraction <= 0:
        return np.zeros_like(p_win)
    q = 1.0 - p_win
    kelly = (p_win * b - q) / b  # shape: (n,)
    sized = fraction * kelly
    return np.clip(sized, 0.0, None)


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
    kelly_fraction: float = 0.0,
) -> tuple[dict, dict[str, int]]:
    """Optimised per-fold evaluation (Phase 9.12 perf pass + C-1 Kelly).

    When ``kelly_fraction == 0.0`` (default), every trade is booked at
    1 unit (reproduces v5 / v6 baseline). When > 0, each trade is
    sized by ``fraction * kelly(p_win, b)`` where ``p_win = max(p_tp,
    p_sl)`` and ``b = tp_mult / sl_mult``. The per-trade pnl in pips
    is then multiplied by the size before aggregation.

    Cost dominated by two ops in the v3 / earlier-v4 implementation:
      (1) per-bar ``predict_proba`` for each pair -> N_bars * N_pairs calls
      (2) ``pdf[pdf["timestamp"] == ts]`` per pair per bar -> O(N_test) lookup

    This version vectorises both:
      - One ``predict_proba`` call per pair on the *whole* test slice.
      - Per-pair test frames are indexed by timestamp once at fold entry,
        giving O(1) access by position in the base timestamp grid.
    """
    base_df = pair_test_dfs[base_pair].dropna(subset=[LABEL_COLUMN]).reset_index(drop=True)
    all_pairs = list(pair_models.keys())
    strats = ["EURUSD_ML", "SELECTOR", "EQUAL_AVG", "RANDOM"]
    pair_select_counts: dict[str, int] = {p: 0 for p in all_pairs}

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
        return empty, pair_select_counts

    base_ts = base_df["timestamp"].to_numpy()
    n_lab = len(base_ts)

    # Pre-compute, per pair, arrays aligned to the base timestamp grid:
    #   p_tp[i], p_sl[i] = LightGBM proba for the bar at base_ts[i]
    #   label[i]         = triple-barrier label (NaN -> NaN)
    #   atr[i]           = ATR(14) at the entry bar
    #   present[i]       = True iff this pair has a labeled row at base_ts[i]
    pair_arrays: dict[str, dict[str, np.ndarray]] = {}

    for pair in all_pairs:
        pdf = pair_test_dfs[pair]
        if pdf.empty:
            empty_bool = np.zeros(n_lab, dtype=bool)
            zeros = np.zeros(n_lab, dtype=np.float64)
            ints = np.zeros(n_lab, dtype=np.int8)
            pair_arrays[pair] = {
                "p_tp": zeros.copy(),
                "p_sl": zeros.copy(),
                "label": ints,
                "atr": zeros.copy(),
                "present": empty_bool,
            }
            continue

        # Index the pair test frame by timestamp; align to base_ts via reindex.
        pdf_indexed = pdf.set_index("timestamp")
        aligned = pdf_indexed.reindex(base_ts)
        present = aligned[LABEL_COLUMN].notna().to_numpy()

        # Where present, fill NaNs in feature columns with 0 (matches v3 _get_ev).
        feat_arr = aligned[feature_cols].fillna(0.0).to_numpy(dtype=np.float64)

        if present.any():
            proba = pair_models[pair].predict_proba(feat_arr)  # shape (n_lab, 3)
            p_tp = proba[:, 2].astype(np.float64)
            p_sl = proba[:, 0].astype(np.float64)
        else:
            p_tp = np.zeros(n_lab, dtype=np.float64)
            p_sl = np.zeros(n_lab, dtype=np.float64)

        label_arr = aligned[LABEL_COLUMN].fillna(0).to_numpy(dtype=np.int8)
        atr_arr = aligned["atr_14"].fillna(0.0).to_numpy(dtype=np.float64)

        pair_arrays[pair] = {
            "p_tp": p_tp,
            "p_sl": p_sl,
            "label": label_arr,
            "atr": atr_arr,
            "present": present,
        }

    # Per-pair signal arrays (vectorised once).
    pair_signal: dict[str, np.ndarray] = {}  # int8: +1 long, -1 short, 0 no-trade
    pair_conf: dict[str, np.ndarray] = {}  # max(p_tp, p_sl)
    pair_pip: dict[str, float] = {p: _pip_size(p) for p in all_pairs}
    for pair in all_pairs:
        pa = pair_arrays[pair]
        sig = _classify_vec(pa["p_tp"], pa["p_sl"], ml_threshold)
        # absent rows can't trade — force no-trade
        sig = np.where(pa["present"], sig, 0).astype(np.int8)
        pair_signal[pair] = sig
        pair_conf[pair] = np.maximum(pa["p_tp"], pa["p_sl"])

    # Per-pair gross PnL in pips (vectorised).
    pair_gross: dict[str, np.ndarray] = {}
    pair_traded: dict[str, np.ndarray] = {}  # bool: bar produced a trade
    b_ratio = tp_mult / sl_mult if sl_mult > 0 else 1.0
    for pair in all_pairs:
        pa = pair_arrays[pair]
        atr = pa["atr"]
        valid_atr = np.isfinite(atr) & (atr > 0)
        sig = pair_signal[pair]
        traded = (sig != 0) & valid_atr
        pip = pair_pip[pair]
        tp_pip = (tp_mult * atr) / pip
        sl_pip = (sl_mult * atr) / pip

        # PnL for long when traded:  label==+1 -> +tp_pip; -1 -> -sl_pip; 0 -> 0
        # PnL for short:             label==-1 -> +tp_pip; +1 -> -sl_pip; 0 -> 0
        label = pa["label"].astype(np.int64)
        pnl = np.zeros(n_lab, dtype=np.float64)
        long_mask = traded & (sig == 1)
        short_mask = traded & (sig == -1)
        pnl = np.where(long_mask & (label == 1), tp_pip, pnl)
        pnl = np.where(long_mask & (label == -1), -sl_pip, pnl)
        pnl = np.where(short_mask & (label == -1), tp_pip, pnl)
        pnl = np.where(short_mask & (label == 1), -sl_pip, pnl)

        # C-1: Kelly sizing applied as a per-bar multiplier when active.
        # When kelly_fraction==0 the multiplier is identically 1.0 so v7
        # at --no-kelly reproduces v5 / v6 numerically.
        if kelly_fraction > 0:
            p_win = pair_conf[pair]
            size = _kelly_size_vec(p_win, b_ratio, kelly_fraction)
            pnl = pnl * size  # only nonzero where traded; size also clamps to >=0
            # Trades whose Kelly says size==0 should NOT count as "traded"
            # for win/loss bookkeeping.
            traded = traded & (size > 0.0)

        pair_gross[pair] = pnl
        pair_traded[pair] = traded

    # ----- Strategy aggregation across the n_lab bars -------------------------
    eu_traded = pair_traded[base_pair]
    eu_gross = pair_gross[base_pair][eu_traded]
    eu_net = eu_gross - spread_pip

    # SELECTOR: pick the highest-confidence active pair per bar.
    # Build n_pairs x n_lab arrays and pick argmax on conf where active.
    pair_idx = list(all_pairs)
    conf_mat = np.stack([pair_conf[p] for p in pair_idx], axis=0)
    gross_mat = np.stack([pair_gross[p] for p in pair_idx], axis=0)
    traded_mat = np.stack([pair_traded[p] for p in pair_idx], axis=0)
    present_mat = np.stack([pair_arrays[p]["present"] for p in pair_idx], axis=0)

    # SELECTOR logic: ignore bars with no active signal anywhere.
    active_any = np.any(traded_mat, axis=0)
    # For each bar, set conf to -inf for non-traded pairs so argmax picks an
    # active one when at least one exists.
    conf_for_pick = np.where(traded_mat, conf_mat, -1.0)
    sel_pair_idx = np.argmax(conf_for_pick, axis=0)
    sel_gross_all = gross_mat[sel_pair_idx, np.arange(n_lab)]
    sel_gross = sel_gross_all[active_any]
    sel_net = sel_gross - spread_pip
    # Tally per-pair selection counts (only on active_any bars)
    for i, pidx in enumerate(sel_pair_idx):
        if active_any[i]:
            pair_select_counts[pair_idx[pidx]] += 1

    # EQUAL_AVG: mean of per-pair gross over pairs that traded this bar.
    # Mask non-traded pairs out, then take mean over the bars where >=1 traded.
    masked = np.where(traded_mat, gross_mat, np.nan)
    mean_per_bar = np.nanmean(masked, axis=0)  # NaN where no pair traded
    eq_active = ~np.isnan(mean_per_bar)
    eq_gross = mean_per_bar[eq_active]
    eq_net = eq_gross - spread_pip

    # RANDOM: per bar where any pair has a row, pick a random one (regardless
    # of whether it traded — matches v3 RANDOM semantics).
    any_present = np.any(present_mat, axis=0)
    rd_gross_list: list[float] = []
    for i in range(n_lab):
        if not any_present[i]:
            continue
        # Eligible = pairs with a present row at this bar
        eligible = [pidx for pidx in range(len(pair_idx)) if present_mat[pidx, i]]
        chosen = pair_idx[rng.choice(eligible)]
        if pair_traded[chosen][i]:
            rd_gross_list.append(float(pair_gross[chosen][i]))
    rd_gross = np.asarray(rd_gross_list, dtype=np.float64)
    rd_net = rd_gross - spread_pip

    # ----- Result dicts -------------------------------------------------------
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
    return results, pair_select_counts


def _sharpe(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    mu = sum(values) / len(values)
    var = sum((v - mu) ** 2 for v in values) / len(values)
    return (mu / math.sqrt(var)) if var > 0 else 0.0


# ---------------------------------------------------------------------------
# Aggregate / report (same shape as v3)
# ---------------------------------------------------------------------------


def _aggregate(fold_results: list[dict]) -> dict:
    agg: dict[str, dict] = {}
    strats = ["EURUSD_ML", "SELECTOR", "EQUAL_AVG", "RANDOM"]
    for s in strats:
        all_net = []
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
        }
    return agg


def _hdr(title: str) -> None:
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100)


def _print_comparison(
    agg: dict[str, dict], spread_pip: float, tp_mult: float, sl_mult: float
) -> None:
    _hdr(
        f"COMPARISON SUMMARY (TP_mult={tp_mult:.2f} x ATR  "
        f"SL_mult={sl_mult:.2f} x ATR  slippage={spread_pip:.2f}pip; "
        "bid/ask spread already in labels)"
    )
    print(
        f"  {'Strategy':<12} {'NetSharpe':>10} {'GrossSh':>9} "
        f"{'NetPnL(pip)':>13} {'GrossPnL(pip)':>14} "
        f"{'WinFold%':>9} {'SigRate':>9} {'Trades':>10}"
    )
    print("  " + "-" * 96)
    for s, v in agg.items():
        print(
            f"  {s:<12} {v['overall_sharpe_net']:>10.3f} {v['overall_gross_sharpe']:>9.3f} "
            f"{v['net_pnl']:>13.1f} {v['gross_pnl']:>14.1f} "
            f"{v['win_fold_pct'] * 100:>8.0f}% {v['signal_rate_mean'] * 100:>8.1f}% "
            f"{v['total_trades']:>10,}"
        )


def _print_verdict(agg: dict[str, dict], spread_pip: float) -> None:
    _hdr(f"PHASE 9.13/C-1 VERDICT (slippage={spread_pip:.2f}pip; bid/ask in labels; Kelly sizing)")
    baseline = agg["EURUSD_ML"]
    selector = agg["SELECTOR"]
    sh_delta = selector["overall_sharpe_net"] - baseline["overall_sharpe_net"]
    pnl_delta = selector["net_pnl"] - baseline["net_pnl"]
    print(
        f"  EURUSD_ML  net Sharpe={baseline['overall_sharpe_net']:.3f}  "
        f"net PnL={baseline['net_pnl']:.0f} pip"
    )
    print(
        f"  SELECTOR   net Sharpe={selector['overall_sharpe_net']:.3f}  "
        f"net PnL={selector['net_pnl']:.0f} pip   "
        f"(vs baseline: Sh {sh_delta:+.3f}, PnL {pnl_delta:+.0f})"
    )
    print("")
    print("  [Go/No-Go gate -- per docs/design/phase9_10_design_memo.md sec.6]")
    if selector["overall_sharpe_net"] >= 0.20 and selector["net_pnl"] > 0:
        print(f"  [GO]      SELECTOR net Sharpe>=0.20 AND net PnL>0 at spread={spread_pip:.2f}")
    elif selector["overall_sharpe_net"] >= 0.15:
        print(
            "  [SOFT GO] SELECTOR net Sharpe>=0.15 but <0.20 - Phase 9.13 risk lever"
            " worth trying before re-running"
        )
    else:
        print("  [NO-GO]   SELECTOR net Sharpe<0.15 - keep iterating Phase 9.12")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="compare_multipair_v4_atr",
        description="Phase 9.12/B-1 ATR-based TP/SL backtest.",
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
            "label PnL. Default 0.0 (no additional cost — bid/ask is already "
            "embedded in the label). Use ~0.2-0.5 pip to model realistic fill "
            "slippage beyond the displayed bid/ask."
        ),
    )
    parser.add_argument(
        "--kelly-fraction",
        type=float,
        default=0.25,
        help=(
            "Fractional Kelly multiplier (default 0.25 = quarter Kelly). "
            "0.0 disables Kelly (equivalent to --no-kelly). "
            "Sweep over {0.10, 0.25, 0.50, 1.00} planned in C-1."
        ),
    )
    parser.add_argument(
        "--no-kelly",
        action="store_true",
        help="Disable Kelly sizing entirely (reproduces v5 numerics).",
    )
    parser.add_argument("--retrain-interval-days", type=int, default=90)
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    if args.no_kelly:
        args.kelly_fraction = 0.0

    pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]
    base_pair = args.base_pair
    if base_pair not in pairs:
        print(f"ERROR: base-pair {base_pair!r} not in pairs list", file=sys.stderr)
        return 2

    print(f"Pairs ({len(pairs)}): {', '.join(pairs)}")
    kelly_label = (
        f"f={args.kelly_fraction:.2f} (b={args.tp_mult / args.sl_mult:.2f})"
        if args.kelly_fraction > 0
        else "DISABLED (uniform 1-unit, reproduces v5)"
    )
    print(
        f"Base: {base_pair} | TP={args.tp_mult}xATR / SL={args.sl_mult}xATR / "
        f"horizon={args.horizon} | conf>={args.conf_threshold} | "
        f"slippage={args.spread_pip}pip (bid/ask in labels) | "
        f"Kelly: {kelly_label} | "
        f"retrain every {args.retrain_interval_days}d\n"
    )

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

    print("\nBuilding features (per pair, ATR labels) ...")
    feat_dfs: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        feat = _build_pair_features(mid_dfs[pair], args.horizon, args.tp_mult, args.sl_mult)
        feat_dfs[pair] = feat
        print(f"  {pair}: {len(feat):>7,} rows  {feat[LABEL_COLUMN].notna().sum():>7,} labeled")
    feat_dfs = _build_cross_pair_features(feat_dfs, ref_pair=base_pair)

    sample = feat_dfs[base_pair]
    # Exclude raw price columns (mid OHLC, bid/ask OHLC) and the label.
    # bid/ask OHLC must be excluded because they directly determine the
    # label — including them would leak the answer into the features.
    feature_cols = [
        c
        for c in sample.columns
        if c
        not in (
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
        )
    ]
    print(f"\nFeatures per pair: {len(feature_cols)}")

    folds = _generate_folds(feat_dfs[base_pair]["timestamp"])
    retrain_schedule = _compute_retrain_schedule(folds, args.retrain_interval_days)
    print(f"Folds: {len(folds)}  retrains at: {retrain_schedule}")

    print(f"\nEvaluating {len(folds)} folds ...")
    rng = random.Random(args.seed)
    pair_models: dict[str, lgb.LGBMClassifier] = {}
    fold_results: list[dict] = []
    pair_select_totals: dict[str, int] = {p: 0 for p in pairs}

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

        results, sel_counts = _eval_fold(
            pair_models,
            pair_test_dfs,
            base_pair,
            feature_cols,
            args.conf_threshold,
            args.spread_pip,
            args.tp_mult,
            args.sl_mult,
            rng,
            kelly_fraction=args.kelly_fraction,
        )
        fold_results.append(results)
        for pair, cnt in sel_counts.items():
            pair_select_totals[pair] += cnt

        retrain_marker = "*" if fid in retrain_schedule else " "
        print(
            f"  Fold{fid:>3}{retrain_marker} "
            f"Sh(EU/SEL/EQ/RD): "
            f"{results['EURUSD_ML']['net_sharpe']:>5.2f} "
            f"{results['SELECTOR']['net_sharpe']:>5.2f} "
            f"{results['EQUAL_AVG']['net_sharpe']:>5.2f} "
            f"{results['RANDOM']['net_sharpe']:>5.2f}"
        )

    agg = _aggregate(fold_results)
    _print_comparison(agg, args.spread_pip, args.tp_mult, args.sl_mult)

    _hdr("PAIR SELECTION FREQUENCY (SELECTOR)")
    total = sum(pair_select_totals.values())
    print(f"  {'Pair':<10} {'Count':>10} {'Pct':>7}")
    print("  " + "-" * 32)
    for pair, cnt in sorted(pair_select_totals.items(), key=lambda kv: -kv[1]):
        pct = cnt / total * 100 if total > 0 else 0.0
        print(f"  {pair:<10} {cnt:>10,} {pct:>6.1f}%")

    _print_verdict(agg, args.spread_pip)
    return 0


if __name__ == "__main__":
    sys.exit(main())
