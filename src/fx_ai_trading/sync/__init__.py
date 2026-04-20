"""Sync module — Primary -> Secondary outbox-based delivery (Phase 6).

Cycle 6.1 scope: contract-only (``sink_protocol``).
Cycle 6.2 scope: InMemorySink / NoopSink, SyncService worker,
                 F-12 enqueue gate.

A future SupabaseSink will plug into the same Protocol without changing
this module.

Coexists with M23 ProjectionService (snapshot-based, supervisor_events only)
without modification — the two paths are intentionally disjoint.
"""

from .enqueue import Sanitizer, enqueue_secondary_sync
from .service import RetryPolicy, SyncRunResult, SyncService, compute_next_attempt_at
from .sink_protocol import SyncEnvelope, SyncResult, SyncSinkProtocol
from .sinks import InMemorySink, NoopSink

__all__ = [
    # Contract (Cycle 6.1)
    "SyncEnvelope",
    "SyncResult",
    "SyncSinkProtocol",
    # Sinks (Cycle 6.2)
    "InMemorySink",
    "NoopSink",
    # Service + policy (Cycle 6.2)
    "RetryPolicy",
    "SyncRunResult",
    "SyncService",
    "compute_next_attempt_at",
    # Enqueue F-12 gate (Cycle 6.2)
    "Sanitizer",
    "enqueue_secondary_sync",
]
