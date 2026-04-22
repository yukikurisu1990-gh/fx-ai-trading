"""``paper_open_position`` — bootstrap CLI: open one paper position.

Why this exists
---------------
The M9 paper-loop runner (#141 + #142) drives the *exit* cadence against
the production paper stack, but it does not open positions on its own —
strategy/signal generation is a separate concern (Cycle 6.9a frozen
boundary).  Operators need a one-shot tool to seed an open position so
they can verify the close path end-to-end without hand-crafting INSERTs.

Path (Option B — FSM-compliant 2-step status transition)
--------------------------------------------------------
For each invocation:

  1. ``OrdersRepository.create_order``               → status='PENDING' (DDL default)
  2. ``OrdersRepository.update_status('SUBMITTED')`` → sent to broker
  3. ``PaperBroker.place_order``                     → fills immediately
  4. ``OrdersRepository.update_status('FILLED')``    → post-fill confirm
  5. ``StateManager.on_fill``                        → positions(open) + outbox

Steps 1/2/4 use the existing public ``OrdersRepository`` API only — the
FSM (D1 §6.6: PENDING → SUBMITTED → FILLED) is honoured exactly.  The
production execution-gate path (``_handle_fill``) collapses the FSM to a
single INSERT with status='FILLED' via a private helper; we deliberately
do not replicate that — it would couple this bootstrap to private
internals.

Known limitations (intentional, NOT fixed in this PR)
-----------------------------------------------------
- ``orders.submitted_at`` and ``orders.filled_at`` remain NULL.
  ``OrdersRepository.update_status`` does not accept timestamp params,
  and adding them would extend the public Repository API surface — out
  of scope for "1PR=1責務 / paper bootstrap".  The schema permits NULL
  on both columns; observability that depends on filled_at can be
  addressed in a follow-up Repository-extension PR (strictly additive).
- No ``order_transactions`` row.  PaperBroker has no transaction stream
  (``get_recent_transactions`` returns ``[]``); not relevant in paper.
- No tp/sl.  The companion runner (#142) drives exits via
  ``ExitPolicyService`` — bootstrap stays consistent with that surface.
- Pre-flight refuses an instrument that is **already open** for the
  account.  Avoids accidentally exercising the pyramiding
  (``event_type='add'``) path; an explicit "add to existing" tool is a
  separate responsibility.

CLI
---
``python -m scripts.paper_open_position \\
    --account-id ACC --instrument EUR_USD --direction buy --units 1000``

Env (read at startup)
---------------------
  DATABASE_URL  — required (read directly via ``os.environ``; the
                  ``config/`` package shadows ``config.py`` — same
                  approach as ``run_paper_loop``).

Exit codes
----------
  0  success
  2  DATABASE_URL missing
  3  instrument already open for the account (pre-flight reject)
  4  PaperBroker did not return status='filled' (should not happen)

Out of scope (do not extend without splitting a new PR)
-------------------------------------------------------
- ``run_exit_gate`` body changes / Supervisor-internal loop.
- SafeStop / schema / metrics / net pnl.
- Strategy / signal / execution-gate surfaces.
- Adding tp/sl to the seeded open.
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

from fx_ai_trading.adapters.broker.paper import PaperBroker
from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.domain.broker import OrderRequest
from fx_ai_trading.ops.logging_config import apply_logging_config
from fx_ai_trading.repositories.orders import OrdersRepository
from fx_ai_trading.services.state_manager import StateManager

_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_LOG_FILENAME = "paper_open_position.jsonl"
_DEFAULT_ACCOUNT_TYPE = "demo"
_DEFAULT_NOMINAL_PRICE = 1.0

_ENV_DATABASE_URL = "DATABASE_URL"

# Same mapping the production execution gate uses
# (``execution_gate_runner._DIRECTION_TO_BROKER_SIDE``).  Kept as a
# private literal here so this script does not import a service-internal
# constant; if the production mapping ever changes, this must follow.
_DIRECTION_TO_BROKER_SIDE: dict[str, str] = {"buy": "long", "sell": "short"}

_RC_OK = 0
_RC_DB_MISSING = 2
_RC_DUPLICATE_OPEN = 3
_RC_BROKER_REJECTED = 4


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BootstrapArgs:
    instrument: str
    direction: str  # 'buy' | 'sell'
    units: int
    account_id: str
    account_type: str
    nominal_price: float
    log_dir: Path
    log_filename: str
    log_level: str


@dataclass(frozen=True)
class BootstrapResult:
    order_id: str
    client_order_id: str
    position_snapshot_id: str
    fill_price: float
    side: str  # 'long' | 'short'


def parse_args(argv: list[str] | None = None) -> BootstrapArgs:
    """Resolve bootstrap configuration from argv.

    Required: --account-id, --instrument, --direction, --units.
    All other flags have sensible defaults.  Split out from ``main`` so
    tests can construct a ``BootstrapArgs`` without going through
    ``sys.argv``.
    """
    parser = argparse.ArgumentParser(
        prog="paper_open_position",
        description=(
            "Open one paper position via the production write path "
            "(OrdersRepository + PaperBroker + StateManager). FSM-compliant "
            "2-step status transition (PENDING → SUBMITTED → FILLED)."
        ),
    )
    parser.add_argument(
        "--account-id",
        dest="account_id",
        type=str,
        required=True,
        help="Account ID for the position (FK to accounts in production).",
    )
    parser.add_argument(
        "--instrument",
        dest="instrument",
        type=str,
        required=True,
        help="Instrument symbol, e.g. EUR_USD.",
    )
    parser.add_argument(
        "--direction",
        dest="direction",
        type=str,
        required=True,
        choices=("buy", "sell"),
        help="Order direction. Mapped to broker side: buy→long, sell→short.",
    )
    parser.add_argument(
        "--units",
        dest="units",
        type=int,
        required=True,
        help="Order size in units (must be > 0).",
    )
    parser.add_argument(
        "--account-type",
        dest="account_type",
        type=str,
        default=_DEFAULT_ACCOUNT_TYPE,
        help=f"Account type. Default: {_DEFAULT_ACCOUNT_TYPE!r}.",
    )
    parser.add_argument(
        "--nominal-price",
        dest="nominal_price",
        type=float,
        default=_DEFAULT_NOMINAL_PRICE,
        help=(
            f"PaperBroker fill price (the broker fills synchronously at this "
            f"price). Default: {_DEFAULT_NOMINAL_PRICE}."
        ),
    )
    parser.add_argument(
        "--log-dir",
        dest="log_dir",
        type=Path,
        default=_DEFAULT_LOG_DIR,
        help=f"Directory for the JSONL log file. Default: {_DEFAULT_LOG_DIR}.",
    )
    parser.add_argument(
        "--log-filename",
        dest="log_filename",
        type=str,
        default=_DEFAULT_LOG_FILENAME,
        help=f"JSONL filename inside --log-dir. Default: {_DEFAULT_LOG_FILENAME!r}.",
    )
    parser.add_argument(
        "--log-level",
        dest="log_level",
        type=str,
        default="INFO",
        help="Root log level. Default: INFO.",
    )
    parsed = parser.parse_args(argv)

    if parsed.units <= 0:
        parser.error(f"--units must be > 0; got {parsed.units!r}")
    if parsed.nominal_price <= 0:
        parser.error(f"--nominal-price must be > 0; got {parsed.nominal_price!r}")

    return BootstrapArgs(
        instrument=parsed.instrument,
        direction=parsed.direction,
        units=int(parsed.units),
        account_id=parsed.account_id,
        account_type=parsed.account_type,
        nominal_price=float(parsed.nominal_price),
        log_dir=parsed.log_dir,
        log_filename=parsed.log_filename,
        log_level=parsed.log_level,
    )


# ---------------------------------------------------------------------------
# Components
# ---------------------------------------------------------------------------


def build_db_engine(env: dict[str, str] | None = None) -> Engine:
    """Construct the SQLAlchemy ``Engine`` from ``DATABASE_URL``.

    Mirrors the seam in ``scripts/run_paper_loop.build_db_engine`` —
    inlined here so the bootstrap does not depend on importing
    ``run_paper_loop`` (``scripts/`` is not a package).  Tests can
    monkeypatch this function to return an in-memory SQLite engine
    without touching env or the real DB.  Raises ``RuntimeError`` if
    ``DATABASE_URL`` is unset or blank — caught by ``main`` and surfaced
    as ``rc=2``.
    """
    src = env if env is not None else os.environ
    url = (src.get(_ENV_DATABASE_URL) or "").strip()
    if not url:
        raise RuntimeError(
            "paper_open_position: DATABASE_URL is not set. "
            "Copy .env.example to .env and fill in the connection string."
        )
    return create_engine(url)


def _make_context(*, account_type: str) -> CommonKeysContext:
    """Construct the CommonKeysContext used for OrdersRepository writes.

    ``RepositoryBase`` does not yet persist these keys to the orders
    table, but ``CommonKeysContext.__post_init__`` requires every field
    to be a non-empty string.  A ULID for ``run_id`` keeps each
    invocation distinguishable in any future log row that does carry
    the keys.
    """
    return CommonKeysContext(
        run_id=f"paper-bootstrap-{generate_ulid()}",
        environment=account_type,
        code_version="paper-bootstrap-cli",
        config_version="paper-bootstrap-cli",
    )


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------


class DuplicateOpenInstrumentError(RuntimeError):
    """Raised when the requested instrument is already open for the account."""


class BrokerDidNotFillError(RuntimeError):
    """Raised when PaperBroker returns a non-'filled' status (should not happen)."""


def bootstrap_open_position(
    *,
    engine: Engine,
    instrument: str,
    direction: str,
    units: int,
    account_id: str,
    account_type: str = _DEFAULT_ACCOUNT_TYPE,
    nominal_price: float = _DEFAULT_NOMINAL_PRICE,
    clock: Clock | None = None,
    state_manager: StateManager | None = None,
    orders: OrdersRepository | None = None,
    broker: PaperBroker | None = None,
    log: logging.Logger | None = None,
) -> BootstrapResult:
    """Open one paper position end-to-end via the production write path.

    Steps (D1 §6.6 FSM compliant):
      1. ``OrdersRepository.create_order``               → status='PENDING'
      2. ``OrdersRepository.update_status('SUBMITTED')`` → sent to broker
      3. ``PaperBroker.place_order``                     → fills immediately
      4. ``OrdersRepository.update_status('FILLED')``    → post-fill confirm
      5. ``StateManager.on_fill``                        → positions(open) + outbox

    Pre-flight: refuses to open if the instrument is already open for
    this account (avoids the pyramid 'add' path inadvertently).

    All collaborators are injectable so unit tests can substitute
    doubles without touching the DB.
    """
    if direction not in _DIRECTION_TO_BROKER_SIDE:
        raise ValueError(f"direction must be 'buy' or 'sell'; got {direction!r}")
    if units <= 0:
        raise ValueError(f"units must be > 0; got {units!r}")

    log = log or logging.getLogger("scripts.paper_open_position")
    effective_clock: Clock = clock if clock is not None else WallClock()
    sm = state_manager or StateManager(engine, account_id=account_id, clock=effective_clock)
    orders_repo = orders or OrdersRepository(engine)
    paper_broker = broker or PaperBroker(account_type=account_type, nominal_price=nominal_price)

    if instrument in sm.open_instruments():
        log.warning(
            "bootstrap.duplicate_open",
            extra={
                "event": "bootstrap.duplicate_open",
                "instrument": instrument,
                "account_id": account_id,
            },
        )
        raise DuplicateOpenInstrumentError(
            f"instrument {instrument!r} already open for account {account_id!r}"
        )

    context = _make_context(account_type=account_type)
    order_id = generate_ulid()
    client_order_id = f"bootstrap:{order_id}:{instrument}"
    side = _DIRECTION_TO_BROKER_SIDE[direction]

    # Step 1: create_order → PENDING (DDL default)
    orders_repo.create_order(
        order_id=order_id,
        account_id=account_id,
        instrument=instrument,
        account_type=account_type,
        order_type="market",
        direction=direction,
        units=str(units),
        context=context,
        client_order_id=client_order_id,
    )

    # Step 2: PENDING → SUBMITTED  (signals "sent to broker")
    orders_repo.update_status(order_id, "SUBMITTED", context)

    # Step 3: broker fills (synchronous in PaperBroker)
    request = OrderRequest(
        client_order_id=client_order_id,
        account_id=account_id,
        instrument=instrument,
        side=side,
        size_units=units,
    )
    result = paper_broker.place_order(request)
    if result.status != "filled" or result.fill_price is None:
        log.error(
            "bootstrap.broker_rejected",
            extra={
                "event": "bootstrap.broker_rejected",
                "order_id": order_id,
                "broker_status": result.status,
                "message": result.message,
            },
        )
        raise BrokerDidNotFillError(
            f"PaperBroker did not fill: status={result.status!r} fill_price={result.fill_price!r}"
        )

    # Step 4: SUBMITTED → FILLED  (post-fill confirm)
    orders_repo.update_status(order_id, "FILLED", context)

    # Step 5: positions(open) + secondary_sync_outbox (single txn)
    psid = sm.on_fill(
        order_id=order_id,
        instrument=instrument,
        units=units,
        avg_price=float(result.fill_price),
    )

    log.info(
        "bootstrap.opened",
        extra={
            "event": "bootstrap.opened",
            "order_id": order_id,
            "client_order_id": client_order_id,
            "position_snapshot_id": psid,
            "instrument": instrument,
            "direction": direction,
            "side": side,
            "units": units,
            "fill_price": float(result.fill_price),
            "account_id": account_id,
        },
    )

    return BootstrapResult(
        order_id=order_id,
        client_order_id=client_order_id,
        position_snapshot_id=psid,
        fill_price=float(result.fill_price),
        side=side,
    )


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
    log = logging.getLogger("scripts.paper_open_position")

    log.info(
        "bootstrap.starting",
        extra={
            "event": "bootstrap.starting",
            "instrument": args.instrument,
            "direction": args.direction,
            "units": args.units,
            "account_id": args.account_id,
            "account_type": args.account_type,
            "nominal_price": args.nominal_price,
            "log_path": str(log_path),
        },
    )

    try:
        engine = build_db_engine()
    except RuntimeError as exc:
        log.error(
            "bootstrap.db_config_missing",
            extra={"event": "bootstrap.db_config_missing", "detail": str(exc)},
        )
        return _RC_DB_MISSING

    try:
        try:
            bootstrap_open_position(
                engine=engine,
                instrument=args.instrument,
                direction=args.direction,
                units=args.units,
                account_id=args.account_id,
                account_type=args.account_type,
                nominal_price=args.nominal_price,
                log=log,
            )
        except DuplicateOpenInstrumentError:
            return _RC_DUPLICATE_OPEN
        except BrokerDidNotFillError:
            return _RC_BROKER_REJECTED
        return _RC_OK
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
