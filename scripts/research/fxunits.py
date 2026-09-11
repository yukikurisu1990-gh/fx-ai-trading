"""One unit for every quantity in the FX spot programme: **basis points of mid**.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Why this module exists
----------------------

The feasibility frontier that motivated this research phase mixed two units and
two universes inside one table. Calendar-horizon rows were basis points measured
across the median of twenty pairs; event-window rows were **pips** measured on
`EUR_USD` alone, and the "hurdle" beside them was a pips figure. Pips and basis
points happen to be within about ten per cent of each other for `EUR_USD`, which
is exactly why the mistake survived a reading — for `USD_JPY` one pip is 0.67 bp,
so the two are not interchangeable and a table that mixes them is not a table.

A pip is a **quote-currency** unit whose economic size depends on the price
level. A basis point is a **relative** unit. Only the second can be added across
pairs, compared with a portfolio return, or netted against a cost. So:

> Every return, cost, hurdle, minimum detectable effect and confidence interval
> in this programme is expressed in **basis points of the mid price at the moment
> of the trade**, converted per observation and never with a panel-wide constant.

`pips_to_bp` is the only conversion, and `verify_unit_consistency` is the machine
check that a set of quantities was produced by it. A number that reaches a
results document without passing through here is a defect, not a rounding
difference.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

#: The programme's cost model, carried over unchanged: one spread plus half a
#: pip for a round trip, on mid-quoted returns.
HALF_SPREAD_ADDITION_PIPS: Final[float] = 0.5

#: A quantity is "decidable" when the design can detect an effect at least as
#: small as this multiple of the measured round trip. Two, so a cell has to be
#: visible at twice the cost it will actually pay.
COST_MULTIPLE_FOR_HURDLE: Final[float] = 2.0

#: z(0.975) + z(0.80): a null dispersion becomes a minimum detectable effect at
#: 80% power, two-sided 5%.
POWER_MULTIPLIER: Final[float] = 2.802

UNIT: Final[str] = "bp_of_mid"


def pips_to_bp(pips: Any, pip_size: Any, mid: Any) -> Any:
    """Convert a pip quantity to basis points of the mid price.

    `mid` is per observation, never a panel constant: the same one-pip move is
    0.93 bp on `EUR_USD` at 1.08 and 0.67 bp on `USD_JPY` at 150, and a constant
    would smear that difference across a four-year panel.
    """
    return np.asarray(pips) * np.asarray(pip_size) / np.asarray(mid) * 1e4


def roundtrip_cost_bp(frame: pd.DataFrame, index: Any = None) -> Any:
    """The round trip a trade opened on those bars would pay, in bp.

    Uses each bar's own spread and its own mid, because both vary by pair, by
    hour and by session — and the programme has twice mistaken a composition
    difference in one of them for an effect.
    """
    spread = frame["spread_close_pips"].to_numpy(dtype=float)
    pip = frame["pip_size"].to_numpy(dtype=float)
    mid = frame["mid_c"].to_numpy(dtype=float)
    cost = pips_to_bp(spread + HALF_SPREAD_ADDITION_PIPS, pip, mid)
    return cost if index is None else cost[index]


def hurdle_bp(cost_bp: Any) -> float:
    """The effect a design must be able to see before it is worth running."""
    return float(COST_MULTIPLE_FOR_HURDLE * np.mean(cost_bp))


def mde_bp(null_means_bp: Any) -> float:
    """Minimum detectable effect at 80% power, from a null distribution of the mean.

    The dispersion must come from a null that preserves the dependence in the
    data. An i.i.d. standard error over correlated observations understates it —
    in this programme by about a factor of three on one occasion, and by
    a factor of about two on another.
    """
    values = np.asarray(null_means_bp, dtype=float)
    return float(POWER_MULTIPLIER * np.std(values, ddof=1))


def verify_unit_consistency(record: dict[str, Any]) -> dict[str, Any]:
    """Machine check that every reported quantity is in one unit.

    Returns a verdict rather than raising, so the artifact can carry the failure.
    A field whose name does not end in `_bp` and is not on the exempt list is a
    unit that escaped conversion.

    A subtree that holds no monetary quantity at all — a table of how many days a
    benchmark fix landed on each UTC hour, say — declares itself with
    `{"_unit": "count"}` and is skipped. That is a declaration by the author,
    checked nowhere else, so it is deliberately the *only* escape and it is
    visible in the artifact: widening the exempt list to cover dynamic keys like
    `"15:00"` would have been endless and would have hidden real fields too.
    """
    exempt = {
        "n",
        "n_events",
        "n_days",
        "n_pairs",
        "n_currencies",
        "horizon_minutes",
        "unit",
        "decidable",
        "label",
        "panel",
        "currency",
        "pair",
        "p_value",
        "family_max_p",
        "breadth",
        "power_multiplier",
        "cost_multiple",
        "ratio",
        "tail_share",
        "hit_rate",
        "sign",
        #: Design descriptors and unit-free ratios. Named one by one rather than
        #: hidden behind a `_unit` marker on their parent, because a marker
        #: placed on the enclosing dict once skipped four monetary siblings with
        #: it and the audit that found that was right to call it a loosening.
        "years",
        "signal_draws",
        "events_per_year",
        "break_even_gross_ir",
        #: The worst of the two panels' break-even ratios, and the smaller of
        #: their event counts. Both surfaced the first time the audit was widened
        #: past the `panels` subtree, which is the widening working.
        "break_even_gross_ir_worst",
        "n_events_min",
        "dispersion_over_median_cost",
        "feasible_events_per_year_floor",
        "n_partial_days_excluded",
        "pair_windows_dropped_as_far_from_the_moment",
        "hold_hours_median",
        #: Track 3's unit-free execution quantities. Rates and shares, a count of
        #: bars, and the ratio the success bands are read from.
        "fill_rate",
        "missed_rate",
        "capture_share_of_quoted",
        "fill_bars_median",
        "cost_ratio",
        "cost_ratio_spread",
        "wait_bars",
        "drift_bars",
        "n_bars",
        "n_measurable",
        "n_cells",
        "n_feasible",
        "sub_steps_per_bar",
        "seed",
        #: The one place a pips figure is legitimate: a fill rule is written in
        #: the broker's own tick, and this is a *rule parameter*, not a measured
        #: quantity. Named rather than hidden behind a `_unit` marker, because a
        #: marker on the enclosing dict once carried four monetary siblings with
        #: it.
        "penetration_pips",
        #: Two more of the same kind: the parameters of the no-information
        #: generator, which is a *specification* of a synthetic market rather
        #: than a measurement taken from one.
        "benchmark_spread_pips",
        "benchmark_sigma_pips_per_bar",
    }
    offenders: list[str] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            if node.get("_unit") == "count":
                return
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    walk(value, f"{path}.{key}")
                elif isinstance(value, (int, float)) and not isinstance(value, bool):
                    name = str(key)
                    if name in exempt or name.endswith("_bp"):
                        continue
                    offenders.append(f"{path}.{name}")
        elif isinstance(node, list):
            for position, value in enumerate(node):
                if isinstance(value, (dict, list)):
                    walk(value, f"{path}[{position}]")

    walk(record, "root")
    return {
        "unit": UNIT,
        "status": "UNIT_CONSISTENCY_VERIFIED" if not offenders else "UNIT_CONSISTENCY_FAILED",
        "numeric_fields_not_in_bp": sorted(offenders),
        "convention": (
            "every return, cost, hurdle, MDE and interval is basis points of the "
            "mid price at the moment of the trade, converted per observation"
        ),
    }


__all__ = [
    "COST_MULTIPLE_FOR_HURDLE",
    "HALF_SPREAD_ADDITION_PIPS",
    "POWER_MULTIPLIER",
    "UNIT",
    "hurdle_bp",
    "mde_bp",
    "pips_to_bp",
    "roundtrip_cost_bp",
    "verify_unit_consistency",
]
