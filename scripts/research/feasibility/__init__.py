"""Research Feasibility Gate v2 — frozen constants and the retroactivity guard.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Why there is a v2
-----------------

Gate v1 was `MDE <= 2 * cost`, which mixes statistical power and transaction
cost into one condition. Track 3 showed both halves of the consequence on real
panels: a design that got **more** expensive became `powered` with its MDE
unchanged, and a design that got **cheaper** lost `powered` for the same reason.
The hurdle is twice the cost, so it moves with the cost, and a fixed cell can
fall out of the feasible band downwards. "Lower the cost and more research
becomes possible" is false under v1.

v2 asks two questions instead of one:

* **statistically** — can this design detect the smallest effect worth knowing
  about? Sample size, dependence and dispersion only. **No cost.**
* **economically** — if an effect that size were real, would it be worth trading
  after a realistic cost? Cost in full, base and stressed.

The constant that makes the separation work
--------------------------------------------

The statistical gate needs something to compare an MDE against. Making it
cost-free entirely would set the target at "the smallest effect that would
matter if trading were free" — under a basis point for a daily design, which is
not an economically meaningful threshold. So the minimum relevant effect is
built from a **frozen programme reference cost** rather than from any design's
own measured cost. A design's cost can move as much as it likes; the statistical
target does not move with it, which is the property the sequencing decision
asked for.

`REFERENCE_ROUNDTRIP_COST_BP` is therefore never read from a `Design`, and
`economic_gate` is the only place a design's own cost is used.

Prospective only
----------------

`FEASIBILITY_GATE_V2_PROSPECTIVE_ONLY`. A new rule may not rescue a family that
has already failed or been blocked under the rules in force at the time. That is
enforced here rather than promised in prose: `assert_prospective` raises on every
family in `EXCLUDED_FROM_GATE_V2`, and `gate_v2.adjudicate` calls it first.
"""

from __future__ import annotations

from typing import Final

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

STATUS_PROSPECTIVE_ONLY: Final[str] = "FEASIBILITY_GATE_V2_PROSPECTIVE_ONLY"
STATUS_V1_FROZEN: Final[str] = "FEASIBILITY_GATE_V1_LEGACY_FROZEN"

# --------------------------------------------------------------- the constants
#: The programme's own market-order round trip, measured by Track 3 at 2.6902 and
#: 2.4660 bp on the two deciding panels and rounded to the midpoint. It is a
#: **reference**, frozen once: it is what a typical retail round trip costs, and
#: it is deliberately not any particular design's cost. Nothing reads a `Design`
#: to obtain it.
REFERENCE_ROUNDTRIP_COST_BP: Final[float] = 2.5

#: Three per cent net a year. Below this a family is not worth the research
#: budget, whatever its statistics say.
MIN_ANNUAL_NET_RETURN_BP: Final[float] = 300.0

#: An effect smaller than this cannot be separated from microstructure and
#: operational uncertainty, so it is not a research target however frequent the
#: design.
MIN_RELEVANT_EFFECT_FLOOR_BP: Final[float] = 1.0

#: Margin for execution uncertainty, model error and live degradation, on top of
#: breaking even. Track 3 measured a round trip moving by about 0.8 bp merely by
#: changing the execution policy to a realistic alternative; half of that is a
#: deliberately modest allowance that does not close the research space.
MIN_NET_MARGIN_BP: Final[float] = 0.5

#: The largest gross annual information ratio worth believing in advance. The
#: unit audit reported its bands at 1.0, 1.5 and 2.0 and observed that nothing
#: this programme has produced approaches 1.5.
MAX_PLAUSIBLE_GROSS_IR: Final[float] = 1.5

#: Cost stress, carried over from the programme's existing practice.
COST_STRESS_MULTIPLE: Final[float] = 2.0

#: Reused from `clock_flow`, not restated: below this a cell is not adjudicated.
MIN_EVENTS_PER_PANEL: Final[int] = 60

#: Two-sided 5%, 80% power. Same object as every other stage.
ALPHA: Final[float] = 0.05
POWER: Final[float] = 0.80

# ------------------------------------------------------- the retroactivity ban
#: Families this gate may **not** adjudicate. Each was closed, blocked or
#: suspended under the rules in force at the time, and a later rule does not get
#: to reopen them. Reopening needs new independent data, a materially new
#: measurement, or a different economic mechanism — not a new gate.
EXCLUDED_FROM_GATE_V2: Final[frozenset[str]] = frozenset(
    {
        "track_1_clock_structure",
        "exploratory_round_1",
        "exploratory_round_2",
        "round_b_prime",
        "monetizability",
        "prior_macro_surprise",
        "cot_positioning",
        "carry",
        "track_3_execution_frontier",
    }
)


class RetroactiveApplicationError(RuntimeError):
    """Raised when Gate v2 is pointed at a family it may not adjudicate."""


def assert_prospective(family: str) -> str:
    """Refuse a retroactive application, by name, before anything is computed.

    A normalising comparison rather than an exact one: `Track 1` and
    `track-1-clock-structure` are the same family as
    `track_1_clock_structure`, and a ban that a spelling can walk around is not
    a ban.
    """
    key = family.strip().lower().replace("-", "_").replace(" ", "_")
    if key in EXCLUDED_FROM_GATE_V2:
        raise RetroactiveApplicationError(
            f"{family!r} was adjudicated under the rules in force at the time. "
            f"{STATUS_PROSPECTIVE_ONLY}: Gate v2 applies to new research only, and "
            "reopening this family needs new independent data, a materially new "
            "measurement or a different economic mechanism — not a new gate."
        )
    return key


__all__ = [
    "ALPHA",
    "CLASSIFICATION",
    "CLASSIFICATION_SECONDARY",
    "COST_STRESS_MULTIPLE",
    "EXCLUDED_FROM_GATE_V2",
    "MAX_PLAUSIBLE_GROSS_IR",
    "MIN_ANNUAL_NET_RETURN_BP",
    "MIN_EVENTS_PER_PANEL",
    "MIN_NET_MARGIN_BP",
    "MIN_RELEVANT_EFFECT_FLOOR_BP",
    "POWER",
    "REFERENCE_ROUNDTRIP_COST_BP",
    "STATUS_PROSPECTIVE_ONLY",
    "STATUS_V1_FROZEN",
    "RetroactiveApplicationError",
    "assert_prospective",
]
