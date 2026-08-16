"""Cost-table metadata SCHEMA validation (no real spread computation).

Validates the shape of a cost-table metadata object against the frozen
contract + PR #430 T-7 (p95 diagnostic). Real per-pair/session spread numbers
are produced later (implementation, design-span data only). This module never
reads data and never computes spreads.
"""

from __future__ import annotations

import math
from typing import Any, Final

from .numeric_authority import NumericAuthorityError, pin_number
from .pair_authority import PAIRS_20, canonical_pair, pip_size_for_pair

SESSIONS_UTC: Final[dict[str, str]] = {
    "asia": "00:00-07:59",
    "europe": "08:00-15:59",
    "us": "16:00-23:59",
}
EXECUTION_PADDING_PIP: Final[float] = 0.3
FLAT_SLIPPAGE_CELL_PIP: Final[float] = 0.5
# RF-17: the previous value ``"quote_cost_validity"`` was **code-minted**. The
# committed plan's ``must_produce_before_gate7_authorisation.claim_scope`` reads
# exactly as below, and the validator used to *refuse* the committed spelling —
# i.e. no table written from the plan could have validated. Quoted verbatim from
# ``artifacts/m15_gate3a/cost_table_plan_or_metadata.json``.
CLAIM_SCOPE: Final[str] = "quote-cost-validity research claim; NOT a live-fill claim"

# RF-16: both stress forms are mandatory in the committed plan ("stress_forms":
# ["2x modelled cost", "p90 session spread substituted for median"]) and the data
# source is restricted there too. Neither was required nor checked, so a table
# omitting both returned COST_TABLE_SCHEMA_VALID — including a table whose
# spreads came from validation or holdout span. Both strings are quoted verbatim
# from the committed plan; nothing here is minted.
STRESS_FORMS: Final[tuple[str, ...]] = (
    "2x modelled cost",
    "p90 session spread substituted for median",
)
DATA_SOURCE_RESTRICTION: Final[str] = (
    "DESIGN span only (2025-04-25..2026-02-28); never validation/holdout; "
    "frozen and committed as metadata"
)


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
# PR #440 invented ``MAX_PLAUSIBLE_SPREAD_PIPS = 100.0``, applied as
# ``value > 100 * pip_size`` — algebraically a uniform 100-pip ceiling for every
# pair, NOT a JPY-specific scaling error. What it could not catch is the JPY
# 100x class: ``USD_JPY median=0.9`` price units is 90 pips, under the ceiling,
# while the same class on a non-JPY pair lands at 9,000 pips and is caught.
# The invented number is removed rather than re-tuned — this module may not mint
# a contract constant — and `max_spread_pips` is made a REQUIRED argument so the
# removal cannot silently become "no check". See the fix note for the referral.
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
    "stress_forms",
    "data_source_restriction",
    "entries",
)


class CostSchemaError(ValueError):
    """Raised when cost-table metadata violates the frozen schema."""


def _check_stress_forms(value: Any) -> None:
    """RF-16: both committed stress forms present, no repeats, nothing unauthorised."""
    if not isinstance(value, list):
        raise CostSchemaError("stress_forms must be a list of the plan's mandatory stress forms")
    if any(not isinstance(v, str) or isinstance(v, bool) for v in value):
        raise CostSchemaError("stress_forms entries must be strings")
    if len(set(value)) != len(value):
        raise CostSchemaError("stress_forms must not repeat a stress form")
    missing = [f for f in STRESS_FORMS if f not in value]
    if missing:
        raise CostSchemaError(f"stress_forms is missing the mandatory form(s) {missing!r}")
    unauthorised = [v for v in value if v not in STRESS_FORMS]
    if unauthorised:
        raise CostSchemaError(f"stress_forms carries unauthorised form(s) {unauthorised!r}")


def _pin_numeric(value: Any, *, what: str) -> Any:
    """Plain numeric character data for a number; anything else unchanged (N-1).

    ``isinstance(v, (int, float))`` admits a *subclass*, and a subclass owns
    ``__lt__`` and ``__eq__``. The audit drove a ``float`` subclass whose
    ordering dunders always answer "not less" straight through the
    non-negativity guard below: ``median_spread = -5.0`` validated as
    ``COST_TABLE_SCHEMA_VALID`` and the summary reported
    ``min_observed_spread_pips = -50000.0``. Every number this validator
    compares is therefore read once, as its plain character data.

    Non-numbers pass through untouched so the *existing* refusal for each field
    keeps firing with its own message — this closes a lying comparison without
    re-routing a type error to a different raise site.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    return pin_number(value, what=what)


def _check_magnitude_bound(bound: Any) -> float | None:
    """Validate a caller-supplied pip-unit magnitude bound, or accept 'none declared'."""
    if bound is None:
        return None
    if isinstance(bound, bool) or not isinstance(bound, (int, float)):
        raise CostSchemaError("max_spread_pips must be a number or None")
    try:
        value = pin_number(bound, what="max_spread_pips")
    except NumericAuthorityError as exc:  # pragma: no cover - guarded above
        raise CostSchemaError(str(exc)) from exc
    if not math.isfinite(value) or value <= 0:
        raise CostSchemaError("max_spread_pips must be a finite positive number of pips")
    return float(value)


def validate_cost_table(table: Any, *, max_spread_pips: float | None) -> dict:
    """Validate cost-table metadata shape (fail-closed). Returns a summary.

    ``max_spread_pips`` is the pip-unit magnitude ceiling and is a **required**
    keyword argument with no default. That is deliberate, and it is the
    resolution of a genuine tension the internal audit surfaced:

    * no committed authority pins a magnitude bound, so this module may not
      invent one (BL-5) — PR #440's ``100.0`` was invented, and at 100 pips it
      was too loose to catch a 100x JPY unit error (``USD_JPY median=0.9``
      price units = 90 pips slipped under it);
    * but simply defaulting to "no check" would have made the non-JPY case,
      where that ceiling *did* work, strictly weaker — a 10,000x error
      (``EUR_USD median=1.5`` = 15,000 pips) would pass unremarked.

    Requiring the argument forces every caller to state a bound or to state
    ``None`` — "no bound is pinned, magnitude UNVALIDATED" — so the choice is
    always recorded and never inherited by accident. With ``None`` the summary
    still reports every statistic converted to the pair's own pips.

    **Coverage is enforced, not reported** (RF-19 / D-10 / §12.16): a table is
    admissible only if it carries every one of the ``20 x 3 = 60`` canonical
    ``(pair, session)`` cells. An incomplete table raises and names the missing
    cells; there is deliberately no flag, parameter or partial mode, because a
    recorded coverage flag is precisely how the previous re-disposition let a
    one-entry table validate.
    """
    ceiling_pips = _check_magnitude_bound(max_spread_pips)
    if not isinstance(table, dict):
        raise CostSchemaError("cost table must be a dict")
    for k in _REQUIRED_GLOBAL_KEYS:
        if k not in table:
            raise CostSchemaError(f"cost table missing global key {k!r}")
    padding = _pin_numeric(table["execution_padding_pip"], what="execution_padding_pip")
    if padding != EXECUTION_PADDING_PIP:
        raise CostSchemaError("execution_padding_pip must be 0.3")
    slippage = _pin_numeric(table["flat_slippage_cell_pip"], what="flat_slippage_cell_pip")
    if slippage != FLAT_SLIPPAGE_CELL_PIP:
        raise CostSchemaError("flat_slippage_cell_pip must be 0.5")
    if table["claim_scope"] != CLAIM_SCOPE:
        raise CostSchemaError(f"claim_scope must be the committed plan's spelling {CLAIM_SCOPE!r}")
    if table["spread_unit"] != SPREAD_UNIT:
        raise CostSchemaError(f"spread_unit must be {SPREAD_UNIT!r} (price units, per the plan)")
    if table["all_in_cost_formula"] != ALL_IN_COST_FORMULA:
        raise CostSchemaError("all_in_cost_formula must match the frozen plan string verbatim")
    _check_stress_forms(table["stress_forms"])
    if table["data_source_restriction"] != DATA_SOURCE_RESTRICTION:
        raise CostSchemaError(
            "data_source_restriction must match the committed plan verbatim "
            f"({DATA_SOURCE_RESTRICTION!r}); a table sourced from validation or holdout span "
            "is not admissible"
        )

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
        if _pin_numeric(e["pip_size"], what="pip_size") != expected_pip:
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
            # N-1: pin the character data BEFORE the sign test. `v < 0` asked a
            # caller-controlled `__lt__` whether the spread was negative.
            v = pin_number(v, what=f"{stat} for {pair}/{session}")
            if not math.isfinite(v) or v < 0:
                raise CostSchemaError(
                    f"{stat} for {pair}/{session} must be a finite non-negative number"
                )
            stats[stat] = float(v)
        # BL-5: convert to the pair's own pips — pair-aware, and the only
        # magnitude statement this module can make from committed authority.
        # No floor is imposed because **no committed authority pins a lower
        # bound on a quoted spread**, and this module may not mint one. That is
        # the whole of the argument. The `stage25_0a` analogy this comment used
        # to cite is REVOKED: the gate-3a contract Gate-decision §3 lists
        # "citing scripts/stage25_0a_build_path_quality_dataset.py ... as
        # authority for a family-A design semantic" under Forbidden, and D-1.7
        # settles the zero-spread limb on its own grounds — `ask == bid` is not
        # a crossed quote, and is refused only by a separate cost/spread
        # contract if one is ever pinned (referral 1, still MAY_DEFER).
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

    # RF-19 / D-10 (NR-J) / §12.16: insufficient required coverage **raises**; a
    # reported coverage flag never permits continuation. Merged-audit R-8's
    # fourth limb ("a one-entry table validates, so 20 x 3 coverage is
    # unenforced — fix all four before the tables are produced") was re-disposed
    # into the boolean this replaces. Both operands are already frozen
    # (``PAIRS_20`` x ``SESSIONS_UTC``), so no number is minted here.
    required_cells = {(p, s) for p in PAIRS_20 for s in SESSIONS_UTC}
    missing_cells = sorted(f"{p}/{s}" for p, s in required_cells - seen)
    if missing_cells:
        raise CostSchemaError(
            f"cost table must cover all {len(PAIRS_20)}x{len(SESSIONS_UTC)}="
            f"{len(required_cells)} canonical (pair, session) cells; "
            f"{len(missing_cells)} missing: {', '.join(missing_cells)}"
        )

    return {
        "entries_validated": len(entries),
        "sessions": sorted(SESSIONS_UTC),
        "spread_unit": SPREAD_UNIT,
        "pairs_covered": sorted({p for p, _ in seen}),
        # R-1 (negative control): ``full_20x3_coverage``, ``p95_diagnostic_present``
        # and ``real_spreads_computed`` were removed. The first became incapable of
        # holding ``False`` the moment coverage started raising — a vacuous field
        # introduced by this very fix is exactly the class PR #442 created four of.
        # The other two never could hold their opposite: they attest properties this
        # validator does not measure, and R-1 requires such a field to be deleted,
        # not reported. Both are enforced by refusals whose counter-cases are
        # exercised in the suite (a table without ``p95_spread`` raises; the module
        # computes no spread at all — see the audit's containment derivation).
        # BL-5: magnitude is reported, never asserted, unless a caller pins it.
        # The flag is named for what it actually says — a bound was supplied and
        # checked — not "the magnitude is valid": a caller is free to declare a
        # bound so loose it excludes nothing, and `max_spread_pips_declared`
        # alongside it is what makes that visible.
        "max_spread_pips_declared": ceiling_pips,
        "magnitude_checked_against_declared_bound": ceiling_pips is not None,
        "max_observed_spread_pips": (max(pips_observed.values()) if pips_observed else None),
        "min_observed_spread_pips": (min(pips_observed.values()) if pips_observed else None),
        "magnitude_authority": (
            "CALLER_DECLARED" if ceiling_pips is not None else MAGNITUDE_AUTHORITY_STATUS
        ),
        "result": "COST_TABLE_SCHEMA_VALID",
    }
