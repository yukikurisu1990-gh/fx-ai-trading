"""group g: safety and observability (9 tables)

Revision ID: 0007_group_g_safety_observability
Revises: 0006_group_ef_execution_outcome
Create Date: 2026-04-18

Creates D1 section 2.1.G (Safety & Observability, 9 tables):

  #25 no_trade_events      — no-trade decisions with 6.16 taxonomy (AO)
  #26 drift_events         — model/feature drift detection events (AO)
  #27 account_snapshots    — balance/margin/PnL snapshots (AO)
  #28 risk_events          — RiskManager accept/reject records (AO)
  #29 stream_status        — pricing/transaction stream state changes (AO)
  #30 data_quality_events  — input data quality incidents (AO)
  #31 reconciliation_events— Reconciler Action Matrix execution records (AO)
  #32 retry_events         — all retry attempts across components (AO)
  #33 anomalies            — general application anomalies (AO)

External FK dependencies (all satisfied by prior revisions):
  - account_snapshots.account_id  -> accounts        (0001 Group A)
  - drift_events.model_id         -> model_registry  (0004 Group C)
  - no_trade_events / risk_events / others use cycle_id as Text (no FK table)

All tables are Append-Only (AO). No MUT state machines in this group.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_group_g_safety_observability"
down_revision: Union[str, None] = "0006_group_ef_execution_outcome"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- no_trade_events (D1 2.1.G #25, AO, Observability) ---
    # Taxonomy: reason_category / reason_code / reason_detail per D1 6.16.
    # source_component identifies which layer raised the no-trade (Filter / Risk / Supervisor).
    op.create_table(
        "no_trade_events",
        sa.Column("no_trade_event_id", sa.Text, primary_key=True),
        sa.Column("cycle_id", sa.Text, nullable=True),
        sa.Column("meta_decision_id", sa.Text, nullable=True),
        sa.Column("reason_category", sa.Text, nullable=False),
        sa.Column("reason_code", sa.Text, nullable=False),
        sa.Column("reason_detail", sa.Text, nullable=True),
        sa.Column("source_component", sa.Text, nullable=False),
        sa.Column("instrument", sa.Text, nullable=True),
        sa.Column("strategy_id", sa.Text, nullable=True),
        sa.Column("event_time_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_no_trade_events_cycle_id", "no_trade_events", ["cycle_id"])
    op.create_index(
        "ix_no_trade_events_reason_category",
        "no_trade_events",
        ["reason_category"],
    )

    # --- drift_events (D1 2.1.G #26, AO, Observability) ---
    # Covers PSI / KL / residual drift. model_id FK -> model_registry (0004).
    op.create_table(
        "drift_events",
        sa.Column("drift_event_id", sa.Text, primary_key=True),
        sa.Column(
            "model_id",
            sa.Text,
            sa.ForeignKey("model_registry.model_id"),
            nullable=True,
        ),
        sa.Column("drift_type", sa.Text, nullable=False),  # 'psi'|'kl'|'residual'|'feature'
        sa.Column("metric_name", sa.Text, nullable=True),
        sa.Column("drift_score", sa.Numeric(10, 6), nullable=True),
        sa.Column("threshold", sa.Numeric(10, 6), nullable=True),
        sa.Column("severity", sa.Text, nullable=True),  # 'warn'|'critical'
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_drift_events_model_id", "drift_events", ["model_id"])

    # --- account_snapshots (D1 2.1.G #27, AO, Execution/Audit) ---
    # trigger_reason enumerates what caused the snapshot (D1 section description).
    op.create_table(
        "account_snapshots",
        sa.Column("account_snapshot_id", sa.Text, primary_key=True),
        sa.Column(
            "account_id",
            sa.Text,
            sa.ForeignKey("accounts.account_id"),
            nullable=False,
        ),
        sa.Column("balance", sa.Numeric(18, 8), nullable=True),
        sa.Column("nav", sa.Numeric(18, 8), nullable=True),
        sa.Column("unrealized_pl", sa.Numeric(18, 8), nullable=True),
        sa.Column("margin_used", sa.Numeric(18, 8), nullable=True),
        sa.Column("margin_available", sa.Numeric(18, 8), nullable=True),
        sa.Column(
            "trigger_reason",
            sa.Text,
            nullable=False,
        ),  # 'order'|'fill'|'close'|'hourly'|'daily_close'|'manual'
        sa.Column("snapshot_time_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_account_snapshots_account_id", "account_snapshots", ["account_id"]
    )
    op.create_index(
        "ix_account_snapshots_snapshot_time",
        "account_snapshots",
        ["snapshot_time_utc"],
    )

    # --- risk_events (D1 2.1.G #28, AO, Observability) ---
    # RiskManager.accept / reject per judgment call.
    op.create_table(
        "risk_events",
        sa.Column("risk_event_id", sa.Text, primary_key=True),
        sa.Column("cycle_id", sa.Text, nullable=True),
        sa.Column("instrument", sa.Text, nullable=True),
        sa.Column("strategy_id", sa.Text, nullable=True),
        sa.Column("verdict", sa.Text, nullable=False),  # 'accept'|'reject'
        sa.Column("constraint_violated", sa.Text, nullable=True),
        sa.Column("detail", sa.JSON, nullable=True),
        sa.Column("event_time_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_risk_events_cycle_id", "risk_events", ["cycle_id"])

    # --- stream_status (D1 2.1.G #29, AO, Observability) ---
    # Pricing / transaction stream connection state transitions.
    op.create_table(
        "stream_status",
        sa.Column("stream_status_id", sa.Text, primary_key=True),
        sa.Column("stream_type", sa.Text, nullable=False),  # 'pricing'|'transaction'
        sa.Column("instrument", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
        ),  # 'connected'|'heartbeat'|'gap'|'reconnect'|'disconnected'
        sa.Column("event_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail", sa.JSON, nullable=True),
    )
    op.create_index(
        "ix_stream_status_stream_type", "stream_status", ["stream_type"]
    )

    # --- data_quality_events (D1 2.1.G #30, AO, Observability) ---
    # Input data quality incidents (stale price / gap / type anomaly / mismatch).
    op.create_table(
        "data_quality_events",
        sa.Column("data_quality_event_id", sa.Text, primary_key=True),
        sa.Column("quality_issue_type", sa.Text, nullable=False),
        sa.Column("instrument", sa.Text, nullable=True),
        sa.Column("source_component", sa.Text, nullable=True),
        sa.Column("detail", sa.JSON, nullable=True),
        sa.Column("event_time_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_data_quality_events_type", "data_quality_events", ["quality_issue_type"]
    )

    # --- reconciliation_events (D1 2.1.G #31, AO, Supervisor/Reconciler) ---
    # Reconciler Action Matrix (6.12) case execution records.
    # trigger_reason: 'startup'|'midrun_heartbeat_gap'|'periodic_drift_check'
    op.create_table(
        "reconciliation_events",
        sa.Column("reconciliation_event_id", sa.Text, primary_key=True),
        sa.Column("trigger_reason", sa.Text, nullable=False),
        sa.Column("action_taken", sa.Text, nullable=False),
        sa.Column("order_id", sa.Text, nullable=True),
        sa.Column("position_snapshot_id", sa.Text, nullable=True),
        sa.Column("detail", sa.JSON, nullable=True),
        sa.Column("event_time_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_reconciliation_events_trigger",
        "reconciliation_events",
        ["trigger_reason"],
    )

    # --- retry_events (D1 2.1.G #32, AO, Observability) ---
    # Universal retry log: caller, endpoint, attempt number, backoff, outcome.
    op.create_table(
        "retry_events",
        sa.Column("retry_event_id", sa.Text, primary_key=True),
        sa.Column("caller", sa.Text, nullable=False),
        sa.Column("endpoint", sa.Text, nullable=True),
        sa.Column("attempt", sa.Integer, nullable=False),
        sa.Column("backoff_ms", sa.Integer, nullable=True),
        sa.Column("outcome", sa.Text, nullable=False),  # 'success'|'failure'|'giving_up'
        sa.Column("error_type", sa.Text, nullable=True),
        sa.Column("event_time_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_retry_events_caller", "retry_events", ["caller"])

    # --- anomalies (D1 2.1.G #33, AO, Observability) ---
    # General application anomalies; distinct from data_quality and reconciliation.
    op.create_table(
        "anomalies",
        sa.Column("anomaly_id", sa.Text, primary_key=True),
        sa.Column("anomaly_type", sa.Text, nullable=False),
        sa.Column("source_component", sa.Text, nullable=False),
        sa.Column("severity", sa.Text, nullable=True),  # 'warn'|'error'|'critical'
        sa.Column("correlation_id", sa.Text, nullable=True),
        sa.Column("detail", sa.JSON, nullable=True),
        sa.Column("event_time_utc", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_anomalies_source_component", "anomalies", ["source_component"]
    )
    op.create_index("ix_anomalies_severity", "anomalies", ["severity"])


def downgrade() -> None:
    op.drop_index("ix_anomalies_severity", table_name="anomalies")
    op.drop_index("ix_anomalies_source_component", table_name="anomalies")
    op.drop_table("anomalies")
    op.drop_index("ix_retry_events_caller", table_name="retry_events")
    op.drop_table("retry_events")
    op.drop_index(
        "ix_reconciliation_events_trigger", table_name="reconciliation_events"
    )
    op.drop_table("reconciliation_events")
    op.drop_index("ix_data_quality_events_type", table_name="data_quality_events")
    op.drop_table("data_quality_events")
    op.drop_index("ix_stream_status_stream_type", table_name="stream_status")
    op.drop_table("stream_status")
    op.drop_index("ix_risk_events_cycle_id", table_name="risk_events")
    op.drop_table("risk_events")
    op.drop_index(
        "ix_account_snapshots_snapshot_time", table_name="account_snapshots"
    )
    op.drop_index("ix_account_snapshots_account_id", table_name="account_snapshots")
    op.drop_table("account_snapshots")
    op.drop_index("ix_drift_events_model_id", table_name="drift_events")
    op.drop_table("drift_events")
    op.drop_index(
        "ix_no_trade_events_reason_category", table_name="no_trade_events"
    )
    op.drop_index("ix_no_trade_events_cycle_id", table_name="no_trade_events")
    op.drop_table("no_trade_events")
