"""Filesystem write-allowlist guard (plan §5 step 5).

Wraps the common write / create / delete primitives so that **only** writes
inside the resolved report directory, with a ``.json`` or ``.md`` extension,
are permitted. Everything else fails closed (raises
:class:`GuardViolationError`). Reads are never intercepted — PR-B is read-only
with respect to source inspection, and only its own report output is written.

The guard is parameterised by the report directory at install time. Directory
creation (``Path.mkdir`` / ``os.makedirs``) is permitted only at or below the
report directory; file writes additionally require an allowed extension.
"""

from __future__ import annotations

import builtins
import io
import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from ..tolerances import ALLOWED_OUTPUT_EXTENSIONS
from . import GuardViolationError

_report_dir: Path | None = None
_originals: dict[str, object] = {}

_WRITE_OPEN_FLAGS = frozenset({"w", "a", "x", "+"})


def _require_installed() -> Path:
    if _report_dir is None:
        raise GuardViolationError("filesystem guard: not installed (no report dir bound).")
    return _report_dir


def _within_report_dir(target: Path) -> bool:
    report_dir = _require_installed()
    resolved = target if target.is_absolute() else Path.cwd() / target
    resolved = Path(os.path.normpath(str(resolved)))
    return resolved == report_dir or report_dir in resolved.parents


def _check_file_write(path: object) -> None:
    target = Path(os.fspath(path))
    if not _within_report_dir(target):
        raise GuardViolationError(
            f"filesystem guard: write to '{target}' is outside the report dir "
            f"'{_require_installed()}' (plan §5 step 5)."
        )
    if target.suffix not in ALLOWED_OUTPUT_EXTENSIONS:
        raise GuardViolationError(
            f"filesystem guard: write to '{target}' has a disallowed extension "
            f"(only {sorted(ALLOWED_OUTPUT_EXTENSIONS)} permitted)."
        )


def _check_dir_write(path: object) -> None:
    target = Path(os.fspath(path))
    if not _within_report_dir(target):
        raise GuardViolationError(
            f"filesystem guard: directory operation on '{target}' is outside "
            f"the report dir '{_require_installed()}' (plan §5 step 5)."
        )


def _is_write_mode(mode: str) -> bool:
    return any(flag in mode for flag in _WRITE_OPEN_FLAGS)


def install(report_dir: str | os.PathLike[str]) -> None:
    """Install the write-allowlist bound to ``report_dir``."""
    global _report_dir
    if _originals:
        return
    _report_dir = Path(os.path.normpath(os.path.abspath(os.fspath(report_dir))))

    _originals["builtins.open"] = builtins.open
    _originals["io.open"] = io.open
    _originals["Path.write_text"] = Path.write_text
    _originals["Path.write_bytes"] = Path.write_bytes
    _originals["Path.touch"] = Path.touch
    _originals["Path.mkdir"] = Path.mkdir
    _originals["os.makedirs"] = os.makedirs
    _originals["os.remove"] = os.remove
    _originals["os.unlink"] = os.unlink
    _originals["os.rename"] = os.rename
    _originals["os.replace"] = os.replace
    _originals["os.rmdir"] = os.rmdir
    _originals["tempfile.mkstemp"] = tempfile.mkstemp
    _originals["tempfile.mkdtemp"] = tempfile.mkdtemp
    _originals["shutil.move"] = shutil.move
    _originals["shutil.rmtree"] = shutil.rmtree

    open_orig = _originals["builtins.open"]

    def guarded_open(file, mode="r", *args, **kwargs):
        if _is_write_mode(mode):
            _check_file_write(file)
        return open_orig(file, mode, *args, **kwargs)

    def guarded_write_text(self, *args, **kwargs):
        _check_file_write(self)
        return _originals["Path.write_text"](self, *args, **kwargs)

    def guarded_write_bytes(self, *args, **kwargs):
        _check_file_write(self)
        return _originals["Path.write_bytes"](self, *args, **kwargs)

    def guarded_touch(self, *args, **kwargs):
        _check_file_write(self)
        return _originals["Path.touch"](self, *args, **kwargs)

    def guarded_path_mkdir(self, *args, **kwargs):
        _check_dir_write(self)
        return _originals["Path.mkdir"](self, *args, **kwargs)

    def guarded_makedirs(name, *args, **kwargs):
        _check_dir_write(name)
        return _originals["os.makedirs"](name, *args, **kwargs)

    def _hard_blocked(name):
        def sentinel(*_args, **_kwargs):
            raise GuardViolationError(
                f"filesystem guard: {name} is prohibited; PR-B.0 never deletes, "
                "renames, or creates temp files (plan §5 step 5)."
            )

        return sentinel

    builtins.open = guarded_open
    io.open = guarded_open
    Path.write_text = guarded_write_text
    Path.write_bytes = guarded_write_bytes
    Path.touch = guarded_touch
    Path.mkdir = guarded_path_mkdir
    os.makedirs = guarded_makedirs
    os.remove = _hard_blocked("os.remove")
    os.unlink = _hard_blocked("os.unlink")
    os.rename = _hard_blocked("os.rename")
    os.replace = _hard_blocked("os.replace")
    os.rmdir = _hard_blocked("os.rmdir")
    tempfile.mkstemp = _hard_blocked("tempfile.mkstemp")
    tempfile.mkdtemp = _hard_blocked("tempfile.mkdtemp")
    shutil.move = _hard_blocked("shutil.move")
    shutil.rmtree = _hard_blocked("shutil.rmtree")


def uninstall() -> None:
    """Restore the original filesystem primitives."""
    global _report_dir
    if not _originals:
        return
    builtins.open = _originals["builtins.open"]
    io.open = _originals["io.open"]
    Path.write_text = _originals["Path.write_text"]
    Path.write_bytes = _originals["Path.write_bytes"]
    Path.touch = _originals["Path.touch"]
    Path.mkdir = _originals["Path.mkdir"]
    os.makedirs = _originals["os.makedirs"]
    os.remove = _originals["os.remove"]
    os.unlink = _originals["os.unlink"]
    os.rename = _originals["os.rename"]
    os.replace = _originals["os.replace"]
    os.rmdir = _originals["os.rmdir"]
    tempfile.mkstemp = _originals["tempfile.mkstemp"]
    tempfile.mkdtemp = _originals["tempfile.mkdtemp"]
    shutil.move = _originals["shutil.move"]
    shutil.rmtree = _originals["shutil.rmtree"]
    _originals.clear()
    _report_dir = None


@contextmanager
def activate(report_dir: str | os.PathLike[str]) -> Iterator[None]:
    """Context manager that installs the filesystem guard for its duration."""
    install(report_dir)
    try:
        yield
    finally:
        uninstall()
