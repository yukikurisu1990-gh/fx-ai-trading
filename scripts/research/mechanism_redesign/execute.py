# ruff: noqa: E501 -- execution prose
"""mechanism redesign cycle の実行層。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**統計は next-five と同じ関数を import して使う**（指標・development economics・Stage 2 適格・
capacity・降格 gate）。この cycle で違うのは 3 つ（すべて alpha 前に凍結）:

1. **判定する P&L に carry と financing を入れる**（pre-alpha review Role 1 B-1）。
   spot だけの P&L は dollar carry が名乗る premium を測らない。全 track を
   `spot + carry accrual − spread cost − 仮定 financing markup` で判定し、
   spot だけの値は前 cycle との比較のための診断として並べる。
2. **検出力の上限**: primary の有効標本数（AR(1) 近似）が 10 未満の track は、
   正の結果でも POSITIVE_EXPLORATORY を超えない。負の結果はその formulation と span に限った
   ものとして記録し、family を閉じない（Role 1 R-4）。
3. **rename gate が評価できないとき**は RENAME にも DISTINCT にもせず NOT_EVALUABLE と記録する。
   verdict は RENAME のときだけ変わる（Role 1 R-2）。
"""

from __future__ import annotations

import dataclasses
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.continuous_portfolio import construction
from scripts.research.mechanism_redesign import prereg, signals
from scripts.research.next_five import execute as _nf
from scripts.research.top_five.execute import (
    TRADING_DAYS,
    _benchmarks,
    _ic,
    _incremental_ic,
    _metrics,
)

_sharpe = _nf._sharpe
_circular_shift = _nf._circular_shift
_lag_one_autocorrelation = _nf._lag_one_autocorrelation

CURRENCIES: Final[tuple[str, ...]] = signals.CURRENCIES


def _config(
    track: str, cost_multiple: float = 1.0, band: float | None = None
) -> construction.BookConfig:
    frozen = {k: v for k, v in prereg.BOOK_CONFIG.items() if not k.startswith("why_")}
    frozen.pop("days_per_year", None)
    frozen.update(prereg.BOOK_CONFIG_DEVIATIONS.get(track, {}))
    if band is not None:
        frozen["band"] = band
    return construction.BookConfig(name=track, cost_multiple=cost_multiple, **frozen)


def book(
    config: construction.BookConfig,
    scores: pd.DataFrame,
    excess: pd.DataFrame,
    rates: pd.DataFrame,
) -> pd.DataFrame:
    """run_book の日次に carry と financing を足す。**判定はこの net で行う。**

    carry: 決定日の保有 exposure × `rates`（**spot と同じ pair book 演算子を通した金利差**、%、年率）
    × 暦日 / 365。spot の P&L は x·e（e は pair return に `_currency_excess` を掛けたもの）なので、
    同じ pair book の carry は pair の金利差に同じ演算子を掛けた値との内積になる（re-audit B-1）。
    financing: |exposure| の和 × 年率の仮定 markup × 暦日 / 365 × cost_multiple。
    """
    daily = construction.run_book(config, scores, excess, TRADING_DAYS)["daily"].copy()
    decision = pd.DatetimeIndex(daily["decision_day"])
    days = np.asarray((daily.index - decision).days, dtype=float)[:, None]
    rate = rates.reindex(decision)[list(CURRENCIES)].fillna(0.0).to_numpy() / 100.0
    exposure = daily[[f"x_{c}" for c in CURRENCIES]].to_numpy()
    carry = exposure * rate * days / 365.0
    financing = (
        np.abs(exposure)
        * prereg.FINANCING["markup_annual_per_unit_currency_gross"]
        * config.cost_multiple
        * days
        / 365.0
    )
    for i, currency in enumerate(CURRENCIES):
        daily[f"pnl_{currency}"] = daily[f"pnl_{currency}"] + carry[:, i] - financing[:, i]
    daily["spot_gross"] = daily["gross"]
    daily["spread_cost"] = daily["cost"]
    daily["carry"] = carry.sum(axis=1)
    daily["financing"] = financing.sum(axis=1)
    daily["gross"] = daily["spot_gross"] + daily["carry"]
    daily["cost"] = daily["spread_cost"] + daily["financing"]
    daily["net"] = daily["gross"] - daily["cost"]
    return daily


def carry_operator(rates: pd.DataFrame, pairs: list[str]) -> pd.DataFrame:
    """pair ごとの金利差（base − quote）に、spot の currency excess return と同じ演算子を掛ける。

    片方の金利が無い pair はその日の平均から外れる。全 pair が無い通貨は book() で 0 になる。
    """
    from scripts.research.top_five import panel

    diff = pd.DataFrame(
        {pair: rates[pair.split("_")[0]] - rates[pair.split("_")[1]] for pair in pairs},
        index=rates.index,
    )
    return panel._currency_excess(diff)["currency_excess_return"]


def effective_observations(scores: pd.DataFrame) -> float:
    values = scores.to_numpy()
    if len(values) < 3:
        return float("nan")
    rho = float(np.corrcoef(values[:-1].ravel(), values[1:].ravel())[0, 1])
    if not np.isfinite(rho) or rho >= 1:
        return 1.0
    return float(len(values) * (1 - rho) / (1 + rho))


def _draw_chunk(
    job: tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame, list[int], float],
) -> list[float]:
    track, scores, excess, rates, shifts, persistence = job
    config = _config(track)
    out: list[float] = []
    for shift in shifts:
        shifted = _circular_shift(scores, shift)
        drawn = _lag_one_autocorrelation(shifted)
        if np.isfinite(persistence) and abs(drawn - persistence) >= 0.05:
            raise AssertionError("帰無が signal の自己相関を壊した")
        out.append(_sharpe(book(config, shifted, excess, rates)["net"]))
    return out


def null_diagnostic(
    track: str,
    scores: pd.DataFrame,
    excess: pd.DataFrame,
    rates: pd.DataFrame,
    *,
    workers: int = 1,
) -> dict[str, Any]:
    """**draw 数は凍結値だけ**（実行時に変えられない。Role 1 R-3 / Role 2 RF-6）。"""
    spec = prereg.NULL_DIAGNOSTIC["permutation"]
    count = int(spec["draws"])
    rng = np.random.default_rng(int(spec["seed"]))
    observed = book(_config(track), scores, excess, rates)
    observed_sharpe = _sharpe(observed["net"])
    observed_annual = float(observed["net"].sum() / (len(observed["net"]) / TRADING_DAYS))
    persistence = _lag_one_autocorrelation(scores)
    shifts = [int(rng.integers(1, max(len(scores), 2))) for _ in range(count)]
    if workers <= 1:
        drawn = _draw_chunk((track, scores, excess, rates, shifts, persistence))
    else:
        from concurrent.futures import ProcessPoolExecutor

        size = max(1, -(-len(shifts) // workers))
        jobs = [
            (track, scores, excess, rates, shifts[i : i + size], persistence)
            for i in range(0, len(shifts), size)
        ]
        with ProcessPoolExecutor(max_workers=workers) as pool:
            drawn = [v for chunk in pool.map(_draw_chunk, jobs) for v in chunk]
    array = np.array([v for v in drawn if np.isfinite(v)])
    p_value = float(int((array >= observed_sharpe).sum()) + 1) / float(len(array) + 1)
    percentile = float((array < observed_sharpe).mean()) if len(array) else float("nan")
    rejected = bool(observed_annual > 0 and p_value <= 0.05)
    return {
        "diagnostic": prereg.NULL_DIAGNOSTIC["id"],
        "is_the_only_gate": False,
        "draws": count,
        "seed": int(spec["seed"]),
        "judged_pnl": prereg.FINANCING["judged_pnl"],
        "observed_net_sharpe": round(observed_sharpe, 4),
        "observed_net_annual_return": round(observed_annual, 5),
        "p_value": round(p_value, 4),
        "observed_percentile": round(percentile, 4),
        "null_net_sharpe_mean": round(float(array.mean()), 4),
        "null_net_sharpe_p05": round(float(np.percentile(array, 5)), 4),
        "null_net_sharpe_p50": round(float(np.percentile(array, 50)), 4),
        "null_net_sharpe_p95": round(float(np.percentile(array, 95)), 4),
        "null_positive_share": round(float((array > 0).mean()), 4),
        "distinct_null_values": int(len(np.unique(np.round(array, 6)))),
        "signal_persistence_lag1": None if not np.isfinite(persistence) else round(persistence, 4),
        "label": "NULL_REJECTION_SUPPORTED" if rejected else "NULL_REJECTION_NOT_SUPPORTED",
        "multiplicity_note": prereg.NULL_DIAGNOSTIC["multiplicity"],
    }


def development_economics(
    track: str, metrics: dict[str, Any], stressed: dict[str, Any]
) -> dict[str, Any]:
    """next-five と同じ判定。**ドル track だけ E5 を USD 以外の LOO で測る**（凍結済みの規則）。"""
    if track in signals.DOLLAR_TRACKS:
        loo = dict(metrics.get("leave_one_currency_out_net_sharpe") or {})
        loo.pop("USD", None)
        metrics = {**metrics, "leave_one_currency_out_net_sharpe": loo}
    return _nf.development_economics(metrics, stressed)


POSITIVE_SUFFIXES: Final[frozenset[str]] = frozenset(
    {"STRONG_DEVELOPMENT_CANDIDATE", "MARGINAL_DEVELOPMENT_CANDIDATE"}
)


def verdict(
    track: str,
    primary: dict[str, Any],
    other: dict[str, Any] | None,
    rename_gates: dict[str, Any],
) -> dict[str, Any]:
    """凍結した VERDICT_LOGIC を上から当て、その後に検出力の上限を当てる。"""
    metrics = primary["metrics"]
    economics = primary["development_economics"]
    null = primary["null_diagnostic"]
    gross, net = float(metrics["gross_sharpe"]), float(metrics["net_sharpe"])
    n_eff = float(metrics["effective_independent_observations"])
    other_sign = None
    if other and "metrics" in other:
        other_sign = "positive" if float(other["metrics"]["gross_sharpe"]) > 0 else "non_positive"
    renamed = any(g.get("verdict") == "RENAME" for g in rename_gates.values())
    not_evaluable = sorted(
        k
        for k, g in rename_gates.items()
        if g.get("verdict") != "RENAME" and g.get("verdict") != "DISTINCT"
    )
    failure = None
    if renamed:
        suffix = "RENAME_OF_A_CLOSED_TRACK"
    elif net <= 0:
        suffix = "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
        failure = "SIGNAL_FAILURE" if gross <= 0 else "COST_FAILURE"
    elif (
        economics["label"] == "DEVELOPMENT_ECONOMICS_SUPPORTED"
        and null["label"] == "NULL_REJECTION_SUPPORTED"
    ):
        suffix = "STRONG_DEVELOPMENT_CANDIDATE"
    elif economics["core_satisfied"] and float(null["observed_percentile"]) >= 0.80:
        suffix = "MARGINAL_DEVELOPMENT_CANDIDATE"
    else:
        suffix = "POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE"
        checks = economics["checks"]
        if not (checks["E5_breadth"] and checks["E6_concentration"]):
            failure = "CONCENTRATION_FAILURE"
    uncapped = suffix
    #: 有効標本数が測れないときも上限を掛ける（re-audit OBS）
    underpowered = bool(
        not np.isfinite(n_eff) or n_eff < prereg.POWER_RULE["min_effective_observations"]
    )
    if underpowered and suffix in POSITIVE_SUFFIXES:
        suffix = "POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE"
    return {
        "status": prereg.track_status(track, suffix),
        "status_before_power_cap": prereg.track_status(track, uncapped),
        "failure_class": failure,
        "null_label": null["label"],
        "economics_label": economics["label"],
        "other_span_gross_sign": other_sign,
        "effective_independent_observations": round(n_eff, 1),
        "underpowered": underpowered,
        "closure_scope": prereg.POWER_RULE["closure_scope"],
        "rename_gates_not_evaluable": not_evaluable,
    }


def _nuisance_sensitivity(
    track: str, span: str, built: dict[str, Any], name: str, rates: pd.DataFrame
) -> dict[str, Any]:
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
        except signals.SignalUnavailableError as error:
            grid[str(value)] = {"status": f"UNAVAILABLE: {error}"[:120]}
            continue
        except signals.NonContiguousScoresError as error:
            grid[str(value)] = {"status": f"NOT_COMPUTABLE_NONCONTIGUOUS: {error}"[:160]}
            continue
        if scores.empty:
            grid[str(value)] = {"status": "NO_USABLE_DAYS"}
            continue
        daily = book(_config(track, band=band), scores, excess, rates)
        grid[str(value)] = {
            "days": int(len(scores)),
            "net_sharpe": round(_sharpe(daily["net"]), 4),
            "gross_sharpe": round(_sharpe(daily["gross"]), 4),
        }
    nets = [row["net_sharpe"] for row in grid.values() if "net_sharpe" in row]
    return {
        "constant": name,
        "primary": spec["primary"],
        "grid": grid,
        "net_sharpe_range": [min(nets), max(nets)] if nets else None,
        "rule": prereg.NUISANCE_RULE,
    }


def _decomposition(daily: pd.DataFrame) -> dict[str, Any]:
    """判定 P&L の 4 行と、spot だけの値（前 cycle との比較用）。"""
    years = len(daily) / TRADING_DAYS
    return {
        "annual_spot_gross": round(float(daily["spot_gross"].sum() / years), 5),
        "annual_carry": round(float(daily["carry"].sum() / years), 5),
        "annual_spread_cost": round(float(daily["spread_cost"].sum() / years), 5),
        "annual_financing": round(float(daily["financing"].sum() / years), 5),
        "spot_only_gross_sharpe": round(_sharpe(daily["spot_gross"]), 4),
        "spot_only_net_sharpe": round(_sharpe(daily["spot_gross"] - daily["spread_cost"]), 4),
        "carry_sharpe_alone": round(_sharpe(daily["carry"]), 4),
    }


def run_track(
    track: str,
    span: str,
    built: dict[str, Any],
    *,
    workers: int = 1,
) -> dict[str, Any]:
    spec = prereg.TRACKS[track]
    excess = built[span]["currency_excess_return"]
    try:
        scores = signals.scores_for(track, built, span)
    except (signals.NonContiguousScoresError, signals.SignalUnavailableError) as error:
        return {
            "track": track,
            "span": span,
            "verdict": prereg.track_status(track, "DATA_NOT_DECISION_GRADE"),
            "why": str(error)[:300],
        }
    if scores.empty or len(scores) < 60:
        return {
            "track": track,
            "span": span,
            "verdict": prereg.track_status(track, "DATA_NOT_DECISION_GRADE"),
            "why": f"3 通貨以上の score がある decision day が {len(scores)} 日",
        }

    rates = carry_operator(
        signals.carry_rate_panel(excess.index), list(built[span]["pair_returns"].columns)
    )
    config = _config(track)
    daily = book(config, scores, excess, rates)
    metrics = _metrics(daily, scores, excess)
    control = _benchmarks(excess)["fx_own_momentum_20d"].reindex(scores.index)
    metrics["incremental_ic"] = _incremental_ic(scores, control, excess)
    metrics["signal_persistence_lag1"] = round(_lag_one_autocorrelation(scores), 4)
    metrics["detection_floor_mde95"] = round(float(1.96 / np.sqrt(len(scores) / TRADING_DAYS)), 4)
    metrics["effective_independent_observations"] = round(effective_observations(scores), 2)

    benches = {}
    for name, frame in _benchmarks(excess).items():
        usable = frame.reindex(scores.index).dropna(how="any")
        if usable.empty:
            continue
        bench_daily = book(config, usable, excess, rates)
        benches[name] = {
            "net_sharpe": _sharpe(bench_daily["net"]),
            "gross_sharpe": _sharpe(bench_daily["gross"]),
            "ic": _ic(usable, excess),
        }

    stressed = {}
    for multiple in prereg.COST["stress_multiples"][1:]:
        stress = book(dataclasses.replace(config, cost_multiple=multiple), scores, excess, rates)[
            "net"
        ]
        stressed[f"cost_x{multiple}"] = {
            "net_annual_return": float(stress.sum() / (len(stress) / TRADING_DAYS)),
            "net_sharpe": round(_sharpe(stress), 4),
        }

    is_primary = span == spec["primary_span"]
    out: dict[str, Any] = {
        "track": track,
        "span": span,
        "is_primary_span": is_primary,
        "book": "DOLLAR" if track in signals.DOLLAR_TRACKS else "XS",
        "metrics": metrics,
        "pnl_decomposition": _decomposition(daily),
        "benchmarks": benches,
        "cost_stress": stressed,
        "diagnostic_gate": _nf._diagnostic_triple(metrics),
        "capacity": _nf._capacity(metrics),
        "daily_net": daily["net"],
        "scores": scores,
    }
    if not is_primary and span == "long":
        out["cost_caveat"] = prereg.PRIMARY_SPAN_RULE["cost_caveat"]
    if is_primary:
        out["null_diagnostic"] = null_diagnostic(track, scores, excess, rates, workers=workers)
        out["development_economics"] = development_economics(track, metrics, stressed)
        eligible = _nf.stage2_eligible(out["development_economics"], out["null_diagnostic"])
        out["stage_2"] = (
            {"eligible": True, "regression": _nf.stage2_regression(scores, excess)}
            if eligible
            else {"eligible": False, "reason": prereg.STAGE_2_ELIGIBILITY["if_not_eligible"]}
        )
        out["nuisance_sensitivity"] = {
            name: _nuisance_sensitivity(track, span, built, name, rates)
            for name in prereg.NUISANCE_APPLIES[track]
        }
    return out


__all__ = [
    "book",
    "development_economics",
    "effective_observations",
    "null_diagnostic",
    "run_track",
    "verdict",
]
