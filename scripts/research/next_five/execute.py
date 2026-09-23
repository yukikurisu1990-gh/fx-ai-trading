# ruff: noqa: E501 -- execution prose
"""次の 5 本の実行層（2026-09-22 裁定 §K / §L）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**統計の中身は前 cycle と同じものを import して使う。** 自分で書き直すと、
2 つの cycle の数字が比較できなくなる。比較できることがこの枠組みの目的である。

新しいのは 2 つだけ。

1. **進行を決めるのは permutation gate** である（裁定 §G）。3 条件 triple は
   `diagnostic` として併記するが、**それを根拠に進まない**。
2. **nuisance 定数の感度を毎回まとめて出す**（裁定 §H）。primary で判定し、
   事前登録した集合の全点を報告する。**良い点を選ばない。**
"""

from __future__ import annotations

import dataclasses
from typing import Any

import numpy as np
import pandas as pd

from scripts.research.continuous_portfolio import construction
from scripts.research.next_five import prereg, signals
from scripts.research.top_five.execute import (
    BENCH_LOOKBACK,
    TRADING_DAYS,
    _benchmarks,
    _ic,
    _incremental_ic,
    _metrics,
)

__all__ = [
    "BENCH_LOOKBACK",
    "NUISANCE_APPLIES",
    "TRADING_DAYS",
    "development_economics",
    "null_diagnostic",
    "run_track",
    "stage2_eligible",
    "verdict",
]

#: 各 track の signal 定義が実際に使う nuisance 定数。**signal の式から機械的に決まる**
#: （U4 の 3 か月変化と U5 の 5 日変化は機構側の定数で、nuisance ではない）。
NUISANCE_APPLIES: dict[str, tuple[str, ...]] = {
    "U1": (
        "max_staleness_days",
        "z_window",
        "change_window_months",
        "implementation_tolerance_band",
    ),
    "U2": (
        "max_staleness_days",
        "z_window",
        "change_window_months",
        "implementation_tolerance_band",
    ),
    "U3": ("max_staleness_days", "z_window", "implementation_tolerance_band"),
    "U4": ("max_staleness_days", "z_window", "implementation_tolerance_band"),
    "U5": ("max_staleness_days", "z_window", "implementation_tolerance_band"),
}


def _config(track: str, cost_multiple: float = 1.0) -> construction.BookConfig:
    frozen = {k: v for k, v in prereg.BOOK_CONFIG.items() if not k.startswith("why_")}
    frozen.pop("days_per_year", None)
    frozen.update(prereg.BOOK_CONFIG_DEVIATIONS.get(track, {}))
    return construction.BookConfig(name=track, cost_multiple=cost_multiple, **frozen)


def _margin_utilisation(portfolio_gross: float) -> float:
    return portfolio_gross / float(prereg.BOOK_CONFIG["max_leverage"])


def _capacity(metrics: dict[str, Any]) -> dict[str, Any]:
    """年 5% / 10% net に必要な risk と、その代償（裁定 §L）。

    **margin は portfolio gross に課される。** risk leverage に掛けない
    （前 cycle でそこを取り違えた記録が残っている）。
    """
    net_sharpe = metrics["net_sharpe"]
    if not np.isfinite(net_sharpe) or net_sharpe <= 0:
        return {"reachable": False, "why": "net Sharpe が 0 以下なので leverage で救わない"}

    realized_vol = float(metrics["realized_vol"])
    gross = float(metrics["portfolio_gross_leverage"])
    vol_per_unit = realized_vol / gross if gross > 0 else float("nan")
    worst_margin_rate = 1.0 / float(prereg.BOOK_CONFIG["max_leverage"])
    observed_dd = float(metrics["max_drawdown"])

    def _at(target_vol: float) -> dict[str, Any]:
        scale = target_vol / realized_vol if realized_vol > 0 else float("nan")
        gross_needed = gross * scale
        return {
            "annual_net": round(net_sharpe * target_vol, 4),
            "portfolio_gross": round(gross_needed, 2),
            "risk_leverage": round(scale * gross, 2),
            "pair_specific_margin": round(gross_needed * worst_margin_rate, 3),
            "remaining_margin_buffer": round(1.0 - gross_needed * worst_margin_rate, 3),
            "scaled_max_drawdown": round(observed_dd * scale, 4),
            "gap_stress_2pct_adverse": round(-0.02 * gross_needed, 4),
        }

    out: dict[str, Any] = {
        "reachable": True,
        "vol_per_unit_gross_measured": round(vol_per_unit, 5),
        "scenarios": {
            f"vol_{target:.0%}": _at(target)
            for target in prereg.CAPACITY_REPORTING["target_vol_scenarios"]
        },
        "forbidden": list(prereg.CAPACITY_REPORTING["forbidden"]),
    }
    for goal in prereg.CAPACITY_REPORTING["annual_return_targets"]:
        needed_vol = goal / net_sharpe
        row = _at(needed_vol)
        row["required_target_vol"] = round(needed_vol, 4)
        #: 必要な gross が book の上限を超えるなら、その目標には届かない（Role 1 O-4）
        row["within_max_leverage"] = bool(
            row["portfolio_gross"] <= float(prereg.BOOK_CONFIG["max_leverage"])
        )
        out[f"for_{goal:.0%}_annual_net"] = row
    out["reachable"] = any(
        out[f"for_{goal:.0%}_annual_net"]["within_max_leverage"]
        for goal in prereg.CAPACITY_REPORTING["annual_return_targets"]
    )
    return out


def _sharpe(series: pd.Series) -> float:
    sd = float(series.std(ddof=0))
    return float(series.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else float("nan")


def _circular_shift(scores: pd.DataFrame, shift: int) -> pd.DataFrame:
    """**行の並びを保ったまま**巡回させる。shuffle ではない。"""
    return pd.DataFrame(
        np.roll(scores.to_numpy(), shift, axis=0), index=scores.index, columns=scores.columns
    )


def _lag_one_autocorrelation(frame: pd.DataFrame) -> float:
    values = frame.to_numpy(dtype=float)
    current, following = values[:-1].ravel(), values[1:].ravel()
    usable = np.isfinite(current) & np.isfinite(following)
    if usable.sum() < 3 or current[usable].std() == 0 or following[usable].std() == 0:
        return float("nan")
    return float(np.corrcoef(current[usable], following[usable])[0, 1])


def _draw_chunk(job: tuple[str, pd.DataFrame, pd.DataFrame, list[int], float]) -> list[float]:
    """1 つの worker が受け持つ shift 群。**module の top level に置く**（process 並列で pickle するため）。"""
    track, scores, excess, shifts, persistence = job
    config = _config(track)
    out: list[float] = []
    for shift in shifts:
        shifted = _circular_shift(scores, shift)
        drawn_persistence = _lag_one_autocorrelation(shifted)
        if np.isfinite(persistence) and abs(drawn_persistence - persistence) >= 0.05:
            raise AssertionError(
                f"帰無が signal の自己相関を壊した（{persistence:.3f} -> {drawn_persistence:.3f}）。"
                "circular shift ではなく shuffle になっていないか"
            )
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
    """**null 診断**（第 2 裁定 §1 / §32）。判定の材料の 1 つであって、唯一の gate ではない。

    零情報の circular shift を引いて、実測の net Sharpe がその分布のどこにいるかを測る。
    **shift の列は並列化の前に 1 本の乱数列から決める**ので、worker 数を変えても結果は同じ。
    """
    spec = prereg.NULL_DIAGNOSTIC["permutation"]
    count = draws if draws is not None else int(spec["draws"])
    rng = np.random.default_rng(int(spec["seed"]))
    config = _config(track)

    observed = construction.run_book(config, scores, excess, TRADING_DAYS)["daily"]
    observed_sharpe = _sharpe(observed["net"])
    observed_annual = float(observed["net"].sum() / (len(observed["net"]) / TRADING_DAYS))
    persistence = _lag_one_autocorrelation(scores)

    length = len(scores)
    shifts = [int(rng.integers(1, max(length, 2))) for _ in range(count)]
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
            drawn = [value for chunk in pool.map(_draw_chunk, jobs) for value in chunk]

    array = np.array([value for value in drawn if np.isfinite(value)])
    exceed = int((array >= observed_sharpe).sum())
    p_value = float(exceed + 1) / float(len(array) + 1)
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
        "signal_persistence_lag1": None if not np.isfinite(persistence) else round(persistence, 4),
        "label": "NULL_REJECTION_SUPPORTED" if rejected else "NULL_REJECTION_NOT_SUPPORTED",
        "multiplicity_note": prereg.NULL_DIAGNOSTIC["multiplicity"],
    }


def _blocks_share(text: Any) -> float:
    try:
        good, total = (int(part) for part in str(text).split("/"))
        return good / total if total else float("nan")
    except (ValueError, TypeError):
        return float("nan")


def development_economics(metrics: dict[str, Any], stressed: dict[str, Any]) -> dict[str, Any]:
    """**凍結した development economics**（第 2 裁定 §1）。primary span の値で判定する。"""
    loo = metrics.get("leave_one_currency_out_net_sharpe") or {}
    worst_loo = min(loo.values()) if loo else float("nan")
    top10 = metrics.get("top_10_day_contribution", float("nan"))
    cost_x2 = (stressed.get("cost_x2.0") or {}).get("net_sharpe", float("nan"))
    net = float(metrics["net_sharpe"])
    checks = {
        "E1_net_positive": bool(net > 0),
        "E2_gross_positive": bool(float(metrics["gross_sharpe"]) > 0),
        "E3_incremental_information": bool(float(metrics["incremental_ic"]) > 0),
        "E4_temporal_stability": bool(
            _blocks_share(metrics.get("positive_temporal_blocks")) >= 0.5
        ),
        "E5_breadth": bool(np.isfinite(worst_loo) and worst_loo > 0),
        #: net が負のときは寄与の符号が反転して意味を持たないので偽とする
        "E6_concentration": bool(net > 0 and np.isfinite(top10) and top10 <= 0.5),
        "E7_cost_robustness": bool(np.isfinite(cost_x2) and cost_x2 > 0),
        "E8_economic_magnitude": bool(net >= 0.30),
    }
    core = all(checks[name] for name in prereg.DEVELOPMENT_ECONOMICS["core"])
    return {
        "checks": checks,
        "evidence": {
            "worst_leave_one_currency_out_net_sharpe": (
                None if not np.isfinite(worst_loo) else round(worst_loo, 4)
            ),
            "top_10_day_contribution": None if not np.isfinite(top10) else round(float(top10), 4),
            "cost_x2_net_sharpe": None if not np.isfinite(cost_x2) else round(float(cost_x2), 4),
            "positive_temporal_blocks": metrics.get("positive_temporal_blocks"),
        },
        "core_satisfied": core,
        "label": (
            "DEVELOPMENT_ECONOMICS_SUPPORTED"
            if all(checks.values())
            else "DEVELOPMENT_ECONOMICS_NOT_SUPPORTED"
        ),
    }


def stage2_eligible(economics: dict[str, Any], null: dict[str, Any]) -> bool:
    """凍結した Stage 2 適格条件。**p ≤ 0.05 を唯一条件にしない。**"""
    return bool(economics["core_satisfied"] and float(null["observed_percentile"]) >= 0.80)


def stage2_regression(scores: pd.DataFrame, excess: pd.DataFrame) -> dict[str, Any]:
    """凍結が許す唯一の model: forward ~ 1 + signal + control（前 cycle と同じ実装）。"""
    from scripts.research.top_five.stage2 import _regression

    control = _benchmarks(excess)["fx_own_momentum_20d"].reindex(scores.index)
    return _regression(scores, control, excess)


def verdict(
    track: str,
    primary: dict[str, Any],
    other: dict[str, Any] | None,
    rename_gate: dict[str, Any] | None,
) -> dict[str, Any]:
    """**凍結した VERDICT_LOGIC を上から順に当てる。** 結果を見た後に変えない。

    p > 0.05 は NOT_SUPPORTED の理由にならない（NOT_SUPPORTED は net ≤ 0 のときだけ）。
    """
    metrics = primary["metrics"]
    economics = primary["development_economics"]
    null = primary["null_diagnostic"]
    gross = float(metrics["gross_sharpe"])
    net = float(metrics["net_sharpe"])
    other_sign = None
    if other and "metrics" in other:
        other_sign = "positive" if float(other["metrics"]["gross_sharpe"]) > 0 else "non_positive"

    failure: str | None = None
    if rename_gate and rename_gate.get("verdict") == "RENAME":
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


def _diagnostic_triple(metrics: dict[str, Any]) -> dict[str, Any]:
    """**降格された gate**（裁定 §G）。報告はするが、これを根拠に進まない。"""
    checks = {
        "gross_sharpe_positive": float(metrics["gross_sharpe"]) > 0,
        "incremental_ic_positive": float(metrics["incremental_ic"]) > 0,
        "net_annual_return_positive": float(metrics["net_annual_return"]) > 0,
    }
    return {
        "id": prereg.DEMOTED_GATE["id"],
        "status": prereg.DEMOTED_GATE["status"],
        "checks": checks,
        "all_three": all(checks.values()),
        "null_pass_rate_measured_at_freeze": prereg.DEMOTED_GATE["measured_null_pass_rate"],
        "reading": "**通ったこと自体は情報が薄い。** 判定は VERDICT_LOGIC が決める",
    }


def _nuisance_sensitivity(
    track: str, span: str, built: dict[str, Any], name: str
) -> dict[str, Any]:
    """凍結した感度集合の**全点**を報告する（裁定 §H）。best point は選ばない。"""
    spec = prereg.NUISANCE_CONSTANTS[name]
    excess = built[span]["currency_excess_return"]
    config = _config(track)
    original = spec["primary"]
    grid: dict[str, Any] = {}
    for value in spec["sensitivity_set"]:
        run_config = config
        overrides: dict[str, Any] | None = {name: value}
        if name == "implementation_tolerance_band":
            #: 執行側の定数。signal ではなく book の band を動かす
            run_config = dataclasses.replace(config, band=float(value))
            overrides = None
        try:
            scores = signals.scores_for(track, built, span, overrides=overrides)
        except signals.SignalUnavailableError as error:
            grid[str(value)] = {"status": f"UNAVAILABLE: {error}"[:120]}
            continue
        if scores.empty:
            grid[str(value)] = {"status": "NO_USABLE_DAYS"}
            continue
        daily = construction.run_book(run_config, scores, excess, TRADING_DAYS)["daily"]
        grid[str(value)] = {
            "days": int(len(scores)),
            "net_sharpe": round(_sharpe(daily["net"]), 4),
            "gross_sharpe": round(_sharpe(daily["gross"]), 4),
        }
    nets = [row["net_sharpe"] for row in grid.values() if "net_sharpe" in row]
    return {
        "constant": name,
        "primary": original,
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
    """1 本を 1 つの span で走らせる。**gate は判定するが、救済はしない。**"""
    spec = prereg.TRACKS[track]
    excess = built[span]["currency_excess_return"]

    try:
        scores = signals.scores_for(track, built, span)
    except signals.SignalUnavailableError as error:
        #: **Stage 0 が既に原因を分類している。** 「到達できない」と「存在しない」を
        #: 混ぜないために、token は凍結記録から取る。
        stage0 = prereg.STAGE_0_OUTCOME["per_track"].get(track, {})
        return {
            "track": track,
            "candidate": spec["candidate"],
            "span": span,
            "verdict": prereg.track_status(
                track, stage0.get("status", "DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES")
            ),
            "why": str(error)[:300],
            "stage_0": stage0,
        }
    if scores.empty or len(scores) < 60:
        return {
            "track": track,
            "candidate": spec["candidate"],
            "span": span,
            "verdict": prereg.track_status(track, "DATA_NOT_DECISION_GRADE"),
            "why": f"3 通貨以上の score がある decision day が {len(scores)} 日しかない",
        }

    config = _config(track)
    result = construction.run_book(config, scores, excess, TRADING_DAYS)
    daily = result["daily"]
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
        "candidate": spec["candidate"],
        "span": span,
        "is_primary_span": is_primary,
        "metrics": metrics,
        "benchmarks": benches,
        "cost_stress": stressed,
        "diagnostic_gate": _diagnostic_triple(metrics),
        "margin_utilisation_at_run": _margin_utilisation(metrics["portfolio_gross_leverage"]),
        "capacity": _capacity(metrics),
        "daily_net": daily["net"],
        "scores": scores,
    }
    if not is_primary and span == "long":
        out["cost_caveat"] = prereg.PRIMARY_SPAN_RULE["cost_caveat"]
    if is_primary:
        out["null_diagnostic"] = null_diagnostic(
            track, scores, excess, draws=permutation_draws, workers=workers
        )
        out["development_economics"] = development_economics(metrics, stressed)
        eligible = stage2_eligible(out["development_economics"], out["null_diagnostic"])
        out["stage_2"] = (
            {"eligible": True, "regression": stage2_regression(scores, excess)}
            if eligible
            else {"eligible": False, "reason": prereg.STAGE_2_ELIGIBILITY["if_not_eligible"]}
        )
        out["nuisance_sensitivity"] = {
            name: _nuisance_sensitivity(track, span, built, name)
            for name in prereg.NUISANCE_CONSTANTS
            if name in NUISANCE_APPLIES.get(track, ())
        }
    return out
