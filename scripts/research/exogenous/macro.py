"""Stage B — real-time macro data: what was actually known, and when.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

A revised historical series is not what a position could have reacted to. US CPI
for a given month is revised by later seasonal-factor updates, so the number in
today's database is not the number that printed. This module keeps four
quantities apart, as the plan requires:

* **first-release actual** — the value for month *m* in the earliest ALFRED
  vintage in which *m* appears;
* **prior value known at release time** — the value for *m−1* in the vintage
  immediately preceding that one;
* **pre-release expectation** — the Cleveland Fed nowcast on the last business
  day strictly before the release;
* **latest revised value** — today's, kept only to measure how far the revision
  went, never used in a signal.

The expectation is a model nowcast, not a consensus
----------------------------------------------------

No free source carries a survey consensus history; every candidate is paid or
licence-restricted. The Cleveland Fed publishes a daily inflation nowcast and
archives the whole daily path per target month, keyless. It is used, and it is
labelled `MODEL_NOWCAST_SURPRISE_NOT_SURVEY_SURPRISE` everywhere it appears: a
null measured against it does **not** refute a consensus-surprise hypothesis.

The archive's CPI path stops on the release date rather than running to the end
of the window, which is what a real-time record looks like and what a re-run
would not. That is evidence, not proof; the residual risk that the published
archive was recomputed with revised inputs cannot be settled from the file and
is disclosed rather than assumed away.

Publication time
----------------

The BLS releases CPI at 08:30 America/New_York, a time fixed by rule and
published a year ahead. It is converted with the real daylight rule per date —
12:30 UTC under EDT and 13:30 under EST. A fixed offset would put half the
sample's entry bar 60 minutes early, which is a leak on exactly the bars that
matter.
"""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import io
import json
import re
import ssl
import time
import urllib.error
import urllib.request
from typing import Any, Final
from zoneinfo import ZoneInfo

import certifi

from scripts.research.exogenous import (
    BLS_RELEASE_LOCAL_TIME,
    BLS_RELEASE_TIMEZONE,
    SURPRISE_SCALE_RELEASES,
)

_CONTEXT: Final[ssl.SSLContext] = ssl.create_default_context(cafile=certifi.where())
_HEADERS: Final[dict[str, str]] = {"User-Agent": "fx-ai-trading-research/1.0"}

ALFRED_VINTAGE_LIST: Final[str] = "https://alfred.stlouisfed.org/series/downloaddata?seid={series}"
ALFRED_VINTAGE_CSV: Final[str] = (
    "https://alfred.stlouisfed.org/graph/alfredgraph.csv?id={series}&vintage_date={vintage}"
)
CLEVELAND_NOWCAST: Final[str] = (
    "https://www.clevelandfed.org/-/media/files/webcharts/inflationnowcasting/nowcast_month.json"
)

#: The two indicators the nowcast archive and ALFRED both cover. They print in
#: the same release, so they are two signals on one event set — not two event
#: sets, and the multiplicity accounting in the plan treats them that way.
INDICATORS: Final[dict[str, dict[str, str]]] = {
    "cpi": {"series": "CPIAUCSL", "nowcast": "CPI Inflation", "label": "US CPI, month over month"},
    "core_cpi": {
        "series": "CPILFESL",
        "nowcast": "Core CPI Inflation",
        "label": "US core CPI, month over month",
    },
}


def _get(url: str, *, attempts: int = 4) -> tuple[bytes, dict[str, Any]]:
    """One GET with provenance, retried.

    A single vintage in a ninety-request walk returned 404 once and served
    normally on every later attempt. Letting that abort the walk would make the
    real-time table depend on which minute it was built in; letting it silently
    skip the vintage would move a first release to the next one. So it is
    retried, and a persistent failure raises.
    """
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers=_HEADERS)  # noqa: S310 - fixed https
            with urllib.request.urlopen(request, timeout=300, context=_CONTEXT) as response:  # noqa: S310
                payload = response.read()
                lowered = {key.lower(): value for key, value in response.headers.items()}
                return payload, {
                    "url": url,
                    "status": int(response.status),
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "content_type": lowered.get("content-type"),
                    "last_modified": lowered.get("last-modified"),
                    "attempts": attempt,
                    "acquired_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                }
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last = exc
            if attempt < attempts:
                time.sleep(3.0 * attempt)
    raise RuntimeError(f"could not acquire {url}: {last}")


def release_timestamp_utc(release_date: str) -> dt.datetime:
    """08:30 America/New_York on that date, in UTC, with the real daylight rule."""
    hour, minute = (int(part) for part in BLS_RELEASE_LOCAL_TIME.split(":"))
    local = dt.datetime.combine(
        dt.date.fromisoformat(release_date),
        dt.time(hour, minute),
        tzinfo=ZoneInfo(BLS_RELEASE_TIMEZONE),
    )
    return local.astimezone(dt.UTC)


def alfred_vintages(series: str) -> tuple[list[str], dict[str, Any]]:
    """Every vintage date ALFRED holds for a series, from its download form."""
    payload, provenance = _get(ALFRED_VINTAGE_LIST.format(series=series))
    text = payload.decode("utf-8", "replace")
    dates = sorted(set(re.findall(r'value="(\d{4}-\d{2}-\d{2})"', text)))
    provenance["vintages"] = len(dates)
    provenance["series"] = series
    return dates, provenance


def alfred_vintage(series: str, vintage: str) -> dict[str, float]:
    """One vintage of a series: observation date -> value, as it stood that day."""
    payload, _ = _get(ALFRED_VINTAGE_CSV.format(series=series, vintage=vintage))
    reader = csv.reader(io.StringIO(payload.decode("utf-8", "replace")))
    rows = list(reader)
    out: dict[str, float] = {}
    for row in rows[1:]:
        if len(row) < 2 or not row[1].strip() or row[1].strip() == ".":
            continue
        out[row[0].strip()] = float(row[1])
    return out


def first_release_table(
    series: str, *, first_release_from: str, first_release_to: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """For each observation month, what printed and when — never a revision.

    Walks the vintages in order and records a month the first time it appears.
    The vintage that introduced it is the release; the vintage before it holds
    the value for *m−1* that was known when *m* printed.
    """
    vintages, provenance = alfred_vintages(series)
    inside = [v for v in vintages if first_release_from <= v <= first_release_to]
    if not inside:
        return [], provenance
    #: one vintage before the window, so the first release inside it has a
    #: predecessor to read the prior-known value from
    start_index = max(0, vintages.index(inside[0]) - 1)
    walk = vintages[start_index : vintages.index(inside[-1]) + 1]

    seen: set[str] = set()
    previous: dict[str, float] = {}
    rows: list[dict[str, Any]] = []
    for order, vintage in enumerate(walk):
        current = alfred_vintage(series, vintage)
        fresh = sorted(set(current) - seen)
        seen.update(current)
        if order == 0:
            previous = current
            continue
        for observation in fresh:
            month = dt.date.fromisoformat(observation)
            prior_month = (month.replace(day=1) - dt.timedelta(days=1)).replace(day=1)
            prior_known = previous.get(prior_month.isoformat())
            level = current[observation]
            rows.append(
                {
                    "observation_month": observation,
                    "release_vintage": vintage,
                    "first_release_level": level,
                    "prior_known_level": prior_known,
                    "first_release_mom_pct": (
                        None if not prior_known else round(100.0 * (level / prior_known - 1.0), 6)
                    ),
                }
            )
        previous = current
    provenance["vintages_walked"] = len(walk)
    provenance["releases_recorded"] = len(rows)
    return rows, provenance


_DAY_LABEL = re.compile(r"^(\d{1,2})/(\d{1,2})$")


def _label_to_date(label: str, target_year: int, target_month: int) -> dt.date | None:
    """A "07/12" label inside target month 2023-6 is 2023-07-12; December wraps.

    Some charts carry non-date labels on the same axis. Those return `None` and
    their column is skipped — rather than crashing the parse or, worse, shifting
    every later column by one position.
    """
    match = _DAY_LABEL.match(label.strip())
    if match is None:
        return None
    month, day = int(match.group(1)), int(match.group(2))
    year = target_year + 1 if month < target_month else target_year
    try:
        return dt.date(year, month, day)
    except ValueError:
        return None


def cleveland_nowcast() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """The archived daily nowcast path, per target month.

    Returns, per target month `YYYY-MM`: the nowcast on each business day for
    each indicator, and the date on which the archive placed the actual — which
    is the release date, and is cross-checked against ALFRED's vintage date
    rather than trusted.
    """
    payload, provenance = _get(CLEVELAND_NOWCAST)
    charts = json.loads(payload)
    out: dict[str, dict[str, Any]] = {}
    for chart in charts:
        subcaption = chart["chart"]["subcaption"]
        year, month = (int(part) for part in subcaption.split("-"))
        labels = [entry.get("label", "") for entry in chart["categories"][0]["category"]]
        #: The axis interleaves marker labels — "CPI May", "PCE Jun" — between the
        #: business days, so there are more categories than data points and the
        #: datasets are aligned to the **date labels only**. Indexing the raw
        #: category list instead put every release two or three business days
        #: early: the archive's actual for target 2023-06 landed on 07-10 where
        #: the release was 07-12, and ALFRED agreed with the archive on 0 of 84
        #: releases. Dropping the markers first is what makes them agree.
        dates = [
            value.isoformat()
            for value in (_label_to_date(label, year, month) for label in labels)
            if value is not None
        ]
        series: dict[str, dict[str, float]] = {}
        actual_dates: dict[str, str] = {}
        for dataset in chart["dataset"]:
            name = dataset["seriesname"]
            values = [point.get("value") for point in dataset["data"]]
            paired = {
                dates[index]: float(value)
                for index, value in enumerate(values)
                if value not in (None, "") and index < len(dates)
            }
            if name.startswith("Actual "):
                if paired:
                    actual_dates[name.removeprefix("Actual ")] = max(paired)
                series[name] = paired
            else:
                series[name] = paired
        out[f"{year:04d}-{month:02d}"] = {
            "series": series,
            "actual_dates": actual_dates,
            "days": dates,
        }
    provenance["target_months"] = len(out)
    return out, provenance


def build_releases(
    *, first_release_from: str, first_release_to: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One row per CPI release: what printed, what was expected, and when.

    The release date is taken from **ALFRED's vintage**, not from the nowcast
    archive. The archive's own actual date is recorded beside it and the two are
    compared, so a disagreement is visible rather than silently resolved in
    favour of whichever source was read first.
    """
    nowcast, nowcast_provenance = cleveland_nowcast()
    provenance: dict[str, Any] = {"nowcast": nowcast_provenance, "alfred": {}}
    per_indicator: dict[str, dict[str, dict[str, Any]]] = {}

    for key, spec in INDICATORS.items():
        rows, alfred_provenance = first_release_table(
            spec["series"],
            first_release_from=first_release_from,
            first_release_to=first_release_to,
        )
        provenance["alfred"][key] = alfred_provenance
        per_indicator[key] = {row["observation_month"]: row for row in rows}

    months = sorted(set().union(*(set(rows) for rows in per_indicator.values())))
    releases: list[dict[str, Any]] = []
    for month in months:
        target = month[:7]
        archive = nowcast.get(target)
        row: dict[str, Any] = {"observation_month": month, "target_month": target}
        release_dates = {
            key: per_indicator[key][month]["release_vintage"]
            for key in per_indicator
            if month in per_indicator[key]
        }
        if len(set(release_dates.values())) != 1:
            row["release_date_disagreement"] = release_dates
            continue
        release_date = next(iter(release_dates.values()))
        row["release_date"] = release_date
        row["release_timestamp_utc"] = release_timestamp_utc(release_date).isoformat()
        row["archive_actual_date"] = (
            archive["actual_dates"].get("CPI Inflation") if archive else None
        )
        row["archive_agrees_with_alfred"] = row["archive_actual_date"] == release_date

        for key, spec in INDICATORS.items():
            source = per_indicator[key].get(month)
            if source is None:
                row[key] = None
                continue
            path = (archive or {}).get("series", {}).get(spec["nowcast"], {})
            before = {day: value for day, value in path.items() if day < release_date}
            expectation = before[max(before)] if before else None
            actual = source["first_release_mom_pct"]
            row[key] = {
                "first_release_mom_pct": actual,
                "prior_known_level": source["prior_known_level"],
                "nowcast_mom_pct": expectation,
                "nowcast_as_of": max(before) if before else None,
                "surprise_pct": (
                    None if actual is None or expectation is None else actual - expectation
                ),
            }
        releases.append(row)
    return releases, provenance


def scale_surprises(releases: list[dict[str, Any]], indicator: str) -> list[dict[str, Any]]:
    """Attach a standardised surprise using **only** the releases before each one.

    The scale is the standard deviation of the preceding
    `SURPRISE_SCALE_RELEASES` surprises. A full-sample standard deviation would
    put information from the future into every early event, which is a mutation
    the tests kill.
    """
    history: list[float] = []
    out: list[dict[str, Any]] = []
    for release in releases:
        cell = release.get(indicator)
        raw = None if cell is None else cell.get("surprise_pct")
        scale = None
        if len(history) >= 4:
            window = history[-SURPRISE_SCALE_RELEASES:]
            mean = sum(window) / len(window)
            variance = sum((value - mean) ** 2 for value in window) / (len(window) - 1)
            scale = variance**0.5 or None
        standardised = None if raw is None or not scale else raw / scale
        out.append(
            {
                **release,
                "indicator": indicator,
                "surprise_pct": raw,
                "surprise_scale": scale,
                "surprise_z": standardised,
                "prior_surprises_used": len(history[-SURPRISE_SCALE_RELEASES:]),
            }
        )
        if raw is not None:
            history.append(raw)
    return out


__all__ = [
    "ALFRED_VINTAGE_CSV",
    "ALFRED_VINTAGE_LIST",
    "CLEVELAND_NOWCAST",
    "INDICATORS",
    "alfred_vintage",
    "alfred_vintages",
    "build_releases",
    "cleveland_nowcast",
    "first_release_table",
    "release_timestamp_utc",
    "scale_surprises",
]
