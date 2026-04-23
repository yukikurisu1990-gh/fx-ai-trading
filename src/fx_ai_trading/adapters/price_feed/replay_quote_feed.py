"""ReplayQuoteFeed — file-backed QuoteFeed for offline backtest (replay).

Reads quotes from a JSONL file (typically produced by
``scripts/record_quotes.py`` in PR2) and returns them in recorded order
through the ``QuoteFeed`` Protocol — letting the existing evaluation
runner, paper broker, and exit gate run on captured market data with no
live OANDA dependency.

Dataset format (1 line = 1 quote):

    {"ts": "2026-04-24T12:34:56.123456+00:00",
     "price": 1.16923,
     "source": "oanda_rest_snapshot"}

Required fields per line: ``ts`` (ISO-8601, tz-aware), ``price`` (float),
``source`` (string).  Extra fields are tolerated and ignored, leaving
room for a later bid/ask extension without a format break.

Single-instrument-per-file convention: instrument lives in the filename,
not in each line.  ``get_quote(instrument)`` compares against the
``instrument`` passed at construction; a mismatch logs a warning but
still returns the next dataset quote — operator error, not a data
integrity bug.

Lazy iteration: the file is read line-by-line via a generator (memory
footprint = one line at a time), so arbitrarily long datasets are safe.

Exhaustion: once the last recorded quote has been served, the next
``get_quote()`` call raises ``ReplayExhaustedError``.  Failing loudly
beats silently re-emitting the last quote — data shortage stays visible
to the operator.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Final

from fx_ai_trading.domain.price_feed import Quote

_LOG = logging.getLogger(__name__)
_REQUIRED_FIELDS: Final[tuple[str, ...]] = ("ts", "price", "source")


class ReplayDataError(RuntimeError):
    """Raised when the replay dataset is malformed or missing required fields.

    Distinct from ``ReplayExhaustedError`` (clean EOF): this fires when a
    line cannot be parsed or lacks ``ts`` / ``price`` / ``source``.  The
    message includes the offending line number to make ``record_quotes``
    output triage-able.
    """


class ReplayExhaustedError(RuntimeError):
    """Raised when ``get_quote()`` is called after the last recorded quote."""


class ReplayQuoteFeed:
    """File-backed ``QuoteFeed`` implementation for offline replay.

    Implements the ``QuoteFeed`` Protocol from
    ``fx_ai_trading.domain.price_feed``.  No explicit base inheritance —
    ``isinstance(feed, QuoteFeed)`` succeeds for any object with a
    ``get_quote(instrument: str) -> Quote`` method.
    """

    def __init__(self, path: Path | str, *, instrument: str) -> None:
        self._path = Path(path)
        self._instrument = instrument
        self._iter: Iterator[Quote] = _iter_quotes(self._path)

    @property
    def instrument(self) -> str:
        return self._instrument

    @property
    def path(self) -> Path:
        return self._path

    def get_quote(self, instrument: str) -> Quote:
        if instrument != self._instrument:
            _LOG.warning(
                "ReplayQuoteFeed: instrument mismatch (requested=%r, dataset=%r); "
                "returning next dataset quote anyway",
                instrument,
                self._instrument,
            )
        try:
            return next(self._iter)
        except StopIteration:
            raise ReplayExhaustedError(
                f"ReplayQuoteFeed exhausted: no more quotes in {self._path!s}"
            ) from None

    def close(self) -> None:
        """Release the underlying generator (and its file handle).

        Optional — Python's GC closes the file when the feed is dropped,
        but explicit ``close()`` is exposed for tests and long-lived
        processes that want deterministic handle release.
        """
        self._iter.close()


def _iter_quotes(path: Path) -> Iterator[Quote]:
    with path.open(encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ReplayDataError(
                    f"ReplayQuoteFeed: malformed JSON on line {line_no} of {path!s}: {exc}"
                ) from exc
            missing = [k for k in _REQUIRED_FIELDS if k not in data]
            if missing:
                raise ReplayDataError(
                    f"ReplayQuoteFeed: missing required field(s) {missing!r} "
                    f"on line {line_no} of {path!s}"
                )
            yield Quote(
                price=float(data["price"]),
                ts=datetime.fromisoformat(data["ts"]),
                source=str(data["source"]),
            )
