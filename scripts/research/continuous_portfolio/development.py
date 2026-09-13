"""Track 1's seen-data development run: one model, one primary book, declared checks.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

The pre-registration is checked before a byte is read. The corpus arrives only
through the three guarded seen-span routes. Every book shares one set of
out-of-fold expected returns, so baselines and diagnostics differ from the
primary in exactly the choice they declare and in nothing fitted.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, replace
from typing import Any, Final

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

from scripts.research.continuous_portfolio import construction, evaluation, model
from scripts.research.continuous_portfolio import prereg as prereg_module
from scripts.research.model_learning import SEEN_SPANS, assert_not_protected
from scripts.research.model_learning import corpus as corpus_module
from scripts.research.model_learning import features as feature_module

RATES_PATH: Final[str] = "artifacts/track_a_scratch/economic_edge/policy_rates_daily.parquet"


def _dispersion_and_threshold(excess: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    dispersion = excess.std(axis=1, ddof=0).rolling(20, min_periods=20).mean()
    threshold = dispersion.expanding(min_periods=60).median().shift(1)
    return dispersion, threshold


def _regime(excess: pd.DataFrame) -> pd.Series:
    """Past-only dispersion regime: 20-day dispersion above its expanding median."""
    dispersion, threshold = _dispersion_and_threshold(excess)
    return (dispersion > threshold).astype(float).where(threshold.notna())


def _rank_ic(scores: pd.DataFrame, realised: pd.DataFrame, horizon: int) -> dict[str, Any]:
    """Daily cross-sectional rank IC; the t statistic uses every `horizon`-th day.

    A `horizon`-day realised return overlaps its neighbours, so the naive t over
    all days overstates by about `sqrt(horizon)`. The mean uses every day.
    """
    values = []
    for day in scores.index:
        if day not in realised.index:
            continue
        a = scores.loc[day].to_numpy(dtype=float)
        b = realised.loc[day].to_numpy(dtype=float)
        if np.all(np.isfinite(a)) and np.all(np.isfinite(b)) and np.std(a) > 0:
            values.append(float(scipy_stats.spearmanr(a, b).statistic))
    series = np.array(values)
    sparse = series[::horizon]
    return {
        "days": int(len(series)),
        "horizon_days": horizon,
        "mean": round(float(series.mean()), 5) if len(series) else None,
        "t_non_overlapping": round(
            float(sparse.mean() / sparse.std(ddof=1) * np.sqrt(len(sparse))), 3
        )
        if len(sparse) > 2
        else None,
        "note": "diagnostic only; the verdict reads portfolio net economics",
    }


#: Amendment A-1 of the economic-edge study: BIS's euro-area series is the ECB
#: main refinancing rate before this date and the deposit facility rate from it.
EUR_DEFINITION_BREAK: Final[str] = "2024-09-18"
#: MRO minus deposit facility over the corpus span before the break, as measured
#: in `scripts/research/economic_edge/rates.py` (exactly +0.500).
EUR_MRO_MINUS_DEPOSIT_FACILITY_PCT: Final[float] = 0.50


def _policy_rates(frame: pd.DataFrame) -> pd.DataFrame:
    """Wide daily policy rates with EUR on the deposit facility throughout."""
    rates = frame.pivot(index="date", columns="currency", values="rate_pct").sort_index()
    rates.index = rates.index.tz_localize(None).normalize()
    before = rates.index < pd.Timestamp(EUR_DEFINITION_BREAK)
    rates.loc[before, "EUR"] = rates.loc[before, "EUR"] - EUR_MRO_MINUS_DEPOSIT_FACILITY_PCT
    return rates


def _carry_accrual(daily: pd.DataFrame, start: str, end: str) -> dict[str, Any]:
    """Policy-rate carry the held exposure would have earned, as a diagnostic.

    Reads a public BIS policy-rate series (not FX data) filtered to the corpus
    span; the parquet is one row group, so rows outside the span are decoded
    and discarded. No FX archive row and no protected FX span is touched.
    """
    assert_not_protected(start, end)
    frame = pd.read_parquet(
        RATES_PATH,
        filters=[
            ("date", ">=", pd.Timestamp(start, tz="UTC")),
            ("date", "<=", pd.Timestamp(end, tz="UTC")),
        ],
    )
    rates = _policy_rates(frame)
    decision_days = pd.DatetimeIndex(daily["decision_day"])
    aligned = rates.reindex(rates.index.union(decision_days)).ffill().reindex(decision_days)
    pnl_days = pd.DatetimeIndex(daily.index)
    gap_days = (pnl_days - decision_days).days.to_numpy()
    accrual = np.zeros(len(daily))
    for c in construction.CURRENCIES:
        accrual += daily[f"x_{c}"].to_numpy() * aligned[c].to_numpy() / 100.0 * gap_days / 365.0
    total = float(np.nansum(accrual))
    years = len(daily) / evaluation.measured_days_per_year(pnl_days)
    return {
        "annual_carry_accrual": round(total / years, 6),
        "note": (
            "excluded from P&L; broker financing spreads are not modelled. A large value "
            "means the book's result depends on carry the spot P&L does not contain"
        ),
    }


def run() -> dict[str, Any]:
    frozen = prereg_module.assert_frozen()
    first = min(block["start"] for block in SEEN_SPANS.values())
    last = max(block["end"] for block in SEEN_SPANS.values())
    assert_not_protected(first, last)

    panel = corpus_module.currency_panel()
    excess = panel["currency_excess_return"][list(construction.CURRENCIES)]
    frames = feature_module.build(panel)
    usable = model.usable_days(frames, excess)
    first_usable = excess.index.get_loc(usable[0])
    if not usable.equals(excess.index[first_usable : first_usable + len(usable)]):
        raise ValueError("usable days are not contiguous; refusing before any model is fitted")

    fitted = model.walk_forward(
        frames,
        excess,
        initial_train_years=prereg_module.WALK_FORWARD["initial_train_years"],
        step_years=prereg_module.WALK_FORWARD["step_years"],
    )
    mu = fitted["mu"][list(construction.CURRENCIES)]
    oos_days = mu.index
    days_per_year = evaluation.measured_days_per_year(oos_days)
    labels = model.fold_of(oos_days, fitted["folds"])
    regime = _regime(excess)

    def book(config: construction.BookConfig, expected: pd.DataFrame) -> dict[str, Any]:
        result = construction.run_book(config, expected, excess, days_per_year)
        return {
            "config": asdict(config),
            "summary": evaluation.summarise(
                result["daily"],
                days_per_year=days_per_year,
                fold_labels=labels,
                regime=regime,
                vol_target=config.vol_target,
            ),
            "daily": result["daily"],
        }

    primary = book(prereg_module.PRIMARY, mu)
    unfitted = {}
    for horizon in model.UNFITTED_HORIZONS:
        proxy = model.unfitted_momentum(frames, oos_days, horizon)[list(construction.CURRENCIES)]
        for sign, label in ((1.0, "persistence"), (-1.0, "reversal")):
            name = f"{label}_{horizon}d"
            unfitted[name] = book(
                replace(prereg_module.PRIMARY, name=f"unfitted_{name}"), sign * proxy
            )
    baseline_2 = book(prereg_module.BASELINE_2, mu)
    diagnostics = {config.name: book(config, mu) for config in prereg_module.DIAGNOSTICS}

    verdict = evaluation.adjudicate(
        primary["summary"],
        stressed_1_5=diagnostics["diag_cost_1_5x"]["summary"],
        unfitted_rules={
            name: {
                "net_sharpe": entry["summary"]["net_sharpe"],
                "pnl_correlation": evaluation.pnl_correlation(
                    primary["daily"]["net"], entry["daily"]["net"]
                ),
            }
            for name, entry in unfitted.items()
        },
        rules=prereg_module.ADJUDICATION_RULES,
    )
    scenario_books = {
        0.08: diagnostics["diag_vol_target_0_08"]["summary"],
        0.10: primary["summary"],
        0.12: diagnostics["diag_vol_target_0_12"]["summary"],
    }

    forward_1d = excess.shift(-1)
    forward_5d = model.forward_target(excess)
    neutral_scores = pd.DataFrame(
        [
            construction.neutralize(
                construction.vol_normalized_scores(
                    mu.loc[day].to_numpy(dtype=float),
                    np.std(excess.loc[:day].to_numpy()[-60:], axis=0),
                ),
                construction.leading_factor(excess.loc[:day].to_numpy()[-120:]),
            )
            for day in oos_days
        ],
        index=oos_days,
        columns=list(construction.CURRENCIES),
    )

    def strip(entry: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in entry.items() if key != "daily"}

    return {
        "track": "TRACK_1_CONTINUOUS_CURRENCY_PORTFOLIO",
        "preregistration_frozen_hash": frozen,
        "run_date_utc": dt.datetime.now(dt.UTC).date().isoformat(),
        "corpus": corpus_module.provenance(panel),
        "oos": {
            "first_decision_day": str(oos_days.min().date()),
            "last_decision_day": str(oos_days.max().date()),
            "decision_days": int(len(oos_days)),
            "days_per_year_measured": round(days_per_year, 3),
        },
        "folds": fitted["fold_diagnostics"],
        "primary": strip(primary),
        "baseline_0_cash": {"summary": {"net_sharpe": 0.0, "net_annual_return": 0.0}},
        "baseline_1_unfitted_persistence": strip(unfitted["persistence_60d"]),
        "baseline_1_unfitted_reversal": strip(unfitted["reversal_60d"]),
        "unfitted_rules": {name: strip(entry) for name, entry in unfitted.items()},
        "baseline_2_linear_no_bundle": strip(baseline_2),
        "diagnostics": {name: strip(entry) for name, entry in diagnostics.items()},
        "vol_scenarios": evaluation.vol_scenarios(scenario_books),
        "information_diagnostics": {
            "raw_mu_rank_ic_1d": _rank_ic(mu, forward_1d, 1),
            "raw_mu_rank_ic_5d": _rank_ic(mu, forward_5d, model.HORIZON_DAYS),
            "neutralised_score_rank_ic_1d": _rank_ic(neutral_scores, forward_1d, 1),
            "neutralised_score_rank_ic_5d": _rank_ic(
                neutral_scores, forward_5d, model.HORIZON_DAYS
            ),
        },
        "carry_diagnostic_primary": _carry_accrual(primary["daily"], first, last),
        "adjudication": verdict,
        "protected_spans_read": False,
        "broker_access": False,
        "strongest_status_reachable": "CONTINUOUS_CURRENCY_PORTFOLIO_DEVELOPMENT_CANDIDATE",
    }


__all__ = ["RATES_PATH", "run"]
