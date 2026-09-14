"""The currency expected-return model: pooled ridge, walk-forward, low capacity.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

One model class, one feature set, one horizon — all frozen by the
pre-registration. The model's job is to supply a continuous expected relative
return per currency per day; whether the architecture turns that into money is
the portfolio's question, not the model's.

Target
------

The forward **5-day** cumulative currency excess return. Five days is the
architecture's own horizon rather than a swept one: the band-rebalanced book
holds targets whose information must persist for days to be worth the band's
lag, and a one-day label would train the model on the noisiest possible
quantity for a position held far longer than a day. P&L is still earned and
measured **daily** on the held book, so no overlapping return enters a Sharpe
ratio — only the training label overlaps, and the fold purge removes it.

Leakage controls, each enforced here
------------------------------------

* Features are the causal, closed-bar, cross-sectionally z-scored columns of
  `scripts.research.model_learning.features`, whose truncation invariance is
  tested in that package.
* Training rows of a fold end `horizon + embargo` days before its test window,
  so no training label overlaps a test-period return.
* Standardisation and the ridge penalty are fitted on the training rows only.
* A test row is predicted by exactly one fold's model, trained strictly earlier.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.model_learning import walkforward as wf

#: Seven features in five abstract families. No indicator zoo, no window sweep.
FEATURES: Final[tuple[str, ...]] = (
    #: multi-horizon currency-relative returns
    "currency_excess_return_5d_z",
    "currency_excess_return_20d_z",
    "currency_excess_return_60d_z",
    #: normalized trend persistence
    "trend_age_d1_normalised",
    #: volatility state
    "currency_realised_vol_20d_z",
    #: dispersion
    "currency_dispersion_share_20d_z",
    #: correlation / factor state (leave-one-out beta to the common factor)
    "currency_beta_to_common_factor_60d",
)

HORIZON_DAYS: Final[int] = 5
EMBARGO_DAYS: Final[int] = 1

#: Effective degrees of freedom the ridge penalty is solved to inside each fold.
#: A declared capacity, not a tuned hyperparameter: seven coefficients shrunk to
#: three effective ones.
TARGET_EFFECTIVE_DF: Final[float] = 3.0


def forward_target(excess: pd.DataFrame, horizon: int = HORIZON_DAYS) -> pd.DataFrame:
    """`y[t] = sum_{k=1..h} excess[t+k]`. NaN where the window runs off the corpus."""
    shifted = [excess.shift(-k) for k in range(1, horizon + 1)]
    total = sum(shifted[1:], shifted[0])
    valid = excess.notna().shift(-horizon).fillna(False).astype(bool)
    return total.where(valid)


def feature_rows(frames: dict[str, pd.DataFrame], days: pd.DatetimeIndex) -> pd.DataFrame:
    """Tidy `(day, currency)` rows of the pre-registered features."""
    pieces = [frames[name].reindex(days).stack(future_stack=True).rename(name) for name in FEATURES]
    tidy = pd.concat(pieces, axis=1)
    tidy.index.names = ["day", "currency"]
    return tidy


def usable_days(frames: dict[str, pd.DataFrame], excess: pd.DataFrame) -> pd.DatetimeIndex:
    """Days on which every feature exists for every currency."""
    complete = pd.Series(True, index=excess.index)
    for name in FEATURES:
        complete &= frames[name].reindex(excess.index).notna().all(axis=1)
    return excess.index[complete.to_numpy()]


def walk_forward(
    frames: dict[str, pd.DataFrame],
    excess: pd.DataFrame,
    *,
    initial_train_years: float,
    step_years: float,
    target_df: float = TARGET_EFFECTIVE_DF,
) -> dict[str, Any]:
    """Out-of-fold expected returns for every test day, plus per-fold diagnostics."""
    days = usable_days(frames, excess)
    folds = wf.make_folds(
        days,
        initial_train_years=initial_train_years,
        step_years=step_years,
        horizon_days=HORIZON_DAYS,
        embargo_days=EMBARGO_DAYS,
    )
    rows = feature_rows(frames, days)
    target = forward_target(excess).reindex(days).stack(future_stack=True).rename("y")
    target.index.names = ["day", "currency"]
    labelled = rows.join(target)
    day_level = rows.index.get_level_values("day")
    names = list(FEATURES)

    predictions: list[pd.Series] = []
    diagnostics: list[dict[str, Any]] = []
    for fold in folds:
        train = labelled[(labelled.index.get_level_values("day") <= fold.train_end)].dropna()
        test = rows[(day_level >= fold.test_start) & (day_level <= fold.test_end)]
        if train.empty or test.empty:
            continue
        centre, scale = wf.standardise(train[names].to_numpy())
        design = (train[names].to_numpy() - centre) / scale
        beta, penalty, achieved = wf.fit_ridge(design, train["y"].to_numpy(), target_df)
        scored = ((test[names].to_numpy() - centre) / scale) @ beta
        predictions.append(pd.Series(scored, index=test.index))
        diagnostics.append(
            {
                "fold": fold.index,
                "train_end": str(fold.train_end.date()),
                "test_start": str(fold.test_start.date()),
                "test_end": str(fold.test_end.date()),
                "train_rows": int(len(train)),
                "test_days": int(fold.n_test_days),
                "penalty": float(penalty),
                "effective_df": round(float(achieved), 4),
                "coefficients": {
                    name: round(float(value), 8) for name, value in zip(names, beta, strict=True)
                },
            }
        )
    mu = pd.concat(predictions).unstack("currency").sort_index()
    return {"mu": mu, "folds": folds, "fold_diagnostics": diagnostics, "usable_days": days}


#: The horizons of the unfitted rules, each run in both signs.
UNFITTED_HORIZONS: Final[tuple[int, ...]] = (5, 20, 60)


def unfitted_momentum(
    frames: dict[str, pd.DataFrame], days: pd.DatetimeIndex, horizon: int = 60
) -> pd.DataFrame:
    """An unfitted expected-return proxy: one excess-return z-score, as is.

    The 60-day one is Baseline 1 (C08-shaped); 5 and 20 days are the same rule at
    the model's other two return horizons.
    """
    return frames[f"currency_excess_return_{horizon}d_z"].reindex(days)


def unfitted_rules(
    frames: dict[str, pd.DataFrame], days: pd.DatetimeIndex, currencies: list[str]
) -> dict[str, pd.DataFrame]:
    """Every unfitted rule's expected-return proxy: `{persistence,reversal}_{h}d`.

    Reversal is exactly the negated persistence proxy at the same horizon, so the
    two books hold mirror positions.
    """
    rules = {}
    for horizon in UNFITTED_HORIZONS:
        proxy = unfitted_momentum(frames, days, horizon)[currencies]
        rules[f"persistence_{horizon}d"] = proxy
        rules[f"reversal_{horizon}d"] = -proxy
    return rules


def fold_of(days: pd.DatetimeIndex, folds: list[wf.Fold]) -> pd.Series:
    labels = pd.Series(np.nan, index=days)
    for fold in folds:
        labels[(days >= fold.test_start) & (days <= fold.test_end)] = fold.index
    return labels


__all__ = [
    "EMBARGO_DAYS",
    "FEATURES",
    "HORIZON_DAYS",
    "TARGET_EFFECTIVE_DF",
    "UNFITTED_HORIZONS",
    "feature_rows",
    "fold_of",
    "forward_target",
    "unfitted_momentum",
    "unfitted_rules",
    "usable_days",
    "walk_forward",
]
