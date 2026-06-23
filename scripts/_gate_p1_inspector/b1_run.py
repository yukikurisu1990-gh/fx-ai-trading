"""PR-B.1 first-run read-only inspection orchestrator.

Wires authority -> raw inventory -> coverage -> retention -> resolver ->
report writers. Read-only over candidate raw files; AST/source-only over
authority sources; derived-metadata-only output. Dependency inventory and
pipeline feasibility (PR-B.2) are NOT performed. First-run PASS is
structurally unreachable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .authority import pair_universe as pu
from .authority import schema as sa
from .b1_constants import CANDIDATE_SPANS
from .inspector import coverage as coverage_mod
from .inspector import raw_inventory as raw_mod
from .inspector import resolver as resolver_mod
from .inspector import retention as retention_mod
from .report import b1_writers

_REPORT_FILENAME = "gate_p1_report.json"
_MARKDOWN_FILENAME = "report.md"


def _candidate_id(span_label: str) -> str:
    return f"{span_label}_BA"


def _render_markdown(
    report_id: str,
    top_level: str,
    per_candidate: list[dict[str, Any]],
    span_scope: dict[str, str],
) -> str:
    lines = [
        "# Gate P1 PR-B.1 first-run inspection report",
        "",
        f"- report_id: `{report_id}`",
        "- pr_b_stage: PR-B.1 (read-only inspection)",
        "- first_run_mode: true",
        f"- top_level_outcome: `{top_level}`",
        "",
        "## First-run binding",
        "",
        "A feasible-for-construction outcome is structurally unreachable on the "
        "first run. This report makes no byte-admissibility claim and grants no "
        "T2 authorisation.",
        "",
        "## Candidate-span scope",
        "",
        "The top_level_outcome above is scoped to the INSPECTED span(s) only; "
        "spans marked NOT_INSPECTED_IN_THIS_PR are neither feasible, infeasible, "
        "complete, nor verified.",
        "",
        "| span | scope |",
        "| --- | --- |",
        *[f"| {span} | {scope} |" for span, scope in sorted(span_scope.items())],
        "",
        "## Per-candidate summary",
        "",
        "| candidate | outcome | retention_substatus |",
        "| --- | --- | --- |",
    ]
    for row in per_candidate:
        lines.append(
            f"| {row['candidate_id']} | {row['candidate_status']} | {row['retention_substatus']} |"
        )
    lines += [
        "",
        "## Not implemented here",
        "",
        "- PR-B.2 (dependency inventory + pipeline feasibility): NOT implemented.",
        "- Dependency inventory: NOT performed.",
        "- Pipeline feasibility: NOT performed.",
        "- T2 execution (retention deposit / round-trip): NOT authorised.",
        "",
        "Each requires independent explicit authorisation (plan §11).",
        "",
    ]
    return "\n".join(lines)


def _span_scope(inspected: tuple[str, ...]) -> dict[str, str]:
    """Map every designed Gate P1 span to INSPECTED / NOT_INSPECTED in this PR."""
    inspected_set = set(inspected)
    scope: dict[str, str] = {}
    for span in CANDIDATE_SPANS:
        scope[span] = (
            "INSPECTED_IN_THIS_PR" if span in inspected_set else "NOT_INSPECTED_IN_THIS_PR"
        )
    # Include any inspected span outside the canonical designed set.
    for span in inspected:
        scope.setdefault(span, "INSPECTED_IN_THIS_PR")
    return scope


def run_b1_inspection(
    report_dir: str | Path,
    report_id: str,
    *,
    data_dir: str | Path,
    repo_root: str | Path,
    candidate_spans: tuple[str, ...] = CANDIDATE_SPANS,
    first_run_mode: bool = True,
    clean_code_sha: str | None = None,
) -> Path:
    """Run the PR-B.1 inspection and emit artifacts; return the report path."""
    report_dir = Path(report_dir)
    pair_result = pu.resolve_pair_universe(repo_root)
    schema_result = sa.resolve_schema_authority(repo_root)
    pairs = pair_result.pairs or []

    per_candidate: list[dict[str, Any]] = []
    candidate_outcomes: list[resolver_mod.CandidateOutcome] = []

    for span in candidate_spans:
        cid = _candidate_id(span)
        candidate = raw_mod.inspect_candidate(data_dir, pairs, span)
        files = candidate["files"]
        coverage = coverage_mod.derive_coverage(span, files)
        retention = retention_mod.assess_retention(
            span, files, first_run_mode=first_run_mode, repo_root=repo_root
        )
        outcome = resolver_mod.resolve_candidate(
            cid,
            pair_outcome=pair_result.outcome,
            schema_outcome=schema_result.outcome,
            files=files,
            pairs=pairs,
            retention_classification=retention["retention_classification"],
            first_run_mode=first_run_mode,
        )
        candidate_outcomes.append(outcome)

        b1_writers.write_b1_json(
            report_dir,
            f"raw_inventory_{cid}.json",
            {
                "candidate_id": cid,
                "nominal_span_label": span,
                "pair_universe": pairs,
                "pair_universe_hash": pair_result.pair_universe_hash,
                "pair_universe_source_a": pair_result.source_a,
                "pair_universe_source_b": pair_result.source_b,
                "schema_authority": {
                    "source": schema_result.source,
                    "required_fields": schema_result.required_fields,
                    "informational_extensions": schema_result.informational_extensions,
                    "outcome": schema_result.outcome,
                },
                "files": files,
                **b1_writers.b1_metadata_block(),
            },
        )
        b1_writers.write_b1_json(
            report_dir, f"coverage_{cid}.json", {**coverage, **b1_writers.b1_metadata_block()}
        )
        b1_writers.write_b1_json(
            report_dir,
            f"retention_feasibility_{cid}.json",
            {**retention, **b1_writers.b1_metadata_block()},
        )

        per_candidate.append(
            {
                "candidate_id": cid,
                "nominal_span_label": span,
                "candidate_status": outcome.outcome,
                "retention_classification": retention["retention_classification"],
                "retention_substatus": outcome.retention_substatus,
                "reason_codes": outcome.reason_codes,
            }
        )

    top_level = resolver_mod.resolve_top_level(candidate_outcomes, first_run_mode=first_run_mode)
    b1_writers.validate_top_level_outcome(top_level)

    span_scope = _span_scope(candidate_spans)
    markdown = _render_markdown(report_id, top_level, per_candidate, span_scope)
    b1_writers.write_b1_markdown(report_dir, _MARKDOWN_FILENAME, markdown)

    report_payload = {
        "report_id": report_id,
        "first_run_mode": first_run_mode,
        "top_level_outcome": top_level,
        "git_commit_sha": clean_code_sha,
        "candidate_spans_inspected": list(candidate_spans),
        "candidate_spans_designed": list(CANDIDATE_SPANS),
        "candidate_span_scope": span_scope,
        "outcome_scope_note": (
            "top_level_outcome is scoped to the inspected candidate span(s) only. "
            "Spans marked NOT_INSPECTED_IN_THIS_PR are neither feasible, "
            "infeasible, complete, nor verified by this report."
        ),
        "pair_universe_outcome": pair_result.outcome,
        "schema_authority_outcome": schema_result.outcome,
        "per_candidate_summary": per_candidate,
        "notice": (
            "PR-B.1 first-run read-only inspection. Derived metadata only; no raw "
            "rows, credentials, or model outputs. No byte-admissibility approval, "
            "no new-epoch adoption, no T3/T4 formal verification. PR-B.2 "
            "(dependency + pipeline) NOT implemented; T2 execution NOT authorised."
        ),
        **b1_writers.b1_metadata_block(),
    }
    # gate_p1_report.json is written last; its presence signals completion.
    return b1_writers.write_b1_json(report_dir, _REPORT_FILENAME, report_payload)


def load_report(report_dir: str | Path) -> dict[str, Any]:
    """Convenience reader for the emitted report (tests / callers)."""
    return json.loads((Path(report_dir) / _REPORT_FILENAME).read_text(encoding="utf-8"))
