"""Track 1 — clock and institutional flow.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

The question
------------

Does a flow that the market's own institutions have pinned to a **wall-clock
moment** leave a conditional return large enough to survive a retail round trip?

Every hypothesis this programme has closed had the same shape: a state, or an
external signal, predicting a direction. This one has a different shape. The
signal is a *clock*, the mechanism is a *mandate* — funds that must transact at a
published benchmark rate, hedges that must be resized when the month closes,
value dates that must roll — and the counterparty is a dealer who knows the order
is coming and is inelastic about when it trades. Nothing in the twenty-one
hypotheses on the ledger tested it.

What is fixed here before anything runs
---------------------------------------

**The signs.** Each primary cell carries a direction derived from the mechanism,
written down in `CELLS` before the first read. A cell whose mechanism does not
name a direction is defined on a magnitude or a probability instead. Reading a
result and then choosing the sign is the failure this file exists to prevent.

**The unit.** Basis points of mid, per observation, through
`scripts.research.fxunits` — never pips, which are not comparable across pairs.

**The architecture.** Eight currency states, not twenty independent pairs. A
pair is an execution vehicle. `H-003` lost 96% of its gross to the dollar factor
by treating pairs as assets, and the construction here makes that impossible
rather than checking for it afterwards.
"""

from __future__ import annotations

from typing import Final

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

#: The eight G10 currencies the twenty-pair universe spans.
CURRENCIES: Final[tuple[str, ...]] = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")

#: M15 bars per hour, and the window every clock cell uses on both sides of its
#: moment. Sixty minutes is four bars: short enough that the flow is still the
#: dominant term, long enough that a single bar's noise does not decide the cell.
BARS_PER_HOUR: Final[int] = 4
WINDOW_BARS: Final[int] = 4

#: Draws for the dependence-preserving null. Signs are drawn **per event day**,
#: never per currency-day, so the cross-currency structure inside a day survives
#: every draw.
NULL_DRAWS: Final[int] = 2000
SEED: Final[int] = 20260910

FAMILYWISE_ALPHA: Final[float] = 0.05

#: A cell fails if its ten largest events carry more than half of its net.
TAIL_SHARE_CEILING: Final[float] = 0.50

#: Of the eight currencies, how many must carry the effect in the same direction
#: for the cell to be called broad rather than concentrated. Five of eight.
MIN_CURRENCY_BREADTH: Final[int] = 5

#: Below this many events on a deciding panel a cell is not adjudicated at all.
MIN_EVENTS_PER_DECIDING_PANEL: Final[int] = 60

__all__ = [
    "BARS_PER_HOUR",
    "CLASSIFICATION",
    "CLASSIFICATION_SECONDARY",
    "CURRENCIES",
    "FAMILYWISE_ALPHA",
    "MIN_CURRENCY_BREADTH",
    "MIN_EVENTS_PER_DECIDING_PANEL",
    "NULL_DRAWS",
    "SEED",
    "TAIL_SHARE_CEILING",
    "WINDOW_BARS",
]
