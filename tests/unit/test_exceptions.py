"""Unit tests for the exception hierarchy (common/exceptions.py)."""

from __future__ import annotations

import pytest

from fx_ai_trading.common.exceptions import (
    AccountTypeMismatch,
    AccountTypeMismatchRuntime,
    ArchiveVerifyError,
    BaseError,
    ConfigError,
    ContractViolationError,
    CriticalWriteError,
    DeferExhausted,
    FeatureUnavailable,
    RepositoryError,
    SignalExpired,
)


class TestInheritance:
    def test_base_error_is_exception(self) -> None:
        assert issubclass(BaseError, Exception)

    def test_contract_violation_inherits_base(self) -> None:
        assert issubclass(ContractViolationError, BaseError)

    def test_account_type_mismatch_inherits_base(self) -> None:
        assert issubclass(AccountTypeMismatch, BaseError)

    def test_account_type_mismatch_runtime_inherits_base(self) -> None:
        assert issubclass(AccountTypeMismatchRuntime, BaseError)

    def test_signal_expired_inherits_base(self) -> None:
        assert issubclass(SignalExpired, BaseError)

    def test_defer_exhausted_inherits_base(self) -> None:
        assert issubclass(DeferExhausted, BaseError)

    def test_feature_unavailable_inherits_base(self) -> None:
        assert issubclass(FeatureUnavailable, BaseError)

    def test_repository_error_inherits_base(self) -> None:
        assert issubclass(RepositoryError, BaseError)

    def test_critical_write_error_inherits_repository(self) -> None:
        assert issubclass(CriticalWriteError, RepositoryError)

    def test_archive_verify_error_inherits_repository(self) -> None:
        assert issubclass(ArchiveVerifyError, RepositoryError)

    def test_config_error_inherits_base(self) -> None:
        assert issubclass(ConfigError, BaseError)


class TestRaisable:
    @pytest.mark.parametrize(
        "exc_class",
        [
            BaseError,
            ContractViolationError,
            AccountTypeMismatch,
            AccountTypeMismatchRuntime,
            SignalExpired,
            DeferExhausted,
            FeatureUnavailable,
            RepositoryError,
            CriticalWriteError,
            ArchiveVerifyError,
            ConfigError,
        ],
    )
    def test_can_be_raised_and_caught(self, exc_class) -> None:
        with pytest.raises(exc_class):
            raise exc_class("test message")

    def test_message_stored(self) -> None:
        exc = BaseError("hello")
        assert exc.message == "hello"
        assert str(exc) == "hello"

    def test_critical_write_caught_as_repository_error(self) -> None:
        with pytest.raises(RepositoryError):
            raise CriticalWriteError("db down")

    def test_all_caught_as_base_error(self) -> None:
        with pytest.raises(BaseError):
            raise AccountTypeMismatchRuntime("mismatch")
