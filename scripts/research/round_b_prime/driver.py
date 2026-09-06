"""Round B′'s driver — every number in the report comes from here.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

`python -m scripts.research.round_b_prime.driver` regenerates the whole round.
Three earlier rounds had headline numbers with no code behind them; this one
writes the null sanity check first, and every real-versus-null comparison after
it.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.round_a import DECIDING_PANELS, PANELS, panels
from scripts.research.round_a import benchmarks as round_a_benchmarks
from scripts.research.round_b_prime import (
    EXCURSION_SIGMAS,
    NULL_DRAWS,
    RETRACE_DIFFERENCE_FLOOR,
    SEED,
    VR_HORIZONS,
    diagnostics,
    monthly,
    retrace,
    variance_ratio,
    volume_inventory,
)

CACHE = bars_module.REPO_ROOT / "artifacts" / "track_a_scratch" / "round_b_prime"
#: fewer null draws for the retrace study: each draw re-runs the anchor detector
#: over every pair, which is far heavier than a variance ratio
RETRACE_DRAWS = 40
VR_DRAWS = NULL_DRAWS


def write(name: str, payload: Any) -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f"{name}.json").write_text(
        json.dumps(
            {
                "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
                "classification_secondary": "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
                "payload": payload,
            },
            indent=2,
            sort_keys=True,
            default=str,
        ),
        encoding="utf-8",
    )


def _vr_verdict(per_panel: dict[str, Any]) -> dict[str, Any]:
    """B′-1's kill condition: is `real − N2` stable across the two deciding panels?"""
    out: dict[str, Any] = {}
    stable: list[int] = []
    for q in VR_HORIZONS:
        rows = {
            name: per_panel[name]["N2_sign_flip"]["per_horizon"].get(q)
            for name in DECIDING_PANELS
            if q in per_panel[name]["N2_sign_flip"]["per_horizon"]
        }
        if len(rows) != len(DECIDING_PANELS):
            continue
        diffs = [rows[name]["real_minus_null"] for name in DECIDING_PANELS]
        zs = [rows[name]["studentized"] or 0.0 for name in DECIDING_PANELS]
        same_sign = (diffs[0] > 0) == (diffs[1] > 0)
        both_strong = all(abs(z) >= 2 for z in zs)
        if same_sign and both_strong:
            stable.append(q)
        out[q] = {
            "real_minus_null": [round(d, 5) for d in diffs],
            "studentized": [round(z, 2) for z in zs],
            "same_sign": same_sign,
            "both_studentized_ge_2": both_strong,
        }
    return {
        "per_horizon": out,
        "stable_horizons": stable,
        "kill_condition_met": not stable,
        "status": (
            "NULL_CONTROLLED_AGGREGATE_PATH_STRUCTURE_NOT_ESTABLISHED"
            if not stable
            else "AGGREGATE_PATH_STRUCTURE_SURVIVES_N2"
        ),
    }


def _retrace_verdict(per_panel: dict[str, Any]) -> dict[str, Any]:
    """B′-2's kill condition, all five clauses of it."""
    out: dict[str, Any] = {}
    surviving: list[float] = []
    for k in EXCURSION_SIGMAS:
        rows = {name: per_panel[name].get(str(k)) for name in DECIDING_PANELS}
        if not all(rows.values()) or not all(r.get("null") for r in rows.values()):
            out[k] = {"decidable": False, "reason": "no anchors or no null on a deciding panel"}
            continue
        stats = {
            name: rows[name]["null"].get("median_retrace_fraction") for name in DECIDING_PANELS
        }
        if not all(stats.values()):
            out[k] = {"decidable": False, "reason": "median retrace fraction unavailable"}
            continue
        diffs = [stats[name]["real_minus_null"] for name in DECIDING_PANELS]
        zs = [stats[name]["studentized"] or 0.0 for name in DECIDING_PANELS]
        same_sign = (diffs[0] > 0) == (diffs[1] > 0)
        both_strong = all(abs(z) >= 2 for z in zs)
        economically_material = all(abs(d) >= RETRACE_DIFFERENCE_FLOOR for d in diffs)
        anchors = [rows[name]["real"]["anchors"] for name in DECIDING_PANELS]
        survives = same_sign and both_strong and economically_material
        if survives:
            surviving.append(k)
        out[k] = {
            "decidable": True,
            "anchors": anchors,
            "real_minus_null": [round(d, 5) for d in diffs],
            "studentized": [round(z, 2) for z in zs],
            "same_sign": same_sign,
            "both_studentized_ge_2": both_strong,
            "above_economic_floor": economically_material,
            "floor": RETRACE_DIFFERENCE_FLOOR,
            "survives": survives,
        }
    return {
        "per_threshold": out,
        "surviving_thresholds": surviving,
        "kill_condition_met": not surviving,
        "status": (
            "EXCURSION_ANCHORED_RETRACE_GEOMETRY_NOT_ESTABLISHED"
            if not surviving
            else "EXCURSION_ANCHORED_RETRACE_GEOMETRY_SURVIVES_MATCHED_NULL"
        ),
    }


def _htf_diagnostic(anchor_frames: dict[str, dict[str, pd.DataFrame]]) -> dict[str, Any]:
    """Two context variables, two states each, one comparison. Nothing more."""
    out: dict[str, Any] = {}
    for context in ("htf_trend", "htf_location"):
        per_panel: dict[str, Any] = {}
        for panel_id, per_k in anchor_frames.items():
            entry: dict[str, Any] = {}
            for k, frame in per_k.items():
                if frame.empty or context not in frame:
                    continue
                grouped = frame.groupby(context)["max_retrace_fraction"]
                entry[k] = {
                    state: {
                        "anchors": int(len(frame[frame[context] == state])),
                        "median_retrace_fraction": round(float(value), 5),
                    }
                    for state, value in grouped.median().items()
                }
                states = sorted(entry[k])
                if len(states) == 2:
                    entry[k]["difference"] = round(
                        entry[k][states[0]]["median_retrace_fraction"]
                        - entry[k][states[1]]["median_retrace_fraction"],
                        5,
                    )
                    entry[k]["states"] = states
            per_panel[panel_id] = entry
        #: reproduce in sign across the two deciding panels, per threshold
        reproduces: list[str] = []
        for k in {str(x) for x in EXCURSION_SIGMAS}:
            diffs = [
                per_panel[name].get(k, {}).get("difference")
                for name in DECIDING_PANELS
                if k in per_panel.get(name, {})
            ]
            if (
                len(diffs) == len(DECIDING_PANELS)
                and all(d is not None for d in diffs)
                and (diffs[0] > 0) == (diffs[1] > 0)
            ):
                reproduces.append(k)
        out[context] = {"per_panel": per_panel, "sign_reproduces_at": sorted(reproduces)}
    any_reproduces = any(v["sign_reproduces_at"] for v in out.values())
    out["status"] = (
        "HTF_GEOMETRY_CONTEXT_NOT_SUPPORTED"
        if not any_reproduces
        else "HTF_GEOMETRY_CONTEXT_DIFFERENCE_REPRODUCES"
    )
    out["kill_condition_met"] = not any_reproduces
    return out


def _monthly_verdict(per_panel: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    stable: list[str] = []
    ids = [monthly.cell_id(row) for row in per_panel[PANELS[0]]]
    for cid in ids:
        rows = {
            name: next(r for r in per_panel[name] if monthly.cell_id(r) == cid) for name in PANELS
        }
        nets = [rows[name]["net_pips_per_pair"] for name in DECIDING_PANELS]
        grosses = [rows[name]["gross_pips_per_pair"] for name in DECIDING_PANELS]
        same_sign = (nets[0] > 0) == (nets[1] > 0)
        gross_present = all(g > 0 for g in grosses)
        if same_sign and gross_present:
            stable.append(cid)
        out[cid] = {
            "net": nets,
            "gross": grosses,
            "same_sign": same_sign,
            "gross_positive_both": gross_present,
            "development_2025_net": rows["development_2025"]["net_pips_per_pair"],
        }
    return {
        "per_cell": out,
        "stable_cells": stable,
        "kill_condition_met": not stable,
        "status": (
            "MONTHLY_TSMOM_NOT_SUPPORTED_IN_EXISTING_PRICE_HISTORY"
            if not stable
            else "MONTHLY_TSMOM_SIGN_STABLE_ON_DECIDING_PANELS"
        ),
    }


def main() -> dict[str, Any]:
    #: the null sanity check comes first, before any real comparison is computed
    write("b1_null_sanity", variance_ratio.null_sanity(draws=40))

    loaded = {panel_id: panels.load_panel(panel_id) for panel_id in PANELS}
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
                "trading_days": panels.trading_days(frames),
            }
            for panel_id, frames in loaded.items()
        },
    )

    # ---------------------------------------------------------------- B′-1
    vr = {
        panel_id: variance_ratio.against_nulls(frames, draws=VR_DRAWS)
        for panel_id, frames in loaded.items()
    }
    write("b1_variance_ratio", vr)
    write("b1_verdict", _vr_verdict(vr))
    write(
        "b1_bloc_split",
        {panel_id: variance_ratio.bloc_split(frames) for panel_id, frames in loaded.items()},
    )
    write(
        "b1_temporal_stability",
        {
            panel_id: variance_ratio.temporal_stability(frames)
            for panel_id, frames in loaded.items()
        },
    )

    # ---------------------------------------------------------------- B′-2
    geometry: dict[str, Any] = {}
    anchor_frames: dict[str, dict[str, pd.DataFrame]] = {}
    for panel_id, frames in loaded.items():
        per_k: dict[str, Any] = {}
        per_k_frames: dict[str, pd.DataFrame] = {}
        for k in EXCURSION_SIGMAS:
            per_k[str(k)] = retrace.against_null(frames, k, draws=RETRACE_DRAWS, seed=SEED)
            _, anchors = retrace.panel_geometry(frames, k)
            per_k_frames[str(k)] = anchors
        geometry[panel_id] = per_k
        anchor_frames[panel_id] = per_k_frames
    write("b2_retrace_geometry", geometry)
    write("b2_verdict", _retrace_verdict(geometry))
    write(
        "b2_subsets",
        {
            panel_id: {
                k: _subset_diagnostics(frame) for k, frame in per_k.items() if not frame.empty
            }
            for panel_id, per_k in anchor_frames.items()
        },
    )
    write("b2_htf_context", _htf_diagnostic(anchor_frames))

    # ---------------------------------------------------------------- B′-4
    tsmom = {panel_id: monthly.screen(frames) for panel_id, frames in loaded.items()}
    write(
        "b4_monthly_tsmom",
        {
            panel_id: [{k: v for k, v in row.items() if k != "_daily"} for row in rows]
            for panel_id, rows in tsmom.items()
        },
    )
    write("b4_verdict", _monthly_verdict(tsmom))
    write(
        "b4_familywise",
        {
            panel_id: round_a_benchmarks.studentized_family_max(
                {monthly.cell_id(row): row["_daily"] for row in rows}
            )
            for panel_id, rows in tsmom.items()
        },
    )

    # ------------------------------------------- POST_HOC_DIAGNOSTIC_ONLY
    #: Not among the 28 pre-registered cells and unable to carry a verdict. They
    #: exist because the pre-registered statistics cannot say *what* survived:
    #: whether the variance deficit is a one-bar quoting effect, whether the
    #: anchor populations are comparable, and whether the surviving effect is
    #: large enough to pay for a round trip.
    write(
        "post_hoc_diagnostics",
        {
            "classification": diagnostics.CLASSIFICATION,
            **{
                panel_id: {
                    "microstructure": diagnostics.microstructure_split(frames),
                    "anchor_population": diagnostics.all_anchor_populations(frames, draws=20),
                    "harvestability": diagnostics.harvestability(frames),
                }
                for panel_id, frames in loaded.items()
            },
        },
    )

    # ---------------------------------------------------------------- B′-VOL
    write("bvol_inventory", volume_inventory.inventory())

    summary = {
        "b1": json.loads((CACHE / "b1_verdict.json").read_text())["payload"]["status"],
        "b2": json.loads((CACHE / "b2_verdict.json").read_text())["payload"]["status"],
        "b2_htf": json.loads((CACHE / "b2_htf_context.json").read_text())["payload"]["status"],
        "b4": json.loads((CACHE / "b4_verdict.json").read_text())["payload"]["status"],
    }
    write("round_b_prime_summary", summary)
    return summary


def _subset_diagnostics(frame: pd.DataFrame) -> dict[str, Any]:
    """Weekend-gap and tail diagnostics, per the plan's §5.5 and §16."""
    out: dict[str, Any] = {"anchors": int(len(frame))}
    for label, subset in (
        ("continuous", frame[~frame["weekend_gap_anchor"]]),
        ("weekend_gap", frame[frame["weekend_gap_anchor"]]),
    ):
        out[label] = {
            "anchors": int(len(subset)),
            "median_retrace_fraction": round(float(subset["max_retrace_fraction"].median()), 5)
            if len(subset)
            else None,
        }
    #: contribution concentration, by anchor rather than by day: the anchors are
    #: the observations here, and there is no P&L series to concentrate
    values = frame["max_retrace_fraction"].to_numpy()
    ranked = np.sort(values)
    out["tails"] = {
        f"median_excluding_{n}_largest": round(float(np.median(ranked[:-n])), 5)
        for n in (1, 3, 5, 10, 20)
        if len(ranked) > n
    } | {
        f"median_excluding_{n}_smallest": round(float(np.median(ranked[n:])), 5)
        for n in (1, 3, 5, 10, 20)
        if len(ranked) > n
    }
    out["ambiguous_bars"] = int(frame.attrs.get("ambiguous_bars", 0))
    return out


if __name__ == "__main__":  # pragma: no cover - the driver
    print(json.dumps(main(), indent=2, sort_keys=True, default=str))
