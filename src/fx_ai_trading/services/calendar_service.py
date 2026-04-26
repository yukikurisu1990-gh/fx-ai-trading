"""CalendarService — causal economic calendar feature computation (Phase 9.X-H).

Loads a curated CSV of high-importance scheduled events and derives 9
calendar features per (bar, pair):

  hours_to_next_event_base       hours_since_last_event_base
  hours_to_next_event_quote      hours_since_last_event_quote
  in_pre_event_window            in_post_event_window
  in_quiet_window
  event_importance_next          event_importance_recent

Causal invariant
----------------
"hours_to_next_event_base" uses ONLY the timestamp of future events
(not their actual values). Future timestamps are public information
(FOMC schedule etc. is published months in advance), so referencing
them does not constitute lookahead. Actual / forecast / surprise
values are NOT used by v1.

CSV format
----------
data/economic_calendar/events_<range>.csv

  timestamp_utc,currency,event_name,importance
  2025-09-17T18:00:00Z,USD,FOMC Rate Decision,high
  2025-09-05T12:30:00Z,USD,Non-Farm Payrolls,high

  importance ∈ {low, medium, high} — only `medium` and `high` enter
  the features. `low` rows are filtered out at load.

Production loader
-----------------
For live trading, the same loader signature accepts events fetched
from the OANDA Labs `/labs/v1/calendar` endpoint after normalisation
to the CSV schema. Backtest and production share this module.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Pre-event / post-event / quiet windows (hours from event timestamp).
PRE_EVENT_HOURS = 0.5  # 30 min before
POST_EVENT_HOURS = 1.0  # 60 min after
QUIET_HALF_HOURS = 2.0  # ±2h gap → "quiet"

# Importance string → numeric (0/0.5/1.0).
_IMPORTANCE_MAP: dict[str, float] = {
    "low": 0.0,
    "medium": 0.5,
    "high": 1.0,
}

# Currencies recognised — anything else in CSV is skipped.
_VALID_CURRENCIES: frozenset[str] = frozenset(
    {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"}
)


@dataclass(frozen=True)
class CalendarEvent:
    timestamp: datetime  # tz-aware UTC
    currency: str
    event_name: str
    importance: str


class CalendarService:
    """Loads events from CSV; derives per-bar per-pair features.

    The service is stateless aside from the loaded events list; it is
    safe to share a single instance across pairs and folds.
    """

    def __init__(self, events: list[CalendarEvent]) -> None:
        # Sort by timestamp so binary-search / linear scans are easy.
        self._events_by_currency: dict[str, list[CalendarEvent]] = {}
        for c in _VALID_CURRENCIES:
            self._events_by_currency[c] = []
        for ev in sorted(events, key=lambda e: e.timestamp):
            if ev.currency not in _VALID_CURRENCIES:
                continue
            if ev.importance not in _IMPORTANCE_MAP:
                continue
            if _IMPORTANCE_MAP[ev.importance] == 0.0:
                # Skip "low" — only medium/high contribute.
                continue
            self._events_by_currency[ev.currency].append(ev)

    @classmethod
    def from_csv(cls, path: Path | str) -> CalendarService:
        events: list[CalendarEvent] = []
        with Path(path).open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    ts_str = row["timestamp_utc"].strip()
                    # Accept both "2025-09-17T18:00:00Z" and "...+00:00".
                    if ts_str.endswith("Z"):
                        ts_str = ts_str[:-1] + "+00:00"
                    ts = datetime.fromisoformat(ts_str)
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=UTC)
                    events.append(
                        CalendarEvent(
                            timestamp=ts.astimezone(UTC),
                            currency=row["currency"].strip().upper(),
                            event_name=row["event_name"].strip(),
                            importance=row["importance"].strip().lower(),
                        )
                    )
                except (KeyError, ValueError):
                    # Silently skip malformed rows — operator will see the
                    # count via len(events) on the loaded service.
                    continue
        return cls(events)

    def event_count(self, currency: str) -> int:
        return len(self._events_by_currency.get(currency.upper(), []))

    def compute_features(
        self,
        instrument: str,
        as_of_time: datetime,
    ) -> dict[str, float]:
        """Return the 9 calendar features for a single (pair, bar).

        Causal: only event timestamps are used. No actual/forecast values.
        For events whose `timestamp` is in the future, the model "knows"
        they exist (public schedule). Past events are discoverable from
        history.
        """
        as_of = _ensure_utc(as_of_time)
        base, quote = _split_pair(instrument)

        h_to_next_base, imp_next_base = self._next_event_distance(base, as_of)
        h_since_last_base, imp_recent_base = self._last_event_distance(base, as_of)
        h_to_next_quote, imp_next_quote = self._next_event_distance(quote, as_of)
        h_since_last_quote, imp_recent_quote = self._last_event_distance(quote, as_of)

        # Combined max-importance for "any currency in this pair, near in time".
        h_to_next = min(h_to_next_base, h_to_next_quote)
        h_since_last = min(h_since_last_base, h_since_last_quote)
        imp_next = max(imp_next_base, imp_next_quote)
        imp_recent = max(imp_recent_base, imp_recent_quote)

        in_pre = 1.0 if h_to_next <= PRE_EVENT_HOURS else 0.0
        in_post = 1.0 if h_since_last <= POST_EVENT_HOURS else 0.0
        in_quiet = 1.0 if h_to_next > QUIET_HALF_HOURS and h_since_last > QUIET_HALF_HOURS else 0.0

        return {
            "cal_h_to_next_base": round(h_to_next_base, 4),
            "cal_h_since_last_base": round(h_since_last_base, 4),
            "cal_h_to_next_quote": round(h_to_next_quote, 4),
            "cal_h_since_last_quote": round(h_since_last_quote, 4),
            "cal_in_pre_event": in_pre,
            "cal_in_post_event": in_post,
            "cal_in_quiet": in_quiet,
            "cal_imp_next": round(imp_next, 2),
            "cal_imp_recent": round(imp_recent, 2),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    _SENTINEL_FAR_HOURS = 999.0

    def _next_event_distance(self, currency: str, as_of: datetime) -> tuple[float, float]:
        """Return (hours_to_next_event, importance_of_next).

        Sentinel ``_SENTINEL_FAR_HOURS`` and importance 0.0 if no future
        event exists.
        """
        events = self._events_by_currency.get(currency, [])
        for ev in events:
            if ev.timestamp > as_of:
                delta = ev.timestamp - as_of
                hours = delta.total_seconds() / 3600.0
                imp = _IMPORTANCE_MAP[ev.importance]
                return hours, imp
        return self._SENTINEL_FAR_HOURS, 0.0

    def _last_event_distance(self, currency: str, as_of: datetime) -> tuple[float, float]:
        """Return (hours_since_last_event, importance_of_last).

        Sentinel ``_SENTINEL_FAR_HOURS`` and importance 0.0 if no past
        event exists.
        """
        events = self._events_by_currency.get(currency, [])
        # Iterate reverse so first match is the most-recent past event.
        for ev in reversed(events):
            if ev.timestamp <= as_of:
                delta = as_of - ev.timestamp
                hours = delta.total_seconds() / 3600.0
                imp = _IMPORTANCE_MAP[ev.importance]
                return hours, imp
        return self._SENTINEL_FAR_HOURS, 0.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts.astimezone(UTC)


def _split_pair(instrument: str) -> tuple[str, str]:
    parts = instrument.split("_")
    if len(parts) != 2:
        raise ValueError(f"Invalid instrument {instrument!r} (expected 'XXX_YYY')")
    return parts[0].upper(), parts[1].upper()


# ---------------------------------------------------------------------------
# Zero-feature defaults (used by callers when CalendarService is unavailable)
# ---------------------------------------------------------------------------


CALENDAR_ZERO_FEATURES: dict[str, float] = {
    "cal_h_to_next_base": CalendarService._SENTINEL_FAR_HOURS,
    "cal_h_since_last_base": CalendarService._SENTINEL_FAR_HOURS,
    "cal_h_to_next_quote": CalendarService._SENTINEL_FAR_HOURS,
    "cal_h_since_last_quote": CalendarService._SENTINEL_FAR_HOURS,
    "cal_in_pre_event": 0.0,
    "cal_in_post_event": 0.0,
    "cal_in_quiet": 1.0,  # absence of calendar = "quiet" prior
    "cal_imp_next": 0.0,
    "cal_imp_recent": 0.0,
}


def empty_calendar() -> CalendarService:
    """Return a CalendarService with no events — useful for fallback."""
    return CalendarService(events=[])


# Maintain backward-compatibility for callers that probe the constant via
# attribute lookup.
_ = timedelta  # silence unused-import warning if timedelta not referenced elsewhere
