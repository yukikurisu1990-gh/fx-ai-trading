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

#: **The comparison must be matched on day of week.** The M15 panels carry a
#: Sunday pseudo-session — the 21:00–24:00 UTC open — of 4 to 12 bars against
#: about 95 on a weekday, and on `EUR_USD` over 2021–23 its median spread is
#: 2.51 pips against 1.49 and its daily move 7.97 pips against 36–48. Policy
#: rates take effect on weekdays, so an unmatched comparison puts **17% Sunday**
#: in the control group and **0%** in the event group, and the "narrower spread
#: on event days" that produces is a composition artefact: excluding Sundays
#: turns the 2021–23 spread ratio from 0.921 to **1.041**, with 17 of 19 pairs
#: now *wider*. Two independent review roles found this and it is the reason
#: this module reports a matched comparison rather than a raw one.
MIN_BARS_FOR_A_TRADING_DAY: int = 48


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
    """Per trading day: what moved, how much it cost, and how busy it was.

    Days with fewer than `MIN_BARS_FOR_A_TRADING_DAY` bars are **dropped**. They
    are the Sunday open, not a trading day, and leaving them in the control
    group is what produced this round's one false headline.
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
        }
    )
    if "volume" in frame.columns:
        table["volume"] = grouped["volume"].sum(min_count=1)
    table["exceeds_cost"] = (table["abs_move"] > table["cost"]).astype(float)
    #: the quantity that decides whether a day was worth trading at all
    table["move_less_cost"] = table["abs_move"] - table["cost"]
    table["dayofweek"] = table.index.dayofweek
    return table[table["bars"] >= MIN_BARS_FOR_A_TRADING_DAY]


def _matched_ratio(table: pd.DataFrame, near: pd.Series, column: str) -> float | None:
    """Event ÷ other, computed **within** each day of week and then pooled.

    Dropping the Sunday session removes most of the contamination; matching on
    day of week removes the rest, because a Wednesday is not a Friday either.
    Weekdays with no event contribute nothing rather than biasing the ratio.
    """
    numerator, denominator = [], []
    for weekday, block in table.groupby("dayofweek"):
        inside = near.reindex(block.index).fillna(False)
        on, off = block.loc[inside, column].dropna(), block.loc[~inside, column].dropna()
        if on.empty or off.empty:
            continue
        del weekday
        numerator.append(float(on.mean()))
        denominator.append(float(off.mean()))
    if not numerator or not sum(denominator):
        return None
    return round(float(np.mean(numerator) / np.mean(denominator)), 4)


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
            "sunday_days_dropped": int((frame["ts"].dt.dayofweek == 6).any()),
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
                "matched_ratio": _matched_ratio(table, near, column),
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
                    #: computed here too, so the summary does not report a null
                    #: matched ratio and a zero agreeing-pair count for it
                    "matched_ratio": _matched_ratio(table, near, "volume"),
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
            "matched_ratio": pooled(column, "matched_ratio"),
            "pairs_matched_ratio_above_one": sum(
                1
                for r in rows
                if column in r
                and r[column].get("matched_ratio") is not None
                and r[column]["matched_ratio"] > 1.0
            ),
            "standardised_difference": pooled(column, "standardised_difference"),
            "pairs_ratio_above_one": agreeing(column),
        }
    summary["per_pair"] = rows
    return summary


def permutation_test(
    panel: dict[str, pd.DataFrame],
    rate_panel: pd.DataFrame,
    *,
    column: str = "move_less_cost",
    draws: int = 3000,
    seed: int = 20260907,
) -> dict[str, Any]:
    """A null for the event effect, which the first version of this had none of.

    Event days are re-drawn **within day of week**, so the null keeps the
    weekday composition that produced the artefact this module now controls for,
    and each pair's daily series is standardised before pooling so that twenty
    correlated pairs are not counted as twenty observations.
    """
    events = change_dates(rate_panel)
    frames = []
    for pair, frame in panel.items():
        base, quote = pair.split("_")
        table = _daily_market(frame)
        if table.empty or column not in table:
            continue
        relevant = pd.DatetimeIndex(sorted(set(events[base]) | set(events[quote])))
        near = pd.Series(False, index=table.index)
        for offset in range(-WINDOW_DAYS, WINDOW_DAYS + 1):
            near |= table.index.isin(relevant + pd.Timedelta(days=offset))
        values = table[column]
        if values.std() == 0 or near.sum() < 5:
            continue
        frames.append(
            pd.DataFrame(
                {
                    "z": (values - values.mean()) / values.std(),
                    "near": near.to_numpy(),
                    "dow": table["dayofweek"].to_numpy(),
                }
            )
        )
    if not frames:
        return {"decidable": False}

    pooled = pd.concat(frames).groupby(level=0).agg({"z": "mean", "near": "max", "dow": "first"})
    observed = float(
        pooled.loc[pooled["near"], "z"].mean() - pooled.loc[~pooled["near"], "z"].mean()
    )

    rng = np.random.default_rng(seed)
    drawn = []
    for _ in range(draws):
        shuffled = pooled["near"].to_numpy().copy()
        for weekday in pooled["dow"].unique():
            mask = (pooled["dow"] == weekday).to_numpy()
            shuffled[mask] = rng.permutation(shuffled[mask])
        drawn.append(float(pooled.loc[shuffled, "z"].mean() - pooled.loc[~shuffled, "z"].mean()))
    drawn = np.asarray(drawn)
    return {
        "column": column,
        "days": int(len(pooled)),
        "event_days": int(pooled["near"].sum()),
        "observed_standardised_difference": round(observed, 4),
        "null_mean": round(float(drawn.mean()), 5),
        "null_sd": round(float(drawn.std()), 5),
        "p_two_sided": round(float((np.abs(drawn) >= abs(observed)).mean()), 5),
        "draws": draws,
        "note": (
            "event days are re-drawn within day of week, so the null carries the "
            "same weekday composition; each pair is standardised before pooling "
            "so correlated pairs are not counted as independent observations"
        ),
    }


def verdict(
    per_panel: dict[str, Any],
    deciding: tuple[str, ...],
    permutations: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Does the event anchor pick out days that are *economically* different?

    Movement being larger on event days is not enough and never was — Stage 3
    showed the same thing about volume. The question is whether the movement
    **net of the cost of capturing it** is larger, whether it agrees across
    pairs and panels, and whether it survives a null.

    Every ratio read here is the **day-of-week matched** one. The unmatched
    version is reported beside it and is not read, because it is the one two
    review roles showed to be a composition artefact.
    """
    rows = {panel: per_panel.get(panel) for panel in deciding}
    if not all(rows.values()) or not all((r or {}).get("pairs") for r in rows.values()):
        return {"decidable": False}

    def matched(panel: str, column: str) -> float | None:
        return (rows[panel].get(column) or {}).get("matched_ratio")

    moves = [matched(p, "abs_move") for p in deciding]
    spreads = [matched(p, "spread") for p in deciding]
    net = [matched(p, "move_less_cost") for p in deciding]
    exceeds = [matched(p, "exceeds_cost") for p in deciding]
    breadth = [rows[p]["move_less_cost"]["pairs_matched_ratio_above_one"] for p in deciding]
    pairs = [rows[p]["pairs"] for p in deciding]

    bigger_moves = all(v is not None and v > 1.0 for v in moves)
    bigger_net = all(v is not None and v > 1.0 for v in net)
    broad = all(b >= 0.75 * n for b, n in zip(breadth, pairs, strict=True))
    #: the cost claim is its own clause now, and it is not assumed
    cheaper = all(v is not None and v < 1.0 for v in spreads)
    significant = (
        all((permutations or {}).get(p, {}).get("p_two_sided", 1.0) <= 0.05 for p in deciding)
        if permutations
        else None
    )

    supported = bool(bigger_net and broad and significant is not False)
    return {
        "decidable": True,
        "read": "day-of-week matched ratios",
        "abs_move_ratio_matched": moves,
        "spread_ratio_matched": spreads,
        "move_less_cost_ratio_matched": net,
        "exceeds_cost_ratio_matched": exceeds,
        "abs_move_ratio_unmatched": [
            (rows[p].get("abs_move") or {}).get("ratio") for p in deciding
        ],
        "spread_ratio_unmatched": [(rows[p].get("spread") or {}).get("ratio") for p in deciding],
        "pairs_with_net_above_one": breadth,
        "pairs": pairs,
        "moves_are_bigger": bigger_moves,
        "net_of_cost_is_bigger": bigger_net,
        "spread_is_narrower": cheaper,
        "broad_across_pairs": broad,
        "significant_against_the_null": significant,
        "permutation": {p: (permutations or {}).get(p) for p in deciding},
        "status": (
            "CALENDAR_EVENT_MOVEMENT_STRUCTURE_SUPPORTED"
            if supported
            else "CALENDAR_EVENT_OPPORTUNITY_STRUCTURE_NOT_SUPPORTED"
        ),
        "cost_advantage_status": (
            "EVENT_DAY_COST_ADVANTAGE_ESTABLISHED"
            if cheaper
            else "EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED"
        ),
    }


__all__ = [
    "MIN_BARS_FOR_A_TRADING_DAY",
    "WINDOW_DAYS",
    "change_dates",
    "event_population",
    "permutation_test",
    "verdict",
]
