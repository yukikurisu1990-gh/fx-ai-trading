"""group b: market data (candles, ticks/events, economic_events)

Revision ID: 0003_group_b_market_data
Revises: 0002_app_settings_initial_values
Create Date: 2026-04-17

Creates D1 section 2.1.B (Market Data, 3 tables). FKs link instrument
columns to the reference master. market_ticks_or_events uses a single
table with a ``type`` column per Designer Decision 2.1-B-1 (split into
two physical tables remains a Phase 7 option).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_group_b_market_data"
down_revision: Union[str, None] = "0002_app_settings_initial_values"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- market_candles (D1 2.1.B #5, Market raw tiered) ---
    op.create_table(
        "market_candles",
        sa.Column(
            "instrument",
            sa.Text,
            sa.ForeignKey("instruments.instrument"),
            nullable=False,
        ),
        sa.Column("tier", sa.Text, nullable=False),  # '1m' | '5m' | '1h' etc.
        sa.Column("event_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(18, 8), nullable=False),
        sa.Column("high", sa.Numeric(18, 8), nullable=False),
        sa.Column("low", sa.Numeric(18, 8), nullable=False),
        sa.Column("close", sa.Numeric(18, 8), nullable=False),
        sa.Column("volume", sa.BigInteger, nullable=True),
        sa.Column(
            "received_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("instrument", "tier", "event_time_utc"),
    )

    # --- market_ticks_or_events (D1 2.1.B #6, single table + type column) ---
    op.create_table(
        "market_ticks_or_events",
        sa.Column(
            "instrument",
            sa.Text,
            sa.ForeignKey("instruments.instrument"),
            nullable=False,
        ),
        sa.Column("event_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_seq", sa.BigInteger, nullable=False),
        sa.Column("type", sa.Text, nullable=False),  # 'tick'|'pricing'|'stream_gap'|'heartbeat'|'reconnect'
        sa.Column("bid", sa.Numeric(18, 8), nullable=True),
        sa.Column("ask", sa.Numeric(18, 8), nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),  # heterogenous per type
        sa.Column(
            "received_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("instrument", "event_time_utc", "event_seq"),
    )

    # --- economic_events (D1 2.1.B #7, Reference long-term) ---
    op.create_table(
        "economic_events",
        sa.Column("event_id", sa.Text, primary_key=True),
        sa.Column("scheduled_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("country", sa.Text, nullable=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("impact", sa.Text, nullable=True),  # 'high'|'medium'|'low'
        sa.Column("actual", sa.Text, nullable=True),
        sa.Column("forecast", sa.Text, nullable=True),
        sa.Column("previous", sa.Text, nullable=True),
        sa.Column("source", sa.Text, nullable=True),
        sa.Column(
            "last_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("economic_events")
    op.drop_table("market_ticks_or_events")
    op.drop_table("market_candles")
