# ruff: noqa: E501 -- pre-registration prose
"""The T-R pre-registration. Frozen and committed before the yields meet FX returns.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Everything below was fixed by the integrity audit and this file, and committed, in
a commit that contains **no result**. The signal has never been correlated with an
FX return at the moment this is written: the only FX information used so far is
the trading calendar, which decided coverage.

What may not change afterwards: the universe, the signal, its lookback and sign,
the two horizons, the three books, the availability lag, the book configuration
and the screen. A result may not reopen any of them.
"""

from __future__ import annotations

import math
from typing import Any, Final

from scripts.research.edge_sources import capacity

#: Fixed by `audit.py` on the acquired sources, before any signal existed.
UNIVERSE: Final[tuple[str, ...]] = ("CAD", "EUR", "GBP", "JPY", "USD")
EXCLUDED: Final[dict[str, str]] = {
    "AUD": "the RBA's table F2 refuses every automated request from this environment (HTTP 403)",
    "NZD": "the RBNZ's current daily file is refused (HTTP 403); the older file stops on 2025-08-22",
    "CHF": "the SNB's daily cube stops on 2025-07-31, so it cannot cover the decision span",
}

#: Effective breadth of a five-currency sum-zero book: fewer independent directions
#: than the eight-currency book the capacity arithmetic was calibrated on. Declared
#: here, before any result, and used only to state what the design would need.
EFFECTIVE_BREADTH: Final[float] = 2.5

DECISION_SPAN: Final[dict[str, str]] = {"first": "2021-04-27", "last": "2025-12-26"}
DECISION_DAYS: Final[int] = 1213


def feasibility() -> dict[str, Any]:
    """Signal-blind: what this design would have to show, computed before it runs."""
    rows = {}
    for half_life in (5.0, 20.0):
        law = capacity.band_law(half_life)
        drag = capacity.cost_ir_drag(law["turnover"])
        rows[f"half_life_{half_life:g}d"] = {
            "turnover_per_unit_gross": law["turnover"],
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
        "note": (
            "the span can separate a net Sharpe of about 1.1 from zero at 80% power, so a "
            "development result of 0.3-0.5 will not be decision-grade whichever way it comes out"
        ),
    }


PREREG: Final[dict[str, Any]] = {
    "track": "T-R — market yield repricing",
    "authority": "Human + ChatGPT ruling of 2026-09-16 (D-2 approved; T-R first)",
    "classification": "NON_DECISION_BEARING_EXPLORATORY_ONLY",
    "question": (
        "does the repricing of market-priced two-year sovereign yields carry incremental "
        "predictive content for G10 FX spot relative returns, beyond the FX price information "
        "already available at the same moment?"
    ),
    "why_new": (
        "H-016 closed the policy rate — the level and change of a step function the central bank "
        "sets. The market's two-year yield is a different quantity: it moves daily and prices the "
        "path. It has never been acquired or tested here. C09 was never executed, and the inventory "
        "records it as failing both the horizon and the economic condition, which this design does "
        "not dispute — it only uses a different cost convention (band-driven turnover, not one "
        "round trip per day)."
    ),
    "stage": "Stage 1: one unfitted rule. No fitted model, no ML, no hyperparameter.",
    "universe": {
        "currencies": list(UNIVERSE),
        "fixed_by": "artifacts/research/market_yields/integrity.json, before any signal",
        "excluded": EXCLUDED,
        "reduced_cross_section_accepted": (
            "five currencies is a reduced universe; the ruling permits it rather than forcing a "
            "G10 cross-section, and the reduced breadth is carried into the feasibility below"
        ),
    },
    "information": {
        "series": "one official two-year sovereign yield per currency (see sources.py)",
        "availability_rule": (
            "publication times are unconfirmed on the source pages, so the conservative rule is "
            "uniform: a yield dated d may only inform a position taken one trading day later, and "
            "that position earns the next day's return. No same-day use, ever."
        ),
        "carry_forward": "the last published value, aged at most ten calendar days",
    },
    "signal": {
        "definition": "cross-sectional z-score, over the five currencies, of the change in the two-year yield over the lookback",
        "lookback_days": 5,
        "sign": "+1 — a currency whose yield rose relative to the cross-section is expected to appreciate",
        "sign_frozen": True,
        "inversion_after_the_result_prohibited": True,
    },
    "targets": {
        "horizons_days": [5, 20],
        "target": "currency excess return against the equally weighted basket of the corpus",
        "both_declared_before_execution": True,
    },
    "books": {
        "A": "the yield repricing signal alone",
        "B": "FX momentum over the same lookback — the closed / underpowered price family, as its own book",
        "C": "the yield signal cross-sectionally residualised against that FX momentum — the primary test",
        "no_control_zoo": "exactly these three books; no further conditioning variable enters",
    },
    "book_configuration": {
        "architecture": "the Track 1 execution layer, reused unchanged: currency weights capped at 0.25, sum-zero, no-trade band 0.10, partial rebalance, cost charged on the traded delta",
        "track_1_alpha_model_reused": False,
        "mapping": "linear on the declared score, because the score is a standardised rank-like quantity and not a return forecast",
        "factor_neutralisation": True,
        "vol_target": 0.10,
        "leverage_cap": "none; required leverage, routed margin and the gap stress are reported instead",
    },
    "metrics": [
        "gross Sharpe",
        "net Sharpe",
        "annual net return",
        "turnover",
        "annual cost",
        "information coefficient at both horizons",
        "signal persistence",
        "fold stability over six contiguous blocks",
        "per-currency contribution",
        "top 1 / 5 / 10 day concentration",
        "net without the top five days",
        "max drawdown",
        "required risk leverage for 5% and 10% net",
        "routed margin utilisation",
        "gap stress",
    ],
    "screen": {
        "kind": "development screen, symmetric and exhaustive; seen data decides nothing",
        "advance": [
            "book A gross Sharpe > 0 and net Sharpe >= 0.3",
            "book C (residualised) keeps a positive net increment over book B",
            "the sign survives dropping any single currency",
            "a majority of the six contiguous blocks are positive",
            "the 10% vol target is reachable inside the declared gap stress",
        ],
        "stop": "any result that fails even one advance condition; there is no held state",
        "status_if_advance": "MARKET_YIELD_REPRICING_DEVELOPMENT_CANDIDATE",
        "status_if_stop": "MARKET_YIELD_REPRICING_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT",
        "status_if_data_fails": "MARKET_YIELD_REPRICING_DATA_NOT_DECISION_GRADE",
        "no_automatic_progress_to_fresh": True,
        "returns_to_human": "either way, the result goes back to Human + ChatGPT",
    },
    "prohibited_after_the_result": [
        "changing the signal definition, lookback, sign or horizons",
        "adding or removing a currency, a control or a book",
        "re-running at another volatility target to rescue the economics",
        "reading any protected span",
        "promoting a stopped track to independent history without a new Human decision",
    ],
}


__all__ = [
    "DECISION_DAYS",
    "DECISION_SPAN",
    "EFFECTIVE_BREADTH",
    "EXCLUDED",
    "PREREG",
    "UNIVERSE",
    "feasibility",
]
