"""Session-wide guards for the test suite.

P1-A (audit memo docs/design/project_wide_logic_audit_fable5_findings.md,
finding F-9): stage-eval smoke tests used to regenerate tracked evidence
files under artifacts/ in place. Test output is now redirected to
tmp_path, and this autouse session fixture is the regression backstop:
it hashes the protected tracked evidence files at session start and
fails the session at teardown if any test modified them.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Tracked evidence files that test runs must never modify (audit F-9 set
# plus the two additional at-risk writers found during P1-A).
PROTECTED_TRACKED_ARTIFACTS: tuple[str, ...] = (
    "artifacts/stage24_0b/eval_report.md",
    "artifacts/stage24_0c/eval_report.md",
    "artifacts/stage24_0d/eval_report.md",
    "artifacts/stage25_0a/dataset_summary.md",
    "artifacts/stage25_0a/causality_audit.md",
    "artifacts/stage25_0b/eval_report.md",
    "artifacts/stage25_0c/eval_report.md",
    "artifacts/stage25_0d/eval_report.md",
)


def _digest(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def protect_tracked_artifacts():
    """Fail the session if any test modifies protected tracked evidence."""
    before = {rel: _digest(_REPO_ROOT / rel) for rel in PROTECTED_TRACKED_ARTIFACTS}
    yield
    dirtied = [
        rel for rel in PROTECTED_TRACKED_ARTIFACTS if _digest(_REPO_ROOT / rel) != before[rel]
    ]
    if dirtied:
        raise AssertionError(
            "P1-A violation: test run modified tracked evidence artifacts: "
            f"{dirtied}. Stage-eval tests must write to tmp_path via --out-dir "
            "(see docs/design/project_wide_logic_audit_fable5_findings.md F-9). "
            "Restore the files with `git restore -- <paths>` and fix the "
            "offending test."
        )
