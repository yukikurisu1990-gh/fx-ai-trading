"""CLI wrapper around ``find_forbidden_patterns`` for pre-commit integration.

Walks the repository's Python source directories (``src/``, ``tests/``,
``tools/``) and applies ``find_forbidden_patterns`` to each ``.py`` file.
Prints violations to stdout and exits with code 1 if any are found; exits 0
when clean.

Intended usage (invoked by ``.pre-commit-config.yaml`` as a local hook):

    python tools/lint/run_custom_checks.py

Direct invocation is also supported for manual auditing of the whole repo.
"""

import sys
from pathlib import Path

# Allow ``from tools.lint.custom_checks import ...`` when this file is run
# as a script (``python tools/lint/run_custom_checks.py``). Does not affect
# the installable package; sys.path is only mutated in-process.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.lint.custom_checks import find_forbidden_patterns  # noqa: E402, I001


SCAN_DIRS: tuple[str, ...] = ("src", "tests", "tools")


def main() -> int:
    total_violations = 0
    for scan_dir in SCAN_DIRS:
        dir_path = _PROJECT_ROOT / scan_dir
        if not dir_path.exists():
            continue
        for py_file in sorted(dir_path.rglob("*.py")):
            try:
                code = py_file.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                sys.stderr.write(f"[warn] could not read {py_file}: {exc}\n")
                continue
            findings = find_forbidden_patterns(code)
            if findings:
                total_violations += len(findings)
                rel = py_file.relative_to(_PROJECT_ROOT)
                for finding in findings:
                    sys.stdout.write(f"{rel}: {finding}\n")
    if total_violations > 0:
        sys.stdout.write(f"\n{total_violations} forbidden-pattern violation(s) found.\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
