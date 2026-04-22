"""``run_paper_loop`` — outside-cadence runner for the M9 exit gate (paper).

Why this exists
---------------
``Supervisor`` deliberately does not own a tick loop (Cycle 6.9a froze
that path; ``run_exit_gate_tick`` is a pure cadence seam introduced by
H-1).  The first PR that brings live OANDA pricing into the runtime
needs a *thin host loop* sitting outside the Supervisor — that is this
script.

What this PR (M9 paper-loop runner scaffold) ships
--------------------------------------------------
- A loop that calls ``Supervisor.run_exit_gate_tick`` on a fixed
  cadence and observes the returned ``ExitGateRunResult`` list,
  emitting one structured log line per result plus one envelope log
  line per tick.
- An ``OandaQuoteFeed`` (M-3d producer) constructed from environment
  variables and attached via ``Supervisor.attach_exit_gate``.
- ``broker`` / ``state_manager`` / ``exit_policy`` are wired to the
  null-safe stubs in ``fx_ai_trading.ops.null_safe_stubs`` so the tick
  is a *wiring verification* — ``open_position_details()`` returns
  ``[]`` and the close path is never reached.  The production paper
  stack bootstrap is a separate responsibility (next PR in the M9 ops
  sub-series).
- SIGINT triggers a graceful shutdown after the in-flight tick
  completes.  No SafeStop / no in-Supervisor signal handling is
  touched (those live in ``ctl.py`` / SafeStop journal).

Logging
-------
``apply_logging_config`` from ``fx_ai_trading.ops.logging_config``
writes one JSON object per log record to
``logs/paper_loop.jsonl`` (rotating, 10 MiB × 5) and mirrors text to
stdout.  Two stable event names operators can grep / jq:

  ``tick.completed``    — one line per tick.  Fields: iteration,
                          results_count, tick_duration_ms.
  ``tick.exit_result``  — one line per ``ExitGateRunResult``.  Fields:
                          iteration, instrument, order_id, outcome,
                          primary_reason.

Both use the standard envelope (ts / level / logger / message); see
``docs/runbook/phase6_paper_operator_checklist.md`` for ``jq`` recipes.

CLI
---
``python -m scripts.run_paper_loop --interval 5 --instrument EUR_USD``

Env (read at startup; CLI flags override):
  OANDA_ACCESS_TOKEN        — required.
  OANDA_ACCOUNT_ID          — required.
  OANDA_ENVIRONMENT         — 'practice' (default) or 'live'.
  PAPER_LOOP_INTERVAL_SECONDS — default 5.0.
  PAPER_LOOP_INSTRUMENT     — default 'EUR_USD'.

Out of scope (do not add here without splitting a new PR)
---------------------------------------------------------
- Production paper stack (real Broker / StateManager / ExitPolicy).
- ``run_exit_gate`` body changes / new ``logger.info`` inside the
  exit hot path.
- Supervisor-internal loop.
- SafeStop / schema / metrics / net pnl.
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

from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.adapters.price_feed.oanda_quote_feed import OandaQuoteFeed
from fx_ai_trading.common.clock import WallClock
from fx_ai_trading.ops.logging_config import apply_logging_config
from fx_ai_trading.ops.null_safe_stubs import (
    NullBroker,
    NullExitPolicy,
    NullStateManager,
)
from fx_ai_trading.supervisor.supervisor import Supervisor

_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_LOG_FILENAME = "paper_loop.jsonl"
_DEFAULT_INTERVAL_SECONDS = 5.0
_DEFAULT_INSTRUMENT = "EUR_USD"
_DEFAULT_OANDA_ENVIRONMENT = "practice"

_ENV_OANDA_ACCESS_TOKEN = "OANDA_ACCESS_TOKEN"
_ENV_OANDA_ACCOUNT_ID = "OANDA_ACCOUNT_ID"
_ENV_OANDA_ENVIRONMENT = "OANDA_ENVIRONMENT"
_ENV_INTERVAL = "PAPER_LOOP_INTERVAL_SECONDS"
_ENV_INSTRUMENT = "PAPER_LOOP_INSTRUMENT"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunnerArgs:
    interval_seconds: float
    instrument: str
    max_iterations: int
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
            "Run the M9 exit-gate cadence outside the Supervisor for "
            "paper-mode wiring verification (next PR adds the real paper stack)."
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

    return RunnerArgs(
        interval_seconds=interval,
        instrument=instrument,
        max_iterations=parsed.max_iterations,
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


def build_supervisor_with_oanda_feed(
    *,
    oanda: OandaConfig,
    instrument: str,
    api_client: OandaAPIClient | None = None,
) -> tuple[Supervisor, OandaQuoteFeed]:
    """Construct a Supervisor + ``OandaQuoteFeed`` and attach the exit gate.

    ``api_client`` is exposed for tests so a ``MagicMock`` oandapyV20
    surface can stand in for the real network client.

    The exit gate is wired with ``NullBroker`` / ``NullStateManager`` /
    ``NullExitPolicy`` so the tick is a wiring verification (no
    positions → no broker calls).  Returns the feed alongside the
    Supervisor so the caller can include it in a startup log line.
    """
    if api_client is None:
        api_client = OandaAPIClient(
            access_token=oanda.access_token,
            environment=oanda.environment,
        )
    feed = OandaQuoteFeed(api_client=api_client, account_id=oanda.account_id)

    supervisor = Supervisor(clock=WallClock())
    supervisor.attach_exit_gate(
        broker=NullBroker(),
        account_id=oanda.account_id,
        state_manager=NullStateManager(account_id=oanda.account_id),
        exit_policy=NullExitPolicy(),
        quote_feed=feed,
    )
    # The instrument is held by the feed conceptually but only used at
    # ``get_quote(instrument)`` call sites.  Stashed for log clarity.
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
    """Emit one envelope line per tick + one line per ``ExitGateRunResult``.

    Wiring verification mode: ``results`` is always ``[]`` so only the
    envelope line fires.  Once the production paper stack lands in the
    next PR, the per-result line will start carrying real ``outcome``
    / ``primary_reason`` values.
    """
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

    supervisor, _feed = build_supervisor_with_oanda_feed(
        oanda=oanda,
        instrument=args.instrument,
    )

    log.info(
        "runner.attached",
        extra={
            "event": "runner.attached",
            "instrument": args.instrument,
            "oanda_environment": oanda.environment,
            "account_id_suffix": oanda.account_id[-4:],
            "wiring_mode": "verification",
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


if __name__ == "__main__":
    sys.exit(main())
