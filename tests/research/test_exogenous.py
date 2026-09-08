"""Exogenous Directional Information — timing, provenance and the frozen signs.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Everything in this package turns on *when* a number became knowable. A policy
decision has an announcement date; a CPI print has a release timestamp with a
daylight rule; a COT report is as of Tuesday and published later in the week. A
single one of those read early would manufacture an edge, so each is asserted
against behaviour rather than against a comment.

Nothing here reaches the network. The parsers are exercised on constructed
payloads shaped exactly like the real ones, including the two shapes that
actually broke: the FOMC page carrying a non-decision statement at the same URL
shape, and the nowcast axis interleaving marker labels between business days.
"""

from __future__ import annotations

import datetime as dt
import json

import numpy as np
import pandas as pd
import pytest

from scripts.research.exogenous import (
    BLS_RELEASE_TIMEZONE,
    BREADTH_SHARE,
    COT_CELLS,
    COT_HORIZON_DAYS,
    COT_PUBLICATION_SAFETY_DAYS,
    COT_SIGNALS,
    COT_SIGNS,
    MACRO_CELLS,
    MACRO_DIRECTION_SIGN,
    MACRO_HORIZON_BARS,
    MIN_BARS_FOR_A_TRADING_DAY,
    MIN_EVENTS_PER_DECIDING_PANEL,
    SCHEDULED_BANKS,
    SCHEDULED_EVENT_CELLS,
    SURPRISE_SCALE_RELEASES,
    TOTAL_CELLS,
    UNCOVERED_CURRENCIES,
    calendars,
    cot,
    events,
    macro,
    surprise,
)

# ----------------------------------------------------------------- fixtures


def _price_frame(
    *,
    start: str = "2023-01-02T00:00:00Z",
    days: int = 120,
    pip: float = 0.0001,
    spread: float = 1.4,
) -> pd.DataFrame:
    """M15 bars on weekdays only, which is what the real panels look like."""
    stamps: list[pd.Timestamp] = []
    day = pd.Timestamp(start)
    while len({s.date() for s in stamps}) < days:
        if day.weekday() < 5:
            stamps.extend(day + pd.Timedelta(minutes=15 * step) for step in range(96))
        day = day + pd.Timedelta(days=1)
    index = pd.DatetimeIndex(stamps)
    rng = np.random.default_rng(11)
    walk = np.cumsum(rng.normal(0.0, 0.0004, size=len(index))) + 1.2
    frame = pd.DataFrame(
        {
            "ts": index,
            "mid_o": walk,
            "mid_h": walk + 0.0006,
            "mid_l": walk - 0.0006,
            "mid_c": walk,
            "spread_close_pips": spread,
            "pip_size": pip,
            "volume": 100.0,
        }
    )
    frame["roundtrip_cost"] = frame["spread_close_pips"] + 0.5
    return frame


@pytest.fixture
def price_frame() -> pd.DataFrame:
    return _price_frame()


# ------------------------------------------------- the frozen contract itself


def test_the_search_is_the_twenty_cells_the_plan_declared() -> None:
    assert (SCHEDULED_EVENT_CELLS, MACRO_CELLS, COT_CELLS) == (6, 6, 8)
    assert TOTAL_CELLS == 20
    assert len(MACRO_HORIZON_BARS) == 3
    assert len(COT_SIGNALS) * len(COT_HORIZON_DAYS) == COT_CELLS


def test_the_covered_and_uncovered_currencies_do_not_overlap() -> None:
    assert set(SCHEDULED_BANKS) == {"USD", "EUR", "JPY", "AUD"}
    assert not set(SCHEDULED_BANKS) & set(UNCOVERED_CURRENCIES)
    assert set(SCHEDULED_BANKS) | set(UNCOVERED_CURRENCIES) == {
        "AUD",
        "CAD",
        "CHF",
        "EUR",
        "GBP",
        "JPY",
        "NZD",
        "USD",
    }


def test_the_cot_signs_are_one_committed_claim_per_signal() -> None:
    assert set(COT_SIGNS) == set(COT_SIGNALS)
    assert all(value in (-1, 1) for value in COT_SIGNS.values())
    #: three contrarian positioning signals and one momentum flow signal
    assert sorted(COT_SIGNS.values()) == [-1, -1, -1, 1]
    assert COT_SIGNS["net_change"] == 1


# ------------------------------------------------------------ Stage 1: dates


def test_the_fomc_parser_excludes_a_statement_that_is_not_a_decision() -> None:
    """The longer-run-goals notation vote shares the URL shape and is not a meeting."""
    page = (
        '<div class="fomc-meeting"><div class="fomc-meeting__date">16-17*</div>'
        "<strong>Statement:</strong><br>"
        '<a href="/newsevents/pressreleases/monetary20250917a.htm">HTML</a></div>'
        '<div class="fomc-meeting"><div class="fomc-meeting__date">22 (notation vote)</div>'
        '<a href="/newsevents/pressreleases/monetary20250822a.htm">'
        "Statement on Longer-Run Goals and Monetary Policy Strategy</a></div>"
    )
    found = sorted(
        calendars._iso(int(y), int(m), int(d))
        for y, m, d in calendars._FOMC_STATEMENT.findall(page)
    )
    assert found == ["2025-09-17"]


def test_the_rba_parser_takes_decisions_and_not_the_payments_board() -> None:
    page = (
        '<article><span itemprop="headline">Payments System Board Update: '
        "February 2023 Meeting</span>"
        '<time datetime="2023-02-16">16 February 2023</time></article>'
        '<article><span itemprop="headline">Statement by Philip Lowe, Governor: '
        "Monetary Policy Decision</span>"
        '<time datetime="2023-02-07">7 February 2023</time></article>'
    )
    found = sorted(
        match.group("date")
        for match in calendars._RBA_ARTICLE.finditer(page)
        if calendars._RBA_TITLE.search(match.group("title"))
    )
    assert found == ["2023-02-07"]


def test_a_pair_with_no_covered_leg_gets_no_events() -> None:
    calendar = {"USD": ["2023-02-01"], "EUR": ["2023-02-02"]}
    assert calendars.event_dates_for_pair("GBP_CHF", calendar) == set()
    assert calendars.event_dates_for_pair("EUR_USD", calendar) == {"2023-02-01", "2023-02-02"}
    #: either leg, not only the base
    assert calendars.event_dates_for_pair("GBP_USD", calendar) == {"2023-02-01"}


def test_the_expected_cadence_records_the_rba_schedule_change() -> None:
    """Eleven meetings a year through 2023 and eight from 2024 is the RBA's own change."""
    aud = calendars.EXPECTED_MEETINGS["AUD"]
    assert aud[2023] == 11
    assert aud[2024] == 8
    assert set(calendars.EXPECTED_MEETINGS["USD"].values()) == {8}


# ------------------------------------------------ Stage A: matched comparison


def test_a_short_session_is_not_a_trading_day(price_frame: pd.DataFrame) -> None:
    """The Sunday session flipped a headline last package; it is dropped here.

    The 47 is written out rather than derived from
    `MIN_BARS_FOR_A_TRADING_DAY`: a fixture built from the constant under test
    moves with it, and a mutant that set the threshold to zero also emptied the
    fixture and survived.
    """
    assert MIN_BARS_FOR_A_TRADING_DAY == 48
    day = pd.Timestamp("2023-03-06T00:00:00Z")
    trimmed = price_frame[
        (price_frame["ts"].dt.floor("D") != day)
        | (price_frame["ts"] < day + pd.Timedelta(minutes=15 * 47))
    ]
    assert int((trimmed["ts"].dt.floor("D") == day).sum()) == 47
    table = events.daily_table(trimmed)
    assert day not in table.index
    #: and a full session on the same day is kept, so the filter is the reason
    assert day in events.daily_table(price_frame).index


def test_the_volatility_tercile_never_reads_the_day_it_labels(
    price_frame: pd.DataFrame,
) -> None:
    """A spike on one day must not raise that day's own trailing label."""
    table = events.daily_table(price_frame)
    spiked = price_frame.copy()
    days = sorted({ts.date() for ts in price_frame["ts"]})
    target = days[80]
    mask = spiked["ts"].dt.date == target
    #: a violent spike, so a trailing mean that included it could not fail to move
    noise = np.arange(int(mask.sum())) % 2 * 0.5
    spiked.loc[mask, "mid_c"] = spiked.loc[mask, "mid_c"] + noise
    after = events.daily_table(spiked)
    stamp = pd.Timestamp(target, tz="UTC")
    assert float(after.loc[stamp, "realised"]) > 50.0 * float(table.loc[stamp, "realised"])

    #: the stratifying quantity on the spiked day is unchanged -- it reads only
    #: earlier days. The tercile itself is asserted through this rather than
    #: directly, because the tercile boundaries are cut on the panel's whole
    #: distribution and a later spike moves other days' ranks by construction.
    assert float(after.loc[stamp, "trailing_vol"]) == pytest.approx(
        float(table.loc[stamp, "trailing_vol"])
    )
    #: ... and the very next day's does move, so the window is not simply frozen
    following = pd.Timestamp(days[81], tz="UTC")
    assert float(after.loc[following, "trailing_vol"]) > 2.0 * float(
        table.loc[following, "trailing_vol"]
    )


def test_the_matched_ratio_is_computed_inside_the_cells(price_frame: pd.DataFrame) -> None:
    """A ratio that ignored the cells would answer a different question."""
    table = events.daily_table(price_frame).copy()
    #: a flat quantity, then one weekday inflated for event and control alike
    table["abs_move"] = 1.0
    monday = table.index.dayofweek == 0
    table.loc[monday, "abs_move"] = 4.0
    event = pd.Series(monday & (np.arange(len(table)) % 2 == 0), index=table.index)
    matched = events.matched_ratio(table, event, "abs_move")
    pooled = events.pooled_ratio(table, event, "abs_move")
    assert matched is not None and pooled is not None
    #: matched sees no difference, because event and control share the weekday
    assert matched == pytest.approx(1.0)
    #: pooled compares an all-Monday event group against a mostly-other control
    assert pooled > 2.0


def test_the_null_preserves_the_weekday_and_regime_mix(price_frame: pd.DataFrame) -> None:
    table = events.daily_table(price_frame)
    event = pd.Series(np.arange(len(table)) % 7 == 0, index=table.index)
    rng = np.random.default_rng(3)
    drawn = events._permute(table, event, rng)
    assert int(drawn.sum()) == int(event.sum())
    for key, block in table.groupby(["dayofweek", "vol_tercile"]):
        del key
        assert int(event.reindex(block.index).fillna(False).sum()) == int(
            drawn.reindex(block.index).fillna(False).sum()
        )


def test_the_event_mask_compares_dates_not_naive_timestamps(
    price_frame: pd.DataFrame,
) -> None:
    """The panel index is tz-aware; a naive timestamp set matches nothing."""
    table = events.daily_table(price_frame)
    day = table.index[10].date().isoformat()
    mask = events._event_mask(table, {day})
    assert int(mask.sum()) == 1


def test_the_event_verdict_fails_closed_on_a_missing_panel() -> None:
    good = {
        "pooled": {
            "abs_move": {"matched_ratio": 1.5, "pooled_ratio": 1.5, "pairs_matched_above_one": 19},
            "spread": {"matched_ratio": 1.01, "pooled_ratio": 1.01, "pairs_matched_above_one": 10},
            "exceeds_cost": {
                "matched_ratio": 1.0,
                "pooled_ratio": 1.0,
                "pairs_matched_above_one": 10,
            },
        },
        "pairs": 19,
        "abs_move_permutation_p": 0.005,
        #: the verdict reads the FAMILY-corrected value, not the raw one --
        #: plan §12 declares six cells and a Westfall-Young maximum over them
        "family_max_p": {"abs_move": 0.005},
    }
    both = events.verdict({"a": good, "b": good}, ("a", "b"))
    assert both["status"] == "FORWARD_KNOWN_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED"
    #: one panel missing must not pass on an empty `all()`
    one = events.verdict({"a": good}, ("a", "b"))
    assert one["status"] == "SCHEDULED_EVENT_OPPORTUNITY_STRUCTURE_NOT_SUPPORTED"
    assert one["complete"] is False


def test_the_event_verdict_reads_the_family_corrected_p() -> None:
    """An uncorrected `p` at the floor must not pass the declared six-cell family."""
    row = {
        "pooled": {
            "abs_move": {"matched_ratio": 1.5, "pooled_ratio": 1.5, "pairs_matched_above_one": 19},
            "spread": {"matched_ratio": 1.01, "pooled_ratio": 1.01, "pairs_matched_above_one": 10},
            "exceeds_cost": {
                "matched_ratio": 1.0,
                "pooled_ratio": 1.0,
                "pairs_matched_above_one": 10,
            },
        },
        "pairs": 19,
        "abs_move_permutation_p": 0.005,
        "family_max_p": {"abs_move": 0.30},
    }
    decision = events.verdict({"a": row, "b": row}, ("a", "b"))
    assert decision["status"] == "SCHEDULED_EVENT_OPPORTUNITY_STRUCTURE_NOT_SUPPORTED"
    #: and a missing correction fails closed rather than falling back to the raw p
    bare = {key: value for key, value in row.items() if key != "family_max_p"}
    assert (
        events.verdict({"a": bare, "b": bare}, ("a", "b"))["status"]
        == "SCHEDULED_EVENT_OPPORTUNITY_STRUCTURE_NOT_SUPPORTED"
    )


def test_the_event_verdict_needs_the_declared_breadth() -> None:
    assert BREADTH_SHARE == 0.60
    thin = {
        "pooled": {
            "abs_move": {
                "matched_ratio": 1.5,
                "pooled_ratio": 1.5,
                #: written out, not derived from BREADTH_SHARE: a fixture built
                #: from the constant under test moves with it, and a mutant that
                #: set the share to zero also moved the fixture and survived
                "pairs_matched_above_one": 10,
            },
            "spread": {"matched_ratio": 1.01, "pooled_ratio": 1.01, "pairs_matched_above_one": 1},
            "exceeds_cost": {
                "matched_ratio": 1.0,
                "pooled_ratio": 1.0,
                "pairs_matched_above_one": 1,
            },
        },
        "pairs": 19,
        "abs_move_permutation_p": 0.005,
        "family_max_p": {"abs_move": 0.005},
    }
    assert (
        events.verdict({"a": thin, "b": thin}, ("a", "b"))["status"]
        == "SCHEDULED_EVENT_OPPORTUNITY_STRUCTURE_NOT_SUPPORTED"
    )


# --------------------------------------------------- Stage B: real-time macro


def test_the_release_time_follows_the_real_daylight_rule() -> None:
    """08:30 New York is 12:30 UTC in summer and 13:30 in winter."""
    summer = macro.release_timestamp_utc("2023-06-13")
    winter = macro.release_timestamp_utc("2023-01-12")
    assert summer.hour == 12 and summer.minute == 30
    assert winter.hour == 13 and winter.minute == 30
    assert BLS_RELEASE_TIMEZONE == "America/New_York"


def test_the_nowcast_axis_markers_do_not_shift_the_release(monkeypatch) -> None:
    """Marker labels between business days moved every release two days early."""
    labels = ["06/01", "06/02", "CPI May", "06/05", "06/06", "CPI Jun", "06/07"]
    chart = {
        "chart": {"subcaption": "2023-6"},
        "categories": [{"category": [{"label": value} for value in labels]}],
        "dataset": [
            {"seriesname": "CPI Inflation", "data": [{"value": "0.1"}] * 3 + [{}] * 2},
            {
                "seriesname": "Actual CPI Inflation",
                "data": [{}, {}, {}, {"value": "0.2"}, {}],
            },
        ],
    }
    payload = json.dumps([chart]).encode()
    monkeypatch.setattr(macro, "_get", lambda url, **kwargs: (payload, {"sha256": "x"}))
    parsed, _ = macro.cleveland_nowcast()
    #: five date labels; index 3 is the fourth date, 06/06 -- not the fourth
    #: category, which the marker labels would have made 06/05
    assert parsed["2023-06"]["days"] == [
        "2023-06-01",
        "2023-06-02",
        "2023-06-05",
        "2023-06-06",
        "2023-06-07",
    ]
    assert parsed["2023-06"]["actual_dates"]["CPI Inflation"] == "2023-06-06"


def test_a_december_target_month_wraps_into_the_next_year() -> None:
    assert macro._label_to_date("01/12", 2023, 12) == dt.date(2024, 1, 12)
    assert macro._label_to_date("12/20", 2023, 12) == dt.date(2023, 12, 20)
    assert macro._label_to_date("PCE Jul", 2023, 6) is None


def test_the_surprise_scale_reads_only_earlier_releases() -> None:
    """A full-sample scale would put the future into every early event."""
    releases = [
        {"release_date": f"2023-{index + 1:02d}-10", "cpi": {"surprise_pct": value}}
        for index, value in enumerate([0.1, -0.1, 0.05, -0.05, 0.2, 3.0, 0.1])
    ]
    scaled = macro.scale_surprises(releases, "cpi")
    early = [row for row in scaled if row["surprise_scale"] is not None][0]
    #: the huge sixth surprise cannot affect a scale computed before it
    before = macro.scale_surprises(releases[:5], "cpi")
    matching = [row for row in before if row["release_date"] == early["release_date"]][0]
    assert early["surprise_scale"] == pytest.approx(matching["surprise_scale"])
    assert all(row["prior_surprises_used"] <= SURPRISE_SCALE_RELEASES for row in scaled)
    assert scaled[0]["surprise_z"] is None


def test_the_first_release_uses_the_vintage_that_introduced_the_month(monkeypatch) -> None:
    """A later revision must never become the number that printed."""
    #: December is REVISED in the vintage that first carries January. A fixture
    #: where it is unchanged cannot tell "the value known before the release"
    #: from "the value in the release vintage", and a mutant that read the
    #: wrong one survived against exactly that fixture.
    vintages = {
        "2023-01-10": {"2022-11-01": 100.0, "2022-12-01": 101.0},
        "2023-02-10": {"2022-11-01": 100.0, "2022-12-01": 101.5, "2023-01-01": 102.0},
        "2023-03-10": {"2022-11-01": 100.0, "2022-12-01": 101.5, "2023-01-01": 999.0},
    }
    monkeypatch.setattr(
        macro, "alfred_vintages", lambda series: (sorted(vintages), {"series": series})
    )
    monkeypatch.setattr(macro, "alfred_vintage", lambda series, vintage: vintages[vintage])
    rows, _ = macro.first_release_table(
        "X", first_release_from="2023-02-01", first_release_to="2023-03-31"
    )
    january = [row for row in rows if row["observation_month"] == "2023-01-01"][0]
    assert january["release_vintage"] == "2023-02-10"
    assert january["first_release_level"] == 102.0
    assert january["prior_known_level"] == 101.0
    assert january["first_release_mom_pct"] == pytest.approx(100.0 * (102.0 / 101.0 - 1.0))


# ---------------------------------------------------- Stage C: the direction


def test_the_usd_side_is_the_right_way_round() -> None:
    assert surprise.usd_side("USD_JPY") == 1
    assert surprise.usd_side("EUR_USD") == -1
    with pytest.raises(ValueError, match="no USD leg"):
        surprise.usd_side("EUR_JPY")


def test_the_entry_bar_starts_strictly_after_the_release(price_frame: pd.DataFrame) -> None:
    times = price_frame["ts"].reset_index(drop=True)
    exact = times.iloc[400].to_pydatetime()
    entry = surprise._entry_index(times, exact)
    assert entry == 401
    assert times.iloc[entry] > pd.Timestamp(exact)


def test_an_event_with_no_bar_within_two_hours_is_dropped(
    price_frame: pd.DataFrame,
) -> None:
    """A holiday or a gap drops the event; it is not shifted to a later bar."""
    times = price_frame["ts"].reset_index(drop=True)
    #: the weekend gap, not a same-day one: the fixture has no Saturday bars
    fridays = [index for index, stamp in enumerate(times) if stamp.weekday() == 4]
    last_friday_bar = min(
        index
        for index in fridays
        if times.iloc[index].hour == 23 and times.iloc[index].minute == 45
    )
    saturday = times.iloc[last_friday_bar].to_pydatetime() + dt.timedelta(hours=12)
    assert times.iloc[last_friday_bar + 1].weekday() == 0
    assert surprise._entry_index(times, saturday) is None


def test_the_pre_registered_sign_is_the_one_that_is_traded(
    price_frame: pd.DataFrame,
) -> None:
    """A rising USD_JPY must pay on a positive surprise, and only then."""
    frame = price_frame.copy()
    frame["mid_c"] = np.linspace(150.0, 151.0, len(frame))
    frame["mid_o"] = frame["mid_c"]
    frame["pip_size"] = 0.01
    release = {
        "release_date": "2023-02-10",
        "release_timestamp_utc": frame["ts"].iloc[300].isoformat(),
        "surprise_z": 1.5,
        "indicator": "cpi",
    }
    rows = surprise.event_returns({"USD_JPY": frame}, [release], horizon="1h")
    assert rows and rows[0]["direction"] == MACRO_DIRECTION_SIGN
    assert rows[0]["gross_pips"] > 0
    flipped = surprise.event_returns(
        {"USD_JPY": frame}, [{**release, "surprise_z": -1.5}], horizon="1h"
    )
    assert flipped[0]["gross_pips"] < 0


def test_the_cost_comes_from_the_entry_bar_not_a_period_median(
    price_frame: pd.DataFrame,
) -> None:
    frame = price_frame.copy()
    frame.loc[300:400, "spread_close_pips"] = 9.0
    release = {
        "release_date": "2023-02-10",
        "release_timestamp_utc": frame["ts"].iloc[320].isoformat(),
        "surprise_z": 1.0,
        "indicator": "cpi",
    }
    rows = surprise.event_returns({"EUR_USD": frame}, [release], horizon="1h")
    assert rows[0]["cost_pips"] == pytest.approx(9.5)


def test_the_macro_verdict_cannot_pass_on_one_currency() -> None:
    """Its best attainable outcome is a negative one, by construction."""
    strong = {
        "events": MIN_EVENTS_PER_DECIDING_PANEL + 10,
        "gross_mean_pips": 20.0,
        "net_mean_pips": 15.0,
        "tail_share_of_gross": 0.2,
    }
    cells = {"a": {"cpi_1h": strong}, "b": {"cpi_1h": strong}}
    decision = surprise.verdict(cells, ("a", "b"), min_events=MIN_EVENTS_PER_DECIDING_PANEL)
    assert decision["status"] == (
        "MACRO_SURPRISE_SIGNAL_PRESENT_BUT_SINGLE_CURRENCY_INSUFFICIENT_BREADTH"
    )
    assert "SINGLE_CURRENCY_USD_ONLY" in decision["drop_reasons"]
    thin = {**strong, "events": MIN_EVENTS_PER_DECIDING_PANEL - 1}
    dropped = surprise.verdict(
        {"a": {"cpi_1h": thin}, "b": {"cpi_1h": thin}},
        ("a", "b"),
        min_events=MIN_EVENTS_PER_DECIDING_PANEL,
    )
    assert dropped["status"] == "MACRO_SURPRISE_DIRECTIONAL_EDGE_NOT_SUPPORTED"


def test_a_panel_sign_reversal_drops_the_macro_family() -> None:
    up = {
        "events": 40,
        "gross_mean_pips": 10.0,
        "net_mean_pips": 8.0,
        "tail_share_of_gross": 0.2,
    }
    down = {**up, "gross_mean_pips": -10.0, "net_mean_pips": -12.0}
    decision = surprise.verdict(
        {"a": {"cpi_1h": up}, "b": {"cpi_1h": down}},
        ("a", "b"),
        min_events=MIN_EVENTS_PER_DECIDING_PANEL,
    )
    assert "PANEL_SIGN_REVERSAL_cpi_1h" in decision["drop_reasons"]


# ------------------------------------------------------------- the COT branch


def test_the_cot_publication_waits_past_the_nominal_friday() -> None:
    """Tuesday as-of, Friday nominal release, and three more days of safety."""
    stamp = cot.publication_timestamp("2023-06-13")
    assert stamp.weekday() == 0
    assert (stamp.date() - dt.date(2023, 6, 16)).days == COT_PUBLICATION_SAFETY_DAYS
    assert (stamp.hour, stamp.minute) == (20, 30)
    nominal = cot.publication_timestamp("2023-06-13", safety_days=0)
    assert nominal.date() == dt.date(2023, 6, 16)


def test_a_monday_as_of_date_still_resolves_to_that_week_s_friday() -> None:
    """Holiday weeks move the as-of date; three of 369 are Mondays."""
    assert cot.publication_timestamp("2023-07-03", safety_days=0).date() == dt.date(2023, 7, 7)


def test_the_cot_entry_is_never_before_publication(price_frame: pd.DataFrame) -> None:
    moves = cot.week_moves({"EUR_USD": price_frame}, ["2023-02-07"], horizon="1w")
    assert moves["EUR_USD"]
    entry = pd.Timestamp(moves["EUR_USD"][0]["entry_utc"])
    assert entry > pd.Timestamp(cot.publication_timestamp("2023-02-07"))


def test_the_cot_horizon_is_calendar_time(price_frame: pd.DataFrame) -> None:
    """Amendment A-1: 7 * 96 bars is nine and a half calendar days, not a week."""
    for horizon, days in COT_HORIZON_DAYS.items():
        moves = cot.week_moves({"EUR_USD": price_frame}, ["2023-02-07"], horizon=horizon)
        held = moves["EUR_USD"][0]["held_days"]
        assert days <= held < days + 4


def test_the_usd_score_is_the_negative_mean_of_the_others() -> None:
    index = pd.Index([f"2023-01-{day:02d}" for day in range(1, 6)], name="report_date")
    levels = pd.DataFrame(
        {currency: np.linspace(0.1, 0.5, 5) for currency in cot.NON_USD}, index=index
    )
    scores = cot.currency_scores(levels)["net_level"]
    assert scores["USD"].iloc[0] == pytest.approx(-scores[list(cot.NON_USD)].iloc[0].mean())
    assert set(scores.columns) == set(cot.NON_USD) | {"USD"}


def test_the_percentile_window_is_backward_only() -> None:
    index = pd.Index(
        [(dt.date(2021, 1, 5) + dt.timedelta(weeks=w)).isoformat() for w in range(220)],
        name="report_date",
    )
    #: ten very high weeks at the start, then flat. A trailing 104-week window
    #: at week 200 has left them behind; an expanding window has not. A fixture
    #: without that early spike cannot tell the two apart, and a mutant that
    #: replaced the rolling window with an expanding one survived against it.
    values = np.concatenate([np.full(10, 99.0), np.zeros(210)])
    levels = pd.DataFrame({currency: values for currency in cot.NON_USD}, index=index)
    percentile = cot.currency_scores(levels)["net_percentile"]
    assert float(percentile["EUR"].iloc[200]) == pytest.approx(0.5, abs=1e-9)
    #: and the window really is 104 long: at week 100 the spike is still inside
    assert float(percentile["EUR"].iloc[100]) < 0.49


def test_the_contrarian_sign_shorts_a_crowded_currency() -> None:
    index = pd.Index(["2023-02-07"], name="report_date")
    scores = pd.DataFrame({"EUR": [0.9], "USD": [-0.9]}, index=index)
    moves = {
        "EUR_USD": [
            {
                "report_date": "2023-02-07",
                "move_pips": 10.0,
                "cost_pips": 1.9,
                "held_days": 7.0,
                "entry_utc": "x",
            }
        ]
    }
    contrarian = cot.evaluate(moves, scores, signal="net_level")
    assert contrarian[0]["position"] == -1.0
    momentum = cot.evaluate(moves, scores, signal="net_change")
    assert momentum[0]["position"] == 1.0


def test_the_family_max_correction_uses_the_shared_draws() -> None:
    cells = {
        "a": {"gross_t": 2.0, "null_statistics": [0.5, 1.0, 3.0]},
        "b": {"gross_t": 0.1, "null_statistics": [2.5, 0.2, 0.3]},
    }
    corrected = cot.family_max_p(cells)
    #: the per-draw maxima are 2.5, 1.0 and 3.0, so |t| = 2.0 is reached twice
    assert corrected["a"] == pytest.approx(3 / 4)
    assert corrected["b"] == pytest.approx(4 / 4)


def test_the_cot_verdict_drops_a_cell_the_family_null_cannot_separate() -> None:
    strong = {
        "events": 90,
        "gross_mean_pips": 24.0,
        "net_mean_pips": 20.0,
        "pairs": 20,
        "pairs_gross_positive": 14,
        "tail_share_of_gross": 0.1,
    }
    panels = {"a": {"net_extreme_4w": strong}, "b": {"net_extreme_4w": strong}}
    dropped = cot.verdict(
        panels,
        ("a", "b"),
        min_events=MIN_EVENTS_PER_DECIDING_PANEL,
        corrected={"a": {"net_extreme_4w": 0.5}, "b": {"net_extreme_4w": 0.4}},
    )
    assert dropped["status"] == "COT_EDGE_NOT_SUPPORTED"
    assert dropped["dropped"]["net_extreme_4w"] == ["FAMILYWISE_NULL"]
    kept = cot.verdict(
        panels,
        ("a", "b"),
        min_events=MIN_EVENTS_PER_DECIDING_PANEL,
        corrected={"a": {"net_extreme_4w": 0.01}, "b": {"net_extreme_4w": 0.02}},
    )
    assert kept["status"] == "COT_EDGE_SUPPORTED_EXPLORATORY"


def test_the_cot_verdict_fails_closed_without_a_correction() -> None:
    strong = {
        "events": 90,
        "gross_mean_pips": 24.0,
        "net_mean_pips": 20.0,
        "pairs": 20,
        "pairs_gross_positive": 14,
        "tail_share_of_gross": 0.1,
    }
    decision = cot.verdict(
        {"a": {"net_extreme_4w": strong}, "b": {"net_extreme_4w": strong}},
        ("a", "b"),
        min_events=MIN_EVENTS_PER_DECIDING_PANEL,
        corrected={},
    )
    assert decision["status"] == "COT_EDGE_NOT_SUPPORTED"
    assert "FAMILYWISE_NULL" in decision["dropped"]["net_extreme_4w"]
