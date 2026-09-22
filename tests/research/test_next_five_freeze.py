"""次の 5 本の inventory / ranking / freeze を固定する。

**前 cycle で壊れたところを、今回は test で押さえる。**

- 凍結語彙に無い status を作れないこと
- gate を「通った」だけで進めないこと（帰無通過率ごと凍結されていること）
- nuisance 定数が primary と感度集合の両方を持つこと
- 選定が **点数より先に hard filter で効く**こと
- 実行済み 5 本が次の execution set に入らないこと
"""

from __future__ import annotations

import pytest

from scripts.research.edge_sources import candidates as edge_candidates
from scripts.research.next_five import inventory, prereg, ranking


class TestTheInventoryCoversEverything:
    def test_every_known_candidate_is_classified(self) -> None:
        coverage = inventory.coverage()
        assert coverage["complete"], coverage["missing_from_classification"]
        assert coverage["classified"] == len({c.cid for c in edge_candidates.CANDIDATES})

    def test_every_bucket_the_ruling_named_exists(self) -> None:
        buckets = inventory.classify()
        assert set(buckets) == set(inventory.CLASSES)

    def test_the_five_just_executed_are_not_runnable_again(self) -> None:
        excluded = inventory.excluded_from_next_execution()
        for cid in inventory.EXECUTED_IN_TOP_FIVE:
            assert cid in excluded, cid
        for cid in inventory.EXECUTED_EARLIER:
            assert cid in excluded, cid

    def test_t5_is_recorded_as_positive_but_not_decision_grade(self) -> None:
        row = inventory.CLASSIFICATION["S26"]
        assert row["klass"] == "POSITIVE_EXPLORATORY_NOT_DECISION_GRADE"
        #: **family closure にはしない**（裁定 §C）。
        assert "閉じていない" in row["family_not_closed"]

    def test_the_four_negatives_are_recorded_as_not_supported(self) -> None:
        for cid in ("S05", "S06", "S02", "S10"):
            assert inventory.CLASSIFICATION[cid]["klass"] == "NOT_SUPPORTED", cid

    def test_the_forbidden_generalisations_are_listed_so_they_can_be_checked(self) -> None:
        blob = " ".join(inventory.FORBIDDEN_GENERALISATIONS)
        for token in ("high-turnover", "cross-asset", "event", "flow", "rates"):
            assert token in blob, token

    def test_what_the_cycle_showed_is_scoped_to_what_was_tested(self) -> None:
        text = inventory.WHAT_THE_CYCLE_ACTUALLY_SHOWED
        assert "救済実験には使わない" in text
        #: 一般化を書いていないこと。
        assert "全部だめ" not in text

    def test_new_candidates_declare_why_they_are_distinct(self) -> None:
        for cid, row in inventory.NEW_CANDIDATES.items():
            assert "why_distinct" in row, cid
            assert row["mechanism"]
            assert "data_risk" in row, cid


class TestTheSelectionIsFilterFirst:
    def test_hard_filters_beat_scores(self) -> None:
        """**S14 は点数では S12 より上だが、rename filter で落ちる。**"""
        assert ranking._total("S14") > ranking._total("S12")
        assert not ranking.passes_filters("S14")
        assert "S14" not in ranking.execution_set()

    def test_the_rename_failure_names_the_prior_track(self) -> None:
        assert "Track 1" in ranking.SCORES["S14"]["filter_failure"]

    def test_exactly_five_are_selected_and_all_pass_filters(self) -> None:
        chosen = ranking.execution_set()
        assert len(chosen) == ranking.EXECUTION_SET_SIZE
        assert all(ranking.passes_filters(cid) for cid in chosen)

    def test_the_tiebreak_is_declared_and_actually_decided_something(self) -> None:
        """S07 と S15 は同点。**事前に決めた次元 2 で割れている。**"""
        assert ranking.TIEBREAK == "incremental_information_beyond_fx_price"
        assert ranking._total("S07") == ranking._total("S15")
        index = ranking.DIMENSIONS.index(ranking.TIEBREAK)
        assert ranking.SCORES["S07"]["scores"][index] > ranking.SCORES["S15"]["scores"][index]
        assert "S07" in ranking.execution_set()
        assert "S15" not in ranking.execution_set()

    def test_every_dimension_the_ruling_named_is_scored(self) -> None:
        assert len(ranking.DIMENSIONS) == 10
        for cid, row in ranking.SCORES.items():
            assert len(row["scores"]) == len(ranking.DIMENSIONS), cid
            assert all(ranking.SCALE[0] <= s <= ranking.SCALE[1] for s in row["scores"]), cid

    def test_slow_by_mechanism_is_distinguished_from_slow_by_smoothing(self) -> None:
        """**low turnover 自体を alpha source にしない**（裁定 §E の但し書き）。"""
        persistence = ranking.DIMENSIONS.index("natural_signal_persistence")
        for cid, row in ranking.SCORES.items():
            if not row["persistence_is_mechanistic"]:
                assert row["scores"][persistence] <= 3, cid

    def test_the_counterfactual_without_new_candidates_is_recorded(self) -> None:
        """新候補を足したことが結論を作っていないか、読む人が確かめられること。"""
        counterfactual = ranking.counterfactual_without_new_candidates()
        assert counterfactual["pool_size"] == 5
        assert "選択肢を作るため" in counterfactual["reading"]

    def test_the_selection_is_declared_signal_blind(self) -> None:
        assert ranking.summary()["signal_blind"].startswith("NO_ALPHA_SEEN")


class TestTheFreezeIsWhatItSaysItIs:
    def test_exactly_five_tracks_in_a_fixed_order(self) -> None:
        assert len(prereg.TRACKS) == 5
        assert tuple(prereg.TRACKS) == prereg.EXECUTION_ORDER

    def test_the_tracks_are_the_ones_the_ranking_chose(self) -> None:
        chosen = {spec["candidate"] for spec in prereg.TRACKS.values()}
        assert chosen == set(ranking.execution_set())

    def test_every_track_fixes_everything_the_ruling_listed(self) -> None:
        for track, spec in prereg.TRACKS.items():
            for field in (
                "mechanism",
                "data",
                "frequency",
                "primary_span",
                "publication_lag",
                "signal",
                "direction",
                "horizon",
                "why_it_is_not_a_rename",
                "declared_expectation",
            ):
                assert spec.get(field), f"{track}.{field}"

    def test_the_digest_moves_when_any_public_constant_moves(self) -> None:
        before = prereg.freeze_digest()
        original = prereg.BOOK_CONFIG["band"]
        try:
            prereg.BOOK_CONFIG["band"] = 0.42
            assert prereg.freeze_digest() != before
        finally:
            prereg.BOOK_CONFIG["band"] = original
        assert prereg.freeze_digest() == before

    def test_the_digest_covers_the_gates_and_the_nuisance_sets(self) -> None:
        """**事後に緩めたくなるものほど digest の内側へ入れる。**"""
        before = prereg.freeze_digest()
        for container, key, replacement in (
            (prereg.ADVANCE_GATE, "expected_null_pass_rate", 0.5),
            (prereg.NUISANCE_CONSTANTS["max_staleness_days"], "primary", 999),
            (prereg.DEMOTED_GATE, "status", "A_HARD_GATE"),
        ):
            original = container[key]
            try:
                container[key] = replacement
                assert prereg.freeze_digest() != before, key
            finally:
                container[key] = original
        assert prereg.freeze_digest() == before

    def test_no_status_outside_the_frozen_vocabulary(self) -> None:
        with pytest.raises(ValueError):
            prereg.track_status("U1", "LOOKS_PROMISING")

    def test_the_status_carries_track_and_candidate(self) -> None:
        assert prereg.track_status("U1", "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT").startswith("U1_S29_")


class TestTheGateWasRedesignedTheWayTheRulingAsked:
    def test_the_old_triple_is_demoted_not_reused(self) -> None:
        assert prereg.DEMOTED_GATE["status"] == "DEMOTED_TO_DIAGNOSTIC_NOT_A_SELECTION_GATE"
        assert prereg.DEMOTED_GATE["measured_null_pass_rate"] == 0.42
        assert prereg.DEMOTED_GATE["still_reported"].startswith("YES")

    def test_the_advance_gate_is_a_separation_test_not_a_sign_triple(self) -> None:
        gate = prereg.ADVANCE_GATE
        assert gate["id"] == "PERMUTATION_SEPARATION"
        joined = " ".join(gate["conditions"])
        assert "permutation p ≤ 0.05" in joined
        assert gate["expected_null_pass_rate"] <= 0.05
        assert gate["must_be_measured_at_freeze"] is True

    def test_the_null_is_a_circular_shift_not_a_shuffle(self) -> None:
        permutation = prereg.ADVANCE_GATE["permutation"]
        assert permutation["method"].startswith("CIRCULAR_SHIFT")
        assert "turnover" in permutation["why_not_shuffle"]

    def test_the_five_way_multiplicity_is_stated_before_results(self) -> None:
        """**1 本通ったことを『edge が見つかった』と書かない**ための事前宣言。"""
        assert "23%" in prereg.ADVANCE_GATE["multiplicity"]

    def test_nonlinear_ml_is_excluded_from_stage_two(self) -> None:
        assert "非線形 ML は禁止" in prereg.ADVANCE_GATE["model_if_passed"]


class TestNuisanceConstantsAreFrozenWithTheirSensitivity:
    def test_every_nuisance_constant_has_a_primary_and_a_set(self) -> None:
        for name, row in prereg.NUISANCE_CONSTANTS.items():
            assert "primary" in row, name
            assert len(row["sensitivity_set"]) >= 3, name
            assert row["primary"] in row["sensitivity_set"], name
            assert row["why_it_has_no_economic_content"], name

    def test_the_rule_forbids_picking_the_best_point_afterwards(self) -> None:
        assert "post-hoc" in prereg.NUISANCE_RULE
        assert "最大" in prereg.NUISANCE_RULE


class TestTheCycleDoesNotRescueThePreviousOne:
    def test_the_forbidden_rescues_name_every_prior_track(self) -> None:
        blob = " ".join(prereg.FORBIDDEN_RESCUES)
        for token in ("T1", "T2", "T3", "T4", "horizon smoothing", "T5 の追加実行"):
            assert token in blob, token

    def test_protected_data_stays_protected(self) -> None:
        assert prereg.PROTECTED_BOUNDS["fresh_pool"]["first"] == "2016-06-02"
        assert prereg.PROTECTED_BOUNDS["fresh_pool"]["last"] == "2021-04-25"
        for key in ("historical_oos", "dead_window", "forward_epoch"):
            assert key in prereg.PROTECTED_BOUNDS

    def test_no_sixth_track_and_no_automatic_escalation(self) -> None:
        blob = " ".join(prereg.FORBIDDEN_NEXT_STEPS)
        for token in ("6 本目", "fresh pool", "paid data", "nonlinear ML", "paper-forward"):
            assert token in blob, token

    def test_the_constant_dollar_null_is_in_the_benchmarks_from_the_start(self) -> None:
        """前 cycle では結果を見た後に足した。**今回は凍結時点で入れる。**"""
        assert "constant_long_usd" in prereg.BENCHMARKS

    def test_there_are_no_book_config_deviations_this_cycle(self) -> None:
        """T5 の breadth 1 は `neutralize_leading_factor=False` と表裏だった。"""
        assert prereg.BOOK_CONFIG_DEVIATIONS == {}

    def test_leverage_keeps_the_three_concepts_separate(self) -> None:
        why = prereg.BOOK_CONFIG["why_max_leverage_is_not_5"]
        assert "hard limit として使うことは禁じられている" in why
        assert "risk budget ではない" in why
        forbidden = " ".join(prereg.CAPACITY_REPORTING["forbidden"])
        assert "5x" in forbidden and "20x" in forbidden


class TestThePrimarySpanRuleAnswersThePreviousFailure:
    def test_slow_signals_are_judged_on_the_long_span(self) -> None:
        for track, spec in prereg.TRACKS.items():
            if spec["frequency"] in {"monthly", "weekly_to_monthly"}:
                assert spec["primary_span"] == "long", track

    def test_daily_signals_are_judged_where_cost_was_measured(self) -> None:
        for track, spec in prereg.TRACKS.items():
            if spec["frequency"] == "daily":
                assert spec["primary_span"] == "recent", track
        assert prereg.COST["measured_on"] == "recent span のみ"

    def test_the_rule_cites_the_measurement_that_motivated_it(self) -> None:
        why = prereg.PRIMARY_SPAN_RULE["why"]
        assert "24" in why and "1.321" in why
        assert prereg.PRIMARY_SPAN_RULE["both_always_reported"] == "YES"

    def test_the_long_span_net_carries_its_cost_caveat(self) -> None:
        assert "実測されていない" in prereg.PRIMARY_SPAN_RULE["cost_caveat"]


class TestTheRenameGatesArePreRegistered:
    def test_the_track_whose_direction_matches_a_closed_one_is_gated(self) -> None:
        """**S07 は S05 と同じ『risk-off → 安全通貨』の向きを持つ。**"""
        gate = prereg.RENAME_GATES["S07"]
        assert "S05" in gate["comparator"]
        assert gate["threshold"] == 0.8
        assert gate["if_exceeded"].startswith("RENAME_OF_A_CLOSED_TRACK")

    def test_the_flow_tracks_must_prove_they_differ(self) -> None:
        assert "S26" in prereg.RENAME_GATES["S31"]["comparator"]
        assert "S31" in prereg.RENAME_GATES["S25"]["comparator"]

    def test_rename_is_an_available_verdict(self) -> None:
        assert "RENAME_OF_A_CLOSED_TRACK" in prereg.TRACK_STATUS_SUFFIXES


class TestTheDeclaredWeaknessesAreOnTheRecordBeforeResults:
    def test_u4_declares_its_breadth_problem_in_advance(self) -> None:
        declared = prereg.TRACKS["U4"]["declared_expectation"]
        assert "breadth が小さい" in declared
        assert "T5" in declared

    def test_u3_declares_it_is_most_likely_to_fail_stage_zero(self) -> None:
        assert "Stage 0 で落ちる公算が最も高い" in prereg.TRACKS["U3"]["declared_expectation"]

    def test_u5_declares_it_is_the_weakest_of_the_five(self) -> None:
        assert "最も不利" in prereg.TRACKS["U5"]["declared_expectation"]

    def test_u1_carries_the_revision_caveat_the_previous_cycle_learned(self) -> None:
        caveat = prereg.TRACKS["U1"]["revision_caveat"]
        assert "改訂" in caveat
        assert "公表 lag 規約はこれを直さない" in caveat


class TestStageZeroDistinguishesUnreachableFromAbsent:
    """**「到達できない」と「存在しない」を混ぜない。**

    前 cycle は S07 をこの取り違えで退場させかけた。今回は FRED が届かなかったので、
    同じ誤りを犯す条件が実際に揃った。
    """

    def test_the_status_says_the_provider_is_unaffected(self) -> None:
        assert (
            "DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED"
            in prereg.TRACK_STATUS_SUFFIXES
        )

    def test_every_track_has_a_stage_zero_reason_with_counts(self) -> None:
        per_track = prereg.STAGE_0_OUTCOME["per_track"]
        assert set(per_track) == set(prereg.EXECUTION_ORDER)
        for track, row in per_track.items():
            assert row["status"] in prereg.TRACK_STATUS_SUFFIXES, track
            assert row["verified_currencies"] < row["needed"], track
            assert row["why"], track

    def test_the_record_names_what_was_verified_and_what_was_guessed_wrong(self) -> None:
        outcome = prereg.STAGE_0_OUTCOME
        assert outcome["verified_series_found"]
        #: **推定が外れたことを隠さない。** provider が教えてくれた事実として残す。
        assert len(outcome["guesses_that_were_wrong_and_how_we_knew"]) >= 3
        blob = " ".join(outcome["guesses_that_were_wrong_and_how_we_knew"])
        assert "Treasury Bills" in blob
        assert "HTML" in blob

    def test_it_refuses_to_blame_the_providers(self) -> None:
        assert prereg.STAGE_0_OUTCOME["fred_reachability"].endswith("FROM_THIS_ENVIRONMENT")
        assert "paid data ではない" in prereg.STAGE_0_OUTCOME["what_would_unblock_it"]

    def test_it_records_why_two_currencies_were_not_enough(self) -> None:
        """**通貨数を下げて走らせるのは実行ではなく凍結の変更である。**"""
        text = prereg.STAGE_0_OUTCOME["what_was_not_done_and_why"]
        assert "鏡像" in text
        assert "凍結の変更" in text

    def test_the_pre_alpha_amendment_is_recorded(self) -> None:
        amendment = prereg.FREEZE_AMENDMENT_PRE_ALPHA
        assert amendment["status"] == "AMENDED_PRE_ALPHA_NO_SIGNAL_HAD_RUN"
        assert amendment["digest_before"] != prereg.freeze_digest()
        assert "事実に反する" in amendment["why"]


@pytest.mark.research_data
class TestTheReportSaysWhatWasAndWasNotMeasured:
    @pytest.fixture(scope="class")
    def report(self) -> str:
        from pathlib import Path

        root = Path(__file__).resolve().parents[2]
        return (root / "docs/research/m15_next_five_report_2026_09_22.md").read_text(
            encoding="utf-8"
        )

    def test_it_records_the_previous_merge_sha(self, report: str) -> None:
        assert "60923fe" in report

    def test_it_refuses_to_say_the_data_does_not_exist(self, report: str) -> None:
        """**到達できないことを「無料ソースが無い」と書かない。**"""
        assert "DATA_NOT_RETRIEVABLE_FROM_THIS_ENVIRONMENT_PROVIDER_UNAFFECTED" in report
        assert "series は無料で存在する" in report
        assert "不要な paid data 購入" in report

    def test_it_states_that_no_alpha_was_measured(self, report: str) -> None:
        assert "alpha は 1 本も測っていない" in report
        assert "未測定" in report

    def test_it_answers_all_five_questions(self, report: str) -> None:
        assert "5 つの問いへの回答" in report
        for number in range(1, 6):
            assert f"### {number}." in report, number

    def test_it_reports_the_gate_strictness_spread(self, report: str) -> None:
        """裁定 §G の前提が実測で確認されたこと。"""
        assert "9.3%" in report and "28.7%" in report
        assert "cost drag" in report

    def test_it_refuses_to_call_the_low_pass_rate_a_good_gate(self, report: str) -> None:
        assert "良い gate」と読んではならない" in report

    def test_it_records_the_two_defects_found_in_stage_zero(self, report: str) -> None:
        assert "classify_failure" in report
        assert "死んだ分類" in report
        assert "HTTP 200 だが HTML" in report

    def test_it_does_not_set_a_programme_level_verdict(self, report: str) -> None:
        """裁定 §55 / §O — **勝手に停止を宣言しない。**

        token の出現そのものは正しい（「設定していない」と書いてある）ので、
        **設定していないと明言していること**を見る。
        """
        assert "programme-level の判断はしていない" in report
        assert "`FX research paused` は設定していない" in report

    def test_it_names_data_access_not_paid_data_as_the_next_step(self, report: str) -> None:
        assert "data access engineering" in report
        assert "今は要らない" in report
