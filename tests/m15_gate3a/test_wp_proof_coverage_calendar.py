"""Contract tests for the byte-level proof, coverage and calendar interfaces.

Covers audit **B-2** (token discipline), **B-3** (the certified value is the
published value), **B-7(a)** (both epoch limbs pinned *in isolation*), and the
contract Gate-decision rulings **D-4 · D-5 · D-6 · D-8 · D-10 · D-11** with
§12 requirements 8-15.

House rules observed throughout, each grounded in a defect this suite previously
concealed: no regex alternation in ``pytest.raises(match=...)`` — every match
string identifies exactly one ``raise`` site; no assertions on source text; no
vacuous globs; no dependence on host state; no test freezes a fail-open as
expected behaviour; only the modules' own exception types.
"""

from __future__ import annotations

import inspect
import re
import subprocess
import sys
from datetime import datetime, timedelta, tzinfo
from pathlib import Path
from typing import Any

import pytest

from scripts.m15_gate3a import calendar_authority, coverage, no_overlap, proof
from scripts.m15_gate3a.calendar_authority import (
    CALENDAR_APPROVAL_MARKER,
    CalendarAbsentError,
    CalendarAmbiguousError,
    CalendarEpochMismatchError,
    CalendarMalformedError,
    CalendarUnapprovedError,
    ValidatedCalendar,
    validate_calendar,
)
from scripts.m15_gate3a.coverage import (
    CoverageEvidenceError,
    CoverageMeasurementMissingError,
    CoverageResult,
    CoverageSetMismatchError,
    MinuteAccountingError,
    PairSlotMeasurement,
    RejectedSlotCountedCoveredError,
    assert_full_coverage,
    measure_pair_coverage,
)
from scripts.m15_gate3a.no_overlap import (
    DESIGN_END,
    DESIGN_START,
    FORWARD_FLOOR,
    NoOverlapError,
    assert_forward_bounds,
    assert_per_file_bounds,
    is_dead_window_instant,
)
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_gate3a.proof import (
    AGGREGATE_ASSERTIONS,
    BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN,
    BYTE_LEVEL_PROOF_PENDING,
    BYTE_LEVEL_PROOF_REFUTED,
    DECLARATION_ONLY_TOKENS,
    DERIVATION_IDENTITY_BOUND,
    FOUR_LIMBS,
    ROLE_PRODUCER,
    ROLE_VERIFIER,
    SUBJECT_DERIVED_M15_ARTIFACT,
    TOKEN_EVIDENTIARY_BASIS,
    TOKEN_VOCABULARY,
    AggregateAssertionUnsatisfiedError,
    ConsumerRecheck,
    DeclarationRecord,
    DerivationBinding,
    MeasurementRecord,
    ProofCoMeasurementError,
    ProofContractError,
    ProofDisagreementError,
    ProofLimbAbsentError,
    ProofLimbUnsatisfiedError,
    ProofNotUsableError,
    ProofPromotionError,
    Provenance,
    RawSourceRehashForbiddenError,
    assert_byte_level_claim,
    assert_measured_conjunction,
    assert_records_agree,
    current_byte_level_proof_status,
    evaluate_four_limbs,
    open_for_consumption,
    refuse_raw_source_rehash,
)
from scripts.m15_gate3a.timeutil import to_utc
from tests.m15_gate3a.roster_fixtures import design_roster, forward_roster

EPOCH = "M15_DESIGN_SPAN_SYNTHETIC_TEST_EPOCH"
OTHER_EPOCH = "M15_FORWARD_SPAN_SYNTHETIC_TEST_EPOCH"

# Three consecutive M15 slots inside the design span. Small on purpose: the
# quantities under test are set membership and conjunction, not volume.
SLOTS: tuple[str, ...] = (
    "2025-05-01T00:00:00Z",
    "2025-05-01T00:15:00Z",
    "2025-05-01T00:30:00Z",
)
MINUTES_PER_SLOT = 15

_OMIT = object()


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def calendar_artifact(**overrides: Any) -> dict[str, Any]:
    """A synthetic, well-formed calendar artifact.

    Every market-hours value here is a placeholder supplied *by the fixture*.
    Neither this test nor the module under test decides any real market hour;
    the artifact for the target epoch is a separate human + ChatGPT approval
    item (``PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED``).
    """
    artifact: dict[str, Any] = {
        "authority": "synthetic session authority (test fixture, not a real broker)",
        "authority_version": "fixture-2026-01-01",
        "timezone": "UTC",
        "market_open_close_rule": "declared by the injected artifact",
        "dst_rule": "declared by the injected artifact",
        "exceptional_closure_handling": "declared by the injected artifact",
        "target_epoch": EPOCH,
        "content_digest": "synthetic-calendar-content-digest-v1",
        "approval": CALENDAR_APPROVAL_MARKER,
        "expected_m15_slots": {pair: list(SLOTS) for pair in PAIRS_20},
    }
    artifact.update(overrides)
    return {key: value for key, value in artifact.items() if value is not _OMIT}


def valid_calendar(**overrides: Any) -> ValidatedCalendar:
    return validate_calendar(calendar_artifact(**overrides), expected_epoch=EPOCH)


def accounting(
    *, slots: int = len(SLOTS), absent: int = 0, rejected: int = 0, max_gap: int = 0
) -> dict[str, int]:
    """The six D-3 quantities for a pair whose expected span is ``slots`` buckets."""
    expected = slots * MINUTES_PER_SLOT
    usable = expected - absent - rejected
    return {
        "expected_source_minute_count": expected,
        "observed_source_minute_count": usable + rejected,
        "absent_source_minute_count": absent,
        "rejected_source_minute_count": rejected,
        "usable_source_minute_count": usable,
        "max_unavailable_gap_minutes": max_gap,
    }


def bars(slots: tuple[str, ...] | list[str]) -> list[dict[str, Any]]:
    """Distinct bar objects, each declaring its bucket start under ``ts``."""
    return [{"ts": slot, "n_source_bars": MINUTES_PER_SLOT} for slot in slots]


def pair_measurement(
    pair: str,
    *,
    slots: tuple[str, ...] | list[str] = SLOTS,
    rejected_slots: tuple[str, ...] | list[str] = (),
    minute_accounting: dict[str, int] | None = None,
) -> PairSlotMeasurement:
    return measure_pair_coverage(
        pair=pair,
        certified_bars=bars(slots),
        minute_accounting=minute_accounting or accounting(),
        rejected_slots=list(rejected_slots),
    )


def full_measurements(**overrides: Any) -> list[PairSlotMeasurement]:
    return [pair_measurement(pair, **overrides) for pair in PAIRS_20]


def digest(index: int) -> str:
    return f"{index:064x}"


def provenance(stream: str, index: int = 1) -> Provenance:
    return Provenance(stream_id=stream, pass_index=index)


def measurement(
    pair: str, index: int, *, role: str = ROLE_PRODUCER, **overrides: Any
) -> MeasurementRecord:
    prov = provenance(f"{role}-read-{pair}")
    fields: dict[str, Any] = {
        "role": role,
        "pair": pair,
        "artifact_id": f"candles_{pair}_M15_365d_BA_DESIGN.jsonl",
        "subject": SUBJECT_DERIVED_M15_ARTIFACT,
        "sha256": digest(index + 1),
        "re_read_sha256": digest(index + 1),
        "staged_artifact_id": f"candles_{pair}_M15_365d_BA_DESIGN.jsonl.staging",
        "size_bytes": 4096 + index,
        "row_count": 512 + index,
        "bars_scanned": 512 + index,
        "measured_ts_min": "2025-05-01T00:00:00Z",
        "measured_ts_max": "2026-02-28T23:45:00Z",
        "dead_window_bars_by_bucket_start": 0,
        "dead_window_bars_by_contributing_minute": 0,
        "out_of_design_range_bar_count": 0,
        "digest_provenance": prov,
        "size_provenance": prov,
        "span_provenance": prov,
        "scan_provenance": prov,
    }
    fields.update(overrides)
    return MeasurementRecord(**fields)


def producer_set(**overrides: Any) -> list[MeasurementRecord]:
    return [measurement(p, i, role=ROLE_PRODUCER, **overrides) for i, p in enumerate(PAIRS_20)]


def verifier_set(**overrides: Any) -> list[MeasurementRecord]:
    return [measurement(p, i, role=ROLE_VERIFIER, **overrides) for i, p in enumerate(PAIRS_20)]


def binding_set(**overrides: Any) -> list[DerivationBinding]:
    out = []
    for index, pair in enumerate(PAIRS_20):
        fields: dict[str, Any] = {
            "pair": pair,
            "script_name": "scripts/m15_gate3a_continuation/derive_design_m15.py",
            "git_sha": "0" * 40,
            "config_hash": digest(999),
            "source_identity": "RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1",
            "re_derivation_sha256": digest(index + 1),
        }
        fields.update(overrides)
        out.append(DerivationBinding(**fields))
    return out


def recheck_set(**overrides: Any) -> list[ConsumerRecheck]:
    out = []
    for index, pair in enumerate(PAIRS_20):
        fields: dict[str, Any] = {
            "pair": pair,
            "artifact_id": f"candles_{pair}_M15_365d_BA_DESIGN.jsonl",
            "sha256": digest(index + 1),
            "size_bytes": 4096 + index,
            "provenance": provenance(f"consumer-read-{pair}", index=9),
        }
        fields.update(overrides)
        out.append(ConsumerRecheck(**fields))
    return out


def evaluated_proof(**overrides: Any):
    kwargs: dict[str, Any] = {
        "producer_records": producer_set(),
        "verifier_records": verifier_set(),
        "coverage_result": assert_full_coverage(
            full_measurements(), valid_calendar(), expected_epoch=EPOCH
        ),
        "derivation_bindings": binding_set(),
        "inventory_digest": digest(4242),
    }
    kwargs.update(overrides)
    return evaluate_four_limbs(**kwargs)


class DriftingTZ(tzinfo):
    """CPython-legal ``tzinfo`` whose offset is stable per parse, then shifts.

    The awareness authority calls ``utcoffset()`` twice per parse and requires
    the two to agree, so this stays legal while still handing a *second* parse a
    different instant. That is the shape audit B-3 used.
    """

    def __init__(self, first: timedelta, later: timedelta) -> None:
        self.calls = 0
        self._first = first
        self._later = later

    def utcoffset(self, dt: datetime | None) -> timedelta:
        self.calls += 1
        return self._first if self.calls <= 2 else self._later

    def dst(self, dt: datetime | None) -> timedelta:
        return timedelta(0)

    def tzname(self, dt: datetime | None) -> str:
        return "DRIFT"


# ===========================================================================
# B-3 — the certified value must be the published value
# ===========================================================================


def test_b3_published_span_is_the_span_that_was_bound_checked() -> None:
    """Parse once: the drifting second parse that published a dead-window span is gone.

    Before the fix this returned the proof token while publishing
    ``ts_max = 2026-03-01T11:00:00+00:00`` — inside the dead window, beside a
    token asserting there is none.
    """
    tz = DriftingTZ(first=timedelta(hours=23), later=timedelta(0))
    roster = design_roster()
    roster[0]["ts_max_utc"] = datetime(2026, 3, 1, 11, 0, 0, tzinfo=tz)

    result = assert_per_file_bounds(roster, role="design", expected_count=20)
    published = to_utc(result["certified_spans"][0]["ts_max_utc"])

    assert tz.calls == 2, "the hostile tzinfo was consulted by more than one parse"
    assert published <= DESIGN_END
    assert not is_dead_window_instant(published)


def test_b3_a_span_whose_first_parse_violates_the_ceiling_publishes_nothing() -> None:
    """The other drift direction: the value that is checked is the one that is refused."""
    tz = DriftingTZ(first=timedelta(0), later=timedelta(hours=23))
    roster = design_roster()
    roster[0]["ts_max_utc"] = datetime(2026, 3, 1, 11, 0, 0, tzinfo=tz)
    with pytest.raises(NoOverlapError, match="exceeds the frozen design-epoch ceiling"):
        assert_per_file_bounds(roster, role="design", expected_count=20)
    assert tz.calls == 2


def test_b3_published_identity_is_the_identity_the_roster_guards_used() -> None:
    result = assert_per_file_bounds(design_roster(), role="design", expected_count=20)
    spans = result["certified_spans"]
    assert {span["pair"] for span in spans} == set(PAIRS_20)
    assert len({span["sha256"] for span in spans}) == len(PAIRS_20)
    assert len({span["filename"] for span in spans}) == len(PAIRS_20)
    for span in spans:
        assert type(span["pair"]) is str
        assert type(span["sha256"]) is str
        assert type(span["filename"]) is str


# ===========================================================================
# B-2 / §12.13 — token discipline
# ===========================================================================


def test_b2_declaration_path_emits_a_declaration_only_token() -> None:
    result = assert_per_file_bounds(design_roster(), role="design", expected_count=20)
    assert result["result"] in DECLARATION_ONLY_TOKENS
    assert result["result"] not in (TOKEN_VOCABULARY - DECLARATION_ONLY_TOKENS), (
        "the declaration path must not reach any other token in the vocabulary"
    )


def test_b2_result_states_that_its_bounds_are_declared_not_measured() -> None:
    result = assert_per_file_bounds(design_roster(), role="design", expected_count=20)
    assert result["evidence_basis"] == no_overlap.DECLARATION_ONLY_EVIDENCE_BASIS
    assert result["files_opened"] == 0
    assert result["bytes_measured"] == 0
    assert set(result["declared_not_measured"]) >= {"ts_min_utc", "ts_max_utc", "sha256"}


def test_b2_declaration_token_is_refused_where_a_byte_level_claim_is_required() -> None:
    result = assert_per_file_bounds(design_roster(), role="design", expected_count=20)
    with pytest.raises(ProofPromotionError, match="can never be promoted to a"):
        assert_byte_level_claim(result["result"])


def test_b2_no_byte_level_token_is_reachable_from_the_declaration_module() -> None:
    """Structural, not editorial: the byte-level strings are not in that namespace."""
    claims = TOKEN_VOCABULARY - DECLARATION_ONLY_TOKENS
    reachable = {value for value in vars(no_overlap).values() if isinstance(value, str)}
    assert reachable.isdisjoint(claims)

    result = assert_per_file_bounds(design_roster(), role="design", expected_count=20)
    emitted = {value for value in result.values() if isinstance(value, str)}
    for span in result["certified_spans"]:
        emitted.update(value for value in span.values() if isinstance(value, str))
    assert emitted.isdisjoint(claims)


def test_the_import_direction_is_one_way_declaration_never_reaches_proof() -> None:
    """§12.14: pin the import direction, not just the current contents of a namespace.

    Run in a fresh interpreter, because this test module has itself already
    imported ``proof`` — asking ``sys.modules`` in-process would answer about the
    test, not about the module under test.
    """
    probe = (
        "import sys;"
        "import scripts.m15_gate3a.no_overlap;"
        "forbidden=[m for m in ('scripts.m15_gate3a.proof','scripts.m15_gate3a.coverage',"
        "'scripts.m15_gate3a.calendar_authority') if m in sys.modules];"
        "print(forbidden)"
    )
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        check=True,
        cwd=Path(__file__).resolve().parents[2],
    )
    assert completed.stdout.strip() == "[]"


def test_the_declaration_only_token_spelling_disclaims_the_byte_level() -> None:
    """Pinned by value, as D-11 names it: the spelling is what a reader sees."""
    assert frozenset({"DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL"}) == DECLARATION_ONLY_TOKENS
    for token in DECLARATION_ONLY_TOKENS:
        assert token.endswith(proof.DECLARATION_ONLY_TOKEN_SUFFIX)
        assert "PROVEN" not in token.removesuffix(proof.DECLARATION_ONLY_TOKEN_SUFFIX)


def test_byte_level_claim_token_spellings_are_pinned() -> None:
    assert BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN == "BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN"
    assert DERIVATION_IDENTITY_BOUND == "DERIVATION_IDENTITY_BOUND"
    assert BYTE_LEVEL_PROOF_PENDING == "BYTE_LEVEL_PROOF_PENDING"
    assert BYTE_LEVEL_PROOF_REFUTED == "BYTE_LEVEL_PROOF_REFUTED"


def test_token_vocabulary_is_closed_and_every_token_names_its_basis() -> None:
    assert set(TOKEN_EVIDENTIARY_BASIS) == set(TOKEN_VOCABULARY)
    assert DECLARATION_ONLY_TOKENS.isdisjoint(
        {BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN, DERIVATION_IDENTITY_BOUND}
    )
    assert BYTE_LEVEL_PROOF_PENDING in TOKEN_VOCABULARY
    assert BYTE_LEVEL_PROOF_REFUTED in TOKEN_VOCABULARY
    assert all(basis.strip() for basis in TOKEN_EVIDENTIARY_BASIS.values())


def test_default_byte_level_status_is_pending_because_nothing_has_been_measured() -> None:
    assert current_byte_level_proof_status() == BYTE_LEVEL_PROOF_PENDING
    with pytest.raises(ProofContractError, match="is not a byte-level claim token"):
        assert_byte_level_claim(BYTE_LEVEL_PROOF_PENDING)


def test_a_declaration_record_may_not_carry_a_byte_level_token() -> None:
    with pytest.raises(ProofPromotionError, match="may only carry a declaration-only token"):
        DeclarationRecord(
            pair="EUR_USD",
            artifact_id="candles_EUR_USD_M15_365d_BA_DESIGN.jsonl",
            declared_sha256=digest(1),
            declared_ts_min_utc=SLOTS[0],
            declared_ts_max_utc=SLOTS[-1],
            token=BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN,
        )


def test_declaration_records_are_refused_by_the_limb_evaluator() -> None:
    declarations = [
        DeclarationRecord(
            pair=pair,
            artifact_id=f"candles_{pair}_M15_365d_BA_DESIGN.jsonl",
            declared_sha256=digest(index + 1),
            declared_ts_min_utc=SLOTS[0],
            declared_ts_max_utc=SLOTS[-1],
        )
        for index, pair in enumerate(PAIRS_20)
    ]
    with pytest.raises(ProofPromotionError, match="is never promoted to a byte-level measurement"):
        evaluated_proof(producer_records=declarations)


# ===========================================================================
# B-7(a) — each epoch limb pinned in isolation
# ===========================================================================


def test_b7a_design_end_limb_raises_on_a_span_that_misses_the_dead_window() -> None:
    """``ts_max > DESIGN_END`` while the span clears the dead window entirely."""
    over = "2026-02-28T23:59:59.999999Z"
    assert to_utc(over) > DESIGN_END
    assert not is_dead_window_instant(over)
    with pytest.raises(NoOverlapError, match="exceeds the frozen design-epoch ceiling"):
        assert_per_file_bounds(
            design_roster(ts_min="2025-05-01T00:00:00Z", ts_max=over), role="design"
        )


def test_b7a_design_start_limb_raises_on_a_span_that_misses_the_dead_window() -> None:
    under = "2025-04-24T23:59:59Z"
    assert to_utc(under) < DESIGN_START
    assert not is_dead_window_instant(under)
    with pytest.raises(NoOverlapError, match="precedes the frozen design-epoch floor"):
        assert_per_file_bounds(
            design_roster(ts_min=under, ts_max="2025-12-31T23:59:59Z"), role="design"
        )


def test_b7a_forward_floor_limb_raises_on_a_span_that_misses_the_dead_window() -> None:
    lo, hi = "2026-02-01T00:00:00Z", "2026-02-10T00:00:00Z"
    assert to_utc(lo) < FORWARD_FLOOR
    assert not is_dead_window_instant(lo)
    assert not is_dead_window_instant(hi)
    with pytest.raises(NoOverlapError, match="precedes the frozen forward-epoch floor"):
        assert_forward_bounds(lo, hi)


def test_b7a_forward_epoch_evidence_cannot_pass_as_a_design_inventory() -> None:
    """The single property this gate exists to protect, pinned without alternation."""
    roster = forward_roster()
    assert not is_dead_window_instant(roster[0]["ts_min_utc"])
    assert not is_dead_window_instant(roster[0]["ts_max_utc"])
    with pytest.raises(NoOverlapError, match="exceeds the frozen design-epoch ceiling"):
        assert_per_file_bounds(roster, role="design", expected_count=20)


def test_forward_role_is_still_refused_outright() -> None:
    with pytest.raises(NoOverlapError, match="per-file proof refused"):
        assert_per_file_bounds(forward_roster(), role="forward")


# ===========================================================================
# BL-1 identity / roster guards must not regress
# ===========================================================================


def test_evidence_duplicate_one_record_object_at_two_indices_is_refused() -> None:
    record = design_roster()[0]
    with pytest.raises(NoOverlapError, match="the same record object appears at indices"):
        assert_per_file_bounds([record] * 20, role="design", expected_count=20)


def test_evidence_duplicate_shared_sha256_is_refused() -> None:
    roster = design_roster()
    roster[5]["sha256"] = roster[4]["sha256"]
    with pytest.raises(NoOverlapError, match=re.escape(f"sha256 {digest(5)} appears at records")):
        assert_per_file_bounds(roster, role="design")


def test_evidence_duplicate_shared_filename_is_refused() -> None:
    roster = design_roster()
    roster[5]["filename"] = roster[4]["filename"]
    with pytest.raises(
        NoOverlapError,
        match=re.escape(f"filename {roster[4]['filename']!r} appears at records"),
    ):
        assert_per_file_bounds(roster, role="design")


def test_alias_duplicate_pair_spelling_is_refused() -> None:
    roster = design_roster()
    roster[1]["pair"] = "eur/usd"
    with pytest.raises(NoOverlapError, match="roster does not match PAIRS_20"):
        assert_per_file_bounds(roster, role="design")


# ===========================================================================
# D-6 — the calendar authority interface
# ===========================================================================


def test_a_well_formed_approved_calendar_validates() -> None:
    calendar = valid_calendar()
    assert calendar.target_epoch == EPOCH
    assert calendar.pairs == PAIRS_20
    assert calendar.expected_slots("EUR_USD") == frozenset(to_utc(s) for s in SLOTS)
    assert calendar.approval_basis == calendar_authority.APPROVAL_BASIS_DECLARED


def test_missing_calendar_fails_closed() -> None:
    with pytest.raises(CalendarAbsentError, match="no calendar artifact supplied"):
        validate_calendar(None, expected_epoch=EPOCH)


def test_empty_calendar_fails_closed() -> None:
    with pytest.raises(CalendarAbsentError, match="calendar artifact is empty"):
        validate_calendar({}, expected_epoch=EPOCH)


@pytest.mark.parametrize("field", calendar_authority.REQUIRED_CALENDAR_FIELDS)
def test_a_calendar_missing_any_required_d6_field_fails_closed(field: str) -> None:
    with pytest.raises(CalendarMalformedError, match="missing the required D-6 field"):
        validate_calendar(calendar_artifact(**{field: _OMIT}), expected_epoch=EPOCH)


def test_a_calendar_field_that_states_nothing_is_ambiguous() -> None:
    with pytest.raises(CalendarAmbiguousError, match="is present but empty"):
        validate_calendar(calendar_artifact(dst_rule="   "), expected_epoch=EPOCH)


def test_unapproved_calendar_fails_closed() -> None:
    with pytest.raises(CalendarUnapprovedError, match="unapproved calendar fails closed"):
        validate_calendar(
            calendar_artifact(approval="PENDING_HUMAN_AND_CHATGPT_REVIEW"), expected_epoch=EPOCH
        )


def test_wrong_epoch_calendar_fails_closed() -> None:
    with pytest.raises(CalendarEpochMismatchError, match="never reused across epochs"):
        validate_calendar(calendar_artifact(target_epoch=OTHER_EPOCH), expected_epoch=EPOCH)


def test_two_slot_authorities_make_the_calendar_ambiguous() -> None:
    artifact = calendar_artifact(expected_m15_slot_rule=lambda pair: list(SLOTS))
    with pytest.raises(CalendarAmbiguousError, match="two authorities for the same quantity"):
        validate_calendar(artifact, expected_epoch=EPOCH)


def test_no_slot_authority_is_malformed() -> None:
    with pytest.raises(CalendarMalformedError, match="supplies neither"):
        validate_calendar(calendar_artifact(expected_m15_slots=_OMIT), expected_epoch=EPOCH)


def test_a_repeated_slot_makes_the_expected_count_ambiguous() -> None:
    slots = {pair: list(SLOTS) for pair in PAIRS_20}
    slots["EUR_USD"] = [*SLOTS, SLOTS[0]]
    with pytest.raises(CalendarAmbiguousError, match="leaves the expected count ambiguous"):
        validate_calendar(calendar_artifact(expected_m15_slots=slots), expected_epoch=EPOCH)


def test_a_slot_off_the_frozen_bucket_grid_is_malformed() -> None:
    slots = {pair: list(SLOTS) for pair in PAIRS_20}
    slots["EUR_USD"] = ["2025-05-01T00:07:00Z"]
    with pytest.raises(CalendarMalformedError, match="is not on the frozen"):
        validate_calendar(calendar_artifact(expected_m15_slots=slots), expected_epoch=EPOCH)


def test_a_calendar_expecting_a_dead_window_slot_is_malformed() -> None:
    slots = {pair: list(SLOTS) for pair in PAIRS_20}
    slots["EUR_USD"] = ["2026-03-15T00:00:00Z"]
    with pytest.raises(CalendarMalformedError, match="which no role may expect"):
        validate_calendar(calendar_artifact(expected_m15_slots=slots), expected_epoch=EPOCH)


def test_a_calendar_short_of_pairs_20_is_malformed() -> None:
    slots = {pair: list(SLOTS) for pair in PAIRS_20[:-1]}
    with pytest.raises(CalendarMalformedError, match="must have one before coverage"):
        validate_calendar(calendar_artifact(expected_m15_slots=slots), expected_epoch=EPOCH)


def test_an_alias_duplicate_pair_in_the_calendar_is_ambiguous() -> None:
    slots = {pair: list(SLOTS) for pair in PAIRS_20}
    slots["eur/usd"] = list(SLOTS)
    with pytest.raises(CalendarAmbiguousError, match="canonicalise to the same pair"):
        validate_calendar(calendar_artifact(expected_m15_slots=slots), expected_epoch=EPOCH)


def test_a_generating_rule_is_accepted_and_must_be_deterministic() -> None:
    artifact = calendar_artifact(
        expected_m15_slots=_OMIT, expected_m15_slot_rule=lambda pair: list(SLOTS)
    )
    calendar = validate_calendar(artifact, expected_epoch=EPOCH)
    assert calendar.expected_slots("GBP_JPY") == frozenset(to_utc(s) for s in SLOTS)


def test_a_non_deterministic_generating_rule_is_ambiguous() -> None:
    counter = {"n": 0}

    def rule(pair: str) -> list[str]:
        counter["n"] += 1
        return list(SLOTS) if counter["n"] % 2 else list(SLOTS[:2])

    artifact = calendar_artifact(expected_m15_slots=_OMIT, expected_m15_slot_rule=rule)
    with pytest.raises(CalendarAmbiguousError, match="is not deterministic for"):
        validate_calendar(artifact, expected_epoch=EPOCH)


def test_the_calendar_never_shrinks_to_what_was_observed() -> None:
    """D-6.1: absence of data is a coverage question, never a calendar answer."""
    calendar = valid_calendar()
    before = calendar.expected_slots("EUR_USD")
    empty = [
        pair_measurement(
            pair,
            slots=[],
            minute_accounting=accounting(absent=len(SLOTS) * MINUTES_PER_SLOT),
        )
        for pair in PAIRS_20
    ]
    with pytest.raises(CoverageSetMismatchError, match="must contain every expected slot"):
        assert_full_coverage(empty, calendar, expected_epoch=EPOCH)
    assert calendar.expected_slots("EUR_USD") == before


# ===========================================================================
# D-5 / D-10 — coverage is set equality, and insufficiency raises
# ===========================================================================


def test_full_set_equality_over_20_pairs_is_the_coverage_conjunction() -> None:
    result = assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH)
    assert isinstance(result, CoverageResult)
    assert result.satisfied
    assert result.pairs_measured == PAIRS_20
    assert len(result.per_pair) == len(PAIRS_20)
    assert all(p.expected_slot_count == len(SLOTS) for p in result.per_pair)


def test_a_single_instant_per_pair_never_earns_coverage() -> None:
    """The exact failure D-5 records: one point per pair, twenty pairs, full token."""
    thin = [pair_measurement(pair, slots=SLOTS[:1]) for pair in PAIRS_20]
    with pytest.raises(CoverageSetMismatchError, match="must contain every expected slot"):
        assert_full_coverage(thin, valid_calendar(), expected_epoch=EPOCH)


def test_a_missing_expected_slot_raises() -> None:
    measurements = full_measurements()
    measurements[3] = pair_measurement(PAIRS_20[3], slots=SLOTS[:-1])
    with pytest.raises(CoverageSetMismatchError, match="must contain every expected slot"):
        assert_full_coverage(measurements, valid_calendar(), expected_epoch=EPOCH)


def test_an_unexpected_extra_slot_raises() -> None:
    measurements = full_measurements()
    measurements[3] = pair_measurement(PAIRS_20[3], slots=[*SLOTS, "2025-05-01T00:45:00Z"])
    with pytest.raises(CoverageSetMismatchError, match="never absorbed into the expected set"):
        assert_full_coverage(measurements, valid_calendar(), expected_epoch=EPOCH)


def test_a_duplicate_certified_slot_raises() -> None:
    measurements = full_measurements()
    measurements[3] = pair_measurement(PAIRS_20[3], slots=[*SLOTS, SLOTS[0]])
    with pytest.raises(CoverageSetMismatchError, match="is certified more than once"):
        assert_full_coverage(measurements, valid_calendar(), expected_epoch=EPOCH)


def test_an_incomplete_pairs_20_roster_is_unsatisfied_not_satisfied() -> None:
    measurements = full_measurements()[:-1]
    with pytest.raises(
        CoverageMeasurementMissingError,
        match="a missing measurement is unsatisfied, never treated as satisfied",
    ):
        assert_full_coverage(measurements, valid_calendar(), expected_epoch=EPOCH)


def test_a_pair_measured_twice_after_canonicalisation_is_refused() -> None:
    measurements = full_measurements()
    measurements[1] = pair_measurement("eur/usd")
    with pytest.raises(CoverageEvidenceError, match="is measured twice in the coverage roster"):
        assert_full_coverage(measurements, valid_calendar(), expected_epoch=EPOCH)


def test_a_bucket_lost_to_a_rejected_minute_is_never_counted_as_covered() -> None:
    with pytest.raises(RejectedSlotCountedCoveredError, match="never counted as covered"):
        pair_measurement(
            "EUR_USD",
            rejected_slots=[SLOTS[1]],
            minute_accounting=accounting(rejected=1),
        )


def test_unusable_minutes_cannot_coexist_with_complete_coverage() -> None:
    measurements = full_measurements()
    measurements[2] = pair_measurement(
        PAIRS_20[2], minute_accounting=accounting(rejected=1, max_gap=1)
    )
    with pytest.raises(CoverageSetMismatchError, match="expected-but-unusable source"):
        assert_full_coverage(measurements, valid_calendar(), expected_epoch=EPOCH)


def test_counts_are_not_coverage_evidence() -> None:
    """`n_pairs == 20` and an ``expected_count`` are not a proof of anything (D-5.9)."""
    counts = [{"pair": pair, "expected_count": len(SLOTS)} for pair in PAIRS_20]
    with pytest.raises(CoverageEvidenceError, match="counts are not coverage evidence"):
        assert_full_coverage(counts, valid_calendar(), expected_epoch=EPOCH)


def test_coverage_requires_a_validated_calendar_authority() -> None:
    with pytest.raises(CoverageEvidenceError, match="an unvalidated calendar is not"):
        assert_full_coverage(full_measurements(), calendar_artifact(), expected_epoch=EPOCH)


def test_coverage_refuses_a_calendar_for_another_epoch() -> None:
    calendar = validate_calendar(
        calendar_artifact(target_epoch=OTHER_EPOCH), expected_epoch=OTHER_EPOCH
    )
    with pytest.raises(CoverageEvidenceError, match="but coverage is being"):
        assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)


def test_one_bar_object_cannot_certify_two_slots() -> None:
    bar = {"ts": SLOTS[0]}
    with pytest.raises(CoverageEvidenceError, match="one bar cannot certify two slots"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=[bar, bar, bar],
            minute_accounting=accounting(),
            rejected_slots=[],
        )


def test_bar_evidence_whose_length_disagrees_with_iteration_is_refused() -> None:
    class LyingBars(list):
        def __len__(self) -> int:
            return len(SLOTS)

    with pytest.raises(CoverageEvidenceError, match="bar evidence is not self-consistent"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=LyingBars(),
            minute_accounting=accounting(),
            rejected_slots=[],
        )


def test_a_certified_bar_off_the_bucket_grid_is_refused() -> None:
    with pytest.raises(CoverageEvidenceError, match="does not fall on the frozen"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=[{"ts": "2025-05-01T00:07:00Z"}],
            minute_accounting=accounting(slots=1),
            rejected_slots=[],
        )


def test_a_certified_bar_inside_the_dead_window_is_refused() -> None:
    with pytest.raises(CoverageEvidenceError, match="falls inside the consumed dead window"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=[{"ts": "2026-03-15T00:00:00Z"}],
            minute_accounting=accounting(slots=1),
            rejected_slots=[],
        )


# ---------------------------------------------------------------------------
# D-3 — the six-field minute accounting, consumed as workstream B emits it
# ---------------------------------------------------------------------------


def test_minute_accounting_key_set_is_the_six_field_schema() -> None:
    assert set(coverage.MINUTE_ACCOUNTING_FIELDS) == {
        "expected_source_minute_count",
        "observed_source_minute_count",
        "absent_source_minute_count",
        "rejected_source_minute_count",
        "usable_source_minute_count",
        "max_unavailable_gap_minutes",
    }


def test_absent_minute_accounting_fails_closed() -> None:
    with pytest.raises(MinuteAccountingError, match="minute_accounting absent"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=bars(SLOTS),
            minute_accounting=None,
            rejected_slots=[],
        )


def test_the_minute_accounting_identity_is_enforced() -> None:
    broken = accounting()
    broken["usable_source_minute_count"] -= 1
    with pytest.raises(MinuteAccountingError, match="minute accounting identity violated"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=bars(SLOTS),
            minute_accounting=broken,
            rejected_slots=[],
        )


def test_a_legacy_gap_report_key_is_refused_by_the_closed_schema() -> None:
    legacy = accounting()
    legacy["missing_minute_count"] = 0
    with pytest.raises(MinuteAccountingError, match="the six-field schema is closed"):
        measure_pair_coverage(
            pair="EUR_USD",
            certified_bars=bars(SLOTS),
            minute_accounting=legacy,
            rejected_slots=[],
        )


# ===========================================================================
# D-11 — the four limbs
# ===========================================================================


def test_all_four_limbs_satisfied_mints_the_byte_level_claim() -> None:
    result = evaluated_proof()
    assert result.token == BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN
    assert result.derivation_token == DERIVATION_IDENTITY_BOUND
    assert result.limbs_evaluated == frozenset(FOUR_LIMBS)
    assert result.pairs_measured == PAIRS_20
    assert result.evidentiary_basis == TOKEN_EVIDENTIARY_BASIS[result.token]
    assert set(result.aggregate_assertions) == set(AGGREGATE_ASSERTIONS)
    assert all(result.aggregate_assertions.values())


def test_omitting_a_limb_argument_entirely_is_a_type_error() -> None:
    # The signature is the guard here, so `TypeError` is the only type available
    # — but it is named, so an unrelated TypeError could not satisfy this.
    with pytest.raises(TypeError, match="coverage_result"):
        evaluate_four_limbs(  # type: ignore[call-arg]
            producer_records=producer_set(),
            verifier_records=verifier_set(),
            derivation_bindings=binding_set(),
            inventory_digest=digest(4242),
        )


def test_the_cv_limb_cannot_be_omitted() -> None:
    with pytest.raises(ProofLimbAbsentError, match="the CV limb is absent"):
        evaluated_proof(coverage_result=None)


def test_the_cv_limb_refuses_a_hand_built_unsatisfied_coverage_result() -> None:
    """The conjunction guard is reachable from a caller, not only from `coverage`.

    ``CoverageResult`` is a public frozen dataclass, so nothing stops a caller
    constructing one that ``coverage`` would never have returned and handing it
    to the proof. Its source carries
    ``# pragma: no cover - coverage raises first``, which is a claim this test
    contradicts: the guard fires, so the pragma sits on a reachable guard
    (audit §9 AP-7, reported to the source workstream).
    """
    hand_built = CoverageResult(
        calendar_digest="0" * 64,
        calendar_epoch=EPOCH,
        per_pair=(),
        pairs_measured=(),
    )
    assert hand_built.satisfied is False
    with pytest.raises(
        ProofLimbUnsatisfiedError, match="the 20-pair coverage conjunction is not held"
    ):
        evaluated_proof(coverage_result=hand_built)


def test_the_db_limb_cannot_be_omitted() -> None:
    with pytest.raises(ProofLimbAbsentError, match="not bound to any named derivation"):
        evaluated_proof(derivation_bindings=None)


def test_the_producer_measurement_set_cannot_be_omitted() -> None:
    with pytest.raises(ProofLimbAbsentError, match="no producer measurement records supplied"):
        evaluated_proof(producer_records=None)


def test_the_verifier_measurement_set_cannot_be_omitted() -> None:
    with pytest.raises(ProofLimbAbsentError, match="no verifier measurement records supplied"):
        evaluated_proof(verifier_records=None)


def test_a_pair_without_an_independent_verifier_is_unattested() -> None:
    with pytest.raises(ProofLimbAbsentError, match="attestation is by the verifier"):
        evaluated_proof(verifier_records=verifier_set()[:-1])


# --- BI ---------------------------------------------------------------------


def test_bi_two_pairs_resolving_to_the_same_object_are_refused() -> None:
    producers = producer_set()
    producers[5] = measurement(PAIRS_20[5], 4)
    verifiers = verifier_set()
    verifiers[5] = measurement(PAIRS_20[5], 4, role=ROLE_VERIFIER)
    with pytest.raises(ProofLimbUnsatisfiedError, match="resolve to the same object"):
        evaluated_proof(producer_records=producers, verifier_records=verifiers)


def test_bi_two_pairs_sharing_an_artifact_identifier_are_refused() -> None:
    shared = "candles_SHARED_M15_365d_BA_DESIGN.jsonl"
    producers = producer_set()
    producers[5] = measurement(PAIRS_20[5], 5, artifact_id=shared)
    producers[6] = measurement(PAIRS_20[6], 6, artifact_id=shared)
    verifiers = verifier_set()
    verifiers[5] = measurement(PAIRS_20[5], 5, role=ROLE_VERIFIER, artifact_id=shared)
    verifiers[6] = measurement(PAIRS_20[6], 6, role=ROLE_VERIFIER, artifact_id=shared)
    with pytest.raises(ProofLimbUnsatisfiedError, match="twenty files means twenty identities"):
        evaluated_proof(producer_records=producers, verifier_records=verifiers)


def test_bi_identity_is_never_a_path() -> None:
    with pytest.raises(ProofContractError, match="looks like a path"):
        measurement("EUR_USD", 0, artifact_id="data/m15/candles_EUR_USD.jsonl")


def test_bi_a_digest_not_reproduced_on_re_read_is_refused() -> None:
    with pytest.raises(ProofContractError, match="does not reproduce the first-pass digest"):
        measurement("EUR_USD", 0, re_read_sha256=digest(777))


def test_bi_row_count_must_be_what_the_full_scan_counted() -> None:
    with pytest.raises(ProofContractError, match="must be what the full scan counted"):
        measurement("EUR_USD", 0, bars_scanned=1)


# --- TC ---------------------------------------------------------------------


def test_tc_a_measured_span_past_design_end_is_refused() -> None:
    producers = producer_set()
    producers[2] = measurement(PAIRS_20[2], 2, measured_ts_max="2026-04-30T00:00:00Z")
    verifiers = verifier_set()
    verifiers[2] = measurement(
        PAIRS_20[2], 2, role=ROLE_VERIFIER, measured_ts_max="2026-04-30T00:00:00Z"
    )
    with pytest.raises(ProofLimbUnsatisfiedError, match="not inside the frozen design epoch"):
        evaluated_proof(producer_records=producers, verifier_records=verifiers)


def test_tc_dead_window_bars_must_be_zero_by_full_scan() -> None:
    producers = producer_set()
    producers[2] = measurement(
        PAIRS_20[2],
        2,
        dead_window_bars_by_bucket_start=1,
        dead_window_bars_by_contributing_minute=1,
    )
    verifiers = verifier_set()
    verifiers[2] = measurement(
        PAIRS_20[2],
        2,
        role=ROLE_VERIFIER,
        dead_window_bars_by_bucket_start=1,
        dead_window_bars_by_contributing_minute=1,
    )
    with pytest.raises(ProofLimbUnsatisfiedError, match="must be zero by full scan"):
        evaluated_proof(producer_records=producers, verifier_records=verifiers)


def test_tc_the_two_dead_window_definitions_diverging_is_terminal() -> None:
    """D-8: they coincide under a correct implementation and diverge when it is wrong."""
    producers = producer_set()
    producers[2] = measurement(
        PAIRS_20[2],
        2,
        dead_window_bars_by_bucket_start=0,
        dead_window_bars_by_contributing_minute=3,
    )
    verifiers = verifier_set()
    verifiers[2] = measurement(
        PAIRS_20[2],
        2,
        role=ROLE_VERIFIER,
        dead_window_bars_by_bucket_start=0,
        dead_window_bars_by_contributing_minute=3,
    )
    with pytest.raises(ProofDisagreementError, match="the bucketing is wrong"):
        evaluated_proof(producer_records=producers, verifier_records=verifiers)


def test_tc_endpoints_never_substitute_for_the_interior_scan() -> None:
    producers = producer_set()
    producers[2] = measurement(PAIRS_20[2], 2, out_of_design_range_bar_count=1)
    verifiers = verifier_set()
    verifiers[2] = measurement(PAIRS_20[2], 2, role=ROLE_VERIFIER, out_of_design_range_bar_count=1)
    with pytest.raises(ProofLimbUnsatisfiedError, match="the interior is where a bucketing fault"):
        evaluated_proof(producer_records=producers, verifier_records=verifiers)


# --- DB ---------------------------------------------------------------------


def test_db_bytes_that_do_not_re_derive_identically_are_refused() -> None:
    bindings = binding_set()
    bindings[4] = DerivationBinding(
        pair=PAIRS_20[4],
        script_name="scripts/m15_gate3a_continuation/derive_design_m15.py",
        git_sha="0" * 40,
        config_hash=digest(999),
        source_identity="RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1",
        re_derivation_sha256=digest(31337),
    )
    with pytest.raises(ProofLimbUnsatisfiedError, match="not byte-reproducible from"):
        evaluated_proof(derivation_bindings=bindings)


def test_db_every_pair_must_name_the_script_that_produced_it() -> None:
    with pytest.raises(ProofLimbUnsatisfiedError, match="no derivation binding for"):
        evaluated_proof(derivation_bindings=binding_set()[:-1])


def test_db_an_unnamed_derivation_is_refused() -> None:
    with pytest.raises(ProofContractError, match="must be a non-empty string; the bytes"):
        DerivationBinding(
            pair="EUR_USD",
            script_name="  ",
            git_sha="0" * 40,
            config_hash=digest(999),
            source_identity="RESEARCH_FROZEN_HOLDOUT_EPOCH_365D_BA_V1",
            re_derivation_sha256=digest(1),
        )


# ===========================================================================
# §12.12 — co-measurement, independent verification, consumer re-verification
# ===========================================================================


def test_a_digest_and_span_from_different_reads_are_refused() -> None:
    with pytest.raises(ProofCoMeasurementError, match="different byte-stream passes"):
        measurement("EUR_USD", 0, span_provenance=provenance("second-read-EUR_USD", index=2))


def test_a_verifier_replaying_the_producers_read_is_not_independent() -> None:
    shared = provenance("one-and-only-read")
    producer = measurement(
        "EUR_USD",
        0,
        digest_provenance=shared,
        size_provenance=shared,
        span_provenance=shared,
        scan_provenance=shared,
    )
    verifier = measurement(
        "EUR_USD",
        0,
        role=ROLE_VERIFIER,
        digest_provenance=shared,
        size_provenance=shared,
        span_provenance=shared,
        scan_provenance=shared,
    )
    with pytest.raises(ProofContractError, match="rather than replaying the producer's read"):
        assert_records_agree(producer, verifier)


def test_a_digest_disagreement_between_producer_and_verifier_is_terminal() -> None:
    producer = measurement("EUR_USD", 0)
    verifier = measurement(
        "EUR_USD", 0, role=ROLE_VERIFIER, sha256=digest(9), re_read_sha256=digest(9)
    )
    with pytest.raises(ProofDisagreementError, match="did not see the same artifact"):
        assert_records_agree(producer, verifier)


def test_a_size_mismatch_under_a_matching_digest_is_the_more_alarming_case() -> None:
    producer = measurement("EUR_USD", 0)
    verifier = measurement("EUR_USD", 0, role=ROLE_VERIFIER, size_bytes=1)
    with pytest.raises(
        ProofDisagreementError, match="identical bytes yielding different measurements"
    ) as excinfo:
        assert_records_agree(producer, verifier)
    assert "size_bytes" in str(excinfo.value)


def test_a_measured_span_mismatch_under_a_matching_digest_is_terminal() -> None:
    producer = measurement("EUR_USD", 0)
    verifier = measurement("EUR_USD", 0, role=ROLE_VERIFIER, measured_ts_max="2026-01-31T23:45:00Z")
    with pytest.raises(
        ProofDisagreementError, match="identical bytes yielding different measurements"
    ) as excinfo:
        assert_records_agree(producer, verifier)
    assert "measured_ts_max" in str(excinfo.value)


def test_a_missing_verifier_record_is_never_treated_as_agreement() -> None:
    with pytest.raises(ProofLimbAbsentError, match="a producer measurement alone is never"):
        assert_records_agree(measurement("EUR_USD", 0), None)


def test_w1_hashing_under_the_published_name_is_refused() -> None:
    with pytest.raises(ProofContractError, match="then renaming atomically"):
        measurement("EUR_USD", 0, staged_artifact_id="candles_EUR_USD_M15_365d_BA_DESIGN.jsonl")


def test_w2_the_inventorys_own_digest_is_recorded_in_the_proof() -> None:
    assert evaluated_proof().inventory_digest == digest(4242)
    with pytest.raises(ProofContractError, match="inventory_digest is not a well-formed"):
        evaluated_proof(inventory_digest="not-a-digest")


def test_w3_a_proof_that_was_not_re_verified_is_not_usable() -> None:
    result = evaluated_proof()
    with pytest.raises(ProofNotUsableError, match="no consumer re-verification supplied"):
        open_for_consumption(result, consumer_rechecks=None)


def test_w3_skipping_the_recheck_is_not_the_same_as_passing_it() -> None:
    result = evaluated_proof()
    with pytest.raises(ProofNotUsableError, match="skipping the re-check is not the same"):
        open_for_consumption(result, consumer_rechecks=[])


def test_w3_consumer_rechecks_are_keyword_only_with_no_default() -> None:
    result = evaluated_proof()
    with pytest.raises(TypeError, match="consumer_rechecks"):
        open_for_consumption(result)  # type: ignore[call-arg]


def test_w3_a_partial_recheck_leaves_artifacts_unusable() -> None:
    result = evaluated_proof()
    with pytest.raises(ProofNotUsableError, match="no consumer re-verification for"):
        open_for_consumption(result, consumer_rechecks=recheck_set()[:-1])


def test_w3_a_digest_change_between_proof_and_consumption_is_terminal() -> None:
    result = evaluated_proof()
    rechecks = recheck_set()
    rechecks[7] = ConsumerRecheck(
        pair=PAIRS_20[7],
        artifact_id=f"candles_{PAIRS_20[7]}_M15_365d_BA_DESIGN.jsonl",
        sha256=digest(31337),
        size_bytes=4096 + 7,
        provenance=provenance("consumer-read-late", index=9),
    )
    with pytest.raises(ProofDisagreementError, match="digest changed between the proof"):
        open_for_consumption(result, consumer_rechecks=rechecks)


def test_w3_a_size_change_between_proof_and_consumption_is_terminal() -> None:
    result = evaluated_proof()
    rechecks = recheck_set()
    rechecks[7] = ConsumerRecheck(
        pair=PAIRS_20[7],
        artifact_id=f"candles_{PAIRS_20[7]}_M15_365d_BA_DESIGN.jsonl",
        sha256=digest(8),
        size_bytes=1,
        provenance=provenance("consumer-read-late", index=9),
    )
    with pytest.raises(ProofDisagreementError, match="byte size changed between the proof"):
        open_for_consumption(result, consumer_rechecks=rechecks)


def test_w3_a_fully_re_verified_proof_is_usable() -> None:
    approval = open_for_consumption(evaluated_proof(), consumer_rechecks=recheck_set())
    assert approval.token == BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN
    assert approval.pairs_reverified == PAIRS_20


# ===========================================================================
# D-4 — hashing is a byte read
# ===========================================================================


def test_the_proof_subject_is_the_derived_artifact_never_the_raw_source() -> None:
    with pytest.raises(RawSourceRehashForbiddenError, match="is not the derived M15 artifact"):
        measurement("EUR_USD", 0, subject="RAW_SOURCE_M1_BYTES")


def test_a_raw_source_rehash_request_is_refused_outright() -> None:
    with pytest.raises(RawSourceRehashForbiddenError, match="refusing to hash"):
        refuse_raw_source_rehash("RAW_SOURCE_M1_BYTES")
    refuse_raw_source_rehash(SUBJECT_DERIVED_M15_ARTIFACT)


# ===========================================================================
# D-8 / §12.15 — aggregate assertions are measured conjunctions
# ===========================================================================


def test_a_missing_measurement_makes_an_aggregate_assertion_unsatisfied() -> None:
    partial = {pair: True for pair in PAIRS_20[:-1]}
    with pytest.raises(AggregateAssertionUnsatisfiedError, match="never vacuously true"):
        assert_measured_conjunction("dead_window_bars_present_is_zero", partial)


def test_a_none_measurement_is_unsatisfied_too() -> None:
    measured: dict[str, Any] = {pair: True for pair in PAIRS_20}
    measured[PAIRS_20[3]] = None
    with pytest.raises(AggregateAssertionUnsatisfiedError, match="never vacuously true"):
        assert_measured_conjunction("dead_window_bars_present_is_zero", measured)


def test_a_declared_count_never_establishes_an_aggregate_assertion() -> None:
    with pytest.raises(AggregateAssertionUnsatisfiedError, match="a declared count is not a"):
        assert_measured_conjunction("dead_window_bars_present_is_zero", 0)


def test_a_false_measurement_breaks_the_conjunction() -> None:
    measured = {pair: True for pair in PAIRS_20}
    measured[PAIRS_20[9]] = False
    with pytest.raises(AggregateAssertionUnsatisfiedError, match="does not hold"):
        assert_measured_conjunction("dead_window_bars_present_is_zero", measured)


def test_the_full_measured_conjunction_holds() -> None:
    assert assert_measured_conjunction(
        "dead_window_bars_present_is_zero", {pair: True for pair in PAIRS_20}
    )


def test_an_unknown_aggregate_assertion_is_refused() -> None:
    with pytest.raises(AggregateAssertionUnsatisfiedError, match="is not one of the committed"):
        assert_measured_conjunction("looks_fine_to_me", {pair: True for pair in PAIRS_20})


# ===========================================================================
# No tolerance parameter, no report-only mode (D-2.1, D-2.2, D-10)
# ===========================================================================


@pytest.mark.parametrize(
    "entry_point",
    [
        assert_full_coverage,
        measure_pair_coverage,
        validate_calendar,
        evaluate_four_limbs,
        open_for_consumption,
        assert_measured_conjunction,
    ],
)
def test_no_entry_point_exposes_a_numeric_or_boolean_switch(entry_point: Any) -> None:
    """A tolerance, a threshold, or a report-only flag would all show up here."""
    for parameter in inspect.signature(entry_point).parameters.values():
        assert not isinstance(parameter.default, (bool, int, float)), parameter.name


def test_insufficient_coverage_raises_rather_than_returning_a_flag() -> None:
    """D-10 / NR-J: recording a coverage flag never permits continuation."""
    thin = [pair_measurement(pair, slots=SLOTS[:1]) for pair in PAIRS_20]
    calendar = valid_calendar()
    with pytest.raises(CoverageSetMismatchError):
        assert_full_coverage(thin, calendar, expected_epoch=EPOCH)
    # And the satisfied path is genuinely reachable, so the raise is not vacuous.
    assert assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH).satisfied
