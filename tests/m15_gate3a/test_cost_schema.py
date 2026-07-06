"""Cost-table metadata schema tests (no real spreads)."""

from __future__ import annotations

import pytest

from scripts.m15_gate3a.cost_schema import CostSchemaError, validate_cost_table


def _table(**overrides):
    entry = {
        "pair": "EUR_USD",
        "session": "europe",
        "median_spread": 0.00008,
        "p90_spread": 0.00015,
        "p95_spread": 0.00020,
        "pip_size": 0.0001,
    }
    entry.update(overrides.pop("entry", {}))
    t = {
        "execution_padding_pip": 0.3,
        "flat_slippage_cell_pip": 0.5,
        "all_in_cost_formula": "median + 0.3 + 0.5",
        "claim_scope": "quote_cost_validity",
        "entries": [entry],
    }
    t.update(overrides)
    return t


def test_valid_cost_table_passes() -> None:
    r = validate_cost_table(_table())
    assert r["result"] == "COST_TABLE_SCHEMA_VALID"
    assert r["p95_diagnostic_present"] is True
    assert r["real_spreads_computed"] is False


def test_missing_p95_fails() -> None:
    e = {
        "pair": "EUR_USD",
        "session": "europe",
        "median_spread": 0.00008,
        "p90_spread": 0.00015,
        "pip_size": 0.0001,
    }
    with pytest.raises(CostSchemaError):
        validate_cost_table(_table(entries=[e]))


def test_wrong_jpy_pip_fails() -> None:
    with pytest.raises(CostSchemaError):
        validate_cost_table(_table(entry={"pair": "USD_JPY", "pip_size": 0.0001}))  # should be 0.01


def test_correct_jpy_pip_passes() -> None:
    r = validate_cost_table(
        _table(
            entry={
                "pair": "USD_JPY",
                "pip_size": 0.01,
                "median_spread": 0.008,
                "p90_spread": 0.015,
                "p95_spread": 0.02,
            }
        )
    )
    assert r["result"] == "COST_TABLE_SCHEMA_VALID"


def test_missing_claim_scope_fails() -> None:
    t = _table()
    del t["claim_scope"]
    with pytest.raises(CostSchemaError):
        validate_cost_table(t)


def test_wrong_claim_scope_fails() -> None:
    with pytest.raises(CostSchemaError):
        validate_cost_table(_table(claim_scope="live_fill_validity"))


def test_unsupported_session_fails() -> None:
    with pytest.raises(CostSchemaError):
        validate_cost_table(_table(entry={"session": "sydney"}))


def test_wrong_padding_or_cell_fails() -> None:
    with pytest.raises(CostSchemaError):
        validate_cost_table(_table(execution_padding_pip=0.1))
    with pytest.raises(CostSchemaError):
        validate_cost_table(_table(flat_slippage_cell_pip=1.0))
