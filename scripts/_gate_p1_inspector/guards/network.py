"""Network-prohibition guard (plan §5 step 3).

Replaces the common socket / urllib / http.client network entrypoints with
sentinels that fail closed (raise :class:`GuardViolationError`) on invocation.
PR-B performs no network access of any kind; the guard makes any accidental
attempt a hard HALT rather than a silent connection.
"""

from __future__ import annotations

import http.client
import socket
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager

from . import GuardViolationError

_originals: dict[str, object] = {}


def _blocked(name: str):
    def sentinel(*_args, **_kwargs):
        raise GuardViolationError(
            f"network guard: network access via {name} is prohibited (plan §5 step 3)."
        )

    return sentinel


def install() -> None:
    """Replace network primitives with HALT sentinels."""
    if _originals:
        return
    _originals["socket.socket"] = socket.socket
    _originals["socket.create_connection"] = socket.create_connection
    _originals["urllib.request.urlopen"] = urllib.request.urlopen
    _originals["http.client.HTTPConnection"] = http.client.HTTPConnection
    _originals["http.client.HTTPSConnection"] = http.client.HTTPSConnection

    socket.socket = _blocked("socket.socket")
    socket.create_connection = _blocked("socket.create_connection")
    urllib.request.urlopen = _blocked("urllib.request.urlopen")
    http.client.HTTPConnection = _blocked("http.client.HTTPConnection")
    http.client.HTTPSConnection = _blocked("http.client.HTTPSConnection")


def uninstall() -> None:
    """Restore the original network primitives."""
    if not _originals:
        return
    socket.socket = _originals["socket.socket"]
    socket.create_connection = _originals["socket.create_connection"]
    urllib.request.urlopen = _originals["urllib.request.urlopen"]
    http.client.HTTPConnection = _originals["http.client.HTTPConnection"]
    http.client.HTTPSConnection = _originals["http.client.HTTPSConnection"]
    _originals.clear()


@contextmanager
def activate() -> Iterator[None]:
    """Context manager that installs the network guard for its duration."""
    install()
    try:
        yield
    finally:
        uninstall()
