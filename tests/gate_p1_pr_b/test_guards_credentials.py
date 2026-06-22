"""Credential guard tripwire tests (plan §10)."""

from __future__ import annotations

import os

import pytest

from scripts._gate_p1_inspector.guards import GuardViolationError
from scripts._gate_p1_inspector.guards import credentials as credentials_guard


def test_credential_getitem_blocked(monkeypatch):
    monkeypatch.setenv("OANDA_ACCESS_TOKEN", "dummy-not-real")
    with credentials_guard.activate(), pytest.raises(GuardViolationError):
        _ = os.environ["OANDA_ACCESS_TOKEN"]


def test_credential_get_blocked(monkeypatch):
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "dummy-not-real")
    with credentials_guard.activate(), pytest.raises(GuardViolationError):
        os.environ.get("AWS_SECRET_ACCESS_KEY")


def test_credential_presence_check_blocked(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "dummy-not-real")
    with credentials_guard.activate(), pytest.raises(GuardViolationError):
        _ = "API_TOKEN" in os.environ


def test_credential_case_insensitive(monkeypatch):
    # Intentionally lowercase to prove the guard's case-insensitive matching.
    lower_key = "aws_access_key_id"
    monkeypatch.setenv(lower_key, "dummy-not-real")
    with credentials_guard.activate(), pytest.raises(GuardViolationError):
        os.environ.get(lower_key)


def test_non_credential_key_passes(monkeypatch):
    monkeypatch.setenv("PR_B0_SAFE_VAR", "ok")
    with credentials_guard.activate():
        assert os.environ.get("PR_B0_SAFE_VAR") == "ok"
        assert "PR_B0_SAFE_VAR" in os.environ


def test_guard_restored_after_context(monkeypatch):
    monkeypatch.setenv("PLAIN_VAR", "v")
    with credentials_guard.activate():
        pass
    # After the context, lookups behave normally (no wrapper left installed).
    assert os.environ.get("PLAIN_VAR") == "v"
