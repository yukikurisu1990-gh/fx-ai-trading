"""Custom lint checks for forbidden patterns defined in docs/development_rules.md 13.1.

Two detection surfaces
─────────────────────
find_forbidden_patterns(code)          — applied to ALL Python files (src/, tests/, tools/).
find_src_only_forbidden_patterns(code) — applied to src/ ONLY; patterns that are legitimate
                                         in test / tool code but forbidden in production logic.

Machine-detectable items (10 total — M11 §6.11 requirement):
  All-file checks (5):
    1.  print()                          — must use structured logging (DR 11.2 / 13.1 #2)
    2.  datetime.now() / .datetime.now() — must use Clock interface (DR 13.1 #1 / 6.10)
    3.  datetime.utcnow()                — non-TZ-aware variant; also forbidden (DR 13.1 #1)
    4.  time.time()                      — must use Clock interface (DR 13.1 #1)
    5.  os.remove / os.unlink / shutil.rmtree — must use Archiver (DR 13.1 #3 / D5 1.3)

  Src-only checks (5):
    6.  SQL 'DELETE FROM' in string literal — D5 single-DELETE ban (Repository only)
    7.  SQL 'TRUNCATE' / 'DROP TABLE'       — D5 no-reset rule
    8.  `if backtest:` / variable 'backtest' in if-test — D2 §12 live/backtest parity
    9.  isinstance(x, PaperBroker/MockBroker) — D2 §12 no broker-type branching in logic
   10.  random.random/randint/choice/… without seed — D3 §6 determinism

Human-review items (5 — not machine-detectable reliably):
    - _verify_account_type_or_raise not called in custom Broker implementation
    - Common Keys written outside Repository via SQLAlchemy
      (contract test: test_common_keys_contract.py)
    - Secret / PII values in log messages (too many false positives)
    - SQLite used in multi_service_mode / container_ready_mode (runtime context)
    - orders.status backward transition (covered by FSM contract test)

Exemption markers
─────────────────
  # noqa: CLOCK   — permits datetime.now() / time.time() on that line
                    (reserved for common/clock.py WallClock._wall_now only)
  # noqa: SQL     — permits SQL string literals containing DELETE/TRUNCATE/DROP TABLE
                    (used in test / migration helper code that legitimately embeds SQL)
"""

from __future__ import annotations

import ast

# ---------------------------------------------------------------------------
# All-file forbidden patterns
# ---------------------------------------------------------------------------

_FORBIDDEN_BUILTINS: set[str] = {"print"}

# (outer-name, attribute) pairs matched in ``outer.attr(...)`` calls.
# Also catches chained form ``X.outer.attr(...)`` (e.g. datetime.datetime.now()).
_FORBIDDEN_ATTR_CALLS: set[tuple[str, str]] = {
    ("datetime", "now"),  # datetime.now()  — use Clock.now()
    ("datetime", "utcnow"),  # datetime.utcnow() — non-TZ-aware, also forbidden
    ("time", "time"),  # time.time()     — use Clock.now()
    ("os", "remove"),  # file deletion   — use Archiver
    ("os", "unlink"),
    ("shutil", "rmtree"),
}

_NOQA_CLOCK_MARKER = "# noqa: CLOCK"
_NOQA_SQL_MARKER = "# noqa: SQL"

# ---------------------------------------------------------------------------
# Src-only forbidden patterns
# ---------------------------------------------------------------------------

# Seeded-random methods: calls to any of these without a prior seed() call
# violate the determinism invariant (D3 §6 / 6.10).
_RANDOM_NON_DETERMINISTIC_METHODS: set[str] = {
    "random",
    "randint",
    "randrange",
    "choice",
    "choices",
    "shuffle",
    "sample",
    "uniform",
    "gauss",
    "normalvariate",
    "betavariate",
    "expovariate",
    "gammavariate",
}

# Broker implementation class names whose presence in isinstance() is forbidden
# in production (src/) code — use Broker / Clock substitution instead.
_FORBIDDEN_BROKER_TYPES: set[str] = {"PaperBroker", "MockBroker"}

# SQL keywords whose presence in string literals is forbidden outside
# the Repository layer (src-only check; exempted with the SQL noqa marker).
#
# Patterns are matched case-sensitively against the raw string value so that
# prose uses of lowercase words ("truncate entries", "drop the table") are not
# flagged.  Real inline SQL is conventionally written in uppercase.
_FORBIDDEN_SQL_KEYWORDS: list[tuple[str, str]] = [
    ("DELETE FROM", "SQL 'DELETE FROM' in string literal"),
    ("TRUNCATE TABLE", "SQL 'TRUNCATE TABLE' in string literal"),
    ("DROP TABLE", "SQL 'DROP TABLE' in string literal"),
]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _noqa_lines(code: str, marker: str) -> frozenset[int]:
    """Return 1-based line numbers that carry *marker* as a noqa comment."""
    return frozenset(i for i, line in enumerate(code.splitlines(), start=1) if marker in line)


def _parse(code: str) -> ast.Module | None:
    """Return the parsed AST or None on SyntaxError (caller records error)."""
    try:
        return ast.parse(code)
    except SyntaxError:
        return None


# ---------------------------------------------------------------------------
# Public API — all-file checks
# ---------------------------------------------------------------------------


def find_forbidden_patterns(code: str) -> list[str]:
    """Parse *code* and return all-file forbidden-pattern findings.

    Applied to every Python file (src/, tests/, tools/).
    Returns [] when no violations are found.
    Each finding is a human-readable string with the pattern and line number.
    On SyntaxError returns a single-element list describing the parse failure.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"syntax error: {exc.msg} at line {exc.lineno}"]

    noqa_clock = _noqa_lines(code, _NOQA_CLOCK_MARKER)
    findings: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        line = node.lineno

        # Bare name call: print(...)
        if isinstance(func, ast.Name):
            if func.id in _FORBIDDEN_BUILTINS:
                findings.append(f"{func.id}() detected at line {line}")
            continue

        # Attribute call: outer.attr(...)
        if isinstance(func, ast.Attribute):
            attr = func.attr
            value = func.value

            # Simple: datetime.now() / time.time() / os.remove() etc.
            if isinstance(value, ast.Name) and (value.id, attr) in _FORBIDDEN_ATTR_CALLS:
                if line not in noqa_clock:
                    findings.append(f"{value.id}.{attr}() detected at line {line}")

            # Chained: datetime.datetime.now() etc.
            elif (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and (value.attr, attr) in _FORBIDDEN_ATTR_CALLS
                and line not in noqa_clock
            ):
                findings.append(f"{value.value.id}.{value.attr}.{attr}() detected at line {line}")

    return findings


# ---------------------------------------------------------------------------
# Public API — src-only checks
# ---------------------------------------------------------------------------


def find_src_only_forbidden_patterns(code: str) -> list[str]:
    """Parse *code* and return src-only forbidden-pattern findings.

    Applied exclusively to files under src/ (see run_custom_checks.py).
    Patterns here are legitimate in test / tool code but forbidden in
    production logic.

    Returns [] when no violations are found. On SyntaxError returns [].
    (SyntaxError already reported by find_forbidden_patterns for the same file.)
    """
    tree = _parse(code)
    if tree is None:
        return []

    noqa_sql = _noqa_lines(code, _NOQA_SQL_MARKER)
    findings: list[str] = []

    for node in ast.walk(tree):
        # ------------------------------------------------------------------
        # Check 6-7: SQL keywords in string literals (DELETE FROM / TRUNCATE / DROP TABLE)
        # ------------------------------------------------------------------
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.lineno not in noqa_sql:
                raw = node.value  # case-sensitive: real SQL is uppercase by convention
                for keyword, msg in _FORBIDDEN_SQL_KEYWORDS:
                    if keyword in raw:
                        findings.append(f"{msg} at line {node.lineno}")
            continue

        # ------------------------------------------------------------------
        # Check 8: `if backtest:` — identifier named 'backtest' in If test
        # ------------------------------------------------------------------
        if isinstance(node, ast.If):
            _check_backtest_in_test(node.test, findings)

        # ------------------------------------------------------------------
        # Check 9: isinstance(x, PaperBroker) / isinstance(x, MockBroker)
        # ------------------------------------------------------------------
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "isinstance"
            and len(node.args) == 2
        ):
            second_arg = node.args[1]
            # isinstance(x, PaperBroker) — single type
            if isinstance(second_arg, ast.Name) and second_arg.id in _FORBIDDEN_BROKER_TYPES:
                findings.append(
                    f"isinstance(x, {second_arg.id}) broker-type branch at line {node.lineno}"
                )
            # isinstance(x, (PaperBroker, MockBroker)) — tuple of types
            elif isinstance(second_arg, ast.Tuple):
                for elt in second_arg.elts:
                    if isinstance(elt, ast.Name) and elt.id in _FORBIDDEN_BROKER_TYPES:
                        findings.append(
                            f"isinstance(x, {elt.id}) broker-type branch at line {node.lineno}"
                        )

        # ------------------------------------------------------------------
        # Check 10: random.*() seed-less calls
        # ------------------------------------------------------------------
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "random"
            and node.func.attr in _RANDOM_NON_DETERMINISTIC_METHODS
        ):
            findings.append(f"random.{node.func.attr}() seed-less random at line {node.lineno}")

    return findings


def _check_backtest_in_test(node: ast.expr, findings: list[str]) -> None:
    """Recursively check if an If-test expression references 'backtest' name."""
    if isinstance(node, ast.Name) and node.id == "backtest":
        findings.append(f"'backtest' name referenced in if-condition at line {node.lineno}")
    elif isinstance(node, ast.BoolOp):
        for value in node.values:
            _check_backtest_in_test(value, findings)
    elif isinstance(node, ast.UnaryOp):
        _check_backtest_in_test(node.operand, findings)
    elif isinstance(node, ast.Compare):
        _check_backtest_in_test(node.left, findings)
        for comp in node.comparators:
            _check_backtest_in_test(comp, findings)
