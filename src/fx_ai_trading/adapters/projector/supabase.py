"""Supabase Projector adapter — secondary DB snapshot transport (M23).

Implements the ProjectionTransport Protocol for Supabase as the secondary
target.  Iteration 2 scope: Interface skeleton only; the real Supabase
client is injected so that all tests use MockSupabaseClient.

Real Supabase connectivity is documented in docs/runbooks/supabase_projector.md
(manual runbook, Phase 7+). Tests never open a real Supabase connection.

Phase 7 note: When Cold Archive is operationalized, SupabaseProjectionTransport
will be refactored to handle 4 tables (positions, close_events, orders,
supervisor_events) and add retry / schema-alignment logic.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SupabaseClient Protocol — thin wrapper around the real Supabase REST client
# ---------------------------------------------------------------------------


class SupabaseClient(Protocol):
    """Minimal Supabase REST client interface (D3 §2.19).

    Iteration 2: only `upsert` is required. Phase 7 extends this with
    retry, pagination, and schema-version checks.
    """

    def upsert(self, table: str, rows: list[dict[str, Any]]) -> int:
        """Upsert *rows* into *table*.

        Returns the number of rows upserted.
        Raises on transport / auth errors (caller handles).
        """
        ...


# ---------------------------------------------------------------------------
# Mock client — used in all Iteration 2 tests
# ---------------------------------------------------------------------------


class MockSupabaseClient:
    """In-memory Supabase stub for testing.

    Stores rows per table in a plain dict; upsert overwrites by primary key
    when the row dict contains 'supervisor_event_id' (or any '*_id' field).
    If no recognized PK is found, rows are appended (idempotency not checked).
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, dict[str, Any]]] = {}
        self.call_log: list[tuple[str, int]] = []

    def upsert(self, table: str, rows: list[dict[str, Any]]) -> int:
        if table not in self._store:
            self._store[table] = {}
        for row in rows:
            pk_key = next((k for k in row if k.endswith("_id")), None)
            if pk_key:
                self._store[table][row[pk_key]] = row
            else:
                self._store[table][id(row)] = row
        count = len(rows)
        self.call_log.append((table, count))
        return count

    def rows(self, table: str) -> list[dict[str, Any]]:
        """Return all stored rows for *table* (for test assertions)."""
        return list(self._store.get(table, {}).values())

    def call_count(self, table: str) -> int:
        """Return the number of upsert calls made for *table*."""
        return sum(1 for t, _ in self.call_log if t == table)


# ---------------------------------------------------------------------------
# Production transport
# ---------------------------------------------------------------------------


class SupabaseProjectionTransport:
    """ProjectionTransport implementation backed by a SupabaseClient.

    Args:
        client: A SupabaseClient implementation.  Production code injects
                the real Supabase REST client; tests inject MockSupabaseClient.
    """

    def __init__(self, client: SupabaseClient) -> None:
        self._client = client

    def upsert(self, table: str, rows: list[dict[str, Any]]) -> int:
        """Upsert *rows* into *table* via the injected client.

        Returns the row count.  On any error: logs a warning and returns 0.
        Never raises (fail-open per D3 §2.19).
        """
        if not rows:
            return 0
        try:
            count = self._client.upsert(table, rows)
            _log.debug("SupabaseProjectionTransport.upsert: table=%s count=%d", table, count)
            return count
        except Exception as exc:
            _log.warning(
                "SupabaseProjectionTransport.upsert: failed table=%s rows=%d: %s",
                table,
                len(rows),
                exc,
            )
            return 0
