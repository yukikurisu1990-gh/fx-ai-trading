"""共有 FX panel が、両 span で同じ構成になっていることを固定する。

**構成が 1 つであることが、2 つの span を同じ表に並べられる唯一の根拠**である。
data source は違ってよいが、pair return → 符号を揃えた通貨平均 → cross-section 平均の
除去、という手順は両方で同一でなければならない。
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from scripts.research.top_five import UNIVERSE, panel, prereg


@pytest.fixture(scope="module")
def built() -> dict:
    return panel.build()


class TestBothSpansUseOneConstruction:
    def test_the_excess_panel_is_cross_sectionally_neutral(self, built: dict) -> None:
        """cross-section 平均を引いたのだから、各日の合計はゼロである。"""
        for span in ("long", "recent"):
            excess = built[span]["currency_excess_return"]
            assert float(excess.mean(axis=1).abs().max()) < 1e-12, span

    def test_both_spans_carry_the_same_currencies(self, built: dict) -> None:
        for span in ("long", "recent"):
            assert tuple(built[span]["currency_excess_return"].columns) == UNIVERSE, span

    def test_every_currency_has_legs_on_both_spans(self, built: dict) -> None:
        for span in ("long", "recent"):
            coverage = built[span]["coverage"]["legs_per_currency"]
            assert int(coverage.min()) >= 1, (span, coverage.to_dict())

    def test_the_construction_is_recorded_as_shared(self, built: dict) -> None:
        assert "両 span で同一" in built["provenance"]["construction"]


class TestThePanelMatchesTheFrozenSpans:
    def test_the_recent_span_starts_and_ends_where_the_freeze_says(self, built: dict) -> None:
        assert built["provenance"]["recent"]["first"] == prereg.SPANS["recent"]["first"]

    def test_the_recent_span_day_count_is_pinned(self, built: dict) -> None:
        """凍結した日付から出る行数。ここが動いたら cache か暦の扱いが変わっている。"""
        assert built["provenance"]["recent"]["days"] == 1213
        assert built["provenance"]["long"]["days"] == 4458

    def test_the_recent_span_ends_where_the_freeze_says(self, built: dict) -> None:
        assert built["provenance"]["recent"]["last"] == prereg.SPANS["recent"]["last_return_day"]

    def test_the_long_span_ends_where_the_freeze_says(self, built: dict) -> None:
        assert built["provenance"]["long"]["last"] == prereg.SPANS["long"]["last_return_day"]

    def test_no_row_falls_outside_a_seen_window(self, built: dict) -> None:
        from scripts.research.top_five import sources

        for span in ("long", "recent"):
            days = [ts.date() for ts in built[span]["currency_excess_return"].index]
            assert all(sources.is_seen(day) for day in days), span

    def test_the_protected_pool_has_no_row_at_all(self, built: dict) -> None:
        pool = (dt.date(2016, 6, 2), dt.date(2021, 4, 25))
        for span in ("long", "recent"):
            days = [ts.date() for ts in built[span]["currency_excess_return"].index]
            assert not [d for d in days if pool[0] <= d <= pool[1]], span


class TestTheRecentPanelReadsNoArchive:
    def test_it_says_so_and_the_caches_are_the_seen_ones(self, built: dict) -> None:
        assert built["provenance"]["recent"]["no_archive_read"] is True
        assert panel.RECENT_CACHES == (
            "momentum_replication_b",
            "supplemental_replication",
            "exploratory_round_1",
        )

    def test_the_three_caches_tile_the_span_without_a_hole(self, built: dict) -> None:
        """穴があれば run_book が『連続でない』と落ちる。先にここで見る。"""
        index = built["recent"]["currency_excess_return"].index
        gaps = pd.Series(index).diff().dt.days.dropna()
        #: 週末と祝日で 3-4 日は開く。それ以上開いたら cache の継ぎ目が疑わしい
        assert int(gaps.max()) <= 5, f"最大 {int(gaps.max())} 日の空白"


class TestTheLagHelperCountsBusinessDaysNotCalendarDays:
    def test_an_external_series_is_forward_filled_then_shifted(self) -> None:
        """休場日が FX と一致しないので、ffill してから panel の行で送る。"""
        index = pd.to_datetime(["2010-01-04", "2010-01-05", "2010-01-06", "2010-01-07"])
        series = pd.Series([1.0, 2.0], index=pd.to_datetime(["2010-01-04", "2010-01-06"]))
        out = panel.align_to_panel(series, index, lag=1)
        #: 1/5 は ffill で 1.0、それを 1 行送るので 1/6 に現れる
        assert out.loc["2010-01-05"] == 1.0
        assert out.loc["2010-01-06"] == 1.0
        assert np.isnan(out.loc["2010-01-04"])

    def test_a_two_day_lag_moves_two_panel_rows(self) -> None:
        index = pd.to_datetime(["2010-01-04", "2010-01-05", "2010-01-06", "2010-01-07"])
        series = pd.Series([5.0], index=pd.to_datetime(["2010-01-04"]))
        out = panel.align_to_panel(series, index, lag=2)
        assert np.isnan(out.loc["2010-01-05"])
        assert out.loc["2010-01-06"] == 5.0

    def test_a_zero_lag_is_refused(self) -> None:
        with pytest.raises(ValueError, match="1 営業日以上"):
            panel.business_day_lag(pd.DataFrame({"x": [1.0]}), 0)

    def test_the_lag_never_lets_today_inform_today(self) -> None:
        """lag >= 1 なら、その日の値がその日の行に載ることはない。"""
        index = pd.to_datetime(["2010-01-04", "2010-01-05", "2010-01-06"])
        series = pd.Series([1.0, 2.0, 3.0], index=index)
        out = panel.align_to_panel(series, index, lag=1)
        assert out.loc["2010-01-05"] == 1.0  # 前日の値
        assert out.loc["2010-01-06"] == 2.0


class TestTheCarryLegAbsenceIsDisclosed:
    def test_the_provenance_says_spot_only(self, built: dict) -> None:
        assert "CARRY_LEG_ABSENT" in built["provenance"]["carry_leg"]
        assert "SPOT_ONLY" in built["provenance"]["carry_leg"]
