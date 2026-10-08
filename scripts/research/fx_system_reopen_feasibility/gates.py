# ruff: noqa: E501 -- governance prose
"""P1 / P2 の gate と、H / G の選択の規則（裁定 `fx_system_architecture_ruling_2026_10.md`）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

#: 一度限りの HOLD の例外が及ぶ範囲（P3 以降には及ばない）
EXCEPTION_SCOPE: Final[frozenset[str]] = frozenset({"P1", "P2"})
UNAPPROVED_PHASES: Final[frozenset[str]] = frozenset({"P3", "P4", "P5", "P6"})
AUTHORITATIVE_STATE: Final[str] = "FXID_LONG_TERM_HOLD_NO_JUSTIFIED_ALPHA_CYCLE"
G4_SYSTEM_SHARPE: Final[float] = 1.0
#: REOPEN の提案は実行の許可ではない
REOPEN_PROPOSAL_GRANTS_EXECUTION: Final[bool] = False


def phase_allowed(phase: str) -> bool:
    return phase in EXCEPTION_SCOPE


def p2_allowed(p1_verdict: str) -> bool:
    """P2 は P1 が PASS の場合だけ。"""
    return p1_verdict == "PASS"


@dataclass(frozen=True)
class PipelineResult:
    """P2 の 1 つの architecture の結果（合成の帰無と対立仮説）。"""

    fwer: float
    fwer_ci_upper: float
    power_by_alternative: dict[str, float]
    search_dof: int


@dataclass(frozen=True)
class GCriterion:
    """G を H より優れると判断する基準（P2 の事前登録で固定する）。"""

    fwer_cap: float = 0.10
    min_power_gain: float = 0.10
    min_share_of_alternatives_improved: float = 0.5
    min_power_gain_per_extra_dof: float = 0.02


def choose_architecture(h: PipelineResult, g: PipelineResult, c: GCriterion) -> str:
    """事前の基準を全て満たす時だけ G。それ以外は H（既定）。

    **基準の値（GCriterion）は placeholder で、将来の P2 の事前登録で、出力の前に改めて固定する**。
    """
    # 同じ対立仮説の集合で比べる
    if set(g.power_by_alternative) != set(h.power_by_alternative) or not g.power_by_alternative:
        return "H"
    # FWER: G の CI の上端が上限を超える、または H の CI の上端より悪いなら H
    if g.fwer_ci_upper > c.fwer_cap or g.fwer_ci_upper > h.fwer_ci_upper:
        return "H"
    gains = {
        k: g.power_by_alternative[k] - h.power_by_alternative[k] for k in g.power_by_alternative
    }
    # どこかの対立仮説で大きく検出力を失うなら H
    if min(gains.values()) <= -c.min_power_gain:
        return "H"
    improved = [k for k, v in gains.items() if v >= c.min_power_gain]
    if len(improved) / len(gains) < c.min_share_of_alternatives_improved:
        return "H"
    extra_dof = g.search_dof - h.search_dof
    median_gain = float(sorted(gains.values())[len(gains) // 2])
    if extra_dof > 0 and median_gain / extra_dof < c.min_power_gain_per_extra_dof:
        return "H"
    return "G"


def final_classification(p1_verdict: str, p2_passed: bool | None) -> str:
    """指示 §32 の分類。"""
    if p1_verdict != "PASS":
        return "FAST-A NO_REOPEN_JUSTIFICATION_COMPONENT_SUPPLY_INSUFFICIENT"
    if not p2_passed:
        return "FAST-B COMPONENT_SUPPLY_EXISTS_BUT_PIPELINE_NOT_DECISION_GRADE"
    return "FAST-C REOPEN_REVIEW_JUSTIFIED_BUT_REAL_DATA_NOT_YET_APPROVED"
