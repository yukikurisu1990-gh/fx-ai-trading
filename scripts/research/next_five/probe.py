# ruff: noqa: E501 -- probe prose
"""新 5 本の **Stage 0 可用性 probe**（2026-09-22 裁定 §K の Stage 0）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**これは alpha ではない。** 測るのは「その series が無料で取れるか / どの期間を覆うか /
どの頻度か」だけで、signal も return も作らない。だから freeze の前に走らせてよい。

**network に出る条件は 2 つ揃ったときだけ。**

1. `NEXT_FIVE_PROBE_APPROVED=1`（`require_opt_in` が fetch のたびに確認）
2. この module を **script として実行**していること

`import` しただけでは何も起きない。opt-in を消す mutation が入っても、`_fetch` が
`require_opt_in` を毎回呼ぶので fetch 単位で止まる。curl 等への fallback は持たない。

**失敗の分類を混同しない**（前 cycle の教訓）。TLS 失敗・timeout・名前解決失敗は
**こちら側の環境**の話であって「provider にデータが無い」ではない。
S07 を「不達」で退場させかけた事故がこれである。
"""

from __future__ import annotations

import argparse
import io
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Final

import pandas as pd

from scripts.research.acquisition_safety import (
    HTTP_STATUS,
    NETWORK_FAILURES,
    OK,
    classify_failure,
    digest,
    require_opt_in,
    write_provenance,
)

OPT_IN_ENV: Final[str] = "NEXT_FIVE_PROBE_APPROVED"
OVERWRITE_ENV: Final[str] = "NEXT_FIVE_PROVENANCE_OVERWRITE_APPROVED"
USER_AGENT: Final[str] = "Mozilla/5.0 fx-ai-trading research probe"
TIMEOUT_SECONDS: Final[int] = 30
ATTEMPTS: Final[int] = 1
RETRY_SECONDS: Final[float] = 2.0

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORD: Final[Path] = REPO_ROOT / "artifacts/research/next_five/stage0_probe.json"

#: 候補 track ごとに、**どの series が取れれば成立するか**。
#: ここに書いた URL だけを叩く。probe は探索しない。
TARGETS: Final[dict[str, dict[str, Any]]] = {
    "S29": {
        "what": "実体貿易 flow（月次 貿易/経常収支）",
        "series": {
            "us_trade_balance": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BOPGSTB",
            "jp_trade_balance": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=XTNTVA01JPM664S",
            "gb_trade_balance": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=XTNTVA01GBM664S",
            "ca_trade_balance": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=XTNTVA01CAM664S",
            "au_trade_balance": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=XTNTVA01AUM664S",
            "nz_trade_balance": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=XTNTVA01NZM664S",
            "ch_trade_balance": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=XTNTVA01CHM664S",
            "ez_trade_balance": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=XTNTVA01EZM664S",
        },
        "minimum_for_viability": 5,
    },
    "S25": {
        "what": "中銀 balance sheet（週次〜月次）",
        "series": {
            "fed_total_assets": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=WALCL",
            "ecb_total_assets": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=ECBASSETSW",
            "boj_total_assets": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=JPNASSETS",
        },
        "minimum_for_viability": 3,
    },
    "S31": {
        "what": "公的外貨準備（月次）",
        "series": {
            "jp_reserves": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TRESEGJPM052N",
            "ch_reserves": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TRESEGCHM052N",
            "gb_reserves": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TRESEGGBM052N",
            "ca_reserves": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TRESEGCAM052N",
            "au_reserves": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=TRESEGAUM052N",
        },
        "minimum_for_viability": 4,
    },
    "S07": {
        "what": "信用 spread / funding stress（日次）",
        "series": {
            "us_hy_oas": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2",
            "us_ig_oas": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLC0A0CM",
            "ted_or_sofr": "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SOFR",
        },
        "minimum_for_viability": 1,
    },
    "S27": {
        "what": "中銀 communication テキスト archive",
        "series": {
            "fed_statements_index": "https://www.federalreserve.gov/json/ne-press.json",
            "ecb_statements_index": "https://www.ecb.europa.eu/press/pressconf/html/index.en.html",
            "boe_statements_index": "https://www.bankofengland.co.uk/news/statements",
        },
        "minimum_for_viability": 2,
        "extra_risk": "**時刻付きの過去分が機械取得できるか**が本質で、index が取れるだけでは足りない",
    },
}


#: **第 2 ラウンド。** FRED が到達しなかったので、**前 cycle で HTTP 200 が確認できた host**
#: に限定して直接経路を試す。series code は公開仕様からの推定を含むので、
#: 404 が返ることもある — それは「到達した上で無い」であり、timeout とは別の事実である。
DIRECT_TARGETS: Final[dict[str, dict[str, Any]]] = {
    "S25": {
        "what": "中銀 balance sheet（直接経路）",
        "series": {
            "snb_balance_sheet": "https://data.snb.ch/api/cube/snbbipo/data/csv/en",
            "ecb_balance_sheet": "https://data-api.ecb.europa.eu/service/data/ILM/W.U2.C.T000000.Z5.EUR?format=csvdata",
            "boe_balance_sheet": "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=04/Jan/1999&Dateto=26/Dec/2025&SeriesCodes=RPWB55A&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N",
            "boc_balance_sheet": "https://www.bankofcanada.ca/valet/observations/V36612/csv",
        },
        "minimum_for_viability": 3,
    },
    "S31": {
        "what": "公的外貨準備（直接経路）",
        "series": {
            "snb_reserves": "https://data.snb.ch/api/cube/snbdevbil/data/csv/en",
            "boe_reserves": "https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=04/Jan/1999&Dateto=26/Dec/2025&SeriesCodes=LPMB8LU&CSVF=TN&UsingCodes=Y&VPD=Y&VFD=N",
            "boc_reserves": "https://www.bankofcanada.ca/valet/observations/V122161/csv",
            "mof_jp_reserves": "https://www.mof.go.jp/english/policy/international_policy/reference/official_reserve_assets/data.csv",
        },
        "minimum_for_viability": 3,
    },
    "S29": {
        "what": "実体貿易 flow（直接経路）",
        "series": {
            "bundesbank_current_account": "https://api.statistiken.bundesbank.de/rest/data/BBDP1/M.DE.N.I8.S1.S1.T.B.CA._Z._Z._Z.EUR._T._X.N?format=csv",
            "ecb_current_account": "https://data-api.ecb.europa.eu/service/data/BP6/M.N.I9.W1.S1.S1.T.B.CA._Z._Z._Z.EUR._T._X.N?format=csvdata",
            "snb_current_account": "https://data.snb.ch/api/cube/aubesilm/data/csv/en",
            "census_us_trade": "https://www.census.gov/foreign-trade/balance/c0004.csv",
        },
        "minimum_for_viability": 3,
    },
    "S07": {
        "what": "信用 spread（直接経路の有無を確かめる）",
        "series": {
            "ust_yield_curve_proxy": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2024/all?type=daily_treasury_yield_curve&field_tdr_date_value=2024&page&_format=csv",
        },
        "minimum_for_viability": 1,
        "extra_risk": "**HY OAS の無料配信は実質 FRED 経由しかない。** ここで測れるのは代替が無いという事実だけである",
    },
}


def _fetch(url: str) -> bytes:
    """network へ出る唯一の場所。**fetch のたびに許可を確認する。** fallback は無い。"""
    last: BaseException | None = None
    for _ in range(ATTEMPTS):
        require_opt_in(OPT_IN_ENV, what="probe next-five public data availability")
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(
                request, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context()
            ) as response:
                return response.read()
        except urllib.error.HTTPError:
            raise
        except NETWORK_FAILURES as error:
            last = error
            time.sleep(RETRY_SECONDS)
    raise last if last is not None else RuntimeError(f"{url}: 取得できなかった")


def _describe_csv(payload: bytes) -> dict[str, Any]:
    """**中身は読むが、返すのは形だけ。** 値は返さない（signal を作らせない）。"""
    frame = pd.read_csv(io.StringIO(payload.decode("utf-8", errors="replace")))
    if frame.empty or frame.shape[1] < 2:
        return {"shape": list(frame.shape), "parsed": False}
    stamps = pd.to_datetime(frame.iloc[:, 0], errors="coerce").dropna()
    values = pd.to_numeric(frame.iloc[:, 1], errors="coerce")
    usable = values.notna()
    if stamps.empty:
        return {"shape": list(frame.shape), "parsed": False}
    spacing = stamps.diff().dt.days.median()
    return {
        "parsed": True,
        "rows": int(len(frame)),
        "usable_rows": int(usable.sum()),
        "first": str(stamps.min().date()),
        "last": str(stamps.max().date()),
        "median_spacing_days": None if pd.isna(spacing) else float(spacing),
        "frequency_guess": (
            "daily"
            if spacing is not None and not pd.isna(spacing) and spacing <= 5
            else "weekly"
            if spacing is not None and not pd.isna(spacing) and spacing <= 10
            else "monthly"
            if spacing is not None and not pd.isna(spacing) and spacing <= 40
            else "quarterly_or_slower"
        ),
    }


def probe_one(url: str) -> dict[str, Any]:
    started = pd.Timestamp.utcnow().isoformat()
    try:
        payload = _fetch(url)
    except Exception as error:  # noqa: BLE001 - 分類して記録するのが仕事である
        classification = classify_failure(error)
        return {
            "url": url,
            "retrieved_utc": started,
            "outcome": classification,
            "http_status": getattr(error, "code", None),
            "error": f"{type(error).__name__}: {error}"[:200],
            "reading": (
                "**これは『provider にデータが無い』ではない。**"
                if classification != HTTP_STATUS
                else "provider が返した status である"
            ),
        }
    text = payload.decode("utf-8", errors="replace")
    #: **200 が返っても data とは限らない。**
    #: BoE は存在しない series code に対して HTTP 200 で HTML のエラーページを返した。
    #: それを「到達 OK」と記録したので、ここで中身を見て弾く。
    looks_like_html = text.lstrip()[:200].lower().startswith(("<!doctype", "<html"))
    row: dict[str, Any] = {
        "url": url,
        "retrieved_utc": started,
        "outcome": "HTTP_200_BUT_NOT_DATA_HTML_PAGE" if looks_like_html else OK,
        "http_status": 200,
        "bytes": len(payload),
        "content_hash": digest(text),
    }
    if looks_like_html:
        row["reading"] = (
            "**200 だが data ではない。** 存在しない series を要求したときに "
            "エラーページが 200 で返ることがある。到達と取得は別の事実である"
        )
        return row
    if url.endswith(".csv") or "fredgraph.csv" in url or "format=csv" in url:
        try:
            row["coverage"] = _describe_csv(payload)
        except Exception as error:  # noqa: BLE001
            row["coverage"] = {"parsed": False, "error": f"{type(error).__name__}: {error}"[:150]}
    return row


def run(targets: dict[str, dict[str, Any]] | None = None, label: str = "fred") -> dict[str, Any]:
    results: dict[str, Any] = {}
    for track, spec in (targets or TARGETS).items():
        rows = {name: probe_one(url) for name, url in spec["series"].items()}
        reachable = [name for name, row in rows.items() if row["outcome"] == OK]
        results[track] = {
            "what": spec["what"],
            "series": rows,
            "reachable": sorted(reachable),
            "reachable_count": len(reachable),
            "minimum_for_viability": spec["minimum_for_viability"],
            "viable": len(reachable) >= spec["minimum_for_viability"],
        }
        if "extra_risk" in spec:
            results[track]["extra_risk"] = spec["extra_risk"]
    return {
        "cycle": "NEXT_FIVE_2026_09",
        "route": label,
        "stage": "STAGE_0_AVAILABILITY_ONLY_NO_SIGNAL_CONSTRUCTED",
        "authority": "2026-09-22 Human + ChatGPT 裁定 §K（Stage 0）",
        "finished_utc": pd.Timestamp.utcnow().isoformat(),
        "results": results,
        "viable_tracks": sorted(t for t, r in results.items() if r["viable"]),
        "blocked_tracks": sorted(t for t, r in results.items() if not r["viable"]),
        "note": (
            "**到達しなかったものを『データが無い』と書かない。** "
            "TLS / timeout / 名前解決の失敗はこちら側の環境の話であり、"
            "provider の可用性ではない。前 cycle で S07 をこの取り違えで退場させかけた"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="次 5 本の Stage 0 可用性 probe")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--route", choices=("fred", "direct"), default="fred")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    payload = run(DIRECT_TARGETS if args.route == "direct" else None, args.route)
    record = Path(args.out) if args.out else RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    written = write_provenance(
        record,
        payload,
        overwrite=args.overwrite,
        env_name=OVERWRITE_ENV if args.overwrite else None,
    )
    for track, row in payload["results"].items():
        print(
            f"{track}: {row['reachable_count']}/{len(row['series'])} 到達 viable={row['viable']}",
            file=sys.stderr,
        )
    print(
        json.dumps({k: payload[k] for k in ("viable_tracks", "blocked_tracks")}, ensure_ascii=False)
    )
    print(f"written: {record} sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    if not os.environ.get(OPT_IN_ENV):
        print(f"{OPT_IN_ENV}=1 が無いので何もしない", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main())
