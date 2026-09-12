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

    def test_the_fresh_pool_is_recorded_as_never_read(self) -> None:
        for name, block in PROTECTED_SPANS.items():
            assert block["status"] == "never read", name


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
        joint = role_gate.assess(design)
        alone = role_gate.assess(dataclasses.replace(design, consumer_effective_parameters=0.0))
        assert joint["verdict"] == role_gate.Verdict.CAPACITY_EXCEEDED.value
        assert alone["verdict"] == role_gate.Verdict.ROLE_PREREQUISITE_MISSING.value

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
    def test_the_required_ratio_rises_with_turnover(self) -> None:
        table = role_gate.hurdle_table(3.406)["frequencies"]
        ratios = [block["required_gross_annual_ir"] for block in table.values()]
        assert ratios == sorted(ratios)

    def test_trading_faster_buys_capacity_only_by_demanding_a_bigger_edge(self) -> None:
        """⭐ The trade the whole phase operates inside."""
        table = role_gate.hurdle_table(3.406)["frequencies"]
        weekly = table["weekly"]
        daily = table["daily"]
        assert daily["required_gross_annual_ir"] > weekly["required_gross_annual_ir"]
        assert daily["admissible_effective_parameters"] > weekly["admissible_effective_parameters"]
        assert weekly["admissible_effective_parameters"] < 1.0

    def test_turnover_that_puts_the_hurdle_out_of_reach_is_refused(self) -> None:
        verdict = role_gate.assess(_catalogue_by_id()["M14_intraday_session_state_return"])
        assert verdict["verdict"] == role_gate.Verdict.ECONOMICALLY_UNREACHABLE.value

    def test_leverage_cannot_clear_the_hurdle(self) -> None:
        design = _catalogue_by_id()["M14_intraday_session_state_return"]
        with pytest.raises(ValueError, match="leverage"):
            role_gate.required_gross_annual_ir(
                dataclasses.replace(design, annual_vol_bp=role_gate.MAX_ANNUAL_VOL_BP + 1)
            )

    def test_an_execution_study_is_not_asked_to_clear_a_return_hurdle(self) -> None:
        verdict = role_gate.assess(_catalogue_by_id()["M12_excursion_conditional_exit_design"])
        assert verdict["economics"]["required_gross_annual_ir"] == 0.0
        assert verdict["verdict"] == role_gate.Verdict.DEVELOPMENT_ADMISSIBLE.value


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

    def test_the_verdict_counts(self, record: dict[str, Any]) -> None:
        counts = {name: len(ids) for name, ids in record["by_verdict"].items()}
        assert counts[role_gate.Verdict.DEVELOPMENT_ADMISSIBLE.value] == 9
        assert counts[role_gate.Verdict.CAPACITY_EXCEEDED.value] == 7
        assert counts[role_gate.Verdict.ECONOMICALLY_UNREACHABLE.value] == 1
        assert counts[role_gate.Verdict.PRIOR_FAMILY_CLOSED.value] == 1
        assert sum(counts.values()) == record["n_candidates"] == 18

    def test_the_default_architecture_is_the_one_that_fails(self, record: dict[str, Any]) -> None:
        """⭐ The control case: the model this phase would have reached for."""
        boosted = next(
            row
            for row in record["candidates"]
            if row["candidate_id"] == "M18_boosted_tree_cross_sectional_ranking"
        )
        assert boosted["verdict"] == role_gate.Verdict.CAPACITY_EXCEEDED.value
        capacity = boosted["budgets"]["capacity"]
        assert (
            capacity["declared_effective_parameters"]
            > 10 * (capacity["admissible_effective_parameters"])
        )

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
        assert one["affordable"] and not three["affordable"]

    def test_the_affordable_shapes_are_the_narrow_ones(self) -> None:
        budget = universe.phase_budget()
        affordable = {
            (s["tracks"], s["configurations_per_track"]) for s in budget["affordable_shapes"]
        }
        assert (3, 1) in affordable
        assert (2, 2) in affordable
        assert (3, 2) not in affordable
        assert (4, 1) not in affordable
        assert budget["most_tracks_affordable"] == 3

    def test_every_shape_marked_affordable_really_is(self) -> None:
        budget = universe.phase_budget()
        for shape in budget["shapes"]:
            expected = (
                shape["selection_inflation_annual_ir"]
                <= (budget["minimum_relevant_incremental_ir"])
            )
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

    def test_every_self_contained_candidate_outranks_every_dependent_one(self) -> None:
        """⭐ The first key in the sort, which a mutation removed without effect.

        With the current catalogue the dependent candidate also happens to fall
        out of the utilisation band, so dropping the criterion changed no verdict
        — and the ordering still moved. A candidate whose result depends on
        another candidate succeeding is a worse use of a one-shot budget whatever
        else is true of it, so the property is asserted directly.
        """
        ranked = universe.rank()
        positions = [row["rank"] for row in ranked if row["self_contained"]]
        dependent = [row["rank"] for row in ranked if not row["self_contained"]]
        assert dependent, "the catalogue has no dependent candidate to order against"
        assert max(positions) < min(dependent)

    def test_the_band_excludes_both_ends_and_not_only_one(self) -> None:
        """⭐ Too little capacity used is as disqualifying as too much."""
        band = universe.CAPACITY_UTILISATION_BAND
        rows = {row["candidate_id"]: row for row in universe.rank()}
        below = [r for r in rows.values() if r["capacity_utilisation"] < band[0]]
        above = [r for r in rows.values() if r["capacity_utilisation"] > band[1]]
        assert below, "no candidate sits below the band, so the lower edge is untested"
        assert above, "no candidate sits above the band, so the upper edge is untested"
        for row in below + above:
            assert row["utilisation_in_band"] is False, row["candidate_id"]
        for row in rows.values():
            if band[0] <= row["capacity_utilisation"] <= band[1]:
                assert row["utilisation_in_band"] is True, row["candidate_id"]

    def test_the_role_constraint_bites_when_the_ranking_would_repeat_a_role(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """⭐ The constraint that makes the three tracks orthogonal.

        The real ranking happens to lead with three distinct roles, so removing
        the check changes nothing and a test of the outcome cannot see it. Feed
        it a ranking whose top three share a role and the mechanism has to show.
        """
        repeated = [
            {"candidate_id": "X1", "role": "cross_sectional_ranking", "rank": 1},
            {"candidate_id": "X2", "role": "cross_sectional_ranking", "rank": 2},
            {"candidate_id": "X3", "role": "trade_or_skip", "rank": 3},
            {"candidate_id": "X4", "role": "direction_or_return_generator", "rank": 4},
        ]
        monkeypatch.setattr(universe, "rank", lambda: repeated)
        chosen = [row["candidate_id"] for row in universe.selected_tracks()["selected"]]
        assert chosen == ["X1", "X3", "X4"], "a repeated role was selected"

    def test_the_selection_is_deterministic(self) -> None:
        first = [row["candidate_id"] for row in universe.selected_tracks()["selected"]]
        second = [row["candidate_id"] for row in universe.selected_tracks()["selected"]]
        assert first == second

    def test_the_selected_tracks_have_distinct_roles(self) -> None:
        selection = universe.selected_tracks()
        roles = [row["role"] for row in selection["selected"]]
        assert len(roles) == len(set(roles))
        assert len(roles) == selection["affordable_tracks"] == 3

    def test_the_selection_matches_the_three_directions_the_decision_named(self) -> None:
        """A/B/C had to be compared; that they were also chosen is the algorithm's answer."""
        chosen = {row["candidate_id"] for row in universe.selected_tracks()["selected"]}
        assert chosen == {
            "M01_currency_cross_sectional_ranking",
            "M03_regime_conditioned_level_multi_timeframe",
            "M13_hurdle_clearing_probability_with_learned_threshold",
        }

    def test_the_configuration_allowance_comes_from_the_phase_budget(self) -> None:
        selection = universe.selected_tracks()
        assert selection["configurations_per_track"] == 1
        budget = universe.phase_budget()
        shape = next(
            s
            for s in budget["affordable_shapes"]
            if s["tracks"] == 3 and s["configurations_per_track"] == 1
        )
        assert shape["affordable"] is True


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

    def test_the_registered_budget_matches_the_computed_one(self) -> None:
        """A prereg that quotes a budget it did not compute is a prereg with a typo."""
        budget = universe.phase_budget()
        shape = next(
            s
            for s in budget["affordable_shapes"]
            if s["tracks"] == 3 and s["configurations_per_track"] == 1
        )
        registered = prereg.MAXIMUM_RESEARCH_BUDGET
        assert registered["tracks"] == 3
        assert registered["configurations_per_track"] == 1
        assert registered["phase_effective_configurations"] == pytest.approx(
            shape["phase_effective_configurations"]
        )
        assert registered["selection_inflation_annual_ir"] == pytest.approx(
            shape["selection_inflation_annual_ir"], abs=1e-3
        )

    def test_every_registered_track_is_a_selected_one(self) -> None:
        selected = {row["candidate_id"] for row in universe.selected_tracks()["selected"]}
        registered = {track["candidate_id"] for track in prereg.TRACKS}
        assert registered == selected

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
