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
) -> dict[str, Any]:
    """Every pre-registered metric for one book."""
    net = daily["net"]
    gross = daily["gross"]
    cost = daily["cost"]
    years = len(daily) / days_per_year
    mean_gross_exposure = float(daily["currency_gross"].mean())

    per_fold = {}
    labels = fold_labels.reindex(daily["decision_day"]).to_numpy()
    for fold in sorted({int(v) for v in labels if np.isfinite(v)}):
        mask = labels == fold
        per_fold[str(fold)] = round(_sharpe(net[mask], days_per_year), 4)

    contributions = {c: float(daily[f"pnl_{c}"].sum()) for c in CURRENCIES if f"pnl_{c}" in daily}
    positive = {c: v for c, v in contributions.items() if v > 0}
    positive_total = sum(positive.values())
    best = max(contributions, key=lambda c: contributions[c]) if contributions else None
    total_gross = float(gross.sum())

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
        "realized_annual_vol": round(float(net.std(ddof=1)) * math.sqrt(days_per_year), 6),
        "gross_sharpe": round(_sharpe(gross, days_per_year), 4),
        "net_sharpe": round(_sharpe(net, days_per_year), 4),
        "net_sharpe_at_implementation_cost": round(
            _sharpe(gross - daily["implementation_cost"], days_per_year), 4
        ),
        "max_drawdown": round(_max_drawdown(net), 6),
        #: --- stability
        "per_fold_net_sharpe": per_fold,
        "share_of_folds_positive": round(
            float(np.mean([v > 0 for v in per_fold.values()])) if per_fold else 0.0, 4
        ),
        "per_currency_gross_pnl": {c: round(v, 6) for c, v in contributions.items()},
        "best_currency": best,
        "best_currency_share_of_positive_pnl": round(contributions[best] / positive_total, 4)
        if best and positive_total > 0
        else None,
        "gross_pnl_without_best_currency": round(total_gross - contributions[best], 6)
        if best
        else None,
        "usd_share_of_gross_pnl": round(contributions.get("USD", 0.0) / total_gross, 4)
        if total_gross
        else None,
        "jpy_share_of_gross_pnl": round(contributions.get("JPY", 0.0) / total_gross, 4)
        if total_gross
        else None,
        "top_1_day_share_of_net": _top_share(net, 1),
        "top_5_day_share_of_net": _top_share(net, 5),
        "top_10_day_share_of_net": _top_share(net, 10),
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


def vol_scenarios(summary: dict[str, Any], base_vol_target: float) -> dict[str, Any]:
    """Constant rescaling of the primary book to other volatility targets.

    Return, volatility, drawdown, leverage and cost all scale by the same factor;
    Sharpe does not. Leverage is not an edge and nothing here can change a sign.
    """
    rows = {}
    for target in VOL_SCENARIOS:
        factor = target / base_vol_target
        rows[f"vol_{target:g}"] = {
            "scale_vs_primary": round(factor, 4),
            "annual_net_return": round(summary["net_annual_return"] * factor, 6),
            "realized_annual_vol": round(summary["realized_annual_vol"] * factor, 6),
            "max_drawdown": round(summary["max_drawdown"] * factor, 6),
            "mean_leverage": round(summary["mean_leverage"] * factor, 4),
            "p95_leverage": round(summary["p95_leverage"] * factor, 4),
            "net_sharpe": summary["net_sharpe"],
        }
    return rows


def adjudicate(
    primary: dict[str, Any],
    *,
    stressed_1_5: dict[str, Any],
    baseline_momentum: dict[str, Any],
    rules: dict[str, Any],
) -> dict[str, Any]:
    """The pre-registered verdict, every clause evaluated and reported."""
    sharpe = primary["net_sharpe"]
    turnover_per_gross = primary["turnover_round_trips_per_year_per_unit_gross"] or float("inf")
    kills = {
        "net_sharpe_not_positive": sharpe <= 0.0,
        "net_return_economically_negligible": sharpe < rules["negligible_net_sharpe"],
        "profit_vanishes_without_top_5_days": primary["net_without_top_5_days"] <= 0.0,
        "single_currency_carries_the_book": (
            primary["gross_pnl_without_best_currency"] is not None
            and primary["gross_pnl_without_best_currency"] <= 0.0
        ),
        "majority_of_folds_negative": primary["share_of_folds_positive"] < 0.5,
        "does_not_beat_the_unfitted_benchmark": sharpe <= baseline_momentum["net_sharpe"],
        "turnover_unexpectedly_high": turnover_per_gross > rules["max_turnover_per_unit_gross"],
        "leverage_impractical": primary["mean_leverage"] > rules["max_mean_leverage"],
    }
    candidate_conditions = {
        "net_sharpe_at_least_0_5": sharpe >= 0.5,
        "majority_of_folds_positive": primary["share_of_folds_positive"] > 0.5,
        "no_currency_above_half_of_positive_pnl": (
            primary["best_currency_share_of_positive_pnl"] is not None
            and primary["best_currency_share_of_positive_pnl"] <= 0.5
        ),
        "top_10_days_at_most_half_of_net": (
            primary["top_10_day_share_of_net"] is not None
            and primary["top_10_day_share_of_net"] <= 0.5
        ),
        "survives_1_5x_cost": stressed_1_5["net_sharpe"] > 0.0,
    }
    marginal_conditions = {
        "net_sharpe_at_least_0_3": sharpe >= 0.3,
        "majority_of_folds_positive": candidate_conditions["majority_of_folds_positive"],
        "no_currency_above_half_of_positive_pnl": candidate_conditions[
            "no_currency_above_half_of_positive_pnl"
        ],
        "top_10_days_at_most_half_of_net": candidate_conditions["top_10_days_at_most_half_of_net"],
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
        "kill_clauses": kills,
        "kills_fired": sorted(name for name, fired in kills.items() if fired),
        "candidate_clauses": candidate_conditions,
        "marginal_clauses": marginal_conditions,
    }


__all__ = [
    "VOL_SCENARIOS",
    "adjudicate",
    "measured_days_per_year",
    "summarise",
    "vol_scenarios",
]
