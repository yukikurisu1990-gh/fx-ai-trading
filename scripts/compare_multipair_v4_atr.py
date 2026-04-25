"""compare_multipair_v4_atr.py — Phase 9.12/B-1 ATR-based TP/SL backtest.

Successor to v3 (`compare_multipair_v3_costs.py`). Same multipair walk-
forward + 4-strategy comparison shape, but with the labelling and PnL
scaled by ATR(14):

    TP = TP_mult * ATR(14)
    SL = SL_mult * ATR(14)

Why this matters
----------------
v3's fixed TP=3pip / SL=2pip was the binding constraint at the Phase 9.10
cost gate — at typical EUR/USD M1 ATR (~5-10 pip) a 3-pip TP is below
the noise floor, so triple-barrier resolution is dominated by random
walk hits rather than directional moves. ATR-scaling lets the labels
chase the actual *signal* in the data while keeping the same per-bar
EV calculation.

Compatibility
-------------
Reads the same MBA / BA JSONL produced by ``fetch_oanda_candles``
(prefers ``data/candles_<pair>_M1_365d_BA.jsonl`` if present, else
``..._365d.jsonl``). Mid OHLC for feature computation is the same as
v3. The only changes are the label function and the PnL helper.

Outputs the same 4-strategy comparison table as v3, with both gross
(no-cost) and net (spread-adjusted) Sharpe so the cost gap is explicit.

Usage
-----
    python scripts/compare_multipair_v4_atr.py \
        --tp-mult 1.5 --sl-mult 1.0 --horizon 20 \
        --spread-pip 1.0 --conf-threshold 0.50

For grid sweep see ``grid_search_atr.py`` (B-1 follow-up).
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
    rows = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            raw = json.loads(line)
            bid_c = float(raw["bid_c"])
            ask_c = float(raw["ask_c"])
            rows.append(
                {
                    "timestamp": _parse_oanda_ts(raw["time"]),
                    "open": (float(raw["bid_o"]) + float(raw["ask_o"])) / 2.0,
                    "high": (float(raw["bid_h"]) + float(raw["ask_h"])) / 2.0,
                    "low": (float(raw["bid_l"]) + float(raw["ask_l"])) / 2.0,
                    "close": (bid_c + ask_c) / 2.0,
                    "bid_c": bid_c,
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
# B-1: ATR-based triple-barrier labelling (the actual change vs v3)
# ---------------------------------------------------------------------------


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
    df = _add_labels_atr(df, horizon, tp_mult, sl_mult)
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
) -> tuple[dict, dict[str, int]]:
    base_df = pair_test_dfs[base_pair].dropna(subset=[LABEL_COLUMN])
    all_pairs = list(pair_models.keys())
    strats = ["EURUSD_ML", "SELECTOR", "EQUAL_AVG", "RANDOM"]
    acc: dict[str, dict] = {
        s: {"gross": [], "net": [], "w": 0, "l": 0, "t": 0, "n": 0} for s in strats
    }
    pair_select_counts: dict[str, int] = {p: 0 for p in all_pairs}

    def _record(s: str, gross_pip: float | None) -> None:
        a = acc[s]
        if gross_pip is None:
            a["n"] += 1
            return
        net = _net_pnl_pips(gross_pip, spread_pip)
        a["gross"].append(gross_pip)
        a["net"].append(net if net is not None else 0.0)
        if net is not None and net > 0:
            a["w"] += 1
        elif net is not None and net < 0:
            a["l"] += 1
        else:
            a["t"] += 1

    for _, base_row in base_df.iterrows():
        ts = base_row["timestamp"]
        base_pip = _pip_size(base_pair)
        base_atr = float(base_row.get("atr_14") or 0.0)

        # EURUSD_ML
        base_sig, _ = _get_ev(pair_models[base_pair], base_row, feature_cols, ml_threshold)
        base_gross = _gross_pnl_pips_atr(
            base_sig, int(base_row[LABEL_COLUMN]), tp_mult, sl_mult, base_atr, base_pip
        )
        _record("EURUSD_ML", base_gross)

        # All pairs at this timestamp
        pair_signals: dict[str, tuple[str, float, int, float, float]] = {}
        # value tuple: (sig, conf, label, atr_at_entry, pip_size)
        for pair, model in pair_models.items():
            pdf = pair_test_dfs[pair]
            rows = pdf[pdf["timestamp"] == ts]
            if rows.empty or rows[LABEL_COLUMN].isna().all():
                continue
            row = rows.iloc[0]
            label = int(row[LABEL_COLUMN])
            sig, conf = _get_ev(model, row, feature_cols, ml_threshold)
            atr = float(row.get("atr_14") or 0.0)
            pair_signals[pair] = (sig, conf, label, atr, _pip_size(pair))

        if not pair_signals:
            for s in ["SELECTOR", "EQUAL_AVG", "RANDOM"]:
                acc[s]["n"] += 1
            continue

        # SELECTOR
        active = [(p, d) for p, d in pair_signals.items() if d[0] != "no_trade"]
        if active:
            best = max(active, key=lambda x: x[1][1])[0]
            sig, _, label, atr, pip = pair_signals[best]
            _record("SELECTOR", _gross_pnl_pips_atr(sig, label, tp_mult, sl_mult, atr, pip))
            pair_select_counts[best] += 1
        else:
            acc["SELECTOR"]["n"] += 1

        # EQUAL_AVG
        traded_gross: list[float] = []
        for sig, _, label, atr, pip in pair_signals.values():
            g = _gross_pnl_pips_atr(sig, label, tp_mult, sl_mult, atr, pip)
            if g is not None:
                traded_gross.append(g)
        if traded_gross:
            mean_g = sum(traded_gross) / len(traded_gross)
            ea = acc["EQUAL_AVG"]
            ea["gross"].append(mean_g)
            ea["net"].append(mean_g - spread_pip)
            if mean_g - spread_pip > 0:
                ea["w"] += 1
            elif mean_g - spread_pip < 0:
                ea["l"] += 1
            else:
                ea["t"] += 1
        else:
            acc["EQUAL_AVG"]["n"] += 1

        # RANDOM
        rp = rng.choice(list(pair_signals.keys()))
        sig, _, label, atr, pip = pair_signals[rp]
        _record("RANDOM", _gross_pnl_pips_atr(sig, label, tp_mult, sl_mult, atr, pip))

    n_lab = len(base_df)
    results: dict[str, dict] = {}
    for s in strats:
        a = acc[s]
        total = a["w"] + a["l"] + a["t"]
        hit = a["w"] / (a["w"] + a["l"]) if (a["w"] + a["l"]) > 0 else 0.0
        results[s] = {
            "gross_sharpe": _sharpe(a["gross"]),
            "net_sharpe": _sharpe(a["net"]),
            "gross_pnl": sum(a["gross"]),
            "net_pnl": sum(a["net"]),
            "hit_rate": hit,
            "total_trades": total,
            "signal_rate": total / n_lab if n_lab > 0 else 0.0,
            "net_pnls": a["net"],
            "n_labeled": n_lab,
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
        f"SL_mult={sl_mult:.2f} x ATR  spread={spread_pip:.2f}pip)"
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
    _hdr(f"PHASE 9.12/B-1 VERDICT (spread={spread_pip:.2f}pip)")
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
    parser.add_argument("--spread-pip", type=float, default=1.0)
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
    print(
        f"Base: {base_pair} | TP={args.tp_mult}xATR / SL={args.sl_mult}xATR / "
        f"horizon={args.horizon} | conf>={args.conf_threshold} | "
        f"spread={args.spread_pip}pip | retrain every {args.retrain_interval_days}d\n"
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
            "bid_c",
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
