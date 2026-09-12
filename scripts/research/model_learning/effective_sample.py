"""How many independent observations 4.674 years actually contains.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The decision asks that "there are a lot of M15 bars" never again stand in for a
sample size, and names seven reasons it does not: serial dependence, overlapping
forward returns, same-day correlation, currency dependence, regime persistence,
event clustering and cross-sectional dependence.

The reduction is computed as an explicit chain, each step labelled with whether
its factor is **measured** in this repository or **assumed**. Nothing is folded
into a single fudge factor, because a single factor cannot be argued with.

One thing to hold on to while reading it
----------------------------------------

⭐ Neither feasibility budget in `budgets.py` depends on any number in this
module. Both reduce to years. The effective count decides how noisy a *fold's*
economic statistics are, how many events a block contains, and whether a stated
metric can be read at all — it does not decide how many parameters may be fitted
or how many configurations may be tried. Two different questions, and this
programme has previously answered the second with the first.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from scripts.research.model_learning import (
    EFFECTIVE_INDEPENDENT_PAIRS,
    M15_ROWS_IN_THE_CORPUS,
    TRAIN_YEARS_TOTAL,
)

TRADING_DAYS_PER_YEAR: Final[float] = 252.0
CALENDAR_DAYS_PER_YEAR: Final[float] = 365.25

#: `effN / N` once a block bootstrap has absorbed the runs of correlated days
#: this corpus shows. An **assumption**, and a deliberately mild one: the
#: repository's own block-shift nulls lose roughly a fifth of their nominal count
#: at daily frequency, so 0.8 is used and the sensitivity is reported.
SERIAL_DEPENDENCE_RETENTION: Final[float] = 0.80

#: Event clustering — releases, meetings and month-ends arrive in bursts, so an
#: event-conditioned population has fewer independent occasions than dates.
#: Applied only to designs that declare an event population.
EVENT_CLUSTER_RETENTION: Final[float] = 0.75


@dataclass(frozen=True, slots=True)
class SampleDesign:
    """Everything the count depends on, all of it declared rather than measured."""

    entries_per_year_per_unit: float
    holding_days: float
    cross_sectional_units: int
    #: Effectively independent units. `PAIRS_20` measures 3.2 to 6.5 depending on
    #: the window and the statistic; a design that trades eight currency legs
    #: against each other declares its own.
    effective_units: float
    regime_persistence_days: float = 0.0
    event_conditioned: bool = False
    train_years: float = TRAIN_YEARS_TOTAL

    def __post_init__(self) -> None:
        if self.entries_per_year_per_unit <= 0:
            raise ValueError("a design with no entries has no sample")
        if self.holding_days <= 0:
            raise ValueError("a design with no holding period has no forward return")
        if self.effective_units <= 0 or self.effective_units > self.cross_sectional_units:
            raise ValueError(
                f"{self.effective_units} effective units out of "
                f"{self.cross_sectional_units} is not a dependence structure"
            )


def decompose(design: SampleDesign) -> dict[str, Any]:
    """The chain, step by step, with each factor's basis named."""
    nominal = design.entries_per_year_per_unit * design.cross_sectional_units

    #: 1. Overlap. Entries spaced more closely than the holding period share the
    #: same forward window, so the count of non-overlapping windows is capped by
    #: the holding period however often the design would like to enter.
    non_overlapping_per_year = min(
        design.entries_per_year_per_unit, CALENDAR_DAYS_PER_YEAR / design.holding_days
    )
    overlap_retention = non_overlapping_per_year / design.entries_per_year_per_unit

    #: 2. Same-day correlation and cross-sectional dependence are **one** step,
    #: not two. Collapsing a day's entries onto one occasion and then multiplying
    #: by an effective-unit ratio measured across those same days would charge
    #: the same dependence twice; the effective-unit count already answers "how
    #: many independent bets does one occasion carry".
    unit_retention = design.effective_units / design.cross_sectional_units

    #: 3. Serial dependence beyond the mechanical overlap.
    serial_retention = SERIAL_DEPENDENCE_RETENTION

    #: 4. Regime persistence. A conditioning state that lasts `R` days cannot
    #: deliver more independent *regime* observations than the span holds
    #: episodes of it, whatever the entry frequency inside one.
    if design.regime_persistence_days > 0:
        regime_cap_per_year = CALENDAR_DAYS_PER_YEAR / design.regime_persistence_days
        regime_retention = min(1.0, regime_cap_per_year / non_overlapping_per_year)
    else:
        regime_retention = 1.0

    #: 5. Event clustering, for designs whose population is an event calendar.
    event_retention = EVENT_CLUSTER_RETENTION if design.event_conditioned else 1.0

    per_year = (
        nominal
        * overlap_retention
        * unit_retention
        * serial_retention
        * regime_retention
        * event_retention
    )
    return {
        "nominal_rows_per_year": round(nominal, 2),
        "steps": {
            "_unit": "retention",
            "1_overlapping_forward_windows": round(overlap_retention, 4),
            "2_cross_sectional_and_same_day_dependence": round(unit_retention, 4),
            "3_serial_dependence_beyond_overlap": round(serial_retention, 4),
            "4_regime_persistence": round(regime_retention, 4),
            "5_event_clustering": round(event_retention, 4),
        },
        "basis": {
            "1_overlapping_forward_windows": "arithmetic",
            "2_cross_sectional_and_same_day_dependence": (
                "measured — 3.2 to 6.5 effective independent directions in PAIRS_20"
            ),
            "3_serial_dependence_beyond_overlap": "assumed, mild, sensitivity reported",
            "4_regime_persistence": "arithmetic, given the declared persistence",
            "5_event_clustering": "assumed where an event population is declared",
        },
        "effective_per_year": round(per_year, 2),
        "effective_total": round(per_year * design.train_years, 2),
        "train_years": design.train_years,
        "budgets_depend_on_this": False,
    }


def effective_n(design: SampleDesign) -> float:
    return float(decompose(design)["effective_total"])


def sensitivity(design: SampleDesign) -> dict[str, Any]:
    """What the two assumed factors are worth, so a reader can discount them.

    Both are retentions in `(0, 1]`, so the count scales linearly in each. The
    point of reporting it is that a candidate whose verdict flips between the
    optimistic and pessimistic ends is a candidate whose verdict is an
    assumption, and none of the verdicts in this phase does.
    """
    base = effective_n(design)
    optimistic = base / (
        SERIAL_DEPENDENCE_RETENTION * (EVENT_CLUSTER_RETENTION if design.event_conditioned else 1.0)
    )
    pessimistic = base * 0.5
    return {
        "effective_total": round(base, 2),
        "if_no_serial_or_event_penalty": round(optimistic, 2),
        "if_the_assumed_factors_are_twice_as_severe": round(pessimistic, 2),
        "span_ratio": round(optimistic / max(pessimistic, 1e-9), 3),
    }


def bars_are_not_a_sample() -> dict[str, Any]:
    """⭐ The comparison the decision asks be made explicit, in one table.

    A 1-day cross-sectional design over twenty pairs on M15 bars: 2,328,360
    nominal rows, and a few hundred effectively independent observations. The
    ratio is the number this programme has previously mistaken for statistical
    power.
    """
    design = SampleDesign(
        entries_per_year_per_unit=TRADING_DAYS_PER_YEAR,
        holding_days=1.0,
        cross_sectional_units=20,
        effective_units=min(EFFECTIVE_INDEPENDENT_PAIRS),
    )
    chain = decompose(design)
    m15_rows = M15_ROWS_IN_THE_CORPUS
    return {
        "m15_rows_in_the_corpus": m15_rows,
        "nominal_daily_rows": round(chain["nominal_rows_per_year"] * TRAIN_YEARS_TOTAL, 1),
        "effective_observations": chain["effective_total"],
        "bars_per_effective_observation": round(m15_rows / max(chain["effective_total"], 1e-9), 1),
        "capacity_budget_uses_years_not_this": True,
    }


__all__ = [
    "CALENDAR_DAYS_PER_YEAR",
    "EVENT_CLUSTER_RETENTION",
    "SERIAL_DEPENDENCE_RETENTION",
    "TRADING_DAYS_PER_YEAR",
    "SampleDesign",
    "bars_are_not_a_sample",
    "decompose",
    "effective_n",
    "sensitivity",
]
