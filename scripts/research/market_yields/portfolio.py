"""A currency book closed inside the tradable universe.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The Track 1 execution layer is written for the eight-currency cross-section, and
#485 measured what that does to a five-currency track: the weights are demeaned
over eight, the no-trade band picks its counter-leg from all eight, and a binding
cap spills a whole slot onto a currency with no signal. Exposure appeared on
AUD, CHF and NZD on 70% of days.

This module keeps every primitive of that layer — vol-normalised or linear
mapping, leading-factor neutralisation, capped sum-zero weights, the no-trade
band, partial rebalance, charged cost on the traded delta, pair routing, vol
targeting — and closes all of them inside the universe actually observed:

* the cross-section is the universe, so demeaning and neutralisation never reach
  a currency the track cannot see;
* routing uses only the pairs whose **both** legs are in the universe, so the
  implemented book is tradable as it stands;
* nothing outside the universe can receive weight, by construction rather than
  by an exact zero cancelling.

It is the same engineering layer, not a new one: Track 1's alpha model is not
here, and no parameter of the layer is tuned.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.continuous_portfolio import PAIR_ROUNDTRIP_BP, construction
from scripts.research.model_learning import PAIRS_20

#: The book's free choices, all declared. Same fields as the reused layer.
BookConfig = construction.BookConfig


def tradable_pairs(universe: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    """Pairs of `PAIRS_20` whose both legs are in the universe."""
    inside = set(universe)
    return tuple(p for p in PAIRS_20 if set(p.split("_")) <= inside)


def split_map(universe: tuple[str, ...] | list[str]) -> np.ndarray:
    """`(pairs x currencies)` equal-split routing, over the tradable pairs only.

    Currency `c` is carried by the universe pairs that contain it, so one unit of
    `x_c` is `1/n_c` of pair notional on each of them — the same construction as
    the reused layer, with the pair set restricted.
    """
    currencies = list(universe)
    pairs = tradable_pairs(currencies)
    counts = {c: sum(c in pair.split("_") for pair in pairs) for c in currencies}
    missing = [c for c, n in counts.items() if n == 0]
    if missing:
        raise ValueError(f"no tradable pair carries {missing}")
    matrix = np.zeros((len(pairs), len(currencies)))
    for row, pair in enumerate(pairs):
        base, quote = pair.split("_")
        matrix[row, currencies.index(base)] = 1.0 / counts[base]
        matrix[row, currencies.index(quote)] = -1.0 / counts[quote]
    return matrix


@dataclass(frozen=True, slots=True)
class Routing:
    """What the universe implies for routing, reported rather than assumed."""

    universe: tuple[str, ...]
    pairs: tuple[str, ...]
    pair_gross_per_unit_currency_gross: float
    connected: bool


def routing_profile(universe: tuple[str, ...] | list[str], samples: int = 4000) -> Routing:
    """Signal-free: how much pair notional one unit of currency gross costs here."""
    currencies = tuple(universe)
    pair_map = split_map(currencies)
    rng = np.random.default_rng(20260918)
    draws = rng.standard_normal((samples, len(currencies)))
    ratios = []
    for row in draws:
        weights = construction.capped_weights(row, 0.25)
        gross = float(np.abs(weights).sum())
        if gross > 0:
            ratios.append(float(np.abs(pair_map @ weights).sum()) / gross)
    #: the routing graph must connect the universe, or some sum-zero book is untradable
    degrees = {c: sum(c in p.split("_") for p in tradable_pairs(currencies)) for c in currencies}
    return Routing(
        universe=currencies,
        pairs=tradable_pairs(currencies),
        pair_gross_per_unit_currency_gross=round(float(np.mean(ratios)), 4),
        connected=all(degrees.values()) and len(tradable_pairs(currencies)) >= len(currencies) - 1,
    )


def run_book(
    config: BookConfig,
    mu: pd.DataFrame,
    excess: pd.DataFrame,
    *,
    universe: tuple[str, ...] | list[str],
    days_per_year: float = 252.0,
    cost_multiple: float | None = None,
) -> dict[str, Any]:
    """One book, closed inside `universe`. Mirrors `construction.run_book` otherwise.

    `mu` is `day x currency` over the universe, one row per decision day; `excess`
    is the daily currency excess-return panel. Everything used on day `t` comes
    from rows `<= t`, and the exposure chosen on `t` earns the return of `t+1`.
    """
    currencies = list(universe)
    if list(mu.columns) != currencies:
        mu = mu[currencies]
    returns = excess[currencies]
    index = returns.index
    positions = {day: index.get_loc(day) for day in mu.index}
    locations = np.array(list(positions.values()), dtype=int)
    if len(locations) and not np.array_equal(
        locations, np.arange(locations[0], locations[0] + len(locations))
    ):
        raise ValueError("mu must cover a contiguous run of the return calendar")
    if cost_multiple is not None:
        config = replace(config, cost_multiple=cost_multiple)
    pair_map = split_map(currencies)
    mapping = construction.MAPPINGS[config.mapping]
    targeter = (
        construction.VolTargeter(config.vol_target, config.max_leverage, config.leverage_hysteresis)
        if config.vol_target is not None
        else None
    )
    held = np.zeros(len(currencies))
    exposure_prev = np.zeros(len(currencies))

    rows: list[dict[str, Any]] = []
    for day in mu.index:
        loc = positions[day]
        if loc + 1 >= len(index):
            break
        history = returns.iloc[: loc + 1].to_numpy()
        sigma = np.nanstd(history[-config.sigma_window :], axis=0, ddof=0)
        raw = mapping(mu.loc[day].to_numpy(dtype=float), sigma)
        factor = construction.leading_factor(history[-config.factor_window :])
        scores = construction.neutralize(raw, factor) if config.neutralize_leading_factor else raw
        target = construction.capped_weights(scores, config.weight_cap)
        held = construction.band_rebalance(target, held, config.band)

        leverage = 1.0
        uncapped = float("nan")
        ex_ante = float("nan")
        if targeter is not None:
            window = history[-config.vol_window :]
            cov = np.cov(window, rowvar=False)
            ex_ante = float(np.sqrt(max(held @ cov @ held, 0.0) * days_per_year))
            leverage = targeter.update(ex_ante)
            uncapped = targeter.uncapped
        exposure = held * leverage
        delta = exposure - exposure_prev
        cost = construction.charged_cost(delta, config.cost_multiple)
        faithful = float(np.abs(pair_map @ delta).sum()) * (PAIR_ROUNDTRIP_BP / 2.0) / 10_000.0
        realised = returns.iloc[loc + 1].to_numpy()
        contributions = exposure * realised
        gross = float(contributions.sum())
        rows.append(
            {
                "decision_day": day,
                "pnl_day": index[loc + 1],
                "gross": gross,
                "cost": cost,
                "implementation_cost": faithful,
                "net": gross - cost,
                "currency_gross": float(np.abs(exposure).sum()),
                "pair_gross": float(np.abs(pair_map @ exposure).sum()),
                "one_way_traded": float(np.abs(delta).sum()),
                "leverage": leverage,
                "uncapped_leverage": uncapped,
                "held_max_weight": float(np.abs(held).max()),
                "held_gross": float(np.abs(held).sum()),
                "ex_ante_vol": ex_ante,
                "traded": bool(np.abs(delta).sum() > 0),
                **{f"x_{c}": float(v) for c, v in zip(currencies, exposure, strict=True)},
                **{f"pnl_{c}": float(v) for c, v in zip(currencies, contributions, strict=True)},
            }
        )
        exposure_prev = exposure

    frame = pd.DataFrame(rows).set_index("pnl_day")
    return {"config": config, "universe": tuple(currencies), "daily": frame}


#: What the repair is for, in one place the tests can read.
REPAIR: Final[dict[str, str]] = {
    "problem": (
        "the eight-currency layer demeans, neutralises, bands and routes over currencies a "
        "restricted track cannot observe, so weight appears on them"
    ),
    "fix": "every step is closed inside the observed universe, and routing uses only its pairs",
    "verdicts_unchanged": (
        "#485's fast five-day verdict stands as recorded; the repaired re-run is reported "
        "beside it as a robustness check, not as a replacement"
    ),
}


__all__ = [
    "REPAIR",
    "BookConfig",
    "Routing",
    "routing_profile",
    "run_book",
    "split_map",
    "tradable_pairs",
]
