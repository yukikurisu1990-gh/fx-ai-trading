"""Track T-R: does market yield repricing lead G10 FX spot relative returns?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Authority: the Human + ChatGPT ruling of 2026-09-16, which approved D-2 (free,
public, non-FX data acquisition) and named T-R the first track to test.

What is new here is the **information**, not the architecture. H-016 closed the
policy rate — a step function the central bank sets. T-R asks about the price the
market puts on the policy path: the two-year sovereign yield, which moves every
day. The execution layer is Track 1's, reused; Track 1's alpha model is not.

The order is fixed by the ruling and by this package's modules:

1. `sources` — which official body publishes what, and what is reachable.
2. `acquire` — fetch and normalise, network only behind an explicit opt-in.
3. `integrity` — coverage, gaps, staleness, duplicates, ranges.
4. `availability` — when a yield could first have been traded on.
5. `coverage` — which currencies are decision-grade, decided before any signal.
6. `prereg` — frozen, then committed, before the yield panel meets the FX panel.
7. `development` — the unfitted rule, its FX-momentum control, and the residual.

The fast formulation returned `NOT_SUPPORTED`, and the ruling of 2026-09-18
authorised exactly one slow reformulation, which repeats the same order:

8. `portfolio` and `risk` — the execution layer and the margin stress, both closed
   inside whatever universe is actually tradable rather than inside all twenty pairs.
9. `fast_repair_check` — the frozen fast signal re-run through the repaired layer,
   so the slow run has a like-for-like comparator it did not choose after the fact.
10. `prereg_r2` — frozen and committed, digest-pinned, before the slow run.
11. `development_r2` — the twenty-day state, its control, the residual and the
    pre-registered leg decomposition.

Seen data decides nothing on its own: every outcome here is development
evidence. The fresh pool, the historical OOS slice, the dead window and the
forward epoch are not read.
"""

from __future__ import annotations

from typing import Final

TRACK: Final[str] = "T-R"
#: Both pre-registered formulations have run and both returned NOT_SUPPORTED. The
#: family boundary below is available for a Human decision and is not declared here.
WORKFLOW_STATUS: Final[str] = (
    "MARKET_YIELD_REPRICING_FAST_AND_SLOW_FORMULATIONS_BOTH_NOT_SUPPORTED_AWAITING_HUMAN_DECISION"
)

#: What each track may conclude. The fast statuses name the measure they belong to:
#: a formulation failing is not the family closing.
OUTCOMES: Final[tuple[str, ...]] = (
    "MARKET_YIELD_REPRICING_FAST_5D_MEASURE_DEVELOPMENT_CANDIDATE",
    "MARKET_YIELD_REPRICING_FAST_5D_MEASURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
    "MARKET_YIELD_REPRICING_FAST_5D_MEASURE_DATA_NOT_DECISION_GRADE",
    "MARKET_YIELD_SLOW_REPRICING_DEVELOPMENT_CANDIDATE",
    "MARKET_YIELD_SLOW_REPRICING_MARGINAL_DEVELOPMENT_CANDIDATE",
    "MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
    "MARKET_YIELD_SLOW_REPRICING_DATA_NOT_DECISION_GRADE",
)

#: Only with both the fast shock and the slow state unsupported, and never reaching
#: OIS, intraday rate futures, the market-implied policy path or curve non-linearities.
FAMILY_BOUNDARY: Final[str] = (
    "MARKET_YIELD_REPRICING_SIMPLE_DIRECTIONAL_FAMILY_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
)

#: G10 currencies of the corpus, in the order the execution layer uses.
CURRENCIES: Final[tuple[str, ...]] = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")

#: Where acquired series land. Ignored by git, like every other acquired dataset;
#: the committed record of what was acquired is the provenance artefact.
DATA_DIR: Final[str] = "artifacts/track_a_scratch/market_yields"
RECORD_DIR: Final[str] = "artifacts/research/market_yields"

__all__ = [
    "CURRENCIES",
    "DATA_DIR",
    "FAMILY_BOUNDARY",
    "OUTCOMES",
    "RECORD_DIR",
    "TRACK",
    "WORKFLOW_STATUS",
]
