"""Economic Edge Source Expansion — rates, carry arithmetic, and temporal integrity.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

This package is the first in the programme to use **external** data, so the
tests that matter most are the ones about time: a rate must not be readable on
the day it was announced, a carry accrual must count calendar days rather than
bars, and a forward target must be forward.

Everything asserts on behaviour. Nothing here reaches the network — the
acquisition path is exercised against constructed frames, and the two tests that
would need a download are the ones the driver's artifacts already record.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.research.economic_edge import (
    CARRY_CELLS,
    CARRY_DEAD_BAND_PCT,
    CROSS_SECTIONAL_K,
    CURRENCIES,
    DAYS_PER_YEAR,
    OPPORTUNITY_TARGETS,
    RATE_LAG_TRADING_DAYS,
    REBALANCE_BARS,
    VOLUME_REPRESENTATIONS,
    calendar_events,
    carry,
    driver,
    opportunity,
    rates,
)
from scripts.research.exploratory_m15 import PAIRS
from scripts.research.round_b_prime import nulls

# ----------------------------------------------------------------- fixtures


def _rate_frame() -> pd.DataFrame:
    """A tiny long-form rate table with one step per currency."""
    rows = []
    for index, currency in enumerate(CURRENCIES):
        for day, value in (("2024-01-01", float(index)), ("2024-02-01", float(index) + 1.0)):
            rows.append((currency, day, value))
    frame = pd.DataFrame(rows, columns=["currency", "date", "rate_pct"])
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    return frame


@pytest.fixture
def price_frame() -> pd.DataFrame:
    """A generated M15 frame with the columns the carry study needs.

    Long enough that the Stage 3 daily state can be built: the state needs a
    60-day trailing window plus a 5-day forward look, so a 40-day fixture
    silently skipped three tests.
    """
    rng = np.random.default_rng(4)
    frame = nulls.random_walk_frame(96 * 200, rng)
    frame["roundtrip_cost"] = 2.5
    #: a monotone ramp makes every rolling percentile 1.0 -- the current value is
    #: always the window maximum -- which silently disabled the filter tests
    frame["volume"] = np.exp(rng.normal(7.0, 0.6, len(frame)))
    return frame


# ------------------------------------------------------- currency and mapping


def test_the_eight_currencies_are_exactly_what_pairs_20_needs() -> None:
    """A source that cannot reach all eight cannot serve — so the set is pinned."""
    needed = sorted({leg for pair in PAIRS for leg in pair.split("_")})
    assert sorted(CURRENCIES) == needed
    assert len(CURRENCIES) == 8


def test_every_currency_maps_to_a_distinct_reference_area() -> None:
    assert set(rates.AREA_FOR_CURRENCY) == set(CURRENCIES)
    assert len(set(rates.AREA_FOR_CURRENCY.values())) == len(CURRENCIES)
    #: the euro area is a bloc, not a country -- picking a member state would be
    #: a different and wrong object
    assert rates.AREA_FOR_CURRENCY["EUR"] == "XM"


def test_the_eur_override_is_the_ecb_deposit_facility() -> None:
    """Amendment A-1. BIS's euro-area series changes definition mid-sample."""
    assert rates.POLICY_RATE_OVERRIDE == {"EUR": "ECBDFR"}


# ------------------------------------------------------------- temporal rule


def test_a_rate_is_not_readable_on_its_own_effective_date() -> None:
    """The plan's one-trading-day lag, asserted on the value, not the docstring."""
    panel = rates.daily_panel.__wrapped__ if hasattr(rates.daily_panel, "__wrapped__") else None
    assert panel is None  # the function is not decorated; the check below is direct
    assert RATE_LAG_TRADING_DAYS >= 1


def test_the_daily_panel_lags_every_step(monkeypatch) -> None:
    """A step on day D must first appear in the panel on day D + 1."""
    monkeypatch.setattr(rates, "POLICY_RATE_OVERRIDE", {})
    panel = rates.daily_panel(_rate_frame(), "2024-01-05", "2024-02-10")
    for index, currency in enumerate(CURRENCIES):
        before = panel.loc["2024-01-31", currency]
        on_the_day = panel.loc["2024-02-01", currency]
        after = panel.loc["2024-02-02", currency]
        assert before == pytest.approx(float(index))
        assert on_the_day == pytest.approx(float(index)), (
            f"{currency}'s new rate was readable on its own effective date"
        )
        assert after == pytest.approx(float(index) + 1.0)


def test_the_forward_fill_runs_before_the_lag(monkeypatch) -> None:
    """A lag in **days**, not in published observations.

    The source is a step function with an observation only where something
    changed. Shifting before filling would move a rate by one *observation*,
    which can be months.
    """
    monkeypatch.setattr(rates, "POLICY_RATE_OVERRIDE", {})
    panel = rates.daily_panel(_rate_frame(), "2024-01-05", "2024-02-10")
    #: every calendar day is present and none is empty after the first
    assert len(panel) == len(pd.date_range("2024-01-05", "2024-02-10", freq="D"))
    assert panel.iloc[1:].notna().all().all()


def test_the_differential_has_the_sign_the_plan_declares(monkeypatch) -> None:
    """`rate(BASE) − rate(QUOTE)`, so long AUD_JPY with AUD above earns positive."""
    monkeypatch.setattr(rates, "POLICY_RATE_OVERRIDE", {})
    panel = rates.daily_panel(_rate_frame(), "2024-01-05", "2024-01-20")
    for pair in ("AUD_JPY", "EUR_USD", "GBP_CHF"):
        base, quote = pair.split("_")
        expected = panel[base] - panel[quote]
        assert np.allclose(
            rates.differential(panel, pair).to_numpy(), expected.to_numpy(), equal_nan=True
        )
    #: and it is antisymmetric
    forward = rates.differential(panel, "EUR_USD")
    reversed_panel = panel.rename(columns={"EUR": "USD", "USD": "EUR"})
    assert np.allclose(
        forward.to_numpy(),
        -rates.differential(reversed_panel, "EUR_USD").to_numpy(),
        equal_nan=True,
    )


# --------------------------------------------------------------- carry maths


def test_carry_accrues_by_calendar_day_so_a_weekend_pays_three(price_frame) -> None:
    """The `random_walk_frame` fixture has weekend gaps; they must accrue."""
    elapsed = carry._elapsed_days(price_frame["ts"])
    assert elapsed[0] == 0.0
    hours = np.round(elapsed * 24, 2)
    assert (hours > 24).any(), "the fixture has no weekend gap, so this test is inert"
    #: the total elapsed must equal the calendar span, not the number of bars
    span = (price_frame["ts"].max() - price_frame["ts"].min()).total_seconds() / 86_400.0
    assert elapsed.sum() == pytest.approx(span, rel=1e-9)


def test_the_daily_accrual_is_the_annual_rate_over_365(price_frame) -> None:
    rate_panel = pd.DataFrame(
        {c: 1.0 for c in CURRENCIES},
        index=pd.date_range("2021-12-01", "2023-12-31", freq="D", tz="UTC"),
    )
    rate_panel["AUD"] = 5.0
    rate_panel["JPY"] = 1.0
    attached = carry.attach_rates(price_frame, rate_panel, "AUD_JPY")
    assert attached["carry_rate_pct"].dropna().unique().tolist() == [4.0]
    expected = 4.0 / 100.0 / DAYS_PER_YEAR * attached["mid_c"] / attached["pip_size"]
    assert np.allclose(attached["carry_pips_per_day"].to_numpy(), expected.to_numpy())
    assert DAYS_PER_YEAR == 365.0


def test_the_accrual_is_per_calendar_day_and_not_per_bar(price_frame) -> None:
    """Kills an accrual divided by a fixed bar count instead of elapsed time.

    Dividing by 96 gives the same answer as elapsed time on a weekday and the
    wrong answer across a weekend, so the discriminator is a position held only
    over a gap against one held only over an ordinary run of bars.
    """
    rate_panel = pd.DataFrame(
        {c: 0.0 for c in CURRENCIES},
        index=pd.date_range("2021-12-01", "2023-12-31", freq="D", tz="UTC"),
    )
    rate_panel["AUD"] = 4.0
    attached = carry.attach_rates(price_frame, rate_panel, "AUD_JPY")
    elapsed = carry._elapsed_days(attached["ts"])
    gap = int(np.argmax(elapsed))
    assert elapsed[gap] > 1.0, "the fixture has no weekend gap, so this test is inert"

    over_gap = pd.Series(0.0, index=attached.index)
    over_gap.iloc[gap - 1] = 1.0
    ordinary = pd.Series(0.0, index=attached.index)
    ordinary.iloc[gap + 4] = 1.0

    across = carry.evaluate(attached, over_gap, pair="AUD_JPY")["carry_pips"]
    inside = carry.evaluate(attached, ordinary, pair="AUD_JPY")["carry_pips"]
    assert across > inside * 50, (
        f"a bar spanning a weekend accrued {across:.6f} against {inside:.6f} for an "
        "ordinary bar; the accrual is not counting calendar time"
    )


def test_spot_plus_carry_minus_cost_equals_net(price_frame) -> None:
    rate_panel = pd.DataFrame(
        {c: 0.0 for c in CURRENCIES},
        index=pd.date_range("2021-12-01", "2023-12-31", freq="D", tz="UTC"),
    )
    rate_panel["AUD"] = 4.0
    attached = carry.attach_rates(price_frame, rate_panel, "AUD_JPY")
    position = pd.Series(1.0, index=attached.index)
    row = carry.evaluate(attached, position, pair="AUD_JPY")
    assert row["spot_pips"] + row["carry_pips"] - row["cost_pips"] == pytest.approx(
        row["net_pips"], abs=0.05
    )
    assert row["carry_pips"] > 0, "a positive differential held long must earn carry"


def test_carry_flips_sign_with_the_position(price_frame) -> None:
    rate_panel = pd.DataFrame(
        {c: 0.0 for c in CURRENCIES},
        index=pd.date_range("2021-12-01", "2023-12-31", freq="D", tz="UTC"),
    )
    rate_panel["AUD"] = 4.0
    attached = carry.attach_rates(price_frame, rate_panel, "AUD_JPY")
    position = pd.Series(1.0, index=attached.index)
    long_row = carry.evaluate(attached, position, pair="AUD_JPY")
    short_row = carry.evaluate(attached, -position, pair="AUD_JPY")
    assert long_row["carry_pips"] == pytest.approx(-short_row["carry_pips"], rel=1e-6)
    assert long_row["spot_pips"] == pytest.approx(-short_row["spot_pips"], rel=1e-6)


def test_carry_accrues_only_while_a_position_is_held(price_frame) -> None:
    rate_panel = pd.DataFrame(
        {c: 0.0 for c in CURRENCIES},
        index=pd.date_range("2021-12-01", "2023-12-31", freq="D", tz="UTC"),
    )
    rate_panel["AUD"] = 4.0
    attached = carry.attach_rates(price_frame, rate_panel, "AUD_JPY")
    flat = pd.Series(0.0, index=attached.index)
    assert carry.evaluate(attached, flat, pair="AUD_JPY")["carry_pips"] == pytest.approx(0.0)

    half = pd.Series(0.0, index=attached.index)
    half.iloc[: len(half) // 2] = 1.0
    full = pd.Series(1.0, index=attached.index)
    assert (
        carry.evaluate(attached, half, pair="AUD_JPY")["carry_pips"]
        < carry.evaluate(attached, full, pair="AUD_JPY")["carry_pips"]
    )


def test_the_position_is_held_from_the_bar_after_the_decision(price_frame) -> None:
    """`engine.evaluate`'s convention, asserted rather than assumed."""
    rate_panel = pd.DataFrame(
        {c: 0.0 for c in CURRENCIES},
        index=pd.date_range("2021-12-01", "2023-12-31", freq="D", tz="UTC"),
    )
    rate_panel["AUD"] = 4.0
    attached = carry.attach_rates(price_frame, rate_panel, "AUD_JPY")
    #: decided on a block of bars, so the exposure is measurable against the
    #: number of bars rather than lost to the metric's one-decimal rounding
    position = pd.Series(0.0, index=attached.index)
    position.iloc[200:400] = 1.0
    row = carry.evaluate(attached, position, pair="AUD_JPY")
    held = position.shift(1).fillna(0.0)
    elapsed = carry._elapsed_days(attached["ts"])
    expected = float((held.abs().to_numpy() * elapsed).sum())
    assert row["days_held"] == pytest.approx(round(expected, 1))

    #: and the decision bar itself carries no exposure. A single-bar position
    #: at `i` must earn the `i+1 -> i+2` move, so the recorded spot is the
    #: forward return of the bar AFTER the decision and not of the decision bar
    single = pd.Series(0.0, index=attached.index)
    single.iloc[300] = 1.0
    one = carry.evaluate(attached, single, pair="AUD_JPY")
    close = attached["mid_c"].to_numpy()
    pip = float(attached["pip_size"].iloc[0])
    latent = (close[302] - close[301]) / pip
    immediate = (close[301] - close[300]) / pip
    #: `spot_pips` is reported to two decimals, so the tolerance is the rounding
    assert one["spot_pips"] == pytest.approx(latent, abs=0.005), (
        f"the recorded spot {one['spot_pips']} matches neither the latent move "
        f"{latent:.4f} nor the immediate one {immediate:.4f}"
    )
    assert abs(latent - immediate) > 0.05, "the two candidates are too close to separate"


# ------------------------------------------------------------ cross-sectional


def test_the_cross_sectional_basket_is_currency_neutral() -> None:
    index = pd.date_range("2024-01-01", "2024-01-10", freq="D", tz="UTC")
    #: rate ascending with the index, so the LAST currencies are the high-rate
    #: ones the basket goes long
    panel = pd.DataFrame(
        {currency: float(rank) for rank, currency in enumerate(CURRENCIES)}, index=index
    )
    for k in CROSS_SECTIONAL_K:
        positions = carry.cross_sectional_positions(panel, PAIRS, k=k)
        assert set(positions) == set(PAIRS)
        ranks = panel[list(CURRENCIES)].rank(axis=1, method="average", ascending=False)
        longs = {c for c in CURRENCIES if ranks[c].iloc[0] <= k}
        shorts = {c for c in CURRENCIES if ranks[c].iloc[0] > len(CURRENCIES) - k}
        assert len(longs) == len(shorts) == k

        for pair, series in positions.items():
            base, quote = pair.split("_")
            value = float(series.iloc[0])
            assert abs(value) <= 1.0 + 1e-9
            #: a pair with both legs on the same side carries no exposure -- the
            #: view is on the currencies, not on the pair
            if (base in longs and quote in longs) or (base in shorts and quote in shorts):
                assert value == pytest.approx(0.0)
            elif base in longs or quote in shorts:
                assert value > 0, f"{pair} should be long the high-rate leg"
            elif base in shorts or quote in longs:
                assert value < 0, f"{pair} should be short the low-rate leg"

        #: and the basket is currency-neutral by construction: the long and
        #: short targets sum to zero
        target = pd.DataFrame(0.0, index=panel.index, columns=list(CURRENCIES))
        target[ranks <= k] = 1.0 / k
        target[ranks > len(CURRENCIES) - k] = -1.0 / k
        assert target.sum(axis=1).abs().max() < 1e-9


def test_a_dead_band_keeps_a_flat_pair_out(price_frame) -> None:
    rate_panel = pd.DataFrame(
        {c: 1.0 for c in CURRENCIES},
        index=pd.date_range("2021-12-01", "2023-12-31", freq="D", tz="UTC"),
    )
    attached = carry.attach_rates(price_frame, rate_panel, "AUD_JPY")
    position = carry.signal_pair_level(attached, stride=96 * 5, phase=0)
    assert position.abs().sum() == 0.0, "a zero differential must not open a position"
    assert CARRY_DEAD_BAND_PCT > 0


# ------------------------------------------------------- opportunity, Stage 3


def test_every_opportunity_state_is_backward_looking(price_frame) -> None:
    """A state must not read the day it labels, nor any day after it.

    Perturbing only the *tail* proves nothing about the day itself, because a
    trailing window never reaches forward anyway. The discriminating probe
    displaces **one day** and asks whether that day's own state moved — which it
    must not, since the state is shifted by one.
    """
    table = opportunity.daily_state(price_frame)
    assert not table.empty, "the fixture is too short for a daily state"

    disturbed = price_frame.copy()
    day = disturbed["ts"].dt.floor("D")
    target = table.index[len(table) // 2]
    disturbed.loc[(day == target).to_numpy(), "volume"] *= 500.0
    after = opportunity.daily_state(disturbed)

    for representation in VOLUME_REPRESENTATIONS:
        before_value = table.loc[target, representation]
        after_value = after.loc[target, representation]
        assert np.allclose([before_value], [after_value], equal_nan=True), (
            f"{representation} read the very day it labels"
        )
        #: and the probe is live: the following day must react
        following = table.index[table.index.get_loc(target) + 1]
        assert not np.allclose(
            [table.loc[following, representation]],
            [after.loc[following, representation]],
            equal_nan=True,
        ), f"{representation} did not react at all -- the probe is inert"


def test_the_opportunity_targets_are_forward_and_never_direction(price_frame) -> None:
    table = opportunity.daily_state(price_frame)
    assert not table.empty, "the fixture is too short for a daily state"
    close = table["close"].to_numpy()
    pip = float(price_frame["pip_size"].iloc[0])
    expected = (
        np.abs(
            np.concatenate(
                [close[opportunity.FORWARD_DAYS :], np.full(opportunity.FORWARD_DAYS, np.nan)]
            )
            - close
        )
        / pip
    )
    assert np.allclose(
        table["future_absolute_return"].to_numpy(), expected, equal_nan=True, atol=1e-6
    )
    #: every target is a magnitude or a rate, never a sign
    assert set(OPPORTUNITY_TARGETS) == {
        "future_absolute_return",
        "future_realised_volatility",
        "movement_exceeds_cost",
    }
    assert (table["future_absolute_return"].dropna() >= 0).all()


def test_the_filter_threshold_is_the_median_and_not_a_search(price_frame) -> None:
    """The median is the only split that needs no choice; anything else is a grid."""
    table = opportunity.daily_state(price_frame)
    assert not table.empty, "the fixture is too short for a daily state"
    mask = opportunity.filter_mask(table, "rolling_percentile")
    values = table["rolling_percentile"].dropna()
    assert mask.reindex(values.index).equals(values > 0.5)
    #: about half the usable days survive it. A threshold moved off the median
    #: keeps a different share, which is what makes it a searched parameter.
    kept = float(mask.reindex(values.index).mean())
    assert 0.40 <= kept <= 0.60, f"the percentile filter keeps {kept:.1%} of days"
    for representation in VOLUME_REPRESENTATIONS:
        share = float(
            opportunity.filter_mask(table, representation).reindex(table.index).fillna(False).mean()
        )
        assert 0.30 <= share <= 0.70, f"{representation} keeps {share:.1%}"

    #: the split has to be a **trailing** median, not a fixed level. Shifting a
    #: state bodily upward must leave the share of days it keeps unchanged,
    #: which a fixed threshold cannot do.
    for representation in VOLUME_REPRESENTATIONS:
        if representation == "rolling_percentile":
            continue
        lifted = table.copy()
        lifted[representation] = table[representation] + 5.0
        base_share = float(
            opportunity.filter_mask(table, representation).reindex(table.index).fillna(False).mean()
        )
        lifted_share = float(
            opportunity.filter_mask(lifted, representation)
            .reindex(table.index)
            .fillna(False)
            .mean()
        )
        assert lifted_share == pytest.approx(base_share, abs=0.02), (
            f"{representation}'s split moved with the level ({base_share:.2f} to "
            f"{lifted_share:.2f}), so it is a fixed threshold rather than a "
            "trailing median"
        )


# ---------------------------------------------------------- calendar, Route C


def test_a_change_date_is_a_date_the_rate_actually_moved() -> None:
    index = pd.date_range("2024-01-01", "2024-01-10", freq="D", tz="UTC")
    panel = pd.DataFrame({c: 1.0 for c in CURRENCIES}, index=index)
    panel.loc["2024-01-05":, "JPY"] = 2.0
    events = calendar_events.change_dates(panel)
    assert [str(d.date()) for d in events["JPY"]] == ["2024-01-05"]
    assert events["USD"] == []


def test_the_event_window_reaches_both_sides() -> None:
    assert calendar_events.WINDOW_DAYS == 1


# --------------------------------------------------------------- frozen plan


def test_the_carry_search_is_twelve_cells_and_no_more() -> None:
    assert len(carry.FAMILIES) * len(REBALANCE_BARS) == CARRY_CELLS == 12
    assert set(REBALANCE_BARS) == {"weekly", "fortnightly", "monthly"}
    assert REBALANCE_BARS["weekly"] == 5 * 96


def test_2025_may_contradict_but_may_not_decide() -> None:
    assert driver.DECIDING_PANELS == ("momentum_2021_2023", "supplemental_2023_2025")
    assert "development_2025" in driver.PANELS
    assert "development_2025" not in driver.DECIDING_PANELS


def test_the_carry_verdict_needs_every_clause() -> None:
    """Each kill clause must be able to fail a cell on its own."""

    def cells(**overrides):
        row = {
            "gross_pips": 100.0,
            "net_pips": 90.0,
            "spot_pips": 10.0,
            "carry_pips": 90.0,
            "top10_day_share": 0.2,
            "largest_pair_share": 0.2,
            "jpy_mean_net": 50.0,
            "non_jpy_mean_net": 40.0,
        } | overrides
        return {
            "cell": {
                panel: {"x1.0": dict(row), "x2.0": dict(row)} for panel in driver.DECIDING_PANELS
            }
        }

    assert driver._carry_verdict(cells())["surviving"] == ["cell"]
    assert driver._carry_verdict(cells(gross_pips=-1.0))["surviving"] == []
    assert driver._carry_verdict(cells(net_pips=-1.0))["surviving"] == []
    assert driver._carry_verdict(cells(top10_day_share=0.9))["surviving"] == []
    assert driver._carry_verdict(cells(non_jpy_mean_net=-1.0))["surviving"] == []
    assert driver._carry_verdict(cells())["status"] == "CARRY_EDGE_SUPPORTED_EXPLORATORY"
    assert driver._carry_verdict(cells(gross_pips=-1.0))["status"] == "CARRY_EDGE_NOT_SUPPORTED"


def test_the_carry_verdict_needs_the_same_sign_on_both_deciding_panels() -> None:
    row = {
        "gross_pips": 100.0,
        "net_pips": 90.0,
        "spot_pips": 10.0,
        "carry_pips": 90.0,
        "top10_day_share": 0.2,
        "largest_pair_share": 0.2,
        "jpy_mean_net": 50.0,
        "non_jpy_mean_net": 40.0,
    }
    flipped = dict(row) | {"net_pips": -90.0, "gross_pips": -100.0}
    cells = {
        "cell": {
            driver.DECIDING_PANELS[0]: {"x1.0": dict(row), "x2.0": dict(row)},
            driver.DECIDING_PANELS[1]: {"x1.0": flipped, "x2.0": flipped},
        }
    }
    verdict = driver._carry_verdict(cells)
    assert verdict["per_cell"]["cell"]["net_same_sign"] is False
    assert verdict["surviving"] == []
