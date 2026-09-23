# ruff: noqa: E501 -- ranking prose
"""未検証候補の **signal-blind rerank**（2026-09-22 裁定 §E）と **5 本の選定**（§I）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**alpha は 1 本も見ていない。** ここで付ける点数は、候補の *機構とデータの性質* だけから
決まる。結果を 1 つでも見た後にこの表を触ったら、それは rerank ではなく後付けである。

裁定 §E が新しく重視すると定めた 10 次元をそのまま使う。等重みで足す —
**重みを自分で選ぶと、重みが結論になる。**

ひとつだけ規則を足してある（§E の但し書き）:

    low turnover 自体を alpha source とはしない。
    「自然な economic mechanism として signal がゆっくり変わる」candidate を優先する。

したがって **次元 3（natural persistence）は `persistence_is_mechanistic` が真のときしか
満点に届かない。** 平滑化して遅くしただけの signal は、ここで点を取れない。
"""

from __future__ import annotations

from typing import Any, Final

from scripts.research.next_five import inventory

#: 裁定 §E が名指しした 10 次元。**順序は重要度ではない**（等重みである）。
DIMENSIONS: Final[tuple[str, ...]] = (
    "expected_return_information_quality",
    "incremental_information_beyond_fx_price",
    "natural_signal_persistence",
    "expected_turnover",
    "cost_drag",
    "breadth",
    "timing_quality",
    "public_data_reproducibility",
    "realistic_annual_return_capacity",
    "expected_information_gain",
)

#: 各次元は 1–5。**5 が良い**（turnover と cost drag は「小さいほど良い」を 5 に揃えてある）。
SCALE: Final[tuple[int, int]] = (1, 5)

#: 同点のときの決め方を **先に** 決めておく。
#:
#: 選ぶのは次元 2（price を超える incremental information）である。理由は前 cycle が
#: 測った事実 — **T2 は gross が正でも T1 を超える増分が両 span とも負で、
#: 独立な情報源として支持されなかった**。gross があっても「価格の言い換え」なら残らない。
#: これは新候補の結果とは無関係に決まる規則なので、signal-blind である。
TIEBREAK: Final[str] = "incremental_information_beyond_fx_price"

#: 裁定 §I の hard filter。**点数の前に効く。**
HARD_FILTERS: Final[tuple[str, ...]] = (
    "genuinely_distinct",
    "not_a_rename_of_a_prior_failed_family",
    "runnable_on_current_free_public_data",
    "needs_no_protected_data",
    "economic_mechanism_is_explicit",
    "timing_is_defensible",
    "expected_return_magnitude_is_plausible",
)

SCORES: Final[dict[str, dict[str, Any]]] = {
    "S29": {
        "name": "実体貿易 flow（貿易収支・経常収支）→ 通貨",
        "scores": (4, 5, 5, 5, 5, 5, 4, 4, 3, 5),
        "persistence_is_mechanistic": True,
        "why_persistence_is_mechanistic": "貿易収支は月次で、景気循環に沿って動く。**遅いのは平滑化したからではなく、実体が遅いから**",
        "filters": dict.fromkeys(HARD_FILTERS, True),
        "note": "G10 8 通貨すべてが公表するので **breadth が構造的に大きい**。前 cycle で breadth 1 が致命的だったことへの直接の対処になる",
    },
    "S25": {
        "name": "中銀 balance sheet・準備資産 flow",
        "scores": (4, 5, 5, 5, 5, 3, 4, 4, 3, 5),
        "persistence_is_mechanistic": True,
        "why_persistence_is_mechanistic": "QE / QT は四半期〜年単位の政策決定で動く。週次公表でも中身はゆっくり変わる",
        "filters": dict.fromkeys(HARD_FILTERS, True),
        "note": "主要 4–5 中銀に限られるので breadth は中程度",
    },
    "S27": {
        "name": "中銀 communication の tone 変化",
        "scores": (4, 5, 4, 5, 5, 3, 3, 2, 3, 5),
        "persistence_is_mechanistic": True,
        "why_persistence_is_mechanistic": "会合の周期そのものが signal の周期になる。**人為的な平滑化ではない**",
        "filters": dict.fromkeys(HARD_FILTERS, True),
        "note": "**public-data reproducibility が最低点。** 時刻付きテキスト archive の機械取得が未確認で、Stage 0 で落ちる可能性が最も高い",
    },
    "S31": {
        "name": "公的外貨準備の変化 → 通貨",
        "scores": (3, 5, 5, 5, 5, 2, 4, 3, 2, 4),
        "persistence_is_mechanistic": True,
        "why_persistence_is_mechanistic": "準備の積み増し / 取り崩しは月次で、政策判断に沿って持続する",
        "filters": dict.fromkeys(HARD_FILTERS, True),
        "note": "**breadth の低さを結果を見る前に宣言してある** — 能動的に準備を動かすのは実質 CHF と JPY だけで、T5 の USD 一軸と同じ構造的弱点を抱える",
    },
    "S07": {
        "name": "信用 spread・funding stress → USD・JPY・CHF",
        "scores": (4, 4, 3, 2, 2, 1, 4, 3, 2, 3),
        "persistence_is_mechanistic": False,
        "why_persistence_is_mechanistic": "credit spread は日次で動く。遅くするには平滑化が要るので、**次元 3 は満点にしない**",
        "filters": dict.fromkeys(HARD_FILTERS, True),
        "note": "非価格情報としての質は高いが、**breadth が最低**で turnover も高い。S15 と同点になった場合は TIEBREAK が効く",
    },
    "S15": {
        "name": "volatility / trend の状態遷移（latent regime）",
        "scores": (2, 1, 2, 2, 2, 4, 5, 5, 2, 3),
        "persistence_is_mechanistic": False,
        "why_persistence_is_mechanistic": "price 由来の状態推定で、持続性は window 長が決める",
        "filters": dict.fromkeys(HARD_FILTERS, True),
        "note": "**price 由来なので次元 2 が 1。** ただし遷移そのものは測られていない（H-022 の regime-gain は一定 gross の book では日次スカラーが消えるため、反証ではない）",
    },
    "S14": {
        "name": "fast / medium / slow の price state 不一致",
        "scores": (2, 1, 2, 2, 2, 4, 5, 5, 2, 1),
        "persistence_is_mechanistic": False,
        "why_persistence_is_mechanistic": "price 由来",
        "filters": {
            **dict.fromkeys(HARD_FILTERS, True),
            "not_a_rename_of_a_prior_failed_family": False,
        },
        "filter_failure": (
            "**Track 1 は 5 / 20 / 60 日 price state + trend age の線形結合を走らせて gross が負だった。** "
            "S14 は同じ入力の別の関数形（不一致）であり、裁定 §I の "
            "「prior failed family の rename ではない」を満たさない。"
            "**点数にかかわらず除外する** — filter は点数より先に効く"
        ),
        "note": "除外。点数は参考として残す",
    },
    "S12": {
        "name": "相関 breakdown / dispersion 状態の relative value",
        "scores": (2, 1, 2, 2, 2, 1, 5, 5, 1, 2),
        "persistence_is_mechanistic": False,
        "why_persistence_is_mechanistic": "price 由来",
        "filters": dict.fromkeys(HARD_FILTERS, True),
        "note": "price 由来かつ breadth が低い。8 本中最下位",
    },
}

#: 選ぶ本数（裁定 §I）。
EXECUTION_SET_SIZE: Final[int] = 5


def _total(cid: str) -> int:
    return sum(SCORES[cid]["scores"])


def passes_filters(cid: str) -> bool:
    return all(SCORES[cid]["filters"].values())


def ranked() -> tuple[dict[str, Any], ...]:
    """hard filter → 合計点 → TIEBREAK の順で並べる。"""
    index = DIMENSIONS.index(TIEBREAK)
    rows = [
        {
            "cid": cid,
            "name": entry["name"],
            "total": _total(cid),
            "tiebreak_value": entry["scores"][index],
            "passes_filters": passes_filters(cid),
            "persistence_is_mechanistic": entry["persistence_is_mechanistic"],
            "by_dimension": dict(zip(DIMENSIONS, entry["scores"], strict=True)),
        }
        for cid, entry in SCORES.items()
    ]
    rows.sort(key=lambda r: (not r["passes_filters"], -r["total"], -r["tiebreak_value"], r["cid"]))
    for position, row in enumerate(rows, start=1):
        row["rank"] = position
    return tuple(rows)


def execution_set() -> tuple[str, ...]:
    """**hard filter を通った上位 5 本。** paid-data-only は元から候補に入っていない。"""
    eligible = [row["cid"] for row in ranked() if row["passes_filters"]]
    return tuple(eligible[:EXECUTION_SET_SIZE])


def counterfactual_without_new_candidates() -> dict[str, Any]:
    """**新候補 2 本を足さなかったら何になっていたか。**

    足したこと自体が結論を動かしていないか、読む人が確かめられるようにしておく。
    """
    old = [
        row["cid"]
        for row in ranked()
        if row["passes_filters"] and row["cid"] not in inventory.NEW_CANDIDATES
    ]
    return {
        "pool_size": len(old),
        "set": tuple(old[:EXECUTION_SET_SIZE]),
        "reading": (
            "既存 28 本のうち未検証 eligible は 6 本で、rename filter で S14 が落ちるので "
            "**残りはちょうど 5 本**だった。つまり新候補を足さなければ『選定』は存在せず、"
            "残り全部を走らせることになっていた。しかもその 5 本のうち **3 本（S12 / S14 / S15）は "
            "price 由来**で、裁定 §E が 2 番目に置いた次元が構造上ほぼ無い。"
            "**新候補を足したのは選択肢を作るためであって、特定の結論へ寄せるためではない**"
        ),
    }


def summary() -> dict[str, Any]:
    chosen = execution_set()
    return {
        "authority": "2026-09-22 Human + ChatGPT 裁定 §E / §I",
        "signal_blind": "NO_ALPHA_SEEN_FOR_ANY_CANDIDATE_IN_THIS_SET",
        "dimensions": list(DIMENSIONS),
        "tiebreak": TIEBREAK,
        "hard_filters": list(HARD_FILTERS),
        "ranked": [{k: v for k, v in row.items() if k != "by_dimension"} for row in ranked()],
        "execution_set": list(chosen),
        "excluded_by_filter": [
            {"cid": cid, "why": SCORES[cid]["filter_failure"]}
            for cid in SCORES
            if not passes_filters(cid)
        ],
        "not_selected": [
            row["cid"] for row in ranked() if row["passes_filters"] and row["cid"] not in chosen
        ],
        "counterfactual_without_new_candidates": counterfactual_without_new_candidates(),
        "paid_data_only_kept_in_inventory_not_in_execution": ["S20", "S22"],
        "data_unavailable_kept_in_inventory": ["S18"],
    }


__all__ = [
    "DIMENSIONS",
    "EXECUTION_SET_SIZE",
    "HARD_FILTERS",
    "SCALE",
    "SCORES",
    "TIEBREAK",
    "counterfactual_without_new_candidates",
    "execution_set",
    "passes_filters",
    "ranked",
    "summary",
]
