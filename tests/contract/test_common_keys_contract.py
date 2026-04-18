"""Contract tests: Common Keys invariants (D1 §3.3 / D3 §8.4 / M11).

D3 §8.4 item 8: Repository 経由以外での Common Keys 書込禁止.

CommonKeysContext is the single authoritative carrier of the 4 mandatory
Common Keys (run_id, environment, code_version, config_version).  All DB
writes must route through the Repository layer which reads from this context;
application code must not set these fields directly on DB rows.

Tests:
  1. CommonKeysContext is importable and is a frozen dataclass.
  2. All 4 mandatory fields are present.
  3. Empty / whitespace fields are rejected at construction time.
  4. Instance is immutable after creation (frozen=True enforcement).
  5. Construction succeeds with valid non-empty values.
  6. No src/ file outside repositories/ / common/ / config/ contains
     raw SQL text with Common Key field names in INSERT/UPDATE context.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fx_ai_trading.config.common_keys_context import CommonKeysContext

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "fx_ai_trading"

# Directories where Common Key manipulation is explicitly allowed.
_ALLOWED_DIRS = frozenset({"repositories", "common", "config"})

# Raw SQL patterns that would indicate a Common Key being hard-coded into a
# query outside the Repository layer.  We look for text() / execute() call
# sites that contain both a write verb and a Common Key field name.
_COMMON_KEY_FIELDS = frozenset({"run_id", "environment", "code_version", "config_version"})

# Matches raw SQL write verbs in string literals (case-insensitive).
_SQL_WRITE_PATTERN = re.compile(r"(?i)\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET)\b")


# ---------------------------------------------------------------------------
# Tests — CommonKeysContext structure
# ---------------------------------------------------------------------------


class TestCommonKeysContextStructure:
    def test_importable(self) -> None:
        """CommonKeysContext must be importable from the expected module."""
        from fx_ai_trading.config.common_keys_context import (
            CommonKeysContext as CKC,  # noqa: F401, N817
        )

        assert CKC is not None

    def test_is_frozen_dataclass(self) -> None:
        """CommonKeysContext must be a frozen dataclass (immutable)."""
        import dataclasses

        assert dataclasses.is_dataclass(CommonKeysContext)
        assert CommonKeysContext.__dataclass_params__.frozen is True  # type: ignore[attr-defined]

    def test_mandatory_fields_present(self) -> None:
        """All 4 mandatory Common Key fields must exist on CommonKeysContext."""
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(CommonKeysContext)}
        assert "run_id" in field_names
        assert "environment" in field_names
        assert "code_version" in field_names
        assert "config_version" in field_names

    def test_valid_construction(self) -> None:
        """Construction with valid values must succeed."""
        ctx = CommonKeysContext(
            run_id="run-001",
            environment="demo",
            code_version="v1.0.0",
            config_version="abcdef01",
        )
        assert ctx.run_id == "run-001"
        assert ctx.environment == "demo"
        assert ctx.code_version == "v1.0.0"
        assert ctx.config_version == "abcdef01"

    def test_immutable_after_creation(self) -> None:
        """Assigning to any field after creation must raise."""
        ctx = CommonKeysContext(
            run_id="r",
            environment="demo",
            code_version="v1",
            config_version="c1",
        )
        with pytest.raises((AttributeError, TypeError)):
            ctx.run_id = "mutated"  # type: ignore[misc]

    @pytest.mark.parametrize("field", ["run_id", "environment", "code_version", "config_version"])
    def test_empty_field_rejected(self, field: str) -> None:
        """Each mandatory field must raise ValueError when empty."""
        valid = {
            "run_id": "r",
            "environment": "demo",
            "code_version": "v1",
            "config_version": "c1",
        }
        invalid = {**valid, field: ""}
        with pytest.raises(ValueError, match=field):
            CommonKeysContext(**invalid)

    @pytest.mark.parametrize("field", ["run_id", "environment", "code_version", "config_version"])
    def test_whitespace_only_field_rejected(self, field: str) -> None:
        """Whitespace-only values must be rejected (same as empty)."""
        valid = {
            "run_id": "r",
            "environment": "demo",
            "code_version": "v1",
            "config_version": "c1",
        }
        invalid = {**valid, field: "   "}
        with pytest.raises(ValueError, match=field):
            CommonKeysContext(**invalid)


# ---------------------------------------------------------------------------
# Tests — No raw SQL writes of Common Keys outside Repository layer
# ---------------------------------------------------------------------------


class TestCommonKeysNotWrittenOutsideRepository:
    def test_no_raw_sql_common_key_writes_outside_repository(self) -> None:
        """No src/ file outside allowed dirs must contain raw SQL writes of Common Keys.

        Scans Python source files for string literals that match BOTH a SQL
        write verb (INSERT INTO / UPDATE SET) AND a Common Key field name.
        This heuristic catches the most likely violations without false-positives
        from DTO construction or pure Python attribute access.
        """
        violations: list[str] = []
        for py_file in _SRC_ROOT.rglob("*.py"):
            parts = py_file.relative_to(_SRC_ROOT).parts
            if parts[0] in _ALLOWED_DIRS:
                continue
            content = py_file.read_text(encoding="utf-8")
            for lineno, line in enumerate(content.splitlines(), start=1):
                if _SQL_WRITE_PATTERN.search(line):
                    for field in _COMMON_KEY_FIELDS:
                        if field in line:
                            rel = py_file.relative_to(_SRC_ROOT)
                            violations.append(f"{rel}:{lineno}: SQL write of '{field}'")

        assert not violations, (
            "Raw SQL writes of Common Key fields found outside Repository layer:\n"
            + "\n".join(violations)
        )
