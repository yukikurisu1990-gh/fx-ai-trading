"""Regression tests for the PR #439 re-check blockers B-1..B-5 and fixes R-1..R-10.

Every test here encodes a defect that was probe-CONFIRMED against the pre-fix
merged source (master 697a1cf): each fails before the corresponding fix and
passes after. Synthetic literals only — no real data, no network, no file reads
outside pytest's ``tmp_path``.

Expected values are restated from the frozen contract and the committed
APPROVED specs, never re-derived from the implementation.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta, timezone

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
    NoOverlapError,
    assert_design_bounds,
    assert_forward_bounds,
    assert_no_dead_window,
    assert_per_file_bounds,
)
from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair
from scripts.m15_gate3a.warmup import WarmupPolicy, WarmupPolicyError

pd = pytest.importorskip("pandas")

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


def test_b1_pandas_timestamp_nanosecond_rejected() -> None:
    ts = pd.Timestamp("2025-06-02 00:00:00.000000500+0000")
    # Guard the premise: the ns is invisible to the fields the old check read.
    assert ts.second == 0 and ts.microsecond == 0 and ts.nanosecond == 500
    with pytest.raises(AggregationError, match="minute-aligned|sub-microsecond"):
        aggregate_m15([_row(ts)], pair="EUR_USD")


def test_b1_fifteen_all_nanosecond_rows_are_rejected_not_eligible() -> None:
    """Pre-fix this produced ONE eligible bar at a non-15-minute bucket start."""
    base = pd.Timestamp("2025-06-02 00:00:00+0000")
    rows = [_row(base + pd.Timedelta(minutes=i) + pd.Timedelta(nanoseconds=500)) for i in range(15)]
    with pytest.raises(AggregationError):
        aggregate_m15(rows, pair="EUR_USD")


def test_b1_same_minute_ns0_and_ns500_cannot_make_two_eligible_bars() -> None:
    """Pre-fix this produced TWO eligible bars for one 15-minute window."""
    base = pd.Timestamp("2025-06-02 00:00:00+0000")
    rows = [_row(base + pd.Timedelta(minutes=i)) for i in range(15)]
    rows += [
        _row(base + pd.Timedelta(minutes=i) + pd.Timedelta(nanoseconds=500)) for i in range(15)
    ]
    with pytest.raises(AggregationError):
        aggregate_m15(rows, pair="EUR_USD")


def test_b1_single_sub_minute_row_among_aligned_rows_rejected() -> None:
    base = pd.Timestamp("2025-06-02 00:00:00+0000")
    rows = [_row(base + pd.Timedelta(minutes=i)) for i in range(15)]
    rows.append(_row(base + pd.Timedelta(minutes=5) + pd.Timedelta(nanoseconds=1)))
    with pytest.raises(AggregationError):
        aggregate_m15(rows, pair="EUR_USD")


def test_b1_aligned_pandas_timestamps_are_accepted_and_bucket_is_plain_utc() -> None:
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
    assert gap["n_eligible"] == 1


def test_b1_timezone_aware_pandas_timestamp_normalised_to_utc() -> None:
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
    with pytest.raises(AggregationError, match="high|incoherent"):
        aggregate_m15(rows, pair="EUR_USD")


def test_r2_crossed_quote_rejected_no_negative_spread() -> None:
    """Each side is internally coherent, but ask sits below bid -> crossed."""
    rows = _bucket(15)
    crossed = _row(START + timedelta(minutes=14))
    for k in ("o", "h", "l", "c"):
        crossed[f"ask_{k}"] = crossed[f"bid_{k}"] - 0.0001
    rows[14] = crossed
    with pytest.raises(AggregationError, match="crossed quote"):
        aggregate_m15(rows, pair="EUR_USD")


def test_r6_finite_inputs_producing_infinite_spread_rejected() -> None:
    """Row is finite, per-side coherent and un-crossed; only the DERIVED spread overflows."""
    row = {"ts": START}
    for k in ("o", "h", "l", "c"):
        row[f"bid_{k}"] = -1.7e308
        row[f"ask_{k}"] = 1.7e308
    assert all(math.isfinite(v) for k, v in row.items() if k != "ts")
    assert math.isinf(row["ask_c"] - row["bid_c"])  # the overflow the guard must catch
    with pytest.raises(AggregationError, match="non-finite"):
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


# ==========================================================================
# R-7 — gap report is minute-granular and uses the committed schema key
# ==========================================================================


def test_r7_minute_level_gap_is_reported() -> None:
    _, gap = aggregate_m15([_row(START), _row(START + timedelta(minutes=29))], pair="EUR_USD")
    assert gap["missing_minute_count"] == 28
    assert gap["max_gap_minutes"] == 28  # pre-fix this was 0
    assert gap["imputation"] is False
    assert gap["synthetic_weekend_bars"] is False
    assert gap["mid_price_constructed"] is False


def test_r7_whole_bucket_gap_still_counted() -> None:
    rows = _bucket(15) + [_row(START + timedelta(minutes=45))]
    _, gap = aggregate_m15(rows, pair="EUR_USD")
    assert gap["missing_whole_buckets"] == 2
    assert gap["max_gap_minutes"] == 30


# ==========================================================================
# B-2 — no-overlap bounds
# ==========================================================================


def test_b2_reversed_span_rejected_by_per_file_bounds() -> None:
    files = [{"ts_min_utc": "2026-05-01T00:00:00Z", "ts_max_utc": "2026-03-15T00:00:00Z"}]
    with pytest.raises(NoOverlapError, match="reversed span"):
        assert_per_file_bounds(files, role="forward")


def test_b2_reversed_span_rejected_by_each_bound_checker() -> None:
    with pytest.raises(NoOverlapError, match="reversed span"):
        assert_forward_bounds("2026-05-01T00:00:00Z", "2026-01-01T00:00:00Z")
    with pytest.raises(NoOverlapError, match="reversed span"):
        assert_design_bounds("2026-01-01T00:00:00Z", "2025-06-01T00:00:00Z")
    with pytest.raises(NoOverlapError, match="reversed span"):
        assert_no_dead_window("2026-05-01T00:00:00Z", "2026-01-01T00:00:00Z", role="probe")


def test_b2_span_containing_dead_window_never_proven() -> None:
    files = [{"ts_min_utc": "2026-01-01T00:00:00Z", "ts_max_utc": "2026-05-01T00:00:00Z"}]
    with pytest.raises(NoOverlapError):
        assert_per_file_bounds(files, role="forward")


def test_b2_boundary_constants_pinned_independently() -> None:
    assert_design_bounds(DESIGN_START_S, DESIGN_END_S)  # inclusive both ends
    with pytest.raises(NoOverlapError):
        assert_design_bounds(DESIGN_START_S, DEAD_START_S)
    with pytest.raises(NoOverlapError):
        assert_design_bounds("2025-04-24T23:59:59+00:00", DESIGN_END_S)
    assert_forward_bounds(FORWARD_FLOOR_S, "2026-06-01T00:00:00+00:00")
    with pytest.raises(NoOverlapError):
        assert_forward_bounds(DEAD_END_S, "2026-06-01T00:00:00+00:00")
    with pytest.raises(NoOverlapError, match="dead window"):
        assert_no_dead_window(DEAD_START_S, DEAD_START_S, role="probe")
    with pytest.raises(NoOverlapError, match="dead window"):
        assert_no_dead_window(DEAD_END_S, DEAD_END_S, role="probe")


def test_b2_sub_second_tail_of_dead_window_is_dead() -> None:
    """O-3 sliver, closed conservatively without moving any published constant."""
    with pytest.raises(NoOverlapError, match="dead window"):
        assert_no_dead_window(
            "2026-04-24T23:59:59.500000+00:00", "2026-06-01T00:00:00+00:00", role="probe"
        )
    # The forward floor itself remains clean.
    assert_no_dead_window(FORWARD_FLOOR_S, "2026-06-01T00:00:00+00:00", role="probe")


def test_b2_valid_design_file_still_proven() -> None:
    files = [{"ts_min_utc": "2025-05-01T00:00:00Z", "ts_max_utc": "2025-06-01T00:00:00Z"}]
    assert assert_per_file_bounds(files, role="design")["result"] == (
        "PROVEN_NO_DEAD_WINDOW_OVERLAP"
    )


# ==========================================================================
# B-3 / B-5 / R-1 — effective-N
# ==========================================================================


def _pp(pair: str, raw: int, overlap: float) -> dict:
    return {"pair": pair, "raw_event_count": raw, "overlap_fraction": overlap}


def test_b3_audited_counterexample_is_insufficient() -> None:
    r = effective_n([_pp("A", 50, 0.0), _pp("B", 8000, 1.0)], cross_pair_corr=0.0)
    assert r["effective_n"] == pytest.approx(383.3333333, rel=1e-6)
    assert r["verdict"] == INSUFFICIENT_SAMPLE


def test_b3_per_pair_granularity_reported() -> None:
    r = effective_n([_pp("A", 100, 0.0), _pp("B", 200, 0.5)], cross_pair_corr=0.0)
    assert [p["pair"] for p in r["per_pair"]] == ["A", "B"]
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
            [_pp("A", 0, 0.0)],
            cross_pair_corr=0.0,
            role="validation",
            validation_raw_floor=raw_floor,
            validation_neff_floor=neff_floor,
        )


def test_b5_zero_events_never_sufficient() -> None:
    r = effective_n(
        [_pp("A", 0, 0.0)],
        cross_pair_corr=0.0,
        role="validation",
        validation_raw_floor=1,
        validation_neff_floor=1.0,
    )
    assert r["verdict"] == INSUFFICIENT_SAMPLE
    assert r["verdict"] != SUFFICIENT


def test_r1_horizon_override_rejected_at_holdout_and_echoed() -> None:
    with pytest.raises(EffectiveNError, match="frozen at 24"):
        effective_n([_pp("A", 1000, 1.0)], cross_pair_corr=0.0, horizon_bars=1)
    r = effective_n([_pp("A", 1000, 1.0)], cross_pair_corr=0.0)
    assert r["horizon_bars"] == 24
    assert r["verdict"] == INSUFFICIENT_SAMPLE
    assert r["floors_applied"] == {"raw_floor": 1000.0, "neff_floor": 400.0}


# ==========================================================================
# B-4 — pair authority
# ==========================================================================


def test_b4_pairs_20_universe_matches_canonical_list() -> None:
    assert len(PAIRS_20) == 20 and len(set(PAIRS_20)) == 20
    assert "USD_JPY" in PAIRS_20 and "EUR_USD" in PAIRS_20


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

    with pytest.raises(CostSchemaError, match="canonical"):
        validate_cost_table(_table(entry={"pair": "usd_jpy", "pip_size": 0.01}))


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
        validate_cost_table(t)
    with pytest.raises(CostSchemaError, match="spread_unit"):
        validate_cost_table(_cost_table(spread_unit="pip"))
    assert validate_cost_table(_cost_table())["spread_unit"] == "price"


def test_r8_formula_string_must_match_the_frozen_plan() -> None:
    with pytest.raises(CostSchemaError, match="all_in_cost_formula"):
        validate_cost_table(_cost_table(all_in_cost_formula="median + 0.0 + 0.0"))


def test_r8_quantiles_must_be_monotone() -> None:
    with pytest.raises(CostSchemaError, match="median <= p90 <= p95"):
        validate_cost_table(
            _cost_table(entry={"median_spread": 0.0009, "p90_spread": 0.0002, "p95_spread": 0.0001})
        )
    with pytest.raises(CostSchemaError, match="median <= p90 <= p95"):
        validate_cost_table(
            _cost_table(
                entry={"median_spread": 0.00008, "p90_spread": 0.0003, "p95_spread": 0.0002}
            )
        )


def test_r8_padding_and_cell_remain_unloosenable() -> None:
    with pytest.raises(CostSchemaError):
        validate_cost_table(_cost_table(execution_padding_pip=0.31))
    with pytest.raises(CostSchemaError):
        validate_cost_table(_cost_table(flat_slippage_cell_pip=0.51))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), -1.0, True])
@pytest.mark.parametrize("stat", ["median_spread", "p90_spread", "p95_spread"])
def test_r8_non_finite_negative_and_bool_spreads_rejected(stat: str, bad) -> None:
    with pytest.raises(CostSchemaError):
        validate_cost_table(_cost_table(entry={stat: bad}))


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


def test_r5_columnar_and_array_rows_rejected() -> None:
    with pytest.raises(ArtifactScrubError, match="columnar|row_like"):
        assert_gate3a_clean({"o": [1.1] * 50, "h": [1.2] * 50, "l": [1.0] * 50, "c": [1.15] * 50})
    with pytest.raises(ArtifactScrubError, match="row_like_numeric_arrays"):
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
    import json

    from scripts.ml_step4.evidence import repo_root

    for path in sorted((repo_root() / "artifacts" / "m15_gate3a").glob("*.json")):
        assert_gate3a_clean(json.loads(path.read_text(encoding="utf-8")))
