"""Subprocess guard tripwire tests (plan §10)."""

from __future__ import annotations

import multiprocessing
import os
import subprocess

import pytest

from scripts._gate_p1_inspector.guards import GuardViolationError
from scripts._gate_p1_inspector.guards import subprocess as subprocess_guard


def test_subprocess_run_blocked():
    with subprocess_guard.activate(), pytest.raises(GuardViolationError):
        subprocess.run(["echo", "hi"], check=False)


def test_subprocess_popen_blocked():
    with subprocess_guard.activate(), pytest.raises(GuardViolationError):
        subprocess.Popen(["echo", "hi"])


def test_os_system_blocked():
    with subprocess_guard.activate(), pytest.raises(GuardViolationError):
        os.system("echo hi")


def test_multiprocessing_process_blocked():
    with subprocess_guard.activate(), pytest.raises(GuardViolationError):
        multiprocessing.Process(target=len, args=("",))


def test_subprocess_restored_after_context():
    with subprocess_guard.activate():
        pass
    # Restored: a benign call works again.
    result = subprocess.run(["git", "--version"], check=False, capture_output=True)
    assert result.returncode == 0
