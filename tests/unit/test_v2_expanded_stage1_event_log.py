"""Stage 1 unit tests — event log ordering + test-access guard."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from scripts._verification_harness import event_log as EL  # noqa: N812


def test_allowed_events_registry():
    assert "val_split_loaded" in EL.ALLOWED_EVENTS
    assert "cell_fit_complete" in EL.ALLOWED_EVENTS
    assert "val_quantile_scored" in EL.ALLOWED_EVENTS
    assert "val_selection_frozen" in EL.ALLOWED_EVENTS
    assert "test_split_loaded" in EL.ALLOWED_EVENTS
    assert "test_metrics_computed" in EL.ALLOWED_EVENTS


def test_pre_and_post_freeze_partition():
    assert "val_selection_frozen" in EL.PRE_FREEZE_EVENTS
    assert "test_split_loaded" in EL.POST_FREEZE_EVENTS
    assert "test_metrics_computed" in EL.POST_FREEZE_EVENTS
    # Partition exhaustive
    assert set(EL.ALLOWED_EVENTS) == EL.PRE_FREEZE_EVENTS | EL.POST_FREEZE_EVENTS
    assert set() == EL.PRE_FREEZE_EVENTS & EL.POST_FREEZE_EVENTS


def test_append_unknown_event_raises():
    log = EL.EventLog()
    with pytest.raises(EL.EventLogError):
        log.append("bogus_event", scope="foundation")


def test_event_log_persists_jsonl(tmp_path: Path):
    out = tmp_path / "verification_log.jsonl"
    log = EL.EventLog(out_path=out)
    log.append("val_split_loaded", scope="foundation")
    log.append("val_selection_frozen", scope="foundation", cell_id="C-sb-baseline", selected_q=5.0)
    assert out.is_file()
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2


def test_assert_val_freeze_precedes_test_passes_on_correct_order():
    log = EL.EventLog()
    log.append("val_split_loaded", scope="S-1")
    log.append("cell_fit_complete", scope="S-1", cell_id="C-se")
    log.append("val_quantile_scored", scope="S-1", cell_id="C-se", selected_q=5.0)
    # Force a measurable delay so timestamps strictly differ
    log.append("val_selection_frozen", scope="S-1", cell_id="C-se", selected_q=5.0)
    time.sleep(0.001)
    log.append("test_split_loaded", scope="S-1")
    log.assert_val_freeze_precedes_test(scope="S-1")  # no raise


def test_assert_val_freeze_precedes_test_halts_when_test_first():
    log = EL.EventLog()
    log.append("test_split_loaded", scope="S-1")
    # val_selection_frozen NOT yet emitted -> HALT
    with pytest.raises(EL.TestIsolationError):
        log.assert_val_freeze_precedes_test(scope="S-1")


def test_assert_no_repeat_test_metrics():
    log = EL.EventLog()
    log.append("val_split_loaded", scope="S-3")
    log.append("val_selection_frozen", scope="S-3", cell_id="C-a1-L1", selected_q=5.0)
    log.append("test_split_loaded", scope="S-3")
    log.append("test_metrics_computed", scope="S-3", cell_id="C-a1-L1", selected_q=5.0)
    # Single emission OK
    log.assert_no_repeat_test_metrics(scope="S-3", cell_id="C-a1-L1", selected_q=5.0)
    # Repeat HALT
    log.append("test_metrics_computed", scope="S-3", cell_id="C-a1-L1", selected_q=5.0)
    with pytest.raises(EL.TestIsolationError):
        log.assert_no_repeat_test_metrics(scope="S-3", cell_id="C-a1-L1", selected_q=5.0)


def test_test_access_guard_pre_freeze_halts():
    log = EL.EventLog()
    guard = EL.TestAccessGuard(log=log)
    log.append("val_split_loaded", scope="foundation")
    # Attempt to read test data before val_selection_frozen
    with pytest.raises(EL.TestIsolationError):
        guard.read_test(scope="foundation")


def test_test_access_guard_unlock_requires_freeze_event():
    log = EL.EventLog()
    guard = EL.TestAccessGuard(log=log)
    log.append("val_split_loaded", scope="foundation")
    with pytest.raises(EL.TestIsolationError):
        guard.unlock(scope="foundation")  # freeze not emitted yet


def test_test_access_guard_post_freeze_permits():
    log = EL.EventLog()
    guard = EL.TestAccessGuard(log=log)
    log.append("val_split_loaded", scope="foundation")
    log.append("val_selection_frozen", scope="foundation", cell_id="C-sb-baseline", selected_q=5.0)
    guard.unlock(scope="foundation")
    assert guard.is_unlocked("foundation")
    # No HALT
    guard.read_test(scope="foundation", payload={"split": "test"})


def test_test_access_guard_scope_isolation():
    log = EL.EventLog()
    guard = EL.TestAccessGuard(log=log)
    log.append("val_split_loaded", scope="S-1")
    log.append("val_selection_frozen", scope="S-1", cell_id="C-se", selected_q=5.0)
    guard.unlock(scope="S-1")
    # S-2 is NOT unlocked just because S-1 is
    with pytest.raises(EL.TestIsolationError):
        guard.read_test(scope="S-2")


def test_per_cell_freeze_for_multi_variant_sentinel():
    """S-3 has 3 substantive variants (L1/L2/L3) + control; each gets its own freeze."""
    log = EL.EventLog()
    for cell in ("C-a1-L1", "C-a1-L2", "C-a1-L3"):
        log.append("val_split_loaded", scope="S-3")
        log.append("cell_fit_complete", scope="S-3", cell_id=cell)
        log.append("val_quantile_scored", scope="S-3", cell_id=cell, selected_q=5.0)
        log.append("val_selection_frozen", scope="S-3", cell_id=cell, selected_q=5.0)
        time.sleep(0.001)
        log.append("test_split_loaded", scope="S-3")
        log.append("test_metrics_computed", scope="S-3", cell_id=cell, selected_q=5.0)

    # Per-cell freeze count
    for cell in ("C-a1-L1", "C-a1-L2", "C-a1-L3"):
        assert log.count("val_selection_frozen", "S-3", cell) == 1
        assert log.count("test_metrics_computed", "S-3", cell, 5.0) == 1
