"""Deposit-manifest builder for the Foundation T2 harness.

The manifest is derived from committed PR-B.1 raw-inventory metadata (read-only
JSON) — NOT from raw candle data. It records, per span, the logical file IDs
(basenames only), byte sizes, and PR-B.1-captured SHA-256 checksums that a
future real deposit would cover. It contains no raw rows and no local paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .constants import PR_B1_RAW_INVENTORY, T2_CONTRACT_VERSION, T2_SPANS


class T2ManifestError(ValueError):
    """Raised when a span's approved file set cannot be unambiguously built."""


def _span_files_from_pr_b1(repo_root: Path, span: str) -> list[dict[str, Any]]:
    rel = PR_B1_RAW_INVENTORY.get(span)
    if rel is None:
        raise T2ManifestError(f"span '{span}' has no PR-B.1 evidence mapping")
    path = repo_root / rel
    if not path.exists():
        raise T2ManifestError(f"PR-B.1 evidence missing for span '{span}': {rel}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    files: list[dict[str, Any]] = []
    for entry in payload.get("files", []):
        if not entry.get("present"):
            raise T2ManifestError(f"span '{span}' file '{entry.get('filename')}' not present")
        filename = entry.get("filename")
        size = entry.get("size_bytes")
        checksum = entry.get("file_sha256")
        if not filename or size is None or not checksum:
            raise T2ManifestError(f"span '{span}' file entry incomplete: {filename}")
        files.append(
            {
                "logical_file_id": filename,  # basename only, machine-independent
                "size_bytes": int(size),
                "sha256": checksum,
                "checksum_source": "pr_b1_committed_metadata",
            }
        )
    if not files:
        raise T2ManifestError(f"span '{span}' has no files in PR-B.1 evidence")
    return files


def build_deposit_manifest(
    repo_root: str | Path,
    manifest_id: str,
    *,
    spans: tuple[str, ...] = T2_SPANS,
) -> dict[str, Any]:
    """Build a metadata-only multi-span deposit manifest from PR-B.1 evidence."""
    repo_root = Path(repo_root)
    span_blocks = []
    total_files = 0
    for span in spans:
        files = _span_files_from_pr_b1(repo_root, span)
        total_files += len(files)
        span_blocks.append(
            {
                "span_id": span,
                "pr_b1_evidence_reference": PR_B1_RAW_INVENTORY[span],
                "file_count": len(files),
                "files": files,
            }
        )
    return {
        "manifest_id": manifest_id,
        "contract_version": T2_CONTRACT_VERSION,
        "checksum_algorithm": "sha256",
        "checksum_source": "pr_b1_committed_metadata (no raw data re-read)",
        "spans": span_blocks,
        "total_file_count": total_files,
    }
