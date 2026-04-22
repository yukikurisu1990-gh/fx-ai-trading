"""NotifierDispatcher factory — production wiring (G-3 PR-1).

Builds a ``NotifierDispatcherImpl`` for the Supervisor process so that
``safe_stop`` events have a real fan-out path in production.  Before
this module the dispatcher was instantiated only in tests, leaving the
production code path wired to ``FileNotifier`` only.

Design references
─────────────────
docs/design/g3_notifier_fix_plan.md
  §3.0 P-1  SafeStop priority — external notifiers must never block.
  §3.0 P-2  File-only fallback — ``FileNotifier`` is required; externals
            are best-effort and may be silently absent.
  §3.1     Factory responsibilities (silent skip of unconfigured channels).
  §5  C-1  Unconfigured channels are silently skipped; startup proceeds.
  §5  C-10 ``FileNotifier`` is always injected; configuration absence
            yields a degraded-but-running dispatcher.

PR-1 hard guard
───────────────
``EmailNotifier`` MUST NOT be activated by this factory.  ``email_notifier``
is hardcoded to ``None`` here and the ``EmailNotifier`` symbol is not
imported.  Email activation is the responsibility of PR-2 (after the
SMTP timeout / retry-budget changes land).  Until PR-2 is merged, an
ill-configured SMTP host could hang ``safe_stop`` step 3 indefinitely
(R-2 / R-3 in the G-3 audit), so the only safe state for this module
is "Email disabled at the construction site".
"""

from __future__ import annotations

import logging

from fx_ai_trading.adapters.notifier.base import NotifierBase
from fx_ai_trading.adapters.notifier.dispatcher import NotifierDispatcherImpl
from fx_ai_trading.adapters.notifier.file import FileNotifier
from fx_ai_trading.adapters.notifier.slack import SlackNotifier

_log = logging.getLogger(__name__)


def build_notifier_dispatcher(
    *,
    file_notifier: FileNotifier,
    slack_webhook_url: str | None = None,
) -> NotifierDispatcherImpl:
    """Build a production ``NotifierDispatcherImpl`` (file-only safe).

    The returned dispatcher always has ``FileNotifier`` wired as the
    last-resort path (P-2).  Slack is added only when a webhook URL is
    supplied; absent configuration is a silent skip with a warning log
    (C-1).  Email is never activated here (PR-1 hard guard — see module
    docstring); ``email_notifier`` is hardcoded to ``None`` and PR-2 is
    the only place that may flip this.

    Args:
        file_notifier: Required last-resort notifier (P-2 invariant).
        slack_webhook_url: Optional Slack webhook URL.  When None / empty
            the Slack channel is skipped silently (factory logs a
            warning so operators can correlate with missing config).

    Returns:
        A dispatcher whose externals contain only the configured
        channels and whose ``email_notifier`` is None.
    """
    externals: list[NotifierBase] = []
    if slack_webhook_url:
        externals.append(SlackNotifier(webhook_url=slack_webhook_url))
    else:
        _log.warning(
            "notifier_factory: Slack webhook URL not configured — channel skipped"
            " (file-only fallback per G-3 §3.0 P-2)"
        )

    # PR-1 hard guard: Email must NOT be activated until PR-2 lands the
    # SMTP timeout + retry-budget changes (G-3 §3.2 / R-2 / R-3).
    return NotifierDispatcherImpl(
        file_notifier=file_notifier,
        external_notifiers=externals,
        email_notifier=None,
    )


__all__ = ["build_notifier_dispatcher"]
