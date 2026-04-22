"""Unit tests: ``fx_ai_trading.ops.null_safe_stubs`` (M9 paper-loop runner scaffold).

Pins the contract that the wiring-verification stubs:
  - Short-circuit ``run_exit_gate`` by returning no positions.
  - Loudly raise on every other surface so a future regression that
    accidentally drives a real close path through them fails fast
    instead of silently dropping the trade.
"""

from __future__ import annotations

import pytest

from fx_ai_trading.domain.broker import OrderRequest
from fx_ai_trading.ops.null_safe_stubs import (
    NullBroker,
    NullExitPolicy,
    NullStateManager,
)


class TestNullStateManager:
    def test_account_id_property_returns_constructor_arg(self) -> None:
        sm = NullStateManager(account_id="acct-xyz")
        assert sm.account_id == "acct-xyz"

    def test_open_position_details_returns_empty_list(self) -> None:
        sm = NullStateManager(account_id="acct-1")
        assert sm.open_position_details() == []

    def test_on_close_raises_with_pointer_to_module(self) -> None:
        sm = NullStateManager(account_id="acct-1")
        with pytest.raises(RuntimeError, match="null_safe_stubs"):
            sm.on_close()


class TestNullBroker:
    def test_account_type_is_demo(self) -> None:
        # Defensive: 'demo' avoids tripping AccountTypeMismatchRuntime in
        # the inherited _verify_account_type_or_raise.  Wiring verification
        # mode never reaches that check, but we don't want a future
        # non-empty StateManager to surface a misleading error.
        assert NullBroker().account_type == "demo"

    def test_place_order_raises(self) -> None:
        req = OrderRequest(
            client_order_id="o-1",
            account_id="acct-1",
            instrument="EUR_USD",
            side="long",
            size_units=1,
        )
        with pytest.raises(RuntimeError, match="null_safe_stubs"):
            NullBroker().place_order(req)

    def test_cancel_order_raises(self) -> None:
        with pytest.raises(RuntimeError, match="null_safe_stubs"):
            NullBroker().cancel_order("o-1")

    def test_get_positions_raises(self) -> None:
        with pytest.raises(RuntimeError, match="null_safe_stubs"):
            NullBroker().get_positions("acct-1")

    def test_get_pending_orders_raises(self) -> None:
        with pytest.raises(RuntimeError, match="null_safe_stubs"):
            NullBroker().get_pending_orders("acct-1")

    def test_get_recent_transactions_raises(self) -> None:
        with pytest.raises(RuntimeError, match="null_safe_stubs"):
            NullBroker().get_recent_transactions("bookmark-1")


class TestNullExitPolicy:
    def test_evaluate_raises(self) -> None:
        with pytest.raises(RuntimeError, match="null_safe_stubs"):
            NullExitPolicy().evaluate(
                position_id="p-1",
                instrument="EUR_USD",
                side="long",
                current_price=1.10,
                tp=None,
                sl=None,
                holding_seconds=0,
                context={},
            )
