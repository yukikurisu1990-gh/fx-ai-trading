"""OandaBroker — OANDA REST API v20 broker (D3 §2.6.1, M13a).

Iteration 2 / M13a scope:
  - place_order / cancel_order / get_positions / get_pending_orders /
    get_recent_transactions are implemented against the OandaAPIClient
    wrapper (oandapyV20-backed).
  - The 6.18 invariant is preserved: place_order calls
    _verify_account_type_or_raise() before issuing any HTTP request.
  - Iteration 2 operates demo-only; the live path is reachable in code
    but is gated by the M13b demo→live confirmation work and by
    `expected_account_type` enforcement at startup. CI must not exercise
    a live API key (see tests/contract/test_oanda_broker_account_type.py).

Streaming and live confirmation are out of scope for M13a:
  - stream_transactions: M13b / later.
  - --confirm-live-trading flag wiring: M13b.
  - operations.md Step 9 SQL runbook for demo↔live: M13b.

Usage:
    api_client = OandaAPIClient(access_token=secret_provider.get(
        "OANDA_ACCESS_TOKEN"), environment="practice")
    adapter = OandaBroker(
        account_id="...",
        access_token="...",  # only used to construct internal client
        account_type="demo",
        environment="practice",
        api_client=api_client,  # optional; auto-constructed if omitted
    )
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from oandapyV20.exceptions import V20Error

from fx_ai_trading.adapters.broker.base import BrokerBase
from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.domain.broker import (
    BrokerOrder,
    BrokerPosition,
    BrokerTransactionEvent,
    CancelResult,
    OrderRequest,
    OrderResult,
)

_SIDE_TO_UNITS_SIGN = {"long": 1, "short": -1}


class OandaBroker(BrokerBase):
    """OANDA REST API v20 broker.

    Stores connection parameters and delegates HTTP work to OandaAPIClient.
    """

    def __init__(
        self,
        account_id: str,
        access_token: str,
        account_type: str = "demo",
        environment: str = "practice",
        api_client: OandaAPIClient | None = None,
    ) -> None:
        super().__init__(account_type=account_type)
        self._account_id = account_id
        self._access_token = access_token
        self._environment = environment
        self._api_client = api_client or OandaAPIClient(
            access_token=access_token, environment=environment
        )

    @property
    def account_id(self) -> str:
        return self._account_id

    @property
    def environment(self) -> str:
        return self._environment

    @property
    def api_client(self) -> OandaAPIClient:
        return self._api_client

    # ------------------------------------------------------------------
    # Broker interface
    # ------------------------------------------------------------------

    def place_order(self, request: OrderRequest) -> OrderResult:
        """Submit an order to OANDA.

        Calls _verify_account_type_or_raise first (6.18 invariant).
        """
        self._verify_account_type_or_raise(self._account_type)
        payload = {"order": self._build_market_order_payload(request)}
        response = self._api_client.create_order(self._account_id, payload)
        return self._parse_order_response(request.client_order_id, response)

    def cancel_order(self, order_id: str) -> CancelResult:
        """Cancel an open order.

        Returns ``CancelResult(cancelled=True)`` only when OANDA reports
        ``orderCancelTransaction``. ``orderCancelRejectTransaction`` (e.g.
        order already filled / unknown id) is surfaced as a non-cancelled
        result with the broker-supplied ``rejectReason`` so the Reconciler
        (M15) can distinguish a definitive reject from a transient API
        failure. Non-API exceptions (auth/config) are *not* swallowed and
        propagate to the caller.
        """
        try:
            response = self._api_client.cancel_order(self._account_id, order_id)
        except V20Error as exc:
            return CancelResult(order_id=order_id, cancelled=False, message=str(exc))
        reject_tx = response.get("orderCancelRejectTransaction")
        if reject_tx is not None:
            return CancelResult(
                order_id=order_id,
                cancelled=False,
                message=reject_tx.get("rejectReason"),
            )
        cancel_tx = response.get("orderCancelTransaction") or {}
        return CancelResult(
            order_id=order_id,
            cancelled=bool(cancel_tx),
            message=cancel_tx.get("reason"),
        )

    def close_position(self, instrument: str, side: str) -> tuple[float, float, str]:
        """Close all units on the given side via OANDA PositionClose.

        Mode-agnostic: works on both netting (OANDA Japan retail) and hedging
        (most demo/practice) accounts. Returns ``(close_price, realized_pl_jpy,
        transaction_id)`` extracted from the side-specific orderFillTransaction.
        """
        self._verify_account_type_or_raise(self._account_type)
        if side == "long":
            response = self._api_client.close_position(
                self._account_id, instrument, long_units="ALL"
            )
            fill = response.get("longOrderFillTransaction") or {}
        elif side == "short":
            response = self._api_client.close_position(
                self._account_id, instrument, short_units="ALL"
            )
            fill = response.get("shortOrderFillTransaction") or {}
        else:
            raise ValueError(f"side must be 'long' or 'short', got {side!r}")
        if not fill:
            raise RuntimeError(
                f"OANDA close_position returned no fill transaction for {instrument} side={side}"
            )
        price = float(fill.get("price", 0.0))
        pl = float(fill.get("pl", 0.0))
        tx_id = str(fill.get("id", ""))
        return price, pl, tx_id

    def get_positions(self, account_id: str) -> list[BrokerPosition]:
        raw = self._api_client.list_open_positions(account_id)
        result: list[BrokerPosition] = []
        for entry in raw:
            instrument = entry.get("instrument", "")
            for side_key, side_label in (("long", "long"), ("short", "short")):
                side_payload = entry.get(side_key) or {}
                units_str = side_payload.get("units")
                if units_str is None or int(units_str) == 0:
                    continue
                result.append(
                    BrokerPosition(
                        instrument=instrument,
                        side=side_label,
                        units=abs(int(units_str)),
                        avg_price=float(side_payload.get("averagePrice", 0.0)),
                        unrealized_pl=float(side_payload.get("unrealizedPL", 0.0)),
                    )
                )
        return result

    def get_pending_orders(self, account_id: str) -> list[BrokerOrder]:
        raw = self._api_client.list_pending_orders(account_id)
        result: list[BrokerOrder] = []
        for entry in raw:
            units = int(entry.get("units", 0))
            side = "long" if units >= 0 else "short"
            result.append(
                BrokerOrder(
                    broker_order_id=str(entry.get("id", "")),
                    client_order_id=str((entry.get("clientExtensions") or {}).get("id", "")),
                    instrument=str(entry.get("instrument", "")),
                    side=side,
                    size_units=abs(units),
                    status=str(entry.get("state", "")),
                )
            )
        return result

    def get_recent_transactions(self, since: str) -> list[BrokerTransactionEvent]:
        raw = self._api_client.list_recent_transactions(self._account_id, since)
        result: list[BrokerTransactionEvent] = []
        for entry in raw:
            result.append(self._parse_transaction(entry))
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_market_order_payload(self, request: OrderRequest) -> dict[str, Any]:
        sign = _SIDE_TO_UNITS_SIGN.get(request.side)
        if sign is None:
            raise ValueError(f"OrderRequest.side must be 'long' or 'short', got {request.side!r}")
        payload: dict[str, Any] = {
            "type": "MARKET",
            "instrument": request.instrument,
            "units": str(sign * request.size_units),
            "timeInForce": "FOK",
            "positionFill": "DEFAULT",
            "clientExtensions": {"id": request.client_order_id},
        }
        if request.tp is not None:
            payload["takeProfitOnFill"] = {"price": f"{request.tp:.5f}"}
        if request.sl is not None:
            payload["stopLossOnFill"] = {"price": f"{request.sl:.5f}"}
        return payload

    def _parse_order_response(self, client_order_id: str, response: dict[str, Any]) -> OrderResult:
        fill_tx = response.get("orderFillTransaction")
        create_tx = response.get("orderCreateTransaction") or {}
        reject_tx = response.get("orderRejectTransaction")

        if reject_tx is not None:
            return OrderResult(
                client_order_id=client_order_id,
                broker_order_id=str(reject_tx.get("id", "")),
                status="rejected",
                filled_units=0,
                fill_price=None,
                message=reject_tx.get("rejectReason"),
            )

        if fill_tx is not None:
            price_raw = fill_tx.get("price")
            return OrderResult(
                client_order_id=client_order_id,
                broker_order_id=str(fill_tx.get("orderID") or create_tx.get("id", "")),
                status="filled",
                filled_units=abs(int(fill_tx.get("units", 0))),
                fill_price=float(price_raw) if price_raw is not None else None,
                message=None,
            )

        return OrderResult(
            client_order_id=client_order_id,
            broker_order_id=str(create_tx.get("id", "")),
            status="pending",
            filled_units=0,
            fill_price=None,
            message=None,
        )

    def _parse_transaction(self, entry: dict[str, Any]) -> BrokerTransactionEvent:
        time_str = entry.get("time", "")
        occurred_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))

        units_raw = entry.get("units")
        units = int(units_raw) if units_raw is not None else None
        price_raw = entry.get("price")
        price = float(price_raw) if price_raw is not None else None

        return BrokerTransactionEvent(
            transaction_id=str(entry.get("id", "")),
            account_id=str(entry.get("accountID", self._account_id)),
            event_type=str(entry.get("type", "")),
            instrument=entry.get("instrument"),
            units=units,
            price=price,
            occurred_at=occurred_at,
        )
