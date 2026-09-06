"""Round A — the Tradability Atlas and the Conditional Sign Screen.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Nothing in this package is evidence. It selects no candidate, produces no Formal
Confirmation input, and reads no market data of its own: it loads the three M15
parquet caches the earlier rounds already built, and nothing else. The fresh
internal replication pool `2016-06-02 … 2021-04-25`, the `EXPLORATORY_OOS_SLICE`,
the dead window and the forward epoch are all unreachable from here — this
package contains no reader and no span guard, because it opens no archive.

Why a separate package rather than more files in `exploratory_m15`
------------------------------------------------------------------

`exploratory_m15` is the *strategy* package: it carries three reader routes, three
span guards, the frozen reversal and momentum candidates and the engine those
candidates are scored with. Round A is descriptive — it measures the opportunity
set and screens conditional structure, and it must not be able to open a file.
Keeping it out of that package is what makes "Round A performs no read" a
property of the code rather than a promise in a document.

It imports `exploratory_m15` for the cached panels and for the indicator and
inference functions the earlier rounds established, and adds nothing to the
fingerprint surface (`scripts/research/**` is outside it).
"""

from __future__ import annotations

from typing import Final

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

#: The three already-seen panels, oldest first. `momentum` is the least
#: contaminated by earlier searching and `development` the most: every round of
#: this programme searched 2025, so §2 of the plan forbids it from being a
#: deciding vote.
PANELS: Final[tuple[str, ...]] = (
    "momentum_2021_2023",
    "supplemental_2023_2025",
    "development_2025",
)

#: The two spans a structural candidate must agree on. 2025 is corroboration.
DECIDING_PANELS: Final[tuple[str, ...]] = ("momentum_2021_2023", "supplemental_2023_2025")

__all__ = [
    "CLASSIFICATION",
    "CLASSIFICATION_SECONDARY",
    "DECIDING_PANELS",
    "PANELS",
]
