"""Signal-free profit-capacity arithmetic for the candidate sources.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Two book shapes cover every candidate:

* a **continuous currency book** — the Track 1 execution architecture (sum-zero
  weights, factor neutralisation, weight cap, no-trade band, volatility target)
  fed by a new expected-return source whose forecasts persist with a given
  half-life; and
* an **event book** — positions opened around a population of dated events and
  held for a few days, idle otherwise.

For each, the arithmetic answers the ruling's question in the ruling's units:
what forecast quality does a net Sharpe of 0.3 / 0.5 / 0.8 require, what does
that mean in annual return, leverage and drawdown at a volatility target, and
how many years of out-of-sample P&L would it take to see it. It never says a
source *has* that quality.

Measured, from the committed Track 1 record
-------------------------------------------

* Volatility per unit of currency gross: the primary Track 1 book realised
  9.9943% a year at mean currency gross 4.2917
  (`artifacts/research/continuous_portfolio/development.json`). With the cost
  convention below this reproduces the recorded gross − net Sharpe (0.374); the
  unlevered diagnostic book's 2.426% would understate the drag by 4%.
* Transfer coefficient 0.90: the raw-to-neutralised score correlation in Track 1
  (applied to new sources, which is itself an assumption).
* The cost convention, 1.703 bp per unit of `sum|delta|` (3.406 bp per turnover
  unit), and the cost drag it implies, which reproduces Track 1's gross − net.

Computed, signal-free
---------------------

* Turnover and alpha capture as a function of forecast half-life: the band law of
  the same construction (`continuous_portfolio.construction.band_calibration`,
  capped weights, band 0.10).

Assumptions, stated with a sensitivity
--------------------------------------

* **Effective breadth.** Four independent currency directions a day is a
  judgement, not a measurement: the programme measured 4.4-6.5 independent
  *pairs* in twenty with the common factor in, and the decision-grade inventory
  sets the cross-sectional share at 0.30 (about two directions a day). Every IC
  is also given at breadth 2.
* **Event-position volatility.** The base case borrows the diversified book's
  volatility; a single currency-against-basket position around its own event is
  concentrated and often *is* the factor the book removes, so every event edge
  and leverage is also given at 7% a year.
* **Drawdown.** Gaussian i.i.d. daily returns, which understates fat tails.
"""

from __future__ import annotations

import json
import math
from functools import cache
from pathlib import Path
from typing import Any, Final

import numpy as np

from scripts.research.continuous_portfolio import CHARGED_ONE_WAY_BP, construction
from scripts.research.feasibility.inventory import PAIR_ROUNDTRIP_BP

TRADING_DAYS: Final[float] = 252.0
TRACK_1_RECORD: Final[str] = "artifacts/research/continuous_portfolio/development.json"

#: Measured (see module docstring); the tests re-derive both from the record.
VOL_PER_UNIT_GROSS: Final[float] = round(0.099943 / 4.2917, 6)
TRANSFER_COEFFICIENT: Final[float] = 0.90
BAND: Final[float] = 0.10
WEIGHT_CAP: Final[float] = 0.25
#: The reused execution layer's leverage ceiling (`construction.BookConfig`).
MAX_LEVERAGE: Final[float] = construction.BookConfig(name="capacity").max_leverage

#: Assumptions (see module docstring), each with the sensitivity value reported.
EFFECTIVE_BREADTH_PER_DAY: Final[float] = 4.0
BREADTH_SENSITIVITY: Final[float] = 2.0

#: Cost of one turnover unit (`sum|delta| / 2`), the charged convention.
COST_PER_TURNOVER_UNIT_BP: Final[float] = 2.0 * CHARGED_ONE_WAY_BP

HALF_LIVES_DAYS: Final[tuple[float, ...]] = (1.0, 5.0, 20.0, 60.0, 120.0)
NET_SHARPE_SCENARIOS: Final[tuple[float, ...]] = (0.3, 0.5, 0.8)
VOL_TARGETS: Final[tuple[float, ...]] = (0.08, 0.10, 0.12)


@cache
def band_law(half_life_days: float) -> dict[str, float]:
    """Turnover per unit gross and alpha capture at the declared band, signal-free."""
    rows = construction.band_calibration(
        bands=(BAND,), half_life_days=half_life_days, days=252 * 10, weight_cap=WEIGHT_CAP
    )["rows"]
    row = rows[f"band_{BAND:g}"]
    return {"turnover": float(row["annual_turnover"]), "capture": float(row["alpha_capture"])}


def cost_ir_drag(turnover_per_gross: float) -> float:
    """Leverage-invariant: cost and volatility both scale with gross."""
    return turnover_per_gross * COST_PER_TURNOVER_UNIT_BP / (VOL_PER_UNIT_GROSS * 10_000.0)


def required_daily_ic(
    net_sharpe: float, half_life_days: float, breadth: float = EFFECTIVE_BREADTH_PER_DAY
) -> float:
    """Cross-sectional IC of the forecast on the next day's return needed for a net Sharpe.

    Daily returns are independent, so a daily-rebalanced book's IR is
    `TC x capture x IC_daily x sqrt(breadth x 252)` whatever the forecast's
    persistence; persistence enters through turnover and capture only.
    """
    law = band_law(half_life_days)
    gross_needed = net_sharpe + cost_ir_drag(law["turnover"])
    return gross_needed / (
        TRANSFER_COEFFICIENT * law["capture"] * math.sqrt(breadth * TRADING_DAYS)
    )


def horizon_ic(daily_ic: float, half_life_days: float) -> float:
    """IC on the return over `h` days of an AR(1) forecast with half-life `h`.

    `corr(alpha_t, r_{t+1} + ... + r_{t+h}) = IC_daily x sum_{k<h} rho^k / sqrt(h)`,
    `rho = 0.5^(1/h)`. Constant alpha over the horizon would give `IC_daily x sqrt(h)`,
    which overstates what a decaying forecast has to show.
    """
    h = max(int(round(half_life_days)), 1)
    rho = 0.5 ** (1.0 / h)
    return daily_ic * sum(rho**k for k in range(h)) / math.sqrt(h)


def required_horizon_ic(
    net_sharpe: float, half_life_days: float, breadth: float = EFFECTIVE_BREADTH_PER_DAY
) -> float:
    return horizon_ic(required_daily_ic(net_sharpe, half_life_days, breadth), half_life_days)


def continuous_book_table() -> dict[str, Any]:
    rows: dict[str, Any] = {}
    for half_life in HALF_LIVES_DAYS:
        law = band_law(half_life)
        drag = cost_ir_drag(law["turnover"])
        rows[f"half_life_{half_life:g}d"] = {
            "turnover_per_unit_gross": law["turnover"],
            "alpha_capture": law["capture"],
            "cost_ir_drag": round(drag, 3),
            "required_gross_ir": {f"{s:g}": round(s + drag, 3) for s in NET_SHARPE_SCENARIOS},
            "required_horizon_ic": {
                f"{s:g}": round(required_horizon_ic(s, half_life), 4) for s in NET_SHARPE_SCENARIOS
            },
            "required_daily_ic_at_net_0_5": {
                f"breadth_{b:g}": round(required_daily_ic(0.5, half_life, b), 4)
                for b in (EFFECTIVE_BREADTH_PER_DAY, BREADTH_SENSITIVITY)
            },
        }
    return {
        "vol_per_unit_gross": VOL_PER_UNIT_GROSS,
        "cost_per_turnover_unit_bp": COST_PER_TURNOVER_UNIT_BP,
        "effective_breadth_per_day_assumed": EFFECTIVE_BREADTH_PER_DAY,
        "breadth_sensitivity": BREADTH_SENSITIVITY,
        "transfer_coefficient": TRANSFER_COEFFICIENT,
        "band": BAND,
        "rows": rows,
    }


#: Gaussian drawdown scenario: paths, years, seed. Deterministic.
DRAWDOWN_PATHS: Final[int] = 2000
DRAWDOWN_YEARS: Final[int] = 10
DRAWDOWN_SEED: Final[int] = 20260915


@cache
def gaussian_drawdown(net_sharpe: float) -> dict[str, float]:
    """Max drawdown over ten years and the chance a five-year window loses, at any vol.

    Expressed in units of annual volatility, so it holds for every vol target.
    """
    days = int(TRADING_DAYS) * DRAWDOWN_YEARS
    rng = np.random.default_rng(DRAWDOWN_SEED)
    daily = rng.standard_normal((DRAWDOWN_PATHS, days)) / math.sqrt(TRADING_DAYS)
    daily += net_sharpe / TRADING_DAYS
    wealth = np.cumsum(daily, axis=1)
    drawdown = np.maximum.accumulate(np.maximum(wealth, 0.0), axis=1) - wealth
    worst = drawdown.max(axis=1)
    five = int(TRADING_DAYS) * 5
    return {
        "median_max_drawdown_in_vol_units": round(float(np.median(worst)), 3),
        "p95_max_drawdown_in_vol_units": round(float(np.quantile(worst, 0.95)), 3),
        "probability_first_five_years_negative": round(float(np.mean(wealth[:, five - 1] < 0)), 3),
    }


def return_and_leverage_table() -> dict[str, Any]:
    """Annual net return, gross leverage and drawdown at each volatility target and net Sharpe."""
    rows: dict[str, Any] = {}
    for vol in VOL_TARGETS:
        leverage = vol / VOL_PER_UNIT_GROSS
        rows[f"vol_{vol:g}"] = {
            "gross_leverage": round(leverage, 2),
            "within_reused_leverage_cap": leverage <= MAX_LEVERAGE,
            "annual_net_return": {f"{s:g}": round(s * vol, 4) for s in NET_SHARPE_SCENARIOS},
            "median_max_drawdown_10y": {
                f"{s:g}": round(gaussian_drawdown(s)["median_max_drawdown_in_vol_units"] * vol, 3)
                for s in NET_SHARPE_SCENARIOS
            },
            "p95_max_drawdown_10y": {
                f"{s:g}": round(gaussian_drawdown(s)["p95_max_drawdown_in_vol_units"] * vol, 3)
                for s in NET_SHARPE_SCENARIOS
            },
        }
    return {
        "max_leverage_of_reused_layer": MAX_LEVERAGE,
        "net_sharpe_needed_for_5pct": {f"vol_{v:g}": round(0.05 / v, 3) for v in VOL_TARGETS},
        "net_sharpe_needed_for_10pct": {f"vol_{v:g}": round(0.10 / v, 3) for v in VOL_TARGETS},
        "probability_first_five_years_negative": {
            f"{s:g}": gaussian_drawdown(s)["probability_first_five_years_negative"]
            for s in NET_SHARPE_SCENARIOS
        },
        "drawdown_model": "gaussian iid daily, 2000 paths x 10 years, fat tails not modelled",
        "rows": rows,
    }


#: Event book assumptions, all explicit.
DAILY_SD_ONE_SIDE_UNIT_BP: Final[float] = round(
    2.0 * VOL_PER_UNIT_GROSS * 10_000.0 / math.sqrt(TRADING_DAYS), 2
)
CONCENTRATED_POSITION_ANNUAL_VOL: Final[float] = 0.07
DAILY_SD_CONCENTRATED_BP: Final[float] = round(
    CONCENTRATED_POSITION_ANNUAL_VOL * 10_000.0 / math.sqrt(TRADING_DAYS), 2
)
EVENT_DAY_VOL_MULTIPLE: Final[float] = 1.5
EVENT_ROUND_TRIP_CHARGED_BP: Final[float] = 4.0 * CHARGED_ONE_WAY_BP
EVENT_ROUND_TRIP_PAIR_BP: Final[float] = PAIR_ROUNDTRIP_BP
CURRENCY_SLOTS: Final[float] = 8.0


def _event_edges(
    events_per_year: float, hold_days: float, net_sharpe: float, daily_sd: float
) -> tuple[float, float, float]:
    sd_hold = daily_sd * math.sqrt(EVENT_DAY_VOL_MULTIPLE**2 + max(hold_days - 1.0, 0.0))
    over_cost = net_sharpe * sd_hold / math.sqrt(events_per_year)
    concurrent = events_per_year * hold_days / TRADING_DAYS
    annual_sd_per_position = sd_hold * math.sqrt(events_per_year / max(concurrent, 1e-9)) / 10_000.0
    leverage = 0.10 * math.sqrt(max(concurrent, 1e-9)) / annual_sd_per_position
    return sd_hold, over_cost, leverage


def event_book(events_per_year: float, hold_days: float, net_sharpe: float) -> dict[str, float]:
    """Per-event edge a dated-event book needs, and the leverage it takes.

    One event = one currency-vs-basket position of one-side notional 1, held
    `hold_days`, with the first day at `EVENT_DAY_VOL_MULTIPLE` times normal
    volatility. Events are treated as independent, which flatters the answer.
    """
    sd_hold, over_cost, leverage = _event_edges(
        events_per_year, hold_days, net_sharpe, DAILY_SD_ONE_SIDE_UNIT_BP
    )
    sd_conc, over_cost_conc, leverage_conc = _event_edges(
        events_per_year, hold_days, net_sharpe, DAILY_SD_CONCENTRATED_BP
    )
    concurrent = events_per_year * hold_days / TRADING_DAYS
    return {
        "events_per_year": events_per_year,
        "hold_days": hold_days,
        "sd_per_event_bp": round(sd_hold, 2),
        "required_edge_bp_charged_cost": round(over_cost + EVENT_ROUND_TRIP_CHARGED_BP, 2),
        "required_edge_bp_pair_cost": round(over_cost + EVENT_ROUND_TRIP_PAIR_BP, 2),
        "required_edge_in_event_sd_charged": round(
            (over_cost + EVENT_ROUND_TRIP_CHARGED_BP) / sd_hold, 4
        ),
        "required_edge_bp_charged_cost_concentrated": round(
            over_cost_conc + EVENT_ROUND_TRIP_CHARGED_BP, 2
        ),
        "mean_concurrent_positions": round(concurrent, 2),
        "share_of_currency_slots": round(min(concurrent / CURRENCY_SLOTS, 1.0), 3),
        "share_of_days_with_a_position": round(1.0 - math.exp(-concurrent), 3),
        "gross_leverage_at_10pct_vol": round(leverage, 2),
        "gross_leverage_at_10pct_vol_concentrated": round(leverage_conc, 2),
    }


#: 34.4 a year is the measured decision count of the four central banks whose
#: calendars can be acquired (`scripts/research/feasibility/inventory.py`, C01).
EVENT_SCENARIOS: Final[tuple[tuple[float, float], ...]] = (
    (34.4, 3.0),
    (150.0, 3.0),
    (300.0, 2.0),
    (300.0, 5.0),
)


def event_book_table() -> dict[str, Any]:
    return {
        "daily_sd_one_side_unit_bp": DAILY_SD_ONE_SIDE_UNIT_BP,
        "daily_sd_concentrated_bp": DAILY_SD_CONCENTRATED_BP,
        "concentrated_position_annual_vol_assumed": CONCENTRATED_POSITION_ANNUAL_VOL,
        "event_day_vol_multiple": EVENT_DAY_VOL_MULTIPLE,
        "round_trip_charged_bp": EVENT_ROUND_TRIP_CHARGED_BP,
        "round_trip_pair_bp": EVENT_ROUND_TRIP_PAIR_BP,
        "rows": {
            f"n{n:g}_h{h:g}_s{s:g}": event_book(n, h, s)
            for n, h in EVENT_SCENARIOS
            for s in NET_SHARPE_SCENARIOS
        },
    }


Z_ONE_SIDED_5PCT: Final[float] = 1.645
Z_POWER_80PCT: Final[float] = 0.8416


def sample_years_needed(net_sharpe: float, power: float = 0.5) -> float:
    """Years of out-of-sample daily P&L for a one-sided 5% test to detect the Sharpe.

    `t = S x sqrt(years)`. At 50% power the expected t just reaches the critical
    value; at 80% it must exceed it by `z_0.80`. Development does not require this,
    but it bounds what any seen-data study can decide.
    """
    z_power = {0.5: 0.0, 0.8: Z_POWER_80PCT}[power]
    return round(((Z_ONE_SIDED_5PCT + z_power) / net_sharpe) ** 2, 2)


def calibration_from_record(root: Path) -> dict[str, float]:
    record = json.loads((root / TRACK_1_RECORD).read_text(encoding="utf-8"))
    primary = record["primary"]["summary"]
    return {
        "realized_annual_vol": primary["realized_annual_vol"],
        "mean_currency_gross": primary["mean_currency_gross"],
        "turnover_per_unit_gross": primary["turnover_round_trips_per_year_per_unit_gross"],
        "raw_to_neutralised_corr": primary["mean_raw_to_neutralised_score_corr"],
        "gross_sharpe": primary["gross_sharpe"],
        "net_sharpe": primary["net_sharpe"],
        "share_days_at_leverage_cap": primary["share_days_at_leverage_cap"],
    }


__all__ = [
    "BREADTH_SENSITIVITY",
    "COST_PER_TURNOVER_UNIT_BP",
    "EFFECTIVE_BREADTH_PER_DAY",
    "EVENT_SCENARIOS",
    "HALF_LIVES_DAYS",
    "MAX_LEVERAGE",
    "NET_SHARPE_SCENARIOS",
    "TRANSFER_COEFFICIENT",
    "VOL_PER_UNIT_GROSS",
    "band_law",
    "calibration_from_record",
    "continuous_book_table",
    "cost_ir_drag",
    "event_book",
    "event_book_table",
    "gaussian_drawdown",
    "horizon_ic",
    "required_daily_ic",
    "required_horizon_ic",
    "return_and_leverage_table",
    "sample_years_needed",
]
