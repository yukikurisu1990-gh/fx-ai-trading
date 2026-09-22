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

#: **実行に使われた digest。この値は書き換えてはならない。**
DIGEST_AS_EXECUTED = "28100ebedfea45765371585df5c4308fee261e2496a9798acca79c920158962c"

#: 現在の digest。**実行後に 2 度動いた**ので、実行値とは別である。
#: 1 度目は payload の覆う範囲を広げたため、2 度目は `POST_EXECUTION_CORRECTIONS`
#: の 3 件（C-1 leakage 閉塞 / C-2 単位バグ + 新定数 / C-3 欠けていた null）を入れたため。
#: **ここを更新するときは、必ず `POST_EXECUTION_CORRECTIONS` に理由を足すこと。**
#: 理由を書かずに digest を追従させると、凍結が凍結でなくなる。
CURRENT_DIGEST = "0d1f3b118fc86f87c5e87d7623b76df1e8e9d1e99ab82e4f87dc85ff2654e24f"

#: 2026-09-21 裁定で差し替えた旧 freeze。**削除せず履歴として保持する。**
SUPERSEDED_DIGEST = "29ba80d68a5462fe015a6f2566d3c0b63319d0549de7b9a4d34a890f2339b1ca"


@pytest.fixture(scope="module")
def document() -> str:
    return DOC.read_text(encoding="utf-8")


class TestTheFreezeIsWhatItSaysItIs:
    def test_the_current_digest_is_pinned(self) -> None:
        assert prereg.freeze_digest() == CURRENT_DIGEST

    def test_the_executed_digest_is_kept_and_differs(self) -> None:
        """**走った設計と、いま repo にある設計は別物である。**両方を残す。"""
        assert prereg.DIGEST_AS_EXECUTED == DIGEST_AS_EXECUTED
        assert prereg.freeze_digest() != DIGEST_AS_EXECUTED

    def test_the_post_execution_corrections_are_recorded(self) -> None:
        """digest が動いた**理由**が凍結 payload の中にあること。"""
        record = prereg.POST_EXECUTION_CORRECTIONS
        assert record["digest_before"] == DIGEST_AS_EXECUTED
        assert record["status"].startswith("CORRECTED_AFTER_RESULTS_WERE_SEEN")
        ids = {row["id"] for row in record["corrections"]}
        assert ids == {"C-1", "C-2", "C-3"}
        #: **裁量のあった訂正は、裁量があったと書いてあること。**
        by_id = {row["id"]: row for row in record["corrections"]}
        assert "ある" in by_id["C-2"]["discretion"]
        assert by_id["C-1"]["kind"] == "LEAKAGE_CLOSURE"

    def test_the_corrections_record_moves_the_digest(self) -> None:
        """記録を消したり緩めたりしたら digest が動くこと（＝凍結の外に置かない）。"""
        before = prereg.freeze_digest()
        original = prereg.POST_EXECUTION_CORRECTIONS["status"]
        try:
            prereg.POST_EXECUTION_CORRECTIONS["status"] = "CLEAN_RUN"
            assert prereg.freeze_digest() != before
        finally:
            prereg.POST_EXECUTION_CORRECTIONS["status"] = original
        assert prereg.freeze_digest() == before

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

    def test_t3_prespecifies_both_signs_rather_than_choosing_one(self) -> None:
        """実行前レビューで economic sign が理論的に曖昧と判明したため。"""
        direction = prereg.TRACKS["T3"]["direction"]
        subs = direction["sub_hypotheses"]
        assert set(subs) == {"T3-H1", "T3-H2"}
        assert "appreciation" in subs["T3-H1"]
        assert "depreciation" in subs["T3-H2"]

    def test_t3_forbids_headlining_the_better_sign(self) -> None:
        rule = prereg.TRACKS["T3"]["direction"]["reporting_rule"]
        assert "両方報告" in rule
        assert "primary 扱いしない" in rule
        assert "sign multiplicity" in rule

    def test_t3_records_that_steepening_is_not_one_mechanism(self) -> None:
        why = prereg.TRACKS["T3"]["direction"]["why_ambiguous"]
        for mechanism in ("bull steepening", "bear steepening", "term-premium", "fiscal-risk"):
            assert mechanism in why, mechanism
        assert "結果後に分類して最適化しない" in why

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
        assert "hard limit として" in prereg.BOOK_CONFIG["why_max_leverage_is_not_5"]

    def test_the_broker_ceiling_is_not_treated_as_a_risk_budget(self) -> None:
        """「20x まで可能だから低い Sharpe でも十分」は明示的に禁じられている。"""
        broker = prereg.LEVERAGE_FRAMEWORK["A_broker_hard"]
        assert "absolute ceiling" in broker["what_it_is"]
        assert "安全だという意味ではない" in broker["what_it_is_not"]
        assert "実用的だという意味でもない" in broker["what_it_is_not"]

    def test_the_cap_does_not_bind_at_the_target_vol(self) -> None:
        """risk は vol targeting が決める。cap はその上の天井でしかない。"""
        from scripts.research.edge_sources import capacity

        needed = prereg.BOOK_CONFIG["vol_target"] / capacity.VOL_PER_UNIT_GROSS
        assert needed < prereg.BOOK_CONFIG["max_leverage"]
        #: 最も高い scenario でも binding しない
        highest = max(prereg.LEVERAGE_FRAMEWORK["standard_target_vol_scenarios"])
        assert highest / capacity.VOL_PER_UNIT_GROSS < prereg.BOOK_CONFIG["max_leverage"]

    def test_the_standard_target_vol_scenarios_are_frozen(self) -> None:
        assert prereg.LEVERAGE_FRAMEWORK["standard_target_vol_scenarios"] == (
            0.08,
            0.10,
            0.12,
            0.15,
        )

    def test_neither_direction_of_the_leverage_fallacy_is_allowed(self) -> None:
        how = prereg.LEVERAGE_FRAMEWORK["how_to_judge"]
        assert "5x を超えるから不可" in how
        assert "20x まで可能だから" in how
        assert "実測" in how

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

    def test_acquisition_is_authorised_and_scoped(self) -> None:
        """2026-09-21 裁定 §5 で本取得が承認された。scope は public/free のみ。"""
        assert prereg.ACQUISITION["scope"] == "public / free source のみ"
        assert "2026-09-21" in prereg.ACQUISITION["authorized"]


class TestKnownDefectsAreDisclosedNotHidden:
    def test_the_oil_data_format_problem_is_stated(self) -> None:
        caveat = prereg.TRACKS["T2"]["data_caveat"]
        assert "OLE2" in caveat
        assert "2026-09-21 裁定 §2 が追加を承認" in caveat
        assert "macro を実行しない" in caveat

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
        for shape in (
            "sign flip after result",
            "horizon optimization",
            "lag optimization",
            "threshold tuning",
            "currency removal",
            "feature addition",
            "cost-specific smoothing",
            "band optimization",
            "leverage optimization",
            "model complexity addition",
        ):
            assert shape in prereg.FORBIDDEN_RESCUES, shape

    def test_negative_results_are_classified_not_lumped(self) -> None:
        assert set(prereg.NEGATIVE_CLASSES) == {
            "SIGNAL_FAILURE",
            "COST_FAILURE",
            "DATA_FAILURE",
            "CONCENTRATION_FAILURE",
            "IMPLEMENTATION_FAILURE",
        }
        for name, meaning in prereg.NEGATIVE_CLASSES.items():
            assert meaning.strip(), name

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
        #: freeze doc は**事前登録の記録**なので、実行値を載せているのが正しい。
        assert DIGEST_AS_EXECUTED in document

    def test_it_names_all_five_and_both_skipped(self, document: str) -> None:
        for token in ("S05", "S06", "S02", "S10", "S26", "S07", "S25"):
            assert token in document, token

    def test_it_states_that_nothing_has_been_looked_at(self, document: str) -> None:
        assert "alpha を 1 本も見ていない" in document

    def test_it_records_that_the_first_draft_did_not_survive_review(self, document: str) -> None:
        assert "初稿" in document

    def test_it_is_marked_non_decision_bearing(self, document: str) -> None:
        assert "NON_DECISION_BEARING_EXPLORATORY_ONLY" in document


class TestTheRulingOfTwentyFirstIsReflected:
    """2026-09-21 裁定が凍結へ反映されていること。"""

    def test_the_old_freeze_is_kept_as_superseded_not_deleted(self) -> None:
        assert prereg.SUPERSEDED_FREEZE["digest"] == SUPERSEDED_DIGEST
        assert prereg.SUPERSEDED_FREEZE["status"] == "SUPERSEDED_PRE_EXECUTION"
        #: 差し替えは alpha を見る前に行われた — post-result rescue ではない
        assert "alpha は 1 本も見られていない" in prereg.SUPERSEDED_FREEZE["why"]

    def test_the_new_digest_differs_from_the_superseded_one(self) -> None:
        assert prereg.freeze_digest() != SUPERSEDED_DIGEST

    def test_acquisition_is_now_authorised_with_its_recording_duties(self) -> None:
        acquisition = prereg.ACQUISITION
        assert "2026-09-21" in acquisition["authorized"]
        for field in ("url", "content_hash", "retrieval_timestamp", "publication_timing"):
            assert field in acquisition["must_record"], field

    def test_the_acquisition_forbids_the_protected_spans(self) -> None:
        forbidden = prereg.ACQUISITION["forbidden"]
        for span in ("fresh span", "historical OOS", "dead window", "forward epoch"):
            assert span in forbidden, span
        assert "paid API" in forbidden
        assert "authenticated OANDA" in forbidden

    def test_the_protected_span_is_excluded_at_the_request_not_after(self) -> None:
        rule = prereg.ACQUISITION["request_level_exclusion"]
        assert "request 自体から除外" in rule
        assert "download-then-filter は禁止" in rule

    def test_every_track_status_carries_its_track_prefix(self) -> None:
        """接頭辞が無いと、どの track の verdict か token から読めない。"""
        token = prereg.track_status("T3", "NOT_SUPPORTED_IN_SEEN_DEVELOPMENT")
        assert token == "T3_S02_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
        with pytest.raises(ValueError):
            prereg.track_status("T1", "EDGE_CONFIRMED")

    def test_all_five_status_suffixes_are_available(self) -> None:
        #: 2026-09-22 裁定 §4 で POSITIVE_EXPLORATORY_SIGNAL_NOT_DECISION_GRADE が加わって 6。
        assert len(prereg.TRACK_STATUS_SUFFIXES) == 6
        for track in prereg.TRACKS:
            for suffix in prereg.TRACK_STATUS_SUFFIXES:
                assert prereg.track_status(track, suffix).startswith(track)

    def test_multi_source_portfolio_is_deferred_not_attempted(self) -> None:
        assert "NO_WEIGHTS_OPTIMIZATION" in prereg.MULTI_SOURCE_PORTFOLIO
        assert "PROPOSAL_ONLY" in prereg.MULTI_SOURCE_PORTFOLIO

    def test_the_cross_track_diagnostic_is_declared_but_not_an_optimiser(self) -> None:
        assert "pairwise_pnl_correlation" in prereg.CROSS_TRACK_DIAGNOSTIC
        assert "common_risk_factor" in prereg.CROSS_TRACK_DIAGNOSTIC

    def test_the_search_breadth_is_disclosed_including_the_t3_sub_search(self) -> None:
        """5 本 + T3 の 2 符号 = 実際には 6 通りの探索である。"""
        assert "FIVE_WAY" in prereg.EXPLORATION_DISCLOSURE
        assert "TWO_SIGN_SUB_SEARCH" in prereg.EXPLORATION_DISCLOSURE

    def test_the_document_carries_the_dual_sign_prereg(self, document: str) -> None:
        assert "T3-H1" in document and "T3-H2" in document
        assert "両方 prespecified sub-hypothesis" in document
        assert "primary 扱いしない" in document

    def test_the_document_refuses_both_leverage_fallacies(self, document: str) -> None:
        assert "5x を超えるから不可" in document
        assert "20x まで可能だから Sharpe 0.107 で十分" in document
        assert "8% / 10% / 12% / 15%" in document

    def test_the_document_records_the_superseded_freeze(self, document: str) -> None:
        assert SUPERSEDED_DIGEST in document
        assert "SUPERSEDED_PRE_EXECUTION" in document
