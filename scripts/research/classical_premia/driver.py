# ruff: noqa: E501 -- driver prose
"""composite を **1 回だけ** 走らせる（裁定 §26）。2 段階に分ける（Role 2 R-2）。

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

1. `python -m scripts.research.classical_premia.driver start`
   ledger が `INTENT` 1 行だけ、INTENT を足した commit が HEAD で push 済み、tree が clean、凍結 digest が一致、
   空き容量が十分、なら `STARTED` を書いて**計算せずに終わる**。これを commit・push する。
2. `python -m scripts.research.classical_premia.driver compute [--workers N]`
   ledger が `INTENT, STARTED` の 2 行、STARTED を足した commit が HEAD で push 済み、tree が clean、
   記録が無い、なら計算する。生の結果・日次 series・月次 target を**判定の前に** atomic に書き
   （Role 2 R-4・N-6）、判定を足した記録を書いてから `COMPLETED` を書く。

例外は捕まえない。compute が落ちても push 済みの `STARTED` が残るので、再実行は Human + ChatGPT の判断になる。
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
import time
import warnings
from pathlib import Path
from typing import Any, Final

from scripts.research.classical_premia import data, execute, ledger, prereg

REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
OUT_DIR: Final[Path] = REPO_ROOT / "artifacts/research/classical_premia"
RECORD: Final[Path] = OUT_DIR / "execution.json"
RAW: Final[Path] = OUT_DIR / "execution_raw.json"
DAILY: Final[Path] = OUT_DIR / "execution_daily.parquet"
TARGETS: Final[Path] = OUT_DIR / "execution_monthly_targets.parquet"
#: compute の最初に書く印。計算の途中で落ちても「試みた」ことが残り、黙った再実行を止める（re-audit NEW-4）
ATTEMPT: Final[Path] = OUT_DIR / "execution_attempt.json"

FROZEN_DIGEST: Final[str] = "401b2b5c31f30444e7edac881a1a1391b323e8026e2ddc588b9805e06fb39f69"


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def _check_common(expected_kinds: list[str]) -> dict[str, Any]:
    for path in (RECORD, RAW, DAILY, TARGETS, ATTEMPT):
        if path.exists():
            raise SystemExit(f"{path} は既にある。1 回だけの実行なので走らせない")
    entries = ledger.read()
    ledger.verify(entries)
    kinds = [e["kind"] for e in entries]
    if kinds != expected_kinds:
        raise SystemExit(f"ledger が {kinds}、期待は {expected_kinds}。走らせない")
    digest = prereg.freeze_digest()
    if digest != FROZEN_DIGEST or any(e["freeze_digest"] != digest for e in entries):
        raise SystemExit(f"凍結 digest が違う（計算 {digest} / FROZEN {FROZEN_DIGEST}）")
    dirty = ledger.dirty_paths()
    if dirty:
        raise SystemExit(f"dirty tree では走らせない: {dirty[:5]}")
    head = ledger.head()
    touched = ledger.commit_that_last_touched(ledger.LEDGER)
    if touched != head:
        raise SystemExit(f"ledger の最後の行を足した commit（{touched}）が HEAD（{head}）ではない")
    if not ledger.is_pushed(head):
        raise SystemExit(f"HEAD（{head}）が push されていない")
    if ledger.free_bytes() < ledger.MIN_FREE_BYTES:
        raise SystemExit(f"空き容量が {ledger.free_bytes()} bytes しかない（5 GB 未満）")
    _assert_loaded_modules_in_closure()
    return {"freeze_digest": digest, "head": head, "dirty_path_count": 0, "entries": entries}


def _assert_loaded_modules_in_closure() -> None:
    """読み込まれた `scripts.*` の module が全て凍結の閉包に入っているか（Role 2 N-4）。"""
    closure = {str(REPO_ROOT / p).replace("\\", "/").lower() for p in prereg.code_closure()}
    outside = []
    for name, module in list(sys.modules.items()):
        if not name.startswith("scripts"):
            continue
        path = getattr(module, "__file__", None)
        if path and str(Path(path).resolve()).replace("\\", "/").lower() not in closure:
            outside.append(name)
    if outside:
        raise SystemExit(f"閉包の外の module が読み込まれている: {sorted(outside)[:5]}")


def start(*, workers: int) -> dict[str, Any]:
    state = _check_common(["INTENT"])
    return ledger.append(
        "STARTED",
        {
            "freeze_digest": state["freeze_digest"],
            "head_at_start": state["head"],
            "intent_sha256": state["entries"][0]["sha256"],
            "dirty_path_count": 0,
            "environment": ledger.environment(),
            "planned_workers": workers,
            "next": "この行を commit・push してから driver compute",
        },
    )


def _clean(value: Any) -> Any:
    """NaN / inf は None に（strict JSON のまま書く、re-audit NEW-7）。numpy の数は Python の数に。"""
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        try:
            value = value.item()
        except (TypeError, ValueError):
            return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _json_bytes(payload: Any) -> bytes:
    text = json.dumps(
        _clean(payload), ensure_ascii=False, indent=1, sort_keys=True, allow_nan=False
    )
    return (text + "\n").encode("utf-8")


def _parquet_bytes(frame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer)
    return buffer.getvalue()


def compute(*, workers: int) -> dict[str, Any]:
    state = _check_common(["INTENT", "STARTED"])
    started = state["entries"][1]
    identity = {
        "freeze_digest": state["freeze_digest"],
        "execution_head": state["head"],
        "started_entry_sha256": started["sha256"],
        "started_utc": started["utc"],
        "compute_started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": ledger.environment(),
        "workers": workers,
    }
    ledger.write_atomic(ATTEMPT, _json_bytes({"cycle": prereg.CYCLE, **identity}))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        inputs, scores, provenance = data.build()
        print(f"[{time.strftime('%H:%M:%S')}] composite 開始", file=sys.stderr, flush=True)
        raw, frame, targets = execute.compute(inputs, scores, workers=workers)
        print(f"[{time.strftime('%H:%M:%S')}] composite 終了", file=sys.stderr, flush=True)
    warning_summary: dict[str, int] = {}
    for item in caught:
        key = f"{item.category.__name__}: {str(item.message)[:80]}"
        warning_summary[key] = warning_summary.get(key, 0) + 1

    #: 判定の前に、生の結果と series を atomic に書く（判定で落ちても run の中身は残る）
    monthly = targets["composite"].add_prefix("composite_")
    for family in ("carry", "momentum"):
        monthly = monthly.join(targets[family].add_prefix(f"{family}_"))
    monthly = monthly.join(targets["capped"])
    hashes = {
        _rel(DAILY): ledger.write_atomic(DAILY, _parquet_bytes(frame)),
        _rel(TARGETS): ledger.write_atomic(TARGETS, _parquet_bytes(monthly)),
    }
    raw_payload = {
        "cycle": prereg.CYCLE,
        **identity,
        "panel": provenance,
        "raw": raw,
        "series_sha256": hashes,
        "warnings": warning_summary,
    }
    hashes[_rel(RAW)] = ledger.write_atomic(RAW, _json_bytes(raw_payload))

    judged = execute.judge(raw, frame)
    record = {
        "cycle": prereg.CYCLE,
        "qualifier": prereg.QUALIFIER,
        **identity,
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "panel": provenance,
        "result": {**raw, **judged},
        "artifact_sha256": hashes,
        "warnings": warning_summary,
    }
    record_sha = ledger.write_atomic(RECORD, _json_bytes(record))
    ledger.append(
        "COMPLETED",
        {"record": _rel(RECORD), "record_sha256": record_sha, "artifact_sha256": hashes},
    )
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("start", "compute"))
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    if args.phase == "start":
        print(json.dumps(start(workers=args.workers), ensure_ascii=False, indent=1))
        return 0
    record = compute(workers=args.workers)
    verdict = record["result"]["research_verdict"]
    print(
        json.dumps(
            {
                "status": verdict["status"],
                "caveats": verdict["caveats"],
                "disposition": record["result"]["disposition"]["preliminary"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
