"""Inventory + checksum verifier tests (synthetic temp files only)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.ml_step4 import contract, inventory


def _write(path: Path, data: bytes) -> tuple[str, int]:
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest(), len(data)


def _make_inventory(tmp: Path, n: int) -> tuple[Path, list[dict], dict[str, Path]]:
    files: list[dict] = []
    paths: dict[str, Path] = {}
    for i in range(n):
        name = f"candles_PAIR{i:02d}_M1_365d_BA.jsonl"
        p = tmp / name
        sha, size = _write(p, f"row-{i}".encode() * (i + 1))
        files.append({"filename": name, "file_sha256": sha, "size_bytes": size})
        paths[name] = p
    inv_path = tmp / "inv.json"
    inv_path.write_text(json.dumps({"candidate_id": "365d_BA", "files": files}), encoding="utf-8")
    return inv_path, files, paths


def test_resolve_synthetic_inventory(tmp_path: Path) -> None:
    inv_path, files, _ = _make_inventory(tmp_path, 3)
    total = sum(f["size_bytes"] for f in files)
    records = inventory.resolve_inventory(inv_path, expected_count=3, expected_total_bytes=total)
    assert [r.filename for r in records] == sorted(f["filename"] for f in files)


def test_resolve_fails_on_wrong_count(tmp_path: Path) -> None:
    inv_path, files, _ = _make_inventory(tmp_path, 3)
    total = sum(f["size_bytes"] for f in files)
    with pytest.raises(inventory.InventoryError):
        inventory.resolve_inventory(inv_path, expected_count=5, expected_total_bytes=total)


def test_resolve_fails_on_wrong_total_bytes(tmp_path: Path) -> None:
    inv_path, files, _ = _make_inventory(tmp_path, 3)
    with pytest.raises(inventory.InventoryError):
        inventory.resolve_inventory(inv_path, expected_count=3, expected_total_bytes=999999)


def test_resolve_fails_on_duplicate_filename(tmp_path: Path) -> None:
    files = [
        {"filename": "dup.jsonl", "file_sha256": "a" * 64, "size_bytes": 1},
        {"filename": "dup.jsonl", "file_sha256": "b" * 64, "size_bytes": 1},
    ]
    inv_path = tmp_path / "inv.json"
    inv_path.write_text(json.dumps({"files": files}), encoding="utf-8")
    with pytest.raises(inventory.InventoryError):
        inventory.resolve_inventory(inv_path, expected_count=2, expected_total_bytes=2)


def test_verify_files_all_match(tmp_path: Path) -> None:
    inv_path, files, paths = _make_inventory(tmp_path, 4)
    total = sum(f["size_bytes"] for f in files)
    records = inventory.resolve_inventory(inv_path, expected_count=4, expected_total_bytes=total)
    report = inventory.verify_files(records, lambda name: paths[name])
    assert report["result"] == "ALL_FILES_MATCH_INVENTORY"
    assert report["sha256_mismatches"] == 0
    assert report["total_bytes_match"] is True
    assert all(r["sha256_match"] and r["size_match"] for r in report["per_file"])


def test_verify_files_fails_on_mismatch(tmp_path: Path) -> None:
    inv_path, files, paths = _make_inventory(tmp_path, 3)
    total = sum(f["size_bytes"] for f in files)
    records = inventory.resolve_inventory(inv_path, expected_count=3, expected_total_bytes=total)
    # Corrupt one runtime file after inventory was built.
    corrupt = records[0].filename
    paths[corrupt].write_bytes(b"tampered-content-different-length")
    with pytest.raises(inventory.InventoryError):
        inventory.verify_files(records, lambda name: paths[name])


def test_verify_files_fails_on_missing(tmp_path: Path) -> None:
    inv_path, files, paths = _make_inventory(tmp_path, 3)
    total = sum(f["size_bytes"] for f in files)
    records = inventory.resolve_inventory(inv_path, expected_count=3, expected_total_bytes=total)
    paths[records[0].filename].unlink()
    with pytest.raises(inventory.InventoryError):
        inventory.verify_files(records, lambda name: paths[name])


def test_committed_365d_inventory_resolves_metadata_only() -> None:
    """Metadata-only wiring check against the real committed PR-B.1 inventory."""
    if not Path(contract.PR_B1_INVENTORY_PATH).is_file():  # pragma: no cover
        pytest.skip("committed inventory not present in this checkout")
    records = inventory.resolve_inventory()
    assert len(records) == contract.EXPECTED_FILE_COUNT
    assert sum(r.size_bytes for r in records) == contract.EXPECTED_TOTAL_BYTES
