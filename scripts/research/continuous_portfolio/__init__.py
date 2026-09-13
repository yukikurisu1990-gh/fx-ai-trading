"""Track 1 — a continuous currency-level expected-return portfolio.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

The question
------------

Can a small, continuously re-estimated expected-return vector over the eight G10
currencies — held as a factor-neutral book and rebalanced only by the difference
between target and held weights — produce cost-adjusted annual returns worth
allocating capital to, on the seen development corpus?

This is not `one signal = one trade`, and not `one prediction = one round trip`.
The economic unit is **realised portfolio turnover x executable cost per unit
traded**, and the success unit is **portfolio-level net Sharpe and annual return**
of the primary book on its own — never an increment over a baseline.

Authority and scope
-------------------

Authorised by the human + ChatGPT ruling of 2026-09-14 (Track 1 core + efficiency
bundle: pre-registration, implementation, seen-data development execution). Not
authorised: Track 3 overlays, any protected span (fresh pool, historical OOS,
dead window, forward epoch), broker-authenticated access, paper-forward
execution, demo or live orders, and non-linear models.

The strongest status reachable is `CONTINUOUS_CURRENCY_PORTFOLIO_DEVELOPMENT_CANDIDATE`,
which is a development verdict on `EXPLORATORY_SEEN_DATA` and never a
confirmation.
"""

from __future__ import annotations

from typing import Final

from scripts.research.feasibility.inventory import BASKET_ROUNDTRIP_BP, PAIR_ROUNDTRIP_BP

TRACK: Final[str] = "TRACK_1_CONTINUOUS_CURRENCY_PORTFOLIO"

CASE_A: Final[str] = "CONTINUOUS_CURRENCY_PORTFOLIO_DEVELOPMENT_CANDIDATE"
CASE_B: Final[str] = "MARGINAL_CONTINUOUS_PORTFOLIO_CANDIDATE"
CASE_C: Final[str] = "CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"

#: The ratio of pair one-way notional to currency one-way notional the cost
#: convention charges: Track 2's measured routing of an isolated
#: one-currency-against-basket position. `2.58 x 1.32 = 3.406`.
CHARGED_ROUTING_RATIO: Final[float] = round(BASKET_ROUNDTRIP_BP / PAIR_ROUNDTRIP_BP, 4)

#: One unit of currency-space one-way notional, traded under the charged routing,
#: costs half a basket round trip. Every realised trade in this package is charged
#: `sum|delta_currency| x CHARGED_ONE_WAY_BP`, and nothing else is charged.
CHARGED_ONE_WAY_BP: Final[float] = round(BASKET_ROUNDTRIP_BP / 2.0, 4)

#: Business interpretation of primary net Sharpe (human + ChatGPT ruling §20).
#: Capital-allocation bands, not a p-value gate.
ECONOMIC_BANDS: Final[tuple[tuple[float, str], ...]] = (
    (0.30, "economically_weak"),
    (0.50, "marginal"),
    (0.80, "potentially_useful"),
    (float("inf"), "strong_development_candidate"),
)


def economic_band(net_sharpe: float) -> str:
    """The ruling's band for a net Sharpe. Below zero is still `economically_weak`."""
    for ceiling, label in ECONOMIC_BANDS:
        if net_sharpe < ceiling:
            return label
    return ECONOMIC_BANDS[-1][1]


__all__ = [
    "BASKET_ROUNDTRIP_BP",
    "CASE_A",
    "CASE_B",
    "CASE_C",
    "CHARGED_ONE_WAY_BP",
    "CHARGED_ROUTING_RATIO",
    "ECONOMIC_BANDS",
    "PAIR_ROUNDTRIP_BP",
    "TRACK",
    "economic_band",
]
