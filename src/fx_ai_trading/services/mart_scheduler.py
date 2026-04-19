"""MartScheduler — coordinates periodic TSS mart refresh (M20).

Single-shot design (CLAUDE.md §14): caller checks due() and calls refresh()
on its own timer.  No while loop, no polling inside this class.

Refresh interval: 15 minutes (INTERVAL_SECONDS = 900).
Instruments: USDJPY, EURUSD, GBPUSD (Iteration 2 scope).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import Engine, text

from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.services.mart_builder import MartBuilder, TSSCandidate
from fx_ai_trading.services.tss_calculator import TSSCalculator

log = logging.getLogger(__name__)

_STRATEGY_ID = "AI"


class MartScheduler:
    """Coordinates TSS calculation → mart write on a configurable interval."""

    INTERVAL_SECONDS: int = 900  # 15 minutes

    def __init__(
        self,
        engine: Engine,
        calculator: TSSCalculator | None = None,
        builder: MartBuilder | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._engine = engine
        self._calculator = calculator or TSSCalculator()
        self._builder = builder or MartBuilder()
        self._clock: Clock = clock or WallClock()
        self._last_refresh: datetime | None = None

    def due(self) -> bool:
        """Return True if a refresh is due (first call or interval elapsed)."""
        if self._last_refresh is None:
            return True
        elapsed = (self._clock.now() - self._last_refresh).total_seconds()
        return elapsed >= self.INTERVAL_SECONDS

    def refresh(self) -> int:
        """Query strategy_signals, compute TSS, write mart. Returns rows written."""
        candidates = self._fetch_candidates()
        count = self._builder.refresh(self._engine, candidates)
        self._last_refresh = self._clock.now()
        log.debug("mart refresh: %d candidates written", count)
        return count

    def _fetch_candidates(self) -> list[TSSCandidate]:
        """Read recent strategy_signals and compute a TSSCandidate per instrument."""
        generated_at = self._clock.now().replace(tzinfo=UTC).isoformat()
        candidates: list[TSSCandidate] = []
        for instrument in sorted(TSSCalculator.INSTRUMENTS):
            signals = self._query_signals(instrument)
            result = self._calculator.compute(instrument, signals)
            if result is None:
                continue
            candidates.append(
                TSSCandidate(
                    instrument=instrument,
                    strategy_id=_STRATEGY_ID,
                    tss_score=result.score,
                    direction=result.direction,
                    generated_at=generated_at,
                )
            )
        return candidates

    def _query_signals(self, instrument: str) -> list[dict]:
        """Return the most recent cycle's strategy_signals for *instrument*."""
        try:
            with self._engine.connect() as conn:
                rows = (
                    conn.execute(
                        text(
                            "SELECT signal_direction, confidence"
                            " FROM strategy_signals"
                            " WHERE instrument = :inst"
                            " ORDER BY signal_time_utc DESC"
                            " LIMIT 20"
                        ),
                        {"inst": instrument},
                    )
                    .mappings()
                    .all()
                )
            return [dict(r) for r in rows]
        except Exception:
            log.warning("strategy_signals query failed for %s", instrument)
            return []
