"""Track A R1 runs with everything off except one local historical read.

§8.13.5 items 3 and 4: no broker, no live, no demo, no order submission, no
external DB, no network — and the isolation is *proved rather than asserted*.
Proving it in full is a containment audit (:mod:`scripts.m15_track_a.containment`);
what this module supplies is the **enforcement**, installed in-process, so that
a route which should not exist fails loudly at the moment it is used rather than
succeeding quietly.

Why in-process hooks and not a policy sentence
----------------------------------------------

§3.7 records the reason: "a research runner is by definition an **unrouted
caller**".  A guard that lives at one call site protects that call site.  The
guards here are installed on the primitives themselves — the socket, the engine
factory, the audit hook — so an import-time side effect or a transitive
dependency is covered too.  This is the same shape ``tests/conftest.py`` uses
for the test session, applied to a research run.

What is refused
---------------

* **Network** — any connect to a non-loopback address, and any UDP send or DNS
  resolution.  Loopback is permitted because a research run may legitimately
  talk to nothing but itself; the failure direction for anything unrecognised
  is closed.
* **Database** — any SQLAlchemy engine on a non-in-memory URL.
* **Broker / live / demo / order submission** — refused by name, so a call to
  one produces an error that says which prohibition it hit.

What is *not* refused
---------------------

Local file reads.  Track A exists to read local historical data once authorised,
and blocking file access here would block the thing the gate is being built for.
The read is gated by :mod:`~scripts.m15_track_a.authorization` and routed
through :mod:`~scripts.m15_track_a.read_route`; containment of *which* files is
that module's job, not this one's.
"""

from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass, field
from typing import Any, Final

TOKEN: Final[str] = "TRACK_A_R1_ISOLATION_ENFORCED"

#: Loopback host spellings that never leave the machine.
_LOOPBACK_NAMES: Final[frozenset[str]] = frozenset({"", "localhost", "localhost.localdomain"})

#: Engine URL schemes a research run may build.  In-memory SQLite only.
_SAFE_ENGINE_URLS: Final[frozenset[str]] = frozenset({"sqlite://", "sqlite:///:memory:"})

#: Named operations refused outright, with the boundary each one belongs to.
FORBIDDEN_OPERATIONS: Final[dict[str, str]] = {
    "broker_connect": "§3.1 — no broker connection",
    "broker_order_submit": "§3.1 — no order submission",
    "live_trading": "§3.1 — no live trading",
    "demo_trading": "§3.1 — no demo trading",
    "production_deploy": "§3 — no production deployment",
    "external_storage_write": "§3.4 — no external storage",
}


class IsolationError(RuntimeError):
    """Raised when a Track A run reaches a boundary it may not cross."""


def _is_loopback(host_value: object) -> bool:
    """Whole loopback range, not four spellings of it.

    Mirrors ``tests/conftest.py``'s helper deliberately: ``127.0.0.2`` and
    ``0:0:0:0:0:0:0:1`` are loopback too, CPython accepts a ``bytes`` host, and
    a name comparison has to be case-insensitive. Anything unrecognised is
    treated as remote.
    """
    host = (
        host_value.decode("ascii", "replace") if isinstance(host_value, bytes) else str(host_value)
    )
    if host.lower() in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _check_destination(address: object, *, how: str) -> None:
    if not isinstance(address, tuple) or not address:
        return  # AF_UNIX and friends never leave the machine
    host = address[0]
    if _is_loopback(host):
        return
    raise IsolationError(
        f"{TOKEN}: a Track A run may not {how} {host!r}. §3.3 — network access is off for "
        "R1, which needs nothing but a local historical read."
    )


@dataclass
class _Installed:
    """What was patched, so a caller can undo it in a test."""

    connect: Any = None
    connect_ex: Any = None
    sendto: Any = None
    getaddrinfo: Any = None
    gethostbyname: Any = None
    engine_targets: list[tuple[Any, str, Any]] = field(default_factory=list)


_state: _Installed | None = None


def install_network_guard() -> None:
    """Refuse non-loopback TCP connects, UDP sends and name resolution.

    The UDP and DNS limbs are here because the test-safety review recorded them
    as the socket guard's two residual routes: a ``connect``-only guard misses
    ``sendto``, and a name lookup reaches a resolver before any connect happens.
    """
    global _state
    if _state is not None:
        return
    state = _Installed()

    state.connect = socket.socket.connect
    state.connect_ex = socket.socket.connect_ex
    state.sendto = socket.socket.sendto
    state.getaddrinfo = socket.getaddrinfo
    state.gethostbyname = socket.gethostbyname

    real_connect = state.connect
    real_connect_ex = state.connect_ex
    real_sendto = state.sendto
    real_getaddrinfo = state.getaddrinfo
    real_gethostbyname = state.gethostbyname

    def guarded_connect(self: socket.socket, address: object) -> object:
        _check_destination(address, how="connect to")
        return real_connect(self, address)

    def guarded_connect_ex(self: socket.socket, address: object) -> object:
        _check_destination(address, how="connect to")
        return real_connect_ex(self, address)

    def guarded_sendto(self: socket.socket, data: object, *args: object) -> object:
        if args:
            _check_destination(args[-1], how="send a datagram to")
        return real_sendto(self, data, *args)

    def guarded_getaddrinfo(host: object, *args: object, **kwargs: object) -> object:
        if not _is_loopback(host):
            raise IsolationError(
                f"{TOKEN}: a Track A run may not resolve {host!r}. A name lookup reaches a "
                "resolver on the network before any connection is opened, so it is refused "
                "on the same footing as the connection."
            )
        return real_getaddrinfo(host, *args, **kwargs)

    def guarded_gethostbyname(host: object) -> object:
        if not _is_loopback(host):
            raise IsolationError(f"{TOKEN}: a Track A run may not resolve {host!r}.")
        return real_gethostbyname(host)

    socket.socket.connect = guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = guarded_connect_ex  # type: ignore[method-assign]
    socket.socket.sendto = guarded_sendto  # type: ignore[method-assign]
    socket.getaddrinfo = guarded_getaddrinfo  # type: ignore[assignment]
    socket.gethostbyname = guarded_gethostbyname  # type: ignore[assignment]
    _state = state


def install_database_guard() -> None:
    """Refuse any SQLAlchemy engine that is not in-memory SQLite.

    A no-op when SQLAlchemy is absent: a run that cannot build an engine needs
    no guard against building one.
    """
    global _state
    try:
        import sqlalchemy
        import sqlalchemy.engine
        import sqlalchemy.engine.create
    except ImportError:  # pragma: no cover - environment without SQLAlchemy
        return
    if _state is None:
        _state = _Installed()
    if _state.engine_targets:
        return

    real_create_engine = sqlalchemy.create_engine

    def guarded_create_engine(url: object, *args: object, **kwargs: object) -> object:
        text = str(
            getattr(url, "render_as_string", lambda **_: url)()
            if hasattr(url, "render_as_string")
            else url
        )
        if text not in _SAFE_ENGINE_URLS:
            raise IsolationError(
                f"{TOKEN}: a Track A run may not build a database engine for {text!r}. "
                "§3.2 — external DB access is off for R1."
            )
        return real_create_engine(url, *args, **kwargs)

    for module, attribute in (
        (sqlalchemy, "create_engine"),
        (sqlalchemy.engine, "create_engine"),
        (sqlalchemy.engine.create, "create_engine"),
    ):
        _state.engine_targets.append((module, attribute, getattr(module, attribute)))
        setattr(module, attribute, guarded_create_engine)


def assert_operation_allowed(operation: str) -> None:
    """Refuse a named forbidden operation.

    Unlike the socket and engine guards this cannot be enforced structurally —
    there is no single primitive "submit an order" goes through — so it is a
    checkpoint a caller invokes. It is here so the prohibition has an
    executable form and an error message that names the boundary.
    """
    if operation in FORBIDDEN_OPERATIONS:
        raise IsolationError(
            f"{TOKEN}: {operation!r} is refused for Track A R1 — {FORBIDDEN_OPERATIONS[operation]}."
        )


def install_all() -> None:
    """Install every guard this module provides."""
    install_network_guard()
    install_database_guard()


def uninstall_all() -> None:
    """Restore the patched primitives.  For tests; a research run never calls it."""
    global _state
    if _state is None:
        return
    if _state.connect is not None:
        socket.socket.connect = _state.connect  # type: ignore[method-assign]
        socket.socket.connect_ex = _state.connect_ex  # type: ignore[method-assign]
        socket.socket.sendto = _state.sendto  # type: ignore[method-assign]
        socket.getaddrinfo = _state.getaddrinfo  # type: ignore[assignment]
        socket.gethostbyname = _state.gethostbyname  # type: ignore[assignment]
    for module, attribute, original in _state.engine_targets:
        setattr(module, attribute, original)
    _state = None


def is_installed() -> bool:
    return _state is not None


__all__ = [
    "FORBIDDEN_OPERATIONS",
    "TOKEN",
    "IsolationError",
    "assert_operation_allowed",
    "install_all",
    "install_database_guard",
    "install_network_guard",
    "is_installed",
    "uninstall_all",
]
