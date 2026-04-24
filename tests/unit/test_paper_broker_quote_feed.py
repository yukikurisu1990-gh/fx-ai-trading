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


# ----------------------------------------------------------------------------
# Phase 9.10: bid/ask-aware fills + synthetic spread model
# ----------------------------------------------------------------------------


class _BidAskQuoteFeed:
    """Test double that returns Quotes with populated bid/ask."""

    def __init__(self, quotes: list[Quote]) -> None:
        self._quotes = list(quotes)
        self.calls: list[str] = []

    def get_quote(self, instrument: str) -> Quote:
        self.calls.append(instrument)
        return self._quotes.pop(0)


def _bid_ask_quote(*, bid: float, ask: float) -> Quote:
    return Quote(
        price=(bid + ask) / 2.0,
        ts=_FIXED_TS,
        source="test",
        bid=bid,
        ask=ask,
    )


def test_long_fill_uses_ask_when_bid_ask_populated() -> None:
    feed = _BidAskQuoteFeed(quotes=[_bid_ask_quote(bid=1.0998, ask=1.1002)])
    broker = PaperBroker(account_type="demo", quote_feed=feed)
    result = broker.place_order(_request(side="long", client_order_id="o-1"))
    assert result.fill_price == 1.1002


def test_short_fill_uses_bid_when_bid_ask_populated() -> None:
    feed = _BidAskQuoteFeed(quotes=[_bid_ask_quote(bid=1.0998, ask=1.1002)])
    broker = PaperBroker(account_type="demo", quote_feed=feed)
    result = broker.place_order(_request(side="short", client_order_id="o-1"))
    assert result.fill_price == 1.0998


def test_round_trip_with_spread_cost_reduces_pnl() -> None:
    """Spread must bleed into PnL: a long opened at ask and closed at bid
    loses the full spread even when the mid did not move."""
    feed = _BidAskQuoteFeed(
        quotes=[
            _bid_ask_quote(bid=1.0998, ask=1.1002),  # open long → ask 1.1002
            _bid_ask_quote(bid=1.0998, ask=1.1002),  # close → short at bid 1.0998
        ]
    )
    broker = PaperBroker(account_type="demo", quote_feed=feed)

    open_result = broker.place_order(_request(side="long", client_order_id="o-1"))
    close_result = broker.place_order(_request(side="short", client_order_id="o-2"))

    import pytest as _pytest

    units = 1000
    pnl = (close_result.fill_price - open_result.fill_price) * units
    # Spread = 0.0004, loss = 0.0004 * 1000 = 0.4
    assert pnl == _pytest.approx(-0.4)


def test_synthetic_spread_model_applied_when_bid_ask_missing() -> None:
    """When the Quote only carries mid, a BidAskSpreadModel can still make
    fills side-aware so backtests from mid-only sources stay cost-aware."""
    from fx_ai_trading.adapters.broker.paper import FixedPipSpreadModel

    feed = _ScriptedQuoteFeed(prices=[1.1000, 1.1000])  # mid only
    broker = PaperBroker(
        account_type="demo",
        quote_feed=feed,
        spread_model=FixedPipSpreadModel(spread_pip=1.0),  # 1 pip round-trip
    )

    long_result = broker.place_order(_request(side="long", client_order_id="o-1"))
    short_result = broker.place_order(_request(side="short", client_order_id="o-2"))

    import pytest as _pytest

    # 1 pip = 0.0001 on EUR_USD, half-spread = 0.00005.
    assert long_result.fill_price == _pytest.approx(1.1000 + 0.00005)
    assert short_result.fill_price == _pytest.approx(1.1000 - 0.00005)


def test_mid_quote_without_spread_model_falls_back_to_legacy_mid_fill() -> None:
    """Existing tests that only care about mid-driven PnL must keep working:
    a mid-only Quote + no spread_model reproduces the pre-9.10 behavior."""
    feed = _ScriptedQuoteFeed(prices=[1.10, 1.12])
    broker = PaperBroker(account_type="demo", quote_feed=feed)  # no spread_model
    long_result = broker.place_order(_request(side="long", client_order_id="o-1"))
    short_result = broker.place_order(_request(side="short", client_order_id="o-2"))
    # Mid-only fills — same as the legacy round-trip test above.
    assert long_result.fill_price == 1.10
    assert short_result.fill_price == 1.12


def test_jpy_pip_size_applied_in_spread_model() -> None:
    from fx_ai_trading.adapters.broker.paper import FixedPipSpreadModel

    model = FixedPipSpreadModel(spread_pip=1.0)
    # JPY pairs: pip = 0.01, half-spread = 0.005.
    assert model.half_spread("USD_JPY") == 0.005
    # Non-JPY pairs: pip = 0.0001, half-spread = 0.00005.
    assert model.half_spread("EUR_USD") == 0.00005


def test_spread_model_rejects_negative_pip() -> None:
    import pytest as _pytest

    from fx_ai_trading.adapters.broker.paper import FixedPipSpreadModel

    with _pytest.raises(ValueError, match="spread_pip must be >= 0"):
        FixedPipSpreadModel(spread_pip=-0.5)
