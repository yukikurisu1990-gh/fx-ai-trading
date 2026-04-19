"""Integration tests: OandaBroker with mocked OANDA REST responses (M13a).

Exercises the OANDA REST surface end-to-end through OandaBroker, using a
recorded-style mock of OandaAPIClient. The point is to verify response
parsing into domain DTOs (OrderResult, BrokerPosition, BrokerOrder,
BrokerTransactionEvent) is correct.

These tests intentionally do NOT touch the network. A real demo-account
smoke test belongs in M13b together with the live-confirmation gate and
will require credentials sourced via SecretProvider.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.adapters.broker.oanda import OandaBroker
from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.domain.broker import OrderRequest


@pytest.fixture
def broker_and_api() -> tuple[OandaBroker, MagicMock]:
    fake_api = MagicMock()
    api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
    broker = OandaBroker(
        account_id="101-001-1234567-001",
        access_token="tok",
        account_type="demo",
        environment="practice",
        api_client=api_client,
    )
    return broker, fake_api


# ---------------------------------------------------------------------------
# place_order — fill / reject / pending
# ---------------------------------------------------------------------------


class TestPlaceOrderResponseParsing:
    def test_fill_response_parsed(self, broker_and_api: tuple[OandaBroker, MagicMock]) -> None:
        broker, fake_api = broker_and_api
        fake_api.request.return_value = {
            "orderCreateTransaction": {"id": "201"},
            "orderFillTransaction": {
                "orderID": "201",
                "units": "1000",
                "price": "1.10250",
            },
        }
        request = OrderRequest(
            client_order_id="01TEST000000000000020",
            account_id="acc-demo",
            instrument="EUR_USD",
            side="long",
            size_units=1000,
        )
        result = broker.place_order(request)
        assert result.status == "filled"
        assert result.broker_order_id == "201"
        assert result.filled_units == 1000
        assert result.fill_price == pytest.approx(1.10250)

    def test_reject_response_parsed(self, broker_and_api: tuple[OandaBroker, MagicMock]) -> None:
        broker, fake_api = broker_and_api
        fake_api.request.return_value = {
            "orderRejectTransaction": {
                "id": "202",
                "rejectReason": "INSUFFICIENT_MARGIN",
            }
        }
        request = OrderRequest(
            client_order_id="01TEST000000000000021",
            account_id="acc-demo",
            instrument="EUR_USD",
            side="long",
            size_units=1_000_000,
        )
        result = broker.place_order(request)
        assert result.status == "rejected"
        assert result.message == "INSUFFICIENT_MARGIN"
        assert result.filled_units == 0

    def test_short_order_uses_negative_units(
        self, broker_and_api: tuple[OandaBroker, MagicMock]
    ) -> None:
        broker, fake_api = broker_and_api
        fake_api.request.return_value = {
            "orderCreateTransaction": {"id": "203"},
            "orderFillTransaction": {
                "orderID": "203",
                "units": "-500",
                "price": "1.0",
            },
        }
        request = OrderRequest(
            client_order_id="01TEST000000000000022",
            account_id="acc-demo",
            instrument="EUR_USD",
            side="short",
            size_units=500,
        )
        broker.place_order(request)
        sent_request = fake_api.request.call_args.args[0]
        assert sent_request.data["order"]["units"] == "-500"

    def test_invalid_side_rejected(self, broker_and_api: tuple[OandaBroker, MagicMock]) -> None:
        broker, _ = broker_and_api
        bad = OrderRequest(
            client_order_id="01TEST000000000000023",
            account_id="acc-demo",
            instrument="EUR_USD",
            side="flat",
            size_units=100,
        )
        with pytest.raises(ValueError, match="OrderRequest.side"):
            broker.place_order(bad)


# ---------------------------------------------------------------------------
# cancel_order
# ---------------------------------------------------------------------------


class TestCancelOrder:
    def test_cancel_success_returns_cancelled_true(
        self, broker_and_api: tuple[OandaBroker, MagicMock]
    ) -> None:
        broker, fake_api = broker_and_api
        fake_api.request.return_value = {
            "orderCancelTransaction": {"id": "300", "reason": "CLIENT_REQUEST"}
        }
        result = broker.cancel_order("201")
        assert result.cancelled is True
        assert result.message == "CLIENT_REQUEST"

    def test_cancel_api_failure_returns_cancelled_false(
        self, broker_and_api: tuple[OandaBroker, MagicMock]
    ) -> None:
        broker, fake_api = broker_and_api
        fake_api.request.side_effect = RuntimeError("404 Not Found")
        result = broker.cancel_order("missing-order")
        assert result.cancelled is False
        assert "404" in (result.message or "")


# ---------------------------------------------------------------------------
# get_positions / get_pending_orders
# ---------------------------------------------------------------------------


class TestGetPositions:
    def test_long_and_short_split_into_separate_entries(
        self, broker_and_api: tuple[OandaBroker, MagicMock]
    ) -> None:
        broker, fake_api = broker_and_api
        fake_api.request.return_value = {
            "positions": [
                {
                    "instrument": "EUR_USD",
                    "long": {
                        "units": "1000",
                        "averagePrice": "1.1000",
                        "unrealizedPL": "5.0",
                    },
                    "short": {"units": "0"},
                },
                {
                    "instrument": "USD_JPY",
                    "long": {"units": "0"},
                    "short": {
                        "units": "-2000",
                        "averagePrice": "150.50",
                        "unrealizedPL": "-3.5",
                    },
                },
            ]
        }
        positions = broker.get_positions("acc-demo")
        assert len(positions) == 2
        eur = next(p for p in positions if p.instrument == "EUR_USD")
        assert eur.side == "long"
        assert eur.units == 1000
        usd = next(p for p in positions if p.instrument == "USD_JPY")
        assert usd.side == "short"
        assert usd.units == 2000


class TestGetPendingOrders:
    def test_pending_orders_parsed(self, broker_and_api: tuple[OandaBroker, MagicMock]) -> None:
        broker, fake_api = broker_and_api
        fake_api.request.return_value = {
            "orders": [
                {
                    "id": "401",
                    "instrument": "EUR_USD",
                    "units": "500",
                    "state": "PENDING",
                    "clientExtensions": {"id": "01CLIENT000000000000400"},
                }
            ]
        }
        orders = broker.get_pending_orders("acc-demo")
        assert len(orders) == 1
        assert orders[0].broker_order_id == "401"
        assert orders[0].client_order_id == "01CLIENT000000000000400"
        assert orders[0].side == "long"
        assert orders[0].size_units == 500


# ---------------------------------------------------------------------------
# get_recent_transactions
# ---------------------------------------------------------------------------


class TestGetRecentTransactions:
    def test_transactions_parsed_into_dtos(
        self, broker_and_api: tuple[OandaBroker, MagicMock]
    ) -> None:
        broker, fake_api = broker_and_api
        fake_api.request.return_value = {
            "transactions": [
                {
                    "id": "501",
                    "type": "ORDER_FILL",
                    "time": "2026-04-19T08:00:00.000000000Z",
                    "instrument": "EUR_USD",
                    "units": "1000",
                    "price": "1.10500",
                }
            ]
        }
        events = broker.get_recent_transactions(since="500")
        assert len(events) == 1
        assert events[0].transaction_id == "501"
        assert events[0].event_type == "ORDER_FILL"
        assert events[0].instrument == "EUR_USD"
        assert events[0].units == 1000
        assert events[0].occurred_at.tzinfo is not None
        assert events[0].occurred_at == datetime(2026, 4, 19, 8, 0, 0, tzinfo=UTC)
