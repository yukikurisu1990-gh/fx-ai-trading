"""fetch_oanda_candles — paginated S5/M1/etc candle puller from OANDA REST.

Why this exists
---------------
Tick-snapshot replay (`scripts/record_quotes.py`) is bounded by polling
cadence and per-day capture cost.  For multi-day momentum / forward-return
studies we need OHLC candles — which OANDA serves directly through
``InstrumentsCandles`` (already wrapped in ``OandaAPIClient.get_candles``).

This script pulls candles in pages of ``--page-size`` (max 5000 per
request, OANDA limit), starting at ``now - days_back`` and walking
forward.  Output is one JSON object per line.

For ``--price M`` (default):

    {"time":"2026-04-23T20:00:00.000000000Z","o":1.16800,"h":1.16805,
     "l":1.16798,"c":1.16802,"volume":17}

For ``--price BA`` (Phase 9.10 cost-aware backtest):

    {"time":"2026-04-23T20:00:00.000000000Z","volume":17,
     "bid_o":1.16798,"bid_h":1.16803,"bid_l":1.16796,"bid_c":1.16800,
     "ask_o":1.16802,"ask_h":1.16807,"ask_l":1.16800,"ask_c":1.16804}

For ``--price MBA`` both legacy ``o/h/l/c`` and ``bid_*``/``ask_*`` are
written on the same line.

Only ``complete=true`` candles are written (the live in-progress one is
skipped).  Duplicates by ``time`` are deduped (re-fetch overlap from
pagination edges is silently dropped).

Env / args
----------
  OANDA_ACCESS_TOKEN  required
  OANDA_ENVIRONMENT   default 'practice'
  --instrument        default EUR_USD
  --granularity       default S5
  --days              default 7
  --price             default M (mid only); B / A / BA / MBA also accepted
  --output            default data/candles_<inst>_<gran>_<from>_<to>.jsonl
  --page-size         default 5000

Forex weekends are closed: a 7-calendar-day pull on a weekday will
return roughly 5 trading days of candles.  Empty pages are interpreted
as "no data in this window" and we advance the cursor by ``page-size *
granularity_sec`` to skip past the closed period.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient

_GRANULARITY_SECONDS: dict[str, int] = {
    "S5": 5,
    "S10": 10,
    "S15": 15,
    "S30": 30,
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "M30": 1800,
    "H1": 3600,
}


def _parse_oanda_time(s: str) -> datetime:
    """OANDA returns nanosecond-precision RFC3339 with Z suffix.

    Python's ``datetime.fromisoformat`` accepts microsecond precision
    (6 digits) and ``+00:00``.  Truncate the fractional part to 6 digits
    and replace the trailing ``Z`` with ``+00:00``.
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


def _format_oanda_time(dt: datetime) -> str:
    """Format a UTC datetime as OANDA-style RFC3339 with nanosecond zeros."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")


_VALID_PRICE_MODES: frozenset[str] = frozenset({"M", "B", "A", "BA", "AB", "MBA", "MB", "MA"})


def _build_candle_record(c: dict, *, price: str) -> dict:
    """Shape one OANDA candle dict into the JSONL record per the price mode.

    ``price`` is OANDA's price component string (any ordering of the letters
    M/B/A).  The output record carries ``time``/``volume`` plus component-
    specific OHLC fields:

      - 'M' present → legacy ``o/h/l/c`` (mid)
      - 'B' present → ``bid_o/h/l/c``
      - 'A' present → ``ask_o/h/l/c``
    """
    want_mid = "M" in price
    want_bid = "B" in price
    want_ask = "A" in price

    rec: dict = {"time": c["time"], "volume": int(c.get("volume", 0))}

    if want_mid:
        mid = c.get("mid", {})
        rec["o"] = float(mid["o"])
        rec["h"] = float(mid["h"])
        rec["l"] = float(mid["l"])
        rec["c"] = float(mid["c"])
    if want_bid:
        bid = c.get("bid", {})
        rec["bid_o"] = float(bid["o"])
        rec["bid_h"] = float(bid["h"])
        rec["bid_l"] = float(bid["l"])
        rec["bid_c"] = float(bid["c"])
    if want_ask:
        ask = c.get("ask", {})
        rec["ask_o"] = float(ask["o"])
        rec["ask_h"] = float(ask["h"])
        rec["ask_l"] = float(ask["l"])
        rec["ask_c"] = float(ask["c"])
    return rec


def fetch_candles(
    *,
    instrument: str,
    granularity: str,
    days: int,
    output_path: Path,
    price: str = "M",
    page_size: int = 5000,
    api_client: OandaAPIClient | None = None,
) -> int:
    if granularity not in _GRANULARITY_SECONDS:
        raise ValueError(
            f"unsupported granularity {granularity!r}; supported: {sorted(_GRANULARITY_SECONDS)}"
        )
    if days <= 0:
        raise ValueError(f"--days must be > 0; got {days!r}")
    if not 1 <= page_size <= 5000:
        raise ValueError(f"--page-size must be in [1, 5000]; got {page_size!r}")
    if price not in _VALID_PRICE_MODES:
        raise ValueError(f"--price must be one of {sorted(_VALID_PRICE_MODES)}; got {price!r}")

    if api_client is None:
        token = (os.environ.get("OANDA_ACCESS_TOKEN") or "").strip()
        env = (os.environ.get("OANDA_ENVIRONMENT") or "practice").strip()
        if not token:
            raise RuntimeError("OANDA_ACCESS_TOKEN env var is not set")
        api_client = OandaAPIClient(access_token=token, environment=env)

    end_time = datetime.now(UTC).replace(microsecond=0)
    start_time = end_time - timedelta(days=days)
    granularity_sec = _GRANULARITY_SECONDS[granularity]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cursor = start_time
    seen: set[str] = set()
    written = 0
    requests = 0

    print(
        f"fetch start: instrument={instrument} granularity={granularity} "
        f"days={days} ({start_time.isoformat()} -> {end_time.isoformat()})"
    )

    with output_path.open("w", encoding="utf-8") as out_f:
        while cursor < end_time:
            params = {
                "granularity": granularity,
                "from": _format_oanda_time(cursor),
                "count": page_size,
                "price": price,
            }
            try:
                resp = api_client.get_candles(instrument, params=params)
            except Exception as exc:
                print(f"REQUEST FAILED at cursor={cursor.isoformat()}: {exc}", file=sys.stderr)
                break
            requests += 1

            candles = resp.get("candles", [])
            if not candles:
                cursor = cursor + timedelta(seconds=granularity_sec * page_size)
                print(f"  req#{requests}: empty page; advancing cursor by {page_size} bars")
                continue

            page_written = 0
            last_time_str: str | None = None
            for c in candles:
                if not c.get("complete", False):
                    continue
                t_str = c["time"]
                if t_str in seen:
                    continue
                seen.add(t_str)
                rec = _build_candle_record(c, price=price)
                out_f.write(json.dumps(rec) + "\n")
                page_written += 1
                last_time_str = t_str

            written += page_written
            print(
                f"  req#{requests}: candles={len(candles)} new_written={page_written} "
                f"total={written} last={last_time_str}"
            )

            if last_time_str is None:
                cursor = cursor + timedelta(seconds=granularity_sec * page_size)
                continue
            last_dt = _parse_oanda_time(last_time_str)
            cursor = last_dt + timedelta(seconds=granularity_sec)

    print(f"DONE: requests={requests} candles_written={written} -> {output_path}")
    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="fetch_oanda_candles")
    parser.add_argument("--instrument", default="EUR_USD")
    parser.add_argument("--granularity", default="S5", choices=sorted(_GRANULARITY_SECONDS))
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--price", default="M", choices=sorted(_VALID_PRICE_MODES))
    parser.add_argument("--page-size", type=int, default=5000)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL path. Default: data/candles_<inst>_<gran>_<days>d.jsonl",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_path = args.output
    if output_path is None:
        output_path = Path(f"data/candles_{args.instrument}_{args.granularity}_{args.days}d.jsonl")
    fetch_candles(
        instrument=args.instrument,
        granularity=args.granularity,
        days=args.days,
        output_path=output_path,
        price=args.price,
        page_size=args.page_size,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
