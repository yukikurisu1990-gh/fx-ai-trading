"""Unit tests for the M-3a Quote / QuoteFeed / callable_to_quote_feed surface.

Scope (M-3a only):
  - ``Quote`` is frozen and rejects naive datetimes.
  - ``callable_to_quote_feed`` wraps a ``Callable[[str], float]`` so that
    its result satisfies the ``QuoteFeed`` Protocol and forwards
    price / clock-time / source faithfully.

Out of scope (deferred to M-3b/c/d): run_exit_gate wiring, staleness
enforcement, supervisor changes.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

import pytest

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.price_feed import (
    SOURCE_LEGACY_CALLABLE,
    SOURCE_OANDA_LIVE,
    SOURCE_OANDA_REST_SNAPSHOT,
    SOURCE_PAPER,
    SOURCE_TEST_FIXTURE,
    Quote,
    QuoteFeed,
    callable_to_quote_feed,
)

_FIXED_AT = datetime(2026, 4, 22, 12, 0, 0, tzinfo=UTC)


class TestQuote:
    def test_accepts_utc_datetime(self) -> None:
        q = Quote(price=1.2345, ts=_FIXED_AT, source=SOURCE_TEST_FIXTURE)
        assert q.price == 1.2345
        assert q.ts == _FIXED_AT
        assert q.source == SOURCE_TEST_FIXTURE

    def test_accepts_non_utc_tz_aware_datetime(self) -> None:
        # Any tz-aware datetime is accepted; the rule is "must carry tzinfo",
        # not "must be UTC" — converting at construction would silently drop
        # the producer's recorded zone.
        jst = timezone(timedelta(hours=9))
        ts = datetime(2026, 4, 22, 21, 0, 0, tzinfo=jst)
        q = Quote(price=1.0, ts=ts, source=SOURCE_TEST_FIXTURE)
        assert q.ts.tzinfo is jst

    def test_rejects_naive_datetime(self) -> None:
        naive = datetime(2026, 4, 22, 12, 0, 0)
        with pytest.raises(ValueError, match="timezone-aware"):
            Quote(price=1.0, ts=naive, source=SOURCE_TEST_FIXTURE)

    def test_is_frozen(self) -> None:
        q = Quote(price=1.0, ts=_FIXED_AT, source=SOURCE_TEST_FIXTURE)
        with pytest.raises(FrozenInstanceError):
            q.price = 2.0  # type: ignore[misc]

    def test_source_constants_are_str(self) -> None:
        # Sanity: typo-prevention constants must all resolve to plain str.
        for s in (
            SOURCE_LEGACY_CALLABLE,
            SOURCE_OANDA_LIVE,
            SOURCE_OANDA_REST_SNAPSHOT,
            SOURCE_PAPER,
            SOURCE_TEST_FIXTURE,
        ):
            assert isinstance(s, str)
            assert s  # non-empty


class TestCallableToQuoteFeed:
    def test_returns_quote_with_callable_price(self) -> None:
        clock = FixedClock(_FIXED_AT)
        feed = callable_to_quote_feed(lambda inst: 1.2345, clock=clock)
        q = feed.get_quote("EUR_USD")
        assert q.price == 1.2345

    def test_ts_uses_clock_now_not_real_time(self) -> None:
        clock = FixedClock(_FIXED_AT)
        feed = callable_to_quote_feed(lambda _: 1.0, clock=clock)
        q = feed.get_quote("EUR_USD")
        assert q.ts == _FIXED_AT

    def test_default_source_is_legacy_callable(self) -> None:
        clock = FixedClock(_FIXED_AT)
        feed = callable_to_quote_feed(lambda _: 1.0, clock=clock)
        q = feed.get_quote("EUR_USD")
        assert q.source == SOURCE_LEGACY_CALLABLE

    def test_source_override_is_reflected(self) -> None:
        clock = FixedClock(_FIXED_AT)
        feed = callable_to_quote_feed(lambda _: 1.0, clock=clock, source=SOURCE_PAPER)
        q = feed.get_quote("EUR_USD")
        assert q.source == SOURCE_PAPER

    def test_instrument_is_forwarded_to_callable(self) -> None:
        seen: list[str] = []

        def _spy(instrument: str) -> float:
            seen.append(instrument)
            return 1.0

        clock = FixedClock(_FIXED_AT)
        feed = callable_to_quote_feed(_spy, clock=clock)
        feed.get_quote("USD_JPY")
        feed.get_quote("EUR_USD")
        assert seen == ["USD_JPY", "EUR_USD"]

    def test_satisfies_quote_feed_protocol_isinstance(self) -> None:
        clock = FixedClock(_FIXED_AT)
        feed = callable_to_quote_feed(lambda _: 1.0, clock=clock)
        # @runtime_checkable on QuoteFeed lets isinstance verify the
        # adapter conforms to the structural contract.
        assert isinstance(feed, QuoteFeed)
