"""Outbox enqueue helper — Phase 6 Cycle 6.2.

This module's SINGLE responsibility is to ensure the F-12 sanitize
step is applied BEFORE a row lands in ``secondary_sync_outbox``.
The Sink side (Cycle 6.1 contract) trusts the payload and must not
re-sanitize, so the enqueue path is the only place where this
invariant can be enforced.

Design:
  - ``sanitizer`` is a **required** keyword argument.  Callers cannot
    forget it at compile / call time.  Passing ``lambda p: p`` is a
    conscious opt-out that is visible in code review.
  - The helper writes a single row.  Batch enqueue is intentionally
    not provided here — the outbox is sized for per-event rows
    (F-2 at-least-once) and batching should happen inside the caller
    (e.g. domain service) if needed.
  - Common Keys (run_id / environment / code_version / config_version)
    are threaded through as optional kwargs.  Nullable in the
    migration, so they may be omitted in simple contexts.
  - Cycle 6.7d (I-03) adds optional ``conn`` kwarg.  When the caller is
    already inside an active transaction, pass ``conn=`` so the outbox
    INSERT joins that transaction; a rollback upstream then discards the
    outbox row together with the domain row, preserving F-12 atomicity.
    When ``conn`` is omitted the helper opens its own ``engine.begin()``
    block — the legacy behaviour for callers that write a single row.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

from fx_ai_trading.common.clock import Clock
from fx_ai_trading.common.ulid import generate_ulid

Sanitizer = Callable[[dict[str, Any]], dict[str, Any]]


def enqueue_secondary_sync(
    engine: Engine,
    *,
    conn: Connection | None = None,
    table_name: str,
    primary_key: str,
    version_no: int,
    payload: dict[str, Any],
    sanitizer: Sanitizer,
    clock: Clock,
    run_id: str | None = None,
    environment: str | None = None,
    code_version: str | None = None,
    config_version: str | None = None,
) -> str:
    """Enqueue a single envelope into ``secondary_sync_outbox``.

    The ``sanitizer`` callable is invoked on ``payload`` and its return
    value is persisted — the original mapping is discarded.  This is
    the F-12 enforcement point.

    When ``conn`` is provided the INSERT runs on that connection and the
    caller owns commit/rollback (Cycle 6.7d I-03 atomicity).  When it is
    omitted the helper opens ``engine.begin()`` and commits on exit, the
    legacy behaviour for single-row callers.

    Returns the generated ULID ``outbox_id``.

    Raises:
        ValueError: on invalid arguments (empty table_name / primary_key,
                    negative version_no, non-dict sanitized result).
    """
    if not table_name or not table_name.strip():
        raise ValueError("table_name must be non-empty")
    if not primary_key or not primary_key.strip():
        raise ValueError("primary_key must be non-empty")
    if version_no < 0:
        raise ValueError("version_no must be >= 0")
    if not callable(sanitizer):
        raise ValueError("sanitizer must be callable")

    sanitized = sanitizer(payload)
    if not isinstance(sanitized, dict):
        raise ValueError(
            "sanitizer must return a dict "
            f"(got {type(sanitized).__name__}); F-12 requires dict payload"
        )

    outbox_id = generate_ulid()
    enqueued_at = clock.now()

    # JSON is serialised by the driver (sa.JSON → JSONB on PG, TEXT on
    # SQLite). We pass the dict directly and let SQLAlchemy encode.
    import json

    payload_text = json.dumps(sanitized, ensure_ascii=False, sort_keys=True)

    sql = text(
        """
        INSERT INTO secondary_sync_outbox (
            outbox_id, table_name, primary_key, version_no,
            payload_json, enqueued_at, attempt_count,
            run_id, environment, code_version, config_version
        ) VALUES (
            :outbox_id, :table_name, :primary_key, :version_no,
            :payload_json, :enqueued_at, 0,
            :run_id, :environment, :code_version, :config_version
        )
        """
    )
    params = {
        "outbox_id": outbox_id,
        "table_name": table_name,
        "primary_key": primary_key,
        "version_no": version_no,
        "payload_json": payload_text,
        "enqueued_at": enqueued_at,
        "run_id": run_id,
        "environment": environment,
        "code_version": code_version,
        "config_version": config_version,
    }
    if conn is not None:
        conn.execute(sql, params)
    else:
        with engine.begin() as owned_conn:
            owned_conn.execute(sql, params)
    return outbox_id


__all__ = ["Sanitizer", "enqueue_secondary_sync"]
