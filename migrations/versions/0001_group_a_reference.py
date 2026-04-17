"""initial reference schema (group A: brokers, accounts, instruments, app_settings)

Revision ID: 0001_group_a_reference
Revises:
Create Date: 2026-04-17

Creates the Config/Reference group of D1 schema_catalog.md section 2.1.A.
Table seed data (including Phase 6.5 initial parameters for app_settings) is
intentionally NOT inserted here — it belongs to a follow-up cycle.

This revision uses direct ``op.create_table`` rather than SQLAlchemy model
subclasses. Cycle 15 deliberately avoids the ORM layer to stay within
scope (no Repository / CRUD / Service). Cycle 16+ will add model classes
that subclass ``fx_ai_trading.db.base.Base`` so autogenerate can diff
future schema changes.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_group_a_reference"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- brokers (D1 2.1.A #1, Reference permanent) ---
    op.create_table(
        "brokers",
        sa.Column("broker_id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("api_base_url", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- accounts (D1 2.1.A #2, FK -> brokers, account_type enforces 6.18) ---
    op.create_table(
        "accounts",
        sa.Column("account_id", sa.Text, primary_key=True),
        sa.Column(
            "broker_id",
            sa.Text,
            sa.ForeignKey("brokers.broker_id"),
            nullable=False,
        ),
        sa.Column("account_type", sa.Text, nullable=False),  # 'demo' | 'live' (Phase 6.18)
        sa.Column("base_currency", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- instruments (D1 2.1.A #3, Reference permanent) ---
    op.create_table(
        "instruments",
        sa.Column("instrument", sa.Text, primary_key=True),
        sa.Column("base_currency", sa.Text, nullable=False),
        sa.Column("quote_currency", sa.Text, nullable=False),
        sa.Column("pip_location", sa.Integer, nullable=False),
        sa.Column("min_trade_units", sa.Integer, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- app_settings (D1 2.1.A #4, schema only; Phase 6.5 seed is NEXT cycle) ---
    op.create_table(
        "app_settings",
        sa.Column("name", sa.Text, primary_key=True),
        sa.Column("value", sa.Text, nullable=False),
        sa.Column("type", sa.Text, nullable=False),  # 'float'|'int'|'bool'|'string'|'json'
        sa.Column("introduced_in_version", sa.Text, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    # Drop in reverse dependency order: accounts before brokers (FK).
    op.drop_table("app_settings")
    op.drop_table("instruments")
    op.drop_table("accounts")
    op.drop_table("brokers")
