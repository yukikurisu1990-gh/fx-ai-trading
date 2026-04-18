"""AppSettingsRepository — read/write access to the app_settings table.

Scope (M3 Cycle 1):
  - get(name) -> str | None
  - set(name, value) -> None (upsert on updated_at only)

Common Keys (run_id / environment / code_version / config_version) are NOT
attached as physical columns yet — deferred to M5 when Repository base and
the corresponding migration are implemented together.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Engine, text


class AppSettingsRepository:
    """Read/write interface for the app_settings table."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def get(self, name: str) -> str | None:
        """Return the value for *name*, or None if not found."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT value FROM app_settings WHERE name = :name"),
                {"name": name},
            ).fetchone()
        return row[0] if row else None

    def set(self, name: str, value: str) -> None:
        """Upsert *value* for *name*, updating updated_at to now (UTC)."""
        now = datetime.now(UTC)
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE app_settings SET value = :value, updated_at = :now WHERE name = :name"
                ),
                {"name": name, "value": value, "now": now},
            )
