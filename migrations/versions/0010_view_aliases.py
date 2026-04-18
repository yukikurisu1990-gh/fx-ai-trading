"""view aliases: Phase 1/3 legacy names mapped to Phase 4 physical tables

Revision ID: 0010_view_aliases
Revises: 0009_group_i_operations
Create Date: 2026-04-18

Creates 11 read-only VIEWs that preserve Phase 1/3 legacy names.
No physical tables are created or modified.

Mapping (old name -> physical table):
  intents            -> trading_signals         (adopted order intents)
  fills              -> order_transactions       (broker transaction stream)
  exits              -> close_events             (position close records)
  features           -> feature_snapshots        (per-cycle feature data)
  ev_decompositions  -> ev_breakdowns            (EV component breakdown)
  risk_evaluations   -> risk_events              (risk gate evaluations)
  candles_1m         -> market_candles tier='1m' (1-minute OHLCV)
  candles_5m         -> market_candles tier='5m' (5-minute OHLCV)
  events_calendar    -> economic_events          (economic calendar)
  no_trade_evaluations -> no_trade_events        (no-trade decisions)
  learning_jobs      -> system_jobs job_type='learning'

Skipped (no unambiguous physical target):
  exit_decisions, execution_gates, experiments
"""

from collections.abc import Sequence
from typing import Union

from alembic import op

revision: str = "0010_view_aliases"
down_revision: Union[str, None] = "0009_group_i_operations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (view_name, select_sql) pairs — order matters for drop in downgrade
_VIEWS = [
    ("intents", "SELECT * FROM trading_signals"),
    ("fills", "SELECT * FROM order_transactions"),
    ("exits", "SELECT * FROM close_events"),
    ("features", "SELECT * FROM feature_snapshots"),
    ("ev_decompositions", "SELECT * FROM ev_breakdowns"),
    ("risk_evaluations", "SELECT * FROM risk_events"),
    ("candles_1m", "SELECT * FROM market_candles WHERE tier = '1m'"),
    ("candles_5m", "SELECT * FROM market_candles WHERE tier = '5m'"),
    ("events_calendar", "SELECT * FROM economic_events"),
    ("no_trade_evaluations", "SELECT * FROM no_trade_events"),
    ("learning_jobs", "SELECT * FROM system_jobs WHERE job_type = 'learning'"),
]


def upgrade() -> None:
    for view_name, select_sql in _VIEWS:
        op.execute(f"CREATE VIEW {view_name} AS {select_sql}")


def downgrade() -> None:
    for view_name, _ in reversed(_VIEWS):
        op.execute(f"DROP VIEW IF EXISTS {view_name}")
