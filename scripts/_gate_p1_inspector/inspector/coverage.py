"""Coverage derivation for a candidate span (plan §6).

Derives the common observation interval across the pair universe from the
per-file timestamp boundaries produced by raw inventory. It performs no I/O of
its own and computes no labels / features / trades — only the interval and
deterministic coverage findings.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _parse_iso(ts: str) -> datetime:
    s = ts[:-1] if ts.endswith("Z") else ts
    if "." in s:
        head, frac = s.split(".", 1)
        frac = frac.rstrip("0")
        if len(frac) > 6:
            frac = frac[:6]
        s = head + ("." + frac if frac else "")
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def derive_coverage(span_label: str, files: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute the common observation interval and coverage findings."""
    present_with_rows = [
        f for f in files if f.get("present") and f.get("row_count", 0) > 0 and f.get("ts_min_utc")
    ]
    missing_or_empty = [
        f["pair"] for f in files if not (f.get("present") and f.get("row_count", 0) > 0)
    ]

    findings: list[dict[str, Any]] = []
    if missing_or_empty:
        findings.append(
            {
                "finding_type": "pairs_missing_or_empty",
                "pairs": sorted(missing_or_empty),
            }
        )

    # Interval is null if ANY pair is absent / empty (plan §6 missing-pair rule).
    if missing_or_empty or not present_with_rows:
        return {
            "span_label": span_label,
            "observation_start_timestamp_utc": None,
            "observation_end_timestamp_utc": None,
            "span_days_effective": None,
            "common_coverage_findings": findings,
        }

    starts = [_parse_iso(f["ts_min_utc"]) for f in present_with_rows]
    ends = [_parse_iso(f["ts_max_utc"]) for f in present_with_rows]
    obs_start = max(starts)
    obs_end = min(ends)

    if obs_end < obs_start:
        findings.append({"finding_type": "degenerate_interval", "value": True})
        return {
            "span_label": span_label,
            "observation_start_timestamp_utc": None,
            "observation_end_timestamp_utc": None,
            "span_days_effective": None,
            "common_coverage_findings": findings,
        }

    span_days = (obs_end - obs_start).total_seconds() / 86400.0
    return {
        "span_label": span_label,
        "observation_start_timestamp_utc": obs_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "observation_end_timestamp_utc": obs_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "span_days_effective": round(span_days, 4),
        "common_coverage_findings": findings,
    }
