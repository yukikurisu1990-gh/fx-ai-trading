"""B′-4 — the monthly TSMOM octave, six cells, once.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Every "momentum" this programme has tested is 4–6 days. The FX literature's
time-series momentum is 1–12 months. That octave is untested here, has a genuine
prior rather than being data-mined, and trades rarely enough that cost is not the
binding constraint — a 3-month hold turns over about four times a year against
the 50-odd times the closed families did.

**Six cells and no more.** `lookback ∈ {1, 2, 3}` months × `hold ∈ {1, 3}`
months, decided on a grid and phase-averaged over eight offsets exactly as
`round2` does, scored by the unchanged `engine.evaluate` and the unchanged
`EXPLORATORY_ASSUMPTION` cost.

The sample is stated before the result, not after
--------------------------------------------------

624 trading days is under 30 months. A 3-month lookback with a 3-month hold gives
roughly **seven non-overlapping observations per pair**, and this corpus has
returned 4.4–6.5 effective independent pairs in every round. So the screen is
powered to detect a large effect and nothing else. That is a reason to run it
once and read it modestly, not a reason to skip it: the octave is cheap to check
and expensive to leave open.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import engine, round2
from scripts.research.round_a import panels
from scripts.research.round_b_prime import MONTH_BARS, TSMOM_HOLDS, TSMOM_LOOKBACKS


def signal(frame: pd.DataFrame, *, lookback: int, hold: int, phase: int) -> pd.Series:
    """`sign(move over `lookback` months)`, decided on the grid, held.

    Causal throughout: the move ends at the decision bar and the position is
    taken from the following bar by `engine.evaluate`'s own shift.
    """
    move = frame["mid_c"] - frame["mid_c"].shift(lookback * MONTH_BARS)
    raw = pd.Series(np.sign(move.to_numpy()), index=frame.index).fillna(0.0)
    grid = np.zeros(len(frame), dtype=bool)
    grid[phase :: hold * MONTH_BARS] = True
    decided = raw.where(pd.Series(grid, index=frame.index)).ffill().fillna(0.0)
    blocked = frame["rollover"] & (decided != decided.shift(1))
    return decided.where(~blocked).ffill().fillna(0.0)


def evaluate_cell(
    panel: dict[str, pd.DataFrame],
    *,
    lookback: int,
    hold: int,
    pairs: tuple[str, ...] | None = None,
    cost_multipliers: tuple[float, ...] = (1.0, 1.25, 1.5, 2.0, 3.0),
) -> dict[str, Any]:
    """One cell, phase-averaged, cost-inclusive. Mirrors `round2.evaluate_config`."""
    chosen = pairs or tuple(panel)
    stride = hold * MONTH_BARS
    phases = list(range(0, stride, max(1, stride // round2.N_PHASES)))[: round2.N_PHASES]
    per_multiplier: dict[float, list[pd.Series]] = {m: [] for m in cost_multipliers}
    metrics: dict[str, list[dict[str, Any]]] = {pair: [] for pair in chosen}
    per_pair_series: dict[str, list[pd.Series]] = {pair: [] for pair in chosen}

    for phase in phases:
        for multiplier in cost_multipliers:
            columns = []
            for pair in chosen:
                frame = panel[pair]
                result = engine.evaluate(
                    frame,
                    signal(frame, lookback=lookback, hold=hold, phase=phase),
                    name="tsmom",
                    pair=pair,
                    cost_multiplier=multiplier,
                )
                columns.append(result.net.set_axis(frame["ts"]).rename(pair))
                if multiplier == 1.0:
                    metrics[pair].append(result.metrics)
                    per_pair_series[pair].append(result.net.set_axis(frame["ts"]))
            per_multiplier[multiplier].append(pd.concat(columns, axis=1).fillna(0.0).mean(axis=1))

    pooled = {
        m: pd.concat(series, axis=1).fillna(0.0).mean(axis=1)
        for m, series in per_multiplier.items()
    }
    base = pooled[1.0]
    equity = base.cumsum()
    per_pair = {
        pair: {
            key: float(np.mean([m[key] for m in rows]))
            for key in (
                "net_pips",
                "gross_pips",
                "cost_pips",
                "n_closed_trades",
                "turnover_per_year",
            )
        }
        for pair, rows in metrics.items()
        if rows
    }
    by_pair_net = {pair: v["net_pips"] for pair, v in per_pair.items()}
    daily = {
        pair: pd.concat(series, axis=1).fillna(0.0).mean(axis=1)
        for pair, series in per_pair_series.items()
        if series
    }
    daily_by_day = {
        pair: series.groupby(series.index.floor("D")).sum() for pair, series in daily.items()
    }
    pooled_daily = base.groupby(base.index.floor("D")).sum()

    jpy = [p for p in by_pair_net if p in panels.JPY_PAIRS]
    non_jpy = [p for p in by_pair_net if p not in panels.JPY_PAIRS]
    #: sigma-normalised: each pair's net divided by its own daily P&L volatility,
    #: so a JPY pair's larger pip numbers do not become a larger contribution
    normalised = [
        float(series.sum() / series.std()) for series in daily_by_day.values() if series.std() > 0
    ]

    return {
        "lookback_months": lookback,
        "hold_months": hold,
        "phases": len(phases),
        "net_pips_per_pair": round(float(base.sum()), 1),
        "gross_pips_per_pair": round(
            float(np.mean([v["gross_pips"] for v in per_pair.values()])), 1
        ),
        "cost_pips_per_pair": round(float(np.mean([v["cost_pips"] for v in per_pair.values()])), 1),
        "turnover_per_year": round(
            float(np.mean([v["turnover_per_year"] for v in per_pair.values()])), 2
        ),
        "closed_trades_pooled": int(sum(v["n_closed_trades"] for v in per_pair.values())),
        "max_drawdown_pips": round(float((equity - equity.cummax()).min()), 1),
        "pairs_positive": int(sum(1 for v in by_pair_net.values() if v > 0)),
        "pairs_counted": len(by_pair_net),
        "jpy_mean_net": round(float(np.mean([by_pair_net[p] for p in jpy])), 1) if jpy else None,
        "non_jpy_mean_net": round(float(np.mean([by_pair_net[p] for p in non_jpy])), 1)
        if non_jpy
        else None,
        "sigma_normalised_net": round(float(np.mean(normalised)), 3) if normalised else None,
        "effective_independent_pairs": panels.effective_independent_pairs(daily_by_day),
        "net_at_cost": {f"x{m}": round(float(series.sum()), 1) for m, series in pooled.items()},
        "tails": panels.tail_contributions(pooled_daily),
        "non_overlapping_obs_per_pair": round(
            float(len(next(iter(panel.values()))) / (max(lookback, hold) * MONTH_BARS)), 1
        ),
        "_daily": pooled_daily,
    }


def screen(panel: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    """The six cells. Nothing else may enter this family."""
    return [
        evaluate_cell(panel, lookback=lookback, hold=hold)
        for lookback in TSMOM_LOOKBACKS
        for hold in TSMOM_HOLDS
    ]


def cell_id(row: dict[str, Any]) -> str:
    return f"tsmom_lb{row['lookback_months']}m_h{row['hold_months']}m"


__all__ = ["cell_id", "evaluate_cell", "screen", "signal"]
