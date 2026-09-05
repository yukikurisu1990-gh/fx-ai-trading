"""The supplemental replication driver: every number in the results doc.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Round 2's post-mortem found that six of its seven artefacts had been produced by
uncommitted scratch scripts, and that this is *why* two arithmetic errors
survived to the report — nobody could re-run the thing that produced them. So
this round's numbers come from here, and `python -m
scripts.research.exploratory_m15.supplemental_replication` reproduces the whole
results document from the cached bars.

The candidate is `supplemental_power.CENTRE`, which is `round2.CENTRE` plus the
`entry_z` the plan froze. It is read, never written.
"""

from __future__ import annotations

import itertools
import json
from typing import Any, Final

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import (
    DEVELOPMENT_END_UTC,
    DEVELOPMENT_START_UTC,
    PAIRS,
    engine,
    round2,
    runner,
)
from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import supplemental as supp
from scripts.research.exploratory_m15 import supplemental_power as power

#: The frozen candidate. `round2.CENTRE` is the committed `(lookback, hold)`.
FROZEN: Final[dict[str, Any]] = {
    "lookback": round2.CENTRE[0],
    "hold": round2.CENTRE[1],
    "entry_z": 1.0,
}
NEIGHBOURHOOD: Final[tuple[int, ...]] = (384, 480, 576)
N_BLOCKS: Final[int] = 8
JPY: Final[list[str]] = [pair for pair in PAIRS if "JPY" in pair]
NON_JPY: Final[list[str]] = [pair for pair in PAIRS if pair not in JPY]


def _panel(result: dict[str, Any]) -> pd.DataFrame:
    return pd.concat(
        [series.rename(pair) for pair, series in result["pair_net_series"].items()], axis=1
    ).fillna(0.0)


def _mean_ic(
    loaded: dict[str, pd.DataFrame],
    *,
    lookback: int,
    horizon: int,
    lo_ts: pd.Timestamp | None = None,
    hi_ts: pd.Timestamp | None = None,
) -> tuple[float, int, int]:
    """Mean past-vs-forward IC and how many pairs carry a negative one.

    Windows are selected by **timestamp**, not by row position. Pair bar counts
    differ by up to 186 over this span, so one pair's row 40,000 is another
    pair's row 39,900 — about two days apart by block 8. The `net` column beside
    this one is timestamp-masked, so a positional slice would put two different
    windows in one table row. An audit found the positional version here, and
    `runner.py` documents the same defect from Round 1.

    Overlapping windows, so this is a descriptive statistic and not a test; the
    inference lives in `supplemental_power`.
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
    return float(np.mean(values)), sum(1 for v in values if v < 0), len(values)


def gross_by_pair(loaded: dict[str, pd.DataFrame], **config: Any) -> dict[str, float]:
    """Per-pair **gross**, phase-averaged, through `round2`'s own primitives.

    `round2.evaluate_config` returns `net_by_pair` but averages gross across
    pairs before returning, so "negative before costs on N of 20 pairs" cannot be
    read off it — an earlier draft quoted the *net* count of 19/20 as though it
    were the gross one. This recomputes gross with `round2._signal`,
    `round2._phases` and `engine.evaluate`, the same three calls
    `evaluate_config` makes, rather than editing `round2.py`: that module being
    byte-identical to its pre-read state is what the parameter freeze rests on.
    """
    phases = round2._phases(config["hold"])
    out: dict[str, float] = {}
    for pair, frame in loaded.items():
        values = []
        for phase in phases:
            signal = round2._signal(frame, phase=phase, **config)
            values.append(
                engine.evaluate(frame, signal, name="gross", pair=pair).metrics["gross_pips"]
            )
        out[pair] = float(np.mean(values))
    return out


def primary(
    development: dict[str, pd.DataFrame], supplemental: dict[str, pd.DataFrame]
) -> dict[str, Any]:
    """The frozen candidate on both periods, reported side by side."""
    out: dict[str, Any] = {
        "config": f"lb{FROZEN['lookback']}_h{FROZEN['hold']}_z{FROZEN['entry_z']}"
    }
    results: dict[str, Any] = {}
    for label, loaded in (("original", development), ("supplemental", supplemental)):
        result = round2.evaluate_config(loaded, **FROZEN)
        results[label] = result
        ic, negative, counted = _mean_ic(
            loaded, lookback=FROZEN["lookback"], horizon=FROZEN["hold"]
        )
        out[label] = {
            key: value
            for key, value in result.items()
            if key not in ("daily_net", "pair_net_series")
        }
        out[label]["mean_ic"] = round(ic, 4)
        out[label]["pairs_with_negative_ic"] = f"{negative}/{counted}"
        gross = gross_by_pair(loaded, **FROZEN)
        out[label]["gross_by_pair"] = {k: round(v, 1) for k, v in sorted(gross.items())}
        out[label]["pairs_gross_negative"] = (
            f"{sum(1 for v in gross.values() if v < 0)}/{len(gross)}"
        )
    combined = pd.concat(
        [results["supplemental"]["daily_net"], results["original"]["daily_net"]]
    ).sort_index()
    out["combined"] = {
        "net_pips_per_pair": round(float(combined.sum()), 1),
        "days": int(len(combined.groupby(combined.index.floor("D")).sum())),
        "note": "a negative supplemental period is not a replication whatever this says",
    }
    out["_series"] = results
    return out


def diagnostics(
    supplemental: dict[str, pd.DataFrame], panels: dict[str, pd.DataFrame]
) -> dict[str, Any]:
    reference = next(iter(supplemental.values()))
    total = len(reference)
    blocks: list[dict[str, Any]] = []
    for index, chunk in enumerate(np.array_split(np.arange(total), N_BLOCKS)):
        lo_ts = reference["ts"].iloc[chunk[0]]
        hi_ts = reference["ts"].iloc[chunk[-1]]
        ic, negative, _ = _mean_ic(
            supplemental,
            lookback=FROZEN["lookback"],
            horizon=FROZEN["hold"],
            lo_ts=lo_ts,
            hi_ts=hi_ts,
        )
        segment = panels["supplemental"]
        segment = segment[(segment.index >= lo_ts) & (segment.index <= hi_ts)]
        blocks.append(
            {
                "block": index + 1,
                "from": str(lo_ts.date()),
                "to": str(hi_ts.date()),
                "mean_ic": round(ic, 4),
                "neg_ic_pairs": negative,
                "net": round(float(segment.mean(axis=1).sum()), 1),
                "pairs_pos": int((segment.sum() > 0).sum()),
            }
        )

    blocs = {
        label: {
            "all": round(float(panel.mean(axis=1).sum()), 1),
            "jpy": round(float(panel[JPY].mean(axis=1).sum()), 1),
            "non_jpy": round(float(panel[NON_JPY].mean(axis=1).sum()), 1),
        }
        for label, panel in panels.items()
    }

    panel = panels["supplemental"]
    loo_pair = {
        pair: round(float(panel.drop(columns=[pair]).mean(axis=1).sum()), 1) for pair in PAIRS
    }
    currencies = sorted({token for pair in PAIRS for token in pair.split("_")})
    loo_currency = {
        currency: round(
            float(panel[[p for p in PAIRS if currency not in p.split("_")]].mean(axis=1).sum()),
            1,
        )
        for currency in currencies
    }

    #: Both tails. Removing only the *best* days measures how much of a gain is
    #: carried by a handful of days -- the right question for the development
    #: window, and the wrong one for a loss. An audit showed that removing the
    #: worst days instead flips the supplemental sign at 20 of 624, which is the
    #: mirror of the development window's concentration rather than its opposite.
    top_days: dict[str, Any] = {}
    for label, frame in panels.items():
        pooled = frame.mean(axis=1)
        daily = pooled.groupby(pooled.index.floor("D")).sum()
        best = np.sort(daily.to_numpy())[::-1]
        worst = np.sort(daily.to_numpy())
        total = float(daily.sum())
        top_days[label] = {
            "total": round(total, 1),
            "days": int(len(daily)),
            **{
                f"net_ex_best{k}": round(total - float(best[:k].sum()), 1)
                for k in (1, 3, 5, 10, 20)
            },
            **{
                f"net_ex_worst{k}": round(total - float(worst[:k].sum()), 1)
                for k in (1, 3, 5, 10, 20)
            },
        }

    cells = []
    for lookback, hold in itertools.product(NEIGHBOURHOOD, NEIGHBOURHOOD):
        result = round2.evaluate_config(
            supplemental, lookback=lookback, hold=hold, entry_z=FROZEN["entry_z"]
        )
        cells.append(
            {
                "cfg": f"lb{lookback}_h{hold}",
                "net": result["net_pips_per_pair"],
                "gross": result["gross_pips_per_pair"],
                "trades": result["closed_trades_pooled"],
                "pairs_pos": result["pairs_positive"],
            }
        )

    atr_high = {}
    for entry_z in (0.0, 1.0):
        result = round2.evaluate_config(
            supplemental,
            lookback=FROZEN["lookback"],
            hold=FROZEN["hold"],
            entry_z=entry_z,
            atr_bucket="high",
        )
        atr_high[f"z{entry_z}"] = {
            key: result[key]
            for key in (
                "net_pips_per_pair",
                "gross_pips_per_pair",
                "closed_trades_pooled",
                "pairs_positive",
            )
        }

    return {
        "blocks": blocks,
        "blocs": blocs,
        "loo_pair": loo_pair,
        "loo_currency": loo_currency,
        "top_days": top_days,
        "neighbourhood": cells,
        "neighbourhood_positive_net": sum(1 for cell in cells if cell["net"] > 0),
        "neighbourhood_positive_gross": sum(1 for cell in cells if cell["gross"] > 0),
        "atr_high": atr_high,
    }


def integrity(
    development: dict[str, pd.DataFrame],
    supplemental: dict[str, pd.DataFrame],
    *,
    sample_day: str = "2024-03-11",
) -> dict[str, Any]:
    """The §8 checks, in committed code.

    They were computed in a scratch script for the first draft, which is exactly
    the Round 2 failure the module docstring cites — and an audit noticed that
    the paragraph claiming committed provenance sat three lines below numbers
    that had none.

    Two things are worth naming here rather than in prose. The periods come from
    **different archive files** (`*_M1_365d_BA` for the development window,
    `*_M1_3650d_BA` for the supplemental one), so a spread difference between
    them is not necessarily a market difference; and the `to_m15` bucketing takes
    the extremum of bid and ask *separately* before averaging, so re-aggregating
    per-M1 mids gives a slightly wider high and low. Both are properties shared by
    the two periods, which is why they do not bias the comparison.
    """
    out: dict[str, Any] = {
        "sources": {
            "development": bars_module.SOURCE_TEMPLATE,
            "supplemental": supp.SOURCE_TEMPLATE,
        }
    }
    for label, loaded, lo, hi in (
        ("development", development, DEVELOPMENT_START_UTC, DEVELOPMENT_END_UTC),
        ("supplemental", supplemental, supp.SUPPLEMENTAL_START_UTC, supp.SUPPLEMENTAL_END_UTC),
    ):
        outside = monotone = duplicated = nan_cells = negative_spreads = 0
        min_gap = None
        for frame in loaded.values():
            stamps = frame["ts"]
            outside += int(
                (
                    (stamps < pd.Timestamp(lo, tz="UTC"))
                    | (stamps > pd.Timestamp(hi, tz="UTC") + pd.Timedelta(days=1))
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
        out[label] = {
            "pairs": len(loaded),
            "bars_outside_span": outside,
            "pairs_monotonic": f"{monotone}/{len(loaded)}",
            "duplicate_timestamps": duplicated,
            "min_gap_seconds": min_gap,
            "nan_cells": nan_cells,
            "negative_spreads": negative_spreads,
            "spread_median_pips": round(float(spreads.median()), 3),
            "spread_p99_pips": round(float(spreads.quantile(0.99)), 2),
        }

    #: Re-aggregate one day of raw M1 and compare against the cached bars.
    m1 = supp.read_m1("USD_JPY", start=sample_day, end=sample_day)
    for key in "ohlc":
        m1["m" + key] = (m1["bid_" + key] + m1["ask_" + key]) / 2.0
    rebuilt = m1.groupby(m1["ts"].dt.floor("15min")).agg(
        o=("mo", "first"), h=("mh", "max"), l=("ml", "min"), c=("mc", "last"), n=("mc", "size")
    )
    cached = supplemental["USD_JPY"]
    day = cached[
        (cached["ts"] >= pd.Timestamp(sample_day, tz="UTC"))
        & (cached["ts"] < pd.Timestamp(sample_day, tz="UTC") + pd.Timedelta(days=1))
    ].set_index("ts")
    joined = rebuilt.join(day[["mid_o", "mid_h", "mid_l", "mid_c", "n_source_bars"]], how="inner")
    open_close = (
        np.isclose(joined["o"], joined["mid_o"])
        & np.isclose(joined["c"], joined["mid_c"])
        & (joined["n"] == joined["n_source_bars"])
    )
    high_low = np.isclose(joined["h"], joined["mid_h"]) & np.isclose(joined["l"], joined["mid_l"])
    out["raw_m1_cross_check"] = {
        "pair": "USD_JPY",
        "day": sample_day,
        "buckets": int(len(joined)),
        "open_close_and_count_match": int(open_close.sum()),
        "high_low_match": int(high_low.sum()),
        "note": "high/low differ where the per-side extremum and the mid extremum disagree",
    }
    return out


def main() -> dict[str, Any]:
    development = {pair: bars_module.load(pair) for pair in PAIRS}
    supplemental = {pair: supp.load(pair) for pair in PAIRS}

    replication = primary(development, supplemental)
    series = replication.pop("_series")
    panels = {label: _panel(series[label]) for label in ("original", "supplemental")}
    runner.write("supplemental_primary_replication", replication)

    runner.write("supplemental_diagnostics", diagnostics(supplemental, panels))
    runner.write("supplemental_integrity", integrity(development, supplemental))

    combined = pd.concat(
        [series["supplemental"]["daily_net"], series["original"]["daily_net"]]
    ).sort_index()
    rates = power.rate_comparison(
        series["original"]["daily_net"], series["supplemental"]["daily_net"]
    )
    #: The alternative the study was designed against: what the supplemental
    #: period returns if the development *rate* is the truth. Not the development
    #: period's total, which is a different span.
    alternative = rates["projection"]["supplemental_net_if_original_rate_held"]
    runner.write(
        "supplemental_power",
        {
            "rate_comparison": rates,
            "power": {
                "original": power.two_sided_power(series["original"]["daily_net"]),
                "supplemental": power.two_sided_power(
                    series["supplemental"]["daily_net"], alternative=alternative
                ),
                "combined": power.two_sided_power(combined),
            },
            "family_max_supplemental": power.family_max(supplemental, reference=alternative),
        },
    )
    return replication


if __name__ == "__main__":  # pragma: no cover - the driver
    print(json.dumps(main(), indent=2, sort_keys=True, default=str))
