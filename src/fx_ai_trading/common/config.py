"""Centralized application configuration.

Loads values from environment variables and (for local development) a `.env` file at
the project root. Secrets MUST NOT be hardcoded here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / ".env", override=False)


@dataclass(frozen=True)
class AppConfig:
    app_env: str
    log_level: str
    db_primary_url: str | None
    db_secondary_url: str | None


def load_config() -> AppConfig:
    return AppConfig(
        app_env=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        db_primary_url=os.getenv("DB_PRIMARY_URL"),
        db_secondary_url=os.getenv("DB_SECONDARY_URL"),
    )
