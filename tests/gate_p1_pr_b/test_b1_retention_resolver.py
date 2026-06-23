"""PR-B.1 retention feasibility + resolver tests (plan §6.2, §8)."""

from __future__ import annotations

import json

import pytest

from scripts._gate_p1_inspector.authority import pair_universe as pu
from scripts._gate_p1_inspector.authority import schema as sa
from scripts._gate_p1_inspector.b1_constants import (
    OANDA_ARCHIVE_MANIFEST_RELPATH,
    OUTCOME_INSUFFICIENT,
    OUTCOME_PARTIAL,
    OUTCOME_RETENTION_UNRESOLVED,
    RETENTION_REQUIRES_PROBE,
    RETENTION_UNRESOLVED,
)
from scripts._gate_p1_inspector.inspector import resolver as resolver_mod
from scripts._gate_p1_inspector.inspector import retention as retention_mod

_PAIRS = ["EUR_USD", "GBP_USD"]
_GOOD_FILES = [
    {"pair": "EUR_USD", "present": True, "schema_valid": True, "size_bytes": 100, "row_count": 5},
    {"pair": "GBP_USD", "present": True, "schema_valid": True, "size_bytes": 100, "row_count": 5},
]


def test_retention_unresolved_without_candidate_option(tmp_path):
    out = retention_mod.assess_retention(
        "365d", _GOOD_FILES, first_run_mode=True, repo_root=tmp_path
    )
    assert out["retention_classification"] == RETENTION_UNRESOLVED
    assert out["in_repo_retention_within_guard"] is False
    assert out["existing_local_immutable_archive_visible_read_only"] is False
    assert out["candidate_retention_options_requiring_later_authorisation"] == []


def test_retention_requires_probe_when_archive_present(tmp_path):
    manifest = tmp_path / OANDA_ARCHIVE_MANIFEST_RELPATH
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"note": "synthetic manifest presence only"}), encoding="utf-8")
    out = retention_mod.assess_retention(
        "365d", _GOOD_FILES, first_run_mode=True, repo_root=tmp_path
    )
    assert out["retention_classification"] == RETENTION_REQUIRES_PROBE
    assert len(out["candidate_retention_options_requiring_later_authorisation"]) == 1


def _resolve(files, retention_classification, *, pair_outcome=pu.OUTCOME_OK):
    return resolver_mod.resolve_candidate(
        "365d_BA",
        pair_outcome=pair_outcome,
        schema_outcome=sa.OUTCOME_OK,
        files=files,
        pairs=_PAIRS,
        retention_classification=retention_classification,
        first_run_mode=True,
    )


def test_resolver_partial_when_sufficient_and_probe_required():
    outcome = _resolve(_GOOD_FILES, RETENTION_REQUIRES_PROBE)
    assert outcome.outcome == OUTCOME_PARTIAL
    assert outcome.retention_substatus == RETENTION_REQUIRES_PROBE


def test_resolver_retention_unresolved_when_sufficient_and_no_destination():
    outcome = _resolve(_GOOD_FILES, RETENTION_UNRESOLVED)
    assert outcome.outcome == OUTCOME_RETENTION_UNRESOLVED


def test_resolver_insufficient_when_pair_missing():
    files = [
        {"pair": "EUR_USD", "present": True, "schema_valid": True},
        {"pair": "GBP_USD", "present": False, "schema_valid": False},
    ]
    outcome = _resolve(files, RETENTION_UNRESOLVED)
    assert outcome.outcome == OUTCOME_INSUFFICIENT


def test_resolver_pass_is_structurally_unreachable():
    # The two PASS-enabling retention classifications HALT under first-run.
    with pytest.raises(resolver_mod.GateP1IntegrityError):
        resolver_mod.resolve_candidate(
            "365d_BA",
            pair_outcome=pu.OUTCOME_OK,
            schema_outcome=sa.OUTCOME_OK,
            files=_GOOD_FILES,
            pairs=_PAIRS,
            retention_classification="IN_REPO_RETENTION_SIZE_FEASIBLE_PENDING_GATE_P2",
            first_run_mode=True,
        )


def test_resolver_schema_drift_halts():
    with pytest.raises(resolver_mod.GateP1IntegrityError):
        resolver_mod.resolve_candidate(
            "365d_BA",
            pair_outcome=pu.OUTCOME_OK,
            schema_outcome=sa.OUTCOME_INTEGRITY_HALT_SCHEMA_AUTHORITY_DRIFT,
            files=_GOOD_FILES,
            pairs=_PAIRS,
            retention_classification=RETENTION_UNRESOLVED,
            first_run_mode=True,
        )


def test_resolver_top_level_precedence():
    partial = resolver_mod.CandidateOutcome("a", OUTCOME_PARTIAL, RETENTION_REQUIRES_PROBE)
    unresolved = resolver_mod.CandidateOutcome(
        "b", OUTCOME_RETENTION_UNRESOLVED, RETENTION_UNRESOLVED
    )
    insufficient = resolver_mod.CandidateOutcome("c", OUTCOME_INSUFFICIENT, RETENTION_UNRESOLVED)

    assert resolver_mod.resolve_top_level([partial, unresolved], first_run_mode=True) == (
        OUTCOME_PARTIAL
    )
    assert resolver_mod.resolve_top_level([unresolved, unresolved], first_run_mode=True) == (
        OUTCOME_RETENTION_UNRESOLVED
    )
    assert resolver_mod.resolve_top_level([insufficient], first_run_mode=True) == (
        OUTCOME_INSUFFICIENT
    )
