"""PromotionGate — challenger-to-champion promotion evaluator (Phase 9.8).

Pure stateless evaluator: no DB access, no clock.
Promotion criteria (all must pass):
  1. paper_days  >= criteria.min_days    (sufficient observation window)
  2. trade_count >= criteria.min_trades  (statistical significance)
  3. sharpe      >= champion.sharpe + criteria.sharpe_margin  (beat baseline)
  4. max_drawdown <= champion.max_drawdown * criteria.max_dd_ratio  (risk budget)

When no champion exists, use NO_CHAMPION_STATS (sharpe=0, dd=inf) so that
criteria 3 requires sharpe >= sharpe_margin and criterion 4 always passes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class PromotionCriteria:
    """Thresholds for the promotion gate."""

    min_days: int = 14
    min_trades: int = 100
    sharpe_margin: float = 0.2
    max_dd_ratio: float = 1.2


@dataclass(frozen=True)
class ChallengerStats:
    """Paper-run performance metrics for a challenger model."""

    model_id: str
    training_run_id: str
    paper_days: int
    trade_count: int
    sharpe: float
    max_drawdown: float


@dataclass(frozen=True)
class ChampionStats:
    """Current champion performance baseline."""

    model_id: str
    training_run_id: str | None
    sharpe: float
    max_drawdown: float


@dataclass(frozen=True)
class PromotionDecision:
    """Output of PromotionGate.evaluate()."""

    promoted: bool
    reason: str
    criteria: dict[str, bool] = field(default_factory=dict)
    challenger_stats: ChallengerStats | None = None
    champion_stats: ChampionStats | None = None


# Sentinel used when no champion is yet established.
NO_CHAMPION_STATS = ChampionStats(
    model_id="none",
    training_run_id=None,
    sharpe=0.0,
    max_drawdown=math.inf,
)


class PromotionGate:
    """Evaluate whether a challenger should replace the current champion.

    Args:
        criteria: Override default PromotionCriteria thresholds.
    """

    def __init__(self, criteria: PromotionCriteria | None = None) -> None:
        self._criteria = criteria or PromotionCriteria()

    def evaluate(
        self,
        challenger: ChallengerStats,
        champion: ChampionStats,
    ) -> PromotionDecision:
        """Return PromotionDecision for *challenger* vs *champion*.

        All four criteria must pass for `promoted=True`.
        `reason` is 'all_criteria_met' on success, or a '|'-joined list
        of failed criterion names on rejection.
        """
        c = self._criteria

        dd_budget = (
            champion.max_drawdown * c.max_dd_ratio
            if math.isfinite(champion.max_drawdown)
            else math.inf
        )

        checks: dict[str, bool] = {
            "min_days": challenger.paper_days >= c.min_days,
            "min_trades": challenger.trade_count >= c.min_trades,
            "sharpe_margin": challenger.sharpe >= champion.sharpe + c.sharpe_margin,
            "max_dd_ratio": challenger.max_drawdown <= dd_budget,
        }

        promoted = all(checks.values())
        failed = [k for k, v in checks.items() if not v]
        reason = "all_criteria_met" if promoted else "|".join(failed)

        return PromotionDecision(
            promoted=promoted,
            reason=reason,
            criteria=checks,
            challenger_stats=challenger,
            champion_stats=champion,
        )


__all__ = [
    "NO_CHAMPION_STATS",
    "ChampionStats",
    "ChallengerStats",
    "PromotionCriteria",
    "PromotionDecision",
    "PromotionGate",
]
