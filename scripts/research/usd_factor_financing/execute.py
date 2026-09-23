# ruff: noqa: E501 -- execution prose
"""M15 / M16 の修正版の実行層（pre-alpha amendment 後）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE` ·
`POST_RESULT_IMPLEMENTATION_CORRECTED_EXPLORATORY_ONLY`.

**USD を numeraire にした book**（Role 2 RF-2）。exposure x（USD に h、外国 7 通貨に −h/7）を
7 本の USD pair だけに振り、P&L は `x · R`（R_c = c の対 USD log return、R_USD = 0）で測る。
和がゼロなので numeraire に依存せず、**実際の通貨 exposure がそのまま x になる**
（equal-split の pair book は recent の 20 pair では外国脚が最大 2.08 倍ずれていた）。
vol targeting も同じ R の上で行う。IC・incremental IC は signal の情報量の指標なので
従来どおり currency excess return で測る。

**financing の会計**（Role 1 B-1）: signal と同じ lag 付き 3 か月金利で carry を測ると、会計が
feature の関数になる。primary の carry は **当時の政策金利**（BIS 月末値を翌月に使う — その月に
実際に効いていた金利）で、lag 付き 3 か月金利は感度。markup band 4 点 × 金利基準 2 つの 8 セルで
TOTAL_ECONOMIC の符号が揃わなければ FINANCING_NOT_DECISION_GRADE。
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
ADVERSE: Final[float] = max(MARKUPS)
BASES: Final[tuple[str, ...]] = ("policy_contemporaneous", "three_month_lagged")
PRIMARY_BASIS: Final[str] = "policy_contemporaneous"
_sharpe = _nf._sharpe


def _config(cost_multiple: float = 1.0, band: float | None = None):
    from scripts.research.continuous_portfolio import construction

    frozen = {k: v for k, v in prereg.BOOK_CONFIG.items() if k != "days_per_year"}
    if band is not None:
        frozen["band"] = band
    return construction.BookConfig(name="usd_factor", cost_multiple=cost_multiple, **frozen)


# ----------------------------------------------------------------------
# USD numeraire の return と金利
# ----------------------------------------------------------------------
def usd_numeraire_returns(pair_returns: pd.DataFrame) -> pd.DataFrame:
    """R_c = c の対 USD log return（C_USD なら +r、USD_C なら −r）、R_USD = 0。"""
    out = pd.DataFrame(0.0, index=pair_returns.index, columns=list(CURRENCIES))
    for currency in FOREIGN:
        if f"{currency}_USD" in pair_returns.columns:
            out[currency] = pair_returns[f"{currency}_USD"]
        elif f"USD_{currency}" in pair_returns.columns:
            out[currency] = -pair_returns[f"USD_{currency}"]
        else:
            raise KeyError(f"{currency} の USD pair が無い")
    return out


def policy_rates_contemporaneous(index: pd.DatetimeIndex) -> pd.DataFrame:
    """BIS の月末政策金利を**その月末から**使う（翌月の各日に効いていた金利）。signal の series ではない。

    BoJ が数値の政策金利を持たなかった期間（BIS に値が無い）だけ JPY を 0% と置く（判断、prereg に凍結）。
    """
    columns: dict[str, pd.Series] = {}
    for currency in CURRENCIES:
        series, _ = signals._load_slot("policy_rate_bis", currency)
        placed = series.copy()
        placed.index = placed.index.to_period("M").to_timestamp(how="end").normalize()
        columns[currency] = signals._align(placed, index, staleness_days=75)
    rates = pd.DataFrame(columns, index=index)
    for first, last in prereg.FINANCING["jpy_policy_zero_periods"]:
        window = (rates.index >= first) & (rates.index <= last)
        rates.loc[window, "JPY"] = rates.loc[window, "JPY"].fillna(0.0)
    return rates


def rate_panels(index: pd.DatetimeIndex) -> dict[str, pd.DataFrame]:
    return {
        "policy_contemporaneous": policy_rates_contemporaneous(index),
        "three_month_lagged": signals.carry_rate_panel(index),
    }


# ----------------------------------------------------------------------
# book と会計
# ----------------------------------------------------------------------
def economic_book(
    config, scores: pd.DataFrame, numeraire: pd.DataFrame, rates: dict[str, pd.DataFrame]
) -> pd.DataFrame:
    """1 回の book（USD numeraire）から spot / spread / 各金利基準の carry / pair notional を取り出す。"""
    daily = book.run_book(config, scores, numeraire, TRADING_DAYS, rebalance=book.factor_rebalance)[
        "daily"
    ].copy()
    decision = pd.DatetimeIndex(daily["decision_day"])
    days = np.asarray((daily.index - decision).days, dtype=float)[:, None]
    exposure = daily[[f"x_{c}" for c in CURRENCIES]].to_numpy()
    for currency in CURRENCIES:
        daily[f"spot_{currency}"] = daily[f"pnl_{currency}"]
    for basis, panel in rates.items():
        level = panel.reindex(decision)[list(CURRENCIES)].to_numpy() / 100.0
        relative = level - level[:, [CURRENCIES.index("USD")]]
        carry = np.nan_to_num(exposure * relative) * days / 365.0
        daily[f"carry_{basis}"] = carry.sum(axis=1)
        for i, currency in enumerate(CURRENCIES):
            daily[f"carry_{basis}_{currency}"] = carry[:, i]
    daily["spot_gross"] = daily["gross"]
    daily["spread_cost"] = daily["cost"]
    #: 実際の pair notional（USD pair 7 本の |notional| の和 = 外国脚の |x| の和 = |x_USD|）× 暦日 / 365
    daily["pair_notional_years"] = (
        np.abs(exposure[:, [CURRENCIES.index(c) for c in FOREIGN]]).sum(axis=1) * days[:, 0] / 365.0
    )
    daily["cost_multiple"] = config.cost_multiple
    return daily


def total(daily: pd.DataFrame, basis: str, markup: float) -> pd.DataFrame:
    """TOTAL_ECONOMIC(basis, markup)。markup は **pair notional 1 単位あたりの年率**。"""
    out = daily.copy()
    financing = markup * out["cost_multiple"] * out["pair_notional_years"]
    foreign_abs = out[[f"x_{c}" for c in FOREIGN]].abs()
    share = foreign_abs.div(foreign_abs.sum(axis=1).replace(0.0, np.nan), axis=0).fillna(0.0)
    for currency in CURRENCIES:
        charge = financing * share[f"x_{currency}"] if currency != "USD" else 0.0
        out[f"pnl_{currency}"] = out[f"spot_{currency}"] + out[f"carry_{basis}_{currency}"] - charge
    out["carry"] = out[f"carry_{basis}"]
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


def _annual(series: pd.Series) -> float:
    return float(series.sum() / (len(series) / TRADING_DAYS))


# ----------------------------------------------------------------------
# null
# ----------------------------------------------------------------------
def _draw_chunk(job):
    scores, numeraire, rates, shifts, persistence = job
    config = _config()
    out = []
    for shift in shifts:
        shifted = _nf._circular_shift(scores, shift)
        drawn = _nf._lag_one_autocorrelation(shifted)
        if np.isfinite(persistence) and abs(drawn - persistence) >= 0.05:
            raise AssertionError("帰無が signal の自己相関を壊した")
        daily = economic_book(config, shifted, numeraire, rates)
        out.append(
            (
                _sharpe(total(daily, PRIMARY_BASIS, CENTRAL)["net"]),
                _sharpe(ex_financing(daily)["net"]),
            )
        )
    return out


def null_diagnostic(scores, numeraire, rates, *, workers: int = 1) -> dict[str, Any]:
    rng = np.random.default_rng(int(prereg.NULL["seed"]))
    count = int(prereg.NULL["draws"])
    shifts = [int(rng.integers(1, max(len(scores), 2))) for _ in range(count)]
    persistence = _nf._lag_one_autocorrelation(scores)
    daily = economic_book(_config(), scores, numeraire, rates)
    observed = {
        "total_central": _sharpe(total(daily, PRIMARY_BASIS, CENTRAL)["net"]),
        "ex_financing": _sharpe(ex_financing(daily)["net"]),
    }
    if workers <= 1:
        drawn = _draw_chunk((scores, numeraire, rates, shifts, persistence))
    else:
        from concurrent.futures import ProcessPoolExecutor

        size = max(1, -(-len(shifts) // workers))
        jobs = [
            (scores, numeraire, rates, shifts[i : i + size], persistence)
            for i in range(0, len(shifts), size)
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


# ----------------------------------------------------------------------
# 分解・exposure・判定
# ----------------------------------------------------------------------
def decomposition(daily: pd.DataFrame) -> dict[str, Any]:
    ex = ex_financing(daily)
    rows: dict[str, Any] = {
        "annual_spot_gross": round(_annual(daily["spot_gross"]), 5),
        "annual_spread_cost": round(_annual(daily["spread_cost"]), 5),
        "annual_carry": {basis: round(_annual(daily[f"carry_{basis}"]), 5) for basis in BASES},
        "annual_pair_notional_years": round(_annual(daily["pair_notional_years"]), 4),
        "net_ex_financing": {
            "name": "NET_EX_TRANSACTION_COSTS_EXCLUDING_FINANCING",
            "annual": round(_annual(ex["net"]), 5),
            "sharpe": round(_sharpe(ex["net"]), 4),
            "gross_sharpe": round(_sharpe(ex["gross"]), 4),
        },
        "total_economic": {},
    }
    signs = set()
    for basis in BASES:
        for markup in MARKUPS:
            frame = total(daily, basis, markup)
            annual = _annual(frame["net"])
            signs.add(annual > 0)
            rows["total_economic"][f"{basis}|{markup:.4f}"] = {
                "annual": round(annual, 5),
                "sharpe": round(_sharpe(frame["net"]), 4),
                "annual_financing_contribution": round(
                    _annual(frame["carry"] - frame["financing_markup"]), 5
                ),
            }
    rows["total_sign_consistent_across_all_cells"] = len(signs) == 1
    notional = _annual(daily["pair_notional_years"])
    rows["breakeven_markup_per_pair_notional"] = {
        basis: (
            round((_annual(ex["net"]) + _annual(daily[f"carry_{basis}"])) / notional, 5)
            if notional > 0
            else None
        )
        for basis in BASES
    }
    central = total(daily, PRIMARY_BASIS, CENTRAL)
    financing_part = _annual(central["carry"] - central["financing_markup"])
    ex_part = _annual(ex["net"])
    rows["pnl_source"] = {
        "net_ex_financing_positive": ex_part > 0,
        "financing_contribution_positive": financing_part > 0,
        "label": (
            "SPOT_AND_FINANCING_BOTH_POSITIVE"
            if ex_part > 0 and financing_part > 0
            else "SPOT_DRIVEN_FINANCING_NEGATIVE"
            if ex_part > 0
            else "FINANCING_DRIVEN_SPOT_NOT_POSITIVE"
            if financing_part > 0
            else "NEITHER_POSITIVE"
        ),
    }
    return rows


def usd_factor_exposure(daily: pd.DataFrame) -> dict[str, Any]:
    active = daily[daily["leverage"] > 0]
    x = active[[f"x_{c}" for c in CURRENCIES]]
    gross = x.abs().sum(axis=1).replace(0.0, np.nan)
    foreign = x[[f"x_{c}" for c in FOREIGN]]
    return {
        "days_with_zero_leverage_excluded": int(len(daily) - len(active)),
        "mean_usd_share_of_currency_gross": round(float((x["x_USD"].abs() / gross).mean()), 4),
        "share_of_days_long_usd": round(float((x["x_USD"] > 0).mean()), 4),
        "min_abs_foreign_leg_share": round(
            float((foreign.abs().div(gross, axis=0)).min().min()), 5
        ),
        "foreign_legs_equal": bool(
            np.allclose(foreign.to_numpy(), foreign.to_numpy()[:, [0]], atol=1e-10)
        ),
        "currencies_ever_zero_when_invested": [
            c for c in FOREIGN if (x[f"x_{c}"].abs() < 1e-12).any()
        ],
    }


def _economics_at(track: str, frame: pd.DataFrame, scores, excess, stressed) -> dict[str, Any]:
    metrics = _metrics(frame, scores, excess)
    control = _benchmarks(excess)["fx_own_momentum_20d"].reindex(scores.index)
    metrics["incremental_ic"] = _incremental_ic(scores, control, excess)
    return _mx.development_economics(track, metrics, stressed)


def verdict(primary: dict[str, Any], rename_gates: dict[str, Any]) -> dict[str, Any]:
    decomp = primary["pnl_decomposition"]
    economics = primary["development_economics"]
    adverse = primary["development_economics_adverse_endpoint"]
    null = primary["null_diagnostic"]["total_central"]
    n_eff = float(primary["metrics_total_central"]["effective_independent_observations"])
    totals = [v["annual"] for v in decomp["total_economic"].values()]
    spot = decomp["annual_spot_gross"]
    ex_net = decomp["net_ex_financing"]["annual"]
    enough = bool(np.isfinite(n_eff) and n_eff >= prereg.POWER_RULE["min_effective_observations"])

    def _suffix(power_ok: bool) -> tuple[str, str | None]:
        if any(g.get("verdict") == "RENAME" for g in rename_gates.values()):
            return "RENAME_OF_A_PRIOR_TRACK", None
        if not decomp["total_sign_consistent_across_all_cells"]:
            return "FINANCING_NOT_DECISION_GRADE", None
        if all(t <= 0 for t in totals):
            failure = (
                "SIGNAL_FAILURE"
                if spot <= 0
                else "COST_FAILURE"
                if ex_net <= 0
                else "FINANCING_FAILURE"
            )
            return "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT", failure
        if (
            economics["label"] == "DEVELOPMENT_ECONOMICS_SUPPORTED"
            and adverse["core_satisfied"]
            and null["p_value"] <= 0.05
            and power_ok
        ):
            return "STRONG_EXPLORATORY_CANDIDATE", None
        if (
            economics["core_satisfied"]
            and adverse["core_satisfied"]
            and null["observed_percentile"] >= 0.80
            and power_ok
        ):
            return "MARGINAL_EXPLORATORY_CANDIDATE", None
        return "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE", None

    suffix, failure = _suffix(enough)
    uncapped, _ = _suffix(True)
    return {
        "status": f"{primary['track']}_CORRECTED_{suffix}",
        "status_before_power_cap": f"{primary['track']}_CORRECTED_{uncapped}",
        "underpowered": not enough,
        "qualifier": prereg.QUALIFIER,
        "failure_class": failure,
        "pnl_source": decomp["pnl_source"]["label"],
        "effective_independent_observations": round(n_eff, 1),
        "rename_gates_not_evaluable": sorted(
            k for k, g in rename_gates.items() if g.get("verdict") not in {"RENAME", "DISTINCT"}
        ),
        "never": prereg.NEVER,
    }


def _capacity_with_financing(
    metrics: dict[str, Any], daily: pd.DataFrame, all_positive: bool
) -> dict[str, Any]:
    if not all_positive:
        return {
            "reachable": False,
            "why": "TOTAL_ECONOMIC が 8 セル全点で正ではないので capacity を出さない",
        }
    capacity = _nf._capacity(metrics)
    if not capacity.get("reachable"):
        return capacity
    realized = float(metrics["realized_vol"])
    central = total(daily, PRIMARY_BASIS, CENTRAL)
    financing = _annual(central["carry"] - central["financing_markup"])
    for _key, row in list(capacity.items()):
        if isinstance(row, dict) and "annual_net" in row and "required_target_vol" in row:
            row["financing_burden_or_benefit"] = round(
                financing * row["required_target_vol"] / realized, 5
            )
    for key, row in capacity.get("scenarios", {}).items():
        target = float(key.removeprefix("vol_").rstrip("%")) / 100.0
        row["financing_burden_or_benefit"] = round(financing * target / realized, 5)
    capacity["meaning_of_reachable"] = "net > 0 なので leverage 計算を出した、という意味だけ"
    return capacity


def run_track(track: str, span: str, built: dict[str, Any], *, workers: int = 1) -> dict[str, Any]:
    excess = built[span]["currency_excess_return"]
    scores = signals.scores_for(track, built, span)
    numeraire = usd_numeraire_returns(built[span]["pair_returns"]).reindex(excess.index).fillna(0.0)
    rates = rate_panels(excess.index)
    config = _config()
    daily = economic_book(config, scores, numeraire, rates)
    central = total(daily, PRIMARY_BASIS, CENTRAL)
    adverse = {basis: total(daily, basis, ADVERSE) for basis in BASES}
    control = _benchmarks(excess)["fx_own_momentum_20d"].reindex(scores.index)
    metrics_total = _metrics(central, scores, excess)
    metrics_total["incremental_ic"] = _incremental_ic(scores, control, excess)
    metrics_total["effective_independent_observations"] = round(
        _mx.effective_observations(scores), 2
    )
    metrics_total["signal_persistence_lag1"] = round(_nf._lag_one_autocorrelation(scores), 4)
    metrics_total["detection_floor_mde95"] = round(
        float(1.96 / np.sqrt(len(scores) / TRADING_DAYS)), 4
    )
    metrics_ex = _metrics(ex_financing(daily), scores, excess)

    stressed: dict[str, Any] = {}
    stressed_adverse: dict[str, Any] = {}
    for multiple in (1.5, 2.0):
        stressed_daily = economic_book(
            dataclasses.replace(config, cost_multiple=multiple), scores, numeraire, rates
        )
        stressed[f"cost_x{multiple}"] = {
            "net_annual_return": _annual(total(stressed_daily, PRIMARY_BASIS, CENTRAL)["net"]),
            "net_sharpe": round(_sharpe(total(stressed_daily, PRIMARY_BASIS, CENTRAL)["net"]), 4),
            "net_ex_financing_sharpe": round(_sharpe(ex_financing(stressed_daily)["net"]), 4),
        }
        for basis in BASES:
            stressed_adverse.setdefault(basis, {})[f"cost_x{multiple}"] = {
                "net_sharpe": round(_sharpe(total(stressed_daily, basis, ADVERSE)["net"]), 4)
            }

    benches = {}
    usable = _benchmarks(excess)["constant_long_usd"].reindex(scores.index).dropna(how="any")
    if not usable.empty:
        bench = economic_book(config, usable, numeraire, rates)
        benches["constant_long_usd"] = {
            "total_central_sharpe": round(_sharpe(total(bench, PRIMARY_BASIS, CENTRAL)["net"]), 4),
            "ex_financing_sharpe": round(_sharpe(ex_financing(bench)["net"]), 4),
            "ic": _ic(usable, excess),
        }

    decomp = decomposition(daily)
    all_positive = all(v["annual"] > 0 for v in decomp["total_economic"].values())
    out: dict[str, Any] = {
        "track": track,
        "span": span,
        "is_primary_span": span == prereg.PRIMARY_SPAN,
        "metrics_total_central": metrics_total,
        "metrics_ex_financing": metrics_ex,
        "pnl_decomposition": decomp,
        "usd_factor_exposure": usd_factor_exposure(daily),
        "cost_stress": stressed,
        "benchmarks": benches,
        "capacity_total_central": _capacity_with_financing(metrics_total, daily, all_positive),
        "daily_net_total_central": central["net"],
        "scores": scores,
    }
    if span == prereg.PRIMARY_SPAN:
        out["null_diagnostic"] = null_diagnostic(scores, numeraire, rates, workers=workers)
        out["development_economics"] = _mx.development_economics(track, metrics_total, stressed)
        #: 不利な端点は金利基準 2 つの両方（markup 最大）。core は両方で真であること（re-audit O-1）
        by_basis = {
            basis: _economics_at(track, adverse[basis], scores, excess, stressed_adverse[basis])
            for basis in BASES
        }
        out["development_economics_adverse_endpoint"] = {
            "by_basis": by_basis,
            "core_satisfied": all(row["core_satisfied"] for row in by_basis.values()),
        }
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
            name: _sensitivity(track, span, built, name, numeraire, rates)
            for name in prereg.NUISANCE_APPLIES[track]
        }
    return out


def _sensitivity(track, span, built, name, numeraire, rates) -> dict[str, Any]:
    spec = signals.NUISANCE[name]
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
        daily = economic_book(_config(band=band), scores, numeraire, rates)
        grid[str(value)] = {
            "total_central_sharpe": round(_sharpe(total(daily, PRIMARY_BASIS, CENTRAL)["net"]), 4),
            "ex_financing_sharpe": round(_sharpe(ex_financing(daily)["net"]), 4),
        }
    return {"constant": name, "primary": spec["primary"], "grid": grid}


__all__ = [
    "decomposition",
    "economic_book",
    "ex_financing",
    "null_diagnostic",
    "policy_rates_contemporaneous",
    "run_track",
    "total",
    "usd_numeraire_returns",
    "verdict",
]
