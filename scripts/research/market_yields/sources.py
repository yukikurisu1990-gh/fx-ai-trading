# ruff: noqa: E501 -- source URLs and provenance prose
"""The official source of each currency's two-year yield, and what it says about itself.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Priority, from the ruling: central bank / treasury first, then FRED-class public
bodies, exchanges, and reproducible public datasets last. Every primary series
below is published by a central bank or a treasury; nothing is scraped from a
third party, and no paid or authenticated source is used.

**Publication times are recorded as unconfirmed.** None of these pages states when
the day's value becomes available, so `availability.py` applies the conservative
rule the ruling requires instead of guessing a delay.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final


@dataclass(frozen=True, slots=True)
class Source:
    currency: str
    body: str
    url: str
    kind: str
    series: str
    maturity: str
    quote_time_local: str
    publication_time: str
    timezone: str
    notes: tuple[str, ...] = field(default_factory=tuple)
    reachable: bool = True
    role: str = "primary"


#: Priority order of the ruling: central bank / treasury first, then FRED-class public
#: bodies, then exchanges, then reproducible public datasets. Every source below is a
#: central bank or a treasury, so no third-party or scraped series is primary.
SOURCES: Final[tuple[Source, ...]] = (
    Source(
        currency="USD",
        body="U.S. Department of the Treasury",
        url="https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={year}&page&_format=csv",
        kind="csv-per-year",
        series="Daily Treasury Par Yield Curve Rates, '2 Yr'",
        maturity="2Y par yield",
        quote_time_local="approximately 15:30 (close of business quotes)",
        publication_time="unconfirmed on the public page",
        timezone="America/New_York",
        notes=("FRED's DGS2 mirrors this series; the Treasury is the primary body",),
    ),
    Source(
        currency="EUR",
        body="Deutsche Bundesbank",
        url="https://api.statistiken.bundesbank.de/rest/data/BBSIS/D.I.ZAR.ZI.EUR.S1311.B.A604.R02XX.R.A.A._Z._Z.A?format=csv&lang=en",
        kind="csv",
        series="BBSIS.D.I.ZAR.ZI.EUR.S1311.B.A604.R02XX.R.A.A._Z._Z.A",
        maturity="2.0Y term-structure yield, listed Federal securities",
        quote_time_local="end of day",
        publication_time="unconfirmed on the public page",
        timezone="Europe/Berlin",
        notes=("the German curve is the euro-area benchmark for a two-year point",),
    ),
    Source(
        currency="EUR",
        body="European Central Bank (data portal, YC dataset)",
        url="https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y?format=csvdata",
        kind="csv",
        series="YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y",
        maturity="2Y spot rate, AAA euro area government bonds",
        quote_time_local="end of day",
        publication_time="unconfirmed on the public page",
        timezone="Europe/Frankfurt",
        role="cross_check",
        notes=("kept as an independent check on the Bundesbank series, never as the primary",),
    ),
    Source(
        currency="JPY",
        body="Ministry of Finance Japan",
        url="https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/historical/jgbcme_all.csv",
        kind="csv",
        series="JGB interest rate, 2Y column",
        maturity="2Y JGB compound yield",
        quote_time_local="approximately 15:00",
        publication_time="unconfirmed on the public page",
        timezone="Asia/Tokyo",
        notes=("the current month arrives in a separate file, jgbcme.csv",),
    ),
    Source(
        currency="GBP",
        body="Bank of England",
        url="https://www.bankofengland.co.uk/-/media/boe/files/statistics/yield-curves/glcnominalddata.zip",
        kind="zip-of-xlsx",
        series="GLC Nominal daily data, sheet '3. spot, short end', 24-month column",
        maturity="2Y nominal spot (fitted curve)",
        quote_time_local="end of day",
        publication_time="unconfirmed on the public page",
        timezone="Europe/London",
        notes=("the current month arrives in latest-yield-curve-data.zip",),
    ),
    Source(
        currency="CAD",
        body="Bank of Canada (Valet API)",
        url="https://www.bankofcanada.ca/valet/observations/BD.CDN.2YR.DQ.YLD/csv",
        kind="csv",
        series="BD.CDN.2YR.DQ.YLD",
        maturity="2Y benchmark bond yield",
        quote_time_local="end of day",
        publication_time="unconfirmed on the public page",
        timezone="America/Toronto",
    ),
    Source(
        currency="NZD",
        body="Reserve Bank of New Zealand",
        url="https://www.rbnz.govt.nz/-/media/project/sites/rbnz/files/statistics/series/b/b2/hb2-daily.xlsx",
        kind="xlsx",
        series="B2 daily, 'Secondary market government bond closing yields', 2 year",
        maturity="2Y government bond closing yield",
        quote_time_local="close",
        publication_time="unconfirmed on the public page",
        timezone="Pacific/Auckland",
        notes=(
            "the page's current file is hb2-daily-close.xlsx, which this environment cannot fetch: "
            "every request is refused with HTTP 403 by the site's protection, with browser headers, "
            "a referer and a cookie jar. The older hb2-daily.xlsx is served and stops on 2025-08-22, "
            "so NZD cannot cover the seen span from here",
        ),
    ),
    Source(
        currency="CHF",
        body="Swiss National Bank (data portal cube rendoblid)",
        url="https://data.snb.ch/api/cube/rendoblid/data/csv/en",
        kind="csv",
        series="rendoblid, D0 = '2J'",
        maturity="2Y Confederation bond yield",
        quote_time_local="end of day",
        publication_time="unconfirmed on the public page",
        timezone="Europe/Zurich",
        notes=(
            "the cube's last publication is dated 2025-09-01 and its last observation is "
            "2025-07-31, so it does not cover the seen corpus to 2025-12-28",
        ),
    ),
    Source(
        currency="AUD",
        body="Reserve Bank of Australia (statistical table F2)",
        url="https://www.rba.gov.au/statistics/tables/csv/f2.1-data.csv",
        kind="csv",
        series="F2.1 capital market yields, government bonds, 2Y",
        maturity="2Y government bond yield",
        quote_time_local="close",
        publication_time="unconfirmed on the public page",
        timezone="Australia/Sydney",
        reachable=False,
        notes=(
            "every automated request from this environment is refused with HTTP 403 "
            "(browser headers included); not unavailable, unverified from here",
        ),
    ),
)


def primary() -> tuple[Source, ...]:
    return tuple(s for s in SOURCES if s.role == "primary")


def by_currency(currency: str) -> Source:
    return next(s for s in primary() if s.currency == currency)


__all__ = ["SOURCES", "Source", "by_currency", "primary"]
