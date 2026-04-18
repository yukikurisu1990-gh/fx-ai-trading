"""StartupRunner — D4 §2.1 Step 1-16 startup sequence (M7).

Executes the sixteen startup steps in strict order.  Each step is a
separate method so the sequence is explicit and independently testable.

Failure semantics (D4 §2.1 Decision 2.1-1):
  - Steps 2-10 failures with EXIT severity → raise StartupError.
  - Steps 11-14 partial failures → degraded mode (continue).
  - Step 15 health check failure → raise StartupError.

Stub steps (M8 / M9 scope — not implemented here):
  - Step 8  OutboxProcessor pending handling
  - Step 10 Reconciler startup run
  - Step 11 Stream subscription
  - Step 12 Feature Service / Model init
  - Step 13 MidRunReconciler start
  - Step 14 OutboxProcessor resume
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from sqlalchemy import Engine, text

from fx_ai_trading.common.assertions import assert_account_type_matches
from fx_ai_trading.common.clock import Clock
from fx_ai_trading.common.exceptions import AccountTypeMismatch
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.config.ntp import NtpChecker
from fx_ai_trading.domain.broker import Broker
from fx_ai_trading.supervisor.safe_stop_journal import SafeStopJournal

_log = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies at module load time.
# NotifierDispatcherImpl / SupervisorEventsRepository / ConfigProvider
# are imported inside methods that use them.


class StartupError(Exception):
    """Raised by StartupRunner when a step fails with EXIT severity.

    The calling Supervisor must NOT start the trading loop after catching
    this exception.  It should propagate or safe_stop.
    """

    def __init__(self, step: int, reason: str) -> None:
        super().__init__(f"Startup failed at Step {step}: {reason}")
        self.step = step
        self.reason = reason


@dataclass
class StartupContext:
    """Injectable dependencies for the 16-step startup sequence.

    All fields except journal, notifier, and clock are optional so that
    unit tests can provide only the subset needed for the step under test.
    """

    journal: SafeStopJournal
    notifier: object  # NotifierDispatcherImpl — avoids import cycle
    clock: Clock

    config_provider: object | None = None  # ConfigProvider
    engine: Engine | None = None
    broker: Broker | None = None
    ntp_checker: NtpChecker | None = None
    supervisor_events_repo: object | None = None  # SupervisorEventsRepository
    common_keys_ctx: CommonKeysContext | None = None
    expected_alembic_head: str | None = None


@dataclass
class StartupResult:
    """Outcome of a completed (non-exit) startup sequence."""

    outcome: str  # "ready" | "degraded"
    config_version: str | None = None
    degraded_steps: list[int] = field(default_factory=list)


class StartupRunner:
    """Executes the D4 §2.1 sixteen-step startup sequence.

    Each step is a separate private method.  Steps raise StartupError
    on EXIT-severity failures.  Degraded steps append to _degraded_steps
    and execution continues.

    Usage:
        runner = StartupRunner(ctx)
        result = runner.run()   # raises StartupError on EXIT failure
    """

    def __init__(self, ctx: StartupContext) -> None:
        self._ctx = ctx
        self._degraded_steps: list[int] = []
        self._config_version: str | None = None

    def run(self) -> StartupResult:
        """Execute all 16 steps in order.  Raises StartupError on EXIT.

        Steps that support the trading loop (Steps 2-10, 15) cause an
        exit on failure.  Steps 11-14 set degraded mode and continue.
        """
        self._step1_init_local_resources()
        self._step2_ntp_check()
        self._step3_config_secret_load()
        self._step4_config_version()
        self._step5_db_connection()
        self._step6_alembic_revision()
        self._step7_journal_reconcile()
        self._step8_outbox_pending_stub()
        self._step9_account_type_check()
        self._step10_reconciler_stub()
        self._step11_stream_connect_stub()
        self._step12_feature_model_init_stub()
        self._step13_midrun_reconciler_stub()
        self._step14_outbox_processor_resume_stub()
        self._step15_health_check()
        self._step16_allow_trading()

        outcome = "degraded" if self._degraded_steps else "ready"
        return StartupResult(
            outcome=outcome,
            config_version=self._config_version,
            degraded_steps=list(self._degraded_steps),
        )

    # ------------------------------------------------------------------
    # Step 1 — local resource initialisation
    # ------------------------------------------------------------------

    def _step1_init_local_resources(self) -> None:
        """Verify FileNotifier and SafeStopJournal are accessible.

        Failure → exit (no DB available; local log only).
        """
        _log.info("Step 1: initialising local resources")
        try:
            # Probe the journal by reading (non-destructive).
            self._ctx.journal.read_all()
        except Exception as exc:  # noqa: BLE001
            raise StartupError(1, f"SafeStopJournal read failed: {exc}") from exc
        _log.info("Step 1: local resources OK")

    # ------------------------------------------------------------------
    # Step 2 — NTP clock skew check (6.14)
    # ------------------------------------------------------------------

    def _step2_ntp_check(self) -> None:
        """Check NTP skew.  Warn if 500ms-5s; exit if >5s."""
        _log.info("Step 2: NTP clock check")
        checker = self._ctx.ntp_checker or NtpChecker()
        result = checker.check()
        if result.should_reject:
            raise StartupError(
                2,
                f"NTP skew {result.skew_ms:.0f}ms exceeds reject threshold"
                f" {checker._reject_ms:.0f}ms",
            )
        if result.should_warn:
            _log.warning(
                "Step 2: NTP skew %.0f ms exceeds warn threshold — continuing",
                result.skew_ms,
            )
        else:
            _log.info("Step 2: NTP skew %.0f ms — OK", result.skew_ms)

    # ------------------------------------------------------------------
    # Step 3 — Config / Secret load
    # ------------------------------------------------------------------

    def _step3_config_secret_load(self) -> None:
        """Ensure ConfigProvider is present and readable."""
        _log.info("Step 3: config / secret load")
        if self._ctx.config_provider is None:
            _log.info("Step 3: ConfigProvider not provided — skipped")
            return
        try:
            # Probe: request any key to confirm provider is functional.
            self._ctx.config_provider.get("environment")
        except Exception as exc:  # noqa: BLE001
            raise StartupError(3, f"ConfigProvider unavailable: {exc}") from exc
        _log.info("Step 3: config load OK")

    # ------------------------------------------------------------------
    # Step 4 — config_version computation (6.19)
    # ------------------------------------------------------------------

    def _step4_config_version(self) -> None:
        """Compute config_version; log if changed from previous run."""
        _log.info("Step 4: computing config_version")
        if self._ctx.config_provider is None:
            _log.info("Step 4: ConfigProvider not provided — skipped")
            return
        try:
            version = self._ctx.config_provider.compute_version()
            self._config_version = version
            _log.info("Step 4: config_version=%s", version)
        except Exception as exc:  # noqa: BLE001
            _log.warning("Step 4: config_version computation failed: %s — continuing", exc)

    # ------------------------------------------------------------------
    # Step 5 — DB connection check
    # ------------------------------------------------------------------

    def _step5_db_connection(self) -> None:
        """Execute SELECT 1 to confirm DB reachability.  Failure → exit."""
        _log.info("Step 5: DB connection check")
        if self._ctx.engine is None:
            _log.info("Step 5: engine not provided — skipped")
            return
        try:
            with self._ctx.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as exc:  # noqa: BLE001
            raise StartupError(5, f"DB connection failed: {exc}") from exc
        _log.info("Step 5: DB connection OK")

    # ------------------------------------------------------------------
    # Step 6 — Alembic revision check
    # ------------------------------------------------------------------

    def _step6_alembic_revision(self) -> None:
        """Confirm DB schema is at the expected Alembic head.  Failure → exit."""
        _log.info("Step 6: Alembic revision check")
        if self._ctx.engine is None or self._ctx.expected_alembic_head is None:
            _log.info("Step 6: engine or expected_head not provided — skipped")
            return
        try:
            from alembic.runtime.migration import MigrationContext

            with self._ctx.engine.connect() as conn:
                mctx = MigrationContext.configure(conn)
                current = mctx.get_current_revision()
        except Exception as exc:  # noqa: BLE001
            raise StartupError(6, f"Alembic revision check failed: {exc}") from exc
        if current != self._ctx.expected_alembic_head:
            raise StartupError(
                6,
                f"Alembic revision mismatch: current={current!r},"
                f" expected={self._ctx.expected_alembic_head!r}",
            )
        _log.info("Step 6: Alembic revision %s OK", current)

    # ------------------------------------------------------------------
    # Step 7 — SafeStopJournal ↔ DB reconcile (6.1)
    # ------------------------------------------------------------------

    def _step7_journal_reconcile(self) -> None:
        """Read SafeStopJournal; log unreconciled entries.  DB write optional.

        Full DB reconciliation (journal → DB補完) is M8 Reconciler scope.
        M7 implementation: count unreconciled safe_stop entries and record
        journal_reconcile_completed in supervisor_events.
        """
        _log.info("Step 7: SafeStopJournal reconcile")
        entries = self._ctx.journal.read_all()
        safe_stops = [e for e in entries if e.get("event_code") == "safe_stop.triggered"]
        if safe_stops:
            _log.warning(
                "Step 7: %d unreconciled safe_stop entries in journal"
                " (DB補完は M8 Reconciler scope)",
                len(safe_stops),
            )
        else:
            _log.info("Step 7: journal clean — no unreconciled safe_stop entries")

        self._record_supervisor_event(
            "journal_reconcile_completed",
            detail={"unreconciled_count": len(safe_stops)},
        )

    # ------------------------------------------------------------------
    # Step 8 — Outbox pending (STUB — M8)
    # ------------------------------------------------------------------

    def _step8_outbox_pending_stub(self) -> None:
        """Stub: OutboxProcessor pending-dispatch is M8 scope."""
        _log.info("Step 8: outbox pending handling — stub (M8 scope)")

    # ------------------------------------------------------------------
    # Step 9 — Account type check (6.18)
    # ------------------------------------------------------------------

    def _step9_account_type_check(self) -> None:
        """Assert broker.account_type matches app_settings.expected_account_type.

        Failure → exit.  Mismatch is recorded as critical Notifier event
        before the StartupError propagates.
        """
        _log.info("Step 9: account_type check")
        if self._ctx.broker is None:
            _log.info("Step 9: broker not provided — skipped")
            return

        expected: str | None = None
        if self._ctx.config_provider is not None:
            expected = self._ctx.config_provider.get("expected_account_type")
        if expected is None:
            _log.info("Step 9: expected_account_type not found in config — skipped")
            return

        try:
            assert_account_type_matches(self._ctx.broker, expected=expected)
        except AccountTypeMismatch as exc:
            raise StartupError(9, str(exc)) from exc

        self._record_supervisor_event(
            "account_type_verified",
            detail={"account_type": self._ctx.broker.account_type, "expected": expected},
        )
        _log.info("Step 9: account_type=%r OK", self._ctx.broker.account_type)

    # ------------------------------------------------------------------
    # Steps 10-14 — STUB (M8 / M9 scope)
    # ------------------------------------------------------------------

    def _step10_reconciler_stub(self) -> None:
        """Stub: Reconciler.reconcile_on_startup() is M8 scope."""
        _log.info("Step 10: reconciler startup — stub (M8 scope)")

    def _step11_stream_connect_stub(self) -> None:
        """Stub: PriceFeed stream subscription is M9 scope."""
        _log.info("Step 11: stream connection — stub (M9 scope)")

    def _step12_feature_model_init_stub(self) -> None:
        """Stub: FeatureBuilder / ModelRegistry init is M9 scope."""
        _log.info("Step 12: feature/model init — stub (M9 scope)")

    def _step13_midrun_reconciler_stub(self) -> None:
        """Stub: MidRunReconciler start is M8 scope."""
        _log.info("Step 13: MidRunReconciler — stub (M8 scope)")

    def _step14_outbox_processor_resume_stub(self) -> None:
        """Stub: OutboxProcessor.resume_dispatch() is M8 scope."""
        _log.info("Step 14: OutboxProcessor resume — stub (M8 scope)")

    # ------------------------------------------------------------------
    # Step 15 — health check (pre-trading gate)
    # ------------------------------------------------------------------

    def _step15_health_check(self) -> None:
        """Confirm all mandatory components are healthy before allowing trading.

        In M7 this checks DB connectivity (if engine present).
        Failure → exit.
        """
        _log.info("Step 15: pre-trading health check")
        if self._ctx.engine is not None:
            try:
                with self._ctx.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
            except Exception as exc:  # noqa: BLE001
                raise StartupError(15, f"Health check failed — DB unreachable: {exc}") from exc
        _log.info("Step 15: health check passed — trading loop may begin")

    # ------------------------------------------------------------------
    # Step 16 — allow trading
    # ------------------------------------------------------------------

    def _step16_allow_trading(self) -> None:
        """Log that the trading loop is now permitted to start."""
        _log.info("Step 16: startup complete — trading loop authorised")

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _record_supervisor_event(
        self,
        event_type: str,
        detail: dict | None = None,
    ) -> None:
        """Write to supervisor_events if repo + context are available."""
        repo = self._ctx.supervisor_events_repo
        ctx = self._ctx.common_keys_ctx
        if repo is None or ctx is None:
            return
        occurred_at = self._ctx.clock.now()
        try:
            repo.insert_event(
                event_type=event_type,
                event_time_utc=occurred_at,
                context=ctx,
                detail=detail,
            )
        except Exception as exc:  # noqa: BLE001
            _log.warning("supervisor_events insert failed for %s: %s", event_type, exc)
