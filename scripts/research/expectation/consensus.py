"""Family 1 data — the survey consensus the programme has never held.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Every direction test in this programme so far has compared a realisation with
either a price or a *model* proxy of the expectation. This module builds the
missing half: what a survey of forecasters expected, as it stood before the
print.

The archive supplies values; it does not supply time
-----------------------------------------------------

The free archive passed the test that mattered — its `Actual` is the number as
first published, not a later revision, verified against ALFRED on 75 releases —
and failed the one about clocks. Against known US CPI release times it is **16
to 17 hours early**, a scraper timezone defect that is systematic without being
a constant, and large enough to move an event onto the wrong UTC date. It cannot
be corrected from the archive alone: the correction needs the ground truth that
would make it unnecessary.

So the join is deliberately lopsided. **ALFRED's vintage date plus the agency's
documented 08:30 America/New_York rule gives every timestamp**; the archive
gives `Actual`, `Forecast` and `Previous` and nothing else. The two are matched
on the release *day* with a one-day tolerance, and the number of rows that
matched, failed to match or matched ambiguously is reported rather than
absorbed.

What can and cannot be proven about a forecast
-----------------------------------------------

That an actual is a first release can be *proven*, and was. That a forecast was
recorded before the print cannot be — no arrangement of values can distinguish a
genuine pre-release survey from one written down afterwards. It can only be
falsified, by a forecast that is too close to the actual, or that adds nothing
over the naive prior value. `audit_forecasts` measures both, and the result is
reported as evidence rather than as proof wherever it appears.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import ssl
import time
import urllib.error
import urllib.request
from typing import Any, Final

import certifi
import numpy as np
import pandas as pd

from scripts.research.exogenous import macro as alfred
from scripts.research.expectation import (
    ARCHIVE_ROWS,
    ARCHIVE_SHA256_PREFIX,
    ARCHIVE_URL,
    RELEASE_FAMILIES,
    RELEASE_LOCAL_TIME,
    RELEASE_TIMEZONE,
    SIGNAL_SIGNS,
    SURPRISE_SCALE_RELEASES,
)

_CONTEXT: Final[ssl.SSLContext] = ssl.create_default_context(cafile=certifi.where())
_HEADERS: Final[dict[str, str]] = {"User-Agent": "fx-ai-trading-research/1.0"}

#: The archive dates a release the evening before it happened, so a match is
#: looked for on the release day and the day before it. Anything wider would
#: start pairing a release with its neighbour.
JOIN_TOLERANCE_DAYS: Final[int] = 1

#: The eight currencies `PAIRS_20` spans, for the non-USD survey in §7.
G10: Final[tuple[str, ...]] = ("USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD")


def _get(url: str, *, attempts: int = 4) -> tuple[bytes, dict[str, Any]]:
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers=_HEADERS)  # noqa: S310 - fixed https
            with urllib.request.urlopen(request, timeout=600, context=_CONTEXT) as response:  # noqa: S310
                payload = response.read()
                return payload, {
                    "url": url,
                    "status": int(response.status),
                    "bytes": len(payload),
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "attempts": attempt,
                    "acquired_utc": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
                }
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last = exc
            if attempt < attempts:
                time.sleep(3.0 * attempt)
    raise RuntimeError(f"could not acquire {url}: {last}")


def to_number(series: pd.Series) -> pd.Series:
    """Archive values are strings: `0.4%`, `-11K`, `1.2M`. Parse, never guess.

    A value that does not parse becomes `NaN` and drops out of the join, which
    is visible in the match counts, rather than being coerced to zero.
    """
    text = (
        series.astype(str)
        .str.strip()
        .str.replace("%", "", regex=False)
        .str.replace(",", "", regex=False)
        .str.replace("<", "", regex=False)
        .str.replace(">", "", regex=False)
    )
    scaled = (
        text.str.replace("K", "e3", regex=False)
        .str.replace("M", "e6", regex=False)
        .str.replace("B", "e9", regex=False)
        .str.replace("T", "e12", regex=False)
    )
    return pd.to_numeric(scaled, errors="coerce")


def acquire_archive() -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fetch the public calendar archive and record what arrived."""
    payload, provenance = _get(ARCHIVE_URL)
    frame = pd.read_csv(io.BytesIO(payload))
    frame["ts"] = pd.to_datetime(frame["DateTime"], utc=True, errors="coerce", format="mixed")
    provenance.update(
        {
            "rows": int(len(frame)),
            "rows_match_frozen_count": int(len(frame)) == ARCHIVE_ROWS,
            "digest_matches_frozen_prefix": provenance["sha256"].startswith(ARCHIVE_SHA256_PREFIX),
            "parsed_timestamps": int(frame["ts"].notna().sum()),
            "span": [str(frame["ts"].min()), str(frame["ts"].max())],
            "licence": "MIT, public, not gated; no account, key or payment",
            "fields": list(frame.columns),
            "timestamp_status": (
                "NOT USED. Measured 16-17 hours early against 75 known US CPI "
                "release times; every timestamp downstream comes from ALFRED."
            ),
        }
    )
    #: recorded AND enforced. A first version measured both flags and printed
    #: them, so a substituted or updated archive would have been used silently
    #: while the document claimed the digest had been checked.
    if not provenance["digest_matches_frozen_prefix"]:
        raise RuntimeError(
            f"archive digest {provenance['sha256'][:16]} does not match the frozen "
            f"{ARCHIVE_SHA256_PREFIX}: the pre-registration describes a different file"
        )
    if not provenance["rows_match_frozen_count"]:
        raise RuntimeError(
            f"archive has {provenance['rows']} rows against the frozen {ARCHIVE_ROWS}"
        )
    return frame, provenance


def release_time_rule() -> dict[str, Any]:
    """Assert the conversion in use is still the one this package froze.

    Timestamps come from `exogenous.macro.release_timestamp_utc`, which reads
    that package's constants. This package freezes its own pair for the record.
    If the two ever diverged every release time would move silently, so the
    equality is checked rather than assumed.
    """
    from scripts.research.exogenous import BLS_RELEASE_LOCAL_TIME, BLS_RELEASE_TIMEZONE

    if (BLS_RELEASE_LOCAL_TIME, BLS_RELEASE_TIMEZONE) != (
        RELEASE_LOCAL_TIME,
        RELEASE_TIMEZONE,
    ):
        raise RuntimeError(
            f"the conversion in use is {BLS_RELEASE_LOCAL_TIME} {BLS_RELEASE_TIMEZONE}, "
            f"but this package froze {RELEASE_LOCAL_TIME} {RELEASE_TIMEZONE}"
        )
    return {"local_time": RELEASE_LOCAL_TIME, "timezone": RELEASE_TIMEZONE}


def audit_actuals(archive: pd.DataFrame, alfred_releases: list[dict[str, Any]]) -> dict[str, Any]:
    """Is the archive's `Actual` the first release, or a later revision?

    This one *is* provable, and it is the failure mode that would make the whole
    source worthless. Each archive `CPI m/m` row is matched to the nearest known
    release within 40 hours and compared with the ALFRED first-release
    month-over-month, at the 0.1pp the archive publishes.
    """
    truth = [
        (pd.Timestamp(row["release_timestamp_utc"]), row["cpi"]["first_release_mom_pct"])
        for row in alfred_releases
        if row.get("cpi") and row["cpi"].get("first_release_mom_pct") is not None
    ]
    rows = archive[
        (archive["Currency"] == "USD") & (archive["Event"] == "CPI m/m") & archive["Actual"].notna()
    ]
    values = to_number(rows["Actual"])
    matched, agree, errors = 0, 0, []
    for stamp, value in zip(rows["ts"], values, strict=True):
        if not np.isfinite(value):
            continue
        near = [
            (abs((stamp - true_ts).total_seconds() / 3600.0), true_ts, mom)
            for true_ts, mom in truth
            if abs((stamp - true_ts).total_seconds() / 3600.0) < 40.0
        ]
        if not near:
            continue
        gap, true_ts, mom = min(near)
        matched += 1
        errors.append(round((stamp - true_ts).total_seconds() / 3600.0, 1))
        if abs(value - mom) < 0.051:
            agree += 1
    return {
        "archive_rows": int(len(rows)),
        "matched_to_known_release": matched,
        "agree_with_alfred_first_release": agree,
        "agreement_rate": round(agree / matched, 4) if matched else None,
        "timestamp_error_hours": dict(
            sorted(pd.Series(errors).value_counts().items(), key=lambda item: -item[1])
        ),
        "verdict": (
            "ACTUAL_IS_FIRST_RELEASE_NOT_A_REVISION"
            if matched and agree / matched > 0.95
            else "ACTUAL_INTEGRITY_NOT_ESTABLISHED"
        ),
    }


def audit_forecasts(archive: pd.DataFrame, *, currency: str = "USD") -> dict[str, Any]:
    """Does the forecast column behave like a real pre-release survey?

    Not provable, falsifiable. Two ways a written-after-the-fact column shows
    itself: it tracks the actual too closely, or — the mirror failure — it adds
    nothing over the previous value, which is what a lazily backfilled column
    would look like. Both are measured; neither fired.
    """
    out: dict[str, Any] = {}
    for family in RELEASE_FAMILIES.values():
        for event in family["events"]:  # type: ignore[index]
            block = archive[(archive["Currency"] == currency) & (archive["Event"] == event)]
            actual = to_number(block["Actual"])
            forecast = to_number(block["Forecast"])
            prior = to_number(block["Previous"])
            keep = actual.notna() & forecast.notna()
            if int(keep.sum()) < 20:
                out[event] = {"n": int(keep.sum()), "note": "too few rows to characterise"}
                continue
            difference = (actual - forecast)[keep]
            naive = (actual - prior)[keep & prior.notna()]
            out[event] = {
                "n": int(keep.sum()),
                "exact_equal_share": round(float((difference.abs() < 1e-9).mean()), 4),
                "correlation": round(float(np.corrcoef(actual[keep], forecast[keep])[0, 1]), 4),
                "sd_actual_minus_forecast": round(float(difference.std()), 6),
                "sd_actual_minus_prior": round(float(naive.std()), 6) if len(naive) > 2 else None,
                "ratio_to_naive_benchmark": (
                    round(float(difference.std() / naive.std()), 4)
                    if len(naive) > 2 and float(naive.std())
                    else None
                ),
            }
    ratios = [
        cell["ratio_to_naive_benchmark"]
        for cell in out.values()
        if cell.get("ratio_to_naive_benchmark") is not None
    ]
    exacts = [cell["exact_equal_share"] for cell in out.values() if "exact_equal_share" in cell]
    #: A contaminated column would beat the naive benchmark completely (ratio
    #: near zero) or reproduce the actual outright (exact share near one).
    consistent = bool(ratios) and min(ratios) > 0.10 and max(exacts) < 0.60
    return {
        "per_event": out,
        "verdict": (
            "FORECAST_BEHAVIOURALLY_CONSISTENT_WITH_A_SURVEY_EVIDENCE_NOT_PROOF"
            if consistent
            else "FORECAST_BEHAVIOUR_INCONSISTENT_WITH_A_PRE_RELEASE_SURVEY"
        ),
        "note": (
            "As-of-ness of a forecast cannot be proven from values. These "
            "statistics falsify the contaminated cases and nothing more."
        ),
    }


def release_dates(*, first_release_from: str, first_release_to: str) -> dict[str, Any]:
    """Authoritative release dates, one walk of ALFRED vintages per family."""
    out: dict[str, Any] = {}
    for name, family in RELEASE_FAMILIES.items():
        rows, provenance = alfred.first_release_table(
            str(family["series"]),
            first_release_from=first_release_from,
            first_release_to=first_release_to,
        )
        dates = sorted({row["release_vintage"] for row in rows})
        out[name] = {"series": family["series"], "dates": dates, "provenance": provenance}
    return out


def build_events(
    archive: pd.DataFrame, dates: dict[str, Any], *, currency: str = "USD"
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """One row per release-time: when it printed, and by how much it surprised.

    The timestamp is ALFRED's vintage date at 08:30 America/New_York, converted
    with the real daylight rule. The archive contributes only the three numbers,
    matched on the release day with a one-day tolerance because the archive
    dates a release the evening before.
    """
    usd = archive[(archive["Currency"] == currency) & archive["Actual"].notna()].copy()
    usd["date"] = usd["ts"].dt.date
    usd["actual"] = to_number(usd["Actual"])
    usd["forecast"] = to_number(usd["Forecast"])
    usd["prior"] = to_number(usd["Previous"])

    events: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {
        "matched": 0,
        "unmatched": 0,
        "ambiguous": 0,
        "same_day": 0,
        "day_before": 0,
    }
    #: per signal, because an aggregate count hides a signal that never matches
    #: at all. `Prelim GDP q/q` is exactly that: ALFRED dates only the vintage
    #: that first introduces a quarter, which is the advance estimate, so the
    #: second estimate has no release date to join to and contributes nothing.
    unmatched_by_event: dict[str, int] = {}
    matched_by_event: dict[str, int] = {}
    for family_name, family in RELEASE_FAMILIES.items():
        wanted = list(family["events"])  # type: ignore[arg-type]
        for value in dates[family_name]["dates"]:
            release_date = dt.date.fromisoformat(value)
            stamp = alfred.release_timestamp_utc(value)
            signals: dict[str, dict[str, float]] = {}
            for event in wanted:
                window = usd[
                    (usd["Event"] == event)
                    & (usd["date"] >= release_date - dt.timedelta(days=JOIN_TOLERANCE_DAYS))
                    & (usd["date"] <= release_date)
                ]
                if window.empty:
                    diagnostics["unmatched"] += 1
                    unmatched_by_event[event] = unmatched_by_event.get(event, 0) + 1
                    continue
                if len(window) > 1:
                    diagnostics["ambiguous"] += 1
                    unmatched_by_event[event] = unmatched_by_event.get(event, 0) + 1
                    continue
                row = window.iloc[0]
                if not np.isfinite(row["actual"]) or not np.isfinite(row["forecast"]):
                    diagnostics["unmatched"] += 1
                    unmatched_by_event[event] = unmatched_by_event.get(event, 0) + 1
                    continue
                diagnostics["matched"] += 1
                matched_by_event[event] = matched_by_event.get(event, 0) + 1
                diagnostics["same_day" if row["date"] == release_date else "day_before"] += 1
                signals[event] = {
                    "actual": float(row["actual"]),
                    "forecast": float(row["forecast"]),
                    "prior": float(row["prior"]) if np.isfinite(row["prior"]) else float("nan"),
                    "raw_surprise": float(row["actual"] - row["forecast"]),
                }
            if signals:
                events.append(
                    {
                        "release_date": value,
                        "release_timestamp_utc": stamp.isoformat(),
                        "family": family_name,
                        "signals": signals,
                    }
                )

    #: Amendment A-1, consequence 3: two families printing at the same 08:30 are
    #: **one** tradeable moment, not two. A version that left them as separate
    #: events would take two positions at a moment where only one is available
    #: and would double-count the same information in the null.
    merged: dict[str, dict[str, Any]] = {}
    for event in events:
        stamp = event["release_timestamp_utc"]
        cell = merged.setdefault(
            stamp,
            {
                "release_date": event["release_date"],
                "release_timestamp_utc": stamp,
                "families": [],
                "signals": {},
            },
        )
        cell["families"].append(event["family"])
        cell["signals"].update(event["signals"])
    events = sorted(merged.values(), key=lambda row: row["release_timestamp_utc"])
    for event in events:
        event["families"] = sorted(set(event["families"]))
    diagnostics["release_times"] = len(events)
    diagnostics["collisions_merged"] = sum(1 for event in events if len(event["families"]) > 1)
    diagnostics["matched_by_event"] = matched_by_event
    diagnostics["unmatched_by_event"] = unmatched_by_event
    diagnostics["signals_that_never_matched"] = sorted(
        name
        for family in RELEASE_FAMILIES.values()
        for name in family["events"]  # type: ignore[union-attr]
        if not matched_by_event.get(name)
    )
    diagnostics["match_rate"] = (
        round(diagnostics["matched"] / (diagnostics["matched"] + diagnostics["unmatched"]), 4)
        if diagnostics["matched"] + diagnostics["unmatched"]
        else None
    )
    return events, diagnostics


def attach_surprises(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Standardise each signal on its own past, then compose the release.

    The scale for a signal is the standard deviation of its **preceding**
    surprises only — at most `SURPRISE_SCALE_RELEASES` of them — so no event is
    scaled by information from after it. The composite is the mean of the
    standardised, sign-oriented signals present in that release, which is what
    makes one release-time carry one number regardless of how many series it
    contains.
    """
    history: dict[str, list[float]] = {}
    out: list[dict[str, Any]] = []
    for event in events:
        standardised: dict[str, float] = {}
        for name, cell in event["signals"].items():
            past = history.setdefault(name, [])
            scale = None
            if len(past) >= 4:
                window = past[-SURPRISE_SCALE_RELEASES:]
                scale = float(np.std(window, ddof=1)) or None
            if scale:
                standardised[name] = SIGNAL_SIGNS[name] * cell["raw_surprise"] / scale
            past.append(cell["raw_surprise"])
        composite = float(np.mean(list(standardised.values()))) if standardised else None
        out.append(
            {
                **event,
                "standardised": standardised,
                "composite_z": composite,
                "signals_used": len(standardised),
            }
        )
    return out


#: The four central banks whose scheduled meeting dates the previous package
#: acquired and validated against BIS rate changes with zero orphans. They are
#: the only ground truth available for testing whether the archive's dates can
#: be repaired outside the US.
CENTRAL_BANK_EVENTS: Final[dict[str, tuple[str, ...]]] = {
    "USD": ("Federal Funds Rate",),
    "EUR": ("Main Refinancing Rate", "Monetary Policy Statement"),
    "JPY": ("BOJ Policy Rate",),
    "AUD": ("Cash Rate",),
}


def non_usd_survey(
    archive: pd.DataFrame,
    calendar: dict[str, list[str]],
    *,
    panels: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    """What a paid provider would actually be selling, measured rather than argued.

    Two questions, and the second is the one that decides the purchase.

    **How much non-USD consensus is already free?** Every high-impact G10 row in
    the deciding panels carrying both an actual and a forecast, and the number
    of distinct release moments they form.

    **Can the archive's dates be repaired outside the US?** The previous package
    acquired scheduled central-bank meeting dates for four currencies and
    validated them against BIS rate changes with zero orphans. If a single
    offset repaired the archive, every central-bank row would land on a meeting
    date under one rule. Measuring both rules per event answers it.
    """
    rows = archive[archive["Impact"].astype(str).str.contains("High", na=False)].copy()
    rows["actual"] = to_number(rows["Actual"])
    rows["forecast"] = to_number(rows["Forecast"])
    usable = rows[rows["actual"].notna() & rows["forecast"].notna()]

    inside = pd.concat(
        [usable[(usable["ts"] >= low) & (usable["ts"] <= high)] for low, high in panels]
    )
    non_usd = inside[inside["Currency"].isin([c for c in G10 if c != "USD"])]
    by_currency = {
        str(key): int(value) for key, value in non_usd["Currency"].value_counts().items()
    }
    moments = len(non_usd.groupby([non_usd["Currency"], non_usd["ts"].dt.date]))

    offsets: dict[str, dict[str, Any]] = {}
    for currency, events in CENTRAL_BANK_EVENTS.items():
        meetings = {dt.date.fromisoformat(value) for value in calendar.get(currency, ())}
        for event in events:
            block = archive[
                (archive["Currency"] == currency)
                & (archive["Event"] == event)
                & (archive["ts"] >= "2021-01-01")
                & (archive["ts"] <= "2025-04-07")
            ]
            if block.empty:
                continue
            same = sum(1 for stamp in block["ts"] if stamp.date() in meetings)
            next_day = sum(
                1 for stamp in block["ts"] if (stamp.date() + dt.timedelta(days=1)) in meetings
            )
            offsets[f"{currency} - {event}"] = {
                "rows": int(len(block)),
                "archive_date_equals_meeting": same,
                "archive_date_plus_one_equals_meeting": next_day,
                "dominant_rule": "+0" if same > next_day else "+1",
            }
    dominant = {cell["dominant_rule"] for cell in offsets.values()}
    return {
        "non_usd_high_impact_rows_with_actual_and_forecast": int(len(non_usd)),
        "by_currency": by_currency,
        "distinct_currency_date_moments": moments,
        "central_bank_date_offsets": offsets,
        "a_single_offset_would_repair_the_archive": len(dominant) == 1,
        "verdict": (
            "FREE_CONSENSUS_EXISTS_FOR_EVERY_G10_CURRENCY_THE_RELEASE_TIMESTAMP_IS_WHAT_IS_MISSING"
            if len(dominant) > 1
            else "ARCHIVE_DATES_MAY_BE_REPAIRABLE_BY_A_SINGLE_OFFSET"
        ),
    }


__all__ = [
    "CENTRAL_BANK_EVENTS",
    "JOIN_TOLERANCE_DAYS",
    "acquire_archive",
    "attach_surprises",
    "audit_actuals",
    "audit_forecasts",
    "build_events",
    "non_usd_survey",
    "release_dates",
    "release_time_rule",
    "to_number",
]
