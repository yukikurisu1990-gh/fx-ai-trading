"""Stage 24.1a — Both-side touch envelope eval (Phase 24 path β implementation).

Implements the C2 envelope confirmed in PR #276 (NG#10 Envelope Confirmation):
- Trigger: bid_high>=TP / bid_low<=SL (long); ask mirror (short). Bar-t-local only.
- Fill: TP exact (limit semantics); SL = min(SL, bid_close) for long /
  max(SL, ask_close) for short (stop-market slippage proxy).
- Same-bar both-hit: SL-first invariant (TP fill never occurs).

This is a *research execution model*, NOT a real-fill guarantee. Live
OANDA fills may differ due to per-tick liquidity, requotes, partial
fills, and microstructure latency.

Sweep: strict 24.0b parity. 33 cells = 3 frozen entry streams x 11
trailing variants (4 T1_ATR + 4 T2_fixed_pip + 3 T3_breakeven). Variants
imported VERBATIM from stage24_0b. No partial / regime variants. No
C1 / C5 / C6 candidates. NG#11 not relaxed. Phase 22 thresholds
unchanged. Frozen entries unchanged.

Routing diagnostics (NOT verdicts; the 8-gate harness is the verdict):
- H1 best Sharpe >= +0.082  -> envelope worked (ADOPT_CANDIDATE / PROMISING)
- H2 best Sharpe lift >= +0.20 vs 24.0b best -0.177 (i.e., new best >=
  +0.023): partial rescue. REJECT but interesting.
- H3 best Sharpe lift < +0.20: no rescue. Routes to gamma recommendation.

This script touches NO production code, NO DB schema, NO src/ files.
20-pair canonical universe; signal_timeframe == 'M15' runtime assertion.
M1 OHLC is loaded from existing stage23_0a.load_m1_ba (already returns
8 OHLC fields; no loader change required).
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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage24_1a"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage23_0b = importlib.import_module("stage23_0b_m5_donchian_eval")
stage23_0d = importlib.import_module("stage23_0d_m15_donchian_eval")
stage24_0b = importlib.import_module("stage24_0b_trailing_stop_eval")

PAIRS_20 = stage23_0a.PAIRS_20
SPAN_DAYS = 730
SIGNAL_TIMEFRAME = "M15"
HORIZON_M1_BARS = 60

# Mandatory variant identity per envelope §8.2: use exactly the same 11 variants
# as stage24_0b. Imported verbatim — DO NOT redefine.
VARIANTS = stage24_0b.VARIANTS
assert len(VARIANTS) == 11, f"Expected 11 24.0b-parity variants, got {len(VARIANTS)}"
TP_ATR_MULT = stage24_0b.TP_ATR_MULT
SL_ATR_MULT = stage24_0b.SL_ATR_MULT

SMOKE_PAIRS = ["USD_JPY", "EUR_USD", "GBP_JPY"]
SMOKE_VARIANTS = (VARIANTS[1], VARIANTS[5], VARIANTS[9])

# Routing diagnostics (FIXED constants per envelope §8.3 / plan §9)
H1_THRESHOLD_SHARPE = 0.082  # >=
H2_LIFT_THRESHOLD = 0.20  # vs 24.0b best of -0.177 -> H2_NEW_SHARPE_THRESHOLD = +0.023
PHASE_24_0B_BEST_SHARPE = -0.177
H2_NEW_SHARPE_THRESHOLD = PHASE_24_0B_BEST_SHARPE + H2_LIFT_THRESHOLD  # +0.023

# Inherited gate thresholds
A0_MIN_ANNUAL_TRADES = stage23_0b.A0_MIN_ANNUAL_TRADES
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
# C2 envelope simulators (NG#10-relaxed; PR #276 envelope §3)
# ---------------------------------------------------------------------------


def _simulate_atr_long_envelope(
    bid_h: np.ndarray,
    bid_l: np.ndarray,
    bid_c: np.ndarray,
    k_atr: float,
    atr_pips: float,
    entry_ask: float,
    pip: float,
) -> tuple[int, float, str]:
    """Trail with ATR distance. Trail level computed from running max of
    bid_close (envelope §3.4 prohibits OHLC outside trigger / SL slippage).
    Trigger on bid_low <= trail_level (touch). Fill at min(trail_level,
    bid_close) (worst-of-bar slippage).
    """
    distance_price = k_atr * atr_pips * pip
    running_max = -np.inf
    n = len(bid_c)
    for t in range(n):
        bc = bid_c[t]
        if bc > running_max:
            running_max = bc
        trail_level = running_max - distance_price
        if bid_l[t] <= trail_level:
            fill = min(trail_level, bc)
            return t, (fill - entry_ask) / pip, "trail"
    last_bc = bid_c[-1]
    return n - 1, (last_bc - entry_ask) / pip, "time"


def _simulate_atr_short_envelope(
    ask_h: np.ndarray,
    ask_l: np.ndarray,
    ask_c: np.ndarray,
    k_atr: float,
    atr_pips: float,
    entry_bid: float,
    pip: float,
) -> tuple[int, float, str]:
    distance_price = k_atr * atr_pips * pip
    running_min = np.inf
    n = len(ask_c)
    for t in range(n):
        ac = ask_c[t]
        if ac < running_min:
            running_min = ac
        trail_level = running_min + distance_price
        if ask_h[t] >= trail_level:
            fill = max(trail_level, ac)
            return t, (entry_bid - fill) / pip, "trail"
    last_ac = ask_c[-1]
    return n - 1, (entry_bid - last_ac) / pip, "time"


def _simulate_fixed_pip_long_envelope(
    bid_h: np.ndarray,
    bid_l: np.ndarray,
    bid_c: np.ndarray,
    fp: float,
    entry_ask: float,
    pip: float,
) -> tuple[int, float, str]:
    distance_price = fp * pip
    running_max = -np.inf
    n = len(bid_c)
    for t in range(n):
        bc = bid_c[t]
        if bc > running_max:
            running_max = bc
        trail_level = running_max - distance_price
        if bid_l[t] <= trail_level:
            fill = min(trail_level, bc)
            return t, (fill - entry_ask) / pip, "trail"
    last_bc = bid_c[-1]
    return n - 1, (last_bc - entry_ask) / pip, "time"


def _simulate_fixed_pip_short_envelope(
    ask_h: np.ndarray,
    ask_l: np.ndarray,
    ask_c: np.ndarray,
    fp: float,
    entry_bid: float,
    pip: float,
) -> tuple[int, float, str]:
    distance_price = fp * pip
    running_min = np.inf
    n = len(ask_c)
    for t in range(n):
        ac = ask_c[t]
        if ac < running_min:
            running_min = ac
        trail_level = running_min + distance_price
        if ask_h[t] >= trail_level:
            fill = max(trail_level, ac)
            return t, (entry_bid - fill) / pip, "trail"
    last_ac = ask_c[-1]
    return n - 1, (entry_bid - last_ac) / pip, "time"


def _simulate_breakeven_long_envelope(
    bid_h: np.ndarray,
    bid_l: np.ndarray,
    bid_c: np.ndarray,
    be_threshold: float,
    atr_pips: float,
    entry_ask: float,
    pip: float,
) -> tuple[int, float, str]:
    """BE state change uses bid_close (per envelope §3.4). TP/SL exit
    triggers use OHLC touch with envelope fill semantics. Same-bar both-hit:
    SL-first invariant (envelope §3.3).
    """
    atr_price = atr_pips * pip
    sl_level = entry_ask - SL_ATR_MULT * atr_price
    tp_level = entry_ask + TP_ATR_MULT * atr_price
    be_trigger_price = be_threshold * atr_price
    breakeven_done = False
    n = len(bid_c)
    for t in range(n):
        bc = bid_c[t]
        bh = bid_h[t]
        bl = bid_l[t]
        # BE state change (close-based, NOT OHLC trigger)
        if not breakeven_done and (bc - entry_ask) >= be_trigger_price:
            sl_level = entry_ask
            breakeven_done = True
        sl_hit = bl <= sl_level
        tp_hit = bh >= tp_level
        if sl_hit:
            fill = min(sl_level, bc)
            return t, (fill - entry_ask) / pip, ("sl_be" if breakeven_done else "sl")
        if tp_hit:
            return t, (tp_level - entry_ask) / pip, "tp"
    last_bc = bid_c[-1]
    return n - 1, (last_bc - entry_ask) / pip, "time"


def _simulate_breakeven_short_envelope(
    ask_h: np.ndarray,
    ask_l: np.ndarray,
    ask_c: np.ndarray,
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
    n = len(ask_c)
    for t in range(n):
        ac = ask_c[t]
        ah = ask_h[t]
        al = ask_l[t]
        if not breakeven_done and (entry_bid - ac) >= be_trigger_price:
            sl_level = entry_bid
            breakeven_done = True
        sl_hit = ah >= sl_level
        tp_hit = al <= tp_level
        if sl_hit:
            fill = max(sl_level, ac)
            return t, (entry_bid - fill) / pip, ("sl_be" if breakeven_done else "sl")
        if tp_hit:
            return t, (entry_bid - tp_level) / pip, "tp"
    last_ac = ask_c[-1]
    return n - 1, (entry_bid - last_ac) / pip, "time"


def simulate_variant_envelope(
    variant: dict,
    direction: str,
    bid_h: np.ndarray,
    bid_l: np.ndarray,
    bid_c: np.ndarray,
    ask_h: np.ndarray,
    ask_l: np.ndarray,
    ask_c: np.ndarray,
    atr_pips: float,
    entry_ask: float,
    entry_bid: float,
    pip: float,
) -> tuple[int, float, str]:
    mode = variant["mode"]
    pv = variant["param_value"]
    if mode == "T1_ATR":
        if direction == "long":
            return _simulate_atr_long_envelope(bid_h, bid_l, bid_c, pv, atr_pips, entry_ask, pip)
        return _simulate_atr_short_envelope(ask_h, ask_l, ask_c, pv, atr_pips, entry_bid, pip)
    if mode == "T2_fixed_pip":
        if direction == "long":
            return _simulate_fixed_pip_long_envelope(bid_h, bid_l, bid_c, pv, entry_ask, pip)
        return _simulate_fixed_pip_short_envelope(ask_h, ask_l, ask_c, pv, entry_bid, pip)
    if mode == "T3_breakeven":
        if direction == "long":
            return _simulate_breakeven_long_envelope(
                bid_h, bid_l, bid_c, pv, atr_pips, entry_ask, pip
            )
        return _simulate_breakeven_short_envelope(ask_h, ask_l, ask_c, pv, atr_pips, entry_bid, pip)
    raise ValueError(f"Unknown variant mode: {mode}")


# ---------------------------------------------------------------------------
# Per-cell metrics (same as 24.0b)
# ---------------------------------------------------------------------------


evaluate_cell = stage24_0b.evaluate_cell


# ---------------------------------------------------------------------------
# Sweep runner
# ---------------------------------------------------------------------------


def run_sweep(pairs: list[str], frozen_cells: list[dict], variants: list[dict]) -> list[dict]:
    print(f"--- preloading per-pair M1 OHLC / M15 / labels for {len(pairs)} pairs ---")
    unique_ns = sorted({c["cell_params"]["N"] for c in frozen_cells})
    pair_data: dict[str, dict] = {}
    for pair in pairs:
        t0 = time.time()
        m1 = stage23_0a.load_m1_ba(pair, days=SPAN_DAYS)
        m15 = stage23_0a.aggregate_m1_to_tf(m1, "M15")
        m1_idx = m1.index
        bid_h = m1["bid_h"].to_numpy()
        bid_l = m1["bid_l"].to_numpy()
        bid_c = m1["bid_c"].to_numpy()
        ask_h = m1["ask_h"].to_numpy()
        ask_l = m1["ask_l"].to_numpy()
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
            "bid_h": bid_h,
            "bid_l": bid_l,
            "bid_c": bid_c,
            "ask_h": ask_h,
            "ask_l": ask_l,
            "ask_c": ask_c,
            "n_m1": n_m1,
            "signals_by_n": signals_by_n,
            "labels_h4": labels_h4,
            "pip": stage23_0a.pip_size_for(pair),
        }
        print(f"  {pair}: m1={n_m1} m15={len(m15)} ({time.time() - t0:5.1f}s)")

    # Per (pair, N) joined-trades cache
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
                bid_h = pdata["bid_h"]
                bid_l = pdata["bid_l"]
                bid_c = pdata["bid_c"]
                ask_h = pdata["ask_h"]
                ask_l = pdata["ask_l"]
                ask_c = pdata["ask_c"]
                n_m1 = pdata["n_m1"]
                pnls: list[float] = []
                reasons: list[str] = []
                exit_idxs: list[int] = []
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
                    direction = row["direction"]
                    atr_pips = float(row["atr_at_entry_signal_tf"])
                    entry_ask = float(row["entry_ask"])
                    entry_bid = float(row["entry_bid"])
                    exit_idx, pnl, reason = simulate_variant_envelope(
                        variant,
                        direction,
                        bid_h[entry_m1:path_end],
                        bid_l[entry_m1:path_end],
                        bid_c[entry_m1:path_end],
                        ask_h[entry_m1:path_end],
                        ask_l[entry_m1:path_end],
                        ask_c[entry_m1:path_end],
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
# Routing diagnostics (H1/H2/H3)
# ---------------------------------------------------------------------------


def classify_routing_hypothesis(best: dict | None) -> tuple[str, str]:
    """Returns (label, narrative)."""
    if best is None or not np.isfinite(best["sharpe"]):
        return "H3", (
            "no A0-passing cell with finite Sharpe; envelope provides no rescue. "
            "Recommends gamma hard close per envelope §9."
        )
    s = float(best["sharpe"])
    lift = s - PHASE_24_0B_BEST_SHARPE
    if s >= H1_THRESHOLD_SHARPE:
        return "H1", (
            f"best Sharpe {s:+.4f} >= A1 threshold {H1_THRESHOLD_SHARPE:+.4f}. "
            "Envelope works at the strategy gate level — final verdict still "
            "depends on the 8-gate harness output (A2-A5 must also clear)."
        )
    if lift >= H2_LIFT_THRESHOLD:
        return "H2", (
            f"best Sharpe {s:+.4f}; lift {lift:+.4f} vs 24.0b best "
            f"{PHASE_24_0B_BEST_SHARPE:+.4f} >= +{H2_LIFT_THRESHOLD:.2f}. "
            "Partial rescue — REJECT but interesting; envelope alone insufficient "
            "to clear A1; routing decision deferred to user."
        )
    return "H3", (
        f"best Sharpe {s:+.4f}; lift {lift:+.4f} < +{H2_LIFT_THRESHOLD:.2f}. "
        "No rescue — envelope does not lift Sharpe meaningfully. Recommends "
        "gamma hard close under current data/execution assumptions per envelope "
        "§9, unless user requests new data/execution audit."
    )


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
    h_label, h_narrative = classify_routing_hypothesis(best)

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
    lines.append("# Stage 24.1a — Both-Side Touch Envelope Eval (Phase 24 path β)")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Envelope contract: `docs/design/ng10_envelope_confirmation.md` (PR #276)")
    lines.append("")
    lines.append("## Mandatory clauses")
    lines.append("")
    lines.append(
        "**Fills follow the NG#10-relaxed envelope confirmed in PR #276; this "
        "is a research execution model and not a real-fill guarantee.** Live "
        "OANDA fills may differ due to per-tick liquidity, requotes, partial "
        "fills, and microstructure latency. Production-readiness still "
        "requires an X-v2-equivalent frozen-OOS PR (Phase 22 gating)."
    )
    lines.append("")
    lines.append(
        "**TP fills at the limit price exactly (limits do not slip); SL fills "
        "via min(SL, bid_close) for long / max(SL, ask_close) for short "
        "(stop-market slippage proxy).** This asymmetry maps to OANDA "
        "structural reality (TP=limit / SL=stop-market)."
    )
    lines.append("")
    lines.append(
        "**Same-bar both-hit fills SL using the §3.2 SL formula; the TP fill "
        "never occurs in a same-bar both-hit (SL-first invariant from envelope "
        "§3.3).** This is a research-model conservatism, not a OANDA semantic."
    )
    lines.append("")
    lines.append(
        "**All frozen entry streams originate from Phase 23.0d REJECT cells.** "
        "Phase 24.1a tests exit-side capture under the relaxed envelope only; "
        "it does not reclassify the entry signal itself as ADOPT."
    )
    lines.append("")
    lines.append("## Scope and inheritance")
    lines.append("")
    lines.append(
        "Strict 24.0b parity: 33 cells = 3 frozen entry streams x 11 trailing "
        "variants (4 T1_ATR + 4 T2_fixed_pip + 3 T3_breakeven). Variants "
        "imported VERBATIM from `stage24_0b.VARIANTS`. No partial-exit "
        "(24.0c) or regime-conditional (24.0d) variants. NG#11 not relaxed. "
        "Phase 22 thresholds unchanged. Frozen entries unchanged. "
        "8-gate harness inherited verbatim."
    )
    lines.append("")
    lines.append(f"Universe: {len(pairs)} pairs (canonical 20). Span = {SPAN_DAYS}d.")
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
            f"x {bv['label']} -> Sharpe {best['sharpe']:+.4f}, "
            f"annual_pnl {best['annual_pnl']:+.1f} pip, "
            f"capture {best['realised_capture_ratio']:+.3f}"
        )
    else:
        lines.append("No cell passed A0 (annual_trades >= 70).")
    lines.append("")
    lines.append("## Routing diagnostic (H1/H2/H3)")
    lines.append("")
    lines.append(
        "Routing hypotheses are FIXED constants set BEFORE this sweep ran. "
        "They are routing diagnostics, NOT formal verdicts (the 8-gate harness "
        "remains the formal verdict mechanism)."
    )
    lines.append("")
    lines.append(
        f"- **H1 (envelope works)**: best Sharpe >= +{H1_THRESHOLD_SHARPE:.3f} "
        "(A1 threshold) -> ADOPT_CANDIDATE / PROMISING."
    )
    lines.append(
        f"- **H2 (partial rescue)**: best Sharpe lift >= +{H2_LIFT_THRESHOLD:.2f} "
        f"vs 24.0b best {PHASE_24_0B_BEST_SHARPE:+.3f} (i.e., new best >= "
        f"{H2_NEW_SHARPE_THRESHOLD:+.3f}). REJECT but interesting."
    )
    lines.append(
        f"- **H3 (no rescue)**: best Sharpe lift < +{H2_LIFT_THRESHOLD:.2f}. "
        "Recommends gamma hard close under current data/execution assumptions."
    )
    lines.append("")
    lines.append(f"**Routing diagnostic this sweep: {h_label}**")
    lines.append("")
    lines.append(h_narrative)
    lines.append("")
    lines.append("## Sweep summary (all 33 cells, sorted by Sharpe desc)")
    lines.append("")
    lines.append(
        "| rank_cell | variant | n | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | "
        "A5 stress | capture | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    def _g(c: dict, name: str) -> str:
        return "OK" if c[f"gate_{name}"] else "x"

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
    lines.append("## Reproducibility note")
    lines.append("")
    lines.append(
        "CI uses smoke-mode regression (3-pair subset) for reproducibility "
        "checks of 24.0b/0c/0d eval_report.md byte-identicality. Full close-"
        "only reproduction is checked locally if feasible. The existing "
        "close-only API (`stage23_0a.load_m1_ba`) remains default and "
        "backward-compatible — no API change. M1 OHLC fields (bid_h/bid_l/"
        "ask_h/ask_l) were already returned by `load_m1_ba` and were "
        "previously unused by 24.0b/0c/0d; no fetch step required for 24.1a."
    )
    lines.append("")
    lines.append("## Phase 24 routing post-24.1a")
    lines.append("")
    lines.append(
        "Per envelope §9, the 24.1a result does NOT auto-route to the next "
        "stage. The user must explicitly decide:"
    )
    lines.append("")
    lines.append(
        "- If routing diagnostic is **H1 / verdict ADOPT_CANDIDATE / PROMISING**: "
        "candidate next PR is Phase 24.1b (C6 stale-quote gate as follow-up if "
        "spread sensitivity is observed)."
    )
    lines.append(
        "- If routing diagnostic is **H2**: REJECT but interesting; user decides "
        "whether to escalate to a focused investigation or close."
    )
    lines.append(
        "- If routing diagnostic is **H3**: recommends gamma hard close under "
        "the current data/execution assumptions, unless user requests new "
        "data/execution audit."
    )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "verdict": verdict,
        "best": best,
        "routing_hypothesis": h_label,
        "routing_narrative": h_narrative,
    }


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
        help="Smoke run: 3 pairs x 1 frozen cell x 3 variants.",
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

    print(f"=== Stage 24.1a both-side touch envelope eval ({len(args.pairs)} pairs) ===")
    print(
        f"Frozen cells: {len(frozen_cells)}; Variants: {len(variants)}; "
        f"Total: {len(frozen_cells) * len(variants)}"
    )
    print(
        f"H1 threshold (Sharpe>=) {H1_THRESHOLD_SHARPE:+.3f}; "
        f"H2 lift (>= +{H2_LIFT_THRESHOLD:.2f}); "
        f"H2 new-Sharpe target {H2_NEW_SHARPE_THRESHOLD:+.3f}"
    )
    cell_results = run_sweep(args.pairs, frozen_cells, variants)
    out_path = args.out_dir / "eval_report.md"
    summary = write_report(out_path, cell_results, args.pairs, frozen_cells)
    print(f"\nReport: {out_path}")
    print(f"Verdict: {summary['verdict']}")
    print(f"Routing diagnostic: {summary['routing_hypothesis']}")
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
