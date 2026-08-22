"""Proof-layer regressions for the fourth re-check: FB-1(consumer), FB-5, FB-6,
FR-3, FR-4, FR-11, FR-20 and the FR-21 survivors in ``scripts/m15_gate3a/proof.py``.

Every test here was run against the pre-fix source and observed to fail; the
"failing-before" behaviour is named in each docstring, in the audit's own terms,
so a later reader can tell a regression test from a tautology.

House rules (§13): no ``pytest.raises`` alternation — every ``match`` string
identifies exactly one ``raise`` site; a negative control sits beside each
refusal so the test discriminates rather than refusing everything; no assertion
on source text; no ``# pragma: no cover`` on reachable code; no numeric
slot-count threshold is asserted anywhere (D-5.8 is ruled with **no numeric
floor**).

The record fixtures are imported from ``test_wp_proof_coverage_calendar`` rather
than duplicated: the calendar and coverage artifacts they build are owned by
another workstream and are still moving, and a second copy of them would be a
second thing to keep in step.
"""

from __future__ import annotations

import copy
import dataclasses
from datetime import UTC, datetime
from typing import Any

import pytest

from scripts.m15_gate3a import proof
from scripts.m15_gate3a.coverage import CoverageResult, assert_full_coverage
from scripts.m15_gate3a.no_overlap import DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_gate3a.proof import (
    BYTE_LEVEL_CLAIM_WITHHELD_REASON,
    BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN,
    BYTE_LEVEL_PROOF_PENDING,
    BYTE_LEVEL_PROOF_REFUTED,
    DECLARED_NOT_MEASURED_BY_THIS_LAYER,
    LIMB_EVALUATION_EVIDENCE_BASIS,
    ROLE_PRODUCER,
    ROLE_VERIFIER,
    SUBJECT_DERIVED_M15_ARTIFACT,
    VERIFIER_INDEPENDENCE_LIMIT,
    ConsumerRecheck,
    DeclarationRecord,
    DerivationBinding,
    MeasurementRecord,
    ProofCoMeasurementError,
    ProofConstructionError,
    ProofContractError,
    ProofDisagreementError,
    ProofLimbUnsatisfiedError,
    ProofNotUsableError,
    ProofPromotionError,
    ProofResult,
    Provenance,
    RawSourceRehashForbiddenError,
    assert_byte_level_claim,
    assert_records_agree,
    evaluate_four_limbs,
    is_declaration_only,
    open_for_consumption,
    refuse_raw_source_rehash,
)
from tests.m15_gate3a.test_wp_proof_coverage_calendar import (
    EPOCH,
    SLOTS,
    binding_set,
    digest,
    evaluated_proof,
    full_measurements,
    measurement,
    producer_set,
    published_id,
    recheck,
    recheck_set,
    staged_id,
    valid_calendar,
    verifier_set,
)

# ---------------------------------------------------------------------------
# Hostile fixtures — the three shapes the audit used, named for what they do
# ---------------------------------------------------------------------------


class MaskedText(str):
    """Character data says one thing; every comparison answers as another.

    This is FB-5's shape. The real character data is what a scrubber, a JSON
    writer and a human see; ``==``, ``!=`` and ``in`` are what the guards used.
    """

    def __new__(cls, real: str, mask: str) -> MaskedText:
        obj = super().__new__(cls, real)
        obj._mask = mask  # noqa: SLF001 - the whole point of the fixture
        return obj

    def __eq__(self, other: Any) -> bool:
        return bool(other == self._mask)

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def __hash__(self) -> int:
        return hash(self._mask)


class AgreeableText(str):
    """Real character data, and ``True`` to every equality asked of it."""

    def __eq__(self, other: Any) -> bool:
        return True

    def __ne__(self, other: Any) -> bool:
        return False

    __hash__ = str.__hash__


class DistinctText(str):
    """Identical character data, deliberately distinct under ``==`` and ``hash``.

    Two of these over one real byte stream (``THE-ONE-AND-ONLY-READ``) compare
    unequal and hash apart, which is how one pass was cited as two.
    """

    def __new__(cls, real: str, tag: int) -> DistinctText:
        obj = super().__new__(cls, real)
        obj._tag = tag  # noqa: SLF001 - the whole point of the fixture
        return obj

    def __eq__(self, other: Any) -> bool:
        return self is other

    def __ne__(self, other: Any) -> bool:
        return self is not other

    def __hash__(self) -> int:
        return object.__hash__(self)


class AgreeableCount(int):
    """A count that answers every comparison favourably while holding any value."""

    def __eq__(self, other: Any) -> bool:
        return True

    def __ne__(self, other: Any) -> bool:
        return False

    __hash__ = int.__hash__


class ClaimsToBeStr:
    """``isinstance(x, str)`` is True; the unbound ``str`` slot refuses it."""

    @property
    def __class__(self) -> type:  # type: ignore[override]
        return str


class ClaimsToBeInt:
    """``isinstance(x, int)`` is True; the unbound ``int`` slot refuses it."""

    @property
    def __class__(self) -> type:  # type: ignore[override]
        return int


class AlwaysEqual:
    """Not a ``str`` at all, and equal to everything it is compared with."""

    def __eq__(self, other: Any) -> bool:
        return True

    def __ne__(self, other: Any) -> bool:
        return False

    __hash__ = object.__hash__


def forge(cls: type, **fields: Any) -> Any:
    """Build *cls* by ``object.__new__``, which no ``__new__`` override intercepts."""
    obj = object.__new__(cls)
    for name, value in fields.items():
        object.__setattr__(obj, name, value)
    return obj


def clone_fields(record: Any) -> dict[str, Any]:
    return {f.name: getattr(record, f.name) for f in dataclasses.fields(record)}


def roster_only(**overrides: Any) -> Any:
    """Drive ``evaluate_four_limbs`` as far as the roster, with no coverage fixture.

    The roster and the agreement loop run before any limb, so the CV and DB
    arguments can be ``None`` for every test whose subject is a record.
    """
    kwargs: dict[str, Any] = {
        "producer_records": producer_set(),
        "verifier_records": verifier_set(),
        "coverage_result": None,
        "derivation_bindings": None,
        "inventory_digest": digest(4242),
    }
    kwargs.update(overrides)
    return evaluate_four_limbs(**kwargs)


# ===========================================================================
# FR-3 / FB-1 (consumer side) — object.__new__ skips every construction check
# ===========================================================================


def forged_measurement(pair: str, index: int, *, role: str = ROLE_PRODUCER) -> Any:
    """The audit's forgery, field for field."""
    prov = Provenance(stream_id=f"{role}-read-{pair}", pass_index=1, artifact_id=staged_id(pair))
    return forge(
        MeasurementRecord,
        role=role,
        pair=pair,
        artifact_id=published_id(pair),
        subject="RAW_M1_SOURCE_BYTES",
        sha256=digest(index + 1),
        re_read_sha256=digest(index + 1),
        staged_artifact_id=staged_id(pair),
        size_bytes=-1,
        row_count=-1,
        bars_scanned=-1,
        measured_ts_min=datetime(2025, 5, 1, 0, 30, tzinfo=UTC),
        measured_ts_max=datetime(2025, 5, 1, 0, 0, tzinfo=UTC),
        dead_window_bars_by_bucket_start=7,
        dead_window_bars_by_contributing_minute=7,
        out_of_design_range_bar_count=0,
        digest_provenance=prov,
        size_provenance=prov,
        span_provenance=prov,
        scan_provenance=prov,
    )


def test_fr3_the_twenty_forged_measurement_records_are_refused_by_the_roster() -> None:
    """The audit's headline reproduction, unchanged.

    Failing-before: all twenty were **accepted** by ``_measurement_roster`` —
    ``subject='RAW_M1_SOURCE_BYTES'`` (D-4 defeated), ``size_bytes=-1``, a
    reversed span and seven dead-window bars, with every check in
    ``__post_init__`` having run on nothing at all.
    """
    forgeries = [forged_measurement(pair, i) for i, pair in enumerate(PAIRS_20)]
    with pytest.raises(ProofConstructionError, match="producer record 0 was not produced by"):
        roster_only(producer_records=forgeries)


def test_fr3_a_forgery_of_any_pair_position_is_refused_not_just_the_first() -> None:
    """Class-level, not the literal payload: the check is per record, not per set."""
    records = producer_set()
    records[11] = forged_measurement(PAIRS_20[11], 11)
    with pytest.raises(ProofConstructionError, match="producer record 11 was not produced by"):
        roster_only(producer_records=records)


def test_fr3_a_forgery_equal_to_a_live_genuine_record_is_still_refused() -> None:
    """Authority is identity, never equality.

    Failing-before, and the reason this test exists at all: the package-wide
    registry is a ``WeakSet``, and ``weakref.ref`` hashes and compares by
    *referent equality*, so a forgery whose fields equal those of a live genuine
    record was reported as minted. A forgery is free to carry two-faced field
    objects that compare equal to the permitted constants, so equality is
    exactly the wrong question.
    """
    genuine = measurement("EUR_USD", 0)
    twin = forge(MeasurementRecord, **clone_fields(genuine))
    assert twin == genuine
    with pytest.raises(ProofConstructionError, match="producer record 0 was not produced by"):
        roster_only(producer_records=[twin], verifier_records=[])


def test_fr3_a_genuine_record_still_reaches_the_limbs() -> None:
    """Negative control: the roster refuses forgeries, not records.

    One genuine producer gets past the roster and the agreement loop and is
    stopped by the BI limb for the nineteen pairs it does not carry — which is
    the proof that the roster accepted it.
    """
    genuine = measurement("EUR_USD", 0)
    verifier = measurement("EUR_USD", 0, role=ROLE_VERIFIER)
    with pytest.raises(ProofLimbUnsatisfiedError, match="BI limb: no byte measurement for"):
        roster_only(producer_records=[genuine], verifier_records=[verifier])


def test_fr3_a_forged_derivation_binding_is_refused_by_the_db_limb() -> None:
    """Failing-before: the DB limb type-checked and then trusted the fields."""
    bindings = binding_set()
    real = bindings[3]
    bindings[3] = forge(DerivationBinding, **clone_fields(real))
    with pytest.raises(ProofConstructionError, match="derivation binding 3 was not produced by"):
        evaluated_proof(derivation_bindings=bindings)


def test_fr3_a_forged_consumer_recheck_is_refused_at_consumption() -> None:
    """Failing-before: W3's own evidence could be built without any construction check."""
    result = evaluated_proof()
    rechecks = recheck_set()
    rechecks[2] = forge(ConsumerRecheck, **clone_fields(rechecks[2]))
    with pytest.raises(
        ProofConstructionError, match="consumer re-verification 2 was not produced by"
    ):
        open_for_consumption(result, consumer_rechecks=rechecks)


def test_fr3_a_forged_provenance_cannot_be_built_into_a_measurement() -> None:
    """A pass identity is authority too: it is what the roster de-duplicates on."""
    real = Provenance(stream_id="p-read", pass_index=1, artifact_id=staged_id("EUR_USD"))
    fake = forge(Provenance, **clone_fields(real))
    with pytest.raises(ProofConstructionError, match="digest provenance was not produced by"):
        measurement(
            "EUR_USD",
            0,
            digest_provenance=fake,
            size_provenance=fake,
            span_provenance=fake,
            scan_provenance=fake,
        )


def test_fr3_a_forged_proof_result_is_refused_at_consumption() -> None:
    """A ``ProofResult`` that is *equal* to a real one is still not a real one.

    Failing-before: ``open_for_consumption`` type-checked the result, re-checked
    its disclosure fields — which this forgery copies verbatim from a real
    evaluation, so they all pass — and then consumed it. No limb had ever been
    evaluated for it.
    """
    real = evaluated_proof()
    forged = forge(ProofResult, **clone_fields(real))
    assert forged == real
    with pytest.raises(
        ProofConstructionError, match="the ProofResult offered for consumption was not produced by"
    ):
        open_for_consumption(forged, consumer_rechecks=recheck_set())


def test_fr3_a_forged_identity_entry_is_refused_at_consumption() -> None:
    """The W3 comparison is only worth the record it compares against."""
    real = evaluated_proof()
    honest = dict(real._identity)  # noqa: SLF001 - W3 keeps the map private
    forged_map = {
        pair: forge(proof._ArtifactIdentity, **clone_fields(entry))  # noqa: SLF001
        for pair, entry in honest.items()
    }
    object.__setattr__(real, "_identity", forged_map)
    with pytest.raises(
        ProofConstructionError, match="EUR_USD: the proof's identity entry was not produced by"
    ):
        open_for_consumption(real, consumer_rechecks=recheck_set())


def test_fr3_a_forged_coverage_result_is_refused_by_the_cv_limb() -> None:
    """The CV limb's own evidence is authority-bearing too.

    Failing-before: ``_limb_cv`` type-checked the result and re-derived the
    roster from it, so a ``CoverageResult`` that ``assert_full_coverage`` had
    never returned satisfied both — the roster it published was the roster it
    was judged on.
    """
    real = real_coverage()
    forged = forge(CoverageResult, **clone_fields(real))
    with pytest.raises(
        ProofConstructionError, match="the CV limb's CoverageResult was not produced by"
    ):
        evaluated_proof(coverage_result=forged)


def test_fr3_an_untampered_proof_still_opens() -> None:
    """Negative control for the whole minting family."""
    approval = open_for_consumption(evaluated_proof(), consumer_rechecks=recheck_set())
    assert approval.byte_level_status == BYTE_LEVEL_PROOF_PENDING
    assert set(approval.identity) == set(PAIRS_20)


# ===========================================================================
# FB-5 — five unpinned comparisons, each deciding a contract rule
# ===========================================================================


def test_fb5_provenance_stores_the_plain_character_data_of_its_stream_id() -> None:
    """``pass_index`` went through ``pin_int`` and ``artifact_id`` through the
    identifier check; ``stream_id`` was neither pinned nor stored pinned."""
    prov = Provenance(
        stream_id=DistinctText("THE-ONE-AND-ONLY-READ", 1),
        pass_index=1,
        artifact_id="a-EUR_USD",
    )
    assert type(prov.stream_id) is str
    assert prov.stream_id == "THE-ONE-AND-ONLY-READ"


def test_fb5_two_records_citing_one_byte_stream_pass_are_de_duplicated() -> None:
    """DI-5, through the ``stream_id`` the roster keys on.

    Failing-before: two ``Provenance`` over the one real pass
    ``THE-ONE-AND-ONLY-READ`` compared unequal and hashed apart, so the
    ``(stream_id, pass_index)`` de-dup never fired and one fabricated pass could
    serve every pair.
    """
    first, second = PAIRS_20[0], PAIRS_20[1]
    one = Provenance(
        stream_id=DistinctText("THE-ONE-AND-ONLY-READ", 1),
        pass_index=1,
        artifact_id=staged_id(first),
    )
    two = Provenance(
        stream_id=DistinctText("THE-ONE-AND-ONLY-READ", 2),
        pass_index=1,
        artifact_id=staged_id(second),
    )
    records = [
        measurement(
            first,
            0,
            digest_provenance=one,
            size_provenance=one,
            span_provenance=one,
            scan_provenance=one,
        ),
        measurement(
            second,
            1,
            digest_provenance=two,
            size_provenance=two,
            span_provenance=two,
            scan_provenance=two,
        ),
    ]
    with pytest.raises(
        ProofCoMeasurementError, match="one pass over one byte stream measures one artifact"
    ):
        roster_only(producer_records=records, verifier_records=[])


def test_fb5_two_distinct_passes_are_still_accepted() -> None:
    """Negative control for the de-dup: distinct streams are not refused."""
    with pytest.raises(ProofLimbUnsatisfiedError, match="BI limb: no byte measurement for"):
        roster_only(
            producer_records=producer_set()[:2],
            verifier_records=verifier_set()[:2],
        )


def test_fb5_a_verifier_citing_the_producers_stream_under_a_distinct_object() -> None:
    """Verifier independence was decided by ``==`` on the caller's own object.

    Failing-before: the same byte stream, wrapped in two objects that deny being
    equal, was accepted as an independent re-measurement.
    """
    name = "THE-ONE-AND-ONLY-READ"
    p_prov = Provenance(
        stream_id=DistinctText(name, 1), pass_index=1, artifact_id=staged_id("EUR_USD")
    )
    v_prov = Provenance(
        stream_id=DistinctText(name, 2), pass_index=2, artifact_id=staged_id("EUR_USD")
    )
    producer = measurement(
        "EUR_USD",
        0,
        digest_provenance=p_prov,
        size_provenance=p_prov,
        span_provenance=p_prov,
        scan_provenance=p_prov,
    )
    verifier = measurement(
        "EUR_USD",
        0,
        role=ROLE_VERIFIER,
        digest_provenance=v_prov,
        size_provenance=v_prov,
        span_provenance=v_prov,
        scan_provenance=v_prov,
    )
    with pytest.raises(ProofContractError, match="rather than replaying the producer's read"):
        assert_records_agree(producer, verifier)


def test_fb5_a_consumer_replaying_a_proof_stream_under_a_distinct_object() -> None:
    """W3 freshness: ``stream_id in measured_stream_ids`` is a hash lookup.

    Failing-before: the producer's own read, wrapped in an object that hashes by
    identity, was not found in the proof's stream set and satisfied W3.
    """
    result = evaluated_proof()
    pair = PAIRS_20[7]
    rechecks = recheck_set()
    rechecks[7] = recheck(
        pair,
        7,
        provenance=Provenance(
            stream_id=DistinctText(f"producer-read-{pair}", 1),
            pass_index=1,
            artifact_id=published_id(pair),
        ),
    )
    with pytest.raises(ProofNotUsableError, match="requires the consumer's own fresh read"):
        open_for_consumption(result, consumer_rechecks=rechecks)


def test_fb5_a_two_faced_subject_naming_raw_source_bytes_is_refused() -> None:
    """D-4, at the record. Failing-before: **accepted**."""
    with pytest.raises(
        RawSourceRehashForbiddenError, match="'RAW_M1_SOURCE_BYTES' is not the derived M15"
    ):
        measurement(
            "EUR_USD",
            0,
            subject=MaskedText("RAW_M1_SOURCE_BYTES", SUBJECT_DERIVED_M15_ARTIFACT),
        )


def test_fb5_the_admissible_subject_is_stored_as_plain_character_data() -> None:
    """Negative control, and the B-3 half: what was checked is what is stored."""
    record = measurement("EUR_USD", 0, subject=MaskedText(SUBJECT_DERIVED_M15_ARTIFACT, "x"))
    assert type(record.subject) is str
    assert record.subject == SUBJECT_DERIVED_M15_ARTIFACT


def test_fb5_the_d4_guard_refuses_a_two_faced_subject() -> None:
    """``refuse_raw_source_rehash`` — **ALLOWED** before the fix, for this object."""
    with pytest.raises(RawSourceRehashForbiddenError, match="refusing to hash 'RAW_M1_SOURCE"):
        refuse_raw_source_rehash(MaskedText("RAW_M1_SOURCE_BYTES", SUBJECT_DERIVED_M15_ARTIFACT))


def test_fb5_the_d4_guard_refuses_a_non_string_subject_that_compares_equal() -> None:
    """The same family one type over: an object is not a subject because it says so."""
    with pytest.raises(RawSourceRehashForbiddenError, match="refusing to hash <"):
        refuse_raw_source_rehash(AlwaysEqual())


def test_fb5_the_d4_guard_still_permits_the_derived_artifact() -> None:
    """Negative control: the guard discriminates rather than refusing everything."""
    refuse_raw_source_rehash(SUBJECT_DERIVED_M15_ARTIFACT)


def test_fb5_the_d4_guard_runs_again_at_the_roster_boundary() -> None:
    """``object.__setattr__`` on a genuine record is the declared threat model.

    Registration cannot see it — the record really was minted — so the roster
    re-reads the subject rather than inheriting it from the type.
    """
    record = measurement("EUR_USD", 0)
    object.__setattr__(record, "subject", "RAW_M1_SOURCE_BYTES")
    with pytest.raises(RawSourceRehashForbiddenError, match="refusing to hash 'RAW_M1_SOURCE"):
        roster_only(producer_records=[record], verifier_records=[])


def test_fb5_the_promotion_guard_refuses_a_two_faced_declaration_token() -> None:
    """D-11's promotion prohibition, the most emphasised rule of the contract.

    Failing-before: ``assert_byte_level_claim`` **returned** this object as an
    accepted byte-level claim, while the plain declaration-only token beside it
    was correctly refused.
    """
    masked = MaskedText(
        DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL, BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN
    )
    with pytest.raises(ProofPromotionError, match="can never be promoted to a"):
        assert_byte_level_claim(masked)


def test_fb5_the_promotion_guard_returns_plain_character_data() -> None:
    """Negative control, and P-3: publish the value that was checked."""
    returned = assert_byte_level_claim(
        MaskedText(BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN, "ANYTHING_ELSE")
    )
    assert type(returned) is str
    assert returned == BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN
    assert assert_byte_level_claim(BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN) == (
        BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN
    )


def test_fb5_a_two_faced_declaration_record_token_is_refused() -> None:
    """Same family, same vocabulary, one class over."""
    with pytest.raises(ProofPromotionError, match="may only carry a declaration-only token"):
        DeclarationRecord(
            pair="EUR_USD",
            artifact_id="a-EUR_USD",
            declared_sha256=digest(1),
            declared_ts_min_utc=SLOTS[0],
            declared_ts_max_utc=SLOTS[-1],
            token=MaskedText(
                BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN,
                DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL,
            ),
        )


def test_fb5_a_declaration_record_with_the_real_token_is_accepted() -> None:
    """Negative control for the token pin."""
    record = DeclarationRecord(
        pair="EUR_USD",
        artifact_id="a-EUR_USD",
        declared_sha256=digest(1),
        declared_ts_min_utc=SLOTS[0],
        declared_ts_max_utc=SLOTS[-1],
        token=MaskedText(DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL, "x"),
    )
    assert type(record.token) is str
    assert record.token == DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL


def test_fb5_one_record_cannot_be_admitted_to_both_rosters() -> None:
    """The producer/verifier split, decided by ``==`` on the record's own role.

    Failing-before: a role answering every equality favourably was accepted into
    the producer set *and* the verifier set, so one measurement attested itself.
    """
    both = measurement("EUR_USD", 0, role=AgreeableText(ROLE_PRODUCER))
    assert type(both.role) is str
    assert both.role == ROLE_PRODUCER
    with pytest.raises(ProofContractError, match="declares role 'producer' in the verifier"):
        roster_only(producer_records=[both], verifier_records=[both])


def test_fb5_the_role_is_re_read_at_the_roster_boundary() -> None:
    """The role half of the same re-check the subject gets.

    Pinning at construction closes the constructor route; it does nothing about
    ``object.__setattr__`` on a genuine, registered record, which is this
    package's declared threat model. Without the roster's own pin, a role that
    answers every equality favourably is admitted to the verifier set as well.
    """
    record = measurement("EUR_USD", 0)
    object.__setattr__(record, "role", AgreeableText(ROLE_PRODUCER))
    with pytest.raises(ProofContractError, match="declares role 'producer' in the verifier"):
        roster_only(producer_records=[record], verifier_records=[record])


def test_fb5_a_spoofed_class_lands_on_the_modules_own_error_type() -> None:
    """RF-29: ``isinstance`` consults ``__class__``; the unbound slot refuses."""
    with pytest.raises(ProofContractError, match="that the str slot refuses"):
        measurement("EUR_USD", 0, staged_artifact_id=ClaimsToBeStr())


# ===========================================================================
# FB-6 — W3 is a precondition of use, and asdict/astuple bypassed it
# ===========================================================================


def test_fb6_asdict_no_longer_republishes_the_gated_identity_map() -> None:
    """Failing-before: a plain stdlib call — no hostile object, no private name —
    returned all twenty identities with ``open_for_consumption`` never called."""
    result = evaluated_proof()
    with pytest.raises(ProofNotUsableError, match="reachable only through"):
        dataclasses.asdict(result)


def test_fb6_astuple_no_longer_republishes_the_gated_identity_map() -> None:
    """``astuple`` recurses the same way; N-5's lesson one function further out."""
    result = evaluated_proof()
    with pytest.raises(ProofNotUsableError, match="reachable only through"):
        dataclasses.astuple(result)


def test_fb6_deep_copying_the_identity_map_is_refused() -> None:
    """The mechanism the two walkers arrive at, pinned directly."""
    result = evaluated_proof()
    with pytest.raises(ProofNotUsableError, match="reachable only through"):
        copy.deepcopy(result._identity)  # noqa: SLF001 - the gated field is the subject
    with pytest.raises(ProofNotUsableError, match="reachable only through"):
        copy.copy(result._identity)  # noqa: SLF001 - the gated field is the subject


def test_fb6_the_identity_repr_carries_no_digest() -> None:
    """A redacted rendering is not a leak that only looks like one."""
    result = evaluated_proof()
    rendered = repr(result._identity)  # noqa: SLF001 - the gated field is the subject
    assert digest(1) not in rendered
    assert published_id("EUR_USD") not in rendered


def test_fb6_the_only_route_to_the_identity_still_works() -> None:
    """Negative control: W3 gates the map, it does not abolish it."""
    approval = open_for_consumption(evaluated_proof(), consumer_rechecks=recheck_set())
    artifact_id, sha256, size_bytes = approval.identity["EUR_USD"]
    assert artifact_id == published_id("EUR_USD")
    assert len(sha256) == 64
    assert size_bytes > 0


def test_fb6_asdict_still_works_on_the_approval_it_gates() -> None:
    """And the refusal is specific to the gated record, not to dataclasses."""
    approval = open_for_consumption(evaluated_proof(), consumer_rechecks=recheck_set())
    published = dataclasses.asdict(approval)
    assert published["byte_level_status"] == BYTE_LEVEL_PROOF_PENDING
    assert published["files_opened"] == 0


# ===========================================================================
# FR-11 — a refutation is terminal for the evidence it condemned
# ===========================================================================


def test_fr11_re_offering_refuted_records_is_refused_terminally() -> None:
    """Failing-before: the identical call raised the identical first-time error,
    so catching and retrying was indistinguishable from never having been
    refuted, and nothing anywhere recorded that a refutation had occurred."""
    producer = measurement("EUR_USD", 0)
    verifier = measurement("EUR_USD", 0, role=ROLE_VERIFIER, size_bytes=1)
    with pytest.raises(
        ProofDisagreementError, match="identical bytes yielding different measurements"
    ):
        assert_records_agree(producer, verifier)
    with pytest.raises(ProofDisagreementError, match="does not rehabilitate it") as excinfo:
        assert_records_agree(producer, verifier)
    assert BYTE_LEVEL_PROOF_REFUTED in str(excinfo.value)
    assert excinfo.value.token == BYTE_LEVEL_PROOF_REFUTED


def test_fr11_the_refusal_quotes_the_refutation_that_was_pronounced() -> None:
    """ "Nothing recording that a refutation occurred" is the half a status token
    alone does not answer, so the reason is carried, not just the verdict."""
    producer = measurement("EUR_USD", 0)
    verifier = measurement(
        "EUR_USD", 0, role=ROLE_VERIFIER, sha256=digest(31337), re_read_sha256=digest(31337)
    )
    with pytest.raises(ProofDisagreementError, match="did not see the same artifact"):
        assert_records_agree(producer, verifier)
    with pytest.raises(ProofDisagreementError, match="The refutation was") as excinfo:
        assert_records_agree(producer, verifier)
    assert "did not see the same artifact" in str(excinfo.value)


def test_fr11_an_amended_re_run_over_a_refuted_record_is_refused() -> None:
    """The audit's scenario verbatim: refute, then re-run with the verifier fixed."""
    producers = producer_set()
    verifiers = verifier_set()
    verifiers[3] = measurement(
        PAIRS_20[3],
        3,
        role=ROLE_VERIFIER,
        sha256=digest(31337),
        re_read_sha256=digest(31337),
    )
    with pytest.raises(ProofDisagreementError, match="did not see the same artifact"):
        evaluated_proof(producer_records=producers, verifier_records=verifiers)
    with pytest.raises(ProofDisagreementError, match="does not rehabilitate it"):
        evaluated_proof(producer_records=producers, verifier_records=verifier_set())


def test_fr11_a_refuted_proof_result_cannot_be_re_opened() -> None:
    """The consumer half: a result refuted at W3 stays refuted."""
    result = evaluated_proof()
    rechecks = recheck_set()
    rechecks[7] = recheck(PAIRS_20[7], 7, sha256=digest(31337))
    with pytest.raises(ProofDisagreementError, match="digest changed between the proof"):
        open_for_consumption(result, consumer_rechecks=rechecks)
    with pytest.raises(ProofDisagreementError, match="does not rehabilitate it"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_fr11_a_tc_limb_divergence_refutes_the_record_it_was_measured_on() -> None:
    """The two dead-window definitions diverging is a refutation, not a shortfall."""
    producers = producer_set()
    verifiers = verifier_set()
    for records, role in ((producers, ROLE_PRODUCER), (verifiers, ROLE_VERIFIER)):
        records[2] = measurement(
            PAIRS_20[2],
            2,
            role=role,
            dead_window_bars_by_bucket_start=0,
            dead_window_bars_by_contributing_minute=3,
        )
    with pytest.raises(ProofDisagreementError, match="the bucketing is wrong"):
        evaluated_proof(producer_records=producers, verifier_records=verifiers)
    with pytest.raises(ProofDisagreementError, match="does not rehabilitate it"):
        evaluated_proof(producer_records=producers, verifier_records=verifier_set())


def test_fr11_a_fresh_evidence_set_is_not_condemned_by_an_earlier_refutation() -> None:
    """Negative control, and the honest limit: terminality binds the evidence that
    was refuted, not the artifact and not the process."""
    producer = measurement("EUR_USD", 0)
    verifier = measurement("EUR_USD", 0, role=ROLE_VERIFIER, size_bytes=1)
    with pytest.raises(
        ProofDisagreementError, match="identical bytes yielding different measurements"
    ):
        assert_records_agree(producer, verifier)
    assert_records_agree(measurement("EUR_USD", 0), measurement("EUR_USD", 0, role=ROLE_VERIFIER))
    assert (
        open_for_consumption(evaluated_proof(), consumer_rechecks=recheck_set()).byte_level_status
        == BYTE_LEVEL_PROOF_PENDING
    )


# ===========================================================================
# FR-20 — the pragma sat on a reachable branch
# ===========================================================================


def test_fr20_the_numeric_refusal_branch_in_require_count_is_reachable() -> None:
    """``# pragma: no cover - guarded above`` asserted this could not happen."""
    with pytest.raises(ProofContractError, match="size_bytes claims to be an int"):
        measurement("EUR_USD", 0, size_bytes=ClaimsToBeInt())


def test_fr20_the_numeric_refusal_branch_in_provenance_is_reachable() -> None:
    """The second of the two proof-layer sites the audit named."""
    with pytest.raises(
        ProofCoMeasurementError, match="provenance pass_index: pass_index claims to be an int"
    ):
        Provenance(stream_id="p-read", pass_index=ClaimsToBeInt(), artifact_id="a-EUR_USD")


def test_fr20_a_plain_count_is_still_accepted() -> None:
    """Negative control: the branch refuses spoofed numbers, not numbers."""
    assert measurement("EUR_USD", 0, size_bytes=4096).size_bytes == 4096
    assert Provenance(stream_id="p-read", pass_index=0, artifact_id="a-EUR_USD").pass_index == 0


# ===========================================================================
# FR-21 — mutation survivors: source correct, nothing pinning it
# ===========================================================================


def test_fr21_a_scalar_disagreement_is_caught_through_the_evaluator() -> None:
    """Survivor: nulling the agreement loop inside ``evaluate_four_limbs``.

    ``assert_records_agree`` was tested only as a unit, so the *call* was
    unpinned and a scalar disagreement became ACCEPTED when the loop was removed.
    """
    verifiers = verifier_set()
    verifiers[5] = measurement(PAIRS_20[5], 5, role=ROLE_VERIFIER, size_bytes=1)
    with pytest.raises(
        ProofDisagreementError, match="identical bytes yielding different measurements"
    ):
        evaluated_proof(verifier_records=verifiers)


def test_fr21_a_digest_disagreement_is_caught_through_the_evaluator() -> None:
    """The other half of the same survivor: neither BI nor DB catches this."""
    verifiers = verifier_set()
    verifiers[5] = measurement(
        PAIRS_20[5],
        5,
        role=ROLE_VERIFIER,
        sha256=digest(31337),
        re_read_sha256=digest(31337),
    )
    with pytest.raises(ProofDisagreementError, match="did not see the same artifact"):
        evaluated_proof(verifier_records=verifiers)


def test_fr21_the_evaluator_accepts_an_agreeing_record_set() -> None:
    """Negative control for the agreement loop."""
    assert evaluated_proof().byte_level_status == BYTE_LEVEL_PROOF_PENDING


def test_fr21_a_consumer_re_verifying_a_different_artifact_is_refused() -> None:
    """Survivor: the consumer's artifact-identity check.

    W3's "the re-verification is of the artifact about to be read" was unpinned,
    so a consumer holding the proof's digest and size for a *different* file was
    accepted.
    """
    result = evaluated_proof()
    pair = PAIRS_20[4]
    other = f"candles_{pair}_M15_365d_BA_SOMETHING_ELSE.jsonl"
    rechecks = recheck_set()
    rechecks[4] = recheck(
        pair,
        4,
        artifact_id=other,
        provenance=Provenance(stream_id=f"consumer-read-{pair}", pass_index=9, artifact_id=other),
    )
    with pytest.raises(ProofDisagreementError, match="but the proof was made about"):
        open_for_consumption(result, consumer_rechecks=rechecks)


def test_fr21_assert_records_agree_refuses_a_swapped_role_pair() -> None:
    """Survivor: the role pairing on the **public** entry point."""
    producer = measurement("EUR_USD", 0)
    verifier = measurement("EUR_USD", 0, role=ROLE_VERIFIER)
    with pytest.raises(
        ProofContractError, match="agreement needs one producer and one verifier record"
    ):
        assert_records_agree(verifier, producer)
    assert_records_agree(producer, verifier)


def test_fr21_is_declaration_only_answers_the_whole_vocabulary() -> None:
    """Survivor: an exported predicate with **zero** references in the suite, so
    ``return False`` survived every test that existed."""
    assert is_declaration_only(DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL) is True
    assert is_declaration_only(BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN) is False
    assert is_declaration_only(BYTE_LEVEL_PROOF_PENDING) is False
    assert is_declaration_only(BYTE_LEVEL_PROOF_REFUTED) is False
    assert is_declaration_only("SOMETHING_NOT_IN_THE_VOCABULARY") is False
    assert is_declaration_only(None) is False


def test_fr21_is_declaration_only_is_decided_on_character_data() -> None:
    """FB-5 family: set membership is answered by the caller's own hash."""
    assert (
        is_declaration_only(
            MaskedText(
                BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN,
                DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL,
            )
        )
        is False
    )
    assert (
        is_declaration_only(
            MaskedText(
                DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL,
                BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN,
            )
        )
        is True
    )


def real_coverage() -> Any:
    return assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH)


def test_fr21_a_twenty_first_coverage_entry_for_a_certified_pair_is_refused() -> None:
    """Survivor: the CV roster's set equality absorbed a 21st ``PairCoverage``.

    A dict comprehension over ``entry.pair`` let a duplicate silently *replace*
    the entry set equality had been decided over, so the extra entry left the
    roster looking canonical.
    """
    result = real_coverage()
    object.__setattr__(result, "per_pair", result.per_pair + (result.per_pair[0],))
    with pytest.raises(ProofLimbUnsatisfiedError, match="certifies EUR_USD twice"):
        evaluated_proof(coverage_result=result)


def test_fr21_a_twenty_first_coverage_entry_for_a_foreign_pair_is_refused() -> None:
    """The *superset* half of the same mutation, which the duplicate guard misses.

    Twenty canonical entries plus a twenty-first naming a pair outside the
    roster: a containment test (``covered >= PAIRS_20``) absorbs it, set
    equality does not. The extra entry is a genuine ``PairCoverage`` taken from a
    second measured result, so nothing here hand-builds a coverage verdict.
    """
    result = real_coverage()
    extra = real_coverage().per_pair[0]
    object.__setattr__(extra, "pair", "XXX_YYY")
    object.__setattr__(result, "per_pair", result.per_pair + (extra,))
    with pytest.raises(ProofLimbUnsatisfiedError, match="is not the canonical"):
        evaluated_proof(coverage_result=result)


def test_fr21_a_twenty_entry_roster_naming_a_foreign_pair_is_refused_by_name() -> None:
    """The count variant of the same mutation leaked a bare ``KeyError``.

    Exactly twenty entries, so any count-based check passes; the pair is not in
    the canonical roster, and the refusal says so instead of the lookup blowing
    up on the next line.
    """
    result = real_coverage()
    object.__setattr__(result.per_pair[0], "pair", "XXX_YYY")
    with pytest.raises(ProofLimbUnsatisfiedError, match="is not the canonical"):
        evaluated_proof(coverage_result=result)


def test_fr21_a_coverage_entry_that_is_not_a_pair_coverage_is_refused() -> None:
    """``per_pair`` is rewritable, and reading a foreign object's attributes is
    not a contract check."""
    result = real_coverage()
    object.__setattr__(result, "per_pair", (object(),) + result.per_pair[1:])
    with pytest.raises(ProofLimbUnsatisfiedError, match="coverage entry 0 is a object"):
        evaluated_proof(coverage_result=result)


def test_fr21_a_certified_slot_count_that_answers_for_itself_is_refused() -> None:
    """N-1 inside the CV limb: the count binding compared the caller's own int."""
    result = real_coverage()
    object.__setattr__(result.per_pair[0], "certified_slot_count", AgreeableCount(999))
    with pytest.raises(ProofLimbUnsatisfiedError, match="certifies 999 M15 slot"):
        evaluated_proof(coverage_result=result)


def test_fr21_an_untampered_coverage_result_still_satisfies_the_cv_limb() -> None:
    """Negative control for every CV re-check above."""
    assert evaluated_proof(coverage_result=real_coverage()).byte_level_status == (
        BYTE_LEVEL_PROOF_PENDING
    )


# ===========================================================================
# FR-4 — CLOSED: the CV limb binds the measured span, not only the count
# ===========================================================================
#
# This section replaced a test that pinned FR-4 as a known limitation and told
# its reader to delete it if the span binding ever landed. It landed: the lead
# added `certified_slot_min` / `certified_slot_max` to `PairCoverage` and the CV
# limb now compares them against the byte scan. The limitation test is gone
# because it was falsified, which is the outcome it existed to make visible.


def test_fr4_a_scan_over_a_different_span_of_the_same_length_is_refused() -> None:
    """The audit's exact construction: May coverage beside a December scan.

    Before the span binding this satisfied the whole four-limb conjunction,
    because the counts matched. It is the one case a count can never catch.
    """
    elsewhere = ("2025-12-01T00:00:00Z", "2025-12-01T00:15:00Z", "2025-12-01T00:30:00Z")
    producers = [
        measurement(pair, i, measured_ts_min=elsewhere[0], measured_ts_max=elsewhere[-1])
        for i, pair in enumerate(PAIRS_20)
    ]
    verifiers = [
        measurement(
            pair,
            i,
            role=ROLE_VERIFIER,
            measured_ts_min=elsewhere[0],
            measured_ts_max=elsewhere[-1],
        )
        for i, pair in enumerate(PAIRS_20)
    ]
    with pytest.raises(ProofLimbUnsatisfiedError, match="certifies slots from"):
        evaluated_proof(producer_records=producers, verifier_records=verifiers)


def test_fr4_a_scan_ending_elsewhere_is_refused_by_its_own_limb() -> None:
    """The upper limb pinned in isolation, so a failure names which end drifted."""
    producers = [
        measurement(pair, i, measured_ts_max="2025-05-01T01:00:00Z")
        for i, pair in enumerate(PAIRS_20)
    ]
    verifiers = [
        measurement(pair, i, role=ROLE_VERIFIER, measured_ts_max="2025-05-01T01:00:00Z")
        for i, pair in enumerate(PAIRS_20)
    ]
    with pytest.raises(ProofLimbUnsatisfiedError, match="certifies slots to"):
        evaluated_proof(producer_records=producers, verifier_records=verifiers)


def test_fr4_a_scan_over_the_certified_span_still_satisfies_the_limb() -> None:
    """Negative control: the binding discriminates, it does not refuse everything."""
    assert evaluated_proof().byte_level_status == BYTE_LEVEL_PROOF_PENDING


# ===========================================================================
# Standing disclosures the fixes must not have weakened
# ===========================================================================


def test_no_fix_here_mints_a_byte_level_claim() -> None:
    result = evaluated_proof()
    assert result.byte_level_status == BYTE_LEVEL_PROOF_PENDING
    assert result.claim_withheld_because == BYTE_LEVEL_CLAIM_WITHHELD_REASON
    assert result.evidence_basis == LIMB_EVALUATION_EVIDENCE_BASIS
    assert result.verifier_independence_limit == VERIFIER_INDEPENDENCE_LIMIT
    assert result.declared_not_measured == DECLARED_NOT_MEASURED_BY_THIS_LAYER
    assert result.files_opened == 0
    assert result.bytes_measured == 0
