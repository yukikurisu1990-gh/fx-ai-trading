"""Supervisor — process lifecycle manager (D4 §2 / M7).

Responsibilities in M7:
  - Startup: delegates to StartupRunner (16-step sequence).
  - Trading gate: exposes is_trading_allowed() flag.
  - Safe stop: delegates to SafeStopHandler (journal→loop→notifier→DB).
  - Health check: delegates to HealthChecker.

Responsibilities deferred to later milestones:
  - 1-minute trading cycle loop owner (M12).  Note: the per-tick
    ``run_exit_gate_tick`` seam is wired here in M9/H-1 so the
    forthcoming M12 loop can simply call it; the loop itself is still
    out of scope.
  - OutboxProcessor lifecycle (M8).
  - Reconciler / MidRunReconciler lifecycle (M8).
  - Emergency Flat CLI integration (M12).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from fx_ai_trading.common.clock import Clock
from fx_ai_trading.supervisor.startup import (
    StartupContext,
    StartupResult,
    StartupRunner,
)

if TYPE_CHECKING:
    from fx_ai_trading.domain.broker import Broker
    from fx_ai_trading.services.exit_gate_runner import ExitGateRunResult
    from fx_ai_trading.services.exit_policy import ExitPolicyService
    from fx_ai_trading.services.state_manager import StateManager

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class _ExitGateAttachment:
    """Snapshot of the exit-gate dependencies bound to a Supervisor.

    Created by ``Supervisor.attach_exit_gate`` and consumed by
    ``Supervisor.run_exit_gate_tick`` so a single attach call freezes
    the wiring for every subsequent cadence tick.  Held privately —
    callers only see ``attach_exit_gate`` / ``run_exit_gate_tick``.
    """

    broker: Broker
    account_id: str
    state_manager: StateManager
    exit_policy: ExitPolicyService
    price_feed: Callable[[str], float]
    tp: float | None
    sl: float | None
    context: dict[str, Any] | None


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
        # _safe_stop_completed is set to True only when every step of the
        # SafeStopHandler 4-step sequence (journal → loop_stop → notifier →
        # supervisor_events) finishes without raising.  It is the
        # idempotency key for trigger_safe_stop: a partial completion
        # (e.g., notifier failed) leaves it False so a follow-up
        # trigger_safe_stop call can re-run the sequence.  This is
        # orthogonal to _is_stopped, which records "the trading loop has
        # been halted" and is set as soon as step 2 succeeds.
        self._safe_stop_completed = False
        self._journal: object = None
        self._notifier: object = None
        self._supervisor_events_repo: object = None
        self._common_keys_ctx: object = None
        self._metrics_loop: object = None
        # M9 / H-1: exit-gate cadence wiring.  None until attach_exit_gate
        # is called by the host (M12 main loop / paper smoke harness).
        self._exit_gate: _ExitGateAttachment | None = None

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
        self._journal = ctx.journal
        self._notifier = ctx.notifier
        self._supervisor_events_repo = ctx.supervisor_events_repo
        self._common_keys_ctx = ctx.common_keys_ctx
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
        multiple times.  The idempotency key is _safe_stop_completed,
        which is set only when every step of the previous fire() call
        succeeded.  If a previous call left the sequence partially
        complete (e.g., notifier dispatch failed), a follow-up call
        re-runs the sequence so the missing steps can be retried.

        Args:
            reason: Machine-readable stop reason (e.g. 'account_type_mismatch').
            occurred_at: UTC datetime of the triggering event (no clock.now() here).
            payload: Optional additional context for the Notifier.
            context: Optional CommonKeysContext for DB write.
        """
        if self._safe_stop_completed:
            _log.warning(
                "trigger_safe_stop called but safe_stop already completed (reason=%s) — no-op",
                reason,
            )
            return

        from fx_ai_trading.supervisor.safe_stop import SafeStopHandler

        handler = SafeStopHandler(
            journal=self._journal,
            notifier=self._notifier,
            stop_callback=self._on_loop_stop,
            supervisor_events_repo=self._supervisor_events_repo,
            common_keys_ctx=self._common_keys_ctx,
        )
        all_steps_ok = handler.fire(
            reason=reason, occurred_at=occurred_at, payload=payload, context=context
        )
        if all_steps_ok:
            self._safe_stop_completed = True
        else:
            _log.warning(
                "trigger_safe_stop: safe_stop sequence partially completed (reason=%s) — "
                "_safe_stop_completed remains False so a follow-up trigger can retry",
                reason,
            )

    def _on_loop_stop(self) -> None:
        """Internal callback executed by SafeStopHandler as loop-stop step."""
        self._trading_allowed = False
        self._is_stopped = True
        _log.critical("Supervisor: trading loop STOPPED (safe_stop)")

    # ------------------------------------------------------------------
    # Metrics loop (M16)
    # ------------------------------------------------------------------

    def attach_metrics_loop(self, metrics_loop: object) -> None:
        """Attach a MetricsLoop instance for caller-driven 60s recording.

        Args:
            metrics_loop: MetricsLoop from supervisor/metrics_loop.py.
        """
        self._metrics_loop = metrics_loop

    def record_metrics(
        self,
        *,
        cycle_duration_seconds: float | None = None,
        stream_heartbeat_age_seconds: float | None = None,
    ) -> bool:
        """Record one metric_sample at clock.now().

        No-op (returns False) if no MetricsLoop is attached or if
        safe_stop has fired.  DB write failures are fail-open (MetricsLoop
        logs a warning and returns False without raising).

        Returns:
            True if the metric_sample was written, False otherwise.
        """
        if self._metrics_loop is None or self._is_stopped:
            return False
        return self._metrics_loop.record(  # type: ignore[union-attr]
            self._clock.now(),
            cycle_duration_seconds=cycle_duration_seconds,
            stream_heartbeat_age_seconds=stream_heartbeat_age_seconds,
        )

    # ------------------------------------------------------------------
    # Exit gate cadence (M9 / H-1)
    # ------------------------------------------------------------------

    def attach_exit_gate(
        self,
        *,
        broker: Broker,
        account_id: str,
        state_manager: StateManager,
        exit_policy: ExitPolicyService,
        price_feed: Callable[[str], float],
        tp: float | None = None,
        sl: float | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Bind the dependencies needed by ``run_exit_gate_tick``.

        Mirrors ``attach_metrics_loop``: caller-driven cadence.  The
        Supervisor itself does NOT spin a loop (deferred to M9/M12 per
        the class docstring); this attach freezes the wiring so a host
        loop can fire ``run_exit_gate_tick`` per cadence.

        Calling this twice replaces the previous attachment.

        M-1b note:
            The pre-M-1b ``side=`` argument was removed.  The closing
            side is now derived per-position from
            ``OpenPositionInfo.side`` inside ``run_exit_gate`` (which in
            turn comes from ``orders.direction`` via the M-1a JOIN).
            Callers no longer pass a process-wide side.

        Args:
            broker: Paper or live Broker.
            account_id: Must match ``state_manager.account_id``.
            state_manager: Authoritative open-positions source.
            exit_policy: Configured ExitPolicyService.
            price_feed: ``instrument → current_price`` callable.
            tp, sl, context: Forwarded to ``run_exit_gate`` unchanged
                each tick.
        """
        self._exit_gate = _ExitGateAttachment(
            broker=broker,
            account_id=account_id,
            state_manager=state_manager,
            exit_policy=exit_policy,
            price_feed=price_feed,
            tp=tp,
            sl=sl,
            context=context,
        )

    def run_exit_gate_tick(self) -> list[ExitGateRunResult]:
        """Run one exit-gate evaluation pass and return its results.

        No-op (returns ``[]``) when:
          - ``attach_exit_gate`` has not been called, OR
          - ``safe_stop`` has fired (``self._is_stopped is True``).

        The post-stop guard mirrors ``record_metrics`` and keeps cadence
        ticks safe to schedule unconditionally — once SafeStop owns the
        process, no further close orders are placed by the cadence path.
        SafeStop's own close-out flow is unchanged by this method.

        Exceptions raised by ``run_exit_gate`` propagate to the caller,
        matching that function's contract.  In particular,
        ``AccountTypeMismatchRuntime`` first triggers
        ``self.trigger_safe_stop`` (because we pass ``supervisor=self``
        below — the existing PR-5 / U-2 wiring) and is then re-raised.
        """
        if self._exit_gate is None or self._is_stopped:
            return []

        from fx_ai_trading.services.exit_gate_runner import run_exit_gate

        cfg = self._exit_gate
        return run_exit_gate(
            broker=cfg.broker,
            account_id=cfg.account_id,
            clock=self._clock,
            state_manager=cfg.state_manager,
            exit_policy=cfg.exit_policy,
            price_feed=cfg.price_feed,
            tp=cfg.tp,
            sl=cfg.sl,
            context=cfg.context,
            supervisor=self,
        )

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
