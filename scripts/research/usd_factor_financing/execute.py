# ruff: noqa: E501 -- execution prose
"""M15 / M16 の修正版の実行層。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY`.

book は `book.run_book(..., rebalance=book.factor_rebalance)`。P&L は 1 回の book から 4 行に分ける:
spot（signal の方向）・spread cost・carry（金利差）・markup（仮定）。markup band の各点で
TOTAL_ECONOMIC を作り、spot − spread（NET_EX_FINANCING）も並べる。
"""

from __future__ import annotations

import dataclasses
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.mechanism_redesign import execute as _mx
from scripts.research.mechanism_redesign import signals
from scripts.research.next_five import execute as _nf
from scripts.research.top_five.execute import (
    TRADING_DAYS,
    _benchmarks,
    _ic,
    _incremental_ic,
    _metrics,
)
from scripts.research.usd_factor_financing import book, prereg

CURRENCIES: Final[tuple[str, ...]] = signals.CURRENCIES
FOREIGN: Final[tuple[str, ...]] = signals.FOREIGN
MARKUPS: Final[tuple[float, ...]] = tuple(prereg.FINANCING["markup_band"])
CENTRAL: Final[float] = float(prereg.FINANCING["central_markup"])
_sharpe = _nf._sharpe


def _config(cost_multiple: float = 1.0, band: float | None = None):
    from scripts.research.continuous_portfolio import construction

    frozen = {k: v for k, v in prereg.BOOK_CONFIG.items() if k != "days_per_year"}
    if band is not None:
        frozen["band"] = band
    return construction.BookConfig(name="usd_factor", cost_multiple=cost_multiple, **frozen)


def economic_book(
    config, scores: pd.DataFrame, excess: pd.DataFrame, rate_excess: pd.DataFrame
) -> pd.DataFrame:
    """1 回の book から spot / spread / carry / notional-days を取り出す（markup は後で掛ける）。"""
    daily = book.run_book(config, scores, excess, TRADING_DAYS, rebalance=book.factor_rebalance)[
        "daily"
    ].copy()
    decision = pd.DatetimeIndex(daily["decision_day"])
    days = np.asarray((daily.index - decision).days, dtype=float)[:, None]
    rate = rate_excess.reindex(decision)[list(CURRENCIES)].fillna(0.0).to_numpy() / 100.0
    exposure = daily[[f"x_{c}" for c in CURRENCIES]].to_numpy()
    carry = exposure * rate * days / 365.0
    for i, currency in enumerate(CURRENCIES):
        daily[f"spot_{currency}"] = daily[f"pnl_{currency}"]
        daily[f"carry_{currency}"] = carry[:, i]
    daily["spot_gross"] = daily["gross"]
    daily["spread_cost"] = daily["cost"]
    daily["carry"] = carry.sum(axis=1)
    #: 通貨 gross × 暦日 / 365（markup 1 単位あたりの年率 notional）
    daily["gross_notional_years"] = np.abs(exposure).sum(axis=1) * days[:, 0] / 365.0
    daily["cost_multiple"] = config.cost_multiple
    return daily


def with_markup(daily: pd.DataFrame, markup: float) -> pd.DataFrame:
    """TOTAL_ECONOMIC(markup) の frame（_metrics が読む列を揃える）。"""
    out = daily.copy()
    financing = markup * out["cost_multiple"] * out["gross_notional_years"]
    exposure_abs = out[[f"x_{c}" for c in CURRENCIES]].abs()
    share = exposure_abs.div(exposure_abs.sum(axis=1).replace(0.0, np.nan), axis=0).fillna(0.0)
    for currency in CURRENCIES:
        out[f"pnl_{currency}"] = (
            out[f"spot_{currency}"] + out[f"carry_{currency}"] - financing * share[f"x_{currency}"]
        )
    out["financing_markup"] = financing
    out["gross"] = out["spot_gross"] + out["carry"]
    out["cost"] = out["spread_cost"] + financing
    out["net"] = out["gross"] - out["cost"]
    return out


def ex_financing(daily: pd.DataFrame) -> pd.DataFrame:
    out = daily.copy()
    for currency in CURRENCIES:
        out[f"pnl_{currency}"] = out[f"spot_{currency}"]
    out["gross"] = out["spot_gross"]
    out["cost"] = out["spread_cost"]
    out["net"] = out["spot_gross"] - out["spread_cost"]
    return out


def _draw_chunk(job):
    scores, excess, rate_excess, shifts = job
    config = _config()
    out = []
    for shift in shifts:
        shifted = _nf._circular_shift(scores, shift)
        daily = economic_book(config, shifted, excess, rate_excess)
        out.append(
            (_sharpe(with_markup(daily, CENTRAL)["net"]), _sharpe(ex_financing(daily)["net"]))
        )
    return out


def null_diagnostic(scores, excess, rate_excess, *, workers: int = 1) -> dict[str, Any]:
    rng = np.random.default_rng(int(prereg.NULL["seed"]))
    count = int(prereg.NULL["draws"])
    shifts = [int(rng.integers(1, max(len(scores), 2))) for _ in range(count)]
    daily = economic_book(_config(), scores, excess, rate_excess)
    observed = {
        "total_central": _sharpe(with_markup(daily, CENTRAL)["net"]),
        "ex_financing": _sharpe(ex_financing(daily)["net"]),
    }
    if workers <= 1:
        drawn = _draw_chunk((scores, excess, rate_excess, shifts))
    else:
        from concurrent.futures import ProcessPoolExecutor

        size = max(1, -(-len(shifts) // workers))
        jobs = [
            (scores, excess, rate_excess, shifts[i : i + size]) for i in range(0, len(shifts), size)
        ]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            drawn = [v for chunk in pool.map(_draw_chunk, jobs) for v in chunk]
    out: dict[str, Any] = {"draws": count, "seed": int(prereg.NULL["seed"])}
    for i, name in enumerate(("total_central", "ex_financing")):
        array = np.array([d[i] for d in drawn if np.isfinite(d[i])])
        value = observed[name]
        out[name] = {
            "observed_sharpe": round(value, 4),
            "p_value": round(float(int((array >= value).sum()) + 1) / float(len(array) + 1), 4),
            "observed_percentile": round(float((array < value).mean()), 4),
            "null_p05": round(float(np.percentile(array, 5)), 4),
            "null_p50": round(float(np.percentile(array, 50)), 4),
            "null_p95": round(float(np.percentile(array, 95)), 4),
            "null_positive_share": round(float((array > 0).mean()), 4),
            "distinct_null_values": int(len(np.unique(np.round(array, 6)))),
        }
    return out


def _annual(series: pd.Series) -> float:
    return float(series.sum() / (len(series) / TRADING_DAYS))


def decomposition(daily: pd.DataFrame) -> dict[str, Any]:
    ex = ex_financing(daily)
    rows = {
        "annual_spot_gross": round(_annual(daily["spot_gross"]), 5),
        "annual_spread_cost": round(_annual(daily["spread_cost"]), 5),
        "annual_carry": round(_annual(daily["carry"]), 5),
        "annual_gross_notional_years_per_year": round(_annual(daily["gross_notional_years"]), 4),
        "net_ex_financing": {
            "annual": round(_annual(ex["net"]), 5),
            "sharpe": round(_sharpe(ex["net"]), 4),
            "gross_sharpe": round(_sharpe(ex["gross"]), 4),
        },
        "total_economic_by_markup": {},
    }
    for markup in MARKUPS:
        total = with_markup(daily, markup)
        rows["total_economic_by_markup"][f"{markup:.4f}"] = {
            "annual": round(_annual(total["net"]), 5),
            "sharpe": round(_sharpe(total["net"]), 4),
            "annual_financing_contribution": round(
                _annual(total["carry"] - total["financing_markup"]), 5
            ),
        }
    signs = {v["annual"] > 0 for v in rows["total_economic_by_markup"].values()}
    rows["total_sign_consistent_across_markup_band"] = len(signs) == 1
    rows["breakeven_markup"] = (
        round(
            float(
                (_annual(ex["net"]) + _annual(daily["carry"]))
                / _annual(daily["gross_notional_years"])
            ),
            5,
        )
        if _annual(daily["gross_notional_years"]) > 0
        else None
    )
    return rows


def _usd_factor_exposure(daily: pd.DataFrame) -> dict[str, Any]:
    x = daily[[f"x_{c}" for c in CURRENCIES]]
    gross = x.abs().sum(axis=1).replace(0.0, np.nan)
    foreign = x[[f"x_{c}" for c in FOREIGN]]
    return {
        "mean_usd_share_of_currency_gross": round(float((x["x_USD"].abs() / gross).mean()), 4),
        "share_of_days_long_usd": round(float((x["x_USD"] > 0).mean()), 4),
        "min_abs_foreign_leg_share": round(
            float((foreign.abs().div(gross, axis=0)).min().min()), 5
        ),
        "foreign_legs_equal": bool(
            np.allclose(foreign.to_numpy(), foreign.to_numpy()[:, [0]], atol=1e-10)
        ),
        "currencies_ever_zero": [c for c in FOREIGN if (x[f"x_{c}"].abs() < 1e-12).any()],
    }


def verdict(primary: dict[str, Any], rename_gates: dict[str, Any]) -> dict[str, Any]:
    decomp = primary["pnl_decomposition"]
    economics = primary["development_economics"]
    null = primary["null_diagnostic"]["total_central"]
    n_eff = float(primary["metrics_total_central"]["effective_independent_observations"])
    totals = [v["annual"] for v in decomp["total_economic_by_markup"].values()]
    spot = decomp["annual_spot_gross"]
    ex_net = decomp["net_ex_financing"]["annual"]
    failure = None
    if any(g.get("verdict") == "RENAME" for g in rename_gates.values()):
        suffix = "RENAME_OF_A_PRIOR_TRACK"
    elif not decomp["total_sign_consistent_across_markup_band"]:
        suffix = "FINANCING_NOT_DECISION_GRADE"
    elif all(t <= 0 for t in totals):
        suffix = "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
        failure = (
            "SIGNAL_FAILURE"
            if spot <= 0
            else "COST_FAILURE"
            if ex_net <= 0
            else "FINANCING_FAILURE"
        )
    elif (
        economics["label"] == "DEVELOPMENT_ECONOMICS_SUPPORTED"
        and null["p_value"] <= 0.05
        and n_eff >= prereg.POWER_RULE["min_effective_observations"]
    ):
        suffix = "STRONG_EXPLORATORY_CANDIDATE"
    elif (
        economics["core_satisfied"]
        and null["observed_percentile"] >= 0.80
        and n_eff >= prereg.POWER_RULE["min_effective_observations"]
    ):
        suffix = "MARGINAL_EXPLORATORY_CANDIDATE"
    else:
        suffix = "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE"
    return {
        "status": f"{primary['track']}_CORRECTED_{suffix}",
        "qualifier": prereg.QUALIFIER,
        "failure_class": failure,
        "effective_independent_observations": round(n_eff, 1),
        "rename_gates_not_evaluable": sorted(
            k for k, g in rename_gates.items() if g.get("verdict") not in {"RENAME", "DISTINCT"}
        ),
        "never": prereg.NEVER,
    }


def run_track(track: str, span: str, built: dict[str, Any], *, workers: int = 1) -> dict[str, Any]:
    excess = built[span]["currency_excess_return"]
    try:
        scores = signals.scores_for(track, built, span)
    except (signals.SignalUnavailableError, signals.NonContiguousScoresError) as error:
        return {
            "track": track,
            "span": span,
            "verdict": "DATA_NOT_DECISION_GRADE",
            "why": str(error)[:300],
        }
    rate_excess = _mx.carry_operator(
        signals.carry_rate_panel(excess.index), list(built[span]["pair_returns"].columns)
    )
    config = _config()
    daily = economic_book(config, scores, excess, rate_excess)
    total = with_markup(daily, CENTRAL)
    control = _benchmarks(excess)["fx_own_momentum_20d"].reindex(scores.index)
    metrics_total = _metrics(total, scores, excess)
    metrics_total["incremental_ic"] = _incremental_ic(scores, control, excess)
    metrics_total["effective_independent_observations"] = round(
        _mx.effective_observations(scores), 2
    )
    metrics_total["signal_persistence_lag1"] = round(_nf._lag_one_autocorrelation(scores), 4)
    metrics_total["detection_floor_mde95"] = round(
        float(1.96 / np.sqrt(len(scores) / TRADING_DAYS)), 4
    )
    metrics_ex = _metrics(ex_financing(daily), scores, excess)

    stressed = {}
    for multiple in (1.5, 2.0):
        stressed_daily = economic_book(
            dataclasses.replace(config, cost_multiple=multiple), scores, excess, rate_excess
        )
        stressed[f"cost_x{multiple}"] = {
            "net_annual_return": _annual(with_markup(stressed_daily, CENTRAL)["net"]),
            "net_sharpe": round(_sharpe(with_markup(stressed_daily, CENTRAL)["net"]), 4),
            "net_ex_financing_sharpe": round(_sharpe(ex_financing(stressed_daily)["net"]), 4),
        }

    benches = {}
    for name, frame in _benchmarks(excess).items():
        usable = frame.reindex(scores.index).dropna(how="any")
        if usable.empty or name != "constant_long_usd":
            continue
        bench = economic_book(config, usable, excess, rate_excess)
        benches[name] = {
            "total_central_sharpe": round(_sharpe(with_markup(bench, CENTRAL)["net"]), 4),
            "ex_financing_sharpe": round(_sharpe(ex_financing(bench)["net"]), 4),
            "ic": _ic(usable, excess),
        }

    out: dict[str, Any] = {
        "track": track,
        "span": span,
        "is_primary_span": span == prereg.PRIMARY_SPAN,
        "metrics_total_central": metrics_total,
        "metrics_ex_financing": metrics_ex,
        "pnl_decomposition": decomposition(daily),
        "usd_factor_exposure": _usd_factor_exposure(daily),
        "cost_stress": stressed,
        "benchmarks": benches,
        "capacity_total_central": _capacity_with_financing(metrics_total, daily),
        "daily_net_total_central": total["net"],
        "scores": scores,
    }
    if span == prereg.PRIMARY_SPAN:
        out["null_diagnostic"] = null_diagnostic(scores, excess, rate_excess, workers=workers)
        out["development_economics"] = _mx.development_economics(track, metrics_total, stressed)
        eligible = _nf.stage2_eligible(
            out["development_economics"],
            {"observed_percentile": out["null_diagnostic"]["total_central"]["observed_percentile"]},
        )
        out["stage_2"] = (
            {"eligible": True, "regression": _nf.stage2_regression(scores, excess)}
            if eligible
            else {"eligible": False}
        )
        out["nuisance_sensitivity"] = {
            name: _sensitivity(track, span, built, name, rate_excess)
            for name in prereg.NUISANCE_APPLIES[track]
        }
    return out


def _capacity_with_financing(metrics: dict[str, Any], daily: pd.DataFrame) -> dict[str, Any]:
    """next-five の capacity に、各 scenario での financing（carry − central markup）の年率を足す。"""
    capacity = _nf._capacity(metrics)
    if not capacity.get("reachable"):
        return capacity
    realized = float(metrics["realized_vol"])
    total = with_markup(daily, CENTRAL)
    financing = _annual(total["carry"] - total["financing_markup"])
    for key, row in list(capacity.items()):
        if isinstance(row, dict) and "annual_net" in row:
            target = (
                row.get("required_target_vol")
                or float(key.removeprefix("vol_").rstrip("%")) / 100.0
            )
            row["financing_burden_or_benefit"] = round(financing * target / realized, 5)
    for key, row in capacity.get("scenarios", {}).items():
        target = float(key.removeprefix("vol_").rstrip("%")) / 100.0
        row["financing_burden_or_benefit"] = round(financing * target / realized, 5)
    return capacity


def _sensitivity(track, span, built, name, rate_excess) -> dict[str, Any]:
    spec = signals.NUISANCE[name]
    excess = built[span]["currency_excess_return"]
    grid: dict[str, Any] = {}
    for value in spec["sensitivity_set"]:
        band = None
        overrides: dict[str, Any] | None = {name: value}
        if name == "implementation_tolerance_band":
            band, overrides = float(value), None
        try:
            scores = signals.scores_for(track, built, span, overrides=overrides)
        except (signals.SignalUnavailableError, signals.NonContiguousScoresError) as error:
            grid[str(value)] = {"status": str(error)[:120]}
            continue
        daily = economic_book(_config(band=band), scores, excess, rate_excess)
        grid[str(value)] = {
            "total_central_sharpe": round(_sharpe(with_markup(daily, CENTRAL)["net"]), 4),
            "ex_financing_sharpe": round(_sharpe(ex_financing(daily)["net"]), 4),
        }
    return {"constant": name, "primary": spec["primary"], "grid": grid}


__all__ = [
    "decomposition",
    "economic_book",
    "ex_financing",
    "null_diagnostic",
    "run_track",
    "verdict",
    "with_markup",
]
