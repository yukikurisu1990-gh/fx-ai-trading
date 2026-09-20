# ruff: noqa: E501 -- backlog prose
"""Engineering findings that are real, recorded, and deliberately not acted on yet.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

A backlog exists so a finding can be kept without becoming a reason to tune. Every
entry here names the condition under which it may be worked on, and every one of
those conditions is "a candidate with positive economics exists first". Optimising
an execution layer under a book with no edge moves numbers without moving profit,
and it is the most natural way to start fitting the layer to the result.
"""

from __future__ import annotations

from typing import Any, Final

ENGINEERING_FLOOR_IDENTIFIED: Final[str] = "ENGINEERING_FLOOR_IDENTIFIED"

BACKLOG: Final[tuple[dict[str, Any], ...]] = (
    {
        "id": "E-001",
        "status": ENGINEERING_FLOOR_IDENTIFIED,
        "found_in": "T-V real exchange rate valuation, 2026-09-18 (docs/research/m15_track_v_real_exchange_rate_valuation.md)",
        "finding": (
            "on a monthly-decision book run through the daily execution layer, about 77% of "
            "realised turnover came from the volatility targeter re-levering rather than from "
            "the signal. The no-trade band blocked 121 of 150 monthly decisions outright, so the "
            "designed-in cadence produced 0.28 round trips a year while the layer produced 0.96"
        ),
        "why_it_matters": (
            "it puts a floor of roughly one round trip a year under any book this layer runs, "
            "whatever the signal does. A slow source cannot express its slowness below that "
            "floor, so 'low turnover because the source is slow' is only partly true and the "
            "cross-track turnover comparison has to be read with it"
        ),
        "what_would_address_it": (
            "a volatility-target deadband, wider hysteresis, less frequent risk resizing, or "
            "equity-proportional sizing. Each changes the realised cost of every book the layer "
            "runs, so each is a change to a shared surface and not a per-track choice"
        ),
        "when_it_may_be_worked_on": (
            "only once a candidate shows positive economics that the floor is materially "
            "holding back. Tuning it now would be tuning an execution layer under books that "
            "have no edge to protect, and the first thing such tuning does is improve a "
            "recorded negative result"
        ),
        "not_a_rescue": (
            "T-V did not fail on cost. Its break-even cost multiple was 10.7 and its net stayed "
            "positive at three times the cost convention. Lowering the floor would not have "
            "changed its verdict, and this entry may not be cited as a reason to re-run it"
        ),
    },
)


def by_id(identifier: str) -> dict[str, Any]:
    for entry in BACKLOG:
        if entry["id"] == identifier:
            return entry
    raise KeyError(identifier)


__all__ = ["BACKLOG", "ENGINEERING_FLOOR_IDENTIFIED", "by_id"]
