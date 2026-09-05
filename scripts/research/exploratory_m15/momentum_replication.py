"""The momentum replication driver: every number in the results document.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `POST_HOC_EXPLORATORY_HYPOTHESIS`.

`round2.evaluate_config` calls `round2._signal` directly, so it cannot evaluate a
different signal, and `round2.py` must stay byte-identical because the parameter
freeze rests on that. The aggregation here therefore takes the signal as an
argument — and `test_the_generic_aggregator_reproduces_the_frozen_one` hands it
`round2._signal` and asserts the output matches `round2.evaluate_config` field
for field on real bars. Two implementations of one thing are a drift hazard
unless something ties them together; that test is the tie.

The exact-mirror relation is used as a check, never as a shortcut. Momentum and
reversal hold opposite positions of equal size, so their turnover — and therefore
their cost — is identical, and gross is exactly negated:

    gross_momentum = -gross_reversal        cost_momentum = cost_reversal
    net_momentum   = -gross_reversal - cost_reversal

Net is *not* the negation of net, which is the whole reason a mirror of a losing
rule is not automatically a winning one: both sides pay the spread.
"""

from __future__ import annotations

import itertools
from collections.abc import Callable
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import PAIRS, engine, momentum, round2, runner
from scripts.research.exploratory_m15 import supplemental_power as power

FROZEN: Final[dict[str, Any]] = {
    "lookback": momentum.FROZEN_LOOKBACK,
    "hold": momentum.FROZEN_HOLD,
    "entry_z": momentum.FROZEN_ENTRY_Z,
}
N_BLOCKS: Final[int] = 8
JPY: Final[list[str]] = [pair for pair in PAIRS if "JPY" in pair]
NON_JPY: Final[list[str]] = [pair for pair in PAIRS if pair not in JPY]
COST_MULTIPLIERS: Final[tuple[float, ...]] = (1.0, 1.25, 1.5, 2.0, 3.0)


def evaluate_config(
    loaded: dict[str, pd.DataFrame],
    signal_fn: Callable[..., pd.Series],
    *,
    lookback: int,
    hold: int,
    entry_z: float,
    atr_bucket: str = "all",
    cost_multipliers: tuple[float, ...] = COST_MULTIPLIERS,
) -> dict[str, Any]:
    """`round2.evaluate_config`, with the signal supplied rather than hard-wired."""
    phases = round2._phases(hold)
    per_phase_net: dict[float, list[pd.Series]] = {m: [] for m in cost_multipliers}
    accum: dict[str, list[dict[str, Any]]] = {pair: [] for pair in loaded}
    pair_net_series: dict[str, list[pd.Series]] = {pair: [] for pair in loaded}

    for phase in phases:
        for multiplier in cost_multipliers:
            columns = []
            for pair, frame in loaded.items():
                signal = signal_fn(
                    frame,
                    lookback=lookback,
                    hold=hold,
                    entry_z=entry_z,
                    phase=phase,
                    atr_bucket=atr_bucket,
                )
                result = engine.evaluate(
                    frame, signal, name="r2", pair=pair, cost_multiplier=multiplier
                )
                columns.append(result.net.set_axis(frame["ts"]).rename(pair))
                if multiplier == 1.0:
                    accum[pair].append(result.metrics)
                    pair_net_series[pair].append(result.net.set_axis(frame["ts"]))
            per_phase_net[multiplier].append(pd.concat(columns, axis=1).fillna(0.0).mean(axis=1))

    pooled = {
        m: pd.concat(series, axis=1).fillna(0.0).mean(axis=1) for m, series in per_phase_net.items()
    }
    base = pooled[1.0]
    equity = base.cumsum()
    drawdown = equity - equity.cummax()
    std = float(base.std())

    per_pair = {
        pair: {
            key: float(np.mean([m[key] for m in metrics]))
            for key in (
                "net_pips",
                "gross_pips",
                "cost_pips",
                "n_closed_trades",
                "win_rate",
                "avg_trade_pips",
                "turnover_per_year",
                "exposure",
            )
        }
        for pair, metrics in accum.items()
    }
    by_pair_net = {pair: values["net_pips"] for pair, values in per_pair.items()}
    by_pair_gross = {pair: values["gross_pips"] for pair, values in per_pair.items()}
    total_abs = sum(abs(v) for v in by_pair_net.values()) or 1.0
    top = max(by_pair_net, key=by_pair_net.get)

    return {
        "lookback": lookback,
        "hold": hold,
        "entry_z": entry_z,
        "atr_bucket": atr_bucket,
        "phases": len(phases),
        "net_pips_per_pair": round(float(base.sum()), 1),
        "gross_pips_per_pair": round(float(np.mean(list(by_pair_gross.values()))), 1),
        "cost_pips_per_pair": round(float(np.mean([v["cost_pips"] for v in per_pair.values()])), 1),
        "sharpe_like": round(float(base.mean() / std * np.sqrt(engine.BARS_PER_YEAR)), 2)
        if std > 0
        else 0.0,
        "max_drawdown_pips": round(float(drawdown.min()), 1),
        "closed_trades_pooled": int(sum(v["n_closed_trades"] for v in per_pair.values())),
        "win_rate": round(float(np.mean([v["win_rate"] for v in per_pair.values()])), 3),
        "avg_trade_pips": round(
            float(np.mean([v["avg_trade_pips"] for v in per_pair.values()])), 2
        ),
        "turnover_per_year": round(
            float(np.mean([v["turnover_per_year"] for v in per_pair.values()])), 1
        ),
        "exposure": round(float(np.mean([v["exposure"] for v in per_pair.values()])), 3),
        "pairs_positive": int(sum(1 for v in by_pair_net.values() if v > 0)),
        "pairs_gross_positive": int(sum(1 for v in by_pair_gross.values() if v > 0)),
        "top_pair": top,
        "top_pair_share_of_abs_pnl": round(abs(by_pair_net[top]) / total_abs, 3),
        "net_by_pair": {k: round(v, 1) for k, v in sorted(by_pair_net.items())},
        "gross_by_pair": {k: round(v, 1) for k, v in sorted(by_pair_gross.items())},
        "net_at_cost": {f"x{m}": round(float(series.sum()), 1) for m, series in pooled.items()},
        "daily_net": pooled[1.0].groupby(pooled[1.0].index.floor("D")).sum(),
        "pair_net_series": {
            pair: pd.concat(series, axis=1).fillna(0.0).mean(axis=1)
            for pair, series in pair_net_series.items()
        },
    }


def _panel(result: dict[str, Any], pairs: list[str] | None = None) -> pd.DataFrame:
    chosen = pairs or list(result["pair_net_series"])
    return pd.concat(
        [result["pair_net_series"][pair].rename(pair) for pair in chosen], axis=1
    ).fillna(0.0)


def mean_ic(
    loaded: dict[str, pd.DataFrame],
    *,
    lookback: int,
    horizon: int,
    lo_ts: pd.Timestamp | None = None,
    hi_ts: pd.Timestamp | None = None,
) -> tuple[float, int, int]:
    """Past-vs-forward IC, masked by timestamp rather than row position.

    A **positive** IC is the momentum direction: what rose keeps rising. The sign
    convention is the same one the reversal rounds used, so the two are directly
    comparable — and the reversal candidate wanted this number negative.
    """
    values: list[float] = []
    for frame in loaded.values():
        close, pip = frame["mid_c"], frame["pip_size"]
        past = (close - close.shift(lookback)) / pip
        forward = (close.shift(-horizon) - close) / pip
        if lo_ts is not None:
            window = (frame["ts"] >= lo_ts) & (frame["ts"] <= hi_ts)
            past, forward = past[window], forward[window]
        mask = past.notna() & forward.notna()
        if int(mask.sum()) > 300:
            values.append(float(np.corrcoef(past[mask], forward[mask])[0, 1]))
    return float(np.mean(values)), sum(1 for v in values if v > 0), len(values)


def primary(loaded: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """The frozen momentum candidate on the fresh span, and its blocs."""
    out: dict[str, Any] = {
        "config": f"lb{FROZEN['lookback']}_h{FROZEN['hold']}_z{FROZEN['entry_z']}_momentum",
        "span_label": momentum.SPAN_LABEL,
        "span": [momentum.MOMENTUM_START_UTC, momentum.MOMENTUM_END_UTC],
    }
    result = evaluate_config(loaded, momentum.signal, **FROZEN)
    ic, positive, counted = mean_ic(loaded, lookback=FROZEN["lookback"], horizon=FROZEN["hold"])
    out["all_20"] = {
        key: value for key, value in result.items() if key not in ("daily_net", "pair_net_series")
    }
    out["all_20"]["mean_ic"] = round(ic, 4)
    out["all_20"]["pairs_with_positive_ic"] = f"{positive}/{counted}"

    #: The mirror identity, checked rather than assumed: same turnover, so the
    #: same cost, and gross exactly negated. If this drifts, one of the two
    #: signals is not the other's mirror any more.
    reversal = round2.evaluate_config(loaded, **FROZEN)
    out["mirror_check"] = {
        "reversal_gross": reversal["gross_pips_per_pair"],
        "momentum_gross": result["gross_pips_per_pair"],
        "gross_sums_to_zero": round(
            reversal["gross_pips_per_pair"] + result["gross_pips_per_pair"], 3
        ),
        "reversal_cost": reversal["cost_pips_per_pair"],
        "momentum_cost": result["cost_pips_per_pair"],
        "costs_identical": reversal["cost_pips_per_pair"] == result["cost_pips_per_pair"],
        "reversal_net": reversal["net_pips_per_pair"],
        "momentum_net": result["net_pips_per_pair"],
        "note": "both sides pay the spread, so net is not the negation of net",
    }

    for label, pairs in (("jpy_6", JPY), ("non_jpy_14", NON_JPY)):
        subset = {pair: loaded[pair] for pair in pairs}
        bloc = evaluate_config(subset, momentum.signal, **FROZEN)
        bloc_ic, bloc_pos, bloc_n = mean_ic(
            subset, lookback=FROZEN["lookback"], horizon=FROZEN["hold"]
        )
        out[label] = {
            key: bloc[key]
            for key in (
                "net_pips_per_pair",
                "gross_pips_per_pair",
                "cost_pips_per_pair",
                "sharpe_like",
                "max_drawdown_pips",
                "closed_trades_pooled",
                "win_rate",
                "avg_trade_pips",
                "turnover_per_year",
                "pairs_positive",
                "net_at_cost",
            )
        }
        out[label]["mean_ic"] = round(bloc_ic, 4)
        out[label]["pairs_with_positive_ic"] = f"{bloc_pos}/{bloc_n}"

    out["_result"] = result
    return out


def diagnostics(loaded: dict[str, pd.DataFrame], result: dict[str, Any]) -> dict[str, Any]:
    panel = _panel(result)
    reference = next(iter(loaded.values()))

    blocks: list[dict[str, Any]] = []
    for index, chunk in enumerate(np.array_split(np.arange(len(reference)), N_BLOCKS)):
        lo_ts = reference["ts"].iloc[chunk[0]]
        hi_ts = reference["ts"].iloc[chunk[-1]]
        ic, positive, _ = mean_ic(
            loaded,
            lookback=FROZEN["lookback"],
            horizon=FROZEN["hold"],
            lo_ts=lo_ts,
            hi_ts=hi_ts,
        )
        segment = panel[(panel.index >= lo_ts) & (panel.index <= hi_ts)]
        blocks.append(
            {
                "block": index + 1,
                "from": str(lo_ts.date()),
                "to": str(hi_ts.date()),
                "mean_ic": round(ic, 4),
                "pos_ic_pairs": positive,
                "net": round(float(segment.mean(axis=1).sum()), 1),
                "pairs_pos": int((segment.sum() > 0).sum()),
            }
        )

    loo_pair = {
        pair: round(float(panel.drop(columns=[pair]).mean(axis=1).sum()), 1) for pair in PAIRS
    }
    currencies = sorted({token for pair in PAIRS for token in pair.split("_")})
    loo_currency = {
        currency: round(
            float(panel[[p for p in PAIRS if currency not in p.split("_")]].mean(axis=1).sum()), 1
        )
        for currency in currencies
    }

    pooled = panel.mean(axis=1)
    daily = pooled.groupby(pooled.index.floor("D")).sum()
    best = np.sort(daily.to_numpy())[::-1]
    worst = np.sort(daily.to_numpy())
    total = float(daily.sum())
    tails = {
        "total": round(total, 1),
        "days": int(len(daily)),
        **{f"contribution_best{k}": round(float(best[:k].sum()), 1) for k in (1, 3, 5, 10)},
        **{f"contribution_worst{k}": round(float(worst[:k].sum()), 1) for k in (1, 3, 5, 10)},
        **{f"net_ex_best{k}": round(total - float(best[:k].sum()), 1) for k in (1, 3, 5, 10)},
        **{f"net_ex_worst{k}": round(total - float(worst[:k].sum()), 1) for k in (1, 3, 5, 10)},
    }

    cells = []
    for lookback, hold in itertools.product(momentum.NEIGHBOURHOOD, momentum.NEIGHBOURHOOD):
        cell = evaluate_config(
            loaded,
            momentum.signal,
            lookback=lookback,
            hold=hold,
            entry_z=FROZEN["entry_z"],
        )
        cells.append(
            {
                "cfg": f"lb{lookback}_h{hold}",
                "net": cell["net_pips_per_pair"],
                "gross": cell["gross_pips_per_pair"],
                "trades": cell["closed_trades_pooled"],
                "pairs_pos": cell["pairs_positive"],
            }
        )

    return {
        "blocks": blocks,
        "blocks_net_positive": sum(1 for b in blocks if b["net"] > 0),
        "blocks_ic_positive": sum(1 for b in blocks if b["mean_ic"] > 0),
        "loo_pair": loo_pair,
        "loo_pair_positive": sum(1 for v in loo_pair.values() if v > 0),
        "loo_currency": loo_currency,
        "loo_currency_positive": sum(1 for v in loo_currency.values() if v > 0),
        "tails": tails,
        "neighbourhood": cells,
        "neighbourhood_positive_net": sum(1 for c in cells if c["net"] > 0),
        "neighbourhood_positive_gross": sum(1 for c in cells if c["gross"] > 0),
    }


def integrity(loaded: dict[str, pd.DataFrame]) -> dict[str, Any]:
    outside = monotone = duplicated = nan_cells = negative_spreads = 0
    min_gap = None
    for frame in loaded.values():
        stamps = frame["ts"]
        outside += int(
            (
                (stamps < pd.Timestamp(momentum.MOMENTUM_START_UTC, tz="UTC"))
                | (stamps >= pd.Timestamp(momentum.FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC, tz="UTC"))
            ).sum()
        )
        monotone += int(stamps.is_monotonic_increasing)
        duplicated += int(stamps.duplicated().sum())
        gaps = stamps.diff().dt.total_seconds().dropna()
        if len(gaps):
            low = float(gaps.min())
            min_gap = low if min_gap is None else min(min_gap, low)
        nan_cells += int(frame[["mid_c", "spread_close_pips"]].isna().sum().sum())
        negative_spreads += int((frame["spread_close_pips"] < 0).sum())
    spreads = pd.concat([f["spread_close_pips"] for f in loaded.values()])
    return {
        "pairs": len(loaded),
        "bars_outside_span": outside,
        "pairs_monotonic": f"{monotone}/{len(loaded)}",
        "duplicate_timestamps": duplicated,
        "min_gap_seconds": min_gap,
        "nan_cells": nan_cells,
        "negative_spreads": negative_spreads,
        "spread_median_pips": round(float(spreads.median()), 3),
        "spread_p99_pips": round(float(spreads.quantile(0.99)), 2),
        "source": momentum.SOURCE_TEMPLATE,
    }


def main() -> dict[str, Any]:
    loaded = momentum.load_all()
    replication = primary(loaded)
    result = replication.pop("_result")
    runner.write("momentum_b_primary", replication)
    runner.write("momentum_b_diagnostics", diagnostics(loaded, result))
    runner.write("momentum_b_integrity", integrity(loaded))
    runner.write(
        "momentum_b_power",
        {
            "two_sided": power.two_sided_power(result["daily_net"]),
            "note": "the pre-specified alternative is zero: this is a first look at an "
            "unread span, not a replication of a measured rate",
        },
    )
    return replication


if __name__ == "__main__":  # pragma: no cover - the driver
    import json

    print(json.dumps(main(), indent=2, sort_keys=True, default=str))
