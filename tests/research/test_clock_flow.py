"""Tests for the unit convention, the institutional clock and the currency book.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

These pin the three things the frontier correction turned on: that a pip is not a
basis point, that a benchmark fix is a *local* time, and that a currency position
and the pairs implementing it are the same position. Each of the first three
classes below fails on a plausible wrong implementation, which is the only reason
to write them — a fixture built from the constant under test cannot fail, and
this programme has shipped one of those before.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from scripts.research.clock_flow import CURRENCIES, WINDOW_BARS, clock, currency, frontier
from scripts.research.exploratory_m15 import PAIRS
from scripts.research.fxunits import (
    COST_MULTIPLE_FOR_HURDLE,
    HALF_SPREAD_ADDITION_PIPS,
    POWER_MULTIPLIER,
    pips_to_bp,
    verify_unit_consistency,
)


class TestUnits:
    def test_one_pip_is_a_different_basis_point_count_on_each_pair(self) -> None:
        """The whole reason the old frontier's two columns were not comparable."""
        eur = float(pips_to_bp(1.0, 0.0001, 1.08))
        jpy = float(pips_to_bp(1.0, 0.01, 150.0))
        assert eur == pytest.approx(0.9259, abs=1e-4)
        assert jpy == pytest.approx(0.6667, abs=1e-4)
        #: Within 10% on EUR_USD, which is how the mix survived a reading, and
        #: 39% apart between the two pairs, which is why it must not.
        assert abs(eur - jpy) / jpy > 0.35

    def test_conversion_scales_with_the_mid_rather_than_being_a_constant(self) -> None:
        cheap = float(pips_to_bp(1.0, 0.01, 100.0))
        dear = float(pips_to_bp(1.0, 0.01, 160.0))
        assert cheap == pytest.approx(dear * 1.6, rel=1e-9)

    def test_a_field_not_in_basis_points_is_reported(self) -> None:
        verdict = verify_unit_consistency({"cell": {"gross_pips": 3.0, "net_bp": 1.0}})
        assert verdict["status"] == "UNIT_CONSISTENCY_FAILED"
        assert verdict["numeric_fields_not_in_bp"] == ["root.cell.gross_pips"]

    def test_an_all_bp_record_passes(self) -> None:
        verdict = verify_unit_consistency({"cell": {"gross_bp": 3.0, "n_events": 12}})
        assert verdict["status"] == "UNIT_CONSISTENCY_VERIFIED"

    def test_the_count_escape_is_narrow(self) -> None:
        """A declared count subtree is skipped; a sibling is still checked."""
        record = {
            "counts": {"_unit": "count", "15:00": 374, "16:00": 250},
            "money": {"gross_pips": 1.0},
        }
        verdict = verify_unit_consistency(record)
        assert verdict["numeric_fields_not_in_bp"] == ["root.money.gross_pips"]

    def test_a_count_marker_does_not_leak_to_the_parent(self) -> None:
        record = {"_unit": "count", "outer_pips": 1.0, "inner": {"also_pips": 2.0}}
        assert verify_unit_consistency({"wrapped": record})["numeric_fields_not_in_bp"] == []
        #: ...but only because the marker is on that dict. Move it and the
        #: fields are checked again.
        record.pop("_unit")
        assert len(verify_unit_consistency({"wrapped": record})["numeric_fields_not_in_bp"]) == 2

    def test_the_power_multiplier_is_the_two_sided_eighty_per_cent_constant(self) -> None:
        from scipy import stats

        assert (
            pytest.approx(stats.norm.ppf(0.975) + stats.norm.ppf(0.80), abs=5e-4)
            == POWER_MULTIPLIER
        )


class TestClock:
    @pytest.mark.parametrize(
        ("day", "expected"),
        [
            (dt.date(2022, 1, 17), "16:00"),  # London on GMT
            (dt.date(2022, 7, 18), "15:00"),  # London on BST
            (dt.date(2023, 3, 26), "15:00"),  # BST begins, last Sunday of March
            (dt.date(2023, 3, 24), "16:00"),  # the Friday before it
            (dt.date(2023, 10, 29), "16:00"),  # BST ends
            (dt.date(2023, 10, 27), "15:00"),  # the Friday before it
        ],
    )
    def test_the_london_fix_follows_british_summer_time(self, day: dt.date, expected: str) -> None:
        assert clock.moment_utc(day, "london_fix").strftime("%H:%M") == expected

    @pytest.mark.parametrize(
        ("day", "cut", "rollover"),
        [
            (dt.date(2023, 1, 10), "15:00", "22:00"),  # EST
            (dt.date(2023, 7, 10), "14:00", "21:00"),  # EDT
        ],
    )
    def test_new_york_moments_follow_united_states_daylight_time(
        self, day: dt.date, cut: str, rollover: str
    ) -> None:
        assert clock.moment_utc(day, "ny_option_cut").strftime("%H:%M") == cut
        assert clock.moment_utc(day, "rollover").strftime("%H:%M") == rollover

    def test_the_two_zones_change_on_different_dates(self) -> None:
        """Between 12 and 19 March 2023 New York is on EDT and London on GMT.

        A single "is it summer" flag would put both on the same side and get this
        fortnight wrong every year.
        """
        day = dt.date(2023, 3, 15)
        assert clock.moment_utc(day, "london_fix").strftime("%H:%M") == "16:00"
        assert clock.moment_utc(day, "ny_option_cut").strftime("%H:%M") == "14:00"

    def test_tokyo_has_no_daylight_saving(self) -> None:
        for day in (dt.date(2023, 1, 10), dt.date(2023, 7, 10)):
            assert clock.moment_utc(day, "tokyo_fix").strftime("%H:%M") == "00:55"

    def test_month_end_is_the_last_observed_day_not_the_calendar_last(self) -> None:
        """31 December is a holiday in most years; the flow follows the open day."""
        days = [dt.date(2023, 12, d) for d in (27, 28, 29)] + [dt.date(2024, 1, 2)]
        assert clock.month_end_days(days) == {dt.date(2023, 12, 29), dt.date(2024, 1, 2)}

    def test_quarter_end_is_a_strict_subset_of_month_end(self) -> None:
        days = [dt.date(2023, m, 28) for m in range(1, 13)]
        month_ends = clock.month_end_days(days)
        quarter_ends = clock.quarter_end_days(days)
        assert quarter_ends < month_ends
        assert {d.month for d in quarter_ends} == {3, 6, 9, 12}

    def test_describe_declares_its_subtree_as_counts(self) -> None:
        record = clock.describe([dt.date(2023, 1, 10), dt.date(2023, 7, 10)])
        assert record["_unit"] == "count"
        assert record["london_fix"]["utc_times_observed"] == {"15:00": 1, "16:00": 1}


class TestCurrencyBook:
    def test_every_pair_contributes_two_legs(self) -> None:
        assert sum(currency.COUNTERPARTIES.values()) == 2 * len(PAIRS)
        assert set(currency.COUNTERPARTIES) == set(CURRENCIES)

    def test_coverage_is_uneven_and_that_is_reported_not_assumed(self) -> None:
        assert currency.COUNTERPARTIES["USD"] == 7
        assert currency.COUNTERPARTIES["CAD"] == 3
        assert currency.COUNTERPARTIES["NZD"] == 3

    def test_pair_weights_reproduce_the_currency_return_exactly(self) -> None:
        """The identity that makes `H-003` impossible to repeat by accident.

        `Σ_p w_p r_p` is not approximately `Σ_c s_c r_c`; it is the same number.
        """
        rng = np.random.default_rng(11)
        for _ in range(200):
            pair_returns = {p: float(rng.normal(0.0, 10.0)) for p in PAIRS}
            signal = currency.neutralise({c: float(rng.normal()) for c in CURRENCIES})
            by_currency = currency.currency_returns(pair_returns)
            direct = sum(signal[c] * by_currency[c] for c in signal)
            via_pairs = sum(w * pair_returns[p] for p, w in currency.pair_weights(signal).items())
            assert direct == pytest.approx(via_pairs, abs=1e-12)

    def test_a_neutralised_signal_carries_no_net_currency_exposure(self) -> None:
        rng = np.random.default_rng(12)
        for _ in range(200):
            signal = currency.neutralise({c: float(rng.normal()) for c in CURRENCIES})
            assert sum(signal.values()) == pytest.approx(0.0, abs=1e-12)
            assert sum(abs(v) for v in signal.values()) == pytest.approx(2.0, abs=1e-12)

    def test_neutralising_removes_a_common_shift(self) -> None:
        """Adding the same number to every currency changes nothing.

        A signal that is really "the dollar moved" has no cross-sectional content,
        and after neutralising it has no position either.
        """
        base = {c: float(i) for i, c in enumerate(CURRENCIES)}
        shifted = {c: v + 3.7 for c, v in base.items()}
        first, second = currency.neutralise(base), currency.neutralise(shifted)
        for c in first:
            assert first[c] == pytest.approx(second[c], abs=1e-12)

    def test_a_flat_signal_takes_no_position(self) -> None:
        assert currency.neutralise({c: 1.0 for c in CURRENCIES}) == {}

    def test_a_missing_pair_is_dropped_rather_than_read_as_no_change(self) -> None:
        """A gap must not be read as "the currency did not move".

        The three `NZD` legs carry mixed signs — `NZD` is the quote of `AUD_NZD`
        and the base of the other two — so the returns are chosen to make every
        *signed* leg `+5`. Dropping one then leaves the index at `+5`, while
        treating the gap as a zero would drag it to `+3.33`.
        """
        full = {p: (-5.0 if p.split("_")[1] == "NZD" else 5.0) for p in PAIRS}
        partial = {p: v for p, v in full.items() if p != "NZD_USD"}
        assert currency.currency_returns(full)["NZD"] == pytest.approx(5.0)
        assert currency.currency_returns(partial)["NZD"] == pytest.approx(5.0)
        #: The zero-filled alternative, written out so the contrast is visible.
        zero_filled = dict(partial, NZD_USD=0.0)
        assert currency.currency_returns(zero_filled)["NZD"] == pytest.approx(10.0 / 3.0)


def _frame(start: str, periods: int, *, spread: float = 1.0, tz: str = "UTC") -> pd.DataFrame:
    index = pd.date_range(start, periods=periods, freq="15min", tz=tz)
    price = np.linspace(1.10, 1.10 + 0.0001 * periods, periods)
    return pd.DataFrame(
        {
            "ts": index,
            "mid_o": price,
            "mid_c": price + 0.0001,
            "spread_close_pips": np.full(periods, spread),
            "pip_size": np.full(periods, 0.0001),
        }
    )


class TestPanelArrays:
    def test_a_non_utc_timezone_is_refused(self) -> None:
        frame = _frame("2023-01-02 00:00", 8, tz="Asia/Tokyo")
        with pytest.raises(ValueError, match="not proven UTC"):
            frontier.PanelArrays({"EUR_USD": frame})

    def test_a_naive_column_is_refused(self) -> None:
        frame = _frame("2023-01-02 00:00", 8)
        frame["ts"] = frame["ts"].dt.tz_localize(None)
        with pytest.raises(ValueError, match="not proven UTC"):
            frontier.PanelArrays({"EUR_USD": frame})

    def test_a_zero_offset_zone_that_is_not_utc_is_accepted_and_is_the_same_instant(
        self,
    ) -> None:
        """`Etc/GMT` is not `UTC` by name but is by offset, which is the test.

        The check is on the offset precisely because a name comparison would
        reject an equivalent zone and accept nothing safer.
        """
        frame = _frame("2023-01-02 00:00", 8, tz="Etc/GMT")
        arrays = frontier.PanelArrays({"EUR_USD": frame})
        assert str(arrays.ts["EUR_USD"][0]) == "2023-01-02T00:00:00.000000000"

    def test_the_bar_containing_a_moment_belongs_to_neither_window(self) -> None:
        """Tokyo's fix at 00:55 UTC falls inside the bar stamped 00:45."""
        frame = _frame("2023-01-02 00:00", 12)
        arrays = frontier.PanelArrays({"EUR_USD": frame})
        moment = pd.Timestamp("2023-01-02 00:55", tz="UTC")
        before = arrays.last_bar_ending_by("EUR_USD", moment)
        after = arrays.bar_at_or_after("EUR_USD", moment)
        assert str(arrays.ts["EUR_USD"][before]).startswith("2023-01-02T00:30")
        assert str(arrays.ts["EUR_USD"][after]).startswith("2023-01-02T01:00")
        #: The 00:45 bar sits between them and is used by neither.
        assert after - before == 2

    def test_a_moment_on_the_grid_ends_the_pre_window_exactly_at_it(self) -> None:
        frame = _frame("2023-01-02 14:00", 12)
        arrays = frontier.PanelArrays({"EUR_USD": frame})
        moment = pd.Timestamp("2023-01-02 15:00", tz="UTC")
        before = arrays.last_bar_ending_by("EUR_USD", moment)
        after = arrays.bar_at_or_after("EUR_USD", moment)
        #: The pre-window's last bar closes at the moment, the post-window's
        #: first bar opens at it, and no bar is shared.
        assert str(arrays.ts["EUR_USD"][before]).startswith("2023-01-02T14:45")
        assert str(arrays.ts["EUR_USD"][after]).startswith("2023-01-02T15:00")
        assert after - before == 1

    def test_a_one_hour_window_is_four_bars(self) -> None:
        assert WINDOW_BARS == 4
        frame = _frame("2023-01-02 14:00", 12)
        arrays = frontier.PanelArrays({"EUR_USD": frame})
        moment = pd.Timestamp("2023-01-02 15:00", tz="UTC")
        exit_ = arrays.last_bar_ending_by("EUR_USD", moment)
        entry = exit_ - (WINDOW_BARS - 1)
        span = pd.Timestamp(arrays.ts["EUR_USD"][exit_]) - pd.Timestamp(arrays.ts["EUR_USD"][entry])
        assert span == pd.Timedelta(minutes=45)  # four bars, closing 60 minutes later

    def test_cost_is_charged_at_both_ends_not_twice_at_the_entry(self) -> None:
        """A window ending in a wide-spread bar must pay for it.

        The rollover spike is the whole reason: charging the entry spread twice
        would price a trade out of a liquidity hole at the cost of the hole it
        started in.
        """
        frame = _frame("2023-01-02 14:00", 8, spread=1.0)
        frame.loc[5, "spread_close_pips"] = 21.0
        arrays = frontier.PanelArrays({"EUR_USD": frame})
        _, cost = arrays.window("EUR_USD", 2, 5)
        cheap_only = float(
            pips_to_bp(1.0 + HALF_SPREAD_ADDITION_PIPS, 0.0001, frame["mid_o"].iat[2])
        )
        assert cost > 5.0 * cheap_only

    def test_the_return_and_the_cost_are_the_same_basis_point(self) -> None:
        """A one-pip move and a one-pip spread must come out the same size."""
        frame = _frame("2023-01-02 14:00", 8, spread=0.0)
        frame["mid_c"] = frame["mid_o"] + 0.0001  # exactly one pip
        arrays = frontier.PanelArrays({"EUR_USD": frame})
        ret_bp, cost_bp = arrays.window("EUR_USD", 2, 2)
        #: The cost model adds half a pip on top of a zero spread, so the round
        #: trip is half the size of the one-pip move. Not to the last digit: the
        #: two halves are converted at the entry mid and the exit mid, which
        #: differ by that same pip. That residual is the per-observation
        #: conversion working, and a constant-mid implementation would make this
        #: assertion exact while being wrong about `USD_JPY`.
        assert cost_bp == pytest.approx(ret_bp / 2.0, rel=1e-3)
        assert cost_bp != ret_bp / 2.0


class TestHurdleScale:
    def test_the_hurdle_and_the_effect_are_on_one_notional(self) -> None:
        """The defect the correction fixed, stated as an executable check.

        A portfolio's gross return and its cost must be measured on the same
        book. Comparing a twenty-pair basket's effect against one pair's spread —
        which the old frontier did — understates the hurdle by the traded
        notional, about 1.55x, before the spread profile is even considered.
        """
        rng = np.random.default_rng(13)
        notionals = []
        for _ in range(2000):
            signal = currency.neutralise({c: float(rng.normal()) for c in CURRENCIES})
            notionals.append(sum(abs(w) for w in currency.pair_weights(signal).values()))
        traded = float(np.mean(notionals))
        assert traded == pytest.approx(1.55, abs=0.05)

        flat_cost = {p: 2.0 for p in PAIRS}
        returns = {p: 0.0 for p in PAIRS}
        signal = currency.neutralise({c: float(rng.normal()) for c in CURRENCIES})
        book = currency.portfolio(signal, returns, flat_cost)
        #: The book pays the traded notional times the per-pair cost, not the
        #: per-pair cost.
        assert book["cost_bp"] == pytest.approx(book["traded_notional"] * 2.0, rel=1e-12)
        assert book["cost_bp"] > 2.0

    def test_the_hurdle_is_twice_the_cost(self) -> None:
        assert COST_MULTIPLE_FOR_HURDLE == 2.0


def _week(spread: float = 1.0) -> pd.DataFrame:
    """A real trading week: a Friday, a weekend gap, a short Sunday reopen, then
    Monday to Friday.

    The gap is the point. Every defect this class pins was invisible to a
    contiguous synthetic frame, which is what the first thirty-seven tests used
    and why an audit rather than a test found them.
    """
    sessions = [
        ("2023-01-06 00:00", 96),  # Friday
        ("2023-01-08 22:00", 4),  # Sunday reopen: 22:00-22:45, a partial session
        ("2023-01-09 00:00", 96),
        ("2023-01-10 00:00", 96),
        ("2023-01-11 00:00", 96),
        ("2023-01-12 00:00", 96),
        ("2023-01-13 00:00", 96),
    ]
    index = pd.DatetimeIndex(
        [
            stamp
            for start, periods in sessions
            for stamp in pd.date_range(start, periods=periods, freq="15min", tz="UTC")
        ]
    )
    frame = pd.DataFrame({"ts": index})
    n = len(frame)
    frame["mid_o"] = np.linspace(1.10, 1.10 + 0.0001 * n, n)
    frame["mid_c"] = frame["mid_o"] + 0.00005
    frame["spread_close_pips"] = spread
    frame["pip_size"] = 0.0001
    return frame


class TestTradingDays:
    def test_a_partial_session_is_not_a_trading_day(self) -> None:
        """Sunday's four bars are a reopen, not a day.

        Counting Sundays made every clock cell 16.5% Friday-and-weekly-open, and
        made `events_per_year` divide a day count by itself.
        """
        arrays = frontier.PanelArrays({"EUR_USD": _week()})
        assert len(arrays.all_days) == 7
        assert len(arrays.days) == 6
        assert arrays.partial_days == 1
        assert dt.date(2023, 1, 8) not in arrays.days

    def test_years_comes_from_the_calendar_span_not_the_day_count(self) -> None:
        """`n_days / 252` returns the constant it divided by, never a measurement."""
        arrays = frontier.PanelArrays({"EUR_USD": _week()})
        assert arrays.years == pytest.approx(7 / 365.25, rel=1e-9)
        assert arrays.years != pytest.approx(len(arrays.days) / 252.0)


class TestMomentProximity:
    def test_a_sunday_moment_resolves_to_fridays_last_hour(self) -> None:
        """The defect, demonstrated: contiguity alone cannot see a 46-hour miss.

        `last_bar_ending_by(Sunday 16:00Z)` returns Friday's final bar, whose own
        four-bar span is perfectly contiguous, so the pre-window passed every
        check the first version applied.
        """
        arrays = frontier.PanelArrays({"EUR_USD": _week()})
        sunday_fix = pd.Timestamp("2023-01-08 16:00", tz="UTC")
        found = arrays.last_bar_ending_by("EUR_USD", sunday_fix)
        assert found is not None
        landed = pd.Timestamp(arrays.ts["EUR_USD"][found])
        assert landed == pd.Timestamp("2023-01-06 23:45")
        assert arrays.contiguous("EUR_USD", found - 3, found)  # the old test passed
        #: ...and it is 46 hours from the moment it claims to measure.
        gap = sunday_fix.tz_localize(None) - (landed + frontier.BAR)
        assert gap >= pd.Timedelta(hours=40)

    def test_no_cell_counts_more_events_than_there_are_trading_days(self) -> None:
        arrays = frontier.PanelArrays(dict.fromkeys(PAIRS, _week()))
        cells = frontier.clock_designs(arrays)
        assert cells
        for name, cell in cells.items():
            assert cell["n_events"] <= len(arrays.days), name

    def test_every_cell_reports_how_many_windows_missed_their_moment(self) -> None:
        """The count is on the record, so a future contamination is visible.

        This fixture cannot produce a miss — its six trading days all carry full
        sessions — so the assertion is that the field exists and is honest at
        zero, not that it fires. What the miss looks like is
        `test_a_sunday_moment_resolves_to_fridays_last_hour`.
        """
        arrays = frontier.PanelArrays(dict.fromkeys(PAIRS, _week()))
        cells = frontier.clock_designs(arrays)
        assert cells
        for name, cell in cells.items():
            assert cell["pair_windows_dropped_as_far_from_the_moment"] >= 0, name

    def test_the_weekly_reopen_is_not_an_entry(self) -> None:
        """`contiguous(entry - 1, ...)` requires the market to have been open."""
        arrays = frontier.PanelArrays({"EUR_USD": _week()})
        reopen = arrays.bar_at_or_after("EUR_USD", pd.Timestamp("2023-01-08 22:00", tz="UTC"))
        assert pd.Timestamp(arrays.ts["EUR_USD"][reopen]) == pd.Timestamp("2023-01-08 22:00")
        assert not arrays.contiguous("EUR_USD", reopen - 1, reopen + 3)
        middle = arrays.bar_at_or_after("EUR_USD", pd.Timestamp("2023-01-10 12:00", tz="UTC"))
        assert arrays.contiguous("EUR_USD", middle - 1, middle + 3)

    def test_contiguous_sees_the_weekend_gap(self) -> None:
        arrays = frontier.PanelArrays({"EUR_USD": _week()})
        friday_close = 95
        assert pd.Timestamp(arrays.ts["EUR_USD"][friday_close]) == pd.Timestamp("2023-01-06 23:45")
        assert not arrays.contiguous("EUR_USD", friday_close, friday_close + 1)
        #: ...and the reopen's own short session ends in a gap too.
        assert not arrays.contiguous("EUR_USD", 99, 100)


class TestCalendarHorizons:
    def test_a_one_day_horizon_holds_one_day_and_does_not_overlap(self) -> None:
        """It held two, and consecutive events shared one of them."""
        arrays = frontier.PanelArrays({"EUR_USD": _week()})
        spans: list[tuple[pd.Timestamp, pd.Timestamp]] = []
        for day in arrays.days:
            entry = arrays.bar_at_or_after("EUR_USD", pd.Timestamp(day, tz="UTC"))
            exit_ = arrays.last_bar_ending_by(
                "EUR_USD", pd.Timestamp(day, tz="UTC") + pd.Timedelta(days=1)
            )
            if entry is None or exit_ is None or exit_ < entry:
                continue
            spans.append(
                (
                    pd.Timestamp(arrays.ts["EUR_USD"][entry]),
                    pd.Timestamp(arrays.ts["EUR_USD"][exit_]),
                )
            )
        assert len(spans) >= 5
        for (_, first_exit), (second_entry, _later) in zip(spans, spans[1:], strict=False):
            assert second_entry > first_exit
        for entry, exit_ in spans:
            assert exit_ - entry < pd.Timedelta(days=1)


class TestNullAndEstimator:
    def test_the_closed_form_null_matches_a_simulation(self) -> None:
        """`sqrt(sum g^2)/n` is the sign-flip null's standard deviation, exactly."""
        rng = np.random.default_rng(5)
        gross = rng.normal(0.0, 7.0, size=300)
        simulated = (rng.choice((-1.0, 1.0), size=(40000, 300)) * gross).mean(axis=1)
        closed = frontier.mde_from_gross(gross, adjust_for_autocorrelation=False)
        assert closed == pytest.approx(POWER_MULTIPLIER * float(np.std(simulated)), rel=0.02)

    def test_positive_serial_dependence_raises_the_requirement(self) -> None:
        rng = np.random.default_rng(6)
        noise = rng.normal(0.0, 1.0, size=500)
        persistent = np.zeros(500)
        for i in range(1, 500):
            persistent[i] = 0.6 * persistent[i - 1] + noise[i]
        plain = frontier.mde_from_gross(persistent, adjust_for_autocorrelation=False)
        adjusted = frontier.mde_from_gross(persistent, adjust_for_autocorrelation=True)
        assert adjusted > plain * 1.5

    def test_negative_serial_dependence_is_not_used_to_lower_it(self) -> None:
        """An anti-persistent series must not be credited with extra power."""
        alternating = np.array([(-1.0) ** i for i in range(400)]) * 3.0
        plain = frontier.mde_from_gross(alternating, adjust_for_autocorrelation=False)
        adjusted = frontier.mde_from_gross(alternating, adjust_for_autocorrelation=True)
        assert adjusted == pytest.approx(plain)

    def test_the_matrix_map_matches_pair_weights(self) -> None:
        """`SIGNAL_TO_PAIR` and `currency.pair_weights` must not drift apart."""
        rng = np.random.default_rng(8)
        checked = 0
        for _ in range(300):
            raw = rng.choice((-1.0, 1.0), size=len(CURRENCIES))
            centred = raw - raw.mean()
            gross = np.abs(centred).sum()
            if gross == 0:
                continue
            vector = 2.0 * centred / gross
            checked += 1
            from_matrix = frontier.SIGNAL_TO_PAIR @ vector
            from_function = currency.pair_weights(dict(zip(CURRENCIES, vector, strict=True)))
            for index, pair in enumerate(PAIRS):
                assert from_matrix[index] == pytest.approx(from_function.get(pair, 0.0), abs=1e-12)
        assert checked > 250


class TestGate:
    def test_a_fatter_cost_tail_cannot_buy_decidability(self) -> None:
        """The hurdle is twice the **median** round trip, which a tail cannot move.

        With a mean-based hurdle, adding expensive outliers made a design read as
        more decidable — the gate rewarded the defect that produced them.
        """
        cheap = np.full(100, 2.0)
        with_tail = cheap.copy()
        with_tail[:10] = 40.0
        assert float(np.mean(with_tail)) > 2.0 * float(np.mean(cheap))
        assert float(np.median(with_tail)) == pytest.approx(float(np.median(cheap)))

    def test_break_even_uses_the_mean_because_a_strategy_pays_the_mean(self) -> None:
        record = frontier.economics(
            dispersion_bp=10.0, median_cost_bp=2.0, mean_cost_bp=4.0, n_events=100, years=2.0
        )
        assert record["break_even_gross_ir"] == pytest.approx(4.0 / 10.0 * np.sqrt(50.0), abs=0.005)
        #: ...and the powered floor uses the median, which is the gate's cost.
        assert record["dispersion_over_median_cost"] == pytest.approx(5.0)

    def test_the_feasible_band_is_quadratic_in_one_over_cost(self) -> None:
        """Halving execution cost widens the band fourfold. The headline of §3.4."""
        base = frontier.economics(10.0, 2.0, 4.0, 100, 2.0)
        halved = frontier.economics(10.0, 1.0, 2.0, 100, 2.0)
        assert halved["feasible_events_per_year_ceiling"]["1.5"] == pytest.approx(
            4.0 * base["feasible_events_per_year_ceiling"]["1.5"], rel=1e-3
        )
        assert halved["feasible_events_per_year_floor"] == pytest.approx(
            4.0 * base["feasible_events_per_year_floor"], rel=1e-3
        )

    def test_the_economics_subtree_declares_only_genuine_counts(self) -> None:
        """The marker covers the ceiling dict alone, not its monetary siblings."""
        record = frontier.economics(10.0, 2.0, 4.0, 100, 2.0)
        assert record["feasible_events_per_year_ceiling"]["_unit"] == "count"
        assert "_unit" not in record
        assert verify_unit_consistency({"cell": record})["status"] == "UNIT_CONSISTENCY_VERIFIED"
        #: A monetary field smuggled alongside is still caught.
        polluted = dict(record, leftover_pips=3.0)
        assert verify_unit_consistency({"cell": polluted})["numeric_fields_not_in_bp"] == [
            "root.cell.leftover_pips"
        ]


def _gappy() -> pd.DataFrame:
    """Five trading days, each broken in a way a contiguous frame cannot be.

    Mutation testing showed the first version of this file killed sixteen of
    twenty-two re-introduced defects and **survived exactly the two blockers and
    two of the required fixes** — because every assertion was on a helper and
    nothing exercised `clock_designs` or `calendar_designs` end to end. A
    fixture whose days are all whole cannot tell a filter that fires from a
    filter that does not.

    So each day here is shaped to trip one filter and nothing else:

    * **Mon 09** — a whole session. The control.
    * **Tue 10** — bars only to 11:45. Still a trading day at 48 bars, but the
      16:00 London fix has no bar within an hour of it, while the four bars
      ending 12:00 are perfectly contiguous. Only a proximity test sees this.
    * **Wed 11** — bars to 09:45, then a gap, then 15:00 onward. The fix window
      opens on the first bar after that gap, which is the weekly-reopen shape.
    * **Thu 12**, **Fri 13** — whole sessions.

    January, so London is on GMT and the fix is 16:00 UTC.
    """
    sessions = [
        ("2023-01-09 00:00", 96),
        ("2023-01-10 00:00", 48),
        ("2023-01-11 00:00", 40),
        ("2023-01-11 15:00", 36),
        ("2023-01-12 00:00", 96),
        ("2023-01-13 00:00", 96),
    ]
    index = pd.DatetimeIndex(
        [
            stamp
            for start, periods in sessions
            for stamp in pd.date_range(start, periods=periods, freq="15min", tz="UTC")
        ]
    )
    frame = pd.DataFrame({"ts": index})
    n = len(frame)
    frame["mid_o"] = np.linspace(1.10, 1.10 + 0.0001 * n, n)
    frame["mid_c"] = frame["mid_o"] + 0.00005
    frame["spread_close_pips"] = 1.0
    frame["pip_size"] = 0.0001
    return frame


class TestClockDesignsEndToEnd:
    @pytest.fixture
    def cells(self) -> dict[str, dict]:
        arrays = frontier.PanelArrays(dict.fromkeys(PAIRS, _gappy()))
        assert len(arrays.days) == 5
        return frontier.clock_designs(arrays)

    def test_a_day_with_no_bar_at_the_moment_is_excluded(self, cells: dict[str, dict]) -> None:
        """Tuesday's session ends at 11:45; its "16:00 fix" window is four hours early.

        Three days survive: Monday, Thursday and Friday. Wednesday is lost to the
        reopen filter and Tuesday to this one. A version without the proximity
        test counts five.
        """
        assert cells["london_fix_pre"]["n_events"] == 3

    def test_the_excluded_windows_are_counted(self, cells: dict[str, dict]) -> None:
        #: Twenty pairs on Tuesday, each too far from the moment.
        assert cells["london_fix_pre"]["pair_windows_dropped_as_far_from_the_moment"] == 20

    def test_a_window_opening_on_the_first_bar_after_a_gap_is_excluded(
        self, cells: dict[str, dict]
    ) -> None:
        """Wednesday's 15:00 bar is the first after a five-hour gap.

        It is exactly at the moment, so proximity passes it; only the
        `entry - 1` contiguity test refuses it. If both filters were removed the
        cell would hold five events, and if only this one were, four.
        """
        arrays = frontier.PanelArrays(dict.fromkeys(PAIRS, _gappy()))
        entry = arrays.bar_at_or_after("EUR_USD", pd.Timestamp("2023-01-11 15:00", tz="UTC"))
        assert pd.Timestamp(arrays.ts["EUR_USD"][entry]) == pd.Timestamp("2023-01-11 15:00")
        assert arrays.contiguous("EUR_USD", entry, entry + 3)
        assert not arrays.contiguous("EUR_USD", entry - 1, entry + 3)
        assert cells["london_fix_pre"]["n_events"] == 3

    def test_a_whole_day_is_still_measured(self, cells: dict[str, dict]) -> None:
        """The filters must not simply reject everything."""
        assert cells["london_fix_pre"]["n_events"] > 0
        assert cells["london_fix_post"]["n_events"] > 0


class TestCalendarDesignsEndToEnd:
    @pytest.fixture
    def cells(self) -> dict[str, dict]:
        arrays = frontier.PanelArrays(dict.fromkeys(PAIRS, _gappy()))
        return frontier.calendar_designs(arrays)

    def test_a_one_day_cell_holds_one_day(self, cells: dict[str, dict]) -> None:
        """The label was once a lie: it held two days and overlapped its neighbour.

        The median hold is now reported in the artifact so the claim is checkable
        rather than assumed.
        """
        assert cells["1d"]["hold_hours_median"] is not None
        assert cells["1d"]["hold_hours_median"] < 24.0

    def test_a_day_opening_after_a_gap_is_not_entered(self, cells: dict[str, dict]) -> None:
        """Wednesday opens at 00:00 but its predecessor bar is Tuesday 11:45.

        Monday is dropped too, having no predecessor at all — the first day of a
        panel is never an entry, which costs one event in five hundred and is
        the price of never entering on a reopen.
        """
        assert cells["1d"]["n_events"] == 3


class TestHurdleUsesTheMedian:
    def test_a_cost_tail_does_not_raise_the_hurdle(self) -> None:
        """Directly: the gate must read the median cost, not the mean.

        With a mean-based hurdle a design got *more* decidable the more its cost
        distribution skewed — the gate rewarded the very defect that skewed it.
        """
        frames = {}
        for index, pair in enumerate(PAIRS):
            frame = _gappy()
            #: One pair with a violently skewed spread. The median across the
            #: book barely moves; the mean does.
            if index == 0:
                frame.loc[frame.index[::7], "spread_close_pips"] = 400.0
            frames[pair] = frame
        arrays = frontier.PanelArrays(frames)
        cells = frontier.clock_designs(arrays)
        cell = cells["london_fix_pre"]
        assert cell["mean_roundtrip_cost_bp"] > cell["median_roundtrip_cost_bp"]
        assert cell["hurdle_bp"] == pytest.approx(2.0 * cell["median_roundtrip_cost_bp"], abs=0.02)
        assert cell["hurdle_bp"] != pytest.approx(2.0 * cell["mean_roundtrip_cost_bp"], abs=0.02)
