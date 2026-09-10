"""Tests for the conservative fill model.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Each of these fails on a plausible *optimistic* implementation, because every
unknown in an M15 bar resolves one way if you are careless and the careless
direction always makes execution look cheaper. So the cases here are the ones a
looser model would get wrong: a touch scored as a fill, a fill taken at the
bar's extreme rather than at the limit, an order filled in the bar whose close
decided it, an order resting through a weekend.

The round-trip identity in `TestBaselineIsTheOldConvention` is the join to
everything this programme measured before: if the baseline leg pair does not sum
to `spread + 0.5 pip`, then `C` is not the `C` the frontier used and no ratio
against it means anything.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.research.execution_frontier import (
    PENETRATION_PIPS,
    SUCCESS_BANDS,
    WAIT_BARS,
    band_for,
)
from scripts.research.execution_frontier.fills import (
    LONG,
    PAD_PIPS_PER_LEG,
    SHORT,
    FillRule,
    leg_costs,
    summarise,
)
from scripts.research.fxunits import HALF_SPREAD_ADDITION_PIPS, pips_to_bp

PIP = 0.0001


def frame(
    mids: list[float],
    *,
    spread_pips: float = 1.0,
    ask_low: list[float] | None = None,
    bid_high: list[float] | None = None,
    gap_after: int | None = None,
) -> pd.DataFrame:
    """A pair's bars with a flat spread, built so each field can be aimed.

    `ask_low` and `bid_high` default to the bar's own quote, which means "the
    market never traded away from where it opened" — no fill anywhere — so a test
    that wants a fill has to say so explicitly rather than inherit one.
    """
    n = len(mids)
    stamps = [
        pd.Timestamp("2023-01-03 00:00", tz="UTC") + pd.Timedelta(minutes=15 * i) for i in range(n)
    ]
    if gap_after is not None:
        stamps = [
            s + (pd.Timedelta(days=2) if i > gap_after else pd.Timedelta(0))
            for i, s in enumerate(stamps)
        ]
    half = spread_pips * PIP / 2.0
    bid = [m - half for m in mids]
    ask = [m + half for m in mids]
    return pd.DataFrame(
        {
            "ts": stamps,
            "mid_o": mids,
            "mid_c": mids,
            "bid_o": bid,
            "bid_c": bid,
            "ask_o": ask,
            "ask_c": ask,
            "ask_l": ask_low if ask_low is not None else ask,
            "bid_h": bid_high if bid_high is not None else bid,
            "pip_size": [PIP] * n,
            "spread_close_pips": [spread_pips] * n,
        }
    )


def flat(n: int, level: float = 1.1000) -> list[float]:
    return [level] * n


class TestBaselineIsTheOldConvention:
    def test_the_two_baseline_legs_sum_to_spread_plus_half_a_pip(self) -> None:
        """`C` here must be the `C` every earlier stage of the programme used."""
        bars = frame(flat(20), spread_pips=1.4)
        costs = leg_costs(bars, at="open")
        k = 2
        total = costs.long.baseline_bp[k] + costs.short.baseline_bp[k]
        expected = float(pips_to_bp(1.4 + HALF_SPREAD_ADDITION_PIPS, PIP, 1.1000))
        assert total == pytest.approx(expected, rel=1e-9)

    def test_a_market_order_leg_costs_the_half_spread_plus_its_share_of_the_pad(self) -> None:
        bars = frame(flat(20), spread_pips=2.0)
        costs = leg_costs(bars, at="open")
        expected = float(pips_to_bp(1.0 + PAD_PIPS_PER_LEG, PIP, 1.1000))
        assert costs.long.baseline_bp[3] == pytest.approx(expected, rel=1e-9)
        assert costs.short.baseline_bp[3] == pytest.approx(expected, rel=1e-9)

    def test_both_directions_pay_rather_than_earn(self) -> None:
        costs = leg_costs(frame(flat(20)), at="open")
        assert costs.long.baseline_bp[3] > 0
        assert costs.short.baseline_bp[3] > 0


class TestTouchIsNotAFill:
    def test_reaching_the_limit_exactly_is_not_a_fill(self) -> None:
        """The bar is consistent with a fill and with no fill, so: no fill."""
        mids = flat(20)
        limit = 1.1000 - 0.5 * PIP  # the bid, where a passive buy would rest
        bars = frame(mids, ask_low=[limit] * 20)
        costs = leg_costs(bars, at="open")
        assert not costs.long.filled[3]

    def test_one_tick_short_of_the_penetration_is_not_a_fill(self) -> None:
        limit = 1.1000 - 0.5 * PIP
        bars = frame(flat(20), ask_low=[limit - 0.999 * PENETRATION_PIPS * PIP] * 20)
        assert not leg_costs(bars, at="open").long.filled[3]

    def test_the_penetration_exactly_is_a_fill(self) -> None:
        limit = 1.1000 - 0.5 * PIP
        bars = frame(flat(20), ask_low=[limit - PENETRATION_PIPS * PIP] * 20)
        assert leg_costs(bars, at="open").long.filled[3]

    def test_the_same_boundary_holds_for_a_sell(self) -> None:
        limit = 1.1000 + 0.5 * PIP
        touch = frame(flat(20), bid_high=[limit] * 20)
        through = frame(flat(20), bid_high=[limit + PENETRATION_PIPS * PIP] * 20)
        assert not leg_costs(touch, at="open").short.filled[3]
        assert leg_costs(through, at="open").short.filled[3]

    def test_a_zero_penetration_rule_is_refused(self) -> None:
        with pytest.raises(ValueError, match="touch-only"):
            FillRule(penetration_pips=0.0)


class TestNoPriceImprovement:
    def test_a_fill_is_at_the_limit_however_far_the_bar_ran_through_it(self) -> None:
        limit = 1.1000 - 0.5 * PIP
        near = frame(flat(20), ask_low=[limit - 1.0 * PIP] * 20)
        far = frame(flat(20), ask_low=[limit - 50.0 * PIP] * 20)
        a = leg_costs(near, at="open").long.conditional_bp[3]
        b = leg_costs(far, at="open").long.conditional_bp[3]
        assert a == pytest.approx(b, rel=1e-12)
        #: And that price is the near touch: half a spread better than crossing,
        #: which is a credit against the decision mid.
        assert a == pytest.approx(float(pips_to_bp(-0.5, PIP, 1.1000)), rel=1e-9)


class TestNoFavourableLatency:
    def test_a_close_decision_cannot_fill_in_the_bar_that_decided_it(self) -> None:
        """Only bar 3 penetrates; a decision at bar 3's close must not use it."""
        low = list(flat(20) + np.array(0.0))
        ask_low = [1.1000 + 0.5 * PIP] * 20
        ask_low[3] = 1.1000 - 5 * PIP
        bars = frame(low, ask_low=ask_low)
        assert leg_costs(bars, at="open").long.filled[3]
        assert not leg_costs(bars, at="close").long.filled[3]

    def test_a_close_decision_fills_from_the_next_bar(self) -> None:
        ask_low = [1.1000 + 0.5 * PIP] * 20
        ask_low[4] = 1.1000 - 5 * PIP
        bars = frame(flat(20), ask_low=ask_low)
        costs = leg_costs(bars, at="close")
        assert costs.long.filled[3]
        assert costs.long.fill_offset[3] == 0

    def test_the_window_is_exactly_wait_bars_long(self) -> None:
        for offset, expected in ((WAIT_BARS - 1, True), (WAIT_BARS, False)):
            ask_low = [1.1000 + 0.5 * PIP] * 30
            ask_low[3 + offset] = 1.1000 - 5 * PIP
            costs = leg_costs(frame(flat(30), ask_low=ask_low), at="open")
            assert bool(costs.long.filled[3]) is expected


class TestNoRestingAcrossAGap:
    def test_a_window_spanning_a_weekend_is_unmeasurable(self) -> None:
        bars = frame(flat(20), gap_after=5)
        costs = leg_costs(bars, at="open")
        #: Decisions whose window has to cross the gap are dropped, not scored.
        assert not costs.measurable[3]
        assert not costs.measurable[5]
        assert costs.measurable[2] or costs.measurable[1]
        assert costs.measurable[10]

    def test_an_unmeasurable_bar_carries_no_number(self) -> None:
        costs = leg_costs(frame(flat(20), gap_after=5), at="open")
        assert np.isnan(costs.long.baseline_bp[4])
        assert np.isnan(costs.long.passive_bp[4])
        assert not costs.long.filled[4]

    def test_the_tail_of_the_panel_is_unmeasurable(self) -> None:
        costs = leg_costs(frame(flat(20)), at="open")
        assert not costs.measurable[-1]
        assert costs.measurable[0]


class TestCrossingWhenUnfilled:
    def test_p2_crosses_and_so_costs_the_spread_when_nothing_fills(self) -> None:
        bars = frame(flat(20), spread_pips=1.2)
        costs = leg_costs(bars, at="open")
        assert not costs.long.filled[3]
        #: A flat market: the crossing bar quotes what the decision bar did, so
        #: P2 lands exactly on the baseline. Any *cheaper* would be a fill this
        #: model was not entitled to grant.
        assert costs.long.passive_bp[3] == pytest.approx(costs.long.baseline_bp[3], rel=1e-9)

    def test_p2_pays_the_drift_when_the_market_ran_away(self) -> None:
        """The half the passive policy never fills is the half that ran away."""
        mids = [1.1000 + i * 2 * PIP for i in range(20)]
        bars = frame(mids)
        costs = leg_costs(bars, at="open")
        assert not costs.long.filled[3]
        assert costs.long.passive_bp[3] > costs.long.baseline_bp[3]

    def test_p1_is_nan_where_it_never_filled(self) -> None:
        costs = leg_costs(frame(flat(20)), at="open")
        assert np.isnan(costs.long.conditional_bp[3])


class TestAdverseSelection:
    def test_a_fill_buys_cheaper_and_still_holds_a_position_moving_against_it(self) -> None:
        """Both halves are true at once, and a summary must not report only one."""
        mids = [1.1000 - i * 2 * PIP for i in range(30)]
        bars = frame(mids, ask_low=[m - 2 * PIP for m in mids])
        costs = leg_costs(bars, at="open")
        assert costs.long.filled[3]
        #: The position is under water an hour later...
        assert costs.long.drift_passive_bp[3] < 0
        #: ...and yet the entry was better than crossing would have been, because
        #: in a market that falls on every bar there is no selection at all: every
        #: passive order fills. Reading this gap as adverse selection is what an
        #: earlier version of this test did, and it was wrong.
        assert costs.long.drift_passive_bp[3] > costs.long.drift_baseline_bp[3]

    def test_selection_is_measured_between_populations_not_between_prices(self) -> None:
        """Fills happen on the dips, and the dips are the bars that keep falling."""
        n = 60
        mids = flat(n)
        ask_low = [1.1000 + 0.5 * PIP] * n  # nothing reaches a resting bid...
        for shock in (10, 25, 40):
            ask_low[shock] = 1.1000 - 5 * PIP  # ...except on three bars
            for step in range(1, 8):  # after which the market keeps going down
                mids[shock + step] = 1.1000 - 4 * PIP
        bars = frame(mids, ask_low=ask_low)
        record = summarise(leg_costs(bars, at="open"), np.ones(n, dtype=bool))
        assert 0.0 < record["fill_rate"] < 1.0
        #: Same execution model on both sides; only the population differs.
        assert record["drift_baseline_on_filled_bp"] < record["drift_baseline_bp"]
        assert record["adverse_selection_bp"] > 0

    def test_a_market_with_no_selection_reports_none(self) -> None:
        limit_buy = 1.1000 - 0.5 * PIP
        limit_sell = 1.1000 + 0.5 * PIP
        bars = frame(
            flat(40),
            ask_low=[limit_buy - 2 * PIP] * 40,
            bid_high=[limit_sell + 2 * PIP] * 40,
        )
        record = summarise(leg_costs(bars, at="open"), np.ones(40, dtype=bool))
        assert record["fill_rate"] == 1.0
        assert record["adverse_selection_bp"] == 0.0


class TestSummary:
    def test_the_fill_rate_and_its_complement_are_the_same_fact(self) -> None:
        bars = frame(flat(40))
        record = summarise(leg_costs(bars, at="open"), np.ones(len(bars), dtype=bool))
        assert record["fill_rate"] + record["missed_rate"] == pytest.approx(1.0)
        assert record["fill_rate"] == 0.0

    def test_capture_is_what_the_policy_saved_against_crossing(self) -> None:
        limit_buy = 1.1000 - 0.5 * PIP
        limit_sell = 1.1000 + 0.5 * PIP
        bars = frame(
            flat(40),
            ask_low=[limit_buy - 2 * PIP] * 40,
            bid_high=[limit_sell + 2 * PIP] * 40,
        )
        record = summarise(leg_costs(bars, at="open"), np.ones(len(bars), dtype=bool))
        assert record["fill_rate"] == 1.0
        #: Everything fills at the touch, so the policy saves the whole quoted
        #: leg: half the spread plus the pad it no longer pays.
        assert record["capture_share_of_quoted"] == pytest.approx(
            1.0 + 0.5 / (0.5 + PAD_PIPS_PER_LEG), abs=1e-4
        )

    def test_an_empty_selection_reports_nothing_rather_than_a_zero(self) -> None:
        bars = frame(flat(20))
        assert summarise(leg_costs(bars, at="open"), np.zeros(len(bars), dtype=bool)) == {"n": 0}


class TestBands:
    def test_each_boundary_falls_in_the_band_the_prereg_names(self) -> None:
        assert band_for(0.60) == "strong"
        assert band_for(0.6001) == "material"
        assert band_for(0.70) == "material"
        assert band_for(0.7001) == "modest"
        assert band_for(0.85) == "modest"
        assert band_for(0.8501) == "weak"

    def test_the_thresholds_live_in_one_place(self) -> None:
        assert [name for name, _ in SUCCESS_BANDS] == ["strong", "material", "modest"]
        assert [ceiling for _, ceiling in SUCCESS_BANDS] == [0.60, 0.70, 0.85]

    def test_no_improvement_at_all_is_weak(self) -> None:
        assert band_for(1.0) == "weak"
        assert band_for(1.4) == "weak"


class TestDirectionGuard:
    def test_an_unknown_direction_is_refused(self) -> None:
        costs = leg_costs(frame(flat(20)), at="open")
        with pytest.raises(ValueError, match="direction must be"):
            costs.for_direction(0)
        assert costs.for_direction(LONG) is costs.long
        assert costs.for_direction(SHORT) is costs.short

    def test_an_unknown_decision_point_is_refused(self) -> None:
        with pytest.raises(ValueError, match="decision point"):
            leg_costs(frame(flat(20)), at="midpoint")
