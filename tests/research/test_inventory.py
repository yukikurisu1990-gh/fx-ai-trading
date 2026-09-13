"""Tests for the Decision-Grade Research Inventory.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

The inventory's job is to answer "can this be answered" without ever asking "what
is the answer". Two families of test carry that:

**No signal can reach it.** The package imports nothing that opens a market-data
file, no candidate carries a realised quantity, and the whole artifact is
reproducible from constants — so a second run of a signal-free thing must be
identical.

**The horizon claim is arithmetic, not an opinion.** `effective_years` is
`panel_years × share` by construction, so the requirement cannot be met on a
1.996-year panel under any assumption. That is the inventory's conclusion and it
is tested as an identity rather than transcribed as a number.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from scripts.research.feasibility import inventory
from scripts.research.feasibility.preflight import (
    Verdict,
    assess,
    required_effective_years,
)

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts/research/feasibility/inventory.json"


@pytest.fixture(scope="module")
def record() -> dict[str, Any]:
    return inventory.build()


class TestTheCatalogue:
    def test_there_are_at_least_fifteen_directions(self, record: dict[str, Any]) -> None:
        assert record["n_candidates"] >= 15

    def test_every_candidate_id_is_distinct(self) -> None:
        ids = [plan.candidate_id for plan in inventory.catalogue()]
        assert len(ids) == len(set(ids))

    def test_none_is_a_timeframe_variant_of_another(self) -> None:
        """Padding the list with H1/H4/D1 copies is explicitly forbidden.

        Two candidates sharing a mechanism *and* a target would be the same
        direction at two speeds; the test is that no such pair exists.
        """
        seen: set[tuple[str, str]] = set()
        for plan in inventory.catalogue():
            key = (plan.mechanism, plan.target)
            assert key not in seen, key
            seen.add(key)

    def test_every_candidate_declares_where_its_variance_would_come_from(self) -> None:
        for plan in inventory.catalogue():
            assert plan.variance_source is not None
            assert (
                "signal" not in plan.variance_source.value or "blind" in plan.variance_source.value
            )

    def test_the_suspended_clock_family_is_marked_suspended_not_refuted(self) -> None:
        """Track 1 is suspended, which is not the same as falsified.

        A review was right that recording an underpowered family as refuted is the
        failure this programme keeps correcting. The two clock candidates carry
        `suspended_by_decision`, which bars them from being proposed, and are
        adjudicated on their statistics like everything else.
        """
        by_id = {plan.candidate_id: plan for plan in inventory.catalogue()}
        for candidate in ("C04_benchmark_fix_flow", "C05_month_end_rebalancing_flow"):
            assert by_id[candidate].suspended_by_decision is True
            assert by_id[candidate].prior_verdict is None

    def test_every_closure_carries_a_citation(self) -> None:
        """A closure a reader cannot check from the artifact is a closure on trust."""
        for plan in inventory.catalogue():
            if plan.prior_verdict != Verdict.PRIOR_FAMILY_CLOSED.value:
                continue
            assert plan.prior_verdict_citation, plan.candidate_id
            assert len(plan.prior_verdict_citation) > 40, plan.candidate_id

    def test_a_closure_is_refused_by_code_and_not_by_a_typed_field(self) -> None:
        """`assert_prospective` raising is the enforcement; the record proves it ran."""
        refused = [
            block
            for block in inventory.build()["candidates"]
            if block.get("refused_by") == "assert_prospective"
        ]
        assert refused, "no closure went through the machine-enforced ban"
        for block in refused:
            assert block["verdict"] == Verdict.PRIOR_FAMILY_CLOSED.value

    def test_a_target_that_is_not_a_signed_effect_is_out_of_scope(self) -> None:
        """The gate's MRE and IR ceiling are undefined for a cost or a magnitude."""
        out_of_scope = set(inventory.build()["by_verdict"][Verdict.OUT_OF_GATE_SCOPE.value])
        assert "C17_intraday_execution_timing" in out_of_scope
        assert "C15_movement_magnitude_forecast" in out_of_scope


class TestNoSignalContamination:
    def test_no_computation_module_can_open_a_market_data_file(self) -> None:
        """Every computation module, not the two a first version happened to scan.

        `driver.py` is excluded on purpose and checked separately: it writes the
        artifact, which is the one filesystem touch the package is allowed.
        """
        for name in ("__init__.py", "gate_v2.py", "preflight.py", "inventory.py"):
            source = (ROOT / "scripts/research/feasibility" / name).read_text(encoding="utf-8")
            for forbidden in ("read_parquet", "read_csv", "urlopen", "load_panel", "open("):
                assert forbidden not in source, f"{name}: {forbidden}"

    def test_the_driver_only_writes_its_own_artifact(self) -> None:
        source = (ROOT / "scripts/research/feasibility/driver.py").read_text(encoding="utf-8")
        for forbidden in ("read_parquet", "read_csv", "urlopen", "load_panel", "read_text"):
            assert forbidden not in source, forbidden
        assert 'ARTIFACTS = Path("artifacts/research/feasibility")' in source

    def test_the_signal_free_flag_is_computed_and_not_declared(self) -> None:
        """A flag that is always True certifies nothing."""
        assert inventory.build()["signal_free"] is True
        contaminated = [{"candidate_id": "x", "verdict": "y", "gross_bp": 1.0}]
        assert inventory._no_realised_quantity_present(contaminated) is False

    def test_the_flag_follows_the_scan_rather_than_a_literal(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A mutation found calling the scan and then ignoring it.

        Checking the scan in isolation and the flag in isolation leaves the wire
        between them untested, which is exactly where `signal_free: True` was
        hard-coded before. Force the scan to refuse and the flag has to follow.
        """
        monkeypatch.setattr(inventory, "_no_realised_quantity_present", lambda _: False)
        assert inventory.build()["signal_free"] is False

    def test_the_scan_reaches_a_quantity_buried_in_a_nested_record(self) -> None:
        """A realised number would arrive inside a conditions or window block.

        A mutation that stopped the walk at the top level survived: no candidate
        carries a forbidden key at depth one, so a scan that never descends looks
        identical to a scan that works.
        """
        nested = [
            {
                "candidate_id": "x",
                "verdict": "y",
                "conditions": {"detail": {"realised_sharpe": 1.0}},
            }
        ]
        assert inventory._no_realised_quantity_present(nested) is False
        listed = [{"candidate_id": "x", "windows": [{"net_bp": 1.0}]}]
        assert inventory._no_realised_quantity_present(listed) is False

    def test_no_candidate_carries_a_realised_quantity(self) -> None:
        blob = json.dumps(inventory.build(), default=str).lower()
        for forbidden in ("sharpe", "p_value", "information_coefficient", "pnl", "alpha"):
            assert forbidden not in blob, forbidden

    def test_the_inventory_is_reproducible(self) -> None:
        """A signal-free computation over constants has one answer."""
        first = json.dumps(inventory.build(), sort_keys=True, default=str)
        second = json.dumps(inventory.build(), sort_keys=True, default=str)
        assert first == second


class TestTheHorizonIsArithmetic:
    def test_effective_years_is_the_panel_times_the_share(self) -> None:
        for plan in inventory.catalogue():
            assert plan.effective_years == pytest.approx(
                plan.panel_years * plan.effective_n_share, rel=1e-12
            )

    def test_no_assumption_reaches_the_requirement_on_these_panels(
        self, record: dict[str, Any]
    ) -> None:
        block = record["horizon_is_assumption_free"]
        assert block["any_assumption_reaches_the_requirement"] is False
        assert block["max_effective_years_over_every_assumption"] == pytest.approx(
            inventory.PANEL_YEARS, rel=1e-9
        )
        assert required_effective_years(1) > inventory.PANEL_YEARS

    def test_all_seen_history_still_does_not_reach_it(self, record: dict[str, Any]) -> None:
        """The one extension that needs no new permission, and it is not enough."""
        block = record["horizon_counterfactuals"]["all_seen_history_split_in_two"]
        assert block["horizon_condition_can_be_met"] is False
        assert block["panel_years"] < required_effective_years(1)

    def test_the_counterfactual_reads_no_protected_data(self) -> None:
        """It is a subtraction between two dates a manifest already records."""
        source = (ROOT / "scripts/research/feasibility/inventory.py").read_text(encoding="utf-8")
        assert "fromisoformat" in source
        assert "load" not in source.replace("payload", "")


class TestTheVerdictDistribution:
    def test_no_green_candidate_on_the_current_panels(self, record: dict[str, Any]) -> None:
        assert Verdict.PASS_REGION_EXISTS.value not in record["by_verdict"]
        assert record["status"] == inventory.STATUS_EXHAUSTED

    def test_more_history_reaches_only_a_marginal_candidate(self, record: dict[str, Any]) -> None:
        """Measured per candidate, not from the share-free horizon flag.

        A review found the flag saying a longer history "would open a pass region"
        while no candidate actually reached one — the flag is computed at perfect
        independence and no catalogued design assumes that.
        """
        assert record["additional_history_would_open_a_pass_region"] is False
        assert record["additional_history_would_reach_only_marginal"] is True
        block = record["counterfactual_verdicts_per_candidate"]["with_the_fresh_pool_split_in_two"]
        assert block["n_pass_region_exists"] == 0
        assert block["n_marginal"] == 1

    def test_no_candidate_reaches_a_pass_region_on_any_seen_configuration(
        self, record: dict[str, Any]
    ) -> None:
        for name in ("current", "all_seen_history_split_in_two"):
            block = record["counterfactual_verdicts_per_candidate"][name]
            assert block["n_pass_region_exists"] == 0
            assert block["n_marginal"] == 0

    def test_a_blocked_candidate_is_blocked_and_not_merely_underpowered(
        self, record: dict[str, Any]
    ) -> None:
        blocked = record["by_verdict"][Verdict.DATA_INTEGRITY_BLOCKED.value]
        assert "C02_macro_surprise_intraday" in blocked
        assert "C20_broker_order_flow" in blocked

    def test_every_underpowered_candidate_says_what_it_would_need(
        self, record: dict[str, Any]
    ) -> None:
        red = set(record["by_verdict"][Verdict.NO_DECISION_GRADE_PASS_REGION.value])
        quantified = {gap["candidate_id"] for gap in record["years_to_decision"]}
        assert red == quantified
        for gap in record["years_to_decision"]:
            assert gap["additional_effective_years"] > 0

    def test_a_high_frequency_candidate_also_fails_on_cost(self, record: dict[str, Any]) -> None:
        """The frequency ceiling is a real constraint, not decoration."""
        by_id = {block["candidate_id"]: block for block in record["candidates"]}
        assert (
            by_id["C03_session_handover_relative"]["conditions"]["economic_net_under_stress"]
            is False
        )

    def test_a_rare_candidate_is_stopped_by_the_event_floor_as_well(
        self, record: dict[str, Any]
    ) -> None:
        by_id = {block["candidate_id"]: block for block in record["candidates"]}
        month_end = by_id["C05_month_end_rebalancing_flow"]
        assert month_end["conditions"]["event_floor"] is False
        assert month_end["binding_constraint"] == "event_floor"

    def test_the_binding_constraint_is_always_a_failing_one(self, record: dict[str, Any]) -> None:
        """A review found a plan naming a condition it passed as binding."""
        for block in record["candidates"]:
            if "conditions" not in block:
                continue
            failing = [name for name, ok in block["conditions"].items() if not ok]
            if failing:
                assert block["binding_constraint"] in failing, block["candidate_id"]


class TestTheDataBoundary:
    def test_the_seen_and_protected_spans_do_not_overlap(self, record: dict[str, Any]) -> None:
        seen_end = max(span["end"] for span in record["seen_spans"].values())
        assert record["protected_spans"]["fresh_pool"]["end"] < min(
            span["start"] for span in record["seen_spans"].values()
        )
        assert record["protected_spans"]["historical_oos_slice"]["start"] > seen_end

    def test_the_unused_but_seen_span_is_named_as_such(self, record: dict[str, Any]) -> None:
        """The development corpus is seen, unprotected, and in neither panel."""
        development = record["seen_spans"]["development_2025"]
        assert "not" in development["role"]
        assert development["start"] == "2025-04-25"

    def test_the_committed_artifact_matches_a_fresh_build(self, record: dict[str, Any]) -> None:
        if not ARTIFACT.exists():
            pytest.skip("run `python -m scripts.research.feasibility.driver inventory`")
        committed = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        #: The **whole** record. A review pointed out that comparing two keys let
        #: every number in the artifact drift unnoticed.
        assert committed == json.loads(json.dumps(record, sort_keys=True, default=str))


class TestCostAssumptions:
    def test_the_cost_basis_is_a_measured_figure_and_not_an_estimate(self) -> None:
        assert pytest.approx(2.58, abs=0.2) == inventory.PAIR_ROUNDTRIP_BP
        assert inventory.BASKET_ROUNDTRIP_BP > inventory.PAIR_ROUNDTRIP_BP

    def test_a_cheaper_world_does_not_create_a_green_candidate(self) -> None:
        """Cost cannot reach the horizon condition, so free execution changes nothing."""
        for plan in inventory.catalogue():
            if plan.prior_verdict or not plan.data_ready:
                continue
            free = assess(
                type(plan)(**{**plan.__dict__, "roundtrip_cost_bp": 0.0})  # type: ignore[arg-type]
            )
            assert free["verdict"] != Verdict.PASS_REGION_EXISTS.value, plan.candidate_id


class TestTheConstantsArePinned:
    """Every load-bearing constant, against the record it comes from.

    A review mutated each of them and found the suite silent. The panel length is
    the one to weight: it is the most load-bearing number in the report, and the
    two checks that looked at it compared the artifact against the constant, so
    they moved together and caught nothing.
    """

    def test_the_panel_length_is_the_loaders_own_span(self) -> None:
        import datetime as dt

        from scripts.research.exploratory_m15 import momentum, supplemental

        spans = (
            (momentum.MOMENTUM_START_UTC, momentum.MOMENTUM_END_UTC),
            (supplemental.SUPPLEMENTAL_START_UTC, supplemental.SUPPLEMENTAL_END_UTC),
        )
        for start, end in spans:
            years = (dt.date.fromisoformat(end) - dt.date.fromisoformat(start)).days / 365.25
            assert pytest.approx(years, abs=5e-3) == inventory.PANEL_YEARS, (start, end)

    def test_the_seen_spans_are_the_loaders_own(self) -> None:
        from scripts.research.exploratory_m15 import (
            DEVELOPMENT_END_UTC,
            DEVELOPMENT_START_UTC,
            momentum,
            supplemental,
        )

        spans = inventory.SEEN_SPANS
        assert spans["momentum_2021_2023"]["start"] == momentum.MOMENTUM_START_UTC
        assert spans["momentum_2021_2023"]["end"] == momentum.MOMENTUM_END_UTC
        assert spans["supplemental_2023_2025"]["start"] == supplemental.SUPPLEMENTAL_START_UTC
        assert spans["supplemental_2023_2025"]["end"] == supplemental.SUPPLEMENTAL_END_UTC
        assert spans["development_2025"]["start"] == DEVELOPMENT_START_UTC
        assert spans["development_2025"]["end"] == DEVELOPMENT_END_UTC

    def test_the_protected_boundary_is_pinned_at_both_ends(self) -> None:
        from scripts.research.exploratory_m15 import FIRST_FORBIDDEN_UTC

        assert inventory.PROTECTED_SPANS["fresh_pool"]["start"] == "2016-06-02"
        assert inventory.PROTECTED_SPANS["fresh_pool"]["end"] == "2021-04-25"
        assert inventory.PROTECTED_SPANS["historical_oos_slice"]["start"] == FIRST_FORBIDDEN_UTC

    def test_the_pair_round_trip_is_the_midpoint_of_two_measured_figures(self) -> None:
        assert pytest.approx((2.6902 + 2.4660) / 2.0, abs=5e-3) == inventory.PAIR_ROUNDTRIP_BP

    def test_the_basket_exposure_is_the_measured_mean_not_its_minimum(self) -> None:
        """1.29 was the minimum, and its cell is the eleven-event one."""
        measured = [1.3283, 1.3310, 1.2884, 1.3263, 1.3356, 1.3059]
        assert pytest.approx(sum(measured) / len(measured), abs=5e-3) == inventory.BASKET_EXPOSURE
        assert min(measured) < inventory.BASKET_EXPOSURE
        assert inventory.BASKET_ROUNDTRIP_BP > inventory.PAIR_ROUNDTRIP_BP

    def test_the_dependence_shares_are_the_ones_the_candidates_use(self) -> None:
        used = {plan.effective_n_share for plan in inventory.catalogue()}
        assert used == {inventory.SHARE_CROSS_SECTIONAL, inventory.SHARE_CURRENCY_LEVEL}

    def test_the_catalogue_size_matches_its_own_docstring(self) -> None:
        assert len(inventory.catalogue()) == 22
        assert "Twenty-two" in (inventory.catalogue.__doc__ or "")
