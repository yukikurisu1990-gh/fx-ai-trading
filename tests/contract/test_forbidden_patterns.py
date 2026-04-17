"""Contract tests for ``tools.lint.custom_checks.find_forbidden_patterns``.

Covers development_rules.md 13.1 #1 (clock/time), #2 (print), and #3 (DELETE
patterns, via os.remove / os.unlink / shutil.rmtree). Also verifies that clean
code produces no false positives.
"""

import sys
from pathlib import Path

# ``tools/`` lives outside the installable package (``src/fx_ai_trading/``),
# so we prepend the project root to sys.path so tests can import it. This
# only affects the test runtime, never the installable package.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.lint.custom_checks import find_forbidden_patterns  # noqa: E402, I001


# --- Clean-code (negative) cases -------------------------------------------------


def test_empty_code_has_no_findings() -> None:
    assert find_forbidden_patterns("") == []


def test_simple_arithmetic_has_no_findings() -> None:
    assert find_forbidden_patterns("x = 1 + 1") == []


def test_user_function_call_has_no_findings() -> None:
    code = "def add(a, b):\n    return a + b\n\nadd(1, 2)\n"
    assert find_forbidden_patterns(code) == []


# --- Forbidden-pattern (positive) cases ------------------------------------------


def test_detect_print() -> None:
    findings = find_forbidden_patterns("print('hello')")
    assert len(findings) == 1
    assert "print" in findings[0]


def test_detect_datetime_now() -> None:
    findings = find_forbidden_patterns("import datetime\nx = datetime.now()\n")
    assert len(findings) == 1
    assert "datetime.now" in findings[0]


def test_detect_datetime_datetime_now() -> None:
    findings = find_forbidden_patterns("import datetime\nx = datetime.datetime.now()\n")
    assert len(findings) == 1
    assert "datetime.now" in findings[0]


def test_detect_time_time() -> None:
    findings = find_forbidden_patterns("import time\nt = time.time()\n")
    assert len(findings) == 1
    assert "time.time" in findings[0]


def test_detect_os_remove() -> None:
    findings = find_forbidden_patterns("import os\nos.remove('foo')\n")
    assert len(findings) == 1
    assert "os.remove" in findings[0]


def test_detect_os_unlink() -> None:
    findings = find_forbidden_patterns("import os\nos.unlink('foo')\n")
    assert len(findings) == 1
    assert "os.unlink" in findings[0]


def test_detect_shutil_rmtree() -> None:
    findings = find_forbidden_patterns("import shutil\nshutil.rmtree('foo')\n")
    assert len(findings) == 1
    assert "shutil.rmtree" in findings[0]


# --- Mixed / error cases ---------------------------------------------------------


def test_detect_multiple_forbidden_patterns() -> None:
    code = "import time\nimport os\nprint('x')\nt = time.time()\nos.remove('y')\n"
    findings = find_forbidden_patterns(code)
    assert len(findings) == 3


def test_syntax_error_returns_single_finding() -> None:
    findings = find_forbidden_patterns("def broken(:\n    pass")
    assert len(findings) == 1
    assert "syntax error" in findings[0]
