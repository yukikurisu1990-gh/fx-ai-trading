"""Cost-table metadata schema tests (no real spreads).

``_table`` is the shared cost-table fixture for this package: ``test_recheck_fixes``,
``test_second_recheck_fixes`` and ``test_source_audit_fixes`` all build their
tables from it, so it is defined once here and kept faithful to the **committed**
plan (``artifacts/m15_gate3a/cost_table_plan_or_metadata.json``).

Two contract rulings shape it:

* **D-10 / §12.16** — coverage is *enforced*, not reported: a table is admissible
  only if it carries all ``20 x 3 = 60`` canonical ``(pair, session)`` cells. The
  fixture therefore builds the whole grid, and a test whose subject is a single
  malformed cell overrides exactly one cell so the guard it names is still the
  first one reached.
* **RF-16 / RF-17** — ``stress_forms``, ``data_source_restriction`` and the
  ``claim_scope`` spelling are quoted from the committed plan. The previous
  code-minted ``"quote_cost_validity"`` was a spelling the validator *refused*,
  so no table written from the plan could have validated.
"""

from __future__ import annotations

from typing import Any, Final

import pytest

from scripts.m15_gate3a.cost_schema import CostSchemaError, validate_cost_table
from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair

# Restated from the committed plan, never imported from the module under test:
# a constant that drifts away from the plan must fail here, not agree with itself.
SESSIONS: Final[tuple[str, ...]] = ("asia", "europe", "us")
PLAN_CLAIM_SCOPE: Final[str] = "quote-cost-validity research claim; NOT a live-fill claim"
PLAN_FORMULA: Final[str] = (
    "cost(pair, session) = median_spread(pair, session) + 0.3 + 0.5 (primary)"
)
PLAN_STRESS_FORMS: Final[tuple[str, ...]] = (
    "2x modelled cost",
    "p90 session spread substituted for median",
)
PLAN_DATA_SOURCE_RESTRICTION: Final[str] = (
    "DESIGN span only (2025-04-25..2026-02-28); never validation/holdout; "
    "frozen and committed as metadata"
)
EXPECTED_CELLS: Final[int] = 60  # 20 canonical pairs x 3 UTC sessions, both frozen

# (median, p90, p95) of every default cell, expressed in the cell's OWN pips so a
# JPY and a non-JPY cell carry the same magnitude. Deliberately small: a test that
# declares a magnitude ceiling must have its overridden cell, not the filler, be
# the one that trips it.
DEFAULT_CELL_PIPS: Final[tuple[float, float, float]] = (1.0, 2.0, 3.0)

# The pip sizes of the frozen universe, restated so a wrong-scale table is built
# from an independent statement of the authority rather than from the authority.
_PIP_JPY: Final[float] = 0.01
_PIP_NON_JPY: Final[float] = 0.0001


def _pip(pair: str) -> float:
    return _PIP_JPY if pair.endswith("_JPY") else _PIP_NON_JPY


def _cell(pair: str, session: str, pips: tuple[float, float, float]) -> dict[str, Any]:
    """One synthetic ``(pair, session)`` cost cell. The spreads are invented test numbers."""
    pip = _pip(pair)
    median, p90, p95 = pips
    return {
        "pair": pair,
        "session": session,
        "median_spread": median * pip,
        "p90_spread": p90 * pip,
        "p95_spread": p95 * pip,
        "pip_size": pip,
    }


def _table(**overrides: Any) -> dict[str, Any]:
    """A complete, valid 20 x 3 cost table, with optional overrides.

    ``pips=(median, p90, p95)`` re-scales **every** cell, in pips, so a test that
    pins a magnitude boundary controls the whole grid rather than one outlier.

    ``entry={...}`` overrides exactly **one** cell — the one named by the
    override's own ``pair``/``session``, defaulting to ``EUR_USD``/``europe``.
    That keeps the other 59 cells valid, so the refusal a test asserts is the one
    its own cell provokes and not the coverage refusal that would otherwise fire
    first. Any other keyword replaces a top-level key (including ``entries``).
    """
    pips: tuple[float, float, float] = overrides.pop("pips", DEFAULT_CELL_PIPS)
    entry_override: dict[str, Any] = dict(overrides.pop("entry", {}))
    entries = [_cell(pair, session, pips) for pair in PAIRS_20 for session in SESSIONS]

    if entry_override:
        # Resolve which grid cell the override is aimed at. A deliberately
        # invalid pair/session in the override still has to land somewhere, so it
        # falls back to the default cell and the override then carries the defect
        # into it.
        try:
            target_pair = canonical_pair(entry_override.get("pair", "EUR_USD"))
        except PairAuthorityError:
            target_pair = "EUR_USD"
        target_session = entry_override.get("session", "europe")
        if target_session not in SESSIONS:
            target_session = "europe"
        position = next(
            i
            for i, cell in enumerate(entries)
            if cell["pair"] == target_pair and cell["session"] == target_session
        )
        entries[position] = {**entries[position], **entry_override}

    table: dict[str, Any] = {
        "execution_padding_pip": 0.3,
        "flat_slippage_cell_pip": 0.5,
        "all_in_cost_formula": PLAN_FORMULA,
        "spread_unit": "price",
        "claim_scope": PLAN_CLAIM_SCOPE,
        "stress_forms": list(PLAN_STRESS_FORMS),
        "data_source_restriction": PLAN_DATA_SOURCE_RESTRICTION,
        "entries": entries,
    }
    table.update(overrides)
    return table


def test_the_shared_fixture_is_the_complete_grid_the_other_tests_assume() -> None:
    """Non-vacuity floor for the fixture itself.

    If ``_table()`` ever stopped covering all 60 cells, every refusal test built
    on it would start passing because of the coverage guard rather than because
    of the guard it names.
    """
    table = _table()
    assert len(table["entries"]) == EXPECTED_CELLS
    assert len({(e["pair"], e["session"]) for e in table["entries"]}) == EXPECTED_CELLS
    assert len(PAIRS_20) * len(SESSIONS) == EXPECTED_CELLS
    assert validate_cost_table(table, max_spread_pips=None)["entries_validated"] == EXPECTED_CELLS


def test_valid_cost_table_passes() -> None:
    r = validate_cost_table(_table(), max_spread_pips=None)
    assert r["result"] == "COST_TABLE_SCHEMA_VALID"
    # R-1 (negative control): ``p95_diagnostic_present`` and ``real_spreads_computed``
    # were single-valued self-attestations and are deleted, not reported. The
    # measured facts that replace them are asserted instead; the p95 property
    # itself is enforced by the refusal in ``test_missing_p95_fails`` below.
    assert r["entries_validated"] == EXPECTED_CELLS
    assert r["pairs_covered"] == sorted(PAIRS_20)
    assert r["sessions"] == sorted(SESSIONS)


def test_missing_p95_fails() -> None:
    e = {
        "pair": "EUR_USD",
        "session": "europe",
        "median_spread": 0.00008,
        "p90_spread": 0.00015,
        "pip_size": 0.0001,
    }
    with pytest.raises(CostSchemaError, match="missing key 'p95_spread'"):
        validate_cost_table(_table(entries=[e]), max_spread_pips=None)


def test_wrong_jpy_pip_fails() -> None:
    with pytest.raises(CostSchemaError, match="pip_size"):
        validate_cost_table(
            _table(entry={"pair": "USD_JPY", "pip_size": 0.0001}), max_spread_pips=None
        )  # should be 0.01


def test_correct_jpy_pip_passes() -> None:
    r = validate_cost_table(
        _table(
            entry={
                "pair": "USD_JPY",
                "pip_size": _PIP_JPY,
                "median_spread": 0.008,
                "p90_spread": 0.015,
                "p95_spread": 0.02,
            }
        ),
        max_spread_pips=None,
    )
    assert r["result"] == "COST_TABLE_SCHEMA_VALID"


def test_missing_claim_scope_fails() -> None:
    t = _table()
    del t["claim_scope"]
    with pytest.raises(CostSchemaError, match="missing global key 'claim_scope'"):
        validate_cost_table(t, max_spread_pips=None)


def test_wrong_claim_scope_fails() -> None:
    with pytest.raises(CostSchemaError, match="claim_scope must be"):
        validate_cost_table(_table(claim_scope="live_fill_validity"), max_spread_pips=None)


def test_unsupported_session_fails() -> None:
    with pytest.raises(CostSchemaError, match="unsupported session"):
        validate_cost_table(_table(entry={"session": "sydney"}), max_spread_pips=None)


def test_wrong_padding_or_cell_fails() -> None:
    with pytest.raises(CostSchemaError, match="execution_padding_pip"):
        validate_cost_table(_table(execution_padding_pip=0.1), max_spread_pips=None)
    with pytest.raises(CostSchemaError, match="flat_slippage_cell_pip"):
        validate_cost_table(_table(flat_slippage_cell_pip=1.0), max_spread_pips=None)
