"""Family 2, free branch — does a day's rate repricing *lead* the FX move?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The programme has tested the policy rate **level** (the carry differential, and
it was a short-yen trade in disguise). It has never tested the **repricing** —
what changed in what the market expects. The two-year Treasury yield is the
cheapest honest proxy for that: it is almost entirely expectations of the policy
path over the next two years, it is published daily by FRED for free, and it
runs back to 1976.

Lead, not level, and not the same day
--------------------------------------

A same-day association between a yield move and an FX move is not a finding: the
two reprice together on the same news, and a rule that needs today's yield close
to trade today's FX is not a rule. The test is therefore about the **lead** —
the position opens after the US session has closed and the yield change is
public, and is held for one day.

The same-day association is computed anyway and reported as a **diagnostic**. It
uses information from inside its own holding period and is labelled as such
everywhere; no verdict reads it. It exists because a lead null with a strong
same-day association means something quite specific — that the information is
real and already in the price — and that is worth saying.

What the free branch cannot do
-------------------------------

This is not the hypothesis that matters most. That one is *intraday* repricing of
the expected policy path around a release, which needs short-rate futures at
exact timestamps across both panels. No free source carries it, and the plan
forbids buying a fragment of it, so the results document prices the whole thing
instead.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import ssl
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any, Final

import certifi
import numpy as np
import pandas as pd

from scripts.research.expectation import (
    MIN_DAYS_PER_DECIDING_PANEL,
    RATES_HORIZON_BARS,
    RATES_SIGN,
    test_engine,
)
from scripts.research.round_a import DECIDING_PANELS, PANELS

_CONTEXT: Final[ssl.SSLContext] = ssl.create_default_context(cafile=certifi.where())
_HEADERS: Final[dict[str, str]] = {"User-Agent": "fx-ai-trading-research/1.0"}

FRED_URL: Final[str] = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"
SERIES: Final[str] = "DGS2"

#: The H.15 release that carries this yield posts around 16:15
#: America/New_York, so a position opened at 22:00 UTC cannot be using a number
#: it did not have: that is 18:00 New York under daylight time and 17:00 under
#: standard time. An earlier comment here said "after the 17:00 close under
#: both rules", which is wrong by an hour under standard time -- it is *at* the
#: close, and still comfortably after the print.
#:
#: This is a deviation from the plan, which said "the first M15 bar of day
#: t+1". It is disclosed in the results rather than absorbed: it costs about a
#: fifth of the days, because a Friday 22:00 UTC has no bar inside the entry
#: tolerance, and it lands entry in the rollover window where the round trip is
#: 4.5 pips against 2.1 intraday.
DECISION_HOUR_UTC: Final[int] = 22


def acquire(series: str = SERIES) -> tuple[pd.Series, dict[str, Any]]:
    """One anonymous GET. No key, no account, no payment."""
    url = FRED_URL.format(series=series)
    last: Exception | None = None
    for attempt in range(1, 5):
        try:
            request = urllib.request.Request(url, headers=_HEADERS)  # noqa: S310 - fixed https
            with urllib.request.urlopen(request, timeout=300, context=_CONTEXT) as response:  # noqa: S310
                payload = response.read()
                break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last = exc
            if attempt == 4:
                raise RuntimeError(f"could not acquire {url}: {last}") from exc
            time.sleep(3.0 * attempt)
    rows = list(csv.reader(io.StringIO(payload.decode("utf-8", "replace"))))
    values = {
        row[0]: float(row[1])
        for row in rows[1:]
        if len(row) > 1 and row[1].strip() not in ("", ".")
    }
    frame = pd.Series(values, name=series).sort_index()
    return frame, {
        "provider": "Federal Reserve Bank of St. Louis, FRED",
        "url": url,
        "series": series,
        "field": "2-year Treasury constant maturity, per cent, daily",
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "observations": int(len(frame)),
        "span": [str(frame.index[0]), str(frame.index[-1])],
        "revision": "not revised; a published constant-maturity yield is final",
        "licence": "public domain, no key, no account, no payment",
        "acquired_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
    }


def build_events(yields: pd.Series, *, same_day: bool) -> list[dict[str, Any]]:
    """One event per day with a usable yield change.

    For the **lead** test the decision moment is `day t` at `DECISION_HOUR_UTC`,
    after the change is public, and the position is held forward from there.

    For the **same-day diagnostic** the moment is the start of `day t`, which is
    before the change it trades on exists. That is the point: it measures the
    contemporaneous association and is never read as evidence.
    """
    change = yields.diff()
    events: list[dict[str, Any]] = []
    dropped_zero = 0
    for day, value in change.items():
        if not np.isfinite(value):
            continue
        if value == 0.0:
            #: no repricing, so no position. Disclosed because the
            #: pre-registered day floor was set against the unfiltered
            #: population and this filter is part of why the floor is missed.
            dropped_zero += 1
            continue
        date = dt.date.fromisoformat(day)
        moment = dt.datetime(
            date.year,
            date.month,
            date.day,
            0 if same_day else DECISION_HOUR_UTC,
            tzinfo=dt.UTC,
        )
        events.append(
            {
                "release_date": day,
                "release_timestamp_utc": moment.isoformat(),
                "families": ("rates",),
                "composite_z": float(RATES_SIGN * value),
            }
        )
    if events:
        events[0]["days_dropped_for_zero_change"] = dropped_zero
    return events


def run(*, write: Callable[[str, Any], None], read: Callable[[str], Any]) -> None:
    """The free rates branch: acquire, check power, then run only what can decide."""
    from scripts.research.round_a import panels as panel_module

    del read
    yields, provenance = acquire()
    print(
        f"  {provenance['series']}: {provenance['observations']} observations "
        f"{provenance['span'][0]}..{provenance['span'][1]} sha={provenance['sha256'][:12]}"
    )

    cells: dict[str, dict[str, Any]] = {}
    power: dict[str, dict[str, Any]] = {}
    corrected: dict[str, dict[str, float]] = {}
    for panel_id in PANELS:
        frames = panel_module.load_panel(panel_id)
        cells[panel_id] = {}
        power[panel_id] = {}
        for name, same_day in (("lead", False), ("same_day_diagnostic", True)):
            events = build_events(yields, same_day=same_day)
            table = test_engine.event_returns(frames, events, horizon_bars=RATES_HORIZON_BARS)
            gate = test_engine.minimum_detectable_effect(table)
            power[panel_id][name] = gate
            enough = gate.get("events", 0) >= MIN_DAYS_PER_DECIDING_PANEL
            if not gate.get("runnable") or not enough:
                cells[panel_id][name] = {
                    "events": gate.get("events", 0),
                    "skipped": {
                        **gate,
                        "enough_days": enough,
                        "required_days": MIN_DAYS_PER_DECIDING_PANEL,
                    },
                }
                print(
                    f"  {panel_id} {name:20s} SKIPPED n={gate.get('events')} {gate.get('reason')}"
                )
                continue
            cell = test_engine.evaluate(table)
            cells[panel_id][name] = cell
            print(
                f"  {panel_id} {name:20s} n={cell['events']:4d} "
                f"gross={cell['gross_mean_pips']:+7.3f} net={cell['net_mean_pips']:+7.3f} "
                f"mde={cell['mde_80pct_power_pips']:5.2f} p={cell['permutation_p']:.3f}"
            )
        corrected[panel_id] = test_engine.family_max_p(cells[panel_id])
        for cell in cells[panel_id].values():
            cell.pop("null_statistics", None)

    decision = test_engine.verdict(
        cells,
        DECIDING_PANELS,
        primary=("lead",),
        corrected=corrected,
        min_events=MIN_DAYS_PER_DECIDING_PANEL,
        supported_status="RATE_REPRICING_LEADS_FX_SUPPORTED",
        not_supported_status="RATE_REPRICING_LEAD_NOT_SUPPORTED",
    )
    decision["note_same_day"] = (
        "The same-day cell trades on a yield change that is not complete until "
        "after its own holding period ends. It is a diagnostic and no verdict "
        "reads it."
    )
    print(f"  {decision['status']}  reasons={decision['drop_reasons']}")
    write(
        "s3_rates",
        {"provenance": provenance, "power": power, "cells": cells, "family_max_p": corrected},
    )
    write("s3_rates_verdict", decision)


__all__ = ["DECISION_HOUR_UTC", "FRED_URL", "SERIES", "acquire", "build_events", "run"]
