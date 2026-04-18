"""Dashboard Query Service — read-only DB queries for the Streamlit UI (M12).

All public functions accept a SQLAlchemy Engine (or None), execute a single
SQL read, and return plain Python data structures.  No streamlit imports.

Callers (dashboard panels) apply their own ``@st.cache_data(ttl=5)`` wrapper;
this module stays framework-free so it is independently testable.

On any DB error the function returns an empty result ([] or {}) rather than
raising, so the dashboard panel can show a graceful fallback.
"""

from __future__ import annotations

from sqlalchemy import Engine, text


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
