"""Regression tests for the fourth fix round of the third re-check (P-1..P-7).

Every test here corresponds to a finding the fresh-context re-audit of head
``0d3af6b`` **reproduced with real output**, except where a test is labelled a
*reachability control* (it must pass before and after, and exists so a fix that
simply refuses everything cannot be mistaken for a fix).

* **P-1, P-2, P-3** are three faces of one defect family in
  :mod:`scripts.m15_gate3a.proof`: a disclosure field is compared with an
  unpinned operator, or is compared pinned and then **published unpinned**.
  ``open_for_consumption`` mints a fresh :class:`ConsumptionApproval`, so
  whatever it publishes is the record of what a consumer was told.
* **P-4** is the same unpinned-``!=`` miss one module over, in the
  ``expected_count`` cross-check of ``assert_per_file_bounds``.
* **P-5** is the BL-2/F-1 divergence guard subtracting two *caller-supplied*
  floats before pinning either of them.
* **P-6** is the R-1 trap — a reported field that can only ever hold one
  favourable value — in its fourth instance on this PR.
* **P-7** is an explicit ruling on ``verifier_independence_basis`` rather than a
  reproduced defect: the favourable half of that sentence was asserted
  unconditionally, so the sentence is restructured to state only the limit.

Nothing in this module reads real data, derives real M15, computes a real
checksum or spread, trains, validates, evaluates or executes anything.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest

from scripts.m15_gate3a import proof
from scripts.m15_gate3a.artifacts import scan_gate3a
from scripts.m15_gate3a.guards import (
    FORBIDDEN_STATUSES,
    UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS,
    is_forbidden_status,
)
from scripts.m15_gate3a.no_overlap import NoOverlapError, assert_per_file_bounds
from scripts.m15_gate3a.numeric_authority import (
    NumericAuthorityError,
    pin_float,
    pin_int,
    pin_number,
)
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_gate3a.proof import (
    BYTE_LEVEL_CLAIM_WITHHELD_REASON,
    BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN,
    BYTE_LEVEL_PROOF_PENDING,
    DECLARED_NOT_MEASURED_BY_THIS_LAYER,
    LIMB_EVALUATION_EVIDENCE_BASIS,
    ProofNotUsableError,
    open_for_consumption,
)
from scripts.m15_gate3a.timeutil import TimestampError, format_utc_z, to_utc
from tests.m15_gate3a.roster_fixtures import design_roster
from tests.m15_gate3a.test_wp_proof_coverage_calendar import (
    digest,
    evaluated_proof,
    recheck_set,
)

INSTANT = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)


# ===========================================================================
# The two-faced objects these tests are built from
# ===========================================================================


class AgreeableToken(str):
    """A ``str`` subclass that answers **every** equality favourably.

    The ordering-liar family cannot defeat ``==`` / ``!=``; this is the shape
    that can. Its real character data is whatever it was constructed with, so
    any guard that reads that data first sees the truth.
    """

    def __eq__(self, other: Any) -> bool:
        return True

    def __ne__(self, other: Any) -> bool:
        return False

    __hash__ = str.__hash__


class AgreeableInt(int):
    """The ``int`` member of the same equality-lying family."""

    def __eq__(self, other: Any) -> bool:
        return True

    def __ne__(self, other: Any) -> bool:
        return False

    __hash__ = int.__hash__


class TwoFacedToken(str):
    """Real character data one thing, every *rendering* another.

    ``json.dumps`` writes the character data, so a JSON artifact would be safe.
    ``str()``, ``repr()`` and ``f"{...}"`` are what a human, a log line and an
    f-string-built message see, and all three are overridden here.
    """

    def __new__(cls, real: str, shown: str) -> TwoFacedToken:
        obj = super().__new__(cls, real)
        obj._shown = shown  # noqa: SLF001 - the whole point of the fixture
        return obj

    def __str__(self) -> str:
        return self._shown

    def __repr__(self) -> str:
        return self._shown

    def __format__(self, spec: str) -> str:
        return self._shown


class DriftFreeFloat(float):
    """A ``float`` subclass that answers every subtraction with zero.

    It lies through the *arithmetic*, not through a comparison, so a guard that
    subtracts before pinning never sees the real difference.
    """

    def __sub__(self, other: Any) -> DriftFreeFloat:
        return DriftFreeFloat(0.0)

    def __rsub__(self, other: Any) -> DriftFreeFloat:
        return DriftFreeFloat(0.0)

    def __abs__(self) -> DriftFreeFloat:
        return DriftFreeFloat(0.0)


class PlainFloatLiar(datetime):
    """A ``datetime`` subclass whose ``timestamp()`` is an hour off, honestly."""

    def timestamp(self) -> float:
        return datetime.timestamp(self) + 3600.0


class SubclassFloatLiar(datetime):
    """The same lie, returned as a ``float`` subclass that cancels the subtraction."""

    def timestamp(self) -> float:
        return DriftFreeFloat(datetime.timestamp(self) + 3600.0)


class NonNumericInstant(datetime):
    """``timestamp()`` that is not a number at all."""

    def timestamp(self) -> Any:
        return "0.0"


# ===========================================================================
# P-1 — `declared_not_measured` is compared element-wise, unpinned
# ===========================================================================


def _forged_disclosure(spelling: str) -> tuple[AgreeableToken, ...]:
    """A same-length disclosure list every element of which claims equality."""
    return tuple(AgreeableToken(spelling) for _ in DECLARED_NOT_MEASURED_BY_THIS_LAYER)


@pytest.mark.parametrize(
    "spelling",
    ["", "-", "measured", "MEASURED_FROM_DERIVED_ARTIFACT_BYTES"],
)
def test_p1_a_same_length_forged_disclosure_cannot_mint_an_approval(spelling: str) -> None:
    """P-1's headline: ``tuple(...) != CONSTANT`` compares element-wise with ``==``.

    Failing-before: no exception at all. ``open_for_consumption`` returned an
    approval whose ``declared_not_measured`` was thirteen copies of *spelling* —
    with ``''`` the disclosure of which quantities were consumed as declarations
    is simply erased, and with ``MEASURED_FROM_DERIVED_ARTIFACT_BYTES`` it is
    inverted into the opposite assertion. The existing N-2 test only shortens the
    list, which the length half of the comparison already caught.
    """
    result = evaluated_proof()
    object.__setattr__(result, "declared_not_measured", _forged_disclosure(spelling))
    with pytest.raises(ProofNotUsableError, match="declared_not_measured entry"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_p1_a_shortened_disclosure_still_names_the_length_it_lost() -> None:
    """The length half keeps its own raise site, so the N-2 test still names it."""
    result = evaluated_proof()
    object.__setattr__(result, "declared_not_measured", ("sha256",))
    with pytest.raises(ProofNotUsableError, match="declared_not_measured list is not the one"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_p1_a_disclosure_that_is_not_a_sequence_at_all_is_refused() -> None:
    result = evaluated_proof()
    object.__setattr__(result, "declared_not_measured", "sha256")
    with pytest.raises(ProofNotUsableError, match="declared_not_measured is not a list"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_p1_the_published_disclosure_is_the_pinned_one() -> None:
    """Reachability control **and** the publication half of the fix."""
    approval = open_for_consumption(evaluated_proof(), consumer_rechecks=recheck_set())
    assert approval.declared_not_measured == DECLARED_NOT_MEASURED_BY_THIS_LAYER
    assert all(type(entry) is str for entry in approval.declared_not_measured)


# ===========================================================================
# P-2 — `(files_opened, bytes_measured) != (0, 0)` is unpinned
# ===========================================================================


@pytest.mark.parametrize("field", ["files_opened", "bytes_measured"])
@pytest.mark.parametrize("count", [20, 999])
def test_p2_an_equality_lying_count_cannot_pass_the_no_bytes_disclosure(
    field: str, count: int
) -> None:
    """P-2's headline: an N-1 miss *inside* the N-2 fix.

    Failing-before: no exception. The tuple comparison asked the caller's own
    ``int`` subclass whether it equalled zero, and it said yes while holding
    20 / 999 — so a record declaring that this layer had opened files minted an
    approval that repeats ``files_opened=0``.
    """
    result = evaluated_proof()
    object.__setattr__(result, field, AgreeableInt(count))
    with pytest.raises(ProofNotUsableError, match="this layer opens no file"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


@pytest.mark.parametrize("field", ["files_opened", "bytes_measured"])
def test_p2_a_non_integer_count_is_refused_on_its_type(field: str) -> None:
    result = evaluated_proof()
    object.__setattr__(result, field, 0.0)
    with pytest.raises(ProofNotUsableError, match="is not a plain integer count"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_p2_the_published_counts_are_plain_ints() -> None:
    approval = open_for_consumption(evaluated_proof(), consumer_rechecks=recheck_set())
    assert type(approval.files_opened) is int and approval.files_opened == 0
    assert type(approval.bytes_measured) is int and approval.bytes_measured == 0


# ===========================================================================
# P-3 — pin for the comparison, publish the pinned object
# ===========================================================================


@pytest.mark.parametrize(
    ("field", "real", "shown"),
    [
        ("byte_level_status", BYTE_LEVEL_PROOF_PENDING, BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN),
        (
            "evidence_basis",
            LIMB_EVALUATION_EVIDENCE_BASIS,
            "MEASURED_FROM_DERIVED_ARTIFACT_BYTES__PRODUCER_AND_VERIFIER_AGREE",
        ),
        ("claim_withheld_because", BYTE_LEVEL_CLAIM_WITHHELD_REASON, "NOTHING_IS_WITHHELD"),
    ],
)
def test_p3_a_two_faced_token_cannot_reach_the_approval(field: str, real: str, shown: str) -> None:
    """P-3's headline: ``_pin_token`` pinned, and the UNPINNED original was published.

    Failing-before: ``open_for_consumption`` succeeded — the pin sees the real
    character data, which is the permitted spelling — and the approval carried
    the caller's subclass, so ``str()``, ``repr()`` and ``f"{...}"`` on the
    approval's own field all asserted the byte-level claim. That is B-3's rule
    ("check and publish the same objects") broken inside the fix meant to
    enforce it.
    """
    result = evaluated_proof()
    object.__setattr__(result, field, TwoFacedToken(real, shown))
    approval = open_for_consumption(result, consumer_rechecks=recheck_set())
    published = getattr(approval, field)
    assert type(published) is str
    assert published == real
    assert str(published) == real
    assert f"{published}" == real
    assert repr(published) == repr(real)


def test_p3_a_tampered_inventory_digest_cannot_be_carried_onto_an_approval() -> None:
    """The digest was repeated onto the approval and never re-checked.

    Failing-before: no exception, and ``approval.inventory_digest`` came back as
    ``'NO_INVENTORY_EVER_EXISTED'``.
    """
    result = evaluated_proof()
    object.__setattr__(result, "inventory_digest", "NO_INVENTORY_EVER_EXISTED")
    with pytest.raises(ProofNotUsableError, match="inventory_digest is no longer"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_p3_a_two_faced_inventory_digest_is_published_as_plain_character_data() -> None:
    result = evaluated_proof()
    real = digest(4242)
    object.__setattr__(result, "inventory_digest", TwoFacedToken(real, "a" * 64))
    approval = open_for_consumption(result, consumer_rechecks=recheck_set())
    assert type(approval.inventory_digest) is str
    assert f"{approval.inventory_digest}" == real


class DriftingIdentityMap(Mapping):
    """A ``Mapping`` that answers honestly once per key, then drifts.

    ``open_for_consumption`` verified one read of ``result._identity[pair]``
    against the consumer's re-check and then built the published map from three
    *further* reads of the same mapping.
    """

    def __init__(self, real: Mapping) -> None:
        self._real = real
        self._reads: Counter = Counter()

    def __getitem__(self, key: str) -> Any:
        self._reads[key] += 1
        identity = self._real[key]
        if self._reads[key] == 1:
            return identity
        return proof._ArtifactIdentity(  # noqa: SLF001 - the fixture forges the private record
            artifact_id="forged-artifact",
            sha256="f" * 64,
            size_bytes=1,
            measured_stream_ids=identity.measured_stream_ids,
        )

    def __iter__(self) -> Any:
        return iter(self._real)

    def __len__(self) -> int:
        return len(self._real)


def test_p3_the_published_identity_is_the_identity_that_was_re_verified() -> None:
    """The identity half of "publish what you checked".

    Failing-before: every entry of ``approval.identity`` came back as
    ``('forged-artifact', 'ffff…', 1)`` while the consumer re-check had been
    compared against the honest one.
    """
    result = evaluated_proof()
    real = dict(result._identity)  # noqa: SLF001 - W3 keeps the map private
    object.__setattr__(result, "_identity", DriftingIdentityMap(real))
    approval = open_for_consumption(result, consumer_rechecks=recheck_set())
    for pair in PAIRS_20:
        artifact_id, sha256, size_bytes = approval.identity[pair]
        assert artifact_id == real[pair].artifact_id
        assert sha256 == real[pair].sha256
        assert size_bytes == real[pair].size_bytes


def test_p3_an_identity_entry_that_is_not_the_evaluators_record_is_refused() -> None:
    result = evaluated_proof()
    object.__setattr__(result, "_identity", dict.fromkeys(PAIRS_20, object()))
    with pytest.raises(ProofNotUsableError, match="identity entry is a"):
        open_for_consumption(result, consumer_rechecks=recheck_set())


def test_p3_an_untampered_proof_still_opens_for_consumption() -> None:
    """Reachability control: the re-check refuses tampering, not every proof."""
    approval = open_for_consumption(evaluated_proof(), consumer_rechecks=recheck_set())
    assert approval.byte_level_status == BYTE_LEVEL_PROOF_PENDING
    assert approval.claim_withheld_because == BYTE_LEVEL_CLAIM_WITHHELD_REASON
    assert approval.evidence_basis == LIMB_EVALUATION_EVIDENCE_BASIS
    assert approval.inventory_digest == digest(4242)


# ===========================================================================
# P-4 — the `expected_count` cross-check is unpinned
# ===========================================================================


def test_p4_a_plain_wrong_expected_count_is_refused() -> None:
    """Reachability control: the plain-``int`` half of the guard works."""
    with pytest.raises(NoOverlapError, match="expected 999 files"):
        assert_per_file_bounds(design_roster(), role="design", expected_count=999)


def test_p4_an_equality_lying_expected_count_is_refused_too() -> None:
    """P-4's headline: ``len(records) != expected_count`` asked the caller's object.

    Failing-before: ``expected_count=999`` plain was REFUSED and the identical
    value wrapped in an equality-lying ``int`` subclass was ACCEPTED.
    """
    with pytest.raises(NoOverlapError, match="expected 999 files"):
        assert_per_file_bounds(design_roster(), role="design", expected_count=AgreeableInt(999))


@pytest.mark.parametrize("bad", [20.0, "20", True])
def test_p4_a_non_integer_expected_count_is_refused_on_its_type(bad: Any) -> None:
    with pytest.raises(NoOverlapError, match="expected_count must be an int"):
        assert_per_file_bounds(design_roster(), role="design", expected_count=bad)


def test_p4_a_correct_expected_count_still_passes() -> None:
    record = assert_per_file_bounds(design_roster(), role="design", expected_count=20)
    assert len(record["certified_spans"]) == len(PAIRS_20)


# ===========================================================================
# P-5 — the BL-2/F-1 divergence guard subtracted before pinning
# ===========================================================================


def test_p5_a_plain_float_instant_liar_is_refused() -> None:
    """Reachability control: the honest-arithmetic half of the guard works."""
    with pytest.raises(TimestampError, match="instant disagrees with its own components"):
        to_utc(PlainFloatLiar(2025, 6, 2, 0, 0, tzinfo=UTC))


def test_p5_a_subclass_float_instant_liar_is_refused_too() -> None:
    """P-5's headline: ``abs(a - b)`` was evaluated on the caller's own floats.

    Failing-before: the plain-float liar was REFUSED and the identical lie
    returned as a ``float`` subclass overriding ``__sub__``/``__abs__`` was
    ACCEPTED — ``format_utc_z`` then emitted ``'2025-06-02T00:00:00Z'`` for an
    instant its own ``timestamp()`` put an hour away.
    """
    with pytest.raises(TimestampError, match="instant disagrees with its own components"):
        to_utc(SubclassFloatLiar(2025, 6, 2, 0, 0, tzinfo=UTC))


def test_p5_a_non_numeric_timestamp_fails_closed_with_the_modules_own_error() -> None:
    """Failing-before: a bare ``TypeError`` escaped ``to_utc``'s documented type."""
    with pytest.raises(TimestampError, match="timestamp\\(\\) did not return a number"):
        to_utc(NonNumericInstant(2025, 6, 2, 0, 0, tzinfo=UTC))


def test_p5_an_honest_datetime_subclass_still_converts() -> None:
    """Reachability control: pinning must not refuse a subclass that tells the truth."""

    class HonestSubclass(datetime):
        pass

    assert format_utc_z(HonestSubclass(2025, 6, 2, 0, 0, tzinfo=UTC)) == "2025-06-02T00:00:00Z"
    assert to_utc(INSTANT) == INSTANT


# ===========================================================================
# P-6 — the R-1 trap, fourth instance: the roster report
# ===========================================================================

_FAVOURABLE_ROSTER_FIELDS = (
    "missing_pairs",
    "duplicate_pairs",
    "unknown_pairs",
    "non_canonical_pair_spellings",
    "actual_pairs",
    "actual_record_count",
)


@pytest.mark.parametrize("field", _FAVOURABLE_ROSTER_FIELDS)
def test_p6_the_record_carries_no_one_valued_favourable_roster_field(field: str) -> None:
    """P-6's headline: six fields that can only ever hold the favourable value.

    The roster guard raises on ``missing or duplicate or unknown or
    non_canonical``, so on the only path that *returns* all four lists are
    empty, ``actual_pairs`` equals ``expected_pairs`` and ``actual_record_count``
    equals ``expected_pair_count``. That is the shape round 2 deleted from
    ``aggregate_assertions`` and round 3 deleted from ``pairs_measured``.

    Failing-before: every one of these keys was present, and every one of them
    read as a measured reconciliation.
    """
    record = assert_per_file_bounds(design_roster(), role="design")
    assert field not in record


def test_p6_the_requirement_the_evidence_was_bound_to_is_still_disclosed() -> None:
    """What survives states what was *required*, not what was favourably found."""
    record = assert_per_file_bounds(design_roster(), role="design")
    assert record["expected_pairs"] == list(PAIRS_20)
    assert record["expected_pair_count"] == len(PAIRS_20)


def test_p6_the_roster_is_recoverable_from_the_certified_spans_instead() -> None:
    """N-4's remedy, applied again: recover the roster from the evidence."""
    record = assert_per_file_bounds(design_roster(), role="design")
    assert tuple(span["pair"] for span in record["certified_spans"]) == PAIRS_20


@pytest.mark.parametrize(
    ("mutate", "phrase"),
    [
        (lambda roster: roster[:19], "missing="),
        (
            lambda roster: [
                *roster[:19],
                {**roster[0], "filename": "twin.jsonl", "sha256": f"{99:064x}"},
            ],
            "duplicate=",
        ),
        (lambda roster: [*roster[:19], {**roster[19], "pair": "XXX_YYY"}], "unknown="),
        (lambda roster: [{**roster[0], "pair": "eur/usd"}, *roster[1:]], "non_canonical="),
    ],
)
def test_p6_a_broken_roster_still_names_what_broke_it(mutate: Any, phrase: str) -> None:
    """The four lists stay two-valued where they are two-valued: the raise site."""
    with pytest.raises(NoOverlapError) as exc:
        assert_per_file_bounds(mutate(design_roster()), role="design")
    assert phrase in str(exc.value)


# ===========================================================================
# P-7 — an explicit ruling on the verifier-independence sentence
# ===========================================================================


def test_p7_the_record_states_the_independence_limit_not_a_favourable_basis() -> None:
    """P-7's ruling: the favourable clause was asserted unconditionally.

    ``VERIFIER_INDEPENDENCE_BASIS`` opened with
    ``DISTINCT_DECLARED_BYTE_STREAM_PASSES_OVER_THE_SAME_STAGED_ARTIFACT__``,
    which is unfalsifiable here — a shared stream id *raises* in
    ``assert_records_agree``, so no record carrying that sentence can ever have
    failed it. The sentence is restructured to state only what is **not**
    excluded; the precondition is named as a precondition a raise enforces, and
    the field is renamed so its key does not read as an attestation.

    Failing-before: ``AttributeError: 'ProofResult' object has no attribute
    'verifier_independence_limit'``.
    """
    result = evaluated_proof()
    assert not hasattr(result, "verifier_independence_basis")
    assert result.verifier_independence_limit == proof.VERIFIER_INDEPENDENCE_LIMIT
    assert proof.VERIFIER_INDEPENDENCE_LIMIT.startswith(
        "SHARED_SCALAR_DERIVATION_CODE_NOT_EXCLUDED_BY_THIS_LAYER"
    )


def test_p7_the_restructured_sentence_is_itself_writable_clean() -> None:
    """A disclaimer that the scrubber would refuse is not a usable disclaimer."""
    assert is_forbidden_status(proof.VERIFIER_INDEPENDENCE_LIMIT) is False
    assert scan_gate3a({"verifier_independence_limit": proof.VERIFIER_INDEPENDENCE_LIMIT}) == []


def test_p7_the_limit_names_the_quantity_the_layer_never_measured() -> None:
    """The sentence and the declared-not-measured list must not disagree."""
    assert "verifier_scalar_derivation_independence" in DECLARED_NOT_MEASURED_BY_THIS_LAYER


def test_p7_the_independence_precondition_is_still_enforced_by_a_raise() -> None:
    """Restructuring the sentence must not have removed the check it describes."""
    from tests.m15_gate3a.test_wp_proof_coverage_calendar import producer_set, verifier_set

    producers = producer_set()
    verifiers = verifier_set()
    with pytest.raises(proof.ProofContractError, match="cites the producer's own byte-stream pass"):
        proof.assert_records_agree(
            producers[0],
            proof.MeasurementRecord(
                **{
                    **{
                        f.name: getattr(verifiers[0], f.name)
                        for f in proof.MeasurementRecord.__dataclass_fields__.values()
                    },
                    "digest_provenance": producers[0].digest_provenance,
                    "size_provenance": producers[0].digest_provenance,
                    "span_provenance": producers[0].digest_provenance,
                    "scan_provenance": producers[0].digest_provenance,
                }
            ),
        )


# ===========================================================================
# The two "ALSO" items: the prohibition-bound prose, and `__class__` spoofing
# ===========================================================================


class SpoofedInt:
    """Not an ``int``, but ``isinstance(x, int)`` says otherwise.

    ``isinstance`` consults ``__class__``, which any object may claim. The
    unbound ``int.__index__`` slot is not fooled — it refuses — but it refused
    with a bare ``TypeError``, which is not the error type every caller of the
    numeric authority is documented to wrap.
    """

    __class__ = int  # type: ignore[assignment]


class SpoofedFloat:
    """The ``float`` member of the same shape."""

    __class__ = float  # type: ignore[assignment]


@pytest.mark.parametrize("pin", [pin_int, pin_number, pin_float])
@pytest.mark.parametrize("spoof", [SpoofedInt, SpoofedFloat])
def test_also_class_spoofing_fails_closed_as_the_modules_own_error(pin: Any, spoof: Any) -> None:
    """Failing-before: ``pin_int(SpoofedInt())`` raised ``TypeError``, not the module's error.

    Still fail-closed either way — nothing was ever accepted — but it escaped the
    wrapping ``proof._require_count`` and every other caller performs, arriving
    as a type those callers do not catch.
    """
    with pytest.raises(NumericAuthorityError):
        pin(spoof(), what="spoofed")


def test_also_the_prohibition_entry_bound_arithmetic_the_comment_states() -> None:
    """The guards comment said the bound would rise to 41; the token is 40 characters.

    Not a source-text assertion: what is pinned is the arithmetic the comment
    describes — the longest ``FORBIDDEN_STATUSES`` entry, and the length the
    bound would have become had the claim vocabulary been folded into it.
    """
    from scripts.m15_gate3a.artifacts import _MAX_PROHIBITION_ENTRY_LEN

    assert _MAX_PROHIBITION_ENTRY_LEN == max(len(s) for s in FORBIDDEN_STATUSES) == 22
    assert max(len(s) for s in UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS) == 40
