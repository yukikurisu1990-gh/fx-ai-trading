"""Round-5 internal-audit findings: the fixes, and the pins they were missing.

Six independent audit roles ran against this branch. Four of them defeated a
defence the previous head reported closed, and between them they also named
guards whose *source* was correct but which no test pinned — so a mutation
removing the guard left the suite green.

Both kinds land here. Every refusal below is paired with a negative control, so
each test discriminates rather than merely refusing everything, and each
``match=`` string identifies one guard.
"""

from __future__ import annotations

import base64
import copy
import gc
import json
import pickle
import struct
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from scripts.m15_gate3a import sealing
from scripts.m15_gate3a.artifacts import (
    ArtifactScrubError,
    _fold_hazards,
    artifact_schema,
    scan_gate3a,
    write_metadata_artifact,
)
from scripts.m15_gate3a.calendar_authority import calendar_content_digest
from scripts.m15_gate3a.coverage import (
    MINUTE_ACCOUNTING_FIELDS,
    CoverageResult,
    PairCoverage,
)
from scripts.m15_gate3a.guards import (
    FORBIDDEN_STATUSES,
    UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS,
    RealDataRefusedError,
    refuse_real_path,
)
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_gate3a.path_authority import PathAuthorityError, resolve_candidate
from scripts.m15_gate3a.proof import (
    AggregateAssertionUnsatisfiedError,
    ProofContractError,
    _pin_instant,
    assert_measured_conjunction,
)

BS = chr(92)
ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts" / "m15_gate3a"


class Masked(str):
    """A ``str`` whose rendering differs from its character data."""

    _shows: str

    def __new__(cls, real: str, shows: str) -> Masked:
        obj = super().__new__(cls, real)
        obj._shows = shows
        return obj

    def __str__(self) -> str:
        return self._shows

    def __repr__(self) -> str:
        return repr(self._shows)


class LyingInstant(datetime):
    """A ``datetime`` that answers comparisons and component reads for itself."""

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    def __hash__(self) -> int:
        return 0

    @property
    def year(self) -> int:
        return 2031


def _entry() -> PairCoverage:
    return PairCoverage(
        pair="EUR_USD",
        expected_slot_count=1,
        certified_slot_count=1,
        certified_slot_min=datetime(2025, 5, 1, tzinfo=UTC),
        certified_slot_max=datetime(2025, 5, 1, tzinfo=UTC),
    )


# ---------------------------------------------------------------------------
# FB-7 — the fold hazard is the deletion, not the codepoint's category
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "codepoint",
    [0x07C0, 0x2223, 0x2227, 0x2203, 0x25CB, 0x3007, 0x00D7, 0x0661, 0x1F170],
)
def test_fb7_a_non_letter_homoglyph_cannot_hide_a_label(codepoint: int) -> None:
    """The class the ``category().startswith("L")`` rule could not see.

    Nineteen of twenty-four labels fell to one substitution from this class and
    the artifact wrote. None of these codepoints is a letter, so none was folded
    and none was reported — while ``_dense`` deleted every one of them.
    """
    char = chr(codepoint)
    defeated: list[str] = []
    examined = 0
    for label in sorted(FORBIDDEN_STATUSES | UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS):
        # LAUNDERING positions only: the substituted character must sit between
        # two ASCII alphanumerics. Elsewhere the deletion does not join two runs
        # — at a label's edge, or beside an underscore, the dense form loses a
        # character the label needs and the result reads as a visible
        # misspelling (`BYTE_ODMISSIBLE`), not as the claim.
        for index in range(1, len(label) - 1):
            if not (label[index].isascii() and label[index].isalpha()):
                continue
            before, after = label[index - 1], label[index + 1]
            if not (before.isascii() and before.isalnum()):
                continue
            if not (after.isascii() and after.isalnum()):
                continue
            examined += 1
            candidate = label[:index] + char + label[index + 1 :]
            if scan_gate3a({"result": candidate}) == [] or not _fold_hazards(candidate):
                defeated.append(candidate)
    assert examined > 150, "the sweep must actually have run"
    assert defeated == [], f"U+{codepoint:04X} hid {len(defeated)} label(s)"


def test_fb7_the_join_rule_needs_the_whole_separator_to_be_invisible() -> None:
    """Negative control, and the exact boundary of the rule.

    A separator a reader can see is not laundering. Only when *every* character
    between two alphanumerics is non-ASCII do the reader and the scanner
    disagree, and only then is anything reported.
    """
    assert scan_gate3a({"note": "1.5 → higher"}) == []
    assert scan_gate3a({"note": "1.5→higher"}) == ["gate3a_non_ascii_join:note:2192"]


def test_fb7_a_metric_root_hidden_by_the_same_fold_is_reported_in_a_key() -> None:
    """One fold defect propagated through three rules; the key side is one."""
    findings = scan_gate3a({"max_drawd߀wn_pct": 3.21})
    assert "gate3a_non_ascii_join_in_key:max_drawd߀wn_pct:07C0" in findings
    assert scan_gate3a({"note": "ordinary text"}) == []


# ---------------------------------------------------------------------------
# FR-15 — the negator is a word, not a suffix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "casino PRODUCTION_READY",
        "kimono BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN",
        "whenever PRODUCTION_READY",
        "UNBLOCKED_PRODUCTION_READY",
        "Piano. PRODUCTION_READY",
    ],
)
def test_fr15_a_word_merely_ending_in_a_negator_does_not_launder_a_claim(text: str) -> None:
    """``dense[:start].endswith(negator)`` had no word boundaries at all.

    ``casino`` ends in ``NO``; ``UNBLOCKED`` ends in ``BLOCKED``; ``whenever``
    ends in ``NEVER``. Each of these wrote a forbidden claim to disk through the
    real writer with a clean scan.
    """
    assert scan_gate3a({"note": text}) != []


@pytest.mark.parametrize(
    "text",
    [
        "NOT_PRODUCTION_READY",
        "NOT_PASS",
        "no PASS is claimed",
        "this gate is not production ready",
        "never MEETS the pre-registered criteria",
    ],
)
def test_fr15_an_honest_denial_is_still_writable(text: str) -> None:
    """The other half of FR-15, which the fix must not cost."""
    assert scan_gate3a({"note": text}) == []


# ---------------------------------------------------------------------------
# FR-3 — minting verifies its caller
# ---------------------------------------------------------------------------


def test_fr3_register_minted_refuses_a_caller_that_is_not_the_records_post_init() -> None:
    """``register_minted`` is exported, so the FB-1 forgery was one public call.

    An audit reached a satisfied four-limb proof over a calendar that never
    existed using only ``object.__new__``, ``object.__setattr__`` and this
    function — no underscore-prefixed name anywhere.
    """
    forged = object.__new__(CoverageResult)
    for name, value in (
        ("calendar_digest", "NO_CALENDAR_EVER_EXISTED"),
        ("calendar_epoch", "NO_EPOCH_WAS_EVER_APPROVED"),
        ("per_pair", ()),
        ("_construction_token", None),
    ):
        object.__setattr__(forged, name, value)
    with pytest.raises(sealing.SealedRecordError, match="only from its own"):
        sealing.register_minted(forged)
    assert sealing.is_minted(forged) is False


def test_fr3_a_genuinely_constructed_record_is_still_minted() -> None:
    """Negative control: the frame check must not break real construction."""
    assert sealing.is_minted(_entry()) is True


# ---------------------------------------------------------------------------
# FB-6 — `__getstate__` is the family member a slots dataclass writes for you
# ---------------------------------------------------------------------------


def test_fb6_getstate_is_refused_on_a_sealed_record() -> None:
    """Refusing copy/deepcopy/reduce left the generated one open.

    ``ProofResult().__getstate__()`` returned the withheld twenty-pair identity
    map as element 9 — two plain stdlib calls, no hostile object, no private
    name.
    """
    entry = _entry()
    with pytest.raises(Exception, match="may not be copied"):
        entry.__getstate__()
    for protocol in (copy.copy, copy.deepcopy, pickle.dumps):
        with pytest.raises(Exception, match="may not be copied"):
            protocol(entry)
    # Negative control: the record itself is still readable and still a record.
    assert entry.pair == "EUR_USD"
    assert gc.get_referents(entry) is not None


# ---------------------------------------------------------------------------
# FB-3(a) — the token bound and the aggregate budget
# ---------------------------------------------------------------------------


def _prices(count: int) -> bytes:
    return b"".join(struct.pack("<d", 1.10000 + index * 1e-5) for index in range(count))


def test_fb3a_a_hex_payload_chunked_below_the_leaf_bound_is_refused() -> None:
    """412 KB of byte-exact float64 prices, plain JSON, previously clean.

    ``[0-9a-fA-F]{64,}`` excised any long hex run before the density limb
    counted, so the third of three "independent" limbs was blind to it.
    """
    records = [{"sha256": _prices(28).hex(), "pair": _prices(28).hex()} for _ in range(20)]
    findings = scan_gate3a(
        {"artifact": "design_m15_inventory", "files": records},
        artifact="design_m15_inventory.json",
    )
    assert any(f.startswith("gate3a_oversize_text_token") for f in findings), findings


def test_fb3a_a_letters_only_payload_is_refused_by_the_token_bound() -> None:
    """The adjacent encoding the narrowed hex rule alone did not close.

    Base32 restricted to letters has zero digit runs, so the density limb never
    applies. What separates description from payload is the token: prose has
    words, an encoded dataset has one enormous run.
    """
    blob = base64.b32encode(_prices(60)).decode().rstrip("=")[:499]
    records = [{"pair": blob} for _ in range(20)]
    findings = scan_gate3a(
        {"artifact": "design_m15_inventory", "files": records},
        artifact="design_m15_inventory.json",
    )
    assert any(f.startswith("gate3a_oversize_text_token") for f in findings), findings


def test_fb3a_a_committed_width_digest_and_ordinary_prose_are_still_writable() -> None:
    """Negative control: the bound is the width the committed schema declares."""
    record = {"sha256": "a" * 64, "pair": "EUR_USD", "filename": "candles_EUR_USD_M15.jsonl"}
    findings = scan_gate3a(
        {"artifact": "design_m15_inventory", "files": [record]},
        artifact="design_m15_inventory.json",
    )
    assert findings == []


def test_fb3a_the_aggregate_text_budget_is_enforced_over_the_whole_document() -> None:
    """The per-leaf limbs had no aggregate; the leaf budget counts leaves."""
    findings = scan_gate3a({"artifact": "scrub_report", "note": ["word " * 60] * 40})
    assert any(f.startswith("gate3a_oversize_text_total") for f in findings), findings


def test_fb3a_every_committed_artifact_is_inside_the_aggregate_budget() -> None:
    """The floor under the budget: it refuses no committed content."""
    paths = sorted(ARTIFACTS.glob("*.json"))
    assert len(paths) >= 8
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert scan_gate3a(payload, artifact=path.name) == [], path.name


# ---------------------------------------------------------------------------
# FB-4 — the namespace family
# ---------------------------------------------------------------------------


def _namespace_spellings(tail: str) -> dict[str, str]:
    guid = "9e556d10-0000-0000-0000-000000000000"
    return {
        "admin_share": BS * 2 + "localhost" + BS + "C$" + tail,
        "extended_unc": BS * 2 + "?" + BS + "UNC" + BS + "localhost" + BS + "C$" + tail,
        "extended_unc_lower": BS * 2 + "?" + BS + "unc" + BS + "localhost" + BS + "C$" + tail,
        "globalroot": BS * 2 + "?" + BS + "GLOBALROOT" + BS + "Device" + BS + "HD4" + tail,
        "volume_guid": BS * 2 + "?" + BS + "Volume{" + guid + "}" + tail,
    }


@pytest.mark.parametrize("spelling", sorted(_namespace_spellings("")))
def test_fb4_a_namespace_spelling_is_refused_whatever_is_on_disk(spelling: str) -> None:
    """These alias a protected root, and ``resolve()`` does NOT canonicalise them.

    With the root absent — which ``.gitignore`` guarantees for ``models/`` in
    every fresh clone — the identity limb had nothing to compare, the name limb
    never saw the protected name, and an audit wrote a real file into the real
    tree through the real writer.
    """
    tail = BS + "never_created" + BS + "models"
    candidate = _namespace_spellings(tail)[spelling]
    with pytest.raises(PathAuthorityError, match="gate-3a addresses only ordinary"):
        resolve_candidate(candidate)
    with pytest.raises(RealDataRefusedError, match="gate-3a addresses only ordinary"):
        refuse_real_path(candidate)


def test_fb4_an_ordinary_local_path_is_untouched_by_the_namespace_rule(tmp_path: Path) -> None:
    """Negative control: the rule refuses spellings, not directories."""
    refuse_real_path(tmp_path / "out" / "scrub_report.json")
    assert resolve_candidate(str(tmp_path / "out")).is_absolute()


def test_fb4_a_relative_path_still_reports_the_working_directory_reason() -> None:
    """Ordering control: "no drive letter" is true of every relative path.

    If the namespace rule ran first it would answer for the relative-spelling
    refusal and say nothing, so it is placed after it deliberately.
    """
    with pytest.raises(PathAuthorityError, match="containment would depend on the working"):
        resolve_candidate("out.json")


# ---------------------------------------------------------------------------
# The unpinned comparisons the audits found
# ---------------------------------------------------------------------------


def test_the_fr4_span_endpoints_are_read_as_plain_datetime_data() -> None:
    """A ``datetime`` subclass answered the FR-4 binding for itself.

    Reading through the base descriptors means the value compared is the value
    the object holds, whatever the subclass overrides.
    """
    liar = LyingInstant(2025, 5, 1, tzinfo=UTC)
    pinned = _pin_instant(liar, what="x")
    assert pinned.year == 2025
    assert type(pinned) is datetime
    with pytest.raises(ProofContractError, match="must be UTC-aware"):
        _pin_instant(datetime(2025, 5, 1), what="x")
    with pytest.raises(ProofContractError, match="must be a datetime"):
        _pin_instant("2025-05-01T00:00:00Z", what="x")


def test_the_per_pair_conjunction_reads_its_mapping_keys_as_character_data() -> None:
    """D-8 was satisfied by twenty keys whose real data was ``PAIR_NEVER_...``.

    The name argument was pinned; the keys the lookup uses were not.
    """
    masked = {Masked(f"PAIR_NEVER_MEASURED_{i}", pair): True for i, pair in enumerate(PAIRS_20)}
    with pytest.raises(AggregateAssertionUnsatisfiedError, match="has no measurement for"):
        assert_measured_conjunction("file_count_is_20", masked)


def test_the_per_pair_conjunction_still_accepts_an_honest_mapping() -> None:
    """Negative control for the key pinning."""
    assert assert_measured_conjunction("file_count_is_20", dict.fromkeys(PAIRS_20, True))


def test_the_path_authority_reads_a_str_subclass_as_character_data(tmp_path: Path) -> None:
    """``text = str.__str__(path)`` is load-bearing and was pinned by nothing.

    ``normalise_spelling`` itself calls ``str(path)``, so with the pin removed
    the guard judges the subclass's rendering and a protected path is allowed.
    """
    protected = Path.cwd() / "docs" / "governance"
    masked = Masked(str(protected), str(tmp_path / "harmless.json"))
    with pytest.raises(RealDataRefusedError, match="refused real/protected path"):
        refuse_real_path(masked)
    honest = str(tmp_path / "ok.json")
    refuse_real_path(Masked(honest, honest))


def test_the_calendar_content_digest_is_injective_across_field_boundaries() -> None:
    """``name=value`` joined by newlines was an ambiguous encoding.

    Two calendars whose market-hours declarations differed field-for-field
    digested identically, from plain JSON, and both passed provenance.
    """
    base: dict[str, Any] = {
        "authority": "A",
        "authority_version": "1",
        "timezone": "UTC",
        "market_open_close_rule": "R",
        "dst_rule": "D",
        "exceptional_closure_handling": "E",
        "target_epoch": "EP",
        "committed_artifact": "artifacts/x.json",
        "committed_revision": "abc",
        "slots_by_pair": dict.fromkeys(PAIRS_20, frozenset()),
    }
    left = dict(base, dst_rule="D\nexceptional_closure_handling=E2")
    right = dict(base, exceptional_closure_handling="E2\ntimezone=UTC")
    assert calendar_content_digest(**left) != calendar_content_digest(**right)
    assert calendar_content_digest(**base) == calendar_content_digest(**dict(base))


# ---------------------------------------------------------------------------
# §12.25 — the declared-block exemption is bounded
# ---------------------------------------------------------------------------


def test_1225_a_declared_block_may_not_carry_more_numerics_than_declared_keys() -> None:
    """Returning early for a declared block set the bound to infinity.

    PR #448 §5.5.5 forbids raising the numeric-field bound to accommodate a
    record shape; exempting a key wholesale is that prohibition's limiting case.
    The bound is now the number of keys the schema declares may sit in a block,
    so a block can never carry more numerics than there are places to put them.
    """
    schema = artifact_schema("design_m15_inventory")
    assert schema is not None
    block: dict[str, Any] = dict.fromkeys(sorted(schema.block_only_keys), 1)
    at_bound = {"artifact": "design_m15_inventory", "files": [{"gap_report": dict(block)}]}
    assert scan_gate3a(at_bound, artifact="design_m15_inventory.json") == []
    block["one_too_many"] = 1
    over = {"artifact": "design_m15_inventory", "files": [{"gap_report": block}]}
    findings = scan_gate3a(over, artifact="design_m15_inventory.json")
    assert any(f.startswith("gate3a_block_immediate_numeric_fields") for f in findings), findings


# ---------------------------------------------------------------------------
# FR-2 — the credential rule discriminates
# ---------------------------------------------------------------------------


def test_fr2_the_credential_rule_has_a_negative_control() -> None:
    """A guard reporting every assignment-shaped string would have shipped.

    This was the one always-refuse mutant of thirty-seven that survived the
    whole suite.
    """
    assert scan_gate3a({"note": "window_label=first_quarter_of_the_year"}) == []
    assert scan_gate3a({"note": "bucket_start=2025_05_01T00_00_00Z"}) == []
    assert scan_gate3a({"secrets": "OANDA_API_KEY=9f3a2b1c8d7e6f5a4b3c2d1e"}) != []


# ---------------------------------------------------------------------------
# FR-12 — the committed inventory carries the ruled schema
# ---------------------------------------------------------------------------


def test_fr12_the_committed_inventory_declares_the_six_field_minute_accounting() -> None:
    """PR #444 §5 approved this schema change and assigned it to this PR.

    The two-key ``gap_report`` reported ``{'missing_minute_count': 0,
    'max_gap_minutes': 0}`` for a file that lost half its source minutes to
    rejection — indistinguishable from a perfect file.
    """
    schema = json.loads((ARTIFACTS / "design_m15_inventory.json").read_text(encoding="utf-8"))
    per_file = schema["required_schema_per_file"]
    assert set(per_file["minute_accounting"]) == set(MINUTE_ACCOUNTING_FIELDS)
    assert "gap_report" not in per_file
    # §12.20's rename, in the same committed authority.
    assert "complete_bucket_count" in per_file
    assert "eligible_event_count" not in per_file


# ---------------------------------------------------------------------------
# The writer still writes
# ---------------------------------------------------------------------------


def test_the_writer_still_writes_an_honest_artifact(tmp_path: Path) -> None:
    """The floor under every refusal above: legitimate output is unaffected."""
    payload = {
        "artifact": "scrub_report",
        "gate": "3a",
        "result": "NOT_PRODUCTION_READY",
        "checked_artifact_count": 8,
    }
    written = write_metadata_artifact(tmp_path, "scrub_report.json", payload)
    assert written.exists()
    assert json.loads(written.read_text(encoding="utf-8"))["result"] == "NOT_PRODUCTION_READY"
    with pytest.raises(ArtifactScrubError):
        write_metadata_artifact(
            tmp_path / "second",
            "scrub_report.json",
            {"artifact": "scrub_report", "result": "PRODUCTION_READY"},
        )


# ---------------------------------------------------------------------------
# Call-site pins. The helpers above exercise the primitives; these exercise the
# places that use them, because a mutation battery showed the primitive tests
# alone left every call site free.
# ---------------------------------------------------------------------------


def test_the_conjunction_key_pin_survives_a_key_that_lies_about_equality() -> None:
    """A key whose real data is not its match target.

    A plain `Masked` key is not enough: it inherits `str.__hash__`/`__eq__`, which
    already use the real data, so the lookup fails with or without the pin. The
    key has to answer the comparison itself — which is what `_pin_text` reading
    character data through the unbound slot refuses.
    """

    class Impostor(str):
        def __new__(cls, real: str, answers: str) -> Impostor:
            obj = super().__new__(cls, real)
            obj._answers = answers  # type: ignore[attr-defined]
            return obj

        def __eq__(self, other: object) -> bool:
            return other == self._answers  # type: ignore[attr-defined]

        def __hash__(self) -> int:
            return hash(self._answers)  # type: ignore[attr-defined]

    masked = {
        Impostor(f"PAIR_NEVER_MEASURED_{index}", pair): True for index, pair in enumerate(PAIRS_20)
    }
    with pytest.raises(AggregateAssertionUnsatisfiedError, match="has no measurement for"):
        assert_measured_conjunction("file_count_is_20", masked)


def test_the_calendar_digest_collision_the_audit_built_no_longer_collides() -> None:
    """The exact two-artifact construction, not an approximation of it.

    Both members render the same three lines under `name=value`, because one puts
    the injected boundary in `dst_rule` and the other puts it in
    `exceptional_closure_handling`. Length-prefixing is what separates them.
    """
    base: dict[str, Any] = {
        "authority": "A",
        "authority_version": "1",
        "timezone": "UTC",
        "market_open_close_rule": "R",
        "target_epoch": "EP",
        "committed_artifact": "artifacts/x.json",
        "committed_revision": "abc",
        "slots_by_pair": dict.fromkeys(PAIRS_20, frozenset()),
    }
    left = calendar_content_digest(
        **base,
        dst_rule="EU_DST",
        exceptional_closure_handling="NONE\nexceptional_closure_handling=XMAS",
    )
    right = calendar_content_digest(
        **base,
        dst_rule="EU_DST\nexceptional_closure_handling=NONE",
        exceptional_closure_handling="XMAS",
    )
    assert left != right
    # Negative control: identical content still digests identically.
    same = dict(base, dst_rule="EU_DST", exceptional_closure_handling="NONE")
    assert calendar_content_digest(**same) == calendar_content_digest(**same)


def test_the_coverage_digest_is_taken_over_the_slots_the_limbs_decided_on() -> None:
    """B-3 across the module boundary: one read must serve both.

    `assert_full_coverage` pinned each pair's expected set and then handed the
    *calendar* to the provenance check, which re-read `expected_slots(pair)`. An
    audit made the two reads disagree: a run certified one slot per pair while
    publishing the digest of the approved three-slot calendar, so the record
    attested to content the limbs never saw.
    """
    from scripts.m15_gate3a.coverage import assert_full_coverage
    from tests.m15_gate3a.test_wp_proof_coverage_calendar import (
        EPOCH,
        full_measurements,
        valid_calendar,
    )

    calendar = valid_calendar()
    honest = assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)

    class TwoFaced:
        """Answers the first read per pair honestly and later reads differently."""

        def __init__(self, real: dict[str, frozenset]) -> None:
            self._real = real
            self.reads: dict[str, int] = {}

        def get(self, pair: str, default: object = None) -> object:
            count = self.reads.get(pair, 0) + 1
            self.reads[pair] = count
            if pair not in self._real:
                return default
            if count == 1:
                return self._real[pair]
            return frozenset(sorted(self._real[pair])[:1])

    real = {pair: calendar.expected_slots(pair) for pair in PAIRS_20}
    faces = TwoFaced(real)
    object.__setattr__(calendar, "_slots", faces)
    second = assert_full_coverage(full_measurements(), calendar, expected_epoch=EPOCH)
    assert second.calendar_digest == honest.calendar_digest
    assert faces.reads and all(count == 1 for count in faces.reads.values()), faces.reads


def test_the_fr4_span_binding_is_pinned_at_its_call_site_not_only_in_the_helper() -> None:
    """`PairCoverage` is publicly constructible and validates nothing.

    `object.__setattr__` on a genuine `CoverageResult.per_pair` is this module's
    declared threat model, and an audit answered both span comparisons with a
    lying `datetime` subclass — a proof accepted a certified span years away from
    the one the byte scan measured.
    """
    from scripts.m15_gate3a.coverage import assert_full_coverage
    from scripts.m15_gate3a.proof import ProofLimbUnsatisfiedError, evaluate_four_limbs
    from tests.m15_gate3a.test_wp_proof_coverage_calendar import (
        EPOCH,
        binding_set,
        digest,
        full_measurements,
        producer_set,
        valid_calendar,
        verifier_set,
    )

    coverage = assert_full_coverage(full_measurements(), valid_calendar(), expected_epoch=EPOCH)
    honest = coverage.per_pair[0]
    liar = LyingInstant(
        honest.certified_slot_min.year + 6,
        honest.certified_slot_min.month,
        honest.certified_slot_min.day,
        tzinfo=UTC,
    )
    object.__setattr__(honest, "certified_slot_min", liar)
    with pytest.raises(ProofLimbUnsatisfiedError, match="certifies slots from"):
        evaluate_four_limbs(
            producer_records=producer_set(),
            verifier_records=verifier_set(),
            coverage_result=coverage,
            derivation_bindings=binding_set(),
            inventory_digest=digest(4242),
        )


def test_the_verifier_artifact_check_reads_the_pass_as_character_data() -> None:
    """One fabricated pass answered `==` for a file it did not name.

    `_pin_pass` re-reads `stream_id` and `pass_index` for exactly this reason;
    `artifact_id` sat beside them unpinned and decided two contract rules.
    """
    from scripts.m15_gate3a.proof import ProofContractError, assert_records_agree
    from tests.m15_gate3a.test_wp_proof_coverage_calendar import (
        producer_set,
        verifier_set,
    )

    producers, verifiers = producer_set(), verifier_set()
    honest_verifier = verifiers[0]
    real = honest_verifier.digest_provenance.artifact_id
    object.__setattr__(
        honest_verifier.digest_provenance,
        "artifact_id",
        Masked("A_DIFFERENT_FILE", real),
    )
    with pytest.raises(ProofContractError):
        assert_records_agree(producers[0], honest_verifier)


def test_a_refuted_recheck_cannot_be_re_offered_against_a_fresh_proof() -> None:
    """`_refute` condemned the recheck and nothing ever read the mark.

    An audit refuted a proof, minted a fresh one from the same evidence, and
    re-offered the very same recheck objects — consumption succeeded. §11 says
    the evidence a refutation was pronounced over is dead; either the ledger
    entry means that or `_refute` should not be writing it.
    """
    from scripts.m15_gate3a.proof import (
        ProofDisagreementError,
        open_for_consumption,
    )
    from tests.m15_gate3a.test_wp_proof_coverage_calendar import (
        evaluated_proof,
        published_id,
        recheck,
        recheck_set,
    )

    tampered = list(recheck_set())
    tampered[0] = recheck(PAIRS_20[0], 0, size_bytes=999_999)
    with pytest.raises(ProofDisagreementError):
        open_for_consumption(evaluated_proof(), consumer_rechecks=tampered)
    # The refutation was pronounced over these objects. A fresh proof minted from
    # the same evidence must not rehabilitate them.
    assert published_id(PAIRS_20[0])
    with pytest.raises(ProofDisagreementError, match="already refuted"):
        open_for_consumption(evaluated_proof(), consumer_rechecks=tampered)
    # Negative control: an untouched recheck set is still accepted.
    assert open_for_consumption(evaluated_proof(), consumer_rechecks=recheck_set())
