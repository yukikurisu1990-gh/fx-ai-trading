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
    VOLUME_REPRESENTATIONS,
    calendar_events,
    carry,
    opportunity,
    rates,
)
from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import volume as volume_reader
from scripts.research.monetizability import volume_info
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
        #: an unmeasurable tail share is **not** a pass. The first version read
        #: `v is None or ...`, so a cell whose daily total was non-positive --
        #: which is exactly when the share is undefined -- cleared the clause.
        tail_ok = all(v is not None and v == v and v < TAIL_SHARE_CEILING for v in tails)
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


def _improves(per_panel: dict[str, Any], deciding: tuple[str, ...]) -> dict[str, bool]:
    """Does M3 beat M1 on **every** deciding panel? Fails closed.

    `all(...)` over an empty list is `True`, so a missing panel would have
    turned every representation into an improvement on no data at all. Its own
    function so that property can be tested.
    """
    rows = [per_panel[panel] for panel in deciding if panel in per_panel]
    complete = len(rows) == len(deciding) and bool(rows)
    return {
        representation: complete
        and all(
            row["M3_combined"].get(representation, float("-inf")) > row["M1_expected_return_only"]
            for row in rows
        )
        for representation in VOLUME_REPRESENTATIONS
    }


def _integration(
    with_volume: dict[str, dict[str, Any]],
    rate_panel: Any,
    days: dict[str, int],
    family: str,
    rebalance: str,
) -> dict[str, Any]:
    """M0-M3 (plan §14). The only question is whether M3 improves on M1."""
    stride = REBALANCE_BARS[rebalance]
    k = int(family.split("_k")[1])
    out: dict[str, Any] = {"base_family": family, "base_rebalance": rebalance}

    for panel_id, frames in with_volume.items():
        targets = carry.cross_sectional_positions(rate_panel, tuple(frames), k=k)
        states = {pair: opportunity.daily_state(frame) for pair, frame in frames.items()}
        m1_daily: dict[str, Any] = {}
        m1_carry: dict[str, Any] = {}
        m1_spot: dict[str, Any] = {}
        m2_daily: dict[str, Any] = {}
        for pair, frame in frames.items():
            expected = carry.signal_cross_sectional(frame, targets[pair], stride=stride, phase=0)
            evaluated = carry.evaluate(frame, expected, pair=pair)
            m1_daily[pair] = evaluated["_daily"]
            #: the two lines separately, so the filter's damage can be attributed
            #: rather than asserted -- a review role measured removed SPOT
            #: dominating removed carry in 8 of 10 deciding cells
            m1_carry[pair] = evaluated["_daily_carry"]
            m1_spot[pair] = evaluated["_daily_spot"]
            #: M2 -- timing with no expected-return view. A constant long is the
            #: direction-free control: if opportunity timing alone earned
            #: anything, it would show here.
            flat = expected.copy()
            flat[:] = 1.0
            m2_daily[pair] = carry.evaluate(frame, flat, pair=pair)["_daily"]

        row: dict[str, Any] = {
            "M0_no_trade": 0.0,
            "M1_expected_return_only": round(
                float(np.mean([s.sum() for s in m1_daily.values()])), 2
            ),
            "M1_spot_pips": round(float(np.mean([v.sum() for v in m1_spot.values()])), 2),
            "M1_carry_pips": round(float(np.mean([v.sum() for v in m1_carry.values()])), 2),
            "M2_timing_only": {},
            "M3_combined": {},
            "trades_removed_share": {},
            "removed_carry": {},
            "removed_spot": {},
        }
        for representation in VOLUME_REPRESENTATIONS:
            usable = {p: states[p] for p in m1_daily if not states[p].empty}
            if not usable:
                continue
            m3 = [
                opportunity.gated_daily(m1_daily[p], usable[p], representation).sum()
                for p in usable
            ]
            m2 = [
                opportunity.gated_daily(m2_daily[p], usable[p], representation).sum()
                for p in usable
            ]
            kept = [
                float(
                    opportunity.filter_mask(usable[p], representation)
                    .reindex(m1_daily[p].index)
                    .fillna(False)
                    .mean()
                )
                for p in usable
            ]
            removed_carry = [
                float(
                    m1_carry[p].sum()
                    - opportunity.gated_daily(m1_carry[p], usable[p], representation).sum()
                )
                for p in usable
            ]
            removed_spot = [
                float(
                    m1_spot[p].sum()
                    - opportunity.gated_daily(m1_spot[p], usable[p], representation).sum()
                )
                for p in usable
            ]
            row["M3_combined"][representation] = round(float(np.mean(m3)), 2)
            row["M2_timing_only"][representation] = round(float(np.mean(m2)), 2)
            row["trades_removed_share"][representation] = round(1.0 - float(np.mean(kept)), 4)
            row["removed_carry"][representation] = round(float(np.mean(removed_carry)), 2)
            row["removed_spot"][representation] = round(float(np.mean(removed_spot)), 2)
        out[panel_id] = row

    improves = _improves(out, DECIDING_PANELS)
    out["m3_beats_m1_on_both_deciding_panels"] = improves
    out["any_representation_improves"] = any(improves.values())
    out["stage_3_status"] = "VOLUME_INFORMATION_MEASURED_AT_THE_CARRY_HORIZON"
    out["status"] = (
        "OPPORTUNITY_TIMING_ADDS_INCREMENTAL_VALUE"
        if out["any_representation_improves"]
        else "OPPORTUNITY_TIMING_ADDS_NO_INCREMENTAL_VALUE"
    )
    return out


def main() -> dict[str, Any]:
    # --------------------------------------------------------------- Stage 1
    frame, provenance = rates.acquire()
    rate_panel = rates.daily_panel(frame, *RATE_SPAN)
    #: written **after** the panel is built, so the EUR override's own source,
    #: digest and coverage are in the record rather than only BIS's
    provenance["override"] = dict(rates.OVERRIDE_PROVENANCE)
    write("s1_rate_provenance", provenance)
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

    # --------------------------------------------------------------- Stage 3
    with_volume = {
        panel_id: {
            pair: volume_info.attach(frame, volume_reader.load(panel_id, pair))
            for pair, frame in frames.items()
        }
        for panel_id, frames in with_rates.items()
    }
    stage(
        "s3_volume_information",
        lambda: {
            panel_id: opportunity.information(frames) for panel_id, frames in with_volume.items()
        },
    )

    # --------------------------------------------------------------- Stage 4
    #: The base is the one carry cell with gross economics on both deciding
    #: panels. It fails its own pass condition on tail dependence, which is a
    #: *timing* failure -- so the integration question is not whether the filter
    #: makes a good signal better, but whether it addresses the specific way
    #: this one breaks.
    base_cell = "cross_sectional_k3"
    base_rebalance = "weekly"
    integration = stage(
        "s4_integration",
        lambda: _integration(with_volume, rate_panel, days, base_cell, base_rebalance),
    )

    # ------------------------------------------------------ Route C: calendar
    #: carry is weak and volume times nothing, so the next source has to be
    #: exogenous rather than another transform of the same prices
    events = stage(
        "s5_calendar_population",
        lambda: {
            panel_id: calendar_events.event_population(frames, rate_panel)
            for panel_id, frames in with_volume.items()
        },
    )
    permutations = stage(
        "s5_calendar_permutation",
        lambda: {
            panel_id: calendar_events.permutation_test(frames, rate_panel)
            for panel_id, frames in with_volume.items()
        },
    )
    calendar_verdict = calendar_events.verdict(events, DECIDING_PANELS, permutations)
    write("s5_calendar_verdict", calendar_verdict)

    summary = {
        "stage_1": "POLICY_RATE_SOURCE_ACQUIRED_ALL_EIGHT_CURRENCIES",
        "stage_2": verdict["status"],
        "stage_2_surviving_cells": verdict["surviving"],
        "stage_3": integration["stage_3_status"],
        "stage_4": integration["status"],
        "route_c_calendar": calendar_verdict.get("status", "NOT_DECIDABLE"),
        "route_c_cost_advantage": calendar_verdict.get("cost_advantage_status", "NOT_DECIDABLE"),
    }
    write("stage_summary", summary)
    return summary


if __name__ == "__main__":  # pragma: no cover - the driver
    print(json.dumps(main(), indent=2, sort_keys=True, default=str))
