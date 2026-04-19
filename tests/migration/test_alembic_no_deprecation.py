"""Alembic configuration must emit zero DeprecationWarning at load time.

Carryover Ob-ALEMBIC-1 / iteration2_implementation_plan.md §6.12 (M24).

The historical issue was alembic 1.18+ emitting:
    DeprecationWarning: No path_separator found in configuration; falling
    back to legacy splitting on spaces, commas, and colons for
    prepend_sys_path. Consider adding path_separator=os to Alembic config.

This test triggers the same code path that Alembic CLI runs and asserts
no DeprecationWarning surfaces. It is DB-free (no upgrade is performed),
so it runs in CI without DATABASE_URL.
"""

from __future__ import annotations

import warnings
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

_ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def test_alembic_config_loads_without_deprecation_warning() -> None:
    """Loading alembic.ini and resolving the script directory emits 0 DeprecationWarning."""
    cfg = Config(str(_ALEMBIC_INI))
    cfg.set_main_option("script_location", "migrations")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        # Trigger the prepend_sys_path resolution that historically warned.
        cfg.get_prepend_sys_paths_list()
        # Trigger ScriptDirectory.from_config() which is what `alembic upgrade`
        # calls first. Any deprecation in this code path must surface here.
        ScriptDirectory.from_config(cfg)

    deprecations = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert not deprecations, "Alembic emitted DeprecationWarning during config load: " + "; ".join(
        str(w.message) for w in deprecations
    )
