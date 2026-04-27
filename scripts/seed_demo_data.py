"""Seed the DB with realistic demo account data for dashboard review.

Creates:
  - 1 broker  (OANDA)
  - 1 account (demo, JPY base)
  - 20 instruments
  - ~90 days of M1 candles for EUR_USD and USD_JPY
  - ~300 closed trades (orders + positions + close_events)
  - meta_decisions + strategy_signals for recent cycles

Usage:
    python scripts/seed_demo_data.py
    python scripts/seed_demo_data.py --database-url postgresql://...
    python scripts/seed_demo_data.py --days 30 --trades 100
    python scripts/seed_demo_data.py --candle-instrument USD_JPY
    python scripts/seed_demo_data.py --wipe  # drop existing demo rows first
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT / "src"))

from sqlalchemy import create_engine, text  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
_log = logging.getLogger(__name__)

_RNG = random.Random(42)

_BROKER_ID = "OANDA"
_ACCOUNT_ID = "demo-001-seed"
_ACCOUNT_TYPE = "demo"
_BASE_CURRENCY = "JPY"

_ALL_PAIRS: list[tuple[str, str, str, int]] = [
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

_BASE_PRICES = {
    "EUR_USD": 1.0850,
    "USD_JPY": 151.50,
    "GBP_USD": 1.2650,
    "AUD_USD": 0.6520,
    "EUR_JPY": 164.40,
    "GBP_JPY": 191.50,
    "EUR_GBP": 0.8580,
    "AUD_JPY": 98.70,
    "EUR_AUD": 1.6640,
    "EUR_CAD": 1.4760,
    "EUR_CHF": 0.9680,
    "EUR_NZD": 1.7920,
    "GBP_AUD": 1.9400,
    "GBP_CHF": 1.1780,
    "GBP_CAD": 1.7100,
    "NZD_USD": 0.6050,
    "NZD_JPY": 91.60,
    "USD_CAD": 1.3630,
    "USD_CHF": 1.0940,
    "AUD_CAD": 0.8880,
    "AUD_NZD": 1.0770,
    "CHF_JPY": 138.40,
}

_STRATEGIES = [
    "lgbm_v3",
    "lgbm_v3",
    "lgbm_v3",
    "rsi_strategy",
    "macd_strategy",
    "bollinger_strategy",
]
_EXIT_REASONS = ["TP", "TP", "TP", "SL", "SL", "TIME", "TIME", "META_EXIT"]


def _ulid_like() -> str:
    import time as _time

    ts = int(_time.time() * 1000) & 0xFFFFFFFFFF
    rand = _RNG.getrandbits(80)
    return f"{ts:010X}{rand:020X}"


def _make_candles(
    instrument: str,
    start: datetime,
    n_candles: int,
    base_price: float,
    pip_size: float,
) -> list[tuple]:
    rows: list[tuple] = []
    price = base_price
    volatility = base_price * 0.0003  # ~0.03% per bar
    t = start
    for _ in range(n_candles):
        drift = _RNG.gauss(0, volatility)
        open_ = price
        close = open_ + drift
        high = max(open_, close) + abs(_RNG.gauss(0, volatility * 0.5))
        low = min(open_, close) - abs(_RNG.gauss(0, volatility * 0.5))
        volume = _RNG.randint(50, 500)
        rows.append(
            (
                instrument,
                "M1",
                t,
                round(open_, 8),
                round(high, 8),
                round(low, 8),
                round(close, 8),
                volume,
            )
        )
        price = close
        t += timedelta(minutes=1)
    return rows


def _insert_candles_batch(conn, rows: list[tuple]) -> None:
    if not rows:
        return
    conn.execute(
        text(
            "INSERT INTO market_candles"
            " (instrument, tier, event_time_utc, open, high, low, close, volume)"
            " VALUES (:instrument, :tier, :ts, :open, :high, :low, :close, :volume)"
            " ON CONFLICT (instrument, tier, event_time_utc) DO NOTHING"
        ),
        [
            {
                "instrument": r[0],
                "tier": r[1],
                "ts": r[2],
                "open": r[3],
                "high": r[4],
                "low": r[5],
                "close": r[6],
                "volume": r[7],
            }
            for r in rows
        ],
    )


def _insert_broker(conn) -> None:
    conn.execute(
        text(
            "INSERT INTO brokers (broker_id, name, api_base_url)"
            " VALUES (:id, :name, :url)"
            " ON CONFLICT (broker_id) DO NOTHING"
        ),
        {"id": _BROKER_ID, "name": "OANDA", "url": "https://api-fxpractice.oanda.com"},
    )


def _insert_account(conn) -> None:
    conn.execute(
        text(
            "INSERT INTO accounts (account_id, broker_id, account_type, base_currency)"
            " VALUES (:id, :broker, :type, :cur)"
            " ON CONFLICT (account_id) DO NOTHING"
        ),
        {"id": _ACCOUNT_ID, "broker": _BROKER_ID, "type": _ACCOUNT_TYPE, "cur": _BASE_CURRENCY},
    )


def _insert_instruments(conn) -> None:
    for instrument, base, quote, pip_loc in _ALL_PAIRS:
        conn.execute(
            text(
                "INSERT INTO instruments"
                " (instrument, base_currency, quote_currency, pip_location, min_trade_units)"
                " VALUES (:inst, :base, :quote, :pip, :min_units)"
                " ON CONFLICT (instrument) DO NOTHING"
            ),
            {"inst": instrument, "base": base, "quote": quote, "pip": pip_loc, "min_units": 1000},
        )


def _generate_trades(
    conn,
    n_trades: int,
    start: datetime,
    end: datetime,
) -> None:
    """Generate synthetic closed trades with proper FK chain."""
    span = (end - start).total_seconds()
    pairs_for_trades = ["EUR_USD", "USD_JPY", "GBP_USD", "EUR_JPY", "AUD_USD", "GBP_JPY"]
    # Ensure these instruments are inserted
    for inst in pairs_for_trades:
        entry = next((x for x in _ALL_PAIRS if x[0] == inst), None)
        if entry:
            conn.execute(
                text(
                    "INSERT INTO instruments"
                    " (instrument, base_currency, quote_currency, pip_location, min_trade_units)"
                    " VALUES (:inst, :base, :quote, :pip, :min_units)"
                    " ON CONFLICT (instrument) DO NOTHING"
                ),
                {
                    "inst": entry[0],
                    "base": entry[1],
                    "quote": entry[2],
                    "pip": entry[3],
                    "min_units": 1000,
                },
            )

    inserted_trades = 0
    for _i in range(n_trades):
        # Random entry time
        entry_offset = _RNG.uniform(0, span * 0.95)
        entry_time = start + timedelta(seconds=entry_offset)
        hold_minutes = _RNG.randint(15, 480)
        exit_time = entry_time + timedelta(minutes=hold_minutes)
        if exit_time > end:
            exit_time = end - timedelta(minutes=1)

        instrument = _RNG.choice(pairs_for_trades)
        base_price = _BASE_PRICES.get(instrument, 1.0)
        is_jpy = instrument.endswith("_JPY")
        pip_value = 0.01 if is_jpy else 0.0001
        direction = _RNG.choice(["buy", "sell"])
        strategy = _RNG.choice(_STRATEGIES)
        exit_reason = _RNG.choice(_EXIT_REASONS)

        # Price drift over hold period
        drift_pips = _RNG.gauss(0.5, 8.0)  # slight positive bias
        entry_price = base_price + _RNG.gauss(0, base_price * 0.002)
        exit_price = entry_price + (drift_pips * pip_value * (1 if direction == "buy" else -1))

        units = _RNG.choice([1000, 2000, 5000, 10000])
        pnl_raw = (exit_price - entry_price) * units * (1 if direction == "buy" else -1)
        pnl_jpy = pnl_raw if is_jpy else pnl_raw * 151.5  # approx USD→JPY
        pnl_jpy = round(pnl_jpy, 2)

        cycle_id = _ulid_like()
        meta_decision_id = _ulid_like()
        trading_signal_id = _ulid_like()
        order_id = _ulid_like()
        position_snapshot_open_id = _ulid_like()
        position_snapshot_close_id = _ulid_like()
        close_event_id = _ulid_like()

        # meta_decisions
        conn.execute(
            text(
                "INSERT INTO meta_decisions"
                " (meta_decision_id, cycle_id, filter_result, active_strategies,"
                "  regime_detected, decision_time_utc, no_trade_reason)"
                " VALUES (:mid, :cid, :fr, :as_, :regime, :dt, NULL)"
                " ON CONFLICT (meta_decision_id) DO NOTHING"
            ),
            {
                "mid": meta_decision_id,
                "cid": cycle_id,
                "fr": json.dumps({"passed": [instrument], "filtered": []}),
                "as_": json.dumps([strategy]),
                "regime": _RNG.choice(["trend", "range", "high_vol"]),
                "dt": entry_time,
            },
        )

        # strategy_signals
        conn.execute(
            text(
                "INSERT INTO strategy_signals"
                " (cycle_id, instrument, strategy_id, strategy_type,"
                "  signal_direction, confidence, signal_time_utc)"
                " VALUES (:cid, :inst, :sid, :stype, :dir, :conf, :st)"
                " ON CONFLICT (cycle_id, instrument, strategy_id) DO NOTHING"
            ),
            {
                "cid": cycle_id,
                "inst": instrument,
                "sid": strategy,
                "stype": strategy.split("_")[0],
                "dir": direction,
                "conf": round(_RNG.uniform(0.52, 0.88), 4),
                "st": entry_time,
            },
        )

        # trading_signals
        conn.execute(
            text(
                "INSERT INTO trading_signals"
                " (trading_signal_id, meta_decision_id, cycle_id, instrument,"
                "  strategy_id, signal_direction, signal_time_utc)"
                " VALUES (:tsid, :mid, :cid, :inst, :sid, :dir, :st)"
                " ON CONFLICT (trading_signal_id) DO NOTHING"
            ),
            {
                "tsid": trading_signal_id,
                "mid": meta_decision_id,
                "cid": cycle_id,
                "inst": instrument,
                "sid": strategy,
                "dir": direction,
                "st": entry_time,
            },
        )

        # orders
        conn.execute(
            text(
                "INSERT INTO orders"
                " (order_id, client_order_id, trading_signal_id, account_id, instrument,"
                "  account_type, order_type, direction, units, status,"
                "  submitted_at, filled_at)"
                " VALUES (:oid, :coid, :tsid, :aid, :inst,"
                "         :atype, 'market', :dir, :units, 'FILLED',"
                "         :sub_at, :fill_at)"
                " ON CONFLICT (order_id) DO NOTHING"
            ),
            {
                "oid": order_id,
                "coid": f"{order_id}:{instrument}:{strategy}",
                "tsid": trading_signal_id,
                "aid": _ACCOUNT_ID,
                "inst": instrument,
                "atype": _ACCOUNT_TYPE,
                "dir": direction,
                "units": units,
                "sub_at": entry_time,
                "fill_at": entry_time + timedelta(milliseconds=_RNG.randint(50, 500)),
            },
        )

        # position open
        conn.execute(
            text(
                "INSERT INTO positions"
                " (position_snapshot_id, order_id, account_id, instrument,"
                "  event_type, units, avg_price, unrealized_pl, realized_pl, event_time_utc)"
                " VALUES (:psid, :oid, :aid, :inst,"
                "         'open', :units, :avg_price, 0, NULL, :et)"
                " ON CONFLICT (position_snapshot_id) DO NOTHING"
            ),
            {
                "psid": position_snapshot_open_id,
                "oid": order_id,
                "aid": _ACCOUNT_ID,
                "inst": instrument,
                "units": units,
                "avg_price": round(entry_price, 8),
                "et": entry_time,
            },
        )

        # position close
        conn.execute(
            text(
                "INSERT INTO positions"
                " (position_snapshot_id, order_id, account_id, instrument,"
                "  event_type, units, avg_price, unrealized_pl, realized_pl, event_time_utc)"
                " VALUES (:psid, :oid, :aid, :inst,"
                "         'close', 0, :avg_price, 0, :pnl, :et)"
                " ON CONFLICT (position_snapshot_id) DO NOTHING"
            ),
            {
                "psid": position_snapshot_close_id,
                "oid": order_id,
                "aid": _ACCOUNT_ID,
                "inst": instrument,
                "avg_price": round(exit_price, 8),
                "pnl": pnl_jpy,
                "et": exit_time,
            },
        )

        # close_events
        conn.execute(
            text(
                "INSERT INTO close_events"
                " (close_event_id, order_id, position_snapshot_id,"
                "  reasons, primary_reason_code, closed_at, pnl_realized)"
                " VALUES (:ceid, :oid, :psid,"
                "         :reasons, :reason, :closed_at, :pnl)"
                " ON CONFLICT (close_event_id) DO NOTHING"
            ),
            {
                "ceid": close_event_id,
                "oid": order_id,
                "psid": position_snapshot_close_id,
                "reasons": json.dumps([{"priority": 1, "reason_code": exit_reason, "detail": ""}]),
                "reason": exit_reason,
                "closed_at": exit_time,
                "pnl": pnl_jpy,
            },
        )
        inserted_trades += 1

    _log.info("inserted %d trades", inserted_trades)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--database-url", default=os.environ.get("DATABASE_URL", ""))
    ap.add_argument("--days", type=int, default=90, help="Trading history span in days")
    ap.add_argument("--trades", type=int, default=300, help="Number of closed trades to insert")
    ap.add_argument(
        "--candle-instruments",
        nargs="+",
        default=["EUR_USD", "USD_JPY"],
        help="Instruments to seed M1 candles for",
    )
    ap.add_argument(
        "--candle-days",
        type=int,
        default=7,
        help="Days of M1 candles per instrument (7d = ~10080 rows)",
    )
    ap.add_argument("--wipe", action="store_true", help="Delete existing seed rows first")
    args = ap.parse_args()

    db_url = args.database_url.strip()
    if not db_url:
        _log.error("--database-url or DATABASE_URL env var required")
        return 1

    engine = create_engine(db_url)
    now = datetime.now(UTC).replace(tzinfo=None)
    start = now - timedelta(days=args.days)

    with engine.begin() as conn:
        if args.wipe:
            _log.info("wiping existing seed data for account %s", _ACCOUNT_ID)
            conn.execute(
                text(
                    "DELETE FROM close_events WHERE order_id IN"
                    " (SELECT order_id FROM orders WHERE account_id = :aid)"
                ),
                {"aid": _ACCOUNT_ID},
            )
            conn.execute(
                text("DELETE FROM positions WHERE account_id = :aid"), {"aid": _ACCOUNT_ID}
            )
            conn.execute(
                text("DELETE FROM order_transactions WHERE account_id = :aid"), {"aid": _ACCOUNT_ID}
            )
            conn.execute(text("DELETE FROM orders WHERE account_id = :aid"), {"aid": _ACCOUNT_ID})
            conn.execute(
                text("DELETE FROM market_candles WHERE instrument IN :insts"),
                {"insts": tuple(args.candle_instruments)},
            )

        _log.info("inserting broker/account/instruments...")
        _insert_broker(conn)
        _insert_account(conn)
        _insert_instruments(conn)

        _log.info("generating %d trades (%d days)...", args.trades, args.days)
        _generate_trades(conn, args.trades, start, now)

        for instrument in args.candle_instruments:
            base_price = _BASE_PRICES.get(instrument, 1.0)
            pip_size = 0.01 if instrument.endswith("_JPY") else 0.0001
            n_candles = args.candle_days * 1440
            candle_start = now - timedelta(days=args.candle_days)
            _log.info("generating %d M1 candles for %s...", n_candles, instrument)
            rows = _make_candles(instrument, candle_start, n_candles, base_price, pip_size)
            _insert_candles_batch(conn, rows)

    _log.info(
        "done — account=%s broker=%s trades=%d candle_days=%d",
        _ACCOUNT_ID,
        _BROKER_ID,
        args.trades,
        args.candle_days,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
