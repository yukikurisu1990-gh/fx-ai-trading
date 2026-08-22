"""Fourth-re-check fixes in the artifact writer/scrubber.

Covers FB-2, FB-3, FB-7, FB-9 (§12.25 strict, as ruled by PR #448 §5.5), FR-1,
FR-2, FR-6, FR-15, FR-16, FR-17, FR-18 and the `artifacts.py` entries in §14's
mutation-survivor table.

Every refusal here was **reproduced against the pre-fix source first** and every
one is paired with a negative control on the same rule, so a test that refuses
everything cannot masquerade as a test that discriminates. Each ``match=`` names
one guard and none uses alternation (§13): four rounds of this audit were
prolonged by matchers that could not say which guard fired.
"""

from __future__ import annotations

import json
import time
import unicodedata
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

import scripts.m15_gate3a.artifacts as artifacts_module
from scripts.m15_gate3a.aggregation import aggregate_m15
from scripts.m15_gate3a.artifacts import (
    _MAX_PROHIBITION_ENTRY_LEN,
    _MAX_PROHIBITION_ITEMS,
    _MAX_TEXT_CHARS,
    _MAX_VALUES_PER_NUMERIC_KEY,
    _RECORD_MAX_IMMEDIATE_NUMERIC_FIELDS,
    _REGISTERED_CLAIM_LABELS,
    ArtifactScrubError,
    artifact_schema,
    assert_gate3a_clean,
    scan_gate3a,
    snapshot_payload,
    write_metadata_artifact,
)
from scripts.m15_gate3a.guards import FORBIDDEN_STATUSES, UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS
from scripts.m15_gate3a.no_overlap import assert_per_file_bounds
from scripts.m15_gate3a.pair_authority import PAIRS_20, pip_size_for_pair

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _conformant_record(pair: str, index: int) -> dict[str, Any]:
    """The §12.20-conformant per-file record: four immediate numerics, nested block."""
    return {
        "filename": f"candles_{pair}_M15_365d_BA_DESIGN.jsonl",
        "pair": pair,
        "sha256": f"{index:064x}",
        "size_bytes": 4_812_345 + index,
        "row_count": 23_040,
        "complete_bucket_count": 21_500,
        "pip_size": pip_size_for_pair(pair),
        "ts_min_utc": "2025-04-25T00:00:00Z",
        "ts_max_utc": "2026-02-28T23:45:00Z",
        "gap_report": {
            "expected_source_minute_count": 345_600,
            "observed_source_minute_count": 345_500,
            "absent_source_minute_count": 100,
            "rejected_source_minute_count": 0,
            "usable_source_minute_count": 345_500,
            "max_unavailable_gap_minutes": 45,
        },
    }


def _conformant_inventory(records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    files = (
        records
        if records is not None
        else [_conformant_record(pair, i) for i, pair in enumerate(PAIRS_20)]
    )
    return {
        "artifact": "design_m15_inventory",
        "gate": "3a",
        "status": "SCHEMA_FIXED__POPULATED_AT_IMPLEMENTATION",
        "file_count": len(files),
        "files": files,
    }


def _immediate_numerics(record: dict[str, Any]) -> int:
    return sum(
        1 for v in record.values() if isinstance(v, (int, float)) and not isinstance(v, bool)
    )


def _price_rows(count: int) -> list[dict[str, Any]]:
    rows = []
    for i in range(count):
        base = 1.10 + i / 1e6
        rows.append(
            {
                "t": f"2025-06-02T{i // 60 % 24:02d}:{i % 60:02d}:00Z",
                "bid_o": base,
                "bid_h": base + 2e-5,
                "bid_l": base - 2e-5,
                "bid_c": base + 1e-5,
                "ask_o": base + 8e-5,
                "ask_h": base + 1e-4,
                "ask_l": base + 6e-5,
                "ask_c": base + 9e-5,
            }
        )
    return rows


# ===========================================================================
# FB-2 — the writer validated one read of the payload and published another
# ===========================================================================


class _TwoFacedPayload(dict):
    """A ``dict`` that shows a clean face until the *n*-th container read.

    The audit's own reproduction shape. ``artifacts.py`` was the one module in
    the package that did not snapshot its input, and it is the one that writes.
    """

    def __init__(self, clean: dict, real: dict, flip_at: int) -> None:
        super().__init__(clean)
        self._clean = clean
        self._real = real
        self._flip_at = flip_at
        self.reads = 0

    def _face(self) -> dict:
        self.reads += 1
        return self._real if self.reads >= self._flip_at else self._clean

    def items(self):  # noqa: ANN201, D102
        return self._face().items()

    def keys(self):  # noqa: ANN201, D102
        return self._face().keys()

    def values(self):  # noqa: ANN201, D102
        return self._face().values()

    def get(self, key, default=None):  # noqa: ANN001, ANN201, D102
        return self._face().get(key, default)

    def __iter__(self):  # noqa: ANN204, D105
        return iter(self._face())

    def __len__(self) -> int:  # noqa: D105
        return len(self._face())

    def __getitem__(self, key):  # noqa: ANN001, ANN204, D105
        return self._face()[key]


_CLEAN_FACE = {"artifact": "scrub_report", "gate": "3a"}
_REAL_FACE = {
    "artifact": "scrub_report",
    "gate": "3a",
    "result": "PRODUCTION_READY",
    "sharpe_ratio": 2.31,
    "net_pnl": 91234.5,
}


@pytest.mark.parametrize("flip_at", [2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
def test_fb2_a_payload_that_changes_between_reads_cannot_publish_its_second_face(
    flip_at: int, tmp_path: Path
) -> None:
    """Failing-before: at ``flip_at=8`` the writer put the real face on disk.

    Reproduced on pre-fix source through the real writer::

        flip@8: WROTE reads=9
        {"artifact": "scrub_report", "gate": "3a", "net_pnl": 91234.5,
         "result": "PRODUCTION_READY", "sharpe_ratio": 2.31}

    The flip point is swept rather than fixed at eight, because pinning the one
    index the audit happened to hit is exactly the instance-specific patch this
    programme exists to stop.
    """
    payload = _TwoFacedPayload(_CLEAN_FACE, _REAL_FACE, flip_at)
    out = tmp_path / f"flip{flip_at}"
    written = write_metadata_artifact(out, "scrub_report.json", payload)
    on_disk = json.loads(written.read_text(encoding="utf-8"))
    assert on_disk == _CLEAN_FACE
    assert "result" not in on_disk
    assert "sharpe_ratio" not in on_disk
    assert "net_pnl" not in on_disk


def test_fb2_the_writer_reads_the_caller_container_exactly_once() -> None:
    """The structural property, not just its observable consequence."""
    payload = _TwoFacedPayload(_CLEAN_FACE, _REAL_FACE, 1000)
    snapshot_payload(payload)
    assert payload.reads == 1


def test_fb2_a_two_faced_payload_whose_first_face_is_dirty_is_still_refused() -> None:
    """Negative control: snapshotting is not a way to smuggle the first face in."""
    payload = _TwoFacedPayload(_REAL_FACE, _CLEAN_FACE, 1000)
    with pytest.raises(ArtifactScrubError, match="forbidden_status_value"):
        assert_gate3a_clean(payload, artifact="scrub_report.json")


def test_fb2_the_bytes_written_are_the_bytes_that_were_validated(tmp_path: Path) -> None:
    """An honest payload still round-trips exactly (negative control)."""
    payload = _conformant_inventory()
    written = write_metadata_artifact(tmp_path / "out", "design_m15_inventory.json", payload)
    assert json.loads(written.read_text(encoding="utf-8")) == payload


class _MutatingList(list):
    """A ``list`` whose contents change on every iteration."""

    def __init__(self, clean: list, real: list) -> None:
        super().__init__(clean)
        self._clean = clean
        self._real = real
        self.reads = 0

    def __iter__(self):  # noqa: ANN204, D105
        self.reads += 1
        return iter(self._real if self.reads > 1 else self._clean)


def test_fb2_a_list_that_changes_between_reads_is_snapshotted_too(tmp_path: Path) -> None:
    """The snapshot covers every container type, not only ``dict``."""
    payload = {
        "artifact": "scrub_report",
        "checked_artifacts": _MutatingList(["a.json"], ["PRODUCTION_READY"]),
    }
    written = write_metadata_artifact(tmp_path / "out", "scrub_report.json", payload)
    assert json.loads(written.read_text(encoding="utf-8"))["checked_artifacts"] == ["a.json"]


# ===========================================================================
# FB-3(a) — a string leaf is a description, not a container
# ===========================================================================


def test_fb3a_a_dataset_serialised_into_one_string_leaf_is_refused(tmp_path: Path) -> None:
    """Failing-before: 428 904 chars under a declared key -> CLEAN, 468 983 bytes WROTE."""
    blob = json.dumps(_price_rows(2000))
    payload = {"artifact": "design_m15_inventory", "reason_not_populated_now": blob}
    findings = scan_gate3a(payload, artifact="design_m15_inventory.json")
    assert f"gate3a_oversize_text:reason_not_populated_now:{len(blob)}" in findings
    with pytest.raises(ArtifactScrubError, match="gate3a_oversize_text"):
        write_metadata_artifact(tmp_path / "out", "design_m15_inventory.json", payload)
    assert not (tmp_path / "out").exists()


def test_fb3a_the_same_dataset_under_no_schema_at_all_is_refused() -> None:
    """The undeclared backstop gets the identical rule, never a weaker one."""
    blob = json.dumps(_price_rows(2000))
    assert f"gate3a_oversize_text:note:{len(blob)}" in scan_gate3a({"note": blob})


def test_fb3a_a_short_serialised_container_is_refused_on_its_own_limb() -> None:
    """Length alone would admit it; structure is a separate limb."""
    blob = json.dumps(_price_rows(1))
    assert len(blob) < _MAX_TEXT_CHARS
    assert "gate3a_serialised_container_in_text:note" in scan_gate3a({"note": blob})
    assert "gate3a_oversize_text" not in " ".join(scan_gate3a({"note": blob}))


def test_fb3a_a_csv_encoded_series_is_refused_on_the_digit_density_limb() -> None:
    """Neither long nor JSON; a description does not quote a series of numbers."""
    csv = ",".join(f"{1.10 + i / 1e5:.5f}" for i in range(40))
    assert len(csv) < _MAX_TEXT_CHARS
    findings = scan_gate3a({"note": csv})
    assert any(f.startswith("gate3a_numeric_series_in_text:note:") for f in findings), findings


def test_fb3a_a_series_glued_to_letters_still_trips_the_density_limb() -> None:
    """The digit-run count is greedy, so padding each value with letters does not help."""
    glued = ",".join(f"v{1.10 + i / 1e5:.5f}v" for i in range(15))
    findings = scan_gate3a({"note": glued})
    assert any(f.startswith("gate3a_numeric_series_in_text:note:") for f in findings), findings


def test_fb3a_a_base64_blob_is_refused() -> None:
    """FB-3(a) names base64 as the same family; it is caught on length."""
    import base64

    blob = base64.b64encode(json.dumps(_price_rows(500)).encode()).decode()
    assert f"gate3a_oversize_text:note:{len(blob)}" in scan_gate3a({"note": blob})


def test_fb3a_data_in_keys_is_bounded_by_the_same_three_limbs() -> None:
    """FB-3(a)'s third encoding: the payload in the key rather than the value."""
    blob = json.dumps(_price_rows(2000))
    findings = scan_gate3a({blob: 1})
    assert any(f.startswith("gate3a_oversize_text:key(") for f in findings), findings


@pytest.mark.parametrize(
    "description",
    [
        "Populating this inventory requires running the M1->M15 aggregation.",
        "2026-09-25 (validation ~2026-04-25..2026-07-25 + purge + holdout ~2026-07-25..2026-09-25)",
        "ab" * 32,
        f"{7:064x}",
        "<= 2026-02-28T23:59:59Z",
        "2025-04-24T22:03:00.000000000Z",
        "candles_EUR_USD_M15_365d_BA_DESIGN.jsonl",
        "[]",
        "{}",
    ],
)
def test_fb3a_real_descriptions_and_digests_are_untouched(description: str) -> None:
    """Negative control, including the two shapes most at risk of a false refusal.

    A sha256 hex digest packs digits among letters — a naive ``\\d+`` count scores
    32 on ``0a0a0a...`` — and the committed artifacts carry one per inventory
    record. An empty container literal is a description, not a payload.
    """
    assert scan_gate3a({"reason": description}) == []


def _committed_strings() -> list[str]:
    """Every string value and key in the eight committed gate-3a artifacts.

    Read here, in the tests, because ``scripts/m15_gate3a/**`` must stay
    reader-free (§12.14) — which is exactly why the source carries a
    transcription and this test is what stops the transcription drifting.
    """
    root = Path(__file__).resolve().parents[2] / "artifacts" / "m15_gate3a"
    found: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                found.append(key)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, str):
            found.append(node)

    paths = sorted(root.glob("*.json"))
    assert len(paths) >= 8
    for path in paths:
        walk(json.loads(path.read_text(encoding="utf-8")))
    assert len(found) > 100
    return found


def test_fb3a_the_text_bound_is_the_longest_string_the_committed_artifacts_carry() -> None:
    """The bound is committed content, not a number chosen here.

    The source transcribes the longest committed string verbatim and takes its
    ``len()``; this test re-derives that string from the committed artifacts and
    asserts the transcription is the same one, so re-spelling it cannot silently
    move the bound.
    """
    longest = max(_committed_strings(), key=len)
    assert longest == artifacts_module._LONGEST_COMMITTED_STRING_VALUE
    assert len(longest) == _MAX_TEXT_CHARS
    assert scan_gate3a({"reason": longest}) == []
    findings = scan_gate3a({"reason": longest + "x"})
    assert f"gate3a_oversize_text:reason:{len(longest) + 1}" in findings


def test_fb3a_the_digit_density_bound_clears_every_committed_string() -> None:
    """The other derived bound, checked against the same committed evidence."""
    from scripts.m15_gate3a.artifacts import _DIGIT_RUN_RE, _HEX_DIGEST_RE

    worst = max(
        len(_DIGIT_RUN_RE.findall(_HEX_DIGEST_RE.sub(" ", text))) for text in _committed_strings()
    )
    assert 0 < worst <= _MAX_VALUES_PER_NUMERIC_KEY


# ===========================================================================
# FB-3(b) — a metric root is a property of the key's letters
# ===========================================================================


@pytest.mark.parametrize(
    "key",
    ["sharperatio", "netpnl", "maxdrawdown", "winrate", "hitrate", "PnL", "netPnL", "MaxDD"],
)
def test_fb3b_a_run_together_metric_key_is_refused(key: str) -> None:
    """Failing-before: every one of these scanned CLEAN and ``metrics.json`` WROTE."""
    with pytest.raises(ArtifactScrubError, match="gate3a_forbidden_key"):
        assert_gate3a_clean({key: 1.0})


@pytest.mark.parametrize("key", ["ROI", "total_roi", "alpha", "information_ratio"])
def test_fb3b_a_metric_the_vocabulary_had_no_entry_for_is_refused(key: str) -> None:
    """The other half of FB-3(b): names the list did not carry at all."""
    with pytest.raises(ArtifactScrubError, match="gate3a_forbidden_key"):
        assert_gate3a_clean({key: 1.0})


@pytest.mark.parametrize(
    "key",
    [
        "raw_event_count",
        "trade_count_floor",
        "raw_holdout_trade_floor",
        "complete_bucket_count",
        "cost_hurdle_eligible_bar_count",
        "raw_traded_event_count",
        "alphabetical_order",
        "max_unavailable_gap_minutes",
        "total_missing_source_minutes_within_emitted_buckets",
    ],
)
def test_fb3b_legitimate_key_names_survive_the_dense_matching(key: str) -> None:
    """Negative control: matching on letters must not sweep up the real vocabulary."""
    assert scan_gate3a({key: 1}) == []


def test_fb3b_every_declared_and_committed_key_survives_the_metric_matcher() -> None:
    """Class-level control: the whole key space this gate may legitimately emit.

    A dense-substring matcher is only safe if nothing it may meet is a false
    positive, so the assertion is over the complete vocabulary rather than a
    sample. The committed disclaimers (``holdout_metrics_committed`` and its
    family) are excluded because they are metric keys by construction and are
    exempt only through their ``false`` value (RF-8), which is asserted next.
    """
    from scripts.m15_gate3a.artifacts import _SCHEMAS, _forbidden_key_hit

    vocabulary = {k for schema in _SCHEMAS for k in schema.allowed_keys}
    assert len(vocabulary) > 100
    offenders = sorted(k for k in vocabulary if _forbidden_key_hit(k) is not None)
    # The only declared keys that name a metric are the scrub report's own
    # disclaimers, and each is admissible solely because its value denies it
    # (RF-8) — asserted here as a property rather than restated as a list.
    assert offenders
    for key in offenders:
        assert scan_gate3a({key: False}) == [], key
        assert f"gate3a_forbidden_key:{key}" in scan_gate3a({key: True}), key


def test_fb3b_the_committed_disclaimer_keys_remain_writable() -> None:
    assert scan_gate3a({key: False for key in ("holdout_metrics_committed",)}) == []


# ===========================================================================
# FB-3(c) — a declared numeric key carries a value from its own domain
# ===========================================================================


def test_fb3c_price_columns_under_declared_numeric_keys_are_refused(tmp_path: Path) -> None:
    """Failing-before: 20 pairs x 8 price columns -> CLEAN, 7 885 bytes WROTE."""
    declared_numeric = (
        "complete_bucket_count",
        "cost_hurdle_eligible_bar_count",
        "dead_window_bars_present",
        "row_count",
        "size_bytes",
    )
    files = []
    for i, pair in enumerate(PAIRS_20):
        record: dict[str, Any] = {"pair": pair}
        for j, key in enumerate(declared_numeric):
            record[key] = round(1.10 + i / 1e4 + j / 1e5, 6)
        files.append(record)
    payload = {"artifact": "design_m15_inventory", "files": files}
    findings = scan_gate3a(payload, artifact="design_m15_inventory.json")
    for key in declared_numeric:
        assert f"gate3a_non_integral_value_under_count_key:{key}" in findings
    with pytest.raises(ArtifactScrubError, match="gate3a_non_integral_value_under_count_key"):
        write_metadata_artifact(tmp_path / "out", "design_m15_inventory.json", payload)


@pytest.mark.parametrize("bad", [1.10001, -1, -0.5, 0.5])
def test_fb3c_a_count_key_refuses_anything_that_is_not_a_non_negative_integer(bad: float) -> None:
    findings = scan_gate3a({"artifact": "design_m15_inventory", "row_count": bad})
    assert "gate3a_non_integral_value_under_count_key:row_count" in findings


@pytest.mark.parametrize("good", [0, 1, 23_040, 21_500])
def test_fb3c_a_count_key_accepts_a_count(good: int) -> None:
    """Negative control: the domain rule discriminates, it does not refuse numbers."""
    assert scan_gate3a({"artifact": "design_m15_inventory", "row_count": good}) == []


def test_fb3c_pip_size_may_hold_only_what_the_pip_authority_produces() -> None:
    """A price is not a pip size, and the domain is the authority's, not a literal."""
    findings = scan_gate3a({"artifact": "design_m15_inventory", "pip_size": 1.10001})
    assert "gate3a_value_outside_committed_domain:pip_size" in findings
    for pair in PAIRS_20:
        payload = {"artifact": "design_m15_inventory", "pip_size": pip_size_for_pair(pair)}
        assert scan_gate3a(payload) == [], pair


def test_fb3c_the_committed_fractional_quantities_are_still_writable() -> None:
    """Negative control: the three committed non-integral values must survive."""
    plan = {
        "artifact": "cost_table_plan",
        "execution_padding_pip": 0.3,
        "flat_slippage_cell_pip": 0.5,
    }
    assert scan_gate3a(plan, artifact="cost_table_plan_or_metadata.json") == []
    manifest = {"artifact": "forward_epoch_adoption_manifest", "elapsed_months_approx": 2.4}
    assert scan_gate3a(manifest) == []


# ===========================================================================
# FB-7 — the fold is script-restricted, not a two-script denylist
# ===========================================================================


@pytest.mark.parametrize(
    ("label", "spelling"),
    [
        ("cherokee_A_for_D", "PROᎠUCTION_READY"),
        ("canadian_PA_for_P", "ᑭASS"),
        ("cherokee_E", "BYTᎡ_ADMISSIBLE"),
        ("cherokee_R", "PᎡODUCTION_READY"),
        ("coptic_P_for_P", "ⲢASS"),
        ("armenian_O_for_O", "PRODUCTIՕN_READY"),
        ("deseret_S_for_S", "PA\U0001041dS"),
        ("osage_A_for_A", "P\U000104b0SS"),
    ],
)
def test_fb7_a_letter_outside_ascii_is_a_finding_whatever_script_it_comes_from(
    label: str, spelling: str
) -> None:
    """Failing-before: a single Cherokee codepoint defeated **all 21** labels.

    Two of the table's own rows folded to the wrong letter — ``"Ꭰ": "A"`` is
    CHEROKEE LETTER A but renders **D**, and ``"ᑭ": "C"`` renders **P** — so the
    fold guaranteed the miss. The rule that replaces the table is structural: a
    letter that survives folding and is still outside ASCII is reported, because
    the scrubber cannot prove it is not a homoglyph.
    """
    with pytest.raises(ArtifactScrubError, match="gate3a_non_ascii_letter"):
        assert_gate3a_clean({"result": spelling})


def test_fb7_the_two_mis_mapped_table_rows_are_gone() -> None:
    """A mis-map is worse than an omission: it rewrites the character into a miss."""
    from scripts.m15_gate3a.artifacts import _CONFUSABLES

    assert "Ꭰ" not in _CONFUSABLES
    assert "ᑭ" not in _CONFUSABLES
    for target in _CONFUSABLES.values():
        assert len(target) == 1
        assert target.isascii()


def test_fb7_no_single_codepoint_substitution_hides_a_label_while_looking_like_one() -> None:
    """The systematic sweep, re-run over the classes that defeated the first fix.

    The predecessor swept **the Cherokee syllabary only**, and an internal audit
    showed it was incapable of reporting the live family by construction: it
    scored a candidate a defeat only if ``_non_ascii_letters`` was non-empty or
    the dense form was unchanged, and the surviving substitutions — non-ASCII
    *digits, symbols and marks* — satisfied neither, so 19 of 24 labels fell
    while the test reported ``defeats == []``.

    The sweep therefore covers a codepoint from every relevant general category,
    including the four the audit used, and the invariant is now the one that
    actually matters: a substitution either scans dirty, or it must not still
    render as the label. A clean result is admissible only when the character
    folded to ASCII and spelled a *different* word — a visible misspelling.
    """
    from scripts.m15_gate3a.artifacts import _dense, _fold_hazards

    probes = [
        *(chr(cp) for cp in range(0x13A0, 0x13F6)),  # Cherokee (Lo) - the old sweep
        "߀",  # NKO DIGIT ZERO (Nd) - reads as O
        "١",  # ARABIC-INDIC DIGIT ONE (Nd)
        "∣",  # DIVIDES (Sm) - reads as I or l
        "∧",  # LOGICAL AND (Sm) - reads as A
        "∃",  # THERE EXISTS (Sm) - reads as E
        "○",  # WHITE CIRCLE (So) - reads as O
        "〇",  # IDEOGRAPHIC NUMBER ZERO (Nl)
        "×",  # MULTIPLICATION SIGN (Sm) - reads as x
    ]
    defeats: list[tuple[str, str]] = []
    examined = 0
    clean_and_folded = 0
    for label in sorted(FORBIDDEN_STATUSES | UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS):
        for char in probes:
            for i, original in enumerate(label):
                if not (original.isascii() and original.isalpha()):
                    continue
                examined += 1
                candidate = label[:i] + char + label[i + 1 :]
                if scan_gate3a({"result": candidate}) != []:
                    continue
                if _fold_hazards(candidate) or _dense(candidate) == _dense(label):
                    defeats.append((label, unicodedata.name(char, hex(ord(char)))))
                else:
                    # Admissible: no hazard, and the dense form spells a
                    # different word. Substitutions at a label's first or last
                    # character land here — they delete a character the label
                    # needs, so the result cannot render as the label.
                    clean_and_folded += 1
    assert examined > 5000, "the sweep must actually have run"
    assert clean_and_folded > 0, "the discriminating branch must have been exercised"
    assert defeats == []


def test_fb7_a_non_letter_homoglyph_is_reported_as_a_fold_join() -> None:
    """The specific mechanism, pinned separately from the sweep.

    A non-ASCII character that is not a letter is *deleted* by the dense fold, so
    the label closes up around the hole exactly as an unlisted letter would. The
    join rule reports the deletion rather than the codepoint's category.
    """
    findings = scan_gate3a({"result": "PR߀DUCTION_READY"})
    assert findings == ["gate3a_non_ascii_join:result:07C0"]


def test_fb7_ordinary_non_ascii_typography_is_still_writable() -> None:
    """Negative control: the join rule must not refuse a visible separator.

    In ``"1.5 -> higher"`` the run between the alphanumerics contains ASCII
    spaces, so a reader sees the break the scanner sees. Only a separator that is
    *entirely* invisible makes the two disagree, and only that is reported.
    """
    assert scan_gate3a({"note": "1.5 → higher"}) == []
    assert scan_gate3a({"note": "café latte"}) == []
    # And the positive half, so this control discriminates: the same sentence
    # with the separator made entirely invisible IS reported.
    assert scan_gate3a({"note": "1.5→higher"}) == ["gate3a_non_ascii_join:note:2192"]


def test_fb7_the_cyrillic_and_greek_table_still_names_the_label_it_spells() -> None:
    """The table is kept for precision: a folded spelling reports *which* label."""
    findings = scan_gate3a({"result": "PАSS"})
    assert "gate3a_forbidden_status_value:PASS" in findings
    assert findings == ["gate3a_forbidden_status_value:PASS"]


def test_fb7_the_committed_artifacts_are_ascii_so_nothing_committed_is_refused() -> None:
    """The floor under the script restriction: it refuses no committed content."""
    root = Path(__file__).resolve().parents[2] / "artifacts" / "m15_gate3a"
    paths = sorted(root.glob("*.json"))
    assert len(paths) >= 8
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert text.isascii(), path.name


# ===========================================================================
# FB-9 / §12.25 — S1 strict, as ruled by PR #448 §5.5
# ===========================================================================


def test_1225_the_conformant_twenty_record_inventory_scans_clean_and_writes(
    tmp_path: Path,
) -> None:
    """§12.25 sentence 2, pinned directly on the §12.20-conformant shape."""
    inventory = _conformant_inventory()
    assert _immediate_numerics(inventory["files"][0]) == 4
    assert scan_gate3a(inventory, artifact="design_m15_inventory.json") == []
    written = write_metadata_artifact(tmp_path / "out", "design_m15_inventory.json", inventory)
    assert len(json.loads(written.read_text(encoding="utf-8"))["files"]) == 20


def test_1225_a_single_six_numeric_record_refuses() -> None:
    """§5.5.4's second sub-question, answered the stricter way the ruling directs.

    Failing-before: the inherited heuristic needed **two** row-like records, so
    ``6 immediate numerics x 1 record`` scanned ``[]``.
    """
    record = _conformant_record("EUR_USD", 0)
    record["cost_hurdle_eligible_bar_count"] = 18_003
    record["raw_traded_event_count"] = 1_204
    assert _immediate_numerics(record) == 6
    inventory = _conformant_inventory([record])
    with pytest.raises(ArtifactScrubError, match="gate3a_record_immediate_numeric_fields"):
        assert_gate3a_clean(inventory, artifact="design_m15_inventory.json")


def test_1225_five_immediate_numerics_is_the_last_accepted_shape() -> None:
    """Both sides of the bound, so the test discriminates rather than refusing."""
    at_bound = _conformant_record("EUR_USD", 0)
    at_bound["cost_hurdle_eligible_bar_count"] = 18_003
    assert _immediate_numerics(at_bound) == _RECORD_MAX_IMMEDIATE_NUMERIC_FIELDS == 5
    assert scan_gate3a(_conformant_inventory([at_bound])) == []
    over = dict(at_bound)
    over["raw_traded_event_count"] = 1_204
    findings = scan_gate3a(_conformant_inventory([over]))
    assert "gate3a_record_immediate_numeric_fields:files:6" in findings


def test_1225_a_flattened_gap_report_refuses_on_its_own_limb() -> None:
    """Failing-before: flattening scanned ``[]`` and a test pinned that reading."""
    record = _conformant_record("EUR_USD", 0)
    record.update(record.pop("gap_report"))
    findings = scan_gate3a(_conformant_inventory([record]))
    assert "gate3a_nested_block_key_flattened:expected_source_minute_count" in findings
    assert "gate3a_nested_block_key_flattened:usable_source_minute_count" in findings


def test_1225_hoisting_one_accounting_field_alone_already_refuses() -> None:
    """The flattening limb is independent of the field count, not a consequence of it."""
    record = _conformant_record("EUR_USD", 0)
    gap = record["gap_report"]
    record["absent_source_minute_count"] = gap.pop("absent_source_minute_count")
    assert _immediate_numerics(record) == 5
    findings = scan_gate3a(_conformant_inventory([record]))
    assert findings == ["gate3a_nested_block_key_flattened:absent_source_minute_count"]


def test_1225_the_declared_scan_is_no_weaker_than_the_undeclared_one() -> None:
    """FB-9's headline inversion: declaring a schema bought LESS shape scrutiny.

    The same six-numeric record is refused with and without a resolvable schema,
    and the resolution is a narrowing of the schema, never a weakening of the
    backstop (§5.5.6).
    """
    record = _conformant_record("EUR_USD", 0)
    record["cost_hurdle_eligible_bar_count"] = 18_003
    record["raw_traded_event_count"] = 1_204
    declared = scan_gate3a(_conformant_inventory([record]), artifact="design_m15_inventory.json")
    schemaless = scan_gate3a({"files": [record]})
    assert any(f.startswith("gate3a_record_immediate_numeric_fields") for f in declared)
    assert any(f.startswith("gate3a_record_immediate_numeric_fields") for f in schemaless)


def test_1225_the_nested_block_exemption_does_not_reach_an_undeclared_block() -> None:
    """Only the two blocks the schema names may carry six immediate numerics."""
    record = _conformant_record("EUR_USD", 0)
    record["required_aggregate_assertions"] = dict(record.pop("gap_report"))
    findings = scan_gate3a(_conformant_inventory([record]))
    assert "gate3a_record_immediate_numeric_fields:required_aggregate_assertions:6" in findings


def test_1225_the_bound_is_the_contract_number_and_not_a_local_choice() -> None:
    assert _RECORD_MAX_IMMEDIATE_NUMERIC_FIELDS == 5


# ===========================================================================
# FR-1 / FR-16 — a prohibition list is a list of registered labels
# ===========================================================================


def test_fr1_a_dict_under_a_prohibition_key_is_not_a_prohibition_list(tmp_path: Path) -> None:
    """Failing-before: this scanned CLEAN and was written to disk."""
    payload = {
        "artifact": "scrub_report",
        "forbidden_labels": {"result": "PASS", "content_kind": "PRODUCTION_READY"},
    }
    findings = scan_gate3a(payload, artifact="scrub_report.json")
    assert "gate3a_prohibition_list_not_a_list:forbidden_labels" in findings
    assert "gate3a_forbidden_status_value:PASS" in findings
    assert "gate3a_forbidden_status_value:PRODUCTIONREADY" in findings
    with pytest.raises(ArtifactScrubError, match="gate3a_prohibition_list_not_a_list"):
        write_metadata_artifact(tmp_path / "out", "scrub_report.json", payload)


@pytest.mark.parametrize(
    ("entry", "expected_label"),
    [
        ("GATE 3A RESULT IS PASS", "PASS"),
        ("READY_FOR_LIVE=TRUE", "READYFORLIVE"),
        ("result: PRODUCTION_READY", "PRODUCTIONREADY"),
        ("we are DEPLOYABLE", "DEPLOYABLE"),
    ],
)
def test_fr1_an_entry_that_is_not_exactly_a_registered_label_is_claim_scanned(
    entry: str, expected_label: str
) -> None:
    """The exemption attaches to a label, never to arbitrary text under a key."""
    payload = {"artifact": "scrub_report", "forbidden_labels": [entry]}
    findings = scan_gate3a(payload, artifact="scrub_report.json")
    assert f"gate3a_forbidden_status_value:{expected_label}" in findings


def test_fr1_a_nested_container_inside_a_prohibition_list_earns_no_exemption() -> None:
    payload = {"artifact": "scrub_report", "forbidden_labels": [["PASS"], {"result": "PASS"}]}
    findings = scan_gate3a(payload, artifact="scrub_report.json")
    assert "gate3a_forbidden_status_value:PASS" in findings


def test_fr1_the_exemption_still_reaches_a_genuine_prohibition_list(tmp_path: Path) -> None:
    """Negative control: the construct playbook §10 permits must remain writable."""
    payload = {
        "artifact": "scrub_report",
        "gate": "3a",
        "forbidden_labels": sorted(FORBIDDEN_STATUSES),
    }
    assert scan_gate3a(payload, artifact="scrub_report.json") == []
    written = write_metadata_artifact(tmp_path / "out", "scrub_report.json", payload)
    labels = json.loads(written.read_text(encoding="utf-8"))["forbidden_labels"]
    assert sorted(labels) == sorted(FORBIDDEN_STATUSES)


def test_fr16_the_byte_level_claim_tokens_are_listable_in_a_prohibition_list(
    tmp_path: Path,
) -> None:
    """Failing-before: ``gate3a_prohibition_entry_too_long`` and the write refused.

    ``guards.py`` says these tokens "may appear only in prohibition lists"; for
    all three they could appear nowhere.
    """
    tokens = sorted(UNWRITABLE_BYTE_LEVEL_CLAIM_TOKENS)
    assert max(len(t) for t in tokens) == 40 > _MAX_PROHIBITION_ENTRY_LEN
    payload = {"artifact": "scrub_report", "gate": "3a", "forbidden_labels": tokens}
    assert scan_gate3a(payload, artifact="scrub_report.json") == []
    written = write_metadata_artifact(tmp_path / "out", "scrub_report.json", payload)
    assert sorted(json.loads(written.read_text(encoding="utf-8"))["forbidden_labels"]) == tokens


def test_fr16_the_entry_length_bound_was_not_raised_to_achieve_that() -> None:
    """A fix that loosens a neighbouring guard to close its own finding is not a fix."""
    assert _MAX_PROHIBITION_ENTRY_LEN == max(len(s) for s in FORBIDDEN_STATUSES) == 22
    long_prose = "this gate3a run is fine and nothing is claimed about it at all"
    assert len(long_prose) > _MAX_PROHIBITION_ENTRY_LEN
    payload = {"artifact": "scrub_report", "forbidden_labels": [long_prose]}
    findings = scan_gate3a(payload, artifact="scrub_report.json")
    assert "gate3a_prohibition_entry_too_long:forbidden_labels" in findings


def test_fr16_a_registered_label_is_admitted_by_membership_not_by_length() -> None:
    """Both halves of the discriminator, on strings of the same length."""
    token = "BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVEN"
    assert token in _REGISTERED_CLAIM_LABELS
    imposter = "BYTE_LEVEL_NO_DEAD_WINDOW_OVERLAP_PROVE_"
    assert len(imposter) == len(token)
    assert scan_gate3a({"artifact": "scrub_report", "forbidden_labels": [token]}) == []
    findings = scan_gate3a({"artifact": "scrub_report", "forbidden_labels": [imposter]})
    assert "gate3a_prohibition_entry_too_long:forbidden_labels" in findings


def test_fr21_the_prohibition_list_length_bound_is_the_registered_vocabulary() -> None:
    """§14 survivor: ``_MAX_PROHIBITION_ITEMS`` -> 10000 went unnoticed."""
    assert _MAX_PROHIBITION_ITEMS == len(_REGISTERED_CLAIM_LABELS) == 24
    at_bound = sorted(_REGISTERED_CLAIM_LABELS)
    assert len(at_bound) == _MAX_PROHIBITION_ITEMS
    assert scan_gate3a({"artifact": "scrub_report", "forbidden_labels": at_bound}) == []
    over = [*at_bound, at_bound[0]]
    findings = scan_gate3a({"artifact": "scrub_report", "forbidden_labels": over})
    assert "gate3a_list_longer_than_declared:forbidden_labels" in findings


def test_fr21_a_label_named_twice_is_reported_as_a_duplicate() -> None:
    """The distinctness rule, isolated below the length bound."""
    findings = scan_gate3a({"artifact": "scrub_report", "forbidden_labels": ["PASS", "PASS"]})
    assert "gate3a_prohibition_entry_duplicated:forbidden_labels" in findings
    assert scan_gate3a({"artifact": "scrub_report", "forbidden_labels": ["PASS", "MEETS"]}) == []


# ===========================================================================
# FR-2 — a live-format credential in a string value
# ===========================================================================


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            {"note": "OANDA_API_KEY=1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f"},
            "gate3a_credential_value:note:OANDA_API_KEY",
        ),
        (
            {"rationale": "api_key=sk-live-51H8gJ2kLmNoPqRsTuVwXyZ0123456789abcdef"},
            "gate3a_credential_value:rationale:api_key",
        ),
        (
            {"note": "export OANDA_TOKEN=abcd1234abcd1234abcd1234abcd1234abcd1234"},
            "gate3a_credential_value:note:OANDA_TOKEN",
        ),
        (
            {"note": "aws_secret_access_key=wJalrXUtnFEMIK7MDENGbPxRfiCYEXAMPLEKEY"},
            "gate3a_credential_value:note:aws_secret_access_key",
        ),
        (
            {"note": "the id is AKIAIOSFODNN7EXAMPLE"},
            "gate3a_credential_value:note:aws_access_key_id",
        ),
    ],
)
def test_fr2_a_credential_value_under_a_permitted_key_is_refused(
    payload: dict[str, str], expected: str
) -> None:
    """Failing-before: all of these scanned CLEAN — detection was key-name based."""
    assert expected in scan_gate3a(payload)


@pytest.mark.parametrize(
    "honest",
    [
        "no api_key, token or credential is committed anywhere in this tree",
        "secrets: NONE_COMMITTED",
        "the token vocabulary is described in guards.py",
        "design_end=2026-02-28T23:59:59Z",
        "aggregation_config_hash=none",
    ],
)
def test_fr2_honest_sentences_about_credentials_are_not_credentials(honest: str) -> None:
    """Negative control: this is an assignment rule, not a keyword rule."""
    assert not any(f.startswith("gate3a_credential_value:") for f in scan_gate3a({"note": honest}))


def test_fr2_a_credential_in_a_key_is_caught_on_the_same_rule() -> None:
    findings = scan_gate3a({"OANDA_API_KEY=1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d": "x"})
    assert any(f.startswith("gate3a_credential_value:key(") for f in findings), findings


# ===========================================================================
# FR-15 — a denial is not a claim, in the value direction too
# ===========================================================================


@pytest.mark.parametrize(
    "denial",
    [
        "NOT_PRODUCTION_READY",
        "NOT_VALIDATED",
        "no PASS is claimed",
        "this gate is not production ready",
        "NOT_DEPLOYABLE",
        "never MEETS the pre-registered criteria",
        "PRODUCTION_READINESS_NOT_CLAIMED",
        "NO_EXECUTION_PERFORMED",
    ],
)
def test_fr15_an_honest_denial_is_writable(denial: str) -> None:
    """Failing-before: the first four were ``gate3a_forbidden_status_value`` findings.

    The machinery must be able to write the denials its own governance vocabulary
    is made of; the always-binding statuses survived only by accident of spelling.
    """
    assert scan_gate3a({"note": denial}) == []


@pytest.mark.parametrize(
    "claim",
    [
        "PRODUCTION_READY",
        "this gate is production ready",
        "PRODUCTION_READY_NOT_PRODUCTION_READY",
        "is not really production ready",
        "verdict: pass",
        "NOTABLE_PRODUCTION_READY",
    ],
)
def test_fr15_the_denial_exemption_is_not_a_bypass(claim: str) -> None:
    """Negative control. The negator must sit immediately before the claim.

    ``"is not really production ready"`` is refused deliberately: the fail-closed
    direction is the safe one, and a looser adjacency window is a bypass.
    """
    with pytest.raises(ArtifactScrubError, match="gate3a_forbidden_status_value"):
        assert_gate3a_clean({"note": claim})


def test_fr15_a_denial_key_and_a_denial_value_behave_the_same_way() -> None:
    """RF-8 covered keys only; the two directions are now symmetric."""
    assert scan_gate3a({"PRODUCTION_READY": "no"}) == []
    assert scan_gate3a({"note": "NOT_PRODUCTION_READY"}) == []
    with pytest.raises(ArtifactScrubError, match="gate3a_forbidden_status_key"):
        assert_gate3a_clean({"PRODUCTION_READY": True})


# ===========================================================================
# FR-6 — the producers' real records must be writable
# ===========================================================================


def _synthetic_m1_rows(count: int) -> tuple[list[dict[str, Any]], frozenset[datetime]]:
    start = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
    rows = []
    for i in range(count):
        base = 1.1000 + i / 1e5
        rows.append(
            {
                "ts": start + timedelta(minutes=i),
                "bid_o": base,
                "bid_h": base + 1e-5,
                "bid_l": base - 1e-5,
                "bid_c": base,
                "ask_o": base + 2e-5,
                "ask_h": base + 3e-5,
                "ask_l": base + 1e-5,
                "ask_c": base + 2e-5,
            }
        )
    return rows, frozenset(start + timedelta(minutes=i) for i in range(count))


def test_fr6_the_gap_report_the_producer_emits_is_writable_into_the_inventory(
    tmp_path: Path,
) -> None:
    """Failing-before: six ``gate3a_undeclared_key`` findings, ``minute_accounting``
    among them — the whole D-3 block coverage consumes."""
    rows, expected = _synthetic_m1_rows(30)
    _, gap_report = aggregate_m15(rows, pair="EUR_USD", expected_minutes=expected)
    assert "minute_accounting" in gap_report
    record = _conformant_record("EUR_USD", 0)
    record["gap_report"] = gap_report
    inventory = _conformant_inventory([record])
    assert scan_gate3a(inventory, artifact="design_m15_inventory.json") == []
    write_metadata_artifact(tmp_path / "out", "design_m15_inventory.json", inventory)


def test_fr6_the_no_overlap_record_the_producer_emits_is_writable(tmp_path: Path) -> None:
    """The other direction: the honest-disclosure keys B-2 added were undeclared."""
    records = [
        {
            "pair": pair,
            "filename": f"candles_{pair}_M15_365d_BA_DESIGN.jsonl",
            "sha256": f"{index:064x}",
            "ts_min_utc": "2025-06-02T00:00:00Z",
            "ts_max_utc": "2026-02-28T23:45:00Z",
        }
        for index, pair in enumerate(PAIRS_20)
    ]
    emitted = assert_per_file_bounds(records, role="design")
    for key in ("evidence_basis", "files_opened", "bytes_measured", "declared_not_measured"):
        assert key in emitted
    payload = {"artifact": "no_overlap_proof", **emitted}
    assert scan_gate3a(payload, artifact="no_overlap_proof.json") == []
    write_metadata_artifact(tmp_path / "out", "no_overlap_proof.json", payload)


def test_fr6_the_extension_did_not_open_the_inventory_to_undeclared_keys() -> None:
    """Negative control: widening the vocabulary is not the same as removing it."""
    findings = scan_gate3a({"artifact": "design_m15_inventory", "not_a_declared_key": "x"})
    assert findings == ["gate3a_undeclared_key:not_a_declared_key"]


# ===========================================================================
# FR-17 — the gatekeeper must return
# ===========================================================================


def test_fr17_text_already_refused_as_unbounded_never_reaches_the_base_scanner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The structural pin, decided by observation rather than by a stopwatch.

    A wall-clock assertion is the wrong instrument here: under a regression that
    removes the skip, the base scrubber does not fail — it **does not return**, so
    a timing test hangs the suite instead of failing it. The sentinel makes the
    same property fail in milliseconds and says which branch was taken.
    """
    calls: list[object] = []

    def sentinel(payload: object) -> list[str]:
        calls.append(payload)
        return ["sentinel_base_finding"]

    monkeypatch.setattr(artifacts_module, "_base_scan_payload", sentinel)

    oversize = {"note": "a" * (_MAX_TEXT_CHARS + 1)}
    findings = scan_gate3a(oversize)
    assert f"gate3a_oversize_text:note:{_MAX_TEXT_CHARS + 1}" in findings
    assert "sentinel_base_finding" not in findings
    assert calls == []

    within_bounds = {"note": "a" * _MAX_TEXT_CHARS}
    assert "sentinel_base_finding" in scan_gate3a(within_bounds)
    assert len(calls) == 1


@pytest.mark.parametrize("width", [2_000, 8_000, 16_000, 32_000])
def test_fr17_a_long_alphanumeric_run_is_refused_promptly(width: int) -> None:
    """FR-17, restated for what the fix actually guarantees.

    This used to assert that a long alphanumeric run *scanned* in bounded time.
    It no longer scans at all: `gate3a_oversize_text_token` refuses any run wider
    than a committed sha256 digest, which is the FB-3(a) fix. What still needs
    pinning is that the refusal is **prompt** — the original defect was a scanner
    that did not return, and a gate that never closes is worse than one that says
    no. The root-cause timing pin, on the pattern itself, lives in
    `test_wp5_lead_reconciliation.py`; this is the end-to-end half.
    """
    started = time.perf_counter()
    findings = scan_gate3a({"note": "a" * width})
    elapsed = time.perf_counter() - started
    assert any(f.startswith("gate3a_oversize_text") for f in findings), findings
    assert elapsed < 1.0, f"{width} characters took {elapsed:.3f}s to refuse"


def test_fr17_a_payload_within_the_bounds_still_reaches_the_base_scrubber() -> None:
    """Negative control: the base scan is skipped only for text already refused."""
    assert "local_path:/Users/" in scan_gate3a({"note": "/Users/someone/data.jsonl"})
    assert "credential_key:token" in scan_gate3a({"token": "AKIAIOSFODNN7EXAMPLE"})


# ===========================================================================
# FR-18 — only the two functions actually used are imported
# ===========================================================================


def test_fr18_the_module_re_exports_no_second_writer() -> None:
    """Failing-before: ``artifacts.evidence.write_report`` was a live second writer.

    It applies ``assert_clean`` only, calls no ``refuse_real_path`` and overwrites
    unconditionally — so it would write into ``docs/`` and over committed evidence.
    """
    assert not hasattr(artifacts_module, "evidence")
    assert not hasattr(artifacts_module, "write_report")
    exported_writers = [
        name for name in dir(artifacts_module) if "write" in name and not name.startswith("__")
    ]
    assert exported_writers == ["write_metadata_artifact"]


def test_fr18_the_two_imported_names_are_the_two_that_are_used() -> None:
    from scripts.ml_step4.evidence import scan_payload, serialise

    assert artifacts_module._base_scan_payload is scan_payload
    assert artifacts_module._serialise is serialise


# ===========================================================================
# §14 — the remaining mutation survivors in this module
# ===========================================================================


def test_fr21_a_non_finite_leaf_under_a_declared_numeric_key_has_three_guards() -> None:
    """§14's worst survivor: one guard caught it and nothing else did.

    Neither ``scan_payload`` nor ``serialise`` rejects NaN, so removing that guard
    made the writer emit the non-standard ``NaN`` literal. There are now three
    independent catchers, the last of which is a property of the *bytes*.
    """
    findings = scan_gate3a({"artifact": "design_m15_inventory", "pip_size": float("nan")})
    assert "gate3a_non_finite_value:pip_size" in findings
    assert "gate3a_value_outside_committed_domain:pip_size" in findings
    assert "gate3a_non_standard_json_output:ValueError" in findings


def test_fr21_the_bytes_about_to_be_written_must_parse_as_strict_json() -> None:
    """The byte-level limb on its own, under a key with no value domain."""
    findings = scan_gate3a({"artifact": "forward_epoch_inventory", "file_count": float("inf")})
    assert "gate3a_non_standard_json_output:ValueError" in findings
    assert scan_gate3a({"artifact": "forward_epoch_inventory", "file_count": 20}) == []


@pytest.mark.parametrize("spelling", ["P A S S", "M E E T S", "R O B U S T", "V A L I D A T E D"])
def test_fr21_a_label_spelled_letter_by_letter_is_caught_by_the_whole_string_fallback(
    spelling: str,
) -> None:
    """§14: the fallback is the ONLY thing catching these; its removal survived."""
    with pytest.raises(ArtifactScrubError, match="gate3a_forbidden_status_value"):
        assert_gate3a_clean({"result": spelling})


def test_fr21_the_whole_string_fallback_discriminates() -> None:
    """Negative control on the same rule."""
    assert scan_gate3a({"result": "P A S S E D"}) == []
    assert scan_gate3a({"result": "N O T   P A S S"}) == []


# ===========================================================================
# Mandatory regression — the committed evidence must keep scanning clean
# ===========================================================================


def test_regression_every_committed_gate3a_artifact_still_scans_clean() -> None:
    """No tightening here may refuse a single byte of committed evidence."""
    root = Path(__file__).resolve().parents[2] / "artifacts" / "m15_gate3a"
    paths = sorted(root.glob("*.json"))
    assert len(paths) >= 8
    scanned = 0
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert scan_gate3a(payload, artifact=path.name) == [], path.name
        scanned += 1
    assert scanned == len(paths)


def test_regression_the_committed_artifacts_are_scanned_by_a_check_that_can_fail() -> None:
    root = Path(__file__).resolve().parents[2] / "artifacts" / "m15_gate3a"
    payload = json.loads((root / "design_m15_inventory.json").read_text(encoding="utf-8"))
    payload["required_aggregate_assertions"]["file_count"] = 1.5
    findings = scan_gate3a(payload, artifact="design_m15_inventory.json")
    assert "gate3a_non_integral_value_under_count_key:file_count" in findings


def test_regression_every_declared_schema_is_internally_consistent() -> None:
    """The new schema fields must not name a key the vocabulary does not declare."""
    from scripts.m15_gate3a.artifacts import _SCHEMAS

    for schema in _SCHEMAS:
        assert schema.numeric_keys <= schema.allowed_keys, schema.stem
        assert schema.prohibition_list_keys <= schema.allowed_keys, schema.stem
        assert schema.fractional_keys <= schema.numeric_keys, schema.stem
        assert schema.nested_block_keys <= schema.allowed_keys, schema.stem
        assert schema.block_only_keys <= schema.allowed_keys, schema.stem
        assert not (schema.nested_block_keys & schema.block_only_keys), schema.stem
        for key, domain in schema.value_domains:
            assert key in schema.numeric_keys, (schema.stem, key)
            assert domain, (schema.stem, key)


def test_regression_the_declared_numeric_budget_still_tracks_its_derivation() -> None:
    schema = artifact_schema("design_m15_inventory")
    assert schema is not None
    assert schema.max_numeric_leaves == _MAX_VALUES_PER_NUMERIC_KEY * len(schema.numeric_keys)
    assert schema.max_leaves == len(PAIRS_20) * len(schema.allowed_keys)
