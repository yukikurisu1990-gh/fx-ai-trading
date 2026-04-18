"""EventCalendarService — economic event calendar skeleton (D3 §2 / 6.3 / M9).

Implements the EventCalendar Protocol.

Stale failsafe invariant (6.3):
  is_stale() returns True when now() - last_updated_at > max_staleness_hours.
  MetaDecider.Filter must check is_stale() and produce no_trade if True.

M9 scope:
  - Events are provided at construction time (list injection for testability).
  - Clock is injected for now() so tests can control time without calling datetime.now().
  - refresh() is a no-op (CSV / API fetch is Phase 7).
  - get_upcoming() returns high-impact events matching currency within the window.

Phase 7: implement CSV / OANDA economic calendar fetch in refresh().
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.domain.event_calendar import EconomicEvent

_log = logging.getLogger(__name__)

_DEFAULT_MAX_STALENESS_HOURS = 24
_HIGH_IMPACT = "high"


class EventCalendarService:
    """Economic event calendar with stale failsafe for M9.

    Args:
        events: Pre-loaded list of EconomicEvent objects.
            In production this is loaded from CSV / API before startup.
        last_updated_at: Timestamp of the most recent calendar refresh.
            Defaults to UTC epoch (immediately stale) if not provided.
        max_staleness_hours: Hours before the calendar is considered stale.
            Overrides the app_settings value for test control.
        clock: Clock for now() computation. Defaults to WallClock.
    """

    def __init__(
        self,
        events: list[EconomicEvent] | None = None,
        last_updated_at: datetime | None = None,
        max_staleness_hours: int = _DEFAULT_MAX_STALENESS_HOURS,
        clock: Clock | None = None,
    ) -> None:
        self._events: list[EconomicEvent] = events or []
        self._last_updated_at: datetime = last_updated_at or datetime(1970, 1, 1, tzinfo=UTC)
        self._max_staleness_hours = max_staleness_hours
        self._clock: Clock = clock or WallClock()

    @property
    def last_updated_at(self) -> datetime:
        """Timestamp of the last successful calendar refresh."""
        return self._last_updated_at

    @property
    def max_staleness_hours(self) -> int:
        """Configured staleness threshold in hours."""
        return self._max_staleness_hours

    def is_stale(self) -> bool:
        """Return True when calendar data exceeds max_staleness_hours (6.3)."""
        now = self._clock.now()
        age = now - self._last_updated_at
        stale = age > timedelta(hours=self._max_staleness_hours)
        if stale:
            _log.warning(
                "EventCalendarService.is_stale: calendar is stale (age=%s, threshold=%dh)",
                age,
                self._max_staleness_hours,
            )
        return stale

    def get_upcoming(self, currency: str, within_minutes: int) -> list[EconomicEvent]:
        """Return high-impact events for *currency* within *within_minutes*.

        Only high-impact events are returned (MetaDecider Filter uses these).
        """
        now = self._clock.now()
        cutoff = now + timedelta(minutes=within_minutes)
        return [
            e
            for e in self._events
            if e.currency == currency
            and e.impact == _HIGH_IMPACT
            and now <= e.scheduled_utc <= cutoff
        ]

    def refresh(self) -> None:
        """M9 skeleton — no-op.

        Phase 7: fetch latest calendar from CSV / OANDA economic calendar API.
        """
        _log.debug("EventCalendarService.refresh: skeleton — no-op (M9)")
