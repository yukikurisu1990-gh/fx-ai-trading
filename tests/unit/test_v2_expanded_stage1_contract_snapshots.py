"""Stage 1 unit tests — contract-snapshot loader + classifications + wording registry."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts._verification_harness import contract_snapshots as CS  # noqa: N812


def test_snapshot_files_registry_has_six():
    assert len(CS.SENTINEL_SNAPSHOT_FILES) == 6
    sids = [s[0] for s in CS.SENTINEL_SNAPSHOT_FILES]
    assert sids == ["S-1", "S-2", "S-3", "S-4", "S-5", "S-6"]


def test_load_all_snapshots_returns_six_with_shas():
    snapshots = CS.load_all_snapshots()
    assert len(snapshots) == 6
    for snap in snapshots:
        assert snap.sentinel_id in ("S-1", "S-2", "S-3", "S-4", "S-5", "S-6")
        assert len(snap.content_sha256) == 64  # SHA-256 hex
        assert snap.n_bytes > 0


def test_snapshots_persist_to_manifest(tmp_path: Path):
    snapshots = CS.load_all_snapshots()
    out = tmp_path / "manifests" / "contract_snapshot_hashes.json"
    CS.write_snapshot_hashes_manifest(snapshots, out)
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "v2-expanded-1.0"
    assert len(payload["snapshots"]) == 6


def test_assert_snapshots_stable_passes_on_same():
    snapshots = CS.load_all_snapshots()
    CS.assert_snapshots_stable(snapshots, snapshots)


def test_assert_snapshots_stable_halts_on_drift():
    snapshots = CS.load_all_snapshots()
    mutated = [
        CS.ContractSnapshot(
            sentinel_id=s.sentinel_id,
            file_name=s.file_name,
            abs_path=s.abs_path,
            content_sha256="0" * 64 if s.sentinel_id == "S-1" else s.content_sha256,
            n_bytes=s.n_bytes,
        )
        for s in snapshots
    ]
    with pytest.raises(CS.ContractSnapshotError):
        CS.assert_snapshots_stable(snapshots, mutated)


# ---------------------------------------------------------------------------
# Compatibility classifications (from PR #358 companion review)
# ---------------------------------------------------------------------------


def test_compatibility_classifications_uniform_case_b():
    for sid in ("S-1", "S-2", "S-3", "S-4", "S-5", "S-6"):
        cls = CS.COMPATIBILITY_CLASSIFICATIONS[sid]
        assert cls["test_touched_once"] == "HISTORIC_TEST_TOUCHED_ONCE_COMPATIBLE"
        assert cls["data_identity"] == "HISTORIC_DATA_IDENTITY_NOT_PROVABLE"
        assert cls["permitted_wording"] == "CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY"


def test_write_compatibility_classification_artifact(tmp_path: Path):
    out = tmp_path / "historic_compatibility_classification.json"
    CS.write_compatibility_classification_artifact(out)
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "v2-expanded-1.0"
    assert len(payload["classifications"]) == 6


# ---------------------------------------------------------------------------
# Wording registry
# ---------------------------------------------------------------------------


def test_permitted_per_sentinel_wording():
    assert CS.PERMITTED_PER_SENTINEL_WORDING == "CURRENT_MANIFEST_CLEAN_REEXECUTION_ONLY"


def test_permitted_aggregate_wording_contains_required_phrase():
    assert "clean re-execution" in CS.PERMITTED_AGGREGATE_WORDING
    assert "V2-expanded" in CS.PERMITTED_AGGREGATE_WORDING
    assert "provenance-bound dataset" in CS.PERMITTED_AGGREGATE_WORDING


def test_forbidden_wording_registry_complete():
    for required_forbidden in (
        "historical execution verified",
        "historic verdict reproduced",
        "prior verdict revalidated",
        "tabular evidence reconfirmed",
        "PASS_TABULAR_EVIDENCE_RECONFIRMED",
        "FULL_TABULAR_EVIDENCE_REBUILT",
    ):
        assert required_forbidden in CS.FORBIDDEN_WORDINGS


def test_assert_wording_not_forbidden_passes_on_permitted_aggregate():
    CS.assert_wording_not_forbidden(CS.PERMITTED_AGGREGATE_WORDING)


def test_assert_wording_not_forbidden_halts_on_forbidden():
    text = "this run shows historical execution verified across all 9 PRs"
    with pytest.raises(CS.ContractSnapshotError):
        CS.assert_wording_not_forbidden(text)


def test_assert_wording_not_forbidden_halts_on_pass_tabular_label():
    with pytest.raises(CS.ContractSnapshotError):
        CS.assert_wording_not_forbidden("Outcome: PASS_TABULAR_EVIDENCE_RECONFIRMED")
