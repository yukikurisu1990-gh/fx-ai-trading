"""Track T-V: is a currency that is cheap in real terms cheap for a reason?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Authority: the Human + ChatGPT ruling of 2026-09-18. T-V is a genuinely different
source from the rate tracks — slow, fundamental, and low-turnover by design rather
than by tuning — and it is the first work in this programme to read public FX
history from before 2016.

The order is fixed and the reason is the whole point: `prereg` is frozen and
committed **before** `acquire` requests a single FX observation, and every request
ends the day before the protected pool begins, so the exclusion is a property of
the request rather than of a filter applied afterwards.

Once read, that span is `EXPLORATORY_SEEN_DEVELOPMENT_DATA` and can never serve as
confirmation. The fresh pool, the historical OOS slice, the dead window and the
forward epoch are not touched by anything here.
"""

from __future__ import annotations

from typing import Final

TRACK: Final[str] = "T-V"
#: Adopted by the Human + ChatGPT ruling of 2026-09-19 §5, which took the development
#: result as the track's authoritative status. The cause is signal content, not cost:
#: the pre-registered incremental IC over the nominal control was -5.57 percentage
#: points at Newey-West t -3.34. An earlier state of this line still read
#: DEVELOPMENT_IN_PROGRESS after the same ruling had finalised the sibling tracks.
WORKFLOW_STATUS: Final[str] = "REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT"

OUTCOMES: Final[tuple[str, ...]] = (
    "REAL_EXCHANGE_RATE_VALUATION_DEVELOPMENT_CANDIDATE",
    "REAL_EXCHANGE_RATE_VALUATION_MARGINAL_DEVELOPMENT_CANDIDATE",
    "REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT",
    "REAL_EXCHANGE_RATE_VALUATION_DATA_NOT_DECISION_GRADE",
)

#: Acquired series land here, git-ignored like every other acquired dataset; the
#: committed record of what was acquired is the provenance artefact.
DATA_DIR: Final[str] = "artifacts/track_a_scratch/valuation"
RECORD_DIR: Final[str] = "artifacts/research/valuation"

__all__ = ["DATA_DIR", "OUTCOMES", "RECORD_DIR", "TRACK", "WORKFLOW_STATUS"]
