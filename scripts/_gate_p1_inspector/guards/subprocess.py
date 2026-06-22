"""Subprocess-prohibition guard (plan §5 step 4).

Replaces the subprocess / os process-spawn / multiprocessing entrypoints with
sentinels that fail closed (raise :class:`GuardViolationError`) on invocation.
The inner inspector must never spawn a child process: all process spawning is
the outer launcher's responsibility and happens *before* guards are installed
in the inner runtime.

Module name note: this module is ``scripts._gate_p1_inspector.guards.subprocess``.
Absolute imports below resolve ``import subprocess`` to the standard-library
module, not this file.
"""

from __future__ import annotations

import multiprocessing
import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager

from . import GuardViolationError

_originals: dict[str, object] = {}


def _blocked(name: str):
    def sentinel(*_args, **_kwargs):
        raise GuardViolationError(
            f"subprocess guard: process spawn via {name} is prohibited from "
            "the inner inspector (plan §5 step 4)."
        )

    return sentinel


def install() -> None:
    """Replace subprocess / process-spawn primitives with HALT sentinels."""
    if _originals:
        return
    _originals["subprocess.run"] = subprocess.run
    _originals["subprocess.Popen"] = subprocess.Popen
    _originals["subprocess.call"] = subprocess.call
    _originals["subprocess.check_output"] = subprocess.check_output
    _originals["subprocess.check_call"] = subprocess.check_call
    _originals["os.system"] = os.system
    _originals["multiprocessing.Process"] = multiprocessing.Process

    subprocess.run = _blocked("subprocess.run")
    subprocess.Popen = _blocked("subprocess.Popen")
    subprocess.call = _blocked("subprocess.call")
    subprocess.check_output = _blocked("subprocess.check_output")
    subprocess.check_call = _blocked("subprocess.check_call")
    os.system = _blocked("os.system")
    multiprocessing.Process = _blocked("multiprocessing.Process")


def uninstall() -> None:
    """Restore the original subprocess / process-spawn primitives."""
    if not _originals:
        return
    subprocess.run = _originals["subprocess.run"]
    subprocess.Popen = _originals["subprocess.Popen"]
    subprocess.call = _originals["subprocess.call"]
    subprocess.check_output = _originals["subprocess.check_output"]
    subprocess.check_call = _originals["subprocess.check_call"]
    os.system = _originals["os.system"]
    multiprocessing.Process = _originals["multiprocessing.Process"]
    _originals.clear()


@contextmanager
def activate() -> Iterator[None]:
    """Context manager that installs the subprocess guard for its duration."""
    install()
    try:
        yield
    finally:
        uninstall()
