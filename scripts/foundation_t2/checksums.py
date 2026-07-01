"""Streaming checksum + size helpers for the Foundation T2 harness."""

from __future__ import annotations

import hashlib
from pathlib import Path

_BLOCK = 8 * 1024 * 1024  # 8 MB streaming block (bounded memory)


def sha256_and_size(path: str | Path) -> tuple[str, int]:
    """Return (sha256_hex, size_bytes) for a file, streamed in bounded memory."""
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as handle:
        while True:
            block = handle.read(_BLOCK)
            if not block:
                break
            size += len(block)
            digest.update(block)
    return digest.hexdigest(), size


def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
