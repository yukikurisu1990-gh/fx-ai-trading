"""group d: decision pipeline (strategy_signals through correlation_snapshots)

Revision ID: 0005_group_d_decision_pipeline
Revises: 0004_group_c_learning_models
Create Date: 2026-04-18

Creates D1 section 2.1.D (Decision Pipeline, 7 tables):
  #12 strategy_signals       — all strategy × candidate signals (AO)
  #13 pair_selection_runs    — MetaDecider Select stage summary (AO)
  #14 pair_selection_scores  — per-candidate score detail (AO)
  #15 meta_decisions         — Filter/Score/Select 3-stage snapshot (AO)
  #16 feature_snapshots      — per-cycle feature snapshot (AO, compact_mode)
  #17 ev_breakdowns          — EV decomposition per candidate (AO)
  #18 correlation_snapshots  — short/long window correlation matrix (AO)

cycle_id is a propagated Common Key (UUID/ULID), not a FK to a "cycles"
table (no such table exists in the D1 schema). It is stored as Text.

Creation order within the revision:
  1. meta_decisions       — no intra-group FKs
  2. strategy_signals     — no intra-group FKs
  3. pair_selection_runs  — no intra-group FKs
  4. pair_selection_scores— FK -> pair_selection_runs (created above)
  5. feature_snapshots    — no intra-group FKs
  6. ev_breakdowns        — no intra-group FKs
  7. correlation_snapshots— no FKs at all

meta_decisions is created first because trading_signals (Group E, next
revision) will reference meta_decision_id.
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_group_d_decision_pipeline"
down_revision: Union[str, None] = "0004_group_c_learning_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- meta_decisions (D1 2.1.D #15, AO, Decision logs) ---
    # Created first: trading_signals (Group E) has FK -> meta_decision_id.
    # 3-stage snapshot: Filter / Score / Select results + 6.7 / 6.17 / 6.8 fields.
    op.create_table(
        "meta_decisions",
        sa.Column("meta_decision_id", sa.Text, primary_key=True),
        sa.Column("cycle_id", sa.Text, nullable=False),
        sa.Column("filter_result", sa.JSON, nullable=True),
        sa.Column("score_contributions", sa.JSON, nullable=True),  # D1 6.7
        sa.Column("active_strategies", sa.JSON, nullable=True),   # D1 6.17
        sa.Column("regime_detected", sa.Text, nullable=True),     # D1 6.8
        sa.Column("decision_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("no_trade_reason", sa.Text, nullable=True),
    )
    op.create_index("ix_meta_decisions_cycle_id", "meta_decisions", ["cycle_id"])

    # --- strategy_signals (D1 2.1.D #12, AO, Decision logs) ---
    # PK: (cycle_id, instrument, strategy_id) — all signals, accepted or not.
    op.create_table(
        "strategy_signals",
        sa.Column("cycle_id", sa.Text, nullable=False),
        sa.Column(
            "instrument",
            sa.Text,
            sa.ForeignKey("instruments.instrument"),
            nullable=False,
        ),
        sa.Column("strategy_id", sa.Text, nullable=False),
        sa.Column("strategy_type", sa.Text, nullable=False),
        sa.Column("strategy_version", sa.Text, nullable=True),
        sa.Column("signal_direction", sa.Text, nullable=False),  # 'buy'|'sell'|'no_trade'
        sa.Column("confidence", sa.Numeric(6, 4), nullable=True),
        sa.Column("signal_time_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("meta", sa.JSON, nullable=True),
        sa.PrimaryKeyConstraint("cycle_id", "instrument", "strategy_id"),
    )
    op.create_index("ix_strategy_signals_cycle_id", "strategy_signals", ["cycle_id"])

    # --- pair_selection_runs (D1 2.1.D #13, AO, Decision logs) ---
    # 1 row per MetaDecider Select execution.
    op.create_table(
        "pair_selection_runs",
        sa.Column("selection_run_id", sa.Text, primary_key=True),
        sa.Column("cycle_id", sa.Text, nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("selected_instruments", sa.JSON, nullable=True),
        sa.Column("selection_params", sa.JSON, nullable=True),
    )
    op.create_index(
        "ix_pair_selection_runs_cycle_id", "pair_selection_runs", ["cycle_id"]
    )

    # --- pair_selection_scores (D1 2.1.D #14, AO, Decision logs) ---
    # PK: (selection_run_id, instrument, strategy_id)
    # FK -> pair_selection_runs created above.
    op.create_table(
        "pair_selection_scores",
        sa.Column(
            "selection_run_id",
            sa.Text,
            sa.ForeignKey("pair_selection_runs.selection_run_id"),
            nullable=False,
        ),
        sa.Column(
            "instrument",
            sa.Text,
            sa.ForeignKey("instruments.instrument"),
            nullable=False,
        ),
        sa.Column("strategy_id", sa.Text, nullable=False),
        sa.Column("score", sa.Numeric(10, 6), nullable=False),
        sa.Column("score_components", sa.JSON, nullable=True),
        sa.PrimaryKeyConstraint("selection_run_id", "instrument", "strategy_id"),
    )

    # --- feature_snapshots (D1 2.1.D #16, AO, Decision logs) ---
    # PK: (cycle_id, instrument). feature_version required (D1 3.2, 6.10).
    # compact_mode=True by default (6.10): stores hash + stats + sampled subset.
    op.create_table(
        "feature_snapshots",
        sa.Column("cycle_id", sa.Text, nullable=False),
        sa.Column(
            "instrument",
            sa.Text,
            sa.ForeignKey("instruments.instrument"),
            nullable=False,
        ),
        sa.Column("feature_version", sa.Text, nullable=False),
        sa.Column("feature_hash", sa.Text, nullable=False),
        sa.Column("feature_stats", sa.JSON, nullable=True),
        sa.Column("sampled_features", sa.JSON, nullable=True),
        sa.Column(
            "compact_mode",
            sa.Boolean,
            nullable=False,
            server_default="true",
        ),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("cycle_id", "instrument"),
    )
    op.create_index(
        "ix_feature_snapshots_cycle_id", "feature_snapshots", ["cycle_id"]
    )

    # --- ev_breakdowns (D1 2.1.D #17, AO, Decision logs) ---
    # PK: (cycle_id, instrument, strategy_id).
    # Stores P(win), AvgWin, AvgLoss, cost breakdown, CI, swap_cost.
    op.create_table(
        "ev_breakdowns",
        sa.Column("cycle_id", sa.Text, nullable=False),
        sa.Column(
            "instrument",
            sa.Text,
            sa.ForeignKey("instruments.instrument"),
            nullable=False,
        ),
        sa.Column("strategy_id", sa.Text, nullable=False),
        sa.Column("p_win", sa.Numeric(6, 4), nullable=True),
        sa.Column("avg_win", sa.Numeric(18, 8), nullable=True),
        sa.Column("avg_loss", sa.Numeric(18, 8), nullable=True),
        sa.Column("cost_breakdown", sa.JSON, nullable=True),
        sa.Column("confidence_interval", sa.JSON, nullable=True),
        sa.Column("swap_cost", sa.Numeric(18, 8), nullable=True),
        sa.Column("ev_value", sa.Numeric(18, 8), nullable=True),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("cycle_id", "instrument", "strategy_id"),
    )
    op.create_index("ix_ev_breakdowns_cycle_id", "ev_breakdowns", ["cycle_id"])

    # --- correlation_snapshots (D1 2.1.D #18, AO, Decision logs) ---
    # PK: (timestamp_utc, window_class). No FKs.
    # window_class: 'short_1h' | 'long_30d'
    op.create_table(
        "correlation_snapshots",
        sa.Column("timestamp_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_class", sa.Text, nullable=False),  # 'short_1h'|'long_30d'
        sa.Column("matrix", sa.JSON, nullable=False),
        sa.Column("regime_detected", sa.Text, nullable=True),
        sa.Column("instruments", sa.JSON, nullable=True),
        sa.PrimaryKeyConstraint("timestamp_utc", "window_class"),
    )


def downgrade() -> None:
    op.drop_table("correlation_snapshots")
    op.drop_index("ix_ev_breakdowns_cycle_id", table_name="ev_breakdowns")
    op.drop_table("ev_breakdowns")
    op.drop_index("ix_feature_snapshots_cycle_id", table_name="feature_snapshots")
    op.drop_table("feature_snapshots")
    op.drop_table("pair_selection_scores")
    op.drop_index(
        "ix_pair_selection_runs_cycle_id", table_name="pair_selection_runs"
    )
    op.drop_table("pair_selection_runs")
    op.drop_index("ix_strategy_signals_cycle_id", table_name="strategy_signals")
    op.drop_table("strategy_signals")
    op.drop_index("ix_meta_decisions_cycle_id", table_name="meta_decisions")
    op.drop_table("meta_decisions")
