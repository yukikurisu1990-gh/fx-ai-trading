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
that mean in annual return at a volatility target, and what leverage and
turnover does it take. It never says a source *has* that quality.

Calibration, every number traceable
-----------------------------------

* Volatility per unit of currency gross, **measured** on the committed Track 1
  record: the unlevered diagnostic book realised 2.3704% a year at mean gross
  0.9771 (`artifacts/research/continuous_portfolio/development.json`).
* Turnover as a function of forecast half-life: the signal-free band law of the
  same construction (`continuous_portfolio.construction.band_calibration`,
  capped weights, band 0.10), computed here, not measured on a market.
* Cost: the inherited conservative convention, 1.703 bp per unit of
  `sum|delta|` (3.406 bp per turnover unit).
* Effective cross-sectional breadth: four independent currency directions a day
  once the common factor is removed (the programme's measured 3.2-6.5 range).
* Transfer coefficient: 0.90, the measured correlation between raw and
  neutralised scores in Track 1 — an assumption about new sources, stated.
"""

from __future__ import annotations

import json
import math
from functools import cache
from pathlib import Path
from typing import Any, Final

from scripts.research.continuous_portfolio import CHARGED_ONE_WAY_BP, construction
from scripts.research.feasibility.inventory import PAIR_ROUNDTRIP_BP

TRADING_DAYS: Final[float] = 252.0
TRACK_1_RECORD: Final[str] = "artifacts/research/continuous_portfolio/development.json"

#: Measured (see module docstring); the tests re-derive both from the record.
VOL_PER_UNIT_GROSS: Final[float] = round(0.023704 / 0.9771, 6)
EFFECTIVE_BREADTH_PER_DAY: Final[float] = 4.0
TRANSFER_COEFFICIENT: Final[float] = 0.90
BAND: Final[float] = 0.10
WEIGHT_CAP: Final[float] = 0.25

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


def independent_bets_per_year(half_life_days: float) -> float:
    return EFFECTIVE_BREADTH_PER_DAY * TRADING_DAYS / max(half_life_days, 1.0)


def required_horizon_ic(net_sharpe: float, half_life_days: float) -> float:
    """Cross-sectional IC on the forecast-horizon return needed for a net Sharpe.

    `gross_ir = TC x capture x IC x sqrt(independent bets a year)` and
    `net = gross - cost drag`, solved for IC.
    """
    law = band_law(half_life_days)
    gross_needed = net_sharpe + cost_ir_drag(law["turnover"])
    scale = (
        TRANSFER_COEFFICIENT * law["capture"] * math.sqrt(independent_bets_per_year(half_life_days))
    )
    return gross_needed / scale


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
            "daily_equivalent_ic_at_net_0_5": round(
                required_horizon_ic(0.5, half_life) / math.sqrt(max(half_life, 1.0)), 4
            ),
        }
    return {
        "vol_per_unit_gross": VOL_PER_UNIT_GROSS,
        "cost_per_turnover_unit_bp": COST_PER_TURNOVER_UNIT_BP,
        "effective_breadth_per_day": EFFECTIVE_BREADTH_PER_DAY,
        "transfer_coefficient": TRANSFER_COEFFICIENT,
        "band": BAND,
        "rows": rows,
    }


def return_and_leverage_table() -> dict[str, Any]:
    """Annual net return and gross leverage at each volatility target and net Sharpe."""
    rows: dict[str, Any] = {}
    for vol in VOL_TARGETS:
        rows[f"vol_{vol:g}"] = {
            "gross_leverage": round(vol / VOL_PER_UNIT_GROSS, 2),
            "annual_net_return": {f"{s:g}": round(s * vol, 4) for s in NET_SHARPE_SCENARIOS},
        }
    return {
        "net_sharpe_needed_for_5pct": {f"vol_{v:g}": round(0.05 / v, 3) for v in VOL_TARGETS},
        "net_sharpe_needed_for_10pct": {f"vol_{v:g}": round(0.10 / v, 3) for v in VOL_TARGETS},
        "rows": rows,
    }


#: Event book assumptions, all explicit.
DAILY_SD_ONE_SIDE_UNIT_BP: Final[float] = round(
    2.0 * VOL_PER_UNIT_GROSS * 10_000.0 / math.sqrt(TRADING_DAYS), 2
)
EVENT_DAY_VOL_MULTIPLE: Final[float] = 1.5
EVENT_ROUND_TRIP_CHARGED_BP: Final[float] = 4.0 * CHARGED_ONE_WAY_BP
EVENT_ROUND_TRIP_PAIR_BP: Final[float] = PAIR_ROUNDTRIP_BP


def event_book(events_per_year: float, hold_days: float, net_sharpe: float) -> dict[str, float]:
    """Per-event edge a dated-event book needs, and the leverage it takes.

    One event = one currency-vs-basket position of one-side notional 1, held
    `hold_days`, with the first day at `EVENT_DAY_VOL_MULTIPLE` times normal
    volatility. Events are treated as independent, which flatters the answer.
    """
    sd_hold = DAILY_SD_ONE_SIDE_UNIT_BP * math.sqrt(
        EVENT_DAY_VOL_MULTIPLE**2 + max(hold_days - 1.0, 0.0)
    )
    edge_over_cost = net_sharpe * sd_hold / math.sqrt(events_per_year)
    concurrent = events_per_year * hold_days / TRADING_DAYS
    annual_sd_per_position = sd_hold * math.sqrt(events_per_year / max(concurrent, 1e-9)) / 10_000.0
    gross_at_10pct = 0.10 * math.sqrt(max(concurrent, 1e-9)) / annual_sd_per_position
    return {
        "events_per_year": events_per_year,
        "hold_days": hold_days,
        "sd_per_event_bp": round(sd_hold, 2),
        "required_edge_bp_charged_cost": round(edge_over_cost + EVENT_ROUND_TRIP_CHARGED_BP, 2),
        "required_edge_bp_pair_cost": round(edge_over_cost + EVENT_ROUND_TRIP_PAIR_BP, 2),
        "required_edge_in_event_sd_charged": round(
            (edge_over_cost + EVENT_ROUND_TRIP_CHARGED_BP) / sd_hold, 4
        ),
        "mean_concurrent_positions": round(concurrent, 2),
        "capital_utilisation_share_of_days": round(min(concurrent / 8.0, 1.0), 3),
        "gross_leverage_at_10pct_vol": round(gross_at_10pct, 2),
    }


EVENT_SCENARIOS: Final[tuple[tuple[float, float], ...]] = (
    (60.0, 3.0),
    (150.0, 3.0),
    (300.0, 2.0),
    (300.0, 5.0),
)


def event_book_table() -> dict[str, Any]:
    return {
        "daily_sd_one_side_unit_bp": DAILY_SD_ONE_SIDE_UNIT_BP,
        "event_day_vol_multiple": EVENT_DAY_VOL_MULTIPLE,
        "round_trip_charged_bp": EVENT_ROUND_TRIP_CHARGED_BP,
        "round_trip_pair_bp": EVENT_ROUND_TRIP_PAIR_BP,
        "rows": {
            f"n{int(n)}_h{int(h)}_s{s:g}": event_book(n, h, s)
            for n, h in EVENT_SCENARIOS
            for s in NET_SHARPE_SCENARIOS
        },
    }


def sample_years_needed(net_sharpe: float, z: float = 1.645) -> float:
    """Years of out-of-sample daily P&L for a one-sided test at the given z to see the Sharpe.

    `t = S x sqrt(years)`; development does not require this, but it bounds what any
    seen-data study can say and why new independent history matters.
    """
    return round((z / net_sharpe) ** 2, 2)


def calibration_from_record(root: Path) -> dict[str, float]:
    record = json.loads((root / TRACK_1_RECORD).read_text(encoding="utf-8"))
    unlevered = record["diagnostics"]["diag_unlevered"]["summary"]
    return {
        "realized_annual_vol": unlevered["realized_annual_vol"],
        "mean_currency_gross": unlevered["mean_currency_gross"],
        "turnover_per_unit_gross": unlevered["turnover_round_trips_per_year_per_unit_gross"],
        "raw_to_neutralised_corr": record["primary"]["summary"][
            "mean_raw_to_neutralised_score_corr"
        ],
    }


__all__ = [
    "COST_PER_TURNOVER_UNIT_BP",
    "EFFECTIVE_BREADTH_PER_DAY",
    "EVENT_SCENARIOS",
    "HALF_LIVES_DAYS",
    "NET_SHARPE_SCENARIOS",
    "TRANSFER_COEFFICIENT",
    "VOL_PER_UNIT_GROSS",
    "band_law",
    "calibration_from_record",
    "continuous_book_table",
    "cost_ir_drag",
    "event_book",
    "event_book_table",
    "required_horizon_ic",
    "return_and_leverage_table",
    "sample_years_needed",
]
