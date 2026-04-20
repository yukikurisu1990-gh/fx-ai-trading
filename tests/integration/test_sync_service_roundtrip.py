"""Integration test: outbox -> sink -> ack round-trip (Cycle 6.2).

No live PostgreSQL is required.  The ``secondary_sync_outbox`` table is
recreated in an in-memory SQLite engine via raw DDL matching migration
0013 (nullability, defaults, index semantics preserved — the worker
only relies on portable SQL, never PG-specific features).

What is verified:
  - happy path: poll -> upsert -> ack (a second run_once sees 0 rows).
  - re-send safety: running twice never duplicates Sink state.
  - rejection path: accepted=False schedules a retry via exponential
    backoff; a subsequent run_once BEFORE the retry window ignores the
    row; AFTER the window it re-delivers.
  - mixed batch: multiple rows, some accepted and some rejected, are
    all reflected correctly.
  - F-3 dedup at the worker-observable level: re-enqueue of the same
    (table_name, primary_key) with a lower version_no is delivered but
    the Sink keeps the higher state.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.common.clock import FixedClock
from fx_ai_trading.sync.enqueue import enqueue_secondary_sync
from fx_ai_trading.sync.service import RetryPolicy, SyncService
from fx_ai_trading.sync.sink_protocol import SyncEnvelope, SyncResult
from fx_ai_trading.sync.sinks import InMemorySink

_DDL = """
CREATE TABLE secondary_sync_outbox (
    outbox_id        TEXT PRIMARY KEY,
    table_name       TEXT NOT NULL,
    primary_key      TEXT NOT NULL,
    version_no       BIGINT NOT NULL DEFAULT 0,
    payload_json     TEXT NOT NULL,
    enqueued_at      TEXT NOT NULL,
    acked_at         TEXT,
    last_error       TEXT,
    attempt_count    INTEGER NOT NULL DEFAULT 0,
    next_attempt_at  TEXT,
    run_id           TEXT,
    environment      TEXT,
    code_version     TEXT,
    config_version   TEXT
)
"""

_FIXED_NOW = datetime(2026, 4, 20, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        conn.execute(text(_DDL))
    yield eng
    eng.dispose()


def _identity(p: dict) -> dict:
    return dict(p)


def _enqueue(engine, *, pk: str, v: int, payload: dict, now: datetime = _FIXED_NOW) -> str:
    return enqueue_secondary_sync(
        engine,
        table_name="positions",
        primary_key=pk,
        version_no=v,
        payload=payload,
        sanitizer=_identity,
        clock=FixedClock(now),
    )


def _pending_count(engine) -> int:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT count(*) FROM secondary_sync_outbox WHERE acked_at IS NULL")
        ).scalar()


class _FailingSink:
    """Sink that rejects every envelope with a fixed error."""

    name = "failing"

    def __init__(self) -> None:
        self.calls: list[SyncEnvelope] = []

    def upsert(self, envelope: SyncEnvelope) -> SyncResult:
        self.calls.append(envelope)
        return SyncResult(accepted=False, error_message="transient: backend unreachable")


class _ToggleSink:
    """Sink that rejects first N envelopes then accepts the rest."""

    name = "toggle"

    def __init__(self, reject_first: int) -> None:
        self._remaining = reject_first
        self.accepted_envelopes: list[SyncEnvelope] = []

    def upsert(self, envelope: SyncEnvelope) -> SyncResult:
        if self._remaining > 0:
            self._remaining -= 1
            return SyncResult(accepted=False, error_message="transient")
        self.accepted_envelopes.append(envelope)
        return SyncResult(accepted=True)


class TestHappyPath:
    def test_single_envelope_round_trip(self, engine) -> None:
        _enqueue(engine, pk="pk1", v=1, payload={"x": 1})
        assert _pending_count(engine) == 1

        sink = InMemorySink()
        svc = SyncService(engine=engine, sink=sink, clock=FixedClock(_FIXED_NOW))
        r = svc.run_once()

        assert r.polled == 1
        assert r.accepted == 1
        assert r.rejected == 0
        assert _pending_count(engine) == 0
        assert sink.get("positions", "pk1") == (1, {"x": 1})

    def test_second_run_after_ack_is_noop(self, engine) -> None:
        """Re-send safety: a second run must see 0 rows (idempotency at the
        poll layer — acked rows are excluded by the WHERE clause)."""
        _enqueue(engine, pk="pk1", v=1, payload={"x": 1})
        sink = InMemorySink()
        svc = SyncService(engine=engine, sink=sink, clock=FixedClock(_FIXED_NOW))

        r1 = svc.run_once()
        r2 = svc.run_once()

        assert r1.accepted == 1
        assert r2.polled == 0
        assert r2.accepted == 0
        assert r2.rejected == 0
        assert sink.size() == 1

    def test_ordering_by_enqueued_at(self, engine) -> None:
        _enqueue(engine, pk="pk1", v=1, payload={"n": 1}, now=_FIXED_NOW)
        _enqueue(engine, pk="pk2", v=1, payload={"n": 2}, now=_FIXED_NOW + timedelta(seconds=1))
        _enqueue(engine, pk="pk3", v=1, payload={"n": 3}, now=_FIXED_NOW + timedelta(seconds=2))

        order_seen: list[str] = []

        class _OrderingSink:
            name = "order"

            def upsert(self, env: SyncEnvelope) -> SyncResult:
                order_seen.append(env.primary_key)
                return SyncResult(accepted=True)

        svc = SyncService(
            engine=engine,
            sink=_OrderingSink(),
            clock=FixedClock(_FIXED_NOW + timedelta(seconds=10)),
        )
        svc.run_once()
        assert order_seen == ["pk1", "pk2", "pk3"]


class TestRejectionAndRetry:
    def test_rejection_schedules_retry(self, engine) -> None:
        _enqueue(engine, pk="pk1", v=1, payload={"x": 1})
        sink = _FailingSink()
        policy = RetryPolicy(
            base_delay=timedelta(seconds=30),
            max_delay=timedelta(minutes=30),
        )
        svc = SyncService(
            engine=engine,
            sink=sink,
            clock=FixedClock(_FIXED_NOW),
            retry_policy=policy,
        )
        r = svc.run_once()

        assert r.polled == 1
        assert r.accepted == 0
        assert r.rejected == 1
        assert len(sink.calls) == 1

        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT attempt_count, last_error, next_attempt_at, acked_at"
                    " FROM secondary_sync_outbox WHERE primary_key='pk1'"
                )
            ).fetchone()
        assert row.attempt_count == 1
        assert row.last_error == "transient: backend unreachable"
        assert row.acked_at is None
        # SQLite stores the datetime param as iso string; the worker passed
        # clock.now() + 30s for the first retry.
        assert row.next_attempt_at is not None

    def test_row_skipped_before_retry_window(self, engine) -> None:
        """A second run_once BEFORE next_attempt_at must ignore the row."""
        _enqueue(engine, pk="pk1", v=1, payload={"x": 1})
        failing = _FailingSink()
        policy = RetryPolicy(base_delay=timedelta(seconds=30), max_delay=timedelta(minutes=30))

        # First run at NOW -> schedules retry at NOW + 30s
        SyncService(
            engine=engine,
            sink=failing,
            clock=FixedClock(_FIXED_NOW),
            retry_policy=policy,
        ).run_once()

        # Second run only 10s later -> window not reached
        later = _FIXED_NOW + timedelta(seconds=10)
        r2 = SyncService(
            engine=engine,
            sink=failing,
            clock=FixedClock(later),
            retry_policy=policy,
        ).run_once()

        assert r2.polled == 0  # correctly skipped
        assert len(failing.calls) == 1  # sink NOT called a second time

    def test_row_re_delivered_after_retry_window(self, engine) -> None:
        """A run_once AFTER next_attempt_at must re-dispatch."""
        _enqueue(engine, pk="pk1", v=1, payload={"x": 1})
        policy = RetryPolicy(base_delay=timedelta(seconds=30), max_delay=timedelta(minutes=30))

        # First run rejects.
        sink = _ToggleSink(reject_first=1)
        svc1 = SyncService(
            engine=engine,
            sink=sink,
            clock=FixedClock(_FIXED_NOW),
            retry_policy=policy,
        )
        r1 = svc1.run_once()
        assert r1.rejected == 1

        # Second run 2 minutes later — sink now accepts.
        later = _FIXED_NOW + timedelta(minutes=2)
        svc2 = SyncService(
            engine=engine,
            sink=sink,
            clock=FixedClock(later),
            retry_policy=policy,
        )
        r2 = svc2.run_once()
        assert r2.polled == 1
        assert r2.accepted == 1
        assert _pending_count(engine) == 0
        assert len(sink.accepted_envelopes) == 1
        # Final outbox row shows the increment-then-clear pattern.
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT attempt_count, acked_at, last_error, next_attempt_at"
                    " FROM secondary_sync_outbox"
                )
            ).fetchone()
        assert row.attempt_count == 1  # count retained for observability
        assert row.acked_at is not None
        assert row.last_error is None
        assert row.next_attempt_at is None


class TestBatchBehavior:
    def test_max_items_caps_batch(self, engine) -> None:
        for i in range(5):
            _enqueue(
                engine, pk=f"pk{i}", v=1, payload={"i": i}, now=_FIXED_NOW + timedelta(seconds=i)
            )
        sink = InMemorySink()
        svc = SyncService(
            engine=engine,
            sink=sink,
            clock=FixedClock(_FIXED_NOW + timedelta(minutes=1)),
        )
        r = svc.run_once(max_items=3)
        assert r.polled == 3
        assert r.accepted == 3
        assert _pending_count(engine) == 2  # remaining 2

    def test_mixed_batch(self, engine) -> None:
        _enqueue(engine, pk="pk1", v=1, payload={"a": 1}, now=_FIXED_NOW)
        _enqueue(engine, pk="pk2", v=1, payload={"b": 2}, now=_FIXED_NOW + timedelta(seconds=1))
        _enqueue(engine, pk="pk3", v=1, payload={"c": 3}, now=_FIXED_NOW + timedelta(seconds=2))

        class _OddRejectSink:
            name = "odd-reject"

            def __init__(self) -> None:
                self.i = 0

            def upsert(self, env: SyncEnvelope) -> SyncResult:
                self.i += 1
                if self.i % 2 == 0:  # 2nd call fails
                    return SyncResult(accepted=False, error_message="e")
                return SyncResult(accepted=True)

        svc = SyncService(
            engine=engine,
            sink=_OddRejectSink(),
            clock=FixedClock(_FIXED_NOW + timedelta(minutes=1)),
        )
        r = svc.run_once()
        assert r.polled == 3
        assert r.accepted == 2
        assert r.rejected == 1
        assert _pending_count(engine) == 1


class TestF3DedupVisibility:
    def test_higher_version_overwrites_sink_state(self, engine) -> None:
        """Two enqueues for the same key — the Sink ends with higher version.

        Outbox preserves both rows (append-only), but the Sink enforces
        F-3 dedup so the final observable state reflects version 2."""
        _enqueue(engine, pk="pk1", v=1, payload={"x": "v1"}, now=_FIXED_NOW)
        _enqueue(engine, pk="pk1", v=2, payload={"x": "v2"}, now=_FIXED_NOW + timedelta(seconds=1))

        sink = InMemorySink()
        SyncService(
            engine=engine,
            sink=sink,
            clock=FixedClock(_FIXED_NOW + timedelta(minutes=1)),
        ).run_once()

        stored = sink.get("positions", "pk1")
        assert stored == (2, {"x": "v2"})
        # Both outbox rows acked (append-only log, neither lost).
        with engine.connect() as conn:
            acked = conn.execute(
                text(
                    "SELECT count(*) FROM secondary_sync_outbox"
                    " WHERE primary_key='pk1' AND acked_at IS NOT NULL"
                )
            ).scalar()
        assert acked == 2


class TestInputValidation:
    def test_max_items_must_be_positive(self, engine) -> None:
        svc = SyncService(engine=engine, sink=InMemorySink(), clock=FixedClock(_FIXED_NOW))
        with pytest.raises(ValueError, match="max_items must be > 0"):
            svc.run_once(max_items=0)


class TestPayloadIsPreserved:
    def test_payload_json_matches_after_roundtrip(self, engine) -> None:
        """End-to-end payload fidelity: enqueue -> poll -> upsert -> sink store."""
        payload = {"a": 1, "b": [1, 2, 3], "c": {"nested": True}}
        _enqueue(engine, pk="pk1", v=1, payload=payload)

        sink = InMemorySink()
        SyncService(engine=engine, sink=sink, clock=FixedClock(_FIXED_NOW)).run_once()

        stored = sink.get("positions", "pk1")
        assert stored is not None
        # JSON round-trip normalises — compare via json encode.
        assert json.dumps(stored[1], sort_keys=True) == json.dumps(payload, sort_keys=True)
