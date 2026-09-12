"""The role gate, the candidate universe, the ranking and the frozen prereg.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Three things this file exists to hold: that every role's prerequisite actually
refuses a design missing it, that the selection rule uses no quantity a market
could have produced, and that the pre-registration is frozen by a hash rather
than by a sentence saying it is frozen.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.research.model_learning import (
    PROTECTED_SPANS,
    SEEN_SPANS,
    TRAIN_YEARS_TOTAL,
    ModelRole,
    ProtectedDataError,
    assert_not_protected,
    prereg,
    role_gate,
    universe,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "scripts/research/model_learning"


@pytest.fixture(scope="module")
def record() -> dict[str, Any]:
    return universe.build()


def _catalogue_by_id() -> dict[str, role_gate.ModelDesign]:
    return {design.candidate_id: design for design in universe.catalogue()}


class TestTheSpansAndTheirProvenance:
    def test_the_three_seen_spans_are_contiguous(self) -> None:
        import datetime as dt

        ordered = sorted(SEEN_SPANS.values(), key=lambda block: block["start"])
        for earlier, later in zip(ordered, ordered[1:], strict=False):
            gap = dt.date.fromisoformat(later["start"]) - dt.date.fromisoformat(earlier["end"])
            assert gap == dt.timedelta(days=1), "the corpus is not contiguous"

    def test_every_span_carries_its_contamination_history(self) -> None:
        """The decision asks for it by name; a span without it is not usable here."""
        for name, block in SEEN_SPANS.items():
            for key in (
                "hypotheses_run_here",
                "prior_strategy_exposure",
                "prior_labels_or_features_used",
                "known_exploratory_reuse",
                "route",
            ):
                assert block.get(key), f"{name} has no {key}"
            assert block["hypotheses_run_here"], f"{name} claims no prior exposure"

    def test_the_recorded_hypotheses_exist_in_the_ledger(self) -> None:
        """⭐ Provenance that points at nothing is decoration.

        Every id in every span's history has to be a real entry in the hypothesis
        ledger, so the contamination record cannot drift into a list of plausible
        strings.
        """
        from scripts.research.round_a.ledger import LEDGER

        known = {entry["id"] for entry in LEDGER}
        for name, block in SEEN_SPANS.items():
            unknown = set(block["hypotheses_run_here"]) - known
            assert not unknown, f"{name} cites {sorted(unknown)}, which the ledger does not have"

    def test_the_corpus_length_matches_the_published_figure(self) -> None:
        assert pytest.approx(4.674, abs=1e-3) == TRAIN_YEARS_TOTAL

    def test_the_protected_boundary_refuses_both_ends(self) -> None:
        assert_not_protected("2021-04-26", "2025-12-28")
        with pytest.raises(ProtectedDataError, match="fresh pool"):
            assert_not_protected("2021-04-25", "2025-12-28")
        with pytest.raises(ProtectedDataError, match="OOS"):
            assert_not_protected("2021-04-26", "2025-12-29")

    def test_a_malformed_bound_is_refused_rather_than_compared(self) -> None:
        """The defect an audit found in three reader routes, closed here at the start."""
        for bad in ("2021-4-26", "2025-12-2", "2021", "", "yesterday"):
            with pytest.raises(ProtectedDataError):
                assert_not_protected(bad, "2025-12-28")
            with pytest.raises(ProtectedDataError):
                assert_not_protected("2021-04-26", bad)

    def test_the_fresh_pool_is_never_read_and_the_oos_claim_is_not_overstated(self) -> None:
        """⭐ A withdrawn claim must not reappear because a new file restated it.

        `HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN`: the R1 read decoded
        one row past each window and twenty of those rows are inside the OOS slice.
        A first version of this package wrote "never read" over that ruling and a
        test enforced it. The wording now matches the sibling inventory exactly.
        """
        from scripts.research.feasibility.inventory import PROTECTED_SPANS as INVENTORY

        assert PROTECTED_SPANS["fresh_pool"]["status"] == "never read"
        assert PROTECTED_SPANS["historical_oos"]["status"] != "never read"
        assert (
            PROTECTED_SPANS["historical_oos"]["status"]
            == INVENTORY["historical_oos_slice"]["status"]
        )

    def test_the_guard_takes_its_bounds_from_the_spans_it_protects(self) -> None:
        """⭐ One edit must not both relax the guard and preserve the frozen hash.

        The boundaries used to come from `SEEN_SPANS`, so moving the corpus start
        onto a fresh-pool day while keeping the span length left the hash untouched
        and the guard widened. They now come from `PROTECTED_SPANS`.
        """
        import scripts.research.model_learning as package

        source = Path(package.__file__).read_text(encoding="utf-8")
        guard = source.split("def assert_not_protected")[1]
        assert "PROTECTED_SPANS[" in guard
        assert "SEEN_SPANS[" not in guard


class TestTheRoleGateRefusesWhatItsRoleNeeds:
    def _base(self, **overrides: Any) -> role_gate.ModelDesign:
        design = _catalogue_by_id()["M01_currency_cross_sectional_ranking"]
        return dataclasses.replace(design, **overrides)

    def test_a_ranking_without_a_stability_metric_is_refused(self) -> None:
        verdict = role_gate.assess(self._base(rank_stability_metric=None))
        assert verdict["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value
        assert "stability" in verdict["reason"]

    def test_a_ranking_over_too_few_independent_units_is_refused(self) -> None:
        verdict = role_gate.assess(self._base(effective_units=2.0))
        assert verdict["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value

    def test_a_trade_skip_without_a_base_opportunity_is_refused(self) -> None:
        design = _catalogue_by_id()["M13_hurdle_clearing_probability_with_learned_threshold"]
        verdict = role_gate.assess(dataclasses.replace(design, base_opportunity=None))
        assert verdict["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value
        assert "base opportunity" in verdict["reason"]

    def test_a_trade_skip_whose_base_expectancy_is_not_a_kill_rule_is_refused(self) -> None:
        """⭐ Selecting inside a negative base is how a filter manufactures a curve."""
        design = _catalogue_by_id()["M13_hurdle_clearing_probability_with_learned_threshold"]
        verdict = role_gate.assess(
            dataclasses.replace(design, base_expectancy_is_a_kill_rule=False)
        )
        assert verdict["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value

    def test_a_representation_without_a_consumer_is_refused(self) -> None:
        design = _catalogue_by_id()["M09_dispersion_and_correlation_state_representation"]
        for field in ("downstream_consumer", "ablation"):
            verdict = role_gate.assess(dataclasses.replace(design, **{field: None}))
            assert verdict["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value

    def test_a_representation_is_charged_its_consumers_parameters_too(self) -> None:
        """⭐ Splitting a model in two must not buy it two capacity budgets."""
        design = _catalogue_by_id()["M09_dispersion_and_correlation_state_representation"]
        cheap = dataclasses.replace(
            design, turnover_per_year=12.0, consumer_annual_ir=1.5, validation_years=20.0
        )
        joint = role_gate.assess(cheap)
        assert joint["verdict"] == role_gate.Verdict.CAPACITY_EXCEEDED.value
        #: 1.2 of its own plus 4.2 of the consumer it is judged by.
        assert joint["budgets"]["capacity"]["declared_effective_parameters"] == pytest.approx(5.4)
        #: Declaring the consumer weightless is refused outright rather than
        #: quietly halving the charge.
        split = role_gate.assess(dataclasses.replace(cheap, consumer_effective_parameters=0.0))
        assert split["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value
        missing = role_gate.assess(dataclasses.replace(design, downstream_consumer=None))
        assert missing["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value

    def test_an_allocator_without_a_parent_is_refused(self) -> None:
        design = _catalogue_by_id()["M06_volatility_scaled_portfolio_allocation"]
        verdict = role_gate.assess(dataclasses.replace(design, parent_candidate=None))
        assert verdict["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value

    def test_a_return_generator_must_predict_a_cost_adjusted_quantity(self) -> None:
        design = _catalogue_by_id()["M02_residual_factor_adjusted_return"]
        verdict = role_gate.assess(dataclasses.replace(design, target_is_cost_adjusted=False))
        assert verdict["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value

    def test_a_horizon_selector_needs_something_to_select_between(self) -> None:
        design = _catalogue_by_id()["M05_holding_period_selection"]
        verdict = role_gate.assess(dataclasses.replace(design, candidate_horizons=("1d",)))
        assert verdict["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value

    def test_a_design_with_no_leakage_controls_is_refused(self) -> None:
        verdict = role_gate.assess(self._base(leakage_controls=()))
        assert verdict["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value


class TestTheGateRefusesForbiddenShapes:
    def _base(self, **overrides: Any) -> role_gate.ModelDesign:
        return dataclasses.replace(
            _catalogue_by_id()["M01_currency_cross_sectional_ranking"], **overrides
        )

    def test_a_random_split_is_refused_before_any_budget(self) -> None:
        verdict = role_gate.assess(self._base(training_architecture="random_kfold"))
        assert verdict["verdict"] == role_gate.Verdict.FORBIDDEN_REPEAT_OF_A_CLOSED_SHAPE.value
        assert "budgets" not in verdict

    def test_every_permitted_architecture_is_temporal(self) -> None:
        for name in role_gate.TEMPORAL_ARCHITECTURES:
            verdict = role_gate.assess(self._base(training_architecture=name))
            assert verdict["verdict"] != (
                role_gate.Verdict.FORBIDDEN_REPEAT_OF_A_CLOSED_SHAPE.value
            )

    def test_treating_the_cross_section_as_independent_is_refused(self) -> None:
        verdict = role_gate.assess(self._base(effective_units=8.0))
        assert verdict["verdict"] == role_gate.Verdict.FORBIDDEN_REPEAT_OF_A_CLOSED_SHAPE.value
        assert "H-003" in verdict["reason"]

    def test_the_round_1_shape_is_refused_by_name(self) -> None:
        verdict = role_gate.assess(
            self._base(
                target="next-bar direction",
                feature_families=("price_state", "technical_indicators", "volatility"),
                model_class="boosted_trees",
                model_settings={"trees": 500, "leaves": 31, "learning_rate": 0.05},
            )
        )
        assert verdict["verdict"] == role_gate.Verdict.FORBIDDEN_REPEAT_OF_A_CLOSED_SHAPE.value
        assert "H-004" in verdict["reason"]

    def test_a_closed_family_is_refused_by_code_not_by_a_typed_field(self) -> None:
        verdict = role_gate.assess(_catalogue_by_id()["M17_rate_differential_conditional_residual"])
        assert verdict["verdict"] == role_gate.Verdict.PRIOR_FAMILY_CLOSED.value
        assert verdict["refused_by"] == "assert_prospective"


class TestTheEconomicCondition:
    """The defect two independent reviews found from opposite directions."""

    def test_the_break_even_ratio_rises_with_turnover(self) -> None:
        table = role_gate.hurdle_table(3.406)["frequencies"]
        ratios = [block["break_even_annual_ir"] for block in table.values()]
        assert ratios == sorted(ratios)

    def test_making_a_design_cheaper_no_longer_shrinks_its_parameter_budget(self) -> None:
        """⭐ The Gate v1 pathology, reintroduced here and now removed.

        The previous version computed the capacity budget from the ratio a design
        **needed**, so halving its cost halved its admissible parameters — the
        exact inversion `scripts/research/feasibility` says Gate v2 exists to
        prevent, and a test in this very file used to assert it as a feature.
        Capacity now comes from the ratio the design claims it can **achieve** and
        does not move with cost at all.
        """
        table = role_gate.hurdle_table(3.406)["frequencies"]
        budgets_by_frequency = {
            name: block["admissible_effective_parameters"]
            for name, block in table.items()
            if block["reachable"]
        }
        assert len(set(budgets_by_frequency.values())) == 1, budgets_by_frequency

    def test_the_volatility_is_measured_rather_than_declared(self) -> None:
        """⭐ 800 bp was a declaration; the book measures 377.7 per unit of gross."""
        low, high = role_gate.MEASURED_VOL_RANGE_BY_SPAN_BP
        assert low <= role_gate.MEASURED_ANNUAL_VOL_PER_GROSS_BP <= high
        assert role_gate.MEASURED_ANNUAL_VOL_PER_GROSS_BP < 500.0

    def test_leverage_cancels_out_of_the_break_even_ratio(self) -> None:
        """An information ratio is scale-free, so the hurdle must be too."""
        design = _catalogue_by_id()["M01_currency_cross_sectional_ranking"]
        plain = role_gate.break_even_annual_ir(design)
        levered = role_gate.break_even_annual_ir(
            dataclasses.replace(
                design,
                turnover_per_year=design.turnover_per_year,
                annual_vol_per_gross_bp=design.annual_vol_per_gross_bp,
            )
        )
        assert plain == levered
        #: Doubling both the notional and the volatility leaves the ratio alone.
        doubled = role_gate.break_even_annual_ir(
            dataclasses.replace(
                design,
                roundtrip_cost_bp=design.roundtrip_cost_bp * 2,
                annual_vol_per_gross_bp=design.annual_vol_per_gross_bp * 2,
            )
        )
        assert doubled == pytest.approx(plain)

    def test_the_minimum_net_return_is_reported_as_a_leverage_statement(self) -> None:
        design = _catalogue_by_id()["M01_currency_cross_sectional_ranking"]
        record = role_gate.assess(dataclasses.replace(design, turnover_per_year=12.0))
        assert "leverage_for_the_minimum_net_return" in record["economics"]

    def test_daily_rebalancing_cannot_pay_for_itself(self) -> None:
        """⭐ The finding: at the measured volatility the daily hurdle is 2.27."""
        daily = role_gate.hurdle_table(3.406)["frequencies"]["daily"]
        assert daily["break_even_annual_ir"] == pytest.approx(2.272, abs=1e-3)
        assert daily["reachable"] is False
        verdict = role_gate.assess(_catalogue_by_id()["M01_currency_cross_sectional_ranking"])
        assert verdict["verdict"] == role_gate.Verdict.ECONOMICALLY_UNREACHABLE.value

    def test_capacity_is_charged_at_the_achievable_ratio_not_the_hurdle(self) -> None:
        """⭐ The Gate v1 inversion, pinned at the point where it would return.

        Every daily candidate now fails economics before capacity is computed, so
        a mutation that restored the hurdle as the capacity input survived: no
        catalogued design reached the line. This one does — it rebalances monthly,
        clears its hurdle easily, and its budget must not move when the hurdle does.
        """
        design = dataclasses.replace(
            _catalogue_by_id()["M01_currency_cross_sectional_ranking"],
            turnover_per_year=12.0,
            validation_years=20.0,
        )
        cheap = role_gate.assess(design)
        dearer = role_gate.assess(dataclasses.replace(design, turnover_per_year=40.0))
        assert (
            cheap["economics"]["break_even_annual_ir"]
            < (dearer["economics"]["break_even_annual_ir"])
        )
        assert (
            cheap["budgets"]["capacity"]["admissible_effective_parameters"]
            == dearer["budgets"]["capacity"]["admissible_effective_parameters"]
        )
        assert cheap["budgets"]["capacity"]["admissible_effective_parameters"] == pytest.approx(
            0.188, abs=1e-3
        )

    def test_an_achievable_ratio_above_the_ceiling_is_refused(self) -> None:
        """⭐ Declaring a ratio nobody has seen is how a capacity budget is talked up."""
        design = dataclasses.replace(
            _catalogue_by_id()["M01_currency_cross_sectional_ranking"],
            turnover_per_year=12.0,
            assumed_achievable_annual_ir=3.0,
        )
        verdict = role_gate.assess(design)
        assert verdict["verdict"] == role_gate.Verdict.ECONOMICALLY_UNREACHABLE.value
        assert "outside" in verdict["reason"]
        for bad in (0.0, -1.0):
            refused = role_gate.assess(
                dataclasses.replace(design, assumed_achievable_annual_ir=bad)
            )
            assert refused["verdict"] == role_gate.Verdict.ECONOMICALLY_UNREACHABLE.value

    def test_the_capacity_budget_is_charged_on_the_shortest_fold(self) -> None:
        """⭐ An expanding walk-forward fits its first model on 1.5 years."""
        design = dataclasses.replace(
            _catalogue_by_id()["M09_dispersion_and_correlation_state_representation"],
            turnover_per_year=12.0,
            consumer_annual_ir=1.5,
            validation_years=20.0,
        )
        short = role_gate.assess(design)
        long = role_gate.assess(dataclasses.replace(design, shortest_fold_train_years=4.674))
        assert (
            short["budgets"]["capacity"]["admissible_effective_parameters"]
            < long["budgets"]["capacity"]["admissible_effective_parameters"]
        )


class TestTheUniverse:
    def test_there_are_at_least_fifteen_directions(self, record: dict[str, Any]) -> None:
        assert record["n_candidates"] >= 15

    def test_every_candidate_id_is_distinct(self) -> None:
        ids = [design.candidate_id for design in universe.catalogue()]
        assert len(ids) == len(set(ids))

    def test_no_two_candidates_share_a_role_target_and_architecture(self) -> None:
        """The padding the decision forbids: a model name or a timeframe variant."""
        shapes = [
            (design.role.value, design.target, design.model_class)
            for design in universe.catalogue()
        ]
        assert len(shapes) == len(set(shapes))

    def test_every_candidate_says_why_it_differs_from_round_1(self) -> None:
        for design in universe.catalogue():
            assert design.why_different_from_round_1.strip()
            assert design.prior_research_overlap.strip()
            assert design.expected_information_gain.strip()

    def test_nothing_is_admissible_under_the_corrected_gate(self, record: dict[str, Any]) -> None:
        counts = {name: len(ids) for name, ids in record["by_verdict"].items()}
        assert role_gate.Verdict.DEVELOPMENT_ADMISSIBLE.value not in counts
        assert counts[role_gate.Verdict.ECONOMICALLY_UNREACHABLE.value] == 14
        assert counts[role_gate.Verdict.SEARCH_BUDGET_EXCEEDED.value] == 3
        assert counts[role_gate.Verdict.PRIOR_FAMILY_CLOSED.value] == 1
        assert sum(counts.values()) == record["n_candidates"] == 18
        assert record["status"] == ("MODEL_LEARNING_NOT_DECISION_GRADE_WITH_AVAILABLE_SEEN_DATA")

    def test_the_default_architecture_never_reaches_its_capacity_budget(self) -> None:
        """⭐ The control case, and why it now fails one condition earlier.

        The boosted ranker is refused on economics before capacity is computed: at
        daily turnover it cannot pay for its own trading. Its capacity figure is
        measured directly so the headline survives the reordering.
        """
        from scripts.research.model_learning import budgets as budget_module

        design = _catalogue_by_id()["M18_boosted_tree_cross_sectional_ranking"]
        assert role_gate.assess(design)["verdict"] == (
            role_gate.Verdict.ECONOMICALLY_UNREACHABLE.value
        )
        parameters = budget_module.effective_parameters(design.model_class, **design.model_settings)
        assert parameters == pytest.approx(72.0)
        assert parameters > 40 * budget_module.admissible_parameters(1.5, 1.5)

    def test_no_candidate_carries_a_realised_quantity(self, record: dict[str, Any]) -> None:
        blob = json.dumps(record, default=str).lower()
        for forbidden in ("sharpe", "p_value", "observed_", "realised_return", "pnl"):
            assert forbidden not in blob, forbidden
        assert record["signal_free"] is True

    def test_the_build_is_reproducible(self) -> None:
        first = json.dumps(universe.build(), sort_keys=True, default=str)
        second = json.dumps(universe.build(), sort_keys=True, default=str)
        assert first == second


class TestThePhaseBudget:
    def test_the_budget_is_charged_once_for_the_phase_not_once_per_track(self) -> None:
        """⭐ Three tracks on one sample are three selections on one sample."""
        budget = universe.phase_budget()
        one = next(
            s for s in budget["shapes"] if s["tracks"] == 1 and s["configurations_per_track"] == 4
        )
        three = next(
            s for s in budget["shapes"] if s["tracks"] == 3 and s["configurations_per_track"] == 4
        )
        assert three["phase_effective_configurations"] == pytest.approx(
            3 * one["phase_effective_configurations"]
        )
        assert three["null_pass_probability"] > one["null_pass_probability"]

    def test_no_shape_is_affordable_on_this_corpus(self) -> None:
        """⭐ The decisive result, once the condition became an error rate."""
        budget = universe.phase_budget()
        assert budget["affordable_shapes"] == []
        assert budget["most_tracks_affordable"] == 0
        smallest = next(
            s for s in budget["shapes"] if s["tracks"] == 1 and s["configurations_per_track"] == 1
        )
        assert smallest["null_pass_probability"] == pytest.approx(0.1865, abs=1e-3)
        assert smallest["validation_years_needed"] == pytest.approx(10.82, abs=0.05)

    def test_a_long_enough_sample_would_afford_something(self) -> None:
        """The condition is a wall, not an impossibility — it names its own price."""
        budget = universe.phase_budget(validation_years=12.0)
        assert budget["most_tracks_affordable"] >= 1

    def test_every_shape_marked_affordable_really_is(self) -> None:
        for years in (3.174, 12.0, 25.0):
            budget = universe.phase_budget(validation_years=years)
            for shape in budget["shapes"]:
                expected = shape["null_pass_probability"] <= budget["alpha"]
                assert shape["affordable"] is expected


class TestTheRankingUsesNoResult:
    def test_every_ranking_criterion_is_a_declared_structural_field(self) -> None:
        """The lesson from the phase before: a criterion not in the artifact is deleted."""
        for row in universe.rank():
            assert set(row) == {
                "candidate_id",
                "role",
                "self_contained",
                "capacity_utilisation",
                "utilisation_in_band",
                "distinct_feature_families",
                "feature_families",
                "rank",
            }

    def test_only_admissible_candidates_are_ranked(self) -> None:
        ranked = {row["candidate_id"] for row in universe.rank()}
        admissible = {
            row["candidate_id"]
            for row in universe.assess_all()
            if row["verdict"] == role_gate.Verdict.DEVELOPMENT_ADMISSIBLE.value
        }
        assert ranked == admissible

    def test_nothing_is_ranked_and_nothing_is_selected(self) -> None:
        """⭐ The corrected gate admits no candidate, so there is nothing to order."""
        assert universe.rank() == []
        selection = universe.selected_tracks()
        assert selection["selected"] == []
        assert selection["affordable_tracks"] == 0
        assert selection["configurations_per_track"] == 0

    def test_the_role_constraint_bites_when_the_ranking_would_repeat_a_role(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """⭐ The constraint that would have made three tracks orthogonal.

        Nothing is selected now, so the mechanism has to be exercised directly:
        feed it a ranking whose top entries share a role, and a phase budget that
        can afford three.
        """
        repeated = [
            {"candidate_id": "X1", "role": "cross_sectional_ranking", "rank": 1},
            {"candidate_id": "X2", "role": "cross_sectional_ranking", "rank": 2},
            {"candidate_id": "X3", "role": "trade_or_skip", "rank": 3},
            {"candidate_id": "X4", "role": "direction_or_return_generator", "rank": 4},
        ]
        monkeypatch.setattr(universe, "rank", lambda: repeated)
        monkeypatch.setattr(
            universe,
            "phase_budget",
            lambda **_: {
                "most_tracks_affordable": 3,
                "affordable_shapes": [
                    {"tracks": 3, "configurations_per_track": 1, "affordable": True}
                ],
            },
        )
        chosen = [row["candidate_id"] for row in universe.selected_tracks()["selected"]]
        assert chosen == ["X1", "X3", "X4"], "a repeated role was selected"

    def test_the_selection_stops_at_what_the_phase_can_afford(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """⭐ The cap that nothing currently exercises, because nothing is selected."""
        ranked = [
            {"candidate_id": "X1", "role": "cross_sectional_ranking", "rank": 1},
            {"candidate_id": "X2", "role": "trade_or_skip", "rank": 2},
            {"candidate_id": "X3", "role": "direction_or_return_generator", "rank": 3},
        ]
        monkeypatch.setattr(universe, "rank", lambda: ranked)
        monkeypatch.setattr(
            universe,
            "phase_budget",
            lambda **_: {
                "most_tracks_affordable": 2,
                "affordable_shapes": [
                    {"tracks": 2, "configurations_per_track": 2, "affordable": True}
                ],
            },
        )
        selection = universe.selected_tracks()
        assert [row["candidate_id"] for row in selection["selected"]] == ["X1", "X2"]
        assert selection["configurations_per_track"] == 2


class TestTheFrozenPreregistration:
    def test_the_hash_matches_what_was_recorded(self) -> None:
        assert prereg.assert_frozen() == prereg.FROZEN_HASH

    def test_moving_any_threshold_breaks_the_freeze(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """⭐ Frozen by a content hash, not by a sentence saying it is frozen."""
        moved = dict(prereg.SUCCESS_RULE)
        moved["positive_currencies_at_least"] = 1
        monkeypatch.setattr(prereg, "SUCCESS_RULE", moved)
        with pytest.raises(prereg.PreregistrationError, match="has changed"):
            prereg.assert_frozen()

    def test_moving_a_feature_list_breaks_the_freeze(self, monkeypatch: pytest.MonkeyPatch) -> None:
        tracks = tuple(dict(track) for track in prereg.TRACKS)
        tracks[0]["features"] = tracks[0]["features"] + ("a_feature_added_later",)
        monkeypatch.setattr(prereg, "TRACKS", tracks)
        with pytest.raises(prereg.PreregistrationError):
            prereg.assert_frozen()

    def test_it_registers_every_item_the_decision_names(self) -> None:
        spec = prereg.specification()
        for key in (
            "cv_architecture",
            "cost_model",
            "metrics",
            "success_rule",
            "kill_rule",
            "tracks",
            "maximum_research_budget",
            "multiple_testing_controls",
        ):
            assert spec[key], key
        for track in spec["tracks"]:
            for key in (
                "target",
                "horizon_days",
                "features",
                "model_class",
                "model_settings",
                "baseline",
                "configurations",
                "declared_effective_parameters",
            ):
                assert track[key] is not None, f"{track['candidate_id']} has no {key}"

    def test_the_registered_budget_is_no_longer_affordable(self) -> None:
        """⭐ The prereg is kept as the record of what ran, and it is marked.

        Three tracks at one configuration each were registered and executed under a
        search budget that bounded an expectation. Under the corrected
        false-positive condition that shape carries a 0.28 null pass rate against
        an alpha of 0.05, so the run it authorised is a record and not evidence.
        """
        budget = universe.phase_budget()
        shape = next(
            s for s in budget["shapes"] if s["tracks"] == 3 and s["configurations_per_track"] == 1
        )
        assert shape["affordable"] is False
        assert shape["null_pass_probability"] > budget["alpha"]
        assert prereg.MAXIMUM_RESEARCH_BUDGET["tracks"] == 3
        assert prereg.POST_REVIEW_STATUS["registered_shape_is_affordable"] is False

    def test_no_registered_track_survives_the_corrected_gate(self) -> None:
        """⭐ What the correction did to the three tracks that had been selected."""
        verdicts = {
            row["candidate_id"]: row["verdict"]
            for row in universe.assess_all()
            if row["candidate_id"] in {track["candidate_id"] for track in prereg.TRACKS}
        }
        assert len(verdicts) == 3
        assert all(
            verdict == role_gate.Verdict.ECONOMICALLY_UNREACHABLE.value
            for verdict in verdicts.values()
        ), verdicts

    def test_each_registered_feature_count_matches_its_declared_capacity(self) -> None:
        catalogue = _catalogue_by_id()
        for track in prereg.TRACKS:
            design = catalogue[track["candidate_id"]]
            assert len(track["features"]) == design.model_settings["coefficients"], (
                f"{track['candidate_id']} registers {len(track['features'])} features against "
                f"{design.model_settings['coefficients']} budgeted coefficients"
            )

    def test_the_cv_architecture_forbids_a_random_split(self) -> None:
        assert prereg.CV_ARCHITECTURE["random_splits_forbidden"] is True
        assert prereg.CV_ARCHITECTURE["validation_never_returns_to_training"] is True
        assert prereg.CV_ARCHITECTURE["scheme"] in role_gate.TEMPORAL_ARCHITECTURES


class TestNoSignalContamination:
    def test_no_module_in_the_package_can_open_a_market_data_file(self) -> None:
        for path in sorted(PACKAGE.glob("*.py")):
            if path.name == "driver.py":
                continue
            source = path.read_text(encoding="utf-8")
            for forbidden in ("read_parquet", "read_csv", "urlopen", "load_all", "open("):
                assert forbidden not in source, f"{path.name}: {forbidden}"

    def test_the_driver_only_writes_its_own_artifact(self) -> None:
        source = (PACKAGE / "driver.py").read_text(encoding="utf-8")
        for forbidden in ("read_parquet", "read_csv", "urlopen", "read_text"):
            assert forbidden not in source, forbidden
        assert 'ARTIFACTS: Final[Path] = Path("artifacts/research/model_learning")' in source

    def test_the_design_stage_declares_no_protected_read(self) -> None:
        for role in ModelRole:
            assert role.value
        assert universe.build()["signal_free"] is True
