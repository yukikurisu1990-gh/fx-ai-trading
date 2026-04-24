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

Phase 9.10: when the ``Quote`` carries populated ``bid``/``ask`` fields,
fills use the side-specific price (long → ask, short → bid) so the
backtest PnL reflects real spread cost. When bid/ask are unavailable but
a ``BidAskSpreadModel`` is injected, a synthetic half-spread is added to
the mid. With neither, the legacy mid-fill behavior stands — preserving
existing tests that only assert a single price per observation.
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


class BidAskSpreadModel(Protocol):
    """Synthesizes a half-spread for a Quote that only carries mid (Phase 9.10).

    When a QuoteFeed supplies only ``Quote.price`` (no bid/ask), the broker
    calls ``half_spread(instrument)`` to approximate the cost of crossing
    the book. Long fills pay ``mid + half_spread``; short fills receive
    ``mid - half_spread``.
    """

    def half_spread(self, instrument: str) -> float:
        """Return half the synthetic bid-ask spread in price units."""
        ...


def _default_pip_size(instrument: str) -> float:
    """Return the pip size in price units for *instrument*.

    JPY-quoted pairs price at 0.01 per pip; most other FX pairs at 0.0001.
    """
    return 0.01 if instrument.endswith("_JPY") else 0.0001


class FixedPipSpreadModel:
    """``BidAskSpreadModel`` that yields a fixed spread in pips across all pairs.

    The spread is specified in pip units so the same constant covers both
    JPY-quoted pairs (pip = 0.01) and the rest (pip = 0.0001).
    """

    def __init__(self, spread_pip: float) -> None:
        if spread_pip < 0:
            raise ValueError(f"spread_pip must be >= 0 (got {spread_pip!r}).")
        self._spread_pip = spread_pip

    def half_spread(self, instrument: str) -> float:
        return _default_pip_size(instrument) * self._spread_pip / 2.0


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
        spread_model: Optional ``BidAskSpreadModel``; consulted only when
            the Quote lacks bid/ask (Phase 9.10). Adds a synthetic
            half-spread to the mid so side-aware fills are still possible
            from mid-only producers.
    """

    def __init__(
        self,
        account_type: str = "demo",
        *,
        nominal_price: float = 1.0,
        slippage_model: SlippageModel | None = None,
        quote_feed: QuoteFeed | None = None,
        spread_model: BidAskSpreadModel | None = None,
    ) -> None:
        super().__init__(account_type=account_type)
        self._nominal_price = nominal_price
        self._slippage: SlippageModel = slippage_model or ZeroSlippageModel()
        self._quote_feed = quote_feed
        self._spread_model = spread_model
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
        base_price = self._base_fill_price(request)
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

    def _base_fill_price(self, request: OrderRequest) -> float:
        """Pre-slippage fill price, side-aware when bid/ask is available.

        Resolution order (Phase 9.10):
          1. No quote_feed → legacy ``nominal_price`` (tests that pin a fixed price).
          2. Quote has both bid and ask → long pays ask, short receives bid.
          3. Quote has only mid + a spread_model is injected → mid ± half_spread.
          4. Otherwise → mid (legacy behavior, no side awareness).
        """
        if self._quote_feed is None:
            return self._nominal_price
        quote = self._quote_feed.get_quote(request.instrument)
        if quote.bid is not None and quote.ask is not None:
            return quote.ask if request.side == "long" else quote.bid
        if self._spread_model is not None:
            half_spread = self._spread_model.half_spread(request.instrument)
            return (
                quote.price + half_spread if request.side == "long" else quote.price - half_spread
            )
        return quote.price

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
