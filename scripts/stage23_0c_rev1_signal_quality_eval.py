"""Stage 23.0c-rev1 — Signal-quality control study.

Diagnostic 144-cell sweep that layers four fixed (non-search) signal-quality
control filters on the 23.0c first-touch z-score MR baseline. Bridges
the Phase 23 routing question:

  (1) "Cost regime alone insufficient for naive / weakly-controlled signal
      firing" (supported by 23.0b/c/d)

  vs.

  (2) "M5/M15 has no recoverable edge even with stronger signal-quality
      controls" (would require all 4 filters here to also REJECT)

Filters (each evaluated independently):
  F1 neutral_reset            — re-entry control
  F2 cooldown                 — time-interval control
  F3 reversal_confirmation    — reversal start confirmation (replaces first-touch)
  F4 cost_gate                — per-entry execution-cost sanity gate
                                (NOT a pair filter; per-bar cost_ratio)

Filter constants (FIXED, not searched):
  NEUTRAL_BAND          = 0.5
  COOLDOWN_BARS         = 3
  COST_GATE_THRESHOLD   = 0.6

Sweep: filter {F1, F2, F3, F4} × N {12, 24, 48} × threshold {2.0, 2.5} ×
horizon {1, 2, 3} × exit {tb, time}  =  4 × 36 = 144 cells.

8-gate harness (Phase 22 inherited, identical to 23.0b/c/d):
  A0 ann_tr >= 70 (overtrading WARN > 1000, NOT blocking)
  A1 Sharpe (ddof=0, no √N) >= +0.082
  A2 ann_pnl >= +180 pip
  A3 max_dd <= 200 pip
  A4 5-fold drop k=0, eval k=1..4, count(>0) >= 3
  A5 +0.5 pip stress ann_pnl > 0

S0/S1 diagnostic-only. 3-class verdict + REJECT-reason classification.

**Multiple-testing caveat (mandatory)**: this is a 144-cell diagnostic
sweep; PROMISING / ADOPT_CANDIDATE results are HYPOTHESIS-GENERATING ONLY.
A separate 23.0c-rev2 PR with frozen-cell strict OOS validation is
required before any production discussion.

This script touches NO production code, NO DB schema, NO src/ files.
20-pair canonical universe; no pair / time-of-day filter.
signal_timeframe == 'M5' enforced at runtime.
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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage23_0c_rev1"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage23_0b = importlib.import_module("stage23_0b_m5_donchian_eval")
stage23_0c = importlib.import_module("stage23_0c_m5_zscore_mr_eval")

PAIRS_20 = stage23_0a.PAIRS_20
SIGNAL_TIMEFRAME = "M5"

# ---- Filter constants (FIXED, NOT SEARCHED) ----
NEUTRAL_BAND = 0.5
COOLDOWN_BARS = 3
COST_GATE_THRESHOLD = 0.6

# Sweep grid
FILTERS: tuple[str, ...] = (
    "F1_neutral_reset",
    "F2_cooldown",
    "F3_reversal_confirmation",
    "F4_cost_gate",
)
FILTER_ROLES: dict[str, str] = {
    "F1_neutral_reset": "re-entry control",
    "F2_cooldown": "time-interval control",
    "F3_reversal_confirmation": "reversal start confirmation",
    "F4_cost_gate": "per-entry execution-cost sanity gate (NOT a pair filter)",
}
N_VALUES: tuple[int, ...] = (12, 24, 48)
THRESHOLDS: tuple[float, ...] = (2.0, 2.5)
HORIZONS: tuple[int, ...] = (1, 2, 3)
EXIT_RULES: tuple[str, ...] = ("tb", "time")
EXIT_COL_MAP = {"tb": "tb_pnl", "time": "time_exit_pnl"}

SPAN_DAYS = 730
SPAN_YEARS = SPAN_DAYS / 365.25

# Inherited gate thresholds (same as 23.0b/c/d)
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
classify_reject_reason = stage23_0c.classify_reject_reason

# 23.0c base reference (transcribed from artifacts/stage23_0c/eval_report.md)
BASE_23_0C_BEST = {
    "stage": "23.0c base (no filter)",
    "best_sharpe": -0.2830,
    "best_annual_pnl": -109888.1,
    "best_annual_trades": 43378.2,
    "best_cell": "N=48, thr=2.5, h=3, exit=time",
}

SMOKE_PAIRS = ["USD_JPY", "EUR_USD", "GBP_JPY"]
SMOKE_CELLS_PER_FILTER: tuple[tuple[int, float, int, str], ...] = (
    (24, 2.0, 1, "tb"),
    (24, 2.0, 2, "time"),
)


# ---------------------------------------------------------------------------
# Numpy-array signal generators (per pair, per (N, threshold))
# ---------------------------------------------------------------------------


def _signals_first_touch(z: np.ndarray, threshold: float) -> tuple[np.ndarray, np.ndarray]:
    """23.0c first-touch base. Returns (long_idx, short_idx) into z."""
    if len(z) < 2:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64)
    z_prev = np.concatenate([[np.nan], z[:-1]])
    z_finite = np.isfinite(z) & np.isfinite(z_prev)
    long_first = (z < -threshold) & (z_prev >= -threshold) & z_finite
    short_first = (z > threshold) & (z_prev <= threshold) & z_finite
    return np.where(long_first)[0], np.where(short_first)[0]


def _signals_f1_neutral_reset(
    z: np.ndarray, threshold: float, neutral_band: float
) -> tuple[np.ndarray, np.ndarray]:
    """F1: trigger on extreme entry; lock until |z| <= neutral_band."""
    long_idx: list[int] = []
    short_idx: list[int] = []
    locked_long = False
    locked_short = False
    for t in range(len(z)):
        z_t = z[t]
        if not np.isfinite(z_t):
            continue
        if abs(z_t) <= neutral_band:
            locked_long = False
            locked_short = False
        if z_t < -threshold and not locked_long:
            long_idx.append(t)
            locked_long = True
        if z_t > threshold and not locked_short:
            short_idx.append(t)
            locked_short = True
    return np.asarray(long_idx, dtype=np.int64), np.asarray(short_idx, dtype=np.int64)


def _signals_f2_cooldown(
    long_idx_first_touch: np.ndarray,
    short_idx_first_touch: np.ndarray,
    cooldown_bars: int,
) -> tuple[np.ndarray, np.ndarray]:
    """F2: filter first-touch signals by enforcing minimum bar separation per direction."""

    def _filter(idx: np.ndarray) -> np.ndarray:
        if len(idx) == 0:
            return idx
        out: list[int] = []
        last = -(10**9)
        for i in idx:
            if i - last >= cooldown_bars:
                out.append(int(i))
                last = int(i)
        return np.asarray(out, dtype=np.int64)

    return _filter(long_idx_first_touch), _filter(short_idx_first_touch)


def _signals_f3_reversal(
    z: np.ndarray, mid_c: np.ndarray, threshold: float, neutral_band: float
) -> tuple[np.ndarray, np.ndarray]:
    """F3: reversal-confirmation trigger with neutral-band lock release.

    Long fires when z is below -threshold AND z is rising AND mid_c is rising
    AND not locked. Lock releases when |z| <= neutral_band.
    """
    long_idx: list[int] = []
    short_idx: list[int] = []
    locked_long = False
    locked_short = False
    z_prev = np.nan
    mid_c_prev = np.nan
    for t in range(len(z)):
        z_t = z[t]
        m_t = mid_c[t]
        if not np.isfinite(z_t) or not np.isfinite(m_t):
            z_prev = z_t
            mid_c_prev = m_t
            continue
        if abs(z_t) <= neutral_band:
            locked_long = False
            locked_short = False
        if (
            z_t < -threshold
            and np.isfinite(z_prev)
            and z_t > z_prev
            and np.isfinite(mid_c_prev)
            and m_t > mid_c_prev
            and not locked_long
        ):
            long_idx.append(t)
            locked_long = True
        if (
            z_t > threshold
            and np.isfinite(z_prev)
            and z_t < z_prev
            and np.isfinite(mid_c_prev)
            and m_t < mid_c_prev
            and not locked_short
        ):
            short_idx.append(t)
            locked_short = True
        z_prev = z_t
        mid_c_prev = m_t
    return np.asarray(long_idx, dtype=np.int64), np.asarray(short_idx, dtype=np.int64)


# ---------------------------------------------------------------------------
# Per-pair signal frame construction
# ---------------------------------------------------------------------------


def _make_signal_frame(
    idx: pd.DatetimeIndex,
    long_idx: np.ndarray,
    short_idx: np.ndarray,
    pair: str,
) -> pd.DataFrame:
    if len(long_idx) == 0 and len(short_idx) == 0:
        return pd.DataFrame(columns=["entry_ts", "pair", "direction"])
    return pd.DataFrame(
        {
            "entry_ts": list(idx[long_idx]) + list(idx[short_idx]),
            "direction": ["long"] * len(long_idx) + ["short"] * len(short_idx),
            "pair": pair,
        }
    )


# ---------------------------------------------------------------------------
# Sweep runner
# ---------------------------------------------------------------------------


def run_sweep(
    pairs: list[str],
    cells: list[tuple[int, float, int, str]] | None = None,
    filters: list[str] | None = None,
) -> tuple[list[dict], dict]:
    if cells is None:
        cells = [
            (n, thr, h, e)
            for n in N_VALUES
            for thr in THRESHOLDS
            for h in HORIZONS
            for e in EXIT_RULES
        ]
    if filters is None:
        filters = list(FILTERS)

    # Phase 1: per-pair m5 + z-by-N + labels (NG#6 enforced inside loader)
    print(f"--- loading m5 + labels for {len(pairs)} pairs ---")
    per_pair_idx: dict[str, pd.DatetimeIndex] = {}
    per_pair_mid_c: dict[str, np.ndarray] = {}
    per_pair_z: dict[str, dict[int, np.ndarray]] = {}
    per_pair_labels: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        t0 = time.time()
        m1 = stage23_0a.load_m1_ba(pair, days=SPAN_DAYS)
        m5 = stage23_0a.aggregate_m1_to_tf(m1, SIGNAL_TIMEFRAME)
        per_pair_idx[pair] = m5.index
        per_pair_mid_c[pair] = ((m5["bid_c"] + m5["ask_c"]) / 2.0).to_numpy()
        per_pair_z[pair] = {}
        for n in N_VALUES:
            df_z = stage23_0c.compute_zscore(m5, n)
            per_pair_z[pair][n] = df_z[f"z_{n}"].to_numpy()
        per_pair_labels[pair] = stage23_0b.load_pair_labels(pair, signal_tf=SIGNAL_TIMEFRAME)
        print(f"  {pair}: m5={len(m5)} rows ({time.time() - t0:5.1f}s)")

    # Phase 2: per-(pair, N, threshold, filter) signals
    print("--- generating per-pair signals (4 filters × 3 N × 2 threshold) ---")
    per_pair_signals: dict[tuple[str, int, float, str], pd.DataFrame] = {}
    for pair in pairs:
        idx = per_pair_idx[pair]
        mid_c = per_pair_mid_c[pair]
        for n in N_VALUES:
            z = per_pair_z[pair][n]
            for thr in THRESHOLDS:
                ft_long, ft_short = _signals_first_touch(z, thr)
                if "F1_neutral_reset" in filters:
                    f1_long, f1_short = _signals_f1_neutral_reset(z, thr, NEUTRAL_BAND)
                    per_pair_signals[(pair, n, thr, "F1_neutral_reset")] = _make_signal_frame(
                        idx, f1_long, f1_short, pair
                    )
                if "F2_cooldown" in filters:
                    f2_long, f2_short = _signals_f2_cooldown(ft_long, ft_short, COOLDOWN_BARS)
                    per_pair_signals[(pair, n, thr, "F2_cooldown")] = _make_signal_frame(
                        idx, f2_long, f2_short, pair
                    )
                if "F3_reversal_confirmation" in filters:
                    f3_long, f3_short = _signals_f3_reversal(z, mid_c, thr, NEUTRAL_BAND)
                    per_pair_signals[(pair, n, thr, "F3_reversal_confirmation")] = (
                        _make_signal_frame(idx, f3_long, f3_short, pair)
                    )
                if "F4_cost_gate" in filters:
                    # F4 base signals = first-touch; cost gate applies post-join
                    per_pair_signals[(pair, n, thr, "F4_cost_gate")] = _make_signal_frame(
                        idx, ft_long, ft_short, pair
                    )

    # Phase 3: per-cell evaluation
    print(f"--- evaluating {len(filters) * len(cells)} cells ---")
    cell_results: list[dict] = []
    cell_trades: dict = {}

    for filter_name in filters:
        for n, thr, h, exit_rule in cells:
            exit_col = EXIT_COL_MAP[exit_rule]
            pooled_parts: list[pd.DataFrame] = []
            labels_pool_parts: list[pd.DataFrame] = []
            for pair in pairs:
                sig = per_pair_signals[(pair, n, thr, filter_name)]
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
                            "cost_ratio",
                        ]
                    ],
                    on=["entry_ts", "pair", "direction"],
                    how="inner",
                )
                joined["pnl_pip"] = joined[exit_col].astype(np.float64)
                joined = joined.dropna(subset=["pnl_pip"])
                pooled_parts.append(joined)
                labels_pool_parts.append(labels_pair_h)

            if pooled_parts:
                trades = pd.concat(pooled_parts, ignore_index=True)
            else:
                trades = pd.DataFrame(
                    columns=[
                        "entry_ts",
                        "pair",
                        "direction",
                        "tb_pnl",
                        "time_exit_pnl",
                        "pnl_pip",
                        "cost_ratio",
                    ]
                )
            labels_pool = (
                pd.concat(labels_pool_parts, ignore_index=True)
                if labels_pool_parts
                else pd.DataFrame()
            )

            if filter_name == "F4_cost_gate" and len(trades) > 0:
                trades = trades[trades["cost_ratio"] <= COST_GATE_THRESHOLD].reset_index(drop=True)

            if len(trades) > 0 and (trades["signal_timeframe"] != SIGNAL_TIMEFRAME).any():
                raise RuntimeError(
                    f"NG#6 violation: filter={filter_name} cell (N={n}, thr={thr}, h={h}, "
                    f"exit={exit_rule}) emitted a row with signal_timeframe != "
                    f"{SIGNAL_TIMEFRAME}"
                )

            metrics = stage23_0b.evaluate_cell(trades, labels_pool, exit_col)
            gates = gate_matrix(metrics)
            reject_reason = classify_reject_reason(metrics, gates)
            cell_results.append(
                {
                    "filter": filter_name,
                    "N": n,
                    "threshold": thr,
                    "horizon_bars": h,
                    "exit_rule": exit_rule,
                    "reject_reason": reject_reason,
                    **metrics,
                    **{f"gate_{k}": v for k, v in gates.items()},
                }
            )
            cell_trades[(filter_name, n, thr, h, exit_rule)] = trades

    # Print compact log
    for c in cell_results:
        gates_bits = "".join(
            "1" if c[f"gate_{g}"] else "0" for g in ("A0", "A1", "A2", "A3", "A4", "A5")
        )
        print(
            f"  {c['filter']:<26} N={c['N']:>2} thr={c['threshold']:.1f} h={c['horizon_bars']} "
            f"exit={c['exit_rule']:<4} n={c['n_trades']:>5} ann_tr={c['annual_trades']:8.1f} "
            f"sharpe={c['sharpe']:+.4f} ann_pnl={c['annual_pnl']:+8.1f} "
            f"gates={gates_bits} reason={c['reject_reason'] or '-'}"
        )
    return cell_results, cell_trades


# ---------------------------------------------------------------------------
# Per-filter and overall verdict
# ---------------------------------------------------------------------------


def select_best_cell_in_filter(cell_results: list[dict], filter_name: str) -> dict | None:
    eligible = [
        c
        for c in cell_results
        if c["filter"] == filter_name and c["gate_A0"] and np.isfinite(c["sharpe"])
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda c: c["sharpe"])


def assign_per_filter_verdict(best_cell: dict | None, s1: dict | None) -> str:
    if best_cell is None:
        return "REJECT"
    gates_only = {k.replace("gate_", ""): v for k, v in best_cell.items() if k.startswith("gate_")}
    return assign_verdict(gates_only, s1)


def overall_verdict(per_filter_verdicts: dict[str, str]) -> tuple[str, str | None]:
    """Return (verdict, winning_filter_name_or_None)."""
    for v in ("ADOPT_CANDIDATE",):
        for fname, vfilter in per_filter_verdicts.items():
            if vfilter == v:
                return v, fname
    for v in ("PROMISING_BUT_NEEDS_OOS",):
        for fname, vfilter in per_filter_verdicts.items():
            if vfilter == v:
                return v, fname
    return "REJECT", None


# ---------------------------------------------------------------------------
# Filter effectiveness ranking
# ---------------------------------------------------------------------------


def filter_effectiveness_ranking(cell_results: list[dict], filters: list[str]) -> list[dict]:
    rows = []
    for filter_name in filters:
        sub = [c for c in cell_results if c["filter"] == filter_name]
        if not sub:
            rows.append(
                {
                    "filter": filter_name,
                    "n_cells": 0,
                    "median_ann_trades": float("nan"),
                    "median_sharpe": float("nan"),
                    "best_sharpe": float("nan"),
                    "best_ann_trades": float("nan"),
                    "n_pass_a0": 0,
                    "n_pass_a1": 0,
                    "n_pass_a2": 0,
                }
            )
            continue
        ann = np.asarray([c["annual_trades"] for c in sub])
        sharpes = np.asarray([c["sharpe"] if np.isfinite(c["sharpe"]) else -1e9 for c in sub])
        rows.append(
            {
                "filter": filter_name,
                "n_cells": len(sub),
                "median_ann_trades": float(np.median(ann)),
                "median_sharpe": float(np.median(sharpes)),
                "best_sharpe": float(np.max(sharpes)),
                "best_ann_trades": float(np.min(ann)),
                "n_pass_a0": int(sum(1 for c in sub if c["gate_A0"])),
                "n_pass_a1": int(sum(1 for c in sub if c["gate_A1"])),
                "n_pass_a2": int(sum(1 for c in sub if c["gate_A2"])),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def write_report(
    out_path: Path,
    cell_results: list[dict],
    cell_trades: dict,
    pairs: list[str],
    filters: list[str],
) -> dict:
    # Per-filter best cell + verdict + S1
    per_filter_best: dict[str, dict | None] = {}
    per_filter_s1: dict[str, dict | None] = {}
    per_filter_verdict: dict[str, str] = {}
    for filter_name in filters:
        best = select_best_cell_in_filter(cell_results, filter_name)
        per_filter_best[filter_name] = best
        if best is not None:
            key = (
                best["filter"],
                best["N"],
                best["threshold"],
                best["horizon_bars"],
                best["exit_rule"],
            )
            per_filter_s1[filter_name] = _strict_oos_split(cell_trades[key])
        else:
            per_filter_s1[filter_name] = None
        per_filter_verdict[filter_name] = assign_per_filter_verdict(
            best, per_filter_s1[filter_name]
        )
    overall, winning_filter = overall_verdict(per_filter_verdict)

    # Per-cell verdict + reject_reason counts
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

    # F4-only flag
    f4_only_improvement = (
        per_filter_verdict.get("F4_cost_gate", "REJECT")
        in ("ADOPT_CANDIDATE", "PROMISING_BUT_NEEDS_OOS")
        and per_filter_verdict.get("F1_neutral_reset", "REJECT") == "REJECT"
        and per_filter_verdict.get("F2_cooldown", "REJECT") == "REJECT"
        and per_filter_verdict.get("F3_reversal_confirmation", "REJECT") == "REJECT"
    )

    rank_rows = filter_effectiveness_ranking(cell_results, filters)

    lines: list[str] = []
    lines.append("# Stage 23.0c-rev1 — Signal-Quality Control Study")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase23_0c_rev1_signal_quality.md`")
    lines.append("")
    lines.append(
        f"Universe: {len(pairs)} pairs, signal TF = `{SIGNAL_TIMEFRAME}`, span = {SPAN_DAYS}d"
    )
    lines.append(
        f"Sweep: {len(filters)} filter(s) × N {N_VALUES} × threshold {THRESHOLDS} × "
        f"horizon {HORIZONS} × exit {EXIT_RULES} = {len(cell_results)} cells"
    )
    lines.append(
        f"Filter constants (FIXED): NEUTRAL_BAND={NEUTRAL_BAND}, "
        f"COOLDOWN_BARS={COOLDOWN_BARS}, COST_GATE_THRESHOLD={COST_GATE_THRESHOLD}"
    )
    lines.append("")
    lines.append("## Multiple-testing caveat (mandatory)")
    lines.append("")
    lines.append(
        "**This is a 144-cell diagnostic sweep across 4 filters; PROMISING / ADOPT_CANDIDATE "
        "results are HYPOTHESIS-GENERATING ONLY.** A separate `23.0c-rev2` PR with "
        "frozen-cell strict OOS validation (no parameter re-search, no filter re-search) "
        "is mandatory before any production discussion. The per-filter `assign_verdict` "
        "function does NOT correct for the 144-cell multiple-testing inflation."
    )
    lines.append("")
    lines.append("## Headline overall verdict")
    lines.append("")
    lines.append(
        f"**{overall}**" + (f" (winning filter: `{winning_filter}`)" if winning_filter else "")
    )
    lines.append("")
    lines.append(
        f"Per-cell verdict counts: {n_reject} REJECT / "
        f"{n_promising} PROMISING_BUT_NEEDS_OOS / "
        f"{n_adopt_candidate} ADOPT_CANDIDATE — out of {len(cell_results)} cells."
    )
    lines.append("")
    if reject_reason_counts:
        lines.append("REJECT reason breakdown (across all 144 cells):")
        for reason in (
            "under_firing",
            "still_overtrading",
            "pnl_edge_insufficient",
            "robustness_failure",
        ):
            count = reject_reason_counts.get(reason, 0)
            lines.append(f"- {reason}: {count} cell(s)")
        lines.append("")

    lines.append("## Filter roles (interpretation labels)")
    lines.append("")
    for filter_name in filters:
        lines.append(f"- **{filter_name}**: {FILTER_ROLES[filter_name]}")
    lines.append("")
    if f4_only_improvement:
        lines.append("## F4-only improvement flag")
        lines.append("")
        lines.append(
            "**F4 cost_gate is the ONLY filter producing a non-REJECT verdict in this run.** "
            "Per design §6.4, this is flagged as a **cost-based selection effect**: the "
            "improvement is driven by selecting trades with favourable per-entry execution "
            "cost, not by improving signal precision per se. The same per-entry cost filter "
            "could be applied to ANY signal source as a trivial post-hoc improvement. "
            "F4-only ADOPT_CANDIDATE / PROMISING therefore warrants extra scrutiny before "
            "being treated as evidence for 'M5 z-score MR has a recoverable edge under "
            "signal-quality controls': the result may instead say 'high-cost trades drag "
            "the average; drop them and the average improves' — a tautology rather than a "
            "finding about MR. Treat F4-only results as further evidence supporting "
            "Phase 23 closure path A (no recoverable edge under stronger controls)."
        )
        lines.append("")

    lines.append("## Per-filter verdict")
    lines.append("")
    lines.append("| filter | role | best cell | Sharpe | annual_pnl | annual_trades | verdict |")
    lines.append("|---|---|---|---|---|---|---|")
    for filter_name in filters:
        best = per_filter_best[filter_name]
        v = per_filter_verdict[filter_name]
        if best is None:
            role = FILTER_ROLES[filter_name]
            lines.append(f"| {filter_name} | {role} | (none passes A0) | - | - | - | {v} |")
        else:
            lines.append(
                f"| {filter_name} | {FILTER_ROLES[filter_name]} | "
                f"N={best['N']}, thr={best['threshold']}, h={best['horizon_bars']}, "
                f"exit={best['exit_rule']} | {best['sharpe']:+.4f} | "
                f"{best['annual_pnl']:+.1f} | {best['annual_trades']:.1f} | {v} |"
            )
    lines.append("")

    lines.append("## Comparison vs 23.0c base")
    lines.append("")
    lines.append(
        "| stage / filter | best Sharpe | best annual_pnl pip | best annual_trades | best cell |"
    )
    lines.append("|---|---|---|---|---|")
    base = BASE_23_0C_BEST
    lines.append(
        f"| {base['stage']} | {base['best_sharpe']:+.4f} | "
        f"{base['best_annual_pnl']:+.1f} | {base['best_annual_trades']:.1f} | "
        f"{base['best_cell']} |"
    )
    for filter_name in filters:
        best = per_filter_best[filter_name]
        if best is None:
            lines.append(f"| {filter_name} | (none passes A0) | - | - | - |")
        else:
            lines.append(
                f"| {filter_name} | {best['sharpe']:+.4f} | {best['annual_pnl']:+.1f} | "
                f"{best['annual_trades']:.1f} | "
                f"N={best['N']}, thr={best['threshold']}, h={best['horizon_bars']}, "
                f"exit={best['exit_rule']} |"
            )
    lines.append("")

    lines.append("## Filter effectiveness summary (across 36 sub-cells per filter)")
    lines.append("")
    lines.append(
        "| filter | n_cells | median ann_tr | median Sharpe | best Sharpe | "
        "best ann_tr | A0 pass | A1 pass | A2 pass |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for r in rank_rows:
        lines.append(
            f"| {r['filter']} | {r['n_cells']} | {r['median_ann_trades']:.1f} | "
            f"{r['median_sharpe']:+.4f} | {r['best_sharpe']:+.4f} | "
            f"{r['best_ann_trades']:.1f} | {r['n_pass_a0']} | {r['n_pass_a1']} | "
            f"{r['n_pass_a2']} |"
        )
    lines.append("")
    lines.append(
        "23.0b reference (continuous-trigger Donchian, M5): annual_trades 105k–250k, "
        "all 18 cells overtrading.  "
        "23.0c reference (first-touch z-MR, M5): 43k–157k, all 36 cells overtrading.  "
        "23.0d reference (first-touch Donchian, M15): 22k–53k, all 18 cells overtrading."
    )
    lines.append("")

    lines.append("## Phase 23 routing post-23.0c-rev1")
    lines.append("")
    lines.append("```")
    lines.append("23.0c-rev1 returns:")
    lines.append("├── any filter ADOPT_CANDIDATE / PROMISING")
    lines.append("│     → that single frozen cell promotes to 23.0c-rev2")
    lines.append("│       (frozen-cell strict OOS, no parameter re-search)")
    lines.append("│     → 23.0e meta-labeling MAY trigger on this cell")
    lines.append("│     → Phase 23 conclusion (path B): 'naive firing was the issue;")
    lines.append("│       signal-quality controls fix it'")
    lines.append("│")
    lines.append("└── all 4 filters REJECT")
    lines.append("      → 23.0e DOES NOT trigger")
    lines.append("      → Phase 23 closes (path A): 'M5/M15 has no recoverable edge")
    lines.append("        even with stronger signal-quality controls'")
    lines.append("      → Phase 24 (Exit/Capture Study, kickoff §7) becomes the next pivot")
    lines.append("```")
    lines.append("")
    if overall == "REJECT":
        lines.append(
            "**This run lands on path A**: all 4 filters REJECT. Phase 23 closes with the "
            "negative-but-bounded conclusion. Per design §6.4, F4-only success would have "
            "been flagged as a cost-based selection effect (separate diagnosis); here all "
            "four filters fail the gate, supporting the broader 'no recoverable edge under "
            "stronger controls' conclusion."
        )
    else:
        lines.append(
            f"**This run lands on path B**: {winning_filter} produced {overall}. The "
            "winning cell must promote to a separate 23.0c-rev2 PR with frozen-cell "
            "strict OOS validation BEFORE any production discussion (multiple-testing "
            "inflation across 144 cells)."
        )
    lines.append("")

    lines.append("## Production-readiness")
    lines.append("")
    lines.append(
        f"Even an `ADOPT_CANDIDATE` verdict is **not** production-ready. {len(cell_results)}-cell "
        "diagnostic sweep with multiple-testing inflation. A separate `23.0c-rev2` PR "
        "with frozen-cell strict OOS validation on chronologically out-of-sample data "
        "and no parameter re-search is required before any production migration."
    )
    lines.append("")

    lines.append("## Best cell deep-dive (per filter)")
    lines.append("")
    for filter_name in filters:
        best = per_filter_best[filter_name]
        s1 = per_filter_s1[filter_name]
        lines.append(f"### {filter_name} — {FILTER_ROLES[filter_name]}")
        lines.append("")
        if best is None:
            lines.append("(no cell passes A0; no deep-dive)")
            lines.append("")
            continue
        lines.append(
            f"- N={best['N']}, threshold={best['threshold']}, "
            f"horizon={best['horizon_bars']}, exit={best['exit_rule']}"
        )
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
        lines.append(f"- hit_rate = {best['hit_rate']:.4f}")
        lines.append(f"- payoff_asymmetry = {best['payoff_asymmetry']:.4f}")
        lines.append(f"- S0 random-entry Sharpe = {best['s0_random_entry_sharpe']:+.4f}")
        if s1 is not None:
            lines.append(
                f"- S1 strict 80/20 OOS: IS {s1['is_sharpe']:+.4f} (n={s1['is_n']}), "
                f"OOS {s1['oos_sharpe']:+.4f} (n={s1['oos_n']}), "
                f"oos/is ratio {s1['oos_is_ratio']:+.3f}"
            )
        lines.append(f"- verdict: **{per_filter_verdict[filter_name]}**")
        lines.append("")

    lines.append("## Sweep summary (all cells, sorted by Sharpe within filter)")
    lines.append("")
    for filter_name in filters:
        sub = [c for c in cell_results if c["filter"] == filter_name]
        if not sub:
            continue
        lines.append(f"### {filter_name}")
        lines.append("")
        lines.append(
            "| N | thr | h | exit | n_trades | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | "
            "A5 stress | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

        def _g(c: dict, name: str) -> str:
            return "✓" if c[f"gate_{name}"] else "✗"

        for c in sorted(
            sub,
            key=lambda x: x["sharpe"] if np.isfinite(x["sharpe"]) else -1e9,
            reverse=True,
        ):
            lines.append(
                f"| {c['N']} | {c['threshold']:.1f} | {c['horizon_bars']} | {c['exit_rule']} | "
                f"{c['n_trades']} | {c['annual_trades']:.1f} | "
                f"{c['sharpe']:+.4f} | {c['annual_pnl']:+.1f} | {c['max_dd']:.1f} | "
                f"{c['a4_n_positive']}/4 | {c['a5_stressed_annual_pnl']:+.1f} | "
                f"{_g(c, 'A0')} | {_g(c, 'A1')} | {_g(c, 'A2')} | "
                f"{_g(c, 'A3')} | {_g(c, 'A4')} | {_g(c, 'A5')} | "
                f"{c.get('reject_reason') or '-'} |"
            )
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return {
        "overall_verdict": overall,
        "winning_filter": winning_filter,
        "per_filter_verdict": per_filter_verdict,
        "per_filter_best": per_filter_best,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_20)
    parser.add_argument("--filters", nargs="*", default=list(FILTERS))
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke run: 3 pairs × 4 filters × 2 cells each = 24 evals.",
    )
    args = parser.parse_args(argv)

    if args.smoke:
        args.pairs = SMOKE_PAIRS
        cells = list(SMOKE_CELLS_PER_FILTER)
    else:
        cells = None

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 23.0c-rev1 signal-quality control ({len(args.pairs)} pairs) ===")
    print(f"Filters: {args.filters}")
    print(
        f"Filter constants: NEUTRAL_BAND={NEUTRAL_BAND}, COOLDOWN_BARS={COOLDOWN_BARS}, "
        f"COST_GATE_THRESHOLD={COST_GATE_THRESHOLD}"
    )
    cell_results, cell_trades = run_sweep(args.pairs, cells=cells, filters=args.filters)
    out_path = args.out_dir / "eval_report.md"
    summary = write_report(out_path, cell_results, cell_trades, args.pairs, args.filters)
    print(f"\nReport: {out_path}")
    print(f"Overall verdict: {summary['overall_verdict']}")
    if summary["winning_filter"]:
        print(f"Winning filter: {summary['winning_filter']}")
    print("Per-filter verdicts:")
    for fname, v in summary["per_filter_verdict"].items():
        print(f"  {fname}: {v}")

    sidecar = args.out_dir / "sweep_results.json"
    sidecar.write_text(json.dumps(cell_results, default=str, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
