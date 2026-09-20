"""The rerank and the feasibility, pinned so a later session cannot quietly widen them.

Every assertion here is about a judgement that was recorded, a closure scope that was
ruled, or a number that was measured. None of it reads market data.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from scripts.research import continuous_portfolio
from scripts.research.edge_sources import candidates, capacity, rerank
from scripts.research.edge_sources import feasibility_2026_09 as feasibility
from scripts.research.edge_sources.engineering_backlog import BACKLOG, ENGINEERING_FLOOR_IDENTIFIED
from scripts.research.market_yields import (
    FAMILY_BOUNDARY,
    FAMILY_CLOSURE_COVERS,
    FAMILY_CLOSURE_DOES_NOT_REACH,
    FAMILY_CLOSURE_FORBIDS,
    WORKFLOW_STATUS,
)

ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT
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
        assert "difference of a nominal and an index-linked public sovereign yield" in row["why"]
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

    def test_the_constant_is_the_one_the_committed_gate_already_uses(self) -> None:
        """The rerank's headline arithmetic is not new; the gate carries it already."""
        from scripts.research.feasibility import inventory

        assessed = inventory._assess(inventory.catalogue()[0])
        assert assessed["power_multiplier"] == pytest.approx(
            rerank.detectable_sharpe(1.0), abs=1e-3
        )

    def test_power_at_reproduces_independently(self) -> None:
        """Pinned, because `detectable_sharpe` alone invites reading a span as usable."""
        pooled = rerank.SPANS["both_disjoint_spans"]["years"]
        assert rerank.power_at(0.2, pooled) == pytest.approx(0.16, abs=0.01)
        assert rerank.power_at(0.3, pooled) == pytest.approx(0.30, abs=0.01)
        assert rerank.power_at(0.5, pooled) == pytest.approx(0.66, abs=0.01)
        #: at the threshold the definition must return the power it was solved for
        assert rerank.power_at(rerank.detectable_sharpe(pooled), pooled) == pytest.approx(
            0.80, abs=0.01
        )
        #: two-sided means both tails: negligible at these effect sizes, so without
        #: this the lower tail can be dropped without any published number moving
        assert rerank.power_at(-0.3, pooled) == pytest.approx(rerank.power_at(0.3, pooled))
        assert rerank.power_at(0.0, pooled) == pytest.approx(0.05, abs=1e-6)

    def test_no_reachable_span_can_decide_a_realistic_edge(self) -> None:
        """The correction that matters: the long span does not fix the power problem."""
        seen = rerank.SPANS["seen_m15_corpus"]
        both = rerank.SPANS["both_disjoint_spans"]
        assert seen["detectable_net_sharpe_at_80pct_power"] == pytest.approx(1.28, abs=0.01)
        assert both["detectable_net_sharpe_at_80pct_power"] == pytest.approx(0.59, abs=0.01)
        #: 0.59 still sits inside a realistic 0.2-0.5 edge band, so by the module's own
        #: criterion the pooled span cannot decide it either
        assert both["detectable_net_sharpe_at_80pct_power"] > 0.5
        assert rerank.power_at(0.3, both["years"]) < 0.5
        assert capacity.sample_years_needed(0.3, 0.8) > both["years"]

    def test_the_day_counts_come_from_committed_records(self) -> None:
        """Both counts are pinned to the record that owns them, not retyped."""
        from scripts.research.market_yields import prereg

        assert rerank.RECENT_DECISION_DAYS == prereg.DECISION_DAYS
        panel = json.loads(
            (REPO_ROOT / "artifacts/research/valuation/development.json").read_text(
                encoding="utf-8"
            )
        )
        assert panel["return_panel_days"] == rerank.LONG_DECISION_DAYS

    def test_the_two_modules_cannot_drift_on_the_spans(self) -> None:
        """An earlier draft duplicated these as literals and they disagreed."""
        assert feasibility.FX_SPANS["long"]["trading_days"] == rerank.LONG_DECISION_DAYS
        assert feasibility.FX_SPANS["recent"]["trading_days"] == rerank.RECENT_DECISION_DAYS
        assert feasibility.FX_SPANS["long"]["years"] == rerank.SPANS["ecb_daily_fx"]["years"]
        assert feasibility.FX_SPANS["recent"]["years"] == rerank.SPANS["seen_m15_corpus"]["years"]
        assert rerank.SPANS["both_disjoint_spans"]["years"] == feasibility.TOTAL_YEARS

    def test_the_two_spans_are_disjoint_around_the_protected_pool(self) -> None:
        """Compared as parsed dates against the committed guard bounds.

        The earlier version asserted `"2016-06-02" not in span`, which is a substring
        fact about a literal the same commit wrote and holds for any string - the
        string-versus-parsed-date confusion this repo has closed three times.
        """
        from scripts.research.exploratory_m15 import momentum
        from scripts.research.valuation import sources

        long_first, long_last = (
            date.fromisoformat(part) for part in feasibility.FX_SPANS["long"]["span"].split(" .. ")
        )
        recent_first, recent_last = (
            date.fromisoformat(part)
            for part in feasibility.FX_SPANS["recent"]["span"].split(" .. ")
        )
        assert long_first < long_last < recent_first < recent_last
        #: the long span stops before the protected pool the valuation route guards
        assert long_last < date.fromisoformat(sources.PROTECTED_FROM)
        #: and the recent span starts no earlier than the earliest guarded M15 window
        assert recent_first >= date.fromisoformat(momentum.MOMENTUM_START_UTC)
        #: the gap between them is a real gap, not a rounding artefact
        assert (recent_first - long_last).days > 1_500

    def test_the_cost_table_is_pinned(self) -> None:
        """Every published drag figure, to the digit the document prints.

        A mutation audit showed the earlier version passing with `ONE_WAY_BP` at ten
        times the convention, because its only equality restated the function body
        from the same constants.
        """
        expected = {60: 0.123, 20: 0.267, 16: 0.308, 5: 0.634}
        for half_life, drag in expected.items():
            turnover = feasibility.turnover_for(half_life)
            assert feasibility.cost_drag(turnover) == pytest.approx(drag, abs=5e-4), half_life

    def test_the_required_ic_column_is_pinned(self) -> None:
        expected = {60: 0.0199, 20: 0.0271, 16: 0.0287, 5: 0.0444}
        for half_life, ic in expected.items():
            got = feasibility.required_daily_ic(
                half_life_days=half_life, breadth=2.5, target_net=0.3
            )
            assert got == pytest.approx(ic, abs=5e-5), half_life

    def test_the_cost_constants_are_the_committed_ones(self) -> None:
        """Bound to their sources, so a stray literal here cannot change the table."""
        assert feasibility.ONE_WAY_BP == continuous_portfolio.CHARGED_ONE_WAY_BP
        assert feasibility.VOL_PER_UNIT_GROSS == capacity.VOL_PER_UNIT_GROSS
        #: and the value an earlier draft used is recorded as the range top, not centre
        assert feasibility.VOL_PER_UNIT_GROSS < 0.030
        assert max(feasibility.VOL_PER_UNIT_GROSS_MEASURED.values()) > 0.030

    def test_the_band_law_is_not_re_derived_here(self) -> None:
        """The half-life inversion an earlier draft used was wrong by about 4x."""
        for half_life in (5, 16, 20, 60):
            assert feasibility.turnover_for(half_life) == capacity.band_law(half_life)["turnover"]
        #: turnover 8/yr is a ~60 day book, not the ~16 day book `252/turnover/2` claimed
        assert feasibility.turnover_for(16) == pytest.approx(21.06, abs=0.01)

    def test_the_arithmetic_refuses_impossible_inputs(self) -> None:
        with pytest.raises(ValueError):
            feasibility.cost_drag(-5.0)
        with pytest.raises(ValueError):
            feasibility.cost_drag(10.0, 0.0)

    def test_cost_drag_rises_with_turnover(self) -> None:
        assert 0 < feasibility.cost_drag(8.0) < feasibility.cost_drag(45.0)


class TestTheFeasibilityIsSignalBlindAndMeasured:
    def test_every_reachability_row_carries_both_observations(self) -> None:
        allowed = {
            feasibility.REACHABLE,
            feasibility.UNREACHABLE,
            feasibility.CONFLICTED,
            feasibility.UNVERIFIED,
            feasibility.THIS_ROUND_ONLY,
            "REACHABLE_BUT_NOT_USED",
        }
        for host, row in feasibility.REACHABILITY.items():
            assert row["status"] in allowed, host
            assert row["this_round"].strip(), host
            assert row["committed_probe"].strip(), host

    def test_this_rounds_observations_left_no_artefact_and_say_so(self) -> None:
        """No host is plain REACHABLE on this round's evidence alone."""
        for host, row in feasibility.REACHABILITY.items():
            if row["status"] == feasibility.REACHABLE:
                assert "agrees" in row["committed_probe"] or "T-V" in row["committed_probe"], host

    def test_the_conflict_matches_the_committed_artefact(self) -> None:
        """Read from the artefact, so the claim cannot drift away from the record."""
        probe = json.loads(
            (REPO_ROOT / "artifacts/research/edge_sources/public_data_availability.json").read_text(
                encoding="utf-8"
            )
        )
        #: every FRED series answered there, including the one S07 was retired for
        assert probe["fred"]["BAMLH0A0HYM2"]["http_status"] == 200
        assert {row["http_status"] for row in probe["fred"].values()} == {200}
        #: and the two curve publishers this round called reachable did not answer
        assert probe["other"]["bundesbank_statistics_api"]["http_status"] is None
        assert probe["other"]["snb_data_portal"]["http_status"] is None
        #: the VIX start date is the one claim both records agree on
        assert probe["fred"]["VIXCLS"]["declared_range"][0] == "1990-01-02"

    def test_no_candidate_is_retired_on_the_unreproduced_observation(self) -> None:
        s07 = feasibility.ASSESSMENTS["S07"]
        assert s07["decision_capability"] == feasibility.DATA_UNRESOLVED
        assert "200" in s07["data"]

    def test_the_redistributor_is_reachable_and_deliberately_unused(self) -> None:
        yahoo = feasibility.REACHABILITY["query1.finance.yahoo.com"]
        assert yahoo["status"] == "REACHABLE_BUT_NOT_USED"
        assert "section 41" in yahoo["consequence"]

    def test_the_impossible_coverage_count_is_withdrawn_not_repaired(self) -> None:
        """1,389 daily closes cannot fit in a span holding 1,219 weekdays."""
        coverage = feasibility.ASSESSMENTS["S05"]["coverage"]
        assert "withdrawn" in coverage
        assert not any(isinstance(v, int) for v in coverage.values())
        assert "1,389" in coverage["withdrawn"]

    def test_no_stated_day_count_exceeds_its_own_span(self) -> None:
        """The bound the withdrawn count never had."""
        for key in ("long", "recent"):
            span = feasibility.FX_SPANS[key]
            first, last = (date.fromisoformat(p) for p in span["span"].split(" .. "))
            weekdays = sum(
                1
                for n in range((last - first).days + 1)
                if (first + timedelta(days=n)).weekday() < 5
            )
            assert span["trading_days"] <= weekdays, key

    def test_every_assessment_states_a_decision_capability(self) -> None:
        allowed = {
            feasibility.BEST_AVAILABLE_BUT_UNDERPOWERED,
            feasibility.NARROW,
            feasibility.MARGINAL,
            feasibility.DATA_UNRESOLVED,
        }
        for cid, row in feasibility.ASSESSMENTS.items():
            assert row["decision_capability"] in allowed, cid
            assert row["why"].strip(), cid
            assert row["timing_quality"].strip(), cid

    def test_nothing_is_stamped_decision_capable(self) -> None:
        """It was, and it did not survive the module own criterion."""
        for cid, row in feasibility.ASSESSMENTS.items():
            assert not row["decision_capability"].startswith("DECISION_CAPABLE"), cid
        assert "none_are_decision_capable" in feasibility.summary()

    def test_the_committed_gate_is_reconciled_rather_than_ignored(self) -> None:
        """Re-run, not cited from memory: span is not the binding constraint there."""
        from scripts.research.feasibility import inventory

        by_id = {p.candidate_id: p for p in inventory.catalogue()}
        pooled_panel = feasibility.TOTAL_YEARS / inventory.MIN_DECIDING_PANELS
        for plan_id, recorded in feasibility.COMMITTED_GATE_AT_THE_POOLED_PANEL.items():
            if plan_id == "what_it_means":
                continue
            plan = by_id[plan_id]
            got = inventory._assess(dataclasses.replace(plan, panel_years=pooled_panel))
            assert got["verdict"] in recorded, plan_id
            assert got["binding_constraint"] in recorded, plan_id
            #: and none of them is short of span at that length
            if got["verdict"] == "PASS_REGION_EXISTS":
                assert got["years_short"] == 0.0, plan_id


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
    def test_two_are_selected_and_named(self) -> None:
        assert feasibility.SELECTED["lead"] == "S05"
        assert feasibility.SELECTED["second"] == "S02"

    def test_the_frozen_two_track_vocabulary_is_not_reused(self) -> None:
        """In this repo Track B IS Formal Confirmation, on UNSEEN forward data.

        Both spans here are already seen, so neither selection can ever be one. An
        earlier draft called these Track A and Track B, which read as though one could.
        """
        assert "track_a" not in feasibility.SELECTED
        assert "track_b" not in feasibility.SELECTED
        assert feasibility.SELECTED["both_are"] == (
            "EXPLORATORY_ON_SEEN_DATA_NEITHER_IS_A_FORMAL_CONFIRMATION"
        )

    def test_neither_selection_is_claimed_to_be_decidable(self) -> None:
        for cid in (feasibility.SELECTED["lead"], feasibility.SELECTED["second"]):
            assert feasibility.ASSESSMENTS[cid]["decision_capability"] == (
                feasibility.BEST_AVAILABLE_BUT_UNDERPOWERED
            )
        not_a_pass = feasibility.SELECTED["what_this_selection_is_not"]
        assert "not a finding that either can be decided" in not_a_pass
        assert "UNRESOLVED" in not_a_pass

    def test_both_selected_are_eligible_in_the_rerank(self) -> None:
        eligible = {cid for _, cid, _ in rerank.eligible()}
        assert feasibility.SELECTED["lead"] in eligible
        assert feasibility.SELECTED["second"] in eligible

    def test_the_reason_for_two_rather_than_three_is_recorded(self) -> None:
        assert "does not require two" in feasibility.SELECTED["why_only_two"]
        #: the third is narrower on breadth, which is a reason and not a dismissal
        assert feasibility.ASSESSMENTS["S06"]["decision_capability"] == feasibility.NARROW

    def test_the_two_are_independent_information_sets(self) -> None:
        why = feasibility.SELECTED["why_these_two"]
        assert "independent" in why
        assert "neither needs the other's result" in why

    def test_seen_is_not_permission_to_read_again(self) -> None:
        """A recorded state is not an act; CLAUDE.md is explicit about this."""
        assert feasibility.RE_READ_REQUIRES == ("EXPLICIT_HUMAN_AND_CHATGPT_AUTHORISATION_PER_READ")


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
        assert "1.28" in document and "0.59" in document
        assert "22.50" in document or "22.5 " in document

    def test_it_states_that_the_long_span_still_cannot_decide(self, document: str) -> None:
        """The correction the review forced: it is not a pass, and it says so."""
        assert "87.2" in document and "68.7" in document
        assert "0.30" in document
        assert "DECISION_CAPABLE` はどの候補にも付かない" in document

    def test_it_records_the_reachability_conflict_rather_than_a_measurement(
        self, document: str
    ) -> None:
        assert "CONFLICTED" in document
        assert "public_data_availability.json" in document
        assert "BAMLH0A0HYM2" in document
        #: the impossible count is withdrawn in the document too, with its arithmetic
        assert "1,389" in document and "1,219" in document

    def test_it_flags_that_the_ruling_itself_is_not_committed(self, document: str) -> None:
        assert "裁定そのものは repo に入っていない" in document

    def test_it_declines_t_e_with_the_section_15_reasoning(self, document: str) -> None:
        assert "EVENT_REPRICING_DATA_NOT_DECISION_GRADE" in document
        assert "nothing to point it at" in document

    def test_it_reassesses_s02_explicitly(self, document: str) -> None:
        assert "S02" in document
        assert "curve shape" in document

    def test_it_refuses_the_overgeneralisations(self, document: str) -> None:
        for phrase in ("rates 全部が無理", "cross-asset 全部が無理", "event 全部が無理"):
            assert phrase in document

    def test_it_names_the_selected_two_without_the_frozen_vocabulary(self, document: str) -> None:
        assert "LEAD" in document and "SECOND" in document
        assert "S05" in document and "S02" in document
        #: Track A / Track B appear only where the document explains why it avoids them
        assert document.count("Track A") <= 2


class TestTheClosureDoesNotDoTheRankingsWork:
    """The closure is scope-limited, so it may not quietly select candidates either."""

    def test_every_exclusion_declares_what_it_rests_on(self) -> None:
        excluded = {cid for cid, _, _ in rerank.removed()}
        for cid in rerank.EXCLUSION_BASIS:
            assert cid in excluded, cid

    def test_event_conditioning_is_not_in_the_forbidden_list(self) -> None:
        """So S03 cannot be excluded by calling it an application of the closure."""
        forbidden = " ".join(FAMILY_CLOSURE_FORBIDS).lower()
        assert "event" not in forbidden
        assert rerank.EXCLUSION_BASIS["S03"].startswith("judgement")
        assert rerank.EXCLUSION_BASIS["S04"].startswith("judgement")

    def test_the_event_exclusion_says_it_is_reopenable(self) -> None:
        rests_on = rerank.REASSESSMENT["S03"]["what_this_exclusion_rests_on"]
        assert "A JUDGEMENT, NOT THE CLOSURE" in rests_on
        assert "may take it up again" in rests_on

    def test_the_asymmetry_between_s28_and_s02_is_named_not_assumed(self) -> None:
        """Both are differences of sovereign yields; one is closed and one is not."""
        assert rerank.EXCLUSION_BASIS["S28"].startswith("the closure")
        why_not = rerank.REASSESSMENT["S02"]["why_not_excluded_like_s28"]
        assert "curve shape" in why_not
        #: and the consistent resolution runs the safe way round
        assert "take S28 up again" in why_not
        #: curve shape is enumerated as out of reach; breakevens are not
        assert "curve shape" in FAMILY_CLOSURE_DOES_NOT_REACH


class TestTheCostConventionIsNotSilentlyPooled:
    def test_the_span_local_cost_is_recorded_as_an_assumption(self) -> None:
        assert feasibility.COST_CONVENTION_IS_SPAN_LOCAL == (
            "CHARGED_COST_MEASURED_ON_2021_2025_OANDA_NOT_ESTABLISHED_FOR_THE_1999_2016_SPAN"
        )

    def test_the_document_says_what_a_prereg_must_do_about_it(self, document: str) -> None:
        assert "COST_CONVENTION_IS_SPAN_LOCAL" in document
        assert "黙って pooled にしてはならない" in document


class TestTheSiblingTrackStatusesArePropagated:
    def test_the_valuation_track_carries_its_adopted_status(self) -> None:
        """An earlier state left this at DEVELOPMENT_IN_PROGRESS after the ruling."""
        from scripts.research import valuation

        assert valuation.WORKFLOW_STATUS == (
            "REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT"
        )
        assert valuation.WORKFLOW_STATUS in valuation.OUTCOMES


def _table_rows(document: str, heading: str) -> list[list[str]]:
    """Every markdown table row under `heading`, as stripped cells."""
    section = document.split(heading, 1)[1]
    rows = []
    for line in section.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("|"):
            if rows:
                break
            continue
        cells = [c.strip().strip("*").strip() for c in stripped.strip("|").split("|")]
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        rows.append(cells)
    return rows


class TestTheDocumentsNumbersComeFromTheCode:
    """Parsed out of the document and compared to the modules.

    A mutation audit showed every published figure surviving, because the assertions
    were `"0.59" in document` and that substring occurs in several places. These
    read the actual table cells instead, so changing one changes a test.
    """

    def test_the_span_table_matches_the_module(self, document: str) -> None:
        rows = _table_rows(document, "| span | decision days | 年数 |")
        assert len(rows) == 3, rows  # the heading itself is consumed by the split
        by_days = {
            int(r[1].replace(",", "")): (float(r[2]), float(r[3]), float(r[4])) for r in rows
        }
        for span in rerank.SPANS.values():
            years, detectable, power = by_days[span["decision_days"]]
            assert years == span["years"]
            assert detectable == span["detectable_net_sharpe_at_80pct_power"]
            assert power == span["power_at_true_sharpe_0_3"]

    def test_the_cost_table_matches_the_module(self, document: str) -> None:
        rows = _table_rows(document, "| half-life | turnover (RT/年) | cost drag (IR) |")
        assert len(rows) == 4, rows
        for row in rows:
            half_life = float(row[0].replace(" 日", ""))
            turnover, drag, ic = float(row[1]), float(row[2]), float(row[3].rstrip("%"))
            assert turnover == pytest.approx(feasibility.turnover_for(half_life), abs=5e-3)
            assert drag == pytest.approx(feasibility.cost_drag(turnover), abs=5e-4)
            assert ic / 100.0 == pytest.approx(
                feasibility.required_daily_ic(
                    half_life_days=half_life, breadth=2.5, target_net=0.3
                ),
                abs=5e-5,
            )

    def test_the_capability_table_carries_the_module_tokens(self, document: str) -> None:
        rows = _table_rows(document, "| ID | verdict | 根拠 |")
        verdicts = {row[0]: row[1].strip("`") for row in rows}
        for cid in ("S05", "S02", "S06", "S07"):
            assert verdicts[cid].startswith(
                feasibility.ASSESSMENTS[cid]["decision_capability"][:20]
            ), cid
        #: and the one that must never come back
        assert not any(v.startswith("DECISION_CAPABLE") for v in verdicts.values())

    def test_the_headings_that_carry_the_conclusion_are_intact(self, document: str) -> None:
        """Each of these was negatable without a test noticing."""
        assert "### ただし、長い span はこれを解決しない" in document
        assert "## 2. reachability は**未解決**である" in document
        assert "- reachability は**測定済みではない**。" in document
        assert "- `DECISION_CAPABLE` な候補は**存在しない**。" in document

    def test_the_breadth_penalty_is_the_arithmetic_it_claims(self, document: str) -> None:
        ratio = (
            feasibility.ASSESSMENTS["S05"]["breadth"] / feasibility.ASSESSMENTS["S06"]["breadth"]
        ) ** 0.5
        assert f"{round((ratio - 1) * 100)}%" == "29%"
        assert "約 29% 増" in document


class TestTheSpansAreBoundToTheirCommittedConstants:
    """The span strings were retyped literals, so an upper bound could drift.

    That is exactly the shape of the withdrawn 1,389 count: an end date that ran past
    the span, across the fresh pool, the OOS slice and the forward epoch.
    """

    def test_the_recent_span_is_the_pre_registered_decision_span(self) -> None:
        from scripts.research.market_yields import prereg

        assert feasibility.FX_SPANS["recent"]["span"] == (
            f"{prereg.DECISION_SPAN['first']} .. {prereg.DECISION_SPAN['last']}"
        )

    def test_the_long_span_is_the_valuation_request_window(self) -> None:
        from scripts.research.valuation import sources

        assert feasibility.FX_SPANS["long"]["span"] == (
            f"{sources.REQUEST_START} .. {sources.REQUEST_END}"
        )

    def test_neither_span_reaches_the_protected_pool(self) -> None:
        from scripts.research.valuation import sources

        protected = date.fromisoformat(sources.PROTECTED_FROM)
        for key in ("long", "recent"):
            first, last = (
                date.fromisoformat(p) for p in feasibility.FX_SPANS[key]["span"].split(" .. ")
            )
            assert first <= last
            if key == "long":
                assert last < protected
            else:
                assert first > protected
        #: and the recent span ends where the record says it ends, not at a request date
        assert feasibility.FX_SPANS["recent"]["span"].endswith("2025-12-26")


class TestTheReachabilityEvidenceClassesAreHonest:
    def test_a_tls_failure_is_not_recorded_as_a_contradiction(self) -> None:
        """The committed artefact's own note forbids that reading."""
        probe = json.loads(
            (REPO_ROOT / "artifacts/research/edge_sources/public_data_availability.json").read_text(
                encoding="utf-8"
            )
        )
        assert "not unavailable" in probe["note"]
        for host in ("api.statistiken.bundesbank.de", "data.snb.ch"):
            assert feasibility.REACHABILITY[host]["status"] == feasibility.UNVERIFIED, host

    def test_only_genuine_disagreements_are_conflicted(self) -> None:
        conflicted = {
            h for h, r in feasibility.REACHABILITY.items() if r["status"] == feasibility.CONFLICTED
        }
        assert conflicted == {"fred.stlouisfed.org", "home.treasury.gov"}

    def test_hosts_the_probe_never_covered_are_not_called_reachable(self) -> None:
        """Absence of contradiction is not corroboration."""
        for host in ("cdn.cboe.com", "www.eia.gov", "stats.bis.org"):
            assert feasibility.REACHABILITY[host]["status"] == feasibility.THIS_ROUND_ONLY, host
        assert feasibility.summary()["reachable"] == [
            "data-api.ecb.europa.eu",
            "www.bankofcanada.ca",
        ]

    def test_the_unsupported_series_start_is_not_asserted(self) -> None:
        assert "1986" not in feasibility.ASSESSMENTS["S06"]["data"]
        assert "1987-05-20" in feasibility.REACHABILITY["www.eia.gov"]["consequence"]


class TestTheTestConventionIsStatedOnce:
    def test_the_module_says_which_side_it_tests(self) -> None:
        assert "two-sided" in rerank.SPANS["seen_m15_corpus"]["convention"]
        #: and names the committed one-sided figure for the same span rather than hiding it
        assert "1.13" in rerank.SPANS["seen_m15_corpus"]["convention"]

    def test_the_one_sided_helper_is_not_quoted_as_if_two_sided(self) -> None:
        from scripts.research.edge_sources import capacity

        one_sided = capacity.sample_years_needed(0.3, 0.8)
        two_sided = ((1.959963985 + 0.841621234) / 0.3) ** 2
        assert one_sided == pytest.approx(68.7, abs=0.05)
        assert two_sided == pytest.approx(87.2, abs=0.05)
        assert "87.2" in rerank.__doc__
        assert "68.7" in rerank.__doc__
