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

Committed provenance (D-5.8, ruled)
-----------------------------------
``D5_8_RULED_NO_NUMERIC_FLOOR_TRUSTED_CALENDAR_PROVENANCE_AND_SET_EQUALITY_REQUIRED``
replaces the open D-5.8 question with four requirements this module implements
(ruling §4.7.1): the expected M15 slot set is obtainable **only** from the
approved calendar artifact and its **committed provenance**; source and runtime
**may not invent** it from observed data or a self-generated rule; where
authority, provenance or epoch binding is not established the behaviour is
**fail-closed**; and coverage is recognised only after the set-equality limbs
**and** provenance validation both hold. **No slot-count floor exists here, and
none may be added** — the ruling records that a rule closing over the derivation
produced 20,832 slots per pair while clearing a count floor, a temporal-extent
criterion and a continuity criterion at once, so a count is not the trust axis.

What "committed provenance" can mean in a **reader-free** package is bounded by
what the package can do. It opens no file (§12.14), so the artifact arrives
already parsed and nothing here can confirm that a commit exists. Two things
*can* be done, and both are:

1. **Inert-data invariant.** The expected slot set must arrive as inert data
   that a commit can carry, be diffed and be digested. A callable cannot: see
   :func:`_refuse_generating_rule_route`, which answers FR-8 explicitly.
2. **Content binding.** The declared ``content_digest`` must **equal** a digest
   this module recomputes from the calendar content it actually carries
   (:func:`calendar_content_digest`). Before this, the digest was shape-checked
   only, so two structurally different calendars carrying the same digest string
   were indistinguishable and the unverified string was republished as
   ``ProofResult.calendar_digest`` (FR-7). Now the digest names the content, so
   the human + ChatGPT approval of the concrete artifact has something to attach
   to and a published record can be contradicted by re-derivation.

**The residual, stated rather than claimed away.** An in-process caller that
supplies both the slot set *and* the declared digest can make the two agree; the
only thing that would refuse it is reading the committed artifact, which this
package may not do. So requirement 1 is implemented **as far as a reader-free
package can implement it**: the digest binds the artifact to its own content and
the provenance block names where that content is committed, but *that* the named
commit carries this content is verified by human review of the artifact — which
is precisely what ``PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`` is
for. A byte-reading producer/verifier at a later gate (contract §15.4) is what
would close it in code.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

from scripts.m15_gate3a.no_overlap import is_dead_window_instant
from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair
from scripts.m15_gate3a.sealing import assert_minted, register_minted, seal
from scripts.m15_gate3a.timeutil import TimestampError, format_utc_z, to_utc

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

#: The two spellings §9 gives for the slot-set authority. Both stay in the
#: vocabulary so that each is *recognised*; only the first is admissible under
#: D-5.8 requirement 1, and the second is refused by name rather than ignored
#: (see :func:`_refuse_generating_rule_route`).
SLOT_SOURCE_FIELDS: Final[tuple[str, ...]] = ("expected_m15_slots", "expected_m15_slot_rule")

#: The materialised-data spelling — the only route D-5.8 requirement 1 admits.
SLOT_SET_FIELD: Final[str] = "expected_m15_slots"

#: The generating-rule spelling. Recognised, and refused (FR-8).
SLOT_RULE_FIELD: Final[str] = "expected_m15_slot_rule"

#: Key of the nested block that carries the artifact's **committed provenance**
#: (D-5.8 requirement 1). Like :data:`CALENDAR_APPROVAL_MARKER` this is an
#: interface encoding: "provenance not established fails closed" is checkable
#: only if the artifact carries a field stating its provenance, so the interface
#: needs an agreed spelling and this is it. It is not a market-hours decision and
#: no value in it is authored here.
PROVENANCE_FIELD: Final[str] = "provenance"

#: What the provenance block must state. Deliberately the **minimum** that lets
#: a human reviewer find the committed content the digest binds to: *which*
#: committed artifact, and *at which reviewed revision*. Both are opaque single
#: tokens — this module performs no path resolution and no lookup on either, and
#: opens nothing (§12.14).
REQUIRED_PROVENANCE_FIELDS: Final[tuple[str, ...]] = (
    "committed_artifact",
    "committed_revision",
)

#: The closed top-level vocabulary of a calendar artifact. A misspelt field is
#: refused rather than silently ignored: §4.8's O4 row records that the open
#: vocabulary "silently ignores a misspelt field", and once the digest binds the
#: content, an unrecognised key would be content the digest does not cover.
CALENDAR_ARTIFACT_FIELDS: Final[frozenset[str]] = frozenset(
    REQUIRED_CALENDAR_FIELDS + SLOT_SOURCE_FIELDS + (PROVENANCE_FIELD,)
)

#: Domain-separation label for :func:`calendar_content_digest`. A label, not a
#: threshold: it names *which* rendering the digest is of, so a digest over this
#: package's calendar content can never collide with a digest over anything else
#: the repository hashes.
CALENDAR_CONTENT_DIGEST_DOMAIN: Final[str] = "M15_GATE3A_CALENDAR_CONTENT_DIGEST_V1"

#: What a validated calendar's provenance actually rests on. The counterpart of
#: :data:`APPROVAL_BASIS_DECLARED`, and equally a disclaimer: the digest binding
#: is real and checked in-process, while "this content is what the named commit
#: carries" is a declaration by the artifact that a reader-free package cannot
#: verify and does not claim to.
PROVENANCE_BASIS_DECLARED_AND_DIGEST_BOUND: Final[str] = (
    "PROVENANCE_DECLARED_BY_ARTIFACT__CONTENT_DIGEST_BOUND_IN_PROCESS__"
    "COMMITMENT_NOT_VERIFIED_BY_THIS_READER_FREE_PACKAGE"
)


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


class CalendarProvenanceError(CalendarAuthorityError):
    """The calendar's committed provenance is absent or not established (D-5.8)."""


class CalendarDigestMismatchError(CalendarProvenanceError):
    """The declared content digest is not the digest of the content carried (FR-7)."""


class CalendarConstructionError(CalendarAuthorityError):
    """A :class:`ValidatedCalendar` was built outside :func:`validate_calendar`."""


class _CalendarConstructionToken:
    """One-shot capability to construct one :class:`ValidatedCalendar`.

    A frozen dataclass documents its constructor in a docstring and enforces
    nothing, so "constructed only by :func:`validate_calendar`" used to be a
    comment. The data-integrity audit built ``ValidatedCalendar(authority="THE
    OBSERVED DATA ITSELF", ...)`` straight from the public API — declaring a slot
    source of "reverse-inferred from observation" on the field that used to
    record it — and used it to satisfy the coverage limb: an artifact refuting
    D-6.1's single "Never" on its own face.
    The token closes that: only :func:`validate_calendar` mints one, and it is
    spent by the first construction so :func:`dataclasses.replace` cannot reuse
    it to mint a variant.

    **N-5 — the copy protocols were public API and are now refused.** This
    docstring used to say the guard "removes the *public-API* route". It did
    not: ``copy.copy``, ``copy.deepcopy`` and ``pickle`` are public API, and all
    three rebuild a frozen ``slots`` dataclass through ``__reduce_ex__`` without
    running ``__post_init__``, so each minted a calendar having spent no token.
    The audit deep-copied a validated calendar, rewrote ``authority`` to "THE
    OBSERVED DATA ITSELF" with ``object.__setattr__``, deep-copied *that* into a
    second free instance, and drove both through coverage. All three protocols
    now raise (:func:`_refuse_reconstruction`).

    **What it still does not do.** Python has no enforced privacy: a caller that
    reaches into this module's private names can mint a token, and
    ``object.__setattr__`` still rewrites a real instance. The guard removes the
    public-API construction routes, not every route, and the consumers re-check
    what they depend on (see ``coverage.assert_full_coverage``'s dead-window and
    design-epoch re-scan of the expected slot set) rather than trusting the type.
    """

    __slots__ = ("spent",)

    def __init__(self) -> None:
        self.spent = False


def _refuse_reconstruction(self: Any, *_args: Any) -> None:
    """Refuse ``copy.copy`` / ``copy.deepcopy`` / ``pickle`` (N-5).

    Each of these rebuilds the instance without ``__post_init__``, which is
    where the one-shot construction token is spent. A duplicated
    :class:`ValidatedCalendar` is a second assertion about market hours that
    :func:`validate_calendar` never made.
    """
    raise CalendarConstructionError(
        f"a {type(self).__name__} may not be copied, deep-copied or pickled; those protocols "
        "rebuild it without spending a construction token, so the copy would be a caller's own "
        "assertion about market hours rather than a validated artifact"
    )


@seal(error=CalendarConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False)
class ValidatedCalendar:
    """A calendar artifact that passed validation, and the slot set it declares.

    Minted only by :func:`validate_calendar`, and that is enforced by
    :class:`_CalendarConstructionToken` rather than asserted in prose. It holds
    no observation and exposes no way to inject one, so the expected slot set can
    never be narrowed to whatever happened to be measured (D-6.1).

    ``eq=False`` — **identity equality, deliberately.** Two validations of one
    artifact are two authority records, not one value, which is the same reason
    the copy protocols are refused.

    That semantic reason is now the **only** one. An earlier revision also argued
    ``eq=False`` was what made the record *registrable*, because the sealing
    registry was a ``WeakSet`` that would have had to hash the ``Mapping`` field.
    The registry is now keyed on ``id()`` with an identity re-check and imposes no
    equality semantics, so that half is **withdrawn as obsolete**.

    Content identity is not lost by this: :attr:`content_digest` is bound to the
    content (:func:`calendar_content_digest`), so two records describing the same
    calendar carry the same digest and two describing different ones cannot.
    """

    authority: str
    authority_version: str
    timezone: str
    market_open_close_rule: str
    dst_rule: str
    exceptional_closure_handling: str
    target_epoch: str
    content_digest: str
    committed_artifact: str
    committed_revision: str
    approval_basis: str = field(default=APPROVAL_BASIS_DECLARED)
    provenance_basis: str = field(default=PROVENANCE_BASIS_DECLARED_AND_DIGEST_BOUND)
    _slots: Mapping[str, frozenset[datetime]] = field(default_factory=dict)
    _construction_token: Any = field(default=None, repr=False, compare=False)

    # R-1 — ``slot_source_field`` is deleted, not reported. It recorded which of
    # §9's two spellings supplied the slot set; under D-5.8 requirement 1 the
    # generating-rule spelling is refused (:func:`_refuse_generating_rule_route`),
    # so the field could only ever hold ``SLOT_SET_FIELD``. R-1 deletes a field
    # that can hold one value, and this one asserted a *favourable* property —
    # exactly why ``pairs_measured`` went from ``CoverageResult``. The route that
    # was actually taken is recoverable from the refusal that would otherwise
    # have fired, not from a constant on the record.

    def __post_init__(self) -> None:
        token = self._construction_token
        if not isinstance(token, _CalendarConstructionToken) or token.spent:
            raise CalendarConstructionError(
                "a ValidatedCalendar is minted only by validate_calendar(); a hand-built or "
                "re-minted instance is a caller's own assertion about market hours, and D-6.1 "
                "forbids an expected slot set that did not come from the calendar artifact"
            )
        token.spent = True
        object.__setattr__(self, "_construction_token", None)
        # FB-1 / FR-3: registration is what a consumer checks. `object.__new__`
        # skips `__post_init__` entirely and no `__new__` override can intercept
        # it, so being *absent from the registry* is the only property that
        # distinguishes a forgery from a record this function actually minted.
        register_minted(self)

    __copy__ = _refuse_reconstruction
    __deepcopy__ = _refuse_reconstruction
    __reduce__ = _refuse_reconstruction

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


def _require_provenance(artifact: Mapping[str, Any]) -> dict[str, str]:
    """The committed-provenance block, or fail closed (D-5.8 requirements 1 and 3).

    A closed schema, like the six-field minute accounting: an unrecognised key
    inside the block would be provenance the digest does not cover, and a missing
    one is provenance that was never stated. Both refuse.

    Each value is treated as an **opaque single token**. ``committed_artifact``
    looks like a path and is deliberately not treated as one: this module
    resolves nothing, joins nothing and opens nothing (§12.14), so the value is
    a name a human reviewer resolves against the repository, never an input to
    any file operation here.
    """
    raw = artifact.get(PROVENANCE_FIELD)
    if raw is None:
        raise CalendarProvenanceError(
            f"calendar artifact carries no {PROVENANCE_FIELD!r} block; D-5.8 obtains the "
            "expected M15 slot set only from the approved calendar artifact and its "
            "committed provenance, and provenance that is not established fails closed"
        )
    if not isinstance(raw, Mapping):
        raise CalendarProvenanceError(
            f"calendar {PROVENANCE_FIELD!r} must be a mapping stating where the content is "
            f"committed, got {type(raw).__name__}"
        )
    block = dict(raw)
    missing = [key for key in REQUIRED_PROVENANCE_FIELDS if key not in block]
    if missing:
        raise CalendarProvenanceError(
            f"calendar {PROVENANCE_FIELD!r} is missing {missing}; committed provenance names "
            "which committed artifact carries the content and at which reviewed revision"
        )
    extra = sorted(key for key in block if key not in REQUIRED_PROVENANCE_FIELDS)
    if extra:
        raise CalendarProvenanceError(
            f"calendar {PROVENANCE_FIELD!r} carries unrecognised key(s) {extra}; the "
            "provenance schema is closed, so an unrecognised key would be provenance no "
            "digest covers"
        )
    resolved: dict[str, str] = {}
    for key in REQUIRED_PROVENANCE_FIELDS:
        value = block[key]
        if not isinstance(value, str):
            raise CalendarProvenanceError(
                f"calendar provenance field {key!r} must be a string, got {type(value).__name__}"
            )
        text = str.__str__(value)
        if not text.strip():
            raise CalendarProvenanceError(
                f"calendar provenance field {key!r} is present but empty, so the artifact "
                "states no provenance for its expected M15 slot set"
            )
        if any(ch.isspace() for ch in text):
            raise CalendarProvenanceError(
                f"calendar provenance field {key!r} is {text!r}; a committed artifact name "
                "and a reviewed revision are single tokens, never prose"
            )
        resolved[key] = text
    return resolved


def _require_single_token(text: str, *, key: str) -> str:
    """A digest/version field is one token, never prose.

    D-6 requires the artifact to carry a "content digest / version" and
    deliberately does not fix its algorithm, so a hex length cannot be demanded
    here. What can be demanded is the *shape* of an identifier: the audit's
    fabricated ``calendar_digest="NO CALENDAR EVER EXISTED"`` is a sentence, and
    a sentence is not a version of anything.
    """
    if any(ch.isspace() for ch in text):
        raise CalendarMalformedError(
            f"calendar field {key!r} is {text!r}; a content digest or version is a single "
            "token, never prose containing whitespace"
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


def _refuse_generating_rule_route(rule: Any) -> None:
    """FR-8 / D-5.8: the generating-rule route has no committed provenance.

    **Does the rule route survive requirement 1? No — not in this package, and
    the reason is structural rather than a judgement about any particular rule.**

    §9 offers two spellings for the slot-set authority: the set itself, "or a
    rule that generates it deterministically". The previous implementation
    validated a rule by calling it twice and comparing, which tests determinism
    and nothing else. **A rule that closes over the derivation output is
    perfectly deterministic**, and the D-5.8 ruling (§4.2) reproduces what that
    buys: 20,832 expected slots per pair, both epoch ends reached, a 60-minute
    maximum gap — clearing a count floor, an extent criterion and a continuity
    criterion at once. Worse, because the expectation then *tracks* the
    derivation, a bucket lost to a D-1 crossed quote or a D-2 rejected minute
    leaves the expected set at the same instant it leaves the certified set, so
    the run reports ``absent = rejected = max_unavailable_gap = 0`` and D-1's
    hard fail-closed, D-2's zero tolerance and D-3's accounting are all disarmed
    together.

    Requirement 1 admits a generating rule **only where it arrives with the
    approved artifact's committed provenance** (ruling §4.7.3). This package is
    reader-free: the artifact reaches :func:`validate_calendar` already parsed,
    and a parsed artifact carries inert data — a commit cannot carry a callable,
    a diff cannot show one and a digest cannot cover one. Therefore **every**
    callable arriving on this route was assembled in this process at runtime,
    and requirement 2 forbids exactly that. The refusal is an invariant about
    what a commit can carry, not a denylist of rule shapes, so no adjacent rule
    form escapes it.

    The interface loses nothing that the contract grants. A committed rule may
    still be *materialised into the slot set* by whatever produces the artifact;
    what the ruling forbids is materialising it inside the run whose coverage it
    is about to certify.
    """
    raise CalendarProvenanceError(
        f"calendar supplies {SLOT_RULE_FIELD!r}, a {type(rule).__name__} assembled in this "
        "process; a callable has no committed provenance because no commit can carry it, no "
        "diff can show it and no digest can cover it, and a rule that closes over the "
        f"derivation is deterministic — supply the materialised {SLOT_SET_FIELD!r} instead"
    )


def _slot_key(slots: Any, *, pair: str) -> tuple[str, ...]:
    """Canonical, sorted rendering of one pair's slot set, for the content digest.

    Every instant goes through :func:`format_utc_z`, the package's single
    artifact spelling (§12.23), so the digest is over the same characters an
    artifact would carry rather than over Python object state.
    """
    if isinstance(slots, (str, bytes, bytearray)) or not isinstance(slots, Set):
        raise CalendarMalformedError(
            f"expected slot set for {pair} must be a set, got {type(slots).__name__}; a "
            "content digest cannot be taken over an object that is not a materialised set"
        )
    try:
        rendered = sorted(format_utc_z(slot) for slot in slots)
    except TimestampError as exc:
        raise CalendarMalformedError(
            f"expected slot set for {pair} carries an instant that is not an exact UTC "
            f"bucket start: {exc}"
        ) from exc
    return tuple(rendered)


def calendar_content_digest(
    *,
    authority: str,
    authority_version: str,
    timezone: str,
    market_open_close_rule: str,
    dst_rule: str,
    exceptional_closure_handling: str,
    target_epoch: str,
    committed_artifact: str,
    committed_revision: str,
    slots_by_pair: Mapping[str, Any],
) -> str:
    """The digest of a calendar's declared content — FR-7's missing binding.

    D-6 fixes no digest algorithm, which is why the previous implementation
    shape-checked ``content_digest`` and stopped. Nothing here invents one
    either: the algorithm is the repository's established content-digest
    pattern — a **sha256 hexdigest over a canonical UTF-8 rendering** (as in
    ``scripts/ml_step4/contract.py`` and ``scripts/ml_uplift_harness/provenance.py``)
    — and the canonical rendering is built from this package's own committed
    forms: :data:`~scripts.m15_gate3a.pair_authority.PAIRS_20` ordering and
    :func:`~scripts.m15_gate3a.timeutil.format_utc_z` spelling.

    **This is not a byte read and not a raw-source re-hash** (D-4 / §12.11). It
    opens no file and touches no source or derived artifact bytes: its subject is
    the calendar's own declared content, already in memory because the caller
    handed it in. It produces no byte-level claim token and is never promoted to
    one (D-11).

    Every declared field is covered except two, each for a stated reason: the
    ``content_digest`` itself, which cannot cover itself, and ``approval``, which
    :func:`validate_calendar` already pins to the single constant
    :data:`CALENDAR_APPROVAL_MARKER` and so carries no content.
    """
    lines: list[str] = [CALENDAR_CONTENT_DIGEST_DOMAIN]
    for name, value in (
        ("authority", authority),
        ("authority_version", authority_version),
        ("timezone", timezone),
        ("market_open_close_rule", market_open_close_rule),
        ("dst_rule", dst_rule),
        ("exceptional_closure_handling", exceptional_closure_handling),
        ("target_epoch", target_epoch),
        ("committed_artifact", committed_artifact),
        ("committed_revision", committed_revision),
    ):
        if not isinstance(value, str):
            raise CalendarMalformedError(
                f"calendar field {name!r} must be a string to be digested, got "
                f"{type(value).__name__}"
            )
        # `str.__str__` is the unbound slot, so a `str` subclass cannot show one
        # spelling to the digest and another to a comparison (the FB-5 family).
        #
        # LENGTH-PREFIXED, not `name=value`. `_require_text` permits embedded
        # newlines in all six free-text D-6 declarations, and the rendering joins
        # lines with a newline, so `name=value` was an ambiguous encoding: an internal
        # audit put the boundary inside a value and produced two calendars whose
        # market-hours declarations differed field-for-field yet digested
        # identically, from plain JSON, both passing provenance. Prefixing each
        # value with its character count makes the encoding injective whatever the
        # content holds, which is stronger than forbidding the separator — a
        # denylist of characters is the shape of defect this programme keeps
        # re-opening.
        rendered = str.__str__(value)
        lines.append(f"{name}[{len(rendered)}]={rendered}")
    for pair in PAIRS_20:
        if pair not in slots_by_pair:
            raise CalendarMalformedError(
                f"calendar declares no expected M15 slot set for {pair}; the content digest "
                "is taken over all twenty pairs or over none"
            )
        lines.append(f"slots[{pair}]")
        lines.extend(_slot_key(slots_by_pair[pair], pair=pair))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


def recompute_content_digest(
    calendar: ValidatedCalendar,
    *,
    pinned_slots: Mapping[str, frozenset[datetime]] | None = None,
) -> str:
    """Re-derive :func:`calendar_content_digest` from a validated record's own fields.

    *pinned_slots* is the B-3 single-read discipline reaching across the module
    boundary. ``assert_full_coverage`` pins each pair's expected set once and
    decides every §8 limb on that pinned object; if the digest were then taken by
    re-reading ``calendar.expected_slots(pair)``, the record would attest to
    content the limbs never saw. An internal audit exercised exactly that: a
    two-faced slot source certified a one-slot-per-pair run while publishing the
    digest of the approved three-slot calendar. Callers that have already pinned
    the sets pass them here so that one read serves both the decision and the
    attestation.
    """
    slots = (
        {pair: pinned_slots[pair] for pair in PAIRS_20}
        if pinned_slots is not None
        else {pair: calendar.expected_slots(pair) for pair in PAIRS_20}
    )
    return calendar_content_digest(
        authority=calendar.authority,
        authority_version=calendar.authority_version,
        timezone=calendar.timezone,
        market_open_close_rule=calendar.market_open_close_rule,
        dst_rule=calendar.dst_rule,
        exceptional_closure_handling=calendar.exceptional_closure_handling,
        target_epoch=calendar.target_epoch,
        committed_artifact=calendar.committed_artifact,
        committed_revision=calendar.committed_revision,
        slots_by_pair=slots,
    )


def assert_calendar_provenance(
    calendar: Any,
    *,
    pinned_slots: Mapping[str, frozenset[datetime]] | None = None,
) -> str:
    """Consumer boundary for D-5.8 requirements 1-4; returns the bound digest.

    Sited at a **consumer**, not only inside :func:`validate_calendar`, because
    ruling §4.9 records that a criterion checked only at validation is bypassed
    by the FB-1 forgery route while ``assert_full_coverage`` — which re-reads
    ``calendar.expected_slots(pair)`` rather than trusting the type — holds. The
    checks here are therefore re-derivations, not a second reading of a flag:

    * the object is a :class:`ValidatedCalendar` **that this package minted**
      (:func:`~scripts.m15_gate3a.sealing.assert_minted`) — subclassing is
      refused at class creation and ``object.__new__`` leaves the forgery absent
      from the registry;
    * its provenance declarations are still present and still single tokens, so
      an ``object.__setattr__`` that blanks one is refused rather than digested;
    * the declared digest **equals** the digest re-derived from the content the
      record actually carries, so rewriting ``authority`` to "THE OBSERVED DATA
      ITSELF" or replacing ``_slots`` after validation no longer survives.

    Requirement 3: anything not established here **raises**. There is no
    report-only path and no parameter (D-10).
    """
    if not isinstance(calendar, ValidatedCalendar):
        raise CalendarProvenanceError(
            f"calendar provenance cannot be established for a {type(calendar).__name__}; "
            "only a validated calendar carries the committed provenance D-5.8 requires"
        )
    assert_minted(
        calendar,
        what="the calendar authority offered to coverage",
        error=CalendarConstructionError,
    )
    for name in ("committed_artifact", "committed_revision"):
        value = getattr(calendar, name)
        if not isinstance(value, str) or not str.__str__(value).strip():
            raise CalendarProvenanceError(
                f"calendar provenance field {name!r} no longer states anything; committed "
                "provenance that is absent at the point of use is not established"
            )
    declared = calendar.content_digest
    if not isinstance(declared, str):
        raise CalendarProvenanceError(
            f"calendar content_digest is a {type(declared).__name__}, not a digest; the "
            "expected slot set is unbound to any committed content"
        )
    recomputed = recompute_content_digest(calendar, pinned_slots=pinned_slots)
    if str.__str__(declared) != recomputed:
        raise CalendarDigestMismatchError(
            f"calendar declares content_digest {str.__str__(declared)!r} but the content it "
            f"carries digests to {recomputed!r}; the expected M15 slot set is therefore not "
            "the content the committed artifact was approved for"
        )
    return recomputed


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

    unrecognised = sorted(key for key in snapshot if key not in CALENDAR_ARTIFACT_FIELDS)
    if unrecognised:
        raise CalendarMalformedError(
            f"calendar artifact carries unrecognised field(s) {unrecognised}; the artifact "
            "vocabulary is closed, so a misspelt or extra key is refused rather than "
            "silently ignored and left outside the content digest"
        )

    fields = {key: _require_text(snapshot, key) for key in REQUIRED_CALENDAR_FIELDS}
    fields["content_digest"] = _require_single_token(fields["content_digest"], key="content_digest")

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

    provenance = _require_provenance(snapshot)

    present = [key for key in SLOT_SOURCE_FIELDS if snapshot.get(key) is not None]
    if not present:
        raise CalendarMalformedError(
            "calendar supplies neither 'expected_m15_slots' nor 'expected_m15_slot_rule', "
            "so it declares no expected M15 slot set"
        )
    if len(present) > 1:
        # Ambiguity is decided before admissibility: two authorities for one
        # quantity is a defect of the artifact whichever of them is admissible,
        # and this keeps the ambiguity refusal identifiable as itself.
        raise CalendarAmbiguousError(
            "calendar supplies both 'expected_m15_slots' and 'expected_m15_slot_rule'; "
            "two authorities for the same quantity leave the expected set ambiguous"
        )
    if present[0] == SLOT_RULE_FIELD:
        _refuse_generating_rule_route(snapshot[SLOT_RULE_FIELD])
    slots = _slots_from_mapping(snapshot[SLOT_SET_FIELD])

    # D-5.8 requirement 1, the bindable half: the digest the artifact commits to
    # must be the digest of the content it carries (FR-7). Computed last, over
    # the materialised slot set, so it covers what a consumer will actually read.
    recomputed = calendar_content_digest(
        authority=fields["authority"],
        authority_version=fields["authority_version"],
        timezone=fields["timezone"],
        market_open_close_rule=fields["market_open_close_rule"],
        dst_rule=fields["dst_rule"],
        exceptional_closure_handling=fields["exceptional_closure_handling"],
        target_epoch=fields["target_epoch"],
        committed_artifact=provenance["committed_artifact"],
        committed_revision=provenance["committed_revision"],
        slots_by_pair=slots,
    )
    if fields["content_digest"] != recomputed:
        raise CalendarDigestMismatchError(
            f"calendar declares content_digest {fields['content_digest']!r} but the content "
            f"it carries digests to {recomputed!r}; a digest that does not name its own "
            "content binds nothing, and two different calendars could carry the same string"
        )

    return ValidatedCalendar(
        authority=fields["authority"],
        authority_version=fields["authority_version"],
        timezone=fields["timezone"],
        market_open_close_rule=fields["market_open_close_rule"],
        dst_rule=fields["dst_rule"],
        exceptional_closure_handling=fields["exceptional_closure_handling"],
        target_epoch=fields["target_epoch"],
        content_digest=fields["content_digest"],
        committed_artifact=provenance["committed_artifact"],
        committed_revision=provenance["committed_revision"],
        approval_basis=APPROVAL_BASIS_DECLARED,
        provenance_basis=PROVENANCE_BASIS_DECLARED_AND_DIGEST_BOUND,
        _slots=dict(slots),
        _construction_token=_CalendarConstructionToken(),
    )


__all__ = [
    "APPROVAL_BASIS_DECLARED",
    "CALENDAR_APPROVAL_MARKER",
    "CALENDAR_ARTIFACT_FIELDS",
    "CALENDAR_CONTENT_DIGEST_DOMAIN",
    "PROVENANCE_BASIS_DECLARED_AND_DIGEST_BOUND",
    "PROVENANCE_FIELD",
    "REQUIRED_CALENDAR_FIELDS",
    "REQUIRED_PROVENANCE_FIELDS",
    "SLOT_MINUTES",
    "SLOT_RULE_FIELD",
    "SLOT_SET_FIELD",
    "SLOT_SOURCE_FIELDS",
    "CalendarAbsentError",
    "CalendarAmbiguousError",
    "CalendarAuthorityError",
    "CalendarConstructionError",
    "CalendarDigestMismatchError",
    "CalendarEpochMismatchError",
    "CalendarMalformedError",
    "CalendarProvenanceError",
    "CalendarUnapprovedError",
    "ValidatedCalendar",
    "assert_calendar_provenance",
    "calendar_content_digest",
    "recompute_content_digest",
    "validate_calendar",
]
