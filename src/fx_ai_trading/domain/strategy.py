"""StrategyEvaluator domain interface and DTOs (D3 §2.4.1).

Strategy produces StrategySignal per instrument per cycle.
Must be pure-functional: no DB access inside evaluate().
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fx_ai_trading.domain.ev_contract import EV_UNIT_UNKNOWN
from fx_ai_trading.domain.feature import FeatureSet

# ---------------------------------------------------------------------------
# Context / DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StrategyContext:
    """Contextual inputs for strategy evaluation."""

    cycle_id: str
    account_id: str
    config_version: str


@dataclass(frozen=True)
class StrategySignal:
    """Output of StrategyEvaluator.evaluate() (D3 §2.4.1).

    signal: 'long' | 'short' | 'no_trade'
    enabled: False means the strategy is disabled (6.17); should not appear
             in MetaDecider candidates.
    ev_unit: unit/cost declaration for ev_before_cost / ev_after_cost
             (F8-F contract — see domain/ev_contract.py).  Only
             ``EV_UNIT_PIPS_POST_COST`` candidates are rankable by the
             Meta selector; anything else is rejected fail-closed.
             Defaults to ``EV_UNIT_UNKNOWN`` (non-comparable) so an
             emitter that forgets to declare its unit can never be
             ranked by accident.
    """

    strategy_id: str
    strategy_type: str
    strategy_version: str
    signal: str
    confidence: float
    ev_before_cost: float
    ev_after_cost: float
    tp: float
    sl: float
    holding_time_seconds: int
    enabled: bool
    ev_unit: str = EV_UNIT_UNKNOWN


# ---------------------------------------------------------------------------
# Interface (Protocol)
# ---------------------------------------------------------------------------


class StrategyEvaluator(Protocol):
    """Per-strategy signal generator (D3 §2.4.1).

    Decision 2.4.1-1: StrategyEvaluator is pure-functional.
    DB writes (strategy_signals) are done by the evaluation framework,
    not inside evaluate().

    Invariant: disabled strategies (6.17) are pre-filtered by the engine;
    evaluate() is never called for them.
    """

    def evaluate(
        self,
        instrument: str,
        features: FeatureSet,
        context: StrategyContext,
    ) -> StrategySignal:
        """Generate a signal for *instrument* given *features*."""
        ...
