"""Foundation T2 forbidden-access / no-cloud-no-secret guard tests."""

from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts.foundation_t2 import scrub

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "scripts" / "foundation_t2"

_FORBIDDEN_IMPORTS = ("scripts.stage", "scripts.fetch_oanda", "src", "fx_ai_trading")
_NETWORK_MODEL = {"socket", "urllib", "http", "requests", "boto3", "torch", "lightgbm", "sklearn"}


def _imports(text: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Import):
            names.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not (node.level or 0):
            names.add(node.module)
    return names


def test_harness_imports_no_production_network_model_libs():
    offenders = []
    for py in sorted(PKG.rglob("*.py")):
        for name in _imports(py.read_text(encoding="utf-8")):
            top = name.split(".", 1)[0]
            if any(name.startswith(p) for p in _FORBIDDEN_IMPORTS) or top in _NETWORK_MODEL:
                offenders.append(f"{py.name}:{name}")
    assert offenders == [], f"harness must not import {offenders}"


def test_harness_does_not_read_env_or_network():
    # No os.environ access and no boto3/http client construction in the package.
    for py in sorted(PKG.rglob("*.py")):
        text = py.read_text(encoding="utf-8")
        assert "os.environ" not in text, f"{py.name} reads os.environ"
        assert "boto3" not in text and "urlopen" not in text, f"{py.name} network access"


def test_cli_run_produces_clean_metadata_only_evidence(tmp_path):
    from scripts.run_foundation_t2_roundtrip import main

    out = tmp_path / "out"
    rc = main(
        [
            "--run-id",
            "guard-run",
            "--output-root",
            str(out),
            "--git-sha",
            "deadbeef",
            "--base-master-sha",
            "cafe",
            "--generated-at",
            "2026-07-02T00:00:00Z",
            "--authorisation-ref",
            "guard-test",
        ]
    )
    assert rc == 0
    report = json.loads((out / "guard-run" / "t2_roundtrip_report.json").read_text())
    # Real deposit not performed; no round-trip claimed.
    assert report["real_cloud_deposit_status"] == "T2_EXECUTION_STOPPED_BEFORE_DEPOSIT"
    assert report["retention_probe_status"] == "RETENTION_PROBE_REMAINS_UNRESOLVED"
    for s in report["per_span_status"]:
        assert s["deposit_status"] == "NOT_PERFORMED"
    # Required explicit did-not-happen statuses are present.
    statuses = set(report["statuses"])
    for required in (
        "T2_EXECUTION_STOPPED_BEFORE_DEPOSIT",
        "T2_CREDENTIALS_UNAVAILABLE",
        "T2_DEPOSIT_NOT_PERFORMED",
        "T2_RESTORE_NOT_PERFORMED",
        "T2_ROUNDTRIP_NOT_PERFORMED",
        "RETENTION_PROBE_REMAINS_UNRESOLVED",
        "BYTE_ADMISSIBILITY_NOT_APPROVED",
        "NEW_EPOCH_NOT_AUTHORISED",
        "ML_STEP4_NOT_AUTHORISED",
    ):
        assert required in statuses, f"missing required status {required}"
    # Forbidden success tokens must NOT appear anywhere (no real round-trip).
    blob = json.dumps(report)
    for forbidden in (
        "T2_ROUNDTRIP_MATCH_OBSERVED",
        "T2_SPAN_365D_BA_ROUNDTRIP_OBSERVED",
        "T2_SPAN_730D_BA_ROUNDTRIP_OBSERVED",
        "T2_SPAN_3650D_BA_ROUNDTRIP_OBSERVED",
        "T2_EXECUTION_ATTEMPTED_WITH_AUTHORISATION",
    ):
        assert forbidden not in blob, f"forbidden success token leaked: {forbidden}"
    # Evidence is clean (scrubber ran at write time; re-scan here).
    assert scrub.scan_payload(report) == []
    clean = json.loads((out / "guard-run" / "evidence_cleanliness_report.json").read_text())
    assert clean["clean"] is True
