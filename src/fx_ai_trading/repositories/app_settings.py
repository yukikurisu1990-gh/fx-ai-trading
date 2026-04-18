"""AppSettingsRepository — read/write access to the app_settings table.

Scope (M3 Cycle 1):
  - get(name) -> str | None
  - set(name, value) -> None (upsert on updated_at only)

Scope (M3 Cycle 6):
  - Extends RepositoryBase (engine holder, Common Keys no-op hook)

Common Keys (run_id / environment / code_version / config_version) are NOT
attached as physical columns yet — deferred to M5 when Repository base and
the corresponding migration are implemented together.
"""

from __future__ import annotations

from sqlalchemy import text

from fx_ai_trading.repositories.base import RepositoryBase


class AppSettingsRepository(RepositoryBase):
    """Read/write interface for the app_settings table."""

    def get(self, name: str) -> str | None:
        """Return the value for *name*, or None if not found."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT value FROM app_settings WHERE name = :name"),
                {"name": name},
            ).fetchone()
        return row[0] if row else None

    def set(self, name: str, value: str) -> None:
        """Upsert *value* for *name*, updating updated_at via DB NOW().

        updated_at is set by the database (NOW()) to avoid datetime.now()
        which is forbidden by custom lint — Clock interface is M3+ scope.
        """
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE app_settings SET value = :value, updated_at = NOW() WHERE name = :name"
                ),
                {"name": name, "value": value},
            )
