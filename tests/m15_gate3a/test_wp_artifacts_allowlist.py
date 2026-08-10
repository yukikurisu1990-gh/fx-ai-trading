"""Per-artifact allowlist scrubber + writer — blocker B-1 and RF-6…RF-11 / RF-15 / RF-22 / RF-27.

Every accept in this file is paired with a refuse on the same rule, and every
refuse with an accept: the negative-control rule (contract Gate-decision §10 R-1)
applies to a test suite as much as to an artifact field, because a check that can
only ever report one outcome is not evidence that it discriminates.

Refusals assert the module's own :class:`ArtifactScrubError` (or
:class:`RealDataRefusedError` where the path authority owns the decision), with a
single unambiguous ``match`` — never an alternation, which is what concealed
audit B-7a for three rounds.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from scripts.m15_gate3a.artifacts import (
    EXPECTED_ARTIFACT_FILES,
    ArtifactScrubError,
    assert_gate3a_clean,
    scan_gate3a,
    validate_metadata_artifact,
    write_metadata_artifact,
)
from scripts.m15_gate3a.guards import FORBIDDEN_STATUSES, RealDataRefusedError
from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.ml_step4.evidence import repo_root

# --------------------------------------------------------------------------
# Fixtures — the shapes this gate must actually be able to write
# --------------------------------------------------------------------------


def _inventory_record(pair: str, index: int) -> dict[str, object]:
    """One realistic populated per-file inventory record.

    Eleven fields, six of them immediate numerics, plus the nested six-quantity
    missing-minute block approved by the contract Gate-decision §5 (D-3). The
    previous shape denylist refused this at six immediate numerics and refused it
    again when the block was flattened (§12.25).
    """
    return {
        "filename": f"candles_{pair}_M15_365d_BA_DESIGN.jsonl",
        "pair": pair,
        "sha256": "ab" * 32,
        "size_bytes": 4_812_345 + index,
        "row_count": 23_040,
        "complete_bucket_count": 21_500,
        "cost_hurdle_eligible_bar_count": 18_003,
        "raw_traded_event_count": 1_204,
        "pip_size": 0.01 if pair.endswith("_JPY") else 0.0001,
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


def _populated_inventory(pairs: tuple[str, ...] = PAIRS_20) -> dict[str, object]:
    return {
        "artifact": "design_m15_inventory",
        "gate": "3a",
        "status": "SCHEMA_FIXED__POPULATED_AT_IMPLEMENTATION",
        "file_count": len(pairs),
        "files": [_inventory_record(pair, i) for i, pair in enumerate(pairs)],
        "required_aggregate_assertions": {
            "all_ts_max_within_design_end": "<= 2026-02-28T23:59:59Z",
            "all_ts_min_within_design_start": ">= 2025-04-25T00:00:00Z",
            "dead_window_bars_present": 0,
        },
    }


def _scrub_report_listing_its_prohibitions() -> dict[str, object]:
    return {
        "artifact": "scrub_report",
        "gate": "3a",
        "checked_artifacts": list(EXPECTED_ARTIFACT_FILES),
        "forbidden_labels": sorted(FORBIDDEN_STATUSES),
        "assertions": {
            "raw_price_rows_committed": False,
            "predictions_committed": False,
            "model_outputs_committed": False,
            "validation_metrics_committed": False,
            "holdout_metrics_committed": False,
            "trade_level_outputs_committed": False,
            "strategy_performance_metrics_committed": False,
            "model_binaries_committed": False,
        },
        "findings": [],
    }


def _price_row(index: int) -> dict[str, float]:
    """One bid/ask bar: eight numeric sides under neutral field names."""
    base = 1.10 + index / 1e6
    return {
        "b_o": base,
        "b_h": base + 2e-5,
        "b_l": base - 2e-5,
        "b_c": base + 1e-5,
        "a_o": base + 8e-5,
        "a_h": base + 1e-4,
        "a_l": base + 6e-5,
        "a_c": base + 9e-5,
    }


# --------------------------------------------------------------------------
# B-1(a) — container shape: the same records re-keyed must not scan clean
# --------------------------------------------------------------------------


def test_b1a_row_records_are_refused_as_a_list_and_as_a_dict_of_dicts() -> None:
    """The list form always tripped; the dict-of-dicts re-keying scanned clean.

    The heuristics traversed ``list``/``tuple`` only, so re-keying 300 identical
    records under string indices was unchecked and unbounded. The replacement
    counts numeric leaves wherever they sit, which a re-encoding cannot change.
    """
    rows = [_price_row(i) for i in range(300)]
    with pytest.raises(ArtifactScrubError, match="row_like_numeric_records"):
        assert_gate3a_clean({"per_file": rows})
    with pytest.raises(ArtifactScrubError, match="numeric_cardinality_exceeded"):
        assert_gate3a_clean({"per_file": {str(i): row for i, row in enumerate(rows)}})


def test_b1a_numeric_budget_discriminates_rather_than_refusing_everything() -> None:
    """The same container shape below the budget is accepted (negative control)."""
    small = {"per_file": {str(i): float(i) for i in range(100)}}
    assert scan_gate3a(small) == []
    large = {"per_file": {str(i): float(i) for i in range(200)}}
    assert "gate3a_numeric_cardinality_exceeded" in scan_gate3a(large)


def test_b1a_declared_schema_refuses_records_it_never_declared() -> None:
    """Declaring an artifact is not a way in: the key vocabulary is the gate."""
    smuggled = {
        "artifact": "design_m15_inventory",
        "files": {str(i): _price_row(i) for i in range(300)},
    }
    with pytest.raises(ArtifactScrubError, match="undeclared_key"):
        assert_gate3a_clean(smuggled)


# --------------------------------------------------------------------------
# B-1(a) — sibling numeric series
# --------------------------------------------------------------------------


def test_b1_two_sibling_numeric_series_are_refused() -> None:
    columnar = {
        "b_c": [1.1, 1.2, 1.3, 1.4, 1.5],
        "a_c": [1.2, 1.3, 1.4, 1.5, 1.6],
    }
    with pytest.raises(ArtifactScrubError, match="columnar_numeric_series"):
        assert_gate3a_clean(columnar)
    one_series_only = {"b_c": [1.1, 1.2, 1.3, 1.4, 1.5], "note": "one series is not a dataset"}
    assert scan_gate3a(one_series_only) == []


def test_b1_sibling_numeric_series_re_keyed_out_of_lists_are_still_refused() -> None:
    """Removing the lists removes the heuristic's grip; the budget still holds."""
    re_keyed = {
        "b_c": {str(i): 1.1 + i / 1e5 for i in range(80)},
        "a_c": {str(i): 1.2 + i / 1e5 for i in range(80)},
    }
    assert not any(f.startswith("gate3a_columnar") for f in scan_gate3a(re_keyed))
    with pytest.raises(ArtifactScrubError, match="numeric_cardinality_exceeded"):
        assert_gate3a_clean(re_keyed)


# --------------------------------------------------------------------------
# B-1(b) — claim phrasing
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrasing",
    [
        "PRODUCTION_READY",
        "PRODUCTION READY: yes",
        "status=PRODUCTION_READY",
        "PRODUCTION_READY_CLAIMED",
        "PRODUCTION_READY!",
        "This machinery is production ready and cleared for live.",
    ],
)
def test_b1b_a_readiness_claim_is_refused_in_any_phrasing(phrasing: str) -> None:
    """Matching was whole-string, so every embedding of the claim scanned clean."""
    with pytest.raises(ArtifactScrubError, match="forbidden_status_value"):
        assert_gate3a_clean({"verdict": phrasing})


@pytest.mark.parametrize(
    "honest",
    [
        "buckets that pass the cost-hurdle and fire an EV-gated trade",
        "PASSED",
        "COMPASS",
        "BYPASS",
        "ROBUSTNESS",
        "PRODUCTION_READINESS_NOT_CLAIMED",
        "NO_EXECUTION_PERFORMED",
        "FORWARD_EPOCH_ADOPTION_BLOCKED_INSUFFICIENT_SAMPLE_ADOPTION_WAITS",
    ],
)
def test_b1b_substring_scanning_does_not_sweep_up_honest_wording(honest: str) -> None:
    """Ordinary English and the always-binding statuses must survive the scan."""
    assert scan_gate3a({"note": honest}) == []


def test_b1b_an_ambiguous_label_after_a_claim_connector_is_refused() -> None:
    """`status=pass` is an assertion; `pass the cost-hurdle` is a verb."""
    with pytest.raises(ArtifactScrubError, match="forbidden_status_value"):
        assert_gate3a_clean({"note": "verdict: pass"})
    assert scan_gate3a({"note": "a bucket may pass or fail the hurdle"}) == []


# --------------------------------------------------------------------------
# B-1(c) — character set
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "spelling"),
    [
        ("ascii", "PASS"),
        ("cyrillic_A", "PАSS"),
        ("zero_width_space", "PASS​"),
        ("zero_width_joiner", "PA‍SS"),
        ("soft_hyphen", "PA­SS"),
        ("fullwidth", "ＰＡＳＳ"),
        ("combining_acute", "PÁSS"),
        ("greek_rho_omicron", "ΡRΟDUCTION_READY"),
    ],
)
def test_b1c_homoglyph_and_invisible_spellings_are_refused(label: str, spelling: str) -> None:
    """NFKC folded the fullwidth forms only; homoglyphs and invisibles walked past."""
    with pytest.raises(ArtifactScrubError, match="forbidden_status_value"):
        assert_gate3a_clean({"result": spelling})


def test_b1c_the_folding_does_not_refuse_unrelated_non_ascii() -> None:
    assert scan_gate3a({"note": "市場 closure calendar — UTC only"}) == []


# --------------------------------------------------------------------------
# B-1 mirror image — the constructs the denylist wrongly refused
# --------------------------------------------------------------------------


def test_b1_a_prohibition_list_is_accepted_when_the_artifact_declares_one() -> None:
    """Playbook §10 permits these tokens inside a prohibition list — and only there."""
    report = _scrub_report_listing_its_prohibitions()
    assert len(report["forbidden_labels"]) >= len(FORBIDDEN_STATUSES)
    assert scan_gate3a(report) == []
    assert scan_gate3a(report, artifact="scrub_report.json") == []


def test_b1_the_same_labels_are_refused_where_no_schema_declares_a_prohibition_list() -> None:
    """The exemption is a declared slot, not a magic key name."""
    with pytest.raises(ArtifactScrubError, match="forbidden_status_value"):
        assert_gate3a_clean({"forbidden_labels": sorted(FORBIDDEN_STATUSES)})


def test_b1_a_populated_twenty_record_inventory_is_accepted() -> None:
    """§12.25: the continuation's own inventory must be writable before derivation."""
    inventory = _populated_inventory()
    assert len(inventory["files"]) == len(PAIRS_20) == 20
    immediate_numerics = sum(
        1
        for value in inventory["files"][0].values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    )
    assert immediate_numerics >= 6, "the shape §12.25 records as refused must be exercised"
    assert scan_gate3a(inventory) == []
    assert scan_gate3a(inventory, artifact="design_m15_inventory.json") == []


def test_b1_a_flattened_gap_report_is_also_accepted() -> None:
    """Nesting is no longer what decides admissibility — the key vocabulary is."""
    inventory = _populated_inventory()
    for record in inventory["files"]:
        record.update(record.pop("gap_report"))
    assert scan_gate3a(inventory) == []


def test_b1_an_inventory_longer_than_the_frozen_roster_is_refused() -> None:
    """The bound is the roster, so a 21st record cannot ride in (negative control)."""
    over = _populated_inventory((*PAIRS_20, "EUR_USD"))
    with pytest.raises(ArtifactScrubError, match="list_longer_than_declared"):
        assert_gate3a_clean(over)


def test_b1_a_natural_columnar_roster_is_accepted_once_declared() -> None:
    roster = {
        "artifact": "design_m15_inventory",
        "pair": list(PAIRS_20),
        "pip_size": [0.01 if p.endswith("_JPY") else 0.0001 for p in PAIRS_20],
        "file_count": len(PAIRS_20),
    }
    assert scan_gate3a(roster) == []


def test_b1_a_declared_artifact_still_refuses_metrics_and_claims() -> None:
    with pytest.raises(ArtifactScrubError, match="forbidden_key"):
        assert_gate3a_clean({"artifact": "design_m15_inventory", "sharpe_ratio": 1.2})
    with pytest.raises(ArtifactScrubError, match="forbidden_status_value"):
        assert_gate3a_clean(
            {"artifact": "scrub_report", "content_kind": "the machinery is production ready"}
        )


def test_b1_a_declared_name_must_match_the_filename_it_is_written_under() -> None:
    report = _scrub_report_listing_its_prohibitions()
    with pytest.raises(ArtifactScrubError, match="artifact_name_mismatch"):
        assert_gate3a_clean(report, artifact="design_m15_inventory.json")


def test_b1_an_unknown_artifact_name_is_reported_not_silently_ignored() -> None:
    findings = scan_gate3a({"artifact": "not_a_gate3a_artifact", "note": "x"})
    assert "gate3a_undeclared_artifact_name:not_a_gate3a_artifact" in findings


# --------------------------------------------------------------------------
# RF-6 — the artifact name is pinned character data
# --------------------------------------------------------------------------


class _TwoFacedName(str):
    """A ``str`` that answers every name check the way the caller wants."""

    def endswith(self, *args: object, **kwargs: object) -> bool:  # noqa: D102
        return True

    def __eq__(self, other: object) -> bool:
        return True

    def __ne__(self, other: object) -> bool:
        return False

    def __hash__(self) -> int:
        return hash(str.__str__(self))

    def __contains__(self, item: object) -> bool:
        return False


def test_rf6_a_two_faced_name_cannot_escape_the_output_directory(tmp_path: Path) -> None:
    """``endswith``, ``!=`` and ``in`` are all overridable; the join is not."""
    out = tmp_path / "inner"
    body = {"ok": 1}
    with pytest.raises(ArtifactScrubError, match="bare filename"):
        write_metadata_artifact(out, _TwoFacedName("../escaped.json"), body)
    assert not (tmp_path / "escaped.json").exists()
    assert not out.exists()
    honest = write_metadata_artifact(out, "ok.json", body)
    assert honest.parent == out


def test_rf6_a_non_string_name_is_refused_on_its_type(tmp_path: Path) -> None:
    body = {"ok": 1}
    with pytest.raises(ArtifactScrubError, match="must be a str"):
        write_metadata_artifact(tmp_path, 7, body)


# --------------------------------------------------------------------------
# RF-7 — forbidden metric keys are matched on word tokens, not exact strings
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    [
        "sharpe_ratio",
        "sharpeRatio",
        "net_pnl",
        "max_drawdown_pct",
        "hit_rate",
        "profit_factor",
        "expectancy_per_trade",
        "total_return",
    ],
)
def test_rf7_a_qualified_metric_key_is_refused(key: str) -> None:
    with pytest.raises(ArtifactScrubError, match="forbidden_key"):
        assert_gate3a_clean({key: 1.0})


@pytest.mark.parametrize(
    "key",
    ["raw_event_count", "trade_count_floor", "raw_holdout_trade_floor", "complete_bucket_count"],
)
def test_rf7_legitimate_committed_key_names_survive(key: str) -> None:
    assert scan_gate3a({key: 1}) == []


def test_rf7_a_metric_key_denied_by_its_value_is_a_disclaimer() -> None:
    """The committed scrub report declares exactly these, all false."""
    assert scan_gate3a({"predictions_committed": False, "model_outputs_committed": False}) == []
    with pytest.raises(ArtifactScrubError, match="forbidden_key"):
        assert_gate3a_clean({"predictions_committed": True})


# --------------------------------------------------------------------------
# RF-8 — a claim and a disclaimer are different things
# --------------------------------------------------------------------------


@pytest.mark.parametrize("denial", [False, "no", "false", "NOT_CLAIMED"])
def test_rf8_a_denied_forbidden_status_key_is_a_disclaimer(denial: object) -> None:
    assert scan_gate3a({"PRODUCTION_READY": denial}) == []


@pytest.mark.parametrize("assertion", [True, "yes", 1, 0, {"a": 1}, ["x"], None])
def test_rf8_anything_that_is_not_a_denial_is_an_assertion(assertion: object) -> None:
    with pytest.raises(ArtifactScrubError, match="forbidden_status_key"):
        assert_gate3a_clean({"PRODUCTION_READY": assertion})


# --------------------------------------------------------------------------
# RF-9 — a refused write leaves nothing behind, and raises this module's error
# --------------------------------------------------------------------------


def test_rf9_a_failure_at_the_write_leaves_no_file_and_no_directory(tmp_path: Path) -> None:
    """The over-long name failed *at* ``write_text``, after ``mkdir`` had run."""
    out = tmp_path / "created_by_the_refused_call"
    body = {"ok": 1}
    with pytest.raises(ArtifactScrubError, match="artifact write failed"):
        write_metadata_artifact(out, "a" * 300 + ".json", body)
    assert not out.exists()
    assert list(tmp_path.iterdir()) == []


def test_rf9_a_blocked_parent_directory_is_reported_as_a_scrub_error(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    out = blocker / "sub"
    body = {"ok": 1}
    with pytest.raises(ArtifactScrubError, match="artifact write failed"):
        write_metadata_artifact(out, "ok.json", body)
    assert not out.exists()
    assert blocker.read_text(encoding="utf-8") == "not a directory"


def test_rf9_a_successful_write_still_creates_what_it_needs(tmp_path: Path) -> None:
    body = {"ok": 1}
    written = write_metadata_artifact(tmp_path / "a" / "b", "ok.json", body)
    assert written.exists()
    assert json.loads(written.read_text(encoding="utf-8")) == body


# --------------------------------------------------------------------------
# D-7 / §12.17 — the writer never overwrites, and the path guard runs first
# --------------------------------------------------------------------------


def test_d7_an_existing_artifact_is_never_overwritten(tmp_path: Path) -> None:
    """Population is by human-reviewed PR diff; no code path rewrites evidence."""
    first = {"ok": 1}
    written = write_metadata_artifact(tmp_path / "out", "ok.json", first)
    second = {"ok": 2}
    with pytest.raises(ArtifactScrubError, match="refusing to overwrite"):
        write_metadata_artifact(tmp_path / "out", "ok.json", second)
    assert json.loads(written.read_text(encoding="utf-8")) == first


def test_rf15_the_writer_guarantees_it_states_actually_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RF-15: the module claimed universal protection; it has a routed refusal.

    What is asserted here is only what the corrected docstring claims — the
    refusal is routed through the path authority on both the directory and the
    joined target, and it runs before anything is created.
    """
    import scripts.m15_gate3a.guards as guards_mod

    synthetic_root = tmp_path / "fake_repo"
    (synthetic_root / "protected_stub").mkdir(parents=True)
    monkeypatch.setattr(guards_mod, "repo_root", lambda: synthetic_root)
    monkeypatch.setattr(guards_mod, "_PROTECTED_PREFIXES", ("protected_stub",))
    body = {"ok": 1}
    refused = synthetic_root / "protected_stub" / "probe"
    with pytest.raises(RealDataRefusedError):
        write_metadata_artifact(refused, "ok.json", body)
    assert not refused.exists()
    allowed = write_metadata_artifact(synthetic_root / "elsewhere", "ok.json", body)
    assert allowed.exists()


# --------------------------------------------------------------------------
# RF-10 / RF-11 — non-finite keys and payloads the writer cannot serialise
# --------------------------------------------------------------------------


def test_rf10_a_non_finite_key_is_refused_not_stringified() -> None:
    """``json.dumps`` turns a NaN key into the string ``"NaN"`` without a word."""
    with pytest.raises(ArtifactScrubError, match="non_finite_key"):
        assert_gate3a_clean({float("nan"): 1})
    with pytest.raises(ArtifactScrubError, match="non_finite_key"):
        assert_gate3a_clean({float("inf"): 1})
    with pytest.raises(ArtifactScrubError, match="non_finite_value"):
        assert_gate3a_clean({"effective_n": float("nan")})
    assert scan_gate3a({"effective_n": 383.33}) == []


@pytest.mark.parametrize(
    "payload",
    [
        {"x": {1, 2}},
        {"x": Decimal("NaN")},
        {"x": 1 + 2j},
        {1: "a", "b": 2},
    ],
)
def test_rf11_a_payload_the_writer_cannot_serialise_fails_as_a_scrub_error(
    payload: dict[object, object], tmp_path: Path
) -> None:
    """These used to reach ``write_text`` and die with a bare ``TypeError``."""
    with pytest.raises(ArtifactScrubError, match="unserialisable_payload"):
        validate_metadata_artifact(payload)
    with pytest.raises(ArtifactScrubError, match="unserialisable_payload"):
        write_metadata_artifact(tmp_path, "ok.json", payload)
    assert not (tmp_path / "ok.json").exists()


def test_a_payload_the_scanner_cannot_traverse_is_a_finding_not_a_crash() -> None:
    """The ``_UNSCANNABLE`` handler around ``scan_payload`` is reachable.

    Its source carries ``# pragma: no cover - defensive``. A payload nested
    past the interpreter's recursion limit makes ``scan_payload`` raise
    ``RecursionError``, the handler converts it to a finding, and the scrub
    refuses — so the pragma sits on a reachable guard (audit §9 AP-7, reported
    to the source workstream).
    """
    deep: dict[str, object] = {}
    cursor = deep
    for _ in range(3000):
        nested: dict[str, object] = {}
        cursor["n"] = nested
        cursor = nested
    with pytest.raises(ArtifactScrubError) as exc:
        assert_gate3a_clean(deep)
    assert "gate3a_unscannable_payload:RecursionError" in str(exc.value)


# --------------------------------------------------------------------------
# RF-22 / RF-27 — the vacuity floor
# --------------------------------------------------------------------------


@pytest.mark.parametrize("vacuous", ["PASS", 42, None, True, 1.5, b"{}", {}, []])
def test_rf27_a_non_object_or_empty_payload_is_not_a_metadata_artifact(
    vacuous: object,
) -> None:
    with pytest.raises(ArtifactScrubError):
        validate_metadata_artifact(vacuous)


def test_rf27_a_minimal_real_artifact_is_still_accepted() -> None:
    validate_metadata_artifact({"artifact": "scrub_report", "gate": "3a"})


def test_rf22_every_committed_gate3a_artifact_scans_clean() -> None:
    """Non-vacuous by construction: the roster is asserted before the loop.

    RF-22 recorded the sibling of this test passing in a tree with no artifacts
    at all. The floor here is the expected file set, not merely a count.
    """
    root = repo_root() / "artifacts" / "m15_gate3a"
    present = sorted(p.name for p in root.glob("*.json"))
    assert len(present) >= 8
    assert set(EXPECTED_ARTIFACT_FILES) <= set(present)
    scanned = 0
    for name in present:
        payload = json.loads((root / name).read_text(encoding="utf-8"))
        assert isinstance(payload, dict) and payload, name
        assert scan_gate3a(payload, artifact=name) == [], name
        scanned += 1
    assert scanned == len(present)


def test_rf22_the_committed_artifacts_are_scanned_by_a_check_that_can_fail() -> None:
    """The same call on a deliberately corrupted committed payload must refuse."""
    root = repo_root() / "artifacts" / "m15_gate3a"
    payload = json.loads((root / "scrub_report.json").read_text(encoding="utf-8"))
    payload["result"] = "PASS"
    with pytest.raises(ArtifactScrubError, match="forbidden_status_value"):
        assert_gate3a_clean(payload, artifact="scrub_report.json")


# --------------------------------------------------------------------------
# R-1 (§12.19) — the negative-control rule applied to what this module emits
# --------------------------------------------------------------------------


def test_r1_the_module_mints_no_one_valued_self_attestation() -> None:
    """A ``clean`` flag beside a fixed ``checks`` list is a field R-1 deletes.

    :func:`scan_gate3a` returns the findings themselves and both of its outcomes
    are reachable, so nothing here reports a property that cannot take the other
    value.
    """
    import scripts.m15_gate3a.artifacts as artifacts_module

    assert not hasattr(artifacts_module, "cleanliness_report")
    assert scan_gate3a({"artifact": "scrub_report", "gate": "3a"}) == []
    assert scan_gate3a({"artifact": "scrub_report", "result": "PASS"}) != []


def test_r1_the_expected_file_list_is_derived_and_has_a_consumer() -> None:
    """The literal tuple had neither consumer nor test; it is now the schema table."""
    from scripts.m15_gate3a.artifacts import artifact_schema

    assert len(EXPECTED_ARTIFACT_FILES) == 8
    assert len(set(EXPECTED_ARTIFACT_FILES)) == len(EXPECTED_ARTIFACT_FILES)
    for filename in EXPECTED_ARTIFACT_FILES:
        assert filename.endswith(".json")
        schema = artifact_schema(filename)
        assert schema is not None, filename
        assert schema.filename == filename
        assert schema.numeric_keys <= schema.allowed_keys
    assert artifact_schema("not_a_gate3a_artifact.json") is None
