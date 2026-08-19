"""Explicit opt-in authority for tests that reach outside the repository.

The governing principle, adopted after the 2026-08 process-boundary incident
recorded in ``docs/design/m15_targeted_fix_b1_b7_rf1_rf29_note.md`` §8:

    the presence of a resource is not authorization to use it

A ``.env`` file sitting on the machine, a populated ``DATABASE_URL``, a
directory full of research ``.jsonl`` files, or a broker credential must never
be enough on its own to make ``pytest`` touch them.  Each class of resource
needs a deliberate opt-in from the caller.

Where a configuration value is *also* required the two are checked separately,
so neither the opt-in alone nor the configuration alone can authorise a run —
that is the double gate the incident review asked for.  ``.env`` is never
auto-loaded during a test session (see ``tests/conftest.py``); a caller who
opts in supplies the environment explicitly.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"

# --- opt-in variable names ------------------------------------------------
# Naming follows the existing repository convention (``ML_STEP4_HEAVY_TESTS``):
# an upper-snake environment variable whose sole accepted value is "1".
DB_OPT_IN = "RUN_DB_INTEGRATION_TESTS"
RESEARCH_DATA_OPT_IN = "RUN_RESEARCH_DATA_TESTS"
EXTERNAL_OPT_IN = "RUN_EXTERNAL_TESTS"

ALL_OPT_INS: tuple[str, ...] = (DB_OPT_IN, RESEARCH_DATA_OPT_IN, EXTERNAL_OPT_IN)

# The one accepted value.  Anything else — "true", "yes", "0", "" — leaves the
# gate closed.  A typo must fail closed, never open.
_GRANTED = "1"

DB_URL_VAR = "DATABASE_URL"


def opt_in_granted(name: str) -> bool:
    """True only when *name* is set to exactly "1" (surrounding space ignored)."""
    return os.environ.get(name, "").strip() == _GRANTED


# --- database -------------------------------------------------------------


def db_configured() -> bool:
    """True when a database connection string is present in the environment."""
    return bool(os.environ.get(DB_URL_VAR, "").strip())


def db_tests_authorized() -> bool:
    """Both gates: a deliberate opt-in *and* a supplied connection string."""
    return opt_in_granted(DB_OPT_IN) and db_configured()


def db_skip_reason() -> str | None:
    """Why database tests are not running, or None when they are authorised."""
    if not opt_in_granted(DB_OPT_IN):
        return (
            f"database tests require {DB_OPT_IN}=1 — the presence of a .env or a "
            f"{DB_URL_VAR} is not authorization to use a database"
        )
    if not db_configured():
        return (
            f"{DB_OPT_IN}=1 was given but {DB_URL_VAR} is unset — refusing to guess "
            "a database; export it explicitly (tests never read .env)"
        )
    return None


def database_url() -> str:
    """The connection string, but only for an authorised caller.

    Raises:
        RuntimeError: if the double gate is not satisfied.  Tests should be
            decorated with :data:`requires_db` so this never fires.
    """
    reason = db_skip_reason()
    if reason is not None:
        raise RuntimeError(f"database access is not authorised in this test run: {reason}")
    return os.environ[DB_URL_VAR].strip()


# --- local research data --------------------------------------------------


def research_data_authorized() -> bool:
    """True when the caller deliberately opted in to reading local research data."""
    return opt_in_granted(RESEARCH_DATA_OPT_IN)


def research_path(*parts: str) -> Path | None:
    """Resolve a path under ``data/`` — but only for an authorised caller.

    Returns None both when the caller has not opted in and when the file is
    absent.  Without the opt-in *no filesystem probe happens at all*, so a
    default run cannot even discover which research files exist.
    """
    if not research_data_authorized():
        return None
    candidate = DATA_DIR.joinpath(*parts)
    return candidate if candidate.exists() else None


def has_research_data(*parts: str) -> bool:
    """True only when opted in *and* the named research file is present."""
    return research_path(*parts) is not None


def research_skip_reason() -> str:
    return (
        f"local research-data tests require {RESEARCH_DATA_OPT_IN}=1 — the presence of "
        "data/ files is not authorization to read them"
    )


# --- external systems (broker, object storage, network) -------------------


def external_tests_authorized() -> bool:
    """True when the caller deliberately opted in to reaching external systems."""
    return opt_in_granted(EXTERNAL_OPT_IN)


def external_skip_reason() -> str:
    return (
        f"tests that reach external systems require {EXTERNAL_OPT_IN}=1 — the presence "
        "of a credential is not authorization to use it"
    )


# --- ready-made marks -----------------------------------------------------
# Evaluated at import time, which is correct: the authorising environment is
# fixed for the whole session.

requires_db = pytest.mark.skipif(
    not db_tests_authorized(),
    reason=db_skip_reason() or "",
)

requires_research_data = pytest.mark.skipif(
    not research_data_authorized(),
    reason=research_skip_reason(),
)

requires_external = pytest.mark.skipif(
    not external_tests_authorized(),
    reason=external_skip_reason(),
)
