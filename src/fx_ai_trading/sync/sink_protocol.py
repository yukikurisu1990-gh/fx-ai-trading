"""SyncSinkProtocol — contract between secondary_sync_outbox and any Secondary target.

This module is contract-only.  It MUST NOT import any DB driver, transport
client, or service implementation.  Cycle 6.2 will add concrete Sinks
(InMemorySink, NoopSink, SupabaseSink) and the Sync Service worker; both
depend on this Protocol.

Phase 6 Decision Freeze references:

  - F-2  : at-least-once delivery via outbox + idempotent upsert on Sink side.
  - F-3  : Sink de-dup key is (table_name, primary_key, version_no);
           higher version_no MUST overwrite lower; equal version_no MAY
           overwrite or skip (Sink's choice).
  - F-12 : payload is sanitized BEFORE enqueue.  Sinks trust the payload
           and MUST NOT echo any payload value into error messages.

Forward-compat:

  - SyncEnvelope is frozen and contains only the minimum needed for
    idempotent delivery; richer telemetry (size, hash, retry hints) is
    intentionally left out — add as a separate optional struct in a future
    cycle rather than extending this contract.
  - SyncResult exposes only `accepted` + `error_message`.  Per-Sink
    metrics (latency, batch size) belong in the worker's telemetry path,
    not in this contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class SyncEnvelope:
    """A single de-duplicatable sync delivery unit.

    Attributes:
        table_name:  Target table name on the Secondary side
                     (one-to-one with Primary table name; Sinks MUST NOT
                     remap names — that responsibility is the Sync
                     Service worker's, applied before invoking the Sink).
        primary_key: JSON-encoded composite PK string of the source row
                     (e.g. '["EUR_USD","2026-04-20T00:00:00Z"]').
                     Used by the Sink as part of the idempotency key.
        version_no:  Monotonically increasing per (table_name, primary_key).
                     A Sink that already saw a higher version_no MAY skip.
        payload:     Sanitized payload (F-12 already applied at enqueue).
                     The Sink trusts that no secret-like fields remain.
    """

    table_name: str
    primary_key: str
    version_no: int
    payload: dict[str, Any]


@dataclass(frozen=True)
class SyncResult:
    """Result of a single SyncSinkProtocol.upsert call.

    Attributes:
        accepted:      True if the Sink considers the envelope durable on
                       its side (or successfully de-duplicated against a
                       higher version_no it had already seen).  False
                       triggers retry / backoff in the worker.
        error_message: Optional human-readable error.  MUST NOT contain
                       any payload value (F-12 echo guard).  Intended for
                       data_quality_events / Sync telemetry only.
    """

    accepted: bool
    error_message: str | None = None


@runtime_checkable
class SyncSinkProtocol(Protocol):
    """Sink contract for the Sync Service worker (F-2 / F-3 / F-12).

    Implementations are stateless from the worker's perspective: each
    upsert call is independent and the Sink MUST be safe to call with
    the same envelope multiple times.

    A Sink MAY batch internally for performance, but MUST report a
    per-envelope SyncResult (no group/transaction semantics are exposed
    through this Protocol).
    """

    name: str  # short identifier used in telemetry / data_quality_events tags

    def upsert(self, envelope: SyncEnvelope) -> SyncResult:
        """Deliver one envelope to the Secondary target.

        Implementations MUST:
          - treat (envelope.table_name, envelope.primary_key,
            envelope.version_no) as the idempotency key,
          - never raise on transient transport failures — return
            SyncResult(accepted=False, error_message=...) instead so the
            worker can apply backoff,
          - never echo any payload value in error_message (F-12).

        Implementations MAY raise only on programmer errors
        (invalid envelope shape, misconfigured Sink) — these are NOT
        handled by the worker's backoff and will surface to the caller.
        """
        ...


__all__ = [
    "SyncEnvelope",
    "SyncResult",
    "SyncSinkProtocol",
]
