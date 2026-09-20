# ruff: noqa: E501 -- probe prose
"""承認済み gated probe（2026-09-20）— S02 / S07 の availability を決着させる。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Authority: 2026-09-20 Human + ChatGPT 裁定 §2
（`docs/governance/m15_adjudication_2026_09_19_and_09_20.md`）。

**なぜ 2026-09-14 の probe を再実行しないのか。** あの script は失敗を
`f"{type(error).__name__}: {error}"` という 1 本の文字列に潰しており、
**TLS 検証の失敗と provider の不在を区別できない**。PR #489 の監査が見つけた誤読
（Bundesbank / SNB の TLS 失敗を「矛盾」と記録した）は、まさにその区別が記録に
無かったことから出ている。裁定 §2 は分類を必須にしたので、probe を作り直す。

**記録するもの**（裁定 §2 が名指しした 8 項目）: source・URL・parameters・
retrieval timestamp・HTTP result・hash・coverage・failure classification。

**やらないこと**: alpha 計算、FX return を読む signal test、protected span への request、
authenticated broker、paid source。ここは **metadata と availability だけ**を見る。

出力は**新しいファイル**に書く。2026-09-14 の記録は歴史であり、上書きしない。
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from scripts.research.acquisition_safety import (
    HTTP_STATUS,
    OK,
    classify_failure,
    digest,
    require_opt_in,
    write_provenance,
)

OPT_IN_ENV: Final[str] = "EDGE_SOURCES_PROBE_APPROVED"
USER_AGENT: Final[str] = "Mozilla/5.0 research-availability-check"
TIMEOUT_SECONDS: Final[int] = 30
READ_LIMIT: Final[int] = 400_000

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
RECORD_DIR: Final[Path] = REPO_ROOT / "artifacts/research/edge_sources"


def record_path(suffix: str = "") -> Path:
    """probe ごとに別ファイル。既存の記録は歴史であり、上書きしない。"""
    stem = "public_data_availability_2026_09_20"
    return RECORD_DIR / f"{stem}{suffix}.json"


#: S07 の生死を決める 1 本。2026-09-14 の記録は 200、PR #489 の round は不達と報告した。
S07_TARGETS: Final[dict[str, str]] = {
    "fred_series_page_BAMLH0A0HYM2": "https://fred.stlouisfed.org/series/BAMLH0A0HYM2",
    "fred_root": "https://fred.stlouisfed.org/",
}

#: S02 の長辺（10y）。3 publisher が CONFLICTED / UNVERIFIED のまま残っている。
S02_TARGETS: Final[dict[str, str]] = {
    "us_treasury_par_yield_2016": (
        "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
        "daily-treasury-rates.csv/2016/all?type=daily_treasury_yield_curve&field_tdr_date_value=2016&page&_format=csv"
    ),
    "bundesbank_10y_daily": (
        "https://api.statistiken.bundesbank.de/rest/download/BBSIS/D.I.ZAR.ZI.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A"
        "?format=csv&lang=en"
    ),
    "boc_valet_10y": "https://www.bankofcanada.ca/valet/observations/BD.CDN.10YR.DQ.YLD/json?recent=5",
    "snb_rendoblid": "https://data.snb.ch/api/cube/rendoblid/data/csv/en",
}

#: PR #489 が THIS_ROUND_ONLY とした 3 host。裏づけが無いままなので同じ probe で確認する。
UNCORROBORATED_TARGETS: Final[dict[str, str]] = {
    "cboe_vix_history": "https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX_History.csv",
    "eia_wti_daily": "https://www.eia.gov/dnav/pet/hist_xls/RWTCd.xls",
    "bis_policy_rates": "https://stats.bis.org/api/v2/data/dataflow/BIS/WS_CBPOL/1.0/D..?format=csv",
}

#: 初回 probe で 404 を返した 2 本の代替。404 は **provider が答えた**ということなので、
#: host が不達なのではなく series key が違う。正しい綴りを探すのは availability の一部。
ALTERNATE_TARGETS: Final[dict[str, str]] = {
    "bundesbank_10y_rest_data": (
        "https://api.statistiken.bundesbank.de/rest/data/BBSIS/"
        "D.I.ZAR.ZI.EUR.S1311.B.A604._Z.R.A.A._Z._Z.A?format=csv&lang=en"
    ),
    "bundesbank_umlaufsrendite": (
        "https://api.statistiken.bundesbank.de/rest/data/BBSIS/D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A"
        "?format=csv&lang=en"
    ),
    "ecb_yield_curve_10y": (
        "https://data-api.ecb.europa.eu/service/data/YC/"
        "B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y?format=csvdata&lastNObservations=5"
    ),
    "bis_policy_rates_v1": "https://stats.bis.org/api/v1/data/WS_CBPOL/D../all?format=csv",
    "bis_dataflow_root": "https://stats.bis.org/api/v2/structure/dataflow/BIS/all/latest",
}

#: 5 本目の枠を決めるために要る availability。S25（中銀 balance sheet）と
#: S26（TIC flow）は #484 以来一度も probe されていない。**結果を見る前に**
#: 実行可能性を確定させるための metadata probe であって、alpha は一切見ない。
SLOT_FIVE_TARGETS: Final[dict[str, str]] = {
    # S25 — central bank balance sheet / reserve flows
    "fed_h41_csv": "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H41&filetype=csv&label=include&layout=seriescolumn&from=01/01/1999&to=12/31/2016",
    "fed_h41_page": "https://www.federalreserve.gov/releases/h41/",
    "ecb_weekly_financial_statement": "https://data-api.ecb.europa.eu/service/data/ILM/W.U2.C.T000000.Z5.EUR?format=csvdata&lastNObservations=5",
    "boj_balance_sheet": "https://www.stat-search.boj.or.jp/index_en.html",
    "snb_balance_sheet": "https://data.snb.ch/api/cube/snbbipo/data/csv/en",
    # S26 — international capital flow (TIC)
    "tic_treasury_landing": "https://home.treasury.gov/data/treasury-international-capital-tic-system",
    "tic_slt_table": "https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/slt_globl.csv",
    "tic_holdings": "https://ticdata.treasury.gov/resource-center/data-chart-center/tic/Documents/mfh.txt",
}

#: S25 / S26 の初回 probe で landing page しか取れなかった分の代替 key。
#: 404 も「応答」なので、正しい綴りを探すのは availability 判定の一部である。
SLOT_FIVE_ALT_TARGETS: Final[dict[str, str]] = {
    # S25 — ECB total assets (ILM) のキー候補
    "ecb_ilm_total_assets_a": "https://data-api.ecb.europa.eu/service/data/ILM/W.U2.C.A050000.U2.EUR?format=csvdata&lastNObservations=3",
    "ecb_ilm_total_assets_b": "https://data-api.ecb.europa.eu/service/data/ILM/W.U2.C.T000000.U2.EUR?format=csvdata&lastNObservations=3",
    "ecb_bsi_total_assets": "https://data-api.ecb.europa.eu/service/data/BSI/M.U2.N.C.T00.A.1.Z5.0000.Z01.E?format=csvdata&lastNObservations=3",
    # S25 — Fed H.4.1 の DDP package
    "fed_h41_ddp_package": "https://www.federalreserve.gov/datadownload/Output.aspx?rel=H41&series=c7b3b0b0e1a1b7b1&lastobs=5&from=&to=&filetype=csv&label=include&layout=seriescolumn",
    "fed_h41_txt_current": "https://www.federalreserve.gov/releases/h41/current/h41.htm",
    # S26 — TIC のファイル候補
    "tic_slt_publish": "https://ticdata.treasury.gov/Publish/slt_globl.csv",
    "tic_s1_publish": "https://ticdata.treasury.gov/Publish/s1_globl.csv",
    "tic_shla": "https://ticdata.treasury.gov/Publish/shla2023r.csv",
}

TARGET_GROUPS: Final[dict[str, dict[str, str]]] = {
    "S07_credit_spread": S07_TARGETS,
    "S02_curve_long_leg": S02_TARGETS,
    "uncorroborated_this_round_only": UNCORROBORATED_TARGETS,
}


def probe(url: str) -> dict[str, Any]:
    """1 本の URL を metadata として叩く。**失敗は分類して記録する。**"""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    parameters = {
        "timeout_seconds": TIMEOUT_SECONDS,
        "read_limit_bytes": READ_LIMIT,
        "user_agent": USER_AGENT,
        "method": "GET",
        "tls": "ssl.create_default_context()",
    }
    started = datetime.now(UTC).isoformat()
    try:
        with urllib.request.urlopen(
            request, timeout=TIMEOUT_SECONDS, context=ssl.create_default_context()
        ) as response:
            body = response.read(READ_LIMIT)
            return {
                "url": url,
                "parameters": parameters,
                "retrieved_utc": started,
                "http_status": response.status,
                "result": OK,
                "failure_classification": None,
                "bytes_read": len(body),
                "sha256_of_read_bytes": digest(body),
                "first_line": body.decode("utf-8", errors="replace").splitlines()[0][:200]
                if body
                else "",
            }
    except urllib.error.HTTPError as error:
        #: provider が返した status。これは相手の答えであって、こちらの環境の話ではない。
        return {
            "url": url,
            "parameters": parameters,
            "retrieved_utc": started,
            "http_status": error.code,
            "result": HTTP_STATUS,
            "failure_classification": HTTP_STATUS,
            "bytes_read": 0,
            "sha256_of_read_bytes": None,
            "detail": f"{type(error).__name__}: {error}"[:300],
        }
    except Exception as error:  # noqa: BLE001 - 分類して記録するのが目的
        return {
            "url": url,
            "parameters": parameters,
            "retrieved_utc": started,
            "http_status": None,
            "result": classify_failure(error),
            "failure_classification": classify_failure(error),
            "bytes_read": 0,
            "sha256_of_read_bytes": None,
            "detail": f"{type(error).__name__}: {error}"[:300],
        }


def run(groups: dict[str, dict[str, str]] | None = None) -> dict[str, Any]:
    require_opt_in(OPT_IN_ENV, what="probe public data availability")
    groups = TARGET_GROUPS if groups is None else groups
    record: dict[str, Any] = {
        "authority": "Human + ChatGPT adjudication 2026-09-20 section 2",
        "scope": "metadata / availability / coverage only — no alpha, no FX return, no protected span",
        "started_utc": datetime.now(UTC).isoformat(),
        "groups": {},
    }
    for group, targets in groups.items():
        record["groups"][group] = {name: probe(url) for name, url in targets.items()}
    record["finished_utc"] = datetime.now(UTC).isoformat()
    return record


def main() -> int:
    if os.environ.get(OPT_IN_ENV) != "1":
        print(f"refused: set {OPT_IN_ENV}=1 only under a recorded approval to run this probe")
        return 2
    if "--slot-five-alt" in sys.argv:
        groups, suffix = {"slot_five_alt": SLOT_FIVE_ALT_TARGETS}, "_slot_five_alt"
    elif "--slot-five" in sys.argv:
        groups, suffix = {"slot_five": SLOT_FIVE_TARGETS}, "_slot_five"
    elif "--alternates" in sys.argv:
        groups, suffix = {"alternates": ALTERNATE_TARGETS}, "_alternates"
    else:
        groups, suffix = TARGET_GROUPS, ""
    path = record_path(suffix)
    record = run(groups)
    written = write_provenance(path, record)
    #: ensure_ascii=True: この端末は cp932 で em dash を印字できない。ファイル側は
    #: utf-8 で書かれているので、読めないのは stdout だけ。
    print(json.dumps(record, indent=1, ensure_ascii=True))
    print(f"written: {path}  sha256={written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
