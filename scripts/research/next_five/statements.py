# ruff: noqa: E501 -- statement prose
"""U3 / S27 の中央銀行声明 — 取得と、凍結した語彙による採点（第 2 裁定 §20）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**一次入力は中央銀行の公式 archive だけ**（news 要約や論評は使わない）:

- Fed — `federalreserve.gov/json/ne-press.json` の「Federal Reserve issues FOMC statement」
- ECB — 年別 press 一覧の「Monetary policy decisions」
- BoJ — 年別 `state_YYYY` 一覧の声明（`kYYMMDD`）

**採点式は凍結どおり**: (hawkish 語数 − dovish 語数) / 文書の語数。signal はその
**前回声明からの変化**なので、各 site の navigation など毎回同じ文言は差分で消える。

**語彙は本文を 1 語も数える前に固定した**（`prereg.TONE_LEXICON`）。別の語彙を試すことはしない。
"""

from __future__ import annotations

import html
import json
import re
from typing import Any, Final

import pandas as pd

from scripts.research.data_access.fetch import PARSER_FAILURE, FetchError, fetch
from scripts.research.next_five import prereg

FED_LIST: Final[str] = "https://www.federalreserve.gov/json/ne-press.json"
#: ECB の年別 press 一覧は 2024 年に形式が変わり 2025 年は 404 になった。**金融政策決定の
#: archive**（同じ公式の声明を列挙する別の一覧）は全年で取れるので、こちらを使う
ECB_LIST: Final[str] = (
    "https://www.ecb.europa.eu/press/govcdec/mopo/{year}/html/index_include.en.html"
)
BOJ_LIST: Final[str] = "https://www.boj.or.jp/en/mopo/mpmdeci/state_{year}/index.htm"

#: 本文の領域（見つからなければ page 全体を使い、その旨を記録する）
MAIN_REGION: Final[dict[str, str]] = {
    "USD": r'<div[^>]*id="article"[^>]*>(.*?)<div[^>]*id="lastUpdate"',
    "EUR": r"<main[^>]*>(.*?)</main>",
    "JPY": r'<div[^>]*id="contents"[^>]*>(.*?)<div[^>]*id="footer"',
}


def _clean(raw: str) -> str:
    raw = re.sub(r"<(script|style|nav|header|footer)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def score(text: str) -> dict[str, float]:
    """凍結した式。**語彙は prereg にあり、ここでは変えない。**"""
    words = re.findall(r"[a-z]+", text.lower())
    if not words:
        raise FetchError(PARSER_FAILURE, "本文に語が無い")
    hawkish = sum(1 for w in words if w in prereg.TONE_LEXICON["hawkish"])
    dovish = sum(1 for w in words if w in prereg.TONE_LEXICON["dovish"])
    return {
        "hawkish": float(hawkish),
        "dovish": float(dovish),
        "words": float(len(words)),
        "tone": (hawkish - dovish) / len(words),
    }


def _document(url: str, currency: str, *, opt_in_env: str) -> tuple[str, str]:
    result = fetch(url, opt_in_env=opt_in_env, expect="html")
    if not result.ok or result.payload is None:
        raise FetchError(result.outcome, result.error or result.outcome, result.http_status)
    raw = result.payload.decode("utf-8", "replace")
    region = re.search(MAIN_REGION[currency], raw, flags=re.S | re.I)
    return _clean(region.group(1) if region else raw), ("MAIN_REGION" if region else "WHOLE_PAGE")


def fed_documents(years: range, *, opt_in_env: str) -> list[dict[str, Any]]:
    result = fetch(FED_LIST, opt_in_env=opt_in_env, expect="json")
    if not result.ok or result.payload is None:
        raise FetchError(result.outcome, result.error or result.outcome, result.http_status)
    rows = json.loads(result.payload.decode("utf-8-sig"))
    out = []
    for row in rows:
        if "FOMC statement" not in row.get("t", ""):
            continue
        #: 日付の形式は「1/31/2006」と「9/22/2026 4:30:00 PM」が混在する。日付部分だけを読む
        stamp = pd.to_datetime(str(row["d"]).split(" ")[0], format="%m/%d/%Y")
        if stamp.year in years:
            out.append(
                {
                    "date": stamp.normalize(),
                    "url": "https://www.federalreserve.gov" + row["l"],
                    "title": row["t"],
                }
            )
    return out


def ecb_documents(years: range, *, opt_in_env: str) -> list[dict[str, Any]]:
    """ECB の「Monetary policy decisions」。一覧は全言語版を並べるので **英語版だけ** を拾う。"""
    out: dict[str, dict[str, Any]] = {}
    for year in years:
        result = fetch(ECB_LIST.format(year=year), opt_in_env=opt_in_env, expect="html")
        if not result.ok or result.payload is None:
            raise FetchError(result.outcome, result.error or result.outcome, result.http_status)
        page = result.payload.decode("utf-8", "replace")
        for path, day in re.findall(
            rf'href="(/press/pr/date/{year}/html/ecb\.mp(\d{{6}})[^"]*\.en\.html)"', page
        ):
            out.setdefault(
                day,
                {
                    "date": pd.to_datetime(day, format="%y%m%d"),
                    "url": "https://www.ecb.europa.eu" + path,
                    "title": "Monetary policy decisions",
                },
            )
    return list(out.values())


def boj_documents(years: range, *, opt_in_env: str) -> list[dict[str, Any]]:
    out = []
    for year in years:
        result = fetch(BOJ_LIST.format(year=year), opt_in_env=opt_in_env, expect="html")
        if not result.ok or result.payload is None:
            raise FetchError(result.outcome, result.error or result.outcome, result.http_status)
        page = result.payload.decode("utf-8", "replace")
        for link in sorted(
            set(re.findall(rf'href="(/en/mopo/mpmdeci/state_{year}/k(\d{{6}})a\.htm)"', page))
        ):
            path, day = link
            out.append(
                {
                    "date": pd.to_datetime(day, format="%y%m%d"),
                    "url": "https://www.boj.or.jp" + path,
                    "title": "Statement on Monetary Policy",
                }
            )
    return out


LISTERS: Final[dict[str, Any]] = {"USD": fed_documents, "EUR": ecb_documents, "JPY": boj_documents}


def tone_series(
    currency: str, years: range, *, opt_in_env: str, is_seen
) -> tuple[pd.Series, list[dict[str, Any]]]:
    """1 中銀の tone series。**保護期間の日付の声明は request しない。**"""
    documents = [
        d for d in LISTERS[currency](years, opt_in_env=opt_in_env) if is_seen(d["date"].date())
    ]
    records: list[dict[str, Any]] = []
    for document in sorted(documents, key=lambda d: d["date"]):
        text, region = _document(document["url"], currency, opt_in_env=opt_in_env)
        scored = score(text)
        records.append(
            {
                "date": str(document["date"].date()),
                "url": document["url"],
                "title": document["title"],
                "region": region,
                **scored,
            }
        )
    if not records:
        raise FetchError(PARSER_FAILURE, f"{currency}: 声明が 1 件も取れなかった")
    series = pd.Series(
        [r["tone"] for r in records],
        index=pd.DatetimeIndex([pd.Timestamp(r["date"]) for r in records]),
        name=f"tone_{currency.lower()}",
    )
    return series, records


__all__ = [
    "LISTERS",
    "MAIN_REGION",
    "boj_documents",
    "ecb_documents",
    "fed_documents",
    "score",
    "tone_series",
]
