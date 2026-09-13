"""FX Spot Decision-Grade Research Inventory — what can be answered at all.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

This is not a backtest and it computes no return. It takes every research
direction the programme could reasonably take next, describes each as a plan, and
runs the Pass-Region Preflight over it. The question throughout is the first of
the three:

    Can this question be answered?  →  Is the answer economically relevant?
                                   →  Only then, what is the answer?

What is deliberately absent
----------------------------

No candidate carries a realised return, sign, information coefficient, Sharpe
ratio, p-value or strategy P&L, and no ranking uses one. Past verdicts are used
for exactly one purpose — excluding hypothesis classes already falsified — which
the decision permits and which is not a performance comparison.

The horizon does most of the work
----------------------------------

The preflight's horizon condition needs `(z(k)/IR_max)²` effective years and can
never exceed the panel's own length. The deciding panels are **1.996 years**, so
the condition is decided before a candidate's mechanism is even read. That is the
inventory's central finding and the reason every specification below also carries
what it would take to change it.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
from typing import Any, Final

from scripts.research.feasibility import RetroactiveApplicationError
from scripts.research.feasibility.preflight import (
    MIN_DECIDING_PANELS,
    ResearchPlan,
    VarianceSource,
    Verdict,
    assess,
    required_effective_years,
    years_to_decision,
)

STATUS_REMAIN: Final[str] = "DECISION_GRADE_FX_RESEARCH_CANDIDATES_REMAIN"
STATUS_EXHAUSTED: Final[str] = "CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED"
STATUS_MORE_HISTORY: Final[str] = "ADDITIONAL_INDEPENDENT_HISTORY_WOULD_OPEN_PASS_REGION"

#: Every span this programme has read, and the two it has not. The boundary is
#: the point of the table: the first three are seen and cannot be unseen, the
#: last three are protected and are not read here, counterfactually or otherwise.
SEEN_SPANS: Final[dict[str, dict[str, Any]]] = {
    "momentum_2021_2023": {
        "start": "2021-04-26",
        "end": "2023-04-25",
        "role": "deciding panel",
        "read_by": "exploratory momentum round",
    },
    "supplemental_2023_2025": {
        "start": "2023-04-26",
        "end": "2025-04-24",
        "role": "deciding panel",
        "read_by": "supplemental historical replication",
    },
    "development_2025": {
        "start": "2025-04-25",
        "end": "2025-12-28",
        "role": "seen, **not** in either deciding panel",
        "read_by": "Track A R1, the authorised first real-data read",
    },
}

PROTECTED_SPANS: Final[dict[str, dict[str, Any]]] = {
    "fresh_pool": {"start": "2016-06-02", "end": "2021-04-25", "status": "never read"},
    "historical_oos_slice": {
        "start": "2025-12-29",
        "end": "(tail 20% of the committed design dates)",
        "status": "one decoded row per pair; no value reached an output",
    },
    "dead_window": {"start": "(after the OOS slice)", "end": "-", "status": "never read"},
    "forward_epoch": {"start": "(future)", "end": "-", "status": "never read"},
}

#: The deciding panels, as they stand.
PANEL_YEARS: Final[float] = 1.996

#: The **midpoint of** Track 3's two measured all-bars market-order round trips,
#: 2.6902 and 2.4660 bp. It is a midpoint and is labelled as one: a review found
#: an earlier comment calling it "the measured figure", and the sibling constant
#: `REFERENCE_ROUNDTRIP_COST_BP` is the same midpoint rounded differently.
PAIR_ROUNDTRIP_BP: Final[float] = 2.58

#: Gross pair notional turned over by **one currency held against the other
#: seven**, measured across the six Track 2 cells: 1.2884 to 1.3356, mean 1.3193.
#:
#: An earlier value of 1.29 was the *minimum* of that range, and its minimum cell
#: is the eleven-event one the same document calls unusable. The unit audit's
#: better-known **1.549** describes a different position — a random ±1 neutralised
#: book across eight currencies — and is not this one.
BASKET_EXPOSURE: Final[float] = 1.32
BASKET_ROUNDTRIP_BP: Final[float] = round(PAIR_ROUNDTRIP_BP * BASKET_EXPOSURE, 3)

#: `effN / N`, and both values are **assumptions**, not measurements.
#:
#: The corpus has measured 4.38 to 6.45 effectively independent *pairs* in twenty,
#: which is a different denominator from the seven-currency cross-section these
#: designs trade. A review was right that the number is therefore a judgement; it
#: is set conservatively and, crucially, **no verdict in this inventory depends on
#: it** — `effective_years = panel_years × share ≤ panel_years` fails the horizon
#: condition at `share = 1.0`, which `horizon_is_assumption_free` computes.
SHARE_CROSS_SECTIONAL: Final[float] = 0.30
SHARE_CURRENCY_LEVEL: Final[float] = 0.80

_CLOSED = Verdict.PRIOR_FAMILY_CLOSED.value


def _plan(**kwargs: Any) -> ResearchPlan:
    defaults: dict[str, Any] = {
        "panel_years": PANEL_YEARS,
        "n_deciding_panels": MIN_DECIDING_PANELS,
        "effective_n_basis": "measured effective independent directions in PAIRS_20",
        "required_breadth": 4,
        "available_breadth": 7,
        "data_ready": True,
        "variance_source": VarianceSource.NOT_ESTIMATED,
    }
    defaults.update(kwargs)
    return ResearchPlan(**defaults)


def catalogue() -> list[ResearchPlan]:
    """Twenty-two research directions, none a timeframe variant of another."""
    return [
        _plan(
            candidate_id="C01_central_bank_decision_response",
            hypothesis="a scheduled policy decision moves its own currency against a basket",
            mechanism="a mandate-bound repricing at a published instant",
            target="currency against the other seven",
            horizon="1d",
            unit_of_observation="currency-decision",
            #: 169 decisions across the four acquirable banks over 2021-01-21 to
            #: 2025-12-19 in `s1_calendar.json` — 34.4 a year. An earlier 24.0 was
            #: a guess, and it made this candidate appear to fail the event floor
            #: when it does not.
            events_per_year=34.4,
            effective_n_share=SHARE_CURRENCY_LEVEL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            #: Only four central banks publish a machine-readable calendar; the
            #: other four refuse every automated route.
            available_breadth=4,
        ),
        _plan(
            candidate_id="C02_macro_surprise_intraday",
            hypothesis="a macro surprise moves its currency in the hour after the print",
            mechanism="announcement repricing",
            target="currency against the other seven",
            horizon="1h",
            unit_of_observation="currency-event",
            events_per_year=200.0,
            effective_n_share=SHARE_CURRENCY_LEVEL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            data_ready=False,
            data_note=(
                "the only free archive's time of day is unusable — Stage 0 identified the "
                "correction only to within a nineteen-hour band, and no free official "
                "release-time calendar exists for the non-USD agencies"
            ),
        ),
        _plan(
            candidate_id="C03_session_handover_relative",
            hypothesis="flow handed between sessions leaves a currency-relative drift",
            mechanism="regional participation changing at fixed local hours",
            target="currency against the other seven",
            horizon="8h",
            unit_of_observation="currency-session",
            #: Three sessions a day across seven currencies, counted in the same
            #: unit as the observation. An earlier 756 counted session-days only,
            #: which is a different unit from the one the row declares.
            events_per_year=252.0 * 3 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
        ),
        _plan(
            candidate_id="C04_benchmark_fix_flow",
            hypothesis="benchmark-bound flow at a published fix leaves a return",
            mechanism="mandated transaction at a published rate",
            target="currency against the other seven",
            horizon="1h",
            unit_of_observation="currency-fix",
            events_per_year=252.0,
            effective_n_share=SHARE_CURRENCY_LEVEL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            #: **Not closed.** Track 1's status is
            #: `CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`,
            #: which is underpowered rather than falsified, and recording an
            #: underpowered family as refuted is the failure this programme keeps
            #: correcting. It is suspended by decision and may not be proposed,
            #: which is a different statement and is carried separately.
            suspended_by_decision=True,
        ),
        _plan(
            candidate_id="C05_month_end_rebalancing_flow",
            hypothesis="month-end hedge rebalancing leaves a currency-relative return",
            mechanism="calendar-bound portfolio rebalancing",
            target="currency against the other seven",
            horizon="1h",
            unit_of_observation="currency-month-end",
            events_per_year=12.0,
            effective_n_share=SHARE_CURRENCY_LEVEL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            suspended_by_decision=True,
        ),
        _plan(
            candidate_id="C06_factor_neutral_residual_value",
            hypothesis="a residual to a dollar-and-carry factor model mean-reverts",
            mechanism="idiosyncratic flow unwinding against a common factor",
            target="residual currency return",
            horizon="1d",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            variance_source=VarianceSource.UNCONDITIONAL_RETURN_VARIANCE,
        ),
        _plan(
            candidate_id="C07_cross_sectional_dispersion_state",
            hypothesis="cross-sectional dispersion conditions the next relative move",
            mechanism="dispersion as a proxy for idiosyncratic versus common driving",
            target="currency against the other seven",
            horizon="1d",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=2,
            variance_source=VarianceSource.UNCONDITIONAL_RETURN_VARIANCE,
        ),
        _plan(
            candidate_id="C08_currency_rank_persistence",
            hypothesis="a currency's rank in the cross-section persists",
            mechanism="relative strength",
            target="currency rank",
            horizon="1w",
            unit_of_observation="currency-week",
            events_per_year=52.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            prior_verdict=_CLOSED,
            prior_verdict_citation=(
                "the sequencing decision names 'H-003 same-shape relative strength' "
                "among the strongly falsified families; H-003 is CLOSED in "
                "artifacts/track_a_scratch/round_a/hypothesis_ledger.json"
            ),
        ),
        _plan(
            candidate_id="C09_yield_differential_change",
            hypothesis="a two-year yield differential change moves the currency",
            mechanism="repricing of the expected policy path",
            target="currency against the other seven",
            horizon="1d",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            variance_source=VarianceSource.UNCONDITIONAL_RETURN_VARIANCE,
        ),
        _plan(
            candidate_id="C10_equity_risk_regime_conditioning",
            hypothesis="an equity risk state conditions a currency's relative move",
            mechanism="risk-on and risk-off flows into and out of funding currencies",
            target="currency against the other seven",
            horizon="1d",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=2,
        ),
        _plan(
            candidate_id="C11_commodity_link_response",
            hypothesis="a commodity move transmits to its exporting currency with a lag",
            mechanism="terms of trade",
            target="commodity currency against the other seven",
            horizon="1d",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 3,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            required_breadth=3,
            available_breadth=3,
        ),
        _plan(
            candidate_id="C12_volatility_regime_transition",
            hypothesis="a realised-volatility regime change precedes a directional move",
            mechanism="volatility clustering and its breaks",
            target="currency against the other seven",
            horizon="1d",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=2,
        ),
        _plan(
            candidate_id="C13_timeframe_disagreement_state",
            hypothesis="disagreement between a short and a long window conditions the next move",
            mechanism="participants at different horizons disagreeing",
            target="currency against the other seven",
            horizon="1d",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            #: **Not closed.** The only HTF verdict in the repository calls itself
            #: "a diagnostic with no null and no error bars"
            #: (m15_round_b_prime_results.md), which is weaker evidence than a
            #: closure needs. What the decision closes is *simple HTF sign
            #: conditioning*; a disagreement state has to be materially more than
            #: that to count, and it is recorded as underpowered, not refuted.
        ),
        _plan(
            candidate_id="C14_latent_regime_state",
            hypothesis="a signal-blind latent state conditions the next relative move",
            mechanism="an unobserved regime variable",
            target="currency against the other seven",
            horizon="1d",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=3,
            ml_role="latent-state extraction",
        ),
        _plan(
            candidate_id="C15_movement_magnitude_forecast",
            hypothesis="the next move's size is forecastable enough to skip small ones",
            mechanism="volatility persistence",
            target="absolute currency move",
            horizon="1d",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            variance_source=VarianceSource.UNCONDITIONAL_RETURN_VARIANCE,
            #: A magnitude forecast, not a signed effect. Gate v2's minimum
            #: relevant effect and plausibility ceiling are undefined for it.
            gate_applies_to_the_target=False,
        ),
        _plan(
            candidate_id="C16_horizon_selection",
            hypothesis="the profitable holding length varies with a measurable state",
            mechanism="the speed of information absorption varying with participation",
            target="holding length",
            horizon="variable",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=3,
        ),
        _plan(
            candidate_id="C17_intraday_execution_timing",
            hypothesis="choosing the hour of a daily entry lowers the round trip materially",
            mechanism="the spread surface has a stable intraday shape",
            target="round-trip cost",
            horizon="intraday",
            unit_of_observation="pair-bar",
            events_per_year=252.0 * 20,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            #: Measuring a spread surface places no trades, so a round trip is not
            #: a cost this study pays. Carried at zero and out of the gate's scope.
            roundtrip_cost_bp=0.0,
            primary_cells=1,
            variance_source=VarianceSource.PREVIOUSLY_FROZEN_DESIGN_STATISTIC,
            gate_applies_to_the_target=False,
        ),
        _plan(
            candidate_id="C18_ml_currency_ranking",
            hypothesis="a learned ranking of currencies beats an equal-weight basket",
            mechanism="a nonlinear combination of state variables",
            target="currency rank",
            horizon="1d",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=3,
            ml_role="cross-sectional ranking",
        ),
        _plan(
            candidate_id="C19_ml_take_skip_gate",
            hypothesis="a learned gate improves a base strategy's net by skipping its bad events",
            mechanism="conditional expected cost-adjusted return",
            target="take or skip",
            horizon="1d",
            unit_of_observation="candidate-trade",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=2,
            ml_role="take/skip",
        ),
        _plan(
            candidate_id="C20_broker_order_flow",
            hypothesis="broker-side positioning predicts a short-horizon reversal",
            mechanism="crowded retail positioning unwinding",
            target="currency against the other seven",
            horizon="1d",
            unit_of_observation="currency-day",
            events_per_year=252.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            data_ready=False,
            data_note="needs an authenticated broker endpoint, which is not approved",
        ),
        _plan(
            candidate_id="C21_futures_positioning",
            hypothesis="reported futures positioning predicts a currency's relative move",
            mechanism="speculative crowding",
            target="currency against the other seven",
            horizon="1w",
            unit_of_observation="currency-week",
            events_per_year=52.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            prior_verdict=_CLOSED,
            prior_verdict_citation=(
                "the sequencing decision names 'COT tested cells' among the closed families"
            ),
            gate_v2_family="cot_positioning",
        ),
        _plan(
            candidate_id="C22_carry_level",
            hypothesis="a policy-rate differential earns a spot-adjusted return",
            mechanism="risk premium for funding",
            target="currency against the other seven",
            horizon="1m",
            unit_of_observation="currency-month",
            events_per_year=12.0 * 7,
            effective_n_share=SHARE_CROSS_SECTIONAL,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            primary_cells=1,
            prior_verdict=_CLOSED,
            prior_verdict_citation=(
                "the sequencing decision names 'policy-rate proxy carry' among the closed families"
            ),
            gate_v2_family="carry",
        ),
    ]


def horizon_counterfactuals() -> dict[str, Any]:
    """What panel length each data boundary would give. **Design arithmetic only.**

    No protected span is read here — only the calendar distance between two dates
    that a manifest already records. The question is whether a pass region could
    exist at all, not what is in the data.
    """

    def years(start: str, end: str) -> float:
        return (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days / 365.25

    seen_total = years(
        SEEN_SPANS["momentum_2021_2023"]["start"], SEEN_SPANS["development_2025"]["end"]
    )
    with_fresh = years(
        PROTECTED_SPANS["fresh_pool"]["start"], SEEN_SPANS["development_2025"]["end"]
    )
    needed = required_effective_years(1)
    return {
        "required_effective_years_at_one_primary_cell": round(needed, 3),
        "current": {
            "description": "the two deciding panels as they stand",
            "panel_years": PANEL_YEARS,
            "total_years": round(PANEL_YEARS * MIN_DECIDING_PANELS, 3),
            "horizon_condition_can_be_met": bool(needed <= PANEL_YEARS),
        },
        "all_seen_history_split_in_two": {
            "description": "both panels plus the development corpus, split into two",
            "total_years": round(seen_total, 3),
            "panel_years": round(seen_total / MIN_DECIDING_PANELS, 3),
            "horizon_condition_can_be_met": (seen_total / MIN_DECIDING_PANELS) >= needed,
        },
        "with_the_fresh_pool_split_in_two": {
            "description": "counterfactual only — the fresh pool is NOT read",
            "total_years": round(with_fresh, 3),
            "panel_years": round(with_fresh / MIN_DECIDING_PANELS, 3),
            "horizon_condition_can_be_met": (with_fresh / MIN_DECIDING_PANELS) >= needed,
        },
        #: At `share = 1.0` — the most optimistic assumption available, and one no
        #: catalogued candidate uses. A review found this figure quoted as *the*
        #: gap; the per-candidate figures in `years_to_decision` are the real
        #: ones, and they are two to five times larger.
        "seen_years_needed_for_two_panels_at_perfect_independence": round(
            needed * MIN_DECIDING_PANELS, 3
        ),
        "seen_years_short_at_perfect_independence": round(
            max(0.0, needed * MIN_DECIDING_PANELS - seen_total), 3
        ),
        "seen_years_available": round(seen_total, 3),
    }


def horizon_is_assumption_free() -> dict[str, Any]:
    """⭐ The horizon condition does not depend on a single contested assumption.

    `effective_years = effN / f = (f · years · share) / f = years · share`, so it
    can never exceed the panel's own length whatever the dependence share, the
    frequency, the dispersion or the cost. On 1.996-year panels the condition is
    therefore decided before any candidate's mechanism is read, and no choice of
    `effective_n_share` — not even perfect independence — changes it.

    Computed rather than asserted, because "no assumption can save this" is
    exactly the kind of claim that should be measured.
    """
    needed = required_effective_years(1)
    rows = {}
    for share in (0.1, 0.3, 0.5, 0.8, 1.0):
        for frequency in (12.0, 60.0, 252.0, 1764.0):
            plan = _plan(
                candidate_id=f"probe_s{share}_f{frequency:g}",
                hypothesis="a probe",
                mechanism="a probe",
                target="a probe",
                horizon="1d",
                unit_of_observation="probe",
                events_per_year=frequency,
                effective_n_share=share,
                roundtrip_cost_bp=0.0,
                primary_cells=1,
            )
            rows[f"share_{share}_f_{frequency:g}"] = round(plan.effective_years, 4)
    return {
        "required_effective_years": round(needed, 3),
        "effective_years_by_assumption": {"_unit": "count", **rows},
        "max_effective_years_over_every_assumption": round(max(rows.values()), 4),
        "any_assumption_reaches_the_requirement": bool(max(rows.values()) >= needed),
        "identity": (
            "effective_years = panel_years x effective_n_share, so it is bounded by the panel"
        ),
    }


FORBIDDEN_KEYS: Final[tuple[str, ...]] = (
    "return",
    "sign",
    "sharpe",
    "p_value",
    "information_coefficient",
    "pnl",
    "alpha",
    "gross_bp",
    "net_bp",
)


def _no_realised_quantity_present(assessed: list[dict[str, Any]]) -> bool:
    """No key anywhere in the assessed records could hold a realised quantity."""
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                seen.add(str(key).lower())
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(assessed)
    return not [key for key in seen for bad in FORBIDDEN_KEYS if bad in key]


def _assess(plan: ResearchPlan) -> dict[str, Any]:
    """`assess`, with the retroactivity refusal **caught and recorded**.

    `assert_prospective` raising is the enforcement, and it has to stay an
    exception — a function that returned a verdict could be ignored. The inventory
    still has to list the family, so it catches the refusal and records it with the
    guard's own message as the evidence. A closure that reaches the artifact this
    way was refused by code, not by a hand-typed field.
    """
    try:
        return assess(plan)
    except RetroactiveApplicationError as refusal:
        return {
            "candidate_id": plan.candidate_id,
            "verdict": Verdict.PRIOR_FAMILY_CLOSED.value,
            "reason": plan.prior_verdict_citation or str(refusal),
            "refused_by": "assert_prospective",
            "gate_v2_family": plan.gate_v2_family,
        }


def counterfactual_verdicts() -> dict[str, Any]:
    """⭐ Re-run **every candidate** at each panel length, not just the flag.

    A review found the share-free horizon flag saying a longer history "would open
    a pass region" while no candidate actually reached one: the flag is computed at
    `share = 1.0`, and every catalogued design uses 0.30 or 0.80. What a reader
    needs is the count of candidates that would pass, so that is what is reported.
    """
    out: dict[str, Any] = {}
    for name, block in horizon_counterfactuals().items():
        if not isinstance(block, dict) or "panel_years" not in block:
            continue
        counts: dict[str, int] = {}
        reaching: list[str] = []
        for plan in catalogue():
            record = _assess(dataclasses.replace(plan, panel_years=block["panel_years"]))
            counts[record["verdict"]] = counts.get(record["verdict"], 0) + 1
            if record["verdict"] in (
                Verdict.PASS_REGION_EXISTS.value,
                Verdict.MARGINAL_PASS_REGION.value,
            ):
                reaching.append(f"{plan.candidate_id}:{record['verdict']}")
        out[name] = {
            "panel_years": block["panel_years"],
            "verdicts": {"_unit": "count", **counts},
            "candidates_reaching_a_pass_region": sorted(reaching),
            "n_pass_region_exists": counts.get(Verdict.PASS_REGION_EXISTS.value, 0),
            "n_marginal": counts.get(Verdict.MARGINAL_PASS_REGION.value, 0),
        }
    return out


def build() -> dict[str, Any]:
    """The whole inventory. Computes no return, reads no price."""
    plans = catalogue()
    assessed = [_assess(plan) for plan in plans]
    by_verdict: dict[str, list[str]] = {}
    for record in assessed:
        by_verdict.setdefault(record["verdict"], []).append(record["candidate_id"])
    green = by_verdict.get(Verdict.PASS_REGION_EXISTS.value, [])
    gaps = [
        years_to_decision(plan)
        for plan, record in zip(plans, assessed, strict=True)
        if record["verdict"] == Verdict.NO_DECISION_GRADE_PASS_REGION.value
    ]
    counterfactual = horizon_counterfactuals()
    per_candidate = counterfactual_verdicts()
    with_history = per_candidate["with_the_fresh_pool_split_in_two"]
    return {
        "classification": [
            "NON_DECISION_BEARING_EXPLORATORY_ONLY",
            "RESEARCH_SCRATCH_NON_AUTHORITATIVE",
        ],
        #: Computed, not declared. A flag that is always `True` certifies nothing.
        "signal_free": _no_realised_quantity_present(assessed),
        "seen_spans": SEEN_SPANS,
        "protected_spans": PROTECTED_SPANS,
        "cost_basis": {
            "pair_roundtrip_bp": PAIR_ROUNDTRIP_BP,
            "basket_roundtrip_bp": BASKET_ROUNDTRIP_BP,
            "source": "Track 3's measured market-order round trip, scaled by gross exposure",
        },
        "n_candidates": len(plans),
        "candidates": assessed,
        "by_verdict": {name: sorted(ids) for name, ids in sorted(by_verdict.items())},
        "years_to_decision": gaps,
        "horizon_counterfactuals": counterfactual,
        "counterfactual_verdicts_per_candidate": per_candidate,
        "horizon_is_assumption_free": horizon_is_assumption_free(),
        "status": STATUS_REMAIN if green else STATUS_EXHAUSTED,
        #: Measured per candidate rather than from the share-free flag. At the
        #: counterfactual panel length **no** candidate reaches
        #: `PASS_REGION_EXISTS`; the honest claim is therefore about marginal
        #: candidates, and the specification says a marginal design is not a
        #: primary research candidate.
        "additional_history_would_open_a_pass_region": bool(
            not green and with_history["n_pass_region_exists"] > 0
        ),
        "additional_history_would_reach_only_marginal": bool(
            not green
            and with_history["n_pass_region_exists"] == 0
            and with_history["n_marginal"] > 0
        ),
    }


__all__ = [
    "BASKET_ROUNDTRIP_BP",
    "PAIR_ROUNDTRIP_BP",
    "PANEL_YEARS",
    "PROTECTED_SPANS",
    "SEEN_SPANS",
    "STATUS_EXHAUSTED",
    "STATUS_MORE_HISTORY",
    "STATUS_REMAIN",
    "build",
    "catalogue",
    "horizon_counterfactuals",
    "counterfactual_verdicts",
    "horizon_is_assumption_free",
]
