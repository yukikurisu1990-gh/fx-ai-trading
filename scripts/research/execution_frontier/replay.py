"""The offline replay: what execution costs on the two deciding panels.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Every bar of every pair is scored as a possible execution under all three
policies, and the populations below are then boolean masks over that. Nothing
here selects a bar by what happened to prices afterwards; the populations are
clock moments, sessions, month ends and the rollover window, all of which are
known in advance and none of which is an outcome.

Where the populations come from
-------------------------------

The clock ones come from `frontier.clock_spans` — the *same* function the
feasibility frontier enumerates its cells with. That matters more than it looks:
if Track 3 measured execution on bars chosen by its own copy of the window
logic, the cost it reported would belong to a design the frontier does not have,
and the two could drift apart without either being wrong on its own terms.

What a round trip means here
----------------------------

`C` and `C'` are the sum of two legs — an entry taken at a bar's **open** and an
exit taken at a bar's **close** — which is the same split the frontier charges,
so the numbers substitute into it directly. The entry and exit legs are summed
as population means, which is exact when both legs are drawn from the same
population and is what the frontier's own cost term does.
"""

from __future__ import annotations

import datetime as dt
import itertools
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.clock_flow import clock, frontier
from scripts.research.execution_frontier import (
    PENETRATION_SENSITIVITY,
    PRIMARY_RULE,
    WAIT_BARS_SENSITIVITY,
    band_for,
)
from scripts.research.execution_frontier.fills import FillRule, leg_costs, summarise_many
from scripts.research.exploratory_m15 import PAIRS

#: Entry legs are taken as a bar opens and exit legs as one closes, matching the
#: frontier's `entry_open` / `exit_close` convention exactly.
ENTRY_AT: Final[str] = "open"
EXIT_AT: Final[str] = "close"

#: Populations reported for every panel. Order fixed so the artifact is stable.
SESSION_NAMES: Final[tuple[str, ...]] = ("asia", "europe", "us")


class PanelReplay:
    """One panel's bars, scored once per pair under one fill rule."""

    def __init__(self, frames: dict[str, pd.DataFrame], rule: FillRule) -> None:
        self.frames = frames
        self.rule = rule
        self.arrays = frontier.PanelArrays(frames)
        self.entry = {p: leg_costs(f, at=ENTRY_AT, rule=rule) for p, f in frames.items()}
        self.exit = {p: leg_costs(f, at=EXIT_AT, rule=rule) for p, f in frames.items()}

    def blank_masks(self) -> dict[str, np.ndarray]:
        return {pair: np.zeros(len(frame), dtype=bool) for pair, frame in self.frames.items()}


def _clock_masks(
    replay: PanelReplay,
) -> dict[str, tuple[dict[str, np.ndarray], dict[str, np.ndarray]]]:
    """Entry-bar and exit-bar masks for every clock cell, from the frontier's own spans."""
    arrays = replay.arrays
    subsets: dict[str, list[dt.date]] = {
        "all_days": list(arrays.days),
        "month_end": sorted(clock.month_end_days(arrays.days)),
        "quarter_end": sorted(clock.quarter_end_days(arrays.days)),
    }
    out: dict[str, tuple[dict[str, np.ndarray], dict[str, np.ndarray]]] = {}
    for moment_name, side, (subset_name, days) in itertools.product(
        clock.MOMENTS, ("pre", "post"), subsets.items()
    ):
        entries, exits = replay.blank_masks(), replay.blank_masks()
        for day in days:
            spans, _ = frontier.clock_spans(arrays, moment_name, side, day)
            for pair, (entry, exit_) in spans.items():
                entries[pair][entry] = True
                exits[pair][exit_] = True
        key = f"{moment_name}_{side}"
        if subset_name != "all_days":
            key = f"{key}__{subset_name}"
        out[key] = (entries, exits)
    return out


def populations(
    replay: PanelReplay,
) -> dict[str, tuple[dict[str, np.ndarray], dict[str, np.ndarray]]]:
    """Every population, as `(entry mask, exit mask)` per pair.

    `all_bars` is the primary cost surface and excludes the rollover window, which
    is reported on its own. Everything else is a design-known subset: the clock
    cells, the three sessions, and the complement of the clock cells.
    """
    frames = replay.frames
    rollover = {pair: frame["rollover"].to_numpy(dtype=bool) for pair, frame in frames.items()}
    tradable = {pair: ~flags for pair, flags in rollover.items()}

    out: dict[str, tuple[dict[str, np.ndarray], dict[str, np.ndarray]]] = {
        "all_bars": (tradable, tradable),
        "rollover_window": (rollover, rollover),
    }
    for name in SESSION_NAMES:
        mask = {
            pair: (frame["session"].to_numpy() == name) & tradable[pair]
            for pair, frame in frames.items()
        }
        out[f"session_{name}"] = (mask, mask)

    clock_masks = _clock_masks(replay)
    out.update(clock_masks)
    #: The complement of every clock entry bar, so "event" and "non-event" are
    #: exhaustive rather than two separately drawn samples.
    any_event = replay.blank_masks()
    for entries, _ in clock_masks.values():
        for pair, mask in entries.items():
            any_event[pair] |= mask
    non_event = {pair: (~mask) & tradable[pair] for pair, mask in any_event.items()}
    out["non_event"] = (non_event, non_event)
    return out


def _roundtrip(entry: dict[str, Any], exit_: dict[str, Any]) -> dict[str, Any]:
    """`C`, `C'` and their ratio, as the sum of the two legs."""
    if not entry.get("n") or not exit_.get("n"):
        return {}
    baseline = entry["baseline_leg_bp"] + exit_["baseline_leg_bp"]
    passive = entry["passive_leg_bp"] + exit_["passive_leg_bp"]
    record = {
        "baseline_roundtrip_bp": round(float(baseline), 4),
        "passive_roundtrip_bp": round(float(passive), 4),
    }
    if baseline > 0:
        record["cost_ratio"] = round(float(passive / baseline), 4)
        record["band"] = band_for(record["cost_ratio"])
    return record


def measure_population(
    replay: PanelReplay,
    entry_masks: dict[str, np.ndarray],
    exit_masks: dict[str, np.ndarray],
) -> dict[str, Any]:
    entry = summarise_many([(replay.entry[p], entry_masks[p]) for p in PAIRS if p in replay.entry])
    exit_ = summarise_many([(replay.exit[p], exit_masks[p]) for p in PAIRS if p in replay.exit])
    return {"entry_leg": entry, "exit_leg": exit_, "roundtrip": _roundtrip(entry, exit_)}


def by_pair(
    replay: PanelReplay,
    entry_masks: dict[str, np.ndarray],
    exit_masks: dict[str, np.ndarray],
) -> dict[str, Any]:
    """The same headline per pair, because a pooled number that is really one
    pair is a composition artifact and this corpus has produced two of them."""
    out: dict[str, Any] = {}
    for pair in PAIRS:
        if pair not in replay.entry:
            continue
        entry = summarise_many([(replay.entry[pair], entry_masks[pair])])
        exit_ = summarise_many([(replay.exit[pair], exit_masks[pair])])
        trip = _roundtrip(entry, exit_)
        if trip:
            out[pair] = {
                **trip,
                "fill_rate": entry.get("fill_rate"),
                "n": entry.get("n"),
            }
    return out


def sensitivity(frames: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """The declared `WAIT_BARS` and `PENETRATION_PIPS` axes, one at a time.

    Reported because the pre-registration obliges it, not because the primary was
    unsatisfying. Only the `all_bars` headline is varied: the point of the axis is
    what the *rule* does to the cost, and repeating thirty cells four times would
    bury that.
    """
    out: dict[str, Any] = {}
    primary_wait, primary_pen = PRIMARY_RULE
    grid = [(w, primary_pen) for w in WAIT_BARS_SENSITIVITY] + [
        (primary_wait, p) for p in PENETRATION_SENSITIVITY if p != primary_pen
    ]
    for wait, penetration in grid:
        rule = FillRule(wait_bars=wait, penetration_pips=penetration)
        replay = PanelReplay(frames, rule)
        #: The tradable mask directly rather than through `populations`, which
        #: would re-enumerate thirty clock cells per grid point to reach one of
        #: them.
        tradable = {pair: ~frame["rollover"].to_numpy(dtype=bool) for pair, frame in frames.items()}
        record = measure_population(replay, tradable, tradable)
        out[rule.label] = {
            "wait_bars": wait,
            "penetration_pips": penetration,
            **record["roundtrip"],
            "fill_rate": record["entry_leg"].get("fill_rate"),
            #: A clock window is four bars long, so a policy that waits four bars
            #: cannot complete an entry inside one. Stated per row rather than
            #: left for a reader to derive, because the primary rule is one of the
            #: rows it disqualifies.
            "fits_inside_a_four_bar_clock_window": wait <= frontier.WINDOW_BARS - 1,
        }
    return out


def build(panels: dict[str, dict[str, pd.DataFrame]]) -> dict[str, Any]:
    """The whole replay: every panel, every population, plus the declared axes."""
    rule = FillRule()
    record: dict[str, Any] = {
        "classification": [
            "NON_DECISION_BEARING_EXPLORATORY_ONLY",
            "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
        ],
        "signal_free": True,
        "rule": {
            "wait_bars": rule.wait_bars,
            "penetration_pips": rule.penetration_pips,
            "drift_bars": rule.drift_bars,
            "label": rule.label,
        },
        "panels": {},
    }
    for panel, frames in panels.items():
        replay = PanelReplay(frames, rule)
        pops = populations(replay)
        measured = {name: measure_population(replay, *masks) for name, masks in pops.items()}
        record["panels"][panel] = {
            "n_pairs": len(frames),
            "n_bars": int(sum(len(f) for f in frames.values())),
            "n_measurable": int(sum(int(c.measurable.sum()) for c in replay.entry.values())),
            "populations": measured,
            "by_pair": by_pair(replay, *pops["all_bars"]),
            "sensitivity": sensitivity(frames),
        }
    record["consistency"] = _consistency(record["panels"])
    return record


def _consistency(panels: dict[str, Any]) -> dict[str, Any]:
    """Whether the two deciding panels say the same thing, headline by headline.

    The pre-registration rules that the **worse** band governs a disagreement, so
    this reports the band each panel reached and the one that governs, rather
    than a pooled figure a disagreement could hide inside.
    """
    names = sorted(panels)
    out: dict[str, Any] = {}
    for population in sorted({key for panel in panels.values() for key in panel["populations"]}):
        ratios: dict[str, float] = {}
        for name in names:
            trip = panels[name]["populations"].get(population, {}).get("roundtrip", {})
            if "cost_ratio" in trip:
                ratios[name] = trip["cost_ratio"]
        if len(ratios) < len(names):
            continue
        worst = max(ratios.values())
        out[population] = {
            #: Nested one level so the numeric key is `cost_ratio` and not a panel
            #: name. The unit audit walks this record and a panel name is not a
            #: declared unit-free field, which is the check working.
            "per_panel": {name: {"cost_ratio": value} for name, value in ratios.items()},
            "cost_ratio_spread": round(max(ratios.values()) - min(ratios.values()), 4),
            "governing_band": band_for(worst),
            "panels_agree_on_band": len({band_for(v) for v in ratios.values()}) == 1,
        }
    return out


__all__ = [
    "ENTRY_AT",
    "EXIT_AT",
    "SESSION_NAMES",
    "PanelReplay",
    "build",
    "by_pair",
    "measure_population",
    "populations",
    "sensitivity",
]
