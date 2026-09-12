"""Contract tests for Research Feasibility Gate v2.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

These are the behaviours the gate exists to have, and they are pinned before the
gate is pointed at any data. The four in `TestBehaviourUnderChange` are the ones
the sequencing decision named; `TestTheV1Inversion` is the defect that motivated
the rewrite, kept as a live comparison so the two gates can be seen to differ on
the same inputs rather than only asserted to.

`TestProspectiveOnly` is the one that is not about statistics at all. A new rule
that can reopen an old family is a rescue mechanism, and this programme has spent
four rounds learning not to build one. The ban is code here, so a future session
cannot honour it by accident or forget it by reading past a paragraph.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.research.feasibility import (
    COST_STRESS_MULTIPLE,
    EXCLUDED_FROM_GATE_V2,
    MAX_PLAUSIBLE_GROSS_IR,
    MIN_ANNUAL_NET_RETURN_BP,
    MIN_EVENTS_PER_PANEL,
    MIN_NET_MARGIN_BP,
    MIN_RELEVANT_EFFECT_FLOOR_BP,
    REFERENCE_ROUNDTRIP_COST_BP,
    RetroactiveApplicationError,
    assert_prospective,
)
from scripts.research.feasibility.gate_v2 import (
    Costs,
    Design,
    adjudicate,
    economic_gate,
    mde_bp,
    minimum_relevant_effect_bp,
    robustness_gate,
    statistical_gate,
)
from scripts.research.fxunits import (
    COST_MULTIPLE_FOR_HURDLE,
    POWER_MULTIPLIER,
    verify_unit_consistency,
)


def design(
    *,
    n: int = 200,
    effective: float | None = None,
    dispersion: float = 45.0,
    per_year: float = 100.0,
    label: str = "probe",
) -> Design:
    """A design with the dependence discount this corpus keeps measuring."""
    return Design(
        label=label,
        n_events=n,
        effective_n=effective if effective is not None else n * 0.8,
        dispersion_bp=dispersion,
        events_per_year=per_year,
    )


class TestTheStatisticalGateCannotSeeCost:
    def test_no_cost_field_reaches_the_statistical_block(self) -> None:
        """A textual check, because a leak would be a field nobody looks at."""
        block = json.dumps(statistical_gate(design()))
        assert "cost" not in block
        assert "net" not in block

    def test_the_design_object_carries_no_cost_at_all(self) -> None:
        assert not any("cost" in field for field in Design.__dataclass_fields__)

    def test_the_reference_cost_is_a_constant_and_not_a_measurement(self) -> None:
        """Changing a design cannot change the reference the target is built on."""
        cheap = minimum_relevant_effect_bp(design())
        assert cheap == pytest.approx(
            REFERENCE_ROUNDTRIP_COST_BP + MIN_ANNUAL_NET_RETURN_BP / 100.0
        )


class TestMinimumRelevantEffect:
    def test_a_rarer_design_has_to_move_the_market_more(self) -> None:
        frequent = minimum_relevant_effect_bp(design(per_year=250.0))
        rare = minimum_relevant_effect_bp(design(per_year=12.0))
        assert rare > frequent
        #: Twelve events a year must each carry the whole annual requirement.
        assert rare == pytest.approx(REFERENCE_ROUNDTRIP_COST_BP + 300.0 / 12.0)

    def test_the_floor_binds_only_where_it_should(self) -> None:
        """The floor exists for designs so frequent the target would vanish."""
        assert minimum_relevant_effect_bp(design(per_year=1e9)) == pytest.approx(
            REFERENCE_ROUNDTRIP_COST_BP
        )
        assert REFERENCE_ROUNDTRIP_COST_BP > MIN_RELEVANT_EFFECT_FLOOR_BP

    def test_it_does_not_move_with_the_sample_size(self) -> None:
        """Otherwise more data would raise the bar as fast as it lowers the MDE."""
        assert minimum_relevant_effect_bp(design(n=100)) == minimum_relevant_effect_bp(
            design(n=10_000)
        )

    def test_it_does_not_move_with_the_dispersion(self) -> None:
        assert minimum_relevant_effect_bp(design(dispersion=10.0)) == minimum_relevant_effect_bp(
            design(dispersion=90.0)
        )


class TestBehaviourUnderChange:
    """The four examples the sequencing decision named, plus the mirror of A."""

    def test_example_a_halving_the_cost_leaves_the_statistics_alone_and_helps_economics(
        self,
    ) -> None:
        subject = design()
        dear, cheap = Costs(roundtrip_bp=3.0), Costs(roundtrip_bp=1.5)
        assert statistical_gate(subject) == statistical_gate(subject)
        before, after = economic_gate(subject, dear), economic_gate(subject, cheap)
        assert before["minimum_relevant_effect_bp"] == after["minimum_relevant_effect_bp"]
        assert after["net_bp"] > before["net_bp"]
        assert after["pass"] >= before["pass"]

    def test_example_a_mirrored_doubling_the_cost_leaves_the_statistics_alone_and_hurts(
        self,
    ) -> None:
        subject = design()
        before = economic_gate(subject, Costs(roundtrip_bp=1.5))
        after = economic_gate(subject, Costs(roundtrip_bp=3.0))
        assert after["net_bp"] < before["net_bp"]
        assert after["pass"] <= before["pass"]
        #: ...and the statistical verdict is the same object either way.
        assert statistical_gate(subject)["pass"] == statistical_gate(subject)["pass"]

    def test_example_b_more_events_improve_statistical_feasibility(self) -> None:
        """Frequency held fixed, so the extra events are extra *years* of panel."""
        few, many = design(n=100), design(n=900)
        assert mde_bp(many) < mde_bp(few)
        assert statistical_gate(many)["headroom_bp"] > statistical_gate(few)["headroom_bp"]
        #: ...and the economics is untouched, because nothing economic changed.
        costs = Costs(roundtrip_bp=2.0)
        assert economic_gate(many, costs) == economic_gate(few, costs)

    def test_example_c_more_variance_worsens_statistical_feasibility(self) -> None:
        quiet, noisy = design(dispersion=30.0), design(dispersion=90.0)
        assert mde_bp(noisy) > mde_bp(quiet)
        assert statistical_gate(noisy)["headroom_bp"] < statistical_gate(quiet)["headroom_bp"]

    def test_example_d_an_unmeetable_gross_requirement_fails_the_economic_gate(self) -> None:
        subject = design()
        relevant = minimum_relevant_effect_bp(subject)
        #: A cost that leaves less than the margin, by construction.
        costs = Costs(roundtrip_bp=relevant - MIN_NET_MARGIN_BP + 0.01)
        verdict = economic_gate(subject, costs)
        assert verdict["checks"]["net_margin"] is False
        assert verdict["pass"] is False

    def test_example_d_a_target_nobody_could_produce_fails_on_plausibility(self) -> None:
        """A rare design's target is easy to *detect* and may be impossible to *earn*."""
        rare = design(per_year=12.0, dispersion=10.0, n=120)
        verdict = economic_gate(rare, Costs(roundtrip_bp=2.0))
        assert statistical_gate(rare)["pass"] is True
        assert verdict["implied_gross_annual_ir"] > MAX_PLAUSIBLE_GROSS_IR
        assert verdict["checks"]["implied_effect_is_believable"] is False
        assert verdict["pass"] is False


class TestTheV1Inversion:
    """The defect that motivated v2, demonstrated rather than described."""

    @staticmethod
    def v1_decidable(subject: Design, cost_bp: float) -> bool:
        return mde_bp(subject) <= COST_MULTIPLE_FOR_HURDLE * cost_bp

    def test_v1_flips_its_verdict_when_only_the_cost_moves(self) -> None:
        subject = design(n=120, dispersion=20.0, per_year=100.0)
        detectable = mde_bp(subject)
        dear = detectable / COST_MULTIPLE_FOR_HURDLE * 1.10
        assert self.v1_decidable(subject, dear) is True
        #: Same data, same design, half the cost — and v1 changes its mind.
        assert self.v1_decidable(subject, dear / 2.0) is False

    def test_v2_does_not(self) -> None:
        subject = design(n=120, dispersion=20.0, per_year=100.0)
        verdict = statistical_gate(subject)["pass"]
        for cost in (0.5, 1.0, 2.0, 4.0, 8.0):
            assert statistical_gate(subject)["pass"] is verdict
            #: and the economics does move, which is where cost belongs.
            assert economic_gate(subject, Costs(roundtrip_bp=cost))["net_bp"] == pytest.approx(
                minimum_relevant_effect_bp(subject) - cost
            )

    def test_gate_v1_is_left_frozen(self) -> None:
        """`FEASIBILITY_GATE_V1_LEGACY_FROZEN`: history is not rewritten."""
        assert COST_MULTIPLE_FOR_HURDLE == 2.0
        assert pytest.approx(2.802, abs=5e-4) == POWER_MULTIPLIER


class TestProspectiveOnly:
    def test_every_excluded_family_is_refused(self) -> None:
        for family in sorted(EXCLUDED_FROM_GATE_V2):
            with pytest.raises(RetroactiveApplicationError):
                assert_prospective(family)

    def test_the_ban_survives_a_respelling(self) -> None:
        for spelling in (
            "Track_1_Clock_Structure",
            "track-1-clock-structure",
            "  track 1 clock structure  ",
        ):
            with pytest.raises(RetroactiveApplicationError):
                assert_prospective(spelling)

    def test_track_1_is_named_explicitly(self) -> None:
        assert "track_1_clock_structure" in EXCLUDED_FROM_GATE_V2
        assert "track_3_execution_frontier" in EXCLUDED_FROM_GATE_V2

    def test_a_new_family_is_allowed(self) -> None:
        assert assert_prospective("non_usd_surprise_relative") == "non_usd_surprise_relative"

    def test_adjudicate_refuses_before_it_computes_anything(self) -> None:
        with pytest.raises(RetroactiveApplicationError):
            adjudicate("track_1_clock_structure", {"a": design()}, Costs(roundtrip_bp=2.0))


class TestRobustness:
    def test_a_single_panel_never_passes(self) -> None:
        assert robustness_gate({"a": design(n=1000)})["pass"] is False

    def test_a_thin_panel_fails_even_beside_a_thick_one(self) -> None:
        panels = {"a": design(n=1000), "b": design(n=MIN_EVENTS_PER_PANEL - 1)}
        assert robustness_gate(panels)["pass"] is False

    def test_pooling_cannot_reach_the_floor(self) -> None:
        """Two half-sized panels are not one whole one."""
        half = MIN_EVENTS_PER_PANEL // 2
        panels = {"a": design(n=half), "b": design(n=half)}
        assert sum(d.n_events for d in panels.values()) >= MIN_EVENTS_PER_PANEL
        assert robustness_gate(panels)["pass"] is False


class TestAdjudication:
    @staticmethod
    def verdict(**kwargs: object) -> dict[str, object]:
        panels = {"panel_a": design(**kwargs), "panel_b": design(**kwargs)}
        return adjudicate("non_usd_surprise_relative", panels, Costs(roundtrip_bp=2.0))

    def test_the_three_gates_are_reported_separately(self) -> None:
        record = self.verdict()
        assert set(record["gates_passed"]) == {"statistical", "economic", "robustness"}
        assert record["research_feasible"] == all(record["gates_passed"].values())

    def test_one_failing_gate_fails_the_composition(self) -> None:
        thin = self.verdict(n=MIN_EVENTS_PER_PANEL - 1)
        assert thin["gates_passed"]["robustness"] is False
        assert thin["research_feasible"] is False

    def test_a_gate_passing_on_one_panel_only_has_not_passed(self) -> None:
        """The two-panel principle, which mutation testing found unpinned.

        Both panels in the other tests are identical, so `all` and `any` agree
        and the aggregation was never exercised. A family that works on one
        panel and not the other is the shape this programme has been fooled by
        before, and pooling to reach power is a diagnostic, never a success.
        """
        panels = {
            "panel_a": design(n=400, dispersion=20.0),
            "panel_b": design(n=400, dispersion=200.0),
        }
        assert statistical_gate(panels["panel_a"])["pass"] is True
        assert statistical_gate(panels["panel_b"])["pass"] is False
        record = adjudicate("non_usd_surprise_relative", panels, Costs(roundtrip_bp=2.0))
        assert record["gates_passed"]["statistical"] is False
        assert record["research_feasible"] is False

    def test_an_economic_gate_passing_on_one_panel_only_has_not_passed(self) -> None:
        """Same aggregation, and the economic gate differs across panels only
        through its dispersion-dependent plausibility term."""
        panels = {
            "panel_a": design(per_year=12.0, dispersion=90.0),
            "panel_b": design(per_year=12.0, dispersion=9.0),
        }
        costs = Costs(roundtrip_bp=2.0)
        assert economic_gate(panels["panel_a"], costs)["pass"] is True
        assert economic_gate(panels["panel_b"], costs)["pass"] is False
        record = adjudicate("non_usd_surprise_relative", panels, costs)
        assert record["gates_passed"]["economic"] is False

    def test_a_verdict_needs_a_panel(self) -> None:
        with pytest.raises(ValueError, match="at least one deciding panel"):
            adjudicate("non_usd_surprise_relative", {}, Costs(roundtrip_bp=2.0))

    def test_the_record_is_all_basis_points(self) -> None:
        audit = verify_unit_consistency(self.verdict())
        assert audit["numeric_fields_not_in_bp"] == []
        assert audit["status"] == "UNIT_CONSISTENCY_VERIFIED"

    def test_the_stressed_cost_is_the_stress_multiple(self) -> None:
        costs = Costs(roundtrip_bp=2.0)
        assert costs.stressed_bp == pytest.approx(COST_STRESS_MULTIPLE * 2.0)


class TestDesignValidation:
    def test_dependence_cannot_manufacture_power(self) -> None:
        with pytest.raises(ValueError, match="effective_n cannot exceed"):
            Design(
                label="x", n_events=100, effective_n=200.0, dispersion_bp=10.0, events_per_year=50.0
            )

    def test_a_zero_dispersion_is_refused(self) -> None:
        with pytest.raises(ValueError, match="dispersion_bp"):
            Design(
                label="x", n_events=100, effective_n=80.0, dispersion_bp=0.0, events_per_year=50.0
            )

    def test_a_zero_frequency_is_refused(self) -> None:
        with pytest.raises(ValueError, match="events_per_year"):
            Design(
                label="x", n_events=100, effective_n=80.0, dispersion_bp=10.0, events_per_year=0.0
            )

    def test_a_negative_cost_is_refused(self) -> None:
        with pytest.raises(ValueError, match="less than nothing"):
            Costs(roundtrip_bp=-0.1)


DESIGN_DOCUMENT = Path(__file__).resolve().parents[2] / "docs/design/m15_feasibility_gate_v2.md"


def test_the_documented_illustration_matches_the_gate() -> None:
    """The design document's worked table, recomputed from the frozen constants.

    A design document is prose until something recomputes it. This one carries
    the magnitudes a reader will reason from — including the claim that each of
    the three rows is stopped by a *different* gate — so the row is parsed, fed
    back through the gate, and every printed figure checked against what comes
    out.
    """
    text = DESIGN_DOCUMENT.read_text(encoding="utf-8").replace("−", "-")
    rows = [
        [cell.strip() for cell in line.strip("|").split("|")]
        for line in text.splitlines()
        if line.startswith("|") and line.count("|") == 13
    ]
    measured = [row for row in rows if row[1].replace(".", "").isdigit()]
    assert len(measured) == 3, f"expected three illustration rows, parsed {len(measured)}"

    for row in measured:
        label = row[0]
        subject = Design(
            label=label,
            n_events=int(row[1]),
            effective_n=float(row[2]),
            dispersion_bp=float(row[3]),
            events_per_year=float(row[4]),
        )
        costs = Costs(roundtrip_bp=float(row[5]))
        stat = statistical_gate(subject)
        econ = economic_gate(subject, costs)
        assert stat["mde_bp"] == pytest.approx(float(row[6]), abs=5e-3), label
        assert stat["minimum_relevant_effect_bp"] == pytest.approx(float(row[7]), abs=5e-3), label
        assert stat["pass"] is (row[8] == "pass"), label
        assert econ["net_bp"] == pytest.approx(float(row[9]), abs=5e-3), label
        assert econ["implied_gross_annual_ir"] == pytest.approx(float(row[10]), abs=5e-3), label
        assert econ["pass"] is (row[11] == "pass"), label

    #: The point of the table: the three rows are stopped by different things.
    verdicts = {row[0]: (row[8] == "pass", row[11] == "pass") for row in measured}
    assert len(set(verdicts.values())) == 3, verdicts
