"""Unit tests for RepositoryBase — pure Python, no DB required."""

from __future__ import annotations

from unittest.mock import MagicMock

from fx_ai_trading.repositories.base import RepositoryBase


def _make_repo() -> RepositoryBase:
    engine = MagicMock()
    return RepositoryBase(engine=engine)


def test_engine_is_stored() -> None:
    engine = MagicMock()
    repo = RepositoryBase(engine=engine)
    assert repo._engine is engine


def test_apply_common_keys_is_no_op() -> None:
    repo = _make_repo()
    result = repo._apply_common_keys(context=object())
    assert result is None


def test_subclass_inherits_engine() -> None:
    class ConcreteRepo(RepositoryBase):
        pass

    engine = MagicMock()
    repo = ConcreteRepo(engine=engine)
    assert repo._engine is engine


def test_subclass_can_override_common_keys_hook() -> None:
    called_with: list[object] = []

    class ConcreteRepo(RepositoryBase):
        def _apply_common_keys(self, context: object) -> None:
            called_with.append(context)

    repo = ConcreteRepo(engine=MagicMock())
    ctx = object()
    repo._apply_common_keys(ctx)
    assert called_with == [ctx]
