"""Bytecode-write guard (plan §5 step 1).

The outer launcher invokes the inner process with ``python -B`` so the inner
never writes ``.pyc`` files. This guard verifies that invariant survived into
the inner runtime. It performs no patching; it only asserts the interpreter
state and HALTs (raises :class:`GuardViolationError`) if bytecode writing is
enabled.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from contextlib import contextmanager

from . import GuardViolationError


def assert_bytecode_disabled() -> None:
    """HALT unless ``sys.dont_write_bytecode`` is True."""
    if not sys.dont_write_bytecode:
        raise GuardViolationError(
            "bytecode guard: sys.dont_write_bytecode is False; the inner "
            "process must run under `python -B` (plan §5 step 1)."
        )


def install() -> None:
    """Install the bytecode guard (assert-only; no patching)."""
    assert_bytecode_disabled()


def uninstall() -> None:
    """No-op; the bytecode guard holds no patched state."""


@contextmanager
def activate() -> Iterator[None]:
    """Context manager that asserts bytecode writing is disabled on entry."""
    install()
    try:
        yield
    finally:
        uninstall()
