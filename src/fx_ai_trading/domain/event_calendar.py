"""EventCalendar domain interface and DTOs (D3 §2 / 6.3).

Stale failsafe (6.3): if is_stale() → MetaDecider Filter treats all candidates as
near-event and returns no_trade. PriceAnomalyGuard provides a second independent
defence (flash-halt via ATR multiplier).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EconomicEvent:
    """A scheduled economic calendar event."""

    event_id: str
    currency: str
    title: str
    impact: str  # high | medium | low
    scheduled_utc: datetime


# ---------------------------------------------------------------------------
# Interface (Protocol)
# ---------------------------------------------------------------------------


class EventCalendar(Protocol):
    """Economic event calendar with stale-failsafe (D3 §2 / 6.3).

    Stale failsafe invariant (6.3):
      - is_stale() returns True when now - last_updated_at > max_staleness_hours.
      - MetaDecider Filter must check is_stale() before querying events;
        stale calendar → treat all instruments as near-event → no_trade.

    max_staleness_hours default: 24 (app_settings key event_calendar_max_staleness_hours).
    """

    @property
    def last_updated_at(self) -> datetime:
        """Timestamp of the last successful calendar refresh."""
        ...

    @property
    def max_staleness_hours(self) -> int:
        """Configured staleness threshold in hours (default 24)."""
        ...

    def is_stale(self) -> bool:
        """Return True when calendar data exceeds max_staleness_hours."""
        ...

    def get_upcoming(
        self,
        currency: str,
        within_minutes: int,
    ) -> list[EconomicEvent]:
        """Return high-impact events for *currency* within *within_minutes*."""
        ...

    def refresh(self) -> None:
        """Fetch latest calendar data and update last_updated_at.

        Side effect: writes to economic_events table via Repository.
        """
        ...
