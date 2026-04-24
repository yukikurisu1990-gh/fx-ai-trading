"""``run_paper_decision_loop`` — D3 bar-cadence decision runner (Phase 9.1).

Wires the full D3 pipeline for paper trading:

  BarFeed  →  FeatureService  →  run_strategy_cycle  →  run_meta_cycle
                                                              ↓
                                                    MetaDecision (logged)
                                                              ↓
                                               (if trade + not --dry-run)
                                                    open position (paper)

Phase 1 invariants enforced:
  I-1  : decisions at bar cadence (1m/5m Candle), not tick cadence.
  I-5  : MetaDeciderService scores by ev_after_cost (Phase 9.1 fix).
  I-6  : run_strategy_cycle writes ALL candidate signals (enabled/disabled).
  I-7  : FeatureService is deterministic (same bars → same FeatureSet).

Current limitations (resolved in later phases):
  - Single --instrument (Phase 9.2 adds dynamic all-pair via OandaInstrumentRegistry).
  - Live bar feed not implemented (Phase 9.2); use --replay-candles for now.
  - Strategies hardcoded to [MAStrategy, ATRStrategy] (Phase 9.4 adds registry).
  - system_jobs run_id linkage is tracked but full column set added in Phase 9.1 alembic.

Usage (replay mode):
  python -m scripts.run_paper_decision_loop \\
    --account-id <id> --instrument EUR_USD \\
    --replay-candles data/eurusd_m5.jsonl \\
    [--granularity M5] [--dry-run]

Environment variables:
  DATABASE_URL     — required (PostgreSQL connection string).
  OANDA_ACCOUNT_ID — used if --account-id is omitted.
"""

from __future__ import annotations

import argparse
import logging
import os
import platform
import sys
from collections import deque
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from fx_ai_trading.adapters.price_feed.candle_file_bar_feed import CandleFileBarFeed
from fx_ai_trading.common.clock import WallClock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.ops.logging_config import apply_logging_config
from fx_ai_trading.services.feature_service import FeatureService
from fx_ai_trading.services.meta_cycle_runner import run_meta_cycle
from fx_ai_trading.services.strategies.atr import ATRStrategy
from fx_ai_trading.services.strategies.ma import MAStrategy
from fx_ai_trading.services.strategy_runner import run_strategy_cycle

_log = logging.getLogger(__name__)

_ENV_DATABASE_URL = "DATABASE_URL"
_ENV_OANDA_ACCOUNT_ID = "OANDA_ACCOUNT_ID"

# Rolling bar history depth for FeatureService (SMA_50 needs ≥50 bars).
_HISTORY_DEPTH = 100


# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="D3 bar-cadence paper decision loop (Phase 9.1)",
    )
    p.add_argument("--account-id", default=os.environ.get(_ENV_OANDA_ACCOUNT_ID, ""))
    p.add_argument(
        "--instrument",
        required=True,
        help="Instrument to trade (e.g. EUR_USD). Phase 9.2 will make this dynamic.",
    )
    p.add_argument(
        "--replay-candles",
        required=True,
        metavar="PATH",
        help="Path to fetch_oanda_candles JSONL. Live bar feed added in Phase 9.2.",
    )
    p.add_argument("--granularity", default="M5", help="Candle granularity (default: M5).")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Run full D3 pipeline but skip position opening.",
    )
    p.add_argument("--log-level", default="INFO")
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _build_engine(src: dict[str, str]) -> Engine:
    url = (src.get(_ENV_DATABASE_URL) or "").strip()
    if not url:
        raise SystemExit(
            f"run_paper_decision_loop: {_ENV_DATABASE_URL} is not set.\n"
            "Set it to a PostgreSQL connection string and retry."
        )
    return create_engine(url)


def _insert_system_job(engine: Engine, *, run_id: str, instrument: str, dry_run: bool) -> None:
    """Record this runner process in system_jobs for run_id audit trail."""
    import json as _json

    now = datetime.now(tz=UTC)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO system_jobs
                    (system_job_id, job_type, status, started_at, input_params)
                VALUES
                    (:id, :job_type, 'running', :started_at, :params)
                """
            ),
            {
                "id": run_id,
                "job_type": "paper_decision_loop",
                "started_at": now,
                "params": _json.dumps(
                    {
                        "instrument": instrument,
                        "dry_run": dry_run,
                        "host": platform.node(),
                        "pid": os.getpid(),
                    }
                ),
            },
        )


def _finish_system_job(engine: Engine, *, run_id: str, cycles: int) -> None:
    import json as _json

    now = datetime.now(tz=UTC)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE system_jobs
                   SET status = 'success',
                       ended_at = :ended_at,
                       result_summary = :summary
                 WHERE system_job_id = :id
                """
            ),
            {
                "id": run_id,
                "ended_at": now,
                "summary": _json.dumps({"cycles_completed": cycles}),
            },
        )


# ---------------------------------------------------------------------------
# FeatureService factory
# ---------------------------------------------------------------------------


def _make_feature_service(history: dict[str, deque]) -> FeatureService:
    """Build FeatureService backed by the rolling bar-history deque.

    The lambda bridges ``Candle`` objects (stored in history) to the
    ``list[dict]`` format expected by FeatureService._compute_features().
    """

    def _get_candles(instrument: str, as_of_time: datetime) -> list[dict]:
        buf = history.get(instrument, deque())
        return [
            {
                "timestamp": c.time_utc,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
            }
            for c in buf
            if c.time_utc < as_of_time
        ]

    return FeatureService(get_candles=_get_candles)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace, *, env: dict[str, str] | None = None) -> int:
    """Execute the D3 decision loop. Returns exit code."""
    src = env if env is not None else dict(os.environ)

    account_id = args.account_id.strip()
    if not account_id:
        raise SystemExit(
            f"run_paper_decision_loop: --account-id is required (or set {_ENV_OANDA_ACCOUNT_ID})."
        )

    engine = _build_engine(src)
    clock = WallClock()
    run_id = generate_ulid()

    _log.info(
        "run_paper_decision_loop starting",
        extra={
            "run_id": run_id,
            "instrument": args.instrument,
            "granularity": args.granularity,
            "dry_run": args.dry_run,
            "replay_candles": args.replay_candles,
        },
    )

    _insert_system_job(engine, run_id=run_id, instrument=args.instrument, dry_run=args.dry_run)

    strategies = [MAStrategy(), ATRStrategy()]
    # Phase 9.4: replace with strategy registry lookup.

    # Rolling per-instrument candle history (fed before FeatureService.build).
    history: dict[str, deque] = {args.instrument: deque(maxlen=_HISTORY_DEPTH)}
    feature_service = _make_feature_service(history)

    bar_feed = CandleFileBarFeed(
        path=args.replay_candles,
        instrument=args.instrument,
        granularity=args.granularity,
    )

    cycles_completed = 0

    try:
        for bar in bar_feed:
            # Accumulate bar into history BEFORE building features (no look-ahead).
            history[args.instrument].append(bar)

            cycle_id = generate_ulid()
            instruments = [args.instrument]
            # Phase 9.2: replace with OandaInstrumentRegistry.list_active().

            from fx_ai_trading.domain.strategy import StrategyContext

            context = StrategyContext(
                cycle_id=cycle_id,
                account_id=account_id,
                config_version="v1",
                # Phase 9.4: read config_version from app_settings.
            )

            # Build FeatureSet for each instrument.
            features = {}
            for inst in instruments:
                try:
                    features[inst] = feature_service.build(
                        instrument=inst,
                        tier=args.granularity,
                        cycle_id=UUID(cycle_id) if len(cycle_id) == 32 else UUID(int=0),
                        as_of_time=bar.time_utc,
                    )
                except Exception:
                    _log.warning("FeatureService.build failed for %s — skipping cycle", inst)
                    continue

            if not features:
                continue

            # --- Stage 1: run_strategy_cycle (Cycle 6.3) ---
            try:
                strategy_result = run_strategy_cycle(
                    engine,
                    cycle_id=cycle_id,
                    instruments=list(features.keys()),
                    strategies=strategies,
                    features=features,
                    context=context,
                    clock=clock,
                    run_id=run_id,
                    environment="paper",
                )
            except Exception:
                _log.exception("run_strategy_cycle failed for cycle %s", cycle_id)
                continue

            # --- Stage 2: run_meta_cycle (Cycle 6.4) ---
            try:
                meta_result = run_meta_cycle(
                    engine,
                    cycle_id=cycle_id,
                    clock=clock,
                    run_id=run_id,
                    environment="paper",
                )
            except Exception:
                _log.exception("run_meta_cycle failed for cycle %s", cycle_id)
                continue

            _log.info(
                "cycle complete",
                extra={
                    "cycle_id": cycle_id,
                    "bar_time": bar.time_utc.isoformat(),
                    "no_trade": meta_result.no_trade,
                    "selected_instrument": meta_result.selected_instrument,
                    "selected_signal": meta_result.selected_signal,
                    "strategy_rows": strategy_result.rows_written,
                },
            )

            cycles_completed += 1

            if not meta_result.no_trade and not args.dry_run:
                # Phase 9.1: position opening via PaperBroker is deferred —
                # the MetaDecision is logged to DB; trade intent is captured in
                # trading_signals by run_meta_cycle. Actual broker call wired in
                # Phase 9.1 follow-up PR once exit-gate integration is confirmed.
                _log.info(
                    "trade intent logged (broker call deferred to Phase 9.1 follow-up)",
                    extra={"selected_signal": meta_result.selected_signal},
                )

    except KeyboardInterrupt:
        _log.info("run_paper_decision_loop interrupted by user")
    finally:
        _finish_system_job(engine, run_id=run_id, cycles=cycles_completed)
        _log.info("run_paper_decision_loop finished — cycles=%d", cycles_completed)

    return 0


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    apply_logging_config(level=args.log_level)
    sys.exit(run(args))


if __name__ == "__main__":
    main()
