"""The rerank and the feasibility, pinned so a later session cannot quietly widen them.

Every assertion here is about a judgement that was recorded, a closure scope that was
ruled, or a number that was measured. None of it reads market data.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest

from scripts.research.edge_sources import candidates, rerank
from scripts.research.edge_sources import feasibility_2026_09 as feasibility
from scripts.research.edge_sources.engineering_backlog import BACKLOG, ENGINEERING_FLOOR_IDENTIFIED
from scripts.research.market_yields import (
    FAMILY_BOUNDARY,
    FAMILY_CLOSURE_COVERS,
    FAMILY_CLOSURE_DOES_NOT_REACH,
    WORKFLOW_STATUS,
)

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/research/m15_candidate_rerank_2026_09.md"


@pytest.fixture(scope="module")
def document() -> str:
    return DOC.read_text(encoding="utf-8")


class TestEveryCandidateWasReassessed:
    def test_all_twenty_eight_are_covered(self) -> None:
        assert {c.cid for c in candidates.CANDIDATES} == set(rerank.REASSESSMENT)

    def test_each_reassessment_gives_a_reason(self) -> None:
        for cid, row in rerank.REASSESSMENT.items():
            assert row["why"].strip(), cid
            assert row["disposition"], cid
            assert row["name"], cid

    def test_the_two_executed_tracks_are_out(self) -> None:
        for cid in ("S01", "S13"):
            assert rerank.REASSESSMENT[cid]["disposition"] == rerank.CLOSED_BY_EXECUTION
            assert rerank.REASSESSMENT[cid]["rank"] is None
        #: and they were the old top two, so the rerank is not cosmetic
        assert rerank.REASSESSMENT["S01"]["old_rank"] == 1
        assert rerank.REASSESSMENT["S13"]["old_rank"] == 2

    def test_the_increments_of_a_closed_base_are_out(self) -> None:
        for cid in ("S08", "S16", "S17"):
            assert rerank.REASSESSMENT[cid]["disposition"] == rerank.DEPENDS_ON_A_CLOSED_BASE
            assert rerank.REASSESSMENT[cid]["rank"] is None

    def test_the_previously_excluded_stay_excluded(self) -> None:
        for cid in ("S09", "S11", "S19", "S21", "S23", "S24"):
            assert rerank.REASSESSMENT[cid]["disposition"] == rerank.STILL_EXCLUDED
        for cid in ("S18", "S20", "S22"):
            assert rerank.REASSESSMENT[cid]["disposition"] == rerank.BLOCKED_BY_DATA

    def test_the_ranking_is_a_strict_order(self) -> None:
        ranks = [rank for rank, _, _ in rerank.eligible()]
        assert ranks == sorted(ranks)
        assert len(ranks) == len(set(ranks))
        assert ranks[0] == 1


class TestTheEventTrackWasReassessedAndDeclined:
    """Section 15 asked for this specifically: is T-E a filter on a closed signal?"""

    def test_t_e_is_excluded_as_an_event_filter_on_a_closed_signal(self) -> None:
        for cid in ("S03", "S04"):
            row = rerank.REASSESSMENT[cid]
            assert row["disposition"] == rerank.EVENT_FILTER_ON_A_CLOSED_SIGNAL
            assert row["rank"] is None

    def test_the_decline_cites_the_measured_absence_of_a_cost_advantage(self) -> None:
        row = rerank.REASSESSMENT["S03"]
        text = row["and_the_opportunity_layer_was_already_measured"]
        #: H-018 and H-019 measured wider spreads and a cost-clearing rate of one
        assert "WIDER" in text
        assert "1.00" in text
        assert "nothing to point it at" in text

    def test_the_decline_names_the_power_ceiling_and_the_missing_currencies(self) -> None:
        power = rerank.REASSESSMENT["S03"]["power"]
        assert "34.4" in power
        for currency in ("GBP", "CAD", "NZD", "CHF"):
            assert currency in power
        assert rerank.REASSESSMENT["S03"]["verdict_token"] == (
            "EVENT_REPRICING_DATA_NOT_DECISION_GRADE"
        )

    def test_it_is_not_declined_by_calling_event_information_worthless(self) -> None:
        joined = " ".join(rerank.NOT_GENERALISED)
        assert "event information as a whole is hopeless" in joined


class TestTheClosureIsNotWidenedByTheRerank:
    def test_curve_shape_survives_because_the_ruling_left_it_open(self) -> None:
        assert "curve shape" in FAMILY_CLOSURE_DOES_NOT_REACH
        #: so S02 may not be excluded, and it is not
        assert rerank.REASSESSMENT["S02"]["rank"] is not None
        assert rerank.REASSESSMENT["S02"]["disposition"] == rerank.PENALISED

    def test_breakeven_is_inside_the_closure_and_says_why(self) -> None:
        row = rerank.REASSESSMENT["S28"]
        assert row["disposition"] == rerank.CLOSED_BY_FAMILY
        assert "difference of two public sovereign yields" in row["why"]
        assert "public daily sovereign-yield data" in FAMILY_CLOSURE_COVERS

    def test_the_track_status_is_the_declared_boundary(self) -> None:
        assert WORKFLOW_STATUS == FAMILY_BOUNDARY

    def test_nothing_is_generalised_beyond_what_was_closed(self) -> None:
        joined = " ".join(rerank.NOT_GENERALISED)
        for forbidden in (
            "rates as a whole",
            "valuation as a whole",
            "non-price information as a whole",
            "machine learning as a whole",
            "cross-asset as a whole",
            "cross-sectional construction as a whole",
        ):
            assert forbidden in joined, forbidden


class TestThePowerArithmeticIsWhatDrovetheRerank:
    def test_the_detectable_sharpe_formula(self) -> None:
        #: two-sided 5%, 80% power
        assert rerank.detectable_sharpe(1.0) == pytest.approx(2.8016, abs=1e-3)
        assert rerank.detectable_sharpe(4.0) == pytest.approx(rerank.detectable_sharpe(1.0) / 2)

    def test_the_seen_corpus_cannot_decide_a_realistic_edge(self) -> None:
        seen = rerank.SPANS["seen_m15_corpus"]
        assert seen["detectable_net_sharpe_at_80pct_power"] > 1.0
        #: which is why T-R and T-R2 settled nothing, and why span now outranks prior
        both = rerank.SPANS["both_disjoint_spans"]
        assert both["detectable_net_sharpe_at_80pct_power"] < 0.7
        assert both["years"] > 4 * seen["years"]

    def test_the_two_spans_are_disjoint_around_the_protected_pool(self) -> None:
        long_span = feasibility.FX_SPANS["long"]
        recent = feasibility.FX_SPANS["recent"]
        assert long_span["span"].endswith("2016-06-01")
        assert recent["span"].startswith("2021-04-27")
        #: the gap between them is the fresh pool and is not being read
        assert "2016-06-02" not in long_span["span"]
        assert pytest.approx(long_span["years"] + recent["years"], abs=1e-6) == (
            feasibility.TOTAL_YEARS
        )

    def test_cost_drag_rises_with_turnover(self) -> None:
        low = feasibility.cost_drag(8.0, feasibility.VOL_PER_UNIT_GROSS)
        high = feasibility.cost_drag(45.0, feasibility.VOL_PER_UNIT_GROSS)
        assert 0 < low < high
        #: the convention, stated once: two one-way legs per round trip
        assert low == pytest.approx(
            2 * 8.0 * feasibility.ONE_WAY_BP / 10_000.0 / feasibility.VOL_PER_UNIT_GROSS
        )

    def test_the_required_ic_rises_with_turnover(self) -> None:
        kwargs: dict[str, Any] = {
            "vol_per_unit_gross": feasibility.VOL_PER_UNIT_GROSS,
            "breadth": 2.5,
            "target_net": 0.3,
        }
        slow = feasibility.required_daily_ic(turnover_round_trips=8.0, **kwargs)
        fast = feasibility.required_daily_ic(turnover_round_trips=45.0, **kwargs)
        assert 0 < slow < fast
        assert math.isfinite(slow)


class TestTheFeasibilityIsSignalBlindAndMeasured:
    def test_reachability_was_measured_with_evidence(self) -> None:
        for host, row in feasibility.REACHABILITY.items():
            assert row["status"] in {"REACHABLE", "UNREACHABLE", "REACHABLE_BUT_NOT_USED"}, host
            assert row["evidence"].strip(), host

    def test_fred_is_recorded_unreachable_and_the_consequence_is_named(self) -> None:
        fred = feasibility.REACHABILITY["fred.stlouisfed.org"]
        assert fred["status"] == "UNREACHABLE"
        #: the point of recording it: the inventory's source list would have retired
        #: the whole cross-asset direction on an environment fault
        assert "cross-asset" in fred["consequence"]

    def test_the_primary_publishers_replace_it(self) -> None:
        for host in ("cdn.cboe.com", "www.eia.gov", "home.treasury.gov"):
            assert feasibility.REACHABILITY[host]["status"] == "REACHABLE"

    def test_the_redistributor_is_reachable_and_deliberately_unused(self) -> None:
        yahoo = feasibility.REACHABILITY["query1.finance.yahoo.com"]
        assert yahoo["status"] == "REACHABLE_BUT_NOT_USED"
        assert "section 41" in yahoo["consequence"]

    def test_every_assessment_states_a_decision_capability(self) -> None:
        allowed = {
            "DECISION_CAPABLE",
            "DECISION_CAPABLE_BUT_NARROW",
            "MARGINAL",
            "DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES",
        }
        for cid, row in feasibility.ASSESSMENTS.items():
            assert row["decision_capability"] in allowed, cid
            assert row["why"].strip(), cid
            assert row["timing_quality"].strip(), cid

    def test_the_lost_source_is_recorded_rather_than_wished_away(self) -> None:
        s07 = feasibility.ASSESSMENTS["S07"]
        assert s07["decision_capability"] == "DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES"
        assert "no free primary publisher" in s07["why"]


class TestThePaidDataAssessmentIsDesignOnly:
    def test_every_paid_row_carries_the_six_required_fields(self) -> None:
        for row in feasibility.PAID_DATA:
            for field in (
                "what",
                "provider",
                "rough_cost",
                "coverage",
                "hypothesis_enabled",
                "why_public_substitute_insufficient",
                "expected_information_gain",
            ):
                assert row[field].strip(), (row["id"], field)

    def test_the_costs_are_marked_as_estimates_not_quotes(self) -> None:
        for row in feasibility.PAID_DATA:
            cost = row["rough_cost"]
            assert "solicited" in cost, row["id"]
            assert "not quotes" in cost or "not solicited" in cost, row["id"]

    def test_the_open_rate_information_sets_are_the_paid_ones(self) -> None:
        #: what the closure left open is largely what costs money, and that is the point
        rates_row = next(r for r in feasibility.PAID_DATA if r["id"] == "rates-implied")
        assert "market-implied policy path" in rates_row["hypothesis_enabled"]
        assert "market-implied policy path" in FAMILY_CLOSURE_DOES_NOT_REACH

    def test_nothing_was_purchased(self, document: str) -> None:
        assert "購入しない" in document


class TestTheSelectionFollowsTheFeasibility:
    def test_two_tracks_are_selected_and_named(self) -> None:
        assert feasibility.SELECTED["track_a"] == "S05"
        assert feasibility.SELECTED["track_b"] == "S02"

    def test_both_selected_are_decision_capable(self) -> None:
        for cid in (feasibility.SELECTED["track_a"], feasibility.SELECTED["track_b"]):
            assert feasibility.ASSESSMENTS[cid]["decision_capability"] == "DECISION_CAPABLE"

    def test_both_selected_are_eligible_in_the_rerank(self) -> None:
        eligible = {cid for _, cid, _ in rerank.eligible()}
        assert feasibility.SELECTED["track_a"] in eligible
        assert feasibility.SELECTED["track_b"] in eligible

    def test_the_reason_for_two_rather_than_three_is_recorded(self) -> None:
        assert "does not require two" in feasibility.SELECTED["why_only_two"]
        #: the third was decision-capable but narrower, which is a reason not a dismissal
        assert feasibility.ASSESSMENTS["S06"]["decision_capability"] == (
            "DECISION_CAPABLE_BUT_NARROW"
        )

    def test_the_two_are_independent_information_sets(self) -> None:
        why = feasibility.SELECTED["why_these_two"]
        assert "independent" in why
        assert "neither needs the other's result" in why


class TestTheEngineeringBacklogIsParkedNotActioned:
    def test_the_turnover_floor_is_recorded_with_its_condition(self) -> None:
        entry = next(e for e in BACKLOG if e["id"] == "E-001")
        assert entry["status"] == ENGINEERING_FLOOR_IDENTIFIED
        assert "77%" in entry["finding"]
        assert "only once a candidate shows positive economics" in entry["when_it_may_be_worked_on"]

    def test_it_is_explicitly_not_a_rescue_of_the_track_that_found_it(self) -> None:
        entry = next(e for e in BACKLOG if e["id"] == "E-001")
        assert "did not fail on cost" in entry["not_a_rescue"]


class TestTheDocument:
    def test_it_records_the_span_finding_as_the_driver(self, document: str) -> None:
        assert "1.29" in document and "0.60" in document
        assert "span" in document

    def test_it_records_the_reachability_measurement(self, document: str) -> None:
        assert "UNREACHABLE" in document
        assert "cdn.cboe.com" in document
        assert "9,276" in document or "9276" in document

    def test_it_declines_t_e_with_the_section_15_reasoning(self, document: str) -> None:
        assert "EVENT_REPRICING_DATA_NOT_DECISION_GRADE" in document
        assert "nothing to point it at" in document

    def test_it_reassesses_s02_explicitly(self, document: str) -> None:
        assert "S02" in document
        assert "curve shape" in document

    def test_it_refuses_the_overgeneralisations(self, document: str) -> None:
        for phrase in ("rates 全部が無理", "cross-asset 全部が無理", "event 全部が無理"):
            assert phrase in document

    def test_it_names_the_selected_tracks(self, document: str) -> None:
        assert "Track A" in document and "Track B" in document
        assert "S05" in document and "S02" in document
