"""取得 request が保護領域に届かないことを固定する。

**この repo は bound を 3 回抜かれている**（文字列比較、`str` subclass、曖昧な綴り）。
ここで見るのは「bound があるか」ではなく「**bound がどの経路でも効くか**」である。
"""

from __future__ import annotations

import datetime as dt

import pytest

from scripts.research.top_five import prereg, sources


class TestTheSeenWindowsAreTheOnlyPlaceSignalMayLook:
    def test_the_windows_come_from_the_freeze(self) -> None:
        long_first, long_last = sources.SEEN_WINDOWS[0]
        assert long_first.isoformat() == prereg.SPANS["long"]["first"]
        assert long_last.isoformat() == prereg.SPANS["long"]["last_return_day"]

    def test_the_protected_pool_sits_between_them_and_is_not_seen(self) -> None:
        fresh_start = dt.date.fromisoformat(prereg.PROTECTED_BOUNDS["fresh_pool_start"])
        assert not sources.is_seen(fresh_start)
        #: pool のど真ん中も、終わり際も
        assert not sources.is_seen(dt.date(2018, 6, 1))
        assert not sources.is_seen(dt.date(2021, 4, 25))

    def test_the_oos_slice_and_everything_after_is_not_seen(self) -> None:
        oos_start = dt.date.fromisoformat(prereg.PROTECTED_BOUNDS["oos_slice_start"])
        assert not sources.is_seen(oos_start)
        assert not sources.is_seen(dt.date(2026, 3, 15))  # dead window
        assert not sources.is_seen(dt.date(2026, 9, 21))  # forward epoch

    def test_the_boundary_days_themselves(self) -> None:
        """端点 1 日ずれが最も起きやすい。両側を名指しで固定する。"""
        assert sources.is_seen(dt.date(2016, 6, 1))
        assert not sources.is_seen(dt.date(2016, 6, 2))
        assert not sources.is_seen(dt.date(2021, 4, 26))
        assert sources.is_seen(dt.date(2021, 4, 27))
        assert sources.is_seen(dt.date(2025, 12, 26))
        assert not sources.is_seen(dt.date(2025, 12, 27))


class TestTheBoundIsAParsedDateNotAString:
    @pytest.mark.parametrize(
        "spelling", ["2016-06", "2016", "2016-6-2", "20160602", "2016/06/02", ""]
    )
    def test_ambiguous_spellings_are_refused(self, spelling: str) -> None:
        """`"2016-06"` を「6 月末」と読む API があり、本 repo はそこで抜かれている。"""
        with pytest.raises(ValueError, match="exact YYYY-MM-DD"):
            sources.as_day(spelling, field="end")

    def test_a_str_subclass_cannot_smuggle_a_comparison(self) -> None:
        """`__lt__` を書き換えた `str` subclass で bound を抜かれた前例がある。"""

        class Sneaky(str):
            def __lt__(self, other: object) -> bool:
                return True

            def __ge__(self, other: object) -> bool:
                return False

        parsed = sources.as_day(Sneaky("2018-06-01"), field="end")
        assert isinstance(parsed, dt.date)
        assert not isinstance(parsed, str)
        #: parse を通った後は素の date なので、subclass の細工は効かない
        assert not sources.is_seen(parsed)

    def test_a_valid_spelling_parses(self) -> None:
        assert sources.as_day("2016-06-01", field="end") == dt.date(2016, 6, 1)


class TestBoundedRequestsCannotReachProtectedData:
    def test_a_request_inside_the_protected_pool_is_refused(self) -> None:
        with pytest.raises(ValueError):
            sources.url_for("boc_10y", start=dt.date(2018, 1, 1), end=dt.date(2018, 12, 31))

    def test_a_request_straddling_the_pool_is_refused(self) -> None:
        with pytest.raises(ValueError):
            sources.url_for("boc_10y", start=dt.date(2016, 1, 1), end=dt.date(2022, 1, 1))

    def test_a_request_into_the_oos_slice_is_refused(self) -> None:
        with pytest.raises(ValueError):
            sources.url_for("boc_10y", start=dt.date(2025, 12, 1), end=dt.date(2026, 1, 31))

    def test_a_request_inside_a_seen_span_is_allowed(self) -> None:
        url = sources.url_for("boc_10y", start=dt.date(2010, 1, 1), end=dt.date(2010, 12, 31))
        assert "2010-01-01" in url and "2010-12-31" in url

    def test_the_years_requested_are_only_seen_years(self) -> None:
        """年単位 request の source が保護 pool の年を取りに行かないこと。"""
        years = sources.bounded_years()
        for protected in (2017, 2018, 2019, 2020):
            assert protected not in years, protected
        assert 2016 in years and 2021 in years

    def test_a_full_history_source_refuses_to_pretend_it_has_bounds(self) -> None:
        """URL に bound を入れられない source で `url_for` を呼ぶのは設計の誤りである。"""
        for key in ("vix", "wti", "snb_10y", "tic_s1"):
            with pytest.raises(ValueError, match="全量配信"):
                sources.url_for(key, start=dt.date(2010, 1, 1), end=dt.date(2010, 12, 31))


class TestFullHistorySourcesAreTruncatedNotTrusted:
    def test_every_source_declares_which_kind_it_is(self) -> None:
        """『request で守ったのか、取得後に守ったのか』が監査で効く。"""
        for source in sources.SOURCES:
            assert isinstance(source.bounded_request, bool)
            assert source.publication_timing.strip(), source.key

    def test_the_unbounded_ones_are_the_ones_we_expect(self) -> None:
        unbounded = {s.key for s in sources.SOURCES if not s.bounded_request}
        assert unbounded == {"vix", "wti", "bund_10y", "snb_10y", "tic_s1"}

    def test_a_frame_containing_protected_days_is_refused(self) -> None:
        days = [dt.date(2010, 1, 4), dt.date(2018, 6, 1)]
        with pytest.raises(ValueError, match="seen span の外"):
            sources.assert_no_protected_day(days, label="vix")

    def test_a_frame_of_seen_days_passes(self) -> None:
        sources.assert_no_protected_day([dt.date(2010, 1, 4), dt.date(2022, 3, 1)], label="vix")


class TestEverySourceIsPublicAndFree:
    def test_no_source_needs_a_key_or_a_login(self) -> None:
        for source in sources.SOURCES:
            lowered = source.url.lower()
            for forbidden in ("api_key", "apikey", "token=", "login", "oanda"):
                assert forbidden not in lowered, (source.key, forbidden)

    def test_every_source_belongs_to_a_frozen_track(self) -> None:
        for source in sources.SOURCES:
            assert source.track in prereg.TRACKS, source.key

    def test_every_external_track_has_at_least_one_source(self) -> None:
        covered = {source.track for source in sources.SOURCES}
        #: T4 は外部データを使わない唯一の track
        assert covered == {"T1", "T2", "T3", "T5"}

    def test_the_oil_source_says_parsing_only(self) -> None:
        """xlrd は parsing のみ。埋め込み macro を実行しない（裁定 §2）。"""
        assert "parsing のみ" in sources.BY_KEY["wti"].note
        assert "macro は実行しない" in sources.BY_KEY["wti"].note
