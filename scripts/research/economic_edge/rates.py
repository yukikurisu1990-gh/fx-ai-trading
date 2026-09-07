"""Stage 1 — central-bank policy rates, acquired with their provenance.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

This is the first external data this programme has ever acquired. It is a
**macro** series, not market data: no FX price outside the three already-seen
panels is read here or anywhere in this package.

Why the policy rate, and not something better
---------------------------------------------

The plan's hierarchy (§5) ranks sources by economic fidelity to what a position
actually earns, and it was fixed **before** anything was fetched so that the
ranking could not be rationalised backwards from whatever turned out to be easy:

1. **broker financing actuals** — what a retail position genuinely earns, and
   what no public archive contains. It is the implementation gap, recorded and
   referred, never claimed;
2. **swap / forward points** — the market price of carry, and the closest
   tradable proxy. No public, reproducible, eight-currency history was found
   without a paid contract;
3. **short-term money-market rates** — economically close to forward points, but
   the eight currencies would have to be assembled from different series with
   different definitions and mixed daily/monthly frequency, and a
   cross-sectional ranking across inconsistent definitions is not a ranking;
4. **policy rates** — coarsest, stepping discretely and lagging the market, and
   the only one available for all eight currencies from **one source with one
   definition at one frequency**.

The horizons this package trades are weekly to monthly, which is the range where
the policy rate's coarseness costs least. Its limitations are recorded rather
than argued away, and §5.1's fallback cross-check against money-market rates is
what tests whether the coarseness matters.

Vintage
-------

A policy rate is **announced and effective**; it is not revised the way a macro
statistic is, which is why the plan ranks it above macro data. It is still used
with a one-trading-day lag (`RATE_LAG_TRADING_DAYS`), so a decision can never be
taken on the bar that announced the change.
"""

from __future__ import annotations

import hashlib
import io
import json
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import pandas as pd

from scripts.research.economic_edge import CURRENCIES, RATE_LAG_TRADING_DAYS
from scripts.research.exploratory_m15 import bars as bars_module

#: BIS "Central bank policy rates", the public bulk flat file. No key, no
#: account, no metered call: one anonymous HTTPS GET of a static artefact.
BIS_CBPOL_URL: Final[str] = "https://data.bis.org/static/bulk/WS_CBPOL_csv_flat.zip"
BIS_LANDING: Final[str] = "https://data.bis.org/topics/CBPOL"

#: BIS reference areas. `XM` is the euro area, which is the right object for EUR
#: -- the ECB sets one rate for the bloc, so there is no country to choose.
AREA_FOR_CURRENCY: Final[dict[str, str]] = {
    "AUD": "AU",
    "CAD": "CA",
    "CHF": "CH",
    "EUR": "XM",
    "GBP": "GB",
    "JPY": "JP",
    "NZD": "NZ",
    "USD": "US",
}

CACHE_DIR: Final[Path] = bars_module.REPO_ROOT / "artifacts" / "track_a_scratch" / "economic_edge"
RATES_PARQUET: Final[Path] = CACHE_DIR / "policy_rates_daily.parquet"
PROVENANCE_JSON: Final[Path] = CACHE_DIR / "policy_rates_provenance.json"

#: the columns the flat file exposes, by their position-independent prefix
_FREQ = "FREQ:Frequency"
_AREA = "REF_AREA:Reference area"
_TIME = "TIME_PERIOD:Time period or range"
_VALUE = "OBS_VALUE:Observation Value"
_UNIT = "UNIT_MEASURE:Unit of measure"
_COMPILATION = "COMPILATION:Compilation"


class RateAcquisitionError(RuntimeError):
    """Raised when the source cannot be turned into a usable eight-currency panel."""


def _download(url: str = BIS_CBPOL_URL) -> tuple[bytes, dict[str, Any]]:
    """One anonymous GET, with everything needed to identify what came back."""
    request = urllib.request.Request(url, headers={"User-Agent": "fx-ai-trading-research/1.0"})
    fetched_at = datetime.now(UTC).isoformat()
    with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310 - fixed https URL
        payload = response.read()
        headers = dict(response.headers)
    return payload, {
        "url": url,
        "landing_page": BIS_LANDING,
        "fetched_at_utc": fetched_at,
        "bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "last_modified": headers.get("Last-Modified"),
        "content_type": headers.get("Content-Type"),
        "requires_key": False,
        "requires_account": False,
        "metered": False,
    }


def _parse(payload: bytes) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Stream the flat file and keep only daily rows for the eight areas.

    The uncompressed file is about 470 MB and almost all of it is other
    countries and other frequencies, so it is filtered line by line rather than
    read into a frame.
    """
    wanted = {AREA_FOR_CURRENCY[c]: c for c in CURRENCIES}
    archive = zipfile.ZipFile(io.BytesIO(payload))
    member = archive.infolist()[0]

    rows: list[tuple[str, str, float]] = []
    definitions: dict[str, str] = {}
    units: set[str] = set()
    seen_lines = 0
    with archive.open(member.filename) as handle:
        header = handle.readline().decode("utf-8").rstrip("\r\n").split(",")
        index = {name: position for position, name in enumerate(header)}
        for column in (_FREQ, _AREA, _TIME, _VALUE, _UNIT, _COMPILATION):
            if column not in index:
                raise RateAcquisitionError(f"the source no longer carries {column!r}")
        reader = pd.read_csv(
            handle,
            header=None,
            names=header,
            usecols=[
                index[_FREQ],
                index[_AREA],
                index[_TIME],
                index[_VALUE],
                index[_UNIT],
                index[_COMPILATION],
            ],
            dtype=str,
            chunksize=200_000,
            engine="c",
            on_bad_lines="skip",
        )
        for chunk in reader:
            seen_lines += len(chunk)
            daily = chunk[chunk[_FREQ].str.startswith("D", na=False)]
            if daily.empty:
                continue
            code = daily[_AREA].str.split(":", n=1).str[0]
            keep = daily[code.isin(wanted)]
            if keep.empty:
                continue
            codes = keep[_AREA].str.split(":", n=1).str[0]
            for area, stamp, value, unit, compilation in zip(
                codes, keep[_TIME], keep[_VALUE], keep[_UNIT], keep[_COMPILATION], strict=True
            ):
                if not isinstance(value, str) or not value.strip():
                    continue
                try:
                    rows.append((wanted[area], stamp, float(value)))
                except ValueError:
                    continue
                units.add(unit)
                definitions.setdefault(
                    wanted[area], compilation if isinstance(compilation, str) else ""
                )

    if not rows:
        raise RateAcquisitionError("no daily observations for any of the eight currencies")

    frame = pd.DataFrame(rows, columns=["currency", "date", "rate_pct"])
    frame["date"] = pd.to_datetime(frame["date"], format="%Y-%m-%d", utc=True)
    frame = frame.drop_duplicates(subset=["currency", "date"]).sort_values(["currency", "date"])

    missing = sorted(set(CURRENCIES) - set(frame["currency"].unique()))
    if missing:
        raise RateAcquisitionError(f"the source does not cover {missing}; it cannot serve PAIRS_20")

    return frame.reset_index(drop=True), {
        "member": member.filename,
        "uncompressed_bytes": member.file_size,
        "source_rows_scanned": seen_lines,
        "daily_rows_kept": len(frame),
        "units": sorted(units),
        "rate_definition_per_currency": definitions,
    }


def acquire(*, force: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Fetch once, cache, and record everything the plan §4 asks for."""
    if RATES_PARQUET.is_file() and PROVENANCE_JSON.is_file() and not force:
        return pd.read_parquet(RATES_PARQUET), json.loads(
            PROVENANCE_JSON.read_text(encoding="utf-8")
        )

    payload, download = _download()
    frame, parsed = _parse(payload)

    coverage = {
        currency: {
            "first": str(group["date"].min().date()),
            "last": str(group["date"].max().date()),
            "observations": int(len(group)),
            "distinct_rates": int(group["rate_pct"].nunique()),
            "min_pct": round(float(group["rate_pct"].min()), 4),
            "max_pct": round(float(group["rate_pct"].max()), 4),
        }
        for currency, group in frame.groupby("currency")
    }

    provenance = {
        "source": "BIS — Central bank policy rates (WS_CBPOL)",
        "download": download,
        "parse": parsed,
        "field": "OBS_VALUE, the policy rate",
        "frequency": "daily, as published (a step function between decisions)",
        "date_semantics": (
            "TIME_PERIOD is the date the rate is EFFECTIVE, not a publication "
            "date. A policy rate is announced and effective; it is not a "
            "statistic that gets revised. It is nonetheless used with a "
            f"{RATE_LAG_TRADING_DAYS}-trading-day lag so no decision can be "
            "taken on the bar that announced the change"
        ),
        "timezone": (
            "the source carries a plain date with no time. It is treated as a "
            "UTC calendar date and joined to the M15 grid's UTC date, which is "
            "the same convention every panel in this repository uses"
        ),
        "revision_behaviour": (
            "policy rates are not revised. The bulk file is regenerated, so a "
            "later download can extend the series or correct a historical "
            "typo; the sha256 above identifies the exact bytes this analysis "
            "used"
        ),
        "licensing": (
            "BIS publishes this dataset publicly for non-commercial use with "
            "attribution. No key, no account, no metered call, no payment"
        ),
        "currency_mapping": AREA_FOR_CURRENCY,
        "coverage": coverage,
        "limitations": [
            "a policy rate is the coarsest of the four candidate carry sources: "
            "it steps discretely and lags the money market",
            "it is not what a broker pays. Research carry and broker-realizable "
            "carry are separate objects and this is the former",
            "the euro area is one rate for a bloc, so EUR carries no national dispersion",
        ],
    }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(RATES_PARQUET, index=False)
    PROVENANCE_JSON.write_text(json.dumps(provenance, indent=2, sort_keys=True), encoding="utf-8")
    return frame, provenance


def _fred_daily(series: str, index: pd.DatetimeIndex) -> tuple[pd.Series, str]:
    """One FRED series, forward-filled onto a dense calendar, with its digest."""
    url = FRED_CSV.format(series=series)
    request = urllib.request.Request(url, headers={"User-Agent": "fx-ai-trading-research/1.0"})
    with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 - fixed https
        payload = response.read()
    frame = pd.read_csv(io.BytesIO(payload))
    frame.columns = ["date", "value"]
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    dense = frame.dropna().set_index("date")["value"]
    return dense.reindex(dense.index.union(index)).sort_index().ffill().reindex(index), (
        hashlib.sha256(payload).hexdigest()
    )


def daily_panel(frame: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """A dense calendar-daily rate for every currency, lagged as the plan requires.

    The source is a step function with an observation only where something
    changed or the publisher emitted one, so it is forward-filled onto a dense
    calendar. **The forward fill runs before the lag**, so the lag is a lag in
    days and not in observations — filling after shifting would move a rate by
    one *published observation*, which can be months.
    """
    index = pd.date_range(start=start, end=end, freq="D", tz="UTC")
    wide = (
        frame.pivot(index="date", columns="currency", values="rate_pct")
        .reindex(index.union(frame["date"].unique()))
        .sort_index()
        .ffill()
        .reindex(index)
    )
    #: amendment A-1: EUR comes from the ECB deposit facility, not from BIS's
    #: mid-sample-broken euro-area series
    for currency, series in POLICY_RATE_OVERRIDE.items():
        replacement, _digest = _fred_daily(series, index)
        wide[currency] = replacement

    missing = [c for c in CURRENCIES if c not in wide.columns or wide[c].isna().all()]
    if missing:
        raise RateAcquisitionError(f"no rate available for {missing} over {start}..{end}")
    lagged = wide[list(CURRENCIES)].shift(RATE_LAG_TRADING_DAYS)
    lagged.index.name = "date"
    return lagged


def differential(panel: pd.DataFrame, pair: str) -> pd.Series:
    """`rate(BASE) − rate(QUOTE)`, per cent per year, for one `PAIRS_20` pair.

    Long one unit of `BASE_QUOTE` earns this; short earns its negative.
    """
    base, quote = pair.split("_")
    if base not in panel.columns or quote not in panel.columns:
        raise RateAcquisitionError(f"{pair} needs {base} and {quote}, which the panel lacks")
    return panel[base] - panel[quote]


#: Plan §5.1's fallback: overnight money-market rates, to measure how much the
#: policy rate's coarseness actually costs. FRED serves these as plain CSV with
#: no key. Only the three currencies with a genuinely daily public series are
#: checked -- a cross-check assembled from monthly series for the rest would
#: measure the frequency mismatch rather than the rate gap.
FRED_CSV: Final[str] = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}"

#: **Amendment A-1**, made before any carry economics was computed, on fidelity
#: grounds rather than on a result.
#:
#: BIS's euro-area series is not one definition. Its own `COMPILATION` field
#: says: *"From 18 Sep 2024 onwards: official central bank steering rate is the
#: deposit facility rate; from 15 Oct 2008 to 17 Sep 2024: official central bank
#: steering rate"* — the main refinancing rate. Measured, the BIS series is
#: **exactly** the MRO before that date (gap to the deposit facility `+0.500`)
#: and **exactly** the deposit facility after (`+0.001`). That is a definition
#: break inside the sample, in a currency that appears in 6 of the 20 pairs.
#:
#: It also measures the wrong thing. Under excess liquidity €STR anchors to the
#: **deposit facility**, not the MRO, which is why the ECB redesignated it in
#: 2024. Against €STR over the panel span: BIS as-is gives a mean gap of
#: `−0.4477` (sd 0.227); the deposit facility gives `−0.0842` (sd 0.042),
#: putting EUR in line with USD (`−0.041`) and GBP (`−0.052`).
#:
#: So EUR uses the ECB deposit facility rate throughout. It is still a policy
#: rate, set by the same central bank at the same frequency — the correction
#: picks the right one of the ECB's three, it does not change the kind of
#: object.
POLICY_RATE_OVERRIDE: Final[dict[str, str]] = {"EUR": "ECBDFR"}
OVERNIGHT_SERIES: Final[dict[str, str]] = {
    "USD": "DFF",
    "EUR": "ECBESTRVOLWGTTRMDMNRT",
    "GBP": "IUDSOIA",
}


def fallback_crosscheck(panel: pd.DataFrame, *, start: str, end: str) -> dict[str, Any]:
    """How far the policy rate sits from the overnight rate it stands in for.

    The plan ranks money-market rates **above** policy rates on fidelity and
    below them on availability, and this is the measurement that says whether
    that trade-off cost anything. A small, stable gap means the coarser series
    is an adequate stand-in at weekly-to-monthly horizons; a large or drifting
    one would mean the carry signal is measuring the wrong thing.
    """
    out: dict[str, Any] = {"series": OVERNIGHT_SERIES, "source": "FRED, public CSV, no key"}
    for currency, series in OVERNIGHT_SERIES.items():
        url = FRED_CSV.format(series=series)
        request = urllib.request.Request(url, headers={"User-Agent": "fx-ai-trading-research/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response:  # noqa: S310 - fixed https
            payload = response.read()
        frame = pd.read_csv(io.BytesIO(payload))
        frame.columns = ["date", "value"]
        frame["date"] = pd.to_datetime(frame["date"], utc=True)
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        overnight = (
            frame.dropna()
            .set_index("date")["value"]
            .reindex(pd.date_range(start=start, end=end, freq="D", tz="UTC"))
            .ffill()
        )
        policy = panel[currency].reindex(overnight.index)
        gap = (overnight - policy).dropna()
        if gap.empty:
            out[currency] = {"decidable": False}
            continue
        out[currency] = {
            "observations": int(len(gap)),
            "mean_gap_pct": round(float(gap.mean()), 4),
            "median_gap_pct": round(float(gap.median()), 4),
            "max_abs_gap_pct": round(float(gap.abs().max()), 4),
            "sd_gap_pct": round(float(gap.std()), 4),
            "correlation": round(float(overnight.corr(policy)), 5),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    return out


__all__ = [
    "AREA_FOR_CURRENCY",
    "BIS_CBPOL_URL",
    "CACHE_DIR",
    "PROVENANCE_JSON",
    "RATES_PARQUET",
    "RateAcquisitionError",
    "OVERNIGHT_SERIES",
    "POLICY_RATE_OVERRIDE",
    "acquire",
    "fallback_crosscheck",
    "daily_panel",
    "differential",
]
