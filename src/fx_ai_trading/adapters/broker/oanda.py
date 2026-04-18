"""OandaBroker — skeleton for OANDA REST API v20 (D3 §2.6.1).

Full implementation is deferred to Iteration 2 (§11 of iteration plan).
All methods raise NotImplementedError with a clear message.

Invariant (6.18): place_order calls _verify_account_type_or_raise first.
Invariant (10-1): OANDA live connections are PROHIBITED in Iteration 1.
                  Only demo API keys are permitted.

Usage (Iteration 2+):
    adapter = OandaBroker(
        account_id="...",
        access_token=secret_provider.get("OANDA_ACCESS_TOKEN"),
        account_type="demo",
        environment="practice",  # 'practice' = demo, 'live' = live
    )
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

_ITERATION2_MSG = (
    "OandaBroker full implementation is deferred to Iteration 2. "
    "Use MockBroker or PaperBroker for Iteration 1 testing."
)


class OandaBroker(BrokerBase):
    """OANDA REST API v20 broker — skeleton only (Iteration 2).

    Stores connection parameters but does not establish any connection at init.
    All operation methods raise NotImplementedError until Iteration 2.
    """

    def __init__(
        self,
        account_id: str,
        access_token: str,
        account_type: str = "demo",
        environment: str = "practice",
    ) -> None:
        super().__init__(account_type=account_type)
        self._account_id = account_id
        self._access_token = access_token
        self._environment = environment

    # ------------------------------------------------------------------
    # Broker interface — all deferred to Iteration 2
    # ------------------------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderResult:
        """Verify account_type then raise NotImplementedError (Iteration 2)."""
        self._verify_account_type_or_raise(self._account_type)
        raise NotImplementedError(_ITERATION2_MSG)

    def cancel_order(self, order_id: str) -> CancelResult:
        """Not implemented — deferred to Iteration 2."""
        raise NotImplementedError(_ITERATION2_MSG)

    def get_positions(self, account_id: str) -> list[BrokerPosition]:
        """Not implemented — deferred to Iteration 2."""
        raise NotImplementedError(_ITERATION2_MSG)

    def get_pending_orders(self, account_id: str) -> list[BrokerOrder]:
        """Not implemented — deferred to Iteration 2."""
        raise NotImplementedError(_ITERATION2_MSG)

    def get_recent_transactions(self, since: str) -> list[BrokerTransactionEvent]:
        """Not implemented — deferred to Iteration 2."""
        raise NotImplementedError(_ITERATION2_MSG)
