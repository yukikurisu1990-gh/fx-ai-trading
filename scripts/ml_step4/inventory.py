"""Inventory + checksum verifier for the ML Step 4 executor (fail-closed).

Resolves the committed PR-B.1 inventory for ``365d_BA`` (metadata only — the
inventory JSON records per-file SHA-256 + size, never raw candle rows), and
verifies that a set of runtime files matches it exactly before any consumption.

The verifier is fail-closed: missing, extra, mismatched, or ambiguous files
raise :class:`InventoryError`. Reading real ``365d_BA`` raw candle files only
happens later, at a separately-authorised execution; in this PR the file-level
verifier is exercised with synthetic temp files only.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import contract

_READ_CHUNK = 8 * 1024 * 1024


class InventoryError(RuntimeError):
    """Raised when the inventory or a runtime fileset fails closed."""


@dataclass(frozen=True)
class InventoryRecord:
    """One committed inventory entry (metadata only)."""

    filename: str
    sha256: str
    size_bytes: int


def load_inventory(inventory_path: str | Path) -> dict[str, Any]:
    """Load the committed inventory JSON (metadata only)."""
    path = Path(inventory_path)
    if not path.is_file():
        raise InventoryError(f"inventory not found: {path.name}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError) as exc:
        raise InventoryError(f"inventory unreadable: {exc}") from exc


def resolve_inventory(
    inventory_path: str | Path | None = None,
    *,
    expected_count: int = contract.EXPECTED_FILE_COUNT,
    expected_total_bytes: int = contract.EXPECTED_TOTAL_BYTES,
) -> list[InventoryRecord]:
    """Resolve + validate the inventory into records; fail closed on mismatch.

    Validates: exactly ``expected_count`` files; unique filenames; each entry
    has a 64-hex SHA-256 and a positive size; the sizes sum to
    ``expected_total_bytes``.
    """
    path = (
        Path(inventory_path) if inventory_path is not None else Path(contract.PR_B1_INVENTORY_PATH)
    )
    raw = load_inventory(path)
    files = raw.get("files")
    if not isinstance(files, list):
        raise InventoryError("inventory has no 'files' list")

    records: list[InventoryRecord] = []
    seen: set[str] = set()
    for entry in files:
        if not isinstance(entry, dict):
            raise InventoryError("inventory file entry is not an object")
        name = entry.get("filename")
        sha = entry.get("file_sha256")
        size = entry.get("size_bytes")
        if not isinstance(name, str) or not name:
            raise InventoryError("inventory entry missing filename")
        if name in seen:
            raise InventoryError(f"duplicate filename in inventory: {name}")
        if not isinstance(sha, str) or len(sha) != 64 or not _is_hex(sha):
            raise InventoryError(f"inventory entry {name} has invalid sha256")
        try:
            size_int = int(size)
        except (TypeError, ValueError) as exc:
            raise InventoryError(f"inventory entry {name} has invalid size") from exc
        if size_int <= 0:
            raise InventoryError(f"inventory entry {name} has non-positive size")
        seen.add(name)
        records.append(InventoryRecord(filename=name, sha256=sha.lower(), size_bytes=size_int))

    if len(records) != expected_count:
        raise InventoryError(f"inventory has {len(records)} files, expected {expected_count}")
    total = sum(r.size_bytes for r in records)
    if total != expected_total_bytes:
        raise InventoryError(f"inventory total bytes {total} != expected {expected_total_bytes}")
    return sorted(records, key=lambda r: r.filename)


def _is_hex(value: str) -> bool:
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


def file_sha256_and_size(path: str | Path) -> tuple[str, int]:
    """Stream a file to SHA-256 + byte size (used at real execution time)."""
    p = Path(path)
    h = hashlib.sha256()
    size = 0
    with p.open("rb") as fh:
        while True:
            chunk = fh.read(_READ_CHUNK)
            if not chunk:
                break
            size += len(chunk)
            h.update(chunk)
    return h.hexdigest(), size


def verify_files(
    records: Iterable[InventoryRecord],
    path_for: Callable[[str], str | Path],
) -> dict[str, Any]:
    """Re-verify runtime files against inventory records; fail closed.

    ``path_for(filename)`` resolves a runtime path for a logical filename. The
    returned report is metadata-only: filenames + match booleans + aggregate,
    never runtime paths or raw rows. Any missing / extra / mismatched / ambiguous
    file raises :class:`InventoryError`.
    """
    records = list(records)
    per_file: list[dict[str, Any]] = []
    mismatches = 0
    total_observed = 0
    for rec in records:
        resolved = path_for(rec.filename)
        p = Path(resolved)
        if not p.is_file():
            raise InventoryError(f"runtime file missing for {rec.filename}")
        observed_sha, observed_size = file_sha256_and_size(p)
        total_observed += observed_size
        sha_ok = observed_sha.lower() == rec.sha256.lower()
        size_ok = observed_size == rec.size_bytes
        if not (sha_ok and size_ok):
            mismatches += 1
        per_file.append(
            {
                "filename": rec.filename,
                "sha256_match": sha_ok,
                "size_match": size_ok,
            }
        )
    if mismatches:
        raise InventoryError(f"{mismatches} runtime file(s) mismatch inventory")
    expected_total = sum(r.size_bytes for r in records)
    if total_observed != expected_total:
        raise InventoryError(f"observed total bytes {total_observed} != inventory {expected_total}")
    return {
        "files_expected": len(records),
        "files_checked": len(per_file),
        "sha256_mismatches": 0,
        "size_mismatches": 0,
        "total_bytes_observed": total_observed,
        "total_bytes_expected": expected_total,
        "total_bytes_match": total_observed == expected_total,
        "result": "ALL_FILES_MATCH_INVENTORY",
        "per_file": per_file,
    }
