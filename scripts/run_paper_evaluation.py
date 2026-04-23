"""``run_paper_evaluation`` — N-tick evaluation runner for entry signals.

What this is (and is NOT)
-------------------------
This is **not** a strategy framework, EV optimizer, or backtest engine.
It is a *minimal evaluation host* that:

  1. Picks a signal configuration (``--strategy``: minimum / fivepoint /
     multi) and constructs the same ``MinimumEntryPolicy`` the M9/M10
     paper entry runner uses.
  2. Drives ``N`` combined entry+exit ticks against the production paper
     stack: per tick it calls ``policy.evaluate()`` then runs one
     ``Supervisor.run_exit_gate_tick()`` so opens are eventually closed
     and ``close_events`` rows accumulate.
  3. After all ticks complete, queries the existing ``positions`` /
     ``close_events`` tables in a fixed time window and reports six
     metrics in a frozen JSON shape.

What this PR specifically does NOT do (per scope, do not extend here)
---------------------------------------------------------------------
- No new ``signal`` classes, no policy logic changes, no new abstractions.
- No new schema tables / columns / migrations.
- No score / EV / Sharpe / drawdown / risk-adjusted metric.
- No multi-pair support (single ``--instrument`` per run, by design).
- No live execution path (``account_type='demo'`` only, mirrors
  ``run_paper_entry_loop`` / ``run_paper_loop``).

The point is to measure existing signal behaviour, not to design a
better one.

Reused building blocks
----------------------
- ``scripts/run_paper_entry_loop.py``: ``MinimumEntrySignal``,
  ``FivePointMomentumSignal``, ``MinimumEntryPolicy``,
  ``_open_one_position``, ``EntryComponents``, ``build_components``,
  ``DuplicateOpenInstrumentError``, ``BrokerDidNotFillError``.
- ``scripts/run_paper_loop.py``: ``build_supervisor_with_paper_stack``,
  ``OandaConfig``, ``read_oanda_config_from_env``, ``build_db_engine``.

Both are loaded via ``importlib`` because ``scripts/`` is not a Python
package — same convention as the existing integration tests.

Multi-signal note
-----------------
The M10-3 first-non-None picker (``MinimumEntryPolicy(signals=[...])``)
is currently only reachable when the policy is built directly — the
production CLI / ``EntryComponents.signal`` slot is single-signal
(Minor-1, see runbook §10.10).  This evaluation runner bypasses that
limitation by constructing ``MinimumEntryPolicy`` itself with the chosen
``signals=`` list, which lets ``--strategy multi`` exercise the picker
end-to-end without touching ``EntryComponents``.

Output (frozen shape, JSON-serializable)
----------------------------------------
::

    {
      "strategy": "minimum" | "fivepoint" | "multi",
      "ticks_executed": int,
      "trades_count": int,             # closed trades in the run window
      "win_rate": float | None,        # None when trades_count == 0
      "avg_pnl": float | None,         # None when trades_count == 0
      "total_pnl": float,
      "no_signal_rate": float,         # decisions with reason='no_signal'
                                       # / ticks_executed
      "avg_holding_sec": float | None  # mean(close_time - open_time)
                                       # over matched trades
    }

CLI
---
``python -m scripts.run_paper_evaluation \\
    --account-id ACC --instrument EUR_USD --strategy minimum \\
    --units 1000 --max-iterations 100 --interval-seconds 1.0 \\
    --max-holding-seconds 30 --output json``

Exit codes
----------
  0  evaluation completed (metrics emitted)
  2  required env / DB config missing
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

_SCRIPTS_DIR = Path(__file__).resolve().parent
_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_LOG_FILENAME = "paper_evaluation.jsonl"
_DEFAULT_INTERVAL_SECONDS = 1.0
_DEFAULT_MAX_HOLDING_SECONDS = 30
_DEFAULT_STALE_AFTER_SECONDS = 60.0
_DEFAULT_ACCOUNT_TYPE = "demo"
_DEFAULT_NOMINAL_PRICE = 1.0
_DEFAULT_INSTRUMENT = "EUR_USD"
_DEFAULT_UNITS = 1000

_STRATEGY_MINIMUM = "minimum"
_STRATEGY_FIVEPOINT = "fivepoint"
_STRATEGY_MULTI = "multi"
_VALID_STRATEGIES = (_STRATEGY_MINIMUM, _STRATEGY_FIVEPOINT, _STRATEGY_MULTI)

_REASON_NO_SIGNAL = "no_signal"


# ---------------------------------------------------------------------------
# Sibling-script loaders (scripts/ is not a package)
# ---------------------------------------------------------------------------


def _load_sibling(filename: str, alias: str) -> Any:
    """Load a sibling script in ``scripts/`` as a module.

    Mirrors the integration-test convention.  Caches in ``sys.modules``
    under ``alias`` so repeated calls return the same module object.
    """
    if alias in sys.modules:
        return sys.modules[alias]
    spec = importlib.util.spec_from_file_location(alias, _SCRIPTS_DIR / filename)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[alias] = module
    spec.loader.exec_module(module)
    return module


def _entry_lib() -> Any:
    return _load_sibling("run_paper_entry_loop.py", "_paper_entry_loop_for_evaluation")


def _exit_lib() -> Any:
    return _load_sibling("run_paper_loop.py", "_paper_loop_for_evaluation")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EvaluationArgs:
    strategy: str
    instrument: str
    direction: str
    units: int
    account_id: str
    account_type: str
    nominal_price: float
    interval_seconds: float
    max_iterations: int
    max_holding_seconds: int
    stale_after_seconds: float
    output_format: str  # 'json' | 'stdout'
    output_path: Path | None
    log_dir: Path
    log_filename: str
    log_level: str


def parse_args(argv: list[str] | None = None) -> EvaluationArgs:
    parser = argparse.ArgumentParser(
        prog="run_paper_evaluation",
        description=(
            "Run an N-tick combined entry+exit cadence against the production "
            "paper stack with a chosen signal configuration, then aggregate "
            "fixed metrics from positions / close_events."
        ),
    )
    parser.add_argument("--account-id", dest="account_id", type=str, required=True)
    parser.add_argument("--instrument", dest="instrument", type=str, default=_DEFAULT_INSTRUMENT)
    parser.add_argument(
        "--direction",
        dest="direction",
        type=str,
        required=True,
        choices=("buy", "sell"),
        help=(
            "Direction the policy filters on (required on M10-3 master). "
            "Run twice with buy/sell if you want both sides evaluated."
        ),
    )
    parser.add_argument("--units", dest="units", type=int, default=_DEFAULT_UNITS)
    parser.add_argument(
        "--strategy",
        dest="strategy",
        type=str,
        required=True,
        choices=_VALID_STRATEGIES,
        help="Signal configuration to evaluate.",
    )
    parser.add_argument(
        "--account-type", dest="account_type", type=str, default=_DEFAULT_ACCOUNT_TYPE
    )
    parser.add_argument(
        "--nominal-price",
        dest="nominal_price",
        type=float,
        default=_DEFAULT_NOMINAL_PRICE,
    )
    parser.add_argument(
        "--interval-seconds",
        dest="interval_seconds",
        type=float,
        default=_DEFAULT_INTERVAL_SECONDS,
    )
    parser.add_argument(
        "--max-iterations",
        dest="max_iterations",
        type=int,
        required=True,
        help="Total combined entry+exit ticks to run (must be > 0).",
    )
    parser.add_argument(
        "--max-holding-seconds",
        dest="max_holding_seconds",
        type=int,
        default=_DEFAULT_MAX_HOLDING_SECONDS,
    )
    parser.add_argument(
        "--stale-after-seconds",
        dest="stale_after_seconds",
        type=float,
        default=_DEFAULT_STALE_AFTER_SECONDS,
    )
    parser.add_argument(
        "--output",
        dest="output_format",
        type=str,
        default="stdout",
        choices=("json", "stdout"),
    )
    parser.add_argument(
        "--output-path",
        dest="output_path",
        type=Path,
        default=None,
        help="When --output=json and --output-path is set, write the JSON dict there.",
    )
    parser.add_argument("--log-dir", dest="log_dir", type=Path, default=_DEFAULT_LOG_DIR)
    parser.add_argument(
        "--log-filename", dest="log_filename", type=str, default=_DEFAULT_LOG_FILENAME
    )
    parser.add_argument("--log-level", dest="log_level", type=str, default="INFO")

    parsed = parser.parse_args(argv)
    if parsed.max_iterations <= 0:
        parser.error(f"--max-iterations must be > 0; got {parsed.max_iterations!r}")
    if parsed.units <= 0:
        parser.error(f"--units must be > 0; got {parsed.units!r}")
    if parsed.interval_seconds < 0:
        parser.error(f"--interval-seconds must be >= 0; got {parsed.interval_seconds!r}")
    if parsed.max_holding_seconds <= 0:
        parser.error(f"--max-holding-seconds must be > 0; got {parsed.max_holding_seconds!r}")

    return EvaluationArgs(
        strategy=parsed.strategy,
        instrument=parsed.instrument,
        direction=parsed.direction,
        units=parsed.units,
        account_id=parsed.account_id,
        account_type=parsed.account_type,
        nominal_price=parsed.nominal_price,
        interval_seconds=parsed.interval_seconds,
        max_iterations=parsed.max_iterations,
        max_holding_seconds=parsed.max_holding_seconds,
        stale_after_seconds=parsed.stale_after_seconds,
        output_format=parsed.output_format,
        output_path=parsed.output_path,
        log_dir=parsed.log_dir,
        log_filename=parsed.log_filename,
        log_level=parsed.log_level,
    )


# ---------------------------------------------------------------------------
# Signal selection
# ---------------------------------------------------------------------------


def build_signal_set(strategy: str) -> list[Any]:
    """Return the ordered signal list for ``--strategy``.

    Always returns a *list* (even for single-signal strategies) so the
    caller can pass it directly to ``MinimumEntryPolicy(signals=...)``,
    exercising the M10-3 first-non-None picker uniformly.
    """
    entry = _entry_lib()
    if strategy == _STRATEGY_MINIMUM:
        return [entry.MinimumEntrySignal()]
    if strategy == _STRATEGY_FIVEPOINT:
        return [entry.FivePointMomentumSignal()]
    if strategy == _STRATEGY_MULTI:
        return [entry.MinimumEntrySignal(), entry.FivePointMomentumSignal()]
    raise ValueError(f"unknown strategy: {strategy!r}")


# ---------------------------------------------------------------------------
# Eval loop (combined entry + exit cadence)
# ---------------------------------------------------------------------------


def run_eval_ticks(
    *,
    components: Any,
    supervisor: Any,
    instrument: str,
    direction: str,
    units: int,
    account_id: str,
    account_type: str,
    interval_seconds: float,
    max_iterations: int,
    stale_after_seconds: float,
    signals: list[Any],
    log: logging.Logger,
    sleep_fn: Callable[[float], None] = time.sleep,
    should_stop: Callable[[], bool] = lambda: False,
) -> tuple[datetime, datetime, int, int]:
    """Drive ``max_iterations`` combined entry+exit ticks.

    Returns ``(start_time, end_time, ticks_executed, no_signal_count)``.
    Time bounds come from ``components.clock`` (NOT wall-clock here)
    so tests with a ``FixedClock`` get deterministic windows.

    Exception philosophy mirrors the entry / exit runners: a bad tick is
    logged and swallowed; the loop keeps going.
    """
    entry = _entry_lib()
    policy = entry.MinimumEntryPolicy(
        instrument=instrument,
        direction=direction,
        state_manager=components.state_manager,
        quote_feed=components.quote_feed,
        clock=components.clock,
        signals=signals,
        stale_after_seconds=stale_after_seconds,
    )

    start_time = components.clock.now()
    no_signal_count = 0
    iteration = 0
    while iteration < max_iterations and not should_stop():
        iteration += 1
        try:
            decision = policy.evaluate()
            if decision.reason == _REASON_NO_SIGNAL:
                no_signal_count += 1
            if decision.should_fire:
                try:
                    entry._open_one_position(
                        instrument=instrument,
                        direction=direction,
                        units=units,
                        account_id=account_id,
                        account_type=account_type,
                        components=components,
                        log=log,
                    )
                except entry.DuplicateOpenInstrumentError:
                    pass
                except entry.BrokerDidNotFillError:
                    pass
            try:
                supervisor.run_exit_gate_tick()
            except Exception:
                log.exception(
                    "eval.exit_tick_error",
                    extra={"event": "eval.exit_tick_error", "iteration": iteration},
                )
        except Exception:
            log.exception(
                "eval.tick_error",
                extra={"event": "eval.tick_error", "iteration": iteration},
            )
        if interval_seconds > 0 and iteration < max_iterations and not should_stop():
            sleep_fn(interval_seconds)
    end_time = components.clock.now()
    return start_time, end_time, iteration, no_signal_count


# ---------------------------------------------------------------------------
# Aggregation (DB read-only; computation in Python)
# ---------------------------------------------------------------------------


def _parse_timestamp(value: Any) -> datetime:
    """Normalize SQLite TEXT or PostgreSQL datetime to tz-aware UTC datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    s = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(s)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def aggregate_metrics(
    *,
    engine: Engine,
    account_id: str,
    instrument: str,
    start_time: datetime,
    end_time: datetime,
    ticks_executed: int,
    no_signal_count: int,
    strategy: str,
) -> dict[str, Any]:
    """Compute the 6 fixed metrics from the existing positions / close_events tables.

    No new tables, no new columns, no SQL aggregation — Python collects
    the rows in the run window and reduces them.
    """
    start_iso = start_time.isoformat()
    end_iso = end_time.isoformat()

    closes_sql = text(
        """
        SELECT ce.order_id, ce.closed_at, ce.pnl_realized
        FROM close_events ce
        JOIN orders o ON o.order_id = ce.order_id
        WHERE o.account_id = :account_id
          AND o.instrument = :instrument
          AND ce.closed_at >= :start_iso
          AND ce.closed_at <= :end_iso
        """
    )
    opens_sql = text(
        """
        SELECT order_id, event_time_utc
        FROM positions
        WHERE account_id = :account_id
          AND instrument = :instrument
          AND event_type = 'open'
        """
    )

    with engine.connect() as conn:
        close_rows = conn.execute(
            closes_sql,
            {
                "account_id": account_id,
                "instrument": instrument,
                "start_iso": start_iso,
                "end_iso": end_iso,
            },
        ).fetchall()
        open_rows = conn.execute(
            opens_sql,
            {"account_id": account_id, "instrument": instrument},
        ).fetchall()

    open_time_by_order: dict[str, datetime] = {str(r[0]): _parse_timestamp(r[1]) for r in open_rows}

    trades_count = len(close_rows)
    pnl_values: list[float] = []
    holding_secs: list[float] = []
    wins = 0
    for order_id, closed_at, pnl_realized in close_rows:
        oid = str(order_id)
        pnl_value = float(pnl_realized) if pnl_realized is not None else 0.0
        pnl_values.append(pnl_value)
        if pnl_value > 0:
            wins += 1
        open_time = open_time_by_order.get(oid)
        if open_time is not None:
            holding_secs.append((_parse_timestamp(closed_at) - open_time).total_seconds())

    total_pnl = sum(pnl_values)
    win_rate = (wins / trades_count) if trades_count > 0 else None
    avg_pnl = (total_pnl / trades_count) if trades_count > 0 else None
    avg_holding_sec = (sum(holding_secs) / len(holding_secs)) if holding_secs else None
    no_signal_rate = (no_signal_count / ticks_executed) if ticks_executed > 0 else 0.0

    return {
        "strategy": strategy,
        "ticks_executed": ticks_executed,
        "trades_count": trades_count,
        "win_rate": win_rate,
        "avg_pnl": avg_pnl,
        "total_pnl": total_pnl,
        "no_signal_rate": no_signal_rate,
        "avg_holding_sec": avg_holding_sec,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------


def emit_metrics(
    metrics: dict[str, Any],
    *,
    output_format: str,
    output_path: Path | None,
    stdout: Any = sys.stdout,
) -> None:
    """Write the metrics dict to stdout (text or JSON) or a JSON file.

    ``stdout`` is parameterized for tests.  When ``output_path`` is set
    and ``output_format='json'``, the file is overwritten (single-shot
    eval; no append semantics).
    """
    if output_format == "json" and output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2, sort_keys=True)
            f.write("\n")
        return
    if output_format == "json":
        json.dump(metrics, stdout, indent=2, sort_keys=True)
        stdout.write("\n")
        return
    # 'stdout' (human-friendly)
    for k in (
        "strategy",
        "ticks_executed",
        "trades_count",
        "win_rate",
        "avg_pnl",
        "total_pnl",
        "no_signal_rate",
        "avg_holding_sec",
    ):
        stdout.write(f"{k}={metrics.get(k)!r}\n")


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    entry = _entry_lib()
    exit_lib = _exit_lib()

    from fx_ai_trading.ops.logging_config import apply_logging_config

    log_path = apply_logging_config(
        log_dir=args.log_dir,
        filename=args.log_filename,
        level=args.log_level,
    )
    log = logging.getLogger("scripts.run_paper_evaluation")

    log.info(
        "eval.starting",
        extra={
            "event": "eval.starting",
            "strategy": args.strategy,
            "instrument": args.instrument,
            "direction": args.direction,
            "units": args.units,
            "max_iterations": args.max_iterations,
            "interval_seconds": args.interval_seconds,
            "max_holding_seconds": args.max_holding_seconds,
            "log_path": str(log_path),
        },
    )

    try:
        oanda = exit_lib.read_oanda_config_from_env()
    except RuntimeError as exc:
        log.error("eval.env_missing", extra={"event": "eval.env_missing", "detail": str(exc)})
        return 2
    try:
        engine = exit_lib.build_db_engine()
    except RuntimeError as exc:
        log.error(
            "eval.db_config_missing",
            extra={"event": "eval.db_config_missing", "detail": str(exc)},
        )
        return 2

    signals = build_signal_set(args.strategy)
    components = entry.build_components(
        oanda=oanda,
        engine=engine,
        account_id=args.account_id,
        account_type=args.account_type,
        nominal_price=args.nominal_price,
        signal=signals[0],  # EntryComponents.signal slot (unused by our policy)
    )
    # Share the entry-side QuoteFeed with the exit-side Supervisor so
    # open-leg avg_price and close-leg fill_price are read from the
    # same source — without this, the entry broker would fall back to
    # nominal_price and pnl_realized would carry an artefact bias.
    supervisor, _feed = exit_lib.build_supervisor_with_paper_stack(
        oanda=oanda,
        instrument=args.instrument,
        engine=engine,
        account_id=args.account_id,
        max_holding_seconds=args.max_holding_seconds,
        quote_feed=components.quote_feed,
    )

    start_time, end_time, ticks_executed, no_signal_count = run_eval_ticks(
        components=components,
        supervisor=supervisor,
        instrument=args.instrument,
        direction=args.direction,
        units=args.units,
        account_id=args.account_id,
        account_type=args.account_type,
        interval_seconds=args.interval_seconds,
        max_iterations=args.max_iterations,
        stale_after_seconds=args.stale_after_seconds,
        signals=signals,
        log=log,
    )

    metrics = aggregate_metrics(
        engine=engine,
        account_id=args.account_id,
        instrument=args.instrument,
        start_time=start_time,
        end_time=end_time,
        ticks_executed=ticks_executed,
        no_signal_count=no_signal_count,
        strategy=args.strategy,
    )

    log.info("eval.completed", extra={"event": "eval.completed", **metrics})
    emit_metrics(metrics, output_format=args.output_format, output_path=args.output_path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
