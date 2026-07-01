"""Foundation T2 manifest tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.foundation_t2.constants import T2_SPANS
from scripts.foundation_t2.manifest import T2ManifestError, build_deposit_manifest

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_manifest_from_committed_pr_b1_metadata():
    m = build_deposit_manifest(REPO_ROOT, "unit-manifest")
    assert [b["span_id"] for b in m["spans"]] == list(T2_SPANS)
    assert m["checksum_algorithm"] == "sha256"
    for block in m["spans"]:
        assert block["file_count"] == 20  # 20 pairs per span in PR-B.1 evidence
        for f in block["files"]:
            assert set(f) >= {"logical_file_id", "size_bytes", "sha256"}
            assert f["logical_file_id"].endswith(".jsonl")  # basename only
            assert ":" not in f["logical_file_id"]  # no drive-letter path


def test_manifest_from_synthetic_repo(tmp_path, synthetic_pr_b1_repo):
    synthetic_pr_b1_repo(tmp_path, pairs=2)
    m = build_deposit_manifest(tmp_path, "syn-manifest")
    assert m["total_file_count"] == 6  # 3 spans x 2 pairs
    assert m["spans"][0]["files"][0]["checksum_source"] == "pr_b1_committed_metadata"


def test_manifest_missing_evidence_stops(tmp_path):
    with pytest.raises(T2ManifestError):
        build_deposit_manifest(tmp_path, "missing")


def test_manifest_incomplete_entry_stops(tmp_path, synthetic_pr_b1_repo):
    import json

    synthetic_pr_b1_repo(tmp_path, pairs=1)
    bad = tmp_path / "artifacts/gate_p1_pr_b/firstrun_365d_ba/raw_inventory_365d_BA.json"
    payload = json.loads(bad.read_text())
    del payload["files"][0]["file_sha256"]
    bad.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(T2ManifestError):
        build_deposit_manifest(tmp_path, "incomplete")
