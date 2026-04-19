"""Contract tests: OandaBroker account_type behavior (M13a, 6.18).

Verifies OANDA-specific aspects of account_type enforcement:
  1. _verify_account_type_or_raise is called before any HTTP request
     in place_order (mocked client must not be touched on mismatch).
  2. CI must never construct an OandaBroker that would talk to a live
     endpoint: an explicit live-account broker is allowed in code paths
     for M13b gate testing, but place_order using a real network must
     not be exercised in CI.
  3. account_type 'demo'/'live' propagates through to OandaAPIClient
     environment selection only via OandaBroker init params (no implicit
     coupling).

These contracts complement test_broker_account_type_assertion.py which
covers the cross-broker invariant; this file is OANDA-only.
"""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from fx_ai_trading.adapters.broker.oanda import OandaBroker
from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.common.exceptions import AccountTypeMismatchRuntime
from fx_ai_trading.domain.broker import OrderRequest

_DEMO_REQUEST = OrderRequest(
    client_order_id="01TEST000000000000010",
    account_id="acc-demo",
    instrument="EUR_USD",
    side="long",
    size_units=1000,
)

_FAKE_FILL_RESPONSE: dict = {
    "orderCreateTransaction": {"id": "100"},
    "orderFillTransaction": {
        "orderID": "100",
        "units": "1000",
        "price": "1.10000",
    },
}


def _make_broker(
    account_type: str = "demo", environment: str = "practice"
) -> tuple[OandaBroker, MagicMock]:
    fake_api = MagicMock()
    fake_api.request.return_value = _FAKE_FILL_RESPONSE
    api_client = OandaAPIClient(access_token="tok", environment=environment, api=fake_api)
    broker = OandaBroker(
        account_id="acc-1",
        access_token="tok",
        account_type=account_type,
        environment=environment,
        api_client=api_client,
    )
    return broker, fake_api


# ---------------------------------------------------------------------------
# place_order — verify-before-HTTP contract
# ---------------------------------------------------------------------------


class TestPlaceOrderVerifyBeforeHTTP:
    def test_demo_broker_demo_request_succeeds(self) -> None:
        broker, fake_api = _make_broker(account_type="demo")
        result = broker.place_order(_DEMO_REQUEST)
        assert result.status == "filled"
        assert fake_api.request.call_count == 1

    def test_runtime_mismatch_blocks_http_call(self) -> None:
        broker, fake_api = _make_broker(account_type="demo")
        _patch = patch.object(
            OandaBroker, "account_type", new_callable=PropertyMock, return_value="live"
        )
        with _patch, pytest.raises(AccountTypeMismatchRuntime):
            broker.place_order(_DEMO_REQUEST)
        fake_api.request.assert_not_called()

    def test_live_broker_with_live_expected_passes_assertion(self) -> None:
        broker, fake_api = _make_broker(account_type="live", environment="live")
        result = broker.place_order(_DEMO_REQUEST)
        assert result.status == "filled"
        fake_api.request.assert_called_once()


# ---------------------------------------------------------------------------
# environment / account_type independence
# ---------------------------------------------------------------------------


class TestEnvironmentDecoupling:
    def test_account_type_does_not_pick_environment(self) -> None:
        # account_type='live' with environment='practice' is allowed at the
        # broker layer; the demo↔live gate (M13b) is responsible for the
        # cross-check. Here we only confirm there is no hidden coupling.
        broker, _ = _make_broker(account_type="live", environment="practice")
        assert broker.account_type == "live"
        assert broker.environment == "practice"

    def test_invalid_environment_rejected(self) -> None:
        with pytest.raises(ValueError, match="environment must be"):
            OandaAPIClient(access_token="tok", environment="staging")


# ---------------------------------------------------------------------------
# CI guard — live API key must not be exercised
# ---------------------------------------------------------------------------


class TestNoLiveCallsInCI:
    def test_default_init_does_not_make_http_request(self) -> None:
        # Constructing the broker (and underlying API) must not perform
        # any network I/O. We assert that no HTTP request happens just by
        # building the broker.
        fake_api = MagicMock()
        api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
        OandaBroker(
            account_id="acc-1",
            access_token="tok",
            account_type="demo",
            environment="practice",
            api_client=api_client,
        )
        fake_api.request.assert_not_called()
