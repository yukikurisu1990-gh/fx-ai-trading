"""PR-B.2 static inspection orchestrator (dependency inventory + pipeline feasibility).

Wires the two static inspections and emits derived-metadata-only reports. Reads
only source text (AST) and committed PR-B.1 metadata JSON; executes nothing;
computes no trading metric; changes no PR-B.1 outcome. First-run PASS remains
structurally unreachable (the PR-B.2 outcome vocabulary contains no PASS).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .b2_constants import (
    OUTCOME_INSUFFICIENT_STATIC_EVIDENCE,
    OUTCOME_OBSERVED_RETENTION_PROBE_REQUIRED,
    OUTCOME_PARTIAL_STATIC_FEASIBILITY,
    PIPE_PATH_OBSERVED,
    PIPE_PATH_UNRESOLVED,
    PR_B1_EVIDENCE_SPANS,
    PR_B1_EXPECTED_OUTCOME,
    PR_B1_EXPECTED_RETENTION,
)
from .inspector import dependency_inventory as dep_mod
from .inspector import pipeline_feasibility as pipe_mod
from .report import b2_writers

_REPORT_FILENAME = "gate_p1_pr_b2_report.json"
_DEP_FILENAME = "dependency_inventory.json"
_PIPE_FILENAME = "pipeline_feasibility.json"
_MARKDOWN_FILENAME = "report.md"


def _resolve_b2_outcome(dependency: dict[str, Any], pipeline: dict[str, Any]) -> str:
    """Conservative top-level PR-B.2 outcome. PASS is not in the vocabulary."""
    path_label = pipeline["static_path_label"]
    evidence_present = pipeline["summary"]["pr_b1_evidence_all_present"]
    evidence_expected = pipeline["summary"]["pr_b1_evidence_all_expected_outcome"]
    inspector_clean = dependency["inspector_self_check"]["inspector_free_of_production_imports"]

    if path_label == PIPE_PATH_UNRESOLVED or not inspector_clean:
        return OUTCOME_INSUFFICIENT_STATIC_EVIDENCE
    if path_label == PIPE_PATH_OBSERVED and evidence_present and evidence_expected:
        # Static surface observed; the binding blocker remains retention probe.
        return OUTCOME_OBSERVED_RETENTION_PROBE_REQUIRED
    return OUTCOME_PARTIAL_STATIC_FEASIBILITY


def _render_markdown(report_id: str, outcome: str, dependency: dict, pipeline: dict) -> str:
    lines = [
        "# Gate P1 PR-B.2 static inspection report",
        "",
        f"- report_id: `{report_id}`",
        "- pr_b_stage: PR-B.2 (dependency inventory + pipeline feasibility)",
        f"- top_level_outcome: `{outcome}`",
        "",
        "## Method",
        "",
        "Static, AST/source-only + committed PR-B.1 metadata only. No pipeline "
        "execution, no raw data read, no model / backtest / sweep / replay, no "
        "labels / features / trades / trading metrics. No byte-admissibility "
        "approval, no T2 retention execution, no new-epoch construction, no "
        "production routing decision.",
        "",
        "## Dependency inventory (summary)",
        "",
        f"- consumers inspected: {dependency['summary']['consumer_count']}",
        f"- distinct labels: {', '.join(dependency['summary']['distinct_labels'])}",
        f"- forbidden-to-execute-in-Gate-P1 deps: "
        f"{dependency['summary']['forbidden_to_execute_count']}",
        f"- inspector free of production imports: "
        f"{dependency['inspector_self_check']['inspector_free_of_production_imports']}",
        "",
        "## Pipeline feasibility (summary)",
        "",
        f"- static references found: {pipeline['summary']['references_found']} / "
        f"{pipeline['summary']['references_total']}",
        f"- PR-B.1 evidence all present: {pipeline['summary']['pr_b1_evidence_all_present']}",
        f"- static_path_label: `{pipeline['static_path_label']}`",
        "",
        "## PR-B.1 span outcomes (unchanged by PR-B.2)",
        "",
    ]
    for span in PR_B1_EVIDENCE_SPANS:
        lines.append(f"- {span} = {PR_B1_EXPECTED_OUTCOME} / {PR_B1_EXPECTED_RETENTION}")
    lines += [
        "",
        "First-run feasible-for-construction remains structurally unreachable; "
        "PR-B.2 makes no byte-admissibility, T2, new-epoch, Tier-1, or production "
        "claim.",
        "",
    ]
    return "\n".join(lines)


def run_b2_inspection(
    report_dir: str | Path,
    report_id: str,
    *,
    repo_root: str | Path,
    clean_code_sha: str | None = None,
    base_master_sha: str | None = None,
    generated_at: str | None = None,
) -> Path:
    """Run PR-B.2 static inspections and emit artifacts; return the report path."""
    report_dir = Path(report_dir)
    dependency = dep_mod.build_dependency_inventory(repo_root)
    pipeline = pipe_mod.build_pipeline_feasibility(repo_root)
    outcome = _resolve_b2_outcome(dependency, pipeline)
    b2_writers.validate_b2_outcome(outcome)

    b2_writers.write_b2_json(
        report_dir, _DEP_FILENAME, {**dependency, **b2_writers.b2_metadata_block()}
    )
    b2_writers.write_b2_json(
        report_dir, _PIPE_FILENAME, {**pipeline, **b2_writers.b2_metadata_block()}
    )

    markdown = _render_markdown(report_id, outcome, dependency, pipeline)
    b2_writers.write_b2_markdown(report_dir, _MARKDOWN_FILENAME, markdown)

    pr_b1_span_status = {
        span: {
            "top_level_outcome": PR_B1_EXPECTED_OUTCOME,
            "retention_classification": PR_B1_EXPECTED_RETENTION,
        }
        for span in PR_B1_EVIDENCE_SPANS
    }
    report_payload = {
        "report_id": report_id,
        "generated_at": generated_at,
        "git_commit_sha": clean_code_sha,
        "base_master_sha": base_master_sha,
        "top_level_outcome": outcome,
        "pr_b1_evidence_paths_consumed": [
            e["evidence_path"] for e in pipeline["pr_b1_evidence_check"]
        ],
        "dependency_inventory_summary": dependency["summary"],
        "pipeline_feasibility_summary": pipeline["summary"],
        "pr_b1_span_status_unchanged": pr_b1_span_status,
        "first_run_pass_structurally_unreachable": True,
        "notice": (
            "PR-B.2 static dependency inventory + pipeline feasibility. AST/source "
            "and committed PR-B.1 metadata only. No pipeline / model / backtest "
            "execution, no raw data, no trading metrics. No byte-admissibility "
            "approval, no T2 authorisation, no new-epoch adoption, no production "
            "claim. PR-B.1 span outcomes are unchanged."
        ),
        **b2_writers.b2_metadata_block(),
    }
    # gate_p1_pr_b2_report.json is written last; its presence signals completion.
    return b2_writers.write_b2_json(report_dir, _REPORT_FILENAME, report_payload)


def load_report(report_dir: str | Path) -> dict[str, Any]:
    return json.loads((Path(report_dir) / _REPORT_FILENAME).read_text(encoding="utf-8"))
