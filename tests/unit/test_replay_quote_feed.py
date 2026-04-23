"""Unit tests: ``ReplayQuoteFeed`` (replay PR1).

Pins the contract that the file-backed feed:
  - Returns ``Quote`` objects in recorded JSONL order, line-by-line.
  - Two feeds backed by the same file produce identical sequences
    (determinism — the load-bearing property for backtest reproducibility).
  - Raises ``ReplayExhaustedError`` after the last quote is served (loud
    EOF, not silent re-emission of the last quote).
  - Tolerates extra per-line fields (forward-compat for a future bid/ask
    extension).
  - Skips blank lines but raises ``ReplayDataError`` on malformed JSON
    or missing required fields, with the offending line number.
  - Propagates ``Quote.__post_init__``'s tz-aware enforcement when the
    file holds a naive ``ts`` (does not silently downgrade).
  - Logs a warning on instrument mismatch but still returns the next
    dataset quote (mismatch = operator error, not data integrity).
  - Satisfies the runtime-checkable ``QuoteFeed`` Protocol.
  - Round-trips a hand-written JSONL: any (price, ts, source) triple in
    the documented format reads back to an equal ``Quote``.  This pins
    the recorder/replayer contract — PR2's recorder must produce lines
    of exactly this shape.
  - Holds no live dependencies: the module's source contains no
    ``oanda``, ``requests``, or ``oandapyV20`` import — operational
    guarantee that replay runs without OANDA env vars.
"""

from __future__ import annotations

import inspect
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest

from fx_ai_trading.adapters.price_feed.replay_quote_feed import (
    ReplayDataError,
    ReplayExhaustedError,
    ReplayQuoteFeed,
)
from fx_ai_trading.domain.price_feed import (
    SOURCE_OANDA_REST_SNAPSHOT,
    Quote,
    QuoteFeed,
)


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(line) for line in lines) + "\n",
        encoding="utf-8",
    )


def _line(price: float, ts: str, source: str = SOURCE_OANDA_REST_SNAPSHOT) -> dict:
    return {"ts": ts, "price": price, "source": source}


class TestReplayQuoteFeedReturnsRecordedOrder:
    def test_returns_quotes_in_recorded_order(self, tmp_path: Path) -> None:
        path = tmp_path / "quotes_EUR_USD.jsonl"
        _write_jsonl(
            path,
            [
                _line(1.0500, "2026-04-24T12:00:00+00:00"),
                _line(1.0510, "2026-04-24T12:00:01+00:00"),
                _line(1.0520, "2026-04-24T12:00:02+00:00"),
            ],
        )

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")

        prices = [feed.get_quote("EUR_USD").price for _ in range(3)]

        assert prices == [1.0500, 1.0510, 1.0520]

    def test_quote_carries_full_fields(self, tmp_path: Path) -> None:
        path = tmp_path / "quotes.jsonl"
        _write_jsonl(
            path,
            [_line(1.1234, "2026-04-24T12:00:00+00:00", "oanda_rest_snapshot")],
        )

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")
        quote = feed.get_quote("EUR_USD")

        assert quote == Quote(
            price=1.1234,
            ts=datetime(2026, 4, 24, 12, 0, 0, tzinfo=UTC),
            source="oanda_rest_snapshot",
        )


class TestReplayQuoteFeedDeterminism:
    def test_two_feeds_same_file_identical_sequence(self, tmp_path: Path) -> None:
        path = tmp_path / "quotes.jsonl"
        _write_jsonl(
            path,
            [_line(1.10 + 0.01 * i, f"2026-04-24T12:00:{i:02d}+00:00") for i in range(5)],
        )

        feed_a = ReplayQuoteFeed(path, instrument="EUR_USD")
        feed_b = ReplayQuoteFeed(path, instrument="EUR_USD")

        seq_a = [feed_a.get_quote("EUR_USD") for _ in range(5)]
        seq_b = [feed_b.get_quote("EUR_USD") for _ in range(5)]

        assert seq_a == seq_b


class TestReplayQuoteFeedExhaustion:
    def test_exhaustion_raises_replay_exhausted_error(self, tmp_path: Path) -> None:
        path = tmp_path / "quotes.jsonl"
        _write_jsonl(path, [_line(1.10, "2026-04-24T12:00:00+00:00")])

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")
        feed.get_quote("EUR_USD")  # consume the only line

        with pytest.raises(ReplayExhaustedError, match="exhausted"):
            feed.get_quote("EUR_USD")

    def test_empty_file_first_call_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")

        with pytest.raises(ReplayExhaustedError):
            feed.get_quote("EUR_USD")


class TestReplayQuoteFeedRobustness:
    def test_blank_lines_are_skipped(self, tmp_path: Path) -> None:
        path = tmp_path / "quotes.jsonl"
        path.write_text(
            "\n"
            + json.dumps(_line(1.10, "2026-04-24T12:00:00+00:00"))
            + "\n\n"
            + json.dumps(_line(1.11, "2026-04-24T12:00:01+00:00"))
            + "\n   \n",
            encoding="utf-8",
        )

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")

        prices = [feed.get_quote("EUR_USD").price for _ in range(2)]

        assert prices == [1.10, 1.11]

    def test_extra_fields_in_line_are_ignored(self, tmp_path: Path) -> None:
        # Forward-compat: a future bid/ask augmentation must not break
        # the PR1 replay path — extra keys must be silently tolerated.
        path = tmp_path / "quotes.jsonl"
        line = {
            "ts": "2026-04-24T12:00:00+00:00",
            "price": 1.10,
            "source": "oanda_rest_snapshot",
            "bid": 1.0998,
            "ask": 1.1002,
            "future_field": {"nested": True},
        }
        path.write_text(json.dumps(line) + "\n", encoding="utf-8")

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")
        quote = feed.get_quote("EUR_USD")

        assert quote.price == 1.10

    def test_malformed_json_raises_replay_data_error(self, tmp_path: Path) -> None:
        path = tmp_path / "quotes.jsonl"
        path.write_text("not-a-json-object\n", encoding="utf-8")

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")

        with pytest.raises(ReplayDataError, match="line 1"):
            feed.get_quote("EUR_USD")

    def test_missing_required_field_raises_replay_data_error(self, tmp_path: Path) -> None:
        # 'source' missing — the message must name the missing field so
        # operators can repair the dataset without grepping.
        path = tmp_path / "quotes.jsonl"
        path.write_text(
            json.dumps({"ts": "2026-04-24T12:00:00+00:00", "price": 1.10}) + "\n",
            encoding="utf-8",
        )

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")

        with pytest.raises(ReplayDataError, match="source"):
            feed.get_quote("EUR_USD")

    def test_naive_ts_propagates_quote_post_init_error(self, tmp_path: Path) -> None:
        # Quote.__post_init__ must continue to be the sole tz-aware
        # enforcement point — a naive ts in the file must surface as
        # ValueError, not be silently coerced to UTC.
        path = tmp_path / "quotes.jsonl"
        path.write_text(
            json.dumps(
                {
                    "ts": "2026-04-24T12:00:00",  # tz-naive
                    "price": 1.10,
                    "source": "oanda_rest_snapshot",
                }
            )
            + "\n",
            encoding="utf-8",
        )

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")

        with pytest.raises(ValueError, match="timezone-aware"):
            feed.get_quote("EUR_USD")


class TestReplayQuoteFeedInstrumentMismatch:
    def test_instrument_mismatch_warns_but_returns_next_quote(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        path = tmp_path / "quotes.jsonl"
        _write_jsonl(path, [_line(1.10, "2026-04-24T12:00:00+00:00")])

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")

        with caplog.at_level(logging.WARNING):
            quote = feed.get_quote("USD_JPY")

        assert quote.price == 1.10
        assert any("instrument mismatch" in rec.message for rec in caplog.records)


class TestReplayQuoteFeedProtocolCompliance:
    def test_satisfies_quote_feed_protocol(self, tmp_path: Path) -> None:
        # The runner / supervisor consume QuoteFeed via isinstance checks
        # against the @runtime_checkable Protocol — replay must pass it.
        path = tmp_path / "quotes.jsonl"
        _write_jsonl(path, [_line(1.10, "2026-04-24T12:00:00+00:00")])

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")

        assert isinstance(feed, QuoteFeed)


class TestReplayQuoteFeedRoundTrip:
    def test_round_trip_jsonl_to_quote_to_jsonl(self, tmp_path: Path) -> None:
        # Pins the recorder/replayer contract: any (price, ts, source)
        # triple written in the documented format round-trips through
        # ReplayQuoteFeed exactly.  PR2's recorder must emit lines of
        # this shape, and this test fails if the shape ever drifts.
        original = [
            Quote(
                price=1.10 + 0.001 * i,
                ts=datetime(2026, 4, 24, 12, 0, i, tzinfo=UTC),
                source=SOURCE_OANDA_REST_SNAPSHOT,
            )
            for i in range(3)
        ]
        path = tmp_path / "round_trip.jsonl"
        path.write_text(
            "\n".join(
                json.dumps({"ts": q.ts.isoformat(), "price": q.price, "source": q.source})
                for q in original
            )
            + "\n",
            encoding="utf-8",
        )

        feed = ReplayQuoteFeed(path, instrument="EUR_USD")
        replayed = [feed.get_quote("EUR_USD") for _ in range(3)]

        assert replayed == original


class TestReplayQuoteFeedNoLiveDependencies:
    def test_module_does_not_import_oanda_or_http(self) -> None:
        # Static check: replay path must stay free of live deps so the
        # operator can run backtests without OANDA credentials or
        # network access.  Scan only the AST import nodes (not docstring
        # / comment text, which legitimately discusses OANDA).
        import ast

        from fx_ai_trading.adapters.price_feed import replay_quote_feed

        tree = ast.parse(inspect.getsource(replay_quote_feed))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.add(node.module)

        forbidden = {"oandapyV20", "requests", "urllib3"}
        leaked = {m for m in imported_modules if any(m.startswith(f) for f in forbidden)}
        assert leaked == set(), f"replay module must not import live deps: {leaked!r}"

        oanda_imports = {m for m in imported_modules if "oanda" in m.lower()}
        assert oanda_imports == set(), (
            f"replay module must not import OANDA modules: {oanda_imports!r}"
        )
