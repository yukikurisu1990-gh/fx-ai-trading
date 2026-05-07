"""Stage 25.0a-β — Path-quality binary label dataset (Phase 25 implementation).

Implements the binding contract from PR #281 (25.0a-α
docs/design/phase25_0a_label_design.md). Builds path_quality_dataset.parquet
on the canonical 20-pair × 730d M1 BA data. NO feature-class signal
generation — that is deferred to 25.0b+.

MANDATORY CLAUSES (verbatim per 25.0a-α §15):

1. Design constants are fixed.
   The numerical thresholds K_FAV, K_ADV, M_MARGIN, H_M1_BARS were
   fixed in 25.0a-α before implementation and MUST NOT be retuned in
   response to observed label balance. If the dataset is pathological
   per §12, the implementation halts and the user decides next steps.

2. Causality.
   Labels are computed from FUTURE bars [t+1, t+H_M1_BARS] only;
   features and ATR are computed from PAST bars only. The boundary at
   signal time t is hard. Same-bar SL-first invariant per PR #276
   envelope §3.3.

3. Diagnostic columns are not features.
   The columns max_fav_excursion_pip, max_adv_excursion_pip,
   time_to_fav_bar, time_to_adv_bar, same_bar_both_hit are label-side
   diagnostic outputs computed from the same future bars as the label.
   Downstream feature-class evals (25.0b+) MUST NOT use them as model
   input features — doing so constitutes feature leakage.

4. γ closure preservation.
   Phase 25.0a does not modify the γ closure declared in PR #279.
   Phase 25 results, regardless of outcome, do not change Phase 24 /
   NG#10 β-chain closure status.

This script touches NO production code, NO DB schema, NO src/ files.
20-pair canonical universe; signal cadence = M5 bar boundaries.
"""

from __future__ import annotations

import argparse
import importlib
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
ARTIFACT_ROOT = REPO_ROOT / "artifacts" / "stage25_0a"
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

stage23_0a = importlib.import_module("stage23_0a_build_outcome_dataset")

PAIRS_20 = stage23_0a.PAIRS_20
load_m1_ba = stage23_0a.load_m1_ba
aggregate_m1_to_tf = stage23_0a.aggregate_m1_to_tf
pip_size_for = stage23_0a.pip_size_for
atr_causal = stage23_0a.atr_causal


# ---------------------------------------------------------------------------
# Design constants (FIXED per 25.0a-α §3 — MUST NOT be retuned)
# ---------------------------------------------------------------------------

K_FAV = 1.5
K_ADV = 1.0
M_MARGIN = 2.0
H_M1_BARS = 60
ATR_N = 20
SIGNAL_TF = "M5"
SPAN_DAYS = 730

SMOKE_PAIRS = ["USD_JPY", "EUR_USD", "GBP_JPY"]

# Pathological balance thresholds (25.0a-α §12)
PATHOLOGICAL_OVERALL_LOW = 0.05
PATHOLOGICAL_OVERALL_HIGH = 0.60
PATHOLOGICAL_PER_PAIR_LOW = 0.02
PATHOLOGICAL_DROPPED_BY_MARGIN_HIGH = 0.80


# ---------------------------------------------------------------------------
# Label computation (vectorized inner per signal candidate)
# ---------------------------------------------------------------------------


def _resolve_label_from_first_hits(first_fav: int, first_adv: int) -> tuple[int, bool]:
    """Resolve binary label given earliest-hit indices.

    Returns (label, same_bar_both_hit). Same-bar SL-first invariant:
    if both hit at the same bar, label is NEGATIVE (per PR #276 §3.3).
    Cross-bar: chronological order wins.
    """
    if first_fav >= 0 and first_adv >= 0:
        if first_fav == first_adv:
            return 0, True  # same-bar SL-first NEGATIVE
        if first_adv < first_fav:
            return 0, False  # adv came first → NEGATIVE
        return 1, False  # fav came first → POSITIVE
    if first_adv >= 0:
        return 0, False  # only adv hit → NEGATIVE
    if first_fav >= 0:
        return 1, False  # only fav hit → POSITIVE
    return 0, False  # neither hit (horizon expiry) → NEGATIVE


def _compute_label_long(
    bid_h: np.ndarray,
    bid_l: np.ndarray,
    entry_ask: float,
    fav_thresh_pip: float,
    adv_thresh_pip: float,
    pip: float,
) -> tuple[int, dict]:
    """Long-direction path-quality label + diagnostics for one signal."""
    fav_excursion_pip = (bid_h - entry_ask) / pip
    adv_excursion_pip = (entry_ask - bid_l) / pip
    fav_hit = fav_excursion_pip >= fav_thresh_pip
    adv_hit = adv_excursion_pip >= adv_thresh_pip
    first_fav = int(np.argmax(fav_hit)) if bool(fav_hit.any()) else -1
    first_adv = int(np.argmax(adv_hit)) if bool(adv_hit.any()) else -1
    label, same_bar = _resolve_label_from_first_hits(first_fav, first_adv)
    return label, {
        "max_fav_excursion_pip": float(fav_excursion_pip.max()),
        "max_adv_excursion_pip": float(adv_excursion_pip.max()),
        "time_to_fav_bar": first_fav,
        "time_to_adv_bar": first_adv,
        "same_bar_both_hit": same_bar,
    }


def _compute_label_short(
    ask_h: np.ndarray,
    ask_l: np.ndarray,
    entry_bid: float,
    fav_thresh_pip: float,
    adv_thresh_pip: float,
    pip: float,
) -> tuple[int, dict]:
    """Short-direction path-quality label + diagnostics for one signal."""
    fav_excursion_pip = (entry_bid - ask_l) / pip
    adv_excursion_pip = (ask_h - entry_bid) / pip
    fav_hit = fav_excursion_pip >= fav_thresh_pip
    adv_hit = adv_excursion_pip >= adv_thresh_pip
    first_fav = int(np.argmax(fav_hit)) if bool(fav_hit.any()) else -1
    first_adv = int(np.argmax(adv_hit)) if bool(adv_hit.any()) else -1
    label, same_bar = _resolve_label_from_first_hits(first_fav, first_adv)
    return label, {
        "max_fav_excursion_pip": float(fav_excursion_pip.max()),
        "max_adv_excursion_pip": float(adv_excursion_pip.max()),
        "time_to_fav_bar": first_fav,
        "time_to_adv_bar": first_adv,
        "same_bar_both_hit": same_bar,
    }


# ---------------------------------------------------------------------------
# Per-pair processing
# ---------------------------------------------------------------------------


def _causal_m5_atr_pip_strict(m5: pd.DataFrame, pair: str) -> pd.Series:
    """Causal M5 ATR with strict shift(1) per 25.0a-α §8.

    stage23_0a.atr_causal includes bar i in its window. 25.0a-α §8
    mandates that the signal bar's own data must NOT be used in its own
    ATR (NG#11 strict invariant). We apply an additional shift(1) on
    top of atr_causal output so atr_at_signal_pip[t] strictly uses
    bars [t-N..t-1].
    """
    pip = pip_size_for(pair)
    atr_price_inclusive = atr_causal(m5, ATR_N)  # includes bar i
    atr_price_strict = np.concatenate([[np.nan], atr_price_inclusive[:-1]])
    return pd.Series(atr_price_strict / pip, index=m5.index)


def _process_pair(
    pair: str, days: int, smoke_slice_days: int | None = None
) -> tuple[pd.DataFrame, dict]:
    """Build path-quality label rows for one pair.

    Returns (DataFrame of rows, counters dict). 2 rows per signal_ts
    (long + short). Drops:
    - rows with insufficient warmup / path / ATR
    - rows with K_FAV*ATR < M_MARGIN*spread (margin filter; §4.3)
    - rows with negative spread (data anomaly)

    `days` selects the canonical loader filename (e.g., 730 -> 730d_BA.jsonl).
    `smoke_slice_days`, if set, slices m1 to the LAST N days after loading
    (used by --smoke to test on a small recent slice).
    """
    pip = pip_size_for(pair)
    m1 = load_m1_ba(pair, days=days)
    if smoke_slice_days is not None and smoke_slice_days > 0:
        cutoff = m1.index.max() - pd.Timedelta(days=smoke_slice_days)
        m1 = m1[m1.index >= cutoff]
    m5 = aggregate_m1_to_tf(m1, SIGNAL_TF)
    m5_atr_pip = _causal_m5_atr_pip_strict(m5, pair)

    bid_h_arr = m1["bid_h"].to_numpy()
    bid_l_arr = m1["bid_l"].to_numpy()
    ask_h_arr = m1["ask_h"].to_numpy()
    ask_l_arr = m1["ask_l"].to_numpy()
    ask_o_arr = m1["ask_o"].to_numpy()
    bid_o_arr = m1["bid_o"].to_numpy()
    n_m1 = len(m1)
    m1_pos_lookup = pd.Series(np.arange(n_m1, dtype=np.int64), index=m1.index)

    rows: list[dict] = []
    counters = {
        "total_signal_candidates": 0,
        "dropped_no_atr": 0,
        "dropped_no_entry_bar": 0,
        "dropped_path_too_short": 0,
        "dropped_invalid_spread": 0,
        "dropped_by_margin": 0,
        "rows_emitted": 0,
    }

    for signal_ts in m5.index:
        counters["total_signal_candidates"] += 1
        atr_pip = m5_atr_pip.loc[signal_ts]
        if not np.isfinite(atr_pip):
            counters["dropped_no_atr"] += 1
            continue
        target_entry_ts = signal_ts + pd.Timedelta(minutes=1)
        if target_entry_ts not in m1_pos_lookup.index:
            counters["dropped_no_entry_bar"] += 1
            continue
        entry_m1_idx = int(m1_pos_lookup.loc[target_entry_ts])
        path_end = entry_m1_idx + H_M1_BARS
        if path_end > n_m1:
            counters["dropped_path_too_short"] += 1
            continue
        entry_ask = float(ask_o_arr[entry_m1_idx])
        entry_bid = float(bid_o_arr[entry_m1_idx])
        spread_pip = (entry_ask - entry_bid) / pip
        if spread_pip < 0 or not np.isfinite(spread_pip):
            counters["dropped_invalid_spread"] += 1
            continue
        fav_thresh_pip = K_FAV * float(atr_pip)
        adv_thresh_pip = K_ADV * float(atr_pip)
        if fav_thresh_pip < M_MARGIN * spread_pip:
            counters["dropped_by_margin"] += 1
            continue

        bh_path = bid_h_arr[entry_m1_idx:path_end]
        bl_path = bid_l_arr[entry_m1_idx:path_end]
        ah_path = ask_h_arr[entry_m1_idx:path_end]
        al_path = ask_l_arr[entry_m1_idx:path_end]

        long_label, long_diag = _compute_label_long(
            bh_path, bl_path, entry_ask, fav_thresh_pip, adv_thresh_pip, pip
        )
        short_label, short_diag = _compute_label_short(
            ah_path, al_path, entry_bid, fav_thresh_pip, adv_thresh_pip, pip
        )

        common = {
            "pair": pair,
            "signal_ts": signal_ts,
            "horizon_bars": H_M1_BARS,
            "entry_ask": entry_ask,
            "entry_bid": entry_bid,
            "atr_at_signal_pip": float(atr_pip),
            "spread_at_signal_pip": float(spread_pip),
        }
        rows.append({**common, "direction": "long", "label": long_label, **long_diag})
        rows.append({**common, "direction": "short", "label": short_label, **short_diag})
        counters["rows_emitted"] += 2

    df = pd.DataFrame(rows) if rows else pd.DataFrame()
    return df, counters


# ---------------------------------------------------------------------------
# Pathological balance check
# ---------------------------------------------------------------------------


def check_pathological_balance(
    df: pd.DataFrame, counters_by_pair: dict[str, dict]
) -> tuple[bool, dict]:
    """Returns (is_pathological, indicators_dict)."""
    if len(df) == 0:
        return True, {"reason": "no_rows_emitted"}

    overall_positive_rate = float(df["label"].mean())
    per_pair_positive_rate = df.groupby("pair", observed=True)["label"].mean().to_dict()
    per_pair_dropped_by_margin_rate: dict[str, float] = {}
    for pair, c in counters_by_pair.items():
        total = c["total_signal_candidates"]
        per_pair_dropped_by_margin_rate[pair] = (
            (c["dropped_by_margin"] / total) if total > 0 else 0.0
        )

    flags = {
        "overall_positive_rate": overall_positive_rate,
        "overall_low_breach": overall_positive_rate < PATHOLOGICAL_OVERALL_LOW,
        "overall_high_breach": overall_positive_rate > PATHOLOGICAL_OVERALL_HIGH,
        "per_pair_low_breaches": [
            p for p, r in per_pair_positive_rate.items() if r < PATHOLOGICAL_PER_PAIR_LOW
        ],
        "per_pair_high_dropped_by_margin": [
            p
            for p, r in per_pair_dropped_by_margin_rate.items()
            if r > PATHOLOGICAL_DROPPED_BY_MARGIN_HIGH
        ],
        "per_pair_positive_rate": per_pair_positive_rate,
        "per_pair_dropped_by_margin_rate": per_pair_dropped_by_margin_rate,
    }
    is_pathological = bool(
        flags["overall_low_breach"]
        or flags["overall_high_breach"]
        or flags["per_pair_low_breaches"]
        or flags["per_pair_high_dropped_by_margin"]
    )
    return is_pathological, flags


# ---------------------------------------------------------------------------
# Summary writers
# ---------------------------------------------------------------------------


def _summary_stats(s: pd.Series) -> dict:
    return {
        "count": int(s.count()),
        "mean": float(s.mean()),
        "median": float(s.median()),
        "p25": float(s.quantile(0.25)),
        "p75": float(s.quantile(0.75)),
        "p95": float(s.quantile(0.95)),
        "max": float(s.max()),
    }


def write_dataset_summary(
    out_path: Path,
    df: pd.DataFrame,
    counters_by_pair: dict[str, dict],
    pathological: bool,
    pathological_flags: dict,
    pairs: list[str],
) -> None:
    lines: list[str] = []
    lines.append("# Stage 25.0a-β — Path-Quality Label Dataset Summary")
    lines.append("")
    lines.append(f"Generated: {datetime.now(UTC).isoformat()}")
    lines.append("")
    lines.append("Design contract: `docs/design/phase25_0a_label_design.md` (PR #281)")
    lines.append("")
    lines.append("## Mandatory clauses")
    lines.append("")
    lines.append(
        "**Design constants are fixed.** K_FAV=1.5, K_ADV=1.0, M_MARGIN=2.0, "
        "H_M1_BARS=60 were fixed in 25.0a-α before implementation and MUST NOT "
        "be retuned in response to observed label balance. If the dataset is "
        "pathological per §12, this script halts and the user decides next "
        "steps."
    )
    lines.append("")
    lines.append(
        "**Causality.** Labels are computed from FUTURE bars [t+1, t+H_M1_BARS] "
        "only; features and ATR are computed from PAST bars only. The boundary "
        "at signal time t is hard. Same-bar SL-first invariant per PR #276 "
        "envelope §3.3."
    )
    lines.append("")
    lines.append(
        "**Diagnostic columns are not features.** The columns "
        "`max_fav_excursion_pip`, `max_adv_excursion_pip`, `time_to_fav_bar`, "
        "`time_to_adv_bar`, `same_bar_both_hit` are label-side diagnostic "
        "outputs computed from the same future bars as the label. Downstream "
        "feature-class evals (25.0b+) MUST NOT use them as model input "
        "features — doing so constitutes feature leakage."
    )
    lines.append("")
    lines.append(
        "**γ closure preservation.** Phase 25.0a does not modify the γ closure "
        "declared in PR #279. Phase 25 results, regardless of outcome, do not "
        "change Phase 24 / NG#10 β-chain closure status."
    )
    lines.append("")

    if pathological:
        lines.append("## ⚠ PATHOLOGICAL BALANCE — HALT")
        lines.append("")
        lines.append(
            "Per 25.0a-α §12, this run is HALTED. Thresholds were NOT retuned "
            "in-place. User direction is required to choose:"
        )
        lines.append("- (a) accept the imbalance and proceed to 25.0b,")
        lines.append("- (b) open a separate threshold-revision PR (NOT 25.0a-β edit),")
        lines.append("- (c) reject Phase 25 entirely.")
        lines.append("")

    lines.append("## Headline counts")
    lines.append("")
    total_rows = len(df)
    lines.append(f"- Total rows emitted: **{total_rows}**")
    if total_rows > 0:
        lines.append(f"- Total positive labels: {int(df['label'].sum())}")
        lines.append(f"- Overall positive rate: **{df['label'].mean():.4f}**")
    lines.append(f"- Pairs processed: {len(counters_by_pair)} / {len(pairs)}")
    lines.append("")

    lines.append("## Per-pair drop counts")
    lines.append("")
    lines.append(
        "| pair | total_candidates | dropped_no_atr | dropped_no_entry | dropped_path_short "
        "| dropped_invalid_spread | dropped_by_margin | rows_emitted |"
    )
    lines.append("|---|---|---|---|---|---|---|---|")
    for pair, c in counters_by_pair.items():
        lines.append(
            f"| {pair} | {c['total_signal_candidates']} | {c['dropped_no_atr']} | "
            f"{c['dropped_no_entry_bar']} | {c['dropped_path_too_short']} | "
            f"{c['dropped_invalid_spread']} | {c['dropped_by_margin']} | "
            f"{c['rows_emitted']} |"
        )
    lines.append("")

    if total_rows > 0:
        lines.append("## Rows by pair")
        lines.append("")
        rows_by_pair = df.groupby("pair", observed=True).size().to_dict()
        lines.append("| pair | rows |")
        lines.append("|---|---|")
        for p, n in sorted(rows_by_pair.items()):
            lines.append(f"| {p} | {n} |")
        lines.append("")

        lines.append("## Rows by direction")
        lines.append("")
        rows_by_dir = df.groupby("direction", observed=True).size().to_dict()
        lines.append("| direction | rows |")
        lines.append("|---|---|")
        for d, n in sorted(rows_by_dir.items()):
            lines.append(f"| {d} | {n} |")
        lines.append("")

        lines.append("## Positive label rate by pair")
        lines.append("")
        lines.append("| pair | positive_rate |")
        lines.append("|---|---|")
        for p, r in sorted(pathological_flags["per_pair_positive_rate"].items()):
            lines.append(f"| {p} | {r:.4f} |")
        lines.append("")

        lines.append("## Positive label rate by direction")
        lines.append("")
        rate_by_dir = df.groupby("direction", observed=True)["label"].mean().to_dict()
        lines.append("| direction | positive_rate |")
        lines.append("|---|---|")
        for d, r in sorted(rate_by_dir.items()):
            lines.append(f"| {d} | {r:.4f} |")
        lines.append("")

        lines.append("## Margin filter — drop count and rate")
        lines.append("")
        total_dropped_margin = sum(c["dropped_by_margin"] for c in counters_by_pair.values())
        total_candidates_overall = sum(
            c["total_signal_candidates"] for c in counters_by_pair.values()
        )
        overall_dropped_rate = (
            total_dropped_margin / total_candidates_overall if total_candidates_overall > 0 else 0.0
        )
        lines.append(
            f"- Overall: {total_dropped_margin} / {total_candidates_overall} = "
            f"**{overall_dropped_rate:.4f}**"
        )
        lines.append("")
        lines.append("Per-pair `dropped_by_margin_rate`:")
        lines.append("")
        lines.append("| pair | dropped_by_margin_rate |")
        lines.append("|---|---|")
        for p, r in sorted(pathological_flags["per_pair_dropped_by_margin_rate"].items()):
            lines.append(f"| {p} | {r:.4f} |")
        lines.append("")

        lines.append("## Same-bar both-hit count and rate")
        lines.append("")
        sbb_count = int(df["same_bar_both_hit"].sum())
        sbb_rate = float(df["same_bar_both_hit"].mean())
        lines.append(f"- count: {sbb_count}")
        lines.append(f"- rate (per emitted row): {sbb_rate:.4f}")
        lines.append("")

        for col_name, col_label in (
            ("time_to_fav_bar", "time_to_fav_bar (resolved rows only; -1 excluded)"),
            ("time_to_adv_bar", "time_to_adv_bar (resolved rows only; -1 excluded)"),
            ("atr_at_signal_pip", "atr_at_signal_pip"),
            ("spread_at_signal_pip", "spread_at_signal_pip"),
        ):
            lines.append(f"## Distribution: {col_label}")
            lines.append("")
            if col_name in ("time_to_fav_bar", "time_to_adv_bar"):
                series = df[col_name][df[col_name] >= 0]
            else:
                series = df[col_name]
            if len(series) > 0:
                stats = _summary_stats(series)
                lines.append(
                    f"- count: {stats['count']}, mean: {stats['mean']:.4f}, "
                    f"median: {stats['median']:.4f}, p25: {stats['p25']:.4f}, "
                    f"p75: {stats['p75']:.4f}, p95: {stats['p95']:.4f}, "
                    f"max: {stats['max']:.4f}"
                )
            else:
                lines.append("- (no rows)")
            lines.append("")

    lines.append("## Pathological balance check")
    lines.append("")
    lines.append(
        f"- overall_positive_rate: {pathological_flags.get('overall_positive_rate', 'n/a')}"
    )
    lines.append(
        f"- overall_low_breach (< {PATHOLOGICAL_OVERALL_LOW}): "
        f"{pathological_flags.get('overall_low_breach', 'n/a')}"
    )
    lines.append(
        f"- overall_high_breach (> {PATHOLOGICAL_OVERALL_HIGH}): "
        f"{pathological_flags.get('overall_high_breach', 'n/a')}"
    )
    lines.append(
        f"- per_pair_low_breaches (< {PATHOLOGICAL_PER_PAIR_LOW}): "
        f"{pathological_flags.get('per_pair_low_breaches', [])}"
    )
    lines.append(
        f"- per_pair_high_dropped_by_margin (> {PATHOLOGICAL_DROPPED_BY_MARGIN_HIGH}): "
        f"{pathological_flags.get('per_pair_high_dropped_by_margin', [])}"
    )
    lines.append("")
    lines.append(f"**Final flag: {'PATHOLOGICAL (HALT)' if pathological else 'PASS'}**")
    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


def write_causality_audit(out_path: Path) -> None:
    text = """# Stage 25.0a-β — Causality Audit

This document maps each binding causality invariant from 25.0a-α §9
to the unit test that enforces it. Unit tests are the authoritative
enforcement; this document is a brief audit map.

## Invariant 1 — Labels at `t` use only future bars `[t+1, t+H_M1_BARS]`

Labels are computed by slicing M1 OHLC arrays at `[entry_m1_idx,
entry_m1_idx + H_M1_BARS)` where `entry_m1_idx = position(signal_ts +
1 minute)`. No bar at index `<= signal_ts` is used in label
computation; no bar at index `> entry_m1_idx + H_M1_BARS - 1` is used.

Tests:
- `test_no_lookahead_uses_only_t_plus_1_through_t_plus_h`
- `test_no_use_of_bars_at_or_before_signal_time_for_label`

## Invariant 2 — `atr_at_signal_pip` at `t` uses only past bars (shift(1))

`stage23_0a.atr_causal` computes ATR over bars `[t-N+1, t]` (inclusive
of bar t). 25.0a-α §8 mandates strict `shift(1)` so signal bar t's own
data is NOT used in its own ATR. We apply an additional `shift(1)` on
top of `atr_causal` output via `_causal_m5_atr_pip_strict`, producing
ATR that strictly uses bars `[t-N..t-1]`.

Tests:
- `test_design_constants_match_25_0a_alpha`
- (manual: `_causal_m5_atr_pip_strict` shifts atr_causal output by 1 bar)

## Invariant 3 — `spread_at_signal_pip` uses bar `t`'s OHLC only

The spread is computed at the entry M1 bar (`t + 1 minute`) using its
ask_o − bid_o. This is the price at which the entry would actually
fill, so it is causally observable.

Tests:
- `test_spread_cost_integrated_long_uses_entry_ask`
- `test_spread_cost_integrated_short_uses_entry_bid`

## Invariant 4 — `entry_ask`, `entry_bid` at `t` are bar `t` open values

We use `ask_o[entry_m1_idx]` and `bid_o[entry_m1_idx]` (the open of
the entry M1 bar) as the cost-inclusive entry prices. This matches
the convention in stage23_0a.

Tests:
- `test_spread_cost_integrated_long_uses_entry_ask`
- `test_spread_cost_integrated_short_uses_entry_bid`

## Invariant 5 — Same-bar SL-first

Within the H-bar window, if a single M1 bar contains both fav-touch
and adv-touch conditions, the label is NEGATIVE (per PR #276 §3.3).
Implemented in `_resolve_label_from_first_hits`.

Tests:
- `test_same_bar_both_hit_long_labels_negative_hard`
- `test_same_bar_both_hit_short_labels_negative_hard`

## Invariant 6 — Ineligible rows are dropped, not labeled

Rows where `K_FAV * ATR < M_MARGIN * spread` are skipped via `continue`
and counted in `dropped_by_margin`. Rows with negative or non-finite
spread are skipped via `continue` and counted in
`dropped_invalid_spread`. Neither category produces a label row.

Tests:
- `test_low_volatility_signal_dropped_when_fav_threshold_below_margin`

## Diagnostic columns leakage prohibition

The columns `max_fav_excursion_pip`, `max_adv_excursion_pip`,
`time_to_fav_bar`, `time_to_adv_bar`, `same_bar_both_hit` are
label-side diagnostic outputs. They are computed from the same future
bars as the label and **MUST NOT be used as model input features by
any downstream Phase 25 PR (25.0b+)**. Per kickoff §10 / 25.0a-α §10,
each per-class PR must include a unit test asserting non-use.
"""
    out_path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pairs", nargs="*", default=PAIRS_20)
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_ROOT)
    parser.add_argument("--days", type=int, default=SPAN_DAYS)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Smoke run: 3 pairs × 1 day.",
    )
    args = parser.parse_args(argv)

    smoke_slice_days: int | None = None
    if args.smoke:
        args.pairs = SMOKE_PAIRS
        smoke_slice_days = 1
        # leave args.days at the canonical 730 for filename lookup

    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== Stage 25.0a-β path-quality label dataset ({len(args.pairs)} pairs) ===")
    print(f"Constants: K_FAV={K_FAV}, K_ADV={K_ADV}, M_MARGIN={M_MARGIN}, H={H_M1_BARS}")
    print(f"Span: {args.days} days; signal cadence: {SIGNAL_TF}")

    parts: list[pd.DataFrame] = []
    counters_by_pair: dict[str, dict] = {}
    for pair in args.pairs:
        t0 = time.time()
        df_pair, counters = _process_pair(pair, days=args.days, smoke_slice_days=smoke_slice_days)
        counters_by_pair[pair] = counters
        if len(df_pair) > 0:
            parts.append(df_pair)
        print(
            f"  {pair}: total_cand={counters['total_signal_candidates']:>6} "
            f"emitted={counters['rows_emitted']:>6} "
            f"drop_margin={counters['dropped_by_margin']:>5} "
            f"drop_spread={counters['dropped_invalid_spread']:>3} "
            f"drop_atr={counters['dropped_no_atr']:>3} "
            f"({time.time() - t0:5.1f}s)"
        )

    df = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if len(df) > 0:
        df["pair"] = df["pair"].astype("category")
        df["direction"] = df["direction"].astype("category")
        df["horizon_bars"] = df["horizon_bars"].astype("int8")
        df["label"] = df["label"].astype("int8")
        df["time_to_fav_bar"] = df["time_to_fav_bar"].astype("int16")
        df["time_to_adv_bar"] = df["time_to_adv_bar"].astype("int16")
        df["same_bar_both_hit"] = df["same_bar_both_hit"].astype("bool")
        for col in (
            "atr_at_signal_pip",
            "spread_at_signal_pip",
            "max_fav_excursion_pip",
            "max_adv_excursion_pip",
        ):
            df[col] = df[col].astype("float32")

    is_pathological, flags = check_pathological_balance(df, counters_by_pair)

    summary_path = args.out_dir / "dataset_summary.md"
    write_dataset_summary(
        summary_path, df, counters_by_pair, is_pathological, flags, list(args.pairs)
    )
    audit_path = args.out_dir / "causality_audit.md"
    write_causality_audit(audit_path)
    print(f"\nSummary: {summary_path}")
    print(f"Audit: {audit_path}")

    if len(df) > 0:
        parquet_path = args.out_dir / "path_quality_dataset.parquet"
        df.to_parquet(parquet_path, compression="snappy", index=False)
        print(f"Dataset: {parquet_path} ({len(df)} rows)")

    if is_pathological:
        print("\nPATHOLOGICAL BALANCE — halting per 25.0a-α §12")
        print("See dataset_summary.md for indicators. NO in-place threshold retuning.")
        return 1

    rate = flags.get("overall_positive_rate", "n/a")
    print(f"\nLabel balance OK. Total rows: {len(df)}; positive rate: {rate}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
