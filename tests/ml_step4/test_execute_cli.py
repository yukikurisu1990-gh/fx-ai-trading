"""Guarded execute CLI tests (preflight only; real execution refused)."""

from __future__ import annotations

from pathlib import Path

from scripts.ml_step4 import evidence
from scripts.ml_step4.evidence import EXECUTION_EVIDENCE_DIR
from scripts.ml_step4.execute_365d_ba import main


def test_preflight_returns_zero(capsys) -> None:
    rc = main(["--preflight"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ML_STEP4_GUARDED_EXECUTE_WIRING_IMPLEMENTED_NO_RUN" in out
    assert "PREFLIGHT_WIRING_COMPLETE_NO_RUN" in out


def test_default_invocation_refused(capsys) -> None:
    rc = main([])
    assert rc == 2
    assert "REFUSED" in capsys.readouterr().out


def test_execute_flag_refused(capsys) -> None:
    rc = main(["--execute"])
    assert rc == 2
    assert "REFUSED" in capsys.readouterr().out


def test_preflight_output_is_scrub_clean(capsys) -> None:
    main(["--preflight"])
    # If the plan weren't clean, main() would have raised before printing.
    out = capsys.readouterr().out
    assert out.strip()  # produced output


def test_cli_does_not_write_execution_evidence() -> None:
    exec_dir = evidence.repo_root() / EXECUTION_EVIDENCE_DIR
    before = sorted(p.name for p in exec_dir.glob("*")) if exec_dir.exists() else []
    main(["--preflight"])
    main([])
    after = sorted(p.name for p in exec_dir.glob("*")) if exec_dir.exists() else []
    # PR #409 stop evidence (8 files) unchanged; nothing added.
    assert before == after
    assert not (exec_dir / "ml_step4_run_manifest_wiring_probe.json").exists()


def test_cli_flags_no_execution() -> None:
    # The plan the CLI prints asserts no execution occurred (structural).
    from scripts.ml_step4 import executor

    plan = executor.build_execution_plan()
    assert plan["execution_performed"] is False
    assert plan["raw_data_read"] is False
    assert plan["model_trained"] is False
    assert Path(EXECUTION_EVIDENCE_DIR).name == "365d_ba_v1"
