"""State domain — Phase 6 Cycle 6.7a/b/c (snapshot DTOs).

Cycle 6.7a: StateSnapshot read-only DTO.
Cycle 6.7c: OpenPositionInfo DTO for exit gate.

``StateSnapshot`` is an immutable value object consumed by Risk /
Execution.  ``open_instruments`` / ``concurrent_count`` /
``recent_failure_count`` should be read from a single ``snapshot()``
call so the three numbers are derived from the same point-in-time read.

``OpenPositionInfo`` carries per-position details for the exit runner.

Cycle 6.7c constraint (L2): 1 order = 1 position in M10 paper-mode.
Partial close, scale-in/out, and position_id are Phase 7 scope.
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


@dataclass(frozen=True)
class OpenPositionInfo:
    """Details of a single currently-open position (Cycle 6.7c).

    Cycle 6.7c constraint (L2): order_id is the position identity.
    One order = one position; pyramiding and partial close are not
    modelled here.  Phase 7 will introduce a dedicated position_id.

    open_time_utc is the event_time_utc of the most recent 'open' or
    'add' event for this instrument, used to compute holding_seconds
    for ExitPolicyService.evaluate().

    M-1a (Design A): ``side`` is derived per-position from
    ``orders.direction`` via ``_DIRECTION_TO_SIDE`` at read time
    (``StateManager.open_position_details``).  The runner consumer
    (``run_exit_gate``) still accepts a call-arg ``side`` in M-1a;
    M-1b will switch the runner to consume ``pos.side`` and remove
    the call-arg.
    """

    instrument: str
    order_id: str
    units: int
    avg_price: float
    open_time_utc: datetime
    side: str


__all__ = ["OpenPositionInfo", "StateSnapshot"]
