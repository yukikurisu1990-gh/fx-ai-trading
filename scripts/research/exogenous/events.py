"""Stage A — does a *forward-known* scheduled decision select a different day?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The previous package compared days a policy rate **changed** against every other
day and found the event days moved more. That population is not knowable in
advance, so the comparison bounded what an anchor could offer without being one.
Here the population is the **scheduled meeting date**, which is published months
ahead — the same comparison, on a population a position could actually have been
placed for.

Three ways this comparison goes wrong, and what is done about each
------------------------------------------------------------------

1. **Session composition.** A Sunday session is about ten bars at a 2.5 pip
   spread; a weekday is ninety-five at 1.5. Sundays were 17.5% of the control
   group and 0% of the event group last package, and pooling them produced a
   headline that reversed when matched. Days with fewer than
   `MIN_BARS_FOR_A_TRADING_DAY` bars are dropped and every ratio is computed
   **within** a day of week.
2. **Volatility regime.** Central banks meet more often in the middle of a
   tightening cycle, and a tightening cycle is a volatile period. Comparing a
   meeting day against the panel average would then measure the cycle. Every
   ratio is additionally computed within a **trailing-volatility tercile**.
3. **A null that ignores the calendar.** Re-drawing event days uniformly would
   compare against a population with a different weekday and regime mix than the
   real one. The null here re-draws **inside the same weekday and the same
   tercile**, so the calendar structure survives the permutation.

The tercile is a **matching covariate, not a signal**. It is a rank of the
trailing 60-day realised volatility inside the panel, and no trade is derived
from it anywhere in this module; the trailing window itself reads only bars
strictly before the day it labels.

Nothing here is an edge. A day that moves more is not a day whose direction is
known, and the last package's own numbers say magnitude was not the binding
constraint: 91% of ordinary days already clear the round trip.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from scripts.research.exogenous import (
    BREADTH_SHARE,
    MIN_BARS_FOR_A_TRADING_DAY,
    NULL_DRAWS,
    SEED,
    VOLATILITY_CONTEXT_DAYS,
    VOLATILITY_TERCILES,
)

#: Plan §6. The six quantities the structure is measured on; the first is what
#: the verdict reads and the other five are reported beside it.
MEASURED: tuple[str, ...] = (
    "abs_move",
    "realised",
    "spread",
    "volume",
    "range",
    "exceeds_cost",
)


def daily_table(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per trading day, with the two matching keys attached.

    `trailing_vol` is a window that is **shifted by one day**, so the value on a
    day never contains that day. A version that forgot the shift would rank a
    meeting day by its own volatility, which is exactly the quantity being
    compared. The tercile cut itself is a stratification over the panel — see
    the comment where it is built.
    """
    day = frame["ts"].dt.floor("D")
    pip = float(frame["pip_size"].iloc[0])
    grouped = frame.groupby(day)
    table = pd.DataFrame(
        {
            "bars": grouped.size(),
            "abs_move": grouped["mid_c"].apply(lambda s: abs(s.iloc[-1] - s.iloc[0])) / pip,
            "realised": grouped["mid_c"].apply(lambda s: float(s.diff().std() or 0.0)) / pip,
            "spread": grouped["spread_close_pips"].median(),
            "cost": grouped["roundtrip_cost"].median(),
            "range": (grouped["mid_h"].max() - grouped["mid_l"].min()) / pip,
        }
    )
    table["volume"] = grouped["volume"].sum(min_count=1) if "volume" in frame.columns else np.nan
    table["exceeds_cost"] = (table["abs_move"] > table["cost"]).astype(float)
    table["dayofweek"] = table.index.dayofweek
    table = table[table["bars"] >= MIN_BARS_FOR_A_TRADING_DAY].copy()
    if table.empty:
        return table

    trailing = (
        table["realised"]
        .shift(1)
        .rolling(VOLATILITY_CONTEXT_DAYS, min_periods=VOLATILITY_CONTEXT_DAYS // 2)
        .mean()
    )
    table["trailing_vol"] = trailing
    #: The tercile boundaries are cut on the panel's whole distribution. That is
    #: a **stratification**, not a signal: it decides which days are compared
    #: with which, the null permutes inside the same strata, and no position is
    #: taken from it anywhere. The quantity being stratified on — `trailing_vol`
    #: — is strictly backward-looking, which is the property the tests pin.
    ranked = trailing.rank(pct=True)
    tercile = pd.Series(np.nan, index=table.index)
    for index in range(VOLATILITY_TERCILES):
        lower = index / VOLATILITY_TERCILES
        upper = (index + 1) / VOLATILITY_TERCILES
        mask = (ranked > lower) & (ranked <= upper) if index else (ranked <= upper)
        tercile[mask] = float(index)
    table["vol_tercile"] = tercile
    return table.dropna(subset=["vol_tercile"])


def _cells(table: pd.DataFrame) -> list[pd.DataFrame]:
    return [block for _, block in table.groupby(["dayofweek", "vol_tercile"])]


def matched_ratio(table: pd.DataFrame, event: pd.Series, column: str) -> float | None:
    """Event ÷ other inside every (weekday × tercile) cell, then pooled.

    A cell with no event day or no control day contributes nothing rather than
    biasing the ratio, and the pooled value is the ratio of the mean of the cell
    numerators to the mean of the cell denominators — not the mean of the cell
    ratios, which a single tiny denominator would dominate.
    """
    numerator: list[float] = []
    denominator: list[float] = []
    for block in _cells(table):
        inside = event.reindex(block.index).fillna(False).to_numpy(dtype=bool)
        on = block.loc[inside, column].dropna()
        off = block.loc[~inside, column].dropna()
        if on.empty or off.empty:
            continue
        numerator.append(float(on.mean()))
        denominator.append(float(off.mean()))
    if not numerator or not float(np.mean(denominator)):
        return None
    return float(np.mean(numerator) / np.mean(denominator))


def pooled_ratio(table: pd.DataFrame, event: pd.Series, column: str) -> float | None:
    """The unmatched comparison, reported only as a diagnostic."""
    inside = event.reindex(table.index).fillna(False).to_numpy(dtype=bool)
    on = table.loc[inside, column].dropna()
    off = table.loc[~inside, column].dropna()
    if on.empty or off.empty or not float(off.mean()):
        return None
    return float(on.mean() / off.mean())


def _event_mask(table: pd.DataFrame, dates: set[str]) -> pd.Series:
    """Compare **calendar dates**, never timestamps.

    The panel index is tz-aware UTC and a plain `pd.Timestamp("2021-04-27")` is
    not, so an `in` test against a set of naive timestamps matches nothing and
    every ratio comes back `None`. That is what the first version of this
    function did.
    """
    days = {pd.Timestamp(value).date() for value in dates}
    return pd.Series([ts.date() in days for ts in table.index], index=table.index)


def _permute(table: pd.DataFrame, event: pd.Series, rng: np.random.Generator) -> pd.Series:
    """Re-draw the event days inside their own (weekday × tercile) cells.

    The number of event days in every cell is preserved exactly, so the draw
    cannot change the weekday mix or the regime mix — only which days inside a
    cell were meetings.
    """
    drawn = pd.Series(False, index=table.index)
    for block in _cells(table):
        inside = event.reindex(block.index).fillna(False)
        count = int(inside.sum())
        if not count or count == len(block):
            drawn.loc[block.index] = inside.to_numpy(dtype=bool)
            continue
        picked = rng.choice(len(block), size=count, replace=False)
        drawn.loc[block.index[picked]] = True
    return drawn


def population(
    panel: dict[str, pd.DataFrame],
    calendar: dict[str, list[str]],
    *,
    draws: int = NULL_DRAWS,
    seed: int = SEED,
) -> dict[str, Any]:
    """The scheduled-event comparison for one panel, per pair and pooled.

    A pair with no covered leg is **excluded and named**, so the coverage limit
    shows up in the artifact rather than being absorbed into a pair count.
    """
    from scripts.research.exogenous.calendars import event_dates_for_pair

    rng = np.random.default_rng(seed)
    rows: list[dict[str, Any]] = []
    excluded: list[str] = []
    null_ratios: list[list[float]] = []

    for pair, frame in sorted(panel.items()):
        dates = event_dates_for_pair(pair, calendar)
        if not dates:
            excluded.append(pair)
            continue
        table = daily_table(frame)
        if table.empty:
            excluded.append(pair)
            continue
        event = _event_mask(table, dates)
        if not bool(event.any()):
            excluded.append(pair)
            continue

        row: dict[str, Any] = {
            "pair": pair,
            "event_days": int(event.sum()),
            "other_days": int((~event).sum()),
        }
        for column in MEASURED:
            row[column] = {
                "matched_ratio": matched_ratio(table, event, column),
                "pooled_ratio": pooled_ratio(table, event, column),
                "event_mean": float(table.loc[event.to_numpy(dtype=bool), column].mean()),
                "other_mean": float(table.loc[~event.to_numpy(dtype=bool), column].mean()),
            }
        rows.append(row)

        pair_null = []
        for _ in range(draws):
            value = matched_ratio(table, _permute(table, event, rng), "abs_move")
            if value is not None:
                pair_null.append(value)
        null_ratios.append(pair_null)

    def _pool(column: str, key: str) -> float | None:
        values = [r[column][key] for r in rows if r[column][key] is not None]
        return float(np.mean(values)) if values else None

    pooled = {
        column: {
            "matched_ratio": _pool(column, "matched_ratio"),
            "pooled_ratio": _pool(column, "pooled_ratio"),
            "pairs_matched_above_one": sum(
                1 for r in rows if (r[column]["matched_ratio"] or 0.0) > 1.0
            ),
        }
        for column in MEASURED
    }

    observed = pooled["abs_move"]["matched_ratio"]
    null_draw_means: list[float] = []
    if null_ratios and all(null_ratios):
        width = min(len(values) for values in null_ratios)
        null_draw_means = [
            float(np.mean([values[index] for values in null_ratios])) for index in range(width)
        ]
    p_value = None
    if null_draw_means and observed is not None:
        extreme = sum(1 for value in null_draw_means if abs(value - 1.0) >= abs(observed - 1.0))
        p_value = (extreme + 1) / (len(null_draw_means) + 1)

    return {
        "pairs": len(rows),
        "excluded_pairs": excluded,
        "per_pair": rows,
        "pooled": pooled,
        "null_draws": len(null_draw_means),
        "abs_move_permutation_p": p_value,
        "null_mean": float(np.mean(null_draw_means)) if null_draw_means else None,
    }


def verdict(per_panel: dict[str, dict[str, Any]], deciding: tuple[str, ...]) -> dict[str, Any]:
    """Plan §6, read mechanically off the matched ratios.

    Every clause fails closed: a missing panel, a missing ratio or a missing
    permutation is a failure, not a pass. `all()` over an empty list is `True`,
    which is how the previous package's integration verdict could flip to
    "adds value" on absent data.
    """
    rows = [per_panel[panel] for panel in deciding if panel in per_panel]
    complete = len(rows) == len(deciding) and bool(rows)

    ratios = [row["pooled"]["abs_move"]["matched_ratio"] for row in rows]
    above_one = complete and all(value is not None and value > 1.0 for value in ratios)

    breadth_ok = complete and all(
        row["pairs"] > 0
        and row["pooled"]["abs_move"]["pairs_matched_above_one"] >= BREADTH_SHARE * row["pairs"]
        for row in rows
    )
    p_values = [row["abs_move_permutation_p"] for row in rows]
    significant = complete and all(value is not None and value < 0.05 for value in p_values)

    supported = bool(above_one and breadth_ok and significant)
    spreads = [row["pooled"]["spread"]["matched_ratio"] for row in rows]
    return {
        "status": (
            "FORWARD_KNOWN_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED"
            if supported
            else "SCHEDULED_EVENT_OPPORTUNITY_STRUCTURE_NOT_SUPPORTED"
        ),
        "complete": complete,
        "abs_move_matched": ratios,
        "abs_move_pooled_unmatched": [row["pooled"]["abs_move"]["pooled_ratio"] for row in rows],
        "breadth": [
            (row["pooled"]["abs_move"]["pairs_matched_above_one"], row["pairs"]) for row in rows
        ],
        "permutation_p": p_values,
        "spread_matched": spreads,
        "exceeds_cost_matched": [row["pooled"]["exceeds_cost"]["matched_ratio"] for row in rows],
        "cost_advantage_status": (
            "EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED"
            if not (spreads and all(v is not None and v < 1.0 for v in spreads))
            else "EVENT_DAY_SPREAD_NARROWER_ON_BOTH_DECIDING_PANELS"
        ),
        "note": (
            "A movement result is an opportunity result. It is not an "
            "expected-return source and may not be reported as one."
        ),
    }


__all__ = [
    "MEASURED",
    "daily_table",
    "matched_ratio",
    "pooled_ratio",
    "population",
    "verdict",
]
