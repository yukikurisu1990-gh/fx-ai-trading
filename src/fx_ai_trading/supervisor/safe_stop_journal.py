"""SafeStopJournal — durable append-only file journal for safe_stop events (6.1).

Writes to logs/safe_stop.jsonl separately from the main database so that
safe_stop evidence survives DB failures. Each entry is fsynced and protected
by a threading.Lock for single-process safety.

DB reconciliation (step 7 of the M7 startup sequence):
  read_all() returns all persisted entries so Supervisor can compare them
  against the orders table and fill in any gaps. The reconciliation logic
  itself lives in M7 (Supervisor startup); this module only provides the
  journal unit.

Design constraints:
  - Must not call datetime.now() / time.time() (development_rules.md §13.1).
    All timestamps must be present in the entry dict provided by the caller.
  - Must not DELETE or truncate entries (append-only model).
  - Cross-process file locking: threading.Lock covers the single-process case.
    Add portalocker for multi-process safety when needed (Iteration 2+).
"""

from __future__ import annotations

import contextlib
import json
import os
import threading
from pathlib import Path

_DEFAULT_JOURNAL_PATH = Path("logs") / "safe_stop.jsonl"


class SafeStopJournal:
    """Append-only JSONL journal for safe_stop events.

    Args:
        journal_path: Path to the JSONL file. Defaults to logs/safe_stop.jsonl.
                      Parent directory must exist before append() is called.

    Thread safety: single-process safe via threading.Lock.
    Durability: each append flushes and fsyncs the file handle.
    """

    def __init__(self, journal_path: Path = _DEFAULT_JOURNAL_PATH) -> None:
        self._path = journal_path
        self._lock = threading.Lock()

    def append(self, entry: dict) -> None:
        """Persist *entry* to the journal with fsync.

        The caller must include all relevant fields (e.g. occurred_at, event_code,
        reason) in *entry*. No timestamp is added here (§13.1 constraint).

        Raises:
            OSError: if the file cannot be opened or written (caller handles).
        """
        line = json.dumps(entry, ensure_ascii=False, default=str)
        with self._lock, self._path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
            fh.flush()
            os.fsync(fh.fileno())

    def read_all(self) -> list[dict]:
        """Return all journal entries as a list of dicts.

        Returns an empty list if the journal file does not exist yet.
        Malformed lines are skipped with a best-effort parse (no raise).
        """
        if not self._path.exists():
            return []
        entries: list[dict] = []
        with self._lock:
            lines = self._path.read_text(encoding="utf-8").splitlines()
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            with contextlib.suppress(json.JSONDecodeError):
                entries.append(json.loads(stripped))
        return entries
