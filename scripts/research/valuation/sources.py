# ruff: noqa: E501 -- source URLs and provenance prose
"""Where T-V's data comes from, and how the protected span is excluded at the request.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Two official publishers, both free and key-free, and both honouring a server-side
period bound — which is what makes the exclusion a property of the request rather
than of a local filter:

* **FX** — the European Central Bank's euro foreign-exchange reference rates. One
  14:15 CET concertation snapshot covers every G10 currency, so the cross-section
  is synchronous by construction. `endPeriod` ends the request before the
  protected span begins.
* **CPI** — the Bank for International Settlements' long consumer price series,
  one provider for all eight countries, with the same period bounds.

The mechanism was verified on **non-FX** datasets before this module existed (the
ECB's yield curve and the BIS's CPI), so no FX observation was fetched to test it.

**Disclosure.** While checking the BIS API's shape, a 2005-2006 daily JPY/USD file
was fetched and deleted immediately; only the header and title text were
displayed, and no observation was read, analysed or kept. The span is outside
every protected window, but the fetch preceded this pre-registration, which is the
wrong order, and it is recorded here rather than left out.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

#: The first day of the protected fresh pool. Every request ends before it.
PROTECTED_FROM: Final[str] = "2016-06-02"
REQUEST_END: Final[str] = "2016-06-01"
REQUEST_START: Final[str] = "1999-01-04"

#: CPI is requested from well before the FX span so the anchor has history to use.
CPI_REQUEST_START: Final[str] = "1994-01"
CPI_REQUEST_END: Final[str] = "2016-05"


@dataclass(frozen=True, slots=True)
class Series:
    currency: str
    body: str
    dataset: str
    key: str
    kind: str
    note: str = ""


#: units of the currency per one euro, daily reference rate
FX: Final[tuple[Series, ...]] = tuple(
    Series(
        currency=currency,
        body="European Central Bank",
        dataset="EXR",
        key=f"D.{currency}.EUR.SP00.A",
        kind="fx",
        note="euro foreign-exchange reference rate, 14:15 CET concertation",
    )
    for currency in ("USD", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD")
)

#: monthly consumer price index, one provider for every country in the universe
CPI: Final[tuple[Series, ...]] = tuple(
    Series(
        currency=currency,
        body="Bank for International Settlements",
        dataset="WS_LONG_CPI",
        key=f"M.{area}.628",
        kind="cpi",
        note=note,
    )
    for currency, area, note in (
        ("EUR", "XM", "euro area"),
        ("USD", "US", ""),
        ("JPY", "JP", ""),
        ("GBP", "GB", ""),
        ("CHF", "CH", ""),
        ("AUD", "AU", "quarterly publication, carried forward"),
        ("CAD", "CA", ""),
        ("NZD", "NZ", "quarterly publication, carried forward"),
    )
)


def fx_url(series: Series, *, start: str = REQUEST_START, end: str = REQUEST_END) -> str:
    """The ECB request, with the period bound in the URL rather than in a later filter."""
    if end >= PROTECTED_FROM:
        raise ValueError(f"the request must end before {PROTECTED_FROM}, not at {end}")
    return (
        f"https://data-api.ecb.europa.eu/service/data/EXR/{series.key}"
        f"?format=csvdata&startPeriod={start}&endPeriod={end}"
    )


def cpi_url(series: Series, *, start: str = CPI_REQUEST_START, end: str = CPI_REQUEST_END) -> str:
    if end >= PROTECTED_FROM[:7]:
        raise ValueError(f"the request must end before {PROTECTED_FROM[:7]}, not at {end}")
    return (
        f"https://stats.bis.org/api/v2/data/dataflow/BIS/{series.dataset}/1.0/{series.key}"
        f"?format=csv&startPeriod={start}&endPeriod={end}"
    )


EXCLUSION: Final[dict[str, str]] = {
    "rule": "the protected fresh pool is excluded by the request, never by a local filter",
    "how": f"every FX request carries endPeriod={REQUEST_END}, one day before {PROTECTED_FROM}",
    "verified_before_any_fx_read": (
        "both APIs were shown to honour startPeriod/endPeriod on non-FX datasets — the ECB's "
        "yield curve and the BIS's consumer prices — so the mechanism was never tested on FX"
    ),
    "guard": (
        "after each download the maximum observation date is checked against the protected start "
        "and the file is refused if it reaches it, so a server that ignored the bound cannot pass"
    ),
    "if_a_source_cannot_be_bounded": "it is not used",
}


__all__ = [
    "CPI",
    "CPI_REQUEST_END",
    "CPI_REQUEST_START",
    "EXCLUSION",
    "FX",
    "PROTECTED_FROM",
    "REQUEST_END",
    "REQUEST_START",
    "Series",
    "cpi_url",
    "fx_url",
]
