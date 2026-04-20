"""migration 0013: create secondary_sync_outbox table (Phase 6 Cycle 6.1).

Group: I (Operations) — extends the 6 existing Operations tables to 7.
Total D1 tables: 43 -> 44.

Why this table is needed (Phase 6 Decision Freeze F-2 / F-3 / F-12):

  Phase 6 introduces a generalized Primary -> Secondary sync mechanism with
  at-least-once delivery and per-row idempotency.  The Sync Service worker
  (Cycle 6.2) will pull pending rows from this table and hand them to a
  SyncSinkProtocol implementation; Sinks treat (table_name, primary_key,
  version_no) as the idempotency key, so retransmissions are safe.

Distinct from existing outbox_events (#39):

  - outbox_events           : order dispatch HTTP outbox (Primary side only;
                              feeds OANDA via OutboxProcessor / M8).
  - secondary_sync_outbox   : Primary -> Secondary DB sync outbox (this table).

  Names are confusingly similar but the responsibilities are disjoint and
  the two tables are intentionally separate to keep dispatch failures of one
  channel from blocking the other.

Coexistence with M23 ProjectionService:

  ProjectionService is a snapshot-based projector for supervisor_events
  only (D3 §2.19).  It is left intact.  All NEW Secondary sync targets
  added from Phase 6 onward use this outbox table instead of extending
  ProjectionService — outbox is event-driven and survives Sync Service
  downtime, which the snapshot model does not.

Forward-compat principles (designed so no future migration is expected for
this contract; new features fit into the existing columns):

  1. version_no allows the worker / Sink to enforce monotonic upsert
     ordering without a separate per-table sequence table.
  2. next_attempt_at lets Sync Service implement exponential backoff
     without a separate scheduling table.
  3. Common Keys (run_id / environment / code_version / config_version)
     are nullable but enqueue-time best-effort.  Secondary marts can be
     filtered by run / config without joining back to Primary.
  4. payload_json is sa.JSON which adapts to JSONB on PostgreSQL and TEXT
     on SQLite; payload IS sanitized BEFORE enqueue (F-12) so the column
     is intentionally schema-less.
  5. Indexes are non-partial (portable to SQLite).  PostgreSQL deployments
     may add partial indexes manually as a perf tuning step without
     altering this contract.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_secondary_sync_outbox"
down_revision: Union[str, None] = "0012_dashboard_top_candidates_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "secondary_sync_outbox",
        # --- Identity -----------------------------------------------------
        sa.Column("outbox_id", sa.Text, primary_key=True),  # ULID
        # --- Routing / idempotency key on Sink side (F-3) -----------------
        sa.Column("table_name", sa.Text, nullable=False),
        sa.Column(
            "primary_key",
            sa.Text,
            nullable=False,
            comment="JSON-encoded composite PK string, e.g. "
            '\'["EUR_USD","2026-04-20T00:00:00Z"]\'',
        ),
        sa.Column(
            "version_no",
            sa.BigInteger,
            nullable=False,
            server_default="0",
        ),
        # --- Payload (sanitized BEFORE enqueue per F-12) ------------------
        sa.Column("payload_json", sa.JSON, nullable=False),
        # --- Lifecycle (F-2 outbox + at-least-once + backoff) -------------
        sa.Column(
            "enqueued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("acked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column(
            "attempt_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        # --- Common Keys (schema_catalog principle 1.3) -------------------
        sa.Column("run_id", sa.Text, nullable=True),
        sa.Column("environment", sa.Text, nullable=True),
        sa.Column("code_version", sa.Text, nullable=True),
        sa.Column("config_version", sa.Text, nullable=True),
    )
    # Worker poll: WHERE acked_at IS NULL [AND next_attempt_at <= now()]
    #              ORDER BY enqueued_at LIMIT N
    op.create_index(
        "ix_secondary_sync_outbox_pending",
        "secondary_sync_outbox",
        ["acked_at", "next_attempt_at", "enqueued_at"],
    )
    # Logical-key lookup: observability + de-dup queries
    op.create_index(
        "ix_secondary_sync_outbox_logical_key",
        "secondary_sync_outbox",
        ["table_name", "primary_key", "version_no"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_secondary_sync_outbox_logical_key",
        table_name="secondary_sync_outbox",
    )
    op.drop_index(
        "ix_secondary_sync_outbox_pending",
        table_name="secondary_sync_outbox",
    )
    op.drop_table("secondary_sync_outbox")
