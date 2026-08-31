"""The two session predicates R1 needs, and **only** what authority supplies.

This module replaces `calendar_build.py`, which is deleted. That module authored
a market calendar — a Sunday 22:00 → Friday 22:00 UTC trading week — and called
it "the committed FX week". It was not committed, and PR #444's D-6 is explicit
about who may write such a thing:

    **This document deliberately invents no broker market-hours times.** No
    open/close instants, no DST transition dates, no holiday list appear here
    **or may be added by an implementer**.

An implementer may not add them. So this module adds none. It carries the two
predicates whose content **is** committed, and nothing else:

* **the session partition** — Asia 00:00–07:59, Europe 08:00–15:59, US
  16:00–23:59 UTC, Ruling 4 **FROZEN**, read from
  :data:`~scripts.m15_gate3a.cost_schema.SESSIONS_UTC` rather than restated;
* **the rollover exclusion** — 21:55–22:15 UTC, Ruling 4 **FROZEN as minimum**,
  "widen only for conservatism; it must not be narrowed".

Both are **fixed UTC clock windows**. Neither is a market-hours claim, neither
moves with DST, and neither says whether the market is open. prereg §3.7 fixes
the clock as UTC with "**No DST logic (UTC only)**", so a UTC-clock window is
the same window in March as in November — which is a property this module's
tests assert against hand-written expectations rather than against itself.

What is deliberately absent
---------------------------

* **No market open or close.** Whether 2025-05-04T21:00Z is inside the trading
  week is a market-hours fact. §8.4.0 records that "no committed source states
  the market's state at 21:55–22:15 UTC" and that "no market-hours instant
  exists anywhere in the M15 contract"; `identity.py` says Track A "may not
  invent one" (ω-12); the execution gate §8 says requiring a validated calendar
  of Track A "would block exploration on an artefact that does not exist, for no
  leakage reason".
* **No expected-slot set.** D-6's coverage authority is a committed, approved
  calendar artifact, and `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`
  is open. Until it is approved, R1 reports coverage as a **declared-label
  observed-structure diagnostic** and says so — which is the route §8 provides.
* **No holiday or thin-liquidity list.** Ruling 4 makes it `[FIXED-AT design
  audit]` and no design audit has fixed one. D-6 forbids an implementer adding
  one. R1 therefore applies **no** illiquidity exclusion and records the
  consequence rather than a guess.

`COVERAGE_AUTHORITY_ABSENT_R1_REPORTS_A_DECLARED_LABEL_DIAGNOSTIC`
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

# ``BUCKET_MINUTES`` comes from the aggregator's own constant so the two cannot
# drift; the session partition comes from ``cost_schema`` for the same reason.
from scripts.m15_gate3a.aggregation import BUCKET_MINUTES
from scripts.m15_gate3a.cost_schema import SESSIONS_UTC

#: Ruling 4 FROZEN as a **minimum**: "widen only for conservatism; it must not
#: be narrowed without a new human + ChatGPT ruling". Taken at exactly the
#: committed minimum, in minutes from UTC midnight.
ROLLOVER_START_MINUTE_OF_DAY: Final[int] = 21 * 60 + 55
ROLLOVER_END_MINUTE_OF_DAY: Final[int] = 22 * 60 + 15

#: What R1's coverage figure is, and is not.
COVERAGE_STATUS: Final[str] = "COVERAGE_AUTHORITY_ABSENT_R1_REPORTS_A_DECLARED_LABEL_DIAGNOSTIC"

#: Why no illiquidity exclusion is applied, and which way that biases R1.
HOLIDAY_STATUS: Final[str] = (
    "RULING_4_HOLIDAY_THIN_LIQUIDITY_LIST_IS_FIXED_AT_DESIGN_AUDIT_AND_NONE_EXISTS"
)
HOLIDAY_CONSEQUENCE: Final[str] = (
    "no date is excluded for illiquidity, so the eligible-bar rate is OVERSTATED "
    "and thin sessions remain in the barrier/cost population, which pushes that "
    "ratio's median DOWN"
)


class SessionWindowError(ValueError):
    """A timestamp no frozen session contains."""


def _minute_of_day(moment: datetime) -> int:
    if moment.utcoffset() is None:
        raise SessionWindowError(
            f"{moment!r} is naive; a session is a UTC clock window and reinterpreting a "
            "naive value in the host timezone is how a bar changes session"
        )
    utc = moment.utctimetuple()
    return utc.tm_hour * 60 + utc.tm_min


def session_of(moment: datetime) -> str:
    """The frozen session containing a UTC instant: ``asia`` / ``europe`` / ``us``.

    Ruling 4 FROZEN. The windows tile the day exactly once — ``cost_schema``
    checks that at import — so exactly one branch matches and an unmatched
    instant is an error rather than a default.
    """
    minute = _minute_of_day(moment)
    for name, window in SESSIONS_UTC.items():
        start_text, _, end_text = window.partition("-")
        start_h, _, start_m = start_text.partition(":")
        end_h, _, end_m = end_text.partition(":")
        if int(start_h) * 60 + int(start_m) <= minute <= int(end_h) * 60 + int(end_m):
            return name
    raise SessionWindowError(f"no frozen session contains {moment.isoformat()}")


def bucket_overlaps_rollover(moment: datetime) -> bool:
    """Whether the M15 bucket starting at ``moment`` overlaps 21:55–22:15 UTC.

    **Overlap, not start.** Testing the bucket start silently narrows Ruling 4's
    minimum: M15 starts fall on :00/:15/:30/:45, so a start test excludes only
    the 22:00 bucket, while the 21:45 bucket spans 21:45–22:00 and keeps
    21:55–21:59 inside it — and that bucket's closing spread is the 21:59 quote,
    the widest of the day, which would then enter the median. A review role
    measured 5 such bars per pair per week. Overlap **widens** the exclusion,
    which is the only direction Ruling 4 permits.
    """
    start = _minute_of_day(moment)
    return (
        start < ROLLOVER_END_MINUTE_OF_DAY and start + BUCKET_MINUTES > ROLLOVER_START_MINUTE_OF_DAY
    )


def is_event_eligible_window(moment: datetime) -> bool:
    """Whether an M15 bucket start is outside every frozen ineligibility window.

    Today that is the rollover window alone. It is **not** a claim that the
    market is open — no committed source supports one — and it applies no
    holiday exclusion, because none exists to apply (:data:`HOLIDAY_STATUS`).
    """
    return not bucket_overlaps_rollover(moment)


__all__ = [
    "BUCKET_MINUTES",
    "COVERAGE_STATUS",
    "HOLIDAY_CONSEQUENCE",
    "HOLIDAY_STATUS",
    "ROLLOVER_END_MINUTE_OF_DAY",
    "ROLLOVER_START_MINUTE_OF_DAY",
    "SessionWindowError",
    "bucket_overlaps_rollover",
    "is_event_eligible_window",
    "session_of",
]
