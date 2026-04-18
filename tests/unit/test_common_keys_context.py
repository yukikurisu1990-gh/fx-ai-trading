"""Unit tests for CommonKeysContext — pure Python, no DB required."""

from __future__ import annotations

import pytest

from fx_ai_trading.config.common_keys_context import CommonKeysContext

_VALID = {
    "run_id": "run-abc123",
    "environment": "demo",
    "code_version": "0.1.0",
    "config_version": "deadbeef01234567",
}


def test_construction_succeeds() -> None:
    ctx = CommonKeysContext(**_VALID)
    assert ctx.run_id == "run-abc123"
    assert ctx.environment == "demo"
    assert ctx.code_version == "0.1.0"
    assert ctx.config_version == "deadbeef01234567"


def test_frozen_prevents_mutation() -> None:
    ctx = CommonKeysContext(**_VALID)
    with pytest.raises((AttributeError, TypeError)):
        ctx.run_id = "other"  # type: ignore[misc]


def test_equality_by_value() -> None:
    ctx_a = CommonKeysContext(**_VALID)
    ctx_b = CommonKeysContext(**_VALID)
    assert ctx_a == ctx_b


def test_inequality_when_fields_differ() -> None:
    ctx_a = CommonKeysContext(**_VALID)
    ctx_b = CommonKeysContext(**{**_VALID, "environment": "live"})
    assert ctx_a != ctx_b


@pytest.mark.parametrize("field", ["run_id", "environment", "code_version", "config_version"])
def test_empty_string_raises(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        CommonKeysContext(**{**_VALID, field: ""})


@pytest.mark.parametrize("field", ["run_id", "environment", "code_version", "config_version"])
def test_whitespace_only_raises(field: str) -> None:
    with pytest.raises(ValueError, match=field):
        CommonKeysContext(**{**_VALID, field: "   "})


def test_hashable_usable_in_set() -> None:
    ctx = CommonKeysContext(**_VALID)
    assert ctx in {ctx}
