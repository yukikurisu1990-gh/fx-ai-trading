"""ExecutionGate domain interface and DTOs (D3 §2.6.2).

ExecutionGate is the second-level gatekeeping before order submission.
Checks: TTL / spread / sudden move / broker reachability.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TradingIntent:
    """A validated intent to trade, produced after MetaDecider approval.

    trading_signal_id links back to the originating signal.
    signal_created_at is used by ExecutionGate for TTL calculation (6.15).
    """

    trading_signal_id: str
    order_id: str
    account_id: str
    instrument: str
    side: str
    size_units: int
    tp: float | None
    sl: float | None
    signal_created_at: datetime
    correlation_id: str | None = None


@dataclass(frozen=True)
class RealtimeContext:
    """Market conditions at the moment of ExecutionGate.check() (D3 §2.6.2)."""

    current_spread: float
    is_broker_reachable: bool
    checked_at: datetime


@dataclass(frozen=True)
class GateResult:
    """Result of ExecutionGate.check() (D3 §2.6.2).

    decision: 'approve' | 'reject' | 'defer'
    reason_code examples: 'SpreadTooWide' | 'SuddenMove' | 'StaleSignal'
                          | 'BrokerUnreachable' | 'SignalExpired' | 'DeferExhausted'
    """

    decision: str
    signal_age_seconds: float
    reason_code: str | None = None
    defer_until: datetime | None = None


# ---------------------------------------------------------------------------
# Interface (Protocol)
# ---------------------------------------------------------------------------


class ExecutionGate(Protocol):
    """Second-level gate before order submission (D3 §2.6.2).

    Invariant (6.15 TTL): check() must evaluate signal TTL as its first step.
    Exceeding signal_ttl_seconds -> reject(SignalExpired) immediately.
    """

    def check(self, intent: TradingIntent, realtime_context: RealtimeContext) -> GateResult:
        """Evaluate the intent against real-time conditions.

        Returns GateResult with decision 'approve', 'reject', or 'defer'.
        Side effect: writes to execution_metrics.
        """
        ...
