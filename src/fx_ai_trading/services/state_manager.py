"""StateManager — Phase 6 Cycle 6.7a/b/c (snapshot source + write path).

Cycle 6.7a added the read-only surface (snapshot / open_instruments /
recent_execution_failures_within).  Cycle 6.7b adds the write path:

  on_fill(order_id, instrument, units, avg_price, ...)
    Writes one ``positions`` row (event_type='open' when the instrument
    is not already held, 'add' if it is).  This is the M10 paper-mode
    equivalent of "position opened" — each filled order opens or adds
    to a position, never modifies an existing row.

  on_close(order_id, instrument, reasons, primary_reason_code, ...)
    Writes one ``positions`` row (event_type='close', units=0) and one
    ``close_events`` row.  Both are linked via position_snapshot_id.
    Cycle 6.7d (I-03): all four writes (positions + close_events + both
    outbox rows) share a single transaction so a partial failure cannot
    leave domain and outbox state divergent.

  on_risk_verdict(verdict, cycle_id, instrument, ...)
    Writes one ``risk_events`` row for every accept or reject decision.
    ``constraint_violated`` stores the dotted reason code per L6.

Cycle 6.7c adds:

  open_position_details() -> list[OpenPositionInfo]
    Returns per-position detail for each currently-open instrument.
    Used by run_exit_gate() to evaluate ExitPolicy and call on_close.

  open_instruments() fix (6.7c):
    6.7b query used ``instrument NOT IN (close events)`` which
    permanently hid re-opened instruments.  Fixed to: instrument whose
    MOST RECENT positions event is 'open' or 'add' (window function).

All writes are append-only and mirrored to ``secondary_sync_outbox``
(F-12) in the same call.

Design decisions frozen in the Cycle 6.7 design report:
  L1  Recent failures = ORDER_REJECT + ORDER_TIMEOUT only (broker-origin).
  L2  order_id is the logical position identity.
  L5  Concrete class, no Protocol.
  L6  constraint_violated stores the dotted risk.* reason code.
  L7  Single instance, shared across Risk and Execution by the Supervisor.

Invariants:
  - All reads and writes filter by account_id.
  - No UPDATE or DELETE — every state change is a new INSERT.
  - snapshot() is still the preferred multi-value read; individual
    methods may issue separate queries when only one value is needed.
  - clock injected in __init__; defaults to WallClock() so 6.7a callers
    that pass no clock continue to work without change.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.domain.state import OpenPositionInfo, StateSnapshot
from fx_ai_trading.sync.enqueue import enqueue_secondary_sync

_log = logging.getLogger(__name__)

# L1 (design-frozen): broker-origin execution failures only.
_BROKER_FAILURE_TRANSACTION_TYPES: frozenset[str] = frozenset({"ORDER_REJECT", "ORDER_TIMEOUT"})


def _state_sanitizer(payload: dict[str, Any]) -> dict[str, Any]:
    """F-12 sanitizer for StateManager writes.  No secrets; shallow copy."""
    return dict(payload)


class StateManager:
    """Runtime state source and write path for Risk and Execution.

    Args:
        engine: SQLAlchemy Engine bound to the primary DB.
        account_id: Account scope for all reads and writes.
        clock: Time source used for event timestamps and outbox enqueueing.
               Defaults to WallClock() — callers that do not inject a clock
               (e.g. existing Cycle 6.7a tests) are unaffected.
    """

    def __init__(
        self,
        engine: Engine,
        *,
        account_id: str,
        clock: Clock | None = None,
    ) -> None:
        self._engine = engine
        self._account_id = account_id
        self._clock: Clock = clock if clock is not None else WallClock()

    @property
    def account_id(self) -> str:
        return self._account_id

    # ------------------------------------------------------------------
    # Aggregate read (unchanged from 6.7a)
    # ------------------------------------------------------------------

    def snapshot(
        self,
        *,
        now: datetime,
        cooloff_window_seconds: int,
    ) -> StateSnapshot:
        """Point-in-time read of the three runtime views."""
        open_instr = self.open_instruments()
        recent_failures = self.recent_execution_failures_within(
            now=now, window_seconds=cooloff_window_seconds
        )
        snap = StateSnapshot(
            open_instruments=open_instr,
            concurrent_count=len(open_instr),
            recent_failure_count=recent_failures,
            snapshot_time_utc=now,
        )
        _log.debug(
            "StateManager.snapshot(account=%s): open=%d failures=%d window=%ds",
            self._account_id,
            snap.concurrent_count,
            snap.recent_failure_count,
            cooloff_window_seconds,
        )
        return snap

    # ------------------------------------------------------------------
    # Individual reads
    # ------------------------------------------------------------------

    def open_instruments(self) -> frozenset[str]:
        """Instruments currently held open for this account.

        Cycle 6.12 fix (R-1, 方針 B): order-independent.  The 6.7c version
        ranked rows by ``event_time_utc DESC, position_snapshot_id DESC``
        and treated the top row as "current state".  At same-millisecond
        ties the ULID lex order decided the result, which non-deterministically
        leaked closed instruments back into the open set.

        The append-only timeline guarantees that an instrument is currently
        held iff its open|add events outnumber its close events.  This count
        comparison needs no row ordering and is therefore deterministic
        regardless of timestamp granularity or ULID suffix entropy.
        """
        sql = text(
            """
            SELECT instrument
            FROM positions
            WHERE account_id = :account_id
            GROUP BY instrument
            HAVING SUM(CASE WHEN event_type IN ('open', 'add') THEN 1 ELSE 0 END) >
                   SUM(CASE WHEN event_type = 'close' THEN 1 ELSE 0 END)
            """
        )
        with self._engine.connect() as conn:
            rows = conn.execute(sql, {"account_id": self._account_id}).fetchall()
        return frozenset(r.instrument for r in rows)

    def open_position_details(self) -> list[OpenPositionInfo]:
        """Details of all currently-open positions for this account.

        Returns one ``OpenPositionInfo`` per open instrument, carrying the
        data that ``run_exit_gate`` needs to evaluate ExitPolicy.

        Cycle 6.7c constraint (L2): 1 order = 1 position.  Each active
        position has exactly one ``event_type='open'`` row in the timeline
        (paper-mode does not pyramid).  An open row is "still active" iff
        no close row exists for the same order_id.

        Cycle 6.12 fix (R-1, 方針 B): selects the open row directly via
        ``NOT EXISTS (close for same order_id)``, which is order-independent.
        The previous window-function ranking depended on
        ``position_snapshot_id`` lex order at same-millisecond ties and
        could leak closed positions into the exit gate.

        Pyramiding (add rows) is paper-mode out of scope; if it lands later,
        units/avg_price aggregation across (open, add*) per order_id will
        require a separate change.
        """
        sql = text(
            """
            SELECT p.instrument, p.order_id, p.units, p.avg_price, p.event_time_utc
            FROM positions p
            WHERE p.account_id = :account_id
              AND p.event_type = 'open'
              AND NOT EXISTS (
                  SELECT 1 FROM positions c
                  WHERE c.account_id = p.account_id
                    AND c.order_id = p.order_id
                    AND c.event_type = 'close'
              )
            ORDER BY p.event_time_utc ASC
            """
        )
        with self._engine.connect() as conn:
            rows = conn.execute(sql, {"account_id": self._account_id}).fetchall()
        return [
            OpenPositionInfo(
                instrument=r.instrument,
                order_id=r.order_id,
                units=int(r.units),
                avg_price=float(r.avg_price),
                open_time_utc=_coerce_datetime(r.event_time_utc),
            )
            for r in rows
        ]

    def recent_execution_failures_within(
        self,
        *,
        now: datetime,
        window_seconds: int,
    ) -> int:
        """Count broker-origin execution failures in the given window (L1)."""
        if window_seconds <= 0:
            return 0

        cutoff = now - timedelta(seconds=window_seconds)
        sql = text(
            """
            SELECT transaction_time_utc
            FROM order_transactions
            WHERE account_id = :account_id
              AND transaction_type IN :failure_types
            """
        ).bindparams(bindparam("failure_types", expanding=True))
        with self._engine.connect() as conn:
            rows = conn.execute(
                sql,
                {
                    "account_id": self._account_id,
                    "failure_types": list(_BROKER_FAILURE_TRANSACTION_TYPES),
                },
            ).fetchall()

        count = 0
        for r in rows:
            if _coerce_datetime(r.transaction_time_utc) >= cutoff:
                count += 1
        return count

    # ------------------------------------------------------------------
    # Write path (6.7b)
    # ------------------------------------------------------------------

    def on_fill(
        self,
        *,
        order_id: str,
        instrument: str,
        units: int,
        avg_price: float,
        correlation_id: str | None = None,
        cycle_id: str | None = None,
        strategy_id: str | None = None,
    ) -> str:
        """Record a broker fill by appending to the positions timeline.

        event_type is 'add' when the instrument is already open for this
        account (pyramiding), 'open' otherwise.  The distinction matters
        for on_close: it must close ALL open events for the position.

        Returns the generated ``position_snapshot_id``.
        """
        now = self._clock.now()
        existing = self.open_instruments()
        event_type = "add" if instrument in existing else "open"

        psid = generate_ulid()
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO positions (
                        position_snapshot_id, order_id, account_id, instrument,
                        event_type, units, avg_price, unrealized_pl, realized_pl,
                        event_time_utc, correlation_id
                    ) VALUES (
                        :psid, :order_id, :account_id, :instrument,
                        :event_type, :units, :avg_price, NULL, NULL,
                        :event_time_utc, :correlation_id
                    )
                    """
                ),
                {
                    "psid": psid,
                    "order_id": order_id,
                    "account_id": self._account_id,
                    "instrument": instrument,
                    "event_type": event_type,
                    "units": units,
                    "avg_price": avg_price,
                    "event_time_utc": now.isoformat(),
                    "correlation_id": correlation_id,
                },
            )
        enqueue_secondary_sync(
            self._engine,
            table_name="positions",
            primary_key=json.dumps([psid]),
            version_no=0,
            payload={
                "position_snapshot_id": psid,
                "order_id": order_id,
                "account_id": self._account_id,
                "instrument": instrument,
                "event_type": event_type,
                "units": units,
                "avg_price": avg_price,
                "event_time_utc": now.isoformat(),
                "correlation_id": correlation_id,
                "cycle_id": cycle_id,
                "strategy_id": strategy_id,
            },
            sanitizer=_state_sanitizer,
            clock=self._clock,
        )
        _log.debug(
            "StateManager.on_fill: psid=%s instrument=%s event_type=%s units=%d",
            psid,
            instrument,
            event_type,
            units,
        )
        return psid

    def on_close(
        self,
        *,
        order_id: str,
        instrument: str,
        reasons: list[dict[str, Any]],
        primary_reason_code: str,
        pnl_realized: float | None = None,
        correlation_id: str | None = None,
    ) -> tuple[str, str]:
        """Record a position close.

        Appends one positions row (event_type='close', units=0) and one
        close_events row linked via position_snapshot_id.  Both rows are
        mirrored to secondary_sync_outbox.

        Args:
            reasons: List of exit-reason dicts in D1 format:
                     [{priority, reason_code, detail}, ...].
                     Must not be empty.

        Returns:
            Tuple (position_snapshot_id, close_event_id).
        """
        now = self._clock.now()

        # Link to the most recent open/add snapshot for this order.  Read
        # before the write transaction — no atomicity requirement with the
        # close row (L7: single StateManager instance, no concurrent closes).
        last_psid = self._last_open_snapshot_id(order_id=order_id, instrument=instrument)

        psid = generate_ulid()
        ceid = generate_ulid()

        # I-03 (Cycle 6.7d): all four writes — positions close row,
        # positions outbox row, close_events row, close_events outbox row —
        # share one transaction.  A failure in any step rolls back the
        # earlier ones, so domain and outbox state cannot diverge.
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO positions (
                        position_snapshot_id, order_id, account_id, instrument,
                        event_type, units, avg_price, unrealized_pl, realized_pl,
                        event_time_utc, correlation_id
                    ) VALUES (
                        :psid, :order_id, :account_id, :instrument,
                        'close', 0, NULL, NULL, :realized_pl,
                        :event_time_utc, :correlation_id
                    )
                    """
                ),
                {
                    "psid": psid,
                    "order_id": order_id,
                    "account_id": self._account_id,
                    "instrument": instrument,
                    "realized_pl": pnl_realized,
                    "event_time_utc": now.isoformat(),
                    "correlation_id": correlation_id,
                },
            )
            enqueue_secondary_sync(
                self._engine,
                conn=conn,
                table_name="positions",
                primary_key=json.dumps([psid]),
                version_no=0,
                payload={
                    "position_snapshot_id": psid,
                    "order_id": order_id,
                    "account_id": self._account_id,
                    "instrument": instrument,
                    "event_type": "close",
                    "units": 0,
                    "realized_pl": pnl_realized,
                    "event_time_utc": now.isoformat(),
                    "correlation_id": correlation_id,
                },
                sanitizer=_state_sanitizer,
                clock=self._clock,
            )
            conn.execute(
                text(
                    """
                    INSERT INTO close_events (
                        close_event_id, order_id, position_snapshot_id,
                        reasons, primary_reason_code,
                        closed_at, pnl_realized, correlation_id
                    ) VALUES (
                        :ceid, :order_id, :psid_link,
                        :reasons, :primary_reason_code,
                        :closed_at, :pnl_realized, :correlation_id
                    )
                    """
                ),
                {
                    "ceid": ceid,
                    "order_id": order_id,
                    "psid_link": last_psid,
                    "reasons": json.dumps(reasons, ensure_ascii=False, sort_keys=True),
                    "primary_reason_code": primary_reason_code,
                    "closed_at": now.isoformat(),
                    "pnl_realized": pnl_realized,
                    "correlation_id": correlation_id,
                },
            )
            enqueue_secondary_sync(
                self._engine,
                conn=conn,
                table_name="close_events",
                primary_key=json.dumps([ceid]),
                version_no=0,
                payload={
                    "close_event_id": ceid,
                    "order_id": order_id,
                    "position_snapshot_id": last_psid,
                    "reasons": reasons,
                    "primary_reason_code": primary_reason_code,
                    "closed_at": now.isoformat(),
                    "pnl_realized": pnl_realized,
                    "correlation_id": correlation_id,
                },
                sanitizer=_state_sanitizer,
                clock=self._clock,
            )
        _log.debug(
            "StateManager.on_close: ceid=%s psid=%s order=%s instrument=%s reason=%s",
            ceid,
            psid,
            order_id,
            instrument,
            primary_reason_code,
        )
        return psid, ceid

    def on_risk_verdict(
        self,
        *,
        verdict: str,
        cycle_id: str | None = None,
        instrument: str | None = None,
        strategy_id: str | None = None,
        constraint_violated: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> str:
        """Record a Risk accept/reject decision in risk_events.

        Per L6, ``constraint_violated`` stores the dotted risk.* reason
        code (e.g. 'risk.max_open_positions').  Accepted verdicts have
        constraint_violated=None.

        Returns the generated ``risk_event_id``.
        """
        now = self._clock.now()
        reid = generate_ulid()
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO risk_events (
                        risk_event_id, cycle_id, instrument, strategy_id,
                        verdict, constraint_violated, detail, event_time_utc
                    ) VALUES (
                        :reid, :cycle_id, :instrument, :strategy_id,
                        :verdict, :constraint_violated, :detail, :event_time_utc
                    )
                    """
                ),
                {
                    "reid": reid,
                    "cycle_id": cycle_id,
                    "instrument": instrument,
                    "strategy_id": strategy_id,
                    "verdict": verdict,
                    "constraint_violated": constraint_violated,
                    "detail": json.dumps(detail, ensure_ascii=False, sort_keys=True)
                    if detail
                    else None,
                    "event_time_utc": now.isoformat(),
                },
            )
        enqueue_secondary_sync(
            self._engine,
            table_name="risk_events",
            primary_key=json.dumps([reid]),
            version_no=0,
            payload={
                "risk_event_id": reid,
                "cycle_id": cycle_id,
                "instrument": instrument,
                "strategy_id": strategy_id,
                "verdict": verdict,
                "constraint_violated": constraint_violated,
                "detail": detail,
                "event_time_utc": now.isoformat(),
            },
            sanitizer=_state_sanitizer,
            clock=self._clock,
        )
        _log.debug(
            "StateManager.on_risk_verdict: reid=%s verdict=%s constraint=%s",
            reid,
            verdict,
            constraint_violated,
        )
        return reid

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _last_open_snapshot_id(self, *, order_id: str, instrument: str) -> str | None:
        """Return the position_snapshot_id of the 'open' row for this order.

        Cycle 6.12 fix (R-1, 方針 B): returns the unique 'open' row for
        (account_id, order_id, instrument) — under L2 (1 order = 1 position)
        each order_id has exactly one 'open' row, so no row ordering is
        required.  Used by ``on_close`` to populate
        ``close_events.position_snapshot_id`` as the audit link back to the
        position's identity event.

        The previous version ordered by ``event_time_utc DESC,
        position_snapshot_id DESC`` to pick the latest 'open' or 'add' row,
        which under same-millisecond ties depended on ULID lex order.
        Because paper-mode does not pyramid, the new query is identity-
        equivalent in practice; for hypothetical future pyramiding the
        link target is the original open row, which remains the most
        stable audit anchor.
        """
        sql = text(
            """
            SELECT position_snapshot_id
            FROM positions
            WHERE account_id = :account_id
              AND order_id = :order_id
              AND instrument = :instrument
              AND event_type = 'open'
            LIMIT 1
            """
        )
        with self._engine.connect() as conn:
            row = conn.execute(
                sql,
                {
                    "account_id": self._account_id,
                    "order_id": order_id,
                    "instrument": instrument,
                },
            ).fetchone()
        return row.position_snapshot_id if row else None


def _coerce_datetime(value: object) -> datetime:
    """SQLite yields str for timestamp columns; Postgres yields datetime."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


__all__ = ["StateManager", "OpenPositionInfo"]
