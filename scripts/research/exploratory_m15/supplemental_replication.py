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

from scripts.research.exploratory_m15 import PAIRS, round2, runner
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
    lo: int | None = None,
    hi: int | None = None,
) -> tuple[float, int, int]:
    """Mean past-vs-forward IC and how many pairs carry a negative one.

    Overlapping windows, so this is a descriptive statistic and not a test; the
    inference lives in `supplemental_power`.
    """
    values: list[float] = []
    for frame in loaded.values():
        close, pip = frame["mid_c"], frame["pip_size"]
        past = (close - close.shift(lookback)) / pip
        forward = (close.shift(-horizon) - close) / pip
        if lo is not None:
            past, forward = past.iloc[lo:hi], forward.iloc[lo:hi]
        mask = past.notna() & forward.notna()
        if int(mask.sum()) > 300:
            values.append(float(np.corrcoef(past[mask], forward[mask])[0, 1]))
    return float(np.mean(values)), sum(1 for v in values if v < 0), len(values)


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
            lo=int(chunk[0]),
            hi=int(chunk[-1]),
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

    top_days: dict[str, Any] = {}
    for label, frame in panels.items():
        pooled = frame.mean(axis=1)
        daily = pooled.groupby(pooled.index.floor("D")).sum()
        ranked = np.sort(daily.to_numpy())[::-1]
        gross_total = float(daily.sum())
        top_days[label] = {
            "total": round(gross_total, 1),
            "days": int(len(daily)),
            **{
                f"net_ex_top{k}": round(gross_total - float(ranked[:k].sum()), 1)
                for k in (1, 3, 5, 10)
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


def main() -> dict[str, Any]:
    development = {pair: bars_module.load(pair) for pair in PAIRS}
    supplemental = {pair: supp.load(pair) for pair in PAIRS}

    replication = primary(development, supplemental)
    series = replication.pop("_series")
    panels = {label: _panel(series[label]) for label in ("original", "supplemental")}
    runner.write("supplemental_primary_replication", replication)

    runner.write("supplemental_diagnostics", diagnostics(supplemental, panels))

    combined = pd.concat(
        [series["supplemental"]["daily_net"], series["original"]["daily_net"]]
    ).sort_index()
    runner.write(
        "supplemental_power",
        {
            "rate_comparison": power.rate_comparison(
                series["original"]["daily_net"], series["supplemental"]["daily_net"]
            ),
            "power": {
                "original": power.two_sided_power(series["original"]["daily_net"]),
                "supplemental": power.two_sided_power(series["supplemental"]["daily_net"]),
                "combined": power.two_sided_power(combined),
            },
            "family_max_supplemental": power.family_max(
                supplemental, reference=replication["original"]["net_pips_per_pair"]
            ),
        },
    )
    return replication


if __name__ == "__main__":  # pragma: no cover - the driver
    print(json.dumps(main(), indent=2, sort_keys=True, default=str))
