"""Regression tests for the PR #439 re-check blockers B-1..B-5 and fixes R-1..R-10.

Every test here encodes a defect that was probe-CONFIRMED against the pre-fix
merged source (master 697a1cf): each fails before the corresponding fix and
passes after. Synthetic literals only — no real data, no network, no file reads
outside pytest's ``tmp_path``.

Expected values are restated from the frozen contract and the committed
APPROVED specs, never re-derived from the implementation.

**Two dispositions this file used to pin have since been RULED against**, and the
tests that pinned them are deleted rather than adjusted (each deletion is
recorded inline with its clause): crossed-quote drop-and-count, revoked by D-1 /
§3; and the reported-not-enforced 20x3 cost-table coverage flag, revoked by D-10
(NR-J) / §12.16, which names the pinning test explicitly.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.m15_gate3a.aggregation import (
    BUCKET_MINUTES,
    AggregationError,
    aggregate_m15,
    to_pips,
)
from scripts.m15_gate3a.artifacts import (
    ArtifactScrubError,
    assert_gate3a_clean,
    write_metadata_artifact,
)
from scripts.m15_gate3a.cost_schema import CostSchemaError, validate_cost_table
from scripts.m15_gate3a.effective_n import (
    INSUFFICIENT_SAMPLE,
    RAW_TRADED_EVENT_COUNT,
    SUFFICIENT,
    EffectiveNError,
    effective_n,
)
from scripts.m15_gate3a.guards import (
    FORBIDDEN_STATUSES,
    RealDataRefusedError,
    assert_status_allowed,
    refuse_real_path,
)
from scripts.m15_gate3a.no_overlap import (
    DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL,
    NoOverlapError,
    assert_design_bounds,
    assert_forward_bounds,
    assert_no_dead_window,
    assert_per_file_bounds,
)
from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair
from scripts.m15_gate3a.path_authority import resolve_candidate
from scripts.m15_gate3a.warmup import WarmupPolicy, WarmupPolicyError
from tests.m15_gate3a.roster_fixtures import design_roster

requires_pandas = pytest.mark.skipif(
    importlib.util.find_spec("pandas") is None,
    reason="pandas not installed; only the B-1 subclass tests need it",
)

# --- contract constants, restated independently of the modules under test ----
DESIGN_START_S = "2025-04-25T00:00:00+00:00"
DESIGN_END_S = "2026-02-28T23:59:59+00:00"
DEAD_START_S = "2026-03-01T00:00:00+00:00"
DEAD_END_S = "2026-04-24T23:59:59+00:00"
FORWARD_FLOOR_S = "2026-04-25T00:00:00+00:00"
PIP_JPY = 0.01
PIP_NON_JPY = 0.0001

START = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)


def _row(ts, *, base: float = 1.10, half: float = 0.00005, **over):
    row = {
        "ts": ts,
        "bid_o": base - half,
        "bid_h": base + 0.0002 - half,
        "bid_l": base - 0.0002 - half,
        "bid_c": base + 0.0001 - half,
        "ask_o": base + half,
        "ask_h": base + 0.0002 + half,
        "ask_l": base - 0.0002 + half,
        "ask_c": base + 0.0001 + half,
    }
    row.update(over)
    return row


def _bucket(n: int, start: datetime = START) -> list[dict]:
    return [_row(start + timedelta(minutes=i)) for i in range(n)]


# ==========================================================================
# B-1 — pandas.Timestamp nanoseconds must not defeat minute alignment
# ==========================================================================


@requires_pandas
def test_b1_pandas_timestamp_nanosecond_rejected() -> None:
    """Isolates the sub-microsecond limb ONLY (audit §9 AP-1).

    The matcher used to read ``"minute-aligned|sub-microsecond"``. An
    alternation cannot say which guard fired, and here only one of them can:
    the value IS minute-aligned on ``.second``/``.microsecond``, so the
    alignment guard in ``to_utc_minute`` is unreachable for this input and the
    nanosecond guard in ``_reject_subclass_divergence`` is the whole test. The
    premise assertion below is what makes that verifiable rather than asserted.
    """
    import pandas as pd

    ts = pd.Timestamp("2025-06-02 00:00:00.000000500+0000")
    # Guard the premise: the ns is invisible to the fields the old check read,
    # so the minute-alignment limb cannot be what refuses this row.
    assert ts.second == 0 and ts.microsecond == 0 and ts.nanosecond == 500
    with pytest.raises(AggregationError, match="carries sub-microsecond resolution"):
        aggregate_m15([_row(ts)], pair="EUR_USD")


def test_b1_a_non_minute_aligned_timestamp_is_refused_by_the_alignment_guard() -> None:
    """The other limb of the split matcher, on an input that isolates it.

    Whole seconds carry no sub-microsecond information at all, so the
    nanosecond guard cannot fire and only ``to_utc_minute``'s alignment check
    can refuse. Needs no pandas: the limb is stdlib-reachable.
    """
    ts = datetime(2025, 6, 2, 0, 0, 30, tzinfo=UTC)
    assert getattr(ts, "nanosecond", 0) == 0 and ts.microsecond == 0
    with pytest.raises(AggregationError, match="is not minute-aligned"):
        aggregate_m15([_row(ts)], pair="EUR_USD")


@requires_pandas
def test_b1_fifteen_all_nanosecond_rows_are_rejected_not_eligible() -> None:
    """Pre-fix this produced ONE eligible bar at a non-15-minute bucket start."""
    import pandas as pd

    base = pd.Timestamp("2025-06-02 00:00:00+0000")
    rows = [_row(base + pd.Timedelta(minutes=i) + pd.Timedelta(nanoseconds=500)) for i in range(15)]
    with pytest.raises(AggregationError):
        aggregate_m15(rows, pair="EUR_USD")


@requires_pandas
def test_b1_same_minute_ns0_and_ns500_cannot_make_two_eligible_bars() -> None:
    """Pre-fix this produced TWO eligible bars for one 15-minute window."""
    import pandas as pd

    base = pd.Timestamp("2025-06-02 00:00:00+0000")
    rows = [_row(base + pd.Timedelta(minutes=i)) for i in range(15)]
    rows += [
        _row(base + pd.Timedelta(minutes=i) + pd.Timedelta(nanoseconds=500)) for i in range(15)
    ]
    with pytest.raises(AggregationError):
        aggregate_m15(rows, pair="EUR_USD")


@requires_pandas
def test_b1_single_sub_minute_row_among_aligned_rows_rejected() -> None:
    import pandas as pd

    base = pd.Timestamp("2025-06-02 00:00:00+0000")
    rows = [_row(base + pd.Timedelta(minutes=i)) for i in range(15)]
    rows.append(_row(base + pd.Timedelta(minutes=5) + pd.Timedelta(nanoseconds=1)))
    with pytest.raises(AggregationError):
        aggregate_m15(rows, pair="EUR_USD")


@requires_pandas
def test_b1_aligned_pandas_timestamps_are_accepted_and_bucket_is_plain_utc() -> None:
    import pandas as pd

    base = pd.Timestamp("2025-06-02 00:00:00+0000")
    bars, gap = aggregate_m15(
        [_row(base + pd.Timedelta(minutes=i)) for i in range(15)], pair="EUR_USD"
    )
    assert len(bars) == 1
    assert bars[0]["eligible"] is True and bars[0]["n_source_bars"] == 15
    ts = bars[0]["ts"]
    assert type(ts) is datetime  # plain datetime, not a pandas subclass
    assert ts == datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
    assert ts.minute % BUCKET_MINUTES == 0 and ts.second == 0 and ts.microsecond == 0
    assert gap["complete_bucket_count"] == 1  # R-2 / §12.20 rename of `n_eligible`


@requires_pandas
def test_b1_timezone_aware_pandas_timestamp_normalised_to_utc() -> None:
    import pandas as pd

    tokyo = pd.Timestamp("2025-06-02 09:00:00+0900")  # == 00:00Z
    bars, _ = aggregate_m15([_row(tokyo)], pair="EUR_USD")
    assert bars[0]["ts"] == datetime(2025, 6, 2, 0, 0, tzinfo=UTC)


def test_b1_duplicate_minute_across_offsets_still_rejected() -> None:
    other = START.astimezone(timezone(timedelta(hours=9)))
    with pytest.raises(AggregationError, match="duplicate source minute"):
        aggregate_m15([_row(START), _row(other)], pair="EUR_USD")


def test_b1_unsorted_input_gives_identical_bars_to_sorted_input() -> None:
    order = [7, 0, 14, 3, 1, 2, 4, 5, 6, 8, 9, 10, 11, 12, 13]
    shuffled = [_row(START + timedelta(minutes=i), base=1.10 + i / 10000) for i in order]
    ordered = [_row(START + timedelta(minutes=i), base=1.10 + i / 10000) for i in range(15)]
    assert aggregate_m15(shuffled, pair="EUR_USD")[0] == aggregate_m15(ordered, pair="EUR_USD")[0]


def test_b1_fifteen_distinct_minutes_eligible_fourteen_not() -> None:
    assert aggregate_m15(_bucket(15), pair="EUR_USD")[0][0]["eligible"] is True
    assert aggregate_m15(_bucket(14), pair="EUR_USD")[0][0]["eligible"] is False


def test_b1_bucket_boundary_splits_at_utc_quarter_hours() -> None:
    rows = [_row(START + timedelta(minutes=m)) for m in (14, 15, 29, 30)]
    bars, _ = aggregate_m15(rows, pair="EUR_USD")
    assert [b["ts"].minute for b in bars] == [0, 15, 30]


# ==========================================================================
# R-2 / R-6 — OHLC coherence and finite derived outputs
# ==========================================================================


def test_r2_high_below_low_row_rejected() -> None:
    rows = _bucket(15)
    rows[7] = _row(START + timedelta(minutes=7), bid_h=0.0, bid_l=9.0)
    # No alternation: the message names the limb that fired, so this cannot pass
    # because some *other* guard raised (the class that concealed B-7a).
    with pytest.raises(AggregationError, match=r"bid high 0\.0 < low 9\.0"):
        aggregate_m15(rows, pair="EUR_USD")


# --------------------------------------------------------------------------
# D-1 / §3 — the drop-and-count disposition is REVOKED.
#
# Five tests stood here pinning it: `test_r2_crossed_quote_dropped_and_counted_
# not_fatal`, `test_bl4_all_rows_crossed_yields_no_bars_and_a_full_drop_count`
# and `test_bl4_a_dropped_minute_cannot_be_substituted_by_a_second_record`
# (deleted below), plus the four-parameter `every_ohlc_limb` case and
# `test_bl4_a_single_crossed_row_no_longer_destroys_the_whole_pair` in
# `test_second_recheck_fixes.py`. The contract Gate-decision restores the hard
# refusal (D-1.3: "a crossed-quote row is never dropped-and-continued";
# D-1.5: "eligibility ... never preserved by dropping") and records the
# re-disposition as procedurally void. They are deleted rather than adjusted:
# a test that pins revoked behaviour is how a re-disposition becomes permanent.
#
# The restored disposition is covered by `test_wp_aggregation.py`
# (`test_d1_crossed_{open,high,low,close}_pair_refuses`, four separate tests with
# distinct match strings as D-1 requires, plus
# `test_d1_one_crossed_row_makes_the_whole_bucket_uncertifiable` and
# `test_d1_a_crossed_record_consumes_its_minute_and_still_refuses`), so it is
# deliberately not re-asserted here.
#
# What survives the revocation is kept, below.
# --------------------------------------------------------------------------


def test_zero_spread_is_not_a_crossed_quote_under_d1_7() -> None:
    """D-1.7: ``ask == bid`` is explicitly NOT a crossed quote.

    The subject survives the revocation; its old justification does not. This
    used to be argued from the ``stage25_0a`` analogy, which D-1.7 removes as
    authority — §11 of the pre-registration does not admit a non-family script as
    authority for a family-A design semantic. The rule now stands on the contract
    itself: a zero spread is refused only by a separate cost/spread contract, and
    then by that contract, never by the crossed-quote rule.
    """
    row = _row(START)
    for k in ("o", "h", "l", "c"):
        row[f"ask_{k}"] = row[f"bid_{k}"]
    bars, _ = aggregate_m15([row], pair="EUR_USD")
    assert len(bars) == 1
    assert bars[0]["spread_open"] == 0.0
    assert bars[0]["spread_close"] == 0.0


def test_intra_side_incoherence_is_fatal() -> None:
    """A broken side cannot describe any quote at all, so it refuses.

    The old name and docstring said "*still* fatal ... only the bid/ask relation
    became a drop", which is the revoked disposition stated as fact. Under D-1
    both refuse; this pins the intra-side limb specifically, and the match string
    names it so the bid/ask limb cannot satisfy this test by accident.
    """
    with pytest.raises(AggregationError, match=r"bid high 1\.0 < low 2\.0"):
        aggregate_m15([_row(START, bid_h=1.0, bid_l=2.0)], pair="EUR_USD")


def test_r6_finite_inputs_producing_infinite_spread_rejected() -> None:
    """Row is finite, per-side coherent and un-crossed; only the DERIVED spread overflows."""
    row = {"ts": START}
    for k in ("o", "h", "l", "c"):
        row[f"bid_{k}"] = -1.7e308
        row[f"ask_{k}"] = 1.7e308
    assert all(math.isfinite(v) for k, v in row.items() if k != "ts")
    assert math.isinf(row["ask_c"] - row["bid_c"])  # the overflow the guard must catch
    # §9 AP-1: "non-finite" names two guards. The premise above pins that every
    # INPUT value is finite, so only the derived-bar guard can be the one firing.
    with pytest.raises(AggregationError, match="derived bar value .* is non-finite"):
        aggregate_m15([row], pair="EUR_USD")


@pytest.mark.parametrize(
    "key", ["bid_o", "bid_h", "bid_l", "bid_c", "ask_o", "ask_h", "ask_l", "ask_c"]
)
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_f2_all_eight_keys_reject_non_finite(key: str, bad: float) -> None:
    with pytest.raises(AggregationError):
        aggregate_m15([_row(START, **{key: bad})], pair="EUR_USD")


@pytest.mark.parametrize(
    "key", ["bid_o", "bid_h", "bid_l", "bid_c", "ask_o", "ask_h", "ask_l", "ask_c"]
)
def test_f2_nan_in_a_middle_row_is_rejected_by_the_input_guard(key: str) -> None:
    """RF-3: a single-row bucket lets the derived guard raise instead.

    With the value in the MIDDLE of a full bucket, ``min()``/``max()`` skip the
    NaN and the bar comes out finite and ``eligible=True`` — so only the
    per-key input check can catch it. The message is pinned so the failure
    cannot come from the wrong guard.
    """
    rows = _bucket(15)
    rows[7] = _row(START + timedelta(minutes=7), **{key: float("nan")})
    with pytest.raises(AggregationError, match=rf"key '{key}' is non-finite"):
        aggregate_m15(rows, pair="EUR_USD")


@pytest.mark.parametrize(
    "key", ["bid_o", "bid_h", "bid_l", "bid_c", "ask_o", "ask_h", "ask_l", "ask_c"]
)
def test_f2_all_eight_keys_reject_bool(key: str) -> None:
    with pytest.raises(AggregationError, match="numeric"):
        aggregate_m15([_row(START, **{key: True})], pair="EUR_USD")


def test_ohlc_outputs_are_value_pinned_both_sides() -> None:
    """High/low swap or a spread-sign inversion must be detectable."""
    rows = [_row(START + timedelta(minutes=i), base=1.10 + i / 10000) for i in range(15)]
    bars, _ = aggregate_m15(rows, pair="EUR_USD")
    b = bars[0]
    assert b["bid_o"] == pytest.approx(1.09995)  # first row, bid open
    assert b["bid_c"] == pytest.approx(1.10145)  # last row, bid close
    assert b["bid_h"] == pytest.approx(1.10155)  # max over rows
    assert b["bid_l"] == pytest.approx(1.09975)  # min over rows
    assert b["ask_o"] == pytest.approx(1.10005)
    assert b["ask_c"] == pytest.approx(1.10155)
    assert b["ask_h"] == pytest.approx(1.10165)
    assert b["ask_l"] == pytest.approx(1.09985)
    assert b["bid_h"] > b["bid_l"] and b["ask_h"] > b["ask_l"]
    assert b["spread_close"] == pytest.approx(0.0001)  # ask_c - bid_c, positive
    assert b["spread_close"] > 0
    assert all(math.isfinite(b[k]) for k in ("bid_h", "bid_l", "ask_h", "ask_l", "spread_close"))


def test_ohlc_uses_bucket_extrema_not_first_or_last_row() -> None:
    """RF-2: with the extremes in a MIDDLE minute, positional selection is wrong.

    Row 7 carries the bucket high and low on both sides; rows 0 and 14 do not.
    A `rows[-1]["bid_h"]`-style implementation would report 1.10015 instead of
    the true 1.50000.
    """
    rows = [_row(START + timedelta(minutes=i), base=1.10 + i / 10000) for i in range(15)]
    spike = _row(START + timedelta(minutes=7))
    spike["bid_h"] = 1.50000
    spike["ask_h"] = 1.50010
    spike["bid_l"] = 0.90000
    spike["ask_l"] = 0.90010
    rows[7] = spike
    bars, _ = aggregate_m15(rows, pair="EUR_USD")
    b = bars[0]
    assert b["bid_h"] == pytest.approx(1.50000)  # from the MIDDLE row, not the last
    assert b["ask_h"] == pytest.approx(1.50010)
    assert b["bid_l"] == pytest.approx(0.90000)  # from the MIDDLE row, not the first
    assert b["ask_l"] == pytest.approx(0.90010)
    # open/close still come from the chronological ends, not from the extremes.
    assert b["bid_o"] == pytest.approx(1.09995)
    assert b["bid_c"] == pytest.approx(1.10145)
    assert b["ask_o"] == pytest.approx(1.10005)
    assert b["ask_c"] == pytest.approx(1.10155)
    assert b["eligible"] is True


# ==========================================================================
# R-7 — gap report is minute-granular and uses the committed schema key
# ==========================================================================


def test_r7_minute_level_gap_is_reported() -> None:
    """R-1: the three self-attestations that stood here are deleted, not reported.

    ``imputation``, ``synthetic_weekend_bars`` and ``mid_price_constructed``
    could each hold only one value, so none was evidence while all three read as
    measured facts. The properties they claimed are observable and are measured
    instead: the hole stays a hole (no back-fill), only the two windows that
    actually contain a minute are emitted (no fabricated weekend bar), and no bar
    carries a mid-price key.
    """
    bars, gap = aggregate_m15([_row(START), _row(START + timedelta(minutes=29))], pair="EUR_USD")
    assert gap["missing_minute_count"] == 28
    assert gap["max_gap_minutes"] == 28  # pre-fix this was 0
    assert len(bars) == 2  # not the four windows the span covers
    assert [b["n_source_bars"] for b in bars] == [1, 1]  # not back-filled to 15
    assert all("mid" not in b for b in bars)


def test_r7_whole_bucket_gap_still_counted() -> None:
    rows = _bucket(15) + [_row(START + timedelta(minutes=45))]
    _, gap = aggregate_m15(rows, pair="EUR_USD")
    assert gap["missing_whole_buckets"] == 2
    assert gap["max_gap_minutes"] == 30


# ==========================================================================
# B-2 — no-overlap bounds
# ==========================================================================


def test_b2_reversed_span_rejected_by_per_file_bounds() -> None:
    files = design_roster(ts_min="2025-12-01T00:00:00Z", ts_max="2025-06-01T00:00:00Z")
    with pytest.raises(NoOverlapError, match="reversed span"):
        assert_per_file_bounds(files, role="design")


def test_b2_reversed_span_rejected_by_each_bound_checker() -> None:
    with pytest.raises(NoOverlapError, match="reversed span"):
        assert_forward_bounds("2026-05-01T00:00:00Z", "2026-01-01T00:00:00Z")
    with pytest.raises(NoOverlapError, match="reversed span"):
        assert_design_bounds("2026-01-01T00:00:00Z", "2025-06-01T00:00:00Z")
    with pytest.raises(NoOverlapError, match="reversed span"):
        assert_no_dead_window("2026-05-01T00:00:00Z", "2026-01-01T00:00:00Z", role="probe")


def test_b2_span_containing_dead_window_never_proven() -> None:
    """B-7a: the epoch-ceiling limb, named on its own (audit §9 AP-1).

    The matcher used to read ``"dead window|DESIGN_END"``, and that alternation
    is what concealed B-7a: only the ceiling limb can fire here. ``DEAD_START``
    sits *after* ``DESIGN_END``, so any design span reaching the dead window has
    already exceeded the ceiling and ``_assert_design_bounds_parsed`` refuses
    before its own dead-window limb is consulted. Naming the ceiling is
    therefore the honest assertion; the dead-window limb is exercised
    separately, through the checker where it is reachable.
    """
    files = design_roster(ts_min="2026-01-01T00:00:00Z", ts_max="2026-05-01T00:00:00Z")
    with pytest.raises(NoOverlapError, match="exceeds the frozen design-epoch ceiling"):
        assert_per_file_bounds(files, role="design")


def test_b2_the_design_ceiling_fires_with_no_dead_window_in_the_span() -> None:
    """The ceiling limb alone: a span half a second past DESIGN_END.

    ``DESIGN_END`` and ``DEAD_START`` are one second apart, so this span
    exceeds the ceiling while ending before the dead window begins — the
    dead-window predicate is False for it and cannot contribute to the refusal.
    """
    over_ceiling = "2026-02-28T23:59:59.500000+00:00"
    with pytest.raises(NoOverlapError, match="exceeds the frozen design-epoch ceiling"):
        assert_design_bounds(DESIGN_START_S, over_ceiling)
    # Premise: the same span is clean as far as the dead window is concerned.
    assert_no_dead_window(DESIGN_START_S, over_ceiling, role="probe")


def test_b2_the_dead_window_limb_is_named_where_it_is_reachable() -> None:
    """The limb the alternation used to stand in for, pinned by its own phrase."""
    with pytest.raises(NoOverlapError, match="span intersects dead window"):
        assert_no_dead_window("2026-01-01T00:00:00Z", "2026-05-01T00:00:00Z", role="design")


def test_b2_boundary_constants_pinned_independently() -> None:
    assert_design_bounds(DESIGN_START_S, DESIGN_END_S)  # inclusive both ends
    with pytest.raises(NoOverlapError):
        assert_design_bounds(DESIGN_START_S, DEAD_START_S)
    with pytest.raises(NoOverlapError):
        assert_design_bounds("2025-04-24T23:59:59+00:00", DESIGN_END_S)
    assert_forward_bounds(FORWARD_FLOOR_S, "2026-06-01T00:00:00+00:00")
    with pytest.raises(NoOverlapError):
        assert_forward_bounds(DEAD_END_S, "2026-06-01T00:00:00+00:00")
    with pytest.raises(NoOverlapError, match="span intersects dead window"):
        assert_no_dead_window(DEAD_START_S, DEAD_START_S, role="probe")
    with pytest.raises(NoOverlapError, match="span intersects dead window"):
        assert_no_dead_window(DEAD_END_S, DEAD_END_S, role="probe")


def test_b2_sub_second_tail_of_dead_window_is_dead() -> None:
    """O-3 sliver, closed conservatively without moving any published constant."""
    with pytest.raises(NoOverlapError, match="span intersects dead window"):
        assert_no_dead_window(
            "2026-04-24T23:59:59.500000+00:00", "2026-06-01T00:00:00+00:00", role="probe"
        )
    # The forward floor itself remains clean.
    assert_no_dead_window(FORWARD_FLOOR_S, "2026-06-01T00:00:00+00:00", role="probe")


def test_b2_a_valid_design_inventory_earns_the_declaration_only_token() -> None:
    """B-2 / D-11: the token names its own basis and is compared by import.

    ``PROVEN_NO_DEAD_WINDOW_OVERLAP`` claimed more than this check establishes —
    no file is opened and no byte is measured here — so it is replaced by the
    declaration-only token. Importing the constant rather than repeating its text
    is what keeps a future rename from passing silently.
    """
    files = design_roster(ts_min="2025-05-01T00:00:00Z", ts_max="2025-06-01T00:00:00Z")
    result = assert_per_file_bounds(files, role="design")
    assert result["result"] == DECLARED_SPANS_SELF_CONSISTENT__NOT_BYTE_LEVEL
    assert result["files_opened"] == 0 and result["bytes_measured"] == 0


# ==========================================================================
# B-3 / B-5 / R-1 — effective-N
# ==========================================================================


def _pp(pair: str, raw: int, overlap: float) -> dict:
    return {"pair": pair, "raw_event_count": raw, "overlap_fraction": overlap}


def test_b3_audited_counterexample_is_insufficient() -> None:
    r = effective_n(
        [_pp("EUR_USD", 50, 0.0), _pp("GBP_USD", 8000, 1.0)],
        count_quantity=RAW_TRADED_EVENT_COUNT,
        cross_pair_corr=0.0,
    )
    assert r["effective_n"] == pytest.approx(383.3333333, rel=1e-6)
    assert r["verdict"] == INSUFFICIENT_SAMPLE


def test_b3_per_pair_granularity_reported() -> None:
    r = effective_n(
        [_pp("EUR_USD", 100, 0.0), _pp("GBP_USD", 200, 0.5)],
        count_quantity=RAW_TRADED_EVENT_COUNT,
        cross_pair_corr=0.0,
    )
    assert [p["pair"] for p in r["per_pair"]] == ["EUR_USD", "GBP_USD"]
    assert r["per_pair"][0]["effective_n"] == pytest.approx(100.0)
    assert r["per_pair"][1]["effective_n"] == pytest.approx(200 / 12.5)
    assert r["raw_event_count"] == 300


@pytest.mark.parametrize(
    "raw_floor,neff_floor",
    [
        (None, 100.0),
        (100, None),
        (0, 100.0),
        (-1, 100.0),
        (100, 0.0),
        (100, -1.0),
        (100, float("nan")),
        (100, float("inf")),
        (True, 100.0),
        (100, True),
        ("100", 100.0),
    ],
)
def test_b5_invalid_validation_floors_fail_closed(raw_floor, neff_floor) -> None:
    with pytest.raises(EffectiveNError):
        effective_n(
            [_pp("EUR_USD", 0, 0.0)],
            count_quantity=RAW_TRADED_EVENT_COUNT,
            cross_pair_corr=0.0,
            role="validation",
            validation_raw_floor=raw_floor,
            validation_neff_floor=neff_floor,
        )


def test_b5_zero_events_never_sufficient() -> None:
    r = effective_n(
        [_pp("EUR_USD", 0, 0.0)],
        count_quantity=RAW_TRADED_EVENT_COUNT,
        cross_pair_corr=0.0,
        role="validation",
        validation_raw_floor=1,
        validation_neff_floor=1.0,
    )
    assert r["verdict"] == INSUFFICIENT_SAMPLE
    assert r["verdict"] != SUFFICIENT


def test_r1_horizon_override_rejected_at_holdout_and_echoed() -> None:
    with pytest.raises(EffectiveNError, match="frozen at 24"):
        effective_n(
            [_pp("EUR_USD", 1000, 1.0)],
            count_quantity=RAW_TRADED_EVENT_COUNT,
            cross_pair_corr=0.0,
            horizon_bars=1,
        )
    r = effective_n(
        [_pp("EUR_USD", 1000, 1.0)], count_quantity=RAW_TRADED_EVENT_COUNT, cross_pair_corr=0.0
    )
    assert r["horizon_bars"] == 24
    assert r["verdict"] == INSUFFICIENT_SAMPLE
    assert r["floors_applied"] == {"raw_floor": 1000.0, "neff_floor": 400.0}


# ==========================================================================
# B-4 — pair authority
# ==========================================================================


# The frozen universe, restated here so a member substitution in the module
# under test cannot pass unnoticed (RF-4).
_EXPECTED_PAIRS_20 = (
    "EUR_USD",
    "GBP_USD",
    "AUD_USD",
    "NZD_USD",
    "USD_CHF",
    "USD_CAD",
    "EUR_GBP",
    "USD_JPY",
    "EUR_JPY",
    "GBP_JPY",
    "AUD_JPY",
    "NZD_JPY",
    "CHF_JPY",
    "EUR_CHF",
    "EUR_AUD",
    "EUR_CAD",
    "AUD_NZD",
    "AUD_CAD",
    "GBP_AUD",
    "GBP_CHF",
)


def test_b4_pairs_20_universe_matches_canonical_list() -> None:
    assert tuple(PAIRS_20) == _EXPECTED_PAIRS_20
    assert len(set(PAIRS_20)) == 20
    for pair in _EXPECTED_PAIRS_20:
        assert canonical_pair(pair) == pair
        expected_pip = PIP_JPY if pair.endswith("_JPY") else PIP_NON_JPY
        assert aggregate_m15(_bucket(1), pair=pair)[0][0]["pip_size"] == expected_pip


@pytest.mark.parametrize(
    "spelling", ["USD_JPY", "usd_jpy", " USD_JPY ", "USDJPY", "usd-jpy", "usd/jpy", "Usd_Jpy"]
)
def test_b4_jpy_spellings_all_resolve_to_jpy_pip(spelling: str) -> None:
    assert canonical_pair(spelling) == "USD_JPY"
    bars, gap = aggregate_m15(_bucket(1), pair=spelling)
    assert bars[0]["pip_size"] == PIP_JPY
    assert gap["pip_size"] == PIP_JPY
    assert to_pips(0.02, spelling) == pytest.approx(2.0)  # NOT 200.0


@pytest.mark.parametrize("spelling", ["EUR_USD", "eur_usd", "EURUSD", "eur/usd"])
def test_b4_non_jpy_spellings_resolve_to_non_jpy_pip(spelling: str) -> None:
    assert canonical_pair(spelling) == "EUR_USD"
    assert aggregate_m15(_bucket(1), pair=spelling)[0][0]["pip_size"] == PIP_NON_JPY


@pytest.mark.parametrize("bad", ["XXX_YYY", "NOT_A_PAIR", "ZZZ", "", "   ", "GARBAGE", None, 42])
def test_b4_off_universe_pairs_fail_closed(bad) -> None:
    with pytest.raises(PairAuthorityError):
        canonical_pair(bad)


def test_b4_normalisation_is_injective_over_the_universe() -> None:
    assert len({canonical_pair(p) for p in PAIRS_20}) == len(PAIRS_20)


def test_b4_cost_schema_rejects_non_canonical_pair_spelling() -> None:
    from tests.m15_gate3a.test_cost_schema import _table  # reuse the fixture shape

    # §9 AP-1: "canonical" also appears in the 20x3 coverage refusal; this names
    # the per-entry spelling guard and nothing else.
    with pytest.raises(CostSchemaError, match="pair must be the canonical spelling"):
        validate_cost_table(
            _table(entry={"pair": "usd_jpy", "pip_size": 0.01}), max_spread_pips=None
        )


# ==========================================================================
# R-8 — cost-table units, formula and quantile ordering
# ==========================================================================


def _cost_table(**over):
    from tests.m15_gate3a.test_cost_schema import _table

    return _table(**over)


def test_r8_spread_unit_is_mandatory_and_pinned() -> None:
    t = _cost_table()
    del t["spread_unit"]
    with pytest.raises(CostSchemaError, match="spread_unit"):
        validate_cost_table(t, max_spread_pips=None)
    with pytest.raises(CostSchemaError, match="spread_unit"):
        validate_cost_table(_cost_table(spread_unit="pip"), max_spread_pips=None)
    assert validate_cost_table(_cost_table(), max_spread_pips=None)["spread_unit"] == "price"


def test_r8_formula_string_must_match_the_frozen_plan() -> None:
    with pytest.raises(CostSchemaError, match="all_in_cost_formula"):
        validate_cost_table(
            _cost_table(all_in_cost_formula="median + 0.0 + 0.0"), max_spread_pips=None
        )


def test_r8_quantiles_must_be_monotone() -> None:
    with pytest.raises(CostSchemaError, match="median <= p90 <= p95"):
        validate_cost_table(
            _cost_table(
                entry={"median_spread": 0.0009, "p90_spread": 0.0002, "p95_spread": 0.0001}
            ),
            max_spread_pips=None,
        )
    with pytest.raises(CostSchemaError, match="median <= p90 <= p95"):
        validate_cost_table(
            _cost_table(
                entry={"median_spread": 0.00008, "p90_spread": 0.0003, "p95_spread": 0.0002}
            ),
            max_spread_pips=None,
        )


def test_r8_padding_and_cell_remain_unloosenable() -> None:
    with pytest.raises(CostSchemaError):
        validate_cost_table(_cost_table(execution_padding_pip=0.31), max_spread_pips=None)
    with pytest.raises(CostSchemaError):
        validate_cost_table(_cost_table(flat_slippage_cell_pip=0.51), max_spread_pips=None)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), -1.0, True])
@pytest.mark.parametrize("stat", ["median_spread", "p90_spread", "p95_spread"])
def test_r8_non_finite_negative_and_bool_spreads_rejected(stat: str, bad) -> None:
    with pytest.raises(CostSchemaError):
        validate_cost_table(_cost_table(entry={stat: bad}), max_spread_pips=None)


# ==========================================================================
# R-3 / R-4 / R-5 / R-9 — guards, statuses, scrubber, writer
# ==========================================================================


def test_r3_extended_length_alias_still_refused(tmp_path) -> None:
    from scripts.ml_step4.evidence import repo_root

    protected = repo_root() / "artifacts" / "ml_step4" / "365d_ba_v1"
    with pytest.raises(RealDataRefusedError):
        refuse_real_path(str(protected))
    with pytest.raises(RealDataRefusedError):
        refuse_real_path("\\\\?\\" + str(protected))
    refuse_real_path(tmp_path)  # unrelated path still allowed


def test_r4_playbook_forbidden_statuses_all_refused() -> None:
    for status in ("READY_FOR_LIVE", "ROBUST", "DEPLOYABLE", "PASS", "MEETS", "Tier 1"):
        assert status in FORBIDDEN_STATUSES or status.upper() in {
            s.upper() for s in FORBIDDEN_STATUSES
        }
        with pytest.raises(RealDataRefusedError):
            assert_status_allowed(status)


@pytest.mark.parametrize(
    "variant",
    ["production ready", "PRODUCTION-READY", "Tier  1", "tier-1", "new epoch adopted", " PASS "],
)
def test_r4_separator_and_case_variants_refused(variant: str) -> None:
    with pytest.raises(RealDataRefusedError):
        assert_status_allowed(variant)


def test_r4_allowed_status_still_ok() -> None:
    assert_status_allowed("M15_AGGREGATION_DATASET_MACHINERY_TARGETED_FIXES_PROPOSED")


def test_r4_forbidden_status_as_artifact_value_is_scrubbed() -> None:
    with pytest.raises(ArtifactScrubError, match="forbidden_status_value"):
        assert_gate3a_clean({"result": "PASS", "note": "x"})
    with pytest.raises(ArtifactScrubError, match="forbidden_status_value"):
        assert_gate3a_clean({"readiness": "PRODUCTION_READY"})
    with pytest.raises(ArtifactScrubError, match="forbidden_status_value"):
        assert_gate3a_clean({"list": ["NEW_EPOCH_ADOPTED"]})


_ROW8 = {"a": 1.1, "b": 1.2, "c": 1.0, "d": 1.15, "e": 1.11, "f": 1.21, "g": 1.01, "h": 1.16}


def test_r5_row_like_records_rejected_even_with_a_benign_dict() -> None:
    with pytest.raises(ArtifactScrubError, match="row_like"):
        assert_gate3a_clean({"data": [_ROW8, dict(_ROW8)]})
    with pytest.raises(ArtifactScrubError, match="row_like"):
        assert_gate3a_clean({"data": [_ROW8, dict(_ROW8), {"label": "x"}]})


def test_r5_columnar_series_rejected() -> None:
    """§9 AP-1: the columnar heuristic, named by the finding token it appends.

    The matcher used to read ``"columnar|row_like"`` across both this payload
    and the array-of-rows one below; this payload emits
    ``gate3a_columnar_numeric_series`` and never a row-like finding, so the
    alternation could not have told the two heuristics apart. The 50-long
    series also trips the numeric-cardinality budget, so the short payload
    isolates the columnar limb on its own.
    """
    with pytest.raises(ArtifactScrubError, match="gate3a_columnar_numeric_series"):
        assert_gate3a_clean({"o": [1.1] * 50, "h": [1.2] * 50, "l": [1.0] * 50, "c": [1.15] * 50})
    with pytest.raises(ArtifactScrubError) as exc:
        assert_gate3a_clean({"o": [1.1] * 4, "h": [1.2] * 4, "l": [1.0] * 4, "c": [1.15] * 4})
    assert "gate3a_columnar_numeric_series" in str(exc.value)
    assert "cardinality_exceeded" not in str(exc.value)  # the columnar limb, alone


def test_r5_array_rows_rejected() -> None:
    """The other heuristic, on its own payload and its own finding token."""
    with pytest.raises(ArtifactScrubError, match="gate3a_row_like_numeric_arrays"):
        assert_gate3a_clean({"data": [[1.1, 1.2, 1.0, 1.15], [1.11, 1.21, 1.01, 1.16]]})


def test_r5_key_matcher_strips_whitespace() -> None:
    with pytest.raises(ArtifactScrubError, match="forbidden_key"):
        assert_gate3a_clean({"sharpe ": 1.0})


def test_r5_legitimate_metadata_still_survives() -> None:
    assert_gate3a_clean(
        {
            "entries": [
                {
                    "pair": "EUR_USD",
                    "session": "europe",
                    "median_spread": 0.00008,
                    "p90_spread": 0.00015,
                    "p95_spread": 0.0002,
                    "pip_size": 0.0001,
                }
            ]
            * 3
        }
    )
    assert_gate3a_clean(
        {
            "files": [
                {"filename": f"{i}.jsonl", "sha256": "ab" * 32, "size_bytes": 10, "row_count": 5}
                for i in range(20)
            ]
        }
    )


def test_r9_artifact_name_cannot_escape_out_dir(tmp_path) -> None:
    for bad in ("../escaped.json", "sub/inner.json", "sub\\inner.json"):
        with pytest.raises(ArtifactScrubError, match="bare filename"):
            write_metadata_artifact(tmp_path / "inner", bad, {"ok": 1})
    assert not (tmp_path / "inner").exists()  # refusal leaves no stray directory
    written = write_metadata_artifact(tmp_path / "inner", "ok.json", {"ok": 1})
    assert written.parent == tmp_path / "inner"


# ==========================================================================
# Warm-up policy hygiene (N-3) and committed-artifact regression
# ==========================================================================


def test_warmup_invalid_policy_cannot_authorise_loads() -> None:
    with pytest.raises(WarmupPolicyError):
        WarmupPolicy(w_bars=0, longest_feature_lookback_bars=50).assert_load_allowed(
            "2026-05-01T00:00:00Z"
        )


def test_warmup_non_utc_offset_converted_not_misread() -> None:
    policy = WarmupPolicy(w_bars=64, longest_feature_lookback_bars=48)
    with pytest.raises(WarmupPolicyError):
        policy.assert_load_allowed("2026-04-25T08:00:00+09:00")  # == 2026-04-24T23:00Z
    policy.assert_load_allowed("2026-04-25T09:00:00+09:00")  # == 2026-04-25T00:00Z
    policy.assert_load_allowed(datetime(2026, 4, 25, 9, 0, tzinfo=timezone(timedelta(hours=9))))


def test_committed_gate3a_artifacts_remain_scrub_clean() -> None:
    """RF-22: a glob with no non-vacuity floor passes in a tree with no artifacts.

    The loop below is only evidence if it actually ran over the committed set, so
    the expected filenames are asserted **first**, and they are sourced from
    ``EXPECTED_ARTIFACT_FILES`` — the constant the scrubber derives from its own
    schema table — rather than from a count restated here that could drift.
    """
    from scripts.m15_gate3a.artifacts import EXPECTED_ARTIFACT_FILES
    from scripts.ml_step4.evidence import repo_root

    paths = sorted((repo_root() / "artifacts" / "m15_gate3a").glob("*.json"))
    assert [p.name for p in paths] == sorted(EXPECTED_ARTIFACT_FILES)
    assert len(paths) == len(EXPECTED_ARTIFACT_FILES) > 0

    scanned = 0
    for path in paths:
        assert_gate3a_clean(json.loads(path.read_text(encoding="utf-8")))
        scanned += 1
    assert scanned == len(EXPECTED_ARTIFACT_FILES)


# ==========================================================================
# NB-1 — refusal hygiene
#
# `test_rf6_coverage_flag_is_reported_and_pinned` stood here and pinned the
# 20x3 coverage flag as "deliberately REPORTED, not enforced". D-10 (NR-J) /
# §12.16 revokes that: "insufficient required coverage **raises**; recording a
# coverage flag never permits continuation", and it names this very test —
# "the existing test that currently pins the re-disposition as correct behaviour
# must be rewritten or deleted; leaving it is how a re-disposition becomes
# permanent". It is deleted. The restored behaviour is covered by
# `test_wp_cost_effn_warmup_status.py::test_rf19_*` (the 60-cell grid validating,
# a one-entry table raising and naming its missing cells, the 59-vs-60 boundary,
# and `test_rf19_no_coverage_flag_is_reported_at_all`), so it is not duplicated
# here.
# ==========================================================================


def test_nb1_refused_write_leaves_no_directory_behind(tmp_path, monkeypatch) -> None:
    """The refusals must run BEFORE mkdir, or a refused write litters the tree.

    RF-4: this used to aim the write at the REAL protected evidence tree on
    every run — correct only for as long as the guard held, and the suite's own
    litter if it ever regressed. The protected prefix is now synthetic, so the
    test proves the ordering without ever addressing real evidence.
    """
    import scripts.m15_gate3a.guards as guards_mod

    synthetic_root = tmp_path / "fake_repo"
    (synthetic_root / "protected_stub").mkdir(parents=True)
    monkeypatch.setattr(guards_mod, "repo_root", lambda: synthetic_root)
    monkeypatch.setattr(guards_mod, "_PROTECTED_PREFIXES", ("protected_stub",))

    target = synthetic_root / "protected_stub" / "nb1_probe"
    with pytest.raises(RealDataRefusedError):
        write_metadata_artifact(target, "x.json", {"ok": 1})
    assert not target.exists()

    fresh = tmp_path / "never_created"
    with pytest.raises(ArtifactScrubError):
        write_metadata_artifact(fresh, "bad.txt", {"ok": 1})
    assert not fresh.exists()


def _path_components(text: str) -> list[str]:
    """Split a path-ish literal into its components, on either separator."""
    return [part for part in text.replace("\\", "/").split("/") if part]


def _protected_component_hit(text: str, leaves: frozenset[str], prefixes: tuple[str, ...]) -> str:
    """The protected tree *text* names as a path COMPONENT, or ``""``.

    Substring matching is what made this test false-positive: the newly protected
    prefix ``data`` is a substring of the *function name* ``write_metadata_artifact``,
    so roughly a dozen entirely-synthetic call sites read as writes into the real
    candle store. A path names a protected tree when one of its **components** is
    a protected leaf, or when a protected prefix appears as a contiguous run of
    its components — never merely because the letters occur somewhere.
    """
    parts = _path_components(text)
    lowered = [p.casefold() for p in parts]
    for index, part in enumerate(lowered):
        if part in leaves:
            return parts[index]
    for prefix in prefixes:
        wanted = [p.casefold() for p in _path_components(prefix)]
        span = len(wanted)
        if span and any(lowered[i : i + span] == wanted for i in range(len(lowered) - span + 1)):
            return prefix
    return ""


def test_rf4_the_suite_never_addresses_the_real_protected_tree() -> None:
    """No test may name a real protected prefix as a write target.

    Anchored to ``__file__``, not the working directory: an earlier version used
    a cwd-relative glob, so running pytest from anywhere else made the glob empty
    and the guard passed vacuously. It scans every ``.py`` in the package and
    matches a write anywhere in the call rather than only on the same source line.

    The comparison is over **path components of the string literals inside the
    call**, not over the raw source text of the call. As a substring test it
    began reporting every ``write_metadata_artifact(...)`` in the suite as a
    write into ``data/`` the moment that prefix was protected — a guard that
    fires on its own callee's name cannot tell anyone anything.
    """
    import ast

    from scripts.m15_gate3a.guards import _PROTECTED_PREFIXES

    here = Path(__file__).resolve().parent
    files = sorted(here.glob("*.py"))
    assert len(files) >= 8, f"protected-tree scan found only {len(files)} files under {here}"

    leaves = frozenset(_path_components(p)[-1].casefold() for p in _PROTECTED_PREFIXES)
    assert leaves, "no protected prefixes to scan for: the guard would be vacuous"

    inspected = 0
    for path in files:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name not in ("write_metadata_artifact", "write_text", "write_bytes", "mkdir"):
                continue
            inspected += 1
            for literal in ast.walk(node):
                if not isinstance(literal, ast.Constant) or not isinstance(literal.value, str):
                    continue
                hit = _protected_component_hit(literal.value, leaves, _PROTECTED_PREFIXES)
                assert not hit, (
                    f"{path.name}: {name}(...) aimed at a protected tree ({hit}): "
                    f"{literal.value[:120]}"
                )
    # Non-vacuity floor: a scan that inspected no write call proves nothing.
    assert inspected > 0, "the protected-tree scan found no write call to inspect"


def test_rf4_the_component_matcher_still_catches_a_real_protected_target() -> None:
    """The matcher must keep both verdicts, or the scan above proves nothing.

    Positive cases are the real protected spellings; the negative case is the
    substring collision that made the scan false-positive — ``write_metadata_artifact``
    contains ``data``, but never as a path component.
    """
    from scripts.m15_gate3a.guards import _PROTECTED_PREFIXES

    leaves = frozenset(_path_components(p)[-1].casefold() for p in _PROTECTED_PREFIXES)
    for named in (
        "artifacts/ml_step4/365d_ba_v1/first_run/x.json",
        "artifacts\\gate_p1_pr_b\\firstrun_365d_ba\\raw_inventory.json",
        "data/candles/USD_JPY_M1.jsonl",
        "models",
        "docs/design/note.md",
    ):
        assert _protected_component_hit(named, leaves, _PROTECTED_PREFIXES), named
    for benign in (
        "write_metadata_artifact",
        "metadata_only.json",
        "no_overlap_proof.json",
        "database_notes/x.json",
        "tmp/model_stub/out.json",
    ):
        assert not _protected_component_hit(benign, leaves, _PROTECTED_PREFIXES), benign


def test_rf6_a_nul_byte_raises_the_documented_exception(tmp_path) -> None:
    """RF-6: a NUL escaped as a bare ValueError, not RealDataRefusedError."""
    with pytest.raises(RealDataRefusedError):
        refuse_real_path("a\x00b")
    with pytest.raises((RealDataRefusedError, ArtifactScrubError)):
        write_metadata_artifact(tmp_path, "a\x00b.json", {"ok": 1})
    with pytest.raises((RealDataRefusedError, ArtifactScrubError)):
        write_metadata_artifact(str(tmp_path) + "\x00x", "ok.json", {"ok": 1})


# ==========================================================================
# D1..D6 — defects found by the internal adversarial audit OF THIS FIX
# ==========================================================================


def test_d1_plain_protected_path_refused() -> None:
    """Platform-independent baseline for the protected-path guard."""
    from scripts.ml_step4.evidence import repo_root

    protected = (repo_root() / "artifacts" / "ml_step4" / "365d_ba_v1").resolve()
    with pytest.raises(RealDataRefusedError):
        refuse_real_path(str(protected))
    with pytest.raises(RealDataRefusedError):
        refuse_real_path(protected / "sub" / "x.json")


@pytest.mark.skipif(
    sys.platform != "win32", reason=r"UNC and \?\ aliases are Windows-only spellings"
)
def _protected_365d_ba_v1() -> Path:
    from scripts.ml_step4.evidence import repo_root

    return (repo_root() / "artifacts" / "ml_step4" / "365d_ba_v1").resolve()


def _alias_spellings(protected: str) -> dict[str, str]:
    """Windows spellings that all name one directory."""
    drive, tail_path = protected[0], protected[2:]
    bs = chr(92)  # backslash, written this way to avoid escape ambiguity
    return {
        "plain": protected,
        "extended_drive": (bs * 2) + "?" + bs + protected,
        "unc_localhost": (bs * 2) + "localhost" + bs + drive + "$" + tail_path,
        "unc_loopback": (bs * 2) + "127.0.0.1" + bs + drive + "$" + tail_path,
        "extended_unc": (bs * 2)
        + "?"
        + bs
        + "UNC"
        + bs
        + "localhost"
        + bs
        + drive
        + "$"
        + tail_path,
    }


@pytest.mark.parametrize("spelling", ["plain", "extended_drive"])
def test_d1_name_limb_aliases_of_a_protected_path_refused(spelling: str) -> None:
    """The spellings the NAME limb decides — no on-disk state participates.

    §9 AP-4: the predecessor asserted all five spellings in one loop, and three
    of them are decided by the *identity* limb, which needs the protected tree
    to exist. The two halves are separated so this one measures only code.
    """
    if spelling != "plain" and os.name != "nt":
        pytest.skip(f"{spelling} is a Windows-namespace spelling; not constructible on this OS")
    protected = _protected_365d_ba_v1()
    alias = _alias_spellings(str(protected))[spelling]
    candidate = resolve_candidate(alias)
    # Premise, asserted rather than assumed: this spelling folds to a path
    # NAMED under the protected tree, so nothing about the filesystem can be
    # what produces the refusal below.
    assert candidate == protected or protected in candidate.parents
    with pytest.raises(RealDataRefusedError):
        refuse_real_path(alias)


@pytest.mark.parametrize("spelling", ["unc_localhost", "unc_loopback", "extended_unc"])
def test_d1_identity_limb_aliases_of_a_protected_path_refused(spelling: str) -> None:
    """The spellings only the IDENTITY limb can decide, with the premise measured.

    §9 AP-4: "in a copy without ``artifacts/ml_step4/365d_ba_v1`` the test
    FAILS" — reproduced. These spellings do not resolve to a path named under
    the protected tree, so the refusal can only come from ``os.path.samestat``,
    which needs the tree to exist and the host to serve the admin share. That
    premise is now measured and stated instead of being an invisible part of
    the assertion; when it holds, what is asserted is the code.
    """
    if os.name != "nt":
        # These are UNC / extended-UNC spellings of a Windows path. Built from a
        # POSIX root they are not the same path in another spelling, they are
        # nonsense — and the test would then measure the relative-path refusal
        # instead of `os.path.samestat`. Skipping states that honestly rather
        # than asserting a refusal that arrives for the wrong reason.
        pytest.skip("UNC alias spellings are Windows-only; identity limb not exercisable here")
    protected = _protected_365d_ba_v1()
    if not protected.is_dir():
        pytest.skip("identity limb inapplicable: no protected tree to be identical to")
    alias = _alias_spellings(str(protected))[spelling]
    candidate = resolve_candidate(alias)
    # Premise: this really is the identity limb, not the name limb in disguise.
    assert candidate != protected and protected not in candidate.parents
    try:
        aliases_the_tree = os.path.samefile(candidate, protected)
    except OSError as exc:
        pytest.skip(f"{spelling} is not reachable on this host: {exc}")
    if not aliases_the_tree:
        pytest.skip(f"{spelling} does not alias the protected tree on this host")
    with pytest.raises(RealDataRefusedError):
        refuse_real_path(alias)


def test_d1_unrelated_paths_are_still_allowed(tmp_path) -> None:
    refuse_real_path(tmp_path)
    refuse_real_path(tmp_path / "does" / "not" / "exist.json")


def test_d2_lazy_iterables_cannot_produce_a_proof_on_zero_evidence() -> None:
    """`if not files` is truthiness on the container: a generator slipped past it."""
    for lazy in ((f for f in []), iter([]), (f for f in [{"a": 1}])):
        with pytest.raises(NoOverlapError, match="concrete sequence"):
            assert_per_file_bounds(lazy, role="design")
    with pytest.raises(NoOverlapError, match="empty file list"):
        assert_per_file_bounds([], role="design")


def test_d2_non_mapping_entries_and_expected_count() -> None:
    with pytest.raises(NoOverlapError, match="must be a mapping"):
        assert_per_file_bounds(["not-a-record"] * 20, role="design")
    ok = design_roster()
    assert assert_per_file_bounds(ok, role="design")["files_checked"] == 20
    with pytest.raises(NoOverlapError, match="expected 19 files"):
        assert_per_file_bounds(ok, role="design", expected_count=19)


def test_d3_forbidden_status_as_a_dict_key_is_scrubbed() -> None:
    for payload in ({"PASS": 1}, {"PRODUCTION_READY": {"ok": 1}}, {"NEW_EPOCH_ADOPTED": "2026"}):
        with pytest.raises(ArtifactScrubError, match="forbidden_status_key"):
            assert_gate3a_clean(payload)


def test_d3_negative_declaration_is_still_allowed() -> None:
    """`production_ready: false` is a disclaimer; the committed manifests use it."""
    assert_gate3a_clean({"production_ready": False})
    assert_gate3a_clean({"byte_admissible": False, "new_epoch_adopted": False})


def test_d4_effective_n_binds_pair_identity_to_the_universe() -> None:
    with pytest.raises(EffectiveNError, match="duplicate pair"):
        effective_n(
            [_pp("USD_JPY", 800, 0.0), _pp("usd_jpy", 800, 0.0)],
            count_quantity=RAW_TRADED_EVENT_COUNT,
            cross_pair_corr=0.0,
        )
    with pytest.raises(EffectiveNError, match="PAIRS_20 universe"):
        effective_n(
            [_pp("NOT_A_PAIR", 1000, 0.0)],
            count_quantity=RAW_TRADED_EVENT_COUNT,
            cross_pair_corr=0.0,
        )
    with pytest.raises(EffectiveNError, match="PAIRS_20 universe"):
        effective_n(
            [_pp("portfolio", 10000, 0.0)],
            count_quantity=RAW_TRADED_EVENT_COUNT,
            cross_pair_corr=0.5,
        )
    canonical = effective_n(
        [_pp("usd_jpy", 1000, 0.0)], count_quantity=RAW_TRADED_EVENT_COUNT, cross_pair_corr=0.0
    )
    assert canonical["per_pair"][0]["pair"] == "USD_JPY"


def test_d5_gap_report_carries_the_canonical_pair_label() -> None:
    labels = {
        aggregate_m15(_bucket(1), pair=s)[1]["pair"]
        for s in ("USD_JPY", "usd_jpy", "USDJPY", "USD/JPY", "usd-jpy")
    }
    assert labels == {"USD_JPY"}


def test_d6_non_finite_never_reaches_the_effective_n_record() -> None:
    # §9 AP-1: the aggregate limb and the per-pair limb both say "non-finite";
    # the overflow here is in the aggregate, so the aggregate limb is named.
    with pytest.raises(EffectiveNError, match="derived effective_n is non-finite"):
        effective_n(
            [_pp(PAIRS_20[i], 10**308, 0.0) for i in range(20)],
            count_quantity=RAW_TRADED_EVENT_COUNT,
            cross_pair_corr=0.0,
        )


def test_d6_scrubber_rejects_non_finite_values(tmp_path) -> None:
    for payload in ({"effective_n": float("inf")}, {"x": float("nan")}, {"a": [1.0, float("inf")]}):
        with pytest.raises(ArtifactScrubError, match="non_finite_value"):
            assert_gate3a_clean(payload)
    written = write_metadata_artifact(tmp_path, "finite.json", {"effective_n": 383.33})
    reparsed = json.loads(
        written.read_text(encoding="utf-8"),
        parse_constant=lambda c: pytest.fail(f"non-standard JSON constant {c}"),
    )
    assert reparsed["effective_n"] == pytest.approx(383.33)


def test_d_observation_artifact_name_rejects_alternate_data_stream(tmp_path) -> None:
    with pytest.raises(ArtifactScrubError, match="bare filename"):
        write_metadata_artifact(tmp_path, "a.json:ads.json", {"ok": 1})


def test_d_observation_horizon_frozen_for_every_role() -> None:
    for role in ("holdout", "validation"):
        with pytest.raises(EffectiveNError, match="frozen at 24"):
            effective_n(
                [_pp("EUR_USD", 1000, 1.0)],
                count_quantity=RAW_TRADED_EVENT_COUNT,
                cross_pair_corr=0.0,
                role=role,
                horizon_bars=1,
            )


def test_d_observation_warmup_rejects_bool_bars() -> None:
    with pytest.raises(WarmupPolicyError):
        WarmupPolicy(w_bars=True, longest_feature_lookback_bars=1).validate()


# ==========================================================================
# RF-2 / RF-3 — audit findings from the contract role
# ==========================================================================


def _canonical_pairs_from(path: str) -> tuple[str, ...]:
    """Extract a committed PAIRS_20 literal by AST, without importing the script."""
    import ast

    from scripts.ml_step4.evidence import repo_root

    tree = ast.parse((repo_root() / path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(
            isinstance(tgt, ast.Name) and tgt.id == "PAIRS_20" for tgt in node.targets
        ):
            return tuple(el.value for el in node.value.elts)
    raise AssertionError(f"PAIRS_20 not found in {path}")


def test_rf2_pairs_20_matches_the_committed_canonical_lists() -> None:
    """The module docstring claims this test exists — so it must."""
    for path in (
        "scripts/fetch_oanda_archive.py",
        "scripts/stage23_0a_build_outcome_dataset.py",
    ):
        assert tuple(PAIRS_20) == _canonical_pairs_from(path), path


def test_rf3_magnitude_is_reported_in_pips_and_marked_unvalidated_by_default() -> None:
    """BL-5: no committed authority pins a ceiling, so none is invented here."""
    from tests.m15_gate3a.test_cost_schema import _table

    # D-10 / §12.16 makes 20x3 coverage a refusal, so the whole grid is scaled
    # rather than one outlier cell: with `pips=`, min and max observed are pinned
    # by construction instead of being whatever the filler cells happened to be.
    summary = validate_cost_table(_table(pips=(9.0, 15.0, 20.0)), max_spread_pips=None)
    assert summary["magnitude_checked_against_declared_bound"] is False
    assert summary["max_spread_pips_declared"] is None
    assert summary["magnitude_authority"] == "REQUIRES_SEPARATE_CONTRACT_GATE_DECISION"
    # The magnitude is nonetheless made visible, in each pair's own pips — the
    # same 9/15/20 pips for a JPY and a non-JPY cell, from different price units.
    assert summary["max_observed_spread_pips"] == pytest.approx(20.0)
    assert summary["min_observed_spread_pips"] == pytest.approx(9.0)


def test_bl5_pip_conversion_is_pair_aware_so_a_100x_jpy_error_is_visible() -> None:
    """The invented ceiling was `100 * pip_size`, which for JPY was 100 pips.

    ``USD_JPY median=0.9`` price units is 90 pips — a 100x unit error — and it
    passed the old ceiling. Under a caller-declared bound it is caught, and the
    same number for a non-JPY pair converts to 9000 pips, not 90.
    """
    from tests.m15_gate3a.test_cost_schema import _table

    jpy = {"pair": "USD_JPY", "pip_size": PIP_JPY}
    jpy_table = _table(entry={**jpy, "median_spread": 0.9, "p90_spread": 1.0, "p95_spread": 1.1})
    assert validate_cost_table(jpy_table, max_spread_pips=None)[
        "max_observed_spread_pips"
    ] == pytest.approx(110.0)
    with pytest.raises(CostSchemaError, match="caller-declared ceiling"):
        validate_cost_table(jpy_table, max_spread_pips=10.0)

    non_jpy = _table(entry={"median_spread": 0.9, "p90_spread": 1.0, "p95_spread": 1.1})
    assert validate_cost_table(non_jpy, max_spread_pips=None)[
        "max_observed_spread_pips"
    ] == pytest.approx(11000.0)


def test_bl5_no_invented_threshold_constant_remains_in_the_module() -> None:
    """A module-level magnitude constant would be this gate minting a contract."""
    import scripts.m15_gate3a.cost_schema as cs

    assert not hasattr(cs, "MAX_PLAUSIBLE_SPREAD_PIPS")
    numeric_constants = {
        name: getattr(cs, name)
        for name in dir(cs)
        if name.isupper() and isinstance(getattr(cs, name), (int, float))
    }
    assert set(numeric_constants) == {"EXECUTION_PADDING_PIP", "FLAT_SLIPPAGE_CELL_PIP"}


@pytest.mark.parametrize("wrong_type", [True, "5"])
def test_bl5_a_declared_bound_of_the_wrong_type_is_refused(wrong_type: object) -> None:
    """§9 AP-1: `_check_magnitude_bound` has two guards, one per class of badness.

    A bare ``"max_spread_pips"`` matcher was satisfied by either, so the single
    loop is split into two tests and each names the guard it aims at. ``bool``
    is deliberately in the type group: it is an ``int`` to Python and a
    non-number here.
    """
    from tests.m15_gate3a.test_cost_schema import _table

    with pytest.raises(CostSchemaError, match="max_spread_pips must be a number or None"):
        validate_cost_table(_table(), max_spread_pips=wrong_type)


@pytest.mark.parametrize("wrong_value", [0, -1.0, float("nan"), float("inf")])
def test_bl5_a_declared_bound_of_an_impossible_magnitude_is_refused(wrong_value: float) -> None:
    """The other guard: a number, but not a usable pip ceiling."""
    from tests.m15_gate3a.test_cost_schema import _table

    with pytest.raises(
        CostSchemaError, match="max_spread_pips must be a finite positive number of pips"
    ):
        validate_cost_table(_table(), max_spread_pips=wrong_value)


def test_bl5_zero_spread_is_accepted_because_no_committed_authority_floors_it() -> None:
    """A zero quoted spread is observable, not impossible — and no floor is minted.

    The old name and docstring argued this from the ``stage25_0a`` precedent.
    D-1.7 removes that analogy as authority: §11 of the pre-registration does not
    admit a non-family script as authority for a family-A design semantic. The
    reasoning that survives is the one this module may actually use — **no
    committed authority pins a lower magnitude bound**, so this validator may not
    invent one, exactly as it may not invent the upper ceiling (BL-5).
    """
    from tests.m15_gate3a.test_cost_schema import _table

    summary = validate_cost_table(_table(pips=(0.0, 0.0, 0.0)), max_spread_pips=None)
    assert summary["min_observed_spread_pips"] == 0.0
    assert summary["max_observed_spread_pips"] == 0.0
    assert summary["result"] == "COST_TABLE_SCHEMA_VALID"


def test_rf1_sessions_utc_tiles_the_day_exactly_once() -> None:
    from scripts.m15_gate3a.cost_schema import SESSIONS_UTC

    covered: list[int] = []
    for window in SESSIONS_UTC.values():
        lo_text, _, hi_text = window.partition("-")
        lo_h, _, lo_m = lo_text.partition(":")
        hi_h, _, hi_m = hi_text.partition(":")
        covered.extend(range(int(lo_h) * 60 + int(lo_m), int(hi_h) * 60 + int(hi_m) + 1))
    assert sorted(covered) == list(range(24 * 60))
    assert len(covered) == len(set(covered))


# RF-21: the probe run in a child interpreter under `-O`. It rewrites ONE frozen
# constant in a scratch copy of the module and imports that copy, so the
# invariant is exercised rather than read. Bare `assert` is avoided inside it for
# the same reason the module under test avoids one — `-O` would strip it.
_SPAN_INVARIANT_PROBE = """
import importlib.util
import pathlib
import sys

source_path, out_dir, old, new = sys.argv[1:5]
source = pathlib.Path(source_path).read_text(encoding="utf-8")
mutated = source.replace(old, new)
if mutated == source:
    print("MUTATION_DID_NOT_APPLY")
    raise SystemExit(3)
target = pathlib.Path(out_dir) / "no_overlap_span_probe.py"
target.write_text(mutated, encoding="utf-8")

spec = importlib.util.spec_from_file_location("no_overlap_span_probe", target)
module = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(module)
except RuntimeError as exc:
    print("REFUSED:" + str(exc))
    raise SystemExit(0) from None
print("ACCEPTED")
raise SystemExit(1)
"""

_DEAD_START_LINE = "DEAD_START: Final[datetime] = datetime(2026, 3, 1, 0, 0, 0, tzinfo=UTC)"
_FORWARD_FLOOR_LINE = "FORWARD_FLOOR: Final[datetime] = datetime(2026, 4, 25, 0, 0, 0, tzinfo=UTC)"


@pytest.mark.parametrize(
    "old,new,expected",
    [
        pytest.param(
            _DEAD_START_LINE,
            "DEAD_START: Final[datetime] = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)",
            "frozen span constants are out of order",
            id="ordering",
        ),
        pytest.param(
            _FORWARD_FLOOR_LINE,
            "FORWARD_FLOOR: Final[datetime] = datetime(2026, 4, 26, 0, 0, 0, tzinfo=UTC)",
            "dead-window end and the forward floor must be contiguous",
            id="contiguity",
        ),
    ],
)
def test_span_ordering_invariants_survive_optimised_mode(
    tmp_path, old: str, new: str, expected: str
) -> None:
    """RF-21: the invariant must be exercised, not merely present in the source.

    This asserted that the string ``raise RuntimeError("frozen span constants are
    out of order")`` **appeared in the source file** — so deleting the ``if`` that
    guards it, or making the condition unreachable, left the test green. A
    regression test that cannot fail on a revert of its own fix is not evidence.

    Behavioural form: a scratch copy of the module with one frozen constant moved
    out of order is imported in a child interpreter under ``-O``. Bare ``assert``
    is stripped by ``-O``; an explicit ``raise`` is not, and that difference is the
    whole point of the guard. Each invariant is a separate parameter with its own
    expected message, so neither can pass because the other one fired.
    """
    import subprocess
    import sys

    from scripts.ml_step4.evidence import repo_root

    module_path = repo_root() / "scripts" / "m15_gate3a" / "no_overlap.py"
    proc = subprocess.run(
        [
            sys.executable,
            "-O",
            "-c",
            _SPAN_INVARIANT_PROBE,
            str(module_path),
            str(tmp_path),
            old,
            new,
        ],
        cwd=repo_root(),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    assert proc.stdout.startswith("REFUSED:"), proc.stdout
    assert expected in proc.stdout


def test_the_unmutated_span_constants_import_cleanly_under_optimised_mode() -> None:
    """Control for the probe above: both verdicts must occur, or it proves nothing."""
    import subprocess
    import sys

    from scripts.ml_step4.evidence import repo_root

    proc = subprocess.run(
        [
            sys.executable,
            "-O",
            "-c",
            "import scripts.m15_gate3a.no_overlap as m; print(m.DEAD_END)",
        ],
        cwd=repo_root(),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_artifact_name_needs_a_non_empty_stem(tmp_path) -> None:
    for bad in (".json", "..json", "  .json"):
        with pytest.raises(ArtifactScrubError):
            write_metadata_artifact(tmp_path, bad, {"ok": 1})


def test_validation_raw_floor_must_be_integral() -> None:
    with pytest.raises(EffectiveNError, match="must be an integer"):
        effective_n(
            [_pp("EUR_USD", 10, 0.0)],
            count_quantity=RAW_TRADED_EVENT_COUNT,
            cross_pair_corr=0.0,
            role="validation",
            validation_raw_floor=1.5,
            validation_neff_floor=1.0,
        )
