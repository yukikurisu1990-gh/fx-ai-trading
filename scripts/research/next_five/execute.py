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
    "TRADING_DAYS",
    "permutation_gate",
    "run_track",
]


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
        out[f"for_{goal:.0%}_annual_net"] = row
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


def permutation_gate(
    track: str, scores: pd.DataFrame, excess: pd.DataFrame, *, draws: int | None = None
) -> dict[str, Any]:
    """**進行を決める hard gate**（裁定 §G）。

    零情報の circular shift を引いて、実測の net Sharpe がその分布のどこにいるかを測る。
    3 条件 triple と違い、**この gate は帰無で 5% しか通らない**（構成上）。
    """
    spec = prereg.ADVANCE_GATE["permutation"]
    count = draws if draws is not None else int(spec["draws"])
    rng = np.random.default_rng(int(spec["seed"]))
    config = _config(track)

    observed = construction.run_book(config, scores, excess, TRADING_DAYS)["daily"]
    observed_sharpe = _sharpe(observed["net"])
    observed_annual = float(observed["net"].sum() / (len(observed["net"]) / TRADING_DAYS))
    persistence = _lag_one_autocorrelation(scores)

    drawn: list[float] = []
    length = len(scores)
    for _ in range(count):
        shift = int(rng.integers(1, max(length, 2)))
        shifted = _circular_shift(scores, shift)
        drawn_persistence = _lag_one_autocorrelation(shifted)
        if np.isfinite(persistence) and abs(drawn_persistence - persistence) >= 0.05:
            raise AssertionError(
                f"帰無が signal の自己相関を壊した（{persistence:.3f} -> {drawn_persistence:.3f}）。"
                "circular shift ではなく shuffle になっていないか"
            )
        drawn.append(
            _sharpe(construction.run_book(config, shifted, excess, TRADING_DAYS)["daily"]["net"])
        )

    array = np.array([value for value in drawn if np.isfinite(value)])
    p_value = float((array >= observed_sharpe).sum() + 1) / float(len(array) + 1)
    passed = bool(observed_annual > 0 and p_value <= 0.05)
    return {
        "gate": prereg.ADVANCE_GATE["id"],
        "draws": count,
        "seed": int(spec["seed"]),
        "observed_net_sharpe": round(observed_sharpe, 4),
        "observed_net_annual_return": round(observed_annual, 5),
        "p_value": round(p_value, 4),
        "null_net_sharpe_mean": round(float(array.mean()), 4),
        "null_net_sharpe_p95": round(float(np.percentile(array, 95)), 4),
        "signal_persistence_lag1": None if not np.isfinite(persistence) else round(persistence, 4),
        "passed": passed,
        "multiplicity_note": prereg.ADVANCE_GATE["multiplicity"],
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
        "reading": "**通ったこと自体は情報が薄い。** 進行は permutation gate が決める",
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
        try:
            scores = signals.scores_for(track, built, span, overrides={name: value})
        except signals.SignalUnavailableError as error:
            grid[str(value)] = {"status": f"UNAVAILABLE: {error}"[:120]}
            continue
        if scores.empty:
            grid[str(value)] = {"status": "NO_USABLE_DAYS"}
            continue
        daily = construction.run_book(config, scores, excess, TRADING_DAYS)["daily"]
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
    track: str, span: str, built: dict[str, Any], *, permutation_draws: int | None = None
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
            "why": f"連続 decision day が {len(scores)} 日しかない",
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
        out["advance_gate"] = permutation_gate(track, scores, excess, draws=permutation_draws)
    return out
