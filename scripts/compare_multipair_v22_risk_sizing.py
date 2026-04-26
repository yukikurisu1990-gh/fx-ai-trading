"""compare_multipair_v22_risk_sizing.py - Phase 9.X-I/I-1 risk-based sizing.

Cloned from v19 (causal-fixed). Adds:
- Per-trade size_units = floor(balance × risk_pct / sl_pips / min_lot) × min_lot
  (PositionSizerService formula, M10).
- ¥-based PnL series alongside the existing pip series.
- New summary columns: Sharpe(JPY), PnL(JPY), MaxDD(JPY), DD%PnL(JPY).

Without --enable-risk-sizing, v22 reproduces v19 behaviour exactly.

Hypothesis: risk-equalised sizing reduces ¥-PnL variance without
materially changing mean → Sharpe(JPY) > Sharpe(pip). Estimated
+10-20% Sharpe lift in ¥ terms.

Original v19 docstring follows.

compare_multipair_v19_causal.py - Phase 9.X-E/L-1 causal multi-TF fix.

Cloned from v18 (Phase 9.X-D crossasset). The ONLY change is in
``_add_multi_tf_extended_features``: every resampled feature is shift(1)'d
BEFORE reindex(method="ffill"), restoring the lookahead-safe pattern
already used by ``_add_upper_tf``.

Without this shift, the daily bar labelled 2026-01-15 (containing the
23:55 close) leaks into m5 bars at e.g. 10:00 same day — ~14h of
in-bar lookahead. v19 quantifies the inflation in Phase 9.X-B's claimed
+mtf Sharpe 0.174 (PnL 15,118, DD%PnL 1.8%).

Production J-5 ``_compute_mtf_features`` is already causal (operates on
candles pre-truncated to ``timestamp < as_of_time``), so this fix
applies ONLY to the backtest pipeline.

Original v14 docstring follows.

compare_multipair_v14_topk.py - Phase 9.19 SELECTOR multi-pick (Top-K).

Successor to v13 ensemble. Identical load + features + cross-pair + train
pipeline; the difference is in the **SELECTOR rule**:

    v13: argmax(confidence) over (pair x strategy) → 1 trade per bar
    v14: argpartition top-K           → K trades per bar (sum of PnLs)

Optionally restrict picks via diversification-aware filter — at most one
pick per currency family (USD/EUR/GBP/AUD/NZD/CHF/JPY/CAD), greedy fill
in confidence-descending order.

Hypothesis (Phase 9.19 design memo H-1): if K-th picks are sufficiently
independent (ρ ≤ 0.4), Sharpe scales by sqrt(K).

  K   ρ=0.0   ρ=0.3   ρ=0.5   ρ=0.7
  1   0.160   0.160   0.160   0.160   (baseline)
  2   0.226   0.198   0.184   0.173
  3   0.277   0.224   0.196   0.179
  5   0.358   0.252   0.207   0.183

Cells (internal sweep). Each cell is evaluated at every K in --top-ks:
  - lgbm_only    : only LightGBM signals participate (= v9 baseline at K=1)
  - lgbm+mr+bo   : full ensemble (Phase 9.17 best PnL cell)

CLI
---
    --top-ks LIST            # comma-separated K values (default: 1,2,3,5)
    --ensemble-cells LIST    # comma-separated cell names
    --diversify-by-currency  # one pick per currency family per bar

Phase 9.19 verdict gates (PnL-priority + diversification gate):
  GO          - PnL >= 1.30 x baseline AND Sharpe >= 0.18 AND DD%PnL <= 5% AND mean ρ <= 0.5
  PARTIAL GO  - PnL >= 1.20 x baseline AND Sharpe >= baseline (ρ 0.5-0.7)
  STRETCH GO  - any (K, variant) cell reaches Sharpe >= 0.20 (clears Phase 9.11)
  NO ADOPT    - PnL < baseline OR DD%PnL > 5% OR mean ρ > 0.7

Baseline = Phase 9.16 production default (20-pair v9 spread bundle,
SELECTOR Sharpe 0.160, PnL 8,157 pip, DD%PnL 2.5%). The K=1 lgbm_only
cell must reproduce this exactly.

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

# Phase 9.X-I/I-1: pip-value-per-unit in JPY for ¥-based PnL.
# Derived from approximate cross-rates (USD/JPY≈150, GBP/JPY≈195, etc).
# 1 pip × 1 unit = pip_size_quote × quote_to_jpy. For a mini lot (1,000
# units), multiply by 1,000 to get ¥ per pip per mini lot.
_PIP_VALUE_JPY_PER_UNIT: dict[str, float] = {
    # Quote = USD: 0.0001 USD × 150 JPY/USD = 0.015 JPY per unit.
    "EUR_USD": 0.015,
    "GBP_USD": 0.015,
    "AUD_USD": 0.015,
    "NZD_USD": 0.015,
    # Quote = JPY: 0.01 JPY per unit (direct).
    "USD_JPY": 0.01,
    "EUR_JPY": 0.01,
    "GBP_JPY": 0.01,
    "AUD_JPY": 0.01,
    "NZD_JPY": 0.01,
    "CHF_JPY": 0.01,
    # Quote = CHF (~165 JPY): 0.0001 × 165 = 0.0165.
    "USD_CHF": 0.0165,
    "EUR_CHF": 0.0165,
    "GBP_CHF": 0.0165,
    # Quote = CAD (~110 JPY): 0.0001 × 110 = 0.011.
    "USD_CAD": 0.011,
    "EUR_CAD": 0.011,
    "AUD_CAD": 0.011,
    # Quote = GBP (~195 JPY): 0.0001 × 195 = 0.0195.
    "EUR_GBP": 0.0195,
    "GBP_AUD": 0.0001 * 100,  # quote=AUD ~100 JPY → 0.010 JPY per unit
    # Quote = AUD (~100 JPY): 0.0001 × 100 = 0.010.
    "EUR_AUD": 0.010,
    # Quote = NZD (~90 JPY): 0.0001 × 90 = 0.009.
    "AUD_NZD": 0.009,
}


def _compute_size_units(
    balance_jpy: float,
    risk_pct: float,
    sl_pip: float,
    pip_value_jpy_per_unit: float,
    min_lot: int,
) -> int:
    """Phase 9.X-I/I-1 risk-based sizing (pip-value-aware variant).

    Worst-case loss if SL hits = N_units × pip_value × sl_pip ≤ risk_amount.
    → N_units = floor(balance × risk_pct / 100 / pip_value / sl_pip / min_lot) × min_lot

    Note: PositionSizerService (src/) has the M10 placeholder formula
    that assumes 1 pip = 1 unit-currency, which is only correct for a
    JPY-quoted pair if the account is in JPY. For backtest accuracy
    across the 20-pair universe we use the correct pip-value-aware
    formula here, and Phase 7 wiring will replace the production
    PositionSizer with the same formula.
    """
    if (
        sl_pip <= 0
        or risk_pct <= 0
        or balance_jpy <= 0
        or min_lot <= 0
        or pip_value_jpy_per_unit <= 0
    ):
        return 0
    risk_amount = balance_jpy * risk_pct / 100.0
    raw_units = risk_amount / (pip_value_jpy_per_unit * sl_pip)
    size = int(raw_units // min_lot) * min_lot
    return size if size >= min_lot else 0


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


# Phase 9.X-B feature groups. Each is OHLC-only (no new data dependency).


_VOL_CLUSTER_COLS: tuple[str, ...] = (
    "real_var_5",
    "real_var_20",
    "vol_of_vol_20",
    "var_ratio_5_20",
    "ewma_var_30",
    "ewma_var_60",
)


def _add_vol_cluster_features(df: pd.DataFrame) -> pd.DataFrame:
    """Phase 9.X-B Group A: volatility clustering features.

    Captures GARCH-like dynamics (variance changes over time) that the
    static rolling ATR_14 does not encode. All from close-to-close
    log-returns; OHLC-only.
    """
    df = df.copy()
    close = df["close"].astype(np.float64)
    logret = np.log(close / close.shift(1))
    # Realized variance at two windows.
    rv5 = (logret**2).rolling(5, min_periods=2).sum()
    rv20 = (logret**2).rolling(20, min_periods=5).sum()
    df["real_var_5"] = rv5
    df["real_var_20"] = rv20
    # Volatility of volatility: rolling std of rv5.
    df["vol_of_vol_20"] = rv5.rolling(20, min_periods=5).std(ddof=0)
    # Variance ratio (Lo-MacKinlay) — short vs long.
    df["var_ratio_5_20"] = (rv5 / 5) / (rv20 / 20).replace(0, np.nan)
    # EWMA conditional variance at two half-lives.
    df["ewma_var_30"] = (logret**2).ewm(halflife=30, min_periods=10).mean()
    df["ewma_var_60"] = (logret**2).ewm(halflife=60, min_periods=20).mean()
    return df


_HIGHER_MOMENT_COLS: tuple[str, ...] = (
    "skew_20",
    "kurt_20",
    "autocorr_lag1",
    "autocorr_lag5",
)


def _add_higher_moment_features(df: pd.DataFrame) -> pd.DataFrame:
    """Phase 9.X-B Group B: higher-order moments + persistence.

    Skewness/kurtosis capture distributional asymmetry; autocorrelation
    captures persistence (trending vs mean-reverting). All from
    close-to-close log-returns.
    """
    df = df.copy()
    close = df["close"].astype(np.float64)
    logret = np.log(close / close.shift(1))
    df["skew_20"] = logret.rolling(20, min_periods=10).skew()
    df["kurt_20"] = logret.rolling(20, min_periods=10).kurt()
    # Rolling Pearson autocorrelation lag-k — vectorised via rolling.corr
    # of (logret, logret.shift(k)). The .apply(lambda) pure-Python form
    # was prohibitively slow at 20-pair × 500k-bar scale.
    df["autocorr_lag1"] = logret.rolling(20, min_periods=10).corr(logret.shift(1))
    df["autocorr_lag5"] = logret.rolling(20, min_periods=10).corr(logret.shift(5))
    return df


_MTF_EXTENDED_COLS: tuple[str, ...] = (
    "d1_return_3",
    "d1_range_pct",
    "d1_atr_14",
    "w1_return_1",
    "w1_range_pct",
    "h4_atr_14",
)


def _add_multi_tf_extended_features(df_m1: pd.DataFrame) -> pd.DataFrame:
    """Phase 9.X-B Group C: deep multi-timeframe extension.

    Phase 9.4 already added m5/m15/h1 features. This group extends to
    4h, daily, weekly bars — slower-cadence regime indicators.

    Phase 9.X-E/L-1 lookahead fix: every resampled feature is shift(1)'d
    BEFORE reindex(method="ffill"), matching the _add_upper_tf pattern.
    Without the shift, the daily bar labelled 2026-01-15 (which contains
    the 23:55 close) would leak into m5 bars at e.g. 10:00 same day.
    With shift(1), the daily bar's value only becomes visible from the
    START of 2026-01-16 onwards — strictly causal.
    """
    df = df_m1.copy()
    idx = df.index
    if not isinstance(idx, pd.DatetimeIndex):
        idx = pd.DatetimeIndex(idx)
        df.index = idx

    def _resample_ohlc(rule: str) -> pd.DataFrame:
        return (
            df[["open", "high", "low", "close"]]
            .resample(rule)
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna(how="all")
        )

    h4 = _resample_ohlc("4h")
    d1 = _resample_ohlc("1D")
    w1 = _resample_ohlc("1W")

    h4_pc = h4["close"].shift(1)
    h4_tr = pd.concat(
        [h4["high"] - h4["low"], (h4["high"] - h4_pc).abs(), (h4["low"] - h4_pc).abs()],
        axis=1,
    ).max(axis=1)
    h4_atr = h4_tr.rolling(14, min_periods=4).mean()

    d1_pc = d1["close"].shift(1)
    d1_tr = pd.concat(
        [d1["high"] - d1["low"], (d1["high"] - d1_pc).abs(), (d1["low"] - d1_pc).abs()],
        axis=1,
    ).max(axis=1)
    d1_atr = d1_tr.rolling(14, min_periods=4).mean()

    h4_raw = pd.DataFrame(
        {"h4_atr_14": h4_atr},
        index=h4.index,
    )
    h4_features = h4_raw.shift(1).reindex(idx, method="ffill")

    d1_raw = pd.DataFrame(
        {
            "d1_return_3": d1["close"].pct_change(3),
            "d1_range_pct": (d1["high"] - d1["low"]) / d1["close"].replace(0, np.nan),
            "d1_atr_14": d1_atr,
        },
        index=d1.index,
    )
    d1_features = d1_raw.shift(1).reindex(idx, method="ffill")

    w1_raw = pd.DataFrame(
        {
            "w1_return_1": w1["close"].pct_change(1),
            "w1_range_pct": (w1["high"] - w1["low"]) / w1["close"].replace(0, np.nan),
        },
        index=w1.index,
    )
    w1_features = w1_raw.shift(1).reindex(idx, method="ffill")

    return pd.concat([df, h4_features, d1_features, w1_features], axis=1)


# Phase 9.X-D Group "dxy": cross-asset features built from existing
# 20-pair feed. DXY-equivalent uses adjusted Fed weights (no SEK).
_DXY_WEIGHTS: dict[str, float] = {
    "EUR_USD": -0.601,
    "GBP_USD": -0.124,
    "USD_JPY": +0.142,
    "USD_CAD": +0.095,
    "USD_CHF": +0.038,
}

_DXY_COLS: tuple[str, ...] = (
    "dxy_return_5",
    "dxy_return_20",
    "dxy_return_60",
    "dxy_volatility_20",
    "dxy_z_score_50",
    "dxy_ma_cross_short",
    "dxy_correlation_pair_20",
    "dxy_pair_alignment",
)


def _compute_dxy_log_return(
    pair_log_returns: dict[str, pd.Series],
) -> pd.Series:
    """Phase 9.X-D: synthetic DXY log-return basket from existing pairs.

    DXY rises when USD strengthens. EUR/USD and GBP/USD have NEGATIVE
    weights (USD on the quote side); USD/JPY, USD/CAD, USD/CHF have
    POSITIVE weights (USD on the base side).

    Returns NaN where any required pair is missing.
    """
    parts: list[pd.Series] = []
    for pair, weight in _DXY_WEIGHTS.items():
        ret = pair_log_returns.get(pair)
        if ret is None:
            return pd.Series(dtype=np.float64)
        parts.append(weight * ret)
    return pd.concat(parts, axis=1).sum(axis=1, skipna=False)


_PHASE_X_B_GROUPS: dict[str, tuple[str, ...]] = {
    "vol": _VOL_CLUSTER_COLS,
    "moments": _HIGHER_MOMENT_COLS,
    "mtf": _MTF_EXTENDED_COLS,
    # Phase 9.X-D dxy group is computed in _build_cross_pair_features (per-pair
    # context requires aligning across pairs); listed here for CLI validation.
    "dxy": _DXY_COLS,
}


def _build_pair_features(
    df_m1: pd.DataFrame,
    horizon: int,
    tp_mult: float,
    sl_mult: float,
    instrument: str,
    enable_groups: frozenset[str] = frozenset(),
) -> pd.DataFrame:
    df = _add_m1_features(df_m1)
    df = _add_upper_tf(df, "5min", "m5")
    df = _add_upper_tf(df, "15min", "m15")
    df = _add_upper_tf(df, "1h", "h1")
    # Phase 9.15/F-1: orthogonal features.
    df = _add_orthogonal_features(df, instrument)
    # Phase 9.X-B feature groups (opt-in via enable_groups).
    if "mtf" in enable_groups:
        df = _add_multi_tf_extended_features(df)
    if "vol" in enable_groups:
        df = _add_vol_cluster_features(df)
    if "moments" in enable_groups:
        df = _add_higher_moment_features(df)
    # Phase 9.17: single bid/ask-aware label at the global mid bucket.
    df = _add_labels_bidask(df, horizon, tp_mult, sl_mult)
    df = df.iloc[50:].copy()
    df = df.reset_index()
    return df


def _build_cross_pair_features(
    feat_dfs: dict[str, pd.DataFrame],
    ref_pair: str = "EUR_USD",
    corr_window: int = 20,
    enable_groups: frozenset[str] = frozenset(),
) -> dict[str, pd.DataFrame]:
    ref_ts_series = feat_dfs[ref_pair].set_index("timestamp")
    ret_map: dict[str, pd.Series] = {}
    log_ret_map: dict[str, pd.Series] = {}
    rsi_map: dict[str, pd.Series] = {}
    for pair, df in feat_dfs.items():
        aligned = df.set_index("timestamp").reindex(ref_ts_series.index, method="ffill")
        ret_map[pair] = aligned["last_close"].pct_change(1)
        log_ret_map[pair] = np.log(aligned["last_close"] / aligned["last_close"].shift(1))
        rsi_map[pair] = aligned["rsi_14"]
    ret_df = pd.DataFrame(ret_map)
    rsi_df = pd.DataFrame(rsi_map)
    basket_ret = ret_df.mean(axis=1)

    # Phase 9.X-D dxy: synthetic DXY log-return + level + derived stats.
    # Computed once for the entire universe; per-pair correlation/alignment
    # features are added per-pair below.
    dxy_log_ret: pd.Series | None = None
    dxy_level: pd.Series | None = None
    dxy_features: pd.DataFrame | None = None
    if "dxy" in enable_groups:
        dxy_log_ret = _compute_dxy_log_return(log_ret_map)
        # Synthetic DXY level — exp(cumulative log-returns) starting at 100.
        # Initial NaN (first row) treated as 0 cumulative shift.
        cum = dxy_log_ret.fillna(0).cumsum()
        dxy_level = 100.0 * np.exp(cum)

        # Pre-compute non-pair-specific DXY features.
        dxy_ret_5 = dxy_log_ret.rolling(5, min_periods=2).sum()
        dxy_ret_20 = dxy_log_ret.rolling(20, min_periods=5).sum()
        dxy_ret_60 = dxy_log_ret.rolling(60, min_periods=10).sum()
        dxy_vol_20 = dxy_log_ret.rolling(20, min_periods=5).std(ddof=0)
        dxy_mean_50 = dxy_level.rolling(50, min_periods=10).mean()
        dxy_std_50 = dxy_level.rolling(50, min_periods=10).std(ddof=0)
        dxy_z_50 = (dxy_level - dxy_mean_50) / dxy_std_50.replace(0, np.nan)
        dxy_ma_5 = dxy_level.rolling(5, min_periods=2).mean()
        dxy_ma_20 = dxy_level.rolling(20, min_periods=5).mean()
        dxy_ma_cross = np.sign(dxy_ma_5 - dxy_ma_20)
        dxy_features = pd.DataFrame(
            {
                "dxy_return_5": dxy_ret_5,
                "dxy_return_20": dxy_ret_20,
                "dxy_return_60": dxy_ret_60,
                "dxy_volatility_20": dxy_vol_20,
                "dxy_z_score_50": dxy_z_50,
                "dxy_ma_cross_short": dxy_ma_cross,
            },
            index=ref_ts_series.index,
        )

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

        # Phase 9.X-D dxy: per-pair correlation + alignment features.
        if "dxy" in enable_groups and dxy_log_ret is not None:
            pair_log_ret = log_ret_map[pair]
            dxy_corr_pair = pair_log_ret.rolling(corr_window, min_periods=5).corr(dxy_log_ret)
            # Alignment: for USD-quote pairs (EUR/USD, GBP/USD, AUD/USD, etc.),
            # rising DXY ⇒ pair falling. For USD-base pairs (USD/JPY, USD/CHF,
            # USD/CAD, etc.) rising DXY ⇒ pair rising. Compute as:
            #   sign(dxy_return_5) × sign(pair_return_5) — should match if aligned.
            pair_ret_5 = pair_log_ret.rolling(5, min_periods=2).sum()
            dxy_alignment = np.sign(dxy_ret_5) * np.sign(pair_ret_5)
            xp = xp.assign(
                **{c: dxy_features[c] for c in dxy_features.columns},
                dxy_correlation_pair_20=dxy_corr_pair,
                dxy_pair_alignment=dxy_alignment,
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


def _mr_signal_vec(
    rsi: np.ndarray, bb_pct_b: np.ndarray, conf_threshold: float = 0.0
) -> tuple[np.ndarray, np.ndarray]:
    """Phase 9.17 G-1 MeanReversionStrategy — vectorised.

    Combined-AND logic:
      long  : rsi <= 30 AND bb_pct_b <= 0.10
      short : rsi >= 70 AND bb_pct_b >= 0.90

    Confidence = mean of normalised RSI- and BB-distances from threshold.
    Mirrors `MeanReversionStrategy.evaluate` in
    src/fx_ai_trading/services/strategies/mean_reversion.py.

    Phase 9.17b/I-1: ``conf_threshold`` post-filter — bars where rule-met
    confidence < threshold are suppressed to no-trade. Default 0.0
    preserves Phase 9.17 G-1 behavior.
    """
    long_mask = (rsi <= _MR_RSI_OVERSOLD) & (bb_pct_b <= _MR_BB_LOWER)
    short_mask = (rsi >= _MR_RSI_OVERBOUGHT) & (bb_pct_b >= _MR_BB_UPPER)

    rsi_long_conf = np.clip((_MR_RSI_OVERSOLD - rsi) / _MR_RSI_OVERSOLD, 0.0, 1.0)
    bb_long_conf = np.clip((_MR_BB_LOWER - bb_pct_b) / _MR_BB_LOWER, 0.0, 1.0)
    long_conf_raw = (rsi_long_conf + bb_long_conf) / 2.0

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
    short_conf_raw = (rsi_short_conf + bb_short_conf) / 2.0

    if conf_threshold > 0.0:
        long_mask = long_mask & (long_conf_raw >= conf_threshold)
        short_mask = short_mask & (short_conf_raw >= conf_threshold)

    sig = np.zeros(rsi.shape, dtype=np.int8)
    sig[long_mask] = 1
    sig[short_mask] = -1

    conf = np.zeros(rsi.shape, dtype=np.float64)
    conf = np.where(long_mask, long_conf_raw, conf)
    conf = np.where(short_mask, short_conf_raw, conf)
    return sig, conf


def _bo_signal_vec(
    last_close: np.ndarray,
    bb_upper: np.ndarray,
    bb_lower: np.ndarray,
    ema_12: np.ndarray,
    ema_26: np.ndarray,
    atr: np.ndarray,
    conf_threshold: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Phase 9.17 G-2 BreakoutStrategy — vectorised.

    Range break + EMA trend confirmation:
      long  : last_close > bb_upper AND ema_12 > ema_26
      short : last_close < bb_lower AND ema_12 < ema_26

    Confidence = ATR-normalised distance from broken band, capped at
    1.0 at `_BO_STRENGTH_FULL_ATR`. Mirrors `BreakoutStrategy.evaluate`
    in src/fx_ai_trading/services/strategies/breakout.py.

    Phase 9.17b/I-1: ``conf_threshold`` post-filter — bars where rule-met
    confidence < threshold are suppressed to no-trade. Default 0.0
    preserves Phase 9.17 G-2 behavior.
    """
    valid_atr = np.isfinite(atr) & (atr > 0)
    long_break = last_close > bb_upper
    short_break = last_close < bb_lower
    trend_up = ema_12 > ema_26
    trend_down = ema_12 < ema_26
    long_mask = long_break & trend_up & valid_atr
    short_mask = short_break & trend_down & valid_atr

    safe_atr = np.where(valid_atr, atr, 1.0)
    long_strength = np.where(long_mask, (last_close - bb_upper) / safe_atr, 0.0)
    short_strength = np.where(short_mask, (bb_lower - last_close) / safe_atr, 0.0)
    if _BO_STRENGTH_FULL_ATR > 0:
        long_conf_raw = np.clip(long_strength / _BO_STRENGTH_FULL_ATR, 0.0, 1.0)
        short_conf_raw = np.clip(short_strength / _BO_STRENGTH_FULL_ATR, 0.0, 1.0)
    else:
        long_conf_raw = np.where(long_mask, 1.0, 0.0)
        short_conf_raw = np.where(short_mask, 1.0, 0.0)

    if conf_threshold > 0.0:
        long_mask = long_mask & (long_conf_raw >= conf_threshold)
        short_mask = short_mask & (short_conf_raw >= conf_threshold)

    sig = np.zeros(last_close.shape, dtype=np.int8)
    sig[long_mask] = 1
    sig[short_mask] = -1

    conf = np.zeros(last_close.shape, dtype=np.float64)
    conf = np.where(long_mask, long_conf_raw, conf)
    conf = np.where(short_mask, short_conf_raw, conf)
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
    strategy_conf_threshold: float = 0.0,
    top_k: int = 1,
    diversify_by_currency: bool = False,
    enable_risk_sizing: bool = False,
    risk_pct: float = 1.0,
    initial_balance_jpy: float = 300_000.0,
    min_lot: int = 1000,
) -> tuple[dict, dict[str, int], dict[str, int], dict[str, list[float]], list[float]]:
    """Phase 9.19 SELECTOR multi-pick (Top-K) per-fold evaluation.

    Computes per-pair per-strategy signals, then runs SELECTOR over the
    cartesian (pair x strategy) candidate space (only strategies in
    `cell_strategies` are eligible).

    All strategies use the same triple-barrier mid-bucket label
    (TP=tp_mult x ATR / SL=sl_mult x ATR) for PnL — design memo §13
    default 4 (apples-to-apples PnL across the cell).

    Phase 9.19: SELECTOR takes top-K candidates per bar (K=1 reproduces
    Phase 9.17 G-3 baseline behavior). PnL is summed across the K picks.
    When ``diversify_by_currency`` is True, picks are filtered greedily
    in confidence-descending order with a per-currency-family cap of 1.

    Returns
    -------
    results : dict
        Per-strategy summary keyed by EURUSD_ML / SELECTOR / EQUAL_AVG / RANDOM.
    pair_select_counts : dict[str, int]
        How many bars SELECTOR picked each pair (counted across all K slots).
    strategy_select_counts : dict[str, int]
        How many bars SELECTOR picked each strategy (counted across all K slots).
    per_strategy_pnl_series : dict[str, list[float]]
        Per-bar mean gross PnL across pairs that traded under each strategy.
        NaN where the strategy did not trade. Used to compute the
        inter-strategy correlation matrix.
    per_pick_sharpe : list[float]
        Per-rank fold Sharpe (rank 1 .. K). For naive top-K only;
        diversified variant returns rank-by-acceptance-order.
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
        return (
            empty,
            pair_select_counts,
            strategy_select_counts,
            per_strategy_pnl_series,
            [],
        )

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
    # Phase 9.X-I: per-pair sl_pip array (for ¥-based sizing post-SELECTOR).
    pair_sl_pip: dict[str, np.ndarray] = {}

    for pair in all_pairs:
        pa = pair_arrays[pair]
        atr = pa["atr"]
        valid_atr = np.isfinite(atr) & (atr > 0)
        present = pa["present"]
        pip = pair_pip[pair]
        label = pa["label"].astype(np.int64)
        tp_pip = (tp_mult * atr) / pip
        sl_pip = (sl_mult * atr) / pip
        pair_sl_pip[pair] = sl_pip

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
            sig_m, conf_m = _mr_signal_vec(
                pa["rsi"], pa["bb_pct_b"], conf_threshold=strategy_conf_threshold
            )
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
                conf_threshold=strategy_conf_threshold,
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

    # ----- SELECTOR over (pair, strategy) — Phase 9.19 Top-K -----
    candidates: list[tuple[str, str]] = [(p, s) for p in all_pairs for s in cell_strategies]
    n_cands = len(candidates)
    conf_mat = np.stack([pair_strat_conf[c] for c in candidates], axis=0)
    gross_mat = np.stack([pair_strat_gross[c] for c in candidates], axis=0)
    traded_mat = np.stack([pair_strat_traded[c] for c in candidates], axis=0)

    conf_for_pick = np.where(traded_mat, conf_mat, -1.0)
    k_use = min(top_k, n_cands)

    # Per-bar SELECTOR pick: array of selected candidate indices per rank.
    # For naive top-K we use argpartition; for diversified we do per-bar
    # greedy fill. In both cases ``sel_cand_idx_per_rank[r, b]`` is the
    # candidate idx for rank-r pick at bar b, or -1 if no rank-r pick.
    sel_cand_idx_per_rank = np.full((k_use, n_lab), -1, dtype=np.int64)

    if not diversify_by_currency:
        # Naive top-K: argpartition O(N) for partial sort.
        if k_use == 1:
            sel_cand_idx_per_rank[0, :] = np.argmax(conf_for_pick, axis=0)
            # Mark slots where nothing was actually traded as -1.
            sel_traded = traded_mat[sel_cand_idx_per_rank[0], np.arange(n_lab)]
            sel_cand_idx_per_rank[0, ~sel_traded] = -1
        else:
            # Negate to get descending; partition picks K smallest -> largest by neg conf.
            partition_idx = np.argpartition(-conf_for_pick, k_use - 1, axis=0)[:k_use, :]
            # Sort each bar's K picks by descending confidence for clean per-rank diagnostics.
            partition_conf = np.take_along_axis(conf_for_pick, partition_idx, axis=0)
            order = np.argsort(-partition_conf, axis=0)
            sel_cand_idx_per_rank = np.take_along_axis(partition_idx, order, axis=0)
            # Mark untraded slots as -1.
            for r in range(k_use):
                cidx_r = sel_cand_idx_per_rank[r]
                traded_r = traded_mat[cidx_r, np.arange(n_lab)]
                sel_cand_idx_per_rank[r, ~traded_r] = -1
    else:
        # Diversification-aware: per-bar greedy fill with per-currency caps.
        pair_to_currencies: dict[str, tuple[str, str]] = {p: tuple(p.split("_")) for p in all_pairs}
        sorted_idx = np.argsort(-conf_for_pick, axis=0)  # descending; (n_cands, n_lab)
        for b in range(n_lab):
            used_curr: set[str] = set()
            slot = 0
            for rank_pos in range(n_cands):
                cidx = int(sorted_idx[rank_pos, b])
                if not bool(traded_mat[cidx, b]):
                    continue
                pair, _strat = candidates[cidx]
                c1, c2 = pair_to_currencies[pair]
                if c1 in used_curr or c2 in used_curr:
                    continue
                sel_cand_idx_per_rank[slot, b] = cidx
                used_curr.add(c1)
                used_curr.add(c2)
                slot += 1
                if slot >= k_use:
                    break

    # Compute per-rank gross PnL (zero where no pick at that rank for the bar).
    per_rank_gross: list[np.ndarray] = []
    for r in range(k_use):
        cidx_r = sel_cand_idx_per_rank[r]
        valid = cidx_r >= 0
        rank_gross = np.zeros(n_lab, dtype=np.float64)
        if valid.any():
            rank_gross[valid] = gross_mat[cidx_r[valid], np.arange(n_lab)[valid]]
        per_rank_gross.append(rank_gross)
        # Tally per-pair, per-strategy counts for this rank.
        for b in np.flatnonzero(valid):
            picked_pair, picked_strat = candidates[int(cidx_r[b])]
            pair_select_counts[picked_pair] += 1
            strategy_select_counts[picked_strat] += 1

    # Aggregate: sum of gross PnL across the K picks per bar.
    sel_gross_all = np.sum(per_rank_gross, axis=0) if per_rank_gross else np.zeros(n_lab)
    # SELECTOR active when at least one rank picked.
    sel_active = np.any(sel_cand_idx_per_rank >= 0, axis=0)
    sel_gross = sel_gross_all[sel_active]
    # Net subtracts K spreads (one per actual pick).
    pick_count_per_bar = (sel_cand_idx_per_rank >= 0).sum(axis=0)
    sel_net = sel_gross - spread_pip * pick_count_per_bar[sel_active]

    # ----- Phase 9.X-I/I-1 ¥-based PnL series (risk-based sizing) -----
    # Replays the SELECTOR's K-pick decisions but applies per-trade
    # size_units = floor(balance × risk_pct / sl_pip / min_lot) × min_lot
    # before converting pip PnL → JPY. Disabled by default; reproduces
    # the v19 pip-only path when enable_risk_sizing=False.
    sel_net_jpy: np.ndarray | None = None
    if enable_risk_sizing:
        per_rank_jpy: list[np.ndarray] = []
        for r in range(k_use):
            cidx_r = sel_cand_idx_per_rank[r]
            valid = cidx_r >= 0
            rank_jpy = np.zeros(n_lab, dtype=np.float64)
            for b in np.flatnonzero(valid):
                cidx = int(cidx_r[b])
                pair, _strat = candidates[cidx]
                sl_b = float(pair_sl_pip[pair][b])
                pip_value = _PIP_VALUE_JPY_PER_UNIT.get(pair, 0.015)  # fallback
                size_b = _compute_size_units(
                    initial_balance_jpy, risk_pct, sl_b, pip_value, min_lot
                )
                if size_b == 0:
                    continue
                pip_pnl = float(gross_mat[cidx, b]) - spread_pip
                rank_jpy[b] = pip_pnl * pip_value * size_b
            per_rank_jpy.append(rank_jpy)
        sel_jpy_all = np.sum(per_rank_jpy, axis=0) if per_rank_jpy else np.zeros(n_lab)
        sel_net_jpy = sel_jpy_all[sel_active]

    # Per-pick (per-rank) Sharpe diagnostic: across folds, what is the
    # standalone Sharpe of just the rank-r pick? Useful to detect dilution.
    per_pick_sharpe: list[float] = []
    for r in range(k_use):
        cidx_r = sel_cand_idx_per_rank[r]
        valid = cidx_r >= 0
        rank_gross = per_rank_gross[r][valid]
        rank_net = rank_gross - spread_pip
        per_pick_sharpe.append(_sharpe(rank_net.tolist()) if rank_net.size > 1 else 0.0)

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

    # Phase 9.X-I/I-1: attach ¥-based stats to SELECTOR when risk-sizing on.
    if enable_risk_sizing and sel_net_jpy is not None and sel_net_jpy.size > 0:
        results["SELECTOR"]["net_sharpe_jpy"] = _sharpe(sel_net_jpy.tolist())
        results["SELECTOR"]["net_pnl_jpy"] = float(sel_net_jpy.sum())
        results["SELECTOR"]["net_pnls_jpy"] = sel_net_jpy.tolist()
        # Phase 9.X-K: per-bar JPY series + timestamps for daily Sharpe.
        results["SELECTOR"]["bar_pnls_jpy"] = sel_jpy_all.tolist()
        results["SELECTOR"]["bar_timestamps_ns"] = [int(pd.Timestamp(t).value) for t in base_ts]
    else:
        results["SELECTOR"]["net_sharpe_jpy"] = 0.0
        results["SELECTOR"]["net_pnl_jpy"] = 0.0
        results["SELECTOR"]["net_pnls_jpy"] = []
        results["SELECTOR"]["bar_pnls_jpy"] = []
        results["SELECTOR"]["bar_timestamps_ns"] = []

    return (
        results,
        pair_select_counts,
        strategy_select_counts,
        per_strategy_pnl_series,
        per_pick_sharpe,
    )


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


def _aggregate(fold_results: list[dict], initial_balance_jpy: float = 300_000.0) -> dict:
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
        max_dd = _max_drawdown(all_net)
        dd_pct_of_pnl = min(999.0, 100.0 * max_dd / net_pnl) if net_pnl > 0 else 999.0
        all_net_jpy: list[float] = []
        for fr in fold_results:
            all_net_jpy.extend(fr[s].get("net_pnls_jpy", []) or [])
        net_pnl_jpy = float(sum(all_net_jpy))
        max_dd_jpy = _max_drawdown(all_net_jpy)
        dd_pct_of_pnl_jpy = (
            min(999.0, 100.0 * max_dd_jpy / net_pnl_jpy) if net_pnl_jpy > 0 else 999.0
        )
        sharpe_jpy = _sharpe(all_net_jpy) if len(all_net_jpy) >= 2 else 0.0
        daily_metrics = _compute_daily_metrics(fold_results, s, initial_balance_jpy)

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
            "overall_sharpe_jpy": sharpe_jpy,
            "net_pnl_jpy": net_pnl_jpy,
            "max_drawdown_jpy": max_dd_jpy,
            "max_dd_pct_of_pnl_jpy": dd_pct_of_pnl_jpy,
            **daily_metrics,
        }
    return agg


def _compute_daily_metrics(
    fold_results: list[dict],
    strategy: str,
    initial_balance_jpy: float,
) -> dict:
    """Phase 9.X-K daily-bar aggregation -> annualized Sharpe + equity max DD."""
    bar_pnls: list[float] = []
    bar_ts_ns: list[int] = []
    for fr in fold_results:
        bp = fr.get(strategy, {}).get("bar_pnls_jpy", []) or []
        bt = fr.get(strategy, {}).get("bar_timestamps_ns", []) or []
        bar_pnls.extend(bp)
        bar_ts_ns.extend(bt)
    if not bar_pnls or not bar_ts_ns or len(bar_pnls) != len(bar_ts_ns):
        return {
            "daily_sharpe_annualized": 0.0,
            "daily_max_drawdown_jpy": 0.0,
            "daily_max_drawdown_pct": 0.0,
            "daily_n_days": 0,
            "daily_mean_return_pct": 0.0,
            "daily_std_return_pct": 0.0,
        }
    ts_index = pd.to_datetime(np.asarray(bar_ts_ns, dtype="int64"))
    series = pd.Series(bar_pnls, index=ts_index, dtype=np.float64)
    daily_pnl = series.groupby(series.index.normalize()).sum().sort_index()
    if daily_pnl.empty:
        return {
            "daily_sharpe_annualized": 0.0,
            "daily_max_drawdown_jpy": 0.0,
            "daily_max_drawdown_pct": 0.0,
            "daily_n_days": 0,
            "daily_mean_return_pct": 0.0,
            "daily_std_return_pct": 0.0,
        }
    full_range = pd.date_range(
        daily_pnl.index.min(), daily_pnl.index.max(), freq="D", tz=daily_pnl.index.tz
    )
    daily_pnl = daily_pnl.reindex(full_range, fill_value=0.0)
    initial_eq = float(initial_balance_jpy)
    equity_after = initial_eq + daily_pnl.cumsum()
    equity = pd.concat(
        [
            pd.Series([initial_eq], index=[daily_pnl.index[0] - pd.Timedelta(days=1)]),
            equity_after,
        ]
    )
    daily_returns = equity.pct_change().dropna()
    if len(daily_returns) < 2:
        return {
            "daily_sharpe_annualized": 0.0,
            "daily_max_drawdown_jpy": 0.0,
            "daily_max_drawdown_pct": 0.0,
            "daily_n_days": int(len(daily_pnl)),
            "daily_mean_return_pct": (
                float(daily_returns.mean() * 100.0) if len(daily_returns) else 0.0
            ),
            "daily_std_return_pct": 0.0,
        }
    mean_r = float(daily_returns.mean())
    std_r = float(daily_returns.std(ddof=1))
    annualized_sharpe = (mean_r / std_r) * math.sqrt(252.0) if std_r > 0 else 0.0
    eq_post = equity.iloc[1:]
    peak = eq_post.cummax()
    drawdown_jpy = peak - eq_post
    max_dd_jpy = float(drawdown_jpy.max())
    max_dd_pct = float((drawdown_jpy / peak).max() * 100.0) if peak.gt(0).all() else 0.0
    return {
        "daily_sharpe_annualized": annualized_sharpe,
        "daily_max_drawdown_jpy": max_dd_jpy,
        "daily_max_drawdown_pct": max_dd_pct,
        "daily_n_days": int(len(daily_pnl)),
        "daily_mean_return_pct": float(mean_r * 100.0),
        "daily_std_return_pct": float(std_r * 100.0),
    }


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


def _print_per_rank_sharpe(
    per_fold_per_pick_sharpe: list[list[float]], k: int, cell_label: str
) -> None:
    """Phase 9.19: print mean per-rank Sharpe across folds for diagnostics.

    A K-th pick with mean Sharpe << rank-1 indicates dilution; if mean
    Sharpe < 0, the K-th pick is reducing the portfolio Sharpe.
    """
    _hdr(f"PER-RANK SHARPE (cell={cell_label}, K={k}) - fold-mean")
    print(f"  {'Rank':<8} {'Mean Sharpe':>14} {'Folds with rank':>18}")
    print("  " + "-" * 42)
    for rank in range(k):
        rank_values = [sharpes[rank] for sharpes in per_fold_per_pick_sharpe if rank < len(sharpes)]
        if not rank_values:
            continue
        mean_sharpe = sum(rank_values) / len(rank_values)
        print(f"  Rank {rank + 1:<3} {mean_sharpe:>14.3f} {len(rank_values):>18}")


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
        default=f"{_CELL_LGBM_ONLY},{_CELL_LGBM_MR_BO}",
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
    parser.add_argument(
        "--feature-groups",
        default="",
        help=(
            "Phase 9.X-B opt-in feature groups (comma-separated). "
            "Choices: vol (volatility clustering), moments (higher-order "
            "moments + autocorrelation), mtf (deep multi-timeframe extension). "
            "Empty (default) reproduces Phase 9.16 v9 baseline. "
            "Example: --feature-groups vol,moments"
        ),
    )
    parser.add_argument(
        "--strategy-conf-threshold",
        type=float,
        default=0.0,
        help=(
            "Phase 9.17b/I-1 confidence floor applied to MR and BO strategies "
            "(LGBM is unaffected; it has its own --conf-threshold). At 0.0 "
            "(default) preserves Phase 9.17 G-3 behavior."
        ),
    )
    parser.add_argument(
        "--top-ks",
        default="1,2,3,5",
        help=(
            "Phase 9.19/J-1 SELECTOR Top-K sweep. Comma-separated K values. "
            "K=1 reproduces Phase 9.17 G-3 (1 trade per bar). K>1 takes the "
            "K highest-confidence (pair x strategy) candidates per bar and "
            "sums their gross PnLs."
        ),
    )
    parser.add_argument(
        "--diversify-by-currency",
        action="store_true",
        default=False,
        help=(
            "Phase 9.19/J-1 diversification rule: at most one pick per "
            "currency family per bar (greedy fill in conf-descending order). "
            "Mitigates USD-cluster correlation that erodes the sqrt(K) "
            "Sharpe lift of naive top-K."
        ),
    )
    parser.add_argument(
        "--enable-risk-sizing",
        action="store_true",
        default=False,
        help=(
            "Phase 9.X-I/I-1: apply per-trade risk-based sizing and report "
            "Sharpe(JPY)/PnL(JPY) alongside pip metrics. When False (default), "
            "the script reproduces v19 numbers exactly."
        ),
    )
    parser.add_argument(
        "--risk-pct",
        type=float,
        default=1.0,
        help="Phase 9.X-I/I-1: risk per trade as %% of balance. Default 1.0.",
    )
    parser.add_argument(
        "--initial-balance-jpy",
        type=float,
        default=300_000.0,
        help="Phase 9.X-I/I-1: account balance in JPY (constant; no compound).",
    )
    parser.add_argument(
        "--min-lot",
        type=int,
        default=1000,
        help="Phase 9.X-I/I-1: minimum trade units (1 mini lot). Default 1000.",
    )
    args = parser.parse_args(argv)

    try:
        top_ks = [int(k.strip()) for k in args.top_ks.split(",") if k.strip()]
    except ValueError:
        print(f"ERROR: --top-ks values must be integers (got {args.top_ks!r})", file=sys.stderr)
        return 2
    for k in top_ks:
        if k < 1:
            print(f"ERROR: --top-ks values must be >= 1 (got {k})", file=sys.stderr)
            return 2

    enable_groups = frozenset(g.strip() for g in args.feature_groups.split(",") if g.strip())
    invalid_groups = enable_groups - set(_PHASE_X_B_GROUPS.keys())
    if invalid_groups:
        print(
            f"ERROR: invalid feature group(s): {sorted(invalid_groups)} "
            f"(valid: {sorted(_PHASE_X_B_GROUPS.keys())})",
            file=sys.stderr,
        )
        return 2

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
    print(
        f"Ensemble cells ({len(cell_specs)}): {', '.join(cell_specs)} | "
        f"strategy_conf_threshold={args.strategy_conf_threshold}"
    )
    diversify_str = "yes" if args.diversify_by_currency else "no"
    print(f"Top-K sweep: K in {top_ks} | diversify_by_currency={diversify_str}\n")

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

    print(
        f"\nBuilding features (per pair, baseline + Phase 9.X-B groups: "
        f"{sorted(enable_groups) if enable_groups else 'none'}) ..."
    )
    feat_dfs: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        feat = _build_pair_features(
            mid_dfs[pair],
            args.horizon,
            args.tp_mult,
            args.sl_mult,
            instrument=pair,
            enable_groups=enable_groups,
        )
        feat_dfs[pair] = feat
        print(f"  {pair}: {len(feat):>7,} rows  {feat[LABEL_COLUMN].notna().sum():>7,} labeled")
    feat_dfs = _build_cross_pair_features(feat_dfs, ref_pair=base_pair, enable_groups=enable_groups)

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

    # Phase 9.19: per-(cell, K) accumulators.
    sweep_keys: list[tuple[str, int]] = [(c, k) for c in cell_specs for k in top_ks]
    fold_results_by_key: dict[tuple[str, int], list[dict]] = {key: [] for key in sweep_keys}
    pair_select_totals_by_key: dict[tuple[str, int], dict[str, int]] = {
        key: {pair: 0 for pair in pairs} for key in sweep_keys
    }
    strategy_select_totals_by_key: dict[tuple[str, int], dict[str, int]] = {
        key: {s: 0 for s in _CELL_STRATEGY_SETS[key[0]]} for key in sweep_keys
    }
    pnl_series_by_key: dict[tuple[str, int], dict[str, list[float]]] = {
        key: {s: [] for s in _CELL_STRATEGY_SETS[key[0]]} for key in sweep_keys
    }
    per_pick_sharpes_by_key: dict[tuple[str, int], list[list[float]]] = {
        key: [] for key in sweep_keys
    }

    print("Running folds (train once -> eval per (cell, K) sweep cell) ...")
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
        for cell_name, k in sweep_keys:
            cell_strategies = _CELL_STRATEGY_SETS[cell_name]
            results, pair_counts, strat_counts, pnl_series, per_pick = _eval_fold(
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
                strategy_conf_threshold=args.strategy_conf_threshold,
                top_k=k,
                diversify_by_currency=args.diversify_by_currency,
                enable_risk_sizing=args.enable_risk_sizing,
                risk_pct=args.risk_pct,
                initial_balance_jpy=args.initial_balance_jpy,
                min_lot=args.min_lot,
            )
            key = (cell_name, k)
            fold_results_by_key[key].append(results)
            for pair, cnt in pair_counts.items():
                pair_select_totals_by_key[key][pair] += cnt
            for strat, cnt in strat_counts.items():
                strategy_select_totals_by_key[key][strat] += cnt
            for strat, series in pnl_series.items():
                pnl_series_by_key[key][strat].extend(series)
            per_pick_sharpes_by_key[key].append(per_pick)
            short_label = f"{cell_name[:6]}K{k}"
            sharpe_strs.append(f"{short_label}={results['SELECTOR']['net_sharpe']:>5.2f}")
        print(f"  Fold{fid:>3}{retrain_marker} SEL Sharpe: " + "  ".join(sharpe_strs))

    # ----- Aggregate and print per-(cell, K) summaries -----
    cell_summaries: list[tuple[str, int, dict, dict[tuple[str, str], float]]] = []
    baseline_cell_pnl: float | None = None
    for key in sweep_keys:
        agg = _aggregate(fold_results_by_key[key], args.initial_balance_jpy)
        if key == (_CELL_LGBM_ONLY, 1):
            baseline_cell_pnl = agg["SELECTOR"]["net_pnl"]

    for key in sweep_keys:
        cell_name, k = key
        agg = _aggregate(fold_results_by_key[key], args.initial_balance_jpy)
        rho_pairs = _compute_correlation_matrix(pnl_series_by_key[key])
        cell_label = f"{cell_name} (K={k})"
        _print_comparison(agg, args.spread_pip, cell_label)
        _print_strategy_breakdown(strategy_select_totals_by_key[key], cell_label)
        if len(_CELL_STRATEGY_SETS[cell_name]) > 1:
            _print_correlation_matrix(rho_pairs)
        # Per-rank Sharpe across folds (mean over folds).
        if k > 1 and per_pick_sharpes_by_key[key]:
            _print_per_rank_sharpe(per_pick_sharpes_by_key[key], k, cell_label)
        _print_verdict(agg, args.spread_pip, cell_label, rho_pairs, baseline_cell_pnl)
        cell_summaries.append((cell_name, k, agg, rho_pairs))

    # Cross-cell summary across the entire sweep.
    if len(cell_summaries) > 1:
        _hdr("MULTI-CELL TOP-K SWEEP SUMMARY (SELECTOR)")
        print(
            f"  {'Cell':<14} {'K':>4} {'NetSharpe':>10} {'NetPnL(pip)':>13} "
            f"{'MaxDD(pip)':>11} {'DD%PnL':>8} {'MaxRho':>8} {'Trades':>10}"
        )
        print("  " + "-" * 100)
        for cell_name, k, agg, rho_pairs in cell_summaries:
            sel = agg["SELECTOR"]
            max_rho = 0.0
            for (a, b), v in rho_pairs.items():
                if a != b:
                    max_rho = max(max_rho, abs(v))
            ratio = (
                f"  ({sel['net_pnl'] / baseline_cell_pnl:.2f}x)"
                if baseline_cell_pnl
                and baseline_cell_pnl > 0
                and (cell_name, k) != (_CELL_LGBM_ONLY, 1)
                else ""
            )
            print(
                f"  {cell_name:<14} {k:>4} {sel['overall_sharpe_net']:>10.3f} "
                f"{sel['net_pnl']:>13.1f} {sel['max_drawdown_pip']:>11.1f} "
                f"{sel['max_dd_pct_of_pnl']:>7.1f}% {max_rho:>8.3f} "
                f"{sel['total_trades']:>10,}{ratio}"
            )

        # Phase 9.X-I/I-1: JPY-based summary block (only when risk-sizing on).
        if args.enable_risk_sizing:
            _hdr(
                f"PHASE 9.X-I/I-1 - RISK-BASED JPY SUMMARY "
                f"(balance=JPY{args.initial_balance_jpy:,.0f}, risk={args.risk_pct}%)"
            )
            print(
                f"  {'Cell':<14} {'K':>4} {'Sharpe(JPY)':>12} {'NetPnL(JPY)':>14} "
                f"{'MaxDD(JPY)':>12} {'DD%PnL':>8} {'Sharpe d':>10}"
            )
            print("  " + "-" * 100)
            for cell_name, k, agg, _rho in cell_summaries:
                sel = agg["SELECTOR"]
                sharpe_pip = sel["overall_sharpe_net"]
                sharpe_jpy = sel.get("overall_sharpe_jpy", 0.0)
                pnl_jpy = sel.get("net_pnl_jpy", 0.0)
                dd_jpy = sel.get("max_drawdown_jpy", 0.0)
                dd_pct_jpy = sel.get("max_dd_pct_of_pnl_jpy", 0.0)
                delta = sharpe_jpy - sharpe_pip
                print(
                    f"  {cell_name:<14} {k:>4} {sharpe_jpy:>12.3f} {pnl_jpy:>14,.0f} "
                    f"{dd_jpy:>12,.0f} {dd_pct_jpy:>7.1f}% {delta:>+10.3f}"
                )
            print()
            print("  Sharpe d > 0 -> variance equalisation working (JPY-Sharpe vs pip-Sharpe)")

        # Phase 9.X-K: daily annualized Sharpe + max DD on equity curve.
        if args.enable_risk_sizing:
            _hdr(
                "PHASE 9.X-K - DAILY ANNUALIZED SHARPE + MAX DD "
                f"(initial=JPY{args.initial_balance_jpy:,.0f}, sqrt(252) annualization)"
            )
            print(
                f"  {'Cell':<14} {'K':>4} {'DailySharpe':>12} {'MeanRet%':>10} "
                f"{'StdRet%':>10} {'MaxDD(JPY)':>13} {'MaxDD%':>9} {'NDays':>7}"
            )
            print("  " + "-" * 100)
            for cell_name, k, agg, _rho in cell_summaries:
                sel = agg["SELECTOR"]
                ds = sel.get("daily_sharpe_annualized", 0.0)
                mr = sel.get("daily_mean_return_pct", 0.0)
                sr = sel.get("daily_std_return_pct", 0.0)
                dd = sel.get("daily_max_drawdown_jpy", 0.0)
                ddp = sel.get("daily_max_drawdown_pct", 0.0)
                nd = sel.get("daily_n_days", 0)
                print(
                    f"  {cell_name:<14} {k:>4} {ds:>12.3f} {mr:>9.4f}% "
                    f"{sr:>9.4f}% {dd:>13,.0f} {ddp:>8.2f}% {nd:>7}"
                )
            print()
            print(
                "  daily_return = equity_t / equity_{t-1} - 1; zero-return days included; "
                "annualized = mean/std * sqrt(252)"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
