"""PR-B.0 stub report schema (plan §7, §11).

PR-B.0 emits a single clearly-marked stub ``gate_p1_report.json`` plus a
``report.md``. The stub carries NO inspection content: no per-candidate
summary, no retention classification, no coverage, no byte-admissibility, and
no top-level feasibility verdict. Its only top-level outcome literal is
``STUB_NO_INSPECTION_PERFORMED`` (added in PR-B.0, removed by PR-B.1).
"""

from __future__ import annotations

from typing import Any

from ..tolerances import STUB_TOP_LEVEL_OUTCOME
from .common_metadata import common_metadata_block

# Keys that, by contract, must NEVER appear in a PR-B.0 stub report — their
# presence would risk the stub being mistaken for a real Gate P1 inspection
# result. Asserted by tests and by the writer.
FORBIDDEN_STUB_KEYS: frozenset[str] = frozenset(
    {
        "per_candidate_summary",
        "retention_classification",
        "retention_substatus",
        "top_level_outcome_real",
        "coverage",
        "byte_admissibility",
        "dependency_inventory",
        "pipeline_feasibility",
        "candidate_retention_options_requiring_later_authorisation",
        "t2_authorisation",
    }
)


def build_stub_report(report_id: str, *, first_run_mode: bool) -> dict[str, Any]:
    """Build the PR-B.0 stub ``gate_p1_report.json`` payload."""
    report: dict[str, Any] = {
        "report_id": report_id,
        "first_run_mode": first_run_mode,
        "top_level_outcome": STUB_TOP_LEVEL_OUTCOME,
        "inspection_performed": False,
        "pr_b1_implemented": False,
        "pr_b2_implemented": False,
        "notice": (
            "PR-B.0 infrastructure stub. No Gate P1 inspection was performed. "
            "No raw data, archive, credential, network, broker, or quote-feed "
            "access occurred. This artifact carries no feasibility, coverage, "
            "retention, dependency, pipeline, or byte-admissibility result and "
            "no T2 authorisation. The real inspection is PR-B.1 / PR-B.2, each "
            "separately authorised and NOT implemented here."
        ),
    }
    report.update(common_metadata_block())
    return report
