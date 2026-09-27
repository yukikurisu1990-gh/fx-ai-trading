# ruff: noqa: E501 -- ledger prose
"""5 つの抽出 part を 1 つの evidence ledger にまとめる（2026-09-28 裁定 §5–§7）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

part（`artifacts/research/programme/parts/ledger_{A..E}.json`）は、過去の artifact と
結果文書から**値を読み取っただけ**のもの（抽出 script は `scripts/research/programme/extract/`）。
ここでは数値を一切作らず、次のことだけをする:

- 全行が schema の全 key を持ち、`track_id` が重複しないことを確かめる。
- ラベルを揃える（下の `LABEL_NORMALISATIONS`。**数値には触れない**）。
- 解釈用の列を足す: `ledger_part`・`era`・`mechanism_id`・`sharpe_comparable`。

過去の記録は書き換えない。ledger は interpretation layer である。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

from scripts.research.acquisition_safety import write_provenance

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
PARTS_DIR: Final[Path] = REPO_ROOT / "artifacts/research/programme/parts"
LEDGER: Final[Path] = REPO_ROOT / "artifacts/research/programme/ledger.json"
PARTS: Final[tuple[str, ...]] = ("A", "B", "C", "D", "E")

SCHEMA_KEYS: Final[tuple[str, ...]] = (
    "track_id", "cycle", "pr", "family", "hypothesis", "mechanism", "information_source",
    "price_only", "book_type", "span_label", "span_dates", "calendar_years", "effective_n",
    "event_count", "gross_annual_return", "gross_sharpe", "tc_adjusted_annual_return",
    "tc_adjusted_sharpe", "financing_included", "financing_type", "turnover", "annual_cost",
    "ic", "incremental_ic", "null_percentile", "p_value", "stability", "loo_worst",
    "concentration_top10", "max_dd", "result_status", "is_primary", "preregistered",
    "post_result_correction", "invalid", "variant_type", "variant_of",
    "protected_data_caveat", "closure_scope", "source", "notes",
)  # fmt: skip

PART_SCOPE: Final[dict[str, str]] = {
    "A": "Exploratory Round 1 / Round 2 / supplemental replication / momentum mirror（M15 archive、PR #464–#470）",
    "B": "Economic edge / exogenous directional / expectation benchmark / Track 2（PR #471–#477）",
    "C": "Track 1 portfolio / model learning / T-R / T-R2 / T-V（PR #478–#488）",
    "D": "Top-Five / next-five / mechanism redesign / USD-factor financing（PR #490–#495）",
    "E": "pre-R1 era（Phase 9–29、ML Step 4。別の harness、Sharpe の定義が揃っていない）",
}

#: **ラベルだけ**を揃える。数値は変えない。各項目に理由を書く。
LABEL_NORMALISATIONS: Final[tuple[dict[str, str], ...]] = (
    {
        "field": "financing_included",
        "from": "OTHER",
        "to": "APPROXIMATE_CARRY_AND_MARKUP",
        "when_financing_type_contains": "APPROXIMATE_RESEARCH_FINANCING",
        "why": "#495 の total 行は近似の政策金利 carry と仮定 markup を含む。抽出時に OTHER と書かれたものを、他 cycle と同じ語彙に揃える",
    },
)

_SPAN_SUFFIX: Final[re.Pattern[str]] = re.compile(
    r"_(long|recent|p2123|p2325|dev25|run2_INVALID|exfin|total)$"
)


def mechanism_id(row: dict[str, Any]) -> str:
    """同じ mechanism の span 違い・再実行を 1 つにまとめる鍵（縮小推定で二重に数えないため）。"""
    base = row["track_id"]
    for _ in range(3):
        base = _SPAN_SUFFIX.sub("", base)
    return base


def _era(part: str) -> str:
    return "PRE_R1_LEGACY_HARNESS" if part == "E" else "POST_R1_PROGRAMME"


MECHANISM_REDESIGN_RESULTS: Final[Path] = (
    REPO_ROOT / "artifacts/research/mechanism_redesign/development.json"
)
_RATE_SOURCE: Final[re.Pattern[str]] = re.compile(
    r"policy[- ]rate|interbank|yield|OIS|money[- ]market", re.IGNORECASE
)
_RATE_FINANCING: Final[frozenset[str]] = frozenset(
    {"APPROXIMATE_CARRY_AND_MARKUP", "RESEARCH_CARRY_POLICY_RATES"}
)
#: judged P&L が政策金利の carry accrual を含む cycle（mechanism redesign は全 track が BIS 政策金利の carry を
#: judged P&L に入れた。ledger の `financing_included` は spot-only の値を指すので NONE になっている）。
_RATE_ACCOUNTING_CYCLES: Final[frozenset[str]] = frozenset({"mechanism redesign"})


def _judged_net_sharpe(row: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> float | None:
    """近似 financing（carry + 仮定 markup）込みの net Sharpe。記録がある行だけ。"""
    if row.get("financing_included") == "APPROXIMATE_CARRY_AND_MARKUP":
        return row.get("tc_adjusted_sharpe")
    if row.get("cycle") in _RATE_ACCOUNTING_CYCLES and not row.get("invalid"):
        results = json.loads(MECHANISM_REDESIGN_RESULTS.read_text(encoding="utf-8"))["results"]
        key = row["track_id"].removeprefix("MR_")
        metrics = results.get(key, {}).get("metrics") or {}
        value = metrics.get("net_sharpe")
        return None if value is None else float(value)
    return None


def _sharpe_ex_financing(row: dict[str, Any], by_id: dict[str, dict[str, Any]]) -> float | None:
    """transaction cost 後・financing 抜きの Sharpe（全分析で 1 つの定義に揃えるため）。"""
    financing = row.get("financing_included")
    if financing in (None, "NONE"):
        return row.get("tc_adjusted_sharpe")
    if financing == "APPROXIMATE_CARRY_AND_MARKUP" and row["track_id"].endswith("_total"):
        twin = by_id.get(row["track_id"].removesuffix("_total") + "_exfin")
        return None if twin is None else twin.get("tc_adjusted_sharpe")
    return None


#: 政策金利の決定・surprise・中銀声明の tone も金利の情報（D-M3 は BoJ の政策決定を読んだ事故）
_RATE_TRACK: Final[re.Pattern[str]] = re.compile(r"policy_rate|statement text", re.IGNORECASE)


def _rate_exposure(row: dict[str, Any]) -> bool:
    """signal か judged P&L が金利（政策金利・短期金利・利回り・政策決定）を使う（D-M3 の範囲の判定に使う）。"""
    return (
        bool(_RATE_SOURCE.search(str(row.get("information_source") or "")))
        or bool(_RATE_TRACK.search(f"{row['track_id']} {row.get('information_source') or ''}"))
        or row.get("financing_included") in _RATE_FINANCING
        or row.get("cycle") in _RATE_ACCOUNTING_CYCLES
    )


def _null_stats_basis(row: dict[str, Any]) -> str:
    if row.get("cycle") in _RATE_ACCOUNTING_CYCLES:
        return "JUDGED_PNL_SPOT_PLUS_CARRY_MINUS_SPREAD_MINUS_ASSUMED_MARKUP"
    if row.get("financing_included") == "APPROXIMATE_CARRY_AND_MARKUP":
        return "TOTAL_WITH_APPROXIMATE_RESEARCH_FINANCING_CENTRAL_CELL"
    return "AS_RECORDED_FOR_THE_ROW"


def _effective_n_kind(row: dict[str, Any]) -> str | None:
    if row.get("effective_n") is None:
        return None
    if "distinct_signal_states" in str(row.get("notes") or ""):
        return "DISTINCT_SIGNAL_STATES_NOT_EFFECTIVE_N"
    return "EFFECTIVE_INDEPENDENT_OBSERVATIONS"


def _annual_cost_unit(part: str, row: dict[str, Any]) -> str | None:
    if row.get("annual_cost") is None:
        return None
    if row["track_id"].startswith("ML_"):
        return "BP_PER_YEAR"
    return "FRACTION_PER_YEAR" if part in {"C", "D"} else "SEE_NOTES"


def load_parts() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for part in PARTS:
        path = PARTS_DIR / f"ledger_{part}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        part_rows = data["rows"] if isinstance(data, dict) else data
        for row in part_rows:
            missing = [k for k in SCHEMA_KEYS if k not in row]
            if missing:
                raise ValueError(f"{part}:{row.get('track_id')} missing keys {missing}")
            row = dict(row)
            for rule in LABEL_NORMALISATIONS:
                if row.get(rule["field"]) == rule["from"] and rule[
                    "when_financing_type_contains"
                ] in str(row.get("financing_type") or ""):
                    row[rule["field"]] = rule["to"]
            row["ledger_part"] = part
            row["era"] = _era(part)
            row["mechanism_id"] = mechanism_id(row)
            rows.append(row)
    ids = [r["track_id"] for r in rows]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate track_id: {duplicates}")
    by_id = {r["track_id"]: r for r in rows}
    for row in rows:
        part = row["ledger_part"]
        row["sharpe_ex_financing"] = None if part == "E" else _sharpe_ex_financing(row, by_id)
        row["judged_net_sharpe_incl_approx_financing"] = _judged_net_sharpe(row, by_id)
        row["null_stats_basis"] = _null_stats_basis(row)
        row["rate_exposure"] = _rate_exposure(row)
        row["effective_n_kind"] = _effective_n_kind(row)
        row["annual_cost_unit"] = _annual_cost_unit(part, row)
        row["annual_cost_includes_assumed_markup"] = (
            row.get("financing_included") == "APPROXIMATE_CARRY_AND_MARKUP"
        )
        #: 年率・日次 book の Sharpe（financing 抜き）で年数の記録があるもの。legacy harness と bar 単位の値は入れない。
        row["sharpe_comparable"] = (
            row["sharpe_ex_financing"] is not None
            and row.get("calendar_years") is not None
            and float(row["calendar_years"]) > 0
        )
    return rows


def build() -> dict[str, Any]:
    rows = load_parts()
    return {
        "status": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "kind": "PROGRAMME_EVIDENCE_LEDGER_INTERPRETATION_LAYER",
        "history_not_rewritten": True,
        "numbers_not_inferred": "全数値は part の source 欄が指す artifact / 文書から読んだもの。記録が無いものは null",
        "net_terminology": {
            "NONE": "NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING（過去の『net』の大半）",
            "APPROXIMATE_CARRY_AND_MARKUP": "NET_INCLUDING_APPROXIMATE_INTEREST_DIFFERENTIAL_AND_ASSUMED_MARKUP（APPROXIMATE_RESEARCH_FINANCING、実際の broker financing ではない）",
            "RESEARCH_CARRY_POLICY_RATES": "政策金利差の research carry、broker markup なし（#471）",
            "every_row": "FULL_RETAIL_NET_UNKNOWN",
        },
        "derived_columns": {
            "sharpe_ex_financing": "transaction cost 後・financing 抜きの Sharpe。financing NONE の行は tc_adjusted_sharpe、#495 の total 行は対の _exfin 行の値。pooling は全てこの 1 つの定義で行う",
            "judged_net_sharpe_incl_approx_financing": "近似 carry + 仮定 markup 込みの net（mechanism redesign の judged net は artifact の metrics.net_sharpe から読む）",
            "null_stats_basis": "null percentile / p / LOO / 集中度 / DD がどの P&L で測られたか（mechanism redesign は judged P&L）",
            "rate_exposure": "signal か judged P&L が金利を使う（D-M3 の範囲）",
            "effective_n_kind": "effective_n の意味（Top-Five の値は distinct signal states で有効標本数ではない）",
            "annual_cost_unit": "model learning の行は bp/年、C・D の他の行は年率の割合",
        },
        "part_scope": PART_SCOPE,
        "label_normalisations": LABEL_NORMALISATIONS,
        "rows": rows,
    }


def main() -> None:
    digest = write_provenance(LEDGER, build(), overwrite=True)
    print(f"wrote {LEDGER} sha256={digest}")


if __name__ == "__main__":
    main()
