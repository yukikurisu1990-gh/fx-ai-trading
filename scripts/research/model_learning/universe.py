"""Eighteen model-learning directions, and what the two budgets do to them.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Every candidate differs from every other in **role, target or architecture** —
not in a hyperparameter, a timeframe or a model name. Three are included because
they are expected to fail and the failure is the information: a tree ensemble at
a usable size, an intraday design whose turnover puts the hurdle out of reach,
and a family this programme has already closed.

Nothing here computes a return, a sign, an information coefficient or a p-value.
The verdicts are properties of the designs.

⭐ The phase budget
-------------------

`phase_budget` applies the search budget to the **whole phase** rather than to
one track. It has to: three tracks selected on the same 3.17 out-of-fold years
are three selections on one sample, and charging each of them separately is how a
research programme spends a budget three times. The affordable shapes turn out to
be narrow — three tracks with one fitted configuration each, two tracks with two,
or one track with seven — and the capacity budget independently rules out the
third level of the model hierarchy, so the ladder stops at Level 1 whatever the
validation would have said.
"""

from __future__ import annotations

import math
from typing import Any, Final

from scripts.research.feasibility.inventory import (
    BASKET_ROUNDTRIP_BP,
    PAIR_ROUNDTRIP_BP,
)
from scripts.research.model_learning import (
    CURRENCIES_G10,
    PAIRS_20,
    TRAIN_YEARS_TOTAL,
    ModelRole,
    role_gate,
)
from scripts.research.model_learning import budgets as budget_module
from scripts.research.model_learning import effective_sample as sample_module

#: Walk-forward with an initial training window of 1.5 years and a half-year
#: step, so the out-of-fold span is the rest of the corpus. Frozen here because
#: the search budget scales with it and a later stage must not lengthen it.
INITIAL_TRAIN_YEARS: Final[float] = 1.5
VALIDATION_YEARS: Final[float] = round(TRAIN_YEARS_TOTAL - INITIAL_TRAIN_YEARS, 3)

#: Effective independent directions, by cross-section. The pair figure is this
#: repository's measured range; the currency figure is smaller than eight for the
#: same reason H-003 found — a dollar factor runs through all of them.
EFFECTIVE_PAIRS: Final[float] = 5.0
EFFECTIVE_CURRENCIES: Final[float] = 4.0

_LEAKAGE_CONTROLS: Final[tuple[str, ...]] = (
    "features use closed bars only, evaluated at the bar after the decision",
    "forward windows are purged and embargoed across every fold boundary",
    "any normalisation is fitted inside the training fold and applied forward",
    "the cross-sectional neutralisation uses only same-bar information",
)


def _design(**kwargs: Any) -> role_gate.ModelDesign:
    kwargs.setdefault("leakage_controls", _LEAKAGE_CONTROLS)
    kwargs.setdefault("training_architecture", "walk_forward")
    kwargs.setdefault("validation_years", VALIDATION_YEARS)
    return role_gate.ModelDesign(**kwargs)


def catalogue() -> list[role_gate.ModelDesign]:
    """Eighteen directions, none of them a hyperparameter variant of another."""
    return [
        _design(
            candidate_id="M01_currency_cross_sectional_ranking",
            hypothesis=(
                "relative expected return across the eight G10 currencies is partly "
                "predictable from currency-level factor state, even where the absolute "
                "direction of any one pair is not"
            ),
            role=ModelRole.RANKING,
            target="cost-adjusted next-day relative return of a currency against the basket",
            target_is_cost_adjusted=True,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("currency_factor_state", "multi_horizon_structure", "dispersion"),
            model_class="ranking_linear",
            model_settings={"coefficients": 7, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            rank_stability_metric="fold-to-fold Spearman of the fitted coefficient vector",
            prior_research_overlap=(
                "H-003 closed simple currency-strength relative value; this shares its "
                "cross-section and nothing else"
            ),
            why_different_from_round_1=(
                "Round 1 predicted a pair's own direction from its own price. This "
                "predicts a currency's return relative to a basket, with shared "
                "coefficients across currencies, so the dollar factor H-003 found "
                "carrying 96% of the gross is removed by construction rather than "
                "hoped away"
            ),
            expected_information_gain=(
                "whether a shared low-capacity cross-sectional mapping retains anything "
                "out of fold once the common factor is gone"
            ),
        ),
        _design(
            candidate_id="M02_residual_factor_adjusted_return",
            hypothesis=(
                "after removing the dollar, risk and commodity factors, the residual "
                "pair return carries a conditional mean a linear model can find"
            ),
            role=ModelRole.DIRECTION_OR_RETURN,
            target="cost-adjusted residual return of a pair after a three-factor projection",
            target_is_cost_adjusted=True,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("currency_factor_state", "volatility", "correlation"),
            model_class="linear",
            model_settings={"coefficients": 5, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=PAIR_ROUNDTRIP_BP,
            cross_sectional_units=len(PAIRS_20),
            effective_units=EFFECTIVE_PAIRS,
            prior_research_overlap="no closed family predicts a factor residual",
            why_different_from_round_1=(
                "the target is the residual, not the raw return, so the quantity being "
                "predicted is the one a factor-neutral book would actually earn"
            ),
            expected_information_gain=(
                "whether the 96% common component H-003 measured leaves a usable 4%"
            ),
        ),
        _design(
            candidate_id="M03_regime_conditioned_level_multi_timeframe",
            hypothesis=(
                "the level of expected relative return shifts with a slow multi-timeframe "
                "state, while the sensitivity to the features does not"
            ),
            role=ModelRole.DIRECTION_OR_RETURN,
            target="cost-adjusted next-day relative return, regime-conditioned intercept",
            target_is_cost_adjusted=True,
            horizon="1 day",
            holding_days=1.0,
            feature_families=(
                "multi_horizon_structure",
                "regime_state",
                "volatility",
                "currency_factor_state",
            ),
            model_class="regime_intercept_linear",
            model_settings={"states": 2, "coefficients": 4, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            prior_research_overlap=(
                "the decision forbids simple higher-timeframe sign conditioning, which "
                "this is not: the state enters the level, not the direction"
            ),
            why_different_from_round_1=(
                "Round 1's conditional work gated an existing rule on a state and lowered "
                "its net every time. Here the state is a fitted level inside one model "
                "rather than a filter applied outside it"
            ),
            expected_information_gain=(
                "whether the affordable form of regime conditioning — shared slopes, a "
                "state-dependent level — buys anything at all"
            ),
        ),
        _design(
            candidate_id="M04_cross_sectional_trade_skip",
            hypothesis=(
                "the weaker half of a cross-sectional ranking is not worth trading, so "
                "skipping it raises net return more than it lowers gross"
            ),
            role=ModelRole.TRADE_SKIP,
            target="whether a ranked leg clears its own round trip",
            target_is_cost_adjusted=True,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("dispersion", "volatility", "execution_cost_state"),
            model_class="linear",
            model_settings={"coefficients": 4, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            base_opportunity="every daily currency-vs-basket leg, taken unconditionally",
            base_expectancy_is_a_kill_rule=True,
            prior_research_overlap=(
                "H-002 closed conditional gates over an existing rule; this gates the "
                "unconditional base population instead"
            ),
            why_different_from_round_1=(
                "the base population is declared and its expectancy is a kill rule, so a "
                "filter cannot manufacture a curve by selecting inside a negative base"
            ),
            expected_information_gain=(
                "whether selection has anything to select from — which H-002 never "
                "established because it never measured its base"
            ),
        ),
        _design(
            candidate_id="M05_holding_period_selection",
            hypothesis=(
                "the horizon at which a signal is worth holding varies with state, and "
                "choosing it is worth more than fixing it"
            ),
            role=ModelRole.HORIZON_SELECTION,
            target="which of three horizons maximises cost-adjusted expected return",
            target_is_cost_adjusted=True,
            horizon="selected from {1d, 3d, 1w}",
            holding_days=3.0,
            candidate_horizons=("1d", "3d", "1w"),
            feature_families=("volatility", "multi_horizon_structure", "execution_cost_state"),
            model_class="linear",
            model_settings={"coefficients": 3, "effective_fraction": 0.5},
            nominal_configurations=1,
            turnover_per_year=104.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            prior_research_overlap=(
                "the decision forbids re-testing the 4-6 day reversal family; this selects "
                "a horizon for a different signal rather than re-running that one"
            ),
            why_different_from_round_1=(
                "Round 1 swept horizons and reported the best. This learns the choice "
                "inside the fold and pays for it in the same budget as everything else"
            ),
            expected_information_gain="whether horizon is a state-dependent decision at all",
        ),
        _design(
            candidate_id="M06_volatility_scaled_portfolio_allocation",
            hypothesis=(
                "scaling exposure to conditional volatility raises the information ratio "
                "of an existing signal without touching its direction"
            ),
            role=ModelRole.PORTFOLIO_ALLOCATION,
            target="portfolio-level expected utility at a volatility target",
            target_is_cost_adjusted=True,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("volatility", "correlation", "dispersion"),
            model_class="linear",
            model_settings={"coefficients": 2, "effective_fraction": 0.5},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            parent_candidate="M01_currency_cross_sectional_ranking",
            prior_research_overlap="no closed family; allocation was never separated before",
            why_different_from_round_1=(
                "Round 1 had no portfolio layer at all; every result was a per-pair sum"
            ),
            expected_information_gain="whether the allocation layer is worth its own turnover",
        ),
        _design(
            candidate_id="M07_event_proximity_conditional_return",
            hypothesis=(
                "proximity to a forward-known central-bank decision changes the "
                "conditional mean, not only the conditional variance"
            ),
            role=ModelRole.DIRECTION_OR_RETURN,
            target="cost-adjusted relative return conditioned on event proximity",
            target_is_cost_adjusted=True,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("event_context", "volatility", "currency_factor_state"),
            model_class="linear",
            model_settings={"coefficients": 3, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=52.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=4,
            effective_units=3.0,
            prior_research_overlap=(
                "H-019 is OPEN: a forward-known opportunity anchor with nothing to point "
                "it at. This points a model at it"
            ),
            why_different_from_round_1="Round 1 had no exogenous calendar at all",
            expected_information_gain=(
                "whether the movement structure H-019 established carries any direction"
            ),
        ),
        _design(
            candidate_id="M08_cross_asset_context_conditional_return",
            hypothesis=(
                "free cross-asset state — yields, equity, volatility indices, commodities "
                "— conditions the FX conditional mean"
            ),
            role=ModelRole.DIRECTION_OR_RETURN,
            target="cost-adjusted weekly relative return under cross-asset state",
            target_is_cost_adjusted=True,
            horizon="1 week",
            holding_days=7.0,
            feature_families=("cross_asset_context", "currency_factor_state", "volatility"),
            model_class="linear",
            model_settings={"coefficients": 5, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=52.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            prior_research_overlap="no closed family uses cross-asset state",
            why_different_from_round_1="an information source Round 1 never had",
            expected_information_gain="whether FX conditional means are readable from outside FX",
        ),
        _design(
            candidate_id="M09_dispersion_and_correlation_state_representation",
            hypothesis=(
                "a learned dispersion-and-correlation state improves a cross-sectional "
                "ranking that does not see it"
            ),
            role=ModelRole.REGIME_REPRESENTATION,
            target="a low-dimensional state, judged only by what it does downstream",
            target_is_cost_adjusted=False,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("dispersion", "correlation", "volatility"),
            model_class="linear",
            model_settings={"coefficients": 2, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            downstream_consumer="M01_currency_cross_sectional_ranking",
            consumer_annual_ir=1.448,
            consumer_effective_parameters=4.2,
            ablation="the consumer refitted with and without the state, same folds",
            prior_research_overlap="no closed family; H-015 keeps volume as a volatility feature",
            why_different_from_round_1="Round 1 fitted no representation",
            expected_information_gain="whether a state is worth its share of one capacity budget",
        ),
        _design(
            candidate_id="M10_hidden_markov_per_regime_mapping",
            hypothesis="the mapping from features to return differs by latent regime",
            role=ModelRole.REGIME_REPRESENTATION,
            target="a latent state plus a separate coefficient vector per state",
            target_is_cost_adjusted=False,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("regime_state", "volatility", "multi_horizon_structure"),
            model_class="regime_linear",
            model_settings={"states": 3, "coefficients": 3},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            downstream_consumer="M01_currency_cross_sectional_ranking",
            consumer_annual_ir=1.448,
            consumer_effective_parameters=4.2,
            ablation="the consumer refitted with a single regime, same folds",
            prior_research_overlap="no closed family fitted a latent state",
            why_different_from_round_1="a latent-state architecture Round 1 never tried",
            expected_information_gain=(
                "included to show what a full per-regime mapping costs, which is the "
                "architecture most people reach for first"
            ),
        ),
        _design(
            candidate_id="M11_factor_representation_of_the_cross_section",
            hypothesis=(
                "a small set of learned factors summarises the currency cross-section "
                "better than the hand-made dollar and risk proxies"
            ),
            role=ModelRole.REGIME_REPRESENTATION,
            target="a factor basis, judged by what the residual model does with it",
            target_is_cost_adjusted=False,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("currency_factor_state", "correlation"),
            model_class="linear",
            model_settings={"coefficients": 3, "effective_fraction": 0.5},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=PAIR_ROUNDTRIP_BP,
            cross_sectional_units=len(PAIRS_20),
            effective_units=EFFECTIVE_PAIRS,
            downstream_consumer="M02_residual_factor_adjusted_return",
            consumer_annual_ir=1.188,
            consumer_effective_parameters=3.0,
            ablation="the residual model refitted on hand-made factors, same folds",
            prior_research_overlap="no closed family learned a factor basis",
            why_different_from_round_1="Round 1 used raw pairs and no factor structure",
            expected_information_gain="whether learned factors beat declared ones at equal cost",
        ),
        _design(
            candidate_id="M12_excursion_conditional_exit_design",
            hypothesis=(
                "the conditional distribution of favourable and adverse excursion tells "
                "an exit rule what it costs to hold"
            ),
            role=ModelRole.EXECUTION_MANAGEMENT,
            target="conditional expectation of maximum favourable and adverse excursion",
            target_is_cost_adjusted=False,
            measures_cost_not_edge=True,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("volatility", "execution_cost_state", "price_state"),
            model_class="linear",
            model_settings={"coefficients": 4, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=PAIR_ROUNDTRIP_BP,
            cross_sectional_units=len(PAIRS_20),
            effective_units=EFFECTIVE_PAIRS,
            prior_research_overlap=(
                "H-013 and H-014 closed retrace geometry as an edge; this measures the "
                "cost of holding rather than claiming a direction, and H-014 explicitly "
                "does not bound barrier exits"
            ),
            why_different_from_round_1="Round 1 had no exit model; every trade ran to window end",
            expected_information_gain="what an exit rule can know in advance about its own cost",
        ),
        _design(
            candidate_id="M13_hurdle_clearing_probability_with_learned_threshold",
            hypothesis=(
                "the probability that a leg clears its round trip is calibratable, and a "
                "threshold learned in-fold beats trading everything"
            ),
            role=ModelRole.TRADE_SKIP,
            target="P(|return| > round trip) per currency leg, with an in-fold threshold",
            target_is_cost_adjusted=True,
            horizon="1 day",
            holding_days=1.0,
            feature_families=(
                "volatility",
                "event_context",
                "execution_cost_state",
                "activity_state",
            ),
            model_class="linear",
            model_settings={"coefficients": 6, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            base_opportunity="every daily currency leg whose parent signal is non-zero",
            base_expectancy_is_a_kill_rule=True,
            prior_research_overlap=(
                "H-018 and H-019 both found that ordinary days already clear the round "
                "trip 91% of the time, so magnitude was never the binding constraint"
            ),
            why_different_from_round_1=(
                "Round 1's classifier predicted direction. This predicts whether the move "
                "is large enough to pay for itself, which H-018 showed is a different and "
                "much better-behaved quantity — and says so about its own limits"
            ),
            expected_information_gain=(
                "whether a calibrated hurdle probability is worth anything once 91% of "
                "days already clear"
            ),
        ),
        _design(
            candidate_id="M14_intraday_session_state_return",
            hypothesis="session and liquidity state carry an intraday conditional mean",
            role=ModelRole.DIRECTION_OR_RETURN,
            target="cost-adjusted return over the next session",
            target_is_cost_adjusted=True,
            horizon="8 hours",
            holding_days=0.333,
            feature_families=("price_state", "volatility", "activity_state"),
            model_class="linear",
            model_settings={"coefficients": 4, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=756.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            prior_research_overlap="H-002 found the session edge was first-half only",
            why_different_from_round_1="a shorter horizon and a portfolio target",
            expected_information_gain=(
                "included to show where turnover puts the hurdle out of reach"
            ),
        ),
        _design(
            candidate_id="M15_structural_break_state",
            hypothesis="a detected structural break marks where a fitted mapping stops applying",
            role=ModelRole.REGIME_REPRESENTATION,
            target="a break indicator, judged by what it does to the consumer",
            target_is_cost_adjusted=False,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("regime_state", "volatility", "correlation"),
            model_class="linear",
            model_settings={"coefficients": 2, "effective_fraction": 0.5},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            downstream_consumer="M03_regime_conditioned_level_multi_timeframe",
            consumer_annual_ir=1.448,
            consumer_effective_parameters=4.4,
            ablation="the consumer refitted ignoring breaks, same folds",
            prior_research_overlap="no closed family detected breaks",
            why_different_from_round_1="Round 1 assumed one stationary mapping throughout",
            expected_information_gain="whether break detection pays for its share of the budget",
        ),
        _design(
            candidate_id="M16_activity_state_opportunity_gate",
            hypothesis=(
                "tick-volume activity state says when an opportunity population is worth "
                "acting on, through volatility rather than through direction"
            ),
            role=ModelRole.TRADE_SKIP,
            target="whether the activity state raises the cost-adjusted expectancy of a leg",
            target_is_cost_adjusted=True,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("activity_state", "volatility", "execution_cost_state"),
            model_class="linear",
            model_settings={"coefficients": 3, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            base_opportunity="every daily currency leg of the ranking book",
            base_expectancy_is_a_kill_rule=True,
            prior_research_overlap=(
                "H-015 is OPEN and keeps tick volume as a VOLATILITY feature: its "
                "correlation with the next bar's signed return is -0.0014 and +0.0013. "
                "H-017 found volume filtering made a carry base worse in 15 of 15 cells"
            ),
            why_different_from_round_1="Round 1 had no volume data",
            expected_information_gain=(
                "whether the one OPEN volume finding survives contact with a cost hurdle, "
                "given that H-017 says filtering by it removed more days than it saved"
            ),
        ),
        _design(
            candidate_id="M17_rate_differential_conditional_residual",
            hypothesis="the policy-rate differential conditions the residual, not the carry",
            role=ModelRole.DIRECTION_OR_RETURN,
            target="cost-adjusted monthly relative return under a rate-differential state",
            target_is_cost_adjusted=True,
            horizon="1 month",
            holding_days=30.0,
            feature_families=("currency_factor_state", "cross_asset_context"),
            model_class="linear",
            model_settings={"coefficients": 3, "effective_fraction": 0.6},
            nominal_configurations=1,
            turnover_per_year=12.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            gate_family="carry",
            prior_research_overlap=(
                "H-016 closed the carry family: over these panels the G10 carry premium "
                "IS the short-yen trade, 63x to 95x concentrated"
            ),
            why_different_from_round_1="not the issue — the issue is that the family is closed",
            expected_information_gain=(
                "included so that the refusal is visible rather than the candidate absent"
            ),
        ),
        _design(
            candidate_id="M18_boosted_tree_cross_sectional_ranking",
            hypothesis=(
                "a gradient-boosted ranker finds cross-sectional structure a linear one cannot"
            ),
            role=ModelRole.RANKING,
            target="cost-adjusted next-day relative return of a currency against the basket",
            target_is_cost_adjusted=True,
            horizon="1 day",
            holding_days=1.0,
            feature_families=("currency_factor_state", "multi_horizon_structure", "volatility"),
            model_class="boosted_trees",
            model_settings={"trees": 300, "leaves": 8, "learning_rate": 0.03},
            nominal_configurations=1,
            turnover_per_year=252.0,
            roundtrip_cost_bp=BASKET_ROUNDTRIP_BP,
            cross_sectional_units=len(CURRENCIES_G10),
            effective_units=EFFECTIVE_CURRENCIES,
            rank_stability_metric="fold-to-fold Spearman of the ranking",
            prior_research_overlap="H-004 closed a boosted direction model on ~50 features",
            why_different_from_round_1=(
                "a different target and cross-section — which is not enough, and the "
                "capacity budget is why"
            ),
            expected_information_gain=(
                "included deliberately: this is the architecture the phase would reach "
                "for by default, and the budget says by how much it misses"
            ),
        ),
    ]


def _sample_record(design: role_gate.ModelDesign) -> dict[str, Any]:
    entries = min(252.0, sample_module.CALENDAR_DAYS_PER_YEAR / max(design.holding_days, 1e-9))
    if design.horizon.startswith("8 hours"):
        entries = 756.0
    plan = sample_module.SampleDesign(
        entries_per_year_per_unit=entries,
        holding_days=design.holding_days,
        cross_sectional_units=design.cross_sectional_units,
        effective_units=design.effective_units,
        event_conditioned="event_context" in design.feature_families,
    )
    chain = sample_module.decompose(plan)
    return {
        "effective_observations_total": chain["effective_total"],
        "effective_observations_per_year": chain["effective_per_year"],
        "nominal_rows_per_year": chain["nominal_rows_per_year"],
        "sensitivity": sample_module.sensitivity(plan),
    }


def assess_all() -> list[dict[str, Any]]:
    records = []
    for design in catalogue():
        record = role_gate.assess(design)
        record["effective_sample"] = _sample_record(design)
        record["turnover_per_year"] = design.turnover_per_year
        record["roundtrip_cost_bp"] = design.roundtrip_cost_bp
        records.append(record)
    return records


# --------------------------------------------------------------- phase budget
def phase_budget(
    *,
    validation_years: float = VALIDATION_YEARS,
    minimum_relevant_incremental_ir: float = budget_module.MINIMUM_RELEVANT_INCREMENTAL_IR,
) -> dict[str, Any]:
    """⭐ The search budget applied to the phase, not to one track.

    Three tracks chosen on the same out-of-fold years are three selections on one
    sample. Tracks are treated as uncorrelated with each other — they are chosen
    to be orthogonal — and configurations inside a track carry the usual
    within-family correlation, so the phase's effective count is the **sum** of
    the per-track effective counts.
    """
    ceiling = minimum_relevant_incremental_ir * math.sqrt(validation_years)
    shapes = []
    for tracks in (1, 2, 3, 4):
        for configs in (1, 2, 3, 4, 5, 6, 7, 8, 10, 12):
            per_track = budget_module.effective_configurations(configs)
            total = tracks * per_track
            inflation = budget_module.expected_max_of_standard_normals(total) / math.sqrt(
                validation_years
            )
            shapes.append(
                {
                    "tracks": tracks,
                    "configurations_per_track": configs,
                    "phase_effective_configurations": round(total, 3),
                    "selection_inflation_annual_ir": round(inflation, 4),
                    "affordable": bool(inflation <= minimum_relevant_incremental_ir),
                }
            )
    affordable = [s for s in shapes if s["affordable"]]
    widest = max(
        affordable,
        key=lambda s: (s["tracks"], s["configurations_per_track"]),
        default=None,
    )
    return {
        "validation_years": validation_years,
        "minimum_relevant_incremental_ir": minimum_relevant_incremental_ir,
        "z_ceiling": round(ceiling, 4),
        "shapes": shapes,
        "affordable_shapes": affordable,
        "most_tracks_affordable": max((s["tracks"] for s in affordable), default=0),
        "widest_affordable_shape": widest,
        #: The model hierarchy's third level is not a search question. Whatever
        #: the validation said, a usable tree ensemble exceeds the capacity budget
        #: by more than an order of magnitude, so the ladder stops at Level 1 and
        #: the configurations that would have gone to Level 2 do not exist.
        "level_2_is_ruled_out_on_capacity_not_on_search": True,
    }


# ------------------------------------------------------------------- ranking
#: A candidate that spends almost none of its admissible capacity is asking a
#: smaller question than the data can answer; one that spends almost all of it is
#: relying on an effective-parameter estimate that has error in it. Both ends are
#: excluded, and the band is declared here rather than chosen after the fact.
CAPACITY_UTILISATION_BAND: Final[tuple[float, float]] = (0.50, 0.95)

MAX_TRACKS: Final[int] = 3


def rank() -> list[dict[str, Any]]:
    """Order the admissible candidates by **declared structural criteria only**.

    Not one criterion is a realised or anticipated quantity. A previous phase
    ranked three candidates on how clean their mechanism sounded, and a review
    deleted the section because none of its criteria existed in the artifact; the
    fix is that every criterion below is a field a reader can check.

    In order: self-contained before dependent, capacity utilisation inside the
    declared band, then the number of distinct feature families — the breadth of
    the question, not the size of the hoped-for answer.
    """
    rows = []
    for record in assess_all():
        if record["verdict"] != role_gate.Verdict.DEVELOPMENT_ADMISSIBLE.value:
            continue
        capacity = record["budgets"]["capacity"]
        admissible = capacity["admissible_effective_parameters"]
        utilisation = capacity["declared_effective_parameters"] / max(admissible, 1e-9)
        design = next(d for d in catalogue() if d.candidate_id == record["candidate_id"])
        self_contained = design.parent_candidate is None and design.downstream_consumer is None
        in_band = CAPACITY_UTILISATION_BAND[0] <= utilisation <= CAPACITY_UTILISATION_BAND[1]
        rows.append(
            {
                "candidate_id": record["candidate_id"],
                "role": record["role"],
                "self_contained": self_contained,
                "capacity_utilisation": round(utilisation, 4),
                "utilisation_in_band": in_band,
                "distinct_feature_families": len(set(design.feature_families)),
                "feature_families": sorted(set(design.feature_families)),
            }
        )
    rows.sort(
        key=lambda row: (
            not row["self_contained"],
            not row["utilisation_in_band"],
            -row["distinct_feature_families"],
            row["candidate_id"],
        )
    )
    for position, row in enumerate(rows, start=1):
        row["rank"] = position
    return rows


def selected_tracks(max_tracks: int = MAX_TRACKS) -> dict[str, Any]:
    """The highest-ranked candidates with **distinct roles**, up to the phase budget.

    The role constraint is what makes the set orthogonal rather than three views
    of one idea, and the phase budget is what caps the count: three tracks are
    affordable only at one fitted configuration each.
    """
    ranked = rank()
    budget = phase_budget()
    affordable_tracks = min(max_tracks, budget["most_tracks_affordable"])
    chosen: list[dict[str, Any]] = []
    roles_taken: set[str] = set()
    for row in ranked:
        if len(chosen) >= affordable_tracks:
            break
        if row["role"] in roles_taken:
            continue
        roles_taken.add(row["role"])
        chosen.append(row)
    configurations = max(
        (
            shape["configurations_per_track"]
            for shape in budget["affordable_shapes"]
            if shape["tracks"] == len(chosen)
        ),
        default=0,
    )
    return {
        "ranked": ranked,
        "affordable_tracks": affordable_tracks,
        "selected": chosen,
        "configurations_per_track": configurations,
        "roles": sorted(roles_taken),
        "model_hierarchy_stops_at": "Level 1",
        "why_level_2_is_not_run": (
            "the capacity budget, not the search budget: a usable gradient-boosted "
            "ensemble carries about 72 effective parameters against 4.9 admissible, so "
            "no validation result could justify adopting one"
        ),
    }


def build() -> dict[str, Any]:
    assessed = assess_all()
    by_verdict: dict[str, list[str]] = {}
    for record in assessed:
        by_verdict.setdefault(record["verdict"], []).append(record["candidate_id"])
    admissible = by_verdict.get(role_gate.Verdict.DEVELOPMENT_ADMISSIBLE.value, [])
    return {
        "status": "MODEL_LEARNING_DESIGN_ASSESSED",
        "train_years": TRAIN_YEARS_TOTAL,
        "initial_train_years": INITIAL_TRAIN_YEARS,
        "validation_years": VALIDATION_YEARS,
        "n_candidates": len(assessed),
        "candidates": assessed,
        "by_verdict": {name: sorted(ids) for name, ids in sorted(by_verdict.items())},
        "n_development_admissible": len(admissible),
        "capacity_budget_table": budget_module.budget_table(),
        "hurdle_table_basket": role_gate.hurdle_table(BASKET_ROUNDTRIP_BP),
        "hurdle_table_pair": role_gate.hurdle_table(PAIR_ROUNDTRIP_BP),
        "bars_are_not_a_sample": sample_module.bars_are_not_a_sample(),
        "phase_budget": phase_budget(),
        "ranking_and_selection": selected_tracks(),
        "prior_screening_configurations_approx": (
            budget_module.PRIOR_SCREENING_CONFIGURATIONS_APPROX
        ),
        "signal_free": True,
    }


__all__ = [
    "EFFECTIVE_CURRENCIES",
    "EFFECTIVE_PAIRS",
    "INITIAL_TRAIN_YEARS",
    "VALIDATION_YEARS",
    "CAPACITY_UTILISATION_BAND",
    "MAX_TRACKS",
    "assess_all",
    "build",
    "catalogue",
    "phase_budget",
    "rank",
    "selected_tracks",
]
