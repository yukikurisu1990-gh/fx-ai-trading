"""``seed_replay_account`` — idempotent one-shot account seeder for replay mode.

Why this exists
---------------
``run_paper_evaluation --replay`` lets operators run offline strategy
evaluations against recorded JSONL quote files without touching OANDA.
However, the ``accounts`` table carries a FK that ``orders.account_id``
references, so any account used in an evaluation must be pre-seeded.

Replay evaluations should use a **dedicated** account (e.g.
``acct-replay-eval``) with zero positions.  Using a shared paper account
that has accumulated historical positions causes the exit gate to call
``QuoteFeed.get_quote()`` once per open position per tick, exhausting
the finite replay dataset in the first few ticks.

This script inserts the replay account row if it does not already exist.
If the row is present, it exits cleanly with rc=0 — safe to run
repeatedly or from CI.

CLI
---
``python -m scripts.seed_replay_account``

Optional flags:
  ``--account-id``    Account id to seed.  Default: ``acct-replay-eval``.
  ``--broker-id``     Broker identifier string.  Default: ``paper``.
  ``--account-type``  Account type string.  Default: ``demo``.
  ``--base-currency`` ISO 4217 currency code.  Default: ``USD``.

Env
---
``DATABASE_URL`` — required.  Same source as all other paper-stack scripts.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Final

from sqlalchemy import create_engine, text

_LOG = logging.getLogger("scripts.seed_replay_account")

_ENV_DATABASE_URL: Final[str] = "DATABASE_URL"
_DEFAULT_ACCOUNT_ID: Final[str] = "acct-replay-eval"
_DEFAULT_BROKER_ID: Final[str] = "paper"
_DEFAULT_ACCOUNT_TYPE: Final[str] = "demo"
_DEFAULT_BASE_CURRENCY: Final[str] = "USD"


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="seed_replay_account",
        description="Idempotent seed of the replay evaluation account row.",
    )
    parser.add_argument("--account-id", default=_DEFAULT_ACCOUNT_ID)
    parser.add_argument("--broker-id", default=_DEFAULT_BROKER_ID)
    parser.add_argument("--account-type", default=_DEFAULT_ACCOUNT_TYPE)
    parser.add_argument("--base-currency", default=_DEFAULT_BASE_CURRENCY)
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    return parser.parse_args(argv)


def seed_account(
    *,
    engine: object,
    account_id: str,
    broker_id: str,
    account_type: str,
    base_currency: str,
) -> bool:
    """Insert account row if absent.  Returns True if a new row was inserted."""
    with engine.begin() as conn:  # type: ignore[attr-defined]
        existing = conn.execute(
            text("SELECT 1 FROM accounts WHERE account_id = :account_id"),
            {"account_id": account_id},
        ).fetchone()
        if existing is not None:
            return False
        conn.execute(
            text(
                "INSERT INTO accounts (account_id, broker_id, account_type, base_currency)"
                " VALUES (:account_id, :broker_id, :account_type, :base_currency)"
            ),
            {
                "account_id": account_id,
                "broker_id": broker_id,
                "account_type": account_type,
                "base_currency": base_currency,
            },
        )
        return True


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    url = (os.environ.get(_ENV_DATABASE_URL) or "").strip()
    if not url:
        _LOG.error("seed_replay_account: DATABASE_URL is not set")
        return 2

    engine = create_engine(url)
    inserted = seed_account(
        engine=engine,
        account_id=args.account_id,
        broker_id=args.broker_id,
        account_type=args.account_type,
        base_currency=args.base_currency,
    )
    if inserted:
        _LOG.info(
            "seed_replay_account: inserted account_id=%s (broker_id=%s, account_type=%s,"
            " base_currency=%s)",
            args.account_id,
            args.broker_id,
            args.account_type,
            args.base_currency,
        )
    else:
        _LOG.info("seed_replay_account: account_id=%s already exists — skipped", args.account_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
