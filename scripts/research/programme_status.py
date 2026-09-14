"""FX spot active-alpha research: the pause, its scope, and what reopens it.

`PRODUCTION_READINESS_NOT_CLAIMED`

The Human + ChatGPT decision of 2026-09-14 accepted Track 1's Case C and paused
active-alpha research on FX spot. This module is the machine-readable copy of
`docs/research/m15_fx_spot_active_alpha_research_pause.md`: every row of that
document's decision, scope, prohibition and condition tables is one entry here,
in the document's own Japanese wording, with its provenance. Tests require each
document row to equal its entry, so the two cannot say different things.

This is a record of a governance **constraint**, not a Track A research output
and not evidence for any GO. Nothing here reads data and nothing here authorises
anything: a status is a record, and resuming is an act that only an explicit
Human + ChatGPT decision performs.

Provenance labels
-----------------

* `裁定` — stated in the decision text as received.
* `裁定（推奨）` — stated in the decision text as a recommendation.
* `裁定から導出` — follows from the decision but is not stated as such; awaits
  confirmation.
* `既存規則` — already binding under repository governance (CLAUDE.md, the
  autonomous development policy, an earlier ruling or pre-registration).
* `起草` — proposed by this record because the decision text was received
  truncated in its §9; awaits confirmation.
* `記録用` — a token this record coins to name a ruled state; the decision did not
  word it.
"""

from __future__ import annotations

from typing import Final

from scripts.research.model_learning import PROTECTED_SPANS

PAUSE_DECISION_DATE: Final[str] = "2026-09-14"

PROVENANCE: Final[tuple[str, ...]] = (
    "裁定",
    "裁定（推奨）",
    "裁定から導出",
    "既存規則",
    "起草",
    "記録用",
)

#: `(key, token, provenance)`. Paused is not closed, and is not a claim about FX.
STATUSES: Final[tuple[tuple[str, str, str], ...]] = (
    ("programme", "FX_SPOT_ACTIVE_ALPHA_RESEARCH_PAUSED", "記録用"),
    (
        "track_1_continuous_currency_portfolio",
        "CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        "裁定",
    ),
    ("efficiency_bundle", "TURNOVER_REDUCTION_MECHANISM_SUPPORTED", "裁定"),
    ("track_3_event_volatility_overlay_of_480", "NOT_STARTED_BASE_EDGE_REQUIRED", "裁定"),
    ("complex_ml", "NOT_AUTHORISED_NO_POSITIVE_BASE_EVIDENCE", "記録用"),
    (
        "post_hoc_currency_reversal_observation",
        "POST_HOC_EXPLORATORY_NON_DECISION_BEARING",
        "裁定",
    ),
    (
        "tail_policy_prospective",
        "TAIL_CONCENTRATION_HARD_KILL_DEMOTED_TO_ADVERSARIAL_DIAGNOSTIC",
        "裁定（推奨）",
    ),
)
NOT_CLAIMED: Final[tuple[str, ...]] = ("FX_HAS_NO_EDGE", "ALPHA_SUPPORTED")


def status(key: str) -> str:
    for name, token, _ in STATUSES:
        if name == key:
            return token
    raise KeyError(key)


#: `(token, provenance)`.
PRINCIPLES: Final[tuple[tuple[str, str], ...]] = (
    ("EFFICIENCY_CANNOT_RESCUE_NEGATIVE_EXPECTED_RETURN", "裁定"),
    ("COMPLEXITY_REQUIRES_POSITIVE_BASE_EVIDENCE", "記録用"),
    ("A_FAILED_RULE_IS_NOT_AN_INVERTED_RULE", "既存規則"),
)

#: `(prohibition, provenance)` — ways a negative base result may not be rescued.
PROHIBITED_RESCUES: Final[tuple[tuple[str, str], ...]] = (
    ("event filter による救済", "裁定"),
    ("volatility filter による救済", "裁定"),
    ("regime filter による救済", "裁定"),
    ("horizon 変更による救済", "裁定"),
    ("post-hoc の通貨レベル reversal 観察（H-024）の再事前登録", "裁定"),
    ("閉鎖・隣接 family の符号反転", "裁定から導出"),
    ("leverage・vol target の変更による救済", "既存規則"),
    ("turnover・コスト効率の改善を alpha として扱うこと", "裁定から導出"),
)

#: `(model family, provenance)` — not authorised.
COMPLEX_ML_NOT_AUTHORISED: Final[tuple[tuple[str, str], ...]] = (
    ("LightGBM expansion", "裁定"),
    ("nonlinear ML", "裁定"),
    ("HMM", "裁定"),
    ("neural networks", "裁定"),
    ("representation learning", "裁定"),
    ("complex ensemble", "裁定"),
)

#: `(diagnostic, provenance)` — the minimum adversarial tail diagnostics a resumed
#: study reports. The decision's list breaks off at "temporal co"; the word is not
#: known, so that item and everything after it is drafted.
TAIL_DIAGNOSTICS: Final[tuple[tuple[str, str], ...]] = (
    ("top 1 day contribution", "裁定"),
    ("top 5 days contribution", "裁定"),
    ("top 10 days contribution", "裁定"),
    ("largest loss days", "裁定"),
    ("top days 除外後の符号", "裁定"),
    ("「temporal co…」（語は未確定: concentration / consistency / correlation 等）", "起草"),
    ("top / worst days の通貨・pair 集中", "起草"),
    ("top days と予定イベントの重なり", "起草"),
    ("日次歪度・超過尖度", "起草"),
    ("±3 robust σ 内の日の収益", "起草"),
)

#: `(activity, provenance)` — stopped until an explicit decision to resume. Rows
#: awaiting confirmation (`起草`, `裁定から導出`) bind provisionally until they are
#: confirmed; the stricter reading applies.
PAUSED_ACTIVITIES: Final[tuple[tuple[str, str], ...]] = (
    ("新しい alpha 探索（FX spot active-alpha research）", "裁定"),
    ("新しい alpha 仮説の事前登録（seen data・新しい外部データのどちらでも）", "起草"),
    ("seen data 上の alpha 目的の実行", "既存規則"),
    ("Track 3 overlay（#480 の event / volatility exposure overlay）", "裁定"),
    ("complex ML", "裁定"),
    (
        "停止中の track（#480 の Track 3 overlay、complex ML など）の実装や学習 pipeline の作成"
        "（市場データを使うかどうかを問わない）",
        "起草",
    ),
    (
        "停止中の track の部品を「engineering」として作り seen data で検証すること"
        "（方向を持たない volatility 予測器、event anchor、overlay 部品など）",
        "起草",
    ),
    ("コスト・band・netting を測り直して閉じた判定の net を再計算すること", "起草"),
    ("commit 済み artefact を再分析して新しい alpha の主張を導くこと", "起草"),
    ("Red 承認なしの fresh pool・forward epoch の読み取り", "既存規則"),
    ("paper-forward、demo / live 注文、broker 認証 API", "既存規則"),
    ("閉鎖・隣接 family の再事前登録や救済", "裁定から導出"),
)

#: `(activity, provenance)` — continues while paused and changes no research
#: state. A row awaiting confirmation never widens what is permitted.
CONTINUING_ACTIVITIES: Final[tuple[tuple[str, str], ...]] = (
    ("既存記録の保守（誤りの訂正、リンク・SHA の更新）", "起草"),
    ("テスト・lint・CI の保守", "起草"),
    (
        "市場データの読み取りも alpha の主張も伴わず、停止中の track の実装でもない engineering",
        "起草",
    ),
)

#: `(id, condition, provenance)`. RC-2..RC-4 are ordering rules for the work after
#: a resumption, not preconditions that would have to be met while paused.
RESUMPTION_CONDITIONS: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "RC-1",
        "実データの読み取りや実行を伴う再開は、operation・span・pairs・timeframe・承認 head を"
        "名指しした Human + ChatGPT の明示の承認を実行前に要する。"
        "記録された status・gate・文書・この表の条件がすべて揃ったことはそれに代わらない",
        "既存規則",
    ),
    (
        "RC-2",
        "再開後の順序: 正の base expected-return source を事前登録した検定で先に確立し、"
        "efficiency 機構・overlay・複雑さはその後にしか載せない",
        "裁定から導出",
    ),
    (
        "RC-3",
        "再開後の順序: #480 の Track 3 overlay は正の base edge を持つ core にのみ適用し、"
        "救済には使わない",
        "裁定から導出",
    ),
    (
        "RC-4",
        "再開後の順序: complex ML は、単純な architecture の正の base evidence が"
        "ある場合にのみ検討する",
        "裁定から導出",
    ),
    (
        "RC-5",
        "仮説は ledger の閉鎖 family と隣接 family の外にあり、"
        "novelty boundary を結果を見る前に書く。post-hoc 観察は昇格しない。"
        "隣接 = 同じ単位（通貨または pair）で、過去リターンに基づく同じ信号を "
        "horizon・符号・閾値だけ変えたもの",
        "起草",
    ),
    (
        "RC-6",
        "seen data の見直しではなく新しい情報に基づく: 独立な情報源、蓄積した forward data、"
        "または完全凍結した候補に対する fresh pool の one-shot 使用（それ自体の Red 承認下）。"
        "Track A の結果は再開決定の根拠にならない",
        "起草",
    ),
    (
        "RC-7",
        "結果を読む前に Feasibility Gate v2（#476、凍結済みの閾値、緩和なし）と signal-blind な "
        "capacity・search budget を計算して通す",
        "起草",
    ),
    (
        "RC-8",
        "tail concentration は hard kill ではなく adversarial diagnostic として報告する",
        "裁定（推奨）",
    ),
    (
        "RC-9",
        "読み取りを伴わない再開（新しい仮説の事前登録の作成など）を含め、一時停止の解除は"
        "仮説を名指しした Human + ChatGPT の明示の決定による",
        "裁定から導出",
    ),
    (
        "RC-10",
        "tail concentration の降格は、tail 条項も発火して閉じた family（H-021、H-022 など）を"
        "再び開かない",
        "裁定から導出",
    ),
)

#: The protected data as it stands at the pause, copied from the one authority.
PROTECTED_DATA_AT_PAUSE: Final[dict[str, str]] = {
    name: block["status"] for name, block in PROTECTED_SPANS.items()
}

#: Merged records of the phases that led here.
MERGES: Final[dict[int, str]] = {
    478: "a0780e3",
    479: "3b4d0a9",
    480: "3bbb7f5",
    481: "e13dba2",
    482: "a98fbc6",
}

#: Research PRs whose results are not on master and so are cited for nothing.
UNMERGED_RESEARCH_PRS: Final[tuple[int, ...]] = (473,)

#: Ledger entries whose status was OPEN when the programme paused. This record
#: does not change their status text; none is an expected-return source, and none
#: is a basis for resuming without a new decision.
OPEN_LEDGER_ENTRIES_AT_PAUSE: Final[tuple[str, ...]] = ("H-011", "H-015", "H-018", "H-019")


__all__ = [
    "COMPLEX_ML_NOT_AUTHORISED",
    "CONTINUING_ACTIVITIES",
    "MERGES",
    "NOT_CLAIMED",
    "OPEN_LEDGER_ENTRIES_AT_PAUSE",
    "PAUSED_ACTIVITIES",
    "PAUSE_DECISION_DATE",
    "PRINCIPLES",
    "PROHIBITED_RESCUES",
    "PROTECTED_DATA_AT_PAUSE",
    "PROVENANCE",
    "RESUMPTION_CONDITIONS",
    "STATUSES",
    "TAIL_DIAGNOSTICS",
    "UNMERGED_RESEARCH_PRS",
    "status",
]
