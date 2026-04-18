"""OrderService — thin wrapper around OrdersRepository (D3 §2.9.1).

All write operations pass CommonKeysContext through to the repository.
"""

from __future__ import annotations

from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.orders import OrdersRepository


class OrderService:
    """Provides order-level operations via OrdersRepository."""

    def __init__(self, repo: OrdersRepository) -> None:
        self._repo = repo

    def get_order(self, order_id: str) -> dict | None:
        """Return the order dict for *order_id*, or None."""
        return self._repo.get_by_order_id(order_id)

    def create_order(
        self,
        order_id: str,
        account_id: str,
        instrument: str,
        account_type: str,
        order_type: str,
        direction: str,
        units: str,
        context: CommonKeysContext,
        *,
        client_order_id: str | None = None,
        trading_signal_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Insert a new order row."""
        self._repo.create_order(
            order_id=order_id,
            account_id=account_id,
            instrument=instrument,
            account_type=account_type,
            order_type=order_type,
            direction=direction,
            units=units,
            context=context,
            client_order_id=client_order_id,
            trading_signal_id=trading_signal_id,
            correlation_id=correlation_id,
        )
