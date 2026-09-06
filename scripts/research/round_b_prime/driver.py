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


def _retrace_verdict(
    per_panel: dict[str, Any], blocs: dict[str, Any] | None = None
) -> dict[str, Any]:
    """B′-2's kill condition, all five clauses of plan §5.6.

    Clauses 1, 2 and 5 (same sign, both studentized, above the economic floor)
    are read for every threshold. Clauses 3 and 4 — day concentration and
    bloc confinement — are kill conditions *for a cell that got that far*, so
    they are evaluated only where the first three pass, which is also why the
    driver measures the bloc split only for those cells.

    An earlier version of this docstring said "all five clauses of it" while the
    body implemented three: the day trim was applied to the real median alone
    and never to `real − null`, and no JPY/non-JPY split existed for B′-2 at
    all.
    """
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
        first_three = same_sign and both_strong and economically_material

        #: clause 3 -- does the difference survive removing the 10 largest
        #: contributing anchor *days*, on both sides of `real − null`?
        trimmed = {
            name: rows[name]["null"].get("median_retrace_fraction_excluding_top_10_days")
            for name in DECIDING_PANELS
        }
        if first_three and all(trimmed.values()):
            trimmed_diffs = [trimmed[name]["real_minus_null"] for name in DECIDING_PANELS]
            day_robust = all((d > 0) == (diffs[0] > 0) for d in trimmed_diffs)
        else:
            trimmed_diffs = None
            day_robust = None

        #: clause 4 -- is it confined to one bloc, or to the weekend-gap subset?
        bloc = (blocs or {}).get(str(k)) if first_three else None
        if bloc:
            bloc_diffs = {
                name: [
                    bloc[name][b]["median_retrace_fraction"]["real_minus_null"]
                    for b in ("JPY", "non_JPY")
                    if bloc.get(name, {}).get(b, {}).get("median_retrace_fraction")
                ]
                for name in DECIDING_PANELS
            }
            both_blocs = all(
                len(v) == 2 and (v[0] > 0) == (v[1] > 0) == (diffs[0] > 0)
                for v in bloc_diffs.values()
            )
        else:
            bloc_diffs = None
            both_blocs = None

        survives = bool(first_three and day_robust is not False and both_blocs is not False)
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
            "clause_3_day_trim_holds": day_robust,
            "clause_3_trimmed_real_minus_null": trimmed_diffs,
            "clause_4_both_blocs_same_sign": both_blocs,
            "clause_4_bloc_real_minus_null": bloc_diffs,
            "clauses_evaluated": 5 if first_three else 3,
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


def _retrace_familywise(per_k: dict[str, Any]) -> dict[str, Any]:
    """One family-max over B′-2's whole 15-cell family, not one per threshold."""
    observed: list[float] = []
    draws: list[list[float]] = []
    for k in EXCURSION_SIGMAS:
        row = (per_k.get(str(k)) or {}).get("null") or {}
        family = row.get("family_max")
        if not family:
            continue
        observed.append(float(family["observed_max_abs_z"]))
        draws.append([float(v) for v in family["per_draw_max_abs_z"]])
    if not observed:
        return {"decidable": False, "reason": "no threshold produced a family-max"}
    width = min(len(row) for row in draws)
    pooled = np.max(np.array([row[:width] for row in draws]), axis=0)
    peak = max(observed)
    return {
        "thresholds": len(observed),
        "cells": sum(
            (per_k[str(k)]["null"]["family_max"]["cells"])
            for k in EXCURSION_SIGMAS
            if (per_k.get(str(k)) or {}).get("null", {}).get("family_max")
        ),
        "observed_max_abs_z": round(peak, 3),
        "family_wise_p": round(float((np.sum(pooled >= peak) + 1) / (len(pooled) + 1)), 5),
        "draws": int(width),
    }


def _classification(verdicts: dict[str, Any]) -> dict[str, Any]:
    """Plan §11, applied to the four machine verdicts. Prose does not enter here.

    The first version of this round had no such function: the four verdicts were
    written out and the case was chosen in the results document, which is how a
    round whose B′-1 and B′-2 kill conditions were both *unmet* came to be
    recorded as `PRICE_ONLY_PATH_STRUCTURE_SCREEN_NEGATIVE` — the case whose
    pre-registered condition is that all three are empty. Two independent review
    roles found it. The rule now runs on the artifacts.

    Economic materiality is deliberately **not** an input. The plan attached an
    economic floor to B′-2 and none to B′-1, and supplying one after the fact is
    the move pre-registration exists to prevent. It is reported beside the case
    as a disclosed post-hoc annotation, and it governs the *consequence*, never
    the case.
    """
    b1_empty = bool(verdicts["b1"]["kill_condition_met"])
    b2_empty = bool(verdicts["b2"]["kill_condition_met"])
    b4_stable = not verdicts["b4"]["kill_condition_met"]

    if not b1_empty or not b2_empty:
        case, token = "A", "PRICE_PATH_STRUCTURE_SURVIVES_NULL_CONTROL"
    elif b4_stable:
        case, token = "B", "MONTHLY_ONLY_STRUCTURE_SURVIVES"
    else:
        case, token = "C", "PRICE_ONLY_PATH_STRUCTURE_SCREEN_NEGATIVE"

    return {
        "case": case,
        "token": token,
        "inputs": {
            "b1_empty": b1_empty,
            "b2_empty": b2_empty,
            "b4_stable": b4_stable,
            "b1_stable_horizons": verdicts["b1"].get("stable_horizons"),
            "b2_surviving_thresholds": verdicts["b2"].get("surviving_thresholds"),
        },
        "rule": (
            "plan §11: A if B′-1 or B′-2 is non-empty on both deciding panels; "
            "B if both are empty and B′-4 is stable; C if all three are empty; "
            "D if a concrete implementation, sample or null-design reason "
            "prevents a verdict"
        ),
        "economic_materiality_is_not_an_input": True,
    }


def main() -> dict[str, Any]:
    #: the null sanity checks come first, before any real comparison is
    #: computed — one per study. B′-2 had none in the first version of this
    #: round, and the bias its null carried is exactly what one would have
    #: caught.
    write("b1_null_sanity", variance_ratio.null_sanity(draws=40))
    write("b2_null_sanity", retrace.null_sanity())

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

    #: plan §5.4 registers a **secondary** null for B′-2 -- the IID shuffle --
    #: whose difference from the primary says how much of any effect needs
    #: volatility clustering. It was registered and, in the first version of this
    #: round, never run.
    write(
        "b2_secondary_null",
        {
            panel_id: {
                str(k): retrace.against_null(
                    frames, k, draws=RETRACE_DRAWS, seed=SEED, null_name="N1_iid"
                )
                for k in EXCURSION_SIGMAS
            }
            for panel_id, frames in loaded.items()
            if panel_id in DECIDING_PANELS
        },
    )

    #: clause 4 needs a bloc split, and a bloc split costs two more null passes
    #: per cell. Only cells that already passed clauses 1, 2 and 5 can be killed
    #: by it, so only those are measured.
    provisional = _retrace_verdict(geometry)
    candidates = [
        k
        for k, row in provisional["per_threshold"].items()
        if row.get("same_sign")
        and row.get("both_studentized_ge_2")
        and row.get("above_economic_floor")
    ]
    blocs: dict[str, Any] = {}
    for k in candidates:
        blocs[str(k)] = {}
        for panel_id in DECIDING_PANELS:
            frames = loaded[panel_id]
            split = {
                "JPY": {p: f for p, f in frames.items() if p in panels.JPY_PAIRS},
                "non_JPY": {p: f for p, f in frames.items() if p not in panels.JPY_PAIRS},
            }
            blocs[str(k)][panel_id] = {
                name: retrace.against_null(sub, float(k), draws=RETRACE_DRAWS, seed=SEED)["null"]
                or {}
                for name, sub in split.items()
            }
    write("b2_bloc_split", {"candidates": candidates, "per_threshold": blocs})

    #: the family-max across all three thresholds together, which is the family
    #: the plan registers -- 3 thresholds x 5 statistics = 15 cells
    write(
        "b2_familywise",
        {
            panel_id: _retrace_familywise(geometry[panel_id])
            for panel_id in DECIDING_PANELS
            if panel_id in geometry
        },
    )
    write("b2_verdict", _retrace_verdict(geometry, blocs))
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
                    #: the two numbers `harvestability` reports are a hundredfold
                    #: apart -- a floor assuming one suboptimal rule and a ceiling
                    #: crediting the whole variance deficit to one component. The
                    #: ACF measures directly what the coarse-base test only
                    #: infers, and the linear bound fills the gap between them.
                    "acf": diagnostics.autocorrelation_function(frames),
                    "optimal_linear_predictor": diagnostics.optimal_linear_predictor(frames),
                }
                for panel_id, frames in loaded.items()
            },
        },
    )

    # ---------------------------------------------------------------- B′-VOL
    write("bvol_inventory", volume_inventory.inventory())

    verdicts = {
        name: json.loads((CACHE / f"{name}_verdict.json").read_text())["payload"]
        for name in ("b1", "b2", "b4")
    }
    classification = _classification(verdicts)
    write("classification", classification)
    summary = {
        "b1": verdicts["b1"]["status"],
        "b2": verdicts["b2"]["status"],
        "b2_htf": json.loads((CACHE / "b2_htf_context.json").read_text())["payload"]["status"],
        "b4": verdicts["b4"]["status"],
        "classification": classification["case"],
        "classification_token": classification["token"],
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
