"""group i: operations (system_jobs, app_runtime_state, outbox_events,
notification_outbox, supervisor_events, app_settings_changes)

Revision ID: 0009_group_i_operations
Revises: 0008_group_h_aggregates
Create Date: 2026-04-18

Creates D1 section 2.1.I (Operations, 6 tables):

  #37 system_jobs          — batch/learning/aggregator job execution history (MUT)
  #38 app_runtime_state    — Supervisor persistent snapshot for restart reconciliation (AO)
  #39 outbox_events        — order dispatch Outbox queue (MUT, D1 6.6)
  #40 notification_outbox  — non-critical notification Outbox (MUT, D1 6.13)
  #41 supervisor_events    — Supervisor lifecycle / safe_stop / config events (AO)
  #42 app_settings_changes — full audit trail for app_settings mutations (AO)

External FK dependencies:
  - outbox_events.order_id -> orders (0006 Group E), nullable per D1 2.1-I-1:
    the outbox row is written *before* HTTP dispatch, so order_id is always
    set at write time — but nullable to tolerate edge cases in reconciliation.

Critical constraint (D1 2.1-I-2):
  outbox_events and notification_outbox are non-persistent (D5); dispatched
  entries may be directly DELETEd after Hot 30d / Warm 90d.
  The schema itself imposes no retention enforcement (handled by application).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009_group_i_operations"
down_revision: Union[str, None] = "0008_group_h_aggregates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- system_jobs (D1 2.1.I #37, MUT, Operations long-term) ---
    # Covers batch, learning, aggregator, cold-archive job runs.
    # status FSM: pending -> running -> success | failed | canceled
    op.create_table(
        "system_jobs",
        sa.Column("system_job_id", sa.Text, primary_key=True),
        sa.Column("job_type", sa.Text, nullable=False),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default="pending",
        ),  # 'pending'|'running'|'success'|'failed'|'canceled'
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_params", sa.JSON, nullable=True),
        sa.Column("result_summary", sa.JSON, nullable=True),
        sa.Column("error_detail", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_system_jobs_job_type", "system_jobs", ["job_type"])
    op.create_index("ix_system_jobs_status", "system_jobs", ["status"])

    # --- app_runtime_state (D1 2.1.I #38, AO, direct 30d + history) ---
    # Persistent snapshot written by Supervisor; used as restart reconciliation
    # starting point (not the in-memory authoritative state).
    op.create_table(
        "app_runtime_state",
        sa.Column("snapshot_id", sa.Text, primary_key=True),
        sa.Column("snapshot_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supervisor_state", sa.JSON, nullable=True),
        sa.Column("active_orders", sa.JSON, nullable=True),
        sa.Column("config_version", sa.Text, nullable=True),
        sa.Column("run_id", sa.Text, nullable=True),
    )
    op.create_index(
        "ix_app_runtime_state_snapshot_time",
        "app_runtime_state",
        ["snapshot_time_utc"],
    )

    # --- outbox_events (D1 2.1.I #39, MUT, Outbox short-term) ---
    # Order dispatch Outbox per D1 6.6. Written atomically with orders row
    # in the same transaction. status FSM: pending -> dispatching -> acked | failed
    op.create_table(
        "outbox_events",
        sa.Column("outbox_event_id", sa.Text, primary_key=True),
        sa.Column(
            "order_id",
            sa.Text,
            sa.ForeignKey("orders.order_id"),
            nullable=True,
        ),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default="pending",
        ),  # 'pending'|'dispatching'|'acked'|'failed'
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column("dispatch_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"])
    op.create_index("ix_outbox_events_order_id", "outbox_events", ["order_id"])

    # --- notification_outbox (D1 2.1.I #40, MUT, Outbox short-term) ---
    # Non-critical notifications only (D1 6.13); critical notifications bypass
    # this table and are sent synchronously.
    op.create_table(
        "notification_outbox",
        sa.Column("notification_outbox_id", sa.Text, primary_key=True),
        sa.Column("channel", sa.Text, nullable=False),  # 'slack'|'file'
        sa.Column("severity", sa.Text, nullable=False),  # 'info'|'warn'|'error'
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default="pending",
        ),  # 'pending'|'dispatching'|'sent'|'failed'
        sa.Column("dispatch_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_notification_outbox_status", "notification_outbox", ["status"]
    )

    # --- supervisor_events (D1 2.1.I #41, AO, Supervisor/Reconciler permanent) ---
    # All Supervisor lifecycle events: startup steps, safe_stop, config_version
    # computation, account_type checks, health checks.
    op.create_table(
        "supervisor_events",
        sa.Column("supervisor_event_id", sa.Text, primary_key=True),
        sa.Column("event_type", sa.Text, nullable=False),
        sa.Column("run_id", sa.Text, nullable=True),
        sa.Column("config_version", sa.Text, nullable=True),
        sa.Column("source_breakdown", sa.JSON, nullable=True),
        sa.Column("detail", sa.JSON, nullable=True),
        sa.Column("event_time_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_supervisor_events_event_type", "supervisor_events", ["event_type"]
    )
    op.create_index(
        "ix_supervisor_events_run_id", "supervisor_events", ["run_id"]
    )

    # --- app_settings_changes (D1 2.1.I #42, AO, Reference permanent) ---
    # Full audit trail for every app_settings mutation.
    op.create_table(
        "app_settings_changes",
        sa.Column("app_settings_change_id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("old_value", sa.Text, nullable=True),
        sa.Column("new_value", sa.Text, nullable=False),
        sa.Column("changed_by", sa.Text, nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_app_settings_changes_name", "app_settings_changes", ["name"]
    )


def downgrade() -> None:
    op.drop_index("ix_app_settings_changes_name", table_name="app_settings_changes")
    op.drop_table("app_settings_changes")
    op.drop_index("ix_supervisor_events_run_id", table_name="supervisor_events")
    op.drop_index("ix_supervisor_events_event_type", table_name="supervisor_events")
    op.drop_table("supervisor_events")
    op.drop_index("ix_notification_outbox_status", table_name="notification_outbox")
    op.drop_table("notification_outbox")
    op.drop_index("ix_outbox_events_order_id", table_name="outbox_events")
    op.drop_index("ix_outbox_events_status", table_name="outbox_events")
    op.drop_table("outbox_events")
    op.drop_index(
        "ix_app_runtime_state_snapshot_time", table_name="app_runtime_state"
    )
    op.drop_table("app_runtime_state")
    op.drop_index("ix_system_jobs_status", table_name="system_jobs")
    op.drop_index("ix_system_jobs_job_type", table_name="system_jobs")
    op.drop_table("system_jobs")
