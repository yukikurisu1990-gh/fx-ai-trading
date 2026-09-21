"""判定が、実測値と凍結した語彙に一致していることを固定する。

**数値は artefact から読む。** doc の散文を信じない — 散文と artefact がずれたら
どちらが正しいか分からなくなる。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.research.top_five import prereg, verdicts

#: 判定は実行 artefact（git 管理外の取得データから作られる）を読む。同じ規約に従う。
pytestmark = pytest.mark.research_data

ROOT = Path(__file__).resolve().parents[2]
DEVELOPMENT = ROOT / "artifacts/research/top_five/development.json"
DOC = ROOT / "docs/research/m15_top_five_development_2026_09.md"


@pytest.fixture(scope="module")
def measured() -> dict:
    return json.loads(DEVELOPMENT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def document() -> str:
    return DOC.read_text(encoding="utf-8")


class TestTheRunUsedTheFrozenDesign:
    def test_the_artefact_carries_the_freeze_digest(self, measured: dict) -> None:
        assert measured["freeze_digest"] == prereg.freeze_digest()

    def test_all_five_tracks_ran(self, measured: dict) -> None:
        tracks = {row.get("track") for row in measured["results"].values()}
        assert tracks == set(prereg.EXECUTION_ORDER)

    def test_both_spans_ran_for_every_track(self, measured: dict) -> None:
        for track in prereg.EXECUTION_ORDER:
            spans = {
                row.get("span") for key, row in measured["results"].items() if key.startswith(track)
            }
            assert spans == {"long", "recent"}, track

    def test_t3_ran_both_signs(self, measured: dict) -> None:
        keys = [k for k in measured["results"] if k.startswith("T3")]
        assert any("T3-H1" in k for k in keys)
        assert any("T3-H2" in k for k in keys)


class TestEveryVerdictUsesTheFrozenVocabulary:
    def test_each_status_carries_its_track_and_candidate(self) -> None:
        for track, row in verdicts.VERDICTS.items():
            status = row["status"]
            assert status.startswith(f"{track}_{prereg.TRACKS[track]['candidate']}_"), track
            suffix = status.split("_", 2)[2]
            assert suffix in prereg.TRACK_STATUS_SUFFIXES, status

    def test_every_negative_names_its_failure_class(self) -> None:
        for track, row in verdicts.VERDICTS.items():
            if "NOT_SUPPORTED" in row["status"]:
                assert any(name in row["failure_class"] for name in prereg.NEGATIVE_CLASSES), track

    def test_exactly_one_track_is_net_positive(self) -> None:
        assert verdicts.summary()["net_positive"] == ["T5"]


class TestTheVerdictsMatchTheMeasurements:
    def test_only_t5_recent_has_positive_net_sharpe(self, measured: dict) -> None:
        positive = [
            key
            for key, row in measured["results"].items()
            if "metrics" in row and row["metrics"]["net_sharpe"] > 0
        ]
        assert positive == ["T5_recent"], positive

    def test_t5_long_is_flat_on_the_better_powered_span(self, measured: dict) -> None:
        """marginal に留める最大の理由。8 倍の標本が何も示さない。"""
        long_span = measured["results"]["T5_long"]["metrics"]
        recent = measured["results"]["T5_recent"]["metrics"]
        assert abs(long_span["net_sharpe"]) < 0.1
        assert long_span["days"] > 7 * recent["days"]

    def test_t3_signs_are_mirrors_of_each_other(self, measured: dict) -> None:
        """H2 の gross が正なのは H1 の gross が負であることと同じ事実である。"""
        h1 = measured["results"]["T3_recent_T3-H1"]["metrics"]
        h2 = measured["results"]["T3_recent_T3-H2"]["metrics"]
        assert h1["gross_sharpe"] == pytest.approx(-h2["gross_sharpe"], abs=1e-6)
        assert h1["incremental_ic"] == pytest.approx(-h2["incremental_ic"], abs=1e-6)
        #: net はどちらも負 — 選ぶ対象が無い
        assert h1["net_sharpe"] < 0 and h2["net_sharpe"] < 0

    def test_t3_long_is_data_not_decision_grade(self, measured: dict) -> None:
        for key in ("T3_long_T3-H1", "T3_long_T3-H2"):
            assert measured["results"][key]["verdict"] == "DATA_NOT_DECISION_GRADE"

    def test_every_rename_gate_that_ran_passed(self, measured: dict) -> None:
        """通らなかった track があれば、その結果は採らない約束だった。"""
        for key, row in measured["results"].items():
            if "rename_gate" in row:
                assert row["rename_gate"]["verdict"] == "DISTINCT", key
                assert row["rename_gate"]["threshold"] == 0.8


class TestTurnoverIsComparedInTheRightUnits:
    """初稿は leverage 適用後の値を band law の単位と比べ、全 track が超過に見えていた。"""

    def test_the_comparison_uses_per_unit_gross(self, measured: dict) -> None:
        for key, row in measured["results"].items():
            check = row.get("turnover_check")
            if not check:
                continue
            assert "measured_per_unit_gross" in check, key
            assert "mean_portfolio_gross" in check, key
            #: 生の値は leverage 倍だけ大きい
            assert check["measured_levered"] > check["measured_per_unit_gross"], key

    def test_only_t3_exceeds_its_frozen_turnover(self, measured: dict) -> None:
        exceeded = [
            key
            for key, row in measured["results"].items()
            if row.get("turnover_check", {}).get("exceeds_corrected")
        ]
        assert all(key.startswith("T3") for key in exceeded), exceeded
        assert exceeded, "T3 は超過しているはず"

    def test_the_correction_did_not_change_any_verdict(self) -> None:
        """cost は実際の建玉変化に課されるので net は影響を受けない。"""
        finding = verdicts.ENGINEERING_FINDING
        assert "verdict は 1 つも変わらない" in finding["not_a_rescue"]
        assert "正しく課金されている" in finding["why_it_matters"]

    def test_the_finding_records_that_it_was_itself_wrong_first(self) -> None:
        finding = verdicts.ENGINEERING_FINDING
        assert finding["id"] == "E-002"
        assert "誤った" in finding["finding"]
        assert "how_it_was_caught" in finding


class TestNoPortfolioWasBuilt:
    def test_the_cycle_records_that_it_did_not_combine(self, measured: dict) -> None:
        assert "NO_WEIGHTS_OPTIMIZATION" in measured["multi_source_portfolio"]

    def test_the_correlations_are_diagnostic_only(self, measured: dict) -> None:
        correlations = measured["cross_track_correlation"]
        #: T3 の H1/H2 は定義上の鏡像。それ以外は小さい
        others = [v for k, v in correlations.items() if "T3-H1|T3_recent_T3-H2" not in k]
        assert max(abs(v) for v in others) < 0.2

    def test_the_search_breadth_is_disclosed(self, measured: dict) -> None:
        assert "FIVE_WAY" in measured["exploration_disclosure"]
        assert "TWO_SIGN_SUB_SEARCH" in measured["exploration_disclosure"]


class TestTheDocumentMatchesTheArtefact:
    def test_it_carries_the_freeze_digest(self, document: str, measured: dict) -> None:
        assert measured["freeze_digest"] in document

    def test_it_names_every_verdict(self, document: str) -> None:
        for row in verdicts.VERDICTS.values():
            assert row["status"] in document, row["status"]

    def test_it_states_the_protected_data_is_unread(self, document: str) -> None:
        for span in ("fresh pool", "historical OOS", "dead window", "forward"):
            assert span in document, span
        assert "未読" in document

    def test_it_refuses_the_overgeneralisations(self, document: str) -> None:
        for phrase in (
            "「cross-asset が無理」とは言っていない",
            "「原油が無理」とは言っていない",
            "「curve shape が無理」とは言っていない",
            "「flow が有望」とは言っていない",
            #: **両方向を拒むこと。** 「有望ではない」だけ書くと、検出力の無さを
            #: 効果の不在へすり替えたことになる。
            "「flow が無望」とも言っていない",
        ):
            assert phrase in document, phrase

    def test_it_reports_both_t3_signs(self, document: str) -> None:
        assert "T3-H1" in document and "T3-H2" in document
        assert "鏡像" in document

    def test_it_discloses_the_post_execution_corrections(self, document: str) -> None:
        """**「凍結どおり 1 回走らせた」と読ませない。**"""
        assert "CORRECTED_AFTER_RESULTS_WERE_SEEN" in document
        for identifier in ("C-1", "C-2", "C-3"):
            assert identifier in document, identifier
        assert "実行前に閉じているべきだった" in document

    def test_it_corrects_the_false_fresh_pool_claim(self, document: str) -> None:
        """初稿の「fresh pool 未読」が **その leg については偽だった**ことを残す。"""
        assert "偽だった" in document
        for day in ("2021-05-11", "2021-05-26", "2021-05-27"):
            assert day in document, day

    def test_it_reports_the_null_calibration(self, document: str) -> None:
        """gate を通った事実の情報量を、数字で出していること。"""
        assert "42%" in document
        assert "0.314" in document

    def test_it_shows_where_the_nuisance_constant_sits(self, document: str) -> None:
        assert "max_staleness_days" in document
        assert "楽観側" in document

    def test_it_reports_t2_against_t1(self, document: str) -> None:
        """凍結が名指しで要求した cross-track control の結果が本文にあること。"""
        assert "over T1" in document
        assert "−0.0115" in document and "−0.0019" in document

    def test_it_broadens_the_carry_disclosure_to_every_track(self, document: str) -> None:
        assert "CARRY_LEG_ABSENT_ON_BOTH_SPANS_SPOT_ONLY" in document
        assert "凍結時の開示が実物より狭かった" in document

    def test_it_reports_drawdown_and_margin_headroom(self, document: str) -> None:
        for token in ("scaled maxDD", "margin 利用率", "逆行 gap"):
            assert token in document, token


class TestTheVerdictsDoNotOverclaim:
    def test_t5_is_not_presented_as_evidence(self) -> None:
        row = verdicts.VERDICTS["T5"]
        assert "MARGINAL_DEVELOPMENT_CANDIDATE" in row["status"]
        assert row["failure_class"].startswith("UNDERPOWERED_FOR_CONFIRMATORY_CLAIM")
        assert "区別がつかない" in row["why_marginal_is_not_evidence"]
        assert "0.314" in row["why_marginal_is_not_evidence"]

    def test_t5_keeps_the_reason_it_is_still_a_candidate_separate(self) -> None:
        """**残す理由は Sharpe ではない**と書いてあること（裁定 §37）。"""
        text = verdicts.VERDICTS["T5"]["why_it_is_still_a_candidate"]
        assert "Sharpe ではなく" in text
        assert "検出力が無い" in text

    def test_nothing_is_recorded_as_confirmed(self) -> None:
        assert verdicts.summary()["confirmed"] == []

    def test_t1_does_not_claim_the_information_is_certain(self) -> None:
        """初稿の「情報は確かにある」を、検定していない以上は書かない。"""
        row = verdicts.VERDICTS["T1"]
        assert "確かにある" not in row["why"]
        assert "検定していない" in row["how_much_information"]

    def test_t2_reports_its_incremental_ic_over_t1(self) -> None:
        text = verdicts.VERDICTS["T2"]["incremental_over_t1"]
        assert "−0.0115" in text and "−0.0019" in text
        assert "何も足していない" in text

    def test_the_shared_caveats_are_not_hidden_inside_one_track(self) -> None:
        assert "carry_leg_absent_on_both_spans" in verdicts.SHARED_CAVEATS
        assert "vocabulary_gap" in verdicts.SHARED_CAVEATS
        assert "seen_development_only" in verdicts.SHARED_CAVEATS

    def test_the_method_finding_is_recorded_separately_from_the_alpha_verdicts(self) -> None:
        """**alpha を救うための発見ではない**ので、分けて持つ。"""
        finding = verdicts.METHOD_FINDING
        assert finding["id"] == "M-001"
        assert "帰無" in finding["finding"]
        assert finding["status"].startswith("A_PREREGISTERED_GATE_WITHOUT_ITS_NULL_PASS_RATE")


@pytest.mark.research_data
class TestTheFinalReportAnswersWhatTheRulingAsked:
    """裁定 §53（報告構造）と §54（7 つの問い）を満たしていること。"""

    @pytest.fixture(scope="class")
    def report(self) -> str:
        return (ROOT / "docs/research/m15_top_five_final_report_2026_09_21.md").read_text(
            encoding="utf-8"
        )

    def test_it_carries_the_identity_block(self, report: str, measured: dict) -> None:
        assert measured["freeze_digest"] in report
        assert prereg.DIGEST_AS_EXECUTED in report
        assert prereg.SUPERSEDED_FREEZE["digest"] in report

    def test_it_states_that_490_was_not_merged_and_why(self, report: str) -> None:
        """**merge SHA を持たない理由を書く。** 空欄で済ませない。"""
        assert "無し（未 merge）" in report
        assert "逸脱" in report

    def test_it_has_every_section_the_ruling_listed(self, report: str) -> None:
        for heading in (
            "Freeze Corrections",
            "xlrd Dependency",
            "Data Acquisition Record",
            "Protected Data Status",
            "Cross-Track Comparison",
            "Cross-Track Correlation",
            "Leverage / Margin",
            "Paid-Data Opportunities",
            "Engineering Findings",
            "Candidate Inventory Update",
            "Remaining Expected-Return Sources",
            "Recommended Next Step",
        ):
            assert heading in report, heading

    def test_it_covers_all_five_candidates(self, report: str) -> None:
        for candidate in ("S05", "S06", "S02", "S10", "S26"):
            assert candidate in report, candidate

    def test_it_answers_all_seven_questions(self, report: str) -> None:
        assert "7 つの問いへの回答" in report
        for number in range(1, 8):
            assert f"### {number}." in report, number

    def test_it_reports_the_detection_floor_against_the_measurement(self, report: str) -> None:
        """**この cycle の中心的な事実** — 実測が自分の窓の検出下限を下回っている。"""
        assert "1.321" in report or "1.32" in report
        assert "MDE95" in report

    def test_it_separates_refuted_from_underpowered(self, report: str) -> None:
        assert "REFUTED" in report
        assert "検出力不足の null" in report

    def test_it_does_not_set_a_programme_level_verdict(self, report: str) -> None:
        """裁定 §55 — `FX research paused` を勝手に設定しない。"""
        assert "FX research paused" not in report
        assert "programme-level" in report

    def test_it_records_that_nothing_beat_its_own_noise_band_upward(self, report: str) -> None:
        assert "正の側でノイズ帯の外に出た測定は 1 つも無い" in report

    def test_it_names_the_next_step_as_turnover_design(self, report: str) -> None:
        """§54-7 の答えが「執行の巧拙」ではなく turnover 設計であること。"""
        assert "execution improvement" in report
        assert "turnover 設計" in report

    def test_the_paid_data_section_is_a_proposal_only(self, report: str) -> None:
        assert "購入していない" in report

    def test_it_discloses_the_revision_caveat(self, report: str) -> None:
        """**公表 lag 規約では塞げない残存 look-ahead** を隠さないこと。"""
        assert prereg.REVISION_CAVEAT in report
        assert "改訂" in report
        assert "無料の範囲では塞げない" in report
