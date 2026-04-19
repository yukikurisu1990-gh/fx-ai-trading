"""Contract tests for ``tools.lint.custom_checks`` forbidden-pattern detectors.

Covers development_rules.md 13.1 and D3 §7 forbidden-pattern list.

All-file checks (find_forbidden_patterns):
  #1  datetime.now() / datetime.datetime.now()   — use Clock interface
  #2  datetime.utcnow()                           — non-TZ-aware variant
  #3  time.time()                                 — use Clock interface
  #4  print()                                     — use structured logging
  #5  os.remove / os.unlink / shutil.rmtree       — use Archiver

Src-only checks (find_src_only_forbidden_patterns):
  #6  SQL 'DELETE FROM' in string literal
  #7  SQL 'TRUNCATE TABLE' / 'DROP TABLE' in string literal
  #8  'backtest' name in if-condition
  #9  isinstance(x, PaperBroker / MockBroker)
  #10 random.*() seed-less calls

Also verifies:
  - Clean code produces no false positives.
  - # noqa: CLOCK exempts clock checks on that line.
  - # noqa: SQL exempts SQL string checks on that line.
  - Syntax errors are reported (not silently swallowed).
"""

import sys
from pathlib import Path

# ``tools/`` lives outside the installable package (``src/fx_ai_trading/``),
# so we prepend the project root to sys.path so tests can import it.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.lint.custom_checks import (  # noqa: E402, I001
    find_forbidden_patterns,
    find_src_only_forbidden_patterns,
)


# ===========================================================================
# Negative cases (no violations expected)
# ===========================================================================


class TestCleanCode:
    def test_empty_code(self) -> None:
        assert find_forbidden_patterns("") == []

    def test_simple_arithmetic(self) -> None:
        assert find_forbidden_patterns("x = 1 + 1") == []

    def test_user_function_call(self) -> None:
        code = "def add(a, b):\n    return a + b\n\nadd(1, 2)\n"
        assert find_forbidden_patterns(code) == []

    def test_clean_src_code_has_no_src_only_violations(self) -> None:
        code = "x = 1\nresult = x + 2\n"
        assert find_src_only_forbidden_patterns(code) == []

    def test_lowercase_truncate_in_prose_not_flagged(self) -> None:
        """'truncate entries' is English prose, not SQL — must not be flagged."""
        code = 'msg = "Must not delete or truncate entries"\n'
        assert find_src_only_forbidden_patterns(code) == []

    def test_lowercase_delete_in_prose_not_flagged(self) -> None:
        """'delete items' is English prose — only uppercase 'DELETE FROM' is forbidden."""
        code = 'msg = "do not delete items directly"\n'
        assert find_src_only_forbidden_patterns(code) == []


# ===========================================================================
# All-file checks — positive cases
# ===========================================================================


class TestAllFileChecks:
    # --- print ---------------------------------------------------------------

    def test_detect_print(self) -> None:
        findings = find_forbidden_patterns("print('hello')")
        assert len(findings) == 1
        assert "print" in findings[0]

    # --- datetime.now --------------------------------------------------------

    def test_detect_datetime_now(self) -> None:
        findings = find_forbidden_patterns("import datetime\nx = datetime.now()\n")
        assert len(findings) == 1
        assert "datetime.now" in findings[0]

    def test_detect_datetime_datetime_now(self) -> None:
        findings = find_forbidden_patterns("import datetime\nx = datetime.datetime.now()\n")
        assert len(findings) == 1
        assert "datetime.now" in findings[0]

    # --- datetime.utcnow -----------------------------------------------------

    def test_detect_datetime_utcnow(self) -> None:
        findings = find_forbidden_patterns("import datetime\nx = datetime.utcnow()\n")
        assert len(findings) == 1
        assert "utcnow" in findings[0]

    def test_detect_datetime_datetime_utcnow(self) -> None:
        findings = find_forbidden_patterns("import datetime\nx = datetime.datetime.utcnow()\n")
        assert len(findings) == 1
        assert "utcnow" in findings[0]

    # --- time.time -----------------------------------------------------------

    def test_detect_time_time(self) -> None:
        findings = find_forbidden_patterns("import time\nt = time.time()\n")
        assert len(findings) == 1
        assert "time.time" in findings[0]

    # --- file deletion -------------------------------------------------------

    def test_detect_os_remove(self) -> None:
        findings = find_forbidden_patterns("import os\nos.remove('foo')\n")
        assert len(findings) == 1
        assert "os.remove" in findings[0]

    def test_detect_os_unlink(self) -> None:
        findings = find_forbidden_patterns("import os\nos.unlink('foo')\n")
        assert len(findings) == 1
        assert "os.unlink" in findings[0]

    def test_detect_shutil_rmtree(self) -> None:
        findings = find_forbidden_patterns("import shutil\nshutil.rmtree('foo')\n")
        assert len(findings) == 1
        assert "shutil.rmtree" in findings[0]

    # --- noqa: CLOCK exemption -----------------------------------------------

    def test_noqa_clock_exempts_datetime_now(self) -> None:
        code = "x = datetime.now()  # noqa: CLOCK\n"
        assert find_forbidden_patterns(code) == []

    def test_noqa_clock_exempts_time_time(self) -> None:
        code = "t = time.time()  # noqa: CLOCK\n"
        assert find_forbidden_patterns(code) == []

    def test_noqa_clock_does_not_exempt_file_deletion(self) -> None:
        """noqa: CLOCK must not silence os.remove — deletion has no CLOCK exemption."""
        code = "os.remove('foo')  # noqa: CLOCK\n"
        findings = find_forbidden_patterns(code)
        assert len(findings) == 1
        assert "os.remove" in findings[0]

    def test_noqa_clock_does_not_exempt_shutil_rmtree(self) -> None:
        """noqa: CLOCK must not silence shutil.rmtree."""
        code = "shutil.rmtree('dir')  # noqa: CLOCK\n"
        findings = find_forbidden_patterns(code)
        assert len(findings) == 1
        assert "shutil.rmtree" in findings[0]

    # --- multiple / syntax error ---------------------------------------------

    def test_detect_multiple_violations(self) -> None:
        code = "import time\nimport os\nprint('x')\nt = time.time()\nos.remove('y')\n"
        findings = find_forbidden_patterns(code)
        assert len(findings) == 3

    def test_syntax_error_reported(self) -> None:
        findings = find_forbidden_patterns("def broken(:\n    pass")
        assert len(findings) == 1
        assert "syntax error" in findings[0]


# ===========================================================================
# Src-only checks — positive cases
# ===========================================================================


class TestSrcOnlyChecks:
    # --- SQL string literals -------------------------------------------------

    def test_detect_sql_delete_from(self) -> None:
        code = 'sql = "DELETE FROM orders WHERE id = 1"\n'
        findings = find_src_only_forbidden_patterns(code)
        assert any("DELETE FROM" in f for f in findings)

    def test_detect_sql_truncate_table(self) -> None:
        code = 'sql = "TRUNCATE TABLE orders"\n'
        findings = find_src_only_forbidden_patterns(code)
        assert any("TRUNCATE TABLE" in f for f in findings)

    def test_detect_sql_drop_table(self) -> None:
        code = 'sql = "DROP TABLE orders"\n'
        findings = find_src_only_forbidden_patterns(code)
        assert any("DROP TABLE" in f for f in findings)

    def test_noqa_sql_exempts_sql_literal(self) -> None:
        code = 'sql = "DELETE FROM orders"  # noqa: SQL\n'
        findings = find_src_only_forbidden_patterns(code)
        assert not any("DELETE FROM" in f for f in findings)

    # --- if backtest ---------------------------------------------------------

    def test_detect_if_backtest(self) -> None:
        code = "if backtest:\n    do_something()\n"
        findings = find_src_only_forbidden_patterns(code)
        assert any("backtest" in f for f in findings)

    def test_detect_if_not_backtest(self) -> None:
        code = "if not backtest:\n    do_something()\n"
        findings = find_src_only_forbidden_patterns(code)
        assert any("backtest" in f for f in findings)

    def test_backtest_in_assignment_not_flagged(self) -> None:
        """Assigning to a 'backtest' variable is not the forbidden if-branch pattern."""
        code = "backtest = True\n"
        assert find_src_only_forbidden_patterns(code) == []

    # --- isinstance broker type branch ---------------------------------------

    def test_detect_isinstance_paper_broker(self) -> None:
        code = "if isinstance(broker, PaperBroker):\n    pass\n"
        findings = find_src_only_forbidden_patterns(code)
        assert any("PaperBroker" in f for f in findings)

    def test_detect_isinstance_mock_broker(self) -> None:
        code = "if isinstance(broker, MockBroker):\n    pass\n"
        findings = find_src_only_forbidden_patterns(code)
        assert any("MockBroker" in f for f in findings)

    def test_detect_isinstance_broker_tuple(self) -> None:
        code = "if isinstance(broker, (PaperBroker, MockBroker)):\n    pass\n"
        findings = find_src_only_forbidden_patterns(code)
        assert any("PaperBroker" in f or "MockBroker" in f for f in findings)

    def test_isinstance_other_type_not_flagged(self) -> None:
        code = "if isinstance(x, str):\n    pass\n"
        assert find_src_only_forbidden_patterns(code) == []

    # --- random seed-less calls ----------------------------------------------

    def test_detect_random_random(self) -> None:
        code = "import random\nx = random.random()\n"
        findings = find_src_only_forbidden_patterns(code)
        assert any("random.random" in f for f in findings)

    def test_detect_random_randint(self) -> None:
        code = "import random\nx = random.randint(1, 10)\n"
        findings = find_src_only_forbidden_patterns(code)
        assert any("random.randint" in f for f in findings)

    def test_detect_random_choice(self) -> None:
        code = "import random\nx = random.choice([1, 2, 3])\n"
        findings = find_src_only_forbidden_patterns(code)
        assert any("random.choice" in f for f in findings)

    def test_random_seed_itself_not_flagged(self) -> None:
        """random.seed() is the allowed call — must not be flagged."""
        code = "import random\nrandom.seed(42)\n"
        assert find_src_only_forbidden_patterns(code) == []


# ===========================================================================
# Check 11: Live API key in string literal (M25 §6.13(a))
# ===========================================================================


class TestLiveApiKeyDetection:
    def test_detect_oanda_access_token_kv_form(self) -> None:
        code = 'config = "OANDA_ACCESS_TOKEN=abc123def456ghi789jkl012"\n'
        findings = find_src_only_forbidden_patterns(code)
        assert any("live API key" in f for f in findings)

    def test_detect_oanda_live_token_format(self) -> None:
        code = 'token = "myapp-live-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefgh"\n'
        findings = find_src_only_forbidden_patterns(code)
        assert any("live API key" in f for f in findings)

    def test_short_token_not_flagged(self) -> None:
        """Token shorter than 20/32 chars should not be flagged."""
        code = 'x = "OANDA_ACCESS_TOKEN=short"\n'
        findings = find_src_only_forbidden_patterns(code)
        assert not any("live API key" in f for f in findings)

    def test_plain_string_not_flagged(self) -> None:
        code = 'msg = "this is a normal configuration string"\n'
        assert find_src_only_forbidden_patterns(code) == []


# ===========================================================================
# Check 12: FixedTwoFactor bypass stub in src/ (M25 §6.13(b))
# ===========================================================================


class TestFixedTwoFactorBypassDetection:
    def test_detect_fixed_two_factor_instantiation(self) -> None:
        code = "auth = FixedTwoFactor(True)\n"
        findings = find_src_only_forbidden_patterns(code)
        assert any("FixedTwoFactor" in f for f in findings)

    def test_detect_fixed_two_factor_false_variant(self) -> None:
        code = "auth = FixedTwoFactor(False)\n"
        findings = find_src_only_forbidden_patterns(code)
        assert any("FixedTwoFactor" in f for f in findings)

    def test_console_two_factor_not_flagged(self) -> None:
        """ConsoleTwoFactor is the legitimate production implementation."""
        code = "auth = ConsoleTwoFactor()\n"
        assert find_src_only_forbidden_patterns(code) == []

    def test_fixed_two_factor_name_in_string_not_flagged(self) -> None:
        """A string containing 'FixedTwoFactor' (e.g. docstring) is not a call."""
        code = 'doc = "Use FixedTwoFactor only in tests."\n'
        assert find_src_only_forbidden_patterns(code) == []
