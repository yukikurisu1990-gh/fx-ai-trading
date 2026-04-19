"""MartBuilder — writes TSS candidates into dashboard_top_candidates mart (M20).

Refresh strategy: deterministic candidate_id = "{instrument}_{strategy_id}" +
dialect-aware UPSERT (INSERT OR REPLACE on SQLite, INSERT ON CONFLICT on
PostgreSQL).  No SQL DELETE is used — this satisfies the append-only data model
contract in development_rules.md §13.1.

Caller (MartScheduler) controls cadence; no polling here.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine, text


@dataclass
class TSSCandidate:
    instrument: str
    strategy_id: str
    tss_score: float
    direction: str
    generated_at: str  # ISO 8601 UTC string


def _candidate_id(instrument: str, strategy_id: str) -> str:
    return f"{instrument}_{strategy_id}"


class MartBuilder:
    """Upsert dashboard_top_candidates with freshly ranked TSS candidates."""

    def refresh(self, engine: Engine, candidates: list[TSSCandidate]) -> int:
        """Upsert candidates ranked by tss_score descending.

        Uses INSERT OR REPLACE (SQLite) / INSERT ON CONFLICT DO UPDATE
        (PostgreSQL) to avoid SQL DELETE.  candidate_id is deterministic so
        the same row is updated on every refresh cycle.

        Returns number of rows upserted.
        """
        ranked = sorted(candidates, key=lambda c: c.tss_score, reverse=True)
        with engine.begin() as conn:
            dialect = conn.dialect.name
            for rank, c in enumerate(ranked, start=1):
                row = {
                    "cid": _candidate_id(c.instrument, c.strategy_id),
                    "inst": c.instrument,
                    "strat": c.strategy_id,
                    "score": c.tss_score,
                    "dir": c.direction,
                    "gen": c.generated_at,
                    "rank": rank,
                }
                if dialect == "sqlite":
                    conn.execute(
                        text(
                            "INSERT OR REPLACE INTO dashboard_top_candidates"
                            " (candidate_id, instrument, strategy_id, tss_score,"
                            "  direction, generated_at, rank)"
                            " VALUES (:cid, :inst, :strat, :score, :dir, :gen, :rank)"
                        ),
                        row,
                    )
                else:
                    conn.execute(
                        text(
                            "INSERT INTO dashboard_top_candidates"
                            " (candidate_id, instrument, strategy_id, tss_score,"
                            "  direction, generated_at, rank)"
                            " VALUES (:cid, :inst, :strat, :score, :dir, :gen, :rank)"
                            " ON CONFLICT (candidate_id) DO UPDATE SET"
                            "  tss_score   = EXCLUDED.tss_score,"
                            "  direction   = EXCLUDED.direction,"
                            "  generated_at = EXCLUDED.generated_at,"
                            "  rank        = EXCLUDED.rank"
                        ),
                        row,
                    )
        return len(ranked)
