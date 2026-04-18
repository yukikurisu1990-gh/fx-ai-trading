"""Supervisor — process lifecycle manager (D4 §2 / M7).

Responsibilities in M7:
  - Startup: delegates to StartupRunner (16-step sequence).
  - Trading gate: exposes is_trading_allowed() flag.
  - Safe stop: delegates to SafeStopHandler (journal→loop→notifier→DB).
  - Health check: delegates to HealthChecker.

Responsibilities deferred to later milestones:
  - 1-minute trading cycle loop (M9/M12).
  - OutboxProcessor lifecycle (M8).
  - Reconciler / MidRunReconciler lifecycle (M8).
  - Metrics recording 9 items per minute (M12).
  - Emergency Flat CLI integration (M12).
"""

from __future__ import annotations

import logging
from datetime import datetime

from fx_ai_trading.common.clock import Clock
from fx_ai_trading.supervisor.startup import (
    StartupContext,
    StartupResult,
    StartupRunner,
)

_log = logging.getLogger(__name__)


class Supervisor:
    """Process lifecycle manager for the FX-AI-Trading system.

    Args:
        clock: Clock implementation for timestamping events.

    Usage:
        supervisor = Supervisor(clock=WallClock())
        try:
            result = supervisor.startup(ctx)
        except StartupError as e:
            # handle exit-severity failure
        if supervisor.is_trading_allowed():
            # begin trading loop
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._trading_allowed = False
        self._is_stopped = False

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def startup(self, ctx: StartupContext) -> StartupResult:
        """Execute the 16-step startup sequence.

        Sets is_trading_allowed() to True if the sequence completes with
        outcome 'ready' or 'degraded'.  Leaves it False on StartupError.

        Raises:
            StartupError: if a step fails with exit severity.
        """
        _log.info("Supervisor: beginning startup sequence")
        runner = StartupRunner(ctx)
        result = runner.run()
        self._trading_allowed = result.outcome in ("ready", "degraded")
        _log.info("Supervisor: startup outcome=%s", result.outcome)
        return result

    # ------------------------------------------------------------------
    # Trading gate
    # ------------------------------------------------------------------

    def is_trading_allowed(self) -> bool:
        """Return True iff startup succeeded and safe_stop has not fired."""
        return self._trading_allowed and not self._is_stopped

    # ------------------------------------------------------------------
    # Safe stop
    # ------------------------------------------------------------------

    def trigger_safe_stop(
        self,
        reason: str,
        occurred_at: datetime,
        payload: dict | None = None,
        context: object | None = None,
    ) -> None:
        """Fire the safe_stop sequence: journal → loop_stop → notifier → DB.

        This method delegates to SafeStopHandler.  It is safe to call
        multiple times — subsequent calls are logged but do not re-fire
        the sequence (idempotent loop-stop flag).

        Args:
            reason: Machine-readable stop reason (e.g. 'account_type_mismatch').
            occurred_at: UTC datetime of the triggering event (no clock.now() here).
            payload: Optional additional context for the Notifier.
            context: Optional CommonKeysContext for DB write.
        """
        if self._is_stopped:
            _log.warning("trigger_safe_stop called but already stopped (reason=%s) — no-op", reason)
            return

        from fx_ai_trading.supervisor.safe_stop import SafeStopHandler

        handler = SafeStopHandler(
            stop_callback=self._on_loop_stop,
        )
        handler.fire(reason=reason, occurred_at=occurred_at, payload=payload, context=context)

    def _on_loop_stop(self) -> None:
        """Internal callback executed by SafeStopHandler as loop-stop step."""
        self._trading_allowed = False
        self._is_stopped = True
        _log.critical("Supervisor: trading loop STOPPED (safe_stop)")

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def check_health(self, engine: object | None = None) -> object:
        """Run a health check and return HealthStatus.

        Args:
            engine: Optional SQLAlchemy Engine for DB connectivity check.

        Returns:
            HealthStatus dataclass (see supervisor/health.py).
        """
        from fx_ai_trading.supervisor.health import HealthChecker

        checker = HealthChecker(clock=self._clock)
        return checker.check(engine=engine)
