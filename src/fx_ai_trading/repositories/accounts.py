"""AccountsRepository — read/write access to the accounts table.

Scope (M3 Cycle 7):
  - get_by_account_id(account_id) -> dict | None
  - list_accounts() -> list[dict]

Scope (M3 Cycle 8):
  - create_account(account_id, broker_id, account_type, base_currency)
  - update_account(account_id, **fields)

Common Keys physical columns are M5 scope.
"""

from __future__ import annotations

from sqlalchemy import text

from fx_ai_trading.repositories.base import RepositoryBase

_COLUMNS = ("account_id", "broker_id", "account_type", "base_currency", "created_at", "updated_at")


class AccountsRepository(RepositoryBase):
    """Read/write interface for the accounts table."""

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

    def create_account(
        self,
        account_id: str,
        broker_id: str,
        account_type: str,
        base_currency: str,
    ) -> None:
        """Insert a new account row."""
        with self._engine.begin() as conn:
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

    def update_account(self, account_id: str, **fields: str) -> None:
        """Update mutable fields on an existing account row.

        Only ``account_type`` and ``base_currency`` are accepted.
        ``updated_at`` is refreshed via DB NOW() to avoid datetime.now().
        """
        allowed = {"account_type", "base_currency"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = :{k}" for k in sorted(updates))
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    f"UPDATE accounts SET {set_clause}, updated_at = NOW()"
                    " WHERE account_id = :account_id"
                ),
                {**updates, "account_id": account_id},
            )
