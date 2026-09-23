"""D-5 を受けた prospective rule — 保護暦日は request の段階で外す。"""

from __future__ import annotations

import datetime as dt

import pandas as pd
import pytest

from scripts.research.data_access import request_policy as rp
from scripts.research.mechanism_redesign import acquire


class _Sneaky(str):
    def __lt__(self, other):  # noqa: D105
        return True

    def __ge__(self, other):  # noqa: D105
        return False


@pytest.mark.parametrize("kind", [rp.POINT, rp.WEEK_ENDING, rp.MONTH, rp.QUARTER])
def test_seen_windows_never_touch_protected_reference_periods(kind) -> None:
    for first, last in rp.seen_request_windows(kind):
        start, end = rp.as_day(first, field="f"), rp.as_day(last, field="l")
        lo = rp.reference_period(start, kind)[0]
        hi = rp.reference_period(end, kind)[1]
        assert not rp.touches_protected(lo, hi)


def test_monthly_request_ending_in_june_2016_is_refused() -> None:
    with pytest.raises(rp.ProtectedRequestError):
        rp.check_request("1990-01-01", "2016-06-01", kind=rp.MONTH)
    rp.check_request("1990-01-01", "2016-05-01", kind=rp.MONTH)


def test_monthly_request_starting_in_april_2021_is_refused() -> None:
    with pytest.raises(rp.ProtectedRequestError):
        rp.check_request("2021-04-01", "2025-11-01", kind=rp.MONTH)
    with pytest.raises(rp.ProtectedRequestError):
        rp.check_request("2021-05-01", "2025-12-01", kind=rp.MONTH)


def test_point_request_spanning_the_gap_is_refused() -> None:
    with pytest.raises(rp.ProtectedRequestError):
        rp.check_request("2016-01-01", "2021-05-01", kind=rp.POINT)
    with pytest.raises(rp.ProtectedRequestError):
        rp.check_request("2025-01-01", "2025-12-27", kind=rp.POINT)
    rp.check_request("2021-04-27", "2025-12-26", kind=rp.POINT)


@pytest.mark.parametrize("bad", ["2016-06", "2016", "2016-6-01", 20160601, dt.date(2016, 6, 1)])
def test_bounds_must_be_exact_strings(bad) -> None:
    with pytest.raises(ValueError):
        rp.check_request("1990-01-01", bad, kind=rp.POINT)


def test_str_subclass_cannot_defeat_the_bound() -> None:
    with pytest.raises(ValueError):
        rp.check_request("1990-01-01", _Sneaky("2016-06-02"), kind=rp.POINT)


def test_bulk_only_providers_are_refused_without_an_exception() -> None:
    assert rp.APPROVED_BULK_EXCEPTIONS == {}
    for provider in rp.BULK_ONLY_PROVIDERS:
        with pytest.raises(rp.BulkOnlySourceRefusedError):
            rp.assert_provider_allowed(provider)
    rp.assert_provider_allowed("alfred")


def test_provider_ignoring_the_bound_is_rejected_not_filtered() -> None:
    stamps = pd.to_datetime(["2016-05-01", "2016-06-01"])
    with pytest.raises(rp.ProviderIgnoredBoundError):
        rp.assert_response_within(stamps, dt.date(1990, 1, 1), dt.date(2016, 5, 1), label="x")


def test_acquire_rejects_a_response_outside_the_request(monkeypatch) -> None:
    def fake_alfred(series_id, *, opt_in_env, first, last):
        index = pd.to_datetime([first, "2016-06-01"])
        return pd.Series([1.0, 2.0], index=index), {"source_url": "u", "title": "t", "units": "u"}

    monkeypatch.setattr(acquire.providers, "alfred", fake_alfred)
    with pytest.raises(rp.ProviderIgnoredBoundError):
        acquire._fetch_bounded("X", rp.MONTH)


def test_acquire_requests_only_seen_windows(monkeypatch) -> None:
    seen: list[tuple[str, str]] = []

    def fake_alfred(series_id, *, opt_in_env, first, last):
        seen.append((first, last))
        return pd.Series([1.0], index=pd.to_datetime([first])), {
            "source_url": "u",
            "title": "t",
            "units": "u",
        }

    monkeypatch.setattr(acquire.providers, "alfred", fake_alfred)
    acquire._fetch_bounded("X", rp.MONTH)
    assert seen == [("1990-01-01", "2016-05-01"), ("2021-05-01", "2025-11-01")]
