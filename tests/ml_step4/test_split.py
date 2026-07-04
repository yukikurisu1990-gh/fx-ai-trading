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
