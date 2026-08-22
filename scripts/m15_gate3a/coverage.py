"""Coverage as **set equality** per pair (D-5, D-10 / NR-J, §12.8).

For every pair::

    actual_certified_m15_slots  ==  expected_m15_slots

Set equality, not min/max containment. The contract Gate-decision records why
containment was insufficient: ``DESIGN_START`` is a floor on ``ts_min``, not a
coverage requirement, so a derivation truncated to **one day** — or to a single
instant — earned the identical token as the full ten-month span, with
``files_checked=20`` beside it. Only set equality closes that.

**Scope boundary.** This module is pure: it consumes measurement records a
caller already produced and decides. It opens no file, derives no M15, and
measures no byte. The byte-reading producer/verifier packages that supply real
measurements sit at a later gate (contract §15.4); an interface is not a proof.

**Fail-closed, never report-only** (D-10 / NR-J): insufficient required coverage
**raises**. Recording a coverage flag never permits continuation, so there is no
success value that means "coverage was short" and no parameter that downgrades
the refusal to a report.

**The expected set is never narrowed to what was observed** (D-6.1). Expected
slots come only from the injected :class:`~scripts.m15_gate3a.calendar_authority.ValidatedCalendar`;
a pair measured with zero slots produces a coverage failure, never an empty
expectation that trivially matches. Nothing here creates a slot, so no weekend
or closure bar can be synthesised (D-6.3).

Minute accounting
-----------------
The six-field schema ruled in D-3 is consumed verbatim from the aggregation
report (``report["minute_accounting"]``), including the identity
``expected == usable + absent + rejected``. Coverage cross-checks it against the
measured slot set: unusable minutes must show up as missing slots, and a slot
whose bucket could not be constituted because a source minute was rejected is
**not counted as covered** (D-2.5, D-5.7). The totals are supplied by the same
caller as the bars, so they are never the *only* certifiability check —
:func:`_assert_bar_certifiable` reads each bar's own fields (D-3.5, §12.7).

D-5.8, as ruled
---------------
``D5_8_RULED_NO_NUMERIC_FLOOR_TRUSTED_CALENDAR_PROVENANCE_AND_SET_EQUALITY_REQUIRED``.
The earlier revision of this docstring referred the "single instant, or a sparse
handful of points" clause to a later contract Gate-decision, and that decision
has now been taken. It rules **no numeric minimum slot-count floor**, on the
evidence that a rule closing over the derivation clears a count floor, a
temporal-extent criterion and a continuity criterion simultaneously — so a count
is not the trust axis and a floor would not touch the defect it appears to
address. **No slot-count threshold exists in this module and none may be added.**

What discharges the clause instead is **trusted calendar provenance plus set
equality**, and requirement 4 fixes the order: coverage is recognised only after
**both** the set-equality limbs **and** calendar-provenance validation hold. So
:func:`assert_full_coverage` runs every §8 limb first and then re-derives the
calendar's content digest, through
:func:`~scripts.m15_gate3a.calendar_authority.assert_calendar_provenance`.
Placement is ruled too: a check sited only in ``validate_calendar`` is bypassed
by a forged record, and a check sited *before* the set-equality limbs takes over
the guard identity of six existing refusals.

Counts survive as **diagnostics** (requirement 8): :class:`PairCoverage` carries
the expected and certified cardinalities, and they are read from the members
iteration actually yields rather than from an object's own ``__len__``. Also
enforced, and mints nothing: the arithmetic relation between the calendar's slot
count and the declared source-minute count, so the two cannot describe different
epochs. ``PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED`` — the human +
ChatGPT approval of the concrete artifact — remains open and is not discharged
by anything here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

from scripts.m15_gate3a.calendar_authority import (
    SLOT_MINUTES,
    CalendarConstructionError,
    ValidatedCalendar,
    assert_calendar_provenance,
)
from scripts.m15_gate3a.no_overlap import DESIGN_END, DESIGN_START, is_dead_window_instant
from scripts.m15_gate3a.numeric_authority import NumericAuthorityError, pin_int
from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair
from scripts.m15_gate3a.sealing import assert_minted, register_minted, seal
from scripts.m15_gate3a.timeutil import TimestampError, to_utc

#: The six separately-measured quantities ruled in D-3 §5, emitted by the
#: aggregation report as ``report["minute_accounting"]``.
MINUTE_ACCOUNTING_FIELDS: Final[tuple[str, ...]] = (
    "expected_source_minute_count",
    "observed_source_minute_count",
    "absent_source_minute_count",
    "rejected_source_minute_count",
    "usable_source_minute_count",
    "max_unavailable_gap_minutes",
)

#: Key under which a bar declares its bucket start.
BAR_SLOT_KEY: Final[str] = "ts"

#: Keys under which a bar declares whether its bucket could be constituted from
#: **every** contract-required source minute (D-3.5 / §12.7). ``eligible`` is the
#: frozen derivation manifest's retained alias of ``complete_bucket`` — the same
#: measured quantity under two committed spellings, never a second measurement,
#: which is why the two are required to agree rather than either being trusted.
BAR_SOURCE_MINUTE_KEY: Final[str] = "n_source_bars"
BAR_COMPLETE_KEY: Final[str] = "complete_bucket"
BAR_COMPLETE_ALIAS_KEY: Final[str] = "eligible"


class CoverageError(RuntimeError):
    """Base class: certified coverage does not equal the expected slot set."""


class CoverageEvidenceError(CoverageError):
    """The measurement evidence itself is unusable, so nothing can be certified."""


class CoverageMeasurementMissingError(CoverageError):
    """A pair was not measured; a missing measurement is unsatisfied (D-5.3)."""


class CoverageSetMismatchError(CoverageError):
    """Certified slots are not equal to the expected slots for some pair (D-5)."""


class RejectedSlotCountedCoveredError(CoverageError):
    """A slot whose bucket could not be constituted was counted as covered (D-5.7)."""


class MinuteAccountingError(CoverageError):
    """The six-field minute accounting is absent, malformed, or self-contradictory."""


class BarNotCertifiableError(CoverageError):
    """A bar without every contract-required source minute was offered (D-3.5)."""


class CoverageConstructionError(CoverageError):
    """A coverage record was built outside the function that measures it."""


class _CoverageConstructionToken:
    """One-shot capability to construct one coverage record.

    ``PairSlotMeasurement`` and ``CoverageResult`` are public frozen dataclasses,
    so "built only by ..." was a docstring and nothing more. The data-integrity
    audit hand-built a ``CoverageResult`` with ``expected_slot_count=0`` and
    ``calendar_digest="NO CALENDAR EVER EXISTED"`` and fed it to the proof's CV
    limb. The token makes the *public-API* route impossible and is spent by the
    first construction, so :func:`dataclasses.replace` cannot mint a variant from
    a real record's token either.

    ``purpose`` keeps the two record types' capabilities distinct: a token minted
    to build a measurement cannot be redirected into a result.

    **What it does not do.** Python has no enforced privacy; a caller reaching
    into this module's private names can mint a token, and
    ``object.__setattr__`` can still tamper with a real record after the fact.
    That is why :func:`assert_full_coverage` and the proof's CV limb re-check the
    invariants they depend on instead of trusting the type alone.

    **N-5 — the copy protocols were a public-API route and are now closed.** An
    earlier revision of this docstring said the token "makes the *public-API*
    route impossible". That was false: ``copy.copy``, ``copy.deepcopy`` and
    ``pickle`` are all public API and all reconstruct a frozen ``slots``
    dataclass through ``__reduce_ex__`` **without calling ``__post_init__``**, so
    each one minted a fresh record having spent no token. The audit drove two
    forged ``ValidatedCalendar`` objects (``authority="THE OBSERVED DATA
    ITSELF"``) to a satisfied ``CoverageResult`` that way. Every token-bearing
    record in this package now refuses all three (:func:`_refuse_reconstruction`).
    ``dataclasses.replace`` and subclassing were already refused. What remains
    open — and is stated rather than claimed away — is that a caller reaching
    into private names, or using ``object.__setattr__`` on a real record, is
    still not stopped by any of this; the re-checks are what cover that.
    """

    __slots__ = ("purpose", "spent")

    def __init__(self, purpose: str) -> None:
        self.purpose = purpose
        self.spent = False


def _refuse_reconstruction(self: Any, *_args: Any) -> None:
    """Refuse ``copy.copy`` / ``copy.deepcopy`` / ``pickle`` (N-5).

    All three rebuild the instance without running ``__post_init__``, so all
    three re-mint a construction-token-bearing record for free. A record that
    only :func:`measure_pair_coverage` or :func:`assert_full_coverage` may mint
    is not a value that may be duplicated: a second copy asserts a second
    measurement that never happened.
    """
    raise CoverageConstructionError(
        f"a {type(self).__name__} may not be copied, deep-copied or pickled; those protocols "
        "rebuild the record without spending a construction token, so the copy would assert a "
        "measurement that was never made"
    )


_MEASUREMENT_PURPOSE: Final[str] = "PairSlotMeasurement"
_RESULT_PURPOSE: Final[str] = "CoverageResult"


@seal(error=CoverageConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False)
class PairSlotMeasurement:
    """What was actually measured for one pair. Built only by :func:`measure_pair_coverage`.

    Carrying the slot **set** rather than a count is the point: D-5.9 rules that
    ``n_pairs == 20`` alone is not coverage proof, and a count of certified bars
    is the same kind of non-evidence one level down.

    ``eq=False`` — **identity equality, deliberately.** Two calls to
    :func:`measure_pair_coverage` with identical inputs are two separate
    measurements, and treating them as one value is the confusion
    :func:`_refuse_reconstruction` already refuses in the copy direction ("a
    second copy asserts a second measurement that never happened").

    That semantic reason is now the **only** one. An earlier revision of this
    docstring also argued that ``eq=False`` was what made the record
    *registrable*, because the sealing registry was a ``WeakSet`` and a
    field-derived hash over the ``Mapping`` field could not exist. The registry
    was subsequently keyed on ``id()`` with an identity re-check
    (:mod:`~scripts.m15_gate3a.sealing`), which imposes no equality semantics at
    all — so that half of the justification is **withdrawn as obsolete** rather
    than left standing as a reason that is no longer true.
    """

    pair: str
    certified_slots: frozenset[datetime]
    duplicate_slots: tuple[datetime, ...]
    rejected_slots: frozenset[datetime]
    minute_accounting: Mapping[str, int]
    _construction_token: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        token = self._construction_token
        if (
            not isinstance(token, _CoverageConstructionToken)
            or token.purpose != _MEASUREMENT_PURPOSE
            or token.spent
        ):
            raise CoverageConstructionError(
                "a PairSlotMeasurement is minted only by measure_pair_coverage(); a hand-built "
                "instance is a caller's assertion about what an artifact contains, not a "
                "measurement of it, and cannot certify a slot"
            )
        token.spent = True
        object.__setattr__(self, "_construction_token", None)
        # FB-1 / FR-3: the token is spent inside `__post_init__`, and
        # `object.__new__` never runs `__post_init__`. Registration is therefore
        # the only property a consumer can check that a forgery cannot fake.
        register_minted(self)

    # N-5: the audit named four record types; this is the fifth of the same
    # family. A deep-copied measurement is a second pair's worth of certified
    # slots that `measure_pair_coverage` never measured.
    __copy__ = _refuse_reconstruction
    __deepcopy__ = _refuse_reconstruction
    __reduce__ = _refuse_reconstruction


@seal(error=CoverageConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True)
class PairCoverage:
    """The set-equality verdict for one pair, for the proof record.

    There is no ``satisfied`` flag here. R-1 deletes a field that can only ever
    hold one value, and once :func:`assert_full_coverage` raises on every
    inequality the flag could only ever have been ``True`` — the audit's
    ``aggregate_assertions`` defect, one level down. The counts and the span are
    what was actually measured, and they vary with the evidence.

    **``certified_slot_min`` / ``certified_slot_max`` exist to close audit FR-4.**
    The proof's CV limb bound coverage to the byte scan by **cardinality alone**,
    so coverage certified for one month and a byte scan measured over another
    satisfied the four-limb conjunction together — the audit reproduced exactly
    that with a May slot set and a December scan. A count cannot express *which*
    slots were certified, and this layer is the only one that holds the slot set,
    so the span has to be published from here or the binding cannot exist at all.
    These are **measured** quantities, not a threshold: they are `min` and `max`
    of the set the equality limbs just certified, so they mint no number and
    D-5.8's prohibition on count-shaped acceptance criteria is untouched.
    """

    pair: str
    expected_slot_count: int
    certified_slot_count: int
    certified_slot_min: datetime
    certified_slot_max: datetime

    def __post_init__(self) -> None:
        # No construction token: this record carries only two counts already
        # published inside a `CoverageResult`, and refusing hand construction
        # would add a token without adding an authority. It is registered
        # anyway, so a consumer that wants to distinguish an entry
        # `assert_full_coverage` built from one `object.__new__` produced can.
        register_minted(self)


@seal(error=CoverageConstructionError)
@dataclass(frozen=True, slots=True, weakref_slot=True)
class CoverageResult:
    """Coverage over the whole roster: the conjunction across 20 measured pairs.

    Only ever returned when every pair satisfied set equality — insufficient
    coverage raises (D-10), so this object never describes a failure. Its
    *existence* is therefore the conjunction (D-8 / NR-C); it carries no
    ``satisfied`` flag, for the R-1 reason recorded on :class:`PairCoverage`.

    **R-1 / N-4 — ``pairs_measured`` is deleted, not reported.** It was assigned
    ``tuple(PAIRS_20)`` unconditionally, never derived from the evidence, and
    could not hold another value: the roster is fixed and a short roster already
    raises :class:`CoverageMeasurementMissingError` above. It asserted a
    *favourable* property — precisely the ``n_pairs == 20`` non-evidence D-5.9
    names — and the identically-named field on ``ProofResult`` had already been
    deleted for that reason, so this was the same defect surviving one module
    over. What was measured is in :attr:`per_pair`, whose entries carry counts
    that vary with the evidence, and ``tuple(c.pair for c in per_pair)`` recovers
    the roster from measurement rather than from an assertion. The remaining
    constants on this package's records (``files_opened=0``,
    ``bytes_measured=0``, the evidence bases, the withheld-claim reason) stay:
    each is a **disclaimer** of something not done, which R-1 keeps.
    """

    calendar_digest: str
    calendar_epoch: str
    per_pair: tuple[PairCoverage, ...]
    _construction_token: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        token = self._construction_token
        if (
            not isinstance(token, _CoverageConstructionToken)
            or token.purpose != _RESULT_PURPOSE
            or token.spent
        ):
            raise CoverageConstructionError(
                "a CoverageResult is minted only by assert_full_coverage(); a hand-built "
                "instance asserts a 20-pair conjunction that was never evaluated"
            )
        token.spent = True
        object.__setattr__(self, "_construction_token", None)
        register_minted(self)

    __copy__ = _refuse_reconstruction
    __deepcopy__ = _refuse_reconstruction
    __reduce__ = _refuse_reconstruction


def _materialise_bars(bars: Any, *, pair: str) -> tuple[dict, ...]:
    """Re-scannable, identity-distinct bar evidence, or refuse it.

    The same BL-1 guard ``no_overlap._materialise`` carries, for the same
    reason: a ``Sequence`` ABC does not force ``__len__`` to agree with
    iteration, and one Mapping object presented many times with a walking
    ``ts`` can forge a slot set out of a single bar (the shape audit RF-4 found
    in aggregation).
    """
    if isinstance(bars, (str, bytes, bytearray)) or not isinstance(bars, Sequence):
        raise CoverageEvidenceError(
            f"{pair}: certified bars must be a concrete sequence, got {type(bars).__name__}"
        )
    try:
        declared = len(bars)
        first = tuple(bars)
        second = tuple(bars)
    except (TypeError, ValueError) as exc:
        raise CoverageEvidenceError(f"{pair}: bar evidence could not be re-scanned: {exc}") from exc
    if len(first) != declared or len(second) != declared:
        raise CoverageEvidenceError(
            f"{pair}: __len__ reports {declared} bars but iteration yields "
            f"{len(first)}/{len(second)} (bar evidence is not self-consistent)"
        )
    identities: dict[int, int] = {}
    snapshot: list[dict] = []
    for index, record in enumerate(first):
        if not isinstance(record, Mapping):
            raise CoverageEvidenceError(
                f"{pair}: bar {index} must be a mapping, got {type(record).__name__}"
            )
        if id(record) in identities:
            raise CoverageEvidenceError(
                f"{pair}: the same bar object appears at indices {identities[id(record)]} "
                f"and {index}; one bar cannot certify two slots"
            )
        identities[id(record)] = index
        try:
            snapshot.append(dict(record))
        except Exception as exc:  # noqa: BLE001 - a bar that cannot be read fails closed
            raise CoverageEvidenceError(f"{pair}: bar {index} could not be read: {exc}") from exc
    return tuple(snapshot)


def _normalise_slot(raw: Any, *, pair: str, what: str) -> datetime:
    try:
        slot = to_utc(raw)
    except TimestampError as exc:
        raise CoverageEvidenceError(
            f"{pair}: {what} timestamp is not an exact UTC instant: {exc}"
        ) from exc
    if slot.minute % SLOT_MINUTES or slot.second or slot.microsecond:
        raise CoverageEvidenceError(
            f"{pair}: {what} timestamp {slot.isoformat()} does not fall on the frozen "
            f"{SLOT_MINUTES}-minute UTC bucket grid"
        )
    if is_dead_window_instant(slot):
        raise CoverageEvidenceError(
            f"{pair}: {what} timestamp {slot.isoformat()} falls inside the consumed dead window"
        )
    # CV and TC used to constrain disjoint evidence: TC bounded the *scanned*
    # span by the frozen design epoch while coverage bounded nothing but the
    # dead window, so a slot certified outside `[DESIGN_START, DESIGN_END]`
    # passed coverage untouched. The epoch constants are the committed ones
    # (D-5.10); nothing here redefines a boundary.
    if slot < DESIGN_START or slot > DESIGN_END:
        raise CoverageEvidenceError(
            f"{pair}: {what} timestamp {slot.isoformat()} lies outside the frozen design epoch "
            f"[{DESIGN_START.isoformat()}, {DESIGN_END.isoformat()}]"
        )
    return slot


def _validate_minute_accounting(raw: Any, *, pair: str) -> dict[str, int]:
    """The six D-3 quantities, present, integral, non-negative, and self-consistent.

    **FR-9 — "self-consistent" now covers all six.** It used to cover four: the
    identity ``expected == usable + absent + rejected`` binds those, and
    ``observed_source_minute_count`` and ``max_unavailable_gap_minutes`` stood in
    no relation to anything. ``observed=999999`` beside ``usable=60``,
    ``observed=0`` beside ``usable=60``, and ``max_unavailable_gap_minutes=999999``
    beside ``absent = rejected = 0`` all validated. Two further relations follow
    from D-3's own definitions and mint no number:

    * a **usable** minute and a **rejected** minute were both *present in the
      source*, and they are disjoint, so ``observed >= usable + rejected``;
    * ``max_unavailable_gap_minutes`` is the longest **run** of consecutive
      expected-but-not-usable minutes, and there are ``absent + rejected`` such
      minutes in total, so ``max_unavailable_gap_minutes <= absent + rejected``.

    Neither is a threshold: each is an inequality between two of the caller's own
    numbers, so no constant is introduced and no minimum is decided.

    **What is still unbounded, and why it is left so.** ``observed`` above
    ``usable + rejected`` describes minutes that were *present in the source but
    not expected by the calendar*, and D-3's six-field schema has no field for
    them: the schema partitions the **expected** minutes only. Deciding whether
    such a minute may exist — and what it means if it does — is a market-hours
    question the calendar artifact owns and §9 deliberately leaves unfixed, so no
    upper bound is asserted here. FR-9's first example
    (``observed = 999999`` beside ``usable = 60``) therefore still validates at
    this layer, and that is recorded rather than closed with an invented rule.
    """
    if raw is None:
        raise MinuteAccountingError(
            f"{pair}: minute_accounting absent; coverage cannot be decided without the "
            "six separately-measured minute quantities"
        )
    if not isinstance(raw, Mapping):
        raise MinuteAccountingError(
            f"{pair}: minute_accounting must be a mapping, got {type(raw).__name__}"
        )
    snapshot = dict(raw)
    missing = [k for k in MINUTE_ACCOUNTING_FIELDS if k not in snapshot]
    if missing:
        raise MinuteAccountingError(f"{pair}: minute_accounting is missing {missing}")
    extra = [k for k in snapshot if k not in MINUTE_ACCOUNTING_FIELDS]
    if extra:
        raise MinuteAccountingError(
            f"{pair}: minute_accounting carries unrecognised keys {sorted(extra)}; the "
            "six-field schema is closed"
        )
    values: dict[str, int] = {}
    for key in MINUTE_ACCOUNTING_FIELDS:
        value = snapshot[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise MinuteAccountingError(
                f"{pair}: minute_accounting[{key!r}] must be an int, got {type(value).__name__}"
            )
        # N-1: pin the character data before `< 0` and before the identity
        # arithmetic below. An `int` subclass owns `__lt__`, `__eq__` and
        # `__add__`, so an unpinned accounting block could report six numbers
        # that satisfy every check while holding six different values.
        #
        # FR-20: the `# pragma: no cover - guarded above` that sat here asserted
        # that the `isinstance` above makes this branch unreachable. It does not:
        # `isinstance` consults `__class__`, which any object may claim, while
        # the unbound `int.__index__` slot then refuses — so an object declaring
        # `__class__ = int` reaches exactly this line. The pragma is removed and
        # the branch is pinned by test instead (§13 names a pragma on a reachable
        # guard as an anti-pattern).
        try:
            value = pin_int(value, what=f"minute_accounting[{key!r}]")
        except NumericAuthorityError as exc:
            raise MinuteAccountingError(f"{pair}: {exc}") from exc
        if value < 0:
            raise MinuteAccountingError(f"{pair}: minute_accounting[{key!r}] is negative ({value})")
        values[key] = value
    expected = values["expected_source_minute_count"]
    usable = values["usable_source_minute_count"]
    absent = values["absent_source_minute_count"]
    rejected = values["rejected_source_minute_count"]
    total = usable + absent + rejected
    if expected != total:
        raise MinuteAccountingError(
            f"{pair}: minute accounting identity violated — expected {expected} != "
            f"usable+absent+rejected {total}"
        )
    observed = values["observed_source_minute_count"]
    if observed < usable + rejected:
        raise MinuteAccountingError(
            f"{pair}: minute accounting reports {observed} observed source minute(s) while "
            f"{usable + rejected} of them are classified usable or rejected; both kinds were "
            "present in the source, so the observed count can never be the smaller"
        )
    unavailable_run = values["max_unavailable_gap_minutes"]
    if unavailable_run > absent + rejected:
        raise MinuteAccountingError(
            f"{pair}: minute accounting reports a longest unavailable run of {unavailable_run} "
            f"minute(s) while only {absent + rejected} expected minute(s) are unavailable at "
            "all; a run cannot be longer than the set it is drawn from"
        )
    return values


def _assert_bar_certifiable(bar: Mapping[str, Any], *, pair: str, index: int) -> None:
    """D-3.5 / §12.7: a certified bar has **every** contract-required source minute.

    The refusal text one level up already said "a bar assembled from fewer than
    all its contract-required minutes is not certifiable", but the only check was
    on the minute-accounting *totals* — supplied by the same caller as the bars.
    The adversarial workstream drove 20 pairs of ``n_source_bars=1,
    complete_bucket=False`` bars to a satisfied coverage conjunction. The bar's
    own fields are what decide certifiability, so they are what is read here.
    """
    if BAR_SOURCE_MINUTE_KEY not in bar:
        raise BarNotCertifiableError(
            f"{pair}: bar {index} declares no {BAR_SOURCE_MINUTE_KEY!r}, so nothing states how "
            "many contract-required source minutes constituted its bucket"
        )
    n_source = bar[BAR_SOURCE_MINUTE_KEY]
    if isinstance(n_source, bool) or not isinstance(n_source, int):
        raise BarNotCertifiableError(
            f"{pair}: bar {index} declares {BAR_SOURCE_MINUTE_KEY!r} as "
            f"{type(n_source).__name__}, not a counted number of source minutes"
        )
    # N-1: an `int` subclass owns `__eq__`, so the count that decides
    # certifiability is read as plain character data before it is compared.
    # FR-20: reachable, for the reason recorded in `_validate_minute_accounting`
    # — `isinstance` consults `__class__` and `int.__index__` then refuses. The
    # pragma that claimed unreachability is removed and the branch is tested.
    try:
        n_source = pin_int(n_source, what=f"bar {index} {BAR_SOURCE_MINUTE_KEY!r}")
    except NumericAuthorityError as exc:
        raise BarNotCertifiableError(f"{pair}: {exc}") from exc
    if n_source != SLOT_MINUTES:
        raise BarNotCertifiableError(
            f"{pair}: bar {index} was constituted from {n_source} of the {SLOT_MINUTES} "
            "contract-required source minutes; a bar assembled from fewer than all of them is "
            "not certifiable and never contributes a certified slot"
        )
    if BAR_COMPLETE_KEY not in bar:
        raise BarNotCertifiableError(
            f"{pair}: bar {index} declares no {BAR_COMPLETE_KEY!r} certifiability flag"
        )
    complete = bar[BAR_COMPLETE_KEY]
    if not isinstance(complete, bool):
        raise BarNotCertifiableError(
            f"{pair}: bar {index} declares {BAR_COMPLETE_KEY!r} as {type(complete).__name__}, "
            "not a measured boolean"
        )
    if not complete:
        raise BarNotCertifiableError(
            f"{pair}: bar {index} is flagged {BAR_COMPLETE_KEY}=False and is therefore not "
            "certifiable; an incomplete bucket never contributes a certified slot"
        )
    if BAR_COMPLETE_ALIAS_KEY in bar and bar[BAR_COMPLETE_ALIAS_KEY] is not complete:
        raise BarNotCertifiableError(
            f"{pair}: bar {index} declares {BAR_COMPLETE_KEY}={complete!r} but its retained "
            f"alias {BAR_COMPLETE_ALIAS_KEY}={bar[BAR_COMPLETE_ALIAS_KEY]!r}; the two committed "
            "spellings name one measured quantity and cannot disagree"
        )


def measure_pair_coverage(
    *,
    pair: object,
    certified_bars: Any,
    minute_accounting: Any,
    rejected_slots: Any,
) -> PairSlotMeasurement:
    """Turn one pair's aggregation output into the slot set it actually certifies.

    ``rejected_slots`` is **required**, not defaulted: a caller that says nothing
    about which buckets a rejection destroyed would otherwise be silently
    claiming there were none, which is exactly the "rejected minute counted as
    covered" failure D-2.5 forbids. Pass an empty sequence to state that
    explicitly.
    """
    try:
        canonical = canonical_pair(pair)
    except PairAuthorityError as exc:
        raise CoverageEvidenceError(f"coverage measured for an unusable pair name: {exc}") from exc

    accounting = _validate_minute_accounting(minute_accounting, pair=canonical)

    bars = _materialise_bars(certified_bars, pair=canonical)
    seen: dict[datetime, int] = {}
    duplicates: list[datetime] = []
    for index, bar in enumerate(bars):
        if BAR_SLOT_KEY not in bar:
            raise CoverageEvidenceError(
                f"{canonical}: bar {index} declares no {BAR_SLOT_KEY!r} bucket start"
            )
        _assert_bar_certifiable(bar, pair=canonical, index=index)
        slot = _normalise_slot(bar[BAR_SLOT_KEY], pair=canonical, what="certified bar")
        if slot in seen:
            duplicates.append(slot)
        else:
            seen[slot] = index

    rejected = _materialise_rejected(rejected_slots, pair=canonical)
    overlap = sorted(rejected & frozenset(seen))
    if overlap:
        raise RejectedSlotCountedCoveredError(
            f"{canonical}: slot {overlap[0].isoformat()} is certified as covered while also "
            "reported as a bucket that could not be constituted; a bucket lost to a rejected "
            "source minute is never counted as covered"
        )

    return PairSlotMeasurement(
        pair=canonical,
        certified_slots=frozenset(seen),
        duplicate_slots=tuple(duplicates),
        rejected_slots=rejected,
        minute_accounting=accounting,
        _construction_token=_CoverageConstructionToken(_MEASUREMENT_PURPOSE),
    )


def _materialise_rejected(raw: Any, *, pair: str) -> frozenset[datetime]:
    if isinstance(raw, (str, bytes, bytearray)) or not isinstance(raw, Sequence):
        raise CoverageEvidenceError(
            f"{pair}: rejected_slots must be a concrete sequence, got {type(raw).__name__}"
        )
    return frozenset(
        _normalise_slot(item, pair=pair, what="rejected bucket") for item in tuple(raw)
    )


def _pinned_slot_set(slots: Any, *, pair: str, what: str) -> frozenset[datetime]:
    """A plain ``frozenset`` of plain UTC instants, built from what iteration yields.

    Every set operation below — ``-``, ``==``, ``len`` — is a question the
    caller's own object would otherwise answer. The audit's second D-5.8 probe is
    exactly that: a ``frozenset`` subclass lying only about ``__len__`` produced a
    **successfully returned** ``CoverageResult`` whose own record read
    ``expected_slot_count=21000, certified_slot_count=1``, and nothing compared
    the two. Ruling §4.9 asks for that comparison; this is the same closure one
    step earlier and strictly stronger, because it refuses the lying object
    instead of detecting one of its consequences — the ``__sub__`` and ``__eq__``
    variants of the same family are closed by the same move.

    This is the ``_materialise_bars`` pattern applied to sets: read the members
    once, check the declared cardinality against the scanned one, and decide
    everything afterwards against the plain rebuild. ``to_utc`` re-pins each
    instant, so a ``datetime`` subclass cannot carry its own equality into the
    set algebra either.
    """
    if isinstance(slots, (str, bytes, bytearray)) or not isinstance(slots, Set):
        raise CoverageEvidenceError(
            f"{pair}: {what} slots must be a set, got {type(slots).__name__}; coverage is "
            "decided over a materialised set, never over an object asked to describe itself"
        )
    try:
        declared = len(slots)
        scanned = tuple(slots)
    except (TypeError, ValueError) as exc:
        raise CoverageEvidenceError(
            f"{pair}: {what} slot set could not be re-scanned: {exc}"
        ) from exc
    if len(scanned) != declared:
        raise CoverageEvidenceError(
            f"{pair}: {what} slot set reports {declared} member(s) but iteration yields "
            f"{len(scanned)}; a cardinality an object states about itself is not a measurement"
        )
    try:
        pinned = frozenset(to_utc(slot) for slot in scanned)
    except TimestampError as exc:
        raise CoverageEvidenceError(
            f"{pair}: {what} slot set carries an instant that is not exact UTC: {exc}"
        ) from exc
    if len(pinned) != declared:
        raise CoverageEvidenceError(
            f"{pair}: {what} slot set reports {declared} member(s) but they resolve to "
            f"{len(pinned)} distinct UTC instant(s); two spellings of one instant are one slot"
        )
    return pinned


def _roster(measurements: Any) -> dict[str, PairSlotMeasurement]:
    if isinstance(measurements, (str, bytes, bytearray)) or not isinstance(measurements, Sequence):
        raise CoverageEvidenceError(
            f"measurements must be a concrete sequence of PairSlotMeasurement, "
            f"got {type(measurements).__name__}"
        )
    by_pair: dict[str, PairSlotMeasurement] = {}
    for index, item in enumerate(tuple(measurements)):
        if not isinstance(item, PairSlotMeasurement):
            # A dict of counts is the "expected_count-only proof" shape: it can
            # report `n_pairs == 20` while describing no slot at all (D-5.9).
            raise CoverageEvidenceError(
                f"measurement {index} is a {type(item).__name__}, not a measured "
                "PairSlotMeasurement; counts are not coverage evidence"
            )
        # FB-1 / FR-3: `isinstance` is satisfied by anything whose `__class__`
        # says so, and `object.__new__(PairSlotMeasurement)` produces a real
        # instance of the real class with `__post_init__` never run. The registry
        # is the discriminator: a forgery was never minted, so it is absent.
        assert_minted(
            item,
            what=f"coverage measurement {index}",
            error=CoverageConstructionError,
        )
        if item.pair in by_pair:
            raise CoverageEvidenceError(
                f"{item.pair} is measured twice in the coverage roster; after "
                "canonicalisation each pair is measured exactly once"
            )
        by_pair[item.pair] = item
    unknown = sorted(set(by_pair) - set(PAIRS_20))
    # NOT pragma'd, for the reason `_limb_cv` gives for re-checking the roster:
    # `canonical_pair` bounds what construction accepts, not what a record holds
    # afterwards, and an audit reached this branch with `object.__setattr__`.
    if unknown:
        raise CoverageEvidenceError(f"measurements name pairs outside PAIRS_20: {unknown}")
    return by_pair


def assert_full_coverage(
    measurements: Any, calendar: Any, *, expected_epoch: str
) -> CoverageResult:
    """Set equality for every pair in PAIRS_20, or raise (D-5, D-10).

    Returns only on the full 20-pair conjunction. There is no report-only mode
    and no tolerance parameter: D-2 rules the rejection tolerance zero and
    *structural*, and D-10 rules that insufficient coverage raises rather than
    being recorded as a flag.

    **Order, ruled (D-5.8 requirement 4 and §4.9).** The set-equality limbs run
    first, per pair; calendar-provenance validation runs after them, over the
    whole roster, and only then is a :class:`CoverageResult` minted. Nothing here
    tests a slot count against a threshold, because no threshold exists.
    """
    if not isinstance(calendar, ValidatedCalendar):
        raise CoverageEvidenceError(
            f"coverage requires a validated calendar authority, got {type(calendar).__name__}; "
            "an unvalidated calendar is not the coverage authority"
        )
    # FB-1 / FR-3, at the authority boundary rather than only at validation.
    # `isinstance` above is satisfied by `object.__new__(ValidatedCalendar)`,
    # which ran no validation at all; the registry is what tells them apart.
    # This precedes the limbs deliberately and takes over no guard identity:
    # every existing set-equality test supplies a genuinely minted calendar, so
    # none of the six refusals §4.9 names can be answered here instead.
    assert_minted(
        calendar,
        what="the calendar authority offered to coverage",
        error=CalendarConstructionError,
    )
    # FB-5: this was the one unpinned comparison of the pair — `validate_calendar`
    # pins the identical epoch bind correctly, so the two sides of one contract
    # disagreed, and a two-faced `str` subclass was accepted here where the plain
    # value raised. Both operands are read as plain character data before the
    # comparison decides anything.
    if not isinstance(expected_epoch, str):
        raise CoverageEvidenceError(
            f"expected_epoch must be a string naming the epoch being certified, got "
            f"{type(expected_epoch).__name__}"
        )
    if not isinstance(calendar.target_epoch, str):
        raise CoverageEvidenceError(
            f"the calendar's target epoch is a {type(calendar.target_epoch).__name__}, not a "
            "string; an epoch that is not character data binds nothing"
        )
    if str.__str__(calendar.target_epoch) != str.__str__(expected_epoch):
        raise CoverageEvidenceError(
            f"calendar targets epoch {calendar.target_epoch!r} but coverage is being "
            f"certified for {expected_epoch!r}"
        )

    by_pair = _roster(measurements)
    missing_pairs = [p for p in PAIRS_20 if p not in by_pair]
    if missing_pairs:
        raise CoverageMeasurementMissingError(
            f"no coverage measurement for {missing_pairs}; a missing measurement is "
            "unsatisfied, never treated as satisfied"
        )

    per_pair: list[PairCoverage] = []
    pinned_by_pair: dict[str, frozenset[datetime]] = {}
    for pair in PAIRS_20:
        measurement = by_pair[pair]
        expected = _pinned_slot_set(calendar.expected_slots(pair), pair=pair, what="expected")
        pinned_by_pair[pair] = expected
        certified = _pinned_slot_set(measurement.certified_slots, pair=pair, what="certified")

        # Defence in depth, and REACHABLE: `validate_calendar` and
        # `measure_pair_coverage` both refuse a dead-window slot, but neither
        # frozen dataclass is sealed — `object.__setattr__` replaces the slot
        # mapping of a real, validated calendar, and no construction token can
        # close that route. The consumed M1 holdout must never be counted as
        # covered by any role, so the set that coverage actually decides over is
        # re-checked here rather than inherited on trust.
        for slot in sorted(expected):
            if is_dead_window_instant(slot):
                raise CoverageEvidenceError(
                    f"{pair}: the calendar expects slot {slot.isoformat()}, which lies inside "
                    "the consumed dead window; no role may expect a dead-window slot"
                )
            if slot < DESIGN_START or slot > DESIGN_END:
                raise CoverageEvidenceError(
                    f"{pair}: the calendar expects slot {slot.isoformat()} outside the frozen "
                    f"design epoch [{DESIGN_START.isoformat()}, {DESIGN_END.isoformat()}]"
                )
        for slot in sorted(certified):
            if is_dead_window_instant(slot):
                raise CoverageEvidenceError(
                    f"{pair}: slot {slot.isoformat()} is certified as covered while lying "
                    "inside the consumed dead window"
                )

        if measurement.duplicate_slots:
            slot = sorted(measurement.duplicate_slots)[0]
            raise CoverageSetMismatchError(
                f"{pair}: slot {slot.isoformat()} is certified more than once; a duplicate "
                "certified slot is a coverage defect, never a larger coverage"
            )

        absent = sorted(expected - certified)
        if absent:
            raise CoverageSetMismatchError(
                f"{pair}: {len(absent)} expected M15 slot(s) are not certified, first "
                f"{absent[0].isoformat()}; certified coverage must contain every expected slot"
            )

        unexpected = sorted(certified - expected)
        if unexpected:
            raise CoverageSetMismatchError(
                f"{pair}: {len(unexpected)} certified M15 slot(s) are not expected by the "
                f"calendar, first {unexpected[0].isoformat()}; an unexpected slot is never "
                "absorbed into the expected set"
            )

        unusable = (
            measurement.minute_accounting["absent_source_minute_count"]
            + measurement.minute_accounting["rejected_source_minute_count"]
        )
        if unusable:
            raise CoverageSetMismatchError(
                f"{pair}: minute accounting reports {unusable} expected-but-unusable source "
                "minute(s) while every expected slot is certified; a bar assembled from "
                "fewer than all its contract-required minutes is not certifiable"
            )

        # The minute accounting and the calendar are two independently supplied
        # quantities that describe the same epoch, and under the frozen
        # 15-minute grid (D-3.5: every contract-required minute usable) the
        # relation between them is arithmetic, not a threshold: an epoch of
        # `len(expected)` buckets expects exactly `15 * len(expected)` source
        # minutes. Binding them stops an accounting block that describes ten
        # months from sitting beside a calendar that declares three slots.
        expected_minutes = measurement.minute_accounting["expected_source_minute_count"]
        if expected_minutes != SLOT_MINUTES * len(expected):
            raise MinuteAccountingError(
                f"{pair}: minute accounting expects {expected_minutes} source minute(s) while "
                f"the calendar expects {len(expected)} M15 slot(s), which the frozen "
                f"{SLOT_MINUTES}-minute grid constitutes from "
                f"{SLOT_MINUTES * len(expected)}; the two describe different epochs"
            )

        # Requirement 8: the counts are a recorded diagnostic, never an
        # acceptance authority. They are the cardinalities of the pinned sets, so
        # what is published is what was scanned.
        per_pair.append(
            PairCoverage(
                pair=pair,
                expected_slot_count=len(expected),
                certified_slot_count=len(certified),
                # FR-4: the span of the very set the limbs above certified.
                # `certified` is non-empty here — an empty expected set is
                # refused by the calendar authority and set equality has just
                # held — so `min`/`max` are total.
                certified_slot_min=min(certified),
                certified_slot_max=max(certified),
            )
        )

    # D-5.8 requirement 4: coverage is recognised only after BOTH the
    # set-equality limbs above AND calendar-provenance validation. Placed here,
    # after the loop, because a provenance check placed before it would answer
    # for the six §8 refusals instead of them (ruling §4.9). The returned digest
    # is the re-derived one, not the string the record carried in: FR-7 records
    # that the unverified value was being copied verbatim into
    # `ProofResult.calendar_digest`, leaving §12.12's "consumer re-verifies
    # before use" with nothing to re-verify on the calendar limb.
    # The pinned sets are handed over rather than letting the digest re-read the
    # calendar: two independent reads of one source let a two-faced slot source
    # be certified against one content and digested against another (B-3).
    bound_digest = assert_calendar_provenance(calendar, pinned_slots=pinned_by_pair)

    return CoverageResult(
        calendar_digest=bound_digest,
        calendar_epoch=str.__str__(calendar.target_epoch),
        per_pair=tuple(per_pair),
        _construction_token=_CoverageConstructionToken(_RESULT_PURPOSE),
    )


__all__ = [
    "BAR_COMPLETE_ALIAS_KEY",
    "BAR_COMPLETE_KEY",
    "BAR_SLOT_KEY",
    "BAR_SOURCE_MINUTE_KEY",
    "MINUTE_ACCOUNTING_FIELDS",
    "BarNotCertifiableError",
    "CoverageConstructionError",
    "CoverageError",
    "CoverageEvidenceError",
    "CoverageMeasurementMissingError",
    "CoverageResult",
    "CoverageSetMismatchError",
    "MinuteAccountingError",
    "PairCoverage",
    "PairSlotMeasurement",
    "RejectedSlotCountedCoveredError",
    "assert_full_coverage",
    "measure_pair_coverage",
]
