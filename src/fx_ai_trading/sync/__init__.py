"""Sync module — Primary -> Secondary outbox-based delivery (Phase 6).

Cycle 6.1 scope: contract-only.  No worker, no transport, no DB connection.
Cycle 6.2 will add the worker and InMemorySink / NoopSink / SupabaseSink
implementations on top of this contract.

Coexists with M23 ProjectionService (snapshot-based, supervisor_events only)
without modification — the two paths are intentionally disjoint.
"""
