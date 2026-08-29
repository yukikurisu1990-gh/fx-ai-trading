"""Track A R1 runs with everything off except one local historical read.

§8.13.5 items 3 and 4: no broker, no live, no demo, no order submission, no
external DB, no network — and the isolation is *proved rather than asserted*.

Why an audit hook is the primary control
----------------------------------------

The first draft of this module patched named functions: ``socket.socket.connect``,
``sqlalchemy.create_engine``, and so on.  An independent review defeated that
design six ways, and every defeat was the same shape — **a patched attribute
protects only the callers who look the attribute up afterwards**:
``_socket.socket.connect`` is a different object; ``asyncio``'s Windows proactor
reaches the stack through ``ConnectEx``; every DB module in this repository does
``from sqlalchemy import create_engine`` at **import** time; ``subprocess`` and
``os.system`` leave the process; ``socket.sendmsg`` was unpatched; and a
``tuple`` subclass can show the guard one destination while CPython reads
another out of the raw slots.

``sys.addaudithook`` has none of those properties: CPython raises its audit
events from inside the C implementation, below every Python-level alias.

Why the *second* draft was wrong too, and what changed
------------------------------------------------------

A fresh re-verification then defeated the audit-hook draft in four more ways,
all of them created by that rewrite:

* it handled the ``open`` event and **no other filesystem event**, so
  ``os.rename``, ``os.remove``, ``os.truncate``, ``os.link``, ``os.mkdir`` and
  friends walked straight past it — and ``os.rename`` of a candle file out of
  the repository, followed by an ordinary read, was a complete escape;
* for ``os.open`` CPython passes ``mode=None`` and puts the flags in the
  **third** argument, so a mode-only test answered "not a write" and
  ``os.open(..., O_WRONLY | O_TRUNC)`` truncated an append-only ledger;
* the market-data prefix test was a raw ``startswith`` on
  ``"artifacts/oanda_archive"`` + ``"/"``, which does not match the directory
  that actually exists, ``artifacts/oanda_archive_2026-05-31/`` — the entire
  committed 10-year archive was readable;
* and the hook imported :mod:`~scripts.m15_track_a.scratch` **lazily, from
  inside itself**, so the import's own ``open`` calls re-entered the hook
  against a half-initialised module and ``install_all()`` crashed in any
  process that had not already imported ``scratch``.

So: every path-bearing audit event is handled, the ``open`` event's flags are
read when its mode is ``None``, paths are normalised (case, ``\\?\\``, symlinks)
before any prefix test, and ``scratch`` is imported at module scope.

What is refused
---------------

* **Network** — connect, datagram send, ``sendmsg``, and every name-resolution
  entry point, to anything that is not loopback.  Also any ``asyncio``
  connection attempt, unconditionally: R1 needs none.
* **Subprocess** — a subprocess escapes every in-process guard at once.
* **Database** — SQLAlchemy engines on anything but in-memory SQLite, and any
  ``sqlite3.connect`` to a file.
* **Every mutating filesystem operation inside the repository** that lands
  outside the Track A scratch root — create, write, append, truncate, rename,
  replace, delete, mkdir, rmdir, link, symlink, chmod, utime, copy, move.
  Build caches are exempt; the evidence tree is not.
* **Reads of the market-data trees** unless a gated read is in progress.
* **Broker / live / demo / order submission** — refused by name.

What this is not
----------------

It is **not** a sandbox, and it is not proof against code deliberately
attacking it from inside the same process: such code can disarm any in-process
guard, or simply do the forbidden thing directly. What these guards buy is that
an **accidental** boundary crossing fails loudly at the moment it happens, and
that a deliberate one has to appear in a diff as an explicit act.

Two limits worth naming rather than hiding. A **hardlink** already created
inside the scratch root cannot be distinguished from an ordinary file by any
path test — the defence against it is that ``os.link`` is itself refused. And
the hook costs roughly **5x** on ``open``; that is affordable for a research
run and would not be for a hot loop.
"""

from __future__ import annotations

import contextvars
import functools
import ipaddress
import os
import pathlib
import socket
import sys
import threading
from dataclasses import dataclass, field
from typing import Any, Final

from scripts.m15_track_a import scratch

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

#: Repository directory names a run may write inside even though they sit in the
#: repo.  Build and tool caches only — nothing that carries research meaning.
#: ``.git`` is deliberately **absent**: a research run has no business writing
#: hooks or config, and an earlier drafting listed it.
_WRITABLE_REPO_CACHES: Final[frozenset[str]] = frozenset(
    {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
)

#: First-level repository entries holding market data.  Matched on the **path
#: component**, and ``artifacts/oanda_archive*`` by component prefix, because
#: the directory on disk is ``artifacts/oanda_archive_2026-05-31``.
_MARKET_DATA_DIRS: Final[tuple[str, ...]] = ("data",)
_MARKET_DATA_ARTIFACT_PREFIXES: Final[tuple[str, ...]] = ("oanda_archive",)

#: Audit events that mean "a process is being launched".
_SUBPROCESS_EVENTS: Final[frozenset[str]] = frozenset(
    {"subprocess.Popen", "os.system", "os.exec", "os.spawn", "os.posix_spawn", "os.startfile"}
)

#: Audit events that mean "a name is being resolved on the network".
_RESOLUTION_EVENTS: Final[frozenset[str]] = frozenset(
    {"socket.getaddrinfo", "socket.gethostbyname", "socket.gethostbyaddr"}
)

#: Audit events that mean "bytes are leaving this machine".
_EGRESS_EVENTS: Final[frozenset[str]] = frozenset(
    {"socket.connect", "socket.sendto", "socket.sendmsg"}
)

#: Path-bearing audit events that **mutate**, and how many leading arguments are
#: paths.  ``os.replace`` raises ``os.rename``; ``shutil.move`` raises both its
#: own event and the underlying ones.
_MUTATING_PATH_EVENTS: Final[dict[str, int]] = {
    "os.rename": 2,
    "os.remove": 1,
    "os.unlink": 1,
    "os.mkdir": 1,
    "os.rmdir": 1,
    "os.truncate": 1,
    "os.link": 2,
    "os.symlink": 2,
    "os.chmod": 1,
    "os.chown": 1,
    "os.utime": 1,
    "shutil.copyfile": 2,
    "shutil.copymode": 2,
    "shutil.copystat": 2,
    "shutil.move": 2,
    "shutil.unpack_archive": 2,
}


class IsolationError(RuntimeError):
    """Raised when a Track A run reaches a boundary it may not cross."""


# ---------------------------------------------------------------------------
# Destinations
# ---------------------------------------------------------------------------


def _is_loopback(host_value: object) -> bool:
    """Whole loopback range, not four spellings of it.

    The host is pinned to an exact ``str``/``bytes`` first. A ``str`` subclass
    can override ``__str__`` to show a guard ``"localhost"`` while CPython's
    ``"et"`` argument converter reads the real buffer, so anything that is not
    exactly one of those two types is treated as **remote**.
    """
    if type(host_value) is bytes:
        host = host_value.decode("ascii", "replace")
    elif type(host_value) is str:
        host = host_value
    else:
        return False
    if host.lower() in _LOOPBACK_NAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _destination_host(address: object) -> object | None:
    """The host an address tuple really names, or ``None`` for a local family.

    Both ``tuple.__len__`` and ``tuple.__getitem__`` are called unbound: a
    ``tuple`` subclass can override either — reporting length 0 so the guard
    treats the address as a local family, or returning a loopback host from
    ``__getitem__`` — while CPython's ``getsockaddrarg`` reads the raw slots.
    """
    if not isinstance(address, tuple):
        return None  # AF_UNIX and friends never leave the machine
    if tuple.__len__(address) == 0:
        return None
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
# Paths
# ---------------------------------------------------------------------------

_EXTENDED_PREFIXES: Final[tuple[tuple[str, str], ...]] = (
    ("\\\\?\\UNC\\", "\\\\"),
    ("//?/UNC/", "\\\\"),
    ("\\\\?\\", ""),
    ("//?/", ""),
)


def _normalise(raw: object) -> str | None:
    """An absolute, link-resolved, case-normalised path, or ``None`` if unclassifiable.

    ``realpath`` is used for **every** decision, reads included. An earlier
    drafting used the cheaper ``abspath`` on the read path only, and a
    re-verification walked straight through it: measured on this machine,
    ``realpath`` expands an 8.3 short name (``FX-AI-~1`` → ``fx-ai-trading``),
    resolves the ``\\.\\`` device namespace and follows a junction, while
    ``abspath`` does none of those. A junction inside the scratch root pointing
    at ``data/`` returned real bytes through the read guard.

    What ``realpath`` does **not** normalise — also measured — is the UNC form
    ``\\localhost\\C$\\…``, which addresses the same volume by another name.
    That is what :func:`_inside_protected` is for.
    """
    if isinstance(raw, int):
        return None  # an already-open descriptor: the open that made it was seen
    try:
        text = os.fsdecode(raw)
    except (TypeError, ValueError):
        return None
    if not text:
        return None
    for prefix, replacement in _EXTENDED_PREFIXES:
        if text.startswith(prefix):
            text = replacement + text[len(prefix) :]
            break
    try:
        return os.path.normcase(os.path.realpath(text))
    except (OSError, ValueError):
        return None


def _root(getter: Any, what: str) -> str:
    """A normalised root, or a **refusal** — never a silent permit.

    An earlier drafting resolved the repository root inside the same ``try``
    that swallowed path errors and returned ``None``, and ``None`` meant
    "outside the repository, therefore permitted". A guard whose own failure
    mode is "permit everything" is not fail-closed.
    """
    try:
        return os.path.normcase(os.path.abspath(str(getter())))
    except Exception as exc:  # noqa: BLE001 - any failure here must fail closed
        raise IsolationError(
            f"{TOKEN}: the {what} could not be resolved ({exc}), so no path can be "
            "classified. Refusing rather than permitting."
        ) from exc


def _relative_parts(candidate: str, root: str) -> tuple[str, ...] | None:
    """The path's components relative to ``root``, or ``None`` if outside it."""
    if candidate == root:
        return ()
    prefixed = root if root.endswith(os.sep) else root + os.sep
    if not candidate.startswith(prefixed):
        return None
    return tuple(part for part in candidate[len(prefixed) :].split(os.sep) if part)


#: How far up a path the identity walk climbs before giving up.
_IDENTITY_WALK_LIMIT: Final[int] = 64


@functools.lru_cache(maxsize=8)
def _identity_map(repo_text: str, scratch_text: str) -> dict[tuple[int, int], str]:
    """``(st_dev, st_ino)`` of every protected root, by role.

    A filesystem identity is exact where a string is not: measured on this
    machine, ``…/data``, ``…\\FX-AI-~1\\data``, ``\\localhost\\C$\\…\\data`` and
    ``…/DATA`` all report the same ``st_dev``/``st_ino``. Cached on the two root
    strings, so a test that repoints the scratch root gets its own entry.
    """
    identities: dict[tuple[int, int], str] = {}
    repo = pathlib.Path(repo_text)
    candidates: list[tuple[str, pathlib.Path]] = [("scratch", pathlib.Path(scratch_text))]
    for name in _MARKET_DATA_DIRS:
        candidates.append(("market_data", repo / name))
    artifacts = repo / "artifacts"
    try:
        for entry in artifacts.iterdir():
            if entry.is_dir() and any(
                entry.name.startswith(prefix) for prefix in _MARKET_DATA_ARTIFACT_PREFIXES
            ):
                candidates.append(("market_data", entry))
    except OSError:
        pass
    candidates.append(("repo", repo))
    for role, path in candidates:
        try:
            stat = os.stat(path)
        except OSError:
            continue
        identities.setdefault((stat.st_dev, stat.st_ino), role)
    return identities


def _inside_protected(candidate: str, repo_text: str, scratch_text: str) -> str | None:
    """Which protected root really contains ``candidate``, by filesystem identity.

    The nearest protected ancestor wins, so the scratch root and the
    market-data trees are recognised before the repository that contains them.
    Only reached when the cheap string test has already said "outside the
    repository" — which is the case a second spelling of the same volume
    produces.
    """
    identities = _identity_map(repo_text, scratch_text)
    current = candidate
    for _ in range(_IDENTITY_WALK_LIMIT):
        try:
            stat = os.stat(current)
        except OSError:
            stat = None
        if stat is not None:
            role = identities.get((stat.st_dev, stat.st_ino))
            if role is not None:
                return role
        parent = os.path.dirname(current)
        if not parent or parent == current:
            return None
        current = parent
    return None  # pragma: no cover - 64 levels is not a real path


def _classify(candidate: str) -> tuple[str, tuple[str, ...]]:
    """One of ``outside`` / ``cache`` / ``scratch`` / ``market_data`` / ``repo``."""
    repo_text = _root(scratch.repo_root, "repository root")
    scratch_text = _root(scratch.scratch_root, "scratch root")
    parts = _relative_parts(candidate, repo_text)
    if parts is not None:
        if any(part in _WRITABLE_REPO_CACHES for part in parts):
            return "cache", parts
        if _relative_parts(candidate, scratch_text) is not None:
            return "scratch", parts
        if _is_market_data(parts):
            return "market_data", parts
        return "repo", parts
    role = _inside_protected(candidate, repo_text, scratch_text)
    return (role or "outside"), ()


def _is_market_data(parts: tuple[str, ...]) -> bool:
    if not parts:
        return False
    if parts[0] in _MARKET_DATA_DIRS:
        return True
    return (
        parts[0] == "artifacts"
        and len(parts) > 1
        and any(parts[1].startswith(prefix) for prefix in _MARKET_DATA_ARTIFACT_PREFIXES)
    )


def _is_write_mode(mode: object, flags: object = None) -> bool:
    """Whether an ``open`` event describes a write.

    For :func:`os.open` CPython passes ``mode=None`` and puts the real flags in
    the event's **third** argument. Reading only the mode meant every
    ``os.open`` — including ``Path.touch``, ``tempfile.mkstemp`` and an
    ``O_TRUNC`` on an append-only ledger — was classified as a read.
    """
    if isinstance(mode, str):
        return any(flag in mode for flag in ("w", "a", "x", "+"))
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC
    for value in (flags, mode):
        if isinstance(value, int) and not isinstance(value, bool):
            return bool(value & write_flags)
    # Neither a recognised mode nor recognised flags: fail closed.
    return True


def _is_append_only_mode(mode: object, flags: object = None) -> bool:
    if isinstance(mode, str):
        return "a" in mode and "w" not in mode and "+" not in mode
    for value in (flags, mode):
        if isinstance(value, int) and not isinstance(value, bool):
            return bool(value & os.O_APPEND) and not bool(value & os.O_TRUNC)
    return False


def assert_write_allowed(raw: object, *, what: str = "write to") -> None:
    """Refuse a mutating operation that lands in the repo outside the scratch root.

    An ``int`` is an already-open descriptor and is **permitted**: the ``open``
    that produced it was checked, and every other event in the hook already
    skips ints. An earlier drafting refused it, which broke far more than it
    guarded — CPython writes every ``.pyc`` through ``_io.FileIO(fd, "wb")``, so
    a Track A run died on its first uncached import, and ``containment.audit()``
    died with it. The suite never saw it because ``__pycache__`` was warm.
    """
    if isinstance(raw, int):
        return
    candidate = _normalise(raw)
    if candidate is None:
        raise IsolationError(
            f"{TOKEN}: a Track A run may not {what} a path it cannot classify ({raw!r}). "
            "An unclassifiable destination fails closed."
        )
    role, parts = _classify(candidate)
    if role in {"outside", "cache", "scratch"}:
        return
    where = "/".join(parts) if parts else candidate
    raise IsolationError(
        f"{TOKEN}: a Track A run may not {what} {where!r}. Every mutating operation goes "
        "beneath the Track A scratch root; the repository's source, docs, data, models and "
        "evidence trees are read-only to a research run."
    )


def _ledger_identities(scratch_text: str) -> dict[tuple[int, int], str]:
    """``(st_dev, st_ino)`` of every append-only ledger that exists."""
    identities: dict[tuple[int, int], str] = {}
    root = pathlib.Path(scratch_text)
    for name in scratch.APPEND_ONLY_FILENAMES:
        try:
            stat = os.stat(root / name)
        except OSError:
            continue
        identities[(stat.st_dev, stat.st_ino)] = name
    return identities


def _check_append_only(raw: object, mode: object, flags: object) -> None:
    """A `BINDING_GOVERNANCE_RECORD` may be appended to and never rewritten.

    Two tests, because either alone has been defeated. The first is **exact**:
    if the target already exists and its ``(st_dev, st_ino)`` is a ledger's,
    it is that ledger whatever the caller typed — an earlier drafting compared
    the raw basename case-sensitively, and six spellings truncated a real
    ledger to zero bytes (trailing dot, trailing space, ``::$DATA``, uppercase,
    mixed case, and ``os.open`` with ``O_TRUNC`` under any of them).

    The second catches a ledger that does not exist yet: the **normalised**
    basename, case-folded, with an NTFS stream suffix stripped. ``abspath``
    already removes the trailing dot and space that Windows ignores; the stream
    suffix it does not.
    """
    if isinstance(raw, int):
        return
    if not _is_write_mode(mode, flags) or _is_append_only_mode(mode, flags):
        return
    scratch_text = _root(scratch.scratch_root, "scratch root")

    try:
        stat = os.stat(os.fsdecode(raw))
    except (OSError, TypeError, ValueError):
        stat = None
    if stat is not None:
        name = _ledger_identities(scratch_text).get((stat.st_dev, stat.st_ino))
        if name is not None:
            raise IsolationError(
                f"{TOKEN}: {name!r} is an append-only governance record and may not be "
                "opened for truncation or overwrite. An append-only API binds only its "
                "own callers."
            )

    candidate = _normalise(raw)
    if candidate is None:
        return
    name = os.path.basename(candidate).split(":", 1)[0].casefold()
    if name not in {entry.casefold() for entry in scratch.APPEND_ONLY_FILENAMES}:
        return
    if _relative_parts(candidate, scratch_text) is not None:
        raise IsolationError(
            f"{TOKEN}: {name!r} is an append-only governance record and may not be opened "
            "for truncation or overwrite."
        )


def _check_open(args: tuple[Any, ...]) -> None:
    raw = args[0] if args else None
    if isinstance(raw, int):
        # An already-open descriptor. The open that produced it was checked, and
        # every other event in the hook skips ints too.
        return
    mode = args[1] if len(args) > 1 else None
    flags = args[2] if len(args) > 2 else None

    _check_append_only(raw, mode, flags)

    if _is_write_mode(mode, flags):
        assert_write_allowed(raw, what="open for writing")
        return

    if _read_window_depth():
        return
    candidate = _normalise(raw)
    if candidate is None:
        return  # a read of something unlocatable is not a market-data read
    role, parts = _classify(candidate)
    if role == "market_data":
        where = "/".join(parts) if parts else candidate
        raise IsolationError(
            f"{TOKEN}: a Track A run may not read {where!r} outside the gated read route. "
            "Market data is reached through "
            "scripts.m15_track_a.read_route.read_historical, which requires an explicit "
            "authorisation grant, an admissible span and a prior seen-data declaration."
        )


# ---------------------------------------------------------------------------
# The audit hook
# ---------------------------------------------------------------------------

#: True while the guards are armed.  An audit hook cannot be removed once added,
#: so ``uninstall_all`` disarms rather than detaches.
_armed: bool = False
_hook_installed: bool = False


@dataclass(frozen=True)
class _WindowOwner:
    """Who opened the read window, and how deep they are inside it."""

    thread_id: int
    task: int | None
    depth: int


#: The gated read window, pinned to the **thread and task that opened it**.
#:
#: Three draftings were needed. A module-level flag opened ``data/`` to every
#: other thread. A ``threading.local`` opened it to every other coroutine on the
#: same thread. A bare ``ContextVar`` looked right and is not: a ``Task`` copies
#: the current context at creation, so a task spawned *inside* the window
#: inherits it — measured, a sibling task's read reached the filesystem. So the
#: owner is recorded and compared, and an inherited copy fails the comparison.
_window: contextvars.ContextVar[_WindowOwner | None] = contextvars.ContextVar(
    "track_a_read_window", default=None
)


def _current_task_id() -> int | None:
    try:
        import asyncio

        task = asyncio.current_task()
    except (ImportError, RuntimeError):
        return None
    return None if task is None else id(task)


def _read_window_depth() -> int:
    owner = _window.get()
    if owner is None:
        return 0
    if owner.thread_id != threading.get_ident() or owner.task != _current_task_id():
        return 0  # an inherited copy, not the holder
    return owner.depth


def _audit_hook(event: str, args: tuple[Any, ...]) -> None:
    if not _armed:
        return
    try:
        if event in _EGRESS_EVENTS:
            if len(args) >= 2:
                _check_destination(args[1], how="reach")
        elif event in _RESOLUTION_EVENTS:
            if args and not _is_loopback(args[0]):
                raise IsolationError(
                    f"{TOKEN}: a Track A run may not resolve {args[0]!r}. A name lookup "
                    "reaches a resolver on the network before any connection is opened."
                )
        elif event in _SUBPROCESS_EVENTS:
            raise IsolationError(
                f"{TOKEN}: a Track A run may not launch a process ({event}). A subprocess "
                "escapes every in-process guard at once — network, database and write "
                "containment alike."
            )
        elif event == "sqlite3.connect":
            target = str(args[0]) if args else ""
            if target not in {":memory:", ""}:
                raise IsolationError(
                    f"{TOKEN}: a Track A run may not open the database {target!r}. §3.2 — "
                    "external DB access is off for R1."
                )
        elif event == "open":
            _check_open(args)
        elif event in _MUTATING_PATH_EVENTS:
            for index in range(min(_MUTATING_PATH_EVENTS[event], len(args))):
                if not isinstance(args[index], int):
                    assert_write_allowed(args[index], what=event.split(".")[-1])
    except IsolationError:
        raise
    except Exception as exc:  # noqa: BLE001 - an internal failure must fail closed
        # An earlier drafting let a non-IsolationError escape the hook and break
        # an unrelated operation with an unrelated traceback. Converting it here
        # keeps the failure closed *and* typed.
        raise IsolationError(
            f"{TOKEN}: the guard could not decide about {event!r} ({exc!r}), so it refused."
        ) from exc


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
    patched: list[tuple[Any, str, Any]] = field(default_factory=list)
    engine_targets: list[tuple[Any, str, Any]] = field(default_factory=list)
    database: bool = False


_state: _Installed | None = None


def _ensure_state() -> _Installed:
    """The single mutable record.

    A previous drafting let :func:`install_database_guard` create ``_state`` as a
    side effect while :func:`install_network_guard` early-returned on
    ``_state is not None``. Installing the database guard first therefore left
    the network completely open while ``is_installed()`` answered True. Each
    limb now carries its own flag and ``is_installed`` requires all three.
    """
    global _state
    if _state is None:
        _state = _Installed()
    return _state


def install_network_guard() -> None:
    """Refuse non-loopback TCP connects, UDP sends, name resolution and asyncio."""
    import asyncio.base_events

    state = _ensure_state()
    if state.network:
        return

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_sendto = socket.socket.sendto
    real_getaddrinfo = socket.getaddrinfo
    real_gethostbyname = socket.gethostbyname

    def guarded_connect(self: socket.socket, address: object) -> object:
        _check_destination(address, how="connect to")
        return real_connect(self, address)

    def guarded_connect_ex(self: socket.socket, address: object) -> object:
        _check_destination(address, how="connect to")
        return real_connect_ex(self, address)

    def guarded_sendto(self: socket.socket, data: object, *rest: object) -> object:
        if rest:
            _check_destination(rest[-1], how="send a datagram to")
        return real_sendto(self, data, *rest)

    def guarded_getaddrinfo(host: object, *rest: object, **kwargs: object) -> object:
        if not _is_loopback(host):
            raise IsolationError(f"{TOKEN}: a Track A run may not resolve {host!r}.")
        return real_getaddrinfo(host, *rest, **kwargs)

    def guarded_gethostbyname(host: object) -> object:
        if not _is_loopback(host):
            raise IsolationError(f"{TOKEN}: a Track A run may not resolve {host!r}.")
        return real_gethostbyname(host)

    async def refuse_create_connection(*_args: object, **_kwargs: object) -> object:
        raise IsolationError(
            f"{TOKEN}: a Track A run may not open an asyncio connection. R1 needs no "
            "network at all, and the Windows proactor reaches the stack below the "
            "socket methods."
        )

    # Each original is recorded **before** its assignment, so a failure part-way
    # through is still fully revertible. An earlier drafting reverted only
    # ``if state.network``, which a partial install never sets — leaving a stray
    # guarded function that a later re-install would record as "the original".
    for target, attribute, original, replacement in (
        (socket.socket, "connect", real_connect, guarded_connect),
        (socket.socket, "connect_ex", real_connect_ex, guarded_connect_ex),
        (socket.socket, "sendto", real_sendto, guarded_sendto),
        (socket, "getaddrinfo", real_getaddrinfo, guarded_getaddrinfo),
        (socket, "gethostbyname", real_gethostbyname, guarded_gethostbyname),
        (
            asyncio.base_events.BaseEventLoop,
            "create_connection",
            asyncio.base_events.BaseEventLoop.create_connection,
            refuse_create_connection,
        ),
    ):
        state.patched.append((target, attribute, original))
        setattr(target, attribute, replacement)

    state.network = True


def install_database_guard() -> None:
    """Refuse any SQLAlchemy engine that is not in-memory SQLite.

    Advisory only, and named as such: a module that did ``from sqlalchemy import
    create_engine`` at import time holds the original, and this repository's DB
    modules all do. SQLAlchemy is also lazy, so *building* an engine opens
    nothing and raises no audit event. The audit hook's ``socket.connect`` and
    ``sqlite3.connect`` limbs are what actually stop the connection such a
    caller would open.
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
    caller invokes.
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
    global _state, _armed
    _armed = False
    _window.set(None)
    state = _state
    _state = None
    if state is None:
        return
    for target, attribute, original in reversed(state.patched):
        setattr(target, attribute, original)
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
    """Open the market-data read window, **for this thread only**.

    Only :mod:`~scripts.m15_track_a.read_route` uses this, and only after every
    gate has passed. Outside it, a read of the market-data trees is refused by
    the audit hook wherever in the process it originates — which is what makes
    "exactly one read route" a property of the process rather than a property
    of one function that a caller may decline to call.

    Pinned to the thread **and the task** that opened it, and re-entrant.
    Three earlier draftings were wrong: a process-wide flag opened ``data/`` to
    every other thread; a ``threading.local`` opened it to every other coroutine
    on the same thread; and a bare ``ContextVar`` is *copied into* a child task,
    so a task spawned inside the window inherited it. Comparing the recorded
    owner is what makes an inherited copy inert.
    """

    _token: contextvars.Token[_WindowOwner | None]

    def __enter__(self) -> gated_read_window:
        if not _armed:
            raise IsolationError(
                f"{TOKEN}: the read window may not be opened while the guards are disarmed."
            )
        self._token = _window.set(
            _WindowOwner(
                thread_id=threading.get_ident(),
                task=_current_task_id(),
                depth=_read_window_depth() + 1,
            )
        )
        return self

    def __exit__(self, *_exc: object) -> None:
        _window.reset(self._token)


def is_read_window_open() -> bool:
    """Whether **this context** currently holds the gated read window."""
    return _read_window_depth() > 0


__all__ = [
    "FORBIDDEN_OPERATIONS",
    "TOKEN",
    "IsolationError",
    "assert_operation_allowed",
    "assert_write_allowed",
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
