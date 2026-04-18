"""Contract tests: ULID generation format and uniqueness (D1 §6.4 / M8).

Verifies that generate_ulid() produces valid ULIDs conforming to the spec:
  - 26 characters
  - Crockford base32 charset (0-9, A-Z, excluding I, L, O, U)
  - Monotonically sortable (lexicographic order ≈ creation time order)
  - Unique across 1000 rapid calls
"""

from __future__ import annotations

import re

from fx_ai_trading.common.ulid import generate_ulid, is_valid_ulid

_CROCKFORD_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
_INVALID_CHARS = frozenset("ILOU")


class TestUlidLength:
    def test_length_is_26(self) -> None:
        assert len(generate_ulid()) == 26

    def test_length_consistent_across_calls(self) -> None:
        lengths = {len(generate_ulid()) for _ in range(100)}
        assert lengths == {26}


class TestUlidCharset:
    def test_only_crockford_base32_chars(self) -> None:
        ulid = generate_ulid()
        assert _CROCKFORD_PATTERN.match(ulid), f"ULID {ulid!r} has invalid characters"

    def test_no_ambiguous_chars(self) -> None:
        for _ in range(100):
            ulid = generate_ulid()
            for ch in _INVALID_CHARS:
                assert ch not in ulid, f"ULID {ulid!r} contains forbidden char {ch!r}"

    def test_uppercase_only(self) -> None:
        ulid = generate_ulid()
        assert ulid == ulid.upper()

    def test_matches_regex_100_times(self) -> None:
        for _ in range(100):
            ulid = generate_ulid()
            assert _CROCKFORD_PATTERN.match(ulid), f"ULID {ulid!r} failed regex"


class TestUlidUniqueness:
    def test_no_duplicates_in_1000_calls(self) -> None:
        ulids = [generate_ulid() for _ in range(1000)]
        assert len(set(ulids)) == 1000, "duplicate ULID generated"

    def test_different_on_each_call(self) -> None:
        a = generate_ulid()
        b = generate_ulid()
        assert a != b


class TestUlidSortability:
    def test_timestamp_prefix_increases_across_milliseconds(self) -> None:
        """ULIDs from different milliseconds must have monotonically increasing prefixes.

        Within the same millisecond, random bits differ so order is not guaranteed.
        This test sleeps 2ms to ensure the timestamp portion increments.
        """
        import time

        a = generate_ulid()
        time.sleep(0.002)  # 2ms — ensures different ms bucket
        b = generate_ulid()
        # Only the first 10 chars (timestamp) must be >=
        assert b[:10] >= a[:10], (
            f"Timestamp prefix of later ULID {b[:10]!r} must be >= earlier {a[:10]!r}"
        )

    def test_all_generated_ulids_are_valid(self) -> None:
        """Bulk generation: all 100 ULIDs must be individually valid."""
        for _ in range(100):
            assert is_valid_ulid(generate_ulid())


class TestIsValidUlid:
    def test_generated_ulid_is_valid(self) -> None:
        assert is_valid_ulid(generate_ulid())

    def test_empty_string_is_invalid(self) -> None:
        assert not is_valid_ulid("")

    def test_wrong_length_is_invalid(self) -> None:
        assert not is_valid_ulid("01ARZ3NDEKTSV4RRFFQ69G5F")  # 25 chars

    def test_invalid_char_is_invalid(self) -> None:
        assert not is_valid_ulid("01ARZ3NDEKTSV4RRFFQ69G5IL")  # contains I, L

    def test_lowercase_is_invalid(self) -> None:
        assert not is_valid_ulid("01arz3ndektsv4rrffq69g5fav")

    def test_valid_known_ulid(self) -> None:
        assert is_valid_ulid("01ARZ3NDEKTSV4RRFFQ69G5FAV")
