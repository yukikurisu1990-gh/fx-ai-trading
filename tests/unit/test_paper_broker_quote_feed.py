"""Unit tests for the quote-driven fill path in :class:`PaperBroker`.

When ``PaperBroker`` is constructed with a ``QuoteFeed``, each
``place_order`` call must read the current ``Quote.price`` from the
feed so that the open and close legs of a round-trip can fill at
different prices — which is what makes ``pnl_realized`` non-zero in
the M9 M-2 formula ``(fill - avg) * units * sign(side)``.

We assert two things, no more:

1. Two sequential ``place_order`` calls reflect the two distinct
   prices returned by the feed (no caching inside the broker).
2. With those two prices, the M-2 PnL formula yields a non-zero
   value — the actual goal of the patch.

Backwards-compat (no ``quote_feed`` → falls back to ``nominal_price``)
is already covered by the existing tests that construct
``PaperBroker(account_type="demo", nominal_price=…)`` without a feed.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fx_ai_trading.adapters.broker.paper import PaperBroker
from fx_ai_trading.domain.broker import OrderRequest
from fx_ai_trading.domain.price_feed import Quote

_FIXED_TS = datetime(2026, 4, 23, 12, 0, 0, tzinfo=UTC)


class _ScriptedQuoteFeed:
    """Test double — returns the next price from a queue per call."""

    def __init__(self, prices: list[float]) -> None:
        self._prices = list(prices)
        self.calls: list[str] = []

    def get_quote(self, instrument: str) -> Quote:
        self.calls.append(instrument)
        price = self._prices.pop(0)
        return Quote(price=price, ts=_FIXED_TS, source="test")


def _request(*, side: str, client_order_id: str) -> OrderRequest:
    return OrderRequest(
        client_order_id=client_order_id,
        account_id="acc-test",
        instrument="EUR_USD",
        side=side,
        size_units=1000,
    )


def test_open_and_close_fills_use_distinct_quote_prices() -> None:
    feed = _ScriptedQuoteFeed(prices=[1.10, 1.12])
    broker = PaperBroker(account_type="demo", quote_feed=feed)

    open_result = broker.place_order(_request(side="long", client_order_id="o-1"))
    close_result = broker.place_order(_request(side="short", client_order_id="o-2"))

    assert open_result.fill_price == 1.10
    assert close_result.fill_price == 1.12
    assert open_result.fill_price != close_result.fill_price
    assert feed.calls == ["EUR_USD", "EUR_USD"]


def test_round_trip_yields_non_zero_pnl_via_m2_formula() -> None:
    feed = _ScriptedQuoteFeed(prices=[1.10, 1.12])
    broker = PaperBroker(account_type="demo", quote_feed=feed)

    open_result = broker.place_order(_request(side="long", client_order_id="o-1"))
    close_result = broker.place_order(_request(side="short", client_order_id="o-2"))

    units = 1000
    sign = 1  # long
    pnl = (close_result.fill_price - open_result.fill_price) * units * sign

    assert pnl != 0.0
    assert pnl == 1000 * (1.12 - 1.10)
