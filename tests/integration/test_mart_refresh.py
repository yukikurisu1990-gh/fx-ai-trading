"""Integration tests: MartScheduler — periodic TSS mart refresh (M20).

Uses a real in-memory SQLite with both strategy_signals and
dashboard_top_candidates tables seeded.  A fake advancing clock verifies
the 15-minute interval logic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.services.mart_scheduler import MartScheduler

_BASE_DT = datetime(2026, 1, 1, tzinfo=UTC)


class _AdvancingClock:
    def __init__(self, start: datetime) -> None:
        self._dt = start

    def now(self) -> datetime:
        return self._dt

    def advance(self, seconds: float) -> None:
        self._dt = self._dt + timedelta(seconds=seconds)


_DDL = [
    """CREATE TABLE strategy_signals (
        cycle_id        TEXT NOT NULL,
        instrument      TEXT NOT NULL,
        strategy_id     TEXT NOT NULL,
        strategy_type   TEXT NOT NULL,
        signal_direction TEXT NOT NULL,
        confidence      REAL,
        signal_time_utc TEXT NOT NULL,
        PRIMARY KEY (cycle_id, instrument, strategy_id)
    )""",
    """CREATE TABLE dashboard_top_candidates (
        candidate_id TEXT PRIMARY KEY,
        instrument   TEXT NOT NULL,
        strategy_id  TEXT NOT NULL,
        tss_score    REAL NOT NULL,
        direction    TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        rank         INTEGER NOT NULL
    )""",
]

_SIGNALS = [
    ("c1", "EURUSD", "AI", "momentum", "buy", 0.85, "2026-01-01T00:00:00"),
    ("c1", "USDJPY", "AI", "momentum", "buy", 0.72, "2026-01-01T00:00:00"),
    ("c1", "GBPUSD", "AI", "momentum", "sell", 0.60, "2026-01-01T00:00:00"),
]


@pytest.fixture()
def seeded_engine():
    eng = create_engine("sqlite:///:memory:")
    with eng.begin() as conn:
        for ddl in _DDL:
            conn.execute(text(ddl))
        for row in _SIGNALS:
            conn.execute(
                text(
                    "INSERT INTO strategy_signals VALUES"
                    " (:cid, :inst, :strat, :stype, :dir, :conf, :ts)"
                ),
                {
                    "cid": row[0],
                    "inst": row[1],
                    "strat": row[2],
                    "stype": row[3],
                    "dir": row[4],
                    "conf": row[5],
                    "ts": row[6],
                },
            )
    yield eng
    eng.dispose()


def _read_mart(eng) -> list[dict]:
    with eng.connect() as conn:
        rows = (
            conn.execute(text("SELECT * FROM dashboard_top_candidates ORDER BY rank"))
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]


class TestMartSchedulerDue:
    def test_initially_due(self, seeded_engine) -> None:
        clock = _AdvancingClock(_BASE_DT)
        scheduler = MartScheduler(seeded_engine, clock=clock)
        assert scheduler.due() is True

    def test_not_due_immediately_after_refresh(self, seeded_engine) -> None:
        clock = _AdvancingClock(_BASE_DT)
        scheduler = MartScheduler(seeded_engine, clock=clock)
        scheduler.refresh()
        assert scheduler.due() is False

    def test_due_after_interval_elapsed(self, seeded_engine) -> None:
        clock = _AdvancingClock(_BASE_DT)
        scheduler = MartScheduler(seeded_engine, clock=clock)
        scheduler.refresh()
        clock.advance(MartScheduler.INTERVAL_SECONDS)
        assert scheduler.due() is True

    def test_not_due_before_interval(self, seeded_engine) -> None:
        clock = _AdvancingClock(_BASE_DT)
        scheduler = MartScheduler(seeded_engine, clock=clock)
        scheduler.refresh()
        clock.advance(MartScheduler.INTERVAL_SECONDS - 1)
        assert scheduler.due() is False

    def test_interval_is_900_seconds(self, seeded_engine) -> None:
        assert MartScheduler.INTERVAL_SECONDS == 900


class TestMartSchedulerRefresh:
    def test_refresh_writes_candidates(self, seeded_engine) -> None:
        clock = _AdvancingClock(_BASE_DT)
        scheduler = MartScheduler(seeded_engine, clock=clock)
        count = scheduler.refresh()
        assert count == 3  # 3 seeded instruments with positive confidence

    def test_mart_contains_correct_instruments(self, seeded_engine) -> None:
        clock = _AdvancingClock(_BASE_DT)
        scheduler = MartScheduler(seeded_engine, clock=clock)
        scheduler.refresh()
        rows = _read_mart(seeded_engine)
        instruments = {r["instrument"] for r in rows}
        assert instruments == {"EURUSD", "USDJPY", "GBPUSD"}

    def test_mart_ranks_are_sequential(self, seeded_engine) -> None:
        clock = _AdvancingClock(_BASE_DT)
        scheduler = MartScheduler(seeded_engine, clock=clock)
        scheduler.refresh()
        rows = _read_mart(seeded_engine)
        assert [r["rank"] for r in rows] == [1, 2, 3]

    def test_mart_highest_confidence_ranked_first(self, seeded_engine) -> None:
        clock = _AdvancingClock(_BASE_DT)
        scheduler = MartScheduler(seeded_engine, clock=clock)
        scheduler.refresh()
        rows = _read_mart(seeded_engine)
        assert rows[0]["instrument"] == "EURUSD"

    def test_second_refresh_updates_mart(self, seeded_engine) -> None:
        clock = _AdvancingClock(_BASE_DT)
        scheduler = MartScheduler(seeded_engine, clock=clock)
        scheduler.refresh()
        clock.advance(MartScheduler.INTERVAL_SECONDS)
        count = scheduler.refresh()
        assert count == 3  # same 3 instruments, updated via UPSERT

    def test_refresh_with_no_signals_returns_zero(self, seeded_engine) -> None:
        with seeded_engine.begin() as conn:
            conn.execute(text("DELETE FROM strategy_signals"))
        clock = _AdvancingClock(_BASE_DT)
        scheduler = MartScheduler(seeded_engine, clock=clock)
        count = scheduler.refresh()
        assert count == 0

    def test_refresh_with_missing_signals_table_returns_zero(self) -> None:
        eng = create_engine("sqlite:///:memory:")
        with eng.begin() as conn:
            conn.execute(
                text(
                    "CREATE TABLE dashboard_top_candidates ("
                    "  candidate_id TEXT PRIMARY KEY,"
                    "  instrument   TEXT NOT NULL,"
                    "  strategy_id  TEXT NOT NULL,"
                    "  tss_score    REAL NOT NULL,"
                    "  direction    TEXT NOT NULL,"
                    "  generated_at TEXT NOT NULL,"
                    "  rank         INTEGER NOT NULL"
                    ")"
                )
            )
        clock = _AdvancingClock(_BASE_DT)
        scheduler = MartScheduler(eng, clock=clock)
        count = scheduler.refresh()
        assert count == 0
        eng.dispose()
