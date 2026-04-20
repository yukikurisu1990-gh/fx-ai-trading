"""Unit tests for run_execution_gate — Phase 6 Cycle 6.5.

Covered in isolation (no strategy/meta chaining — trading_signals rows
are seeded directly so each branch can be exercised):
  - Paper-fixed guard: refuses non-'demo' expected_account_type.
  - Paper-fixed guard: refuses a broker whose account_type ≠ expected.
  - noop: no unprocessed trading_signals → no writes, no broker call.
  - expired: TTL elapsed → orders=CANCELED, 1 ORDER_EXPIRED txn,
             broker NOT called.
  - filled: broker returns 'filled' → orders=FILLED, 2 txns
            (ORDER_CREATE + ORDER_FILL).
  - rejected: broker returns non-'filled' → orders=CANCELED,
              1 ORDER_REJECT txn.
  - timeout: broker raises TimeoutError → orders=FAILED,
             1 ORDER_TIMEOUT txn.
  - append-only: a second call on a fresh signal writes another
                 independent orders row.
  - unprocessed selector: if an orders row already exists for a
                          trading_signal, it is skipped.
  - direction mapping: 'buy' → broker side 'long'; 'sell' → 'short'.
  - outbox mirror: orders row + each order_transactions row
                   appears in secondary_sync_outbox.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.adapters.broker.base import BrokerBase
from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.domain.broker import (
    BrokerOrder,
    BrokerPosition,
    BrokerTransactionEvent,
    CancelResult,
    OrderRequest,
    OrderResult,
)
from fx_ai_trading.services.execution_gate_runner import (
    ExecutionGateRunResult,
    run_execution_gate,
)

_FIXED_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)


# --- SQLite DDL (subset of migrations 0005/0006/0013) ---------------------

_DDL_TRADING_SIGNALS = """
CREATE TABLE trading_signals (
    trading_signal_id TEXT PRIMARY KEY,
    meta_decision_id  TEXT NOT NULL,
    cycle_id          TEXT NOT NULL,
    instrument        TEXT NOT NULL,
    strategy_id       TEXT NOT NULL,
    signal_direction  TEXT NOT NULL,
    signal_time_utc   TEXT NOT NULL,
    correlation_id    TEXT,
    ttl_seconds       INTEGER
)
"""

_DDL_ORDERS = """
CREATE TABLE orders (
    order_id          TEXT PRIMARY KEY,
    client_order_id   TEXT,
    trading_signal_id TEXT,
    account_id        TEXT NOT NULL,
    instrument        TEXT NOT NULL,
    account_type      TEXT NOT NULL,
    order_type        TEXT NOT NULL,
    direction         TEXT NOT NULL,
    units             NUMERIC(18,4) NOT NULL,
    status            TEXT NOT NULL DEFAULT 'PENDING',
    submitted_at      TEXT,
    filled_at         TEXT,
    canceled_at       TEXT,
    correlation_id    TEXT,
    created_at        TEXT NOT NULL
)
"""

_DDL_ORDER_TRANSACTIONS = """
CREATE TABLE order_transactions (
    broker_txn_id       TEXT NOT NULL,
    account_id          TEXT NOT NULL,
    order_id            TEXT,
    transaction_type    TEXT NOT NULL,
    transaction_time_utc TEXT NOT NULL,
    payload             TEXT,
    received_at_utc     TEXT NOT NULL,
    PRIMARY KEY (broker_txn_id, account_id)
)
"""

_DDL_OUTBOX = """
CREATE TABLE secondary_sync_outbox (
    outbox_id       TEXT PRIMARY KEY,
    table_name      TEXT NOT NULL,
    primary_key     TEXT NOT NULL,
    version_no      BIGINT NOT NULL DEFAULT 0,
    payload_json    TEXT NOT NULL,
    enqueued_at     TEXT NOT NULL,
    acked_at        TEXT,
    last_error      TEXT,
    attempt_count   INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TEXT,
    run_id          TEXT,
    environment     TEXT,
    code_version    TEXT,
    config_version  TEXT
)
"""


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL_TRADING_SIGNALS))
        conn.execute(text(_DDL_ORDERS))
        conn.execute(text(_DDL_ORDER_TRANSACTIONS))
        conn.execute(text(_DDL_OUTBOX))
    yield eng
    eng.dispose()


# --- Fake brokers --------------------------------------------------------


class _FakeBroker(BrokerBase):
    """Fake broker that can be programmed to fill / reject / timeout.

    Also records each OrderRequest so tests can assert on the
    translated side / client_order_id fields.
    """

    def __init__(
        self,
        *,
        account_type: str = "demo",
        mode: str = "fill",  # 'fill' | 'reject' | 'timeout'
        status_on_reject: str = "rejected",
        reject_message: str | None = "insufficient margin",
    ) -> None:
        super().__init__(account_type=account_type)
        self.mode = mode
        self.status_on_reject = status_on_reject
        self.reject_message = reject_message
        self.received: list[OrderRequest] = []

    def place_order(self, request: OrderRequest) -> OrderResult:
        self._verify_account_type_or_raise(self._account_type)
        self.received.append(request)
        if self.mode == "timeout":
            raise TimeoutError("broker timed out after 5s")
        if self.mode == "reject":
            return OrderResult(
                client_order_id=request.client_order_id,
                broker_order_id=f"paper-{request.client_order_id}",
                status=self.status_on_reject,
                filled_units=0,
                fill_price=None,
                message=self.reject_message,
            )
        # fill
        return OrderResult(
            client_order_id=request.client_order_id,
            broker_order_id=f"paper-{request.client_order_id}",
            status="filled",
            filled_units=request.size_units,
            fill_price=1.2345,
            message=None,
        )

    def cancel_order(self, order_id: str) -> CancelResult:
        return CancelResult(order_id=order_id, cancelled=True)

    def get_positions(self, account_id: str) -> list[BrokerPosition]:
        return []

    def get_pending_orders(self, account_id: str) -> list[BrokerOrder]:
        return []

    def get_recent_transactions(self, since: str) -> list[BrokerTransactionEvent]:
        return []


# --- Helpers ---------------------------------------------------------------


def _seed_trading_signal(
    engine,
    *,
    trading_signal_id: str,
    cycle_id: str = "cyc-1",
    instrument: str = "EURUSD",
    strategy_id: str = "stub.deterministic_trend.v1",
    direction: str = "buy",
    signal_time_utc: datetime | None = None,
    ttl_seconds: int = 60,
    correlation_id: str | None = "chain-XYZ",
    meta_decision_id: str = "md-1",
) -> None:
    ts = (signal_time_utc or _FIXED_NOW).isoformat()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO trading_signals (
                    trading_signal_id, meta_decision_id, cycle_id, instrument,
                    strategy_id, signal_direction, signal_time_utc,
                    correlation_id, ttl_seconds
                ) VALUES (
                    :trading_signal_id, :meta_decision_id, :cycle_id, :instrument,
                    :strategy_id, :direction, :signal_time_utc,
                    :correlation_id, :ttl_seconds
                )
                """
            ),
            {
                "trading_signal_id": trading_signal_id,
                "meta_decision_id": meta_decision_id,
                "cycle_id": cycle_id,
                "instrument": instrument,
                "strategy_id": strategy_id,
                "direction": direction,
                "signal_time_utc": ts,
                "correlation_id": correlation_id,
                "ttl_seconds": ttl_seconds,
            },
        )


def _count(engine, table: str, where: str = "1=1") -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT count(*) FROM {table} WHERE {where}")).scalar()


# --- Paper-fixed guard ----------------------------------------------------


class TestPaperFixedGuard:
    def test_expected_account_type_must_be_demo(self, engine) -> None:
        b = _FakeBroker(account_type="demo")
        with pytest.raises(ValueError, match="expected_account_type must be 'demo'"):
            run_execution_gate(
                engine,
                broker=b,
                account_id="acc-1",
                clock=FixedClock(_FIXED_NOW),
                expected_account_type="live",
            )

    def test_broker_account_type_must_match_expected(self, engine) -> None:
        b = _FakeBroker(account_type="live")
        with pytest.raises(ValueError, match="does not match expected"):
            run_execution_gate(
                engine,
                broker=b,
                account_id="acc-1",
                clock=FixedClock(_FIXED_NOW),
            )

    def test_guards_run_before_any_db_read(self, engine) -> None:
        """Guard must fire even when trading_signals table is empty —
        i.e. before the selector query."""
        b = _FakeBroker(account_type="live")
        with pytest.raises(ValueError):
            run_execution_gate(
                engine,
                broker=b,
                account_id="acc-1",
                clock=FixedClock(_FIXED_NOW),
            )
        # Nothing written.
        assert _count(engine, "orders") == 0
        assert _count(engine, "order_transactions") == 0


# --- noop ------------------------------------------------------------------


class TestNoop:
    def test_no_unprocessed_signal_returns_noop(self, engine) -> None:
        b = _FakeBroker()
        r = run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert isinstance(r, ExecutionGateRunResult)
        assert r.processed is False
        assert r.outcome == "noop"
        assert r.order_id is None
        assert _count(engine, "orders") == 0
        assert _count(engine, "order_transactions") == 0
        assert b.received == []


# --- Filled (happy path) --------------------------------------------------


class TestFilledPath:
    def test_broker_fill_writes_order_and_two_transactions(self, engine) -> None:
        _seed_trading_signal(engine, trading_signal_id="ts-1", direction="buy")
        b = _FakeBroker(mode="fill")
        r = run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert r.processed is True
        assert r.outcome == "filled"
        assert r.order_status == "FILLED"
        assert r.order_transactions_written == 2

        assert _count(engine, "orders", "trading_signal_id='ts-1'") == 1
        assert _count(engine, "order_transactions", f"order_id='{r.order_id}'") == 2

        with engine.connect() as conn:
            types = [
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT transaction_type FROM order_transactions"
                        f" WHERE order_id='{r.order_id}' ORDER BY transaction_type"
                    )
                ).fetchall()
            ]
        assert types == ["ORDER_CREATE", "ORDER_FILL"]

    def test_buy_maps_to_broker_side_long(self, engine) -> None:
        _seed_trading_signal(engine, trading_signal_id="ts-buy", direction="buy")
        b = _FakeBroker(mode="fill")
        run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert b.received[0].side == "long"

    def test_sell_maps_to_broker_side_short(self, engine) -> None:
        _seed_trading_signal(engine, trading_signal_id="ts-sell", direction="sell")
        b = _FakeBroker(mode="fill")
        run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert b.received[0].side == "short"

    def test_order_row_carries_account_type_and_correlation(self, engine) -> None:
        _seed_trading_signal(
            engine,
            trading_signal_id="ts-meta",
            direction="buy",
            correlation_id="chain-ABC",
        )
        b = _FakeBroker(mode="fill", account_type="demo")
        r = run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT account_type, correlation_id, units, direction, status, order_type"
                    f" FROM orders WHERE order_id='{r.order_id}'"
                )
            ).fetchone()
        assert row.account_type == "demo"
        assert row.correlation_id == "chain-ABC"
        assert row.direction == "buy"
        assert row.status == "FILLED"
        assert row.order_type == "market"
        assert float(row.units) == 1000.0  # runner default


# --- Rejected --------------------------------------------------------------


class TestRejectedPath:
    def test_broker_reject_writes_canceled_order_and_one_txn(self, engine) -> None:
        _seed_trading_signal(engine, trading_signal_id="ts-rej", direction="buy")
        b = _FakeBroker(mode="reject", reject_message="spread too wide")
        r = run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert r.outcome == "rejected"
        assert r.order_status == "CANCELED"
        assert r.reject_reason == "spread too wide"
        assert r.order_transactions_written == 1

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT transaction_type FROM order_transactions WHERE order_id='{r.order_id}'"
                )
            ).fetchone()
        assert row.transaction_type == "ORDER_REJECT"


# --- Timeout ---------------------------------------------------------------


class TestTimeoutPath:
    def test_timeout_exception_writes_failed_order_and_txn(self, engine) -> None:
        _seed_trading_signal(engine, trading_signal_id="ts-timeout", direction="buy")
        b = _FakeBroker(mode="timeout")
        r = run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert r.outcome == "timeout"
        assert r.order_status == "FAILED"
        assert r.reject_reason  # contains the timeout message
        assert r.order_transactions_written == 1

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT transaction_type, payload FROM order_transactions"
                    f" WHERE order_id='{r.order_id}'"
                )
            ).fetchone()
        assert row.transaction_type == "ORDER_TIMEOUT"
        payload = json.loads(str(row.payload))
        assert "timed out" in payload["message"]


# --- Expired ---------------------------------------------------------------


class TestExpiredPath:
    def test_expired_signal_not_sent_to_broker(self, engine) -> None:
        _seed_trading_signal(
            engine,
            trading_signal_id="ts-exp",
            direction="buy",
            signal_time_utc=_FIXED_NOW - timedelta(seconds=120),
            ttl_seconds=60,
        )
        b = _FakeBroker(mode="fill")
        r = run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert r.outcome == "expired"
        assert r.order_status == "CANCELED"
        # CRITICAL: broker must NOT have been invoked for expired signals.
        assert b.received == []
        assert r.order_transactions_written == 1

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    f"SELECT transaction_type FROM order_transactions WHERE order_id='{r.order_id}'"
                )
            ).fetchone()
        assert row.transaction_type == "ORDER_EXPIRED"

    def test_at_ttl_boundary_still_fills(self, engine) -> None:
        """signal_age == ttl_seconds is NOT expired (strict greater-than)."""
        _seed_trading_signal(
            engine,
            trading_signal_id="ts-boundary",
            direction="buy",
            signal_time_utc=_FIXED_NOW - timedelta(seconds=60),
            ttl_seconds=60,
        )
        b = _FakeBroker(mode="fill")
        r = run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert r.outcome == "filled"


# --- Unprocessed selector / append-only -----------------------------------


class TestUnprocessedSelector:
    def test_second_call_does_not_reprocess(self, engine) -> None:
        _seed_trading_signal(engine, trading_signal_id="ts-a", direction="buy")
        b = _FakeBroker(mode="fill")
        first = run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert first.outcome == "filled"
        second = run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert second.outcome == "noop"
        # Still exactly one orders row for the signal.
        assert _count(engine, "orders", "trading_signal_id='ts-a'") == 1

    def test_multiple_pending_signals_are_processed_one_per_call(self, engine) -> None:
        _seed_trading_signal(
            engine,
            trading_signal_id="ts-old",
            direction="buy",
            signal_time_utc=_FIXED_NOW - timedelta(seconds=10),
        )
        _seed_trading_signal(
            engine,
            trading_signal_id="ts-new",
            direction="sell",
            signal_time_utc=_FIXED_NOW - timedelta(seconds=5),
        )
        b = _FakeBroker(mode="fill")
        # First call picks the older signal (FIFO by signal_time_utc).
        r1 = run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert r1.trading_signal_id == "ts-old"
        # Second call picks the remaining newer one.
        r2 = run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        assert r2.trading_signal_id == "ts-new"
        assert _count(engine, "orders") == 2


# --- Outbox mirror ---------------------------------------------------------


class TestOutboxMirror:
    def test_filled_path_produces_three_outbox_rows(self, engine) -> None:
        _seed_trading_signal(engine, trading_signal_id="ts-ob", direction="buy")
        b = _FakeBroker(mode="fill")
        run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
        )
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT table_name, count(*) FROM secondary_sync_outbox"
                    " GROUP BY table_name ORDER BY table_name"
                )
            ).fetchall()
        by_table: dict[str, Any] = {r[0]: r[1] for r in rows}
        # 1 orders + 2 order_transactions
        assert by_table["orders"] == 1
        assert by_table["order_transactions"] == 2

    def test_common_keys_flow_through(self, engine) -> None:
        _seed_trading_signal(engine, trading_signal_id="ts-ck", direction="buy")
        b = _FakeBroker(mode="fill")
        run_execution_gate(
            engine,
            broker=b,
            account_id="acc-1",
            clock=FixedClock(_FIXED_NOW),
            run_id="run-99",
            environment="paper",
            code_version="sha-1",
            config_version="cv-1",
        )
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT run_id, environment, code_version, config_version"
                    " FROM secondary_sync_outbox WHERE table_name='orders'"
                )
            ).fetchone()
        assert row == ("run-99", "paper", "sha-1", "cv-1")
