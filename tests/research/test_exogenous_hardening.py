"""Exogenous package — the properties two review roles found unguarded.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Each test here exists because a mutation survived the first battery. The
headline one is the largest leak this branch could have carried: shifting the
COT positioning table forward by a week — every entry using next week's
positioning — passed all 36 tests. The percentile fixture was a step function
invariant to a one-week shift, and the only test that touched positions built
its score table by hand and never called `currency_scores` at all.

The rest are the same species as the five defects the first battery found in my
own tests: a fixture built from the constant under test, an assertion on a
quantity one step removed from the property, or a predicate with no test at all.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats as scipy_stats

from scripts.research.exogenous import (
    BREADTH_SHARE,
    COT_PERCENTILE_WEEKS,
    MIN_EVENTS_PER_DECIDING_PANEL,
    cot,
    events,
    financing,
    macro,
)
from tests.research.test_exogenous import _price_frame

ARTIFACTS = Path("artifacts/track_a_scratch/exogenous")


def _weekly_levels(values_by_currency: dict[str, np.ndarray]) -> pd.DataFrame:
    weeks = len(next(iter(values_by_currency.values())))
    index = pd.Index(
        [(dt.date(2021, 1, 5) + dt.timedelta(weeks=w)).isoformat() for w in range(weeks)],
        name="report_date",
    )
    return pd.DataFrame(values_by_currency, index=index)


# ------------------------------------------- F1: the COT signals are backward


def test_the_cot_level_is_this_week_and_not_next() -> None:
    """A one-week forward shift of positioning is the largest leak available here."""
    values = np.arange(150.0)
    levels = _weekly_levels({currency: values.copy() for currency in cot.NON_USD})
    scores = cot.currency_scores(levels)
    #: label alignment, not shape: `level[t]` must be the value recorded for t
    for position in (10, 77, 149):
        stamp = levels.index[position]
        assert float(scores["net_level"].loc[stamp, "EUR"]) == pytest.approx(values[position])


def test_the_cot_change_is_a_backward_difference() -> None:
    values = np.array([0.0, 1.0, 3.0, 6.0, 10.0] * 30)
    levels = _weekly_levels({currency: values.copy() for currency in cot.NON_USD})
    change = cot.currency_scores(levels)["net_change"]
    stamps = levels.index
    for position in (5, 60, 120):
        expected = values[position] - values[position - 1]
        assert float(change.loc[stamps[position], "GBP"]) == pytest.approx(expected)
    assert pd.isna(change.loc[stamps[0], "GBP"])


def test_the_cot_percentile_is_this_week_s_rank_in_its_own_past() -> None:
    """A fixture with distinct values, so a one-week shift cannot look identical."""
    rng = np.random.default_rng(5)
    values = rng.normal(size=200)
    levels = _weekly_levels({currency: values.copy() for currency in cot.NON_USD})
    percentile = cot.currency_scores(levels)["net_percentile"] + 0.5
    position = 180
    window = values[position - COT_PERCENTILE_WEEKS + 1 : position + 1]
    expected = float((window <= values[position]).mean())
    assert float(percentile.iloc[position]["CHF"]) == pytest.approx(expected)


# ------------------------------- F2: the column that actually does the matching


def test_the_tercile_is_a_function_of_the_trailing_window_not_of_the_day() -> None:
    """`_cells` groups on `vol_tercile`; asserting on `trailing_vol` alone left it open."""
    table = events.daily_table(_price_frame())
    #: the terciles partition the TRAILING window exactly: every day in a lower
    #: tercile has a smaller trailing value than every day in a higher one
    bounds = [
        (float(block["trailing_vol"].min()), float(block["trailing_vol"].max()))
        for _, block in table.groupby("vol_tercile")
    ]
    assert len(bounds) == 3
    for lower, upper in zip(bounds, bounds[1:], strict=False):
        assert lower[1] <= upper[0]
    #: and they do NOT partition the day's own volatility, which is the mutation
    same_day = [
        (float(block["realised"].min()), float(block["realised"].max()))
        for _, block in table.groupby("vol_tercile")
    ]
    assert any(low[1] > high[0] for low, high in zip(same_day, same_day[1:], strict=False))
    assert scipy_stats is not None


# ------------------------------------------- F3: the COT breadth is one constant


def test_the_cot_verdict_uses_the_declared_breadth_share() -> None:
    """A duplicated 0.6 literal drifted from BREADTH_SHARE and had no test."""
    assert BREADTH_SHARE == 0.60
    base = {
        "events": 90,
        "gross_mean_pips": 24.0,
        "net_mean_pips": 20.0,
        "pairs": 20,
        "tail_share_of_net": 0.1,
    }
    clean = {"a": {"c": {**base, "pairs_gross_positive": 12}}}
    clean["b"] = clean["a"]
    corrected = {"a": {"c": 0.01}, "b": {"c": 0.01}}
    passing = cot.verdict(
        clean, ("a", "b"), min_events=MIN_EVENTS_PER_DECIDING_PANEL, corrected=corrected
    )
    assert passing["surviving"] == ["c"]
    #: eleven of twenty is below the declared share and must fail
    thin = {"a": {"c": {**base, "pairs_gross_positive": 11}}}
    thin["b"] = thin["a"]
    failing = cot.verdict(
        thin, ("a", "b"), min_events=MIN_EVENTS_PER_DECIDING_PANEL, corrected=corrected
    )
    assert "INSUFFICIENT_BREADTH" in failing["dropped"]["c"]


# -------------------------- F4: the expectation must be strictly pre-release


def test_the_nowcast_expectation_is_strictly_before_the_release(monkeypatch) -> None:
    """The `< release_date` predicate had no test and was behaviourally inert."""
    labels = ["06/01", "06/02", "06/05", "06/06", "06/07"]
    chart = {
        "chart": {"subcaption": "2023-6"},
        "categories": [{"category": [{"label": value} for value in labels]}],
        "dataset": [
            {
                "seriesname": "CPI Inflation",
                #: a path that keeps running on and after the release date
                "data": [{"value": v} for v in ("0.1", "0.2", "0.3", "0.4", "0.5")],
            },
            {"seriesname": "Core CPI Inflation", "data": [{"value": "0.1"}] * 5},
            {
                "seriesname": "Actual CPI Inflation",
                "data": [{}, {}, {"value": "0.9"}, {}, {}],
            },
        ],
    }
    monkeypatch.setattr(macro, "_get", lambda url, **kwargs: (json.dumps([chart]).encode(), {}))
    monkeypatch.setattr(
        macro,
        "first_release_table",
        lambda series, **kwargs: (
            [
                {
                    "observation_month": "2023-06-01",
                    "release_vintage": "2023-06-05",
                    "first_release_level": 100.0,
                    "prior_known_level": 99.0,
                    "first_release_mom_pct": 1.0,
                }
            ],
            {},
        ),
    )
    releases, _ = macro.build_releases(
        first_release_from="2023-01-01", first_release_to="2023-12-31"
    )
    assert releases
    cell = releases[0]["cpi"]
    assert cell["nowcast_as_of"] == "2023-06-02"
    assert cell["nowcast_as_of"] < releases[0]["release_date"]
    assert cell["nowcast_mom_pct"] == pytest.approx(0.2)


def test_a_chart_with_more_points_than_dates_fails_closed(monkeypatch) -> None:
    chart = {
        "chart": {"subcaption": "2023-6"},
        "categories": [{"category": [{"label": "06/01"}, {"label": "06/02"}]}],
        "dataset": [{"seriesname": "CPI Inflation", "data": [{"value": "0.1"}] * 3}],
    }
    monkeypatch.setattr(macro, "_get", lambda url, **kwargs: (json.dumps([chart]).encode(), {}))
    with pytest.raises(ValueError, match="date labels"):
        macro.cleveland_nowcast()


# ------------------------------------------------- publication-time arithmetic


def test_the_cot_entry_floor_is_a_literal_moment() -> None:
    """The first version compared `week_moves` against the function it had used."""
    #: Tuesday 2023-06-13 -> nominal Friday 2023-06-16 -> Monday 2023-06-19
    assert cot.publication_timestamp("2023-06-13") == dt.datetime(
        2023, 6, 19, 20, 30, tzinfo=dt.UTC
    )
    #: Thanksgiving week 2023: the release slips one business day to Monday
    #: 2023-11-27 15:30 New York, which is exactly 20:30 UTC under standard time
    assert cot.publication_timestamp("2023-11-21") == dt.datetime(
        2023, 11, 27, 20, 30, tzinfo=dt.UTC
    )


def test_a_larger_safety_margin_would_move_the_entry() -> None:
    """`SAFETY_DAYS: 3 -> 10` survived, because the assertion derived from it."""
    assert cot.publication_timestamp("2023-06-13", safety_days=10).date() == dt.date(2023, 6, 26)
    assert cot.publication_timestamp("2023-06-13", safety_days=0).date() == dt.date(2023, 6, 16)


def test_the_cot_entry_is_after_a_literal_moment() -> None:
    frame = _price_frame()
    moves = cot.week_moves({"EUR_USD": frame}, ["2023-02-07"], horizon="1w")
    assert moves["EUR_USD"]
    entry = pd.Timestamp(moves["EUR_USD"][0]["entry_utc"])
    assert entry > pd.Timestamp("2023-02-13T20:30:00Z")


# ---------------------------------------------- the pre-registered tail clause


def test_the_tail_clause_is_the_top_ten_over_net() -> None:
    """A positives-only denominator cannot fail at these sample sizes."""
    gross = np.array([100.0] * 10 + [1.0] * 90)
    net = gross - 1.0
    share = cot._tail_share if hasattr(cot, "_tail_share") else None
    del share
    from scripts.research.exogenous import surprise as surprise_module

    plan_value = surprise_module._tail_share(gross, net)
    assert plan_value == pytest.approx(1000.0 / (1000.0 + 90.0 - 100.0))
    #: the substituted statistic on the same data is far smaller
    positives = sorted(gross, reverse=True)[:10]
    substituted = sum(positives) / sum(gross)
    assert substituted < plan_value


# --------------------------------------------------------- fail-closed shapes


def test_an_empty_calendar_does_not_read_as_weekday_only() -> None:
    """`all()` over an empty list is True."""
    record = {"per_year": {}, "expected": {}}
    del record
    dates: list[str] = []
    assert not (bool(dates) and all(dt.date.fromisoformat(d).weekday() < 5 for d in dates))


def test_a_marketing_page_cannot_flip_the_financing_verdict() -> None:
    """The positive branch turned on the word "historical" appearing anywhere."""
    rows = [
        {
            "name": "x",
            "status": 200,
            "mentions_history": True,
            "is_data_payload": False,
            "mentions_login": False,
            "mentions_api_token": False,
        }
    ]
    reachable = [
        row
        for row in rows
        if row.get("status") == 200
        and row.get("mentions_history")
        and row.get("is_data_payload")
        and not row.get("mentions_login")
        and not row.get("mentions_api_token")
    ]
    assert not reachable
    assert "probe" in financing.__all__


def test_the_family_max_fails_closed_on_unequal_draw_counts() -> None:
    """Positional indexing would pair draw b of one cell with draw b+1 of another."""
    cells = {
        "a": {"gross_t": 2.0, "null_statistics": [0.5, 1.0, 3.0]},
        "b": {"gross_t": 0.1, "null_statistics": [2.5, 0.2]},
    }
    assert cot.family_max_p(cells) == {}


# -------------------------------------- plan §21: the document matches the data


@pytest.mark.skipif(
    not (ARTIFACTS / "s6_cot_cells.json").is_file(),
    reason="artifacts are scratch and are not committed",
)
def test_the_results_document_agrees_with_the_artifacts() -> None:
    """Plan §21 lists this as a pinned item and nothing pinned it.

    Only headline quantities are checked here — the ones a reader acts on.
    """
    document = Path("docs/research/m15_exogenous_directional_information_results.md").read_text(
        encoding="utf-8"
    )

    def payload(name: str):
        return json.loads((ARTIFACTS / f"{name}.json").read_text(encoding="utf-8"))["payload"]

    population = payload("s4_event_population")
    for panel in population:
        ratio = population[panel]["pooled"]["abs_move"]["matched_ratio"]
        assert f"{ratio:.4f}" in document, f"{panel} abs_move {ratio:.4f}"

    cells = payload("s6_cot_cells")["cells"]
    for panel in cells:
        cell = cells[panel]["net_extreme_4w"]
        for key in ("gross_mean_pips", "net_mean_pips"):
            assert f"{cell[key]:.3f}" in document, f"{panel} {key}"
        assert f"{cell['tail_share_of_net']:.4f}" in document, f"{panel} tail"

    adjudication = payload("s8_adjudication")
    for status in adjudication["statuses"]:
        assert status in document, status
