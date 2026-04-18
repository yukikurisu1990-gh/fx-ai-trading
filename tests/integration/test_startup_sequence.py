"""Integration tests for D4 §2.1 Step 1-16 startup sequence (M7).

No DATABASE_URL required for most tests — the engine fixture uses
SQLite in-memory with a fully migrated schema.

Test coverage:
  - Happy path: all Steps succeed → outcome='ready'
  - Step 1 failure: journal inaccessible → StartupError(step=1)
  - Step 2 NTP warn: skew 500ms–5s → continues (no StartupError)
  - Step 2 NTP reject: skew >5s → StartupError(step=2)
  - Step 5 DB failure: engine raises → StartupError(step=5)
  - Step 6 Alembic mismatch: wrong head → StartupError(step=6)
  - Step 9 account_type mismatch: → StartupError(step=9)
  - Stub steps 8/10-14: run silently, no error
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.config.ntp import NtpChecker
from fx_ai_trading.supervisor.safe_stop_journal import SafeStopJournal
from fx_ai_trading.supervisor.startup import StartupContext, StartupError, StartupRunner

_FIXED_AT = datetime(2026, 1, 1, tzinfo=UTC)
_CLOCK = FixedClock(_FIXED_AT)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def journal(tmp_path: Path) -> SafeStopJournal:
    return SafeStopJournal(journal_path=tmp_path / "safe_stop.jsonl")


@pytest.fixture()
def notifier() -> MagicMock:
    m = MagicMock()
    m.dispatch_direct_sync.return_value = None
    return m


def _make_ctx(
    journal: SafeStopJournal,
    notifier: MagicMock,
    *,
    engine=None,
    broker=None,
    ntp_checker=None,
    config_provider=None,
    expected_alembic_head=None,
) -> StartupContext:
    return StartupContext(
        journal=journal,
        notifier=notifier,
        clock=_CLOCK,
        engine=engine,
        broker=broker,
        ntp_checker=ntp_checker,
        config_provider=config_provider,
        expected_alembic_head=expected_alembic_head,
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_all_steps_succeed_returns_ready(self, journal, notifier) -> None:
        ctx = _make_ctx(journal, notifier)
        result = StartupRunner(ctx).run()
        assert result.outcome == "ready"

    def test_trading_allowed_after_ready(self, journal, notifier) -> None:
        from fx_ai_trading.supervisor.supervisor import Supervisor

        sup = Supervisor(clock=_CLOCK)
        ctx = _make_ctx(journal, notifier)
        result = sup.startup(ctx)
        assert result.outcome == "ready"
        assert sup.is_trading_allowed()

    def test_config_version_captured_in_result(self, journal, notifier) -> None:
        mock_provider = MagicMock()
        mock_provider.get.return_value = None
        mock_provider.compute_version.return_value = "abc123deadbeef00"
        ctx = _make_ctx(journal, notifier, config_provider=mock_provider)
        result = StartupRunner(ctx).run()
        assert result.config_version == "abc123deadbeef00"


# ---------------------------------------------------------------------------
# Step 1 — local resource failure
# ---------------------------------------------------------------------------


class TestStep1LocalResources:
    def test_journal_read_failure_raises_startup_error(self, notifier, tmp_path) -> None:
        bad_journal = MagicMock()
        bad_journal.read_all.side_effect = OSError("permission denied")
        ctx = _make_ctx(bad_journal, notifier)
        with pytest.raises(StartupError) as exc_info:
            StartupRunner(ctx).run()
        assert exc_info.value.step == 1


# ---------------------------------------------------------------------------
# Step 2 — NTP checks
# ---------------------------------------------------------------------------


class TestStep2Ntp:
    def _checker_with_skew(self, skew_ms: float) -> NtpChecker:
        checker = NtpChecker()
        checker.measure_skew_ms = lambda: skew_ms  # type: ignore[method-assign]
        return checker

    def test_ok_skew_passes(self, journal, notifier) -> None:
        ctx = _make_ctx(journal, notifier, ntp_checker=self._checker_with_skew(0.0))
        result = StartupRunner(ctx).run()
        assert result.outcome == "ready"

    def test_warn_skew_continues(self, journal, notifier) -> None:
        ctx = _make_ctx(journal, notifier, ntp_checker=self._checker_with_skew(1000.0))
        result = StartupRunner(ctx).run()
        assert result.outcome == "ready"

    def test_reject_skew_raises_startup_error(self, journal, notifier) -> None:
        ctx = _make_ctx(journal, notifier, ntp_checker=self._checker_with_skew(6000.0))
        with pytest.raises(StartupError) as exc_info:
            StartupRunner(ctx).run()
        assert exc_info.value.step == 2

    def test_startup_error_contains_skew_info(self, journal, notifier) -> None:
        ctx = _make_ctx(journal, notifier, ntp_checker=self._checker_with_skew(9999.0))
        with pytest.raises(StartupError) as exc_info:
            StartupRunner(ctx).run()
        assert "9999" in exc_info.value.reason or "skew" in exc_info.value.reason.lower()


# ---------------------------------------------------------------------------
# Step 5 — DB connection
# ---------------------------------------------------------------------------


class TestStep5DbConnection:
    def test_db_failure_raises_startup_error(self, journal, notifier) -> None:
        bad_engine = MagicMock()
        bad_engine.connect.side_effect = Exception("connection refused")
        ctx = _make_ctx(journal, notifier, engine=bad_engine)
        with pytest.raises(StartupError) as exc_info:
            StartupRunner(ctx).run()
        assert exc_info.value.step == 5

    def test_db_success_passes(self, journal, notifier, tmp_path) -> None:
        engine = create_engine("sqlite:///:memory:")
        ctx = _make_ctx(journal, notifier, engine=engine)
        result = StartupRunner(ctx).run()
        assert result.outcome == "ready"


# ---------------------------------------------------------------------------
# Step 6 — Alembic revision
# ---------------------------------------------------------------------------


class TestStep6AlembicRevision:
    def test_revision_mismatch_raises_startup_error(self, journal, notifier) -> None:
        engine = create_engine("sqlite:///:memory:")
        ctx = _make_ctx(
            journal,
            notifier,
            engine=engine,
            expected_alembic_head="nonexistent_rev_abc123",
        )
        with pytest.raises(StartupError) as exc_info:
            StartupRunner(ctx).run()
        assert exc_info.value.step == 6

    def test_skipped_when_head_not_provided(self, journal, notifier) -> None:
        engine = create_engine("sqlite:///:memory:")
        ctx = _make_ctx(journal, notifier, engine=engine)  # no expected_alembic_head
        result = StartupRunner(ctx).run()
        assert result.outcome == "ready"


# ---------------------------------------------------------------------------
# Step 9 — account_type check
# ---------------------------------------------------------------------------


class TestStep9AccountType:
    def _mock_config(self, expected_type: str) -> MagicMock:
        cp = MagicMock()
        cp.get.side_effect = lambda name: expected_type if name == "expected_account_type" else None
        cp.compute_version.return_value = "abc123"
        return cp

    def test_matching_account_type_passes(self, journal, notifier) -> None:
        broker = MagicMock()
        broker.account_type = "demo"
        ctx = _make_ctx(journal, notifier, broker=broker, config_provider=self._mock_config("demo"))
        result = StartupRunner(ctx).run()
        assert result.outcome == "ready"

    def test_mismatched_account_type_raises_startup_error(self, journal, notifier) -> None:
        broker = MagicMock()
        broker.account_type = "live"
        ctx = _make_ctx(journal, notifier, broker=broker, config_provider=self._mock_config("demo"))
        with pytest.raises(StartupError) as exc_info:
            StartupRunner(ctx).run()
        assert exc_info.value.step == 9

    def test_skipped_when_broker_not_provided(self, journal, notifier) -> None:
        ctx = _make_ctx(journal, notifier)  # no broker
        result = StartupRunner(ctx).run()
        assert result.outcome == "ready"


# ---------------------------------------------------------------------------
# Stub steps (8, 10-14) — must not raise
# ---------------------------------------------------------------------------


class TestStubSteps:
    def test_all_stubs_run_without_error(self, journal, notifier) -> None:
        ctx = _make_ctx(journal, notifier)
        result = StartupRunner(ctx).run()
        assert result.outcome == "ready"


# ---------------------------------------------------------------------------
# Step 15 — pre-trading health check
# ---------------------------------------------------------------------------


class TestStep15HealthCheck:
    def test_db_failure_in_health_check_raises(self, journal, notifier) -> None:
        bad_engine = MagicMock()
        # Step 5 uses connect() — make that succeed so we reach step 15
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=MagicMock())
        cm.__exit__ = MagicMock(return_value=False)
        bad_engine.connect.return_value = cm
        # But make the second call (step 15) raise
        call_count = {"n": 0}

        def side_effect():
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise Exception("DB down at step 15")
            return cm

        bad_engine.connect.side_effect = side_effect
        ctx = _make_ctx(journal, notifier, engine=bad_engine)
        with pytest.raises(StartupError) as exc_info:
            StartupRunner(ctx).run()
        assert exc_info.value.step == 15


# ---------------------------------------------------------------------------
# Supervisor.trigger_safe_stop integration
# ---------------------------------------------------------------------------


class TestSupervisorSafeStop:
    def test_safe_stop_prevents_trading(self, journal, notifier) -> None:
        from fx_ai_trading.supervisor.supervisor import Supervisor

        sup = Supervisor(clock=_CLOCK)
        ctx = _make_ctx(journal, notifier)
        sup.startup(ctx)
        assert sup.is_trading_allowed()

        sup.trigger_safe_stop(reason="test_stop", occurred_at=_FIXED_AT, payload={}, context=None)
        assert not sup.is_trading_allowed()

    def test_safe_stop_is_idempotent(self, journal, notifier) -> None:
        from fx_ai_trading.supervisor.supervisor import Supervisor

        sup = Supervisor(clock=_CLOCK)
        ctx = _make_ctx(journal, notifier)
        sup.startup(ctx)
        sup.trigger_safe_stop("reason_a", _FIXED_AT)
        sup.trigger_safe_stop("reason_b", _FIXED_AT)  # second call must not raise
        assert not sup.is_trading_allowed()
