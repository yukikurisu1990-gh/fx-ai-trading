"""The contiguous seen corpus, assembled through each span's own guarded route.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Three spans partition `2021-04-26 … 2025-12-28` and each already has a reader that
guards it. This module **calls those readers** and never constructs a path, a date
bound or a file name of its own: the obvious way to assemble a contiguous corpus
is to parameterise one reader's bounds, and that turns a prohibition into a
default. The guards stay where they are, and what this adds is the concatenation
plus a check that the result is exactly the union of the three declared windows
and nothing else.

The daily currency panel
------------------------

`PAIRS_20` carries each G10 currency an uneven number of times — JPY and USD
appear in seven pairs, CAD, CHF, GBP and NZD in four — so a currency's return is
the mean of its signed pair returns and the cross-section is then demeaned. The
unevenness is real and is reported rather than hidden: a currency observed
through four pairs is measured more noisily than one observed through seven, and
the cross-sectional demeaning is what removes the common factor that H-003
measured at 96% of a naive relative-value book's gross.

Costs
-----

A currency-against-basket position is implemented in pairs, so establishing one
unit of it turns over more than one unit of pair notional. The round trip charged
is the frozen basket figure, applied to the realised change in position.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import bars as development_route
from scripts.research.exploratory_m15 import momentum as momentum_route
from scripts.research.exploratory_m15 import supplemental as supplemental_route
from scripts.research.model_learning import (
    CURRENCIES_G10,
    PAIRS_20,
    SEEN_SPANS,
    assert_not_protected,
)

#: Route per span, in corpus order. The key is the span name in `SEEN_SPANS`, so
#: a span added there without a route here fails loudly rather than silently
#: dropping out of the corpus.
ROUTES: Final[dict[str, Any]] = {
    "momentum_2021_2023": momentum_route,
    "supplemental_2023_2025": supplemental_route,
    "development_2025": development_route,
}

#: A UTC day needs this many M15 bars to count as a trading day. Reused from the
#: figure the Track 2 work settled on: a Sunday reopen carries about a dozen bars
#: and is not a day a daily strategy can trade.
MIN_BARS_FOR_A_TRADING_DAY: Final[int] = 48


class CorpusError(RuntimeError):
    """Raised when the assembled corpus is not the union of the declared spans."""


def _span_bounds() -> tuple[str, str]:
    starts = [block["start"] for block in SEEN_SPANS.values()]
    ends = [block["end"] for block in SEEN_SPANS.values()]
    return min(starts), max(ends)


def load_pair(pair: str) -> pd.DataFrame:
    """One pair's M15 bars across the whole corpus, via the three guarded readers."""
    if pair not in PAIRS_20:
        raise CorpusError(f"{pair!r} is not in PAIRS_20")
    frames = []
    for name, route in ROUTES.items():
        frame = route.load(pair)
        block = SEEN_SPANS[name]
        assert_not_protected(block["start"], block["end"])
        lo = pd.Timestamp(block["start"], tz="UTC")
        hi = pd.Timestamp(block["end"], tz="UTC") + pd.Timedelta(days=1)
        inside = frame[(frame["ts"] >= lo) & (frame["ts"] < hi)]
        if len(inside) != len(frame):
            raise CorpusError(
                f"{name}/{pair}: {len(frame) - len(inside)} rows outside the declared span"
            )
        frames.append(inside)
    corpus = pd.concat(frames, ignore_index=True).sort_values("ts").reset_index(drop=True)
    start, end = _span_bounds()
    if corpus["ts"].min() < pd.Timestamp(start, tz="UTC"):
        raise CorpusError(f"{pair}: a row precedes {start}")
    if corpus["ts"].max() >= pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1):
        raise CorpusError(f"{pair}: a row reaches past {end}")
    if corpus["ts"].duplicated().any():
        raise CorpusError(f"{pair}: the three spans overlap")
    return corpus


def daily_pair_frame(pair: str) -> pd.DataFrame:
    """Daily close-to-close mid log return, spread and activity, all causal.

    The day's close is the last M15 bar stamped inside that UTC day, so nothing in
    a row uses information from after the day it belongs to. Days with too few
    bars are dropped rather than carried at a distorted spread.
    """
    frame = load_pair(pair)
    frame = frame.assign(day=frame["ts"].dt.tz_convert("UTC").dt.date)
    grouped = frame.groupby("day", sort=True)
    daily = pd.DataFrame(
        {
            "bars": grouped["mid_c"].size(),
            "mid_close": grouped["mid_c"].last(),
            "spread_pips": grouped["spread_close_pips"].mean(),
            "bar_range_pips": (
                (grouped["mid_h"].max() - grouped["mid_l"].min()) / frame["pip_size"].iloc[0]
            ),
        }
    )
    daily = daily[daily["bars"] >= MIN_BARS_FOR_A_TRADING_DAY].copy()
    daily["log_return"] = np.log(daily["mid_close"]).diff()
    daily["pair"] = pair
    daily.index = pd.to_datetime(daily.index)
    daily.index.name = "day"
    return daily.dropna(subset=["log_return"])


def _legs(pair: str) -> tuple[str, str]:
    base, quote = pair.split("_")
    return base, quote


def currency_panel(pairs: tuple[str, ...] = PAIRS_20) -> dict[str, pd.DataFrame]:
    """Daily per-currency excess return, plus the state series a feature may use.

    Returns a mapping of quantity name to a `day x currency` frame. Everything is
    stamped on the day it is observed; a feature that needs a trailing window
    takes it from these frames, and a target that needs tomorrow shifts these
    frames rather than reaching into the source.
    """
    daily = {pair: daily_pair_frame(pair) for pair in pairs}
    returns = pd.DataFrame(
        {pair: frame["log_return"] for pair, frame in daily.items()}
    ).sort_index()
    spreads = pd.DataFrame(
        {pair: frame["spread_pips"] for pair, frame in daily.items()}
    ).sort_index()
    ranges = pd.DataFrame(
        {pair: frame["bar_range_pips"] for pair, frame in daily.items()}
    ).sort_index()

    currency_return = pd.DataFrame(index=returns.index, columns=list(CURRENCIES_G10), dtype=float)
    currency_spread = pd.DataFrame(index=returns.index, columns=list(CURRENCIES_G10), dtype=float)
    currency_range = pd.DataFrame(index=returns.index, columns=list(CURRENCIES_G10), dtype=float)
    coverage: dict[str, int] = {}
    for currency in CURRENCIES_G10:
        signed = []
        legs = []
        for pair in pairs:
            base, quote = _legs(pair)
            if currency == base:
                signed.append(returns[pair])
            elif currency == quote:
                signed.append(-returns[pair])
            else:
                continue
            legs.append(pair)
        coverage[currency] = len(legs)
        currency_return[currency] = pd.concat(signed, axis=1).mean(axis=1)
        currency_spread[currency] = spreads[legs].mean(axis=1)
        currency_range[currency] = ranges[legs].mean(axis=1)

    #: The cross-sectional mean is the common factor. Removing it is what makes
    #: this a relative-value panel rather than twenty correlated bets on the
    #: dollar, and it is done here once rather than hoped for downstream.
    excess = currency_return.sub(currency_return.mean(axis=1), axis=0)
    return {
        "currency_return": currency_return,
        "currency_excess_return": excess,
        "common_factor": currency_return.mean(axis=1).to_frame("common_factor"),
        "currency_spread_pips": currency_spread,
        "currency_range_pips": currency_range,
        "coverage": pd.Series(coverage, name="pairs_per_currency").to_frame(),
        "pair_returns": returns,
    }


def provenance(panel: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """What was assembled, in numbers a reader can check against the declaration."""
    excess = panel["currency_excess_return"]
    start, end = _span_bounds()
    return {
        "declared_span": {"start": start, "end": end},
        "observed_first_day": str(excess.index.min().date()),
        "observed_last_day": str(excess.index.max().date()),
        "trading_days": int(len(excess)),
        "currencies": list(excess.columns),
        "pairs_per_currency": {
            currency: int(count)
            for currency, count in panel["coverage"]["pairs_per_currency"].items()
        },
        "min_bars_for_a_trading_day": MIN_BARS_FOR_A_TRADING_DAY,
        "routes": {name: module.__name__ for name, module in ROUTES.items()},
        "protected_spans_read": False,
    }


__all__ = [
    "MIN_BARS_FOR_A_TRADING_DAY",
    "ROUTES",
    "CorpusError",
    "currency_panel",
    "daily_pair_frame",
    "load_pair",
    "provenance",
]
