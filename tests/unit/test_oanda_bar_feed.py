"""Unit tests: OandaBarFeed — boundary polling, dedup, max_bars, stop (Phase 9.2)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from fx_ai_trading.adapters.price_feed.oanda_bar_feed import OandaBarFeed, _parse_oanda_time
from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.price_feed import Candle


def _make_candle(ts: datetime, instrument: str = "EUR_USD") -> Candle:
    return Candle(
        instrument=instrument,
        tier="M5",
        time_utc=ts,
        open=1.1000,
        high=1.1050,
        low=1.0950,
        close=1.1020,
        volume=100,
    )


def _at_boundary_feed(
    instrument: str = "EUR_USD",
    granularity: str = "M5",
    max_bars: int = 0,
) -> OandaBarFeed:
    """Return a feed whose clock always lands at a bar boundary.

    timestamp=2 → int(2) % 300 = 2 < poll_interval(5) → always at boundary.
    """
    client = MagicMock()
    clock = FixedClock(datetime.fromtimestamp(2.0, tz=UTC))
    return OandaBarFeed(client, instrument, granularity, max_bars=max_bars, clock=clock)


class TestParseOandaTime:
    def test_basic_rfc3339_z_suffix(self) -> None:
        dt = _parse_oanda_time("2024-06-01T12:00:00.000000000Z")
        assert dt == datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)

    def test_no_z_suffix(self) -> None:
        dt = _parse_oanda_time("2024-06-01T12:00:00.123456")
        assert dt.tzinfo is UTC
        assert dt.microsecond == 123456

    def test_truncates_nanoseconds_to_microseconds(self) -> None:
        dt = _parse_oanda_time("2024-06-01T12:00:00.123456789Z")
        assert dt.microsecond == 123456

    def test_no_fractional_seconds(self) -> None:
        dt = _parse_oanda_time("2024-06-01T12:00:00Z")
        assert dt == datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)


class TestOandaBarFeedMaxBars:
    def _run_with_candles(self, candles: list[Candle | None], max_bars: int) -> list[Candle]:
        """Run the feed with _fetch_latest_completed returning the given sequence."""
        feed = _at_boundary_feed(max_bars=max_bars)
        feed._fetch_latest_completed = MagicMock(side_effect=candles)  # type: ignore[method-assign]
        with patch("fx_ai_trading.adapters.price_feed.oanda_bar_feed.time"):
            return list(feed)

    def test_max_bars_limits_output(self) -> None:
        t1 = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        t2 = datetime(2024, 6, 1, 12, 5, 0, tzinfo=UTC)
        bars = self._run_with_candles([_make_candle(t1), _make_candle(t2)], max_bars=2)
        assert len(bars) == 2

    def test_yields_candle_objects(self) -> None:
        t1 = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        bars = self._run_with_candles([_make_candle(t1)], max_bars=1)
        assert len(bars) == 1
        bar = bars[0]
        assert isinstance(bar, Candle)
        assert bar.instrument == "EUR_USD"
        assert bar.tier == "M5"
        assert bar.close == pytest.approx(1.1020)

    def test_none_from_fetch_not_yielded(self) -> None:
        t1 = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        # First fetch returns None (e.g. API miss), second returns a real candle.
        bars = self._run_with_candles([None, _make_candle(t1)], max_bars=1)
        assert len(bars) == 1
        assert bars[0].time_utc == t1


class TestOandaBarFeedDedup:
    def test_same_bar_not_yielded_twice(self) -> None:
        t1 = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        t2 = datetime(2024, 6, 1, 12, 5, 0, tzinfo=UTC)
        candle1 = _make_candle(t1)
        candle2 = _make_candle(t2)
        feed = _at_boundary_feed(max_bars=2)
        # candle1 returned twice (dedup skips 2nd), then candle2 — only 2 bars yielded.
        feed._fetch_latest_completed = MagicMock(  # type: ignore[method-assign]
            side_effect=[candle1, candle1, candle2]
        )

        with patch("fx_ai_trading.adapters.price_feed.oanda_bar_feed.time"):
            bars = list(feed)

        assert len(bars) == 2
        assert bars[0].time_utc == t1
        assert bars[1].time_utc == t2


class TestOandaBarFeedStop:
    def test_stop_halts_iteration(self) -> None:
        t1 = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        candle = _make_candle(t1)
        feed = _at_boundary_feed(max_bars=0)
        feed._fetch_latest_completed = MagicMock(return_value=candle)  # type: ignore[method-assign]

        collected: list[Candle] = []
        with patch("fx_ai_trading.adapters.price_feed.oanda_bar_feed.time"):
            for bar in feed:
                collected.append(bar)
                feed.stop()

        assert len(collected) == 1


class TestOandaBarFeedFetchLatestCompleted:
    """Unit tests for _fetch_latest_completed (no __iter__ mocking needed)."""

    def _raw(self, time: str, complete: bool = True) -> dict:
        return {
            "time": time,
            "complete": complete,
            "volume": 100,
            "mid": {"o": "1.1000", "h": "1.1050", "l": "1.0950", "c": "1.1020"},
        }

    def test_returns_last_complete_candle(self) -> None:
        t1 = "2024-06-01T12:00:00.000000000Z"
        t2 = "2024-06-01T12:05:00.000000000Z"
        client = MagicMock()
        client.get_candles.return_value = {"candles": [self._raw(t1), self._raw(t2)]}
        feed = OandaBarFeed(client, "EUR_USD", "M5")
        candle = feed._fetch_latest_completed()
        assert candle is not None
        assert candle.time_utc == datetime(2024, 6, 1, 12, 5, 0, tzinfo=UTC)

    def test_skips_incomplete_candles(self) -> None:
        t1 = "2024-06-01T12:00:00.000000000Z"
        client = MagicMock()
        client.get_candles.return_value = {"candles": [self._raw(t1, complete=False)]}
        feed = OandaBarFeed(client, "EUR_USD", "M5")
        assert feed._fetch_latest_completed() is None

    def test_empty_candles_returns_none(self) -> None:
        client = MagicMock()
        client.get_candles.return_value = {"candles": []}
        feed = OandaBarFeed(client, "EUR_USD", "M5")
        assert feed._fetch_latest_completed() is None

    def test_api_exception_returns_none(self) -> None:
        client = MagicMock()
        client.get_candles.side_effect = Exception("network error")
        feed = OandaBarFeed(client, "EUR_USD", "M5")
        assert feed._fetch_latest_completed() is None

    def test_candle_fields_parsed_correctly(self) -> None:
        client = MagicMock()
        client.get_candles.return_value = {"candles": [self._raw("2024-06-01T12:00:00Z")]}
        feed = OandaBarFeed(client, "EUR_USD", "M5")
        candle = feed._fetch_latest_completed()
        assert candle is not None
        assert candle.open == pytest.approx(1.1000)
        assert candle.high == pytest.approx(1.1050)
        assert candle.low == pytest.approx(1.0950)
        assert candle.close == pytest.approx(1.1020)
        assert candle.volume == 100
        assert candle.instrument == "EUR_USD"
        assert candle.tier == "M5"
