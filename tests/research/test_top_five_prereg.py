"""5 本一括凍結を固定する。

**この test file の役目**: 5 本が *同時に*、*結果を見る前に* 凍結されたという事実を、
後から確認できる形にすること。digest が変われば別の事前登録であり、
cross-track contamination は隠せない。

初稿は 2 つの独立レビューで blocker を受けた。ここで固定するのは、そのうち
**実際に凍結を壊していたもの**が直っていることである:
lag の向き / OOS 境界 / digest の網羅漏れ / 発火しない gate / 使えない data 形式 /
leverage 規約の欠落。
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from scripts.research import top_five
from scripts.research.top_five import prereg

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs/research/m15_top_five_freeze_2026_09.md"

#: 凍結時の digest。**この値は書き換えてはならない。**
#: 変える必要が出たときは、それは編集ではなく新しい事前登録である。
FROZEN_DIGEST = "29ba80d68a5462fe015a6f2566d3c0b63319d0549de7b9a4d34a890f2339b1ca"


@pytest.fixture(scope="module")
def document() -> str:
    return DOC.read_text(encoding="utf-8")


class TestTheFreezeIsWhatItSaysItIs:
    def test_the_digest_has_not_moved(self) -> None:
        assert prereg.freeze_digest() == FROZEN_DIGEST

    def test_exactly_five_tracks(self) -> None:
        assert len(prereg.TRACKS) == 5
        assert tuple(prereg.TRACKS) == prereg.EXECUTION_ORDER

    def test_every_track_fixes_everything_the_ruling_listed(self) -> None:
        """1 つでも欠けたら、そこが実行時の裁量になる。"""
        for name, track in prereg.TRACKS.items():
            for field in (
                "mechanism",
                "data",
                "data_evidence",
                "signal",
                "direction",
                "horizon",
                "category",
                "breadth",
                "expected_turnover",
            ):
                assert field in track, (name, field)
            assert "frozen" in track["direction"], name

    def test_all_five_share_one_execution_layer(self) -> None:
        assert prereg.EXECUTION_LAYER.endswith("run_book")


class TestTheDigestCoversEveryPublicConstant:
    """初稿の最大の穴: 事後に最も緩めたくなるリストが digest の外にあった。"""

    def test_no_public_constant_sits_outside_the_digest(self) -> None:
        public = {name for name in prereg.__all__ if name.isupper()}
        covered = {key.upper() for key in prereg._payload()}
        assert not (public - covered), sorted(public - covered)

    @pytest.mark.parametrize(
        "name",
        ["FORBIDDEN_RESCUES", "NEGATIVE_CLASSES", "NONLINEAR_ML", "PROMOTION_REASONING"],
    )
    def test_the_four_that_used_to_escape_now_move_the_digest(self, name: str) -> None:
        """mutation で実証された 4 つ。1 つずつ実際に動かして確かめる。"""
        before = prereg.freeze_digest()
        original = getattr(prereg, name)
        try:
            setattr(prereg, name, ("tampered",) if isinstance(original, tuple) else "tampered")
            assert prereg.freeze_digest() != before, name
        finally:
            setattr(prereg, name, original)
        assert prereg.freeze_digest() == before

    def test_the_package_level_constants_are_covered_too(self) -> None:
        """`OUTCOMES` と `FORBIDDEN_NEXT_STEPS` は別モジュールにあり、初稿では無防備だった。"""
        payload = prereg._payload()
        assert payload["outcomes"] == list(top_five.OUTCOMES)
        assert payload["forbidden_next_steps"] == list(top_five.FORBIDDEN_NEXT_STEPS)

    def test_the_digest_refuses_what_it_cannot_serialise(self) -> None:
        """初稿は `default=str` を渡しており、型変更に盲目だった。"""
        before = prereg.freeze_digest()
        original = prereg.BENCHMARKS
        try:
            prereg.BENCHMARKS = {object()}  # type: ignore[assignment]
            with pytest.raises(TypeError):
                prereg.freeze_digest()
        finally:
            prereg.BENCHMARKS = original  # type: ignore[assignment]
        assert prereg.freeze_digest() == before


class TestTheLagIsDefinedByPublicationNotByHope:
    """初稿は論証の向きを取り違え、長 span で 8 時間の先読みを許していた。"""

    def test_the_rule_is_stated_as_publication_relative(self) -> None:
        assert prereg.TIMESTAMP_RULE.startswith("AN_EXTERNAL_VALUE_MAY_ONLY_INFORM")
        assert "BEGINS_STRICTLY_AFTER_ITS_PUBLICATION" in prereg.TIMESTAMP_RULE

    def test_vix_gets_two_days_on_the_long_span(self) -> None:
        """VIX close 22:15 CET は ECB fix 14:15 CET の後なので 1 日では足りない。"""
        vix = prereg.PUBLICATION_TIMES["cboe_vix_close"]
        assert vix["long_span_lag_business_days"] == 2
        assert vix["recent_span_lag_business_days"] == 1

    def test_the_oil_series_is_not_treated_as_daily(self) -> None:
        """EIA の spot は水曜サイクル更新で、day t の値は当日存在しない。"""
        eia = prereg.PUBLICATION_TIMES["eia_wti_daily"]
        assert eia["long_span_lag_business_days"] == 7
        assert eia["recent_span_lag_business_days"] == 7
        assert "日次公表ではない" in eia["why"]

    def test_the_curves_get_two_days_on_both_spans(self) -> None:
        curves = prereg.PUBLICATION_TIMES["sovereign_curves"]
        assert curves["long_span_lag_business_days"] == 2
        assert curves["recent_span_lag_business_days"] == 2

    def test_every_external_source_has_a_publication_time(self) -> None:
        for name, row in prereg.PUBLICATION_TIMES.items():
            assert str(row["published_cet"]).strip(), name
            assert row["why"].strip(), name


class TestTheSpanEndsBeforeTheProtectedData:
    """近 span 最終日の t+1 return が OOS 初日を要求していた — R1 の事故と同じ形。"""

    def test_the_last_return_day_is_inside_the_span(self) -> None:
        for key in ("long", "recent"):
            span = prereg.SPANS[key]
            decision = dt.date.fromisoformat(span["last_decision_day"])
            ret = dt.date.fromisoformat(span["last_return_day"])
            assert decision < ret, key

    def test_the_recent_span_return_stops_before_the_oos_slice(self) -> None:
        from scripts.m15_track_a.oos_slice import SLICE_START_UTC

        last_return = dt.date.fromisoformat(prereg.SPANS["recent"]["last_return_day"])
        oos_start = dt.date.fromisoformat(prereg.PROTECTED_BOUNDS["oos_slice_start"])
        assert last_return < oos_start
        assert prereg.PROTECTED_BOUNDS["oos_slice_start"] == str(SLICE_START_UTC)

    def test_the_long_span_stops_before_the_fresh_pool(self) -> None:
        from scripts.research.valuation import sources

        last_return = dt.date.fromisoformat(prereg.SPANS["long"]["last_return_day"])
        assert last_return < dt.date.fromisoformat(sources.PROTECTED_FROM)
        assert prereg.PROTECTED_BOUNDS["fresh_pool_start"] == sources.PROTECTED_FROM

    def test_the_recent_span_starts_no_earlier_than_the_guarded_window(self) -> None:
        from scripts.research.exploratory_m15 import momentum

        first = dt.date.fromisoformat(prereg.SPANS["recent"]["first"])
        assert first >= dt.date.fromisoformat(momentum.MOMENTUM_START_UTC)

    def test_bounds_are_parsed_dates_not_string_compares(self) -> None:
        assert prereg.PROTECTED_BOUNDS["rule"].startswith("PARSED_TYPED_DATE_BOUNDS_ONLY")
        assert "切り落としてから" in prereg.PROTECTED_BOUNDS["acquisition"]


class TestTheRenameGatesCanActuallyFire:
    """初稿の T4 gate は算術的に到達不能な閾値を持っていた。"""

    def test_the_t4_comparator_is_the_one_that_can_reach_the_threshold(self) -> None:
        gate = prereg.TRACKS["T4"]["novelty_gate"]["PRE_REGISTERED_AUDIT"]
        assert "res_i(t)" in gate
        assert "own-return book" in gate
        assert "0.8" in gate and "RENAME" in gate

    def test_the_old_unreachable_comparator_is_gone(self) -> None:
        """5/20/60 日 momentum との相関上限は rho/sqrt(h) で 0.36 以下。"""
        gate = prereg.TRACKS["T4"]["novelty_gate"]["PRE_REGISTERED_AUDIT"]
        assert "発火しえなかった" in gate
        for horizon, ceiling in ((5, 0.36), (20, 0.18), (60, 0.11)):
            assert 0.8 / horizon**0.5 < ceiling

    def test_t4_declares_its_conflict_with_the_closed_mean_reversion(self) -> None:
        """H-010 は残差の 1 日構造を VR<1 と測って CLOSED。T4 は符号が逆である。"""
        gate = prereg.TRACKS["T4"]["novelty_gate"]
        assert "H-010" in gate["conflict_with_h010"]
        assert "符号が逆" in gate["conflict_with_h010"]

    def test_t3_has_a_gate_against_the_closed_rule_inverted(self) -> None:
        gate = prereg.TRACKS["T3"]["rename_gate"]
        assert "T-R2" in gate and "0.8" in gate

    def test_t5_has_a_gate_against_lagged_dollar_momentum(self) -> None:
        gate = prereg.TRACKS["T5"]["rename_gate"]
        assert "USD basket return" in gate and "0.8" in gate

    def test_three_tracks_carry_a_gate(self) -> None:
        gated = {n for n, t in prereg.TRACKS.items() if "rename_gate" in t or "novelty_gate" in t}
        assert gated == {"T3", "T4", "T5"}


class TestTheExecutionLayerIsFrozenNumerically:
    """初稿は関数名の文字列だけを凍結し、既定値を野放しにしていた。"""

    def test_the_book_config_is_numbers_not_defaults(self) -> None:
        for key in ("band", "vol_target", "weight_cap", "sigma_window", "factor_window"):
            assert key in prereg.BOOK_CONFIG, key

    def test_the_forbidden_five_times_cap_is_not_used(self) -> None:
        assert prereg.BOOK_CONFIG["max_leverage"] == 20.0
        assert "5x hard cap" in prereg.BOOK_CONFIG["why_max_leverage_is_not_5"]

    def test_the_broker_leverage_comes_from_the_public_margin_record(self) -> None:
        record = json.loads(
            (ROOT / "artifacts/research/edge_sources/oanda_margin_rates.json").read_text(
                encoding="utf-8"
            )
        )
        universe = set(top_five.UNIVERSE)
        rates = [
            row.get("margin_rate_mt5") or row.get("margin_rate_mt4")
            for pair, row in record["pairs"].items()
            if set(pair.split("_")) <= universe
        ]
        assert 1.0 / max(rates) == prereg.BOOK_CONFIG["max_leverage"]

    def test_the_three_leverage_concepts_are_separated(self) -> None:
        framework = prereg.LEVERAGE_FRAMEWORK
        assert {"A_broker_hard", "B_portfolio_gross", "C_risk"} <= set(framework)
        assert "net edge <= 0 を leverage で救わない" in framework["never"]

    def test_t5_deviates_from_the_shared_layer_and_says_why(self) -> None:
        deviation = prereg.BOOK_CONFIG_DEVIATIONS["T5"]
        assert deviation["neutralize_leading_factor"] is False
        assert deviation["disclosed"] is True

    def test_the_layer_effect_is_measured_every_time(self) -> None:
        assert "raw_to_neutralised_score_corr" in prereg.METRICS
        assert "factor_abs_cosine" in prereg.METRICS


class TestTurnoverIsNotTakenFromTheBandLawAlone:
    def test_both_the_law_and_the_corrected_value_are_frozen(self) -> None:
        for name, track in prereg.TRACKS.items():
            turnover = track["expected_turnover"]
            assert "band_law" in turnover and "corrected_x1_90" in turnover, name
            assert turnover["corrected_x1_90"] > turnover["band_law"], name

    def test_the_correction_cites_the_measurement_it_comes_from(self) -> None:
        assert prereg.TURNOVER_CORRECTION["measured_multiple"] == 1.90
        assert "prereg_r2" in prereg.TURNOVER_CORRECTION["evidence"]
        assert "B_cost_or_turnover_failure" in prereg.TURNOVER_CORRECTION["rule"]


class TestTheFiveAreGenuinelyDistinct:
    def test_five_distinct_categories(self) -> None:
        assert len({t["category"] for t in prereg.TRACKS.values()}) == 5

    def test_only_one_track_is_price_derived(self) -> None:
        price_only = [
            n for n, t in prereg.TRACKS.items() if not t["data_evidence"].startswith("gated probe")
        ]
        assert price_only == ["T4"], price_only

    def test_the_overlapping_pair_carries_a_cross_track_control(self) -> None:
        """beta 相関 +0.856 は、T4 の rename 閾値 0.8 を超えている。"""
        assert "T1" in prereg.CROSS_TRACK_CONTROLS["T2"]
        assert "0.856" in prereg.CROSS_TRACK_CONTROLS["T2"]

    def test_the_oil_betas_follow_the_declared_mechanism(self) -> None:
        """初稿は NZD を +0.5 にしており、宣言した機構を自分の beta が破っていた。"""
        beta = prereg.TRACKS["T2"]["direction"]["beta"]
        assert beta["NZD"] < 0, "NZ は原油の純輸入国"
        assert beta["CAD"] > beta["AUD"], "豪州の輸出は鉄鉱石・石炭・LNG で原油ではない"


class TestStageDisciplineIsFixedInAdvance:
    def test_stage_1_is_unfitted(self) -> None:
        assert "NO_FITTING" in prereg.STAGE_1_ONLY and "NO_ML" in prereg.STAGE_1_ONLY

    def test_the_judgement_span_is_the_one_where_cost_was_measured(self) -> None:
        assert "recent span" in prereg.STAGE_2_ELIGIBILITY["judged_on"]
        assert "pooled net は判定に使わない" in prereg.COST["reporting"]

    def test_stage_2_conditions_are_frozen(self) -> None:
        for key in ("condition_1", "condition_2", "condition_3"):
            assert prereg.STAGE_2_ELIGIBILITY[key].strip(), key
        assert "STOP" in prereg.STAGE_2_ELIGIBILITY["if_not_eligible"]

    def test_automatic_advance_carries_its_null_pass_probability(self) -> None:
        assert "帰無通過確率" in prereg.STAGE_2_ELIGIBILITY["multiplicity_note"]

    def test_nonlinear_ml_is_not_trained_this_cycle(self) -> None:
        assert prereg.NONLINEAR_ML == "PROPOSAL_ONLY_NO_TRAINING_IN_THIS_CYCLE"


class TestWhatIsNotExecutedKeepsItsRank:
    def test_the_blocked_candidates_are_recorded_not_deleted(self) -> None:
        assert set(prereg.NOT_EXECUTED) >= {"S07", "S25"}
        for cid in ("S07", "S25"):
            assert prereg.NOT_EXECUTED[cid]["status"] == "DESIGN_ONLY_NOT_EXECUTED"

    def test_neither_is_described_as_refuted(self) -> None:
        """どちらも local failure が原因であり、相手の不在ではない。"""
        assert "検定されていない" in prereg.NOT_EXECUTED["S07"]["why"]
        assert "閉じたのではなく" in prereg.NOT_EXECUTED["S07"]["why"]
        assert "閉じたのではない" in prereg.NOT_EXECUTED["S25"]["why"]

    def test_the_promotion_is_justified_against_the_closures(self) -> None:
        reasoning = prereg.PROMOTION_REASONING
        assert all(cid in reasoning for cid in ("S14", "S15", "S12"))
        assert "alpha を 1 つも見る前" in reasoning


class TestTheAuthorityIsCitedHonestly:
    def test_the_missing_ruling_text_is_carried_forward(self) -> None:
        """#489 が立てた token を 1 世代で落とさない。"""
        assert prereg.AUTHORITY["2026_09_19"] == (
            "PRIOR_ADJUDICATION_TEXT_NOT_IN_REPO_CITATIONS_UNVERIFIABLE"
        )

    def test_the_record_it_points_at_exists(self) -> None:
        assert (ROOT / prereg.AUTHORITY["record"]).exists()

    def test_the_freeze_is_not_an_acquisition_permission(self) -> None:
        assert "probe は metadata / availability のみ" in prereg.EXECUTION_REQUIRES
        assert "explicit な Human + ChatGPT の act" in prereg.EXECUTION_REQUIRES


class TestKnownDefectsAreDisclosedNotHidden:
    def test_the_oil_data_format_problem_is_stated(self) -> None:
        caveat = prereg.TRACKS["T2"]["data_caveat"]
        assert "OLE2" in caveat and "Amber" in caveat

    def test_the_vix_backfill_is_stated(self) -> None:
        assert "遡及計算" in prereg.TRACKS["T1"]["data_caveat"]

    def test_the_curve_universe_is_frozen_with_its_exclusions(self) -> None:
        universe = prereg.TRACKS["T3"]["universe"]
        assert set(universe["included"]) == {"USD", "EUR", "CAD", "CHF", "GBP"}
        assert set(universe["excluded"]) == {"JPY", "AUD", "NZD"}
        assert "加えない" in universe["why"]

    def test_the_bundesbank_series_is_the_one_that_answered(self) -> None:
        """初稿は 404 を返した系列名を data 欄に書いていた。"""
        assert "Zinsstruktur" in prereg.TRACKS["T3"]["data"]
        assert "404" in prereg.TRACKS["T3"]["data_evidence"]

    def test_the_missing_carry_leg_is_disclosed(self) -> None:
        assert "CARRY_LEG_ABSENT" in prereg.EXCESS_PANEL["disclosure"]
        assert "後から足さない" in prereg.EXCESS_PANEL["consequence"]

    def test_the_tic_revision_problem_is_disclosed(self) -> None:
        assert "NOT_THE_VINTAGE_AVAILABLE_AT_DECISION_TIME" in prereg.REVISION_CAVEAT
        assert "denomination_caveat" in prereg.TRACKS["T5"]

    def test_the_interpretation_band_conflict_is_recorded(self) -> None:
        assert "ECONOMIC_BANDS" in prereg.INTERPRETATION["differs_from_committed_bands"]


class TestResultDrivenRescueIsForbiddenUpFront:
    def test_the_forbidden_list_is_complete(self) -> None:
        assert len(prereg.FORBIDDEN_RESCUES) == 8
        for shape in (
            "sign reversal after result",
            "horizon tweak",
            "threshold optimization",
            "currency exclusion",
            "feature addition",
            "band optimization",
            "leverage optimization",
            "nonlinear rescue",
        ):
            assert shape in prereg.FORBIDDEN_RESCUES, shape

    def test_negative_results_are_classified_not_lumped(self) -> None:
        assert len(prereg.NEGATIVE_CLASSES) == 4

    def test_the_interpretation_is_economic_not_a_p_value_rule(self) -> None:
        assert "p < 0.05" in prereg.INTERPRETATION["not_a_significance_rule"]


class TestTheCycleStopsAtFive:
    def test_the_sixth_track_is_named_as_forbidden(self) -> None:
        assert any("6 本目" in item for item in top_five.FORBIDDEN_NEXT_STEPS)

    def test_fresh_and_paid_and_broker_are_all_out(self) -> None:
        blob = " ".join(top_five.FORBIDDEN_NEXT_STEPS)
        assert "fresh pool" in blob and "paid data" in blob and "broker" in blob

    def test_the_status_says_frozen_not_executed(self) -> None:
        assert top_five.WORKFLOW_STATUS == "TOP_FIVE_FROZEN_AWAITING_EXECUTION"


class TestTheDocumentMatchesTheFreeze:
    def test_it_carries_the_digest(self, document: str) -> None:
        assert FROZEN_DIGEST in document

    def test_it_names_all_five_and_both_skipped(self, document: str) -> None:
        for token in ("S05", "S06", "S02", "S10", "S26", "S07", "S25"):
            assert token in document, token

    def test_it_states_that_nothing_has_been_looked_at(self, document: str) -> None:
        assert "alpha を 1 本も見ていない" in document

    def test_it_records_that_the_first_draft_did_not_survive_review(self, document: str) -> None:
        assert "初稿" in document

    def test_it_is_marked_non_decision_bearing(self, document: str) -> None:
        assert "NON_DECISION_BEARING_EXPLORATORY_ONLY" in document
