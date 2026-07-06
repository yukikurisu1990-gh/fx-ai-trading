"""M1->M15 aggregation tests — synthetic rows only, value-pinned pip scaling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from scripts.m15_gate3a.aggregation import (
    AggregationError,
    aggregate_m15,
    to_pips,
)
from scripts.ml_step4.data_adapter import PipSizeError


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


def _bucket(start: datetime, n: int) -> list[dict]:
    return [_m1(start + timedelta(minutes=i), base=1.10 + i * 0.0001) for i in range(n)]


def test_fifteen_rows_one_eligible_bucket() -> None:
    start = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
    bars, gap = aggregate_m15(_bucket(start, 15), pair="EUR_USD")
    assert len(bars) == 1
    b = bars[0]
    assert b["n_source_bars"] == 15
    assert b["eligible"] is True
    assert b["ts"] == start
    assert gap["n_eligible"] == 1 and gap["n_incomplete"] == 0
    # per-side OHLC (open=first, close=last, high=max, low=min); no mid.
    assert b["bid_o"] == _m1(start, base=1.10)["bid_o"]
    assert "mid" not in b and "open" not in b and "close" not in b
    assert gap["mid_price_constructed"] is False


def test_fewer_than_15_incomplete_not_eligible() -> None:
    start = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
    bars, gap = aggregate_m15(_bucket(start, 9), pair="EUR_USD")
    assert bars[0]["n_source_bars"] == 9
    assert bars[0]["eligible"] is False
    assert gap["n_incomplete"] == 1 and gap["n_eligible"] == 0


def test_missing_minute_incomplete_no_imputation() -> None:
    start = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
    rows = _bucket(start, 15)
    del rows[7]  # drop one minute
    bars, gap = aggregate_m15(rows, pair="EUR_USD")
    assert bars[0]["n_source_bars"] == 14
    assert bars[0]["eligible"] is False
    assert gap["imputation"] is False
    assert gap["total_missing_source_minutes_within_emitted_buckets"] == 1


def test_utc_boundary_splits_buckets() -> None:
    a = datetime(2025, 6, 2, 0, 14, tzinfo=UTC)
    b = datetime(2025, 6, 2, 0, 15, tzinfo=UTC)
    bars, _ = aggregate_m15([_m1(a), _m1(b)], pair="EUR_USD")
    assert len(bars) == 2
    assert bars[0]["ts"] == datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
    assert bars[1]["ts"] == datetime(2025, 6, 2, 0, 15, tzinfo=UTC)


def test_weekend_gap_no_synthetic_bars() -> None:
    fri = datetime(2025, 5, 30, 20, 45, tzinfo=UTC)  # Friday
    mon = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)  # Monday
    bars, gap = aggregate_m15([_m1(fri), _m1(mon)], pair="EUR_USD")
    # Only the two windows that actually contain minutes are emitted; the whole
    # weekend produces no fabricated bars.
    assert len(bars) == 2
    assert gap["synthetic_weekend_bars"] is False
    assert gap["missing_whole_buckets"] > 0  # counted, not fabricated


def test_jpy_pip_conversion_value_pinned() -> None:
    assert to_pips(0.10, "USD_JPY") == pytest.approx(10.0)  # 0.01 pip
    start = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
    bars, _ = aggregate_m15(_bucket(start, 15), pair="USD_JPY")
    assert bars[0]["pip_size"] == 0.01


def test_non_jpy_pip_conversion_value_pinned() -> None:
    assert to_pips(0.0010, "EUR_USD") == pytest.approx(10.0)  # 0.0001 pip
    # Same raw 0.10 move is 100x more pips for a non-JPY pair than a JPY pair.
    assert to_pips(0.10, "EUR_USD") == pytest.approx(1000.0)
    assert to_pips(0.10, "USD_JPY") * 100 == pytest.approx(to_pips(0.10, "EUR_USD"))
    start = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
    bars, _ = aggregate_m15(_bucket(start, 15), pair="EUR_USD")
    assert bars[0]["pip_size"] == 0.0001


def test_unknown_pair_fails_closed() -> None:
    with pytest.raises(PipSizeError):
        aggregate_m15(_bucket(datetime(2025, 6, 2, tzinfo=UTC), 15), pair="")


def test_naive_timestamp_fails_closed() -> None:
    with pytest.raises(AggregationError):
        aggregate_m15([_m1(datetime(2025, 6, 2, 0, 0))], pair="EUR_USD")  # naive ts


def test_more_than_15_source_bars_fails_closed() -> None:
    start = datetime(2025, 6, 2, 0, 0, tzinfo=UTC)
    rows = _bucket(start, 15) + [_m1(start)]  # 16 rows in one bucket
    with pytest.raises(AggregationError):
        aggregate_m15(rows, pair="EUR_USD")
