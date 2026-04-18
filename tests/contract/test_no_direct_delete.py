"""Contract test: no SQL DELETE statements in src/ (development_rules.md §13.1).

Scans all .py files under src/fx_ai_trading/ for raw SQL DELETE patterns.
os.remove / os.unlink / shutil.rmtree are covered by test_forbidden_patterns.py.
This test focuses on SQL-level DELETE which violates the append-only data model.
"""

from __future__ import annotations

import re
from pathlib import Path

_SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "fx_ai_trading"

# Matches SQL DELETE keyword used in a string (case-insensitive).
# Excludes comment lines and docstring-only occurrences.
_DELETE_PATTERN = re.compile(r"""["']\s*DELETE\b""", re.IGNORECASE)


def _find_sql_delete_violations() -> list[str]:
    violations: list[str] = []
    for path in sorted(_SRC_ROOT.rglob("*.py")):
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if _DELETE_PATTERN.search(line):
                rel = path.relative_to(_SRC_ROOT.parent.parent)
                violations.append(f"{rel}:{lineno}: {stripped}")
    return violations


def test_no_sql_delete_in_src() -> None:
    violations = _find_sql_delete_violations()
    assert violations == [], (
        "SQL DELETE found in src/ — use soft-delete or archive pattern instead:\n"
        + "\n".join(violations)
    )
