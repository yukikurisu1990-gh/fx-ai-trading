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

from datetime import timedelta

from sqlalchemy import Engine, text

from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.services.exit_fire_metrics import ExitFireMetricsService


def list_accounts(engine: Engine | None) -> list[dict]:
    """Return all accounts joined with broker name (for the dashboard switcher)."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = (
                conn.execute(
                    text(
                        "SELECT a.account_id, a.account_type, a.base_currency,"
                        " a.broker_id, b.name AS broker_name"
                        " FROM accounts a"
                        " LEFT JOIN brokers b ON b.broker_id = a.broker_id"
                        " ORDER BY a.account_type, a.account_id"
                    )
                )
                .mappings()
                .all()
            )
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_open_positions(engine: Engine | None, account_id: str | None = None) -> list[dict]:
    """Return open position snapshots (event_type 'open' or 'add').

    If ``account_id`` is provided, results are scoped to that account.
    """
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            sql = (
                "SELECT position_snapshot_id, account_id, instrument,"
                " event_type, units, avg_price, unrealized_pl, event_time_utc"
                " FROM positions"
                " WHERE event_type IN ('open', 'add')"
            )
            params: dict = {}
            if account_id:
                sql += " AND account_id = :aid"
                params["aid"] = account_id
            sql += " ORDER BY event_time_utc DESC LIMIT 50"
            rows = conn.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_recent_orders(
    engine: Engine | None, limit: int = 20, account_id: str | None = None
) -> list[dict]:
    """Return the most recent *limit* orders ordered by created_at desc.

    If ``account_id`` is provided, results are scoped to that account.
    """
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            sql = "SELECT order_id, instrument, direction, units, status, created_at FROM orders"
            params: dict = {"limit": limit}
            if account_id:
                sql += " WHERE account_id = :aid"
                params["aid"] = account_id
            sql += " ORDER BY created_at DESC LIMIT :limit"
            rows = conn.execute(text(sql), params).mappings().all()
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


def get_daily_order_summary(engine: Engine | None, account_id: str | None = None) -> dict:
    """Aggregate today's order counts by status.

    If ``account_id`` is provided, results are scoped to that account.
    """
    if engine is None:
        return {"total": 0, "filled": 0, "canceled": 0, "failed": 0}
    try:
        with engine.connect() as conn:
            sql = (
                "SELECT"
                "  COUNT(*) AS total,"
                "  SUM(CASE WHEN status = 'FILLED'   THEN 1 ELSE 0 END) AS filled,"
                "  SUM(CASE WHEN status = 'CANCELED' THEN 1 ELSE 0 END) AS canceled,"
                "  SUM(CASE WHEN status = 'FAILED'   THEN 1 ELSE 0 END) AS failed"
                " FROM orders"
                " WHERE DATE(created_at) = CURRENT_DATE"
            )
            params: dict = {}
            if account_id:
                sql += " AND account_id = :aid"
                params["aid"] = account_id
            row = conn.execute(text(sql), params).fetchone()
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


def get_execution_quality_summary(
    engine: Engine | None, limit: int = 20, account_id: str | None = None
) -> list[dict]:
    """Return recent execution quality metrics (fill latency, slippage, signal age).

    Joins ``orders`` to scope by ``account_id`` when provided.
    """
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            sql = (
                "SELECT em.order_id, em.signal_age_seconds,"
                " em.slippage_pips, em.latency_ms, em.recorded_at"
                " FROM execution_metrics em"
            )
            params: dict = {"limit": limit}
            if account_id:
                sql += " JOIN orders o ON o.order_id = em.order_id WHERE o.account_id = :aid"
                params["aid"] = account_id
            sql += " ORDER BY em.recorded_at DESC LIMIT :limit"
            rows = conn.execute(text(sql), params).mappings().all()
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
                        "SELECT risk_event_id, cycle_id, instrument, verdict,"
                        " constraint_violated, event_time_utc"
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


def get_close_events_recent(
    engine: Engine | None, limit: int = 20, account_id: str | None = None
) -> list[dict]:
    """Return recent position close events with exit reasons.

    Joins ``orders`` to scope by ``account_id`` when provided.
    """
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            sql = (
                "SELECT ce.close_event_id, ce.order_id, ce.primary_reason_code,"
                " ce.reasons, ce.closed_at, ce.pnl_realized"
                " FROM close_events ce"
            )
            params: dict = {"limit": limit}
            if account_id:
                sql += " JOIN orders o ON o.order_id = ce.order_id WHERE o.account_id = :aid"
                params["aid"] = account_id
            sql += " ORDER BY ce.closed_at DESC LIMIT :limit"
            rows = conn.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Analytics queries — equity / per-pair / outcomes / hour / strategy
# ---------------------------------------------------------------------------


def _account_join_clause(account_id: str | None) -> tuple[str, dict]:
    """Return (' JOIN orders... WHERE ... ', params) for account scoping."""
    if not account_id:
        return "", {}
    return " JOIN orders o ON o.order_id = ce.order_id WHERE o.account_id = :aid", {
        "aid": account_id
    }


def get_equity_curve(
    engine: Engine | None, account_id: str | None = None, limit: int = 1000
) -> list[dict]:
    """Return per-trade close events with cumulative PnL.

    Each row: {closed_at, pnl_realized, cumulative_pnl}. Caller scopes to the
    selected account. Cumulative is computed in Python.
    """
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            join, params = _account_join_clause(account_id)
            params = {**params, "limit": limit}
            sql = (
                "SELECT ce.closed_at, ce.pnl_realized FROM close_events ce"
                + join
                + " ORDER BY ce.closed_at ASC LIMIT :limit"
            )
            rows = conn.execute(text(sql), params).mappings().all()
        cumulative = 0.0
        out: list[dict] = []
        for r in rows:
            pnl = float(r["pnl_realized"] or 0.0)
            cumulative += pnl
            out.append(
                {
                    "closed_at": r["closed_at"],
                    "pnl_realized": pnl,
                    "cumulative_pnl": cumulative,
                }
            )
        return out
    except Exception:
        return []


def get_daily_pnl(
    engine: Engine | None, account_id: str | None = None, days: int = 30
) -> list[dict]:
    """Return per-day aggregated PnL: {day, total_pnl, n_trades, n_wins, n_losses}."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            join, params = _account_join_clause(account_id)
            params = {**params, "days": days}
            sql = (
                "SELECT DATE(ce.closed_at) AS day,"
                " SUM(ce.pnl_realized) AS total_pnl,"
                " COUNT(*) AS n_trades,"
                " SUM(CASE WHEN ce.pnl_realized > 0 THEN 1 ELSE 0 END) AS n_wins,"
                " SUM(CASE WHEN ce.pnl_realized < 0 THEN 1 ELSE 0 END) AS n_losses"
                " FROM close_events ce"
                + join
                + (" AND " if join else " WHERE ")
                + "ce.closed_at >= NOW() - (:days || ' days')::interval"
                " GROUP BY DATE(ce.closed_at)"
                " ORDER BY day ASC"
            )
            rows = conn.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_per_pair_performance(engine: Engine | None, account_id: str | None = None) -> list[dict]:
    """Return per-instrument trade stats: {instrument, n_trades, total_pnl, win_rate, avg_pnl}."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            sql = (
                "SELECT o.instrument,"
                " COUNT(*) AS n_trades,"
                " SUM(ce.pnl_realized) AS total_pnl,"
                " AVG(ce.pnl_realized) AS avg_pnl,"
                " SUM(CASE WHEN ce.pnl_realized > 0 THEN 1 ELSE 0 END) AS n_wins,"
                " SUM(CASE WHEN ce.pnl_realized < 0 THEN 1 ELSE 0 END) AS n_losses"
                " FROM close_events ce"
                " JOIN orders o ON o.order_id = ce.order_id"
            )
            params: dict = {}
            if account_id:
                sql += " WHERE o.account_id = :aid"
                params["aid"] = account_id
            sql += " GROUP BY o.instrument ORDER BY total_pnl DESC"
            rows = conn.execute(text(sql), params).mappings().all()
        out: list[dict] = []
        for r in rows:
            n = int(r["n_trades"]) if r["n_trades"] else 0
            wins = int(r["n_wins"] or 0)
            out.append(
                {
                    "instrument": r["instrument"],
                    "n_trades": n,
                    "total_pnl": float(r["total_pnl"] or 0.0),
                    "avg_pnl": float(r["avg_pnl"] or 0.0),
                    "n_wins": wins,
                    "n_losses": int(r["n_losses"] or 0),
                    "win_rate": (wins / n) if n > 0 else 0.0,
                }
            )
        return out
    except Exception:
        return []


def get_trade_outcome_breakdown(engine: Engine | None, account_id: str | None = None) -> list[dict]:
    """Return count + total PnL per primary_reason_code (TP/SL/TIME/etc)."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            join, params = _account_join_clause(account_id)
            sql = (
                "SELECT ce.primary_reason_code,"
                " COUNT(*) AS n,"
                " SUM(ce.pnl_realized) AS total_pnl"
                " FROM close_events ce" + join + " GROUP BY ce.primary_reason_code ORDER BY n DESC"
            )
            rows = conn.execute(text(sql), params).mappings().all()
        return [
            {
                "reason": r["primary_reason_code"],
                "n_trades": int(r["n"] or 0),
                "total_pnl": float(r["total_pnl"] or 0.0),
            }
            for r in rows
        ]
    except Exception:
        return []


def get_hourly_distribution(engine: Engine | None, account_id: str | None = None) -> list[dict]:
    """Return trade frequency + avg PnL per hour-of-day (UTC)."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            join, params = _account_join_clause(account_id)
            sql = (
                "SELECT EXTRACT(hour FROM ce.closed_at) AS hour,"
                " COUNT(*) AS n_trades,"
                " AVG(ce.pnl_realized) AS avg_pnl,"
                " SUM(ce.pnl_realized) AS total_pnl"
                " FROM close_events ce" + join + " GROUP BY EXTRACT(hour FROM ce.closed_at)"
                " ORDER BY hour ASC"
            )
            rows = conn.execute(text(sql), params).mappings().all()
        return [
            {
                "hour": int(r["hour"] or 0),
                "n_trades": int(r["n_trades"] or 0),
                "avg_pnl": float(r["avg_pnl"] or 0.0),
                "total_pnl": float(r["total_pnl"] or 0.0),
            }
            for r in rows
        ]
    except Exception:
        return []


def get_strategy_breakdown(engine: Engine | None, account_id: str | None = None) -> list[dict]:
    """Return per-strategy stats. Strategy id parsed from orders.client_order_id
    convention "{ulid}:{instrument}:{strategy_id}"."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            sql = (
                "SELECT split_part(o.client_order_id, ':', 3) AS strategy_id,"
                " COUNT(*) AS n_trades,"
                " SUM(ce.pnl_realized) AS total_pnl,"
                " AVG(ce.pnl_realized) AS avg_pnl,"
                " SUM(CASE WHEN ce.pnl_realized > 0 THEN 1 ELSE 0 END) AS n_wins"
                " FROM close_events ce"
                " JOIN orders o ON o.order_id = ce.order_id"
            )
            params: dict = {}
            if account_id:
                sql += " WHERE o.account_id = :aid"
                params["aid"] = account_id
            sql += " GROUP BY split_part(o.client_order_id, ':', 3) ORDER BY total_pnl DESC"
            rows = conn.execute(text(sql), params).mappings().all()
        out: list[dict] = []
        for r in rows:
            n = int(r["n_trades"] or 0)
            wins = int(r["n_wins"] or 0)
            out.append(
                {
                    "strategy_id": r["strategy_id"] or "(none)",
                    "n_trades": n,
                    "total_pnl": float(r["total_pnl"] or 0.0),
                    "avg_pnl": float(r["avg_pnl"] or 0.0),
                    "win_rate": (wins / n) if n > 0 else 0.0,
                }
            )
        return out
    except Exception:
        return []


def get_account_summary(engine: Engine | None, account_id: str) -> dict:
    """Return high-level account stats: total trades, total PnL, win rate, max DD."""
    empty = {
        "n_trades": 0,
        "total_pnl": 0.0,
        "win_rate": 0.0,
        "best_trade": 0.0,
        "worst_trade": 0.0,
        "max_drawdown": 0.0,
    }
    if engine is None or not account_id:
        return empty
    try:
        equity = get_equity_curve(engine, account_id=account_id, limit=10000)
        if not equity:
            return empty
        pnls = [r["pnl_realized"] for r in equity]
        cum = [r["cumulative_pnl"] for r in equity]
        n = len(pnls)
        wins = sum(1 for p in pnls if p > 0)
        peak = 0.0
        max_dd = 0.0
        for c in cum:
            peak = max(peak, c)
            dd = peak - c
            if dd > max_dd:
                max_dd = dd
        return {
            "n_trades": n,
            "total_pnl": cum[-1] if cum else 0.0,
            "win_rate": (wins / n) if n > 0 else 0.0,
            "best_trade": max(pnls) if pnls else 0.0,
            "worst_trade": min(pnls) if pnls else 0.0,
            "max_drawdown": max_dd,
        }
    except Exception:
        return empty


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
# Cycle 6.9d — ExitFireMetricsService UI-safe wrappers
# ---------------------------------------------------------------------------
#
# Thin fail-open adapters around ExitFireMetricsService for dashboard /
# query consumers. The underlying service raises on DB error; these
# wrappers catch and return an empty fallback so UI panels stay graceful.
#
# ``window_seconds`` is the wire form (UI-friendly int) for the service's
# ``window: timedelta`` parameter. None means "all time".


_EMPTY_SUMMARY: dict = {
    "total_fires": 0,
    "distinct_reasons": 0,
    "span_start_utc": None,
    "span_end_utc": None,
}


def _to_window(window_seconds: int | None) -> timedelta | None:
    return timedelta(seconds=window_seconds) if window_seconds is not None else None


def get_exit_fire_summary(engine: Engine | None, window_seconds: int | None = None) -> dict:
    """Top-line exit-fire aggregates with UI-safe fallback."""
    if engine is None:
        return dict(_EMPTY_SUMMARY)
    try:
        return ExitFireMetricsService(engine).summary(window=_to_window(window_seconds))
    except Exception:
        return dict(_EMPTY_SUMMARY)


def get_exit_fire_count_by_reason(
    engine: Engine | None, window_seconds: int | None = None
) -> dict[str, int]:
    """Count of close_events grouped by primary_reason_code, UI-safe."""
    if engine is None:
        return {}
    try:
        return ExitFireMetricsService(engine).count_by_reason(window=_to_window(window_seconds))
    except Exception:
        return {}


def get_exit_fire_pnl_summary_by_reason(
    engine: Engine | None, window_seconds: int | None = None
) -> dict[str, dict]:
    """count / pnl_sum / pnl_avg per primary_reason_code, UI-safe."""
    if engine is None:
        return {}
    try:
        return ExitFireMetricsService(engine).pnl_summary_by_reason(
            window=_to_window(window_seconds)
        )
    except Exception:
        return {}


def get_exit_fire_recent(engine: Engine | None, limit: int = 50) -> list[dict]:
    """Most-recent close_events (newest first), UI-safe."""
    if engine is None:
        return []
    try:
        return ExitFireMetricsService(engine).recent_fires(limit=limit)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# M26 Phase 2 — Configuration Console write path (queue only)
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Candlestick chart queries
# ---------------------------------------------------------------------------


def get_market_candles(
    engine: Engine | None,
    instrument: str,
    tier: str | None = None,
    limit: int = 500,
) -> list[dict]:
    """Return OHLCV candles for a given instrument, newest-last.

    When ``tier`` is None (default), returns candles regardless of tier
    (useful when the stored tier is unknown, e.g. M5 vs M1).
    """
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            if tier is None:
                rows = (
                    conn.execute(
                        text(
                            "SELECT event_time_utc, open, high, low, close, volume"
                            " FROM market_candles"
                            " WHERE instrument = :inst"
                            " ORDER BY event_time_utc DESC LIMIT :limit"
                        ),
                        {"inst": instrument, "limit": limit},
                    )
                    .mappings()
                    .all()
                )
            else:
                rows = (
                    conn.execute(
                        text(
                            "SELECT event_time_utc, open, high, low, close, volume"
                            " FROM market_candles"
                            " WHERE instrument = :inst AND tier = :tier"
                            " ORDER BY event_time_utc DESC LIMIT :limit"
                        ),
                        {"inst": instrument, "tier": tier, "limit": limit},
                    )
                    .mappings()
                    .all()
                )
        return [dict(r) for r in reversed(rows)]
    except Exception:
        return []


def get_trade_markers(
    engine: Engine | None,
    instrument: str,
    account_id: str | None = None,
    limit: int = 200,
) -> list[dict]:
    """Return entry/exit price markers for closed trades on a given instrument.

    Each row: {entry_time, exit_time, entry_price, exit_price, direction, pnl_realized}.
    """
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            sql = (
                "SELECT"
                "  o.direction,"
                "  o.filled_at AS entry_time,"
                "  ce.closed_at AS exit_time,"
                "  p_open.avg_price AS entry_price,"
                "  p_close.avg_price AS exit_price,"
                "  ce.pnl_realized,"
                "  ce.primary_reason_code"
                " FROM orders o"
                " JOIN close_events ce ON ce.order_id = o.order_id"
                " JOIN positions p_open ON p_open.order_id = o.order_id"
                "   AND p_open.event_type = 'open'"
                " JOIN positions p_close ON p_close.order_id = o.order_id"
                "   AND p_close.event_type = 'close'"
                " WHERE o.instrument = :inst AND o.status = 'FILLED'"
            )
            params: dict = {"inst": instrument, "limit": limit}
            if account_id:
                sql += " AND o.account_id = :aid"
                params["aid"] = account_id
            sql += " ORDER BY o.filled_at DESC LIMIT :limit"
            rows = conn.execute(text(sql), params).mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        return []


def get_decision_markers(
    engine: Engine | None,
    instrument: str,
    limit: int = 200,
    since: object | None = None,
) -> list[dict]:
    """Return MetaDecider decision markers for a given instrument.

    Each row: {signal_time_utc, signal_direction, confidence, strategy_id, p_long, p_short}.
    p_long/p_short are extracted from the meta JSON column when available.

    If *since* is provided (a UTC-aware or UTC-naive datetime), only rows at or after
    that timestamp are returned and *limit* is raised to 20 000 to cover multi-day views.
    """
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            if since is not None:
                rows = (
                    conn.execute(
                        text(
                            "SELECT signal_time_utc, signal_direction, confidence, strategy_id, meta"
                            " FROM strategy_signals"
                            " WHERE instrument = :inst AND signal_time_utc >= :since"
                            " ORDER BY signal_time_utc ASC LIMIT 20000"
                        ),
                        {"inst": instrument, "since": since},
                    )
                    .mappings()
                    .all()
                )
            else:
                rows = (
                    conn.execute(
                        text(
                            "SELECT signal_time_utc, signal_direction, confidence, strategy_id, meta"
                            " FROM strategy_signals"
                            " WHERE instrument = :inst"
                            " ORDER BY signal_time_utc DESC LIMIT :limit"
                        ),
                        {"inst": instrument, "limit": limit},
                    )
                    .mappings()
                    .all()
                )
        result = []
        for r in rows:
            d = dict(r)
            meta = d.pop("meta", None)
            if isinstance(meta, str):
                try:
                    import json as _json
                    meta = _json.loads(meta)
                except Exception:
                    meta = {}
            if isinstance(meta, dict):
                d["p_long"] = meta.get("p_long")
                d["p_short"] = meta.get("p_short")
                d["tp_pips"] = meta.get("tp")
                d["sl_pips"] = meta.get("sl")
                d["holding_time_seconds"] = meta.get("holding_time_seconds")
            else:
                d["p_long"] = None
                d["p_short"] = None
                d["tp_pips"] = None
                d["sl_pips"] = None
                d["holding_time_seconds"] = None
            result.append(d)
        return result
    except Exception:
        return []


def list_candle_instruments(engine: Engine | None) -> list[str]:
    """Return distinct instruments that have candle data."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT DISTINCT instrument FROM market_candles ORDER BY instrument")
            ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


def list_instruments(engine: Engine | None) -> list[str]:
    """Return all registered instruments from the instruments table."""
    if engine is None:
        return []
    try:
        with engine.connect() as conn:
            rows = conn.execute(
                text("SELECT instrument FROM instruments ORDER BY instrument")
            ).fetchall()
        return [r[0] for r in rows]
    except Exception:
        return []


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
