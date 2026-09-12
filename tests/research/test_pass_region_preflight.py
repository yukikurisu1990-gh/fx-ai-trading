"""Contract tests for the Pass-Region Preflight.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The preflight exists because Track 2 ran a study whose success arm was
unreachable the day it was frozen. `TestTrack2Retrospective` is therefore the
test that matters most: the preflight, given Track 2's **frozen plan and no data
at all**, must refuse it.

`TestBehaviourUnderChange` holds the six behaviours the decision named, including
the one the whole rewrite is about — that lowering a cost may not change the
statistical side of the answer.
"""

from __future__ import annotations

import dataclasses

import pytest

from scripts.research.feasibility import (
    COST_STRESS_MULTIPLE,
    MAX_PLAUSIBLE_GROSS_IR,
    MIN_EVENTS_PER_PANEL,
    MIN_NET_MARGIN_BP,
)
from scripts.research.feasibility.preflight import (
    MARGIN_FLOOR,
    MIN_DECIDING_PANELS,
    ResearchPlan,
    VarianceSource,
    Verdict,
    admissible_frequency_bp,
    assess,
    dispersion_window_bp,
    power_multiplier,
    required_effective_years,
    years_to_decision,
)


def plan(**overrides: object) -> ResearchPlan:
    """A plan that passes, so that each test can break exactly one thing."""
    base = {
        "candidate_id": "probe",
        "hypothesis": "a probe",
        "mechanism": "a mechanism",
        "target": "currency-level relative return",
        "horizon": "1d",
        "unit_of_observation": "currency-event",
        "events_per_year": 60.0,
        "panel_years": 6.0,
        "n_deciding_panels": 2,
        "effective_n_share": 0.8,
        "effective_n_basis": "seven effective currency dimensions in twenty pairs",
        "roundtrip_cost_bp": 2.0,
        "primary_cells": 1,
        "required_breadth": 4,
        "available_breadth": 7,
        "data_ready": True,
        "variance_source": VarianceSource.UNCONDITIONAL_RETURN_VARIANCE,
    }
    base.update(overrides)
    return ResearchPlan(**base)  # type: ignore[arg-type]


class TestTheClosedForm:
    def test_the_requirement_is_the_gate_constants_and_nothing_else(self) -> None:
        assert required_effective_years(1) == pytest.approx(
            (power_multiplier(1) / MAX_PLAUSIBLE_GROSS_IR) ** 2
        )
        assert required_effective_years(1) == pytest.approx(3.488, abs=5e-3)

    def test_more_primary_cells_need_a_longer_panel(self) -> None:
        """The multiple-testing burden, in years."""
        years = [required_effective_years(k) for k in (1, 2, 3, 4, 5)]
        assert years == sorted(years)
        assert required_effective_years(3) == pytest.approx(4.653, abs=5e-3)

    def test_the_window_does_not_move_with_the_cost(self) -> None:
        cheap, dear = plan(roundtrip_cost_bp=0.5), plan(roundtrip_cost_bp=9.0)
        assert dispersion_window_bp(cheap) == dispersion_window_bp(dear)

    def test_effective_years_can_never_exceed_the_panel(self) -> None:
        for share in (0.1, 0.5, 1.0):
            assert plan(effective_n_share=share).effective_years <= plan().panel_years


class TestBehaviourUnderChange:
    """The six the decision named."""

    def test_lower_cost_leaves_the_statistical_side_alone(self) -> None:
        dear = assess(plan(roundtrip_cost_bp=3.0))
        cheap = assess(plan(roundtrip_cost_bp=1.0))
        for name in ("horizon", "event_floor", "dispersion_window_is_non_empty"):
            assert dear["conditions"][name] == cheap["conditions"][name]
        assert dear["margins"]["horizon"] == cheap["margins"]["horizon"]
        #: ...and the economic side is the same or better.
        assert (
            cheap["margins"]["economic_net_under_stress"]
            >= dear["margins"]["economic_net_under_stress"]
        )

    def test_higher_cost_hurts_only_the_economic_side(self) -> None:
        cheap = assess(plan(roundtrip_cost_bp=1.0))
        dear = assess(plan(roundtrip_cost_bp=3.0))
        assert dear["margins"]["horizon"] == cheap["margins"]["horizon"]
        assert (
            dear["margins"]["economic_net_under_stress"]
            < cheap["margins"]["economic_net_under_stress"]
        )

    def test_a_longer_panel_helps(self) -> None:
        short, long = assess(plan(panel_years=2.0)), assess(plan(panel_years=8.0))
        assert long["margins"]["horizon"] > short["margins"]["horizon"]
        assert short["conditions"]["horizon"] is False
        assert long["conditions"]["horizon"] is True

    def test_too_few_events_fails_the_floor(self) -> None:
        record = assess(plan(events_per_year=4.0, panel_years=6.0))
        assert record["n_events_per_panel"] < MIN_EVENTS_PER_PANEL
        assert record["conditions"]["event_floor"] is False
        assert record["verdict"] == Verdict.NO_DECISION_GRADE_PASS_REGION.value

    def test_a_higher_variance_can_leave_the_window(self) -> None:
        lower, upper = dispersion_window_bp(plan())
        inside = assess(plan(dispersion_bp=(lower + upper) / 2.0))
        outside = assess(plan(dispersion_bp=upper * 2.0))
        assert inside["conditions"]["declared_dispersion_inside_the_window"] is True
        assert outside["conditions"]["declared_dispersion_inside_the_window"] is False

    def test_more_multiple_testing_burden_hurts(self) -> None:
        one, five = assess(plan(primary_cells=1)), assess(plan(primary_cells=5))
        assert five["required_effective_years"] > one["required_effective_years"]
        assert five["margins"]["horizon"] < one["margins"]["horizon"]


class TestTheFrequencyBand:
    def test_a_design_can_be_too_frequent_to_pay_for(self) -> None:
        """The stressed-cost condition is an upper bound on frequency."""
        _floor, ceiling = admissible_frequency_bp(plan(roundtrip_cost_bp=2.5))
        assert ceiling == pytest.approx(
            300.0 / (COST_STRESS_MULTIPLE * 2.5 + MIN_NET_MARGIN_BP - 2.5)
        )
        record = assess(plan(events_per_year=ceiling * 1.5, roundtrip_cost_bp=2.5))
        assert record["conditions"]["economic_net_under_stress"] is False

    def test_a_design_can_be_too_rare_to_adjudicate(self) -> None:
        floor, _ceiling = admissible_frequency_bp(plan(panel_years=6.0))
        assert floor == pytest.approx(MIN_EVENTS_PER_PANEL / 6.0)
        assert assess(plan(events_per_year=floor * 0.5))["conditions"]["event_floor"] is False

    def test_a_free_design_has_no_frequency_ceiling(self) -> None:
        _floor, ceiling = admissible_frequency_bp(plan(roundtrip_cost_bp=0.0))
        assert ceiling is None


class TestVerdicts:
    def test_a_closed_family_is_refused_before_anything_is_computed(self) -> None:
        record = assess(plan(prior_verdict=Verdict.PRIOR_FAMILY_CLOSED.value))
        assert record["verdict"] == Verdict.PRIOR_FAMILY_CLOSED.value
        assert "conditions" not in record

    def test_unusable_data_is_refused_before_the_arithmetic(self) -> None:
        record = assess(plan(data_ready=False, data_note="no free consensus history"))
        assert record["verdict"] == Verdict.DATA_INTEGRITY_BLOCKED.value
        assert "no free consensus history" in record["reason"]

    def test_a_thin_margin_is_marginal_rather_than_feasible(self) -> None:
        needed = required_effective_years(1)
        #: Just over the line, by less than the floor.
        years = needed / 0.8 * (1.0 + MARGIN_FLOOR / 2.0)
        record = assess(plan(panel_years=years))
        assert record["conditions"]["horizon"] is True
        assert record["verdict"] == Verdict.MARGINAL_PASS_REGION.value

    def test_a_comfortable_plan_passes(self) -> None:
        record = assess(plan(panel_years=8.0))
        assert record["verdict"] == Verdict.PASS_REGION_EXISTS.value
        assert all(record["conditions"].values())

    def test_one_panel_is_never_enough(self) -> None:
        record = assess(plan(n_deciding_panels=1, panel_years=8.0))
        assert record["conditions"]["two_panels"] is False
        assert record["verdict"] == Verdict.NO_DECISION_GRADE_PASS_REGION.value

    def test_insufficient_breadth_fails(self) -> None:
        record = assess(plan(panel_years=8.0, available_breadth=2, required_breadth=4))
        assert record["conditions"]["breadth"] is False


class TestTrack2Retrospective:
    """⭐ The regression the decision required.

    Track 2's frozen plan — two deciding panels of 1.996 years, three primary
    cells — must be refused **before any signal is measured**. It is refused on
    the horizon alone, which needs nothing but the panel length and the cell
    count: no frequency, no dispersion, no cost and no data.
    """

    @staticmethod
    def track_2_frozen_plan(**overrides: object) -> ResearchPlan:
        frozen = {
            "candidate_id": "track_2_non_usd_surprise_relative",
            "hypothesis": "a non-USD macro surprise carries a forward relative return",
            "mechanism": "a hawkish print appreciates its own currency",
            "target": "currency against a basket of the other seven",
            "horizon": "1d",
            "unit_of_observation": "currency-event",
            "events_per_year": 60.0,
            "panel_years": 1.996,
            "n_deciding_panels": 2,
            "effective_n_share": 0.8,
            "primary_cells": 3,
            "roundtrip_cost_bp": 4.5,
            "required_breadth": 4,
            "available_breadth": 7,
        }
        frozen.update(overrides)
        return plan(**frozen)

    def test_the_preflight_would_have_stopped_track_2(self) -> None:
        record = assess(self.track_2_frozen_plan())
        assert record["verdict"] == Verdict.NO_DECISION_GRADE_PASS_REGION.value
        assert record["conditions"]["horizon"] is False
        assert record["binding_constraint"] == "horizon"

    def test_it_is_refused_whatever_the_frequency_and_the_cost(self) -> None:
        """So the refusal cannot be argued away by redesigning around it."""
        for frequency in (30.0, 60.0, 120.0, 250.0):
            for cost in (0.0, 1.0, 2.5, 6.0):
                record = assess(
                    self.track_2_frozen_plan(events_per_year=frequency, roundtrip_cost_bp=cost)
                )
                assert record["conditions"]["horizon"] is False, (frequency, cost)

    def test_it_is_refused_even_with_perfectly_independent_observations(self) -> None:
        """`effective_n_share = 1` is the most generous assumption available."""
        record = assess(self.track_2_frozen_plan(effective_n_share=1.0))
        assert record["conditions"]["horizon"] is False
        assert record["effective_years"] == pytest.approx(1.996, abs=1e-3)

    def test_even_a_single_primary_cell_would_not_have_saved_it(self) -> None:
        record = assess(self.track_2_frozen_plan(primary_cells=1, effective_n_share=1.0))
        assert record["required_effective_years"] == pytest.approx(3.488, abs=5e-3)
        assert record["conditions"]["horizon"] is False

    def test_the_refusal_needs_no_data(self) -> None:
        """Every field the horizon condition reads is in the pre-registration."""
        record = assess(self.track_2_frozen_plan(variance_source=VarianceSource.NOT_ESTIMATED))
        assert record["verdict"] == Verdict.NO_DECISION_GRADE_PASS_REGION.value

    def test_it_says_how_much_would_have_been_needed(self) -> None:
        gap = years_to_decision(self.track_2_frozen_plan())
        assert gap["current_effective_years"] == pytest.approx(1.597, abs=1e-2)
        assert gap["required_effective_years"] == pytest.approx(4.653, abs=5e-3)
        assert gap["total_seen_years_needed"] > 10.0


class TestNoSignalCanReachAVerdict:
    def test_the_plan_has_no_field_for_a_realised_quantity(self) -> None:
        """A textual check over the dataclass, because a field nobody looks at is
        exactly how a signal gets in."""
        forbidden = ("return", "alpha", "sharpe", "p_value", "ic_", "sign", "pnl")
        names = set(ResearchPlan.__dataclass_fields__)
        assert not [name for name in names for bad in forbidden if bad in name]

    def test_no_variance_source_is_the_candidates_own_signal(self) -> None:
        for source in VarianceSource:
            assert "signal_return" not in source.value
            assert "realis" not in source.value

    def test_two_plans_differing_only_in_prose_get_the_same_verdict(self) -> None:
        a = plan(hypothesis="one story", mechanism="a", panel_years=8.0)
        b = dataclasses.replace(a, hypothesis="another story", mechanism="b")
        assert assess(a)["verdict"] == assess(b)["verdict"]
        assert assess(a)["margins"] == assess(b)["margins"]


class TestYearsToDecision:
    def test_a_passing_plan_needs_nothing_more(self) -> None:
        gap = years_to_decision(plan(panel_years=8.0))
        assert gap["additional_effective_years"] == 0.0

    def test_the_total_is_per_panel_times_the_panel_count(self) -> None:
        gap = years_to_decision(plan(panel_years=2.0))
        assert gap["total_seen_years_needed"] == pytest.approx(
            gap["panel_years_needed_per_panel"] * MIN_DECIDING_PANELS, abs=5e-3
        )
