"""The monetizability package, run once, in the order the plan fixed.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Stage 1A and Stage 1C both write a **sanity artifact first**, before any real
comparison of theirs is computed. Round B′ shipped a null that was wrong for two
months of work because B′-2 had no sanity check; the same shape is not repeated.

Stage 1B's noise reference and positive control are written first for the same
reason, and they are the evidence behind plan amendment A-1.
"""

from __future__ import annotations

import json
from typing import Any

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import volume as volume_reader
from scripts.research.monetizability import (
    BOUND_HORIZONS,
    CLASSIFICATION,
    CLASSIFICATION_SECONDARY,
    COST_MULTIPLIERS,
    EXCURSION_SIGMAS,
    NULL_DRAWS,
    ORACLE_NET_PER_EVENT_FLOOR_IN_COSTS,
    PLAN_COMMIT,
    SEED,
    TAIL_SHARE_CEILING,
    VOLUME_REDUNDANCY_R2,
    geometry,
    oracle,
    volume_info,
)
from scripts.research.round_a import DECIDING_PANELS, PANELS, panels
from scripts.research.round_b_prime import retrace

CACHE = bars_module.REPO_ROOT / "artifacts" / "track_a_scratch" / "monetizability"


def done(name: str) -> bool:
    """Has this artifact already been produced by an earlier attempt?

    The run is hours long, so a stage that finished is not repeated. Everything
    here is seeded, so a resumed run produces the same artifacts a single pass
    would — and the final pass is verified by re-reading them, not by trusting
    this.
    """
    return (CACHE / f"{name}.json").is_file()


def read(name: str) -> Any:
    return json.loads((CACHE / f"{name}.json").read_text())["payload"]


def stage(name: str, produce) -> Any:
    if done(name):
        return read(name)
    payload = produce()
    write(name, payload)
    return payload


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


def _economic_gate(referenced: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Plan §11 as amended by A-1: E1′, E2′, E3 and E4, all on B-3.

    Economic materiality decides the **consequence** here rather than a
    classification, so unlike Round B′ there is no risk of it choosing a case.
    """
    populations: dict[str, Any] = {}
    for population in referenced[DECIDING_PANELS[0]]:
        rows = {panel: referenced[panel].get(population) for panel in DECIDING_PANELS}
        if not all(rows.values()) or not all((r or {}).get("null") for r in rows.values()):
            populations[population] = {"decidable": False}
            continue
        excess = {
            panel: (rows[panel]["null"].get("b3_net_per_event") or {}).get("real_minus_null")
            for panel in DECIDING_PANELS
        }
        cost = {panel: rows[panel]["real"]["median_cost"] for panel in DECIDING_PANELS}
        if any(v is None for v in excess.values()):
            populations[population] = {"decidable": False}
            continue
        in_costs = {
            panel: excess[panel] / cost[panel] if cost[panel] else None for panel in DECIDING_PANELS
        }
        e1 = all(
            v is not None and v >= ORACLE_NET_PER_EVENT_FLOOR_IN_COSTS for v in in_costs.values()
        )
        tail = {panel: rows[panel]["real"].get("b3_top10_day_share") for panel in DECIDING_PANELS}
        e3 = all(v is not None and v == v and v < TAIL_SHARE_CEILING for v in tail.values())
        populations[population] = {
            "decidable": True,
            "b3_excess_over_null": excess,
            "b3_excess_in_costs": {k: round(v, 4) for k, v in in_costs.items() if v is not None},
            "E1_excess_at_least_half_a_cost": e1,
            "E3_tail_share_below_ceiling": e3,
            "b3_top10_day_share": tail,
        }
    return populations


def main() -> dict[str, Any]:
    # ------------------------------------------------- sanity, before anything
    stage("s1a_null_sanity", lambda: retrace.null_sanity(draws=40))
    stage("s1b_noise_reference", lambda: oracle.noise_reference(horizons=BOUND_HORIZONS, seed=SEED))
    stage(
        "s1b_signal_reference", lambda: oracle.signal_reference(horizons=BOUND_HORIZONS, seed=SEED)
    )

    loaded = {panel_id: panels.load_panel(panel_id) for panel_id in PANELS}
    days = {panel_id: panels.trading_days(frames) for panel_id, frames in loaded.items()}
    stage(
        "panels",
        lambda: {
            panel_id: {
                "declared_span": list(panels.panel_span(panel_id)),
                "measured_span": [
                    str(min(f["ts"].min() for f in frames.values()).date()),
                    str(max(f["ts"].max() for f in frames.values()).date()),
                ],
                "pairs": len(frames),
                "bars": int(sum(len(f) for f in frames.values())),
                "trading_days": days[panel_id],
            }
            for panel_id, frames in loaded.items()
        },
    )

    # --------------------------------------------------------------- Stage 1A
    stage_1a = {
        panel_id: stage(
            f"s1a_geometry_{panel_id}",
            lambda frames=frames: {
                str(k): geometry.against_null(frames, k, draws=NULL_DRAWS, seed=SEED)
                for k in EXCURSION_SIGMAS
            },
        )
        for panel_id, frames in loaded.items()
    }
    blocs = {
        str(k): {
            panel_id: stage(
                f"s1a_bloc_{panel_id}_{k}",
                lambda panel_id=panel_id, k=k: geometry.bloc_split(
                    loaded[panel_id], k, draws=NULL_DRAWS, seed=SEED
                ),
            )
            for panel_id in DECIDING_PANELS
        }
        for k in EXCURSION_SIGMAS
    }
    stage_1a_verdict = geometry.verdict(stage_1a, blocs, DECIDING_PANELS)
    write("s1a_verdict", stage_1a_verdict)

    # --------------------------------------------------------------- Stage 1B
    per_panel = {
        panel_id: stage(
            f"s1b_bounds_{panel_id}",
            lambda frames=frames, panel_id=panel_id: oracle.null_referenced(
                frames,
                trading_days=days[panel_id],
                horizons=BOUND_HORIZONS,
                thresholds=EXCURSION_SIGMAS,
                draws=NULL_DRAWS,
                seed=SEED,
                cost_multipliers=COST_MULTIPLIERS,
            ),
        )
        for panel_id, frames in loaded.items()
    }
    referenced = {
        f"x{multiplier}": {
            panel_id: per_panel[panel_id][f"x{multiplier}"] for panel_id in per_panel
        }
        for multiplier in COST_MULTIPLIERS
    }
    gate = {
        f"x{multiplier}": _economic_gate(referenced[f"x{multiplier}"])
        for multiplier in COST_MULTIPLIERS
    }
    passing = [
        population
        for population, row in gate["x1.0"].items()
        if row.get("decidable")
        and row.get("E1_excess_at_least_half_a_cost")
        and row.get("E3_tail_share_below_ceiling")
        and gate["x2.0"].get(population, {}).get("E1_excess_at_least_half_a_cost")
    ]
    stage_1b_verdict = {
        "gate": gate,
        "populations_passing": passing,
        "status": (
            "PATH_STRUCTURE_HAS_ECONOMIC_HEADROOM"
            if passing
            else "PATH_STRUCTURE_STATISTICALLY_REAL_BUT_ECONOMICALLY_TOO_SMALL"
        ),
    }
    write("s1b_verdict", stage_1b_verdict)

    # --------------------------------------------------------------- Stage 1C
    with_volume = {
        panel_id: {
            pair: volume_info.attach(frame, volume_reader.load(panel_id, pair))
            for pair, frame in frames.items()
        }
        for panel_id, frames in loaded.items()
    }
    stage(
        "s1c_coverage",
        lambda: {panel_id: volume_info.coverage(f) for panel_id, f in with_volume.items()},
    )
    redundancy = stage(
        "s1c_redundancy",
        lambda: {panel_id: volume_info.redundancy(f) for panel_id, f in with_volume.items()},
    )
    incremental = stage(
        "s1c_incremental",
        lambda: {
            panel_id: volume_info.incremental(with_volume[panel_id], draws=NULL_DRAWS, seed=SEED)
            for panel_id in DECIDING_PANELS
        },
    )
    stage(
        "s1c_persistence",
        lambda: {panel_id: volume_info.persistence(f) for panel_id, f in with_volume.items()},
    )

    redundant_r2 = all(
        (redundancy[panel_id].get("median_r2") or 0.0) >= VOLUME_REDUNDANCY_R2
        for panel_id in DECIDING_PANELS
    )
    forward = {
        panel_id: {
            target: (row or {}).get("studentized") for target, row in incremental[panel_id].items()
        }
        for panel_id in DECIDING_PANELS
    }
    any_forward = any(
        z is not None and abs(z) >= 2.0 for row in forward.values() for z in row.values()
    )
    stage_1c_verdict = {
        "median_r2": {p: redundancy[p].get("median_r2") for p in DECIDING_PANELS},
        "redundancy_threshold": VOLUME_REDUNDANCY_R2,
        "r2_above_threshold_on_both": redundant_r2,
        "forward_studentized": forward,
        "any_forward_relation": any_forward,
        "status": (
            "TICK_VOLUME_INFORMATION_REDUNDANT"
            if redundant_r2 and not any_forward
            else "TICK_VOLUME_INFORMATION_INCREMENTALLY_DISTINCT"
        ),
    }
    write("s1c_verdict", stage_1c_verdict)

    summary = {
        "stage_1a": stage_1a_verdict["status"],
        "stage_1a_surviving_thresholds": stage_1a_verdict["surviving_thresholds"],
        "stage_1b": stage_1b_verdict["status"],
        "stage_1b_populations_passing": passing,
        "stage_1c": stage_1c_verdict["status"],
    }
    write("stage_1_summary", summary)
    return summary


if __name__ == "__main__":  # pragma: no cover - the driver
    print(json.dumps(main(), indent=2, sort_keys=True, default=str))
