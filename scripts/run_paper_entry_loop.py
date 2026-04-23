"""``run_paper_entry_loop`` — outside-cadence runner for the paper *open* path.

Why this exists
---------------
The M9 sub-series gives operators two complementary outside-cadence
runners against the production paper stack:

  * ``run_paper_loop`` (#142) drives the **exit** cadence
    (``Supervisor.run_exit_gate_tick`` → close path).
  * ``paper_open_position`` (#143) is a **one-shot** open bootstrap
    (single FSM-compliant 5-step orchestration, then exits).

Neither tool can keep firing opens on a cadence — strategy / signal
generation is a separate frozen surface (Cycle 6.9a).  Operators
verifying paper round-trip end-to-end need a **looping** open-side
runner that fires the same FSM-compliant write path on a tick, gated by
a deliberately minimal entry policy.  This script is that runner.

Path (per tick)
---------------
  1. Evaluate ``MinimumEntryPolicy`` →
     ``EntryDecision(should_fire, reason)`` with reasons:

       ``already_open`` — instrument is already open for this account
                          (avoids the pyramid 'add' path; same pre-flight
                          contract as ``paper_open_position``).
       ``no_quote``     — ``QuoteFeed.get_quote`` raised; transient feed
                          outage, will retry next tick.
       ``stale_quote``  — ``(clock.now() - quote.ts).total_seconds()``
                          exceeded the freshness threshold (M-3c default
                          60s).
       ``no_signal``    — fresh quote acquired but the configured
                          ``EntrySignal`` says no fireable direction
                          (warmup, flat / mixed / non-monotonic window,
                          or signal direction != configured
                          ``--direction``).
       ``ok``           — fire.

  2. If ``should_fire``: invoke ``_open_one_position`` which inlines the
     5-step FSM orchestration from ``paper_open_position`` (Option B):

       ``OrdersRepository.create_order``               → status='PENDING'
       ``OrdersRepository.update_status('SUBMITTED')`` → sent to broker
       ``PaperBroker.place_order``                     → fills immediately
       ``OrdersRepository.update_status('FILLED')``    → post-fill confirm
       ``StateManager.on_fill``                        → positions(open) + outbox

     The 5-step body is duplicated in this script (rather than imported
     from ``paper_open_position``) because ``scripts/`` is not a Python
     package — same convention used by ``run_paper_loop``.

  3. Exceptions never kill the loop: the next tick re-attempts.  This
     mirrors the M-3c stale-gate philosophy used by ``run_exit_gate``.

Hard out-of-scope (intentionally NOT done — split a separate PR)
----------------------------------------------------------------
- Real strategy / signal-generation surfaces (Cycle 6.9a frozen).
- Pyramiding (``event_type='add'`` on existing open) — pre-flight
  rejects with ``DuplicateOpenInstrumentError``.
- Extending ``OrdersRepository.update_status`` to set
  ``submitted_at`` / ``filled_at`` (still NULL on bootstrap rows; see
  ``paper_open_position`` module docstring).
- ``run_exit_gate`` body changes / Supervisor-internal loop / SafeStop /
  schema / metrics / net pnl.

Logging
-------
``apply_logging_config`` writes one JSON object per record to
``logs/paper_entry_loop.jsonl`` (rotating, 10 MiB × 5).  Stable event
names operators can grep / jq:

  ``entry_runner.starting``       ``entry_runner.attached``
  ``entry_runner.env_missing``    ``entry_runner.db_config_missing``
  ``entry_runner.shutdown``
  ``tick.no_fire``                ``tick.opened``
  ``tick.skip_duplicate``         ``tick.broker_rejected``
  ``tick.error``                  ``tick.completed``
  ``shutdown.signal_received``

CLI
---
``python -m scripts.run_paper_entry_loop \\
    --account-id ACC --instrument EUR_USD --direction buy --units 1000``

Env (read at startup; CLI flags override)
-----------------------------------------
  DATABASE_URL              — required.
  OANDA_ACCESS_TOKEN        — required.
  OANDA_ACCOUNT_ID          — required.
  OANDA_ENVIRONMENT         — 'practice' (default) or 'live'.
  PAPER_ENTRY_INTERVAL_SECONDS    — default 5.0.
  PAPER_ENTRY_STALE_AFTER_SECONDS — default 60.0 (mirrors M-3c).

Exit codes
----------
  0  graceful shutdown
  2  required env / DB config missing
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import sys
import time
from collections import deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
from fx_ai_trading.adapters.broker.paper import PaperBroker
from fx_ai_trading.adapters.price_feed.oanda_quote_feed import OandaQuoteFeed
from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.domain.broker import OrderRequest
from fx_ai_trading.domain.price_feed import Quote, QuoteFeed
from fx_ai_trading.ops.logging_config import apply_logging_config
from fx_ai_trading.repositories.orders import OrdersRepository
from fx_ai_trading.services.state_manager import StateManager

_DEFAULT_LOG_DIR = Path("logs")
_DEFAULT_LOG_FILENAME = "paper_entry_loop.jsonl"
_DEFAULT_INTERVAL_SECONDS = 5.0
_DEFAULT_STALE_AFTER_SECONDS = 60.0
_DEFAULT_ACCOUNT_TYPE = "demo"
_DEFAULT_NOMINAL_PRICE = 1.0
_DEFAULT_OANDA_ENVIRONMENT = "practice"

_ENV_OANDA_ACCESS_TOKEN = "OANDA_ACCESS_TOKEN"
_ENV_OANDA_ACCOUNT_ID = "OANDA_ACCOUNT_ID"
_ENV_OANDA_ENVIRONMENT = "OANDA_ENVIRONMENT"
_ENV_DATABASE_URL = "DATABASE_URL"
_ENV_INTERVAL = "PAPER_ENTRY_INTERVAL_SECONDS"
_ENV_STALE_AFTER = "PAPER_ENTRY_STALE_AFTER_SECONDS"

# Same mapping the production execution gate uses
# (``execution_gate_runner._DIRECTION_TO_BROKER_SIDE``).  Redeclared
# here as a private literal — same convention as ``paper_open_position``
# — so this script does not import a service-internal constant.  If the
# production mapping ever changes, this must follow.
_DIRECTION_TO_BROKER_SIDE: dict[str, str] = {"buy": "long", "sell": "short"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EntryRunnerArgs:
    instrument: str
    direction: str  # 'buy' | 'sell'
    units: int
    account_id: str
    account_type: str
    nominal_price: float
    interval_seconds: float
    stale_after_seconds: float
    max_iterations: int
    log_dir: Path
    log_filename: str
    log_level: str


def parse_args(argv: list[str] | None = None) -> EntryRunnerArgs:
    """Resolve runner configuration from argv + environment.

    CLI flags take precedence over env; env takes precedence over the
    module-level defaults.  Required: --account-id, --instrument,
    --direction, --units (the minimum-entry policy is deterministic on
    these — it does NOT decide *what* to open, only *whether* to fire).
    """
    parser = argparse.ArgumentParser(
        prog="run_paper_entry_loop",
        description=(
            "Run an outside-cadence open-side loop against the production "
            "paper stack (OrdersRepository + PaperBroker + StateManager). "
            "Each tick evaluates a minimum entry policy "
            "(already_open / no_quote / stale_quote / ok) and, on 'ok', "
            "fires the FSM-compliant 5-step open path."
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
        help=(f"PaperBroker fill price (synchronous fill). Default: {_DEFAULT_NOMINAL_PRICE}."),
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
        "--stale-after-seconds",
        dest="stale_after_seconds",
        type=float,
        default=None,
        help=(
            f"Quote staleness threshold (M-3c default {_DEFAULT_STALE_AFTER_SECONDS}). "
            f"Falls back to ${_ENV_STALE_AFTER} or {_DEFAULT_STALE_AFTER_SECONDS}."
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

    interval = parsed.interval_seconds
    if interval is None:
        env_raw = os.environ.get(_ENV_INTERVAL, "").strip()
        interval = float(env_raw) if env_raw else _DEFAULT_INTERVAL_SECONDS
    if interval <= 0:
        parser.error(f"--interval must be > 0; got {interval!r}")

    stale_after = parsed.stale_after_seconds
    if stale_after is None:
        env_raw = os.environ.get(_ENV_STALE_AFTER, "").strip()
        stale_after = float(env_raw) if env_raw else _DEFAULT_STALE_AFTER_SECONDS
    if stale_after <= 0:
        parser.error(f"--stale-after-seconds must be > 0; got {stale_after!r}")

    if parsed.max_iterations < 0:
        parser.error(f"--max-iterations must be >= 0; got {parsed.max_iterations!r}")

    return EntryRunnerArgs(
        instrument=parsed.instrument,
        direction=parsed.direction,
        units=int(parsed.units),
        account_id=parsed.account_id,
        account_type=parsed.account_type,
        nominal_price=float(parsed.nominal_price),
        interval_seconds=interval,
        stale_after_seconds=stale_after,
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

    Verbatim small-duplicate of ``run_paper_loop.read_oanda_config_from_env``;
    ``scripts/`` is not a package, so importing across scripts is not
    available.  Pass ``env`` explicitly in tests to avoid touching
    ``os.environ``.  Raises ``RuntimeError`` if any required variable is
    missing — early fail beats a confusing 401 from oandapyV20 mid-loop.
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
        raise RuntimeError(
            "run_paper_entry_loop: required OANDA env vars missing: " + ", ".join(missing)
        )

    return OandaConfig(
        access_token=access_token,
        account_id=account_id,
        environment=environment,
    )


def build_db_engine(env: dict[str, str] | None = None) -> Engine:
    """Construct the SQLAlchemy ``Engine`` from ``DATABASE_URL``.

    Verbatim small-duplicate of ``run_paper_loop.build_db_engine``.
    Tests can monkeypatch this seam to return an in-memory SQLite engine
    without touching env or the real DB.  Raises ``RuntimeError`` if
    ``DATABASE_URL`` is unset or blank — caught by ``main`` and surfaced
    as ``rc=2``.
    """
    src = env if env is not None else os.environ
    url = (src.get(_ENV_DATABASE_URL) or "").strip()
    if not url:
        raise RuntimeError(
            "run_paper_entry_loop: DATABASE_URL is not set. "
            "Copy .env.example to .env and fill in the connection string."
        )
    return create_engine(url)


@dataclass(frozen=True)
class EntryComponents:
    state_manager: StateManager
    orders: OrdersRepository
    broker: PaperBroker
    quote_feed: QuoteFeed
    clock: Clock
    signal: EntrySignal


def build_components(
    *,
    oanda: OandaConfig,
    engine: Engine,
    account_id: str | None = None,
    account_type: str = _DEFAULT_ACCOUNT_TYPE,
    nominal_price: float = _DEFAULT_NOMINAL_PRICE,
    clock: Clock | None = None,
    api_client: OandaAPIClient | None = None,
    signal: EntrySignal | None = None,
    quote_feed: QuoteFeed | None = None,
) -> EntryComponents:
    """Compose the production paper open-side stack.

    Mirrors ``run_paper_loop.build_supervisor_with_paper_stack`` but
    returns the four collaborators directly — the open path does not go
    through Supervisor (Cycle 6.9a forbids a Supervisor-internal loop,
    and the entry side is a script-level concern that never registers a
    gate).

    ``signal`` is optional; when omitted, defaults to a fresh
    ``MinimumEntrySignal()`` (M9 behavior preserved).  Injection is the
    M10-1 seam — it lets future signal classes be swapped in without
    editing this factory.

    ``quote_feed`` is optional; when omitted, an ``OandaQuoteFeed`` is
    built internally (legacy behavior).  When provided, the same feed
    is used both for the policy / staleness gate (via
    ``EntryComponents.quote_feed``) and for ``PaperBroker.place_order``
    fill prices — matching the exit-side wiring in
    ``build_supervisor_with_paper_stack`` so open and close legs reflect
    real quote drift instead of a fixed nominal price.
    """
    effective_account_id = account_id or oanda.account_id
    effective_clock: Clock = clock if clock is not None else WallClock()
    effective_signal: EntrySignal = signal if signal is not None else MinimumEntrySignal()

    if quote_feed is None:
        if api_client is None:
            api_client = OandaAPIClient(
                access_token=oanda.access_token,
                environment=oanda.environment,
            )
        effective_feed: QuoteFeed = OandaQuoteFeed(
            api_client=api_client, account_id=oanda.account_id
        )
    else:
        effective_feed = quote_feed

    state_manager = StateManager(engine, account_id=effective_account_id, clock=effective_clock)
    orders = OrdersRepository(engine)
    broker = PaperBroker(
        account_type=account_type,
        nominal_price=nominal_price,
        quote_feed=effective_feed,
    )

    return EntryComponents(
        state_manager=state_manager,
        orders=orders,
        broker=broker,
        quote_feed=effective_feed,
        clock=effective_clock,
        signal=effective_signal,
    )


def _make_context(*, account_type: str) -> CommonKeysContext:
    """Construct the CommonKeysContext used for OrdersRepository writes.

    Mirrors ``paper_open_position._make_context``.  Every field must be
    a non-empty string (CommonKeysContext.__post_init__ enforces this) —
    a ULID for ``run_id`` keeps each tick's writes distinguishable in
    any future log row that does carry the keys.
    """
    return CommonKeysContext(
        run_id=f"paper-entry-{generate_ulid()}",
        environment=account_type,
        code_version="paper-entry-cli",
        config_version="paper-entry-cli",
    )


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


_REASON_ALREADY_OPEN = "already_open"
_REASON_NO_QUOTE = "no_quote"
_REASON_STALE_QUOTE = "stale_quote"
_REASON_NO_SIGNAL = "no_signal"
_REASON_OK = "ok"


@dataclass(frozen=True)
class EntryDecision:
    should_fire: bool
    reason: str  # one of: already_open / no_quote / stale_quote / no_signal / ok
    age_seconds: float | None = None  # populated when reason in {stale_quote, no_signal, ok}


class EntrySignal(Protocol):
    """Structural Protocol for entry-side signal classes.

    Any class with ``evaluate(quote: Quote) -> str | None`` satisfies
    this Protocol structurally — no explicit inheritance or registration
    required.  ``MinimumEntrySignal`` and ``FivePointMomentumSignal``
    both comply.  M10-3 multi-signal picker and future EV-weighted
    selectors will consume this type.
    """

    def evaluate(self, quote: Quote) -> str | None: ...


class MinimumEntrySignal:
    """3-point monotonic momentum signal from consecutive fresh quotes.

    Stateless w.r.t. time and feed: receives a *fresh* ``Quote`` (already
    filtered by the policy's no_quote / stale_quote gates) and returns
    the direction implied by the most recent three observed quotes:

      * fewer than 3 quotes seen      → ``None`` (warmup; first 2 ticks)
      * 3 prices strictly increasing  → ``'buy'``  (p1 < p2 < p3)
      * 3 prices strictly decreasing  → ``'sell'`` (p1 > p2 > p3)
      * otherwise (flat / mixed equality / non-monotonic) → ``None``

    The signal does NOT call ``QuoteFeed.get_quote``, does NOT consult a
    ``Clock``, and does NOT make staleness judgements — those remain in
    ``MinimumEntryPolicy``.  Process state is the last three ``Quote``
    observations (a ``deque`` with ``maxlen=3``); on process restart the
    signal returns to warmup and 2 fresh ticks must elapse before it can
    fire again.
    """

    def __init__(self) -> None:
        self._quotes: deque[Quote] = deque(maxlen=3)

    def evaluate(self, quote: Quote) -> str | None:
        self._quotes.append(quote)
        if len(self._quotes) < 3:
            return None
        p1, p2, p3 = (q.price for q in self._quotes)
        if p1 < p2 < p3:
            return "buy"
        if p1 > p2 > p3:
            return "sell"
        return None


class FivePointMomentumSignal:
    """5-point strict-monotonic momentum signal (M10-2 Protocol-validation concrete).

    Identical structure to ``MinimumEntrySignal`` with a window of 5
    consecutive fresh quotes instead of 3.  Added in M10-2 as the second
    concrete implementation of ``EntrySignal``, validating that the Protocol
    seam accepts any conforming class.  Not intended as a production-strategy
    improvement over the 3-point variant.

      * fewer than 5 quotes seen         → ``None`` (warmup; first 4 ticks)
      * 5 prices strictly increasing     → ``'buy'``  (p1 < p2 < p3 < p4 < p5)
      * 5 prices strictly decreasing     → ``'sell'`` (p1 > p2 > p3 > p4 > p5)
      * otherwise (flat / mixed / non-monotonic) → ``None``
    """

    def __init__(self) -> None:
        self._quotes: deque[Quote] = deque(maxlen=5)

    def evaluate(self, quote: Quote) -> str | None:
        self._quotes.append(quote)
        if len(self._quotes) < 5:
            return None
        p1, p2, p3, p4, p5 = (q.price for q in self._quotes)
        if p1 < p2 < p3 < p4 < p5:
            return "buy"
        if p1 > p2 > p3 > p4 > p5:
            return "sell"
        return None


class StridedMinimumEntrySignal:
    """Stride-subsampled 3-point monotonic momentum signal.

    Identical decision logic to ``MinimumEntrySignal`` but only *samples*
    every ``stride``-th quote into the 3-point deque; intermediate
    observations are dropped.  Lets the 1-second eval cadence probe
    longer-horizon monotonic moves without changing the tick interval
    (``stride=5`` ≈ 5-second momentum at a 1 Hz feed).

      * non-sampling ticks                                   → ``None``
      * sampled < 3 quotes                                   → ``None`` (warmup)
      * 3 sampled prices strictly increasing                 → ``'buy'``
      * 3 sampled prices strictly decreasing                 → ``'sell'``
      * otherwise (flat / mixed / non-monotonic)             → ``None``

    ``stride=1`` reduces exactly to ``MinimumEntrySignal`` (every tick
    is sampled; same 2-tick warmup, same 3-point rule), which is pinned
    in the unit tests as an invariance check.  Counter starts at 0 so
    the *first* call is a sampling call (same warmup shape as the
    un-strided signal).
    """

    def __init__(self, stride: int = 5) -> None:
        if stride < 1:
            raise ValueError(f"stride must be >= 1; got {stride!r}")
        self._stride = stride
        self._counter = 0
        self._quotes: deque[Quote] = deque(maxlen=3)

    def evaluate(self, quote: Quote) -> str | None:
        sample = self._counter % self._stride == 0
        self._counter += 1
        if not sample:
            return None
        self._quotes.append(quote)
        if len(self._quotes) < 3:
            return None
        p1, p2, p3 = (q.price for q in self._quotes)
        if p1 < p2 < p3:
            return "buy"
        if p1 > p2 > p3:
            return "sell"
        return None


class MinimumEntryPolicy:
    """Deterministic open-side policy for the paper entry runner.

    The policy fires the configured ``(instrument, direction, units)``
    open whenever:
      - the instrument is NOT already open for this account, AND
      - a fresh ``Quote`` is available for the instrument, AND
      - at least one signal in the ordered ``signals`` sequence returns
        the configured ``direction`` before any other returns a different
        direction (first-non-None priority picker; M10-3).

    "Fresh" mirrors the M-3c definition used by ``run_exit_gate``:
    ``(clock.now() - quote.ts).total_seconds() > stale_after_seconds``
    is stale (strictly ``>``, not ``>=``).  Both ``clock.now()`` (UTC
    tz-aware by Clock contract) and ``quote.ts`` (tz-aware enforced by
    ``Quote.__post_init__``) are tz-aware datetimes, so the subtraction
    is well-defined regardless of the quote's source timezone.

    The signal is consulted only AFTER the no_quote / stale_quote gates
    pass — so the signal sees a strictly ascending stream of fresh
    quotes (warmup ticks aside) and never has to make staleness
    decisions itself.
    """

    def __init__(
        self,
        *,
        instrument: str,
        direction: str,
        state_manager: StateManager,
        quote_feed: QuoteFeed,
        clock: Clock,
        signal: EntrySignal | None = None,
        signals: Sequence[EntrySignal] | None = None,
        stale_after_seconds: float = _DEFAULT_STALE_AFTER_SECONDS,
    ) -> None:
        if direction not in _DIRECTION_TO_BROKER_SIDE:
            raise ValueError(f"direction must be 'buy' or 'sell'; got {direction!r}")
        if signals is not None:
            self._signals: tuple[EntrySignal, ...] = tuple(signals)
        elif signal is not None:
            self._signals = (signal,)
        else:
            raise ValueError("MinimumEntryPolicy requires signal= or signals=")
        self._instrument = instrument
        self._direction = direction
        self._sm = state_manager
        self._feed = quote_feed
        self._clock = clock
        self._stale_after_seconds = stale_after_seconds

    def evaluate(self) -> EntryDecision:
        if self._instrument in self._sm.open_instruments():
            return EntryDecision(should_fire=False, reason=_REASON_ALREADY_OPEN)

        try:
            quote = self._feed.get_quote(self._instrument)
        except Exception:
            # Transient feed failure — caller logs ``tick.no_fire`` with
            # reason='no_quote' and we re-attempt next tick.  Same
            # philosophy as run_exit_gate's stale gate: a feed outage is
            # observable but not fatal.
            return EntryDecision(should_fire=False, reason=_REASON_NO_QUOTE)

        # Quote.__post_init__ guarantees quote.ts is tz-aware; Clock
        # contract guarantees now() is UTC tz-aware.  Subtraction is
        # well-defined across mixed tz-aware datetimes.
        age = (self._clock.now() - quote.ts).total_seconds()
        if age > self._stale_after_seconds:
            return EntryDecision(
                should_fire=False,
                reason=_REASON_STALE_QUOTE,
                age_seconds=age,
            )

        # Priority picker: iterate signals in order; adopt the first non-None
        # direction.  All-None → no_signal.  Direction mismatch → no_signal.
        signal_direction: str | None = None
        for s in self._signals:
            candidate = s.evaluate(quote)
            if candidate is not None:
                signal_direction = candidate
                break
        if signal_direction is None or signal_direction != self._direction:
            return EntryDecision(
                should_fire=False,
                reason=_REASON_NO_SIGNAL,
                age_seconds=age,
            )

        return EntryDecision(should_fire=True, reason=_REASON_OK, age_seconds=age)


# ---------------------------------------------------------------------------
# Open path (5-step inline, mirrors paper_open_position)
# ---------------------------------------------------------------------------


class DuplicateOpenInstrumentError(RuntimeError):
    """Raised when the instrument is already open for the account.

    Re-declared here (not imported from ``paper_open_position``) because
    ``scripts/`` is not a package.  Per-tick ``_open_one_position``
    raises this when the pre-flight ``open_instruments()`` check trips —
    the duplicate guard is **always** signalled via this exception so
    callers (and tests) can rely on a single contract.
    """


class BrokerDidNotFillError(RuntimeError):
    """Raised when PaperBroker returns a non-'filled' status."""


@dataclass(frozen=True)
class OpenResult:
    order_id: str
    client_order_id: str
    position_snapshot_id: str
    fill_price: float
    side: str  # 'long' | 'short'


def _open_one_position(
    *,
    instrument: str,
    direction: str,
    units: int,
    account_id: str,
    account_type: str,
    components: EntryComponents,
    log: logging.Logger,
) -> OpenResult:
    """Inline FSM-compliant 5-step open orchestration.

    Mirrors ``paper_open_position.bootstrap_open_position`` byte-for-byte
    on the steps that matter (the duplicate-guard + 5-step body), but
    operates on the long-lived ``EntryComponents`` constructed once at
    runner startup so we do NOT rebuild StateManager / OrdersRepository
    / PaperBroker per tick.

    The duplicate guard is **always** signalled via
    ``DuplicateOpenInstrumentError`` (per the user's Loop 2 contract):
    no return-value short-circuits, no None, no flag.  The same is true
    for broker rejection (``BrokerDidNotFillError``).  This keeps the
    caller's exception-driven control flow uniform.
    """
    if direction not in _DIRECTION_TO_BROKER_SIDE:
        raise ValueError(f"direction must be 'buy' or 'sell'; got {direction!r}")
    if units <= 0:
        raise ValueError(f"units must be > 0; got {units!r}")

    sm = components.state_manager
    orders_repo = components.orders
    paper_broker = components.broker

    if instrument in sm.open_instruments():
        raise DuplicateOpenInstrumentError(
            f"instrument {instrument!r} already open for account {account_id!r}"
        )

    context = _make_context(account_type=account_type)
    order_id = generate_ulid()
    client_order_id = f"entry:{order_id}:{instrument}"
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
            "tick.broker_rejected",
            extra={
                "event": "tick.broker_rejected",
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

    return OpenResult(
        order_id=order_id,
        client_order_id=client_order_id,
        position_snapshot_id=psid,
        fill_price=float(result.fill_price),
        side=side,
    )


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------


def run_loop(
    *,
    components: EntryComponents,
    policy: MinimumEntryPolicy,
    instrument: str,
    direction: str,
    units: int,
    account_id: str,
    account_type: str,
    interval_seconds: float,
    max_iterations: int,
    log: logging.Logger,
    should_stop: Callable[[], bool],
    sleep_fn: Callable[[float], None] = time.sleep,
    monotonic_fn: Callable[[], float] = time.monotonic,
) -> int:
    """Run the cadence loop until ``should_stop()`` or ``max_iterations``.

    Returns the number of completed iterations.  Same skeleton as
    ``run_paper_loop.run_loop`` — exceptions per-tick are logged and
    swallowed so a single bad tick (broker reject, transient DB error)
    does not kill the runner.  The next tick re-attempts.
    """
    iteration = 0
    while not should_stop():
        iteration += 1
        tick_start = monotonic_fn()
        try:
            decision = policy.evaluate()
            if not decision.should_fire:
                log.info(
                    "tick.no_fire",
                    extra={
                        "event": "tick.no_fire",
                        "iteration": iteration,
                        "instrument": instrument,
                        "reason": decision.reason,
                        "age_seconds": decision.age_seconds,
                    },
                )
            else:
                try:
                    opened = _open_one_position(
                        instrument=instrument,
                        direction=direction,
                        units=units,
                        account_id=account_id,
                        account_type=account_type,
                        components=components,
                        log=log,
                    )
                    log.info(
                        "tick.opened",
                        extra={
                            "event": "tick.opened",
                            "iteration": iteration,
                            "instrument": instrument,
                            "direction": direction,
                            "side": opened.side,
                            "units": units,
                            "order_id": opened.order_id,
                            "client_order_id": opened.client_order_id,
                            "position_snapshot_id": opened.position_snapshot_id,
                            "fill_price": opened.fill_price,
                            "account_id": account_id,
                        },
                    )
                except DuplicateOpenInstrumentError:
                    # Race between policy.evaluate() and _open_one_position
                    # (open_instruments() observed empty, but a concurrent
                    # writer landed first).  Recoverable — next tick
                    # re-evaluates.
                    log.warning(
                        "tick.skip_duplicate",
                        extra={
                            "event": "tick.skip_duplicate",
                            "iteration": iteration,
                            "instrument": instrument,
                            "account_id": account_id,
                        },
                    )
                except BrokerDidNotFillError:
                    # _open_one_position already emitted tick.broker_rejected
                    # at ERROR with the broker_status / message context.
                    pass
        except Exception:
            # Catch-all: never let a single bad tick kill the runner.
            # Mirrors run_paper_loop philosophy.
            log.exception(
                "tick.error",
                extra={"event": "tick.error", "iteration": iteration},
            )
        tick_duration_ms = (monotonic_fn() - tick_start) * 1000.0
        log.info(
            "tick.completed",
            extra={
                "event": "tick.completed",
                "iteration": iteration,
                "tick_duration_ms": round(tick_duration_ms, 3),
            },
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

    Verbatim small-duplicate of ``run_paper_loop._install_sigint_handler``.
    A single-element list is used as a mutable container so the handler
    can flip the flag without ``global``.  The handler intentionally
    does **not** raise; the loop checks the flag between ticks for
    graceful shutdown.
    """

    def _handle(signum: int, _frame: object) -> None:
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
    log = logging.getLogger("scripts.run_paper_entry_loop")

    log.info(
        "entry_runner.starting",
        extra={
            "event": "entry_runner.starting",
            "instrument": args.instrument,
            "direction": args.direction,
            "units": args.units,
            "account_id": args.account_id,
            "account_type": args.account_type,
            "nominal_price": args.nominal_price,
            "interval_seconds": args.interval_seconds,
            "stale_after_seconds": args.stale_after_seconds,
            "max_iterations": args.max_iterations,
            "log_path": str(log_path),
        },
    )

    try:
        oanda = read_oanda_config_from_env()
    except RuntimeError as exc:
        log.error(
            "entry_runner.env_missing",
            extra={"event": "entry_runner.env_missing", "detail": str(exc)},
        )
        return 2

    try:
        engine = build_db_engine()
    except RuntimeError as exc:
        log.error(
            "entry_runner.db_config_missing",
            extra={"event": "entry_runner.db_config_missing", "detail": str(exc)},
        )
        return 2

    try:
        components = build_components(
            oanda=oanda,
            engine=engine,
            account_id=args.account_id,
            account_type=args.account_type,
            nominal_price=args.nominal_price,
        )
        policy = MinimumEntryPolicy(
            instrument=args.instrument,
            direction=args.direction,
            state_manager=components.state_manager,
            quote_feed=components.quote_feed,
            clock=components.clock,
            signal=components.signal,
            stale_after_seconds=args.stale_after_seconds,
        )

        log.info(
            "entry_runner.attached",
            extra={
                "event": "entry_runner.attached",
                "instrument": args.instrument,
                "oanda_environment": oanda.environment,
                "account_id_suffix": args.account_id[-4:],
                "interval_seconds": args.interval_seconds,
                "stale_after_seconds": args.stale_after_seconds,
                "stack": "paper",
            },
        )

        stop_flag = [False]
        _install_sigint_handler(stop_flag, log)

        iterations = run_loop(
            components=components,
            policy=policy,
            instrument=args.instrument,
            direction=args.direction,
            units=args.units,
            account_id=args.account_id,
            account_type=args.account_type,
            interval_seconds=args.interval_seconds,
            max_iterations=args.max_iterations,
            log=log,
            should_stop=lambda: stop_flag[0],
        )

        log.info(
            "entry_runner.shutdown",
            extra={"event": "entry_runner.shutdown", "iterations": iterations},
        )
        return 0
    finally:
        # Release pooled connections so SIGINT shutdown doesn't leave
        # idle Postgres sessions behind.  No-op on SQLite in-memory.
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
