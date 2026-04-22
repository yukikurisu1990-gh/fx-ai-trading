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
      M-1b (post-M-1a): the open side is read from
      ``OpenPositionInfo.side``, which ``StateManager.open_position_details``
      derives from ``orders.direction`` per row.  The runner no longer
      accepts a per-call ``side=`` argument (it was the paper-mode
      long-only fixture from Cycle 6.7c) and ``ExitPolicyService.evaluate``
      receives the per-position side as well.

  E3  M-2 (post-M-1b): pnl_realized is computed at close time from
      ``(result.fill_price - pos.avg_price) * pos.units`` with the sign
      flipped for short positions, and forwarded to
      ``StateManager.on_close``.  This is **gross PnL only — fees,
      spread, swap and any quote-currency conversion are NOT included**;
      net PnL is a separate milestone.  When the broker returns
      ``fill_price=None`` (a known OANDA edge case), ``pnl_realized``
      is left as ``None`` so the close still records but downstream
      aggregates remain ANSI-NULL-aware.

  E4  M-3b (post-M-3a): the price source is now a ``QuoteFeed`` — the
      runner reads ``.price`` from ``quote_feed.get_quote(instrument)``.
      For backward compatibility, ``quote_feed`` also accepts a legacy
      ``Callable[[str], float]``; in that case the runner internally
      wraps it via ``callable_to_quote_feed(fn, clock=clock)`` so the
      consumer logic stays uniform.  Staleness enforcement is **NOT**
      added in M-3b — that lands in M-3c.  No new outcome is introduced
      by this milestone.

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
from fx_ai_trading.domain.price_feed import QuoteFeed, callable_to_quote_feed
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
    quote_feed: QuoteFeed | Callable[[str], float],
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
        quote_feed: ``QuoteFeed`` providing ``get_quote(instrument) -> Quote``.
                    For backward compatibility a legacy
                    ``Callable[[str], float]`` is also accepted and
                    wrapped internally via ``callable_to_quote_feed``;
                    in that case ``Quote.ts`` is synthesized from
                    ``clock.now()`` and ``Quote.source`` defaults to
                    ``"legacy_callable"``.
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

    M-1b note:
        The open-side is now ``pos.side`` (per-position, derived from
        ``orders.direction`` by ``StateManager.open_position_details``).
        The pre-M-1b ``side=`` per-call argument has been removed; both
        ``ExitPolicyService.evaluate`` and the closing ``OrderRequest``
        consume ``pos.side`` directly.
    """
    ctx = context or {}
    now = clock.now()
    positions = state_manager.open_position_details()

    if not positions:
        _log.debug("run_exit_gate(account=%s): no open positions", account_id)
        return []

    # M-3b: normalize a legacy callable to QuoteFeed via the M-3a adapter
    # so the per-position loop reads price uniformly through .get_quote().
    # Discrimination uses the @runtime_checkable QuoteFeed Protocol — a
    # bare lambda has no get_quote and falls into the wrap branch.
    qf: QuoteFeed = (
        quote_feed
        if isinstance(quote_feed, QuoteFeed)
        else callable_to_quote_feed(quote_feed, clock=clock)
    )

    results: list[ExitGateRunResult] = []

    for pos in positions:
        holding_seconds = max(0, int((now - pos.open_time_utc).total_seconds()))
        current_price = qf.get_quote(pos.instrument).price

        decision = exit_policy.evaluate(
            position_id=pos.order_id,
            instrument=pos.instrument,
            side=pos.side,
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
            side=_CLOSE_SIDE[pos.side],
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

        # M-2 (E3): compute gross realized PnL in quote currency.  Units
        # are unsigned by repo convention (direction lives in pos.side),
        # so we apply the long/short sign explicitly.  When the broker
        # could not report a fill price, leave pnl_realized as None
        # rather than fabricate a value — the close itself still records.
        assert pos.units > 0, (
            f"OpenPositionInfo.units must be positive (got {pos.units}); "
            "M-2 PnL math relies on unsigned units."
        )
        if result.fill_price is None:
            pnl_realized: float | None = None
        else:
            sign = 1 if pos.side == "long" else -1
            pnl_realized = (result.fill_price - pos.avg_price) * pos.units * sign

        # Append-only state update (E1, E3).
        state_manager.on_close(
            order_id=pos.order_id,
            instrument=pos.instrument,
            reasons=reasons,
            primary_reason_code=decision.primary_reason or "",
            pnl_realized=pnl_realized,
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
