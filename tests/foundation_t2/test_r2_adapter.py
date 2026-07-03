"""T2_PRIMARY_R2 adapter tests — fake in-memory client only (no cloud, no creds).

All bytes are synthetic. No real OANDA candles, no local archive data, no real
R2, no network. Credential checks use a fake env dict (name presence only);
no real env value is ever read.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.foundation_t2.constants import (
    T2_PRIMARY_R2_ADAPTER_READY_WITH_MOCKS,
    T2_PRIMARY_R2_CONFIG_INCOMPLETE,
    T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT,
    T2_PRIMARY_R2_OBJECT_LOCK_NOT_OBSERVED,
    T2_PRIMARY_R2_OBJECT_LOCK_OBSERVED,
)
from scripts.foundation_t2.destination import (
    DestinationUnavailableError,
    UnavailableR2Destination,
    resolve_primary_destination,
)
from scripts.foundation_t2.r2_adapter import (
    R2Destination,
    R2DestinationConfig,
    build_object_key,
    config_env_present,
    credentials_present,
    readiness_status,
    scrub_error_text,
)

_FULL_ENV = {
    "T2_PRIMARY_R2_ACCESS_KEY_ID": "x",
    "T2_PRIMARY_R2_SECRET_ACCESS_KEY": "x",
    "T2_PRIMARY_R2_BUCKET": "x",
    "T2_PRIMARY_R2_ENDPOINT": "x",
}
_COMPLETE_CONFIG = R2DestinationConfig(bucket="t2-bucket-alias", object_prefix="t2")


# --------------------------------------------------------------------------- #
# Fake client (in-memory; models put/head/get/object-lock)
# --------------------------------------------------------------------------- #


class FakeR2Client:
    def __init__(self, *, object_lock: dict | None = None, fail_on: str | None = None):
        self._store: dict[str, Path] = {}
        self._object_lock = object_lock
        self._fail_on = fail_on

    def put_object(self, key: str, local_path: Path) -> dict:
        if self._fail_on == "put":
            raise RuntimeError("boto simulated failure at C:\\Users\\op\\secret put")
        target = local_path.parent / f"__remote__{key.replace('/', '_')}"
        shutil.copyfile(local_path, target)
        self._store[key] = target
        return {"etag": "fake-etag", "size_bytes": target.stat().st_size}

    def head_object(self, key: str) -> dict:
        if self._fail_on == "head":
            raise RuntimeError("head failed")
        p = self._store.get(key)
        return {
            "present": p is not None,
            "size_bytes": p.stat().st_size if p else None,
            "storage_class": "STANDARD",
            "retention_mode": "COMPLIANCE" if self._object_lock else "NONE",
        }

    def get_object(self, key: str, dest_path: Path) -> None:
        if self._fail_on == "get":
            raise RuntimeError("get failed")
        src = self._store[key]
        shutil.copyfile(src, dest_path)

    def get_object_lock(self, key: str) -> dict | None:
        return self._object_lock


def _mk(tmp_path: Path, name: str, data: bytes) -> Path:
    p = tmp_path / name
    p.write_bytes(data)
    return p


# --------------------------------------------------------------------------- #
# Credential / config readiness (presence-only)
# --------------------------------------------------------------------------- #


def test_credentials_present_uses_name_presence_only():
    assert credentials_present(env=_FULL_ENV) is True
    assert credentials_present(env={}) is False
    # partial credential set → not present
    assert credentials_present(env={"T2_PRIMARY_R2_ACCESS_KEY_ID": "x"}) is False


def test_config_env_present():
    assert config_env_present(env=_FULL_ENV) is True
    assert config_env_present(env={"T2_PRIMARY_R2_BUCKET": "x"}) is False


def test_readiness_missing_credentials_is_not_present():
    assert (
        readiness_status(env={}, config=_COMPLETE_CONFIG, client=FakeR2Client())
        == T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT
    )


def test_readiness_partial_credentials_is_not_present():
    env = {"T2_PRIMARY_R2_ACCESS_KEY_ID": "x", "T2_PRIMARY_R2_BUCKET": "x"}
    assert (
        readiness_status(env=env, config=_COMPLETE_CONFIG, client=FakeR2Client())
        == T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT
    )


def test_readiness_config_incomplete():
    assert (
        readiness_status(env=_FULL_ENV, config=R2DestinationConfig(), client=FakeR2Client())
        == T2_PRIMARY_R2_CONFIG_INCOMPLETE
    )


def test_readiness_no_client_is_not_ready():
    # creds + config present but no runtime client wired here → still not ready
    assert (
        readiness_status(env=_FULL_ENV, config=_COMPLETE_CONFIG, client=None)
        == T2_PRIMARY_R2_CONFIG_INCOMPLETE
    )


def test_readiness_ready_with_mocks():
    assert (
        readiness_status(env=_FULL_ENV, config=_COMPLETE_CONFIG, client=FakeR2Client())
        == T2_PRIMARY_R2_ADAPTER_READY_WITH_MOCKS
    )


# --------------------------------------------------------------------------- #
# Object-key construction
# --------------------------------------------------------------------------- #


def test_object_key_deterministic():
    k1 = build_object_key(
        config=_COMPLETE_CONFIG,
        phase="phase_c1",
        span_id="365d_BA",
        logical_file_id="candles_EUR_USD_M1_365d_BA.jsonl",
    )
    k2 = build_object_key(
        config=_COMPLETE_CONFIG,
        phase="phase_c1",
        span_id="365d_BA",
        logical_file_id="candles_EUR_USD_M1_365d_BA.jsonl",
    )
    assert k1 == k2 == "t2/phase_c1/365d_BA/candles_EUR_USD_M1_365d_BA.jsonl"


def test_object_key_confined_to_prefix_and_no_escape():
    k = build_object_key(
        config=_COMPLETE_CONFIG,
        phase="phase_c1",
        span_id="365d_BA",
        logical_file_id="../../etc/passwd",
    )
    # basename reduction defeats path escape
    assert k == "t2/phase_c1/365d_BA/passwd"
    assert ".." not in k.split("/")
    assert k.startswith("t2/")


def test_object_key_rejects_personal_path_component():
    with pytest.raises(ValueError):
        build_object_key(
            config=_COMPLETE_CONFIG,
            phase="phase_c1",
            span_id="365d_BA",
            logical_file_id="C:\\Users\\yukik\\secret.jsonl",
        )


def test_object_key_no_secrets_in_key():
    k = build_object_key(
        config=_COMPLETE_CONFIG,
        phase="phase_c1",
        span_id="365d_BA",
        logical_file_id="candles_EUR_USD_M1_365d_BA.jsonl",
        sha256_prefix="deadbeef",
    )
    assert "AKIA" not in k and "secret" not in k.lower()
    assert k.endswith("/deadbeef")


def test_phase_c1_rejects_expansion_spans_by_default():
    for span in ("730d_BA", "3650d_BA"):
        with pytest.raises(ValueError):
            build_object_key(
                config=_COMPLETE_CONFIG,
                phase="phase_c1",
                span_id=span,
                logical_file_id="candles_EUR_USD_M1.jsonl",
            )


def test_phase_c1_allows_expansion_only_with_explicit_flag():
    k = build_object_key(
        config=_COMPLETE_CONFIG,
        phase="phase_c1",
        span_id="730d_BA",
        logical_file_id="candles_EUR_USD_M1_730d_BA.jsonl",
        allow_expansion_spans=True,
    )
    assert k == "t2/phase_c1/730d_BA/candles_EUR_USD_M1_730d_BA.jsonl"


# --------------------------------------------------------------------------- #
# Mocked deposit / observe / restore / checksum round-trip
# --------------------------------------------------------------------------- #


def test_mock_round_trip_matches(tmp_path):
    from scripts.foundation_t2.checksums import sha256_and_size

    src = _mk(tmp_path, "candles_EUR_USD_M1_365d_BA.jsonl", b"synthetic-bytes-abc")
    exp_sha, exp_size = sha256_and_size(src)

    dest = R2Destination(config=_COMPLETE_CONFIG, client=FakeR2Client())
    ref = dest.deposit(src, "candles_EUR_USD_M1_365d_BA.jsonl")
    assert ref == "t2/phase_c1/365d_BA/candles_EUR_USD_M1_365d_BA.jsonl"

    obs = dest.observe(ref)
    assert obs["present"] is True and obs["size_bytes"] == exp_size

    restored = tmp_path / "restored.jsonl"
    dest.restore(ref, restored)
    got_sha, got_size = sha256_and_size(restored)
    assert got_sha == exp_sha and got_size == exp_size  # checksum match


def test_mock_checksum_mismatch_is_detectable(tmp_path):
    from scripts.foundation_t2.checksums import sha256_and_size

    src = _mk(tmp_path, "a.jsonl", b"original")
    dest = R2Destination(config=_COMPLETE_CONFIG, client=FakeR2Client())
    ref = dest.deposit(src, "a.jsonl")
    restored = tmp_path / "r.jsonl"
    dest.restore(ref, restored)
    # tamper the restored copy → mismatch is observable by the caller
    restored.write_bytes(b"tampered")
    assert sha256_and_size(restored)[0] != sha256_and_size(src)[0]


def test_deposit_error_fails_closed_and_scrubbed(tmp_path):
    src = _mk(tmp_path, "a.jsonl", b"x")
    dest = R2Destination(config=_COMPLETE_CONFIG, client=FakeR2Client(fail_on="put"))
    with pytest.raises(DestinationUnavailableError) as ei:
        dest.deposit(src, "a.jsonl")
    msg = str(ei.value)
    # personal path in the simulated error is redacted
    assert "C:\\Users" not in msg and "[REDACTED]" in msg


def test_restore_error_fails_closed(tmp_path):
    src = _mk(tmp_path, "a.jsonl", b"x")
    dest = R2Destination(config=_COMPLETE_CONFIG, client=FakeR2Client())
    ref = dest.deposit(src, "a.jsonl")
    dest2 = R2Destination(config=_COMPLETE_CONFIG, client=FakeR2Client(fail_on="get"))
    with pytest.raises(DestinationUnavailableError):
        dest2.restore(ref, tmp_path / "r.jsonl")


def test_incomplete_config_construction_fails_closed():
    with pytest.raises(DestinationUnavailableError):
        R2Destination(config=R2DestinationConfig(), client=FakeR2Client())


def test_missing_client_construction_fails_closed():
    with pytest.raises(DestinationUnavailableError):
        R2Destination(config=_COMPLETE_CONFIG, client=None)


# --------------------------------------------------------------------------- #
# Object-lock observation
# --------------------------------------------------------------------------- #


def test_object_lock_not_observed_status(tmp_path):
    src = _mk(tmp_path, "a.jsonl", b"x")
    dest = R2Destination(config=_COMPLETE_CONFIG, client=FakeR2Client(object_lock=None))
    ref = dest.deposit(src, "a.jsonl")
    obs = dest.observe_object_lock(ref)
    assert obs["object_lock_observed"] is False
    assert obs["status"] == T2_PRIMARY_R2_OBJECT_LOCK_NOT_OBSERVED


def test_object_lock_observed_status(tmp_path):
    src = _mk(tmp_path, "a.jsonl", b"x")
    lock = {"mode": "COMPLIANCE", "retain_until": "2036-01-01T00:00:00Z"}
    dest = R2Destination(config=_COMPLETE_CONFIG, client=FakeR2Client(object_lock=lock))
    ref = dest.deposit(src, "a.jsonl")
    obs = dest.observe_object_lock(ref)
    assert obs["object_lock_observed"] is True
    assert obs["status"] == T2_PRIMARY_R2_OBJECT_LOCK_OBSERVED
    assert obs["retention_mode"] == "COMPLIANCE"


# --------------------------------------------------------------------------- #
# Error scrubbing + fail-closed resolution
# --------------------------------------------------------------------------- #


def test_scrub_error_text_redacts_paths_and_urls():
    dirty = "failed at C:\\Users\\yukik\\k and https://b.example/o?X-Amz-Signature=abc"
    clean = scrub_error_text(dirty)
    assert "C:\\Users" not in clean
    assert "X-Amz-Signature=abc" not in clean
    assert "[REDACTED]" in clean


def test_resolve_primary_default_is_unavailable():
    # no injected config/client → fail-closed unavailable (unchanged contract)
    assert isinstance(resolve_primary_destination(), UnavailableR2Destination)


def test_resolve_primary_with_injection_returns_r2(tmp_path):
    dest = resolve_primary_destination(config=_COMPLETE_CONFIG, client=FakeR2Client())
    assert isinstance(dest, R2Destination)


def test_no_credential_value_appears_in_reports(tmp_path):
    # The adapter is constructed with a config that has NO secret fields; prove
    # no secret-like value can be emitted by deposit/observe references.
    src = _mk(tmp_path, "a.jsonl", b"x")
    dest = R2Destination(config=_COMPLETE_CONFIG, client=FakeR2Client())
    ref = dest.deposit(src, "a.jsonl")
    obs = dest.observe(ref)
    blob = f"{ref} {obs}"
    for needle in ("AKIA", "secret_access_key", "X-Amz-Signature", "Bearer "):
        assert needle not in blob
