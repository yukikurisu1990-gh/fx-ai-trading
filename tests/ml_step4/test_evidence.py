"""Evidence writer + ml_step4 scrubber tests (leak rejection, determinism)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ml_step4 import evidence
from scripts.ml_step4.evidence import (
    EXECUTION_EVIDENCE_DIR,
    EvidenceScrubError,
    assert_clean,
    scan_payload,
    serialise,
    write_report,
)


def test_metric_keys_are_allowed() -> None:
    payload = {
        "sharpe": 1.2,
        "pnl": 34.5,
        "expectancy": 0.4,
        "win_rate": 0.55,
        "drawdown": 0.05,
    }
    assert scan_payload(payload) == []
    assert_clean(payload)  # no raise


def test_rejects_raw_row_keys() -> None:
    with pytest.raises(EvidenceScrubError):
        assert_clean({"candles": [{"bid_o": 1.1, "ask_o": 1.2}]})
    with pytest.raises(EvidenceScrubError):
        assert_clean({"bid_o": 1.1})


def test_rejects_personal_path() -> None:
    with pytest.raises(EvidenceScrubError):
        assert_clean({"note": r"C:\Users\someone\data\file.jsonl"})
    with pytest.raises(EvidenceScrubError):
        assert_clean({"note": "/Users/someone/data"})


def test_rejects_credentials() -> None:
    with pytest.raises(EvidenceScrubError):
        assert_clean({"aws_secret_access_key": "AKIAsomethinglong"})


def test_rejects_google_drive_and_r2() -> None:
    with pytest.raises(EvidenceScrubError):
        assert_clean({"link": "https://drive.google.com/file/d/abc/view"})
    with pytest.raises(EvidenceScrubError):
        assert_clean({"endpoint": "https://acct.r2.cloudflarestorage.com/bucket/key"})


def test_rejects_env_dump() -> None:
    with pytest.raises(EvidenceScrubError):
        assert_clean({"dump": "FOO=1;BAR=2;BAZ=3;QUX=4;"})
    with pytest.raises(EvidenceScrubError):
        assert_clean({"environ": {"PATH": "x", "HOME": "y"}})


def test_serialise_is_deterministic_and_sorted() -> None:
    a = serialise({"b": 1, "a": 2})
    b = serialise({"a": 2, "b": 1})
    assert a == b
    assert a.startswith('{\n  "a": 2')
    assert a.endswith("\n")


def test_write_report_json_no_bom_sorted(tmp_path: Path) -> None:
    out = write_report(tmp_path, "ml_step4_metrics_report.json", {"z": 1, "a": 2})
    raw = out.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")  # no BOM
    text = raw.decode("utf-8")
    assert json.loads(text) == {"z": 1, "a": 2}
    assert text.index('"a"') < text.index('"z"')  # keys sorted deterministically


def test_write_report_scrubs_before_write(tmp_path: Path) -> None:
    with pytest.raises(EvidenceScrubError):
        write_report(tmp_path, "bad.json", {"bid_o": 1.0})
    assert not (tmp_path / "bad.json").exists()


def test_write_report_refuses_real_execution_dir() -> None:
    # The real execution-evidence dir may already exist on this branch (it holds
    # PR #409 stop evidence). The guard must refuse to write there regardless.
    probe = Path.cwd() / EXECUTION_EVIDENCE_DIR / "guard_probe_should_not_exist.json"
    with pytest.raises(EvidenceScrubError):
        write_report(EXECUTION_EVIDENCE_DIR, "guard_probe_should_not_exist.json", {"ok": True})
    # Guard fires before any write: our probe file was never created.
    assert not probe.exists()


def test_write_markdown_report(tmp_path: Path) -> None:
    out = write_report(tmp_path, "ml_step4_acceptance_failure_decision_report.md", "# Clean\n")
    assert out.read_text(encoding="utf-8").endswith("\n")
    with pytest.raises(EvidenceScrubError):
        write_report(tmp_path, "leak.md", r"path C:\Users\x")


def test_expected_evidence_filenames() -> None:
    assert len(evidence.EXPECTED_EVIDENCE_FILES) == 8
    assert "ml_step4_run_manifest.json" in evidence.EXPECTED_EVIDENCE_FILES
    assert evidence.EXPECTED_EVIDENCE_FILES[-1].endswith(".md")
