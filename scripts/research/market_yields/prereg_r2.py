# ruff: noqa: E501 -- pre-registration prose
"""T-R2 — slow market-yield repricing state. Frozen before the signal meets a return.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Authority: the Human + ChatGPT ruling of 2026-09-18, which authorised one slow
formulation after the fast one failed, and forbade a horizon search.

**This is a different economic hypothesis, not a smoother.** The fast track asked
whether FX follows the day's rate shock. It does not, at a price worth paying.
T-R2 asks whether FX follows the *state* those shocks accumulate into: a relative
monetary-policy repricing that builds over about a month and is meant to persist,
so that a position in it is held rather than continuously replaced.

Two consequences follow from the hypothesis, and both are declared here rather
than discovered later: the measure is a twenty-day cumulative repricing, and the
book that carries it should turn over far less than the fast one did. If turnover
falls and the gross expected return falls with it, the earlier result was not a
cost problem — the information was short-lived and never monetisable.
"""

from __future__ import annotations

import math
from typing import Any, Final

from scripts.research.edge_sources import capacity
from scripts.research.market_yields import prereg

#: Inherited from the data audit, unchanged: the five decision-grade currencies.
UNIVERSE: Final[tuple[str, ...]] = prereg.UNIVERSE
EXCLUDED: Final[dict[str, str]] = prereg.EXCLUDED
DECISION_SPAN: Final[dict[str, str]] = prereg.DECISION_SPAN
DECISION_DAYS: Final[int] = prereg.DECISION_DAYS
EFFECTIVE_BREADTH: Final[float] = prereg.EFFECTIVE_BREADTH

#: The one horizon. Chosen for what it means, not for what it scores.
PRIMARY_HORIZON_DAYS: Final[int] = 20


def feasibility() -> dict[str, Any]:
    """Signal-blind, before the run: what this design would have to show.

    The band law gives the turnover a book with a twenty-day forecast half-life
    pays, and the cost convention turns that into an information-ratio drag. The
    required IC follows from the drag, the transfer coefficient and the breadth of
    a five-currency cross-section. Nothing here has seen a yield or a return.
    """
    rows = {}
    for half_life in (5.0, 20.0):
        law = capacity.band_law(half_life)
        drag = capacity.cost_ir_drag(law["turnover"])
        rows[f"half_life_{half_life:g}d"] = {
            "turnover_per_unit_gross": law["turnover"],
            "alpha_capture": law["capture"],
            "cost_ir_drag": round(drag, 3),
            "required_daily_ic_for_net_0_3": round(
                capacity.required_daily_ic(0.3, half_life, EFFECTIVE_BREADTH), 4
            ),
            "required_daily_ic_for_net_0_5": round(
                capacity.required_daily_ic(0.5, half_life, EFFECTIVE_BREADTH), 4
            ),
        }
    years = DECISION_DAYS / 252.0
    return {
        "effective_breadth_assumed": EFFECTIVE_BREADTH,
        "decision_days": DECISION_DAYS,
        "decision_years": round(years, 3),
        "rows": rows,
        "detectable_net_sharpe_at_80pct_power": round((1.645 + 0.8416) / math.sqrt(years), 3),
        "what_the_fast_run_paid": {
            "realised_turnover": 82.4,
            "realised_cost_ir_drag": 1.065,
            "required_daily_ic_at_that_drag": 0.0642,
            "observed_daily_equivalent_ic": 0.0124,
        },
        "note": (
            "a twenty-day forecast should trade at roughly a fifth of the fast book's turnover, "
            "which lowers the required daily IC from about 6.4% to about 2.7%. The span still "
            "separates only a net Sharpe near 1.13 at 80% power, so neither outcome is "
            "decision-grade on its own"
        ),
    }


PREREG: Final[dict[str, Any]] = {
    "track": "T-R2 — slow market-yield repricing state",
    "authority": "Human + ChatGPT ruling of 2026-09-18",
    "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
    "question": (
        "does FX follow, with a lag, the relative monetary-policy repricing state that builds "
        "over about a month — carrying expected-return information beyond what the currency's own "
        "price history already holds?"
    ),
    "why_this_is_not_the_fast_hypothesis_smoothed": (
        "the fast track tested a shock: the day-to-day revision of the policy path, which the "
        "measurement itself makes noisy (the two euro-area sources agree only 0.65 on one-day "
        "changes). T-R2 tests a state: a persistent repricing of where policy is heading, which "
        "is a claim about slow adjustment rather than about reaction speed. The two differ in "
        "what they assert about the market, not only in how often they trade"
    ),
    "stage": "Stage 1: one unfitted rule. No fitted coefficient, no ML, no search.",
    "universe": {
        "currencies": list(UNIVERSE),
        "fixed_by": "the data audit of artifacts/research/market_yields/integrity.json",
        "excluded": EXCLUDED,
        "breadth_expansion": (
            "AUD, NZD and CHF are not acquirable from this environment. Their absence does not "
            "stop T-R2, and a negative T-R2 may not be rescued by proposing to add them"
        ),
    },
    "signal": {
        "definition": (
            "cross-sectional z-score, over the five currencies, of the change in the two-year "
            "market yield over the primary horizon"
        ),
        "horizon_days": PRIMARY_HORIZON_DAYS,
        "why_twenty": [
            "about one month of market repricing, the scale on which a policy-path revision is expressed rather than a day's noise",
            "an economic interpretation distinct from the fast shock, not a better score",
            "a state a book can hold, so turnover falls as a consequence of the hypothesis",
        ],
        "not_chosen_for_fit": "no horizon was scored before this was frozen; 10, 15, 30, 40, 60 and any EWMA half-life are out of scope",
        "sign": "+1 — a currency whose relative yield has risen over the horizon is expected to appreciate",
        "sign_frozen": True,
        "inversion_after_the_result_prohibited": True,
    },
    "availability_rule": (
        "unchanged from the fast track: publication times are unconfirmed on the source pages, "
        "so a yield dated d may inform a position only one trading day later, and that position "
        "earns the next day's return. No same-day use"
    ),
    "books": {
        "A_fast_5d_reference": "the fast five-day signal, re-run through the repaired layer for comparison only — not re-searched, not re-tuned",
        "B_slow_rate_state": "the twenty-day repricing state alone",
        "C_fx_price_control": "FX momentum over the same twenty days — the currency's own price history, as its own book",
        "D_residualised": "the twenty-day rate state cross-sectionally residualised against that FX price control",
    },
    "primary_test": "D",
    "no_control_zoo": (
        "exactly these four books. The control is the currency's own recent return over the same "
        "window, which is available at the decision because the yield is a further day behind. No "
        "further conditioning variable may be added after a result"
    ),
    "book_configuration": {
        "architecture": (
            "the Track 1 execution layer, with every step closed inside the observed universe "
            "(scripts/research/market_yields/portfolio.py): capped sum-zero weights at 0.25, "
            "no-trade band 0.10, partial rebalance, charged cost on the traded delta, routing over "
            "the eight pairs whose both legs are in the universe, volatility target 10%"
        ),
        "track_1_alpha_model_reused": False,
        "mapping": "linear on the declared score",
        "factor_neutralisation": "inside the universe",
        "vol_target": 0.10,
        "leverage_cap": "none; required leverage, routed margin and the gap stress are reported",
        "identical_to_the_fast_run_except": "the signal horizon. The layer is the repaired one, which the fast books were also re-run through, so the two are compared like with like",
    },
    "metrics": [
        "gross Sharpe",
        "net Sharpe",
        "annual gross return",
        "annual net return",
        "realised vol",
        "IC at the primary horizon",
        "incremental IC beyond the FX control",
        "turnover",
        "annual transaction cost",
        "signal persistence",
        "position persistence",
        "positive temporal blocks",
        "leave-one-currency-out",
        "currency contribution",
        "top 1 / 5 / 10 day contribution",
        "max drawdown",
        "cost x1.5",
        "cost x2",
        "risk leverage for 5% and 10% annual net",
        "pair-level margin utilisation",
        "stressed margin utilisation",
    ],
    "central_diagnostic": (
        "if turnover falls to the twenties or thirties and the gross expected return survives, "
        "the fast result was a cost problem. If turnover falls and the gross goes with it, the "
        "rate information was short-lived and never monetisable — which is the more informative "
        "outcome of the two"
    ),
    "screen": {
        "kind": "development screen, symmetric and exhaustive; seen data decides nothing",
        "candidate": [
            "book B gross Sharpe > 0 and book D net Sharpe > 0",
            "D carries a positive net increment over the FX price control C",
            "a majority of the six contiguous blocks are positive",
            "no single currency dominates: the sign survives dropping any one of the five",
            "turnover is realistic for the hypothesis and the annual cost does not exceed the gross",
            "net Sharpe at 1.5x and 2x cost stays positive",
            "5% annual net is reachable at a target volatility whose gap stress does not force a loss-cut",
        ],
        "strong_if": "net Sharpe of D is 0.5 or more",
        "marginal_candidate": (
            "net Sharpe between about 0.2 and 0.5 with very low turnover, high stability and a "
            "low correlation to what the programme already holds — returned to Human as marginal, "
            "never advanced on its own"
        ),
        "stop": "any result that fails a candidate condition and does not meet the marginal bar",
        "status_candidate": "MARKET_YIELD_SLOW_REPRICING_DEVELOPMENT_CANDIDATE",
        "status_marginal": "MARKET_YIELD_SLOW_REPRICING_MARGINAL_DEVELOPMENT_CANDIDATE",
        "status_stop": "MARKET_YIELD_SLOW_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        "status_data": "MARKET_YIELD_SLOW_REPRICING_DATA_NOT_DECISION_GRADE",
        "no_automatic_progress_to_fresh": True,
    },
    "family_boundary_if_stop": (
        "with both the fast shock and the slow state unsupported, the simple directional use of "
        "market-yield repricing may be closed as a scope-limited family. That closure would not "
        "reach OIS, intraday rate futures, the market-implied policy path or curve "
        "non-linearities, none of which has been observed"
    ),
    "prohibited_after_the_result": [
        "changing the horizon, the sign, the lookback or the universe",
        "adding a control, a book or a currency",
        "re-running at another volatility target, band or cost convention to rescue the economics",
        "any nonlinear or ML formulation",
        "reading any protected span",
    ],
}


__all__ = [
    "DECISION_DAYS",
    "DECISION_SPAN",
    "EFFECTIVE_BREADTH",
    "EXCLUDED",
    "PREREG",
    "PRIMARY_HORIZON_DAYS",
    "UNIVERSE",
    "feasibility",
]
