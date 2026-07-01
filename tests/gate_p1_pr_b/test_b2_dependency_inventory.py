"""PR-B.2 static dependency inventory tests."""

from __future__ import annotations

import sys
from pathlib import Path

from scripts._gate_p1_inspector.b2_constants import (
    DEP_FORBIDDEN_TO_EXECUTE,
    DEP_OBSERVED,
    DEPENDENCY_LABELS,
)
from scripts._gate_p1_inspector.inspector import dependency_inventory as dep

REPO_ROOT = Path(__file__).resolve().parents[2]

_SYNTHETIC_CONSUMER = """
import json
import numpy as np
import pandas as pd
from scripts.stage23_0a_build_outcome_dataset import load_m1_ba
import lightgbm
"""


def _write(tmp_path: Path, relpath: str, text: str) -> Path:
    p = tmp_path / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_collect_imports_ast_only_and_sorted():
    names = dep._collect_imports(_SYNTHETIC_CONSUMER)
    assert names == sorted(names)
    assert "json" in names
    assert "numpy" in names
    assert "lightgbm" in names
    assert "scripts.stage23_0a_build_outcome_dataset" in names


def test_classification_stdlib_thirdparty_internal(tmp_path):
    _write(tmp_path, "scripts/synthetic_consumer.py", _SYNTHETIC_CONSUMER)
    inv = dep.inventory_consumer(tmp_path, "scripts/synthetic_consumer.py")
    kinds = {d["module"]: d["kind"] for d in inv["dependencies"]}
    assert kinds["json"] == "stdlib"
    assert kinds["numpy"] == "third_party"
    assert kinds["scripts.stage23_0a_build_outcome_dataset"] == "internal"


def test_forbidden_execution_surface_labelled(tmp_path):
    _write(tmp_path, "scripts/synthetic_consumer.py", _SYNTHETIC_CONSUMER)
    inv = dep.inventory_consumer(tmp_path, "scripts/synthetic_consumer.py")
    labels = {d["module"]: d["label"] for d in inv["dependencies"]}
    assert labels["lightgbm"] == DEP_FORBIDDEN_TO_EXECUTE  # model lib: never execute in Gate P1
    assert labels["json"] == DEP_OBSERVED


def test_missing_consumer_handled(tmp_path):
    inv = dep.inventory_consumer(tmp_path, "scripts/does_not_exist.py")
    assert inv["present"] is False
    assert inv["dependencies"] == []


def test_build_inventory_no_import_execution_and_self_clean():
    inventory = dep.build_dependency_inventory(REPO_ROOT)
    assert inventory["import_execution_performed"] is False
    assert inventory["package_manager_invoked"] is False
    # The inspector package must import no production trading module.
    assert inventory["inspector_self_check"]["inspector_free_of_production_imports"] is True
    assert inventory["inspector_self_check"]["offending_imports"] == []


def test_build_inventory_labels_are_controlled_vocab():
    inventory = dep.build_dependency_inventory(REPO_ROOT)
    for consumer in inventory["consumers"]:
        for d in consumer["dependencies"]:
            assert d["label"] in DEPENDENCY_LABELS


def test_dependency_inventory_did_not_import_production(monkeypatch):
    # Guard against accidental import: run the inventory, then assert no new
    # production module entered sys.modules as a result.
    before = {m for m in sys.modules if m.startswith(("scripts.stage", "fx_ai_trading", "src."))}
    dep.build_dependency_inventory(REPO_ROOT)
    after = {m for m in sys.modules if m.startswith(("scripts.stage", "fx_ai_trading", "src."))}
    assert after - before == set()
