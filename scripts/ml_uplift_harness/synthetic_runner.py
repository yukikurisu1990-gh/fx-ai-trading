"""Synthetic-only smoke runner for the ML uplift harness.

Validates a contract, captures provenance, plans an artifact manifest, and
writes a clearly-marked SYNTHETIC-ONLY report. It trains no model, reads no
real data, and computes no trading metric. It is the no-real-run mechanics
check for the harness.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .artifacts import plan_artifact_manifest, resolve_experiment_dir
from .contracts import HarnessContractError, contract_from_dict
from .provenance import capture_provenance
from .reporting import build_synthetic_report, write_markdown, write_report
from .validators import validate_contract

_REPORT_JSON = "synthetic_report.json"
_REPORT_MD = "report.md"


def _render_markdown(report: dict[str, Any]) -> str:
    return (
        "# ML uplift harness — SYNTHETIC-ONLY smoke report\n\n"
        f"- experiment_id: `{report['experiment_id']}`\n"
        f"- markers: {', '.join(report['markers'])}\n\n"
        "## Non-scope\n\n"
        "SYNTHETIC_ONLY / NOT_REAL_EXPERIMENT_EVIDENCE. NO_REAL_DATA,"
        " NO_MODEL_RUN, NO_BACKTEST, NO_TRADING_METRICS. No real data read; no"
        " features / labels / model / inference / sweep / replay; no"
        " trading-performance metrics computed. No T2 execution,"
        " byte-admissibility, new-epoch adoption, production routing, or LLM"
        " integration authorised.\n"
    )


def run_synthetic_smoke(
    payload: dict[str, Any],
    output_root: str | Path,
    *,
    code_sha: str | None = None,
) -> dict[str, Any]:
    """Run the synthetic-only smoke path; write reports under ``output_root``.

    Raises HarnessContractError (fail-closed) if the contract is invalid or
    requests any real-run / downstream authorisation.
    """
    result = validate_contract(payload)
    if not result.valid:
        raise HarnessContractError(f"contract invalid: {result.errors}")

    contract = contract_from_dict(payload)
    provenance = capture_provenance(contract, code_sha=code_sha)
    report_files = contract.output_report.report_files or [_REPORT_JSON]
    manifest = plan_artifact_manifest(output_root, contract.experiment_id, report_files)

    # The manifest is machine-independent; the actual write dir is resolved
    # separately and never embedded in the committed report.
    output_dir = resolve_experiment_dir(output_root, contract.experiment_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_synthetic_report(contract, provenance, manifest, result.status)
    write_markdown(output_dir, _REPORT_MD, _render_markdown(report))
    # JSON written last; its presence signals completion.
    write_report(output_dir, _REPORT_JSON, report)
    return report
