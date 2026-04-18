"""Unit tests for RepositoryBase — pure Python, no DB required."""

from __future__ import annotations

from unittest.mock import MagicMock

from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.repositories.base import RepositoryBase

_CTX = CommonKeysContext(
    run_id="run-test",
    environment="test",
    code_version="0.0.0",
    config_version="abc123",
)


def _make_repo() -> RepositoryBase:
    engine = MagicMock()
    return RepositoryBase(engine=engine)


def test_engine_is_stored() -> None:
    engine = MagicMock()
    repo = RepositoryBase(engine=engine)
    assert repo._engine is engine


def test_with_common_keys_merges_context() -> None:
    repo = _make_repo()
    result = repo._with_common_keys({"col": "val"}, _CTX)
    assert result["col"] == "val"
    assert result["run_id"] == "run-test"
    assert result["environment"] == "test"
    assert result["code_version"] == "0.0.0"
    assert result["config_version"] == "abc123"


def test_with_common_keys_does_not_mutate_original() -> None:
    repo = _make_repo()
    params: dict = {"col": "val"}
    repo._with_common_keys(params, _CTX)
    assert "run_id" not in params


def test_subclass_inherits_engine() -> None:
    class ConcreteRepo(RepositoryBase):
        pass

    engine = MagicMock()
    repo = ConcreteRepo(engine=engine)
    assert repo._engine is engine


def test_subclass_inherits_with_common_keys() -> None:
    class ConcreteRepo(RepositoryBase):
        pass

    repo = ConcreteRepo(engine=MagicMock())
    result = repo._with_common_keys({}, _CTX)
    assert result["run_id"] == "run-test"
