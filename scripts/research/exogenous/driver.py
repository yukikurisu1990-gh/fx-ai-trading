"""Exogenous Directional Information — the runner.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Stages are selected on the command line so a long acquisition does not have to
be repeated to re-run a cheap statistic:

    python -m scripts.research.exogenous.driver calendar events

Every stage writes one artifact and every artifact carries the classification.
No stage writes a verdict that a later stage's data could change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from scripts.research.exogenous import (
    CLASSIFICATION,
    CLASSIFICATION_SECONDARY,
)
from scripts.research.round_a import DECIDING_PANELS, PANELS

ARTIFACTS = Path("artifacts/track_a_scratch/exogenous")


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


def _panels() -> dict[str, dict[str, Any]]:
    """The three panels with tick volume attached, loaded once."""
    from scripts.research.exploratory_m15 import volume as volume_reader
    from scripts.research.monetizability import volume_info
    from scripts.research.round_a import panels as panel_module

    loaded: dict[str, dict[str, Any]] = {}
    for panel_id in PANELS:
        volume_reader.build_cache(panel_id)
        frames = panel_module.load_panel(panel_id)
        loaded[panel_id] = {
            pair: volume_info.attach(frame, volume_reader.load(panel_id, pair))
            for pair, frame in frames.items()
        }
        print(f"  {panel_id}: {len(loaded[panel_id])} pairs")
    return loaded


def stage_calendar() -> None:
    """Stage 1 — acquire the scheduled meeting dates and check them against BIS."""
    import datetime as dt

    from scripts.research.economic_edge import rates
    from scripts.research.exogenous import calendars

    print("stage 1: central-bank scheduled meeting calendars")
    record = calendars.acquire()
    for currency, info in record["cadence"].items():
        print(f"  {currency}: {info['per_year']} cadence_ok={info['matches']}")

    #: An independent check the calendar cannot pass by accident: every policy
    #: rate change the BIS series records must be explained by a scheduled
    #: meeting shortly before it. A hallucinated or missing meeting date shows up
    #: here as an orphaned change.
    frame, _ = rates.acquire()
    panel = rates.daily_panel(frame, start="2021-01-01", end="2025-12-31")
    containment: dict[str, Any] = {}
    for currency, dates in record["dates"].items():
        series = panel[currency]
        moved = series[series.diff().fillna(0.0) != 0.0]
        meetings = sorted(dt.date.fromisoformat(value) for value in dates)
        lags, orphans = [], []
        for stamp in moved.index:
            day = stamp.date()
            prior = [m for m in meetings if 0 <= (day - m).days <= 14]
            if prior:
                lags.append((day - max(prior)).days)
            else:
                orphans.append(day.isoformat())
        containment[currency] = {
            "rate_changes": int(len(moved)),
            "explained_by_a_scheduled_meeting": len(lags),
            "effective_date_lag_days": sorted({int(v) for v in lags}),
            "orphan_changes": orphans,
        }
        print(f"  {currency}: {len(lags)}/{len(moved)} changes explained, orphans={len(orphans)}")
    record["bis_containment"] = containment
    write("s1_calendar", record)


def stage_events() -> None:
    """Stage A — the scheduled-event structure, matched and permutation-tested."""
    from scripts.research.exogenous import events

    print("stage A: forward-known scheduled-event structure")
    calendar = read("s1_calendar")["dates"]
    loaded = _panels()
    per_panel = {
        panel_id: events.population(frames, calendar) for panel_id, frames in loaded.items()
    }
    for panel_id, result in per_panel.items():
        pooled = result["pooled"]["abs_move"]
        print(
            f"  {panel_id}: pairs={result['pairs']} "
            f"matched={pooled['matched_ratio']:.4f} "
            f"breadth={pooled['pairs_matched_above_one']}/{result['pairs']} "
            f"p={result['abs_move_permutation_p']}"
        )
    write("s4_event_population", per_panel)
    decision = events.verdict(per_panel, DECIDING_PANELS)
    print(f"  {decision['status']} / {decision['cost_advantage_status']}")
    write("s4_event_verdict", decision)


#: Plan §8's surprise scale needs 24 prior releases, so the real-time table
#: starts well before the first panel. 2019-01 gives every event inside the
#: earliest panel a full backward window without ever reading forward.
MACRO_FIRST_RELEASE_FROM = "2019-01-01"
MACRO_FIRST_RELEASE_TO = "2026-01-31"


def stage_macro() -> None:
    """Stage B — acquire the real-time CPI releases: actual, expectation, timing."""
    from scripts.research.exogenous import macro

    print("stage B: real-time macro releases")
    releases, provenance = macro.build_releases(
        first_release_from=MACRO_FIRST_RELEASE_FROM,
        first_release_to=MACRO_FIRST_RELEASE_TO,
    )
    agree = sum(1 for row in releases if row.get("archive_agrees_with_alfred"))
    complete = [
        row for row in releases if row.get("cpi") and row["cpi"].get("surprise_pct") is not None
    ]
    print(f"  releases={len(releases)} usable={len(complete)}")
    print(f"  ALFRED release date agrees with the nowcast archive on {agree}/{len(releases)}")
    write(
        "s2_macro_releases",
        {
            "releases": releases,
            "provenance": provenance,
            "expectation_kind": "MODEL_NOWCAST_SURPRISE_NOT_SURVEY_SURPRISE",
            "consensus_status": (
                "REAL_TIME_MACRO_SURVEY_CONSENSUS_NOT_AVAILABLE_WITHOUT_A_PAID_CONTRACT"
            ),
            "release_date_agreement": {"agree": agree, "total": len(releases)},
        },
    )


def stage_surprise() -> None:
    """Stage C — the pre-registered directional test on the real-time surprise."""
    from scripts.research.exogenous import MACRO_HORIZON_BARS, MIN_EVENTS_PER_DECIDING_PANEL, macro
    from scripts.research.exogenous import surprise as surprise_module
    from scripts.research.round_a import panels as panel_module

    print("stage C: macro surprise direction")
    releases = read("s2_macro_releases")["releases"]
    scaled = {
        indicator: macro.scale_surprises(releases, indicator) for indicator in macro.INDICATORS
    }

    cells: dict[str, dict[str, dict[str, Any]]] = {}
    for panel_id in PANELS:
        frames = panel_module.load_panel(panel_id)
        cells[panel_id] = {}
        for indicator, rows in scaled.items():
            for horizon in MACRO_HORIZON_BARS:
                events = surprise_module.event_returns(frames, rows, horizon=horizon)
                summary = surprise_module.summarise(events)
                cells[panel_id][f"{indicator}_{horizon}"] = summary
                if summary.get("events"):
                    print(
                        f"  {panel_id} {indicator}_{horizon}: n={summary['events']} "
                        f"gross={summary['gross_mean_pips']:+.3f} "
                        f"net={summary['net_mean_pips']:+.3f} "
                        f"ic={summary['directional_ic']:+.4f} "
                        f"p={summary['permutation_p']:.3f}"
                    )
    write("s5_macro_surprise", cells)
    decision = surprise_module.verdict(
        cells, DECIDING_PANELS, min_events=MIN_EVENTS_PER_DECIDING_PANEL
    )
    print(f"  {decision['status']}  reasons={decision['drop_reasons']}")
    write("s5_macro_verdict", decision)


def stage_financing() -> None:
    """Stage D — probe for public broker financing, and never log in."""
    from scripts.research.exogenous import financing

    print("stage D: broker financing feasibility")
    record = financing.probe()
    for row in record["candidates"]:
        print(f"  {row['name']:30s} status={row.get('status')} error={row.get('error', '')}")
    print(f"  {record['status']}")
    print(f"  {record['carry_family']}")
    write("s3_financing_feasibility", record)


STAGES = {
    "calendar": stage_calendar,
    "financing": stage_financing,
    "events": stage_events,
    "macro": stage_macro,
    "surprise": stage_surprise,
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
