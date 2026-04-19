"""Migration tests: 0011_app_settings_phase_mode_seed (M18 / Ob-PANEL-FALLBACK-1).

Verifies statically (no live DB):
  1. Revision file is importable with correct metadata.
  2. down_revision points to 0010_view_aliases (chain continuity).
  3. _NEW_VALUES contains both expected keys.
  4. introduced_in_version is "0.0.2" (separate from 0.0.1 seed).
  5. upgrade() and downgrade() are callable.
  6. phase_mode and runtime_environment keys are present (IP2-Q6 naming).
  7. "environment" (bare name) is NOT used (avoids Common Keys collision).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_VERSIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"
_REVISION_FILE = _VERSIONS_DIR / "0011_app_settings_phase_mode_seed.py"


def _load_revision():
    spec = importlib.util.spec_from_file_location(_REVISION_FILE.stem, _REVISION_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRevisionMetadata:
    def test_file_exists(self) -> None:
        assert _REVISION_FILE.exists(), "0011 migration file not found"

    def test_revision_id_correct(self) -> None:
        mod = _load_revision()
        assert mod.revision == "0011_app_settings_phase_mode_seed"

    def test_down_revision_links_to_0010(self) -> None:
        mod = _load_revision()
        assert mod.down_revision == "0010_view_aliases"

    def test_upgrade_callable(self) -> None:
        mod = _load_revision()
        assert callable(getattr(mod, "upgrade", None))

    def test_downgrade_callable(self) -> None:
        mod = _load_revision()
        assert callable(getattr(mod, "downgrade", None))


class TestSeedData:
    def test_introduced_in_version_is_002(self) -> None:
        mod = _load_revision()
        assert mod._INTRODUCED_IN == "0.0.2"

    def test_phase_mode_key_present(self) -> None:
        mod = _load_revision()
        names = [row[0] for row in mod._NEW_VALUES]
        assert "phase_mode" in names

    def test_runtime_environment_key_present(self) -> None:
        mod = _load_revision()
        names = [row[0] for row in mod._NEW_VALUES]
        assert "runtime_environment" in names

    def test_bare_environment_key_absent(self) -> None:
        """IP2-Q6: 'environment' must not appear — use 'runtime_environment' instead."""
        mod = _load_revision()
        names = [row[0] for row in mod._NEW_VALUES]
        assert "environment" not in names

    def test_exactly_two_new_keys(self) -> None:
        mod = _load_revision()
        assert len(mod._NEW_VALUES) == 2

    def test_phase_mode_default_value(self) -> None:
        mod = _load_revision()
        row = next(r for r in mod._NEW_VALUES if r[0] == "phase_mode")
        assert row[1] == "phase6"

    def test_runtime_environment_default_value(self) -> None:
        mod = _load_revision()
        row = next(r for r in mod._NEW_VALUES if r[0] == "runtime_environment")
        assert row[1] == "demo"
