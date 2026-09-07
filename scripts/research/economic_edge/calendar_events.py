"""Route C — do scheduled macro events define an exogenous opportunity population?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Plan §16's first question is deliberately **not** whether scheduled events
predict direction. It is whether they pick out periods by something other than
the price series itself — an *exogenous* anchor — because every opportunity
variable this programme has tried was a transform of the same prices, and Stage 3
has just shown the best of them cannot see the one target that pays.

The event source, and why it is this one
-----------------------------------------

**Policy-rate decisions** are one of the four event classes the plan names, and
the dates on which a G10 policy rate changed are already in the BIS series
acquired at Stage 1. No new acquisition, no new provenance risk, and the dates
are as exogenous to the FX price series as anything can be.

What this population is **not**, stated plainly:

* it contains only meetings that **changed** a rate. A scheduled meeting that
  held is invisible here, and those are the majority. So this is "rate change
  days", not "central bank meeting days", and the difference matters — a market
  that had priced the change would show less movement, and this sample is
  biased toward the surprises;
* it carries no CPI, employment or GDP releases. Those need a separate source
  with its own provenance, and the plan refers them rather than guessing;
* the BIS date is the date the rate became **effective**, which for most of
  these central banks is the announcement day or the day after.

Those limitations are why the result below is read as a bound on what an event
anchor could offer, not as a calendar study.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from scripts.research.economic_edge import CURRENCIES

#: days either side of the event that count as "around" it
WINDOW_DAYS: int = 1


def change_dates(rate_panel: pd.DataFrame) -> dict[str, list[pd.Timestamp]]:
    """The dates on which each currency's policy rate changed.

    The panel is already lagged by the plan's one trading day, so a date here is
    a date on which the *knowable* rate changed — which is what a position could
    have reacted to.
    """
    out: dict[str, list[pd.Timestamp]] = {}
    for currency in CURRENCIES:
        series = rate_panel[currency]
        moved = series.ne(series.shift(1)) & series.notna() & series.shift(1).notna()
        out[currency] = list(series.index[moved])
    return out


def _daily_market(frame: pd.DataFrame) -> pd.DataFrame:
    """Per trading day: what moved, how much it cost, and how busy it was."""
    day = frame["ts"].dt.floor("D")
    pip = float(frame["pip_size"].iloc[0])
    grouped = frame.groupby(day)
    table = pd.DataFrame(
        {
            "abs_move": grouped["mid_c"].apply(lambda s: abs(s.iloc[-1] - s.iloc[0])) / pip,
            "realised": grouped["mid_c"].apply(lambda s: float(s.diff().std() or 0.0)) / pip,
            "spread": grouped["spread_close_pips"].median(),
            "cost": grouped["roundtrip_cost"].median(),
        }
    )
    if "volume" in frame.columns:
        table["volume"] = grouped["volume"].sum(min_count=1)
    table["exceeds_cost"] = (table["abs_move"] > table["cost"]).astype(float)
    #: the quantity that decides whether a day was worth trading at all
    table["move_less_cost"] = table["abs_move"] - table["cost"]
    return table


def event_population(panel: dict[str, pd.DataFrame], rate_panel: pd.DataFrame) -> dict[str, Any]:
    """Around a rate change in either leg, against every other day.

    Pooled across pairs, and reported per pair count so a result carried by one
    pair is visible rather than averaged away.
    """
    events = change_dates(rate_panel)
    rows: list[dict[str, Any]] = []
    for pair, frame in panel.items():
        base, quote = pair.split("_")
        table = _daily_market(frame)
        if table.empty:
            continue
        relevant = pd.DatetimeIndex(sorted(set(events[base]) | set(events[quote])))
        near = pd.Series(False, index=table.index)
        for offset in range(-WINDOW_DAYS, WINDOW_DAYS + 1):
            shifted = relevant + pd.Timedelta(days=offset)
            near |= table.index.isin(shifted)
        if near.sum() < 10 or (~near).sum() < 50:
            continue

        row: dict[str, Any] = {
            "pair": pair,
            "event_days": int(near.sum()),
            "other_days": int((~near).sum()),
        }
        for column in ("abs_move", "realised", "spread", "cost", "exceeds_cost", "move_less_cost"):
            if column not in table:
                continue
            on = table.loc[near, column].dropna()
            off = table.loc[~near, column].dropna()
            if on.empty or off.empty:
                continue
            pooled_sd = float(np.sqrt((on.var() + off.var()) / 2.0))
            row[column] = {
                "event": round(float(on.mean()), 4),
                "other": round(float(off.mean()), 4),
                "ratio": round(float(on.mean() / off.mean()), 4) if off.mean() else None,
                "standardised_difference": round(float((on.mean() - off.mean()) / pooled_sd), 4)
                if pooled_sd > 0
                else None,
            }
        if "volume" in table:
            on, off = table.loc[near, "volume"].dropna(), table.loc[~near, "volume"].dropna()
            if not on.empty and not off.empty:
                row["volume"] = {
                    "event": round(float(on.mean()), 1),
                    "other": round(float(off.mean()), 1),
                    "ratio": round(float(on.mean() / off.mean()), 4),
                }
        rows.append(row)

    if not rows:
        return {"decidable": False}

    def pooled(column: str, key: str) -> float | None:
        values = [r[column][key] for r in rows if column in r and r[column].get(key) is not None]
        return round(float(np.mean(values)), 4) if values else None

    def agreeing(column: str) -> int:
        return sum(
            1
            for r in rows
            if column in r and r[column].get("ratio") is not None and r[column]["ratio"] > 1.0
        )

    summary = {
        "pairs": len(rows),
        "event_days_mean": round(float(np.mean([r["event_days"] for r in rows])), 1),
        "other_days_mean": round(float(np.mean([r["other_days"] for r in rows])), 1),
    }
    for column in (
        "abs_move",
        "realised",
        "spread",
        "cost",
        "exceeds_cost",
        "move_less_cost",
        "volume",
    ):
        if not any(column in r for r in rows):
            continue
        summary[column] = {
            "event": pooled(column, "event"),
            "other": pooled(column, "other"),
            "ratio": pooled(column, "ratio"),
            "standardised_difference": pooled(column, "standardised_difference"),
            "pairs_ratio_above_one": agreeing(column),
        }
    summary["per_pair"] = rows
    return summary


def verdict(per_panel: dict[str, Any], deciding: tuple[str, ...]) -> dict[str, Any]:
    """Does the event anchor pick out days that are *economically* different?

    Movement being larger on event days is not enough and never was — Stage 3
    showed the same thing about volume. The question is whether the movement
    **net of the cost of capturing it** is larger, and whether it agrees across
    pairs and panels.
    """
    rows = {panel: per_panel.get(panel) for panel in deciding}
    if not all(rows.values()) or not all(r.get("pairs") for r in rows.values()):
        return {"decidable": False}

    moves = [rows[p]["abs_move"]["ratio"] for p in deciding]
    spreads = [rows[p]["spread"]["ratio"] for p in deciding]
    net = [rows[p]["move_less_cost"]["ratio"] for p in deciding]
    exceeds = [rows[p]["exceeds_cost"]["ratio"] for p in deciding]
    breadth = [rows[p]["move_less_cost"]["pairs_ratio_above_one"] for p in deciding]
    pairs = [rows[p]["pairs"] for p in deciding]

    bigger_moves = all(v is not None and v > 1.0 for v in moves)
    bigger_net = all(v is not None and v > 1.0 for v in net)
    broad = all(b >= 0.75 * n for b, n in zip(breadth, pairs, strict=True))

    return {
        "decidable": True,
        "abs_move_ratio": moves,
        "spread_ratio": spreads,
        "move_less_cost_ratio": net,
        "exceeds_cost_ratio": exceeds,
        "pairs_with_net_above_one": breadth,
        "pairs": pairs,
        "moves_are_bigger": bigger_moves,
        "net_of_cost_is_bigger": bigger_net,
        "broad_across_pairs": broad,
        "status": (
            "CALENDAR_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED"
            if bigger_net and broad
            else "CALENDAR_EVENT_OPPORTUNITY_STRUCTURE_NOT_SUPPORTED"
        ),
    }


__all__ = ["WINDOW_DAYS", "change_dates", "event_population", "verdict"]
