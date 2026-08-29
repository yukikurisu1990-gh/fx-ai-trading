"""The authorisation gate: nothing reaches data without a covering grant."""

from __future__ import annotations

import pytest

from scripts.m15_track_a import authorization
from scripts.m15_track_a.authorization import (
    AuthorizationError,
    AuthorizationMalformedError,
    ReadGrant,
    require_authorization,
)

_SHA = "0" * 40


def _grant(**overrides: object) -> ReadGrant:
    kwargs: dict[str, object] = {
        "operation": authorization.OPERATION_HISTORICAL_READ,
        "span_start_utc": "2025-04-25",
        "span_end_utc": "2026-02-28",
        "pairs": ("EUR_USD", "USD_JPY"),
        "timeframe": "M1",
        "approved_head_sha": _SHA,
        "approver_record": "PR #451 §8.13 approval record",
    }
    kwargs.update(overrides)
    return ReadGrant(**kwargs)  # type: ignore[arg-type]


def _require(grant: object, **overrides: object) -> ReadGrant:
    kwargs: dict[str, object] = {
        "operation": authorization.OPERATION_HISTORICAL_READ,
        "span_start_utc": "2025-05-01",
        "span_end_utc": "2025-06-01",
        "pairs": ("EUR_USD",),
        "timeframe": "M1",
    }
    kwargs.update(overrides)
    return require_authorization(grant, **kwargs)  # type: ignore[arg-type]


def test_no_grant_is_refused_with_the_token() -> None:
    with pytest.raises(AuthorizationError, match=authorization.TOKEN):
        _require(None)


def test_a_covering_grant_is_accepted() -> None:
    assert _require(_grant()) is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"span_start_utc": "2025-04-24"},  # one day before the grant
        {"span_end_utc": "2026-03-01"},  # one day after
        {"pairs": ("GBP_USD",)},  # a pair the grant omits
        {"timeframe": "M15"},  # a different timeframe
        {"operation": authorization.OPERATION_M15_DERIVATION},  # a different operation
    ],
)
def test_a_request_outside_the_grant_is_refused(overrides: dict[str, object]) -> None:
    with pytest.raises(AuthorizationError):
        _require(_grant(), **overrides)


def test_a_read_grant_does_not_authorise_a_derivation() -> None:
    """playbook §2.5: irreversible stages are separate gates with separate approvals."""
    read_grant = _grant(operation=authorization.OPERATION_HISTORICAL_READ)
    with pytest.raises(AuthorizationError):
        _require(read_grant, operation=authorization.OPERATION_M15_DERIVATION)


def test_a_non_grant_object_is_refused() -> None:
    class Impostor:
        def covers(self, **_: object) -> bool:
            return True

    with pytest.raises(AuthorizationError):
        _require(Impostor())


@pytest.mark.parametrize(
    "overrides",
    [
        {"operation": "something_else"},
        {"span_start_utc": "2026-02-28", "span_end_utc": "2025-04-25"},  # reversed
        {"span_start_utc": "25-04-2025"},  # not ISO
        {"span_start_utc": "2025-02-30"},  # not a real date
        {"pairs": ()},
        {"pairs": ("EUR_USD", "EUR_USD")},  # duplicate
        {"pairs": ["EUR_USD"]},  # a list, not a tuple
        {"approved_head_sha": "0" * 12},  # abbreviated
        {"approved_head_sha": "Z" * 40},  # not hex
        {"approver_record": "short"},
        {"timeframe": "  "},
    ],
)
def test_a_malformed_grant_cannot_be_constructed(overrides: dict[str, object]) -> None:
    with pytest.raises(AuthorizationMalformedError):
        _grant(**overrides)


def test_a_str_subclass_cannot_smuggle_a_head_sha() -> None:
    """A subclass may lie about its content, so the check pins plain ``str``."""

    class Sneaky(str):
        def __eq__(self, other: object) -> bool:  # pragma: no cover - never reached
            return True

        __hash__ = str.__hash__

    with pytest.raises(AuthorizationMalformedError):
        _grant(approved_head_sha=Sneaky(_SHA))


def test_as_record_round_trips_the_scope() -> None:
    record = _grant().as_record()
    assert record["operation"] == authorization.OPERATION_HISTORICAL_READ
    assert record["approved_head_sha"] == _SHA
    assert record["pairs"] == ["EUR_USD", "USD_JPY"]
