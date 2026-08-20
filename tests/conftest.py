"""Session-wide guards for the test suite.

Two independent guarantees live here.

**P1-A** (audit memo docs/design/project_wide_logic_audit_fable5_findings.md,
finding F-9): stage-eval smoke tests used to regenerate tracked evidence
files under artifacts/ in place. Test output is now redirected to
tmp_path, and the autouse session fixture below is the regression backstop:
it hashes the protected tracked evidence files at session start and
fails the session at teardown if any test modified them.

**Test-safety** (process-boundary incident,
docs/design/m15_targeted_fix_b1_b7_rf1_rf29_note.md §8): a repository-wide
``pytest`` once reached a live database, because ``.env`` was auto-loaded at
test-module import and the only gate was ``skipif(not DATABASE_URL)``. Having
the resource silently authorised using it. The guards installed at the bottom
of this module remove that class of accident outright: the principle is

    the presence of a resource is not authorization to use it

and the opt-in vocabulary is defined once in :mod:`tests.optin`.

The guards are installed at *conftest import time* — before pytest imports any
test module — so an ``import``-time side effect in a test module, or in
production code that a test module pulls in, is caught too.
"""

from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import socket
import sys
from pathlib import Path

import pytest

from tests import optin

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Tracked evidence files that test runs must never modify (audit F-9 set
# plus the two additional at-risk writers found during P1-A).
PROTECTED_TRACKED_ARTIFACTS: tuple[str, ...] = (
    "artifacts/stage24_0b/eval_report.md",
    "artifacts/stage24_0c/eval_report.md",
    "artifacts/stage24_0d/eval_report.md",
    "artifacts/stage25_0a/dataset_summary.md",
    "artifacts/stage25_0a/causality_audit.md",
    "artifacts/stage25_0b/eval_report.md",
    "artifacts/stage25_0c/eval_report.md",
    "artifacts/stage25_0d/eval_report.md",
)


def _digest(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def protect_tracked_artifacts():
    """Fail the session if any test modifies protected tracked evidence."""
    before = {rel: _digest(_REPO_ROOT / rel) for rel in PROTECTED_TRACKED_ARTIFACTS}
    yield
    dirtied = [
        rel for rel in PROTECTED_TRACKED_ARTIFACTS if _digest(_REPO_ROOT / rel) != before[rel]
    ]
    if dirtied:
        raise AssertionError(
            "P1-A violation: test run modified tracked evidence artifacts: "
            f"{dirtied}. Stage-eval tests must write to tmp_path via --out-dir "
            "(see docs/design/project_wide_logic_audit_fable5_findings.md F-9). "
            "Restore the files with `git restore -- <paths>` and fix the "
            "offending test."
        )


# ---------------------------------------------------------------------------
# What counts as consent
# ---------------------------------------------------------------------------
# Read once, here, at conftest import. The guards below use this snapshot
# rather than consulting ``os.environ`` when they fire, because a live lookup
# would let any test disarm a guard for the duration of a ``monkeypatch.setenv``
# — and this repository's own contract tests set those variables while checking
# the opt-in vocabulary. Consent is what the caller supplied when the session
# started, not what a fixture put in the environment a moment ago.

_DB_AUTHORIZED = optin.db_tests_authorized()
_NETWORK_AUTHORIZED = optin.external_tests_authorized() or _DB_AUTHORIZED


# ---------------------------------------------------------------------------
# Guard 1 — .env is never auto-loaded during a test session
# ---------------------------------------------------------------------------
# The incident route was: a module called ``load_dotenv`` at import, which
# populated ``DATABASE_URL`` from the developer's own ``.env`` even though the
# shell was clean. Ten integration modules did it directly, and
# ``tests/unit/test_f5_ingestion_provenance.py`` did it *indirectly* by importing
# ``scripts.fetch_oanda_archive``, whose module body loads ``.env`` — so even a
# plain unit-test run read it. A caller who wants database tests exports the
# variable deliberately.


def _refuse_load_dotenv(*_args: object, **_kwargs: object) -> bool:
    """Stand-in for ``dotenv.load_dotenv`` — reads nothing, changes nothing."""
    return False


def _disable_dotenv_autoload() -> None:
    import dotenv
    import dotenv.main

    # Library-level backstop first: python-dotenv checks this inside
    # ``load_dotenv`` itself, so it also covers a binding some module captured
    # before this conftest was imported, and it is inherited by subprocesses.
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"

    # Then the bindings, so the refusal is explicit rather than a silent no-op.
    # Both names: modules import either ``dotenv.load_dotenv`` or the
    # definition in ``dotenv.main``.
    dotenv.load_dotenv = _refuse_load_dotenv
    dotenv.main.load_dotenv = _refuse_load_dotenv


# ---------------------------------------------------------------------------
# Guard 2 — no engine may point at anything but sqlite without authorization
# ---------------------------------------------------------------------------
# Every ``create_engine`` call in the suite is ``sqlite:///:memory:`` except the
# database-integration modules, so this gate is exact rather than approximate.

_SAFE_ENGINE_SCHEMES = ("sqlite",)


_SCHEME_SHAPE = re.compile(r"[a-z0-9_.]+")


def _engine_scheme(url: object) -> str:
    """Dialect name only — never the rest of the URL, which carries the password.

    ``str.split("://")`` returns the *whole* string when the separator is
    absent, so a malformed ``DATABASE_URL`` would otherwise be echoed verbatim
    into the refusal message. SQLAlchemy redacts that case; so does this.
    """
    text = str(url)
    if "://" not in text:
        return "<unparsable>"
    scheme = text.split("://", 1)[0].split("+", 1)[0].lower()
    return scheme if _SCHEME_SHAPE.fullmatch(scheme) else "<unparsable>"


def _install_engine_guard() -> None:
    import sqlalchemy
    import sqlalchemy.engine
    import sqlalchemy.engine.create

    real_create_engine = sqlalchemy.create_engine

    def guarded_create_engine(url: object, *args: object, **kwargs: object) -> object:
        scheme = _engine_scheme(url)
        if scheme not in _SAFE_ENGINE_SCHEMES and not _DB_AUTHORIZED:
            raise RuntimeError(
                f"a default test run may not build a {scheme!r} engine. "
                f"{optin.db_skip_reason()}. Mark the test with @pytest.mark.db and "
                f"decorate it with tests.optin.requires_db."
            )
        return real_create_engine(url, *args, **kwargs)

    sqlalchemy.create_engine = guarded_create_engine
    sqlalchemy.engine.create_engine = guarded_create_engine
    sqlalchemy.engine.create.create_engine = guarded_create_engine


# ---------------------------------------------------------------------------
# Guard 3 — no connection off the loopback interface without authorization
# ---------------------------------------------------------------------------

_LOOPBACK_NAMES = frozenset({"", "localhost", "localhost.localdomain"})


def _is_loopback(host_value: object) -> bool:
    """Whole loopback range, not four spellings of it.

    ``127.0.0.2`` and ``0:0:0:0:0:0:0:1`` are loopback too, CPython accepts a
    ``bytes`` host, and a name comparison has to be case-insensitive. Anything
    unrecognised is treated as remote — the failure direction is closed.
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


def _check_destination(address: object) -> None:
    if not isinstance(address, tuple) or not address:
        return  # AF_UNIX and friends never leave the machine
    host = address[0]
    if _is_loopback(host) or _NETWORK_AUTHORIZED:
        return
    raise RuntimeError(
        f"a default test run may not open a network connection to {host!r}. "
        f"{optin.external_skip_reason()}."
    )


def _install_socket_guard() -> None:
    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def guarded_connect(self: socket.socket, address: object) -> object:
        _check_destination(address)
        return real_connect(self, address)

    def guarded_connect_ex(self: socket.socket, address: object) -> object:
        _check_destination(address)
        return real_connect_ex(self, address)

    socket.socket.connect = guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = guarded_connect_ex  # type: ignore[method-assign]


# ---------------------------------------------------------------------------
# Guard 4 — the repository's own .env may not be opened, by any route
# ---------------------------------------------------------------------------
# Guards 1-3 all patch a named function, so they only see the routes they know
# about. This one does not care how the file is reached: an audit hook sits
# under every ``open``, including ``Path.read_text``, ``io.open`` and the C
# implementations, and an audit hook cannot be removed once installed.
#
# It found a real case that guard 1 could never have seen:
# ``bootstrap_view.render()`` without ``env_path`` falls back to the repository
# root and calls ``path.read_text()`` — a plain read, no dotenv involved.

_REPO_ENV_FILE = str(_REPO_ROOT / ".env").lower()


def _refuse_repo_dotenv_open(event: str, args: tuple) -> None:
    if event != "open":
        return
    target = args[0]
    if isinstance(target, int) or not isinstance(target, (str, bytes, os.PathLike)):
        return  # a file descriptor, not a path
    # Cheap first: almost nothing a test opens ends in ".env".
    text = target if isinstance(target, str) else os.fsdecode(target)
    if not text.endswith(".env"):
        return
    if os.path.abspath(text).lower() == _REPO_ENV_FILE:
        raise RuntimeError(
            "a test tried to open the repository's .env. Tests never read it — "
            "pass an explicit path (a file under tmp_path) instead, and let the "
            "caller supply real configuration through the environment."
        )


def _install_dotenv_read_guard() -> None:
    sys.addaudithook(_refuse_repo_dotenv_open)


_disable_dotenv_autoload()
_install_engine_guard()
_install_socket_guard()
_install_dotenv_read_guard()


# ---------------------------------------------------------------------------
# Collection gate — marked tests skip unless authorised
# ---------------------------------------------------------------------------
# This runs after collection, so it cannot be sidestepped by ``-m``, ``-k``,
# or by naming a test file directly on the command line.

_GATED_MARKERS: tuple[str, ...] = ("db", "research_data", "external")


def _authorization_for(marker: str) -> tuple[bool, str]:
    if marker == "db":
        return optin.db_tests_authorized(), optin.db_skip_reason() or ""
    if marker == "research_data":
        return optin.research_data_authorized(), optin.research_skip_reason()
    return optin.external_tests_authorized(), optin.external_skip_reason()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    decisions = {name: _authorization_for(name) for name in _GATED_MARKERS}
    for item in items:
        for marker in _GATED_MARKERS:
            if item.get_closest_marker(marker) is None:
                continue
            authorized, reason = decisions[marker]
            if not authorized:
                item.add_marker(pytest.mark.skip(reason=reason))


def pytest_report_header(config: pytest.Config) -> list[str]:
    """Make the authorisation state visible instead of silently implied."""
    granted = [name for name in optin.ALL_OPT_INS if optin.opt_in_granted(name)]
    lines = [
        "test-safety: .env auto-load disabled; "
        f"opt-ins granted: {', '.join(granted) if granted else 'none'}"
    ]
    if optin.opt_in_granted(optin.DB_OPT_IN) and not optin.db_configured():
        lines.append(
            f"test-safety: WARNING {optin.DB_OPT_IN}=1 but {optin.DB_URL_VAR} is unset "
            "— database tests will skip, not run"
        )
    return lines
