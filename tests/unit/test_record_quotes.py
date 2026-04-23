"""Unit tests: ``scripts.record_quotes`` (replay PR2).

Pins the contract that the recorder:
  - Writes one JSONL line per ``Quote`` returned by an injected
    ``QuoteFeed``.
  - Each line contains ONLY ``ts`` / ``price`` / ``source`` — no extra
    fields.  The recorder/replayer round-trip pin in PR1
    (``test_round_trip_jsonl_to_quote_to_jsonl``) assumes this exact
    shape; adding fields here would silently extend the contract.
  - Output JSONL is round-trip compatible with ``ReplayQuoteFeed``:
    feeding the recorder's output back through the replayer yields the
    exact ``Quote`` sequence.  This is the load-bearing property — if
    it ever breaks, weekend backtests no longer reflect captured
    market state.
  - Honours ``stop_requested`` (cooperative SIGINT seam) before the
    next poll AND before the next sleep, so Ctrl-C never produces a
    half-written line.
  - Tolerates a transient ``OandaQuoteFeedError`` on a single poll:
    the failed tick is skipped (not written), the loop continues, the
    return count reflects only successful writes.
  - Flushes after each line so a recording interrupted at any point
    leaves a parseable file (no truncated final line).

Tests use a local ``_FakeQuoteFeed`` and a no-op sleep so nothing
touches the network or the wall clock.
"""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from fx_ai_trading.adapters.price_feed.oanda_quote_feed import OandaQuoteFeedError
from fx_ai_trading.adapters.price_feed.replay_quote_feed import ReplayQuoteFeed
from fx_ai_trading.domain.price_feed import SOURCE_OANDA_REST_SNAPSHOT, Quote
from scripts.record_quotes import record_quotes

# --- helpers -----------------------------------------------------------------


class _FakeQuoteFeed:
    """Yields a fixed sequence of quotes; raises ``OandaQuoteFeedError`` on
    iterations whose index appears in ``raise_at``.

    The recorder's only contract with the feed is the ``QuoteFeed``
    Protocol (``get_quote(instrument: str) -> Quote``); this fake
    matches that surface and lets tests dictate exactly what the
    recorder sees per tick.
    """

    def __init__(
        self,
        quotes: list[Quote],
        *,
        raise_at: set[int] | None = None,
    ) -> None:
        self._iter: Iterator[Quote] = iter(quotes)
        self._raise_at = raise_at or set()
        self._call_no = 0

    def get_quote(self, instrument: str) -> Quote:  # noqa: ARG002 — Protocol shape
        idx = self._call_no
        self._call_no += 1
        if idx in self._raise_at:
            raise OandaQuoteFeedError(f"fake transient error on call #{idx}")
        return next(self._iter)


def _quote(price: float, second: int) -> Quote:
    return Quote(
        price=price,
        ts=datetime(2026, 4, 24, 12, 0, second, tzinfo=UTC),
        source=SOURCE_OANDA_REST_SNAPSHOT,
    )


# --- happy-path write --------------------------------------------------------


class TestRecordQuotesWritesLines:
    def test_writes_one_line_per_quote(self) -> None:
        feed = _FakeQuoteFeed([_quote(1.10, 0), _quote(1.11, 1), _quote(1.12, 2)])
        buf = io.StringIO()

        written = record_quotes(
            feed=feed,
            instrument="EUR_USD",
            output=buf,
            interval_seconds=0.0,
            max_iterations=3,
            sleep=lambda _s: None,
        )

        assert written == 3
        lines = [ln for ln in buf.getvalue().splitlines() if ln]
        assert len(lines) == 3

    def test_lines_contain_only_required_fields(self) -> None:
        # Pinning the JSONL shape: extra fields would silently break PR1's
        # round-trip pin and the recorder/replayer contract.
        feed = _FakeQuoteFeed([_quote(1.10, 0)])
        buf = io.StringIO()

        record_quotes(
            feed=feed,
            instrument="EUR_USD",
            output=buf,
            interval_seconds=0.0,
            max_iterations=1,
            sleep=lambda _s: None,
        )

        line = buf.getvalue().strip()
        data = json.loads(line)
        assert set(data.keys()) == {"ts", "price", "source"}


# --- round-trip with ReplayQuoteFeed -----------------------------------------


class TestRecordQuotesRoundTripWithReplay:
    def test_recorder_output_replays_to_identical_quotes(self, tmp_path: Path) -> None:
        # Load-bearing: PR2's recorder must emit lines that PR1's
        # ReplayQuoteFeed reads back as the exact same Quote sequence.
        # If this ever fails, weekend backtests no longer reflect the
        # captured market state.
        original = [_quote(1.10 + 0.001 * i, i) for i in range(5)]
        feed = _FakeQuoteFeed(original)
        out_path = tmp_path / "quotes_EUR_USD.jsonl"

        with out_path.open("w", encoding="utf-8") as f:
            record_quotes(
                feed=feed,
                instrument="EUR_USD",
                output=f,
                interval_seconds=0.0,
                max_iterations=5,
                sleep=lambda _s: None,
            )

        replay = ReplayQuoteFeed(out_path, instrument="EUR_USD")
        replayed = [replay.get_quote("EUR_USD") for _ in range(5)]
        assert replayed == original


# --- stop_requested (SIGINT seam) --------------------------------------------


class TestRecordQuotesStopRequested:
    def test_stop_requested_before_first_poll_writes_nothing(self) -> None:
        feed = _FakeQuoteFeed([_quote(1.10, 0)])
        buf = io.StringIO()

        written = record_quotes(
            feed=feed,
            instrument="EUR_USD",
            output=buf,
            interval_seconds=0.0,
            max_iterations=10,
            sleep=lambda _s: None,
            stop_requested=lambda: True,
        )

        assert written == 0
        assert buf.getvalue() == ""

    def test_stop_requested_mid_run_halts_loop_cleanly(self) -> None:
        # Trip the stop flag after the 2nd write: recorder must finish
        # the current tick (already counted) and exit before polling the
        # 3rd quote.  No half-written line is possible because flush()
        # runs before the predicate is checked again.
        feed = _FakeQuoteFeed([_quote(1.10, 0), _quote(1.11, 1), _quote(1.12, 2)])
        buf = io.StringIO()
        calls = {"n": 0}

        def stop_after_two() -> bool:
            calls["n"] += 1
            return calls["n"] > 4  # 2 polls × 2 predicate checks per iter

        written = record_quotes(
            feed=feed,
            instrument="EUR_USD",
            output=buf,
            interval_seconds=0.0,
            max_iterations=10,
            sleep=lambda _s: None,
            stop_requested=stop_after_two,
        )

        assert written == 2
        lines = [ln for ln in buf.getvalue().splitlines() if ln]
        assert len(lines) == 2
        # Every emitted line must be valid JSON — no truncation.
        for ln in lines:
            json.loads(ln)


# --- transient OANDA error skipped -------------------------------------------


class TestRecordQuotesSkipsTransientErrors:
    def test_oanda_error_on_one_tick_skips_and_continues(self) -> None:
        # Iteration 1 raises; iterations 0 and 2 succeed → 2 written.
        feed = _FakeQuoteFeed(
            [_quote(1.10, 0), _quote(1.11, 1)],
            raise_at={1},
        )
        buf = io.StringIO()

        written = record_quotes(
            feed=feed,
            instrument="EUR_USD",
            output=buf,
            interval_seconds=0.0,
            max_iterations=3,
            sleep=lambda _s: None,
        )

        assert written == 2
        prices = [json.loads(ln)["price"] for ln in buf.getvalue().splitlines() if ln]
        assert prices == [1.10, 1.11]


# --- file flush after every line ---------------------------------------------


class TestRecordQuotesFlushesEveryLine:
    def test_flush_called_after_each_write(self) -> None:
        # If the recorder buffered, a SIGINT mid-run could leave the
        # last line unwritten.  Pin "flush per line" by counting flushes.
        feed = _FakeQuoteFeed([_quote(1.10, 0), _quote(1.11, 1)])

        class _CountingBuffer(io.StringIO):
            flush_count = 0

            def flush(self) -> None:  # type: ignore[override]
                _CountingBuffer.flush_count += 1
                super().flush()

        buf = _CountingBuffer()
        record_quotes(
            feed=feed,
            instrument="EUR_USD",
            output=buf,
            interval_seconds=0.0,
            max_iterations=2,
            sleep=lambda _s: None,
        )

        assert _CountingBuffer.flush_count == 2


# --- sleep interval honoured -------------------------------------------------


class TestRecordQuotesSleepInterval:
    def test_sleep_called_with_interval_between_polls(self) -> None:
        feed = _FakeQuoteFeed([_quote(1.10, 0), _quote(1.11, 1), _quote(1.12, 2)])
        buf = io.StringIO()
        slept: list[float] = []

        record_quotes(
            feed=feed,
            instrument="EUR_USD",
            output=buf,
            interval_seconds=0.250,
            max_iterations=3,
            sleep=lambda s: slept.append(s),
        )

        # sleep is called once per loop iteration after writing — 3 polls
        # → 3 sleeps with the configured interval.
        assert slept == [0.250, 0.250, 0.250]


# --- pytest discovery --------------------------------------------------------


def test_module_imports() -> None:
    # Sanity check: the recorder module must be importable without
    # OANDA env vars (env-reading is deferred until main()).
    import scripts.record_quotes as rec  # noqa: F401
