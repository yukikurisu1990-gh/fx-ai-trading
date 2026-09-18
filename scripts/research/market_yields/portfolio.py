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
* **the returns are rebuilt from those same pairs**, so the reported P&L is the
  P&L of the routed book. Slicing five columns out of the eight-currency panel
  would not do it: there, CAD's return still carries `AUD_CAD` and JPY's carries
  `CHF_JPY`, so a book holding no AUD would still be paid as if it did -- about
  8% of the implied spot exposure. `universe_panel` closes that;
* nothing outside the universe can receive weight, by construction rather than
  by an exact zero cancelling.

The identity is exact for a sum-zero book: with `M[p, c] = sign / legs(c)`,
`x . r = sum_p R_p (M x)_p`, and the demeaning changes nothing because the
weights already sum to zero.

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


def universe_panel(
    panel: dict[str, pd.DataFrame], universe: tuple[str, ...] | list[str]
) -> pd.DataFrame:
    """Daily currency excess returns built from the universe's own pairs.

    `panel` is `corpus.currency_panel()`, whose `pair_returns` came through the
    guarded readers. Nothing is re-read here; the currency definition is rebuilt so
    that it uses only pairs the restricted book can trade.
    """
    currencies = list(universe)
    pairs = tradable_pairs(currencies)
    returns = panel["pair_returns"][list(pairs)]
    rebuilt = pd.DataFrame(index=returns.index, columns=currencies, dtype=float)
    for currency in currencies:
        signed = [
            returns[pair] if currency == pair.split("_")[0] else -returns[pair]
            for pair in pairs
            if currency in pair.split("_")
        ]
        rebuilt[currency] = pd.concat(signed, axis=1).mean(axis=1)
    return rebuilt.sub(rebuilt.mean(axis=1), axis=0)


def identity_residual(
    panel: dict[str, pd.DataFrame], universe: tuple[str, ...] | list[str], weights: np.ndarray
) -> float:
    """`|x . r - (M x) . R|` for one sum-zero weight vector: it must be zero."""
    currencies = list(universe)
    pairs = tradable_pairs(currencies)
    excess = universe_panel(panel, currencies)
    routed = split_map(currencies) @ weights
    direct = excess.to_numpy() @ weights
    through_pairs = panel["pair_returns"][list(pairs)].to_numpy() @ routed
    return float(np.nanmax(np.abs(direct - through_pairs)))


@dataclass(frozen=True, slots=True)
class Routing:
    """What the universe implies for routing, reported rather than assumed."""

    universe: tuple[str, ...]
    pairs: tuple[str, ...]
    pair_gross_per_unit_currency_gross: float
    connected: bool
    mean_gross: float = float("nan")
    share_days_gross_below_one: float = float("nan")
    largest_currency_share_of_gross_p95: float = float("nan")


def _connected(universe: tuple[str, ...]) -> bool:
    """Union-find over the tradable pairs: a split graph cannot express every book."""
    parent = {c: c for c in universe}

    def find(c: str) -> str:
        while parent[c] != c:
            parent[c] = parent[parent[c]]
            c = parent[c]
        return c

    for pair in tradable_pairs(universe):
        first, second = (find(x) for x in pair.split("_"))
        if first != second:
            parent[first] = second
    return len({find(c) for c in universe}) == 1


def routing_profile(
    universe: tuple[str, ...] | list[str], weight_cap: float = 0.25, samples: int = 4000
) -> Routing:
    """Signal-free: how much pair notional one unit of currency gross costs here.

    Also reports how often the cap binds hard enough to hold gross below one, which
    on a small cross-section is not the rare event it is on eight names.
    """
    currencies = tuple(universe)
    pair_map = split_map(currencies)
    rng = np.random.default_rng(20260918)
    draws = rng.standard_normal((samples, len(currencies)))
    ratios, grosses, tops = [], [], []
    for row in draws:
        weights = construction.capped_weights(row, weight_cap)
        gross = float(np.abs(weights).sum())
        if gross > 0:
            ratios.append(float(np.abs(pair_map @ weights).sum()) / gross)
            grosses.append(gross)
            tops.append(float(np.abs(weights).max() / gross))
    return Routing(
        universe=currencies,
        pairs=tradable_pairs(currencies),
        pair_gross_per_unit_currency_gross=round(float(np.mean(ratios)), 4),
        connected=_connected(currencies),
        mean_gross=round(float(np.mean(grosses)), 4),
        share_days_gross_below_one=round(float(np.mean(np.array(grosses) < 0.999)), 4),
        largest_currency_share_of_gross_p95=round(float(np.quantile(tops, 0.95)), 4),
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
    if config.drawdown_governor:
        #: the reused layer applies a governor scale this module does not implement;
        #: ignoring it would change every number silently, so it is refused instead
        raise NotImplementedError("the drawdown governor is not implemented here")
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
        at_cap = False
        if targeter is not None and len(history) > 1:
            window = history[-config.vol_window :]
            cov = np.cov(window, rowvar=False)
            ex_ante = float(np.sqrt(max(held @ cov @ held, 0.0) * days_per_year))
            leverage = targeter.update(ex_ante)
            uncapped = targeter.uncapped
            at_cap = bool(np.isfinite(uncapped) and uncapped >= config.max_leverage)
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
                "at_leverage_cap": at_cap,
                "raw_target_corr": construction._corr(raw, scores),
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
    "fix": (
        "every step is closed inside the observed universe: weights, neutralisation, the band, "
        "routing over its pairs, and the currency returns themselves, rebuilt from those same "
        "pairs so the reported P&L is the routed book's"
    ),
    "verdicts_unchanged": (
        "#485's fast five-day verdict stands as recorded; the repaired re-run is reported "
        "beside it as a robustness check, not as a replacement"
    ),
}


__all__ = [
    "REPAIR",
    "BookConfig",
    "Routing",
    "identity_residual",
    "routing_profile",
    "run_book",
    "split_map",
    "tradable_pairs",
    "universe_panel",
]
