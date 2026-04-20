"""Dashboard Query Service — read-only DB queries for the Streamlit UI (M12).

All public read functions accept a SQLAlchemy Engine (or None), execute a
single SQL read, and return plain Python data structures.  No streamlit
imports.

Callers (dashboard panels) apply their own ``@st.cache_data(ttl=5)`` wrapper;
this module stays framework-free so it is independently testable.

On any DB error the read function returns an empty result ([] or {}) rather
than raising, so the dashboard panel can show a graceful fallback.

Write helpers (M26 Phase 2): ``enqueue_app_settings_change`` is the only
write path. It INSERTs into ``app_settings_changes`` and never UPDATEs
``app_settings`` (changes apply on next restart / hot-reload).
"""

from __future__ import annotations

from sqlalchemy import Engine, text

from fx_ai_trading.common.ulid import generate_ulid


def get_open_positions(engine: Engine | None) -> list[dict]:
    """Return open position snapshots (event_type 'open' or 'add')."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT position_snapshot_id, account_id, instrument,"
                        " event_type, units, avg_price, unrealized_pl, event_time_utc"
                        " FROM position_snapshots"
                        " WHERE event_type IN ('open', 'add')"
                        " ORDER BY event_time_utc DESC"
                        " LIMIT 50"
                    )
                )
                .mappings()
                .all()
            )
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_recent_orders(engine: Engine | None, limit: int = 20) -> list[dict]:
    """Return the most recent *limit* orders ordered by created_at desc."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT order_id, instrument, direction, units, status, created_at"
                        " FROM orders"
                        " ORDER BY created_at DESC"
                        " LIMIT :limit"
                    ),
                    {"limit": limit},
                )
                .mappings()
                .all()
            )
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_recent_supervisor_events(engine: Engine | None, limit: int = 10) -> list[dict]:
    """Return the most recent *limit* supervisor lifecycle events."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT event_type, run_id, config_version, event_time_utc, detail"
                        " FROM supervisor_events"
                        " ORDER BY event_time_utc DESC"
                        " LIMIT :limit"
                    ),
                    {"limit": limit},
                )
                .mappings()
                .all()
            )
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_app_setting(engine: Engine | None, name: str) -> str | None:
    """Return a single app_settings value, or None if missing / no DB."""
    if engine is None:
        return None
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT value FROM app_settings WHERE name = :name"),
                {"name": name},
            ).fetchone()
        return row[0] if row else None
    except Exception:
        return None


def get_daily_order_summary(engine: Engine | None) -> dict:
    """Aggregate today's order counts by status."""
    if engine is None:
        return {"total": 0, "filled": 0, "canceled": 0, "failed": 0}
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT"
                    "  COUNT(*) AS total,"
                    "  SUM(CASE WHEN status = 'FILLED'   THEN 1 ELSE 0 END) AS filled,"
                    "  SUM(CASE WHEN status = 'CANCELED' THEN 1 ELSE 0 END) AS canceled,"
                    "  SUM(CASE WHEN status = 'FAILED'   THEN 1 ELSE 0 END) AS failed"
                    " FROM orders"
                    " WHERE DATE(created_at) = CURRENT_DATE"
                )
            ).fetchone()
        if row is None:
            return {"total": 0, "filled": 0, "canceled": 0, "failed": 0}
        return {
            "total": row[0] or 0,
            "filled": row[1] or 0,
            "canceled": row[2] or 0,
            "failed": row[3] or 0,
        }
    except Exception:
        return {"total": 0, "filled": 0, "canceled": 0, "failed": 0}


# ---------------------------------------------------------------------------
# M18 — Extended queries (Ob-PANEL-FALLBACK-1)
# ---------------------------------------------------------------------------


def get_top_candidates(engine: Engine | None, limit: int = 20) -> list[dict]:
    """Return top-ranked trade candidates from the dashboard_top_candidates mart.

    Returns [] when the table does not yet exist (created in M20) or on any
    DB error — callers display a graceful "data unavailable" state.
    """
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT instrument, strategy_id, tss_score, direction,"
                        " generated_at, rank"
                        " FROM dashboard_top_candidates"
                        " ORDER BY rank ASC"
                        " LIMIT :limit"
                    ),
                    {"limit": limit},
                )
                .mappings()
                .all()
            )
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_execution_quality_summary(engine: Engine | None, limit: int = 20) -> list[dict]:
    """Return recent execution quality metrics (fill latency, slippage, signal age)."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT order_id, instrument, signal_age_seconds,"
                        " slippage_pips, fill_latency_ms, created_at"
                        " FROM execution_metrics"
                        " ORDER BY created_at DESC"
                        " LIMIT :limit"
                    ),
                    {"limit": limit},
                )
                .mappings()
                .all()
            )
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_risk_state_detail(engine: Engine | None, limit: int = 20) -> list[dict]:
    """Return recent risk manager accept/reject decisions."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT risk_event_id, cycle_id, instrument, decision,"
                        " reason_codes, event_time_utc"
                        " FROM risk_events"
                        " ORDER BY event_time_utc DESC"
                        " LIMIT :limit"
                    ),
                    {"limit": limit},
                )
                .mappings()
                .all()
            )
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_close_events_recent(engine: Engine | None, limit: int = 20) -> list[dict]:
    """Return recent position close events with exit reasons."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT close_event_id, order_id, primary_reason_code,"
                        " reasons, closed_at, pnl_realized"
                        " FROM close_events"
                        " ORDER BY closed_at DESC"
                        " LIMIT :limit"
                    ),
                    {"limit": limit},
                )
                .mappings()
                .all()
            )
        return [dict(r) for r in rows]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# M21 — Learning Jobs query (M-LRN-1)
# ---------------------------------------------------------------------------


def get_learning_jobs(engine: Engine | None, limit: int = 20) -> list[dict]:
    """Return recent training jobs from system_jobs (job_type='training')."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT system_job_id, job_type, status,"
                        " created_at, started_at, ended_at"
                        " FROM system_jobs"
                        " WHERE job_type = 'training'"
                        " ORDER BY created_at DESC"
                        " LIMIT :limit"
                    ),
                    {"limit": limit},
                )
                .mappings()
                .all()
            )
        return [dict(r) for r in rows]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# M26 Phase 2 — Configuration Console write path (queue only)
# ---------------------------------------------------------------------------


def enqueue_app_settings_change(
    engine: Engine | None,
    *,
    name: str,
    old_value: str | None,
    new_value: str,
    changed_by: str | None,
    reason: str | None,
) -> int:
    """Enqueue an app_settings change for next-restart application.

    INSERTs one row into ``app_settings_changes``. Does NOT touch
    ``app_settings`` — the queue is consumed by Supervisor on restart /
    hot-reload (operations.md §15.2).

    The PK ``app_settings_change_id`` is generated as a ULID.
    ``changed_at`` is set by the database via ``CURRENT_TIMESTAMP`` to
    avoid ``datetime.now()`` (development_rules.md §13.1; matches the
    pattern used by ``AppSettingsRepository.set``).

    Returns the inserted row count (1 on success). Raises ``ValueError``
    when ``engine`` is None or ``name`` / ``new_value`` is empty.
    """
    if engine is None:
        raise ValueError("engine is required for enqueue_app_settings_change")
    if not name or not name.strip():
        raise ValueError("name must be non-empty")
    if not new_value or not new_value.strip():
        raise ValueError("new_value must be non-empty")

    change_id = generate_ulid()

    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO app_settings_changes"
                " (app_settings_change_id, name, old_value, new_value,"
                "  changed_by, changed_at, reason)"
                " VALUES"
                " (:change_id, :name, :old_value, :new_value,"
                "  :changed_by, CURRENT_TIMESTAMP, :reason)"
            ),
            {
                "change_id": change_id,
                "name": name,
                "old_value": old_value,
                "new_value": new_value,
                "changed_by": changed_by,
                "reason": reason,
            },
        )
    return result.rowcount
