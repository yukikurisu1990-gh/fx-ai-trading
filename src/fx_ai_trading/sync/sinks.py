"""Concrete SyncSinkProtocol implementations — Phase 6 Cycle 6.2.

Two Sinks are provided here:

  - InMemorySink : dict-backed store, used by tests and local dev runs.
                   Implements the F-3 de-dup rule (higher version_no wins,
                   equal version_no is skipped).
  - NoopSink     : accepts every envelope without persisting — used when
                   the Sync feature flag is OFF (Phase 6 Decision Freeze
                   allows running without a Secondary target).

Neither Sink imports a DB driver or external transport: they satisfy the
Cycle 6.1 contract's "contract-only module" guarantee at the Sink side.

A future SupabaseSink will live alongside these (separate Cycle) and
share the same Protocol — no change here.
"""

from __future__ import annotations

from threading import Lock
from typing import Any

from .sink_protocol import SyncEnvelope, SyncResult


class InMemorySink:
    """Thread-safe, in-process Sink for tests and dev.

    F-3 dedup semantics:
      - If stored version_no is strictly higher, incoming is skipped
        (accepted=True to signal the envelope is already superseded).
      - If stored version_no is equal, incoming is skipped (idempotent).
      - Otherwise the payload is overwritten.

    The store is exposed via ``get()`` so tests can assert end state.
    """

    name = "in_memory"

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}
        self._lock = Lock()

    def upsert(self, envelope: SyncEnvelope) -> SyncResult:
        key = (envelope.table_name, envelope.primary_key)
        with self._lock:
            existing = self._store.get(key)
            if existing is not None and existing[0] >= envelope.version_no:
                return SyncResult(accepted=True)
            self._store[key] = (envelope.version_no, dict(envelope.payload))
        return SyncResult(accepted=True)

    def get(self, table_name: str, primary_key: str) -> tuple[int, dict[str, Any]] | None:
        with self._lock:
            stored = self._store.get((table_name, primary_key))
            if stored is None:
                return None
            return stored[0], dict(stored[1])

    def size(self) -> int:
        with self._lock:
            return len(self._store)


class NoopSink:
    """Black-hole Sink used when the Sync feature flag is OFF.

    Every envelope is accepted without side effects. Safe to call from
    any context — no state, no I/O.
    """

    name = "noop"

    def upsert(self, envelope: SyncEnvelope) -> SyncResult:  # noqa: ARG002
        return SyncResult(accepted=True)


__all__ = ["InMemorySink", "NoopSink"]
