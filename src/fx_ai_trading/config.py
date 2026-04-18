"""Application configuration — environment variable resolution.

Loads .env from the project root (if present) then exposes typed accessors.
Raises RuntimeError at import time if a required variable is absent, so
misconfiguration fails loudly before any DB connection is attempted.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the repository root (two levels above this file).
_env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_env_path, override=False)


def get_database_url() -> str:
    """Return DATABASE_URL from the environment.

    Raises:
        RuntimeError: if DATABASE_URL is not set.
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Copy .env.example to .env and fill in the connection string."
        )
    return url
