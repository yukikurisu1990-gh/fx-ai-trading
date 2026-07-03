"""Emergency 10-year archive fetch for PAIRS_20 × {M1,M5,M15,H1,H4,D}.

Triggered by impending OANDA tier downgrade. One-shot bulk fetcher driven
by `fetch_candles()` from `fetch_oanda_candles.py`. Each (pair × granularity)
job is resume-safe via a sidecar completion marker
`<output>.complete.json` written after a fully-successful fetch.

Fail-closed resume semantics (F5-D; status
F5_INGESTION_PROVENANCE_HARDENED_BY_TESTS /
F5_INVENTORIED_SPAN_OVERWRITE_GUARDED):

- A job is skipped ONLY if its marker exists, parses, has
  ``completed == true`` and ``size_bytes`` matching the file's current
  size.  A non-empty file WITHOUT a valid marker is treated as incomplete
  (the pre-hardening rule skipped any non-empty file, so truncations were
  never repaired on resume).
- Before re-fetching over existing-but-unmarked bytes whose basename is
  referenced by committed inventory metadata (Gate P1 PR-B / Foundation
  T2), the job FAILS CLOSED instead of silently re-pointing span identity
  at new bytes.
- `fetch_candles()` itself writes to ``<output>.incomplete`` and promotes
  atomically only on success, so a failed re-fetch never destroys the
  existing final file.

Naming: matches existing local convention `candles_<PAIR>_<GRAN>_<days>d_BA.jsonl`.
Price mode: BA (bid + ask OHLC), matching all existing `_BA.jsonl` files
under `data/`.

Outputs:
- raw JSONL files: `data/candles_<PAIR>_<GRAN>_3650d_BA.jsonl`
- progress log:    `artifacts/oanda_archive_2026-05-31/fetch_log.jsonl`
- final manifest:  `artifacts/oanda_archive_2026-05-31/candles_manifest.json`
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from fetch_oanda_candles import fetch_candles  # noqa: E402
from provenance_guard import find_inventory_references  # noqa: E402

from fx_ai_trading.adapters.broker.oanda_api_client import OandaAPIClient  # noqa: E402

PAIRS_20 = [
    "EUR_USD",
    "GBP_USD",
    "AUD_USD",
    "NZD_USD",
    "USD_CHF",
    "USD_CAD",
    "EUR_GBP",
    "USD_JPY",
    "EUR_JPY",
    "GBP_JPY",
    "AUD_JPY",
    "NZD_JPY",
    "CHF_JPY",
    "EUR_CHF",
    "EUR_AUD",
    "EUR_CAD",
    "AUD_NZD",
    "AUD_CAD",
    "GBP_AUD",
    "GBP_CHF",
]

GRANULARITIES = ["M1", "M5", "M15", "H1", "H4", "D"]
DAYS = 3650  # 10 years
PRICE = "BA"
PAGE_SIZE = 5000

DATA_DIR = REPO_ROOT / "data"
ARCHIVE_DIR = REPO_ROOT / "artifacts" / "oanda_archive_2026-05-31"
LOG_PATH = ARCHIVE_DIR / "fetch_log.jsonl"
MANIFEST_PATH = ARCHIVE_DIR / "candles_manifest.json"


def _output_path(pair: str, granularity: str) -> Path:
    return DATA_DIR / f"candles_{pair}_{granularity}_3650d_BA.jsonl"


def _completion_marker_path(out: Path) -> Path:
    return out.with_name(out.name + ".complete.json")


def _write_completion_marker(out: Path, rows_written: int) -> Path:
    """Record a fully-successful fetch (F5-D resume evidence)."""
    marker = _completion_marker_path(out)
    marker.write_text(
        json.dumps(
            {
                "rows_written": rows_written,
                "size_bytes": out.stat().st_size,
                "completed": True,
            }
        ),
        encoding="utf-8",
    )
    return marker


def _is_marked_complete(out: Path) -> bool:
    """True only if the sidecar marker exists, parses, has completed==true,
    and its recorded size_bytes matches the file's current size."""
    marker = _completion_marker_path(out)
    if not out.exists() or not marker.exists():
        return False
    try:
        meta = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not isinstance(meta, dict):
        return False
    return meta.get("completed") is True and meta.get("size_bytes") == out.stat().st_size


def _resume_decision(out: Path, *, inventory_roots: list[Path] | None = None) -> tuple[str, dict]:
    """F5-D resume policy for one output file.

    Returns ``(action, info)`` where action is one of:

    - ``"skip"``    — valid completion marker matches the file's size.
    - ``"blocked"`` — the basename is referenced by committed inventory
      metadata and no valid marker exists: fail closed rather than re-point
      span identity at new bytes.  This applies even when the local file is
      missing — recreating an inventoried span with post-downgrade bytes is
      the same identity re-point.  There is deliberately no override flag
      here: the archived pre-downgrade bytes are unreproducible, so any
      legitimate re-fetch belongs to a new epoch/output path.
    - ``"fetch"``   — (re-)fetch via the atomic ``.incomplete`` path.
    """
    if _is_marked_complete(out):
        return "skip", {"size_bytes": out.stat().st_size}
    refs = find_inventory_references(out.name, inventory_roots=inventory_roots)
    if refs:
        return "blocked", {"inventory_references": refs}
    return "fetch", {}


def _log(event: dict) -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    event = {"ts_utc": datetime.now(UTC).isoformat(), **event}
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")
    print(json.dumps(event), flush=True)


def _sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(8 * 1024 * 1024)
            if not chunk:
                break
            n += len(chunk)
            h.update(chunk)
    return h.hexdigest(), n


def _file_summary(path: Path) -> dict:
    sha, size = _sha256_file(path)
    row_count = 0
    first_ts = None
    last_ts = None
    with path.open("rb") as fh:
        for line in fh:
            if not line.strip():
                continue
            row_count += 1
            try:
                rec = json.loads(line)
                t = rec.get("time")
                if t:
                    if first_ts is None:
                        first_ts = t
                    last_ts = t
            except Exception:
                continue
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "size_bytes": size,
        "sha256": sha,
        "row_count": row_count,
        "first_time": first_ts,
        "last_time": last_ts,
    }


def main() -> int:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    token = (os.environ.get("OANDA_ACCESS_TOKEN") or "").strip()
    env = (os.environ.get("OANDA_ENVIRONMENT") or "practice").strip()
    if not token:
        print("ERROR: OANDA_ACCESS_TOKEN missing", file=sys.stderr)
        return 1
    api = OandaAPIClient(access_token=token, environment=env)

    jobs = [(p, g) for p in PAIRS_20 for g in GRANULARITIES]
    n_total = len(jobs)
    _log({"event": "start", "n_jobs": n_total, "days": DAYS, "price": PRICE, "env": env})

    skipped: list[dict] = []
    completed: list[dict] = []
    failed: list[dict] = []
    t0 = time.time()

    for i, (pair, gran) in enumerate(jobs, 1):
        out = _output_path(pair, gran)
        rec = {
            "job": i,
            "n_total": n_total,
            "pair": pair,
            "granularity": gran,
            "output": str(out.relative_to(REPO_ROOT)),
        }

        action, info = _resume_decision(out)
        if action == "skip":
            _log({**rec, "event": "skip_complete_marker", **info})
            skipped.append(rec)
            continue
        if action == "blocked":
            _log(
                {
                    **rec,
                    "event": "resume_blocked_inventoried",
                    "error": (
                        "existing bytes lack a valid completion marker and the "
                        "basename is referenced by committed inventory metadata; "
                        "failing closed (use a new output path / dataset epoch)"
                    ),
                    **info,
                }
            )
            failed.append({**rec, "error": "resume_blocked_inventoried", **info})
            continue

        _log({**rec, "event": "fetch_begin"})
        t_job = time.time()
        try:
            written = fetch_candles(
                instrument=pair,
                granularity=gran,
                days=DAYS,
                output_path=out,
                price=PRICE,
                page_size=PAGE_SIZE,
                api_client=api,
            )
            _write_completion_marker(out, written)
            elapsed = time.time() - t_job
            _log(
                {**rec, "event": "fetch_done", "written": written, "elapsed_sec": round(elapsed, 1)}
            )
            completed.append({**rec, "written": written, "elapsed_sec": round(elapsed, 1)})
        except Exception as exc:
            elapsed = time.time() - t_job
            _log(
                {
                    **rec,
                    "event": "fetch_failed",
                    "error": str(exc),
                    "elapsed_sec": round(elapsed, 1),
                }
            )
            failed.append({**rec, "error": str(exc), "elapsed_sec": round(elapsed, 1)})

    _log(
        {
            "event": "fetch_phase_done",
            "skipped": len(skipped),
            "completed": len(completed),
            "failed": len(failed),
        }
    )

    print("\n=== Building manifest ===", flush=True)
    manifest_files: list[dict] = []
    for pair, gran in jobs:
        out = _output_path(pair, gran)
        if not out.exists():
            continue
        try:
            summary = _file_summary(out)
            summary.update({"pair": pair, "granularity": gran, "days": DAYS, "price": PRICE})
            manifest_files.append(summary)
            print(
                f"  {pair} {gran}: rows={summary['row_count']} sha={summary['sha256'][:12]}",
                flush=True,
            )
        except Exception as exc:
            print(f"  {pair} {gran}: MANIFEST FAILED: {exc}", flush=True)

    total_elapsed = time.time() - t0
    manifest = {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "environment": env,
        "scope": {
            "pairs": PAIRS_20,
            "granularities": GRANULARITIES,
            "days": DAYS,
            "price": PRICE,
            "n_jobs": n_total,
        },
        "outcome": {
            "n_files_manifested": len(manifest_files),
            "n_skipped": len(skipped),
            "n_completed": len(completed),
            "n_failed": len(failed),
            "total_elapsed_sec": round(total_elapsed, 1),
        },
        "files": manifest_files,
        "failures": failed,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest written: {MANIFEST_PATH}", flush=True)
    print(f"Total elapsed: {total_elapsed / 60:.1f} min", flush=True)
    return 0 if not failed else 2


if __name__ == "__main__":
    sys.exit(main())
