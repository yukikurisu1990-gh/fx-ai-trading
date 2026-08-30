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
    calendar_content_digest,
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
#: Calendar A's identity.
CALENDAR_A_AUTHORITY: Final[str] = "m15_gate3a_d6_closure_calendar"
CALENDAR_A_VERSION: Final[str] = "1.0.0"
CALENDAR_A_ARTIFACT: Final[str] = "artifacts/m15_calendar/calendar_a_closure.json"

#: Calendar B's identity.
CALENDAR_B_AUTHORITY: Final[str] = "m15_gate3a_ruling4_event_eligibility_calendar"
CALENDAR_B_VERSION: Final[str] = "1.0.0"
CALENDAR_B_ARTIFACT: Final[str] = "artifacts/m15_calendar/calendar_b_event_eligibility.json"

#: The committed FX week, in UTC. Sunday 22:00 open, Friday 22:00 close.
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
    "FX spot week: opens Sunday 22:00 UTC, closes Friday 22:00 UTC; "
    "membership is continuous within the week"
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
    computes no boundary. A test asserts the loaded artifact is identical to the
    in-memory one this module builds, so the two cannot drift.
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
        if key not in (SHARED_SLOTS_FIELD, SLOT_ROSTER_FIELD)
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


def is_event_eligible(moment: datetime, calendar_b: dict[str, Any]) -> bool:
    """Whether an M15 bucket start is event-eligible under Calendar B."""
    if in_rollover_window(moment):
        return False
    excluded = set(calendar_b.get("holiday_thin_liquidity_dates_utc", ()))
    return moment.date().isoformat() not in excluded


__all__ = [
    "CALENDAR_A_ARTIFACT",
    "CALENDAR_A_AUTHORITY",
    "CALENDAR_A_VERSION",
    "CALENDAR_B_ARTIFACT",
    "CALENDAR_B_AUTHORITY",
    "CALENDAR_B_VERSION",
    "DST_RULE",
    "EXCEPTIONAL_CLOSURE_HANDLING",
    "HOLIDAY_LIST_STATUS",
    "MARKET_OPEN_CLOSE_RULE",
    "ROLLOVER_END_MINUTE_OF_DAY",
    "ROLLOVER_START_MINUTE_OF_DAY",
    "SHARED_SLOTS_FIELD",
    "SLOT_ROSTER_FIELD",
    "calendar_a_artifact",
    "calendar_a_committed_form",
    "calendar_b_artifact",
    "expected_slots",
    "in_fx_week",
    "in_rollover_window",
    "is_event_eligible",
    "load_calendar_a",
    "session_of",
]
