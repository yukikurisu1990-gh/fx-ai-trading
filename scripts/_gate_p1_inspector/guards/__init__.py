"""Runtime safety guards for the Gate P1 inner inspector process (PR-B.0).

Every guard monkey-patches the inner process's *own* runtime to make a
prohibited operation fail closed by raising :class:`GuardViolationError`. The
guards exist precisely to enforce that PR-B's inspection of production code
stays read-only / AST-source-only; they do not modify any production module
(plan §5 "Guard scope justification").

Import discipline: importing this package and its guard modules has NO
side effects. Guards are inert until ``install()`` is called explicitly, and
each guard provides ``uninstall()`` plus an ``activate()`` context manager so
tests (and the inner process) can scope patches precisely and never leak them.
"""

from typing import Final

__all__ = ["GuardViolationError", "GUARD_VIOLATION_ARTIFACT"]


class GuardViolationError(RuntimeError):
    """Raised when a guarded (prohibited) primitive is invoked.

    A ``GuardViolationError`` is an inspection-integrity HALT signal: it means
    PR-B code attempted an operation the protocol forbids (network, subprocess,
    credential access, an out-of-bounds write, or a production-module import).
    It is never a permitted inspection outcome (plan §5 "HALT semantics").
    """


# Canonical filename the inner process writes (inside the report dir) when a
# guard trips. Never a permitted inspection outcome (plan §5).
GUARD_VIOLATION_ARTIFACT: Final[str] = "guard_violation.json"
