"""Tests for the replay, the populations and the substituted frontier.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Three claims carry the whole stage and each is pinned here.

**The substitution is a substitution.** Passing the quoted source back into the
recomputed frontier must reproduce the committed frontier exactly. If it does
not, then whatever the execution variant reports differs from the baseline for
reasons that include the refactor, and no ratio between them means anything.

**The populations are design-known and exhaustive.** Event and non-event have to
partition the tradable bars, or "non-event" is a second sample rather than a
complement — and rollover has to be out of the primary, or the one expensive
window of the day is quietly inside the headline.

**The gates are the ones the pre-registration named.** A cell passing on one
panel has not passed; the worse panel governs the band; and the event floor is
reported beside the count rather than folded into it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.research.clock_flow import MIN_EVENTS_PER_DECIDING_PANEL, frontier
from scripts.research.execution_frontier import band_for
from scripts.research.execution_frontier import refrontier as rf
from scripts.research.execution_frontier import replay as rp
from scripts.research.execution_frontier.fills import FillRule
from scripts.research.exploratory_m15 import PAIRS


def synthetic_pair(pair: str, days: int, seed: int) -> pd.DataFrame:
    """A pair with real bid/ask geometry, weekends removed, rollover flagged."""
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2023-01-02 00:00", tz="UTC")
    stamps: list[pd.Timestamp] = []
    for day in range(days):
        base = start + pd.Timedelta(days=day)
        if base.weekday() >= 5:
            continue
        stamps.extend(base + pd.Timedelta(minutes=15 * i) for i in range(96))
    n = len(stamps)
    pip = 0.01 if "JPY" in pair else 0.0001
    level = 140.0 if "JPY" in pair else 1.1
    mid_o = level + np.cumsum(rng.normal(0, 3 * pip, n))
    mid_c = mid_o + rng.normal(0, 2 * pip, n)
    spread = np.abs(rng.normal(1.2, 0.3, n)) + 0.4
    half = spread * pip / 2.0
    high = np.maximum(mid_o, mid_c) + np.abs(rng.normal(0, 4 * pip, n))
    low = np.minimum(mid_o, mid_c) - np.abs(rng.normal(0, 4 * pip, n))
    ts = pd.DatetimeIndex(stamps)
    minute = ts.hour * 60 + ts.minute
    return pd.DataFrame(
        {
            "ts": ts,
            "mid_o": mid_o,
            "mid_c": mid_c,
            "bid_o": mid_o - half,
            "bid_c": mid_c - half,
            "bid_h": high - half,
            "bid_l": low - half,
            "ask_o": mid_o + half,
            "ask_c": mid_c + half,
            "ask_h": high + half,
            "ask_l": low + half,
            "spread_close_pips": spread,
            "pip_size": np.full(n, pip),
            "rollover": (minute >= 21 * 60 + 55) & (minute <= 22 * 60 + 15),
            "session": np.where(ts.hour < 8, "asia", np.where(ts.hour < 16, "europe", "us")),
        }
    )


@pytest.fixture(scope="module")
def panel() -> dict[str, pd.DataFrame]:
    return {pair: synthetic_pair(pair, 40, 11 + i) for i, pair in enumerate(PAIRS)}


@pytest.fixture(scope="module")
def replayed(panel: dict[str, pd.DataFrame]) -> rp.PanelReplay:
    return rp.PanelReplay(panel, FillRule())


class TestTheSubstitutionIsASubstitution:
    def test_the_quoted_source_reproduces_the_frontiers_own_numbers(
        self, panel: dict[str, pd.DataFrame]
    ) -> None:
        """The whole comparison rests on this: same enumeration, same result."""
        arrays = frontier.PanelArrays(panel)
        expected = frontier.clock_designs(arrays)
        measured, dropped = rf.variant(panel, None)
        assert measured["clock"] == expected
        assert dropped == 0

    def test_the_execution_source_changes_the_cost_and_not_the_sample(
        self, panel: dict[str, pd.DataFrame]
    ) -> None:
        quoted, _ = rf.variant(panel, None)
        source = rf.MeasuredExecutionCosts(panel, FillRule(wait_bars=1))
        passive, _ = rf.variant(panel, source)
        key = next(iter(quoted["clock"]))
        assert passive["clock"][key]["n_events"] == quoted["clock"][key]["n_events"]
        assert (
            passive["clock"][key]["median_roundtrip_cost_bp"]
            != quoted["clock"][key]["median_roundtrip_cost_bp"]
        )

    def test_the_mde_does_not_move_when_only_the_cost_source_changes(
        self, panel: dict[str, pd.DataFrame]
    ) -> None:
        """The MDE is a property of the returns; if it moves, the sample moved."""
        quoted, _ = rf.variant(panel, None)
        source = rf.MeasuredExecutionCosts(panel, FillRule(wait_bars=1))
        passive, _ = rf.variant(panel, source)
        for key, cell in quoted["clock"].items():
            other = passive["clock"][key]
            if cell.get("n_events") and other.get("n_events") == cell["n_events"]:
                assert other["mde_bp"] == cell["mde_bp"]


class TestTheDrawnSidePicksItsOwnCost:
    """A passive leg is not symmetric, and the design statistics must use that.

    Mutation testing found this open: replacing the per-pair choice with the long
    leg's cost alone left every test green, because under `QuotedCosts` the two
    sides are equal and nothing else exercised an asymmetric source. An execution
    frontier priced entirely on one side of the book would have been invisible.
    """

    class Sided:
        def __init__(self, long_cost: float, short_cost: float) -> None:
            self.long_cost = long_cost
            self.short_cost = short_cost

        def entry(self, pair: str, index: int, direction: int) -> float:
            return self.long_cost if direction > 0 else self.short_cost

        def exit(self, pair: str, index: int, direction: int) -> float:
            return 0.0

    @staticmethod
    def mean_cost(panel: dict[str, pd.DataFrame], long_cost: float, short_cost: float) -> float:
        arrays = frontier.PanelArrays(
            panel, costs=TestTheDrawnSidePicksItsOwnCost.Sided(long_cost, short_cost)
        )
        cells = frontier.clock_designs(arrays)
        sized = [c for c in cells.values() if c.get("n_events")]
        assert sized
        return float(sized[0]["mean_roundtrip_cost_bp"])

    def test_an_asymmetric_source_lands_between_its_two_symmetric_bounds(
        self, panel: dict[str, pd.DataFrame]
    ) -> None:
        cheap = self.mean_cost(panel, 1.0, 1.0)
        dear = self.mean_cost(panel, 3.0, 3.0)
        mixed = self.mean_cost(panel, 1.0, 3.0)
        assert cheap < mixed < dear
        #: Random signs, so the book is half long and half short and the mean
        #: sits at the midpoint. Pricing every pair on the long side would return
        #: `cheap` exactly.
        assert mixed == pytest.approx((cheap + dear) / 2.0, rel=0.05)
        assert mixed != pytest.approx(cheap, rel=0.05)


class TestMeasuredExecutionCosts:
    def test_an_unmeasurable_bar_is_refused_rather_than_priced_at_zero(
        self, panel: dict[str, pd.DataFrame]
    ) -> None:
        source = rf.MeasuredExecutionCosts(panel, FillRule())
        pair = PAIRS[0]
        last = len(panel[pair]) - 1
        assert source.entry(pair, last, 1) is None
        assert source.dropped >= 1

    def test_an_index_outside_the_panel_is_refused(self, panel: dict[str, pd.DataFrame]) -> None:
        source = rf.MeasuredExecutionCosts(panel, FillRule())
        assert source.entry(PAIRS[0], 10**9, 1) is None
        assert source.entry(PAIRS[0], -1, 1) is None
        assert source.entry("NOT_A_PAIR", 5, 1) is None

    def test_the_two_directions_are_allowed_to_differ(self, panel: dict[str, pd.DataFrame]) -> None:
        """A resting buy and a resting sell face opposite sides of the same move.

        The quoted model cannot tell them apart; this one must be able to, or the
        substitution is priced as if a passive policy were symmetric.
        """
        source = rf.MeasuredExecutionCosts(panel, FillRule())
        pair = PAIRS[0]
        differ = [
            i
            for i in range(200, 400)
            if source.entry(pair, i, 1) is not None
            and source.entry(pair, i, 1) != source.entry(pair, i, -1)
        ]
        assert differ


class TestPopulations:
    def test_rollover_is_out_of_the_primary_and_reported_on_its_own(
        self, replayed: rp.PanelReplay
    ) -> None:
        pops = rp.populations(replayed)
        pair = PAIRS[0]
        flags = replayed.frames[pair]["rollover"].to_numpy(dtype=bool)
        assert flags.any()
        assert not (pops["all_bars"][0][pair] & flags).any()
        assert (pops["rollover_window"][0][pair] == flags).all()

    def test_event_and_non_event_partition_the_tradable_bars(
        self, replayed: rp.PanelReplay
    ) -> None:
        pops = rp.populations(replayed)
        pair = PAIRS[0]
        tradable = pops["all_bars"][0][pair]
        event = np.zeros(len(tradable), dtype=bool)
        for key, (entries, _) in pops.items():
            if key.split("__")[0] in {
                f"{m}_{s}"
                for m in ["london_fix", "ny_option_cut", "tokyo_fix", "london_open", "rollover"]
                for s in ("pre", "post")
            }:
                event |= entries[pair]
        #: Non-event is the complement, not a second sample: no tradable bar may
        #: be in both, and none may be in neither.
        non_event = pops["non_event"][0][pair]
        assert not (non_event & event).any()
        assert ((non_event | event) >= tradable).all()

    def test_the_clock_populations_come_from_the_frontiers_own_spans(
        self, replayed: rp.PanelReplay
    ) -> None:
        """Not a copy of the window logic — the same function."""
        pops = rp.populations(replayed)
        entries = pops["london_fix_pre"][0]
        found = False
        for day in replayed.arrays.days:
            spans, _ = frontier.clock_spans(replayed.arrays, "london_fix", "pre", day)
            for pair, (entry, _exit) in spans.items():
                assert entries[pair][entry]
                found = True
        assert found

    def test_a_month_end_population_is_a_subset_of_its_all_days_one(
        self, replayed: rp.PanelReplay
    ) -> None:
        pops = rp.populations(replayed)
        for pair in PAIRS:
            broad = pops["london_fix_pre"][0][pair]
            narrow = pops["london_fix_pre__month_end"][0][pair]
            assert not (narrow & ~broad).any()


class TestRoundTrip:
    def test_the_ratio_is_the_two_legs_and_the_band_follows_it(self) -> None:
        entry = {"n": 5, "baseline_leg_bp": 1.0, "passive_leg_bp": 0.4}
        exit_ = {"n": 5, "baseline_leg_bp": 1.0, "passive_leg_bp": 0.8}
        trip = rp._roundtrip(entry, exit_)
        assert trip["baseline_roundtrip_bp"] == 2.0
        assert trip["passive_roundtrip_bp"] == pytest.approx(1.2)
        assert trip["cost_ratio"] == pytest.approx(0.6)
        assert trip["band"] == band_for(0.6) == "strong"

    def test_an_empty_leg_produces_no_ratio_rather_than_a_zero(self) -> None:
        assert rp._roundtrip({"n": 0}, {"n": 5, "baseline_leg_bp": 1.0}) == {}


class TestConsistency:
    def test_the_worse_panel_governs_the_band(self) -> None:
        panels = {
            "a": {"populations": {"all_bars": {"roundtrip": {"cost_ratio": 0.55}}}},
            "b": {"populations": {"all_bars": {"roundtrip": {"cost_ratio": 0.90}}}},
        }
        record = rp._consistency(panels)["all_bars"]
        assert record["governing_band"] == "weak"
        assert record["panels_agree_on_band"] is False
        assert record["cost_ratio_spread"] == pytest.approx(0.35)

    def test_a_population_missing_from_one_panel_is_not_reported(self) -> None:
        panels = {
            "a": {"populations": {"all_bars": {"roundtrip": {"cost_ratio": 0.55}}}},
            "b": {"populations": {}},
        }
        assert rp._consistency(panels) == {}


class TestFeasibilityGates:
    @staticmethod
    def cell(*, decidable: bool, ir: float, n: int = 200) -> dict[str, object]:
        return {
            "n_events": n,
            "mde_bp": 1.0,
            "median_roundtrip_cost_bp": 2.0,
            "mean_roundtrip_cost_bp": 2.0,
            "hurdle_bp": 4.0,
            "headroom_bp": 3.0,
            "decidable": decidable,
            "economics": {"break_even_gross_ir": ir},
        }

    def test_a_cell_powered_on_one_panel_only_is_not_feasible(self) -> None:
        verdict = rf._verdicts(
            {
                "a": self.cell(decidable=True, ir=0.5),
                "b": self.cell(decidable=False, ir=0.5),
            }
        )
        assert verdict["powered_on_both_panels"] is False
        assert verdict["feasible"]["2.0"] is False

    def test_the_worst_panels_break_even_ratio_governs(self) -> None:
        verdict = rf._verdicts(
            {
                "a": self.cell(decidable=True, ir=0.4),
                "b": self.cell(decidable=True, ir=1.8),
            }
        )
        assert verdict["break_even_gross_ir_worst"] == 1.8
        assert verdict["feasible"]["1.0"] is False
        assert verdict["feasible"]["1.5"] is False
        assert verdict["feasible"]["2.0"] is True

    def test_the_event_floor_is_reported_and_not_applied(self) -> None:
        thin = rf._verdicts(
            {
                "a": self.cell(decidable=True, ir=0.4, n=MIN_EVENTS_PER_DECIDING_PANEL - 1),
                "b": self.cell(decidable=True, ir=0.4, n=MIN_EVENTS_PER_DECIDING_PANEL - 1),
            }
        )
        #: Thin, and still feasible on the three gates that were pre-registered.
        #: Folding a fourth gate in after the fact would be the same failure as
        #: loosening one.
        assert thin["clears_the_event_floor"] is False
        assert thin["feasible"]["1.0"] is True

    def test_the_reported_minimum_is_the_minimum(self) -> None:
        """Mutation testing found this open: `n_events_min` could be anything.

        It is the field a reader uses to see how thin a cell is, and the one the
        event floor is read against, so a number nobody checks is worse than no
        number.
        """
        verdict = rf._verdicts(
            {
                "a": self.cell(decidable=True, ir=0.4, n=310),
                "b": self.cell(decidable=True, ir=0.4, n=44),
            }
        )
        assert verdict["n_events_min"] == 44
        assert verdict["per_panel"]["a"]["n_events"] == 310
        assert verdict["clears_the_event_floor"] is False

    def test_a_cell_with_no_events_produces_no_verdict(self) -> None:
        assert rf._verdicts({"a": {"n_events": 0}, "b": self.cell(decidable=True, ir=0.4)}) == {}

    def test_a_cell_without_economics_produces_no_verdict(self) -> None:
        broken = self.cell(decidable=True, ir=0.4)
        broken["economics"] = {}
        assert rf._verdicts({"a": broken, "b": self.cell(decidable=True, ir=0.4)}) == {}

    def test_the_survivor_lists_and_the_counts_are_the_same_fact(self) -> None:
        variants = {
            "v": {
                "a": {
                    "calendar": {"1d": self.cell(decidable=True, ir=0.4)},
                    "clock": {"x_pre": self.cell(decidable=True, ir=1.7)},
                },
                "b": {
                    "calendar": {"1d": self.cell(decidable=True, ir=0.4)},
                    "clock": {"x_pre": self.cell(decidable=True, ir=1.7)},
                },
            }
        }
        block = rf.feasibility(variants)["v"]
        assert block["n_cells"] == 2
        assert block["n_feasible"]["1.0"] == len(block["feasible_cells"]["1.0"]) == 1
        assert block["n_feasible"]["2.0"] == len(block["feasible_cells"]["2.0"]) == 2
        assert block["feasible_cells"]["1.0"] == ["calendar:1d"]


class TestSensitivityIsDeclaredNotChosen:
    def test_every_declared_wait_is_reported(self, panel: dict[str, pd.DataFrame]) -> None:
        record = rp.sensitivity(panel)
        assert {row["wait_bars"] for row in record.values()} == {1, 2, 4, 8}

    def test_each_row_says_whether_it_fits_inside_a_clock_window(
        self, panel: dict[str, pd.DataFrame]
    ) -> None:
        record = rp.sensitivity(panel)
        fits = {
            row["wait_bars"]: row["fits_inside_a_four_bar_clock_window"] for row in record.values()
        }
        #: A four-bar window cannot host a four-bar wait, and the primary rule is
        #: a four-bar wait. That is a finding about the clock family, so it is
        #: carried in the artifact rather than left to a reader.
        assert fits[1] is True and fits[2] is True
        assert fits[4] is False and fits[8] is False
