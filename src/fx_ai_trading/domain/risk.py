"""Risk domain interfaces and DTOs (D3 §2.5).

RiskManager: applies 4 constraints before order approval.
PositionSizer: calculates lot size based on risk %.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

# ---------------------------------------------------------------------------
# DTOs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Exposure:
    """Current portfolio exposure snapshot (D3 §2.5.2).

    per_currency: net exposure per currency code, e.g. {'EUR': 10000.0}
    per_direction: per-currency long/short breakdown
    total_risk_correlation_adjusted: correlation-weighted total risk
    concurrent_positions: count of open positions
    """

    per_currency: dict
    per_direction: dict
    total_risk_correlation_adjusted: float
    concurrent_positions: int


@dataclass(frozen=True)
class RiskAcceptResult:
    """Result of RiskManager.accept() (D3 §2.5.2).

    accepted: whether the trade is approved
    reject_reason: 6.16 taxonomy code, e.g. 'risk.max_concurrent_positions'
    exposure_after: projected exposure if accepted (only when accepted=True)
    """

    accepted: bool
    reject_reason: str | None = None
    exposure_after: Exposure | None = None


@dataclass(frozen=True)
class SizeResult:
    """Result of PositionSizer.size() (D3 §2.5.1).

    size_units=0 means no_trade (SizeUnderMin).
    size_units is always a multiple of min_lot or 0.
    """

    size_units: int
    reason: str | None = None


@dataclass(frozen=True)
class Instrument:
    """Reference data for a tradeable instrument (D3 §2.5.1 input)."""

    instrument: str
    base_currency: str
    quote_currency: str
    pip_location: int
    min_trade_units: int = 1


# ---------------------------------------------------------------------------
# Interfaces (Protocol)
# ---------------------------------------------------------------------------


class PositionSizer(Protocol):
    """Calculates trade size from account balance and risk % (D3 §2.5.1).

    Invariant: returned size_units is always a multiple of min_lot, or 0.
    """

    def size(
        self,
        account_balance: float,
        risk_pct: float,
        sl_pips: float,
        instrument: Instrument,
    ) -> SizeResult:
        """Return the appropriate lot size, or 0 if under minimum."""
        ...


class RiskManager(Protocol):
    """Applies portfolio-level risk constraints (D3 §2.5.2).

    Constraints (6.18 inherited):
      - Max concurrent positions
      - Single currency exposure cap
      - Net direction cap per currency
      - Total correlation-adjusted risk cap

    Invariant: accept() is called before orders row creation.
    Side effect: writes to risk_events.
    """

    def accept(self, decision: object, exposure: Exposure) -> RiskAcceptResult:
        """Evaluate MetaDecision against current exposure.

        decision type is MetaDecision (imported at runtime to avoid circular deps).
        """
        ...
