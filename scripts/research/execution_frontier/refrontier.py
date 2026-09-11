"""The feasibility frontier recomputed on a measured execution cost.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The substitution, and why it is a substitution
----------------------------------------------

The unit audit measured what each design could decide when a round trip costs
what a market order costs. This module runs **the same enumeration** with the
cost source swapped for the replay's simulated passive policy. Nothing else
changes: the same windows, the same random directions, the same MDE estimator,
the same gates. That the two agree byte for byte when the quoted source is
passed back in is what makes the difference attributable to execution.

What the substitution does not do
---------------------------------

It does not re-simulate the strategy. The returns are still measured from the
design's own entry and exit bars, while a passive fill lands somewhere inside
the resting window. The question being answered is the sensitivity of the
frontier to cost — *if a round trip cost `C'`, which cells could be decided?* —
and not what a passive clock strategy would have earned.

That gap is not cosmetic, and it is the reason `WAIT_BARS` is reported across its
whole declared range rather than at the primary alone. A clock window is four
bars. A policy that rests four bars cannot complete an entry inside one, so the
primary rule is not a rule those cells could use; only the one- and two-bar
variants fit. The frontier is therefore reported at every declared wait, with
each row saying whether it fits.

The gates
---------

Unchanged from the unit audit, because inventing a gate after seeing a result is
the failure this sequencing exists to prevent:

* **powered** — the MDE sits at or under twice the median round trip, on **both**
  deciding panels;
* **payable** — the break-even gross information ratio sits at or under
  `IR_max`, again on both, reported at 1.0, 1.5 and 2.0 rather than at one
  chosen value;
* **two-panel** — a cell that passes on one panel and fails on the other has not
  passed.

The committed `MIN_EVENTS_PER_DECIDING_PANEL` floor of sixty is reported beside
the count rather than folded into it. It is a real constant and a thin cell
should be visible as thin, but it was not one of the three gates named in the
adjudication, and quietly adding a fourth after the fact would be the same
mistake in the other direction.
"""

from __future__ import annotations

from typing import Any, Final

import pandas as pd

from scripts.research.clock_flow import MIN_EVENTS_PER_DECIDING_PANEL, frontier
from scripts.research.clock_flow.frontier import ILLUSTRATIVE_GROSS_IR
from scripts.research.execution_frontier import PENETRATION_PIPS, WAIT_BARS_SENSITIVITY
from scripts.research.execution_frontier.fills import FillRule, leg_costs
from scripts.research.execution_frontier.replay import ENTRY_AT, EXIT_AT

QUOTED: Final[str] = "quoted"

#: `POST_HOC_EXPLORATORY`. The pre-registered penetration requirement is one
#: pip, and a review showed the *sign* of the cost comparison is set by that
#: constant rather than by the panels. So the frontier is also computed at a
#: near-touch calibration — a fill granted for a twentieth of a pip through the
#: limit, which is what full queue priority would buy and which no retail account
#: can rely on. It is the **best case** for passive execution that this data can
#: support, and it is here so that the claim "no cost level reached by any of
#: these policies makes a cell decision-grade" is a property of the artifact
#: rather than of a reviewer's scratch file.
TOUCH_PENETRATION_PIPS: Final[float] = 0.05
TOUCH_WAITS: Final[tuple[int, ...]] = (1, 2)

#: Which leg cost the measured source serves. `MARKET` is the same market order
#: the quoted source prices, but measured through the fill model — same bars,
#: same refusals, same open/close quotes. It exists so that `passive` can be
#: compared against a baseline that differs from it in **policy only**: the
#: quoted source prices the entry leg from the bar's *closing* spread applied at
#: its opening mid, which is a source difference, not an execution one.
PASSIVE: Final[str] = "passive"
MARKET: Final[str] = "market"


class MeasuredExecutionCosts:
    """Costs from the replay's `P2` policy, addressed by bar and direction.

    A bar the fill model could not measure — one whose resting window runs across
    a session gap or off the end of the panel — returns `None`, and the frontier
    drops that pair from that event rather than pricing it at zero. That is a
    real difference from the quoted source, which can price any bar, and it is
    reported as dropped pair-windows rather than absorbed silently.
    """

    def __init__(
        self, frames: dict[str, pd.DataFrame], rule: FillRule, *, policy: str = PASSIVE
    ) -> None:
        if policy not in (PASSIVE, MARKET):
            raise ValueError(f"policy must be {PASSIVE!r} or {MARKET!r}, not {policy!r}")
        self.rule = rule
        self.policy = policy
        self._entry = {p: leg_costs(f, at=ENTRY_AT, rule=rule) for p, f in frames.items()}
        self._exit = {p: leg_costs(f, at=EXIT_AT, rule=rule) for p, f in frames.items()}
        #: Refusals are recorded as the *pair-windows* they are, not as the two
        #: to four leg lookups `window` makes for each one. A first version
        #: counted lookups and reported them under a name that said windows,
        #: which overstated the disclosure by two to four times.
        self.refused: set[tuple[str, str, int]] = set()

    @property
    def dropped(self) -> int:
        return len(self.refused)

    def _lookup(
        self, table: dict[str, Any], side: str, pair: str, index: int, direction: int
    ) -> float | None:
        costs = table.get(pair)
        if costs is None or index < 0 or index >= len(costs.measurable):
            return None
        if not costs.measurable[index]:
            self.refused.add((side, pair, index))
            return None
        leg = costs.for_direction(direction)
        source = leg.passive_bp if self.policy == PASSIVE else leg.baseline_bp
        return float(source[index])

    def entry(self, pair: str, index: int, direction: int) -> float | None:
        return self._lookup(self._entry, ENTRY_AT, pair, index, direction)

    def exit(self, pair: str, index: int, direction: int) -> float | None:
        return self._lookup(self._exit, EXIT_AT, pair, index, direction)


def _cells(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Flatten a panel's clock and calendar designs into one keyed table."""
    out: dict[str, dict[str, Any]] = {}
    for family in ("calendar", "clock"):
        for key, cell in record[family].items():
            out[f"{family}:{key}"] = cell
    return out


def variant(frames: dict[str, pd.DataFrame], costs: Any) -> tuple[dict[str, Any], int]:
    """One panel, one cost source, through the frontier's own enumeration."""
    arrays = frontier.PanelArrays(frames, costs=costs)
    record = {
        "years": round(arrays.years, 3),
        "n_days": len(arrays.days),
        "calendar": frontier.calendar_designs(arrays),
        "clock": frontier.clock_designs(arrays),
    }
    dropped = getattr(costs, "dropped", 0)
    return record, int(dropped)


def _verdicts(per_panel: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Join a cell across the two panels and apply the three gates."""
    if not per_panel or any(not cell.get("n_events") for cell in per_panel.values()):
        return {}
    powered = all(bool(cell.get("decidable")) for cell in per_panel.values())
    ratios = [cell.get("economics", {}).get("break_even_gross_ir") for cell in per_panel.values()]
    if any(value is None for value in ratios):
        return {}
    worst_ir = max(float(value) for value in ratios)
    events = min(int(cell["n_events"]) for cell in per_panel.values())
    out: dict[str, Any] = {
        "n_events_min": events,
        "break_even_gross_ir_worst": round(worst_ir, 2),
        "powered_on_both_panels": powered,
        "clears_the_event_floor": events >= MIN_EVENTS_PER_DECIDING_PANEL,
        "per_panel": {
            name: {
                "n_events": int(cell["n_events"]),
                "mde_bp": cell["mde_bp"],
                "median_roundtrip_cost_bp": cell["median_roundtrip_cost_bp"],
                "mean_roundtrip_cost_bp": cell["mean_roundtrip_cost_bp"],
                "hurdle_bp": cell["hurdle_bp"],
                "one_times_cost_bp": round(cell["median_roundtrip_cost_bp"], 3),
                "headroom_bp": cell["headroom_bp"],
                "decidable": bool(cell["decidable"]),
                "break_even_gross_ir": cell.get("economics", {}).get("break_even_gross_ir"),
            }
            for name, cell in per_panel.items()
        },
    }
    out["feasible"] = {
        "_unit": "count",
        **{str(ir): bool(powered and worst_ir <= ir) for ir in ILLUSTRATIVE_GROSS_IR},
    }
    return out


def feasibility(panels_by_variant: dict[str, dict[str, dict[str, Any]]]) -> dict[str, Any]:
    """Every cell, every variant, with the three gates applied across both panels."""
    out: dict[str, Any] = {}
    for label, panels in panels_by_variant.items():
        tables = {name: _cells(record) for name, record in panels.items()}
        keys = sorted(set.intersection(*(set(t) for t in tables.values()))) if tables else []
        cells: dict[str, Any] = {}
        for key in keys:
            verdict = _verdicts({name: table[key] for name, table in tables.items()})
            if verdict:
                cells[key] = verdict
        counts = {
            "_unit": "count",
            **{
                str(ir): sum(1 for c in cells.values() if c["feasible"][str(ir)])
                for ir in ILLUSTRATIVE_GROSS_IR
            },
        }
        survivors = {
            str(ir): sorted(k for k, c in cells.items() if c["feasible"][str(ir)])
            for ir in ILLUSTRATIVE_GROSS_IR
        }
        out[label] = {
            "n_cells": len(cells),
            "n_feasible": counts,
            "feasible_cells": survivors,
            "feasible_cells_clearing_the_event_floor": {
                str(ir): sorted(
                    k
                    for k, c in cells.items()
                    if c["feasible"][str(ir)] and c["clears_the_event_floor"]
                )
                for ir in ILLUSTRATIVE_GROSS_IR
            },
            "cells": cells,
        }
    return out


def build(panels: dict[str, dict[str, pd.DataFrame]]) -> dict[str, Any]:
    """The quoted frontier and the execution frontier at every declared wait."""
    variants: dict[str, dict[str, dict[str, Any]]] = {}
    dropped: dict[str, dict[str, int]] = {}
    record: dict[str, Any] = {
        "classification": [
            "NON_DECISION_BEARING_EXPLORATORY_ONLY",
            "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
        ],
        "signal_free": True,
        "variants_measured": [],
    }
    for panel, frames in panels.items():
        quoted, _ = variant(frames, None)
        variants.setdefault(QUOTED, {})[panel] = quoted
        for wait in WAIT_BARS_SENSITIVITY:
            rule = FillRule(wait_bars=wait, penetration_pips=PENETRATION_PIPS)
            for policy in (MARKET, PASSIVE):
                label = f"{policy}_{rule.label}"
                source = MeasuredExecutionCosts(frames, rule, policy=policy)
                measured, drops = variant(frames, source)
                variants.setdefault(label, {})[panel] = measured
                dropped.setdefault(label, {})[panel] = drops
        for wait in TOUCH_WAITS:
            rule = FillRule(wait_bars=wait, penetration_pips=TOUCH_PENETRATION_PIPS)
            source = MeasuredExecutionCosts(frames, rule, policy=PASSIVE)
            measured, drops = variant(frames, source)
            label = f"post_hoc_touch_{rule.label}"
            variants.setdefault(label, {})[panel] = measured
            dropped.setdefault(label, {})[panel] = drops
    record["variants_measured"] = sorted(variants)
    record["post_hoc_variants"] = sorted(
        label for label in variants if label.startswith("post_hoc_")
    )
    record["fits_inside_a_four_bar_clock_window"] = {
        **{
            f"{policy}_w{wait}_p{PENETRATION_PIPS:g}": wait <= frontier.WINDOW_BARS - 1
            for wait in WAIT_BARS_SENSITIVITY
            for policy in (MARKET, PASSIVE)
        },
        **{
            f"post_hoc_touch_w{wait}_p{TOUCH_PENETRATION_PIPS:g}": wait <= frontier.WINDOW_BARS - 1
            for wait in TOUCH_WAITS
        },
    }
    record["pair_windows_the_fill_model_could_not_price"] = {
        "_unit": "count",
        **{label: sum(counts.values()) for label, counts in dropped.items()},
    }
    record["feasibility"] = feasibility(variants)
    record["panels"] = variants
    return record


__all__ = [
    "MARKET",
    "TOUCH_PENETRATION_PIPS",
    "TOUCH_WAITS",
    "PASSIVE",
    "QUOTED",
    "MeasuredExecutionCosts",
    "build",
    "feasibility",
    "variant",
]
