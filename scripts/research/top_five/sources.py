# ruff: noqa: E501 -- acquisition prose
"""Top-Five が使う public / free source の request 定義。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Authority: 2026-09-21 Human + ChatGPT 裁定 §5（本取得の承認）・§6（記録義務）・§8（境界）。

**境界の守り方は 2 通りしかない。**

1. **期間パラメータを取る endpoint** — bound を URL に入れる。`valuation/sources.py` が
   確立した形で、これが原則である（裁定 §8「request 自体から protected span を除外」）。
2. **全量配信しかない endpoint**（CBOE / EIA / SNB / TIC）— URL に bound を入れられない。
   この場合は **acquisition 層で parsed date により切り落とし、切り落とす前の frame を
   signal 層へ一切渡さない**。`load()` は truncate 済みの frame しか返さないので、
   呼び出し側は raw frame に触れられない。

**文字列比較は使わない。** bound は `dt.date` に parse してから比較する。
`"2016-6-2"` や `"2016-06"` のような曖昧な綴りは受け付けずに落とす。
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Final

from scripts.research.top_five import prereg

#: signal が触れてよい唯一の期間。2 つの seen span の和集合であり、
#: **その間にある保護 pool は含まない**。
SEEN_WINDOWS: Final[tuple[tuple[dt.date, dt.date], ...]] = (
    (
        dt.date.fromisoformat(prereg.SPANS["long"]["first"]),
        dt.date.fromisoformat(prereg.SPANS["long"]["last_return_day"]),
    ),
    (
        dt.date.fromisoformat(prereg.SPANS["recent"]["first"]),
        dt.date.fromisoformat(prereg.SPANS["recent"]["last_return_day"]),
    ),
)

_FRESH_POOL_START: Final[dt.date] = dt.date.fromisoformat(
    prereg.PROTECTED_BOUNDS["fresh_pool_start"]
)
_OOS_START: Final[dt.date] = dt.date.fromisoformat(prereg.PROTECTED_BOUNDS["oos_slice_start"])


def as_day(value: str, *, field: str) -> dt.date:
    """厳密な `YYYY-MM-DD` だけを受ける。

    緩い parse を許すと `"2016-06"` が「6 月の末日」と解釈される API があり、
    本 repo はその経路で bound を 3 回抜かれている。曖昧な綴りは通さない。
    """
    if not isinstance(value, str) or len(value) != 10 or value[4] != "-" or value[7] != "-":
        raise ValueError(f"{field} must be an exact YYYY-MM-DD, not {value!r}")
    try:
        return dt.date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} must be an exact YYYY-MM-DD, not {value!r}") from error


def is_seen(day: dt.date) -> bool:
    """その日が 2 つの seen span のどちらかに入っているか。**parsed date で判定する。**"""
    return any(first <= day <= last for first, last in SEEN_WINDOWS)


def assert_no_protected_day(days: list[dt.date], *, label: str) -> None:
    """保護領域の日が 1 つでも混じっていたら落とす。

    fresh pool / OOS / dead / forward はいずれも「2 つの seen span の外側」なので、
    `is_seen` の否定で足りる。個別の境界も名前つきで確認しておく — 将来 span が
    足されたときに、この assertion がまず気づく側でいてほしい。
    """
    stray = [day for day in days if not is_seen(day)]
    if stray:
        raise ValueError(
            f"{label}: seen span の外の日が {len(stray)} 件混じっている "
            f"（最初の 3 件 {stray[:3]}）。protected 領域を signal に触れさせない"
        )
    for day in days:
        if _FRESH_POOL_START <= day < _OOS_START and not is_seen(day):  # pragma: no cover
            raise ValueError(f"{label}: {day} は保護 pool である")


@dataclass(frozen=True)
class Source:
    """1 本の public / free source。

    `bounded_request` が True のものは URL に期間を入れられる。False のものは全量配信
    しかないので、acquisition 層で切り落とす。**どちらであるかを記録する**のは、
    「境界を request で守ったのか、取得後に守ったのか」が監査で効くからである。
    """

    key: str
    track: str
    provider: str
    url: str
    frequency: str
    bounded_request: bool
    publication_timing: str
    parser: str
    note: str = ""


SOURCES: Final[tuple[Source, ...]] = (
    Source(
        key="vix",
        track="T1",
        provider="CBOE",
        url="https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
        frequency="daily",
        bounded_request=False,
        publication_timing="close 22:15 CET（長 span で 2 営業日 lag、近 span で 1 営業日）",
        parser="csv",
        note="1990-2003 は 2003 年の新方式による遡及計算値",
    ),
    Source(
        key="wti",
        track="T2",
        provider="U.S. Energy Information Administration",
        url="https://www.eia.gov/dnav/pet/hist_xls/RWTCd.xls",
        frequency="daily observations, weekly (Wednesday) publication cycle",
        bounded_request=False,
        publication_timing="水曜サイクル。day t の値は 1-7 暦日遅れ（両 span で 7 営業日 lag）",
        parser="xls",
        note="OLE2 バイナリ。xlrd で **parsing のみ** 行い、埋め込み macro は実行しない",
    ),
    Source(
        key="ust_10y",
        track="T3",
        provider="U.S. Department of the Treasury",
        url=(
            "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
            "daily-treasury-rates.csv/{year}/all?type=daily_treasury_yield_curve"
            "&field_tdr_date_value={year}&page&_format=csv"
        ),
        frequency="daily",
        bounded_request=True,
        publication_timing="US 21:30-24:00 CET（両 span で 2 営業日 lag）",
        parser="csv",
        note="年ごとに 1 request。取得する年は seen span の年だけに限る",
    ),
    Source(
        key="bund_10y",
        track="T3",
        provider="Deutsche Bundesbank",
        url=(
            "https://api.statistiken.bundesbank.de/rest/data/BBSIS/"
            "D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A?format=csv&lang=en"
        ),
        frequency="daily",
        bounded_request=False,
        publication_timing="夕刻（両 span で 2 営業日 lag）",
        parser="csv",
        note="Zinsstruktur 10 年。Umlaufsrendite (ZAR) は 404 を返す別系列",
    ),
    Source(
        key="boc_10y",
        track="T3",
        provider="Bank of Canada",
        url="https://www.bankofcanada.ca/valet/observations/BD.CDN.10YR.DQ.YLD/csv?start_date={start}&end_date={end}",
        frequency="daily",
        bounded_request=True,
        publication_timing="22:30 CET（両 span で 2 営業日 lag）",
        parser="csv",
    ),
    Source(
        key="snb_10y",
        track="T3",
        provider="Swiss National Bank",
        url="https://data.snb.ch/api/cube/rendoblid/data/csv/en",
        frequency="daily",
        bounded_request=False,
        publication_timing="同等以降（両 span で 2 営業日 lag）",
        parser="csv",
    ),
    Source(
        key="boe_10y",
        track="T3",
        provider="Bank of England",
        url=(
            "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp"
            "?csv.x=yes&Datefrom={boe_from}&Dateto={boe_to}&SeriesCodes=IUDMNZC"
            "&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N"
        ),
        frequency="daily",
        bounded_request=True,
        publication_timing="夕刻（両 span で 2 営業日 lag）",
        parser="csv",
    ),
    Source(
        key="tic_s1",
        track="T5",
        provider="U.S. Department of the Treasury (TIC)",
        url="https://ticdata.treasury.gov/Publish/s1_globl.csv",
        frequency="monthly",
        bounded_request=False,
        publication_timing="第 m 月の値は m+2 月中旬。使用は m+2 月末以降",
        parser="csv",
        note="配信ファイルは改訂後の値（REVISION_CAVEAT）",
    ),
)

BY_KEY: Final[dict[str, Source]] = {source.key: source for source in SOURCES}


def url_for(key: str, *, start: dt.date, end: dt.date) -> str:
    """期間つき request の URL。**bound を入れられない source では呼ばない。**"""
    source = BY_KEY[key]
    if not source.bounded_request:
        raise ValueError(f"{key} は全量配信しかない。acquisition 層で切り落とすこと")
    if end >= _FRESH_POOL_START and start < _FRESH_POOL_START:
        raise ValueError(f"{key}: request が保護 pool をまたいでいる（{start} .. {end}）")
    if not (is_seen(start) and is_seen(end)):
        raise ValueError(f"{key}: request の両端が seen span の内側でない（{start} .. {end}）")
    return source.url.format(
        year=start.year,
        start=start.isoformat(),
        end=end.isoformat(),
        boe_from=start.strftime("%d/%b/%Y"),
        boe_to=end.strftime("%d/%b/%Y"),
    )


def bounded_years() -> tuple[int, ...]:
    """年ごとに request する source が取りに行ってよい年。seen span の年だけ。"""
    years: set[int] = set()
    for first, last in SEEN_WINDOWS:
        years.update(range(first.year, last.year + 1))
    return tuple(sorted(years))


__all__ = [
    "BY_KEY",
    "SEEN_WINDOWS",
    "SOURCES",
    "Source",
    "as_day",
    "assert_no_protected_day",
    "bounded_years",
    "is_seen",
    "url_for",
]
