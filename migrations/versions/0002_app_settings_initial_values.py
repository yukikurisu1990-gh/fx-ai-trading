"""app_settings initial values (phase 6.5 seed)

Revision ID: 0002_app_settings_initial_values
Revises: 0001_group_a_reference
Create Date: 2026-04-17

Seeds ``app_settings`` with the 42 initial parameters defined in
``docs/phase6_hardening.md`` 6.5. All rows carry
``introduced_in_version = '0.0.1'`` so downgrade can remove precisely
what this revision added without touching future manual updates.

Kept separate from the schema migration (0001) to preserve the
"schema change vs data change" boundary (docs/development_rules.md 1.3).
"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_app_settings_initial_values"
down_revision: Union[str, None] = "0001_group_a_reference"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_INTRODUCED_IN = "0.0.1"


# (name, value, type, description)
_INITIAL_VALUES: list[tuple[str, str, str, str]] = [
    # --- Risk / Money management (6.5) ---
    ("risk_per_trade_pct", "1.0", "float", "Per-trade risk cap; range 0.5-2.0."),
    ("max_concurrent_positions", "5", "int", "Hard cap on simultaneous open positions."),
    ("max_single_currency_exposure_pct", "30", "int", "Cap per currency gross exposure."),
    ("max_net_directional_exposure_per_currency_pct", "40", "int", "Cap per currency net directional exposure (S3 mitigation)."),
    ("correlation_threshold", "0.7", "float", "Same-direction correlation ban threshold."),
    ("safe_stop_daily_loss_pct", "5.0", "float", "Daily loss % triggering safe_stop."),
    ("safe_stop_consecutive_loss_count", "5", "int", "Consecutive losses triggering safe_stop."),
    ("safe_stop_drawdown_warning_pct", "4.0", "float", "Drawdown % triggering warning (80% of safe_stop)."),

    # --- Execution / latency (6.5 + 6.15) ---
    ("cycle_timeout_seconds", "45", "int", "Per-cycle wall-clock budget (75% of 1m)."),
    ("stream_gap_safe_stop_seconds", "120", "int", "Stream gap duration triggering safe_stop."),
    ("stream_mid_run_reconcile_interval_minutes", "15", "int", "Periodic drift-check interval (6.2)."),
    ("event_calendar_max_staleness_hours", "24", "int", "EventCalendar stale-failsafe threshold (6.3)."),
    ("price_anomaly_flash_halt_multiplier", "5", "int", "ATR multiplier for PriceAnomalyGuard (6.3)."),
    ("signal_ttl_seconds", "15", "int", "ExecutionGate signal TTL (6.15); range 10-20."),
    ("defer_timeout_seconds", "5", "int", "Individual Defer timeout; must be <= signal_ttl_seconds."),
    ("defer_exhausted_threshold", "3", "int", "Defer retries before Reject(DeferExhausted)."),

    # --- Correlation / Meta (6.5 + 6.7 + 6.8) ---
    ("correlation_short_window_hours", "1", "int", "Short rolling correlation window."),
    ("correlation_long_window_days", "30", "int", "Long rolling correlation window."),
    ("correlation_regime_delta_threshold", "0.3", "float", "Short-vs-long delta to flag regime shift."),
    ("correlation_regime_tightening_delta", "0.1", "float", "Tightening delta (MVP: recorded only, Phase 7 activates)."),
    ("meta_score_concentration_warn_pct", "60", "int", "Single score component contribution warning."),

    # --- Data / log / DB (6.5 + 6.10 + 6.21) ---
    ("retention_hot_days", "7", "int", "Default hot-tier retention (category-level overrides in D5)."),
    ("retention_warm_days", "90", "int", "Default warm-tier retention."),
    ("retention_cold_years", "2", "int", "Default cold-tier retention."),
    ("feature_snapshots_max_mb_per_day", "500", "int", "Daily cap for feature_snapshots under compact_mode."),
    ("db_connection_pool_trading_max", "10", "int", "Trading-path DB pool size."),
    ("db_connection_pool_ui_max", "4", "int", "UI-path DB pool size (separated from trading)."),
    ("db_connection_pool_projector_max", "4", "int", "SecondaryProjector DB pool size."),

    # --- Rate limiter / UI (6.5 + 6.9) ---
    ("rate_limit_trading_rps", "8", "int", "OANDA trading-endpoint RPS budget."),
    ("rate_limit_reconcile_rps", "2", "int", "OANDA reconcile-endpoint RPS budget."),
    ("rate_limit_market_data_rps", "4", "int", "OANDA market-data-endpoint RPS budget."),
    ("ui_polling_interval_seconds_min", "5", "int", "Minimum UI polling interval."),
    ("ui_cache_ttl_seconds_default", "5", "int", "Default st.cache_data TTL."),
    ("secondary_db_error_rate_degrade_pct", "10", "int", "Secondary DB error rate triggering degraded mode."),

    # --- NTP startup check (6.14, two-tier) ---
    ("ntp_skew_warn_ms", "500", "int", "NTP skew >500ms emits warning (continue startup)."),
    ("ntp_skew_reject_ms", "5000", "int", "NTP skew >5000ms rejects startup."),

    # --- Strategy ON/OFF (6.17) ---
    ("strategy.AI.enabled", "true", "bool", "AIStrategy enable flag."),
    ("strategy.MA.enabled", "true", "bool", "MAStrategy enable flag."),
    ("strategy.ATR.enabled", "true", "bool", "ATRStrategy enable flag."),
    ("strategy.AI.lifecycle_state", "stub", "string", "AIStrategy lifecycle: stub|shadow|active (6.11)."),

    # --- Broker safety (6.1 in-flight + 6.18 account_type) ---
    ("expected_account_type", "demo", "string", "Expected broker account_type; local is demo-fixed (6.18)."),
    ("place_order_timeout_seconds", "30", "int", "In-flight place_order timeout during safe_stop (6.1)."),
]


_APP_SETTINGS_TABLE = sa.table(
    "app_settings",
    sa.column("name", sa.Text),
    sa.column("value", sa.Text),
    sa.column("type", sa.Text),
    sa.column("introduced_in_version", sa.Text),
    sa.column("description", sa.Text),
)


def upgrade() -> None:
    op.bulk_insert(
        _APP_SETTINGS_TABLE,
        [
            {
                "name": name,
                "value": value,
                "type": type_,
                "introduced_in_version": _INTRODUCED_IN,
                "description": description,
            }
            for name, value, type_, description in _INITIAL_VALUES
        ],
    )


def downgrade() -> None:
    # Version-aware delete: only remove rows added by this revision,
    # leaving any manual later additions untouched.
    op.execute(
        sa.text(
            "DELETE FROM app_settings WHERE introduced_in_version = :v"
        ).bindparams(v=_INTRODUCED_IN)
    )
