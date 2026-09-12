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

    def test_the_suspended_clock_family_is_not_revived(self) -> None:
        """Track 1 is frozen; a benchmark-fix or month-end candidate is closed."""
        closed = {
            plan.candidate_id
            for plan in inventory.catalogue()
            if plan.prior_verdict == Verdict.PRIOR_FAMILY_CLOSED.value
        }
        assert "C04_benchmark_fix_flow" in closed
        assert "C05_month_end_rebalancing_flow" in closed


class TestNoSignalContamination:
    def test_the_package_cannot_open_a_market_data_file(self) -> None:
        """Read the source rather than trusting the docstring."""
        source = (ROOT / "scripts/research/feasibility/inventory.py").read_text(
            encoding="utf-8"
        ) + (ROOT / "scripts/research/feasibility/preflight.py").read_text(encoding="utf-8")
        for forbidden in ("read_parquet", "read_csv", "urlopen", "load_panel", "open("):
            assert forbidden not in source, forbidden

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

    def test_more_history_would_open_a_pass_region(self, record: dict[str, Any]) -> None:
        assert record["additional_history_would_open_a_pass_region"] is True
        assert record["horizon_counterfactuals"]["with_the_fresh_pool_split_in_two"][
            "horizon_condition_can_be_met"
        ]

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

    def test_a_high_frequency_candidate_is_stopped_by_cost_as_well(
        self, record: dict[str, Any]
    ) -> None:
        """The frequency ceiling is a real constraint, not decoration."""
        by_id = {block["candidate_id"]: block for block in record["candidates"]}
        session = by_id["C03_session_handover_relative"]
        assert session["conditions"]["economic_net_under_stress"] is False
        assert session["binding_constraint"] == "economic_net_under_stress"

    def test_a_rare_candidate_is_stopped_by_the_event_floor_as_well(
        self, record: dict[str, Any]
    ) -> None:
        by_id = {block["candidate_id"]: block for block in record["candidates"]}
        decisions = by_id["C01_central_bank_decision_response"]
        assert decisions["conditions"]["event_floor"] is False


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
        assert committed["status"] == record["status"]
        assert committed["by_verdict"] == record["by_verdict"]


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
