"""T1 — the Tradability Atlas: where does tradable movement exist at all?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

This file answers a question no previous round asked: **before** asking whether a
signal can pick the direction, is there enough movement in a given
`horizon × state` to pay for a round trip? Four rounds of directional research
have now failed, and every one of them assumed the opportunity existed and asked
only whether the sign was predictable. The atlas measures the opportunity itself.

The excursions are computed with knowledge of the future, on purpose
---------------------------------------------------------------------

`MFE` here is `max(up excursion, down excursion)` over the holding window — the
best any direction rule could possibly have reached. That is a deliberate
oracle: it is an **upper bound on capturable movement**, and its whole value is
that a cell where even the oracle cannot clear two round trips is closed to every
strategy, not merely to the ones tried so far.

The plan (§4.5) records the corresponding prohibition, and it is repeated here
because this is the file that could violate it: **MFE and MAE may never be a
feature, a filter, a conditioning variable or an entry rule.** Nothing in this
module returns a position, and nothing that consumes it may pass an excursion
into one. Their legitimate downstream use is to derive candidate take-profit and
stop distances for a *future* round's label design.

Window semantics are the engine's own
-------------------------------------

`engine.evaluate` holds `position.shift(1)` and earns `mid_c.shift(-1) - mid_c`,
so a decision at `t` is on risk from `t+1` and an `H`-bar hold exits at `t+H+1`.
The reference price is therefore `mid_c[t+1]` and the path is bars `t+2 … t+H+1`
— strictly after entry, `H` bars long. Getting this off by one is the same class
of defect as same-bar leakage, only harder to see, so it is pinned by a test.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.round_a import panels

#: Multiples of the round-trip cost the atlas asks about.
COST_MULTIPLES: Final[tuple[int, ...]] = (1, 2, 3)
QUANTILES: Final[tuple[float, ...]] = (0.10, 0.25, 0.50, 0.75, 0.90)

#: Fixed in the plan before any cell was computed.
RICH_MFE_OVER_COST: Final[float] = 3.0
RICH_P_TWO_COST: Final[float] = 0.50
MARGINAL_MFE_OVER_COST: Final[float] = 1.5


def excursions(frame: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Forward path statistics for a decision at each bar, in pips.

    Returns one row per bar with the reference price's own excursions. Rows whose
    window runs past the end of the panel are `NaN` and are dropped by the caller
    rather than filled — a truncated window would understate every excursion.
    """
    pip = frame["pip_size"].to_numpy()
    close = frame["mid_c"].to_numpy()
    high = frame["mid_h"].to_numpy()
    low = frame["mid_l"].to_numpy()
    n = len(frame)

    #: entry reference is the close of t+1
    reference = np.full(n, np.nan)
    reference[: n - 1] = close[1:]

    #: rolling max/min over bars t+2 … t+H+1, computed once by reversing the
    #: series so the forward window becomes a backward one
    forward_high = (
        pd.Series(high[::-1]).rolling(horizon, min_periods=horizon).max().to_numpy()[::-1]
    )
    forward_low = pd.Series(low[::-1]).rolling(horizon, min_periods=horizon).min().to_numpy()[::-1]

    path_high = np.full(n, np.nan)
    path_low = np.full(n, np.nan)
    terminal = np.full(n, np.nan)
    #: bar t's window starts at t+2, so index into the reversed rolling result at
    #: t+2 and require t+H+1 to exist
    last = n - horizon - 2
    if last >= 0:
        index = np.arange(0, last + 1)
        path_high[index] = forward_high[index + 2]
        path_low[index] = forward_low[index + 2]
        terminal[index] = close[index + horizon + 1]

    up = (path_high - reference) / pip
    down = (reference - path_low) / pip
    move = (terminal - reference) / pip

    return pd.DataFrame(
        {
            "ts": frame["ts"].to_numpy(),
            "day": frame["day"].to_numpy(),
            "atr_state": frame["atr_state"].to_numpy(),
            "session": frame["session"].to_numpy(),
            "rollover": frame["rollover"].to_numpy(),
            "cost": frame["roundtrip_cost"].to_numpy(),
            "up_excursion": up,
            "down_excursion": down,
            "mfe": np.maximum(up, down),
            "mae_at_mfe": np.where(up >= down, down, up),
            "terminal_move": move,
            "abs_move": np.abs(move),
            "realized_range": up + down,
        }
    ).dropna(subset=["mfe", "abs_move"])


def _cell_metrics(rows: pd.DataFrame) -> dict[str, Any]:
    if rows.empty:
        return {"observations": 0}
    cost = rows["cost"].to_numpy()
    mfe = rows["mfe"].to_numpy()
    abs_move = rows["abs_move"].to_numpy()
    median_cost = float(np.median(cost))
    out: dict[str, Any] = {
        "observations": int(len(rows)),
        "median_cost_pips": round(median_cost, 3),
        "mean_mfe": round(float(mfe.mean()), 2),
        "median_mfe": round(float(np.median(mfe)), 2),
        "median_mae_at_mfe": round(float(np.median(rows["mae_at_mfe"])), 2),
        "median_abs_move": round(float(np.median(abs_move)), 2),
        "mean_abs_move": round(float(abs_move.mean()), 2),
        "median_realized_range": round(float(np.median(rows["realized_range"])), 2),
        "median_mfe_over_cost": round(float(np.median(mfe / cost)), 3),
        "median_abs_move_over_cost": round(float(np.median(abs_move / cost)), 3),
    }
    for q in QUANTILES:
        tag = f"q{int(q * 100):02d}"
        out[f"mfe_{tag}"] = round(float(np.quantile(mfe, q)), 2)
        out[f"abs_move_{tag}"] = round(float(np.quantile(abs_move, q)), 2)
    for k in COST_MULTIPLES:
        out[f"p_mfe_gt_{k}x_cost"] = round(float((mfe > k * cost).mean()), 4)
        out[f"p_move_gt_{k}x_cost"] = round(float((abs_move > k * cost).mean()), 4)
    reachable = rows[rows["mfe"] > 2 * rows["cost"]]
    out["median_adverse_when_mfe_gt_2x"] = (
        round(float(np.median(reachable["mae_at_mfe"])), 2) if len(reachable) else None
    )
    return out


def atlas_for_panel(panel: dict[str, pd.DataFrame], panel_id: str) -> list[dict[str, Any]]:
    """Every pre-registered cell for one period. Nothing is selected."""
    rows: list[dict[str, Any]] = []
    for horizon in panels.ATLAS_HORIZONS:
        per_pair = {pair: excursions(frame, horizon) for pair, frame in panel.items()}
        for bloc, members in panels.BLOCS.items():
            stacked = pd.concat([per_pair[p] for p in members], ignore_index=True)
            #: effective observations: entries that do not share a window
            effective = int(len(stacked) / horizon)
            for atr_state in ("low", "mid", "high"):
                subset = stacked[stacked["atr_state"] == atr_state]
                rows.append(
                    {
                        "panel": panel_id,
                        "table": "atr",
                        "horizon": horizon,
                        "bloc": bloc,
                        "state": atr_state,
                        "effective_observations": int(len(subset) / horizon),
                        **_cell_metrics(subset),
                    }
                )
            for session in ("asia", "europe", "us"):
                subset = stacked[(stacked["session"] == session) & (~stacked["rollover"])]
                rows.append(
                    {
                        "panel": panel_id,
                        "table": "session",
                        "horizon": horizon,
                        "bloc": bloc,
                        "state": session,
                        "effective_observations": int(len(subset) / horizon),
                        **_cell_metrics(subset),
                    }
                )
            subset = stacked[stacked["rollover"]]
            rows.append(
                {
                    "panel": panel_id,
                    "table": "session",
                    "horizon": horizon,
                    "bloc": bloc,
                    "state": "rollover",
                    "effective_observations": int(len(subset) / horizon),
                    **_cell_metrics(subset),
                }
            )
            rows.append(
                {
                    "panel": panel_id,
                    "table": "overall",
                    "horizon": horizon,
                    "bloc": bloc,
                    "state": "all",
                    "effective_observations": effective,
                    **_cell_metrics(stacked),
                }
            )
    return rows


def classify(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply the plan's thresholds across the three periods jointly.

    A cell is opportunity-rich only if it clears in **every** period. One period's
    number never promotes a cell — that rule is the plan's, fixed before the
    numbers existed, and it is the one that stops a 2025-only artefact becoming a
    headline for the fifth time.
    """
    frame = pd.DataFrame(rows)
    out: list[dict[str, Any]] = []
    keys = ["table", "horizon", "bloc", "state"]
    for key, group in frame.groupby(keys, dropna=False):
        if len(group) != len(panels.LOADERS) or (group["observations"] == 0).any():
            verdict = "insufficient_data"
        else:
            ratio = group["median_mfe_over_cost"]
            reach = group["p_mfe_gt_2x_cost"]
            if (ratio >= RICH_MFE_OVER_COST).all() and (reach >= RICH_P_TWO_COST).all():
                verdict = "opportunity_rich"
            elif (ratio >= MARGINAL_MFE_OVER_COST).all():
                verdict = "marginal"
            else:
                verdict = "structurally_unattractive"
        record = dict(zip(keys, key, strict=True))
        record["verdict"] = verdict
        for _, row in group.iterrows():
            record[f"{row['panel']}__median_mfe_over_cost"] = row["median_mfe_over_cost"]
            record[f"{row['panel']}__p_mfe_gt_2x_cost"] = row["p_mfe_gt_2x_cost"]
            record[f"{row['panel']}__median_mfe"] = row["median_mfe"]
        out.append(record)
    return out


__all__ = [
    "COST_MULTIPLES",
    "MARGINAL_MFE_OVER_COST",
    "RICH_MFE_OVER_COST",
    "RICH_P_TWO_COST",
    "atlas_for_panel",
    "classify",
    "excursions",
]
