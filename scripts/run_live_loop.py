"""``run_live_loop`` — outside-cadence runner for the M9 exit gate (live demo).

Why this exists separately from ``run_paper_loop``
--------------------------------------------------
``run_paper_loop`` drives the same exit-gate cadence using ``PaperBroker``,
which is an in-process fake fill.  This module drives the same cadence
but against the **real OANDA REST broker** in **demo (practice) mode** —
no live money is at risk, but actual HTTP requests reach OANDA's
practice account.

Operators (and grep) can tell which runner is active at a glance because
the log filename and env-var prefix differ:

  run_paper_loop:  logs/paper_loop.jsonl  / PAPER_LOOP_* env
  run_live_loop:   logs/live_loop.jsonl   / LIVE_LOOP_*  env

The OANDA credentials env vars (``OANDA_ACCESS_TOKEN`` / ``OANDA_ACCOUNT_ID``
/ ``OANDA_ENVIRONMENT``) are shared with the paper runner.

Safety contract
---------------
- ``OandaBroker(account_type="demo")`` is constructed unconditionally.
  Even if a future bug widens this, ``OandaBroker.place_order`` calls
  ``_verify_account_type_or_raise`` before every HTTP request (the 6.18
  invariant), so live-money trading remains gated by
  ``expected_account_type`` at the broker layer.
- No ``--confirm-live-trading`` flag is wired here.  That work belongs
  to M13b together with the demo↔live SQL runbook (operations.md Step 9).
- SIGINT triggers a graceful shutdown after the in-flight tick.  No
  SafeStop / no in-Supervisor signal handling is touched.

Logging
-------
``apply_logging_config`` from ``fx_ai_trading.ops.logging_config`` writes
one JSON object per log record to ``logs/live_loop.jsonl`` (rotating,
10 MiB × 5) and mirrors text to stdout.  Stable event names (mirroring
the paper runner so dashboards / runbooks can reuse jq filters):

  ``runner.starting``  ``runner.attached``  ``runner.env_missing``
  ``runner.db_config_missing``  ``runner.shutdown``
  ``tick.completed``  ``tick.exit_result``  ``tick.error``
  ``shutdown.signal_received``

The ``runner.attached`` line carries ``"stack": "live-demo"`` so an
operator running ``jq 'select(.event=="runner.attached") | .stack'``
across both files can disambiguate without parsing the filename.

CLI
---
``python -m scripts.run_live_loop --interval 5 --instrument EUR_USD``

Env (read at startup; CLI flags override):
  DATABASE_URL                  — required.
  OANDA_ACCESS_TOKEN            — required.
  OANDA_ACCOUNT_ID              — required.
  OANDA_ENVIRONMENT             — 'practice' (default) or 'live'.
  LIVE_LOOP_INTERVAL_SECONDS    — default 5.0.
  LIVE_LOOP_INSTRUMENT          — default 'EUR_USD'.
  LIVE_LOOP_MAX_HOLDING_SECONDS — default 86400 (24h).

Out of scope (do not add here without splitting a new PR)
---------------------------------------------------------
- ``--confirm-live-trading`` flag wiring (M13b).
- Demo↔live runtime switch (M13b + operations.md Step 9).
- Supervisor-internal loop / SafeStop / schema / metrics / net pnl.
- Strategy / execution-gate / signal-generation surfaces.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from fx_ai_trading.adapters.broker.oanda import OandaBroker
from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.adapters.price_feed.oanda_quote_feed import OandaQuoteFeed
from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.domain.price_feed import QuoteFeed
from fx_ai_trading.ops.logging_config import apply_logging_config
from fx_ai_trading.services.exit_policy import ExitPolicyService
from fx_ai_trading.services.state_manager import StateManager
from fx_ai_trading.supervisor.supervisor import Supervisor

# Reuse the paper runner's loop / signal / OANDA-config helpers — they
# are framework-free and equally correct for the live-demo stack.
from scripts.run_paper_loop import (
    OandaConfig,
    _install_sigint_handler,
    run_loop,
)

_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_LOG_FILENAME = "live_loop.jsonl"
_DEFAULT_INTERVAL_SECONDS = 5.0
_DEFAULT_INSTRUMENT = "EUR_USD"
_DEFAULT_OANDA_ENVIRONMENT = "practice"
_DEFAULT_MAX_HOLDING_SECONDS = 86400

_ENV_OANDA_ACCESS_TOKEN = "OANDA_ACCESS_TOKEN"
_ENV_OANDA_ACCOUNT_ID = "OANDA_ACCOUNT_ID"
_ENV_OANDA_ENVIRONMENT = "OANDA_ENVIRONMENT"
_ENV_DATABASE_URL = "DATABASE_URL"
_ENV_INTERVAL = "LIVE_LOOP_INTERVAL_SECONDS"
_ENV_INSTRUMENT = "LIVE_LOOP_INSTRUMENT"
_ENV_MAX_HOLDING_SECONDS = "LIVE_LOOP_MAX_HOLDING_SECONDS"


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
    module-level defaults.  Mirrors ``run_paper_loop.parse_args`` but
    advertises ``LIVE_LOOP_*`` env names in --help text and defaults the
    log filename to ``live_loop.jsonl``.
    """
    parser = argparse.ArgumentParser(
        prog="run_live_loop",
        description=(
            "Run the M9 exit-gate cadence outside the Supervisor against "
            "the live-demo stack (OandaBroker + StateManager + "
            "ExitPolicyService + OandaQuoteFeed).  account_type is "
            "hard-pinned to 'demo'; no live-money path is reachable from "
            "this script (M13b territory)."
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


def read_oanda_config_from_env(env: dict[str, str] | None = None) -> OandaConfig:
    """Pull OANDA credentials from the environment (live-loop variant).

    Same semantics as ``run_paper_loop.read_oanda_config_from_env`` but
    error messages are scoped to ``run_live_loop`` so a missing-env log
    line points at the right script.
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
        raise RuntimeError("run_live_loop: required OANDA env vars missing: " + ", ".join(missing))

    return OandaConfig(
        access_token=access_token,
        account_id=account_id,
        environment=environment,
    )


def build_db_engine(env: dict[str, str] | None = None) -> Engine:
    """Construct the SQLAlchemy ``Engine`` from ``DATABASE_URL`` (live-loop variant)."""
    src = env if env is not None else os.environ
    url = (src.get(_ENV_DATABASE_URL) or "").strip()
    if not url:
        raise RuntimeError(
            "run_live_loop: DATABASE_URL is not set. "
            "Copy .env.example to .env and fill in the connection string."
        )
    return create_engine(url)


def build_supervisor_with_live_demo_stack(
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
    """Construct a Supervisor wired to the live-demo stack.

    Differs from ``build_supervisor_with_paper_stack`` in exactly one
    place: the broker is ``OandaBroker(account_type="demo")`` instead
    of ``PaperBroker``.  Everything else (StateManager, ExitPolicyService,
    OandaQuoteFeed, attach_exit_gate wiring) is identical so the M9 exit
    contract is unchanged.

    Args:
        oanda: OANDA credentials (also supplies the default ``account_id``).
        instrument: Instrument the OandaQuoteFeed is queried against.
        engine: SQLAlchemy engine for ``StateManager``.
        account_id: Override for the account scope; defaults to
            ``oanda.account_id``.
        clock: Time source; defaults to ``WallClock()``.
        max_holding_seconds: ``ExitPolicyService`` holding ceiling.
        api_client: Optional pre-built OANDA REST client (test injection
            point).  Shared between the broker and the quote feed when
            both are constructed here so we issue exactly one REST
            client per runner.
        quote_feed: Optional pre-built ``QuoteFeed``.

    Returns:
        ``(supervisor, feed)`` — feed is returned alongside the
        Supervisor so the caller can include it in a startup log line.
    """
    effective_account_id = account_id or oanda.account_id
    effective_clock: Clock = clock if clock is not None else WallClock()

    if api_client is None:
        api_client = OandaAPIClient(
            access_token=oanda.access_token,
            environment=oanda.environment,
        )

    if quote_feed is None:
        feed: QuoteFeed = OandaQuoteFeed(api_client=api_client, account_id=oanda.account_id)
    else:
        feed = quote_feed

    broker = OandaBroker(
        account_id=oanda.account_id,
        access_token=oanda.access_token,
        account_type="demo",
        environment=oanda.environment,
        api_client=api_client,
    )
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
    supervisor._exit_gate_live_loop_instrument = instrument  # type: ignore[attr-defined]
    return supervisor, feed


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    log_path = apply_logging_config(
        log_dir=args.log_dir,
        filename=args.log_filename,
        level=args.log_level,
    )
    log = logging.getLogger("scripts.run_live_loop")

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
        supervisor, _feed = build_supervisor_with_live_demo_stack(
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
                "stack": "live-demo",
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
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
