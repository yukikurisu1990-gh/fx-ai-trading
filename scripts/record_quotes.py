"""``record_quotes`` — capture OANDA quotes to a JSONL file (PR2/3 of replay).

Why this exists
---------------
PR1 (#159) added ``ReplayQuoteFeed``: a file-backed ``QuoteFeed``
implementation that lets the eval runner / paper broker / exit gate run
on captured market data with no live OANDA dependency.  This script is
the producer side: poll OANDA at a fixed interval and append each
``Quote`` to a JSONL file in the format ``ReplayQuoteFeed`` consumes.

The recorder runs only against the live OANDA REST feed.  It does not
touch the database, the broker, the exit gate, or the supervisor — its
sole side effect is appending lines to the output file.

Output format (1 line = 1 quote — pinned by PR1's round-trip test):

    {"ts": "2026-04-24T12:34:56.123456+00:00",
     "price": 1.16923,
     "source": "oanda_rest_snapshot"}

CLI
---
``python -m scripts.record_quotes \\
    --instrument EUR_USD --interval 1.0 --duration 60 \\
    --output data/quotes_EUR_USD.jsonl``

Env (read at startup)
---------------------
  OANDA_ACCESS_TOKEN  — required.
  OANDA_ACCOUNT_ID    — required.
  OANDA_ENVIRONMENT   — 'practice' (default) or 'live'.

Stop conditions
---------------
- ``--duration`` seconds elapsed (clean stop, normal exit).
- ``SIGINT`` / Ctrl-C (clean stop, normal exit).  Each line is written
  and ``flush()``-ed before the next sleep, so an interrupt can never
  produce a half-written line — at worst the loop ends one quote early.
- ``OandaQuoteFeedError`` from a single poll: logged, **skipped**, the
  loop continues.  A transient OANDA hiccup must not abort a long
  recording run; the missed tick simply doesn't appear in the file.

Out of scope (do not extend without splitting a new PR)
-------------------------------------------------------
- Wiring ``--replay`` into ``run_paper_evaluation`` (PR3).
- Adding bid/ask or volume to the JSONL format (would break PR1's
  round-trip pin and the recorder/replayer contract).
- Multi-instrument-per-file: PR1 enforces single-instrument-per-file
  via filename convention; the recorder respects that.
- Database / broker / exit-gate / supervisor surfaces.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Final

from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.adapters.price_feed.oanda_quote_feed import (
    OandaQuoteFeed,
    OandaQuoteFeedError,
)
from fx_ai_trading.domain.price_feed import Quote, QuoteFeed

_LOG = logging.getLogger("scripts.record_quotes")

_ENV_OANDA_ACCESS_TOKEN: Final[str] = "OANDA_ACCESS_TOKEN"
_ENV_OANDA_ACCOUNT_ID: Final[str] = "OANDA_ACCOUNT_ID"
_ENV_OANDA_ENVIRONMENT: Final[str] = "OANDA_ENVIRONMENT"
_DEFAULT_OANDA_ENVIRONMENT: Final[str] = "practice"


# ---------------------------------------------------------------------------
# Pure recording loop (testable without OANDA / clock / signals)
# ---------------------------------------------------------------------------


def record_quotes(
    *,
    feed: QuoteFeed,
    instrument: str,
    output: IO[str],
    interval_seconds: float,
    max_iterations: int,
    sleep: Callable[[float], None] = time.sleep,
    stop_requested: Callable[[], bool] = lambda: False,
) -> int:
    """Poll *feed* up to *max_iterations* times, writing one JSONL line per quote.

    Pure function over its arguments — no env / signal / wall-clock
    assumptions — so unit tests inject a fake feed, a no-op sleep, and
    a stop predicate.

    Returns the number of quotes successfully written.  A poll that
    raises ``OandaQuoteFeedError`` is logged and skipped (does not
    increment the count), matching the docstring's stop-conditions
    contract.
    """
    written = 0
    for _ in range(max_iterations):
        if stop_requested():
            break
        try:
            quote = feed.get_quote(instrument)
        except OandaQuoteFeedError as exc:
            _LOG.warning("record_quotes: skipping tick (OandaQuoteFeedError: %s)", exc)
        else:
            line = json.dumps(
                {"ts": quote.ts.isoformat(), "price": quote.price, "source": quote.source}
            )
            output.write(line + "\n")
            output.flush()
            written += 1
        if stop_requested():
            break
        sleep(interval_seconds)
    return written


# ---------------------------------------------------------------------------
# CLI wiring
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Args:
    instrument: str
    interval: float
    duration: float
    output: Path
    log_level: str


def _parse_args(argv: list[str]) -> _Args:
    parser = argparse.ArgumentParser(
        prog="record_quotes",
        description="Record OANDA quotes to a JSONL file for offline replay.",
    )
    parser.add_argument(
        "--instrument",
        required=True,
        help="Instrument to poll (e.g. EUR_USD).",
    )
    parser.add_argument(
        "--interval",
        type=float,
        required=True,
        help="Seconds between polls (e.g. 1.0).",
    )
    parser.add_argument(
        "--duration",
        type=float,
        required=True,
        help="Total wall-clock seconds to record before clean stop.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination JSONL file (created or appended to).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parsed = parser.parse_args(argv)
    if parsed.interval <= 0:
        parser.error("--interval must be > 0")
    if parsed.duration <= 0:
        parser.error("--duration must be > 0")
    return _Args(
        instrument=parsed.instrument,
        interval=parsed.interval,
        duration=parsed.duration,
        output=parsed.output,
        log_level=parsed.log_level,
    )


def _read_env(env: dict[str, str] | None = None) -> tuple[str, str, str]:
    src = env if env is not None else os.environ
    access_token = (src.get(_ENV_OANDA_ACCESS_TOKEN) or "").strip()
    account_id = (src.get(_ENV_OANDA_ACCOUNT_ID) or "").strip()
    environment = (src.get(_ENV_OANDA_ENVIRONMENT) or _DEFAULT_OANDA_ENVIRONMENT).strip()
    missing = [
        name
        for name, value in (
            (_ENV_OANDA_ACCESS_TOKEN, access_token),
            (_ENV_OANDA_ACCOUNT_ID, account_id),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("record_quotes: required OANDA env vars missing: " + ", ".join(missing))
    return access_token, account_id, environment


def _build_oanda_quote_feed(env: dict[str, str] | None = None) -> tuple[OandaQuoteFeed, str]:
    access_token, account_id, environment = _read_env(env)
    api_client = OandaAPIClient(access_token=access_token, environment=environment)
    feed = OandaQuoteFeed(api_client=api_client, account_id=account_id)
    return feed, account_id


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    try:
        feed, account_id = _build_oanda_quote_feed()
    except RuntimeError as exc:
        _LOG.error("%s", exc)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)

    # SIGINT → cooperative stop.  We *do not* swap the handler back: the
    # recorder runs to a duration and exits, so the original handler is
    # only relevant if the caller embeds main() in a longer-lived process,
    # which is not the documented use case.
    stop_flag = {"stop": False}

    def _on_sigint(_signum: int, _frame: object | None) -> None:
        stop_flag["stop"] = True
        _LOG.info("record_quotes: SIGINT received, stopping after current tick")

    signal.signal(signal.SIGINT, _on_sigint)

    max_iterations = max(1, int(args.duration / args.interval))
    _LOG.info(
        "record_quotes: starting (account=%s, instrument=%s, interval=%.3fs, "
        "duration=%.1fs, max_iterations=%d, output=%s)",
        account_id,
        args.instrument,
        args.interval,
        args.duration,
        max_iterations,
        args.output,
    )

    with args.output.open("a", encoding="utf-8") as f:
        written = record_quotes(
            feed=feed,
            instrument=args.instrument,
            output=f,
            interval_seconds=args.interval,
            max_iterations=max_iterations,
            stop_requested=lambda: stop_flag["stop"],
        )

    _LOG.info("record_quotes: stopped (quotes_written=%d, output=%s)", written, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------------------
# Re-exports to keep the test surface narrow / explicit.
# ---------------------------------------------------------------------------

__all__ = ["Quote", "main", "record_quotes"]
