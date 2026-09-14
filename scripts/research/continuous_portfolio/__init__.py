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

#: Track 2's measured routing: pair notional per unit of **one side** of an
#: isolated one-currency-against-the-other-seven position (`x_c = 1`, the rest
#: `-1/7`, so `sum|x| = 2`). `2.58 x 1.32 = 3.406`.
CHARGED_ROUTING_RATIO: Final[float] = round(BASKET_ROUNDTRIP_BP / PAIR_ROUNDTRIP_BP, 4)

#: The charge per unit of `sum|delta_currency|`, inherited from #480: 3.406 bp per
#: turnover unit `sum|delta| / 2`. It applies a one-side routing ratio to a
#: both-sides notional, so it is **about 2x** Track 2's measured routing for an
#: isolated position (opening it is charged 3.406 bp, the pair book pays 1.703)
#: and about **1.7x** the faithful equal-split cost of a random sum-zero trade.
#: The direction is conservative: it can only make a book look worse. The
#: faithful cost is reported beside it and never used for the verdict.
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
