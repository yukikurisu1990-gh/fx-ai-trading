"""Unit tests: ``CandleReplayQuoteFeed``.

Pins the contract that the file-backed candle feed:
  - Emits one ``Quote`` per OHLCV candle line, in recorded order, with
    ``price=c`` (close) and ``ts`` parsed from the candle's ``time`` field.
  - Two feeds backed by the same file produce identical sequences
    (determinism — the load-bearing property for backtest reproducibility).
  - Raises ``ReplayExhaustedError`` after the last candle is served (loud
    EOF, not silent re-emission of the last close).
  - Tolerates extra per-line fields (forward-compat).
  - Skips blank lines but raises ``ReplayDataError`` on malformed JSON
    or missing required OHLCV fields, with the offending line number.
  - Logs a warning on instrument mismatch but still returns the next
    dataset quote (mismatch = operator error, not data integrity).
  - Satisfies the runtime-checkable ``QuoteFeed`` Protocol.
  - Round-trips a real ``fetch_oanda_candles``-shaped JSONL line
    (nanosecond-precision RFC3339 with ``Z`` suffix) without losing
    timezone info or close price precision.
  - Stamps every ``Quote.source`` with ``SOURCE_OANDA_CANDLE_REPLAY`` so
    downstream consumers can distinguish replay quotes from live OANDA.
  - Refuses ``ReplayQuoteFeed``-shaped lines (``ts``/``price``/``source``)
    — passing a quotes file via ``--replay-candles`` must fail loudly,
    not silently.
"""

from __future__ import annotations

import inspect
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fx_ai_trading.adapters.price_feed.candle_replay_quote_feed import (
    CandleReplayQuoteFeed,
)
from fx_ai_trading.adapters.price_feed.replay_quote_feed import (
    ReplayDataError,
    ReplayExhaustedError,
)
from fx_ai_trading.domain.price_feed import (
    SOURCE_OANDA_CANDLE_REPLAY,
    Quote,
    QuoteFeed,
)


def _candle(
    time_str: str,
    *,
    o: float = 1.10000,
    h: float = 1.10005,
    low: float = 1.09995,
    c: float = 1.10002,
    volume: int = 17,
) -> dict:
    return {"time": time_str, "o": o, "h": h, "l": low, "c": c, "volume": volume}


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(line) for line in lines) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Order, projection, exhaustion
# ---------------------------------------------------------------------------


class TestEmitsOneQuotePerCandleAtClose:
    def test_returns_quotes_in_recorded_order_at_close(self, tmp_path: Path) -> None:
        path = tmp_path / "candles.jsonl"
        _write_jsonl(
            path,
            [
                _candle("2026-04-23T20:00:00.000000000Z", c=1.10010),
                _candle("2026-04-23T20:00:05.000000000Z", c=1.10020),
                _candle("2026-04-23T20:00:10.000000000Z", c=1.10030),
            ],
        )
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")

        prices = [feed.get_quote("EUR_USD").price for _ in range(3)]
        assert prices == [1.10010, 1.10020, 1.10030]

    def test_quote_carries_close_price_and_candle_time(self, tmp_path: Path) -> None:
        path = tmp_path / "candles.jsonl"
        _write_jsonl(
            path,
            [_candle("2026-04-23T20:00:00.000000000Z", o=1.1, h=1.2, low=1.0, c=1.15)],
        )
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        q = feed.get_quote("EUR_USD")

        assert q.price == 1.15
        assert q.ts == datetime(2026, 4, 23, 20, 0, 0, tzinfo=UTC)
        assert q.source == SOURCE_OANDA_CANDLE_REPLAY

    def test_two_feeds_over_same_file_are_deterministic(self, tmp_path: Path) -> None:
        path = tmp_path / "candles.jsonl"
        _write_jsonl(
            path,
            [
                _candle(f"2026-04-23T20:00:{i:02d}.000000000Z", c=1.1 + i / 1000)
                for i in range(0, 25, 5)
            ],
        )
        feed_a = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        feed_b = CandleReplayQuoteFeed(path, instrument="EUR_USD")

        seq_a = [feed_a.get_quote("EUR_USD") for _ in range(5)]
        seq_b = [feed_b.get_quote("EUR_USD") for _ in range(5)]
        assert seq_a == seq_b


class TestExhaustion:
    def test_raises_after_last_candle(self, tmp_path: Path) -> None:
        path = tmp_path / "one.jsonl"
        _write_jsonl(path, [_candle("2026-04-23T20:00:00.000000000Z")])
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        feed.get_quote("EUR_USD")

        with pytest.raises(ReplayExhaustedError, match="exhausted"):
            feed.get_quote("EUR_USD")

    def test_raises_immediately_on_empty_file(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")

        with pytest.raises(ReplayExhaustedError):
            feed.get_quote("EUR_USD")


# ---------------------------------------------------------------------------
# Tolerance and validation
# ---------------------------------------------------------------------------


class TestSkipsBlankLines:
    def test_blank_lines_are_skipped(self, tmp_path: Path) -> None:
        path = tmp_path / "with_blanks.jsonl"
        path.write_text(
            "\n"
            + json.dumps(_candle("2026-04-23T20:00:00.000000000Z", c=1.1))
            + "\n\n   \n"
            + json.dumps(_candle("2026-04-23T20:00:05.000000000Z", c=1.2))
            + "\n",
            encoding="utf-8",
        )
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")

        assert feed.get_quote("EUR_USD").price == 1.1
        assert feed.get_quote("EUR_USD").price == 1.2


class TestExtraFieldsTolerated:
    def test_extra_fields_do_not_break(self, tmp_path: Path) -> None:
        candle = _candle("2026-04-23T20:00:00.000000000Z", c=1.234)
        candle["bid"] = 1.233
        candle["ask"] = 1.235
        candle["complete"] = True
        path = tmp_path / "extra.jsonl"
        _write_jsonl(path, [candle])
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        assert feed.get_quote("EUR_USD").price == 1.234


class TestValidationErrors:
    def test_malformed_json_raises_with_line_number(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.jsonl"
        path.write_text(
            json.dumps(_candle("2026-04-23T20:00:00.000000000Z")) + "\n" + "not-json-at-all\n",
            encoding="utf-8",
        )
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        feed.get_quote("EUR_USD")  # line 1 OK

        with pytest.raises(ReplayDataError, match="line 2"):
            feed.get_quote("EUR_USD")

    @pytest.mark.parametrize("missing_field", ["time", "o", "h", "l", "c", "volume"])
    def test_missing_required_field_raises(self, tmp_path: Path, missing_field: str) -> None:
        candle = _candle("2026-04-23T20:00:00.000000000Z")
        del candle[missing_field]
        path = tmp_path / f"missing_{missing_field}.jsonl"
        _write_jsonl(path, [candle])
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")

        with pytest.raises(ReplayDataError, match=missing_field):
            feed.get_quote("EUR_USD")

    def test_quote_shaped_line_is_rejected(self, tmp_path: Path) -> None:
        """A ``ReplayQuoteFeed``-shaped line (ts/price/source instead of
        OHLCV) must fail loudly when fed to ``--replay-candles`` — silent
        mis-replay would defeat the purpose of having two replay
        sources."""
        path = tmp_path / "wrong_shape.jsonl"
        _write_jsonl(
            path,
            [{"ts": "2026-04-23T20:00:00+00:00", "price": 1.1, "source": "test"}],
        )
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")

        with pytest.raises(ReplayDataError, match="missing"):
            feed.get_quote("EUR_USD")

    def test_unparseable_time_raises_data_error(self, tmp_path: Path) -> None:
        path = tmp_path / "bad_time.jsonl"
        _write_jsonl(path, [_candle("not-a-timestamp")])
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")

        with pytest.raises(ReplayDataError, match="time"):
            feed.get_quote("EUR_USD")


# ---------------------------------------------------------------------------
# Time parsing — OANDA's nanosecond+Z RFC3339 round-trip
# ---------------------------------------------------------------------------


class TestNanosecondTimeRoundTrip:
    def test_nanosecond_precision_is_truncated_to_microseconds(self, tmp_path: Path) -> None:
        # OANDA emits 9 fractional digits; Python's stdlib only accepts 6.
        # The parser must truncate (not reject).
        path = tmp_path / "nano.jsonl"
        _write_jsonl(path, [_candle("2026-04-23T20:00:00.123456789Z", c=1.1)])
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        q = feed.get_quote("EUR_USD")

        assert q.ts == datetime(2026, 4, 23, 20, 0, 0, 123456, tzinfo=UTC)

    def test_microsecond_precision_round_trips(self, tmp_path: Path) -> None:
        path = tmp_path / "micro.jsonl"
        _write_jsonl(path, [_candle("2026-04-23T20:00:00.000123Z", c=1.1)])
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        q = feed.get_quote("EUR_USD")

        assert q.ts == datetime(2026, 4, 23, 20, 0, 0, 123, tzinfo=UTC)

    def test_no_fractional_digits_round_trips(self, tmp_path: Path) -> None:
        # OANDA usually pads zeros, but a hand-written fixture might omit
        # the fractional part entirely.
        path = tmp_path / "no_frac.jsonl"
        _write_jsonl(path, [_candle("2026-04-23T20:00:00Z", c=1.1)])
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        q = feed.get_quote("EUR_USD")

        assert q.ts == datetime(2026, 4, 23, 20, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Instrument mismatch behavior
# ---------------------------------------------------------------------------


class TestInstrumentMismatchWarns:
    def test_mismatch_logs_warning_and_returns_next_quote(
        self,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        path = tmp_path / "candles.jsonl"
        _write_jsonl(path, [_candle("2026-04-23T20:00:00.000000000Z", c=1.5)])
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")

        with caplog.at_level(
            logging.WARNING,
            logger="fx_ai_trading.adapters.price_feed.candle_replay_quote_feed",
        ):
            q = feed.get_quote("USD_JPY")
        assert q.price == 1.5
        assert any("instrument mismatch" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------


class TestSatisfiesQuoteFeedProtocol:
    def test_isinstance_quote_feed(self, tmp_path: Path) -> None:
        path = tmp_path / "candles.jsonl"
        _write_jsonl(path, [_candle("2026-04-23T20:00:00.000000000Z")])
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        assert isinstance(feed, QuoteFeed)


# ---------------------------------------------------------------------------
# Source / live-import isolation
# ---------------------------------------------------------------------------


class TestSourceAndIsolation:
    def test_every_quote_carries_oanda_candle_replay_source(self, tmp_path: Path) -> None:
        path = tmp_path / "candles.jsonl"
        _write_jsonl(
            path,
            [_candle(f"2026-04-23T20:00:{i:02d}.000000000Z") for i in range(0, 15, 5)],
        )
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        sources = {feed.get_quote("EUR_USD").source for _ in range(3)}
        assert sources == {SOURCE_OANDA_CANDLE_REPLAY}

    def test_module_does_not_import_live_oanda(self) -> None:
        """The replay adapter must run with no OANDA env vars and no
        network — pin that the module's source contains no live
        dependencies (oandapyV20 / requests / OandaAPIClient)."""
        from fx_ai_trading.adapters.price_feed import candle_replay_quote_feed

        src = inspect.getsource(candle_replay_quote_feed)
        for forbidden in ("oandapyV20", "requests", "OandaAPIClient"):
            assert forbidden not in src, f"{forbidden} leaked into replay module"


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------


class TestClose:
    def test_close_after_partial_iteration_releases_handle(self, tmp_path: Path) -> None:
        path = tmp_path / "candles.jsonl"
        _write_jsonl(
            path,
            [_candle(f"2026-04-23T20:00:{i:02d}.000000000Z") for i in range(0, 15, 5)],
        )
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        feed.get_quote("EUR_USD")
        feed.close()
        # Subsequent calls raise — generator is closed.
        with pytest.raises(ReplayExhaustedError):
            feed.get_quote("EUR_USD")


# ---------------------------------------------------------------------------
# Quote DTO interaction
# ---------------------------------------------------------------------------


class TestQuoteDtoInvariants:
    def test_returned_quote_is_tz_aware_utc(self, tmp_path: Path) -> None:
        path = tmp_path / "candles.jsonl"
        _write_jsonl(path, [_candle("2026-04-23T20:00:00.000000000Z")])
        feed = CandleReplayQuoteFeed(path, instrument="EUR_USD")
        q = feed.get_quote("EUR_USD")
        assert isinstance(q, Quote)
        assert q.ts.tzinfo is not None
        assert q.ts.utcoffset().total_seconds() == 0  # type: ignore[union-attr]
