"""取得層が、許可と境界の両方で守られていることを固定する。

裁定 §7 が要求するのは「opt-in guard が壊れても live network へ到達できない構造」である。
したがってここで見るのは **guard が 1 枚かどうか**であり、`_fetch` に fallback が
戻っていないかである — 本 repo は「拒否を握りつぶして curl へ落ちる」経路で
一度 network へ出ている。
"""

from __future__ import annotations

import datetime as dt
import inspect

import pandas as pd
import pytest

from scripts.research.acquisition_safety import AcquisitionRefusedError
from scripts.research.top_five import acquire, sources


class TestNetworkNeedsTheOptInEveryTime:
    def test_fetch_refuses_without_the_env(self, monkeypatch) -> None:
        monkeypatch.delenv(acquire.OPT_IN_ENV, raising=False)
        with pytest.raises(AcquisitionRefusedError):
            acquire._fetch("https://example.invalid/never-requested")

    def test_importing_the_module_fetches_nothing(self) -> None:
        """import しただけで network に出る module が本 repo には実在した。"""
        source = inspect.getsource(acquire)
        module_body = source.split("def _fetch")[0]
        for call in ("urlopen(", "urlretrieve(", "requests.get("):
            assert call not in module_body, call

    def test_there_is_exactly_one_place_that_opens_a_socket(self) -> None:
        source = inspect.getsource(acquire)
        assert source.count("urlopen(") == 1

    def test_the_fetch_has_no_subprocess_fallback(self) -> None:
        """curl へ落ちる fallback が、conftest の socket guard を迂回した前例がある。"""
        source = inspect.getsource(acquire)
        for escape in ("subprocess", "shutil.which", "os.system", "popen"):
            assert escape not in source.lower(), escape

    def test_a_refusal_is_not_swallowed_into_a_retry(self) -> None:
        fetch_source = inspect.getsource(acquire._fetch)
        assert "except" not in fetch_source


class TestNothingOutsideTheSeenSpansSurvivesTruncation:
    @staticmethod
    def _frame(days: list[str]) -> pd.DataFrame:
        return pd.DataFrame({"x": range(len(days))}, index=pd.to_datetime(pd.Series(days)))

    def test_protected_rows_are_dropped(self) -> None:
        frame = self._frame(["2010-03-01", "2018-06-01", "2022-03-01", "2026-01-05"])
        kept = acquire._truncate(frame, label="test")
        assert [ts.date().isoformat() for ts in kept.index] == ["2010-03-01", "2022-03-01"]

    def test_a_frame_entirely_inside_the_pool_becomes_empty(self) -> None:
        frame = self._frame(["2017-01-03", "2018-06-01", "2020-12-31"])
        assert acquire._truncate(frame, label="test").empty

    def test_a_string_index_is_refused_rather_than_compared(self) -> None:
        """文字列のまま比較させない — bound を 3 回抜かれた経路である。"""
        frame = pd.DataFrame({"x": [1, 2]}, index=["2010-03-01", "2018-06-01"])
        with pytest.raises(TypeError, match="DatetimeIndex"):
            acquire._truncate(frame, label="test")

    def test_the_boundary_rows_land_on_the_right_side(self) -> None:
        frame = self._frame(["2016-06-01", "2016-06-02", "2025-12-26", "2025-12-29"])
        kept = [ts.date().isoformat() for ts in acquire._truncate(frame, label="t").index]
        assert kept == ["2016-06-01", "2025-12-26"]


class TestTheParsersReturnOnlyTruncatedFrames:
    def test_every_parser_goes_through_truncate(self) -> None:
        """raw frame が外へ出る経路を持たせない。"""
        for key, parser in acquire.PARSERS.items():
            target = parser if key in {"vix", "wti"} else acquire._parse_generic_daily
            assert "_truncate" in inspect.getsource(target), key

    def test_every_source_with_a_parser_is_a_frozen_source(self) -> None:
        for key in acquire.PARSERS:
            assert key in sources.BY_KEY, key

    def test_the_oil_parser_reads_cells_not_macros(self) -> None:
        """xlrd は worksheet の cell を読むだけで VBA project を評価しない（裁定 §2）。"""
        source = inspect.getsource(acquire._parse_wti)
        assert 'engine="xlrd"' in source
        assert "macro" in source


class TestTheProvenanceRecordsWhatTheRulingListed:
    def test_the_record_fields_cover_the_required_nine(self) -> None:
        source = inspect.getsource(acquire.acquire_one)
        for field in (
            "provider",
            "url",
            "request_parameters",
            "retrieval_timestamp",
            "http_status",
            "content_hash",
            "coverage",
            "frequency",
            "publication_timing",
        ):
            assert field in source, field

    def test_the_record_writer_refuses_a_silent_overwrite(self) -> None:
        source = inspect.getsource(acquire.main)
        assert "write_provenance" in source
        assert "write_text" not in source

    def test_bounded_sources_build_their_urls_through_the_guard(self) -> None:
        """`url_for` を通さずに URL を組み立てる経路が無いこと。"""
        source = inspect.getsource(acquire.acquire_one)
        assert "sources.url_for" in source
        assert ".format(" not in source


class TestTheYearlyRequestsSkipTheProtectedYears:
    def test_the_requested_years_exclude_the_pool(self) -> None:
        years = sources.bounded_years()
        assert not ({2017, 2018, 2019, 2020} & set(years))

    def test_a_yearly_url_for_a_protected_year_cannot_be_built(self) -> None:
        with pytest.raises(ValueError):
            sources.url_for("ust_10y", start=dt.date(2019, 1, 1), end=dt.date(2019, 12, 31))
