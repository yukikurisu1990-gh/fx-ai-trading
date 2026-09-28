# ruff: noqa: E501 -- ledger prose
"""**append-only の実行 ledger**（裁定 §25）。「1 回だけ走らせた」を後から状況証拠で主張しないための記録。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

JSON Lines。各行は `prev_sha256`（直前の行の `sha256`）と、自分自身の `sha256`（`sha256` を除いた
正規化 JSON の hash）を持つ hash chain で、途中の行を書き換えると以降の全行の検証が落ちる。

行の種類は順に 1 回ずつ:

1. `INTENT` — alpha の前。commit・push する。
2. `STARTED` — `driver start` が書く。commit・push してから `driver compute` が計算する。
3. `COMPLETED` — 記録の後。

INTENT と STARTED はどちらも計算の前に remote に残るので、失敗した run を local の file を消して
黙ってやり直すことはできない（Role 2 R-2）。git の失敗は例外にする（fail-closed、Role 2 R-3）。
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Final

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
LEDGER: Final[Path] = REPO_ROOT / "artifacts/research/classical_premia/execution_ledger.jsonl"
ORDER: Final[tuple[str, ...]] = ("INTENT", "STARTED", "COMPLETED")
GENESIS: Final[str] = "0" * 64
SHA: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{40}$")
MIN_FREE_BYTES: Final[int] = 5 * 1024**3


def _canonical(entry: dict[str, Any]) -> bytes:
    body = {k: v for k, v in entry.items() if k != "sha256"}
    return json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")


def read(path: Path = LEDGER) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def verify(entries: list[dict[str, Any]]) -> None:
    """hash chain と行の順序を確かめる。壊れていれば例外。"""
    previous = GENESIS
    for i, entry in enumerate(entries):
        if i >= len(ORDER):
            raise ValueError(f"行 {i}: {len(ORDER)} 行より多い")
        if entry.get("seq") != i:
            raise ValueError(f"行 {i}: seq が {entry.get('seq')}")
        if entry.get("kind") != ORDER[i]:
            raise ValueError(f"行 {i}: kind が {entry.get('kind')}（期待 {ORDER[i]}）")
        if entry.get("prev_sha256") != previous:
            raise ValueError(f"行 {i}: prev_sha256 が直前の行と繋がらない")
        if hashlib.sha256(_canonical(entry)).hexdigest() != entry.get("sha256"):
            raise ValueError(f"行 {i}: 自分の sha256 と中身が合わない（書き換え）")
        previous = entry["sha256"]


def append(kind: str, payload: dict[str, Any], path: Path = LEDGER) -> dict[str, Any]:
    entries = read(path)
    verify(entries)
    if len(entries) >= len(ORDER) or ORDER[len(entries)] != kind:
        expected = ORDER[len(entries)] if len(entries) < len(ORDER) else "無し"
        raise ValueError(f"次に書ける行は {expected}、{kind} ではない")
    entry = {
        "seq": len(entries),
        "kind": kind,
        "prev_sha256": entries[-1]["sha256"] if entries else GENESIS,
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **payload,
    }
    entry["sha256"] = hashlib.sha256(_canonical(entry)).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    #: 1 行を 1 回の write で書き、flush・fsync してから検証する（半端な行を残さない、Role 2 B-1）
    line = (json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    with path.open("ab") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    verify(read(path))
    return entry


def write_atomic(path: Path, data: bytes) -> str:
    """temp file に書いて fsync し、`os.replace` で置く。既存の file は上書きしない。戻り値は sha256。"""
    if path.exists():
        raise SystemExit(f"{path} は既にある。上書きしない")
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".partial")
    with temp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)
    return hashlib.sha256(data).hexdigest()


# ----------------------------------------------------------------------
# git と環境（どれも失敗は例外）
# ----------------------------------------------------------------------
def git(*args: str) -> str:
    done = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        raise SystemExit(
            f"git {' '.join(args)} が失敗した（{done.returncode}）: {done.stderr.strip()[:200]}"
        )
    return done.stdout.strip()


def sha(*args: str) -> str:
    value = git(*args)
    if not SHA.match(value):
        raise SystemExit(f"git {' '.join(args)} が commit SHA を返さない: {value!r}")
    return value


def head() -> str:
    return sha("rev-parse", "HEAD")


def commit_that_last_touched(path: Path) -> str:
    return sha(
        "log", "-1", "--format=%H", "--", str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    )


def is_pushed(commit: str) -> bool:
    """commit がどこかの remote branch に含まれるか（push 済みか）。"""
    return bool(git("branch", "-r", "--contains", commit).strip())


def dirty_paths() -> list[str]:
    return git(
        "status", "--porcelain", "--", "scripts", "tests", "artifacts/research/classical_premia"
    ).splitlines()


def free_bytes() -> int:
    return shutil.disk_usage(REPO_ROOT).free


def environment() -> dict[str, str]:
    import numpy
    import pandas

    return {
        "python": sys.version.split()[0],
        "numpy": numpy.__version__,
        "pandas": pandas.__version__,
    }


def write_intent() -> dict[str, Any]:
    """INTENT を書く（alpha の前）。この後に commit・push してから `driver start`。"""
    from scripts.research.classical_premia import driver, prereg

    digest = prereg.freeze_digest()
    if digest != driver.FROZEN_DIGEST:
        raise SystemExit(
            f"driver.FROZEN_DIGEST が凍結 digest と違う（{driver.FROZEN_DIGEST} != {digest}）"
        )
    dirty = dirty_paths()
    if dirty:
        raise SystemExit(f"dirty tree では INTENT を書かない: {dirty[:5]}")
    if read():
        raise SystemExit("ledger は既に行を持つ。INTENT は最初の 1 行だけ")
    parent = head()
    if not is_pushed(parent):
        raise SystemExit(f"FROZEN_DIGEST を入れた commit（{parent}）が push されていない")
    return append(
        "INTENT",
        {
            "cycle": prereg.CYCLE,
            "freeze_digest": digest,
            "parent_head": parent,
            "dirty_path_count": len(dirty),
            "execution": "driver start → commit・push → driver compute を 1 回だけ。primary は composite。結果確認後の再実行はしない",
        },
    )


if __name__ == "__main__":
    if sys.argv[1:] != ["intent"]:
        raise SystemExit("usage: python -m scripts.research.classical_premia.ledger intent")
    print(json.dumps(write_intent(), ensure_ascii=False, indent=1))
