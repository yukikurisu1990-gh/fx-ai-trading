"""Metadata-only evidence builder + writer for the Foundation T2 harness.

Every evidence artifact is scrubbed (fail-closed) before write. Reports carry
the non-authorisation statuses and never claim byte-admissibility, new-epoch
adoption, ML Step 4, or production readiness.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import (
    NON_AUTHORISATION_STATUSES,
    PRIMARY_DESTINATION_ALIAS,
    T2_CONTRACT_VERSION,
    T2_EVIDENCE_METADATA_ONLY,
    T2_EVIDENCE_SCRUBBED,
    T2_MULTI_SPAN_MANIFEST_PREPARED,
)
from .scrub import EvidenceScrubError, assert_clean, cleanliness_report

_MANIFEST_FILE = "t2_manifest.json"
_REPORT_JSON = "t2_roundtrip_report.json"
_REPORT_MD = "t2_roundtrip_report.md"
_CLEANLINESS_FILE = "evidence_cleanliness_report.json"


def build_roundtrip_report(
    run_id: str,
    manifest: dict[str, Any],
    *,
    git_sha: str | None,
    base_master_sha: str | None,
    generated_at: str | None,
    authorisation_reference: str,
    real_deposit_status: str,
    top_level_status: str,
    retention_probe_status: str,
    per_span: list[dict[str, Any]],
    extra_statuses: list[str],
) -> dict[str, Any]:
    """Assemble the metadata-only T2 round-trip report payload."""
    return {
        "run_id": run_id,
        "contract_version": T2_CONTRACT_VERSION,
        "git_sha": git_sha,
        "base_master_sha": base_master_sha,
        "generated_at": generated_at,
        "operator_authorisation_reference": authorisation_reference,
        "destination_logical_alias": PRIMARY_DESTINATION_ALIAS,
        "manifest_id": manifest["manifest_id"],
        "target_spans": [b["span_id"] for b in manifest["spans"]],
        "top_level_status": top_level_status,
        "real_cloud_deposit_status": real_deposit_status,
        "retention_probe_status": retention_probe_status,
        "per_span_status": per_span,
        "backup_hdd": "NOT_EXECUTED_DEFERRED",
        "ipfs_sidecar": "NOT_EXECUTED_DEFERRED",
        "statuses": [
            T2_MULTI_SPAN_MANIFEST_PREPARED,
            T2_EVIDENCE_METADATA_ONLY,
            T2_EVIDENCE_SCRUBBED,
            *extra_statuses,
            *NON_AUTHORISATION_STATUSES,
        ],
        "notice": (
            "Foundation T2 round-trip harness + pre-deposit stop evidence. "
            "Execution stopped before deposit: NO deposit, NO restore/download, "
            "and NO round-trip verification were performed, so the retention "
            "probe remains UNRESOLVED. Metadata-only evidence; no raw rows, "
            "credentials, env values, signed URLs, tokens, or local absolute "
            "paths. SHA-256 values are copied from committed PR-B.1 metadata; "
            "they were not recomputed and no raw candidate bytes were read. No "
            "byte-admissibility approval, no new-epoch adoption, no ML Step 4, "
            "no production change, no model / backtest / trading metric."
        ),
    }


def write_evidence(
    output_dir: str | Path,
    manifest: dict[str, Any],
    report: dict[str, Any],
    markdown: str,
) -> dict[str, str]:
    """Scrub then write the four metadata-only evidence artifacts."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    assert_clean(manifest)
    assert_clean(report)
    if any(bad in markdown for bad in ("C:\\", "/Users/", "/home/", "AppData")):
        raise EvidenceScrubError("markdown contains a local/personal path")

    clean = cleanliness_report({"manifest": manifest, "report": report})
    if not clean["clean"]:
        raise EvidenceScrubError(f"combined evidence not clean: {clean['findings']}")

    (output_dir / _MANIFEST_FILE).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / _REPORT_JSON).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / _REPORT_MD).write_text(markdown, encoding="utf-8")
    (output_dir / _CLEANLINESS_FILE).write_text(
        json.dumps(clean, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "manifest": str(output_dir / _MANIFEST_FILE),
        "report_json": str(output_dir / _REPORT_JSON),
        "report_md": str(output_dir / _REPORT_MD),
        "cleanliness": str(output_dir / _CLEANLINESS_FILE),
    }
