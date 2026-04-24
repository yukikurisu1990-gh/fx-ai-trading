"""CandleReplayQuoteFeed — file-backed QuoteFeed projecting OHLCV candles.

Reads candles from a JSONL file produced by ``scripts/fetch_oanda_candles``
and emits one ``Quote`` per candle through the ``QuoteFeed`` Protocol —
letting the existing evaluation runner, paper broker, and exit gate run
on captured historical OHLCV data with no live OANDA dependency.

Dataset format (1 line = 1 candle, OANDA ``InstrumentsCandles`` shape):

    {"time": "2026-04-23T20:00:00.000000000Z",
     "o": 1.16800, "h": 1.16805, "l": 1.16798, "c": 1.16802,
     "volume": 17}

Required fields per line: ``time`` (RFC3339 with ``Z`` or ``+00:00``,
nanosecond precision tolerated), ``o``, ``h``, ``l``, ``c`` (floats),
``volume`` (int).  Requiring the full OHLCV set (not just ``c``) means a
``quotes_*.jsonl`` file accidentally passed via ``--replay-candles`` will
fail loudly with a missing-field error rather than silently mis-replay.

OHLCV → Quote projection
------------------------
One candle becomes exactly one ``Quote(price=c, ts=time, source="oanda_candle_replay")``.

The choice of ``c`` (close) over ``(h+l+c)/3`` (typical price) is
deliberate: ``c`` is an actually-observed market price executable in
principle at bar close, while typical price is a synthesized value that
never traded.  For backtest realism (no synthetic-price bias) ``c`` is
the standard FX/quant convention.

H/L/V are intentionally **not** carried in the ``Quote`` DTO — the exit
gate and paper broker only need a single price.  Future TA/ML signals
that need OHLCV will read the same JSONL via a separate
``CandleReplaySignalFeed`` (not built here) so this projection layer
stays minimal.

Phase 9.10: when the source JSONL carries optional ``bid_c`` / ``ask_c``
(produced by ``fetch_oanda_candles --price BA`` or ``MBA``), the emitted
``Quote`` populates ``bid`` / ``ask`` so downstream ``PaperBroker`` fills
at side-specific prices (long at ask, short at bid). With mid-only input
the bid/ask remain ``None`` and fills stay at mid (legacy behaviour).

Single-instrument-per-file convention: instrument lives in the filename,
not in each candle line (matching ``ReplayQuoteFeed`` semantics).
``get_quote(instrument)`` compares against the instrument passed at
construction; mismatch logs a warning but still returns the next
candle's projected quote.

Lazy iteration: the file is read line-by-line via a generator (memory
footprint = one line at a time), so multi-day S5 datasets are safe.

Exhaustion: once the last candle has been served, the next
``get_quote()`` raises ``ReplayExhaustedError`` (loud EOF, not silent
re-emission of the last close).

Errors are reused from ``replay_quote_feed`` (``ReplayDataError`` /
``ReplayExhaustedError``) so callers handle a uniform error surface
across both replay sources.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Final

from fx_ai_trading.adapters.price_feed.replay_quote_feed import (
    ReplayDataError,
    ReplayExhaustedError,
)
from fx_ai_trading.domain.price_feed import SOURCE_OANDA_CANDLE_REPLAY, Quote

_LOG = logging.getLogger(__name__)
_REQUIRED_FIELDS: Final[tuple[str, ...]] = ("time", "o", "h", "l", "c", "volume")


class CandleReplayQuoteFeed:
    """File-backed ``QuoteFeed`` over OHLCV candle JSONL.

    Implements the ``QuoteFeed`` Protocol from
    ``fx_ai_trading.domain.price_feed``.  No explicit base inheritance —
    ``isinstance(feed, QuoteFeed)`` succeeds for any object with a
    ``get_quote(instrument: str) -> Quote`` method.
    """

    def __init__(self, path: Path | str, *, instrument: str) -> None:
        self._path = Path(path)
        self._instrument = instrument
        self._iter: Iterator[Quote] = _iter_candles_as_quotes(self._path)

    @property
    def instrument(self) -> str:
        return self._instrument

    @property
    def path(self) -> Path:
        return self._path

    def get_quote(self, instrument: str) -> Quote:
        if instrument != self._instrument:
            _LOG.warning(
                "CandleReplayQuoteFeed: instrument mismatch (requested=%r, dataset=%r); "
                "returning next dataset quote anyway",
                instrument,
                self._instrument,
            )
        try:
            return next(self._iter)
        except StopIteration:
            raise ReplayExhaustedError(
                f"CandleReplayQuoteFeed exhausted: no more candles in {self._path!s}"
            ) from None

    def close(self) -> None:
        """Release the underlying generator (and its file handle)."""
        self._iter.close()


def _parse_candle_time(s: str) -> datetime:
    """Parse OANDA's nanosecond-precision RFC3339 timestamp.

    OANDA emits ``2026-04-23T20:00:00.000000000Z`` (9 fractional digits +
    ``Z``).  ``datetime.fromisoformat`` accepts up to 6 fractional digits
    and ``+00:00`` instead of ``Z``.  Truncate fractional to 6 digits and
    swap the ``Z`` for ``+00:00``.
    """
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    if "." in s:
        head, frac_tz = s.split(".", 1)
        tz_idx = max(frac_tz.find("+"), frac_tz.find("-"))
        if tz_idx > 0:
            frac = frac_tz[:tz_idx][:6].ljust(6, "0")
            tz = frac_tz[tz_idx:]
            s = f"{head}.{frac}{tz}"
    return datetime.fromisoformat(s)


def _iter_candles_as_quotes(path: Path) -> Iterator[Quote]:
    with path.open(encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ReplayDataError(
                    f"CandleReplayQuoteFeed: malformed JSON on line {line_no} of {path!s}: {exc}"
                ) from exc
            missing = [k for k in _REQUIRED_FIELDS if k not in data]
            if missing:
                raise ReplayDataError(
                    f"CandleReplayQuoteFeed: missing required field(s) {missing!r} "
                    f"on line {line_no} of {path!s}"
                )
            try:
                ts = _parse_candle_time(str(data["time"]))
            except ValueError as exc:
                raise ReplayDataError(
                    f"CandleReplayQuoteFeed: unparseable 'time' on line {line_no} "
                    f"of {path!s}: {exc}"
                ) from exc
            # Phase 9.10: propagate optional bid_c / ask_c as Quote.bid/ask.
            # When either is absent, both stay None so Quote.__post_init__
            # accepts it (and PaperBroker falls back to mid-price fills).
            bid_raw = data.get("bid_c")
            ask_raw = data.get("ask_c")
            if bid_raw is not None and ask_raw is not None:
                bid: float | None = float(bid_raw)
                ask: float | None = float(ask_raw)
                # With explicit bid/ask the Quote mid must equal (bid+ask)/2
                # for the invariant to hold.  Synthesize that mid here — the
                # candle's mid close may diverge from the BA mid when the
                # producer pulled separate M and BA passes; we trust BA for
                # cost-aware backtests.
                projected_price = (bid + ask) / 2.0
            else:
                bid = None
                ask = None
                projected_price = float(data["c"])
            yield Quote(
                price=projected_price,
                ts=ts,
                source=SOURCE_OANDA_CANDLE_REPLAY,
                bid=bid,
                ask=ask,
            )
