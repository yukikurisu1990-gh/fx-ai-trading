"""Research reframing: which expected-return source to study next for G10 FX spot.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Authority: the Human + ChatGPT ruling of 2026-09-15 withdrew the programme-level
pause proposed after Track 1 and asked for a zero-based review of expected-return
sources, a profit-capacity assessment and at most three next research tracks.

Nothing in this package reads market data, fits a model or evaluates a strategy.
It holds a candidate catalogue, a prior-evidence map, signal-free capacity
arithmetic calibrated to the committed Track 1 record, and a declared ranking.
The market stays G10 FX spot; the fresh pool, the historical OOS slice, the dead
window and the forward epoch are not read for any purpose, including this one.
"""

from __future__ import annotations

from typing import Final

WORKFLOW_STATUS: Final[str] = "FX_SPOT_ACTIVE_ALPHA_RESEARCH_CONTINUES_REFRAMING_NEXT_EDGE_SOURCE"

#: Business interpretation of net Sharpe from the ruling (§15). Not a statistical gate.
ECONOMIC_BANDS: Final[tuple[tuple[float, str], ...]] = (
    (0.30, "low_value"),
    (0.50, "marginal"),
    (0.80, "meaningful"),
    (float("inf"), "attractive"),
)

#: The ruling's capacity target: net 5% a year at reasonable risk.
TARGET_NET_RETURN: Final[float] = 0.05


def economic_band(net_sharpe: float) -> str:
    for ceiling, label in ECONOMIC_BANDS:
        if net_sharpe < ceiling:
            return label
    return ECONOMIC_BANDS[-1][1]


__all__ = ["ECONOMIC_BANDS", "TARGET_NET_RETURN", "WORKFLOW_STATUS", "economic_band"]
