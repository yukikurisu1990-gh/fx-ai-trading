"""Leverage, margin and gap stress measured on the universe that actually trades.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

`edge_sources.leverage` answers the same questions for the eight-currency book:
it routes over twenty pairs and scales by Track 1's volatility per unit of gross.
A five-currency book is a different portfolio — its cap binds far more often, its
largest single-currency exposure is twice as large, and its volatility per unit of
gross is its own — so those numbers do not transfer. The three leverage concepts,
the margin arithmetic and the stress assumptions are unchanged; only the portfolio
they are computed on is.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Final

import numpy as np

from scripts.research.edge_sources import leverage
from scripts.research.market_yields import portfolio

#: One currency gaps this far against all the others before the book can resize.
STRESS_CURRENCY_GAP: Final[float] = leverage.STRESS_CURRENCY_GAP


def margin_per_unit_currency_gross(
    root: Path, universe: tuple[str, ...] | list[str], samples: int = 4000
) -> dict[str, float]:
    """`sum |routed notional| x pair margin rate`, over the universe's own pairs."""
    rates = leverage.margin_rates(root)["rates"]
    currencies = tuple(universe)
    pairs = portfolio.tradable_pairs(currencies)
    pair_map = portfolio.split_map(currencies)
    rate_vector = np.array([rates[p] for p in pairs])
    rng = np.random.default_rng(20260918)
    margins, exposures = [], []
    for row in rng.standard_normal((samples, len(currencies))):
        weights = portfolio.construction.capped_weights(row, 0.25)
        gross = float(np.abs(weights).sum())
        if gross <= 0:
            continue
        routed = np.abs(pair_map @ weights) / gross
        margins.append(float(routed @ rate_vector))
        exposures.append(float(np.abs(weights).max() / gross))
    return {
        "margin_mean": round(float(np.mean(margins)), 5),
        "margin_p95": round(float(np.quantile(margins, 0.95)), 5),
        "largest_currency_exposure_p95": round(float(np.quantile(exposures, 0.95)), 4),
        "pairs": len(pairs),
    }


def gap_stress(
    root: Path,
    universe: tuple[str, ...] | list[str],
    *,
    vol_per_unit_gross: float,
    target_vol: float,
    leverage_tail_multiple: float | None = None,
) -> dict[str, Any]:
    """Whether a target volatility survives a one-currency gap, on this universe.

    Sharpe-independent, as the policy requires: only the routed margin, the leverage
    the target asks for, and the declared shock enter.
    """
    tail = (
        leverage.leverage_tail_multiple(root)
        if leverage_tail_multiple is None
        else leverage_tail_multiple
    )
    profile = margin_per_unit_currency_gross(root, universe)
    risk_leverage = target_vol / vol_per_unit_gross
    c_tail = risk_leverage * tail
    margin_tail = c_tail * profile["margin_p95"]
    gap_loss = c_tail * profile["largest_currency_exposure_p95"] * STRESS_CURRENCY_GAP
    equity_after_gap = 1.0 - gap_loss
    maintenance = equity_after_gap / margin_tail if margin_tail > 0 else float("inf")
    return {
        "universe": list(universe),
        "vol_per_unit_gross": round(vol_per_unit_gross, 6),
        "target_vol": target_vol,
        "risk_leverage_C_mean": round(risk_leverage, 2),
        "risk_leverage_C_tail": round(c_tail, 2),
        "leverage_tail_multiple": round(tail, 4),
        "margin_utilisation_mean": round(risk_leverage * profile["margin_mean"], 4),
        "margin_utilisation_at_leverage_tail": round(margin_tail, 4),
        "largest_currency_exposure_p95": profile["largest_currency_exposure_p95"],
        "gap_loss_at_leverage_tail": round(gap_loss, 4),
        "equity_after_gap": round(equity_after_gap, 4),
        "maintenance_ratio_after_gap": round(maintenance, 2),
        "loss_cut_on_gap": bool(maintenance <= 1.0),
        "largest_currency_gap_before_loss_cut": round(
            (1.0 - margin_tail) / (c_tail * profile["largest_currency_exposure_p95"]), 4
        ),
    }


def feasible_target_vol(
    root: Path, universe: tuple[str, ...] | list[str], vol_per_unit_gross: float
) -> float:
    """The largest target volatility whose gap stress leaves equity above margin."""
    tail = leverage.leverage_tail_multiple(root)
    profile = margin_per_unit_currency_gross(root, universe)
    per_unit = tail * (
        profile["largest_currency_exposure_p95"] * STRESS_CURRENCY_GAP + profile["margin_p95"]
    )
    return round(vol_per_unit_gross / per_unit, 4)


def leverage_for_return(
    root: Path,
    universe: tuple[str, ...] | list[str],
    *,
    vol_per_unit_gross: float,
    net_sharpe: float,
    annual_target: float,
) -> dict[str, Any]:
    """What an annual net return would require of this book, if the Sharpe were real."""
    if net_sharpe <= 0:
        return {
            "annual_target": annual_target,
            "reachable": False,
            "why": "a non-positive net Sharpe cannot be levered into a positive return",
        }
    required_vol = annual_target / net_sharpe
    stress = gap_stress(
        root, universe, vol_per_unit_gross=vol_per_unit_gross, target_vol=required_vol
    )
    return {"annual_target": annual_target, "reachable": not stress["loss_cut_on_gap"], **stress}


__all__ = [
    "STRESS_CURRENCY_GAP",
    "feasible_target_vol",
    "gap_stress",
    "leverage_for_return",
    "margin_per_unit_currency_gross",
]
