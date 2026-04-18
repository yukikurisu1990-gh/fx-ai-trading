"""Migration chain integrity tests.

Verifies that every revision file in migrations/versions/ can be imported
and that the revision chain is linear and unbroken (no gaps, no forks).

These tests are intentionally lightweight — they do not connect to a
database. Database-level up/down/up round-trip tests are tracked in
TODO(M2-test-roundtrip) and require a running PostgreSQL or SQLite
fixture; they will be added once the full 42-table schema is complete.

How to run:
    pytest tests/migration/test_migration_chain.py -v
"""

import importlib.util
from pathlib import Path

# Locate the versions directory relative to this file.
_VERSIONS_DIR = Path(__file__).resolve().parents[2] / "migrations" / "versions"

# Collect all revision files (files matching 0NNN_*.py, excluding __init__).
_REVISION_FILES = sorted(p for p in _VERSIONS_DIR.glob("0*.py") if p.name != "__init__.py")


def _load_revision(path: Path):
    """Import a migration revision file and return its module."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_at_least_one_revision_exists() -> None:
    """Sanity: the versions directory must contain at least one revision."""
    assert len(_REVISION_FILES) >= 1, "No revision files found in migrations/versions/"


def test_all_revisions_importable() -> None:
    """Every revision file must be importable without errors."""
    for path in _REVISION_FILES:
        mod = _load_revision(path)
        assert hasattr(mod, "revision"), f"{path.name}: missing 'revision'"
        assert hasattr(mod, "down_revision"), f"{path.name}: missing 'down_revision'"
        assert callable(getattr(mod, "upgrade", None)), f"{path.name}: upgrade() not callable"
        assert callable(getattr(mod, "downgrade", None)), f"{path.name}: downgrade() not callable"


def test_revision_chain_is_linear() -> None:
    """The down_revision links must form a single linear chain with no gaps."""
    mods = [_load_revision(p) for p in _REVISION_FILES]

    # Build lookup: revision_id -> module
    by_id = {m.revision: m for m in mods}

    # Find root (down_revision is None)
    roots = [m for m in mods if m.down_revision is None]
    assert len(roots) == 1, (
        f"Expected exactly 1 root revision, got {len(roots)}: {[r.revision for r in roots]}"
    )

    # Walk the chain from root and verify each link resolves
    visited = []
    current = roots[0]
    for _ in range(len(mods)):
        visited.append(current.revision)
        # Find the next revision that points to current
        children = [m for m in mods if m.down_revision == current.revision]
        if not children:
            break
        assert len(children) == 1, (
            f"Fork detected after {current.revision}: "
            f"multiple revisions point to it: {[c.revision for c in children]}"
        )
        current = children[0]

    assert len(visited) == len(mods), (
        f"Chain length mismatch: visited {len(visited)} of {len(mods)} revisions. "
        f"Unreachable: {set(by_id) - set(visited)}"
    )


def test_revision_ids_match_filenames() -> None:
    """Each file's 'revision' attribute must match the file stem prefix convention."""
    for path in _REVISION_FILES:
        mod = _load_revision(path)
        # Convention: filename stem equals revision id (e.g. 0001_group_a_reference)
        assert mod.revision == path.stem, (
            f"{path.name}: revision id '{mod.revision}' does not match filename stem '{path.stem}'"
        )
