# ruff: noqa: E501 -- research prose
"""D2 の机上の経済性（D0 の事前登録 §6・§7 の方法）。価格の系列を読まない。

入力:
- 原典の公表値（Mueller, Tahbaz-Salehi, Vedolin, J. Finance 72(3) 2017。本文と表から確認した値。下の定数）
- 現代の retail の cost: `artifacts/research/fxid_cycle1/cycle1_run2.json` の時刻ごとの spread の平均（commit 済みの集計の記録）

候補は D1 を通った 1 つの family（中央銀行の発表の日の不確実性の premium。FOMC と BoJ の 2 つの窓）。
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Final

REPO: Final[Path] = Path(__file__).resolve().parents[3]
COST_RECORD: Final[Path] = REPO / "artifacts/research/fxid_cycle1/cycle1_run2.json"
RECORD: Final[Path] = REPO / "artifacts/research/fx_component_discovery/d2_desk.json"
SLIPPAGE_BP: Final[float] = 0.5
Z_REQUIRED: Final[float] = 1.6449 + 0.8416  # 片側 5%、検出力 80%
#: 当日決済の窓（ET）: 入りは rollover（17 時台）の後の 18 時台、出は 16 時台（16:45）
ENTRY_HOUR: Final[str] = "18"
EXIT_HOUR: Final[str] = "16"

#: 原典の値（MTV 2017。本文の文で確認）
SOURCE: Final[dict[str, dict[str, Any]]] = {
    "FOMC": {
        "pairs": ["EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD", "USD_CAD", "USD_CHF", "USD_JPY"],
        "gross_event_bp": 10.77,  # dol、発表の日の 4pm→4pm（Table II の本文）
        "diff_event_bp": 10.30,  # 発表の日 − 他の日（本文）
        "annual_sharpe_gross": 0.508,  # dol（本文: 0.51）。年 8 回で年率化
        "events_per_year_source": 8.0,
        "events_per_year_now": 8.0,
        "net_sharpe_interbank": 0.377,  # Table X（interbank の bid / ask の後）
        "sample": "1994-01 … 2013-12、160 回",
        "replication": "未確認（Lin, Taylor, Wang, Xu 2025 は abstract のみ）。Lucca & Moench（2015）は主要通貨の pre-FOMC の異常な return を否定（Table 9、本文で確認）",
    },
    "BoJ": {
        "pairs": ["AUD_JPY", "NZD_JPY", "GBP_JPY"],  # 高金利通貨 対 JPY（pf3 の代理）
        "gross_event_bp": 17.59,  # pf3、発表の日（Table VIII の本文）
        "diff_event_bp": 14.77,  # 発表の日 − 他の日（本文）
        "annual_sharpe_gross": 1.32,  # pf3（本文、gross、cost の報告なし）
        "events_per_year_source": 232 / 16,  # 1998–2013 で 232 回
        "events_per_year_now": 8.0,  # 2016 年以降の金融政策決定会合
        "net_sharpe_interbank": None,
        "sample": "1998 … 2013、232 回",
        "replication": "未確認",
    },
}
#: D0 §6 の scenario（固定）
DECAY: Final[dict[str, float]] = {"Optimistic": 0.0, "Base": 0.5, "Stress": 0.7}
COST_MULT: Final[dict[str, float]] = {"Optimistic": 1.0, "Base": 1.0, "Stress": 1.5}
#: 検証に使える非 fresh・文献の sample の外の年数（2014-01 … 2016-05 と seen 2021-04 … 2025-12）
AVAILABLE_YEARS: Final[float] = 2.4 + 4.7


def retail_round_trip_bp(pairs: list[str]) -> dict[str, float]:
    rec = json.loads(COST_RECORD.read_text(encoding="utf-8"))
    out = {}
    for p in pairs:
        h = rec["r_a2"]["per_pair"][p]["hourly_ny"]
        out[p] = (
            h[ENTRY_HOUR]["spread_bp_mean"] + h[EXIT_HOUR]["spread_bp_mean"]
        ) / 2 + SLIPPAGE_BP
    return out


def desk(name: str) -> dict[str, Any]:
    src = SOURCE[name]
    costs = retail_round_trip_bp(src["pairs"])
    cost = sum(costs.values()) / len(costs)
    per_event_ir_gross = src["annual_sharpe_gross"] / math.sqrt(src["events_per_year_source"])
    sigma = src["gross_event_bp"] / per_event_ir_gross
    rows = {}
    for sc in DECAY:
        # Optimistic は発表の日の全体の return、Base / Stress は発表の日 − 他の日（carry など毎日の部分を除く）
        gross = src["gross_event_bp"] if sc == "Optimistic" else src["diff_event_bp"]
        gross *= 1 - DECAY[sc]
        net = gross - COST_MULT[sc] * cost
        ir = net / sigma
        sharpe = ir * math.sqrt(src["events_per_year_now"])
        years = (Z_REQUIRED / sharpe) ** 2 if sharpe > 0 else math.inf
        rows[sc] = {
            "gross_event_bp": round(gross, 3),
            "retail_cost_bp": round(COST_MULT[sc] * cost, 3),
            "gross_over_cost": round(gross / (COST_MULT[sc] * cost), 2),
            "net_event_bp": round(net, 3),
            "annual_net_sharpe": round(sharpe, 3),
            "years_to_detect_80pct": None if math.isinf(years) else round(years, 1),
            "K1_cost_ge_gross": gross <= COST_MULT[sc] * cost,
            "K8_years_exceed_available": (math.isinf(years) or years > AVAILABLE_YEARS),
        }
    return {
        "pairs": src["pairs"],
        "retail_round_trip_bp_by_pair": {k: round(v, 3) for k, v in costs.items()},
        "retail_round_trip_bp_mean": round(cost, 3),
        "sigma_per_event_bp": round(sigma, 1),
        "sample": src["sample"],
        "replication": src["replication"],
        "scenarios": rows,
    }


def compute() -> dict[str, Any]:
    out = {name: desk(name) for name in SOURCE}
    # family 全体（FOMC と BoJ を独立と仮定した合成の上限）
    fam = {}
    for sc in DECAY:
        s = [max(out[n]["scenarios"][sc]["annual_net_sharpe"], 0.0) for n in SOURCE]
        comb = math.sqrt(sum(x * x for x in s))
        years = (Z_REQUIRED / comb) ** 2 if comb > 0 else math.inf
        fam[sc] = {
            "annual_net_sharpe_combined_independent": round(comb, 3),
            "years_to_detect_80pct": None if math.isinf(years) else round(years, 1),
            "K8": math.isinf(years) or years > AVAILABLE_YEARS,
        }
    out["family_CB_ANNOUNCEMENT_DAY_UNCERTAINTY_PREMIUM"] = fam
    out["available_validation_years"] = AVAILABLE_YEARS
    out["cost_record_sha256"] = hashlib.sha256(
        COST_RECORD.read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    return out


def main() -> int:
    if RECORD.exists():
        raise SystemExit(f"{RECORD} は既にある。上書きしない")
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(compute(), ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    RECORD.write_bytes(raw)
    print(hashlib.sha256(raw).hexdigest())
    return 0


if __name__ == "__main__":
    sys.exit(main())
