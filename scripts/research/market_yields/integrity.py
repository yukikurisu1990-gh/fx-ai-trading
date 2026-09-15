"""Data integrity, temporal availability and the currency-coverage gate.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

This runs before any signal exists, and it decides the universe. The order the
ruling fixes is: integrity, then availability, then coverage, then the signal-blind
feasibility, then the pre-registration freeze, then execution.

**Availability is the part that is easy to get wrong.** An observation dated `d` is
not information a trader had on `d`. None of the publishing bodies states, on the
page the series comes from, when the value appears. So the rule here is uniform
and conservative rather than guessed per source: a yield observed for date `d`
may inform a position taken at the FX close of `d + 1` trading day, and that
position earns the return of the following day. The lag is applied to the
publication date, not the quote time, so a same-day quote never leaks.
"""

from __future__ import annotations

from typing import Any, Final

import pandas as pd

#: A currency is decision-grade only if all of these hold over the decision span.
GATE: Final[dict[str, Any]] = {
    "source_is_official": "a central bank, a treasury or the equivalent public body",
    "frequency": "daily (business days)",
    "covers_span": "an observation on or before the first decision day and on or after the last",
    "max_gap_business_days": 5,
    "max_stale_run_days": 10,
    #: after the lag and carry-forward, the share of decision days with a usable value
    "min_availability_on_decision_days": 0.99,
    #: how stale a carried value may be, in calendar days, on any decision day
    "max_carried_age_calendar_days": 10,
    "no_duplicate_dates": True,
    "plausible_range_percent": (-5.0, 25.0),
}

#: The conservative availability rule (see the module docstring).
AVAILABILITY_LAG_TRADING_DAYS: Final[int] = 1


def audit_series(frame: pd.DataFrame, first_day: str, last_day: str) -> dict[str, Any]:
    """Coverage, gaps, staleness, duplicates and range of one currency's series."""
    series = frame.dropna(subset=["yield_percent"]).sort_values("date")
    dates = pd.to_datetime(series["date"])
    inside = series[
        (dates >= pd.Timestamp(first_day)).to_numpy() & (dates <= pd.Timestamp(last_day)).to_numpy()
    ]
    inside_dates = pd.to_datetime(inside["date"])
    gaps = inside_dates.diff().dt.days.dropna()
    values = inside["yield_percent"].astype(float)
    unchanged = (values.diff() == 0).astype(int)
    runs = unchanged.groupby((unchanged != unchanged.shift()).cumsum()).sum()
    return {
        "first": str(dates.min().date()) if len(dates) else None,
        "last": str(dates.max().date()) if len(dates) else None,
        "rows_total": int(len(series)),
        "rows_in_span": int(len(inside)),
        "max_gap_calendar_days": int(gaps.max()) if len(gaps) else 0,
        "gaps_over_five_business_days": int((gaps > 7).sum()),
        "longest_unchanged_run": int(runs.max()) if len(runs) else 0,
        "duplicate_dates": int(inside_dates.duplicated().sum()),
        "min_value": round(float(values.min()), 4) if len(values) else None,
        "max_value": round(float(values.max()), 4) if len(values) else None,
        #: measured on the whole series: the span slice cannot reach outside itself
        "covers_first_day": bool(len(dates) and dates.min() <= pd.Timestamp(first_day)),
        "covers_last_day": bool(len(dates) and dates.max() >= pd.Timestamp(last_day)),
        "publication_days_per_fx_trading_day": None,
    }


def verdict(audit: dict[str, Any], fx_trading_days: int, leak: dict[str, Any]) -> dict[str, Any]:
    """Decision-grade or not, with every failing reason named.

    Coverage is measured on what a decision could actually use — the carried,
    lagged value — because national holidays differ between a bond market and the
    FX day, so raw publication days never match one for one. Staleness is gated
    separately, which is where a thin series would show up.
    """
    coverage = leak["observations_used"] / fx_trading_days if fx_trading_days else 0.0
    reasons: list[str] = []
    if not audit["covers_first_day"]:
        reasons.append("no observation on or before the first decision day")
    if not audit["covers_last_day"]:
        reasons.append("no observation on or after the last decision day")
    if coverage < GATE["min_availability_on_decision_days"]:
        reasons.append(f"a usable value on only {coverage:.1%} of decision days")
    age = leak.get("max_age_days")
    if age is not None and age > GATE["max_carried_age_calendar_days"]:
        reasons.append(f"a carried value up to {age} calendar days old")
    if leak.get("same_or_future_dated_values"):
        reasons.append("a value dated on or after its decision day")
    if audit["gaps_over_five_business_days"]:
        reasons.append("a gap longer than five business days")
    if audit["longest_unchanged_run"] > GATE["max_stale_run_days"]:
        reasons.append("an unchanged run longer than ten days")
    if audit["duplicate_dates"]:
        reasons.append("duplicate dates")
    low, high = GATE["plausible_range_percent"]
    for key in ("min_value", "max_value"):
        value = audit[key]
        if value is None or not (low <= value <= high):
            reasons.append(f"{key} outside the plausible range")
    return {
        "availability_on_decision_days": round(coverage, 4),
        "decision_grade": not reasons,
        "reasons": reasons,
    }


def available_from(frame: pd.DataFrame, trading_days: pd.DatetimeIndex) -> pd.Series:
    """The yield usable on each FX trading day, under the conservative lag.

    The value carried into day `t` is the last observation published strictly
    before the previous trading day's close — i.e. dated on or before `t - 1`
    trading day. Nothing dated `t` can reach day `t`.
    """
    series = (
        frame.dropna(subset=["yield_percent"])
        .assign(date=lambda f: pd.to_datetime(f["date"]))
        .set_index("date")["yield_percent"]
        .astype(float)
        .sort_index()
    )
    on_trading_days = series.reindex(series.index.union(trading_days)).ffill().reindex(trading_days)
    return on_trading_days.shift(AVAILABILITY_LAG_TRADING_DAYS)


def leak_check(frame: pd.DataFrame, trading_days: pd.DatetimeIndex) -> dict[str, Any]:
    """Prove the lag: every value used on day t is dated on or before t-1."""
    series = (
        frame.dropna(subset=["yield_percent"])
        .assign(date=lambda f: pd.to_datetime(f["date"]))
        .set_index("date")["yield_percent"]
        .astype(float)
        .sort_index()
    )
    stamps = pd.Series(series.index, index=series.index)
    carried = (
        stamps.reindex(series.index.union(trading_days))
        .ffill()
        .reindex(trading_days)
        .shift(AVAILABILITY_LAG_TRADING_DAYS)
    )
    used = pd.DataFrame({"decision_day": trading_days, "value_dated": carried.to_numpy()}).dropna()
    ages = (used["decision_day"] - used["value_dated"]).dt.days
    return {
        "observations_used": int(len(used)),
        "min_age_days": int(ages.min()) if len(ages) else None,
        "same_or_future_dated_values": int((ages <= 0).sum()),
        "median_age_days": float(ages.median()) if len(ages) else None,
        "max_age_days": int(ages.max()) if len(ages) else None,
    }


__all__ = [
    "AVAILABILITY_LAG_TRADING_DAYS",
    "GATE",
    "audit_series",
    "available_from",
    "leak_check",
    "verdict",
]
