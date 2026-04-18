"""CostModelService — spread/slippage cost computation (D3 §2.4.3 / M9).

Implements the CostModel Protocol.

M9 scope (v0 heuristic):
  - Spread: per-instrument table with a safe default for unknowns.
  - Slippage: 0.5 × spread (heuristic).
  - Commission: 0.0 (paper mode — no real broker commission).
  - Swap: 0.0 (simplified for M9; Phase 7 adds overnight rate lookup).
  - intent parameter is accepted for Protocol compliance but unused in M9.

Phase 7: replace with real spread from broker tick / OANDA pricing stream.
"""

from __future__ import annotations

from fx_ai_trading.domain.ev import Cost

# Per-instrument typical spread in price units (major pairs, demo account).
# Phase 7: fetch from broker pricing stream instead of this table.
_SPREAD_TABLE: dict[str, float] = {
    "EUR_USD": 0.00015,
    "GBP_USD": 0.00020,
    "USD_JPY": 0.015,
    "USD_CHF": 0.00018,
    "AUD_USD": 0.00018,
    "USD_CAD": 0.00020,
    "NZD_USD": 0.00022,
    "EUR_GBP": 0.00018,
    "EUR_JPY": 0.020,
    "GBP_JPY": 0.030,
}

_DEFAULT_SPREAD = 0.00025


class CostModelService:
    """Heuristic cost model for M9 paper-mode pipeline (D3 §2.4.3).

    Args:
        spread_overrides: Optional per-instrument spread overrides (price units).
            Merged on top of the built-in table; useful for tests.
    """

    def __init__(
        self,
        spread_overrides: dict[str, float] | None = None,
    ) -> None:
        self._spreads = dict(_SPREAD_TABLE)
        if spread_overrides:
            self._spreads.update(spread_overrides)

    def compute(self, instrument: str, intent: object) -> Cost:
        """Return Cost for *instrument*.

        intent is accepted for Protocol compliance; unused in M9.
        total = spread + slippage + commission + swap (all components).
        """
        spread = self._spreads.get(instrument, _DEFAULT_SPREAD)
        slippage = spread * 0.5
        commission = 0.0
        swap = 0.0
        total = spread + slippage + commission + swap

        return Cost(
            spread=round(spread, 8),
            slippage_expected=round(slippage, 8),
            commission=round(commission, 8),
            swap_rate_per_day=round(swap, 8),
            total=round(total, 8),
        )
