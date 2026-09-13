"""Expanding-window walk-forward, ridge at a declared effective df, and metrics.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Three things here are decisions rather than mechanics, so they are stated.

**The penalty is solved for, not tuned.** The pre-registration declares an
effective degrees-of-freedom target — 4.2 for Track A, 2.4 for Track B's slopes,
3.6 for Track C — and the ridge penalty is whatever produces it inside each
training fold. That is not a hyperparameter search: there is one answer per fold
and no validation result is consulted to pick it. It is also what makes the
capacity budget enforceable rather than aspirational, since the fitted df is the
quantity the budget bounds.

**Purge and embargo are applied to the training side.** The target spans day
`t+1`, so the last training day whose label could overlap the test window is
dropped, and one further day is embargoed. With a one-day horizon that is two
days; the code derives it from the declared horizon rather than hard-coding two.

**Cost is charged on realised turnover.** A position change of `|dw|` summed over
currencies is two position changes per round trip, so the day's cost is
`sum|dw|/2 * roundtrip_bp`. The realised turnover is **measured and reported**,
never assumed — and it is not fed back into the capacity budget, because the
budget was set before the run and re-deriving it from a realised quantity would
be exactly the post-hoc re-gating the pre-registration forbids.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

import numpy as np
import pandas as pd

TRADING_DAYS_PER_YEAR: Final[float] = 252.0
#: Bisection bounds for the ridge penalty. Wide enough that the solved df spans
#: the whole range from `p` to nearly zero for any standardised design matrix.
PENALTY_BOUNDS: Final[tuple[float, float]] = (1e-10, 1e10)
PENALTY_ITERATIONS: Final[int] = 200


class WalkForwardError(RuntimeError):
    """Raised when a fold cannot be formed as the architecture declares."""


@dataclass(frozen=True, slots=True)
class Fold:
    index: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    n_train_days: int
    n_test_days: int


def make_folds(
    days: pd.DatetimeIndex,
    *,
    initial_train_years: float,
    step_years: float,
    horizon_days: int,
    embargo_days: int = 1,
) -> list[Fold]:
    """Expanding-window folds with the training side purged and embargoed."""
    if len(days) == 0:
        raise WalkForwardError("no days")
    per_year = len(days) / ((days[-1] - days[0]).days / 365.25)
    initial = int(round(initial_train_years * per_year))
    step = int(round(step_years * per_year))
    if initial <= 0 or step <= 0:
        raise WalkForwardError("the fold geometry is empty")
    gap = horizon_days + embargo_days
    folds: list[Fold] = []
    cursor = initial
    while cursor < len(days):
        stop = min(cursor + step, len(days))
        train_stop = cursor - gap
        if train_stop <= 0:
            raise WalkForwardError("the purge consumes the whole training window")
        folds.append(
            Fold(
                index=len(folds),
                train_start=days[0],
                train_end=days[train_stop - 1],
                test_start=days[cursor],
                test_end=days[stop - 1],
                n_train_days=train_stop,
                n_test_days=stop - cursor,
            )
        )
        cursor = stop
    return folds


def solve_penalty(design: np.ndarray, target_df: float) -> tuple[float, float]:
    """The ridge penalty whose hat-matrix trace equals the declared df.

    `df(lambda) = sum d_i^2 / (d_i^2 + lambda)` over the design matrix's singular
    values, which is strictly decreasing in `lambda`, so a bisection is exact to
    machine tolerance and needs no starting guess.
    """
    singular = np.linalg.svd(design, compute_uv=False)
    squared = singular**2
    if target_df >= len(squared):
        return 0.0, float(len(squared))

    def degrees(penalty: float) -> float:
        return float(np.sum(squared / (squared + penalty)))

    low, high = PENALTY_BOUNDS
    for _ in range(PENALTY_ITERATIONS):
        middle = np.sqrt(low * high)
        if degrees(middle) > target_df:
            low = middle
        else:
            high = middle
    penalty = float(np.sqrt(low * high))
    return penalty, degrees(penalty)


def fit_ridge(
    design: np.ndarray, target: np.ndarray, target_df: float
) -> tuple[np.ndarray, float, float]:
    """Centred ridge at the declared effective df. Returns (beta, penalty, df)."""
    penalty, achieved = solve_penalty(design, target_df)
    gram = design.T @ design + penalty * np.eye(design.shape[1])
    beta = np.linalg.solve(gram, design.T @ target)
    return beta, penalty, achieved


def standardise(train: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Mean and scale from the training fold only, applied forward unchanged."""
    centre = train.mean(axis=0)
    scale = train.std(axis=0, ddof=0)
    scale[scale == 0.0] = 1.0
    return centre, scale


def weights_from_scores(scores: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectionally demeaned scores, normalised to one unit of gross exposure."""
    demeaned = scores.sub(scores.mean(axis=1), axis=0)
    gross = demeaned.abs().sum(axis=1).replace(0.0, np.nan)
    return demeaned.div(gross, axis=0).fillna(0.0)


def top_bottom_weights(scores: pd.DataFrame, k: int = 2) -> pd.DataFrame:
    """Long the top `k`, short the bottom `k`, equal weight, one unit of gross."""
    ranks = scores.rank(axis=1, method="first")
    width = scores.shape[1]
    longs = (ranks > width - k).astype(float)
    shorts = (ranks <= k).astype(float)
    raw = longs - shorts
    return raw / (2.0 * k)


def evaluate(
    weights: pd.DataFrame,
    forward_return: pd.DataFrame,
    *,
    roundtrip_bp: float,
    cost_multiple: float = 1.0,
) -> dict[str, Any]:
    """Net and gross daily series for a weight book, with cost on realised turnover."""
    aligned = weights.reindex(forward_return.index).fillna(0.0)
    gross_daily = (aligned * forward_return).sum(axis=1) * 10_000.0
    change = aligned.diff()
    change.iloc[0] = aligned.iloc[0]
    turnover = change.abs().sum(axis=1) / 2.0
    cost_daily = turnover * roundtrip_bp * cost_multiple
    net_daily = gross_daily - cost_daily
    return {
        "gross_daily_bp": gross_daily,
        "net_daily_bp": net_daily,
        "cost_daily_bp": cost_daily,
        "turnover_daily": turnover,
        "weights": aligned,
    }


def _information_ratio(daily_bp: pd.Series) -> float:
    deviation = daily_bp.std(ddof=1)
    if not np.isfinite(deviation) or deviation == 0.0:
        return 0.0
    return float(daily_bp.mean() / deviation * np.sqrt(TRADING_DAYS_PER_YEAR))


def summarise(
    series: dict[str, Any],
    forward_return: pd.DataFrame,
    *,
    fold_of: pd.Series,
    regime: pd.Series | None = None,
) -> dict[str, Any]:
    """Every pre-registered metric, computed once."""
    net = series["net_daily_bp"]
    gross = series["gross_daily_bp"]
    weights = series["weights"]
    contribution = (weights * forward_return).sum(axis=0) * 10_000.0
    ordered = net.sort_values(ascending=False)
    total = net.sum()
    equity = net.cumsum()
    drawdown = (equity - equity.cummax()).min()
    per_fold = {
        int(fold): _information_ratio(net[fold_of == fold])
        for fold in sorted(fold_of.dropna().unique())
    }
    out: dict[str, Any] = {
        "days": int(len(net)),
        "net_annualised_ir": round(_information_ratio(net), 4),
        "gross_annualised_ir": round(_information_ratio(gross), 4),
        "net_annualised_bp": round(float(net.mean() * TRADING_DAYS_PER_YEAR), 2),
        "gross_annualised_bp": round(float(gross.mean() * TRADING_DAYS_PER_YEAR), 2),
        "cost_annualised_bp": round(
            float(series["cost_daily_bp"].mean() * TRADING_DAYS_PER_YEAR), 2
        ),
        "annualised_turnover": round(
            float(series["turnover_daily"].mean() * TRADING_DAYS_PER_YEAR), 2
        ),
        "per_fold_net_ir": {str(k): round(v, 4) for k, v in per_fold.items()},
        "share_of_folds_positive": round(
            float(np.mean([v > 0 for v in per_fold.values()])) if per_fold else 0.0, 4
        ),
        "per_currency_net_bp": {
            currency: round(float(value), 2) for currency, value in contribution.items()
        },
        "positive_currencies": int((contribution > 0).sum()),
        "top_ten_day_share_of_net": (
            round(float(ordered.head(10).sum() / total), 4) if total > 0 else None
        ),
        "maximum_drawdown_bp": round(float(drawdown), 2),
    }
    if regime is not None:
        aligned = regime.reindex(net.index)
        out["per_regime_net_bp"] = {
            str(state): round(float(net[aligned == state].sum()), 2)
            for state in sorted(aligned.dropna().unique())
        }
    return out


__all__ = [
    "PENALTY_BOUNDS",
    "TRADING_DAYS_PER_YEAR",
    "Fold",
    "WalkForwardError",
    "evaluate",
    "fit_ridge",
    "make_folds",
    "solve_penalty",
    "standardise",
    "summarise",
    "top_bottom_weights",
    "weights_from_scores",
]
