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

    def test_a_refusal_is_not_swallowed_into_a_retry(self, monkeypatch) -> None:
        """再試行が入っても、**拒否は 1 回目で抜ける**こと。

        `_fetch` は一過性の切断だけを再試行する。拒否まで再試行すれば、guard は
        「何度も聞かれて最後に通る」ものに変わってしまう。
        """
        monkeypatch.delenv(acquire.OPT_IN_ENV, raising=False)
        calls = {"n": 0}
        real = acquire.require_opt_in

        def counted(*args, **kwargs):
            calls["n"] += 1
            return real(*args, **kwargs)

        monkeypatch.setattr(acquire, "require_opt_in", counted)
        with pytest.raises(AcquisitionRefusedError):
            acquire._fetch("https://example.invalid/never-requested")
        assert calls["n"] == 1, "拒否が再試行されている"

    def test_the_refusal_type_is_outside_the_retried_set(self) -> None:
        from scripts.research.acquisition_safety import NETWORK_FAILURES

        assert not issubclass(AcquisitionRefusedError, NETWORK_FAILURES)

    def test_a_provider_status_is_not_retried(self) -> None:
        """404 は相手の返事である。何度聞いても 404 なので再試行しない。"""
        source = inspect.getsource(acquire._fetch)
        assert "except urllib.error.HTTPError" in source
        assert "raise" in source.split("except urllib.error.HTTPError")[1][:120]

    def test_the_permission_is_checked_inside_the_retry_loop(self) -> None:
        source = inspect.getsource(acquire._fetch)
        loop = source.index("for _ in range(ATTEMPTS)")
        assert source.index("require_opt_in", loop) > loop


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
    def test_every_daily_parser_goes_through_truncate(self) -> None:
        """raw frame が外へ出る経路を持たせない。"""
        for key, parser in acquire.PARSERS.items():
            source = inspect.getsource(parser)
            if key == "tic_s1":
                #: 月次は vintage 日で切る。観測月で切ると保護 pool の月を抱える
                assert "is_seen" in source and "months=2" in source, key
            else:
                assert "_truncate" in source, key

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
