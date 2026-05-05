"""Stage 23.0a M5/M15 outcome dataset builder.

PR1 of Phase 23. Generates the path-aware outcome datasets that all
subsequent Phase 23 stages will consume. Two timeframes:

- M5 (horizons: 1, 2, 3 bars  = 5, 10, 15 minutes)
- M15 (horizons: 1, 2, 4 bars = 15, 30, 60 minutes)

For each (entry_ts, pair, signal_timeframe, horizon_bars, direction),
records the row schema in `docs/design/phase23_0a_outcome_dataset.md` §3
(key / price / outcome / validity / context / barrier columns).

Aggregation: M1 -> signal-TF, right-closed / right-labeled.
Entry: open of the M1 bar at signal_ts + 1 minute.
Path: horizon_bars * tf_minutes M1 bars from entry inclusive.
Barrier profile: TP=1.5*ATR(14), SL=1.0*ATR(14), ATR on the signal-TF.
Same-bar TP/SL ambiguity: conservative (SL priority).

This script touches NO production code, NO DB schema, NO src/ files.
20-pair canonical universe; no pair / time filter.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage23_0a"

PAIRS_20 = [
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

TF_MINUTES = {"M5": 5, "M15": 15}
HORIZONS_BY_TF: dict[str, tuple[int, ...]] = {
    "M5": (1, 2, 3),
    "M15": (1, 2, 4),
}
DIRECTIONS: tuple[str, ...] = ("long", "short")

BARRIER_PROFILE = "standard"
TP_MULT = 1.5
SL_MULT = 1.0
ATR_PERIOD = 14
GAP_THRESHOLD_SECONDS = 300.0

SCHEMA_VERSION = "23.0a-1"

OUTPUT_COLUMNS: list[str] = [
    # key
    "entry_ts",
    "pair",
    "signal_timeframe",
    "horizon_bars",
    "horizon_minutes",
    "direction",
    # price
    "entry_ask",
    "entry_bid",
    "exit_bid_close",
    "exit_ask_close",
    # outcome
    "tb_pnl",
    "time_exit_pnl",
    "best_possible_pnl",
    "worst_possible_pnl",
    "mfe_after_cost",
    "mae_after_cost",
    "tb_outcome",
    "time_to_tp",
    "time_to_sl",
    "hit_tp",
    "hit_sl",
    "same_bar_tp_sl_ambiguous",
    # validity
    "valid_label",
    "gap_affected_forward_window",
    # context
    "atr_at_entry_signal_tf",
    "spread_entry",
    "cost_ratio",
    # barrier
    "barrier_profile",
    "tp_atr_mult",
    "sl_atr_mult",
    "tp_dist_pip",
    "sl_dist_pip",
    # auxiliary
    "exit_reason",
]


def pip_size_for(pair: str) -> float:
    return 0.01 if pair.endswith("_JPY") else 0.0001


def _parse_oanda_ts(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1]
    if "." in s:
        head, frac = s.split(".", 1)
        frac = frac.rstrip("0")
        if len(frac) > 6:
            frac = frac[:6]
        s = head + ("." + frac if frac else "")
    dt = datetime.fromisoformat(s)
    return dt.replace(tzinfo=UTC)


def load_m1_ba(pair: str, days: int = 730) -> pd.DataFrame:
    path = DATA_DIR / f"candles_{pair}_M1_{days}d_BA.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    rows: list[dict] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            raw = json.loads(line)
            rows.append(
                {
                    "timestamp": _parse_oanda_ts(raw["time"]),
                    "bid_o": float(raw["bid_o"]),
                    "bid_h": float(raw["bid_h"]),
                    "bid_l": float(raw["bid_l"]),
                    "bid_c": float(raw["bid_c"]),
                    "ask_o": float(raw["ask_o"]),
                    "ask_h": float(raw["ask_h"]),
                    "ask_l": float(raw["ask_l"]),
                    "ask_c": float(raw["ask_c"]),
                }
            )
    df = pd.DataFrame(rows).set_index("timestamp")
    df.index = pd.DatetimeIndex(df.index, tz=UTC)
    df = df[~df.index.duplicated(keep="first")].sort_index()
    return df


def aggregate_m1_to_tf(m1_df: pd.DataFrame, tf: str) -> pd.DataFrame:
    """Aggregate M1 candles to a higher TF, right-closed / right-labeled.

    For tf=M5 with M1 timestamps marking the start of each bar, the M5 bar
    labeled T contains the M1 bars whose start times fall in (T - 5min, T].
    Empty bins (e.g., across weekend gaps) are dropped.
    """
    minutes = TF_MINUTES[tf]
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
    return agg.dropna(how="all")


def atr_causal(df: pd.DataFrame, period: int = ATR_PERIOD) -> np.ndarray:
    """Causal ATR on mid prices. Output[i] uses bars 0..i."""
    h_mid = (df["bid_h"].to_numpy() + df["ask_h"].to_numpy()) / 2.0
    l_mid = (df["bid_l"].to_numpy() + df["ask_l"].to_numpy()) / 2.0
    c_mid = (df["bid_c"].to_numpy() + df["ask_c"].to_numpy()) / 2.0
    pc = np.concatenate([[np.nan], c_mid[:-1]])
    tr = np.maximum.reduce([h_mid - l_mid, np.abs(h_mid - pc), np.abs(l_mid - pc)])
    out = np.full(len(tr), np.nan, dtype=np.float64)
    if len(tr) >= period:
        cs = np.cumsum(np.where(np.isnan(tr), 0.0, tr))
        cnt = np.cumsum(~np.isnan(tr))
        for i in range(period - 1, len(tr)):
            window_count = cnt[i] - (cnt[i - period] if i - period >= 0 else 0)
            window_sum = cs[i] - (cs[i - period] if i - period >= 0 else 0.0)
            if window_count == period:
                out[i] = window_sum / period
    return out


def first_hit_idx_2d(hits: np.ndarray) -> np.ndarray:
    """For each row of bool (N, H), return index of first True or -1."""
    if hits.size == 0:
        return np.empty((hits.shape[0],), dtype=np.int64)
    any_hit = hits.any(axis=1)
    first = np.argmax(hits, axis=1)
    return np.where(any_hit, first, -1)


def _derive_exit_reason(
    tb_outcome: np.ndarray, gap_affected: np.ndarray, valid: np.ndarray
) -> np.ndarray:
    n = len(tb_outcome)
    reason = np.empty(n, dtype=object)
    reason[:] = ""
    if n == 0:
        return reason.astype(np.dtypes.StringDType()) if False else reason
    is_tp = (tb_outcome == 1) & valid
    is_sl = (tb_outcome == -1) & valid
    is_time = (tb_outcome == 0) & valid & ~gap_affected
    is_gap = (tb_outcome == 0) & valid & gap_affected
    reason[is_tp] = "tp"
    reason[is_sl] = "sl"
    reason[is_time] = "time"
    reason[is_gap] = "weekend_gap"
    return reason


def compute_pair_rows(
    pair: str,
    m1_df: pd.DataFrame,
    signal_df: pd.DataFrame,
    signal_tf: str,
    horizons: tuple[int, ...],
) -> pd.DataFrame:
    pip = pip_size_for(pair)
    tf_min = TF_MINUTES[signal_tf]

    m1_idx = m1_df.index
    n_m1 = len(m1_idx)
    bid_o = m1_df["bid_o"].to_numpy()
    bid_h = m1_df["bid_h"].to_numpy()
    bid_l = m1_df["bid_l"].to_numpy()
    bid_c = m1_df["bid_c"].to_numpy()
    ask_o = m1_df["ask_o"].to_numpy()
    ask_h = m1_df["ask_h"].to_numpy()
    ask_l = m1_df["ask_l"].to_numpy()
    ask_c = m1_df["ask_c"].to_numpy()

    # Resolution-agnostic M1 deltas
    if n_m1 >= 2:
        diffs = (m1_idx[1:] - m1_idx[:-1]) / pd.Timedelta(seconds=1)
        m1_delta_seconds = np.asarray(diffs, dtype=np.float64)
    else:
        m1_delta_seconds = np.zeros(0, dtype=np.float64)

    signal_idx = signal_df.index
    n_signal = len(signal_idx)

    signal_atr_price = atr_causal(signal_df, ATR_PERIOD)
    signal_atr_pip = signal_atr_price / pip

    # Map each signal_ts to its entry M1 position
    target_entry_ts = signal_idx + pd.Timedelta(minutes=1)
    m1_pos_lookup = pd.Series(np.arange(n_m1, dtype=np.int64), index=m1_idx)
    entry_m1_pos_raw = m1_pos_lookup.reindex(target_entry_ts).to_numpy()
    has_entry = ~np.isnan(entry_m1_pos_raw)
    entry_m1_pos = np.where(has_entry, entry_m1_pos_raw, -1).astype(np.int64)

    # Per-signal entry prices / spread / cost_ratio (signal-bar-level, common to all horizons)
    entry_ask_signal_level = np.full(n_signal, np.nan)
    entry_bid_signal_level = np.full(n_signal, np.nan)
    if has_entry.any():
        ep = entry_m1_pos[has_entry]
        entry_ask_signal_level[has_entry] = ask_o[ep]
        entry_bid_signal_level[has_entry] = bid_o[ep]
    spread_pip = (entry_ask_signal_level - entry_bid_signal_level) / pip
    with np.errstate(divide="ignore", invalid="ignore"):
        cost_ratio = np.where(signal_atr_pip > 0, spread_pip / signal_atr_pip, np.nan)

    blocks: list[pd.DataFrame] = []

    for horizon in horizons:
        path_length = horizon * tf_min
        path_fits = has_entry & ((entry_m1_pos + path_length) <= n_m1)
        atr_ok = np.isfinite(signal_atr_price) & (signal_atr_price > 0)
        valid = path_fits & atr_ok

        n_valid = int(valid.sum())

        # Default-fill arrays (length n_signal, NaN/0/False for invalid)
        entry_ask_full = np.full(n_signal, np.nan)
        entry_bid_full = np.full(n_signal, np.nan)
        exit_bid_close_full = np.full(n_signal, np.nan)
        exit_ask_close_full = np.full(n_signal, np.nan)
        gap_affected_full = np.zeros(n_signal, dtype=bool)

        per_dir_metrics: dict[str, dict[str, np.ndarray]] = {}
        for direction in DIRECTIONS:
            per_dir_metrics[direction] = {
                "mfe": np.full(n_signal, np.nan, dtype=np.float64),
                "mae": np.full(n_signal, np.nan, dtype=np.float64),
                "time_exit_pnl": np.full(n_signal, np.nan, dtype=np.float64),
                "tb_pnl": np.full(n_signal, np.nan, dtype=np.float64),
                "tb_outcome": np.zeros(n_signal, dtype=np.int8),
                "time_to_tp": np.full(n_signal, np.nan, dtype=np.float64),
                "time_to_sl": np.full(n_signal, np.nan, dtype=np.float64),
                "hit_tp": np.zeros(n_signal, dtype=bool),
                "hit_sl": np.zeros(n_signal, dtype=bool),
                "ambig": np.zeros(n_signal, dtype=bool),
            }

        if n_valid > 0:
            valid_entry_m1 = entry_m1_pos[valid]
            offsets = np.arange(path_length, dtype=np.int64)[None, :]
            path_indices = valid_entry_m1[:, None] + offsets

            bh_path = bid_h[path_indices]
            bl_path = bid_l[path_indices]
            bc_path = bid_c[path_indices]
            ah_path = ask_h[path_indices]
            al_path = ask_l[path_indices]
            ac_path = ask_c[path_indices]

            entry_ask_v = ask_o[valid_entry_m1]
            entry_bid_v = bid_o[valid_entry_m1]
            atr_pip_v = signal_atr_pip[valid]
            atr_price_v = signal_atr_price[valid]

            tp_dist_pip_v = TP_MULT * atr_pip_v
            sl_dist_pip_v = SL_MULT * atr_pip_v
            tp_dist_price_v = TP_MULT * atr_price_v
            sl_dist_price_v = SL_MULT * atr_price_v

            exit_bid_close_v = bc_path[:, -1]
            exit_ask_close_v = ac_path[:, -1]

            entry_ask_full[valid] = entry_ask_v
            entry_bid_full[valid] = entry_bid_v
            exit_bid_close_full[valid] = exit_bid_close_v
            exit_ask_close_full[valid] = exit_ask_close_v

            # Gap detection on the forward path's interior deltas
            if path_length >= 2:
                gap_offsets = np.arange(path_length - 1, dtype=np.int64)[None, :]
                gap_indices = valid_entry_m1[:, None] + gap_offsets
                # gap_indices runs from valid_entry_m1 to valid_entry_m1+path_length-2;
                # path_indices' last is valid_entry_m1+path_length-1, so valid implies
                # valid_entry_m1+path_length-1 <= n_m1-1, i.e. gap_indices' max <= n_m1-2,
                # which is len(m1_delta_seconds) - 1 (in-range).
                gap_max_v = m1_delta_seconds[gap_indices].max(axis=1)
                gap_affected_v = gap_max_v > GAP_THRESHOLD_SECONDS
            else:
                gap_affected_v = np.zeros(n_valid, dtype=bool)
            gap_affected_full[valid] = gap_affected_v

            # === long ===
            mfe_long = (bh_path.max(axis=1) - entry_ask_v) / pip
            mae_long = (bl_path.min(axis=1) - entry_ask_v) / pip
            time_exit_pnl_long = (exit_bid_close_v - entry_ask_v) / pip

            tp_trig_long = bh_path >= (entry_ask_v[:, None] + tp_dist_price_v[:, None])
            sl_trig_long = bl_path <= (entry_ask_v[:, None] - sl_dist_price_v[:, None])
            ambig_long = (tp_trig_long & sl_trig_long).any(axis=1)
            hit_tp_long = tp_trig_long.any(axis=1)
            hit_sl_long = sl_trig_long.any(axis=1)

            eff_tp_long = tp_trig_long & ~sl_trig_long
            eff_sl_long = sl_trig_long.copy()
            first_tp_long = first_hit_idx_2d(eff_tp_long)
            first_sl_long = first_hit_idx_2d(eff_sl_long)

            outcome_long = np.zeros(n_valid, dtype=np.int8)
            tp_only = (first_tp_long >= 0) & ((first_sl_long < 0) | (first_tp_long < first_sl_long))
            sl_only = (first_sl_long >= 0) & (
                (first_tp_long < 0) | (first_sl_long <= first_tp_long)
            )
            outcome_long[tp_only] = 1
            outcome_long[sl_only] = -1

            tb_pnl_long = np.where(
                outcome_long == 1,
                tp_dist_pip_v,
                np.where(outcome_long == -1, -sl_dist_pip_v, time_exit_pnl_long),
            )
            ttp_long = np.where(outcome_long == 1, first_tp_long + 1, np.nan)
            tts_long = np.where(outcome_long == -1, first_sl_long + 1, np.nan)

            md = per_dir_metrics["long"]
            md["mfe"][valid] = mfe_long
            md["mae"][valid] = mae_long
            md["time_exit_pnl"][valid] = time_exit_pnl_long
            md["tb_pnl"][valid] = tb_pnl_long
            md["tb_outcome"][valid] = outcome_long
            md["time_to_tp"][valid] = ttp_long
            md["time_to_sl"][valid] = tts_long
            md["hit_tp"][valid] = hit_tp_long
            md["hit_sl"][valid] = hit_sl_long
            md["ambig"][valid] = ambig_long

            # === short ===
            mfe_short = (entry_bid_v - al_path.min(axis=1)) / pip
            mae_short = (entry_bid_v - ah_path.max(axis=1)) / pip
            time_exit_pnl_short = (entry_bid_v - exit_ask_close_v) / pip

            tp_trig_short = al_path <= (entry_bid_v[:, None] - tp_dist_price_v[:, None])
            sl_trig_short = ah_path >= (entry_bid_v[:, None] + sl_dist_price_v[:, None])
            ambig_short = (tp_trig_short & sl_trig_short).any(axis=1)
            hit_tp_short = tp_trig_short.any(axis=1)
            hit_sl_short = sl_trig_short.any(axis=1)

            eff_tp_short = tp_trig_short & ~sl_trig_short
            eff_sl_short = sl_trig_short.copy()
            first_tp_short = first_hit_idx_2d(eff_tp_short)
            first_sl_short = first_hit_idx_2d(eff_sl_short)

            outcome_short = np.zeros(n_valid, dtype=np.int8)
            s_tp_only = (first_tp_short >= 0) & (
                (first_sl_short < 0) | (first_tp_short < first_sl_short)
            )
            s_sl_only = (first_sl_short >= 0) & (
                (first_tp_short < 0) | (first_sl_short <= first_tp_short)
            )
            outcome_short[s_tp_only] = 1
            outcome_short[s_sl_only] = -1

            tb_pnl_short = np.where(
                outcome_short == 1,
                tp_dist_pip_v,
                np.where(outcome_short == -1, -sl_dist_pip_v, time_exit_pnl_short),
            )
            ttp_short = np.where(outcome_short == 1, first_tp_short + 1, np.nan)
            tts_short = np.where(outcome_short == -1, first_sl_short + 1, np.nan)

            md = per_dir_metrics["short"]
            md["mfe"][valid] = mfe_short
            md["mae"][valid] = mae_short
            md["time_exit_pnl"][valid] = time_exit_pnl_short
            md["tb_pnl"][valid] = tb_pnl_short
            md["tb_outcome"][valid] = outcome_short
            md["time_to_tp"][valid] = ttp_short
            md["time_to_sl"][valid] = tts_short
            md["hit_tp"][valid] = hit_tp_short
            md["hit_sl"][valid] = hit_sl_short
            md["ambig"][valid] = ambig_short

        # Common per-row context (NaN for invalid)
        atr_ctx = np.where(valid, signal_atr_pip, np.nan).astype(np.float32)
        spread_ctx = np.where(valid, spread_pip, np.nan).astype(np.float32)
        cost_ctx = np.where(valid, cost_ratio, np.nan).astype(np.float32)
        tp_dist_pip_full = np.where(valid, TP_MULT * signal_atr_pip, np.nan).astype(np.float32)
        sl_dist_pip_full = np.where(valid, SL_MULT * signal_atr_pip, np.nan).astype(np.float32)

        for direction in DIRECTIONS:
            md = per_dir_metrics[direction]
            block = pd.DataFrame(
                {
                    "entry_ts": signal_idx,
                    "pair": pair,
                    "signal_timeframe": signal_tf,
                    "horizon_bars": np.int8(horizon),
                    "horizon_minutes": np.int16(path_length),
                    "direction": direction,
                    "entry_ask": entry_ask_full,
                    "entry_bid": entry_bid_full,
                    "exit_bid_close": exit_bid_close_full,
                    "exit_ask_close": exit_ask_close_full,
                    "tb_pnl": md["tb_pnl"].astype(np.float32),
                    "time_exit_pnl": md["time_exit_pnl"].astype(np.float32),
                    "best_possible_pnl": md["mfe"].astype(np.float32),
                    "worst_possible_pnl": md["mae"].astype(np.float32),
                    "mfe_after_cost": md["mfe"].astype(np.float32),
                    "mae_after_cost": md["mae"].astype(np.float32),
                    "tb_outcome": md["tb_outcome"],
                    "time_to_tp": md["time_to_tp"].astype(np.float32),
                    "time_to_sl": md["time_to_sl"].astype(np.float32),
                    "hit_tp": md["hit_tp"],
                    "hit_sl": md["hit_sl"],
                    "same_bar_tp_sl_ambiguous": md["ambig"],
                    "valid_label": valid,
                    "gap_affected_forward_window": gap_affected_full,
                    "atr_at_entry_signal_tf": atr_ctx,
                    "spread_entry": spread_ctx,
                    "cost_ratio": cost_ctx,
                    "barrier_profile": BARRIER_PROFILE,
                    "tp_atr_mult": np.float32(TP_MULT),
                    "sl_atr_mult": np.float32(SL_MULT),
                    "tp_dist_pip": tp_dist_pip_full,
                    "sl_dist_pip": sl_dist_pip_full,
                    "exit_reason": _derive_exit_reason(md["tb_outcome"], gap_affected_full, valid),
                }
            )
            blocks.append(block)

    out = pd.concat(blocks, ignore_index=True)
    return out[OUTPUT_COLUMNS]


def run_pair_tf(pair: str, signal_tf: str, days: int, out_root: Path) -> dict:
    m1_df = load_m1_ba(pair, days=days)
    signal_df = aggregate_m1_to_tf(m1_df, signal_tf)
    horizons = HORIZONS_BY_TF[signal_tf]
    rows = compute_pair_rows(pair, m1_df, signal_df, signal_tf, horizons)

    out_dir = out_root / f"labels_{signal_tf}"
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = out_dir / f"labels_{signal_tf}_{pair}.parquet"
    pq.write_table(
        pa.Table.from_pandas(rows, preserve_index=False),
        parquet_path,
        compression="snappy",
    )

    valid = rows[rows["valid_label"]]
    n_total = int(len(rows))
    n_valid = int(len(valid))
    summary = {
        "pair": pair,
        "signal_timeframe": signal_tf,
        "n_m1_bars": int(len(m1_df)),
        "n_signal_bars": int(len(signal_df)),
        "n_rows_total": n_total,
        "n_rows_valid": n_valid,
        "coverage": (n_valid / n_total) if n_total > 0 else float("nan"),
        "cost_ratio_p10": float(valid["cost_ratio"].quantile(0.10)) if n_valid else float("nan"),
        "cost_ratio_p50": float(valid["cost_ratio"].quantile(0.50)) if n_valid else float("nan"),
        "cost_ratio_p90": float(valid["cost_ratio"].quantile(0.90)) if n_valid else float("nan"),
        "ambig_rate_long": _ambig_rate(valid, "long"),
        "ambig_rate_short": _ambig_rate(valid, "short"),
        "gap_affected_rate": float(rows["gap_affected_forward_window"].mean())
        if n_total
        else float("nan"),
        "mean_time_exit_long": _mean_finite(valid, "long", "time_exit_pnl"),
        "mean_time_exit_short": _mean_finite(valid, "short", "time_exit_pnl"),
        "mean_spread_pip": float(valid["spread_entry"].mean()) if n_valid else float("nan"),
        "parquet_path": str(parquet_path.relative_to(REPO_ROOT)),
    }
    return summary


def _ambig_rate(valid: pd.DataFrame, direction: str) -> float:
    sub = valid[valid["direction"] == direction]
    if len(sub) == 0:
        return float("nan")
    return float(sub["same_bar_tp_sl_ambiguous"].mean())


def _mean_finite(valid: pd.DataFrame, direction: str, col: str) -> float:
    sub = valid[(valid["direction"] == direction)][col]
    sub = sub[np.isfinite(sub)]
    if len(sub) == 0:
        return float("nan")
    return float(sub.mean())


def write_schema_json(out_root: Path) -> Path:
    schema = {
        "version": SCHEMA_VERSION,
        "generated_at": datetime.now(UTC).isoformat(),
        "row_key": [
            "entry_ts",
            "pair",
            "signal_timeframe",
            "horizon_bars",
            "direction",
        ],
        "signal_timeframes": list(TF_MINUTES.keys()),
        "horizons_by_tf": {k: list(v) for k, v in HORIZONS_BY_TF.items()},
        "tf_minutes": dict(TF_MINUTES),
        "directions": list(DIRECTIONS),
        "barrier_profile": BARRIER_PROFILE,
        "tp_atr_mult": TP_MULT,
        "sl_atr_mult": SL_MULT,
        "atr_period": ATR_PERIOD,
        "gap_threshold_seconds": GAP_THRESHOLD_SECONDS,
        "ambiguity_resolution": "conservative_sl",
        "columns": OUTPUT_COLUMNS,
        "design_doc": "docs/design/phase23_0a_outcome_dataset.md",
        "carried_over_from_22_0a": [
            "entry_ts",
            "pair",
            "horizon_bars",
            "direction",
            "tb_pnl",
            "time_exit_pnl",
            "tb_outcome",
            "time_to_tp",
            "time_to_sl",
            "same_bar_tp_sl_ambiguous",
            "entry_ask",
            "entry_bid",
            "exit_bid_close",
            "exit_ask_close",
            "gap_affected_forward_window",
            "valid_label",
            "mfe_after_cost",
            "mae_after_cost",
            "spread_entry",
            "cost_ratio",
        ],
        "removed_from_22_0a": [
            "path_shape_class",
            "is_week_open_window",
            "hour_utc",
            "dow",
            "atr_at_entry",
        ],
    }
    p = out_root / "label_schema.json"
    p.write_text(json.dumps(schema, indent=2), encoding="utf-8")
    return p


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_20)
    parser.add_argument("--tfs", nargs="*", default=list(TF_MINUTES.keys()), choices=["M5", "M15"])
    parser.add_argument("--days", type=int, default=730)
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke run: 3 pairs only (USD_JPY, EUR_USD, GBP_JPY).",
    )
    args = parser.parse_args(argv)

    if args.smoke:
        args.pairs = ["USD_JPY", "EUR_USD", "GBP_JPY"]

    args.out_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[dict] = []
    print(f"=== Stage 23.0a outcome dataset ({len(args.pairs)} pairs × {args.tfs}) ===")
    for tf in args.tfs:
        print(f"\n[{tf}] horizons={HORIZONS_BY_TF[tf]}")
        for i, pair in enumerate(args.pairs, 1):
            t0 = time.time()
            try:
                s = run_pair_tf(pair, tf, args.days, args.out_dir)
            except FileNotFoundError as exc:
                print(f"  [{i:2d}/{len(args.pairs)}] {pair}: SKIP (no data: {exc})")
                continue
            summaries.append(s)
            elapsed = time.time() - t0
            print(
                f"  [{i:2d}/{len(args.pairs)}] {pair}: m1={s['n_m1_bars']:>7} "
                f"sig={s['n_signal_bars']:>6} rows={s['n_rows_total']:>7} "
                f"valid={s['n_rows_valid']:>7} cov={s['coverage']:.4f} "
                f"cost_ratio_p50={s['cost_ratio_p50']:.3f} ({elapsed:5.1f}s)"
            )

    schema_path = write_schema_json(args.out_dir)
    print(f"\nSchema: {schema_path}")

    summary_json = args.out_dir / "build_summary.json"
    summary_json.write_text(json.dumps(summaries, indent=2, default=str), encoding="utf-8")
    print(f"Build summary: {summary_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
