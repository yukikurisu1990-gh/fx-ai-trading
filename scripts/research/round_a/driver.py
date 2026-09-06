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

import pandas as pd

from scripts.research.exploratory_m15 import bars as bars_module
from scripts.research.exploratory_m15 import familywise
from scripts.research.exploratory_m15 import momentum_inference as inference
from scripts.research.round_a import DECIDING_PANELS, PANELS, atlas, ledger, panels, screen

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
    overall_verdict = {
        (row["horizon"], row["bloc"]): row["verdict"]
        for row in atlas_verdicts
        if row["table"] == "overall"
    }

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
        checks["5_sample_adequate"] = all(
            row["effective_observations"] >= screen.MIN_EFFECTIVE_OBSERVATIONS
            and row["effective_independent_pairs"] >= screen.MIN_EFFECTIVE_PAIRS
            for row in (first, second)
        )

        def survives_tail(row: dict[str, Any]) -> bool:
            tails = row.get("tails") or {}
            total = tails.get("total")
            trimmed = (
                tails.get("net_ex_best10") if (total or 0) > 0 else tails.get("net_ex_worst10")
            )
            if total is None or trimmed is None:
                return False
            return (total > 0) == (trimmed > 0)

        checks["6_survives_top10_day_removal"] = all(survives_tail(row) for row in (first, second))

        out.append(
            {
                "cell": cid,
                "qualifies": all(checks.values()),
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


def main() -> dict[str, Any]:
    atlas_rows: list[dict[str, Any]] = []
    screen_rows: list[dict[str, Any]] = []
    panel_summary: dict[str, Any] = {}

    for panel_id in PANELS:
        loaded = panels.load_panel(panel_id)
        start, end = panels.panel_span(panel_id)
        panel_summary[panel_id] = {
            "span": [start, end],
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
    write("hypothesis_ledger", ledger.LEDGER)

    summary = {
        "panels": panel_summary,
        "t1_cells": len(atlas_rows),
        "t1_verdict_counts": pd.Series([v["verdict"] for v in verdicts]).value_counts().to_dict(),
        "t2_cells_per_panel": len(screen_rows) // len(PANELS),
        "t2_qualifying_candidates": sum(1 for c in candidates if c["qualifies"]),
        "t2_sign_agreement_only": sum(
            1 for c in candidates if c["checks"]["1_two_periods_agree_in_sign"]
        ),
    }
    write("round_a_summary", summary)
    return summary


if __name__ == "__main__":  # pragma: no cover - the driver
    print(json.dumps(main(), indent=2, sort_keys=True, default=str))
