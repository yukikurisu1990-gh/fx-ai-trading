"""ExitFireMetricsService — read-only aggregation over close_events (Cycle 6.9b).

Read-only service that computes summary metrics from ``close_events``. The
table is the authoritative record of position closures (D3 §2.14,
EXECUTION_PERMANENT).

Design constraints (Cycle 6.9b):
  - **Read only**: never INSERT/UPDATE/DELETE; uses ``engine.connect()`` only.
  - **Schema unchanged**: aggregations are computed on-the-fly via SQL GROUP BY.
  - **Supervisor-loop independent**: callers instantiate the service directly.
  - **Append-only respected**: no caching, no derived tables, no materialised
    views.
  - **No repository reuse for ``recent_fires``**: the service issues SQL
    directly rather than delegating to ``CloseEventsRepository.get_recent``.
    Rationale — keep all read paths within one tested module so the test
    surface stays consistent and there is no runtime coupling to a write-side
    repository.

Failure mode:
  - DB exceptions are NOT swallowed — they propagate to the caller. UI
    callers that need empty fallback should wrap via
    ``dashboard_query_service.py`` (separate concern, separate PR).
"""

from __future__ import annotations

import json
from datetime import timedelta

from sqlalchemy import Engine, text

from fx_ai_trading.common.clock import Clock, WallClock


class ExitFireMetricsService:
    """Read-only metrics over the ``close_events`` table.

    Each public method runs a single ``SELECT`` and returns plain Python
    structures. ``window`` arguments are interpreted relative to
    ``clock.now()`` so behaviour is deterministic under a ``FixedClock``.

    Args:
        engine: SQLAlchemy Engine bound to the database holding
            ``close_events``. Required — ``None`` raises ``ValueError``.
        clock: Optional Clock for window boundary calculation. Defaults to
            ``WallClock()``. Tests should pass a ``FixedClock`` for
            deterministic window behaviour.
    """

    def __init__(self, engine: Engine, clock: Clock | None = None) -> None:
        if engine is None:
            raise ValueError("engine is required for ExitFireMetricsService")
        self._engine = engine
        self._clock = clock or WallClock()

    # ------------------------------------------------------------------
    # Public read methods
    # ------------------------------------------------------------------

    def count_by_reason(self, window: timedelta | None = None) -> dict[str, int]:
        """Return ``{primary_reason_code: count}`` grouped by reason.

        Args:
            window: When set, restrict to rows with
                ``closed_at >= clock.now() - window``. ``None`` aggregates
                across the entire table.

        Returns:
            Empty dict when no rows match — never raises on empty result.
        """
        sql, params = self._build_filtered_sql(
            "SELECT primary_reason_code, COUNT(*) FROM close_events",
            window,
            " GROUP BY primary_reason_code",
        )
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
        return {row[0]: int(row[1]) for row in rows}

    def pnl_summary_by_reason(self, window: timedelta | None = None) -> dict[str, dict]:
        """Aggregate ``count`` / ``pnl_sum`` / ``pnl_avg`` per reason.

        ``pnl_realized`` is currently always NULL (Cycle 6.7c E3). Per
        ANSI SQL semantics, ``SUM`` / ``AVG`` return NULL — not 0 — when
        every value in the group is NULL, and ignore NULL rows otherwise.
        All-NULL groups therefore surface as ``None`` here, while mixed
        groups return a real number computed over the non-NULL rows.
        ``count`` always reflects the total row count regardless of NULL
        pnl values.

        Returns:
            ``{primary_reason_code: {"count": int,
                                     "pnl_sum": float | None,
                                     "pnl_avg": float | None}}``
        """
        sql, params = self._build_filtered_sql(
            "SELECT primary_reason_code, COUNT(*),"
            " SUM(pnl_realized), AVG(pnl_realized)"
            " FROM close_events",
            window,
            " GROUP BY primary_reason_code",
        )
        with self._engine.connect() as conn:
            rows = conn.execute(text(sql), params).fetchall()
        return {
            row[0]: {
                "count": int(row[1]),
                "pnl_sum": float(row[2]) if row[2] is not None else None,
                "pnl_avg": float(row[3]) if row[3] is not None else None,
            }
            for row in rows
        }

    def recent_fires(self, limit: int = 50) -> list[dict]:
        """Return the *limit* most recent close_events, newest first.

        Service issues SQL directly rather than delegating to
        ``CloseEventsRepository.get_recent`` — see module docstring for
        rationale (single tested read path, no runtime repo coupling).
        """
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT close_event_id, order_id, position_snapshot_id,"
                    " reasons, primary_reason_code, closed_at,"
                    " pnl_realized, correlation_id"
                    " FROM close_events"
                    " ORDER BY closed_at DESC"
                    " LIMIT :limit"
                ),
                {"limit": int(limit)},
            ).fetchall()
        results: list[dict] = []
        for row in rows:
            reasons = row[3]
            if isinstance(reasons, str):
                reasons = json.loads(reasons)
            results.append(
                {
                    "close_event_id": row[0],
                    "order_id": row[1],
                    "position_snapshot_id": row[2],
                    "reasons": reasons,
                    "primary_reason_code": row[4],
                    "closed_at": row[5],
                    "pnl_realized": float(row[6]) if row[6] is not None else None,
                    "correlation_id": row[7],
                }
            )
        return results

    def summary(self, window: timedelta | None = None) -> dict:
        """Top-line aggregates: total fires, distinct reasons, time span.

        Returns:
            ``{
                "total_fires": int,
                "distinct_reasons": int,
                "span_start_utc": datetime | None,
                "span_end_utc":   datetime | None,
            }``

            ``span_start_utc`` and ``span_end_utc`` are derived from the
            ``closed_at`` column which is ``TIMESTAMPTZ`` — values are
            tz-aware UTC datetimes. Both are ``None`` when zero rows match.
        """
        sql, params = self._build_filtered_sql(
            "SELECT COUNT(*), COUNT(DISTINCT primary_reason_code),"
            " MIN(closed_at), MAX(closed_at)"
            " FROM close_events",
            window,
            "",
        )
        with self._engine.connect() as conn:
            row = conn.execute(text(sql), params).fetchone()
        return {
            "total_fires": int(row[0] or 0),
            "distinct_reasons": int(row[1] or 0),
            "span_start_utc": row[2],
            "span_end_utc": row[3],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_filtered_sql(
        self,
        select_clause: str,
        window: timedelta | None,
        suffix: str,
    ) -> tuple[str, dict]:
        """Compose SQL + params, optionally appending ``closed_at >= :since``."""
        if window is None:
            return select_clause + suffix, {}
        since = self._clock.now() - window
        return (
            select_clause + " WHERE closed_at >= :since" + suffix,
            {"since": since},
        )


__all__ = ["ExitFireMetricsService"]
