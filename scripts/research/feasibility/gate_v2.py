"""The two gates, and the composition that keeps them apart.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    statistical:  MDE <= minimum relevant effect        (no cost anywhere)
    economic:     MRE - cost >= net margin, at base and stressed cost,
                  and the implied gross annual IR is believable
    robustness:   both deciding panels carry enough events to adjudicate

Why `events_per_year` is an input and not `n_events / years`
--------------------------------------------------------------

The minimum relevant effect scales with the design's **frequency**: a monthly
event has to move the market more than a daily one to be worth the same annual
return. It must **not** scale with the sample size, or lengthening the panel
would raise the bar as fast as it lowers the MDE and no amount of data would ever
improve feasibility. So frequency is declared by the design and `n_events` only
enters the MDE. Contract test B holds exactly this.

Why the economic gate carries a plausibility ceiling
-----------------------------------------------------

For a rare design the minimum relevant effect is large — a twelve-a-year cell
needs 25 bp an event to make three per cent — and a large target is *easy* to
detect, so the statistical gate passes automatically. The binding question there
is not statistical at all: it is whether an effect that large could exist. That
is the unit audit's break-even gross information ratio, rebuilt from the frozen
reference rather than from the design's own cost, and it lives in the economic
gate where cost questions belong.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from scripts.research.feasibility import (
    COST_STRESS_MULTIPLE,
    MAX_PLAUSIBLE_GROSS_IR,
    MIN_ANNUAL_NET_RETURN_BP,
    MIN_EVENTS_PER_PANEL,
    MIN_NET_MARGIN_BP,
    MIN_RELEVANT_EFFECT_FLOOR_BP,
    REFERENCE_ROUNDTRIP_COST_BP,
    STATUS_PROSPECTIVE_ONLY,
    assert_prospective,
)
from scripts.research.fxunits import POWER_MULTIPLIER, UNIT


@dataclass(frozen=True)
class Design:
    """What a gate needs to know about a research design. No prices, no returns."""

    label: str
    n_events: int
    effective_n: float
    dispersion_bp: float
    events_per_year: float

    def __post_init__(self) -> None:
        if self.n_events < 0:
            raise ValueError("n_events cannot be negative")
        if self.effective_n <= 0:
            raise ValueError("effective_n must be positive")
        if self.effective_n > self.n_events:
            raise ValueError(
                "effective_n cannot exceed n_events: dependence can only shrink a "
                "sample, and a value above it would raise power out of nothing"
            )
        if self.dispersion_bp <= 0:
            raise ValueError("dispersion_bp must be positive")
        if self.events_per_year <= 0:
            raise ValueError("events_per_year must be positive")


@dataclass(frozen=True)
class Costs:
    """A design's own realistic round trip, in basis points of mid."""

    roundtrip_bp: float
    source: str = "realistic market-order execution"

    def __post_init__(self) -> None:
        if self.roundtrip_bp < 0:
            raise ValueError("a round trip cannot cost less than nothing")

    @property
    def stressed_bp(self) -> float:
        return COST_STRESS_MULTIPLE * self.roundtrip_bp


def minimum_relevant_effect_bp(design: Design) -> float:
    """The smallest per-event gross effect this programme would act on.

    Built from the **frozen reference** round trip, never from the design's own
    cost — that separation is the whole point of v2, and `Design` does not carry
    a cost for it to read.
    """
    from_return = REFERENCE_ROUNDTRIP_COST_BP + MIN_ANNUAL_NET_RETURN_BP / design.events_per_year
    return max(from_return, MIN_RELEVANT_EFFECT_FLOOR_BP)


def mde_bp(design: Design) -> float:
    """Minimum detectable effect at 80% power, two-sided 5%.

    Uses `effective_n`, so a design whose events overlap or whose observations
    are correlated is charged for it rather than credited with independence it
    does not have.
    """
    return POWER_MULTIPLIER * design.dispersion_bp / math.sqrt(design.effective_n)


def statistical_gate(design: Design) -> dict[str, Any]:
    """Can this design see an effect worth seeing? Cost appears nowhere."""
    detectable = mde_bp(design)
    relevant = minimum_relevant_effect_bp(design)
    return {
        "mde_bp": round(detectable, 4),
        "minimum_relevant_effect_bp": round(relevant, 4),
        "headroom_bp": round(relevant - detectable, 4),
        "n_events": design.n_events,
        "effective_n": round(float(design.effective_n), 3),
        "dispersion_bp": round(design.dispersion_bp, 4),
        "events_per_year": round(design.events_per_year, 3),
        "pass": bool(detectable <= relevant),
    }


def economic_gate(design: Design, costs: Costs) -> dict[str, Any]:
    """Would an effect of that size be worth trading? Cost appears in full."""
    relevant = minimum_relevant_effect_bp(design)
    net = relevant - costs.roundtrip_bp
    stressed_net = relevant - costs.stressed_bp
    implied_ir = relevant * math.sqrt(design.events_per_year) / design.dispersion_bp
    checks = {
        "net_margin": bool(net >= MIN_NET_MARGIN_BP),
        "stressed_net_margin": bool(stressed_net >= MIN_NET_MARGIN_BP),
        "implied_effect_is_believable": bool(implied_ir <= MAX_PLAUSIBLE_GROSS_IR),
    }
    return {
        "minimum_relevant_effect_bp": round(relevant, 4),
        "roundtrip_cost_bp": round(costs.roundtrip_bp, 4),
        "stressed_cost_bp": round(costs.stressed_bp, 4),
        "net_bp": round(net, 4),
        "stressed_net_bp": round(stressed_net, 4),
        "implied_gross_annual_ir": round(implied_ir, 4),
        "checks": checks,
        "pass": all(checks.values()),
    }


def robustness_gate(panels: dict[str, Design]) -> dict[str, Any]:
    """Enough events on **each** deciding panel, and more than one of them.

    Deliberately minimal. Pooling panels to reach power is a diagnostic and never
    a success criterion, so nothing here can be satisfied by adding two panels
    together.
    """
    counts = {name: design.n_events for name, design in panels.items()}
    return {
        "n_events_per_panel": {"_unit": "count", **counts},
        "min_events_required": MIN_EVENTS_PER_PANEL,
        "n_panels": len(panels),
        "pass": bool(
            len(panels) >= 2 and all(count >= MIN_EVENTS_PER_PANEL for count in counts.values())
        ),
    }


def adjudicate(family: str, panels: dict[str, Design], costs: Costs) -> dict[str, Any]:
    """Every gate, per panel, plus the composition — for a **new** family only.

    The first thing this does is refuse a retroactive application. A family that
    was closed under earlier rules is not reopened by a later gate.
    """
    key = assert_prospective(family)
    if not panels:
        raise ValueError("a verdict needs at least one deciding panel")

    statistical = {name: statistical_gate(design) for name, design in panels.items()}
    economic = {name: economic_gate(design, costs) for name, design in panels.items()}
    robustness = robustness_gate(panels)
    passes = {
        "statistical": all(block["pass"] for block in statistical.values()),
        "economic": all(block["pass"] for block in economic.values()),
        "robustness": robustness["pass"],
    }
    return {
        "family": key,
        "status": STATUS_PROSPECTIVE_ONLY,
        "unit": UNIT,
        "reference_roundtrip_cost_bp": REFERENCE_ROUNDTRIP_COST_BP,
        "statistical": statistical,
        "economic": economic,
        "robustness": robustness,
        "gates_passed": passes,
        #: Reported as three verdicts and a conjunction, never as the conjunction
        #: alone: separating them is why this gate exists.
        "research_feasible": all(passes.values()),
    }


__all__ = [
    "Costs",
    "Design",
    "adjudicate",
    "economic_gate",
    "mde_bp",
    "minimum_relevant_effect_bp",
    "robustness_gate",
    "statistical_gate",
]
