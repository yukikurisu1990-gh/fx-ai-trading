"""Cost-table metadata SCHEMA validation (no real spread computation).

Validates the shape of a cost-table metadata object against the frozen
contract + PR #430 T-7 (p95 diagnostic). Real per-pair/session spread numbers
are produced later (implementation, design-span data only). This module never
reads data and never computes spreads.
"""

from __future__ import annotations

import math
from typing import Any, Final

from .pair_authority import PAIRS_20, canonical_pair, pip_size_for_pair

SESSIONS_UTC: Final[dict[str, str]] = {
    "asia": "00:00-07:59",
    "europe": "08:00-15:59",
    "us": "16:00-23:59",
}
EXECUTION_PADDING_PIP: Final[float] = 0.3
FLAT_SLIPPAGE_CELL_PIP: Final[float] = 0.5
CLAIM_SCOPE: Final[str] = "quote_cost_validity"

# R-8: the committed cost_table_plan_or_metadata.json fixes the convention —
# "spreads measured in price units; converted via pip_size_for". Without a
# declared unit a price-unit table and a pip-unit table were indistinguishable
# (a 10,000x difference the schema could not see), and the formula string could
# document away the pinned 0.3 / 0.5.
SPREAD_UNIT: Final[str] = "price"
# A quoted spread wider than 100 pips is not a real quote for PAIRS_20; anything
# above it is far more likely a unit error than a market condition.
MAX_PLAUSIBLE_SPREAD_PIPS: Final[float] = 100.0
ALL_IN_COST_FORMULA: Final[str] = (
    "cost(pair, session) = median_spread(pair, session) + 0.3 + 0.5 (primary)"
)

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
    "spread_unit",
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
    if table["spread_unit"] != SPREAD_UNIT:
        raise CostSchemaError(f"spread_unit must be {SPREAD_UNIT!r} (price units, per the plan)")
    if table["all_in_cost_formula"] != ALL_IN_COST_FORMULA:
        raise CostSchemaError("all_in_cost_formula must match the frozen plan string verbatim")

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
        # B-4: normalise + universe-check before the pip comparison, so a
        # non-canonical spelling cannot agree with a wrongly scaled pip_size.
        pair = canonical_pair(e["pair"])
        if e["pair"] != pair:
            raise CostSchemaError(
                f"pair must be the canonical spelling {pair!r}, got {e['pair']!r}"
            )
        expected_pip = pip_size_for_pair(pair)
        if e["pip_size"] != expected_pip:
            raise CostSchemaError(
                f"pip_size {e['pip_size']} for {pair} != authority {expected_pip}"
            )
        stats: dict[str, float] = {}
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
            stats[stat] = float(v)
        # R-8 residual (a): declaring the unit does not catch a mis-declared
        # MAGNITUDE. A pip-scale number under spread_unit="price" is a 10,000x
        # error that every other check would accept, so bound each statistic to
        # a generous plausibility ceiling expressed in the pair's own pips.
        for stat, value in stats.items():
            if value > MAX_PLAUSIBLE_SPREAD_PIPS * expected_pip:
                raise CostSchemaError(
                    f"{stat} for {pair}/{session} is {value} price units = "
                    f"{value / expected_pip:.1f} pips, above the plausibility ceiling of "
                    f"{MAX_PLAUSIBLE_SPREAD_PIPS} pips (wrong unit?)"
                )
        # R-8: without monotonicity the mandatory p90 stress could be milder
        # than the base case.
        if not stats["median_spread"] <= stats["p90_spread"] <= stats["p95_spread"]:
            raise CostSchemaError(
                f"spread quantiles for {pair}/{session} must satisfy "
                f"median <= p90 <= p95 (got {stats['median_spread']}, "
                f"{stats['p90_spread']}, {stats['p95_spread']})"
            )
        key = (pair, session)
        if key in seen:
            raise CostSchemaError(f"duplicate (pair, session): {key}")
        seen.add(key)

    return {
        "entries_validated": len(entries),
        "sessions": sorted(SESSIONS_UTC),
        "spread_unit": SPREAD_UNIT,
        "pairs_covered": sorted({p for p, _ in seen}),
        "full_20x3_coverage": len(seen) == len(PAIRS_20) * len(SESSIONS_UTC),
        "p95_diagnostic_present": True,
        "real_spreads_computed": False,
        "result": "COST_TABLE_SCHEMA_VALID",
    }
