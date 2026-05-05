"""Strategy cycle runner — Phase 6 Cycle 6.3.

Takes a list of StrategyEvaluator stubs plus one FeatureSet per
instrument and, within a single cycle:

  1. Generates a decision_chain_id per (cycle_id, instrument).  All
     strategies for that (cycle, instrument) share the same chain_id,
     giving Meta and Execution a stable thread to follow through the
     decision pipeline.
  2. Runs every (strategy × instrument) evaluate() call.
  3. INSERTs the resulting signal into ``strategy_signals`` (append-only,
     never UPDATE or DELETE).
  4. Enqueues the same row into ``secondary_sync_outbox`` via
     ``enqueue_secondary_sync``, respecting the F-12 sanitize gate.

Design constraints (Cycle 6.3 brief):
  - Runner is a pure function (``run_strategy_cycle``).  No internal
    loop, no sleep, no retry.
  - ``append-only`` invariant: the runner issues only INSERT
    statements.  Tests verify this.
  - At least one stub (DeterministicTrendStrategy) must produce a
    trade direction, so Cycle 6.4 Meta is guaranteed a non-degenerate
    input.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from fx_ai_trading.common.clock import Clock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.domain.feature import FeatureSet
from fx_ai_trading.domain.strategy import StrategyContext, StrategyEvaluator, StrategySignal
from fx_ai_trading.sync.enqueue import enqueue_secondary_sync

# --- Direction mapping (domain -> persistence) ------------------------------
# Domain model uses 'long' / 'short' / 'no_trade'.  The persisted
# strategy_signals.signal_direction column uses 'buy' / 'sell' /
# 'no_trade' to stay compatible with existing readers (mart_scheduler,
# tss_calculator, dashboard queries).
_DIRECTION_MAP = {"long": "buy", "short": "sell", "no_trade": "no_trade"}


def _map_direction(domain_signal: str) -> str:
    try:
        return _DIRECTION_MAP[domain_signal]
    except KeyError as e:
        raise ValueError(
            f"invalid StrategySignal.signal={domain_signal!r}; expected 'long'|'short'|'no_trade'"
        ) from e


# --- F-12 sanitizer for strategy_signals payloads ---------------------------
def _strategy_sanitizer(payload: dict[str, Any]) -> dict[str, Any]:
    """Strategy-domain sanitizer invoked before outbox enqueue.

    Strategy outputs do NOT carry secrets, but the F-12 contract
    requires every enqueue to go through a sanitizer.  We return a
    shallow copy to prevent accidental aliasing and document any
    redaction keys here as the set grows.  Today: empty redaction set.
    """
    return dict(payload)


@dataclass(frozen=True)
class StrategyRunResult:
    """Per-cycle outcome.

    Attributes:
      rows_written       : total strategy_signals rows inserted
                           (= len(instruments) * len(strategies)).
      trade_signals      : count of buy|sell rows (proves ≥1 trade exists
                           when DeterministicTrendStrategy is in the mix).
      no_trade_signals   : count of no_trade rows.
      decision_chain_ids : mapping instrument -> chain_id used this cycle.
      signals            : per-instrument signals (instrument -> StrategySignal list).
    """

    rows_written: int
    trade_signals: int
    no_trade_signals: int
    decision_chain_ids: dict[str, str]
    signals: dict[str, list[StrategySignal]]


def run_strategy_cycle(
    engine: Engine,
    *,
    cycle_id: str,
    instruments: list[str],
    strategies: list[StrategyEvaluator],
    features: dict[str, FeatureSet],
    context: StrategyContext,
    clock: Clock,
    run_id: str | None = None,
    environment: str | None = None,
    code_version: str | None = None,
    config_version: str | None = None,
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> StrategyRunResult:
    """Run one full strategy cycle and persist results.

    For each (instrument, strategy) pair:
      - call ``strategy.evaluate(instrument, features[instrument], context)``
      - translate domain direction to persistence direction
      - INSERT into ``strategy_signals``
      - enqueue into ``secondary_sync_outbox`` (F-12 sanitize applied)

    Returns a StrategyRunResult summarising the batch.  The
    ``decision_chain_ids`` mapping lets Cycle 6.4 tests pin a specific
    chain_id to assert round-tripping through meta_decisions.

    Raises:
      ValueError: on empty ``instruments`` / ``strategies`` or missing
                  FeatureSet for any instrument.
    """
    if not instruments:
        raise ValueError("instruments must be non-empty")
    if not strategies:
        raise ValueError("strategies must be non-empty")
    missing = [inst for inst in instruments if inst not in features]
    if missing:
        raise ValueError(f"missing FeatureSet for instruments: {missing}")

    san = sanitizer or _strategy_sanitizer

    now = clock.now()
    chain_ids: dict[str, str] = {inst: generate_ulid() for inst in instruments}

    rows_written = 0
    trade_signals = 0
    no_trade_signals = 0
    collected_signals: dict[str, list[StrategySignal]] = {inst: [] for inst in instruments}

    for instrument in instruments:
        feat = features[instrument]
        chain_id = chain_ids[instrument]
        for strategy in strategies:
            signal = strategy.evaluate(instrument, feat, context)
            collected_signals[instrument].append(signal)
            persisted_direction = _map_direction(signal.signal)

            meta_payload = _build_meta_payload(
                signal=signal,
                decision_chain_id=chain_id,
            )

            _insert_strategy_signal_row(
                engine,
                cycle_id=cycle_id,
                instrument=instrument,
                signal=signal,
                persisted_direction=persisted_direction,
                signal_time_utc=now,
                meta=meta_payload,
            )

            _enqueue_outbox_row(
                engine,
                cycle_id=cycle_id,
                instrument=instrument,
                signal=signal,
                persisted_direction=persisted_direction,
                signal_time_utc=now,
                meta=meta_payload,
                sanitizer=san,
                clock=clock,
                run_id=run_id,
                environment=environment,
                code_version=code_version,
                config_version=config_version,
            )

            rows_written += 1
            if persisted_direction == "no_trade":
                no_trade_signals += 1
            else:
                trade_signals += 1

    return StrategyRunResult(
        rows_written=rows_written,
        trade_signals=trade_signals,
        no_trade_signals=no_trade_signals,
        decision_chain_ids=chain_ids,
        signals=collected_signals,
    )


# --- helpers ---------------------------------------------------------------


def _build_meta_payload(*, signal: StrategySignal, decision_chain_id: str) -> dict[str, Any]:
    """Assemble the JSON meta dict persisted with each strategy_signal row.

    Why in meta JSON: the strategy_signals table (migration 0005) does
    not have dedicated columns for the StrategySignal numeric fields
    or decision_chain_id.  Storing them here lets Cycle 6.4 read them
    without a migration change.  A future cycle can promote any of
    these to first-class columns.
    """
    return {
        "decision_chain_id": decision_chain_id,
        "ev_before_cost": signal.ev_before_cost,
        "ev_after_cost": signal.ev_after_cost,
        "tp": signal.tp,
        "sl": signal.sl,
        "holding_time_seconds": signal.holding_time_seconds,
        "enabled": signal.enabled,
        "p_long": signal.p_long,
        "p_short": signal.p_short,
    }


def _insert_strategy_signal_row(
    engine: Engine,
    *,
    cycle_id: str,
    instrument: str,
    signal: StrategySignal,
    persisted_direction: str,
    signal_time_utc,  # datetime
    meta: dict[str, Any],
) -> None:
    import json

    sql = text(
        """
        INSERT INTO strategy_signals (
            cycle_id, instrument, strategy_id, strategy_type,
            strategy_version, signal_direction, confidence,
            signal_time_utc, meta
        ) VALUES (
            :cycle_id, :instrument, :strategy_id, :strategy_type,
            :strategy_version, :signal_direction, :confidence,
            :signal_time_utc, :meta
        )
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "cycle_id": cycle_id,
                "instrument": instrument,
                "strategy_id": signal.strategy_id,
                "strategy_type": signal.strategy_type,
                "strategy_version": signal.strategy_version,
                "signal_direction": persisted_direction,
                "confidence": signal.confidence,
                "signal_time_utc": signal_time_utc,
                "meta": json.dumps(meta, ensure_ascii=False, sort_keys=True),
            },
        )


def _enqueue_outbox_row(
    engine: Engine,
    *,
    cycle_id: str,
    instrument: str,
    signal: StrategySignal,
    persisted_direction: str,
    signal_time_utc,  # datetime
    meta: dict[str, Any],
    sanitizer: Callable[[dict[str, Any]], dict[str, Any]],
    clock: Clock,
    run_id: str | None,
    environment: str | None,
    code_version: str | None,
    config_version: str | None,
) -> None:
    """Enqueue one strategy_signal row into secondary_sync_outbox.

    primary_key is a JSON-encoded tuple matching the strategy_signals
    composite PK (cycle_id, instrument, strategy_id) per F-3 semantics.
    version_no is 0 because strategy_signals rows are append-only —
    each (cycle_id, instrument, strategy_id) tuple is unique, so
    version bumping is never needed.
    """
    import json

    primary_key = json.dumps([cycle_id, instrument, signal.strategy_id])
    payload = {
        "cycle_id": cycle_id,
        "instrument": instrument,
        "strategy_id": signal.strategy_id,
        "strategy_type": signal.strategy_type,
        "strategy_version": signal.strategy_version,
        "signal_direction": persisted_direction,
        "confidence": signal.confidence,
        "signal_time_utc": signal_time_utc.isoformat(),
        "meta": meta,
    }
    enqueue_secondary_sync(
        engine,
        table_name="strategy_signals",
        primary_key=primary_key,
        version_no=0,
        payload=payload,
        sanitizer=sanitizer,
        clock=clock,
        run_id=run_id,
        environment=environment,
        code_version=code_version,
        config_version=config_version,
    )


__all__ = [
    "StrategyRunResult",
    "run_strategy_cycle",
]
