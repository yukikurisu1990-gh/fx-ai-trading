"""Generate a curated economic-calendar CSV for the 9-month walk-forward.

Phase 9.X-H/H-1 — produce data/economic_calendar/events_2025_2026.csv.

Strategy:
- FOMC, ECB, BOJ, BOE, RBA, BOC, RBNZ, SNB rate-decision dates: hard-coded
  from the 2025-2026 published meeting calendars (verify before live use).
- NFP, CPI, retail sales: derived from monthly recurring rules
  (NFP = first Friday 12:30 UTC during EDT / 13:30 UTC during EST).

Run: python tools/generate_calendar_csv.py

Output: data/economic_calendar/events_2025_2026.csv
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

OUT_PATH = Path("data/economic_calendar/events_2025_2026.csv")

# 2025-2026 FOMC meetings (8 per year), confirmed from Federal Reserve.
# Decision time = 18:00 UTC (14:00 ET) on the second day of each two-day meeting.
FOMC_DATES_UTC: list[datetime] = [
    datetime(2025, 7, 30, 18, 0, tzinfo=UTC),
    datetime(2025, 9, 17, 18, 0, tzinfo=UTC),
    datetime(2025, 10, 29, 18, 0, tzinfo=UTC),
    datetime(2025, 12, 10, 19, 0, tzinfo=UTC),  # EST: 14:00 ET = 19:00 UTC
    datetime(2026, 1, 28, 19, 0, tzinfo=UTC),
    datetime(2026, 3, 18, 18, 0, tzinfo=UTC),  # back to EDT
    datetime(2026, 4, 29, 18, 0, tzinfo=UTC),
    datetime(2026, 6, 17, 18, 0, tzinfo=UTC),
]

# ECB rate decisions (8 per year). Published time 13:15 CET (~12:15 UTC during CEST).
ECB_DATES_UTC: list[datetime] = [
    datetime(2025, 7, 24, 12, 15, tzinfo=UTC),
    datetime(2025, 9, 11, 12, 15, tzinfo=UTC),
    datetime(2025, 10, 30, 13, 15, tzinfo=UTC),  # CET (DST ends Oct)
    datetime(2025, 12, 18, 13, 15, tzinfo=UTC),
    datetime(2026, 1, 29, 13, 15, tzinfo=UTC),
    datetime(2026, 3, 12, 13, 15, tzinfo=UTC),
    datetime(2026, 4, 16, 12, 15, tzinfo=UTC),  # CEST starts late March
    datetime(2026, 6, 4, 12, 15, tzinfo=UTC),
]

# BOJ rate decisions (~8 per year). Published time ~03:00-04:00 UTC.
BOJ_DATES_UTC: list[datetime] = [
    datetime(2025, 7, 31, 3, 0, tzinfo=UTC),
    datetime(2025, 9, 19, 3, 0, tzinfo=UTC),
    datetime(2025, 10, 31, 3, 0, tzinfo=UTC),
    datetime(2025, 12, 19, 3, 0, tzinfo=UTC),
    datetime(2026, 1, 23, 3, 0, tzinfo=UTC),
    datetime(2026, 3, 19, 3, 0, tzinfo=UTC),
    datetime(2026, 4, 28, 3, 0, tzinfo=UTC),
    datetime(2026, 6, 17, 3, 0, tzinfo=UTC),
]

# BOE rate decisions (8 per year). Published time 11:00 UTC (12:00 BST).
BOE_DATES_UTC: list[datetime] = [
    datetime(2025, 8, 7, 11, 0, tzinfo=UTC),
    datetime(2025, 9, 18, 11, 0, tzinfo=UTC),
    datetime(2025, 11, 6, 12, 0, tzinfo=UTC),  # GMT after Oct DST end
    datetime(2025, 12, 18, 12, 0, tzinfo=UTC),
    datetime(2026, 2, 5, 12, 0, tzinfo=UTC),
    datetime(2026, 3, 19, 12, 0, tzinfo=UTC),
    datetime(2026, 5, 7, 11, 0, tzinfo=UTC),  # BST starts late March
    datetime(2026, 6, 18, 11, 0, tzinfo=UTC),
]

# RBA rate decisions (~11 per year, first Tue of month except Jan).
RBA_DATES_UTC: list[datetime] = [
    datetime(2025, 8, 5, 4, 30, tzinfo=UTC),  # 14:30 AEST = 04:30 UTC
    datetime(2025, 9, 30, 4, 30, tzinfo=UTC),
    datetime(2025, 11, 4, 3, 30, tzinfo=UTC),  # AEDT starts Oct = -11:00 from UTC
    datetime(2025, 12, 9, 3, 30, tzinfo=UTC),
    datetime(2026, 2, 17, 3, 30, tzinfo=UTC),
    datetime(2026, 3, 31, 3, 30, tzinfo=UTC),
    datetime(2026, 5, 5, 4, 30, tzinfo=UTC),  # AEST after Apr DST end
    datetime(2026, 6, 23, 4, 30, tzinfo=UTC),
]

# BOC rate decisions (8 per year).
BOC_DATES_UTC: list[datetime] = [
    datetime(2025, 7, 30, 13, 45, tzinfo=UTC),
    datetime(2025, 9, 17, 13, 45, tzinfo=UTC),
    datetime(2025, 10, 29, 13, 45, tzinfo=UTC),
    datetime(2025, 12, 10, 14, 45, tzinfo=UTC),  # EST after Nov
    datetime(2026, 1, 28, 14, 45, tzinfo=UTC),
    datetime(2026, 3, 11, 13, 45, tzinfo=UTC),
    datetime(2026, 4, 15, 13, 45, tzinfo=UTC),
    datetime(2026, 6, 3, 13, 45, tzinfo=UTC),
]


def _first_friday(year: int, month: int) -> date:
    """Return the date of the first Friday of (year, month)."""
    d = date(year, month, 1)
    # Friday is weekday 4 (Mon=0).
    while d.weekday() != 4:
        d += timedelta(days=1)
    return d


def _is_us_dst(d: date) -> bool:
    """Crude US DST check: 2nd Sun Mar -> 1st Sun Nov."""
    if d.month < 3 or d.month > 11:
        return False
    if 4 <= d.month <= 10:
        return True
    if d.month == 3:
        # 2nd Sunday of March
        first_sun = 1 + ((6 - date(d.year, 3, 1).weekday()) % 7)
        second_sun = first_sun + 7
        return d.day >= second_sun
    if d.month == 11:
        # First Sunday of November
        first_sun = 1 + ((6 - date(d.year, 11, 1).weekday()) % 7)
        return d.day < first_sun
    return False


def _us_release_time_utc(d: date, hour_et: int = 8, minute_et: int = 30) -> datetime:
    """8:30 ET → 12:30 UTC (EDT) or 13:30 UTC (EST)."""
    offset = 4 if _is_us_dst(d) else 5
    return datetime(d.year, d.month, d.day, hour_et + offset, minute_et, tzinfo=UTC)


def _generate_recurring_us_events() -> list[tuple[datetime, str, str, str]]:
    """NFP first Friday + CPI mid-month + Retail Sales mid-month."""
    out: list[tuple[datetime, str, str, str]] = []
    months = [
        (2025, 7),
        (2025, 8),
        (2025, 9),
        (2025, 10),
        (2025, 11),
        (2025, 12),
        (2026, 1),
        (2026, 2),
        (2026, 3),
        (2026, 4),
        (2026, 5),
        (2026, 6),
    ]
    for y, m in months:
        # NFP — first Friday at 8:30 ET.
        nfp_date = _first_friday(y, m)
        out.append((_us_release_time_utc(nfp_date), "USD", "Non-Farm Payrolls", "high"))

        # US CPI — typically 10th-15th of month, exact day varies. Assume 12th.
        # Use 13th if 12th is weekend.
        cpi_d = date(y, m, 12)
        while cpi_d.weekday() >= 5:
            cpi_d += timedelta(days=1)
        out.append((_us_release_time_utc(cpi_d), "USD", "CPI", "high"))

        # Retail sales — typically mid-month, ~15th. Use 16th if 15th is weekend.
        rs_d = date(y, m, 15)
        while rs_d.weekday() >= 5:
            rs_d += timedelta(days=1)
        out.append((_us_release_time_utc(rs_d), "USD", "Retail Sales", "medium"))
    return out


def _generate_eurozone_cpi() -> list[tuple[datetime, str, str, str]]:
    """EZ CPI flash — typically last business day of month at 09:00 UTC."""
    out: list[tuple[datetime, str, str, str]] = []
    months = [
        (2025, 8),
        (2025, 9),
        (2025, 10),
        (2025, 11),
        (2025, 12),
        (2026, 1),
        (2026, 2),
        (2026, 3),
        (2026, 4),
        (2026, 5),
        (2026, 6),
    ]
    for y, m in months:
        # Approx: last weekday of the month.
        d = date(y, m, 28)
        while d.weekday() >= 5 or (d + timedelta(days=1)).month == m and d.weekday() < 4:
            d += timedelta(days=1)
            if d.month != m:
                d -= timedelta(days=1)
                while d.weekday() >= 5:
                    d -= timedelta(days=1)
                break
        ts = datetime(d.year, d.month, d.day, 9, 0, tzinfo=UTC)
        out.append((ts, "EUR", "EZ CPI Flash", "medium"))
    return out


def _generate_uk_cpi() -> list[tuple[datetime, str, str, str]]:
    """UK CPI — typically mid-month at 06:00-07:00 UTC."""
    out: list[tuple[datetime, str, str, str]] = []
    months = [
        (2025, 8),
        (2025, 9),
        (2025, 10),
        (2025, 11),
        (2025, 12),
        (2026, 1),
        (2026, 2),
        (2026, 3),
        (2026, 4),
        (2026, 5),
        (2026, 6),
    ]
    for y, m in months:
        d = date(y, m, 17)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        out.append((datetime(d.year, d.month, d.day, 6, 0, tzinfo=UTC), "GBP", "UK CPI", "high"))
    return out


def main() -> None:
    rows: list[tuple[datetime, str, str, str]] = []
    for d in FOMC_DATES_UTC:
        rows.append((d, "USD", "FOMC Rate Decision", "high"))
    for d in ECB_DATES_UTC:
        rows.append((d, "EUR", "ECB Rate Decision", "high"))
    for d in BOJ_DATES_UTC:
        rows.append((d, "JPY", "BOJ Rate Decision", "high"))
    for d in BOE_DATES_UTC:
        rows.append((d, "GBP", "BOE Rate Decision", "high"))
    for d in RBA_DATES_UTC:
        rows.append((d, "AUD", "RBA Rate Decision", "high"))
    for d in BOC_DATES_UTC:
        rows.append((d, "CAD", "BOC Rate Decision", "high"))
    rows.extend(_generate_recurring_us_events())
    rows.extend(_generate_eurozone_cpi())
    rows.extend(_generate_uk_cpi())
    rows.sort(key=lambda r: r[0])

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        fh.write("timestamp_utc,currency,event_name,importance\n")
        for ts, cur, name, imp in rows:
            ts_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
            # Quote event name if it contains commas.
            name_safe = f'"{name}"' if "," in name else name
            fh.write(f"{ts_str},{cur},{name_safe},{imp}\n")
    print(f"Wrote {len(rows)} events to {OUT_PATH}")  # noqa: PRINT


if __name__ == "__main__":
    main()
