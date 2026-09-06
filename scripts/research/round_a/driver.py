"""Round A's driver — every number in the report comes from here.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Round 2's post-mortem found six of seven artefacts produced by scratch scripts
that no longer existed, and the supplemental and momentum rounds each repeated it
once more. So: `python -m scripts.research.round_a.driver` regenerates the whole
Round A report, and nothing is transcribed from anywhere else.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import familywise
from scripts.research.exploratory_m15 import momentum_inference as inference
from scripts.research.round_a import (
    DECIDING_PANELS,
    PANELS,
    atlas,
    benchmarks,
    ledger,
    panels,
    screen,
)

CACHE = bars_module.REPO_ROOT / "artifacts" / "track_a_scratch" / "round_a"
#: fewer draws than the 20,000 a single headline gets: this runs 117 times
SCREEN_BOOTSTRAP_DRAWS = 5_000


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


def structural_candidates(
    screen_rows: list[dict[str, Any]], atlas_verdicts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """The plan's six conditions, applied together.

    Sign agreement is condition 1 of 6. With 39 cells and two periods roughly ten
    agree by chance, which is exactly why the other five exist — an earlier round
    of this programme promoted a cell on consistency alone and had to withdraw it.
    """
    verdict_by_key = {
        (row["horizon"], row["bloc"], row["state"]): row["verdict"]
        for row in atlas_verdicts
        if row["table"] == "atr"
    }
    #: `atlas` labels this table `overall_unregistered` because it is not one of
    #: the plan's 105 registered cells. A first version of this rename left the
    #: lookup here on the old name, so the dict was empty and condition 4 failed
    #: for all 30 non-F1 cells — silently, because a missing key defaults to
    #: `insufficient_data`.
    overall_verdict = {
        (row["horizon"], row["bloc"]): row["verdict"]
        for row in atlas_verdicts
        if row["table"] == "overall_unregistered"
    }
    if not overall_verdict:
        raise RuntimeError("the atlas emitted no unconditioned table; condition 4 cannot resolve")

    by_cell: dict[str, dict[str, dict[str, Any]]] = {}
    for row in screen_rows:
        by_cell.setdefault(screen.cell_id(row), {})[row["panel"]] = row

    out: list[dict[str, Any]] = []
    for cid, per_panel in sorted(by_cell.items()):
        if not all(p in per_panel for p in PANELS):
            continue
        first, second = (per_panel[p] for p in DECIDING_PANELS)
        third = per_panel["development_2025"]
        if not first.get("entries") or not second.get("entries"):
            continue

        a, b, c = (
            first["mean_pips_per_entry"],
            second["mean_pips_per_entry"],
            third.get("mean_pips_per_entry", 0.0),
        )
        checks: dict[str, bool] = {}
        checks["1_two_periods_agree_in_sign"] = (a > 0 and b > 0) or (a < 0 and b < 0)
        smaller = min(abs(a), abs(b))
        checks["2_development_not_strong_counter_evidence"] = not ((c * a < 0) and abs(c) > smaller)
        checks["3_effect_at_least_2x_cost"] = all(
            abs(row["effect_over_cost"] or 0.0) >= screen.MIN_EFFECT_OVER_COST
            for row in (first, second)
        )
        #: T1 tradability for the matching horizon; the screen's cells are not
        #: ATR-partitioned except for F1, so F1 uses its own ATR cell and the
        #: others use the horizon's unconditioned verdict
        if first["family"] == "F1_atr":
            keys = [(first["horizon"], "ALL", first["level"])]
            verdicts = [verdict_by_key.get(k, "insufficient_data") for k in keys]
        else:
            verdicts = [overall_verdict.get((first["horizon"], "ALL"), "insufficient_data")]
        checks["4_t1_tradable"] = all(v in ("opportunity_rich", "marginal") for v in verdicts)
        #: **Per pair.** The plan quantifies its only "30" as "the non-overlapping
        #: count per pair" (§5.2). A first version applied the threshold to the
        #: count pooled over twenty pairs, under which all 39 cells passed and the
        #: condition could never have failed — and the ambiguity was resolved in
        #: the direction that produced a survivor. The pooled reading is kept
        #: beside it so the difference is visible rather than argued about.
        checks["5_sample_adequate"] = all(
            row["effective_observations_per_pair"] >= screen.MIN_EFFECTIVE_OBSERVATIONS
            and row["effective_independent_pairs"] >= screen.MIN_EFFECTIVE_PAIRS
            for row in (first, second)
        )
        checks["5_sample_adequate_pooled_reading"] = all(
            row["effective_observations"] >= screen.MIN_EFFECTIVE_OBSERVATIONS
            and row["effective_independent_pairs"] >= screen.MIN_EFFECTIVE_PAIRS
            for row in (first, second)
        )

        def survives_registered_tail(row: dict[str, Any]) -> bool:
            """The plan's literal rule: remove **the best 10 days**, either sign."""
            tails = row.get("tails") or {}
            total, trimmed = tails.get("total"), tails.get("net_ex_best10")
            if total is None or trimmed is None:
                return False
            return (total > 0) == (trimmed > 0)

        def survives_both_tails(row: dict[str, Any]) -> bool:
            """Stricter: trim whichever tail carries the result's own sign.

            Removing the *best* days from an already-negative total makes it more
            negative, so the registered rule cannot fail for a negative cell.
            This variant is reported beside it and is not the registered gate.
            """
            tails = row.get("tails") or {}
            total = tails.get("total")
            trimmed = (
                tails.get("net_ex_best10") if (total or 0) > 0 else tails.get("net_ex_worst10")
            )
            if total is None or trimmed is None:
                return False
            return (total > 0) == (trimmed > 0)

        checks["6_survives_top10_day_removal"] = all(
            survives_registered_tail(row) for row in (first, second)
        )
        checks["6_survives_both_tails_stricter"] = all(
            survives_both_tails(row) for row in (first, second)
        )

        registered = [k for k in checks if not k.endswith(("_pooled_reading", "_stricter"))]
        out.append(
            {
                "cell": cid,
                "qualifies": all(checks[k] for k in registered),
                "qualifies_under_pooled_sample_reading": all(
                    checks[k]
                    for k in checks
                    if k != "5_sample_adequate" and not k.endswith("_stricter")
                ),
                "checks": checks,
                "t1_verdict": verdicts[0],
                "per_panel": {
                    p: {
                        k: per_panel[p].get(k)
                        for k in (
                            "mean_pips_per_entry",
                            "effect_over_cost",
                            "rate_pips_per_day",
                            "contribution_pips_per_day",
                            "cell_share",
                            "effective_observations",
                            "effective_observations_per_pair",
                            "effective_independent_pairs",
                            "pairs_positive",
                            "pairs_counted",
                            "jpy_total",
                            "non_jpy_total",
                            "total_pips_per_pair",
                            "tails",
                            "inference",
                        )
                    }
                    for p in PANELS
                },
            }
        )
    return out


def familywise_for_panel(screen_rows: list[dict[str, Any]], panel_id: str) -> dict[str, Any]:
    """Family-max over the 39 cells, for the record rather than as the gate."""
    daily = {
        screen.cell_id(row): row["_daily"]
        for row in screen_rows
        if row["panel"] == panel_id and row.get("entries") and len(row["_daily"]) > 1
    }
    if len(daily) < 2:
        return {"cells": len(daily), "note": "too few cells to correct over"}
    result = familywise.family_wise(daily, draws=2000)
    return {"cells": len(daily), **result}


def _pooled_adverse(loaded: dict[str, pd.DataFrame], horizon: int) -> dict[str, Any]:
    rows = [atlas.adverse_before_peak(frame, horizon) for frame in loaded.values()]
    rows = [r for r in rows if r.get("entries")]
    if not rows:
        return {"entries": 0}
    total = sum(r["entries"] for r in rows)
    weighted = sum(r["median_adverse_paid_to_reach"] * r["entries"] for r in rows) / total
    whole = sum(r["median_adverse_whole_window"] * r["entries"] for r in rows) / total
    cost = sum(r["median_cost"] * r["entries"] for r in rows) / total
    return {
        "entries": total,
        "median_adverse_paid_to_reach": round(weighted, 2),
        "median_adverse_whole_window": round(whole, 2),
        "median_cost": round(cost, 3),
        "paid_over_cost": round(weighted / cost, 2) if cost else None,
    }


def _conditional_vs_complement(screen_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Each level beside the rest of its own family, at the same horizon.

    T2 asks whether a state *stabilises* a sign. A level whose complement carries
    the same sign with a larger total has not stabilised anything — it has scaled
    the per-entry magnitude, which is mechanical when the conditioning variable is
    itself the size of the past move. An audit found the survivor's 90%-of-bars
    complement is positive in all three panels with four times its total, and no
    artifact showed it.
    """
    out: dict[str, Any] = {}
    for family, (_, levels, _) in screen.FAMILIES.items():
        for horizon in panels.SCREEN_HORIZONS:
            for level in levels:
                key = f"{family}:{level}:h{horizon}"
                entry: dict[str, Any] = {}
                for panel_id in PANELS:
                    rows = [
                        r
                        for r in screen_rows
                        if r["panel"] == panel_id
                        and r["family"] == family
                        and r["horizon"] == horizon
                        and r.get("entries")
                    ]
                    this = next((r for r in rows if r["level"] == level), None)
                    others = [r for r in rows if r["level"] != level]
                    if this is None or not others:
                        continue
                    entry[panel_id] = {
                        "level_pips_per_entry": this["mean_pips_per_entry"],
                        "level_total": this["total_pips_per_pair"],
                        "level_share": this["cell_share"],
                        "complement_pips_per_entry": round(
                            float(sum(r["mean_pips_per_entry"] for r in others) / len(others)), 3
                        ),
                        "complement_total": round(
                            float(sum(r["total_pips_per_pair"] for r in others)), 2
                        ),
                        "same_sign_as_complement": (this["mean_pips_per_entry"] > 0)
                        == (sum(r["mean_pips_per_entry"] for r in others) > 0),
                    }
                if entry:
                    out[key] = entry
    return out


def _panel_comparison(screen_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Inverse-variance pooling and the between-panel difference, per cell.

    The results document quoted both while no code produced either — the Round 2
    failure the module docstring above cites as this driver's reason for
    existing, in the round that cites it.
    """
    out: dict[str, Any] = {}
    by_cell: dict[str, dict[str, dict[str, Any]]] = {}
    for row in screen_rows:
        by_cell.setdefault(screen.cell_id(row), {})[row["panel"]] = row
    for cid, per_panel in sorted(by_cell.items()):
        if not all(p in per_panel and per_panel[p].get("inference") for p in DECIDING_PANELS):
            continue
        a, b = (per_panel[p]["inference"] for p in DECIDING_PANELS)
        ra, sa = a["rate_pips_per_pair_per_day"], a["rate_se"]
        rb, sb = b["rate_pips_per_pair_per_day"], b["rate_se"]
        if sa <= 0 or sb <= 0:
            continue
        weight = 1 / sa**2 + 1 / sb**2
        pooled_rate = (ra / sa**2 + rb / sb**2) / weight
        pooled_se = weight**-0.5
        diff_se = float(np.hypot(sa, sb))
        out[cid] = {
            "pooled_rate": round(pooled_rate, 4),
            "pooled_se": round(pooled_se, 4),
            "pooled_z": round(pooled_rate / pooled_se, 2),
            "difference": round(rb - ra, 4),
            "difference_se": round(diff_se, 4),
            "difference_z": round((rb - ra) / diff_se, 2),
            "active_days": {p: per_panel[p]["inference"]["days"] for p in DECIDING_PANELS},
        }
    return out


def _static_conditions_pass(
    row: dict[str, Any], atlas_verdicts: list[dict[str, Any]], screen_rows: list[dict[str, Any]]
) -> bool:
    """Conditions 4 and 5, which do not move with a sign draw.

    The false-positive rate has to carry them: a first version assumed both
    always passed, which inflates it. Condition 4 passes for 9 of 39 cells and
    condition 5 for 33, so assuming otherwise measures a screen nobody ran.
    """
    verdict_by_key = {
        (v["horizon"], v["bloc"], v["state"]): v["verdict"]
        for v in atlas_verdicts
        if v["table"] == "atr"
    }
    overall = {
        (v["horizon"], v["bloc"]): v["verdict"]
        for v in atlas_verdicts
        if v["table"] == "overall_unregistered"
    }
    if row["family"] == "F1_atr":
        verdict = verdict_by_key.get((row["horizon"], "ALL", row["level"]), "insufficient_data")
    else:
        verdict = overall.get((row["horizon"], "ALL"), "insufficient_data")
    if verdict not in ("opportunity_rich", "marginal"):
        return False
    peers = [
        r
        for r in screen_rows
        if screen.cell_id(r) == screen.cell_id(row) and r["panel"] in DECIDING_PANELS
    ]
    return all(
        r.get("effective_observations_per_pair", 0) >= screen.MIN_EFFECTIVE_OBSERVATIONS
        and r.get("effective_independent_pairs", 0) >= screen.MIN_EFFECTIVE_PAIRS
        for r in peers
    )


def main() -> dict[str, Any]:
    atlas_rows: list[dict[str, Any]] = []
    screen_rows: list[dict[str, Any]] = []
    panel_summary: dict[str, Any] = {}
    loaded_panels: dict[str, dict[str, pd.DataFrame]] = {}

    for panel_id in PANELS:
        loaded = panels.load_panel(panel_id)
        loaded_panels[panel_id] = loaded
        start, end = panels.panel_span(panel_id)
        panel_summary[panel_id] = {
            "declared_span": [start, end],
            #: measured from the bars, because `bars.load` -- unlike the other
            #: two routes -- does not validate the rows it serves, so the
            #: declared span for the development panel is an assertion until
            #: something measures it
            "measured_span": [
                str(min(f["ts"].min() for f in loaded.values()).date()),
                str(max(f["ts"].max() for f in loaded.values()).date()),
            ],
            "pairs": len(loaded),
            "bars": int(sum(len(f) for f in loaded.values())),
            "trading_days": panels.trading_days(loaded),
            "median_roundtrip_cost_pips": round(
                float(pd.concat([f["roundtrip_cost"] for f in loaded.values()]).median()), 3
            ),
        }
        atlas_rows.extend(atlas.atlas_for_panel(loaded, panel_id))
        screen_rows.extend(screen.screen_panel(loaded, panel_id))

    verdicts = atlas.classify(atlas_rows)
    write("round_a_panels", panel_summary)
    write("t1_atlas_cells", atlas_rows)
    write("t1_atlas_verdicts", verdicts)
    #: The plan (§5.4) requires a block-bootstrap CI and a two-sided p on every
    #: cell's daily contribution series. A first version of this driver computed
    #: neither, which is the difference between "one cell passed the screen" and
    #: "one cell passed the screen and here is how far it sits from zero".
    for row in screen_rows:
        series = row.get("_daily")
        row["inference"] = (
            inference.interval(series, draws=SCREEN_BOOTSTRAP_DRAWS)
            if series is not None and len(series) > 5
            else None
        )

    write(
        "t2_screen_cells",
        [{k: v for k, v in row.items() if k != "_daily"} for row in screen_rows],
    )
    candidates = structural_candidates(screen_rows, verdicts)
    write("t2_structural_candidates", candidates)
    write(
        "t2_familywise",
        {p: familywise_for_panel(screen_rows, p) for p in PANELS},
    )
    write(
        "t2_unconditional_reference",
        {
            p: inference.interval(
                next(
                    row["_daily"]
                    for row in screen_rows
                    if row["panel"] == p
                    and row.get("entries")
                    and screen.cell_id(row) == "F5_extreme:normal:h480"
                )
            )
            for p in PANELS
        },
    )
    #: The two deciding panels pooled, and the same family-max correction applied
    #: to the pooled series. A pooled p is the natural headline for a cell that
    #: agrees across both, and it is also the number most likely to be quoted
    #: uncorrected — so the corrected one is computed beside it rather than left
    #: for a reader to wonder about.
    pooled_daily: dict[str, pd.Series] = {}
    for row in screen_rows:
        if row["panel"] not in DECIDING_PANELS or not row.get("entries"):
            continue
        series = row.get("_daily")
        if series is None or len(series) < 5:
            continue
        cid = screen.cell_id(row)
        pooled_daily[cid] = (
            pd.concat([pooled_daily[cid], series]).sort_index() if cid in pooled_daily else series
        )
    complete = {
        cid: series
        for cid, series in pooled_daily.items()
        if sum(
            1
            for row in screen_rows
            if screen.cell_id(row) == cid and row["panel"] in DECIDING_PANELS and row.get("entries")
        )
        == 2
    }
    write(
        "t2_pooled_deciding_panels",
        {
            "note": "the two 730-day panels concatenated; 2025 excluded by the plan",
            "cells": len(complete),
            "per_cell": {
                cid: inference.interval(series, draws=SCREEN_BOOTSTRAP_DRAWS)
                for cid, series in sorted(complete.items())
            },
            "familywise": familywise.family_wise(complete, draws=2000)
            if len(complete) > 1
            else None,
        },
    )
    #: The atlas needs a null, because the null wins. Without this the whole of
    #: T1 is the identity `median MFE / cost ~= 1.1 * (sigma/cost) * sqrt(H)`.
    write(
        "t1_null_benchmark",
        {
            panel_id: {
                "shuffled": benchmarks.atlas_null(loaded, panels.ATLAS_HORIZONS),
                "break_even_ic": benchmarks.break_even_ic(loaded, panels.ATLAS_HORIZONS),
                "adverse_paid_to_reach": {
                    horizon: _pooled_adverse(loaded, horizon) for horizon in panels.ATLAS_HORIZONS
                },
            }
            for panel_id, loaded in loaded_panels.items()
        },
    )
    #: Max-t, so a cell firing on 8% of bars is not judged against a null max
    #: produced by one firing on 50%.
    write(
        "t2_studentized_familymax",
        {
            "pooled_deciding": benchmarks.studentized_family_max(complete)
            if len(complete) > 1
            else None,
            **{
                panel_id: benchmarks.studentized_family_max(
                    {
                        screen.cell_id(row): row["_daily"]
                        for row in screen_rows
                        if row["panel"] == panel_id
                        and row.get("entries")
                        and len(row["_daily"]) > 1
                    }
                )
                for panel_id in PANELS
            },
        },
    )
    #: The screen's own false-positive rate. "One of 39 passed" is
    #: uninterpretable until this is known, and the branch turns on it.
    write(
        "t2_screen_false_positive_rate",
        benchmarks.screen_false_positive_rate(
            {
                screen.cell_id(row): {
                    r["panel"]: {
                        "daily": r["_daily"],
                        "effect_over_cost": r["effect_over_cost"] or 0.0,
                        "passes_static": _static_conditions_pass(r, verdicts, screen_rows),
                    }
                    for r in screen_rows
                    if screen.cell_id(r) == screen.cell_id(row) and r.get("entries")
                }
                for row in screen_rows
                if row["panel"] == PANELS[0] and row.get("entries")
            },
            deciding=DECIDING_PANELS,
        ),
    )
    #: The comparison T2 was for and did not make: each level against the rest of
    #: its own family. If a level's complement carries the same sign, the state
    #: did not stabilise anything.
    write("t2_conditional_vs_complement", _conditional_vs_complement(screen_rows))
    #: The pooled and difference statistics the results document quoted while no
    #: code produced them.
    write("t2_panel_comparison", _panel_comparison(screen_rows))
    write("hypothesis_ledger", ledger.LEDGER)

    summary = {
        "panels": panel_summary,
        "t1_cells": len(atlas_rows),
        "t1_verdict_counts": pd.Series([v["verdict"] for v in verdicts]).value_counts().to_dict(),
        "t2_cells_per_panel": len(screen_rows) // len(PANELS),
        "t2_qualifying_candidates": sum(1 for c in candidates if c["qualifies"]),
        "t2_qualifying_under_pooled_sample_reading": sum(
            1 for c in candidates if c["qualifies_under_pooled_sample_reading"]
        ),
        "t2_sign_agreement_only": sum(
            1 for c in candidates if c["checks"]["1_two_periods_agree_in_sign"]
        ),
    }
    write("round_a_summary", summary)
    return summary


if __name__ == "__main__":  # pragma: no cover - the driver
    print(json.dumps(main(), indent=2, sort_keys=True, default=str))
