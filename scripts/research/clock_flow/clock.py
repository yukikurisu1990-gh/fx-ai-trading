"""The wall-clock moments institutions are bound to, resolved to UTC per date.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Why this is not a constant
--------------------------

The WM/Refinitiv benchmark is struck at **16:00 London**, which is 16:00 UTC for
roughly five months of the year and 15:00 UTC for the other seven. The New York
option cut is 10:00 in New York, which is 14:00 or 15:00 UTC. A study that pins
these to a fixed UTC hour is not studying one moment — it is studying a mixture
of the moment and the hour beside it, in a proportion that changes with the
season, and the exploratory probe that motivated this package did exactly that.

So every moment here is a *local* time in a named zone, converted per date. The
conversion is the point of the module, and `moment_utc` is the only way to get
one.

A second thing an audit should be able to check: this file contains no market
data path and no span bound. It maps dates to timestamps. What keeps the fresh
pool unreachable is the span guard inside each reader route; nothing here can
widen it, because nothing here opens anything.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Final
from zoneinfo import ZoneInfo

import pandas as pd

LONDON: Final[ZoneInfo] = ZoneInfo("Europe/London")
NEW_YORK: Final[ZoneInfo] = ZoneInfo("America/New_York")
TOKYO: Final[ZoneInfo] = ZoneInfo("Asia/Tokyo")
UTC: Final[dt.timezone] = dt.UTC

#: name -> (zone, hour, minute). Local wall-clock, converted per date.
#:
#: `london_fix` is the WM/Refinitiv 16:00 benchmark — the one index funds,
#: benchmark-tracking mandates and month-end hedge rebalancing transact against.
#: `ny_option_cut` is the 10:00 expiry convention for vanilla FX options.
#: `tokyo_fix` is the 09:55 bank fixing that Japanese importer and exporter flow
#: is settled at. `rollover` is 17:00 New York, when the value date rolls and
#: liquidity is thinnest — the only moment here studied for its cost rather than
#: its direction.
MOMENTS: Final[dict[str, tuple[ZoneInfo, int, int]]] = {
    "london_fix": (LONDON, 16, 0),
    "ny_option_cut": (NEW_YORK, 10, 0),
    "tokyo_fix": (TOKYO, 9, 55),
    "london_open": (LONDON, 8, 0),
    "rollover": (NEW_YORK, 17, 0),
}


def moment_utc(day: dt.date, name: str) -> dt.datetime:
    """The UTC instant of a named institutional moment on that calendar date.

    The date is the *local* date in the moment's own zone. For `rollover`, 17:00
    New York on a Monday is 21:00 or 22:00 UTC the same Monday; for `tokyo_fix`,
    09:55 Tokyo is the previous UTC day's evening, and callers that group by UTC
    day must handle that rather than assume it away.
    """
    zone, hour, minute = MOMENTS[name]
    local = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone)
    return local.astimezone(UTC)


def utc_offset_hours(day: dt.date, name: str) -> float:
    """How far the moment sat from UTC on that date. Reported, not assumed."""
    zone, hour, minute = MOMENTS[name]
    local = dt.datetime(day.year, day.month, day.day, hour, minute, tzinfo=zone)
    offset = local.utcoffset()
    return 0.0 if offset is None else offset.total_seconds() / 3600.0


def month_end_days(days: list[dt.date]) -> set[dt.date]:
    """The last **observed trading day** of each calendar month.

    Derived from the days the panel actually contains, not from a calendar: the
    last business day of a month is a holiday somewhere often enough that a
    calendar rule and the data disagree, and the flow follows the day the market
    is open.
    """
    last: dict[tuple[int, int], dt.date] = {}
    for day in days:
        key = (day.year, day.month)
        if key not in last or day > last[key]:
            last[key] = day
    return set(last.values())


def quarter_end_days(days: list[dt.date]) -> set[dt.date]:
    """Month-ends that close a quarter. A strict subset of `month_end_days`."""
    return {day for day in month_end_days(days) if day.month in (3, 6, 9, 12)}


def session_of(stamp: pd.Timestamp) -> str:
    """Which trading session a UTC timestamp falls in, by London local hour.

    Coarse by design: the cell that uses it is a diagnostic, and a finer split
    would multiply cells without adding a mechanism.
    """
    hour = (
        stamp.tz_localize(UTC).astimezone(LONDON).hour
        if stamp.tzinfo is None
        else stamp.astimezone(LONDON).hour
    )
    if 0 <= hour < 7:
        return "asia"
    if 7 <= hour < 12:
        return "london_only"
    if 12 <= hour < 17:
        return "overlap"
    return "new_york_late"


def describe(days: list[dt.date]) -> dict[str, Any]:
    """A record of what the clock resolved to, for the artifact.

    Reports the *distribution* of UTC hours each moment landed on, so a reader
    can see that `london_fix` really did split across two hours and in what
    proportion — the thing the fixed-hour probe hid.
    """
    out: dict[str, Any] = {}
    for name in MOMENTS:
        hours: dict[str, int] = {}
        for day in days:
            hour = moment_utc(day, name).strftime("%H:%M")
            hours[hour] = hours.get(hour, 0) + 1
        out[name] = {
            "utc_times_observed": dict(sorted(hours.items())),
            "n_days": len(days),
        }
    out["month_end_days"] = len(month_end_days(days))
    out["quarter_end_days"] = len(quarter_end_days(days))
    #: Everything in this subtree is a count of days, not a price. Declared so
    #: the unit audit skips it rather than reporting every `"15:00"` key as a
    #: quantity that escaped conversion.
    out["_unit"] = "count"
    return out


__all__ = [
    "LONDON",
    "MOMENTS",
    "NEW_YORK",
    "TOKYO",
    "describe",
    "moment_utc",
    "month_end_days",
    "quarter_end_days",
    "session_of",
    "utc_offset_hours",
]
