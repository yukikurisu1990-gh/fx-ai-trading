"""Filesystem write-allowlist guard tripwire tests (plan §10)."""

from __future__ import annotations

import os
import tempfile

import pytest

from scripts._gate_p1_inspector.guards import GuardViolationError
from scripts._gate_p1_inspector.guards import filesystem as filesystem_guard


def test_write_inside_report_dir_allowed(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    with filesystem_guard.activate(report_dir):
        (report_dir / "ok.json").write_text("{}", encoding="utf-8")
    assert (report_dir / "ok.json").read_text() == "{}"


def test_write_outside_report_dir_blocked(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    outside = tmp_path / "outside.json"
    with filesystem_guard.activate(report_dir), pytest.raises(GuardViolationError):
        outside.write_text("{}", encoding="utf-8")


def test_disallowed_extension_blocked(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    with filesystem_guard.activate(report_dir), pytest.raises(GuardViolationError):
        (report_dir / "note.txt").write_text("x", encoding="utf-8")


def test_open_write_outside_blocked(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    target = str(tmp_path / "evil.json")
    with filesystem_guard.activate(report_dir), pytest.raises(GuardViolationError):
        open(target, "w").close()


def test_open_read_not_blocked(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    source = tmp_path / "source.txt"
    source.write_text("data", encoding="utf-8")
    with filesystem_guard.activate(report_dir), open(source, encoding="utf-8") as handle:
        assert handle.read() == "data"


def test_mkdtemp_blocked(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    with filesystem_guard.activate(report_dir), pytest.raises(GuardViolationError):
        tempfile.mkdtemp()


def test_mkdir_outside_blocked(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    with filesystem_guard.activate(report_dir), pytest.raises(GuardViolationError):
        (tmp_path / "newdir").mkdir()


def test_destructive_rename_hard_blocked(tmp_path):
    # os.rename is hard-blocked by the guard (PR-B.0 never mutates files in
    # place). os.remove/unlink/rmtree are likewise hard-blocked, but those call
    # forms are additionally forbidden repo-wide by the custom linter, so this
    # test exercises os.rename to prove the hard-block path.
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    victim = report_dir / "x.json"
    victim.write_text("{}", encoding="utf-8")
    with filesystem_guard.activate(report_dir), pytest.raises(GuardViolationError):
        os.rename(str(victim), str(report_dir / "y.json"))


def test_filesystem_restored_after_context(tmp_path):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    with filesystem_guard.activate(report_dir):
        pass
    # Writes anywhere work again (no wrapper installed).
    (tmp_path / "after.txt").write_text("y", encoding="utf-8")
    assert (tmp_path / "after.txt").read_text() == "y"
