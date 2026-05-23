"""F-6 row-set manifests — full + aligned split row-index persistence.

Stage 1 implementation: primitives only. Stage 2/3 will call these against
the actual R7-A-clean parent row-set and the windowed_input_valid mask
(when A0-broad β v2 is eventually authorised; not in scope for V2-expanded
itself, whose foundation uses the inherited 70/15/15 historical split).

The "aligned" suffix here refers to the V2-expanded F-2/F-3 foundation cells
that A0-broad will later compare against; for V2-expanded itself, the
aligned row-set is `R7-A-clean ∩ windowed_input_valid` per PR #355 §A.3.

Per amendment Stage 1 binding "Row-set policy":

  * full and aligned split row-index manifests required
  * identical formal comparison row-sets required unless the sentinel's
    declared axis explicitly changes row-set (S-2 Fix A, S-6 per-target NaN)
  * row-set mismatch = HALT
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


class RowSetManifestError(RuntimeError):
    """Raised on row-set manifest mismatch / missing parquet / hash drift."""


# ---------------------------------------------------------------------------
# Row-index manifest primitives
# ---------------------------------------------------------------------------


@dataclass
class RowIndexManifest:
    """Per-cell row-index manifest backed by a parquet shard.

    The parquet shard contains the integer row indices of the parent
    R7-A-clean row-set; the manifest JSON records the SHA-256 of the shard
    so that cross-cell row-set equality can be verified by hash comparison
    alone, without re-reading the parquet.
    """

    cell_id: str
    split: str  # "train" | "val" | "test"
    n_rows: int
    parquet_path: str  # project-relative
    parquet_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "v2-expanded-1.0",
            "cell_id": self.cell_id,
            "split": self.split,
            "n_rows": self.n_rows,
            "parquet_path": self.parquet_path,
            "parquet_sha256": self.parquet_sha256,
        }


def compute_indices_sha256(idx: np.ndarray) -> str:
    """SHA-256 of a uint64 row-index array (cross-platform; endian-stable)."""
    arr = np.asarray(idx, dtype=np.uint64)
    # Use the raw bytes in little-endian so the hash is reproducible across
    # platforms.
    return hashlib.sha256(arr.astype("<u8").tobytes()).hexdigest()


def persist_row_index_manifest(
    cell_id: str,
    split: str,
    indices: np.ndarray,
    parquet_out: Path,
    json_out: Path,
) -> RowIndexManifest:
    """Persist row-index parquet + JSON manifest for one cell + split.

    Uses pandas to write parquet (project's standard).
    """
    import pandas as pd  # local import; pandas is a project dep but heavy

    parquet_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame({"row_idx": np.asarray(indices, dtype=np.int64)})
    df.to_parquet(parquet_out, index=False)

    # Compute SHA over canonical bytes (the original index array, NOT the
    # parquet file bytes — parquet is not byte-stable across writers).
    sha = compute_indices_sha256(indices)
    manifest = RowIndexManifest(
        cell_id=cell_id,
        split=split,
        n_rows=int(len(indices)),
        parquet_path=str(parquet_out).replace("\\", "/"),
        parquet_sha256=sha,
    )
    json_out.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    return manifest


def load_row_index_manifest(json_path: Path) -> RowIndexManifest:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    return RowIndexManifest(
        cell_id=payload["cell_id"],
        split=payload["split"],
        n_rows=payload["n_rows"],
        parquet_path=payload["parquet_path"],
        parquet_sha256=payload["parquet_sha256"],
    )


# ---------------------------------------------------------------------------
# Cross-cell row-set equality
# ---------------------------------------------------------------------------


def assert_row_sets_equal(
    manifest_a: RowIndexManifest,
    manifest_b: RowIndexManifest,
    *,
    label: str = "",
) -> None:
    """HALT if two manifests should share a row-set but their SHAs differ.

    For declared-axis exceptions (S-2 Fix A row isolation, S-6 per-target
    NaN propagation), the caller MUST NOT invoke this primitive; instead
    the caller asserts the *declared* row-count delta separately.
    """
    if manifest_a.split != manifest_b.split:
        raise RowSetManifestError(
            f"row-set comparison split mismatch: {manifest_a.split!r} vs "
            f"{manifest_b.split!r} (label={label!r})"
        )
    if manifest_a.parquet_sha256 != manifest_b.parquet_sha256:
        raise RowSetManifestError(
            f"row-set parquet SHA mismatch ({label!r}): "
            f"{manifest_a.cell_id}/{manifest_a.split} sha={manifest_a.parquet_sha256[:12]} "
            f"vs {manifest_b.cell_id}/{manifest_b.split} sha={manifest_b.parquet_sha256[:12]}"
        )
    if manifest_a.n_rows != manifest_b.n_rows:
        raise RowSetManifestError(
            f"row-set row-count mismatch ({label!r}): "
            f"{manifest_a.cell_id}/{manifest_a.split} n={manifest_a.n_rows} "
            f"vs {manifest_b.cell_id}/{manifest_b.split} n={manifest_b.n_rows}"
        )


def compute_row_set_manifest_hash(manifests: list[RowIndexManifest]) -> str:
    """Hash a collection of manifests for the orchestrator's manifest registry.

    Sorted by (cell_id, split) so the hash is deterministic regardless of
    insertion order.
    """
    payload = sorted(
        ((m.cell_id, m.split, m.parquet_sha256, m.n_rows) for m in manifests),
    )
    return hashlib.sha256(json.dumps(payload).encode("utf-8")).hexdigest()
