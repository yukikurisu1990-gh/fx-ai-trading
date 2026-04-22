"""Integration test for ``python -m fx_ai_trading.supervisor`` (G-3 PR-1).

Closes audit finding R-1: before this PR the spawn target invoked by
``ProcessManager.start()`` had no ``__main__`` module and the subprocess
would die with ``ModuleNotFoundError`` — leaving production with no
working Supervisor and ``safe_stop`` step 3 wired only to ``FileNotifier``.

This test verifies the file-only safe path:
  - The module can be imported and run as a subprocess.
  - It exits 0 without DB / broker / SMTP / Slack configuration.
  - The dispatcher built by ``_build_supervisor_context`` matches the
    PR-1 hard guard: file-only externals + ``email_notifier=None``.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from fx_ai_trading.adapters.notifier.dispatcher import NotifierDispatcherImpl
from fx_ai_trading.adapters.notifier.file import FileNotifier
from fx_ai_trading.adapters.notifier.slack import SlackNotifier
from fx_ai_trading.supervisor.__main__ import _build_supervisor_context

_REPO_ROOT = Path(__file__).resolve().parents[2]


class TestBuildSupervisorContext:
    """In-process checks of the wiring assembled by ``_build_supervisor_context``."""

    def test_dispatcher_is_file_only_when_no_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.chdir(tmp_path)

        _, ctx = _build_supervisor_context()
        dispatcher = ctx.notifier
        assert isinstance(dispatcher, NotifierDispatcherImpl)
        assert isinstance(dispatcher._file, FileNotifier)
        assert dispatcher._externals == []
        # PR-1 hard guard: Email never enabled.
        assert dispatcher._email is None

    def test_dispatcher_includes_slack_when_env_set(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.example/T/B/X")
        monkeypatch.chdir(tmp_path)

        _, ctx = _build_supervisor_context()
        dispatcher = ctx.notifier
        assert isinstance(dispatcher, NotifierDispatcherImpl)
        assert len(dispatcher._externals) == 1
        assert isinstance(dispatcher._externals[0], SlackNotifier)
        # PR-1 hard guard: Email remains None even with Slack wired.
        assert dispatcher._email is None

    def test_logs_dir_is_created(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.chdir(tmp_path)

        _build_supervisor_context()
        assert (tmp_path / "logs").is_dir()

    def test_startup_context_uses_default_journal_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.chdir(tmp_path)

        _, ctx = _build_supervisor_context()
        # The journal should write to logs/safe_stop.jsonl under cwd.
        ctx.journal.append({"event_code": "smoke_test"})
        assert (tmp_path / "logs" / "safe_stop.jsonl").exists()


class TestPr4ProbeEnvWiring:
    """G-3 PR-4 (memo §3.4): SMTP_HOST / SMTP_PORT / SLACK_WEBHOOK_URL must
    flow into ``StartupContext`` as probe-only fields.

    Hard guards re-asserted here:
      - Email is NEVER activated by the env-var path (``dispatcher._email``
        stays ``None`` no matter what SMTP_HOST/PORT contain).
      - A non-numeric ``SMTP_PORT`` is treated as "no SMTP probe" rather
        than crashing startup.
    """

    def _clean_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for name in ("SLACK_WEBHOOK_URL", "SMTP_HOST", "SMTP_PORT"):
            monkeypatch.delenv(name, raising=False)

    def test_probe_fields_default_to_none_when_no_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._clean_env(monkeypatch)
        monkeypatch.chdir(tmp_path)

        _, ctx = _build_supervisor_context()
        assert ctx.slack_webhook_url is None
        assert ctx.smtp_host is None
        assert ctx.smtp_port is None

    def test_smtp_env_vars_propagate_to_startup_context(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._clean_env(monkeypatch)
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.chdir(tmp_path)

        _, ctx = _build_supervisor_context()
        assert ctx.smtp_host == "smtp.example.com"
        assert ctx.smtp_port == 587
        # Email channel must remain disabled — probes are connectivity only.
        assert ctx.notifier._email is None

    def test_slack_webhook_env_propagates_to_startup_context(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._clean_env(monkeypatch)
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.example/T/B/X")
        monkeypatch.chdir(tmp_path)

        _, ctx = _build_supervisor_context()
        assert ctx.slack_webhook_url == "https://hooks.slack.example/T/B/X"

    def test_non_numeric_smtp_port_disables_probe_without_crashing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._clean_env(monkeypatch)
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_PORT", "not-a-port")
        monkeypatch.chdir(tmp_path)

        # Must not raise; the bad port is normalised to None.
        _, ctx = _build_supervisor_context()
        assert ctx.smtp_port is None

    def test_blank_smtp_host_normalised_to_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self._clean_env(monkeypatch)
        monkeypatch.setenv("SMTP_HOST", "   ")
        monkeypatch.chdir(tmp_path)

        _, ctx = _build_supervisor_context()
        assert ctx.smtp_host is None


class TestModuleSubprocessSmoke:
    """End-to-end: ``python -m fx_ai_trading.supervisor`` exits 0 file-only."""

    def test_module_runs_to_completion(self, tmp_path: Path) -> None:
        env = dict(os.environ)
        env.pop("SLACK_WEBHOOK_URL", None)
        # Steer the subprocess into a clean tmp_path so its log files
        # land outside the repo working tree.
        env["PYTHONPATH"] = str(_REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")

        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "fx_ai_trading.supervisor"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0, (
            f"supervisor entry point exited {result.returncode}\n"
            f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        )
        # Confirm the file-only fallback notice landed in stderr (logging default).
        combined = result.stdout + result.stderr
        assert "Supervisor entry point" in combined
        assert "startup complete" in combined.lower()
