"""CLI wrapper around custom_checks for pre-commit integration.

Walks the repository's Python source directories and applies forbidden-pattern
checks.  Two scan surfaces are used:

  find_forbidden_patterns            — applied to ALL directories (src/, tests/, tools/)
  find_src_only_forbidden_patterns   — applied to src/ ONLY (production-logic checks)

Prints violations to stdout and exits with code 1 if any are found.
Exits 0 when clean.

Intended usage (invoked by .pre-commit-config.yaml as a local hook):
    python tools/lint/run_custom_checks.py

Direct invocation is also supported for manual auditing.
"""

import sys
from pathlib import Path

# Allow ``from tools.lint.custom_checks import ...`` when run as a script.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.lint.custom_checks import (  # noqa: E402, I001
    find_forbidden_patterns,
    find_src_only_forbidden_patterns,
)

# Directories scanned with common checks (all Python files).
_ALL_DIRS: tuple[str, ...] = ("src", "tests", "tools")

# Directories also scanned with src-only production checks.
_SRC_DIRS: tuple[str, ...] = ("src",)


def _scan_dir(dir_path: Path, src_only: bool) -> int:
    """Scan all .py files under *dir_path* and return the violation count."""
    total = 0
    for py_file in sorted(dir_path.rglob("*.py")):
        try:
            code = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            sys.stderr.write(f"[warn] could not read {py_file}: {exc}\n")
            continue

        findings = find_forbidden_patterns(code)
        if src_only:
            findings = findings + find_src_only_forbidden_patterns(code)

        if findings:
            total += len(findings)
            rel = py_file.relative_to(_PROJECT_ROOT)
            for finding in findings:
                sys.stdout.write(f"{rel}: {finding}\n")
    return total


def main() -> int:
    total_violations = 0
    scanned_as_src: set[Path] = set()

    # Pass 1: src/ with both common + src-only checks.
    for scan_dir in _SRC_DIRS:
        dir_path = _PROJECT_ROOT / scan_dir
        if not dir_path.exists():
            continue
        total_violations += _scan_dir(dir_path, src_only=True)
        scanned_as_src.add(dir_path.resolve())

    # Pass 2: tests/ and tools/ with common checks only.
    for scan_dir in _ALL_DIRS:
        dir_path = _PROJECT_ROOT / scan_dir
        if not dir_path.exists() or dir_path.resolve() in scanned_as_src:
            continue
        total_violations += _scan_dir(dir_path, src_only=False)

    if total_violations > 0:
        sys.stdout.write(f"\n{total_violations} forbidden-pattern violation(s) found.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
