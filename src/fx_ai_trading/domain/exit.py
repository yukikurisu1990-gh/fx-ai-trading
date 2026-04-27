"""ExitPolicy domain interface and DTOs (D3 §2 / design §6.1).

ExitPolicy evaluates open positions each cycle and decides whether to close them.
Priority (high to low) per Phase 1 §4.9.3:
  emergency_stop > manual > session_close > sl > tp > news_pause
  > max_holding_time > reverse_signal > ev_decay.

All fired reasons are fully enumerated in ExitDecision and written to close_events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExitDecision:
    """Output of ExitPolicy.evaluate() for a single position.

    should_exit: True means the caller must submit a close order.
    reasons: all triggered exit conditions in priority order (full enumeration).
    primary_reason: the highest-priority triggered reason (decisive for close_events).
    """

    position_id: str
    should_exit: bool
    reasons: tuple[str, ...]
    primary_reason: str | None = None
    tp_price: float | None = None
    sl_price: float | None = None


# ---------------------------------------------------------------------------
# Interface (Protocol)
# ---------------------------------------------------------------------------


@runtime_checkable
class ExitPolicy(Protocol):
    """Per-position exit decision engine (D3 §2 / design §6.1).

    Evaluates each open position every 1m/5m cycle.
    Priority per Phase 1 §4.9.3:
      emergency_stop > manual > session_close > sl > tp > news_pause
      > max_holding_time > reverse_signal > ev_decay.

    Invariant: all triggered reasons are fully enumerated in ExitDecision.reasons;
    the highest-priority reason is primary_reason.
    Side effect: caller writes ExitDecision to close_events (not ExitPolicy itself).

    Rules 2-3, 6, 8-9 (manual/session_close/news_pause/reverse_signal/ev_decay) are
    context-dict driven: set the corresponding key to True in context to activate.
    """

    def evaluate(
        self,
        position_id: str,
        instrument: str,
        side: str,
        current_price: float,
        tp: float | None,
        sl: float | None,
        holding_seconds: int,
        context: dict,
    ) -> ExitDecision:
        """Evaluate whether *position_id* should be closed.

        context carries cycle metadata (cycle_id, emergency_stop flag, etc.).
        Returns ExitDecision with should_exit=True if any condition fires.
        """
        ...
