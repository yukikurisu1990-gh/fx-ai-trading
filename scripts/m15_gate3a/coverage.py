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

What this module does **not** enforce
-------------------------------------
D-5.8 ("a single instant, or a sparse handful of points, **never** produces a
proof token") is enforced here only against the *derivation*: a truncated
derivation cannot equal a full calendar's slot set. It is **not** enforced
against a calendar that itself declares one slot per pair. Any count floor is a
number nobody pinned, and D-6 forbids this module to decide how many M15 buckets
an epoch contains — that is a market-hours question owned by the calendar
artifact. Raising the floor therefore **requires a separate contract
Gate-decision**; the ruled control meanwhile is
``PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED``, the human + ChatGPT
approval of the concrete artifact. What *is* enforced is the arithmetic relation
between the calendar's slot count and the declared source-minute count, so the
two cannot describe different epochs.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

from scripts.m15_gate3a.calendar_authority import SLOT_MINUTES, ValidatedCalendar
from scripts.m15_gate3a.no_overlap import DESIGN_END, DESIGN_START, is_dead_window_instant
from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair
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
    """

    __slots__ = ("purpose", "spent")

    def __init__(self, purpose: str) -> None:
        self.purpose = purpose
        self.spent = False


_MEASUREMENT_PURPOSE: Final[str] = "PairSlotMeasurement"
_RESULT_PURPOSE: Final[str] = "CoverageResult"


@dataclass(frozen=True, slots=True)
class PairSlotMeasurement:
    """What was actually measured for one pair. Built only by :func:`measure_pair_coverage`.

    Carrying the slot **set** rather than a count is the point: D-5.9 rules that
    ``n_pairs == 20`` alone is not coverage proof, and a count of certified bars
    is the same kind of non-evidence one level down.
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


@dataclass(frozen=True, slots=True)
class PairCoverage:
    """The set-equality verdict for one pair, for the proof record.

    There is no ``satisfied`` flag here. R-1 deletes a field that can only ever
    hold one value, and once :func:`assert_full_coverage` raises on every
    inequality the flag could only ever have been ``True`` — the audit's
    ``aggregate_assertions`` defect, one level down. The two counts are what was
    actually measured, and they vary with the evidence.
    """

    pair: str
    expected_slot_count: int
    certified_slot_count: int


@dataclass(frozen=True, slots=True)
class CoverageResult:
    """Coverage over the whole roster: the conjunction across 20 measured pairs.

    Only ever returned when every pair satisfied set equality — insufficient
    coverage raises (D-10), so this object never describes a failure. Its
    *existence* is therefore the conjunction (D-8 / NR-C); it carries no
    ``satisfied`` flag, for the R-1 reason recorded on :class:`PairCoverage`.
    """

    calendar_digest: str
    calendar_epoch: str
    per_pair: tuple[PairCoverage, ...]
    pairs_measured: tuple[str, ...]
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
    """The six D-3 quantities, present, integral, non-negative, and self-consistent."""
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
        if value < 0:
            raise MinuteAccountingError(f"{pair}: minute_accounting[{key!r}] is negative ({value})")
        values[key] = value
    expected = values["expected_source_minute_count"]
    total = (
        values["usable_source_minute_count"]
        + values["absent_source_minute_count"]
        + values["rejected_source_minute_count"]
    )
    if expected != total:
        raise MinuteAccountingError(
            f"{pair}: minute accounting identity violated — expected {expected} != "
            f"usable+absent+rejected {total}"
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
        if item.pair in by_pair:
            raise CoverageEvidenceError(
                f"{item.pair} is measured twice in the coverage roster; after "
                "canonicalisation each pair is measured exactly once"
            )
        by_pair[item.pair] = item
    unknown = sorted(set(by_pair) - set(PAIRS_20))
    if unknown:  # pragma: no cover - canonical_pair already bounds the universe
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
    """
    if not isinstance(calendar, ValidatedCalendar):
        raise CoverageEvidenceError(
            f"coverage requires a validated calendar authority, got {type(calendar).__name__}; "
            "an unvalidated calendar is not the coverage authority"
        )
    if calendar.target_epoch != expected_epoch:
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
    for pair in PAIRS_20:
        measurement = by_pair[pair]
        expected = calendar.expected_slots(pair)
        certified = measurement.certified_slots

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

        per_pair.append(
            PairCoverage(
                pair=pair,
                expected_slot_count=len(expected),
                certified_slot_count=len(certified),
            )
        )

    return CoverageResult(
        calendar_digest=calendar.content_digest,
        calendar_epoch=calendar.target_epoch,
        per_pair=tuple(per_pair),
        pairs_measured=tuple(PAIRS_20),
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
