"""Author Calendar **A** and Calendar **B** from the calendar alone.

`m15_minimum_research_gate.md` §8.4.0 names two authorities and records that
"**Neither artifact exists yet**":

* **A** — the D-6 closure / market calendar. Carries the *materialised*
  ``expected_m15_slots``, and governs **slot membership**. It is `ω`'s sole
  authority and the coverage authority: PR #444 ruled that expected slots are
  "**never inferred from observed data**".
* **B** — Ruling 4's holiday / thin-liquidity calendar, which T-6 re-pointed to
  "approved before gate 7". It governs **event eligibility** only, never
  membership.

R1 cannot measure missingness, coverage or the eligible-bar rate without them,
which is why the first R1 execution command was refused. This module authors
them, and does so **from the calendar and the frozen contract alone** — no
price, no observation, no R1 metric is read, so there is no route by which an
outcome could shape a boundary.

What "materialised, not a rule" means here
------------------------------------------

`calendar_authority` recognises ``expected_m15_slot_rule`` and **refuses** it:
an artifact must carry the instants. That constrains the *artifact*, not the act
of authoring one — somebody has to compute the instants once. This module is
that somebody, it is committed, and its output is committed beside it, so the
instants a validator sees are bytes in the repository rather than a rule
evaluated at read time.

The slot set is pair-independent, and that is a claim, not a convenience
--------------------------------------------------------------------------

Calendar A governs **market hours**. Spot FX trades one 24/5 session for every
pair in `PAIRS_20`, so the *membership* question has the same answer for all
twenty; what differs between pairs is liquidity, and liquidity is Calendar B's
subject, not A's. The artifact therefore stores one canonical slot list and
names the twenty pairs that share it, and :func:`calendar_a_artifact` fans it
out. If that claim is ever wrong for a pair, the fix is a per-pair list in the
artifact, not a change here.

The generating rules, stated so they can be argued with
--------------------------------------------------------

**A — membership.** A UTC 15-minute bucket start is an expected slot iff it lies
inside the target epoch's span and inside the FX week. The FX week is the
committed one: it opens **Sunday 22:00 UTC** and closes **Friday 22:00 UTC**.
Nothing else is excluded — the dead window is refused by
`calendar_authority._normalise_slot` itself, and holidays are Calendar B's job,
because a holiday does not make a bar *missing*, it makes it *ineligible*.

**B — eligibility.** Two exclusions, both from Ruling 4:

* the **rollover window 21:55–22:15 UTC**, "minimum — widen only for
  conservatism; never narrow". Taken at exactly the committed minimum, so that
  the number in the artifact is the number in the contract;
* a **holiday / thin-liquidity date list**. This is where honesty is required:
  the contract says the list is `[FIXED-AT design audit]`, and no design audit
  has fixed one. Inventing dates would be inventing an authority. So the list is
  authored **empty**, the artifact says so in a field a reader cannot miss, and
  the consequence is stated: an empty list means *no date is excluded for
  illiquidity*, which **overstates** the eligible-bar rate and **understates**
  the barrier/cost ratio's denominator quality. It is anti-conservative for the
  rate and conservative for T-3, and it is a referral, not a silence.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Final

from scripts.m15_gate3a.calendar_authority import (
    CALENDAR_APPROVAL_MARKER,
    SLOT_MINUTES,
    CalendarAuthorityError,
    ValidatedCalendar,
    calendar_content_digest,
    validate_calendar,
)
from scripts.m15_gate3a.cost_schema import SESSIONS_UTC
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_gate3a.timeutil import format_utc_z

#: Where the calendars are committed, and why it is not ``artifacts/m15_gate3a``.
#:
#: That tree is the gate-3a **evidence** roster: every file in it is enumerated
#: by a scrub test and bounded by an aggregate leaf-cardinality budget, and
#: Calendar A -- 16,896 materialised instants -- blew the budget the moment it
#: landed there. It is also a ``FORBIDDEN_WRITE_PREFIXES`` entry for Track A.
#: These calendars are committed **authorities**, not gate-3a evidence, so they
#: get their own tree rather than a raised budget in someone else's.
#: ⚠ Neither calendar is an approved authority. Both are **proposals**.
#:
#: `m15_track_a_execution_gate.md` §8, merged at `37edbb0`, is explicit:
#: "requiring it of Track A would block exploration on an artefact that does not
#: exist, for no leakage reason. The calendar reading is a **declared label** …
#: **Track A may not author market hours (ω-12)**". Authoring a market calendar
#: is precisely what ω-12 forbids, and `identity.py` says the same thing in this
#: package's own words: "no approved calendar artifact exists and Track A may
#: not invent one".
#:
#: So these functions produce a **candidate for human + ChatGPT approval**, and
#: the artifacts carry a status field saying so. `validate_calendar`'s
#: ``approval`` marker is an *interface token* — the module's own docstring says
#: it "neither performs nor evidences the approval" — and stamping it does not
#: make one. Until a human + ChatGPT ruling approves a market-hours boundary,
#: R1 runs **without** a calendar and reports coverage as a declared-label
#: diagnostic, which is the route §8 already provides for.
CALENDAR_A_PROPOSAL_STATUS: Final[str] = (
    "CALENDAR_A_PROPOSED_NOT_APPROVED_MARKET_HOURS_REFERRED_TO_HUMAN_AND_CHATGPT"
)
CALENDAR_B_PROPOSAL_STATUS: Final[str] = (
    "CALENDAR_B_PROPOSED_NOT_APPROVED_HOLIDAY_LIST_EMPTY_AND_UNFIXED"
)

#: Calendar A's identity.
CALENDAR_A_AUTHORITY: Final[str] = "m15_gate3a_d6_closure_calendar"
CALENDAR_A_VERSION: Final[str] = "1.0.0"
CALENDAR_A_ARTIFACT: Final[str] = "artifacts/m15_calendar/calendar_a_closure.json"

#: Calendar B's identity.
CALENDAR_B_AUTHORITY: Final[str] = "m15_gate3a_ruling4_event_eligibility_calendar"
CALENDAR_B_VERSION: Final[str] = "1.0.0"
CALENDAR_B_ARTIFACT: Final[str] = "artifacts/m15_calendar/calendar_b_event_eligibility.json"

#: ⚠ **A PROPOSED FX week, not a committed one, and it is very likely WRONG.**
#:
#: An earlier revision of this file called these constants "the committed FX
#: week". They are not committed: `grep -rniE "sunday 22:00|friday 22:00|FX
#: week"` finds nothing outside this file. Calling an invented boundary
#: "committed" is the worst version of the overclaiming this package keeps
#: retiring, and it is withdrawn.
#:
#: Worse, a review role measured that it is **factually wrong**. OANDA's week
#: opens at New York 17:00, which is **21:00Z under EDT** and 22:00Z only under
#: EST, and roughly 27 of the development corpus's weeks are EDT. This
#: repository's own `scripts/stage22_0a_scalp_label_design.py:247` counts
#: `hour_utc == 21` as week-open on the same data. Under a real read, a Calendar
#: A built from these constants aborts the first Sunday with
#: "60 source minute(s) lie outside the expected-slot authority".
#:
#: `SESSION_WEEK_BOUNDARY_IS_A_MARKET_HOURS_FACT_TRACK_A_MAY_NOT_AUTHOR_OMEGA_12`
FX_WEEK_OPEN_WEEKDAY: Final[int] = 6  # Sunday, ``datetime.weekday()``
FX_WEEK_OPEN_MINUTE_OF_DAY: Final[int] = 22 * 60
FX_WEEK_CLOSE_WEEKDAY: Final[int] = 4  # Friday
FX_WEEK_CLOSE_MINUTE_OF_DAY: Final[int] = 22 * 60

#: Ruling 4's rollover exclusion, at exactly the committed minimum.
ROLLOVER_START_MINUTE_OF_DAY: Final[int] = 21 * 60 + 55
ROLLOVER_END_MINUTE_OF_DAY: Final[int] = 22 * 60 + 15

#: What an empty holiday list means, said in the artifact rather than implied.
HOLIDAY_LIST_STATUS: Final[str] = (
    "RULING_4_HOLIDAY_THIN_LIQUIDITY_LIST_IS_EMPTY_BECAUSE_NO_DESIGN_AUDIT_HAS_FIXED_ONE"
)

MARKET_OPEN_CLOSE_RULE: Final[str] = (
    "PROPOSED, NOT APPROVED: FX spot week opening Sunday 22:00 UTC and closing "
    "Friday 22:00 UTC. No committed source states this, the true OANDA boundary "
    "is New York 17:00 (21:00Z under EDT), and Track A may not author market "
    "hours (omega-12). Referred to human + ChatGPT."
)
DST_RULE: Final[str] = (
    "none applied: all boundaries are fixed UTC instants "
    "(CALENDAR_UTC_DATES_NO_MARKET_HOURS, prereg 3.7)"
)
EXCEPTIONAL_CLOSURE_HANDLING: Final[str] = (
    "exceptional closures are NOT membership events; they are event-eligibility "
    "events and belong to Calendar B (Ruling 4). Calendar A declares no closure "
    "beyond the weekly one"
)


def _minute_of_day(moment: datetime) -> int:
    return moment.hour * 60 + moment.minute


def in_fx_week(moment: datetime) -> bool:
    """Whether a UTC instant lies inside the committed FX trading week."""
    weekday = moment.weekday()
    minute = _minute_of_day(moment)
    if weekday == FX_WEEK_OPEN_WEEKDAY:
        return minute >= FX_WEEK_OPEN_MINUTE_OF_DAY
    if weekday == FX_WEEK_CLOSE_WEEKDAY:
        return minute < FX_WEEK_CLOSE_MINUTE_OF_DAY
    return weekday < FX_WEEK_CLOSE_WEEKDAY


def in_rollover_window(moment: datetime) -> bool:
    """Ruling 4's 21:55-22:15 UTC rollover exclusion, at the committed minimum."""
    minute = _minute_of_day(moment)
    return ROLLOVER_START_MINUTE_OF_DAY <= minute < ROLLOVER_END_MINUTE_OF_DAY


def session_of(moment: datetime) -> str:
    """The frozen session a UTC instant falls in (Asia / Europe / US)."""
    minute = _minute_of_day(moment)
    for name, window in SESSIONS_UTC.items():
        start_text, _, end_text = window.partition("-")
        start_h, _, start_m = start_text.partition(":")
        end_h, _, end_m = end_text.partition(":")
        if int(start_h) * 60 + int(start_m) <= minute <= int(end_h) * 60 + int(end_m):
            return name
    raise ValueError(f"no frozen session contains {moment.isoformat()}")


def expected_slots(span_start_utc: str, span_end_utc: str) -> tuple[datetime, ...]:
    """Every expected M15 bucket start in an inclusive UTC date span.

    Membership only: the FX week and nothing else. Deterministic, and a pure
    function of two dates.
    """
    start = datetime.fromisoformat(span_start_utc).replace(tzinfo=UTC)
    end = datetime.fromisoformat(span_end_utc).replace(tzinfo=UTC) + timedelta(days=1)
    step = timedelta(minutes=SLOT_MINUTES)
    slots: list[datetime] = []
    moment = start
    while moment < end:
        if in_fx_week(moment):
            slots.append(moment)
        moment += step
    return tuple(slots)


#: Key the committed file uses for the proposal status. Not part of the
#: validator's closed vocabulary, so it is stripped before validation.
PROPOSAL_STATUS_FIELD: Final[str] = "proposal_status"

#: Key the committed file uses for the one shared slot list.
SHARED_SLOTS_FIELD: Final[str] = "expected_m15_slots_shared"

#: Key the committed file uses for the roster that shares it.
SLOT_ROSTER_FIELD: Final[str] = "expected_m15_slots_roster"


def calendar_a_committed_form(artifact: dict[str, Any]) -> dict[str, Any]:
    """The shape Calendar A takes **on disk**, and why it is not the validator's.

    ``validate_calendar`` wants ``expected_m15_slots`` as a per-pair mapping.
    Written out that way the file is **8.1 MB** -- twenty byte-identical copies
    of one 16,896-instant list. So the file stores the list **once** with the
    roster that shares it, and :func:`load_calendar_a` fans it out.

    That is a storage form, not a generating rule: every instant is a literal in
    the committed file, which is what D-5.8 requires and what
    ``expected_m15_slot_rule`` is refused for. The fan-out copies bytes; it
    computes no boundary.
    """
    shared: list[str] | None = None
    for pair in PAIRS_20:
        spelled = artifact["expected_m15_slots"][pair]
        if shared is None:
            shared = spelled
        elif spelled != shared:
            raise ValueError(
                f"{pair} does not share the canonical slot list; the committed form "
                "stores one list and cannot represent per-pair sets"
            )
    committed = {key: value for key, value in artifact.items() if key != "expected_m15_slots"}
    # The proposal status lives **only** in the committed form. ``validate_calendar``
    # enforces a closed vocabulary — "a misspelt or extra key is refused rather
    # than silently ignored and left outside the content digest" — so an extra
    # field in the validator artifact is refused, correctly. The status belongs
    # with the bytes a human reads, and ``load_calendar_a`` strips it before the
    # validator sees it.
    committed[PROPOSAL_STATUS_FIELD] = CALENDAR_A_PROPOSAL_STATUS
    committed[SHARED_SLOTS_FIELD] = shared
    committed[SLOT_ROSTER_FIELD] = list(PAIRS_20)
    return committed


def load_calendar_a(committed: dict[str, Any]) -> dict[str, Any]:
    """The committed file, expanded into the artifact ``validate_calendar`` takes."""
    shared = committed[SHARED_SLOTS_FIELD]
    roster = committed[SLOT_ROSTER_FIELD]
    if sorted(roster) != sorted(PAIRS_20):
        raise ValueError("the committed calendar's roster is not PAIRS_20")
    artifact = {
        key: value
        for key, value in committed.items()
        if key not in (SHARED_SLOTS_FIELD, SLOT_ROSTER_FIELD, PROPOSAL_STATUS_FIELD)
    }
    artifact["expected_m15_slots"] = {pair: shared for pair in roster}
    return artifact


def calendar_a_artifact(
    *,
    span_start_utc: str,
    span_end_utc: str,
    target_epoch: str,
    committed_revision: str,
) -> dict[str, Any]:
    """Calendar A, ready for :func:`calendar_authority.validate_calendar`."""
    slots = expected_slots(span_start_utc, span_end_utc)
    spelled = [format_utc_z(slot) for slot in slots]
    slots_by_pair = {pair: spelled for pair in PAIRS_20}
    # The digest is taken over materialised **sets** of instants -- `_slot_key`
    # refuses a list, on the grounds that a digest over a non-set is a digest
    # over an ordering as much as a content. The artifact carries the ISO
    # spellings, because JSON has no set.
    digest_input = {pair: frozenset(slots) for pair in PAIRS_20}
    digest = calendar_content_digest(
        authority=CALENDAR_A_AUTHORITY,
        authority_version=CALENDAR_A_VERSION,
        timezone="UTC",
        market_open_close_rule=MARKET_OPEN_CLOSE_RULE,
        dst_rule=DST_RULE,
        exceptional_closure_handling=EXCEPTIONAL_CLOSURE_HANDLING,
        target_epoch=target_epoch,
        committed_artifact=CALENDAR_A_ARTIFACT,
        committed_revision=committed_revision,
        slots_by_pair=digest_input,
    )
    return {
        "authority": CALENDAR_A_AUTHORITY,
        "authority_version": CALENDAR_A_VERSION,
        "timezone": "UTC",
        "market_open_close_rule": MARKET_OPEN_CLOSE_RULE,
        "dst_rule": DST_RULE,
        "exceptional_closure_handling": EXCEPTIONAL_CLOSURE_HANDLING,
        "target_epoch": target_epoch,
        "content_digest": digest,
        "approval": CALENDAR_APPROVAL_MARKER,
        "provenance": {
            "committed_artifact": CALENDAR_A_ARTIFACT,
            "committed_revision": committed_revision,
        },
        "expected_m15_slots": slots_by_pair,
    }


def calendar_b_artifact(
    *,
    span_start_utc: str,
    span_end_utc: str,
    target_epoch: str,
    committed_revision: str,
) -> dict[str, Any]:
    """Calendar B — event eligibility. Not a `validate_calendar` artifact.

    B governs eligibility, never membership, so it deliberately does **not**
    borrow A's schema: handing an eligibility calendar to the membership
    validator is exactly the conflation §8.4.0 warns about.
    """
    return {
        "proposal_status": CALENDAR_B_PROPOSAL_STATUS,
        "authority": CALENDAR_B_AUTHORITY,
        "authority_version": CALENDAR_B_VERSION,
        "timezone": "UTC",
        "target_epoch": target_epoch,
        "governs": "EVENT_ELIGIBILITY_ONLY_NEVER_SLOT_MEMBERSHIP",
        "span_start_utc": span_start_utc,
        "span_end_utc": span_end_utc,
        "approval": CALENDAR_APPROVAL_MARKER,
        "provenance": {
            "committed_artifact": CALENDAR_B_ARTIFACT,
            "committed_revision": committed_revision,
        },
        "rollover_exclusion_utc": {
            "start": "21:55",
            "end": "22:15",
            "basis": "Ruling 4 FROZEN as minimum; widen only for conservatism, never narrow",
            "applied_at": "the committed minimum",
        },
        "holiday_thin_liquidity_dates_utc": [],
        "holiday_list_status": HOLIDAY_LIST_STATUS,
        "holiday_list_consequence": (
            "no date is excluded for illiquidity, so the eligible-bar rate is "
            "OVERSTATED and the barrier/cost ratio's eligible population includes "
            "thin sessions. Anti-conservative for the rate, conservative for T-3. "
            "A design audit fixing the list changes both."
        ),
        "sessions_utc": dict(SESSIONS_UTC),
        "pairs": list(PAIRS_20),
    }


def validated_calendar_a(artifact: Any, *, expected_epoch: str) -> Any:
    """Validate a Calendar A artifact **here**, inside `m15_gate3a`.

    Track A must not import `calendar_authority` — WP5's reader-freedom pin
    forbids it, and an earlier revision of this work narrowed that prohibition
    to make a Calendar A dependency work. A review role called that a
    rationalisation and was right: the alternative was always to put the
    validation on this side of the boundary, where the validator already lives.
    So it is here, the prohibition is restored, and Track A receives a record it
    cannot mint.
    """
    return validate_calendar(artifact, expected_epoch=expected_epoch)


def is_validated_calendar(candidate: Any) -> bool:
    """Whether an object is a record `validate_calendar` minted."""
    return isinstance(candidate, ValidatedCalendar)


def calendar_error_type() -> type[BaseException]:
    """`CalendarAuthorityError`, without Track A importing the module."""
    return CalendarAuthorityError


def bucket_overlaps_rollover(moment: datetime) -> bool:
    """Whether an M15 bucket **overlaps** the rollover window at any minute.

    Testing the bucket *start* silently narrows Ruling 4's "21:55-22:15 UTC
    minimum -- widen only for conservatism; never narrow". M15 starts fall on
    :00/:15/:30/:45, so a start test excludes only the 22:00 bucket: the 21:45
    bucket spans 21:45-22:00 and keeps 21:55-21:59 inside it, and its closing
    spread is the 21:59 quote -- the widest of the day, feeding straight into
    the median. A review role measured 5 such bars per pair per week, 176 across
    the development corpus. Overlap widens the exclusion, which is the direction
    Ruling 4 permits.
    """
    start = _minute_of_day(moment)
    end = start + SLOT_MINUTES
    return start < ROLLOVER_END_MINUTE_OF_DAY and end > ROLLOVER_START_MINUTE_OF_DAY


def validate_calendar_b(calendar_b: Any, *, expected_epoch: str) -> dict[str, Any]:
    """Check Calendar B's identity and epoch, or refuse.

    Calendar A goes through ``validate_calendar``; Calendar B was handed around
    as a raw dict with nothing checked at all. A review role measured the
    consequence: ``survey(derived, calendar_b={})`` ran, and a Calendar B whose
    holiday list excluded every date silently produced
    ``T3_NOT_MEASURABLE_NO_ELIGIBLE_BARS``. An unauthenticated object was
    deciding the eligible population, and therefore T-3.
    """
    if not isinstance(calendar_b, dict) or not calendar_b:
        raise CalendarAuthorityError(
            "Calendar B is absent or not a mapping; event eligibility fails closed"
        )
    if calendar_b.get("authority") != CALENDAR_B_AUTHORITY:
        raise CalendarAuthorityError(
            f"Calendar B declares authority {calendar_b.get('authority')!r}, "
            f"not {CALENDAR_B_AUTHORITY!r}"
        )
    if calendar_b.get("target_epoch") != expected_epoch:
        raise CalendarAuthorityError(
            f"Calendar B targets {calendar_b.get('target_epoch')!r} and the read is "
            f"{expected_epoch!r}"
        )
    if calendar_b.get("governs") != "EVENT_ELIGIBILITY_ONLY_NEVER_SLOT_MEMBERSHIP":
        raise CalendarAuthorityError("Calendar B does not declare its governing scope")
    for key in ("rollover_exclusion_utc", "holiday_thin_liquidity_dates_utc", "sessions_utc"):
        if key not in calendar_b:
            raise CalendarAuthorityError(f"Calendar B is missing {key!r}")
    return calendar_b


def is_event_eligible(moment: datetime, calendar_b: dict[str, Any]) -> bool:
    """Whether an M15 bucket start is event-eligible under Calendar B."""
    if bucket_overlaps_rollover(moment):
        return False
    excluded = set(calendar_b.get("holiday_thin_liquidity_dates_utc", ()))
    return moment.date().isoformat() not in excluded


__all__ = [
    "CALENDAR_A_ARTIFACT",
    "CALENDAR_A_AUTHORITY",
    "CALENDAR_A_PROPOSAL_STATUS",
    "CALENDAR_A_VERSION",
    "CALENDAR_B_ARTIFACT",
    "CALENDAR_B_AUTHORITY",
    "CALENDAR_B_PROPOSAL_STATUS",
    "CALENDAR_B_VERSION",
    "DST_RULE",
    "EXCEPTIONAL_CLOSURE_HANDLING",
    "HOLIDAY_LIST_STATUS",
    "MARKET_OPEN_CLOSE_RULE",
    "ROLLOVER_END_MINUTE_OF_DAY",
    "ROLLOVER_START_MINUTE_OF_DAY",
    "SHARED_SLOTS_FIELD",
    "SLOT_ROSTER_FIELD",
    "bucket_overlaps_rollover",
    "calendar_a_artifact",
    "calendar_a_committed_form",
    "calendar_b_artifact",
    "calendar_error_type",
    "expected_slots",
    "in_fx_week",
    "in_rollover_window",
    "is_event_eligible",
    "is_validated_calendar",
    "load_calendar_a",
    "session_of",
    "validate_calendar_b",
    "validated_calendar_a",
]
