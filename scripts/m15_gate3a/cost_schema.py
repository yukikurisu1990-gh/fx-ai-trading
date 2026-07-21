"""Cost-table metadata SCHEMA validation (no real spread computation).

Validates the shape of a cost-table metadata object against the frozen
contract + PR #430 T-7 (p95 diagnostic). Real per-pair/session spread numbers
are produced later (implementation, design-span data only). This module never
reads data and never computes spreads.
"""

from __future__ import annotations

import math
from typing import Any, Final

from scripts.ml_step4.data_adapter import pip_size_for

SESSIONS_UTC: Final[dict[str, str]] = {
    "asia": "00:00-07:59",
    "europe": "08:00-15:59",
    "us": "16:00-23:59",
}
EXECUTION_PADDING_PIP: Final[float] = 0.3
FLAT_SLIPPAGE_CELL_PIP: Final[float] = 0.5
CLAIM_SCOPE: Final[str] = "quote_cost_validity"

_REQUIRED_ENTRY_KEYS: Final[tuple[str, ...]] = (
    "pair",
    "session",
    "median_spread",
    "p90_spread",
    "p95_spread",
    "pip_size",
)
_REQUIRED_GLOBAL_KEYS: Final[tuple[str, ...]] = (
    "execution_padding_pip",
    "flat_slippage_cell_pip",
    "all_in_cost_formula",
    "claim_scope",
    "entries",
)


class CostSchemaError(ValueError):
    """Raised when cost-table metadata violates the frozen schema."""


def validate_cost_table(table: Any) -> dict:
    """Validate cost-table metadata shape (fail-closed). Returns a summary."""
    if not isinstance(table, dict):
        raise CostSchemaError("cost table must be a dict")
    for k in _REQUIRED_GLOBAL_KEYS:
        if k not in table:
            raise CostSchemaError(f"cost table missing global key {k!r}")
    if table["execution_padding_pip"] != EXECUTION_PADDING_PIP:
        raise CostSchemaError("execution_padding_pip must be 0.3")
    if table["flat_slippage_cell_pip"] != FLAT_SLIPPAGE_CELL_PIP:
        raise CostSchemaError("flat_slippage_cell_pip must be 0.5")
    if table["claim_scope"] != CLAIM_SCOPE:
        raise CostSchemaError("claim_scope must be 'quote_cost_validity'")

    entries = table["entries"]
    if not isinstance(entries, list) or not entries:
        raise CostSchemaError("cost table 'entries' must be a non-empty list")

    seen: set[tuple[str, str]] = set()
    for e in entries:
        if not isinstance(e, dict):
            raise CostSchemaError("cost entry must be a dict")
        for k in _REQUIRED_ENTRY_KEYS:
            if k not in e:
                raise CostSchemaError(f"cost entry missing key {k!r} (p95 diagnostic mandatory)")
        session = e["session"]
        if session not in SESSIONS_UTC:
            raise CostSchemaError(f"unsupported session {session!r}")
        pair = e["pair"]
        # Fail-closed pip check against the single authority (unknown pair raises).
        expected_pip = pip_size_for(pair)
        if e["pip_size"] != expected_pip:
            raise CostSchemaError(
                f"pip_size {e['pip_size']} for {pair} != authority {expected_pip}"
            )
        for stat in ("median_spread", "p90_spread", "p95_spread"):
            v = e[stat]
            # F-4 fix: NaN/inf must fail closed (``NaN < 0`` is False, so the
            # old check silently accepted non-finite spreads).
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                raise CostSchemaError(f"{stat} for {pair}/{session} must be a number")
            if not math.isfinite(v) or v < 0:
                raise CostSchemaError(
                    f"{stat} for {pair}/{session} must be a finite non-negative number"
                )
        key = (pair, session)
        if key in seen:
            raise CostSchemaError(f"duplicate (pair, session): {key}")
        seen.add(key)

    return {
        "entries_validated": len(entries),
        "sessions": sorted(SESSIONS_UTC),
        "p95_diagnostic_present": True,
        "real_spreads_computed": False,
        "result": "COST_TABLE_SCHEMA_VALID",
    }
