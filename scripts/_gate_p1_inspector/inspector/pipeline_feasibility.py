"""Static pipeline feasibility (PR-B.2 — plan §7).

Answers, WITHOUT execution: which source references relevant to a later ML
harness are statically present, whether the committed PR-B.1 metadata evidence
exists for all candidate spans, and which prerequisites remain blocked. It
executes no pipeline / data loader / model / backtest, reads no raw data, and
computes no labels / features / trades / metrics. It only AST-parses source
text and reads committed PR-B.1 metadata JSON.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any

from ..b2_constants import (
    PIPE_NEW_EPOCH_NOT_AUTHORISED,
    PIPE_PATH_OBSERVED,
    PIPE_PATH_PARTIAL,
    PIPE_PATH_UNRESOLVED,
    PIPE_RETENTION_PROBE_REQUIRED,
    PIPELINE_REFERENCE_TARGETS,
    PR_B1_EVIDENCE_DIRS,
    PR_B1_EXPECTED_OUTCOME,
    PR_B1_EXPECTED_RETENTION,
)


def _defines_name(source_text: str, name: str) -> bool:
    """True if the module statically defines a function / class / assignment `name`."""
    try:
        tree = ast.parse(source_text)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == name:
                return True
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return True
    return False


def _reference_scan(repo_root: Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for relpath, target in PIPELINE_REFERENCE_TARGETS:
        path = repo_root / relpath
        if not path.exists():
            results.append({"source_path": relpath, "target": target, "found": False})
            continue
        found = _defines_name(path.read_text(encoding="utf-8"), target)
        results.append({"source_path": relpath, "target": target, "found": found})
    return results


def _pr_b1_evidence_check(repo_root: Path) -> list[dict[str, Any]]:
    """Read-only check that committed PR-B.1 metadata evidence exists per span."""
    checks: list[dict[str, Any]] = []
    for span, reldir in PR_B1_EVIDENCE_DIRS.items():
        report_path = repo_root / reldir / "gate_p1_report.json"
        entry: dict[str, Any] = {
            "span": span,
            "evidence_path": f"{reldir}/gate_p1_report.json",
            "present": report_path.exists(),
        }
        if report_path.exists():
            try:
                payload = json.loads(report_path.read_text(encoding="utf-8"))
                entry["top_level_outcome"] = payload.get("top_level_outcome")
                per = payload.get("per_candidate_summary") or []
                entry["retention_classification"] = (
                    per[0].get("retention_classification") if per else None
                )
                entry["outcome_matches_expected"] = (
                    payload.get("top_level_outcome") == PR_B1_EXPECTED_OUTCOME
                )
            except (ValueError, OSError):
                entry["parse_error"] = True
        checks.append(entry)
    return checks


def build_pipeline_feasibility(repo_root: str | Path) -> dict[str, Any]:
    """Build the static pipeline feasibility report (metadata only)."""
    repo_root = Path(repo_root)
    references = _reference_scan(repo_root)
    evidence = _pr_b1_evidence_check(repo_root)

    refs_found = sum(1 for r in references if r["found"])
    all_refs_found = refs_found == len(references) and references
    all_evidence_present = bool(evidence) and all(e["present"] for e in evidence)
    all_evidence_expected = all(
        e.get("outcome_matches_expected") for e in evidence if e.get("present")
    )

    if all_refs_found and all_evidence_present and all_evidence_expected:
        path_label = PIPE_PATH_OBSERVED
    elif refs_found > 0 or any(e["present"] for e in evidence):
        path_label = PIPE_PATH_PARTIAL
    else:
        path_label = PIPE_PATH_UNRESOLVED

    return {
        "method": "ast_source_and_committed_pr_b1_metadata_only",
        "pipeline_executed": False,
        "raw_data_read": False,
        "features_generated": False,
        "labels_generated": False,
        "model_inputs_constructed": False,
        "trading_metrics_computed": False,
        "static_reference_scan": references,
        "pr_b1_evidence_check": evidence,
        "static_path_label": path_label,
        "blocking_labels": [
            PIPE_RETENTION_PROBE_REQUIRED,
            PIPE_NEW_EPOCH_NOT_AUTHORISED,
        ],
        "statements": [
            "feasibility is static / source-only",
            "no pipeline execution occurred",
            "no new epoch dataset was constructed",
            "no model-ready dataset was constructed",
            "no byte-admissibility approval was granted",
            "no T2 retention execution occurred",
            "no production routing decision was made",
        ],
        "summary": {
            "references_found": refs_found,
            "references_total": len(references),
            "pr_b1_evidence_all_present": all_evidence_present,
            "pr_b1_evidence_all_expected_outcome": bool(all_evidence_expected),
            "pr_b1_expected_outcome": PR_B1_EXPECTED_OUTCOME,
            "pr_b1_expected_retention": PR_B1_EXPECTED_RETENTION,
        },
    }
