"""group h: aggregates (strategy_performance, meta_strategy_evaluations, daily_metrics)

Revision ID: 0008_group_h_aggregates
Revises: 0007_group_g_safety_observability
Create Date: 2026-04-18

Creates D1 section 2.1.H (Aggregates, 3 tables):

  #34 strategy_performance       — per-strategy roll-up (UPS), window × strategy × instrument
  #35 meta_strategy_evaluations  — meta-strategy selection accuracy (UPS), window × version
  #36 daily_metrics              — daily KPI roll-up (UPS), date × account

All three are Upsert (UPS): the Aggregator recalculates idempotently and
writes the result back under the same composite PK (D1 4.3, Inherited
Constraint 2.1-H-1).

External FK dependencies:
  - strategy_performance.instrument -> instruments (0001 Group A)
  - daily_metrics.account_id        -> accounts    (0001 Group A)
  - meta_strategy_evaluations       -> no external FKs
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_group_h_aggregates"
down_revision: Union[str, None] = "0007_group_g_safety_observability"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- strategy_performance (D1 2.1.H #34, UPS, Aggregates permanent) ---
    # PK: (window_class, window_start, strategy_type, strategy_version, instrument)
    # Aggregator writes idempotently; same PK → replace values (upsert).
    op.create_table(
        "strategy_performance",
        sa.Column("window_class", sa.Text, nullable=False),  # 'daily'|'weekly'|'monthly'
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("strategy_type", sa.Text, nullable=False),
        sa.Column("strategy_version", sa.Text, nullable=False),
        sa.Column(
            "instrument",
            sa.Text,
            sa.ForeignKey("instruments.instrument"),
            nullable=False,
        ),
        sa.Column("trade_count", sa.Integer, nullable=True),
        sa.Column("win_rate", sa.Numeric(6, 4), nullable=True),
        sa.Column("avg_pnl", sa.Numeric(18, 8), nullable=True),
        sa.Column("total_pnl", sa.Numeric(18, 8), nullable=True),
        sa.Column("sharpe_ratio", sa.Numeric(10, 6), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(10, 6), nullable=True),
        sa.Column("aggregated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "window_class", "window_start", "strategy_type", "strategy_version", "instrument"
        ),
    )
    op.create_index(
        "ix_strategy_performance_window",
        "strategy_performance",
        ["window_class", "window_start"],
    )

    # --- meta_strategy_evaluations (D1 2.1.H #35, UPS, Aggregates permanent) ---
    # PK: (window_class, window_start, meta_strategy_version)
    # meta_eval_protocol_version required per D1 6.11.
    op.create_table(
        "meta_strategy_evaluations",
        sa.Column("window_class", sa.Text, nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta_strategy_version", sa.Text, nullable=False),
        sa.Column("meta_eval_protocol_version", sa.Text, nullable=False),  # D1 6.11
        sa.Column("selection_accuracy", sa.Numeric(6, 4), nullable=True),
        sa.Column("counterfactual_pnl", sa.Numeric(18, 8), nullable=True),
        sa.Column("metrics", sa.JSON, nullable=True),
        sa.Column("aggregated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint(
            "window_class", "window_start", "meta_strategy_version"
        ),
    )

    # --- daily_metrics (D1 2.1.H #36, UPS, Aggregates permanent) ---
    # PK: (date_utc, account_id). One row per calendar day × account.
    op.create_table(
        "daily_metrics",
        sa.Column("date_utc", sa.Date, nullable=False),
        sa.Column(
            "account_id",
            sa.Text,
            sa.ForeignKey("accounts.account_id"),
            nullable=False,
        ),
        sa.Column("realized_pnl", sa.Numeric(18, 8), nullable=True),
        sa.Column("unrealized_pnl", sa.Numeric(18, 8), nullable=True),
        sa.Column("max_drawdown", sa.Numeric(10, 6), nullable=True),
        sa.Column("exposure", sa.Numeric(18, 8), nullable=True),
        sa.Column("trade_count", sa.Integer, nullable=True),
        sa.Column("rejection_count", sa.Integer, nullable=True),
        sa.Column("no_trade_count", sa.Integer, nullable=True),
        sa.Column("aggregated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("date_utc", "account_id"),
    )
    op.create_index(
        "ix_daily_metrics_date_utc", "daily_metrics", ["date_utc"]
    )


def downgrade() -> None:
    op.drop_index("ix_daily_metrics_date_utc", table_name="daily_metrics")
    op.drop_table("daily_metrics")
    op.drop_table("meta_strategy_evaluations")
    op.drop_index("ix_strategy_performance_window", table_name="strategy_performance")
    op.drop_table("strategy_performance")
