"""A feasibility gate per model **role**, because one gate cannot fit all of them.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The decision is explicit that the five-condition gate built for a direction
generator must not be applied mechanically to every use of a model. A ranking
model, a trade/skip filter, a regime representation and a portfolio allocator
fail in different ways, so they are gated on different prerequisites — with two
budgets and one economic condition shared by all of them.

The economic condition closes a loophole in the capacity budget
---------------------------------------------------------------

`budgets.admissible_parameters` scales with `IR^2`, so a design that simply
*declares* a high target ratio buys itself a larger model. It does not get to.
The target ratio is **computed from the design's own economics**:

    required_gross_IR = (min_annual_net_bp + turnover * roundtrip_bp) / annual_vol_bp

and the design is refused outright if that exceeds the frozen plausibility
ceiling. ⭐ The consequence is worth stating plainly: daily rebalancing of a
currency basket at the measured round trip needs a gross annual IR near the
ceiling, and weekly rebalancing needs about a third of it — so **trading more
often buys capacity only by demanding an edge nobody here has ever seen**. The
capacity budget is then evaluated at that required ratio, never at a wish.

What the gate refuses on sight
------------------------------

The decision lists shapes that may not be re-run. They are encoded rather than
promised: a high-capacity model pointed at a direction target over raw price
features is refused before any budget is computed, as is a design that declares a
random split, and one that counts twenty pairs as twenty independent assets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Final

from scripts.research.feasibility import (
    MAX_PLAUSIBLE_GROSS_IR,
    MIN_ANNUAL_NET_RETURN_BP,
    RetroactiveApplicationError,
    assert_prospective,
)
from scripts.research.model_learning import ModelRole
from scripts.research.model_learning import budgets as budget_module

#: A **declared volatility target** for the traded book, not a measurement of
#: anything: volatility scaling is a design choice, and this is the scale at
#: which the hurdle is expressed. Capped so that the economic condition cannot be
#: passed by leverage — a design that needs 40% annualised volatility to clear a
#: 3% net hurdle has not cleared it.
DEFAULT_ANNUAL_VOL_BP: Final[float] = 800.0
MAX_ANNUAL_VOL_BP: Final[float] = 1000.0

#: Effective parameters above which a model is "high capacity" for the purpose of
#: recognising the Round 1 shape. Two orders of magnitude above anything 4.674
#: years can support, so the recogniser cannot catch an admissible design.
HIGH_CAPACITY_PARAMETERS: Final[float] = 50.0

#: Training architectures that are not a random split. Anything else is refused.
TEMPORAL_ARCHITECTURES: Final[frozenset[str]] = frozenset(
    {"walk_forward", "blocked_purged", "expanding_window"}
)


class Verdict(StrEnum):
    DEVELOPMENT_ADMISSIBLE = "DEVELOPMENT_ADMISSIBLE"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    SEARCH_BUDGET_EXCEEDED = "SEARCH_BUDGET_EXCEEDED"
    ECONOMICALLY_UNREACHABLE = "ECONOMICALLY_UNREACHABLE"
    ROLE_PREREQUISITE_MISSING = "ROLE_PREREQUISITE_MISSING"
    FORBIDDEN_REPEAT_OF_A_CLOSED_SHAPE = "FORBIDDEN_REPEAT_OF_A_CLOSED_SHAPE"
    PRIOR_FAMILY_CLOSED = "PRIOR_FAMILY_CLOSED"


@dataclass(frozen=True, slots=True)
class ModelDesign:
    """One candidate, declared in full before anything is fitted."""

    candidate_id: str
    hypothesis: str
    role: ModelRole
    target: str
    #: A target that is not adjusted for the cost of acting on it cannot be
    #: economically assessed. Roles that produce a tradable signal require it.
    target_is_cost_adjusted: bool
    horizon: str
    holding_days: float
    feature_families: tuple[str, ...]
    model_class: str
    model_settings: dict[str, float]
    nominal_configurations: int
    training_architecture: str
    validation_years: float
    turnover_per_year: float
    roundtrip_cost_bp: float
    cross_sectional_units: int
    effective_units: float
    leakage_controls: tuple[str, ...]
    prior_research_overlap: str
    why_different_from_round_1: str
    expected_information_gain: str
    annual_vol_bp: float = DEFAULT_ANNUAL_VOL_BP
    #: Role prerequisites, each required by exactly one role.
    base_opportunity: str | None = None
    base_expectancy_is_a_kill_rule: bool = False
    rank_stability_metric: str | None = None
    candidate_horizons: tuple[str, ...] = ()
    downstream_consumer: str | None = None
    consumer_annual_ir: float | None = None
    #: A representation's parameters are **added** to its consumer's, because the
    #: pair is what gets fitted on the same 4.674 years. Charging the two budgets
    #: separately would let a design buy capacity by splitting itself in half.
    consumer_effective_parameters: float = 0.0
    ablation: str | None = None
    parent_candidate: str | None = None
    measures_cost_not_edge: bool = False
    #: The adjudicated family this candidate belongs to, when it belongs to one.
    #: Checked through the same `assert_prospective` that guards Gate v2, so a
    #: closed family cannot be reopened by moving to a different gate — which is
    #: exactly the move a new phase is tempted to make.
    gate_family: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


def required_gross_annual_ir(design: ModelDesign) -> float:
    """The ratio the design has to reach to be worth running, from its own costs."""
    if design.annual_vol_bp <= 0:
        raise ValueError("a book with no volatility has no information ratio")
    if design.annual_vol_bp > MAX_ANNUAL_VOL_BP:
        raise ValueError(
            f"{design.annual_vol_bp} bp of annualised volatility exceeds the cap "
            f"{MAX_ANNUAL_VOL_BP}; clearing a net hurdle by leverage is not clearing it"
        )
    annual_cost_bp = design.turnover_per_year * design.roundtrip_cost_bp
    return (MIN_ANNUAL_NET_RETURN_BP + annual_cost_bp) / design.annual_vol_bp


def _forbidden_repeat(design: ModelDesign) -> str | None:
    """The shapes the decision forbids, recognised rather than promised against."""
    architecture = design.training_architecture.strip().lower()
    if architecture not in TEMPORAL_ARCHITECTURES:
        return (
            f"{design.training_architecture!r} is not a temporal architecture; a random "
            "split over overlapping forward returns leaks the label"
        )
    if design.cross_sectional_units > 1 and design.effective_units >= design.cross_sectional_units:
        return (
            f"{design.cross_sectional_units} units declared as "
            f"{design.effective_units} effective ones — treating the pairs as "
            "independent assets is the error H-003 measured at 96%"
        )
    try:
        parameters = budget_module.effective_parameters(design.model_class, **design.model_settings)
    except budget_module.BudgetError:
        parameters = float("inf")
    raw_price_only = set(design.feature_families) <= {
        "price_state",
        "technical_indicators",
        "volatility",
    }
    direction_target = "direction" in design.target.lower() or "sign" in design.target.lower()
    if parameters > HIGH_CAPACITY_PARAMETERS and direction_target and raw_price_only:
        return (
            "a high-capacity model over raw price features pointed at direction is the "
            "H-004 shape, which the decision forbids re-running"
        )
    return None


def _role_prerequisite(design: ModelDesign) -> str | None:
    """What this role needs before a budget is worth computing."""
    role = design.role
    if role is ModelRole.DIRECTION_OR_RETURN and not design.target_is_cost_adjusted:
        return "a direction or return generator must predict a cost-adjusted quantity"
    if role is ModelRole.RANKING:
        if design.cross_sectional_units < 6:
            return f"a cross-section of {design.cross_sectional_units} is not a ranking problem"
        if design.effective_units < 3:
            return (
                f"{design.effective_units} effectively independent units cannot support a "
                "rank; the ranking would be one factor wearing a cross-sectional label"
            )
        if not design.rank_stability_metric:
            return "a ranking candidate must declare how rank stability will be measured"
    if role is ModelRole.TRADE_SKIP:
        if not design.base_opportunity:
            return (
                "a trade/skip model must name the base opportunity it selects from; "
                "selection has nothing to improve without one"
            )
        if not design.base_expectancy_is_a_kill_rule:
            return (
                "the base population's expectancy must be a declared kill rule — "
                "selecting inside a negative base is how a filter manufactures a curve"
            )
    if role is ModelRole.HORIZON_SELECTION and len(design.candidate_horizons) < 2:
        return "a horizon-selection model needs at least two horizons to select between"
    if role is ModelRole.REGIME_REPRESENTATION:
        if not design.downstream_consumer or design.consumer_annual_ir is None:
            return (
                "a representation is worth nothing on its own; it must name the consumer "
                "whose information ratio its capacity budget is charged against"
            )
        if not design.ablation:
            return "a representation must declare the ablation that isolates its contribution"
        if design.consumer_effective_parameters <= 0:
            return (
                "a representation must declare the consumer's own effective parameters; "
                "the pair is fitted on one corpus and is charged one capacity budget"
            )
    if role is ModelRole.PORTFOLIO_ALLOCATION and not design.parent_candidate:
        return (
            "a portfolio allocator needs an underlying signal that has itself survived; "
            "allocation does not rescue a negative edge"
        )
    if role is ModelRole.EXECUTION_MANAGEMENT and not design.measures_cost_not_edge:
        return (
            "execution management measures the cost of acting, not an expected return; "
            "a candidate that claims otherwise is a direction generator in disguise"
        )
    if not design.leakage_controls:
        return "no leakage controls declared"
    return None


def assess(design: ModelDesign) -> dict[str, Any]:
    """Role prerequisites, then economics, then the two budgets."""
    record: dict[str, Any] = {
        "candidate_id": design.candidate_id,
        "role": design.role.value,
        "target": design.target,
        "horizon": design.horizon,
        "model_class": design.model_class,
        "feature_families": list(design.feature_families),
        "prior_research_overlap": design.prior_research_overlap,
        "why_different_from_round_1": design.why_different_from_round_1,
        "expected_information_gain": design.expected_information_gain,
    }

    if design.gate_family:
        try:
            assert_prospective(design.gate_family)
        except RetroactiveApplicationError as refusal:
            return {
                **record,
                "verdict": Verdict.PRIOR_FAMILY_CLOSED.value,
                "reason": str(refusal),
                "refused_by": "assert_prospective",
                "gate_family": design.gate_family,
            }

    repeat = _forbidden_repeat(design)
    if repeat is not None:
        return {
            **record,
            "verdict": Verdict.FORBIDDEN_REPEAT_OF_A_CLOSED_SHAPE.value,
            "reason": repeat,
        }

    missing = _role_prerequisite(design)
    if missing is not None:
        return {**record, "verdict": Verdict.ROLE_PREREQUISITE_MISSING.value, "reason": missing}

    #: A representation's capacity is charged against the ratio of the thing that
    #: will consume it, and an execution study is not required to clear a return
    #: hurdle it never claimed.
    if design.role is ModelRole.REGIME_REPRESENTATION:
        target_ir = float(design.consumer_annual_ir or 0.0)
        required = target_ir
        economic_ok = 0.0 < target_ir <= MAX_PLAUSIBLE_GROSS_IR
    elif design.role is ModelRole.EXECUTION_MANAGEMENT:
        target_ir = MAX_PLAUSIBLE_GROSS_IR
        required = 0.0
        economic_ok = True
    else:
        required = required_gross_annual_ir(design)
        target_ir = min(required, MAX_PLAUSIBLE_GROSS_IR)
        economic_ok = required <= MAX_PLAUSIBLE_GROSS_IR

    record["economics"] = {
        "annual_cost_bp": round(design.turnover_per_year * design.roundtrip_cost_bp, 1),
        "annual_vol_bp": design.annual_vol_bp,
        "required_gross_annual_ir": round(required, 3),
        "plausibility_ceiling": MAX_PLAUSIBLE_GROSS_IR,
        "ok": economic_ok,
    }
    if not economic_ok:
        return {
            **record,
            "verdict": Verdict.ECONOMICALLY_UNREACHABLE.value,
            "reason": (
                f"clearing {MIN_ANNUAL_NET_RETURN_BP:.0f} bp a year net of "
                f"{record['economics']['annual_cost_bp']} bp of cost needs a gross annual "
                f"information ratio of {required:.2f}, above the frozen ceiling "
                f"{MAX_PLAUSIBLE_GROSS_IR}"
            ),
        }

    parameters = budget_module.effective_parameters(design.model_class, **design.model_settings)
    if design.role is ModelRole.REGIME_REPRESENTATION:
        parameters += design.consumer_effective_parameters
    verdict = budget_module.assess(
        target_annual_ir=target_ir,
        declared_effective_parameters=parameters,
        declared_configurations=design.nominal_configurations,
        validation_years=design.validation_years,
    )
    record["budgets"] = verdict.as_dict()
    if verdict.binding == "capacity":
        outcome = Verdict.CAPACITY_EXCEEDED
    elif verdict.binding == "search":
        outcome = Verdict.SEARCH_BUDGET_EXCEEDED
    else:
        outcome = Verdict.DEVELOPMENT_ADMISSIBLE
    record["verdict"] = outcome.value
    if outcome is not Verdict.DEVELOPMENT_ADMISSIBLE:
        record["reason"] = (
            f"{verdict.binding} budget: "
            f"{verdict.capacity_declared_parameters:.2f} effective parameters against "
            f"{verdict.capacity_admissible_parameters:.2f} admissible, and "
            f"{verdict.search_declared_configurations} configurations against "
            f"{verdict.search_admissible_configurations} admissible"
        )
    return record


def hurdle_table(
    roundtrip_cost_bp: float, annual_vol_bp: float = DEFAULT_ANNUAL_VOL_BP
) -> dict[str, Any]:
    """⭐ What each rebalancing frequency demands, and what capacity it buys.

    Signal-free arithmetic over the frozen constants. It is the clearest statement
    of the trade this phase is working inside: a faster design needs a larger
    information ratio, and the larger ratio is the only thing that enlarges its
    parameter budget.
    """
    rows: dict[str, Any] = {}
    for name, turnover in (
        ("monthly", 12.0),
        ("fortnightly", 26.0),
        ("weekly", 52.0),
        ("twice_weekly", 104.0),
        ("daily", 252.0),
    ):
        cost = turnover * roundtrip_cost_bp
        required = (MIN_ANNUAL_NET_RETURN_BP + cost) / annual_vol_bp
        reachable = required <= MAX_PLAUSIBLE_GROSS_IR
        rows[name] = {
            "turnover_per_year": turnover,
            "annual_cost_bp": round(cost, 1),
            "required_gross_annual_ir": round(required, 3),
            "reachable": reachable,
            "admissible_effective_parameters": (
                round(budget_module.admissible_parameters(min(required, MAX_PLAUSIBLE_GROSS_IR)), 3)
                if reachable
                else 0.0
            ),
        }
    return {
        "roundtrip_cost_bp": roundtrip_cost_bp,
        "annual_vol_bp": annual_vol_bp,
        "minimum_annual_net_bp": MIN_ANNUAL_NET_RETURN_BP,
        "frequencies": rows,
    }


__all__ = [
    "DEFAULT_ANNUAL_VOL_BP",
    "HIGH_CAPACITY_PARAMETERS",
    "MAX_ANNUAL_VOL_BP",
    "TEMPORAL_ARCHITECTURES",
    "ModelDesign",
    "Verdict",
    "assess",
    "hurdle_table",
    "required_gross_annual_ir",
]
