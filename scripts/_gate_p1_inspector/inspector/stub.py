"""Stub inspector for PR-B.0 (plan §11).

Performs NO inspection. It reads no candidate data, computes no SHA-256 over
any candidate file, derives no coverage, classifies no retention, and makes no
feasibility decision. It exists solely to exercise the guarded execution
envelope end-to-end and emit a clearly-marked stub report.
"""

from __future__ import annotations

from pathlib import Path

from ..report.schema import build_stub_report
from ..report.writers import write_json_artifact, write_markdown_artifact

_STUB_REPORT_FILENAME = "gate_p1_report.json"
_STUB_MARKDOWN_FILENAME = "report.md"


def _render_markdown(report_id: str, *, first_run_mode: bool) -> str:
    first_run_line = (
        "First-run binding: a real feasibility verdict is not reachable; this is a PR-B.0 stub."
        if first_run_mode
        else "Stub mode: no inspection performed."
    )
    return (
        f"# Gate P1 PR-B.0 stub report\n\n"
        f"- report_id: `{report_id}`\n"
        f"- pr_b_stage: PR-B.0 (infrastructure only)\n"
        f"- inspection_performed: false\n"
        f"- {first_run_line}\n\n"
        "## Non-scope\n\n"
        "This run performed NO Gate P1 inspection. No raw data, OANDA archive, "
        "credential, environment variable, network endpoint, broker, quote "
        "feed, or production runtime state was accessed. This report carries no "
        "feasibility, coverage, retention, dependency, pipeline, or byte "
        "admissibility result and grants no T2 authorisation.\n\n"
        "## Not implemented here\n\n"
        "- PR-B.1 (authority + raw inventory + coverage + retention + resolver): "
        "NOT implemented.\n"
        "- PR-B.2 (dependency inventory + pipeline feasibility): NOT "
        "implemented.\n\n"
        "Each subsequent stage requires independent explicit authorisation "
        "(plan §11).\n"
    )


def run_stub_inspection(report_dir: str | Path, report_id: str, *, first_run_mode: bool) -> Path:
    """Emit the PR-B.0 stub report under ``report_dir``; return its path."""
    report_dir = Path(report_dir)
    payload = build_stub_report(report_id, first_run_mode=first_run_mode)
    markdown = _render_markdown(report_id, first_run_mode=first_run_mode)
    write_markdown_artifact(report_dir, _STUB_MARKDOWN_FILENAME, markdown)
    # gate_p1_report.json is written last so its presence signals completion.
    return write_json_artifact(report_dir, _STUB_REPORT_FILENAME, payload)
