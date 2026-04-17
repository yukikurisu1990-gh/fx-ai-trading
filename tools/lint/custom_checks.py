"""Custom lint checks for forbidden patterns defined in docs/development_rules.md 13.1.

Detects the following forbidden calls in Python source code:
- ``print()`` — must use structured logging (development_rules 11.2 / 13.1 #2).
- ``datetime.now()`` / ``datetime.datetime.now()`` — must use Clock interface
  (development_rules 13.1 #1 / phase6_hardening 6.10 determinism).
- ``time.time()`` — must use Clock interface (development_rules 13.1 #1).
- ``os.remove()`` / ``os.unlink()`` / ``shutil.rmtree()`` — must use Archiver
  (development_rules 13.1 #3 / retention_policy 1.3 "single DELETE ban").

This is a minimum-viable implementation for Cycle 6. Additional forbidden
patterns (``DELETE FROM`` string detection, ``isinstance(broker, PaperBroker)``
branching, etc.) are scheduled for follow-up cycles per
``docs/iteration1_implementation_plan.md``.
"""

import ast

_FORBIDDEN_BUILTINS: set[str] = {"print"}

# (outer-name, attribute) pairs. Matches ``outer.attr(...)`` calls.
# The chained-attribute branch in ``find_forbidden_patterns`` also catches
# ``X.outer.attr(...)`` such as ``datetime.datetime.now()``.
_FORBIDDEN_ATTR_CALLS: set[tuple[str, str]] = {
    ("datetime", "now"),
    ("time", "time"),
    ("os", "remove"),
    ("os", "unlink"),
    ("shutil", "rmtree"),
}


def find_forbidden_patterns(code: str) -> list[str]:
    """Parse ``code`` and return forbidden-pattern findings.

    Returns an empty list when ``code`` contains no violations. Each finding
    is a human-readable string that includes the offending pattern and the
    line number where it was detected. On a ``SyntaxError`` the function
    returns a single-element list describing the parse failure so callers
    can distinguish "clean" from "unparseable".

    The function is a pure function: no side effects, no I/O, deterministic.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"syntax error: {exc.msg} at line {exc.lineno}"]

    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        line = node.lineno

        # Case 1: bare name call such as ``print(...)``.
        if isinstance(func, ast.Name):
            if func.id in _FORBIDDEN_BUILTINS:
                findings.append(f"{func.id}() detected at line {line}")
            continue

        # Case 2: attribute call.
        if isinstance(func, ast.Attribute):
            attr = func.attr
            value = func.value
            # 2a: ``outer.attr(...)`` with ``outer`` a plain name.
            if isinstance(value, ast.Name) and (value.id, attr) in _FORBIDDEN_ATTR_CALLS:
                findings.append(f"{value.id}.{attr}() detected at line {line}")
            # 2b: ``X.outer.attr(...)`` such as ``datetime.datetime.now()``.
            elif (
                isinstance(value, ast.Attribute)
                and isinstance(value.value, ast.Name)
                and (value.attr, attr) in _FORBIDDEN_ATTR_CALLS
            ):
                findings.append(f"{value.value.id}.{value.attr}.{attr}() detected at line {line}")

    return findings
