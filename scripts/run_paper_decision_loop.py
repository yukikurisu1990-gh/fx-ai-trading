"""``run_paper_decision_loop`` — D3 bar-cadence decision runner (Phase 9.1/9.2).

Wires the full D3 pipeline for paper trading:

  BarFeed  →  FeatureService  →  run_strategy_cycle  →  run_meta_cycle
                                                              ↓
                                                    MetaDecision (logged)
                                                              ↓
                                               (if trade + not --dry-run)
                                                    open position (paper)

Phase 1 invariants enforced:
  I-1  : decisions at bar cadence (1m/5m Candle), not tick cadence.
  I-5  : MetaDeciderService scores by ev_after_cost.
  I-6  : run_strategy_cycle writes ALL candidate signals (enabled/disabled).
  I-7  : FeatureService is deterministic (same bars → same FeatureSet).
  I-8  : Instrument list fetched dynamically from OANDA (live mode).

Modes:
  replay  --replay-candles <path> --instrument <sym>
            Reads a fetch_oanda_candles JSONL. Single instrument. No OANDA creds needed.
  live    (no --replay-candles)
            Polls OANDA for bar closes. Instruments from OandaInstrumentRegistry
            unless --instrument overrides to a single pair.

Usage:
  # Replay
  python -m scripts.run_paper_decision_loop \\
    --account-id <id> --instrument EUR_USD \\
    --replay-candles data/eurusd_m5.jsonl [--dry-run]

  # Live (dynamic all-pair)
  python -m scripts.run_paper_decision_loop \\
    --account-id <id> [--dry-run]

Environment variables:
  DATABASE_URL        — required.
  OANDA_ACCOUNT_ID    — used if --account-id omitted.
  OANDA_ACCESS_TOKEN  — required in live mode.
"""

from __future__ import annotations

import argparse
import logging
import os
import platform
import sys
from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from fx_ai_trading.adapters.instrument_registry import OandaInstrumentRegistry
from fx_ai_trading.adapters.price_feed.candle_file_bar_feed import CandleFileBarFeed
from fx_ai_trading.adapters.price_feed.oanda_bar_feed import OandaBarFeed
from fx_ai_trading.common.clock import WallClock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.domain.price_feed import Candle
from fx_ai_trading.ops.logging_config import apply_logging_config
from fx_ai_trading.services.feature_service import FeatureService
from fx_ai_trading.services.meta_cycle_runner import run_meta_cycle
from fx_ai_trading.services.strategies.atr import ATRStrategy
from fx_ai_trading.services.strategies.bollinger import BollingerStrategy
from fx_ai_trading.services.strategies.ma import MAStrategy
from fx_ai_trading.services.strategies.macd import MACDStrategy
from fx_ai_trading.services.strategies.rsi import RSIStrategy
from fx_ai_trading.services.strategy_runner import run_strategy_cycle

if TYPE_CHECKING:
    from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient

_log = logging.getLogger(__name__)

_ENV_DATABASE_URL = "DATABASE_URL"
_ENV_OANDA_ACCOUNT_ID = "OANDA_ACCOUNT_ID"
_ENV_OANDA_ACCESS_TOKEN = "OANDA_ACCESS_TOKEN"

# Rolling bar history depth for FeatureService (SMA_50 needs ≥50 bars).
_HISTORY_DEPTH = 100


# ---------------------------------------------------------------------------
# Args
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="D3 bar-cadence paper decision loop (Phase 9.1/9.2)",
    )
    p.add_argument("--account-id", default=os.environ.get(_ENV_OANDA_ACCOUNT_ID, ""))
    p.add_argument(
        "--instrument",
        default=None,
        help=(
            "Single instrument override (e.g. EUR_USD). "
            "In live mode, omit to use all active instruments from OandaInstrumentRegistry (I-8). "
            "Required in replay mode."
        ),
    )
    p.add_argument(
        "--replay-candles",
        default=None,
        metavar="PATH",
        help="Path to fetch_oanda_candles JSONL (replay mode). Omit for live OANDA polling.",
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


def _build_oanda_client(src: dict[str, str]) -> OandaAPIClient:
    from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient

    token = (src.get(_ENV_OANDA_ACCESS_TOKEN) or "").strip()
    if not token:
        raise SystemExit(
            f"run_paper_decision_loop: {_ENV_OANDA_ACCESS_TOKEN} is not set"
            " (required for live mode)."
        )
    return OandaAPIClient(access_token=token, environment="practice")


def _warmup_history(
    client: OandaAPIClient,
    instruments: list[str],
    granularity: str,
    history: dict[str, deque],
    depth: int,
) -> None:
    """Pre-fill rolling candle history from OANDA (live mode warmup)."""
    from fx_ai_trading.adapters.price_feed.oanda_bar_feed import _parse_oanda_time

    for inst in instruments:
        try:
            response = client.get_candles(
                inst,
                params={"granularity": granularity, "count": depth, "price": "M"},
            )
            for raw in response.get("candles", []):
                if not raw.get("complete", True):
                    continue
                mid = raw["mid"]
                history[inst].append(
                    Candle(
                        instrument=inst,
                        tier=granularity,
                        time_utc=_parse_oanda_time(raw["time"]),
                        open=float(mid["o"]),
                        high=float(mid["h"]),
                        low=float(mid["l"]),
                        close=float(mid["c"]),
                        volume=int(raw.get("volume", 0)),
                    )
                )
            _log.info("warmup: %s — %d bars loaded", inst, len(history[inst]))
        except Exception:
            _log.warning("warmup failed for %s — starting with empty history", inst, exc_info=True)


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

    is_live = args.replay_candles is None

    if is_live and args.instrument is None:
        # Live + dynamic all-pair mode (I-8).
        oanda_client = _build_oanda_client(src)
        registry = OandaInstrumentRegistry(oanda_client, account_id)
        active_instruments = registry.list_active()
        if not active_instruments:
            raise SystemExit(
                "run_paper_decision_loop: OandaInstrumentRegistry returned no instruments."
            )
        reference_instrument = active_instruments[0]
        _log.info("live mode: %d instruments from registry", len(active_instruments))
    elif is_live:
        oanda_client = _build_oanda_client(src)
        registry = None
        active_instruments = [args.instrument]
        reference_instrument = args.instrument
    else:
        # Replay mode — single instrument, no OANDA creds needed.
        if args.instrument is None:
            raise SystemExit("run_paper_decision_loop: --instrument is required in replay mode.")
        oanda_client = None
        registry = None
        active_instruments = [args.instrument]
        reference_instrument = args.instrument

    engine = _build_engine(src)
    clock = WallClock()
    run_id = generate_ulid()

    _log.info(
        "run_paper_decision_loop starting",
        extra={
            "run_id": run_id,
            "mode": "live" if is_live else "replay",
            "instruments": active_instruments,
            "granularity": args.granularity,
            "dry_run": args.dry_run,
        },
    )

    _insert_system_job(engine, run_id=run_id, instrument=reference_instrument, dry_run=args.dry_run)

    strategies = [
        MAStrategy(strategy_id="ma"),
        ATRStrategy(strategy_id="atr"),
        RSIStrategy(strategy_id="rsi"),
        MACDStrategy(strategy_id="macd"),
        BollingerStrategy(strategy_id="bollinger"),
    ]

    # Rolling per-instrument candle history (fed before FeatureService.build).
    history: dict[str, deque] = {inst: deque(maxlen=_HISTORY_DEPTH) for inst in active_instruments}
    feature_service = _make_feature_service(history)

    # Live mode: warmup history for all instruments before starting loop.
    if is_live and oanda_client is not None:
        _warmup_history(oanda_client, active_instruments, args.granularity, history, _HISTORY_DEPTH)

    # Build BarFeed.
    if is_live:
        assert oanda_client is not None
        bar_feed: object = OandaBarFeed(
            oanda_client,
            instrument=reference_instrument,
            granularity=args.granularity,
        )
    else:
        bar_feed = CandleFileBarFeed(
            path=args.replay_candles,
            instrument=reference_instrument,
            granularity=args.granularity,
        )

    cycles_completed = 0

    try:
        for bar in bar_feed:  # type: ignore[union-attr]
            # Accumulate reference bar into history (no look-ahead).
            history[reference_instrument].append(bar)

            # In live multi-instrument mode, refresh instrument list each cycle (I-8).
            if is_live and registry is not None:
                current_instruments = registry.list_active()
                for inst in current_instruments:
                    if inst not in history:
                        history[inst] = deque(maxlen=_HISTORY_DEPTH)
            else:
                current_instruments = active_instruments

            cycle_id = generate_ulid()

            from fx_ai_trading.domain.strategy import StrategyContext

            context = StrategyContext(
                cycle_id=cycle_id,
                account_id=account_id,
                config_version="v1",
                # Phase 9.4: read config_version from app_settings.
            )

            # Build FeatureSet for each instrument.
            features = {}
            for inst in current_instruments:
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
