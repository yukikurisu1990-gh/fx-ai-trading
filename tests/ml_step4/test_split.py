"""Deterministic split builder tests (synthetic timestamp metadata)."""

from __future__ import annotations

import pytest

from scripts.ml_step4 import split
from scripts.ml_step4.split import PairWindow, SplitError, build_split, common_window


def _windows() -> list[PairWindow]:
    # Three pairs with slightly different vintages; common window is the overlap.
    return [
        PairWindow("a", "2025-01-01T00:00:00Z", "2026-01-10T00:00:00Z"),
        PairWindow("b", "2025-01-02T00:00:00Z", "2026-01-05T00:00:00Z"),
        PairWindow("c", "2025-01-03T00:00:00Z", "2026-01-08T00:00:00Z"),
    ]


def test_common_window_is_overlap() -> None:
    start, end = common_window(_windows())
    assert start.isoformat() == "2025-01-03T00:00:00+00:00"  # max of mins
    assert end.isoformat() == "2026-01-05T00:00:00+00:00"  # min of maxs


def test_build_split_deterministic() -> None:
    a = build_split(_windows())
    b = build_split(_windows())
    assert a == b


def test_split_fractions_and_ordering() -> None:
    out = build_split(_windows())
    seg = out["segments"]
    assert out["fractions"] == {"train": 0.70, "validation": 0.15, "holdout": 0.15}
    assert out["purge_embargo_bars"] == 21
    # Chronological, non-overlapping segment order.
    assert (
        seg["train"]["start_utc"]
        < seg["train"]["end_utc"]
        == seg["validation"]["start_utc"]
        < seg["validation"]["end_utc"]
        == seg["holdout"]["start_utc"]
        < seg["holdout"]["end_utc"]
    )


def test_purge_reduces_label_eligible_end() -> None:
    out = build_split(_windows())
    seg = out["segments"]
    # Label-eligible end is strictly before the segment end (purge applied).
    assert seg["train"]["label_eligible_end_utc"] < seg["train"]["end_utc"]
    assert seg["validation"]["label_eligible_end_utc"] < seg["validation"]["end_utc"]
    assert seg["holdout"]["evaluated_once"] is True


def test_fail_closed_on_no_overlap() -> None:
    bad = [
        PairWindow("a", "2025-01-01T00:00:00Z", "2025-02-01T00:00:00Z"),
        PairWindow("b", "2025-03-01T00:00:00Z", "2025-04-01T00:00:00Z"),
    ]
    with pytest.raises(SplitError):
        build_split(bad)


def test_fail_closed_on_unparseable_timestamp() -> None:
    with pytest.raises(SplitError):
        common_window([PairWindow("a", "not-a-date", "2026-01-01T00:00:00Z")])


def test_fail_closed_on_naive_timestamp() -> None:
    with pytest.raises(SplitError):
        common_window([PairWindow("a", "2025-01-01T00:00:00", "2026-01-01T00:00:00Z")])


def test_fail_closed_on_bad_fractions() -> None:
    with pytest.raises(SplitError):
        build_split(_windows(), fractions=(0.5, 0.3, 0.3))


def test_fail_closed_on_window_too_short_for_purge() -> None:
    tiny = [PairWindow("a", "2025-01-01T00:00:00Z", "2025-01-01T00:30:00Z")]
    with pytest.raises(SplitError):
        build_split(tiny, purge_bars=21)


def test_module_exposes_bar_seconds() -> None:
    assert split._BAR_SECONDS == 60


# --- PR #411 R-1: bar-granularity boundary rule -----------------------------


def test_r1_bar_index_split_boundaries() -> None:
    from scripts.ml_step4.split import bar_index_split

    out = bar_index_split(1000)
    seg = out["segments"]
    assert out["granularity"] == "m1_bar_index"
    assert out["purge_embargo_bars"] == 21
    assert seg["train"]["start_index"] == 0
    assert seg["train"]["end_index_exclusive"] == 700
    assert seg["train"]["label_eligible_end_index_exclusive"] == 679  # 700 - 21
    assert seg["validation"]["start_index"] == 700
    assert seg["validation"]["end_index_exclusive"] == 850
    assert seg["validation"]["label_eligible_end_index_exclusive"] == 829
    assert seg["holdout"]["start_index"] == 850
    assert seg["holdout"]["end_index_exclusive"] == 1000
    assert seg["holdout"]["evaluated_once"] is True


def test_r1_end_exclusive_no_overlap() -> None:
    from scripts.ml_step4.split import bar_index_split

    seg = bar_index_split(1000)["segments"]
    # end-exclusive: validation starts exactly where train ends (no shared bar).
    assert seg["train"]["end_index_exclusive"] == seg["validation"]["start_index"]
    assert seg["validation"]["end_index_exclusive"] == seg["holdout"]["start_index"]


def test_r1_off_by_one_small_n() -> None:
    from scripts.ml_step4.split import SplitError, bar_index_split

    with pytest.raises(SplitError):
        bar_index_split(10)  # too small for purge=21


def test_r1_m1_alignment_rejects_non_aligned() -> None:
    from scripts.ml_step4.split import SplitError, assert_m1_aligned

    assert_m1_aligned("2025-04-25T17:09:00Z")  # aligned, no raise
    with pytest.raises(SplitError):
        assert_m1_aligned("2025-04-25T17:09:30Z")  # :30 seconds -> not M1-aligned


def test_r1_purge_is_horizon_plus_one() -> None:
    from scripts.ml_step4 import contract
    from scripts.ml_step4.split import bar_index_split

    out = bar_index_split(5000, purge_bars=contract.PURGE_EMBARGO_BARS)
    seg = out["segments"]
    gap = seg["train"]["end_index_exclusive"] - seg["train"]["label_eligible_end_index_exclusive"]
    assert gap == 21 == contract.HORIZON_M1_BARS + 1
