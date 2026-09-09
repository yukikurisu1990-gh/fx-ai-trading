"""Eight currency states, and the pair trades that implement them.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The lesson this module encodes
------------------------------

`H-003` ranked twenty pairs by relative strength, found a gross edge, and lost
**96% of it** to a time-series control: the ranking had been selecting net
currency exposure, mostly the dollar, and the "relative" part contributed almost
nothing. Twenty G10 pairs are not twenty assets. Triangular arithmetic leaves
about seven currency degrees of freedom, and any signal defined on pairs
decomposes into a currency signal whether the author intended it or not.

So this file does the decomposition first. A hypothesis produces a number for
each of eight **currencies**; the module turns that into pair weights, and the
pair weights are what pays the spread. The dollar factor cannot be smuggled in
as an effect because a demeaned currency signal has no room for it.

The construction, exactly
-------------------------

For currency `c`, its index return over a window is the mean of the signed pair
returns of every available pair containing it. A portfolio holding `s_c` of each
currency therefore returns `Σ_c s_c · r_c`, which rearranges into pair space as

    w_p = s_base(p) / n_base(p)  −  s_quote(p) / n_quote(p)

and that identity — not a resemblance, an identity — is what
`test_pair_weights_reproduce_the_currency_return` checks. Cost is charged on
`Σ_p |w_p|`, the notional actually traded, with each bar's own spread and mid.

Coverage is uneven and reported rather than hidden: `USD` appears in seven of the
twenty pairs, `CAD` and `NZD` in three. A currency held against three
counterparties is a noisier estimate of "against the world" than one held against
seven, and the breadth clause has to be read knowing that.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np

from scripts.research.clock_flow import CURRENCIES
from scripts.research.exploratory_m15 import PAIRS

#: currency -> the pairs containing it, with the sign that holding the pair gives.
LEGS: Final[dict[str, tuple[tuple[str, int], ...]]] = {
    currency: tuple(
        (pair, 1 if pair.split("_")[0] == currency else -1)
        for pair in PAIRS
        if currency in pair.split("_")
    )
    for currency in CURRENCIES
}

#: How many counterparties each currency is measured against. Uneven: see above.
COUNTERPARTIES: Final[dict[str, int]] = {c: len(legs) for c, legs in LEGS.items()}


def currency_returns(pair_returns: dict[str, float]) -> dict[str, float]:
    """Index return per currency, in whatever unit the pair returns arrived in.

    A pair missing from the mapping is dropped from that currency's mean rather
    than treated as zero: a zero would pull the index toward no-change and make a
    gap look like a fact about the market.
    """
    out: dict[str, float] = {}
    for currency, legs in LEGS.items():
        values = [sign * pair_returns[pair] for pair, sign in legs if pair in pair_returns]
        out[currency] = float(np.mean(values)) if values else float("nan")
    return out


def neutralise(signal: dict[str, float]) -> dict[str, float]:
    """Demean across the currencies that have a signal, then scale gross to 2.

    Demeaning is what makes the portfolio carry no net exposure to the common
    factor; scaling to a gross of two makes every cell's return one long unit
    against one short unit, so cells are comparable and a cell cannot look large
    by holding more.
    """
    live = {c: v for c, v in signal.items() if v is not None and np.isfinite(v)}
    if not live:
        return {}
    centre = float(np.mean(list(live.values())))
    centred = {c: v - centre for c, v in live.items()}
    gross = float(sum(abs(v) for v in centred.values()))
    if gross == 0.0:
        return {}
    return {c: 2.0 * v / gross for c, v in centred.items()}


def pair_weights(signal: dict[str, float]) -> dict[str, float]:
    """Pair-space weights implementing a currency-space position.

    `w_p = s_base/n_base − s_quote/n_quote`, so that `Σ_p w_p · r_p` is exactly
    `Σ_c s_c · r_c`.
    """
    weights: dict[str, float] = {}
    for pair in PAIRS:
        base, quote = pair.split("_")
        value = 0.0
        if base in signal:
            value += signal[base] / COUNTERPARTIES[base]
        if quote in signal:
            value -= signal[quote] / COUNTERPARTIES[quote]
        if value != 0.0:
            weights[pair] = value
    return weights


def portfolio(
    signal: dict[str, float],
    pair_returns: dict[str, float],
    pair_costs: dict[str, float],
) -> dict[str, Any]:
    """Gross, cost and net for one event, all in the unit the inputs arrived in.

    `cost` is the round trip on the notional actually traded — one spread plus
    half a pip per pair, weighted by `|w_p|`. It is charged once, because the
    window is opened and closed inside the cell.
    """
    weights = pair_weights(signal)
    gross = float(sum(w * pair_returns[p] for p, w in weights.items() if p in pair_returns))
    cost = float(sum(abs(w) * pair_costs[p] for p, w in weights.items() if p in pair_costs))
    return {
        "gross_bp": gross,
        "cost_bp": cost,
        "net_bp": gross - cost,
        "traded_notional": float(sum(abs(w) for w in weights.values())),
        "n_pairs": len(weights),
    }


#: There is deliberately no `window_returns` here. One existed, charging the full
#: round trip at the entry bar, while `frontier.PanelArrays.window` charged half
#: at each end — two cost models in one package, with opposite docstrings, and
#: the entry-only one had no caller and no test. Whichever a later stage picked
#: up, the hurdle it would be judged against was built with the other.
#: `frontier.PanelArrays.window` is the one.


def per_currency_contribution(
    signal: dict[str, float], currency_return: dict[str, float]
) -> dict[str, float]:
    """What each currency contributed to the gross. Used for the breadth clause."""
    return {
        c: float(s * currency_return[c])
        for c, s in signal.items()
        if c in currency_return and np.isfinite(currency_return[c])
    }


__all__ = [
    "COUNTERPARTIES",
    "LEGS",
    "currency_returns",
    "neutralise",
    "pair_weights",
    "per_currency_contribution",
    "portfolio",
]
