"""Migration tests: 0012_dashboard_top_candidates_table (M20).

Verifies statically (no live DB):
  1. Revision file is importable with correct metadata.
  2. down_revision points to 0011 (chain continuity).
  3. upgrade() and downgrade() are callable.
  4. revision ID matches filename.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_VERSIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"
_REVISION_FILE = _VERSIONS_DIR / "0012_dashboard_top_candidates_table.py"


def _load_revision():
    spec = importlib.util.spec_from_file_location(_REVISION_FILE.stem, _REVISION_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestRevisionMetadata:
    def test_file_exists(self) -> None:
        assert _REVISION_FILE.exists(), "0012 migration file not found"

    def test_revision_id_correct(self) -> None:
        mod = _load_revision()
        assert mod.revision == "0012_dashboard_top_candidates_table"

    def test_down_revision_links_to_0011(self) -> None:
        mod = _load_revision()
        assert mod.down_revision == "0011_app_settings_phase_mode_seed"

    def test_upgrade_callable(self) -> None:
        mod = _load_revision()
        assert callable(getattr(mod, "upgrade", None))

    def test_downgrade_callable(self) -> None:
        mod = _load_revision()
        assert callable(getattr(mod, "downgrade", None))
