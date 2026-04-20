"""Unit tests for env_diff (M26 Phase 3).

Verifies parse_env_text, hash_prefix, and compute_diff. The critical
contract is that diff output never contains plaintext values — only
key names and sha256 hex prefixes.
"""

from __future__ import annotations

from fx_ai_trading.dashboard.config_console.env_diff import (
    compute_diff,
    hash_prefix,
    parse_env_text,
    render_env_text,
)


class TestHashPrefix:
    def test_returns_8_chars(self) -> None:
        assert len(hash_prefix("anything")) == 8

    def test_empty_returns_dash(self) -> None:
        assert hash_prefix("") == "-"

    def test_none_returns_dash(self) -> None:
        assert hash_prefix(None) == "-"

    def test_deterministic(self) -> None:
        assert hash_prefix("abc") == hash_prefix("abc")

    def test_different_values_yield_different_prefixes(self) -> None:
        assert hash_prefix("a") != hash_prefix("b")

    def test_known_value(self) -> None:
        # sha256("hello").hex()[:8]
        assert hash_prefix("hello") == "2cf24dba"


class TestParseEnvText:
    def test_basic_kv(self) -> None:
        result = parse_env_text("FOO=bar\nBAZ=qux\n")
        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_skips_blank_lines(self) -> None:
        result = parse_env_text("\nFOO=bar\n\n\nBAZ=qux\n")
        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_skips_comments(self) -> None:
        result = parse_env_text("# header\nFOO=bar\n# inline note\nBAZ=qux\n")
        assert result == {"FOO": "bar", "BAZ": "qux"}

    def test_strips_double_quotes(self) -> None:
        assert parse_env_text('FOO="hello world"\n') == {"FOO": "hello world"}

    def test_strips_single_quotes(self) -> None:
        assert parse_env_text("FOO='hello world'\n") == {"FOO": "hello world"}

    def test_strips_whitespace(self) -> None:
        assert parse_env_text("  FOO  =  bar  \n") == {"FOO": "bar"}

    def test_skips_lines_without_equals(self) -> None:
        assert parse_env_text("nokeyhere\nFOO=bar\n") == {"FOO": "bar"}

    def test_duplicate_key_last_wins(self) -> None:
        assert parse_env_text("FOO=a\nFOO=b\n") == {"FOO": "b"}

    def test_empty_value_is_kept(self) -> None:
        assert parse_env_text("FOO=\n") == {"FOO": ""}

    def test_value_may_contain_equals(self) -> None:
        assert parse_env_text("URL=postgres://u:p@host/db?x=1\n") == {
            "URL": "postgres://u:p@host/db?x=1"
        }

    def test_blank_input(self) -> None:
        assert parse_env_text("") == {}


class TestRenderEnvText:
    def test_round_trip_preserves_kv(self) -> None:
        original = {"A": "1", "B": "two", "C": "url=ok"}
        text = render_env_text(original)
        assert parse_env_text(text) == original

    def test_empty_dict_yields_empty_string(self) -> None:
        assert render_env_text({}) == ""

    def test_trailing_newline_when_nonempty(self) -> None:
        assert render_env_text({"A": "1"}).endswith("\n")


class TestComputeDiff:
    def test_added(self) -> None:
        diff = compute_diff({}, {"NEW": "value"})
        assert len(diff["added"]) == 1
        assert diff["added"][0]["name"] == "NEW"
        assert diff["added"][0]["new_hash"] == hash_prefix("value")
        assert diff["removed"] == []
        assert diff["changed"] == []
        assert diff["unchanged"] == []

    def test_removed(self) -> None:
        diff = compute_diff({"OLD": "value"}, {})
        assert len(diff["removed"]) == 1
        assert diff["removed"][0]["name"] == "OLD"
        assert diff["removed"][0]["old_hash"] == hash_prefix("value")
        assert diff["added"] == []
        assert diff["changed"] == []

    def test_changed(self) -> None:
        diff = compute_diff({"K": "old"}, {"K": "new"})
        assert len(diff["changed"]) == 1
        entry = diff["changed"][0]
        assert entry["name"] == "K"
        assert entry["old_hash"] == hash_prefix("old")
        assert entry["new_hash"] == hash_prefix("new")
        assert entry["old_hash"] != entry["new_hash"]

    def test_unchanged(self) -> None:
        diff = compute_diff({"K": "same"}, {"K": "same"})
        assert diff["added"] == []
        assert diff["removed"] == []
        assert diff["changed"] == []
        assert diff["unchanged"] == ["K"]

    def test_no_plaintext_in_diff_output(self) -> None:
        secret = "super-secret-token-VALUE-DO-NOT-LEAK"
        diff = compute_diff({}, {"TOKEN": secret})
        # Walk the entire diff structure as text and assert the secret is absent
        flat = repr(diff)
        assert secret not in flat

    def test_no_plaintext_for_changed_keys(self) -> None:
        old_secret = "OLD-PLAINTEXT-XYZ"
        new_secret = "NEW-PLAINTEXT-XYZ"
        diff = compute_diff({"K": old_secret}, {"K": new_secret})
        flat = repr(diff)
        assert old_secret not in flat
        assert new_secret not in flat

    def test_deterministic_ordering(self) -> None:
        diff = compute_diff({}, {"B": "1", "A": "1", "C": "1"})
        names = [e["name"] for e in diff["added"]]
        assert names == ["A", "B", "C"]

    def test_mixed_diff(self) -> None:
        old = {"KEEP": "x", "DROP": "y", "MUTATE": "old"}
        new = {"KEEP": "x", "MUTATE": "new", "ADD": "z"}
        diff = compute_diff(old, new)
        assert [e["name"] for e in diff["added"]] == ["ADD"]
        assert [e["name"] for e in diff["removed"]] == ["DROP"]
        assert [e["name"] for e in diff["changed"]] == ["MUTATE"]
        assert diff["unchanged"] == ["KEEP"]
