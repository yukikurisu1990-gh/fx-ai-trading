"""ULID generation utility (D1 §6.4 / M8).

ULID (Universally Unique Lexicographically Sortable Identifier):
  - 26 Crockford base32 characters
  - 10 chars = 48-bit timestamp (ms since Unix epoch)
  - 16 chars = 80-bit cryptographic random
  - Lexicographically sortable by generation time (ms granularity)

No external dependency — uses only Python stdlib (time, secrets).

Reference: https://github.com/ulid/spec
"""

from __future__ import annotations

import secrets
import time

# Crockford base32 alphabet — excludes I, L, O, U to avoid visual ambiguity
_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Pre-compute decode table for validation
_CROCKFORD_SET = frozenset(_CROCKFORD)


def _encode(n: int, length: int) -> str:
    """Encode an integer as a Crockford base32 string of exactly *length* chars."""
    chars: list[str] = []
    for _ in range(length):
        chars.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(chars))


def generate_ulid() -> str:
    """Generate a ULID string (26 uppercase Crockford base32 characters).

    Thread-safe: each call generates independent random bits.

    Returns:
        26-character ULID string, e.g. '01ARZ3NDEKTSV4RRFFQ69G5FAV'.
    """
    ts_ms = int(time.time() * 1000)  # noqa: CLOCK — ULID timestamp, not application clock
    rand = secrets.randbits(80)
    return _encode(ts_ms, 10) + _encode(rand, 16)


def is_valid_ulid(value: str) -> bool:
    """Return True iff *value* is a syntactically valid ULID string.

    Checks length (26) and character set (Crockford base32) only.
    Does not validate timestamp range.
    """
    if len(value) != 26:
        return False
    return all(c in _CROCKFORD_SET for c in value)
