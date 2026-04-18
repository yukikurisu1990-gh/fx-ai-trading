"""Common assertion helpers for startup-time contract validation (D3 §2.6.1 / 6.18).

Provides:
  assert_account_type_matches: validates broker.account_type == expected at startup.
    Raises AccountTypeMismatch (not AccountTypeMismatchRuntime) since this is a
    static configuration check, not a runtime order-time check.

Usage (M7 Supervisor startup — Step 9):
    from fx_ai_trading.common.assertions import assert_account_type_matches
    assert_account_type_matches(broker=broker, expected=config["account_type"])
"""

from __future__ import annotations

from fx_ai_trading.common.exceptions import AccountTypeMismatch
from fx_ai_trading.domain.broker import Broker

_VALID_ACCOUNT_TYPES = frozenset({"demo", "live"})


def assert_account_type_matches(broker: Broker, expected: str) -> None:
    """Assert broker.account_type == expected at startup.

    This is the static configuration guard (AccountTypeMismatch, not Runtime).
    Called once during the Supervisor startup sequence (M7 Step 9).
    For per-order runtime checks, Broker._verify_account_type_or_raise is used.

    Args:
        broker: Configured Broker instance.
        expected: Account type the system is configured to use ('demo' or 'live').

    Raises:
        ValueError: If expected is not 'demo' or 'live'.
        AccountTypeMismatch: If broker.account_type != expected.
    """
    if expected not in _VALID_ACCOUNT_TYPES:
        raise ValueError(
            f"expected must be one of {sorted(_VALID_ACCOUNT_TYPES)}, got {expected!r}"
        )
    if broker.account_type != expected:
        raise AccountTypeMismatch(
            f"Broker account_type {broker.account_type!r} does not match"
            f" configured expected {expected!r}. Startup aborted."
        )
