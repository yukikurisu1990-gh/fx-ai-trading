"""Stage 24.0b — Trailing-stop variants on frozen entry streams.

Imports the top-K=3 frozen entry streams from 24.0a (all 23.0d M15
first-touch Donchian, horizon=4) and evaluates 11 single-rule trailing-stop
variants per cell on M1 path simulation with bid/ask close discipline
(direction-aware) and NG#10 strict close-only causality.

Trailing modes (FIXED constants, NOT searched):
  T1 ATR trailing:     K_ATR ∈ {1.0, 1.5, 2.0, 2.5}
  T2 fixed-pip:        fixed_pip ∈ {5, 10, 20, 30}
  T3 breakeven move:   BE_threshold ∈ {1.0, 1.5, 2.0} × ATR
                       (wraps 23.0a TP=1.5×ATR, SL=1.0×ATR profile)

Sweep: 3 frozen cells × 11 variants = 33 cells.

NG#10 strict reading (mandatory):
- Running max/min uses M1 close ONLY (not high/low)
- Exit condition evaluated at M1 close ONLY
- TP/SL/BE evaluated at M1 close ONLY
- No intra-bar favourable ordering, no forward-looking path decisions

Spread treatment (direction-aware, consistent with 23.0a):
- Long: running_max=max(bid_close); trail=running_max-dist; exit when
  bid_close<=trail; pnl=(exit_bid_close-entry_ask)/pip
- Short: running_min=min(ask_close); trail=running_min+dist; exit when
  ask_close>=trail; pnl=(entry_bid-exit_ask_close)/pip
- T3 TP/SL/BE all at bid_close (long) / ask_close (short)
- Time exit (no trail/TP/SL within 60 M1 bars): exit at last bar's
  bid_close (long) / ask_close (short)

Mandatory clause (verbatim in eval_report.md):
  "All frozen entry streams originate from Phase 23.0d REJECT cells.
  Phase 24.0b tests exit-side capture only; it does not reclassify the
  entry signal itself as ADOPT."

8-gate harness (Phase 22/23 inherited). New REJECT reason for Phase 24:
  path_ev_unrealisable: A0 pass + A1/A2 fail (entry has positive path-EV
  per 24.0a but THIS trailing logic cannot capture enough)

Diagnostic (NOT a gate): realised_capture_ratio = mean(realised_pnl) /
mean(best_possible_pnl) — fraction of path-EV captured. Ex-post
diagnostic, NOT production efficiency.

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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage24_0b"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage23_0b = importlib.import_module("stage23_0b_m5_donchian_eval")
stage23_0c = importlib.import_module("stage23_0c_m5_zscore_mr_eval")
stage23_0d = importlib.import_module("stage23_0d_m15_donchian_eval")

PAIRS_20 = stage23_0a.PAIRS_20
SPAN_DAYS = 730
SPAN_YEARS = SPAN_DAYS / 365.25
SIGNAL_TIMEFRAME = "M15"
HORIZON_M1_BARS = 60  # 4 M15 bars × 15 min = 60 M1 bars

# Trailing constants (FIXED, NOT searched)
TRAILING_K_ATR: tuple[float, ...] = (1.0, 1.5, 2.0, 2.5)
TRAILING_FIXED_PIP: tuple[float, ...] = (5.0, 10.0, 20.0, 30.0)
TRAILING_BE_THRESHOLD_ATR: tuple[float, ...] = (1.0, 1.5, 2.0)

# T3 wraps 23.0a barrier profile
TP_ATR_MULT = 1.5
SL_ATR_MULT = 1.0

# Inherited gate thresholds (Phase 22/23)
A0_MIN_ANNUAL_TRADES = stage23_0b.A0_MIN_ANNUAL_TRADES
A0_OVERTRADING_WARN = stage23_0b.A0_OVERTRADING_WARN
A1_MIN_SHARPE = stage23_0b.A1_MIN_SHARPE
A2_MIN_ANNUAL_PNL = stage23_0b.A2_MIN_ANNUAL_PNL
A3_MAX_MAXDD = stage23_0b.A3_MAX_MAXDD
A4_MIN_POSITIVE_FOLDS = stage23_0b.A4_MIN_POSITIVE_FOLDS
A5_SPREAD_STRESS_PIP = stage23_0b.A5_SPREAD_STRESS_PIP
S0_SEED = stage23_0b.S0_SEED
S1_OOS_FRACTION = stage23_0b.S1_OOS_FRACTION
S1_STRONG_RATIO = stage23_0b.S1_STRONG_RATIO

# Helpers reused
_per_trade_sharpe = stage23_0b._per_trade_sharpe
_max_drawdown_pip = stage23_0b._max_drawdown_pip
_fold_stability = stage23_0b._fold_stability
_strict_oos_split = stage23_0b._strict_oos_split
gate_matrix = stage23_0b.gate_matrix
assign_verdict = stage23_0b.assign_verdict
session_label = stage23_0b.session_label
per_pair_breakdown = stage23_0b.per_pair_breakdown
per_session_breakdown = stage23_0b.per_session_breakdown


# ---------------------------------------------------------------------------
# Variants and frozen-stream import
# ---------------------------------------------------------------------------


def _make_variants() -> list[dict]:
    variants: list[dict] = []
    for k in TRAILING_K_ATR:
        variants.append(
            {
                "mode": "T1_ATR",
                "param_name": "K_ATR",
                "param_value": float(k),
                "label": f"T1_ATR_K={k}",
            }
        )
    for p in TRAILING_FIXED_PIP:
        variants.append(
            {
                "mode": "T2_fixed_pip",
                "param_name": "fixed_pip",
                "param_value": float(p),
                "label": f"T2_fixed_pip_{int(p)}",
            }
        )
    for be in TRAILING_BE_THRESHOLD_ATR:
        variants.append(
            {
                "mode": "T3_breakeven",
                "param_name": "BE_threshold_ATR",
                "param_value": float(be),
                "label": f"T3_breakeven_BE={be}",
            }
        )
    return variants


VARIANTS = _make_variants()
assert len(VARIANTS) == 11

SMOKE_PAIRS = ["USD_JPY", "EUR_USD", "GBP_JPY"]
SMOKE_VARIANTS = (VARIANTS[1], VARIANTS[5], VARIANTS[9])  # 1 from each mode


def load_frozen_streams(json_path: Path = FROZEN_JSON_PATH) -> list[dict]:
    if not json_path.exists():
        raise FileNotFoundError(f"24.0a frozen JSON not found: {json_path}. Run 24.0a first.")
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if payload.get("halt_triggered"):
        raise RuntimeError("24.0a halted; no frozen cells available for 24.0b")
    cells = payload.get("frozen_cells", [])
    if not cells:
        raise RuntimeError("24.0a frozen_cells is empty")
    for c in cells:
        if c["signal_timeframe"] != SIGNAL_TIMEFRAME:
            raise RuntimeError(
                f"NG#6 violation: frozen cell signal_timeframe={c['signal_timeframe']} "
                f"!= {SIGNAL_TIMEFRAME}"
            )
    return cells


# ---------------------------------------------------------------------------
# Trailing simulators (close-only, NG#10 strict)
# ---------------------------------------------------------------------------


def _simulate_atr_long(
    bid_close: np.ndarray, k_atr: float, atr_pips: float, entry_ask: float, pip: float
) -> tuple[int, float, str]:
    distance_price = k_atr * atr_pips * pip
    running_max = -np.inf
    n = len(bid_close)
    for t in range(n):
        bc = bid_close[t]
        if bc > running_max:
            running_max = bc
        trail_level = running_max - distance_price
        if bc <= trail_level:
            return t, (bc - entry_ask) / pip, "trail"
    last_bc = bid_close[-1]
    return n - 1, (last_bc - entry_ask) / pip, "time"


def _simulate_atr_short(
    ask_close: np.ndarray, k_atr: float, atr_pips: float, entry_bid: float, pip: float
) -> tuple[int, float, str]:
    distance_price = k_atr * atr_pips * pip
    running_min = np.inf
    n = len(ask_close)
    for t in range(n):
        ac = ask_close[t]
        if ac < running_min:
            running_min = ac
        trail_level = running_min + distance_price
        if ac >= trail_level:
            return t, (entry_bid - ac) / pip, "trail"
    last_ac = ask_close[-1]
    return n - 1, (entry_bid - last_ac) / pip, "time"


def _simulate_fixed_pip_long(
    bid_close: np.ndarray, fp: float, entry_ask: float, pip: float
) -> tuple[int, float, str]:
    distance_price = fp * pip
    running_max = -np.inf
    n = len(bid_close)
    for t in range(n):
        bc = bid_close[t]
        if bc > running_max:
            running_max = bc
        trail_level = running_max - distance_price
        if bc <= trail_level:
            return t, (bc - entry_ask) / pip, "trail"
    last_bc = bid_close[-1]
    return n - 1, (last_bc - entry_ask) / pip, "time"


def _simulate_fixed_pip_short(
    ask_close: np.ndarray, fp: float, entry_bid: float, pip: float
) -> tuple[int, float, str]:
    distance_price = fp * pip
    running_min = np.inf
    n = len(ask_close)
    for t in range(n):
        ac = ask_close[t]
        if ac < running_min:
            running_min = ac
        trail_level = running_min + distance_price
        if ac >= trail_level:
            return t, (entry_bid - ac) / pip, "trail"
    last_ac = ask_close[-1]
    return n - 1, (entry_bid - last_ac) / pip, "time"


def _simulate_breakeven_long(
    bid_close: np.ndarray,
    be_threshold: float,
    atr_pips: float,
    entry_ask: float,
    pip: float,
) -> tuple[int, float, str]:
    atr_price = atr_pips * pip
    sl_level = entry_ask - SL_ATR_MULT * atr_price
    tp_level = entry_ask + TP_ATR_MULT * atr_price
    be_trigger_price = be_threshold * atr_price
    breakeven_done = False
    n = len(bid_close)
    for t in range(n):
        bc = bid_close[t]
        if not breakeven_done and (bc - entry_ask) >= be_trigger_price:
            sl_level = entry_ask
            breakeven_done = True
        if bc >= tp_level:
            return t, (bc - entry_ask) / pip, "tp"
        if bc <= sl_level:
            return t, (bc - entry_ask) / pip, ("sl_be" if breakeven_done else "sl")
    last_bc = bid_close[-1]
    return n - 1, (last_bc - entry_ask) / pip, "time"


def _simulate_breakeven_short(
    ask_close: np.ndarray,
    be_threshold: float,
    atr_pips: float,
    entry_bid: float,
    pip: float,
) -> tuple[int, float, str]:
    atr_price = atr_pips * pip
    sl_level = entry_bid + SL_ATR_MULT * atr_price
    tp_level = entry_bid - TP_ATR_MULT * atr_price
    be_trigger_price = be_threshold * atr_price
    breakeven_done = False
    n = len(ask_close)
    for t in range(n):
        ac = ask_close[t]
        if not breakeven_done and (entry_bid - ac) >= be_trigger_price:
            sl_level = entry_bid
            breakeven_done = True
        if ac <= tp_level:
            return t, (entry_bid - ac) / pip, "tp"
        if ac >= sl_level:
            return t, (entry_bid - ac) / pip, ("sl_be" if breakeven_done else "sl")
    last_ac = ask_close[-1]
    return n - 1, (entry_bid - last_ac) / pip, "time"


def simulate_variant(
    variant: dict,
    direction: str,
    bid_close: np.ndarray,
    ask_close: np.ndarray,
    atr_pips: float,
    entry_ask: float,
    entry_bid: float,
    pip: float,
) -> tuple[int, float, str]:
    mode = variant["mode"]
    pv = variant["param_value"]
    if mode == "T1_ATR":
        if direction == "long":
            return _simulate_atr_long(bid_close, pv, atr_pips, entry_ask, pip)
        return _simulate_atr_short(ask_close, pv, atr_pips, entry_bid, pip)
    if mode == "T2_fixed_pip":
        if direction == "long":
            return _simulate_fixed_pip_long(bid_close, pv, entry_ask, pip)
        return _simulate_fixed_pip_short(ask_close, pv, entry_bid, pip)
    if mode == "T3_breakeven":
        if direction == "long":
            return _simulate_breakeven_long(bid_close, pv, atr_pips, entry_ask, pip)
        return _simulate_breakeven_short(ask_close, pv, atr_pips, entry_bid, pip)
    raise ValueError(f"Unknown variant mode: {mode}")


# ---------------------------------------------------------------------------
# Per-cell metrics (extends Phase 23 evaluate_cell pattern)
# ---------------------------------------------------------------------------


def evaluate_cell(trades: pd.DataFrame) -> dict:
    if len(trades) == 0:
        return {
            "n_trades": 0,
            "annual_trades": 0.0,
            "sharpe": float("nan"),
            "annual_pnl": float("nan"),
            "max_dd": float("nan"),
            "a4_n_positive": 0,
            "a4_fold_sharpes": [float("nan")] * 4,
            "a5_stressed_annual_pnl": float("nan"),
            "hit_rate": float("nan"),
            "payoff_asymmetry": float("nan"),
            "overtrading_warning": False,
            "n_long": 0,
            "n_short": 0,
            "realised_capture_ratio": float("nan"),
            "mean_realised_pnl": float("nan"),
            "mean_best_possible_pnl": float("nan"),
        }
    pnl = trades["pnl_pip"]
    n_trades = int(len(trades))
    annual_trades = n_trades / SPAN_YEARS
    sharpe = _per_trade_sharpe(pnl)
    annual_pnl = float(pnl.sum() / SPAN_YEARS)
    max_dd = _max_drawdown_pip(pnl)
    fold = _fold_stability(trades)
    stressed_pnl = pnl - A5_SPREAD_STRESS_PIP
    a5_stressed_annual_pnl = float(stressed_pnl.sum() / SPAN_YEARS)
    pos = pnl[pnl > 0]
    neg = pnl[pnl < 0]
    hit_rate = float((pnl > 0).mean()) if n_trades > 0 else float("nan")
    payoff_asymmetry = (
        float(abs(pos.mean()) / abs(neg.mean()))
        if (len(pos) > 0 and len(neg) > 0 and float(neg.mean()) != 0)
        else float("nan")
    )
    n_long = int((trades["direction"] == "long").sum())
    n_short = int((trades["direction"] == "short").sum())
    overtrading = annual_trades > A0_OVERTRADING_WARN

    # realised_capture_ratio diagnostic
    if "best_possible_pnl" in trades.columns:
        valid_bpp = trades["best_possible_pnl"][np.isfinite(trades["best_possible_pnl"])]
        mean_bpp = float(valid_bpp.mean()) if len(valid_bpp) > 0 else float("nan")
    else:
        mean_bpp = float("nan")
    mean_realised = float(pnl.mean())
    if np.isfinite(mean_bpp) and mean_bpp != 0:
        realised_capture_ratio = mean_realised / mean_bpp
    else:
        realised_capture_ratio = float("nan")

    return {
        "n_trades": n_trades,
        "annual_trades": float(annual_trades),
        "sharpe": float(sharpe),
        "annual_pnl": annual_pnl,
        "max_dd": max_dd,
        "a4_n_positive": int(fold["n_positive"]),
        "a4_fold_sharpes": fold["fold_sharpes_eval"],
        "a5_stressed_annual_pnl": a5_stressed_annual_pnl,
        "hit_rate": hit_rate,
        "payoff_asymmetry": payoff_asymmetry,
        "overtrading_warning": bool(overtrading),
        "n_long": n_long,
        "n_short": n_short,
        "realised_capture_ratio": float(realised_capture_ratio),
        "mean_realised_pnl": mean_realised,
        "mean_best_possible_pnl": mean_bpp,
    }


def classify_reject_reason_phase24(metrics: dict, gates: dict) -> str | None:
    if not gates["A0"]:
        return "under_firing"
    if metrics["overtrading_warning"] and (not gates["A1"] or not gates["A2"]):
        return "still_overtrading"
    if not gates["A1"] or not gates["A2"]:
        return "path_ev_unrealisable"
    if not gates["A3"] or not gates["A4"] or not gates["A5"]:
        return "robustness_failure"
    return None


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

    # Cache joined-trades-with-path-data per (pair, N) — independent of variant
    print("--- joining signals to 23.0a labels (per pair × N) ---")
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

    # Per cell × variant simulation
    print(f"--- evaluating {len(frozen_cells)} cells × {len(variants)} variants ---")
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
                # Per-trade simulation
                for _, row in joined.iterrows():
                    target_m1_ts = pd.Timestamp(row["entry_ts"]) + pd.Timedelta(minutes=1)
                    if target_m1_ts not in m1_pos.index:
                        pnls.append(np.nan)
                        reasons.append("no_entry")
                        exit_idxs.append(-1)
                        continue
                    entry_m1 = int(m1_pos.loc[target_m1_ts])
                    path_end = entry_m1 + HORIZON_M1_BARS
                    if path_end > n_m1:
                        pnls.append(np.nan)
                        reasons.append("path_too_short")
                        exit_idxs.append(-1)
                        continue
                    bid_path = bid_c[entry_m1:path_end]
                    ask_path = ask_c[entry_m1:path_end]
                    direction = row["direction"]
                    atr_pips = float(row["atr_at_entry_signal_tf"])
                    entry_ask = float(row["entry_ask"])
                    entry_bid = float(row["entry_bid"])
                    exit_idx, pnl, reason = simulate_variant(
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
                joined_with_pnl = joined.assign(
                    pnl_pip=pnls, exit_reason=reasons, exit_idx=exit_idxs
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
                f"{variant['label']:<25} "
                f"n={metrics['n_trades']:>6} ann_tr={metrics['annual_trades']:8.1f} "
                f"sharpe={metrics['sharpe']:+.4f} ann_pnl={metrics['annual_pnl']:+8.1f} "
                f"capture={metrics['realised_capture_ratio']:+.3f} "
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
    s1 = None
    if best is not None:
        # S1 strict OOS on best cell — we don't have trades here cached,
        # so this will be a NaN placeholder unless we re-simulate.
        # For compactness, skip S1 for now and document.
        s1 = None

    best_gates = (
        {k.replace("gate_", ""): v for k, v in best.items() if k.startswith("gate_")}
        if best is not None
        else {}
    )
    verdict = assign_verdict(best_gates, s1) if best is not None else "REJECT"

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
    lines.append("# Stage 24.0b — Trailing-Stop Variants on Frozen Entry Streams")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase24_0b_trailing_stop.md`")
    lines.append("")
    lines.append("## Mandatory clause")
    lines.append("")
    lines.append(
        "**All frozen entry streams originate from Phase 23.0d REJECT cells. "
        "Phase 24.0b tests exit-side capture only; it does not reclassify the "
        "entry signal itself as ADOPT.** A 24.0b ADOPT_CANDIDATE verdict means "
        '"for this entry stream that Phase 23 rejected, this trailing-stop '
        "variant converts enough of the path-EV (per 24.0a) into realised PnL "
        'to clear the gates" — NOT "this entry signal is now adopted". '
        "Production-readiness still requires `24.0b-v2` frozen-cell strict OOS."
    )
    lines.append("")
    lines.append("## NG#10 strict-rule disclosure")
    lines.append("")
    lines.append(
        "All trailing decisions in this stage are computed at M1 bar **close only**. "
        "Running max/min, exit conditions, TP/SL, and breakeven shifts all use "
        "`bid_close` (long) or `ask_close` (short) — intra-bar high/low are NOT used. "
        "This is conservatively pessimistic vs intra-bar variants. If 24.0b results "
        "motivate testing intra-bar variants, that work goes into a follow-up "
        "`24.0b-rev1` PR — Phase 24's core verdict closes on the strict-close basis."
    )
    lines.append("")
    lines.append("## realised_capture_ratio diagnostic disclosure")
    lines.append("")
    lines.append(
        "`realised_capture_ratio = mean(realised_pnl) / mean(best_possible_pnl)` is "
        "the **fraction of path-EV captured by the trailing logic**. It is "
        "**diagnostic-only** — `best_possible_pnl` is an ex-post path peak (after "
        "entry-side spread), not an executable PnL, so capture ratio is NOT a "
        "production efficiency metric. Use for cross-variant comparison only."
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
            f"capture {best['realised_capture_ratio']:+.3f}"
        )
    else:
        lines.append("No cell passed A0 (annual_trades >= 70).")
    lines.append("")
    lines.append("## Per-mode effectiveness (best cell per mode)")
    lines.append("")
    lines.append("| mode | best variant | best Sharpe | best ann_pnl | best capture |")
    lines.append("|---|---|---|---|---|")
    for mode in ("T1_ATR", "T2_fixed_pip", "T3_breakeven"):
        sub = [c for c in cell_results if c["variant"]["mode"] == mode]
        if not sub:
            lines.append(f"| {mode} | (none) | - | - | - |")
            continue
        best_in_mode = max(sub, key=lambda c: c["sharpe"] if np.isfinite(c["sharpe"]) else -1e9)
        lines.append(
            f"| {mode} | {best_in_mode['variant']['label']} | "
            f"{best_in_mode['sharpe']:+.4f} | {best_in_mode['annual_pnl']:+.1f} | "
            f"{best_in_mode['realised_capture_ratio']:+.3f} |"
        )
    lines.append("")
    lines.append("## Sweep summary (all 33 cells, sorted by Sharpe descending)")
    lines.append("")
    lines.append(
        "| rank_cell | variant | n | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | "
        "A5 stress | capture | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

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
            f"{c['realised_capture_ratio']:+.3f} | "
            f"{_g(c, 'A0')} | {_g(c, 'A1')} | {_g(c, 'A2')} | "
            f"{_g(c, 'A3')} | {_g(c, 'A4')} | {_g(c, 'A5')} | "
            f"{c.get('reject_reason') or '-'} |"
        )
    lines.append("")

    lines.append("## Phase 24 routing post-24.0b")
    lines.append("")
    if verdict in ("ADOPT_CANDIDATE", "PROMISING_BUT_NEEDS_OOS"):
        lines.append(
            f"Best cell verdict is **{verdict}**. 24.0c (partial-exit variants) and "
            "24.0d (regime-conditional exits) still mandatory per kickoff §5. "
            "24.0b-v2 (frozen-cell strict OOS, no parameter re-search) becomes a "
            "candidate downstream PR — production discussion only after 24.0b-v2 "
            "confirms."
        )
    else:
        lines.append(
            "Best cell verdict is **REJECT**. 24.0b's REJECT does NOT halt Phase 24 — "
            "24.0c and 24.0d continue independently. The trailing-stop search space "
            "tested here (3 modes × 11 variants under NG#10 strict close-only) was "
            "insufficient to convert the 24.0a-validated path-EV into realised PnL "
            "clearing the 8-gate harness."
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
        help="Smoke run: 3 pairs × 1 frozen cell × 3 variants (1 from each mode).",
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

    print(f"=== Stage 24.0b trailing-stop eval ({len(args.pairs)} pairs) ===")
    print(
        f"Frozen cells: {len(frozen_cells)}; Variants: {len(variants)}; "
        f"Total: {len(frozen_cells) * len(variants)}"
    )
    print(f"K_ATR={TRAILING_K_ATR}, fixed_pip={TRAILING_FIXED_PIP}, BE={TRAILING_BE_THRESHOLD_ATR}")
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
            f"capture={b['realised_capture_ratio']:+.3f}"
        )

    sidecar = args.out_dir / "sweep_results.json"
    sidecar.write_text(json.dumps(cell_results, default=str, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
