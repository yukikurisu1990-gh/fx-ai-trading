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
from fx_ai_trading.domain.price_feed import Candle
from fx_ai_trading.domain.risk import Instrument
from fx_ai_trading.ops.logging_config import apply_logging_config
from fx_ai_trading.repositories.orders import OrdersRepository
from fx_ai_trading.services.feature_service import FeatureService
from fx_ai_trading.services.meta_cycle_runner import MetaCycleConfig, run_meta_cycle
from fx_ai_trading.services.position_sizer import PositionSizerService
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

# Phase 9.X-O clip cap: maximum position size in units (100 mini-lots).
_DEFAULT_MAX_UNITS = 10_000

# Phase 9.X-N margin-aware: Japan FX leverage limit (25:1).
_DEFAULT_MAX_LEVERAGE = 25.0

# Phase 9.X-J daily DD brake: halt if daily loss exceeds 3% of opening balance.
_DEFAULT_DAILY_DD_PCT = 3.0

# Phase 9.X-O recommended initial balance (¥300k) and risk per trade (1%).
_DEFAULT_INITIAL_BALANCE = 300_000.0
_DEFAULT_RISK_PCT = 1.0

# MetaDecision adopted_direction → PaperBroker side mapping.
_DIRECTION_TO_BROKER_SIDE: dict[str, str] = {"buy": "long", "sell": "short"}


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
) -> bool:
    """Execute the 5-step paper open sequence (D1 §6.6 FSM).

    Steps:
      1. OrdersRepository.create_order    → status=PENDING
      2. OrdersRepository.update_status   → SUBMITTED
      3. PaperBroker.place_order          → fills synchronously at fill_price
      4. OrdersRepository.update_status   → FILLED
      5. StateManager.on_fill             → positions(open) + secondary_sync_outbox

    Returns True on success. Returns False (without raising) when:
      - direction is unknown (neither 'buy' nor 'sell')
      - instrument is already open for this account (no pyramiding in paper mode)
      - PaperBroker unexpectedly does not fill (should not happen in paper mode)
    """
    side = _DIRECTION_TO_BROKER_SIDE.get(direction)
    if side is None:
        _log.error("paper_open: unknown direction %r — skipped (%s)", direction, instrument)
        return False

    if instrument in state_manager.open_instruments():
        _log.info("paper_open: %s already open for %s — skipped", instrument, account_id)
        return False

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
        return False

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
    return True


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
        "--max-spread-pip",
        type=float,
        default=2.0,
        metavar="PIPS",
        help=(
            "Pre-trade spread gate: skip trade if live bid/ask spread exceeds "
            "this threshold (in pips). Applied in live mode only; ignored in "
            "replay mode where real-time quotes are unavailable. Default 2.0 pips."
        ),
    )
    p.add_argument(
        "--feature-groups",
        default="",
        help=(
            "Phase 9.X-B/J-4 config plumbing only. "
            "Comma-separated feature groups to enable on top of the "
            "Phase 9.16 baseline. Valid: vol, moments, mtf. "
            "Recommended (per docs/design/phase9_x_b_closure_memo.md) "
            "is 'mtf' alone — 4h/daily/weekly stats lift Sharpe 0.160 "
            "→ 0.174 / PnL 1.85x at K=3. Empty (default) preserves "
            "Phase 9.16 production behaviour. "
            "ACTIVATION DEFERRED: actual feature computation in "
            "FeatureService requires _HISTORY_DEPTH expansion (100 → "
            "~2000 bars) and FEATURE_VERSION bump (v2 → v3). This PR "
            "ships only the flag plumbing; flag value validated and "
            "stored but not yet wired into FeatureService."
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
            "Phase 9.X-O clip cap: maximum position size in units. "
            "Sized positions are clamped to min(computed, max_units). "
            "Default 10,000 (= 100 mini-lots). "
            "Eliminates compounding blowup risk at high K."
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
    args = p.parse_args(argv)
    if args.top_k < 1:
        p.error(f"--top-k must be >= 1 (got {args.top_k})")
    if args.risk_pct <= 0 or args.risk_pct > 100:
        p.error(f"--risk-pct must be in (0, 100], got {args.risk_pct}")
    if args.max_units < 1:
        p.error(f"--max-units must be >= 1, got {args.max_units}")
    if args.max_leverage <= 0:
        p.error(f"--max-leverage must be > 0, got {args.max_leverage}")
    if args.daily_dd_pct <= 0 or args.daily_dd_pct > 100:
        p.error(f"--daily-dd-pct must be in (0, 100], got {args.daily_dd_pct}")
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


def _fetch_spread_pips(
    client: OandaAPIClient,
    account_id: str,
    instrument: str,
) -> float | None:
    """Return current bid/ask spread in pips, or None if unavailable."""
    try:
        prices = client.get_pricing(account_id, [instrument])
        if not prices:
            return None
        entry = prices[0]
        bids = entry.get("bids", [])
        asks = entry.get("asks", [])
        if not bids or not asks:
            return None
        bid = float(bids[0]["price"])
        ask = float(asks[0]["price"])
        pip = _PIP_SIZE.get(instrument, 0.0001)
        return (ask - bid) / pip
    except Exception:
        _log.warning("spread fetch failed for %s — gate skipped", instrument, exc_info=True)
        return None


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


def _compute_position_size(
    inst: str,
    features: dict[str, FeatureSet],
    initial_balance: float,
    risk_pct: float,
    max_units: int,
    max_leverage: float,
    bar_close: float,
) -> tuple[int, str | None]:
    """Compute risk-sized position with clip cap and margin check.

    Returns (size_units, skip_reason). size_units=0 means skip this trade.

    Steps:
      1. ATR-based SL distance → PositionSizerService (risk-% formula)
      2. Clip cap: min(computed, max_units)
      3. Margin-aware: skip if margin_required > 50% of initial_balance
    """
    feat = features.get(inst)
    if feat is None:
        return 0, "NoFeatures"
    atr = feat.sampled_features.get("atr_14", 0.0)
    if not atr or atr <= 0:
        return 0, "NoATR"
    pip = _PIP_SIZE.get(inst, 0.0001)
    sl_pips = atr / pip
    instrument_ref = Instrument(
        instrument=inst,
        base_currency=inst[:3],
        quote_currency=inst[4:] if len(inst) > 4 else "???",
        pip_location=-4 if pip == 0.0001 else -2,
        min_trade_units=1,
    )
    sizer = PositionSizerService(risk_pct=risk_pct)
    sr = sizer.size(initial_balance, risk_pct, sl_pips, instrument_ref)
    if sr.size_units == 0:
        return 0, sr.reason or "SizeUnderMin"

    # Apply clip cap (Phase 9.X-O: 100 mini-lots).
    size_units = min(sr.size_units, max_units)
    clipped = size_units < sr.size_units
    if clipped:
        _log.debug(
            "clip cap applied: %s raw=%d → %d (max_units=%d)",
            inst,
            sr.size_units,
            size_units,
            max_units,
        )

    # Margin-aware check (Phase 9.X-N: Japan 25:1 leverage limit).
    # Approximation: margin_required = units × close_price / leverage.
    # For JPY-quoted pairs this gives JPY margin directly; for non-JPY
    # pairs it overestimates slightly (base-to-JPY conversion omitted
    # — conservative bias is intentional for paper mode).
    if bar_close > 0 and max_leverage > 0:
        margin_required = size_units * bar_close / max_leverage
        margin_limit = initial_balance * 0.5
        if margin_required > margin_limit:
            # Reduce size to fit within 50% margin constraint.
            reduced = int(margin_limit * max_leverage / bar_close)
            if reduced < 1:
                return 0, "InsufficientMargin"
            size_units = reduced
            _log.debug(
                "margin-aware size reduction: %s margin_req=%.2f > limit=%.2f → units=%d",
                inst,
                margin_required,
                margin_limit,
                size_units,
            )

    return size_units, None


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
        strategies = [LGBMStrategy(strategy_id="lgbm")]

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
    dd_brake = _DailyDrawdownBrake(
        opening_balance=args.initial_balance,
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
                # Spread gate (live mode only — replay has no real-time quotes).
                if is_live and oanda_client is not None and inst is not None:
                    spread_pip = _fetch_spread_pips(oanda_client, account_id, inst)
                    if spread_pip is not None and spread_pip > args.max_spread_pip:
                        _log.info(
                            "spread_too_wide: trade skipped",
                            extra={
                                "instrument": inst,
                                "spread_pip": round(spread_pip, 3),
                                "max_spread_pip": args.max_spread_pip,
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

                # Phase 9.X-K: compute risk-sized position (clip cap + margin check).
                # Sizing is logged regardless of whether the broker call is live.
                size_units, skip_reason = _compute_position_size(
                    inst=inst or "",
                    features=features,
                    initial_balance=args.initial_balance,
                    risk_pct=args.risk_pct,
                    max_units=args.max_units,
                    max_leverage=args.max_leverage,
                    bar_close=bar.close,
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
                        "initial_balance": args.initial_balance,
                        "risk_pct": args.risk_pct,
                        "max_units": args.max_units,
                    },
                )

                _open_paper_position(
                    engine=engine,
                    account_id=account_id,
                    instrument=inst or "",
                    direction=meta_result.adopted_direction or "",
                    size_units=size_units,
                    fill_price=bar.close,
                    clock=clock,
                    state_manager=state_manager,
                    orders_repo=orders_repo,
                    orders_context=orders_context,
                    trading_signal_id=meta_result.trading_signal_id,
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
