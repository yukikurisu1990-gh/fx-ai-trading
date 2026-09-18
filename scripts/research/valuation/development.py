"""T-V Stage 1: is a currency that is cheap in real terms cheap for a reason?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

    python -m scripts.research.valuation.development

Runs what `prereg.py` froze and committed before the first FX observation was
requested: one anchor, one sign, one horizon, three books, a monthly cadence, and
a screen whose bands were fixed in advance. Seen data decides nothing either way.

Two facts about the construction are worth stating because they are easy to get
wrong and neither is a choice made here:

* **Base years cancel.** The CPI indices have different base years, so the level
  of `log CPI_c` is arbitrary. The anchor is each currency's own expanding mean of
  `q_c`, and `d_c = q_c - a_c` removes any constant per currency, so an arbitrary
  base is not an arbitrary signal. What survives is the *change* in relative price
  levels since each currency's own history, which is what the hypothesis is about.
* **The book is spot-only, and that is a disclosed shortfall.** The frozen data
  sources are the ECB's reference rates and the BIS's consumer prices. Neither
  carries an interest rate, so the routed P&L here is the spot return of the pairs
  and not a full currency excess return. Which way that cuts is measured rather
  than assumed (`carry_exposure`): the primary test is systematically long the
  *low*-inflation currencies, so if inflation carries into rates the omitted carry
  is negative and the omission **overstates** this book. No rate source was added
  after the freeze to repair it.
* **The quarterly publishers needed the lag counted from a different label.** The
  frozen text believed the source carried each quarter's value forward across its
  months; it does not — it stamps the one reading on all three, two of which
  precede its publication. `_lagged_log_cpi` counts the frozen lag from the
  quarter's end, and `as_frozen=True` reproduces the original for comparison.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from scripts.research.market_yields import development as fast
from scripts.research.market_yields import portfolio, risk
from scripts.research.valuation import DATA_DIR, RECORD_DIR, prereg, sources

ROOT = Path(__file__).resolve().parents[3]

BOOK = portfolio.BookConfig(
    name="t_v",
    mapping="linear",
    neutralize_leading_factor=True,
    weight_cap=0.25,
    band=0.10,
    vol_target=0.10,
    max_leverage=1_000_000.0,
)


def load_panels() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The acquired series as two frames: daily FX per euro, and monthly log CPI.

    The FX frame carries a EUR column of exactly 1.0 — the euro is the numeraire of
    the ECB's own reference rates, not a series that could be fetched.
    """
    data = ROOT / DATA_DIR
    fx = pd.DataFrame(
        {
            series.currency: pd.read_parquet(data / f"fx_{series.currency.lower()}.parquet")
            .set_index("period")["value"]
            .astype(float)
            for series in sources.FX
        }
    )
    fx.index = pd.to_datetime(fx.index)
    fx["EUR"] = 1.0
    fx = fx[list(prereg.UNIVERSE)].sort_index()
    cpi = pd.DataFrame(
        {
            series.currency: pd.read_parquet(data / f"cpi_{series.currency.lower()}.parquet")
            .set_index("period")["value"]
            .astype(float)
            for series in sources.CPI
        }
    )
    cpi = cpi[list(prereg.UNIVERSE)].sort_index()
    return fx, cpi


def pair_return_panel(fx: pd.DataFrame) -> pd.DataFrame:
    """Pair returns from the cross rates, for every pair both of whose legs are here.

    The price of `BASE_QUOTE` is units of quote per unit of base, which from rates
    quoted against the euro is `rate_quote / rate_base`. A day missing either leg
    cannot be priced and is dropped by the caller.
    """
    pairs = portfolio.tradable_pairs(prereg.UNIVERSE)
    prices = {}
    for pair in pairs:
        base, quote = pair.split("_")
        prices[pair] = fx[quote] / fx[base]
    return pd.DataFrame(prices).pct_change().dropna(how="all")


def _decision_days(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """The last trading day of each month present in the FX calendar."""
    frame = pd.Series(index, index=index)
    return pd.DatetimeIndex(frame.groupby([index.year, index.month]).last().to_numpy())


def quarterly_publishers(cpi: pd.DataFrame) -> tuple[str, ...]:
    """Which series the publisher stamps on all three months of its quarter.

    Detected from the data rather than named, so the property is measured on what
    was actually acquired instead of asserted from a country list.
    """
    quarters = pd.PeriodIndex(cpi.index, freq="M").asfreq("Q")
    return tuple(
        currency
        for currency in cpi.columns
        if bool((cpi[currency].groupby(quarters).nunique() <= 1).all())
    )


def _lagged_log_cpi(
    cpi: pd.DataFrame, days: pd.DatetimeIndex, *, as_frozen: bool = False
) -> pd.DataFrame:
    """Log CPI as it could have been known, with the quarterly publishers handled.

    The frozen text says the index for month `M` is used only from the end of month
    `M + lag`, and describes the quarterly publishers as carrying their quarter's
    value forward under the same rule. **The source does not do that.** The BIS
    stamps a quarter's single reading onto all three of its months, including the two
    that precede the reading's existence, so a lag counted from the *stamped* month
    lands inside the quarter for a third of decisions — the decision at the end of
    December 2010 would use the Q4-2010 Australian CPI, published on 26 January 2011.

    The lag is therefore counted from the end of the quarter the reading belongs to,
    which is the frozen constant applied to the right label. Removing a look-ahead is
    not a rescue and cannot be one here: the look-ahead flattered a book that failed,
    and the leak-free result is the weaker of the two. `as_frozen=True` reproduces the
    original behaviour so both can be reported side by side.
    """
    lag = prereg.CPI_PUBLICATION_LAG_MONTHS
    periods = pd.PeriodIndex(cpi.index, freq="M")
    logged = pd.DataFrame(np.log(cpi.to_numpy(dtype=float)), index=periods, columns=cpi.columns)
    wanted = pd.PeriodIndex(days, freq="M") - lag
    missing = wanted.difference(logged.index)
    if len(missing):  # pragma: no cover - the request covers the span with room to spare
        raise RuntimeError(f"CPI missing for {list(missing)[:3]}")
    quarterly = () if as_frozen else quarterly_publishers(cpi)
    out = pd.DataFrame(index=days, columns=cpi.columns, dtype=float)
    for currency in cpi.columns:
        if currency not in quarterly:
            out[currency] = logged.loc[wanted, currency].to_numpy()
            continue
        labels = []
        for period in wanted:
            #: the end of the quarter this stamped month belongs to, stepped back when
            #: that end has not happened yet by the month the lag points at
            end = period.asfreq("Q").asfreq("M", how="end")
            if end > period:
                end = (period.asfreq("Q") - 1).asfreq("M", how="end")
            labels.append(end)
        out[currency] = logged.loc[pd.PeriodIndex(labels), currency].to_numpy()
    return out


def _demean(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.sub(frame.mean(axis=1), axis=0)


def _expanding_anchor(q: pd.DataFrame) -> pd.DataFrame:
    """Each currency's own mean of every month observed so far, itself included.

    `min_periods` is the pre-registered minimum: a currency with fewer months than
    that has no anchor and therefore no position, which `dropna` enforces later.
    """
    return q.expanding(min_periods=prereg.MIN_ANCHOR_MONTHS).mean()


def _median_anchor(q: pd.DataFrame) -> pd.DataFrame:
    return q.expanding(min_periods=prereg.MIN_ANCHOR_MONTHS).median()


def build_signals(
    fx: pd.DataFrame,
    cpi: pd.DataFrame,
    days: pd.DatetimeIndex,
    *,
    anchor=_expanding_anchor,
    as_frozen: bool = False,
) -> dict[str, pd.DataFrame]:
    """The three pre-registered books, on the monthly decision calendar.

    `n_c` is the log euro value of one unit of `c`; the ECB quotes units of `c` per
    euro, so it is the negative of the log rate and the euro's own value is zero.
    The real value adds the lagged relative price level: `q_c = n_c + pi_c`, so a
    currency whose nominal value held while its prices rose is dear in real terms.

    This is the only construction in the track — the leave-one-out books come through
    here too, on a subset of the columns, so a subset cannot drift from the whole.
    """
    nominal = _demean(-np.log(fx.loc[days].astype(float)))
    prices = _demean(_lagged_log_cpi(cpi, days, as_frozen=as_frozen))
    real = nominal + prices

    valuation = fast._z(-(real - anchor(real)))
    control = fast._z(-(nominal - anchor(nominal)))
    return {
        "A_valuation": valuation,
        "B_nominal_control": control,
        "C_residualised": fast._residualise(valuation, control),
    }


def daily_mu(signal: pd.DataFrame, calendar: pd.DatetimeIndex) -> pd.DataFrame:
    """The monthly decision, held until the next one.

    The execution layer is daily, so a monthly book is a daily book whose target
    does not move between decisions. The no-trade band then produces no trade on
    the days in between, and the only intra-month movement is the volatility
    targeter's own leverage, which is a real cost of running a targeted book.
    """
    usable = signal.dropna(how="any")
    if usable.empty:  # pragma: no cover - the span is long enough by construction
        raise RuntimeError("no decision day has a complete cross-section")
    start = calendar.get_loc(usable.index[0])
    held = pd.DataFrame(index=calendar[start:], columns=signal.columns, dtype=float)
    held.loc[usable.index] = usable
    return held.ffill().dropna(how="any")


def _turnover_cost(
    result: dict[str, Any], decision_days: pd.DatetimeIndex, turnover: float
) -> dict[str, Any]:
    """The cost picture, and — the part that is easy to get backwards — who trades.

    A monthly book on a daily layer trades for two reasons: the signal steps at the
    month end, and the volatility targeter re-levers whenever its hysteresis is
    crossed. Only the first is the designed-in cadence. Splitting them is the
    difference between "the source is slow" and "the execution layer has a floor".
    """
    daily = result["daily"]
    net = daily["net"].to_numpy(dtype=float)
    gross = daily["gross"].to_numpy(dtype=float)
    annual_gross = float(np.mean(gross) * 252.0)
    annual_cost = float(daily["cost"].mean() * 252.0)
    on_decision = daily["decision_day"].isin(set(decision_days))
    traded_notional = daily["one_way_traded"]
    total = float(traded_notional.sum())
    signal_share = float(traded_notional[on_decision].sum()) / total if total > 0 else float("nan")
    return {
        "gross_t_stat": round(float(np.mean(gross) / np.std(gross, ddof=0) * np.sqrt(len(net))), 3),
        "net_t_stat": round(float(np.mean(net) / np.std(net, ddof=0) * np.sqrt(len(net))), 3),
        "break_even_cost_multiple": round(annual_gross / annual_cost, 3)
        if annual_cost > 0
        else None,
        "faithful_annual_implementation_cost": round(
            float(daily["implementation_cost"].mean() * 252.0), 5
        ),
        "days_traded": int(daily["traded"].sum()),
        "trades_per_year": round(float(daily["traded"].sum()) / len(daily) * 252.0, 2),
        "decisions_in_the_book": int(on_decision.sum()),
        "decisions_that_did_not_trade": int((on_decision & ~daily["traded"]).sum()),
        "turnover_from_the_signal": round(turnover * signal_share, 3),
        "turnover_from_the_volatility_targeter": round(turnover * (1.0 - signal_share), 3),
        "share_of_turnover_from_the_signal": round(signal_share, 4),
        "what_that_means": (
            "the no-trade band blocks most monthly decisions outright, so most of what this "
            "book pays is the targeter re-levering, not the signal moving. The layer imposes a "
            "turnover floor that no slowing of the signal can go below"
        ),
    }


def _concentration(result: dict[str, Any]) -> dict[str, Any]:
    """Where the net came from in time, which the prereg asks for and a stop needs."""
    daily = result["daily"]
    net = daily["net"]
    total = float(net.sum())
    ranked = net.sort_values(ascending=False)
    by_year = net.groupby(net.index.year).sum()
    largest_day = ranked.index[0]
    row = daily.loc[largest_day]
    exposures = {c: float(row[f"x_{c}"]) for c in prereg.UNIVERSE}
    biggest = max(exposures, key=lambda c: abs(exposures[c]))
    return {
        "total_net": round(total, 5),
        "top_1_day_share_of_net": round(float(ranked.iloc[0]) / total, 4) if total else None,
        "top_5_day_share_of_net": round(float(ranked.iloc[:5].sum()) / total, 4) if total else None,
        "top_10_day_share_of_net": round(float(ranked.iloc[:10].sum()) / total, 4)
        if total
        else None,
        "net_without_the_top_5_days": round(total - float(ranked.iloc[:5].sum()), 5),
        "largest_day": str(pd.Timestamp(largest_day).date()),
        "largest_day_net": round(float(ranked.iloc[0]), 5),
        "largest_exposure_on_that_day": {biggest: round(exposures[biggest], 4)},
        "positive_calendar_years": int((by_year > 0).sum()),
        "calendar_years": int(len(by_year)),
    }


def _terciles(signal: pd.DataFrame, excess: pd.DataFrame, months: int) -> dict[str, Any]:
    """Mean forward excess return by valuation tercile, at the primary horizon.

    The ordering the hypothesis predicts is monotone: cheap earns more than dear.
    """
    horizon = int(round(months * 21))
    forward = excess.rolling(horizon).sum().shift(-horizon)
    rows: list[tuple[int, float]] = []
    for day in signal.index:
        if day not in forward.index:
            continue
        scores = signal.loc[day].dropna()
        future = forward.loc[day].reindex(scores.index).dropna()
        if len(future) < 3:
            continue
        ranked = scores.loc[future.index].rank(pct=True)
        for currency, value in future.items():
            bucket = 0 if ranked[currency] <= 1 / 3 else (2 if ranked[currency] > 2 / 3 else 1)
            rows.append((bucket, float(value)))
    frame = pd.DataFrame(rows, columns=["tercile", "forward"])
    means = frame.groupby("tercile")["forward"].mean()
    #: tercile 2 is the cheapest, because the signal is the z-score of -deviation
    order = [round(float(means.get(b, np.nan)), 5) for b in (2, 1, 0)]
    return {
        "mean_forward_excess_return_cheap_mid_dear": order,
        "monotone_cheap_to_dear": bool(all(np.isfinite(order)) and order[0] > order[1] > order[2]),
        "horizon_trading_days": horizon,
        "observations": int(len(frame)),
    }


def _newey_west_t(values: np.ndarray, lag: int = 3) -> float:
    """A t-statistic that survives the overlap a 3-month horizon on monthly dates has.

    Consecutive observations share two thirds of their window, so the naive standard
    error understates. Bartlett weights at lag 3 are the smallest honest correction.
    """
    if len(values) < lag + 2:  # pragma: no cover - the span is far longer
        return float("nan")
    centred = values - values.mean()
    n = len(values)
    variance = float(centred @ centred) / n
    for k in range(1, lag + 1):
        weight = 1.0 - k / (lag + 1.0)
        variance += 2.0 * weight * float(centred[k:] @ centred[:-k]) / n
    return float(values.mean() / np.sqrt(max(variance, 1e-18) / n))


def _monthly_ic(signal: pd.DataFrame, forward: pd.DataFrame) -> np.ndarray:
    """The per-decision cross-sectional rank IC against the forward window."""
    out = []
    for day in signal.dropna(how="any").index:
        if day not in forward.index or forward.loc[day].isna().any():
            continue
        out.append(signal.loc[day].corr(forward.loc[day], method="spearman"))
    return np.array(out, dtype=float)


def _tercile_spread(signal: pd.DataFrame, forward: pd.DataFrame) -> np.ndarray:
    """Cheap-minus-dear forward return, one observation per decision."""
    out = []
    for day in signal.dropna(how="any").index:
        if day not in forward.index or forward.loc[day].isna().any():
            continue
        ranked = signal.loc[day].rank(pct=True)
        out.append(
            float(
                forward.loc[day][ranked > 2 / 3].mean() - forward.loc[day][ranked <= 1 / 3].mean()
            )
        )
    return np.array(out, dtype=float)


def forecasting_power(
    signals: dict[str, pd.DataFrame], excess: pd.DataFrame, months: int
) -> dict[str, Any]:
    """The two pre-registered metrics the first run declared and did not compute.

    `PREREG["metrics"]` names "incremental IC beyond the nominal control" and the
    signal's persistence. The incremental IC is the direct, pre-registered answer to
    the primary question — whether the real valuation signal forecasts better than
    nominal mean reversion alone — and it is better powered than the tercile spreads
    the first write-up leaned on, so leaving it out understated the run's own result.
    """
    horizon = int(round(months * 21))
    forward = excess.rolling(horizon).sum().shift(-horizon)
    ics = {name: _monthly_ic(signal, forward) for name, signal in signals.items()}
    spreads = {name: _tercile_spread(signal, forward) for name, signal in signals.items()}
    shared = min(len(ics["A_valuation"]), len(ics["B_nominal_control"]))
    incremental = ics["A_valuation"][:shared] - ics["B_nominal_control"][:shared]
    spread_gap = spreads["B_nominal_control"][:shared] - spreads["A_valuation"][:shared]
    return {
        "horizon_trading_days": horizon,
        "decisions_scored": int(shared),
        "ic": {
            name: {
                "mean": round(float(values.mean()), 4),
                "newey_west_t": round(_newey_west_t(values), 2),
            }
            for name, values in ics.items()
        },
        "incremental_ic_of_valuation_beyond_the_nominal_control": {
            "mean": round(float(incremental.mean()), 4),
            "newey_west_t": round(_newey_west_t(incremental), 2),
            "reading": (
                "negative means the real valuation signal forecasts the three-month "
                "cross-section worse than the nominal deviation it is supposed to improve on"
            ),
        },
        "tercile_spread_cheap_minus_dear": {
            name: {
                "mean_pp": round(float(values.mean()) * 100, 4),
                "newey_west_t": round(_newey_west_t(values), 2),
            }
            for name, values in spreads.items()
        },
        "control_minus_valuation_tercile_spread": {
            "mean_pp": round(float(spread_gap.mean()) * 100, 4),
            "newey_west_t": round(_newey_west_t(spread_gap), 2),
            "reading": (
                "the point estimate favours the control, but this is the statistic that "
                "cannot carry the claim on its own; the incremental IC can"
            ),
        },
        "signal_persistence_month_to_month": {
            name: round(float(np.nanmean([signal[c].autocorr(1) for c in signal.columns])), 4)
            for name, signal in signals.items()
        },
    }


def carry_exposure(signals: dict[str, pd.DataFrame], cpi: pd.DataFrame) -> dict[str, Any]:
    """Which way the omitted carry would have gone, measured rather than assumed.

    The spot-only shortfall is only interpretable with a direction, and the direction
    is testable on the frozen CPI panel without any new source: if the book is long
    the currencies whose prices rose fastest, omitting carry understates it; if it is
    long the slow-inflation currencies, omitting carry overstates it.
    """
    lag = prereg.CPI_PUBLICATION_LAG_MONTHS
    logged = pd.DataFrame(
        np.log(cpi.to_numpy(dtype=float)),
        index=pd.PeriodIndex(cpi.index, freq="M"),
        columns=cpi.columns,
    )
    out: dict[str, Any] = {}
    for name, signal in signals.items():
        rows = []
        for day in signal.dropna(how="any").index:
            period = pd.Period(day, freq="M") - lag
            if period - 12 not in logged.index:
                continue
            trailing = logged.loc[period] - logged.loc[period - 12]
            rows.append(signal.loc[day].corr(trailing - trailing.mean(), method="spearman"))
        values = np.array(rows, dtype=float)
        out[name] = {
            "mean_rank_correlation_with_relative_trailing_inflation": round(
                float(values.mean()), 4
            ),
            "newey_west_t": round(_newey_west_t(values), 2),
            "decisions": int(len(values)),
        }
    return out


def negative_drops(drops: dict[str, float]) -> int:
    """How many leave-one-out books lose the sign. Counted, never transcribed."""
    return sum(1 for value in drops.values() if value <= 0)


def _worst_year(result: dict[str, Any]) -> dict[str, Any]:
    """The sign after removing the best rolling twelve months of net P&L."""
    #: the layer already indexes by the P&L day
    daily = result["daily"]["net"]
    rolling = daily.rolling(252).sum()
    if rolling.dropna().empty:  # pragma: no cover - the span is far longer
        return {"available": False}
    best_end = rolling.idxmax()
    window = daily.loc[:best_end].tail(252).index
    without = daily.drop(window)
    return {
        "best_12m_window_net": round(float(rolling.max()), 5),
        "worst_12m_window_net": round(float(rolling.min()), 5),
        "total_net": round(float(daily.sum()), 5),
        "net_without_the_best_12m": round(float(without.sum()), 5),
        "sign_survives_removing_the_best_year": bool(without.sum() > 0),
    }


def _drop_one(fx: pd.DataFrame, cpi: pd.DataFrame, panel: pd.DataFrame) -> dict[str, float]:
    """The primary test rebuilt on seven currencies, routing and returns included."""
    drops: dict[str, float] = {}
    for dropped in prereg.UNIVERSE:
        kept = tuple(c for c in prereg.UNIVERSE if c != dropped)
        kept_excess = portfolio.universe_panel({"pair_returns": panel}, kept)
        kept_days = _decision_days(pd.DatetimeIndex(kept_excess.index))
        signals = build_signals(fx[list(kept)], cpi[list(kept)], kept_days)
        mu = daily_mu(signals["C_residualised"], pd.DatetimeIndex(kept_excess.index))
        result = portfolio.run_book(BOOK, mu, kept_excess, universe=kept)
        drops[f"without_{dropped}"] = fast._summary(result)["net_sharpe"]
    return drops


def run() -> dict[str, Any]:
    fx, cpi = load_panels()
    panel = pair_return_panel(fx)
    excess = portfolio.universe_panel({"pair_returns": panel}, prereg.UNIVERSE)
    calendar = pd.DatetimeIndex(excess.index)
    last = str(calendar[-1].date())
    if last >= sources.PROTECTED_FROM:  # pragma: no cover - the acquisition guard ran first
        raise RuntimeError(f"the panel reaches {last}, at or past the protected span")

    days = _decision_days(calendar)
    signals = build_signals(fx, cpi, days)
    median_signals = build_signals(fx, cpi, days, anchor=_median_anchor)

    books: dict[str, Any] = {}
    results: dict[str, Any] = {}
    for name, signal in signals.items():
        mu = daily_mu(signal, calendar)
        result = portfolio.run_book(BOOK, mu, excess, universe=prereg.UNIVERSE)
        results[name] = result
        summary = fast._summary(result)
        books[name] = {
            "summary": summary,
            "extra": _turnover_cost(
                result,
                signal.dropna(how="any").index,
                summary["turnover_round_trips_per_year_per_unit_gross"],
            ),
            "concentration": _concentration(result),
            "blocks": fast._blocks(result),
            "per_currency_gross_pnl": fast._per_currency(result),
            "ic_at_the_primary_horizon": fast._ic(
                signal.dropna(how="any"), excess, int(round(prereg.PRIMARY_HORIZON_MONTHS * 21))
            ),
            "terciles": _terciles(signal, excess, prereg.PRIMARY_HORIZON_MONTHS),
            "worst_year": _worst_year(result),
            "first_decision_day": str(mu.index[0].date()),
            "cost_stress": {
                f"x{multiple:g}": fast._summary(
                    portfolio.run_book(
                        BOOK, mu, excess, universe=prereg.UNIVERSE, cost_multiple=multiple
                    )
                )["net_sharpe"]
                for multiple in prereg.COST_STRESSES
            },
        }

    robustness = {}
    for name, signal in median_signals.items():
        mu = daily_mu(signal, calendar)
        result = portfolio.run_book(BOOK, mu, excess, universe=prereg.UNIVERSE)
        robustness[name] = fast._summary(result)

    #: the run as the frozen text literally described it, kept for comparison only:
    #: it is the version that carried the quarterly look-ahead, and it is the better
    #: of the two, which is exactly why it cannot be the one the verdict rests on
    as_frozen = {}
    frozen_signals = build_signals(fx, cpi, days, as_frozen=True)
    for name, signal in frozen_signals.items():
        mu = daily_mu(signal, calendar)
        as_frozen[name] = fast._summary(
            portfolio.run_book(BOOK, mu, excess, universe=prereg.UNIVERSE)
        )

    drops = _drop_one(fx, cpi, panel)
    primary = books["C_residualised"]["summary"]
    vol_per_unit_gross = primary["realized_annual_vol"] / primary["mean_currency_gross"]
    capacity = {
        f"{target:g}": risk.leverage_for_return(
            ROOT,
            prereg.UNIVERSE,
            vol_per_unit_gross=vol_per_unit_gross,
            net_sharpe=primary["net_sharpe"],
            annual_target=target,
        )
        for target in (0.05, 0.10)
    }
    stress = risk.gap_stress(
        ROOT, prereg.UNIVERSE, vol_per_unit_gross=vol_per_unit_gross, target_vol=0.10
    )
    screen = _screen(books, robustness, drops, capacity)
    #: the book's own span, not the panel's: the warm-up years carry no position
    years = primary["days"] / 252.0
    return {
        "power": {
            "traded_years": round(years, 2),
            "panel_years": round(len(calendar) / 252.0, 2),
            "decision_months_with_a_position": int(
                len(build_signals(fx, cpi, days)["C_residualised"].dropna(how="any"))
            ),
            #: two-sided 5%, 80% power, on an annual Sharpe estimated over this span
            "detectable_net_sharpe_at_80pct_power": round((1.96 + 0.8416) / np.sqrt(years), 3),
            "what_it_means": (
                "a book below this Sharpe cannot be separated from zero here, whichever way the "
                "screen falls. It is why a pass would not have been a confirmation either"
            ),
        },
        "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
        "workflow_status": "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
        "track": "T-V",
        "prereg": prereg.PREREG,
        "prereg_digest": hashlib.sha256(
            json.dumps(prereg.PREREG, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
        "executed_book_config": {
            field.name: getattr(BOOK, field.name) for field in dataclasses.fields(BOOK)
        },
        "universe": list(prereg.UNIVERSE),
        "tradable_pairs": list(portfolio.tradable_pairs(prereg.UNIVERSE)),
        "span": {"first": str(calendar[0].date()), "last": last},
        "return_panel_days": int(len(calendar)),
        "decision_months": int(len(days)),
        "identity_check": portfolio.identity_check(
            {"pair_returns": panel},
            prereg.UNIVERSE,
            np.array([0.25, -0.25, 0.10, -0.10, 0.05, -0.05, 0.0, 0.0]),
        ),
        "books": books,
        "forecasting_power": forecasting_power(signals, excess, prereg.PRIMARY_HORIZON_MONTHS),
        "carry_exposure": carry_exposure(signals, cpi),
        "quarterly_publishers": list(quarterly_publishers(cpi)),
        "as_the_frozen_text_described_the_source": {
            "summaries": as_frozen,
            "why_it_is_not_the_result": (
                "the frozen text says the quarterly publishers carry their quarter's value "
                "forward under the same lag. The BIS instead stamps a quarter's single reading "
                "onto all three of its months, so counting the lag from the stamped month reaches "
                "a reading published weeks later on a third of decisions. This column is that "
                "behaviour; the reported books count the lag from the quarter's end instead. The "
                "look-ahead flattered the book, so removing it lowers every figure and cannot be "
                "a rescue"
            ),
        },
        "robustness_median_anchor": robustness,
        "leave_one_currency_out_net_sharpe": drops,
        "leave_one_out_negative_count": negative_drops(drops),
        "gap_stress_at_10pct_vol": stress,
        "annual_return_capacity": capacity,
        "screen": screen,
        "verdict": screen["verdict"],
        "disclosed_shortfalls": [
            {
                "what": "the routed P&L is a spot return, not a full currency excess return",
                "why": (
                    "the frozen sources are the ECB's reference rates and the BIS's consumer "
                    "prices, and neither carries an interest rate. No rate source was added "
                    "after the freeze"
                ),
                "direction": (
                    "measured, not assumed — see `carry_exposure`. The plausible-sounding chain "
                    "runs the other way for this book: the primary test is strongly and "
                    "systematically long the LOW-inflation currencies, because residualising the "
                    "real signal on the nominal one leaves essentially the relative price level "
                    "with its sign reversed. If inflation carries into rates, the omitted carry "
                    "on this book is negative, so omitting it OVERSTATES the result rather than "
                    "understating it. The first version of this record asserted the opposite "
                    "from the textbook story without checking it against the frozen CPI panel. "
                    "Trailing realised inflation is a proxy for the rate, not the rate, so the "
                    "sign is evidence rather than proof — but it is the only measurable link in "
                    "the argument and it points the wrong way for a rescue"
                ),
            },
            {
                "what": "the CPI series are revised history, not vintages",
                "why": "free vintage data does not cover eight countries back to 1994",
                "direction": (
                    "a revision that arrived after a decision could not have been known, so any "
                    "positive result carries that caveat; the pre-registration says so"
                ),
            },
        ],
        "protected_spans_read": False,
    }


def _screen(
    books: dict[str, Any],
    robustness: dict[str, Any],
    drops: dict[str, float],
    capacity: dict[str, Any],
) -> dict[str, Any]:
    """The frozen conditions, applied as written, then the frozen bands.

    The frozen text carries eleven bullets; one of them is a conjunction (no currency
    over half the gross **and** the sign surviving any single drop), split here into
    two so a record cannot report a conjunction as satisfied when half of it is not.
    Splitting is stricter, never weaker.

    "The gross" in the concentration bullet is the book's gross P&L, which is what
    the word means everywhere else in this record and is exactly the signed sum of
    the per-currency contributions. An earlier version normalised by the sum of
    absolute contributions instead — a quantity used nowhere else — which made the
    condition materially easier to pass, and it passed on it.
    """
    valuation = books["A_valuation"]["summary"]
    control = books["B_nominal_control"]["summary"]
    primary = books["C_residualised"]["summary"]
    blocks = books["C_residualised"]["blocks"]
    positive_blocks = sum(1 for row in blocks if (row["net_sharpe"] or 0) > 0)
    contributions = books["C_residualised"]["per_currency_gross_pnl"]
    gross = sum(float(v) for v in contributions.values())
    largest = max(abs(float(v)) for v in contributions.values()) if contributions else 0.0
    net = primary["net_sharpe"]
    conditions = {
        "book A gross Sharpe > 0": valuation["gross_sharpe"] > 0,
        "C has positive gross and net": primary["gross_sharpe"] > 0 and net > 0,
        "C carries a positive net increment over B": net - control["net_sharpe"] > 0,
        "forward return falls monotonically from the cheap tercile to the dear one": books[
            "C_residualised"
        ]["terciles"]["monotone_cheap_to_dear"],
        "a majority of the temporal blocks are positive": positive_blocks > len(blocks) / 2,
        "no single currency carries more than half of the gross": bool(
            gross > 0 and largest / gross <= 0.5
        ),
        "the sign survives dropping any one of the eight": all(v > 0 for v in drops.values()),
        "removing the best twelve-month window leaves the sign": books["C_residualised"][
            "worst_year"
        ]["sign_survives_removing_the_best_year"],
        f"turnover at or below {prereg.TURNOVER_BOUND:g}": primary[
            "turnover_round_trips_per_year_per_unit_gross"
        ]
        <= prereg.TURNOVER_BOUND,
        "net Sharpe stays positive at "
        + " and ".join(f"{m:g}x" for m in prereg.COST_STRESSES)
        + " cost": all(value > 0 for value in books["C_residualised"]["cost_stress"].values()),
        "the sign is unchanged under the declared robustness anchor": bool(
            np.sign(robustness["C_residualised"]["net_sharpe"]) == np.sign(net)
        ),
        "5% annual net is reachable at a volatility at most 15% whose gap stress survives": bool(
            capacity["0.05"]["reachable"] and capacity["0.05"]["target_vol"] <= 0.15
        ),
    }
    shared = all(conditions.values())
    if shared and net >= prereg.CANDIDATE_NET_SHARPE:
        decision = "candidate"
    elif (
        shared
        and net >= prereg.MARGINAL_NET_SHARPE
        and primary["turnover_round_trips_per_year_per_unit_gross"] <= prereg.TURNOVER_BOUND / 2
    ):
        decision = "marginal"
    else:
        decision = "stop"
    verdict = {
        "candidate": prereg.PREREG["screen"]["status_candidate"],
        "marginal": prereg.PREREG["screen"]["status_marginal"],
        "stop": prereg.PREREG["screen"]["status_stop"],
    }[decision]
    return {
        "shared_conditions": conditions,
        "all_shared_conditions_hold": shared,
        "failing_conditions": sorted(name for name, value in conditions.items() if not value),
        "primary_net_sharpe": net,
        "positive_blocks": positive_blocks,
        "decision": decision,
        "verdict": verdict,
        "decision_grade": False,
        "note": (
            "a development screen on seen data. It cannot make this source confirmed, and a "
            "marginal result returns to Human rather than advancing"
        ),
    }


def main() -> int:
    record = run()
    path = ROOT / RECORD_DIR / "development.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    for name, book in record["books"].items():
        summary = book["summary"]
        print(
            f"{name}: gross {summary['gross_sharpe']:+.3f} net {summary['net_sharpe']:+.3f} "
            f"turnover {summary['turnover_round_trips_per_year_per_unit_gross']:.1f} "
            f"IC {book['ic_at_the_primary_horizon']} "
            f"terciles {book['terciles']['mean_forward_excess_return_cheap_mid_dear']}"
        )
    print("leave-one-out:", record["leave_one_currency_out_net_sharpe"])
    print("failing:", record["screen"]["failing_conditions"])
    print("verdict:", record["verdict"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
