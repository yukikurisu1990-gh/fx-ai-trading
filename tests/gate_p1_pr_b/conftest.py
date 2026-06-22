"""Shared fixtures for Gate P1 PR-B.0 tests.

The ``guard_cleanup`` fixture guarantees that every guard is uninstalled after
each test even if the test installs guards directly, so monkey-patched global
state (os.environ wrappers, socket sentinels, write-allowlist) can never leak
into the pytest session and break unrelated tests.
"""

from __future__ import annotations

import pytest

from scripts._gate_p1_inspector.guards import bytecode as bytecode_guard
from scripts._gate_p1_inspector.guards import credentials as credentials_guard
from scripts._gate_p1_inspector.guards import filesystem as filesystem_guard
from scripts._gate_p1_inspector.guards import imports as imports_guard
from scripts._gate_p1_inspector.guards import network as network_guard
from scripts._gate_p1_inspector.guards import subprocess as subprocess_guard


@pytest.fixture(autouse=True)
def guard_cleanup():
    """Ensure all guards are uninstalled after each test."""
    yield
    for guard in (
        filesystem_guard,
        subprocess_guard,
        network_guard,
        credentials_guard,
        imports_guard,
        bytecode_guard,
    ):
        guard.uninstall()
