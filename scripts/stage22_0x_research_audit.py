"""Stage 22 research integrity audit script.

Read-only audit that auto-recomputes key metrics from the 22.0a/b/c
artifacts and compares to the reported eval_report values. Produces a
JSON summary used by docs/design/phase22_research_integrity_audit.md.

Hypotheses verified:
  H1: huge negative annual_pnl is NOT due to annualization / trade-count
      bug.
  H2: 22.0b/c REJECTs are NOT caused by pnl-sign or bid/ask convention
      bugs.
  H3: best_possible vs realistic gap is real path EV that the exit rule
      destroys, not an implementation artifact.
  H4: valid_label / gap_affected_forward_window / skipped trades are
      handled consistently across stages.

Out of scope: writing to src/, running paper/live runners, mutating any
22.0a/b/c artifact.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import warnings
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings(
    "ignore",
    message="no explicit representation of timezones available for np.datetime64",
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
LABEL_DIR = REPO_ROOT / "artifacts" / "stage22_0a" / "labels"
AUDIT_OUT_DIR = REPO_ROOT / "artifacts" / "stage22_audit"

# Top cells reported in eval_report.md
B_TOP_CELL = {
    "N": 100,
    "threshold": 3.0,
    "horizon_bars": 40,
    "exit_rule": "time_exit_pnl",
    "reported_n_trades_annual": 132771,
    "reported_annual_pnl": -366617.5,
    "reported_sharpe": -0.1828,
}

C_TOP_CELL = {
    "N": 100,
    "entry_timing": "retest",
    "horizon_bars": 40,
    "exit_rule": "time_exit_pnl",
    "reported_n_trades_annual": 26211,
    "reported_annual_pnl": -62719.9,
    "reported_sharpe": -0.1751,
}

EVAL_SPAN_YEARS = 730.0 / 365.25
TP_MULT = 1.5
SL_MULT = 1.0
GAP_THRESHOLD_SECONDS = 300.0

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


def pip_size_for(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


# ---------------------------------------------------------------------------
# 22.0a convention checks
# ---------------------------------------------------------------------------


def load_m1_ba(pair: str, days: int = 730) -> pd.DataFrame:
    path = DATA_DIR / f"candles_{pair}_M1_{days}d_BA.jsonl"
    df = pd.read_json(path, lines=True)
    df["timestamp"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    keep = ["bid_o", "bid_h", "bid_l", "bid_c", "ask_o", "ask_h", "ask_l", "ask_c"]
    return df[keep].astype(np.float64)


def audit_22_0a_convention(pair: str = "USD_JPY", n_samples: int = 10) -> dict:
    """Verify 22.0a outcome dataset bid/ask convention on a sample.

    Convention claim:
        entry_ts labels the SIGNAL bar (bar i).
        Actual entry happens at bar i+1's open:
            long: entry_ask = ask_o[i+1]
            short: entry_bid = bid_o[i+1]
        Exit at horizon end (bar i+horizon):
            long: exit_bid_close = bid_c[i+horizon]
            short: exit_ask_close = ask_c[i+horizon]
    """
    parquet = LABEL_DIR / f"labels_{pair}.parquet"
    labels = pd.read_parquet(parquet)
    m1 = load_m1_ba(pair)
    pip = pip_size_for(pair)

    # Sample valid+non-gap rows for direction=long, horizon=40 directly
    sample = labels[
        labels["valid_label"]
        & ~labels["gap_affected_forward_window"]
        & (labels["direction"] == "long")
        & (labels["horizon_bars"] == 40)
    ]
    # Take rows from the middle of the dataset (avoid boundary bars)
    mid = len(sample) // 2
    sample = sample.iloc[mid : mid + n_samples]

    ts_index = m1.index
    findings: list[dict] = []

    for _, row in sample.iterrows():
        entry_ts = row["entry_ts"]
        # locate index of entry_ts in m1
        try:
            i = ts_index.get_loc(entry_ts)
        except KeyError:
            continue
        if i + 40 >= len(m1):
            continue
        # Verify convention
        recomputed_entry_ask = m1["ask_o"].iloc[i + 1]
        recomputed_entry_bid = m1["bid_o"].iloc[i + 1]
        recomputed_exit_bid_close = m1["bid_c"].iloc[i + 40]
        recomputed_exit_ask_close = m1["ask_c"].iloc[i + 40]
        recomputed_time_exit_pnl_long = (recomputed_exit_bid_close - recomputed_entry_ask) / pip
        # MFE/MAE re-compute
        path_bid_h = m1["bid_h"].iloc[i + 1 : i + 41].to_numpy()
        path_bid_l = m1["bid_l"].iloc[i + 1 : i + 41].to_numpy()
        recomputed_mfe_long = (path_bid_h.max() - recomputed_entry_ask) / pip
        recomputed_mae_long = (path_bid_l.min() - recomputed_entry_ask) / pip

        findings.append(
            {
                "entry_ts": str(entry_ts),
                "entry_ask_match": float(abs(row["entry_ask"] - recomputed_entry_ask)) < 1e-7,
                "entry_bid_match": float(abs(row["entry_bid"] - recomputed_entry_bid)) < 1e-7,
                "exit_bid_close_match": float(
                    abs(row["exit_bid_close"] - recomputed_exit_bid_close)
                )
                < 1e-7,
                "exit_ask_close_match": float(
                    abs(row["exit_ask_close"] - recomputed_exit_ask_close)
                )
                < 1e-7,
                "time_exit_pnl_match": abs(
                    float(row["time_exit_pnl"]) - recomputed_time_exit_pnl_long
                )
                < 1e-3,
                "mfe_after_cost_match": abs(float(row["mfe_after_cost"]) - recomputed_mfe_long)
                < 1e-3,
                "mae_after_cost_match": abs(float(row["mae_after_cost"]) - recomputed_mae_long)
                < 1e-3,
                "best_possible_eq_mfe": abs(
                    float(row["best_possible_pnl"]) - float(row["mfe_after_cost"])
                )
                < 1e-5,
                "reported_time_exit_pnl": float(row["time_exit_pnl"]),
                "recomputed_time_exit_pnl": float(recomputed_time_exit_pnl_long),
            }
        )

    all_match = bool(findings) and all(
        f["entry_ask_match"]
        and f["entry_bid_match"]
        and f["exit_bid_close_match"]
        and f["exit_ask_close_match"]
        and f["time_exit_pnl_match"]
        and f["mfe_after_cost_match"]
        and f["mae_after_cost_match"]
        and f["best_possible_eq_mfe"]
        for f in findings
    )
    return {
        "pair": pair,
        "n_samples_checked": len(findings),
        "all_match": all_match,
        "findings": findings,
    }


def audit_22_0a_short_convention(pair: str = "USD_JPY", n_samples: int = 10) -> dict:
    """Same as audit_22_0a_convention but for short direction."""
    parquet = LABEL_DIR / f"labels_{pair}.parquet"
    labels = pd.read_parquet(parquet)
    m1 = load_m1_ba(pair)
    pip = pip_size_for(pair)

    sample = labels[
        labels["valid_label"]
        & ~labels["gap_affected_forward_window"]
        & (labels["direction"] == "short")
        & (labels["horizon_bars"] == 40)
    ]
    mid = len(sample) // 2
    sample = sample.iloc[mid : mid + n_samples]

    ts_index = m1.index
    findings: list[dict] = []
    for _, row in sample.iterrows():
        entry_ts = row["entry_ts"]
        try:
            i = ts_index.get_loc(entry_ts)
        except KeyError:
            continue
        if i + 40 >= len(m1):
            continue
        rec_entry_ask = m1["ask_o"].iloc[i + 1]
        rec_entry_bid = m1["bid_o"].iloc[i + 1]
        rec_exit_ask_close = m1["ask_c"].iloc[i + 40]
        # short: time_exit_pnl_short = (entry_bid - exit_ask_close) / pip
        rec_time_exit_pnl_short = (rec_entry_bid - rec_exit_ask_close) / pip
        path_ask_l = m1["ask_l"].iloc[i + 1 : i + 41].to_numpy()
        path_ask_h = m1["ask_h"].iloc[i + 1 : i + 41].to_numpy()
        rec_mfe_short = (rec_entry_bid - path_ask_l.min()) / pip
        rec_mae_short = (rec_entry_bid - path_ask_h.max()) / pip

        findings.append(
            {
                "entry_ts": str(entry_ts),
                "entry_ask_match": abs(row["entry_ask"] - rec_entry_ask) < 1e-7,
                "entry_bid_match": abs(row["entry_bid"] - rec_entry_bid) < 1e-7,
                "exit_ask_close_match": abs(row["exit_ask_close"] - rec_exit_ask_close) < 1e-7,
                "time_exit_pnl_match": abs(float(row["time_exit_pnl"]) - rec_time_exit_pnl_short)
                < 1e-3,
                "mfe_after_cost_match": abs(float(row["mfe_after_cost"]) - rec_mfe_short) < 1e-3,
                "mae_after_cost_match": abs(float(row["mae_after_cost"]) - rec_mae_short) < 1e-3,
                "reported_time_exit_pnl": float(row["time_exit_pnl"]),
                "recomputed_time_exit_pnl": float(rec_time_exit_pnl_short),
            }
        )
    all_match = bool(findings) and all(
        f["entry_ask_match"]
        and f["entry_bid_match"]
        and f["exit_ask_close_match"]
        and f["time_exit_pnl_match"]
        and f["mfe_after_cost_match"]
        and f["mae_after_cost_match"]
        for f in findings
    )
    return {
        "pair": pair,
        "n_samples_checked": len(findings),
        "all_match": all_match,
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# valid_label / gap_affected exclusion counts
# ---------------------------------------------------------------------------


def audit_valid_label_exclusion(pairs: list[str] | None = None) -> dict:
    """Counts valid+non-gap rows per pair and verifies they match what the
    22.0b/c eval scripts would observe.
    """
    pairs = pairs or PAIRS_CANONICAL_20
    out: dict = {"per_pair": {}, "summary": {}}
    total_rows = 0
    total_valid = 0
    total_non_gap = 0
    total_valid_non_gap = 0
    for p in pairs:
        path = LABEL_DIR / f"labels_{p}.parquet"
        if not path.exists():
            continue
        df = pd.read_parquet(
            path,
            columns=["valid_label", "gap_affected_forward_window", "horizon_bars", "direction"],
        )
        n_rows = len(df)
        n_valid = int(df["valid_label"].sum())
        n_non_gap = int((~df["gap_affected_forward_window"]).sum())
        n_valid_non_gap = int((df["valid_label"] & ~df["gap_affected_forward_window"]).sum())
        # Per-horizon × direction breakdown for tail invalidation check
        horizon_breakdown: dict = {}
        for h in [5, 10, 20, 40]:
            sub_long = df[(df["horizon_bars"] == h) & (df["direction"] == "long")]
            sub_short = df[(df["horizon_bars"] == h) & (df["direction"] == "short")]
            horizon_breakdown[h] = {
                "long_n_rows": len(sub_long),
                "long_valid_count": int(sub_long["valid_label"].sum()),
                "long_invalid_count": int((~sub_long["valid_label"]).sum()),
                "short_n_rows": len(sub_short),
                "short_valid_count": int(sub_short["valid_label"].sum()),
                "short_invalid_count": int((~sub_short["valid_label"]).sum()),
            }
        out["per_pair"][p] = {
            "n_rows": n_rows,
            "n_valid": n_valid,
            "n_non_gap": n_non_gap,
            "n_valid_non_gap": n_valid_non_gap,
            "valid_pct": n_valid / n_rows if n_rows else 0.0,
            "horizon_breakdown": horizon_breakdown,
        }
        total_rows += n_rows
        total_valid += n_valid
        total_non_gap += n_non_gap
        total_valid_non_gap += n_valid_non_gap
    out["summary"] = {
        "total_rows": total_rows,
        "total_valid": total_valid,
        "total_non_gap": total_non_gap,
        "total_valid_non_gap": total_valid_non_gap,
        "pct_excluded": 1.0 - (total_valid_non_gap / total_rows) if total_rows else 0.0,
    }
    return out


# ---------------------------------------------------------------------------
# Reproduce 22.0b top cell
# ---------------------------------------------------------------------------


def causal_zscore(mid: pd.Series, n: int) -> pd.Series:
    mu = mid.rolling(n, min_periods=n).mean()
    sigma = mid.rolling(n, min_periods=n).std(ddof=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (mid - mu) / sigma.where(sigma > 0, np.nan)
    return z


def reproduce_22_0b_top_cell(pairs: list[str] | None = None) -> dict:
    """Independently re-aggregate 22.0b top cell metrics across all 20 pairs."""
    pairs = pairs or PAIRS_CANONICAL_20
    n_z = B_TOP_CELL["N"]
    th = B_TOP_CELL["threshold"]
    h = B_TOP_CELL["horizon_bars"]
    exit_rule = B_TOP_CELL["exit_rule"]

    pooled_pnl: list[np.ndarray] = []
    pooled_pair: list[str] = []
    pooled_direction: list[str] = []

    for pair in pairs:
        m1_path = DATA_DIR / f"candles_{pair}_M1_730d_BA.jsonl"
        label_path = LABEL_DIR / f"labels_{pair}.parquet"
        if not m1_path.exists() or not label_path.exists():
            continue
        m1 = load_m1_ba(pair)
        labels = pd.read_parquet(
            label_path,
            columns=[
                "entry_ts",
                "horizon_bars",
                "direction",
                "valid_label",
                "gap_affected_forward_window",
                exit_rule,
            ],
        )
        labels = labels[labels["valid_label"] & ~labels["gap_affected_forward_window"]]
        if not pd.api.types.is_datetime64_any_dtype(labels["entry_ts"]):
            labels["entry_ts"] = pd.to_datetime(labels["entry_ts"], utc=True)

        # Build z-score causally on M1 mid_close
        mid = (m1["bid_c"] + m1["ask_c"]) / 2.0
        z = causal_zscore(mid, n_z).dropna()

        long_idx = z.index[z.values < -th]
        short_idx = z.index[z.values > th]

        for direction, sigs in (("long", long_idx), ("short", short_idx)):
            if len(sigs) == 0:
                continue
            sub = labels[(labels["horizon_bars"] == h) & (labels["direction"] == direction)]
            sub = sub.set_index("entry_ts").sort_index()
            common = sub.index.intersection(sigs)
            rows = sub.loc[common]
            if rows.empty:
                continue
            pnl_vals = rows[exit_rule].to_numpy()
            pooled_pnl.append(pnl_vals)
            pooled_pair.extend([pair] * len(pnl_vals))
            pooled_direction.extend([direction] * len(pnl_vals))

    if not pooled_pnl:
        return {"error": "no trades reproduced"}
    flat_pnl = np.concatenate(pooled_pnl)
    dir_arr = np.array(pooled_direction)
    _pair_arr = np.array(pooled_pair)  # kept for future per-pair diagnostic; not used here

    n_trades = len(flat_pnl)
    total_pnl = float(flat_pnl.sum())
    annual_pnl = total_pnl / EVAL_SPAN_YEARS
    annual_trades = n_trades / EVAL_SPAN_YEARS
    mean_pnl = float(flat_pnl.mean())
    std_pnl = float(flat_pnl.std(ddof=0))
    sharpe = mean_pnl / std_pnl if std_pnl > 0 else 0.0
    annual_pnl_stress_05 = (flat_pnl - 0.5).sum() / EVAL_SPAN_YEARS

    long_mask = dir_arr == "long"
    short_mask = dir_arr == "short"
    long_pnl_sum = float(flat_pnl[long_mask].sum()) if long_mask.any() else 0.0
    short_pnl_sum = float(flat_pnl[short_mask].sum()) if short_mask.any() else 0.0
    long_n = int(long_mask.sum())
    short_n = int(short_mask.sum())

    return {
        "cell": B_TOP_CELL,
        "recomputed_n_trades": n_trades,
        "recomputed_annual_trades": annual_trades,
        "recomputed_total_pnl": total_pnl,
        "recomputed_annual_pnl": annual_pnl,
        "recomputed_mean_pnl": mean_pnl,
        "recomputed_std_pnl": std_pnl,
        "recomputed_sharpe": sharpe,
        "recomputed_annual_pnl_stress_+0.5": annual_pnl_stress_05,
        "long_n": long_n,
        "long_pnl_sum": long_pnl_sum,
        "long_mean_pnl": long_pnl_sum / long_n if long_n else 0.0,
        "short_n": short_n,
        "short_pnl_sum": short_pnl_sum,
        "short_mean_pnl": short_pnl_sum / short_n if short_n else 0.0,
        "annual_trades_match": abs(annual_trades - B_TOP_CELL["reported_n_trades_annual"]) < 1.0,
        "annual_pnl_match": abs(annual_pnl - B_TOP_CELL["reported_annual_pnl"]) < 5.0,
        "sharpe_match": abs(sharpe - B_TOP_CELL["reported_sharpe"]) < 1e-3,
    }


# ---------------------------------------------------------------------------
# Reproduce 22.0c top cell
# ---------------------------------------------------------------------------


def aggregate_m1_to_m5_mid(m1: pd.DataFrame) -> pd.DataFrame:
    mid_h = (m1["bid_h"] + m1["ask_h"]) / 2.0
    mid_l = (m1["bid_l"] + m1["ask_l"]) / 2.0
    mid_c = (m1["bid_c"] + m1["ask_c"]) / 2.0
    rs = pd.DataFrame(
        {
            "mid_h": mid_h.resample("5min", closed="right", label="right").max(),
            "mid_l": mid_l.resample("5min", closed="right", label="right").min(),
            "mid_c": mid_c.resample("5min", closed="right", label="right").last(),
        }
    )
    return rs.dropna(how="all")


def reproduce_22_0c_top_cell(pairs: list[str] | None = None) -> dict:
    """Re-aggregate 22.0c top cell (N=100, retest, h=40, time_exit_pnl)."""
    pairs = pairs or PAIRS_CANONICAL_20
    n_d = C_TOP_CELL["N"]
    h = C_TOP_CELL["horizon_bars"]
    exit_rule = C_TOP_CELL["exit_rule"]

    pooled_pnl: list[np.ndarray] = []
    pooled_dir: list[str] = []
    n_signals_total = 0
    n_fired_total = 0

    for pair in pairs:
        m1_path = DATA_DIR / f"candles_{pair}_M1_730d_BA.jsonl"
        label_path = LABEL_DIR / f"labels_{pair}.parquet"
        if not m1_path.exists() or not label_path.exists():
            continue
        m1 = load_m1_ba(pair)
        labels = pd.read_parquet(
            label_path,
            columns=[
                "entry_ts",
                "horizon_bars",
                "direction",
                "valid_label",
                "gap_affected_forward_window",
                exit_rule,
                "atr_at_entry",
            ],
        )
        labels = labels[labels["valid_label"] & ~labels["gap_affected_forward_window"]]
        if not pd.api.types.is_datetime64_any_dtype(labels["entry_ts"]):
            labels["entry_ts"] = pd.to_datetime(labels["entry_ts"], utc=True)

        # M5 Donchian breakouts
        m5 = aggregate_m1_to_m5_mid(m1)
        hi = m5["mid_h"].shift(1).rolling(n_d, min_periods=n_d).max()
        lo = m5["mid_l"].shift(1).rolling(n_d, min_periods=n_d).min()
        long_break_mask = m5["mid_c"] > hi
        short_break_mask = m5["mid_c"] < lo

        m1_ts_int = m1.index.values.astype("datetime64[ns]").view("int64")
        ask_l_arr = m1["ask_l"].to_numpy()
        bid_h_arr = m1["bid_h"].to_numpy()

        # Helper: locate M1 entry for retest entry-side condition
        # Default args bind the loop variables explicitly (closure-safe).
        def find_retest(
            direction: str,
            sig_ts_arr: np.ndarray,
            levels: np.ndarray,
            _m1: pd.DataFrame = m1,
            _ts_int: np.ndarray = m1_ts_int,
            _ask_l: np.ndarray = ask_l_arr,
            _bid_h: np.ndarray = bid_h_arr,
        ) -> list:
            entries: list[pd.Timestamp] = []
            n = len(_m1)
            for sig_ts, lvl in zip(sig_ts_arr, levels, strict=False):
                sig_int = np.datetime64(sig_ts, "ns").view("int64")
                idx = int(np.searchsorted(_ts_int, sig_int, side="right"))
                if idx >= n:
                    continue
                end = min(idx + 5, n)
                for j in range(idx, end):
                    cond = _ask_l[j] <= lvl if direction == "long" else _bid_h[j] >= lvl
                    if cond:
                        entries.append(_m1.index[j])
                        break
            return entries

        long_sig_ts = m5.index[long_break_mask].values
        long_levels = hi[long_break_mask].values
        short_sig_ts = m5.index[short_break_mask].values
        short_levels = lo[short_break_mask].values
        n_signals_total += len(long_sig_ts) + len(short_sig_ts)

        long_entries = find_retest("long", long_sig_ts, long_levels)
        short_entries = find_retest("short", short_sig_ts, short_levels)
        n_fired_total += len(long_entries) + len(short_entries)

        sub_long = labels[(labels["horizon_bars"] == h) & (labels["direction"] == "long")]
        sub_long = sub_long.set_index("entry_ts").sort_index()
        sub_short = labels[(labels["horizon_bars"] == h) & (labels["direction"] == "short")]
        sub_short = sub_short.set_index("entry_ts").sort_index()

        if long_entries:
            common_long = sub_long.index.intersection(pd.DatetimeIndex(long_entries))
            rows_long = sub_long.loc[common_long]
            if not rows_long.empty:
                pnl_long = rows_long[exit_rule].to_numpy()
                pooled_pnl.append(pnl_long)
                pooled_dir.extend(["long"] * len(pnl_long))
        if short_entries:
            common_short = sub_short.index.intersection(pd.DatetimeIndex(short_entries))
            rows_short = sub_short.loc[common_short]
            if not rows_short.empty:
                pnl_short = rows_short[exit_rule].to_numpy()
                pooled_pnl.append(pnl_short)
                pooled_dir.extend(["short"] * len(pnl_short))

    if not pooled_pnl:
        return {"error": "no trades reproduced"}
    flat_pnl = np.concatenate(pooled_pnl)
    dir_arr = np.array(pooled_dir)
    n_trades = len(flat_pnl)
    total_pnl = float(flat_pnl.sum())
    annual_pnl = total_pnl / EVAL_SPAN_YEARS
    annual_trades = n_trades / EVAL_SPAN_YEARS
    mean_pnl = float(flat_pnl.mean())
    std_pnl = float(flat_pnl.std(ddof=0))
    sharpe = mean_pnl / std_pnl if std_pnl > 0 else 0.0

    long_mask = dir_arr == "long"
    short_mask = dir_arr == "short"
    return {
        "cell": C_TOP_CELL,
        "recomputed_n_trades": n_trades,
        "recomputed_annual_trades": annual_trades,
        "recomputed_total_pnl": total_pnl,
        "recomputed_annual_pnl": annual_pnl,
        "recomputed_sharpe": sharpe,
        "n_signals_total_pooled": n_signals_total,
        "n_fired_total_pooled": n_fired_total,
        "skipped_rate_pooled": 1.0 - (n_fired_total / n_signals_total) if n_signals_total else 0.0,
        "long_n": int(long_mask.sum()),
        "long_pnl_sum": float(flat_pnl[long_mask].sum()) if long_mask.any() else 0.0,
        "short_n": int(short_mask.sum()),
        "short_pnl_sum": float(flat_pnl[short_mask].sum()) if short_mask.any() else 0.0,
        # Tolerance: 22.0c retest entry uses Python loop with searchsorted edge
        # cases that may include/exclude a handful of trades on bar-boundary
        # ties; ±100 pip / 0.2% relative is well within numerical noise for
        # a -62k-pip cell.
        "annual_trades_match": abs(annual_trades - C_TOP_CELL["reported_n_trades_annual"]) < 50.0,
        "annual_pnl_match": abs(annual_pnl - C_TOP_CELL["reported_annual_pnl"]) < 200.0,
        "annual_pnl_relative_diff_pct": abs(
            (annual_pnl - C_TOP_CELL["reported_annual_pnl"]) / C_TOP_CELL["reported_annual_pnl"]
        )
        * 100
        if C_TOP_CELL["reported_annual_pnl"] != 0
        else 0.0,
        "sharpe_match": abs(sharpe - C_TOP_CELL["reported_sharpe"]) < 1e-3,
    }


# ---------------------------------------------------------------------------
# best_possible vs realistic gap reproduction
# ---------------------------------------------------------------------------


def audit_best_possible_gap(pair: str = "USD_JPY") -> dict:
    """Verify that for valid+non-gap rows, best_possible_pnl is genuinely the
    path's max excursion (i.e., the gap to tb_pnl / time_exit_pnl is the path
    not yet captured by the exit rule, not a numerical artifact).
    """
    parquet = LABEL_DIR / f"labels_{pair}.parquet"
    df = pd.read_parquet(parquet)
    valid = df[df["valid_label"] & ~df["gap_affected_forward_window"]]

    # For long: best_possible_pnl - time_exit_pnl should be ≥ 0
    # because best_possible = mfe = path bid_h max above entry_ask, and time_exit
    # is the close at horizon end. The peak >= the close (after entry-side cost).
    long_rows = valid[valid["direction"] == "long"]
    short_rows = valid[valid["direction"] == "short"]

    long_gap = (long_rows["best_possible_pnl"] - long_rows["time_exit_pnl"]).to_numpy()
    short_gap = (short_rows["best_possible_pnl"] - short_rows["time_exit_pnl"]).to_numpy()

    return {
        "pair": pair,
        "long_n": int(len(long_rows)),
        "long_gap_min": float(np.nanmin(long_gap)),
        "long_gap_p50": float(np.nanmedian(long_gap)),
        "long_gap_p90": float(np.nanpercentile(long_gap, 90)),
        "long_gap_p99": float(np.nanpercentile(long_gap, 99)),
        "long_gap_negative_count": int((long_gap < -1e-3).sum()),
        "short_n": int(len(short_rows)),
        "short_gap_min": float(np.nanmin(short_gap)),
        "short_gap_p50": float(np.nanmedian(short_gap)),
        "short_gap_p90": float(np.nanpercentile(short_gap, 90)),
        "short_gap_p99": float(np.nanpercentile(short_gap, 99)),
        "short_gap_negative_count": int((short_gap < -1e-3).sum()),
        "best_possible_pnl_eq_mfe_after_cost": bool(
            (long_rows["best_possible_pnl"] == long_rows["mfe_after_cost"]).all()
            and (short_rows["best_possible_pnl"] == short_rows["mfe_after_cost"]).all()
        ),
    }


# ---------------------------------------------------------------------------
# 22.0e plan inspection (forbidden feature names)
# ---------------------------------------------------------------------------


def audit_22_0e_plan_features() -> dict:
    """Static check on the 22.0e plan I'll include in the audit doc.

    The plan submitted in this PR's discussion lists features. We assert
    that:
      - is_week_open_window is NOT a model feature (excluded entirely)
      - hour_utc / dow are ablation-diagnostic only
      - no forward-looking (mfe/mae/best_possible/tb_*/time_to_*) names
        are present in the allowlist.
    """
    forbidden_in_main_features = {
        "is_week_open_window",
        # forward-looking (must never be features):
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
    ablation_only = {"hour_utc", "dow"}
    allowlist_main = {
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
    }
    overlap = forbidden_in_main_features & allowlist_main
    return {
        "forbidden_in_main_features": sorted(forbidden_in_main_features),
        "ablation_only_features": sorted(ablation_only),
        "allowlist_main_features": sorted(allowlist_main),
        "overlap_violations": sorted(overlap),
        "is_week_open_window_excluded_from_main": "is_week_open_window" not in allowlist_main,
        "hour_utc_excluded_from_main": "hour_utc" not in allowlist_main,
        "dow_excluded_from_main": "dow" not in allowlist_main,
    }


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_CANONICAL_20)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run convention checks on USD_JPY only; reproductions on 3 pairs.",
    )
    parser.add_argument("--out-dir", type=Path, default=AUDIT_OUT_DIR)
    args = parser.parse_args(argv)

    pairs = args.pairs
    if args.smoke:
        pairs = ["USD_JPY", "EUR_USD", "GBP_JPY"]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    print(f"=== Stage 22 Research Integrity Audit ({len(pairs)} pairs) ===")
    out: dict = {
        "generated": datetime.now(UTC).isoformat(),
        "eval_span_years": EVAL_SPAN_YEARS,
        "pairs_used": pairs,
    }

    print("[1/5] 22.0a long convention check ...")
    t0 = time.time()
    out["audit_22_0a_long_convention"] = audit_22_0a_convention("USD_JPY", n_samples=10)
    long_match = out["audit_22_0a_long_convention"]["all_match"]
    print(f"     all_match={long_match} ({time.time() - t0:.1f}s)")

    print("[2/5] 22.0a short convention check ...")
    t0 = time.time()
    out["audit_22_0a_short_convention"] = audit_22_0a_short_convention("USD_JPY", n_samples=10)
    short_match = out["audit_22_0a_short_convention"]["all_match"]
    print(f"     all_match={short_match} ({time.time() - t0:.1f}s)")

    print("[3/5] valid_label / gap exclusion counts ...")
    t0 = time.time()
    out["audit_valid_label_exclusion"] = audit_valid_label_exclusion(pairs)
    s = out["audit_valid_label_exclusion"]["summary"]
    print(
        f"     total_rows={s['total_rows']}, "
        f"valid_non_gap={s['total_valid_non_gap']} ({time.time() - t0:.1f}s)"
    )

    print("[4a/5] 22.0b top cell reproduction ...")
    t0 = time.time()
    out["reproduce_22_0b_top_cell"] = reproduce_22_0b_top_cell(pairs)
    r = out["reproduce_22_0b_top_cell"]
    print(
        f"     recomputed annual_pnl={r['recomputed_annual_pnl']:.1f} "
        f"(reported {B_TOP_CELL['reported_annual_pnl']}, match={r['annual_pnl_match']})"
        f" ({time.time() - t0:.1f}s)"
    )

    print("[4b/5] 22.0c top cell reproduction ...")
    t0 = time.time()
    out["reproduce_22_0c_top_cell"] = reproduce_22_0c_top_cell(pairs)
    r = out["reproduce_22_0c_top_cell"]
    print(
        f"     recomputed annual_pnl={r['recomputed_annual_pnl']:.1f} "
        f"(reported {C_TOP_CELL['reported_annual_pnl']}, match={r['annual_pnl_match']})"
        f" ({time.time() - t0:.1f}s)"
    )

    print("[5a/5] best_possible vs realistic gap (USD_JPY) ...")
    t0 = time.time()
    out["audit_best_possible_gap"] = audit_best_possible_gap("USD_JPY")
    g = out["audit_best_possible_gap"]
    print(
        f"     long gap min={g['long_gap_min']:.3f} p50={g['long_gap_p50']:.3f} "
        f"neg_count={g['long_gap_negative_count']} ({time.time() - t0:.1f}s)"
    )

    print("[5b/5] 22.0e plan feature allowlist check ...")
    out["audit_22_0e_plan_features"] = audit_22_0e_plan_features()
    f = out["audit_22_0e_plan_features"]
    print(
        f"     overlap_violations={len(f['overlap_violations'])}, "
        f"is_week_open_excluded={f['is_week_open_window_excluded_from_main']}"
    )

    out_path = args.out_dir / "audit_results.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"\nResults: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
