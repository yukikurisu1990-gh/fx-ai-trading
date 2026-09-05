"""Track A exploratory strategy research over the seen M15 development corpus.

**`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.**

Nothing in this package is evidence. It produces no formal result, no candidate
selection, no Gate-3a input and nothing usable in a Formal Confirmation. It is
here to answer one exploratory question — *does M15 look like it has an
economic edge worth pursuing?* — over data that is already
`EXPLORATORY_SEEN_DATA`.

Why this is a separate package
------------------------------

`scripts/m15_track_a/` is the **gated R1 route**. It carries the read grant, the
seen-data ledger, the containment guards and the implementation fingerprint both
grants bind to. Running exploratory backtests through it would append to the
governance ledgers and re-declare a corpus that is already declared, and adding
files to it would move the fingerprint and void the grants.

So this package touches none of it. It is outside the fingerprint surface (a
test asserts that), it writes only to the exploratory scratch directory, and it
re-implements the M15 bucketing it needs rather than reaching into
`aggregate_m15` — which refuses real rows outside its own route, and whose
refusal is not something a research script should be routing around.

What that costs, stated: this package's M15 bars are **not** the gated route's
output. They are checked against R1's published per-pair bar counts, first and
last timestamps and complete/incomplete split, and the check is a test, not a
claim.

The boundary that still binds
-----------------------------

`2025-04-25 … 2025-12-28` only. `2025-12-29` onward is the
`EXPLORATORY_OOS_SLICE`, the dead window and the forward epoch follow it, and
none of the three is authorised. The loader refuses a span that reaches any of
them — not because a research script is untrusted, but because the cheapest
place to stop an accident is where the dates are parsed.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Final

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

#: The twenty pairs, and the pip-size rule, **copied rather than imported**.
#:
#: `scripts/m15_gate3a/` is pinned by
#: `test_the_package_has_no_reverse_caller_outside_itself_and_its_own_tests`:
#: nothing outside that package, its own tests and Track A's gated route may
#: import it. A research package is none of those, and the right response to a
#: committed prohibition is to stop importing, not to widen the allowlist. So
#: the universe and the pip size are restated here, and the restatement was
#: checked against `pair_authority.PAIRS_20` and `pip_size_for_pair` at the time
#: it was written: same twenty, and zero mismatches on the rule across all of
#: them. The cost of the copy is that a change to the authority does not reach
#: here; it is exploratory code and that is the cheaper of the two failures.
PAIRS: Final[tuple[str, ...]] = (
    "AUD_CAD",
    "AUD_JPY",
    "AUD_NZD",
    "AUD_USD",
    "CHF_JPY",
    "EUR_AUD",
    "EUR_CAD",
    "EUR_CHF",
    "EUR_GBP",
    "EUR_JPY",
    "EUR_USD",
    "GBP_AUD",
    "GBP_CHF",
    "GBP_JPY",
    "GBP_USD",
    "NZD_JPY",
    "NZD_USD",
    "USD_CAD",
    "USD_CHF",
    "USD_JPY",
)


def pip_size(pair: str) -> float:
    """0.01 for a JPY quote, 0.0001 otherwise. Verified against the authority."""
    if pair not in PAIRS:
        raise ValueError(f"{pair!r} is not one of the twenty registered pairs")
    return 0.01 if pair.endswith("_JPY") else 0.0001


_UTC_DATE: Final[re.Pattern[str]] = re.compile(r"\d{4}-\d{2}-\d{2}")


class MalformedUtcDateError(ValueError):
    """Raised when a span bound is not an exact `YYYY-MM-DD` UTC date.

    Both span guards compare bounds as **strings**, which is sound only for
    fixed-width dates. A truncated bound silently defeats them: `"2025"` sorts
    below `"2025-04-25"`, so it passes a `start < DEVELOPMENT_START_UTC` test,
    and a row stamp `"2025-12-29T…"` sorts below a `"2025T99"` sentinel because
    `-` (0x2D) precedes `T` (0x54) — so the row is decoded, and under
    `HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN` a decode is a read. An
    independent audit found this reachable through the public `end` keyword of
    both readers.

    The fix is to refuse the shape rather than to patch each comparison. Once a
    bound is known to be exactly `YYYY-MM-DD`, string order and date order
    coincide and every comparison downstream of it is sound again.
    """


def utc_date(value: str, *, field: str) -> date:
    """Parse an exact `YYYY-MM-DD` UTC date, refusing every other shape."""
    if not isinstance(value, str) or not _UTC_DATE.fullmatch(value):
        raise MalformedUtcDateError(
            f"{field}={value!r} is not an exact YYYY-MM-DD UTC date. Span bounds are "
            "compared as strings, and a bound of any other shape makes those "
            "comparisons unsound rather than merely wrong."
        )
    try:
        return date.fromisoformat(value)
    except ValueError as error:  # pragma: no cover - unreachable past the regex
        raise MalformedUtcDateError(f"{field}={value!r} is not a real date") from error


#: The span this package may touch, and the first date it may not.
DEVELOPMENT_START_UTC: Final[str] = "2025-04-25"
DEVELOPMENT_END_UTC: Final[str] = "2025-12-28"
FIRST_FORBIDDEN_UTC: Final[str] = "2025-12-29"

__all__ = [
    "CLASSIFICATION",
    "PAIRS",
    "CLASSIFICATION_SECONDARY",
    "DEVELOPMENT_END_UTC",
    "DEVELOPMENT_START_UTC",
    "FIRST_FORBIDDEN_UTC",
    "MalformedUtcDateError",
    "pip_size",
    "utc_date",
]
