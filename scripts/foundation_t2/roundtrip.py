"""Round-trip driver for the Foundation T2 harness.

Drives deposit -> observe -> restore -> compare (size + sha256) for each file
in a manifest, through a Destination interface. Used with LocalMockDestination
for CI / harness validation; the real primary destination is unavailable in
this PR so the real round-trip is never executed here.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .checksums import sha256_and_size
from .constants import (
    T2_ROUNDTRIP_MATCH_OBSERVED,
    T2_ROUNDTRIP_MISMATCH,
)
from .destination import Destination, DestinationUnavailableError


def roundtrip_file(
    destination: Destination,
    local_path: Path,
    logical_file_id: str,
    expected_sha256: str,
    expected_size: int,
    restore_dir: Path,
) -> dict[str, Any]:
    """Deposit -> observe -> restore -> compare a single file. Metadata only."""
    remote_ref = destination.deposit(local_path, logical_file_id)
    observed = destination.observe(remote_ref)
    Path(restore_dir).mkdir(parents=True, exist_ok=True)
    restored = Path(restore_dir) / f"restored_{logical_file_id}"
    destination.restore(remote_ref, restored)
    restored_sha, restored_size = sha256_and_size(restored)
    size_match = restored_size == expected_size
    checksum_match = restored_sha == expected_sha256
    return {
        "logical_file_id": logical_file_id,
        "remote_logical_reference": remote_ref,
        "remote_present": observed.get("present"),
        "deposit_status": "DEPOSITED",
        "restore_status": "RESTORED",
        "size_match": size_match,
        "checksum_match": checksum_match,
        "roundtrip_status": (
            T2_ROUNDTRIP_MATCH_OBSERVED
            if (size_match and checksum_match)
            else T2_ROUNDTRIP_MISMATCH
        ),
    }


def roundtrip_span_synthetic(
    destination: Destination,
    span_id: str,
    synthetic_files: list[dict[str, Any]],
    source_dir: Path,
    restore_dir: Path,
) -> dict[str, Any]:
    """Round-trip a span's synthetic files (harness validation, not real data)."""
    results = []
    for meta in synthetic_files:
        fid = meta["logical_file_id"]
        try:
            result = roundtrip_file(
                destination,
                Path(source_dir) / fid,
                fid,
                meta["sha256"],
                meta["size_bytes"],
                restore_dir,
            )
        except DestinationUnavailableError as exc:
            result = {
                "logical_file_id": fid,
                "deposit_status": "NOT_PERFORMED",
                "restore_status": "NOT_PERFORMED",
                "roundtrip_status": str(exc),
            }
        results.append(result)
    all_match = bool(results) and all(
        r.get("size_match") and r.get("checksum_match") for r in results
    )
    return {
        "span_id": span_id,
        "synthetic": True,
        "files": results,
        "all_files_matched": all_match,
    }
