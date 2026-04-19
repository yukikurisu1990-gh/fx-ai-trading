"""OandaAPIClient — thin wrapper around oandapyV20 (D3 §2.6.1, M13a).

Encapsulates the oandapyV20 surface so OandaBroker depends only on this
client for testability. Production: instantiates `oandapyV20.API` internally
from access_token + environment. Tests: pass an `api` double via the
optional `api` constructor argument.

Scope (M13a):
  - REST endpoints used by OandaBroker: order create/cancel, list pending
    orders, list open positions, recent transactions, pricing, candles,
    account summary.
  - Streaming (transaction stream) is intentionally out of scope for M13a
    and remains in M13b / later cycles.

Rate limit handling: oandapyV20 raises V20Error on HTTP 429. We re-raise
unchanged; retry policy is owned by callers (M16 metrics loop) — this
client does not auto-retry.

Account-type safety (6.18): this client does not enforce demo/live
matching. That responsibility stays in OandaBroker via
_verify_account_type_or_raise (Decision 2.6.1-1).
"""

from __future__ import annotations

from typing import Any

_DEFAULT_ENVIRONMENT = "practice"
_VALID_ENVIRONMENTS = frozenset({"practice", "live"})


class OandaAPIClient:
    """Thin wrapper over oandapyV20.API for the endpoints OandaBroker uses."""

    def __init__(
        self,
        access_token: str,
        environment: str = _DEFAULT_ENVIRONMENT,
        api: Any | None = None,
    ) -> None:
        if environment not in _VALID_ENVIRONMENTS:
            raise ValueError(
                f"environment must be one of {sorted(_VALID_ENVIRONMENTS)}, got {environment!r}"
            )
        if api is None:
            from oandapyV20 import API

            api = API(access_token=access_token, environment=environment)
        self._api = api
        self._environment = environment

    @property
    def environment(self) -> str:
        return self._environment

    # ------------------------------------------------------------------
    # Order endpoints
    # ------------------------------------------------------------------

    def create_order(self, account_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        from oandapyV20.endpoints import orders

        request = orders.OrderCreate(accountID=account_id, data=payload)
        return self._api.request(request)

    def cancel_order(self, account_id: str, order_id: str) -> dict[str, Any]:
        from oandapyV20.endpoints import orders

        request = orders.OrderCancel(accountID=account_id, orderID=order_id)
        return self._api.request(request)

    def list_pending_orders(self, account_id: str) -> list[dict[str, Any]]:
        from oandapyV20.endpoints import orders

        request = orders.OrdersPending(accountID=account_id)
        response = self._api.request(request)
        return list(response.get("orders", []))

    # ------------------------------------------------------------------
    # Position endpoints
    # ------------------------------------------------------------------

    def list_open_positions(self, account_id: str) -> list[dict[str, Any]]:
        from oandapyV20.endpoints import positions

        request = positions.OpenPositions(accountID=account_id)
        response = self._api.request(request)
        return list(response.get("positions", []))

    # ------------------------------------------------------------------
    # Transaction endpoints
    # ------------------------------------------------------------------

    def list_recent_transactions(self, account_id: str, since_id: str) -> list[dict[str, Any]]:
        from oandapyV20.endpoints import transactions

        request = transactions.TransactionsSinceID(accountID=account_id, params={"id": since_id})
        response = self._api.request(request)
        return list(response.get("transactions", []))

    # ------------------------------------------------------------------
    # Market data endpoints (used by demo connection check)
    # ------------------------------------------------------------------

    def get_pricing(self, account_id: str, instruments: list[str]) -> list[dict[str, Any]]:
        from oandapyV20.endpoints import pricing

        request = pricing.PricingInfo(
            accountID=account_id, params={"instruments": ",".join(instruments)}
        )
        response = self._api.request(request)
        return list(response.get("prices", []))

    def get_candles(self, instrument: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        from oandapyV20.endpoints import instruments as inst_endpoints

        request = inst_endpoints.InstrumentsCandles(instrument=instrument, params=params or {})
        return self._api.request(request)

    def get_account_summary(self, account_id: str) -> dict[str, Any]:
        from oandapyV20.endpoints import accounts

        request = accounts.AccountSummary(accountID=account_id)
        response = self._api.request(request)
        return dict(response.get("account", {}))

    def list_account_instruments(self, account_id: str) -> list[dict[str, Any]]:
        from oandapyV20.endpoints import accounts

        request = accounts.AccountInstruments(accountID=account_id)
        response = self._api.request(request)
        return list(response.get("instruments", []))
