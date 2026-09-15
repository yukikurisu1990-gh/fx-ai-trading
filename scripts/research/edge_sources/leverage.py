# ruff: noqa: E501 -- provenance prose
"""Leverage and margin, with three concepts kept apart.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

* **A. Broker hard leverage** — what OANDA Japan permits per pair:
  `1 / margin_rate`, from the public TY3 specification recorded in
  `artifacts/research/edge_sources/oanda_margin_rates.json`.
* **B. Portfolio gross leverage** — `sum |routed pair notional| / equity`, after
  the currency book is routed to the twenty pairs.
* **C. Risk leverage** — the scale that takes the unlevered currency book to a
  target volatility: `target vol / unlevered vol`. The unlevered book has
  currency gross 1, so C is also its currency gross.

Required margin is never `gross / 25`: it is `sum_i |routed notional_i| x
margin_rate_i`, computed on the routed pair book.

Leverage scales an edge; it does not make one. Every quantity here is
signal-free: routing comes from synthetic AR(1) targets through the Track 1
execution layer, drawdown from Gaussian paths, stress from declared shocks.
Nothing here says a source earns its Sharpe.
"""

from __future__ import annotations

import json
import math
from functools import cache
from pathlib import Path
from typing import Any, Final

import numpy as np

from scripts.research.continuous_portfolio import construction
from scripts.research.edge_sources import capacity

MARGIN_RECORD: Final[str] = "artifacts/research/edge_sources/oanda_margin_rates.json"

#: Where the old "5x" came from, traced to the commit that introduced it.
PREVIOUS_FIVE_X: Final[dict[str, str]] = {
    "value": "5.0",
    "where": "scripts/research/continuous_portfolio/construction.py BookConfig.max_leverage default; docs/design/m15_track1_continuous_portfolio_prereg.md",
    "introduced_in": "3ed3527 (2026-09-14) research(track-1): continuous currency portfolio — pre-registration and implementation",
    "leverage_concept_capped": "risk leverage (concept C): the VolTargeter scalar applied to the currency book, exposure = held x leverage; 5 on C is about 3.85 of routed portfolio gross (concept B)",
    "used_as": "the VolTargeter ceiling of every Track 1 book, and Track 1 kill rule 'the target asks for the 5x leverage cap or more on more than half of days'",
    "provenance_option_in_the_ruling": "option 'prior pre-registration internal risk limit', in substance 'placeholder': frozen into the Track 1 pre-registration with no recorded rationale; not an OANDA limit, not derived from margin, drawdown or risk",
    "status": "WITHDRAWN as a feasibility boundary for new research. Track 1's frozen pre-registration and its Case C are unchanged: Track 1 failed on negative gross Sharpe, which no leverage changes",
}

#: Declared stress assumption (no market data read): one currency gaps against all others.
STRESS_CURRENCY_GAP: Final[float] = 0.20
ROUTING_DAYS: Final[int] = 252 * 20
ROUTING_SEED: Final[int] = 20260916
ROUTING_HALF_LIFE_DAYS: Final[float] = 20.0

RISK_BASED_POLICY: Final[dict[str, Any]] = {
    "fixed_leverage_cap": None,
    "order": [
        "1. unit-risk economics first: the unlevered book's gross and net Sharpe decide whether a source exists; leverage never enters that decision",
        "2. choose a target volatility; risk leverage C = target vol / unlevered vol",
        "3. route the scaled currency book to pairs; portfolio gross leverage B and required margin = sum |routed notional_i| x margin_rate_i",
        "4. broker test (gap): the book is sized to equity every day, so a slow drawdown does not approach the loss-cut; a gap does. At the leverage tail (Track 1's recorded p95 / mean uncapped leverage) and the p95 single-currency exposure of the routed book, one currency gaps 20% against all others before the book can resize",
        "5. a scale is broker-infeasible only if equity after that gap is at or below the required margin on the still-open notional (maintenance ratio 100%, loss-cut) — not because it exceeds any fixed multiple",
        "6. risk appetite (reported, not a broker test): ten-year maximum drawdown with equity-proportional sizing, at net Sharpe 0 (the sizing-relevant case) and at the assumed Sharpe; drawdown, margin utilisation and concentration are for Human judgement, never optimised",
    ],
    "why_these_stresses": {
        "gap_20pct": "the order of magnitude of the largest G10 one-day repricing on record (the SNB's January 2015 floor removal). A declared assumption, not measured here",
        "leverage_tail": "vol targeting raises leverage in calm spells, which is when gaps arrive; Track 1 recorded mean uncapped leverage 5.08 and p95 8.04 at a 10% target",
        "routed_exposure": "a single currency's exposure in the routed pair book exceeds its capped weight after band drift; the p95 of the routed book is used, not the 0.25 cap",
        "drawdown_at_zero_sharpe": "a sizing rule must not grant more leverage because a higher Sharpe is hoped for",
    },
    "second_order_effects_ignored": [
        "a gap also changes the JPY value of the open notional and so its required margin",
        "loss-cut fills are not guaranteed; the specification says losses can exceed deposited margin",
        "the account-level position limit (USD 30M market value one-sided) and per-pair maximum order sizes cap account size, not rate-based leverage",
    ],
    "not_a_recommendation": "the broker maximum (25x on most pairs) is a boundary to measure distance to, never a target; 25x is not an operating scenario",
}

RISK_LEVERAGE_SCENARIOS: Final[tuple[float, ...]] = (1.0, 2.0, 3.0, 5.0, 8.0, 10.0)
VOL_TARGET_SCENARIOS: Final[tuple[float, ...]] = (0.08, 0.10, 0.12, 0.15)
RETURN_TARGETS: Final[tuple[float, ...]] = (0.05, 0.10, 0.15)


def margin_rates(root: Path) -> dict[str, Any]:
    record = json.loads((root / MARGIN_RECORD).read_text(encoding="utf-8"))
    return {
        "rates": {pair: row["margin_rate"] for pair, row in record["research_universe"].items()},
        "loss_cut_maintenance_ratio": record["loss_cut_margin_maintenance_ratio"],
        "retrieved_utc": record["retrieved_utc"],
        "source": record["sources"]["pair_table"]["url"],
        "account": record["account_assumption"]["server_platform"],
    }


@cache
def _routing(rates_key: tuple[tuple[str, float], ...]) -> dict[str, Any]:
    rates = dict(rates_key)
    pairs = construction.PAIRS_20
    pair_map = construction.split_map()
    rate_vector = np.array([rates[p] for p in pairs])
    rho = 0.5 ** (1.0 / ROUTING_HALF_LIFE_DAYS)
    innovation = math.sqrt(1.0 - rho * rho)
    rng = np.random.default_rng(ROUTING_SEED)
    state = rng.standard_normal(len(construction.CURRENCIES))
    held: np.ndarray | None = None
    abs_notional = np.zeros(len(pairs))
    pair_gross: list[float] = []
    margin: list[float] = []
    top_share: list[float] = []
    exposure: list[float] = []
    incidence = np.zeros((len(pairs), len(construction.CURRENCIES)))
    for row, pair in enumerate(pairs):
        base, quote = pair.split("_")
        incidence[row, construction.CURRENCIES.index(base)] = 1.0
        incidence[row, construction.CURRENCIES.index(quote)] = -1.0
    for _ in range(ROUTING_DAYS):
        state = rho * state + innovation * rng.standard_normal(len(construction.CURRENCIES))
        target = construction.capped_weights(
            state, construction.BookConfig(name="routing").weight_cap
        )
        held = (
            target.copy()
            if held is None
            else construction.band_rebalance(target, held, capacity.BAND)
        )
        currency_gross = float(np.abs(held).sum())
        routed = np.abs(pair_map @ held) / currency_gross
        abs_notional += routed
        pair_gross.append(float(routed.sum()))
        margin.append(float(routed @ rate_vector))
        top_share.append(float(routed.max() / routed.sum()))
        signed = (pair_map @ held) / currency_gross
        exposure.append(float(np.abs(incidence.T @ signed).max()))
    mean_notional = abs_notional / ROUTING_DAYS
    return {
        "per_pair_mean_notional_per_unit_currency_gross": {
            p: round(float(v), 4) for p, v in zip(pairs, mean_notional, strict=True)
        },
        "pair_gross_per_unit_currency_gross": {
            "mean": round(float(np.mean(pair_gross)), 4),
            "p95": round(float(np.quantile(pair_gross, 0.95)), 4),
        },
        "margin_per_unit_currency_gross": {
            "mean": round(float(np.mean(margin)), 5),
            "p95": round(float(np.quantile(margin, 0.95)), 5),
        },
        "largest_single_currency_exposure_per_unit_currency_gross": {
            "mean": round(float(np.mean(exposure)), 4),
            "p95": round(float(np.quantile(exposure, 0.95)), 4),
        },
        "largest_single_pair_share_of_pair_gross": {
            "mean": round(float(np.mean(top_share)), 4),
            "p95": round(float(np.quantile(top_share, 0.95)), 4),
        },
    }


def routing_profile(root: Path) -> dict[str, Any]:
    """Signal-free pair routing of the Track 1 execution layer, per unit currency gross."""
    rates = margin_rates(root)["rates"]
    return _routing(tuple(sorted(rates.items())))


def leverage_tail_multiple(root: Path) -> float:
    summary = json.loads((root / capacity.TRACK_1_RECORD).read_text(encoding="utf-8"))["primary"][
        "summary"
    ]
    return round(summary["p95_uncapped_leverage"] / summary["mean_uncapped_leverage"], 4)


def _equity_drawdown(units: float, vol: float) -> float:
    """Drawdown of equity sized to itself: `1 - exp(-log drawdown)`."""
    return 1.0 - math.exp(-units * vol)


def scale(root: Path, risk_leverage: float, net_sharpe: float) -> dict[str, Any]:
    """Everything a mean risk leverage implies, at an assumed net Sharpe of the unlevered book."""
    route = routing_profile(root)
    tail = leverage_tail_multiple(root)
    vol = risk_leverage * capacity.VOL_PER_UNIT_GROSS
    c_tail = risk_leverage * tail
    margin_rate_p95 = route["margin_per_unit_currency_gross"]["p95"]
    exposure_p95 = route["largest_single_currency_exposure_per_unit_currency_gross"]["p95"]
    margin_mean = risk_leverage * route["margin_per_unit_currency_gross"]["mean"]
    margin_tail = c_tail * margin_rate_p95
    gap_loss = c_tail * exposure_p95 * STRESS_CURRENCY_GAP
    equity_after_gap = 1.0 - gap_loss
    maintenance_after_gap = equity_after_gap / margin_tail
    assumed = capacity.gaussian_drawdown(net_sharpe)
    zero = capacity.gaussian_drawdown(0.0)
    return {
        "risk_leverage_C_mean": round(risk_leverage, 2),
        "risk_leverage_C_tail": round(c_tail, 2),
        "annual_vol": round(vol, 4),
        "annual_net_return": round(net_sharpe * vol, 4),
        "portfolio_gross_leverage_B_mean": round(
            risk_leverage * route["pair_gross_per_unit_currency_gross"]["mean"], 2
        ),
        "margin_utilisation_mean": round(margin_mean, 4),
        "margin_utilisation_at_leverage_tail": round(margin_tail, 4),
        "gap_loss_at_leverage_tail": round(gap_loss, 4),
        "equity_after_gap": round(equity_after_gap, 4),
        "maintenance_ratio_after_gap": round(maintenance_after_gap, 2),
        "loss_cut_on_gap": bool(maintenance_after_gap <= 1.0),
        "largest_currency_gap_before_loss_cut": round(
            (1.0 - margin_tail) / (c_tail * exposure_p95), 4
        ),
        "median_max_drawdown_10y_at_assumed_sharpe": round(
            _equity_drawdown(assumed["median_max_drawdown_in_vol_units"], vol), 3
        ),
        "p95_max_drawdown_10y_at_assumed_sharpe": round(
            _equity_drawdown(assumed["p95_max_drawdown_in_vol_units"], vol), 3
        ),
        "p95_max_drawdown_10y_at_zero_sharpe": round(
            _equity_drawdown(zero["p95_max_drawdown_in_vol_units"], vol), 3
        ),
    }


def broker_feasible_mean_risk_leverage(root: Path) -> float:
    """The largest mean C at which the leverage-tail gap leaves equity above margin."""
    route = routing_profile(root)
    per_unit = (
        route["largest_single_currency_exposure_per_unit_currency_gross"]["p95"]
        * STRESS_CURRENCY_GAP
        + route["margin_per_unit_currency_gross"]["p95"]
    )
    return round(1.0 / (leverage_tail_multiple(root) * per_unit), 2)


def pair_margin_table(root: Path, risk_leverage: float) -> list[dict[str, Any]]:
    record = margin_rates(root)
    route = routing_profile(root)
    rows = []
    for pair, per_unit in route["per_pair_mean_notional_per_unit_currency_gross"].items():
        rate = record["rates"][pair]
        notional = per_unit * risk_leverage
        rows.append(
            {
                "pair": pair,
                "margin_rate": rate,
                "broker_hard_leverage_A": round(1.0 / rate, 1),
                "routed_notional_per_equity": round(notional, 4),
                "required_margin_per_equity": round(notional * rate, 5),
            }
        )
    return rows


def build(root: Path) -> dict[str, Any]:
    record = margin_rates(root)
    route = routing_profile(root)
    track_1 = json.loads((root / capacity.TRACK_1_RECORD).read_text(encoding="utf-8"))["primary"][
        "summary"
    ]
    ten_pct = 0.10 / capacity.VOL_PER_UNIT_GROSS
    table = pair_margin_table(root, ten_pct)
    return {
        "previous_five_x": PREVIOUS_FIVE_X,
        "risk_based_policy": RISK_BASED_POLICY,
        "broker": {
            k: record[k]
            for k in ("retrieved_utc", "source", "account", "loss_cut_maintenance_ratio")
        },
        "routing": route,
        "routing_check_against_track_1": {
            "track_1_pair_gross_per_currency_gross": round(
                track_1["mean_pair_gross_notional"] / track_1["mean_currency_gross"], 4
            ),
            "synthetic_mean": route["pair_gross_per_unit_currency_gross"]["mean"],
        },
        "broker_capacity_risk_leverage_at_margin_100pct": round(
            1.0 / route["margin_per_unit_currency_gross"]["p95"], 1
        ),
        "leverage_tail_multiple_from_track_1": leverage_tail_multiple(root),
        "broker_feasible_mean_risk_leverage_under_gap_stress": broker_feasible_mean_risk_leverage(
            root
        ),
        "broker_feasible_vol_target_under_gap_stress": round(
            broker_feasible_mean_risk_leverage(root) * capacity.VOL_PER_UNIT_GROSS, 4
        ),
        "pair_margin_at_10pct_vol": {
            "risk_leverage_C": round(ten_pct, 2),
            "rows": table,
            "total_routed_notional_B": round(
                sum(r["routed_notional_per_equity"] for r in table), 3
            ),
            "total_required_margin": round(sum(r["required_margin_per_equity"] for r in table), 4),
            "equity": 1.0,
        },
        "risk_leverage_scenarios": {
            f"{lev:g}": {f"{s:g}": scale(root, lev, s) for s in capacity.NET_SHARPE_SCENARIOS}
            for lev in RISK_LEVERAGE_SCENARIOS
        },
        "vol_target_scenarios": {
            f"{vol:g}": {
                f"{s:g}": scale(root, vol / capacity.VOL_PER_UNIT_GROSS, s)
                for s in capacity.NET_SHARPE_SCENARIOS
            }
            for vol in VOL_TARGET_SCENARIOS
        },
        "return_targets": {
            f"{target:g}": {
                f"{s:g}": {
                    "required_vol": round(target / s, 4),
                    **scale(root, target / s / capacity.VOL_PER_UNIT_GROSS, s),
                }
                for s in capacity.NET_SHARPE_SCENARIOS
            }
            for target in RETURN_TARGETS
        },
    }


__all__ = [
    "MARGIN_RECORD",
    "PREVIOUS_FIVE_X",
    "RISK_BASED_POLICY",
    "broker_feasible_mean_risk_leverage",
    "build",
    "leverage_tail_multiple",
    "margin_rates",
    "pair_margin_table",
    "routing_profile",
    "scale",
]
