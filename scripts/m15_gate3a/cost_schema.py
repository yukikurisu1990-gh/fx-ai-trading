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


# RF-1: the session partition is part of the frozen contract, so pin its
# structure at import time — three windows, minute-granular, tiling 00:00..23:59
# exactly once. An edit that overlapped or left a hole would otherwise change
# which bars land in which session with nothing to notice it. Explicit raise,
# not `assert`: bare asserts are stripped under `python -O`.
def _check_session_partition() -> None:
    covered: set[int] = set()
    for name, window in SESSIONS_UTC.items():
        start_text, _, end_text = window.partition("-")
        start_h, _, start_m = start_text.partition(":")
        end_h, _, end_m = end_text.partition(":")
        lo = int(start_h) * 60 + int(start_m)
        hi = int(end_h) * 60 + int(end_m)
        if not 0 <= lo <= hi <= 24 * 60 - 1:
            raise RuntimeError(f"session {name!r} window {window!r} is out of range")
        minutes = set(range(lo, hi + 1))
        if covered & minutes:
            raise RuntimeError(f"session {name!r} overlaps another session")
        covered |= minutes
    if covered != set(range(24 * 60)):
        raise RuntimeError("SESSIONS_UTC does not tile the UTC day exactly once")


_check_session_partition()

# R-8: the committed cost_table_plan_or_metadata.json fixes the convention —
# "spreads measured in price units; converted via pip_size_for". Without a
# declared unit a price-unit table and a pip-unit table were indistinguishable
# (a 10,000x difference the schema could not see), and the formula string could
# document away the pinned 0.3 / 0.5.
SPREAD_UNIT: Final[str] = "price"
ALL_IN_COST_FORMULA: Final[str] = (
    "cost(pair, session) = median_spread(pair, session) + 0.3 + 0.5 (primary)"
)

# BL-5: there is NO absolute spread-magnitude bound in any committed authority.
# PR #440 invented ``MAX_PLAUSIBLE_SPREAD_PIPS = 100.0`` and applied it as
# ``100 * pip_size``; for a JPY pair that ceiling is 1.0 *price units* = 100
# pips, so ``USD_JPY median=0.9`` under ``spread_unit="price"`` — a 100x unit
# error — validated. The invented number is removed rather than re-tuned: this
# module may not mint a contract constant. Callers that hold a pinned bound pass
# it in explicitly; until one is recorded, the summary reports the magnitude in
# pips and states that it is UNVALIDATED. See the fix note for the referral.
MAGNITUDE_AUTHORITY_STATUS: Final[str] = "REQUIRES_SEPARATE_CONTRACT_GATE_DECISION"

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


def _check_magnitude_bound(bound: Any) -> float | None:
    """Validate a caller-supplied pip-unit magnitude bound, or accept 'none declared'."""
    if bound is None:
        return None
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        raise CostSchemaError("max_spread_pips must be a number or None")
    if not math.isfinite(bound) or bound <= 0:
        raise CostSchemaError("max_spread_pips must be a finite positive number of pips")
    return float(bound)


def validate_cost_table(table: Any, *, max_spread_pips: float | None = None) -> dict:
    """Validate cost-table metadata shape (fail-closed). Returns a summary.

    ``max_spread_pips`` is the pip-unit magnitude ceiling. It is deliberately
    **not** defaulted to a number: no committed authority pins one (BL-5), and
    inventing one here is what let a 100x JPY unit error validate. When it is
    ``None`` the summary reports every statistic converted to the pair's own
    pips and marks the magnitude UNVALIDATED, so a reader cannot mistake schema
    validity for magnitude validity.
    """
    ceiling_pips = _check_magnitude_bound(max_spread_pips)
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
    pips_observed: dict[str, float] = {}
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
        # BL-5: convert to the pair's own pips — pair-aware, and the only
        # magnitude statement this module can make from committed authority.
        # No floor is imposed: a zero quoted spread is accepted here because the
        # in-repo precedent (stage25_0a, which drops only `spread_pip < 0`, and
        # `aggregation._assert_bar_finite`, which rejects only a negative
        # spread_close) treats zero as observable rather than impossible.
        for stat, value in stats.items():
            in_pips = value / expected_pip
            pips_observed[f"{pair}/{session}/{stat}"] = in_pips
            if ceiling_pips is not None and in_pips > ceiling_pips:
                raise CostSchemaError(
                    f"{stat} for {pair}/{session} is {value} {SPREAD_UNIT} units = "
                    f"{in_pips:.4f} pips, above the caller-declared ceiling of "
                    f"{ceiling_pips} pips (wrong unit?)"
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
        # BL-5: magnitude is reported, never asserted, unless a caller pins it.
        "max_spread_pips_declared": ceiling_pips,
        "spread_magnitude_validated": ceiling_pips is not None,
        "max_observed_spread_pips": (max(pips_observed.values()) if pips_observed else None),
        "min_observed_spread_pips": (min(pips_observed.values()) if pips_observed else None),
        "magnitude_authority": (
            "CALLER_DECLARED" if ceiling_pips is not None else MAGNITUDE_AUTHORITY_STATUS
        ),
        "result": "COST_TABLE_SCHEMA_VALID",
    }
