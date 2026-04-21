"""ExitExecutor — closes positions and writes close_events (M14 / M-EXIT-1).

.. deprecated:: Cycle 6.7d (I-09)
    ``ExitExecutor`` is superseded by
    :func:`fx_ai_trading.services.exit_gate_runner.run_exit_gate`, which
    delegates the close writes to :meth:`StateManager.on_close` (one
    atomic transaction covering positions, close_events, and the outbox).
    Instantiating ``ExitExecutor`` writes ``close_events`` via the legacy
    repository path and would duplicate those writes (see E1 in
    ``exit_gate_runner``).  New code MUST use ``run_exit_gate``; existing
    callers will be migrated before this class is removed.

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

import contextlib
import uuid
import warnings
from datetime import datetime
from typing import TYPE_CHECKING

from fx_ai_trading.common.exceptions import AccountTypeMismatchRuntime
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.domain.broker import OrderRequest, OrderResult
from fx_ai_trading.domain.exit import ExitDecision
from fx_ai_trading.repositories.close_events import CloseEventsRepository

if TYPE_CHECKING:
    from fx_ai_trading.supervisor.supervisor import Supervisor

_CLOSE_SIDE = {"long": "short", "short": "long"}

_DEPRECATION_MESSAGE = (
    "ExitExecutor is deprecated since Cycle 6.7d (I-09). "
    "Use fx_ai_trading.services.exit_gate_runner.run_exit_gate instead — "
    "it delegates close writes to StateManager.on_close (single atomic "
    "transaction covering positions, close_events, and the outbox)."
)


class ExitExecutor:
    """Executes the close sequence for a single position.

    .. deprecated:: Cycle 6.7d (I-09)
        Use :func:`fx_ai_trading.services.exit_gate_runner.run_exit_gate`.

    Args:
        broker: Any Broker implementation (MockBroker / OandaBroker etc.).
        close_events_repo: CloseEventsRepository for writing the event record.
    """

    def __init__(self, broker, close_events_repo: CloseEventsRepository) -> None:
        warnings.warn(_DEPRECATION_MESSAGE, DeprecationWarning, stacklevel=2)
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
        supervisor: Supervisor | None = None,
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
            supervisor: Optional Supervisor for safe_stop wiring (PR-5 / U-2).
                When provided, an ``AccountTypeMismatchRuntime`` raised
                inside ``broker.place_order`` triggers
                ``supervisor.trigger_safe_stop`` with the canonical reason
                ``"account_type_mismatch_runtime"`` (per phase6_hardening
                §6.18 / operations F14) before the exception propagates.
                The close_event is NOT written and the broker fill is NOT
                returned.  When None, behaviour is unchanged from pre-PR-5.
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
        try:
            result = self._broker.place_order(close_request)
        except AccountTypeMismatchRuntime as exc:
            # PR-5 (U-2): Mid-flight account_type drift detected by the
            # broker's pre-place_order assertion (Decision 2.6.1-1).  Per
            # phase6_hardening §6.18 / operations F14, this MUST trigger
            # safe_stop(reason=account_type_mismatch_runtime) and write
            # NO close_events row.  We fire the wired Supervisor (if any)
            # and then re-raise so the caller sees the failure.
            #
            # ``expected_account_type`` is None here because execute() has
            # no per-call expected value (unlike run_execution_gate); the
            # mismatch text is fully captured in ``detail`` (str(exc)).
            if supervisor is not None:
                payload = {
                    "actual_account_type": self._broker.account_type,
                    "expected_account_type": None,
                    "instrument": instrument,
                    "client_order_id": close_request.client_order_id,
                    "detail": str(exc),
                }
                # Never let a downstream safe_stop bug swallow the
                # original mismatch exception.
                with contextlib.suppress(Exception):
                    supervisor.trigger_safe_stop(
                        reason="account_type_mismatch_runtime",
                        occurred_at=occurred_at,
                        payload=payload,
                    )
            raise

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
