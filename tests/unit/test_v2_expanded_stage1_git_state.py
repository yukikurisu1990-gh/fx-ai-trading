"""Stage 1 unit tests — git state snapshot for the formal-run discipline.

Per amendment Stage 1 binding "Clean formal-run commit discipline":

  6. verify git status is clean
  7. record run_code_commit_sha and git_state_at_run_start in committed manifests

The primitive lives in manifests.py; this test ensures it works on the
implementation branch.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts._verification_harness import manifests as M  # noqa: N812

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git_repo_present() -> bool:
    try:
        subprocess.check_output(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(REPO_ROOT),
            stderr=subprocess.STDOUT,
            text=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


@pytest.mark.skipif(not _git_repo_present(), reason="not a git repo")
def test_record_git_state_at_run_start_returns_head_sha():
    state = M.record_git_state_at_run_start(REPO_ROOT)
    assert state["schema_version"] == "v2-expanded-1.0"
    assert len(state["head_sha"]) == 40  # full SHA
    assert "tracked_clean" in state


@pytest.mark.skipif(not _git_repo_present(), reason="not a git repo")
def test_assert_git_state_clean_passes_on_clean_state():
    state = {"tracked_clean": True}
    M.assert_git_state_clean(state)


def test_assert_git_state_clean_halts_on_dirty_state():
    state = {
        "tracked_clean": False,
        "tracked_dirty_lines": [" M scripts/foo.py"],
    }
    with pytest.raises(M.ManifestError):
        M.assert_git_state_clean(state)
