"""Unit tests: ``OandaQuoteFeed`` (M-3d).

Pins the contract that the producer:
  - Implements the ``QuoteFeed`` Protocol (``isinstance`` discrimination
    used by ``run_exit_gate`` succeeds).
  - Returns ``Quote.price`` as the mid of best bid / best ask.
  - Uses **OANDA's ``time`` field** as ``Quote.ts`` (NOT clock.now() —
    the M-3c staleness gate must compare against the real observation
    time).
  - Sets ``Quote.source`` to ``SOURCE_OANDA_REST_SNAPSHOT`` by default
    and respects an explicit override.
  - Forwards ``account_id`` and ``[instrument]`` to
    ``OandaAPIClient.get_pricing`` unchanged.
  - Raises ``OandaQuoteFeedError`` (not generic) when the response is
    missing required fields, separating parse failures from transport
    failures (V20Error from the underlying client).

Network is **never** touched — every test uses a ``MagicMock`` for the
oandapyV20 ``api`` surface, mirroring ``tests/integration/
test_oanda_demo_connection.py``'s convention.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.adapters.price_feed.oanda_quote_feed import (
    OandaQuoteFeed,
    OandaQuoteFeedError,
)
from fx_ai_trading.domain.price_feed import (
    SOURCE_OANDA_LIVE,
    SOURCE_OANDA_REST_SNAPSHOT,
    Quote,
    QuoteFeed,
)

# --- helpers -----------------------------------------------------------------


def _make_feed(
    *,
    response: dict,
    account_id: str = "acc-1",
    source: str = SOURCE_OANDA_REST_SNAPSHOT,
) -> tuple[OandaQuoteFeed, MagicMock]:
    fake_api = MagicMock()
    fake_api.request.return_value = response
    api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
    feed = OandaQuoteFeed(api_client=api_client, account_id=account_id, source=source)
    return feed, fake_api


def _pricing_response(
    *,
    instrument: str = "EUR_USD",
    time_str: str = "2026-04-22T13:00:00.000000000Z",
    bid: str | None = "1.10000",
    ask: str | None = "1.10010",
    omit_bids: bool = False,
    omit_asks: bool = False,
    omit_time: bool = False,
    empty_prices: bool = False,
) -> dict:
    if empty_prices:
        return {"prices": []}
    entry: dict = {"instrument": instrument}
    if not omit_time:
        entry["time"] = time_str
    if not omit_bids:
        entry["bids"] = [] if bid is None else [{"price": bid}]
    if not omit_asks:
        entry["asks"] = [] if ask is None else [{"price": ask}]
    return {"prices": [entry]}


# --- protocol satisfaction ---------------------------------------------------


class TestProtocolSatisfaction:
    def test_isinstance_quote_feed_succeeds(self) -> None:
        """``run_exit_gate`` discriminates QuoteFeed via ``isinstance`` —
        if this assertion ever fails, the runner would silently wrap
        the producer in ``callable_to_quote_feed`` (and lose ``ts``
        fidelity)."""
        feed, _ = _make_feed(response=_pricing_response())
        assert isinstance(feed, QuoteFeed)


# --- happy path --------------------------------------------------------------


class TestGetQuoteHappyPath:
    def test_mid_price_is_average_of_best_bid_and_ask(self) -> None:
        feed, _ = _make_feed(response=_pricing_response(bid="1.10000", ask="1.10010"))
        q = feed.get_quote("EUR_USD")
        assert q.price == pytest.approx(1.10005)

    def test_ts_is_parsed_from_oanda_time_field_not_clock(self) -> None:
        """OANDA's ``time`` field is the authoritative observation
        timestamp. The producer MUST NOT substitute clock.now() here —
        M-3c staleness depends on this."""
        feed, _ = _make_feed(response=_pricing_response(time_str="2026-04-22T12:34:56.789000000Z"))
        q = feed.get_quote("EUR_USD")
        assert q.ts == datetime(2026, 4, 22, 12, 34, 56, 789000, tzinfo=UTC)
        assert q.ts.tzinfo is not None  # Quote.__post_init__ already enforces this

    def test_default_source_is_oanda_rest_snapshot(self) -> None:
        feed, _ = _make_feed(response=_pricing_response())
        q = feed.get_quote("EUR_USD")
        assert q.source == SOURCE_OANDA_REST_SNAPSHOT

    def test_source_override_is_respected(self) -> None:
        """Caller can re-tag (e.g. a streaming wrapper later) without
        sub-classing the producer."""
        feed, _ = _make_feed(
            response=_pricing_response(),
            source=SOURCE_OANDA_LIVE,
        )
        q = feed.get_quote("EUR_USD")
        assert q.source == SOURCE_OANDA_LIVE

    def test_returns_a_frozen_quote_dto(self) -> None:
        from dataclasses import FrozenInstanceError

        feed, _ = _make_feed(response=_pricing_response())
        q = feed.get_quote("EUR_USD")
        assert isinstance(q, Quote)
        with pytest.raises(FrozenInstanceError):
            q.price = 9.99  # type: ignore[misc]


# --- request shape -----------------------------------------------------------


class TestRequestShape:
    def test_account_id_and_instrument_forwarded_to_pricing_endpoint(self) -> None:
        """Pin the producer → ``OandaAPIClient.get_pricing`` boundary:
        the producer must forward its constructor ``account_id`` and a
        single-element instrument list per call.  We inspect the
        underlying oandapyV20 ``PricingInfo`` request that the api
        client constructed, which is the canonical evidence both
        arguments threaded through correctly.
        """
        feed, fake_api = _make_feed(
            response=_pricing_response(),
            account_id="101-001-1234567-001",
        )
        feed.get_quote("USD_JPY")
        sent = fake_api.request.call_args.args[0]
        # PricingInfo URL-template substitutes accountID into _endpoint.
        endpoint = vars(sent).get("_endpoint", "")
        assert "101-001-1234567-001" in endpoint
        assert sent.params["instruments"] == "USD_JPY"


# --- error paths -------------------------------------------------------------


class TestErrorPaths:
    def test_empty_prices_list_raises(self) -> None:
        feed, _ = _make_feed(response=_pricing_response(empty_prices=True))
        with pytest.raises(OandaQuoteFeedError, match="no pricing entry"):
            feed.get_quote("EUR_USD")

    def test_missing_bids_raises(self) -> None:
        feed, _ = _make_feed(response=_pricing_response(omit_bids=True))
        with pytest.raises(OandaQuoteFeedError, match="missing 'bid' side"):
            feed.get_quote("EUR_USD")

    def test_empty_bids_list_raises(self) -> None:
        feed, _ = _make_feed(response=_pricing_response(bid=None))
        with pytest.raises(OandaQuoteFeedError, match="missing 'bid' side"):
            feed.get_quote("EUR_USD")

    def test_missing_asks_raises(self) -> None:
        feed, _ = _make_feed(response=_pricing_response(omit_asks=True))
        with pytest.raises(OandaQuoteFeedError, match="missing 'ask' side"):
            feed.get_quote("EUR_USD")

    def test_bid_entry_without_price_raises(self) -> None:
        fake_api = MagicMock()
        fake_api.request.return_value = {
            "prices": [
                {
                    "instrument": "EUR_USD",
                    "time": "2026-04-22T13:00:00.000000000Z",
                    "bids": [{"liquidity": 10_000_000}],  # no 'price'
                    "asks": [{"price": "1.10010"}],
                }
            ]
        }
        api_client = OandaAPIClient(access_token="tok", environment="practice", api=fake_api)
        feed = OandaQuoteFeed(api_client=api_client, account_id="acc-1")
        with pytest.raises(OandaQuoteFeedError, match="bid'\\[0\\] missing 'price'"):
            feed.get_quote("EUR_USD")

    def test_missing_time_raises(self) -> None:
        feed, _ = _make_feed(response=_pricing_response(omit_time=True))
        with pytest.raises(OandaQuoteFeedError, match="missing 'time'"):
            feed.get_quote("EUR_USD")
