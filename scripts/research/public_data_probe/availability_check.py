"""Metadata-only availability check of public, key-free, NON-FX data sources.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Committed as the audit trail of `artifacts/research/edge_sources/public_data_availability.json`,
which it printed once on 2026-09-14 (UTC). **Do not re-run without approval**: it
touches the network, and a changed list of series must still request no FX
series, because FX series pages carry values inside protected spans and the
forward epoch.

For FRED, only the series HTML page (`https://fred.stlouisfed.org/series/<id>`) is
read and only the declared frequency / observation range text is parsed; a null
field means the parser did not match the page, not that the series is absent.
No observation is analysed. Other sources are checked for reachability only.
"""

import json
import re
import ssl
import urllib.request
from datetime import UTC, datetime

FRED_SERIES = {
    "DGS2": "US Treasury 2y constant maturity (daily)",
    "DGS10": "US Treasury 10y constant maturity (daily)",
    "T10Y2Y": "US 10y-2y spread (daily)",
    "IRLTLT01DEM156N": "Germany 10y long-term rate (OECD, monthly)",
    "IRLTLT01JPM156N": "Japan 10y long-term rate (OECD, monthly)",
    "IRLTLT01GBM156N": "UK 10y long-term rate (OECD, monthly)",
    "IRLTLT01AUM156N": "Australia 10y long-term rate (OECD, monthly)",
    "IRLTLT01CAM156N": "Canada 10y long-term rate (OECD, monthly)",
    "IRLTLT01CHM156N": "Switzerland 10y long-term rate (OECD, monthly)",
    "IRLTLT01NZM156N": "New Zealand 10y long-term rate (OECD, monthly)",
    "VIXCLS": "CBOE VIX (daily)",
    "SP500": "S&P 500 index (daily)",
    "NIKKEI225": "Nikkei 225 (daily)",
    "DCOILWTICO": "WTI crude oil spot (daily)",
    "DCOILBRENTEU": "Brent crude oil spot (daily)",
    "BAMLH0A0HYM2": "ICE BofA US high-yield OAS (daily)",
    "SOFR": "SOFR (daily)",
}

OTHER_ENDPOINTS = {
    "ecb_data_portal_yield_curve": "https://data.ecb.europa.eu/data/datasets/YC",
    "bundesbank_statistics_api": "https://api.statistiken.bundesbank.de/rest/",
    "boe_database": "https://www.bankofengland.co.uk/boeapps/database/",
    "boc_valet_series_metadata_2y": "https://www.bankofcanada.ca/valet/series/BD.CDN.2YR.DQ.YLD/json",  # noqa: E501
    "rba_statistical_tables_f2": "https://www.rba.gov.au/statistics/tables/",
    "japan_mof_jgb_interest_rate": "https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/index.htm",  # noqa: E501
    "snb_data_portal": "https://data.snb.ch/en",
    "rbnz_statistics": "https://www.rbnz.govt.nz/statistics",
    "cftc_cot_historical": "https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm",  # noqa: E501
    "us_treasury_par_yield": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates",  # noqa: E501
}

CTX = ssl.create_default_context()


def fetch(url: str, limit: int = 400_000) -> tuple[int | None, str]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 research-availability-check"}
    )
    try:
        with urllib.request.urlopen(request, timeout=30, context=CTX) as response:
            return response.status, response.read(limit).decode("utf-8", errors="replace")
    except Exception as error:  # noqa: BLE001
        return None, f"{type(error).__name__}: {error}"[:200]


out = {"checked_utc": datetime.now(UTC).isoformat(), "fred": {}, "other": {}}
for series, label in FRED_SERIES.items():
    status, text = fetch(f"https://fred.stlouisfed.org/series/{series}")
    record = {"label": label, "http_status": status}
    if status == 200:
        freq = re.search(r"Frequency:\s*</span>\s*([^<]+)<", text) or re.search(
            r'"frequency"\s*:\s*"([^"]+)"', text
        )
        rng = re.search(r"(\d{4}-\d{2}-\d{2})\s*(?:to|&nbsp;to&nbsp;)\s*(\d{4}-\d{2}-\d{2})", text)
        start = re.search(r"observation_start[^0-9]*(\d{4}-\d{2}-\d{2})", text)
        record["frequency_text"] = freq.group(1).strip() if freq else None
        record["declared_range"] = [rng.group(1), rng.group(2)] if rng else None
        record["observation_start_field"] = start.group(1) if start else None
    else:
        record["error"] = text
    out["fred"][series] = record
for name, url in OTHER_ENDPOINTS.items():
    status, text = fetch(url, limit=20_000)
    out["other"][name] = {"url": url, "http_status": status, "error": None if status else text}
print(json.dumps(out, indent=1, ensure_ascii=False))
