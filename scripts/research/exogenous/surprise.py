"""Stage C — does a real-time macro surprise carry direction?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The hypothesis is fixed in the plan before any return was computed:

> A **higher-than-expected** US CPI print is hawkish for the Fed and
> **appreciates the USD**.

So the position is long USD when the standardised surprise is positive and short
USD when it is negative, in every pair with a USD leg, at every horizon. The sign
is not read off the data. **A measured effect in the opposite direction drops the
family; it does not invert it** — the rule this programme adopted after a failed
reversal rule was nearly re-run as a momentum rule on the data that refuted it.

Execution is deliberately pessimistic
--------------------------------------

An event study that enters on the bar containing the release is measuring a
number nobody could have traded. Entry here is the **open of the first M15 bar
that starts strictly after** the release timestamp, so the bar spanning 08:30
America/New_York is skipped entirely. Cost is one round trip taken from **that
bar's own spread**, not from a period median, so the event-time widening is paid
rather than averaged away, and everything is reported again at twice the cost.

What this family can and cannot conclude
-----------------------------------------

It is USD-only with about 24 releases per deciding panel, so the plan's kill
rules — one currency, fewer than 30 events — drop it whatever it shows. It is
run because it answers a question the programme asked, and its **best attainable
outcome is a negative one**. The expectation is a model nowcast rather than a
survey consensus, so a null here does not refute a consensus-surprise hypothesis
either. Both limits are pre-registered, not discovered afterwards.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from scripts.research.exogenous import (
    MACRO_DIRECTION_SIGN,
    MACRO_HORIZON_BARS,
    NULL_DRAWS,
    SEED,
    TAIL_SHARE_CEILING,
)

#: The cost the whole programme uses: one spread plus half a pip, round trip.
HALF_SPREAD_ADDITION = 0.5


def usd_side(pair: str) -> int:
    """+1 if holding the pair is holding USD, −1 if it is selling USD.

    `USD_JPY` quotes JPY per USD, so long USD is long the pair. `EUR_USD` quotes
    USD per EUR, so long USD is **short** the pair. Getting this backwards would
    flip every result and still look like a clean directional effect, which is
    why it is one function with one test rather than an inline expression.
    """
    base, quote = pair.split("_")
    if base == "USD":
        return 1
    if quote == "USD":
        return -1
    raise ValueError(f"{pair} has no USD leg")


def usd_pairs(pairs: list[str]) -> list[str]:
    return sorted(pair for pair in pairs if "USD" in pair.split("_"))


def _entry_index(times: pd.Series, release: dt.datetime) -> int | None:
    """The first bar starting **strictly after** the release, or `None`.

    Strictly after, so the bar containing the print is never entered on. A bar
    more than two hours later means the market was closed at the release — a
    holiday or a gap — and the event is dropped rather than shifted onto a much
    later bar at a different information set.
    """
    stamp = pd.Timestamp(release)
    later = times.searchsorted(stamp, side="right")
    if later >= len(times):
        return None
    if times.iloc[later] - stamp > pd.Timedelta(hours=2):
        return None
    return int(later)


def event_returns(
    frames: dict[str, pd.DataFrame],
    releases: list[dict[str, Any]],
    *,
    horizon: str,
) -> list[dict[str, Any]]:
    """One row per (release × USD pair) at one horizon: gross, cost and net pips."""
    bars = MACRO_HORIZON_BARS[horizon]
    rows: list[dict[str, Any]] = []
    for pair in usd_pairs(list(frames)):
        frame = frames[pair]
        times = frame["ts"].reset_index(drop=True)
        close = frame["mid_c"].reset_index(drop=True)
        spread = frame["spread_close_pips"].reset_index(drop=True)
        open_ = frame["mid_o"].reset_index(drop=True)
        pip = float(frame["pip_size"].iloc[0])
        side = usd_side(pair)

        for release in releases:
            z = release.get("surprise_z")
            if z is None or not np.isfinite(z) or z == 0.0:
                continue
            stamp = dt.datetime.fromisoformat(release["release_timestamp_utc"])
            entry = _entry_index(times, stamp)
            if entry is None or entry + bars >= len(close):
                continue
            direction = int(np.sign(z)) * MACRO_DIRECTION_SIGN * side
            move = (float(close.iloc[entry + bars]) - float(open_.iloc[entry])) / pip
            cost = float(spread.iloc[entry]) + HALF_SPREAD_ADDITION
            rows.append(
                {
                    "pair": pair,
                    "release_date": release["release_date"],
                    "indicator": release["indicator"],
                    "horizon": horizon,
                    "surprise_z": float(z),
                    "direction": direction,
                    "signal": float(z) * MACRO_DIRECTION_SIGN * side,
                    "gross_pips": direction * move,
                    "cost_pips": cost,
                    "net_pips": direction * move - cost,
                    "entry_utc": times.iloc[entry].isoformat(),
                    "entry_spread_pips": float(spread.iloc[entry]),
                }
            )
    return rows


def _tail_share(values: list[float]) -> float | None:
    total = float(sum(values))
    if not total:
        return None
    top = sorted(values, reverse=True)[:10]
    return float(sum(top) / total)


def summarise(
    rows: list[dict[str, Any]], *, seed: int = SEED, draws: int = NULL_DRAWS
) -> dict[str, Any]:
    """Everything plan §20 asks for, plus a null that keeps the events fixed.

    The null permutes the **surprise values across releases** while leaving the
    event set, the pairs and the returns exactly as they are. That destroys the
    surprise-to-return relation and nothing else, so it is a null about the
    signal rather than about the calendar.
    """
    if not rows:
        return {"events": 0, "pair_events": 0}

    frame = pd.DataFrame(rows)
    gross = frame["gross_pips"].to_numpy(dtype=float)
    net = frame["net_pips"].to_numpy(dtype=float)
    releases = sorted(frame["release_date"].unique())

    per_pair = {
        pair: {
            "events": int(len(block)),
            "gross_mean": float(block["gross_pips"].mean()),
            "net_mean": float(block["net_pips"].mean()),
        }
        for pair, block in frame.groupby("pair")
    }
    positive = frame[frame["surprise_z"] > 0]
    negative = frame[frame["surprise_z"] < 0]

    signal = frame["signal"].to_numpy(dtype=float)
    #: The realised move in the pair's own direction, so the IC is between the
    #: signed surprise and the signed move rather than between a sign and itself.
    realised = frame["gross_pips"].to_numpy(dtype=float) * np.sign(signal)
    ic = float(scipy_stats.spearmanr(signal, realised).statistic) if len(signal) > 2 else None

    statistic = float(np.mean(gross) / (np.std(gross, ddof=1) / np.sqrt(len(gross))))
    rng = np.random.default_rng(seed)
    by_release = {value: index for index, value in enumerate(releases)}
    release_index = frame["release_date"].map(by_release).to_numpy()
    per_release_z = np.array(
        [
            float(frame.loc[frame["release_date"] == value, "surprise_z"].iloc[0])
            for value in releases
        ]
    )
    sides = np.array([usd_side(pair) for pair in frame["pair"]])
    move = frame["gross_pips"].to_numpy(dtype=float) / np.where(
        frame["direction"].to_numpy(dtype=float) == 0, 1.0, frame["direction"].to_numpy(dtype=float)
    )
    null_statistics: list[float] = []
    for _ in range(draws):
        shuffled = rng.permutation(per_release_z)
        drawn_direction = np.sign(shuffled[release_index]) * MACRO_DIRECTION_SIGN * sides
        drawn = drawn_direction * move
        null_statistics.append(
            float(np.mean(drawn) / (np.std(drawn, ddof=1) / np.sqrt(len(drawn))))
        )
    extreme = sum(1 for value in null_statistics if abs(value) >= abs(statistic))
    p_value = (extreme + 1) / (len(null_statistics) + 1)

    return {
        "events": len(releases),
        "pair_events": int(len(frame)),
        "pairs": len(per_pair),
        "gross_mean_pips": float(np.mean(gross)),
        "cost_mean_pips": float(frame["cost_pips"].mean()),
        "net_mean_pips": float(np.mean(net)),
        "net_mean_pips_double_cost": float(np.mean(gross - 2.0 * frame["cost_pips"].to_numpy())),
        "gross_t": statistic,
        "permutation_p": p_value,
        "directional_ic": ic,
        "hit_rate": float((gross > 0).mean()),
        "pairs_gross_positive": sum(1 for v in per_pair.values() if v["gross_mean"] > 0),
        "pairs_net_positive": sum(1 for v in per_pair.values() if v["net_mean"] > 0),
        "per_pair": per_pair,
        "tail_share_of_gross": _tail_share([float(v) for v in gross if v > 0]),
        "positive_surprise": {
            "events": int(positive["release_date"].nunique()),
            "gross_mean": float(positive["gross_pips"].mean()) if len(positive) else None,
        },
        "negative_surprise": {
            "events": int(negative["release_date"].nunique()),
            "gross_mean": float(negative["gross_pips"].mean()) if len(negative) else None,
        },
    }


def verdict(
    cells: dict[str, dict[str, dict[str, Any]]],
    deciding: tuple[str, ...],
    *,
    min_events: int,
) -> dict[str, Any]:
    """Plan §13, read mechanically. Every clause fails closed.

    `single_currency` is `True` by construction and is stated rather than
    computed, because the source covers one currency and no measurement can
    change that.
    """
    rows = [cells[panel] for panel in deciding if panel in cells]
    complete = len(rows) == len(deciding) and bool(rows)

    reasons: list[str] = ["SINGLE_CURRENCY_USD_ONLY"]
    if not complete:
        reasons.append("PANEL_MISSING")
    else:
        counts = [cell.get("events", 0) for panel in rows for cell in panel.values() if cell]
        if not counts or min(counts) < min_events:
            reasons.append(f"FEWER_THAN_{min_events}_EVENTS_PER_DECIDING_PANEL")

        for name in sorted({key for panel in rows for key in panel}):
            per_panel = [panel.get(name) for panel in rows]
            if any(cell is None or not cell for cell in per_panel):
                continue
            gross = [cell["gross_mean_pips"] for cell in per_panel]
            if len({np.sign(value) for value in gross}) > 1:
                reasons.append(f"PANEL_SIGN_REVERSAL_{name}")
            if all(value <= 0 for value in gross):
                reasons.append(f"NO_GROSS_EFFECT_{name}")
            nets = [cell["net_mean_pips"] for cell in per_panel]
            if all(value <= 0 for value in nets):
                reasons.append(f"NEGATIVE_AFTER_COST_{name}")
            tails = [cell.get("tail_share_of_gross") for cell in per_panel]
            if any(value is not None and value > TAIL_SHARE_CEILING for value in tails):
                reasons.append(f"TAIL_ABOVE_CEILING_{name}")

    survives = complete and reasons == ["SINGLE_CURRENCY_USD_ONLY"]
    return {
        "status": (
            "MACRO_SURPRISE_SIGNAL_PRESENT_BUT_SINGLE_CURRENCY_INSUFFICIENT_BREADTH"
            if survives
            else "MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED"
        ),
        "expectation_kind": "MODEL_NOWCAST_SURPRISE_NOT_SURVEY_SURPRISE",
        "drop_reasons": sorted(set(reasons)),
        "complete": complete,
        "note": (
            "The pre-registered sign is fixed. A measured effect in the opposite "
            "direction drops this family; it is never inverted."
        ),
    }


__all__ = [
    "HALF_SPREAD_ADDITION",
    "event_returns",
    "summarise",
    "usd_pairs",
    "usd_side",
    "verdict",
]
