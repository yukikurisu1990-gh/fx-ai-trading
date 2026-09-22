# ruff: noqa: E501 -- inventory prose
"""Top-Five 実行後の **candidate inventory**（2026-09-22 裁定 §D）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

裁定 §D が求める 7 分類へ、`scripts/research/edge_sources/candidates.py` の全候補を割り当てる。

**分類は判断ではなく帰結として書く。** どの候補も「なぜその箱に入ったか」を
1 つの出来事（実行された / family 境界の内側だった / データが無い）に紐づける。
紐づかないものは `UNTESTED` に残す — **「弱そう」は分類の根拠にならない。**

裁定 §F が禁じた一般化はしない: high-turnover source 全部 / cross-asset 全部 /
event 全部 / flow 全部 / rates 全部 が駄目、とは書かない。**今回 tested した scope だけを反映する。**
"""

from __future__ import annotations

from typing import Any, Final

from scripts.research.edge_sources import candidates as edge_candidates

#: 裁定 §D が名指しした 7 分類。**この順に強い** わけではない。別の種類の状態である。
CLASSES: Final[tuple[str, ...]] = (
    "CLOSED",
    "NOT_SUPPORTED",
    "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE",
    "DATA_NOT_DECISION_GRADE",
    "DATA_UNAVAILABLE",
    "PAID_DATA_ONLY",
    "UNTESTED",
)

#: Top-Five で実行された 5 本（裁定 §D: 次の execution set から除外する）。
EXECUTED_IN_TOP_FIVE: Final[dict[str, str]] = {
    "S05": "T1",
    "S06": "T2",
    "S02": "T3",
    "S10": "T4",
    "S26": "T5",
}

#: それ以前に実行された track。
EXECUTED_EARLIER: Final[dict[str, str]] = {
    "S01": "T-R（PR #485）",
    "S13": "T-V（PR #486–#488）",
}

#: 各候補の分類と、その**根拠になった出来事**。
CLASSIFICATION: Final[dict[str, dict[str, Any]]] = {
    # ---- 実行して支持されなかったもの ----------------------------------
    "S01": {
        "klass": "NOT_SUPPORTED",
        "basis": "EXECUTED",
        "where": "T-R / PR #485",
        "why": "5 日 measure は半減期 1.7 日で turnover 82–98、gross 正・net 負",
    },
    "S13": {
        "klass": "NOT_SUPPORTED",
        "basis": "EXECUTED",
        "where": "T-V / PR #486–#488",
        "why": "turnover 1.25 回転/年で cost は結論を決めなかったが、incremental IC の NW t が −3.34 で名目平均回帰より有意に悪い",
    },
    "S05": {
        "klass": "NOT_SUPPORTED",
        "basis": "EXECUTED",
        "where": "T1 / Top-Five",
        "why": "gross は両 span で正（+0.139 / +0.336）、net は両方負（−0.435 / −0.500）。turnover は凍結範囲内で、**gross が想定どおりの cost に届かなかった**",
    },
    "S06": {
        "klass": "NOT_SUPPORTED",
        "basis": "EXECUTED",
        "where": "T2 / Top-Five",
        "why": "長 span は gross から負。近 span は gross +0.519 / net −0.253。**T1 を超える incremental IC が両 span とも負**で、独立な情報源として支持されなかった",
    },
    "S02": {
        "klass": "NOT_SUPPORTED",
        "basis": "EXECUTED",
        "where": "T3 / Top-Five",
        "why": "両符号を事前登録して両方走らせ、net は H1 −1.638 / H2 −0.148 で**どちらも負**。5 本で唯一 turnover 想定を超えた（57.9 対 34.8）",
        "sub_status": "DATA_NOT_DECISION_GRADE（長 span のみ）",
    },
    "S10": {
        "klass": "NOT_SUPPORTED",
        "basis": "EXECUTED",
        "where": "T4 / Top-Five",
        "why": "近 span は gross から負（−0.409）。net −1.435 / −2.890 で 5 本最悪。turnover は凍結範囲内だが絶対水準が桁違い",
    },
    # ---- 実行して net 正だったが decision grade ではないもの --------------
    "S26": {
        "klass": "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE",
        "basis": "EXECUTED",
        "where": "T5 / Top-Five",
        "why": "近 span で net +0.838 / 年 +8.57%。**ただしその窓の 95% 検出下限 1.321 を下回り**、permutation p = 0.314、零情報 null の 95 パーセンタイル +1.13 の内側",
        "ruling": "2026-09-22 §4 — MARGINAL_DEVELOPMENT_CANDIDATE としては扱わない",
        "family_not_closed": (
            "**TIC / capital-flow の方向そのものは閉じていない**（裁定 §C）。"
            "genuine historical vintage data・独立した flow source・"
            "実質的に異なる positioning / flow 情報が得られたときは新 hypothesis になり得る"
        ),
    },
    # ---- family 境界・rename・rescue・構造的不能 -------------------------
    "S03": {
        "klass": "CLOSED",
        "basis": "JUDGEMENT_RECORDED_AT_RERANK",
        "where": "#489 §3",
        "why": "閉じた direction source に event 条件を付けたもの。cost 優位の不在が実測され、検出力の天井もある",
    },
    "S04": {
        "klass": "CLOSED",
        "basis": "JUDGEMENT_RECORDED_AT_RERANK",
        "where": "#489 §3",
        "why": "S03 と同じ理由に加え、**US 以外に無料の公式 timestamp 付きカレンダーが無い**",
    },
    "S08": {
        "klass": "CLOSED",
        "basis": "OWN_RULE_REQUIRES_A_CLOSED_BASE",
        "where": "#489",
        "why": "自身の順序規則が S01（閉じた base）を要求する",
    },
    "S16": {
        "klass": "CLOSED",
        "basis": "OWN_RULE_REQUIRES_A_CLOSED_BASE",
        "where": "#489",
        "why": "S08 と同じ — 前提が満たせなくなった",
    },
    "S17": {
        "klass": "CLOSED",
        "basis": "OWN_RULE_REQUIRES_A_CLOSED_BASE",
        "where": "#489",
        "why": "base が除外済みで、cross-asset 部分は S05。**その S05 は Top-Five で NOT_SUPPORTED になった**",
    },
    "S28": {
        "klass": "CLOSED",
        "basis": "INSIDE_A_DECLARED_FAMILY_BOUNDARY",
        "where": "#489",
        "why": "sovereign yield 差の単純な方向 repricing として family 境界の内側",
    },
    "S09": {
        "klass": "CLOSED",
        "basis": "STRUCTURALLY_CANNOT_CLEAR_COST",
        "where": "candidates.py",
        "why": "三角 residual は構造的に cost を超えられない",
    },
    "S11": {
        "klass": "CLOSED",
        "basis": "RENAME_OR_RESCUE",
        "where": "candidates.py",
        "why": "閉じた family の言い換え",
    },
    "S19": {
        "klass": "CLOSED",
        "basis": "RENAME_OR_RESCUE",
        "where": "candidates.py",
        "why": "閉じた family の言い換え",
    },
    "S21": {
        "klass": "CLOSED",
        "basis": "FAMILY_SUSPENDED_BY_DECISION",
        "where": "candidates.py",
        "why": "決定により family が停止中",
    },
    "S23": {
        "klass": "CLOSED",
        "basis": "RENAME_OR_RESCUE",
        "where": "candidates.py",
        "why": "閉じた family の言い換え",
    },
    "S24": {
        "klass": "CLOSED",
        "basis": "RENAME_OR_RESCUE",
        "where": "candidates.py",
        "why": "閉じた family の言い換え",
    },
    # ---- データが無いもの ------------------------------------------------
    "S18": {
        "klass": "DATA_UNAVAILABLE",
        "basis": "NO_FREE_HISTORY_EXISTS",
        "where": "candidates.py",
        "why": "retail positioning の過去履歴が無料で揃わない。forward に蓄積するしかなく、認証または scraping が要る（未承認）",
    },
    "S20": {
        "klass": "PAID_DATA_ONLY",
        "basis": "PAID_SOURCE_ONLY",
        "where": "candidates.py",
        "why": "25 delta risk reversal の無料履歴が存在しない",
    },
    "S22": {
        "klass": "PAID_DATA_ONLY",
        "basis": "PAID_SOURCE_ONLY",
        "where": "candidates.py",
        "why": "intraday の株価指数先物が有料。price のみにすると閉じた family と同じになる",
    },
    # ---- 未検証 ----------------------------------------------------------
    "S07": {
        "klass": "UNTESTED",
        "basis": "NEVER_RUN",
        "where": "-",
        "why": "信用 spread・funding stress。FRED の HY OAS は probe で range を取れていない（**到達不能ではなく未確認**）",
    },
    "S12": {
        "klass": "UNTESTED",
        "basis": "NEVER_RUN",
        "where": "-",
        "why": "相関 breakdown / dispersion。**price 由来**",
    },
    "S14": {
        "klass": "UNTESTED",
        "basis": "NEVER_RUN",
        "where": "-",
        "why": "fast / medium / slow の price state 不一致。**price 由来**で、Track 1 が同じ入力の線形結合で gross 負",
    },
    "S15": {
        "klass": "UNTESTED",
        "basis": "NEVER_RUN",
        "where": "-",
        "why": "volatility / trend の状態遷移。**price 由来**だが、遷移そのものは測られていない",
    },
    "S25": {
        "klass": "UNTESTED",
        "basis": "NEVER_RUN",
        "where": "-",
        "why": "中銀 balance sheet・準備資産 flow。非価格・低頻度・無料",
    },
    "S27": {
        "klass": "UNTESTED",
        "basis": "NEVER_RUN",
        "where": "-",
        "why": "中銀 communication の tone。非価格・テキスト・無料（機械取得の可否は未確認）",
    },
}

#: **本 cycle で inventory へ新しく足した候補。**
#:
#: 足した理由を明示する: 既存 28 本のうち未検証 eligible は **6 本しか残っていない**。
#: そのうち 3 本（S12 / S14 / S15）は FX 価格の変換で、裁定 §E が 2 番目に置いた
#: 「price を超える incremental information」が**構造上ほぼ無い**。
#: CORE PRINCIPLE の "Then move to genuinely new information" に従い、
#: **無料 / 非価格 / 機構が明確で、既存 family の言い換えでない source** を 2 本足す。
#:
#: **alpha は 1 本も見ていない状態で足している**（signal-blind）。
NEW_CANDIDATES: Final[dict[str, dict[str, Any]]] = {
    "S29": {
        "name": "実体貿易 flow（貿易収支・経常収支）の相対変化 → 通貨",
        "direction": "A",
        "mechanism": (
            "財・サービスの純輸出は、決済のための**実需の通貨需要**を生む。"
            "portfolio flow（S26）とは別の主体・別の経路であり、"
            "景気循環に沿ってゆっくり変わる"
        ),
        "information": "各国の月次貿易収支 / 経常収支（各国統計局・FRED・OECD）",
        "why_distinct": (
            "S26 は **US の証券投資 flow**（TIC）で、主体は投資家、対象は証券。"
            "S29 は **G10 各国の財・サービス収支**で、主体は企業と家計、対象は実需決済。"
            "S13（実質為替 valuation）は **価格水準**の乖離であって flow ではない。"
            "**同じ数字を別名で呼んだものではない**"
        ),
        "why_it_fits_the_new_ranking": (
            "裁定 §E が求めた『自然な economic mechanism として signal がゆっくり変わる』"
            "に最も素直に当てはまる — 貿易収支は月次で、構造的にゆっくり動く。"
            "**低 turnover を alpha source として扱っているのではなく、"
            "機構そのものが遅いから遅い**"
        ),
        "data_risk": "G10 8 通貨すべてで無料・時刻付き・十分な履歴が揃うかは Stage 0 で確認する",
    },
    "S31": {
        "name": "公的外貨準備の変化 → 通貨",
        "direction": "A",
        "mechanism": (
            "中銀・財務省が外貨準備を積み増す / 取り崩す行為は、"
            "**それ自体が為替市場での売買**である。介入と準備再配分が直接に通貨需要を動かす"
        ),
        "information": "各国の月次外貨準備高（各中銀・財務省・IMF）",
        "why_distinct": (
            "S25 は**自国通貨建ての balance sheet の大きさ**（QE / QT の相対ペース）で、"
            "国内流動性の話。S31 は**外貨建て準備の増減**で、為替市場での実際の売買。"
            "S26 は民間の証券投資。**主体も通貨も経路も違う**"
        ),
        "expected_weakness_declared_in_advance": (
            "**breadth が小さいと予想する。** G10 のうち準備を能動的に動かしてきたのは "
            "実質 CHF（SNB）と JPY（MOF）で、他は受動的である。"
            "T5 が USD 一軸だったのと同じ構造的弱点を、**結果を見る前に宣言しておく**"
        ),
        "why_it_is_not_a_t5_rescue": (
            "裁定 §C は TIC / capital-flow を family closure にせず、"
            "**独立した flow source は新 hypothesis になり得る**と明示した。"
            "S31 は公的部門の実需売買で、T5 の民間証券投資とはデータも主体も異なる。"
            "**T5 の signal を作り直したものではない**"
        ),
        "data_risk": "無料・時刻付きの月次履歴が G10 で揃うかは Stage 0 で確認する",
    },
}


def classify() -> dict[str, list[str]]:
    """分類 → 候補 id。**空の箱も残す**（無いことが情報である）。"""
    buckets: dict[str, list[str]] = {name: [] for name in CLASSES}
    for cid, row in CLASSIFICATION.items():
        buckets[row["klass"]].append(cid)
    for cid in NEW_CANDIDATES:
        buckets["UNTESTED"].append(cid)
    return {name: sorted(ids) for name, ids in buckets.items()}


def untested() -> tuple[str, ...]:
    """次の ranking に載る候補。**裁定 §D により実行済み 5 本は除外される。**"""
    ids = [cid for cid, row in CLASSIFICATION.items() if row["klass"] == "UNTESTED"]
    return tuple(sorted(ids) + sorted(NEW_CANDIDATES))


def excluded_from_next_execution() -> tuple[str, ...]:
    """次の execution set に入れないもの（実行済み + 実行不能）。"""
    blocked = {
        cid
        for cid, row in CLASSIFICATION.items()
        if row["klass"] in {"CLOSED", "DATA_UNAVAILABLE", "PAID_DATA_ONLY"}
    }
    return tuple(sorted(set(EXECUTED_IN_TOP_FIVE) | set(EXECUTED_EARLIER) | blocked))


def coverage() -> dict[str, Any]:
    """**inventory が全候補を覆っているか**を、主張ではなく計算で示す。"""
    known = {candidate.cid for candidate in edge_candidates.CANDIDATES}
    classified = set(CLASSIFICATION)
    return {
        "known_candidates": len(known),
        "classified": len(classified),
        "added_this_cycle": sorted(NEW_CANDIDATES),
        "missing_from_classification": sorted(known - classified),
        "classified_but_unknown": sorted(classified - known),
        "complete": known == classified,
    }


#: 裁定 §F が明示的に禁じた一般化。**ここに書いてあるものは書かない。**
FORBIDDEN_GENERALISATIONS: Final[tuple[str, ...]] = (
    "high-turnover source は全部だめ",
    "cross-asset は全部だめ",
    "event は全部だめ",
    "flow は全部だめ",
    "rates は全部だめ",
)

#: 逆に、**今回 tested した scope で言えること**。
WHAT_THE_CYCLE_ACTUALLY_SHOWED: Final[str] = (
    "G10 FX spot の日次 book において、**VIX shock / 原油交易条件 / sovereign curve 形状 / "
    "通貨間伝播**の 4 つは、凍結した cost 規約のもとで net を残さなかった。"
    "4 本とも gross は正で、年 6–9% の cost がそれを飲み込んだ。"
    "**これは candidate prior には使えるが、同じ signal の救済実験には使わない**（裁定 §B）"
)


__all__ = [
    "CLASSES",
    "CLASSIFICATION",
    "EXECUTED_EARLIER",
    "EXECUTED_IN_TOP_FIVE",
    "FORBIDDEN_GENERALISATIONS",
    "NEW_CANDIDATES",
    "WHAT_THE_CYCLE_ACTUALLY_SHOWED",
    "classify",
    "coverage",
    "excluded_from_next_execution",
    "untested",
]
