"""Profit-architecture redesign — the market is fixed, the architecture is open.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

What this package is
--------------------

Every prior phase of this programme asked some version of "does an edge exist,
and can we prove it?". This one asks a different question, under instruction:

    Given everything the programme has measured, what systematic trading
    architecture over G10 FX spot could plausibly convert a small edge into a
    meaningful annual net profit — and what edge, breadth, turnover and leverage
    would it minimally require?

Nothing here estimates a signal, computes a return, or backtests anything. The
package contains **arithmetic and mechanics only**: a decomposition of the cost
conventions previous gates used, signal-free turnover mechanics for continuous
portfolios (synthetic weight processes, no market data), leverage and
return-translation tables built on the programme's own measured constants, and a
catalogue of twenty profit architectures assessed on declared structural fields.

The six distinctions the redesign instruction demands, and this package encodes:

    prediction frequency  != turnover
    signal                != trade
    trade                 != full round trip
    pair                  != independent bet
    small edge            != small annual profit, given breadth and utilization
    leverage              != edge

What it does not do
-------------------

* It does not reopen any adjudicated verdict. The closed families stay closed,
  and the gate audit in `cost_audit` is about what future evaluation should
  measure, not about relitigating what past evaluation concluded.
* It does not read any market data. The measured inputs are frozen constants
  imported from the modules that measured them, with their provenance named.
* It does not touch the fresh pool, the OOS slice, the dead window or the
  forward epoch, and it computes nothing a protected span could leak into.
"""

from __future__ import annotations

from typing import Final

from scripts.research.feasibility import MAX_PLAUSIBLE_GROSS_IR
from scripts.research.feasibility.inventory import BASKET_ROUNDTRIP_BP, PAIR_ROUNDTRIP_BP
from scripts.research.model_learning.role_gate import (
    MEASURED_ANNUAL_VOL_PER_GROSS_BP,
    MEASURED_VOL_RANGE_BY_SPAN_BP,
)

STATUS: Final[str] = "PROFIT_ARCHITECTURE_REDESIGN_ASSESSED"

TRADING_DAYS_PER_YEAR: Final[float] = 252.0

#: Measured annualised turnover of the four daily-updated books the
#: model-learning development run actually produced, in full-book round trips a
#: year. Provenance: `artifacts/research/model_learning/development.json`
#: (`annualised_turnover` per track). ⭐ These are the numbers that falsify the
#: "1 prediction = 1 round trip" convention: every one of these books updated its
#: target daily, and none of them turned over 252.
MEASURED_TURNOVER_RANKING_MODEL: Final[float] = 36.7
MEASURED_TURNOVER_TOP2_BOTTOM2: Final[float] = 49.4
MEASURED_TURNOVER_REGIME_MODEL: Final[float] = 89.9
MEASURED_TURNOVER_FILTERED_BOOK: Final[float] = 142.5

#: Effective independent directions, as this programme has measured them: 3.2 to
#: 6.5 across twenty pairs depending on window and statistic, and roughly four
#: across the eight-currency cross-section once the common factor is removed.
EFFECTIVE_CURRENCY_BREADTH_PER_DAY: Final[float] = 4.0

#: The fresh pool's length in years, from its manifest dates — used only for
#: power arithmetic about a future one-shot confirmation. The span itself is
#: never read.
FRESH_POOL_YEARS: Final[float] = 4.9

__all__ = [
    "BASKET_ROUNDTRIP_BP",
    "EFFECTIVE_CURRENCY_BREADTH_PER_DAY",
    "FRESH_POOL_YEARS",
    "MAX_PLAUSIBLE_GROSS_IR",
    "MEASURED_ANNUAL_VOL_PER_GROSS_BP",
    "MEASURED_TURNOVER_FILTERED_BOOK",
    "MEASURED_TURNOVER_RANKING_MODEL",
    "MEASURED_TURNOVER_REGIME_MODEL",
    "MEASURED_TURNOVER_TOP2_BOTTOM2",
    "MEASURED_VOL_RANGE_BY_SPAN_BP",
    "PAIR_ROUNDTRIP_BP",
    "STATUS",
    "TRADING_DAYS_PER_YEAR",
]
