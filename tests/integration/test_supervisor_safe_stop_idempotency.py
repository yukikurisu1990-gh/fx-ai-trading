"""Integration tests: Supervisor.trigger_safe_stop idempotency reform (G-2 / I-G2-02).

PR-2 splits the idempotency key from _is_stopped to _safe_stop_completed:

  - _is_stopped              ← set as soon as step 2 (loop_stop) succeeds.
                                Drives is_trading_allowed() and metrics
                                gating; correctly true the moment the
                                trading loop is halted.
  - _safe_stop_completed     ← set ONLY when fire() returns True (every
                                step finished without raising).  This is
                                the new idempotency key for
                                trigger_safe_stop: a partial-completion
                                run leaves it False so a follow-up call
                                can retry the missing steps.

Pre-PR-2 bug: _is_stopped was used as the idempotency key, so any failure
in step 3 (notifier) or step 4 (DB) would still flip _is_stopped (because
step 2 ran first), and the next trigger_safe_stop call became a silent
no-op — operators lost the ability to retry the missing notification or
DB write.

Verified here:
  - Happy path: 1st trigger flips both flags; 2nd trigger is no-op.
  - Notifier partial failure: 1st trigger flips _is_stopped only;
    2nd trigger re-runs the sequence and completes both flags.
  - _is_stopped semantics preserved: trading is gated off as soon as
    step 2 succeeds, regardless of step 3/4 outcome.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.supervisor.safe_stop_journal import SafeStopJournal
from fx_ai_trading.supervisor.startup import StartupContext
from fx_ai_trading.supervisor.supervisor import Supervisor

_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)
_CLOCK = FixedClock(_FIXED_AT)


@pytest.fixture()
def journal(tmp_path: Path) -> SafeStopJournal:
    return SafeStopJournal(journal_path=tmp_path / "safe_stop.jsonl")


@pytest.fixture()
def notifier() -> MagicMock:
    m = MagicMock()
    m.dispatch_direct_sync.return_value = None
    return m


def _started_supervisor(journal: SafeStopJournal, notifier: MagicMock) -> Supervisor:
    sup = Supervisor(clock=_CLOCK)
    ctx = StartupContext(
        journal=journal,
        notifier=notifier,
        clock=_CLOCK,
    )
    sup.startup(ctx)
    return sup


class TestHappyPathIdempotency:
    def test_first_trigger_sets_both_flags(self, journal, notifier) -> None:
        sup = _started_supervisor(journal, notifier)
        sup.trigger_safe_stop(reason="first", occurred_at=_FIXED_AT)
        assert sup._is_stopped is True
        assert sup._safe_stop_completed is True

    def test_second_trigger_is_noop_when_first_succeeded(self, journal, notifier) -> None:
        sup = _started_supervisor(journal, notifier)
        sup.trigger_safe_stop(reason="first", occurred_at=_FIXED_AT)
        notifier.dispatch_direct_sync.reset_mock()

        sup.trigger_safe_stop(reason="second", occurred_at=_FIXED_AT)
        # Second trigger must NOT re-fire the sequence.
        notifier.dispatch_direct_sync.assert_not_called()

    def test_second_trigger_does_not_double_journal(self, journal, notifier) -> None:
        sup = _started_supervisor(journal, notifier)
        sup.trigger_safe_stop(reason="first", occurred_at=_FIXED_AT)
        sup.trigger_safe_stop(reason="second", occurred_at=_FIXED_AT)
        entries = [e for e in journal.read_all() if e.get("event_code") == "safe_stop.triggered"]
        assert len(entries) == 1


class TestPartialFailureRetry:
    def test_notifier_failure_leaves_safe_stop_completed_false(self, journal, notifier) -> None:
        notifier.dispatch_direct_sync.side_effect = RuntimeError("slack 503")
        sup = _started_supervisor(journal, notifier)

        sup.trigger_safe_stop(reason="first", occurred_at=_FIXED_AT)

        assert sup._is_stopped is True, "step 2 ran, _is_stopped must be True"
        assert sup._safe_stop_completed is False, (
            "step 3 raised, _safe_stop_completed must remain False so retry is allowed"
        )

    def test_second_trigger_after_notifier_failure_retries_sequence(
        self, journal, notifier
    ) -> None:
        # First trigger: notifier fails.
        notifier.dispatch_direct_sync.side_effect = RuntimeError("slack 503")
        sup = _started_supervisor(journal, notifier)
        sup.trigger_safe_stop(reason="first", occurred_at=_FIXED_AT)
        first_call_count = notifier.dispatch_direct_sync.call_count
        assert first_call_count == 1, "step 3 should have been attempted exactly once"

        # Second trigger: notifier recovered.
        notifier.dispatch_direct_sync.side_effect = None
        sup.trigger_safe_stop(reason="second", occurred_at=_FIXED_AT)

        # Notifier must have been re-attempted on the second trigger.
        assert notifier.dispatch_direct_sync.call_count == 2, (
            "second trigger must re-run step 3 because _safe_stop_completed was False"
        )
        assert sup._safe_stop_completed is True, (
            "second trigger fully succeeded — _safe_stop_completed must now be True"
        )

    def test_third_trigger_after_recovery_is_noop(self, journal, notifier) -> None:
        notifier.dispatch_direct_sync.side_effect = RuntimeError("slack 503")
        sup = _started_supervisor(journal, notifier)
        sup.trigger_safe_stop(reason="first", occurred_at=_FIXED_AT)

        notifier.dispatch_direct_sync.side_effect = None
        sup.trigger_safe_stop(reason="second", occurred_at=_FIXED_AT)

        third_call_count_before = notifier.dispatch_direct_sync.call_count
        sup.trigger_safe_stop(reason="third", occurred_at=_FIXED_AT)
        # Third trigger must be a no-op (sequence already completed).
        assert notifier.dispatch_direct_sync.call_count == third_call_count_before


class TestIsStoppedSemanticsPreserved:
    def test_trading_gated_off_even_on_partial_failure(self, journal, notifier) -> None:
        notifier.dispatch_direct_sync.side_effect = RuntimeError("slack 503")
        sup = _started_supervisor(journal, notifier)
        assert sup.is_trading_allowed() is True

        sup.trigger_safe_stop(reason="first", occurred_at=_FIXED_AT)

        # Trading must be gated off as soon as step 2 succeeds —
        # independent of whether step 3/4 succeeded.
        assert sup.is_trading_allowed() is False

    def test_trading_remains_gated_off_across_retries(self, journal, notifier) -> None:
        notifier.dispatch_direct_sync.side_effect = RuntimeError("slack 503")
        sup = _started_supervisor(journal, notifier)
        sup.trigger_safe_stop(reason="first", occurred_at=_FIXED_AT)

        notifier.dispatch_direct_sync.side_effect = None
        sup.trigger_safe_stop(reason="second", occurred_at=_FIXED_AT)

        assert sup.is_trading_allowed() is False


class TestFlagInitialization:
    def test_safe_stop_completed_starts_false(self) -> None:
        sup = Supervisor(clock=_CLOCK)
        assert sup._safe_stop_completed is False

    def test_is_stopped_starts_false(self) -> None:
        sup = Supervisor(clock=_CLOCK)
        assert sup._is_stopped is False
