"""Track A R1 runs with everything off except one local historical read.

§8.13.5 items 3 and 4: no broker, no live, no demo, no order submission, no
external DB, no network — and the isolation is *proved rather than asserted*.

Why an audit hook is the primary control
----------------------------------------

The first draft of this module patched named functions: ``socket.socket.connect``,
``sqlalchemy.create_engine``, and so on.  An independent review defeated that
design six ways, and every defeat was the same shape — **a patched attribute
protects only the callers who look the attribute up afterwards**:

* ``_socket.socket.connect`` is a different object from ``socket.socket.connect``;
* ``asyncio``'s Windows proactor reaches the stack through ``ConnectEx`` and
  never touches the Python method at all;
* every DB module in this repository does ``from sqlalchemy import
  create_engine`` at **import** time, so it holds the original long before
  ``install_all()`` runs;
* ``subprocess`` and ``os.system`` leave the process entirely;
* ``socket.sendmsg`` exists on Linux and was not patched;
* and a ``tuple`` subclass can show the guard one destination through
  ``__getitem__`` while CPython reads another out of the raw slots.

``sys.addaudithook`` has none of those properties.  CPython raises its audit
events from inside the C implementation, **after** argument parsing and
**below** every Python-level alias, so one hook sees ``socket``, ``_socket``,
``asyncio``, a pre-bound ``create_engine``, a subprocess launch and a raw
``sqlite3.connect`` alike.  ``tests/conftest.py`` already reached this
conclusion for the ``.env`` guard — "guards 1-3 all patch a named function, so
they only see the routes they know about" — and this module now follows it.

The attribute patches are kept as a **second line**, because they produce a far
better error message at the call site than an audit hook can.  They are not the
mechanism.

What is refused
---------------

* **Network** — connect, datagram send, ``sendmsg``, and every name-resolution
  entry point, to anything that is not loopback.  Also any ``asyncio``
  connection attempt, unconditionally: R1 needs none.
* **Subprocess** — ``subprocess``, ``os.system``, ``os.exec*``, ``os.spawn*``.
  A subprocess escapes every in-process guard at once.
* **Database** — SQLAlchemy engines on anything but in-memory SQLite, and any
  ``sqlite3.connect`` to a file.
* **Writes inside the repository** that land outside the Track A scratch root.
  Build caches are exempt; the evidence tree is not.
* **Reads of the market-data trees** unless a gated read is in progress —
  :mod:`~scripts.m15_track_a.read_route` opens that window only after all of its
  gates pass, so ``pandas.read_json("data/candles_….jsonl")`` from anywhere else
  in the process is refused.  This is the limb that makes "one read route" a
  property of the **process** rather than a property of one function.
* **Broker / live / demo / order submission** — refused by name, so a call to
  one produces an error that says which prohibition it hit.

What this is not
----------------

It is **not** a sandbox, and it is not proof against code that is deliberately
attacking it from inside the same process.  Nothing in-process can be, because
such code can disarm any in-process guard — or simply do the forbidden thing
directly.  What these guards buy is that an **accidental** boundary crossing
fails loudly at the moment it happens, and that a **deliberate** one has to
appear in a diff as an explicit act.  That is the claim this module makes, and
it does not make a larger one.
"""

from __future__ import annotations

import ipaddress
import os
import socket
import sys
from dataclasses import dataclass, field
from pathlib import Path
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

#: Repository subtrees a run may write to even though they sit inside the repo.
#: Build and tool caches only — nothing that carries research meaning.
_WRITABLE_REPO_CACHES: Final[tuple[str, ...]] = (
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
)

#: Repository subtrees holding market data.  Reads refuse unless a gated read is
#: in progress.  ``artifacts/oanda_archive_*`` is matched by prefix.
_MARKET_DATA_ROOTS: Final[tuple[str, ...]] = ("data", "artifacts/oanda_archive")

#: Audit events that mean "a process is being launched".
_SUBPROCESS_EVENTS: Final[tuple[str, ...]] = (
    "subprocess.Popen",
    "os.system",
    "os.exec",
    "os.spawn",
    "os.posix_spawn",
    "os.startfile",
)

#: Audit events that mean "a name is being resolved on the network".
_RESOLUTION_EVENTS: Final[tuple[str, ...]] = (
    "socket.getaddrinfo",
    "socket.gethostbyname",
    "socket.gethostbyaddr",
)

#: Audit events that mean "bytes are leaving this machine".
_EGRESS_EVENTS: Final[tuple[str, ...]] = (
    "socket.connect",
    "socket.sendto",
    "socket.sendmsg",
)


class IsolationError(RuntimeError):
    """Raised when a Track A run reaches a boundary it may not cross."""


def _is_loopback(host_value: object) -> bool:
    """Whole loopback range, not four spellings of it.

    ``127.0.0.2`` and ``0:0:0:0:0:0:0:1`` are loopback too, CPython accepts a
    ``bytes`` host, and a name comparison has to be case-insensitive. Anything
    unrecognised is treated as remote.
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


def _destination_host(address: object) -> object | None:
    """The host an address tuple really names, or ``None`` for a local family.

    ``tuple.__getitem__`` is used rather than ``address[0]``: a ``tuple``
    subclass can override ``__getitem__`` to show a guard ``"localhost"`` while
    CPython's ``getsockaddrarg`` reads a remote host straight out of the raw
    slots. Reading the slot the C code reads closes that gap.
    """
    if not isinstance(address, tuple) or len(address) == 0:
        return None  # AF_UNIX and friends never leave the machine
    return tuple.__getitem__(address, 0)


def _check_destination(address: object, *, how: str) -> None:
    host = _destination_host(address)
    if host is None or _is_loopback(host):
        return
    raise IsolationError(
        f"{TOKEN}: a Track A run may not {how} {host!r}. §3.3 — network access is off for "
        "R1, which needs nothing but a local historical read."
    )


# ---------------------------------------------------------------------------
# The audit hook — the primary control
# ---------------------------------------------------------------------------

#: True while the guards are armed.  An audit hook cannot be removed once added,
#: so ``uninstall_all`` disarms rather than detaches, and the hook is a no-op
#: when disarmed.
_armed: bool = False

#: True while a gated historical read is in progress.  Only
#: :mod:`~scripts.m15_track_a.read_route` opens this window, and only after all
#: of its gates have passed.
_read_window_open: bool = False

_hook_installed: bool = False


def _repo_root() -> Path:
    # Imported lazily: ``scratch`` must not import this module back.
    from scripts.m15_track_a import scratch

    return scratch.repo_root()


def _scratch_root() -> Path:
    from scripts.m15_track_a import scratch

    return scratch.scratch_root()


def _relative_to_repo(raw: object) -> str | None:
    """The path as a POSIX-style repo-relative string, or ``None`` if outside."""
    if isinstance(raw, int):
        return None  # already-open file descriptor; the open that made it was seen
    try:
        candidate = Path(os.fsdecode(raw))
    except (TypeError, ValueError):
        return None
    try:
        resolved = candidate if candidate.is_absolute() else Path.cwd() / candidate
        relative = os.path.relpath(str(resolved), str(_repo_root()))
    except (OSError, ValueError):
        return None
    if relative.startswith(".."):
        return None
    return relative.replace(os.sep, "/")


def _is_write_mode(mode: object) -> bool:
    if isinstance(mode, int):
        return bool(mode & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC))
    text = str(mode)
    return any(flag in text for flag in ("w", "a", "x", "+"))


def _is_append_only(mode: object) -> bool:
    if isinstance(mode, int):
        return bool(mode & os.O_APPEND) and not bool(mode & os.O_TRUNC)
    text = str(mode)
    return "a" in text and "w" not in text and "+" not in text


def _check_append_only(args: tuple[Any, ...]) -> None:
    """A `BINDING_GOVERNANCE_RECORD` may be appended to and never rewritten.

    Checked against the **scratch root**, not against the repository: the
    scratch root is wherever the module constant points, and an append-only
    record is append-only there. One ``Path.write_text("")`` erases a ledger
    that ``SEEN_IS_TERMINAL_AND_NO_RULING_CAN_RESTORE_UNSEEN_STATUS`` says
    cannot be restored, and an append-only *API* binds only its own callers.
    """
    from scripts.m15_track_a import scratch

    try:
        candidate = Path(os.fsdecode(args[0]))
    except (TypeError, ValueError):
        return
    if candidate.name not in scratch.APPEND_ONLY_FILENAMES:
        return
    if not _is_write_mode(args[1]) or _is_append_only(args[1]):
        return
    try:
        root = scratch.scratch_root()
        resolved = candidate if candidate.is_absolute() else Path.cwd() / candidate
        inside = not os.path.relpath(str(resolved), str(root)).startswith("..")
    except (OSError, ValueError):  # pragma: no cover
        inside = False
    if inside:
        raise IsolationError(
            f"{TOKEN}: {candidate.name!r} is an append-only governance record and may not "
            "be opened for truncation or overwrite."
        )


def _check_open(args: tuple[Any, ...]) -> None:
    if len(args) < 2:
        return
    _check_append_only(args)
    relative = _relative_to_repo(args[0])
    if relative is None:
        return  # outside the repository: temp dirs, site-packages, the OS
    parts = relative.split("/")
    if any(part in _WRITABLE_REPO_CACHES for part in parts):
        return

    if _is_write_mode(args[1]):
        try:
            scratch_relative = os.path.relpath(str(_repo_root() / relative), str(_scratch_root()))
        except (OSError, ValueError):
            scratch_relative = ".."
        if scratch_relative.startswith(".."):
            raise IsolationError(
                f"{TOKEN}: a Track A run may not write to {relative!r}. Every write goes "
                "beneath the Track A scratch root; the repository's source, docs, data, "
                "models and evidence trees are read-only to a research run."
            )
        return

    if _read_window_open:
        return
    if any(relative == root or relative.startswith(root + "/") for root in _MARKET_DATA_ROOTS):
        raise IsolationError(
            f"{TOKEN}: a Track A run may not read {relative!r} outside the gated read "
            "route. Market data is reached through "
            "scripts.m15_track_a.read_route.read_historical, which requires an explicit "
            "authorisation grant, an admissible span and a prior seen-data declaration."
        )


def _audit_hook(event: str, args: tuple[Any, ...]) -> None:
    if not _armed:
        return
    if event in _EGRESS_EVENTS:
        if len(args) >= 2:
            _check_destination(args[1], how="reach")
        return
    if event in _RESOLUTION_EVENTS:
        if args and not _is_loopback(args[0]):
            raise IsolationError(
                f"{TOKEN}: a Track A run may not resolve {args[0]!r}. A name lookup reaches "
                "a resolver on the network before any connection is opened, so it is "
                "refused on the same footing as the connection."
            )
        return
    if event in _SUBPROCESS_EVENTS:
        raise IsolationError(
            f"{TOKEN}: a Track A run may not launch a process ({event}). A subprocess "
            "escapes every in-process guard at once — network, database and write "
            "containment alike."
        )
    if event == "sqlite3.connect":
        target = str(args[0]) if args else ""
        if target not in {":memory:", ""}:
            raise IsolationError(
                f"{TOKEN}: a Track A run may not open the database {target!r}. §3.2 — "
                "external DB access is off for R1."
            )
        return
    if event == "open":
        _check_open(args)


def install_audit_hook() -> None:
    """Arm the route-independent guard.  Idempotent; the hook is added once."""
    global _armed, _hook_installed
    if not _hook_installed:
        sys.addaudithook(_audit_hook)
        _hook_installed = True
    _armed = True


# ---------------------------------------------------------------------------
# Attribute patches — the second line, kept for their error messages
# ---------------------------------------------------------------------------


@dataclass
class _Installed:
    """What was patched, so a caller can undo it in a test."""

    network: bool = False
    connect: Any = None
    connect_ex: Any = None
    sendto: Any = None
    getaddrinfo: Any = None
    gethostbyname: Any = None
    asyncio_create_connection: Any = None
    engine_targets: list[tuple[Any, str, Any]] = field(default_factory=list)
    database: bool = False


_state: _Installed | None = None


def _ensure_state() -> _Installed:
    """The single mutable record.

    A previous drafting let :func:`install_database_guard` create ``_state`` as a
    side effect while :func:`install_network_guard` early-returned on
    ``_state is not None``. Installing the database guard first therefore left
    the network completely open while ``is_installed()`` answered True — the
    one condition both routes check. Each limb now carries its own flag and
    ``is_installed`` requires all three.
    """
    global _state
    if _state is None:
        _state = _Installed()
    return _state


def install_network_guard() -> None:
    """Refuse non-loopback TCP connects, UDP sends, name resolution and asyncio."""
    state = _ensure_state()
    if state.network:
        return

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
            raise IsolationError(f"{TOKEN}: a Track A run may not resolve {host!r}.")
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

    try:
        import asyncio.base_events

        state.asyncio_create_connection = asyncio.base_events.BaseEventLoop.create_connection

        async def refuse_create_connection(*_args: object, **_kwargs: object) -> object:
            raise IsolationError(
                f"{TOKEN}: a Track A run may not open an asyncio connection. R1 needs no "
                "network at all, and the Windows proactor reaches the stack below the "
                "socket methods."
            )

        asyncio.base_events.BaseEventLoop.create_connection = (  # type: ignore[method-assign]
            refuse_create_connection
        )
    except ImportError:  # pragma: no cover - asyncio is always present
        pass

    state.network = True


def install_database_guard() -> None:
    """Refuse any SQLAlchemy engine that is not in-memory SQLite.

    A no-op when SQLAlchemy is absent. Note this limb is **advisory**: a module
    that did ``from sqlalchemy import create_engine`` at import time holds the
    original, and this repository's DB modules all do. The audit hook's
    ``socket.connect`` and ``sqlite3.connect`` limbs are what actually stop the
    connection those callers would open.
    """
    state = _ensure_state()
    if state.database:
        return
    try:
        import sqlalchemy
        import sqlalchemy.engine
        import sqlalchemy.engine.create
    except ImportError:  # pragma: no cover - environment without SQLAlchemy
        state.database = True
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
        state.engine_targets.append((module, attribute, getattr(module, attribute)))
        setattr(module, attribute, guarded_create_engine)
    state.database = True


def assert_operation_allowed(operation: str) -> None:
    """Refuse a named forbidden operation.

    Unlike the audit hook this cannot be enforced structurally — there is no
    single primitive "submit an order" goes through — so it is a checkpoint a
    caller invokes. It is here so the prohibition has an executable form and an
    error message that names the boundary.
    """
    if operation in FORBIDDEN_OPERATIONS:
        raise IsolationError(
            f"{TOKEN}: {operation!r} is refused for Track A R1 — {FORBIDDEN_OPERATIONS[operation]}."
        )


def install_all() -> None:
    """Install every guard this module provides, audit hook first."""
    install_audit_hook()
    install_network_guard()
    install_database_guard()


def uninstall_all() -> None:
    """Disarm the guards.  For tests; a research run never calls it.

    The audit hook is **disarmed, not detached** — CPython provides no way to
    remove one, which is a property in this module's favour: the primary
    control cannot be unhooked, only switched off by code that could equally
    have called the forbidden thing directly.
    """
    global _state, _armed, _read_window_open
    _armed = False
    _read_window_open = False
    state = _state
    _state = None
    if state is None:
        return
    if state.network and state.connect is not None:
        socket.socket.connect = state.connect  # type: ignore[method-assign]
        socket.socket.connect_ex = state.connect_ex  # type: ignore[method-assign]
        socket.socket.sendto = state.sendto  # type: ignore[method-assign]
        socket.getaddrinfo = state.getaddrinfo  # type: ignore[assignment]
        socket.gethostbyname = state.gethostbyname  # type: ignore[assignment]
        if state.asyncio_create_connection is not None:
            import asyncio.base_events

            asyncio.base_events.BaseEventLoop.create_connection = (  # type: ignore[method-assign]
                state.asyncio_create_connection
            )
    for module, attribute, original in state.engine_targets:
        setattr(module, attribute, original)


def is_installed() -> bool:
    """True only when **every** limb is up.

    "Something was patched" is not the question a read route needs answered.
    """
    return bool(_armed and _state is not None and _state.network and _state.database)


def is_armed() -> bool:
    """True when the audit hook is armed, whatever else is installed."""
    return _armed


class gated_read_window:  # noqa: N801 - a context manager reads as a noun here
    """Open the market-data read window for the duration of a gated read.

    Only :mod:`~scripts.m15_track_a.read_route` uses this, and only after every
    gate has passed. Outside it, a read of ``data/`` or the archive is refused
    by the audit hook wherever in the process it originates — which is what
    makes "exactly one read route" a property of the process rather than a
    property of one function that a caller may simply decline to call.
    """

    def __enter__(self) -> gated_read_window:
        global _read_window_open
        if not _armed:
            raise IsolationError(
                f"{TOKEN}: the read window may not be opened while the guards are disarmed."
            )
        _read_window_open = True
        return self

    def __exit__(self, *_exc: object) -> None:
        global _read_window_open
        _read_window_open = False


def is_read_window_open() -> bool:
    return _read_window_open


__all__ = [
    "FORBIDDEN_OPERATIONS",
    "TOKEN",
    "IsolationError",
    "assert_operation_allowed",
    "gated_read_window",
    "install_all",
    "install_audit_hook",
    "install_database_guard",
    "install_network_guard",
    "is_armed",
    "is_installed",
    "is_read_window_open",
    "uninstall_all",
]
