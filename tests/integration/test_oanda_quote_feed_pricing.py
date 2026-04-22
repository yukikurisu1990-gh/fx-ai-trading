"""Integration tests: ``OandaQuoteFeed`` end-to-end via ``OandaAPIClient`` (M-3d).

Exercises the producer through a real ``OandaAPIClient`` constructed
from a mocked ``oandapyV20.API``.  The value here (vs the unit suite
in ``tests/unit/test_oanda_quote_feed.py``) is verifying that the
oandapyV20 ``PricingInfo`` request shape that ``OandaAPIClient.get_pricing``
constructs is actually accepted by the producer's response-parsing
path — and that prices flow through cleanly end-to-end.

These tests intentionally do NOT touch the network.  Mirrors the
recorded-style mock convention used by
``tests/integration/test_oanda_demo_connection.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.adapters.price_feed.oanda_quote_feed import OandaQuoteFeed
from fx_ai_trading.domain.price_feed import SOURCE_OANDA_REST_SNAPSHOT


@pytest.fixture
def feed_and_api() -> tuple[OandaQuoteFeed, MagicMock]:
    fake_api = MagicMock()
    api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
    feed = OandaQuoteFeed(api_client=api_client, account_id="101-001-1234567-001")
    return feed, fake_api


class TestPriceFlowsEndToEnd:
    def test_realistic_pricing_response_yields_correct_quote(
        self, feed_and_api: tuple[OandaQuoteFeed, MagicMock]
    ) -> None:
        """A pricing response shaped like what OANDA documents
        actually returns must produce a Quote with the expected mid /
        ts / source — proving the producer parses the real envelope,
        not just unit-test fixtures."""
        feed, fake_api = feed_and_api
        fake_api.request.return_value = {
            "time": "2026-04-22T13:00:00.123456789Z",
            "prices": [
                {
                    "instrument": "EUR_USD",
                    "time": "2026-04-22T13:00:00.000000000Z",
                    "tradeable": True,
                    "type": "PRICE",
                    "bids": [
                        {"price": "1.10000", "liquidity": 10_000_000},
                        {"price": "1.09995", "liquidity": 10_000_000},
                    ],
                    "asks": [
                        {"price": "1.10010", "liquidity": 10_000_000},
                        {"price": "1.10015", "liquidity": 10_000_000},
                    ],
                    "closeoutBid": "1.09990",
                    "closeoutAsk": "1.10020",
                }
            ],
        }
        q = feed.get_quote("EUR_USD")
        assert q.price == pytest.approx(1.10005)
        assert q.ts == datetime(2026, 4, 22, 13, 0, 0, tzinfo=UTC)
        assert q.source == SOURCE_OANDA_REST_SNAPSHOT

    def test_per_call_request_is_independent(
        self, feed_and_api: tuple[OandaQuoteFeed, MagicMock]
    ) -> None:
        """Two consecutive ``get_quote`` calls for two instruments must
        produce two independent prices — proves there is no caching /
        shared state between calls (the M-3d producer is strictly
        stateless polling).
        """
        feed, fake_api = feed_and_api

        responses = iter(
            [
                {
                    "prices": [
                        {
                            "instrument": "EUR_USD",
                            "time": "2026-04-22T13:00:00.000000000Z",
                            "bids": [{"price": "1.10000"}],
                            "asks": [{"price": "1.10010"}],
                        }
                    ]
                },
                {
                    "prices": [
                        {
                            "instrument": "USD_JPY",
                            "time": "2026-04-22T13:00:01.000000000Z",
                            "bids": [{"price": "150.000"}],
                            "asks": [{"price": "150.020"}],
                        }
                    ]
                },
            ]
        )
        fake_api.request.side_effect = lambda _req: next(responses)

        eur = feed.get_quote("EUR_USD")
        jpy = feed.get_quote("USD_JPY")

        assert eur.price == pytest.approx(1.10005)
        assert jpy.price == pytest.approx(150.010)
        # Distinct ts proves we're reading per-response observation
        # times, not reusing a cached one.
        assert eur.ts != jpy.ts
        # Two distinct PricingInfo requests reached the api.
        assert fake_api.request.call_count == 2
