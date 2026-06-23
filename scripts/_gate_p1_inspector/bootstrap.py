"""Inner inspector bootstrap (plan §5).

Invoked by the outer launcher as::

    python -B -m scripts._gate_p1_inspector.bootstrap --report-dir <dir> \\
        --envelope <path> [--first-run]

It installs the five guard families in a fixed order *before* running any
inspection, then (PR-B.0) runs only the stub inspector. Importing this module
has no side effects; all guard installation happens inside ``run_inner`` /
``main``.

PR-B.0 performs NO real inspection. PR-B.1 / PR-B.2 inspection submodules are
absent and are not importable from here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .b1_constants import CANDIDATE_SPANS
from .b1_run import run_b1_inspection
from .guards import GUARD_VIOLATION_ARTIFACT, GuardViolationError
from .guards import bytecode as bytecode_guard
from .guards import credentials as credentials_guard
from .guards import filesystem as filesystem_guard
from .guards import imports as imports_guard
from .guards import network as network_guard
from .guards import subprocess as subprocess_guard
from .inspector.stub import run_stub_inspection
from .report.common_metadata import compute_pr_b_code_hash

EXIT_OK = 0
EXIT_GUARD_VIOLATION = 2
EXIT_INTEGRITY_HALT = 3

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def install_guards(report_dir: str | Path, *, enforce_bytecode: bool = True) -> None:
    """Install the five guard families in the fixed plan §5 order."""
    if enforce_bytecode:
        bytecode_guard.install()
    imports_guard.install()
    credentials_guard.install()
    network_guard.install()
    subprocess_guard.install()
    filesystem_guard.install(report_dir)


def uninstall_guards() -> None:
    """Uninstall all guards (reverse order). Used by in-process tests."""
    filesystem_guard.uninstall()
    subprocess_guard.uninstall()
    network_guard.uninstall()
    credentials_guard.uninstall()
    imports_guard.uninstall()
    bytecode_guard.uninstall()


def run_inner(
    report_dir: str | Path,
    report_id: str,
    *,
    first_run_mode: bool,
    enforce_bytecode: bool = True,
) -> Path:
    """Install guards, run the PR-B.0 stub, and return the report path.

    Guards are uninstalled on the way out so in-process callers (tests) do not
    leak patched state. The real inner process exits immediately afterward, so
    the patches never outlive the run either way.
    """
    install_guards(report_dir, enforce_bytecode=enforce_bytecode)
    try:
        return run_stub_inspection(report_dir, report_id, first_run_mode=first_run_mode)
    finally:
        uninstall_guards()


def run_b1_under_guards(
    report_dir: str | Path,
    report_id: str,
    *,
    data_dir: str | Path,
    repo_root: str | Path,
    candidate_spans: tuple[str, ...] = CANDIDATE_SPANS,
    first_run_mode: bool = True,
    clean_code_sha: str | None = None,
    enforce_bytecode: bool = True,
) -> Path:
    """Install guards, run the PR-B.1 read-only inspection, return report path.

    Guards confine WRITES to the report dir (reads of candidate raw files and
    AST/source reads remain allowed); they are uninstalled on the way out.
    """
    install_guards(report_dir, enforce_bytecode=enforce_bytecode)
    try:
        return run_b1_inspection(
            report_dir,
            report_id,
            data_dir=data_dir,
            repo_root=repo_root,
            candidate_spans=candidate_spans,
            first_run_mode=first_run_mode,
            clean_code_sha=clean_code_sha,
        )
    finally:
        uninstall_guards()


def _write_guard_violation(report_dir: Path, message: str) -> None:
    payload = {
        "guard_violation": True,
        "message": message,
        "inspection_performed": False,
        "pr_b_stage": "PR-B.0",
    }
    try:
        target = report_dir / GUARD_VIOLATION_ARTIFACT
        target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except (OSError, GuardViolationError):
        # Last-resort path: report dir unwritable; fall back to stderr.
        sys.stderr.write(f"guard_violation (unwritable report dir): {message}\n")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gate_p1_pr_b_bootstrap",
        description="Gate P1 PR-B inner inspector (stub or PR-B.1 read-only).",
    )
    parser.add_argument("--report-dir", required=True)
    parser.add_argument("--envelope", default=None)
    parser.add_argument("--report-id", default=None)
    parser.add_argument("--first-run", action="store_true")
    parser.add_argument("--mode", default="stub", choices=("stub", "b1"))
    parser.add_argument("--data-dir", default=str(_REPO_ROOT / "data"))
    parser.add_argument("--repo-root", default=str(_REPO_ROOT))
    parser.add_argument("--candidate-spans", default=",".join(CANDIDATE_SPANS))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -B -m scripts._gate_p1_inspector.bootstrap``."""
    args = _parse_args(argv)
    report_dir = Path(args.report_dir).resolve()

    report_id = args.report_id
    expected_code_hash: str | None = None
    clean_code_sha: str | None = None
    if args.envelope is not None:
        envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        report_id = report_id or envelope.get("report_id")
        expected_code_hash = envelope.get("pr_b_code_hash")
        clean_code_sha = envelope.get("clean_code_sha")
    report_id = report_id or report_dir.name

    if not report_dir.is_dir():
        sys.stderr.write(f"bootstrap: report dir does not exist: {report_dir}\n")
        return EXIT_INTEGRITY_HALT

    # Cross-check inspector code hash against the outer-recorded value (plan §7).
    actual_code_hash = compute_pr_b_code_hash()
    if expected_code_hash is not None and expected_code_hash != actual_code_hash:
        _write_guard_violation(
            report_dir,
            "pr_b_code_hash drift between outer envelope and inner recompute.",
        )
        return EXIT_INTEGRITY_HALT

    spans = tuple(s for s in args.candidate_spans.split(",") if s)
    try:
        if args.mode == "b1":
            run_b1_under_guards(
                report_dir,
                report_id,
                data_dir=args.data_dir,
                repo_root=args.repo_root,
                candidate_spans=spans,
                first_run_mode=args.first_run,
                clean_code_sha=clean_code_sha,
            )
        else:
            run_inner(report_dir, report_id, first_run_mode=args.first_run)
    except GuardViolationError as exc:
        _write_guard_violation(report_dir, str(exc))
        return EXIT_GUARD_VIOLATION
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
