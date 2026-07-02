"""Foundation T2 evidence scrubbing + writing tests."""

from __future__ import annotations

import json

import pytest

from scripts.foundation_t2.evidence import build_roundtrip_report, write_evidence
from scripts.foundation_t2.manifest import build_deposit_manifest
from scripts.foundation_t2.scrub import EvidenceScrubError, assert_clean, scan_payload


@pytest.mark.parametrize(
    "payload",
    [
        {"path": "C:\\Users\\yukik\\secret"},
        {"home": "/Users/yukik/x"},
        {"home": "/home/user/x"},
        {"url": "https://bucket.example/obj?X-Amz-Signature=abc&X-Amz-Credential=z"},
        {"auth": "Bearer eyJabc.def.ghi"},
        {"creds": {"aws_secret_access_key": "AKIA..."}},
        {"row": {"bid_o": 1.1, "ask_o": 1.2}},
        {"results": {"sharpe": 1.2}},
        {"pnl": 100.0},
        {"label": "PASS"},
        {"claim": "byte_admissibility_approved now"},
        {"note": "production_ready"},
    ],
)
def test_scrubber_rejects_dirty(payload):
    assert scan_payload(payload)  # non-empty findings
    with pytest.raises(EvidenceScrubError):
        assert_clean(payload)


def test_scrubber_accepts_clean_metadata():
    clean = {
        "run_id": "t2-x",
        "destination_logical_alias": "T2_PRIMARY_R2",
        "spans": [
            {
                "span_id": "365d_BA",
                "files": [
                    {
                        "logical_file_id": "candles_A_M1_365d_BA.jsonl",
                        "size_bytes": 10,
                        "sha256": "ab" * 32,
                    }
                ],
            }
        ],
        "statuses": ["T2_EXECUTION_STOPPED_BEFORE_DEPOSIT", "BYTE_ADMISSIBILITY_NOT_APPROVED"],
    }
    assert scan_payload(clean) == []
    assert_clean(clean)


def test_write_evidence_writes_four_scrubbed_files(tmp_path):
    repo_root = __import__("pathlib").Path(__file__).resolve().parents[2]
    manifest = build_deposit_manifest(repo_root, "t2-evidence-test")
    report = build_roundtrip_report(
        "t2-evidence-test",
        manifest,
        git_sha="deadbeef",
        base_master_sha="cafe",
        generated_at="2026-07-02T00:00:00Z",
        authorisation_reference="unit-test-authorisation",
        real_deposit_status="T2_EXECUTION_STOPPED_BEFORE_DEPOSIT",
        top_level_status="T2_EXECUTION_STOPPED_BEFORE_DEPOSIT",
        retention_probe_status="RETENTION_PROBE_REMAINS_UNRESOLVED",
        per_span=[
            {
                "span_id": b["span_id"],
                "deposit_status": "NOT_PERFORMED",
                "restore_status": "NOT_PERFORMED",
                "roundtrip_status": "NOT_PERFORMED",
            }
            for b in manifest["spans"]
        ],
        extra_statuses=["T2_CREDENTIALS_UNAVAILABLE"],
    )
    paths = write_evidence(tmp_path / "run", manifest, report, "# clean md\n")
    assert len(paths) == 4
    clean = json.loads(__import__("pathlib").Path(paths["cleanliness"]).read_text())
    assert clean["clean"] is True


def test_write_evidence_rejects_local_path_in_markdown(tmp_path):
    repo_root = __import__("pathlib").Path(__file__).resolve().parents[2]
    manifest = build_deposit_manifest(repo_root, "t2-md-test")
    report = build_roundtrip_report(
        "t2-md-test",
        manifest,
        git_sha=None,
        base_master_sha=None,
        generated_at=None,
        authorisation_reference="x",
        real_deposit_status="T2_EXECUTION_STOPPED_BEFORE_DEPOSIT",
        top_level_status="T2_EXECUTION_STOPPED_BEFORE_DEPOSIT",
        retention_probe_status="RETENTION_PROBE_REMAINS_UNRESOLVED",
        per_span=[],
        extra_statuses=[],
    )
    with pytest.raises(EvidenceScrubError):
        write_evidence(tmp_path / "run", manifest, report, "path: C:\\Users\\yukik\\x\n")
