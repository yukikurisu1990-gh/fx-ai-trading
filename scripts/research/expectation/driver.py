"""Expectation Benchmark — the runner.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

    python -m scripts.research.expectation.driver consensus macro rates adjudicate

Each stage writes one artifact. The macro stage checks its own power **before**
reading any result and refuses to report an underpowered cell as a null.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from scripts.research.expectation import (
    CLASSIFICATION,
    CLASSIFICATION_SECONDARY,
)
from scripts.research.round_a import DECIDING_PANELS, PANELS

ARTIFACTS = Path("artifacts/track_a_scratch/expectation")

#: The surprise scale needs 24 prior releases, so the table starts well before
#: the first panel. 2019-01 gives every event inside the earliest panel a full
#: backward window without ever reading forward.
FIRST_RELEASE_FROM = "2019-01-01"
FIRST_RELEASE_TO = "2026-01-31"


def write(name: str, payload: Any) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    body = {
        "classification": CLASSIFICATION,
        "classification_secondary": CLASSIFICATION_SECONDARY,
        "payload": payload,
    }
    (ARTIFACTS / f"{name}.json").write_text(
        json.dumps(body, indent=1, sort_keys=True, default=str), encoding="utf-8"
    )
    print(f"  wrote {name}.json")


def read(name: str) -> Any:
    return json.loads((ARTIFACTS / f"{name}.json").read_text(encoding="utf-8"))["payload"]


def stage_consensus() -> None:
    """Stage 1 — acquire the free archive, audit it, and build the event table."""
    from scripts.research.expectation import consensus

    print("stage 1: free survey-consensus audit")
    archive, provenance = consensus.acquire_archive()
    print(
        f"  archive rows={provenance['rows']} sha={provenance['sha256'][:12]} "
        f"frozen_digest_ok={provenance['digest_matches_frozen_prefix']}"
    )

    alfred_releases = json.loads(
        Path("artifacts/track_a_scratch/exogenous/s2_macro_releases.json").read_text(
            encoding="utf-8"
        )
    )["payload"]["releases"]
    actual_audit = consensus.audit_actuals(archive, alfred_releases)
    print(
        f"  ACTUALS: {actual_audit['agree_with_alfred_first_release']}"
        f"/{actual_audit['matched_to_known_release']} "
        f"({actual_audit['agreement_rate']}) -> {actual_audit['verdict']}"
    )
    print(f"  timestamp error hours: {actual_audit['timestamp_error_hours']}")

    forecast_audit = consensus.audit_forecasts(archive)
    print(f"  FORECASTS: {forecast_audit['verdict']}")
    for event, cell in forecast_audit["per_event"].items():
        if "ratio_to_naive_benchmark" in cell:
            print(
                f"    {event:32s} n={cell['n']:3d} exact={cell['exact_equal_share']:.3f} "
                f"corr={cell['correlation']:+.3f} ratio={cell['ratio_to_naive_benchmark']}"
            )

    dates = consensus.release_dates(
        first_release_from=FIRST_RELEASE_FROM, first_release_to=FIRST_RELEASE_TO
    )
    for name, cell in dates.items():
        print(f"  {name:12s} ALFRED {cell['series']:10s} release dates={len(cell['dates'])}")

    events, diagnostics = consensus.build_events(archive, dates)
    events = consensus.attach_surprises(events)
    print(f"  join: {diagnostics}")
    usable = [event for event in events if event["composite_z"] is not None]
    print(f"  release-times with a composite surprise: {len(usable)} of {len(events)}")

    write(
        "s1_consensus",
        {
            "archive_provenance": provenance,
            "actual_audit": actual_audit,
            "forecast_audit": forecast_audit,
            "release_dates": {
                k: {"series": v["series"], "count": len(v["dates"])} for k, v in dates.items()
            },
            "join_diagnostics": diagnostics,
            "events": events,
            "decision_grade": (
                "FREE_CONSENSUS_DECISION_GRADE_FOR_A_USD_KILL_NOT_FOR_A_MULTI_CURRENCY_CANDIDATE"
            ),
        },
    )


def stage_macro() -> None:
    """Family 1 — power first, then the pre-registered directional test."""
    from scripts.research.expectation import (
        FLAGGED_FAMILIES,
        HIGH_IMPACT_FAMILIES,
        MACRO_HORIZON_BARS,
        MIN_RELEASES_PER_DECIDING_PANEL,
        test_engine,
    )
    from scripts.research.round_a import panels as panel_module

    print("Family 1: survey consensus macro surprise")
    events = read("s1_consensus")["events"]
    families = sorted({name for event in events for name in event["families"]})

    power: dict[str, dict[str, Any]] = {}
    cells: dict[str, dict[str, Any]] = {}
    corrected: dict[str, dict[str, float]] = {}
    for panel_id in PANELS:
        frames = panel_module.load_panel(panel_id)
        power[panel_id] = {}
        cells[panel_id] = {}
        for horizon, bars in MACRO_HORIZON_BARS.items():
            pooled = test_engine.event_returns(frames, events, horizon_bars=bars)
            if pooled.empty:
                power[panel_id][f"pooled_{horizon}"] = {
                    "events": 0,
                    "runnable": False,
                    "reason": "no events in this panel",
                }
                cells[panel_id][f"pooled_{horizon}"] = {
                    "events": 0,
                    "skipped": {"reason": "no events in this panel", "events": 0},
                }
                continue
            #: the high-impact subset is reported beside the pooled cell, not
            #: instead of it: a pooled null bounds a *concentrated* effect only
            #: by the subset's share of the population, so the subset has to be
            #: named even when it turns out to be underpowered on its own
            high = pooled[
                pooled["families"].apply(
                    lambda names: any(name in HIGH_IMPACT_FAMILIES for name in names)
                )
            ]
            #: A robustness check forced by the integrity flag, not by a result.
            #: The pre-registered forecast audit fired on two families whose
            #: naive benchmark is meaningless (quarterly GDP) or whose inputs
            #: are already public before the print (core PCE). Contamination of
            #: a forecast ATTENUATES a surprise rather than manufacturing one,
            #: so it makes a null more likely; dropping the flagged families is
            #: therefore the conservative direction and is reported beside the
            #: primary rather than instead of it.
            clean = pooled[
                pooled["families"].apply(lambda names: not set(names) <= set(FLAGGED_FAMILIES))
            ]
            plans = [("pooled", pooled), ("pooled_ex_flagged", clean), ("high_impact", high)] + [
                (family, pooled[pooled["families"].apply(lambda names, f=family: f in names)])
                for family in families
            ]
            for name, table in plans:
                key = f"{name}_{horizon}"
                gate = test_engine.minimum_detectable_effect(table)
                power[panel_id][key] = gate
                if not gate.get("runnable"):
                    cells[panel_id][key] = {"events": gate.get("events", 0), "skipped": gate}
                    continue
                cells[panel_id][key] = test_engine.evaluate(table)
        corrected[panel_id] = test_engine.family_max_p(cells[panel_id])
        for key, cell in cells[panel_id].items():
            if "skipped" in cell:
                print(f"  {panel_id} {key:16s} SKIPPED {cell['skipped']['reason']}")
                continue
            print(
                f"  {panel_id} {key:16s} n={cell['events']:3d} "
                f"gross={cell['gross_mean_pips']:+7.3f} net={cell['net_mean_pips']:+7.3f} "
                f"mde={cell['mde_80pct_power_pips']:5.2f} p={cell['permutation_p']:.3f} "
                f"fam={corrected[panel_id].get(key)}"
            )
            cell.pop("null_statistics", None)

    decision = test_engine.verdict(
        cells,
        DECIDING_PANELS,
        primary=tuple(f"pooled_{h}" for h in MACRO_HORIZON_BARS),
        # the high-impact subset is a secondary: it is reported, and it is not
        # allowed to carry the verdict on its own
        corrected=corrected,
        min_events=MIN_RELEASES_PER_DECIDING_PANEL,
        supported_status="SURVEY_CONSENSUS_MACRO_EDGE_SUPPORTED_ON_USD",
        not_supported_status=(
            "SURVEY_CONSENSUS_MACRO_EDGE_NOT_SUPPORTED_ON_USD_AT_DECISION_GRADE_POWER"
        ),
    )
    print(f"  {decision['status']}  reasons={decision['drop_reasons']}")
    write("s2_macro", {"power": power, "cells": cells, "family_max_p": corrected})
    write("s2_macro_verdict", decision)


def stage_rates() -> None:
    """Family 2 free branch — does a day's rate repricing lead the FX move?"""
    from scripts.research.expectation import rates

    print("Family 2 (free): US 2-year yield repricing, lead versus same day")
    rates.run(write=write, read=read)


def stage_adjudicate() -> None:
    """Collect the verdicts and state what was and was not decided."""
    print("adjudication")
    macro = read("s2_macro_verdict")
    consensus_record = read("s1_consensus")
    try:
        rates_verdict = read("s3_rates_verdict")
    except FileNotFoundError:
        rates_verdict = {"status": "NOT_RUN"}

    statuses = [
        consensus_record["decision_grade"],
        macro["status"],
        rates_verdict["status"],
        "RATE_PATH_EVENT_REPRICING_NOT_TESTABLE_ON_FREE_DATA",
        "SIGNED_ORDER_FLOW_NOT_TESTABLE_ON_FREE_DATA",
    ]
    for line in statuses:
        print(f"  {line}")
    write(
        "s4_adjudication",
        {
            "statuses": statuses,
            "always_binding": [
                "NON_DECISION_BEARING_EXPLORATORY_ONLY",
                "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
                "PRODUCTION_READINESS_NOT_CLAIMED",
                "FRESH_POOL_2016_06_02_TO_2021_04_25_UNTOUCHED",
                "HISTORICAL_OOS_SLICE_UNTOUCHED",
                "FUTURE_UNTOUCHED_EPOCH_UNTOUCHED",
                "NO_CONTRACT_NO_TRIAL_NO_ACCOUNT_NO_PAYMENT",
            ],
        },
    )


STAGES = {
    "consensus": stage_consensus,
    "macro": stage_macro,
    "rates": stage_rates,
    "adjudicate": stage_adjudicate,
}


def main(argv: list[str]) -> int:
    wanted = argv[1:] or list(STAGES)
    unknown = [name for name in wanted if name not in STAGES]
    if unknown:
        print(f"unknown stage(s): {unknown}; known: {list(STAGES)}")
        return 2
    for name in wanted:
        STAGES[name]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
