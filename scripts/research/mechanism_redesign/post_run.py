# ruff: noqa: E501 -- post-run prose
"""実行後の統合 review（2 役）の結論と、それに基づく結果の扱い（2026-09-24 裁定 §36 / §37）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

実行記録 `development.json`（HEAD 0ee7160、1 回）は**書き換えない**。ここにあるのは、その記録を
どう読むかの決定と、review が見つけた開示である。

**再実行はしない。** M15 / M16 の book の欠陥は結果を見た後に見つかった。修正して走らせ直すと、
唯一 MARGINAL だった M16 を結果を見てから作り直すことになる（しかも設計どおりの book に当たる
band 0.05 の感度行は既に見ている）。これは救済の形そのものなので、修正は新しい事前登録として
Human + ChatGPT の判断に回す。
"""

from __future__ import annotations

from typing import Any, Final

#: Role 1 BLOCKER-1。**M15 / M16 の結果は、凍結した mechanism の検定として無効。**
INVALIDATED: Final[dict[str, dict[str, Any]]] = {
    "M15": {
        "status": "INVALID_AS_A_TEST_OF_THE_FROZEN_MECHANISM_BOOK_CONSTRUCTION_DEFECT",
        "recorded_verdict_kept_as_history": "M15_M15_POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE",
    },
    "M16": {
        "status": "INVALID_AS_A_TEST_OF_THE_FROZEN_MECHANISM_BOOK_CONSTRUCTION_DEFECT",
        "recorded_verdict_kept_as_history": "M16_M16_MARGINAL_DEVELOPMENT_CANDIDATE",
    },
}
BOOK_DEFECT: Final[dict[str, str]] = {
    "found_by": "実行後の独立 review Role 1（経済）BLOCKER-1。lead が記録で確認",
    "frozen_intent": "USD 対 7 通貨の等ウェイト basket（ドル factor）",
    "what_ran": (
        "target は USD ±0.5・外国 7 通貨 各 ∓0.0714。band 0.10 の下で外国の脚の gap（0.0714）が band 未満なので"
        "売買されず、band_rebalance の『全 breach が同符号なら反対側 gap 最大の通貨を counter-leg にする』規則が"
        "同値の中からアルファベット順の先頭（AUD → CAD → CHF）を選んだ。定常の book は USD ±0.43 対 AUD / CAD / CHF 各 ∓0.14 で、"
        "EUR / GBP / JPY / NZD は恒久的に 0"
    ),
    "evidence_in_the_record": (
        "M15 / M16 の両 span で currency_contribution の EUR / GBP / JPY / NZD が厳密に 0.0。"
        "その 4 通貨の LOO が全体の net と同値。M15_long と M16_long の portfolio gross（2.376）と risk leverage（2.773）が一致"
    ),
    "consequences": (
        "null・E5・E6・E8・capacity・carry（符号は 7 通貨平均で決め、受け取るのは AUD / CAD / CHF との金利差）のすべてが"
        "『USD 対 commodity / CHF の小 basket』の数字。Stage 2 の回帰だけは設計どおりの mu を使っていた"
    ),
    "as_designed_rows_already_seen": (
        "band 0.05 の感度行だけが設計どおりの 7 通貨 book に当たる（M16 net 0.279 / gross 0.354、M15 net 0.102）。"
        "これは感度行で、null も E5 / E6 / E8 も測られていない。**POST_HOC_EXPLORATORY として並べるだけで、verdict は付けない**"
    ),
    "why_it_escaped_every_pre_alpha_review": (
        "5 回の pre-alpha review は signal・timing・carry・凍結を見たが、run_book の band 規則とドル track の mu の相互作用は"
        "return 無しの合成入力で走らせないと見えず、誰も走らせなかった"
    ),
    "not_a_shared_defect_for": "M11 / M01 / M10（XS book、連続 score なので同値の tie が起きない）",
    "fix_proposal_not_applied": (
        "ドル track では basket を 1 単位として rebalance する（USD の脚が band を超えたら 7 通貨の脚を同時に動かす）か、"
        "band を外国の脚の target 未満にする。**どちらも結果を見た後の設計変更なので、新しい事前登録として扱う**"
    ),
}

#: 実行後 review の REQUIRED_FIX（結果の数値は変えない。報告で限定・開示する）。
REPORT_QUALIFICATIONS: Final[dict[str, str]] = {
    "M16_EVIDENCE": (
        "（記録上の）M16 は凍結規則上 MARGINAL だったが、book が欠陥なので無効。仮に book を度外視しても、p 0.132、"
        "5 本の最小 p が 0.132 以下になる確率は帰無でも約 50%、Stage 2 の signal t 0.92（重複未補正で過大）、E6 は余裕 0.003、"
        "E8 は不足 0.007（markup 0.22% なら通る）、recent は負、change window で 0.09〜0.42 — Sharpe 0.3 級の edge の証拠ではない"
    ),
    "M15_CARRY": (
        "long の net は spot +0.035%（spot のみの gross Sharpe 0.003）+ carry 1.49% − spread 0.09% − financing 0.585% で、"
        "ほぼ全部が carry。net がゼロになる markup は約 0.61%/年。recent の M15 は符号が一度も変わらず constant_long_usd と同一"
    ),
    "M01_CARRY": (
        "spot のみの net Sharpe 0.296 は低金利通貨を持つ費用を無視した値。carry（−1.48%）を入れた gross 0.185 が正しい像。"
        "E4 30/70、USD 抜き LOO −0.149、top10 173% — 集中と時間的な不安定が本体"
    ),
    "M11_ROBUSTNESS": "change window 6 / 12 / 24 の net が −0.234 / +0.159 / +0.553 で符号を跨ぐ。recent は −0.83。頑健性は無い",
    "M10": "SIGNAL_FAILURE。band 感度は符号を跨ぐが、primary は凍結どおり。有効標本 0.5（過小推定）で refutation ではない",
    "CAPACITY_REACHABLE_LABEL": "capacity.reachable: True は『net > 0 だったので leverage 計算を出した』の意味だけ。どの track も 5% / 10% は現実的な risk に入らない",
    "CARRY_SHARPE_ALONE": "carry_sharpe_alone（±18 など）は accrual がほぼ決定論的で分散が小さいため発散した値。risk 調整後の指標ではない",
    "PANEL_CARRY_LEG_LABEL": "record の panel.carry_leg『SPOT_ONLY』は top_five panel の provenance の引き継ぎ。判定 P&L には carry が入っている",
    "STALENESS_SENSITIVITY": "max_staleness_days_monthly の感度が M11 / M15 / M16 で全点同一なのは、月次 series が 31 日以内に更新され 45 日以上の閾値が効かないため。頑健性の証拠ではない",
}

#: Role 2 の REQUIRED_FIX（開示）。
DISCLOSURES: Final[dict[str, str]] = {
    "CPI_YOY_SAVED_WITH_PROTECTED_BASE": (
        "CPI 前年比の recent の stamp 2021-05 … 2022-04（四半期 2021-07 … 2022-04）は分母が fresh pool の物価で、"
        "request・保存された（読む側では落とした）。JPY は 2021-05・06 の前年比と指数の両方が保存されており、"
        "2020-05・06（fresh pool）の JPY CPI 水準が逆算可能（逆算はしていない）。D-5 の request-level exclusion を"
        "『参照期間が分母を含む』series には満たしていなかった"
    ),
    "HICP_BASE_YEAR": (
        "CP0000EZ19M086NEST の単位は Index 2025=100。2025 年平均は 2025-12（保護側を含む月）を含むので、保存した 1〜11 月から"
        "2025-12 の HICP 水準が丸め誤差の範囲で決まる（計算はしていない）。signal は log 12 か月変化なので結果への影響は無い"
    ),
    "D_M3_CONSEQUENCE": (
        "lead session は forward epoch の BoJ 政策決定（2026 年）を読んだ。JPY の金利を使う track（M01・carry を含む全 track）を"
        "将来 Formal Confirmation する場合、この session の知識は forward epoch の汚染として扱う必要がある"
    ),
    "GBP_LAG_CONVENTION": (
        "GBP 失業率の lag m+3 は OECD が中心月か末尾月に stamp する場合だけ公表後になる。開始月の慣行なら約 2 週間の先読み。"
        "慣行は metadata で確かめていない（影響は 1 通貨・1 か月程度）"
    ),
    "SA_COEFFICIENTS": "現行 vintage の季節調整済み失業率は、係数の推定に fresh pool と forward の data を含む（revision caveat としては宣言済みだが、保護期間の情報流入とは書いていなかった）",
    "STARTED_MARKER_NOT_COMMITTED_BEFORE_RUN": "development_started.json は実行前に commit されていない。1 回だけの実行は file 時刻・reflog の状況証拠による",
}


def record() -> dict[str, Any]:
    return {
        "invalidated": INVALIDATED,
        "book_defect": BOOK_DEFECT,
        "report_qualifications": REPORT_QUALIFICATIONS,
        "disclosures": DISCLOSURES,
        "rerun": "NONE — 修正は新しい事前登録として Human + ChatGPT の判断に回す",
    }


__all__ = ["BOOK_DEFECT", "DISCLOSURES", "INVALIDATED", "REPORT_QUALIFICATIONS", "record"]
