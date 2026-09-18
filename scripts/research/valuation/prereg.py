# ruff: noqa: E501 -- pre-registration prose
"""T-V — real exchange rate valuation. Frozen before any pre-2016 FX byte is read.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Authority: the Human + ChatGPT ruling of 2026-09-18, which authorised T-V to be
taken to a frozen pre-registration and then, without further confirmation, to a
minimal development run on public pre-2016 FX history with the protected span
excluded at the request.

The question is whether a currency that is cheap against its own history in
**real** terms — nominal value adjusted for relative price levels — earns more
over the following months. The control that matters is not a market factor but a
simpler explanation: a currency that is cheap against its own *nominal* history
may revert for reasons that have nothing to do with price levels. So the primary
test is the valuation signal after that nominal mean reversion is removed.

Everything below was fixed before the first FX observation was requested, and the
T-R2 result played no part in it: the design was drafted while T-R2 was still in
review and its numbers were not consulted.
"""

from __future__ import annotations

from typing import Any, Final

#: Eight currencies: the ECB reference rates cover all of them from one snapshot.
UNIVERSE: Final[tuple[str, ...]] = ("AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD")

#: The span requested. It ends the day before the protected pool begins.
SPAN: Final[dict[str, str]] = {"first": "1999-01-04", "last": "2016-06-01"}
WARM_UP_END: Final[str] = "2003-12-31"
MIN_ANCHOR_MONTHS: Final[int] = 60

#: CPI for month M is treated as unknown until the end of month M+2.
CPI_PUBLICATION_LAG_MONTHS: Final[int] = 2

PRIMARY_HORIZON_MONTHS: Final[int] = 3
TURNOVER_BOUND: Final[float] = 12.0
CANDIDATE_NET_SHARPE: Final[float] = 0.30
MARGINAL_NET_SHARPE: Final[float] = 0.25
COST_STRESSES: Final[tuple[float, ...]] = (2.0, 3.0)

PREREG: Final[dict[str, Any]] = {
    "track": "T-V — real exchange rate valuation",
    "authority": "Human + ChatGPT ruling of 2026-09-18 (D-1 conditional approval, sections 21-34)",
    "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
    "question": (
        "does an ex-ante measure of real exchange rate valuation — a currency's nominal value "
        "against the basket, adjusted for relative price levels, compared with its own history — "
        "predict G10 FX excess returns over the following months, beyond the nominal mean "
        "reversion that needs no price levels at all?"
    ),
    "why_it_is_not_price_mean_reversion": (
        "a nominal deviation from a long average is a price statistic and nothing more. The "
        "valuation claim is that the equilibrium a currency returns to moves with relative price "
        "levels, so the same nominal level is cheap or dear depending on inflation since. The "
        "control book is the nominal deviation alone, and the primary test is what survives it"
    ),
    "stage": "Stage 1: one unfitted rule, no fitted coefficient, no model, no ML, no search",
    "data": {
        "fx": (
            "ECB euro foreign-exchange reference rates, daily, one 14:15 CET snapshot for every "
            "currency, so the cross-section is synchronous"
        ),
        "cpi": "BIS long consumer price series, monthly index, one provider for all eight countries",
        "span": SPAN,
        "protected_span_excluded_at_the_request": True,
        "status_of_the_span_once_read": "EXPLORATORY_SEEN_DEVELOPMENT_DATA, never available for confirmation",
    },
    "publication_lag": {
        "cpi": f"the index for month M is used only from the end of month M+{CPI_PUBLICATION_LAG_MONTHS}",
        "quarterly_countries": (
            "Australia and New Zealand publish quarterly; the quarter's value is carried forward "
            "under the same lag and the step is not smoothed"
        ),
        "vintages": (
            "only revised history is available for most of these series, so the run uses revised "
            "data and the bias is disclosed rather than modelled: a revision that arrived after "
            "the decision cannot have been known, and this design cannot see that. Any positive "
            "result carries that caveat explicitly"
        ),
        "fx": "the reference rate of day d informs a decision at the close of day d at the earliest, never earlier",
    },
    "valuation_formula": {
        "nominal_value": "n_c = log of the euro value of one unit of c, cross-sectionally demeaned",
        "relative_price_level": "pi_c = log CPI_c, cross-sectionally demeaned, at the lagged availability",
        "real_value": "q_c = n_c + pi_c — a currency whose nominal value has held while its prices rose is dear in real terms",
        "anchor": (
            "a_c = the expanding-window mean of q_c using only months already observed, with at "
            f"least {MIN_ANCHOR_MONTHS} months required before the currency may take a position"
        ),
        "deviation": "d_c = q_c - a_c, positive meaning overvalued",
        "signal": "the cross-sectional z-score of -d_c: undervalued currencies are expected to appreciate",
        "sign_frozen": True,
        "no_full_sample_anchor": (
            "the anchor never uses a month the decision could not have seen; a full-sample mean "
            "applied backwards is prohibited"
        ),
    },
    "robustness_anchor": (
        "one alternative anchor is declared in advance — the expanding median instead of the mean "
        "— and reported as a robustness check, never as a selection. If the sign of the result "
        "changes between the two, the design is too anchor-dependent and stops"
    ),
    "cadence": {
        "decision": "the last trading day of each month",
        "rebalance": "monthly, through the same no-trade band of 0.10",
        "why": (
            "a valuation deviation moves on the timescale of price levels, so a daily decision "
            "would pay daily costs for a monthly signal. Low turnover is the economic advantage "
            "this source is supposed to have, and it is designed in, not discovered"
        ),
    },
    "books": {
        "A_valuation": "the real valuation signal alone",
        "B_nominal_control": "the same construction with the price-level term removed — nominal mean reversion",
        "C_residualised": "the valuation signal residualised against B, cross-sectionally, each decision",
    },
    "primary_test": "C",
    "benchmarks": ["no position (cash)", "the nominal control B"],
    "book_configuration": {
        "architecture": (
            "the Track 1 execution layer through scripts/research/market_yields/portfolio.py, "
            "closed inside the universe: capped sum-zero weights at 0.25, no-trade band 0.10, "
            "charged cost on the traded delta, routing over the pairs whose both legs are in the "
            "universe, volatility target 10%"
        ),
        "returns": "currency excess returns rebuilt from those pairs, so the P&L is the routed book's",
        "factor_neutralisation": "the layer's own single pass over the universe columns",
        "vol_target": 0.10,
        "max_leverage": 1_000_000.0,
        "leverage_cap": "none; required leverage, routed margin and the gap stress are reported",
    },
    "cost": {
        "convention": "the charged convention, 1.703 bp per unit of summed absolute delta",
        "stress": list(COST_STRESSES),
        "why_stress_harder_than_elsewhere": (
            "spreads before 2016 were wider than the convention was calibrated on, and this span "
            "reaches back to 1999, so the result is reported at 2x and 3x as well as at 1x"
        ),
    },
    "metrics": [
        "gross Sharpe",
        "net Sharpe",
        "annual gross and net return",
        "realised volatility",
        "information coefficient at the primary horizon",
        "incremental IC beyond the nominal control",
        "turnover",
        "annual cost",
        "signal and position persistence",
        "positive temporal blocks",
        "leave-one-currency-out",
        "currency contribution",
        "monotonicity across valuation terciles",
        "worst 12-month window",
        "top 1 / 5 / 10 day contribution",
        "max drawdown",
        "net at 2x and 3x cost",
        "risk leverage for 5% annual net",
        "routed margin utilisation",
        "gap stress",
    ],
    "screen": {
        "kind": "development screen, symmetric and exhaustive; seen data decides nothing",
        "shared_conditions": [
            "book A gross Sharpe > 0",
            "the primary test C has positive gross and net",
            "C carries a positive net increment over the nominal control B",
            "the valuation ordering is economically sensible: mean forward excess return falls monotonically from the cheap tercile to the dear one",
            "a majority of the temporal blocks are positive",
            "no single currency carries more than half of the gross, and the sign survives dropping any one of the eight",
            "the result is not one episode: removing the best twelve-month window leaves the sign",
            f"turnover at or below {TURNOVER_BOUND:g} round trips a year per unit gross",
            f"net Sharpe stays positive at {COST_STRESSES[0]:g}x and {COST_STRESSES[1]:g}x cost",
            "the sign is unchanged under the declared robustness anchor",
            "5% annual net is reachable at a target volatility whose gap stress, measured on this universe, does not force a loss-cut, and whose required volatility is at most 15%",
        ],
        "candidate": f"every shared condition holds and C's net Sharpe is at least {CANDIDATE_NET_SHARPE}",
        "marginal_candidate": (
            f"every shared condition holds and C's net Sharpe is in [{MARGINAL_NET_SHARPE}, "
            f"{CANDIDATE_NET_SHARPE}) with turnover at or below half the bound. The ruling allows "
            "this tier for a slow, stable source; it is a tier for returning to Human, never for "
            "advancing, and a diversification argument alone may not reach it while the programme "
            "has no positive core"
        ),
        "stop": "every other outcome, including any failure of a shared condition at any Sharpe",
        "status_candidate": "REAL_EXCHANGE_RATE_VALUATION_DEVELOPMENT_CANDIDATE",
        "status_marginal": "REAL_EXCHANGE_RATE_VALUATION_MARGINAL_DEVELOPMENT_CANDIDATE",
        "status_stop": "REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT",
        "status_data": "REAL_EXCHANGE_RATE_VALUATION_DATA_NOT_DECISION_GRADE",
        "no_automatic_progress_to_fresh": True,
    },
    "evaluated_separately_not_merged": (
        "standalone economics, stability, turnover and cost, and any future diversification value "
        "are reported apart. A net Sharpe below the bands is not rescued by calling it a "
        "diversifier, and no fixed 0.5 rule is applied to close the family"
    ),
    "prohibited_after_the_result": [
        "changing the anchor, the lag, the horizon, the cadence, the sign or the universe",
        "adding a control, a book or a currency",
        "re-running at another volatility target or cost convention to rescue the economics",
        "any nonlinear or ML formulation",
        "reading any protected span, or extending the request past the frozen end date",
    ],
}


__all__ = [
    "CANDIDATE_NET_SHARPE",
    "COST_STRESSES",
    "CPI_PUBLICATION_LAG_MONTHS",
    "MARGINAL_NET_SHARPE",
    "MIN_ANCHOR_MONTHS",
    "PREREG",
    "PRIMARY_HORIZON_MONTHS",
    "SPAN",
    "TURNOVER_BOUND",
    "UNIVERSE",
    "WARM_UP_END",
]
