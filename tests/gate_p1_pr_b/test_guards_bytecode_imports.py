"""Bytecode + production-import guard tests (plan §10)."""

from __future__ import annotations

import contextlib
import importlib
import sys

import pytest

from scripts._gate_p1_inspector.guards import GuardViolationError
from scripts._gate_p1_inspector.guards import bytecode as bytecode_guard
from scripts._gate_p1_inspector.guards import imports as imports_guard


@contextlib.contextmanager
def _ensure_not_cached(name: str):
    """Evict ``name`` (and its submodules) from sys.modules, restore after.

    Python's import system consults ``sys.meta_path`` finders only for modules
    that are NOT already cached. To prove the guard finder fires on a fresh
    import, we must evict any pre-imported copy first (other tests in the same
    session may have imported it) and restore it afterwards.
    """
    saved = {k: v for k, v in sys.modules.items() if k == name or k.startswith(name + ".")}
    for key in saved:
        del sys.modules[key]
    try:
        yield
    finally:
        sys.modules.update(saved)


def test_bytecode_guard_passes_when_disabled(monkeypatch):
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    bytecode_guard.assert_bytecode_disabled()  # no raise


def test_bytecode_guard_halts_when_enabled(monkeypatch):
    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    with pytest.raises(GuardViolationError):
        bytecode_guard.assert_bytecode_disabled()


def test_import_guard_blocks_production_stage_module():
    name = "scripts.stage23_0a_build_outcome_dataset"
    with _ensure_not_cached(name), imports_guard.activate(), pytest.raises(GuardViolationError):
        importlib.import_module(name)


def test_import_guard_blocks_src_package():
    name = "fx_ai_trading"
    with _ensure_not_cached(name), imports_guard.activate(), pytest.raises(GuardViolationError):
        importlib.import_module(name)


def test_import_guard_blocks_fetch_module():
    name = "scripts.fetch_oanda_candles"
    with _ensure_not_cached(name), imports_guard.activate(), pytest.raises(GuardViolationError):
        importlib.import_module(name)


def test_import_guard_allows_stdlib():
    with imports_guard.activate():
        json_mod = importlib.import_module("json")
        assert hasattr(json_mod, "dumps")


def test_import_guard_removed_after_context():
    before = len(sys.meta_path)
    with imports_guard.activate():
        assert len(sys.meta_path) == before + 1
    assert len(sys.meta_path) == before
