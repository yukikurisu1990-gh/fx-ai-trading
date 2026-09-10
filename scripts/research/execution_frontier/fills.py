"""The conservative fill model, vectorised over a pair's bars.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

What a limit order can be *proved* to have done, from M15 bid/ask bars
-----------------------------------------------------------------------

Very little, which is the point. A bar gives four prices a side and no path. It
cannot say when inside the bar a level was reached, whether a queue stood at that
level, whether the quote was withdrawn before the order arrived, or whether the
fill would have been partial. Every one of those unknowns has a direction: each
of them, resolved optimistically, *lowers* the cost this model reports. So each
is resolved the other way.

1. **Penetration, not touch.** A limit at `L` fills only when the opposing side
   trades a whole pip through it. At a touch the order may sit behind a queue
   this data cannot see, so penetration stands in for the queue being consumed.
2. **No price improvement.** A fill is at `L` exactly, however far the bar ran
   past it.
3. **No favourable latency.** An order decided at a bar's close is live only from
   the next bar. One decided at a bar's open is live during that bar, which reads
   nothing from inside it.
4. **Ambiguity resolves against the order.** The touch case — `ask_low` equal to
   `L`, or short of the penetration — is scored as no fill, because the bar is
   consistent with both outcomes.
5. **No resting across a gap.** Every bar from the decision to the crossing bar
   must be fifteen minutes apart. An order does not sit through a weekend; such
   an observation is dropped as unmeasurable rather than scored as a miss, since
   scoring it either way would be a claim the data does not support.
6. **All or nothing.** No partial fill, so no proportional saving.

Why the cost metric is implementation shortfall
-----------------------------------------------

A passive order does not transact at the moment of the decision, and a metric
that priced only the spread would credit the saving while hiding the delay. So
every leg is scored against the mid at the moment the design says to trade::

    leg cost (bp) = direction * (fill price - decision mid) / decision mid * 1e4

which makes the spread and the drift one number and makes the three policies
comparable.

The selection this file exists to expose
----------------------------------------

`P1` — rest and cancel — fills **precisely when the market came to the order**.
Its conditional mean is therefore excellent and means almost nothing: it is an
average over the subset that moved in the order's favour. `P2` — rest, then
cross — has no such subset, because every decision ends in a trade. That is why
the pre-registration applies the bands to `P2` and reports `P1` only beside its
fill rate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.execution_frontier import (
    DRIFT_BARS,
    PENETRATION_PIPS,
    WAIT_BARS,
)
from scripts.research.fxunits import HALF_SPREAD_ADDITION_PIPS

BAR: Final[pd.Timedelta] = pd.Timedelta(minutes=15)

#: A market order pays half the round-trip pad on each leg, which keeps a round
#: trip equal to the `spread + 0.5 pip` convention every earlier stage used.
PAD_PIPS_PER_LEG: Final[float] = HALF_SPREAD_ADDITION_PIPS / 2.0

#: Where in a bar the design says to trade. `open` means the decision is taken as
#: the bar begins and the order is live during it; `close` means the decision
#: uses the bar's closing quote and the order is live only afterwards.
DECISION_POINTS: Final[tuple[str, ...]] = ("open", "close")

LONG: Final[int] = 1
SHORT: Final[int] = -1


@dataclass(frozen=True)
class FillRule:
    """The pre-registered fill rule. Frozen so a caller cannot tune it mid-run."""

    wait_bars: int = WAIT_BARS
    penetration_pips: float = PENETRATION_PIPS
    drift_bars: int = DRIFT_BARS

    def __post_init__(self) -> None:
        if self.wait_bars < 1:
            raise ValueError("a passive order must rest for at least one bar")
        if self.penetration_pips <= 0:
            raise ValueError(
                "penetration must be strictly positive; zero would be a touch-only "
                "fill, which the pre-registration forbids"
            )
        if self.drift_bars < 1:
            raise ValueError("the drift horizon must be at least one bar")

    @property
    def label(self) -> str:
        return f"w{self.wait_bars}_p{self.penetration_pips:g}"


@dataclass(frozen=True)
class DirectionCosts:
    """One direction's costs and fill facts, one entry per bar of the pair."""

    baseline_bp: np.ndarray
    passive_bp: np.ndarray
    conditional_bp: np.ndarray
    filled: np.ndarray
    fill_offset: np.ndarray
    drift_passive_bp: np.ndarray
    drift_baseline_bp: np.ndarray


@dataclass(frozen=True)
class LegCosts:
    """Both directions, plus the mask saying which bars could be measured at all."""

    measurable: np.ndarray
    long: DirectionCosts
    short: DirectionCosts

    def for_direction(self, direction: int) -> DirectionCosts:
        if direction == LONG:
            return self.long
        if direction == SHORT:
            return self.short
        raise ValueError(f"direction must be {LONG} or {SHORT}, not {direction!r}")


def _sliding(values: np.ndarray, window: int) -> np.ndarray:
    """Row `i` covers `values[i : i + window]`."""
    return np.lib.stride_tricks.sliding_window_view(values, window)


def _contiguity_prefix(ts: np.ndarray) -> np.ndarray:
    """`prefix[b] - prefix[a] == b - a` exactly when bars `a..b` are contiguous.

    A prefix sum rather than a rolling `all`, so a span of any length is one
    subtraction and the crossing bar and the drift horizon can use the same
    object as the resting window.
    """
    steps = (np.diff(ts) == np.timedelta64(BAR)).astype(np.int64)
    return np.concatenate(([0], np.cumsum(steps)))


def _finite_positive(*arrays: np.ndarray) -> np.ndarray:
    ok = np.ones(len(arrays[0]), dtype=bool)
    for array in arrays:
        ok &= np.isfinite(array) & (array > 0)
    return ok


def leg_costs(frame: pd.DataFrame, *, at: str, rule: FillRule | None = None) -> LegCosts:
    """Score every bar of a pair as a possible execution, under all three policies.

    Returns one entry per bar. A bar whose window runs off the end of the panel,
    or across a session gap, or over a non-finite quote, is `measurable = False`
    and carries `nan`; nothing downstream may read those without the mask.
    """
    if at not in DECISION_POINTS:
        raise ValueError(f"decision point must be one of {DECISION_POINTS}, not {at!r}")
    rule = rule or FillRule()
    suffix = "o" if at == "open" else "c"
    #: An order decided on a bar's close is live from the *next* bar; one decided
    #: on its open is live during that bar. This single integer is the whole of
    #: the no-favourable-latency rule.
    offset = 0 if at == "open" else 1

    n = len(frame)
    ts = frame["ts"].to_numpy(dtype="datetime64[ns]")
    pip = frame["pip_size"].to_numpy(dtype=float)
    mid = frame[f"mid_{suffix}"].to_numpy(dtype=float)
    bid = frame[f"bid_{suffix}"].to_numpy(dtype=float)
    ask = frame[f"ask_{suffix}"].to_numpy(dtype=float)
    ask_low = frame["ask_l"].to_numpy(dtype=float)
    bid_high = frame["bid_h"].to_numpy(dtype=float)
    mid_close = frame["mid_c"].to_numpy(dtype=float)

    wait, drift = rule.wait_bars, rule.drift_bars
    #: The last bar a decision at `k` can need for a cost is `k + wait`: the
    #: crossing bar, which for `at="close"` is also the resting window's last bar.
    #: The drift diagnostic reaches `drift - 1` bars past the latest fill.
    horizon = wait + drift - 2 + offset
    if n <= max(wait, horizon):
        empty = np.full(n, np.nan)
        false = np.zeros(n, dtype=bool)
        blank = DirectionCosts(
            empty.copy(), empty.copy(), empty.copy(), false.copy(), np.full(n, -1), empty, empty
        )
        return LegCosts(false, blank, blank)

    prefix = _contiguity_prefix(ts)
    index = np.arange(n)
    last_cost_bar = index + wait
    cost_reach = last_cost_bar < n
    safe_cost = np.where(cost_reach, last_cost_bar, n - 1)
    contiguous_cost = (prefix[safe_cost] - prefix[index]) == (safe_cost - index)

    measurable = (
        cost_reach
        & contiguous_cost
        & _finite_positive(mid, bid, ask, pip)
        & np.isfinite(ask_low)
        & np.isfinite(bid_high)
    )
    #: The crossing quote has to be finite too: it is the price the unfilled half
    #: of `P2` actually transacts at.
    cross_index = np.where(cost_reach, index + wait, n - 1)
    measurable &= np.isfinite(bid[cross_index]) & np.isfinite(ask[cross_index])

    last_drift_bar = index + horizon
    drift_reach = last_drift_bar < n
    safe_drift = np.where(drift_reach, last_drift_bar, n - 1)
    drift_ok = (
        measurable & drift_reach & ((prefix[safe_drift] - prefix[index]) == (safe_drift - index))
    )

    pad_price = PAD_PIPS_PER_LEG * pip
    penetration = rule.penetration_pips * pip

    def direction_costs(direction: int) -> DirectionCosts:
        if direction == LONG:
            limit = bid
            baseline_price = ask + pad_price
            cross_price = ask[cross_index] + pad_price[cross_index]
            extreme = _sliding(ask_low, wait)[offset:]
            hit = extreme <= (limit[: len(extreme)] - penetration[: len(extreme)])[:, None]
        else:
            limit = ask
            baseline_price = bid - pad_price
            cross_price = bid[cross_index] - pad_price[cross_index]
            extreme = _sliding(bid_high, wait)[offset:]
            hit = extreme >= (limit[: len(extreme)] + penetration[: len(extreme)])[:, None]

        filled = np.zeros(n, dtype=bool)
        fill_offset = np.full(n, -1, dtype=int)
        any_hit = hit.any(axis=1)
        filled[: len(any_hit)] = any_hit
        fill_offset[: len(any_hit)] = np.where(any_hit, hit.argmax(axis=1), -1)
        filled &= measurable
        fill_offset = np.where(filled, fill_offset, -1)

        def shortfall(price: np.ndarray) -> np.ndarray:
            return direction * (price - mid) / mid * 1e4

        baseline_bp = np.where(measurable, shortfall(baseline_price), np.nan)
        at_limit = shortfall(limit)
        crossed = shortfall(cross_price)
        passive_bp = np.where(measurable, np.where(filled, at_limit, crossed), np.nan)
        conditional_bp = np.where(filled, at_limit, np.nan)

        #: The bar the trade actually happened in — the fill bar for a passive
        #: fill, and the first live bar for a market order — so both drifts are
        #: measured over the same number of bars of exposure.
        exposure = index + offset + np.where(filled, fill_offset, 0)
        passive_at = np.clip(exposure + drift - 1, 0, n - 1)
        baseline_at = np.clip(index + offset + drift - 1, 0, n - 1)
        drift_passive = np.where(
            drift_ok & filled,
            direction * (mid_close[passive_at] - limit) / limit * 1e4,
            np.nan,
        )
        drift_baseline = np.where(
            drift_ok,
            direction * (mid_close[baseline_at] - baseline_price) / baseline_price * 1e4,
            np.nan,
        )
        return DirectionCosts(
            baseline_bp=baseline_bp,
            passive_bp=passive_bp,
            conditional_bp=conditional_bp,
            filled=filled,
            fill_offset=fill_offset,
            drift_passive_bp=drift_passive,
            drift_baseline_bp=drift_baseline,
        )

    with np.errstate(invalid="ignore", divide="ignore"):
        return LegCosts(measurable, direction_costs(LONG), direction_costs(SHORT))


def summarise(costs: LegCosts, selector: np.ndarray) -> dict[str, Any]:
    """The one-pair form of `summarise_many`."""
    return summarise_many([(costs, selector)])


def summarise_many(items: list[tuple[LegCosts, np.ndarray]]) -> dict[str, Any]:
    """Pool both directions, and every pair given, over the selected bars.

    Both directions are pooled because the direction a design will take is drawn
    from a generator, so the population being described is "a trade at these
    bars", not "a buy" or "a sell". Keeping them apart would report the drift of
    a market that happened to fall over the panel as an execution property.

    Pairs are pooled per observation rather than by averaging per-pair means, so
    a pair that is tradable on fewer bars carries proportionally less weight —
    which is what a book actually experiences. The per-pair breakdown is reported
    separately for the same reason it exists elsewhere in this programme: a
    pooled number that is really one pair is a composition artifact, and this
    corpus has produced two of them.
    """
    rows: dict[str, list[np.ndarray]] = {
        "baseline": [],
        "passive": [],
        "conditional": [],
        "filled": [],
        "offset": [],
        "drift_passive": [],
        "drift_baseline": [],
    }
    for costs, selector in items:
        for direction in (LONG, SHORT):
            side = costs.for_direction(direction)
            keep = selector & costs.measurable
            rows["baseline"].append(side.baseline_bp[keep])
            rows["passive"].append(side.passive_bp[keep])
            rows["conditional"].append(side.conditional_bp[keep])
            rows["filled"].append(side.filled[keep])
            rows["offset"].append(side.fill_offset[keep])
            rows["drift_passive"].append(side.drift_passive_bp[keep])
            rows["drift_baseline"].append(side.drift_baseline_bp[keep])
    if not rows["baseline"]:
        return {"n": 0}
    pooled = {key: np.concatenate(value) for key, value in rows.items()}

    n = int(len(pooled["baseline"]))
    if n == 0:
        return {"n": 0}
    baseline = pooled["baseline"]
    passive = pooled["passive"]
    filled = pooled["filled"].astype(bool)
    quoted_half = baseline  # the market-order leg cost *is* half spread plus pad
    capture = baseline - passive
    out: dict[str, Any] = {
        "n": n,
        "baseline_leg_bp": round(float(np.mean(baseline)), 4),
        "passive_leg_bp": round(float(np.mean(passive)), 4),
        "capture_bp": round(float(np.mean(capture)), 4),
        "capture_share_of_quoted": round(float(np.mean(capture) / np.mean(quoted_half)), 4)
        if np.mean(quoted_half) != 0
        else None,
        "fill_rate": round(float(filled.mean()), 4),
        "missed_rate": round(float(1.0 - filled.mean()), 4),
    }
    conditional = pooled["conditional"][filled]
    if conditional.size:
        out["conditional_leg_bp"] = round(float(np.mean(conditional)), 4)
        offsets = pooled["offset"][filled]
        out["fill_bars_median"] = float(np.median(offsets) + 1)

    def mean_of(values: np.ndarray) -> float | None:
        finite = values[np.isfinite(values)]
        return round(float(np.mean(finite)), 4) if finite.size else None

    #: Three drifts, because two of them answer different questions and mixing
    #: them was this file's first error. `drift_passive` is measured from the
    #: fill price and shows what the *position* then did. `drift_baseline` is
    #: measured from a market order over every decision. The third restricts the
    #: baseline to the decisions whose passive order filled, which holds the
    #: execution model fixed and varies only the population.
    out["drift_passive_bp"] = mean_of(pooled["drift_passive"])
    out["drift_baseline_bp"] = mean_of(pooled["drift_baseline"])
    out["drift_baseline_on_filled_bp"] = mean_of(np.where(filled, pooled["drift_baseline"], np.nan))
    if out["drift_baseline_bp"] is not None and out["drift_baseline_on_filled_bp"] is not None:
        #: Positive means the market behaved worse after the decisions a passive
        #: order actually filled on — the selection, isolated from the price
        #: advantage the fill itself carries. A model reporting only the price
        #: advantage would call a systematically bad entry a cheap one.
        out["adverse_selection_bp"] = round(
            float(out["drift_baseline_bp"] - out["drift_baseline_on_filled_bp"]), 4
        )
    return {key: value for key, value in out.items() if value is not None}


__all__ = [
    "BAR",
    "DECISION_POINTS",
    "LONG",
    "PAD_PIPS_PER_LEG",
    "SHORT",
    "DirectionCosts",
    "FillRule",
    "LegCosts",
    "leg_costs",
    "summarise",
    "summarise_many",
]
