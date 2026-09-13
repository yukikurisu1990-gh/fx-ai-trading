"""The frozen pre-registration of Track 1 — written before any model is fitted.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Everything the development run may do is declared here: the corpus, the
features, the target and horizon, the model and its capacity, the walk-forward
geometry, the primary book, the baselines, the diagnostics, the cost model, the
metrics, the search budget, the kill clauses and the survival clauses.

It is frozen by a SHA-256 over the canonical specification **and** over the
normalised source of every module that computes a number the verdict reads, so a
changed definition is a changed specification. The development driver refuses to
run on a mismatch.

H-003 and C08 — the novelty boundary, stated before the run
-----------------------------------------------------------

**H-003** (Exploratory Round 1, role G) traded pair-level relative strength and
found that 96% of its gross was net currency exposure, beaten by a matched
time-series control. **C08** (decision-grade inventory) closed currency-level
**rank persistence** — "the currency that has been strong stays strong" — as the
same-shape family, enforced by `assert_prospective`.

Track 1 differs on four axes, each of which is a property of the code, not of a
sentence:

1. **Unit of prediction.** A continuous expected-return vector over eight
   currencies, never a pair signal. Pairs appear only in execution.
2. **Common exposure is handled by construction.** Weights are sum-zero, so the
   equally weighted basket drops out of P&L identically, and the trailing
   leading factor of the currency cross-section is projected out of the scores
   before any weight exists. H-003's failure was exposure it did not know it had;
   this book's exposure to the dominant factor is removed ex ante and its
   residual is measured ex post.
3. **The hypothesis is conditional estimation, not persistence.** Strength over
   three horizons is three of seven inputs to a ridge model that may weight any
   of them at zero or negative, alongside volatility, dispersion, trend age and
   factor beta. The C08 hypothesis — raw persistence, unfitted — is run as
   **Baseline 1**, and the primary must beat it outright or it is killed: a
   primary that only reproduces the closed family is the closed family.
4. **Continuous weights and partial rebalancing** replace binary top/bottom
   selection, so the book trades target differences rather than entries and
   exits.

If the primary's per-currency P&L or its fitted coefficients show it to be a
persistence book in disguise — the momentum coefficients carrying the fit and
the primary indistinguishable from Baseline 1 — the kill clause
`does_not_beat_the_unfitted_benchmark` is the pre-registered stop.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Final

from scripts.research.continuous_portfolio import (
    CASE_A,
    CASE_B,
    CASE_C,
    CHARGED_ONE_WAY_BP,
    CHARGED_ROUTING_RATIO,
    ECONOMIC_BANDS,
    PAIR_ROUNDTRIP_BP,
)
from scripts.research.continuous_portfolio.construction import BookConfig
from scripts.research.continuous_portfolio.evaluation import VOL_SCENARIOS
from scripts.research.continuous_portfolio.model import (
    EMBARGO_DAYS,
    FEATURES,
    HORIZON_DAYS,
    TARGET_EFFECTIVE_DF,
)
from scripts.research.model_learning import PAIRS_20, PROTECTED_SPANS, SEEN_SPANS


class PreregistrationError(RuntimeError):
    """Raised when a run is attempted against a specification that has moved."""


WALK_FORWARD: Final[dict[str, Any]] = {
    "scheme": "expanding_window_walk_forward",
    "initial_train_years": 1.5,
    "step_years": 0.5,
    "purge_days": HORIZON_DAYS,
    "embargo_days": EMBARGO_DAYS,
    "random_splits": False,
}

PRIMARY: Final[BookConfig] = BookConfig(name="primary")

BASELINES: Final[dict[str, Any]] = {
    "baseline_0_cash": "zero position; net return identically zero",
    "baseline_1_unfitted_persistence": (
        "the 60-day currency excess-return z-score, unfitted and positive-signed, "
        "through the primary book's own construction and efficiency bundle — the "
        "C08-shaped rule the primary must beat outright"
    ),
    "baseline_2_linear_no_bundle": (
        "the primary's fitted expected returns through linear score weights, no "
        "factor neutralisation, no cap, full daily rebalance, no volatility target"
    ),
}

BASELINE_2: Final[BookConfig] = BookConfig(
    name="baseline_2_linear_no_bundle",
    mapping="linear",
    neutralize_leading_factor=False,
    weight_cap=1.0,
    band=0.0,
    vol_target=None,
)

#: Diagnostics are reported and never replace the primary. Each changes exactly
#: one declared choice.
DIAGNOSTICS: Final[tuple[BookConfig, ...]] = (
    BookConfig(name="diag_unlevered_gross_1", vol_target=None),
    BookConfig(name="diag_mapping_linear", mapping="linear"),
    BookConfig(name="diag_mapping_rank", mapping="rank"),
    BookConfig(name="diag_band_none", band=0.0),
    BookConfig(name="diag_band_0_15", band=0.15),
    BookConfig(name="diag_no_factor_neutralisation", neutralize_leading_factor=False),
    BookConfig(name="diag_cost_1_5x", cost_multiple=1.5),
    BookConfig(name="diag_cost_2x", cost_multiple=2.0),
    BookConfig(name="diag_drawdown_governor", drawdown_governor=True),
)

COST_MODEL: Final[dict[str, Any]] = {
    "pair_round_trip_bp": PAIR_ROUNDTRIP_BP,
    "charged_routing_ratio": CHARGED_ROUTING_RATIO,
    "charged_one_way_bp_per_unit_currency_notional": CHARGED_ONE_WAY_BP,
    "charged_on": "sum|x_t - x_(t-1)| only — the realised delta of the held exposure",
    "not_charged": [
        "per prediction",
        "per signal",
        "per pair as an independent round trip",
        "a close and reopen of an unchanged position",
    ],
    "faithful_implementation_cost": (
        "equal-split pair one-way notional x half the pair round trip, reported beside "
        "the charge and never used for the verdict"
    ),
    "stress_multiples": [1.0, 1.5, 2.0],
    "financing": (
        "excluded from P&L; policy-rate carry accrual on the held exposure is reported "
        "as a diagnostic so a book that earns or pays carry systematically is visible"
    ),
}

ADJUDICATION_RULES: Final[dict[str, Any]] = {
    "negligible_net_sharpe": 0.20,
    "max_turnover_per_unit_gross": 50.0,
    "max_mean_leverage": 5.0,
    "economic_bands": [[ceiling, label] for ceiling, label in ECONOMIC_BANDS],
    "case_a": CASE_A,
    "case_b": CASE_B,
    "case_c": CASE_C,
    "case_a_requires": [
        "no kill clause",
        "net Sharpe >= 0.5",
        "more than half of folds positive",
        "no currency above half of positive gross P&L",
        "top 10 days at most half of net",
        "net Sharpe positive at 1.5x cost",
    ],
    "case_b_requires": [
        "no kill clause",
        "net Sharpe >= 0.3",
        "more than half of folds positive",
        "no currency above half of positive gross P&L",
        "top 10 days at most half of net",
    ],
    "kill_clauses": [
        "net Sharpe <= 0",
        "net Sharpe < 0.20 (net return economically negligible)",
        "net P&L <= 0 once the five best days are removed",
        "gross P&L <= 0 once the best currency is removed",
        "fewer than half of folds positive",
        "primary net Sharpe <= Baseline 1 net Sharpe",
        "turnover above 50 round trips a year per unit of gross",
        "mean leverage above 5x at the 10% volatility target",
    ],
    "an_increment_over_a_negative_baseline_is_never_a_survival_reason": True,
}

SEARCH_BUDGET: Final[dict[str, Any]] = {
    "feature_sets": 1,
    "features": len(FEATURES),
    "model_classes": 1,
    "horizons": 1,
    "primary_mappings": 1,
    "diagnostic_mappings": 2,
    "primary_bands": 1,
    "diagnostic_bands": 2,
    "fitted_models": 1,
    "baselines": 3,
    "diagnostic_books": 9,
    "hyperparameter_search": "none — the ridge penalty is solved to a declared df",
    "selection_among_diagnostics": "forbidden — the verdict reads the primary only",
    "automl": False,
}

FORBIDDEN_AFTER_RESULTS: Final[tuple[str, ...]] = (
    "adding a feature",
    "changing the horizon",
    "flipping a sign",
    "excluding a currency",
    "optimising the band",
    "optimising leverage or the volatility target",
    "adding a regime filter",
    "adding a non-linear model",
    "reading any protected span for any purpose",
)

PROTECTED_BOUNDARY: Final[dict[str, Any]] = {
    "seen_spans_used": {name: (b["start"], b["end"]) for name, b in SEEN_SPANS.items()},
    "protected_spans_never_used": {
        name: (b["start"], b["end"], b["status"]) for name, b in PROTECTED_SPANS.items()
    },
    "not_authorised": [
        "Track 3 event/volatility overlay",
        "broker-authenticated access",
        "paper-forward execution",
        "demo or live orders",
        "non-linear models",
    ],
}

#: Modules whose code defines a number the verdict reads. Hashed with line
#: endings normalised, because a digest of raw bytes is a property of the
#: checkout — the model-learning prereg learned that on CI.
HASHED_SOURCES: Final[tuple[str, ...]] = (
    "scripts/research/continuous_portfolio/__init__.py",
    "scripts/research/continuous_portfolio/construction.py",
    "scripts/research/continuous_portfolio/model.py",
    "scripts/research/continuous_portfolio/evaluation.py",
    "scripts/research/continuous_portfolio/development.py",
    "scripts/research/model_learning/features.py",
    "scripts/research/model_learning/corpus.py",
    "scripts/research/model_learning/walkforward.py",
)

_ROOT: Final[Path] = Path(__file__).resolve().parents[3]


def source_digests() -> dict[str, str]:
    out = {}
    for relative in HASHED_SOURCES:
        text = (_ROOT / relative).read_text(encoding="utf-8")
        normalised = "".join(line + chr(10) for line in text.splitlines())
        out[relative] = hashlib.sha256(normalised.encode("utf-8")).hexdigest()
    return out


def specification() -> dict[str, Any]:
    return {
        "track": "TRACK_1_CONTINUOUS_CURRENCY_PORTFOLIO",
        "corpus": {
            "pairs": list(PAIRS_20),
            **PROTECTED_BOUNDARY,
        },
        "features": list(FEATURES),
        "target": f"forward {HORIZON_DAYS}-day cumulative currency excess return",
        "model": {
            "class": "pooled ridge over (day, currency) rows",
            "target_effective_df": TARGET_EFFECTIVE_DF,
            "standardisation": "training fold only",
        },
        "walk_forward": WALK_FORWARD,
        "primary": asdict(PRIMARY),
        "baselines": BASELINES,
        "baseline_2": asdict(BASELINE_2),
        "diagnostics": [asdict(config) for config in DIAGNOSTICS],
        "cost_model": COST_MODEL,
        "vol_scenarios": list(VOL_SCENARIOS),
        "adjudication": ADJUDICATION_RULES,
        "search_budget": SEARCH_BUDGET,
        "forbidden_after_results": list(FORBIDDEN_AFTER_RESULTS),
        "source_sha256": source_digests(),
    }


def freeze_hash() -> str:
    canonical = json.dumps(specification(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


FROZEN_HASH: Final[str] = "UNFROZEN"


def assert_frozen() -> str:
    measured = freeze_hash()
    if measured != FROZEN_HASH:
        raise PreregistrationError(
            f"the pre-registration has changed: recorded {FROZEN_HASH}, measured {measured}. "
            "A development run against a moved specification is not a pre-registered run."
        )
    return measured


__all__ = [
    "ADJUDICATION_RULES",
    "BASELINES",
    "BASELINE_2",
    "COST_MODEL",
    "DIAGNOSTICS",
    "FORBIDDEN_AFTER_RESULTS",
    "FROZEN_HASH",
    "HASHED_SOURCES",
    "PRIMARY",
    "PROTECTED_BOUNDARY",
    "SEARCH_BUDGET",
    "WALK_FORWARD",
    "PreregistrationError",
    "assert_frozen",
    "freeze_hash",
    "source_digests",
    "specification",
]
