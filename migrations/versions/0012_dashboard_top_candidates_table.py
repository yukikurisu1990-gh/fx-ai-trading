"""migration 0012: create dashboard_top_candidates mart table (M20).

This table stores the TSS-ranked top trade candidates refreshed every 15 minutes
by MartScheduler.  The M19 top_candidates panel reads from this table; until M20
runs, the panel returns [].

group: H (Aggregates)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0012_dashboard_top_candidates_table"
down_revision: str | None = "0011_app_settings_phase_mode_seed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dashboard_top_candidates",
        sa.Column("candidate_id", sa.Text, primary_key=True),
        sa.Column("instrument", sa.Text, nullable=False),
        sa.Column("strategy_id", sa.Text, nullable=False),
        sa.Column("tss_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("direction", sa.Text, nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rank", sa.Integer, nullable=False),
    )
    op.create_index(
        "ix_dashboard_top_candidates_rank",
        "dashboard_top_candidates",
        ["rank"],
    )


def downgrade() -> None:
    op.drop_index("ix_dashboard_top_candidates_rank", table_name="dashboard_top_candidates")
    op.drop_table("dashboard_top_candidates")
