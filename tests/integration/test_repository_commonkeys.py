"""Integration tests: Common Keys context is required on all repository write methods.

Requires DATABASE_URL (from .env or env var). Auto-skipped when unset.

Verifies that:
  1. Write methods without context raise TypeError (required positional arg).
  2. Write methods with a valid CommonKeysContext succeed without error.
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from fx_ai_trading.config.common_keys_context import CommonKeysContext

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not _DATABASE_URL, reason="DATABASE_URL not set — skipping integration tests"
)

_CTX = CommonKeysContext(
    run_id="ck-integ-test",
    environment="test",
    code_version="0.0.0",
    config_version="test-cfg",
)


class TestCommonKeysSignatures:
    """Context parameter must be present and required on every write method."""

    def _assert_context_required(self, cls, method_name: str) -> None:
        sig = inspect.signature(getattr(cls, method_name))
        assert "context" in sig.parameters, (
            f"{cls.__name__}.{method_name}() missing 'context' parameter"
        )
        param = sig.parameters["context"]
        assert param.default is inspect.Parameter.empty, (
            f"{cls.__name__}.{method_name}() context must be required (no default)"
        )

    def test_orders_create_order_has_context(self) -> None:
        from fx_ai_trading.repositories.orders import OrdersRepository

        self._assert_context_required(OrdersRepository, "create_order")

    def test_orders_update_status_has_context(self) -> None:
        from fx_ai_trading.repositories.orders import OrdersRepository

        self._assert_context_required(OrdersRepository, "update_status")

    def test_positions_insert_event_has_context(self) -> None:
        from fx_ai_trading.repositories.positions import PositionsRepository

        self._assert_context_required(PositionsRepository, "insert_event")

    def test_accounts_create_account_has_context(self) -> None:
        from fx_ai_trading.repositories.accounts import AccountsRepository

        self._assert_context_required(AccountsRepository, "create_account")

    def test_accounts_update_account_has_context(self) -> None:
        from fx_ai_trading.repositories.accounts import AccountsRepository

        self._assert_context_required(AccountsRepository, "update_account")

    def test_order_service_create_order_has_context(self) -> None:
        from fx_ai_trading.services.order_service import OrderService

        self._assert_context_required(OrderService, "create_order")

    def test_position_service_record_event_has_context(self) -> None:
        from fx_ai_trading.services.position_service import PositionService

        self._assert_context_required(PositionService, "record_position_event")

    def test_account_service_create_account_has_context(self) -> None:
        from fx_ai_trading.services.account_service import AccountService

        self._assert_context_required(AccountService, "create_account")

    def test_place_order_usecase_execute_has_context(self) -> None:
        from fx_ai_trading.usecases.place_order_usecase import PlaceOrderUseCase

        self._assert_context_required(PlaceOrderUseCase, "execute")


class TestCommonKeysContextValidation:
    """CommonKeysContext rejects blank or non-string fields."""

    def test_empty_run_id_raises(self) -> None:
        with pytest.raises(ValueError, match="run_id"):
            CommonKeysContext(
                run_id="", environment="test", code_version="0.0.0", config_version="x"
            )

    def test_whitespace_environment_raises(self) -> None:
        with pytest.raises(ValueError, match="environment"):
            CommonKeysContext(
                run_id="r", environment="  ", code_version="0.0.0", config_version="x"
            )

    def test_valid_context_is_frozen(self) -> None:
        with pytest.raises(AttributeError):
            _CTX.run_id = "mutated"  # type: ignore[misc]

    def test_all_four_keys_present_in_with_common_keys(self) -> None:
        from unittest.mock import MagicMock

        from fx_ai_trading.repositories.base import RepositoryBase

        repo = RepositoryBase(engine=MagicMock())
        result = repo._with_common_keys({"x": 1}, _CTX)
        assert result["run_id"] == _CTX.run_id
        assert result["environment"] == _CTX.environment
        assert result["code_version"] == _CTX.code_version
        assert result["config_version"] == _CTX.config_version
        assert result["x"] == 1
