"""Round 2: is the multi-day reversal real, and can this corpus tell?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The family is fixed in `docs/research/m15_track_a_exploratory_round_2_plan.md`,
committed before any of this ran: 27 primary configurations over the 4-to-6 day
neighbourhood and 12 secondary ones on the ATR axis. Nothing here searches for a
better cell; the neighbourhood is being characterised, not optimised.

**Every configuration is phase-averaged over 8 rebalance offsets.** Round 1
established that `grid[::hold]` locks to one UTC hour on this corpus and that a
single phase is one draw from a distribution spanning -171 to +713 pips per
pair. Phase is a nuisance parameter: averaged, never chosen.
"""

from __future__ import annotations

from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import PAIRS, engine
from scripts.research.exploratory_m15 import bars as bars_module

#: The pre-registered axes. Changing these changes the family the multiplicity
#: correction is over, which is why they are constants and not arguments.
LOOKBACKS: Final[tuple[int, ...]] = (384, 480, 576)
HOLDS: Final[tuple[int, ...]] = (384, 480, 576)
ENTRY_ZS: Final[tuple[float, ...]] = (0.0, 1.0, 1.5)
CENTRE: Final[tuple[int, int]] = (480, 480)
ATR_BUCKETS: Final[tuple[str, ...]] = ("all", "low", "mid", "high")
N_PHASES: Final[int] = 8
Z_WINDOW: Final[int] = 480
ATR_PERIOD: Final[int] = 14
ATR_RANK_WINDOW: Final[int] = 960
BLOCKS: Final[int] = 8


def _signal(
    frame: pd.DataFrame,
    *,
    lookback: int,
    hold: int,
    entry_z: float,
    phase: int,
    atr_bucket: str = "all",
) -> pd.Series:
    """Fade the `lookback` move, decide on the grid, hold. Causal throughout."""
    move = (frame["mid_c"] - frame["mid_c"].shift(lookback)) / frame["pip_size"]
    score = engine.zscore(move, Z_WINDOW)
    raw = pd.Series(0.0, index=frame.index)
    raw[score > entry_z] = -1.0
    raw[score < -entry_z] = 1.0

    if atr_bucket != "all":
        atr = engine.atr_pips(frame, ATR_PERIOD)
        #: the pair's own trailing ATR distribution, strictly past-only
        rank = atr.rolling(ATR_RANK_WINDOW, min_periods=ATR_RANK_WINDOW // 2).rank(pct=True)
        if atr_bucket == "low":
            allowed = rank <= 1 / 3
        elif atr_bucket == "mid":
            allowed = (rank > 1 / 3) & (rank <= 2 / 3)
        else:
            allowed = rank > 2 / 3
        raw = raw.where(allowed.fillna(False), 0.0)

    grid = np.zeros(len(frame), dtype=bool)
    grid[phase::hold] = True
    decided = raw.where(pd.Series(grid, index=frame.index)).ffill().fillna(0.0)
    #: never open on a rollover bar; the day's widest quotes are charged there
    blocked = frame["rollover"] & (decided != decided.shift(1))
    return decided.where(~blocked).ffill().fillna(0.0)


def _phases(hold: int) -> list[int]:
    return list(range(0, hold, max(1, hold // N_PHASES)))[:N_PHASES]


def evaluate_config(
    loaded: dict[str, pd.DataFrame],
    *,
    lookback: int,
    hold: int,
    entry_z: float,
    atr_bucket: str = "all",
    cost_multipliers=(1.0, 1.25, 1.5, 2.0, 3.0),
) -> dict[str, Any]:
    """One configuration, phase-averaged, with everything the plan asks for."""
    phases = _phases(hold)
    per_phase_net: dict[float, list[pd.Series]] = {m: [] for m in cost_multipliers}
    accum: dict[str, list[dict[str, Any]]] = {pair: [] for pair in loaded}
    pair_net_series: dict[str, list[pd.Series]] = {pair: [] for pair in loaded}

    for phase in phases:
        for multiplier in cost_multipliers:
            columns = []
            for pair, frame in loaded.items():
                signal = _signal(
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
    total_abs = sum(abs(v) for v in by_pair_net.values()) or 1.0
    top = max(by_pair_net, key=by_pair_net.get)

    return {
        "lookback": lookback,
        "hold": hold,
        "entry_z": entry_z,
        "atr_bucket": atr_bucket,
        "phases": len(phases),
        "net_pips_per_pair": round(float(base.sum()), 1),
        "gross_pips_per_pair": round(
            float(np.mean([v["gross_pips"] for v in per_pair.values()])), 1
        ),
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
        "top_pair": top,
        "top_pair_share_of_abs_pnl": round(abs(by_pair_net[top]) / total_abs, 3),
        "net_by_pair": {k: round(v, 1) for k, v in sorted(by_pair_net.items())},
        "net_at_cost": {f"x{m}": round(float(series.sum()), 1) for m, series in pooled.items()},
        "daily_net": pooled[1.0].groupby(pooled[1.0].index.floor("D")).sum(),
        "pair_net_series": {
            pair: pd.concat(series, axis=1).fillna(0.0).mean(axis=1)
            for pair, series in pair_net_series.items()
        },
    }


def primary_family() -> list[dict[str, int | float | str]]:
    return [
        {"lookback": lb, "hold": h, "entry_z": z}
        for lb in LOOKBACKS
        for h in HOLDS
        for z in ENTRY_ZS
    ]


def secondary_family() -> list[dict[str, int | float | str]]:
    lookback, hold = CENTRE
    return [
        {"lookback": lookback, "hold": hold, "entry_z": z, "atr_bucket": bucket}
        for bucket in ATR_BUCKETS
        for z in ENTRY_ZS
    ]


def name_of(config: dict) -> str:
    bucket = config.get("atr_bucket", "all")
    suffix = "" if bucket == "all" else f"_atr{bucket}"
    return f"lb{config['lookback']}_h{config['hold']}_z{config['entry_z']}{suffix}"


def load_all() -> dict[str, pd.DataFrame]:
    return {pair: bars_module.load(pair) for pair in PAIRS}


# ---------------------------------------------------------------------------
# temporal stability, per the plan's section 5
# ---------------------------------------------------------------------------


def signal_ic(frame: pd.DataFrame, lookback: int, horizon: int) -> pd.Series:
    """Per-bar product terms whose mean is the IC's numerator; kept as a series
    so it can be sliced by block without recomputing."""
    close = frame["mid_c"]
    pip = frame["pip_size"]
    past = (close - close.shift(lookback)) / pip
    forward = (close.shift(-horizon) - close) / pip
    return pd.DataFrame({"past": past, "forward": forward}, index=frame.index)


def block_stability(
    loaded: dict[str, pd.DataFrame], config: dict, result: dict, *, blocks: int = BLOCKS
) -> list[dict[str, Any]]:
    """IC, gross, net, trades and pair breadth per chronological block."""
    lookback = int(config["lookback"])
    horizon = int(config["hold"])
    reference = next(iter(loaded.values()))
    edges = np.array_split(np.arange(len(reference)), blocks)
    out: list[dict[str, Any]] = []
    for index, chunk in enumerate(edges):
        lo, hi = reference["ts"].iloc[chunk[0]], reference["ts"].iloc[chunk[-1]]
        ics, spreads, atrs = [], [], []
        pair_nets = {}
        for pair, frame in loaded.items():
            window = (frame["ts"] >= lo) & (frame["ts"] <= hi)
            terms = signal_ic(frame, lookback, horizon)[window]
            usable = terms.dropna()
            if len(usable) > 200:
                ics.append(float(np.corrcoef(usable["past"], usable["forward"])[0, 1]))
            spreads.append(float(frame.loc[window, "spread_close_pips"].median()))
            atrs.append(float(engine.atr_pips(frame, ATR_PERIOD)[window].median()))
            series = result["pair_net_series"][pair]
            pair_nets[pair] = float(series[(series.index >= lo) & (series.index <= hi)].sum())
        out.append(
            {
                "block": index + 1,
                "from": str(lo.date()),
                "to": str(hi.date()),
                "mean_ic": round(float(np.mean(ics)), 4),
                "pairs_negative_ic": int(sum(1 for v in ics if v < 0)),
                "pairs_with_ic": len(ics),
                "net_pips_per_pair": round(float(np.mean(list(pair_nets.values()))), 1),
                "pairs_positive_net": int(sum(1 for v in pair_nets.values() if v > 0)),
                "median_atr_pips": round(float(np.mean(atrs)), 2),
                "median_spread_pips": round(float(np.mean(spreads)), 2),
            }
        )
    return out


__all__ = [
    "ATR_BUCKETS",
    "BLOCKS",
    "CENTRE",
    "ENTRY_ZS",
    "HOLDS",
    "LOOKBACKS",
    "N_PHASES",
    "block_stability",
    "evaluate_config",
    "load_all",
    "name_of",
    "primary_family",
    "secondary_family",
    "signal_ic",
]
