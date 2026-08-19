"""The default test run touches nothing outside the repository.

These are the regression tests for the process-boundary incident recorded in
``docs/design/m15_targeted_fix_b1_b7_rf1_rf29_note.md`` §8, where a repo-wide
``pytest`` reached a live database because ``.env`` was auto-loaded at test
import and the only gate was ``skipif(not DATABASE_URL)``.

The invariant they pin is a single sentence:

    the presence of a resource is not authorization to use it

so every check below asks the same question in a different way — *does merely
having the thing switch anything on?*  The answer must always be no.
"""

from __future__ import annotations

import ast
import os
import re
import socket
import subprocess
import sys
from pathlib import Path

import pytest
import sqlalchemy

from tests import optin

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = REPO_ROOT / "tests"

_TEST_MODULES = sorted(TESTS_DIR.rglob("*.py"))


# ---------------------------------------------------------------------------
# 1. Opt-in semantics — a gate that only a deliberate act can open
# ---------------------------------------------------------------------------


class TestOptInSemantics:
    @pytest.mark.parametrize("value", ["1", " 1", "1 ", "  1  "])
    def test_exactly_one_grants(self, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
        monkeypatch.setenv(optin.DB_OPT_IN, value)
        assert optin.opt_in_granted(optin.DB_OPT_IN)

    @pytest.mark.parametrize(
        "value", ["", "0", "true", "True", "TRUE", "yes", "on", "2", "11", "1x", "no"]
    )
    def test_everything_else_fails_closed(
        self, monkeypatch: pytest.MonkeyPatch, value: str
    ) -> None:
        """A typo must leave the gate shut, never open it."""
        monkeypatch.setenv(optin.DB_OPT_IN, value)
        assert not optin.opt_in_granted(optin.DB_OPT_IN)

    def test_absent_variable_fails_closed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(optin.DB_OPT_IN, raising=False)
        assert not optin.opt_in_granted(optin.DB_OPT_IN)


class TestDatabaseDoubleGate:
    def test_database_url_alone_does_not_authorize(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """The incident in one assertion: a populated DATABASE_URL is not consent."""
        monkeypatch.delenv(optin.DB_OPT_IN, raising=False)
        monkeypatch.setenv(optin.DB_URL_VAR, "postgresql+psycopg://u:p@h:5432/d")
        assert optin.db_configured()
        assert not optin.db_tests_authorized()
        assert optin.DB_OPT_IN in (optin.db_skip_reason() or "")

    def test_opt_in_alone_does_not_authorize(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Opting in without configuration is skip-safe, never a guess."""
        monkeypatch.setenv(optin.DB_OPT_IN, "1")
        monkeypatch.delenv(optin.DB_URL_VAR, raising=False)
        assert not optin.db_tests_authorized()
        reason = optin.db_skip_reason() or ""
        assert optin.DB_URL_VAR in reason

    def test_both_gates_authorize(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(optin.DB_OPT_IN, "1")
        monkeypatch.setenv(optin.DB_URL_VAR, "postgresql+psycopg://u:p@h:5432/d")
        assert optin.db_tests_authorized()
        assert optin.db_skip_reason() is None

    def test_database_url_refuses_unauthorized_callers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(optin.DB_OPT_IN, raising=False)
        monkeypatch.setenv(optin.DB_URL_VAR, "postgresql+psycopg://u:p@h:5432/d")
        with pytest.raises(RuntimeError, match="not authorised"):
            optin.database_url()

    def test_database_url_error_does_not_leak_the_url(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        secret = "postgresql+psycopg://user:sup3rsecret@db.example:5432/prod"
        monkeypatch.delenv(optin.DB_OPT_IN, raising=False)
        monkeypatch.setenv(optin.DB_URL_VAR, secret)
        with pytest.raises(RuntimeError) as excinfo:
            optin.database_url()
        assert "sup3rsecret" not in str(excinfo.value)


class TestResearchDataGate:
    def test_present_file_is_not_authorization(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """A directory full of .jsonl files must not switch anything on."""
        fake_data = tmp_path / "data"
        fake_data.mkdir()
        for i in range(5):
            (fake_data / f"candles_PAIR{i:02d}_M1_730d_BA.jsonl").write_text("{}\n")
        monkeypatch.setattr(optin, "DATA_DIR", fake_data)
        monkeypatch.delenv(optin.RESEARCH_DATA_OPT_IN, raising=False)

        assert optin.research_path("candles_PAIR00_M1_730d_BA.jsonl") is None
        assert not optin.has_research_data("candles_PAIR00_M1_730d_BA.jsonl")

    def test_no_filesystem_probe_without_opt_in(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without the opt-in there is no discovery — not even an ``exists`` call."""
        monkeypatch.delenv(optin.RESEARCH_DATA_OPT_IN, raising=False)

        probed: list[str] = []

        class _Tattling(type(optin.DATA_DIR)):  # type: ignore[misc]
            def exists(self) -> bool:  # pragma: no cover - must never run
                probed.append(str(self))
                return True

        monkeypatch.setattr(optin, "DATA_DIR", _Tattling(optin.DATA_DIR))
        assert optin.research_path("anything.jsonl") is None
        assert probed == []

    def test_opt_in_plus_presence_authorizes(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        fake_data = tmp_path / "data"
        fake_data.mkdir()
        (fake_data / "present.jsonl").write_text("{}\n")
        monkeypatch.setattr(optin, "DATA_DIR", fake_data)
        monkeypatch.setenv(optin.RESEARCH_DATA_OPT_IN, "1")

        assert optin.has_research_data("present.jsonl")
        assert not optin.has_research_data("absent.jsonl")


# ---------------------------------------------------------------------------
# 2. .env is never auto-loaded
# ---------------------------------------------------------------------------


class TestDotenvIsNeutralised:
    def test_load_dotenv_is_disarmed_for_the_session(self) -> None:
        import dotenv
        import dotenv.main

        assert dotenv.load_dotenv.__name__ == "_refuse_load_dotenv"
        assert dotenv.main.load_dotenv.__name__ == "_refuse_load_dotenv"

    def test_a_real_env_file_is_not_read(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Synthetic .env, synthetic value — and it must not reach os.environ."""
        import dotenv

        env_file = tmp_path / ".env"
        env_file.write_text("SYNTHETIC_TEST_ONLY_VAR=placeholder-not-a-credential\n")
        monkeypatch.delenv("SYNTHETIC_TEST_ONLY_VAR", raising=False)

        assert dotenv.load_dotenv(env_file) is False
        assert "SYNTHETIC_TEST_ONLY_VAR" not in os.environ

    def test_importing_a_script_module_cannot_populate_the_environment(self) -> None:
        """The indirect route, pinned.

        ``tests/unit/test_f5_ingestion_provenance.py`` imports
        ``scripts.fetch_oanda_archive``, and that module calls ``load_dotenv``
        at import — without ``override=False``, so it would even overwrite
        values the caller set deliberately. A default ``pytest`` therefore read
        ``.env`` through a *unit* test, before any integration module was
        involved. The guard has to reach that binding too.
        """
        import importlib

        module = importlib.import_module("scripts.fetch_oanda_archive")

        # Non-vacuity: the module must still be one that calls load_dotenv at
        # import, otherwise this test would silently stop proving anything.
        source = (REPO_ROOT / "scripts" / "fetch_oanda_archive.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        module_level_calls = [
            call
            for node in tree.body
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            for call in ast.walk(node)
            if isinstance(call, ast.Call) and getattr(call.func, "id", None) == "load_dotenv"
        ]
        assert module_level_calls, (
            "scripts/fetch_oanda_archive.py no longer calls load_dotenv at import — "
            "this regression test has lost its subject and should be re-pointed"
        )

        assert module.load_dotenv.__name__ == "_refuse_load_dotenv", (
            "the module captured the real load_dotenv, so importing it read .env"
        )

    def test_no_test_module_loads_dotenv_at_import(self) -> None:
        """Import-time ``load_dotenv`` is the exact route the incident took."""
        offenders: list[str] = []
        for path in _TEST_MODULES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue  # bodies run at call time, not at import
                for call in ast.walk(node):
                    if not isinstance(call, ast.Call):
                        continue
                    func = call.func
                    name = (
                        func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
                    )
                    if name == "load_dotenv":
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{call.lineno}")
        assert offenders == [], f"module-level load_dotenv reintroduced: {offenders}"

    def test_no_test_module_reads_database_url_directly(self) -> None:
        """``DATABASE_URL`` is read in one place — the opt-in module."""
        allowed = {Path("tests/optin.py"), Path("tests/contract") / Path(__file__).name}
        offenders: list[str] = []
        for path in _TEST_MODULES:
            rel = path.relative_to(REPO_ROOT)
            if rel in allowed or rel.parent / rel.name in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            if 'environ.get("DATABASE_URL"' in text or "environ['DATABASE_URL'" in text:
                offenders.append(str(rel))
        assert offenders == [], (
            f"these modules resolve DATABASE_URL themselves instead of going "
            f"through tests.optin: {offenders}"
        )


# ---------------------------------------------------------------------------
# 3. Engine guard — no non-sqlite engine without authorization
# ---------------------------------------------------------------------------


class TestEngineGuard:
    def test_sqlite_is_always_allowed(self) -> None:
        engine = sqlalchemy.create_engine("sqlite:///:memory:")
        with engine.connect() as conn:
            assert conn.execute(sqlalchemy.text("SELECT 1")).scalar() == 1
        engine.dispose()

    def test_postgres_engine_refused_in_a_default_run(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(optin.DB_OPT_IN, raising=False)
        with pytest.raises(RuntimeError, match="may not build"):
            sqlalchemy.create_engine("postgresql+psycopg://u:p@example.invalid:5432/d")

    def test_refusal_does_not_echo_the_connection_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv(optin.DB_OPT_IN, raising=False)
        with pytest.raises(RuntimeError) as excinfo:
            sqlalchemy.create_engine("postgresql+psycopg://user:hunter2@host:5432/db")
        message = str(excinfo.value)
        assert "hunter2" not in message
        assert "host:5432" not in message

    def test_guard_is_installed_on_every_alias(self) -> None:
        import sqlalchemy.engine
        import sqlalchemy.engine.create

        assert sqlalchemy.create_engine.__name__ == "guarded_create_engine"
        assert sqlalchemy.engine.create_engine.__name__ == "guarded_create_engine"
        assert sqlalchemy.engine.create.create_engine.__name__ == "guarded_create_engine"


# ---------------------------------------------------------------------------
# 4. Socket guard — nothing leaves the loopback interface
# ---------------------------------------------------------------------------


class TestSocketGuard:
    def test_external_connection_refused(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(optin.EXTERNAL_OPT_IN, raising=False)
        monkeypatch.delenv(optin.DB_OPT_IN, raising=False)
        with socket.socket() as sock, pytest.raises(RuntimeError, match="network connection"):
            sock.connect(("example.invalid", 80))

    def test_connect_ex_is_guarded_too(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv(optin.EXTERNAL_OPT_IN, raising=False)
        monkeypatch.delenv(optin.DB_OPT_IN, raising=False)
        with socket.socket() as sock, pytest.raises(RuntimeError, match="network connection"):
            sock.connect_ex(("example.invalid", 80))

    def test_loopback_still_works(self) -> None:
        """Local fake servers (e.g. the SMTP dispatch test) must keep working."""
        with socket.socket() as server:
            server.bind(("127.0.0.1", 0))
            server.listen(1)
            port = server.getsockname()[1]
            with socket.socket() as client:
                client.settimeout(2)
                client.connect(("127.0.0.1", port))


# ---------------------------------------------------------------------------
# 5. Collection and import are side-effect free
# ---------------------------------------------------------------------------


class TestCollectionIsInert:
    def test_no_module_level_engine_construction(self) -> None:
        offenders: list[str] = []
        for path in _TEST_MODULES:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    continue  # bodies run at call time, not import time
                for call in ast.walk(node):
                    if not isinstance(call, ast.Call):
                        continue
                    func = call.func
                    name = (
                        func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
                    )
                    if name in {"create_engine", "connect"}:
                        offenders.append(f"{path.relative_to(REPO_ROOT)}:{call.lineno}")
        assert offenders == [], f"import-time database work: {offenders}"

    def test_collection_connects_to_nothing_even_when_fully_authorized(self) -> None:
        """Collect with an unreachable database *and* both gates open.

        If any module opened a connection while being imported, this bogus host
        would surface as a collection error. It must not.
        """
        env = dict(os.environ)
        env[optin.DB_OPT_IN] = "1"
        env[optin.DB_URL_VAR] = "postgresql+psycopg://u:p@169.254.0.1:1/none"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "--collect-only",
                "-q",
                "-p",
                "no:cacheprovider",
                "tests/integration",
                "tests/unit",
            ],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        assert result.returncode == 0, (
            "collection failed with a database configured — something connected "
            f"at import time:\n{result.stdout[-4000:]}"
        )
        collection_errors = [
            line for line in result.stdout.splitlines() if line.startswith("ERROR ")
        ]
        assert collection_errors == [], collection_errors


class _StubItem:
    """Minimal stand-in for a collected item, so the hook can be driven directly."""

    def __init__(self, marker: str | None) -> None:
        self.marker = marker
        self.added: list[pytest.Mark] = []

    def get_closest_marker(self, name: str) -> object | None:
        return object() if name == self.marker else None

    def add_marker(self, mark: object) -> None:
        self.added.append(mark)


def _load_root_conftest():
    """Import tests/conftest.py as a module so its hook can be called directly."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "_root_conftest_under_test", TESTS_DIR / "conftest.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# 6. The gates are actually wired to the tests that need them
# ---------------------------------------------------------------------------


class TestGatesAreApplied:
    def test_every_live_database_module_is_marked(self) -> None:
        """Any module resolving a live URL must carry the db mark."""
        unmarked: list[str] = []
        for path in _TEST_MODULES:
            if path.name == "optin.py":
                continue
            text = path.read_text(encoding="utf-8")
            if not re.search(r"(?<![\w.])database_url\(\)", text):
                continue
            if "pytest.mark.db" not in text:
                unmarked.append(str(path.relative_to(REPO_ROOT)))
        assert unmarked == [], f"live-database modules without @pytest.mark.db: {unmarked}"

    def test_collection_hook_skips_every_gated_marker(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The hook itself, exercised directly: no authorization, no execution."""
        conftest = _load_root_conftest()
        for var in optin.ALL_OPT_INS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.delenv(optin.DB_URL_VAR, raising=False)

        items = [_StubItem("db"), _StubItem("research_data"), _StubItem("external")]
        conftest.pytest_collection_modifyitems(config=None, items=items)

        for item in items:
            assert item.added, f"{item.marker} item was left runnable"
            assert item.added[0].name == "skip"

    def test_collection_hook_lets_authorized_items_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        conftest = _load_root_conftest()
        monkeypatch.setenv(optin.DB_OPT_IN, "1")
        monkeypatch.setenv(optin.DB_URL_VAR, "postgresql+psycopg://u:p@h:5432/d")

        item = _StubItem("db")
        conftest.pytest_collection_modifyitems(config=None, items=[item])
        assert item.added == []

    def test_unmarked_items_are_untouched(self, monkeypatch: pytest.MonkeyPatch) -> None:
        conftest = _load_root_conftest()
        for var in optin.ALL_OPT_INS:
            monkeypatch.delenv(var, raising=False)
        item = _StubItem(None)
        conftest.pytest_collection_modifyitems(config=None, items=[item])
        assert item.added == []

    def test_selecting_the_marker_still_does_not_run_it(self) -> None:
        """``-m db`` selects the database tests; none of them may execute.

        End-to-end through the real suite, in a subprocess, with a DATABASE_URL
        present and the opt-in absent — the exact shape of the incident.
        """
        env = dict(os.environ)
        env.pop(optin.DB_OPT_IN, None)
        env[optin.DB_URL_VAR] = "postgresql+psycopg://u:p@169.254.0.1:1/none"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "-m",
                "db",
                "tests/integration",
            ],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
        )
        summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
        assert " passed" not in summary, f"a database test executed unauthorised: {summary}"
        assert "skipped" in summary, f"expected skips, got: {summary}"
