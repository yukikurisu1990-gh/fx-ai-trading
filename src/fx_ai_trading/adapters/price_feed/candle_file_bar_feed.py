"""CandleFileBarFeed — JSONL-backed BarFeed for D3 decision-loop replay.

Reads candles from a JSONL file produced by ``scripts/fetch_oanda_candles``
and yields one ``Candle`` per line through the ``BarFeed`` Protocol — letting
``run_paper_decision_loop`` replay historical bars through the full D3 pipeline
(FeatureService → run_strategy_cycle → run_meta_cycle) without a live OANDA
dependency.

Same dataset format as ``CandleReplayQuoteFeed``:

    {"time": "2026-04-23T20:00:00.000000000Z",
     "o": 1.16800, "h": 1.16805, "l": 1.16798, "c": 1.16802,
     "volume": 17}

Required fields per line: ``time``, ``o``, ``h``, ``l``, ``c``, ``volume``.

Phase 9.10: if optional ``bid_c`` and ``ask_c`` fields are present on the
JSONL line (produced by ``fetch_oanda_candles --price BA`` or ``MBA``),
they are carried onto ``Candle.bid_close`` / ``Candle.ask_close``. Lines
without bid/ask still produce valid mid-only Candles.

Yields completed ``Candle`` objects in file order (ascending time assumed).
StopIteration when the file is exhausted.  Raises ``ReplayDataError`` on
malformed lines — never silently skips.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from fx_ai_trading.adapters.price_feed.replay_quote_feed import ReplayDataError
from fx_ai_trading.domain.price_feed import Candle

_REQUIRED_FIELDS = frozenset({"time", "o", "h", "l", "c", "volume"})


def _parse_time(raw: str) -> datetime:
    """Parse RFC3339 / nanosecond-precision timestamp → UTC datetime."""
    # Normalise nanoseconds: keep only microseconds (6 digits).
    # e.g. "2026-04-23T20:00:00.000000000Z" → "2026-04-23T20:00:00.000000Z"
    raw = raw.rstrip("Z")
    if "." in raw:
        base, frac = raw.split(".", 1)
        raw = f"{base}.{frac[:6]}"
    return datetime.fromisoformat(raw).replace(tzinfo=UTC)


class CandleFileBarFeed:
    """File-backed BarFeed that replays candles from a JSONL file.

    Args:
        path: Path to the JSONL file (one candle object per line).
        instrument: Instrument name to tag emitted Candles with.
        granularity: Candle granularity string (e.g. ``"M5"``).  Used as
            ``Candle.tier`` — kept as-is, not validated against the file.
    """

    def __init__(
        self,
        path: Path | str,
        instrument: str,
        granularity: str = "M5",
    ) -> None:
        self._path = Path(path)
        self._instrument = instrument
        self._granularity = granularity

    def __iter__(self) -> Iterator[Candle]:
        with self._path.open(encoding="utf-8") as fh:
            for lineno, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ReplayDataError(
                        f"CandleFileBarFeed: invalid JSON on line {lineno}: {exc}"
                    ) from exc
                missing = _REQUIRED_FIELDS - obj.keys()
                if missing:
                    raise ReplayDataError(
                        f"CandleFileBarFeed: missing fields {sorted(missing)} on line {lineno}"
                    )
                # Phase 9.10: optional bid_c / ask_c carried through as
                # Candle.bid_close / ask_close when both are present. If
                # only one of the pair is present, propagate neither and
                # let the downstream Quote fall back to mid.
                bid_c = obj.get("bid_c")
                ask_c = obj.get("ask_c")
                if bid_c is not None and ask_c is not None:
                    bid_close: float | None = float(bid_c)
                    ask_close: float | None = float(ask_c)
                else:
                    bid_close = None
                    ask_close = None
                yield Candle(
                    instrument=self._instrument,
                    tier=self._granularity,
                    time_utc=_parse_time(str(obj["time"])),
                    open=float(obj["o"]),
                    high=float(obj["h"]),
                    low=float(obj["l"]),
                    close=float(obj["c"]),
                    volume=int(obj["volume"]),
                    bid_close=bid_close,
                    ask_close=ask_close,
                )


__all__ = ["CandleFileBarFeed"]
