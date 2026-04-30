"""Train per-pair LGBM classifiers and save to models/lgbm/.

B-2 bid/ask triple-barrier labels (Phase 9.12): entry at ask_o, TP from
bid_h (long) / ask_l (short), SL from bid_l (long) / ask_h (short).

Features match FeatureService base feature set so training and inference
use identical feature vectors (no train/serve skew).

Usage:
    .venv/Scripts/python.exe scripts/train_lgbm_models.py
    .venv/Scripts/python.exe scripts/train_lgbm_models.py --pairs USD_JPY EUR_USD

Output:
    models/lgbm/{INSTRUMENT}.joblib  — per-pair LGBMClassifier
    models/lgbm/manifest.json        — feature_cols + training metadata
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants (match compare_multipair_v23_realism.py defaults)
# ---------------------------------------------------------------------------
_TP_MULT = 1.5
_SL_MULT = 1.0
_HORIZON = 20
_N_ESTIMATORS = 200
_LABEL_ENCODE = {-1: 0, 0: 1, 1: 2}
_LABEL_COLUMN = "label_tb"

_LGBM_PARAMS = {
    "learning_rate": 0.05,
    "num_leaves": 31,
    "verbose": -1,
}

_ALL_PAIRS = [
    "AUD_CAD",
    "AUD_JPY",
    "AUD_NZD",
    "AUD_USD",
    "CHF_JPY",
    "EUR_AUD",
    "EUR_CAD",
    "EUR_CHF",
    "EUR_GBP",
    "EUR_JPY",
    "EUR_USD",
    "GBP_AUD",
    "GBP_CHF",
    "GBP_JPY",
    "GBP_USD",
    "NZD_JPY",
    "NZD_USD",
    "USD_CAD",
    "USD_CHF",
    "USD_JPY",
]

_PIP_SIZE: dict[str, float] = {
    "AUD_CAD": 0.0001,
    "AUD_JPY": 0.01,
    "AUD_NZD": 0.0001,
    "AUD_USD": 0.0001,
    "CHF_JPY": 0.01,
    "EUR_AUD": 0.0001,
    "EUR_CAD": 0.0001,
    "EUR_CHF": 0.0001,
    "EUR_GBP": 0.0001,
    "EUR_JPY": 0.01,
    "EUR_USD": 0.0001,
    "GBP_AUD": 0.0001,
    "GBP_CHF": 0.0001,
    "GBP_JPY": 0.01,
    "GBP_USD": 0.0001,
    "NZD_JPY": 0.01,
    "NZD_USD": 0.0001,
    "USD_CAD": 0.0001,
    "USD_CHF": 0.0001,
    "USD_JPY": 0.01,
}


# ---------------------------------------------------------------------------
# Feature computation (vectorised pandas, matching FeatureService)
# ---------------------------------------------------------------------------


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add all FeatureService base features to the DataFrame (vectorised)."""
    df = df.copy()

    # Mid-price close (already computed as df["close"])
    c = df["close"]

    # EMA
    df["ema_12"] = c.ewm(span=12, adjust=False, min_periods=1).mean()
    df["ema_26"] = c.ewm(span=26, adjust=False, min_periods=1).mean()

    # MACD
    df["macd_line"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd_line"].ewm(span=9, adjust=False, min_periods=1).mean()
    df["macd_histogram"] = df["macd_line"] - df["macd_signal"]

    # RSI-14 (Wilder smoothing)
    delta = c.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / 14, adjust=False, min_periods=1).mean()
    avg_loss = loss.ewm(alpha=1.0 / 14, adjust=False, min_periods=1).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    df["rsi_14"] = 100.0 - 100.0 / (1.0 + rs)
    df["rsi_14"] = df["rsi_14"].fillna(50.0)

    # Bollinger Bands(20, 2σ)
    sma20 = c.rolling(20, min_periods=1).mean()
    std20 = c.rolling(20, min_periods=1).std(ddof=0).fillna(0.0)
    df["bb_middle"] = sma20
    df["bb_upper"] = sma20 + 2.0 * std20
    df["bb_lower"] = sma20 - 2.0 * std20
    bb_range = df["bb_upper"] - df["bb_lower"]
    df["bb_width"] = (bb_range / sma20.replace(0.0, np.nan)).fillna(0.0)
    df["bb_pct_b"] = ((c - df["bb_lower"]) / bb_range.replace(0.0, np.nan)).fillna(0.5)

    # SMA 20 / 50
    df["sma_20"] = sma20
    df["sma_50"] = c.rolling(50, min_periods=1).mean()

    # ATR-14 (standard true range)
    high = df["high"]
    low = df["low"]
    prev_close = c.shift(1).fillna(c)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(
        axis=1
    )
    df["atr_14"] = tr.rolling(14, min_periods=1).mean()

    # last_close
    df["last_close"] = c

    return df


def _add_labels_bidask(
    df: pd.DataFrame,
    instrument: str,
    horizon: int = _HORIZON,
    tp_mult: float = _TP_MULT,
    sl_mult: float = _SL_MULT,
) -> pd.DataFrame:
    """B-2 bid/ask triple-barrier labels (Phase 9.12).

    +1 = long TP hit first (bid_h reaches entry_ask + tp_mult*ATR within horizon)
    -1 = short TP hit first (ask_l reaches entry_bid - tp_mult*ATR within horizon)
     0 = neither TP hit before SL or timeout
    """
    df = df.copy()
    if "ask_o" not in df.columns or "bid_o" not in df.columns:
        raise ValueError(f"{instrument}: BA candles required for B-2 labels")

    n = len(df)
    atrs = df["atr_14"].to_numpy(dtype=np.float64)
    ask_o = df["ask_o"].to_numpy(dtype=np.float64)
    bid_o = df["bid_o"].to_numpy(dtype=np.float64)
    bid_h = df["bid_h"].to_numpy(dtype=np.float64)
    bid_l = df["bid_l"].to_numpy(dtype=np.float64)
    ask_h = df["ask_h"].to_numpy(dtype=np.float64)
    ask_l = df["ask_l"].to_numpy(dtype=np.float64)

    labels: list[int | None] = [None] * n
    for i in range(n - horizon - 1):
        atr_i = atrs[i]
        if np.isnan(atr_i) or atr_i <= 0.0:
            continue
        entry_ask = ask_o[i + 1]
        entry_bid = bid_o[i + 1]
        tp = tp_mult * atr_i
        sl = sl_mult * atr_i

        # Find first occurrence of each barrier within the horizon window.
        # Tracking all four in one pass avoids a second full-range scan for SL.
        long_tp_idx = long_sl_idx = short_tp_idx = short_sl_idx = None
        for j in range(i + 1, i + 1 + horizon):
            if long_tp_idx is None and bid_h[j] >= entry_ask + tp:
                long_tp_idx = j
            if long_sl_idx is None and bid_l[j] <= entry_ask - sl:
                long_sl_idx = j
            if short_tp_idx is None and ask_l[j] <= entry_bid - tp:
                short_tp_idx = j
            if short_sl_idx is None and ask_h[j] >= entry_bid + sl:
                short_sl_idx = j
            if (
                long_tp_idx is not None
                and long_sl_idx is not None
                and short_tp_idx is not None
                and short_sl_idx is not None
            ):
                break  # all barriers found; no need to scan further

        # Direction is profitable when TP hit arrives before SL (or SL never fires).
        long_profit = long_tp_idx is not None and (
            long_sl_idx is None or long_tp_idx <= long_sl_idx
        )
        short_profit = short_tp_idx is not None and (
            short_sl_idx is None or short_tp_idx <= short_sl_idx
        )

        if long_profit and not short_profit:
            labels[i] = 1
        elif short_profit and not long_profit:
            labels[i] = -1
        elif long_profit and short_profit:
            # Both directions profitable — take whichever TP landed first.
            labels[i] = 1 if long_tp_idx <= short_tp_idx else -1  # type: ignore[operator]
        else:
            labels[i] = 0

    df[_LABEL_COLUMN] = labels
    return df


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

_FEATURE_COLS = [
    # M1 base (15)
    "atr_14",
    "bb_lower",
    "bb_middle",
    "bb_pct_b",
    "bb_upper",
    "bb_width",
    "ema_12",
    "ema_26",
    "last_close",
    "macd_histogram",
    "macd_line",
    "macd_signal",
    "rsi_14",
    "sma_20",
    "sma_50",
    # M5 upper-TF (8)
    "m5_return_1",
    "m5_return_3",
    "m5_volatility",
    "m5_rsi_14",
    "m5_ma_slope",
    "m5_bb_pct_b",
    "m5_trend_slope",
    "m5_trend_dir",
    # M15 upper-TF (8)
    "m15_return_1",
    "m15_return_3",
    "m15_volatility",
    "m15_rsi_14",
    "m15_ma_slope",
    "m15_bb_pct_b",
    "m15_trend_slope",
    "m15_trend_dir",
    # H1 upper-TF (8)
    "h1_return_1",
    "h1_return_3",
    "h1_volatility",
    "h1_rsi_14",
    "h1_ma_slope",
    "h1_bb_pct_b",
    "h1_trend_slope",
    "h1_trend_dir",
    # MTF H4/D1/W1 (6)
    "h4_atr_14",
    "d1_return_3",
    "d1_range_pct",
    "d1_atr_14",
    "w1_return_1",
    "w1_range_pct",
]


def _rsi_series(c: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI on a pandas Series."""
    delta = c.diff()
    gain = delta.clip(lower=0.0).ewm(alpha=1.0 / period, adjust=False, min_periods=1).mean()
    loss = (-delta).clip(lower=0.0).ewm(alpha=1.0 / period, adjust=False, min_periods=1).mean()
    rs = gain / loss.replace(0.0, np.nan)
    return (100.0 - 100.0 / (1.0 + rs)).fillna(50.0)


def _add_upper_tf_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add M5/M15/H1 upper-timeframe features (vectorised, shift(1) no-lookahead)."""
    df = df.copy()
    idx = pd.DatetimeIndex(df["timestamp"])

    for rule, prefix in [("5min", "m5"), ("15min", "m15"), ("1h", "h1")]:
        ohlc = (
            df.set_index(idx)[["open", "high", "low", "close"]]
            .resample(rule)
            .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
            .dropna(how="all")
        )
        c = ohlc["close"]
        ret1 = c.pct_change(1)
        ret3 = c.pct_change(3)
        vol = ret1.rolling(5, min_periods=2).std(ddof=0)
        rsi14 = _rsi_series(c, 14)
        sma5 = c.rolling(5, min_periods=1).mean()
        ma_slope = sma5.diff(1) / sma5.shift(1)
        bb_std = c.rolling(20, min_periods=1).std(ddof=0).fillna(0.0)
        bb_mid = c.rolling(20, min_periods=1).mean()
        bb_lo = bb_mid - 2 * bb_std
        bb_wi = (4 * bb_std).replace(0.0, float("nan"))
        bb_pct = (c - bb_lo) / bb_wi
        trend_slope = c.pct_change(5)
        trend_dir = np.sign(c.diff(3))
        raw = pd.DataFrame(
            {
                f"{prefix}_return_1": ret1,
                f"{prefix}_return_3": ret3,
                f"{prefix}_volatility": vol,
                f"{prefix}_rsi_14": rsi14,
                f"{prefix}_ma_slope": ma_slope,
                f"{prefix}_bb_pct_b": bb_pct,
                f"{prefix}_trend_slope": trend_slope,
                f"{prefix}_trend_dir": trend_dir,
            },
            index=ohlc.index,
        )
        aligned = raw.shift(1).reindex(idx, method="ffill")
        for col in aligned.columns:
            df[col] = aligned[col].fillna(0.0).values

    return df


def _add_mtf_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add H4/D1/W1 MTF features (shift(1) no-lookahead, matches FeatureService)."""
    df = df.copy()
    idx = pd.DatetimeIndex(df["timestamp"])
    df_ts = df.set_index(idx)

    def _tr_series(ohlc: pd.DataFrame) -> pd.Series:
        h, lo, pc = ohlc["high"], ohlc["low"], ohlc["close"].shift(1)
        return pd.concat([h - lo, (h - pc).abs(), (lo - pc).abs()], axis=1).max(axis=1)

    # H4: h4_atr_14
    h4 = (
        df_ts[["open", "high", "low", "close"]]
        .resample("4h")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna(how="all")
    )
    h4_raw = pd.DataFrame(
        {"h4_atr_14": _tr_series(h4).rolling(14, min_periods=1).mean()},
        index=h4.index,
    )
    h4_aligned = h4_raw.shift(1).reindex(idx, method="ffill")
    df["h4_atr_14"] = h4_aligned["h4_atr_14"].fillna(0.0).values

    # D1: d1_return_3, d1_range_pct, d1_atr_14
    d1 = (
        df_ts[["open", "high", "low", "close"]]
        .resample("1D")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna(how="all")
    )
    d1_c = d1["close"]
    d1_raw = pd.DataFrame(
        {
            "d1_return_3": d1_c.pct_change(3),
            "d1_range_pct": (d1["high"] - d1["low"]) / d1_c.replace(0.0, float("nan")),
            "d1_atr_14": _tr_series(d1).rolling(14, min_periods=1).mean(),
        },
        index=d1.index,
    )
    d1_aligned = d1_raw.shift(1).reindex(idx, method="ffill")
    for col in d1_raw.columns:
        df[col] = d1_aligned[col].fillna(0.0).values

    # W1: w1_return_1, w1_range_pct
    w1 = (
        df_ts[["open", "high", "low", "close"]]
        .resample("1W")
        .agg({"open": "first", "high": "max", "low": "min", "close": "last"})
        .dropna(how="all")
    )
    w1_c = w1["close"]
    w1_raw = pd.DataFrame(
        {
            "w1_return_1": w1_c.pct_change(1),
            "w1_range_pct": (w1["high"] - w1["low"]) / w1_c.replace(0.0, float("nan")),
        },
        index=w1.index,
    )
    w1_aligned = w1_raw.shift(1).reindex(idx, method="ffill")
    for col in w1_raw.columns:
        df[col] = w1_aligned[col].fillna(0.0).values

    return df


def _train(df: pd.DataFrame) -> lgb.LGBMClassifier:
    labeled = df.dropna(subset=[_LABEL_COLUMN])
    x = labeled[_FEATURE_COLS].fillna(0.0).values.tolist()
    y = [_LABEL_ENCODE[int(v)] for v in labeled[_LABEL_COLUMN]]
    params = {**_LGBM_PARAMS, "n_estimators": _N_ESTIMATORS}
    model = lgb.LGBMClassifier(**params)
    model.fit(x, y)
    return model


def _load_ba_candles(path: Path) -> pd.DataFrame:
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["time"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Mid prices
    df["open"] = (df["bid_o"] + df["ask_o"]) / 2.0
    df["high"] = (df["bid_h"] + df["ask_h"]) / 2.0
    df["low"] = (df["bid_l"] + df["ask_l"]) / 2.0
    df["close"] = (df["bid_c"] + df["ask_c"]) / 2.0
    return df


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pairs",
        nargs="*",
        default=None,
        help="Instruments to train (default: all available)",
    )
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing candle JSONL files",
    )
    parser.add_argument(
        "--model-dir",
        default="models/lgbm",
        help="Output directory for saved models",
    )
    parser.add_argument(
        "--train-frac",
        type=float,
        default=0.80,
        help="Fraction of data to use for training (default 0.80)",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=_HORIZON,
        help="Triple-barrier horizon in bars (default 20)",
    )
    parser.add_argument(
        "--tp-mult",
        type=float,
        default=_TP_MULT,
    )
    parser.add_argument(
        "--sl-mult",
        type=float,
        default=_SL_MULT,
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    model_dir = Path(args.model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)

    pairs = args.pairs or _ALL_PAIRS
    trained: list[str] = []
    skipped: list[str] = []

    for pair in pairs:
        # Prefer BA candle file; fall back to mid-only
        ba_path = data_dir / f"candles_{pair}_M1_365d_BA.jsonl"
        mid_path = data_dir / f"candles_{pair}_M1_365d.jsonl"
        path = ba_path if ba_path.exists() else (mid_path if mid_path.exists() else None)
        if path is None:
            print(f"  SKIP {pair}: no candle file found")
            skipped.append(pair)
            continue

        print(f"  {pair}: loading {path.name} ...", end=" ", flush=True)
        df = _load_ba_candles(path)
        df = _add_features(df)
        df = _add_upper_tf_features(df)
        df = _add_mtf_features(df)

        if "ask_o" in df.columns:
            df = _add_labels_bidask(df, pair, args.horizon, args.tp_mult, args.sl_mult)
        else:
            print("SKIP (no bid/ask for B-2 labels)")
            skipped.append(pair)
            continue

        labeled = df.dropna(subset=[_LABEL_COLUMN])
        if len(labeled) < 1000:
            print(f"SKIP (only {len(labeled)} labeled rows)")
            skipped.append(pair)
            continue

        # Train/test split + purge
        n = len(labeled)
        n_train = int(n * args.train_frac)
        train_df = labeled.iloc[:n_train]
        if len(train_df) > args.horizon:
            train_df = train_df.iloc[: -args.horizon]

        label_dist = labeled[_LABEL_COLUMN].value_counts().to_dict()
        print(f"{len(train_df)} train rows, labels={label_dist}", end=" ... ", flush=True)

        model = _train(train_df)

        out_path = model_dir / f"{pair}.joblib"
        joblib.dump(model, out_path)
        trained.append(pair)
        print(f"saved → {out_path.name}")

    # Save manifest
    manifest = {
        "feature_version": "v4",
        "feature_cols": _FEATURE_COLS,
        "tp_mult": args.tp_mult,
        "sl_mult": args.sl_mult,
        "horizon": args.horizon,
        "n_estimators": _N_ESTIMATORS,
        "trained_pairs": trained,
    }
    manifest_path = model_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest: {manifest_path}")
    print(f"Trained: {len(trained)} pairs — {trained}")
    if skipped:
        print(f"Skipped: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
