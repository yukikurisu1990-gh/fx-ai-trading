"""StateManager — Phase 6 Cycle 6.7a (read-only snapshot source).

Responsibility (6.7a scope):
  Provide a single read-only query surface that replaces the
  Execution Gate's ad-hoc helpers (``_fetch_open_instruments`` and
  ``_count_recent_failures``).  Write paths (positions /
  close_events / risk_events / app_runtime_state) are deliberately
  out of scope — they land in 6.7b and 6.7c.

Design decisions frozen in Cycle 6.7 design (see design report):
  L1  Recent execution failures are defined in terms of
      ``order_transactions.transaction_type`` — broker-origin only.
      The set ``{ORDER_REJECT, ORDER_TIMEOUT}`` is authoritative;
      ``ORDER_EXPIRED`` (TTL elapsed before broker contact) and the
      Risk-blocked ``orders(CANCELED)`` rows (which never produce
      an order_transactions row at all) do NOT count.  This is the
      only semantic change 6.7a introduces; 6.7b will reconfirm.
  L2  ``order_id`` is the logical position identity; 6.7a does not
      need it because it operates at the instrument-set granularity.
  L5  Concrete class — no Protocol until a second implementation is
      actually required.
  L7  The caller (Supervisor / test harness) is expected to build a
      single instance per run and share it across Risk + Execution.
      Instances are cheap; they hold only the engine and account_id.

Invariants:
  - Never writes.  Every method is read-only by construction.
  - Every query filters by ``account_id``.  Snapshots from different
    accounts are fully isolated.
  - ``snapshot()`` returns a ``StateSnapshot`` DTO carrying three
    values captured in a single logical read.  Callers should prefer
    this over calling the individual methods if they need more than
    one value, since the convenience helpers re-issue queries.
  - M10 paper-mode: ``open_instruments`` currently derives from
    ``orders.status='FILLED'`` (the same semantics the deprecated
    Execution Gate helper used).  6.7b replaces the source with the
    ``positions`` timeline once the write path exists.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Engine

from fx_ai_trading.domain.state import StateSnapshot

_log = logging.getLogger(__name__)

# L1 (design-frozen): broker-origin execution failures only.  This set
# is the authoritative definition for Cycle 6.7a and must be updated
# through a follow-up design freeze — not silently.
_BROKER_FAILURE_TRANSACTION_TYPES: frozenset[str] = frozenset({"ORDER_REJECT", "ORDER_TIMEOUT"})


class StateManager:
    """Read-only snapshot source for Risk and Execution.

    Args:
        engine: SQLAlchemy Engine bound to the primary DB.
        account_id: The account whose state we are reading.  All
                    queries filter by this value, so snapshots across
                    accounts never mix.

    Notes:
        Instances are pure adapters — they hold no mutable state and
        are safe to share across threads as long as the underlying
        engine is.  Each method issues its own short-lived connection;
        callers needing consistent multi-value reads should prefer
        ``snapshot()`` which groups the three values into one call.
    """

    def __init__(self, engine: Engine, *, account_id: str) -> None:
        self._engine = engine
        self._account_id = account_id

    @property
    def account_id(self) -> str:
        return self._account_id

    # ------------------------------------------------------------------
    # Aggregate read
    # ------------------------------------------------------------------

    def snapshot(
        self,
        *,
        now: datetime,
        cooloff_window_seconds: int,
    ) -> StateSnapshot:
        """Return a point-in-time read of the three runtime views.

        ``concurrent_count`` is intentionally equal to
        ``len(open_instruments)`` in 6.7a (paper-mode assumption:
        one instrument = one open position).  6.7b will split this
        once the positions timeline becomes the authoritative source.
        """
        open_instruments = self.open_instruments()
        recent_failures = self.recent_execution_failures_within(
            now=now, window_seconds=cooloff_window_seconds
        )
        snap = StateSnapshot(
            open_instruments=open_instruments,
            concurrent_count=len(open_instruments),
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
    # Individual reads (available for callers that need only one value)
    # ------------------------------------------------------------------

    def open_instruments(self) -> frozenset[str]:
        """Instruments currently considered held open for this account.

        6.7a derivation (paper-mode shortcut, preserved from the
        Execution Gate helper): ``orders.status='FILLED'``.  6.7b will
        switch this to the ``positions`` timeline projection.
        """
        sql = text(
            """
            SELECT DISTINCT instrument
            FROM orders
            WHERE status = 'FILLED'
              AND account_id = :account_id
            """
        )
        with self._engine.connect() as conn:
            rows = conn.execute(sql, {"account_id": self._account_id}).fetchall()
        return frozenset(r.instrument for r in rows)

    def recent_execution_failures_within(
        self,
        *,
        now: datetime,
        window_seconds: int,
    ) -> int:
        """Count broker-origin execution failures in the given window.

        Per L1, a failure is an ``order_transactions`` row whose
        ``transaction_type`` is in ``_BROKER_FAILURE_TRANSACTION_TYPES``
        (``ORDER_REJECT`` or ``ORDER_TIMEOUT``).  Rows with
        ``ORDER_EXPIRED`` or the success types are excluded; Risk-
        blocked flows write no order_transactions row at all and are
        therefore naturally excluded.
        """
        if window_seconds <= 0:
            return 0

        cutoff = now - timedelta(seconds=window_seconds)
        # SQLite stores timestamps as strings in the test fixture; we
        # filter in Python for dialect-agnosticism.  The IN-list uses
        # SQLAlchemy's expanding bindparam so the query is safe
        # regardless of how many failure types are registered.
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
            ts = _coerce_datetime(r.transaction_time_utc)
            if ts >= cutoff:
                count += 1
        return count


def _coerce_datetime(value: object) -> datetime:
    """SQLite yields str for timestamp columns; Postgres yields datetime."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


__all__ = ["StateManager"]
