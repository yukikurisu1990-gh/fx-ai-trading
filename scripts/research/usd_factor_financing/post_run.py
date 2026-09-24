# ruff: noqa: E501 -- post-run prose
"""M15 / M16 修正版の実行後 review（2 役）の結論と、記録の読み方。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY`.

実行記録 `development.json`（HEAD 69a18a0、1 回、両 track）は書き換えない。
実行後 review: Role 1（経済・financing）BLOCKER 0 / REQUIRED 5、Role 2（実装・governance）BLOCKER 0 / REQUIRED 3。
"""

from __future__ import annotations

from typing import Any, Final

FINAL_STATUS: Final[dict[str, dict[str, str]]] = {
    "M15": {
        "status": "M15_CORRECTED_FINANCING_NOT_DECISION_GRADE",
        "qualifier": "POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY",
        "reading": (
            "carry を機械的に受け取る取引。long の年率は spot +0.15%（net ex-financing Sharpe 0.007、null p 0.57）、"
            "carry +1.65%（政策金利）、markup −0.71%（central）。損益分岐 markup 1.2%/pair notional ≈ 平均 |金利差|。"
            "**『financing が分かれば判定できる』ではない**: markup 0 でも E6 / E8 偽、null p 0.40、有効標本 5、"
            "spot 平均の SE ≈ 2.5%/年は markup band の幅と同じ大きさで、broker データでは減らない"
        ),
        "recent_span": "long USD 100%・有効標本 1。total / ex-financing の Sharpe は constant_long_usd benchmark と小数 4 桁まで同一。**M15 の証拠として引用しない**（capacity も『ドル買い benchmark の capacity』）",
    },
    "M16": {
        "status": "M16_CORRECTED_POSITIVE_EXPLORATORY_NOT_DECISION_GRADE",
        "qualifier": "POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY",
        "reading": (
            "long は 8 セル全点で正、spot 由来（carry −0.04%/年でほぼ中立、markup は純粋な費用）。"
            "null: ex-financing Sharpe 0.348（percentile 0.839、p 0.162）、total 0.276（0.809、p 0.192）。"
            "Stage 2 の signal t 0.92（過大）。**long の central の大きさ・符号と change-window の grid 形は実行前に既知**で、"
            "新しい情報（routing 修正後の recent −0.50、分解、null percentile 0.87→0.81）はどれも不利な方向"
        ),
        "why_not_marginal": "E6（top10 0.536）と E8（0.276 < 0.30）が central で偽、不利な端点で E7 偽（cost ×2 が markup も ×2 = 4%）。凍結規則どおりで、**救済の論拠にしない**。MARGINAL だったとしても p 0.19 は decision-grade ではない",
    },
}

CAPACITY_CORRECTIONS: Final[dict[str, str]] = {
    "portfolio_gross": "記録の portfolio_gross は通貨 gross で、USD numeraire では broker の pair notional の 2 倍",
    "risk_leverage": "held gross = 1 なので portfolio_gross と恒等的に同じ値（独立の情報ではない）",
    "pair_specific_margin": "通貨 gross に掛けているので 2 倍過大（保守側）",
    "m16_5pct": "M16 で年 5% には vol 18.2%、線形に拡大した DD −70%（central markup で financing −1.3%/年、markup 2% なら約 −5%/年）。年 10% は vol 36%・DD −140%（破綻）。DD 20% に抑えると net 約 1.4%/年",
    "m15": "long の central Sharpe 0.097 で年 5% には vol 52%",
    "broker_ceiling": "margin（20x / 25x）は制約にならない。制約は risk",
}

POST_RESULT_DESIGN_CHANGES: Final[dict[str, str]] = {
    "note": "第 3 裁定の『同一の修正』について: 以下は結果（旧 book の値）を見た後に、M15 と M16 に同じく当てた設計の変更である。book の rebalance 単位以外にも及ぶので、Human + ChatGPT の確認事項として列挙する",
    "rebalance_unit": "basket を 1 単位（factor_rebalance）— 裁定 §16 の必須修正",
    "routing": "USD numeraire（7 本の USD pair）— 裁定 §17『routing preserves factor exposure』のための修正（equal-split は recent で外国脚が最大 2.08 倍ずれた）",
    "carry_rate_basis": "primary を当時の政策金利、lag 付き 3 か月金利を感度 — 裁定 §7『financing は会計』に合わせた（3 か月 lag は signal の series そのもの）",
    "markup_unit_and_band": "pair notional 1 単位あたり {0, 0.5, 1, 2}%/年（通貨 gross では従来と同じ {0, 0.25, 0.5, 1}%）",
    "eight_cell_rule": "金利基準 2 × markup 4 の符号一致、不利な端点でも core — 裁定 §11『都合のよい 1 点の近似で決めない』",
}

DISCLOSURES: Final[dict[str, str]] = {
    "STARTED_MARKER_NOT_COMMITTED_BEFORE_RUN": "開始記録は実行前に commit されていない。1 回だけの実行は、最後の凍結 commit から 7 秒後の開始・約 20 分の実行・dangling object / log 無し・reflog による状況証拠",
    "INHERITED_FROM_MECHANISM_REDESIGN": "M16 は M11 と同じ入力で、CPI 前年比の分母が保護期間に掛かる保存値・HICP の 2025=100・季節調整係数・GBP lag の慣行の開示（mechanism_redesign.post_run.DISCLOSURES）がそのまま当てはまる",
    "D_M3_MORE_DIRECT": "JPY の政策金利が primary の carry 会計に入った。D-M3（lead が 2026 年の BoJ 決定を読んだ）の JPY_RATE_RELATED_FORWARD_CONFIRMATION_CONTAMINATED はこの track にも当てはまる",
    "PANEL_CARRY_LEG_LABEL": "記録の panel.carry_leg『SPOT_ONLY』は top_five panel の provenance の引き継ぎで、判定 P&L には carry が入っている",
    "USD_CONTRIBUTION_ZERO": "USD の currency_contribution が 0.0 なのは USD numeraire の構成（R_USD = 0）。旧 book の欠陥（通貨の恒久的な 0）とは別",
    "IDENTICAL_RISK_LEVERAGE": "M15_long と M16_long の risk_leverage が同じなのは、±同じ book の ex-ante vol が符号に依らないため",
    "CONTEMPORANEOUS_MEANS": "当時の政策金利は『最大 1 か月遅れの月末値』。BIS に無い JPY −0.1%（2016-02…05）は 0% で補完",
    "SOURCE_AUDIT_WORDING": "『現在値の公開ページは存在する』は取得した証拠ではない（#472 の probe では financing-rates ページは 404）",
    "SPREAD_CONVENTION": "spread cost は Σ|Δx| を通貨で数えるので USD routing では pair notional の 2 倍に課金（保守側、0.08〜0.18%/年）",
}

FINANCING_IMPACT_READING: Final[str] = (
    "financing を入れなかったことで過去の負の結論が candidate に変わる現実的な経路は無い（向きが金利と無関係なら "
    "carry の期待値は 0、markup は常に費用）。flag された負の 4 本は転じても年 1% 未満。**正の net だった過去の結果は "
    "ほぼ一様に過大評価の方向**（U2 recent・U4 recent・T-R2 B・T-V A・M11・M01 は現実的な markup で負になりうる。"
    "T5 recent は残る）。判定ラベル（どれも decision-grade ではない）は変わらない"
)


def record() -> dict[str, Any]:
    return {
        "final_status": FINAL_STATUS,
        "capacity_corrections": CAPACITY_CORRECTIONS,
        "post_result_design_changes": POST_RESULT_DESIGN_CHANGES,
        "disclosures": DISCLOSURES,
        "financing_impact_reading": FINANCING_IMPACT_READING,
    }


__all__ = [
    "CAPACITY_CORRECTIONS",
    "DISCLOSURES",
    "FINAL_STATUS",
    "FINANCING_IMPACT_READING",
    "POST_RESULT_DESIGN_CHANGES",
    "record",
]
