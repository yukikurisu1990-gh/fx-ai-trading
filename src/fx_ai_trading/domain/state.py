"""State domain — Phase 6 Cycle 6.7a (read-only StateManager snapshot DTO).

The StateManager provides a single source of truth for the runtime
state views that Risk and Execution already consume today via ad-hoc
helpers on the Execution Gate.  Cycle 6.7a introduces the read-only
view only; write paths (positions / close_events / risk_events) land
in 6.7b.

``StateSnapshot`` is an immutable value object.  Callers that need
``open_instruments`` / ``concurrent_count`` / ``recent_failure_count``
should read them from a single ``snapshot()`` call rather than issue
separate queries — this guarantees the three numbers were derived from
the same point-in-time read and cannot drift against each other.

Invariants (Cycle 6.7a):
  - ``concurrent_count == len(open_instruments)`` (M10 paper-mode:
    one instrument ⇔ one position).  6.7b will decouple these once
    the positions timeline is authoritative.
  - ``snapshot_time_utc`` is the ``now`` the caller supplied when
    building the snapshot, not the DB read time.  Callers are
    expected to pass the Clock's ``now()`` so every decision within
    a single cycle shares a timestamp.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class StateSnapshot:
    """Read-only runtime state view consumed by Risk / Execution."""

    open_instruments: frozenset[str]
    concurrent_count: int
    recent_failure_count: int
    snapshot_time_utc: datetime


__all__ = ["StateSnapshot"]
