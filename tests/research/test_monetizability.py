"""The monetizability package — its data boundary, its nulls and its bounds.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Written to the standard the Round B′ review roles set: everything here asserts on
**behaviour**, never on source text or on a docstring, and the boundary tests
probe the guard rather than reading the constant beside it.

Two properties carry most of the weight.

* **The volume reader may not widen a span.** It exists because one field was
  authorised over three already-seen spans, and the failure mode that matters is
  it reaching a fourth. It calls the routes' own guards, so these tests are also
  a check that those guards are still the thing standing in the way.
* **B-3 must be neither inert nor credulous.** It has to return zero on a random
  walk and something on a real mean-reverting process, because the whole economic
  gate is read off it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from scripts.research.exploratory_m15 import MalformedUtcDateError
from scripts.research.exploratory_m15 import volume as volume_reader
from scripts.research.exploratory_m15.bars import ExploratorySpanError
from scripts.research.exploratory_m15.momentum import MomentumSpanError
from scripts.research.exploratory_m15.supplemental import SupplementalSpanError
from scripts.research.monetizability import (
    EXCURSION_SIGMAS,
    NULL_DRAWS,
    ORACLE_NET_PER_EVENT_FLOOR_IN_COSTS,
    PRIMARY_STATISTIC,
    SEED,
    STUDENTIZED_FLOOR,
    TAIL_TRIM_DAYS,
    VOLUME_REDUNDANCY_R2,
    driver,
    geometry,
    oracle,
)
from scripts.research.round_b_prime import nulls, retrace

#: every way a span may be refused. Named rather than caught as `Exception`, so a
#: `KeyError` or a `FileNotFoundError` cannot be mistaken for a guard firing.
REFUSALS = (
    ExploratorySpanError,
    MomentumSpanError,
    SupplementalSpanError,
    MalformedUtcDateError,
    volume_reader.VolumeSpanError,
)


@pytest.fixture(scope="module")
def walk() -> pd.DataFrame:
    frame = nulls.random_walk_frame(20_000, np.random.default_rng(5))
    frame["roundtrip_cost"] = 2.5
    return frame


# --------------------------------------------------------------- data boundary


def test_the_volume_reader_admits_exactly_the_three_seen_spans() -> None:
    """Each panel is admitted by its own route, and by no other."""
    assert set(volume_reader.ROUTES) == {
        "momentum_2021_2023",
        "supplemental_2023_2025",
        "development_2025",
    }
    for panel, route in volume_reader.ROUTES.items():
        route.guard(route.start, route.end)
        for other, elsewhere in volume_reader.ROUTES.items():
            if other == panel:
                continue
            with pytest.raises(REFUSALS):
                route.guard(elsewhere.start, elsewhere.end)


@pytest.mark.parametrize(
    ("panel", "start", "end"),
    [
        #: the fresh pool, which is never readable
        ("momentum_2021_2023", "2016-06-02", "2021-04-25"),
        #: one day past either edge of each span
        ("momentum_2021_2023", "2021-04-25", "2023-04-25"),
        ("momentum_2021_2023", "2021-04-26", "2023-04-26"),
        ("supplemental_2023_2025", "2023-04-25", "2025-04-24"),
        ("supplemental_2023_2025", "2023-04-26", "2025-04-25"),
        ("development_2025", "2025-04-24", "2025-12-28"),
        #: the historical OOS slice and beyond
        ("development_2025", "2025-04-25", "2025-12-29"),
        ("development_2025", "2025-04-25", "2026-06-01"),
        #: a malformed bound, which sorts below a well-formed one as a string
        ("development_2025", "2025", "2025-12-28"),
        ("development_2025", "2025-04-25", "2025-12-2"),
    ],
)
def test_the_volume_reader_refuses_every_span_it_was_not_given(
    panel: str, start: str, end: str
) -> None:
    """No overreach on either edge, and no truncated bound, reaches a file."""
    with pytest.raises(REFUSALS):
        volume_reader.read_m1_volume(panel, "EUR_USD", start=start, end=end)


def test_the_volume_reader_refuses_an_unknown_panel_and_an_unknown_pair() -> None:
    for panel in ("fresh_pool", "historical_oos", "forward_epoch", ""):
        with pytest.raises(volume_reader.VolumeSpanError):
            volume_reader.read_m1_volume(panel, "EUR_USD")
    for pair in ("XAU_USD", "BTC_USD", "eur_usd"):
        with pytest.raises(volume_reader.VolumeSpanError):
            volume_reader.read_m1_volume("development_2025", pair)


def test_the_volume_reader_uses_the_routes_own_guards(monkeypatch) -> None:
    """Not a copy of a bound — the guard object itself.

    If the reader had its own bounds, hardening a route would stop protecting
    this path. Replacing the route's guard with one that refuses everything has
    to stop the reader.
    """

    def refuse(*_args, **_kwargs):
        raise RuntimeError("the route's guard was consulted")

    for panel, route in volume_reader.ROUTES.items():
        monkeypatch.setitem(volume_reader.ROUTES, panel, route._replace(guard=refuse))
        with pytest.raises(RuntimeError, match="the route's guard was consulted"):
            volume_reader.read_m1_volume(panel, "EUR_USD")
        monkeypatch.setitem(volume_reader.ROUTES, panel, route)


def test_retained_rows_are_checked_against_the_span_not_only_the_scan() -> None:
    """The scan's `break` trusts the file's ordering; this does not."""
    route = volume_reader.ROUTES["development_2025"]
    inside = pd.DataFrame({"ts": pd.to_datetime(["2025-06-01T00:00:00Z"], utc=True)})
    volume_reader.assert_rows_in_span(inside, "development_2025")
    for stamp in ("2025-04-24T23:45:00Z", "2025-12-29T00:00:00Z", "2021-01-01T00:00:00Z"):
        outside = pd.DataFrame({"ts": pd.to_datetime([stamp], utc=True)})
        with pytest.raises(volume_reader.VolumeSpanError):
            volume_reader.assert_rows_in_span(outside, "development_2025")
    assert route.start == "2025-04-25"


def test_the_m15_volume_aggregate_is_a_sum_over_the_committed_grid() -> None:
    stamps = pd.date_range("2025-06-02", periods=45, freq="1min", tz="UTC")
    m1 = pd.DataFrame({"ts": stamps, "volume": pd.Series(np.arange(45), dtype="Float64")})
    bars = volume_reader.to_m15_volume(m1)
    assert len(bars) == 3
    assert bars["volume"].tolist() == [sum(range(15)), sum(range(15, 30)), sum(range(30, 45))]
    assert bars["volume_bars"].tolist() == [15, 15, 15]
    assert bars["volume_missing"].tolist() == [0, 0, 0]


def test_a_missing_volume_field_is_counted_rather_than_zeroed() -> None:
    stamps = pd.date_range("2025-06-02", periods=15, freq="1min", tz="UTC")
    volumes = pd.Series([10.0] * 14 + [None], dtype="Float64")
    bars = volume_reader.to_m15_volume(pd.DataFrame({"ts": stamps, "volume": volumes}))
    assert bars["volume_missing"].iloc[0] == 1
    assert bars["volume"].iloc[0] == 140.0


# ------------------------------------------------------------------ Stage 1A


def test_the_primary_is_the_sigma_level_statistic_not_the_fraction() -> None:
    """The whole point of Stage 1A: no excursion in the verdict's denominator."""
    assert PRIMARY_STATISTIC == "median_retrace_sigma"
    verdict = geometry.verdict(_geometry_input(+0.9, -9.0), _bloc_input(+0.9), _DECIDING)
    assert verdict["per_threshold"][2.0]["primary"] == "median_retrace_sigma"
    #: and the fraction is carried, so a reader can see both
    assert "secondary_fraction" in verdict["per_threshold"][2.0]


_DECIDING = ("momentum_2021_2023", "supplemental_2023_2025")


def _geometry_input(difference: float, studentized: float = 9.0, family_p: float = 0.005) -> dict:
    cell = {
        "real": {"anchors": 4000},
        "null": {
            PRIMARY_STATISTIC: {"real_minus_null": difference, "studentized": studentized},
            "median_retrace_sigma_excluding_top_10_days": {
                "real_minus_null": difference,
                "studentized": studentized,
            },
            "median_retrace_fraction": {"real_minus_null": difference, "studentized": studentized},
            "family_max": {"family_wise_p": family_p},
        },
    }
    return {panel: {str(k): cell for k in EXCURSION_SIGMAS} for panel in _DECIDING}


def _bloc_input(difference: float) -> dict:
    return {
        str(k): {
            panel: {
                "JPY": {"real_minus_null": difference},
                "non_JPY": {"real_minus_null": difference},
            }
            for panel in _DECIDING
        }
        for k in EXCURSION_SIGMAS
    }


def test_all_five_clauses_can_each_kill_a_threshold() -> None:
    """A clause that cannot fail is not a clause."""
    passing = geometry.verdict(_geometry_input(+0.9, 9.0), _bloc_input(+0.9), _DECIDING)
    assert passing["surviving_thresholds"] == list(EXCURSION_SIGMAS)
    assert passing["kill_condition_met"] is False

    #: clause 2 — studentized below the floor
    weak = geometry.verdict(
        _geometry_input(+0.9, STUDENTIZED_FLOOR - 0.1), _bloc_input(+0.9), _DECIDING
    )
    assert weak["surviving_thresholds"] == []

    #: clause 3 — the family-wise p
    wide = geometry.verdict(_geometry_input(+0.9, 9.0, family_p=0.20), _bloc_input(+0.9), _DECIDING)
    assert wide["surviving_thresholds"] == []

    #: clause 4 — the day trim reverses the sign
    trimmed = _geometry_input(+0.9, 9.0)
    for panel in trimmed:
        for cell in trimmed[panel].values():
            cell["null"]["median_retrace_sigma_excluding_top_10_days"] = {
                "real_minus_null": -0.4,
                "studentized": -3.0,
            }
    assert geometry.verdict(trimmed, _bloc_input(+0.9), _DECIDING)["surviving_thresholds"] == []

    #: clause 5 — one bloc carries the other sign
    split = _bloc_input(+0.9)
    for k in split:
        for panel in split[k]:
            split[k][panel]["JPY"] = {"real_minus_null": -0.5}
    assert (
        geometry.verdict(_geometry_input(+0.9, 9.0), split, _DECIDING)["surviving_thresholds"] == []
    )


def test_clause_1_requires_the_same_sign_on_both_deciding_panels() -> None:
    mixed = _geometry_input(+0.9, 9.0)
    mixed[_DECIDING[1]] = {
        str(k): {
            "real": {"anchors": 4000},
            "null": {
                PRIMARY_STATISTIC: {"real_minus_null": -0.9, "studentized": -9.0},
                "median_retrace_sigma_excluding_top_10_days": {
                    "real_minus_null": -0.9,
                    "studentized": -9.0,
                },
                "median_retrace_fraction": {"real_minus_null": -0.9, "studentized": -9.0},
                "family_max": {"family_wise_p": 0.005},
            },
        }
        for k in EXCURSION_SIGMAS
    }
    verdict = geometry.verdict(mixed, _bloc_input(+0.9), _DECIDING)
    assert verdict["per_threshold"][2.0]["clause_1_same_sign"] is False
    assert verdict["surviving_thresholds"] == []
    assert verdict["status"] == "RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST"


def test_the_sigma_level_day_trim_comes_out_of_the_same_null_loop(walk: pd.DataFrame) -> None:
    """Clause 4's statistic is produced by `summarise`, not by a second pass."""
    panel = {f"W{i}": nulls.random_walk_frame(15_000, np.random.default_rng(i)) for i in range(3)}
    summary, _ = retrace.panel_geometry(panel, 1.5)
    assert "median_retrace_sigma_excluding_top_10_days" in summary
    assert summary["median_retrace_sigma_excluding_top_10_days"] < summary["median_retrace_sigma"]
    result = geometry.against_null(panel, 1.5, draws=6, seed=SEED)
    assert "median_retrace_sigma_excluding_top_10_days" in result["null"]
    assert TAIL_TRIM_DAYS == 10


# ------------------------------------------------------------------ Stage 1B


def test_the_horizon_events_are_causal_and_non_overlapping(walk: pd.DataFrame) -> None:
    """A decision at `t` earns the `t+1 → t+1+q` move, and events do not overlap."""
    built = oracle.basis(walk)
    horizon = 12
    events = oracle.horizon_events(built, horizon=horizon, phase=0)
    assert events is not None
    assert np.all(np.diff(events["index"]) == horizon)

    #: perturbing the bar the decision is taken on must not change an earlier event
    disturbed = walk.copy()
    target = int(events["index"][40])
    close = disturbed["mid_c"].to_numpy().copy()
    close[target:] += 500 * float(disturbed["pip_size"].iloc[0])
    disturbed["mid_c"] = close
    for column in ("mid_o", "mid_h", "mid_l"):
        disturbed[column] = disturbed[column].to_numpy() + np.where(
            np.arange(len(disturbed)) >= target, 500 * float(disturbed["pip_size"].iloc[0]), 0.0
        )
    after = oracle.horizon_events(oracle.basis(disturbed), horizon=horizon, phase=0)
    assert np.allclose(events["gross"][:38], after["gross"][:38])


def test_the_bounds_are_ordered_as_their_definitions_require(walk: pd.DataFrame) -> None:
    """B-1 ≥ B-0, B-2 ≥ B-0, B-1 ≥ B-3 ≥ 0 — and **B-2 does not dominate B-1**.

    The last one is a property of the definitions and is easy to read the wrong
    way. B-2 picks the side perfectly but is still obliged to trade, so every
    event whose move is smaller than the spread costs it money; B-1 keeps a fixed
    side and may skip, so it never books a loss. Measured here: B-2 comes out
    *below* B-1 on a random walk at a 2.5 pip cost, and neither is the overall
    ceiling.
    """
    built = oracle.basis(walk)
    events = oracle.horizon_events(built, horizon=12, phase=0)
    row = oracle.bounds(built, events, trading_days=200, cost_multiplier=1.0)
    assert row["b1_net_per_event"] >= 0.0
    assert row["b1_net_per_event"] >= row["b0_net_per_event"] - 1e-9
    assert row["b2_net_per_event"] >= row["b0_net_per_event"] - 1e-9
    assert row["b1_net_per_event"] >= row["b3_net_per_event"] - 1e-9
    #: the non-domination, asserted so a later reading of B-2 as "the ceiling"
    #: fails here rather than in a report
    assert row["b2_net_per_event"] < row["b1_net_per_event"]


def test_a_higher_cost_never_improves_a_bound(walk: pd.DataFrame) -> None:
    built = oracle.basis(walk)
    events = oracle.horizon_events(built, horizon=12, phase=0)
    cheap = oracle.bounds(built, events, trading_days=200, cost_multiplier=1.0)
    dear = oracle.bounds(built, events, trading_days=200, cost_multiplier=2.0)
    assert dear["b0_net_per_event"] < cheap["b0_net_per_event"]
    assert dear["b1_net_per_event"] <= cheap["b1_net_per_event"] + 1e-9
    assert dear["b2_net_per_event"] < cheap["b2_net_per_event"]
    assert dear["median_cost"] == pytest.approx(2 * cheap["median_cost"])


def test_b3_is_silent_on_noise_and_speaks_on_a_real_structure() -> None:
    """The gate is read off B-3, so it must be neither inert nor credulous.

    Both halves matter. Zero on a walk is the right answer and is also what a
    broken selector returns; the Ornstein–Uhlenbeck control separates them.
    """
    noise = oracle.noise_reference(pairs=3, length=20_000, horizons=(48,), seed=SEED)
    walk_row = noise["bounds"]["horizon_48"]
    assert abs(walk_row["b3_net_per_event"]) <= 0.10 * walk_row["median_cost"]

    signal = oracle.signal_reference(pairs=3, length=20_000, horizons=(48,), seed=SEED)
    ou_row = signal["bounds"]["horizon_48"]
    assert ou_row["b0_net_per_event"] > 0, "the control has no edge to find"
    assert ou_row["b3_net_per_event"] > ou_row["median_cost"]
    assert ou_row["b3_selected"] > 0


def test_the_perfect_foresight_bounds_are_large_on_pure_noise() -> None:
    """The measurement behind amendment A-1, as a standing test.

    If B-1 ever stops clearing the frozen floor on a random walk, the amendment's
    justification has changed and the gate should be revisited rather than
    silently kept.
    """
    noise = oracle.noise_reference(pairs=3, length=20_000, horizons=(48,), seed=SEED)
    row = noise["bounds"]["horizon_48"]
    assert row["b1_net_per_event"] > ORACLE_NET_PER_EVENT_FLOOR_IN_COSTS * row["median_cost"]
    assert row["b0_net_per_event"] < 0


# -------------------------------------------------------------- the frozen plan


def test_the_frozen_constants_are_the_plans() -> None:
    assert EXCURSION_SIGMAS == (1.5, 2.0, 3.0)
    assert NULL_DRAWS >= 200
    assert STUDENTIZED_FLOOR == 2.0
    assert ORACLE_NET_PER_EVENT_FLOOR_IN_COSTS == 0.5
    assert VOLUME_REDUNDANCY_R2 == 0.80


def test_2025_may_contradict_but_may_not_decide() -> None:
    assert driver.DECIDING_PANELS == _DECIDING
    assert "development_2025" in driver.PANELS
    assert "development_2025" not in driver.DECIDING_PANELS


def test_the_economic_gate_reads_b3_and_not_the_foresight_bounds() -> None:
    """Amendment A-1: B-1 and B-2 are descriptive, B-3 decides."""

    def referenced(b3_excess: float, b1_excess: float) -> dict:
        return {
            panel: {
                "horizon_48": {
                    "real": {"median_cost": 2.5, "b3_top10_day_share": 0.2},
                    "null": {
                        "b1_net_per_event": {"real_minus_null": b1_excess},
                        "b3_net_per_event": {"real_minus_null": b3_excess},
                    },
                }
            }
            for panel in _DECIDING
        }

    #: a huge foresight excess with no selectable excess must not pass
    assert (
        driver._economic_gate(referenced(0.0, 50.0))["horizon_48"]["E1_excess_at_least_half_a_cost"]
        is False
    )
    #: and a selectable excess above the floor must
    assert (
        driver._economic_gate(referenced(2.0, 0.0))["horizon_48"]["E1_excess_at_least_half_a_cost"]
        is True
    )
    #: exactly at the floor is inside it
    assert (
        driver._economic_gate(referenced(1.25, 0.0))["horizon_48"]["E1_excess_at_least_half_a_cost"]
        is True
    )
    assert (
        driver._economic_gate(referenced(1.24, 0.0))["horizon_48"]["E1_excess_at_least_half_a_cost"]
        is False
    )


def test_a_tail_carried_result_fails_the_gate() -> None:
    def referenced(share: float) -> dict:
        return {
            panel: {
                "horizon_48": {
                    "real": {"median_cost": 2.5, "b3_top10_day_share": share},
                    "null": {"b3_net_per_event": {"real_minus_null": 5.0}},
                }
            }
            for panel in _DECIDING
        }

    assert driver._economic_gate(referenced(0.30))["horizon_48"]["E3_tail_share_below_ceiling"]
    assert not driver._economic_gate(referenced(0.70))["horizon_48"]["E3_tail_share_below_ceiling"]
