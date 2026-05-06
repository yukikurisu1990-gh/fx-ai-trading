"""Stage 24.0c — Partial-exit variants on frozen entry streams.

Imports the top-K=3 frozen entry streams from 24.0a (all 23.0d M15
first-touch Donchian, horizon=4) and evaluates 9 single-rule
partial-exit variants per cell on M1 path simulation with bid/ask
close discipline (direction-aware) and NG#10 strict close-only causality.

Variants (FIXED constants, NOT searched):
  P1 TP/2-triggered: partial_fraction in {0.25, 0.50, 0.75}
                     trigger = entry +/- 0.75 * ATR (= TP/2)
  P2 time-midpoint:  partial_fraction in {0.25, 0.50, 0.75}
                     trigger at t == HORIZON_M1_BARS // 2 = 30
  P3 MFE-triggered:  K_MFE in {1.0, 1.5, 2.0} x ATR
                     fraction fixed at 0.5
                     long: running_max_bid_close >= entry_ask + K_MFE * ATR
                     short: running_min_ask_close <= entry_bid - K_MFE * ATR
                     partial executed at the same M1 close that first
                     satisfies the trigger; no high/low used

Sweep: 3 frozen cells x (3 + 3 + 3) = 3 x 9 = 27 cells.

CRITICAL — per-bar priority ordering (mandatory unit-tested):
  At any M1 bar where both full TP/SL and partial trigger conditions
  are satisfied, full TP/SL takes priority and the partial trigger
  does NOT fire on that bar.

NG#10 strict close-only: all triggers (TP/SL/partial/MFE running_max)
evaluated at M1 bar close ONLY. Intra-bar high/low NOT used.

Spread treatment (consistent with 23.0a/24.0b):
  Long: triggers + exit at bid_close; pnl uses entry_ask
  Short: triggers + exit at ask_close; pnl uses entry_bid
  Total per-trade pnl: fraction*partial_leg + (1-fraction)*remaining_leg
  if partial_done; else full-position exit pnl

Mandatory clause (verbatim in eval_report.md):
  "All frozen entry streams originate from Phase 23.0d REJECT cells.
  Phase 24.0c tests exit-side capture only; it does not reclassify
  the entry signal itself as ADOPT."

8-gate harness (Phase 22/23 inherited). REJECT reasons inherited from
24.0b including path_ev_unrealisable.

Diagnostics (NOT gates): realised_capture_ratio, partial_hit_rate.

This script touches NO production code, NO DB schema, NO src/ files.
20-pair canonical universe; signal_timeframe=='M15' runtime assertion.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
LABELS_ROOT = REPO_ROOT / "artifacts" / "stage23_0a"
FROZEN_JSON_PATH = REPO_ROOT / "artifacts" / "stage24_0a" / "frozen_entry_streams.json"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage24_0c"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage23_0b = importlib.import_module("stage23_0b_m5_donchian_eval")
stage23_0c = importlib.import_module("stage23_0c_m5_zscore_mr_eval")
stage23_0d = importlib.import_module("stage23_0d_m15_donchian_eval")
stage24_0b = importlib.import_module("stage24_0b_trailing_stop_eval")

PAIRS_20 = stage23_0a.PAIRS_20
SPAN_DAYS = 730
SPAN_YEARS = SPAN_DAYS / 365.25
SIGNAL_TIMEFRAME = "M15"
HORIZON_M1_BARS = 60  # 4 M15 bars * 15 min
MIDPOINT_IDX = HORIZON_M1_BARS // 2  # 30

# Partial-exit constants (FIXED, NOT searched)
PARTIAL_FRACTIONS: tuple[float, ...] = (0.25, 0.50, 0.75)
K_MFE_VALUES: tuple[float, ...] = (1.0, 1.5, 2.0)
P3_FRACTION = 0.5  # P3 fraction fixed

# 23.0a barrier profile (carried from 24.0b)
TP_ATR_MULT = stage24_0b.TP_ATR_MULT  # 1.5
SL_ATR_MULT = stage24_0b.SL_ATR_MULT  # 1.0

# Inherited gate thresholds (Phase 22/23, identical to 24.0b)
A0_MIN_ANNUAL_TRADES = stage23_0b.A0_MIN_ANNUAL_TRADES
A0_OVERTRADING_WARN = stage23_0b.A0_OVERTRADING_WARN
A1_MIN_SHARPE = stage23_0b.A1_MIN_SHARPE
A2_MIN_ANNUAL_PNL = stage23_0b.A2_MIN_ANNUAL_PNL
A3_MAX_MAXDD = stage23_0b.A3_MAX_MAXDD
A4_MIN_POSITIVE_FOLDS = stage23_0b.A4_MIN_POSITIVE_FOLDS
A5_SPREAD_STRESS_PIP = stage23_0b.A5_SPREAD_STRESS_PIP

# Helpers reused
_per_trade_sharpe = stage23_0b._per_trade_sharpe
_max_drawdown_pip = stage23_0b._max_drawdown_pip
_fold_stability = stage23_0b._fold_stability
gate_matrix = stage23_0b.gate_matrix
assign_verdict = stage23_0b.assign_verdict
classify_reject_reason_phase24 = stage24_0b.classify_reject_reason_phase24
load_frozen_streams = stage24_0b.load_frozen_streams


# ---------------------------------------------------------------------------
# Variants
# ---------------------------------------------------------------------------


def _make_variants() -> list[dict]:
    variants: list[dict] = []
    for f in PARTIAL_FRACTIONS:
        variants.append(
            {
                "mode": "P1_tp_half",
                "params": {"fraction": float(f)},
                "label": f"P1_tp_half_frac={f}",
            }
        )
    for f in PARTIAL_FRACTIONS:
        variants.append(
            {
                "mode": "P2_time_midpoint",
                "params": {"fraction": float(f), "midpoint_idx": MIDPOINT_IDX},
                "label": f"P2_midpoint_frac={f}",
            }
        )
    for k in K_MFE_VALUES:
        variants.append(
            {
                "mode": "P3_mfe",
                "params": {"K_MFE": float(k), "fraction": P3_FRACTION},
                "label": f"P3_mfe_K={k}_frac={P3_FRACTION}",
            }
        )
    return variants


VARIANTS = _make_variants()
assert len(VARIANTS) == 9

SMOKE_PAIRS = ["USD_JPY", "EUR_USD", "GBP_JPY"]
SMOKE_VARIANTS = (VARIANTS[1], VARIANTS[4], VARIANTS[7])  # one from each mode


# ---------------------------------------------------------------------------
# P1 — TP/2 triggered partial exit
# ---------------------------------------------------------------------------


def _simulate_p1_long(
    bid_close: np.ndarray, fraction: float, atr_pips: float, entry_ask: float, pip: float
) -> tuple[int, float, str, bool]:
    """Returns (exit_idx, total_pnl_pip, exit_reason, partial_done)."""
    atr_price = atr_pips * pip
    sl = entry_ask - SL_ATR_MULT * atr_price
    tp = entry_ask + TP_ATR_MULT * atr_price
    partial_trigger = entry_ask + 0.5 * TP_ATR_MULT * atr_price  # = entry + 0.75*ATR
    partial_done = False
    partial_pnl_pip = 0.0
    n = len(bid_close)
    for t in range(n):
        bc = bid_close[t]
        # Step 1: full TP/SL check (priority)
        if bc >= tp:
            if partial_done:
                rem = (1.0 - fraction) * (bc - entry_ask) / pip
                return t, partial_pnl_pip + rem, "p1_tp", True
            return t, (bc - entry_ask) / pip, "tp_full_no_partial", False
        if bc <= sl:
            if partial_done:
                rem = (1.0 - fraction) * (bc - entry_ask) / pip
                return t, partial_pnl_pip + rem, "p1_sl", True
            return t, (bc - entry_ask) / pip, "sl_no_partial", False
        # Step 2: partial trigger
        if not partial_done and bc >= partial_trigger:
            partial_pnl_pip = fraction * (bc - entry_ask) / pip
            partial_done = True
    last_bc = bid_close[-1]
    if partial_done:
        rem = (1.0 - fraction) * (last_bc - entry_ask) / pip
        return n - 1, partial_pnl_pip + rem, "p1_time_after_partial", True
    return n - 1, (last_bc - entry_ask) / pip, "time_full", False


def _simulate_p1_short(
    ask_close: np.ndarray, fraction: float, atr_pips: float, entry_bid: float, pip: float
) -> tuple[int, float, str, bool]:
    atr_price = atr_pips * pip
    sl = entry_bid + SL_ATR_MULT * atr_price
    tp = entry_bid - TP_ATR_MULT * atr_price
    partial_trigger = entry_bid - 0.5 * TP_ATR_MULT * atr_price
    partial_done = False
    partial_pnl_pip = 0.0
    n = len(ask_close)
    for t in range(n):
        ac = ask_close[t]
        if ac <= tp:
            if partial_done:
                rem = (1.0 - fraction) * (entry_bid - ac) / pip
                return t, partial_pnl_pip + rem, "p1_tp", True
            return t, (entry_bid - ac) / pip, "tp_full_no_partial", False
        if ac >= sl:
            if partial_done:
                rem = (1.0 - fraction) * (entry_bid - ac) / pip
                return t, partial_pnl_pip + rem, "p1_sl", True
            return t, (entry_bid - ac) / pip, "sl_no_partial", False
        if not partial_done and ac <= partial_trigger:
            partial_pnl_pip = fraction * (entry_bid - ac) / pip
            partial_done = True
    last_ac = ask_close[-1]
    if partial_done:
        rem = (1.0 - fraction) * (entry_bid - last_ac) / pip
        return n - 1, partial_pnl_pip + rem, "p1_time_after_partial", True
    return n - 1, (entry_bid - last_ac) / pip, "time_full", False


# ---------------------------------------------------------------------------
# P2 — time-midpoint partial exit
# ---------------------------------------------------------------------------


def _simulate_p2_long(
    bid_close: np.ndarray,
    fraction: float,
    midpoint_idx: int,
    atr_pips: float,
    entry_ask: float,
    pip: float,
) -> tuple[int, float, str, bool]:
    atr_price = atr_pips * pip
    sl = entry_ask - SL_ATR_MULT * atr_price
    tp = entry_ask + TP_ATR_MULT * atr_price
    partial_done = False
    partial_pnl_pip = 0.0
    n = len(bid_close)
    for t in range(n):
        bc = bid_close[t]
        if bc >= tp:
            if partial_done:
                rem = (1.0 - fraction) * (bc - entry_ask) / pip
                return t, partial_pnl_pip + rem, "p2_tp", True
            return t, (bc - entry_ask) / pip, "tp_full_no_partial", False
        if bc <= sl:
            if partial_done:
                rem = (1.0 - fraction) * (bc - entry_ask) / pip
                return t, partial_pnl_pip + rem, "p2_sl", True
            return t, (bc - entry_ask) / pip, "sl_no_partial", False
        # Step 2: midpoint partial trigger (only if not done and t == midpoint_idx)
        if not partial_done and t == midpoint_idx:
            partial_pnl_pip = fraction * (bc - entry_ask) / pip
            partial_done = True
    last_bc = bid_close[-1]
    if partial_done:
        rem = (1.0 - fraction) * (last_bc - entry_ask) / pip
        return n - 1, partial_pnl_pip + rem, "p2_time_after_partial", True
    return n - 1, (last_bc - entry_ask) / pip, "time_full", False


def _simulate_p2_short(
    ask_close: np.ndarray,
    fraction: float,
    midpoint_idx: int,
    atr_pips: float,
    entry_bid: float,
    pip: float,
) -> tuple[int, float, str, bool]:
    atr_price = atr_pips * pip
    sl = entry_bid + SL_ATR_MULT * atr_price
    tp = entry_bid - TP_ATR_MULT * atr_price
    partial_done = False
    partial_pnl_pip = 0.0
    n = len(ask_close)
    for t in range(n):
        ac = ask_close[t]
        if ac <= tp:
            if partial_done:
                rem = (1.0 - fraction) * (entry_bid - ac) / pip
                return t, partial_pnl_pip + rem, "p2_tp", True
            return t, (entry_bid - ac) / pip, "tp_full_no_partial", False
        if ac >= sl:
            if partial_done:
                rem = (1.0 - fraction) * (entry_bid - ac) / pip
                return t, partial_pnl_pip + rem, "p2_sl", True
            return t, (entry_bid - ac) / pip, "sl_no_partial", False
        if not partial_done and t == midpoint_idx:
            partial_pnl_pip = fraction * (entry_bid - ac) / pip
            partial_done = True
    last_ac = ask_close[-1]
    if partial_done:
        rem = (1.0 - fraction) * (entry_bid - last_ac) / pip
        return n - 1, partial_pnl_pip + rem, "p2_time_after_partial", True
    return n - 1, (entry_bid - last_ac) / pip, "time_full", False


# ---------------------------------------------------------------------------
# P3 — MFE-triggered partial exit (close-only running max/min)
# ---------------------------------------------------------------------------


def _simulate_p3_long(
    bid_close: np.ndarray,
    k_mfe: float,
    fraction: float,
    atr_pips: float,
    entry_ask: float,
    pip: float,
) -> tuple[int, float, str, bool]:
    atr_price = atr_pips * pip
    sl = entry_ask - SL_ATR_MULT * atr_price
    tp = entry_ask + TP_ATR_MULT * atr_price
    mfe_trigger = entry_ask + k_mfe * atr_price
    partial_done = False
    partial_pnl_pip = 0.0
    running_max = -np.inf
    n = len(bid_close)
    for t in range(n):
        bc = bid_close[t]
        # Step 0: update running max (close-only)
        if bc > running_max:
            running_max = bc
        # Step 1: full TP/SL check (priority over MFE partial)
        if bc >= tp:
            if partial_done:
                rem = (1.0 - fraction) * (bc - entry_ask) / pip
                return t, partial_pnl_pip + rem, "p3_tp", True
            return t, (bc - entry_ask) / pip, "tp_full_no_partial", False
        if bc <= sl:
            if partial_done:
                rem = (1.0 - fraction) * (bc - entry_ask) / pip
                return t, partial_pnl_pip + rem, "p3_sl", True
            return t, (bc - entry_ask) / pip, "sl_no_partial", False
        # Step 2: MFE partial trigger
        if not partial_done and running_max >= mfe_trigger:
            partial_pnl_pip = fraction * (bc - entry_ask) / pip
            partial_done = True
    last_bc = bid_close[-1]
    if partial_done:
        rem = (1.0 - fraction) * (last_bc - entry_ask) / pip
        return n - 1, partial_pnl_pip + rem, "p3_time_after_partial", True
    return n - 1, (last_bc - entry_ask) / pip, "time_full", False


def _simulate_p3_short(
    ask_close: np.ndarray,
    k_mfe: float,
    fraction: float,
    atr_pips: float,
    entry_bid: float,
    pip: float,
) -> tuple[int, float, str, bool]:
    atr_price = atr_pips * pip
    sl = entry_bid + SL_ATR_MULT * atr_price
    tp = entry_bid - TP_ATR_MULT * atr_price
    mfe_trigger = entry_bid - k_mfe * atr_price
    partial_done = False
    partial_pnl_pip = 0.0
    running_min = np.inf
    n = len(ask_close)
    for t in range(n):
        ac = ask_close[t]
        if ac < running_min:
            running_min = ac
        if ac <= tp:
            if partial_done:
                rem = (1.0 - fraction) * (entry_bid - ac) / pip
                return t, partial_pnl_pip + rem, "p3_tp", True
            return t, (entry_bid - ac) / pip, "tp_full_no_partial", False
        if ac >= sl:
            if partial_done:
                rem = (1.0 - fraction) * (entry_bid - ac) / pip
                return t, partial_pnl_pip + rem, "p3_sl", True
            return t, (entry_bid - ac) / pip, "sl_no_partial", False
        if not partial_done and running_min <= mfe_trigger:
            partial_pnl_pip = fraction * (entry_bid - ac) / pip
            partial_done = True
    last_ac = ask_close[-1]
    if partial_done:
        rem = (1.0 - fraction) * (entry_bid - last_ac) / pip
        return n - 1, partial_pnl_pip + rem, "p3_time_after_partial", True
    return n - 1, (entry_bid - last_ac) / pip, "time_full", False


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def simulate_variant(
    variant: dict,
    direction: str,
    bid_close: np.ndarray,
    ask_close: np.ndarray,
    atr_pips: float,
    entry_ask: float,
    entry_bid: float,
    pip: float,
) -> tuple[int, float, str, bool]:
    mode = variant["mode"]
    p = variant["params"]
    if mode == "P1_tp_half":
        if direction == "long":
            return _simulate_p1_long(bid_close, p["fraction"], atr_pips, entry_ask, pip)
        return _simulate_p1_short(ask_close, p["fraction"], atr_pips, entry_bid, pip)
    if mode == "P2_time_midpoint":
        if direction == "long":
            return _simulate_p2_long(
                bid_close, p["fraction"], p["midpoint_idx"], atr_pips, entry_ask, pip
            )
        return _simulate_p2_short(
            ask_close, p["fraction"], p["midpoint_idx"], atr_pips, entry_bid, pip
        )
    if mode == "P3_mfe":
        if direction == "long":
            return _simulate_p3_long(bid_close, p["K_MFE"], p["fraction"], atr_pips, entry_ask, pip)
        return _simulate_p3_short(ask_close, p["K_MFE"], p["fraction"], atr_pips, entry_bid, pip)
    raise ValueError(f"Unknown variant mode: {mode}")


# ---------------------------------------------------------------------------
# Per-cell metrics
# ---------------------------------------------------------------------------


def evaluate_cell(trades: pd.DataFrame) -> dict:
    if len(trades) == 0:
        empty = stage24_0b.evaluate_cell(trades).copy()
        empty["partial_hit_rate"] = float("nan")
        return empty
    base_metrics = stage24_0b.evaluate_cell(trades)
    if "partial_done" in trades.columns:
        partial_hit_rate = float(trades["partial_done"].mean())
    else:
        partial_hit_rate = float("nan")
    base_metrics["partial_hit_rate"] = partial_hit_rate
    return base_metrics


# ---------------------------------------------------------------------------
# Sweep runner
# ---------------------------------------------------------------------------


def run_sweep(pairs: list[str], frozen_cells: list[dict], variants: list[dict]) -> list[dict]:
    print(f"--- preloading per-pair M1 / M15 / labels for {len(pairs)} pairs ---")
    unique_ns = sorted({c["cell_params"]["N"] for c in frozen_cells})
    pair_data: dict[str, dict] = {}
    for pair in pairs:
        t0 = time.time()
        m1 = stage23_0a.load_m1_ba(pair, days=SPAN_DAYS)
        m15 = stage23_0a.aggregate_m1_to_tf(m1, "M15")
        m1_idx = m1.index
        bid_c = m1["bid_c"].to_numpy()
        ask_c = m1["ask_c"].to_numpy()
        n_m1 = len(m1_idx)
        m1_pos = pd.Series(np.arange(n_m1, dtype=np.int64), index=m1_idx)
        signals_by_n: dict[int, pd.DataFrame] = {}
        for n in unique_ns:
            sig = stage23_0d.extract_signals_first_touch_donchian(m15, n)
            if "pair" not in sig.columns:
                sig = sig.copy()
                sig["pair"] = pair
            signals_by_n[n] = sig
        labels_m15 = stage23_0b.load_pair_labels(pair, signal_tf=SIGNAL_TIMEFRAME)
        labels_h4 = labels_m15[(labels_m15["horizon_bars"] == 4) & labels_m15["valid_label"]].copy()
        pair_data[pair] = {
            "m1_pos": m1_pos,
            "bid_c": bid_c,
            "ask_c": ask_c,
            "n_m1": n_m1,
            "signals_by_n": signals_by_n,
            "labels_h4": labels_h4,
            "pip": stage23_0a.pip_size_for(pair),
        }
        print(f"  {pair}: m1={n_m1} m15={len(m15)} ({time.time() - t0:5.1f}s)")

    # Per (pair, N) cache for joined trades (independent of variant)
    print("--- joining signals to 23.0a labels (per pair x N) ---")
    pair_n_trades: dict[tuple[str, int], pd.DataFrame] = {}
    for pair in pairs:
        for n in unique_ns:
            sig = pair_data[pair]["signals_by_n"][n]
            labels = pair_data[pair]["labels_h4"]
            joined = pd.merge(
                sig[["entry_ts", "pair", "direction"]],
                labels[
                    [
                        "entry_ts",
                        "pair",
                        "direction",
                        "entry_ask",
                        "entry_bid",
                        "atr_at_entry_signal_tf",
                        "best_possible_pnl",
                        "signal_timeframe",
                    ]
                ],
                on=["entry_ts", "pair", "direction"],
                how="inner",
            )
            pair_n_trades[(pair, n)] = joined

    print(f"--- evaluating {len(frozen_cells)} cells x {len(variants)} variants ---")
    cell_results: list[dict] = []
    for cell_idx, cell in enumerate(frozen_cells):
        n_value = cell["cell_params"]["N"]
        for v_idx, variant in enumerate(variants):
            pooled_parts: list[pd.DataFrame] = []
            for pair in pairs:
                joined = pair_n_trades[(pair, n_value)]
                if len(joined) == 0:
                    continue
                pdata = pair_data[pair]
                pip = pdata["pip"]
                m1_pos = pdata["m1_pos"]
                bid_c = pdata["bid_c"]
                ask_c = pdata["ask_c"]
                n_m1 = pdata["n_m1"]
                pnls: list[float] = []
                reasons: list[str] = []
                exit_idxs: list[int] = []
                partials: list[bool] = []
                for _, row in joined.iterrows():
                    target_m1_ts = pd.Timestamp(row["entry_ts"]) + pd.Timedelta(minutes=1)
                    if target_m1_ts not in m1_pos.index:
                        pnls.append(np.nan)
                        reasons.append("no_entry")
                        exit_idxs.append(-1)
                        partials.append(False)
                        continue
                    entry_m1 = int(m1_pos.loc[target_m1_ts])
                    path_end = entry_m1 + HORIZON_M1_BARS
                    if path_end > n_m1:
                        pnls.append(np.nan)
                        reasons.append("path_too_short")
                        exit_idxs.append(-1)
                        partials.append(False)
                        continue
                    bid_path = bid_c[entry_m1:path_end]
                    ask_path = ask_c[entry_m1:path_end]
                    direction = row["direction"]
                    atr_pips = float(row["atr_at_entry_signal_tf"])
                    entry_ask = float(row["entry_ask"])
                    entry_bid = float(row["entry_bid"])
                    exit_idx, pnl, reason, partial_done = simulate_variant(
                        variant,
                        direction,
                        bid_path,
                        ask_path,
                        atr_pips,
                        entry_ask,
                        entry_bid,
                        pip,
                    )
                    pnls.append(pnl)
                    reasons.append(reason)
                    exit_idxs.append(exit_idx)
                    partials.append(partial_done)
                joined_with_pnl = joined.assign(
                    pnl_pip=pnls,
                    exit_reason=reasons,
                    exit_idx=exit_idxs,
                    partial_done=partials,
                )
                joined_with_pnl = joined_with_pnl.dropna(subset=["pnl_pip"])
                pooled_parts.append(joined_with_pnl)

            trades = pd.concat(pooled_parts, ignore_index=True) if pooled_parts else pd.DataFrame()
            if len(trades) > 0 and (trades["signal_timeframe"] != SIGNAL_TIMEFRAME).any():
                raise RuntimeError(
                    f"NG#6 violation: cell {cell_idx} variant {variant['label']} "
                    f"emitted non-{SIGNAL_TIMEFRAME} rows"
                )
            metrics = evaluate_cell(trades)
            gates = gate_matrix(metrics)
            reject_reason = classify_reject_reason_phase24(metrics, gates)
            cell_results.append(
                {
                    "cell_idx": cell_idx,
                    "frozen_rank": cell["rank"],
                    "frozen_source_stage": cell["source_stage"],
                    "frozen_pr": cell["source_pr"],
                    "frozen_merge_commit": cell["source_merge_commit"],
                    "frozen_verdict": cell["source_verdict"],
                    "frozen_reject_reason": cell["reject_reason"],
                    "cell_params": cell["cell_params"],
                    "variant": variant,
                    "reject_reason": reject_reason,
                    **metrics,
                    **{f"gate_{k}": v for k, v in gates.items()},
                }
            )
            cp = cell["cell_params"]
            gates_bits = "".join(
                "1" if gates[g] else "0" for g in ("A0", "A1", "A2", "A3", "A4", "A5")
            )
            print(
                f"  cell {cell_idx + 1}/{len(frozen_cells)} "
                f"(rank{cell['rank']}, N={cp['N']}, h={cp['horizon_bars']}, "
                f"exit={cp['exit_rule']}) variant {v_idx + 1}/{len(variants)} "
                f"{variant['label']:<32} "
                f"n={metrics['n_trades']:>6} ann_tr={metrics['annual_trades']:8.1f} "
                f"sharpe={metrics['sharpe']:+.4f} ann_pnl={metrics['annual_pnl']:+8.1f} "
                f"capture={metrics['realised_capture_ratio']:+.3f} "
                f"phr={metrics['partial_hit_rate']:.3f} "
                f"gates={gates_bits} reason={reject_reason or '-'}"
            )
    return cell_results


def select_best_cell(cell_results: list[dict]) -> dict | None:
    eligible = [c for c in cell_results if c["gate_A0"] and np.isfinite(c["sharpe"])]
    if not eligible:
        return None
    return max(eligible, key=lambda c: c["sharpe"])


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def write_report(
    out_path: Path,
    cell_results: list[dict],
    pairs: list[str],
    frozen_cells: list[dict],
) -> dict:
    best = select_best_cell(cell_results)
    best_gates = (
        {k.replace("gate_", ""): v for k, v in best.items() if k.startswith("gate_")}
        if best is not None
        else {}
    )
    verdict = assign_verdict(best_gates, None) if best is not None else "REJECT"

    per_cell_verdicts: list[str] = []
    reject_reason_counts: dict[str, int] = {}
    for c in cell_results:
        gates_only = {k.replace("gate_", ""): v for k, v in c.items() if k.startswith("gate_")}
        v = assign_verdict(gates_only, None)
        per_cell_verdicts.append(v)
        if v == "REJECT":
            reason = c.get("reject_reason") or "robustness_failure"
            reject_reason_counts[reason] = reject_reason_counts.get(reason, 0) + 1
    n_reject = sum(1 for v in per_cell_verdicts if v == "REJECT")
    n_promising = sum(1 for v in per_cell_verdicts if v == "PROMISING_BUT_NEEDS_OOS")
    n_adopt_candidate = sum(1 for v in per_cell_verdicts if v == "ADOPT_CANDIDATE")

    lines: list[str] = []
    lines.append("# Stage 24.0c — Partial-Exit Variants on Frozen Entry Streams")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase24_0c_partial_exit.md`")
    lines.append("")
    lines.append("## Mandatory clause")
    lines.append("")
    lines.append(
        "**All frozen entry streams originate from Phase 23.0d REJECT cells. "
        "Phase 24.0c tests exit-side capture only; it does not reclassify the "
        "entry signal itself as ADOPT.** A 24.0c ADOPT_CANDIDATE verdict means "
        '"for this entry stream that Phase 23 rejected, this partial-exit '
        "variant captures enough of the path-EV (per 24.0a) into realised PnL "
        'to clear the gates" — NOT "this entry signal is now adopted". '
        "Production-readiness still requires `24.0c-v2` frozen-cell strict OOS."
    )
    lines.append("")
    lines.append("## NG#10 strict-rule disclosure")
    lines.append("")
    lines.append(
        "All triggers (TP, SL, partial trigger, MFE running max/min) are "
        "evaluated at M1 bar **close only**. Long uses `bid_close`, short uses "
        "`ask_close`. Intra-bar high/low are NOT used. "
        "**Per-bar priority**: at any M1 bar where both full TP/SL and "
        "partial trigger conditions are satisfied, full TP/SL takes priority "
        "and the partial trigger does NOT fire on that bar. Mandatory unit "
        "tests verify this priority for P1, P2, and P3."
    )
    lines.append("")
    lines.append("## Diagnostics disclosure")
    lines.append("")
    lines.append(
        "`realised_capture_ratio = mean(realised_pnl) / mean(best_possible_pnl)` "
        "and `partial_hit_rate = count(partial_done=True) / total_trades` are "
        "**diagnostic-only**. `best_possible_pnl` is an ex-post path peak (after "
        "entry-side spread), not an executable PnL — capture ratio is NOT a "
        "production efficiency metric. `partial_hit_rate` reports how often the "
        "partial trigger fired across the trade population; useful to interpret "
        "per-mode behaviour but not a gate."
    )
    lines.append("")
    lines.append(
        f"Universe: {len(pairs)} pairs (canonical 20). Span = {SPAN_DAYS}d. "
        f"Cells evaluated: {len(cell_results)} ({len(frozen_cells)} frozen × "
        f"{len(VARIANTS)} variants)."
    )
    lines.append("")
    lines.append("## Frozen entry streams (imported from 24.0a)")
    lines.append("")
    lines.append("| rank | source | cell_params | Phase 23 verdict | Phase 23 reject_reason |")
    lines.append("|---|---|---|---|---|")
    for c in frozen_cells:
        cp = c["cell_params"]
        cp_str = ", ".join(f"{k}={v}" for k, v in cp.items())
        lines.append(
            f"| {c['rank']} | {c['source_stage']} (PR #{c['source_pr']}, "
            f"{c['source_merge_commit']}) | {cp_str} | {c['source_verdict']} | "
            f"{c['reject_reason']} |"
        )
    lines.append("")
    lines.append("## Headline verdict")
    lines.append("")
    lines.append(f"**{verdict}**")
    lines.append("")
    lines.append(
        f"Per-cell verdict counts: {n_reject} REJECT / "
        f"{n_promising} PROMISING_BUT_NEEDS_OOS / {n_adopt_candidate} ADOPT_CANDIDATE — "
        f"out of {len(cell_results)} cells."
    )
    lines.append("")
    if reject_reason_counts:
        lines.append("REJECT reason breakdown:")
        for reason in (
            "under_firing",
            "still_overtrading",
            "path_ev_unrealisable",
            "pnl_edge_insufficient",
            "robustness_failure",
        ):
            count = reject_reason_counts.get(reason, 0)
            if count > 0:
                lines.append(f"- {reason}: {count} cell(s)")
        lines.append("")
    if best is not None:
        bv = best["variant"]
        bcp = best["cell_params"]
        lines.append(
            f"**Best cell (max A1 Sharpe among A0-passers):** rank {best['frozen_rank']} "
            f"(N={bcp['N']}, h={bcp['horizon_bars']}, exit_rule={bcp['exit_rule']}) "
            f"× {bv['label']} → Sharpe {best['sharpe']:+.4f}, "
            f"annual_pnl {best['annual_pnl']:+.1f} pip, "
            f"capture {best['realised_capture_ratio']:+.3f}, "
            f"partial_hit_rate {best['partial_hit_rate']:.3f}"
        )
    else:
        lines.append("No cell passed A0 (annual_trades >= 70).")
    lines.append("")
    lines.append("## Per-mode effectiveness (best cell per mode)")
    lines.append("")
    lines.append(
        "| mode | best variant | best Sharpe | best ann_pnl | capture | partial_hit_rate |"
    )
    lines.append("|---|---|---|---|---|---|")
    for mode in ("P1_tp_half", "P2_time_midpoint", "P3_mfe"):
        sub = [c for c in cell_results if c["variant"]["mode"] == mode]
        if not sub:
            lines.append(f"| {mode} | (none) | - | - | - | - |")
            continue
        best_in_mode = max(sub, key=lambda c: c["sharpe"] if np.isfinite(c["sharpe"]) else -1e9)
        lines.append(
            f"| {mode} | {best_in_mode['variant']['label']} | "
            f"{best_in_mode['sharpe']:+.4f} | {best_in_mode['annual_pnl']:+.1f} | "
            f"{best_in_mode['realised_capture_ratio']:+.3f} | "
            f"{best_in_mode['partial_hit_rate']:.3f} |"
        )
    lines.append("")
    lines.append("## Sweep summary (all 27 cells, sorted by Sharpe descending)")
    lines.append("")
    lines.append(
        "| rank_cell | variant | n | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | "
        "A5 stress | capture | phr | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    def _g(c: dict, name: str) -> str:
        return "✓" if c[f"gate_{name}"] else "✗"

    for c in sorted(
        cell_results,
        key=lambda x: x["sharpe"] if np.isfinite(x["sharpe"]) else -1e9,
        reverse=True,
    ):
        cp = c["cell_params"]
        cp_str = f"r{c['frozen_rank']}_N={cp['N']}_h={cp['horizon_bars']}_exit={cp['exit_rule']}"
        lines.append(
            f"| {cp_str} | {c['variant']['label']} | "
            f"{c['n_trades']} | {c['annual_trades']:.1f} | "
            f"{c['sharpe']:+.4f} | {c['annual_pnl']:+.1f} | {c['max_dd']:.1f} | "
            f"{c['a4_n_positive']}/4 | {c['a5_stressed_annual_pnl']:+.1f} | "
            f"{c['realised_capture_ratio']:+.3f} | {c['partial_hit_rate']:.3f} | "
            f"{_g(c, 'A0')} | {_g(c, 'A1')} | {_g(c, 'A2')} | "
            f"{_g(c, 'A3')} | {_g(c, 'A4')} | {_g(c, 'A5')} | "
            f"{c.get('reject_reason') or '-'} |"
        )
    lines.append("")

    lines.append("## Phase 24 routing post-24.0c")
    lines.append("")
    if verdict in ("ADOPT_CANDIDATE", "PROMISING_BUT_NEEDS_OOS"):
        lines.append(
            f"Best cell verdict is **{verdict}**. 24.0d (regime-conditional exits) "
            "still mandatory per kickoff §5. 24.0c-v2 (frozen-cell strict OOS) "
            "becomes a candidate downstream PR — production discussion only "
            "after 24.0c-v2 confirms."
        )
    else:
        lines.append(
            "Best cell verdict is **REJECT**. 24.0c's REJECT does NOT halt Phase 24 — "
            "24.0d continues independently. The partial-exit search space tested here "
            "(3 modes × 9 variants under NG#10 strict close-only) was insufficient to "
            "convert the 24.0a-validated path-EV into realised PnL clearing the 8-gate "
            "harness."
        )
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return {"verdict": verdict, "best": best}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_20)
    parser.add_argument("--frozen-json", type=Path, default=FROZEN_JSON_PATH)
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke run: 3 pairs x 1 frozen cell x 3 variants (1 from each mode).",
    )
    args = parser.parse_args(argv)

    if args.smoke:
        args.pairs = SMOKE_PAIRS
        variants = list(SMOKE_VARIANTS)
        frozen_cells = load_frozen_streams(args.frozen_json)[:1]
    else:
        variants = VARIANTS
        frozen_cells = load_frozen_streams(args.frozen_json)

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 24.0c partial-exit eval ({len(args.pairs)} pairs) ===")
    print(
        f"Frozen cells: {len(frozen_cells)}; Variants: {len(variants)}; "
        f"Total: {len(frozen_cells) * len(variants)}"
    )
    print(
        f"PARTIAL_FRACTIONS={PARTIAL_FRACTIONS}, K_MFE={K_MFE_VALUES}, "
        f"P3_FRACTION={P3_FRACTION}, MIDPOINT_IDX={MIDPOINT_IDX}"
    )
    cell_results = run_sweep(args.pairs, frozen_cells, variants)
    out_path = args.out_dir / "eval_report.md"
    summary = write_report(out_path, cell_results, args.pairs, frozen_cells)
    print(f"\nReport: {out_path}")
    print(f"Verdict: {summary['verdict']}")
    if summary["best"]:
        b = summary["best"]
        print(
            f"Best cell: rank{b['frozen_rank']} {b['variant']['label']} "
            f"Sharpe={b['sharpe']:+.4f} ann_pnl={b['annual_pnl']:+.1f} "
            f"capture={b['realised_capture_ratio']:+.3f} "
            f"phr={b['partial_hit_rate']:.3f}"
        )

    sidecar = args.out_dir / "sweep_results.json"
    sidecar.write_text(json.dumps(cell_results, default=str, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
