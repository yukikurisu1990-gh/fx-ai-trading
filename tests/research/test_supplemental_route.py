"""The supplemental route's guard, and the guard it must not have weakened.

The point of these tests is not that the new reader works. It is that adding a
door did not remove a wall: `bars._assert_span` must still refuse exactly what it
refused before this branch existed, and neither route may reach the other's
window, the `EXPLORATORY_OOS_SLICE`, the dead window or the forward epoch.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.
"""

from __future__ import annotations

import inspect

import pytest

from scripts.research.exploratory_m15 import bars, supplemental, supplemental_replication

DEVELOPMENT = ("2025-04-25", "2025-12-28")
SUPPLEMENTAL = ("2023-04-26", "2025-04-24")
OOS_SLICE = ("2025-12-29", "2026-02-28")
DEAD_WINDOW = ("2026-03-01", "2026-04-24")
FORWARD_EPOCH = ("2026-04-25", "2026-05-29")


@pytest.mark.parametrize("span", [DEVELOPMENT, OOS_SLICE, DEAD_WINDOW, FORWARD_EPOCH])
def test_the_supplemental_guard_refuses_everything_outside_its_own_window(span):
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.assert_supplemental_span(*span)


def test_the_supplemental_guard_refuses_reaching_back_before_the_recorded_start():
    """The span was fixed from the manifest before any content was read."""
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.assert_supplemental_span("2023-04-25", "2025-04-24")


def test_the_supplemental_guard_admits_exactly_the_recorded_span():
    supplemental.assert_supplemental_span(*SUPPLEMENTAL)


def test_the_supplemental_guard_refuses_a_single_day_over_the_boundary():
    """`2025-04-25` is the development corpus. One day is the whole test."""
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.assert_supplemental_span("2023-04-26", "2025-04-25")


@pytest.mark.parametrize("span", [SUPPLEMENTAL, OOS_SLICE, DEAD_WINDOW, FORWARD_EPOCH])
def test_the_development_guard_still_refuses_what_it_refused_before(span):
    """Adding the supplemental route must not have relaxed this one."""
    with pytest.raises(bars.ExploratorySpanError):
        bars._assert_span(*span)


def test_the_development_guard_still_admits_the_development_corpus():
    bars._assert_span(*DEVELOPMENT)


def test_the_development_guard_takes_no_configurable_bounds():
    """A guard whose bounds are arguments with defaults is a default, not a guard."""
    source = inspect.getsource(bars._assert_span)
    assert bars.DEVELOPMENT_START_UTC == "2025-04-25"
    assert bars.FIRST_FORBIDDEN_UTC == "2025-12-29"
    assert "DEVELOPMENT_START_UTC" in source
    assert "FIRST_FORBIDDEN_UTC" in source


def test_the_two_routes_cannot_reach_each_others_window():
    with pytest.raises(bars.ExploratorySpanError):
        bars._assert_span(*SUPPLEMENTAL)
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.assert_supplemental_span(*DEVELOPMENT)


def test_the_supplemental_reader_gates_before_it_opens_a_file():
    """The guard runs first, so a refused span never touches the ten-year archive."""
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.read_m1("USD_JPY", start="2025-04-25", end="2025-12-28")
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.build_cache(["USD_JPY"], start="2023-04-26", end="2026-05-29")


def test_the_supplemental_reader_refuses_a_pair_outside_the_registered_twenty():
    with pytest.raises(ValueError):
        supplemental.source_path("EUR_TRY")


def test_the_frozen_candidate_is_read_from_round_2_not_restated():
    """If someone edits `round2.CENTRE`, this round's candidate moves with it.

    The candidate is frozen by that constant, committed at `c076988` and merged
    as `eab8f255`. Restating `480` here would let the two drift apart and let a
    later edit quietly re-point the replication at a different rule.
    """
    from scripts.research.exploratory_m15 import round2

    assert supplemental_replication.FROZEN["lookback"] == round2.CENTRE[0]
    assert supplemental_replication.FROZEN["hold"] == round2.CENTRE[1]
    assert round2.CENTRE == (480, 480)
    assert supplemental_replication.FROZEN["entry_z"] == 1.0


def test_the_recorded_span_matches_the_pre_read_plan():
    """The plan was committed before the reader existed; the constants follow it."""
    assert supplemental.SUPPLEMENTAL_START_UTC == "2023-04-26"
    assert supplemental.SUPPLEMENTAL_END_UTC == "2025-04-24"
    assert supplemental.FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC == bars.DEVELOPMENT_START_UTC
    assert supplemental.SCOPE == "SUPPLEMENTAL_EXPLORATORY_HISTORY"
    assert supplemental.OPERATION_READ == "track_a_supplemental_historical_read"
    assert supplemental.OPERATION_DERIVATION == "track_a_supplemental_m15_derivation"
