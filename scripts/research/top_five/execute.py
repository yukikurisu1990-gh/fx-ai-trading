# ruff: noqa: E501 -- execution prose
"""凍結した 5 本を、凍結した枠組みで走らせる。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

**この module も判断をしない。** 走らせて測るだけで、閾値の解釈は報告側が行う。
5 本が同じ執行層・同じ cost 規約・同じ metric を通ることだけが、結果を同じ表に
並べてよい根拠である。

実行順は凍結どおり T1 -> T2 -> T3 -> T4 -> T5。**前の結果を後の設計に反映しない。**
"""

from __future__ import annotations

import dataclasses
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.continuous_portfolio import construction
from scripts.research.top_five import UNIVERSE, prereg, signals

TRADING_DAYS: Final[float] = 252.0

#: benchmark の lookback。凍結文の「FX own momentum 20d / mean reversion 20d」。
BENCH_LOOKBACK: Final[int] = 20


def _config(track: str, cost_multiple: float = 1.0) -> construction.BookConfig:
    """凍結した BookConfig。T5 だけ開示済みの逸脱を持つ。"""
    frozen = dict(prereg.BOOK_CONFIG)
    frozen.pop("days_per_year", None)
    frozen.pop("why_max_leverage_is_not_5", None)
    deviation = prereg.BOOK_CONFIG_DEVIATIONS.get(track, {})
    for key, value in deviation.items():
        if key in frozen:
            frozen[key] = value
    return construction.BookConfig(name=track, cost_multiple=cost_multiple, **frozen)


def _benchmarks(excess: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """zero signal / FX own momentum / simple mean reversion。"""
    momentum = excess.rolling(BENCH_LOOKBACK).sum()
    return {
        "zero_signal": pd.DataFrame(0.0, index=excess.index, columns=excess.columns),
        "fx_own_momentum_20d": momentum,
        "fx_own_mean_reversion_20d": -momentum,
    }


def _ic(scores: pd.DataFrame, excess: pd.DataFrame) -> float:
    """1 日先 return との日次 cross-section 相関の平均。"""
    forward = excess.shift(-1)
    both = scores.notna() & forward.notna()
    per_day = []
    for day in scores.index:
        row_s = scores.loc[day][both.loc[day]]
        row_f = forward.loc[day][both.loc[day]]
        if len(row_s) >= 3 and row_s.std() > 0 and row_f.std() > 0:
            per_day.append(float(np.corrcoef(row_s, row_f)[0, 1]))
    return float(np.mean(per_day)) if per_day else float("nan")


def _incremental_ic(scores: pd.DataFrame, control: pd.DataFrame, excess: pd.DataFrame) -> float:
    """control を除いた残差 score の IC。**FX 自身の価格情報を超える分**を測る。"""
    residual = pd.DataFrame(np.nan, index=scores.index, columns=scores.columns)
    for day in scores.index:
        s = scores.loc[day]
        c = control.loc[day]
        usable = s.notna() & c.notna()
        if usable.sum() < 3 or c[usable].std() == 0:
            continue
        beta = float(np.cov(s[usable], c[usable])[0, 1] / np.var(c[usable]))
        residual.loc[day, usable] = s[usable] - beta * c[usable]
    return _ic(residual, excess)


def _metrics(daily: pd.DataFrame, scores: pd.DataFrame, excess: pd.DataFrame) -> dict[str, Any]:
    """裁定 §20 の metric。event / 低頻度 track でも同じ形で出す。"""
    net = daily["net"]
    gross = daily["gross"]
    days = len(daily)
    if days == 0:
        return {"days": 0}
    years = days / TRADING_DAYS

    def _sharpe(series: pd.Series) -> float:
        sd = float(series.std(ddof=0))
        return float(series.mean() / sd * np.sqrt(TRADING_DAYS)) if sd > 0 else float("nan")

    equity = net.cumsum()
    drawdown = equity - equity.cummax()
    blocks = net.groupby(pd.Grouper(freq="QE")).sum()
    contributions = daily[[f"pnl_{c}" for c in UNIVERSE]].sum()
    sorted_days = net.sort_values(ascending=False)
    total_net = float(net.sum())

    def _share(n: int) -> float:
        return float(sorted_days.head(n).sum() / total_net) if total_net != 0 else float("nan")

    leave_one_out = {}
    for currency in UNIVERSE:
        without = net - daily[f"pnl_{currency}"]
        leave_one_out[currency] = _sharpe(without)

    return {
        "days": days,
        "years": round(years, 2),
        "gross_annual_return": float(gross.sum() / years),
        "net_annual_return": float(total_net / years),
        "gross_sharpe": _sharpe(gross),
        "net_sharpe": _sharpe(net),
        "realized_vol": float(net.std(ddof=0) * np.sqrt(TRADING_DAYS)),
        "ic": _ic(scores, excess),
        "turnover_round_trips_per_year": float(daily["one_way_traded"].sum() / 2.0 / years),
        "annual_cost": float(daily["cost"].sum() / years),
        "signal_persistence": float(
            scores.stack().groupby(level=1).apply(lambda s: s.autocorr()).mean()
        )
        if scores.notna().any().any()
        else float("nan"),
        "position_persistence": float(pd.concat([daily[f"x_{c}"] for c in UNIVERSE]).autocorr()),
        "max_drawdown": float(drawdown.min()),
        "positive_temporal_blocks": f"{int((blocks > 0).sum())}/{len(blocks)}",
        "currency_contribution": {c: float(contributions[f"pnl_{c}"]) for c in UNIVERSE},
        "leave_one_currency_out_net_sharpe": leave_one_out,
        "top_1_day_contribution": _share(1),
        "top_5_day_contribution": _share(5),
        "top_10_day_contribution": _share(10),
        "downside_tail_p05": float(net.quantile(0.05)),
        "temporal_concentration": float(blocks.abs().max() / blocks.abs().sum())
        if float(blocks.abs().sum()) > 0
        else float("nan"),
        "raw_to_neutralised_score_corr": float(daily["raw_target_corr"].mean()),
        "factor_abs_cosine": float(daily["factor_abs_cosine"].mean()),
        "portfolio_gross_leverage": float(daily["currency_gross"].mean()),
        "risk_leverage": float(daily["leverage"].mean()),
        "at_leverage_cap_share": float(daily["at_leverage_cap"].mean()),
    }


def _margin_utilisation(portfolio_gross: float) -> float:
    """pair 別 margin の最悪値で見た利用率。broker 仕様のみを使う。"""
    worst_margin_rate = 1.0 / float(prereg.BOOK_CONFIG["max_leverage"])
    return portfolio_gross * worst_margin_rate


def _capacity(net_sharpe: float, realized_vol: float) -> dict[str, Any]:
    """年 5% / 10% net に必要な target vol・risk leverage・margin 利用率。

    **broker ceiling を hurdle にしない。** 実測 net Sharpe から、realistic な
    target risk で年間 return へ変換できるかを見る（裁定 §26-§28）。
    """
    if not np.isfinite(net_sharpe) or net_sharpe <= 0:
        return {"reachable": False, "why": "net Sharpe が 0 以下なので leverage で救わない"}
    vol_per_unit = 0.023288  # capacity.VOL_PER_UNIT_GROSS
    out: dict[str, Any] = {"reachable": True, "scenarios": {}}
    for target in prereg.LEVERAGE_FRAMEWORK["standard_target_vol_scenarios"]:
        out["scenarios"][f"vol_{target:.0%}"] = {
            "annual_net": round(net_sharpe * target, 4),
            "risk_leverage": round(target / vol_per_unit, 2),
            "margin_utilisation": round(target / vol_per_unit * 0.05, 3),
        }
    for goal in (0.05, 0.10):
        needed_vol = goal / net_sharpe
        out[f"for_{goal:.0%}_annual_net"] = {
            "required_target_vol": round(needed_vol, 4),
            "risk_leverage": round(needed_vol / vol_per_unit, 2),
            "margin_utilisation": round(needed_vol / vol_per_unit * 0.05, 3),
            "within_broker_ceiling": bool(
                needed_vol / vol_per_unit <= prereg.BOOK_CONFIG["max_leverage"]
            ),
        }
    return out


def run_track(
    track: str, span: str, built: dict, *, hypothesis: str | None = None
) -> dict[str, Any]:
    """1 本 1 span を走らせて測る。"""
    excess = built[span]["currency_excess_return"]
    index = excess.index

    if track == "T1":
        scores = signals.t1_scores(index, span)
    elif track == "T2":
        scores = signals.t2_scores(index, span)
    elif track == "T3":
        scores = signals.t3_scores(index, span, hypothesis=hypothesis or "T3-H1")
    elif track == "T4":
        scores, _ = signals.t4_scores(excess)
    elif track == "T5":
        scores = signals.t5_scores(index)
    else:  # pragma: no cover
        raise ValueError(track)

    usable = scores.dropna(how="any")
    if len(usable) < 60:
        return {
            "track": track,
            "span": span,
            "days": len(usable),
            "verdict": "DATA_NOT_DECISION_GRADE",
        }
    #: `run_book` は decision day が return calendar 上で連続であることを要求する
    contiguous = index[index.get_loc(usable.index[0]) : index.get_loc(usable.index[-1]) + 1]
    scores = scores.reindex(contiguous).ffill().dropna(how="any")

    result = construction.run_book(_config(track), scores, excess, TRADING_DAYS)
    daily = result["daily"]
    metrics = _metrics(daily, scores, excess)

    benches = {}
    for name, bench in _benchmarks(excess).items():
        bench_usable = bench.reindex(scores.index)
        if name == "zero_signal":
            benches[name] = {"net_sharpe": 0.0, "ic": 0.0}
            continue
        bench_result = construction.run_book(
            _config(track), bench_usable.dropna(how="any"), excess, TRADING_DAYS
        )
        bench_daily = bench_result["daily"]
        sd = float(bench_daily["net"].std(ddof=0))
        benches[name] = {
            "net_sharpe": float(bench_daily["net"].mean() / sd * np.sqrt(TRADING_DAYS))
            if sd > 0
            else float("nan"),
            "ic": _ic(bench_usable, excess),
        }

    control = _benchmarks(excess)["fx_own_momentum_20d"].reindex(scores.index)
    metrics["incremental_ic"] = _incremental_ic(scores, control, excess)

    stressed = {}
    for multiple in prereg.COST["stress_multiples"][1:]:
        stress_result = construction.run_book(
            dataclasses.replace(_config(track), cost_multiple=multiple),
            scores,
            excess,
            TRADING_DAYS,
        )
        net = stress_result["daily"]["net"]
        sd = float(net.std(ddof=0))
        stressed[f"cost_x{multiple}"] = {
            "net_annual_return": float(net.sum() / (len(net) / TRADING_DAYS)),
            "net_sharpe": float(net.mean() / sd * np.sqrt(TRADING_DAYS))
            if sd > 0
            else float("nan"),
        }

    return {
        "track": track,
        "candidate": prereg.TRACKS[track]["candidate"],
        "span": span,
        "hypothesis": hypothesis,
        "metrics": metrics,
        "benchmarks": benches,
        "cost_stress": stressed,
        "margin_utilisation_at_run": _margin_utilisation(metrics["portfolio_gross_leverage"]),
        "capacity": _capacity(metrics["net_sharpe"], metrics["realized_vol"]),
        "daily_net": daily["net"],
    }


__all__ = ["BENCH_LOOKBACK", "TRADING_DAYS", "run_track"]
