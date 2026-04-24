"""Unit tests: ``CandleFileBarFeed``.

Contract:
  - Yields one ``Candle`` per OHLCV line in file order.
  - Candle fields (o/h/l/c/volume/time) are correctly parsed.
  - Two feeds backed by the same file produce identical sequences (determinism).
  - StopIteration (exhaustion) on EOF — no re-emission.
  - Raises ``ReplayDataError`` on missing required fields or malformed JSON.
  - Skips blank lines without error.
  - instrument / granularity tags are applied from constructor, not file.
  - Nanosecond-precision RFC3339 ``Z``-suffix timestamps are parsed to UTC.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fx_ai_trading.adapters.price_feed.candle_file_bar_feed import CandleFileBarFeed
from fx_ai_trading.adapters.price_feed.replay_quote_feed import ReplayDataError
from fx_ai_trading.domain.price_feed import Candle


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line) + "\n")


_CANDLE_A = {
    "time": "2026-04-23T20:00:00.000000000Z",
    "o": 1.16800,
    "h": 1.16810,
    "l": 1.16795,
    "c": 1.16802,
    "volume": 17,
}
_CANDLE_B = {
    "time": "2026-04-23T20:05:00.000000000Z",
    "o": 1.16802,
    "h": 1.16820,
    "l": 1.16800,
    "c": 1.16815,
    "volume": 23,
}


class TestCandleFileBarFeedContract:
    def test_yields_candle_per_line(self, tmp_path: Path) -> None:
        f = tmp_path / "bars.jsonl"
        _write_jsonl(f, [_CANDLE_A, _CANDLE_B])
        bars = list(CandleFileBarFeed(f, instrument="EUR_USD", granularity="M5"))
        assert len(bars) == 2
        assert all(isinstance(b, Candle) for b in bars)

    def test_fields_parsed_correctly(self, tmp_path: Path) -> None:
        f = tmp_path / "bars.jsonl"
        _write_jsonl(f, [_CANDLE_A])
        bar = next(iter(CandleFileBarFeed(f, instrument="EUR_USD", granularity="M5")))
        assert bar.open == pytest.approx(1.168)
        assert bar.high == pytest.approx(1.1681)
        assert bar.low == pytest.approx(1.16795)
        assert bar.close == pytest.approx(1.16802)
        assert bar.volume == 17
        assert bar.instrument == "EUR_USD"
        assert bar.tier == "M5"

    def test_timestamp_parsed_to_utc(self, tmp_path: Path) -> None:
        f = tmp_path / "bars.jsonl"
        _write_jsonl(f, [_CANDLE_A])
        bar = next(iter(CandleFileBarFeed(f, instrument="EUR_USD")))
        assert bar.time_utc.tzinfo is not None
        assert bar.time_utc == datetime(2026, 4, 23, 20, 0, 0, tzinfo=UTC)

    def test_deterministic_two_reads(self, tmp_path: Path) -> None:
        f = tmp_path / "bars.jsonl"
        _write_jsonl(f, [_CANDLE_A, _CANDLE_B])
        feed = CandleFileBarFeed(f, instrument="EUR_USD")
        first = list(feed)
        second = list(feed)
        assert first == second

    def test_exhaustion_on_eof(self, tmp_path: Path) -> None:
        f = tmp_path / "bars.jsonl"
        _write_jsonl(f, [_CANDLE_A])
        bars = list(CandleFileBarFeed(f, instrument="EUR_USD"))
        assert len(bars) == 1  # no re-emission after EOF

    def test_skips_blank_lines(self, tmp_path: Path) -> None:
        f = tmp_path / "bars.jsonl"
        f.write_text(
            json.dumps(_CANDLE_A) + "\n\n" + json.dumps(_CANDLE_B) + "\n",
            encoding="utf-8",
        )
        bars = list(CandleFileBarFeed(f, instrument="EUR_USD"))
        assert len(bars) == 2

    def test_raises_on_missing_field(self, tmp_path: Path) -> None:
        f = tmp_path / "bars.jsonl"
        bad = {k: v for k, v in _CANDLE_A.items() if k != "volume"}
        _write_jsonl(f, [bad])
        with pytest.raises(ReplayDataError, match="missing fields"):
            list(CandleFileBarFeed(f, instrument="EUR_USD"))

    def test_raises_on_malformed_json(self, tmp_path: Path) -> None:
        f = tmp_path / "bars.jsonl"
        f.write_text("not-json\n", encoding="utf-8")
        with pytest.raises(ReplayDataError, match="invalid JSON"):
            list(CandleFileBarFeed(f, instrument="EUR_USD"))

    def test_default_granularity_is_m5(self, tmp_path: Path) -> None:
        f = tmp_path / "bars.jsonl"
        _write_jsonl(f, [_CANDLE_A])
        bar = next(iter(CandleFileBarFeed(f, instrument="EUR_USD")))
        assert bar.tier == "M5"

    def test_extra_fields_tolerated(self, tmp_path: Path) -> None:
        """Forward-compat: extra JSONL fields must not raise."""
        f = tmp_path / "bars.jsonl"
        candle_with_extra = {**_CANDLE_A, "complete": True, "note": "x"}
        _write_jsonl(f, [candle_with_extra])
        bars = list(CandleFileBarFeed(f, instrument="EUR_USD"))
        assert len(bars) == 1


class TestBidAskPropagation:
    """Phase 9.10: bid_c / ask_c in JSONL → Candle.bid_close / ask_close."""

    def test_bid_close_and_ask_close_populated_when_both_present(self, tmp_path: Path) -> None:
        f = tmp_path / "bars_ba.jsonl"
        candle_ba = {**_CANDLE_A, "bid_c": 1.16798, "ask_c": 1.16806}
        _write_jsonl(f, [candle_ba])
        bar = next(iter(CandleFileBarFeed(f, instrument="EUR_USD")))
        assert bar.bid_close == pytest.approx(1.16798)
        assert bar.ask_close == pytest.approx(1.16806)

    def test_bid_close_and_ask_close_none_when_absent(self, tmp_path: Path) -> None:
        """Back-compat: legacy mid-only JSONL must keep bid/ask = None."""
        f = tmp_path / "bars_m.jsonl"
        _write_jsonl(f, [_CANDLE_A])
        bar = next(iter(CandleFileBarFeed(f, instrument="EUR_USD")))
        assert bar.bid_close is None
        assert bar.ask_close is None

    def test_half_populated_bid_or_ask_treated_as_absent(self, tmp_path: Path) -> None:
        """If only one of bid_c/ask_c is present, both propagate as None —
        avoiding a mid-plus-one-side half-populated Candle."""
        f = tmp_path / "bars_partial.jsonl"
        partial = {**_CANDLE_A, "bid_c": 1.16798}  # ask_c missing
        _write_jsonl(f, [partial])
        bar = next(iter(CandleFileBarFeed(f, instrument="EUR_USD")))
        assert bar.bid_close is None
        assert bar.ask_close is None
