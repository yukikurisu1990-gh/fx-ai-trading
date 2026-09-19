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

import json
import math
import pathlib
from typing import Any, Final

from scripts.research.edge_sources import capacity
from scripts.research.market_yields import prereg

#: Inherited from the data audit, unchanged: the five decision-grade currencies.
UNIVERSE: Final[tuple[str, ...]] = prereg.UNIVERSE
EXCLUDED: Final[dict[str, str]] = prereg.EXCLUDED
DECISION_SPAN: Final[dict[str, str]] = prereg.DECISION_SPAN
DECISION_DAYS: Final[int] = prereg.DECISION_DAYS
EFFECTIVE_BREADTH: Final[float] = prereg.EFFECTIVE_BREADTH

#: The one horizon. Chosen for what it means, not for what it scores, and named by
#: the ruling itself rather than picked here.
PRIMARY_HORIZON_DAYS: Final[int] = 20

#: Above this the book is not holding a state, whatever else it shows.
TURNOVER_BOUND: Final[float] = 45.0

#: Bands of the screen, disjoint by construction.
CANDIDATE_NET_SHARPE: Final[float] = 0.3
MARGINAL_NET_SHARPE: Final[float] = 0.2


def _fast_run_record() -> dict[str, float]:
    """The adjudicated fast book's own numbers, read from its record rather than typed."""
    path = (
        pathlib.Path(__file__).resolve().parents[3]
        / "artifacts/research/market_yields/development.json"
    )
    book = json.loads(path.read_text(encoding="utf-8"))["books"]["A_yield_repricing"]
    return {
        "realised_turnover": book["summary"]["turnover_round_trips_per_year_per_unit_gross"],
        "realised_cost_ir_drag": book["ic_comparison"]["realised_cost_ir_drag"],
        "required_daily_ic_at_that_drag": book["ic_comparison"][
            "required_daily_ic_for_net_0_3_at_realised_turnover"
        ],
        "daily_equivalent_ic_it_showed": book["ic_comparison"]["observed_daily_equivalent_ic"],
    }


def _turnover_expectation() -> dict[str, Any]:
    """What turnover to expect, from what the fast run actually paid — not from the law.

    Two extrapolations, both declared before the run: the realised-over-design
    multiplier the fast book showed, and a noise-attenuation model in which part of
    the measured change is source noise that does not persist.
    """
    fast = _fast_run_record()
    law_five = capacity.band_law(5.0)["turnover"]
    law_twenty = capacity.band_law(20.0)["turnover"]
    multiplier = fast["realised_turnover"] / law_five
    #: an iid-increment five-day difference has lag-one autocorrelation 0.8; the fast
    #: signal showed 0.661, so the attenuation is 0.661 / 0.8
    attenuation = 0.661 / 0.8
    implied_ac1 = (1.0 - 1.0 / 20.0) * attenuation
    implied_half_life = math.log(0.5) / math.log(implied_ac1)
    return {
        "band_law_at_twenty_day_half_life": law_twenty,
        "realised_over_design_multiplier_from_the_fast_run": round(multiplier, 2),
        "expected_turnover_by_that_multiplier": round(law_twenty * multiplier, 1),
        "implied_half_life_under_noise_attenuation": round(implied_half_life, 2),
        "expected_turnover_under_noise_attenuation": round(
            capacity.band_law(round(implied_half_life))["turnover"], 1
        ),
        "screen_bound": TURNOVER_BOUND,
        "why_forty_five": (
            "the twenty-day hypothesis implies about 18 round trips a year and the two "
            "extrapolations give 35 and 58. A bound at 45 sits above both the law and the "
            "realised-multiplier expectation, so it does not fail a book that behaves as the "
            "hypothesis says, and below the noise-attenuation one, so a book that decays like the "
            "fast signal does fail it. It is deliberately the looser of the two defensible "
            "choices: a tighter 30 would fail on the multiplier expectation alone"
        ),
        "why_a_bound": (
            "the hypothesis is that the book holds a state. If turnover does not fall below the "
            "bound the state was not held, and the formulation is recorded as not supported "
            "rather than left arguable"
        ),
    }


def feasibility() -> dict[str, Any]:
    """Signal-blind, before the run: what this design would have to show.

    The band law gives the turnover a book with a twenty-day forecast half-life
    pays, and the cost convention turns that into an information-ratio drag. The
    required IC follows from the drag, the transfer coefficient and the breadth of
    a five-currency cross-section — none of which has seen a yield or a return.

    The one block that has is `the_fast_run_paid`: it is read from the committed
    record of the fast track, not transcribed, and it describes a run that is
    already adjudicated. No quantity of the slow book appears anywhere here.
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
        "the_fast_run_paid": _fast_run_record(),
        "turnover_expectation": _turnover_expectation(),
        "note": (
            "the band law's 18.3 assumes the forecast decays at the lookback. The fast run says "
            "it will not: a five-day lookback produced a 1.68-day half-life and 82.4 round trips "
            "against the law's 43.4. The expectation carried into the screen is therefore the "
            "realised-multiplier one, not the law's. The span still separates only a net Sharpe "
            "near 1.13 at 80% power, so neither outcome is decision-grade on its own"
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
        "the fast track tested a shock: whether FX reacts to the day's revision of the policy "
        "path. T-R2 tests a state: whether FX adjusts slowly to where the path has moved over a "
        "month. The two differ in what they assert about the market, not only in how often they "
        "trade — one is about reaction speed, the other about the speed of adjustment. The "
        "measurement supports the distinction without carrying it: the two euro-area sources "
        "agree 0.65 on one-day changes and 0.93 on five-day changes, so a longer window is a "
        "cleaner measurement of the same underlying quantity, which is a reason the state can be "
        "measured at all, not a reason it exists"
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
        "not_chosen_for_fit": (
            "no signal lookback other than five has been scored in this programme. The twenty-day "
            "*target* horizon was scored in the fast run and argues against this choice if anything "
            "(its ICs there were -0.0099, -0.0455 and +0.0013), so the lookback is not outcome-fitted. "
            "10, 15, 30, 40, 60 and any EWMA half-life are out of scope"
        ),
        "who_named_twenty": (
            "the ruling of 2026-09-18 named twenty trading days as the primary horizon and forbade a "
            "grid. The fast track's results document had listed a 20-60 day range among the options "
            "it returned to Human; the choice within that range was made by Human, not here"
        ),
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
    "primary_test_decomposition": (
        "D = B - beta * C is a rate residual carried together with a reversed momentum leg. The "
        "fast record already says this makes an unexplained D uninterpretable, so the split is "
        "pre-registered here rather than requested afterwards: D's P&L is reported as the "
        "rate-residual leg and the -beta*C leg separately, with the mean and dispersion of the "
        "daily cross-sectional beta. A positive D whose P&L comes from the momentum leg is not "
        "rate information and is recorded as such"
    ),
    "marginal_tier_authority": (
        "the ruling of 2026-09-18 allows a marginal tier for a net Sharpe between about 0.2 and "
        "0.5 when turnover is very low and stability high. It is implemented here as the stricter "
        "[0.2, 0.3) band with every shared condition required, because above 0.3 the result is a "
        "candidate outright. The implemented band is the binding one; this authority note may not "
        "be used to widen it. It is a tier for returning to Human, never for advancing"
    ),
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
        "factor_neutralisation": (
            "exactly one pass: portfolio.run_book's own neutralize_leading_factor=True, whose "
            "leading factor is computed over the five universe columns. No separate pre-step, so "
            "the fast track's post-freeze deviation does not recur and double neutralisation is "
            "excluded"
        ),
        "returns": (
            "portfolio.universe_panel: currency returns rebuilt from the eight tradable pairs, so "
            "the reported P&L is the routed book's. Slicing the eight-currency panel would leave "
            "about 8% of the implied spot exposure on currencies the book does not hold"
        ),
        "vol_target": 0.10,
        "max_leverage": 1_000_000.0,
        "leverage_cap": "none; required leverage, routed margin and the gap stress are reported",
        "cap_behaviour_on_five_names": (
            "the inherited 0.25 cap binds far harder on five currencies than on eight: gross "
            "falls below one on about 9.8% of draws against 0.09%, and the largest single-currency "
            "share of gross reaches 0.50 at the 95th percentile against 0.25. The parameter is "
            "reused unchanged and the consequence is reported, not tuned away"
        ),
        "identical_to_the_fast_run_except": (
            "the signal horizon, and the neutralisation path: the fast re-run neutralised in a "
            "pre-step with the layer's flag off, T-R2 uses the layer's own flag over the five "
            "columns. The two are mathematically the same projection given the same window, and "
            "naming which one runs is what the fast track failed to do. Everything else — cap, "
            "band, cost, vol target, routing and the rebuilt returns — is the same book"
        ),
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
        "shared_conditions": [
            "book B gross Sharpe > 0",
            "D carries a positive net increment over the FX price control C",
            "a majority of the six contiguous blocks are positive",
            "no single currency dominates: the sign survives dropping any one of the five",
            f"turnover at or below {TURNOVER_BOUND:g} round trips a year per unit gross, so the "
            "book held the state the hypothesis describes",
            "the annual charged cost does not exceed the annual gross return",
            "net Sharpe stays positive at 1.5x and 2x cost",
            "D's rate-residual leg carries at least half of D's gross P&L",
            "5% annual net is reachable at a target volatility whose gap stress does not force a "
            "loss-cut, measured by risk.gap_stress on this universe's own routing and on the "
            "book's own volatility per unit of currency gross (realised annual volatility divided "
            "by mean currency gross, taken from the run's own record, never Track 1's constant)",
        ],
        "candidate": f"every shared condition holds and D's net Sharpe is at least {CANDIDATE_NET_SHARPE}",
        "strong_if": "net Sharpe of D is 0.5 or more",
        "marginal_candidate": (
            f"every shared condition holds and D's net Sharpe is in [{MARGINAL_NET_SHARPE}, "
            f"{CANDIDATE_NET_SHARPE}). The bands do not overlap, so which token is recorded is "
            "not a choice made after the result. Returned to Human as marginal, never advanced"
        ),
        "stop": (
            "every other outcome, including a net Sharpe below the marginal band and any failure "
            "of a shared condition at any Sharpe. There is no held state"
        ),
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
