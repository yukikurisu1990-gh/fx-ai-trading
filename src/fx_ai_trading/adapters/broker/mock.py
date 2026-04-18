"""MockBroker — deterministic test double for Broker (D3 §2.6.1).

Returns configured fixed responses. Never connects to external systems.
Use in unit / contract tests where real order flow is not needed.

Invariant (6.18): place_order calls _verify_account_type_or_raise first.
"""

from __future__ import annotations

from fx_ai_trading.adapters.broker.base import BrokerBase
from fx_ai_trading.domain.broker import (
    BrokerOrder,
    BrokerPosition,
    BrokerTransactionEvent,
    CancelResult,
    OrderRequest,
    OrderResult,
)

_DEFAULT_FILL_PRICE = 1.0
_DEFAULT_FILLED_UNITS = 0


class MockBroker(BrokerBase):
    """Deterministic broker double for testing.

    Responses are configured at init time. All state is in-memory and
    discarded after the instance is garbage-collected.
    """

    def __init__(
        self,
        account_type: str = "demo",
        *,
        fill_price: float = _DEFAULT_FILL_PRICE,
        positions: list[BrokerPosition] | None = None,
        pending_orders: list[BrokerOrder] | None = None,
        transactions: list[BrokerTransactionEvent] | None = None,
    ) -> None:
        super().__init__(account_type=account_type)
        self._fill_price = fill_price
        self._positions: list[BrokerPosition] = positions or []
        self._pending_orders: list[BrokerOrder] = pending_orders or []
        self._transactions: list[BrokerTransactionEvent] = transactions or []
        self._placed_orders: list[OrderRequest] = []
        self._cancelled_order_ids: list[str] = []

    # ------------------------------------------------------------------
    # Broker interface
    # ------------------------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderResult:
        """Record the order request and return a synthetic filled result.

        Calls _verify_account_type_or_raise first (6.18 invariant).
        """
        self._verify_account_type_or_raise(self._account_type)
        self._placed_orders.append(request)
        return OrderResult(
            client_order_id=request.client_order_id,
            broker_order_id=f"mock-{request.client_order_id}",
            status="filled",
            filled_units=request.size_units,
            fill_price=self._fill_price,
        )

    def cancel_order(self, order_id: str) -> CancelResult:
        """Record the cancellation and return a synthetic success result."""
        self._cancelled_order_ids.append(order_id)
        return CancelResult(order_id=order_id, cancelled=True)

    def get_positions(self, account_id: str) -> list[BrokerPosition]:
        """Return the configured list of positions."""
        return list(self._positions)

    def get_pending_orders(self, account_id: str) -> list[BrokerOrder]:
        """Return the configured list of pending orders."""
        return list(self._pending_orders)

    def get_recent_transactions(self, since: str) -> list[BrokerTransactionEvent]:
        """Return the configured list of transactions."""
        return list(self._transactions)

    # ------------------------------------------------------------------
    # Test introspection helpers
    # ------------------------------------------------------------------

    @property
    def placed_orders(self) -> list[OrderRequest]:
        """All OrderRequest instances passed to place_order (test use only)."""
        return list(self._placed_orders)

    @property
    def cancelled_order_ids(self) -> list[str]:
        """All order_ids passed to cancel_order (test use only)."""
        return list(self._cancelled_order_ids)
