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

Seen data decides nothing on its own: every outcome here is development
evidence. The fresh pool, the historical OOS slice, the dead window and the
forward epoch are not read.
"""

from __future__ import annotations

from typing import Final

TRACK: Final[str] = "T-R"
WORKFLOW_STATUS: Final[str] = "MARKET_YIELD_REPRICING_DEVELOPMENT_IN_PROGRESS"

#: The three outcomes the ruling allows this track to reach.
OUTCOMES: Final[tuple[str, ...]] = (
    "MARKET_YIELD_REPRICING_DEVELOPMENT_CANDIDATE",
    "MARKET_YIELD_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
    "MARKET_YIELD_REPRICING_DATA_NOT_DECISION_GRADE",
)

#: G10 currencies of the corpus, in the order the execution layer uses.
CURRENCIES: Final[tuple[str, ...]] = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")

#: Where acquired series land. Ignored by git, like every other acquired dataset;
#: the committed record of what was acquired is the provenance artefact.
DATA_DIR: Final[str] = "artifacts/track_a_scratch/market_yields"
RECORD_DIR: Final[str] = "artifacts/research/market_yields"

__all__ = ["CURRENCIES", "DATA_DIR", "OUTCOMES", "RECORD_DIR", "TRACK", "WORKFLOW_STATUS"]
