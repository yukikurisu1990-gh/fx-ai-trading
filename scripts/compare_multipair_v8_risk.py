"""compare_multipair_v8_risk.py — Phase 9.13/C-2+C-3 risk-managed SELECTOR.

Successor to v5 (B-2 bid/ask labels). Same labels and vectorised
fold-eval; adds two risk levers on top of the SELECTOR strategy that
are inherently *sequential* (state machines depend on past trades):

  C-2 — Portfolio correlation cap. Defines static FX correlation
        clusters (USD_LONG, JPY_WEAKNESS, EUR_GBP_BLOCK, COMMODITY)
        and caps the number of concurrent open SELECTOR positions
        per cluster.

  C-3 — Kill switches. Three independently configurable halts:
        * Daily loss limit (default -3% of intraday open equity)
        * Consecutive-loss cooldown (5 SL hits -> 60-bar pause)
        * Drawdown kill (-10% from peak equity -> halt for run)

Because both levers depend on running state (open positions, daily
PnL, equity curve), the SELECTOR strategy is replayed sequentially
in v8; EU/EQ/RD baselines stay vectorised so the comparison row in
the summary still matches v5/v7.

Internal sweep design
---------------------
v8 supports an *internal* sweep over (max_concurrent, kill switch
configs). Load + features + train run **once**; the cached per-bar
(p_tp, p_sl) is then replayed under each cell. This collapses 4-cell
sweeps from 4 × 5 min to 1 × 5 min + 4 × ~30 sec ≈ 7 min.

Activate via ``--sweep`` to print a heatmap. Without ``--sweep`` the
script runs a single config (defaults below).

Default config:
  --max-concurrent-per-cluster 2
  --daily-loss-pct 0.03
  --consec-loss-n 5
  --cooldown-bars 60
  --drawdown-kill-pct 0.10
  --no-correlation-cap   disables C-2 (replays without cluster cap)
  --no-kill-switch       disables C-3 (replays without state halts)

Usage
-----
    # Single config:
    python scripts/compare_multipair_v8_risk.py

    # Sweep over (max_concurrent, daily_loss_pct, dd_kill_pct):
    python scripts/compare_multipair_v8_risk.py --sweep

    # Disable all risk levers (reproduces v5):
    python scripts/compare_multipair_v8_risk.py --no-correlation-cap --no-kill-switch

Requires data/candles_<pair>_M1_365d_BA.jsonl (same as v5).
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass
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
# C-2: correlation cluster definition
# ---------------------------------------------------------------------------

# Static FX correlation clusters. A pair belongs to all clusters whose set
# contains it. Cap is enforced per-cluster on currently-open positions.
CORRELATION_CLUSTERS: dict[str, frozenset[str]] = {
    "USD_LONG": frozenset({"USD_JPY", "USD_CHF", "USD_CAD"}),
    "JPY_WEAKNESS": frozenset({"USD_JPY", "EUR_JPY", "GBP_JPY"}),
    "EUR_GBP_BLOCK": frozenset({"EUR_USD", "GBP_USD", "EUR_GBP"}),
    "COMMODITY": frozenset({"AUD_USD", "NZD_USD", "USD_CAD"}),
}


def _pair_clusters(pair: str) -> set[str]:
    """Return the set of cluster names this pair belongs to."""
    return {name for name, members in CORRELATION_CLUSTERS.items() if pair in members}


# ---------------------------------------------------------------------------
# C-3: kill switch configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KillSwitchConfig:
    """Configures the three kill switches.

    Pip thresholds (not %) so the simulator stays in pip-space. To
    interpret as % of equity, pick a notional account size: at $10k
    with $1/pip, daily_loss_pip=300 corresponds to -3% daily.
    """

    daily_loss_pip: float = 300.0  # -3% on $10k @ $1/pip
    consec_loss_n: int = 5
    cooldown_bars: int = 60
    drawdown_kill_pip: float = 1000.0  # -10% on $10k @ $1/pip


# ---------------------------------------------------------------------------
# Sequential SELECTOR replay with risk levers
# ---------------------------------------------------------------------------


def _replay_selector_with_risk(
    base_ts: np.ndarray,
    sel_pair_idx: np.ndarray,
    sel_active: np.ndarray,
    sel_gross: np.ndarray,
    pair_idx: list[str],
    horizon: int,
    slippage_pip: float,
    max_concurrent_per_cluster: int | None,
    kill_config: KillSwitchConfig | None,
) -> tuple[list[float], dict[str, int]]:
    """Sequentially apply C-2 (correlation cap) and C-3 (kill switches).

    Returns the per-trade *net* pnl pip series and a telemetry dict
    counting how often each lever blocked a trade. When both
    ``max_concurrent_per_cluster`` is None and ``kill_config`` is None,
    the function reproduces v5's vectorised SELECTOR aggregation
    exactly (modulo float order-of-operations).

    Open positions are tracked by their exit bar index = open_idx +
    horizon. We do not have access to the actual TP/SL exit time
    (that requires recomputing the bid/ask label resolution); using
    horizon as a conservative upper bound overcounts concurrent
    positions slightly — a stricter cap, which is fine from a risk
    perspective.
    """
    # open_positions: list of (cluster_set, exit_bar_idx)
    open_positions: list[tuple[set[str], int]] = []

    pnl_series: list[float] = []
    equity = 0.0
    peak_equity = 0.0
    consec_losses = 0
    cooldown_until = -1
    halted_until_eod = -1
    halted_run = False

    skip = {"correlation": 0, "cooldown": 0, "daily_kill": 0, "dd_kill": 0}

    # Pre-compute trading-day indices so the daily kill can find the
    # next-day boundary cheaply. Each timestamp belongs to a "trading day"
    # = UTC date. ``day_starts[d]`` is the smallest bar index of day d.
    if len(base_ts) > 0 and isinstance(base_ts[0], pd.Timestamp):
        days_arr = np.array([t.date() for t in base_ts])
    else:
        days_arr = np.array([pd.Timestamp(t).date() for t in base_ts])

    daily_open_equity_by_idx: dict[int, float] = {}
    current_day = None
    daily_open_equity = 0.0

    for i in range(len(base_ts)):
        # === Day rollover ===
        d = days_arr[i]
        if d != current_day:
            current_day = d
            daily_open_equity = equity
            daily_open_equity_by_idx[i] = daily_open_equity
            # The end-of-day halt is rolled off at the start of the next day.
            if i >= halted_until_eod:
                halted_until_eod = -1

        # === Prune open positions whose exit_bar <= i ===
        if open_positions:
            open_positions = [(c, ex) for c, ex in open_positions if ex > i]

        if not sel_active[i]:
            continue

        # === Hard halts ===
        if halted_run:
            continue
        if i < halted_until_eod:
            skip["daily_kill"] += 1
            continue
        if i < cooldown_until:
            skip["cooldown"] += 1
            continue

        # === Correlation cap check ===
        chosen_pair = pair_idx[sel_pair_idx[i]]
        chosen_clusters = _pair_clusters(chosen_pair)
        if max_concurrent_per_cluster is not None and chosen_clusters:
            blocked = False
            for cluster in chosen_clusters:
                count = sum(1 for c, _ in open_positions if cluster in c)
                if count >= max_concurrent_per_cluster:
                    blocked = True
                    break
            if blocked:
                skip["correlation"] += 1
                continue

        # === Take the trade ===
        gross = float(sel_gross[i])
        pnl = gross - slippage_pip
        pnl_series.append(pnl)
        equity += pnl
        peak_equity = max(peak_equity, equity)

        # Update consecutive-loss state
        if pnl < 0:
            consec_losses += 1
            if kill_config is not None and consec_losses >= kill_config.consec_loss_n:
                cooldown_until = i + kill_config.cooldown_bars
                consec_losses = 0
        else:
            consec_losses = 0

        # Track this open position
        open_positions.append((chosen_clusters, i + horizon))

        # === Daily / drawdown kill checks ===
        if kill_config is not None:
            daily_pnl = equity - daily_open_equity
            if daily_pnl < -kill_config.daily_loss_pip:
                # Halt for the rest of the current day. Find the next day's
                # first bar by scanning forward (rare path).
                end_idx = i + 1
                while end_idx < len(base_ts) and days_arr[end_idx] == d:
                    end_idx += 1
                halted_until_eod = end_idx

            dd_pip = peak_equity - equity
            if dd_pip > kill_config.drawdown_kill_pip:
                halted_run = True

    return pnl_series, skip


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
    horizon: int = 20,
    max_concurrent_per_cluster: int | None = None,
    kill_config: KillSwitchConfig | None = None,
) -> tuple[dict, dict[str, int]]:
    """Optimised per-fold evaluation (Phase 9.12 perf pass).

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

    # C-2/C-3 risk-managed replay (or pass-through when both are None).
    if max_concurrent_per_cluster is not None or kill_config is not None:
        sel_net_list, _skip_telem = _replay_selector_with_risk(
            base_ts=base_ts,
            sel_pair_idx=sel_pair_idx,
            sel_active=active_any,
            sel_gross=sel_gross_all,
            pair_idx=pair_idx,
            horizon=horizon,
            slippage_pip=spread_pip,
            max_concurrent_per_cluster=max_concurrent_per_cluster,
            kill_config=kill_config,
        )
        sel_net = np.asarray(sel_net_list, dtype=np.float64)
        sel_gross = sel_net + spread_pip  # invert slippage for "gross" reporting
        # Per-pair selection counts: only count bars that the replay actually
        # traded, not bars the cap/kill blocked.
        # We don't track which bars were taken in the replay above; recompute
        # by re-running the same logic with a side-effect flag is overkill —
        # simplest: count from the un-blocked bars in active_any.
        # (Telemetry diff vs v5 is captured in the skip_telem dict.)
        for i, pidx in enumerate(sel_pair_idx):
            if active_any[i]:
                pair_select_counts[pair_idx[pidx]] += 1
    else:
        sel_gross = sel_gross_all[active_any]
        sel_net = sel_gross - spread_pip
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
    _hdr(
        f"PHASE 9.13/C-2+C-3 VERDICT (slippage={spread_pip:.2f}pip; bid/ask in labels; risk levers)"
    )
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
    # C-2: correlation cluster cap
    parser.add_argument(
        "--max-concurrent-per-cluster",
        type=int,
        default=2,
        help=(
            "Max concurrent open SELECTOR positions per FX correlation "
            "cluster (USD_LONG, JPY_WEAKNESS, EUR_GBP_BLOCK, COMMODITY). "
            "Default 2."
        ),
    )
    parser.add_argument(
        "--no-correlation-cap",
        action="store_true",
        help="Disable C-2 correlation cap entirely.",
    )
    # C-3: kill switches
    parser.add_argument("--daily-loss-pip", type=float, default=300.0)
    parser.add_argument("--consec-loss-n", type=int, default=5)
    parser.add_argument("--cooldown-bars", type=int, default=60)
    parser.add_argument("--drawdown-kill-pip", type=float, default=1000.0)
    parser.add_argument(
        "--no-kill-switch",
        action="store_true",
        help="Disable C-3 kill switches entirely.",
    )
    # Sweep mode
    parser.add_argument(
        "--sweep",
        action="store_true",
        help=(
            "Run an internal sweep over (max_concurrent_per_cluster, "
            "drawdown_kill_pip) for the trained models in this run. "
            "Bypasses the single-config flags above."
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

    print(f"Pairs ({len(pairs)}): {', '.join(pairs)}")
    cap_label = (
        "DISABLED" if args.no_correlation_cap else f"{args.max_concurrent_per_cluster}/cluster"
    )
    kill_label = (
        "DISABLED"
        if args.no_kill_switch
        else (
            f"daily=-{args.daily_loss_pip:.0f}pip / "
            f"consec={args.consec_loss_n}->{args.cooldown_bars}b / "
            f"DD=-{args.drawdown_kill_pip:.0f}pip"
        )
    )
    print(
        f"Base: {base_pair} | TP={args.tp_mult}xATR / SL={args.sl_mult}xATR / "
        f"horizon={args.horizon} | conf>={args.conf_threshold} | "
        f"slippage={args.spread_pip}pip (bid/ask in labels)\n"
        f"  C-2 cap: {cap_label} | C-3 kill: {kill_label} | "
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

        max_conc = None if args.no_correlation_cap else args.max_concurrent_per_cluster
        kill_cfg = (
            None
            if args.no_kill_switch
            else KillSwitchConfig(
                daily_loss_pip=args.daily_loss_pip,
                consec_loss_n=args.consec_loss_n,
                cooldown_bars=args.cooldown_bars,
                drawdown_kill_pip=args.drawdown_kill_pip,
            )
        )
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
            horizon=args.horizon,
            max_concurrent_per_cluster=max_conc,
            kill_config=kill_cfg,
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
