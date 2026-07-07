"""Regression tests for the PR #433 source-audit findings F-1..F-5 (+ O-1/O-2).

Each F-test encodes a probe that CONFIRMED a defect in the pre-fix machinery;
all would fail before the targeted fixes and must pass after. Synthetic
literals only — no real data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scripts.m15_gate3a.aggregation import AggregationError, aggregate_m15
from scripts.m15_gate3a.artifacts import ArtifactScrubError, assert_gate3a_clean
from scripts.m15_gate3a.cost_schema import CostSchemaError, validate_cost_table
from scripts.m15_gate3a.effective_n import (
    INSUFFICIENT_SAMPLE,
    NOT_EVALUATED,
    SUFFICIENT,
    EffectiveNError,
    effective_n,
)
from scripts.m15_gate3a.guards import RealDataRefusedError, assert_status_allowed
from scripts.m15_gate3a.no_overlap import NoOverlapError, assert_design_bounds
from scripts.m15_gate3a.warmup import WarmupPolicy, WarmupPolicyError


def _m1(ts: datetime, base: float = 1.10, half: float = 0.00005) -> dict:
    return {
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


_START = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)


def _bucket(n: int) -> list[dict]:
    return [_m1(_START + timedelta(minutes=i)) for i in range(n)]


# --------------------------------------------------------------------------
# F-1: duplicate-minute / sub-minute rows must never create eligibility
# --------------------------------------------------------------------------


def test_f1_duplicate_minute_fails_closed() -> None:
    rows = _bucket(14)
    rows.append(_m1(_START + timedelta(minutes=5)))  # duplicate minute 5 -> 15 rows
    with pytest.raises(AggregationError, match="duplicate source minute"):
        aggregate_m15(rows, pair="EUR_USD")


def test_f1_sub_minute_timestamp_fails_closed() -> None:
    rows = _bucket(14)
    rows.append(_m1(_START + timedelta(minutes=5, seconds=30)))  # not minute-aligned
    with pytest.raises(AggregationError, match="not minute-aligned"):
        aggregate_m15(rows, pair="EUR_USD")


def test_f1_fifteen_distinct_minutes_still_eligible() -> None:
    bars, gap = aggregate_m15(_bucket(15), pair="EUR_USD")
    assert bars[0]["n_source_bars"] == 15
    assert bars[0]["eligible"] is True
    assert gap["n_eligible"] == 1


def test_f1_missing_minute_not_eligible() -> None:
    rows = _bucket(15)
    del rows[7]
    bars, gap = aggregate_m15(rows, pair="EUR_USD")
    assert bars[0]["n_source_bars"] == 14
    assert bars[0]["eligible"] is False
    assert gap["total_missing_source_minutes_within_emitted_buckets"] == 1


# --------------------------------------------------------------------------
# F-2: non-finite prices must fail closed before any output exists
# --------------------------------------------------------------------------


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
@pytest.mark.parametrize("key", ["bid_o", "bid_h", "ask_l", "ask_c"])
def test_f2_non_finite_price_fails_closed(bad: float, key: str) -> None:
    rows = _bucket(15)
    rows[3][key] = bad
    with pytest.raises(AggregationError, match="non-finite"):
        aggregate_m15(rows, pair="EUR_USD")


def test_f2_finite_values_still_pass() -> None:
    bars, _ = aggregate_m15(_bucket(15), pair="EUR_USD")
    assert bars[0]["eligible"] is True


def test_f2_bool_price_fails_closed() -> None:
    rows = _bucket(15)
    rows[0]["bid_h"] = True  # bool is not a price
    with pytest.raises(AggregationError, match="must be numeric"):
        aggregate_m15(rows, pair="EUR_USD")


# --------------------------------------------------------------------------
# F-3: effective-N role handling fail-closed
# --------------------------------------------------------------------------


def test_f3_unknown_role_raises() -> None:
    with pytest.raises(EffectiveNError, match="unknown role"):
        effective_n(1000, overlap_fraction=0.0, cross_pair_corr=0.0, n_pairs=1, role="bogus")


def test_f3_validation_not_default_sufficient() -> None:
    r = effective_n(5, overlap_fraction=0.0, cross_pair_corr=0.0, n_pairs=1, role="validation")
    assert r["verdict"] == NOT_EVALUATED
    assert r["verdict"] != SUFFICIENT


def test_f3_validation_with_explicit_floors_applies_them() -> None:
    low = effective_n(
        5,
        overlap_fraction=0.0,
        cross_pair_corr=0.0,
        n_pairs=1,
        role="validation",
        validation_raw_floor=100,
    )
    assert low["verdict"] == INSUFFICIENT_SAMPLE
    ok = effective_n(
        500,
        overlap_fraction=0.0,
        cross_pair_corr=0.0,
        n_pairs=1,
        role="validation",
        validation_raw_floor=100,
        validation_neff_floor=100.0,
    )
    assert ok["verdict"] == SUFFICIENT


def test_f3_holdout_floors_unchanged() -> None:
    assert (
        effective_n(900, overlap_fraction=0.0, cross_pair_corr=0.0, n_pairs=1)["verdict"]
        == INSUFFICIENT_SAMPLE
    )
    low_eff = effective_n(1200, overlap_fraction=0.9, cross_pair_corr=0.5, n_pairs=20)
    assert low_eff["effective_n"] < 400 and low_eff["verdict"] == INSUFFICIENT_SAMPLE
    assert (
        effective_n(5000, overlap_fraction=0.0, cross_pair_corr=0.0, n_pairs=20)["verdict"]
        == SUFFICIENT
    )


# --------------------------------------------------------------------------
# F-4: non-finite spreads must fail closed in the cost schema
# --------------------------------------------------------------------------


def _table(entry_overrides: dict) -> dict:
    entry = {
        "pair": "EUR_USD",
        "session": "europe",
        "median_spread": 0.00008,
        "p90_spread": 0.00015,
        "p95_spread": 0.00020,
        "pip_size": 0.0001,
    }
    entry.update(entry_overrides)
    return {
        "execution_padding_pip": 0.3,
        "flat_slippage_cell_pip": 0.5,
        "all_in_cost_formula": "median + 0.3 + 0.5",
        "claim_scope": "quote_cost_validity",
        "entries": [entry],
    }


def test_f4_nan_median_fails() -> None:
    with pytest.raises(CostSchemaError, match="finite"):
        validate_cost_table(_table({"median_spread": float("nan")}))


def test_f4_inf_p90_fails() -> None:
    with pytest.raises(CostSchemaError, match="finite"):
        validate_cost_table(_table({"p90_spread": float("inf")}))


def test_f4_neg_inf_p95_fails() -> None:
    with pytest.raises(CostSchemaError, match="finite"):
        validate_cost_table(_table({"p95_spread": float("-inf")}))


def test_f4_finite_non_negative_pass_and_missing_p95_still_fails() -> None:
    assert validate_cost_table(_table({}))["result"] == "COST_TABLE_SCHEMA_VALID"
    t = _table({})
    del t["entries"][0]["p95_spread"]
    with pytest.raises(CostSchemaError):
        validate_cost_table(t)


# --------------------------------------------------------------------------
# F-5: naive datetimes / offset-less ISO strings must fail closed
# --------------------------------------------------------------------------


def test_f5_naive_datetime_rejected_in_no_overlap() -> None:
    with pytest.raises(NoOverlapError, match="naive"):
        assert_design_bounds(datetime(2025, 5, 1), datetime(2025, 12, 31, tzinfo=UTC))


def test_f5_offsetless_iso_string_rejected() -> None:
    with pytest.raises(NoOverlapError, match="without explicit offset"):
        assert_design_bounds("2025-05-01T00:00:00", "2025-12-31T00:00:00Z")


def test_f5_z_and_offset_timestamps_pass() -> None:
    assert_design_bounds("2025-05-01T00:00:00Z", "2025-12-31T00:00:00+00:00")


def test_f5_non_utc_offset_converted_not_misread() -> None:
    # 2026-02-28T20:00:00-05:00 == 2026-03-01T01:00:00Z -> inside the dead
    # window -> must FAIL design bounds (correct conversion, not naive misread).
    with pytest.raises(NoOverlapError):
        assert_design_bounds("2025-05-01T00:00:00Z", "2026-02-28T20:00:00-05:00")
    # 2026-02-28T18:00:00-05:00 == 2026-02-28T23:00:00Z -> within design -> pass.
    assert_design_bounds("2025-05-01T00:00:00Z", "2026-02-28T18:00:00-05:00")


def test_f5_naive_rejected_in_warmup() -> None:
    p = WarmupPolicy(w_bars=50, longest_feature_lookback_bars=50)
    with pytest.raises(WarmupPolicyError, match="naive"):
        p.assert_load_allowed(datetime(2026, 5, 1))
    with pytest.raises(WarmupPolicyError, match="without offset"):
        p.assert_load_allowed("2026-05-01T00:00:00")
    p.assert_load_allowed("2026-05-01T00:00:00Z")  # explicit UTC still allowed


# --------------------------------------------------------------------------
# O-1: status normalisation (casing / whitespace variants refused)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "variant",
    ["new_epoch_adopted", "NEW_EPOCH_ADOPTED ", " Byte_Admissible", "production_ready", "meets"],
)
def test_o1_status_variants_refused(variant: str) -> None:
    with pytest.raises(RealDataRefusedError):
        assert_status_allowed(variant)


def test_o1_allowed_status_still_ok() -> None:
    assert_status_allowed("M15_AGGREGATION_DATASET_MACHINERY_TARGETED_FIXES_PROPOSED")


# --------------------------------------------------------------------------
# O-2: row-like numeric-record heuristic (conservative)
# --------------------------------------------------------------------------


def test_o2_full_ba_rows_under_generic_key_rejected() -> None:
    row = {
        "a": 1.1,
        "b": 1.2,
        "c": 1.0,
        "d": 1.15,
        "e": 1.11,
        "f": 1.21,
        "g": 1.01,
        "h": 1.16,
    }  # 8 numeric fields, row-like
    with pytest.raises(ArtifactScrubError, match="row_like"):
        assert_gate3a_clean({"data": [row, dict(row)]})


def test_o2_legitimate_metadata_survives() -> None:
    # Cost-table-like entries (4 numeric fields) and inventory-like records
    # (<= 4 numeric) must NOT trip the heuristic.
    cost_entries = [
        {
            "pair": "EUR_USD",
            "session": "europe",
            "median_spread": 0.00008,
            "p90_spread": 0.00015,
            "p95_spread": 0.0002,
            "pip_size": 0.0001,
        }
    ] * 3
    inventory = [
        {"filename": "x.jsonl", "sha256": "ab" * 32, "size_bytes": 100, "row_count": 5}
    ] * 3
    assert_gate3a_clean({"entries": cost_entries})
    assert_gate3a_clean({"files": inventory})
