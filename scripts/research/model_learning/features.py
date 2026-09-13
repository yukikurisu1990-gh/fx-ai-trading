"""The pre-registered features, computed causally and nothing else computed.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Every column below is stamped on the day it could have been known: a feature for
day `t` uses bars up to and including the last M15 bar of day `t`, and the target
it will be joined to is day `t+1`. No column reaches forward, and the one that
looks as though it does — days to the next scheduled central-bank decision — is
forward-known by construction: the meeting dates are published years ahead.

What is here and what is not
----------------------------

The three feature lists are exactly the ones the pre-registration freezes. They
are shorter and plainer than a first draft, because a first draft asked for three
things this corpus cannot give:

* **a day-constant feature in a cross-sectionally demeaned model.** A feature
  identical across currencies on a day has exactly zero covariance with a target
  that sums to zero across currencies, so its coefficient is unidentified by
  construction. It was replaced by the per-currency share of the day's
  dispersion, which is in the same family and is actually estimable.
* **tick volume.** The M15 caches these three routes produced carry no volume
  column, so an activity feature comes from the bar range instead. ⭐ The reason
  as first written was wrong and is corrected here: tick volume **does** exist in
  this repository, at `artifacts/track_a_scratch/monetizability/volume_cache/`,
  for all three spans and all twenty pairs. What is true is that it is not in the
  declared cache, and a phase that reaches outside its own declared inputs has a
  worse problem than a missing feature. It was not re-added after the reviews,
  because adding a feature once results exist is a rescue the pre-registration
  forbids.
* **per-currency central-bank proximity.** Only four of the eight G10 banks
  publish an acquirable calendar. A per-currency anchor would therefore be a
  dummy for "is one of these four currencies", which a model would happily learn
  and which the breadth requirement would then fail. The feature is global — how
  close is the calendar, not whose bank it is — which is what the available data
  supports.

Each substitution was made before any model was fitted and re-froze the
pre-registration hash.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.model_learning import CURRENCIES_G10, PAIRS_20

CALENDAR_PATH: Final[Path] = Path("artifacts/track_a_scratch/exogenous/s1_calendar.json")

#: The four banks whose scheduled decisions this repository could acquire without
#: a login. The other four refused every automated route, which is recorded in the
#: same artefact and is why the proximity feature is global rather than per
#: currency.
ANCHORED_CURRENCIES: Final[tuple[str, ...]] = ("AUD", "EUR", "JPY", "USD")

#: A declared, unfitted risk proxy: commodity and high-beta currencies against the
#: classic funding pair. Fixed in advance, never estimated, so a beta to it is a
#: beta to a constant basket rather than to something chosen with hindsight.
RISK_FACTOR_WEIGHTS: Final[dict[str, float]] = {
    "AUD": 0.5,
    "NZD": 0.5,
    "JPY": -0.5,
    "CHF": -0.5,
}

BETA_WINDOW: Final[int] = 60
VOL_WINDOW: Final[int] = 20
DISPERSION_WINDOW: Final[int] = 20


def _zscore_cross_section(frame: pd.DataFrame) -> pd.DataFrame:
    """Standardise across currencies within each day.

    A cross-sectional standardisation uses only same-day information, which the
    leakage controls require, and it removes the common level that the target has
    already had removed.
    """
    centred = frame.sub(frame.mean(axis=1), axis=0)
    spread = frame.std(axis=1, ddof=0).replace(0.0, np.nan)
    return centred.div(spread, axis=0)


def _rolling_beta(series: pd.DataFrame, factor: pd.Series, window: int) -> pd.DataFrame:
    """Trailing beta of each column on `factor`, closed at the same bar."""
    out = {}
    for column in series.columns:
        paired = pd.concat([series[column], factor], axis=1).dropna()
        covariance = paired.iloc[:, 0].rolling(window).cov(paired.iloc[:, 1])
        variance = paired.iloc[:, 1].rolling(window).var()
        out[column] = (covariance / variance.replace(0.0, np.nan)).reindex(series.index)
    return pd.DataFrame(out)


def leave_one_out_common_factor(currency_return: pd.DataFrame) -> pd.DataFrame:
    """⭐ Each currency's beta is measured against a factor that excludes it.

    Regressing a currency on an average that contains it guarantees a positive
    beta from the arithmetic alone — with eight currencies, one eighth of the
    factor *is* the regressand. The leave-one-out factor removes that, and the
    difference is not small: the naive version would hand every currency a beta
    biased upward by roughly `1/8` of its own variance over the factor's.
    """
    total = currency_return.sum(axis=1)
    count = currency_return.notna().sum(axis=1)
    out = {}
    for currency in currency_return.columns:
        others = (total - currency_return[currency]) / (count - 1)
        out[currency] = others
    return pd.DataFrame(out)


def calendar_distance(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Days to the next and since the last scheduled decision of the four banks.

    Forward-known: the meeting dates are published well in advance, so knowing on
    day `t` that a meeting falls on `t+3` uses no information from `t+3`.
    """
    payload = json.loads(CALENDAR_PATH.read_text(encoding="utf-8"))["payload"]
    dates = sorted(
        {
            dt.date.fromisoformat(value)
            for currency in ANCHORED_CURRENCIES
            for value in payload["dates"][currency]
        }
    )
    stamps = np.array([pd.Timestamp(value) for value in dates])
    days = index.normalize()
    to_next, since_last = [], []
    for day in days:
        future = stamps[stamps >= day]
        past = stamps[stamps <= day]
        to_next.append((future[0] - day).days if len(future) else np.nan)
        since_last.append((day - past[-1]).days if len(past) else np.nan)
    return pd.DataFrame(
        {
            "days_to_next_scheduled_g4_decision": to_next,
            "days_since_last_scheduled_g4_decision": since_last,
        },
        index=index,
    )


def hourly_currency_excess(pairs: tuple[str, ...] = PAIRS_20) -> pd.DataFrame:
    """H1 currency excess returns, for the multi-timeframe alignment feature."""
    from scripts.research.model_learning import corpus as corpus_module

    hourly: dict[str, pd.Series] = {}
    for pair in pairs:
        frame = corpus_module.load_pair(pair)
        series = frame.set_index("ts")["mid_c"].resample("1h").last().dropna()
        hourly[pair] = np.log(series).diff()
    returns = pd.DataFrame(hourly).sort_index()
    per_currency = {}
    for currency in CURRENCIES_G10:
        signed = []
        for pair in pairs:
            base, quote = pair.split("_")
            if currency == base:
                signed.append(returns[pair])
            elif currency == quote:
                signed.append(-returns[pair])
        per_currency[currency] = pd.concat(signed, axis=1).mean(axis=1)
    level = pd.DataFrame(per_currency)
    return level.sub(level.mean(axis=1), axis=0)


def _alignment(hourly_excess: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    """Sign agreement of the trailing 1h, 4h and 24h cumulative excess return.

    Evaluated at the last hourly stamp inside each decision day, so the window
    closes with the day rather than straddling it.
    """
    cumulative = {
        hours: hourly_excess.rolling(hours, min_periods=hours).sum() for hours in (1, 4, 24)
    }
    signs = sum(np.sign(frame) for frame in cumulative.values()) / 3.0
    daily = signs.resample("1D").last()
    #: The hourly frame is tz-aware UTC and the daily panel is stamped with plain
    #: dates. Reindexing across that difference silently returns an all-NaN
    #: column rather than raising, which is how a feature can reach a fit as a
    #: column of nothing — so the index is made comparable explicitly.
    daily.index = pd.DatetimeIndex(daily.index).tz_localize(None).normalize()
    return daily.reindex(days.normalize()).set_axis(days)


def build(panel: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Every pre-registered feature, as `day x currency` frames.

    One dictionary, so a track can take the columns it registered and nothing
    else. A feature computed here and not registered by any track is dead weight,
    and a test measures that the two sets agree.
    """
    excess = panel["currency_excess_return"]
    level = panel["currency_return"]
    days = excess.index

    features: dict[str, pd.DataFrame] = {}

    for window in (5, 20, 60):
        features[f"currency_excess_return_{window}d_z"] = _zscore_cross_section(
            excess.rolling(window, min_periods=window).sum()
        )

    realised_vol = level.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).std(ddof=0)
    features["currency_realised_vol_20d_z"] = _zscore_cross_section(realised_vol)
    short_vol = level.rolling(5, min_periods=5).std(ddof=0)
    features["currency_realised_vol_5d_over_20d"] = _zscore_cross_section(
        short_vol / realised_vol.replace(0.0, np.nan)
    )

    #: Per-currency share of the day's cross-sectional dispersion, averaged over
    #: the window. Replaces a day-constant dispersion level, which a demeaned
    #: target cannot identify.
    dispersion = excess.abs().div(excess.abs().sum(axis=1).replace(0.0, np.nan), axis=0)
    features["currency_dispersion_share_20d_z"] = _zscore_cross_section(
        dispersion.rolling(DISPERSION_WINDOW, min_periods=DISPERSION_WINDOW).mean()
    )

    loo = leave_one_out_common_factor(level)
    common_beta = {}
    for currency in level.columns:
        paired = pd.concat([level[currency], loo[currency]], axis=1)
        covariance = paired.iloc[:, 0].rolling(BETA_WINDOW).cov(paired.iloc[:, 1])
        variance = paired.iloc[:, 1].rolling(BETA_WINDOW).var()
        common_beta[currency] = covariance / variance.replace(0.0, np.nan)
    features["currency_beta_to_common_factor_60d"] = _zscore_cross_section(
        pd.DataFrame(common_beta)
    )

    risk = sum(weight * level[currency] for currency, weight in RISK_FACTOR_WEIGHTS.items())
    features["currency_beta_to_risk_factor_60d"] = _zscore_cross_section(
        _rolling_beta(level, risk, BETA_WINDOW)
    )

    #: Days since the sign of the trailing 20-day excess return last changed,
    #: capped so one long trend cannot dominate the column's scale.
    trend = np.sign(excess.rolling(20, min_periods=20).sum())
    ages = {}
    for column in trend.columns:
        group = trend[column].ne(trend[column].shift(1)).cumsum()
        ages[column] = trend[column].groupby(group).cumcount()
    features["trend_age_d1_normalised"] = _zscore_cross_section(
        pd.DataFrame(ages).clip(upper=60).astype(float)
    )

    spread = panel["currency_spread_pips"]
    features["currency_spread_state_20d_z"] = _zscore_cross_section(
        spread / spread.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).mean().replace(0.0, np.nan)
    )
    bar_range = panel["currency_range_pips"]
    features["currency_range_state_20d_z"] = _zscore_cross_section(
        bar_range
        / bar_range.rolling(VOL_WINDOW, min_periods=VOL_WINDOW).mean().replace(0.0, np.nan)
    )

    alignment = _alignment(hourly_currency_excess(), days)
    features["multi_timeframe_alignment_h1_h4_d1"] = alignment

    distance = calendar_distance(days)
    for column in distance.columns:
        features[column] = pd.DataFrame(
            {currency: distance[column] for currency in CURRENCIES_G10}, index=days
        )

    return features


def provenance() -> dict[str, Any]:
    return {
        "anchored_currencies": list(ANCHORED_CURRENCIES),
        "unacquirable_currencies": ["CAD", "CHF", "GBP", "NZD"],
        "risk_factor_weights": dict(RISK_FACTOR_WEIGHTS),
        "beta_window_days": BETA_WINDOW,
        "beta_factor_is_leave_one_out": True,
        "substitutions": {
            "cross_sectional_dispersion_20d_z": (
                "replaced by currency_dispersion_share_20d_z — a day-constant feature has "
                "zero covariance with a cross-sectionally demeaned target"
            ),
            "tick_activity_state_20d_z": (
                "replaced by currency_range_state_20d_z — the declared M15 caches carry "
                "no volume column. Volume exists in this repository at "
                "artifacts/track_a_scratch/monetizability/volume_cache/, which the first "
                "version of this note did not say; reaching outside the declared inputs "
                "is the reason it was not used, not absence"
            ),
            "days_to_next_scheduled_central_bank_decision": (
                "made global (days_to_next_scheduled_g4_decision) — four of eight banks "
                "publish no acquirable calendar, so a per-currency anchor is a dummy for "
                "those four currencies"
            ),
            "currency_beta_to_usd_factor_60d": (
                "renamed currency_beta_to_common_factor_60d and computed leave-one-out"
            ),
        },
    }


__all__ = [
    "ANCHORED_CURRENCIES",
    "BETA_WINDOW",
    "CALENDAR_PATH",
    "RISK_FACTOR_WEIGHTS",
    "build",
    "calendar_distance",
    "hourly_currency_excess",
    "leave_one_out_common_factor",
    "provenance",
]
