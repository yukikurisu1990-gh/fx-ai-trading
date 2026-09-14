"""Portfolio-level economics of one book, and the pre-registered adjudication.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Every figure is computed from the daily, non-overlapping P&L of the held book,
so annualisation is `sqrt(days_per_year)` on daily returns and no overlapping
window enters a Sharpe ratio. `days_per_year` is **measured** from the
out-of-fold span (trading days per calendar year), not assumed to be 252.

The success unit is the primary book's own net economics. An increment over a
baseline is reported and is never, by itself, a reason to survive.
"""

from __future__ import annotations

import math
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.continuous_portfolio import CASE_A, CASE_B, CASE_C, economic_band
from scripts.research.continuous_portfolio.construction import CURRENCIES

VOL_SCENARIOS: Final[tuple[float, ...]] = (0.08, 0.10, 0.12)

#: A fold shorter than this is reported but does not count toward the share of
#: positive folds: a one-week tail fold would otherwise weigh as much as a
#: half-year one.
MIN_FOLD_TEST_DAYS: Final[int] = 60


def measured_days_per_year(index: pd.DatetimeIndex) -> float:
    span_years = (index.max() - index.min()).days / 365.25
    return float(len(index) / span_years) if span_years > 0 else float("nan")


def _sharpe(daily: pd.Series, days_per_year: float) -> float:
    deviation = float(daily.std(ddof=1))
    if not math.isfinite(deviation) or deviation == 0.0:
        return 0.0
    return float(daily.mean() / deviation * math.sqrt(days_per_year))


def _max_drawdown(daily: pd.Series) -> float:
    equity = daily.cumsum()
    return float((equity - equity.cummax()).min())


def pnl_correlation(first: pd.Series, second: pd.Series) -> float | None:
    """Correlation of two books' daily net P&L on the days both exist."""
    joined = pd.concat([first, second], axis=1, join="inner").dropna()
    if len(joined) < 3 or joined.iloc[:, 0].std() == 0 or joined.iloc[:, 1].std() == 0:
        return None
    return round(float(joined.iloc[:, 0].corr(joined.iloc[:, 1])), 4)


def _finite_round(value: float, digits: int = 4) -> float | None:
    return round(float(value), digits) if math.isfinite(float(value)) else None


def _top_share(net: pd.Series, count: int) -> float | None:
    total = float(net.sum())
    if total <= 0:
        return None
    return round(float(net.sort_values(ascending=False).head(count).sum()) / total, 4)


def summarise(
    daily: pd.DataFrame,
    *,
    days_per_year: float,
    fold_labels: pd.Series,
    regime: pd.Series | None = None,
    vol_target: float | None = None,
) -> dict[str, Any]:
    """Every pre-registered metric for one book."""
    net = daily["net"]
    gross = daily["gross"]
    cost = daily["cost"]
    years = len(daily) / days_per_year
    mean_gross_exposure = float(daily["currency_gross"].mean())

    per_fold = {}
    fold_days = {}
    labels = fold_labels.reindex(daily["decision_day"]).to_numpy()
    for fold in sorted({int(v) for v in labels if np.isfinite(v)}):
        mask = labels == fold
        per_fold[str(fold)] = round(_sharpe(net[mask], days_per_year), 4)
        fold_days[str(fold)] = int(mask.sum())
    counted = [v for k, v in per_fold.items() if fold_days[k] >= MIN_FOLD_TEST_DAYS]

    contributions = {c: float(daily[f"pnl_{c}"].sum()) for c in CURRENCIES if f"pnl_{c}" in daily}
    positive = {c: v for c, v in contributions.items() if v > 0}
    positive_total = sum(positive.values())
    ranked = sorted(contributions, key=lambda c: contributions[c], reverse=True)
    best = ranked[0] if ranked else None
    total_gross = float(gross.sum())
    realized_vol = float(net.std(ddof=1)) * math.sqrt(days_per_year)

    out: dict[str, Any] = {
        "days": int(len(daily)),
        "years": round(years, 3),
        "days_per_year_measured": round(days_per_year, 2),
        #: --- frequencies, kept apart
        "prediction_days": int(len(daily)),
        "predictions_made": int(len(daily)) * len(CURRENCIES),
        "position_update_days": int(daily["traded"].sum()),
        "position_update_share_of_days": round(float(daily["traded"].mean()), 4),
        #: --- turnover
        "currency_one_way_traded_per_year": round(float(daily["one_way_traded"].sum()) / years, 3),
        "turnover_round_trips_per_year": round(
            float(daily["one_way_traded"].sum()) / 2.0 / years, 3
        ),
        "turnover_round_trips_per_year_per_unit_gross": round(
            float(daily["one_way_traded"].sum()) / 2.0 / years / mean_gross_exposure, 3
        )
        if mean_gross_exposure > 0
        else None,
        #: --- exposure / capital utilisation
        "mean_currency_gross": round(mean_gross_exposure, 4),
        "mean_pair_gross_notional": round(float(daily["pair_gross"].mean()), 4),
        "share_of_days_invested": round(float((daily["currency_gross"] > 0).mean()), 4),
        "mean_leverage": round(float(daily["leverage"].mean()), 4),
        "p95_leverage": round(float(daily["leverage"].quantile(0.95)), 4),
        "share_days_at_leverage_cap": round(float(daily["at_leverage_cap"].mean()), 4),
        "mean_uncapped_leverage": _finite_round(daily["uncapped_leverage"].mean()),
        "p95_uncapped_leverage": _finite_round(daily["uncapped_leverage"].quantile(0.95)),
        "realized_vol_over_target": round(realized_vol / vol_target, 4) if vol_target else None,
        "held_max_weight_p99": round(float(daily["held_max_weight"].quantile(0.99)), 4),
        "held_max_weight_max": round(float(daily["held_max_weight"].max()), 4),
        "share_days_held_gross_above_1": round(
            float((daily["held_gross"] > 1.0 + 1e-12).mean()), 4
        ),
        #: --- residual exposure to the dominant factor, measured on the held book
        "mean_factor_abs_cosine": _finite_round(daily["factor_abs_cosine"].mean()),
        "factor_pnl_total": round(float(daily["factor_pnl"].sum()), 6),
        "factor_pnl_share_of_gross": round(float(daily["factor_pnl"].sum()) / total_gross, 4)
        if total_gross > 0
        else None,
        #: --- economics, fractions of capital
        "gross_annual_return": round(float(gross.mean()) * days_per_year, 6),
        "cost_annual_drag": round(float(cost.mean()) * days_per_year, 6),
        "implementation_cost_annual_drag": round(
            float(daily["implementation_cost"].mean()) * days_per_year, 6
        ),
        "cost_per_unit_gross_exposure_bp_per_year": round(
            float(cost.mean()) * days_per_year / mean_gross_exposure * 10_000.0, 3
        )
        if mean_gross_exposure > 0
        else None,
        "net_annual_return": round(float(net.mean()) * days_per_year, 6),
        "realized_annual_vol": round(realized_vol, 6),
        "gross_sharpe": round(_sharpe(gross, days_per_year), 4),
        "net_sharpe": round(_sharpe(net, days_per_year), 4),
        "net_sharpe_at_implementation_cost": round(
            _sharpe(gross - daily["implementation_cost"], days_per_year), 4
        ),
        "max_drawdown": round(_max_drawdown(net), 6),
        #: --- stability
        "per_fold_net_sharpe": per_fold,
        "per_fold_days": fold_days,
        "min_fold_test_days_counted": MIN_FOLD_TEST_DAYS,
        "share_of_folds_positive": round(float(np.mean([v > 0 for v in counted])), 4)
        if counted
        else 0.0,
        "per_currency_gross_pnl": {c: round(v, 6) for c, v in contributions.items()},
        "best_currency": best,
        "best_currency_share_of_positive_pnl": round(contributions[best] / positive_total, 4)
        if best and positive_total > 0
        else None,
        "gross_pnl_without_best_currency": round(total_gross - contributions[best], 6)
        if best
        else None,
        #: a sum-zero one-pair bet survives the single-currency clause, so the
        #: best two are removed together as well
        "gross_pnl_without_best_two_currencies": round(
            total_gross - sum(contributions[c] for c in ranked[:2]), 6
        )
        if len(ranked) >= 2
        else None,
        "gross_pnl_without_usd": round(total_gross - contributions.get("USD", 0.0), 6),
        "usd_share_of_gross_pnl": round(contributions.get("USD", 0.0) / total_gross, 4)
        if total_gross
        else None,
        "jpy_share_of_gross_pnl": round(contributions.get("JPY", 0.0) / total_gross, 4)
        if total_gross
        else None,
        "top_1_day_share_of_net": _top_share(net, 1),
        "top_5_day_share_of_net": _top_share(net, 5),
        "top_10_day_share_of_net": _top_share(net, 10),
        #: the tail-dependence kill: the mean daily net with both 1% tails clipped.
        #: Symmetric fat tails leave it near the mean; profit that lives in a few
        #: outsized up-days does not survive it
        "net_winsorised_1pct_annual": round(
            float(net.clip(net.quantile(0.01), net.quantile(0.99)).mean()) * days_per_year, 6
        ),
        "net_without_top_5_days": round(
            float(net.sum() - net.sort_values(ascending=False).head(5).sum()), 6
        ),
        "mean_raw_to_neutralised_score_corr": round(float(daily["raw_target_corr"].mean()), 4),
    }
    if regime is not None:
        aligned = regime.reindex(daily["decision_day"]).to_numpy()
        out["net_by_regime"] = {
            str(int(state)): round(float(net[aligned == state].sum()), 6)
            for state in sorted({v for v in aligned if np.isfinite(v)})
        }
    out["economic_band"] = economic_band(out["net_sharpe"])
    return out


def vol_scenarios(books: dict[float, dict[str, Any]]) -> dict[str, Any]:
    """The primary construction actually run at each volatility target.

    A rescaled 10% book is not an 8% or 12% book: the leverage cap binds
    differently and the realised volatility need not equal its target. So every
    row is a book that was run, reported as run. Leverage is not an edge and
    nothing here enters the verdict.
    """
    rows = {}
    for target in VOL_SCENARIOS:
        summary = books[target]
        rows[f"vol_{target:g}"] = {
            "vol_target": target,
            "annual_net_return": summary["net_annual_return"],
            "realized_annual_vol": summary["realized_annual_vol"],
            "realized_vol_over_target": summary["realized_vol_over_target"],
            "max_drawdown": summary["max_drawdown"],
            "mean_leverage": summary["mean_leverage"],
            "p95_leverage": summary["p95_leverage"],
            "share_days_at_leverage_cap": summary["share_days_at_leverage_cap"],
            "cost_annual_drag": summary["cost_annual_drag"],
            "net_sharpe": summary["net_sharpe"],
        }
    return rows


def adjudicate(
    primary: dict[str, Any],
    *,
    stressed_1_5: dict[str, Any],
    unfitted_rules: dict[str, dict[str, Any]],
    rules: dict[str, Any],
) -> dict[str, Any]:
    """The pre-registered verdict, every clause evaluated and reported.

    `unfitted_rules` maps `{persistence,reversal}_{5,20,60}d` to that rule's
    `net_sharpe` and the correlation of its daily net P&L with the primary's.

    Two benchmark kills. The C08-shaped 60-day rule is read in **both** signs
    and the primary must beat the better one outright: a ridge may put a
    negative weight on persistence, and the closed family inverted must not
    survive because the positive rule lost money. And at every horizon, a rule
    whose P&L moves with the primary's (correlation at or above the declared
    threshold) that earns at least the primary's Sharpe kills it: the fit added
    nothing to a single unfitted rule it resembles.

    The top-day shares are reported and do not gate: over ~850 days ten
    ordinary days already hold about 26 daily deviations against a total of
    about 52.5 x Sharpe, so a "top ten at most half" clause demands a realised
    Sharpe near 1.0 whatever the tails look like, and "net without the top five
    days" kills about half of fat-tailed books at Sharpe 0.3-0.4. Tail dependence
    is read from the 1%-winsorised mean instead, which symmetric fat tails leave
    alone and a book living on a few outsized up-days does not survive.
    """
    sharpe = primary["net_sharpe"]
    correlations = [
        rule["pnl_correlation"]
        for rule in unfitted_rules.values()
        if rule["pnl_correlation"] is not None
    ]
    turnover_per_gross = primary["turnover_round_trips_per_year_per_unit_gross"] or float("inf")
    unfitted_best = max(
        unfitted_rules["persistence_60d"]["net_sharpe"],
        unfitted_rules["reversal_60d"]["net_sharpe"],
    )
    threshold = rules["unfitted_rule_correlation_kill"]
    resembling = {
        name: rule
        for name, rule in unfitted_rules.items()
        if rule["pnl_correlation"] is not None and rule["pnl_correlation"] >= threshold
    }
    kills = {
        "net_sharpe_not_positive": sharpe <= 0.0,
        "net_return_economically_negligible": sharpe < rules["negligible_net_sharpe"],
        "profit_lives_in_the_extreme_days": primary["net_winsorised_1pct_annual"] <= 0.0,
        "single_currency_carries_the_book": (
            primary["gross_pnl_without_best_currency"] is None
            or primary["gross_pnl_without_best_currency"] <= 0.0
        ),
        "majority_of_folds_negative": primary["share_of_folds_positive"] < 0.5,
        "does_not_beat_the_unfitted_benchmark": sharpe <= unfitted_best,
        "a_resembling_unfitted_rule_does_as_well": any(
            rule["net_sharpe"] >= sharpe for rule in resembling.values()
        ),
        "turnover_unexpectedly_high": turnover_per_gross > rules["max_turnover_per_unit_gross"],
        "leverage_cap_binds_most_days": (
            primary["share_days_at_leverage_cap"] > rules["max_share_days_at_leverage_cap"]
        ),
    }
    breadth = {
        "no_two_currencies_carry_the_book": (
            primary["gross_pnl_without_best_two_currencies"] is not None
            and primary["gross_pnl_without_best_two_currencies"] > 0.0
        ),
        "profitable_without_the_usd_leg": primary["gross_pnl_without_usd"] > 0.0,
    }
    candidate_conditions = {
        "net_sharpe_at_least_0_5": sharpe >= 0.5,
        "majority_of_folds_positive": primary["share_of_folds_positive"] > 0.5,
        "no_currency_above_half_of_positive_pnl": (
            primary["best_currency_share_of_positive_pnl"] is not None
            and primary["best_currency_share_of_positive_pnl"] <= 0.5
        ),
        "survives_1_5x_cost": stressed_1_5["net_sharpe"] > 0.0,
        **breadth,
    }
    marginal_conditions = {
        "net_sharpe_at_least_0_3": sharpe >= 0.3,
        "majority_of_folds_positive": candidate_conditions["majority_of_folds_positive"],
        "no_currency_above_half_of_positive_pnl": candidate_conditions[
            "no_currency_above_half_of_positive_pnl"
        ],
        **breadth,
    }
    if any(kills.values()):
        case = CASE_C
    elif all(candidate_conditions.values()):
        case = CASE_A
    elif all(marginal_conditions.values()):
        case = CASE_B
    else:
        case = CASE_C
    return {
        "case": case,
        "economic_band": primary["economic_band"],
        "unfitted_rules": unfitted_rules,
        "max_pnl_correlation_with_an_unfitted_rule": max(correlations, default=None),
        "resembles_an_unfitted_rule": any(
            value >= rules["unfitted_rule_resemblance_flag"] for value in correlations
        ),
        "top_day_shares_reported_not_gated": {
            "top_1": primary.get("top_1_day_share_of_net"),
            "top_5": primary.get("top_5_day_share_of_net"),
            "top_10": primary.get("top_10_day_share_of_net"),
        },
        "kill_clauses": kills,
        "kills_fired": sorted(name for name, fired in kills.items() if fired),
        "candidate_clauses": candidate_conditions,
        "marginal_clauses": marginal_conditions,
    }


__all__ = [
    "MIN_FOLD_TEST_DAYS",
    "VOL_SCENARIOS",
    "adjudicate",
    "measured_days_per_year",
    "pnl_correlation",
    "summarise",
    "vol_scenarios",
]
