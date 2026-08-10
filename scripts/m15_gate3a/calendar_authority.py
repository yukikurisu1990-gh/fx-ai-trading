"""Closure/market calendar **validation interface** for gate-3a (D-6, §12.9-10).

D-5 makes coverage set equality against an *expected* M15 slot set, and D-6 rules
that the expected slot set is **never inferred from the raw source**: the
authority is a versioned, committed closure/market calendar artifact for the
target epoch.

**This module validates an injected calendar. It never authors one.** It
contains no market open/close instant, no DST transition date, and no holiday —
those are properties of a broker's session calendar, and the contract Gate-decision
(`docs/design/m15_contract_design_gate_decision.md` §9) deliberately invents none
of them. Every such value arrives from the artifact the caller injects; this
module only checks that the artifact declares what D-6 requires and fails closed
when it does not.

**Scope boundary.** This is the reader-free half of the calendar mechanism: the
interface, its validation, and its fail-closed behaviour. It opens no file. The
artifact object is supplied by the caller already parsed; loading it from disk is
a byte read and belongs to the producer/verifier packages placed at a later gate
(contract §15.4). An interface is not a proof, and a validated calendar object is
not an approved calendar artifact.

**Fail-closed on** (D-6.2): a missing calendar, a malformed calendar, an
ambiguous calendar, an **unapproved** calendar, and a calendar whose declared
target epoch does not match the epoch the caller is certifying.

**Never** (D-6.1, D-6.3): reverse-infers "there is no data, therefore the market
was closed" — the validated calendar is built from the artifact alone and has no
access to any observation; and never synthesises a weekend or closure bar — it
only reports the slot set the artifact declared.

Approval marker
---------------
:data:`CALENDAR_APPROVAL_MARKER` is an **interface token**. "Unapproved fails
closed" is only checkable if the artifact carries a field asserting approval, so
D-6.2 needs an agreed spelling for it and this is that spelling. It is an
interface encoding of D-6.2 and **not** a market-hours decision, and validating
the marker neither performs nor evidences the approval: the marker is a
*declaration by the artifact*, which is why a validated calendar reports its
approval basis as :data:`APPROVAL_BASIS_DECLARED`. The open pre-continuation item
``PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`` remains open and is not
discharged by anything in this module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

from scripts.m15_gate3a.no_overlap import is_dead_window_instant
from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair
from scripts.m15_gate3a.timeutil import TimestampError, to_utc

# The M15 bucket grid, taken verbatim from the committed derivation manifest
# (`design_m15_derivation_manifest.json`: "floor(source_minute / 15) on the UTC
# clock; bar timestamp = bucket start"). This is the frozen derivation contract,
# not a market-hours decision.
SLOT_MINUTES: Final[int] = 15

CALENDAR_APPROVAL_MARKER: Final[str] = "CALENDAR_ARTIFACT_APPROVED_BY_HUMAN_AND_CHATGPT"

APPROVAL_BASIS_DECLARED: Final[str] = (
    "APPROVAL_DECLARED_BY_ARTIFACT__NOT_EVIDENCE_THAT_APPROVAL_OCCURRED"
)

#: Fields D-6 requires a calendar artifact to carry, verbatim from §9.
REQUIRED_CALENDAR_FIELDS: Final[tuple[str, ...]] = (
    "authority",  # source / broker / session authority
    "authority_version",  # authority version or retrieval date
    "timezone",
    "market_open_close_rule",
    "dst_rule",
    "exceptional_closure_handling",
    "target_epoch",
    "content_digest",  # content digest / version
    "approval",  # approval marker (interface encoding of D-6.2)
)

#: Exactly one of these supplies the expected M15 slot set (D-6: "the expected
#: M15 slot set, **or** a rule that generates it deterministically").
SLOT_SOURCE_FIELDS: Final[tuple[str, ...]] = ("expected_m15_slots", "expected_m15_slot_rule")


class CalendarAuthorityError(RuntimeError):
    """Base class: the injected calendar cannot serve as the coverage authority."""


class CalendarAbsentError(CalendarAuthorityError):
    """No calendar artifact was supplied at all (D-6.2)."""


class CalendarMalformedError(CalendarAuthorityError):
    """The calendar is present but does not carry what D-6 requires."""


class CalendarAmbiguousError(CalendarAuthorityError):
    """The calendar admits more than one reading of the expected slot set (D-6.2)."""


class CalendarUnapprovedError(CalendarAuthorityError):
    """The calendar does not declare the approval D-6.2 requires."""


class CalendarEpochMismatchError(CalendarAuthorityError):
    """The calendar's target epoch is not the epoch being certified (D-6.2)."""


@dataclass(frozen=True, slots=True)
class ValidatedCalendar:
    """A calendar artifact that passed validation, and the slot set it declares.

    Constructed only by :func:`validate_calendar`. It holds no observation and
    exposes no way to inject one, so the expected slot set can never be narrowed
    to whatever happened to be measured (D-6.1).
    """

    authority: str
    authority_version: str
    timezone: str
    market_open_close_rule: str
    dst_rule: str
    exceptional_closure_handling: str
    target_epoch: str
    content_digest: str
    slot_source_field: str
    approval_basis: str = field(default=APPROVAL_BASIS_DECLARED)
    _slots: Mapping[str, frozenset[datetime]] = field(default_factory=dict)

    def expected_slots(self, pair: object) -> frozenset[datetime]:
        """Expected M15 slots for ``pair``, exactly as the artifact declared them."""
        try:
            canonical = canonical_pair(pair)
        except PairAuthorityError as exc:
            raise CalendarMalformedError(
                f"calendar queried for a pair outside the frozen PAIRS_20 universe: {exc}"
            ) from exc
        slots = self._slots.get(canonical)
        if slots is None:  # pragma: no cover - validation guarantees all 20
            raise CalendarMalformedError(
                f"calendar declares no expected M15 slot set for {canonical}"
            )
        return slots

    @property
    def pairs(self) -> tuple[str, ...]:
        """The canonical roster the calendar covers (always exactly PAIRS_20)."""
        return PAIRS_20


def _require_text(artifact: Mapping[str, Any], key: str) -> str:
    value = artifact.get(key)
    if value is None:
        raise CalendarMalformedError(f"calendar artifact is missing the required D-6 field {key!r}")
    if not isinstance(value, str):
        raise CalendarMalformedError(
            f"calendar field {key!r} must be a string, got {type(value).__name__}"
        )
    text = str.__str__(value)
    if not text.strip():
        raise CalendarAmbiguousError(
            f"calendar field {key!r} is present but empty, so the artifact states nothing"
        )
    return text


def _normalise_slot(raw: Any, *, pair: str) -> datetime:
    """One expected slot: an exact, aligned, dead-window-free UTC bucket start."""
    try:
        slot = to_utc(raw)
    except TimestampError as exc:
        raise CalendarMalformedError(
            f"calendar slot for {pair} is not an exact UTC instant: {exc}"
        ) from exc
    if slot.minute % SLOT_MINUTES or slot.second or slot.microsecond:
        raise CalendarMalformedError(
            f"calendar slot {slot.isoformat()} for {pair} is not on the frozen "
            f"{SLOT_MINUTES}-minute UTC bucket grid"
        )
    if is_dead_window_instant(slot):
        raise CalendarMalformedError(
            f"calendar slot {slot.isoformat()} for {pair} lies inside the consumed "
            "dead window, which no role may expect"
        )
    return slot


def _slot_set(raw_slots: Any, *, pair: str) -> frozenset[datetime]:
    if isinstance(raw_slots, (str, bytes, bytearray)) or not isinstance(raw_slots, Sequence):
        raise CalendarMalformedError(
            f"calendar slots for {pair} must be a concrete sequence, got {type(raw_slots).__name__}"
        )
    seen: dict[datetime, int] = {}
    for index, raw in enumerate(tuple(raw_slots)):
        slot = _normalise_slot(raw, pair=pair)
        if slot in seen:
            raise CalendarAmbiguousError(
                f"calendar lists slot {slot.isoformat()} for {pair} at positions "
                f"{seen[slot]} and {index}; a repeated slot leaves the expected count ambiguous"
            )
        seen[slot] = index
    if not seen:
        raise CalendarMalformedError(
            f"calendar declares an empty expected M15 slot set for {pair}; absence of "
            "slots is never a statement that the market was closed"
        )
    return frozenset(seen)


def _slots_from_mapping(raw: Any) -> dict[str, frozenset[datetime]]:
    if not isinstance(raw, Mapping):
        raise CalendarMalformedError(
            f"'expected_m15_slots' must map each pair to its slot set, got {type(raw).__name__}"
        )
    resolved: dict[str, frozenset[datetime]] = {}
    origin: dict[str, Any] = {}
    for raw_pair, raw_slots in dict(raw).items():
        try:
            pair = canonical_pair(raw_pair)
        except PairAuthorityError as exc:
            raise CalendarMalformedError(
                f"calendar names a pair outside the frozen PAIRS_20 universe: {exc}"
            ) from exc
        if pair in resolved:
            raise CalendarAmbiguousError(
                f"calendar declares slots for {pair} twice ({origin[pair]!r} and "
                f"{raw_pair!r} canonicalise to the same pair)"
            )
        origin[pair] = raw_pair
        resolved[pair] = _slot_set(raw_slots, pair=pair)
    missing = [p for p in PAIRS_20 if p not in resolved]
    if missing:
        raise CalendarMalformedError(
            f"calendar declares no expected M15 slot set for {missing}; every pair in "
            "PAIRS_20 must have one before coverage can be evaluated"
        )
    return resolved


def _slots_from_rule(rule: Any) -> dict[str, frozenset[datetime]]:
    """Materialise a caller-injected generating rule; the rule is never interpreted.

    The rule object comes from the artifact's owner. This module calls it once
    per canonical pair and validates its output; it does not read, parse or
    reason about any market-hours expression inside it.
    """
    if not callable(rule):
        raise CalendarMalformedError(
            f"'expected_m15_slot_rule' must be callable, got {type(rule).__name__}"
        )
    resolved: dict[str, frozenset[datetime]] = {}
    for pair in PAIRS_20:
        try:
            first = _slot_set(rule(pair), pair=pair)
            second = _slot_set(rule(pair), pair=pair)
        except CalendarAuthorityError:
            raise
        except Exception as exc:  # noqa: BLE001 - a rule that cannot answer fails closed
            raise CalendarMalformedError(
                f"'expected_m15_slot_rule' raised {type(exc).__name__} for {pair}: {exc}"
            ) from exc
        if first != second:
            raise CalendarAmbiguousError(
                f"'expected_m15_slot_rule' is not deterministic for {pair}: two calls "
                "returned different slot sets, so the expected set is not a fixed quantity"
            )
        resolved[pair] = first
    return resolved


def validate_calendar(artifact: Any, *, expected_epoch: str) -> ValidatedCalendar:
    """Validate an injected calendar artifact, or fail closed (D-6.2).

    ``expected_epoch`` is the epoch the caller is certifying. A calendar for a
    different epoch is refused rather than reinterpreted, because the expected
    slot set of one epoch is not evidence about another.

    Authoring, generating or defaulting a calendar is out of scope by ruling:
    there is no code path here that produces a slot set the artifact did not
    supply.
    """
    if artifact is None:
        raise CalendarAbsentError(
            "no calendar artifact supplied; the coverage authority is absent and "
            "coverage therefore fails closed"
        )
    if not isinstance(artifact, Mapping):
        raise CalendarMalformedError(
            f"calendar artifact must be a mapping, got {type(artifact).__name__}"
        )
    snapshot = dict(artifact)
    if not snapshot:
        raise CalendarAbsentError(
            "calendar artifact is empty; the coverage authority is absent and "
            "coverage therefore fails closed"
        )

    if not isinstance(expected_epoch, str) or not expected_epoch.strip():
        raise CalendarMalformedError(
            "expected_epoch must be a non-empty string naming the epoch being certified"
        )

    fields = {key: _require_text(snapshot, key) for key in REQUIRED_CALENDAR_FIELDS}

    # Approval is checked before the slot set: an unapproved calendar is refused
    # whether or not its contents happen to be well-formed.
    if fields["approval"] != CALENDAR_APPROVAL_MARKER:
        raise CalendarUnapprovedError(
            f"calendar declares approval {fields['approval']!r}; the coverage authority "
            f"is usable only when it declares {CALENDAR_APPROVAL_MARKER!r}, and an "
            "unapproved calendar fails closed"
        )

    if fields["target_epoch"] != str.__str__(expected_epoch):
        raise CalendarEpochMismatchError(
            f"calendar targets epoch {fields['target_epoch']!r} but the certification "
            f"is for epoch {expected_epoch!r}; a calendar is never reused across epochs"
        )

    present = [key for key in SLOT_SOURCE_FIELDS if snapshot.get(key) is not None]
    if not present:
        raise CalendarMalformedError(
            "calendar supplies neither 'expected_m15_slots' nor 'expected_m15_slot_rule', "
            "so it declares no expected M15 slot set"
        )
    if len(present) > 1:
        raise CalendarAmbiguousError(
            "calendar supplies both 'expected_m15_slots' and 'expected_m15_slot_rule'; "
            "two authorities for the same quantity leave the expected set ambiguous"
        )
    source_field = present[0]
    if source_field == "expected_m15_slots":
        slots = _slots_from_mapping(snapshot[source_field])
    else:
        slots = _slots_from_rule(snapshot[source_field])

    return ValidatedCalendar(
        authority=fields["authority"],
        authority_version=fields["authority_version"],
        timezone=fields["timezone"],
        market_open_close_rule=fields["market_open_close_rule"],
        dst_rule=fields["dst_rule"],
        exceptional_closure_handling=fields["exceptional_closure_handling"],
        target_epoch=fields["target_epoch"],
        content_digest=fields["content_digest"],
        slot_source_field=source_field,
        approval_basis=APPROVAL_BASIS_DECLARED,
        _slots=dict(slots),
    )


__all__ = [
    "APPROVAL_BASIS_DECLARED",
    "CALENDAR_APPROVAL_MARKER",
    "REQUIRED_CALENDAR_FIELDS",
    "SLOT_MINUTES",
    "SLOT_SOURCE_FIELDS",
    "CalendarAbsentError",
    "CalendarAmbiguousError",
    "CalendarAuthorityError",
    "CalendarEpochMismatchError",
    "CalendarMalformedError",
    "CalendarUnapprovedError",
    "ValidatedCalendar",
    "validate_calendar",
]
