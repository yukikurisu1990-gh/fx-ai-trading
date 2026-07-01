"""Gate P1 PR-B.0 outer launcher (plan §4).

PR-B.0 is infrastructure-only. This outer launcher establishes the
side-effect-free, audited execution envelope and spawns the inner guarded
inspector in **stub mode**. No Gate P1 inspection is performed: the inner
process reads no candidate data, computes no candidate SHA-256, and emits only
a clearly-marked stub report.

The launcher fails closed: unknown flags, a non-stub mode request, an unsafe
report root, a dirty tracked worktree, or a report-id collision all abort
before the inner process starts. PR-B.1 / PR-B.2 inspections are not
implemented and cannot be requested here.

Usage::

    python scripts/gate_p1_pr_b_launcher.py --report-id my-run-001 [--first-run]
    python scripts/gate_p1_pr_b_launcher.py --report-id t --report-root /tmp/x
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Allow running as `python scripts/gate_p1_pr_b_launcher.py` (which puts the
# scripts/ dir on sys.path, not the repo root) by ensuring the repo root is
# importable so `import scripts._gate_p1_inspector...` resolves.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SUPPORTED_MODES = ("stub", "b1", "b2")

# PR-B.0 stub output defaults OUTSIDE the repository, in a clearly stub-only
# system-temp location. A PR-B.0 stub report must never be written under
# data/ or artifacts/ (where it could be confused with real evidence) or
# anywhere repo-tracked (where it could be accidentally committed).
DEFAULT_STUB_REPORT_ROOT = Path(tempfile.gettempdir()) / "gate_p1_pr_b0_stub"

# PR-B.1 real inspection writes derived-metadata reports under a controlled,
# clearly-namespaced Gate P1 PR-B path (the real evidence location). This is
# distinct from the Gate P2 verification path and from the original plan's
# gate_p1_report path.
DEFAULT_B1_REPORT_ROOT = Path(__file__).resolve().parent.parent / "artifacts" / "gate_p1_pr_b"

# Backwards-compatible alias (PR-B.0 default).
DEFAULT_REPORT_ROOT = DEFAULT_STUB_REPORT_ROOT

_REPORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_CREDENTIAL_PATTERN = re.compile(r"(?i)(OANDA|TOKEN|SECRET|KEY|PASSWORD|CREDENTIAL|AWS|GCP|AZURE)")
_PR_A_SPEC_RELPATH = "docs/design/gate_p1_feasibility_inspection_protocol.md"

# Reserved path components NO report root may contain (either mode): real raw
# data, OANDA archive paths, the original plan gate_p1_report path, and Gate P2
# verification paths.
_RESERVED_ROOT_PARTS_ALWAYS = (
    "data",
    "oanda_archive",
    "gate_p1_report",
    "gate_p2_verification",
)
# Additionally forbidden for the STUB mode only (stub must never land under any
# artifact tree or anywhere in the repo).
_RESERVED_ROOT_PARTS_STUB = ("artifacts",)
# The single in-repo subtree PR-B.1 may write its controlled real report into.
_B1_ALLOWED_INREPO_RELPATH = "artifacts/gate_p1_pr_b"

EXIT_OK = 0
EXIT_PREFLIGHT_FAILED = 1
EXIT_INNER_CRASHED = 2
EXIT_AUDIT_FAILED = 3

_PR_B_STAGE_BY_MODE = {"stub": "PR-B.0", "b1": "PR-B.1", "b2": "PR-B.2"}

# Minimal env keys forwarded to the inner process (plan §13.Q8). Credential-
# pattern keys are excluded by construction.
_ENV_ALLOWLIST = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "SystemRoot",
    "SystemDrive",
    "windir",
    "COMSPEC",
    "TEMP",
    "TMP",
    "TMPDIR",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_ARCHITECTURE",
    "LANG",
    "LC_ALL",
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    # Fixed git argv; the outer launcher is the only place process spawning is
    # allowed (the inner inspector prohibits subprocess entirely).
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    )


def _tracked_dirty(porcelain: str) -> list[str]:
    """Return tracked (non-``??``) porcelain lines."""
    return [ln for ln in porcelain.splitlines() if ln and not ln.startswith("??")]


def _base_master_sha() -> str | None:
    """Best-effort merge-base of HEAD with origin/master (provenance only)."""
    try:
        return _git("merge-base", "HEAD", "origin/master").stdout.strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _scrubbed_env() -> dict[str, str]:
    env: dict[str, str] = {}
    for key in _ENV_ALLOWLIST:
        value = os.environ.get(key)
        if value is not None and not _CREDENTIAL_PATTERN.search(key):
            env[key] = value
    return env


def _pr_a_spec_version() -> dict[str, object]:
    spec_path = REPO_ROOT / _PR_A_SPEC_RELPATH
    sha256: str | None = None
    if spec_path.exists():
        sha256 = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    return {"path": _PR_A_SPEC_RELPATH, "sha256": sha256, "amendment": "amendment_1"}


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gate_p1_pr_b_launcher",
        description="Gate P1 PR-B.0 outer launcher (stub mode only).",
    )
    parser.add_argument("--report-id", default=None, help="ASCII [A-Za-z0-9_-], 1-64 chars.")
    parser.add_argument(
        "--report-root",
        default=None,
        help=(
            "Parent dir for the report. Default depends on --mode: stub -> a "
            "system-temp gate_p1_pr_b0_stub dir; b1 -> artifacts/gate_p1_pr_b. "
            "Never data/, OANDA archive, gate_p1_report, or gate_p2_verification."
        ),
    )
    parser.add_argument("--first-run", action="store_true")
    parser.add_argument(
        "--mode",
        default="stub",
        help=(
            "'stub' (PR-B.0 inert) or 'b1' (PR-B.1 read-only inspection). Any "
            "other value (e.g. 'b2', dependency/pipeline) fails closed."
        ),
    )
    parser.add_argument(
        "--data-dir",
        default=str(REPO_ROOT / "data"),
        help="Candidate raw data dir (b1 mode, read-only).",
    )
    parser.add_argument(
        "--candidate-spans",
        default=None,
        help="Comma-separated candidate spans for b1 (default: 365d,730d,3650d).",
    )
    return parser.parse_args(argv)


def _fail(message: str) -> int:
    sys.stderr.write(f"[PR-B preflight HALT] {message}\n")
    return EXIT_PREFLIGHT_FAILED


def _unsafe_report_root_reason(report_root: Path, mode: str) -> str | None:
    """Return a reason string if ``report_root`` is unsafe for the given mode.

    Always reject reserved components (data / OANDA archive / gate_p1_report /
    gate_p2_verification).

    * ``stub`` mode additionally rejects any ``artifacts`` component and any
      path inside the repository working tree — a stub must never land where it
      could be committed or confused with real evidence.
    * ``b1`` mode permits the single controlled in-repo subtree
      ``artifacts/gate_p1_pr_b`` (the real-evidence destination) and any
      external (temp/test) path; everything else in-repo is rejected.
    """
    parts_lower = {part.lower() for part in report_root.parts}
    reserved = parts_lower.intersection(_RESERVED_ROOT_PARTS_ALWAYS)
    if reserved:
        return f"contains reserved path component(s) {sorted(reserved)}"

    if mode == "stub":
        stub_reserved = parts_lower.intersection(_RESERVED_ROOT_PARTS_STUB)
        if stub_reserved:
            return f"stub output must not be under {sorted(stub_reserved)}"
        try:
            report_root.relative_to(REPO_ROOT)
        except ValueError:
            return None
        return "is inside the repository working tree (stub output must be external)"

    # b1 mode.
    try:
        rel = report_root.relative_to(REPO_ROOT)
    except ValueError:
        return None  # external (temp/test) path is fine for b1
    allowed = Path(_B1_ALLOWED_INREPO_RELPATH)
    if rel == allowed or allowed in rel.parents:
        return None
    return (
        "in-repo PR-B.1 report root must be under "
        f"'{_B1_ALLOWED_INREPO_RELPATH}' (got '{rel.as_posix()}')"
    )


def run(argv: list[str] | None = None) -> int:
    """Execute the Gate P1 PR-B outer launcher. Returns the process exit code."""
    args = _parse_args(argv)

    # --- step 1: arg validation (fail closed) ---
    if args.mode not in SUPPORTED_MODES:
        return _fail(
            f"mode '{args.mode}' is not implemented. Supported: 'stub' (PR-B.0 "
            "inert), 'b1' (PR-B.1 read-only inspection), 'b2' (PR-B.2 static "
            "dependency inventory + pipeline feasibility). Any other mode "
            "requires separate authorisation."
        )

    report_id = args.report_id or _utc_now_iso().replace(":", "").replace("-", "")
    if not _REPORT_ID_RE.match(report_id):
        return _fail(f"invalid --report-id '{report_id}' (must match {_REPORT_ID_RE.pattern}).")

    if args.report_root is not None:
        report_root = Path(args.report_root).resolve()
    elif args.mode in ("b1", "b2"):
        report_root = DEFAULT_B1_REPORT_ROOT.resolve()
    else:
        report_root = DEFAULT_STUB_REPORT_ROOT.resolve()

    unsafe_reason = _unsafe_report_root_reason(report_root, args.mode)
    if unsafe_reason is not None:
        return _fail(
            f"unsafe --report-root '{report_root}' for mode '{args.mode}': {unsafe_reason}."
        )

    report_dir = report_root / report_id

    # --- step 2: clean code SHA capture ---
    try:
        clean_code_sha = _git("rev-parse", "HEAD").stdout.strip()
        porcelain_before = _git("status", "--porcelain").stdout
        base_master_sha = _base_master_sha()
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return _fail(f"git unavailable or not a repo: {exc}")

    # --- step 3: clean tracked worktree check ---
    if _tracked_dirty(porcelain_before):
        return _fail("tracked worktree is dirty; commit or stash before launching.")

    # --- step 4: report directory creation (collision => HALT) ---
    try:
        report_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        return _fail(f"report dir already exists: {report_dir}")

    # --- steps 5-6: envelope (outer self-restricts writes to the report dir) ---
    from scripts._gate_p1_inspector.report.common_metadata import compute_pr_b_code_hash

    pr_b_code_hash = compute_pr_b_code_hash()
    envelope = {
        "report_id": report_id,
        "outer_launch_ts_utc": _utc_now_iso(),
        "clean_code_sha": clean_code_sha,
        "python_version": list(sys.version_info[:3]) + [sys.version],
        "platform": [sys.platform, platform.platform()],
        "pr_a_spec_version": _pr_a_spec_version(),
        "pr_b_code_hash": pr_b_code_hash,
        "first_run_mode": args.first_run,
        "mode": args.mode,
        "base_master_sha": base_master_sha,
        "pr_b_stage": _PR_B_STAGE_BY_MODE.get(args.mode, "PR-B.0"),
    }
    envelope_path = report_dir / "execution_envelope.json"
    if envelope_path.resolve().parent != report_dir.resolve():
        return _fail("outer write-allowlist violation (envelope outside report dir).")
    envelope_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")

    # --- step 7: inner process start (guarded, -B, scrubbed env) ---
    inner_argv = [
        sys.executable,
        "-B",
        "-m",
        "scripts._gate_p1_inspector.bootstrap",
        "--report-dir",
        str(report_dir),
        "--envelope",
        str(envelope_path),
        "--mode",
        args.mode,
    ]
    if args.first_run:
        inner_argv.append("--first-run")
    if args.mode == "b1":
        inner_argv += ["--data-dir", str(Path(args.data_dir).resolve())]
        inner_argv += ["--repo-root", str(REPO_ROOT)]
        if args.candidate_spans:
            inner_argv += ["--candidate-spans", args.candidate_spans]
    elif args.mode == "b2":
        inner_argv += ["--repo-root", str(REPO_ROOT)]
    inner = subprocess.run(
        inner_argv,
        cwd=str(REPO_ROOT),
        check=False,
        capture_output=True,
        text=True,
        env=_scrubbed_env(),
    )

    # --- step 8: inner result capture ---
    report_json = report_dir / "gate_p1_report.json"
    inner_ok = inner.returncode == 0 and report_json.exists()

    # --- step 9: post-run audit ---
    try:
        head_after = _git("rev-parse", "HEAD").stdout.strip()
        porcelain_after = _git("status", "--porcelain").stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        return _fail(f"post-run git audit failed: {exc}")

    head_unchanged = head_after == clean_code_sha
    new_entries = set(porcelain_after.splitlines()) - set(porcelain_before.splitlines())
    diff_confined = _diff_confined_to_report(new_entries, report_dir)

    audit = {
        "head_unchanged": head_unchanged,
        "diff_confined_to_report_dir": diff_confined,
        "audit_ts_utc": _utc_now_iso(),
        "inner_returncode": inner.returncode,
        "inner_emitted_report": report_json.exists(),
    }
    envelope["post_run_audit"] = audit
    envelope_path.write_text(json.dumps(envelope, indent=2) + "\n", encoding="utf-8")

    # --- step 10: exit code ---
    if not (head_unchanged and diff_confined):
        sys.stderr.write(f"[PR-B.0 audit HALT] {audit}\n")
        return EXIT_AUDIT_FAILED
    if not inner_ok:
        sys.stderr.write(
            f"[PR-B.0 inner failure] returncode={inner.returncode} "
            f"stderr_tail={inner.stderr[-500:]!r}\n"
        )
        return EXIT_INNER_CRASHED
    return EXIT_OK


def _diff_confined_to_report(new_entries: set[str], report_dir: Path) -> bool:
    """True if every new porcelain entry stays within the report-dir subtree.

    When the report root is outside the repo working tree, new_entries is
    empty and the diff is trivially confined. Git collapses a newly-created
    untracked tree to its top-most new directory, so a new entry that is an
    ANCESTOR directory of the report dir (e.g. ``artifacts/gate_p1_pr_b/`` when
    the report dir is ``artifacts/gate_p1_pr_b/<id>/``) is accepted: it exists
    only to contain the report dir, since the guarded inner writes nowhere else.
    """
    if not new_entries:
        return True
    try:
        report_rel = report_dir.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        # report dir is outside the repo; any in-repo diff is NOT from us.
        return False
    for entry in new_entries:
        path_part = entry[3:] if len(entry) > 3 else ""
        path_part = path_part.strip().strip('"')
        normalised = path_part.rstrip("/")
        under_report = path_part.startswith(report_rel)
        ancestor_of_report = bool(normalised) and report_rel.startswith(normalised + "/")
        if not (under_report or ancestor_of_report):
            return False
    return True


if __name__ == "__main__":
    raise SystemExit(run())
