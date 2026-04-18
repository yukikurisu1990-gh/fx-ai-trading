"""group c: learning / models (training_runs, model_registry, model_evaluations, predictions)

Revision ID: 0004_group_c_learning_models
Revises: 0003_group_b_market_data
Create Date: 2026-04-18

Creates D1 section 2.1.C (Learning / Models, 4 tables).

model_registry and training_runs have a mutual reference:
  - training_runs.model_id  -> model_registry (nullable FK)
  - model_registry.training_run_id -> training_runs (added via ALTER after both tables exist)

Resolution: create model_registry first (without FK to training_runs), then
training_runs (FK to model_registry), then add the reverse FK via
op.create_foreign_key. This avoids deferred constraints and keeps both
tables consistent from the first upgrade.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_group_c_learning_models"
down_revision: Union[str, None] = "0003_group_b_market_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- model_registry (D1 2.1.C #9, MUT, Reference permanent) ---
    # Created first because training_runs.model_id references it.
    # The reverse FK (model_registry.training_run_id -> training_runs) is
    # added after training_runs is created.
    op.create_table(
        "model_registry",
        sa.Column("model_id", sa.Text, primary_key=True),
        # training_run_id FK is added below via op.create_foreign_key
        sa.Column("training_run_id", sa.Text, nullable=True),
        sa.Column("model_type", sa.Text, nullable=False),  # e.g. 'ai_strategy'
        sa.Column("model_version", sa.Text, nullable=False),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default="shadow",
        ),  # 'active'|'shadow'|'review'|'demoted'
        sa.Column("artifact_path", sa.Text, nullable=True),
        sa.Column("meta", sa.JSON, nullable=True),
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

    # --- training_runs (D1 2.1.C #8, AO with status transitions) ---
    # experiment_id is a UUID label with no FK target table in Phase 6.
    # model_id is nullable: a run may finish before a model is registered.
    op.create_table(
        "training_runs",
        sa.Column("training_run_id", sa.Text, primary_key=True),
        sa.Column("experiment_id", sa.Text, nullable=True),
        sa.Column(
            "model_id",
            sa.Text,
            sa.ForeignKey("model_registry.model_id"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Text,
            nullable=False,
            server_default="pending",
        ),  # 'pending'|'running'|'success'|'failed'
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_params", sa.JSON, nullable=True),
        sa.Column("artifact_path", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Add the reverse FK now that training_runs exists.
    op.create_foreign_key(
        "fk_model_registry_training_run_id",
        "model_registry",
        "training_runs",
        ["training_run_id"],
        ["training_run_id"],
    )

    # --- model_evaluations (D1 2.1.C #10, AO, Learning artifacts) ---
    op.create_table(
        "model_evaluations",
        sa.Column("evaluation_id", sa.Text, primary_key=True),
        sa.Column(
            "model_id",
            sa.Text,
            sa.ForeignKey("model_registry.model_id"),
            nullable=False,
        ),
        sa.Column(
            "training_run_id",
            sa.Text,
            sa.ForeignKey("training_runs.training_run_id"),
            nullable=True,
        ),
        sa.Column(
            "evaluation_type",
            sa.Text,
            nullable=False,
        ),  # 'oos'|'walk_forward'|'brier'|'shadow'
        sa.Column("is_shadow", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metrics", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # --- predictions (D1 2.1.C #11, AO, Decision logs) ---
    # PK: (model_id, cycle_id, instrument) per D1 table 11.
    # feature_version required per D1 3.2 (Common Keys for Learning-derived tables).
    op.create_table(
        "predictions",
        sa.Column(
            "model_id",
            sa.Text,
            sa.ForeignKey("model_registry.model_id"),
            nullable=False,
        ),
        sa.Column("cycle_id", sa.Text, nullable=False),
        sa.Column(
            "instrument",
            sa.Text,
            sa.ForeignKey("instruments.instrument"),
            nullable=False,
        ),
        sa.Column("strategy_id", sa.Text, nullable=False),
        sa.Column("predicted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prediction", sa.Numeric(18, 8), nullable=False),
        sa.Column("confidence", sa.Numeric(6, 4), nullable=True),
        sa.Column("feature_version", sa.Text, nullable=True),
        sa.Column("experiment_id", sa.Text, nullable=True),
        sa.PrimaryKeyConstraint("model_id", "cycle_id", "instrument"),
    )

    op.create_index("ix_predictions_cycle_id", "predictions", ["cycle_id"])
    op.create_index("ix_predictions_instrument", "predictions", ["instrument"])


def downgrade() -> None:
    op.drop_index("ix_predictions_instrument", table_name="predictions")
    op.drop_index("ix_predictions_cycle_id", table_name="predictions")
    op.drop_table("predictions")
    op.drop_table("model_evaluations")
    # Drop the reverse FK before dropping training_runs
    op.drop_constraint(
        "fk_model_registry_training_run_id", "model_registry", type_="foreignkey"
    )
    op.drop_table("training_runs")
    op.drop_table("model_registry")
