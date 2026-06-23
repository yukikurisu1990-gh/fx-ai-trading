"""Read-only raw inventory inspection (plan §6).

For each candidate M1 BA file this computes, in a SINGLE bounded-memory
streaming pass: presence, size, file SHA-256, row count, UTC timestamp
min/max, monotonicity / duplicate counts, schema-key presence, numeric
finiteness, a coarse gap profile, and any extra-key extensions. It never
loads the whole dataset into memory, never mutates / copies / transfers the
file, and produces only derived metadata (no raw rows).
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from ..b1_constants import NUMERIC_REQUIRED_FIELDS, PROTOCOL_REQUIRED_FIELDS

_BLOCK_SIZE = 8 * 1024 * 1024  # 8 MB streaming block

# Gap-profile bucket upper bounds in seconds (coarse; M1 expectation is a 60 s
# modal gap plus weekend / holiday clusters).
_GAP_BUCKETS_SECONDS = (60, 120, 300, 600, 3600, 21600, 86400, 604800)


def _parse_oanda_ts(s: str) -> datetime:
    """Local re-implementation of the OANDA timestamp parse (no import)."""
    if s.endswith("Z"):
        s = s[:-1]
    if "." in s:
        head, frac = s.split(".", 1)
        frac = frac.rstrip("0")
        if len(frac) > 6:
            frac = frac[:6]
        s = head + ("." + frac if frac else "")
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


@dataclass
class FileInventory:
    pair: str
    path: str
    present: bool
    size_bytes: int | None = None
    file_sha256: str | None = None
    row_count: int = 0
    malformed_rows: int = 0
    ts_min_utc: str | None = None
    ts_max_utc: str | None = None
    monotonicity_violations: int = 0
    duplicate_timestamps: int = 0
    missing_fields_count: int = 0
    non_finite_fields_count: int = 0
    schema_valid: bool = False
    schema_extension_findings: list[dict[str, object]] = field(default_factory=list)
    gap_profile: dict[str, object] = field(default_factory=dict)


class _RowAccumulator:
    """Bounded-memory per-file accumulator over streamed rows."""

    def __init__(self) -> None:
        self.row_count = 0
        self.malformed_rows = 0
        self.missing_fields_count = 0
        self.non_finite_fields_count = 0
        self.monotonicity_violations = 0
        self.duplicate_timestamps = 0
        self.ts_min: datetime | None = None
        self.ts_max: datetime | None = None
        self.ts_min_str: str | None = None
        self.ts_max_str: str | None = None
        self._prev_ts: datetime | None = None
        self._prev_ts_str: str | None = None
        self._extension_counts: dict[str, int] = {}
        self._gap_hist = dict.fromkeys(self._gap_labels(), 0)
        self.max_gap_seconds = 0

    @staticmethod
    def _gap_labels() -> list[str]:
        labels = []
        prev = 0
        for bound in _GAP_BUCKETS_SECONDS:
            labels.append(f"<= {bound}s")
            prev = bound
        labels.append(f"> {prev}s")
        return labels

    def _bucket(self, seconds: float) -> str:
        for bound in _GAP_BUCKETS_SECONDS:
            if seconds <= bound:
                return f"<= {bound}s"
        return f"> {_GAP_BUCKETS_SECONDS[-1]}s"

    def process(self, line: bytes) -> None:
        stripped = line.strip()
        if not stripped:
            return
        try:
            record = json.loads(stripped)
        except (ValueError, UnicodeDecodeError):
            self.malformed_rows += 1
            return
        if not isinstance(record, dict):
            self.malformed_rows += 1
            return
        self.row_count += 1

        keys = set(record.keys())
        if not PROTOCOL_REQUIRED_FIELDS.issubset(keys):
            self.missing_fields_count += 1
        for extra in keys - PROTOCOL_REQUIRED_FIELDS:
            self._extension_counts[extra] = self._extension_counts.get(extra, 0) + 1
        for fname in NUMERIC_REQUIRED_FIELDS:
            if fname in record:
                value = record[fname]
                if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    self.non_finite_fields_count += 1

        time_value = record.get("time")
        if isinstance(time_value, str):
            self._process_timestamp(time_value)

    def _process_timestamp(self, time_str: str) -> None:
        try:
            ts = _parse_oanda_ts(time_str)
        except ValueError:
            self.malformed_rows += 1
            return
        if self.ts_min is None or ts < self.ts_min:
            self.ts_min = ts
            self.ts_min_str = time_str
        if self.ts_max is None or ts > self.ts_max:
            self.ts_max = ts
            self.ts_max_str = time_str
        if self._prev_ts is not None:
            if time_str == self._prev_ts_str:
                self.duplicate_timestamps += 1
            elif ts <= self._prev_ts:
                self.monotonicity_violations += 1
            else:
                gap = (ts - self._prev_ts).total_seconds()
                self._gap_hist[self._bucket(gap)] += 1
                self.max_gap_seconds = max(self.max_gap_seconds, int(gap))
        self._prev_ts = ts
        self._prev_ts_str = time_str

    def extensions(self) -> list[dict[str, object]]:
        return [
            {"field_name": name, "occurrence_count": count}
            for name, count in sorted(self._extension_counts.items())
        ]

    def gap_profile(self) -> dict[str, object]:
        return {
            "histogram": [{"bucket": k, "count": v} for k, v in self._gap_hist.items()],
            "max_gap_seconds": self.max_gap_seconds,
        }


def inspect_file(pair: str, path: Path) -> FileInventory:
    """Inspect a single candidate file read-only (streaming, bounded memory)."""
    if not path.exists():
        return FileInventory(pair=pair, path=str(path), present=False)

    digest = hashlib.sha256()
    acc = _RowAccumulator()
    carry = b""
    size_bytes = 0
    with path.open("rb") as handle:
        while True:
            block = handle.read(_BLOCK_SIZE)
            if not block:
                break
            size_bytes += len(block)
            digest.update(block)
            data = carry + block
            parts = data.split(b"\n")
            carry = parts.pop()
            for part in parts:
                acc.process(part)
        if carry:
            acc.process(carry)

    schema_valid = acc.missing_fields_count == 0 and acc.non_finite_fields_count == 0
    return FileInventory(
        pair=pair,
        path=str(path),
        present=True,
        size_bytes=size_bytes,
        file_sha256=digest.hexdigest(),
        row_count=acc.row_count,
        malformed_rows=acc.malformed_rows,
        ts_min_utc=acc.ts_min_str,
        ts_max_utc=acc.ts_max_str,
        monotonicity_violations=acc.monotonicity_violations,
        duplicate_timestamps=acc.duplicate_timestamps,
        missing_fields_count=acc.missing_fields_count,
        non_finite_fields_count=acc.non_finite_fields_count,
        schema_valid=schema_valid and acc.row_count > 0,
        schema_extension_findings=acc.extensions(),
        gap_profile=acc.gap_profile(),
    )


def inspect_candidate(data_dir: str | Path, pairs: list[str], span_label: str) -> dict[str, object]:
    """Inspect all pair files for one candidate span. Returns derived metadata."""
    data_dir = Path(data_dir)
    files: list[dict[str, object]] = []
    for pair in pairs:
        path = data_dir / f"candles_{pair}_M1_{span_label}_BA.jsonl"
        files.append(asdict(inspect_file(pair, path)))
    return {"span_label": span_label, "files": files}
