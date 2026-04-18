"""Clock interface and implementations (M3 / D3 §2).

Provides a testable abstraction over system time so that no production
code ever calls ``datetime.now()`` or ``time.time()`` directly.

Design constraint (development_rules.md §13.1):
  - Only WallClock.now() may call datetime.now(). It is marked
    ``# noqa: CLOCK`` and this is the only permitted use.
  - All application code that needs the current time must accept a
    ``Clock`` and call ``clock.now()``.

Usage:
    clock: Clock = WallClock()          # production
    clock: Clock = FixedClock(some_dt)  # tests
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Single-method protocol: returns current UTC datetime."""

    def now(self) -> datetime:
        """Return current UTC-aware datetime."""
        ...


def _wall_now() -> datetime:
    """Single authorised call site for system time.

    Separated into its own function so the ``# noqa: CLOCK`` exemption
    is precisely scoped to this line and does not mask adjacent code.
    """
    return datetime.now(UTC)  # noqa: CLOCK


class WallClock:
    """Production clock — delegates to system time.

    This is the ONLY class permitted to call ``datetime.now()``.
    All other production code must use an injected Clock.
    """

    def now(self) -> datetime:
        return _wall_now()


class FixedClock:
    """Deterministic clock for tests — always returns the same instant."""

    def __init__(self, fixed_dt: datetime) -> None:
        self._dt = fixed_dt

    def now(self) -> datetime:
        return self._dt
