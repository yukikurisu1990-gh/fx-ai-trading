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
  and not a full currency excess return. Over this span the omitted carry is
  unlikely to be neutral for a valuation book — a currency cheap in real terms has
  usually inflated faster and tends to carry a higher rate — so the omission most
  likely understates a valuation book's return. It is reported, not modelled, and
  no rate source was added after the freeze to repair it.
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


def _lagged_log_cpi(cpi: pd.DataFrame, days: pd.DatetimeIndex) -> pd.DataFrame:
    """Log CPI as it could have been known: month M's index only from the end of M+lag.

    Quarterly publishers repeat the quarter's value, so the carry-forward is already
    in the source and the step is left unsmoothed, as the pre-registration declares.
    """
    lag = prereg.CPI_PUBLICATION_LAG_MONTHS
    periods = pd.PeriodIndex(cpi.index, freq="M")
    logged = pd.DataFrame(np.log(cpi.to_numpy(dtype=float)), index=periods, columns=cpi.columns)
    wanted = pd.PeriodIndex(days, freq="M") - lag
    missing = wanted.difference(logged.index)
    if len(missing):  # pragma: no cover - the request covers the span with room to spare
        raise RuntimeError(f"CPI missing for {list(missing)[:3]}")
    out = logged.loc[wanted]
    out.index = days
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
    fx: pd.DataFrame, cpi: pd.DataFrame, days: pd.DatetimeIndex, *, anchor=_expanding_anchor
) -> dict[str, pd.DataFrame]:
    """The three pre-registered books, on the monthly decision calendar.

    `n_c` is the log euro value of one unit of `c`; the ECB quotes units of `c` per
    euro, so it is the negative of the log rate and the euro's own value is zero.
    """
    nominal = _demean(-np.log(fx.loc[days].astype(float)))
    prices = _demean(_lagged_log_cpi(cpi, days))
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


def _turnover_cost(result: dict[str, Any]) -> dict[str, Any]:
    daily = result["daily"]
    net = daily["net"].to_numpy(dtype=float)
    gross = daily["gross"].to_numpy(dtype=float)
    annual_gross = float(np.mean(gross) * 252.0)
    annual_cost = float(daily["cost"].mean() * 252.0)
    #: how much of the turnover is the signal moving, and how much is the targeter
    decisions = daily["traded"].sum()
    return {
        "gross_t_stat": round(float(np.mean(gross) / np.std(gross, ddof=0) * np.sqrt(len(net))), 3),
        "net_t_stat": round(float(np.mean(net) / np.std(net, ddof=0) * np.sqrt(len(net))), 3),
        "break_even_cost_multiple": round(annual_gross / annual_cost, 3)
        if annual_cost > 0
        else None,
        "faithful_annual_implementation_cost": round(
            float(daily["implementation_cost"].mean() * 252.0), 5
        ),
        "days_traded": int(decisions),
        "trades_per_year": round(float(decisions) / len(daily) * 252.0, 2),
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
        signals = _build_on(fx[list(kept)], cpi[list(kept)], kept_days)
        mu = daily_mu(signals["C_residualised"], pd.DatetimeIndex(kept_excess.index))
        result = portfolio.run_book(BOOK, mu, kept_excess, universe=kept)
        drops[f"without_{dropped}"] = fast._summary(result)["net_sharpe"]
    return drops


def _build_on(
    fx: pd.DataFrame, cpi: pd.DataFrame, days: pd.DatetimeIndex
) -> dict[str, pd.DataFrame]:
    """`build_signals` on a subset: the cross-sectional demeaning follows the subset."""
    nominal = _demean(-np.log(fx.loc[days].astype(float)))
    prices = _demean(_lagged_log_cpi(cpi, days))
    real = nominal + prices
    valuation = fast._z(-(real - _expanding_anchor(real)))
    control = fast._z(-(nominal - _expanding_anchor(nominal)))
    return {
        "A_valuation": valuation,
        "B_nominal_control": control,
        "C_residualised": fast._residualise(valuation, control),
    }


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
        books[name] = {
            "summary": fast._summary(result),
            "extra": _turnover_cost(result),
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
        "robustness_median_anchor": robustness,
        "leave_one_currency_out_net_sharpe": drops,
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
                    "a currency cheap in real terms has usually inflated faster and tends to "
                    "carry a higher rate, so omitting carry most likely understates this book"
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
    """The eleven frozen conditions, applied as written, then the frozen bands."""
    valuation = books["A_valuation"]["summary"]
    control = books["B_nominal_control"]["summary"]
    primary = books["C_residualised"]["summary"]
    blocks = books["C_residualised"]["blocks"]
    positive_blocks = sum(1 for row in blocks if (row["net_sharpe"] or 0) > 0)
    contributions = books["C_residualised"]["per_currency_gross_pnl"]
    total = sum(abs(float(v)) for v in contributions.values())
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
            total > 0 and largest / total <= 0.5
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
