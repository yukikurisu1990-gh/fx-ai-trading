"""Broker domain interface and DTOs (D3 §2.6.1).

Broker is the critical abstraction for order submission.
Implementations: OandaBroker (live) / PaperBroker (backtest) / MockBroker (test).

Critical Invariant (6.18): place_order must call _verify_account_type_or_raise()
before submitting. Verified by contract tests.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OrderRequest:
    """Request to place an order (D3 §2.6.1).

    client_order_id must be a ULID (6.4) for idempotency.
    side: 'long' | 'short'
    """

    client_order_id: str
    account_id: str
    instrument: str
    side: str
    size_units: int
    tp: float | None = None
    sl: float | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True)
class OrderResult:
    """Result of a place_order call."""

    client_order_id: str
    broker_order_id: str
    status: str
    filled_units: int
    fill_price: float | None = None
    message: str | None = None


@dataclass(frozen=True)
class CancelResult:
    """Result of a cancel_order call."""

    order_id: str
    cancelled: bool
    message: str | None = None


@dataclass(frozen=True)
class BrokerPosition:
    """A position as reported by the broker."""

    instrument: str
    side: str
    units: int
    avg_price: float
    unrealized_pl: float


@dataclass(frozen=True)
class BrokerOrder:
    """A pending order as reported by the broker."""

    broker_order_id: str
    client_order_id: str
    instrument: str
    side: str
    size_units: int
    status: str


@dataclass(frozen=True)
class TransactionEvent:
    """A broker transaction stream event."""

    transaction_id: str
    account_id: str
    event_type: str
    instrument: str | None
    units: int | None
    price: float | None
    occurred_at: datetime


# ---------------------------------------------------------------------------
# Interface (ABC — contract enforcement via _verify_account_type_or_raise)
# ---------------------------------------------------------------------------


class Broker(ABC):
    """Abstract base for all broker implementations (D3 §2.6.1).

    ABC is used instead of Protocol so that _verify_account_type_or_raise()
    can be provided as a concrete protected method that all subclasses inherit
    and are required to call in place_order (Decision 2.6.1-1).

    account_type must be 'demo' or 'live' (6.18).
    """

    @property
    @abstractmethod
    def account_type(self) -> str:
        """Return 'demo' or 'live' (6.18 mandatory property)."""

    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderResult:
        """Submit an order. Must call _verify_account_type_or_raise() first."""

    @abstractmethod
    def cancel_order(self, order_id: str) -> CancelResult:
        """Cancel an open order."""

    @abstractmethod
    def get_positions(self, account_id: str) -> list[BrokerPosition]:
        """Return open positions for the account."""

    @abstractmethod
    def get_pending_orders(self, account_id: str) -> list[BrokerOrder]:
        """Return pending orders for the account."""

    @abstractmethod
    def get_recent_transactions(self, since: str) -> list[TransactionEvent]:
        """Return transactions since the given bookmark."""

    # ------------------------------------------------------------------
    # Protected contract method (Decision 2.6.1-1)
    # ------------------------------------------------------------------

    def _verify_account_type_or_raise(self, expected: str) -> None:
        """Assert self.account_type == expected; raise on mismatch (6.18).

        All place_order implementations must call this as their first action.
        Verified by tests/contract/test_protocols_exist.py.
        """
        from fx_ai_trading.common.exceptions import AccountTypeMismatchRuntime

        if self.account_type != expected:
            raise AccountTypeMismatchRuntime(
                f"Broker account_type {self.account_type!r} != expected {expected!r}"
            )
