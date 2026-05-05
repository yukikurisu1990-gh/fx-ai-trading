"""Stage 23.0b — M5 Donchian breakout + M1 execution baseline eval.

Rule-based Donchian breakout on the M5 signal timeframe; PnL via M1
execution recorded in 23.0a's ``labels_M5_<pair>.parquet``.

Sweep:
- N (Donchian window, M5 bars): {10, 20, 50}
- horizon_bars: {1, 2, 3}
- exit_rule: {tb (= tb_pnl), time (= time_exit_pnl)}
= 18 cells.

Gates (Phase 22 inherited, exact thresholds):
- A0: annual_trades >= 70 (overtrading warning if > 1000, not blocking)
- A1: per-trade Sharpe (ddof=0, no sqrt-of-N) >= +0.082
- A2: annual_pnl_pip >= +180
- A3: max_dd_pip <= 200
- A4: 5-fold chronological split, drop k=0, evaluate k=1..4,
       count(Sharpe > 0) >= 3
- A5: annual_pnl after subtracting 0.5 pip per round trip > 0

Diagnostics (NOT gates): hit_rate, payoff_asymmetry, false_breakout_rate,
per-pair contribution, per-session contribution, S0 random-entry Sharpe,
S1 strict 80/20 OOS Sharpe.

Verdict (3-class):
- ADOPT_CANDIDATE: A0..A5 all pass AND S1 strong (oos > 0 and oos/is >= 0.5)
- PROMISING_BUT_NEEDS_OOS: A0..A3 pass but A4 OR A5 fails;
                           OR A0..A5 all pass but S1 weak
- REJECT: A1 OR A2 fails; OR A0 fails

Production-readiness: even ADOPT_CANDIDATE requires a separate 23.0b-v2
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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage23_0b"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")

PAIRS_20 = stage23_0a.PAIRS_20
SIGNAL_TIMEFRAME = "M5"

N_VALUES: tuple[int, ...] = (10, 20, 50)
HORIZONS: tuple[int, ...] = (1, 2, 3)
EXIT_RULES: tuple[str, ...] = ("tb", "time")
EXIT_COL_MAP = {"tb": "tb_pnl", "time": "time_exit_pnl"}

SPAN_DAYS = 730
SPAN_YEARS = SPAN_DAYS / 365.25

# Phase 22 inherited gate thresholds
A0_MIN_ANNUAL_TRADES = 70.0
A0_OVERTRADING_WARN = 1000.0  # not blocking
A1_MIN_SHARPE = 0.082
A2_MIN_ANNUAL_PNL = 180.0
A3_MAX_MAXDD = 200.0
A4_MIN_POSITIVE_FOLDS = 3
A4_EVAL_FOLDS = 4  # k=1..4 of 5
A5_SPREAD_STRESS_PIP = 0.5  # per round trip

# Diagnostic thresholds
S0_SEED = 42
S1_OOS_FRACTION = 0.20
S1_STRONG_RATIO = 0.5  # oos_sharpe / is_sharpe >= 0.5 AND oos_sharpe > 0
FALSE_BREAKOUT_LOOKAHEAD_M1 = 5  # bars

SMOKE_PAIRS = ["USD_JPY", "EUR_USD", "GBP_JPY"]
SMOKE_CELLS: tuple[tuple[int, int, str], ...] = ((20, 1, "tb"), (20, 2, "time"))


# ---------------------------------------------------------------------------
# Signal generation
# ---------------------------------------------------------------------------


def compute_donchian_bands(m5_df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Return a copy of m5_df with mid OHLC and causal Donchian bands."""
    out = m5_df.copy()
    out["mid_h"] = (out["bid_h"] + out["ask_h"]) / 2.0
    out["mid_l"] = (out["bid_l"] + out["ask_l"]) / 2.0
    out["mid_c"] = (out["bid_c"] + out["ask_c"]) / 2.0
    out[f"upper_{n}"] = out["mid_h"].shift(1).rolling(n).max()
    out[f"lower_{n}"] = out["mid_l"].shift(1).rolling(n).min()
    return out


def extract_signals(m5_df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Emit Donchian breakout signals for window N.

    Returns columns [entry_ts, direction]. entry_ts equals the M5 signal-bar
    boundary (right-edge); the 23.0a outcome dataset uses the same key.
    """
    df = compute_donchian_bands(m5_df, n)
    upper = df[f"upper_{n}"]
    lower = df[f"lower_{n}"]
    long_break = (df["mid_c"] > upper) & upper.notna()
    short_break = (df["mid_c"] < lower) & lower.notna()

    sig_long = df.index[long_break]
    sig_short = df.index[short_break]
    out = pd.DataFrame(
        {
            "entry_ts": list(sig_long) + list(sig_short),
            "direction": ["long"] * len(sig_long) + ["short"] * len(sig_short),
        }
    )
    return out


def load_pair_signals_all_n(pair: str, days: int = SPAN_DAYS) -> dict[int, pd.DataFrame]:
    """Build M5 OHLC + Donchian signals once per pair, for all N values.

    Returns: {N: signals_df with columns [entry_ts, direction]}.
    """
    m1 = stage23_0a.load_m1_ba(pair, days=days)
    m5 = stage23_0a.aggregate_m1_to_tf(m1, SIGNAL_TIMEFRAME)
    out: dict[int, pd.DataFrame] = {}
    for n in N_VALUES:
        out[n] = extract_signals(m5, n)
    return out, m5


def load_pair_labels(pair: str, signal_tf: str = SIGNAL_TIMEFRAME) -> pd.DataFrame:
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
# Cell evaluation
# ---------------------------------------------------------------------------


def _per_trade_sharpe(pnl: np.ndarray | pd.Series) -> float:
    arr = np.asarray(pnl, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if len(arr) < 2:
        return float("nan")
    sd = arr.std(ddof=0)
    if sd <= 0:
        return float("nan")
    return float(arr.mean() / sd)


def _max_drawdown_pip(pnl: pd.Series) -> float:
    arr = np.asarray(pnl, dtype=np.float64)
    arr = arr[np.isfinite(arr)]
    if len(arr) == 0:
        return float("nan")
    cum = np.cumsum(arr)
    running_max = np.maximum.accumulate(cum)
    dd = cum - running_max  # always <= 0
    return float(-dd.min())


def _fold_stability(trades_df: pd.DataFrame) -> dict:
    """5-fold chronological, drop k=0, eval k=1..4, count Sharpe > 0."""
    n = len(trades_df)
    if n < 5:
        return {
            "fold_sharpes_all": [float("nan")] * 5,
            "fold_sharpes_eval": [float("nan")] * 4,
            "n_positive": 0,
        }
    sorted_df = trades_df.sort_values("entry_ts").reset_index(drop=True)
    boundaries = [int(round(k * n / 5)) for k in range(6)]
    fold_sharpes_all: list[float] = []
    for k in range(5):
        lo, hi = boundaries[k], boundaries[k + 1]
        fold = sorted_df.iloc[lo:hi]
        s = _per_trade_sharpe(fold["pnl_pip"]) if len(fold) >= 2 else float("nan")
        fold_sharpes_all.append(s)
    fold_sharpes_eval = fold_sharpes_all[1:]  # drop k=0 warmup
    n_positive = sum(1 for s in fold_sharpes_eval if np.isfinite(s) and s > 0)
    return {
        "fold_sharpes_all": fold_sharpes_all,
        "fold_sharpes_eval": fold_sharpes_eval,
        "n_positive": n_positive,
    }


def _strict_oos_split(trades_df: pd.DataFrame) -> dict:
    n = len(trades_df)
    if n < 10:
        return {
            "is_sharpe": float("nan"),
            "oos_sharpe": float("nan"),
            "oos_is_ratio": float("nan"),
            "is_n": 0,
            "oos_n": 0,
        }
    sorted_df = trades_df.sort_values("entry_ts").reset_index(drop=True)
    cut = int(round(n * (1 - S1_OOS_FRACTION)))
    is_part = sorted_df.iloc[:cut]
    oos_part = sorted_df.iloc[cut:]
    is_sharpe = _per_trade_sharpe(is_part["pnl_pip"])
    oos_sharpe = _per_trade_sharpe(oos_part["pnl_pip"])
    if np.isfinite(is_sharpe) and is_sharpe > 0:
        oos_is_ratio = oos_sharpe / is_sharpe if np.isfinite(oos_sharpe) else float("nan")
    else:
        oos_is_ratio = float("nan")
    return {
        "is_sharpe": is_sharpe,
        "oos_sharpe": oos_sharpe,
        "oos_is_ratio": oos_is_ratio,
        "is_n": int(len(is_part)),
        "oos_n": int(len(oos_part)),
    }


def _random_entry_sharpe(
    labels_pool: pd.DataFrame, n_long: int, n_short: int, exit_col: str, seed: int = S0_SEED
) -> float:
    """Random-entry baseline matching the Donchian trade count and direction
    balance. Sample without replacement from valid 23.0a rows in the cell's
    (signal_tf, horizon) slice.
    """
    long_pool = labels_pool[labels_pool["direction"] == "long"]
    short_pool = labels_pool[labels_pool["direction"] == "short"]
    parts = []
    if n_long > 0 and len(long_pool) >= n_long:
        parts.append(long_pool.sample(n=n_long, random_state=seed))
    if n_short > 0 and len(short_pool) >= n_short:
        parts.append(short_pool.sample(n=n_short, random_state=seed + 1))
    if not parts:
        return float("nan")
    sampled = pd.concat(parts, ignore_index=True)
    sampled_pnl = sampled[exit_col].astype(np.float64)
    return _per_trade_sharpe(sampled_pnl)


def evaluate_cell(
    trades_df: pd.DataFrame,
    labels_pool_for_s0: pd.DataFrame,
    exit_col: str,
) -> dict:
    n_trades = int(len(trades_df))
    if n_trades == 0:
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
            "s0_random_entry_sharpe": float("nan"),
            "overtrading_warning": False,
            "n_long": 0,
            "n_short": 0,
        }

    pnl = trades_df["pnl_pip"]
    annual_trades = n_trades / SPAN_YEARS
    sharpe = _per_trade_sharpe(pnl)
    annual_pnl = float(pnl.sum() / SPAN_YEARS)
    max_dd = _max_drawdown_pip(pnl)

    fold = _fold_stability(trades_df)
    a4_n_positive = fold["n_positive"]

    stressed_pnl = pnl - A5_SPREAD_STRESS_PIP
    a5_stressed_annual_pnl = float(stressed_pnl.sum() / SPAN_YEARS)

    pos = pnl[pnl > 0]
    neg = pnl[pnl < 0]
    hit_rate = float((pnl > 0).mean()) if n_trades > 0 else float("nan")
    if len(pos) > 0 and len(neg) > 0 and float(neg.mean()) != 0:
        payoff_asymmetry = float(abs(pos.mean()) / abs(neg.mean()))
    else:
        payoff_asymmetry = float("nan")

    n_long = int((trades_df["direction"] == "long").sum())
    n_short = int((trades_df["direction"] == "short").sum())
    s0 = _random_entry_sharpe(labels_pool_for_s0, n_long, n_short, exit_col)

    overtrading = annual_trades > A0_OVERTRADING_WARN

    return {
        "n_trades": n_trades,
        "annual_trades": float(annual_trades),
        "sharpe": float(sharpe),
        "annual_pnl": annual_pnl,
        "max_dd": max_dd,
        "a4_n_positive": int(a4_n_positive),
        "a4_fold_sharpes": fold["fold_sharpes_eval"],
        "a5_stressed_annual_pnl": a5_stressed_annual_pnl,
        "hit_rate": hit_rate,
        "payoff_asymmetry": payoff_asymmetry,
        "s0_random_entry_sharpe": float(s0),
        "overtrading_warning": bool(overtrading),
        "n_long": n_long,
        "n_short": n_short,
    }


def gate_matrix(metrics: dict) -> dict:
    a0 = metrics["annual_trades"] >= A0_MIN_ANNUAL_TRADES
    a1 = np.isfinite(metrics["sharpe"]) and metrics["sharpe"] >= A1_MIN_SHARPE
    a2 = np.isfinite(metrics["annual_pnl"]) and metrics["annual_pnl"] >= A2_MIN_ANNUAL_PNL
    a3 = np.isfinite(metrics["max_dd"]) and metrics["max_dd"] <= A3_MAX_MAXDD
    a4 = metrics["a4_n_positive"] >= A4_MIN_POSITIVE_FOLDS
    a5 = np.isfinite(metrics["a5_stressed_annual_pnl"]) and metrics["a5_stressed_annual_pnl"] > 0
    return {"A0": a0, "A1": a1, "A2": a2, "A3": a3, "A4": a4, "A5": a5}


def assign_verdict(gates: dict, s1: dict | None) -> str:
    a0_pass = gates["A0"]
    a1_pass = gates["A1"]
    a2_pass = gates["A2"]
    a3_pass = gates["A3"]
    a4_pass = gates["A4"]
    a5_pass = gates["A5"]

    # REJECT first
    if not a1_pass or not a2_pass:
        return "REJECT"
    if not a0_pass:
        return "REJECT"

    a0_to_a3 = a0_pass and a1_pass and a2_pass and a3_pass
    a0_to_a5 = a0_to_a3 and a4_pass and a5_pass

    if a0_to_a5:
        # Modulate by S1
        if s1 is None:
            return "ADOPT_CANDIDATE"
        oos_sharpe = s1["oos_sharpe"]
        ratio = s1["oos_is_ratio"]
        s1_strong = (
            np.isfinite(oos_sharpe)
            and oos_sharpe > 0
            and np.isfinite(ratio)
            and ratio >= S1_STRONG_RATIO
        )
        return "ADOPT_CANDIDATE" if s1_strong else "PROMISING_BUT_NEEDS_OOS"

    if a0_to_a3 and (not a4_pass or not a5_pass):
        return "PROMISING_BUT_NEEDS_OOS"

    return "REJECT"


# ---------------------------------------------------------------------------
# Per-pair / per-session diagnostics
# ---------------------------------------------------------------------------


def session_label(ts: pd.Timestamp) -> str:
    h = ts.hour
    if 0 <= h < 6:
        return "Asian (00-06 UTC)"
    if 6 <= h < 12:
        return "European (06-12 UTC)"
    if 12 <= h < 18:
        return "American (12-18 UTC)"
    return "Late (18-24 UTC)"


def per_pair_breakdown(trades_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pair, sub in trades_df.groupby("pair"):
        rows.append(
            {
                "pair": pair,
                "n_trades": int(len(sub)),
                "sharpe": _per_trade_sharpe(sub["pnl_pip"]),
                "annual_pnl": float(sub["pnl_pip"].sum() / SPAN_YEARS),
                "hit_rate": float((sub["pnl_pip"] > 0).mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("sharpe", ascending=False)


def per_session_breakdown(trades_df: pd.DataFrame) -> pd.DataFrame:
    df = trades_df.copy()
    df["session"] = df["entry_ts"].apply(session_label)
    rows = []
    for session, sub in df.groupby("session"):
        rows.append(
            {
                "session": session,
                "n_trades": int(len(sub)),
                "sharpe": _per_trade_sharpe(sub["pnl_pip"]),
                "annual_pnl": float(sub["pnl_pip"].sum() / SPAN_YEARS),
                "hit_rate": float((sub["pnl_pip"] > 0).mean()),
            }
        )
    return pd.DataFrame(rows).sort_values("session")


# ---------------------------------------------------------------------------
# Sweep runner
# ---------------------------------------------------------------------------


def run_sweep(
    pairs: list[str], cells: list[tuple[int, int, str]] | None = None
) -> tuple[list[dict], dict[tuple[int, int, str], pd.DataFrame]]:
    """Build signals + outcomes for each pair, then evaluate every cell."""
    if cells is None:
        cells = [(n, h, e) for n in N_VALUES for h in HORIZONS for e in EXIT_RULES]

    # Per-pair: signals (per N) + labels (per h, slice once)
    per_pair_signals: dict[str, dict[int, pd.DataFrame]] = {}
    per_pair_labels: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        t0 = time.time()
        signals, _ = load_pair_signals_all_n(pair)
        labels = load_pair_labels(pair)
        per_pair_signals[pair] = signals
        per_pair_labels[pair] = labels
        print(
            f"  signals+labels {pair}: long+short trigger counts "
            f"(N={N_VALUES[0]}/{N_VALUES[1]}/{N_VALUES[2]}) "
            f"= "
            + " / ".join(str(len(signals[n])) for n in N_VALUES)
            + f" ({time.time() - t0:5.1f}s)"
        )

    # Per cell: pool 20 pairs
    cell_results: list[dict] = []
    cell_trades: dict[tuple[int, int, str], pd.DataFrame] = {}

    for n, h, exit_rule in cells:
        exit_col = EXIT_COL_MAP[exit_rule]
        pooled_trades_parts: list[pd.DataFrame] = []
        labels_pool_parts: list[pd.DataFrame] = []
        for pair in pairs:
            sig = per_pair_signals[pair][n][["entry_ts", "direction"]].copy()
            sig["pair"] = pair
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
                columns=["entry_ts", "pair", "direction", "tb_pnl", "time_exit_pnl", "pnl_pip"]
            )
        labels_pool = (
            pd.concat(labels_pool_parts, ignore_index=True) if labels_pool_parts else pd.DataFrame()
        )

        # Runtime NG#6 assertion
        if len(trades) > 0 and (trades["signal_timeframe"] != SIGNAL_TIMEFRAME).any():
            raise RuntimeError(
                f"NG#6 violation: cell (N={n}, h={h}, exit={exit_rule}) emitted "
                f"a row with signal_timeframe != {SIGNAL_TIMEFRAME}"
            )

        metrics = evaluate_cell(trades, labels_pool, exit_col)
        gates = gate_matrix(metrics)
        cell_results.append(
            {
                "N": n,
                "horizon_bars": h,
                "exit_rule": exit_rule,
                **metrics,
                **{f"gate_{k}": v for k, v in gates.items()},
            }
        )
        cell_trades[(n, h, exit_rule)] = trades
        gates_bits = "".join("1" if gates[g] else "0" for g in ("A0", "A1", "A2", "A3", "A4", "A5"))
        print(
            f"  cell N={n:>2} h={h} exit={exit_rule:<4} "
            f"n={metrics['n_trades']:>6} ann_tr={metrics['annual_trades']:7.1f} "
            f"sharpe={metrics['sharpe']:+.4f} ann_pnl={metrics['annual_pnl']:+8.1f} "
            f"dd={metrics['max_dd']:7.1f} A4={metrics['a4_n_positive']}/4 "
            f"gates={gates_bits}"
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
    if best is not None:
        best_key = (best["N"], best["horizon_bars"], best["exit_rule"])
        s1 = _strict_oos_split(cell_trades[best_key])
    best_gates = (
        {k.replace("gate_", ""): v for k, v in best.items() if k.startswith("gate_")}
        if best is not None
        else {}
    )
    verdict = assign_verdict(best_gates, s1) if best is not None else "REJECT"

    lines: list[str] = []
    lines.append("# Stage 23.0b — M5 Donchian Breakout + M1 Execution Eval")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase23_0b_m5_donchian_baseline.md`")
    lines.append("")
    lines.append(
        f"Universe: {len(pairs)} pairs, signal TF = `{SIGNAL_TIMEFRAME}`, span = {SPAN_DAYS}d"
    )
    lines.append(
        f"Sweep: N {N_VALUES} × horizon {HORIZONS} × exit {EXIT_RULES} = {len(cell_results)} cells"
    )
    lines.append("")
    lines.append("## Headline verdict")
    lines.append("")
    lines.append(f"**{verdict}**")
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
    lines.append("## Production-readiness")
    lines.append("")
    lines.append(
        "Even an `ADOPT_CANDIDATE` verdict is **not** production-ready. The S1 strict "
        "OOS is computed *after* the in-sample sweep selected the best cell across 18 "
        "cells × 20 pairs (multiple-testing surface). A separate `23.0b-v2` PR with "
        "frozen-cell strict OOS validation on chronologically out-of-sample data and "
        "no parameter re-search is required before any production migration."
    )
    lines.append("")
    lines.append("## Gate thresholds (Phase 22 inherited)")
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
    lines.append("## Sweep summary (all 18 cells)")
    lines.append("")
    lines.append(
        "| N | h | exit | n_trades | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | "
        "A5 stress | A0 | A1 | A2 | A3 | A4 | A5 |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

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
            f"{_gate_glyph(c, 'A3')} | {_gate_glyph(c, 'A4')} | {_gate_glyph(c, 'A5')} |"
        )
    lines.append("")
    lines.append("## Best cell deep-dive")
    lines.append("")
    if best is None:
        lines.append("(no cell passes A0; no deep-dive)")
    else:
        best_key = (best["N"], best["horizon_bars"], best["exit_rule"])
        trades = cell_trades[best_key]
        lines.append(
            f"- N = {best['N']}, horizon = {best['horizon_bars']}, exit = {best['exit_rule']}"
        )
        lines.append(
            f"- n_trades = {best['n_trades']} (long {best['n_long']} / short {best['n_short']})"
        )
        lines.append(
            f"- annual_trades = {best['annual_trades']:.1f}"
            + (
                f" — **OVERTRADING WARNING** (> {A0_OVERTRADING_WARN})"
                if best["overtrading_warning"]
                else ""
            )
        )
        lines.append(f"- Sharpe = {best['sharpe']:+.4f}")
        lines.append(f"- annual_pnl = {best['annual_pnl']:+.1f} pip")
        lines.append(f"- max_dd = {best['max_dd']:.1f} pip")
        lines.append(
            "- A4 fold Sharpes (k=1..4): " + ", ".join(f"{s:+.4f}" for s in best["a4_fold_sharpes"])
        )
        lines.append(f"- A5 stressed annual_pnl = {best['a5_stressed_annual_pnl']:+.1f} pip")
        lines.append("")
        lines.append("### Diagnostics (NOT gates)")
        lines.append("")
        lines.append(f"- hit_rate = {best['hit_rate']:.4f}")
        lines.append(f"- payoff_asymmetry = {best['payoff_asymmetry']:.4f}")
        lines.append(
            f"- S0 random-entry Sharpe = {best['s0_random_entry_sharpe']:+.4f} "
            f"(vs cell Sharpe {best['sharpe']:+.4f}; ratio "
            f"{best['s0_random_entry_sharpe'] / best['sharpe']:+.3f}"
            f" if cell > 0)"
            if np.isfinite(best["sharpe"]) and best["sharpe"] > 0
            else f"- S0 random-entry Sharpe = {best['s0_random_entry_sharpe']:+.4f}"
        )
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
    return {"verdict": verdict, "best": best, "s1": s1}


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

    print(f"=== Stage 23.0b M5 Donchian eval ({len(args.pairs)} pairs) ===")
    cell_results, cell_trades = run_sweep(args.pairs, cells=cells)
    out_path = args.out_dir / "eval_report.md"
    summary = write_report(out_path, cell_results, cell_trades, args.pairs)
    print(f"\nReport: {out_path}")
    print(f"Verdict: {summary['verdict']}")
    if summary["best"]:
        b = summary["best"]
        print(
            f"Best cell: N={b['N']} h={b['horizon_bars']} exit={b['exit_rule']} "
            f"Sharpe={b['sharpe']:+.4f} annual_pnl={b['annual_pnl']:+.1f}"
        )

    # Persist sweep results to JSON sidecar (parquet form is gitignored; this
    # JSON is also gitignored via build_summary.json glob)
    sidecar = args.out_dir / "sweep_results.json"
    sidecar.write_text(json.dumps(cell_results, default=str, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
