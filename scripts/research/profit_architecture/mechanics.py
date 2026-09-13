"""Signal-free portfolio mechanics: turnover laws, leverage translation, power.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Everything in this module is arithmetic or Monte Carlo over **synthetic weight
processes** — no market data, no signal, no return of any instrument. The
questions it answers are the mechanical halves of the redesign:

1. How does a continuous book's turnover depend on the persistence of its
   target weights, on a no-trade band, and on blending horizons? (`turnover
   mechanics` — this is where "prediction frequency != turnover" gets numbers.)
2. What does a given net Sharpe translate into at realistic volatility targets,
   with the cost drag charged on realised turnover? (`capacity tables`.)
3. What could a future one-shot confirmation actually detect? (`power
   arithmetic` — the honest bottleneck, stated rather than discovered later.)

The one closed form worth having
--------------------------------

For a stationary Gaussian AR(1) target with daily autocorrelation `rho`, the
day-to-day change has standard deviation `sigma_w * sqrt(2(1-rho))`, so annual
turnover scales as **sqrt(1 - rho)**. A book whose targets have a 20-day
half-life (rho ~ 0.966) therefore turns over about `sqrt(0.034/1)` ~ 18% of a
fresh-every-day book — persistence, not update frequency, is what sets the cost.
The Monte Carlo below confirms the scaling on the normalised, cross-sectionally
demeaned book the closed form only approximates.
"""

from __future__ import annotations

import math
from typing import Any, Final

import numpy as np
from scipy import stats as scipy_stats

from scripts.research.profit_architecture import (
    BASKET_ROUNDTRIP_BP,
    EFFECTIVE_CURRENCY_BREADTH_PER_DAY,
    FRESH_POOL_YEARS,
    MEASURED_ANNUAL_VOL_PER_GROSS_BP,
    TRADING_DAYS_PER_YEAR,
)

#: Simulation size: long enough that the reported turnovers are stable to well
#: under a round trip a year, small enough to run in seconds. Fixed seed —
#: the module must be deterministic.
SIMULATION_DAYS: Final[int] = 252 * 60
SEED: Final[int] = 20260913
N_CURRENCIES: Final[int] = 8


# ------------------------------------------------------------- turnover laws
def simulate_book_turnover(
    rho: float,
    *,
    band: float = 0.0,
    days: int = SIMULATION_DAYS,
    seed: int = SEED,
) -> dict[str, float]:
    """Annualised turnover of a gross-1 long-short book with AR(1) targets.

    `band` is a no-trade band per currency, in units of gross (the book's gross
    is 1, so a band of 0.05 ignores target-vs-held gaps smaller than 5% of the
    book). When a gap exceeds the band the position trades **to the target** —
    the simplest policy, and a conservative one: trading only to the band edge
    reduces turnover further.

    Returns annualised full-book round trips and the mean tracking gap the band
    leaves open (sum of |held - target| over currencies, in gross units).
    """
    if not 0.0 <= rho < 1.0:
        raise ValueError(f"rho {rho} is not in [0, 1)")
    rng = np.random.default_rng(seed)
    innovation = math.sqrt(1.0 - rho * rho)
    state = rng.standard_normal(N_CURRENCIES)
    held: np.ndarray | None = None
    one_way = 0.0
    tracking = 0.0
    dot_held_target = 0.0
    dot_target_target = 0.0
    counted = 0
    for _ in range(days):
        state = rho * state + innovation * rng.standard_normal(N_CURRENCIES)
        target = state - state.mean()
        gross = np.abs(target).sum()
        if gross == 0.0:
            continue
        target = target / gross
        if held is None:
            held = target.copy()
            continue
        gap = target - held
        trade = np.where(np.abs(gap) > band, gap, 0.0)
        held = held + trade
        one_way += float(np.abs(trade).sum())
        tracking += float(np.abs(held - target).sum())
        dot_held_target += float(np.dot(held, target))
        dot_target_target += float(np.dot(target, target))
        counted += 1
    return {
        "annual_turnover": round(one_way / 2.0 / counted * TRADING_DAYS_PER_YEAR, 2),
        "mean_tracking_gap": round(tracking / counted, 4),
        #: ⭐ What the band forfeits, measured rather than asserted. If the alpha
        #: is proportional to the target — the premise of every other number in
        #: this module — the held book captures `E[held.target]/E[target.target]`
        #: of the target book's gross IR. A first draft claimed the gap "costs
        #: nothing" without computing this; a review computed it and it costs
        #: about 4% of gross at the recommended band.
        "alpha_capture": round(dot_held_target / dot_target_target, 4),
    }


def rho_for_half_life(days: float) -> float:
    """Daily autocorrelation of a target whose information half-life is `days`."""
    if days <= 0:
        raise ValueError("a half-life needs a positive length")
    return float(0.5 ** (1.0 / days))


def turnover_law_table() -> dict[str, Any]:
    """⭐ Turnover against target persistence — the central mechanical fact.

    Every row updates its target **daily**. The old convention would charge all
    of them 252 round trips a year; the actual turnover spans a factor of
    twenty, set entirely by how long the target's information lives.
    """
    rows: dict[str, Any] = {}
    for label, half_life in (
        ("half_life_1d", 1.0),
        ("half_life_5d", 5.0),
        ("half_life_10d", 10.0),
        ("half_life_20d", 20.0),
        ("half_life_60d", 60.0),
    ):
        rho = rho_for_half_life(half_life)
        result = simulate_book_turnover(rho)
        rows[label] = {
            "daily_autocorrelation": round(rho, 4),
            "annual_turnover": result["annual_turnover"],
            "annual_cost_bp": round(result["annual_turnover"] * BASKET_ROUNDTRIP_BP, 1),
            "ir_drag": round(
                result["annual_turnover"] * BASKET_ROUNDTRIP_BP / MEASURED_ANNUAL_VOL_PER_GROSS_BP,
                3,
            ),
        }
    fresh = simulate_book_turnover(0.0)
    return {
        "update_frequency": "daily, every row",
        "close_reopen_convention_would_charge": 252.0,
        "fresh_targets_every_day": fresh["annual_turnover"],
        "rows": rows,
        "scaling": "turnover ~ sqrt(1 - rho): persistence, not update frequency",
    }


def no_trade_band_table(half_life_days: float = 20.0) -> dict[str, Any]:
    """What a no-trade band buys, and what tracking gap it costs.

    The tracking gap is reported in gross units so a reader can judge it: a mean
    gap of 0.10 means the held book is, on average, 10% of gross away from its
    target — noise-level slippage against targets whose own day-to-day noise is
    far larger.
    """
    rho = rho_for_half_life(half_life_days)
    rows: dict[str, Any] = {}
    for band in (0.0, 0.02, 0.05, 0.10, 0.15):
        result = simulate_book_turnover(rho, band=band)
        capture = result["alpha_capture"]
        drag = ir_drag(result["annual_turnover"])
        rows[f"band_{band:g}"] = {
            "annual_turnover": result["annual_turnover"],
            "annual_cost_bp": round(result["annual_turnover"] * BASKET_ROUNDTRIP_BP, 1),
            "mean_tracking_gap_gross": result["mean_tracking_gap"],
            "alpha_capture": capture,
            #: The gross target-book IR the forecasts must deliver for net 0.5,
            #: with the band's alpha loss charged: `(net + drag) / capture`.
            "required_target_gross_ir_for_net_0_5": round((0.5 + drag) / capture, 3),
            "required_daily_ic_for_net_0_5": round(
                (0.5 + drag)
                / capture
                / math.sqrt(EFFECTIVE_CURRENCY_BREADTH_PER_DAY * TRADING_DAYS_PER_YEAR),
                4,
            ),
        }
    return {"target_half_life_days": half_life_days, "rows": rows}


def multi_horizon_turnover(
    *,
    slow_half_life: float = 60.0,
    fast_half_life: float = 3.0,
    fast_share: float = 0.3,
    band: float = 0.0,
    days: int = SIMULATION_DAYS,
    seed: int = SEED,
) -> dict[str, float]:
    """Turnover of a blended book `w = (1-s) * slow + s * fast`, both AR(1).

    The point the instruction makes at §14, measured: a fast component that
    *modulates* a persistent core adds far less turnover than a fast book run
    on its own, because the core never flips and the fast piece trades only its
    own share of gross.

    ⭐ The sub-additivity holds for **modulating shares up to about 0.3** and is
    claimed for nothing more: at share 0.5 the added turnover (41.8) already
    slightly exceeds `share x fast-alone` (40.6), because the renormalisation of
    the blended book starts churning the slow half too. A review measured the
    0.5 point against a first draft that had stated the bound unconditionally.
    """
    rng = np.random.default_rng(seed)
    slow_rho = rho_for_half_life(slow_half_life)
    fast_rho = rho_for_half_life(fast_half_life)
    slow = rng.standard_normal(N_CURRENCIES)
    fast = rng.standard_normal(N_CURRENCIES)
    held: np.ndarray | None = None
    one_way = 0.0
    counted = 0
    for _ in range(days):
        slow = slow_rho * slow + math.sqrt(1 - slow_rho**2) * rng.standard_normal(N_CURRENCIES)
        fast = fast_rho * fast + math.sqrt(1 - fast_rho**2) * rng.standard_normal(N_CURRENCIES)

        def unit_gross(vector: np.ndarray) -> np.ndarray:
            centred = vector - vector.mean()
            gross = np.abs(centred).sum()
            return centred / gross if gross else centred

        target = (1.0 - fast_share) * unit_gross(slow) + fast_share * unit_gross(fast)
        gross = np.abs(target).sum()
        target = target / gross if gross else target
        if held is None:
            held = target.copy()
            continue
        gap = target - held
        trade = np.where(np.abs(gap) > band, gap, 0.0)
        held = held + trade
        one_way += float(np.abs(trade).sum())
        counted += 1
    return {"annual_turnover": round(one_way / 2.0 / counted * TRADING_DAYS_PER_YEAR, 2)}


# ------------------------------------------------------- leverage translation
def ir_drag(annual_turnover: float) -> float:
    """Cost drag on the annual information ratio, leverage-invariant.

    `turnover x roundtrip / vol_per_gross`: both numerator and denominator scale
    with gross exposure, so leverage cancels — leverage is not an edge and
    cannot become one here.
    """
    return annual_turnover * BASKET_ROUNDTRIP_BP / MEASURED_ANNUAL_VOL_PER_GROSS_BP


def required_gross_ir(net_sharpe: float, annual_turnover: float) -> float:
    return net_sharpe + ir_drag(annual_turnover)


def leverage_for_vol_target(vol_target: float) -> float:
    """Gross exposure per unit of capital at a volatility target."""
    return vol_target / (MEASURED_ANNUAL_VOL_PER_GROSS_BP / 10_000.0)


def expected_max_drawdown(
    net_sharpe: float, vol_target: float, *, years: float = 5.0, seed: int = SEED
) -> float:
    """Mean maximum drawdown over `years`, simulated for a Gaussian daily book."""
    rng = np.random.default_rng(seed)
    days = int(TRADING_DAYS_PER_YEAR * years)
    daily_mu = net_sharpe * vol_target / TRADING_DAYS_PER_YEAR
    daily_sigma = vol_target / math.sqrt(TRADING_DAYS_PER_YEAR)
    worst = []
    for _ in range(400):
        path = np.cumsum(rng.normal(daily_mu, daily_sigma, size=days))
        worst.append(float((path - np.maximum.accumulate(path)).min()))
    return round(-float(np.mean(worst)), 4)


def capacity_table() -> dict[str, Any]:
    """⭐ The economics of the continuous book, end to end.

    For each realistic turnover level and net-Sharpe scenario: the gross ratio
    the forecasts must deliver, the per-day cross-sectional information
    coefficient that implies at the measured breadth, and the annual net return
    and expected drawdown at three volatility targets.
    """
    breadth_per_year = EFFECTIVE_CURRENCY_BREADTH_PER_DAY * TRADING_DAYS_PER_YEAR
    turnover_rows: dict[str, Any] = {}
    for turnover in (252.0, 90.0, 50.0, 36.7, 25.0, 12.0, 6.0):
        drag = ir_drag(turnover)
        turnover_rows[f"turnover_{turnover:g}"] = {
            "annual_cost_bp": round(turnover * BASKET_ROUNDTRIP_BP, 1),
            "ir_drag": round(drag, 3),
            "required_gross_ir_for_net_sharpe": {
                f"{net:g}": round(required_gross_ir(net, turnover), 3)
                for net in (0.3, 0.5, 0.8, 1.0)
            },
            "required_daily_ic_for_net_sharpe": {
                f"{net:g}": round(required_gross_ir(net, turnover) / math.sqrt(breadth_per_year), 4)
                for net in (0.3, 0.5, 0.8, 1.0)
            },
        }
    vol_rows: dict[str, Any] = {}
    for vol in (0.08, 0.10, 0.12):
        vol_rows[f"vol_{vol:g}"] = {
            "leverage_gross_over_capital": round(leverage_for_vol_target(vol), 2),
            "annual_net_return_at_net_sharpe": {
                f"{net:g}": f"{net * vol:.1%}" for net in (0.3, 0.5, 0.8, 1.0)
            },
            "expected_max_drawdown_5y_at_net_sharpe": {
                f"{net:g}": f"{expected_max_drawdown(net, vol):.1%}" for net in (0.3, 0.5, 0.8, 1.0)
            },
        }
    return {
        "vol_per_gross_bp": MEASURED_ANNUAL_VOL_PER_GROSS_BP,
        "effective_breadth_per_day": EFFECTIVE_CURRENCY_BREADTH_PER_DAY,
        "by_turnover": turnover_rows,
        "by_vol_target": vol_rows,
        "identities": [
            "net_sharpe = gross_ir - turnover x roundtrip / vol_per_gross",
            "annual_net_return = net_sharpe x vol_target",
            "leverage = vol_target / vol_per_gross; cancels out of every ratio",
            "required_daily_ic = gross_ir / sqrt(breadth_per_day x 252)",
        ],
    }


# -------------------------------------------------------------- pair routing
def pair_routing_audit(
    *,
    half_life_days: float = 20.0,
    days: int = 252 * 10,
    seed: int = SEED,
) -> dict[str, Any]:
    """⭐ What the diversified book actually pays per unit of turnover.

    One formula covers everything: **cost per turnover unit = R x 2.58 bp**,
    where `R` is the one-way pair notional traded per unit of one-way currency
    notional. Three values of `R` matter, and this audit measures the two that
    were never measured before:

    * `R = 1.32` — the **charged** value: Track 2's measured routing of an
      isolated one-currency-against-basket position. `1.32 x 2.58 = 3.406`.
    * `R ~ 0.77` — the **implementation** value: the corpus's own equal-split
      construction (`currency_return` averages each currency over its available
      pairs), which nets overlapping basket legs across currencies.
    * `R ~ 0.55` — the **floor**: minimum-notional routing of the same deltas by
      linear programme over the archive's real twenty-pair topology.

    So the 3.406 convention is conservative by ~1.7x against the book the
    programme's own evaluator prices, and by ~2.4x against the routing floor.
    Both are measured signal-free — AR(1) synthetic deltas, pair *names* only,
    no price read — and both assume the average 2.58 bp round trip applies
    uniformly across pairs, which minimum-notional routing would not quite
    achieve (it leans on wider-spread crosses). ⭐ The headline requirements
    keep the conservative 3.406 charge; this table records the measured room,
    and A08 execution-vehicle optimization is the candidate that would claim it.

    A first version of this function multiplied one-way notional by the full
    round-trip rate and fed the LP a mixed-space delta; a review's independent
    measurement (0.77, factor ~1.7) is what the corrected version reproduces.
    """
    from scipy.optimize import linprog

    from scripts.research.exploratory_m15 import PAIRS

    currencies = sorted({leg for pair in PAIRS for leg in pair.split("_")})
    pairs_per_currency = {
        currency: sum(currency in pair.split("_") for pair in PAIRS) for currency in currencies
    }
    incidence = np.zeros((len(currencies), len(PAIRS)))
    #: The corpus construction: currency c's index is the mean of its signed
    #: pair returns, so one unit of w on c is 1/n_c of pair notional on each of
    #: c's pairs. `split_map` maps a currency-weight vector to that implicit
    #: pair book.
    split_map = np.zeros((len(PAIRS), len(currencies)))
    for column, pair in enumerate(PAIRS):
        base, quote = pair.split("_")
        incidence[currencies.index(base), column] = 1.0
        incidence[currencies.index(quote), column] = -1.0
        split_map[column, currencies.index(base)] = 1.0 / pairs_per_currency[base]
        split_map[column, currencies.index(quote)] = -1.0 / pairs_per_currency[quote]

    rho = rho_for_half_life(half_life_days)
    rng = np.random.default_rng(seed)
    innovation = math.sqrt(1.0 - rho * rho)
    state = rng.standard_normal(len(currencies))
    previous: np.ndarray | None = None
    currency_one_way = 0.0
    equal_split_one_way = 0.0
    minimal_one_way = 0.0
    #: min sum|t| subject to incidence @ t = the currency delta, via t = t+ - t-.
    objective = np.ones(2 * len(PAIRS))
    equality = np.hstack([incidence, -incidence])
    for _ in range(days):
        state = rho * state + innovation * rng.standard_normal(len(currencies))
        target = state - state.mean()
        target = target / np.abs(target).sum()
        if previous is None:
            previous = target
            continue
        delta = target - previous
        previous = target
        currency_one_way += float(np.abs(delta).sum())
        equal_split_one_way += float(np.abs(split_map @ delta).sum())
        solution = linprog(objective, A_eq=equality, b_eq=delta, bounds=(0, None), method="highs")
        if not solution.success:
            raise RuntimeError("the routing programme failed, which it cannot")
        minimal_one_way += float(solution.fun)

    from scripts.research.profit_architecture import PAIR_ROUNDTRIP_BP as PAIR_RT

    charged_ratio = round(BASKET_ROUNDTRIP_BP / PAIR_RT, 4)

    def block(one_way: float) -> dict[str, float]:
        ratio = one_way / currency_one_way
        #: One turnover unit = currency one-way / 2, and one unit of one-way
        #: pair notional costs half the 2.58 round trip — so per turnover unit
        #: the cost is `2 x ratio x (2.58 / 2) = ratio x 2.58`.
        cost = ratio * PAIR_RT
        return {
            "pair_one_way_per_currency_one_way": round(ratio, 4),
            "cost_per_turnover_unit_bp": round(cost, 3),
            "conservatism_factor_vs_convention": round(BASKET_ROUNDTRIP_BP / cost, 2),
            "ir_drag_at_measured_turnover_36_7": round(
                36.7 * cost / MEASURED_ANNUAL_VOL_PER_GROSS_BP, 3
            ),
        }

    return {
        "pair_topology": f"{len(PAIRS)} archive pairs over {len(currencies)} currencies",
        "identity": "cost per turnover unit = R x pair round trip (2.58 bp)",
        "charged_isolated_position": {
            "pair_one_way_per_currency_one_way": charged_ratio,
            "cost_per_turnover_unit_bp": BASKET_ROUNDTRIP_BP,
            "conservatism_factor_vs_convention": 1.0,
            "ir_drag_at_measured_turnover_36_7": round(
                36.7 * BASKET_ROUNDTRIP_BP / MEASURED_ANNUAL_VOL_PER_GROSS_BP, 3
            ),
        },
        "implementation_equal_split_netting": block(equal_split_one_way),
        "minimal_notional_floor": block(minimal_one_way),
        "uniform_cost_caveat": (
            "both measured rows price every pair at the average 2.58 bp; a "
            "cost-weighted router would land between them and the charge"
        ),
        "note": (
            "headline requirements keep the conservative 3.406 charge; this is the "
            "measured room, and A08 execution-vehicle optimization is the candidate "
            "that would claim it"
        ),
    }


# --------------------------------------------------------- confirmation power
def one_shot_power(true_net_ir: float, years: float, *, alpha: float = 0.05) -> float:
    """P(a one-shot test of net IR > 0 rejects), one-sided, SE ~ 1/sqrt(years)."""
    if years <= 0:
        raise ValueError("no years, no test")
    z_alpha = float(scipy_stats.norm.ppf(1.0 - alpha))
    return float(scipy_stats.norm.cdf(true_net_ir * math.sqrt(years) - z_alpha))


def confirmation_power_table() -> dict[str, Any]:
    """⭐ What the fresh pool can and cannot confirm — the honest bottleneck.

    The fresh pool is 4.9 years. A strategy whose true net Sharpe is 0.5 — the
    central profitable scenario — has under a one-in-three chance of clearing a
    one-shot alpha=0.05 test on it. Proof-grade confirmation of realistic edges
    is decades of data away; what shorter horizons support is a **decision**
    standard (deploy small, with kill rules), which is a different standard and
    a human's to set.
    """
    rows: dict[str, Any] = {}
    for years, label in (
        (FRESH_POOL_YEARS, "fresh_pool_one_shot"),
        (FRESH_POOL_YEARS + 3.0, "fresh_pool_plus_3y_paper_forward"),
        (10.0, "ten_years"),
        (25.0, "twenty_five_years"),
    ):
        rows[label] = {
            "years": years,
            "power_at_true_net_ir": {
                f"{ir:g}": round(one_shot_power(ir, years), 3) for ir in (0.3, 0.5, 0.8, 1.2)
            },
        }
    return {
        "alpha_one_sided": 0.05,
        "rows": rows,
        "years_for_80_percent_power": {
            f"{ir:g}": round(((1.645 + 0.842) / ir) ** 2, 1) for ir in (0.3, 0.5, 0.8, 1.2)
        },
    }


__all__ = [
    "N_CURRENCIES",
    "SEED",
    "SIMULATION_DAYS",
    "capacity_table",
    "confirmation_power_table",
    "expected_max_drawdown",
    "ir_drag",
    "leverage_for_vol_target",
    "multi_horizon_turnover",
    "no_trade_band_table",
    "one_shot_power",
    "pair_routing_audit",
    "required_gross_ir",
    "rho_for_half_life",
    "simulate_book_turnover",
    "turnover_law_table",
]
