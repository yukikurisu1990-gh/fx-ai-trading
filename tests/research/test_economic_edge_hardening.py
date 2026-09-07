"""Economic Edge — the tests that had to exist after two review roles read it.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

A review role mutated the package 30 ways and **nine survived**, including a
one-day look-ahead in the rate join that changed 959 of 50,019 bars by up to
0.50 percentage points and still passed 25 of 25 tests. The cause was uniform:
every carry test built a *constant* rate panel, so the join date was invisible
to all of them; and four tests did not test what they were named for.

Both roles also found the round's one false headline — a day-of-week composition
artefact in the calendar comparison — so the day-matching that now controls for
it is pinned here.

Each test names the mutation it kills, and every one asserts on behaviour.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import pytest

from scripts.research.economic_edge import (
    CURRENCIES,
    calendar_events,
    carry,
    driver,
    opportunity,
    rates,
)
from scripts.research.exploratory_m15 import PAIRS
from scripts.research.round_b_prime import nulls


@pytest.fixture
def price_frame() -> pd.DataFrame:
    rng = np.random.default_rng(4)
    frame = nulls.random_walk_frame(96 * 200, rng)
    frame["roundtrip_cost"] = 2.5
    frame["volume"] = np.exp(rng.normal(7.0, 0.6, len(frame)))
    return frame


# ------------------------------------------------------- the rate join date


def _stepped_panel(step_day: str) -> pd.DataFrame:
    """A rate panel where JPY steps on a known calendar day, everything else flat."""
    index = pd.date_range("2021-12-01", "2023-12-31", freq="D", tz="UTC")
    panel = pd.DataFrame({c: 0.0 for c in CURRENCIES}, index=index)
    panel.loc[step_day:, "JPY"] = -4.0
    return panel


def test_the_rate_join_reads_the_bars_own_day_and_no_later(price_frame) -> None:
    """Kills a one-day look-ahead in `attach_rates`.

    Every other carry test builds a **constant** rate panel, so the join date is
    invisible to all of them — a mutant joining `day + 1` changed 959 of 50,019
    bars by up to 0.50 percentage points and passed the whole suite.
    """
    step = "2022-06-15"
    panel = _stepped_panel(step)
    attached = carry.attach_rates(price_frame, panel, "AUD_JPY")
    day = attached["ts"].dt.floor("D")

    before = attached.loc[(day < step).to_numpy(), "carry_rate_pct"]
    on_the_day = attached.loc[(day == step).to_numpy(), "carry_rate_pct"]
    after = attached.loc[(day > step).to_numpy(), "carry_rate_pct"]
    assert len(on_the_day) > 0, "the fixture does not span the step day"
    assert (before == 0.0).all()
    #: the panel is already lagged upstream, so a bar on the step day must read
    #: the value the panel carries for that day -- never the next day's
    assert (on_the_day == 4.0).all(), "a bar read a rate dated after its own day"
    assert (after == 4.0).all()


def test_the_fred_override_forward_fills_before_it_is_lagged(monkeypatch) -> None:
    """Kills a `_fred_daily` that skips its forward fill.

    Real `ECBDFR` is dense, so the defect is latent on today's data — which is
    exactly why it needs a constructed sparse series to be visible at all.
    """
    sparse = b"observation_date,ECBDFR\n2022-01-03,-0.50\n2022-07-27,0.00\n2022-09-14,0.75\n"

    class _Response:
        def read(self) -> bytes:
            return sparse

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(rates.urllib.request, "urlopen", lambda *_a, **_k: _Response())
    index = pd.date_range("2022-07-20", "2022-07-31", freq="D", tz="UTC")
    series, digest = rates._fred_daily("ECBDFR", index)

    assert series.notna().all(), "the override left gaps; it did not forward-fill"
    assert series.loc["2022-07-26"] == pytest.approx(-0.50)
    assert series.loc["2022-07-27"] == pytest.approx(0.00)
    assert len(digest) == 64


def test_the_override_records_its_own_provenance(monkeypatch) -> None:
    """Kills a discarded digest.

    The EUR leg appears in 6 of 20 pairs and its real source is a FRED series,
    not the BIS one the provenance artifact described. The first version
    computed the digest and threw it away.
    """
    dense = "observation_date,ECBDFR\n" + "".join(
        f"{d.date()},1.25\n" for d in pd.date_range("2023-12-25", "2024-01-10", freq="D")
    )

    class _Response:
        def read(self) -> bytes:
            return dense.encode()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(rates.urllib.request, "urlopen", lambda *_a, **_k: _Response())
    rates.OVERRIDE_PROVENANCE.clear()

    rows = []
    for currency in CURRENCIES:
        for day in ("2023-12-26", "2024-01-02"):
            rows.append((currency, day, 2.0))
    frame = pd.DataFrame(rows, columns=["currency", "date", "rate_pct"])
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    rates.daily_panel(frame, "2023-12-28", "2024-01-08")

    record = rates.OVERRIDE_PROVENANCE.get("EUR")
    assert record is not None, "the EUR override left no provenance record"
    for key in ("series", "url", "sha256", "observations", "revision_behaviour", "replaces"):
        assert record.get(key), f"the override record has no {key}"
    assert len(record["sha256"]) == 64


def test_the_download_record_keeps_the_headers_the_server_sends() -> None:
    """Kills a case-sensitive header lookup that silently nulled the file vintage."""
    import email.message

    message = email.message.Message()
    message["Last-Modified"] = "Wed, 02 Sep 2026 07:35:06 GMT"
    message["Content-Type"] = "application/zip"

    class _Response:
        headers = message

        def read(self) -> bytes:
            return b"payload"

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    import unittest.mock

    with unittest.mock.patch.object(rates.urllib.request, "urlopen", lambda *_a, **_k: _Response()):
        _payload, record = rates._download("https://example.invalid/x.zip")
    assert record["last_modified"] == "Wed, 02 Sep 2026 07:35:06 GMT"
    assert record["content_type"] == "application/zip"


# ------------------------------------------------------------ carry basket


def test_the_cross_sectional_targets_the_code_builds_sum_to_zero() -> None:
    """Kills a non-neutral basket.

    The original test re-derived the target **inside itself** rather than
    reading what the code builds, so it could not see the code's version become
    non-neutral.
    """
    index = pd.date_range("2024-01-01", "2024-01-05", freq="D", tz="UTC")
    panel = pd.DataFrame({c: float(r) for r, c in enumerate(CURRENCIES)}, index=index)
    for k in (2, 3):
        positions = carry.cross_sectional_positions(panel, PAIRS, k=k)
        exposure = carry.realised_currency_exposure(positions, PAIRS)
        assert sum(exposure.values()) == pytest.approx(0.0, abs=1e-9)
        #: and the long and short legs are non-trivial, so neutrality is not
        #: being satisfied by an all-zero book
        assert max(exposure.values()) > 0.1
        assert min(exposure.values()) < -0.1


def test_the_dead_band_actually_excludes_a_small_differential(price_frame) -> None:
    """Kills a dead band set to zero.

    The original test used a **zero** differential, which stays flat at any band
    including zero.
    """
    index = pd.date_range("2021-12-01", "2023-12-31", freq="D", tz="UTC")
    panel = pd.DataFrame({c: 0.0 for c in CURRENCIES}, index=index)
    #: inside the band -- must not trade
    panel["AUD"] = 0.10
    inside = carry.signal_pair_level(
        carry.attach_rates(price_frame, panel, "AUD_JPY"), stride=96 * 5, phase=0
    )
    assert inside.abs().sum() == 0.0, "a differential inside the dead band opened a position"

    #: outside it -- must trade, and long, since the base yields more
    panel["AUD"] = 1.00
    outside = carry.signal_pair_level(
        carry.attach_rates(price_frame, panel, "AUD_JPY"), stride=96 * 5, phase=0
    )
    assert outside.max() == pytest.approx(1.0)


def test_the_bloc_decomposition_separates_what_the_pooled_row_hides() -> None:
    """A pooled 'spot did not take the carry away' can be false of every part."""
    index = pd.date_range("2024-01-01", periods=8, freq="D", tz="UTC")

    def row(spot: float, carry_pips: float) -> dict[str, Any]:
        return {
            "spot_pips": spot,
            "carry_pips": carry_pips,
            "net_pips": spot + carry_pips,
            "_daily": pd.Series((spot + carry_pips) / 8.0, index=index),
        }

    per_pair = {
        "AUD_JPY": row(200.0, 60.0),
        "EUR_JPY": row(200.0, 60.0),
        "EUR_USD": row(-40.0, 45.0),
        "GBP_USD": row(-40.0, 45.0),
    }
    out = carry.bloc_decomposition(per_pair)
    assert out["JPY"]["net_pips"] == pytest.approx(260.0)
    assert out["non_JPY"]["net_pips"] == pytest.approx(5.0)
    assert out["non_JPY"]["spot_pips"] < 0 < out["non_JPY"]["carry_pips"]


# ---------------------------------------------------- the calendar comparison


def _daily_with_sundays(days: int = 200) -> pd.DataFrame:
    """A frame whose Sunday sessions are thin, wide and quiet, as the panels' are."""
    stamps = pd.date_range("2024-01-01", periods=96 * days, freq="15min", tz="UTC")
    frame = pd.DataFrame({"ts": stamps})
    frame["pip_size"] = 0.0001
    sunday = frame["ts"].dt.dayofweek == 6
    #: keep only the last 10 bars of each Sunday, as the archive does
    hour = frame["ts"].dt.hour
    frame = frame[~sunday | (hour >= 21)].reset_index(drop=True)
    rng = np.random.default_rng(1)
    frame["mid_c"] = 1.10 + np.cumsum(rng.normal(0.0, 0.0002, len(frame)))
    is_sunday = frame["ts"].dt.dayofweek == 6
    frame["spread_close_pips"] = np.where(is_sunday, 4.5, 1.5)
    frame["roundtrip_cost"] = frame["spread_close_pips"] + 0.5
    return frame


def test_the_sunday_session_is_dropped_from_the_daily_table() -> None:
    """Kills the composition artefact that produced this round's false headline.

    The M15 panels carry a Sunday pseudo-session of 4–12 bars against about 95
    on a weekday, with a much wider spread. Leaving it in the control group made
    event days look cheaper than they are.
    """
    table = calendar_events._daily_market(_daily_with_sundays())
    assert not table.empty
    assert (table["bars"] >= calendar_events.MIN_BARS_FOR_A_TRADING_DAY).all()
    assert (table["dayofweek"] != 6).all(), "a Sunday pseudo-session survived the filter"
    assert calendar_events.MIN_BARS_FOR_A_TRADING_DAY > 12


def test_the_matched_ratio_removes_a_weekday_composition_effect() -> None:
    """The ratio the verdict reads must be computed within day of week.

    Constructed so that the level differs by weekday and the event days sit
    only on the high-level weekday: the raw ratio then reports an effect that
    the matched one correctly reports as absent.
    """
    index = pd.date_range("2024-01-01", periods=120, freq="D", tz="UTC")
    table = pd.DataFrame(index=index)
    table["dayofweek"] = index.dayofweek
    #: Wednesdays are simply a bigger day, for everyone, event or not
    table["x"] = np.where(table["dayofweek"] == 2, 10.0, 1.0)
    #: events land on Wednesdays only -- but not on every Wednesday, so the
    #: matched comparison has a within-weekday control to compare against
    near = pd.Series((table["dayofweek"] == 2) & (np.arange(len(index)) % 14 < 7), index=index)

    raw = float(table.loc[near, "x"].mean() / table.loc[~near, "x"].mean())
    matched = calendar_events._matched_ratio(table, near, "x")
    assert raw > 4.0, f"the fixture does not produce a composition effect (raw {raw:.2f})"
    assert matched == pytest.approx(1.0, abs=1e-6), (
        f"the matched ratio reports {matched} where the effect is entirely weekday; "
        "it is not controlling for day of week"
    )


def test_the_event_window_really_reaches_both_sides() -> None:
    """Kills a one-sided window, measured through `event_population` itself.

    The original test asserted only that `WINDOW_DAYS == 1` and never ran the
    loop, so a window that reached forward and not back survived. Counting the
    flagged days separates them: eight Wednesday changes give 24 days two-sided
    and 16 one-sided.
    """
    frame = _daily_with_sundays()
    stamps = frame["ts"]
    span = pd.date_range(stamps.min().floor("D"), stamps.max().floor("D"), freq="D", tz="UTC")
    panel = pd.DataFrame({c: 1.0 for c in CURRENCIES}, index=span)
    wednesdays = span[span.dayofweek == 2]
    changes = list(wednesdays[1:9])
    for index, day in enumerate(changes):
        panel.loc[day:, "JPY"] = 2.0 + index

    #: the pair must contain the leg whose rate moves
    summary = calendar_events.event_population({"USD_JPY": frame}, panel)
    assert summary.get("pairs") == 1, f"the pair was skipped: {summary}"
    assert summary["event_days_mean"] == pytest.approx(3 * len(changes)), (
        f"the window flagged {summary['event_days_mean']} days for {len(changes)} "
        f"changes; a two-sided window gives {3 * len(changes)}"
    )
    assert calendar_events.WINDOW_DAYS == 1


def _calendar_rows(matched: float, breadth: int, pairs: int) -> dict[str, Any]:
    def column(value: float) -> dict[str, Any]:
        return {"ratio": value, "matched_ratio": value, "pairs_matched_ratio_above_one": breadth}

    return {
        "pairs": pairs,
        "abs_move": column(1.3),
        "spread": column(1.02),
        "move_less_cost": column(matched),
        "exceeds_cost": column(1.00),
    }


def test_the_calendar_verdict_needs_breadth_and_a_null() -> None:
    """`calendar_events.verdict` had no test at all."""
    good = {p: _calendar_rows(1.35, 18, 20) for p in driver.DECIDING_PANELS}
    permutations = {p: {"p_two_sided": 0.01} for p in driver.DECIDING_PANELS}
    passing = calendar_events.verdict(good, driver.DECIDING_PANELS, permutations)
    assert passing["status"] == "CALENDAR_EVENT_MOVEMENT_STRUCTURE_SUPPORTED"
    assert passing["read"] == "day-of-week matched ratios"

    #: and it must read the MATCHED ratio, not the raw one. This is the exact
    #: shape of the artefact two review roles found: raw says there is an
    #: effect, matched says there is not.
    contaminated = {
        p: {
            "pairs": 20,
            "abs_move": {"ratio": 1.5, "matched_ratio": 1.0, "pairs_matched_ratio_above_one": 18},
            "spread": {"ratio": 0.92, "matched_ratio": 1.04, "pairs_matched_ratio_above_one": 2},
            "move_less_cost": {
                "ratio": 1.6,
                "matched_ratio": 0.98,
                "pairs_matched_ratio_above_one": 18,
            },
            "exceeds_cost": {
                "ratio": 1.04,
                "matched_ratio": 1.0,
                "pairs_matched_ratio_above_one": 10,
            },
        }
        for p in driver.DECIDING_PANELS
    }
    fooled = calendar_events.verdict(contaminated, driver.DECIDING_PANELS, permutations)
    assert fooled["status"].endswith("NOT_SUPPORTED"), (
        "the verdict was fooled by the unmatched ratio"
    )
    assert fooled["cost_advantage_status"] == "EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED"

    #: breadth alone can kill it
    thin = {p: _calendar_rows(1.35, 5, 20) for p in driver.DECIDING_PANELS}
    assert calendar_events.verdict(thin, driver.DECIDING_PANELS, permutations)["status"].endswith(
        "NOT_SUPPORTED"
    )
    #: so can the null
    weak = {p: {"p_two_sided": 0.40} for p in driver.DECIDING_PANELS}
    assert calendar_events.verdict(good, driver.DECIDING_PANELS, weak)["status"].endswith(
        "NOT_SUPPORTED"
    )
    #: and the cost claim is its own clause, not assumed by the movement one
    assert passing["spread_is_narrower"] is False
    assert passing["cost_advantage_status"] == "EVENT_DAY_COST_ADVANTAGE_NOT_ESTABLISHED"

    cheaper = {p: _calendar_rows(1.35, 18, 20) for p in driver.DECIDING_PANELS}
    for row in cheaper.values():
        row["spread"] = {"ratio": 0.92, "matched_ratio": 0.92, "pairs_matched_ratio_above_one": 2}
    assert (
        calendar_events.verdict(cheaper, driver.DECIDING_PANELS, permutations)[
            "cost_advantage_status"
        ]
        == "EVENT_DAY_COST_ADVANTAGE_ESTABLISHED"
    )


# ------------------------------------------------------------- fail closed


def test_the_integration_status_fails_closed_on_missing_panels() -> None:
    """Kills a status that flips to 'adds value' on no data.

    `all(...)` over an empty list is `True`, so a missing deciding panel turned
    every representation into an improvement.
    """
    assert driver._improves({}, driver.DECIDING_PANELS) == dict.fromkeys(
        driver.VOLUME_REPRESENTATIONS, False
    )
    one_panel = {
        driver.DECIDING_PANELS[0]: {
            "M1_expected_return_only": 10.0,
            "M3_combined": dict.fromkeys(driver.VOLUME_REPRESENTATIONS, 999.0),
        }
    }
    assert not any(driver._improves(one_panel, driver.DECIDING_PANELS).values()), (
        "one panel was enough to declare an improvement on both"
    )


def test_an_unmeasurable_tail_share_is_not_a_pass() -> None:
    """Kills `v is None or ...`, which let an undefined tail share clear the clause."""

    def cells(tail: float | None) -> dict[str, Any]:
        row = {
            "gross_pips": 100.0,
            "net_pips": 90.0,
            "spot_pips": 10.0,
            "carry_pips": 90.0,
            "top10_day_share": tail,
            "largest_pair_share": 0.2,
            "jpy_mean_net": 50.0,
            "non_jpy_mean_net": 40.0,
        }
        return {"cell": {p: {"x1.0": dict(row), "x2.0": dict(row)} for p in driver.DECIDING_PANELS}}

    assert driver._carry_verdict(cells(0.2))["surviving"] == ["cell"]
    assert driver._carry_verdict(cells(None))["surviving"] == []
    assert driver._carry_verdict(cells(float("nan")))["surviving"] == []


def test_the_carry_verdict_reads_the_cost_level_it_names() -> None:
    """Kills a verdict that reads `x2.0` where it means `x1.0`.

    The original fixture wrote identical dicts to both levels, so the key was
    unfalsifiable.
    """
    base = {
        "gross_pips": 100.0,
        "net_pips": 90.0,
        "spot_pips": 10.0,
        "carry_pips": 90.0,
        "top10_day_share": 0.2,
        "largest_pair_share": 0.2,
        "jpy_mean_net": 50.0,
        "non_jpy_mean_net": 40.0,
    }
    doubled = dict(base) | {"gross_pips": -100.0, "net_pips": -90.0}
    cells = {
        "cell": {p: {"x1.0": dict(base), "x2.0": dict(doubled)} for p in driver.DECIDING_PANELS}
    }
    row = driver._carry_verdict(cells)["per_cell"]["cell"]
    assert row["gross_positive_both_panels"] is True, "the verdict read the 2C level for gross"
    assert row["net_positive_at_2c"] is False, "the verdict read the 1C level for the 2C clause"
    assert row["net_pips"] == [90.0, 90.0]
    assert row["net_pips_2c"] == [-90.0, -90.0]


# --------------------------------------------------------- forward targets


def test_the_forward_volatility_target_is_forward(price_frame) -> None:
    """Kills a dropped final shift. Only the absolute-return target was checked."""
    table = opportunity.daily_state(price_frame)
    assert not table.empty
    realised = table["realised"].to_numpy(dtype=float)
    window = opportunity.FORWARD_DAYS
    expected = np.array(
        [
            realised[i + 1 : i + 1 + window].mean() if i + window < len(realised) else np.nan
            for i in range(len(realised))
        ]
    )
    got = table["future_realised_volatility"].to_numpy(dtype=float)
    keep = np.isfinite(expected) & np.isfinite(got)
    assert keep.sum() > 100
    assert np.allclose(got[keep], expected[keep], atol=1e-9), (
        "the forward volatility target does not average the NEXT five days"
    )


def test_the_vacuous_rate_lag_assertion_is_replaced(price_frame) -> None:
    """The original test asserted `panel is None` and a constant. This measures it."""
    step = "2022-09-14"
    long_form = pd.DataFrame(
        [(c, d, 0.0 if d < step else 3.0) for c in CURRENCIES for d in ("2021-12-01", step)],
        columns=["currency", "date", "rate_pct"],
    )
    long_form["date"] = pd.to_datetime(long_form["date"], utc=True)
    import unittest.mock

    with unittest.mock.patch.dict(rates.POLICY_RATE_OVERRIDE, {}, clear=True):
        panel = rates.daily_panel(long_form, "2022-09-01", "2022-09-30")
    assert panel.loc[step, "USD"] == pytest.approx(0.0), (
        "the new rate was readable on its own effective date"
    )
    assert panel.loc["2022-09-15", "USD"] == pytest.approx(3.0)
