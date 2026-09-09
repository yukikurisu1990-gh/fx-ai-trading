"""The feasibility frontier, in one unit, and the audit that proves it is one unit.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

This module answers two questions before any hypothesis is tested.

**What can these panels decide at all?** For a design — a horizon, a window, a
portfolio construction — it reports the smallest effect the design could detect
at 80% power, and the round trip that design would pay. A design whose MDE sits
above twice its cost cannot produce evidence, and saying so in advance is cheaper
than saying it afterwards. Because that gate has a perverse property — it gets
easier as a design gets more expensive — every cell also carries the gross
information ratio that break-even alone would demand, which the gate cannot see.

**Is every number in one unit?** The frontier that motivated this phase was not.
Calendar rows were basis points across the median of twenty pairs; event rows
were **pips** on `EUR_USD` alone, with a pips hurdle beside them. For `EUR_USD` a
pip is 0.93 bp, so the two columns looked comparable and were not; for `USD_JPY`
a pip is 0.67 bp and they are not even close. Everything here goes through
`fxunits`, and `verify_unit_consistency` walks the finished record looking for a
number that did not.

Nothing here uses a signal. Portfolio directions are drawn from a generator, so
no signal-to-return relation exists to be found; what is measured is a property
of the design.

Five defects an independent audit found in the first version
------------------------------------------------------------

All are fixed here and pinned by a test, and each of them made a design look
*better* than it is.

**A window did not have to be near its moment.** The only filter was that the
four bars were contiguous. On the 102 Sundays in each panel no pair has a bar
before about 21:00 UTC, so a "pre-fix" window silently became Friday's last hour
and a "post-fix" window the weekly open — 16.5% of every clock cell, and the
reason `n_events` equalled `n_days` exactly. `spread_by_moment` thirty lines away
already applied the right test, so the two halves of the artifact disagreed about
which days existed.

**A window could open at the weekly reopen.** The widest spreads of the week sit
in the first bars after the weekend gap. Those entries carried a mean cost near
three times the rest and lifted the hurdle by a quarter.

**The hurdle was a mean over that inflated tail.** Since `decidable` compares the
MDE against twice the cost, a fatter cost tail *bought* decidability. The gate
now uses the median round trip, which a tail cannot move; the mean is reported
separately as the expectancy cost, which is what a strategy actually pays.

**A "1d" horizon was two overlapping days.** The exit was taken at the end of
`days[start + step]`, so every horizon ran one day long, and at `step = 1`
consecutive events shared a whole day.

**The MDE was one draw, and an average over directions.** One random direction
per event makes the gross series independent by construction, which randomises
away the serial dependence a real rule would carry; the resulting number matched
the i.i.d. standard error the docstring claimed to be avoiding. Directions are
now drawn both ways — independently per event, and held fixed across a whole
panel — and the gate uses the conservative branch with a lag-one adjustment to
the effective sample size.
"""

from __future__ import annotations

import datetime as dt
import itertools
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.clock_flow import (
    CURRENCIES,
    SEED,
    WINDOW_BARS,
    clock,
    currency,
)
from scripts.research.exploratory_m15 import PAIRS
from scripts.research.fxunits import (
    COST_MULTIPLE_FOR_HURDLE,
    HALF_SPREAD_ADDITION_PIPS,
    POWER_MULTIPLIER,
    UNIT,
    pips_to_bp,
    verify_unit_consistency,
)

#: Calendar horizons in trading days. Non-overlapping, and exactly as long as
#: their label: a first version held `step + 1` days and sampled every `step`, so
#: "1d" was a two-day window overlapping its neighbour by half.
CALENDAR_HORIZONS: Final[tuple[tuple[str, int], ...]] = (
    ("1d", 1),
    ("1w", 5),
    ("2w", 10),
    ("1m", 21),
)

#: Below this many bars a UTC date is not a trading day. Sundays carry about
#: twelve — the hours between the weekly reopen and midnight — and counting them
#: as days made `events_per_year` return exactly 252 by arithmetic rather than by
#: measurement. Same threshold as `economic_edge.calendar_events`.
MIN_BARS_FOR_A_TRADING_DAY: Final[int] = 48

#: Below this many pairs an event is dropped rather than measured on a thin
#: cross-section, which would make the currency indices incomparable across days.
MIN_PAIRS_PER_EVENT: Final[int] = 15

#: How many random signal realisations the design statistics are averaged over. A
#: first version drew one and reported its dispersion; at the 25 events of a
#: month-end cell the same cell then read 21.5 bp and 14.2 bp on two runs that
#: differed only in how far the generator had been advanced.
SIGNAL_DRAWS: Final[int] = 200

#: The largest gross information ratio worth assuming in advance. Used only to
#: locate the feasible band's ceiling, and reported at three values so a reader
#: can see how much it decides rather than inheriting one. It is a judgement, not
#: a measurement: nothing this programme has produced has had a gross IR near 1.5.
ILLUSTRATIVE_GROSS_IR: Final[tuple[float, ...]] = (1.0, 1.5, 2.0)

DAYS_PER_YEAR: Final[float] = 365.25

#: `w = SIGNAL_TO_PAIR @ s` — the identity `currency.pair_weights` computes, in
#: matrix form so a whole panel of draws is one product. Built from
#: `currency.COUNTERPARTIES` rather than restated, and held to the function by
#: `test_the_matrix_map_matches_pair_weights`.
SIGNAL_TO_PAIR: Final[np.ndarray] = np.array(
    [
        [
            (1.0 / currency.COUNTERPARTIES[c] if pair.split("_")[0] == c else 0.0)
            - (1.0 / currency.COUNTERPARTIES[c] if pair.split("_")[1] == c else 0.0)
            for c in CURRENCIES
        ]
        for pair in PAIRS
    ]
)

BAR: Final[pd.Timedelta] = pd.Timedelta(minutes=15)


def _utc_datetime64(series: pd.Series, label: str) -> np.ndarray:
    """Drop the tzinfo, having first **proved** the series is UTC.

    `searchsorted` over a tz-aware column falls back to an object array and
    compares `Timestamp` objects one at a time, which is both slow and — when the
    needle is naive — an error. Stripping the zone is the fix, and stripping it
    without checking is how a host-timezone reinterpretation entered this
    programme once before. `tzinfo is not None` is not the check: a zone can be
    present and not be UTC. The offset is.

    Fail-closed rather than exact: `Africa/Abidjan` is genuinely UTC+0 and is
    refused, because a zone carrying a transition table returns `None` from
    `utcoffset(None)`. Refusing a correct panel is recoverable; accepting a
    shifted one is not.
    """
    offset = series.dt.tz.utcoffset(None) if series.dt.tz is not None else None
    if offset is None or offset != dt.timedelta(0):
        raise ValueError(f"{label}: bar timestamps are not proven UTC ({series.dt.tz!r})")
    return series.dt.tz_convert("UTC").dt.tz_localize(None).to_numpy(dtype="datetime64[ns]")


def _naive_utc(moment: dt.datetime) -> np.datetime64:
    """The same conversion for a single moment, so needle and haystack match.

    Accepts a moment that is already naive-UTC and returns it unchanged, so a
    caller may normalise once and pass the result back through the lookups
    without the conversion happening twice or raising.
    """
    stamp = pd.Timestamp(moment)
    if stamp.tzinfo is not None:
        stamp = stamp.tz_convert("UTC").tz_localize(None)
    return np.datetime64(stamp)


class PanelArrays:
    """Per-pair numpy views of a panel, keyed for timestamp lookup.

    Held as arrays rather than frames because every cell indexes the same bars
    thousands of times and the frame overhead dominated a first version.
    """

    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self.ts: dict[str, np.ndarray] = {}
        self.open_: dict[str, np.ndarray] = {}
        self.close: dict[str, np.ndarray] = {}
        self.spread: dict[str, np.ndarray] = {}
        self.pip: dict[str, np.ndarray] = {}
        for pair, frame in frames.items():
            self.ts[pair] = _utc_datetime64(frame["ts"], pair)
            self.open_[pair] = frame["mid_o"].to_numpy(dtype=float)
            self.close[pair] = frame["mid_c"].to_numpy(dtype=float)
            self.spread[pair] = frame["spread_close_pips"].to_numpy(dtype=float)
            self.pip[pair] = frame["pip_size"].to_numpy(dtype=float)

        counts: dict[dt.date, int] = {}
        for stamp in frames[next(iter(frames))]["ts"]:
            day = pd.Timestamp(stamp).date()
            counts[day] = counts.get(day, 0) + 1
        self.all_days: list[dt.date] = sorted(counts)
        #: Sundays carry a partial session and are not trading days. Keeping them
        #: made every clock cell 16.5% Friday-and-weekly-open, and made
        #: `events_per_year` echo back the constant it was divided by.
        self.days: list[dt.date] = [
            day for day in self.all_days if counts[day] >= MIN_BARS_FOR_A_TRADING_DAY
        ]
        self.partial_days: int = len(self.all_days) - len(self.days)
        self.years: float = (self.all_days[-1] - self.all_days[0]).days / DAYS_PER_YEAR

    def bar_at_or_after(self, pair: str, moment: pd.Timestamp) -> int | None:
        position = int(np.searchsorted(self.ts[pair], _naive_utc(moment), side="left"))
        return position if position < len(self.ts[pair]) else None

    def last_bar_ending_by(self, pair: str, moment: pd.Timestamp) -> int | None:
        """Index of the last bar whose close lands at or before the moment.

        A bar stamped `t` covers `[t, t+15m)`, so its close is at `t+15m`. A bar
        that *contains* a moment falling strictly inside it belongs to neither
        window, which is how the fix window itself is kept out of both.
        """
        cutoff = _naive_utc(moment - BAR)
        position = int(np.searchsorted(self.ts[pair], cutoff, side="right")) - 1
        return position if position >= 0 else None

    def contiguous(self, pair: str, first: int, last: int) -> bool:
        """Every bar from `first` to `last` fifteen minutes apart, `first` included.

        Callers pass `entry - 1`, so a window opening on the first bar after the
        weekend gap is refused: the market has to have been trading already for
        the spread at entry to be one a trade would actually meet.
        """
        ts = self.ts[pair]
        if first < 0 or last >= len(ts) or last < first:
            return False
        return bool(np.all(np.diff(ts[first : last + 1]) == np.timedelta64(BAR)))

    def window(self, pair: str, entry: int, exit_: int) -> tuple[float, float] | None:
        """`(return_bp, roundtrip_cost_bp)`, or `None` if the bars are unusable.

        Cost is split across the two bars actually transacted on — half the round
        trip at the entry bar's spread and mid, half at the exit bar's — because a
        window ending inside a liquidity hole pays for that hole. The exit spread
        is not a signal: it enters only as a subtraction, and the direction was
        chosen at entry.
        """
        ts = self.ts[pair]
        if entry < 0 or exit_ >= len(ts) or exit_ < entry:
            return None
        entry_open = self.open_[pair][entry]
        exit_close = self.close[pair][exit_]
        if not (np.isfinite(entry_open) and np.isfinite(exit_close)) or entry_open <= 0:
            return None
        ret_bp = float((exit_close - entry_open) / entry_open * 1e4)
        half_in = (
            float(
                pips_to_bp(
                    self.spread[pair][entry] + HALF_SPREAD_ADDITION_PIPS,
                    self.pip[pair][entry],
                    entry_open,
                )
            )
            / 2.0
        )
        half_out = (
            float(
                pips_to_bp(
                    self.spread[pair][exit_] + HALF_SPREAD_ADDITION_PIPS,
                    self.pip[pair][exit_],
                    exit_close,
                )
            )
            / 2.0
        )
        return ret_bp, half_in + half_out


def economics(
    dispersion_bp: float,
    median_cost_bp: float,
    mean_cost_bp: float,
    n_events: int,
    years: float,
) -> dict[str, Any]:
    """What break-even alone demands of a design, and where it is feasible.

    The power gate has a property nobody had noticed: `MDE <= 2 * cost` gets
    **easier** as a design gets more expensive, because the bar it must clear is
    set by its own cost. All ten clock windows pass it, and each needs a gross
    information ratio between six and fifty-odd merely to break even. So the gate
    is reported beside a second, unit-free number it cannot see::

        break-even gross IR = (mean cost / dispersion) * sqrt(events per year)

    computed from the **mean** cost, because break-even is an expectancy and a
    strategy pays the mean.

    An **event** design decouples the two terms: the window length fixes the
    dispersion, and selectivity fixes the frequency. That leaves a band of
    frequencies at once powered and payable, bounded below by the panel's ability
    to see the effect and above by the largest gross IR worth assuming. The band
    is quadratic in `1/cost`, which is why halving execution cost widens it
    fourfold and no improvement in a signal can do the same.
    """
    if min(dispersion_bp, median_cost_bp, mean_cost_bp, years) <= 0 or n_events <= 0:
        return {}
    per_year = n_events / years
    #: The floor uses the gate's cost (median) and the ceiling the expectancy's
    #: (mean), because each answers its own question.
    powered_ratio = dispersion_bp / median_cost_bp
    payable_ratio = dispersion_bp / mean_cost_bp
    return {
        "events_per_year": round(per_year, 1),
        "break_even_gross_ir": round(float(mean_cost_bp / dispersion_bp * np.sqrt(per_year)), 2),
        "dispersion_over_median_cost": round(float(powered_ratio), 3),
        "feasible_events_per_year_floor": round(
            float((POWER_MULTIPLIER / COST_MULTIPLE_FOR_HURDLE * powered_ratio) ** 2 / years), 2
        ),
        #: Keyed by the assumed gross IR, so every value is an events-per-year
        #: count and the subtree may declare itself as one.
        "feasible_events_per_year_ceiling": {
            "_unit": "count",
            **{str(ir): round(float((ir * payable_ratio) ** 2), 2) for ir in ILLUSTRATIVE_GROSS_IR},
        },
    }


def mde_from_gross(gross: np.ndarray, *, adjust_for_autocorrelation: bool) -> float:
    """Minimum detectable effect at 80% power from a series of per-event grosses.

    Under sign flips drawn per event the null mean has standard deviation
    `sqrt(sum g_i^2)/n` in closed form; simulating it would add noise to a number
    that has none, and the tests carry the Monte Carlo cross-check instead.

    When the direction is held fixed the grosses inherit whatever serial
    dependence the returns carry — the calendar windows abut, and a real rule is
    persistent — so the effective sample size is deflated by the lag-one
    autocorrelation. Positive dependence only ever raises the MDE here; negative
    dependence is clipped to zero rather than used to lower it.
    """
    n = len(gross)
    if n < 2:
        return float("inf")
    base = float(POWER_MULTIPLIER * np.sqrt(np.square(gross).sum()) / n)
    if not adjust_for_autocorrelation:
        return base
    centred = gross - gross.mean()
    denominator = float(np.square(centred).sum())
    if denominator <= 0:
        return base
    rho = float((centred[:-1] * centred[1:]).sum() / denominator)
    rho = min(max(rho, 0.0), 0.95)
    return base * float(np.sqrt((1.0 + rho) / (1.0 - rho)))


def _design_statistics(
    events: list[dict[str, Any]], rng: np.random.Generator, years: float
) -> dict[str, Any]:
    """MDE, cost and break-even economics for a design, from random directions.

    Directions are drawn as ±1 per currency and neutralised, because that is the
    shape a hypothesis produces; a Gaussian draw spreads exposure differently
    across eight correlated currencies and gives a different dispersion for the
    same design.

    Two direction regimes are reported, not one. `independent` redraws per event,
    which makes the gross series independent by construction and is the
    optimistic bound. `persistent` holds one direction across the whole panel, so
    abutting windows and a persistent rule show up as serial dependence. The gate
    uses the conservative branch — the 90th percentile of the persistent MDE over
    draws — because a single averaged number hid a range of three to nine on the
    calendar cell.
    """
    if not events:
        return {"n_events": 0, "decidable": False}

    returns = np.stack([event["returns"] for event in events])
    costs = np.stack([event["costs"] for event in events])
    mask = np.stack([event["present"] for event in events]).astype(float)
    n = len(events)

    def draw(persistent: bool) -> np.ndarray:
        raw = (
            np.repeat(rng.choice((-1.0, 1.0), size=(1, len(CURRENCIES))), n, axis=0)
            if persistent
            else rng.choice((-1.0, 1.0), size=(n, len(CURRENCIES)))
        )
        centred = raw - raw.mean(axis=1, keepdims=True)
        gross_exposure = np.abs(centred).sum(axis=1, keepdims=True)
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(gross_exposure > 0, 2.0 * centred / gross_exposure, 0.0)

    optimistic: list[float] = []
    conservative: list[float] = []
    dispersions: list[float] = []
    mean_costs: list[float] = []
    median_costs: list[float] = []
    for _ in range(SIGNAL_DRAWS):
        for persistent in (False, True):
            signal = draw(persistent)
            weights = (signal @ SIGNAL_TO_PAIR.T) * mask
            gross = (weights * returns).sum(axis=1)
            sink = conservative if persistent else optimistic
            sink.append(mde_from_gross(gross, adjust_for_autocorrelation=persistent))
            if not persistent:
                cost = (np.abs(weights) * costs).sum(axis=1)
                dispersions.append(float(np.std(gross, ddof=1)))
                mean_costs.append(float(cost.mean()))
                median_costs.append(float(np.median(cost)))

    mde = float(np.percentile(conservative, 90))
    mean_cost = float(np.mean(mean_costs))
    median_cost = float(np.mean(median_costs))
    dispersion = float(np.mean(dispersions))
    #: The gate uses the median round trip. A fatter cost tail must not be able
    #: to buy decidability, which a mean-based hurdle let it do.
    hurdle = COST_MULTIPLE_FOR_HURDLE * median_cost
    return {
        "n_events": n,
        "dispersion_bp": round(dispersion, 2),
        "mde_bp": round(mde, 3),
        "mde_optimistic_bp": round(float(np.median(optimistic)), 3),
        "mde_persistent_median_bp": round(float(np.median(conservative)), 3),
        "median_roundtrip_cost_bp": round(median_cost, 3),
        "mean_roundtrip_cost_bp": round(mean_cost, 3),
        "hurdle_bp": round(hurdle, 3),
        "headroom_bp": round(hurdle - mde, 3),
        "decidable": bool(mde <= hurdle),
        "economics": economics(dispersion, median_cost, mean_cost, n, years),
    }


def _event(arrays: PanelArrays, spans: dict[str, tuple[int, int]]) -> dict[str, Any] | None:
    """One event's pair returns and costs, aligned to the fixed `PAIRS` order.

    A pair the window could not be measured on is marked absent rather than set
    to zero, and `present` carries that, so a gap never reads as "the pair did
    not move" or "the pair was free to trade".
    """
    returns = np.zeros(len(PAIRS))
    costs = np.zeros(len(PAIRS))
    present = np.zeros(len(PAIRS), dtype=bool)
    for index, pair in enumerate(PAIRS):
        span = spans.get(pair)
        if span is None:
            continue
        measured = arrays.window(pair, *span)
        if measured is None:
            continue
        returns[index], costs[index] = measured
        present[index] = True
    if int(present.sum()) < MIN_PAIRS_PER_EVENT:
        return None
    return {"returns": returns, "costs": costs, "present": present}


def calendar_designs(arrays: PanelArrays) -> dict[str, Any]:
    """What a continuous calendar-time strategy could decide on this panel.

    Non-overlapping, and each horizon exactly as long as its name: entry at the
    open of `days[start]`, exit at the close of `days[start + step - 1]`.
    """
    rng = np.random.default_rng(SEED)
    out: dict[str, Any] = {}
    reference = PAIRS[0]
    for label, step in CALENDAR_HORIZONS:
        events: list[dict[str, Any]] = []
        held: list[float] = []
        for start in range(0, len(arrays.days) - step + 1, step):
            first, last = arrays.days[start], arrays.days[start + step - 1]
            spans: dict[str, tuple[int, int]] = {}
            for pair in PAIRS:
                entry = arrays.bar_at_or_after(pair, pd.Timestamp(first, tz="UTC"))
                exit_ = arrays.last_bar_ending_by(
                    pair, pd.Timestamp(last, tz="UTC") + pd.Timedelta(days=1)
                )
                if entry is None or exit_ is None or exit_ < entry:
                    continue
                #: The entry bar must not be the weekly reopen: the widest spreads
                #: of the week sit in the first bars after the gap, and letting
                #: them in lifted the hurdle by a quarter on the daily cell.
                if not arrays.contiguous(pair, entry - 1, entry):
                    continue
                spans[pair] = (entry, exit_)
            event = _event(arrays, spans)
            if event is not None and reference in spans:
                events.append(event)
                held.append(
                    (
                        pd.Timestamp(arrays.ts[reference][spans[reference][1]])
                        - pd.Timestamp(arrays.ts[reference][spans[reference][0]])
                    ).total_seconds()
                    / 3600.0
                )
        record = _design_statistics(events, rng, arrays.years)
        #: Reported because the label was once a lie: a "1d" cell held two days
        #: and overlapped its neighbour, and nothing in the artifact said so.
        record["hold_hours_median"] = round(float(np.median(held)), 2) if held else None
        out[label] = record
    return out


def clock_designs(arrays: PanelArrays) -> dict[str, Any]:
    """What a one-hour window at each institutional moment could decide.

    Each window is measured over every trading day, and then over the two
    selective subsets whose frequency might land inside the feasible band. The
    subsets are not a hypothesis: only a dispersion and a cost are read from
    them, never a mean, so no direction here could have been chosen after seeing
    one.
    """
    rng = np.random.default_rng(SEED + 1)
    subsets: dict[str, list[dt.date]] = {
        "all_days": list(arrays.days),
        "month_end": sorted(clock.month_end_days(arrays.days)),
        "quarter_end": sorted(clock.quarter_end_days(arrays.days)),
    }
    out: dict[str, Any] = {}
    for moment_name, side, (subset_name, subset_days) in itertools.product(
        clock.MOMENTS, ("pre", "post"), subsets.items()
    ):
        events: list[dict[str, Any]] = []
        dropped_far = 0
        for day in subset_days:
            #: Naive, because `arrays.ts` is naive UTC and the two are subtracted
            #: below. A test caught this as a `TypeError`; had the two sides been
            #: silently comparable it would have been a shifted window instead.
            moment = pd.Timestamp(_naive_utc(pd.Timestamp(clock.moment_utc(day, moment_name))))
            spans: dict[str, tuple[int, int]] = {}
            for pair in PAIRS:
                if side == "pre":
                    found = arrays.last_bar_ending_by(pair, moment)
                    if found is None:
                        continue
                    entry, exit_ = found - (WINDOW_BARS - 1), found
                    #: The window must actually reach the moment. Without this,
                    #: the contiguity check alone let a Sunday "pre-fix" window
                    #: be Friday's last hour, forty-three hours early.
                    gap = moment - (pd.Timestamp(arrays.ts[pair][exit_]) + BAR)
                else:
                    found = arrays.bar_at_or_after(pair, moment)
                    if found is None or found + (WINDOW_BARS - 1) >= len(arrays.ts[pair]):
                        continue
                    entry, exit_ = found, found + (WINDOW_BARS - 1)
                    gap = pd.Timestamp(arrays.ts[pair][entry]) - moment
                if not pd.Timedelta(0) <= gap < BAR:
                    dropped_far += 1
                    continue
                if not arrays.contiguous(pair, entry - 1, exit_):
                    continue
                spans[pair] = (entry, exit_)
            event = _event(arrays, spans)
            if event is not None:
                events.append(event)
        key = f"{moment_name}_{side}"
        if subset_name != "all_days":
            key = f"{key}__{subset_name}"
        record = _design_statistics(events, rng, arrays.years)
        record["pair_windows_dropped_as_far_from_the_moment"] = dropped_far
        out[key] = record
    return out


def spread_by_moment(arrays: PanelArrays) -> dict[str, Any]:
    """The round trip at each institutional moment, in bp, across all pairs.

    The earlier probe read this on `EUR_USD` in pips at fixed UTC hours and
    reported a rollover spike smeared across two of them. It is one spike, at
    17:00 New York, split by daylight saving.
    """
    out: dict[str, Any] = {}
    for moment_name in clock.MOMENTS:
        values: list[float] = []
        for day in arrays.days:
            moment = pd.Timestamp(clock.moment_utc(day, moment_name))
            for pair in PAIRS:
                index = arrays.bar_at_or_after(pair, moment)
                if index is None:
                    continue
                if pd.Timestamp(arrays.ts[pair][index]) - pd.Timestamp(_naive_utc(moment)) >= BAR:
                    continue
                if not arrays.contiguous(pair, index - 1, index):
                    continue
                values.append(
                    float(
                        pips_to_bp(
                            arrays.spread[pair][index] + HALF_SPREAD_ADDITION_PIPS,
                            arrays.pip[pair][index],
                            arrays.close[pair][index],
                        )
                    )
                )
        if values:
            out[moment_name] = {"roundtrip_cost_bp": round(float(np.median(values)), 3)}
    baseline: list[float] = []
    for pair in PAIRS:
        baseline.extend(
            pips_to_bp(
                arrays.spread[pair] + HALF_SPREAD_ADDITION_PIPS,
                arrays.pip[pair],
                arrays.close[pair],
            ).tolist()
        )
    out["all_bars_baseline"] = {"roundtrip_cost_bp": round(float(np.median(baseline)), 3)}
    return out


def cost_at_week_boundaries(arrays: PanelArrays) -> dict[str, Any]:
    """What the last bar of the week costs, against an ordinary weekday close.

    Not a curiosity. The calendar rows exposed it: on one panel 84% of the "1w"
    periods happened to end on a Friday and on the other 1% did, purely because
    five *trading* days is not one *calendar* week and holidays shift the
    alignment — and the two panels' costs then differed by 2.6x for no economic
    reason. The economic fact underneath is real and belongs in the record: any
    design holding across the weekly close pays the thinnest spread of the week
    to get out of it.
    """
    last_of_week: list[float] = []
    ordinary_close: list[float] = []
    for pair in PAIRS:
        ts = arrays.ts[pair]
        cost = pips_to_bp(
            arrays.spread[pair] + HALF_SPREAD_ADDITION_PIPS,
            arrays.pip[pair],
            arrays.close[pair],
        )
        #: The final bar before a gap longer than one bar is a session close;
        #: the ones followed by a gap over a day are the weekly close.
        gaps = np.diff(ts)
        boundary = np.flatnonzero(gaps > np.timedelta64(pd.Timedelta(hours=12)))
        last_of_week.extend(cost[boundary].tolist())
        daily = np.flatnonzero(
            (ts.astype("datetime64[h]").astype(np.int64) % 24 == 23)
            & (ts.astype("datetime64[m]").astype(np.int64) % 60 == 45)
        )
        ordinary_close.extend(cost[daily].tolist())
    out: dict[str, Any] = {}
    if last_of_week:
        out["last_bar_before_the_weekend"] = {
            "roundtrip_cost_bp": round(float(np.median(last_of_week)), 3)
        }
    if ordinary_close:
        out["ordinary_2345_utc_close"] = {
            "roundtrip_cost_bp": round(float(np.median(ordinary_close)), 3)
        }
    return out


def cost_by_utc_hour(arrays: PanelArrays) -> dict[str, Any]:
    """The median round trip in each UTC hour, so the one expensive hour is visible."""
    out: dict[str, Any] = {}
    for hour in range(24):
        values: list[float] = []
        for pair in PAIRS:
            selector = arrays.ts[pair].astype("datetime64[h]").astype(np.int64) % 24 == hour
            if not selector.any():
                continue
            values.extend(
                pips_to_bp(
                    arrays.spread[pair][selector] + HALF_SPREAD_ADDITION_PIPS,
                    arrays.pip[pair][selector],
                    arrays.close[pair][selector],
                ).tolist()
            )
        if values:
            out[f"{hour:02d}"] = {"roundtrip_cost_bp": round(float(np.median(values)), 3)}
    return out


def build(panels: dict[str, dict[str, pd.DataFrame]]) -> dict[str, Any]:
    """The whole frontier, and the unit verdict over it."""
    record: dict[str, Any] = {
        "classification": [
            "NON_DECISION_BEARING_EXPLORATORY_ONLY",
            "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
        ],
        "unit": UNIT,
        "power_multiplier": POWER_MULTIPLIER,
        "cost_multiple": COST_MULTIPLE_FOR_HURDLE,
        "signal_draws": SIGNAL_DRAWS,
        "signal_free": True,
        "panels": {},
    }
    for panel, frames in panels.items():
        arrays = PanelArrays(frames)
        record["panels"][panel] = {
            "n_days": len(arrays.days),
            "n_partial_days_excluded": arrays.partial_days,
            "years": round(arrays.years, 3),
            "n_pairs": len(frames),
            "clock_resolution": clock.describe(arrays.days),
            "spread_at_moments": spread_by_moment(arrays),
            "cost_by_utc_hour": cost_by_utc_hour(arrays),
            "cost_at_week_boundaries": cost_at_week_boundaries(arrays),
            "calendar": calendar_designs(arrays),
            "clock": clock_designs(arrays),
        }
    record["unit_audit"] = verify_unit_consistency(record["panels"])
    return record


__all__ = [
    "BAR",
    "CALENDAR_HORIZONS",
    "DAYS_PER_YEAR",
    "ILLUSTRATIVE_GROSS_IR",
    "MIN_BARS_FOR_A_TRADING_DAY",
    "MIN_PAIRS_PER_EVENT",
    "SIGNAL_DRAWS",
    "SIGNAL_TO_PAIR",
    "PanelArrays",
    "build",
    "calendar_designs",
    "clock_designs",
    "cost_at_week_boundaries",
    "cost_by_utc_hour",
    "economics",
    "mde_from_gross",
    "spread_by_moment",
]
