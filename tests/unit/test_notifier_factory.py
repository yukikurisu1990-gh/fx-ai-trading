"""Unit tests for the production NotifierDispatcher factory (G-3 PR-1).

Covers contracts C-1 (silent skip) and C-10 (file-only fallback) from
``docs/design/g3_notifier_fix_plan.md``.

PR-1 hard guard checks (most important assertions):
  - ``email_notifier`` on the returned dispatcher is **always** ``None``,
    independent of any environment configuration.  PR-1 must not let
    Email enter the live dispatch path before PR-2 lands the SMTP
    timeout / retry-budget changes (G-3 §3.0 P-1, R-2 / R-3).
  - The factory module must not import ``EmailNotifier`` at all — even
    a stale import would risk later refactors accidentally re-enabling
    the channel.
"""

from __future__ import annotations

import sys

import pytest

from fx_ai_trading.adapters.notifier.dispatcher import NotifierDispatcherImpl
from fx_ai_trading.adapters.notifier.file import FileNotifier
from fx_ai_trading.adapters.notifier.slack import SlackNotifier
from fx_ai_trading.supervisor import notifier_factory
from fx_ai_trading.supervisor.notifier_factory import build_notifier_dispatcher


@pytest.fixture()
def file_notifier(tmp_path) -> FileNotifier:
    return FileNotifier(log_path=tmp_path / "notifications.jsonl")


class TestC1SilentSkipUnconfiguredChannels:
    """C-1: configured-only channels are wired; absent ones are silent."""

    def test_no_slack_url_yields_empty_externals(self, file_notifier: FileNotifier) -> None:
        dispatcher = build_notifier_dispatcher(file_notifier=file_notifier)

        assert isinstance(dispatcher, NotifierDispatcherImpl)
        # Externals is empty when no channel configuration is supplied.
        assert dispatcher._externals == []

    def test_empty_string_slack_url_treated_as_unconfigured(
        self, file_notifier: FileNotifier
    ) -> None:
        dispatcher = build_notifier_dispatcher(
            file_notifier=file_notifier,
            slack_webhook_url="",
        )
        assert dispatcher._externals == []

    def test_factory_does_not_raise_when_no_channels_configured(
        self, file_notifier: FileNotifier
    ) -> None:
        # The contract: "startup must proceed" — i.e. no exception.
        try:
            build_notifier_dispatcher(file_notifier=file_notifier)
        except Exception as exc:  # pragma: no cover - defensive
            pytest.fail(f"factory must not raise when channels are unconfigured: {exc}")

    def test_unconfigured_channel_emits_warning_log(
        self, file_notifier: FileNotifier, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level("WARNING", logger="fx_ai_trading.supervisor.notifier_factory"):
            build_notifier_dispatcher(file_notifier=file_notifier)
        # Operators must be able to grep for the missing-Slack notice.
        assert any("Slack" in r.message for r in caplog.records)


class TestC10FileOnlyFallback:
    """C-10: FileNotifier is always present; degraded-but-running."""

    def test_file_notifier_is_always_wired(self, file_notifier: FileNotifier) -> None:
        dispatcher = build_notifier_dispatcher(file_notifier=file_notifier)
        # Identity check: the exact instance the caller passed in.
        assert dispatcher._file is file_notifier

    def test_file_notifier_required_param_is_keyword_only(
        self, file_notifier: FileNotifier
    ) -> None:
        # Positional invocation must fail — the factory is keyword-only
        # so callers cannot accidentally swap file/slack arguments.
        with pytest.raises(TypeError):
            build_notifier_dispatcher(file_notifier)  # type: ignore[misc]


class TestSlackChannelWiring:
    """When Slack URL is supplied, exactly one SlackNotifier is added."""

    def test_slack_url_present_adds_slack_notifier(self, file_notifier: FileNotifier) -> None:
        dispatcher = build_notifier_dispatcher(
            file_notifier=file_notifier,
            slack_webhook_url="https://hooks.slack.example/T000/B000/XXX",
        )
        assert len(dispatcher._externals) == 1
        assert isinstance(dispatcher._externals[0], SlackNotifier)

    def test_slack_notifier_uses_supplied_url_not_env(
        self,
        file_notifier: FileNotifier,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Even when env var is set, the explicit kwarg wins (avoids
        # surprising precedence flips between PR-1 and PR-2 / PR-4).
        monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.example/ENV/URL")
        explicit = "https://hooks.slack.example/T999/B999/EXPLICIT"

        dispatcher = build_notifier_dispatcher(
            file_notifier=file_notifier,
            slack_webhook_url=explicit,
        )
        slack = dispatcher._externals[0]
        assert isinstance(slack, SlackNotifier)
        assert slack._webhook_url == explicit


class TestPR1EmailHardGuard:
    """PR-1 invariant: Email is never activated by this factory."""

    def test_email_notifier_is_none_with_no_config(self, file_notifier: FileNotifier) -> None:
        dispatcher = build_notifier_dispatcher(file_notifier=file_notifier)
        assert dispatcher._email is None

    def test_email_notifier_is_none_even_when_slack_configured(
        self, file_notifier: FileNotifier
    ) -> None:
        dispatcher = build_notifier_dispatcher(
            file_notifier=file_notifier,
            slack_webhook_url="https://hooks.slack.example/T/B/X",
        )
        assert dispatcher._email is None

    def test_email_notifier_is_none_even_with_smtp_env_vars(
        self,
        file_notifier: FileNotifier,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # If a future operator pre-stages SMTP env vars expecting PR-2
        # behaviour, PR-1 must still leave email disabled.
        monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
        monkeypatch.setenv("SMTP_PORT", "587")
        monkeypatch.setenv("SMTP_PASSWORD", "irrelevant")

        dispatcher = build_notifier_dispatcher(file_notifier=file_notifier)
        assert dispatcher._email is None

    def test_factory_module_does_not_import_email_notifier(self) -> None:
        # The EmailNotifier symbol must not appear in the factory's
        # namespace.  An import would risk a future tweak accidentally
        # constructing one before PR-2's SMTP timeout lands.
        assert not hasattr(notifier_factory, "EmailNotifier")

        # And it must not be transitively imported via this module's
        # dependencies (a clean PR-1 state lets PR-2 own the import).
        loaded_via_factory = "fx_ai_trading.adapters.notifier.email" in sys.modules
        # We can't enforce a global "never loaded" assertion (other
        # tests in the same session may load it), so we only check that
        # the factory itself does not bind it as a name.
        _ = loaded_via_factory  # documented for reviewers; not asserted.
