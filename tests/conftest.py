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
import socket
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
# Guard 1 — .env is never auto-loaded during a test session
# ---------------------------------------------------------------------------
# The incident route was: a test module (or ``fx_ai_trading.config``, imported
# transitively) called ``load_dotenv`` at import, which populated
# ``DATABASE_URL`` from the developer's own ``.env`` even though the shell was
# clean. A caller who wants database tests exports the variable deliberately.

_REAL_LOAD_DOTENV = None


def _refuse_load_dotenv(*_args: object, **_kwargs: object) -> bool:
    """Stand-in for ``dotenv.load_dotenv`` — reads nothing, changes nothing."""
    return False


def _disable_dotenv_autoload() -> None:
    global _REAL_LOAD_DOTENV
    import dotenv
    import dotenv.main

    _REAL_LOAD_DOTENV = dotenv.load_dotenv
    # Both names: modules import either ``dotenv.load_dotenv`` or the
    # definition in ``dotenv.main``.
    dotenv.load_dotenv = _refuse_load_dotenv
    dotenv.main.load_dotenv = _refuse_load_dotenv


@pytest.fixture
def real_load_dotenv():
    """Hand back the genuine ``load_dotenv`` to a test that needs to exercise it.

    Deliberately explicit: a test asking for this fixture is stating that it
    means to load a file it created itself, not the repository's ``.env``.
    """
    assert _REAL_LOAD_DOTENV is not None
    return _REAL_LOAD_DOTENV


# ---------------------------------------------------------------------------
# Guard 2 — no engine may point at anything but sqlite without authorization
# ---------------------------------------------------------------------------
# Every ``create_engine`` call in the suite is ``sqlite:///:memory:`` except the
# database-integration modules, so this gate is exact rather than approximate.

_SAFE_ENGINE_SCHEMES = ("sqlite",)


def _engine_scheme(url: object) -> str:
    """Dialect name only — never the rest of the URL, which carries the password."""
    text = str(url)
    return text.split("://", 1)[0].split("+", 1)[0].lower()


def _install_engine_guard() -> None:
    import sqlalchemy
    import sqlalchemy.engine
    import sqlalchemy.engine.create

    real_create_engine = sqlalchemy.create_engine

    def guarded_create_engine(url: object, *args: object, **kwargs: object) -> object:
        scheme = _engine_scheme(url)
        if scheme not in _SAFE_ENGINE_SCHEMES and not optin.db_tests_authorized():
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

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", ""})


def _network_authorized() -> bool:
    # A database opt-in authorises reaching that database's host; the external
    # opt-in authorises brokers, object storage and everything else.
    return optin.external_tests_authorized() or optin.db_tests_authorized()


def _check_destination(address: object) -> None:
    if not isinstance(address, tuple) or not address:
        return  # AF_UNIX and friends never leave the machine
    host = str(address[0])
    if host in _LOOPBACK_HOSTS or _network_authorized():
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


_disable_dotenv_autoload()
_install_engine_guard()
_install_socket_guard()


# ---------------------------------------------------------------------------
# Collection gate — marked tests skip unless authorised
# ---------------------------------------------------------------------------
# This runs after collection, so it cannot be sidestepped by ``-m``, ``-k``,
# or by naming a test file directly on the command line.

_GATED_MARKERS: tuple[tuple[str, str], ...] = (
    ("db", "database"),
    ("research_data", "local research data"),
    ("external", "external systems"),
)


def _authorization_for(marker: str) -> tuple[bool, str]:
    if marker == "db":
        return optin.db_tests_authorized(), optin.db_skip_reason() or ""
    if marker == "research_data":
        return optin.research_data_authorized(), optin.research_skip_reason()
    return optin.external_tests_authorized(), optin.external_skip_reason()


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    decisions = {name: _authorization_for(name) for name, _ in _GATED_MARKERS}
    for item in items:
        for marker, _label in _GATED_MARKERS:
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
