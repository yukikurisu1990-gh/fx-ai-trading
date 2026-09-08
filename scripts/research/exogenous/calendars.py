"""Stage 1 — the scheduled central-bank meeting calendar.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The Economic Edge package anchored on days a policy rate **changed**. Whether a
meeting changes a rate is not knowable in advance, so that population could
bound what an event anchor might offer without being one. This module builds the
population that *is* knowable in advance: the dates a central bank had a
**scheduled** monetary policy decision.

Four of eight banks, and the limit is access rather than choice
---------------------------------------------------------------

The Federal Reserve, the ECB, the Bank of Japan and the Reserve Bank of
Australia each publish a machine-readable index from which the decision dates
fall out of the document identifiers themselves — an FOMC statement lives at
`monetaryYYYYMMDDa.htm`, an ECB statement at `ecb.mpYYMMDD…`, a BoJ statement at
`kYYMMDDa.pdf`. Those identifiers are the primary record, not a rendering of it.

The Bank of England, the Bank of Canada, the Reserve Bank of New Zealand and the
Swiss National Bank return 403, 404 or 500 to every automated route tried —
index pages, RSS, sitemaps, year archives — or serve only future dates. **Their
meeting dates are not reconstructed by hand.** A date typed from memory into a
committed file is unverified scope inside an artifact, and this repository has
ruled against that before. GBP, CAD, NZD and CHF therefore carry no scheduled
anchor here, which is recorded as a coverage limitation in the results.

What "the date" means
---------------------

For every bank this is the **announcement date** — the day the decision was
published, which for a two-day meeting is the second day. The **time** of day is
not acquired for all four, so everything downstream is a day-level study
(plan §5). No intraday claim may be made from a source whose timestamp is a date.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import re
import ssl
import time
import urllib.error
import urllib.request
from typing import Any, Final

import certifi

#: Some of these hosts sit behind a TLS chain the platform store cannot complete;
#: certifi resolves it. The previous package fetched BIS and FRED without this
#: and would have failed on four of the hosts here.
_CONTEXT: Final[ssl.SSLContext] = ssl.create_default_context(cafile=certifi.where())

#: Two clients. The plain one is what this repository already uses; the browser
#: one exists because rba.gov.au rejects anything else, and it is used only where
#: the plain client is refused.
_PLAIN_HEADERS: Final[dict[str, str]] = {"User-Agent": "fx-ai-trading-research/1.0"}
_BROWSER_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "close",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

FOMC_URL: Final[str] = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
ECB_URL_TEMPLATE: Final[str] = (
    "https://www.ecb.europa.eu/press/press_conference/monetary-policy-statement/"
    "{year}/html/index_include.en.html"
)
BOJ_URL: Final[str] = "https://www.boj.or.jp/en/mopo/mpmsche_minu/past.htm"
RBA_URL_TEMPLATE: Final[str] = "https://www.rba.gov.au/media-releases/{year}/"

#: The published cadence of each bank, used as an integrity check rather than as
#: a source. A year whose extracted count differs is reported, not silently
#: accepted -- the RBA moved from eleven meetings a year to eight in 2024 and a
#: single hard-coded number would have hidden either the change or a parse bug.
#:
#: It is necessary and **not sufficient**: one extra unscheduled decision plus
#: one missed scheduled meeting would net to the right count. Plan §6 asks for
#: unscheduled decisions to be flagged and excluded, and this package does not
#: implement that flag -- no source it acquires carries one. What it has instead
#: is the BIS containment check in the driver, which explains every rate change
#: in the span from a scheduled meeting at a constant per-bank lag; an
#: unscheduled decision would appear there as an orphan, and none did.
EXPECTED_MEETINGS: Final[dict[str, dict[int, int]]] = {
    "USD": dict.fromkeys(range(2021, 2027), 8),
    "EUR": dict.fromkeys(range(2021, 2027), 8),
    "JPY": dict.fromkeys(range(2021, 2027), 8),
    "AUD": {2021: 11, 2022: 11, 2023: 11, 2024: 8, 2025: 8, 2026: 8},
}

#: The banks whose calendars could not be acquired, with the failure that ended
#: each attempt. Kept in the source so a later session does not repeat them.
UNACQUIRABLE: Final[dict[str, str]] = {
    "GBP": (
        "Bank of England: /monetary-policy/upcoming-mpc-dates serves 2026-2027 only; "
        "/monetary-policy-summary-and-minutes/{year} 404; sitemap.xml 500; "
        "the publications RSS carries the latest 50 items"
    ),
    "CAD": (
        "Bank of Canada: /press/press-releases/{year}/ renders client-side and "
        "carries no dates in the served HTML; the key-interest-rate page lists "
        "recent decisions only; sitemap_index.xml 404"
    ),
    "NZD": (
        "Reserve Bank of New Zealand: HTTP 403 to every client tried, including a "
        "complete browser header set, and to the sitemap and RSS paths"
    ),
    "CHF": (
        "Swiss National Bank: every monetary-policy-assessment and press-release "
        "path tried returns 404; no machine-readable index found"
    ),
}


def _fetch(url: str, *, browser: bool = False, attempts: int = 4) -> tuple[bytes, dict[str, Any]]:
    """One GET, with the provenance the plan requires recorded beside the bytes.

    `rba.gov.au` refuses intermittently even with the browser header set, so a
    refusal is retried. A retry that succeeds is still one acquisition; the
    record carries the number of attempts so a flaky source is visible rather
    than smoothed over.
    """
    headers = _BROWSER_HEADERS if browser else _PLAIN_HEADERS
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            request = urllib.request.Request(url, headers=headers)  # noqa: S310 - fixed https
            with urllib.request.urlopen(request, timeout=180, context=_CONTEXT) as response:  # noqa: S310
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
                time.sleep(4.0 * attempt)
    raise RuntimeError(f"could not acquire {url}: {last}")


def _iso(year: int, month: int, day: int) -> str:
    return dt.date(year, month, day).isoformat()


_FOMC_STATEMENT = re.compile(
    r"<strong>Statement:</strong>.{0,400}?monetary(\d{4})(\d{2})(\d{2})a\.htm",
    re.S,
)


def fomc() -> tuple[list[str], dict[str, Any]]:
    """FOMC announcement dates, from the statement identifiers on the calendar.

    A statement is published at `/newsevents/pressreleases/monetaryYYYYMMDDa.htm`
    and the calendar page links one per meeting. The date is the identifier, so
    nothing here depends on how the page renders.

    The identifier alone is **not** enough. The same page carries the *Statement
    on Longer-Run Goals and Monetary Policy Strategy*, published by notation vote
    on 2025-08-22 at the same URL shape, which is not a rate decision and is not
    a scheduled meeting. A decision row is the one labelled `Statement:`, so the
    link is taken only where that label precedes it. Taking every identifier gave
    nine FOMC meetings in 2025, which the cadence check caught.
    """
    payload, provenance = _fetch(FOMC_URL)
    text = payload.decode("utf-8", "replace")
    stamps = sorted(set(_FOMC_STATEMENT.findall(text)))
    dates = [_iso(int(y), int(m), int(d)) for y, m, d in stamps]
    provenance["extracted"] = len(dates)
    provenance["rule"] = (
        "monetaryYYYYMMDDa.htm preceded by a <strong>Statement:</strong> label, "
        "which excludes the longer-run-goals notation vote"
    )
    return dates, provenance


def ecb(years: tuple[int, ...]) -> tuple[list[str], dict[str, Any]]:
    """ECB Governing Council monetary policy decision dates, one index per year."""
    dates: list[str] = []
    records: list[dict[str, Any]] = []
    for year in years:
        payload, provenance = _fetch(ECB_URL_TEMPLATE.format(year=year))
        text = payload.decode("utf-8", "replace")
        stamps = sorted(set(re.findall(r"ecb\.is(\d{2})(\d{2})(\d{2})", text)))
        found = [_iso(2000 + int(y), int(m), int(d)) for y, m, d in stamps]
        provenance["year"] = year
        provenance["extracted"] = len(found)
        records.append(provenance)
        dates.extend(found)
    return sorted(set(dates)), {
        "rule": (
            "statement identifier ecb.isYYMMDD on the monetary-policy-statement index. "
            "The ecb.mp identifier is not used: it appears on only three of the five "
            "years and would have given 0, 0, 3, 7, 3 meetings"
        ),
        "pages": records,
    }


def boj() -> tuple[list[str], dict[str, Any]]:
    """Bank of Japan MPM statement dates, from the statement filenames.

    The page carries every meeting back to 2010, so it is filtered downstream by
    span rather than by page. A BoJ statement is `kYYMMDD[a-z].pdf` and the date
    in the filename is the day the decision was published.
    """
    payload, provenance = _fetch(BOJ_URL)
    text = payload.decode("utf-8", "replace")
    stamps = sorted(set(re.findall(r"k(\d{2})(\d{2})(\d{2})[a-z]?\.pdf", text)))
    dates = [_iso(2000 + int(y), int(m), int(d)) for y, m, d in stamps]
    provenance["extracted"] = len(dates)
    provenance["rule"] = "statement filename kYYMMDD.pdf on the MPM schedule-and-minutes page"
    return dates, provenance


_RBA_ARTICLE = re.compile(
    r'<span itemprop="headline">(?P<title>.*?)</span>'
    r'.*?<time datetime="(?P<date>\d{4}-\d{2}-\d{2})"',
    re.S,
)
#: The RBA release titles are "Statement by <Governor>: Monetary Policy Decision"
#: through 2023 and "Statement by the Monetary Policy Board: Monetary Policy
#: Decision" from 2024. Matching the trailing phrase covers both without
#: enumerating governors, and excludes the Payments System Board updates that
#: share the page.
_RBA_TITLE = re.compile(r"Monetary Policy Decision", re.I)


def rba(years: tuple[int, ...]) -> tuple[list[str], dict[str, Any]]:
    """RBA Board monetary policy decision dates, from the media-release index."""
    dates: list[str] = []
    records: list[dict[str, Any]] = []
    for year in years:
        payload, provenance = _fetch(RBA_URL_TEMPLATE.format(year=year), browser=True)
        text = payload.decode("utf-8", "replace")
        found = sorted(
            {
                match.group("date")
                for match in _RBA_ARTICLE.finditer(text)
                if _RBA_TITLE.search(re.sub(r"<[^>]+>", "", match.group("title")))
            }
        )
        provenance["year"] = year
        provenance["extracted"] = len(found)
        records.append(provenance)
        dates.extend(found)
    return sorted(set(dates)), {
        "rule": 'media releases whose headline contains "Monetary Policy Decision"',
        "pages": records,
    }


def acquire(years: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025)) -> dict[str, Any]:
    """Every acquirable scheduled calendar, with provenance and a cadence check.

    Returns dates for the whole calendar years, not for the panel spans. The
    panel filter belongs where the panels are, so a meeting one day outside a
    span is visible as an excluded meeting rather than as a missing one.
    """
    usd_dates, usd_provenance = fomc()
    eur_dates, eur_provenance = ecb(years)
    jpy_dates, jpy_provenance = boj()
    aud_dates, aud_provenance = rba(years)

    by_currency = {
        "USD": [d for d in usd_dates if int(d[:4]) in years],
        "EUR": [d for d in eur_dates if int(d[:4]) in years],
        "JPY": [d for d in jpy_dates if int(d[:4]) in years],
        "AUD": [d for d in aud_dates if int(d[:4]) in years],
    }
    provenance = {
        "USD": usd_provenance,
        "EUR": eur_provenance,
        "JPY": jpy_provenance,
        "AUD": aud_provenance,
    }

    cadence: dict[str, Any] = {}
    for currency, dates in by_currency.items():
        per_year = {year: sum(1 for d in dates if int(d[:4]) == year) for year in years}
        expected = {year: EXPECTED_MEETINGS[currency].get(year) for year in years}
        cadence[currency] = {
            "per_year": per_year,
            "expected": expected,
            "matches": all(per_year[y] == expected[y] for y in years),
            #: `all()` over an empty list is True, so a bank whose extraction
            #: returned nothing would report "weekday only" and "strictly
            #: increasing". Both now require dates to exist.
            "weekday_only": bool(dates)
            and all(dt.date.fromisoformat(d).weekday() < 5 for d in dates),
            "strictly_increasing": bool(dates) and dates == sorted(set(dates)),
        }

    return {
        "dates": by_currency,
        "provenance": provenance,
        "cadence": cadence,
        "unacquirable": UNACQUIRABLE,
        "years": list(years),
    }


def event_dates_for_pair(pair: str, calendar: dict[str, list[str]]) -> set[str]:
    """The scheduled-decision dates that touch `pair`.

    A meeting is an event for a pair when the bank belongs to **either** leg. A
    pair with no covered leg gets an empty set, which is why `GBP_CHF` drops out
    of the study by construction rather than by result.
    """
    base, quote = pair.split("_")
    dates: set[str] = set()
    for currency in (base, quote):
        dates.update(calendar.get(currency, ()))
    return dates


__all__ = [
    "BOJ_URL",
    "ECB_URL_TEMPLATE",
    "EXPECTED_MEETINGS",
    "FOMC_URL",
    "RBA_URL_TEMPLATE",
    "UNACQUIRABLE",
    "acquire",
    "boj",
    "ecb",
    "event_dates_for_pair",
    "fomc",
    "rba",
]
