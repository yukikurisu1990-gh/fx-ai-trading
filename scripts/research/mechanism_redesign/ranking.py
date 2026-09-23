# ruff: noqa: E501 -- ranking prose
"""prior-overlap audit と signal-blind ranking（2026-09-24 裁定 §14–§21）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**ranking は 2 段で、どちらも return を見ない。**

1. **prior score**（裁定 §18 の概念式）— universe の 1〜5 の判断を掛け算・割り算する。
   判断であって測定ではないので、**順位の近いものの差には意味が無い**。
2. **signal-blind feasibility**（`feasibility.py`）— Stage 0 で取得した入力だけから
   coverage・持続性・turnover の見込み・検出下限・cost の算術を出し、1 の shortlist を
   実行可能性で篩う。

overlap audit は、裁定 §14 の閉じた family を **名前ではなく情報集合と定式** で照合する。
§15 に従い、閉じるのは測定した specific な formulation までで、family 全体は閉じない。
"""

from __future__ import annotations

import math
from typing import Any, Final

from scripts.research.mechanism_redesign import universe

#: 裁定 §14 の閉じた family と、それを測った場所。
CLOSED_FAMILIES: Final[dict[str, str]] = {
    "multi_day_reversal": "Round 2 / 補足再現で FAILED、MULTI_DAY_REVERSAL_FAMILY_DROPPED",
    "mirror_momentum": "fresh exploratory history で UNRESOLVED、family は dropped",
    "h003_relative_strength": "H-003 系、T4（S10）でも NOT_SUPPORTED",
    "simple_htf_sign_conditioning": "HTF sign 系",
    "simple_daily_public_yield_repricing": "T-R（S01、PR #485）",
    "simple_reer_valuation": "T-V（S13、PR #486–#488）",
    "top_five_mechanisms": "T1 VIX shock / T2 商品交易条件 / T3 曲線形状 / T4 通貨伝播 / T5 TIC flow（PR #490）",
    "tic_flow_formulation": "T5 で観測済みの定式",
    "cot_rename": "S19",
    "clock_fix_rename": "clock_flow family",
    "track1_linear_continuous_currency_model": "Track 1（PR #481/#482）",
    "next_five_u1_u5": "U1 貿易収支 / U2 中銀 balance sheet / U3 声明 tone / U4 外貨準備 / U5 HY OAS（PR #493）",
}

#: 候補ごとの overlap 判定。**名前ではなく、情報集合と定式で照合した結果。**
OVERLAP_AUDIT: Final[dict[str, dict[str, str]]] = {
    "M01": {
        "verdict": "ELIGIBLE",
        "closest": "S23 / carry / S01",
        "why": "入力に市場金利を使わない。gap は水準でも変化でもない別の量",
    },
    "M02": {
        "verdict": "ELIGIBLE_DATA_LIMITED",
        "closest": "simple_daily_public_yield_repricing",
        "why": "2 年金利を単独で使わない限り rename ではない。無料では breadth 3",
    },
    "M03": {
        "verdict": "EXCLUDED_NEAR_RENAME",
        "closest": "top_five_mechanisms（T3 曲線形状）",
        "why": "同じ 2 本の金利の状態分類で、情報集合が T3 と同じ",
    },
    "M04": {
        "verdict": "EXCLUDED_RENAME",
        "closest": "simple_daily_public_yield_repricing",
        "why": "満期を替えただけ",
    },
    "M05": {
        "verdict": "EXCLUDED_RENAME",
        "closest": "top_five_mechanisms（T1 VIX shock）/ next_five_u1_u5（U5）",
        "why": "同じ risk-on/off 軸",
    },
    "M06": {
        "verdict": "EXCLUDED_RENAME",
        "closest": "h003_relative_strength / top_five_mechanisms（T4）",
        "why": "同じ伝播 mechanism",
    },
    "M07": {
        "verdict": "EXCLUDED_DATA_OR_RENAME",
        "closest": "clock_fix_rename",
        "why": "無料版は FX 価格だけになり clock/fix と同型。有料 intraday が要る",
    },
    "M08": {
        "verdict": "EXCLUDED_BULK_ONLY",
        "closest": "tic_flow_formulation",
        "why": "財務省は一括 CSV のみ（D-5 policy で取得しない）。breadth 1 で T5 と同型",
    },
    "M09": {
        "verdict": "ELIGIBLE_BREADTH_ONE",
        "closest": "tic_flow_formulation",
        "why": "データは独立だが breadth 1。最低 3 通貨の規則を満たさない",
    },
    "M10": {"verdict": "ELIGIBLE", "closest": "（無し）", "why": "取引費用の状態は未使用の観測量"},
    "M11": {
        "verdict": "ELIGIBLE_WITH_RENAME_GATE",
        "closest": "next_five_u1_u5（U1）",
        "why": "貿易収支を入れないことで U1 の救済にしない。U1 score との相関を rename gate で測る",
    },
    "M12": {"verdict": "EXCLUDED_PAID", "closest": "—", "why": "G10 の予測分散は有料"},
    "M13": {
        "verdict": "EXCLUDED_NEAR_RENAME",
        "closest": "S24 / top_five_mechanisms（T1）",
        "why": "vol timing と risk beta は閉じた 2 つの交差",
    },
    "M14": {
        "verdict": "EXCLUDED_NEAR_RENAME",
        "closest": "next_five_u1_u5（U5）",
        "why": "funding stress 軸は U5 と同じ",
    },
    "M15": {
        "verdict": "ELIGIBLE",
        "closest": "cross-sectional carry（#471）",
        "why": "target がドル factor。相対 book はこれを捨てていた（ドル軸を測った T5 は TIC flow で、金利の情報ではない）",
    },
    "M16": {
        "verdict": "ELIGIBLE_WITH_RENAME_GATE",
        "closest": "M11",
        "why": "入力を M11 と共有。M11 の USD 成分との重なりを測る",
    },
    "M17": {
        "verdict": "ELIGIBLE",
        "closest": "next_five_u1_u5（U3）",
        "why": "新聞全体の不確実性で、中銀の文書 tone とは情報源が違う",
    },
    "M18": {
        "verdict": "ELIGIBLE_DATA_BURDEN",
        "closest": "M11",
        "why": "point-in-time の再構成が重い。現行 vintage は look-ahead を含む",
    },
    "M19": {"verdict": "EXCLUDED_CLOSED", "closest": "S28", "why": "閉鎖済み"},
    "M20": {
        "verdict": "EXCLUDED_NEAR_RENAME",
        "closest": "top_five_mechanisms（T2）",
        "why": "交易条件の別データ",
    },
    "M21": {
        "verdict": "EXCLUDED_NEAR_RENAME",
        "closest": "C01 / H-019",
        "why": "決定の累積は C01 の情報集合の再集計",
    },
    "M22": {
        "verdict": "EXCLUDED_OVERFIT",
        "closest": "clock_fix_rename / S21",
        "why": "event 数が span ごとに 5〜17",
    },
    "M23": {
        "verdict": "EXCLUDED_SIGN_UNDEFINED",
        "closest": "—",
        "why": "符号の理論が定まらない。事前に凍結できない",
    },
    "M24": {"verdict": "EXCLUDED_PAID", "closest": "S20", "why": "有料"},
    "M25": {
        "verdict": "EXCLUDED_PAID",
        "closest": "simple_daily_public_yield_repricing",
        "why": "有料。定式次第で S01 の rename",
    },
    "M26": {"verdict": "EXCLUDED_PAID", "closest": "S22", "why": "有料"},
    "M27": {"verdict": "EXCLUDED_PAID", "closest": "cot_rename", "why": "有料"},
}

#: 次段（Stage 0 の取得と feasibility）へ進める判定。
ADVANCING_VERDICTS: Final[frozenset[str]] = frozenset(
    {"ELIGIBLE", "ELIGIBLE_WITH_RENAME_GATE", "ELIGIBLE_DATA_LIMITED", "ELIGIBLE_DATA_BURDEN"}
)


def prior_score(row: dict[str, Any]) -> float:
    """裁定 §18 の概念式。**幾何平均の比**にして、因子の数で尺度が変わらないようにする。"""
    score = row["score"]
    top = math.prod(score[f] for f in universe.NUMERATOR) ** (1 / len(universe.NUMERATOR))
    bottom = math.prod(score[f] for f in universe.DENOMINATOR) ** (1 / len(universe.DENOMINATOR))
    return round(top / bottom, 3)


def ranked() -> list[dict[str, Any]]:
    rows = []
    for row in universe.MECHANISMS:
        mid = row["mechanism_id"]
        audit = OVERLAP_AUDIT[mid]
        rows.append(
            {
                "mechanism_id": mid,
                "name": row["name"],
                "family_letter": row["family_letter"],
                "prior_score": prior_score(row),
                "overlap_verdict": audit["verdict"],
                "advances_to_stage_0": audit["verdict"] in ADVANCING_VERDICTS,
            }
        )
    return sorted(rows, key=lambda r: (-r["prior_score"], r["mechanism_id"]))


def shortlist() -> tuple[str, ...]:
    """Stage 0 へ進む候補（overlap audit を通ったもの全部）。**prior score で切らない。**

    prior score は判断の集計なので、ここで上位だけを残すと判断の誤差がそのまま選抜になる。
    実行可能性は Stage 0 の測定で篩う。
    """
    return tuple(r["mechanism_id"] for r in ranked() if r["advances_to_stage_0"])


def coverage() -> dict[str, Any]:
    ids = {row["mechanism_id"] for row in universe.MECHANISMS}
    return {
        "mechanisms": len(ids),
        "audited": len(OVERLAP_AUDIT),
        "complete": ids == set(OVERLAP_AUDIT),
        "letters_covered": sorted({row["family_letter"] for row in universe.MECHANISMS}),
    }


__all__ = [
    "ADVANCING_VERDICTS",
    "CLOSED_FAMILIES",
    "OVERLAP_AUDIT",
    "coverage",
    "prior_score",
    "ranked",
    "shortlist",
]
