"""T2_PRIMARY_R2 runtime client-injection + dry-run readiness tests.

All fakes/synthetic only. No real R2, no network, no real credentials. Env is
always a fake dict; no real environment value is read. No object is ever
deposited/restored.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_RUNTIME_PATH = Path(__file__).resolve().parents[2] / "scripts" / "t2_r2_runtime.py"
_spec = importlib.util.spec_from_file_location("t2_r2_runtime_under_test", _RUNTIME_PATH)
rt = importlib.util.module_from_spec(_spec)
sys.modules["t2_r2_runtime_under_test"] = rt
assert _spec.loader is not None
_spec.loader.exec_module(rt)

from scripts.foundation_t2.constants import (  # noqa: E402
    T2_PRIMARY_R2_CLIENT_CONSTRUCTION_FAILED,
    T2_PRIMARY_R2_CONFIG_INCOMPLETE,
    T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT,
    T2_PRIMARY_R2_DRY_RUN_READY_NO_OBJECTS_TOUCHED,
    T2_PRIMARY_R2_RUNTIME_CLIENT_READY,
)
from scripts.foundation_t2.destination import UnavailableR2Destination  # noqa: E402
from scripts.foundation_t2.r2_adapter import R2Destination  # noqa: E402

_FULL_ENV = {
    "T2_PRIMARY_R2_ACCESS_KEY_ID": "fake-access-key",
    "T2_PRIMARY_R2_SECRET_ACCESS_KEY": "fake-secret-value",
    "T2_PRIMARY_R2_ENDPOINT": "https://fake.r2.example",
    "T2_PRIMARY_R2_BUCKET": "t2-bucket-alias",
    "T2_PRIMARY_R2_REGION": "auto",
}


class FakeClient:
    """Records whether any object operation was called (they must not be)."""

    def __init__(self):
        self.calls: list[str] = []

    def put_object(self, key, local_path):
        self.calls.append("put")
        return {}

    def head_object(self, key):
        self.calls.append("head")
        return {}

    def get_object(self, key, dest_path):
        self.calls.append("get")

    def get_object_lock(self, key):
        self.calls.append("lock")
        return None


def _factory_ok(captured):
    def factory(*, config, access_key_id, secret_access_key):
        captured["access_key_id"] = access_key_id
        captured["secret_access_key"] = secret_access_key
        captured["bucket"] = config.bucket
        return FakeClient()

    return factory


def _factory_boom(*, config, access_key_id, secret_access_key):
    raise RuntimeError(f"connect failed at C:\\Users\\op\\k with {secret_access_key}")


# --------------------------------------------------------------------------- #
# Presence / config (names only)
# --------------------------------------------------------------------------- #


def test_env_presence_is_names_only():
    presence = rt.env_presence(_FULL_ENV)
    assert presence["access_key_id"] is True and presence["bucket"] is True
    assert rt.env_presence({})["access_key_id"] is False


def test_credentials_present():
    assert rt.credentials_present(_FULL_ENV) is True
    assert rt.credentials_present({"T2_PRIMARY_R2_ACCESS_KEY_ID": "x"}) is False


def test_config_from_env_reads_no_secret():
    cfg = rt.config_from_env(_FULL_ENV)
    assert cfg.bucket == "t2-bucket-alias"
    assert cfg.endpoint == "https://fake.r2.example"
    # config object carries NO secret fields at all
    assert not hasattr(cfg, "secret_access_key")


# --------------------------------------------------------------------------- #
# Readiness — fail-closed paths
# --------------------------------------------------------------------------- #


def test_readiness_missing_credentials():
    r = rt.readiness_report({})
    assert r["status"] == T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT
    assert r["objects_touched"] is False


def test_readiness_partial_credentials():
    r = rt.readiness_report({"T2_PRIMARY_R2_ACCESS_KEY_ID": "x"})
    assert r["status"] == T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT


def test_readiness_missing_config():
    env = {
        "T2_PRIMARY_R2_ACCESS_KEY_ID": "x",
        "T2_PRIMARY_R2_SECRET_ACCESS_KEY": "x",
    }
    assert rt.readiness_report(env)["status"] == T2_PRIMARY_R2_CONFIG_INCOMPLETE


def test_readiness_client_construction_failure_is_scrubbed():
    r = rt.readiness_report(_FULL_ENV, client_factory=_factory_boom)
    assert r["status"] == T2_PRIMARY_R2_CLIENT_CONSTRUCTION_FAILED
    # scrubbed: no personal path, no secret value in the detail
    assert "C:\\Users" not in r["detail"]
    assert "fake-secret-value" not in r["detail"]


# --------------------------------------------------------------------------- #
# Readiness — ready path (no objects touched)
# --------------------------------------------------------------------------- #


def test_readiness_ready_touches_no_objects():
    captured: dict = {}
    fake = FakeClient
    r = rt.readiness_report(_FULL_ENV, client_factory=_factory_ok(captured))
    assert r["status"] == T2_PRIMARY_R2_RUNTIME_CLIENT_READY
    assert r["dry_run"] == T2_PRIMARY_R2_DRY_RUN_READY_NO_OBJECTS_TOUCHED
    assert r["objects_touched"] is False
    assert r["deposit_performed"] is False and r["restore_performed"] is False
    assert fake  # sanity


def test_readiness_report_contains_no_secret_values():
    captured: dict = {}
    r = rt.readiness_report(_FULL_ENV, client_factory=_factory_ok(captured))
    blob = str(r)
    assert "fake-secret-value" not in blob
    assert "fake-access-key" not in blob


def test_dry_run_never_calls_object_ops():
    client = FakeClient()

    def factory(*, config, access_key_id, secret_access_key):
        return client

    rt.readiness_report(_FULL_ENV, client_factory=factory)
    assert client.calls == []  # no put/head/get/lock during readiness


# --------------------------------------------------------------------------- #
# build_runtime_client
# --------------------------------------------------------------------------- #


def test_build_runtime_client_success_passes_creds_to_factory():
    captured: dict = {}
    client = rt.build_runtime_client(_FULL_ENV, client_factory=_factory_ok(captured))
    assert isinstance(client, FakeClient)
    # the factory received the real values (to hand to a real client), and the
    # values live only in the local capture — never in a returned/loggable obj
    assert captured["access_key_id"] == "fake-access-key"
    assert captured["bucket"] == "t2-bucket-alias"


def test_build_runtime_client_missing_creds_returns_none():
    assert rt.build_runtime_client({}, client_factory=_factory_ok({})) is None


def test_build_runtime_client_error_is_scrubbed():
    with pytest.raises(RuntimeError) as ei:
        rt.build_runtime_client(_FULL_ENV, client_factory=_factory_boom)
    assert "C:\\Users" not in str(ei.value)
    assert "fake-secret-value" not in str(ei.value)


# --------------------------------------------------------------------------- #
# Phase C1 integration point (fake injection) + default fail-closed
# --------------------------------------------------------------------------- #


def test_resolve_phase_c1_with_fake_client_returns_r2():
    captured: dict = {}
    dest = rt.resolve_phase_c1_destination(_FULL_ENV, client_factory=_factory_ok(captured))
    assert isinstance(dest, R2Destination)


def test_resolve_phase_c1_without_creds_is_unavailable():
    dest = rt.resolve_phase_c1_destination({}, client_factory=_factory_ok({}))
    assert isinstance(dest, UnavailableR2Destination)


def test_resolve_phase_c1_construction_failure_is_unavailable():
    dest = rt.resolve_phase_c1_destination(_FULL_ENV, client_factory=_factory_boom)
    assert isinstance(dest, UnavailableR2Destination)


def test_default_no_arg_resolution_still_fail_closed():
    from scripts.foundation_t2.destination import resolve_primary_destination

    assert isinstance(resolve_primary_destination(), UnavailableR2Destination)


# --------------------------------------------------------------------------- #
# CLI dry-run
# --------------------------------------------------------------------------- #


def test_cli_dry_run_reports_status_only(capsys):
    # Real environment here has no T2 credentials → CREDENTIALS_NOT_PRESENT.
    rc = rt.main([])
    assert rc == 0
    out = capsys.readouterr().out
    assert "status" in out
    # no credential value can appear (there are none set); guard against the
    # literal env-var names leaking a value form
    assert "SECRET_ACCESS_KEY=" not in out


def test_pr395_stop_evidence_untouched():
    root = Path(__file__).resolve().parents[2]
    manifest = (
        root
        / "artifacts"
        / "foundation_t2"
        / "phase_c1_365d_ba_pilot"
        / ("t2_phase_c1_365d_ba_manifest.json")
    )
    assert manifest.exists()
    text = manifest.read_text(encoding="utf-8")
    # the committed stop status is intact and not turned into a success
    assert "T2_C1_STOPPED_BEFORE_DEPOSIT_CREDENTIALS_UNAVAILABLE_OR_UNSAFE" in text
    assert "T2_C1_365D_BA_ROUND_TRIP_EVIDENCE_CREATED" not in text
