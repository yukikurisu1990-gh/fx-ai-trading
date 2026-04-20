"""Unit tests for InMemorySink / NoopSink (Phase 6 Cycle 6.2).

Covers:
  - Protocol conformance (runtime_checkable).
  - F-3 de-dup semantics for InMemorySink (higher / equal / lower
    version_no scenarios).
  - Re-send safety (same envelope twice -> same end state).
  - NoopSink always accepts, never stores.
"""

from __future__ import annotations

from fx_ai_trading.sync.sink_protocol import (
    SyncEnvelope,
    SyncResult,
    SyncSinkProtocol,
)
from fx_ai_trading.sync.sinks import InMemorySink, NoopSink


def _env(v: int, payload: dict | None = None) -> SyncEnvelope:
    return SyncEnvelope(
        table_name="positions",
        primary_key='["EUR_USD","2026-04-20T00:00:00Z"]',
        version_no=v,
        payload=payload if payload is not None else {"v": v},
    )


class TestInMemorySinkBasics:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(InMemorySink(), SyncSinkProtocol)

    def test_has_name(self) -> None:
        assert InMemorySink().name == "in_memory"

    def test_first_upsert_stores(self) -> None:
        sink = InMemorySink()
        r = sink.upsert(_env(1))
        assert r == SyncResult(accepted=True)
        assert sink.size() == 1
        stored = sink.get("positions", '["EUR_USD","2026-04-20T00:00:00Z"]')
        assert stored is not None
        assert stored[0] == 1
        assert stored[1] == {"v": 1}


class TestInMemorySinkDedup:
    """F-3: higher version_no MUST overwrite; equal MAY skip."""

    def test_higher_version_overwrites(self) -> None:
        sink = InMemorySink()
        sink.upsert(_env(1, {"v": 1}))
        sink.upsert(_env(2, {"v": 2}))
        stored = sink.get("positions", '["EUR_USD","2026-04-20T00:00:00Z"]')
        assert stored is not None
        assert stored[0] == 2
        assert stored[1] == {"v": 2}

    def test_equal_version_is_skipped(self) -> None:
        """Equal version is skipped and treated as already-accepted (idempotent)."""
        sink = InMemorySink()
        sink.upsert(_env(5, {"v": "first"}))
        r = sink.upsert(_env(5, {"v": "SECOND — should be ignored"}))
        assert r.accepted is True
        stored = sink.get("positions", '["EUR_USD","2026-04-20T00:00:00Z"]')
        assert stored is not None
        assert stored[1] == {"v": "first"}

    def test_lower_version_is_skipped(self) -> None:
        sink = InMemorySink()
        sink.upsert(_env(10, {"v": 10}))
        r = sink.upsert(_env(3, {"v": "older"}))
        assert r.accepted is True  # accepted-as-superseded
        stored = sink.get("positions", '["EUR_USD","2026-04-20T00:00:00Z"]')
        assert stored is not None
        assert stored[0] == 10
        assert stored[1] == {"v": 10}

    def test_resend_is_idempotent(self) -> None:
        """Same envelope replayed N times -> same end state (core F-2 promise)."""
        sink = InMemorySink()
        env = _env(7, {"v": 7})
        for _ in range(10):
            r = sink.upsert(env)
            assert r.accepted is True
        stored = sink.get("positions", '["EUR_USD","2026-04-20T00:00:00Z"]')
        assert stored == (7, {"v": 7})
        assert sink.size() == 1


class TestInMemorySinkDistinctKeys:
    def test_different_primary_keys_coexist(self) -> None:
        sink = InMemorySink()
        env_a = SyncEnvelope(
            table_name="positions",
            primary_key='["EUR_USD","t1"]',
            version_no=1,
            payload={"a": 1},
        )
        env_b = SyncEnvelope(
            table_name="positions",
            primary_key='["USD_JPY","t1"]',
            version_no=1,
            payload={"b": 1},
        )
        sink.upsert(env_a)
        sink.upsert(env_b)
        assert sink.size() == 2

    def test_different_tables_coexist(self) -> None:
        sink = InMemorySink()
        env_a = SyncEnvelope(
            table_name="positions",
            primary_key="pk",
            version_no=1,
            payload={"a": 1},
        )
        env_b = SyncEnvelope(
            table_name="orders",
            primary_key="pk",
            version_no=1,
            payload={"b": 1},
        )
        sink.upsert(env_a)
        sink.upsert(env_b)
        assert sink.size() == 2


class TestInMemorySinkPayloadIsolation:
    def test_stored_payload_is_copy(self) -> None:
        """Mutating the caller's payload dict must not mutate the sink store."""
        sink = InMemorySink()
        payload = {"v": 1}
        sink.upsert(
            SyncEnvelope(
                table_name="t",
                primary_key="pk",
                version_no=1,
                payload=payload,
            )
        )
        payload["v"] = 999  # mutate caller's copy
        stored = sink.get("t", "pk")
        assert stored is not None
        assert stored[1] == {"v": 1}

    def test_get_returns_copy(self) -> None:
        """Mutating the return value must not mutate the sink store."""
        sink = InMemorySink()
        sink.upsert(
            SyncEnvelope(table_name="t", primary_key="pk", version_no=1, payload={"v": 1})
        )
        stored = sink.get("t", "pk")
        assert stored is not None
        stored[1]["v"] = 999
        again = sink.get("t", "pk")
        assert again is not None
        assert again[1] == {"v": 1}


class TestNoopSink:
    def test_satisfies_protocol(self) -> None:
        assert isinstance(NoopSink(), SyncSinkProtocol)

    def test_has_name(self) -> None:
        assert NoopSink().name == "noop"

    def test_always_accepts(self) -> None:
        sink = NoopSink()
        for v in range(5):
            r = sink.upsert(_env(v))
            assert r.accepted is True
            assert r.error_message is None
