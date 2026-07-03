"""provenance_guard — F5-C inventoried-span overwrite protection.

Status: F5_INVENTORIED_SPAN_OVERWRITE_GUARDED

Audit context (docs/design/project_wide_logic_audit_fable5_findings.md §4 F-5):
Gate P1 PR-B.1 and the Foundation T2 manifest reference local candle span
files by basename / ``logical_file_id`` together with SHA-256 checksums.
Re-fetching over one of those filenames silently re-points span identity at
different bytes while the committed SHA evidence still refers to the old
bytes.

This module provides a read-only guard over the committed inventory
metadata: callers pass an intended output path; if its basename is
referenced by any committed JSON metadata under the inventory roots, the
guard fails closed (``ProvenanceGuardError``) unless the operator passes an
explicit override (``allow_overwrite=True`` /
``--allow-overwrite-inventoried`` on the wired CLIs).

The guard only READS the committed metadata; it never modifies anything
under ``artifacts/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

#: Committed metadata roots that reference candidate span files by
#: logical_file_id / basename: Gate P1 PR-B inventories, Foundation T2
#: manifest, and the 2026-05-31 pre-downgrade OANDA archive manifest
#: (120 files across M1/M5/M15/H1/H4/D — only the 20 M1 basenames also
#: appear in the PR-B.1 inventory, so the archive manifest must be a
#: root of its own or 100 committed-SHA spans would be unprotected).
DEFAULT_INVENTORY_ROOTS: tuple[Path, ...] = (
    _REPO_ROOT / "artifacts" / "gate_p1_pr_b",
    _REPO_ROOT / "artifacts" / "foundation_t2",
    _REPO_ROOT / "artifacts" / "oanda_archive_2026-05-31",
)


class ProvenanceGuardError(RuntimeError):
    """Raised when an output path would overwrite an inventoried span file."""


def find_inventory_references(
    filename: str | Path,
    inventory_roots: list[Path] | tuple[Path, ...] | None = None,
) -> list[str]:
    """Return committed JSON metadata files that reference ``filename``.

    ``filename`` is reduced to its basename; every ``*.json`` file under the
    inventory roots is searched (read-only) for that basename as a
    substring.  Substring matching is intentionally conservative
    (fail-closed): metadata that mentions the basename in any field —
    ``filename``, ``logical_file_id``, free text — counts as a reference.
    """
    basename = Path(filename).name
    roots = DEFAULT_INVENTORY_ROOTS if inventory_roots is None else inventory_roots
    references: list[str] = []
    for root in roots:
        root = Path(root)
        if not root.is_dir():
            continue
        for meta_path in sorted(root.rglob("*.json")):
            try:
                text = meta_path.read_text(encoding="utf-8")
            except OSError:
                continue
            if basename in text:
                references.append(str(meta_path))
    return references


def assert_not_inventoried_span(
    output_path: str | Path,
    *,
    allow_overwrite: bool = False,
    inventory_roots: list[Path] | tuple[Path, ...] | None = None,
) -> list[str]:
    """Fail closed if ``output_path``'s basename is inventoried.

    Returns the (possibly empty) list of referencing metadata files when the
    write is permitted.  Raises :class:`ProvenanceGuardError` when the
    basename is referenced by committed inventory metadata and
    ``allow_overwrite`` is False.

    When the override IS used against a referenced basename, an explicit
    ``PROVENANCE_OVERRIDE`` warning is emitted to stderr — an overridden
    overwrite must never look like a normal provenance-clean run.  The
    override grants nothing beyond the write itself: no byte-admissibility,
    no new-epoch adoption, no ML Step 4 authorisation.
    """
    references = find_inventory_references(output_path, inventory_roots=inventory_roots)
    if references and allow_overwrite:
        print(
            f"PROVENANCE_OVERRIDE: overwriting inventoried span "
            f"{Path(output_path).name!r} referenced by {len(references)} "
            "committed metadata file(s); committed SHA-256 evidence still "
            "refers to the OLD bytes. This override does NOT confer "
            "byte-admissibility, new-epoch adoption, or ML Step 4 "
            "authorisation.",
            file=sys.stderr,
        )
    if references and not allow_overwrite:
        shown = "\n  ".join(references[:5])
        more = f"\n  ... and {len(references) - 5} more" if len(references) > 5 else ""
        raise ProvenanceGuardError(
            f"Refusing to write {Path(output_path).name!r}: this basename is "
            f"referenced by {len(references)} committed inventory metadata "
            f"file(s):\n  {shown}{more}\n"
            "Overwriting would re-point span identity at different bytes while "
            "committed SHA-256 evidence still refers to the old bytes. Use a "
            "new output path / dataset epoch, or pass an explicit override "
            "(--allow-overwrite-inventoried / allow_overwrite=True) if you "
            "really intend to replace the inventoried bytes."
        )
    return references
