"""取得・mapping・最終凍結を固定する（第 2 裁定 §9–§29）。

実データ（git 管理外の parquet と取得記録）を読む test は `research_data` gate の下に置く。
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.research.next_five import acquire, prereg, series_map, signals, statements

ROOT = Path(__file__).resolve().parents[2]
ACQUISITION = ROOT / "artifacts/research/next_five/acquisition.json"
STAGE0 = ROOT / "artifacts/research/next_five/stage0_rerun.json"


class TestTheLexiconWasFixedBeforeCounting:
    def test_the_lexicon_is_inside_the_digest(self) -> None:
        before = prereg.freeze_digest()
        original = prereg.TONE_LEXICON["hawkish"]
        try:
            prereg.TONE_LEXICON["hawkish"] = (*original, "resilient")
            assert prereg.freeze_digest() != before
        finally:
            prereg.TONE_LEXICON["hawkish"] = original
        assert prereg.freeze_digest() == before

    def test_the_two_lists_do_not_overlap(self) -> None:
        assert not set(prereg.TONE_LEXICON["hawkish"]) & set(prereg.TONE_LEXICON["dovish"])

    def test_direction_ambiguous_words_are_absent(self) -> None:
        """何が上下するかで向きが変わる語は入れない。"""
        for word in ("lower", "higher", "increase", "decrease", "reduce", "raise"):
            assert word not in prereg.TONE_LEXICON["hawkish"], word
            assert word not in prereg.TONE_LEXICON["dovish"], word

    def test_the_score_is_the_frozen_formula(self) -> None:
        """(hawkish − dovish) / 語数。"""
        text = "the committee will tighten policy because inflation is elevated but growth is weak"
        scored = statements.score(text)
        assert scored["hawkish"] == 2.0
        assert scored["dovish"] == 1.0
        assert scored["words"] == 13.0
        assert scored["tone"] == pytest.approx(1 / 13)


class TestThePlumbingAmendmentIsRecorded:
    def test_every_change_has_an_id_and_the_variables_did_not_change(self) -> None:
        amendment = prereg.FREEZE_AMENDMENT_PLUMBING
        assert amendment["status"] == "AMENDED_PRE_ALPHA_NO_SIGNAL_HAD_RUN"
        assert amendment["economic_variables_unchanged"] is True
        ids = {row["id"] for row in amendment["what_changed"]}
        assert {"P-1", "P-2", "P-3", "P-4", "P-5", "P-6", "P-7"} <= ids

    def test_the_things_that_must_not_change_are_listed(self) -> None:
        blob = " ".join(prereg.FREEZE_AMENDMENT_PLUMBING["not_changed"])
        for item in ("符号", "horizon", "benchmark", "最低 3 通貨", "cost"):
            assert item in blob, item

    def test_the_look_ahead_fix_is_explained(self) -> None:
        rows = {row["id"]: row for row in prereg.FREEZE_AMENDMENT_PLUMBING["what_changed"]}
        assert "look-ahead" in rows["P-2"]["why"]
        assert "12 週" in rows["P-3"]["why"]


class TestTheFinalExecutionSet:
    def test_five_tracks_no_replacements(self) -> None:
        final = prereg.FINAL_EXECUTION_SET
        assert final["tracks"] == prereg.EXECUTION_ORDER
        assert final["replacements_used"] == ()
        assert final["maximum_alpha_tracks"] == 5

    def test_the_known_power_limit_is_declared_before_results(self) -> None:
        assert "1.46" in prereg.FINAL_EXECUTION_SET["known_power_limits"]["U5"]

    def test_the_series_map_is_inside_the_digest(self) -> None:
        before = prereg.freeze_digest()
        row = series_map.SERIES_MAP["U2"]["USD"]
        original = row["args"]["series_name"]
        try:
            row["args"]["series_name"] = "RESPPA_F02_N.WW"
            assert prereg.freeze_digest() != before
        finally:
            row["args"]["series_name"] = original
        assert prereg.freeze_digest() == before


class TestTheSeenWindowIsJudgedOnParsedDates:
    @pytest.mark.parametrize(
        ("day", "seen"),
        [
            ("1999-01-04", True),
            ("2016-06-01", True),
            ("2016-06-02", False),
            ("2021-04-25", False),
            ("2021-04-26", False),
            ("2021-04-27", True),
            ("2025-12-26", True),
            ("2025-12-27", False),
        ],
    )
    def test_boundaries(self, day: str, seen: bool) -> None:
        assert acquire.is_seen(dt.date.fromisoformat(day)) is seen

    def test_truncation_refuses_to_keep_protected_rows(self) -> None:
        series = pd.Series(
            [1.0, 2.0, 3.0], index=pd.to_datetime(["2016-05-31", "2018-01-01", "2022-01-03"])
        )
        kept = acquire._truncate(series, label="t")
        assert [d.date().isoformat() for d in kept.index] == ["2016-05-31", "2022-01-03"]


class TestMissingCurrenciesDoNotEraseTheSpan:
    def test_a_fully_missing_currency_does_not_drop_every_day(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """P-6: 初版の dropna(how="any") は、列が 1 本でも全欠けだと全日を消した。"""
        index = pd.bdate_range("2020-01-01", periods=300)
        rng = np.random.default_rng(1)
        frame = pd.DataFrame(
            rng.normal(size=(300, 8)), index=index, columns=list(signals.CURRENCIES)
        )
        frame["GBP"] = np.nan
        frame["NZD"] = np.nan
        monkeypatch.setitem(signals.SCORERS, "U2", lambda idx, overrides=None: frame.reindex(idx))
        built = {
            "long": {
                "currency_excess_return": pd.DataFrame(
                    0.0, index=index, columns=list(signals.CURRENCIES)
                )
            }
        }
        scores = signals.scores_for("U2", built, "long")
        assert len(scores) == 300
        assert (scores["GBP"] == 0.0).all()
        assert list(scores.columns) == list(signals.CURRENCIES)

    def test_days_below_three_currencies_are_dropped_not_filled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        index = pd.bdate_range("2020-01-01", periods=100)
        frame = pd.DataFrame(np.nan, index=index, columns=list(signals.CURRENCIES))
        frame.iloc[:, :2] = 1.0  # 2 通貨しかない
        frame.iloc[50:, 2] = 1.0  # 50 日目から 3 通貨
        monkeypatch.setitem(signals.SCORERS, "U2", lambda idx, overrides=None: frame.reindex(idx))
        built = {
            "long": {
                "currency_excess_return": pd.DataFrame(
                    0.0, index=index, columns=list(signals.CURRENCIES)
                )
            }
        }
        scores = signals.scores_for("U2", built, "long")
        assert scores.index[0] == index[50]


@pytest.mark.research_data
class TestTheAcquisitionRecord:
    @pytest.fixture(scope="class")
    def record(self) -> dict:
        return json.loads(ACQUISITION.read_text(encoding="utf-8"))

    def test_every_mapped_series_was_acquired_and_semantically_checked(self, record: dict) -> None:
        for key, row in record["series"].items():
            assert row["outcome"] == "OK", key
            assert row["semantic_check"]["matched"], key

    def test_every_series_carries_the_audit_fields(self, record: dict) -> None:
        for key, row in record["series"].items():
            for field in (
                "provider",
                "series_id",
                "official_title",
                "units",
                "frequency",
                "coverage_first",
                "coverage_last",
                "publication_lag",
                "revision_behavior",
                "source_url",
                "retrieval_timestamp_utc",
                "content_hash",
            ):
                assert row.get(field) not in (None, ""), f"{key}.{field}"

    def test_no_saved_series_touches_the_protected_pool_or_forward(self, record: dict) -> None:
        for key, row in record["series"].items():
            frame = pd.read_parquet(acquire.DATA_DIR / f"{row['file']}.parquet")
            for stamp in frame.index:
                assert acquire.is_seen(stamp.date()), f"{key}: {stamp.date()}"

    def test_the_three_central_banks_were_read_from_official_archives(self, record: dict) -> None:
        tone = record["statements"]
        assert {c for c, r in tone.items() if r["outcome"] == "OK"} == {"USD", "EUR", "JPY"}
        for row in tone.values():
            for doc in row["documents_detail"]:
                assert any(
                    host in doc["url"]
                    for host in ("federalreserve.gov", "ecb.europa.eu", "boj.or.jp")
                )
                assert acquire.is_seen(dt.date.fromisoformat(doc["date"]))


@pytest.mark.research_data
class TestStageZero:
    @pytest.fixture(scope="class")
    def stage0(self) -> dict:
        return json.loads(STAGE0.read_text(encoding="utf-8"))

    def test_it_used_no_returns(self, stage0: dict) -> None:
        assert stage0["returns_used"] is False

    def test_it_carries_the_final_digest(self, stage0: dict) -> None:
        assert stage0["freeze_digest"] == prereg.freeze_digest()

    def test_every_track_passed_and_meets_the_breadth_floor(self, stage0: dict) -> None:
        assert stage0["passed"] == list(prereg.EXECUTION_ORDER)
        for track, row in stage0["tracks"].items():
            primary = row["spans"][row["primary_span"]]
            assert primary["currencies_with_signal_min"] >= 3, track


class TestTheTruncationGuardWorksOnItsOwn:
    def test_a_protected_row_that_slips_past_the_filter_still_stops_the_save(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """**二重の防御の 2 枚目**。filter が壊れても、保護 pool の行は保存されない。"""
        monkeypatch.setattr(acquire, "is_seen", lambda _day: True)
        series = pd.Series([1.0, 2.0], index=pd.to_datetime(["2016-05-31", "2018-01-01"]))
        with pytest.raises(AssertionError, match="保護 pool"):
            acquire._truncate(series, label="t")

    def test_a_forward_row_that_slips_past_the_filter_still_stops_the_save(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(acquire, "is_seen", lambda _day: True)
        series = pd.Series([1.0, 2.0], index=pd.to_datetime(["2016-05-31", "2026-03-02"]))
        with pytest.raises(AssertionError, match="forward"):
            acquire._truncate(series, label="t")
