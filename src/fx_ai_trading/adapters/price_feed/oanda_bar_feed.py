"""OandaBarFeed — live bar-cadence feed via OANDA REST candles API (Phase 9.2).

Polls OANDA for the latest completed candle at each bar boundary and yields
one ``Candle`` per completed bar through the ``BarFeed`` Protocol.

Phase 1 I-1: sell/buy decisions are made at 1m/5m bar granularity, not tick.
This feed is the live counterpart to ``CandleFileBarFeed`` (replay).

Design:
  - ``__iter__`` yields completed ``Candle`` objects in ascending time order.
  - Waits for the next bar boundary (aligned to granularity), then polls
    OANDA for ``count=2`` (last two bars) to ensure the most recent bar
    is *complete* — the second-to-last bar is the latest completed one.
  - ``poll_interval_seconds`` controls how often to re-check after a
    boundary miss (default 5 s).  Jitter-free; callers can wrap in retry.
  - ``max_bars`` limits total bars yielded (0 = unlimited, for testing).
  - StopIteration when ``max_bars`` is reached or ``_stop`` is set via
    ``stop()``.

Boundary alignment:
  - M1: boundaries at :00 of every minute.
  - M5: boundaries at :00, :05, :10, … of every hour.
  - Other granularities (M15, H1, etc.) are accepted but alignment is
    computed relative to the granularity's seconds per bar.

Deduplication: the last yielded bar's ``time_utc`` is remembered; the same
bar is never yielded twice (guards against clock skew / early poll).
"""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.domain.price_feed import Candle

if TYPE_CHECKING:
    from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient

_log = logging.getLogger(__name__)

# Seconds per bar for common granularities.
_GRANULARITY_SECONDS: dict[str, int] = {
    "S5": 5,
    "S10": 10,
    "S15": 15,
    "S30": 30,
    "M1": 60,
    "M2": 120,
    "M4": 240,
    "M5": 300,
    "M10": 600,
    "M15": 900,
    "M30": 1800,
    "H1": 3600,
    "H2": 7200,
    "H4": 14400,
    "H6": 21600,
    "H8": 28800,
    "H12": 43200,
    "D": 86400,
}


class OandaBarFeed:
    """Live OANDA bar feed that yields one completed Candle per bar.

    Args:
        client: ``OandaAPIClient`` instance.
        instrument: Instrument to fetch bars for (e.g. ``"EUR_USD"``).
        granularity: OANDA granularity string (default ``"M5"``).
        poll_interval_seconds: Seconds between re-polls while waiting for
            next boundary (default 5).
        max_bars: Maximum bars to yield before stopping (0 = unlimited).
    """

    def __init__(
        self,
        client: OandaAPIClient,
        instrument: str,
        granularity: str = "M5",
        *,
        poll_interval_seconds: int = 5,
        max_bars: int = 0,
        clock: Clock = WallClock(),
    ) -> None:
        self._client = client
        self._instrument = instrument
        self._granularity = granularity
        self._poll_interval = poll_interval_seconds
        self._max_bars = max_bars
        self._stop_flag = False
        self._bar_seconds = _GRANULARITY_SECONDS.get(granularity, 300)
        self._clock = clock

    def stop(self) -> None:
        """Signal the feed to stop after the current bar."""
        self._stop_flag = True

    def __iter__(self) -> Iterator[Candle]:
        last_bar_time: datetime | None = None
        bars_yielded = 0

        while not self._stop_flag:
            if self._max_bars and bars_yielded >= self._max_bars:
                break

            # Wait until we are past a bar boundary.
            now = self._clock.now()
            secs_into_bar = int(now.timestamp()) % self._bar_seconds
            if secs_into_bar < self._poll_interval:
                # Near the boundary — poll OANDA now.
                candle = self._fetch_latest_completed()
                if candle is not None and candle.time_utc != last_bar_time:
                    last_bar_time = candle.time_utc
                    bars_yielded += 1
                    yield candle
                    continue

            # Not yet at a boundary — sleep until close to it.
            secs_to_boundary = self._bar_seconds - secs_into_bar
            sleep_for = max(1, secs_to_boundary - self._poll_interval)
            _log.debug(
                "OandaBarFeed: %s bars=%d sleep=%ds to boundary",
                self._granularity,
                bars_yielded,
                sleep_for,
            )
            time.sleep(sleep_for)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _fetch_latest_completed(self) -> Candle | None:
        """Fetch the latest COMPLETED bar from OANDA.

        Requests count=2 (last two bars); the SECOND-TO-LAST is the most
        recent complete bar (the last bar may still be forming).
        """
        try:
            response = self._client.get_candles(
                self._instrument,
                params={
                    "granularity": self._granularity,
                    "count": 2,
                    "price": "M",  # mid-price candles
                },
            )
        except Exception:
            _log.warning(
                "OandaBarFeed: get_candles failed for %s — will retry",
                self._instrument,
                exc_info=True,
            )
            return None

        raw_candles = response.get("candles", [])
        # Take the second-to-last (index -2) if available, else the last.
        completed = [c for c in raw_candles if c.get("complete", True)]
        if not completed:
            return None

        raw = completed[-1]
        try:
            mid = raw["mid"]
            return Candle(
                instrument=self._instrument,
                tier=self._granularity,
                time_utc=_parse_oanda_time(raw["time"]),
                open=float(mid["o"]),
                high=float(mid["h"]),
                low=float(mid["l"]),
                close=float(mid["c"]),
                volume=int(raw.get("volume", 0)),
            )
        except (KeyError, ValueError):
            _log.warning("OandaBarFeed: malformed candle payload: %s", raw, exc_info=True)
            return None


def _parse_oanda_time(raw: str) -> datetime:
    """Parse OANDA RFC3339 timestamp (nanosecond precision) → UTC datetime."""
    raw = raw.rstrip("Z")
    if "." in raw:
        base, frac = raw.split(".", 1)
        raw = f"{base}.{frac[:6]}"
    return datetime.fromisoformat(raw).replace(tzinfo=UTC)


__all__ = ["OandaBarFeed"]
