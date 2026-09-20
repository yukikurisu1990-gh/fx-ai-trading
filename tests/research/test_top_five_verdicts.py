"""判定が、実測値と凍結した語彙に一致していることを固定する。

**数値は artefact から読む。** doc の散文を信じない — 散文と artefact がずれたら
どちらが正しいか分からなくなる。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.research.top_five import prereg, verdicts

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


class TestTheTurnoverFindingIsSeparatedFromTheVerdicts:
    def test_every_track_exceeded_its_frozen_turnover(self, measured: dict) -> None:
        for key, row in measured["results"].items():
            if "turnover_check" in row:
                assert row["turnover_check"]["exceeds_corrected"] is True, key

    def test_the_finding_is_recorded_as_engineering_not_as_a_rescue(self) -> None:
        finding = verdicts.ENGINEERING_FINDING
        assert "band optimization" in finding["not_a_rescue"]
        assert "救わない" in finding["not_a_rescue"]
        assert finding["id"] == "E-002"


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
            "「flow が有望」とも言っていない",
        ):
            assert phrase in document, phrase

    def test_it_reports_both_t3_signs(self, document: str) -> None:
        assert "T3-H1" in document and "T3-H2" in document
        assert "鏡像" in document
