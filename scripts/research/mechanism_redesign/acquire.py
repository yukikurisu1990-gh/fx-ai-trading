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


if __name__ == "__main__":
    raise SystemExit(main())
