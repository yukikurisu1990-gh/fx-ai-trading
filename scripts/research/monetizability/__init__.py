"""Is the Round B′ path structure monetizable? Frozen constants.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Every value here was fixed in `docs/research/m15_monetizability_package_plan.md`
at `40cbcd9`, **before the first statistic of this package was computed**. None
may be changed because of a result. A defect in an implementation is fixed and
recorded as a deviation; a threshold is never moved to change an outcome.

The one substantive change from Round B′ is the **primary statistic**. B′-2 used
the retrace *fraction*, which divides by the realised excursion — and real and
null anchors do not have the same excursions, so the fraction gave `z` up to
`+5.70` where the denominator-free version of the same quantity gave `z ≤ +1.96`.
The primary here is the σ-level absolute geometry (plan §5).
"""

from __future__ import annotations

from typing import Final

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

#: `docs/research/m15_monetizability_package_plan.md`, frozen before any statistic
PLAN_COMMIT: Final[str] = "40cbcd994c97a9c8ee7ab9058b1fca52a1ccbcaf"
BASE_MASTER: Final[str] = "a0858ecba4143037d4137da44ac66cf976b77b8e"

SEED: Final[int] = 20260907

# ----------------------------------------------------------------- Stage 1A
#: the Round B′ detector, unchanged. Three thresholds, and no more (plan §4).
EXCURSION_SIGMAS: Final[tuple[float, ...]] = (1.5, 2.0, 3.0)
#: plan §6 -- 200 minimum for every real comparison, bloc splits included. Round
#: B′ used 40 for B′-2 and its family-wise p was pinned at the 1/41 floor.
NULL_DRAWS: Final[int] = 200
#: the statistic the Stage 1A verdict reads (plan §5)
PRIMARY_STATISTIC: Final[str] = "median_retrace_sigma"
#: reported, never decisive -- it carries the excursion in its denominator
SECONDARY_STATISTIC: Final[str] = "median_retrace_fraction"
#: plan §7 clauses 2 and 3
STUDENTIZED_FLOOR: Final[float] = 2.0
FAMILYWISE_ALPHA: Final[float] = 0.05
#: plan §7 clause 4
TAIL_TRIM_DAYS: Final[int] = 10

# ----------------------------------------------------------------- Stage 1B
#: plan §9 -- the detector-free population, where B′-1's structure lives
BOUND_HORIZONS: Final[tuple[int, ...]] = (1, 4, 12, 48)
#: plan §3 -- reported at C and at 2C, always
COST_MULTIPLIERS: Final[tuple[float, ...]] = (1.0, 2.0)
#: plan §11 -- the economic gate, all four on both deciding panels
#: E1: perfect take/skip net per **opportunity** (skipped ones included)
ORACLE_NET_PER_EVENT_FLOOR_IN_COSTS: Final[float] = 0.5
#: E3: the share of net the ten largest days may contribute
TAIL_SHARE_CEILING: Final[float] = 0.50

# ----------------------------------------------------------------- Stage 1C
#: plan §14 -- redundant if volume is this well explained by what we already have
VOLUME_REDUNDANCY_R2: Final[float] = 0.80
#: the forward relations the residual is tested against
VOLUME_FORWARD_TARGETS: Final[tuple[str, ...]] = ("abs_next_return", "signed_next_return")

# ----------------------------------------------------------------- Stage 3
#: plan §19 condition 5, and §20
MIN_EVENTS_PER_FEATURE: Final[int] = 50
MAX_FEATURES: Final[int] = 20

__all__ = [
    "BASE_MASTER",
    "BOUND_HORIZONS",
    "CLASSIFICATION",
    "CLASSIFICATION_SECONDARY",
    "COST_MULTIPLIERS",
    "EXCURSION_SIGMAS",
    "FAMILYWISE_ALPHA",
    "MAX_FEATURES",
    "MIN_EVENTS_PER_FEATURE",
    "NULL_DRAWS",
    "ORACLE_NET_PER_EVENT_FLOOR_IN_COSTS",
    "PLAN_COMMIT",
    "PRIMARY_STATISTIC",
    "SECONDARY_STATISTIC",
    "SEED",
    "STUDENTIZED_FLOOR",
    "TAIL_SHARE_CEILING",
    "TAIL_TRIM_DAYS",
    "VOLUME_FORWARD_TARGETS",
    "VOLUME_REDUNDANCY_R2",
]
