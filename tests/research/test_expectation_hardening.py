"""Expectation Benchmark — the properties two review roles found unguarded.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Every test here exists because a mutation survived the first suite. Three of
them were leak-shaped: an archive row dated **after** the release could join to
it, an event's own surprise could enter its own scale, and the COT-style
decision hour could move to before the number it trades on was public. None of
those defects is in the shipped code; all three were simply unguarded.

The rest are the same species this programme keeps rediscovering — a fixture
built from the constant under test, or an assertion one step removed from the
property. The worst example here was a cost test whose entry bar and exit bar
both sat inside the same widened-spread block, so reading the cost from the
wrong bar was invisible.

Nothing here reaches the network.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
import pytest

from scripts.research.expectation import (
    FLAGGED_FAMILIES,
    RELEASE_FAMILIES,
    RELEASE_LOCAL_TIME,
    RELEASE_TIMEZONE,
    consensus,
    rates,
    test_engine,
)

EMPTY_DATES: dict[str, dict[str, list[str]]] = {name: {"dates": []} for name in RELEASE_FAMILIES}


def _archive(rows: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["ts"] = pd.to_datetime(frame["ts"], utc=True)
    return frame


def _linear_frame(*, days: int = 40, pip: float = 0.01, spread: float = 1.5) -> pd.DataFrame:
    stamps: list[pd.Timestamp] = []
    day = pd.Timestamp("2023-06-01T00:00:00Z")
    while len({s.date() for s in stamps}) < days:
        if day.weekday() < 5:
            stamps.extend(day + pd.Timedelta(minutes=15 * step) for step in range(96))
        day = day + pd.Timedelta(days=1)
    index = pd.DatetimeIndex(stamps)
    #: exactly one pip per bar, so a horizon error is arithmetic rather than luck
    level = 150.0 + pip * np.arange(len(index))
    return pd.DataFrame(
        {
            "ts": index,
            "mid_o": level,
            "mid_h": level,
            "mid_l": level,
            "mid_c": level,
            "spread_close_pips": spread,
            "pip_size": pip,
        }
    )


# ------------------------------------------------------- the join, both sides


def test_an_archive_row_dated_after_the_release_does_not_join() -> None:
    """The window is [release − 1, release]. An upper bound of +1 would leak."""
    dates = {**EMPTY_DATES, "cpi": {"dates": ["2023-06-13"]}}
    after = _archive(
        [
            {
                "Currency": "USD",
                "Event": "CPI m/m",
                "Actual": "0.4%",
                "Forecast": "0.3%",
                "Previous": "0.2%",
                #: the day AFTER the release: information that did not exist
                "ts": "2023-06-14T20:30:00Z",
            }
        ]
    )
    events, diagnostics = consensus.build_events(after, dates)
    assert events == []
    assert diagnostics["unmatched_by_event"]["CPI m/m"] == 1
    assert "CPI m/m" in diagnostics["signals_that_never_matched"]


def test_two_candidate_rows_in_one_window_drop_both() -> None:
    """Taking the first would silently pick one of two contradictory values."""
    dates = {**EMPTY_DATES, "cpi": {"dates": ["2023-06-13"]}}
    ambiguous = _archive(
        [
            {
                "Currency": "USD",
                "Event": "CPI m/m",
                "Actual": "0.4%",
                "Forecast": "0.3%",
                "Previous": "0.2%",
                "ts": "2023-06-12T20:30:00Z",
            },
            {
                "Currency": "USD",
                "Event": "CPI m/m",
                "Actual": "0.9%",
                "Forecast": "0.1%",
                "Previous": "0.2%",
                "ts": "2023-06-13T09:00:00Z",
            },
        ]
    )
    events, diagnostics = consensus.build_events(ambiguous, dates)
    assert events == []
    assert diagnostics["ambiguous"] == 1


def test_the_merged_event_carries_the_alfred_timestamp_not_the_archive_one() -> None:
    """The archive is 16-17 hours early; nothing downstream may inherit that."""
    dates = {**EMPTY_DATES, "cpi": {"dates": ["2023-06-13"]}}
    archive = _archive(
        [
            {
                "Currency": "USD",
                "Event": "CPI m/m",
                "Actual": "0.4%",
                "Forecast": "0.3%",
                "Previous": "0.2%",
                "ts": "2023-06-12T20:30:00Z",
            }
        ]
    )
    events, _ = consensus.build_events(archive, dates)
    assert len(events) == 1
    #: 08:30 America/New_York on the ALFRED vintage date, in June, is 12:30 UTC
    assert events[0]["release_timestamp_utc"] == "2023-06-13T12:30:00+00:00"
    assert "2023-06-12" not in events[0]["release_timestamp_utc"]


def test_the_conversion_in_use_is_the_one_this_package_froze() -> None:
    rule = consensus.release_time_rule()
    assert (rule["local_time"], rule["timezone"]) == (RELEASE_LOCAL_TIME, RELEASE_TIMEZONE)


def test_a_substituted_archive_is_refused(monkeypatch) -> None:
    """A digest that is measured and printed but never read is not a check."""
    payload = b"DateTime,Currency,Impact,Event,Actual,Forecast,Previous,Detail\n"
    monkeypatch.setattr(
        consensus, "_get", lambda url, **kwargs: (payload, {"sha256": "deadbeef" * 8})
    )
    with pytest.raises(RuntimeError, match="does not match the frozen"):
        consensus.acquire_archive()


# ----------------------------------------------------- the backward-only scale


def test_an_events_own_surprise_never_enters_its_own_scale() -> None:
    """Including it would shrink a large surprise toward zero using itself."""
    history = [
        {
            "release_date": f"2023-{index + 1:02d}-10",
            "release_timestamp_utc": f"2023-{index + 1:02d}-10T12:30:00+00:00",
            "families": ["cpi"],
            "signals": {"CPI m/m": {"raw_surprise": value}},
        }
        for index, value in enumerate([0.1, -0.1, 0.1, -0.1, 0.1, 6.0])
    ]
    scaled = consensus.attach_surprises(history)
    last = scaled[-1]["composite_z"]
    #: the scale is the sd of [0.1, -0.1, 0.1, -0.1, 0.1] alone
    expected_scale = float(np.std([0.1, -0.1, 0.1, -0.1, 0.1], ddof=1))
    assert last == pytest.approx(6.0 / expected_scale)
    #: and including the 6.0 would have given something far smaller
    contaminated = float(np.std([0.1, -0.1, 0.1, -0.1, 0.1, 6.0], ddof=1))
    assert 6.0 / contaminated < last / 5.0


# ------------------------------------------------------------------ execution


def test_the_horizon_is_exactly_the_bars_it_says() -> None:
    """One pip per bar, so an off-by-four exit is an arithmetic mismatch."""
    frame = _linear_frame()
    event = {
        "release_timestamp_utc": frame["ts"].iloc[200].isoformat(),
        "families": ("cpi",),
        "composite_z": 1.0,
    }
    table = test_engine.event_returns({"USD_JPY": frame}, [event], horizon_bars=4)
    assert len(table) == 1
    #: entry is bar 201's open, exit is bar 205's close, four pips apart
    assert table["usd_move_pips"].iloc[0] == pytest.approx(4.0)


def test_the_cost_is_the_entry_bars_spread_and_not_the_exits() -> None:
    """A first version widened entry and exit together, hiding the difference."""
    frame = _linear_frame()
    frame.loc[201, "spread_close_pips"] = 8.0
    frame.loc[205, "spread_close_pips"] = 30.0
    event = {
        "release_timestamp_utc": frame["ts"].iloc[200].isoformat(),
        "families": ("cpi",),
        "composite_z": 1.0,
    }
    table = test_engine.event_returns({"USD_JPY": frame}, [event], horizon_bars=4)
    assert table["cost_pips"].iloc[0] == pytest.approx(8.5)


# --------------------------------------------------------------- rates branch


def test_the_rates_decision_moment_is_a_literal_and_is_after_the_print() -> None:
    """The fixture must not be built from the constant it is testing."""
    yields = pd.Series({"2023-06-12": 4.60, "2023-06-13": 4.70})
    lead = rates.build_events(yields, same_day=False)
    assert lead[0]["release_timestamp_utc"] == "2023-06-13T22:00:00+00:00"
    #: H.15 posts around 16:15 America/New_York; 22:00 UTC is 18:00 EDT
    moment = dt.datetime.fromisoformat(lead[0]["release_timestamp_utc"])
    assert moment.hour >= 21


def test_days_with_no_repricing_are_counted_not_silently_dropped() -> None:
    yields = pd.Series({"2023-06-12": 4.60, "2023-06-13": 4.60, "2023-06-14": 4.65})
    events = rates.build_events(yields, same_day=False)
    assert len(events) == 1
    assert events[0]["days_dropped_for_zero_change"] == 1


# ------------------------------------------------------------- verdict clauses


def _cell(**overrides: object) -> dict[str, object]:
    base = {
        "events": 200,
        "gross_mean_pips": 5.0,
        "net_mean_pips": 2.0,
        "tail_share_of_net": 0.1,
    }
    return {**base, **overrides}


def _decide(panels: dict[str, dict[str, object]], corrected: dict[str, dict[str, float]]):
    return test_engine.verdict(
        panels,
        ("a", "b"),
        primary=("cell",),
        corrected=corrected,
        min_events=90,
        supported_status="SUPPORTED",
        not_supported_status="NOT_SUPPORTED",
    )


def test_a_missing_familywise_correction_fails_closed() -> None:
    """A `None` must not be read as 'no evidence against', which is a pass."""
    panels = {"a": {"cell": _cell()}, "b": {"cell": _cell()}}
    assert _decide(panels, {"a": {"cell": 0.01}, "b": {"cell": 0.01}})["status"] == "SUPPORTED"
    assert _decide(panels, {"a": {"cell": 0.01}, "b": {}})["status"] == "NOT_SUPPORTED"
    assert "FAMILYWISE_NULL_cell" in _decide(panels, {"a": {}, "b": {}})["drop_reasons"]


def test_the_tail_ceiling_actually_fires() -> None:
    fat = _cell(tail_share_of_net=0.75)
    decision = _decide(
        {"a": {"cell": fat}, "b": {"cell": fat}}, {"a": {"cell": 0.01}, "b": {"cell": 0.01}}
    )
    assert "TAIL_ABOVE_CEILING_cell" in decision["drop_reasons"]
    assert decision["status"] == "NOT_SUPPORTED"


def test_a_missing_panel_fails_closed() -> None:
    """`all()` over one panel is not a two-panel result."""
    decision = _decide({"a": {"cell": _cell()}}, {"a": {"cell": 0.01}})
    assert decision["complete"] is False
    assert "PANEL_MISSING" in decision["drop_reasons"]
    assert decision["status"] == "NOT_SUPPORTED"


# --------------------------------------------------- the IC has a null band now


def test_the_directional_ic_carries_its_own_null() -> None:
    """A bare IC invites a 'real in sign' claim its dispersion does not support."""
    rng = np.random.default_rng(2)
    n = 400
    table = pd.DataFrame(
        {
            "event": np.arange(n),
            "pair": ["EUR_USD"] * n,
            "signal": rng.normal(size=n),
            "usd_move_pips": rng.normal(0.0, 20.0, size=n),
            "cost_pips": 2.0,
        }
    )
    cell = test_engine.evaluate(table, draws=200)
    assert cell["directional_ic_null_sd"] is not None
    assert cell["directional_ic_permutation_p"] is not None
    #: pure noise: the IC must sit inside its own band
    assert abs(cell["directional_ic"]) < 3.0 * cell["directional_ic_null_sd"]
    assert "reference_statistic_not_a_t" in cell


# ------------------------------------------------- the flagged-signal exclusion


def test_the_flagged_families_name_real_signals() -> None:
    flagged = {
        name
        for family in FLAGGED_FAMILIES
        for name in RELEASE_FAMILIES[family]["events"]  # type: ignore[index]
    }
    assert "Core PCE Price Index m/m" in flagged
    assert "Advance GDP q/q" in flagged
    #: and the exclusion is at signal level: a mixed moment loses only these
    assert "CPI m/m" not in flagged
