"""The event test, its null, and the power figure that decides whether to run.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

One engine serves both families, because the shape is the same: a set of
timestamps, a signed signal per timestamp, and a forward return per pair. What
differs is where the signal comes from.

The three things this engine refuses to get wrong
--------------------------------------------------

**Power is computed before the result is read.** `minimum_detectable_effect`
runs the null with random signs and reports what the design could have found. A
cell whose MDE sits above the round-trip break-even is marked
`UNDERPOWERED_NOT_REPORTED_AS_EVIDENCE` — it is not quietly reported as a null.

**The null keeps the events and moves only the signal.** Signs are drawn per
*event*, never per pair-event, so the cross-pair dependence inside a release
survives every draw. Drawing per pair-event would treat seven correlated
observations as seven independent ones and shrink the null by about `√7`.

**The tail clause is the programme's own.** Top ten events over **net**,
negatives included — not over the positive part, which at these sample sizes
returns roughly what noise gives and therefore cannot fail.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from scripts.research.expectation import (
    NULL_DRAWS,
    POWER_MULTIPLIER,
    SEED,
    TAIL_SHARE_CEILING,
)

#: One spread plus half a pip, round trip — the programme's cost model.
HALF_SPREAD_ADDITION = 0.5


def usd_side(pair: str) -> int:
    """+1 if holding the pair is holding USD, −1 if it is selling USD."""
    base, quote = pair.split("_")
    if base == "USD":
        return 1
    if quote == "USD":
        return -1
    raise ValueError(f"{pair} has no USD leg")


def usd_pairs(pairs: list[str]) -> list[str]:
    return sorted(pair for pair in pairs if "USD" in pair.split("_"))


def entry_index(
    times: pd.Series, stamp: dt.datetime, *, tolerance_hours: float = 2.0
) -> int | None:
    """The first bar starting **strictly after** the moment, or `None`.

    Strictly after, so the bar containing the print is never entered on. A gap
    wider than the tolerance means the market was shut; the event is dropped
    rather than shifted onto a much later bar carrying a different information
    set.
    """
    moment = pd.Timestamp(stamp)
    position = int(times.searchsorted(moment, side="right"))
    if position >= len(times):
        return None
    if times.iloc[position] - moment > pd.Timedelta(hours=tolerance_hours):
        return None
    return position


def event_returns(
    frames: dict[str, pd.DataFrame],
    events: list[dict[str, Any]],
    *,
    horizon_bars: int,
    signal_key: str = "composite_z",
) -> pd.DataFrame:
    """Per (event × USD pair): the USD-direction move, its cost, and the signal.

    The move is kept **separate from the sign**. The price side is computed once
    and the signal side is permuted against it, which is what makes the null a
    statement about the signal rather than about the calendar.
    """
    rows: list[dict[str, Any]] = []
    for pair in usd_pairs(list(frames)):
        frame = frames[pair]
        times = frame["ts"].reset_index(drop=True)
        close = frame["mid_c"].to_numpy(dtype=float)
        open_ = frame["mid_o"].to_numpy(dtype=float)
        spread = frame["spread_close_pips"].to_numpy(dtype=float)
        pip = float(frame["pip_size"].iloc[0])
        side = usd_side(pair)
        for index, event in enumerate(events):
            signal = event.get(signal_key)
            if signal is None or not np.isfinite(signal) or signal == 0.0:
                continue
            entry = entry_index(times, dt.datetime.fromisoformat(event["release_timestamp_utc"]))
            if entry is None or entry + horizon_bars >= len(close):
                continue
            #: the move expressed as "long USD", so a sign of +1 is long USD
            usd_move = side * (close[entry + horizon_bars] - open_[entry]) / pip
            rows.append(
                {
                    "event": index,
                    "pair": pair,
                    "release_timestamp_utc": event["release_timestamp_utc"],
                    "families": tuple(event.get("families", ())),
                    "signal": float(signal),
                    "usd_move_pips": float(usd_move),
                    "cost_pips": float(spread[entry]) + HALF_SPREAD_ADDITION,
                }
            )
    return pd.DataFrame(rows)


def _null_means(table: pd.DataFrame, *, draws: int, seed: int) -> list[float]:
    """Random signs **per event**, so cross-pair dependence survives the draw."""
    rng = np.random.default_rng(seed)
    events = table["event"].to_numpy()
    order = {value: index for index, value in enumerate(sorted(set(events)))}
    position = np.array([order[value] for value in events])
    move = table["usd_move_pips"].to_numpy(dtype=float)
    out: list[float] = []
    for _ in range(draws):
        signs = rng.choice([-1.0, 1.0], size=len(order))
        out.append(float(np.mean(signs[position] * move)))
    return out


def minimum_detectable_effect(
    table: pd.DataFrame, *, draws: int = NULL_DRAWS, seed: int = SEED
) -> dict[str, Any]:
    """What this design could have found, computed before the result is read.

    A cell whose MDE exceeds the round-trip break-even at double cost cannot
    distinguish a tradeable effect from nothing, and is marked so rather than
    being reported as a null.
    """
    if table.empty:
        return {"events": 0, "runnable": False, "reason": "no events"}
    nulls = _null_means(table, draws=draws, seed=seed)
    mde = POWER_MULTIPLIER * float(np.std(nulls, ddof=1))
    break_even_double = 2.0 * float(table["cost_pips"].mean())
    return {
        "events": int(table["event"].nunique()),
        "pair_events": int(len(table)),
        "pairs": int(table["pair"].nunique()),
        "mean_cost_pips": round(float(table["cost_pips"].mean()), 4),
        "break_even_double_cost_pips": round(break_even_double, 4),
        "mde_80pct_power_pips": round(mde, 4),
        "runnable": bool(mde <= break_even_double),
        "reason": (
            None
            if mde <= break_even_double
            else "UNDERPOWERED_NOT_REPORTED_AS_EVIDENCE: MDE exceeds the double-cost break-even"
        ),
    }


def evaluate(table: pd.DataFrame, *, draws: int = NULL_DRAWS, seed: int = SEED) -> dict[str, Any]:
    """Everything the plan asks a cell to report, plus its own null."""
    if table.empty:
        return {"events": 0}
    direction = np.sign(table["signal"].to_numpy(dtype=float))
    gross = direction * table["usd_move_pips"].to_numpy(dtype=float)
    cost = table["cost_pips"].to_numpy(dtype=float)
    net = gross - cost

    per_pair = {
        pair: {
            "events": int(len(block)),
            "gross_mean": float((np.sign(block["signal"]) * block["usd_move_pips"]).mean()),
        }
        for pair, block in table.groupby("pair")
    }
    statistic = float(np.mean(gross) / (np.std(gross, ddof=1) / np.sqrt(len(gross))))
    nulls = _null_means(table, draws=draws, seed=seed)
    null_stats = []
    for value in nulls:
        #: the same statistic under the null, so the p-value compares like with
        #: like: a mean scaled by the same i.i.d. standard error
        null_stats.append(value / (np.std(gross, ddof=1) / np.sqrt(len(gross))))
    extreme = sum(1 for value in null_stats if abs(value) >= abs(statistic))
    p_value = (extreme + 1) / (len(null_stats) + 1)

    net_total = float(net.sum())
    tail = float(np.sort(gross)[-10:].sum() / net_total) if net_total else None
    sd_null = float(np.std(nulls, ddof=1))

    signal = table["signal"].to_numpy(dtype=float)
    realised = table["usd_move_pips"].to_numpy(dtype=float)
    return {
        "events": int(table["event"].nunique()),
        "pair_events": int(len(table)),
        "pairs": len(per_pair),
        "gross_mean_pips": float(np.mean(gross)),
        "cost_mean_pips": float(np.mean(cost)),
        "net_mean_pips": float(np.mean(net)),
        "net_mean_pips_double_cost": float(np.mean(gross - 2.0 * cost)),
        "expectancy_per_event_pips": float(np.mean(net) * len(table) / table["event"].nunique()),
        "gross_t": statistic,
        "permutation_p": p_value,
        "null_statistics": null_stats,
        "null_mean_sd_pips": sd_null,
        "gross_mean_ci95_pips": [
            float(np.mean(gross) - 1.96 * sd_null),
            float(np.mean(gross) + 1.96 * sd_null),
        ],
        "mde_80pct_power_pips": float(POWER_MULTIPLIER * sd_null),
        "directional_ic": float(scipy_stats.spearmanr(signal, realised).statistic),
        "hit_rate": float((gross > 0).mean()),
        "pairs_gross_positive": sum(1 for cell in per_pair.values() if cell["gross_mean"] > 0),
        "tail_share_of_net": tail,
        "per_pair": per_pair,
        "positive_signal_events": int((table.groupby("event")["signal"].first() > 0).sum()),
        "negative_signal_events": int((table.groupby("event")["signal"].first() < 0).sum()),
    }


def family_max_p(cells: dict[str, dict[str, Any]]) -> dict[str, float]:
    """Westfall–Young over the shared draws, refusing to truncate.

    Draw `b` must be the same draw in every cell. A cell that produced a
    different number of draws would silently be paired with its neighbour's
    draw `b+1`, so unequal lengths refuse rather than truncate.
    """
    usable = {name: cell for name, cell in cells.items() if cell.get("null_statistics")}
    if not usable:
        return {}
    widths = {len(cell["null_statistics"]) for cell in usable.values()}
    if len(widths) != 1:
        return {}
    width = widths.pop()
    maxima = [
        max(abs(cell["null_statistics"][index]) for cell in usable.values())
        for index in range(width)
    ]
    return {
        name: (sum(1 for value in maxima if value >= abs(cell["gross_t"])) + 1) / (len(maxima) + 1)
        for name, cell in usable.items()
    }


def verdict(
    per_panel: dict[str, dict[str, Any]],
    deciding: tuple[str, ...],
    *,
    primary: tuple[str, ...],
    corrected: dict[str, dict[str, float]],
    min_events: int,
    supported_status: str,
    not_supported_status: str,
) -> dict[str, Any]:
    """The plan's kill clauses, read mechanically. Every one fails closed."""
    rows = [per_panel[panel] for panel in deciding if panel in per_panel]
    complete = len(rows) == len(deciding) and bool(rows)

    reasons: list[str] = []
    if not complete:
        reasons.append("PANEL_MISSING")
    else:
        for name in primary:
            cells = [panel.get(name) for panel in rows]
            if any(cell is None or not cell.get("events") for cell in cells):
                reasons.append(f"CELL_MISSING_{name}")
                continue
            #: A cell the power gate refused is **not a null**. It carries no
            #: statistics at all, so every clause below would raise on it; the
            #: verdict records that the design could not decide instead of
            #: silently treating an absence of evidence as evidence of absence.
            if any("skipped" in cell for cell in cells):
                reasons.append(f"UNDERPOWERED_NOT_DECIDABLE_{name}")
                continue
            if min(cell["events"] for cell in cells) < min_events:
                reasons.append(f"TOO_FEW_EVENTS_{name}")
            gross = [cell["gross_mean_pips"] for cell in cells]
            if len({int(np.sign(value)) for value in gross}) > 1:
                reasons.append(f"PANEL_SIGN_REVERSAL_{name}")
            if any(cell["net_mean_pips"] <= 0 for cell in cells):
                reasons.append(f"NEGATIVE_AFTER_COST_{name}")
            tails = [cell.get("tail_share_of_net") for cell in cells]
            if any(value is not None and value > TAIL_SHARE_CEILING for value in tails):
                reasons.append(f"TAIL_ABOVE_CEILING_{name}")
            adjusted = [
                corrected.get(panel, {}).get(name) for panel in deciding if panel in per_panel
            ]
            if any(value is None or value >= 0.05 for value in adjusted):
                reasons.append(f"FAMILYWISE_NULL_{name}")

    survives = complete and not reasons
    undecidable = any(reason.startswith("UNDERPOWERED_NOT_DECIDABLE") for reason in reasons)
    return {
        "status": (
            supported_status
            if survives
            else ("NOT_DECISION_GRADE_SKIP" if undecidable else not_supported_status)
        ),
        "decidable": not undecidable,
        "complete": complete,
        "primary_cells": list(primary),
        "drop_reasons": sorted(set(reasons)),
        "note": (
            "The pre-registered sign is fixed. A measured effect in the "
            "opposite direction drops the family; it is never inverted."
        ),
    }


__all__ = [
    "HALF_SPREAD_ADDITION",
    "entry_index",
    "evaluate",
    "event_returns",
    "family_max_p",
    "minimum_detectable_effect",
    "usd_pairs",
    "usd_side",
    "verdict",
]
