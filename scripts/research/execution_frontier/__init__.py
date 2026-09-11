"""Track 3 — the offline execution frontier.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

The question
------------

Cost is an **input** to the feasibility frontier, not a nuisance term beside it.
The unit audit showed the feasible band is quadratic in `1/cost`: halving what a
round trip costs widens the set of testable designs fourfold, and no improvement
to a signal can do the same. So this package measures execution before any
hypothesis is pre-registered, because freezing a candidate universe against an
obsolete cost assumption is the failure mode the sequencing decision exists to
avoid.

> Under realistic passive or improved execution, how far can the round-trip
> retail cost hurdle be lowered on the two already-seen deciding panels?

What this is not
----------------

**Not alpha discovery.** Directions are drawn from a generator, exactly as the
frontier does, so there is no signal-to-return relation for this package to find
and nothing here can be read as an edge. What is measured is a property of
execution.

**Not a broker claim.** Every number here comes from M15 bid/ask bars replayed
offline. Queue position, quote withdrawal, latency, broker fill logic, hidden
liquidity and partial fills are not observable in that data, so a simulated
`C'` bounds what execution *could* give and does not establish what a broker
*would* give. The prohibited status is
`BROKER_REALIZABLE_COST_REDUCTION_ESTABLISHED`; the permitted one is
`SIMULATED_EXECUTION_COST_BOUND_ESTABLISHED`.

**No new route to data.** This package holds no archive path. It loads the two
deciding panels through `round_a.panels`, whose loaders carry their own span
guards, and it can therefore no more reach the fresh pool, the OOS slice, the
dead window or the forward epoch than `clock_flow` can.

The three policies
------------------

`P0` crosses immediately and is the baseline `C`. `P2` rests a limit at the near
touch and crosses if it has not filled, so **every decision trades** and its mean
is comparable to `P0` over the same population — that is `C'`, and it is the one
the success bands are applied to. `P1` rests the same limit and cancels, which
makes its mean conditional on the market having come to the order; it is a
diagnostic reported beside its fill rate, never a band metric.

Everything in this module was fixed in
`docs/research/m15_track_3_execution_prereg.md` before the first measurement
existed.
"""

from __future__ import annotations

from typing import Final

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

#: How long a passive order rests before the policy crosses. Four M15 bars is one
#: hour, the same window every clock cell in Track 1 measures over.
WAIT_BARS: Final[int] = 4

#: How far the opposing side must trade **through** a resting limit before this
#: model grants a fill. A touch is not a fill: at a touch the order may sit
#: behind a queue this data cannot see, so penetration stands in for the queue
#: having been consumed.
PENETRATION_PIPS: Final[float] = 1.0

#: Horizon for the post-fill adverse-movement diagnostic, in bars.
DRIFT_BARS: Final[int] = 4

#: The primary cell, and the sensitivities declared in advance so that reporting
#: them is an obligation rather than a choice made after seeing the primary.
PRIMARY_RULE: Final[tuple[int, float]] = (WAIT_BARS, PENETRATION_PIPS)
WAIT_BARS_SENSITIVITY: Final[tuple[int, ...]] = (1, 2, 4, 8)
PENETRATION_SENSITIVITY: Final[tuple[float, ...]] = (0.5, 1.0, 2.0)

#: `C' / C` bands, fixed before the measurement. The worse band governs when the
#: two deciding panels disagree.
SUCCESS_BANDS: Final[tuple[tuple[str, float], ...]] = (
    ("strong", 0.60),
    ("material", 0.70),
    ("modest", 0.85),
)
WEAK_BAND: Final[str] = "weak"

#: The statuses this stage is permitted to reach, and the one it is not.
STATUS_SIMULATED: Final[str] = "SIMULATED_EXECUTION_COST_BOUND_ESTABLISHED"
STATUS_FRONTIER: Final[str] = "OFFLINE_EXECUTION_FRONTIER_ESTIMATED"
PROHIBITED_STATUS: Final[str] = "BROKER_REALIZABLE_COST_REDUCTION_ESTABLISHED"


def band_for(ratio: float) -> str:
    """Which pre-registered band a `C' / C` ratio falls in.

    Written as a lookup over `SUCCESS_BANDS` rather than a chain of literals so
    that the thresholds live in exactly one place and a test can prove the
    boundaries are inclusive on the side the pre-registration says they are.
    """
    for name, ceiling in SUCCESS_BANDS:
        if ratio <= ceiling:
            return name
    return WEAK_BAND


__all__ = [
    "CLASSIFICATION",
    "CLASSIFICATION_SECONDARY",
    "DRIFT_BARS",
    "PENETRATION_PIPS",
    "PENETRATION_SENSITIVITY",
    "PRIMARY_RULE",
    "PROHIBITED_STATUS",
    "STATUS_FRONTIER",
    "STATUS_SIMULATED",
    "SUCCESS_BANDS",
    "WAIT_BARS",
    "WAIT_BARS_SENSITIVITY",
    "WEAK_BAND",
    "band_for",
]
