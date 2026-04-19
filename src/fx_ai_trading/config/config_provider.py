"""ConfigProvider — reads app_settings and computes config_version.

Scope (M3 Cycle 4):
  - get(name) — thin wrapper around AppSettingsRepository.get
  - compute_version() — assembles the five canonical elements and delegates
    to compute_config_version()

Secret refs (element 5) are not yet wired — SecretProvider is M6+ scope.
Default catalog (element 4) is empty for now; values will be added as the
codebase defines explicit fallback constants.
"""

from __future__ import annotations

import os
from pathlib import Path

from fx_ai_trading.config.config_version import compute_config_version
from fx_ai_trading.repositories.app_settings import AppSettingsRepository


class ConfigProvider:
    """Provides typed read access to app_settings and config_version."""

    # Fields selected per phase6_hardening §6.19 element 1.
    _SETTINGS_FIELDS = ("name", "value", "type", "introduced_in_version")

    def __init__(
        self,
        repo: AppSettingsRepository,
        env_file_path: Path | None = None,
        default_catalog: dict[str, str] | None = None,
    ) -> None:
        self._repo = repo
        self._env_file_path = env_file_path
        self._default_catalog: dict[str, str] = default_catalog or {}

    def get(self, name: str) -> str | None:
        """Return the value for *name* from app_settings, or None."""
        return self._repo.get(name)

    def get_env_secret(self, key: str) -> str | None:
        """Return os.environ.get(key) without logging the value (M13b).

        Use for secrets that live in environment variables rather than
        app_settings — e.g. OANDA_ACCOUNT_TYPE for live gate verification.
        The value is never logged or stored; callers must not log it either.
        """
        return os.environ.get(key)

    def compute_version(self) -> str:
        """Return SHA256[:16] of the effective configuration.

        Reads all app_settings rows from the DB, collects APP_/FX_ env vars,
        parses the .env file if present, and calls compute_config_version().
        Secret refs are empty until SecretProvider is implemented (M6+).
        """
        app_settings_rows = self._load_app_settings_rows()
        env_vars = self._collect_env_vars()
        env_file_entries = self._parse_env_file()
        return compute_config_version(
            app_settings_rows=app_settings_rows,
            env_vars=env_vars,
            env_file_entries=env_file_entries,
            default_catalog=self._default_catalog,
            secret_refs={},
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_app_settings_rows(self) -> list[dict[str, str]]:
        from sqlalchemy import text

        rows: list[dict[str, str]] = []
        with self._repo._engine.connect() as conn:
            result = conn.execute(
                text(
                    "SELECT name, value, type, introduced_in_version"
                    " FROM app_settings ORDER BY name ASC"
                )
            )
            for row in result:
                rows.append(dict(zip(self._SETTINGS_FIELDS, row, strict=True)))
        return rows

    def _collect_env_vars(self) -> dict[str, str]:
        return {
            k: v
            for k, v in sorted(os.environ.items())
            if k.startswith("APP_") or k.startswith("FX_")
        }

    def _parse_env_file(self) -> dict[str, str]:
        if self._env_file_path is None or not self._env_file_path.exists():
            return {}
        entries: dict[str, str] = {}
        for line in self._env_file_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" in stripped:
                key, _, value = stripped.partition("=")
                entries[key.strip()] = value.strip()
        return dict(sorted(entries.items()))
