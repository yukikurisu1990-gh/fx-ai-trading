"""Economic Edge Source Expansion — frozen constants.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Every value here was fixed in
`docs/research/m15_economic_edge_source_expansion_plan.md` at `a36ab82`, **before
any external data was fetched**. None may be changed because of a result.

The package separates three layers and forbids the third from creating an edge:

* **A — expected return.** Why hold this side at all?
* **B — opportunity.** When is holding it worth the cost?
* **C — execution.** How is it held cheaply? *Never* where the edge comes from.
"""

from __future__ import annotations

from typing import Final

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

PLAN_COMMIT: Final[str] = "a36ab8274e4107c5fe272a0357d7f875235d6476"
BASE_MASTER: Final[str] = "cfe2f9499e7dac9d799fc1580be403830903d356"

SEED: Final[int] = 20260907

#: `PAIRS_20` spans exactly these eight. A source that cannot reach all of them
#: cannot serve, because a ranking over a subset silently changes the universe.
CURRENCIES: Final[tuple[str, ...]] = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")

# ------------------------------------------------------------------ the rule
#: Plan §5.1. Every rate is used at least one trading day after its own
#: effective date, so a decision cannot be taken on the bar that announced it.
RATE_LAG_TRADING_DAYS: Final[int] = 1
#: Plan §6. Carry accrues by **calendar** day, so a weekend accrues three. A
#: weekday-only accrual is wrong by about 40%.
DAYS_PER_YEAR: Final[float] = 365.0

# ------------------------------------------------------- signal families (§7)
#: C-A's dead-band, in percentage points of annual differential. Derived from
#: cost geometry rather than searched: below roughly this, a monthly rebalance
#: cannot accrue one round trip.
CARRY_DEAD_BAND_PCT: Final[float] = 0.25
#: C-B ranks the eight currencies and holds the top and bottom `k`.
CROSS_SECTIONAL_K: Final[tuple[int, ...]] = (2, 3)
#: C-C's lookback, matched to the rebalance rather than searched.
CARRY_CHANGE_LOOKBACK_REBALANCES: Final[int] = 3

# ------------------------------------------------------------- horizons (§8)
#: Rebalance frequencies, in M15 bars. 96 bars is one day.
REBALANCE_BARS: Final[dict[str, int]] = {
    "weekly": 5 * 96,
    "fortnightly": 10 * 96,
    "monthly": 21 * 96,
}

# ----------------------------------------------------------------- cost (§9)
COST_MULTIPLIERS: Final[tuple[float, ...]] = (1.0, 2.0)

# -------------------------------------------------------- opportunity (§13)
VOLUME_REPRESENTATIONS: Final[tuple[str, ...]] = (
    "normalised_level",
    "rolling_percentile",
    "shock",
    "change",
    "persistence",
)
#: Never sign. Tick volume has no direction information and a rule that appears
#: to find some is a bug.
OPPORTUNITY_TARGETS: Final[tuple[str, ...]] = (
    "future_absolute_return",
    "future_realised_volatility",
    "movement_exceeds_cost",
)

# ------------------------------------------------------ multiplicity (§18)
#: 4 carry families x 3 rebalances. This is the entire carry search.
CARRY_CELLS: Final[int] = 12
OPPORTUNITY_CELLS: Final[int] = len(VOLUME_REPRESENTATIONS) * len(OPPORTUNITY_TARGETS)

NULL_DRAWS: Final[int] = 200
STUDENTIZED_FLOOR: Final[float] = 2.0
FAMILYWISE_ALPHA: Final[float] = 0.05
#: Plan §11: the share of net the ten largest days may contribute.
TAIL_SHARE_CEILING: Final[float] = 0.50

__all__ = [
    "BASE_MASTER",
    "CARRY_CELLS",
    "CARRY_CHANGE_LOOKBACK_REBALANCES",
    "CARRY_DEAD_BAND_PCT",
    "CLASSIFICATION",
    "CLASSIFICATION_SECONDARY",
    "COST_MULTIPLIERS",
    "CROSS_SECTIONAL_K",
    "CURRENCIES",
    "DAYS_PER_YEAR",
    "FAMILYWISE_ALPHA",
    "NULL_DRAWS",
    "OPPORTUNITY_CELLS",
    "OPPORTUNITY_TARGETS",
    "PLAN_COMMIT",
    "RATE_LAG_TRADING_DAYS",
    "REBALANCE_BARS",
    "SEED",
    "STUDENTIZED_FLOOR",
    "TAIL_SHARE_CEILING",
    "VOLUME_REPRESENTATIONS",
]
