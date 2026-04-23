"""``run_paper_loop`` — outside-cadence runner for the M9 exit gate (paper).

Why this exists
---------------
``Supervisor`` deliberately does not own a tick loop (Cycle 6.9a froze
that path; ``run_exit_gate_tick`` is a pure cadence seam introduced by
H-1).  A thin host loop sitting outside the Supervisor drives the
exit-gate cadence in paper mode — that is this script.

What this PR (M9 paper-stack bootstrap) ships
---------------------------------------------
- The same outside-cadence loop introduced by the previous PR
  (#141, paper-loop runner scaffold), now wired to the **production**
  paper stack instead of null-safe stubs:

    * ``StateManager`` constructed against the real DB engine
      (``DATABASE_URL`` from the env, resolved via
      ``fx_ai_trading.config.get_database_url``).
    * ``PaperBroker`` (account_type='demo') as the concrete ``Broker``.
    * ``ExitPolicyService`` with the default holding-time ceiling.
    * ``OandaQuoteFeed`` (M-3d producer) — unchanged from the scaffold
      PR.

- An open position now flows all the way through ``run_exit_gate``
  to ``StateManager.on_close``, producing a ``close_events`` row and a
  computed ``pnl_realized`` (M-2 contract: gross only).

- SIGINT triggers a graceful shutdown after the in-flight tick.  No
  SafeStop / no in-Supervisor signal handling is touched.

Logging
-------
``apply_logging_config`` from ``fx_ai_trading.ops.logging_config``
writes one JSON object per log record to ``logs/paper_loop.jsonl``
(rotating, 10 MiB × 5) and mirrors text to stdout.  Stable event names
operators can grep / jq:

  ``runner.starting``  ``runner.attached``  ``runner.env_missing``
  ``runner.db_config_missing``  ``runner.shutdown``
  ``tick.completed``  ``tick.exit_result``  ``tick.error``
  ``shutdown.signal_received``

See ``docs/runbook/phase6_paper_operator_checklist.md`` §10.

CLI
---
``python -m scripts.run_paper_loop --interval 5 --instrument EUR_USD``

Env (read at startup; CLI flags override):
  DATABASE_URL              — required (read via fx_ai_trading.config).
  OANDA_ACCESS_TOKEN        — required.
  OANDA_ACCOUNT_ID          — required.
  OANDA_ENVIRONMENT         — 'practice' (default) or 'live'.
  PAPER_LOOP_INTERVAL_SECONDS — default 5.0.
  PAPER_LOOP_INSTRUMENT     — default 'EUR_USD'.
  PAPER_LOOP_MAX_HOLDING_SECONDS — default 86400 (24h, ExitPolicyService).

Out of scope (do not add here without splitting a new PR)
---------------------------------------------------------
- ``run_exit_gate`` body changes.
- Supervisor-internal loop.
- SafeStop / schema / metrics / net pnl.
- Strategy / execution-gate / signal-generation surfaces.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.adapters.broker.paper import PaperBroker
from fx_ai_trading.adapters.price_feed.oanda_quote_feed import OandaQuoteFeed
from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.domain.price_feed import QuoteFeed
from fx_ai_trading.ops.logging_config import apply_logging_config
from fx_ai_trading.services.exit_policy import ExitPolicyService
from fx_ai_trading.services.state_manager import StateManager
from fx_ai_trading.supervisor.supervisor import Supervisor

_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_LOG_FILENAME = "paper_loop.jsonl"
_DEFAULT_INTERVAL_SECONDS = 5.0
_DEFAULT_INSTRUMENT = "EUR_USD"
_DEFAULT_OANDA_ENVIRONMENT = "practice"
_DEFAULT_MAX_HOLDING_SECONDS = 86400

_ENV_OANDA_ACCESS_TOKEN = "OANDA_ACCESS_TOKEN"
_ENV_OANDA_ACCOUNT_ID = "OANDA_ACCOUNT_ID"
_ENV_OANDA_ENVIRONMENT = "OANDA_ENVIRONMENT"
_ENV_DATABASE_URL = "DATABASE_URL"
_ENV_INTERVAL = "PAPER_LOOP_INTERVAL_SECONDS"
_ENV_INSTRUMENT = "PAPER_LOOP_INSTRUMENT"
_ENV_MAX_HOLDING_SECONDS = "PAPER_LOOP_MAX_HOLDING_SECONDS"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunnerArgs:
    interval_seconds: float
    instrument: str
    max_iterations: int
    max_holding_seconds: int
    log_dir: Path
    log_filename: str
    log_level: str


def parse_args(argv: list[str] | None = None) -> RunnerArgs:
    """Resolve runner configuration from argv + environment.

    CLI flags take precedence over env; env takes precedence over the
    module-level defaults.  Split out from ``main`` so tests can
    construct a ``RunnerArgs`` without going through ``sys.argv``.
    """
    parser = argparse.ArgumentParser(
        prog="run_paper_loop",
        description=(
            "Run the M9 exit-gate cadence outside the Supervisor against "
            "the production paper stack (PaperBroker + StateManager + "
            "ExitPolicyService + OandaQuoteFeed)."
        ),
    )
    parser.add_argument(
        "--interval",
        dest="interval_seconds",
        type=float,
        default=None,
        help=(
            f"Seconds between ticks. Falls back to ${_ENV_INTERVAL} or {_DEFAULT_INTERVAL_SECONDS}."
        ),
    )
    parser.add_argument(
        "--instrument",
        dest="instrument",
        type=str,
        default=None,
        help=(
            f"OANDA instrument the QuoteFeed is constructed against. "
            f"Falls back to ${_ENV_INSTRUMENT} or {_DEFAULT_INSTRUMENT!r}."
        ),
    )
    parser.add_argument(
        "--max-iterations",
        dest="max_iterations",
        type=int,
        default=0,
        help="Stop after N ticks (0 = run until SIGINT). Useful for smoke tests.",
    )
    parser.add_argument(
        "--max-holding-seconds",
        dest="max_holding_seconds",
        type=int,
        default=None,
        help=(
            f"ExitPolicyService max-holding-time ceiling in seconds. "
            f"Falls back to ${_ENV_MAX_HOLDING_SECONDS} or {_DEFAULT_MAX_HOLDING_SECONDS}."
        ),
    )
    parser.add_argument(
        "--log-dir",
        dest="log_dir",
        type=Path,
        default=_DEFAULT_LOG_DIR,
        help=f"Directory for the JSONL log file. Default: {_DEFAULT_LOG_DIR}",
    )
    parser.add_argument(
        "--log-filename",
        dest="log_filename",
        type=str,
        default=_DEFAULT_LOG_FILENAME,
        help=f"JSONL filename inside --log-dir. Default: {_DEFAULT_LOG_FILENAME!r}",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        type=str,
        default="INFO",
        help="Root log level. Default: INFO",
    )
    parsed = parser.parse_args(argv)

    interval = parsed.interval_seconds
    if interval is None:
        env_raw = os.environ.get(_ENV_INTERVAL, "").strip()
        interval = float(env_raw) if env_raw else _DEFAULT_INTERVAL_SECONDS
    if interval <= 0:
        parser.error(f"--interval must be > 0; got {interval!r}")

    instrument = (
        parsed.instrument or os.environ.get(_ENV_INSTRUMENT, "").strip() or _DEFAULT_INSTRUMENT
    )
    if parsed.max_iterations < 0:
        parser.error(f"--max-iterations must be >= 0; got {parsed.max_iterations!r}")

    max_holding_seconds = parsed.max_holding_seconds
    if max_holding_seconds is None:
        env_raw = os.environ.get(_ENV_MAX_HOLDING_SECONDS, "").strip()
        max_holding_seconds = int(env_raw) if env_raw else _DEFAULT_MAX_HOLDING_SECONDS
    if max_holding_seconds <= 0:
        parser.error(f"--max-holding-seconds must be > 0; got {max_holding_seconds!r}")

    return RunnerArgs(
        interval_seconds=interval,
        instrument=instrument,
        max_iterations=parsed.max_iterations,
        max_holding_seconds=max_holding_seconds,
        log_dir=parsed.log_dir,
        log_filename=parsed.log_filename,
        log_level=parsed.log_level,
    )


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OandaConfig:
    access_token: str
    account_id: str
    environment: str


def read_oanda_config_from_env(env: dict[str, str] | None = None) -> OandaConfig:
    """Pull OANDA credentials from the environment.

    Pass ``env`` explicitly in tests to avoid touching ``os.environ``.
    Raises ``RuntimeError`` if any required variable is missing — early
    fail beats a confusing 401 from oandapyV20 mid-loop.
    """
    src = env if env is not None else os.environ
    access_token = (src.get(_ENV_OANDA_ACCESS_TOKEN) or "").strip()
    account_id = (src.get(_ENV_OANDA_ACCOUNT_ID) or "").strip()
    environment = (src.get(_ENV_OANDA_ENVIRONMENT) or _DEFAULT_OANDA_ENVIRONMENT).strip()

    missing = [
        name
        for name, value in (
            (_ENV_OANDA_ACCESS_TOKEN, access_token),
            (_ENV_OANDA_ACCOUNT_ID, account_id),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("run_paper_loop: required OANDA env vars missing: " + ", ".join(missing))

    return OandaConfig(
        access_token=access_token,
        account_id=account_id,
        environment=environment,
    )


def build_db_engine(env: dict[str, str] | None = None) -> Engine:
    """Construct the SQLAlchemy ``Engine`` from ``DATABASE_URL``.

    Reads ``DATABASE_URL`` directly via the env (the dashboard +
    integration-test pattern in this repo).  Tests can monkeypatch this
    seam to return an in-memory SQLite engine without touching env or
    the real DB.  Raises ``RuntimeError`` if ``DATABASE_URL`` is unset
    or blank — caught by ``main`` and surfaced as ``rc=2``.
    """
    src = env if env is not None else os.environ
    url = (src.get(_ENV_DATABASE_URL) or "").strip()
    if not url:
        raise RuntimeError(
            "run_paper_loop: DATABASE_URL is not set. "
            "Copy .env.example to .env and fill in the connection string."
        )
    return create_engine(url)


def build_supervisor_with_paper_stack(
    *,
    oanda: OandaConfig,
    instrument: str,
    engine: Engine,
    account_id: str | None = None,
    clock: Clock | None = None,
    max_holding_seconds: int = _DEFAULT_MAX_HOLDING_SECONDS,
    api_client: OandaAPIClient | None = None,
    quote_feed: QuoteFeed | None = None,
    stale_max_age_seconds: float = 60.0,
) -> tuple[Supervisor, QuoteFeed]:
    """Construct a Supervisor wired to the production paper stack.

    Replaces the null-safe stubs from PR #141 with the real
    ``PaperBroker`` / ``StateManager`` / ``ExitPolicyService``.  Open
    positions visible to ``StateManager.open_position_details()`` will
    now flow through to ``broker.place_order`` and
    ``state_manager.on_close``.

    Args:
        oanda: OANDA credentials (also supplies the default ``account_id``).
        instrument: Instrument the OandaQuoteFeed is queried against.
        engine: SQLAlchemy engine for ``StateManager``.
        account_id: Override for the account scope; defaults to
            ``oanda.account_id``.  Useful for tests that wire a different
            scope than OANDA's account id.
        clock: Time source used by ``StateManager`` and ``Supervisor``.
            Defaults to ``WallClock()``.
        max_holding_seconds: ``ExitPolicyService`` holding ceiling.
        api_client: Optional pre-built OANDA REST client (test injection
            point so a ``MagicMock`` stand-in can replace the network
            client).

    Returns:
        ``(supervisor, feed)`` — feed is returned alongside the
        Supervisor so the caller can include it in a startup log line.
    """
    effective_account_id = account_id or oanda.account_id
    effective_clock: Clock = clock if clock is not None else WallClock()

    if quote_feed is None:
        if api_client is None:
            api_client = OandaAPIClient(
                access_token=oanda.access_token,
                environment=oanda.environment,
            )
        feed: QuoteFeed = OandaQuoteFeed(api_client=api_client, account_id=oanda.account_id)
    else:
        feed = quote_feed

    broker = PaperBroker(account_type="demo", quote_feed=feed)
    state_manager = StateManager(engine, account_id=effective_account_id, clock=effective_clock)
    exit_policy = ExitPolicyService(max_holding_seconds=max_holding_seconds)

    supervisor = Supervisor(clock=effective_clock)
    supervisor.attach_exit_gate(
        broker=broker,
        account_id=effective_account_id,
        state_manager=state_manager,
        exit_policy=exit_policy,
        quote_feed=feed,
        stale_max_age_seconds=stale_max_age_seconds,
    )
    # Stashed for log clarity — get_quote(instrument) call sites are
    # the only ones that read it; not part of the Supervisor contract.
    supervisor._exit_gate_paper_loop_instrument = instrument  # type: ignore[attr-defined]
    return supervisor, feed


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------


def _log_tick(
    log: logging.Logger,
    *,
    iteration: int,
    results: list,
    tick_duration_ms: float,
) -> None:
    """Emit one envelope line per tick + one line per ``ExitGateRunResult``."""
    log.info(
        "tick.completed",
        extra={
            "event": "tick.completed",
            "iteration": iteration,
            "results_count": len(results),
            "tick_duration_ms": round(tick_duration_ms, 3),
        },
    )
    for r in results:
        log.info(
            "tick.exit_result",
            extra={
                "event": "tick.exit_result",
                "iteration": iteration,
                "instrument": r.instrument,
                "order_id": r.order_id,
                "outcome": r.outcome,
                "primary_reason": r.primary_reason,
            },
        )


def run_loop(
    *,
    supervisor: Supervisor,
    interval_seconds: float,
    max_iterations: int,
    log: logging.Logger,
    should_stop: Callable[[], bool],
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> int:
    """Run the cadence loop until ``should_stop()`` or ``max_iterations``.

    Returns the number of completed iterations.  Factored out of
    ``main`` so tests can drive it with deterministic ``should_stop`` /
    ``sleep_fn`` / ``monotonic_fn`` doubles instead of real signals or
    real sleeps.
    """
    iteration = 0
    while not should_stop():
        iteration += 1
        tick_start = monotonic_fn()
        try:
            results = supervisor.run_exit_gate_tick()
        except Exception:
            log.exception(
                "tick.error",
                extra={"event": "tick.error", "iteration": iteration},
            )
            # Don't let a single bad tick kill the runner — the next
            # tick re-attempts.  This mirrors the M-3c stale-gate
            # philosophy: a transient feed failure is observable but
            # not fatal.
            results = []
        tick_duration_ms = (monotonic_fn() - tick_start) * 1000.0
        _log_tick(
            log,
            iteration=iteration,
            results=results,
            tick_duration_ms=tick_duration_ms,
        )

        if max_iterations and iteration >= max_iterations:
            break
        if should_stop():
            break
        sleep_fn(interval_seconds)
    return iteration


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def _install_sigint_handler(stop_flag: list[bool], log: logging.Logger) -> None:
    """Wire SIGINT → set ``stop_flag[0] = True``.

    A single-element list is used as a mutable container so the handler
    can flip the flag without ``global``.  The handler intentionally
    does **not** raise; the loop checks the flag between ticks for
    graceful shutdown.
    """

    def _handle(signum: int, _frame: object) -> None:
        # Logging from a signal handler is supported by the stdlib
        # logging module on Unix; on Windows SIGINT runs in the main
        # thread anyway so this is safe in both cases.
        log.info(
            "shutdown.signal_received",
            extra={"event": "shutdown.signal_received", "signum": int(signum)},
        )
        stop_flag[0] = True

    signal.signal(signal.SIGINT, _handle)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    log_path = apply_logging_config(
        log_dir=args.log_dir,
        filename=args.log_filename,
        level=args.log_level,
    )
    log = logging.getLogger("scripts.run_paper_loop")

    log.info(
        "runner.starting",
        extra={
            "event": "runner.starting",
            "interval_seconds": args.interval_seconds,
            "instrument": args.instrument,
            "max_iterations": args.max_iterations,
            "max_holding_seconds": args.max_holding_seconds,
            "log_path": str(log_path),
        },
    )

    try:
        oanda = read_oanda_config_from_env()
    except RuntimeError as exc:
        log.error(
            "runner.env_missing",
            extra={"event": "runner.env_missing", "detail": str(exc)},
        )
        return 2

    try:
        engine = build_db_engine()
    except RuntimeError as exc:
        log.error(
            "runner.db_config_missing",
            extra={"event": "runner.db_config_missing", "detail": str(exc)},
        )
        return 2

    try:
        supervisor, _feed = build_supervisor_with_paper_stack(
            oanda=oanda,
            instrument=args.instrument,
            engine=engine,
            max_holding_seconds=args.max_holding_seconds,
        )

        log.info(
            "runner.attached",
            extra={
                "event": "runner.attached",
                "instrument": args.instrument,
                "oanda_environment": oanda.environment,
                "account_id_suffix": oanda.account_id[-4:],
                "max_holding_seconds": args.max_holding_seconds,
                "stack": "paper",
            },
        )

        stop_flag = [False]
        _install_sigint_handler(stop_flag, log)

        iterations = run_loop(
            supervisor=supervisor,
            interval_seconds=args.interval_seconds,
            max_iterations=args.max_iterations,
            log=log,
            should_stop=lambda: stop_flag[0],
        )

        log.info(
            "runner.shutdown",
            extra={"event": "runner.shutdown", "iterations": iterations},
        )
        return 0
    finally:
        # Release pooled connections so SIGINT shutdown doesn't leave
        # idle Postgres sessions behind.  No-op on SQLite in-memory.
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
