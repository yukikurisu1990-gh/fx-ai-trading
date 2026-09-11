"""Stage 0 — can the non-USD calendar data decide anything?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

No signal and no return is computed anywhere in this module. It answers one
question, with a rule frozen before it ran: **is the release date right?**

Why the date and not the time
------------------------------

The archive's timestamps are wrong — an earlier stage measured them sixteen to
seventeen hours early against known US release times. A one-day study needs only
the date, so the audit asks whether the date survives the defect, and the
pre-registration forbids promoting a date-only source to an intraday one.

Why the correction is estimated on a different currency from the one it is judged on
-------------------------------------------------------------------------------------

One constant offset is allowed. It is chosen on **USD** rows, against ALFRED's
vintage dates for CPI — which for that series *are* the release dates — and then
applied unchanged to the **non-USD** rows the verdict rests on. Fitting the
offset on the rows it will be validated against would make the 95% threshold a
measurement of the search rather than of the data.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import ssl
import urllib.request
from typing import Any, Final

import certifi
import numpy as np
import pandas as pd

from scripts.research.exogenous import calendars
from scripts.research.exogenous import macro as alfred
from scripts.research.track2 import (
    ARCHIVE_ROWS,
    ARCHIVE_SHA256_PREFIX,
    ARCHIVE_URL,
    G10,
    KNOWN_NON_UNIVERSE_CODES,
    MAX_FORECAST_EXACT_MATCH_SHARE,
    MIN_DATE_AGREEMENT,
    NON_USD,
    OFFSET_GRID_HOURS,
    OFFSET_TRAINING_EVENT,
    OFFSET_TRAINING_SERIES,
    PANEL_SPANS,
    POLICY_EVENTS,
    STATUS_SKIP,
)

_CONTEXT: Final[ssl.SSLContext] = ssl.create_default_context(cafile=certifi.where())
_HEADERS: Final[dict[str, str]] = {"User-Agent": "fx-ai-trading-research/1.0"}

#: Currencies whose official announcement calendar `exogenous.calendars` can
#: acquire. The other four banks refuse every automated route, which is recorded
#: there as a coverage limitation rather than filled in by hand.
OFFICIAL_NON_USD: Final[tuple[str, ...]] = ("EUR", "JPY", "AUD")


def acquire_archive(cache: Any = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Download the archive and fingerprint it. **P1.**"""
    if cache is not None and cache.is_file():
        raw = cache.read_bytes()
        source = "cache"
    else:
        request = urllib.request.Request(ARCHIVE_URL, headers=_HEADERS)
        with urllib.request.urlopen(request, timeout=300, context=_CONTEXT) as response:
            raw = response.read()
        source = ARCHIVE_URL
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    frame = pd.read_csv(
        io.BytesIO(raw),
        usecols=["DateTime", "Currency", "Impact", "Event", "Actual", "Forecast", "Previous"],
    )
    frame["utc"] = pd.to_datetime(frame["DateTime"], format="ISO8601", utc=True)
    provenance = {
        "source": source,
        "sha256_prefix": digest[:16],
        "sha256_matches_expected": digest.startswith(ARCHIVE_SHA256_PREFIX),
        "n_rows": int(len(frame)),
        "n_rows_matches_expected": int(len(frame)) == ARCHIVE_ROWS,
        "bytes": int(len(raw)),
    }
    return frame, provenance


def in_panels(frame: pd.DataFrame) -> pd.DataFrame:
    """Rows inside either deciding panel's span, by the archive's own stamp.

    Deliberately generous: the span filter is applied *before* any offset, so a
    row the correction would move across a boundary is still present to be
    counted rather than silently gone.
    """
    lo = min(start for start, _ in PANEL_SPANS.values())
    hi = max(end for _, end in PANEL_SPANS.values())
    inside = (frame["utc"] >= pd.Timestamp(lo, tz="UTC")) & (
        frame["utc"] <= pd.Timestamp(hi, tz="UTC") + pd.Timedelta(days=1)
    )
    return frame[inside].copy()


def currency_mapping(frame: pd.DataFrame) -> dict[str, Any]:
    """**P2.** Every code recognised, and how many rows each currency carries."""
    codes = sorted(frame["Currency"].dropna().astype(str).unique())
    unknown = [code for code in codes if code not in G10 and code not in KNOWN_NON_UNIVERSE_CODES]
    counts = frame["Currency"].value_counts()
    return {
        "codes_seen": codes,
        "unrecognised_codes": unknown,
        "all_codes_recognised": not unknown,
        "rows_per_currency": {"_unit": "count", **{c: int(counts.get(c, 0)) for c in G10}},
        "n_non_usd_rows": int(sum(int(counts.get(c, 0)) for c in NON_USD)),
    }


def _event_row_dates(
    frame: pd.DataFrame, currency: str, event: str, offset_hours: int
) -> list[str]:
    """One date **per row**, duplicates kept: a duplicated row is a defect too."""
    rows = frame[(frame["Currency"] == currency) & (frame["Event"] == event)]
    shifted = rows["utc"] + pd.Timedelta(hours=offset_hours)
    return [stamp.date().isoformat() for stamp in shifted]


def _event_dates(frame: pd.DataFrame, currency: str, event: str, offset_hours: int) -> list[str]:
    return sorted(set(_event_row_dates(frame, currency, event, offset_hours)))


def _agreement(
    archive_dates: list[str], official_dates: list[str], row_dates: list[str] | None = None
) -> dict[str, Any]:
    """Both directions, because one of them alone is not an agreement rate.

    **Recall** is the share of official announcement dates the archive carries.
    **Precision** is the share of the archive's own rows that land on an official
    date — the pre-registration's "share of the checkable rows", and the one that
    decides whether a study built on these rows would trade on real event days.

    A first version reported recall only. Recall can be perfect while the archive
    also carries dates that are not events at all, and a design would then place
    trades on days nothing happened. Both are reported and the **lower** governs.

    Scored over the official dates inside the archive's own range, so a bank whose
    calendar extends past the archive is not counted as a miss.
    """
    if not archive_dates:
        return {"n_official": 0, "n_matched": 0, "agreement": None}
    lo, hi = min(archive_dates), max(archive_dates)
    official = [d for d in official_dates if lo <= d <= hi]
    official_set = set(official)
    matched = sum(1 for d in official if d in set(archive_dates))
    rows = row_dates if row_dates is not None else archive_dates
    rows_in_range = [d for d in rows if lo <= d <= hi]
    on_official = sum(1 for d in rows_in_range if d in official_set)
    offsets: list[int] = []
    archive_ordinals = sorted(dt.date.fromisoformat(d).toordinal() for d in archive_dates)
    for d in official:
        target = dt.date.fromisoformat(d).toordinal()
        nearest = min(archive_ordinals, key=lambda value: abs(value - target))
        offsets.append(nearest - target)
    histogram: dict[str, int] = {}
    for value in offsets:
        histogram[str(value)] = histogram.get(str(value), 0) + 1
    recall = matched / len(official) if official else None
    precision = on_official / len(rows_in_range) if rows_in_range else None
    both = [value for value in (recall, precision) if value is not None]
    return {
        "n_official": len(official),
        "n_archive_dates": len(archive_dates),
        "n_archive_rows": len(rows_in_range),
        "n_matched": matched,
        "n_rows_on_an_official_date": on_official,
        "recall": round(recall, 4) if recall is not None else None,
        "precision": round(precision, 4) if precision is not None else None,
        #: The lower of the two. A source that finds every event but also invents
        #: some has not agreed with the official calendar.
        "agreement": round(min(both), 4) if both else None,
        "days_from_official": {
            "_unit": "count",
            **dict(sorted(histogram.items(), key=lambda kv: int(kv[0]))),
        },
    }


def estimate_offset(frame: pd.DataFrame) -> dict[str, Any]:
    """**The one correction.** Estimated on USD CPI against ALFRED vintages.

    The whole grid's profile is reported, not just the argmax: a correction whose
    best hour is barely better than its neighbours is not a correction, and a
    reader has to be able to see that.
    """
    vintages, provenance = alfred.alfred_vintages(OFFSET_TRAINING_SERIES)
    lo = min(start for start, _ in PANEL_SPANS.values())
    hi = max(end for _, end in PANEL_SPANS.values())
    official = sorted(d for d in vintages if lo <= d <= hi)
    profile: dict[str, Any] = {}
    best_hours, best_agreement = 0, -1.0
    for hours in OFFSET_GRID_HOURS:
        dates = _event_dates(frame, "USD", OFFSET_TRAINING_EVENT, hours)
        score = _agreement(
            dates, official, _event_row_dates(frame, "USD", OFFSET_TRAINING_EVENT, hours)
        )
        profile[str(hours)] = score["agreement"]
        if score["agreement"] is not None and score["agreement"] > best_agreement:
            best_hours, best_agreement = hours, score["agreement"]
    runner_up = sorted(
        (value for key, value in profile.items() if value is not None and key != str(best_hours)),
        reverse=True,
    )
    return {
        "training_series": OFFSET_TRAINING_SERIES,
        "training_event": OFFSET_TRAINING_EVENT,
        "training_currency": "USD",
        "n_official_vintages": len(official),
        "alfred_provenance": provenance,
        "agreement_by_offset_hours": {"_unit": "count", **profile},
        "best_offset_hours": best_hours,
        "best_agreement": round(best_agreement, 4),
        "runner_up_agreement": round(runner_up[0], 4) if runner_up else None,
        "separated_from_runner_up": bool(runner_up and best_agreement - runner_up[0] >= 0.10),
    }


def date_fidelity(frame: pd.DataFrame, offset_hours: int) -> dict[str, Any]:
    """**P3 and P4.** The non-USD dates against the official announcement dates."""
    calendar = calendars.acquire()
    official = calendar["dates"]
    per_currency: dict[str, Any] = {}
    total_official = total_matched = total_rows = total_on_official = 0
    for currency in OFFICIAL_NON_USD:
        event = POLICY_EVENTS[currency]
        raw = _agreement(
            _event_dates(frame, currency, event, 0),
            official[currency],
            _event_row_dates(frame, currency, event, 0),
        )
        corrected = _agreement(
            _event_dates(frame, currency, event, offset_hours),
            official[currency],
            _event_row_dates(frame, currency, event, offset_hours),
        )
        per_currency[currency] = {"event": event, "as_is": raw, "corrected": corrected}
        if corrected["n_official"]:
            total_official += corrected["n_official"]
            total_matched += corrected["n_matched"]
            total_rows += corrected["n_archive_rows"]
            total_on_official += corrected["n_rows_on_an_official_date"]
    recall = total_matched / total_official if total_official else None
    precision = total_on_official / total_rows if total_rows else None
    both = [value for value in (recall, precision) if value is not None]
    pooled = round(min(both), 4) if both else None
    return {
        "offset_hours_applied": offset_hours,
        "pooled_recall": round(recall, 4) if recall is not None else None,
        "pooled_precision": round(precision, 4) if precision is not None else None,
        "n_archive_rows_total": total_rows,
        "n_rows_on_an_official_date_total": total_on_official,
        "per_currency": per_currency,
        "n_official_total": total_official,
        "n_matched_total": total_matched,
        "pooled_agreement": pooled,
        "calendar_provenance": {c: calendar["provenance"][c] for c in OFFICIAL_NON_USD},
        "banks_without_an_acquirable_calendar": calendar["unacquirable"],
    }


def _numeric(series: pd.Series) -> np.ndarray:
    cleaned = (
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("K", "e3", regex=False)
        .str.replace("M", "e6", regex=False)
        .str.replace("B", "e9", regex=False)
        .str.replace("T", "e12", regex=False)
    )
    return pd.to_numeric(cleaned, errors="coerce").to_numpy(dtype=float)


def forecast_audit(frame: pd.DataFrame) -> dict[str, Any]:
    """**P5.** Two falsifications, on the non-USD rows that carry all three values.

    That a forecast was recorded *before* the print cannot be proven — no
    arrangement of numbers distinguishes a survey from a number written down
    afterwards. It can be falsified: by matching the actual too often, or by
    adding nothing over the naive "same as last time" benchmark.
    """
    rows = frame[frame["Currency"].isin(NON_USD)]
    actual_all, forecast_all, previous_all = (
        _numeric(rows["Actual"]),
        _numeric(rows["Forecast"]),
        _numeric(rows["Previous"]),
    )
    usable = np.isfinite(actual_all) & np.isfinite(forecast_all) & np.isfinite(previous_all)
    if not usable.any():
        return {"n_usable": 0}
    exact = float(np.mean(forecast_all[usable] == actual_all[usable]))

    #: Per series, never pooled. These rows carry percentages, index points and
    #: counts in the millions in the same column, so a pooled mean absolute error
    #: is a weighted average of incommensurable units — a first version reported
    #: one of about four billion, which is a unit artifact and not a measurement.
    labels = (rows["Currency"].astype(str) + " | " + rows["Event"].astype(str)).to_numpy()
    better = worse = 0
    ratios: list[float] = []
    for label in sorted(set(labels[usable])):
        pick = usable & (labels == label)
        if int(pick.sum()) < 12:
            continue
        actual, forecast, previous = actual_all[pick], forecast_all[pick], previous_all[pick]
        forecast_error = float(np.mean(np.abs(actual - forecast)))
        naive_error = float(np.mean(np.abs(actual - previous)))
        if naive_error <= 0:
            continue
        ratios.append(forecast_error / naive_error)
        better += int(forecast_error < naive_error)
        worse += int(forecast_error >= naive_error)
    total = better + worse
    return {
        "n_usable": int(usable.sum()),
        "n_non_usd_rows": int(len(rows)),
        "n_series_compared": total,
        "exact_match_share": round(exact, 4),
        "exact_match_below_ceiling": bool(exact < MAX_FORECAST_EXACT_MATCH_SHARE),
        "share_of_series_beating_the_naive_benchmark": round(better / total, 4) if total else None,
        "median_forecast_error_over_naive_error": round(float(np.median(ratios)), 4)
        if ratios
        else None,
        #: The falsification is at the *family* level: a majority of series must
        #: carry information the previous print did not.
        "beats_the_naive_benchmark": bool(total and better / total > 0.5),
    }


def revision_consistency(frame: pd.DataFrame) -> dict[str, Any]:
    """**P6.** No vintages exist for non-USD, so measure what does exist.

    Within one event series, the `Previous` of a row should be the `Actual` of
    the row before it. Where it is not, either the archive back-filled a revision
    or the series is not what its name says. This is weaker than a vintage check
    and is reported as such.
    """
    rows = frame[frame["Currency"].isin(NON_USD)].sort_values("utc")
    agree = total = 0
    for (_currency, _event), group in rows.groupby(["Currency", "Event"], sort=False):
        actual = _numeric(group["Actual"])
        previous = _numeric(group["Previous"])
        for index in range(1, len(group)):
            if np.isfinite(actual[index - 1]) and np.isfinite(previous[index]):
                total += 1
                agree += int(np.isclose(actual[index - 1], previous[index], rtol=0, atol=1e-9))
    return {
        "n_comparable_pairs": total,
        "n_previous_equals_prior_actual": agree,
        "share": round(agree / total, 4) if total else None,
        "limitation": (
            "no vintage archive exists for these agencies, so a first-release check "
            "of the kind ALFRED supports for US series cannot be performed here"
        ),
    }


def verdict(record: dict[str, Any]) -> dict[str, Any]:
    """The pre-registered acceptance rule, applied without a repair clause."""
    fidelity = record["date_fidelity"]["pooled_agreement"]
    checks = {
        "date_agreement_at_least_95_percent": bool(
            fidelity is not None and fidelity >= MIN_DATE_AGREEMENT
        ),
        "all_currency_codes_recognised": bool(record["currency_mapping"]["all_codes_recognised"]),
        "forecast_not_falsified": bool(
            record["forecast_audit"].get("exact_match_below_ceiling")
            and record["forecast_audit"].get("beats_the_naive_benchmark")
        ),
    }
    passed = all(checks.values())
    return {
        "checks": checks,
        "min_date_agreement_required": MIN_DATE_AGREEMENT,
        "pass": passed,
        "status": None if passed else STATUS_SKIP,
        "no_repair_clause": (
            "the pre-registration allows exactly one declared correction, a single "
            "constant offset estimated on USD rows. Nothing here is hand-repaired, "
            "back-filled or corrected per currency to reach the threshold."
        ),
    }


def build(cache: Any = None) -> dict[str, Any]:
    """The whole audit. Reads no FX bar and computes no return."""
    frame, provenance = acquire_archive(cache)
    panel_rows = in_panels(frame)
    offset = estimate_offset(panel_rows)
    record: dict[str, Any] = {
        "classification": [
            "NON_DECISION_BEARING_EXPLORATORY_ONLY",
            "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
        ],
        "signal_free": True,
        "provenance": provenance,
        "n_rows_in_panel_spans": int(len(panel_rows)),
        "currency_mapping": currency_mapping(panel_rows),
        "offset_estimation": offset,
        "date_fidelity": date_fidelity(panel_rows, offset["best_offset_hours"]),
        "forecast_audit": forecast_audit(panel_rows),
        "revision_consistency": revision_consistency(panel_rows),
    }
    record["verdict"] = verdict(record)
    return record


__all__ = [
    "OFFICIAL_NON_USD",
    "acquire_archive",
    "build",
    "currency_mapping",
    "date_fidelity",
    "estimate_offset",
    "forecast_audit",
    "in_panels",
    "revision_consistency",
    "verdict",
]
