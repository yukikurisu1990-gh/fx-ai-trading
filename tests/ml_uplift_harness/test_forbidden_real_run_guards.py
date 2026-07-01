"""ML uplift harness forbidden-access / no-real-run guard tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from scripts.ml_uplift_harness.artifacts import validate_artifact_root
from scripts.ml_uplift_harness.contracts import HarnessContractError

REPO_ROOT = Path(__file__).resolve().parents[2]
HARNESS_PKG = REPO_ROOT / "scripts" / "ml_uplift_harness"

_PRODUCTION_IMPORT_PREFIXES = ("scripts.stage", "scripts.fetch_oanda", "src", "fx_ai_trading")
_FORBIDDEN_RUNTIME_MODULES = ("socket", "urllib", "http.client", "subprocess", "requests")
_MODEL_LIBS = ("lightgbm", "xgboost", "catboost", "sklearn", "torch")


@pytest.mark.parametrize(
    "bad",
    [
        "data/candles",
        "data/candles_EUR_USD_M1_365d_BA.jsonl",
        "somewhere/oanda_archive/x",
        "artifacts/gate_p1_pr_b/firstrun_365d_ba",
        "x/y.parquet",
        "x/y.csv",
    ],
)
def test_raw_data_and_archive_paths_rejected(tmp_path, bad):
    with pytest.raises(HarnessContractError):
        validate_artifact_root(tmp_path / bad)


def _collect_imports(text: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not (node.level or 0):
            names.add(node.module)
    return names


def test_harness_imports_no_production_or_network_or_model_libs():
    offenders: list[str] = []
    for py in sorted(HARNESS_PKG.rglob("*.py")):
        imports = _collect_imports(py.read_text(encoding="utf-8"))
        for name in imports:
            if any(name.startswith(p) for p in _PRODUCTION_IMPORT_PREFIXES):
                offenders.append(f"{py.name}:{name}")
            if name in _FORBIDDEN_RUNTIME_MODULES or name.split(".", 1)[0] in _MODEL_LIBS:
                offenders.append(f"{py.name}:{name}")
    assert offenders == [], f"harness must not import {offenders}"


def test_harness_does_not_read_repo_data_dir(tmp_path, synthetic_contract):
    # A synthetic run writes only under the tmp output root; the repo data/ dir
    # is never referenced by the produced report.
    from scripts.ml_uplift_harness.synthetic_runner import run_synthetic_smoke

    report = run_synthetic_smoke(synthetic_contract, tmp_path, code_sha="test-sha")
    import json

    text = json.dumps(report)
    assert "/data/" not in text and "\\data\\" not in text
    assert report["non_authorisation_flags"]["real_data_read"] is False
