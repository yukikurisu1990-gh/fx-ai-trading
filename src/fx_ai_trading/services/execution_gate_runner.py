"""Execution gate runner — Phase 6 Cycle 6.5 + 6.6 Risk + 6.7a/b StateManager.

Closes the minimum viable path from ``trading_signals`` to a persisted
broker round-trip.  One call, one trading_signal, one outcome.

Pipeline (Cycle 6.6):

  1. SELECT one ``trading_signals`` row for which no ``orders`` row
     exists yet (the "unprocessed" queue, ordered by signal_time).
     No row → ``noop``, no writes, no broker contact.
  2. Hard paper-fixed guard:
       a. ``expected_account_type`` must equal ``"demo"`` (Iteration 1
          §10 constraint).
       b. ``broker.account_type`` must match.
       c. PaperBroker's own ``_verify_account_type_or_raise`` fires
          as a third independent check inside ``place_order``.
  3. TTL check: if ``now - signal_time_utc > ttl_seconds`` the signal
     is expired; we NEVER call the broker in that case.  The orders
     row is written with status=CANCELED and one order_transactions
     row with type=ORDER_EXPIRED is appended.
  4. **Cycle 6.6**: Risk gate (only when ``risk_manager`` is injected).
     a. ``compute_size`` — delegated to PositionSizer.  ``size_units``
        == 0 → blocked (reason_code derived from SizeResult.reason).
     b. ``allow_trade`` — 3 guards (duplicate instrument /
        max_open_positions / recent_execution_failure_cooloff).  First
        failure → blocked (reason_code from AllowTradeResult).
     On blocked we DO write orders (status=CANCELED) + no_trade_events,
     but NEVER order_transactions, and NEVER call the broker.  Outcome
     is ``blocked``.
  5. Otherwise submit an ``OrderRequest`` to the injected ``Broker``.
     - ``OrderResult.status == 'filled'``  → orders status=FILLED,
       two order_transactions rows (ORDER_CREATE + ORDER_FILL).
     - Any other status                    → orders status=CANCELED,
       one order_transactions row (ORDER_REJECT).
     - Broker raises ``TimeoutError``      → orders status=FAILED,
       one order_transactions row (ORDER_TIMEOUT).
  6. Every persisted row is mirrored into ``secondary_sync_outbox``
     via ``enqueue_secondary_sync`` under F-12.

Design choices intentionally deferred to later cycles:
  - No FSM tracking (no PENDING → SUBMITTED → FILLED updates).  The
    orders row is inserted once with its *terminal* status for this
    cycle.  State Manager (later cycle) will own the async transition
    path when OANDA streaming enters the picture.
  - Risk inputs ``account_balance`` / ``risk_pct`` / ``sl_pips`` are
    runner parameters (provisional); State Manager will take over
    balance snapshot + per-strategy SL source in a later cycle.
  - No execution_metrics writes (M12).
  - No retry, no defer, no reconciliation.

Cycle 6.7a/b note:
  The Risk block derives ``open_instruments`` / ``concurrent_positions`` /
  ``recent_failure_count`` from ``StateManager.snapshot()``.  ``state_manager``
  is a required dependency — the Cycle 6.6 backward-compat path that read
  from the ``orders`` table directly was removed in Cycle 6.7d (I-02).

  Cycle 6.7b adds write-path calls:
    - After a broker fill: ``state_manager.on_fill()`` appends a
      positions row before ``_handle_fill`` persists the orders row.
    - After every Risk verdict (compute_size reject, allow_trade
      reject/accept): ``state_manager.on_risk_verdict()`` appends a
      risk_events row.

Runner is a pure function: no loops, no polling, no sleeps.  Callers
drive cadence.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from fx_ai_trading.common.clock import Clock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.domain.broker import Broker, OrderRequest, OrderResult
from fx_ai_trading.domain.risk import Instrument
from fx_ai_trading.sync.enqueue import enqueue_secondary_sync

if TYPE_CHECKING:
    from fx_ai_trading.services.risk_manager import RiskManagerService
    from fx_ai_trading.services.state_manager import StateManager

SOURCE_COMPONENT = "execution_gate_runner"

# Paper-mode is the only account_type permitted in Iteration 1 (§10).
PAPER_ACCOUNT_TYPE = "demo"

# Default cool-off window for Cycle 6.6 recent-failure counting.
_DEFAULT_COOLOFF_WINDOW_SECONDS = 900  # 15 minutes

# --- Domain direction → broker side mapping ---------------------------------
# The DB stores 'buy' / 'sell' on trading_signals.  Broker OrderRequest
# uses the canonical 'long' / 'short' vocabulary (D3 §2.6.1).
_DIRECTION_TO_BROKER_SIDE = {"buy": "long", "sell": "short"}

# --- SizeResult.reason → no_trade reason_code mapping (dotted form) --------
# Cycle 6.6: PositionSizer returns camelcase reasons; execution gate maps
# them onto the risk.* taxonomy when writing no_trade_events.
_SIZE_REASON_TO_CODE = {
    "InvalidSL": "risk.invalid_sl",
    "InvalidRiskPct": "risk.invalid_risk_pct",
    "SizeUnderMin": "risk.size_under_min",
}


# --- F-12 sanitizer ---------------------------------------------------------


def _exec_sanitizer(payload: dict[str, Any]) -> dict[str, Any]:
    """Execution-domain sanitizer.  Order / transaction payloads carry
    no secrets today; we still pass through a sanitizer to honour the
    F-12 contract.  Returns a shallow copy to prevent aliasing."""
    return dict(payload)


# --- Result ------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutionGateRunResult:
    """Outcome of one ``run_execution_gate`` invocation.

    ``outcome`` is one of:
      'noop'      : no unprocessed trading_signal was waiting.
      'filled'    : broker accepted + filled.
      'rejected'  : broker returned non-filled status.
      'expired'   : TTL elapsed before broker was called.
      'timeout'   : broker raised TimeoutError.
      'blocked'   : Risk gate rejected (Cycle 6.6) — broker was NOT called.
    """

    processed: bool
    trading_signal_id: str | None
    order_id: str | None
    order_status: str | None  # 'FILLED' | 'CANCELED' | 'FAILED' | None
    outcome: str
    reject_reason: str | None
    order_transactions_written: int
    no_trade_events_written: int = 0


# --- Internal pending-signal DTO -------------------------------------------


@dataclass(frozen=True)
class _PendingSignal:
    trading_signal_id: str
    meta_decision_id: str
    cycle_id: str
    instrument: str
    strategy_id: str
    signal_direction: str  # 'buy' | 'sell'
    signal_time_utc: datetime
    correlation_id: str | None
    ttl_seconds: int


# --- Public entry point ----------------------------------------------------


def run_execution_gate(
    engine: Engine,
    *,
    broker: Broker,
    account_id: str,
    clock: Clock,
    size_units: int = 1000,
    expected_account_type: str = PAPER_ACCOUNT_TYPE,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    run_id: str | None = None,
    environment: str | None = None,
    code_version: str | None = None,
    config_version: str | None = None,
    # Cycle 6.6 — Risk integration.  All inputs are optional; when
    # ``risk_manager`` is None the runner behaves exactly as Cycle 6.5.
    risk_manager: RiskManagerService | None = None,
    account_balance: float | None = None,
    risk_pct: float | None = None,
    sl_pips: float | None = None,
    instruments: dict[str, Instrument] | None = None,
    cooloff_window_seconds: int = _DEFAULT_COOLOFF_WINDOW_SECONDS,
    # Cycle 6.7a — required StateManager.  Risk reads ``open_instruments`` /
    # ``concurrent_count`` / ``recent_failures`` through
    # ``StateManager.snapshot()``.  Required since Cycle 6.7d (I-02).
    state_manager: StateManager,
) -> ExecutionGateRunResult:
    """Pick one unprocessed trading_signal and drive it through the gate.

    When ``risk_manager`` is provided, the caller MUST also provide
    ``account_balance``, ``risk_pct``, ``sl_pips`` and an ``instruments``
    mapping containing the pending signal's instrument.  Those four
    inputs feed ``compute_size``; ``open_instruments`` /
    ``concurrent_positions`` / ``recent_failure_count`` for
    ``allow_trade`` are derived from the orders table.

    Raises:
      ValueError: if ``expected_account_type`` is not 'demo' or the
                  injected broker's account_type does not match.
                  These are the paper-fixed guards — they run BEFORE
                  any DB read so a misconfigured call cannot enqueue
                  work against a live broker.
                  Also raised if ``risk_manager`` is provided without
                  the matching sizing inputs.
    """
    _assert_paper_mode(broker=broker, expected=expected_account_type)
    if risk_manager is not None:
        _assert_risk_inputs_complete(
            account_balance=account_balance,
            risk_pct=risk_pct,
            sl_pips=sl_pips,
            instruments=instruments,
        )

    san = sanitizer or _exec_sanitizer
    now = clock.now()

    pending = _fetch_next_unprocessed(engine)
    if pending is None:
        return ExecutionGateRunResult(
            processed=False,
            trading_signal_id=None,
            order_id=None,
            order_status=None,
            outcome="noop",
            reject_reason=None,
            order_transactions_written=0,
        )

    signal_age = _compute_signal_age_seconds(pending.signal_time_utc, now)
    order_id = generate_ulid()
    client_order_id = f"{order_id}:{pending.instrument}:{pending.strategy_id}"

    # --- Expired branch: DO NOT call broker --------------------------------
    if signal_age > pending.ttl_seconds:
        _insert_order(
            engine,
            order_id=order_id,
            client_order_id=client_order_id,
            pending=pending,
            account_id=account_id,
            account_type=broker.account_type,
            units=size_units,
            status="CANCELED",
            submitted_at=None,
            filled_at=None,
            canceled_at=now,
            created_at=now,
        )
        _enqueue_order(
            engine,
            order_id=order_id,
            client_order_id=client_order_id,
            pending=pending,
            account_id=account_id,
            account_type=broker.account_type,
            units=size_units,
            status="CANCELED",
            sanitizer=san,
            clock=clock,
            run_id=run_id,
            environment=environment,
            code_version=code_version,
            config_version=config_version,
        )
        txn_count = _insert_transaction(
            engine,
            order_id=order_id,
            account_id=account_id,
            transaction_type="ORDER_EXPIRED",
            transaction_time_utc=now,
            payload={
                "reason": "SignalExpired",
                "signal_age_seconds": signal_age,
                "ttl_seconds": pending.ttl_seconds,
                "correlation_id": pending.correlation_id,
                "trading_signal_id": pending.trading_signal_id,
            },
            sanitizer=san,
            clock=clock,
            run_id=run_id,
            environment=environment,
            code_version=code_version,
            config_version=config_version,
        )
        # Cycle 6.7d (I-01): TTL expiry is also a "did-not-trade" outcome.
        # Record a no_trade_events row alongside the ORDER_EXPIRED txn so
        # operators can query a single table for every non-entry reason.
        _insert_and_enqueue_no_trade_event(
            engine,
            cycle_id=pending.cycle_id,
            meta_decision_id=pending.meta_decision_id,
            reason_category="timeout",
            reason_code="ttl_expired",
            reason_detail=json.dumps(
                {
                    "order_id": order_id,
                    "trading_signal_id": pending.trading_signal_id,
                    "correlation_id": pending.correlation_id,
                    "signal_age_seconds": signal_age,
                    "ttl_seconds": pending.ttl_seconds,
                },
                sort_keys=True,
            ),
            instrument=pending.instrument,
            strategy_id=pending.strategy_id,
            event_time_utc=now,
            sanitizer=san,
            clock=clock,
            run_id=run_id,
            environment=environment,
            code_version=code_version,
            config_version=config_version,
        )
        return ExecutionGateRunResult(
            processed=True,
            trading_signal_id=pending.trading_signal_id,
            order_id=order_id,
            order_status="CANCELED",
            outcome="expired",
            reject_reason="SignalExpired",
            order_transactions_written=txn_count,
            no_trade_events_written=1,
        )

    # --- Cycle 6.6 Risk gate ----------------------------------------------
    # Order of evaluation is fixed: compute_size first, then the 3
    # allow_trade guards (G1 duplicate, G2 max_open, G3 cooloff).  Any
    # block short-circuits: broker is NOT called, no order_transactions
    # are written, and one orders (CANCELED) + one no_trade_events row
    # are persisted with matching ``correlation_id`` / ``cycle_id``.
    effective_units = size_units
    if risk_manager is not None:
        assert instruments is not None  # guarded above
        instrument_ref = instruments.get(pending.instrument)
        if instrument_ref is None:
            raise ValueError(
                f"instruments mapping is missing a reference for "
                f"{pending.instrument!r}; required when risk_manager is set."
            )
        size_result = risk_manager.compute_size(
            account_balance=float(account_balance),  # type: ignore[arg-type]
            risk_pct=float(risk_pct),  # type: ignore[arg-type]
            sl_pips=float(sl_pips),  # type: ignore[arg-type]
            instrument=instrument_ref,
        )
        if size_result.size_units == 0:
            reject_reason = _SIZE_REASON_TO_CODE.get(
                size_result.reason or "", "risk.size_under_min"
            )
            state_manager.on_risk_verdict(
                verdict="reject",
                cycle_id=pending.cycle_id,
                instrument=pending.instrument,
                strategy_id=pending.strategy_id,
                constraint_violated=reject_reason,
                detail={"size_reason": size_result.reason},
            )
            return _handle_risk_blocked(
                engine,
                order_id=order_id,
                client_order_id=client_order_id,
                pending=pending,
                account_id=account_id,
                account_type=broker.account_type,
                units=0,
                reject_reason=reject_reason,
                now=now,
                sanitizer=san,
                clock=clock,
                run_id=run_id,
                environment=environment,
                code_version=code_version,
                config_version=config_version,
            )
        effective_units = size_result.size_units

        snap = state_manager.snapshot(now=now, cooloff_window_seconds=cooloff_window_seconds)
        open_instruments = snap.open_instruments
        concurrent_positions = snap.concurrent_count
        recent_failure_count = snap.recent_failure_count
        allow_result = risk_manager.allow_trade(
            instrument=pending.instrument,
            open_instruments=open_instruments,
            concurrent_positions=concurrent_positions,
            recent_failure_count=recent_failure_count,
        )
        if not allow_result.allowed:
            state_manager.on_risk_verdict(
                verdict="reject",
                cycle_id=pending.cycle_id,
                instrument=pending.instrument,
                strategy_id=pending.strategy_id,
                constraint_violated=allow_result.reject_reason,
            )
            return _handle_risk_blocked(
                engine,
                order_id=order_id,
                client_order_id=client_order_id,
                pending=pending,
                account_id=account_id,
                account_type=broker.account_type,
                units=effective_units,
                reject_reason=allow_result.reject_reason or "risk.unknown",
                now=now,
                sanitizer=san,
                clock=clock,
                run_id=run_id,
                environment=environment,
                code_version=code_version,
                config_version=config_version,
            )

        # Risk passed: log the accept verdict.
        state_manager.on_risk_verdict(
            verdict="accept",
            cycle_id=pending.cycle_id,
            instrument=pending.instrument,
            strategy_id=pending.strategy_id,
            constraint_violated=None,
        )

    # --- Broker call -------------------------------------------------------
    request = OrderRequest(
        client_order_id=client_order_id,
        account_id=account_id,
        instrument=pending.instrument,
        side=_DIRECTION_TO_BROKER_SIDE[pending.signal_direction],
        size_units=effective_units,
        tp=None,
        sl=None,
        expires_at=None,
    )

    try:
        result = broker.place_order(request)
    except TimeoutError as exc:
        return _handle_timeout(
            engine,
            order_id=order_id,
            client_order_id=client_order_id,
            pending=pending,
            account_id=account_id,
            account_type=broker.account_type,
            units=effective_units,
            exc=exc,
            now=now,
            sanitizer=san,
            clock=clock,
            run_id=run_id,
            environment=environment,
            code_version=code_version,
            config_version=config_version,
        )

    if result.status == "filled":
        state_manager.on_fill(
            order_id=order_id,
            instrument=pending.instrument,
            units=effective_units,
            avg_price=float(result.fill_price or 0.0),
            correlation_id=pending.correlation_id,
            cycle_id=pending.cycle_id,
            strategy_id=pending.strategy_id,
        )
        return _handle_fill(
            engine,
            order_id=order_id,
            client_order_id=client_order_id,
            pending=pending,
            account_id=account_id,
            account_type=broker.account_type,
            units=effective_units,
            result=result,
            now=now,
            sanitizer=san,
            clock=clock,
            run_id=run_id,
            environment=environment,
            code_version=code_version,
            config_version=config_version,
        )

    return _handle_reject(
        engine,
        order_id=order_id,
        client_order_id=client_order_id,
        pending=pending,
        account_id=account_id,
        account_type=broker.account_type,
        units=effective_units,
        result=result,
        now=now,
        sanitizer=san,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )


# --- Paper-fixed guard ------------------------------------------------------


def _assert_paper_mode(*, broker: Broker, expected: str) -> None:
    if expected != PAPER_ACCOUNT_TYPE:
        raise ValueError(
            f"expected_account_type must be {PAPER_ACCOUNT_TYPE!r} in Iteration 1; "
            f"got {expected!r}.  Live account wiring is forbidden in Cycle 6.5."
        )
    if broker.account_type != expected:
        raise ValueError(
            f"broker.account_type={broker.account_type!r} does not match "
            f"expected {expected!r}; execution refused."
        )


# --- Selector --------------------------------------------------------------


def _fetch_next_unprocessed(engine: Engine) -> _PendingSignal | None:
    sql = text(
        """
        SELECT ts.trading_signal_id, ts.meta_decision_id, ts.cycle_id,
               ts.instrument, ts.strategy_id, ts.signal_direction,
               ts.signal_time_utc, ts.correlation_id, ts.ttl_seconds
        FROM trading_signals ts
        LEFT JOIN orders o ON o.trading_signal_id = ts.trading_signal_id
        WHERE o.order_id IS NULL
        ORDER BY ts.signal_time_utc ASC, ts.trading_signal_id ASC
        LIMIT 1
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql).fetchone()
    if row is None:
        return None
    return _PendingSignal(
        trading_signal_id=row.trading_signal_id,
        meta_decision_id=row.meta_decision_id,
        cycle_id=row.cycle_id,
        instrument=row.instrument,
        strategy_id=row.strategy_id,
        signal_direction=row.signal_direction,
        signal_time_utc=_coerce_datetime(row.signal_time_utc),
        correlation_id=row.correlation_id,
        ttl_seconds=int(row.ttl_seconds) if row.ttl_seconds is not None else 0,
    )


def _coerce_datetime(value: Any) -> datetime:
    """SQLite returns signal_time_utc as str in tests; PG gives datetime."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _compute_signal_age_seconds(signal_time_utc: datetime, now: datetime) -> float:
    delta: timedelta = now - signal_time_utc
    return delta.total_seconds()


# --- Outcome handlers ------------------------------------------------------


def _handle_fill(
    engine: Engine,
    *,
    order_id: str,
    client_order_id: str,
    pending: _PendingSignal,
    account_id: str,
    account_type: str,
    units: int,
    result: OrderResult,
    now: datetime,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> ExecutionGateRunResult:
    _insert_order(
        engine,
        order_id=order_id,
        client_order_id=client_order_id,
        pending=pending,
        account_id=account_id,
        account_type=account_type,
        units=units,
        status="FILLED",
        submitted_at=now,
        filled_at=now,
        canceled_at=None,
        created_at=now,
    )
    _enqueue_order(
        engine,
        order_id=order_id,
        client_order_id=client_order_id,
        pending=pending,
        account_id=account_id,
        account_type=account_type,
        units=units,
        status="FILLED",
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )
    # Two transactions: CREATE + FILL — matches the minimal broker
    # round-trip that OANDA will produce in practice.
    txn_count = 0
    txn_count += _insert_transaction(
        engine,
        order_id=order_id,
        account_id=account_id,
        transaction_type="ORDER_CREATE",
        transaction_time_utc=now,
        payload={
            "client_order_id": client_order_id,
            "broker_order_id": result.broker_order_id,
            "instrument": pending.instrument,
            "units": units,
            "side": _DIRECTION_TO_BROKER_SIDE[pending.signal_direction],
            "correlation_id": pending.correlation_id,
            "trading_signal_id": pending.trading_signal_id,
        },
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )
    txn_count += _insert_transaction(
        engine,
        order_id=order_id,
        account_id=account_id,
        transaction_type="ORDER_FILL",
        transaction_time_utc=now,
        payload={
            "broker_order_id": result.broker_order_id,
            "filled_units": result.filled_units,
            "fill_price": result.fill_price,
            "message": result.message,
            "correlation_id": pending.correlation_id,
            "trading_signal_id": pending.trading_signal_id,
        },
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )
    return ExecutionGateRunResult(
        processed=True,
        trading_signal_id=pending.trading_signal_id,
        order_id=order_id,
        order_status="FILLED",
        outcome="filled",
        reject_reason=None,
        order_transactions_written=txn_count,
    )


def _handle_reject(
    engine: Engine,
    *,
    order_id: str,
    client_order_id: str,
    pending: _PendingSignal,
    account_id: str,
    account_type: str,
    units: int,
    result: OrderResult,
    now: datetime,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> ExecutionGateRunResult:
    reject_reason = result.message or result.status
    _insert_order(
        engine,
        order_id=order_id,
        client_order_id=client_order_id,
        pending=pending,
        account_id=account_id,
        account_type=account_type,
        units=units,
        status="CANCELED",
        submitted_at=now,
        filled_at=None,
        canceled_at=now,
        created_at=now,
    )
    _enqueue_order(
        engine,
        order_id=order_id,
        client_order_id=client_order_id,
        pending=pending,
        account_id=account_id,
        account_type=account_type,
        units=units,
        status="CANCELED",
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )
    txn_count = _insert_transaction(
        engine,
        order_id=order_id,
        account_id=account_id,
        transaction_type="ORDER_REJECT",
        transaction_time_utc=now,
        payload={
            "broker_order_id": result.broker_order_id,
            "broker_status": result.status,
            "message": result.message,
            "correlation_id": pending.correlation_id,
            "trading_signal_id": pending.trading_signal_id,
        },
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )
    return ExecutionGateRunResult(
        processed=True,
        trading_signal_id=pending.trading_signal_id,
        order_id=order_id,
        order_status="CANCELED",
        outcome="rejected",
        reject_reason=reject_reason,
        order_transactions_written=txn_count,
    )


def _handle_timeout(
    engine: Engine,
    *,
    order_id: str,
    client_order_id: str,
    pending: _PendingSignal,
    account_id: str,
    account_type: str,
    units: int,
    exc: TimeoutError,
    now: datetime,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> ExecutionGateRunResult:
    _insert_order(
        engine,
        order_id=order_id,
        client_order_id=client_order_id,
        pending=pending,
        account_id=account_id,
        account_type=account_type,
        units=units,
        status="FAILED",
        submitted_at=now,
        filled_at=None,
        canceled_at=None,
        created_at=now,
    )
    _enqueue_order(
        engine,
        order_id=order_id,
        client_order_id=client_order_id,
        pending=pending,
        account_id=account_id,
        account_type=account_type,
        units=units,
        status="FAILED",
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )
    message = str(exc) or "broker timeout"
    txn_count = _insert_transaction(
        engine,
        order_id=order_id,
        account_id=account_id,
        transaction_type="ORDER_TIMEOUT",
        transaction_time_utc=now,
        payload={
            "message": message,
            "correlation_id": pending.correlation_id,
            "trading_signal_id": pending.trading_signal_id,
        },
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )
    return ExecutionGateRunResult(
        processed=True,
        trading_signal_id=pending.trading_signal_id,
        order_id=order_id,
        order_status="FAILED",
        outcome="timeout",
        reject_reason=message,
        order_transactions_written=txn_count,
    )


# --- orders INSERT + outbox -------------------------------------------------


def _insert_order(
    engine: Engine,
    *,
    order_id: str,
    client_order_id: str,
    pending: _PendingSignal,
    account_id: str,
    account_type: str,
    units: int,
    status: str,
    submitted_at: datetime | None,
    filled_at: datetime | None,
    canceled_at: datetime | None,
    created_at: datetime,
) -> None:
    """Insert a terminal-state orders row.

    Note: the D1 orders FSM (PENDING → SUBMITTED → FILLED |
    CANCELED | FAILED) is collapsed to a single INSERT here.  Cycle
    6.5 runs synchronously against the paper broker and always knows
    the terminal state at INSERT time — no UPDATE path exists, which
    preserves the append-only invariant.  Real async OANDA cycles
    will introduce the PENDING-first + UPDATE pattern under the State
    Manager.
    """
    sql = text(
        """
        INSERT INTO orders (
            order_id, client_order_id, trading_signal_id, account_id,
            instrument, account_type, order_type, direction, units,
            status, submitted_at, filled_at, canceled_at,
            correlation_id, created_at
        ) VALUES (
            :order_id, :client_order_id, :trading_signal_id, :account_id,
            :instrument, :account_type, :order_type, :direction, :units,
            :status, :submitted_at, :filled_at, :canceled_at,
            :correlation_id, :created_at
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "order_id": order_id,
                "client_order_id": client_order_id,
                "trading_signal_id": pending.trading_signal_id,
                "account_id": account_id,
                "instrument": pending.instrument,
                "account_type": account_type,
                "order_type": "market",
                "direction": pending.signal_direction,
                "units": units,
                "status": status,
                "submitted_at": submitted_at,
                "filled_at": filled_at,
                "canceled_at": canceled_at,
                "correlation_id": pending.correlation_id,
                "created_at": created_at,
            },
        )


def _enqueue_order(
    engine: Engine,
    *,
    order_id: str,
    client_order_id: str,
    pending: _PendingSignal,
    account_id: str,
    account_type: str,
    units: int,
    status: str,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> None:
    payload = {
        "order_id": order_id,
        "client_order_id": client_order_id,
        "trading_signal_id": pending.trading_signal_id,
        "account_id": account_id,
        "instrument": pending.instrument,
        "account_type": account_type,
        "direction": pending.signal_direction,
        "units": units,
        "status": status,
        "correlation_id": pending.correlation_id,
    }
    enqueue_secondary_sync(
        engine,
        table_name="orders",
        primary_key=json.dumps([order_id]),
        version_no=0,
        payload=payload,
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )


# --- order_transactions INSERT + outbox ------------------------------------


def _insert_transaction(
    engine: Engine,
    *,
    order_id: str,
    account_id: str,
    transaction_type: str,
    transaction_time_utc: datetime,
    payload: dict[str, Any],
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> int:
    """Insert one order_transactions row and mirror it to the outbox.

    Cycle 6.8 (I-05): the INSERT and the outbox enqueue share a single
    transaction via the ``conn=`` kwarg added in Cycle 6.7d (I-03).  A
    failure in either step rolls back the other, so order_transactions
    and secondary_sync_outbox cannot diverge.

    Returns 1 for accounting in the caller.
    """
    broker_txn_id = generate_ulid()
    sql = text(
        """
        INSERT INTO order_transactions (
            broker_txn_id, account_id, order_id, transaction_type,
            transaction_time_utc, payload, received_at_utc
        ) VALUES (
            :broker_txn_id, :account_id, :order_id, :transaction_type,
            :transaction_time_utc, :payload, :received_at_utc
        )
        """
    )
    outbox_payload = {
        "broker_txn_id": broker_txn_id,
        "account_id": account_id,
        "order_id": order_id,
        "transaction_type": transaction_type,
        "transaction_time_utc": transaction_time_utc.isoformat(),
        "payload": payload,
        "source_component": SOURCE_COMPONENT,
    }
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "broker_txn_id": broker_txn_id,
                "account_id": account_id,
                "order_id": order_id,
                "transaction_type": transaction_type,
                "transaction_time_utc": transaction_time_utc,
                "payload": json.dumps(payload, ensure_ascii=False, sort_keys=True),
                "received_at_utc": transaction_time_utc,
            },
        )
        enqueue_secondary_sync(
            engine,
            conn=conn,
            table_name="order_transactions",
            primary_key=json.dumps([broker_txn_id, account_id]),
            version_no=0,
            payload=outbox_payload,
            sanitizer=sanitizer,
            clock=clock,
            run_id=run_id,
            environment=environment,
            code_version=code_version,
            config_version=config_version,
        )
    return 1


# --- Cycle 6.6 helpers -----------------------------------------------------


def _assert_risk_inputs_complete(
    *,
    account_balance: float | None,
    risk_pct: float | None,
    sl_pips: float | None,
    instruments: dict[str, Instrument] | None,
) -> None:
    """Fail fast when Risk is enabled but sizing inputs are missing."""
    missing: list[str] = []
    if account_balance is None:
        missing.append("account_balance")
    if risk_pct is None:
        missing.append("risk_pct")
    if sl_pips is None:
        missing.append("sl_pips")
    if instruments is None:
        missing.append("instruments")
    if missing:
        raise ValueError(
            "risk_manager was provided but the following sizing inputs are "
            f"missing: {', '.join(missing)}.  All four are required "
            "(Cycle 6.6 provisional runner params)."
        )


def _handle_risk_blocked(
    engine: Engine,
    *,
    order_id: str,
    client_order_id: str,
    pending: _PendingSignal,
    account_id: str,
    account_type: str,
    units: int,
    reject_reason: str,
    now: datetime,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> ExecutionGateRunResult:
    """Persist a Cycle 6.6 Risk-blocked outcome.

    Writes exactly one orders row (status=CANCELED) and exactly one
    no_trade_events row.  Never writes order_transactions and never
    calls the broker.  Both rows are enqueued to secondary_sync_outbox.
    """
    _insert_order(
        engine,
        order_id=order_id,
        client_order_id=client_order_id,
        pending=pending,
        account_id=account_id,
        account_type=account_type,
        units=units,
        status="CANCELED",
        submitted_at=None,
        filled_at=None,
        canceled_at=now,
        created_at=now,
    )
    _enqueue_order(
        engine,
        order_id=order_id,
        client_order_id=client_order_id,
        pending=pending,
        account_id=account_id,
        account_type=account_type,
        units=units,
        status="CANCELED",
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )
    # Split dotted "risk.<code>" back into category + bare code for
    # no_trade_events storage (matches existing taxonomy layout).
    if "." in reject_reason:
        category, bare_code = reject_reason.split(".", 1)
    else:
        category, bare_code = "risk", reject_reason
    _insert_and_enqueue_no_trade_event(
        engine,
        cycle_id=pending.cycle_id,
        meta_decision_id=pending.meta_decision_id,
        reason_category=category,
        reason_code=bare_code,
        reason_detail=json.dumps(
            {
                "order_id": order_id,
                "trading_signal_id": pending.trading_signal_id,
                "correlation_id": pending.correlation_id,
                "units": units,
            },
            sort_keys=True,
        ),
        instrument=pending.instrument,
        strategy_id=pending.strategy_id,
        event_time_utc=now,
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )
    return ExecutionGateRunResult(
        processed=True,
        trading_signal_id=pending.trading_signal_id,
        order_id=order_id,
        order_status="CANCELED",
        outcome="blocked",
        reject_reason=reject_reason,
        order_transactions_written=0,
        no_trade_events_written=1,
    )


def _insert_and_enqueue_no_trade_event(
    engine: Engine,
    *,
    cycle_id: str,
    meta_decision_id: str,
    reason_category: str,
    reason_code: str,
    reason_detail: str | None,
    instrument: str | None,
    strategy_id: str | None,
    event_time_utc: datetime,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> str:
    no_trade_event_id = generate_ulid()
    sql = text(
        """
        INSERT INTO no_trade_events (
            no_trade_event_id, cycle_id, meta_decision_id,
            reason_category, reason_code, reason_detail,
            source_component, instrument, strategy_id, event_time_utc
        ) VALUES (
            :no_trade_event_id, :cycle_id, :meta_decision_id,
            :reason_category, :reason_code, :reason_detail,
            :source_component, :instrument, :strategy_id, :event_time_utc
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "no_trade_event_id": no_trade_event_id,
                "cycle_id": cycle_id,
                "meta_decision_id": meta_decision_id,
                "reason_category": reason_category,
                "reason_code": reason_code,
                "reason_detail": reason_detail,
                "source_component": SOURCE_COMPONENT,
                "instrument": instrument,
                "strategy_id": strategy_id,
                "event_time_utc": event_time_utc,
            },
        )
    payload = {
        "no_trade_event_id": no_trade_event_id,
        "cycle_id": cycle_id,
        "meta_decision_id": meta_decision_id,
        "reason_category": reason_category,
        "reason_code": reason_code,
        "reason_detail": reason_detail,
        "source_component": SOURCE_COMPONENT,
        "instrument": instrument,
        "strategy_id": strategy_id,
        "event_time_utc": event_time_utc.isoformat(),
    }
    enqueue_secondary_sync(
        engine,
        table_name="no_trade_events",
        primary_key=json.dumps([no_trade_event_id]),
        version_no=0,
        payload=payload,
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )
    return no_trade_event_id


__all__ = [
    "PAPER_ACCOUNT_TYPE",
    "ExecutionGateRunResult",
    "run_execution_gate",
]
