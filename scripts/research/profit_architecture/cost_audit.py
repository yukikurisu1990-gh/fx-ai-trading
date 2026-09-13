"""The cost conventions this programme has used, fully decomposed.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The instruction names the cost audit as the redesign's first priority, and the
number it asks about by name is **3.406 bp**. This module states exactly what
that number is, what it is charged against in each place it has been used, and
where a charging convention silently answered an economic question the design
never asked.

What 3.406 bp is
----------------

    3.406 bp  =  PAIR_ROUNDTRIP_BP (2.58)  x  BASKET_EXPOSURE (1.32)

* `2.58` — the midpoint of Track 3's two measured **all-bars market-order full
  round trips** on `PAIRS_20`: 2.6902 and 2.4660 bp of pair notional. A full
  round trip means both legs — open at the ask, close at the bid — so a single
  one-way trade costs **half** of it, 1.29 bp of the notional traded.
* `1.32` — the measured mean gross pair notional turned over per unit of
  currency-against-basket exposure, across the six Track 2 cells (1.2884 to
  1.3356).

So 3.406 bp is **the cost of one full open-and-close of one unit of gross
currency-basket notional**, and 1.703 bp is the cost of trading one unit of
one-way notional. It is a cost per unit *traded*, and nothing about it says how
often anything trades.

The convention that conflated prediction with trading
-----------------------------------------------------

Three generations of gate charged annual cost as

    annual_cost = turnover_per_year x roundtrip_bp

with `turnover_per_year` **declared from the prediction frequency**: a daily
design was assigned 252, meaning the whole book closes and reopens every day.
The development run then *measured* what daily-updated books actually do:

    ranking model (smooth scores)    36.7 round trips / year
    top2/bottom2 rank baseline       49.4
    regime-gain model                89.9
    filtered book (renormalising)   142.5

A daily-updated book built from multi-day features turns over 15-20% of its
gross per day, because consecutive targets overlap — the position is a
**difference of targets**, not a sequence of round trips. Charging 252 overstated
the cost of the smooth book by a factor of **6.9**, and that factor sat inside
`ECONOMICALLY_UNREACHABLE` verdicts, break-even ratios and hurdle tables.

⭐ None of this reopens a verdict. Each gate's verdict was correct **for the
declared inputs it was given**; the audit finding is that the declared input
`turnover = prediction frequency` was the wrong question for a continuous
portfolio, and every future economic evaluation must charge
`measured portfolio turnover x cost per unit turnover` instead.

Where each past convention was right and wrong
----------------------------------------------

* **Per-event round trips** (Gate v2's MRE, the event studies, the exploratory
  rounds): correct for what they measured — discrete positions opened and closed
  per event. Wrong as a template for a book that holds continuous positions.
* **The model-learning gate's `turnover_per_year=252`**: the conflation above.
  Its own artifact contains the refutation (measured 36.7) and its own document
  disclosed the direction without re-gating.
* **The walk-forward evaluator** (`walkforward.evaluate`): already correct — it
  charges `sum|dw|/2 x roundtrip_bp` on realised weight changes. The measured
  numbers above come from it.

The gate-audit findings the redesign must carry forward
--------------------------------------------------------

`gate_audit()` records, for each past gate, what it controlled well and what it
structurally could not see. The purpose is stated by the instruction: not to
change verdicts, but to stop a profit-seeking architecture from being excluded
by a confirmation-grade convention applied at the wrong layer.
"""

from __future__ import annotations

from typing import Any, Final

from scripts.research.profit_architecture import (
    BASKET_ROUNDTRIP_BP,
    MEASURED_TURNOVER_FILTERED_BOOK,
    MEASURED_TURNOVER_RANKING_MODEL,
    MEASURED_TURNOVER_REGIME_MODEL,
    MEASURED_TURNOVER_TOP2_BOTTOM2,
    PAIR_ROUNDTRIP_BP,
)

#: One-way cost per unit of basket notional traded: half a full round trip.
ONE_WAY_BASKET_BP: Final[float] = round(BASKET_ROUNDTRIP_BP / 2.0, 4)
ONE_WAY_PAIR_BP: Final[float] = round(PAIR_ROUNDTRIP_BP / 2.0, 4)

#: The prediction frequency the old convention charged as turnover, and the
#: factor by which it overstated the smooth book's cost.
DECLARED_DAILY_TURNOVER: Final[float] = 252.0
OVERSTATEMENT_FACTOR_SMOOTH_BOOK: Final[float] = round(
    DECLARED_DAILY_TURNOVER / MEASURED_TURNOVER_RANKING_MODEL, 2
)


def decomposition() -> dict[str, Any]:
    """The 3.406 figure taken apart, with the provenance of every factor."""
    return {
        "basket_roundtrip_bp": BASKET_ROUNDTRIP_BP,
        "factors": {
            "pair_roundtrip_bp": {
                "value": PAIR_ROUNDTRIP_BP,
                "meaning": "full round trip (both legs) of one pair, bp of pair notional",
                "provenance": (
                    "midpoint of Track 3's two measured all-bars market-order round "
                    "trips, 2.6902 and 2.4660 bp"
                ),
            },
            "basket_exposure": {
                "value": round(BASKET_ROUNDTRIP_BP / PAIR_ROUNDTRIP_BP, 4),
                "meaning": (
                    "gross pair notional turned over per unit of currency-vs-basket exposure"
                ),
                "provenance": "measured mean of the six Track 2 cells, 1.2884 to 1.3356",
            },
        },
        "per_unit_traded": {
            "one_way_basket_bp": ONE_WAY_BASKET_BP,
            "one_way_pair_bp": ONE_WAY_PAIR_BP,
            "full_round_trip_basket_bp": BASKET_ROUNDTRIP_BP,
        },
        "what_it_is_not": (
            "a cost per prediction, per signal, per day, or per position update — it "
            "is a cost per unit of notional actually traded"
        ),
    }


def prediction_vs_turnover() -> dict[str, Any]:
    """⭐ The conflation, stated with the measured numbers that refute it."""
    return {
        "declared_by_the_old_convention": {
            "daily_design_turnover_per_year": DECLARED_DAILY_TURNOVER,
            "annual_cost_bp": round(DECLARED_DAILY_TURNOVER * BASKET_ROUNDTRIP_BP, 1),
            "meaning": "the whole book closes and reopens every day",
        },
        "measured_by_the_development_run": {
            "_unit": "full-book round trips per year, from realised |dw|",
            "ranking_model_smooth_scores": MEASURED_TURNOVER_RANKING_MODEL,
            "top2_bottom2_rank_baseline": MEASURED_TURNOVER_TOP2_BOTTOM2,
            "regime_gain_model": MEASURED_TURNOVER_REGIME_MODEL,
            "filtered_renormalising_book": MEASURED_TURNOVER_FILTERED_BOOK,
        },
        "annual_cost_at_measured_turnover_bp": {
            "ranking_model": round(MEASURED_TURNOVER_RANKING_MODEL * BASKET_ROUNDTRIP_BP, 1),
            "top2_bottom2": round(MEASURED_TURNOVER_TOP2_BOTTOM2 * BASKET_ROUNDTRIP_BP, 1),
        },
        "overstatement_factor_for_the_smooth_book": OVERSTATEMENT_FACTOR_SMOOTH_BOOK,
        "rule_going_forward": (
            "annual cost = measured portfolio turnover x cost per unit turnover; "
            "prediction frequency, position-update frequency and traded turnover are "
            "three different quantities and are reported separately"
        ),
    }


def gate_audit() -> dict[str, Any]:
    """What each past gate controlled well, and what it structurally could not see.

    Per the instruction: this is an audit of the gates **as instruments for
    profit-seeking design**, not a revision of any verdict they issued. Each
    verdict stands for the design it judged.
    """
    return {
        "gate_v1": {
            "controlled_well": "nothing — `MDE <= 2x cost` rewarded expensive designs",
            "already_corrected_by": "Gate v2 (frozen)",
        },
        "gate_v2_and_pass_region_preflight": {
            "controlled_well": (
                "decision-grade hypothesis claims: alpha=0.05, 80% power, two "
                "independent panels, no pooling — the right standard for CLOSING or "
                "CONFIRMING a family"
            ),
            "structurally_could_not_see": (
                "any development activity on <=2-year panels: the composite needs "
                "3.488 effective years per panel, so applied to development it forbids "
                "discovery as such rather than distinguishing good from bad discovery. "
                "Appropriate as a confirmation gate; not an architecture-evaluation "
                "instrument"
            ),
        },
        "model_learning_feasibility_gate": {
            "controlled_well": (
                "capacity accounting (parameters vs years, breadth and frequency "
                "cancel), leakage shapes, closed-family reopening, and the corrected "
                "unit discipline (cost and volatility per unit of gross)"
            ),
            "structurally_could_not_see": [
                {
                    "finding": "prediction frequency charged as turnover",
                    "consequence": (
                        "daily designs were charged 858 bp/yr against a measured "
                        "125 bp/yr for the smooth book — break-even gross IR 2.27 "
                        "against an actual 0.33 — and ECONOMICALLY_UNREACHABLE "
                        "verdicts inherited that factor of 6.9"
                    ),
                },
                {
                    "finding": (
                        "confirmation-level family-wise error (alpha=0.05) charged to "
                        "development selection"
                    ),
                    "consequence": (
                        "one selection was priced at 10.8 out-of-fold years, which no "
                        "development corpus will ever have; the standard belongs at "
                        "the one-shot confirmation layer, where the fresh pool and "
                        "forward data pay for it"
                    ),
                },
                {
                    "finding": "single-trade economics as the unit of account",
                    "consequence": (
                        "per-event MRE and per-trade expectancy cannot represent an "
                        "architecture whose profit is edge x breadth x utilization - "
                        "turnover x cost at the portfolio level"
                    ),
                },
            ],
        },
        "verdicts_reopened_by_this_audit": [],
    }


__all__ = [
    "DECLARED_DAILY_TURNOVER",
    "ONE_WAY_BASKET_BP",
    "ONE_WAY_PAIR_BP",
    "OVERSTATEMENT_FACTOR_SMOOTH_BOOK",
    "decomposition",
    "gate_audit",
    "prediction_vs_turnover",
]
