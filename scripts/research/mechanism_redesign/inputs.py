# ruff: noqa: E501 -- manifest prose
"""入力 data の manifest（pre-alpha review Role 1 R-1 / Role 2 RF-5）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

凍結 digest は manifest の sha256 を含み、driver は走る前に**すべての入力を manifest と照合する**。
対象: 外部 series の parquet（content hash）、FX panel と流動性 signal の元になる cache の file bytes。
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Final

import pandas as pd

from scripts.research.acquisition_safety import digest, write_provenance

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
#: v1（inputs_manifest.json）は rename の比較対象の入力を含んでいなかった（re-audit RF-B）。
MANIFEST: Final[Path] = REPO_ROOT / "artifacts/research/mechanism_redesign/inputs_manifest_v2.json"
EXTERNAL_DIR: Final[Path] = REPO_ROOT / "artifacts/track_a_scratch/mechanism_redesign"
FILE_GLOBS: Final[tuple[tuple[str, str], ...]] = (
    ("artifacts/track_a_scratch/momentum_replication_b", "m15_*.parquet"),
    ("artifacts/track_a_scratch/supplemental_replication", "m15_*.parquet"),
    ("artifacts/track_a_scratch/exploratory_round_1", "m15_*.parquet"),
    ("artifacts/track_a_scratch/valuation", "fx_*.parquet"),
    #: rename gate の比較対象（T5 の TIC、U1 の貿易収支）
    ("artifacts/track_a_scratch/top_five", "*.parquet"),
    ("artifacts/track_a_scratch/next_five", "*.parquet"),
)
RECORDS: Final[tuple[str, ...]] = (
    "artifacts/research/mechanism_redesign/acquisition.json",
    "artifacts/research/mechanism_redesign/acquisition_amendment.json",
)


def _file_sha(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            sha.update(block)
    return sha.hexdigest()


def build() -> dict[str, Any]:
    external = {
        path.stem: digest(pd.read_parquet(path).to_csv())
        for path in sorted(EXTERNAL_DIR.glob("*.parquet"))
    }
    files = {
        f"{directory}/{path.name}": _file_sha(path)
        for directory, pattern in FILE_GLOBS
        for path in sorted((REPO_ROOT / directory).glob(pattern))
    }
    records = {
        record: hashlib.sha256(
            (REPO_ROOT / record).read_bytes().replace(b"\r\n", b"\n")
        ).hexdigest()
        for record in RECORDS
    }
    return {
        "external_series_content_hash": external,
        "cache_file_sha256": files,
        "acquisition_records": records,
    }


def verify() -> None:
    import json

    expected = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual = build()
    for key in expected:
        if expected[key] != actual[key]:
            diff = sorted(set(expected[key].items()) ^ set(actual[key].items()))[:3]
            raise SystemExit(f"入力が manifest と違う（{key}）: {diff}。走らせない")


def main() -> int:
    written = write_provenance(MANIFEST, build())
    print(f"written {MANIFEST} {written}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
