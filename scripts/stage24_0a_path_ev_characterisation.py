"""Stage 24.0a — path-EV characterisation + frozen entry stream selection.

Foundational stage for Phase 24. Re-evaluates all 216 Phase 23 cells
(23.0b 18 + 23.0c 36 + 23.0d 18 + 23.0c-rev1 144) on path-EV statistics
using the read-only 23.0a M5/M15 outcome datasets, applies pre-declared
multi-axis ranking + halt criteria, and emits the top-K=3 frozen entry
streams for 24.0b/c/d/e to import.

Score formula (FIXED):
  SCORE = 1.0 * mean(best_possible_pnl)         # axis 1 primary
        + 0.3 * realised_gap                     # axis 2 auxiliary
        - 0.5 * mean(|mae_after_cost|)           # axis 3 risk-path penalty
Tie-breaker: lower mean(|mae_after_cost|).
p75(best_possible_pnl) is diagnostic only — NOT in score.

Eligibility (FIXED, includes H1 path-EV criteria):
  ELIGIBLE = annual_trades >= 70
            AND max_pair_share <= 0.5
            AND min_fold_share >= 0.10
            AND mean(best_possible_pnl) > 0
            AND p75(best_possible_pnl) > 0
            AND positive_rate(best_possible_pnl > 0) >= 0.55

Halt: phase 24 closes early iff zero eligible cells.

K = 3 (top-K cells frozen for downstream stages).

This script touches NO production code, NO DB schema, NO src/ files.
20-pair canonical universe; signal_timeframe ∈ {M5, M15} runtime
assertion carried forward (NG#6).
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
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage24_0a"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")
stage23_0b = importlib.import_module("stage23_0b_m5_donchian_eval")
stage23_0c = importlib.import_module("stage23_0c_m5_zscore_mr_eval")
stage23_0d = importlib.import_module("stage23_0d_m15_donchian_eval")
stage23_0c_rev1 = importlib.import_module("stage23_0c_rev1_signal_quality_eval")

PAIRS_20 = stage23_0a.PAIRS_20
SPAN_DAYS = 730
SPAN_YEARS = SPAN_DAYS / 365.25

# ---- Score formula constants (FIXED, NOT searched) ----
AXIS_1_WEIGHT = 1.0  # mean(best_possible_pnl)
AXIS_2_WEIGHT = 0.3  # realised_gap
AXIS_3_WEIGHT = -0.5  # mean(|mae_after_cost|)
K = 3

# ---- Eligibility constants (FIXED, NOT searched) ----
ANNUAL_TRADES_MIN = 70.0
MAX_PAIR_SHARE = 0.5
MIN_FOLD_SHARE = 0.10
MEAN_BEST_PNL_MIN = 0.0
P75_BEST_PNL_MIN = 0.0
POSITIVE_RATE_MIN = 0.55


# ---------------------------------------------------------------------------
# Phase 23 cell catalogue (216 cells)
# ---------------------------------------------------------------------------


def _build_phase23_cells() -> list[dict]:
    cells: list[dict] = []
    # 23.0b: 18 cells (M5 continuous Donchian)
    for n in (10, 20, 50):
        for h in (1, 2, 3):
            for e in ("tb", "time"):
                cells.append(
                    {
                        "source_stage": "23.0b",
                        "source_pr": 264,
                        "source_merge_commit": "8d58c42",
                        "source_verdict": "REJECT",
                        "reject_reason": "overtrading",
                        "signal_timeframe": "M5",
                        "filter": None,
                        "cell_params": {"N": n, "horizon_bars": h, "exit_rule": e},
                    }
                )
    # 23.0c: 36 cells (M5 first-touch z-MR)
    for n in (12, 24, 48):
        for thr in (2.0, 2.5):
            for h in (1, 2, 3):
                for e in ("tb", "time"):
                    cells.append(
                        {
                            "source_stage": "23.0c",
                            "source_pr": 265,
                            "source_merge_commit": "cc416e6",
                            "source_verdict": "REJECT",
                            "reject_reason": "still_overtrading",
                            "signal_timeframe": "M5",
                            "filter": None,
                            "cell_params": {
                                "N": n,
                                "threshold": thr,
                                "horizon_bars": h,
                                "exit_rule": e,
                            },
                        }
                    )
    # 23.0d: 18 cells (M15 first-touch Donchian)
    for n in (10, 20, 50):
        for h in (1, 2, 4):
            for e in ("tb", "time"):
                cells.append(
                    {
                        "source_stage": "23.0d",
                        "source_pr": 266,
                        "source_merge_commit": "d929867",
                        "source_verdict": "REJECT",
                        "reject_reason": "still_overtrading",
                        "signal_timeframe": "M15",
                        "filter": None,
                        "cell_params": {"N": n, "horizon_bars": h, "exit_rule": e},
                    }
                )
    # 23.0c-rev1: 144 cells (4 filters on M5)
    for f in ("F1_neutral_reset", "F2_cooldown", "F3_reversal_confirmation", "F4_cost_gate"):
        for n in (12, 24, 48):
            for thr in (2.0, 2.5):
                for h in (1, 2, 3):
                    for e in ("tb", "time"):
                        cells.append(
                            {
                                "source_stage": "23.0c-rev1",
                                "source_pr": 267,
                                "source_merge_commit": "b90e03d",
                                "source_verdict": "REJECT",
                                "reject_reason": "still_overtrading",
                                "signal_timeframe": "M5",
                                "filter": f,
                                "cell_params": {
                                    "N": n,
                                    "threshold": thr,
                                    "horizon_bars": h,
                                    "exit_rule": e,
                                },
                            }
                        )
    return cells


PHASE23_CELLS = _build_phase23_cells()
assert len(PHASE23_CELLS) == 216, f"expected 216 cells, got {len(PHASE23_CELLS)}"

SMOKE_PAIRS = ["USD_JPY", "EUR_USD", "GBP_JPY"]


def smoke_cells() -> list[dict]:
    return [c for c in PHASE23_CELLS if c["source_stage"] == "23.0b"][:3]


# ---------------------------------------------------------------------------
# Per-pair preload
# ---------------------------------------------------------------------------


def preload_pair_data(pair: str) -> dict:
    m1 = stage23_0a.load_m1_ba(pair, days=SPAN_DAYS)
    m5 = stage23_0a.aggregate_m1_to_tf(m1, "M5")
    m15 = stage23_0a.aggregate_m1_to_tf(m1, "M15")
    mid_c_m5 = ((m5["bid_c"] + m5["ask_c"]) / 2.0).to_numpy()
    z_per_n_m5 = {n: stage23_0c.compute_zscore(m5, n)[f"z_{n}"].to_numpy() for n in (12, 24, 48)}
    labels_m5 = stage23_0b.load_pair_labels(pair, signal_tf="M5")
    labels_m15 = stage23_0b.load_pair_labels(pair, signal_tf="M15")
    return {
        "m5": m5,
        "m15": m15,
        "mid_c_m5": mid_c_m5,
        "z_per_n_m5": z_per_n_m5,
        "labels_m5": labels_m5,
        "labels_m15": labels_m15,
    }


# ---------------------------------------------------------------------------
# Per-cell signal generation (dispatch by stage / filter)
# ---------------------------------------------------------------------------


def generate_signals_for_cell(pair: str, cell_def: dict, pdata: dict) -> pd.DataFrame:
    stage = cell_def["source_stage"]
    cp = cell_def["cell_params"]
    if stage == "23.0b":
        sig = stage23_0b.extract_signals(pdata["m5"], cp["N"])
    elif stage == "23.0c":
        sig = stage23_0c.extract_signals_first_touch(pdata["m5"], cp["N"], cp["threshold"])
    elif stage == "23.0d":
        sig = stage23_0d.extract_signals_first_touch_donchian(pdata["m15"], cp["N"])
    elif stage == "23.0c-rev1":
        z = pdata["z_per_n_m5"][cp["N"]]
        mid_c = pdata["mid_c_m5"]
        m5_idx = pdata["m5"].index
        f = cell_def["filter"]
        if f == "F1_neutral_reset":
            long_idx, short_idx = stage23_0c_rev1._signals_f1_neutral_reset(
                z, cp["threshold"], stage23_0c_rev1.NEUTRAL_BAND
            )
        elif f == "F2_cooldown":
            ft_long, ft_short = stage23_0c_rev1._signals_first_touch(z, cp["threshold"])
            long_idx, short_idx = stage23_0c_rev1._signals_f2_cooldown(
                ft_long, ft_short, stage23_0c_rev1.COOLDOWN_BARS
            )
        elif f == "F3_reversal_confirmation":
            long_idx, short_idx = stage23_0c_rev1._signals_f3_reversal(
                z, mid_c, cp["threshold"], stage23_0c_rev1.NEUTRAL_BAND
            )
        elif f == "F4_cost_gate":
            long_idx, short_idx = stage23_0c_rev1._signals_first_touch(z, cp["threshold"])
        else:
            raise ValueError(f"Unknown filter: {f}")
        sig = stage23_0c_rev1._make_signal_frame(m5_idx, long_idx, short_idx, pair)
    else:
        raise ValueError(f"Unknown stage: {stage}")
    if "pair" not in sig.columns:
        sig = sig.copy()
        sig["pair"] = pair
    return sig


def join_to_outcomes(sig: pd.DataFrame, cell_def: dict, pdata: dict) -> pd.DataFrame:
    if len(sig) == 0:
        return pd.DataFrame(
            columns=[
                "entry_ts",
                "pair",
                "direction",
                "tb_pnl",
                "time_exit_pnl",
                "best_possible_pnl",
                "mae_after_cost",
                "worst_possible_pnl",
                "cost_ratio",
                "signal_timeframe",
            ]
        )
    cp = cell_def["cell_params"]
    h = cp["horizon_bars"]
    signal_tf = cell_def["signal_timeframe"]
    labels = pdata["labels_m5"] if signal_tf == "M5" else pdata["labels_m15"]
    labels_h = labels[labels["horizon_bars"] == h]
    return pd.merge(
        sig[["entry_ts", "pair", "direction"]],
        labels_h[
            [
                "entry_ts",
                "pair",
                "direction",
                "tb_pnl",
                "time_exit_pnl",
                "best_possible_pnl",
                "mae_after_cost",
                "worst_possible_pnl",
                "cost_ratio",
                "signal_timeframe",
            ]
        ],
        on=["entry_ts", "pair", "direction"],
        how="inner",
    )


# ---------------------------------------------------------------------------
# Metrics, eligibility, score
# ---------------------------------------------------------------------------


def _empty_metrics() -> dict:
    return {
        "n_trades": 0,
        "annual_trades": 0.0,
        "mean_best_possible_pnl": float("nan"),
        "median_best_possible_pnl": float("nan"),
        "p75_best_possible_pnl": float("nan"),
        "positive_rate_best_pnl": float("nan"),
        "realised_gap": float("nan"),
        "mean_abs_mae_after_cost": float("nan"),
        "worst_possible_pnl_p10": float("nan"),
        "max_pair_share": float("nan"),
        "min_fold_share": float("nan"),
    }


def compute_metrics(trades: pd.DataFrame) -> dict:
    if len(trades) == 0:
        return _empty_metrics()
    valid = trades.dropna(subset=["best_possible_pnl"]).copy()
    n = int(len(valid))
    if n == 0:
        return _empty_metrics()
    annual_trades = n / SPAN_YEARS
    mean_best = float(valid["best_possible_pnl"].mean())
    median_best = float(valid["best_possible_pnl"].median())
    p75_best = float(valid["best_possible_pnl"].quantile(0.75))
    positive_rate = float((valid["best_possible_pnl"] > 0).mean())
    realised_per_trade = np.maximum(
        valid["tb_pnl"].astype(np.float64), valid["time_exit_pnl"].astype(np.float64)
    )
    mean_realised = float(np.nanmean(realised_per_trade))
    realised_gap = mean_best - mean_realised
    mean_abs_mae = float(valid["mae_after_cost"].abs().mean())
    worst_p10 = float(valid["worst_possible_pnl"].quantile(0.10))
    pair_counts = valid["pair"].value_counts()
    max_pair_share = float(pair_counts.max() / n) if n > 0 else float("nan")
    fold_sizes: list[int] = []
    for k in range(5):
        lo = int(round(k * n / 5))
        hi = int(round((k + 1) * n / 5))
        fold_sizes.append(hi - lo)
    eval_fold_sizes = fold_sizes[1:]  # drop k=0 warmup
    eval_total = sum(eval_fold_sizes)
    if eval_total > 0:
        fold_shares = [s / eval_total for s in eval_fold_sizes]
        min_fold_share = float(min(fold_shares))
    else:
        min_fold_share = 0.0
    return {
        "n_trades": n,
        "annual_trades": float(annual_trades),
        "mean_best_possible_pnl": mean_best,
        "median_best_possible_pnl": median_best,
        "p75_best_possible_pnl": p75_best,
        "positive_rate_best_pnl": positive_rate,
        "realised_gap": float(realised_gap),
        "mean_abs_mae_after_cost": mean_abs_mae,
        "worst_possible_pnl_p10": worst_p10,
        "max_pair_share": max_pair_share,
        "min_fold_share": min_fold_share,
    }


def is_eligible(m: dict) -> bool:
    return (
        m["annual_trades"] >= ANNUAL_TRADES_MIN
        and np.isfinite(m["max_pair_share"])
        and m["max_pair_share"] <= MAX_PAIR_SHARE
        and np.isfinite(m["min_fold_share"])
        and m["min_fold_share"] >= MIN_FOLD_SHARE
        and np.isfinite(m["mean_best_possible_pnl"])
        and m["mean_best_possible_pnl"] > MEAN_BEST_PNL_MIN
        and np.isfinite(m["p75_best_possible_pnl"])
        and m["p75_best_possible_pnl"] > P75_BEST_PNL_MIN
        and np.isfinite(m["positive_rate_best_pnl"])
        and m["positive_rate_best_pnl"] >= POSITIVE_RATE_MIN
    )


def compute_score(m: dict) -> float:
    if not (
        np.isfinite(m["mean_best_possible_pnl"])
        and np.isfinite(m["realised_gap"])
        and np.isfinite(m["mean_abs_mae_after_cost"])
    ):
        return float("-inf")
    return (
        AXIS_1_WEIGHT * m["mean_best_possible_pnl"]
        + AXIS_2_WEIGHT * m["realised_gap"]
        + AXIS_3_WEIGHT * m["mean_abs_mae_after_cost"]
    )


def select_frozen(cell_results: list[dict]) -> tuple[bool, list[dict]]:
    eligible = [c for c in cell_results if c["eligible"]]
    halt_triggered = len(eligible) == 0
    if halt_triggered:
        return True, []
    sorted_eligible = sorted(
        eligible,
        key=lambda c: (-c["score"], c["metrics"]["mean_abs_mae_after_cost"]),
    )
    return False, sorted_eligible[:K]


# ---------------------------------------------------------------------------
# Sweep runner
# ---------------------------------------------------------------------------


def run_sweep(pairs: list[str], cells: list[dict]) -> list[dict]:
    print(f"--- preloading per-pair data for {len(pairs)} pairs ---")
    pair_data: dict[str, dict] = {}
    for pair in pairs:
        t0 = time.time()
        pair_data[pair] = preload_pair_data(pair)
        print(
            f"  {pair}: m5={len(pair_data[pair]['m5'])} m15={len(pair_data[pair]['m15'])} "
            f"({time.time() - t0:5.1f}s)"
        )

    print(f"--- evaluating {len(cells)} cells ---")
    cell_results: list[dict] = []
    for i, cell in enumerate(cells, 1):
        pooled: list[pd.DataFrame] = []
        for pair in pairs:
            sig = generate_signals_for_cell(pair, cell, pair_data[pair])
            joined = join_to_outcomes(sig, cell, pair_data[pair])
            if cell["filter"] == "F4_cost_gate" and len(joined) > 0:
                joined = joined[joined["cost_ratio"] <= stage23_0c_rev1.COST_GATE_THRESHOLD]
            pooled.append(joined)
        trades = pd.concat(pooled, ignore_index=True) if pooled else pd.DataFrame()
        if len(trades) > 0 and (trades["signal_timeframe"] != cell["signal_timeframe"]).any():
            raise RuntimeError(
                f"NG#6 violation: cell {cell} emitted non-{cell['signal_timeframe']} rows"
            )
        m = compute_metrics(trades)
        eligible = is_eligible(m)
        score = compute_score(m) if eligible else float("-inf")
        cell_results.append({**cell, "metrics": m, "eligible": eligible, "score": score})
        if i % 25 == 0 or i == len(cells):
            cp = cell["cell_params"]
            cp_str = ", ".join(f"{k}={v}" for k, v in cp.items())
            print(
                f"  [{i:3d}/{len(cells)}] {cell['source_stage']:<11} "
                f"f={cell['filter'] or '-':<25} {cp_str} -- "
                f"n={m['n_trades']:>6}, mean_best={m['mean_best_possible_pnl']:+.3f}, "
                f"eligible={eligible}, score={score:+.3f}"
            )
    return cell_results


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _make_frozen_payload(
    cell_results: list[dict], halt_triggered: bool, frozen: list[dict]
) -> dict:
    n_eligible = sum(1 for c in cell_results if c["eligible"])
    return {
        "version": "24.0a-1",
        "generated_at": datetime.now(UTC).isoformat(),
        "halt_triggered": halt_triggered,
        "halt_criteria": {
            "annual_trades_min": ANNUAL_TRADES_MIN,
            "mean_best_pnl_min": MEAN_BEST_PNL_MIN,
            "p75_best_pnl_min": P75_BEST_PNL_MIN,
            "positive_rate_min": POSITIVE_RATE_MIN,
        },
        "eligibility_criteria": {
            "annual_trades_min": ANNUAL_TRADES_MIN,
            "max_pair_share_max": MAX_PAIR_SHARE,
            "min_fold_share_min": MIN_FOLD_SHARE,
            "mean_best_possible_pnl_min": MEAN_BEST_PNL_MIN,
            "p75_best_possible_pnl_min": P75_BEST_PNL_MIN,
            "positive_rate_best_pnl_min": POSITIVE_RATE_MIN,
        },
        "score_formula": {
            "axis_1_weight_mean_best_possible_pnl": AXIS_1_WEIGHT,
            "axis_2_weight_realised_gap": AXIS_2_WEIGHT,
            "axis_3_weight_mean_abs_mae_after_cost": AXIS_3_WEIGHT,
            "tiebreaker": "lower mean |mae_after_cost|",
            "p75_in_score": False,
            "p75_in_diagnostic_only": True,
        },
        "K": K,
        "n_eligible_cells": n_eligible,
        "n_total_cells": len(cell_results),
        "frozen_cells": [
            {
                "rank": i + 1,
                "source_stage": c["source_stage"],
                "source_pr": c["source_pr"],
                "source_merge_commit": c["source_merge_commit"],
                "source_verdict": c["source_verdict"],
                "reject_reason": c["reject_reason"],
                "signal_timeframe": c["signal_timeframe"],
                "filter": c["filter"],
                "cell_params": c["cell_params"],
                "score": c["score"],
                "metrics": c["metrics"],
            }
            for i, c in enumerate(frozen)
        ],
    }


def write_frozen_json(out_path: Path, payload: dict) -> None:
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def write_report(
    out_path: Path,
    cell_results: list[dict],
    halt_triggered: bool,
    frozen: list[dict],
    pairs: list[str],
) -> None:
    n_eligible = sum(1 for c in cell_results if c["eligible"])
    lines: list[str] = []
    lines.append("# Stage 24.0a — Path-EV Characterisation + Frozen Entry Stream Selection")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase24_0a_path_ev_characterisation.md`")
    lines.append("")
    lines.append(
        f"Universe: {len(pairs)} pairs (canonical 20). Span = {SPAN_DAYS}d. "
        f"Cells evaluated: {len(cell_results)} / total Phase 23 cells: 216."
    )
    lines.append("")
    lines.append("## Mandatory caveats")
    lines.append("")
    lines.append(
        "**best_possible_pnl is an ex-post path diagnostic, not an executable PnL. "
        "Frozen entry streams are selected for exit-study eligibility only, not for "
        "production. Path-EV magnitude indicates path-side upside availability that "
        "exit-side improvements may attempt to capture; it does NOT guarantee that any "
        "exit logic will succeed in converting that path-EV into realised PnL.**"
    )
    lines.append("")
    lines.append(
        "**positive_rate(best_possible_pnl > 0) is path-side upside availability rate, "
        "NOT trade win rate.** A trade with `best_possible_pnl > 0` means the price "
        "moved in the favourable direction at some point during the holding window "
        "after entry-side spread; whether the trade closed positive depends on the "
        "exit logic (which is the entire question Phase 24 is investigating)."
    )
    lines.append("")
    lines.append("## Headline verdict")
    lines.append("")
    if halt_triggered:
        lines.append(
            f"**HALT — Phase 24 closes early.** No cell out of {len(cell_results)} satisfies "
            "all 6 eligibility constraints (annual_trades + max_pair_share + min_fold_share + "
            "H1 path-EV criteria). Phase 24's H1 hypothesis (path-EV exists across selected "
            "Phase 23 cells) is REJECTED by this evidence; per kickoff §7 routing, Phase 24 "
            "closes early and a Phase 24 final synthesis (24.0f short form) summarises the "
            "negative-but-bounded conclusion."
        )
    else:
        lines.append(
            f"**OK — {n_eligible} eligible cell(s) out of {len(cell_results)}; top-K={K} "
            f"frozen for 24.0b/c/d/e.**"
        )
    lines.append("")
    lines.append("## Score formula and weights (FIXED in this PR)")
    lines.append("")
    lines.append(f"- Axis 1 (primary, weight {AXIS_1_WEIGHT:+.1f}): `mean(best_possible_pnl)`")
    lines.append(
        f"- Axis 2 (auxiliary, weight {AXIS_2_WEIGHT:+.1f}): "
        "`realised_gap = mean(best_possible_pnl) - mean(max(tb_pnl, time_exit_pnl))`"
    )
    lines.append(
        f"- Axis 3 (risk-path penalty, weight {AXIS_3_WEIGHT:+.1f}): `mean(|mae_after_cost|)`"
    )
    lines.append(f"- K = {K}. Tie-breaker: lower `mean(|mae_after_cost|)`.")
    lines.append("- `p75(best_possible_pnl)` is reported as diagnostic only — NOT in the score.")
    lines.append("")
    lines.append("## Eligibility constraints (FIXED in this PR; H1 path-EV criteria included)")
    lines.append("")
    lines.append(f"- `annual_trades >= {ANNUAL_TRADES_MIN}`")
    lines.append(f"- `max_pair_share <= {MAX_PAIR_SHARE}`")
    lines.append(f"- `min_fold_share >= {MIN_FOLD_SHARE}`")
    lines.append(f"- `mean(best_possible_pnl) > {MEAN_BEST_PNL_MIN}`")
    lines.append(f"- `p75(best_possible_pnl) > {P75_BEST_PNL_MIN}`")
    lines.append(f"- `positive_rate(best_possible_pnl > 0) >= {POSITIVE_RATE_MIN}`")
    lines.append("")

    # eligibility violation breakdown
    violations = {
        "annual_trades_lt_70": 0,
        "max_pair_share_gt_0_5": 0,
        "min_fold_share_lt_0_10": 0,
        "mean_best_le_0": 0,
        "p75_best_le_0": 0,
        "positive_rate_lt_0_55": 0,
    }
    for c in cell_results:
        m = c["metrics"]
        if m["annual_trades"] < ANNUAL_TRADES_MIN:
            violations["annual_trades_lt_70"] += 1
        if not (np.isfinite(m["max_pair_share"]) and m["max_pair_share"] <= MAX_PAIR_SHARE):
            violations["max_pair_share_gt_0_5"] += 1
        if not (np.isfinite(m["min_fold_share"]) and m["min_fold_share"] >= MIN_FOLD_SHARE):
            violations["min_fold_share_lt_0_10"] += 1
        if not (
            np.isfinite(m["mean_best_possible_pnl"])
            and m["mean_best_possible_pnl"] > MEAN_BEST_PNL_MIN
        ):
            violations["mean_best_le_0"] += 1
        if not (
            np.isfinite(m["p75_best_possible_pnl"])
            and m["p75_best_possible_pnl"] > P75_BEST_PNL_MIN
        ):
            violations["p75_best_le_0"] += 1
        if not (
            np.isfinite(m["positive_rate_best_pnl"])
            and m["positive_rate_best_pnl"] >= POSITIVE_RATE_MIN
        ):
            violations["positive_rate_lt_0_55"] += 1
    lines.append("### Eligibility violation breakdown (cells failing each constraint)")
    lines.append("")
    for k, v in violations.items():
        lines.append(f"- `{k}`: {v} / {len(cell_results)} cells")
    lines.append("")

    # Top-K deep-dive
    lines.append("## Top-K frozen entry streams")
    lines.append("")
    if halt_triggered or not frozen:
        lines.append("(No frozen cells — halt triggered or zero eligible.)")
    else:
        lines.append(
            "| rank | source | filter | cell_params | score | mean_best | p75_best | "
            "positive_rate | annual_tr | mae | gap |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for i, c in enumerate(frozen, 1):
            cp = c["cell_params"]
            cp_str = ", ".join(f"{k}={v}" for k, v in cp.items())
            m = c["metrics"]
            lines.append(
                f"| {i} | {c['source_stage']} (PR #{c['source_pr']}, {c['source_merge_commit']}) | "
                f"{c['filter'] or '-'} | {cp_str} | "
                f"{c['score']:+.4f} | {m['mean_best_possible_pnl']:+.3f} | "
                f"{m['p75_best_possible_pnl']:+.3f} | {m['positive_rate_best_pnl']:.4f} | "
                f"{m['annual_trades']:.1f} | {m['mean_abs_mae_after_cost']:.3f} | "
                f"{m['realised_gap']:+.3f} |"
            )
    lines.append("")

    # Per-stage summary
    lines.append("## Per-stage summary")
    lines.append("")
    lines.append("| stage | cells | eligible | best score | median ann_tr | median mean_best |")
    lines.append("|---|---|---|---|---|---|")
    for stage in ("23.0b", "23.0c", "23.0d", "23.0c-rev1"):
        sub = [c for c in cell_results if c["source_stage"] == stage]
        if not sub:
            continue
        n_sub = len(sub)
        n_elig_sub = sum(1 for c in sub if c["eligible"])
        scores = [c["score"] for c in sub if c["eligible"]]
        best = max(scores) if scores else float("-inf")
        ann_tr_arr = np.asarray([c["metrics"]["annual_trades"] for c in sub])
        mean_best_arr = np.asarray(
            [
                c["metrics"]["mean_best_possible_pnl"]
                for c in sub
                if np.isfinite(c["metrics"]["mean_best_possible_pnl"])
            ]
        )
        med_ann = float(np.median(ann_tr_arr))
        med_mb = float(np.median(mean_best_arr)) if len(mean_best_arr) else float("nan")
        best_str = f"{best:+.4f}" if best != float("-inf") else "(none eligible)"
        lines.append(
            f"| {stage} | {n_sub} | {n_elig_sub} | {best_str} | {med_ann:.1f} | {med_mb:+.3f} |"
        )
    lines.append("")

    # Full ranking table
    lines.append("## Full ranking (all cells, sorted by score descending)")
    lines.append("")
    lines.append(
        "| rank | source | filter | cell_params | eligible | score | mean_best | p75_best | "
        "positive_rate | annual_tr | mae | gap |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")

    def _sort_key(c: dict) -> tuple[int, float, float]:
        # eligible cells first (sort by score desc); non-eligible sorted by mean_best desc
        if c["eligible"]:
            return (0, -c["score"], c["metrics"]["mean_abs_mae_after_cost"])
        m_val = c["metrics"]["mean_best_possible_pnl"]
        if not np.isfinite(m_val):
            m_val = -1e18
        return (1, -m_val, 0.0)

    for rank, c in enumerate(sorted(cell_results, key=_sort_key), 1):
        cp = c["cell_params"]
        cp_str = ", ".join(f"{k}={v}" for k, v in cp.items())
        m = c["metrics"]
        score_str = f"{c['score']:+.4f}" if np.isfinite(c["score"]) else "-inf"
        mb_str = (
            f"{m['mean_best_possible_pnl']:+.3f}"
            if np.isfinite(m["mean_best_possible_pnl"])
            else "nan"
        )
        p75_str = (
            f"{m['p75_best_possible_pnl']:+.3f}"
            if np.isfinite(m["p75_best_possible_pnl"])
            else "nan"
        )
        pr_str = (
            f"{m['positive_rate_best_pnl']:.4f}"
            if np.isfinite(m["positive_rate_best_pnl"])
            else "nan"
        )
        mae_str = (
            f"{m['mean_abs_mae_after_cost']:.3f}"
            if np.isfinite(m["mean_abs_mae_after_cost"])
            else "nan"
        )
        gap_str = f"{m['realised_gap']:+.3f}" if np.isfinite(m["realised_gap"]) else "nan"
        lines.append(
            f"| {rank} | {c['source_stage']} | {c['filter'] or '-'} | {cp_str} | "
            f"{'✓' if c['eligible'] else '✗'} | {score_str} | {mb_str} | {p75_str} | "
            f"{pr_str} | {m['annual_trades']:.1f} | {mae_str} | {gap_str} |"
        )
    lines.append("")

    # Phase 24 forward routing
    lines.append("## Phase 24 forward routing")
    lines.append("")
    if halt_triggered:
        lines.append(
            "Phase 24 closes early. The negative-but-bounded conclusion: the 216 Phase 23 "
            "cells, when re-evaluated for path-EV under the multi-axis eligibility, do NOT "
            "include any cell with non-trivial positive path-EV. Per kickoff §1 scope clause, "
            "this does NOT generalise to model-based entries, longer timeframes, or different "
            "cost regimes — it concludes that the 4 rule-based signal families tested in "
            "Phase 23 do not produce path-EV-positive entry streams under the 6 eligibility "
            "constraints fixed here."
        )
    else:
        lines.append(
            f"24.0b (trailing-stop variants), 24.0c (partial-exit variants), and 24.0d "
            f"(regime-conditional exits — exit-parameter selection only, NOT entry filter) "
            f"will import `frozen_entry_streams.json` and use the top-{K} cells as their "
            f"frozen entry streams. The score formula and K are sealed by this 24.0a PR's "
            f"commit hash; downstream stages must NOT override or re-search them."
        )
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


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
        help="Smoke run: 3 pairs (USD_JPY/EUR_USD/GBP_JPY) × 3 cells from 23.0b only.",
    )
    args = parser.parse_args(argv)

    if args.smoke:
        args.pairs = SMOKE_PAIRS
        cells = smoke_cells()
    else:
        cells = PHASE23_CELLS

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 24.0a path-EV characterisation ({len(args.pairs)} pairs) ===")
    print(f"Score: AXIS_1={AXIS_1_WEIGHT}, AXIS_2={AXIS_2_WEIGHT}, AXIS_3={AXIS_3_WEIGHT}, K={K}")
    print(
        f"Eligibility: ann_tr>={ANNUAL_TRADES_MIN}, max_pair<={MAX_PAIR_SHARE}, "
        f"min_fold>={MIN_FOLD_SHARE}, mean_best>{MEAN_BEST_PNL_MIN}, p75>{P75_BEST_PNL_MIN}, "
        f"positive_rate>={POSITIVE_RATE_MIN}"
    )
    cell_results = run_sweep(args.pairs, cells)
    halt_triggered, frozen = select_frozen(cell_results)

    payload = _make_frozen_payload(cell_results, halt_triggered, frozen)
    json_path = args.out_dir / "frozen_entry_streams.json"
    write_frozen_json(json_path, payload)
    print(f"\nFrozen JSON: {json_path}")
    print(f"Halt triggered: {halt_triggered}")
    print(f"Eligible cells: {payload['n_eligible_cells']} / {payload['n_total_cells']}")
    if frozen:
        print(f"Top-{K} frozen cells:")
        for i, c in enumerate(frozen, 1):
            cp = c["cell_params"]
            cp_str = ", ".join(f"{k}={v}" for k, v in cp.items())
            print(
                f"  [{i}] {c['source_stage']} f={c['filter'] or '-'} {cp_str} -> "
                f"score {c['score']:+.4f} (mean_best {c['metrics']['mean_best_possible_pnl']:+.3f})"
            )

    report_path = args.out_dir / "path_ev_characterisation_report.md"
    write_report(report_path, cell_results, halt_triggered, frozen, args.pairs)
    print(f"Report: {report_path}")

    # Sidecar for downstream auditing (gitignored)
    sidecar = args.out_dir / "path_ev_distribution.parquet"
    pd.DataFrame(
        [
            {
                "source_stage": c["source_stage"],
                "filter": c["filter"],
                **c["cell_params"],
                "eligible": c["eligible"],
                "score": c["score"],
                **c["metrics"],
            }
            for c in cell_results
        ]
    ).to_parquet(sidecar, compression="snappy")
    print(f"Sidecar: {sidecar}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
