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
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from fx_ai_trading.adapters.notifier.dispatcher import NotifierDispatcherImpl
from fx_ai_trading.adapters.notifier.file import FileNotifier
from fx_ai_trading.adapters.notifier.slack import SlackNotifier
from fx_ai_trading.supervisor.__main__ import (
    _build_supervisor_context,
    _install_signal_driven_safe_stop,
    main,
)

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
    """End-to-end: ``python -m fx_ai_trading.supervisor`` blocks on signal then exits 0.

    Skipped on Windows because ``CTRL_BREAK_EVENT`` delivery requires the
    target subprocess to share a console with the sender; pytest under
    common Windows runners (git-bash, MSYS, headless CI shells) often has
    no console attached and the event is silently dropped.  That delivery
    contract is an OS guarantee, not something this codebase implements.
    Windows coverage of the catchable-stop wiring lives in:
      - ``TestSignalDrivenSafeStop.test_install_registers_sigbreak_on_windows``
        (handler is wired to SIGBREAK on Windows), and
      - ``test_ctl_start_stop.TestProcessManagerCrossPlatformBranching``
        (start uses CREATE_NEW_PROCESS_GROUP, stop sends CTRL_BREAK_EVENT).
    """

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="CTRL_BREAK_EVENT needs a shared console; covered by mock+in-process tests",
    )
    def test_module_blocks_then_exits_clean_on_sigterm(self, tmp_path: Path) -> None:
        env = dict(os.environ)
        env.pop("SLACK_WEBHOOK_URL", None)
        env["PYTHONPATH"] = str(_REPO_ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")

        proc = subprocess.Popen(  # noqa: S603
            [sys.executable, "-m", "fx_ai_trading.supervisor"],
            cwd=tmp_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # Wait for startup + signal-handler install to land before signaling.
        # 5s is generous: file-only startup is sub-second on the CI runners.
        time.sleep(5)
        proc.send_signal(signal.SIGTERM)
        try:
            stdout, stderr = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            pytest.fail(
                f"supervisor did not exit within 15s after SIGTERM\n"
                f"--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
            )

        assert proc.returncode == 0, (
            f"supervisor entry point exited {proc.returncode}\n"
            f"--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}"
        )
        combined = stdout + stderr
        assert "Supervisor entry point" in combined
        assert "startup complete" in combined.lower()
        assert "awaiting stop signal" in combined.lower()
        assert "signal received" in combined.lower()
        assert "safe_stop complete" in combined.lower()


class TestSignalDrivenSafeStop:
    """In-process tests for the signal → safe_stop wiring added in PR-A.

    These run without spawning a subprocess so the same coverage applies
    on Windows (where SIGTERM-via-TerminateProcess is uncatchable).  The
    handler is invoked directly to avoid relying on signal delivery.
    """

    def test_install_returns_event_and_received_list(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.chdir(tmp_path)
        supervisor, ctx = _build_supervisor_context()
        log = __import__("logging").getLogger("test")

        # signal.signal can only run on the main thread.  Save and
        # restore prior handlers so sibling tests are unaffected.
        prior_term = signal.getsignal(signal.SIGTERM)
        prior_int = signal.getsignal(signal.SIGINT)
        try:
            stop_event, received = _install_signal_driven_safe_stop(supervisor, ctx, log)
            assert isinstance(stop_event, threading.Event)
            assert received == []
            assert not stop_event.is_set()
        finally:
            signal.signal(signal.SIGTERM, prior_term)
            signal.signal(signal.SIGINT, prior_int)

    def test_install_registers_sigbreak_on_windows(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PR-B: on Windows the same handler must also be wired to SIGBREAK.

        ``ProcessManager.stop()`` delivers ``CTRL_BREAK_EVENT`` on Windows,
        which Python translates to ``SIGBREAK`` in the child.  Without this
        registration the catchable-stop path lands on the default handler
        and the supervisor exits without firing safe_stop.
        """
        if sys.platform != "win32":
            pytest.skip("SIGBREAK is Windows-only")

        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.chdir(tmp_path)
        supervisor, ctx = _build_supervisor_context()
        log = __import__("logging").getLogger("test")

        sigbreak = signal.SIGBREAK  # type: ignore[attr-defined]
        prior_term = signal.getsignal(signal.SIGTERM)
        prior_int = signal.getsignal(signal.SIGINT)
        prior_break = signal.getsignal(sigbreak)
        try:
            stop_event, received = _install_signal_driven_safe_stop(supervisor, ctx, log)
            handler = signal.getsignal(sigbreak)
            # Default handlers are SIG_DFL/SIG_IGN sentinels — our handler
            # is a callable installed by _install_signal_driven_safe_stop.
            assert callable(handler)
            handler(sigbreak, None)
            assert stop_event.is_set()
            assert received == [sigbreak]
        finally:
            signal.signal(signal.SIGTERM, prior_term)
            signal.signal(signal.SIGINT, prior_int)
            signal.signal(sigbreak, prior_break)

    def test_handler_sets_event_and_records_signum(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invoke the registered SIGTERM handler directly to verify wiring.

        Skips signal delivery (which is fiddly cross-platform) and just
        confirms the handler installed by ``_install_signal_driven_safe_stop``
        sets the event and appends the signum.
        """
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.chdir(tmp_path)
        supervisor, ctx = _build_supervisor_context()
        log = __import__("logging").getLogger("test")

        prior_term = signal.getsignal(signal.SIGTERM)
        prior_int = signal.getsignal(signal.SIGINT)
        try:
            stop_event, received = _install_signal_driven_safe_stop(supervisor, ctx, log)
            handler = signal.getsignal(signal.SIGTERM)
            # Invoke the handler as the runtime would (signum, frame).
            handler(signal.SIGTERM, None)
            assert stop_event.is_set()
            assert received == [signal.SIGTERM]
        finally:
            signal.signal(signal.SIGTERM, prior_term)
            signal.signal(signal.SIGINT, prior_int)

    def test_main_blocks_then_fires_safe_stop_on_signal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Run main() in a worker thread, set the stop event from outside, assert exit 0.

        We patch ``_install_signal_driven_safe_stop`` so the test can
        flip the stop event without actually delivering a signal —
        signals can only be raised on the main thread, but pytest IS
        the main thread.
        """
        monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
        monkeypatch.chdir(tmp_path)

        externally_visible_event = threading.Event()
        spy_received: list[int] = []

        def _fake_install(supervisor, ctx, log):  # type: ignore[no-untyped-def]
            return externally_visible_event, spy_received

        trigger_calls: list[dict] = []

        # Capture the real Supervisor.trigger_safe_stop so we can verify
        # main() invoked it with the right reason without firing the
        # full SafeStopHandler 4-step sequence (which would write real
        # files / require a journal etc.).
        from fx_ai_trading.supervisor.supervisor import Supervisor

        def _spy_trigger(self, reason, occurred_at, payload=None, context=None):  # type: ignore[no-untyped-def]
            trigger_calls.append({"reason": reason, "occurred_at": occurred_at})

        with (
            patch(
                "fx_ai_trading.supervisor.__main__._install_signal_driven_safe_stop",
                _fake_install,
            ),
            patch.object(Supervisor, "trigger_safe_stop", _spy_trigger),
        ):
            rc_holder: list[int] = []

            def _run():
                rc_holder.append(main())

            t = threading.Thread(target=_run, daemon=True)
            t.start()
            # Wait briefly for startup to land and main() to enter wait().
            time.sleep(2)
            externally_visible_event.set()
            t.join(timeout=10)
            assert not t.is_alive(), "main() did not return after stop_event was set"

        assert rc_holder == [0]
        assert len(trigger_calls) == 1
        assert trigger_calls[0]["reason"] == "signal_received"
