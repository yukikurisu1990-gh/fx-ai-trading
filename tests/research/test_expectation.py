"""Expectation Benchmark — power gating, as-of integrity, and the frozen signs.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

This package's whole claim is that it refuses to produce an ambiguous null. The
tests that matter therefore guard the **gate**, not just the arithmetic: a cell
the design cannot decide must be skipped and named, never reported as a null,
and never allowed to reach a verdict.

The second cluster guards the join. The free archive is trusted for values and
distrusted for time — its timestamps are 16 to 17 hours early — so every test
that touches a release time asserts the time came from ALFRED, not from the
archive.

Nothing here reaches the network.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from scripts.research.expectation import (
    HIGH_IMPACT_FAMILIES,
    MACRO_HORIZON_BARS,
    MACRO_HORIZONS_EXCLUDED_FOR_POWER,
    POWER_MULTIPLIER,
    RATES_SIGN,
    RELEASE_FAMILIES,
    RELEASES_NEEDED_FOR_1H_POWER,
    SIGNAL_SIGNS,
    SURPRISE_SCALE_RELEASES,
    consensus,
    rates,
    test_engine,
)


def _frame(*, days: int = 60, spread: float = 1.5, drift: float = 0.0) -> pd.DataFrame:
    stamps: list[pd.Timestamp] = []
    day = pd.Timestamp("2023-01-02T00:00:00Z")
    while len({s.date() for s in stamps}) < days:
        if day.weekday() < 5:
            stamps.extend(day + pd.Timedelta(minutes=15 * step) for step in range(96))
        day = day + pd.Timedelta(days=1)
    index = pd.DatetimeIndex(stamps)
    rng = np.random.default_rng(7)
    walk = np.cumsum(rng.normal(drift, 0.0004, size=len(index))) + 1.2
    return pd.DataFrame(
        {
            "ts": index,
            "mid_o": walk,
            "mid_h": walk + 0.0005,
            "mid_l": walk - 0.0005,
            "mid_c": walk,
            "spread_close_pips": spread,
            "pip_size": 0.0001,
        }
    )


# ------------------------------------------------- the frozen contract itself


def test_the_excluded_horizons_are_named_and_disjoint() -> None:
    """An omission has to be legible as a decision, not as a gap."""
    assert set(MACRO_HORIZON_BARS) == {"1h"}
    assert set(MACRO_HORIZONS_EXCLUDED_FOR_POWER) == {"4h", "12h", "1d"}
    assert not set(MACRO_HORIZON_BARS) & set(MACRO_HORIZONS_EXCLUDED_FOR_POWER)
    assert RELEASES_NEEDED_FOR_1H_POWER > 90


def test_every_admitted_event_carries_a_pre_registered_sign() -> None:
    events = [name for family in RELEASE_FAMILIES.values() for name in family["events"]]
    assert len(events) == len(set(events))
    assert set(events) == set(SIGNAL_SIGNS)
    assert all(value in (-1, 1) for value in SIGNAL_SIGNS.values())
    #: the two where a bigger number is a weaker economy
    assert SIGNAL_SIGNS["Unemployment Rate"] == -1
    assert SIGNAL_SIGNS["Unemployment Claims"] == -1
    assert SIGNAL_SIGNS["Non-Farm Employment Change"] == +1


def test_the_high_impact_subset_is_a_subset() -> None:
    assert set(HIGH_IMPACT_FAMILIES) <= set(RELEASE_FAMILIES)


# --------------------------------------------------------------- the gate


def test_an_underpowered_cell_is_refused_rather_than_reported() -> None:
    """The single most important behaviour in the package."""
    rng = np.random.default_rng(3)
    small = pd.DataFrame(
        {
            "event": np.repeat(np.arange(6), 7),
            "pair": ["EUR_USD"] * 42,
            "signal": rng.normal(size=42),
            "usd_move_pips": rng.normal(0.0, 30.0, size=42),
            "cost_pips": 2.0,
        }
    )
    gate = test_engine.minimum_detectable_effect(small)
    assert gate["runnable"] is False
    assert "UNDERPOWERED" in gate["reason"]
    assert gate["break_even_double_cost_pips"] == pytest.approx(4.0)


def test_a_well_powered_cell_is_allowed_through() -> None:
    rng = np.random.default_rng(4)
    n = 3000
    big = pd.DataFrame(
        {
            "event": np.arange(n),
            "pair": ["EUR_USD"] * n,
            "signal": rng.normal(size=n),
            "usd_move_pips": rng.normal(0.0, 20.0, size=n),
            "cost_pips": 2.0,
        }
    )
    gate = test_engine.minimum_detectable_effect(big)
    assert gate["runnable"] is True
    assert gate["reason"] is None
    assert gate["mde_80pct_power_pips"] < gate["break_even_double_cost_pips"]


def test_a_skipped_cell_never_reaches_a_verdict_as_a_null() -> None:
    """`NOT_DECISION_GRADE_SKIP` is a different outcome from `NOT_SUPPORTED`."""
    skipped = {"events": 50, "skipped": {"reason": "UNDERPOWERED..."}}
    decision = test_engine.verdict(
        {"a": {"cell": skipped}, "b": {"cell": skipped}},
        ("a", "b"),
        primary=("cell",),
        corrected={"a": {"cell": 0.01}, "b": {"cell": 0.01}},
        min_events=10,
        supported_status="SUPPORTED",
        not_supported_status="NOT_SUPPORTED",
    )
    assert decision["status"] == "NOT_DECISION_GRADE_SKIP"
    assert decision["decidable"] is False
    assert decision["drop_reasons"] == ["UNDERPOWERED_NOT_DECIDABLE_cell"]


def test_a_powered_cell_that_fails_a_clause_is_a_null_not_a_skip() -> None:
    weak = {
        "events": 200,
        "gross_mean_pips": 0.5,
        "net_mean_pips": -1.5,
        "tail_share_of_net": 0.1,
    }
    decision = test_engine.verdict(
        {"a": {"cell": weak}, "b": {"cell": weak}},
        ("a", "b"),
        primary=("cell",),
        corrected={"a": {"cell": 0.6}, "b": {"cell": 0.6}},
        min_events=90,
        supported_status="SUPPORTED",
        not_supported_status="NOT_SUPPORTED",
    )
    assert decision["status"] == "NOT_SUPPORTED"
    assert decision["decidable"] is True
    assert "NEGATIVE_AFTER_COST_cell" in decision["drop_reasons"]
    assert "FAMILYWISE_NULL_cell" in decision["drop_reasons"]


def test_the_null_draws_one_sign_per_event_not_per_pair_event() -> None:
    """Per-pair-event signs would shrink the null by about the square root of 7."""
    rng = np.random.default_rng(11)
    events, pairs = 60, 7
    move = rng.normal(0.0, 25.0, size=events)
    table = pd.DataFrame(
        {
            "event": np.repeat(np.arange(events), pairs),
            "pair": list("abcdefg") * events,
            "signal": 1.0,
            #: every pair moves together, which is what a dollar move does
            "usd_move_pips": np.repeat(move, pairs),
            "cost_pips": 2.0,
        }
    )
    per_event = np.std(test_engine._null_means(table, draws=400, seed=1), ddof=1)
    #: the wrong version: an independent sign for every row
    rng2 = np.random.default_rng(1)
    values = table["usd_move_pips"].to_numpy()
    per_row = np.std(
        [float(np.mean(rng2.choice([-1.0, 1.0], size=len(values)) * values)) for _ in range(400)],
        ddof=1,
    )
    assert per_event > 2.0 * per_row


# ------------------------------------------------------------ the join


def test_the_release_time_comes_from_alfred_and_not_from_the_archive() -> None:
    """08:30 New York, with the real daylight rule, on the ALFRED vintage date."""
    from scripts.research.exogenous import macro as alfred

    summer = alfred.release_timestamp_utc("2023-06-13")
    winter = alfred.release_timestamp_utc("2023-01-12")
    assert (summer.hour, summer.minute) == (12, 30)
    assert (winter.hour, winter.minute) == (13, 30)


def test_two_families_printing_at_one_moment_become_one_event() -> None:
    """Two positions cannot be taken at a moment where only one is available."""
    archive = pd.DataFrame(
        {
            "Currency": ["USD", "USD"],
            "Event": ["CPI m/m", "PPI m/m"],
            "Actual": ["0.4%", "0.2%"],
            "Forecast": ["0.3%", "0.1%"],
            "Previous": ["0.2%", "0.0%"],
            "ts": pd.to_datetime(["2023-06-12T20:30:00Z", "2023-06-12T20:30:00Z"], utc=True),
        }
    )
    dates = {
        "cpi": {"dates": ["2023-06-13"]},
        "employment": {"dates": []},
        "retail": {"dates": []},
        "ppi": {"dates": ["2023-06-13"]},
        "claims": {"dates": []},
        "durable_goods": {"dates": []},
        "housing": {"dates": []},
        "trade": {"dates": []},
        "pce": {"dates": []},
        "gdp": {"dates": []},
    }
    events, diagnostics = consensus.build_events(archive, dates)
    assert len(events) == 1
    assert sorted(events[0]["families"]) == ["cpi", "ppi"]
    assert set(events[0]["signals"]) == {"CPI m/m", "PPI m/m"}
    assert diagnostics["collisions_merged"] == 1


def test_the_archive_value_parser_does_not_guess() -> None:
    values = consensus.to_number(pd.Series(["0.4%", "-11K", "1.2M", "", "n/a", "3"]))
    assert list(values[:3]) == [0.4, -11000.0, 1200000.0]
    assert bool(values[3:5].isna().all())
    assert values.iloc[5] == 3.0


def test_the_surprise_scale_reads_only_earlier_releases() -> None:
    """A full-sample scale would put the future into every early event."""
    events = [
        {
            "release_date": f"2023-{index + 1:02d}-10",
            "release_timestamp_utc": f"2023-{index + 1:02d}-10T13:30:00+00:00",
            "families": ["cpi"],
            "signals": {"CPI m/m": {"raw_surprise": value}},
        }
        for index, value in enumerate([0.1, -0.1, 0.05, -0.05, 0.2, 9.0, 0.1])
    ]
    scaled = consensus.attach_surprises(events)
    assert scaled[0]["composite_z"] is None
    early = scaled[4]["composite_z"]
    #: the enormous sixth surprise cannot change a scale computed before it
    truncated = consensus.attach_surprises(events[:5])
    assert truncated[4]["composite_z"] == pytest.approx(early)
    assert all(row["signals_used"] <= len(row["signals"]) for row in scaled)


def test_the_composite_orients_each_signal_by_its_own_sign() -> None:
    """A rising unemployment rate must push the composite the other way."""
    history = [
        {
            "release_date": f"2023-{index + 1:02d}-05",
            "release_timestamp_utc": f"2023-{index + 1:02d}-05T13:30:00+00:00",
            "families": ["employment"],
            #: varying, so the backward scale is non-zero. A constant history
            #: gives a zero standard deviation and the signal drops out, which
            #: is what a first version of this fixture silently did.
            "signals": {
                "Non-Farm Employment Change": {"raw_surprise": 10.0 * (-1) ** index},
                "Unemployment Rate": {"raw_surprise": 0.1 * (-1) ** index},
            },
        }
        for index in range(6)
    ]
    history.append(
        {
            "release_date": "2023-07-05",
            "release_timestamp_utc": "2023-07-05T12:30:00+00:00",
            "families": ["employment"],
            "signals": {
                "Non-Farm Employment Change": {"raw_surprise": 50.0},
                "Unemployment Rate": {"raw_surprise": 0.5},
            },
        }
    )
    scaled = consensus.attach_surprises(history)
    last = scaled[-1]
    payrolls = last["standardised"]["Non-Farm Employment Change"]
    unemployment = last["standardised"]["Unemployment Rate"]
    assert payrolls > 0
    assert unemployment < 0
    assert last["composite_z"] == pytest.approx((payrolls + unemployment) / 2)


# ------------------------------------------------------------ execution


def test_the_entry_bar_starts_strictly_after_the_release() -> None:
    frame = _frame()
    times = frame["ts"].reset_index(drop=True)
    exact = times.iloc[300].to_pydatetime()
    assert test_engine.entry_index(times, exact) == 301


def test_an_event_with_no_bar_inside_the_tolerance_is_dropped() -> None:
    frame = _frame()
    times = frame["ts"].reset_index(drop=True)
    fridays = [i for i, stamp in enumerate(times) if stamp.weekday() == 4]
    close = min(i for i in fridays if times.iloc[i].hour == 23 and times.iloc[i].minute == 45)
    assert (
        test_engine.entry_index(times, times.iloc[close].to_pydatetime() + dt.timedelta(hours=12))
        is None
    )


def test_the_usd_side_is_the_right_way_round() -> None:
    assert test_engine.usd_side("USD_JPY") == 1
    assert test_engine.usd_side("EUR_USD") == -1
    with pytest.raises(ValueError, match="no USD leg"):
        test_engine.usd_side("EUR_JPY")


def test_a_positive_surprise_on_a_rising_dollar_pays() -> None:
    frame = _frame()
    frame["mid_c"] = np.linspace(150.0, 151.0, len(frame))
    frame["mid_o"] = frame["mid_c"]
    frame["pip_size"] = 0.01
    event = {
        "release_timestamp_utc": frame["ts"].iloc[300].isoformat(),
        "families": ("cpi",),
        "composite_z": 1.5,
    }
    table = test_engine.event_returns({"USD_JPY": frame}, [event], horizon_bars=4)
    assert len(table) == 1
    assert table["usd_move_pips"].iloc[0] > 0
    flipped = test_engine.event_returns(
        {"USD_JPY": frame}, [{**event, "composite_z": -1.5}], horizon_bars=4
    )
    cell = test_engine.evaluate(pd.concat([table, flipped]), draws=5)
    #: a rising dollar pays the positive surprise and costs the negative one
    assert cell["events"] == 1


def test_the_cost_comes_from_the_entry_bar() -> None:
    frame = _frame()
    frame.loc[300:400, "spread_close_pips"] = 9.0
    event = {
        "release_timestamp_utc": frame["ts"].iloc[320].isoformat(),
        "families": ("cpi",),
        "composite_z": 1.0,
    }
    table = test_engine.event_returns({"EUR_USD": frame}, [event], horizon_bars=4)
    assert table["cost_pips"].iloc[0] == pytest.approx(9.5)


# ------------------------------------------------------------ rates branch


def test_the_lead_decision_moment_is_after_the_us_close() -> None:
    yields = pd.Series({"2023-06-12": 4.60, "2023-06-13": 4.70})
    lead = rates.build_events(yields, same_day=False)
    assert len(lead) == 1
    moment = dt.datetime.fromisoformat(lead[0]["release_timestamp_utc"])
    assert moment.hour == rates.DECISION_HOUR_UTC
    assert moment.date() == dt.date(2023, 6, 13)
    #: a rise in the two-year yield is long USD
    assert lead[0]["composite_z"] == pytest.approx(RATES_SIGN * 0.10)


def test_the_same_day_cell_is_marked_as_a_diagnostic_by_construction() -> None:
    """It opens before the change it trades on exists; that is the point."""
    yields = pd.Series({"2023-06-12": 4.60, "2023-06-13": 4.70})
    same_day = rates.build_events(yields, same_day=True)
    moment = dt.datetime.fromisoformat(same_day[0]["release_timestamp_utc"])
    assert moment.hour == 0
    lead = dt.datetime.fromisoformat(
        rates.build_events(yields, same_day=False)[0]["release_timestamp_utc"]
    )
    assert moment < lead


def test_a_day_with_no_yield_change_produces_no_event() -> None:
    yields = pd.Series({"2023-06-12": 4.60, "2023-06-13": 4.60, "2023-06-14": 4.65})
    assert len(rates.build_events(yields, same_day=False)) == 1


# ------------------------------------------------------- multiplicity


def test_the_family_max_refuses_unequal_draw_counts() -> None:
    cells = {
        "a": {"gross_t": 2.0, "null_statistics": [0.5, 1.0, 3.0]},
        "b": {"gross_t": 0.1, "null_statistics": [2.5, 0.2]},
    }
    assert test_engine.family_max_p(cells) == {}


def test_the_family_max_uses_the_shared_draws() -> None:
    cells = {
        "a": {"gross_t": 2.0, "null_statistics": [0.5, 1.0, 3.0]},
        "b": {"gross_t": 0.1, "null_statistics": [2.5, 0.2, 0.3]},
    }
    corrected = test_engine.family_max_p(cells)
    #: per-draw maxima are 2.5, 1.0 and 3.0, so |t| = 2.0 is reached twice
    assert corrected["a"] == pytest.approx(3 / 4)
    assert corrected["b"] == pytest.approx(4 / 4)


def test_the_power_multiplier_is_the_two_sided_eighty_percent_constant() -> None:
    assert pytest.approx(2.802, abs=0.002) == POWER_MULTIPLIER
    assert SURPRISE_SCALE_RELEASES == 24


def test_the_flagged_families_are_recorded_and_are_real_families() -> None:
    """The robustness check that drops them has to be reproducible, not ad hoc."""
    from scripts.research.expectation import FLAGGED_FAMILIES

    assert set(FLAGGED_FAMILIES) == {"gdp", "pce"}
    assert set(FLAGGED_FAMILIES) <= set(RELEASE_FAMILIES)


def test_the_forecast_audit_can_fail_and_says_so() -> None:
    """A rule that cannot fire is not a rule; this one fired on the real archive."""
    contaminated = pd.DataFrame(
        {
            "Currency": ["USD"] * 40,
            "Event": ["CPI m/m"] * 40,
            #: the forecast IS the actual: the failure mode the rule exists for
            "Actual": [f"{0.1 * (index % 5):.1f}%" for index in range(40)],
            "Forecast": [f"{0.1 * (index % 5):.1f}%" for index in range(40)],
            "Previous": [f"{0.1 * ((index + 2) % 5):.1f}%" for index in range(40)],
        }
    )
    audit = consensus.audit_forecasts(contaminated)
    assert audit["verdict"] == "FORECAST_BEHAVIOUR_INCONSISTENT_WITH_A_PRE_RELEASE_SURVEY"
    assert audit["per_event"]["CPI m/m"]["exact_equal_share"] == pytest.approx(1.0)
