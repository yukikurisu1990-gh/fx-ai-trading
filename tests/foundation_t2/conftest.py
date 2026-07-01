"""Shared synthetic helpers for Foundation T2 tests (no real data / cloud)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


def _sha256_size(data: bytes) -> tuple[str, int]:
    return hashlib.sha256(data).hexdigest(), len(data)


@pytest.fixture
def synthetic_span_files():
    """Create a few tiny synthetic files; return (source_dir, files_meta)."""

    def _make(source_dir: Path, n: int = 3):
        source_dir.mkdir(parents=True, exist_ok=True)
        files = []
        for i in range(n):
            fid = f"synthetic_span_file_{i}.bin"
            data = f"synthetic-bytes-{i}".encode() * (i + 1)
            (source_dir / fid).write_bytes(data)
            sha, size = _sha256_size(data)
            files.append({"logical_file_id": fid, "sha256": sha, "size_bytes": size})
        return files

    return _make


@pytest.fixture
def synthetic_pr_b1_repo():
    """Write a synthetic repo root with a PR-B.1-shaped raw_inventory per span."""

    def _make(repo_root: Path, spans=("365d_BA", "730d_BA", "3650d_BA"), pairs=2):
        for span in spans:
            low = span.lower()
            d = repo_root / "artifacts" / "gate_p1_pr_b" / f"firstrun_{low}"
            d.mkdir(parents=True, exist_ok=True)
            files = []
            for p in range(pairs):
                data = f"{span}-pair-{p}".encode()
                sha, size = _sha256_size(data)
                files.append(
                    {
                        "pair": f"P{p}",
                        "filename": f"candles_P{p}_M1_{span}.jsonl",
                        "present": True,
                        "size_bytes": size,
                        "file_sha256": sha,
                    }
                )
            (d / f"raw_inventory_{span}.json").write_text(
                json.dumps({"candidate_id": span, "files": files}), encoding="utf-8"
            )

    return _make
