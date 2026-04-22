"""Exit gate runner — Cycle 6.7c (position close pipeline).

Evaluates all currently-open positions against ExitPolicyService and
closes those where a rule fires.  One call → 0‥N close actions.

Design decisions (Cycle 6.7c):

  L2  order_id is the logical position identity (1 order = 1 position).
      Partial close, scale-in/out, and position_id are Phase 7 scope.

  E1  All close-event DB writes are delegated to ``StateManager.on_close``,
      which performs a single atomic transaction covering positions,
      close_events, and the secondary_sync_outbox.  The exit runner
      calls Broker directly and never writes close_events itself —
      doing so would duplicate the on_close write.

  E2  Broker close order uses the OPPOSITE side of the open position.
      Paper-mode (6.7c): side is always 'long'; Phase 7 derives it from
      the original OrderRequest stored in the orders table.

  E3  pnl_realized is not computed (None).  Phase 7 will derive it from
      fill_price vs avg_price once price data is authoritative.

  E4  Price feed is a plain ``Callable[[str], float]`` — no Protocol
      wrapper in 6.7c.  The caller (Supervisor / test) injects a lambda
      or a named function.

  E5  Context dict is passed through to ExitPolicyService.evaluate()
      unchanged.  Callers may include ``{"emergency_stop": True}`` to
      trigger immediate flat-all.

Append-only: StateManager.on_close() only inserts rows.  This runner
never issues UPDATE or DELETE.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from fx_ai_trading.common.clock import Clock
from fx_ai_trading.common.exceptions import AccountTypeMismatchRuntime
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.domain.broker import Broker, OrderRequest
from fx_ai_trading.services.exit_policy import ExitPolicyService
from fx_ai_trading.services.state_manager import StateManager

if TYPE_CHECKING:
    from fx_ai_trading.supervisor.supervisor import Supervisor

_log = logging.getLogger(__name__)

# Closing side is always the opposite of the open side.
_CLOSE_SIDE: dict[str, str] = {"long": "short", "short": "long"}


# ---------------------------------------------------------------------------
# Result DTO
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExitGateRunResult:
    """Outcome for one position evaluated by ``run_exit_gate``.

    outcome:
      'noop'            — ExitPolicy did not fire; position held.
      'closed'          — Broker accepted close; on_close written.
      'broker_rejected' — Broker returned non-filled; no state change.
    """

    instrument: str
    order_id: str
    outcome: str
    primary_reason: str | None = None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_exit_gate(
    *,
    broker: Broker,
    account_id: str,
    clock: Clock,
    state_manager: StateManager,
    exit_policy: ExitPolicyService,
    price_feed: Callable[[str], float],
    side: str = "long",
    tp: float | None = None,
    sl: float | None = None,
    context: dict[str, Any] | None = None,
    supervisor: Supervisor | None = None,
) -> list[ExitGateRunResult]:
    """Evaluate all open positions and close those where ExitPolicy fires.

    Reads open positions from ``StateManager.open_position_details()``,
    calls ``ExitPolicyService.evaluate()`` for each, and — when
    ``should_exit`` is True — places a closing order via Broker and
    appends state via ``StateManager.on_close()``.

    Args:
        broker: Paper or mock Broker implementation.
        account_id: Account scope (must match state_manager.account_id).
        clock: Injected time source.
        state_manager: Authoritative positions source and write path.
        exit_policy: Configured ExitPolicyService instance.
        price_feed: ``instrument → current_price`` callable.
        side: Open position side. Paper-mode long-only (E2).
              Phase 7 will derive this from the orders table.
        tp: Take-profit level; None disables TP rule (paper-mode).
        sl: Stop-loss level; None disables SL rule (paper-mode).
        context: Passed to ExitPolicyService.evaluate() unchanged.
                 Pass ``{"emergency_stop": True}`` for M22 flat-all.
        supervisor: Optional Supervisor for safe_stop wiring (PR-5 / U-2).
                    When provided, an ``AccountTypeMismatchRuntime`` raised
                    inside ``broker.place_order`` triggers
                    ``supervisor.trigger_safe_stop`` with the canonical
                    reason ``"account_type_mismatch_runtime"`` (per
                    phase6_hardening §6.18 / operations F14) before the
                    exception propagates.  The for-loop is then aborted
                    without writing the close_event or invoking
                    ``state_manager.on_close`` for that position.  When
                    None, behaviour is unchanged from pre-PR-5.

    Returns:
        One ``ExitGateRunResult`` per open position evaluated.
        Empty list when no positions are open.
    """
    ctx = context or {}
    now = clock.now()
    positions = state_manager.open_position_details()

    if not positions:
        _log.debug("run_exit_gate(account=%s): no open positions", account_id)
        return []

    results: list[ExitGateRunResult] = []

    for pos in positions:
        holding_seconds = max(0, int((now - pos.open_time_utc).total_seconds()))
        current_price = price_feed(pos.instrument)

        decision = exit_policy.evaluate(
            position_id=pos.order_id,
            instrument=pos.instrument,
            side=side,
            current_price=current_price,
            tp=tp,
            sl=sl,
            holding_seconds=holding_seconds,
            context=ctx,
        )

        if not decision.should_exit:
            _log.debug(
                "run_exit_gate: hold %s order=%s holding=%ds",
                pos.instrument,
                pos.order_id,
                holding_seconds,
            )
            results.append(
                ExitGateRunResult(
                    instrument=pos.instrument,
                    order_id=pos.order_id,
                    outcome="noop",
                )
            )
            continue

        # Build D1-format reasons list for on_close.
        reasons = [
            {"priority": i + 1, "reason_code": r, "detail": ""}
            for i, r in enumerate(decision.reasons)
        ]

        close_request = OrderRequest(
            client_order_id=generate_ulid(),
            account_id=account_id,
            instrument=pos.instrument,
            side=_CLOSE_SIDE[side],
            size_units=pos.units,
        )
        try:
            result = broker.place_order(close_request)
        except AccountTypeMismatchRuntime as exc:
            # PR-5 (U-2): Mid-flight account_type drift detected by the
            # broker's pre-place_order assertion (Decision 2.6.1-1).  Per
            # phase6_hardening §6.18 / operations F14, this MUST trigger
            # safe_stop(reason=account_type_mismatch_runtime) and write
            # NO close_event / NO state_manager.on_close row for this
            # position.  We fire the wired Supervisor (if any) and then
            # re-raise so the for-loop aborts and any remaining positions
            # are NOT evaluated against the now-untrusted broker.
            #
            # ``expected_account_type`` is None here because run_exit_gate
            # has no per-call expected value (unlike run_execution_gate);
            # the mismatch text is fully captured in ``detail`` (str(exc)).
            if supervisor is not None:
                payload = {
                    "actual_account_type": broker.account_type,
                    "expected_account_type": None,
                    "instrument": pos.instrument,
                    "client_order_id": close_request.client_order_id,
                    "detail": str(exc),
                }
                # Never let a downstream safe_stop bug swallow the
                # original mismatch exception.
                with contextlib.suppress(Exception):
                    supervisor.trigger_safe_stop(
                        reason="account_type_mismatch_runtime",
                        occurred_at=now,
                        payload=payload,
                    )
            raise

        if result.status != "filled":
            _log.warning(
                "run_exit_gate: broker rejected close for %s order=%s status=%s",
                pos.instrument,
                pos.order_id,
                result.status,
            )
            results.append(
                ExitGateRunResult(
                    instrument=pos.instrument,
                    order_id=pos.order_id,
                    outcome="broker_rejected",
                    primary_reason=decision.primary_reason,
                )
            )
            continue

        # Append-only state update (E1, E3).
        state_manager.on_close(
            order_id=pos.order_id,
            instrument=pos.instrument,
            reasons=reasons,
            primary_reason_code=decision.primary_reason or "",
            pnl_realized=None,
        )
        _log.info(
            "run_exit_gate: closed %s order=%s reason=%s holding=%ds",
            pos.instrument,
            pos.order_id,
            decision.primary_reason,
            holding_seconds,
        )
        results.append(
            ExitGateRunResult(
                instrument=pos.instrument,
                order_id=pos.order_id,
                outcome="closed",
                primary_reason=decision.primary_reason,
            )
        )

    return results


__all__ = ["ExitGateRunResult", "run_exit_gate"]
