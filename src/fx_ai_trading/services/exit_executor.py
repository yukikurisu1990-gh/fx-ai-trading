"""ExitExecutor — closes positions and writes close_events (M14 / M-EXIT-1).

Orchestrates the close sequence:
  1. If decision.should_exit is False → no-op, return None.
  2. Place a closing order via Broker (opposite side).
  3. Insert a close_event row via CloseEventsRepository.
  4. Return the OrderResult from the broker.

Emergency-flat (M22): when context["emergency_stop"] is True the caller (ctl
emergency-flat-all, M22 scope) invokes this executor.  No M22-specific code is
added here; the context flag is already evaluated by ExitPolicyService.

Partial close is NOT supported in Iteration 2 (100% close only, per §6.2 risk).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.domain.broker import OrderRequest, OrderResult
from fx_ai_trading.domain.exit import ExitDecision
from fx_ai_trading.repositories.close_events import CloseEventsRepository

_CLOSE_SIDE = {"long": "short", "short": "long"}


class ExitExecutor:
    """Executes the close sequence for a single position.

    Args:
        broker: Any Broker implementation (MockBroker / OandaBroker etc.).
        close_events_repo: CloseEventsRepository for writing the event record.
    """

    def __init__(self, broker, close_events_repo: CloseEventsRepository) -> None:
        self._broker = broker
        self._repo = close_events_repo

    def execute(
        self,
        decision: ExitDecision,
        account_id: str,
        instrument: str,
        side: str,
        size_units: int,
        entry_order_id: str,
        occurred_at: datetime,
        position_snapshot_id: str | None = None,
        pnl_realized: float | None = None,
        correlation_id: str | None = None,
        context: CommonKeysContext | None = None,
    ) -> OrderResult | None:
        """Execute close for *decision* if should_exit is True.

        Returns the broker OrderResult if a close order was placed, None otherwise.

        Args:
            decision: ExitDecision from ExitPolicyService.evaluate().
            account_id: Broker account identifier.
            instrument: FX instrument (e.g. "EUR_USD").
            side: Original position side ("long" | "short").
            size_units: Number of units to close (100% of position).
            entry_order_id: Order ID of the original entry order (FK for close_events).
            occurred_at: TZ-aware UTC timestamp for the close event record.
            position_snapshot_id: FK to positions table (optional).
            pnl_realized: Realized P&L (optional, supplied by caller).
            correlation_id: Cross-table trace key (optional).
            context: CommonKeysContext for contract compliance.
        """
        if not decision.should_exit:
            return None

        close_side = _CLOSE_SIDE[side]
        close_request = OrderRequest(
            client_order_id=str(uuid.uuid4()),
            account_id=account_id,
            instrument=instrument,
            side=close_side,
            size_units=size_units,
        )
        result = self._broker.place_order(close_request)

        reasons_json = [
            {"priority": i + 1, "reason_code": r, "detail": ""}
            for i, r in enumerate(decision.reasons)
        ]

        self._repo.insert(
            close_event_id=str(uuid.uuid4()),
            order_id=entry_order_id,
            primary_reason_code=decision.primary_reason or "",
            reasons=reasons_json,
            closed_at=occurred_at,
            position_snapshot_id=position_snapshot_id,
            pnl_realized=pnl_realized,
            correlation_id=correlation_id,
            context=context,
        )

        return result
