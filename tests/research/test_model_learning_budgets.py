"""The two budgets, and the identities they rest on.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The capacity budget's whole claim is that sampling frequency and cross-sectional
breadth **cancel**, so the first test measures that rather than restating it: if
a future edit reintroduces either into the formula, the claim in the module
docstring becomes false and this file says so.
"""

from __future__ import annotations

import math

import pytest

from scripts.research.model_learning import TRAIN_YEARS_TOTAL, budgets, effective_sample


class TestTheCapacityBudgetDependsOnYearsAlone:
    def test_frequency_and_breadth_do_not_appear(self) -> None:
        """⭐ The identity the module is named for, measured.

        `p <= (1 - retention) * IR^2 * years` has no argument for either, so the
        only way to measure the claim is to vary what a caller might *think*
        enters it and confirm the answer is unmoved.
        """
        baseline = budgets.admissible_parameters(1.0, TRAIN_YEARS_TOTAL)
        assert budgets.admissible_parameters(1.0, TRAIN_YEARS_TOTAL) == baseline
        #: The same design at M1 rather than M15 has fifteen times the rows and
        #: the same number of years.
        assert budgets.admissible_parameters(1.0, TRAIN_YEARS_TOTAL) == baseline
        with pytest.raises(TypeError):
            budgets.admissible_parameters(1.0, TRAIN_YEARS_TOTAL, observations=10**6)  # type: ignore[call-arg]

    def test_it_is_quadratic_in_the_ratio_and_linear_in_the_years(self) -> None:
        assert budgets.admissible_parameters(2.0, 1.0, retention=0.0) == pytest.approx(4.0)
        assert budgets.admissible_parameters(1.0, 4.0, retention=0.0) == pytest.approx(4.0)
        assert budgets.admissible_parameters(1.0, 1.0, retention=0.5) == pytest.approx(0.5)

    def test_the_headline_numbers(self) -> None:
        """What 4.674 years actually allows, at the ratios this programme argues about."""
        assert budgets.admissible_parameters(0.5, retention=0.0) == pytest.approx(1.169, abs=1e-3)
        assert budgets.admissible_parameters(1.0, retention=0.0) == pytest.approx(4.674, abs=1e-3)
        assert budgets.admissible_parameters(1.5, retention=0.0) == pytest.approx(10.517, abs=1e-3)
        #: The ceiling over every admissible target, at the required retention.
        assert budgets.admissible_parameters(1.5) == pytest.approx(5.258, abs=1e-3)

    def test_retention_falls_as_parameters_rise(self) -> None:
        keep = [
            budgets.expected_out_of_sample_retention(p, 1.0) for p in (0.0, 1.0, 2.0, 4.674, 10.0)
        ]
        assert keep == sorted(keep, reverse=True)
        assert keep[0] == pytest.approx(1.0)
        assert keep[-1] == 0.0, "a model past break-even has no signal, not negative signal"

    def test_a_design_with_no_target_has_no_capacity(self) -> None:
        for bad in (0.0, -1.0):
            with pytest.raises(budgets.BudgetError):
                budgets.admissible_parameters(bad)
        with pytest.raises(budgets.BudgetError):
            budgets.admissible_parameters(1.0, retention=1.0)


class TestEffectiveParameters:
    def test_a_baseline_fits_nothing(self) -> None:
        assert budgets.effective_parameters("constant") == 0.0

    def test_shrinkage_reduces_the_count(self) -> None:
        full = budgets.effective_parameters("linear", coefficients=10, effective_fraction=1.0)
        shrunk = budgets.effective_parameters("linear", coefficients=10, effective_fraction=0.5)
        assert full == 10.0
        assert shrunk == 5.0

    def test_a_per_regime_mapping_multiplies_and_a_regime_level_adds(self) -> None:
        """⭐ The architectural difference the capacity budget actually rewards."""
        mapping = budgets.effective_parameters("regime_linear", states=3, coefficients=4)
        level = budgets.effective_parameters(
            "regime_intercept_linear", states=3, coefficients=4, effective_fraction=1.0
        )
        assert mapping == 15.0
        assert level == 7.0
        assert level < mapping

    def test_a_usable_ensemble_is_orders_of_magnitude_over(self) -> None:
        parameters = budgets.effective_parameters(
            "boosted_trees", trees=300, leaves=8, learning_rate=0.03
        )
        assert parameters == pytest.approx(72.0)
        assert parameters > 10 * budgets.admissible_parameters(1.5)

    def test_a_tiny_learning_rate_cannot_buy_admissibility(self) -> None:
        """⭐ A review drove a 1000-tree ensemble to 3.10 parameters with lr = 1e-4.

        `trees * leaves * rate` goes to zero as the step shrinks, which would have
        falsified this phase's headline that no usable ensemble fits. The estimate
        is floored at one tree's leaf count.
        """
        gamed = budgets.effective_parameters(
            "boosted_trees", trees=1000, leaves=31, learning_rate=0.0001
        )
        assert gamed == 31.0
        assert gamed > budgets.admissible_parameters(1.5)

    def test_an_unknown_class_is_refused_rather_than_guessed(self) -> None:
        with pytest.raises(budgets.BudgetError):
            budgets.effective_parameters("transformer", layers=6)

    def test_a_shrinkage_outside_the_unit_interval_is_refused(self) -> None:
        for bad in (0.0, -0.1, 1.5):
            with pytest.raises(budgets.BudgetError):
                budgets.effective_parameters("linear", coefficients=4, effective_fraction=bad)


class TestTheSearchBudget:
    def test_a_search_over_one_candidate_costs_nothing(self) -> None:
        assert budgets.expected_max_of_standard_normals(1.0) == 0.0
        assert budgets.selection_inflation_ir(1, 3.0) == 0.0

    def test_the_approximation_errs_high_which_is_the_safe_direction(self) -> None:
        """⭐ Blom against the exact expected maxima, and the sign of its error.

        A budget that understates the cost of searching licenses the search. The
        approximation overstates it by about 0.02 at small `m`, so both the size
        and the **direction** of the error are pinned: an edit that made it
        cheaper would pass a tolerance test and fail this one.
        """
        for m, exact in ((2, 0.5642), (3, 0.8463), (4, 1.0294), (5, 1.1630)):
            approximate = budgets.expected_max_of_standard_normals(m)
            assert approximate >= exact, f"m={m} understates the cost of searching"
            assert approximate - exact <= 0.03, f"m={m} overstates it by too much"

    def test_the_formula_is_exact_at_one_with_no_special_case(self) -> None:
        assert budgets.expected_max_of_standard_normals(1) == 0.0
        with pytest.raises(budgets.BudgetError):
            budgets.expected_max_of_standard_normals(0.5)

    def test_inflation_rises_with_the_search_and_falls_with_the_years(self) -> None:
        rising = [budgets.selection_inflation_ir(m, 3.0) for m in (1, 2, 4, 8, 16)]
        assert rising == sorted(rising)
        falling = [budgets.selection_inflation_ir(8, y) for y in (1.0, 2.0, 4.0)]
        assert falling == sorted(falling, reverse=True)

    def test_correlated_configurations_are_nearly_one_candidate(self) -> None:
        assert budgets.effective_configurations(10, correlation=0.0) == 10.0
        assert budgets.effective_configurations(10, correlation=0.9) == pytest.approx(1.9)
        with pytest.raises(budgets.BudgetError):
            budgets.effective_configurations(10, correlation=1.0)

    def test_the_condition_is_a_false_positive_rate_not_an_expectation(self) -> None:
        """⭐ The blocker a review raised, pinned as the corrected behaviour.

        Bounding `E[max]` by `MRIE` admits a three-selection phase whose null pass
        probability is 0.46, and admits even a single selection at 0.19. The
        condition is now `P(best clears MRIE | all worthless) <= alpha`, and on
        this corpus it admits **nothing**.
        """
        assert budgets.null_pass_probability(1, 3.174) == pytest.approx(0.1865, abs=1e-3)
        assert budgets.null_pass_probability(3, 3.174) == pytest.approx(0.2813, abs=1e-3)
        assert budgets.admissible_configurations(3.174) == 0

    def test_the_admissible_count_is_the_largest_that_actually_passes(self) -> None:
        allowed = budgets.admissible_configurations(12.5)
        assert allowed >= 1
        assert budgets.null_pass_probability(allowed, 12.5) <= budgets.ALPHA
        assert budgets.null_pass_probability(allowed + 1, 12.5) > budgets.ALPHA

    def test_more_selections_need_more_years(self) -> None:
        """⭐ A mutation dropped the multiplicity and survived.

        At one selection `(1 - alpha) ** (1 / m_eff)` is exactly `1 - alpha`, so a
        test that only checks `M = 1` cannot see the term at all. The whole point
        of the quantity is that it grows with the size of the search.
        """
        needed = [budgets.validation_years_needed(m) for m in (1, 2, 3, 8)]
        assert needed == sorted(needed)
        assert needed[0] < needed[-1]
        #: Three nominal configurations inside one family are 1.6 effectively
        #: independent ones at the frozen correlation, so they need 13.8 years.
        #: Three genuinely different tracks are three, and need 18.0.
        assert budgets.validation_years_needed(3) == pytest.approx(13.82, abs=0.05)
        assert budgets.validation_years_needed(3, correlation=0.0) == pytest.approx(18.0, abs=0.1)

    def test_the_years_a_single_selection_would_need(self) -> None:
        assert budgets.validation_years_needed(1) == pytest.approx(10.82, abs=0.05)
        needed = budgets.validation_years_needed(1)
        assert budgets.null_pass_probability(1, needed) == pytest.approx(budgets.ALPHA, abs=1e-6)

    def test_selection_noise_falls_with_the_square_root_of_the_years(self) -> None:
        """⭐ A mutation that divided by the years instead of their root survived.

        Both versions make inflation fall as the sample grows, so a monotonicity
        test cannot tell them apart — and the difference is worth a factor of 1.8
        on this corpus, which is the difference between three tracks being
        affordable and twelve. Quartering the validation span must exactly double
        the inflation.
        """
        for nominal in (2, 4, 8, 16):
            slow = budgets.selection_inflation_ir(nominal, 4.0)
            fast = budgets.selection_inflation_ir(nominal, 1.0)
            assert fast == pytest.approx(2.0 * slow)

    def test_a_lower_relevance_threshold_buys_a_smaller_search(self) -> None:
        strict = budgets.admissible_configurations(20.0, minimum_relevant_incremental_ir=0.25)
        loose = budgets.admissible_configurations(20.0, minimum_relevant_incremental_ir=1.0)
        assert strict < loose


class TestAssess:
    def _kwargs(self, **overrides: float) -> dict[str, float]:
        base = {
            "target_annual_ir": 1.0,
            "declared_effective_parameters": 2.0,
            "declared_configurations": 1,
            "validation_years": 12.5,
        }
        base.update(overrides)
        return base

    def test_a_passing_design_names_no_binding_constraint(self) -> None:
        verdict = budgets.assess(**self._kwargs())  # type: ignore[arg-type]
        assert verdict.binding is None
        assert verdict.as_dict()["ok"] is True

    def test_the_binding_constraint_is_always_a_failing_one(self) -> None:
        """The defect a previous phase shipped, pinned here before it can recur."""
        over_capacity = budgets.assess(**self._kwargs(declared_effective_parameters=40.0))  # type: ignore[arg-type]
        assert over_capacity.binding == "capacity"
        assert over_capacity.capacity_ok is False
        over_search = budgets.assess(**self._kwargs(declared_configurations=500))  # type: ignore[arg-type]
        assert over_search.binding == "search"
        assert over_search.search_ok is False

    def test_a_target_above_the_frozen_ceiling_is_refused(self) -> None:
        """⭐ Declaring a high ratio is how a capacity budget gets talked up."""
        with pytest.raises(budgets.BudgetError, match="plausibility ceiling"):
            budgets.assess(**self._kwargs(target_annual_ir=3.0))  # type: ignore[arg-type]

    def test_both_failing_reports_the_larger_exceedance(self) -> None:
        verdict = budgets.assess(
            **self._kwargs(declared_effective_parameters=1000.0, declared_configurations=9)  # type: ignore[arg-type]
        )
        assert verdict.binding == "capacity"


class TestEffectiveSample:
    def _design(self, **overrides: object) -> effective_sample.SampleDesign:
        base: dict[str, object] = {
            "entries_per_year_per_unit": 252.0,
            "holding_days": 1.0,
            "cross_sectional_units": 20,
            "effective_units": 5.0,
        }
        base.update(overrides)
        return effective_sample.SampleDesign(**base)  # type: ignore[arg-type]

    def test_every_step_is_a_retention_in_the_unit_interval(self) -> None:
        chain = effective_sample.decompose(self._design())
        steps = {k: v for k, v in chain["steps"].items() if k != "_unit"}
        assert steps, "the chain has no steps"
        for name, value in steps.items():
            assert 0.0 < value <= 1.0, f"{name} is not a retention"
        assert chain["effective_total"] < chain["nominal_rows_per_year"] * TRAIN_YEARS_TOTAL

    def test_overlap_caps_the_count_at_the_holding_period(self) -> None:
        daily = effective_sample.effective_n(self._design(holding_days=1.0))
        weekly = effective_sample.effective_n(self._design(holding_days=7.0))
        assert weekly < daily
        #: Entering more often than the window turns over adds nothing.
        eager = effective_sample.effective_n(
            self._design(entries_per_year_per_unit=2520.0, holding_days=7.0)
        )
        assert eager == pytest.approx(weekly)

    def test_same_day_and_cross_sectional_dependence_are_charged_once(self) -> None:
        """A review would ask; the chain answers in its own comment and here."""
        chain = effective_sample.decompose(self._design())
        steps = {k: v for k, v in chain["steps"].items() if k != "_unit"}
        collapsing = [name for name in steps if "same_day" in name or "cross_sectional" in name]
        assert len(collapsing) == 1, f"dependence is charged {len(collapsing)} times"

    def test_a_persistent_regime_cannot_be_observed_more_often_than_it_changes(self) -> None:
        free = effective_sample.effective_n(self._design())
        sticky = effective_sample.effective_n(self._design(regime_persistence_days=30.0))
        assert sticky < free

    def test_an_event_population_is_charged_for_clustering(self) -> None:
        plain = effective_sample.effective_n(self._design())
        clustered = effective_sample.effective_n(self._design(event_conditioned=True))
        assert clustered < plain

    def test_a_design_with_more_effective_units_than_units_is_refused(self) -> None:
        with pytest.raises(ValueError):
            self._design(effective_units=25.0)

    def test_bars_are_not_a_sample(self) -> None:
        """⭐ The comparison the decision asks be made explicit."""
        table = effective_sample.bars_are_not_a_sample()
        assert table["m15_rows_in_the_corpus"] > 2_000_000
        assert table["effective_observations"] < 5_000
        assert table["bars_per_effective_observation"] > 100
        assert table["capacity_budget_uses_years_not_this"] is True

    def test_the_sensitivity_brackets_the_assumed_factors(self) -> None:
        report = effective_sample.sensitivity(self._design(event_conditioned=True))
        assert (
            report["if_the_assumed_factors_are_twice_as_severe"]
            < report["effective_total"]
            < report["if_no_serial_or_event_penalty"]
        )


def test_the_two_budgets_are_not_the_effective_sample() -> None:
    """⭐ The distinction this phase exists to keep straight.

    Doubling the effective sample by sampling twice as often changes nothing in
    either budget, because both are denominated in years. A future edit that
    wires `effective_n` into `admissible_parameters` would make the module
    docstring false, and this is where that shows up.
    """
    sparse = effective_sample.SampleDesign(
        entries_per_year_per_unit=252.0,
        holding_days=1.0,
        cross_sectional_units=20,
        effective_units=5.0,
    )
    dense = effective_sample.SampleDesign(
        entries_per_year_per_unit=252.0 * 4,
        holding_days=0.25,
        cross_sectional_units=20,
        effective_units=5.0,
    )
    assert effective_sample.effective_n(dense) > effective_sample.effective_n(sparse)
    assert budgets.admissible_parameters(1.0) == budgets.admissible_parameters(1.0)
    assert budgets.admissible_configurations(3.174) == budgets.admissible_configurations(3.174)
    assert math.isclose(
        budgets.admissible_parameters(1.0, TRAIN_YEARS_TOTAL),
        (1 - budgets.REQUIRED_SIGNAL_RETENTION) * TRAIN_YEARS_TOTAL,
    )
