"""Stage 22.0c M5 Donchian Breakout + M1 Entry Hybrid.

Consumes the path-aware scalp outcome dataset produced by 22.0a
(artifacts/stage22_0a/labels/labels_<pair>.parquet) and runs a 144-cell
sweep:
  Donchian N (M5 bars) ∈ {10, 20, 50, 100}
  entry timing         ∈ {immediate, retest, momentum}
  horizon (M1 bars)    ∈ {5, 10, 20, 40}
  exit rule            ∈ {tb_pnl, time_exit_pnl, best_possible_pnl}

For each cell aggregates per-trade PnL pooled across pairs, reports
mandatory 5-fold walk-forward stability of the top-K cells, +0.2 / +0.5
pip spread stress, entry-timing comparison, breakout sanity (incl.
direction-specific false-breakout rate), and cost diagnostics. Verdict
in {ADOPT, PROMISING_BUT_NEEDS_OOS, REJECT} on the best realistic-exit
cell. best_possible_pnl is diagnostic only (forced REJECT in classification).

Design contract: docs/design/phase22_0c_m5_breakout_m1_entry_hybrid.md.

M5 is signal-side only; outcome remains M1-entry based via the 22.0a
dataset. M1→M5 aggregation is performed on the fly (22.0z-2 confirmed
agreement with native M5 within ±2 pp).

Touches NO src/ files, NO scripts/run_*.py, NO DB schema. 20-pair
canonical universe; no time-of-day or pair filter.

Harness reuse note: cell aggregation, fold split, spread stress, verdict,
and cost diagnostics are copy-pasted from
scripts/stage22_0b_mean_reversion_baseline.py. Refactor into
phase22_research_lib.py should be considered before 22.0e or 22.0f lands.
"""

from __future__ import annotations

import argparse
import sys
import time
import warnings
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

# numpy emits a benign UserWarning when constructing datetime64 from a
# tz-aware pandas Timestamp; the conversion uses the UTC value correctly.
warnings.filterwarnings(
    "ignore",
    message="no explicit representation of timezones available for np.datetime64",
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
LABEL_DIR = REPO_ROOT / "artifacts" / "stage22_0a" / "labels"
OUT_DIR = REPO_ROOT / "artifacts" / "stage22_0c"

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

N_VALUES: tuple[int, ...] = (10, 20, 50, 100)
ENTRY_TIMINGS: tuple[str, ...] = ("immediate", "retest", "momentum")
HORIZONS: tuple[int, ...] = (5, 10, 20, 40)
EXIT_RULES: tuple[str, ...] = ("tb_pnl", "time_exit_pnl", "best_possible_pnl")
REALISTIC_EXIT_RULES: tuple[str, ...] = ("tb_pnl", "time_exit_pnl")

# Entry-timing search window in M1 bars (strictly after the signal bar)
ENTRY_WINDOW_M1_BARS = 5
MOMENTUM_ATR_MULT = 0.5

N_FOLDS = 5
SPREAD_STRESS_PIPS: tuple[float, ...] = (0.0, 0.2, 0.5)
EVAL_SPAN_YEARS_DEFAULT = 730.0 / 365.25
MIN_TRADES_FOR_RANKING = 30


# ---------------------------------------------------------------------------
# pip helper
# ---------------------------------------------------------------------------


def pip_size_for(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


# ---------------------------------------------------------------------------
# M1 BA loader (full bid/ask OHLC needed for retest/momentum on entry-side)
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
    df = df[keep].astype(np.float64)
    return df


# ---------------------------------------------------------------------------
# M1 → M5 aggregation (causal, right-closed, right-labeled)
# ---------------------------------------------------------------------------


def aggregate_m1_to_m5_mid(m1: pd.DataFrame) -> pd.DataFrame:
    """Aggregate M1 bid/ask OHLC to M5 mid-OHLC.

    The right-closed, right-labeled convention means each M5 bar's close
    reflects only M1 bars whose timestamp ``≤ T`` (the M5 boundary).
    """
    mid_o = (m1["bid_o"] + m1["ask_o"]) / 2.0
    mid_h = (m1["bid_h"] + m1["ask_h"]) / 2.0
    mid_l = (m1["bid_l"] + m1["ask_l"]) / 2.0
    mid_c = (m1["bid_c"] + m1["ask_c"]) / 2.0
    rs = pd.DataFrame(
        {
            "mid_o": mid_o.resample("5min", closed="right", label="right").first(),
            "mid_h": mid_h.resample("5min", closed="right", label="right").max(),
            "mid_l": mid_l.resample("5min", closed="right", label="right").min(),
            "mid_c": mid_c.resample("5min", closed="right", label="right").last(),
        }
    )
    return rs.dropna(how="all")


def donchian_channel(m5: pd.DataFrame, n: int) -> tuple[pd.Series, pd.Series]:
    """Causal Donchian channel from bars < T (shift(1) excludes current).

    Returns (hi_N, lo_N). NaN for the first n bars (and for bar 0 from shift).
    """
    hi = m5["mid_h"].shift(1).rolling(n, min_periods=n).max()
    lo = m5["mid_l"].shift(1).rolling(n, min_periods=n).min()
    return hi, lo


def detect_breakouts(m5: pd.DataFrame, n: int) -> pd.DataFrame:
    """Return DataFrame with [signal_ts, direction, break_level] for each
    bar where mid_close exceeds the Donchian channel.
    """
    hi, lo = donchian_channel(m5, n)
    long_break = m5["mid_c"] > hi
    short_break = m5["mid_c"] < lo
    longs = pd.DataFrame(
        {
            "signal_ts": m5.index[long_break],
            "direction": "long",
            "break_level": hi[long_break].values,
        }
    )
    shorts = pd.DataFrame(
        {
            "signal_ts": m5.index[short_break],
            "direction": "short",
            "break_level": lo[short_break].values,
        }
    )
    out = pd.concat([longs, shorts], ignore_index=True)
    out = out.sort_values("signal_ts").reset_index(drop=True)
    return out


# ---------------------------------------------------------------------------
# Entry-timing logic
# ---------------------------------------------------------------------------


@dataclass
class EntryFire:
    """A successful M1 entry (signal fired)."""

    signal_ts: np.datetime64
    entry_ts: np.datetime64
    direction: str
    bars_to_fire: int  # 1..ENTRY_WINDOW_M1_BARS


@dataclass
class M1Arrays:
    """Pre-extracted numpy views of an M1 BA frame for fast inner-loop access."""

    ts_int: np.ndarray  # int64 ns since epoch
    bid_c: np.ndarray
    ask_c: np.ndarray
    ask_l: np.ndarray
    ask_h: np.ndarray
    bid_l: np.ndarray
    bid_h: np.ndarray
    atr_at_entry: np.ndarray  # NaN-aligned to ts_int
    index_dt: np.ndarray  # datetime64[ns], naive (UTC)


def m1_arrays(m1: pd.DataFrame, atr_aligned: pd.Series) -> M1Arrays:
    idx_dt = m1.index.values.astype("datetime64[ns]")
    return M1Arrays(
        ts_int=idx_dt.view("int64"),
        bid_c=m1["bid_c"].to_numpy(),
        ask_c=m1["ask_c"].to_numpy(),
        ask_l=m1["ask_l"].to_numpy(),
        ask_h=m1["ask_h"].to_numpy(),
        bid_l=m1["bid_l"].to_numpy(),
        bid_h=m1["bid_h"].to_numpy(),
        atr_at_entry=atr_aligned.to_numpy(),
        index_dt=idx_dt,
    )


def find_entries_for_signal(
    m1: pd.DataFrame,
    m1_ts_int: np.ndarray,
    atr_at_entry_per_m1: pd.Series,
    signal_ts: pd.Timestamp,
    direction: str,
    break_level: float,
    timing: str,
    arrays: M1Arrays | None = None,
) -> tuple[EntryFire | None, list[float]]:
    """Apply entry-timing rule to find the M1 bar that fires the entry.

    Returns (EntryFire or None, mid_close_path_for_false_break_check).
    """
    arr = arrays if arrays is not None else m1_arrays(m1, atr_at_entry_per_m1)
    sig_int = np.datetime64(signal_ts, "ns").view("int64")
    idx = int(np.searchsorted(arr.ts_int, sig_int, side="right"))
    n = arr.ts_int.size
    if idx >= n:
        return None, []
    end_idx = min(idx + ENTRY_WINDOW_M1_BARS, n)

    mid_close_path = ((arr.bid_c[idx:end_idx] + arr.ask_c[idx:end_idx]) / 2.0).tolist()

    if timing == "immediate":
        return (
            EntryFire(
                signal_ts=np.datetime64(signal_ts, "ns"),
                entry_ts=arr.index_dt[idx],
                direction=direction,
                bars_to_fire=1,
            ),
            mid_close_path,
        )

    # retest / momentum: vectorized candidate scan
    for k, j in enumerate(range(idx, end_idx)):
        if timing == "retest":
            if direction == "long":
                cond = arr.ask_l[j] <= break_level
            else:
                cond = arr.bid_h[j] >= break_level
        else:  # momentum
            atr = arr.atr_at_entry[j]
            if not np.isfinite(atr) or atr <= 0:
                continue
            offset = MOMENTUM_ATR_MULT * atr
            if direction == "long":
                cond = arr.ask_h[j] > break_level + offset
            else:
                cond = arr.bid_l[j] < break_level - offset
        if bool(cond):
            return (
                EntryFire(
                    signal_ts=np.datetime64(signal_ts, "ns"),
                    entry_ts=arr.index_dt[j],
                    direction=direction,
                    bars_to_fire=k + 1,
                ),
                mid_close_path,
            )
    return None, mid_close_path


# ---------------------------------------------------------------------------
# False breakout rate (direction-specific)
# ---------------------------------------------------------------------------


def is_false_breakout(direction: str, break_level: float, mid_path: list[float]) -> bool:
    """Long false-break: mid returns BELOW break_level within window.
    Short false-break: mid returns ABOVE break_level within window.
    """
    if not mid_path:
        return False
    if direction == "long":
        return any(p < break_level for p in mid_path)
    return any(p > break_level for p in mid_path)


# ---------------------------------------------------------------------------
# Cell accumulator (copy-pasted from 22.0b — see harness reuse note in design doc)
# ---------------------------------------------------------------------------


@dataclass
class CellAcc:
    entry_ts: list[np.ndarray] = field(default_factory=list)
    pnl: list[np.ndarray] = field(default_factory=list)
    pair_arr: list[np.ndarray] = field(default_factory=list)
    spread_entry: list[np.ndarray] = field(default_factory=list)
    cost_ratio: list[np.ndarray] = field(default_factory=list)
    hour_utc: list[np.ndarray] = field(default_factory=list)
    dow: list[np.ndarray] = field(default_factory=list)
    direction: list[np.ndarray] = field(default_factory=list)

    def extend(
        self,
        entry_ts_arr: np.ndarray,
        pnl_arr: np.ndarray,
        pair_arr: np.ndarray,
        spread_arr: np.ndarray,
        cost_arr: np.ndarray,
        hour_arr: np.ndarray,
        dow_arr: np.ndarray,
        direction_arr: np.ndarray,
    ) -> None:
        if entry_ts_arr.size == 0:
            return
        self.entry_ts.append(entry_ts_arr)
        self.pnl.append(pnl_arr)
        self.pair_arr.append(pair_arr)
        self.spread_entry.append(spread_arr)
        self.cost_ratio.append(cost_arr)
        self.hour_utc.append(hour_arr)
        self.dow.append(dow_arr)
        self.direction.append(direction_arr)

    def materialize(self) -> pd.DataFrame:
        if not self.entry_ts:
            return pd.DataFrame(
                columns=[
                    "entry_ts",
                    "pnl",
                    "pair",
                    "spread_entry",
                    "cost_ratio",
                    "hour_utc",
                    "dow",
                    "direction",
                ]
            )
        out = pd.DataFrame(
            {
                "entry_ts": np.concatenate(self.entry_ts),
                "pnl": np.concatenate(self.pnl),
                "pair": np.concatenate(self.pair_arr),
                "spread_entry": np.concatenate(self.spread_entry),
                "cost_ratio": np.concatenate(self.cost_ratio),
                "hour_utc": np.concatenate(self.hour_utc),
                "dow": np.concatenate(self.dow),
                "direction": np.concatenate(self.direction),
            }
        )
        out = out.sort_values("entry_ts").reset_index(drop=True)
        return out


# ---------------------------------------------------------------------------
# Per-pair processing
# ---------------------------------------------------------------------------

_LABEL_COLUMNS_NEEDED = (
    "entry_ts",
    "horizon_bars",
    "direction",
    "valid_label",
    "gap_affected_forward_window",
    "tb_pnl",
    "time_exit_pnl",
    "best_possible_pnl",
    "spread_entry",
    "cost_ratio",
    "hour_utc",
    "dow",
    "atr_at_entry",
)


def _build_lookup_arrays(labels: pd.DataFrame) -> dict[tuple[int, str], dict[str, np.ndarray]]:
    out: dict[tuple[int, str], dict[str, np.ndarray]] = {}
    for h in HORIZONS:
        for d in ("long", "short"):
            mask = (labels["horizon_bars"] == h) & (labels["direction"] == d)
            sub = labels[mask].sort_values("entry_ts")
            ts_aware = sub["entry_ts"]
            ts_naive = ts_aware.dt.tz_convert("UTC").dt.tz_localize(None)
            ts = ts_naive.to_numpy().astype("datetime64[ns]").view("int64")
            out[(h, d)] = {
                "ts": ts,
                "tb_pnl": sub["tb_pnl"].to_numpy(dtype=np.float32),
                "time_exit_pnl": sub["time_exit_pnl"].to_numpy(dtype=np.float32),
                "best_possible_pnl": sub["best_possible_pnl"].to_numpy(dtype=np.float32),
                "spread_entry": sub["spread_entry"].to_numpy(dtype=np.float32),
                "cost_ratio": sub["cost_ratio"].to_numpy(dtype=np.float32),
                "hour_utc": sub["hour_utc"].to_numpy(dtype=np.int8),
                "dow": sub["dow"].to_numpy(dtype=np.int8),
            }
    return out


def _match_signals(label_ts: np.ndarray, sig_ts: np.ndarray) -> np.ndarray:
    if sig_ts.size == 0 or label_ts.size == 0:
        return np.empty(0, dtype=np.int64)
    idx = np.searchsorted(label_ts, sig_ts)
    valid = (idx < len(label_ts)) & (label_ts[np.minimum(idx, len(label_ts) - 1)] == sig_ts)
    return idx[valid]


@dataclass
class TimingStats:
    """Per (N, entry_timing, direction) breakout-side bookkeeping for diagnostics."""

    n_signals: int = 0
    n_fired: int = 0
    bars_to_fire_hist: dict[int, int] = field(default_factory=lambda: dict.fromkeys(range(1, 6), 0))
    n_false_breakouts: int = 0


def process_pair(
    pair: str,
    days: int,
    accumulators: dict[tuple[int, str, int, str], CellAcc],
    timing_stats: dict[tuple[int, str, str], TimingStats],
) -> int:
    """Compute breakouts and entries; populate accumulators across cells."""
    m1 = load_m1_ba(pair, days=days)
    label_path = LABEL_DIR / f"labels_{pair}.parquet"
    if not label_path.exists():
        raise FileNotFoundError(label_path)
    labels = pd.read_parquet(label_path, columns=list(_LABEL_COLUMNS_NEEDED))
    labels = labels[labels["valid_label"] & ~labels["gap_affected_forward_window"]]
    n_valid = len(labels)
    if n_valid == 0:
        return 0
    if not pd.api.types.is_datetime64_any_dtype(labels["entry_ts"]):
        labels["entry_ts"] = pd.to_datetime(labels["entry_ts"], utc=True)
    lookup_arrays = _build_lookup_arrays(labels)

    # M1 ATR(14) per M1 bar in PRICE UNITS (the 22.0a parquet stores it in pip
    # units; multiply by pip_size to compare against break_level which is in
    # price units).
    pip = pip_size_for(pair)
    atr_lookup = labels[(labels["horizon_bars"] == 5) & (labels["direction"] == "long")]
    atr_lookup = atr_lookup.set_index("entry_ts").sort_index()
    atr_pip_series = pd.Series(atr_lookup["atr_at_entry"].values, index=atr_lookup.index)
    atr_aligned = (atr_pip_series.reindex(m1.index)) * pip  # price units

    m5 = aggregate_m1_to_m5_mid(m1)
    arrays = m1_arrays(m1, atr_aligned)
    m1_ts_int = arrays.ts_int

    for n in N_VALUES:
        breakouts = detect_breakouts(m5, n)
        if breakouts.empty:
            continue
        # Pre-extract breakout arrays for fast iteration
        bk_signal_ts = breakouts["signal_ts"].to_numpy()
        bk_directions = breakouts["direction"].to_numpy()
        bk_break_levels = breakouts["break_level"].to_numpy()
        for timing in ENTRY_TIMINGS:
            fires_long: list[EntryFire] = []
            fires_short: list[EntryFire] = []
            stats_long = timing_stats.setdefault((n, timing, "long"), TimingStats())
            stats_short = timing_stats.setdefault((n, timing, "short"), TimingStats())
            for sig_ts_, direction, level in zip(
                bk_signal_ts,
                bk_directions,
                bk_break_levels,
                strict=True,
            ):
                stats = stats_long if direction == "long" else stats_short
                stats.n_signals += 1
                fire, mid_path = find_entries_for_signal(
                    m1,
                    m1_ts_int,
                    atr_aligned,
                    sig_ts_,
                    direction,
                    float(level),
                    timing,
                    arrays=arrays,
                )
                if is_false_breakout(direction, float(level), mid_path):
                    stats.n_false_breakouts += 1
                if fire is not None:
                    stats.n_fired += 1
                    stats.bars_to_fire_hist[fire.bars_to_fire] = (
                        stats.bars_to_fire_hist.get(fire.bars_to_fire, 0) + 1
                    )
                    if direction == "long":
                        fires_long.append(fire)
                    else:
                        fires_short.append(fire)

            for h in HORIZONS:
                for direction, fires in (("long", fires_long), ("short", fires_short)):
                    if not fires:
                        continue
                    sig_ts_int = np.array(
                        [int(f.entry_ts.astype("datetime64[ns]").view("int64")) for f in fires],
                        dtype=np.int64,
                    )
                    sig_ts_int.sort()
                    arr = lookup_arrays[(h, direction)]
                    matched = _match_signals(arr["ts"], sig_ts_int)
                    if matched.size == 0:
                        continue
                    entry_ts_arr = arr["ts"][matched].view("datetime64[ns]")
                    spread_arr = arr["spread_entry"][matched]
                    cost_arr = arr["cost_ratio"][matched]
                    hour_arr = arr["hour_utc"][matched]
                    dow_arr = arr["dow"][matched]
                    pair_arr = np.full(matched.size, pair, dtype=object)
                    direction_arr = np.full(matched.size, direction, dtype=object)
                    for exit_rule in EXIT_RULES:
                        pnl = arr[exit_rule][matched]
                        accumulators[(n, timing, h, exit_rule)].extend(
                            entry_ts_arr,
                            pnl,
                            pair_arr,
                            spread_arr,
                            cost_arr,
                            hour_arr,
                            dow_arr,
                            direction_arr,
                        )
    return n_valid


# ---------------------------------------------------------------------------
# Cell metric computation (copy-pasted from 22.0b)
# ---------------------------------------------------------------------------


def compute_eval_span_years(_trades_df: pd.DataFrame) -> float:
    return EVAL_SPAN_YEARS_DEFAULT


def annualize(total: float, n: int, span_years: float) -> float:
    if n == 0 or span_years <= 0:
        return 0.0
    return total / span_years


def per_trade_sharpe(pnl: np.ndarray) -> float:
    if pnl.size < 2:
        return 0.0
    mean = float(np.mean(pnl))
    var = float(np.var(pnl, ddof=0))
    if var <= 0:
        return 0.0
    return mean / np.sqrt(var)


def max_drawdown(pnl: np.ndarray) -> float:
    if pnl.size == 0:
        return 0.0
    eq = np.cumsum(pnl)
    peak = np.maximum.accumulate(eq)
    dd = peak - eq
    return float(dd.max())


def compute_cell_metrics(
    cell_key: tuple[int, str, int, str],
    trades: pd.DataFrame,
) -> dict:
    n_pkw, timing, h, exit_rule = cell_key
    n = len(trades)
    if n == 0:
        return _empty_metrics(cell_key)
    span_years = compute_eval_span_years(trades)
    pnl = trades["pnl"].to_numpy()
    annual_pnl = annualize(float(pnl.sum()), n, span_years)
    sharpe = per_trade_sharpe(pnl)
    dd = max_drawdown(pnl)
    dd_pct = (dd / abs(annual_pnl)) * 100.0 if abs(annual_pnl) > 1e-9 else float("inf")

    stress_metrics: dict[str, float] = {}
    for stress in SPREAD_STRESS_PIPS:
        stressed = pnl - stress
        stress_metrics[f"annual_pnl_stress_+{stress:.1f}"] = annualize(
            float(stressed.sum()), n, span_years
        )
        stress_metrics[f"sharpe_stress_+{stress:.1f}"] = per_trade_sharpe(stressed)

    fold_metrics = compute_fold_metrics(trades)

    return {
        "N": n_pkw,
        "entry_timing": timing,
        "horizon_bars": h,
        "exit_rule": exit_rule,
        "n_trades": n,
        "annual_trades": n / span_years,
        "annual_pnl_pip": annual_pnl,
        "sharpe": sharpe,
        "max_dd_pip": dd,
        "dd_pct_pnl": dd_pct,
        "mean_pnl": float(pnl.mean()),
        "median_pnl": float(np.median(pnl)),
        "win_rate": float((pnl > 0).mean()),
        **stress_metrics,
        **fold_metrics,
    }


def _empty_metrics(cell_key: tuple[int, str, int, str]) -> dict:
    n, timing, h, exit_rule = cell_key
    out = {
        "N": n,
        "entry_timing": timing,
        "horizon_bars": h,
        "exit_rule": exit_rule,
        "n_trades": 0,
        "annual_trades": 0.0,
        "annual_pnl_pip": 0.0,
        "sharpe": 0.0,
        "max_dd_pip": 0.0,
        "dd_pct_pnl": float("inf"),
        "mean_pnl": 0.0,
        "median_pnl": 0.0,
        "win_rate": 0.0,
    }
    for stress in SPREAD_STRESS_PIPS:
        out[f"annual_pnl_stress_+{stress:.1f}"] = 0.0
        out[f"sharpe_stress_+{stress:.1f}"] = 0.0
    out.update(
        {
            "fold_pos": 0,
            "fold_neg": 0,
            "fold_pnl_cv": float("inf"),
            "fold_concentration_top": 0.0,
            **{f"fold_{i}_pnl": 0.0 for i in range(N_FOLDS)},
            **{f"fold_{i}_n": 0 for i in range(N_FOLDS)},
        }
    )
    return out


def compute_fold_metrics(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {
            "fold_pos": 0,
            "fold_neg": 0,
            "fold_pnl_cv": float("inf"),
            "fold_concentration_top": 0.0,
            **{f"fold_{i}_pnl": 0.0 for i in range(N_FOLDS)},
            **{f"fold_{i}_n": 0 for i in range(N_FOLDS)},
        }
    ts = trades["entry_ts"].to_numpy()
    pnl = trades["pnl"].to_numpy()
    t_min = ts.min()
    t_max = ts.max()
    span = t_max - t_min
    edges = [t_min + (span * i / N_FOLDS) for i in range(N_FOLDS + 1)]
    fold_pnls: list[float] = []
    fold_ns: list[int] = []
    for i in range(N_FOLDS):
        if i < N_FOLDS - 1:
            mask = (ts >= edges[i]) & (ts < edges[i + 1])
        else:
            mask = (ts >= edges[i]) & (ts <= edges[i + 1])
        fp = pnl[mask]
        fold_pnls.append(float(fp.sum()))
        fold_ns.append(int(fp.size))
    fold_pos = sum(1 for v in fold_pnls if v > 0)
    fold_neg = sum(1 for v in fold_pnls if v < 0)
    arr = np.asarray(fold_pnls)
    mean = float(arr.mean())
    std = float(arr.std(ddof=0))
    cv = std / abs(mean) if abs(mean) > 1e-9 else float("inf")
    total = float(np.abs(arr).sum())
    top = float(np.abs(arr).max() / total) if total > 0 else 0.0
    out = {
        "fold_pos": fold_pos,
        "fold_neg": fold_neg,
        "fold_pnl_cv": cv,
        "fold_concentration_top": top,
    }
    out.update({f"fold_{i}_pnl": fold_pnls[i] for i in range(N_FOLDS)})
    out.update({f"fold_{i}_n": fold_ns[i] for i in range(N_FOLDS)})
    return out


# ---------------------------------------------------------------------------
# Verdict (copy-pasted from 22.0b)
# ---------------------------------------------------------------------------

ADOPT_MIN_TRADES = 70
OVERTRADE_WARN_TRADES = 1000
ADOPT_MIN_SHARPE = 0.082
ADOPT_MIN_PNL = 180.0
ADOPT_MAX_DD = 200.0
ADOPT_MIN_FOLD_POSNEG = (4, 1)


def classify_cell(cell: dict) -> tuple[str, list[str]]:
    failed: list[str] = []
    exit_rule = cell["exit_rule"]
    if exit_rule == "best_possible_pnl":
        return "REJECT", ["non-realistic exit_rule (diagnostic only)"]
    annual_trades = cell["annual_trades"]
    if annual_trades < ADOPT_MIN_TRADES:
        return "REJECT", [f"A0: annual_trades {annual_trades:.0f} < {ADOPT_MIN_TRADES}"]
    if cell["sharpe"] < ADOPT_MIN_SHARPE:
        return "REJECT", [f"A1: sharpe {cell['sharpe']:.4f} < {ADOPT_MIN_SHARPE}"]
    if cell["annual_pnl_pip"] < ADOPT_MIN_PNL:
        return "REJECT", [f"A2: annual_pnl {cell['annual_pnl_pip']:.1f} < {ADOPT_MIN_PNL}"]
    if cell["max_dd_pip"] > ADOPT_MAX_DD:
        failed.append(f"A3: MaxDD {cell['max_dd_pip']:.1f} > {ADOPT_MAX_DD}")
    if not (
        cell["fold_pos"] >= ADOPT_MIN_FOLD_POSNEG[0]
        and cell["fold_neg"] <= ADOPT_MIN_FOLD_POSNEG[1]
    ):
        failed.append(f"A4: fold pos/neg {cell['fold_pos']}/{cell['fold_neg']} not >= 4/1")
    if cell["annual_pnl_stress_+0.5"] <= 0:
        failed.append(f"A5: stress +0.5pip annual PnL {cell['annual_pnl_stress_+0.5']:.1f} <= 0")
    if not failed:
        return "ADOPT", []
    return "PROMISING_BUT_NEEDS_OOS", failed


# ---------------------------------------------------------------------------
# Cost diagnostics (copy-pasted from 22.0b)
# ---------------------------------------------------------------------------


def cost_diagnostics(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {}
    cost_buckets = [(0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, np.inf)]
    spread_buckets = [(0, 1), (1, 2), (2, 3), (3, np.inf)]
    out: dict = {
        "median_spread_entry": float(trades["spread_entry"].median()),
        "median_cost_ratio": float(trades["cost_ratio"].median()),
        "p10_cost_ratio": float(trades["cost_ratio"].quantile(0.10)),
        "p90_cost_ratio": float(trades["cost_ratio"].quantile(0.90)),
        "by_cost_ratio_bucket": {},
        "by_spread_bucket": {},
        "by_pair": {},
        "by_session": {},
    }
    for lo, hi in cost_buckets:
        mask = (trades["cost_ratio"] >= lo) & (trades["cost_ratio"] < hi)
        sub = trades[mask]
        out["by_cost_ratio_bucket"][f"[{lo}, {hi})"] = {
            "n": int(len(sub)),
            "pnl_sum": float(sub["pnl"].sum()),
            "pnl_mean": float(sub["pnl"].mean()) if len(sub) else 0.0,
        }
    for lo, hi in spread_buckets:
        mask = (trades["spread_entry"] >= lo) & (trades["spread_entry"] < hi)
        sub = trades[mask]
        out["by_spread_bucket"][f"[{lo}, {hi}) pip"] = {
            "n": int(len(sub)),
            "pnl_sum": float(sub["pnl"].sum()),
            "pnl_mean": float(sub["pnl"].mean()) if len(sub) else 0.0,
        }
    pair_grp = trades.groupby("pair")["pnl"].agg(["count", "sum", "mean"])
    for pair, row in pair_grp.iterrows():
        out["by_pair"][pair] = {
            "n": int(row["count"]),
            "pnl_sum": float(row["sum"]),
            "pnl_mean": float(row["mean"]),
        }
    sessions = {
        "Tokyo (0-7 UTC)": (0, 7),
        "London (7-14 UTC)": (7, 14),
        "NY (14-21 UTC)": (14, 21),
        "Rollover (21-24 UTC)": (21, 24),
    }
    for name, (lo, hi) in sessions.items():
        mask = (trades["hour_utc"] >= lo) & (trades["hour_utc"] < hi)
        sub = trades[mask]
        out["by_session"][name] = {
            "n": int(len(sub)),
            "pnl_sum": float(sub["pnl"].sum()),
            "pnl_mean": float(sub["pnl"].mean()) if len(sub) else 0.0,
        }
    return out


# ---------------------------------------------------------------------------
# Report writer (extends 22.0b with entry-timing + breakout-sanity sections)
# ---------------------------------------------------------------------------


def write_report(
    sweep_df: pd.DataFrame,
    top_k_cells: list[dict],
    top_k_diagnostics: list[dict],
    timing_stats: dict[tuple[int, str, str], TimingStats],
    out_dir: Path,
    pairs_used: list[str],
    pairs_missing: list[str],
) -> Path:
    p = out_dir / "eval_report.md"
    lines: list[str] = []
    lines.append("# Stage 22.0c M5 Donchian Breakout + M1 Entry Hybrid — Evaluation Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase22_0c_m5_breakout_m1_entry_hybrid.md`.")
    lines.append("")
    lines.append("> ⚠ **Multiple testing caveat**: 144 cells were searched. The reported best")
    lines.append("> cell's Sharpe / PnL are *in-sample search results*. Production migration")
    lines.append("> of any ADOPT-classified cell requires independent OOS validation")
    lines.append("> (held-out future time slice, paper-run, or fresh data fetch). The")
    lines.append('> ADOPT classification here means "passes all 6 in-sample gates" — not')
    lines.append('> "production-ready".')
    lines.append("")
    lines.append("## Pair coverage")
    lines.append("")
    lines.append(
        f"- Active pairs: {len(pairs_used)} / 20 canonical "
        f"(missing: {', '.join(pairs_missing) if pairs_missing else 'none'})"
    )
    lines.append("")
    if pairs_missing:
        lines.append(f"  *{', '.join(pairs_missing)} M1 BA candle file missing in local store.*")
        lines.append("")

    realistic = sweep_df[
        sweep_df["exit_rule"].isin(REALISTIC_EXIT_RULES)
        & (sweep_df["n_trades"] >= MIN_TRADES_FOR_RANKING)
    ]
    if realistic.empty:
        lines.append("## Verdict: NO_DATA — no realistic cell with sufficient trades.")
        verdict_cell: dict | None = None
    else:
        ranked = realistic.sort_values(
            by=["sharpe", "annual_pnl_pip", "n_trades"],
            ascending=[False, False, False],
        )
        verdict_cell = ranked.iloc[0].to_dict()
        verdict, failed = classify_cell(verdict_cell)
        lines.append(f"## Verdict: **{verdict}**")
        lines.append("")
        lines.append(
            f"- Best realistic-exit cell: N={verdict_cell['N']}, "
            f"timing={verdict_cell['entry_timing']}, "
            f"horizon={verdict_cell['horizon_bars']}, exit={verdict_cell['exit_rule']}"
        )
        a0_pass = verdict_cell["annual_trades"] >= ADOPT_MIN_TRADES
        a1_pass = verdict_cell["sharpe"] >= ADOPT_MIN_SHARPE
        a2_pass = verdict_cell["annual_pnl_pip"] >= ADOPT_MIN_PNL
        a3_pass = verdict_cell["max_dd_pip"] <= ADOPT_MAX_DD
        a4_pass = verdict_cell["fold_pos"] >= 4 and verdict_cell["fold_neg"] <= 1
        a5_pass = verdict_cell["annual_pnl_stress_+0.5"] > 0
        lines.append(
            f"- annual_trades={verdict_cell['annual_trades']:.0f} (A0 ≥ 70: "
            f"{'PASS' if a0_pass else 'FAIL'})"
        )
        lines.append(
            f"- Sharpe={verdict_cell['sharpe']:.4f} (A1 ≥ 0.082: {'PASS' if a1_pass else 'FAIL'})"
        )
        lines.append(
            f"- annual_pnl={verdict_cell['annual_pnl_pip']:.1f} pip (A2 ≥ 180: "
            f"{'PASS' if a2_pass else 'FAIL'})"
        )
        lines.append(
            f"- MaxDD={verdict_cell['max_dd_pip']:.1f} pip (A3 ≤ 200: "
            f"{'PASS' if a3_pass else 'FAIL'})"
        )
        lines.append(
            f"- fold pos/neg={verdict_cell['fold_pos']}/{verdict_cell['fold_neg']} "
            f"(A4 ≥ 4/1: {'PASS' if a4_pass else 'FAIL'})"
        )
        lines.append(
            f"- annual_pnl @ +0.5 pip stress={verdict_cell['annual_pnl_stress_+0.5']:.1f} "
            f"(A5 > 0: {'PASS' if a5_pass else 'FAIL'})"
        )
        if failed:
            lines.append("")
            lines.append("**Gates that failed**:")
            for f in failed:
                lines.append(f"- {f}")
        if verdict_cell["annual_trades"] > OVERTRADE_WARN_TRADES:
            lines.append("")
            lines.append(
                f"⚠ Overtrading warning: annual_trades = {verdict_cell['annual_trades']:.0f} "
                f"> {OVERTRADE_WARN_TRADES}."
            )
        lines.append("")

    # Top-K table
    lines.append("## Top-10 cells (realistic exit_rule, by Sharpe)")
    lines.append("")
    lines.append(
        "| rank | N | timing | h | exit | n/yr | PnL/yr | Sharpe | MaxDD | DD%PnL"
        " | fold ± | +0.5 stress |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(top_k_cells, 1):
        lines.append(
            f"| {i} | {c['N']} | {c['entry_timing']} | {c['horizon_bars']} | "
            f"{c['exit_rule']} | {c['annual_trades']:.0f} | {c['annual_pnl_pip']:.1f} | "
            f"{c['sharpe']:.4f} | {c['max_dd_pip']:.1f} | {c['dd_pct_pnl']:.1f}% | "
            f"{c['fold_pos']}/{c['fold_neg']} | {c['annual_pnl_stress_+0.5']:.1f} |"
        )
    lines.append("")

    # Per-fold table for top-10
    lines.append("## Top-10 per-fold PnL (pip)")
    lines.append("")
    lines.append("| rank | f1 | f2 | f3 | f4 | f5 | CV | top concentration |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for i, c in enumerate(top_k_cells, 1):
        lines.append(
            f"| {i} | {c['fold_0_pnl']:.1f} | {c['fold_1_pnl']:.1f} | "
            f"{c['fold_2_pnl']:.1f} | {c['fold_3_pnl']:.1f} | {c['fold_4_pnl']:.1f} | "
            f"{c['fold_pnl_cv']:.2f} | {c['fold_concentration_top']:.1%} |"
        )
    lines.append("")

    # Spread stress table for top-10
    lines.append("## Top-10 spread stress sensitivity (annual PnL, pip)")
    lines.append("")
    lines.append("| rank | base | +0.2 | +0.5 |")
    lines.append("|---|---|---|---|")
    for i, c in enumerate(top_k_cells, 1):
        lines.append(
            f"| {i} | {c['annual_pnl_pip']:.1f} | "
            f"{c['annual_pnl_stress_+0.2']:.1f} | "
            f"{c['annual_pnl_stress_+0.5']:.1f} |"
        )
    lines.append("")

    # best_possible vs realistic gap
    lines.append("## Failure-mode diagnostic — best_possible vs realistic")
    lines.append("")
    lines.append(
        "Per (N, timing, horizon), compare `best_possible_pnl` (post-hoc path peak) "
        "with `tb_pnl` and `time_exit_pnl`. Large gap = path EV exists but exit destroys it; "
        "small gap = no path EV to capture."
    )
    lines.append("")
    keys = [(c["N"], c["entry_timing"], c["horizon_bars"]) for c in top_k_cells]
    seen: set[tuple[int, str, int]] = set()
    lines.append(
        "| N | timing | h | best/yr | tb/yr | time_exit/yr | best - tb | best - time_exit |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for k in keys:
        if k in seen:
            continue
        seen.add(k)
        n, timing, h = k
        sub = sweep_df[
            (sweep_df["N"] == n)
            & (sweep_df["entry_timing"] == timing)
            & (sweep_df["horizon_bars"] == h)
        ]
        rows_by_exit = {row["exit_rule"]: row for _, row in sub.iterrows()}
        if all(r in rows_by_exit for r in EXIT_RULES):
            best = rows_by_exit["best_possible_pnl"]["annual_pnl_pip"]
            tb = rows_by_exit["tb_pnl"]["annual_pnl_pip"]
            te = rows_by_exit["time_exit_pnl"]["annual_pnl_pip"]
            lines.append(
                f"| {n} | {timing} | {h} | {best:.1f} | {tb:.1f} | {te:.1f} | "
                f"{best - tb:+.1f} | {best - te:+.1f} |"
            )
    lines.append("")

    # Entry-timing comparison (new for 22.0c)
    lines.append("## Entry-timing comparison (top cell context)")
    lines.append("")
    if verdict_cell is not None:
        n_top = verdict_cell["N"]
        h_top = verdict_cell["horizon_bars"]
        er_top = verdict_cell["exit_rule"]
        lines.append(
            f"Holding N={n_top}, horizon={h_top}, exit={er_top} fixed; varying entry_timing:"
        )
        lines.append("")
        lines.append("| timing | n/yr | mean_pnl | win_rate | Sharpe | MaxDD | annual_pnl |")
        lines.append("|---|---|---|---|---|---|---|")
        for t in ENTRY_TIMINGS:
            sub = sweep_df[
                (sweep_df["N"] == n_top)
                & (sweep_df["entry_timing"] == t)
                & (sweep_df["horizon_bars"] == h_top)
                & (sweep_df["exit_rule"] == er_top)
            ]
            if sub.empty:
                continue
            row = sub.iloc[0]
            lines.append(
                f"| {t} | {row['annual_trades']:.0f} | {row['mean_pnl']:.3f} | "
                f"{row['win_rate']:.3f} | {row['sharpe']:.4f} | {row['max_dd_pip']:.1f} | "
                f"{row['annual_pnl_pip']:.1f} |"
            )
    lines.append("")

    # Skipped-rate + time-to-fire diagnostic per (N, timing, direction)
    lines.append("## Skipped-trade rate and time-to-fire histogram")
    lines.append("")
    lines.append("Per (N, timing, direction):")
    lines.append("")
    lines.append(
        "| N | timing | dir | n_signals | n_fired | skipped_rate | bars_to_fire 1 / 2 / 3 / 4 / 5 |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for (n, t, d), s in sorted(timing_stats.items()):
        skipped = 1.0 - (s.n_fired / s.n_signals) if s.n_signals else 0.0
        h1 = s.bars_to_fire_hist.get(1, 0)
        h2 = s.bars_to_fire_hist.get(2, 0)
        h3 = s.bars_to_fire_hist.get(3, 0)
        h4 = s.bars_to_fire_hist.get(4, 0)
        h5 = s.bars_to_fire_hist.get(5, 0)
        annot = ""
        if s.n_signals > 0 and skipped > 0.95:
            annot = " *INSUFFICIENT_FIRES*"
        lines.append(
            f"| {n} | {t} | {d} | {s.n_signals} | {s.n_fired} | "
            f"{skipped:.3f}{annot} | {h1} / {h2} / {h3} / {h4} / {h5} |"
        )
    lines.append("")

    # Breakout false-rate (direction-specific)
    lines.append(
        "## Breakout false-rate (direction-specific, mid returns through break "
        "level within 5 M1 bars)"
    )
    lines.append("")
    lines.append("| N | direction | n_signals | n_false | false_rate |")
    lines.append("|---|---|---|---|---|")
    # Aggregate false_breakouts across timings (the false-break flag is direction+window only;
    # but we recompute per (N, timing, direction). Use timing=immediate as reference since
    # mid_path is identical across timings.)
    for n in N_VALUES:
        for d in ("long", "short"):
            s = timing_stats.get((n, "immediate", d))
            if s is None or s.n_signals == 0:
                continue
            fr = s.n_false_breakouts / s.n_signals
            lines.append(f"| {n} | {d} | {s.n_signals} | {s.n_false_breakouts} | {fr:.3f} |")
    lines.append("")

    # Cost diagnostics
    lines.append("## Cost diagnostics for top-10 cells")
    lines.append("")
    for i, (c, diag) in enumerate(zip(top_k_cells, top_k_diagnostics, strict=False), 1):
        lines.append(
            f"### Rank {i}: N={c['N']}, timing={c['entry_timing']}, "
            f"h={c['horizon_bars']}, exit={c['exit_rule']}"
        )
        lines.append("")
        lines.append(f"- median spread_entry: {diag.get('median_spread_entry', 0):.3f} pip")
        lines.append(
            f"- median cost_ratio: {diag.get('median_cost_ratio', 0):.3f} "
            f"(p10 {diag.get('p10_cost_ratio', 0):.3f}, "
            f"p90 {diag.get('p90_cost_ratio', 0):.3f})"
        )
        lines.append("")
        for label, key in (
            ("PnL by cost_ratio bucket", "by_cost_ratio_bucket"),
            ("PnL by spread_entry bucket", "by_spread_bucket"),
            ("PnL by session", "by_session"),
        ):
            lines.append(f"{label}:")
            lines.append("")
            lines.append("| bucket | n | sum | mean |")
            lines.append("|---|---|---|---|")
            for k_, v in diag.get(key, {}).items():
                lines.append(f"| {k_} | {v['n']} | {v['pnl_sum']:.1f} | {v['pnl_mean']:.3f} |")
            lines.append("")
        lines.append("Per-pair contribution (top 10 by absolute PnL):")
        lines.append("")
        lines.append("| pair | n | sum | mean |")
        lines.append("|---|---|---|---|")
        ranked_pairs = sorted(
            diag.get("by_pair", {}).items(),
            key=lambda kv: abs(kv[1]["pnl_sum"]),
            reverse=True,
        )[:10]
        for pair, v in ranked_pairs:
            lines.append(f"| {pair} | {v['n']} | {v['pnl_sum']:.1f} | {v['pnl_mean']:.3f} |")
        lines.append("")

    # NG list compliance
    lines.append("## NG list compliance (postmortem §4)")
    lines.append("")
    lines.append(
        f"- NG#1 pair filter: {len(pairs_used)}/20 pairs evaluated"
        f"{' (missing: ' + ', '.join(pairs_missing) + ')' if pairs_missing else ''}"
        "; no cell-level pair drop ✓"
    )
    lines.append("- NG#2 train-side time filter: not applied — Donchian uses all M5 bars ✓")
    lines.append(
        "- NG#3 test-side filter improvement claim: verdict on all valid+non-gap rows,"
        " not a time-of-day subset ✓"
    )
    lines.append("- NG#4 WeekOpen-aware sample weighting: none ✓")
    lines.append("- NG#5 universe-restricted cross-pair feature: none ✓")
    lines.append("")
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def init_accumulators() -> dict[tuple[int, str, int, str], CellAcc]:
    return {
        (n, timing, h, exit_rule): CellAcc()
        for n in N_VALUES
        for timing in ENTRY_TIMINGS
        for h in HORIZONS
        for exit_rule in EXIT_RULES
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_CANONICAL_20)
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke run on USD_JPY, EUR_USD, GBP_JPY only.",
    )
    args = parser.parse_args(argv)
    if args.smoke:
        args.pairs = ["USD_JPY", "EUR_USD", "GBP_JPY"]
    args.out_dir.mkdir(parents=True, exist_ok=True)

    accumulators = init_accumulators()
    timing_stats: dict[tuple[int, str, str], TimingStats] = {}

    pairs_used: list[str] = []
    pairs_missing: list[str] = []
    print(f"=== Stage 22.0c M5 Donchian Breakout + M1 Entry ({len(args.pairs)} pairs) ===")
    for i, pair in enumerate(args.pairs, 1):
        t0 = time.time()
        try:
            n_valid = process_pair(pair, args.days, accumulators, timing_stats)
        except FileNotFoundError as exc:
            print(f"[{i:2d}/{len(args.pairs)}] {pair}: SKIP (no data: {exc})")
            pairs_missing.append(pair)
            continue
        elapsed = time.time() - t0
        pairs_used.append(pair)
        print(f"[{i:2d}/{len(args.pairs)}] {pair}: valid_label_rows={n_valid:>9} ({elapsed:5.1f}s)")

    sweep_rows: list[dict] = []
    cell_dfs: dict[tuple[int, str, int, str], pd.DataFrame] = {}
    print("Materializing cells and computing metrics ...")
    for cell_key, acc in accumulators.items():
        df = acc.materialize()
        cell_dfs[cell_key] = df
        sweep_rows.append(compute_cell_metrics(cell_key, df))
    sweep_df = pd.DataFrame(sweep_rows)
    sweep_path = args.out_dir / "sweep_results.parquet"
    sweep_df.to_parquet(sweep_path, compression="snappy")
    print(f"Sweep results: {sweep_path}")

    realistic = sweep_df[
        sweep_df["exit_rule"].isin(REALISTIC_EXIT_RULES)
        & (sweep_df["n_trades"] >= MIN_TRADES_FOR_RANKING)
    ]
    top_sorted = realistic.sort_values(
        by=["sharpe", "annual_pnl_pip", "n_trades"],
        ascending=[False, False, False],
    )
    top_k = top_sorted.head(args.top_k).to_dict("records")
    top_k_diags: list[dict] = []
    for c in top_k:
        cell_key = (
            int(c["N"]),
            c["entry_timing"],
            int(c["horizon_bars"]),
            c["exit_rule"],
        )
        df = cell_dfs[cell_key]
        top_k_diags.append(cost_diagnostics(df))

    report_path = write_report(
        sweep_df,
        top_k,
        top_k_diags,
        timing_stats,
        args.out_dir,
        pairs_used,
        pairs_missing,
    )
    print(f"Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
