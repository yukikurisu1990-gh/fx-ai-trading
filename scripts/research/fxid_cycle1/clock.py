# ruff: noqa: E501 -- clock prose
"""夏時間に正しい時計（事前定義）。UTC を通年固定しない。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

- 取引日: NY 17:00（OANDA の rollover）で区切る。NY 17:00 以降は翌取引日。
- 開場（各地の現地時刻、事前定義）: 東京 09:00 Asia/Tokyo、London 08:00 Europe/London、NY 08:00 America/New_York。
- 米国の定時発表の時刻（現地時刻）: 08:30 と 10:00 America/New_York（発表の有無は見ない。時計の窓だけ）。
"""

from __future__ import annotations

from typing import Final
from zoneinfo import ZoneInfo

import pandas as pd

NEW_YORK: Final[ZoneInfo] = ZoneInfo("America/New_York")
LONDON: Final[ZoneInfo] = ZoneInfo("Europe/London")
TOKYO: Final[ZoneInfo] = ZoneInfo("Asia/Tokyo")

#: name -> (zone, hour, minute)
ANCHORS: Final[dict[str, tuple[ZoneInfo, int, int]]] = {
    "tokyo_open_0900": (TOKYO, 9, 0),
    "london_open_0800": (LONDON, 8, 0),
    "ny_open_0800": (NEW_YORK, 8, 0),
    "us_release_0830": (NEW_YORK, 8, 30),
    "us_release_1000": (NEW_YORK, 10, 0),
}
ROLLOVER_NY: Final[tuple[int, int]] = (17, 0)


def ny_time(ts: pd.Series) -> pd.Series:
    """UTC の timestamp を NY 現地時刻へ。"""
    return pd.to_datetime(ts, utc=True).dt.tz_convert(NEW_YORK)


def trading_day(ts: pd.Series) -> pd.Series:
    """NY 17:00 で区切った取引日（NY 17:00 以降は翌日）。"""
    local = ny_time(ts)
    shifted = local + pd.Timedelta(hours=24 - ROLLOVER_NY[0])
    return shifted.dt.date


def anchor_utc(day: pd.Timestamp, name: str) -> pd.Timestamp:
    """その暦日（現地）の anchor の UTC 時刻。"""
    zone, hour, minute = ANCHORS[name]
    local = pd.Timestamp(
        year=day.year, month=day.month, day=day.day, hour=hour, minute=minute, tz=zone
    )
    return local.tz_convert("UTC")


def anchor_series(first: str, last: str, name: str) -> pd.DatetimeIndex:
    """first … last の平日（現地の曜日）の anchor の UTC 時刻の列。"""
    days = pd.date_range(first, last, freq="D")
    out = [anchor_utc(d, name) for d in days if d.dayofweek < 5]
    return pd.DatetimeIndex(out)


__all__ = ["ANCHORS", "anchor_series", "anchor_utc", "ny_time", "trading_day"]
