"""Stage 23.0d — M15 Donchian first-touch breakout + M1 execution eval.

Rule-based Donchian breakout on the M15 signal timeframe with **first-touch
trigger semantics** (rising-edge into the band with same-direction re-entry
lock). Continuous-trigger Donchian is intentionally NOT used; per the
23.0b lesson and 23.0c follow-up, Phase 23 commits to first-touch at the
rule-based stage.

Sweep:
- N (Donchian window, M15 bars): {10, 20, 50} = 2.5h / 5h / 12.5h
- horizon_bars: {1, 2, 4} = 15 / 30 / 60 minutes (kickoff §6.2)
- exit_rule: {tb, time}
= 18 cells.

Gates (Phase 22 inherited, exact thresholds — same as 23.0b/0c):
- A0 annual_trades >= 70  (overtrading WARN > 1000, NOT blocking)
- A1 per-trade Sharpe (ddof=0, no √N) >= +0.082
- A2 annual_pnl_pip >= +180
- A3 max_dd_pip <= 200
- A4 5-fold split, k=0 dropped, eval k=1..4, count(>0) >= 3
- A5 annual_pnl after subtracting 0.5 pip per round trip > 0

Diagnostics (NOT gates):
- hit_rate, payoff_asymmetry, per-pair / per-session contribution
- band_distance_at_entry distribution (pip distance above upper / below lower)
- breakout_holding_diagnostic (best-cell only, forward-path M1 bars where
  the price stays beyond the band before retreating). Forward-path
  diagnostic-only — must NOT be used in features or ADOPT.
- S0 random-entry sanity, S1 strict 80/20 OOS — diagnostic-only

Verdict (3-class): ADOPT_CANDIDATE / PROMISING_BUT_NEEDS_OOS / REJECT
REJECT reason classification: under_firing / still_overtrading /
pnl_edge_insufficient / robustness_failure.

Phase 23 routing on 23.0d outcome (see design §7.2):
- ADOPT_CANDIDATE / PROMISING → 23.0e meta-labeling triggers
- REJECT with NO 23.0b/c/d cell positive → 23.0c-rev1 (signal-quality
  control study, NOT 23.0e) is the next candidate

Production-readiness: even ADOPT_CANDIDATE requires a separate 23.0d-v2
PR with frozen-cell strict OOS validation.

This script touches NO production code, NO DB schema, NO src/ files.
20-pair canonical universe; no pair / time filter.
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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage23_0d"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage23_0b = importlib.import_module("stage23_0b_m5_donchian_eval")
stage23_0c = importlib.import_module("stage23_0c_m5_zscore_mr_eval")

PAIRS_20 = stage23_0a.PAIRS_20
SIGNAL_TIMEFRAME = "M15"

TRIGGER_MODE = "first_touch"  # 23.0d default (Phase 23 commitment)

N_VALUES: tuple[int, ...] = (10, 20, 50)
HORIZONS: tuple[int, ...] = (1, 2, 4)  # M15 horizons per kickoff §6.2
EXIT_RULES: tuple[str, ...] = ("tb", "time")
EXIT_COL_MAP = {"tb": "tb_pnl", "time": "time_exit_pnl"}

SPAN_DAYS = 730
SPAN_YEARS = SPAN_DAYS / 365.25

# Inherited gate thresholds (same as 23.0b/0c)
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
_random_entry_sharpe = stage23_0b._random_entry_sharpe
gate_matrix = stage23_0b.gate_matrix
assign_verdict = stage23_0b.assign_verdict
session_label = stage23_0b.session_label
per_pair_breakdown = stage23_0b.per_pair_breakdown
per_session_breakdown = stage23_0b.per_session_breakdown
classify_reject_reason = stage23_0c.classify_reject_reason

SMOKE_PAIRS = ["USD_JPY", "EUR_USD", "GBP_JPY"]
SMOKE_CELLS: tuple[tuple[int, int, str], ...] = (
    (20, 1, "tb"),
    (20, 4, "time"),
)


# ---------------------------------------------------------------------------
# Signal generation — first-touch Donchian on M15 mid OHLC
# ---------------------------------------------------------------------------


def compute_donchian_bands(m15_df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Return a copy of m15_df with mid OHLC and causal Donchian bands."""
    out = m15_df.copy()
    out["mid_h"] = (out["bid_h"] + out["ask_h"]) / 2.0
    out["mid_l"] = (out["bid_l"] + out["ask_l"]) / 2.0
    out["mid_c"] = (out["bid_c"] + out["ask_c"]) / 2.0
    out[f"upper_{n}"] = out["mid_h"].shift(1).rolling(n).max()
    out[f"lower_{n}"] = out["mid_l"].shift(1).rolling(n).min()
    return out


def extract_signals_first_touch_donchian(m15_df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Emit first-touch Donchian breakout signals.

    Long: mid_c[t] > upper_N[t] AND mid_c[t-1] <= upper_N[t-1]  (rising-edge above)
    Short: mid_c[t] < lower_N[t] AND mid_c[t-1] >= lower_N[t-1]  (rising-edge below)

    The prior bar's relationship is checked against the prior band, not
    today's band — necessary because the band moves bar-by-bar.
    """
    df = compute_donchian_bands(m15_df, n)
    upper = df[f"upper_{n}"]
    lower = df[f"lower_{n}"]
    mid_c = df["mid_c"]
    upper_prev = upper.shift(1)
    lower_prev = lower.shift(1)
    mid_c_prev = mid_c.shift(1)

    long_first = (
        (mid_c > upper)
        & (mid_c_prev <= upper_prev)
        & upper.notna()
        & upper_prev.notna()
        & mid_c_prev.notna()
    )
    short_first = (
        (mid_c < lower)
        & (mid_c_prev >= lower_prev)
        & lower.notna()
        & lower_prev.notna()
        & mid_c_prev.notna()
    )

    sig_long_idx = df.index[long_first]
    sig_short_idx = df.index[short_first]

    out = pd.DataFrame(
        {
            "entry_ts": list(sig_long_idx) + list(sig_short_idx),
            "direction": ["long"] * len(sig_long_idx) + ["short"] * len(sig_short_idx),
            "mid_c_at_entry": list(mid_c.loc[sig_long_idx].to_numpy())
            + list(mid_c.loc[sig_short_idx].to_numpy()),
            "band_at_entry": list(upper.loc[sig_long_idx].to_numpy())
            + list(lower.loc[sig_short_idx].to_numpy()),
        }
    )
    return out


def load_pair_signals_all_n(
    pair: str, days: int = SPAN_DAYS
) -> tuple[dict[int, pd.DataFrame], pd.DataFrame]:
    """Build M15 OHLC + first-touch Donchian signals for all N values."""
    m1 = stage23_0a.load_m1_ba(pair, days=days)
    m15 = stage23_0a.aggregate_m1_to_tf(m1, SIGNAL_TIMEFRAME)
    out: dict[int, pd.DataFrame] = {}
    for n in N_VALUES:
        out[n] = extract_signals_first_touch_donchian(m15, n)
    return out, m15


def load_pair_labels(pair: str, signal_tf: str = SIGNAL_TIMEFRAME) -> pd.DataFrame:
    """Load 23.0a M15 labels for the pair (with NG#6 runtime assertion)."""
    parquet = LABELS_ROOT / f"labels_{signal_tf}" / f"labels_{signal_tf}_{pair}.parquet"
    if not parquet.exists():
        raise FileNotFoundError(parquet)
    df = pd.read_parquet(parquet)
    df = df[df["valid_label"]].copy()
    if (df["signal_timeframe"] != signal_tf).any():
        raise RuntimeError(
            f"NG#6 violation: labels for {pair} contain non-{signal_tf} rows; "
            f"Phase 22 cell reuse prevention requires signal_timeframe == {signal_tf!r}"
        )
    return df


# ---------------------------------------------------------------------------
# MR-cell-style evaluation with band_distance diagnostic
# ---------------------------------------------------------------------------


def evaluate_donchian_cell(
    trades_df: pd.DataFrame,
    labels_pool_for_s0: pd.DataFrame,
    exit_col: str,
) -> dict:
    metrics = stage23_0b.evaluate_cell(trades_df, labels_pool_for_s0, exit_col)
    if len(trades_df) > 0 and "band_distance_pip" in trades_df.columns:
        d = trades_df["band_distance_pip"].abs()
        d = d[np.isfinite(d)]
        if len(d) > 0:
            metrics["band_dist_p10"] = float(d.quantile(0.10))
            metrics["band_dist_p25"] = float(d.quantile(0.25))
            metrics["band_dist_p50"] = float(d.quantile(0.50))
            metrics["band_dist_p75"] = float(d.quantile(0.75))
            metrics["band_dist_p90"] = float(d.quantile(0.90))
        else:
            for k in (
                "band_dist_p10",
                "band_dist_p25",
                "band_dist_p50",
                "band_dist_p75",
                "band_dist_p90",
            ):
                metrics[k] = float("nan")
    else:
        for k in (
            "band_dist_p10",
            "band_dist_p25",
            "band_dist_p50",
            "band_dist_p75",
            "band_dist_p90",
        ):
            metrics[k] = float("nan")
    return metrics


# ---------------------------------------------------------------------------
# breakout_holding_diagnostic — best-cell only, M1-path reload
# ---------------------------------------------------------------------------


def compute_breakout_holding_for_best_cell(trades_df: pd.DataFrame) -> dict:
    """Forward-path M1 bars during which price stays beyond the entry band.

    For long trades (long_break, broke above upper): count M1 bars in the
    forward path where mid_c > upper_at_entry; for shorts: mid_c < lower_at_entry.
    Diagnostic only — must not feed back into ADOPT or features.
    """
    if len(trades_df) == 0:
        return {
            "n_trades": 0,
            "p25_m1": float("nan"),
            "p50_m1": float("nan"),
            "p75_m1": float("nan"),
            "frac_held_full_horizon": float("nan"),
        }
    holding_bars: list[float] = []
    n_full_holds = 0
    n_evaluated = 0
    pairs_in_play = sorted(trades_df["pair"].unique())
    for pair in pairs_in_play:
        sub = trades_df[trades_df["pair"] == pair]
        if len(sub) == 0:
            continue
        m1 = stage23_0a.load_m1_ba(pair, days=SPAN_DAYS)
        m1_idx = m1.index
        n_m1 = len(m1_idx)
        bid_c = m1["bid_c"].to_numpy()
        ask_c = m1["ask_c"].to_numpy()
        mid_c_m1 = (bid_c + ask_c) / 2.0
        m1_pos_lookup = pd.Series(np.arange(n_m1, dtype=np.int64), index=m1_idx)
        for _, row in sub.iterrows():
            entry_ts = pd.Timestamp(row["entry_ts"])
            direction = row["direction"]
            band_at_entry = row.get("band_at_entry", np.nan)
            horizon_m1_bars = int(row["horizon_bars"]) * 15  # M15 -> M1
            if not np.isfinite(band_at_entry):
                continue
            target_entry_m1_ts = entry_ts + pd.Timedelta(minutes=1)
            if target_entry_m1_ts not in m1_pos_lookup.index:
                continue
            entry_m1_pos = int(m1_pos_lookup.loc[target_entry_m1_ts])
            path_end = entry_m1_pos + horizon_m1_bars
            if path_end > n_m1:
                continue
            path = mid_c_m1[entry_m1_pos:path_end]
            holding_mask = path > band_at_entry if direction == "long" else path < band_at_entry
            held_count = int(holding_mask.sum())
            holding_bars.append(float(held_count))
            n_evaluated += 1
            if held_count == horizon_m1_bars:
                n_full_holds += 1
    holding_arr = np.asarray(holding_bars, dtype=np.float64)
    finite = holding_arr[np.isfinite(holding_arr)]
    return {
        "n_trades": int(n_evaluated),
        "p25_m1": float(np.percentile(finite, 25)) if len(finite) > 0 else float("nan"),
        "p50_m1": float(np.percentile(finite, 50)) if len(finite) > 0 else float("nan"),
        "p75_m1": float(np.percentile(finite, 75)) if len(finite) > 0 else float("nan"),
        "frac_held_full_horizon": (
            float(n_full_holds / n_evaluated) if n_evaluated > 0 else float("nan")
        ),
    }


# ---------------------------------------------------------------------------
# Sweep runner
# ---------------------------------------------------------------------------


def run_sweep(
    pairs: list[str], cells: list[tuple[int, int, str]] | None = None
) -> tuple[list[dict], dict[tuple[int, int, str], pd.DataFrame]]:
    if cells is None:
        cells = [(n, h, e) for n in N_VALUES for h in HORIZONS for e in EXIT_RULES]

    per_pair_signals: dict[str, dict[int, pd.DataFrame]] = {}
    per_pair_labels: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        t0 = time.time()
        signals, _ = load_pair_signals_all_n(pair)
        labels = load_pair_labels(pair)
        per_pair_signals[pair] = signals
        per_pair_labels[pair] = labels
        sample_counts = " / ".join(f"N={n}:{len(signals[n])}" for n in N_VALUES)
        print(f"  signals+labels {pair}: {sample_counts}  ({time.time() - t0:5.1f}s)")

    cell_results: list[dict] = []
    cell_trades: dict[tuple[int, int, str], pd.DataFrame] = {}

    for n, h, exit_rule in cells:
        exit_col = EXIT_COL_MAP[exit_rule]
        pooled_trades_parts: list[pd.DataFrame] = []
        labels_pool_parts: list[pd.DataFrame] = []
        for pair in pairs:
            sig = per_pair_signals[pair][n].copy()
            sig["pair"] = pair
            pip = stage23_0a.pip_size_for(pair)
            # band_distance in pips (signed: positive for long means above band, etc.)
            if len(sig) > 0:
                sig["band_distance_pip"] = (sig["mid_c_at_entry"] - sig["band_at_entry"]) / pip
                sig.loc[sig["direction"] == "short", "band_distance_pip"] *= -1.0
            else:
                sig["band_distance_pip"] = pd.Series(dtype=np.float64)
            labels_pair_h = per_pair_labels[pair]
            labels_pair_h = labels_pair_h[labels_pair_h["horizon_bars"] == h]
            joined = pd.merge(
                sig,
                labels_pair_h[
                    [
                        "entry_ts",
                        "pair",
                        "direction",
                        "tb_pnl",
                        "time_exit_pnl",
                        "signal_timeframe",
                        "horizon_bars",
                    ]
                ],
                on=["entry_ts", "pair", "direction"],
                how="inner",
            )
            joined["pnl_pip"] = joined[exit_col].astype(np.float64)
            joined = joined.dropna(subset=["pnl_pip"])
            pooled_trades_parts.append(joined)
            labels_pool_parts.append(labels_pair_h)

        if pooled_trades_parts:
            trades = pd.concat(pooled_trades_parts, ignore_index=True)
        else:
            trades = pd.DataFrame(
                columns=[
                    "entry_ts",
                    "pair",
                    "direction",
                    "tb_pnl",
                    "time_exit_pnl",
                    "pnl_pip",
                    "band_distance_pip",
                    "band_at_entry",
                ]
            )
        labels_pool = (
            pd.concat(labels_pool_parts, ignore_index=True) if labels_pool_parts else pd.DataFrame()
        )

        if len(trades) > 0 and (trades["signal_timeframe"] != SIGNAL_TIMEFRAME).any():
            raise RuntimeError(
                f"NG#6 violation: cell (N={n}, h={h}, exit={exit_rule}) emitted a row "
                f"with signal_timeframe != {SIGNAL_TIMEFRAME}"
            )

        metrics = evaluate_donchian_cell(trades, labels_pool, exit_col)
        gates = gate_matrix(metrics)
        reject_reason = classify_reject_reason(metrics, gates)
        cell_results.append(
            {
                "N": n,
                "horizon_bars": h,
                "exit_rule": exit_rule,
                "reject_reason": reject_reason,
                **metrics,
                **{f"gate_{k}": v for k, v in gates.items()},
            }
        )
        cell_trades[(n, h, exit_rule)] = trades
        gates_bits = "".join("1" if gates[g] else "0" for g in ("A0", "A1", "A2", "A3", "A4", "A5"))
        print(
            f"  cell N={n:>2} h={h} exit={exit_rule:<4} "
            f"n={metrics['n_trades']:>5} ann_tr={metrics['annual_trades']:7.1f} "
            f"sharpe={metrics['sharpe']:+.4f} ann_pnl={metrics['annual_pnl']:+8.1f} "
            f"dd={metrics['max_dd']:7.1f} A4={metrics['a4_n_positive']}/4 "
            f"gates={gates_bits} reason={reject_reason or '-'}"
        )

    return cell_results, cell_trades


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
    cell_trades: dict[tuple[int, int, str], pd.DataFrame],
    pairs: list[str],
) -> dict:
    best = select_best_cell(cell_results)
    s1 = None
    holding_stats: dict | None = None
    if best is not None:
        best_key = (best["N"], best["horizon_bars"], best["exit_rule"])
        s1 = _strict_oos_split(cell_trades[best_key])
        holding_stats = compute_breakout_holding_for_best_cell(cell_trades[best_key])
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
    n_overtrading = sum(1 for c in cell_results if c["overtrading_warning"])

    lines: list[str] = []
    lines.append("# Stage 23.0d — M15 Donchian First-Touch Breakout + M1 Execution Eval")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase23_0d_m15_donchian_baseline.md`")
    lines.append("")
    lines.append(
        f"Universe: {len(pairs)} pairs, signal TF = `{SIGNAL_TIMEFRAME}`, span = {SPAN_DAYS}d, "
        f"trigger mode = `{TRIGGER_MODE}`"
    )
    lines.append(
        f"Sweep: N {N_VALUES} × horizon {HORIZONS} × exit {EXIT_RULES} = {len(cell_results)} cells"
    )
    lines.append("")
    lines.append("## Headline verdict")
    lines.append("")
    lines.append(f"**{verdict}**")
    lines.append("")
    lines.append(
        f"Per-cell verdict counts: {n_reject} REJECT / "
        f"{n_promising} PROMISING_BUT_NEEDS_OOS / "
        f"{n_adopt_candidate} ADOPT_CANDIDATE — out of {len(cell_results)} cells."
    )
    lines.append("")
    if reject_reason_counts:
        lines.append("REJECT reason breakdown:")
        for reason in (
            "under_firing",
            "still_overtrading",
            "pnl_edge_insufficient",
            "robustness_failure",
        ):
            count = reject_reason_counts.get(reason, 0)
            lines.append(f"- {reason}: {count} cell(s)")
        lines.append("")
    if best is not None:
        lines.append(
            f"Best cell: `N={best['N']}, horizon={best['horizon_bars']}, "
            f"exit={best['exit_rule']}` "
            f"(Sharpe {best['sharpe']:+.4f}, annual_pnl {best['annual_pnl']:+.1f} pip, "
            f"n_trades {best['n_trades']})"
        )
    else:
        lines.append("No cell passed A0 (annual_trades >= 70).")
    lines.append("")
    lines.append("## Interpretation note carried from 23.0c")
    lines.append("")
    lines.append(
        "**The 23.0c REJECT was not a complete dismissal of M5 z-score MR.** All 36 "
        "cells were classified `still_overtrading`, meaning trade volume was reduced "
        "2-5× by first-touch but remained above the 1000-trade warning threshold; "
        "per-trade EV was dominated by spread cost. This is consistent with "
        "**insufficient signal firing precision**, not with 'M5 z-score MR has no edge'."
    )
    lines.append("")
    lines.append(
        "23.0d's design therefore considers first-touch a *partial* fix and documents "
        "follow-up signal-quality controls (see Phase 23 routing below)."
    )
    lines.append("")
    lines.append("## Phase 23 routing on 23.0d outcome")
    lines.append("")
    lines.append("```")
    lines.append("23.0d returns:")
    lines.append("├── ADOPT_CANDIDATE / PROMISING_BUT_NEEDS_OOS")
    lines.append("│     → 23.0e (meta-labeling on best 23.0b/c/d cell) triggers")
    lines.append("│     → 23.0d-v2 (frozen-cell strict OOS) mandatory before production")
    lines.append("│")
    lines.append("└── REJECT (any reason)")
    lines.append("      ├── If any 23.0b/c/d cell has positive realistic-exit Sharpe")
    lines.append("      │     → 23.0e meta-labeling on that cell triggers")
    lines.append("      │")
    lines.append("      └── If NO 23.0b/c/d cell has positive realistic-exit Sharpe")
    lines.append("            → 23.0e DOES NOT trigger")
    lines.append("            → 23.0c-rev1 (signal-quality control study) is the next candidate")
    lines.append("              with fixed (non-search) controls layered on 23.0c first-touch:")
    lines.append("              • neutral reset: re-entry only after z returns to [-0.5, +0.5]")
    lines.append("              • cooldown: 3 M5 bars block after any fire")
    lines.append("              • reversal confirmation: z direction + mid_c direction agree")
    lines.append("              • fixed cost gate: cost_ratio_at_entry <= 0.6")
    lines.append("            → If 23.0c-rev1 also fails, Phase 23 closes with the")
    lines.append("              negative-but-bounded conclusion")
    lines.append("```")
    lines.append("")
    lines.append("**Phase 23 closure must distinguish two failure modes** (per design §7.2):")
    lines.append(
        "1. *Cost regime alone (M5/M15 vs M1) was insufficient for naive / weakly-controlled "
        "signal firing* — supported by 23.0b/0c (and 23.0d, if it REJECTs)."
    )
    lines.append(
        "2. *M5/M15 has no recoverable edge even with stronger signal-quality controls* — "
        "would require 23.0c-rev1 also failing across all four candidate filters."
    )
    lines.append("These are different conclusions; closure must NOT short-circuit (1) into (2).")
    lines.append("")
    lines.append("## Production-readiness")
    lines.append("")
    lines.append(
        "Even an `ADOPT_CANDIDATE` verdict is **not** production-ready. The S1 strict OOS "
        "is computed *after* the in-sample sweep selected the best cell from "
        f"{len(cell_results)} cells × {len(pairs)} pairs (multiple-testing surface). "
        "A separate `23.0d-v2` PR with frozen-cell strict OOS validation on "
        "chronologically out-of-sample data and no parameter re-search is required "
        "before any production migration."
    )
    lines.append("")
    lines.append("## Trigger semantics")
    lines.append("")
    lines.append(
        f"- Trigger mode: `{TRIGGER_MODE}` (rising-edge crossing of the band, with "
        "shift(1) on both `mid_c` and the band itself for causality)."
    )
    lines.append(
        "- Same-direction re-entry locked while price stays beyond the band; long-side "
        "and short-side locks independent."
    )
    lines.append(
        "- **Continuous trigger is not the Phase 23 default because 23.0b showed "
        "continuous-trigger overtrading.**"
    )
    lines.append("")
    lines.append("## Gate thresholds (Phase 22 inherited, identical to 23.0b/0c)")
    lines.append("")
    lines.append(
        f"- A0: annual_trades >= {A0_MIN_ANNUAL_TRADES} "
        f"(overtrading warning if > {A0_OVERTRADING_WARN}, NOT blocking)"
    )
    lines.append(f"- A1: per-trade Sharpe (ddof=0, no √N) >= +{A1_MIN_SHARPE}")
    lines.append(f"- A2: annual_pnl_pip >= +{A2_MIN_ANNUAL_PNL}")
    lines.append(f"- A3: max_dd_pip <= {A3_MAX_MAXDD}")
    lines.append(
        f"- A4: 5-fold chronological, drop k=0, eval k=1..4, "
        f"count(Sharpe > 0) >= {A4_MIN_POSITIVE_FOLDS}/4"
    )
    lines.append(
        f"- A5: annual_pnl after subtracting {A5_SPREAD_STRESS_PIP} pip per round trip > 0"
    )
    lines.append("")
    lines.append("## Sweep summary (all cells, sorted by Sharpe)")
    lines.append("")
    lines.append(
        "| N | h | exit | n_trades | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | "
        "A5 stress | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    def _gate_glyph(cell: dict, name: str) -> str:
        return "✓" if cell[f"gate_{name}"] else "✗"

    for c in sorted(
        cell_results,
        key=lambda x: x["sharpe"] if np.isfinite(x["sharpe"]) else -1e9,
        reverse=True,
    ):
        lines.append(
            f"| {c['N']} | {c['horizon_bars']} | {c['exit_rule']} | "
            f"{c['n_trades']} | {c['annual_trades']:.1f} | "
            f"{c['sharpe']:+.4f} | {c['annual_pnl']:+.1f} | {c['max_dd']:.1f} | "
            f"{c['a4_n_positive']}/4 | {c['a5_stressed_annual_pnl']:+.1f} | "
            f"{_gate_glyph(c, 'A0')} | {_gate_glyph(c, 'A1')} | {_gate_glyph(c, 'A2')} | "
            f"{_gate_glyph(c, 'A3')} | {_gate_glyph(c, 'A4')} | {_gate_glyph(c, 'A5')} | "
            f"{c.get('reject_reason') or '-'} |"
        )
    lines.append("")
    lines.append("## Did first-touch + M15 fix overtrading?")
    lines.append("")
    if cell_results:
        ann_trades_list = [c["annual_trades"] for c in cell_results]
        ann_min = min(ann_trades_list)
        ann_max = max(ann_trades_list)
        ann_med = float(np.median(ann_trades_list))
        lines.append(
            f"- 23.0d annual_trades distribution across {len(cell_results)} cells: "
            f"min {ann_min:.1f} / median {ann_med:.1f} / max {ann_max:.1f}"
        )
        lines.append(
            f"- Cells triggering overtrading warning (`> {int(A0_OVERTRADING_WARN)}`): "
            f"{n_overtrading} / {len(cell_results)}"
        )
    lines.append(
        "- 23.0b reference (continuous-trigger Donchian, M5): annual_trades "
        "105,275 – 249,507 across 18 cells; ALL 18 triggered the warning."
    )
    lines.append(
        "- 23.0c reference (first-touch z-score MR, M5): annual_trades "
        "43,378 – 157,058 across 36 cells; ALL 36 triggered the warning."
    )
    lines.append("")
    lines.append("## Best cell deep-dive")
    lines.append("")
    if best is None:
        lines.append("(no cell passes A0; no deep-dive)")
    else:
        best_key = (best["N"], best["horizon_bars"], best["exit_rule"])
        trades = cell_trades[best_key]
        lines.append(f"- N={best['N']}, horizon={best['horizon_bars']}, exit={best['exit_rule']}")
        lines.append(
            f"- n_trades = {best['n_trades']} (long {best['n_long']} / short {best['n_short']})"
        )
        ann_warn = (
            f" — **OVERTRADING WARNING** (> {int(A0_OVERTRADING_WARN)})"
            if best["overtrading_warning"]
            else ""
        )
        lines.append(f"- annual_trades = {best['annual_trades']:.1f}{ann_warn}")
        lines.append(f"- Sharpe = {best['sharpe']:+.4f}")
        lines.append(f"- annual_pnl = {best['annual_pnl']:+.1f} pip")
        lines.append(f"- max_dd = {best['max_dd']:.1f} pip")
        lines.append(
            "- A4 fold Sharpes (k=1..4): " + ", ".join(f"{s:+.4f}" for s in best["a4_fold_sharpes"])
        )
        lines.append(f"- A5 stressed annual_pnl = {best['a5_stressed_annual_pnl']:+.1f} pip")
        lines.append("")
        lines.append("### band_distance_at_entry distribution (|pip| beyond band)")
        lines.append("")
        lines.append(
            f"- p10 = {best.get('band_dist_p10', float('nan')):.3f}, "
            f"p25 = {best.get('band_dist_p25', float('nan')):.3f}, "
            f"p50 = {best.get('band_dist_p50', float('nan')):.3f}, "
            f"p75 = {best.get('band_dist_p75', float('nan')):.3f}, "
            f"p90 = {best.get('band_dist_p90', float('nan')):.3f}"
        )
        lines.append("")
        if holding_stats is not None:
            lines.append("### breakout_holding_diagnostic (forward-path, diagnostic only)")
            lines.append("")
            lines.append(f"- n_trades evaluated: {holding_stats['n_trades']}")
            lines.append(
                f"- M1 bars beyond band (p25/p50/p75): "
                f"{holding_stats['p25_m1']:.1f} / {holding_stats['p50_m1']:.1f} / "
                f"{holding_stats['p75_m1']:.1f}"
            )
            lines.append(
                f"- Fraction held the full horizon: {holding_stats['frac_held_full_horizon']:.4f}"
                if np.isfinite(holding_stats["frac_held_full_horizon"])
                else "- Fraction held the full horizon: data unavailable"
            )
            lines.append(
                "- (Forward-path diagnostic only — NOT used for ADOPT decisions or features.)"
            )
            lines.append("")
        lines.append("### Diagnostics (NOT gates)")
        lines.append("")
        lines.append(f"- hit_rate = {best['hit_rate']:.4f}")
        lines.append(f"- payoff_asymmetry = {best['payoff_asymmetry']:.4f}")
        lines.append(f"- S0 random-entry Sharpe = {best['s0_random_entry_sharpe']:+.4f}")
        if s1 is not None:
            lines.append(
                f"- S1 strict 80/20 OOS: IS Sharpe {s1['is_sharpe']:+.4f} "
                f"(n={s1['is_n']}), OOS Sharpe {s1['oos_sharpe']:+.4f} "
                f"(n={s1['oos_n']}), oos/is ratio {s1['oos_is_ratio']:+.3f}"
            )
        lines.append("")
        lines.append("### Per-pair contribution")
        lines.append("")
        per_pair = per_pair_breakdown(trades)
        lines.append("| pair | n_trades | Sharpe | annual_pnl | hit_rate |")
        lines.append("|---|---|---|---|---|")
        for _, r in per_pair.iterrows():
            lines.append(
                f"| {r['pair']} | {int(r['n_trades'])} | {r['sharpe']:+.4f} | "
                f"{r['annual_pnl']:+.1f} | {r['hit_rate']:.4f} |"
            )
        lines.append("")
        lines.append("### Per-session contribution")
        lines.append("")
        per_session = per_session_breakdown(trades)
        lines.append("| session | n_trades | Sharpe | annual_pnl | hit_rate |")
        lines.append("|---|---|---|---|---|")
        for _, r in per_session.iterrows():
            lines.append(
                f"| {r['session']} | {int(r['n_trades'])} | {r['sharpe']:+.4f} | "
                f"{r['annual_pnl']:+.1f} | {r['hit_rate']:.4f} |"
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return {"verdict": verdict, "best": best, "s1": s1, "holding_stats": holding_stats}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_20)
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke run: 3 pairs (USD_JPY/EUR_USD/GBP_JPY) × 2 cells.",
    )
    args = parser.parse_args(argv)

    if args.smoke:
        args.pairs = SMOKE_PAIRS
        cells = list(SMOKE_CELLS)
    else:
        cells = None

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 23.0d M15 Donchian first-touch eval ({len(args.pairs)} pairs) ===")
    print(f"Trigger mode: {TRIGGER_MODE}")
    cell_results, cell_trades = run_sweep(args.pairs, cells=cells)
    out_path = args.out_dir / "eval_report.md"
    summary = write_report(out_path, cell_results, cell_trades, args.pairs)
    print(f"\nReport: {out_path}")
    print(f"Verdict: {summary['verdict']}")
    if summary["best"]:
        b = summary["best"]
        print(
            f"Best cell: N={b['N']} h={b['horizon_bars']} exit={b['exit_rule']} "
            f"Sharpe={b['sharpe']:+.4f} ann_pnl={b['annual_pnl']:+.1f}"
        )

    sidecar = args.out_dir / "sweep_results.json"
    sidecar.write_text(json.dumps(cell_results, default=str, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
