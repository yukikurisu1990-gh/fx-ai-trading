"""PR-B.1 authority resolution tests (plan §6)."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts._gate_p1_inspector.authority import pair_universe as pu
from scripts._gate_p1_inspector.authority import schema as sa
from scripts._gate_p1_inspector.b1_constants import PROTOCOL_REQUIRED_FIELDS

REPO_ROOT = Path(__file__).resolve().parents[2]

_EXPECTED_PAIRS = {
    "EUR_USD", "GBP_USD", "AUD_USD", "NZD_USD", "USD_CHF",
    "USD_CAD", "EUR_GBP", "USD_JPY", "EUR_JPY", "GBP_JPY",
    "AUD_JPY", "NZD_JPY", "CHF_JPY", "EUR_CHF", "EUR_AUD",
    "EUR_CAD", "AUD_NZD", "AUD_CAD", "GBP_AUD", "GBP_CHF",
}  # fmt: skip


def test_pair_universe_resolved_deterministically():
    result = pu.resolve_pair_universe(REPO_ROOT)
    assert result.outcome in (pu.OUTCOME_OK, pu.OUTCOME_OK_SECONDARY_UNAVAILABLE)
    assert result.pairs is not None
    assert len(result.pairs) == 20
    assert set(result.pairs) == _EXPECTED_PAIRS
    # Hash is deterministic across calls.
    again = pu.resolve_pair_universe(REPO_ROOT)
    assert result.pair_universe_hash == again.pair_universe_hash


def test_pair_universe_resolution_uses_ast_not_import():
    before = set(sys.modules)
    pu.resolve_pair_universe(REPO_ROOT)
    after = set(sys.modules)
    new_production = [
        m for m in (after - before) if m.startswith(("scripts.stage", "fx_ai_trading", "src."))
    ]
    assert new_production == []


def test_pair_universe_unparseable_canonical_halts(tmp_path):
    # A repo root with no canonical source yields the canonical-HALT outcome.
    result = pu.resolve_pair_universe(tmp_path)
    assert result.outcome == pu.OUTCOME_INTEGRITY_HALT_CANONICAL_UNPARSEABLE
    assert result.pairs is None


def test_schema_authority_resolved_via_ast():
    result = sa.resolve_schema_authority(REPO_ROOT)
    assert result.outcome == sa.OUTCOME_OK
    assert set(result.required_fields) == set(PROTOCOL_REQUIRED_FIELDS)
    assert result.source["sha256"] is not None


def test_schema_authority_missing_source_halts(tmp_path):
    result = sa.resolve_schema_authority(tmp_path)
    assert result.outcome == sa.OUTCOME_INTEGRITY_HALT_SOURCE_UNPARSEABLE
    assert result.required_fields is None
