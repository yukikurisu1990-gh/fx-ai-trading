"""Unit tests: MartBuilder (M20).

Uses a real in-memory SQLite with dashboard_top_candidates table created inline.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text

from fx_ai_trading.services.mart_builder import MartBuilder, TSSCandidate

_TS = "2026-01-01T00:00:00+00:00"


@pytest.fixture()
def engine():
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
    yield eng
    eng.dispose()


def _candidates(*pairs) -> list[TSSCandidate]:
    return [TSSCandidate(inst, "AI", score, "buy", _TS) for inst, score in pairs]


def _read_all(eng) -> list[dict]:
    with eng.connect() as conn:
        rows = (
            conn.execute(text("SELECT * FROM dashboard_top_candidates ORDER BY rank"))
            .mappings()
            .all()
        )
    return [dict(r) for r in rows]


class TestMartBuilderRefresh:
    def test_empty_candidates_clears_mart(self, engine) -> None:
        builder = MartBuilder()
        count = builder.refresh(engine, [])
        assert count == 0
        assert _read_all(engine) == []

    def test_single_candidate_written(self, engine) -> None:
        builder = MartBuilder()
        count = builder.refresh(engine, _candidates(("EURUSD", 0.85)))
        assert count == 1
        rows = _read_all(engine)
        assert len(rows) == 1
        assert rows[0]["instrument"] == "EURUSD"
        assert rows[0]["rank"] == 1

    def test_ranking_by_score_descending(self, engine) -> None:
        builder = MartBuilder()
        candidates = _candidates(("USDJPY", 0.6), ("EURUSD", 0.9), ("GBPUSD", 0.75))
        builder.refresh(engine, candidates)
        rows = _read_all(engine)
        assert rows[0]["instrument"] == "EURUSD"
        assert rows[1]["instrument"] == "GBPUSD"
        assert rows[2]["instrument"] == "USDJPY"
        assert [r["rank"] for r in rows] == [1, 2, 3]

    def test_second_refresh_updates_scores(self, engine) -> None:
        builder = MartBuilder()
        builder.refresh(engine, _candidates(("EURUSD", 0.5)))
        builder.refresh(engine, _candidates(("EURUSD", 0.9)))
        rows = _read_all(engine)
        assert len(rows) == 1
        assert abs(rows[0]["tss_score"] - 0.9) < 1e-4

    def test_tss_score_stored_correctly(self, engine) -> None:
        builder = MartBuilder()
        builder.refresh(engine, _candidates(("GBPUSD", 0.1234)))
        rows = _read_all(engine)
        assert abs(rows[0]["tss_score"] - 0.1234) < 1e-4

    def test_returns_correct_count(self, engine) -> None:
        builder = MartBuilder()
        result = builder.refresh(
            engine,
            _candidates(("EURUSD", 0.9), ("USDJPY", 0.8), ("GBPUSD", 0.7)),
        )
        assert result == 3
