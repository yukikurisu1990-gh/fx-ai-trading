"""EVEstimator and CostModel domain interfaces and DTOs (D3 §2.4.2–2.4.3).

EVEstimator computes expected value after cost.
CostModel computes cost components for a trading intent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from fx_ai_trading.domain.strategy import StrategySignal

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Cost:
    """Cost breakdown for a trade (D3 §2.4.3).

    total = spread + slippage_expected + commission + swap_rate_per_day (× holding_days)
    """

    spread: float
    slippage_expected: float
    commission: float
    swap_rate_per_day: float
    total: float


@dataclass(frozen=True)
class EVEstimate:
    """Output of EVEstimator.estimate() (D3 §2.4.2).

    Invariant: value = p_win * avg_win - (1 - p_win) * avg_loss - cost_total
    """

    value: float
    confidence_interval: tuple[float, float]
    components: dict


# ---------------------------------------------------------------------------
# Interfaces (Protocol)
# ---------------------------------------------------------------------------


class CostModel(Protocol):
    """Computes cost components for a trading intent (D3 §2.4.3).

    Side effects: none.
    Idempotent: deterministic for fixed inputs.
    """

    def compute(self, instrument: str, intent: object) -> Cost:
        """Return the Cost for *intent* on *instrument*.

        intent type is TradingIntent (imported at runtime to avoid circular deps).
        """
        ...


class EVEstimator(Protocol):
    """Estimates expected value after cost (D3 §2.4.2).

    Invariant: value = p_win * avg_win - (1 - p_win) * avg_loss - cost_total
    Side effect: writes to ev_breakdowns (via evaluation framework).
    Idempotent: deterministic for fixed inputs.
    """

    def estimate(self, signal: StrategySignal, cost: Cost) -> EVEstimate:
        """Return EVEstimate for the given signal and cost."""
        ...
