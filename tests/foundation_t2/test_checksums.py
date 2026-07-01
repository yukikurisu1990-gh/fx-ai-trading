"""Foundation T2 checksum helper tests."""

from __future__ import annotations

import hashlib

from scripts.foundation_t2.checksums import sha256_and_size, sha256_of_bytes


def test_sha256_and_size_matches_reference(tmp_path):
    data = b"foundation-t2-synthetic" * 100
    p = tmp_path / "f.bin"
    p.write_bytes(data)
    sha, size = sha256_and_size(p)
    assert size == len(data)
    assert sha == hashlib.sha256(data).hexdigest()


def test_sha256_and_size_deterministic(tmp_path):
    p = tmp_path / "f.bin"
    p.write_bytes(b"abc" * 1000)
    assert sha256_and_size(p) == sha256_and_size(p)


def test_sha256_of_bytes():
    assert sha256_of_bytes(b"x") == hashlib.sha256(b"x").hexdigest()
