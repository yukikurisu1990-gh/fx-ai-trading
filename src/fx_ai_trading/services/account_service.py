"""AccountService — thin wrapper around AccountsRepository.

Scope (M3 Cycle 12):
  - get_account(account_id) -> dict | None
  - list_accounts() -> list[dict]
  - create_account(...)
"""

from __future__ import annotations

from fx_ai_trading.repositories.accounts import AccountsRepository


class AccountService:
    """Provides account-level operations via AccountsRepository."""

    def __init__(self, repo: AccountsRepository) -> None:
        self._repo = repo

    def get_account(self, account_id: str) -> dict | None:
        """Return the account dict for *account_id*, or None."""
        return self._repo.get_by_account_id(account_id)

    def list_accounts(self) -> list[dict]:
        """Return all accounts ordered by account_id."""
        return self._repo.list_accounts()

    def create_account(
        self,
        account_id: str,
        broker_id: str,
        account_type: str,
        base_currency: str,
    ) -> None:
        """Insert a new account row."""
        self._repo.create_account(
            account_id=account_id,
            broker_id=broker_id,
            account_type=account_type,
            base_currency=base_currency,
        )
