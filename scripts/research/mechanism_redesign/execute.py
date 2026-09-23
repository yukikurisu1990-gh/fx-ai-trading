# ruff: noqa: E501 -- execution prose
"""mechanism redesign cycle の実行層。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**統計は next-five と同じ関数を import して使う**（指標・development economics・Stage 2 適格・
capacity・降格 gate）。book の設定（ドル track の deviation）と track の名前だけがこの cycle のもの。
"""

from __future__ import annotations

import dataclasses
from typing import Any

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


def _config(
    track: str, cost_multiple: float = 1.0, band: float | None = None
) -> construction.BookConfig:
    frozen = {k: v for k, v in prereg.BOOK_CONFIG.items() if not k.startswith("why_")}
    frozen.pop("days_per_year", None)
    frozen.update(prereg.BOOK_CONFIG_DEVIATIONS.get(track, {}))
    if band is not None:
        frozen["band"] = band
    return construction.BookConfig(name=track, cost_multiple=cost_multiple, **frozen)


def _draw_chunk(job: tuple[str, pd.DataFrame, pd.DataFrame, list[int], float]) -> list[float]:
    track, scores, excess, shifts, persistence = job
    config = _config(track)
    out: list[float] = []
    for shift in shifts:
        shifted = _circular_shift(scores, shift)
        drawn = _lag_one_autocorrelation(shifted)
        if np.isfinite(persistence) and abs(drawn - persistence) >= 0.05:
            raise AssertionError("帰無が signal の自己相関を壊した")
        out.append(
            _sharpe(construction.run_book(config, shifted, excess, TRADING_DAYS)["daily"]["net"])
        )
    return out


def null_diagnostic(
    track: str,
    scores: pd.DataFrame,
    excess: pd.DataFrame,
    *,
    draws: int | None = None,
    workers: int = 1,
) -> dict[str, Any]:
    spec = prereg.NULL_DIAGNOSTIC["permutation"]
    count = draws if draws is not None else int(spec["draws"])
    rng = np.random.default_rng(int(spec["seed"]))
    observed = construction.run_book(_config(track), scores, excess, TRADING_DAYS)["daily"]
    observed_sharpe = _sharpe(observed["net"])
    observed_annual = float(observed["net"].sum() / (len(observed["net"]) / TRADING_DAYS))
    persistence = _lag_one_autocorrelation(scores)
    shifts = [int(rng.integers(1, max(len(scores), 2))) for _ in range(count)]
    if workers <= 1:
        drawn = _draw_chunk((track, scores, excess, shifts, persistence))
    else:
        from concurrent.futures import ProcessPoolExecutor

        size = max(1, -(-len(shifts) // workers))
        jobs = [
            (track, scores, excess, shifts[i : i + size], persistence)
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


def verdict(
    track: str, primary: dict[str, Any], other: dict[str, Any] | None, renamed: bool
) -> dict[str, Any]:
    """凍結した VERDICT_LOGIC を上から当てる（next-five と同じ規則）。"""
    metrics = primary["metrics"]
    economics = primary["development_economics"]
    null = primary["null_diagnostic"]
    gross, net = float(metrics["gross_sharpe"]), float(metrics["net_sharpe"])
    other_sign = None
    if other and "metrics" in other:
        other_sign = "positive" if float(other["metrics"]["gross_sharpe"]) > 0 else "non_positive"
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
    return {
        "status": prereg.track_status(track, suffix),
        "failure_class": failure,
        "null_label": null["label"],
        "economics_label": economics["label"],
        "other_span_gross_sign": other_sign,
    }


def _nuisance_sensitivity(
    track: str, span: str, built: dict[str, Any], name: str
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
        daily = construction.run_book(_config(track, band=band), scores, excess, TRADING_DAYS)[
            "daily"
        ]
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


def run_track(
    track: str,
    span: str,
    built: dict[str, Any],
    *,
    permutation_draws: int | None = None,
    workers: int = 1,
) -> dict[str, Any]:
    spec = prereg.TRACKS[track]
    excess = built[span]["currency_excess_return"]
    try:
        scores = signals.scores_for(track, built, span)
    except signals.NonContiguousScoresError as error:
        return {
            "track": track,
            "span": span,
            "verdict": prereg.track_status(track, "DATA_NOT_DECISION_GRADE"),
            "why": str(error)[:300],
        }
    except signals.SignalUnavailableError as error:
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

    config = _config(track)
    daily = construction.run_book(config, scores, excess, TRADING_DAYS)["daily"]
    metrics = _metrics(daily, scores, excess)
    control = _benchmarks(excess)["fx_own_momentum_20d"].reindex(scores.index)
    metrics["incremental_ic"] = _incremental_ic(scores, control, excess)
    metrics["signal_persistence_lag1"] = round(_lag_one_autocorrelation(scores), 4)
    metrics["detection_floor_mde95"] = round(float(1.96 / np.sqrt(len(scores) / TRADING_DAYS)), 4)

    benches = {}
    for name, frame in _benchmarks(excess).items():
        usable = frame.reindex(scores.index).dropna(how="any")
        if usable.empty:
            continue
        bench_daily = construction.run_book(config, usable, excess, TRADING_DAYS)["daily"]
        benches[name] = {
            "net_sharpe": _sharpe(bench_daily["net"]),
            "gross_sharpe": _sharpe(bench_daily["gross"]),
            "ic": _ic(usable, excess),
        }

    stressed = {}
    for multiple in prereg.COST["stress_multiples"][1:]:
        stress = construction.run_book(
            dataclasses.replace(config, cost_multiple=multiple), scores, excess, TRADING_DAYS
        )["daily"]["net"]
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
        out["null_diagnostic"] = null_diagnostic(
            track, scores, excess, draws=permutation_draws, workers=workers
        )
        out["development_economics"] = development_economics(track, metrics, stressed)
        eligible = _nf.stage2_eligible(out["development_economics"], out["null_diagnostic"])
        out["stage_2"] = (
            {"eligible": True, "regression": _nf.stage2_regression(scores, excess)}
            if eligible
            else {"eligible": False, "reason": prereg.STAGE_2_ELIGIBILITY["if_not_eligible"]}
        )
        out["nuisance_sensitivity"] = {
            name: _nuisance_sensitivity(track, span, built, name)
            for name in prereg.NUISANCE_APPLIES[track]
        }
    return out


__all__ = ["development_economics", "null_diagnostic", "run_track", "verdict"]
