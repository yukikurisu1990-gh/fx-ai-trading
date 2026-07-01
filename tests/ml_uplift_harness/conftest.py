"""Shared synthetic-config builder for ML uplift harness tests.

Configs are built inline (not committed) so no file under tests/fixtures or
artifacts/ can be mistaken for real experiment evidence.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

_SYNTHETIC_CONTRACT: dict[str, Any] = {
    "experiment_id": "synthetic-exp-001",
    "purpose": "harness scaffolding validation (synthetic only)",
    "generated_at": "2026-07-01T00:00:00Z",
    "code_sha": "synthetic-code-sha",
    "contract_version": "ml-uplift-harness.v1",
    "data_span": {
        "candidate_span_id": "365d_BA",
        "synthetic_fixture": True,
        "real_data_authorised": False,
    },
    "feature_set": {
        "feature_set_id": "fs-synth-1",
        "feature_family": ["multi_tf_trend", "volatility_regime", "session"],
    },
    "label_contract": {
        "label_contract_id": "lc-synth-1",
        "horizon": 30,
        "barrier_type": "triple_barrier_atr",
        "cost_inclusion": True,
    },
    "cost_contract": {
        "spread_assumption": 0.0,
        "slippage_stress": "conservative_placeholder",
        "commission_hurdle": 0.0,
    },
    "validation_split": {
        "split_type": "walk_forward_purged_embargo",
        "walk_forward_folds": 5,
        "purged": True,
        "embargo_bars": 10,
    },
    "model_config": {
        "model_family": "lightgbm_placeholder",
        "hyperparameters": {"num_leaves": 31},
        "random_seed": 7,
    },
    "output_report": {
        "artifact_root": "PLACEHOLDER_SET_BY_TEST",
        "report_files": ["synthetic_report.json", "report.md"],
        "metrics_schema": ["net_pips_after_cost", "per_trade_expectancy_name_only"],
    },
    "non_authorisation": {},
}


@pytest.fixture
def synthetic_contract():
    """Return a deep copy of a valid synthetic contract dict."""
    return copy.deepcopy(_SYNTHETIC_CONTRACT)
