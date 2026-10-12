"""RATES_ANCHORED_FX_CONVERGENCE の契約（合成の data だけ。実 data を読まない）。"""

from __future__ import annotations

import datetime as dt
import hashlib
import pathlib

import pytest

from scripts.research.rates_anchored_fx import data_rates as dr

REPO = pathlib.Path(__file__).resolve().parents[2]
HOLD = REPO / "docs/governance/fxid_long_term_hold_ruling_2026_10.md"


def test_hold_ruling_is_unchanged():
    raw = HOLD.read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(raw).hexdigest() == (
        "e7abc2f56c559d0965c551485dbc9d4e883af8acd66ebfb2e393954d9718e221"
    )


def test_request_windows_stay_inside_the_seen_span():
    ws = dr.windows()
    assert ws[0][0] == dt.datetime(2021, 4, 26, tzinfo=dt.UTC)
    assert ws[-1][1] == dt.datetime(2025, 12, 29, tzinfo=dt.UTC)
    for lo, hi in ws:
        dr.check_bounds(lo, hi)
        assert (hi - lo).days <= 45


@pytest.mark.parametrize(
    ("lo", "hi"),
    [
        (dt.datetime(2021, 4, 25, tzinfo=dt.UTC), dt.datetime(2021, 5, 1, tzinfo=dt.UTC)),
        (dt.datetime(2025, 12, 1, tzinfo=dt.UTC), dt.datetime(2025, 12, 30, tzinfo=dt.UTC)),
        (dt.datetime(2022, 1, 1), dt.datetime(2022, 2, 1)),
    ],
)
def test_out_of_span_or_naive_bounds_are_refused(lo, hi):
    with pytest.raises(dr.BoundaryError):
        dr.check_bounds(lo, hi)


def test_candle_times_outside_span_are_refused():
    with pytest.raises(dr.BoundaryError):
        dr.check_candle_times([dt.datetime(2021, 4, 25, 23, 45, tzinfo=dt.UTC)])
    with pytest.raises(dr.BoundaryError):
        dr.check_candle_times([dt.datetime(2025, 12, 29, 0, 0, tzinfo=dt.UTC)])
    dr.check_candle_times([dt.datetime(2025, 12, 28, 23, 45, tzinfo=dt.UTC)])


def test_time_parser_refuses_str_subclass_and_non_utc():
    class Evil(str):
        pass

    with pytest.raises(dr.BoundaryError):
        dr.parse_oanda_time(Evil("2021-05-01T00:00:00.000000000Z"))
    with pytest.raises(dr.BoundaryError):
        dr.parse_oanda_time("2021-05-01T00:00:00.000000000+01:00")
    assert dr.parse_oanda_time("2021-05-01T00:15:00.000000000Z") == dt.datetime(
        2021, 5, 1, 0, 15, tzinfo=dt.UTC
    )
