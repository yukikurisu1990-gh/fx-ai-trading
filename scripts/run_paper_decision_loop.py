"""``run_paper_decision_loop`` — D3 bar-cadence decision runner (Phase 9.1/9.2).

Wires the full D3 pipeline for paper trading:

  BarFeed  →  FeatureService  →  run_strategy_cycle  →  run_meta_cycle
                                                              ↓
                                                    MetaDecision (logged)
                                                              ↓
                                               (if trade + not --dry-run)
                                          Phase 9.X-K pre-trade gate:
                                            1. Clip cap (--max-units)
                                            2. Margin-aware sizing (--max-leverage)
                                            3. Daily DD brake (--daily-dd-pct)
                                            → position opened (paper)

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
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from fx_ai_trading.adapters.broker.paper import PaperBroker
from fx_ai_trading.adapters.instrument_registry import OandaInstrumentRegistry
from fx_ai_trading.adapters.price_feed.candle_file_bar_feed import CandleFileBarFeed
from fx_ai_trading.adapters.price_feed.oanda_bar_feed import OandaBarFeed
from fx_ai_trading.common.clock import Clock, WallClock
from fx_ai_trading.common.ulid import generate_ulid
from fx_ai_trading.config.common_keys_context import CommonKeysContext
from fx_ai_trading.domain.broker import OrderRequest
from fx_ai_trading.domain.price_feed import Candle, callable_to_quote_feed
from fx_ai_trading.domain.risk import Instrument
from fx_ai_trading.ops.logging_config import apply_logging_config
from fx_ai_trading.repositories.orders import OrdersRepository
from fx_ai_trading.services.exit_gate_runner import run_exit_gate
from fx_ai_trading.services.exit_policy import ExitPolicyService
from fx_ai_trading.services.feature_service import FeatureService
from fx_ai_trading.services.meta_cycle_runner import MetaCycleConfig, run_meta_cycle
from fx_ai_trading.services.position_sizer import PositionSizerService
from fx_ai_trading.services.risk_manager import RiskManagerService
from fx_ai_trading.services.startup_position_check import check_position_integrity
from fx_ai_trading.services.state_manager import StateManager
from fx_ai_trading.services.strategies.atr import ATRStrategy
from fx_ai_trading.services.strategies.bollinger import BollingerStrategy
from fx_ai_trading.services.strategies.lgbm_strategy import LGBMStrategy
from fx_ai_trading.services.strategies.ma import MAStrategy
from fx_ai_trading.services.strategies.macd import MACDStrategy
from fx_ai_trading.services.strategies.rsi import RSIStrategy
from fx_ai_trading.services.strategy_runner import run_strategy_cycle

if TYPE_CHECKING:
    from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient
    from fx_ai_trading.domain.feature import FeatureSet

_log = logging.getLogger(__name__)

_ENV_DATABASE_URL = "DATABASE_URL"
_ENV_OANDA_ACCOUNT_ID = "OANDA_ACCOUNT_ID"
_ENV_OANDA_ACCESS_TOKEN = "OANDA_ACCESS_TOKEN"

# Rolling bar history depth for FeatureService.
# Default 100 bars covers Phase 9.16 baseline (SMA_50 needs ≥50 bars).
# When --feature-groups mtf is active, weekly stats need ≥7 days of m5
# bars (~2,016) — depth is auto-expanded in run() based on enabled groups.
# When --feature-groups vol is active, ewma_var_60 needs ~7 half-lives
# (~420 bars) for the EWMA to converge cleanly.
_HISTORY_DEPTH_BASELINE = 100
_HISTORY_DEPTH_VOL = 500  # halflife=60 EWMA × ~7 half-lives + safety margin
_HISTORY_DEPTH_MTF = 2100  # 7d × 24h × 12 bars/h + safety margin
_HISTORY_DEPTH = _HISTORY_DEPTH_BASELINE  # back-compat module-level alias

# Phase 9.X-O clip cap: 0 = no cap (rely on leverage cap only).
_DEFAULT_MAX_UNITS = 0

# Phase 9.X-N margin-aware: Japan FX leverage limit (25:1).
_DEFAULT_MAX_LEVERAGE = 25.0

# Phase 9.X-J daily DD brake: halt if daily loss exceeds 3% of opening balance.
_DEFAULT_DAILY_DD_PCT = 3.0

# Phase 9.X-O recommended initial balance (¥300k) and risk per trade (1%).
_DEFAULT_INITIAL_BALANCE = 300_000.0
_DEFAULT_RISK_PCT = 1.0

# MetaDecision adopted_direction → PaperBroker side mapping.
_DIRECTION_TO_BROKER_SIDE: dict[str, str] = {"buy": "long", "sell": "short"}

# B-2 triple-barrier TP/SL ATR multipliers (matching train_lgbm_models.py).
# Used to compute absolute price TP/SL levels stored in _tpsl_map at open time.
_TP_MULT = 1.5
_SL_MULT = 1.0

# Reference data required before any FK-dependent table can be written.
_BROKER_SEED = ("OANDA", "OANDA", "https://api-fxpractice.oanda.com")
_INSTRUMENT_SEED: list[tuple[str, str, str, int]] = [
    ("AUD_CAD", "AUD", "CAD", -4),
    ("AUD_JPY", "AUD", "JPY", -2),
    ("AUD_NZD", "AUD", "NZD", -4),
    ("AUD_USD", "AUD", "USD", -4),
    ("CHF_JPY", "CHF", "JPY", -2),
    ("EUR_AUD", "EUR", "AUD", -4),
    ("EUR_CAD", "EUR", "CAD", -4),
    ("EUR_CHF", "EUR", "CHF", -4),
    ("EUR_GBP", "EUR", "GBP", -4),
    ("EUR_JPY", "EUR", "JPY", -2),
    ("EUR_USD", "EUR", "USD", -4),
    ("GBP_AUD", "GBP", "AUD", -4),
    ("GBP_CHF", "GBP", "CHF", -4),
    ("GBP_JPY", "GBP", "JPY", -2),
    ("GBP_USD", "GBP", "USD", -4),
    ("NZD_JPY", "NZD", "JPY", -2),
    ("NZD_USD", "NZD", "USD", -4),
    ("USD_CAD", "USD", "CAD", -4),
    ("USD_CHF", "USD", "CHF", -4),
    ("USD_JPY", "USD", "JPY", -2),
]


def _ensure_reference_data(engine) -> None:
    """Seed brokers + instruments on every startup (idempotent, ON CONFLICT DO NOTHING).

    Prevents FK cascading failures when these reference tables are accidentally
    wiped (migration re-run, restore from backup, etc.).
    """
    from sqlalchemy import text as _text

    broker_id, broker_name, broker_url = _BROKER_SEED
    with engine.begin() as conn:
        conn.execute(
            _text(
                "INSERT INTO brokers (broker_id, name, api_base_url)"
                " VALUES (:id, :name, :url) ON CONFLICT (broker_id) DO NOTHING"
            ),
            {"id": broker_id, "name": broker_name, "url": broker_url},
        )
        for inst, base, quote, pip_loc in _INSTRUMENT_SEED:
            conn.execute(
                _text(
                    "INSERT INTO instruments"
                    " (instrument, base_currency, quote_currency, pip_location, min_trade_units)"
                    " VALUES (:inst, :base, :quote, :pip, :min_units)"
                    " ON CONFLICT (instrument) DO NOTHING"
                ),
                {"inst": inst, "base": base, "quote": quote, "pip": pip_loc, "min_units": 1000},
            )
    _log.info("reference data: brokers + %d instruments ensured", len(_INSTRUMENT_SEED))


# ---------------------------------------------------------------------------
# Granularity helper
# ---------------------------------------------------------------------------


def _granularity_minutes(granularity: str) -> int:
    """Return the number of minutes per bar for an OANDA granularity string.

    Examples: "M1" → 1, "M5" → 5, "H1" → 60, "H4" → 240.
    Falls back to 5 (M5) for unrecognised strings.
    """
    gran = granularity.upper()
    if gran.startswith("M"):
        try:
            return int(gran[1:])
        except ValueError:
            pass
    if gran.startswith("H"):
        try:
            return int(gran[1:]) * 60
        except ValueError:
            pass
    return 5


# ---------------------------------------------------------------------------
# Live (OandaBroker) open helper (5-step FSM sequence)
# ---------------------------------------------------------------------------


def _open_live_position(
    *,
    account_id: str,
    instrument: str,
    direction: str,
    size_units: int,
    clock: Clock,
    state_manager: StateManager,
    orders_repo: OrdersRepository,
    orders_context: CommonKeysContext,
    broker: object,  # OandaBroker — avoids import at module level
    trading_signal_id: str | None = None,
    tp: float | None = None,
    sl: float | None = None,
) -> str | None:
    """Execute the 5-step live open sequence using OandaBroker.

    Same FSM as _open_paper_position; fill price and broker_order_id
    come from the real OANDA REST response instead of PaperBroker.

    Returns the order_id (str) on success.  Returns None when:
      - direction is unknown
      - instrument is already open (no pyramiding)
      - OANDA did not return a filled status
    """
    side = _DIRECTION_TO_BROKER_SIDE.get(direction)
    if side is None:
        _log.error("live_open: unknown direction %r — skipped (%s)", direction, instrument)
        return None

    if instrument in state_manager.open_instruments():
        _log.info("live_open: %s already open for %s — skipped", instrument, account_id)
        return None

    order_id = generate_ulid()
    client_order_id = f"dl:{order_id}:{instrument}"

    # Step 1: PENDING
    orders_repo.create_order(
        order_id=order_id,
        account_id=account_id,
        instrument=instrument,
        account_type=broker.account_type,
        order_type="market",
        direction=direction,
        units=str(size_units),
        context=orders_context,
        client_order_id=client_order_id,
        trading_signal_id=trading_signal_id,
    )

    # Step 2: SUBMITTED
    orders_repo.update_status(order_id, "SUBMITTED", orders_context)

    # Step 3: OandaBroker fill (real OANDA REST call)
    from fx_ai_trading.domain.broker import OrderRequest

    request = OrderRequest(
        client_order_id=client_order_id,
        account_id=account_id,
        instrument=instrument,
        side=side,
        size_units=size_units,
        tp=tp,
        sl=sl,
    )
    try:
        result = broker.place_order(request)
    except Exception:
        _log.exception("live_open: place_order raised — order_id=%s", order_id)
        orders_repo.update_status(order_id, "FAILED", orders_context)
        return None

    if result.status != "filled" or result.fill_price is None:
        _log.error(
            "live_open: broker did not fill — order_id=%s status=%r message=%r",
            order_id,
            result.status,
            result.message,
        )
        orders_repo.update_status(order_id, "FAILED", orders_context)
        return None

    # Step 4: FILLED
    orders_repo.update_status(order_id, "FILLED", orders_context)

    # Step 5: positions(open) + secondary_sync_outbox
    state_manager.on_fill(
        order_id=order_id,
        instrument=instrument,
        units=size_units,
        avg_price=float(result.fill_price),
    )

    _log.info(
        "live_open: position opened",
        extra={
            "instrument": instrument,
            "direction": direction,
            "size_units": size_units,
            "fill_price": result.fill_price,
            "broker_order_id": result.broker_order_id,
            "order_id": order_id,
        },
    )
    return order_id


# ---------------------------------------------------------------------------
# Paper open helper (5-step FSM sequence)
# ---------------------------------------------------------------------------


def _open_paper_position(
    *,
    engine: Engine,
    account_id: str,
    instrument: str,
    direction: str,
    size_units: int,
    fill_price: float,
    clock: Clock,
    state_manager: StateManager,
    orders_repo: OrdersRepository,
    orders_context: CommonKeysContext,
    trading_signal_id: str | None = None,
) -> str | None:
    """Execute the 5-step paper open sequence (D1 §6.6 FSM).

    Steps:
      1. OrdersRepository.create_order    → status=PENDING
      2. OrdersRepository.update_status   → SUBMITTED
      3. PaperBroker.place_order          → fills synchronously at fill_price
      4. OrdersRepository.update_status   → FILLED
      5. StateManager.on_fill             → positions(open) + secondary_sync_outbox

    Returns the order_id (str) on success. Returns None (without raising) when:
      - direction is unknown (neither 'buy' nor 'sell')
      - instrument is already open for this account (no pyramiding in paper mode)
      - PaperBroker unexpectedly does not fill (should not happen in paper mode)
    """
    side = _DIRECTION_TO_BROKER_SIDE.get(direction)
    if side is None:
        _log.error("paper_open: unknown direction %r — skipped (%s)", direction, instrument)
        return None

    if instrument in state_manager.open_instruments():
        _log.info("paper_open: %s already open for %s — skipped", instrument, account_id)
        return None

    order_id = generate_ulid()
    client_order_id = f"dl:{order_id}:{instrument}"

    # Step 1: PENDING
    orders_repo.create_order(
        order_id=order_id,
        account_id=account_id,
        instrument=instrument,
        account_type="demo",
        order_type="market",
        direction=direction,
        units=str(size_units),
        context=orders_context,
        client_order_id=client_order_id,
        trading_signal_id=trading_signal_id,
    )

    # Step 2: SUBMITTED
    orders_repo.update_status(order_id, "SUBMITTED", orders_context)

    # Step 3: PaperBroker fill (synchronous; nominal_price = current bar close)
    broker = PaperBroker(account_type="demo", nominal_price=fill_price)
    request = OrderRequest(
        client_order_id=client_order_id,
        account_id=account_id,
        instrument=instrument,
        side=side,
        size_units=size_units,
    )
    result = broker.place_order(request)
    if result.status != "filled" or result.fill_price is None:
        _log.error(
            "paper_open: broker did not fill — order_id=%s status=%r",
            order_id,
            result.status,
        )
        return None

    # Step 4: FILLED
    orders_repo.update_status(order_id, "FILLED", orders_context)

    # Step 5: positions(open) + secondary_sync_outbox
    state_manager.on_fill(
        order_id=order_id,
        instrument=instrument,
        units=size_units,
        avg_price=float(result.fill_price),
    )

    _log.info(
        "paper_open: position opened",
        extra={
            "instrument": instrument,
            "direction": direction,
            "size_units": size_units,
            "fill_price": result.fill_price,
            "order_id": order_id,
        },
    )
    return order_id


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
    p.add_argument(
        "--granularity",
        default="M1",
        choices=["M1"],
        help="Candle granularity. Only M1 is supported (must match LGBM training granularity).",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Run full D3 pipeline but skip position opening.",
    )
    p.add_argument("--log-level", default="INFO")
    p.add_argument(
        "--log-dir",
        dest="log_dir",
        type=Path,
        default=Path("logs"),
        help="Directory for the JSONL log file (default: logs/).",
    )
    p.add_argument(
        "--log-filename",
        dest="log_filename",
        type=str,
        default="paper_decision_loop.jsonl",
        help="JSONL filename inside --log-dir (default: paper_decision_loop.jsonl).",
    )
    p.add_argument(
        "--top-k",
        type=int,
        default=1,
        help=(
            "Phase 9.19/J-3 config plumbing only. "
            "Intended SELECTOR rule: adopt the K highest-EV candidates "
            "per cycle (backtest verified K=2 naive lifts PnL +25%%; "
            "see docs/design/phase9_19_closure_memo.md). "
            "Currently honours top_k in the F-16 sort but ADOPTS ONLY "
            "rank-1 (multi-trade adoption deferred — requires changes "
            "to MetaCycleRunResult, execution gateway, position-mgmt). "
            "Default 1 reproduces Phase 9.16 production behaviour."
        ),
    )
    p.add_argument(
        "--use-ta-strategies",
        action="store_true",
        default=False,
        help=(
            "Use unvalidated TA strategies (MA/ATR/RSI/MACD/Bollinger) instead "
            "of the default LGBM classifier. Intended for A/B testing only."
        ),
    )
    p.add_argument(
        "--max-slippage-pip",
        type=float,
        default=2.0,
        metavar="PIPS",
        help=(
            "Pre-trade sudden-move (急変) gate: skip trade if the live mid-price "
            "deviates from the latest bar close by more than this many pips. "
            "Applied in live mode only via the same get_pricing call as the "
            "spread gate (single round-trip). Default 2.0 pips."
        ),
    )
    p.add_argument(
        "--no-compound",
        dest="compound",
        action="store_false",
        help=(
            "Disable J-1 compounding: always size positions from --initial-balance "
            "regardless of accumulated realized PnL. Default is compounding=True "
            "(current_balance = initial_balance + SUM(pnl_realized))."
        ),
    )
    p.set_defaults(compound=True)
    p.add_argument(
        "--feature-groups",
        default="mtf",
        help=(
            "Comma-separated feature groups to activate. Valid: vol, mtf. "
            "Default 'mtf' enables the H4/D1/W1 multi-timeframe features "
            "(6 features) that are part of the v4 45-feature production set. "
            "M5/M15/H1 upper-TF features (24 features) are always computed "
            "regardless of this flag. Passing 'mtf' also auto-expands the "
            "rolling bar history to 2100 bars for weekly stats. "
            "Pass '' to disable the MTF group (reverts to 39 features)."
        ),
    )
    # -----------------------------------------------------------------------
    # Phase 9.X-K: production levers (clip cap + margin-aware + daily DD brake)
    # -----------------------------------------------------------------------
    p.add_argument(
        "--initial-balance",
        type=float,
        default=_DEFAULT_INITIAL_BALANCE,
        metavar="AMOUNT",
        help=(
            "Starting account balance in account currency (JPY). "
            "Used by PositionSizerService (risk-% sizing) and daily DD brake "
            "(threshold = initial_balance × daily_dd_pct / 100). "
            "Default ¥300,000 per Phase 9.X-O production recommendation."
        ),
    )
    p.add_argument(
        "--risk-pct",
        type=float,
        default=_DEFAULT_RISK_PCT,
        help=(
            "Risk percentage per trade passed to PositionSizerService "
            "(risk_amount = balance × risk_pct / 100). "
            "Default 1.0%% per Phase 9.X-O recommendation."
        ),
    )
    p.add_argument(
        "--max-units",
        type=int,
        default=_DEFAULT_MAX_UNITS,
        metavar="UNITS",
        help=(
            "Hard cap on position size in units. 0 = no cap (default); "
            "relies solely on leverage cap (50%% margin rule). "
            "Set > 0 to impose an additional upper bound."
        ),
    )
    p.add_argument(
        "--max-leverage",
        type=float,
        default=_DEFAULT_MAX_LEVERAGE,
        help=(
            "Phase 9.X-N margin-aware leverage limit. "
            "Trade skipped if margin_required = units × close / max_leverage "
            "exceeds 50%% of initial_balance. "
            "Default 25.0 (Japan FX regulation for retail accounts)."
        ),
    )
    p.add_argument(
        "--daily-dd-pct",
        type=float,
        default=_DEFAULT_DAILY_DD_PCT,
        help=(
            "Phase 9.X-J daily drawdown brake: halt new entries for the "
            "remainder of the UTC day if cumulative realized daily loss exceeds "
            "daily_dd_pct%% of initial_balance. Default 3.0%%."
        ),
    )
    p.add_argument(
        "--max-holding-bars",
        type=int,
        default=20,
        metavar="BARS",
        help=(
            "Exit gate: maximum bars a position may be held before "
            "max_holding_time exit fires. Converted to seconds as "
            "bars × granularity_minutes × 60. "
            "Default 20 matches the B-2 triple-barrier horizon "
            "(TP=1.5×ATR, SL=1.0×ATR, horizon=20 M5 bars)."
        ),
    )
    p.add_argument(
        "--max-open-positions",
        type=int,
        default=5,
        metavar="N",
        help=(
            "RiskManagerService G2 guard: skip new entry if the number of "
            "concurrent open positions reaches this limit. Also covers G1 "
            "(no duplicate instrument) and G3 (execution failure cooloff). "
            "Default 5 matches RiskManagerService._DEFAULT_MAX_OPEN_POSITIONS."
        ),
    )
    p.add_argument(
        "--live-execution",
        action="store_true",
        default=False,
        help=(
            "Use OandaBroker (real OANDA REST API) for position opening instead "
            "of PaperBroker simulation. Requires live bar-feed mode (no "
            "--replay-candles). The account type (demo/live) is determined by "
            "the OANDA account tied to OANDA_ACCESS_TOKEN. Default False "
            "(paper simulation)."
        ),
    )
    args = p.parse_args(argv)
    if args.top_k < 1:
        p.error(f"--top-k must be >= 1 (got {args.top_k})")
    if args.risk_pct <= 0 or args.risk_pct > 100:
        p.error(f"--risk-pct must be in (0, 100], got {args.risk_pct}")
    if args.max_units < 0:
        p.error(f"--max-units must be >= 0 (0 = no cap), got {args.max_units}")
    if args.max_leverage <= 0:
        p.error(f"--max-leverage must be > 0, got {args.max_leverage}")
    if args.daily_dd_pct <= 0 or args.daily_dd_pct > 100:
        p.error(f"--daily-dd-pct must be in (0, 100], got {args.daily_dd_pct}")
    if args.max_holding_bars < 1:
        p.error(f"--max-holding-bars must be >= 1, got {args.max_holding_bars}")
    if args.max_open_positions < 1:
        p.error(f"--max-open-positions must be >= 1, got {args.max_open_positions}")
    if args.live_execution and args.replay_candles is not None:
        p.error("--live-execution requires live bar-feed mode (incompatible with --replay-candles)")
    # Must mirror feature_service._VALID_GROUPS. "moments" was scoped during
    # J-4 plumbing but never wired into FeatureService — leave it out so a
    # typo doesn't reach runtime.
    valid_groups = {"vol", "mtf"}
    feature_groups = {g.strip() for g in args.feature_groups.split(",") if g.strip()}
    invalid_groups = feature_groups - valid_groups
    if invalid_groups:
        p.error(
            f"--feature-groups: invalid value(s) {sorted(invalid_groups)} "
            f"(valid: {sorted(valid_groups)})"
        )
    args.feature_groups_set = frozenset(feature_groups)
    return args


# ---------------------------------------------------------------------------
# Spread gate helper
# ---------------------------------------------------------------------------

_PIP_SIZE: dict[str, float] = {
    "AUD_CAD": 0.0001,
    "AUD_JPY": 0.01,
    "AUD_NZD": 0.0001,
    "AUD_USD": 0.0001,
    "CHF_JPY": 0.01,
    "EUR_AUD": 0.0001,
    "EUR_CAD": 0.0001,
    "EUR_CHF": 0.0001,
    "EUR_GBP": 0.0001,
    "EUR_JPY": 0.01,
    "EUR_USD": 0.0001,
    "GBP_AUD": 0.0001,
    "GBP_CHF": 0.0001,
    "GBP_JPY": 0.01,
    "GBP_USD": 0.0001,
    "NZD_JPY": 0.01,
    "NZD_USD": 0.0001,
    "USD_CAD": 0.0001,
    "USD_CHF": 0.0001,
    "USD_JPY": 0.01,
}


def _fetch_live_quote(
    client: OandaAPIClient,
    account_id: str,
    instrument: str,
) -> tuple[float | None, float | None]:
    """Return (spread_pips, mid_price) from a live OANDA pricing tick.

    Both values are None when the pricing endpoint is unavailable or returns
    an unexpected shape.  Callers should treat None as "gate skipped" (fail-open).
    A single get_pricing call covers both the spread gate and the sudden-move
    (急変) check, avoiding a redundant round-trip.
    """
    try:
        prices = client.get_pricing(account_id, [instrument])
        if not prices:
            return None, None
        entry = prices[0]
        bids = entry.get("bids", [])
        asks = entry.get("asks", [])
        if not bids or not asks:
            return None, None
        bid = float(bids[0]["price"])
        ask = float(asks[0]["price"])
        pip = _PIP_SIZE.get(instrument, 0.0001)
        spread_pips = (ask - bid) / pip
        mid_price = (bid + ask) / 2.0
        return spread_pips, mid_price
    except Exception:
        _log.warning("live quote fetch failed for %s — gates skipped", instrument, exc_info=True)
        return None, None


def _fetch_spread_pips(
    client: OandaAPIClient,
    account_id: str,
    instrument: str,
) -> float | None:
    """Return current bid/ask spread in pips, or None if unavailable."""
    spread, _ = _fetch_live_quote(client, account_id, instrument)
    return spread


# ---------------------------------------------------------------------------
# Phase 9.X-K: production lever helpers
# ---------------------------------------------------------------------------


class _DailyDrawdownBrake:
    """Intraday drawdown circuit breaker (Phase 9.X-J GO lever).

    Queries close_events for today's total realized loss.  Halts new entries
    for the remainder of the UTC day when cumulative daily loss exceeds
    dd_pct% of opening_balance.

    On DB query error the brake falls through safely (not engaged).
    """

    def __init__(self, opening_balance: float, dd_pct: float) -> None:
        self._threshold = opening_balance * dd_pct / 100.0
        self._opening_balance = opening_balance

    def is_engaged(self, engine: Engine, today: date) -> bool:
        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text(
                        "SELECT COALESCE(SUM(pnl_realized), 0.0) "
                        "FROM close_events "
                        "WHERE DATE(closed_at AT TIME ZONE 'UTC') = :today "
                        "  AND pnl_realized < 0"
                    ),
                    {"today": str(today)},
                ).one()
            daily_loss = float(row[0])
        except Exception:
            _log.debug("daily DD brake: DB query failed — brake not engaged")
            return False
        if daily_loss < -self._threshold:
            _log.warning(
                "daily DD brake engaged: daily_loss=%.2f exceeds threshold=%.2f (%.1f%% of %.2f)",
                daily_loss,
                -self._threshold,
                -daily_loss / self._opening_balance * 100,
                self._opening_balance,
            )
            return True
        return False


def _reconcile_broker_closes(
    *,
    broker: object,
    account_id: str,
    state_manager: StateManager,
    price_fn: object,
    tpsl_map: dict[str, tuple[float | None, float | None]],
) -> None:
    """Sync StateManager with OANDA for positions already auto-closed by TP/SL.

    When OANDA executes a takeProfitOnFill or stopLossOnFill order, the
    position disappears from OANDA's open-positions list but StateManager
    still holds it as open.  This function detects that discrepancy and
    calls on_close() so DB state stays consistent.

    Called in live mode only, before run_exit_gate each bar.
    """
    sm_positions = state_manager.open_position_details()
    if not sm_positions:
        return
    try:
        broker_positions = broker.get_positions(account_id)  # type: ignore[attr-defined]
    except Exception:
        _log.warning("reconcile: get_positions failed — skipping this bar")
        return

    broker_open: set[tuple[str, str]] = {(p.instrument, p.side) for p in broker_positions}

    for pos in sm_positions:
        if (pos.instrument, pos.side) in broker_open:
            continue  # still open at OANDA

        # Position gone from OANDA — auto-executed TP/SL or manual close.
        sign = 1 if pos.side == "long" else -1
        pos_tp, pos_sl = tpsl_map.get(pos.order_id, (None, None))

        try:
            current_price = price_fn(pos.instrument)  # type: ignore[operator]
        except Exception:
            current_price = pos.avg_price

        # Determine reason first, then assign fill_price.
        # When OANDA executes a takeProfitOnFill / stopLossOnFill order it
        # fills at exactly the attached limit price (no partial fill, no
        # slippage in the conventional sense for limit-type attached orders).
        # Using those levels as fill_price is therefore more accurate than
        # the current bar close.
        if pos_tp is not None and sign * (current_price - pos_tp) >= -1e-8:
            reason = "tp_hit_broker"
            fill_price = pos_tp
        elif pos_sl is not None and sign * (pos_sl - current_price) >= -1e-8:
            reason = "sl_hit_broker"
            fill_price = pos_sl
        else:
            reason = "closed_by_broker"
            fill_price = current_price  # best estimate; unknown external close

        pnl = (fill_price - pos.avg_price) * pos.units * sign

        _log.info(
            "reconcile: OANDA closed %s %s order=%s reason=%s fill=%.5f pnl=%.2f",
            pos.instrument,
            pos.side,
            pos.order_id,
            reason,
            fill_price,
            pnl,
        )
        state_manager.on_close(
            order_id=pos.order_id,
            instrument=pos.instrument,
            reasons=[{"priority": 1, "reason_code": reason, "detail": "oanda_auto_close"}],
            primary_reason_code=reason,
            pnl_realized=pnl,
        )
        tpsl_map.pop(pos.order_id, None)


def _compute_position_size(
    inst: str,
    features: dict[str, FeatureSet],
    initial_balance: float,
    risk_pct: float,
    max_units: int,
    max_leverage: float,
    bar_close: float,
) -> tuple[int, str | None]:
    """Compute risk-sized position with clip cap and leverage-aware margin check.

    Returns (size_units, skip_reason). size_units=0 means skip this trade.

    Steps:
      1. ATR-based SL in JPY/unit → risk-% formula (pip-value-corrected)
      2. Clip cap: min(computed, max_units)
      3. Leverage cap: max units such that margin ≤ 50 % of balance

    Pip-value correction:
      For JPY-quoted pairs (e.g. USD_JPY): ATR is already in JPY, so
        sl_value_jpy_per_unit = ATR.
      For non-JPY pairs (e.g. EUR_USD): ATR is in USD; we multiply by the
        current USD/JPY close fetched from the features dict.
      Fallback (no USD_JPY data): old simplified formula (ATR / pip_size).
    """
    feat = features.get(inst)
    if feat is None:
        return 0, "NoFeatures"
    atr = feat.sampled_features.get("atr_14", 0.0)
    if not atr or atr <= 0:
        return 0, "NoATR"
    pip = _PIP_SIZE.get(inst, 0.0001)

    # --- pip-value-corrected SL distance in JPY per unit ---
    quote_ccy = inst.split("_")[1] if "_" in inst else ""
    if quote_ccy == "JPY":
        # ATR is quoted in JPY; each unit moves ATR JPY at SL.
        sl_value_jpy = atr
    else:
        # ATR is in the quote currency (e.g., USD for EUR/USD).
        # Multiply by USDJPY close to get JPY equivalent.
        usdjpy_feat = features.get("USD_JPY")
        usdjpy_close = usdjpy_feat.sampled_features.get("last_close") if usdjpy_feat else None
        if usdjpy_close and usdjpy_close > 0:
            sl_value_jpy = atr * usdjpy_close
        else:
            # USD_JPY feature unavailable.  Using atr / pip (= pip count)
            # would implicitly assume USDJPY=1.0 and oversize by ~150×.
            # Use a conservative approximate rate instead.
            _log.warning(
                "_compute_position_size: USD_JPY feature missing for %s "
                "— falling back to USDJPY≈150 approximation",
                inst,
            )
            sl_value_jpy = atr * 150.0

    instrument_ref = Instrument(
        instrument=inst,
        base_currency=inst[:3],
        quote_currency=quote_ccy or "???",
        pip_location=-4 if pip == 0.0001 else -2,
        min_trade_units=1,
    )
    sizer = PositionSizerService(risk_pct=risk_pct)
    # Pass sl_value_jpy as sl_pips: sizer formula is risk_amount / sl_pips,
    # which is now dimensionally correct (JPY / JPY·unit⁻¹ = units).
    sr = sizer.size(initial_balance, risk_pct, sl_value_jpy, instrument_ref)
    if sr.size_units == 0:
        return 0, sr.reason or "SizeUnderMin"

    # Apply optional clip cap (max_units=0 means no cap).
    size_units = sr.size_units
    if max_units > 0 and size_units > max_units:
        _log.debug(
            "clip cap: %s raw=%d → %d (max_units=%d)",
            inst,
            size_units,
            max_units,
            max_units,
        )
        size_units = max_units

    # Leverage cap (Phase 9.X-N): margin ≤ 50 % of balance.
    # max_units_leverage = balance × 0.5 × leverage / price
    if bar_close > 0 and max_leverage > 0:
        max_units_leverage = int(initial_balance * 0.5 * max_leverage / bar_close)
        if max_units_leverage < 1:
            return 0, "InsufficientMargin"
        if size_units > max_units_leverage:
            _log.debug(
                "leverage cap: %s %d → %d (balance=%.0f, leverage=%.0f, price=%.5f)",
                inst,
                size_units,
                max_units_leverage,
                initial_balance,
                max_leverage,
                bar_close,
            )
            size_units = max_units_leverage

    return size_units, None


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


def _query_realized_pnl(engine: Engine, account_id: str) -> float:
    """Return the sum of all realized PnL for the given account.

    Used by J-1 compounding to adjust position sizing as profits accumulate.
    Returns 0.0 on DB error (fail-safe — sizing falls back to initial_balance).
    """
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT COALESCE(SUM(ce.pnl_realized), 0.0) "
                    "FROM close_events ce "
                    "INNER JOIN orders o ON ce.order_id = o.order_id "
                    "WHERE o.account_id = :account_id "
                    "  AND ce.pnl_realized IS NOT NULL"
                ),
                {"account_id": account_id},
            ).one()
        return float(row[0])
    except Exception:
        _log.debug("_query_realized_pnl: DB query failed — returning 0.0")
        return 0.0


def _query_live_balance(client: OandaAPIClient, account_id: str) -> float | None:
    """Fetch the current account balance from OANDA. Returns None on failure."""
    try:
        summary = client.get_account_summary(account_id)
        val = float(summary.get("balance", 0.0))
        return val if val > 0 else None
    except Exception:
        _log.warning("_query_live_balance: API call failed — falling back to initial_balance")
        return None


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


def _persist_candle(engine: Engine, bar: Candle) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO market_candles"
                    " (instrument, tier, event_time_utc, open, high, low, close, volume)"
                    " VALUES (:instrument, :tier, :ts, :open, :high, :low, :close, :volume)"
                    " ON CONFLICT (instrument, tier, event_time_utc) DO NOTHING"
                ),
                {
                    "instrument": bar.instrument,
                    "tier": bar.tier,
                    "ts": bar.time_utc,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                },
            )
    except Exception:
        _log.warning("_persist_candle: failed for %s %s", bar.instrument, bar.time_utc)


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
# External MTF bar fetcher (H4/D1/W1 direct from OANDA)
# ---------------------------------------------------------------------------

_MTF_EXT_REFRESH_SECS = 3600  # 1 時間ごとに D1/W1/H4 を再フェッチ


def _fetch_granularity_bars(
    oanda_client: object,
    instrument: str,
    granularity: str,
    count: int,
) -> list[dict]:
    """指定 granularity の完了済みバーを list[dict(open,high,low,close)] で返す。
    H4/D/W は UTC midnight アラインメントを指定して pandas resample と一致させる。
    """
    params: dict[str, object] = {"granularity": granularity, "count": count, "price": "M"}
    if granularity in ("H4", "D"):
        params.update({"dailyAlignment": 0, "alignmentTimezone": "UTC"})
    elif granularity == "W":
        params.update(
            {
                "weeklyAlignment": "Sunday",
                "dailyAlignment": 0,
                "alignmentTimezone": "UTC",
            }
        )
    try:
        resp = oanda_client.get_candles(  # type: ignore[union-attr]
            instrument,
            params=params,
        )
        bars = []
        for r in resp.get("candles", []):
            if not r.get("complete", True):
                continue
            mid = r["mid"]
            bars.append(
                {
                    "open": float(mid["o"]),
                    "high": float(mid["h"]),
                    "low": float(mid["l"]),
                    "close": float(mid["c"]),
                }
            )
        return bars
    except Exception:
        return []


def _load_ext_mtf(
    oanda_client: object,
    instruments: list[str],
    feature_service: FeatureService,
) -> None:
    """全ペアの H4(60本)/D1(30本)/W1(15本) を取得して feature_service に設定する。"""
    for inst in instruments:
        h4 = _fetch_granularity_bars(oanda_client, inst, "H4", 60)
        d1 = _fetch_granularity_bars(oanda_client, inst, "D", 30)
        w1 = _fetch_granularity_bars(oanda_client, inst, "W", 15)
        feature_service.set_ext_mtf_bars(inst, h4, d1, w1)
    _log.info("ext MTF bars loaded: %d instruments", len(instruments))


# ---------------------------------------------------------------------------
# FeatureService factory
# ---------------------------------------------------------------------------


def _make_feature_service(
    history: dict[str, deque],
    enable_groups: frozenset[str] = frozenset(),
) -> FeatureService:
    """Build FeatureService backed by the rolling bar-history deque.

    The lambda bridges ``Candle`` objects (stored in history) to the
    ``list[dict]`` format expected by FeatureService._compute_features().

    Phase 9.X-B/J-5: ``enable_groups`` activates opt-in feature groups
    (currently only "mtf"). When mtf is enabled, the rolling buffer
    depth at the call site MUST be expanded to >= 2,016 m5 bars.
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

    return FeatureService(get_candles=_get_candles, enable_groups=enable_groups)


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
        # Restrict to LGBM-trained pairs so strategy_signals FK (→instruments) is satisfied.
        _manifest_path = Path(__file__).resolve().parents[1] / "models" / "lgbm" / "manifest.json"
        if _manifest_path.exists():
            import json as _json

            _trained = set(_json.loads(_manifest_path.read_text()).get("trained_pairs", []))
            _before = len(active_instruments)
            active_instruments = [i for i in active_instruments if i in _trained]
            _log.info(
                "live mode: filtered %d → %d instruments (manifest trained_pairs)",
                _before,
                len(active_instruments),
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
    _ensure_reference_data(engine)
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

    # Phase 9.5-A: LGBM classifier is the primary strategy.
    # TA strategies (MA/ATR/RSI/MACD/Bollinger) are retained in the codebase
    # for future A/B testing but excluded from the default loop because they
    # are not backtest-validated and use arbitrary EV formulas.
    if args.use_ta_strategies:
        strategies: list = [
            MAStrategy(strategy_id="ma"),
            ATRStrategy(strategy_id="atr"),
            RSIStrategy(strategy_id="rsi"),
            MACDStrategy(strategy_id="macd"),
            BollingerStrategy(strategy_id="bollinger"),
        ]
    else:
        lgbm = LGBMStrategy(strategy_id="lgbm")
        try:
            lgbm.register_models(engine)
        except Exception:
            _log.warning(
                "LGBMStrategy.register_models failed — predictions table may be incomplete"
            )
        strategies = [lgbm]

    # Rolling per-instrument candle history (fed before FeatureService.build).
    # Phase 9.X-B/J-5: depth auto-expanded when --feature-groups mtf or vol
    # is set; mtf needs ≥7 days of m5 bars (~2,016) and vol needs ~7
    # half-lives of EWMA convergence (~420 bars). max() picks the larger
    # when both are enabled.
    enable_groups: frozenset[str] = args.feature_groups_set
    history_depth = _HISTORY_DEPTH_BASELINE
    if "mtf" in enable_groups:
        history_depth = max(history_depth, _HISTORY_DEPTH_MTF)
    if "vol" in enable_groups:
        history_depth = max(history_depth, _HISTORY_DEPTH_VOL)
    history: dict[str, deque] = {inst: deque(maxlen=history_depth) for inst in active_instruments}
    feature_service = _make_feature_service(history, enable_groups=enable_groups)

    # Live mode: warmup history for all instruments before starting loop.
    if is_live and oanda_client is not None:
        _warmup_history(oanda_client, active_instruments, args.granularity, history, history_depth)
        # Persist warmup bars to market_candles so the dashboard chart is
        # populated immediately for all 20 pairs (not just the reference instrument).
        _log.info("persisting warmup history to market_candles (%d instruments)…", len(history))
        for _inst, _buf in history.items():
            for _bar in _buf:
                _persist_candle(engine, _bar)
        _log.info("warmup candles persisted")
        # D1/W1 warmup fix: fetch proper-depth H4/D1/W1 bars directly from OANDA.
        # M1 warmup (2100 bars = 35h) is insufficient for D1-ATR14 (needs 14+ D1 bars).
        if "mtf" in enable_groups:
            _load_ext_mtf(oanda_client, active_instruments, feature_service)

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

    # Phase 9.X-K: instantiate daily DD brake (J-2 lever).
    # In live mode, calibrate to the actual OANDA balance fetched at startup.
    # In paper/replay mode, fall back to --initial-balance.
    startup_balance: float = args.initial_balance
    if is_live and oanda_client is not None:
        _fetched_balance = _query_live_balance(oanda_client, account_id)
        if _fetched_balance:
            startup_balance = _fetched_balance
            _log.info(
                "startup: live balance ¥%s fetched from OANDA (DD brake threshold ¥%s/day)",
                f"{startup_balance:,.0f}",
                f"{startup_balance * args.daily_dd_pct / 100:,.0f}",
            )
        else:
            _log.warning(
                "startup: could not fetch live balance; DD brake using --initial-balance ¥%s",
                f"{startup_balance:,.0f}",
            )
    dd_brake = _DailyDrawdownBrake(
        opening_balance=startup_balance,
        dd_pct=args.daily_dd_pct,
    )

    # Paper trading collaborators (shared across the full loop lifecycle).
    state_manager = StateManager(engine, account_id=account_id, clock=clock)
    orders_repo = OrdersRepository(engine)
    orders_context = CommonKeysContext(
        run_id=run_id,
        environment="demo",
        code_version="decision-loop",
        config_version="v1",
    )

    # Live execution broker (OandaBroker) — built only when --live-execution is set.
    # In paper/replay mode oanda_exec_broker is None; positions open via PaperBroker.
    oanda_exec_broker: object | None = None
    if args.live_execution:
        assert oanda_client is not None, "--live-execution requires live mode (no --replay-candles)"
        from fx_ai_trading.adapters.broker.oanda import OandaBroker

        token = (src.get(_ENV_OANDA_ACCESS_TOKEN) or "").strip()
        oanda_exec_broker = OandaBroker(
            account_id=account_id,
            access_token=token,
            account_type="demo",
            environment="practice",
            api_client=oanda_client,
        )
        _log.info("live_execution: OandaBroker initialised (account_type=demo)")

    # Startup position integrity check.
    # In live-execution mode: compare DB vs broker for drift detection.
    # In paper/replay mode: broker_instruments=None (no live broker to query).
    _broker_instruments: frozenset[str] | None = None
    if oanda_exec_broker is not None:
        _raw_positions = oanda_exec_broker.get_positions(account_id)  # type: ignore[union-attr]
        _broker_instruments = frozenset(p.instrument for p in _raw_positions)
    check_position_integrity(
        open_db_instruments=state_manager.open_instruments(),
        open_broker_instruments=_broker_instruments,
    )

    # Ensure the account row exists in the accounts table so the dashboard
    # sidebar can list it.  Safe to call on every startup (ON CONFLICT DO UPDATE).
    with engine.begin() as _conn:
        _conn.execute(
            text(
                "INSERT INTO accounts (account_id, broker_id, account_type, base_currency)"
                " VALUES (:aid, 'OANDA', :atype, 'JPY')"
                " ON CONFLICT (account_id) DO UPDATE SET account_type = EXCLUDED.account_type"
            ),
            {"aid": account_id, "atype": "demo" if is_live else "dummy"},
        )
    _log.info("accounts: upserted %s", account_id)

    # Exit gate: time-based policy (B-2 horizon = 20 bars × granularity).
    # TP/SL price-based exit is deferred — current_price awareness requires
    # storing entry-price TP/SL levels in the orders table (Phase 9.X-K+1).
    _gran_min = _granularity_minutes(args.granularity)
    max_holding_secs = args.max_holding_bars * _gran_min * 60
    exit_policy = ExitPolicyService(max_holding_seconds=max_holding_secs)
    _log.info(
        "exit_policy: max_holding=%ds (%d bars × %dmin)",
        max_holding_secs,
        args.max_holding_bars,
        _gran_min,
    )

    risk_manager = RiskManagerService(max_open_positions=args.max_open_positions)
    _log.info("risk_manager: max_open_positions=%d", args.max_open_positions)

    cycles_completed = 0
    _last_ext_mtf_refresh: float = 0.0  # epoch seconds; triggers first-bar refresh

    # Per-position TP/SL price map keyed by order_id.
    # Populated at open time from B-2 ATR multipliers; consumed by run_exit_gate.
    _tpsl_map: dict[str, tuple[float | None, float | None]] = {}

    try:
        from fx_ai_trading.adapters.price_feed.oanda_bar_feed import _parse_oanda_time

        for bar in bar_feed:  # type: ignore[union-attr]
            # Accumulate reference bar into history (no look-ahead).
            history[reference_instrument].append(bar)
            _persist_candle(engine, bar)

            # In live multi-instrument mode, refresh instrument list each cycle (I-8).
            if is_live and registry is not None:
                current_instruments = [i for i in registry.list_active() if i in active_instruments]
                for inst in current_instruments:
                    if inst not in history:
                        history[inst] = deque(maxlen=_HISTORY_DEPTH)
            else:
                current_instruments = active_instruments

            # Hourly refresh of external H4/D1/W1 bars for accurate MTF features.
            if is_live and oanda_client is not None and "mtf" in enable_groups:
                import time as _time_mod

                _now_epoch = _time_mod.time()
                if _now_epoch - _last_ext_mtf_refresh >= _MTF_EXT_REFRESH_SECS:
                    _load_ext_mtf(oanda_client, list(current_instruments), feature_service)
                    _last_ext_mtf_refresh = _now_epoch

            # Refresh bar history for all non-reference instruments in live mode.
            # Without this, features for the other 19 pairs would be computed from
            # warmup-only data and grow increasingly stale over the session.
            if is_live and oanda_client is not None:
                for inst in current_instruments:
                    if inst == reference_instrument:
                        continue
                    try:
                        resp = oanda_client.get_candles(
                            inst,
                            params={"granularity": args.granularity, "count": 2, "price": "M"},
                        )
                        for raw in resp.get("candles", []):
                            if not raw.get("complete", True):
                                continue
                            mid = raw["mid"]
                            c = Candle(
                                instrument=inst,
                                tier=args.granularity,
                                time_utc=_parse_oanda_time(raw["time"]),
                                open=float(mid["o"]),
                                high=float(mid["h"]),
                                low=float(mid["l"]),
                                close=float(mid["c"]),
                                volume=int(raw.get("volume", 0)),
                            )
                            buf = history[inst]
                            if not buf or c.time_utc > buf[-1].time_utc:
                                buf.append(c)
                                _persist_candle(engine, c)
                    except Exception:
                        _log.debug("bar refresh failed for %s — using cached history", inst)

            # --- Exit gate (runs before open decision — exit-before-entry) ---
            # Evaluates all open positions against ExitPolicyService and closes
            # those where max_holding_time fires.  TP/SL price levels are
            # deferred (requires per-position storage of entry TP/SL).
            # Uses per-instrument latest bar close as the current price.
            def _bar_price(inst: str, _hist: dict = history, _bar=bar) -> float:
                buf = _hist.get(inst)
                return buf[-1].close if buf else _bar.close

            try:
                # Live mode: use OandaBroker to actually send the close order
                # to OANDA and get the real fill price for PnL.
                # Paper mode: give PaperBroker a per-instrument quote_feed so
                # the fill price is instrument-specific (not the reference bar.close).
                if oanda_exec_broker is not None:
                    close_broker: object = oanda_exec_broker
                    # Reconcile: mark positions OANDA has already auto-closed
                    # via takeProfitOnFill / stopLossOnFill before running the
                    # exit gate so we don't try to close them a second time.
                    _reconcile_broker_closes(
                        broker=oanda_exec_broker,
                        account_id=account_id,
                        state_manager=state_manager,
                        price_fn=_bar_price,
                        tpsl_map=_tpsl_map,
                    )
                else:
                    close_broker = PaperBroker(
                        account_type="demo",
                        quote_feed=callable_to_quote_feed(_bar_price, clock=clock),
                    )
                run_exit_gate(
                    broker=close_broker,
                    account_id=account_id,
                    clock=clock,
                    state_manager=state_manager,
                    exit_policy=exit_policy,
                    quote_feed=_bar_price,
                    tp=None,
                    sl=None,
                    per_position_tpsl=_tpsl_map,
                )
            except Exception:
                _log.exception("run_exit_gate failed — open positions not evaluated this bar")

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
                    config=MetaCycleConfig(top_k=args.top_k),
                )
            except Exception:
                _log.exception("run_meta_cycle failed for cycle %s", cycle_id)
                continue

            _log.info(
                "cycle complete",
                extra={
                    "cycle_id": cycle_id,
                    "bar_time": bar.time_utc.isoformat(),
                    "adopted": meta_result.adopted,
                    "adopted_instrument": meta_result.adopted_instrument,
                    "adopted_direction": meta_result.adopted_direction,
                    "strategy_rows": strategy_result.rows_written,
                },
            )

            cycles_completed += 1

            if meta_result.adopted and not args.dry_run:
                inst = meta_result.adopted_instrument
                # Use the adopted instrument's latest bar close, not the reference bar.
                inst_close = _bar_price(inst or "")
                # Live-quote gate (live mode only — replay has no real-time quotes).
                # A single get_pricing call populates both the spread gate and the
                # sudden-move (急変) guard; skipping if either threshold is breached.
                if is_live and oanda_client is not None and inst is not None:
                    spread_pip, live_mid = _fetch_live_quote(oanda_client, account_id, inst)
                    if spread_pip is not None:
                        ev = meta_result.adopted_ev_after_cost or 0.0
                        # EV gate: skip if spread exceeds model's expected value.
                        if ev - spread_pip <= 0:
                            _log.info(
                                "spread_eats_ev: trade skipped",
                                extra={
                                    "instrument": inst,
                                    "spread_pip": round(spread_pip, 3),
                                    "ev_after_cost": round(ev, 4),
                                    "net_ev": round(ev - spread_pip, 4),
                                },
                            )
                            continue
                    if live_mid is not None:
                        _pip_sz = _PIP_SIZE.get(inst, 0.0001)
                        dev_pips = abs(live_mid - inst_close) / _pip_sz
                        if dev_pips > args.max_slippage_pip:
                            _log.info(
                                "sudden_move: trade skipped",
                                extra={
                                    "instrument": inst,
                                    "dev_pips": round(dev_pips, 3),
                                    "max_slippage_pip": args.max_slippage_pip,
                                    "live_mid": live_mid,
                                    "bar_close": inst_close,
                                },
                            )
                            continue

                # Phase 9.X-J: daily DD brake — halt entries when today's
                # realized loss exceeds dd_pct% of opening balance.
                today_utc = bar.time_utc.date()
                if dd_brake.is_engaged(engine, today_utc):
                    _log.info(
                        "daily_dd_brake: trade skipped",
                        extra={"instrument": inst, "bar_time": bar.time_utc.isoformat()},
                    )
                    continue

                # Live mode: use actual OANDA account balance as sizing base.
                # Paper/replay mode: fall back to initial_balance + realized PnL
                # (J-1 compounding) or initial_balance (--no-compound).
                if is_live and oanda_client is not None:
                    current_balance = max(
                        _query_live_balance(oanda_client, account_id) or args.initial_balance,
                        1.0,
                    )
                else:
                    current_balance = (
                        max(
                            args.initial_balance + _query_realized_pnl(engine, account_id),
                            1.0,
                        )
                        if args.compound
                        else args.initial_balance
                    )

                # Phase 9.X-K: compute risk-sized position (clip cap + margin check).
                # Sizing is logged regardless of whether the broker call is live.
                size_units, skip_reason = _compute_position_size(
                    inst=inst or "",
                    features=features,
                    initial_balance=current_balance,
                    risk_pct=args.risk_pct,
                    max_units=args.max_units,
                    max_leverage=args.max_leverage,
                    bar_close=inst_close,
                )
                if size_units == 0:
                    _log.info(
                        "sizing_skipped: trade skipped",
                        extra={"instrument": inst, "reason": skip_reason},
                    )
                    continue

                _log.info(
                    "trade intent: position sized",
                    extra={
                        "instrument": inst,
                        "direction": meta_result.adopted_direction,
                        "size_units": size_units,
                        "current_balance": current_balance,
                        "initial_balance": args.initial_balance,
                        "risk_pct": args.risk_pct,
                        "max_units": args.max_units,
                    },
                )

                # RiskManagerService pre-execution gate (G1/G2/G3).
                # G1: no duplicate instrument (defense-in-depth over _open_paper_position check).
                # G2: concurrent open positions cap (not checked elsewhere).
                # G3: recent execution failure cooloff (failure_count=0 until tracked).
                _open_instr = state_manager.open_instruments()
                _risk_result = risk_manager.allow_trade(
                    instrument=inst or "",
                    open_instruments=_open_instr,
                    concurrent_positions=len(_open_instr),
                    recent_failure_count=0,
                )
                if not _risk_result.allowed:
                    _log.info(
                        "risk_gate: trade rejected",
                        extra={
                            "instrument": inst,
                            "reject_reason": _risk_result.reject_reason,
                            "concurrent_positions": len(_open_instr),
                            "max_open_positions": args.max_open_positions,
                        },
                    )
                    continue

                # Compute absolute TP/SL price levels from B-2 ATR multipliers.
                # Stored in _tpsl_map and passed to run_exit_gate each bar.
                _direction = meta_result.adopted_direction or ""
                _feat = features.get(inst or "")
                _atr = _feat.sampled_features.get("atr_14", 0.0) if _feat else 0.0
                # OANDA price precision: JPY pairs = 3 dp, others = 5 dp.
                _price_dp = 3 if (inst or "").endswith("_JPY") else 5
                if _atr and _atr > 0:
                    if _direction == "buy":
                        _tp_price: float | None = round(inst_close + _TP_MULT * _atr, _price_dp)
                        _sl_price: float | None = round(inst_close - _SL_MULT * _atr, _price_dp)
                    else:  # sell
                        _tp_price = round(inst_close - _TP_MULT * _atr, _price_dp)
                        _sl_price = round(inst_close + _SL_MULT * _atr, _price_dp)
                else:
                    _tp_price = None
                    _sl_price = None

                if oanda_exec_broker is not None:
                    opened_order_id = _open_live_position(
                        account_id=account_id,
                        instrument=inst or "",
                        direction=_direction,
                        size_units=size_units,
                        clock=clock,
                        state_manager=state_manager,
                        orders_repo=orders_repo,
                        orders_context=orders_context,
                        broker=oanda_exec_broker,
                        trading_signal_id=meta_result.trading_signal_id,
                        tp=_tp_price,
                        sl=_sl_price,
                    )
                else:
                    opened_order_id = _open_paper_position(
                        engine=engine,
                        account_id=account_id,
                        instrument=inst or "",
                        direction=_direction,
                        size_units=size_units,
                        fill_price=inst_close,
                        clock=clock,
                        state_manager=state_manager,
                        orders_repo=orders_repo,
                        orders_context=orders_context,
                        trading_signal_id=meta_result.trading_signal_id,
                    )
                if opened_order_id:
                    _tpsl_map[opened_order_id] = (_tp_price, _sl_price)
                    _log.debug(
                        "tpsl_map: stored tp=%.5f sl=%.5f for order=%s (%s %s)",
                        _tp_price or 0.0,
                        _sl_price or 0.0,
                        opened_order_id,
                        inst,
                        _direction,
                    )

    except KeyboardInterrupt:
        _log.info("run_paper_decision_loop interrupted by user")
    finally:
        _finish_system_job(engine, run_id=run_id, cycles=cycles_completed)
        _log.info("run_paper_decision_loop finished — cycles=%d", cycles_completed)

    return 0


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    log_path = apply_logging_config(
        log_dir=args.log_dir,
        filename=args.log_filename,
        level=args.log_level,
    )
    print(f"Logging to: {log_path}  (tail -f {log_path})")
    sys.exit(run(args))


if __name__ == "__main__":
    main()
