# ruff: noqa: E501 -- provider prose
"""provider ごとの取得・parse・metadata 抽出（第 2 裁定 §8 / §10）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

各関数は **(series, metadata)** を返す。series は日付 index の float、metadata は
title / units / frequency / seasonal_adjustment / notes / source_url / metadata_url を持つ。

**切り落としは呼び出し側（cycle の取得層）が行う。** ここで返る series は、
呼び出し側が seen window へ切り落とすまで保存も signal 化もされない。
期間 parameter を受け付ける endpoint では、呼び出し側が期間を request に入れる。
"""

from __future__ import annotations

import html
import io
import json
import re
import zipfile
from typing import Any

import pandas as pd

from scripts.research.data_access.fetch import (
    PARSER_FAILURE,
    SERIES_NOT_FOUND,
    FetchError,
    FetchResult,
    fetch,
)


def _require(result: FetchResult) -> bytes:
    if not result.ok or result.payload is None:
        raise FetchError(result.outcome, result.error or result.outcome, result.http_status)
    return result.payload


def _text(payload: bytes) -> str:
    return payload.decode("utf-8-sig", errors="replace")


def _series(stamps: Any, values: Any, name: str) -> pd.Series:
    index = pd.to_datetime(pd.Series(stamps), errors="coerce")
    numbers = pd.to_numeric(
        pd.Series(values).astype(str).str.replace(",", "", regex=False), errors="coerce"
    )
    frame = pd.DataFrame({"v": numbers.to_numpy()}, index=pd.DatetimeIndex(index))
    frame = frame[frame.index.notna()].dropna()
    series = frame["v"].sort_index()
    series = series[~series.index.duplicated(keep="last")]
    series.name = name
    if series.empty:
        raise FetchError(PARSER_FAILURE, f"{name}: 数値の観測が 1 つも無い")
    if float(series.std(ddof=0)) == 0.0:
        #: 前 cycle の TIC は全 0.0 で通りかけた。**分散ゼロは parse 失敗として扱う**
        raise FetchError(PARSER_FAILURE, f"{name}: 値が定数である（parse を疑う）")
    return series


def _strip_html(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


# ----------------------------------------------------------------------
# ALFRED（St. Louis Fed の公式 vintage 配信。Tier 2）
# ----------------------------------------------------------------------
def alfred(
    series_id: str, *, opt_in_env: str, first: str | None = None, last: str | None = None
) -> tuple[pd.Series, dict[str, Any]]:
    """`alfred.stlouisfed.org` から **現行 vintage** を取る。

    `fred.stlouisfed.org` は本環境から timeout するが、同じ St. Louis Fed の ALFRED は届く。
    **現行 vintage であって real-time vintage ではない** — 改訂留保は呼び出し側が付ける。

    **期間を必ず request に入れる**（2026-09-24 裁定の D-5 policy）。first / last の無い呼び出しは
    全期間を返させるので拒否する。
    """
    if not first or not last:
        from scripts.research.data_access.request_policy import ProtectedRequestError

        raise ProtectedRequestError(
            f"{series_id}: 期間の無い ALFRED request は保護暦日を含みうるので拒否する"
        )
    params = f"id={series_id}"
    if first:
        params += f"&cosd={first}"
    if last:
        params += f"&coed={last}"
    data_url = f"https://alfred.stlouisfed.org/graph/alfredgraph.csv?{params}"
    meta_url = f"https://alfred.stlouisfed.org/series?seid={series_id}"
    frame = pd.read_csv(
        io.StringIO(_text(_require(fetch(data_url, opt_in_env=opt_in_env, expect="csv"))))
    )
    if frame.shape[1] < 2:
        raise FetchError(PARSER_FAILURE, f"{series_id}: 列が足りない")
    series = _series(frame.iloc[:, 0], frame.iloc[:, 1], series_id)

    page = _strip_html(_text(_require(fetch(meta_url, opt_in_env=opt_in_env, expect="html"))))
    title = re.search(r"^(.*?)\s*\|\s*ALFRED", page)
    units = re.search(r"Units:\s*(.{1,90}?)\s*(?:Frequency:|Notes:|$)", page)
    frequency = re.search(r"Frequency:\s*([A-Za-z,\- ]{3,40}?)\s*(?:Notes:|Units:|Source|$)", page)
    notes = re.search(r"Notes:\s*(.{0,600}?)\s*(?:Suggested Citation|Source:|Release:|$)", page)
    units_text = units.group(1).strip() if units else ""
    adjustment = (
        "Seasonally Adjusted"
        if "Not Seasonally Adjusted" not in units_text and "Seasonally Adjusted" in units_text
        else "Not Seasonally Adjusted"
        if "Not Seasonally Adjusted" in units_text
        else "UNKNOWN"
    )
    frequency_text = frequency.group(1).strip() if frequency else ""
    if not frequency_text:
        #: metadata ページから取れないときは、観測間隔から導き、その旨を記録する
        spacing = float(pd.Series(series.index).diff().dt.days.median())
        frequency_text = (
            "Daily"
            if spacing <= 4
            else "Weekly"
            if spacing <= 10
            else "Monthly"
            if spacing <= 40
            else "Quarterly"
        ) + "（観測間隔から導出）"
    return series, {
        "provider": "Federal Reserve Bank of St. Louis (ALFRED)",
        "series_id": series_id,
        "title": title.group(1).strip() if title else "",
        "units": units_text,
        "frequency": frequency_text,
        "seasonal_adjustment": adjustment,
        "notes": notes.group(1).strip() if notes else "",
        "source_url": data_url,
        "metadata_url": meta_url,
    }


# ----------------------------------------------------------------------
# Bank of Japan 時系列 API（Tier 1）
# ----------------------------------------------------------------------
def boj(db: str, code: str, *, opt_in_env: str) -> tuple[pd.Series, dict[str, Any]]:
    meta_url = f"https://www.stat-search.boj.or.jp/api/v1/getMetadata?format=json&lang=en&db={db}"
    data_url = f"https://www.stat-search.boj.or.jp/api/v1/getDataCode?format=json&lang=en&db={db}&code={code}"
    meta = json.loads(_text(_require(fetch(meta_url, opt_in_env=opt_in_env, expect="json"))))
    row = next((r for r in meta.get("RESULTSET", []) if r.get("SERIES_CODE") == code), None)
    if row is None:
        raise FetchError(SERIES_NOT_FOUND, f"BoJ {db}/{code} が metadata に無い")
    payload = json.loads(_text(_require(fetch(data_url, opt_in_env=opt_in_env, expect="json"))))
    result = (payload.get("RESULTSET") or [{}])[0]
    values = result.get("VALUES") or {}
    stamps = values.get("SURVEY_DATES") or []
    numbers = values.get("VALUES") or []
    if not stamps:
        raise FetchError(PARSER_FAILURE, f"BoJ {code}: VALUES が空（形: {list(result)[:8]}）")
    parsed = [pd.to_datetime(str(s), format="%Y%m", errors="coerce") for s in stamps]
    series = _series(parsed, numbers, code)
    return series, {
        "provider": "Bank of Japan",
        "series_id": f"{db}/{code}",
        "title": row.get("NAME_OF_TIME_SERIES", ""),
        "units": row.get("UNIT", ""),
        "frequency": row.get("FREQUENCY", ""),
        "seasonal_adjustment": "Not Seasonally Adjusted（残高）",
        "notes": row.get("NOTES", ""),
        "source_url": data_url,
        "metadata_url": meta_url,
    }


# ----------------------------------------------------------------------
# Swiss National Bank data portal（Tier 1）
# ----------------------------------------------------------------------
def snb_cube(cube: str, item: str, *, opt_in_env: str) -> tuple[pd.Series, dict[str, Any]]:
    meta_url = f"https://data.snb.ch/api/cube/{cube}/dimensions/en"
    data_url = f"https://data.snb.ch/api/cube/{cube}/data/csv/en"
    dims = json.loads(_text(_require(fetch(meta_url, opt_in_env=opt_in_env, expect="json"))))
    path: list[str] = []

    def walk(items: list[dict[str, Any]], trail: list[str]) -> None:
        for entry in items:
            here = [*trail, entry.get("name", "")]
            if entry.get("id") == item:
                path.extend(here)
            walk(entry.get("dimensionItems", []) or [], here)

    for dim in dims.get("dimensions", []):
        walk(dim.get("dimensionItems", []), [])
    if not path:
        raise FetchError(SERIES_NOT_FOUND, f"SNB {cube}: item {item} が dimension 一覧に無い")
    raw = _text(_require(fetch(data_url, opt_in_env=opt_in_env, expect="csv")))
    lines = raw.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.replace('"', "").startswith("Date")), None
    )
    if start is None:
        raise FetchError(PARSER_FAILURE, f"SNB {cube}: header 行が無い")
    frame = pd.read_csv(io.StringIO("\n".join(lines[start:])), sep=";")
    frame = frame[frame.iloc[:, 1].astype(str) == item]
    stamps = pd.to_datetime(frame.iloc[:, 0].astype(str), format="%Y-%m", errors="coerce")
    series = _series(stamps, frame.iloc[:, -1], f"{cube}/{item}")
    return series, {
        "provider": "Swiss National Bank",
        "series_id": f"{cube}/D0={item}",
        "title": " / ".join(path),
        "units": "CHF millions",
        "frequency": "MONTHLY",
        "seasonal_adjustment": "Not Seasonally Adjusted（残高）",
        "notes": "",
        "source_url": data_url,
        "metadata_url": meta_url,
    }


# ----------------------------------------------------------------------
# Bank of Canada Valet（Tier 1）
# ----------------------------------------------------------------------
def boc_valet(
    series_id: str, *, opt_in_env: str, first: str | None = None, last: str | None = None
) -> tuple[pd.Series, dict[str, Any]]:
    params = []
    if first:
        params.append(f"start_date={first}")
    if last:
        params.append(f"end_date={last}")
    query = ("?" + "&".join(params)) if params else ""
    data_url = f"https://www.bankofcanada.ca/valet/observations/{series_id}/json{query}"
    payload = json.loads(_text(_require(fetch(data_url, opt_in_env=opt_in_env, expect="json"))))
    detail = (payload.get("seriesDetail") or {}).get(series_id)
    if not detail:
        raise FetchError(SERIES_NOT_FOUND, f"BoC {series_id}: seriesDetail が無い")
    observations = payload.get("observations") or []
    stamps = [row.get("d") for row in observations]
    values = [(row.get(series_id) or {}).get("v") for row in observations]
    series = _series(stamps, values, series_id)
    return series, {
        "provider": "Bank of Canada",
        "series_id": series_id,
        "title": f"{detail.get('label', '')} — {detail.get('description', '')}",
        #: valet の seriesDetail は単位を持たない。推測で埋めない
        "units": "NOT_PROVIDED_BY_ENDPOINT（signal は log 変化なので単位に依存しない）",
        "frequency": "MONTHLY（group B1_MONTHLY: month-end）",
        "seasonal_adjustment": "Not Seasonally Adjusted（残高）",
        "notes": "",
        "source_url": data_url,
        "metadata_url": f"https://www.bankofcanada.ca/valet/series/{series_id}/json",
    }


# ----------------------------------------------------------------------
# Federal Reserve H.4.1 一括配信（Tier 1）
# ----------------------------------------------------------------------
def fed_h41(series_name: str, *, opt_in_env: str) -> tuple[pd.Series, dict[str, Any]]:
    url = "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H41&filetype=zip"
    archive = zipfile.ZipFile(io.BytesIO(_require(fetch(url, opt_in_env=opt_in_env, expect="zip"))))
    name = next((n for n in archive.namelist() if n.lower().endswith("_data.xml")), None)
    if name is None:
        raise FetchError(PARSER_FAILURE, "H.4.1: data xml が zip に無い")
    text = archive.read(name).decode("utf-8", "replace")
    match = re.search(
        rf'<kf:Series ([^>]*SERIES_NAME="{re.escape(series_name)}"[^>]*)>(.*?)</kf:Series>',
        text,
        flags=re.S,
    )
    if match is None:
        raise FetchError(SERIES_NOT_FOUND, f"H.4.1: {series_name} が無い")
    attrs, body = match.group(1), match.group(2)
    descriptions = re.findall(r"<common:AnnotationText>([^<]*)</common:AnnotationText>", body)
    observations = re.findall(r'<frb:Obs[^>]*TIME_PERIOD="([^"]+)"[^>]*OBS_VALUE="([^"]+)"', body)
    if not observations:
        observations = [
            (b, a)
            for a, b in re.findall(
                r'<frb:Obs[^>]*OBS_VALUE="([^"]+)"[^>]*TIME_PERIOD="([^"]+)"', body
            )
        ]
    series = _series([o[0] for o in observations], [o[1] for o in observations], series_name)

    def attr(key: str) -> str:
        found = re.search(rf'{key}="([^"]+)"', attrs)
        return found.group(1) if found else ""

    return series, {
        "provider": "Board of Governors of the Federal Reserve System (H.4.1)",
        "series_id": series_name,
        "title": descriptions[0] if descriptions else "",
        "units": f"{attr('UNIT')} x{attr('UNIT_MULT')} {attr('CURRENCY')}".strip(),
        "frequency": "WEEKLY（Wednesday level）" if series_name.endswith(".WW") else attr("FREQ"),
        "seasonal_adjustment": "Not Seasonally Adjusted（残高）",
        "notes": descriptions[1] if len(descriptions) > 1 else "",
        "source_url": url,
        "metadata_url": url,
    }


__all__ = ["alfred", "boc_valet", "boj", "fed_h41", "snb_cube"]
