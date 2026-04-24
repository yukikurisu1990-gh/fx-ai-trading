"""MetaDecider domain interface and DTOs (D3 §2.4.4).

MetaDecider runs Filter → Score → Select over StrategySignal candidates
and produces a single MetaDecision per cycle.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from fx_ai_trading.domain.strategy import StrategySignal

# ---------------------------------------------------------------------------
# Context / DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetaContext:
    """Contextual inputs for MetaDecider.decide()."""

    cycle_id: UUID
    account_id: str
    config_version: str
    correlation_threshold: float = 0.7
    currency_strength: dict[str, float] | None = None


@dataclass(frozen=True)
class NoTradeReason:
    """A single no-trade reason in the 6.16 taxonomy."""

    reason_code: str
    detail: str = ""


@dataclass(frozen=True)
class MetaDecision:
    """Output of MetaDecider.decide() (D3 §2.4.4).

    Invariant: no_trade == True  ↔  selected_instrument is None
    """

    meta_decision_id: UUID
    cycle_id: UUID
    no_trade: bool
    active_strategies: tuple[str, ...]
    regime_detected: bool
    filter_snapshot: dict
    score_snapshot: dict
    select_snapshot: dict
    score_contributions: tuple[dict, ...]
    concentration_warning: bool
    no_trade_reasons: tuple[NoTradeReason, ...] = ()
    selected_instrument: str | None = None
    selected_strategy_id: str | None = None
    selected_signal: str | None = None
    selected_tp: float | None = None
    selected_sl: float | None = None


# ---------------------------------------------------------------------------
# Interface (Protocol)
# ---------------------------------------------------------------------------


class MetaDecider(Protocol):
    """Filter → Score → Select consensus over strategy candidates (D3 §2.4.4).

    Idempotent: same candidates + same context → same MetaDecision.
    Side effects: writes to meta_decisions / pair_selection_runs /
                  pair_selection_scores (via evaluation framework).

    Failure modes:
      All candidates filtered → no_trade (with reasons)
      EV below threshold → no_trade
      No valid combination → no_trade
    """

    def decide(
        self,
        candidates: list[StrategySignal],
        context: MetaContext,
    ) -> MetaDecision:
        """Run 3-stage consensus and return a MetaDecision."""
        ...
