"""BrokerBase — concrete base for all Broker implementations (D3 §2.6.1 / 6.18).

Provides:
  - _account_type storage and account_type property
  - _verify_account_type_or_raise() inherited from domain Broker ABC
  - Enforcement contract: place_order MUST call _verify_account_type_or_raise first

Subclasses must:
  - Accept account_type at __init__ ('demo' or 'live')
  - Call self._verify_account_type_or_raise(self._account_type) as first line of place_order
  - Never connect to live endpoints (Iteration 1 is demo-only, §10)
"""

from __future__ import annotations

from abc import abstractmethod

from fx_ai_trading.domain.broker import (
    Broker,
    BrokerOrder,
    BrokerPosition,
    BrokerTransactionEvent,
    CancelResult,
    OrderRequest,
    OrderResult,
)

_VALID_ACCOUNT_TYPES = frozenset({"demo", "live"})


class BrokerBase(Broker):
    """Intermediate base that stores account_type for all concrete Brokers.

    Invariant (6.18): account_type must be 'demo' or 'live'.
    Raises ValueError at init if an invalid type is passed.
    """

    def __init__(self, account_type: str) -> None:
        if account_type not in _VALID_ACCOUNT_TYPES:
            raise ValueError(
                f"account_type must be one of {sorted(_VALID_ACCOUNT_TYPES)}, got {account_type!r}"
            )
        self._account_type = account_type

    @property
    def account_type(self) -> str:
        """Return configured account type: 'demo' or 'live' (6.18)."""
        return self._account_type

    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderResult:
        """Submit an order. Subclasses MUST call _verify_account_type_or_raise first."""

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
    def get_recent_transactions(self, since: str) -> list[BrokerTransactionEvent]:
        """Return transactions since the given bookmark."""
