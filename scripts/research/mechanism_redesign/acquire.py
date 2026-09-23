# ruff: noqa: E501 -- acquisition prose
"""Stage 0 の取得 — **保護暦日を request から外したものだけ**（2026-09-24 裁定 §6 / §33–§35）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

- 使う provider は **期間を request に入れられる ALFRED だけ**。bulk-only の provider は
  `request_policy.assert_provider_allowed` が呼ぶ前に止める。
- request の範囲は `request_policy.seen_request_windows(kind)` が **参照期間で**決める
  （月次は long 1990-01 … 2016-05、recent 2021-05 … 2025-11）。
- 応答に request 外の stamp が 1 つでもあれば **保存せずに止める**（filter はしない）。
- series code は候補を事前に列挙し、**provider の metadata（title・units）で意味を確かめたもの
  だけを採る**。候補が 404 なら SERIES_NOT_FOUND として記録し、推測で埋めない。
- **metadata ページ**（alfred.stlouisfed.org/series?seid=…）は provider の文書であって data request
  ではないが、ページの見出しに**最新の観測値が 1 つ表示される**ことがある。ここでは title / units /
  frequency / notes の label だけを読み、観測値は読まない。この露出は報告で開示する（D-M1）。

network に出るのは `MECHANISM_ACQUIRE_APPROVED=1` かつ script として実行した時だけ。
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any, Final

import pandas as pd

from scripts.research.acquisition_safety import digest, write_provenance
from scripts.research.data_access import mapping, providers, request_policy
from scripts.research.data_access.fetch import FetchError

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
DATA_DIR: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch/mechanism_redesign"
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/mechanism_redesign/acquisition.json"
OPT_IN_ENV: Final[str] = "MECHANISM_ACQUIRE_APPROVED"

M: Final[str] = request_policy.MONTH
Q: Final[str] = request_policy.QUARTER

#: slot → 通貨 → 候補（順に試す）。候補は **metadata で確かめるまで mapping ではない。**
#: 各候補は (series_id, 参照期間の種類)。
CANDIDATES: Final[dict[str, dict[str, tuple[tuple[str, str], ...]]]] = {
    "cpi_yoy": {
        "USD": (("CPALTT01USM659N", M),),
        "JPY": (("CPALTT01JPM659N", M),),
        "GBP": (("CPALTT01GBM659N", M),),
        "CAD": (("CPALTT01CAM659N", M),),
        "CHF": (("CPALTT01CHM659N", M),),
        "EUR": (("CPALTT01EZM659N", M),),
        "AUD": (("CPALTT01AUQ659N", Q),),
        "NZD": (("CPALTT01NZQ659N", Q),),
    },
    #: cpi_yoy が 404 / recent 欠けの通貨だけ、**同じ変数（消費者物価）の指数水準**で補う
    "cpi_index": {
        "EUR": (("CP0000EZ19M086NEST", M),),
        "JPY": (("JPNCPIALLMINMEI", M),),
    },
    "unemployment": {
        "USD": (("LRHUTTTTUSM156S", M),),
        "JPY": (("LRHUTTTTJPM156S", M),),
        "GBP": (("LRHUTTTTGBM156S", M),),
        "CAD": (("LRHUTTTTCAM156S", M),),
        "AUD": (("LRHUTTTTAUM156S", M),),
        "EUR": (("LRHUTTTTEZM156S", M),),
        "CHF": (("LRHUTTTTCHQ156S", Q),),
        "NZD": (("LRHUTTTTNZQ156S", Q),),
    },
    "policy_rate": {
        "USD": (("FEDFUNDS", M),),
        "JPY": (("IRSTCB01JPM156N", M),),
        "GBP": (("IRSTCB01GBM156N", M),),
        "CAD": (("IRSTCB01CAM156N", M),),
        "AUD": (("IRSTCB01AUM156N", M),),
        "NZD": (("IRSTCB01NZM156N", M),),
        "CHF": (("IRSTCB01CHM156N", M),),
        "EUR": (("IRSTCB01EZM156N", M),),
    },
    "short_rate_3m": {
        "USD": (("IR3TIB01USM156N", M), ("TB3MS", M)),
        "JPY": (("IR3TIB01JPM156N", M),),
        "GBP": (("IR3TIB01GBM156N", M),),
        "CAD": (("IR3TIB01CAM156N", M),),
        "AUD": (("IR3TIB01AUM156N", M),),
        "NZD": (("IR3TIB01NZM156N", M),),
        "CHF": (("IR3TIB01CHM156N", M),),
        "EUR": (("IR3TIB01EZM156N", M),),
    },
    "epu": {
        "USD": (("USEPUINDXM", M),),
        "EUR": (("EUEPUINDXM", M),),
        "JPY": (("JPNEPUINDXM", M),),
        "GBP": (("UKEPUINDXM", M),),
        "CAD": (("CANEPUINDXM", M),),
        "AUD": (("AUSEPUINDXM", M),),
        "CHF": (("CHEPUINDXM", M),),
    },
}

#: 取得の途中で **provider が request の期間を守らなかった** family。以後この route には request しない。
#: 1 回目の実行（2026-09-24 05:25 UTC 前後）で JPNEPUINDXM の recent 区間の request に対し、ALFRED が
#: 1988-06 以降の全系列を返した。**応答は保護暦日と forward の行を含み、CSV として parse された後に
#: `assert_response_within` が拒否した**（保存なし）。D-5 と同じ種類の露出であり、報告で D-M2 として開示する。
#: 同じ family の他の series（GBP / CAD / AUD / CHF）は同じ挙動の可能性があるので、**試さずに止める。**
ROUTE_NOT_REQUEST_BOUNDED: Final[dict[str, str]] = {
    "epu": "ALFRED が JPNEPUINDXM の cosd / coed を無視した（D-M2）。EPU family は request-level exclusion を保証できない",
}

VARIABLE_OF: Final[dict[str, str]] = {
    "cpi_yoy": "CPI_INFLATION_YOY",
    "cpi_index": "CPI_INDEX",
    "unemployment": "UNEMPLOYMENT_RATE",
    "policy_rate": "POLICY_RATE",
    "short_rate_3m": "SHORT_RATE_3M",
    "epu": "EPU_INDEX",
}

#: title の国名照合。変数の意味検証（mapping）とは別に、**どの国の系列か**を確かめる。
COUNTRY_WORDS: Final[dict[str, tuple[str, ...]]] = {
    "USD": ("united states", "u.s.", "us "),
    "JPY": ("japan",),
    "GBP": ("united kingdom", "u.k.", "uk "),
    "CAD": ("canada",),
    "AUD": ("australia",),
    "NZD": ("new zealand",),
    "CHF": ("switzerland",),
    "EUR": ("euro area", "europe"),
}


def _country_matches(currency: str, text: str, series_id: str) -> bool:
    lowered = f" {text.lower()} "
    if currency == "USD" and series_id in {"FEDFUNDS", "TB3MS", "USEPUINDXM"}:
        return True  # 米国の系列は title に国名を持たない
    return any(word in lowered for word in COUNTRY_WORDS[currency])


def _fetch_bounded(series_id: str, kind: str) -> tuple[pd.Series, dict[str, Any]]:
    request_policy.assert_provider_allowed("alfred")
    parts: list[pd.Series] = []
    meta: dict[str, Any] = {}
    urls: list[str] = []
    for first, last in request_policy.seen_request_windows(kind):
        start, end = request_policy.check_request(first, last, kind=kind)
        try:
            piece, meta = providers.alfred(series_id, opt_in_env=OPT_IN_ENV, first=first, last=last)
        except FetchError as error:
            if error.outcome == "PARSER_FAILURE":
                continue  # その区間に観測が無い
            raise
        request_policy.assert_response_within(piece.index, start, end, label=series_id)
        parts.append(piece)
        urls.append(meta["source_url"])
    if not parts:
        raise FetchError("SERIES_NOT_FOUND", f"{series_id}: どちらの区間にも観測が無い")
    series = pd.concat(parts).sort_index()
    series = series[~series.index.duplicated(keep="last")]
    return series, {**meta, "source_url": " | ".join(urls)}


def acquire_slot(slot: str, currency: str) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for series_id, kind in CANDIDATES[slot][currency]:
        started = pd.Timestamp.now(tz="UTC").isoformat()
        try:
            series, meta = _fetch_bounded(series_id, kind)
            evidence = f"{meta['title']} {meta['units']}"
            semantic = mapping.check_semantics(VARIABLE_OF[slot], evidence)
            if not _country_matches(currency, meta["title"], series_id):
                raise FetchError(
                    "SEMANTIC_MISMATCH",
                    f"{series_id}: title の国が {currency} と合わない — {meta['title'][:120]}",
                )
        except request_policy.ProviderIgnoredBoundError as error:
            attempts.append(
                {
                    "series_id": series_id,
                    "outcome": "PROVIDER_IGNORED_BOUND",
                    "error": str(error)[:240],
                    "at": started,
                }
            )
            return {
                "slot": slot,
                "currency": currency,
                "outcome": "PROVIDER_IGNORED_BOUND",
                "attempts": attempts,
            }
        except FetchError as error:
            attempts.append(
                {
                    "series_id": series_id,
                    "outcome": error.outcome,
                    "error": str(error)[:240],
                    "at": started,
                }
            )
            continue
        name = f"{slot}_{currency.lower()}"
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        frame = series.to_frame(name=name)
        frame.index.name = "date"
        frame.to_parquet(DATA_DIR / f"{name}.parquet")
        long_rows = int((series.index <= "2016-06-01").sum())
        return {
            "slot": slot,
            "currency": currency,
            "outcome": "OK",
            "series_id": series_id,
            "reference_period": kind,
            "official_title": meta["title"],
            "units": meta["units"],
            "frequency": meta["frequency"],
            "seasonal_adjustment": meta["seasonal_adjustment"],
            "semantic_check": semantic,
            "source_url": meta["source_url"],
            "metadata_url": meta["metadata_url"],
            "request_windows": [list(w) for w in request_policy.seen_request_windows(kind)],
            "coverage_first": series.index.min().date().isoformat(),
            "coverage_last": series.index.max().date().isoformat(),
            "rows_long_span": long_rows,
            "rows_recent_span": int(len(series) - long_rows),
            "content_hash": digest(frame.to_csv()),
            "revision": "CURRENT_VINTAGE_ONLY_REVISION_CAVEAT",
            "retrieval_timestamp_utc": started,
            "rejected_candidates": attempts,
        }
    return {"slot": slot, "currency": currency, "outcome": "NOT_MAPPED", "attempts": attempts}


def run() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for slot in CANDIDATES:
        if slot in ROUTE_NOT_REQUEST_BOUNDED:
            rows.extend(
                {
                    "slot": slot,
                    "currency": c,
                    "outcome": "ROUTE_NOT_REQUEST_BOUNDED",
                    "why": ROUTE_NOT_REQUEST_BOUNDED[slot],
                }
                for c in CANDIDATES[slot]
            )
            continue
        for currency in CANDIDATES[slot]:
            row = acquire_slot(slot, currency)
            rows.append(row)
            if row["outcome"] == "PROVIDER_IGNORED_BOUND":
                #: 同じ family の残りには request しない
                rows.extend(
                    {"slot": slot, "currency": c, "outcome": "NOT_REQUESTED_AFTER_IGNORED_BOUND"}
                    for c in list(CANDIDATES[slot])[list(CANDIDATES[slot]).index(currency) + 1 :]
                )
                break
    return {
        "cycle": "MECHANISM_REDESIGN_2026_09",
        "policy": "REQUEST_LEVEL_EXCLUSION_ONLY（data_access.request_policy）",
        "bulk_only_used": [],
        "route_not_request_bounded": ROUTE_NOT_REQUEST_BOUNDED,
        "incidents": {
            "D-M2_PROVIDER_IGNORED_BOUND": (
                "1 回目の取得で、JPNEPUINDXM の recent 区間（cosd=2021-05-01, coed=2025-11-01）の request に対し "
                "ALFRED が 1988-06 以降の全系列を返した。応答は保護暦日と forward の行を含み、CSV として parse された "
                "後に assert_response_within が拒否した（保存なし、計算なし）。その実行は例外で止まり、record は "
                "書かれていない。EPU family はそれ以後 request していない"
            ),
            "D-M1_METADATA_PAGE": (
                "ALFRED の series ページ（metadata）は見出しに最新の観測値を表示することがある。title / units / "
                "frequency / notes の label だけを読み、観測値は読まない"
            ),
            "RERUN": "この record は 3 回目の実行（EPU を止め、cpi_index を足した後）。1 回目は D-M2 で停止、2 回目の record は同一 session で置き換えた（未 commit）",
        },
        "finished_utc": dt.datetime.now(dt.UTC).isoformat(),
        "series": rows,
    }


def main() -> int:
    if RECORD.exists():
        #: 取得を再実行すると parquet が先に上書きされ、record の上書き拒否は後から起きる（Role 2 RF-5）
        raise SystemExit(f"{RECORD} は既にある。parquet を上書きする前に止める")
    payload = run()
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(RECORD, payload)
    for row in payload["series"]:
        print(
            row["slot"],
            row["currency"],
            row["outcome"],
            row.get("series_id"),
            row.get("coverage_first"),
            row.get("coverage_last"),
            file=sys.stderr,
        )
    print(json.dumps({"written": str(RECORD), "sha256": written}), file=sys.stderr)
    return 0


# ----------------------------------------------------------------------
# 追補（pre-alpha amendment）: BIS 政策金利を date-bounded な SDMX で取る
# ----------------------------------------------------------------------
AMENDMENT_RECORD: Final[Path] = (
    REPO_ROOT / "artifacts/research/mechanism_redesign/acquisition_amendment.json"
)

#: BIS WS_CBPOL の参照地域（euro area は XM）。
BIS_AREAS: Final[dict[str, str]] = {
    "USD": "US",
    "JPY": "JP",
    "GBP": "GB",
    "CAD": "CA",
    "AUD": "AU",
    "NZD": "NZ",
    "CHF": "CH",
    "EUR": "XM",
}
BIS_STRUCTURE_URL: Final[str] = "https://stats.bis.org/api/v2/structure/dataflow/BIS/WS_CBPOL/1.0"


def _bis_month(stamp: str) -> str:
    """request_policy が通した `YYYY-MM-DD`（月初）を BIS の `YYYY-MM` にする。"""
    day = request_policy.as_day(stamp, field="stamp")
    return f"{day.year:04d}-{day.month:02d}"


def acquire_bis_policy_rates() -> dict[str, Any]:
    """**`detail=dataonly`**: 観測値の列だけを返させる。

    属性列（COMPILATION など）は provider の注記で、**2026 年の政策決定の記述を含んでいた**（D-M3）。
    dataonly にすると属性列そのものが応答に入らない。意味の確認は dataflow の構造定義（観測値を含まない）で行う。
    """
    import io

    from scripts.research.data_access.fetch import fetch

    structure = providers._require(fetch(BIS_STRUCTURE_URL, opt_in_env=OPT_IN_ENV, expect="json"))
    flow = json.loads(structure.decode("utf-8"))["data"]["dataflows"][0]
    semantic = mapping.check_semantics(
        "POLICY_RATE", f"{flow.get('name', '')} {flow.get('description', '')}"
    )
    rows: list[dict[str, Any]] = []
    for currency, area in BIS_AREAS.items():
        parts: list[pd.Series] = []
        urls: list[str] = []
        for first, last in request_policy.seen_request_windows(request_policy.MONTH):
            start, end = request_policy.check_request(first, last, kind=request_policy.MONTH)
            url = (
                f"https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/M.{area}"
                f"?format=csv&startPeriod={_bis_month(first)}&endPeriod={_bis_month(last)}&detail=dataonly"
            )
            result = fetch(url, opt_in_env=OPT_IN_ENV, expect="csv")
            if result.outcome != "OK" and result.http_status == 404:
                continue  # その区間に観測が無い
            frame = pd.read_csv(io.BytesIO(providers._require(result)))
            if set(frame.columns) - {"FREQ", "REF_AREA", "TIME_PERIOD", "OBS_VALUE"}:
                raise AssertionError(f"{area}: dataonly なのに属性列が返った {list(frame.columns)}")
            stamps = pd.to_datetime(frame["TIME_PERIOD"] + "-01")
            series = pd.Series(frame["OBS_VALUE"].astype(float).to_numpy(), index=stamps).dropna()
            request_policy.assert_response_within(series.index, start, end, label=f"BIS {area}")
            parts.append(series)
            urls.append(url)
        if not parts:
            rows.append(
                {"slot": "policy_rate_bis", "currency": currency, "outcome": "SERIES_NOT_FOUND"}
            )
            continue
        series = pd.concat(parts).sort_index()
        name = f"policy_rate_bis_{currency.lower()}"
        frame = series.to_frame(name=name)
        frame.index.name = "date"
        frame.to_parquet(DATA_DIR / f"{name}.parquet")
        long_rows = int((series.index <= "2016-06-01").sum())
        rows.append(
            {
                "slot": "policy_rate_bis",
                "currency": currency,
                "outcome": "OK",
                "series_key": f"WS_CBPOL/M.{area}",
                "official_title": f"Central bank policy rates - {area} - Monthly - End of period（dataflow 構造定義と、事前の 1 回の probe の TITLE で確認）",
                "reference_period": request_policy.MONTH,
                "semantic_check": semantic,
                "source_url": " | ".join(urls),
                "metadata_url": BIS_STRUCTURE_URL,
                "coverage_first": series.index.min().date().isoformat(),
                "coverage_last": series.index.max().date().isoformat(),
                "rows_long_span": long_rows,
                "rows_recent_span": int(len(series) - long_rows),
                "content_hash": digest(frame.to_csv()),
                "revision": "政策金利の決定値。改訂無し",
            }
        )
    return {"cycle": "MECHANISM_REDESIGN_2026_09", "slot": "policy_rate_bis", "rows": rows}


AMENDMENT_INCIDENTS: Final[dict[str, str]] = {
    "D-M1_METADATA_PAGE": (
        "providers.alfred は window ごとに metadata page（alfred.stlouisfed.org/series?seid=…）を取得した。"
        "1 series あたり 2 回、実行 3 回で合計約 200 ページ。page 全体を decode して regex で走査しており、"
        "見出しの最新観測値（2026 年 = forward epoch の値）が**メモリ上で parse された**。抽出・保存はしていない。"
        "『観測値は読まない』という初版の記述は不正確で、正しくは『抽出・保存しない』"
    ),
    "D-M2_PROVIDER_IGNORED_BOUND": (
        "1 回目の実行で JPNEPUINDXM の recent request に対し ALFRED が 1988-06 以降の全系列を返した。"
        "providers._series が応答全体を parse して標準偏差まで計算した後に assert_response_within が拒否した"
        "（『計算なし』は厳密には誤り。保存は無し）。以後 EPU family には request していない"
    ),
    "D-M2b_EPU_USD_EUR_SAVED_IN_RUN_1": (
        "同じ 1 回目の実行で、EPU の USD / EUR は bound どおりに返り、epu_usd.parquet / epu_eur.parquet として"
        "保存された（保護 stamp は 0 件）。acquisition.json はこの 2 本を ROUTE_NOT_REQUEST_BOUNDED と記録しており、"
        "保存の事実が抜けていた。2 本は signal に使われておらず、この amendment で削除した"
    ),
    "D-M3_BIS_ATTRIBUTE_TEXT": (
        "BIS WS_CBPOL の probe 1 回（JP、recent 区間、属性付き）で、属性列 COMPILATION に 2026 年の政策決定の記述"
        "（forward epoch の内容）が含まれていた。**lead session がこれを表示して読んだ。** 保存も計算もしていない。"
        "本取得は detail=dataonly（観測値の列だけ）で行い、属性列は応答に入っていない"
    ),
    "RUNS_1_AND_2": (
        "1 回目（D-M2 で停止、record 無し）と 2 回目（EPU を止めた後、record は同一 session で置き換えた）は、"
        "CANDIDATES の全 series を同じ bound で request した。parquet は 3 回目が上書きした（未 commit の段階）。"
        "request の一覧は CANDIDATES と同じで、別の記録は残っていない"
    ),
}


def amend() -> int:
    """pre-alpha amendment の取得と記録。**既存の記録は上書きしない。**"""
    if AMENDMENT_RECORD.exists():
        raise SystemExit(f"{AMENDMENT_RECORD} は既にある。取得をやり直すなら別の record に書く")
    for stray in ("epu_usd", "epu_eur"):
        (DATA_DIR / f"{stray}.parquet").unlink(missing_ok=True)
    payload = acquire_bis_policy_rates()
    payload["incidents"] = AMENDMENT_INCIDENTS
    payload["deleted_files"] = ["epu_usd.parquet", "epu_eur.parquet"]
    payload["finished_utc"] = dt.datetime.now(dt.UTC).isoformat()
    written = write_provenance(AMENDMENT_RECORD, payload)
    print(json.dumps({"written": str(AMENDMENT_RECORD), "sha256": written}), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(amend() if "--amend" in sys.argv else main())
