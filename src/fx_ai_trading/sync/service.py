"""Sync Service worker — Phase 6 Cycle 6.2.

Single public entry point: ``SyncService.run_once``.

Design intent (important):
  - ``run_once`` is **pure per-batch**.  One call processes up to
    ``max_items`` envelopes and returns a ``SyncRunResult``.  The
    function does NOT loop, sleep, or retry internally — callers
    (cron, supervisor, tests) decide cadence.  This keeps the worker
    testable as a plain function and leaves future daemon-mode
    adoption a trivial wrapper around repeated calls.
  - All side effects go through the passed-in ``Engine`` and
    ``Clock``.  No module-level state, no global time lookups.
  - Failure of a single envelope never aborts the batch — the worker
    records ``last_error`` / ``next_attempt_at`` and continues with
    the next row (Phase 6 F-2: at-least-once with backoff).

Forward-compat:
  - ``SyncRunResult`` starts minimal; richer telemetry (avg latency,
    per-Sink histograms) belongs in a separate struct.
  - ``RetryPolicy`` is a frozen dataclass; extensions (jitter, per-
    error-class policies) can be added without changing call sites.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from fx_ai_trading.common.clock import Clock

from .sink_protocol import SyncEnvelope, SyncSinkProtocol


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential backoff parameters (no jitter in this cycle).

    next_attempt_at = now + min(base_delay * 2**attempt_count, max_delay)

    ``attempt_count`` is the count AFTER incrementing on the current
    failure (so the first retry is scheduled ``base_delay`` seconds
    out, not 2 * base_delay).
    """

    base_delay: timedelta = timedelta(seconds=30)
    max_delay: timedelta = timedelta(minutes=30)


def compute_next_attempt_at(
    *,
    now: datetime,
    attempt_count: int,
    policy: RetryPolicy,
) -> datetime:
    """Pure backoff calculation — exposed for unit tests."""
    if attempt_count <= 0:
        raise ValueError("attempt_count must be >= 1 (count after failure)")
    # 2 ** (attempt_count - 1) so attempt 1 -> base_delay exactly.
    shift = attempt_count - 1
    # Cap the exponent to avoid OverflowError at large attempt counts.
    if shift > 30:
        shift = 30
    delay_seconds = policy.base_delay.total_seconds() * (2**shift)
    delay = min(timedelta(seconds=delay_seconds), policy.max_delay)
    return now + delay


@dataclass(frozen=True)
class SyncRunResult:
    """Per-batch outcome.

    Attributes:
        polled:            rows read from the outbox in this batch.
        accepted:          sink reported accepted=True (may include
                           F-3 skipped-as-superseded).
        rejected:          sink reported accepted=False; retry scheduled.
    """

    polled: int
    accepted: int
    rejected: int


# Internal representation of a polled outbox row.
@dataclass(frozen=True)
class _PolledRow:
    outbox_id: str
    table_name: str
    primary_key: str
    version_no: int
    payload: dict[str, Any]
    attempt_count: int


class SyncService:
    """Outbox poller + Sink dispatcher (batch-per-call)."""

    def __init__(
        self,
        *,
        engine: Engine,
        sink: SyncSinkProtocol,
        clock: Clock,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self._engine = engine
        self._sink = sink
        self._clock = clock
        self._policy = retry_policy or RetryPolicy()

    def run_once(self, *, max_items: int = 100) -> SyncRunResult:
        """Poll up to ``max_items`` pending envelopes and dispatch.

        Flow per batch:
          1. SELECT pending rows (acked_at IS NULL AND
             (next_attempt_at IS NULL OR next_attempt_at <= now))
             ORDER BY enqueued_at LIMIT :max_items.
          2. For each row, call ``sink.upsert(envelope)``.
          3. On accepted=True : UPDATE ... SET acked_at = now.
             On accepted=False: UPDATE ... SET attempt_count += 1,
                                last_error, next_attempt_at = now +
                                backoff(attempt_count).
          4. Return SyncRunResult.
        """
        if max_items <= 0:
            raise ValueError("max_items must be > 0")

        now = self._clock.now()
        rows = self._poll(now=now, limit=max_items)

        accepted = 0
        rejected = 0
        for row in rows:
            envelope = SyncEnvelope(
                table_name=row.table_name,
                primary_key=row.primary_key,
                version_no=row.version_no,
                payload=row.payload,
            )
            result = self._sink.upsert(envelope)
            if result.accepted:
                self._ack(outbox_id=row.outbox_id, now=self._clock.now())
                accepted += 1
            else:
                new_attempt_count = row.attempt_count + 1
                self._schedule_retry(
                    outbox_id=row.outbox_id,
                    attempt_count=new_attempt_count,
                    last_error=result.error_message,
                    now=self._clock.now(),
                )
                rejected += 1

        return SyncRunResult(polled=len(rows), accepted=accepted, rejected=rejected)

    # -- internals ---------------------------------------------------------

    def _poll(self, *, now: datetime, limit: int) -> list[_PolledRow]:
        sql = text(
            """
            SELECT outbox_id, table_name, primary_key, version_no,
                   payload_json, attempt_count
            FROM secondary_sync_outbox
            WHERE acked_at IS NULL
              AND (next_attempt_at IS NULL OR next_attempt_at <= :now)
            ORDER BY enqueued_at
            LIMIT :limit
            """
        )
        with self._engine.connect() as conn:
            rs = conn.execute(sql, {"now": now, "limit": limit}).fetchall()
        out: list[_PolledRow] = []
        for r in rs:
            payload = _coerce_payload(r.payload_json)
            out.append(
                _PolledRow(
                    outbox_id=r.outbox_id,
                    table_name=r.table_name,
                    primary_key=r.primary_key,
                    version_no=r.version_no,
                    payload=payload,
                    attempt_count=r.attempt_count,
                )
            )
        return out

    def _ack(self, *, outbox_id: str, now: datetime) -> None:
        sql = text(
            """
            UPDATE secondary_sync_outbox
            SET acked_at = :now,
                last_error = NULL,
                next_attempt_at = NULL
            WHERE outbox_id = :outbox_id
              AND acked_at IS NULL
            """
        )
        with self._engine.begin() as conn:
            conn.execute(sql, {"now": now, "outbox_id": outbox_id})

    def _schedule_retry(
        self,
        *,
        outbox_id: str,
        attempt_count: int,
        last_error: str | None,
        now: datetime,
    ) -> None:
        next_at = compute_next_attempt_at(
            now=now, attempt_count=attempt_count, policy=self._policy
        )
        sql = text(
            """
            UPDATE secondary_sync_outbox
            SET attempt_count = :attempt_count,
                next_attempt_at = :next_at,
                last_error = :last_error
            WHERE outbox_id = :outbox_id
              AND acked_at IS NULL
            """
        )
        with self._engine.begin() as conn:
            conn.execute(
                sql,
                {
                    "attempt_count": attempt_count,
                    "next_at": next_at,
                    "last_error": last_error,
                    "outbox_id": outbox_id,
                },
            )


def _coerce_payload(raw: Any) -> dict[str, Any]:
    """SQLite stores sa.JSON as TEXT; PG returns dict directly."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        import json

        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError(
                f"outbox payload_json must decode to dict, got {type(decoded).__name__}"
            )
        return decoded
    raise ValueError(f"unexpected payload_json type: {type(raw).__name__}")


__all__ = [
    "RetryPolicy",
    "SyncRunResult",
    "SyncService",
    "compute_next_attempt_at",
]
