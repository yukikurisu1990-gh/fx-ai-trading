"""The supplemental route's guard, and the guard it must not have weakened.

The point of these tests is not that the new reader works. It is that adding a
door did not remove a wall: `bars._assert_span` must still refuse exactly what it
refused before this branch existed, and neither route may reach the other's
window, the `EXPLORATORY_OOS_SLICE`, the dead window or the forward epoch.

An independent audit measured the first version of this file at a 55% mutation
kill rate and named the survivors: the *scan* was pinned by nothing (deleting
either bound, or widening the stop sentinel, left the suite green), the
"bounds are not parameters" test asserted only that constant *names* appeared in
the source — which a mutant that made them keyword arguments *and used them*
passed — and nothing tested that a forbidden row could not arrive from a cached
frame. The sections below are named after those survivors.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.
"""

from __future__ import annotations

import inspect
import json

import pandas as pd
import pytest

from scripts.research.exploratory_m15 import (
    MalformedUtcDateError,
    bars,
    round2,
    supplemental,
    supplemental_replication,
)

DEVELOPMENT = ("2025-04-25", "2025-12-28")
SUPPLEMENTAL = ("2023-04-26", "2025-04-24")
OOS_SLICE = ("2025-12-29", "2026-02-28")
DEAD_WINDOW = ("2026-03-01", "2026-04-24")
FORWARD_EPOCH = ("2026-04-25", "2026-05-29")

#: Bounds that are not exact `YYYY-MM-DD`. Each sorts *below* a real date it
#: should sort above, which is how a truncated bound walks past a string
#: comparison.
MALFORMED = ("2025", "2025-", "2025-12-2", "2025-4-5", "20251229", "", "2025-13-01")


# --------------------------------------------------------------------------
# the guards
# --------------------------------------------------------------------------


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


@pytest.mark.parametrize("span", [("2025-06-01", "2025-05-01"), ("2024-01-01", "2023-01-01")])
def test_both_guards_still_refuse_an_empty_span(span):
    with pytest.raises(bars.ExploratorySpanError):
        bars._assert_span(*span)
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.assert_supplemental_span(*span)


def test_the_two_routes_cannot_reach_each_others_window():
    with pytest.raises(bars.ExploratorySpanError):
        bars._assert_span(*SUPPLEMENTAL)
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.assert_supplemental_span(*DEVELOPMENT)


def test_the_two_routes_partition_rather_than_leave_a_gap():
    """A day of slack either side and the partition becomes two opinions."""
    supplemental.assert_supplemental_span("2023-04-26", supplemental.SUPPLEMENTAL_END_UTC)
    bars._assert_span(supplemental.FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC, "2025-12-28")
    assert supplemental.FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC == bars.DEVELOPMENT_START_UTC
    gap = pd.Timestamp(supplemental.FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC) - pd.Timestamp(
        supplemental.SUPPLEMENTAL_END_UTC
    )
    assert gap == pd.Timedelta(days=1)


# --------------------------------------------------------------------------
# malformed bounds -- the audit's BLOCKER
# --------------------------------------------------------------------------


@pytest.mark.parametrize("end", MALFORMED)
def test_no_malformed_end_reaches_either_guard(end):
    """`end="2025"` passed both guards and then let OOS rows reach `json.loads`.

    `"2025" < "2025-04-25"` is True, so the supplemental upper bound admitted it;
    and the old scan sentinel `end + "T99"` sorted *above* `"2025-12-29T…"`
    because `-` (0x2D) precedes `T` (0x54), so the scan never broke. Under
    `HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN`, a decode is a read.
    """
    with pytest.raises((MalformedUtcDateError, supplemental.SupplementalSpanError)):
        supplemental.assert_supplemental_span("2023-04-26", end)
    with pytest.raises((MalformedUtcDateError, bars.ExploratorySpanError)):
        bars._assert_span("2025-04-25", end)


@pytest.mark.parametrize("start", MALFORMED)
def test_no_malformed_start_reaches_either_guard(start):
    with pytest.raises((MalformedUtcDateError, supplemental.SupplementalSpanError)):
        supplemental.assert_supplemental_span(start, "2025-04-24")
    with pytest.raises((MalformedUtcDateError, bars.ExploratorySpanError)):
        bars._assert_span(start, "2025-12-28")


@pytest.mark.parametrize("guard", [bars._assert_span, supplemental.assert_supplemental_span])
def test_a_guards_bounds_are_not_parameters(guard):
    """Bounds with defaults are a default, not a guard.

    Asserting that the constants' *names* appear in the source does not detect a
    mutant that adds them as keyword arguments and uses them — the audit built
    exactly that mutant and the earlier version of this test passed it. Pin the
    signature instead.
    """
    assert list(inspect.signature(guard).parameters) == ["start", "end"]


# --------------------------------------------------------------------------
# the scan -- what actually gets decoded
# --------------------------------------------------------------------------

ARCHIVE_DAYS = (
    "2016-06-02",  # before the supplemental span
    "2023-04-25",  # one day before it
    "2023-04-26",  # first authorised day
    "2024-06-15",  # inside
    "2025-04-24",  # last authorised day
    "2025-04-25",  # development corpus
    "2025-12-29",  # EXPLORATORY_OOS_SLICE
    "2026-03-01",  # dead window
    "2026-04-25",  # forward epoch
    "2026-05-29",  # end of archive
)
AUTHORISED = {"2023-04-26", "2024-06-15", "2025-04-24"}


def _write_archive(path, dates):
    """A miniature ten-year archive: one row per named date."""
    with path.open("w", encoding="utf-8") as handle:
        for day in dates:
            handle.write(
                json.dumps(
                    {
                        "time": f"{day}T00:00:00.000000000Z",
                        "bid_o": 1.0,
                        "bid_h": 1.0,
                        "bid_l": 1.0,
                        "bid_c": 1.0,
                        "ask_o": 1.1,
                        "ask_h": 1.1,
                        "ask_l": 1.1,
                        "ask_c": 1.1,
                    }
                )
                + "\n"
            )


def _spy_on_decodes(monkeypatch):
    decoded: list[str] = []
    real = json.loads

    def spy(line, *args, **kwargs):
        row = real(line, *args, **kwargs)
        decoded.append(row["time"][:10])
        return row

    monkeypatch.setattr(supplemental.json, "loads", spy)
    return decoded


@pytest.fixture
def spied_reader(tmp_path, monkeypatch):
    """The supplemental reader over a synthetic archive, recording every decode."""
    path = tmp_path / "candles_USD_JPY_M1_3650d_BA.jsonl"
    _write_archive(path, ARCHIVE_DAYS)
    monkeypatch.setattr(supplemental, "source_path", lambda pair: path)
    return _spy_on_decodes(monkeypatch)


def test_the_scan_decodes_only_authorised_days(spied_reader):
    """Not "returns" — **decodes**. Under the ruling those are the same act."""
    frame = supplemental.read_m1("USD_JPY")
    assert set(spied_reader) == AUTHORISED
    assert set(frame["ts"].dt.strftime("%Y-%m-%d")) == AUTHORISED


def test_the_scan_never_decodes_a_forbidden_day_even_when_unsorted(tmp_path, monkeypatch):
    """The two bounds decide what is decoded; the `break` is an optimisation.

    An archive out of order makes a reader that relies on ordering alone stop
    early or walk on. This one under-reads rather than over-reads.
    """
    path = tmp_path / "candles_USD_JPY_M1_3650d_BA.jsonl"
    _write_archive(path, tuple(reversed(ARCHIVE_DAYS)))
    monkeypatch.setattr(supplemental, "source_path", lambda pair: path)
    decoded = _spy_on_decodes(monkeypatch)
    supplemental.read_m1("USD_JPY")
    assert not set(decoded) - AUTHORISED


def test_a_narrower_request_narrows_the_scan(spied_reader):
    supplemental.read_m1("USD_JPY", start="2024-01-01", end="2024-12-31")
    assert set(spied_reader) == {"2024-06-15"}


def test_the_supplemental_reader_gates_before_it_opens_a_file():
    """The guard runs first, so a refused span never touches the ten-year archive."""
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.read_m1("USD_JPY", start="2025-04-25", end="2025-12-28")
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.build_cache(["USD_JPY"], start="2023-04-26", end="2026-05-29")


def test_the_supplemental_reader_refuses_a_pair_outside_the_registered_twenty():
    with pytest.raises(ValueError):
        supplemental.source_path("EUR_TRY")


# --------------------------------------------------------------------------
# rows, not just requests
# --------------------------------------------------------------------------


def _frame(days):
    return pd.DataFrame({"ts": pd.to_datetime([f"{d}T00:00:00Z" for d in days], utc=True)})


@pytest.mark.parametrize("day", ["2025-04-25", "2025-12-29", "2026-04-25", "2023-04-25"])
def test_a_cached_frame_carrying_a_forbidden_row_is_refused(day):
    """Both guards validate the request. Something has to validate the rows.

    A parquet written by an older build — or through the malformed-bound hole,
    before it was closed — was served by `load()` forever with no check.
    """
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.assert_rows_in_span(_frame(["2023-04-26", day]), pair="USD_JPY")


def test_a_cached_frame_inside_the_span_is_returned_unchanged():
    frame = _frame(["2023-04-26", "2024-06-15", "2025-04-24"])
    assert supplemental.assert_rows_in_span(frame, pair="USD_JPY") is frame


def test_an_empty_cached_frame_is_refused_rather_than_silently_accepted():
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.assert_rows_in_span(_frame([]), pair="USD_JPY")


def test_load_itself_refuses_a_forbidden_cached_parquet(tmp_path, monkeypatch):
    """That the validator exists is not the same as `load` calling it.

    A first pass tested `assert_rows_in_span` directly, and a mutant that dropped
    the call from `load` survived — the defect the validator was written for,
    passing the test written for the validator.
    """
    monkeypatch.setattr(supplemental, "CACHE_DIR", tmp_path)
    frame = pd.DataFrame(
        {
            "ts": pd.to_datetime(["2023-04-26T00:00:00Z", "2025-12-29T00:00:00Z"], utc=True),
            "mid_c": [1.0, 1.0],
        }
    )
    frame.to_parquet(tmp_path / "m15_USD_JPY.parquet", index=False)
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.load("USD_JPY")
    with pytest.raises(supplemental.SupplementalSpanError):
        supplemental.build_cache(["USD_JPY"])


@pytest.mark.parametrize("compact", ["20230426", "20251229"])
def test_a_compact_form_date_is_refused_although_it_is_a_real_date(compact):
    """`date.fromisoformat` accepts `YYYYMMDD`; the string comparisons do not.

    `"20230426" > "2023-04-26"` because `0` sorts above `-`, so a compact start
    slips past `start < SUPPLEMENTAL_START_UTC`. The width check is what makes
    every comparison downstream sound, so it is pinned separately from the
    calendar check.
    """
    with pytest.raises(MalformedUtcDateError):
        supplemental.assert_supplemental_span(compact, "2025-04-24")
    with pytest.raises(MalformedUtcDateError):
        supplemental.assert_supplemental_span("2023-04-26", compact)


# --------------------------------------------------------------------------
# the freeze, and the evaluation
# --------------------------------------------------------------------------


def test_the_frozen_candidate_is_read_from_round_2_not_restated():
    """If someone edits `round2.CENTRE`, this round's candidate moves with it.

    The candidate is frozen by that constant, committed at `c076988` and merged
    as `eab8f255`. Restating `480` would let the two drift apart and let a later
    edit quietly re-point the replication at a different rule — which the audit
    found had already happened once, in a dead `CENTRE` literal no test pinned.
    """
    assert supplemental_replication.FROZEN["lookback"] == round2.CENTRE[0]
    assert supplemental_replication.FROZEN["hold"] == round2.CENTRE[1]
    assert round2.CENTRE == (480, 480)
    assert supplemental_replication.FROZEN["entry_z"] == 1.0


def test_the_candidate_is_defined_exactly_once():
    """No second copy of a frozen parameter in this round's own modules."""
    from scripts.research.exploratory_m15 import supplemental_power

    assert not hasattr(supplemental_power, "CENTRE")


def test_the_evaluation_is_still_causal():
    """A pin on the one-bar shift and the trailing ATR rank, which nothing covered.

    The audit injected same-bar look-ahead (`position` without `.shift(1)`) and a
    full-sample ATR rank, and the whole suite stayed green both times.
    """
    from scripts.research.exploratory_m15 import engine

    assert "position.shift(1)" in inspect.getsource(engine.evaluate)
    assert round2.ATR_RANK_WINDOW == 960
    assert ".rolling(ATR_RANK_WINDOW" in inspect.getsource(round2._signal)
    assert round2.N_PHASES == 8


def test_the_replication_evaluates_both_periods_through_one_unbranched_call():
    """One call site, so neither period can be given its own treatment."""
    source = inspect.getsource(supplemental_replication.primary)
    assert source.count("round2.evaluate_config") == 1
    assert '("original", development), ("supplemental", supplemental)' in source


def test_the_recorded_span_matches_the_pre_read_plan():
    """The plan was committed before the reader existed; the constants follow it."""
    assert supplemental.SUPPLEMENTAL_START_UTC == "2023-04-26"
    assert supplemental.SUPPLEMENTAL_END_UTC == "2025-04-24"
    assert supplemental.FIRST_FORBIDDEN_FOR_THIS_ROUTE_UTC == bars.DEVELOPMENT_START_UTC
    assert supplemental.SCOPE == "SUPPLEMENTAL_EXPLORATORY_HISTORY"
    assert supplemental.OPERATION_READ == "track_a_supplemental_historical_read"
    assert supplemental.OPERATION_DERIVATION == "track_a_supplemental_m15_derivation"
