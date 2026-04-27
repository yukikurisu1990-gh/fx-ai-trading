"""ExposureComputer — derive portfolio Exposure from open positions.

Used by RiskManagerService.accept() (C1–C4 constraint check) before each
new position is opened.  Phase 1 §4.8.2 requires these four constraints:

  C1 concurrent_positions >= max_concurrent
  C2 per_currency[currency]        >= max_single_currency_exposure_pct
  C3 per_direction[currency][side] >= max_net_directional_exposure_pct
  C4 total_risk_correlation_adjusted >= total_risk_cap_pct

Computation strategy (MVP — risk-% based):
  Each open position is assumed to have consumed ``risk_pct`` % of the
  account (the configured per-trade risk).  This maps cleanly to the
  percentage thresholds used by the constraints and avoids the need for
  cross-currency FX rate conversions or correlation matrices at runtime.

  per_currency[base]           += risk_pct  (for each open position)
  per_currency[quote]          += risk_pct
  per_direction[base][side]    += risk_pct
  per_direction[quote][side]   += risk_pct
  total_risk_correlation_adjusted = 0.0  (simplified — C4 disabled for MVP)

This is intentionally conservative on the per-currency dimension (both
base and quote currencies are charged ``risk_pct``) and intentionally
lenient on total risk (C4 disabled) until a correlation matrix is
available.  With default thresholds (C2=30%, C3=40%) and risk_pct=1%,
the constraints fire when a single currency appears in ~30 simultaneous
positions — a soft guard against extreme concentration, not a hard
operational limit at small position counts.
"""

from __future__ import annotations

from fx_ai_trading.domain.risk import Exposure
from fx_ai_trading.domain.state import OpenPositionInfo


def compute_exposure(
    positions: list[OpenPositionInfo],
    risk_pct: float = 1.0,
) -> Exposure:
    """Build an Exposure snapshot from the current open position list.

    Args:
        positions: List of open positions from StateManager.open_position_details().
        risk_pct:  Per-trade risk % used when each position was sized
                   (default 1.0%).  Acts as the unit contribution for
                   per_currency and per_direction accounting.

    Returns:
        Exposure ready for RiskManagerService.accept().
    """
    per_currency: dict[str, float] = {}
    per_direction: dict[str, dict[str, float]] = {}

    for pos in positions:
        parts = pos.instrument.split("_")
        if len(parts) != 2:
            continue
        base, quote = parts

        for currency in (base, quote):
            per_currency[currency] = per_currency.get(currency, 0.0) + risk_pct
            if currency not in per_direction:
                per_direction[currency] = {}
            per_direction[currency][pos.side] = (
                per_direction[currency].get(pos.side, 0.0) + risk_pct
            )

    return Exposure(
        per_currency=per_currency,
        per_direction=per_direction,
        total_risk_correlation_adjusted=0.0,
        concurrent_positions=len(positions),
    )
