"""The frozen pre-registration for the three selected development tracks.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Everything the development stage is allowed to do is written here before it runs:
the target, the horizon, the exact feature list, the model class and its
shrinkage, the cross-validation architecture, the cost model, the metrics, the
baseline each track must beat, the search budget, the success rule and the kill
rule.

It is frozen by a **content hash**, not by a promise
-----------------------------------------------------

`freeze_hash()` is the SHA-256 of this specification's canonical JSON. The
development driver refuses to run unless the hash it recomputes matches
`FROZEN_HASH`, so editing a threshold after seeing a fold is not a discipline
question — the run stops. Re-freezing is a deliberate act that changes a constant
in this file and invalidates every result recorded against the old value.

The search budget is one configuration per track
------------------------------------------------

Not a preference. `universe.phase_budget` shows that three tracks selected on the
same 3.174 out-of-fold years can afford three effectively independent selections
in total, and three tracks with one configuration each sits at 0.488 of annual IR
inflation against a 0.5 ceiling. There is no hyperparameter search anywhere in
this phase, and Level 2 of the model hierarchy is not run at all — the capacity
budget rules it out whatever a validation fold would have said.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Final

from scripts.research.feasibility import COST_STRESS_MULTIPLE
from scripts.research.feasibility.inventory import BASKET_ROUNDTRIP_BP, PAIR_ROUNDTRIP_BP
from scripts.research.model_learning import TRAIN_YEARS_TOTAL
from scripts.research.model_learning.budgets import (
    MINIMUM_RELEVANT_INCREMENTAL_IR,
    REQUIRED_SIGNAL_RETENTION,
)
from scripts.research.model_learning.universe import (
    INITIAL_TRAIN_YEARS,
    VALIDATION_YEARS,
)


class PreregistrationError(RuntimeError):
    """Raised when a run is attempted against a specification that has moved."""


CV_ARCHITECTURE: Final[dict[str, Any]] = {
    #: One vocabulary, not two. The name has to be a member of the role gate's
    #: frozen set of temporal architectures — a prereg that spells its own scheme
    #: differently from the gate that admits it is a prereg the gate cannot check,
    #: and this one did until a test compared them.
    "scheme": "walk_forward",
    "window": "expanding",
    "initial_train_years": INITIAL_TRAIN_YEARS,
    "step_years": 0.5,
    "train_years_total": TRAIN_YEARS_TOTAL,
    "out_of_fold_years": VALIDATION_YEARS,
    #: The forward window is purged from the end of every training fold and an
    #: embargo is applied after it, so a label that straddles a boundary belongs
    #: to neither side. Overlapping forward returns are the leak Round 1's random
    #: split never closed.
    "purge_bars": "the full forward horizon of the target",
    "embargo_bars": "one further day",
    "validation_never_returns_to_training": True,
    "random_splits_forbidden": True,
}

COST_MODEL: Final[dict[str, Any]] = {
    "pair_roundtrip_bp": PAIR_ROUNDTRIP_BP,
    "basket_roundtrip_bp": BASKET_ROUNDTRIP_BP,
    "basis": "Track 3's measured market-order round trip, scaled by basket gross exposure",
    "stress_multiple": COST_STRESS_MULTIPLE,
    "charged": "on realised turnover, every rebalance, both legs",
}

METRICS: Final[tuple[str, ...]] = (
    "out_of_fold_net_annualised_information_ratio",
    "out_of_fold_gross_annualised_information_ratio",
    "annualised_turnover",
    "net_annualised_return_bp",
    "net_at_stressed_cost",
    "per_fold_net_information_ratio",
    "per_currency_net_contribution",
    "per_volatility_regime_net_contribution",
    "top_ten_day_share_of_net",
    "maximum_drawdown",
    "rank_information_coefficient",
    "fold_to_fold_coefficient_stability",
)

#: Every condition must hold. The economic ones first, because a model that is
#: statistically interesting and economically dead is the thing this programme
#: keeps rediscovering.
SUCCESS_RULE: Final[dict[str, Any]] = {
    "beats_its_declared_baseline_by_at_least_ir": MINIMUM_RELEVANT_INCREMENTAL_IR,
    "net_annualised_ir_positive": True,
    "survives_stressed_cost": True,
    "positive_in_at_least_this_share_of_folds": 0.75,
    "positive_currencies_at_least": 5,
    "top_ten_day_share_of_net_at_most": 0.50,
    "fitted_effective_parameters_within_budget": True,
}

KILL_RULE: Final[tuple[str, ...]] = (
    "the fitted model does not beat its declared baseline by the minimum relevant "
    "incremental information ratio",
    "out-of-fold net annualised return is negative",
    "the result does not survive the stressed cost multiple",
    "fewer than three quarters of folds are positive",
    "fewer than five currencies contribute positively",
    "the ten largest days are more than half of the net",
    "the effect is confined to one volatility regime",
    "any leakage control is found to have been violated",
)

#: What may **not** be done in response to a kill, restated where the development
#: stage will read it.
FORBIDDEN_RESCUES: Final[tuple[str, ...]] = (
    "adding a feature after seeing a fold",
    "changing the horizon after seeing a fold",
    "flipping the sign of a failing model",
    "adding a regime condition that isolates the losing period",
    "raising the model's capacity",
    "re-running with a different seed and reporting the better one",
    "reading any protected span for any purpose",
)

TRACKS: Final[tuple[dict[str, Any], ...]] = (
    {
        "track": "A",
        "candidate_id": "M01_currency_cross_sectional_ranking",
        "role": "cross_sectional_ranking",
        "target": (
            "the next UTC day's return of each G10 currency against the equally "
            "weighted basket of the other seven, minus the round trip charged on the "
            "rebalance that establishes the position"
        ),
        "horizon_days": 1.0,
        "cross_section": "8 G10 currencies, one shared coefficient vector",
        #: Exactly seven, frozen. A feature added later is a different candidate
        #: and costs a fresh configuration out of a budget that has none.
        "features": (
            "currency_excess_return_5d_z",
            "currency_excess_return_20d_z",
            "currency_excess_return_60d_z",
            "currency_realised_vol_20d_z",
            "cross_sectional_dispersion_20d_z",
            "currency_beta_to_usd_factor_60d",
            "currency_beta_to_risk_factor_60d",
        ),
        "model_class": "ranking_linear",
        "model_settings": {"coefficients": 7, "effective_fraction": 0.6},
        "regularisation": (
            "ridge, penalty chosen by the declared effective-degrees-of-freedom target "
            "of 4.2 inside each training fold — a target, not a tuned hyperparameter"
        ),
        "baseline": (
            "Level 0: the unfitted equal-weight cross-sectional rank of "
            "currency_excess_return_20d_z alone, long the top two and short the bottom "
            "two, at the same turnover and the same cost model"
        ),
        "configurations": 1,
        "turnover_per_year": 252.0,
        "roundtrip_cost_bp": BASKET_ROUNDTRIP_BP,
        "declared_effective_parameters": 4.2,
    },
    {
        "track": "B",
        "candidate_id": "M03_regime_conditioned_level_multi_timeframe",
        "role": "direction_or_return_generator",
        "target": (
            "the same cost-adjusted next-day currency-against-basket return, with the "
            "level — not the slopes — allowed to differ between two states"
        ),
        "horizon_days": 1.0,
        "cross_section": "8 G10 currencies, shared slopes, per-state intercept",
        "features": (
            "currency_excess_return_20d_z",
            "multi_timeframe_alignment_h1_h4_d1",
            "currency_realised_vol_20d_z",
            "trend_age_d1_normalised",
        ),
        "state_variable": (
            "a two-state split on the 60-day realised volatility of the currency "
            "basket, thresholded at its expanding-window median inside the training "
            "fold only"
        ),
        "model_class": "regime_intercept_linear",
        "model_settings": {"states": 2, "coefficients": 4, "effective_fraction": 0.6},
        "regularisation": "ridge to an effective-degrees-of-freedom target of 2.4 on the slopes",
        "baseline": (
            "Level 0: the same four features with a single fitted intercept and no "
            "regime split, which isolates what the state itself is worth"
        ),
        "configurations": 1,
        "turnover_per_year": 252.0,
        "roundtrip_cost_bp": BASKET_ROUNDTRIP_BP,
        "declared_effective_parameters": 4.4,
    },
    {
        "track": "C",
        "candidate_id": "M13_hurdle_clearing_probability_with_learned_threshold",
        "role": "trade_or_skip",
        "target": (
            "the probability that a currency leg's absolute next-day move exceeds its "
            "own round trip, with the accept threshold fitted inside the training fold"
        ),
        "horizon_days": 1.0,
        "cross_section": "8 G10 currency legs",
        "features": (
            "currency_realised_vol_20d_z",
            "currency_realised_vol_5d_over_20d",
            "days_to_next_scheduled_central_bank_decision",
            "days_since_last_scheduled_central_bank_decision",
            "spread_state_20d_z",
            "tick_activity_state_20d_z",
        ),
        "model_class": "linear",
        "model_settings": {"coefficients": 6, "effective_fraction": 0.6},
        "regularisation": "ridge to an effective-degrees-of-freedom target of 3.6",
        "base_opportunity": (
            "every daily currency leg on which Track A's baseline takes a position. "
            "Its unconditional cost-adjusted expectancy is measured FIRST and is a "
            "kill rule: if the base is negative, a filter inside it is not evidence"
        ),
        "baseline": "Level 0: take every leg in the base opportunity, no filter",
        "configurations": 1,
        "turnover_per_year": 252.0,
        "roundtrip_cost_bp": BASKET_ROUNDTRIP_BP,
        "declared_effective_parameters": 3.6,
    },
)

MAXIMUM_RESEARCH_BUDGET: Final[dict[str, Any]] = {
    "tracks": len(TRACKS),
    "configurations_per_track": 1,
    "total_fitted_configurations": len(TRACKS),
    "phase_effective_configurations": 3.0,
    "selection_inflation_annual_ir": 0.488,
    "ceiling": MINIMUM_RELEVANT_INCREMENTAL_IR,
    "model_hierarchy_levels_run": ("Level 0 baseline", "Level 1 regularised linear"),
    "level_2_not_run_because": "the capacity budget, not the validation result",
    "required_signal_retention": REQUIRED_SIGNAL_RETENTION,
}

MULTIPLE_TESTING_CONTROLS: Final[tuple[str, ...]] = (
    "one fitted configuration per track, declared before any fit",
    "three tracks, whose phase-level selection inflation is computed and reported",
    "no hyperparameter search, no feature selection, no threshold sweep outside a fold",
    "the baseline comparison is an absolute threshold, not a maximum over candidates",
    "the roughly 1,200 configurations already run against these spans are disclosed "
    "and are NOT corrected for — nothing in a seen-data phase can correct for them",
)


def specification() -> dict[str, Any]:
    """The whole frozen object, in the order a reader needs it."""
    return {
        "phase": "model_learning_development",
        "corpus": {
            "train_years_total": TRAIN_YEARS_TOTAL,
            "spans": ("momentum_2021_2023", "supplemental_2023_2025", "development_2025"),
            "protected_spans_read": False,
        },
        "cv_architecture": CV_ARCHITECTURE,
        "cost_model": COST_MODEL,
        "metrics": list(METRICS),
        "success_rule": SUCCESS_RULE,
        "kill_rule": list(KILL_RULE),
        "forbidden_rescues": list(FORBIDDEN_RESCUES),
        "tracks": [dict(track) for track in TRACKS],
        "maximum_research_budget": MAXIMUM_RESEARCH_BUDGET,
        "multiple_testing_controls": list(MULTIPLE_TESTING_CONTROLS),
    }


def freeze_hash() -> str:
    """SHA-256 of the canonical specification. The object, not a description of it."""
    canonical = json.dumps(specification(), sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


#: Recorded after the specification above was written and before anything was
#: fitted. A development run checks it and refuses to proceed on a mismatch.
FROZEN_HASH: Final[str] = "6e912e38f07e524d3c6861c0755492b2c014df0754033b5fa33b0a02345eeb4b"


def assert_frozen() -> str:
    """Refuse to proceed if the specification has moved since it was frozen."""
    measured = freeze_hash()
    if measured != FROZEN_HASH:
        raise PreregistrationError(
            f"the pre-registration has changed: recorded {FROZEN_HASH}, measured "
            f"{measured}. A development run against a moved specification is not a "
            "pre-registered run. Re-freezing is deliberate and invalidates every "
            "result recorded against the previous value."
        )
    return measured


__all__ = [
    "COST_MODEL",
    "CV_ARCHITECTURE",
    "FORBIDDEN_RESCUES",
    "FROZEN_HASH",
    "KILL_RULE",
    "MAXIMUM_RESEARCH_BUDGET",
    "METRICS",
    "MULTIPLE_TESTING_CONTROLS",
    "SUCCESS_RULE",
    "TRACKS",
    "PreregistrationError",
    "assert_frozen",
    "freeze_hash",
    "specification",
]
