"""Research Design Pass-Region Preflight — can this question be answered at all?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Track 2's real defect was not a threshold. It was that nothing asked, **before the
study ran**, whether a design of that shape could pass Gate v2 at all. Its
pre-registration's success arm required the economic gate, and that arm was
unreachable the day it was frozen. This module asks that question first, from the
plan alone.

⭐ The unit convention, which is what makes the horizon a wall
---------------------------------------------------------------

A plan declares `events_per_year` and `panel_years`, and `n_events` follows from
them. That is **not** Gate v2's convention — `Design` takes the two separately,
deliberately — so it has to be justified rather than assumed, because the whole
horizon result rests on it.

The justification is that a design has **one** unit of observation, and every
quantity must use it:

* if the unit is a currency-day, then a seven-currency book takes seven positions
  a day, pays seven positions' turnover, and `f` counts currency-days;
* if the unit is the netted portfolio-day, then `N` counts days, the dispersion is
  the book's rather than a single currency's, and `f` counts days.

Either way `N = f × panel_years` **for that unit**, and `effN ≤ N`, so
`effN/f ≤ panel_years`. A review offered a counterexample that passes Gate v2 on
today's panels — and it counts `N` in currency-days while counting `f` in
portfolio-days, claiming sevenfold precision while paying for one book's
turnover. Re-specified consistently in *either* unit, it fails at every dispersion
and at zero cost. `TestTheUnitConventionIsForced` holds exactly that.

There is no third option in which the estimate is sharper than the trading: a book
that averages seven currency positions has a dispersion smaller by the same
factor its count is larger by, and the two cancel in the MDE.

The closed form
---------------

Gate v2's two conditions, solved for the dispersion, are an interval::

    statistical   z(k)·σ/√effN ≤ MRE     ⟺   σ ≤ MRE·√effN / z(k)
    plausibility  MRE·√f/σ ≤ IR_max      ⟺   σ ≥ MRE·√f / IR_max

The interval is non-empty exactly when ``effN ≥ (z(k)/IR_max)²·f`` — a condition in
which **MRE, σ and cost all cancel**. Since ``f = N/years`` and ``effN ≤ N``, the
ratio ``effN/f`` can never exceed the panel's own length, so this is a statement
about the **data horizon** and nothing else:

    required effective years = (z(k) / IR_max)²

``z(k)`` carries the multiple-testing burden, so a family with more primary cells
needs a longer panel. Nothing here can be satisfied by choosing a better signal, a
cheaper execution or a happier threshold.

What cost may and may not touch
--------------------------------

Cost enters the **economic net** condition and nothing else. Lowering it can only
leave the statistical side alone and help the economic side; raising it can only
hurt the economic side. That is the v1 inversion designed out rather than
promised away, and synthetic tests hold it.

Nothing here reads a return
----------------------------

There is no path from a realised return, a sign, an information coefficient, a
Sharpe ratio or a p-value into any verdict. The inputs are a plan. A variance
estimate is allowed, but it must declare where it came from, and
`VarianceSource` does not contain an option that would come from the candidate's
own signal.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

from scipy import stats as scipy_stats

from scripts.research.feasibility import (
    ALPHA,
    COST_STRESS_MULTIPLE,
    MAX_PLAUSIBLE_GROSS_IR,
    MIN_EVENTS_PER_PANEL,
    MIN_NET_MARGIN_BP,
    POWER,
    assert_prospective,
)
from scripts.research.feasibility.gate_v2 import Design, minimum_relevant_effect_bp
from scripts.research.fxunits import POWER_MULTIPLIER as GATE_V2_MULTIPLIER

STATUS: Final[str] = "PASS_REGION_PREFLIGHT_SPECIFIED"

#: How close to a boundary a plan may sit before it is called marginal rather
#: than feasible. A design that passes by less than this is one assumption away
#: from not passing, and the decision ruled that such designs are not primary
#: research candidates.
MARGIN_FLOOR: Final[float] = 0.20

#: Two panels, because the two-panel rule is not relaxable.
MIN_DECIDING_PANELS: Final[int] = 2


class Verdict(StrEnum):
    PASS_REGION_EXISTS = "PASS_REGION_EXISTS"
    #: A study whose target is not a signed per-event return. Not a refusal and
    #: not an approval: this gate is about tradable edges and does not adjudicate
    #: measurements that feed one.
    OUT_OF_GATE_SCOPE = "OUT_OF_GATE_SCOPE"
    MARGINAL_PASS_REGION = "MARGINAL_PASS_REGION"
    NO_DECISION_GRADE_PASS_REGION = "NO_DECISION_GRADE_PASS_REGION"
    DATA_INTEGRITY_BLOCKED = "DATA_INTEGRITY_BLOCKED"
    PRIOR_FAMILY_CLOSED = "PRIOR_FAMILY_CLOSED"


class VarianceSource(StrEnum):
    """Where a dispersion estimate is allowed to come from. Never from the signal."""

    UNCONDITIONAL_RETURN_VARIANCE = "unconditional_return_variance"
    WINDOW_VARIANCE = "window_variance"
    PREVIOUSLY_FROZEN_DESIGN_STATISTIC = "previously_frozen_design_statistic"
    SYNTHETIC_CONSERVATIVE_ESTIMATE = "synthetic_conservative_estimate"
    SIGNAL_BLIND_SAMPLE_VARIANCE = "signal_blind_sample_variance"
    NOT_ESTIMATED = "not_estimated"


@dataclass(frozen=True)
class ResearchPlan:
    """A research design, described without a single realised return."""

    candidate_id: str
    hypothesis: str
    mechanism: str
    target: str
    horizon: str
    unit_of_observation: str
    events_per_year: float
    panel_years: float
    n_deciding_panels: int
    #: `effN / N`, declared with its reason. One over the number of effectively
    #: independent cross-sectional dimensions is the usual shape in this corpus,
    #: which has measured 4.6 to 6.5 independent directions in twenty pairs.
    effective_n_share: float
    effective_n_basis: str
    roundtrip_cost_bp: float
    primary_cells: int
    required_breadth: int
    available_breadth: int
    data_ready: bool
    data_note: str = ""
    variance_source: VarianceSource = VarianceSource.NOT_ESTIMATED
    dispersion_bp: float | None = None
    prior_verdict: str | None = None
    #: Where the closing verdict is recorded, so a reader can check it from the
    #: artifact rather than from a markdown table.
    prior_verdict_citation: str | None = None
    #: The family name Gate v2's retroactivity registry knows this plan by, when
    #: there is one. Naming an excluded family here makes `assess` raise.
    gate_v2_family: str | None = None
    #: Not every research target is a signed per-event return. A cost measurement
    #: or a magnitude forecast is a real study that this gate's MRE and IR ceiling
    #: are simply not defined for, and saying so is better than returning a
    #: verdict computed from the wrong thing.
    gate_applies_to_the_target: bool = True
    #: Suspended by a Human + ChatGPT decision. Not a falsification, and not a
    #: verdict — a plan can be suspended and underpowered at once.
    suspended_by_decision: bool = False
    ml_role: str = "none"

    def __post_init__(self) -> None:
        if not 0.0 < self.effective_n_share <= 1.0:
            raise ValueError("effective_n_share is a fraction of N and cannot exceed one")
        if self.events_per_year <= 0 or self.panel_years <= 0:
            raise ValueError("a plan needs a positive frequency and a positive panel")
        if self.primary_cells < 1:
            raise ValueError("a family has at least one primary cell")
        if self.roundtrip_cost_bp < 0:
            raise ValueError("a round trip cannot cost less than nothing")

    @property
    def n_events(self) -> float:
        return self.events_per_year * self.panel_years

    @property
    def effective_n(self) -> float:
        return self.n_events * self.effective_n_share

    @property
    def effective_years(self) -> float:
        """`effN / f`, which can never exceed the panel's own length."""
        return self.effective_n / self.events_per_year


def power_multiplier(primary_cells: int) -> float:
    """`z(1 - α/2k) + z(power)`: the multiple-testing burden, in the multiplier.

    At `k = 1` this is Gate v2's own multiplier, and `test_the_multiplier_is_gate_v2s`
    holds the two to each other — a review found the preflight recomputing from
    `ALPHA`/`POWER` while Gate v2 used a rounded literal, so the two could have
    drifted apart without anything noticing.
    """
    return float(
        scipy_stats.norm.ppf(1.0 - ALPHA / (2.0 * primary_cells)) + scipy_stats.norm.ppf(POWER)
    )


def required_effective_years_gate_v2() -> float:
    """**Gate v2's own necessary condition**, with no correction added.

    `(z / IR_max)²` at one primary cell. Nothing here is stricter than the frozen
    gate; this is the horizon below which the gate's two conditions cannot both
    hold, derived from the gate and from nothing else.
    """
    return (GATE_V2_MULTIPLIER / MAX_PLAUSIBLE_GROSS_IR) ** 2


def required_effective_years(primary_cells: int) -> float:
    """The preflight's admissibility bar, which at `k > 1` is **stricter** than
    Gate v2.

    Gate v2 carries no multiple-testing correction. The sequencing decision lists
    the multiple-testing burden as a preflight input, so it is applied here — but
    it is an **additional** requirement the preflight imposes, not a necessary
    condition of the gate, and a review was right that calling it the latter was
    wrong. `required_effective_years_gate_v2()` is the gate's own figure.

    Two caveats a reader should have, neither of them resolved here:

    * the two-panel rule already demands the same effect on both panels, which is
      a stronger control than `α` on its own, so a Bonferroni term on top of it
      over-corrects;
    * the power side is left per-panel at 80%, so the conjunction's power is
      lower than 80% and this under-corrects.

    The two run in opposite directions. They are disclosed rather than netted,
    because netting them would be a threshold choice and thresholds are frozen.
    """
    return (power_multiplier(primary_cells) / MAX_PLAUSIBLE_GROSS_IR) ** 2


def _minimum_relevant_effect(plan: ResearchPlan) -> float:
    """MRE for the plan, through Gate v2's own function.

    `Design` refuses an effective sample larger than the sample, so the rounded
    count is taken as the ceiling and the effective count clamped to it — a
    fractional `n_events` is a planning figure, not an observation.
    """
    count = max(int(round(plan.n_events)), 1)
    return minimum_relevant_effect_bp(
        Design(
            label=plan.candidate_id,
            n_events=count,
            effective_n=min(max(plan.effective_n, 1e-9), float(count)),
            dispersion_bp=1.0,
            events_per_year=plan.events_per_year,
        )
    )


def dispersion_window_bp(plan: ResearchPlan) -> tuple[float, float]:
    """`[lower, upper]` — the dispersions at which both Gate v2 conditions hold."""
    relevant = _minimum_relevant_effect(plan)
    lower = relevant * math.sqrt(plan.events_per_year) / MAX_PLAUSIBLE_GROSS_IR
    upper = relevant * math.sqrt(plan.effective_n) / power_multiplier(plan.primary_cells)
    return lower, upper


def admissible_frequency_bp(plan: ResearchPlan) -> tuple[float, float | None]:
    """The frequency band the other two conditions leave open.

    The event floor gives a lower bound and the stressed-cost condition an upper
    one, so a design can be too rare to adjudicate **and** too frequent to pay
    for. Reporting the band is what tells a reader which way to move a design.
    """
    floor = MIN_EVENTS_PER_PANEL / plan.panel_years
    #: `2.5 + 300/f >= 2c + 0.5` rearranges to `f <= 300 / (2c - 2)`.
    denominator = COST_STRESS_MULTIPLE * plan.roundtrip_cost_bp + MIN_NET_MARGIN_BP - 2.5
    ceiling = 300.0 / denominator if denominator > 0 else None
    return floor, ceiling


def assess(plan: ResearchPlan) -> dict[str, Any]:
    """Every condition, the margins, and the verdict. Reads no return."""
    #: The machine-enforced ban, on this path as well. A review found it reachable
    #: only through a hand-typed `prior_verdict` string, which is the "prose
    #: promise" the frozen gate says it is not. A plan naming an excluded family
    #: now raises from `assert_prospective` before anything is computed.
    if plan.gate_v2_family:
        assert_prospective(plan.gate_v2_family)
    if plan.prior_verdict == Verdict.PRIOR_FAMILY_CLOSED.value:
        return {
            "candidate_id": plan.candidate_id,
            "verdict": Verdict.PRIOR_FAMILY_CLOSED.value,
            "reason": plan.prior_verdict_citation
            or "a prior research verdict closed this hypothesis class",
            "prior_verdict_citation": plan.prior_verdict_citation,
        }
    if not plan.data_ready:
        return {
            "candidate_id": plan.candidate_id,
            "verdict": Verdict.DATA_INTEGRITY_BLOCKED.value,
            "reason": plan.data_note or "provenance, timestamp, coverage or access",
        }

    if not plan.gate_applies_to_the_target:
        #: The MRE is a net-return threshold and the plausibility ceiling is a
        #: directional information ratio. Neither is defined for a cost surface or
        #: a magnitude forecast, so the honest output is the horizon arithmetic
        #: and an explicit statement that the economic gate does not apply.
        return {
            "candidate_id": plan.candidate_id,
            "verdict": Verdict.OUT_OF_GATE_SCOPE.value,
            "reason": (
                "the target is not a signed per-event return, so Gate v2's minimum "
                "relevant effect and plausibility ceiling are not defined for it"
            ),
            "n_events_per_panel": round(plan.n_events, 1),
            "effective_n": round(plan.effective_n, 1),
            "gate_applies_to_the_target": False,
        }

    needed = required_effective_years(plan.primary_cells)
    lower, upper = dispersion_window_bp(plan)
    floor, ceiling = admissible_frequency_bp(plan)
    relevant = _minimum_relevant_effect(plan)

    conditions = {
        "horizon": plan.effective_years >= needed,
        "event_floor": plan.n_events >= MIN_EVENTS_PER_PANEL,
        "two_panels": plan.n_deciding_panels >= MIN_DECIDING_PANELS,
        "economic_net_under_stress": relevant
        >= COST_STRESS_MULTIPLE * plan.roundtrip_cost_bp + MIN_NET_MARGIN_BP,
        "breadth": plan.available_breadth >= plan.required_breadth,
        "dispersion_window_is_non_empty": lower <= upper,
    }
    #: A declared dispersion has to sit inside the window; an undeclared one only
    #: has to have somewhere to sit, and the plan says so.
    if plan.dispersion_bp is not None:
        conditions["declared_dispersion_inside_the_window"] = lower <= plan.dispersion_bp <= upper

    margins = {
        "horizon": plan.effective_years / needed - 1.0,
        "event_floor": plan.n_events / MIN_EVENTS_PER_PANEL - 1.0,
        "economic_net_under_stress": relevant
        / (COST_STRESS_MULTIPLE * plan.roundtrip_cost_bp + MIN_NET_MARGIN_BP)
        - 1.0,
    }
    #: The binding constraint is the first **failing** condition when there is
    #: one, and only otherwise the thinnest margin. A review found a plan failing
    #: `breadth` or `two_panels` reporting a binding constraint it passed.
    failing = [name for name, ok in conditions.items() if not ok]
    tightest = min(margins.values())
    binding = failing[0] if failing else sorted(margins, key=lambda name: margins[name])[0]
    if failing and failing[0] in margins:
        binding = sorted(
            (name for name in failing if name in margins), key=lambda name: margins[name]
        )[0]

    if not all(conditions.values()):
        verdict = Verdict.NO_DECISION_GRADE_PASS_REGION
    elif tightest < MARGIN_FLOOR:
        verdict = Verdict.MARGINAL_PASS_REGION
    else:
        verdict = Verdict.PASS_REGION_EXISTS

    return {
        "candidate_id": plan.candidate_id,
        "verdict": verdict.value,
        "conditions": conditions,
        "margins": {name: round(value, 4) for name, value in margins.items()},
        "binding_constraint": binding,
        "required_effective_years": round(needed, 3),
        "effective_years": round(plan.effective_years, 3),
        "years_short": round(max(0.0, needed - plan.effective_years), 3),
        "n_events_per_panel": round(plan.n_events, 1),
        "effective_n": round(plan.effective_n, 1),
        "minimum_relevant_effect_bp": round(relevant, 4),
        "dispersion_window_bp": [round(lower, 4), round(upper, 4)],
        "admissible_events_per_year": [
            round(floor, 2),
            round(ceiling, 2) if ceiling is not None else None,
        ],
        "power_multiplier": round(power_multiplier(plan.primary_cells), 4),
        "variance_source": plan.variance_source.value,
        "effective_n_basis": plan.effective_n_basis,
    }


def years_to_decision(plan: ResearchPlan) -> dict[str, Any]:
    """What a blocked plan would need, quantified. Design arithmetic only.

    Reported for every plan the horizon condition stops, because "not now" is
    only useful beside "and this much would change it".
    """
    needed = required_effective_years(plan.primary_cells)
    have = plan.effective_years
    #: Panel years, not effective years: the panel has to be long enough that its
    #: dependence-adjusted observation reaches the requirement.
    panel_years_needed = needed / plan.effective_n_share
    return {
        "candidate_id": plan.candidate_id,
        "current_effective_years": round(have, 3),
        "required_effective_years": round(needed, 3),
        "additional_effective_years": round(max(0.0, needed - have), 3),
        "panel_years_needed_per_panel": round(panel_years_needed, 3),
        "total_seen_years_needed": round(panel_years_needed * MIN_DECIDING_PANELS, 3),
        "events_needed_per_panel": round(panel_years_needed * plan.events_per_year, 1),
    }


__all__ = [
    "MARGIN_FLOOR",
    "MIN_DECIDING_PANELS",
    "STATUS",
    "ResearchPlan",
    "VarianceSource",
    "Verdict",
    "admissible_frequency_bp",
    "assess",
    "dispersion_window_bp",
    "power_multiplier",
    "required_effective_years",
    "required_effective_years_gate_v2",
    "years_to_decision",
]
