"""AccountsRepository — read access to the accounts table.

Scope (M3 Cycle 7):
  - get_by_account_id(account_id) -> dict | None
  - list_accounts() -> list[dict]

Write operations (create / update) are M3 Cycle 8 scope.
Common Keys physical columns are M5 scope.
"""

from __future__ import annotations

from sqlalchemy import text

from fx_ai_trading.repositories.base import RepositoryBase

_COLUMNS = ("account_id", "broker_id", "account_type", "base_currency", "created_at", "updated_at")


class AccountsRepository(RepositoryBase):
    """Read interface for the accounts table."""

    def get_by_account_id(self, account_id: str) -> dict | None:
        """Return the account row for *account_id*, or None if not found."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT account_id, broker_id, account_type, base_currency,"
                    " created_at, updated_at"
                    " FROM accounts WHERE account_id = :account_id"
                ),
                {"account_id": account_id},
            ).fetchone()
        if row is None:
            return None
        return dict(zip(_COLUMNS, row, strict=True))

    def list_accounts(self) -> list[dict]:
        """Return all account rows ordered by account_id ascending."""
        with self._engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT account_id, broker_id, account_type, base_currency,"
                    " created_at, updated_at"
                    " FROM accounts ORDER BY account_id ASC"
                )
            )
            return [dict(zip(_COLUMNS, row, strict=True)) for row in result]
