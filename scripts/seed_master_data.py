"""Seed required master-data tables after a DB reset.

Idempotent (ON CONFLICT DO NOTHING) — safe to run at any time.
Does NOT touch trading data (orders, positions, candles, etc.).

Tables seeded:
  brokers     — oanda, paper
  instruments — 20 LGBM-trained pairs

Usage:
    python scripts/seed_master_data.py
    python scripts/seed_master_data.py --database-url postgresql://...
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

_BROKERS = [
    {"broker_id": "oanda", "name": "OANDA", "api_base_url": "https://api-fxtrade.oanda.com"},
    {"broker_id": "paper", "name": "Paper", "api_base_url": ""},
]

_INSTRUMENTS = [
    "AUD_CAD", "AUD_JPY", "AUD_NZD", "AUD_USD",
    "CHF_JPY",
    "EUR_AUD", "EUR_CAD", "EUR_CHF", "EUR_GBP", "EUR_JPY", "EUR_USD",
    "GBP_AUD", "GBP_CHF", "GBP_JPY", "GBP_USD",
    "NZD_JPY", "NZD_USD",
    "USD_CAD", "USD_CHF", "USD_JPY",
]

_JPY_PAIRS = {
    "AUD_JPY", "CHF_JPY", "EUR_JPY", "GBP_JPY", "NZD_JPY", "USD_JPY",
}


def _seed(engine, *, verbose: bool = True) -> None:
    now = datetime.now(UTC)

    def log(msg: str) -> None:
        if verbose:
            print(msg)

    with engine.begin() as conn:
        # brokers
        inserted = 0
        for b in _BROKERS:
            result = conn.execute(
                text("""
                    INSERT INTO brokers (broker_id, name, api_base_url, created_at, updated_at)
                    VALUES (:broker_id, :name, :api_base_url, :now, :now)
                    ON CONFLICT (broker_id) DO NOTHING
                """),
                {**b, "now": now},
            )
            inserted += result.rowcount
        log(f"brokers:     {inserted} inserted, {len(_BROKERS) - inserted} already existed")

        # instruments
        inserted = 0
        for pair in _INSTRUMENTS:
            base, quote = pair.split("_")
            pip_location = -2 if pair in _JPY_PAIRS else -4
            result = conn.execute(
                text("""
                    INSERT INTO instruments
                        (instrument, base_currency, quote_currency,
                         pip_location, min_trade_units, created_at, updated_at)
                    VALUES
                        (:instrument, :base, :quote,
                         :pip_location, 1, :now, :now)
                    ON CONFLICT (instrument) DO NOTHING
                """),
                {
                    "instrument": pair,
                    "base": base,
                    "quote": quote,
                    "pip_location": pip_location,
                    "now": now,
                },
            )
            inserted += result.rowcount
        log(f"instruments: {inserted} inserted, {len(_INSTRUMENTS) - inserted} already existed")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", ""),
        help="PostgreSQL connection string (defaults to DATABASE_URL env var)",
    )
    args = parser.parse_args(argv)

    url = args.database_url.strip()
    if not url:
        sys.exit(
            "seed_master_data: DATABASE_URL is not set.\n"
            "Pass --database-url or set the DATABASE_URL environment variable."
        )

    engine = create_engine(url)
    _seed(engine)
    engine.dispose()
    print("Done.")


if __name__ == "__main__":
    main()
