"""A feasibility gate per model **role**, because one gate cannot fit all of them.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The decision is explicit that the five-condition gate built for a direction
generator must not be applied mechanically to every use of a model. A ranking
model, a trade/skip filter, a regime representation and a portfolio allocator
fail in different ways, so they are gated on different prerequisites — with two
budgets and one economic condition shared by all of them.

The economic condition, after two reviews took it apart
-------------------------------------------------------

An earlier version computed the target ratio from the design's own hurdle:

    required_gross_IR = (min_annual_net_bp + turnover * roundtrip_bp) / annual_vol_bp

and fed it straight into the capacity budget. Three things were wrong with that,
and two independent reviews found them from opposite directions.

* **The units did not match.** `roundtrip_bp` is bp of gross leg notional;
  `annual_vol_bp` was a *declared* 800 bp of levered capital. The measured
  volatility of the book this phase actually trades — four currencies long, four
  short, one unit of gross, no optimisation — is **377.7 bp**, so the ratio
  flattered every design by about 2.1×. Levering to 800 levers the cost by the
  same factor, which is why the corrected hurdle carries no leverage term at all.
* **Capacity grew with transaction cost.** `admissible_parameters` scales with
  `IR^2`, so a design that got *cheaper* needed a smaller ratio and was allowed a
  *smaller* model. That is the Gate v1 inversion this programme built Gate v2 to
  remove, reintroduced here and frozen by a passing test.
* **The 300 bp minimum net return is not a statement about a ratio.** At a given
  information ratio it is a statement about **leverage**, and it is reported as
  one.

So the hurdle is now `turnover * roundtrip_bp / vol_per_gross` — what the design
must clear to pay for its own trading — and capacity is charged at the ratio the
design declares it can **achieve**, on the **shortest fold's** training window
rather than the whole corpus. ⭐ At the measured volatility a daily currency book
needs a gross annual ratio of **2.27** before it earns a basis point, against a
frozen ceiling of 1.5.

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

#: ⭐ **Measured**, per unit of gross notional, on the seen corpus: the annualised
#: volatility of a fixed long-short currency book — four currencies at +0.25 and
#: four at −0.25, assigned alphabetically, no optimisation and no signal — is
#: 377.7 bp. Per span it runs 370 to 430.
#:
#: An earlier version of this file **declared** 800 bp and called it a design
#: choice. Two independent reviews arrived at the same defect from opposite
#: directions: the cost term is denominated in bp of gross leg notional and the
#: volatility term was denominated in bp of levered capital, so the ratio compared
#: unlike quantities and flattered every design by roughly 2.1×. Levering the book
#: to 800 bp levers its cost by the same factor, so leverage cancels and cannot
#: rescue anything — which is why the hurdle below is expressed per unit of gross
#: and carries no leverage term at all.
MEASURED_ANNUAL_VOL_PER_GROSS_BP: Final[float] = 377.7
MEASURED_VOL_RANGE_BY_SPAN_BP: Final[tuple[float, float]] = (370.0, 430.0)

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
    annual_vol_per_gross_bp: float = MEASURED_ANNUAL_VOL_PER_GROSS_BP
    #: ⭐ The annual information ratio this design claims it could **achieve**,
    #: declared and defended rather than derived from what it needs. Bounded by the
    #: frozen plausibility ceiling. Deriving it from the cost hurdle — which an
    #: earlier version did — makes the capacity budget grow with transaction cost.
    assumed_achievable_annual_ir: float = 0.5
    #: The shortest training window any fold will have. The capacity budget is
    #: charged against this rather than against the corpus.
    shortest_fold_train_years: float = 1.5
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


def break_even_annual_ir(design: ModelDesign) -> float:
    """⭐ The gross ratio that pays for the trading and nothing else.

    `turnover * roundtrip_bp / vol_per_gross`, both terms per unit of **gross
    notional**, so leverage cancels exactly — as it must, because an information
    ratio is scale-free. The previous formula added a 300 bp minimum net return to
    the numerator and divided by a levered volatility, which is neither scale-free
    nor dimensionally consistent.

    The 300 bp minimum has not been dropped; it has been moved to where it belongs.
    At a given ratio it is a statement about **leverage** — how much gross notional
    a unit of capital must carry to earn 3% net — not about the ratio, and
    `leverage_needed_for_the_minimum_return` reports it separately.
    """
    if design.annual_vol_per_gross_bp <= 0:
        raise ValueError("a book with no volatility has no information ratio")
    annual_cost_bp = design.turnover_per_year * design.roundtrip_cost_bp
    return annual_cost_bp / design.annual_vol_per_gross_bp


def leverage_needed_for_the_minimum_return(design: ModelDesign, achieved_ir: float) -> float:
    """Gross notional per unit of capital to turn `achieved_ir` into 300 bp a year."""
    net_per_gross = (
        achieved_ir * design.annual_vol_per_gross_bp
        - design.turnover_per_year * design.roundtrip_cost_bp
    )
    if net_per_gross <= 0:
        return float("inf")
    return MIN_ANNUAL_NET_RETURN_BP / net_per_gross


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

    #: Capacity is charged at the ratio the design claims it can **achieve**; a
    #: representation borrows its consumer's, and an execution study is charged
    #: against the parent whose cost it is trying to reduce rather than being
    #: handed the ceiling for free.
    achievable = float(design.assumed_achievable_annual_ir)
    if design.role is ModelRole.REGIME_REPRESENTATION:
        achievable = float(design.consumer_annual_ir or 0.0)
    if achievable <= 0.0 or achievable > MAX_PLAUSIBLE_GROSS_IR:
        return {
            **record,
            "verdict": Verdict.ECONOMICALLY_UNREACHABLE.value,
            "reason": (
                f"an assumed achievable annual information ratio of {achievable} is "
                f"outside (0, {MAX_PLAUSIBLE_GROSS_IR}]"
            ),
        }

    break_even = (
        0.0 if design.role is ModelRole.EXECUTION_MANAGEMENT else (break_even_annual_ir(design))
    )
    economic_ok = break_even <= achievable
    record["economics"] = {
        "annual_cost_bp": round(design.turnover_per_year * design.roundtrip_cost_bp, 1),
        "annual_vol_per_gross_bp": design.annual_vol_per_gross_bp,
        "break_even_annual_ir": round(break_even, 3),
        "assumed_achievable_annual_ir": achievable,
        "leverage_for_the_minimum_net_return": round(
            leverage_needed_for_the_minimum_return(design, achievable), 3
        ),
        "plausibility_ceiling": MAX_PLAUSIBLE_GROSS_IR,
        "ok": economic_ok,
    }
    if not economic_ok:
        return {
            **record,
            "verdict": Verdict.ECONOMICALLY_UNREACHABLE.value,
            "reason": (
                f"paying {record['economics']['annual_cost_bp']} bp of cost a year against "
                f"{design.annual_vol_per_gross_bp} bp of volatility per unit of gross needs a "
                f"gross annual information ratio of {break_even:.2f} before a single basis "
                f"point is earned, against an assumed achievable {achievable}"
            ),
        }

    parameters = budget_module.effective_parameters(design.model_class, **design.model_settings)
    if design.role is ModelRole.REGIME_REPRESENTATION:
        parameters += design.consumer_effective_parameters
    #: ⭐ The shortest fold's training window, not the corpus. An expanding
    #: walk-forward fits its first model on `initial_train_years`, and charging
    #: optimism against 4.674 years spends years that fold does not have.
    verdict = budget_module.assess(
        target_annual_ir=achievable,
        declared_effective_parameters=parameters,
        declared_configurations=design.nominal_configurations,
        train_years=design.shortest_fold_train_years,
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
    roundtrip_cost_bp: float,
    annual_vol_per_gross_bp: float = MEASURED_ANNUAL_VOL_PER_GROSS_BP,
    *,
    achievable_annual_ir: float = MAX_PLAUSIBLE_GROSS_IR,
    shortest_fold_train_years: float = 1.5,
) -> dict[str, Any]:
    """⭐ What each rebalancing frequency costs before it earns anything.

    Signal-free arithmetic over the measured volatility and the frozen cost. The
    break-even ratio is what the design must clear to pay for its own trading; the
    parameter budget is charged at the **achievable** ratio and does not move with
    it, which is the property an earlier version of this table did not have —
    there, making a design cheaper made it inadmissible.
    """
    rows: dict[str, Any] = {}
    capacity = budget_module.admissible_parameters(achievable_annual_ir, shortest_fold_train_years)
    for name, turnover in (
        ("monthly", 12.0),
        ("fortnightly", 26.0),
        ("weekly", 52.0),
        ("twice_weekly", 104.0),
        ("daily", 252.0),
    ):
        cost = turnover * roundtrip_cost_bp
        break_even = cost / annual_vol_per_gross_bp
        reachable = break_even <= achievable_annual_ir
        rows[name] = {
            "turnover_per_year": turnover,
            "annual_cost_bp": round(cost, 1),
            "break_even_annual_ir": round(break_even, 3),
            "reachable": reachable,
            "admissible_effective_parameters": round(capacity, 3) if reachable else 0.0,
        }
    return {
        "roundtrip_cost_bp": roundtrip_cost_bp,
        "annual_vol_per_gross_bp": annual_vol_per_gross_bp,
        "achievable_annual_ir": achievable_annual_ir,
        "shortest_fold_train_years": shortest_fold_train_years,
        "minimum_annual_net_bp_is_a_leverage_statement": MIN_ANNUAL_NET_RETURN_BP,
        "frequencies": rows,
    }


__all__ = [
    "MEASURED_ANNUAL_VOL_PER_GROSS_BP",
    "MEASURED_VOL_RANGE_BY_SPAN_BP",
    "HIGH_CAPACITY_PARAMETERS",
    "TEMPORAL_ARCHITECTURES",
    "ModelDesign",
    "Verdict",
    "assess",
    "hurdle_table",
    "break_even_annual_ir",
    "leverage_needed_for_the_minimum_return",
]
