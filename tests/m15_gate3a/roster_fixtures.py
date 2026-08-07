"""Shared PAIRS_20 evidence builders for the no-overlap proof tests (BL-1).

``assert_per_file_bounds`` now only emits ``PROVEN_NO_DEAD_WINDOW_OVERLAP`` for
a complete, distinct, canonical 20-pair inventory, so every test that exercises
the proof needs real roster evidence rather than a single record. These helpers
build exactly that, and give each record the distinct ``filename``/``sha256``
identity the committed ``design_m15_inventory.json`` schema declares.
"""

from __future__ import annotations

from typing import Any

from scripts.m15_gate3a.pair_authority import PAIRS_20

DESIGN_TS_MIN = "2025-05-01T00:00:00Z"
DESIGN_TS_MAX = "2025-12-31T23:59:59Z"
FORWARD_TS_MIN = "2026-05-01T00:00:00Z"
FORWARD_TS_MAX = "2026-06-30T23:59:59Z"


def file_record(pair: str, index: int, *, ts_min: str, ts_max: str, role: str) -> dict[str, Any]:
    """One inventory record with the identity keys the committed schema declares."""
    return {
        "pair": pair,
        "filename": f"candles_{pair}_M15_365d_BA_{role.upper()}.jsonl",
        "sha256": f"{index:064x}",
        "ts_min_utc": ts_min,
        "ts_max_utc": ts_max,
    }


def design_roster(ts_min: str = DESIGN_TS_MIN, ts_max: str = DESIGN_TS_MAX) -> list[dict[str, Any]]:
    """A complete, distinct 20-pair design inventory."""
    return [
        file_record(pair, i + 1, ts_min=ts_min, ts_max=ts_max, role="design")
        for i, pair in enumerate(PAIRS_20)
    ]


def forward_roster(
    ts_min: str = FORWARD_TS_MIN, ts_max: str = FORWARD_TS_MAX
) -> list[dict[str, Any]]:
    """A complete, distinct 20-pair forward inventory."""
    return [
        file_record(pair, i + 1, ts_min=ts_min, ts_max=ts_max, role="forward")
        for i, pair in enumerate(PAIRS_20)
    ]
