"""signal と執行の契約を拘束する。

**この file は実行後のレビューで欠落が判明して書かれた。** それまで `signals.py` と
`execute.py` には test が 1 つも無く、17 mutation のうち 15 が生き残っていた —
lag を 0 にする / z を centered にする / beta を反転する / vintage を m+0 にする /
cost を 0 にする、いずれも通った。

ここで守るのは **凍結した契約**であって、結果ではない。合成データで確かめられるものは
合成データで確かめ、取得済みデータが要るものだけ `research_data` gate の下に置く。
"""

from __future__ import annotations

import datetime as dt
import inspect

import numpy as np
import pandas as pd
import pytest

from scripts.research.top_five import UNIVERSE, execute, panel, prereg, signals, sources


class TestTheLagCanNeverBeZero:
    """lag=0 は「その日の値でその日の建玉を決める」ことであり、先読みそのものである。"""

    @pytest.mark.parametrize("source_key", list(prereg.PUBLICATION_TIMES))
    def test_every_declared_lag_is_at_least_one(self, source_key: str) -> None:
        row = prereg.PUBLICATION_TIMES[source_key]
        for span in ("long", "recent"):
            value = row[f"{span}_span_lag_business_days"]
            if isinstance(value, int):
                assert value >= 1, (source_key, span)

    def test_lag_for_refuses_a_non_integer(self) -> None:
        with pytest.raises(TypeError):
            signals._lag_for("tic_monthly", "long")

    def test_the_vix_lag_is_two_on_the_long_span(self) -> None:
        """ECB fix 14:15 CET は VIX close 22:15 CET より前なので 1 日では足りない。"""
        assert signals._lag_for("cboe_vix_close", "long") == 2
        assert signals._lag_for("cboe_vix_close", "recent") == 1

    def test_the_oil_lag_is_seven_on_both_spans(self) -> None:
        assert signals._lag_for("eia_wti_daily", "long") == 7
        assert signals._lag_for("eia_wti_daily", "recent") == 7

    def test_an_external_value_never_reaches_its_own_day(self) -> None:
        """合成系列で直接確かめる。lag>=1 ならその日の値はその日の行に載らない。"""
        index = pd.date_range("2010-01-04", periods=10, freq="B")
        series = pd.Series(range(10), index=index, dtype=float)
        for lag in (1, 2, 7):
            out = panel.align_to_panel(series, index, lag=lag)
            for position, day in enumerate(index):
                if position >= lag:
                    assert out.loc[day] == float(position - lag), (lag, day)


class TestTheStandardisationIsTrailing:
    def test_the_z_window_never_looks_forward(self) -> None:
        """centered 窓は明白な look-ahead である。"""
        source = inspect.getsource(signals._trailing_z)
        assert "center=True" not in source

    def test_a_late_spike_does_not_move_an_early_z(self) -> None:
        index = pd.date_range("2010-01-04", periods=400, freq="B")
        base = pd.Series(np.linspace(1.0, 2.0, 400), index=index)
        spiked = base.copy()
        spiked.iloc[-1] = 99.0
        before = signals._trailing_z(base, 252)
        after = signals._trailing_z(spiked, 252)
        #: 最後の 1 点を動かしても、それ以前の z は 1 つも変わらない
        assert (before.iloc[:-1].fillna(0) == after.iloc[:-1].fillna(0)).all()


class TestTheFrozenSignalConstantsAreTheOnlyOnes:
    def test_signals_reads_its_numbers_from_the_freeze(self) -> None:
        """定義が 2 か所にあると、digest の外で片方だけ動かせてしまう。"""
        frozen = prereg.SIGNAL_CONSTANTS
        assert frozen["z_window"] == signals.Z_WINDOW
        assert frozen["shock_lookback"] == signals.SHOCK_LOOKBACK
        assert frozen["slope_lookback"] == signals.SLOPE_LOOKBACK
        assert frozen["factor_window"] == signals.FACTOR_WINDOW
        assert frozen["partner_window"] == signals.PARTNER_WINDOW
        assert frozen["tic_window_months"] == signals.TIC_WINDOW_MONTHS
        assert frozen["max_staleness_days"] == signals.MAX_STALENESS_DAYS

    def test_the_constants_move_the_digest(self) -> None:
        before = prereg.freeze_digest()
        original = prereg.SIGNAL_CONSTANTS["shock_lookback"]
        try:
            prereg.SIGNAL_CONSTANTS["shock_lookback"] = 10
            assert prereg.freeze_digest() != before
        finally:
            prereg.SIGNAL_CONSTANTS["shock_lookback"] = original
        assert prereg.freeze_digest() == before

    def test_the_digest_as_executed_is_recorded(self) -> None:
        """digest が覆う範囲を広げたので、走った値と現在値は別である。両方残す。"""
        assert prereg.DIGEST_AS_EXECUTED.startswith("28100ebe")
        assert prereg.freeze_digest() != prereg.DIGEST_AS_EXECUTED


class TestTheFrozenDirectionsAreNotFlipped:
    def test_t1_favours_the_funding_currencies(self) -> None:
        beta = prereg.TRACKS["T1"]["direction"]["beta"]
        assert beta["JPY"] > 0 and beta["CHF"] > 0
        assert beta["AUD"] < 0 and beta["NZD"] < 0

    def test_t2_favours_the_exporters(self) -> None:
        beta = prereg.TRACKS["T2"]["direction"]["beta"]
        assert beta["CAD"] > 0
        assert beta["JPY"] < 0
        assert beta["NZD"] < 0, "NZ は原油の純輸入国"

    def test_the_broadcast_applies_the_beta_unflipped(self) -> None:
        index = pd.date_range("2010-01-04", periods=5, freq="B")
        score = pd.Series(1.0, index=index)
        out = signals._broadcast(score, {"JPY": 1.0, "AUD": -1.0})
        assert out["JPY"].iloc[0] == 1.0
        assert out["AUD"].iloc[0] == -1.0

    def test_t3_refuses_an_unregistered_hypothesis(self) -> None:
        with pytest.raises(ValueError, match="未登録"):
            signals.t3_scores(pd.DatetimeIndex([]), "recent", hypothesis="T3-H3")


class TestTheTicVintageIsNotBypassed:
    def test_the_shift_is_two_months(self) -> None:
        source = inspect.getsource(signals.t5_scores)
        assert "months=2" in source

    def test_staleness_is_counted_in_calendar_days_not_rows(self) -> None:
        """`ffill(limit=n)` は行数を数えるので、空白を 1 行で跨いでしまう。"""
        source = inspect.getsource(signals.t5_scores)
        #: コメントは除く — 何が禁じられているかを説明する文には現れてよい
        code = chr(10).join(
            line for line in source.split(chr(10)) if not line.strip().startswith("#")
        )
        assert "MAX_STALENESS_DAYS" in code
        assert "ffill(limit=" not in code

    def test_a_gap_longer_than_the_limit_produces_no_position(self) -> None:
        monthly = pd.Series([1.0], index=pd.to_datetime(["2016-03-31"]))
        index = pd.date_range("2021-04-27", periods=5, freq="B")
        union = monthly.index.union(index)
        filled = monthly.reindex(union).sort_index().ffill()
        vintage = pd.Series(monthly.index, index=monthly.index).reindex(union).sort_index().ffill()
        age = (pd.Series(union, index=union) - vintage).dt.days
        filled[age > signals.MAX_STALENESS_DAYS] = np.nan
        assert filled.reindex(index).isna().all(), "5 年前の値で建ててはならない"


class TestTheTwoYearLegGoesThroughTheBoundaryGuard:
    """唯一 `_truncate` を通らない経路で、fresh pool の値が score に届いていた。"""

    def test_the_loader_truncates(self) -> None:
        source = inspect.getsource(signals._two_year)
        assert "is_seen" in source
        assert "assert_no_protected_day" in source

    @pytest.mark.research_data
    def test_no_two_year_row_sits_outside_a_seen_window(self) -> None:
        for currency in signals.CURVE_LEGS:
            series = signals._two_year(currency)
            outside = [ts.date() for ts in series.index if not sources.is_seen(ts.date())]
            assert not outside, (currency, outside[:3])

    @pytest.mark.research_data
    def test_no_two_year_row_reaches_the_forward_epoch(self) -> None:
        cutoff = dt.date.fromisoformat(prereg.SPANS["recent"]["last_return_day"])
        for currency in signals.CURVE_LEGS:
            series = signals._two_year(currency)
            assert series.index.max().date() <= cutoff, currency


class TestTheExecutionUsesTheFrozenConfig:
    def test_every_frozen_parameter_reaches_the_book(self) -> None:
        config = execute._config("T1")
        for key, value in prereg.BOOK_CONFIG.items():
            if key in {"days_per_year", "why_max_leverage_is_not_5"}:
                continue
            assert getattr(config, key) == value, key

    def test_the_cost_multiple_defaults_to_one(self) -> None:
        """既定を 0 にすれば cost がまるごと消える。"""
        assert execute._config("T1").cost_multiple == 1.0

    def test_the_days_per_year_matches_the_freeze(self) -> None:
        assert prereg.BOOK_CONFIG["days_per_year"] == execute.TRADING_DAYS

    def test_only_t5_deviates_from_the_shared_layer(self) -> None:
        assert execute._config("T5").neutralize_leading_factor is False
        for track in ("T1", "T2", "T3", "T4"):
            assert execute._config(track).neutralize_leading_factor is True, track

    def test_the_leverage_cap_is_not_the_forbidden_five(self) -> None:
        assert execute._config("T1").max_leverage == 20.0


class TestTheBenchmarksIncludeTheRightNull:
    def test_the_constant_dollar_null_exists(self) -> None:
        """T5 は neutralize を切って走るので、静的な dollar exposure が正しい null。"""
        index = pd.date_range("2010-01-04", periods=5, freq="B")
        excess = pd.DataFrame(0.0, index=index, columns=list(UNIVERSE))
        benches = execute._benchmarks(excess)
        assert "constant_long_usd" in benches
        row = benches["constant_long_usd"].iloc[0]
        assert row["USD"] == 1.0
        assert all(row[c] < 0 for c in UNIVERSE if c != "USD")
        assert abs(float(row.sum())) < 1e-12, "ゼロサムであること"

    def test_the_momentum_benchmark_is_trailing(self) -> None:
        source = inspect.getsource(execute._benchmarks)
        assert "rolling(BENCH_LOOKBACK)" in source
        assert "center=True" not in source

    def test_the_ic_looks_one_day_forward(self) -> None:
        """`shift(0)` なら同時点相関になり、意味が変わる。"""
        assert "shift(-1)" in inspect.getsource(execute._ic)


class TestTheCapacityArithmeticUsesTheRightLeverageConcept:
    def test_margin_is_charged_on_portfolio_gross_not_risk_leverage(self) -> None:
        metrics = {
            "net_sharpe": 0.5,
            "realized_vol": 0.10,
            "portfolio_gross_leverage": 2.0,
            "max_drawdown": -0.10,
        }
        out = execute._capacity(metrics, pd.DataFrame())
        at_ten = out["scenarios"]["vol_10%"]
        #: gross 2.0、最悪 margin 0.05 -> 利用率 0.10
        assert at_ten["margin_utilisation"] == pytest.approx(0.10, abs=1e-9)
        assert at_ten["remaining_margin_buffer"] == pytest.approx(0.90, abs=1e-9)

    def test_it_uses_the_measured_volatility_not_a_constant(self) -> None:
        metrics = {
            "net_sharpe": 0.5,
            "realized_vol": 0.10,
            "portfolio_gross_leverage": 2.0,
            "max_drawdown": -0.10,
        }
        out = execute._capacity(metrics, pd.DataFrame())
        assert out["vol_per_unit_gross_measured"] == pytest.approx(0.05, abs=1e-9)

    def test_the_drawdown_and_gap_stress_are_reported(self) -> None:
        metrics = {
            "net_sharpe": 0.5,
            "realized_vol": 0.10,
            "portfolio_gross_leverage": 2.0,
            "max_drawdown": -0.10,
        }
        out = execute._capacity(metrics, pd.DataFrame())
        for key in ("scaled_max_drawdown", "gap_stress_2pct_adverse", "remaining_margin_buffer"):
            assert key in out["scenarios"]["vol_15%"], key

    def test_a_non_positive_sharpe_is_not_rescued_by_leverage(self) -> None:
        out = execute._capacity(
            {
                "net_sharpe": -0.1,
                "realized_vol": 0.1,
                "portfolio_gross_leverage": 2.0,
                "max_drawdown": -0.1,
            },
            pd.DataFrame(),
        )
        assert out["reachable"] is False
