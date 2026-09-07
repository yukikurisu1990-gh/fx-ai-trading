"""The Economic Edge Source Expansion package, run in the order the plan fixed.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Stages run in order and each writes its own artifact, so a long run resumes
rather than restarting. Nothing here reads an FX price outside the three
already-seen panels.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from scripts.research.economic_edge import (
    CARRY_CELLS,
    CLASSIFICATION,
    CLASSIFICATION_SECONDARY,
    COST_MULTIPLIERS,
    PLAN_COMMIT,
    REBALANCE_BARS,
    TAIL_SHARE_CEILING,
    carry,
    rates,
)
from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.round_a import DECIDING_PANELS, PANELS, panels

CACHE = bars_module.REPO_ROOT / "artifacts" / "track_a_scratch" / "economic_edge"

#: rates are fetched wider than the panels because a signal needs history before
#: the first bar. No FX price outside the panels is read.
RATE_SPAN = ("2020-06-01", "2026-01-05")


def write(name: str, payload: Any) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"{name}.json").write_text(
        json.dumps(
            {
                "classification": CLASSIFICATION,
                "classification_secondary": CLASSIFICATION_SECONDARY,
                "plan_commit": PLAN_COMMIT,
                "payload": payload,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )


def done(name: str) -> bool:
    return (CACHE / f"{name}.json").is_file()


def read(name: str) -> Any:
    return json.loads((CACHE / f"{name}.json").read_text())["payload"]


def stage(name: str, produce) -> Any:
    if done(name):
        return read(name)
    payload = produce()
    write(name, payload)
    return payload


def _carry_verdict(cells: dict[str, Any]) -> dict[str, Any]:
    """Plan §11 and §12, applied to the twelve carry cells.

    Economic materiality decides the **consequence**, never a classification, so
    the verdict is derived here rather than chosen in prose.
    """
    out: dict[str, Any] = {}
    surviving: list[str] = []
    for key, per_panel in cells.items():
        rows = {panel: per_panel.get(panel) for panel in DECIDING_PANELS}
        if not all(rows.values()):
            out[key] = {"decidable": False}
            continue

        gross = [rows[p]["x1.0"]["gross_pips"] for p in DECIDING_PANELS]
        net = [rows[p]["x1.0"]["net_pips"] for p in DECIDING_PANELS]
        net_2c = [rows[p]["x2.0"]["net_pips"] for p in DECIDING_PANELS]
        spot = [rows[p]["x1.0"]["spot_pips"] for p in DECIDING_PANELS]
        income = [rows[p]["x1.0"]["carry_pips"] for p in DECIDING_PANELS]
        tails = [rows[p]["x1.0"].get("top10_day_share") for p in DECIDING_PANELS]
        share = [rows[p]["x1.0"].get("largest_pair_share") for p in DECIDING_PANELS]
        jpy = [rows[p]["x1.0"].get("jpy_mean_net") for p in DECIDING_PANELS]
        non_jpy = [rows[p]["x1.0"].get("non_jpy_mean_net") for p in DECIDING_PANELS]

        gross_positive = all(v > 0 for v in gross)
        same_sign = (net[0] > 0) == (net[1] > 0)
        net_positive = all(v > 0 for v in net)
        survives_2c = all(v > 0 for v in net_2c)
        tail_ok = all(v is None or (v == v and v < TAIL_SHARE_CEILING) for v in tails)
        breadth = all(
            j is not None and n is not None and (j > 0) == (n > 0)
            for j, n in zip(jpy, non_jpy, strict=True)
        )

        survives = bool(gross_positive and same_sign and net_positive and tail_ok and breadth)
        if survives:
            surviving.append(key)
        out[key] = {
            "decidable": True,
            "gross_pips": gross,
            "spot_pips": spot,
            "carry_income_pips": income,
            "net_pips": net,
            "net_pips_2c": net_2c,
            "gross_positive_both_panels": gross_positive,
            "net_same_sign": same_sign,
            "net_positive_both_panels": net_positive,
            "net_positive_at_2c": survives_2c,
            "tail_share_below_ceiling": tail_ok,
            "top10_day_share": tails,
            "largest_pair_share": share,
            "both_blocs_same_sign": breadth,
            "jpy_mean_net": jpy,
            "non_jpy_mean_net": non_jpy,
            "carry_covers_spot_loss": [
                bool(i > 0 and s < 0 and i + s > 0) for i, s in zip(income, spot, strict=True)
            ],
            "survives": survives,
        }
    return {
        "per_cell": out,
        "cells": len(out),
        "surviving": surviving,
        "status": (
            "CARRY_EDGE_NOT_SUPPORTED" if not surviving else "CARRY_EDGE_SUPPORTED_EXPLORATORY"
        ),
    }


def main() -> dict[str, Any]:
    # --------------------------------------------------------------- Stage 1
    frame, provenance = rates.acquire()
    write("s1_rate_provenance", provenance)
    rate_panel = rates.daily_panel(frame, *RATE_SPAN)
    stage(
        "s1_fallback_crosscheck",
        lambda: rates.fallback_crosscheck(rate_panel, start=RATE_SPAN[0], end=RATE_SPAN[1]),
    )

    loaded = {panel_id: panels.load_panel(panel_id) for panel_id in PANELS}
    days = {panel_id: panels.trading_days(frames) for panel_id, frames in loaded.items()}
    with_rates = {
        panel_id: {pair: carry.attach_rates(f, rate_panel, pair) for pair, f in frames.items()}
        for panel_id, frames in loaded.items()
    }
    write(
        "panels",
        {
            panel_id: {
                "declared_span": list(panels.panel_span(panel_id)),
                "measured_span": [
                    str(min(f["ts"].min() for f in frames.values()).date()),
                    str(max(f["ts"].max() for f in frames.values()).date()),
                ],
                "pairs": len(frames),
                "bars": int(sum(len(f) for f in frames.values())),
                "trading_days": days[panel_id],
                "mean_carry_rate_pct": {
                    pair: round(float(np.nanmean(f["carry_rate_pct"].to_numpy())), 4)
                    for pair, f in sorted(with_rates[panel_id].items())
                },
            }
            for panel_id, frames in loaded.items()
        },
    )

    # --------------------------------------------------------------- Stage 2
    cells: dict[str, Any] = {}
    for family in carry.FAMILIES:
        for rebalance in REBALANCE_BARS:
            key = f"{family}|{rebalance}"
            cells[key] = stage(
                f"s2_carry_{family}_{rebalance}",
                lambda family=family, rebalance=rebalance: {
                    panel_id: {
                        f"x{multiplier}": {
                            k: v
                            for k, v in carry.run_family(
                                with_rates[panel_id],
                                rate_panel,
                                family=family,
                                rebalance=rebalance,
                                trading_days=days[panel_id],
                                cost_multiplier=multiplier,
                            ).items()
                            if not k.startswith("_")
                        }
                        for multiplier in COST_MULTIPLIERS
                    }
                    for panel_id in PANELS
                },
            )
    assert len(cells) == CARRY_CELLS, f"{len(cells)} cells, the plan fixed {CARRY_CELLS}"
    verdict = _carry_verdict(cells)
    write("s2_carry_verdict", verdict)

    summary = {
        "stage_1": "POLICY_RATE_SOURCE_ACQUIRED_ALL_EIGHT_CURRENCIES",
        "stage_2": verdict["status"],
        "stage_2_surviving_cells": verdict["surviving"],
    }
    write("stage_summary", summary)
    return summary


if __name__ == "__main__":  # pragma: no cover - the driver
    print(json.dumps(main(), indent=2, sort_keys=True, default=str))
