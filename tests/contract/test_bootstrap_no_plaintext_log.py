"""Contract test — Bootstrap path never writes plaintext secret to logs / DB.

Per ``development_rules.md`` §10.3.1 / ``operations.md`` §15.4:
secret values handled by the Bootstrap UI MUST NOT appear in:
  - log output (any logger / any handler)
  - audit row values stored in ``app_settings_changes``
  - exception messages

This test exercises ``atomic_write_env`` end-to-end with a real tmp ``.env``
and a real captured logger, then asserts the secret value never surfaces.
The audit-row hash-only contract is verified by reading what
``bootstrap_view._enqueue_audit_rows`` would emit through the diff helper.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from fx_ai_trading.dashboard.config_console.env_diff import (
    compute_diff,
    parse_env_text,
)
from fx_ai_trading.dashboard.config_console.env_writer import atomic_write_env

SECRET_VALUE = "PLAINTEXT-SECRET-XYZ-DO-NOT-LEAK-99887766"


class _StubPM:
    def is_running(self) -> bool:
        return False


def test_no_plaintext_in_logs_during_write(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    target = tmp_path / ".env"
    caplog.set_level(logging.DEBUG)

    atomic_write_env(target, {"TOKEN": SECRET_VALUE}, process_manager=_StubPM())

    for record in caplog.records:
        assert SECRET_VALUE not in record.getMessage(), (
            f"Plaintext secret leaked into log record: {record.name}"
        )
        # Also check formatted args
        assert SECRET_VALUE not in str(record.args or "")


def test_no_plaintext_in_diff_output() -> None:
    """The diff that bootstrap_view shows to the operator must not contain values."""
    old = parse_env_text(f"TOKEN=oldvalue-XXX-{SECRET_VALUE}\n")
    new = parse_env_text(f"TOKEN=newvalue-YYY-{SECRET_VALUE}\n")
    diff = compute_diff(old, new)
    flat = repr(diff)
    assert SECRET_VALUE not in flat


def test_no_plaintext_in_audit_payload() -> None:
    """Simulate audit-row payload: must use hash prefixes only.

    bootstrap_view._enqueue_audit_rows passes hash prefixes (from compute_diff)
    as old_value / new_value. We assert here that the diff entries themselves
    only carry hash strings (not the source plaintext).
    """
    diff = compute_diff(
        {"TOKEN": SECRET_VALUE},
        {"TOKEN": SECRET_VALUE + "-new"},
    )
    for entry in diff["changed"]:
        assert SECRET_VALUE not in entry["old_hash"]
        assert SECRET_VALUE not in entry["new_hash"]
        # hash prefixes are 8 hex chars (or "-")
        assert len(entry["old_hash"]) in (1, 8)
        assert len(entry["new_hash"]) in (1, 8)


def test_no_plaintext_in_supervisor_running_error(tmp_path: Path) -> None:
    """When PID gate trips mid-write, the exception text must redact values."""
    from fx_ai_trading.dashboard.config_console.env_writer import (
        SupervisorRunningError,
    )

    class _BusyPM:
        def is_running(self) -> bool:
            return True

    target = tmp_path / ".env"
    with pytest.raises(SupervisorRunningError) as excinfo:
        atomic_write_env(target, {"TOKEN": SECRET_VALUE}, process_manager=_BusyPM())
    assert SECRET_VALUE not in str(excinfo.value)
    assert SECRET_VALUE not in repr(excinfo.value)


def test_module_source_does_not_contain_value_in_log_call() -> None:
    """Defensive: scan env_writer source for f-string log calls referencing values."""
    import fx_ai_trading.dashboard.config_console.env_writer as mod

    source = Path(mod.__file__).read_text(encoding="utf-8")
    # No log call should interpolate `payload`, `new_env`, or values from new_env
    forbidden_patterns = [
        '_log.info(f"',
        '_log.warning(f"',
        '_log.error(f"',
        '_log.debug(f"',
        '_log.exception(f"',
    ]
    for pat in forbidden_patterns:
        assert pat not in source, f"env_writer must not f-string into log calls (found {pat!r})"
