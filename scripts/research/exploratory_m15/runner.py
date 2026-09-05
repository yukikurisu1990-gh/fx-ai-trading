"""Run a registry of strategies over the cached corpus. Exploratory only.

`NON_DECISION_BEARING_EXPLORATORY_ONLY`.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import engine


def _pooled(
    per_pair: list[engine.Result],
    name: str,
    cost_multiplier: float,
    timestamps: dict[str, pd.Series] | None = None,
) -> dict[str, Any]:
    """Equal-weight across pairs, on a shared **timestamp** line.

    A first drafting concatenated the per-pair series by row number. Pair bar
    counts differ (16,710 to 16,796 over this span, because a thin pair is
    missing whole buckets), so row *i* was a different instant for different
    pairs and the pooled series mixed times. A review role found it. Aligning on
    `ts` is the fix; the per-pair metrics were never affected, only the pooled
    aggregate and anything derived from it.
    """
    if timestamps is not None:
        columns = [
            result.net.set_axis(timestamps[result.pair]).rename(result.pair) for result in per_pair
        ]
    else:
        columns = [result.net.rename(result.pair) for result in per_pair]
    frame = pd.concat(columns, axis=1).fillna(0.0)
    pooled_net = frame.mean(axis=1)
    equity = pooled_net.cumsum()
    drawdown = equity - equity.cummax()
    std = float(pooled_net.std())
    by_pair = {r.pair: r.metrics["net_pips"] for r in per_pair}
    total_abs = sum(abs(v) for v in by_pair.values()) or 1.0
    best = max(by_pair, key=by_pair.get)
    return {
        "strategy": name,
        "cost_multiplier": cost_multiplier,
        "pooled_net_pips_per_pair": float(pooled_net.sum()),
        "pooled_sharpe_like": float(pooled_net.mean() / std * np.sqrt(engine.BARS_PER_YEAR))
        if std > 0
        else 0.0,
        "pooled_max_drawdown_pips": float(drawdown.min()),
        "pairs_positive": int(sum(1 for v in by_pair.values() if v > 0)),
        "pairs": len(by_pair),
        "total_trades": int(sum(r.metrics["trades"] for r in per_pair)),
        "total_closed_trades": int(sum(r.metrics["n_closed_trades"] for r in per_pair)),
        "mean_win_rate": float(np.nanmean([r.metrics["win_rate"] for r in per_pair])),
        "mean_profit_factor": float(np.nanmedian([r.metrics["profit_factor"] for r in per_pair])),
        "mean_avg_trade_pips": float(np.nanmean([r.metrics["avg_trade_pips"] for r in per_pair])),
        "mean_turnover_per_year": float(
            np.mean([r.metrics["turnover_per_year"] for r in per_pair])
        ),
        "top_pair_share_of_abs_pnl": float(abs(by_pair[best]) / total_abs),
        "top_pair": best,
        "gross_pips_per_pair": float(np.mean([r.metrics["gross_pips"] for r in per_pair])),
        "cost_pips_per_pair": float(np.mean([r.metrics["cost_pips"] for r in per_pair])),
        "net_by_pair": {k: round(v, 1) for k, v in sorted(by_pair.items())},
    }


def run_registry(
    registry: dict[str, tuple],
    pairs,
    *,
    cost_multipliers=engine.COST_MULTIPLIERS,
    session_breakdown: bool = True,
) -> dict[str, Any]:
    loaded = {pair: bars_module.load(pair) for pair in pairs}
    rows: list[dict[str, Any]] = []
    pooled_rows: list[dict[str, Any]] = []
    sessions: list[dict[str, Any]] = []
    stability_rows: list[dict[str, Any]] = []

    for name, (function, kwargs) in registry.items():
        signals = {pair: function(frame, **kwargs) for pair, frame in loaded.items()}
        for multiplier in cost_multipliers:
            results = [
                engine.evaluate(
                    loaded[pair], signals[pair], name=name, pair=pair, cost_multiplier=multiplier
                )
                for pair in pairs
            ]
            rows.extend(result.metrics for result in results)
            pooled_rows.append(
                _pooled(
                    results,
                    name,
                    multiplier,
                    timestamps={pair: loaded[pair]["ts"] for pair in pairs},
                )
            )
            if multiplier == 1.0:
                pooled_net = (
                    pd.concat(
                        [r.net.set_axis(loaded[r.pair]["ts"]).rename(r.pair) for r in results],
                        axis=1,
                    )
                    .fillna(0.0)
                    .mean(axis=1)
                )
                stability_rows.append(
                    {
                        "strategy": name,
                        **engine.stability(pooled_net, loaded[pairs[0]]["ts"]),
                    }
                )
                if session_breakdown:
                    for pair, result in zip(pairs, results, strict=True):
                        frame = loaded[pair]
                        for session in ("asia", "europe", "us"):
                            mask = (frame["session"] == session).to_numpy()
                            sessions.append(
                                {
                                    "strategy": name,
                                    "pair": pair,
                                    "session": session,
                                    "net_pips": float(result.net.to_numpy()[mask].sum()),
                                    "bars": int(mask.sum()),
                                }
                            )
    return {
        "per_pair": pd.DataFrame(rows),
        "pooled": pd.DataFrame(pooled_rows),
        "sessions": pd.DataFrame(sessions),
        "stability": pd.DataFrame(stability_rows),
    }


def summarise(pooled: pd.DataFrame, stability: pd.DataFrame) -> pd.DataFrame:
    """One row per strategy: base result, cost sensitivity, spread, stability."""
    base = pooled[pooled["cost_multiplier"] == 1.0].set_index("strategy")
    out = base[
        [
            "pooled_net_pips_per_pair",
            "pooled_sharpe_like",
            "pooled_max_drawdown_pips",
            "pairs_positive",
            "total_closed_trades",
            "mean_win_rate",
            "mean_profit_factor",
            "mean_avg_trade_pips",
            "mean_turnover_per_year",
            "top_pair_share_of_abs_pnl",
            "gross_pips_per_pair",
            "cost_pips_per_pair",
        ]
    ].copy()
    for multiplier in (1.25, 1.5):
        column = pooled[pooled["cost_multiplier"] == multiplier].set_index("strategy")
        out[f"net_at_cost_x{multiplier}"] = column["pooled_net_pips_per_pair"]
    if not stability.empty:
        stat = stability.set_index("strategy")
        out["periods_positive"] = stat["periods_positive"]
        out["worst_period_pips"] = stat["worst_period_pips"]
    return out.sort_values("pooled_net_pips_per_pair", ascending=False)


def write(name: str, payload: dict[str, Any]) -> None:
    bars_module.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = bars_module.CACHE_DIR / f"{name}.json"
    target.write_text(
        json.dumps(
            {
                "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
                "classification_secondary": "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
                "cost_assumption": engine.COST_LABEL,
                **payload,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )


__all__ = ["run_registry", "summarise", "write"]
