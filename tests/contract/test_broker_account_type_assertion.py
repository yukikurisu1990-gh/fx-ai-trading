"""Contract tests: all Broker implementations enforce account_type assertion (6.18).

Verifies:
  1. _verify_account_type_or_raise raises AccountTypeMismatchRuntime on mismatch.
  2. place_order calls _verify_account_type_or_raise before any other action.
  3. MockBroker / PaperBroker / OandaBroker all call it.
  4. assert_account_type_matches raises AccountTypeMismatch at startup.
  5. BrokerBase rejects invalid account_type at init.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from fx_ai_trading.adapters.broker.mock import MockBroker
from fx_ai_trading.adapters.broker.oanda import OandaBroker
from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.adapters.broker.paper import PaperBroker
from fx_ai_trading.common.assertions import assert_account_type_matches
from fx_ai_trading.common.exceptions import AccountTypeMismatch, AccountTypeMismatchRuntime
from fx_ai_trading.domain.broker import OrderRequest

_DEMO_REQUEST = OrderRequest(
    client_order_id="01TEST000000000000001",
    account_id="acc-demo",
    instrument="EUR_USD",
    side="long",
    size_units=1000,
)

_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)


# ---------------------------------------------------------------------------
# _verify_account_type_or_raise mechanics
# ---------------------------------------------------------------------------


class TestVerifyAccountTypeOrRaise:
    def test_raises_runtime_on_mismatch(self) -> None:
        broker = MockBroker(account_type="demo")
        with pytest.raises(AccountTypeMismatchRuntime):
            broker._verify_account_type_or_raise(expected="live")

    def test_passes_on_match(self) -> None:
        broker = MockBroker(account_type="demo")
        broker._verify_account_type_or_raise(expected="demo")

    def test_live_broker_passes_live_expected(self) -> None:
        broker = MockBroker(account_type="live")
        broker._verify_account_type_or_raise(expected="live")

    def test_live_broker_fails_demo_expected(self) -> None:
        broker = MockBroker(account_type="live")
        with pytest.raises(AccountTypeMismatchRuntime):
            broker._verify_account_type_or_raise(expected="demo")


# ---------------------------------------------------------------------------
# place_order calls _verify_account_type_or_raise first (6.18 invariant)
# ---------------------------------------------------------------------------


class TestMockBrokerPlaceOrderCallsVerify:
    def test_place_order_calls_verify(self) -> None:
        broker = MockBroker(account_type="demo")
        _wrap = broker._verify_account_type_or_raise
        with patch.object(broker, "_verify_account_type_or_raise", wraps=_wrap) as spy:
            broker.place_order(_DEMO_REQUEST)
            spy.assert_called_once_with(broker.account_type)

    def test_place_order_mismatch_raises_before_recording(self) -> None:
        broker = MockBroker(account_type="demo")
        _patch = patch.object(
            MockBroker, "account_type", new_callable=PropertyMock, return_value="live"
        )
        with _patch, pytest.raises(AccountTypeMismatchRuntime):
            broker.place_order(_DEMO_REQUEST)
        assert broker.placed_orders == []


class TestPaperBrokerPlaceOrderCallsVerify:
    def test_place_order_calls_verify(self) -> None:
        broker = PaperBroker(account_type="demo")
        _wrap = broker._verify_account_type_or_raise
        with patch.object(broker, "_verify_account_type_or_raise", wraps=_wrap) as spy:
            broker.place_order(_DEMO_REQUEST)
            spy.assert_called_once_with(broker.account_type)

    def test_place_order_mismatch_raises(self) -> None:
        broker = PaperBroker(account_type="demo")
        _patch = patch.object(
            PaperBroker, "account_type", new_callable=PropertyMock, return_value="live"
        )
        with _patch, pytest.raises(AccountTypeMismatchRuntime):
            broker.place_order(_DEMO_REQUEST)


def _make_oanda_broker_with_fake_client(account_type: str = "demo") -> OandaBroker:
    fake_api = MagicMock()
    fake_api.request.return_value = {
        "orderCreateTransaction": {"id": "12345"},
        "orderFillTransaction": {
            "orderID": "12345",
            "units": "1000",
            "price": "1.10000",
        },
    }
    api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
    return OandaBroker(
        account_id="acc-1",
        access_token="tok",
        account_type=account_type,
        environment="practice",
        api_client=api_client,
    )


class TestOandaBrokerPlaceOrderCallsVerify:
    def test_place_order_calls_verify_before_http(self) -> None:
        broker = _make_oanda_broker_with_fake_client(account_type="demo")
        _wrap = broker._verify_account_type_or_raise
        with patch.object(broker, "_verify_account_type_or_raise", wraps=_wrap) as spy:
            result = broker.place_order(_DEMO_REQUEST)
            spy.assert_called_once_with(broker.account_type)
            assert result.status == "filled"

    def test_place_order_mismatch_raises_before_http_call(self) -> None:
        broker = _make_oanda_broker_with_fake_client(account_type="demo")
        _patch = patch.object(
            OandaBroker, "account_type", new_callable=PropertyMock, return_value="live"
        )
        with _patch, pytest.raises(AccountTypeMismatchRuntime):
            broker.place_order(_DEMO_REQUEST)
        broker.api_client._api.request.assert_not_called()


# ---------------------------------------------------------------------------
# Startup-time assertion (assert_account_type_matches)
# ---------------------------------------------------------------------------


class TestAssertAccountTypeMatches:
    def test_passes_when_types_match(self) -> None:
        broker = MockBroker(account_type="demo")
        assert_account_type_matches(broker, expected="demo")

    def test_raises_account_type_mismatch_on_difference(self) -> None:
        broker = MockBroker(account_type="demo")
        with pytest.raises(AccountTypeMismatch):
            assert_account_type_matches(broker, expected="live")

    def test_raises_value_error_on_invalid_expected(self) -> None:
        broker = MockBroker(account_type="demo")
        with pytest.raises(ValueError, match="expected must be"):
            assert_account_type_matches(broker, expected="staging")


# ---------------------------------------------------------------------------
# BrokerBase rejects invalid account_type at init
# ---------------------------------------------------------------------------


class TestBrokerBaseInitValidation:
    def test_valid_demo_accepted(self) -> None:
        broker = MockBroker(account_type="demo")
        assert broker.account_type == "demo"

    def test_valid_live_accepted(self) -> None:
        broker = MockBroker(account_type="live")
        assert broker.account_type == "live"

    def test_invalid_account_type_raises(self) -> None:
        with pytest.raises(ValueError, match="account_type must be"):
            MockBroker(account_type="staging")
