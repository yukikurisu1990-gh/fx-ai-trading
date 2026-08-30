"""Where the ``EXPLORATORY_OOS_SLICE`` begins, by calendar arithmetic alone.

R-2 fixed the slice's **shape** — "the final contiguous portion of the design
span" — and its **timing** — the boundary is "chosen and recorded before stage
R1".  It fixed no size, so until the ruling recorded below there was no date,
and `docs/design/m15_track_a_r1_read_authorization.md` refused to invent one.

The ruling, recorded 2026-08-30 as a human + ChatGPT decision:

    `EXPLORATORY_OOS_SLICE_RULED_AS_FINAL_TWENTY_PERCENT_OF_COMMITTED_DESIGN_UTC_DATES`

    * the unit is the **UTC calendar date**;
    * the population is the **committed DESIGN span only**;
    * ``tail = ceil(0.20 x number_of_design_dates)``;
    * the tail is **contiguous** and ends on the last design date;
    * **no weekday or market-day snapping** — a calendar date is a calendar date;
    * computed **without looking at any price, outcome or metric**;
    * the slice is the **N = 1** exploratory OOS (:mod:`.oos_budget`);
    * it is **separate** from every ordinary development read;
    * once read it is **not reused**.

**A human chose the fraction; no human chose a date.**  That separation is the
whole point of putting this in code: `0.20` is a number someone can argue about
before any data exists, while `2025-12-29` is a consequence.  Nothing here reads
a file, a price or an environment variable, so the dates cannot drift with the
data, the host or the clock.

Why a fraction of dates and not of bars
---------------------------------------

Bars are a property of the data; dates are a property of the calendar.  Sizing
the slice in bars would mean counting rows, and counting rows in the design span
means reading it — which is what stage R1 has not been authorised to do.  Dates
are derivable from two committed constants and nothing else.

Why no market-day snapping
--------------------------

Snapping to trading days needs a market calendar, and a market calendar is an
authority this module would have to consult and this programme would then have
to freeze.  §3.7's calendar semantics are already
``CALENDAR_UTC_DATES_NO_MARKET_HOURS``; a weekend inside the tail costs a little
tail data and introduces nothing.

The arithmetic is integer, not floating point
---------------------------------------------

``ceil(0.20 * 310)`` in binary floating point is not obviously 62, and a
boundary that depends on the rounding of ``0.2`` is a boundary nobody can check
by hand.  ``-(-n * 20 // 100)`` is exact integer ceiling division and gives the
same answer for every ``n`` the ruling could ever be applied to.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Final

from scripts.m15_gate3a.no_overlap import DESIGN_END, DESIGN_START


class OosSliceError(RuntimeError):
    """A read whose interval reaches into the quarantined slice."""


#: The ruled fraction, as an exact integer ratio.  A human + ChatGPT decision.
OOS_TAIL_NUMERATOR: Final[int] = 20
OOS_TAIL_DENOMINATOR: Final[int] = 100

#: The ruling's own name, for reports and grant records.
RULING_TOKEN: Final[str] = (
    "EXPLORATORY_OOS_SLICE_RULED_AS_FINAL_TWENTY_PERCENT_OF_COMMITTED_DESIGN_UTC_DATES"
)

#: The committed design span, as calendar dates.  Taken from ``no_overlap``, the
#: single authority for the span, rather than restated here.
DESIGN_START_DATE: Final[date] = DESIGN_START.date()
DESIGN_END_DATE: Final[date] = DESIGN_END.date()

#: Inclusive, so the last design date counts.  310 for the committed span, which
#: is the same ``N_design_dates`` the pre-registration's 25%-prefix ruling
#: (§8.8) arrived at independently — a cross-check on the counting convention,
#: not a second authority for it.
DESIGN_DATE_COUNT: Final[int] = (DESIGN_END_DATE - DESIGN_START_DATE).days + 1

#: ``ceil(0.20 x DESIGN_DATE_COUNT)`` by exact integer arithmetic.
OOS_TAIL_DATE_COUNT: Final[int] = -(-DESIGN_DATE_COUNT * OOS_TAIL_NUMERATOR // OOS_TAIL_DENOMINATOR)

#: The quarantined tail.  ``SLICE_END`` is the design span's own last date: the
#: slice is a *final* portion, so it cannot end anywhere else.
SLICE_END_DATE: Final[date] = DESIGN_END_DATE
SLICE_START_DATE: Final[date] = SLICE_END_DATE - timedelta(days=OOS_TAIL_DATE_COUNT - 1)

#: Where an ordinary Track A development read has to stop: the day before the
#: slice.  Not "the slice minus a purge" — the purge R-2 requires is a *training*
#: exclusion measured in M15 bars, and dropping bars from training is a stage
#: that happens after this read, on data this read has already returned. Cutting
#: it out here would silently make the development corpus smaller than the
#: corpus the purge is defined against.
DEVELOPMENT_START_DATE: Final[date] = DESIGN_START_DATE
DEVELOPMENT_END_DATE: Final[date] = SLICE_START_DATE - timedelta(days=1)

#: The same four dates as ISO strings, which is the shape a ``ReadGrant`` and a
#: ``ReadRequest`` take.
DEVELOPMENT_START_UTC: Final[str] = DEVELOPMENT_START_DATE.isoformat()
DEVELOPMENT_END_UTC: Final[str] = DEVELOPMENT_END_DATE.isoformat()
SLICE_START_UTC: Final[str] = SLICE_START_DATE.isoformat()
SLICE_END_UTC: Final[str] = SLICE_END_DATE.isoformat()


def _as_date(value: datetime | date) -> date:
    """A ``date`` from either, without letting a naive datetime through.

    ``datetime`` is a ``date`` subclass, so an ``isinstance`` test in the wrong
    order silently accepts one — the shape that produced F-1 in an earlier
    round. The datetime branch is therefore tested **first**, and a naive one is
    refused rather than read in whatever timezone the host happens to be in.
    """
    if isinstance(value, datetime):
        if value.utcoffset() is None:
            raise OosSliceError(
                f"a naive datetime has no UTC date: {value!r}. Reinterpreting it in the "
                "host timezone is how a bar moves across a boundary."
            )
        return value.date()
    if type(value) is date:
        return value
    raise OosSliceError(f"expected a date or an aware datetime, got {type(value).__name__}")


def is_slice_date(value: datetime | date) -> bool:
    """True if this UTC calendar date is inside the quarantined slice."""
    day = _as_date(value)
    return SLICE_START_DATE <= day <= SLICE_END_DATE


def assert_clear_of_slice(
    span_start_utc: datetime | date, span_end_utc: datetime | date, *, what: str
) -> None:
    """Refuse an interval that touches the slice by so much as one date.

    R-2 quarantines the slice from **describing, plotting or computing a
    statistic over it**, descriptive statistics included, until R4. Returning
    its bars to a caller is upstream of all three, so this refuses rather than
    trimming: a read silently shortened to the development span would leave the
    caller believing it had asked for something it did not get.
    """
    lo = _as_date(span_start_utc)
    hi = _as_date(span_end_utc)
    if lo > hi:
        raise OosSliceError(f"{what}: {lo} is after {hi}")
    if hi < SLICE_START_DATE:
        return
    raise OosSliceError(
        f"{what}: {lo}..{hi} reaches into the EXPLORATORY_OOS_SLICE "
        f"({SLICE_START_UTC}..{SLICE_END_UTC}). R-2 quarantines the slice from every stage "
        "before R4, and reading it is a separate closed operation "
        "(track_a_exploratory_oos_slice_read) with its own grant and an N = 1 budget. "
        f"An ordinary development read stops at {DEVELOPMENT_END_UTC}."
    )


__all__ = [
    "DESIGN_DATE_COUNT",
    "DESIGN_END_DATE",
    "DESIGN_START_DATE",
    "DEVELOPMENT_END_DATE",
    "DEVELOPMENT_END_UTC",
    "DEVELOPMENT_START_DATE",
    "DEVELOPMENT_START_UTC",
    "OOS_TAIL_DATE_COUNT",
    "OOS_TAIL_DENOMINATOR",
    "OOS_TAIL_NUMERATOR",
    "RULING_TOKEN",
    "SLICE_END_DATE",
    "SLICE_END_UTC",
    "SLICE_START_DATE",
    "SLICE_START_UTC",
    "OosSliceError",
    "assert_clear_of_slice",
    "is_slice_date",
]
