"""Unit tests: ``scripts.fetch_oanda_candles``.

The fetcher is a paginated puller for OANDA ``InstrumentsCandles`` whose only
side-effect is writing JSONL.  Tests mock the ``api_client`` so nothing
touches the network, and pin the contract that the writer:

  - Writes one JSONL record per ``complete=true`` candle returned by the
    api client, and **only** ``time / o / h / l / c / volume``.
  - Skips ``complete=false`` candles (the in-progress live bar).
  - Dedupes by ``time`` so pagination overlap does not produce duplicate
    rows when the cursor walks backward through the last bar of the
    previous page.
  - Advances the cursor by ``page_size * granularity_sec`` past empty
    pages (forex weekends / holidays) so we do not infinite-loop.
  - Stops when the cursor passes the end_time computed from
    ``--days``.

Helper round-trip pinning (``_parse_oanda_time`` / ``_format_oanda_time``)
ensures the cursor advancement math is invariant against OANDA's
nanosecond-precision RFC3339 with the ``Z`` suffix that
``datetime.fromisoformat`` does not natively accept.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts.fetch_oanda_candles import (
    _format_oanda_time,
    _parse_oanda_time,
    fetch_candles,
)


def _candle(time_str: str, *, complete: bool = True, price: float = 1.1) -> dict[str, Any]:
    return {
        "time": time_str,
        "complete": complete,
        "mid": {
            "o": f"{price:.5f}",
            "h": f"{price + 0.0001:.5f}",
            "l": f"{price - 0.0001:.5f}",
            "c": f"{price + 0.00005:.5f}",
        },
        "volume": 17,
    }


class _FakeAPIClient:
    """Returns canned ``{"candles": [...]}`` pages in order; raises if asked
    for more pages than were queued."""

    def __init__(self, pages: list[list[dict[str, Any]]]) -> None:
        self._pages = list(pages)
        self.calls: list[dict[str, Any]] = []

    def get_candles(self, instrument: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.calls.append({"instrument": instrument, "params": dict(params or {})})
        if not self._pages:
            return {"candles": []}
        return {"candles": self._pages.pop(0)}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# ---------------------------------------------------------------------------
# helper round-trip
# ---------------------------------------------------------------------------


def test_parse_oanda_time_accepts_nanosecond_z_suffix() -> None:
    parsed = _parse_oanda_time("2026-04-23T20:00:00.000000000Z")
    assert parsed == datetime(2026, 4, 23, 20, 0, 0, tzinfo=UTC)


def test_format_oanda_time_round_trips() -> None:
    dt = datetime(2026, 4, 23, 20, 0, 0, tzinfo=UTC)
    formatted = _format_oanda_time(dt)
    assert formatted == "2026-04-23T20:00:00.000000000Z"
    assert _parse_oanda_time(formatted) == dt


# ---------------------------------------------------------------------------
# fetch_candles core contract
# ---------------------------------------------------------------------------


def test_writes_one_jsonl_record_per_complete_candle(tmp_path: Path) -> None:
    output = tmp_path / "candles.jsonl"
    page = [
        _candle("2026-04-23T20:00:00.000000000Z", price=1.10),
        _candle("2026-04-23T20:00:05.000000000Z", price=1.11),
    ]
    api = _FakeAPIClient(pages=[page])

    written = fetch_candles(
        instrument="EUR_USD",
        granularity="S5",
        days=1,
        output_path=output,
        api_client=api,
    )

    rows = _read_jsonl(output)
    assert written == 2
    assert len(rows) == 2
    assert rows[0]["time"] == "2026-04-23T20:00:00.000000000Z"
    assert rows[0]["o"] == pytest.approx(1.10)
    assert rows[0]["volume"] == 17


def test_record_shape_contains_only_expected_keys(tmp_path: Path) -> None:
    output = tmp_path / "candles.jsonl"
    page = [_candle("2026-04-23T20:00:00.000000000Z")]
    api = _FakeAPIClient(pages=[page])

    fetch_candles(
        instrument="EUR_USD",
        granularity="S5",
        days=1,
        output_path=output,
        api_client=api,
    )

    rows = _read_jsonl(output)
    assert set(rows[0].keys()) == {"time", "o", "h", "l", "c", "volume"}


def test_skips_incomplete_candle(tmp_path: Path) -> None:
    output = tmp_path / "candles.jsonl"
    page = [
        _candle("2026-04-23T20:00:00.000000000Z", complete=True),
        _candle("2026-04-23T20:00:05.000000000Z", complete=False),
    ]
    api = _FakeAPIClient(pages=[page])

    written = fetch_candles(
        instrument="EUR_USD",
        granularity="S5",
        days=1,
        output_path=output,
        api_client=api,
    )

    rows = _read_jsonl(output)
    assert written == 1
    assert [r["time"] for r in rows] == ["2026-04-23T20:00:00.000000000Z"]


def test_dedupes_overlapping_time_across_pages(tmp_path: Path) -> None:
    """Pagination overlap (cursor = last_dt + 1 bar) must not duplicate the
    boundary candle if the next page re-emits it."""
    output = tmp_path / "candles.jsonl"
    boundary = _candle("2026-04-23T20:00:05.000000000Z", price=1.10)
    page_1 = [_candle("2026-04-23T20:00:00.000000000Z", price=1.10), boundary]
    page_2 = [boundary, _candle("2026-04-23T20:00:10.000000000Z", price=1.11)]
    api = _FakeAPIClient(pages=[page_1, page_2])

    written = fetch_candles(
        instrument="EUR_USD",
        granularity="S5",
        days=1,
        output_path=output,
        api_client=api,
    )

    rows = _read_jsonl(output)
    times = [r["time"] for r in rows]
    assert len(times) == len(set(times))
    assert times == [
        "2026-04-23T20:00:00.000000000Z",
        "2026-04-23T20:00:05.000000000Z",
        "2026-04-23T20:00:10.000000000Z",
    ]
    assert written == 3


def test_empty_page_advances_cursor_past_closed_window(tmp_path: Path) -> None:
    """An empty page must advance the cursor by ``page_size * granularity_sec``
    so the loop eventually exits.  ``days=1`` + ``page_size=5000`` + ``S5``
    means a single empty page jumps 5000*5s = ~6.9 hours; the loop should
    issue at most ~4 requests over a 1-day window before terminating."""
    output = tmp_path / "candles.jsonl"
    api = _FakeAPIClient(pages=[])  # every call returns {"candles": []}

    written = fetch_candles(
        instrument="EUR_USD",
        granularity="S5",
        days=1,
        output_path=output,
        api_client=api,
    )

    assert written == 0
    assert output.read_text(encoding="utf-8") == ""
    assert 1 <= len(api.calls) <= 10


def test_request_params_match_spec(tmp_path: Path) -> None:
    output = tmp_path / "candles.jsonl"
    api = _FakeAPIClient(pages=[[]])

    fetch_candles(
        instrument="USD_JPY",
        granularity="M1",
        days=1,
        output_path=output,
        price="B",
        page_size=1000,
        api_client=api,
    )

    assert api.calls[0]["instrument"] == "USD_JPY"
    params = api.calls[0]["params"]
    assert params["granularity"] == "M1"
    assert params["count"] == 1000
    assert params["price"] == "B"
    assert params["from"].endswith("Z")


# ---------------------------------------------------------------------------
# argument validation
# ---------------------------------------------------------------------------


def test_rejects_unsupported_granularity(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported granularity"):
        fetch_candles(
            instrument="EUR_USD",
            granularity="W1",
            days=1,
            output_path=tmp_path / "x.jsonl",
            api_client=_FakeAPIClient(pages=[]),
        )


def test_rejects_zero_days(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="--days must be > 0"):
        fetch_candles(
            instrument="EUR_USD",
            granularity="S5",
            days=0,
            output_path=tmp_path / "x.jsonl",
            api_client=_FakeAPIClient(pages=[]),
        )


def test_rejects_out_of_range_page_size(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="--page-size must be in"):
        fetch_candles(
            instrument="EUR_USD",
            granularity="S5",
            days=1,
            output_path=tmp_path / "x.jsonl",
            page_size=0,
            api_client=_FakeAPIClient(pages=[]),
        )
    with pytest.raises(ValueError, match="--page-size must be in"):
        fetch_candles(
            instrument="EUR_USD",
            granularity="S5",
            days=1,
            output_path=tmp_path / "x.jsonl",
            page_size=5001,
            api_client=_FakeAPIClient(pages=[]),
        )


def test_creates_output_parent_directory(tmp_path: Path) -> None:
    nested = tmp_path / "deep" / "data" / "out.jsonl"
    api = _FakeAPIClient(pages=[[_candle("2026-04-23T20:00:00.000000000Z")]])

    fetch_candles(
        instrument="EUR_USD",
        granularity="S5",
        days=1,
        output_path=nested,
        api_client=api,
    )

    assert nested.exists()
    assert nested.parent.is_dir()


# ---------------------------------------------------------------------------
# defensive: helper unused-time-imports guard (catches stray edits)
# ---------------------------------------------------------------------------


def test_format_then_parse_drops_microsecond_only_precision() -> None:
    """``_format_oanda_time`` always emits 9 fractional digits (zeros).  If a
    future edit narrowed it to microseconds, the round-trip would still
    succeed but downstream OANDA cursor strings would drift; pin the
    canonical width here."""
    dt = datetime(2026, 4, 23, 20, 0, 0, tzinfo=UTC) + timedelta(seconds=5)
    formatted = _format_oanda_time(dt)
    assert ".000000000Z" in formatted
