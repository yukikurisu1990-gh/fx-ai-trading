"""Stage 24.0d — Regime-conditional exits on frozen entry streams.

Imports the top-K=3 frozen entry streams from 24.0a (all 23.0d M15
first-touch Donchian, horizon=4) and evaluates 9 regime-conditional
exit-rule variants per cell. Regime tags are computed causally at
signal time and used EXCLUSIVELY to select an exit parameter per
trade. Regime tags MUST NOT drop or filter signals — entry-stream
trade count is invariant across all regime configurations.

Modes (FIXED constants):
  R1 ATR-regime-conditional ATR trailing (uses 24.0b._simulate_atr_*)
     low_vol if atr_at_entry_signal_tf < cross-pair median; else high_vol
     dispatched K_ATR per regime
  R2 Session-regime-conditional partial-exit fraction (uses 24.0c._simulate_p1_*)
     UTC hour bucket: [0,8) asian / [8,16) london / [16,24) ny
     (conventional UTC bucket labels, NOT market-open filters)
     dispatched partial_fraction per session bucket
  R3 Trend-regime-conditional ATR trailing (uses 24.0b._simulate_atr_*)
     binary by mid_c[t-1] - mid_c[t-5] sign (shift(1) causal slope)
     long + up = with_trend; long + down = against_trend; short mirrored
     dispatched K_ATR per (direction, trend) match

Sweep: 3 frozen cells x 9 variants = 27 cells, pooled across 20 pairs.

CRITICAL constraints (mandatory unit-tested):
- kickoff §5 24.0d: regime is exit-parameter selector ONLY, NEVER entry
  filter. Entry-stream trade count is invariant across regime configs.
- NG#10 strict close-only: 24.0d reuses 24.0b/0c simulators directly
  (no re-implementation), inheriting close-only discipline.
- NG#11 causal regime tags: R1 uses 23.0a causal ATR; R2 uses entry
  hour (always known); R3 uses mid_c.shift(1) slope.

R2 session note (mandatory): asian/london/ny labels are CONVENTIONAL UTC
hour bucket labels. They do NOT correspond to actual market-session
boundaries. Daylight saving and pair-specific session semantics are NOT
modeled. The 3-way [0,8)/[8,16)/[16,24) split is purely a regime
partition for exit-parameter selection.

Mandatory clause (verbatim in eval_report.md):
  "All frozen entry streams originate from Phase 23.0d REJECT cells.
  Phase 24.0d tests exit-side capture only; it does not reclassify the
  entry signal itself as ADOPT. Regime conditioning is applied to exit
  logic only — regime tags select an exit parameter per trade and never
  drop or filter entries."

8-gate harness (Phase 22/23 inherited). REJECT reasons inherited.

Diagnostics (NOT gates): realised_capture_ratio (carried from 24.0b/0c),
per_regime_breakdown (NEW; diagnostic-only; must NOT be used to filter trades).

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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage24_0d"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage23_0b = importlib.import_module("stage23_0b_m5_donchian_eval")
stage23_0c = importlib.import_module("stage23_0c_m5_zscore_mr_eval")
stage23_0d = importlib.import_module("stage23_0d_m15_donchian_eval")
stage24_0b = importlib.import_module("stage24_0b_trailing_stop_eval")
stage24_0c = importlib.import_module("stage24_0c_partial_exit_eval")

PAIRS_20 = stage23_0a.PAIRS_20
SPAN_DAYS = 730
SPAN_YEARS = SPAN_DAYS / 365.25
SIGNAL_TIMEFRAME = "M15"
HORIZON_M1_BARS = 60

# R3 trend slope lookback (M15 bars)
R3_SLOPE_LOOKBACK = 5

# Mandatory constant for tests: confirms R2 labels are conventional UTC bucket labels
_R2_LABELS_ARE_CONVENTIONAL_UTC_BUCKETS = True

# R1 variants
R1_VARIANTS: tuple[dict, ...] = (
    {"label": "R1_v1_K_low=1.0_K_high=2.0", "K_low": 1.0, "K_high": 2.0},
    {"label": "R1_v2_K_low=1.5_K_high=2.5", "K_low": 1.5, "K_high": 2.5},
    {"label": "R1_v3_uniform_K=1.5", "K_low": 1.5, "K_high": 1.5},
)

# R2 variants
R2_VARIANTS: tuple[dict, ...] = (
    {"label": "R2_v1_asian=0.25_london=0.50_ny=0.75", "asian": 0.25, "london": 0.50, "ny": 0.75},
    {"label": "R2_v2_asian=0.75_london=0.50_ny=0.25", "asian": 0.75, "london": 0.50, "ny": 0.25},
    {"label": "R2_v3_uniform_frac=0.50", "asian": 0.50, "london": 0.50, "ny": 0.50},
)

# R3 variants
R3_VARIANTS: tuple[dict, ...] = (
    {"label": "R3_v1_with=2.0_against=1.0", "with_trend": 2.0, "against_trend": 1.0},
    {"label": "R3_v2_with=1.0_against=2.0", "with_trend": 1.0, "against_trend": 2.0},
    {"label": "R3_v3_uniform_K=1.5", "with_trend": 1.5, "against_trend": 1.5},
)


def _make_variants() -> list[dict]:
    out: list[dict] = []
    for v in R1_VARIANTS:
        out.append({"mode": "R1_atr_regime", "params": v, "label": v["label"]})
    for v in R2_VARIANTS:
        out.append({"mode": "R2_session_regime", "params": v, "label": v["label"]})
    for v in R3_VARIANTS:
        out.append({"mode": "R3_trend_regime", "params": v, "label": v["label"]})
    return out


VARIANTS = _make_variants()
assert len(VARIANTS) == 9

SMOKE_PAIRS = ["USD_JPY", "EUR_USD", "GBP_JPY"]
SMOKE_VARIANTS = (VARIANTS[1], VARIANTS[4], VARIANTS[7])  # one from each mode

# Inherited gate thresholds
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
# Regime tag computers (NG#11 causal)
# ---------------------------------------------------------------------------


def compute_r1_atr_regime(atr_at_entry_pips: float, atr_median: float) -> str:
    """Binary low/high vs cross-pair median."""
    return "low_vol" if atr_at_entry_pips < atr_median else "high_vol"


def compute_r2_session_regime(entry_ts: pd.Timestamp) -> str:
    """3-bucket UTC hour (NOT market-open filter; conventional bucket labels only)."""
    h = entry_ts.hour
    if 0 <= h < 8:
        return "asian"
    if 8 <= h < 16:
        return "london"
    return "ny"


def compute_r3_trend_regime(
    m15_mid_c: np.ndarray, signal_idx: int, lookback: int = R3_SLOPE_LOOKBACK
) -> str:
    """slope_5 = mid_c[t-1] - mid_c[t-lookback]; uses shift(1) — signal bar excluded."""
    if signal_idx - lookback < 0:
        return "up"
    prior_close = m15_mid_c[signal_idx - 1]
    older_close = m15_mid_c[signal_idx - lookback]
    if not (np.isfinite(prior_close) and np.isfinite(older_close)):
        return "up"
    return "up" if (prior_close - older_close) > 0 else "down"


# ---------------------------------------------------------------------------
# Regime-conditional dispatcher
# ---------------------------------------------------------------------------


def simulate_regime_variant(
    variant: dict,
    direction: str,
    regime_tag: str,
    bid_close: np.ndarray,
    ask_close: np.ndarray,
    atr_pips: float,
    entry_ask: float,
    entry_bid: float,
    pip: float,
) -> tuple[int, float, str, bool]:
    """Returns (exit_idx, pnl_pip, exit_reason, partial_done)."""
    mode = variant["mode"]
    p = variant["params"]
    if mode == "R1_atr_regime":
        k = p["K_low"] if regime_tag == "low_vol" else p["K_high"]
        if direction == "long":
            ei, pnl, reason = stage24_0b._simulate_atr_long(bid_close, k, atr_pips, entry_ask, pip)
        else:
            ei, pnl, reason = stage24_0b._simulate_atr_short(ask_close, k, atr_pips, entry_bid, pip)
        return ei, pnl, reason, False
    if mode == "R2_session_regime":
        fraction = p[regime_tag]  # asian/london/ny lookup
        if direction == "long":
            return stage24_0c._simulate_p1_long(bid_close, fraction, atr_pips, entry_ask, pip)
        return stage24_0c._simulate_p1_short(ask_close, fraction, atr_pips, entry_bid, pip)
    if mode == "R3_trend_regime":
        # Long with up-trend = with_trend; long with down = against_trend.
        # Short with down-trend = with_trend; short with up = against_trend.
        if direction == "long":
            k = p["with_trend"] if regime_tag == "up" else p["against_trend"]
            ei, pnl, reason = stage24_0b._simulate_atr_long(bid_close, k, atr_pips, entry_ask, pip)
        else:
            k = p["with_trend"] if regime_tag == "down" else p["against_trend"]
            ei, pnl, reason = stage24_0b._simulate_atr_short(ask_close, k, atr_pips, entry_bid, pip)
        return ei, pnl, reason, False
    raise ValueError(f"Unknown regime mode: {mode}")


# ---------------------------------------------------------------------------
# Per-cell metrics + regime breakdown
# ---------------------------------------------------------------------------


def compute_per_regime_breakdown(trades: pd.DataFrame, mode: str) -> dict:
    """Per-regime sub-statistics. Diagnostic only — must NOT be used to filter trades."""
    if "regime_tag" not in trades.columns or len(trades) == 0:
        return {}
    out: dict[str, dict] = {}
    for regime_label, sub in trades.groupby("regime_tag"):
        if len(sub) < 2:
            out[str(regime_label)] = {
                "n_trades": int(len(sub)),
                "sharpe": float("nan"),
                "mean_pnl": float(sub["pnl_pip"].mean()) if len(sub) else float("nan"),
                "hit_rate": float((sub["pnl_pip"] > 0).mean()) if len(sub) else float("nan"),
            }
            continue
        out[str(regime_label)] = {
            "n_trades": int(len(sub)),
            "sharpe": _per_trade_sharpe(sub["pnl_pip"]),
            "mean_pnl": float(sub["pnl_pip"].mean()),
            "hit_rate": float((sub["pnl_pip"] > 0).mean()),
        }
    return out


def evaluate_cell(trades: pd.DataFrame, mode: str) -> dict:
    base = stage24_0b.evaluate_cell(trades)
    base["per_regime_breakdown"] = compute_per_regime_breakdown(trades, mode)
    return base


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
        m15_idx = m15.index
        m15_mid_c = ((m15["bid_c"] + m15["ask_c"]) / 2.0).to_numpy()
        m15_pos = pd.Series(np.arange(len(m15_idx), dtype=np.int64), index=m15_idx)
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
            "m15_mid_c": m15_mid_c,
            "m15_pos": m15_pos,
            "signals_by_n": signals_by_n,
            "labels_h4": labels_h4,
            "pip": stage23_0a.pip_size_for(pair),
        }
        print(f"  {pair}: m1={n_m1} m15={len(m15)} ({time.time() - t0:5.1f}s)")

    # Pass 1: cross-pair ATR median for R1
    print("--- pass 1: collecting cross-pair ATR median ---")
    atr_values: list[float] = []
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
            if len(joined) > 0:
                atr_values.extend(joined["atr_at_entry_signal_tf"].dropna().astype(float).tolist())
    atr_median = float(np.median(atr_values)) if atr_values else float("nan")
    print(f"  cross-pair ATR median: {atr_median:.3f} pip ({len(atr_values)} signals)")

    # Pass 2: per cell × variant simulation
    print(f"--- pass 2: evaluating {len(frozen_cells)} cells x {len(variants)} variants ---")
    cell_results: list[dict] = []
    for cell_idx, cell in enumerate(frozen_cells):
        n_value = cell["cell_params"]["N"]
        for v_idx, variant in enumerate(variants):
            mode = variant["mode"]
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
                m15_mid_c = pdata["m15_mid_c"]
                m15_pos = pdata["m15_pos"]
                pnls: list[float] = []
                reasons: list[str] = []
                exit_idxs: list[int] = []
                partials: list[bool] = []
                regimes: list[str] = []
                for _, row in joined.iterrows():
                    entry_ts = pd.Timestamp(row["entry_ts"])
                    direction = row["direction"]
                    atr_pips = float(row["atr_at_entry_signal_tf"])
                    entry_ask = float(row["entry_ask"])
                    entry_bid = float(row["entry_bid"])

                    # Regime tag
                    if mode == "R1_atr_regime":
                        regime_tag = compute_r1_atr_regime(atr_pips, atr_median)
                    elif mode == "R2_session_regime":
                        regime_tag = compute_r2_session_regime(entry_ts)
                    elif mode == "R3_trend_regime":
                        if entry_ts in m15_pos.index:
                            sig_idx_in_m15 = int(m15_pos.loc[entry_ts])
                            regime_tag = compute_r3_trend_regime(
                                m15_mid_c, sig_idx_in_m15, R3_SLOPE_LOOKBACK
                            )
                        else:
                            regime_tag = "up"
                    else:
                        raise ValueError(f"Unknown mode: {mode}")

                    # Locate entry M1 and path
                    target_m1_ts = entry_ts + pd.Timedelta(minutes=1)
                    if target_m1_ts not in m1_pos.index:
                        pnls.append(np.nan)
                        reasons.append("no_entry")
                        exit_idxs.append(-1)
                        partials.append(False)
                        regimes.append(regime_tag)
                        continue
                    entry_m1 = int(m1_pos.loc[target_m1_ts])
                    path_end = entry_m1 + HORIZON_M1_BARS
                    if path_end > n_m1:
                        pnls.append(np.nan)
                        reasons.append("path_too_short")
                        exit_idxs.append(-1)
                        partials.append(False)
                        regimes.append(regime_tag)
                        continue
                    bid_path = bid_c[entry_m1:path_end]
                    ask_path = ask_c[entry_m1:path_end]

                    exit_idx, pnl, reason, partial_done = simulate_regime_variant(
                        variant,
                        direction,
                        regime_tag,
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
                    regimes.append(regime_tag)

                joined_with_pnl = joined.assign(
                    pnl_pip=pnls,
                    exit_reason=reasons,
                    exit_idx=exit_idxs,
                    partial_done=partials,
                    regime_tag=regimes,
                )
                joined_with_pnl = joined_with_pnl.dropna(subset=["pnl_pip"])
                pooled_parts.append(joined_with_pnl)

            trades = pd.concat(pooled_parts, ignore_index=True) if pooled_parts else pd.DataFrame()
            if len(trades) > 0 and (trades["signal_timeframe"] != SIGNAL_TIMEFRAME).any():
                raise RuntimeError(
                    f"NG#6 violation: cell {cell_idx} variant {variant['label']} "
                    f"emitted non-{SIGNAL_TIMEFRAME} rows"
                )
            metrics = evaluate_cell(trades, mode)
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
                f"{variant['label']:<48} "
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
    lines.append("# Stage 24.0d — Regime-Conditional Exits on Frozen Entry Streams")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase24_0d_regime_conditional.md`")
    lines.append("")
    lines.append("## Mandatory clause")
    lines.append("")
    lines.append(
        "**All frozen entry streams originate from Phase 23.0d REJECT cells. "
        "Phase 24.0d tests exit-side capture only; it does not reclassify the "
        "entry signal itself as ADOPT. Regime conditioning is applied to exit "
        "logic only — regime tags select an exit parameter (trailing K or "
        "partial fraction) per trade and never drop or filter entries.** "
        "Production-readiness still requires `24.0d-v2` frozen-cell strict OOS."
    )
    lines.append("")
    lines.append("## Regime is exit-parameter selector ONLY (not entry filter)")
    lines.append("")
    lines.append(
        "Per kickoff §5 24.0d, regime tags select WHICH trailing distance / "
        "partial fraction to use per trade. Regime tags MUST NOT be used as "
        "entry filters. Phase 22/23 explicitly rejected time-of-day, session, "
        "and regime entry filtering; 24.0d MUST NOT revive that route via the "
        "back door of 'regime-conditional exits'. Mandatory unit test "
        "`test_regime_is_exit_parameter_only_not_entry_filter` verifies entry-"
        "stream count is invariant across all regime configurations."
    )
    lines.append("")
    lines.append(
        "**R2 session note**: `asian` / `london` / `ny` are CONVENTIONAL UTC "
        "hour bucket labels for the 3-way `[0,8) / [8,16) / [16,24)` partition. "
        "They do NOT correspond to actual market-session boundaries (which "
        "vary with daylight saving and pair-specific session semantics). "
        "24.0d does not enforce any market-open semantic — the labels are "
        "purely cosmetic for hour-of-day grouping."
    )
    lines.append("")
    lines.append("## NG#10 strict-rule disclosure (carried from 24.0b/0c)")
    lines.append("")
    lines.append(
        "All exit triggers (TP, SL, partial trigger, MFE running max/min, "
        "trailing) are evaluated at M1 bar **close only**. 24.0d reuses "
        "`stage24_0b._simulate_atr_long/short` (R1, R3) and "
        "`stage24_0c._simulate_p1_long/short` (R2) directly — no "
        "re-implementation. The close-only discipline is inherited by reuse."
    )
    lines.append("")
    lines.append("## NG#11 causal regime-tag disclosure")
    lines.append("")
    lines.append("All regime tags are computed using data available **at signal time** only:")
    lines.append(
        "- **R1 ATR regime**: uses `atr_at_entry_signal_tf` from 23.0a labels "
        "(already causal — computed via `mid_c.shift(1).rolling(N)` per 23.0a §2.1)."
    )
    lines.append(
        "- **R2 session regime**: `entry_ts.hour_utc` is always known at signal "
        "generation (trivially causal)."
    )
    lines.append(
        "- **R3 trend regime**: `slope_5 = mid_c[t-1] - mid_c[t-5]` uses "
        "`mid_c.shift(1)` only — the signal bar's own close is NEVER used."
    )
    lines.append("")
    lines.append("## Diagnostics disclosure")
    lines.append("")
    lines.append(
        "`realised_capture_ratio` (carried from 24.0b/0c) and "
        "`per_regime_breakdown` (NEW for 24.0d) are **diagnostic-only**. "
        "`per_regime_breakdown` reports per-bucket sub-statistics (n_trades, "
        "sharpe, mean_pnl, hit_rate) within each cell and **must NOT be used "
        "to ex-post select a 'best regime' and drop the others** — that would "
        "be a regime-as-entry-filter route via the back door. Use for "
        "interpretation only."
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
    lines.append("## Per-mode effectiveness + uniform-control comparison")
    lines.append("")
    lines.append(
        "If conditional regime variants outperform their uniform-control "
        "siblings (R1_v3, R2_v3, R3_v3), the regime conditioning is capturing "
        "exit-side information. If conditional == uniform, the regime tag "
        "carries no useful exit-parameter signal."
    )
    lines.append("")
    lines.append(
        "| mode | best variant | best Sharpe | best ann_pnl | uniform Sharpe | uniform ann_pnl |"
    )
    lines.append("|---|---|---|---|---|---|")
    for mode, uniform_label in (
        ("R1_atr_regime", "R1_v3_uniform_K=1.5"),
        ("R2_session_regime", "R2_v3_uniform_frac=0.50"),
        ("R3_trend_regime", "R3_v3_uniform_K=1.5"),
    ):
        sub = [c for c in cell_results if c["variant"]["mode"] == mode]
        if not sub:
            continue
        best_in_mode = max(sub, key=lambda c: c["sharpe"] if np.isfinite(c["sharpe"]) else -1e9)
        uniform = next((c for c in sub if c["variant"]["label"] == uniform_label), None)
        u_sharpe = (
            f"{uniform['sharpe']:+.4f}" if uniform and np.isfinite(uniform["sharpe"]) else "n/a"
        )
        u_pnl = f"{uniform['annual_pnl']:+.1f}" if uniform else "n/a"
        lines.append(
            f"| {mode} | {best_in_mode['variant']['label']} | "
            f"{best_in_mode['sharpe']:+.4f} | {best_in_mode['annual_pnl']:+.1f} | "
            f"{u_sharpe} | {u_pnl} |"
        )
    lines.append("")
    lines.append("## Sweep summary (all 27 cells, sorted by Sharpe descending)")
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

    if best is not None:
        lines.append("## Best cell — per-regime breakdown (diagnostic only)")
        lines.append("")
        per_regime = best.get("per_regime_breakdown") or {}
        if per_regime:
            lines.append("| regime bucket | n_trades | Sharpe | mean_pnl | hit_rate |")
            lines.append("|---|---|---|---|---|")
            for label, stats in per_regime.items():
                lines.append(
                    f"| {label} | {stats['n_trades']} | "
                    f"{stats['sharpe']:+.4f} | {stats['mean_pnl']:+.4f} | "
                    f"{stats['hit_rate']:.4f} |"
                )
            lines.append("")
            lines.append(
                "(`per_regime_breakdown` is diagnostic-only; not used for any "
                "ADOPT decision or trade filtering.)"
            )
        lines.append("")

    lines.append("## Phase 24 routing post-24.0d")
    lines.append("")
    if verdict in ("ADOPT_CANDIDATE", "PROMISING_BUT_NEEDS_OOS"):
        lines.append(
            f"Best cell verdict is **{verdict}**. 24.0e (exit meta-labeling) "
            "trigger condition met per kickoff §5 (any of 24.0b/c/d returns "
            "ADOPT/PROMISING). 24.0d-v2 (frozen-cell strict OOS) becomes a "
            "candidate downstream PR — production discussion only after "
            "24.0d-v2 confirms."
        )
    else:
        lines.append(
            "Best cell verdict is **REJECT**. Combined with 24.0b and 24.0c "
            "REJECTs, **24.0e (exit meta-labeling) is NOT triggered** per "
            "kickoff §5 (no 24.0b/c/d cell ADOPT/PROMISING). Phase 24 closes "
            "with 24.0f final synthesis (path A analogous to Phase 23): "
            "exit-side improvements under NG#10 strict close-only and "
            "non-forward-looking regime conditioning are insufficient to "
            "convert the 24.0a-validated path-EV into realised PnL clearing "
            "the 8-gate harness."
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

    print(f"=== Stage 24.0d regime-conditional eval ({len(args.pairs)} pairs) ===")
    print(
        f"Frozen cells: {len(frozen_cells)}; Variants: {len(variants)}; "
        f"Total: {len(frozen_cells) * len(variants)}"
    )
    print(f"R3_SLOPE_LOOKBACK={R3_SLOPE_LOOKBACK} M15 bars (shift(1) causal)")
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
