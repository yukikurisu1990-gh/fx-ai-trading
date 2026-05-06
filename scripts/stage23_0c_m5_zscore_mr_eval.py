"""Stage 23.0c — M5 z-score MR + M1 execution alternative baseline eval.

Rule-based mean-reversion on the M5 signal timeframe; PnL via M1
execution recorded in 23.0a's ``labels_M5_<pair>.parquet``.

Trigger semantics: **first-touch only** with same-direction re-entry
lock. A long signal fires when ``z[t] < -threshold`` AND
``z[t-1] >= -threshold`` (rising-edge into the negative-extreme zone);
no further long signal fires while ``z`` stays below ``-threshold``.
Long-side and short-side locks are independent.

Continuous-trigger MR is intentionally NOT used here. 23.0b showed that
continuous-trigger Donchian breakout overtrades; Phase 23 is therefore
committed to first-touch by design at the rule-based stage. Continuous
variants are deferred to follow-up diagnostics or 23.0e meta-labeling.

Sweep:
- N (rolling window, M5 bars): {12, 24, 48} = 1h / 2h / 4h
- threshold (absolute z): {2.0, 2.5}
- horizon_bars: {1, 2, 3}
- exit_rule: {tb (= tb_pnl), time (= time_exit_pnl)}
= 36 cells.

Gates (Phase 22 inherited, exact thresholds — same as 23.0b):
- A0 annual_trades >= 70  (overtrading WARN > 1000, NOT blocking)
- A1 per-trade Sharpe (ddof=0, no √N) >= +0.082
- A2 annual_pnl_pip >= +180
- A3 max_dd_pip <= 200
- A4 5-fold split, k=0 dropped, eval k=1..4, count(>0) >= 3
- A5 annual_pnl after subtracting 0.5 pip per round trip > 0

Diagnostics (NOT gates):
- hit_rate, payoff_asymmetry, per-pair / per-session contribution
- z_at_entry distribution (p10/p25/p50/p75/p90 of |z| at signal bars)
- time_to_revert_to_mean (best-cell only; forward-path M1 bars until
  mid path first returns to mu_N at signal close; capped at horizon).
  Forward-path diagnostic-only — must NOT be used in features or ADOPT.
- S0 random-entry sanity, S1 strict 80/20 OOS — diagnostic-only

Verdict (3-class):
- ADOPT_CANDIDATE: A0..A5 all pass AND S1 strong
- PROMISING_BUT_NEEDS_OOS: A0..A3 pass but A4 OR A5 fails;
                           OR A0..A5 all pass but S1 weak
- REJECT: A1 OR A2 fails; OR A0 fails

REJECT reason classification:
- under_firing: annual_trades < 70
- still_overtrading: annual_trades > 1000 AND (A1 fail OR A2 fail)
- pnl_edge_insufficient: trade volume in tractable range, A1 OR A2 fails
- robustness_failure: A1+A2 pass, but A3 OR A4 OR A5 fails

Production-readiness: even ADOPT_CANDIDATE requires a separate 23.0c-v2
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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage23_0c"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage23_0b = importlib.import_module("stage23_0b_m5_donchian_eval")

PAIRS_20 = stage23_0a.PAIRS_20
SIGNAL_TIMEFRAME = "M5"

TRIGGER_MODE = "first_touch"  # 23.0c default; continuous-trigger NOT used (see design §2.2)

N_VALUES: tuple[int, ...] = (12, 24, 48)
THRESHOLDS: tuple[float, ...] = (2.0, 2.5)
HORIZONS: tuple[int, ...] = (1, 2, 3)
EXIT_RULES: tuple[str, ...] = ("tb", "time")
EXIT_COL_MAP = {"tb": "tb_pnl", "time": "time_exit_pnl"}

SPAN_DAYS = 730
SPAN_YEARS = SPAN_DAYS / 365.25

# Inherited gate thresholds (same as 23.0b)
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

# Helpers reused from 23.0b
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

SMOKE_PAIRS = ["USD_JPY", "EUR_USD", "GBP_JPY"]
SMOKE_CELLS: tuple[tuple[int, float, int, str], ...] = (
    (24, 2.0, 1, "tb"),
    (24, 2.0, 2, "time"),
)


# ---------------------------------------------------------------------------
# Signal generation — causal z-score + first-touch trigger
# ---------------------------------------------------------------------------


def compute_zscore(m5_df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Return a copy of m5_df with mid_c, mu_N, sigma_N, z columns (causal)."""
    out = m5_df.copy()
    out["mid_c"] = (out["bid_c"] + out["ask_c"]) / 2.0
    shifted = out["mid_c"].shift(1)
    out[f"mu_{n}"] = shifted.rolling(n).mean()
    out[f"sigma_{n}"] = shifted.rolling(n).std(ddof=0)
    sigma = out[f"sigma_{n}"]
    valid_sigma = sigma > 0
    out[f"z_{n}"] = np.where(
        valid_sigma,
        (out["mid_c"] - out[f"mu_{n}"]) / sigma.where(valid_sigma, np.nan),
        np.nan,
    )
    return out


def extract_signals_first_touch(m5_df: pd.DataFrame, n: int, threshold: float) -> pd.DataFrame:
    """Emit first-touch z-score MR signals.

    Long: z[t] < -threshold AND z[t-1] >= -threshold  (rising-edge into negative extreme)
    Short: z[t] > +threshold AND z[t-1] <= +threshold  (rising-edge into positive extreme)

    No further same-direction signal fires until z returns inside the band.
    """
    df = compute_zscore(m5_df, n)
    z = df[f"z_{n}"]
    z_prev = z.shift(1)
    long_first = (z < -threshold) & (z_prev >= -threshold) & z.notna() & z_prev.notna()
    short_first = (z > threshold) & (z_prev <= threshold) & z.notna() & z_prev.notna()

    sig_long_idx = df.index[long_first]
    sig_short_idx = df.index[short_first]
    out = pd.DataFrame(
        {
            "entry_ts": list(sig_long_idx) + list(sig_short_idx),
            "direction": ["long"] * len(sig_long_idx) + ["short"] * len(sig_short_idx),
            "z_at_entry": list(z.loc[sig_long_idx].to_numpy())
            + list(z.loc[sig_short_idx].to_numpy()),
            "mu_at_entry": list(df[f"mu_{n}"].loc[sig_long_idx].to_numpy())
            + list(df[f"mu_{n}"].loc[sig_short_idx].to_numpy()),
            "sigma_at_entry": list(df[f"sigma_{n}"].loc[sig_long_idx].to_numpy())
            + list(df[f"sigma_{n}"].loc[sig_short_idx].to_numpy()),
        }
    )
    return out


def load_pair_signals_all_cells(
    pair: str, days: int = SPAN_DAYS
) -> tuple[dict[tuple[int, float], pd.DataFrame], pd.DataFrame]:
    """Build M5 OHLC + first-touch signals for all (N, threshold) combinations.

    Returns: ({(n, threshold): signals_df}, m5_df).
    """
    m1 = stage23_0a.load_m1_ba(pair, days=days)
    m5 = stage23_0a.aggregate_m1_to_tf(m1, SIGNAL_TIMEFRAME)
    out: dict[tuple[int, float], pd.DataFrame] = {}
    for n in N_VALUES:
        for threshold in THRESHOLDS:
            out[(n, threshold)] = extract_signals_first_touch(m5, n, threshold)
    return out, m5


def load_pair_labels(pair: str, signal_tf: str = SIGNAL_TIMEFRAME) -> pd.DataFrame:
    """Reuse 23.0b's loader (with NG#6 runtime assertion)."""
    return stage23_0b.load_pair_labels(pair, signal_tf=signal_tf)


# ---------------------------------------------------------------------------
# REJECT-reason classification (new in 23.0c)
# ---------------------------------------------------------------------------


def classify_reject_reason(metrics: dict, gates: dict) -> str | None:
    """Attach a reason to a REJECT verdict; returns None for non-REJECT cells."""
    if not gates["A0"]:
        return "under_firing"
    if metrics.get("overtrading_warning", False) and (not gates["A1"] or not gates["A2"]):
        return "still_overtrading"
    if not gates["A1"] or not gates["A2"]:
        return "pnl_edge_insufficient"
    if not gates["A3"] or not gates["A4"] or not gates["A5"]:
        return "robustness_failure"
    return None


# ---------------------------------------------------------------------------
# MR-specific cell evaluation (extends 23.0b's evaluate_cell with z stats)
# ---------------------------------------------------------------------------


def evaluate_mr_cell(
    trades_df: pd.DataFrame,
    labels_pool_for_s0: pd.DataFrame,
    exit_col: str,
) -> dict:
    metrics = stage23_0b.evaluate_cell(trades_df, labels_pool_for_s0, exit_col)
    if len(trades_df) > 0 and "z_at_entry" in trades_df.columns:
        z_abs = trades_df["z_at_entry"].abs()
        z_abs = z_abs[np.isfinite(z_abs)]
        if len(z_abs) > 0:
            metrics["z_abs_p10"] = float(z_abs.quantile(0.10))
            metrics["z_abs_p25"] = float(z_abs.quantile(0.25))
            metrics["z_abs_p50"] = float(z_abs.quantile(0.50))
            metrics["z_abs_p75"] = float(z_abs.quantile(0.75))
            metrics["z_abs_p90"] = float(z_abs.quantile(0.90))
        else:
            for k in ("z_abs_p10", "z_abs_p25", "z_abs_p50", "z_abs_p75", "z_abs_p90"):
                metrics[k] = float("nan")
    else:
        for k in ("z_abs_p10", "z_abs_p25", "z_abs_p50", "z_abs_p75", "z_abs_p90"):
            metrics[k] = float("nan")
    return metrics


# ---------------------------------------------------------------------------
# time_to_revert_to_mean — best-cell only post-sweep
# ---------------------------------------------------------------------------


def compute_time_to_revert_for_best_cell(
    trades_df: pd.DataFrame,
) -> dict:
    """Forward-path diagnostic: M1 bars until mid path first returns to mu_at_entry.

    Diagnostic only — must not feed back into ADOPT or features.
    """
    if len(trades_df) == 0:
        return {
            "n_trades": 0,
            "n_reverted": 0,
            "reverted_fraction": float("nan"),
            "p25_m1": float("nan"),
            "p50_m1": float("nan"),
            "p75_m1": float("nan"),
        }
    times: list[float] = []
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
            mu_at_entry = row.get("mu_at_entry", np.nan)
            horizon_m1_bars = int(row["horizon_bars"]) * 5  # M5 -> M1
            if not np.isfinite(mu_at_entry):
                times.append(np.nan)
                continue
            target_entry_m1_ts = entry_ts + pd.Timedelta(minutes=1)
            if target_entry_m1_ts not in m1_pos_lookup.index:
                times.append(np.nan)
                continue
            entry_m1_pos = int(m1_pos_lookup.loc[target_entry_m1_ts])
            path_end = entry_m1_pos + horizon_m1_bars
            if path_end > n_m1:
                times.append(np.nan)
                continue
            path = mid_c_m1[entry_m1_pos:path_end]
            if direction == "long":
                # Long entry was triggered at z < -threshold (price below mean);
                # "revert to mean" = mid path crosses up to >= mu_at_entry.
                crossings = np.where(path >= mu_at_entry)[0]
            else:
                crossings = np.where(path <= mu_at_entry)[0]
            if len(crossings) > 0:
                times.append(float(crossings[0] + 1))  # 1-indexed M1 bars
            else:
                times.append(np.nan)
    times_arr = np.asarray(times, dtype=np.float64)
    finite = times_arr[np.isfinite(times_arr)]
    n_total = int((~np.isnan(times_arr)).sum() + np.isnan(times_arr).sum())
    return {
        "n_trades": int(n_total),
        "n_reverted": int(len(finite)),
        "reverted_fraction": float(len(finite) / n_total) if n_total > 0 else float("nan"),
        "p25_m1": float(np.percentile(finite, 25)) if len(finite) > 0 else float("nan"),
        "p50_m1": float(np.percentile(finite, 50)) if len(finite) > 0 else float("nan"),
        "p75_m1": float(np.percentile(finite, 75)) if len(finite) > 0 else float("nan"),
    }


# ---------------------------------------------------------------------------
# Sweep runner
# ---------------------------------------------------------------------------


def run_sweep(
    pairs: list[str], cells: list[tuple[int, float, int, str]] | None = None
) -> tuple[list[dict], dict[tuple[int, float, int, str], pd.DataFrame]]:
    """Build signals + outcomes for each pair, then evaluate every cell."""
    if cells is None:
        cells = [
            (n, threshold, h, e)
            for n in N_VALUES
            for threshold in THRESHOLDS
            for h in HORIZONS
            for e in EXIT_RULES
        ]

    per_pair_signals: dict[str, dict[tuple[int, float], pd.DataFrame]] = {}
    per_pair_labels: dict[str, pd.DataFrame] = {}
    for pair in pairs:
        t0 = time.time()
        signals, _ = load_pair_signals_all_cells(pair)
        labels = load_pair_labels(pair)
        per_pair_signals[pair] = signals
        per_pair_labels[pair] = labels
        sample_counts = " / ".join(
            f"N={n},t={threshold}:{len(signals[(n, threshold)])}"
            for n, threshold in [(N_VALUES[0], THRESHOLDS[0]), (N_VALUES[-1], THRESHOLDS[-1])]
        )
        print(f"  signals+labels {pair}: {sample_counts}  ({time.time() - t0:5.1f}s)")

    cell_results: list[dict] = []
    cell_trades: dict[tuple[int, float, int, str], pd.DataFrame] = {}

    for n, threshold, h, exit_rule in cells:
        exit_col = EXIT_COL_MAP[exit_rule]
        pooled_trades_parts: list[pd.DataFrame] = []
        labels_pool_parts: list[pd.DataFrame] = []
        for pair in pairs:
            sig = per_pair_signals[pair][(n, threshold)].copy()
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
                columns=[
                    "entry_ts",
                    "pair",
                    "direction",
                    "tb_pnl",
                    "time_exit_pnl",
                    "pnl_pip",
                    "z_at_entry",
                    "mu_at_entry",
                ]
            )
        labels_pool = (
            pd.concat(labels_pool_parts, ignore_index=True) if labels_pool_parts else pd.DataFrame()
        )

        # NG#6 runtime assertion
        if len(trades) > 0 and (trades["signal_timeframe"] != SIGNAL_TIMEFRAME).any():
            raise RuntimeError(
                f"NG#6 violation: cell (N={n}, threshold={threshold}, h={h}, exit={exit_rule}) "
                f"emitted a row with signal_timeframe != {SIGNAL_TIMEFRAME}"
            )

        metrics = evaluate_mr_cell(trades, labels_pool, exit_col)
        gates = gate_matrix(metrics)
        reject_reason = classify_reject_reason(metrics, gates)
        cell_results.append(
            {
                "N": n,
                "threshold": threshold,
                "horizon_bars": h,
                "exit_rule": exit_rule,
                "reject_reason": reject_reason,
                **metrics,
                **{f"gate_{k}": v for k, v in gates.items()},
            }
        )
        cell_trades[(n, threshold, h, exit_rule)] = trades
        gates_bits = "".join("1" if gates[g] else "0" for g in ("A0", "A1", "A2", "A3", "A4", "A5"))
        print(
            f"  cell N={n:>2} thr={threshold:.1f} h={h} exit={exit_rule:<4} "
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
    cell_trades: dict[tuple[int, float, int, str], pd.DataFrame],
    pairs: list[str],
) -> dict:
    best = select_best_cell(cell_results)
    s1 = None
    revert_stats: dict | None = None
    if best is not None:
        best_key = (best["N"], best["threshold"], best["horizon_bars"], best["exit_rule"])
        s1 = _strict_oos_split(cell_trades[best_key])
        revert_stats = compute_time_to_revert_for_best_cell(cell_trades[best_key])
    best_gates = (
        {k.replace("gate_", ""): v for k, v in best.items() if k.startswith("gate_")}
        if best is not None
        else {}
    )
    verdict = assign_verdict(best_gates, s1) if best is not None else "REJECT"

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
    n_overtrading = sum(1 for c in cell_results if c["overtrading_warning"])

    lines: list[str] = []
    lines.append("# Stage 23.0c — M5 z-score MR + M1 Execution Eval")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase23_0c_m5_zscore_mr_baseline.md`")
    lines.append("")
    lines.append(
        f"Universe: {len(pairs)} pairs, signal TF = `{SIGNAL_TIMEFRAME}`, span = {SPAN_DAYS}d, "
        f"trigger mode = `{TRIGGER_MODE}`"
    )
    lines.append(
        f"Sweep: N {N_VALUES} × threshold {THRESHOLDS} × horizon {HORIZONS} × exit {EXIT_RULES} "
        f"= {len(cell_results)} cells"
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
            f"Best cell: `N={best['N']}, threshold={best['threshold']}, "
            f"horizon={best['horizon_bars']}, exit={best['exit_rule']}` "
            f"(Sharpe {best['sharpe']:+.4f}, annual_pnl {best['annual_pnl']:+.1f} pip, "
            f"n_trades {best['n_trades']})"
        )
    else:
        lines.append("No cell passed A0 (annual_trades >= 70).")
    lines.append("")
    lines.append("## Did first-touch fix overtrading?")
    lines.append("")
    ann_trades_list = [c["annual_trades"] for c in cell_results]
    ann_trades_min = min(ann_trades_list) if ann_trades_list else float("nan")
    ann_trades_max = max(ann_trades_list) if ann_trades_list else float("nan")
    ann_trades_med = float(np.median(ann_trades_list)) if ann_trades_list else float("nan")
    lines.append(
        f"- 23.0c annual_trades distribution across {len(cell_results)} cells: "
        f"min {ann_trades_min:.1f} / median {ann_trades_med:.1f} / max {ann_trades_max:.1f}"
    )
    lines.append(
        f"- Cells triggering overtrading warning (`> {int(A0_OVERTRADING_WARN)}`): "
        f"{n_overtrading} / {len(cell_results)}"
    )
    lines.append(
        "- 23.0b reference (continuous-trigger Donchian): annual_trades 105,275 – 249,507 "
        "across 18 cells; ALL 18 triggered the overtrading warning."
    )
    if n_overtrading == 0:
        lines.append("- **First-touch eliminated overtrading at the cell-aggregate level.**")
    elif n_overtrading < len(cell_results):
        lines.append(
            f"- First-touch reduced overtrading: {n_overtrading} / {len(cell_results)} cells "
            f"still trigger the warning (vs 18/18 in 23.0b)."
        )
    else:
        lines.append("- First-touch did **not** eliminate overtrading; all cells still warn.")
    lines.append("")
    lines.append("## Production-readiness")
    lines.append("")
    lines.append(
        "Even an `ADOPT_CANDIDATE` verdict is **not** production-ready. The S1 strict OOS "
        "is computed *after* the in-sample sweep selected the best cell from "
        f"{len(cell_results)} cells × {len(pairs)} pairs (multiple-testing surface). "
        "A separate `23.0c-v2` PR with frozen-cell strict OOS validation on chronologically "
        "out-of-sample data and no parameter re-search is required before any production "
        "migration."
    )
    lines.append("")
    lines.append("## Trigger semantics")
    lines.append("")
    lines.append(
        f"- Trigger mode: `{TRIGGER_MODE}` (rising-edge into the extreme zone). "
        "Long: `z[t] < -threshold AND z[t-1] >= -threshold`. Short: mirrored."
    )
    lines.append(
        "- Same-direction re-entry is locked while `z` stays outside the band. "
        "Long-side and short-side locks are independent."
    )
    lines.append(
        "- **Continuous trigger is not the Phase 23 default because 23.0b showed "
        "continuous-trigger overtrading. A continuous variant may be reintroduced only as "
        "a diagnostic follow-up, not as the main baseline.**"
    )
    lines.append("")
    lines.append("## Gate thresholds (Phase 22 inherited, identical to 23.0b)")
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
        "| N | thr | h | exit | n_trades | ann_tr | Sharpe | ann_pnl | max_dd | A4 pos | "
        "A5 stress | A0 | A1 | A2 | A3 | A4 | A5 | reject_reason |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")

    def _gate_glyph(cell: dict, name: str) -> str:
        return "✓" if cell[f"gate_{name}"] else "✗"

    for c in sorted(
        cell_results,
        key=lambda x: x["sharpe"] if np.isfinite(x["sharpe"]) else -1e9,
        reverse=True,
    ):
        lines.append(
            f"| {c['N']} | {c['threshold']:.1f} | {c['horizon_bars']} | {c['exit_rule']} | "
            f"{c['n_trades']} | {c['annual_trades']:.1f} | "
            f"{c['sharpe']:+.4f} | {c['annual_pnl']:+.1f} | {c['max_dd']:.1f} | "
            f"{c['a4_n_positive']}/4 | {c['a5_stressed_annual_pnl']:+.1f} | "
            f"{_gate_glyph(c, 'A0')} | {_gate_glyph(c, 'A1')} | {_gate_glyph(c, 'A2')} | "
            f"{_gate_glyph(c, 'A3')} | {_gate_glyph(c, 'A4')} | {_gate_glyph(c, 'A5')} | "
            f"{c.get('reject_reason') or '-'} |"
        )
    lines.append("")
    lines.append("## Best cell deep-dive")
    lines.append("")
    if best is None:
        lines.append("(no cell passes A0; no deep-dive)")
    else:
        best_key = (best["N"], best["threshold"], best["horizon_bars"], best["exit_rule"])
        trades = cell_trades[best_key]
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
        lines.append("")
        lines.append("### z_at_entry distribution (|z| at signal bars)")
        lines.append("")
        lines.append(
            f"- p10 = {best.get('z_abs_p10', float('nan')):.3f}, "
            f"p25 = {best.get('z_abs_p25', float('nan')):.3f}, "
            f"p50 = {best.get('z_abs_p50', float('nan')):.3f}, "
            f"p75 = {best.get('z_abs_p75', float('nan')):.3f}, "
            f"p90 = {best.get('z_abs_p90', float('nan')):.3f}"
        )
        lines.append("")
        if revert_stats is not None:
            lines.append("### time_to_revert_to_mean (forward-path, diagnostic only)")
            lines.append("")
            lines.append(
                f"- Reverted within horizon: "
                f"{revert_stats['n_reverted']} / {revert_stats['n_trades']} trades "
                f"({revert_stats['reverted_fraction'] * 100:.2f}%)"
                if np.isfinite(revert_stats["reverted_fraction"])
                else "- Reverted: data unavailable"
            )
            lines.append(
                f"- M1 bars to revert (among reverted): "
                f"p25 {revert_stats['p25_m1']:.1f} / p50 {revert_stats['p50_m1']:.1f} / "
                f"p75 {revert_stats['p75_m1']:.1f}"
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
    return {"verdict": verdict, "best": best, "s1": s1, "revert_stats": revert_stats}


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

    print(f"=== Stage 23.0c M5 z-score MR eval ({len(args.pairs)} pairs) ===")
    print(f"Trigger mode: {TRIGGER_MODE}")
    cell_results, cell_trades = run_sweep(args.pairs, cells=cells)
    out_path = args.out_dir / "eval_report.md"
    summary = write_report(out_path, cell_results, cell_trades, args.pairs)
    print(f"\nReport: {out_path}")
    print(f"Verdict: {summary['verdict']}")
    if summary["best"]:
        b = summary["best"]
        print(
            f"Best cell: N={b['N']} thr={b['threshold']} h={b['horizon_bars']} "
            f"exit={b['exit_rule']} Sharpe={b['sharpe']:+.4f} ann_pnl={b['annual_pnl']:+.1f}"
        )

    sidecar = args.out_dir / "sweep_results.json"
    sidecar.write_text(json.dumps(cell_results, default=str, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
