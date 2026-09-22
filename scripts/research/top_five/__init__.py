# ruff: noqa: E501 -- freeze prose
"""2026-09-20 裁定が承認した **5 本一括 development cycle** の共通定義。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`PRODUCTION_READINESS_NOT_CLAIMED`.

Authority: `docs/governance/m15_adjudication_2026_09_19_and_09_20.md`。

**この cycle の目的は勝者を作ることではない。** どの種類の information source に
economic edge の兆候が残っているかを、**同一の framework で一気に地図化する**ことである。
したがって 5 本は互いに独立に、**1 本目の結果を見る前に全て凍結**される（裁定 §10）。

confirmation ではない。`development candidate discovery / comparative screening` である。
"""

from __future__ import annotations

from typing import Final

CYCLE: Final[str] = "TOP_FIVE_2026_09"

#: 本 cycle で許される per-track verdict（裁定 §48）。
OUTCOMES: Final[tuple[str, ...]] = (
    "STRONG_DEVELOPMENT_CANDIDATE",
    "MARGINAL_DEVELOPMENT_CANDIDATE",
    "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
    "DATA_NOT_DECISION_GRADE",
    "DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES",
)

#: 本 cycle 全体の status。5 本が終わったら **STOP** であり、6 本目へは進まない（裁定 §60）。
WORKFLOW_STATUS: Final[str] = "TOP_FIVE_FROZEN_AWAITING_EXECUTION"

#: 5 本が終わった後に自動で進んではいけない先（裁定 §53–§55, §64）。
FORBIDDEN_NEXT_STEPS: Final[tuple[str, ...]] = (
    "fresh pool / historical OOS / dead window / forward epoch の読み取り",
    "paid data の購入",
    "authenticated broker / demo / paper / live",
    "nonlinear ML の training",
    "multi-source portfolio の最適化",
    "6 本目の track",
)

#: 取引市場は動かない。G10 FX spot のままである（裁定 CORE PRINCIPLE）。
UNIVERSE: Final[tuple[str, ...]] = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")

__all__ = ["CYCLE", "FORBIDDEN_NEXT_STEPS", "OUTCOMES", "UNIVERSE", "WORKFLOW_STATUS"]
