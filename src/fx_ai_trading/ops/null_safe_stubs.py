"""Wiring-verification stubs for the paper-loop runner (M9 ops scaffold).

Purpose
-------
``Supervisor.attach_exit_gate`` requires real ``Broker`` /
``StateManager`` / ``ExitPolicyService`` instances, but constructing
the production paper stack (DB engine + open-positions write path +
configured policy) is a separate responsibility — see the **next PR**
in the M9 operations sub-series.

For the runner-scaffold PR, we only need to prove that:

  1. The runner can boot, attach a ``QuoteFeed`` (the live
     ``OandaQuoteFeed``), tick on cadence, and shut down on SIGINT.
  2. The observation log records each tick with a stable, JSON-friendly
     shape that operators can ``tail -f | jq`` against.

These stubs satisfy (1) by short-circuiting the exit-gate hot path:
``open_position_details()`` always returns ``[]``, so
``run_exit_gate`` returns ``[]`` immediately and the broker /
exit-policy code paths are **never reached**.

Defensive: if a future change ever does invoke them, every method
raises ``RuntimeError`` with a pointer back to this docstring so an
operator (or test) sees an unmissable failure rather than a silent
no-op trade.

Scope guards
------------
- Not safe for use outside the wiring-verification runner.
- Not exported from any package ``__init__``.
- Do not subclass these to "make a real broker" — implement
  ``Broker`` from scratch instead.
"""

from __future__ import annotations

from typing import Any

from fx_ai_trading.adapters.broker.base import BrokerBase
from fx_ai_trading.domain.broker import (
    BrokerOrder,
    BrokerPosition,
    BrokerTransactionEvent,
    CancelResult,
    OrderRequest,
    OrderResult,
)
from fx_ai_trading.domain.exit import ExitDecision

_STUB_INVOCATION_MESSAGE = (
    "wiring-verification stub invoked; production paper stack bootstrap "
    "is the next PR in the M9 operations sub-series — "
    "see fx_ai_trading.ops.null_safe_stubs"
)


class NullStateManager:
    """``open_position_details() -> []`` — short-circuits ``run_exit_gate``.

    Mirrors only the surface ``run_exit_gate`` reads: ``account_id``
    property and ``open_position_details()``.  ``on_close()`` is
    defensively present so misuse fails loudly instead of silently
    dropping a write.
    """

    def __init__(self, account_id: str) -> None:
        self._account_id = account_id

    @property
    def account_id(self) -> str:
        return self._account_id

    def open_position_details(self) -> list:
        return []

    def on_close(self, *args: Any, **kwargs: Any) -> None:  # pragma: no cover - defensive
        raise RuntimeError(f"NullStateManager.on_close called — {_STUB_INVOCATION_MESSAGE}")


class NullBroker(BrokerBase):
    """Concrete ``Broker`` whose every method raises ``RuntimeError``.

    ``account_type`` is fixed to ``'demo'`` so the inherited
    ``_verify_account_type_or_raise`` (6.18) treats this as a paper-mode
    broker and never escalates to ``AccountTypeMismatchRuntime``.  The
    runner is still expected to never hit ``place_order`` because
    ``NullStateManager`` returns no positions.
    """

    def __init__(self) -> None:
        super().__init__(account_type="demo")

    def place_order(self, request: OrderRequest) -> OrderResult:  # pragma: no cover - defensive
        raise RuntimeError(
            f"NullBroker.place_order called for {request!r} — {_STUB_INVOCATION_MESSAGE}"
        )

    def cancel_order(self, order_id: str) -> CancelResult:  # pragma: no cover - defensive
        raise RuntimeError(
            f"NullBroker.cancel_order called for order_id={order_id!r} — {_STUB_INVOCATION_MESSAGE}"
        )

    def get_positions(
        self, account_id: str
    ) -> list[BrokerPosition]:  # pragma: no cover - defensive
        raise RuntimeError(
            f"NullBroker.get_positions called for account_id={account_id!r} "
            f"— {_STUB_INVOCATION_MESSAGE}"
        )

    def get_pending_orders(
        self, account_id: str
    ) -> list[BrokerOrder]:  # pragma: no cover - defensive
        raise RuntimeError(
            f"NullBroker.get_pending_orders called for account_id={account_id!r} "
            f"— {_STUB_INVOCATION_MESSAGE}"
        )

    def get_recent_transactions(
        self, since: str
    ) -> list[BrokerTransactionEvent]:  # pragma: no cover - defensive
        raise RuntimeError(
            f"NullBroker.get_recent_transactions called since={since!r} "
            f"— {_STUB_INVOCATION_MESSAGE}"
        )


class NullExitPolicy:
    """``evaluate()`` raises — runner must never reach this path."""

    def evaluate(  # pragma: no cover - defensive
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
        raise RuntimeError(
            f"NullExitPolicy.evaluate called for position_id={position_id!r} — "
            f"{_STUB_INVOCATION_MESSAGE}"
        )
