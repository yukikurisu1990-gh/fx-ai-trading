"""D-5.8 provenance, the digest binding, and the coverage/calendar hardening.

Workstream B of the fifth targeted-fix Work PR. Everything here is synthetic: no
file is opened, no real datum is read, no market hour is decided and no calendar
artifact is authored. The fixture's calendar is a placeholder naming a file that
does not exist.

**No numeric slot-count threshold appears in this module, and none may be added.**
D-5.8 is ruled
``D5_8_RULED_NO_NUMERIC_FLOOR_TRUSTED_CALENDAR_PROVENANCE_AND_SET_EQUALITY_REQUIRED``:
requirement 6 establishes no minimum count and requirement 7 forbids introducing
any value for the purpose — the two the ruling names by way of foreclosure, or
any other. The two tests at the end of the D-5.8 section assert the *absence* of
a floor directly, so a later edit that quietly adds one fails here.

House rules, as elsewhere in this suite: no regex alternation in
``pytest.raises(match=...)`` — every pattern identifies exactly one ``raise``
site; a negative control beside every refusal, so the test discriminates rather
than refusing everything; no assertions on source text; no ``# pragma: no cover``
on reachable code.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Set
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from scripts.m15_gate3a import calendar_authority, sealing
from scripts.m15_gate3a.calendar_authority import (
    REQUIRED_CALENDAR_FIELDS,
    REQUIRED_PROVENANCE_FIELDS,
    CalendarConstructionError,
    CalendarDigestMismatchError,
    CalendarMalformedError,
    CalendarProvenanceError,
    ValidatedCalendar,
    calendar_content_digest,
    validate_calendar,
)
from scripts.m15_gate3a.coverage import (
    BarNotCertifiableError,
    CoverageConstructionError,
    CoverageEvidenceError,
    CoverageResult,
    CoverageSetMismatchError,
    MinuteAccountingError,
    PairCoverage,
    PairSlotMeasurement,
    assert_full_coverage,
    measure_pair_coverage,
)
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_gate3a.timeutil import to_utc
from tests.m15_gate3a.test_wp_proof_coverage_calendar import (
    _OMIT,
    EPOCH,
    MINUTES_PER_SLOT,
    PROVENANCE,
    SLOTS,
    accounting,
    bar,
    bars,
    calendar_artifact,
    full_measurements,
    pair_measurement,
    valid_calendar,
)

#: One slot per pair. Used to show that a *small* expected set is still accepted
#: — D-5.8 adopts no count floor — and never to argue that small is adequate.
ONE_SLOT = SLOTS[:1]


def one_slot_calendar() -> ValidatedCalendar:
    return valid_calendar(expected_m15_slots={pair: list(ONE_SLOT) for pair in PAIRS_20})


def one_slot_measurements() -> list[PairSlotMeasurement]:
    return [
        pair_measurement(pair, slots=ONE_SLOT, minute_accounting=accounting(slots=1))
        for pair in PAIRS_20
    ]


class LyingLen(frozenset):
    """A ``frozenset`` honest about its members and lying about its cardinality.

    The exact shape of the ruling's second D-5.8 probe (§4.2), which returned a
    ``CoverageResult`` reading ``expected_slot_count=21000`` beside
    ``certified_slot_count=1``.
    """

    def __len__(self) -> int:
        return 21_000


class LyingSub(frozenset):
    """A ``frozenset`` that answers "nothing is missing" to every difference."""

    def __sub__(self, other: Any) -> frozenset:
        return frozenset()

    def __rsub__(self, other: Any) -> frozenset:
        return frozenset()


class RepeatingSet(Set):
    """A ``Set`` whose two declared members are one instant seen twice."""

    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def __contains__(self, item: object) -> bool:
        return item == self._instant

    def __iter__(self):
        yield self._instant
        yield self._instant

    def __len__(self) -> int:
        return 2


class ClassSpoofingInt:
    """``isinstance(x, int)`` is True; ``int.__index__`` then refuses.

    This is why ``# pragma: no cover - guarded above`` was wrong at
    ``coverage.py``'s two numeric-authority sites (FR-20): ``isinstance``
    consults ``__class__``, which any object may claim.
    """

    @property
    def __class__(self) -> type:  # type: ignore[override]
        return int


class TwoFacedEpoch(str):
    """Character data says one epoch; ``__eq__`` says it matches everything."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    def __hash__(self) -> int:
        return hash(str.__str__(self))


# ===========================================================================
# D-5.8 requirement 1-3 — committed provenance, and the rule route
# ===========================================================================


def test_d58_a_deterministic_rule_closing_over_the_derivation_is_refused() -> None:
    """The ruling's headline case (§4.2), pinned directly.

    The rule is perfectly deterministic — it answers identically every time — and
    that is the point: determinism was the only property the previous
    implementation tested, and a closure over the derivation has it. Because the
    expectation then tracks the observation, a bucket lost to a crossed quote
    leaves the expected set as it leaves the certified set, so D-1, D-2 and D-3
    are disarmed together.
    """
    derivation = {pair: list(ONE_SLOT) for pair in PAIRS_20}

    def rule_closing_over_the_derivation(pair: str) -> list[str]:
        return list(derivation[pair])

    assert rule_closing_over_the_derivation("EUR_USD") == rule_closing_over_the_derivation(
        "EUR_USD"
    )
    artifact = calendar_artifact(
        expected_m15_slots=_OMIT, expected_m15_slot_rule=rule_closing_over_the_derivation
    )
    with pytest.raises(CalendarProvenanceError, match="no commit can carry it"):
        validate_calendar(artifact, expected_epoch=EPOCH)


def test_d58_the_rule_route_is_refused_for_any_callable_not_only_a_closure() -> None:
    """Class-level, not payload-level: the invariant is "a commit cannot carry it"."""

    class CallableRule:
        def __call__(self, pair: str) -> list[str]:
            return list(SLOTS)

    artifact = calendar_artifact(expected_m15_slots=_OMIT, expected_m15_slot_rule=CallableRule())
    with pytest.raises(CalendarProvenanceError, match="no commit can carry it"):
        validate_calendar(artifact, expected_epoch=EPOCH)


def test_d58_a_non_callable_rule_field_is_refused_on_the_same_ground() -> None:
    """A rule field is refused for having no provenance, not for failing to run."""
    artifact = calendar_artifact(
        expected_m15_slots=_OMIT, expected_m15_slot_rule="generate the usual weekdays"
    )
    with pytest.raises(CalendarProvenanceError, match="no commit can carry it"):
        validate_calendar(artifact, expected_epoch=EPOCH)


def test_d58_a_calendar_without_committed_provenance_is_refused() -> None:
    with pytest.raises(CalendarProvenanceError, match="carries no 'provenance' block"):
        validate_calendar(calendar_artifact(provenance=_OMIT), expected_epoch=EPOCH)


@pytest.mark.parametrize("field", REQUIRED_PROVENANCE_FIELDS)
def test_d58_provenance_missing_a_required_field_is_refused(field: str) -> None:
    block = dict(PROVENANCE)
    del block[field]
    with pytest.raises(CalendarProvenanceError, match="committed provenance names"):
        validate_calendar(calendar_artifact(provenance=block), expected_epoch=EPOCH)


def test_d58_a_provenance_block_that_is_not_a_mapping_is_refused() -> None:
    with pytest.raises(CalendarProvenanceError, match="must be a mapping stating where"):
        validate_calendar(
            calendar_artifact(provenance=list(PROVENANCE.items())), expected_epoch=EPOCH
        )


def test_d58_an_unrecognised_provenance_key_is_refused() -> None:
    """A closed schema: an unrecognised key would be provenance no digest covers."""
    block = dict(PROVENANCE, committed_artefact="the-british-spelling")
    with pytest.raises(CalendarProvenanceError, match="provenance schema is closed"):
        validate_calendar(calendar_artifact(provenance=block), expected_epoch=EPOCH)


@pytest.mark.parametrize("field", REQUIRED_PROVENANCE_FIELDS)
def test_d58_a_non_string_provenance_field_is_refused(field: str) -> None:
    block = dict(PROVENANCE, **{field: 12345})
    with pytest.raises(CalendarProvenanceError, match="must be a string, got int"):
        validate_calendar(calendar_artifact(provenance=block), expected_epoch=EPOCH)


@pytest.mark.parametrize("field", REQUIRED_PROVENANCE_FIELDS)
def test_d58_an_empty_provenance_field_is_refused(field: str) -> None:
    block = dict(PROVENANCE, **{field: "   "})
    with pytest.raises(CalendarProvenanceError, match="states no provenance for its expected"):
        validate_calendar(calendar_artifact(provenance=block), expected_epoch=EPOCH)


@pytest.mark.parametrize("field", REQUIRED_PROVENANCE_FIELDS)
def test_d58_a_provenance_field_that_is_prose_is_refused(field: str) -> None:
    block = dict(PROVENANCE, **{field: "wherever it came from originally"})
    with pytest.raises(CalendarProvenanceError, match="single tokens, never prose"):
        validate_calendar(calendar_artifact(provenance=block), expected_epoch=EPOCH)


def test_d58_an_unrecognised_top_level_field_is_refused() -> None:
    """§4.8's O4 row: the open vocabulary silently ignored a misspelt field."""
    with pytest.raises(CalendarMalformedError, match="artifact vocabulary is closed"):
        validate_calendar(
            calendar_artifact(expected_m15_slotss={pair: list(SLOTS) for pair in PAIRS_20}),
            expected_epoch=EPOCH,
        )


def test_d58_a_well_formed_calendar_with_committed_provenance_is_accepted() -> None:
    """Negative control: the provenance mechanism discriminates."""
    calendar = valid_calendar()
    assert calendar.committed_artifact == PROVENANCE["committed_artifact"]
    assert calendar.committed_revision == PROVENANCE["committed_revision"]
    assert calendar.expected_slots("EUR_USD") == frozenset(to_utc(s) for s in SLOTS)


def test_d58_the_record_carries_no_one_valued_slot_source_field() -> None:
    """R-1: with the rule route refused, ``slot_source_field`` could hold one value."""
    assert not hasattr(valid_calendar(), "slot_source_field")


# ---------------------------------------------------------------------------
# Requirements 5-7 — no count floor, and counts are never authenticity proof
# ---------------------------------------------------------------------------


def test_d58_no_slot_count_floor_governs_coverage() -> None:
    """Requirement 6: no minimum count is established, so a small set still passes.

    This is deliberately the *permissive* direction. D-5.8 was discharged by
    provenance and set equality, not by a threshold, and a later edit that adds
    one — at any value — fails here.
    """
    result = assert_full_coverage(
        one_slot_measurements(), one_slot_calendar(), expected_epoch=EPOCH
    )
    assert isinstance(result, CoverageResult)
    assert all(entry.expected_slot_count == len(ONE_SLOT) for entry in result.per_pair)


def test_d58_two_calendars_of_different_size_are_treated_identically() -> None:
    """The criterion is not count-shaped: cardinality changes nothing about admission."""
    small = assert_full_coverage(one_slot_measurements(), one_slot_calendar(), expected_epoch=EPOCH)
    larger = assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH)
    assert {entry.expected_slot_count for entry in small.per_pair} == {len(ONE_SLOT)}
    assert {entry.expected_slot_count for entry in larger.per_pair} == {len(SLOTS)}


def test_d58_a_large_expected_set_is_no_substitute_for_provenance() -> None:
    """Requirement 5: a count is never proof of calendar authenticity.

    A full day of buckets, reaching further than any fixture elsewhere in this
    suite, and it changes nothing — the provenance limb still refuses.
    """
    start = datetime(2025, 5, 1, tzinfo=UTC)
    day = [
        (start + timedelta(minutes=MINUTES_PER_SLOT * i)).isoformat()
        for i in range(24 * 60 // MINUTES_PER_SLOT)
    ]
    artifact = calendar_artifact(
        provenance=_OMIT, expected_m15_slots={pair: list(day) for pair in PAIRS_20}
    )
    with pytest.raises(CalendarProvenanceError, match="carries no 'provenance' block"):
        validate_calendar(artifact, expected_epoch=EPOCH)


# ===========================================================================
# FR-7 — the content digest binds to the content
# ===========================================================================


def test_fr7_two_structurally_different_calendars_cannot_carry_one_digest() -> None:
    """Before: two calendars differing in their slot sets carried the same string."""
    three = valid_calendar()
    one = one_slot_calendar()
    assert three.content_digest != one.content_digest
    assert len(three.expected_slots("EUR_USD")) != len(one.expected_slots("EUR_USD"))


def test_fr7_a_declared_digest_that_does_not_name_its_content_is_refused() -> None:
    with pytest.raises(CalendarDigestMismatchError, match="binds nothing"):
        validate_calendar(
            calendar_artifact(content_digest="not-the-digest-of-anything-here"),
            expected_epoch=EPOCH,
        )


@pytest.mark.parametrize(
    "field",
    (
        "authority",
        "authority_version",
        "timezone",
        "market_open_close_rule",
        "dst_rule",
        "exceptional_closure_handling",
    ),
)
def test_fr7_every_digested_field_changes_the_digest(field: str) -> None:
    """The binding is over the whole declared content, not only the slot set."""
    base = valid_calendar()
    altered = valid_calendar(**{field: "a materially different declaration"})
    assert altered.content_digest != base.content_digest


def test_fr7_the_slot_set_changes_the_digest() -> None:
    base = valid_calendar()
    slots = {pair: list(SLOTS) for pair in PAIRS_20}
    slots["EUR_USD"] = list(SLOTS[:2])
    moved = valid_calendar(expected_m15_slots=slots)
    assert moved.content_digest != base.content_digest


def test_fr7_the_provenance_declaration_changes_the_digest() -> None:
    base = valid_calendar()
    elsewhere = valid_calendar(
        provenance=dict(PROVENANCE, committed_revision="1" * 40),
    )
    assert elsewhere.content_digest != base.content_digest


def test_fr7_the_digest_is_reproducible_from_the_declared_content_alone() -> None:
    calendar = valid_calendar()
    assert calendar_authority.recompute_content_digest(calendar) == calendar.content_digest
    assert (
        calendar_content_digest(
            authority=calendar.authority,
            authority_version=calendar.authority_version,
            timezone=calendar.timezone,
            market_open_close_rule=calendar.market_open_close_rule,
            dst_rule=calendar.dst_rule,
            exceptional_closure_handling=calendar.exceptional_closure_handling,
            target_epoch=calendar.target_epoch,
            committed_artifact=calendar.committed_artifact,
            committed_revision=calendar.committed_revision,
            slots_by_pair={pair: calendar.expected_slots(pair) for pair in PAIRS_20},
        )
        == calendar.content_digest
    )


def test_fr7_the_coverage_result_publishes_the_re_derived_digest() -> None:
    """The value handed downstream is re-derived, not the string that arrived."""
    calendar = valid_calendar()
    result = assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)
    assert result.calendar_digest == calendar_authority.recompute_content_digest(calendar)


def test_fr7_a_calendar_missing_a_pair_has_no_computable_digest() -> None:
    with pytest.raises(CalendarMalformedError, match="over all twenty pairs or over none"):
        calendar_content_digest(
            authority="a",
            authority_version="b",
            timezone="UTC",
            market_open_close_rule="c",
            dst_rule="d",
            exceptional_closure_handling="e",
            target_epoch=EPOCH,
            committed_artifact="f",
            committed_revision="g",
            slots_by_pair={pair: frozenset() for pair in PAIRS_20[:-1]},
        )


def test_fr7_a_slot_set_that_is_not_a_set_has_no_computable_digest() -> None:
    with pytest.raises(CalendarMalformedError, match="cannot be taken over an object"):
        calendar_content_digest(
            authority="a",
            authority_version="b",
            timezone="UTC",
            market_open_close_rule="c",
            dst_rule="d",
            exceptional_closure_handling="e",
            target_epoch=EPOCH,
            committed_artifact="f",
            committed_revision="g",
            slots_by_pair={pair: list(SLOTS) for pair in PAIRS_20},
        )


# ===========================================================================
# Requirement 4 — provenance is validated at coverage, AFTER the limbs
# ===========================================================================


def test_req4_a_calendar_rewritten_after_validation_is_refused_at_coverage() -> None:
    """Set equality still holds; the provenance limb is what refuses.

    ``object.__setattr__`` on a genuinely validated record is the one route no
    construction token can close, and it is exactly how the audit produced
    ``authority="THE OBSERVED DATA ITSELF"``. The digest re-derivation at the
    consumer catches it because the digest covers the whole declared content.
    """
    calendar = valid_calendar()
    object.__setattr__(calendar, "authority", "THE OBSERVED DATA ITSELF")
    with pytest.raises(CalendarDigestMismatchError, match="not the content the committed"):
        assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)


def test_req4_a_blanked_provenance_field_is_refused_at_coverage() -> None:
    calendar = valid_calendar()
    object.__setattr__(calendar, "committed_artifact", "   ")
    with pytest.raises(CalendarProvenanceError, match="no longer states anything"):
        assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)


def test_req4_a_non_string_content_digest_is_refused_at_coverage() -> None:
    calendar = valid_calendar()
    object.__setattr__(calendar, "content_digest", 1234)
    with pytest.raises(CalendarProvenanceError, match="not a digest; the"):
        assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)


def test_req4_provenance_is_checked_after_the_set_equality_limbs() -> None:
    """Ruling §4.9's ordering: the six §8 refusals keep their own guard identity.

    The calendar here is *both* provenance-broken and short of a certified slot.
    The set-equality limb is the one that answers, so a test naming that limb
    still identifies it.
    """
    calendar = valid_calendar()
    object.__setattr__(calendar, "authority", "THE OBSERVED DATA ITSELF")
    measurements = full_measurements()
    measurements[3] = pair_measurement(PAIRS_20[3], slots=SLOTS[:-1])
    with pytest.raises(CoverageSetMismatchError, match="must contain every expected slot"):
        assert_full_coverage(measurements, calendar, expected_epoch=EPOCH)


def test_req4_an_untampered_calendar_reaches_the_conjunction() -> None:
    """Negative control for the whole requirement-4 block."""
    result = assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH)
    assert tuple(entry.pair for entry in result.per_pair) == PAIRS_20


# ===========================================================================
# FB-1 / FR-3 — sealed records, and the consumer boundaries that check them
# ===========================================================================


def test_fb1_a_validated_calendar_may_not_be_subclassed() -> None:
    with pytest.raises(CalendarConstructionError, match="ValidatedCalendar may not be subclassed"):

        class ForgedCalendar(ValidatedCalendar):
            def __post_init__(self) -> None:
                pass


def test_fb1_a_pair_slot_measurement_may_not_be_subclassed() -> None:
    with pytest.raises(
        CoverageConstructionError, match="PairSlotMeasurement may not be subclassed"
    ):

        class ForgedMeasurement(PairSlotMeasurement):
            def __post_init__(self) -> None:
                pass


def test_fb1_a_coverage_result_may_not_be_subclassed() -> None:
    with pytest.raises(CoverageConstructionError, match="CoverageResult may not be subclassed"):

        class ForgedResult(CoverageResult):
            def __post_init__(self) -> None:
                pass


def test_fb1_a_pair_coverage_may_not_be_subclassed() -> None:
    with pytest.raises(CoverageConstructionError, match="PairCoverage may not be subclassed"):

        class ForgedEntry(PairCoverage):
            pass


def forged_calendar() -> ValidatedCalendar:
    """A ``ValidatedCalendar`` built by ``object.__new__``: no validation ever ran."""
    genuine = valid_calendar()
    forged = object.__new__(ValidatedCalendar)
    for name in (
        "authority_version",
        "timezone",
        "market_open_close_rule",
        "dst_rule",
        "exceptional_closure_handling",
        "target_epoch",
        "approval_basis",
        "committed_artifact",
        "committed_revision",
    ):
        object.__setattr__(forged, name, getattr(genuine, name))
    object.__setattr__(forged, "authority", "THE OBSERVED DATA ITSELF")
    object.__setattr__(forged, "content_digest", "NO_CALENDAR_EVER_EXISTED")
    object.__setattr__(forged, "_slots", {pair: genuine.expected_slots(pair) for pair in PAIRS_20})
    object.__setattr__(forged, "_construction_token", None)
    return forged


def test_fb1_a_forged_calendar_is_refused_at_the_coverage_boundary() -> None:
    """``object.__new__`` skips ``__post_init__``, so the forgery is never registered."""
    forged = forged_calendar()
    assert isinstance(forged, ValidatedCalendar)
    assert not sealing.is_minted(forged)
    with pytest.raises(
        CalendarConstructionError, match="calendar authority offered to coverage was not produced"
    ):
        assert_full_coverage(full_measurements(), forged, expected_epoch=EPOCH)


def test_fb1_a_forged_calendar_is_refused_before_its_slot_sets_are_read() -> None:
    """Placement, not merely refusal: the forgery never reaches the set algebra.

    Without the boundary check the same forgery is still refused — but only after
    the per-pair loop has read its expected sets, so a forged calendar whose slots
    disagree with the measurements answers as a *set mismatch* instead. This test
    supplies exactly that pairing, so it fails if the boundary check moves or goes.
    """
    forged = forged_calendar()
    object.__setattr__(forged, "_slots", {pair: frozenset({to_utc(SLOTS[0])}) for pair in PAIRS_20})
    with pytest.raises(
        CalendarConstructionError, match="calendar authority offered to coverage was not produced"
    ):
        assert_full_coverage(full_measurements(), forged, expected_epoch=EPOCH)


def test_fb1_a_forged_calendar_is_refused_by_the_provenance_check_directly() -> None:
    with pytest.raises(
        CalendarConstructionError, match="calendar authority offered to coverage was not produced"
    ):
        calendar_authority.assert_calendar_provenance(forged_calendar())


def test_fb1_a_forged_measurement_is_refused_at_the_roster() -> None:
    genuine = full_measurements()
    forged = object.__new__(PairSlotMeasurement)
    for name in ("pair", "certified_slots", "duplicate_slots", "rejected_slots"):
        object.__setattr__(forged, name, getattr(genuine[0], name))
    object.__setattr__(forged, "minute_accounting", dict(genuine[0].minute_accounting))
    object.__setattr__(forged, "_construction_token", None)
    assert not sealing.is_minted(forged)
    with pytest.raises(CoverageConstructionError, match="coverage measurement 0 was not produced"):
        assert_full_coverage([forged, *genuine[1:]], valid_calendar(), expected_epoch=EPOCH)


def test_fb1_genuine_records_are_registered_as_minted() -> None:
    """Negative control: the registry admits what the package actually minted."""
    calendar = valid_calendar()
    measurement = pair_measurement("EUR_USD")
    result = assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH)
    assert sealing.is_minted(calendar)
    assert sealing.is_minted(measurement)
    assert sealing.is_minted(result)
    assert all(sealing.is_minted(entry) for entry in result.per_pair)


def test_fb1_a_deep_copied_calendar_is_still_refused() -> None:
    """Round 3's route, re-pinned beside round 4's."""
    with pytest.raises(CalendarConstructionError, match="may not be copied"):
        copy.deepcopy(valid_calendar())


def test_fb1_a_deep_copied_measurement_is_still_refused() -> None:
    with pytest.raises(CoverageConstructionError, match="may not be copied"):
        copy.deepcopy(pair_measurement("EUR_USD"))


# ===========================================================================
# FB-5 — the epoch bind is decided on character data, not by the caller's object
# ===========================================================================


def test_fb5_a_two_faced_epoch_string_is_refused_exactly_as_the_plain_one_is() -> None:
    """A ``str`` subclass was accepted here where the identical plain value raised."""
    two_faced = TwoFacedEpoch("A_COMPLETELY_DIFFERENT_EPOCH")
    assert two_faced == EPOCH  # the object insists it matches
    with pytest.raises(CoverageEvidenceError, match="but coverage is being"):
        assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=two_faced)


def test_fb5_the_plain_control_is_refused_with_the_same_guard() -> None:
    with pytest.raises(CoverageEvidenceError, match="but coverage is being"):
        assert_full_coverage(
            full_measurements(), valid_calendar(), expected_epoch="A_COMPLETELY_DIFFERENT_EPOCH"
        )


def test_fb5_a_str_subclass_whose_character_data_matches_still_certifies() -> None:
    """Negative control: the pin refuses the lie, not the subclass.

    ``TwoFacedEpoch`` here carries the *right* characters, so reading it as plain
    character data admits it — the guard discriminates on content, not on type.
    """
    honest_data = TwoFacedEpoch(EPOCH)
    result = assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=honest_data)
    assert result.calendar_epoch == EPOCH
    assert type(result.calendar_epoch) is str


def test_fb5_a_non_string_expected_epoch_is_refused() -> None:
    with pytest.raises(CoverageEvidenceError, match="must be a string naming the epoch"):
        assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=object())


def test_fb5_a_calendar_whose_target_epoch_is_not_a_string_is_refused() -> None:
    calendar = valid_calendar()
    object.__setattr__(calendar, "target_epoch", 2026)
    with pytest.raises(CoverageEvidenceError, match="an epoch that is not character data"):
        assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)


# ===========================================================================
# FR-9 — all six D-3 quantities stand in a checked relation
# ===========================================================================


def test_fr9_observed_below_usable_plus_rejected_is_refused() -> None:
    with pytest.raises(MinuteAccountingError, match="can never be the smaller"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=bars(SLOTS),
            minute_accounting=accounting(observed_source_minute_count=0),
            rejected_slots=[],
        )


def test_fr9_observed_short_by_one_is_refused() -> None:
    """The exact boundary, so a ``<`` mutated to ``<=`` or shifted by one dies."""
    book = accounting(rejected=1, max_gap=1)
    book["observed_source_minute_count"] = (
        book["usable_source_minute_count"] + book["rejected_source_minute_count"] - 1
    )
    with pytest.raises(MinuteAccountingError, match="can never be the smaller"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=bars(SLOTS),
            minute_accounting=book,
            rejected_slots=[],
        )


def test_fr9_observed_exactly_equal_to_usable_plus_rejected_is_accepted() -> None:
    """Negative control at the boundary: the relation is ``>=``, not ``>``."""
    book = accounting()
    assert book["observed_source_minute_count"] == (
        book["usable_source_minute_count"] + book["rejected_source_minute_count"]
    )
    measurement = measure_pair_coverage(
        pair="EUR_USD",
        certified_bars=bars(SLOTS),
        minute_accounting=book,
        rejected_slots=[],
    )
    assert measurement.certified_slots == frozenset(to_utc(s) for s in SLOTS)


def test_fr9_a_gap_longer_than_the_unavailable_minutes_is_refused() -> None:
    with pytest.raises(MinuteAccountingError, match="cannot be longer than the set"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=bars(SLOTS),
            minute_accounting=accounting(max_unavailable_gap_minutes=1),
            rejected_slots=[],
        )


def test_fr9_a_gap_longer_by_one_than_the_unavailable_minutes_is_refused() -> None:
    """The exact boundary, from the other side."""
    book = accounting(absent=1, rejected=1)
    book["max_unavailable_gap_minutes"] = (
        book["absent_source_minute_count"] + book["rejected_source_minute_count"] + 1
    )
    with pytest.raises(MinuteAccountingError, match="cannot be longer than the set"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=bars(SLOTS),
            minute_accounting=book,
            rejected_slots=[],
        )


def test_fr9_a_gap_exactly_as_long_as_the_unavailable_minutes_is_accepted() -> None:
    """Negative control at the boundary: the relation is ``<=``, not ``<``."""
    book = accounting(absent=1, rejected=1, max_gap=2)
    measurement = measure_pair_coverage(
        pair="EUR_USD",
        certified_bars=bars(SLOTS),
        minute_accounting=book,
        rejected_slots=[],
    )
    assert measurement.minute_accounting["max_unavailable_gap_minutes"] == 2


# ===========================================================================
# FR-20 — the two `pragma: no cover` sites were reachable, and are now pinned
# ===========================================================================


def test_fr20_a_class_spoofing_accounting_value_reaches_the_numeric_authority() -> None:
    spoofed = ClassSpoofingInt()
    assert isinstance(spoofed, int)  # the pragma's premise, refuted
    with pytest.raises(
        MinuteAccountingError,
        match=re.escape("minute_accounting['max_unavailable_gap_minutes'] claims to be an int"),
    ):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=bars(SLOTS),
            minute_accounting=accounting(max_unavailable_gap_minutes=spoofed),
            rejected_slots=[],
        )


def test_fr20_a_class_spoofing_bar_count_reaches_the_numeric_authority() -> None:
    with pytest.raises(BarNotCertifiableError, match="'n_source_bars' claims to be an int"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=[bar(SLOTS[0], n_source_bars=ClassSpoofingInt())],
            minute_accounting=accounting(slots=1),
            rejected_slots=[],
        )


def test_fr20_a_plain_int_control_passes_both_sites() -> None:
    """Negative control: the branch refuses the spoof, not every integer."""
    measurement = measure_pair_coverage(
        pair="EUR_USD",
        certified_bars=[bar(SLOTS[0], n_source_bars=MINUTES_PER_SLOT)],
        minute_accounting=accounting(slots=1),
        rejected_slots=[],
    )
    assert measurement.minute_accounting["max_unavailable_gap_minutes"] == 0


# ===========================================================================
# FR-21 — the mutation survivors in coverage.py and calendar_authority.py
# ===========================================================================


def test_fr21_an_absent_source_minute_beside_complete_coverage_is_refused() -> None:
    """The ``absent`` limb of the ``unusable`` check; the ``rejected`` mirror was pinned."""
    measurements = full_measurements()
    measurements[2] = pair_measurement(
        PAIRS_20[2], minute_accounting=accounting(absent=1, max_gap=1)
    )
    with pytest.raises(CoverageSetMismatchError, match="expected-but-unusable source"):
        assert_full_coverage(measurements, valid_calendar(), expected_epoch=EPOCH)


def test_fr21_neither_absent_nor_rejected_minutes_reaches_the_conjunction() -> None:
    """Negative control for both limbs together."""
    result = assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH)
    assert len(result.per_pair) == len(PAIRS_20)


@pytest.mark.parametrize("flag", (1, 0, "yes", "True", 1.0))
def test_fr21_complete_bucket_must_be_a_measured_boolean(flag: Any) -> None:
    with pytest.raises(BarNotCertifiableError, match="not a measured boolean"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=[bar(SLOTS[0], complete_bucket=flag, eligible=flag)],
            minute_accounting=accounting(slots=1),
            rejected_slots=[],
        )


def test_fr21_a_measured_boolean_true_is_accepted() -> None:
    """Negative control: the check refuses the non-bool, not the flag."""
    measurement = measure_pair_coverage(
        pair="EUR_USD",
        certified_bars=[bar(SLOTS[0], complete_bucket=True, eligible=True)],
        minute_accounting=accounting(slots=1),
        rejected_slots=[],
    )
    assert len(measurement.certified_slots) == 1


@pytest.mark.parametrize("field", REQUIRED_CALENDAR_FIELDS)
def test_fr21_a_non_string_calendar_field_raises_the_modules_own_error(field: str) -> None:
    """RF-29 class: a non-string must not surface as a bare ``TypeError``."""
    with pytest.raises(CalendarMalformedError, match="must be a string, got int"):
        validate_calendar(calendar_artifact(**{field: 12345}), expected_epoch=EPOCH)


def test_fr21_a_bar_without_a_ts_key_raises_the_modules_own_error() -> None:
    """RF-29 class: a missing key must not surface as a bare ``KeyError``."""
    with pytest.raises(CoverageEvidenceError, match="declares no 'ts' bucket start"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=[bar(SLOTS[0], ts=_OMIT)],
            minute_accounting=accounting(slots=1),
            rejected_slots=[],
        )


def test_fr21_a_bar_with_a_ts_key_is_accepted() -> None:
    """Negative control for the missing-key guard."""
    measurement = measure_pair_coverage(
        pair="EUR_USD",
        certified_bars=[bar(SLOTS[0])],
        minute_accounting=accounting(slots=1),
        rejected_slots=[],
    )
    assert measurement.certified_slots == frozenset({to_utc(SLOTS[0])})


# ===========================================================================
# Ruling §4.9 — the published counts are measured, not stated by the object
# ===========================================================================


def test_a_lying_len_on_the_expected_slot_set_is_refused() -> None:
    """The ruling's second probe returned ``expected=21000`` beside ``certified=1``."""
    calendar = valid_calendar()
    object.__setattr__(
        calendar,
        "_slots",
        {pair: LyingLen(calendar.expected_slots(pair)) for pair in PAIRS_20},
    )
    with pytest.raises(CoverageEvidenceError, match="a cardinality an object states about itself"):
        assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)


def test_a_lying_len_on_the_certified_slot_set_is_refused() -> None:
    measurements = full_measurements()
    object.__setattr__(
        measurements[0], "certified_slots", LyingLen(measurements[0].certified_slots)
    )
    with pytest.raises(CoverageEvidenceError, match="a cardinality an object states about itself"):
        assert_full_coverage(measurements, valid_calendar(), expected_epoch=EPOCH)


def test_a_lying_difference_cannot_forge_set_equality() -> None:
    """The same family through ``__sub__``: the plain rebuild is what is compared."""
    calendar = valid_calendar()
    object.__setattr__(
        calendar,
        "_slots",
        {pair: LyingSub(frozenset({to_utc(SLOTS[0])})) for pair in PAIRS_20},
    )
    with pytest.raises(CoverageSetMismatchError, match="never absorbed into the expected set"):
        assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)


def test_an_expected_slot_set_that_is_a_sequence_is_refused() -> None:
    calendar = valid_calendar()
    object.__setattr__(calendar, "_slots", {pair: list(SLOTS) for pair in PAIRS_20})
    with pytest.raises(CoverageEvidenceError, match="decided over a materialised set"):
        assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)


def test_two_declared_members_resolving_to_one_instant_are_refused() -> None:
    calendar = valid_calendar()
    object.__setattr__(
        calendar, "_slots", {pair: RepeatingSet(to_utc(SLOTS[0])) for pair in PAIRS_20}
    )
    with pytest.raises(CoverageEvidenceError, match="distinct UTC instant"):
        assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)


def test_the_published_counts_are_the_scanned_cardinalities() -> None:
    """Negative control: honest sets publish honest diagnostics."""
    result = assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH)
    for entry in result.per_pair:
        assert entry.expected_slot_count == len(SLOTS)
        assert entry.certified_slot_count == len(SLOTS)
