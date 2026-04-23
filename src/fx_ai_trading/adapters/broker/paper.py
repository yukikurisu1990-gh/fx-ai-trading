"""PaperBroker — in-memory simulation broker for demo/backtest (D3 §2.6.1).

No external connections. Simulates order fills with configurable slippage.
State is in-memory only — not persisted across restarts.

Invariant (6.18): place_order calls _verify_account_type_or_raise first.
Invariant (10-1): account_type is always 'demo' in Iteration 1.

SlippageModel: injected at init; defaults to ZeroSlippageModel (no slippage).

Fill price source: when ``quote_feed`` is supplied, ``place_order`` reads
the current ``Quote.price`` from the feed for each fill so that open and
close legs reflect different observation times (enabling non-zero
``pnl_realized`` evaluation). When omitted, the legacy ``nominal_price``
is used (preserved for tests that pin a fixed fill price).
"""

from __future__ import annotations

from typing import Protocol

from fx_ai_trading.adapters.broker.base import BrokerBase
from fx_ai_trading.domain.broker import (
    BrokerOrder,
    BrokerPosition,
    BrokerTransactionEvent,
    CancelResult,
    OrderRequest,
    OrderResult,
)
from fx_ai_trading.domain.price_feed import QuoteFeed


class SlippageModel(Protocol):
    """Computes the fill price given a nominal price and order side."""

    def apply(self, nominal_price: float, side: str) -> float:
        """Return the adjusted fill price after slippage."""
        ...


class ZeroSlippageModel:
    """No-op slippage model — fill at exact nominal price."""

    def apply(self, nominal_price: float, side: str) -> float:
        return nominal_price


class PaperBroker(BrokerBase):
    """In-memory paper trading broker.

    Maintains an in-memory position register. Cancellation marks orders as
    cancelled. No external connections are made (Iteration 1: demo only).

    Args:
        account_type: Must be 'demo' (Iteration 1 constraint §10).
        nominal_price: Fallback fill price when ``quote_feed`` is None.
        slippage_model: Optional SlippageModel; defaults to ZeroSlippageModel.
        quote_feed: Optional QuoteFeed; when provided, ``place_order``
            reads the current quote price for each fill instead of
            ``nominal_price``. Open and close legs then reflect distinct
            observation times so ``pnl_realized`` can be non-zero.
    """

    def __init__(
        self,
        account_type: str = "demo",
        *,
        nominal_price: float = 1.0,
        slippage_model: SlippageModel | None = None,
        quote_feed: QuoteFeed | None = None,
    ) -> None:
        super().__init__(account_type=account_type)
        self._nominal_price = nominal_price
        self._slippage: SlippageModel = slippage_model or ZeroSlippageModel()
        self._quote_feed = quote_feed
        self._positions: dict[str, BrokerPosition] = {}
        self._pending: dict[str, BrokerOrder] = {}
        self._order_counter = 0

    # ------------------------------------------------------------------
    # Broker interface
    # ------------------------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderResult:
        """Simulate an immediate market fill.

        Calls _verify_account_type_or_raise first (6.18 invariant).
        Updates the in-memory position register.
        """
        self._verify_account_type_or_raise(self._account_type)
        base_price = (
            self._quote_feed.get_quote(request.instrument).price
            if self._quote_feed is not None
            else self._nominal_price
        )
        fill_price = self._slippage.apply(base_price, request.side)
        broker_order_id = f"paper-{request.client_order_id}"
        self._update_position(request, fill_price)
        return OrderResult(
            client_order_id=request.client_order_id,
            broker_order_id=broker_order_id,
            status="filled",
            filled_units=request.size_units,
            fill_price=fill_price,
        )

    def cancel_order(self, order_id: str) -> CancelResult:
        """Remove the order from pending register if present."""
        removed = self._pending.pop(order_id, None)
        return CancelResult(order_id=order_id, cancelled=removed is not None)

    def get_positions(self, account_id: str) -> list[BrokerPosition]:
        """Return current in-memory positions (all accounts share the same store)."""
        return list(self._positions.values())

    def get_pending_orders(self, account_id: str) -> list[BrokerOrder]:
        """Return current pending orders."""
        return list(self._pending.values())

    def get_recent_transactions(self, since: str) -> list[BrokerTransactionEvent]:
        """Return empty list — transaction log not implemented in paper mode."""
        return []

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _update_position(self, request: OrderRequest, fill_price: float) -> None:
        key = request.instrument
        existing = self._positions.get(key)
        if existing is None:
            self._positions[key] = BrokerPosition(
                instrument=request.instrument,
                side=request.side,
                units=request.size_units,
                avg_price=fill_price,
                unrealized_pl=0.0,
            )
        else:
            total_units = existing.units + request.size_units
            avg = existing.avg_price * existing.units + fill_price * request.size_units
            avg /= total_units
            self._positions[key] = BrokerPosition(
                instrument=request.instrument,
                side=request.side,
                units=total_units,
                avg_price=avg,
                unrealized_pl=0.0,
            )
