"""記録の provenance（事前登録 §13）。記録は上書きを拒否する。"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Final

import numpy as np
import scipy

REPO: Final[Path] = Path(__file__).resolve().parents[3]
PREREG: Final[Path] = REPO / "docs/research/fx_constraint_frontier_prereg_2026_10.md"


def git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} が失敗した")
    return done.stdout.strip()


def sha256_text(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def start(record: Path) -> dict[str, Any]:
    if record.exists():
        raise SystemExit(f"{record} は既にある。上書きしない")
    dirty = git("status", "--porcelain", "--", "scripts", "tests", "docs").splitlines()
    if dirty:
        raise SystemExit(f"dirty tree では走らせない: {dirty[:5]}")
    return {
        "head": git("rev-parse", "HEAD"),
        "dirty_path_count": 0,
        "prereg_sha256": sha256_text(PREREG),
        "prereg_commit": git("log", "-1", "--format=%H", "--", str(PREREG.relative_to(REPO))),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        },
    }


def finish(record: Path, payload: dict[str, Any]) -> str:
    payload["completed_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    raw = (json.dumps(payload, ensure_ascii=False, indent=1, default=float) + "\n").encode("utf-8")
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    print(digest)
    return digest
