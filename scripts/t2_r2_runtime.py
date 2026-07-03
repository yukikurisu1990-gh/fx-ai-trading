"""T2_PRIMARY_R2 runtime client construction + dry-run readiness.

This module lives OUTSIDE the pure ``scripts/foundation_t2`` package (which is
kept env-free / network-free and is guarded as such). It is the integration
point where a LATER, separately-authorised Phase C1 re-run constructs a real
Cloudflare R2 / S3-compatible client from operator-provisioned config and
injects it into ``resolve_primary_destination(config=..., client=...)``.

This PR does NOT execute Phase C1, deposit, restore, or perform a real round
trip. The dry-run readiness command reports readiness states ONLY and touches
no objects.

Boundaries enforced here:

- **Reads only the specific required env vars** (never dumps the environment).
- **Credential VALUES are never logged, printed, or serialised.** They are read
  at the last moment and handed straight to the injected client factory.
- **No cloud SDK is a hard dependency.** The default client factory imports
  boto3 lazily and fails closed (``T2_PRIMARY_R2_CLIENT_CONSTRUCTION_FAILED``)
  if it is unavailable; a future run may instead inject its own factory.
- **Fail-closed:** missing credentials/config → unavailable / not-ready status.

Statuses: T2_PRIMARY_R2_RUNTIME_CLIENT_READY, T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT,
T2_PRIMARY_R2_CONFIG_INCOMPLETE, T2_PRIMARY_R2_CLIENT_CONSTRUCTION_FAILED,
T2_PRIMARY_R2_DRY_RUN_READY_NO_OBJECTS_TOUCHED, REAL_T2_EXECUTION_NOT_PERFORMED,
PHASE_C1_RERUN_NOT_AUTHORISED.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Protocol

# Import the foundation_t2 package by its CANONICAL path (scripts.foundation_t2)
# so class identities match the rest of the codebase (isinstance works). Add the
# repo root — not the scripts dir — to sys.path for standalone CLI execution.
_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from scripts.foundation_t2.constants import (  # noqa: E402
    PHASE_C1_RERUN_NOT_AUTHORISED,
    REAL_T2_EXECUTION_NOT_PERFORMED,
    T2_OBJECT_KEY_NAMESPACE,
    T2_PRIMARY_R2_CLIENT_CONSTRUCTION_FAILED,
    T2_PRIMARY_R2_CONFIG_INCOMPLETE,
    T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT,
    T2_PRIMARY_R2_DRY_RUN_READY_NO_OBJECTS_TOUCHED,
    T2_PRIMARY_R2_RUNTIME_CLIENT_READY,
)
from scripts.foundation_t2.destination import (  # noqa: E402
    Destination,
    UnavailableR2Destination,
    resolve_primary_destination,
)
from scripts.foundation_t2.r2_adapter import (  # noqa: E402
    R2Client,
    R2DestinationConfig,
    scrub_error_text,
)

# Logical role -> env-var NAME. Only these specific names are ever consulted.
R2_ENV_VARS: dict[str, str] = {
    "access_key_id": "T2_PRIMARY_R2_ACCESS_KEY_ID",
    "secret_access_key": "T2_PRIMARY_R2_SECRET_ACCESS_KEY",
    "endpoint": "T2_PRIMARY_R2_ENDPOINT",
    "bucket": "T2_PRIMARY_R2_BUCKET",
    "region": "T2_PRIMARY_R2_REGION",
    "object_prefix": "T2_PRIMARY_R2_OBJECT_PREFIX",
    "retention_expectation": "T2_PRIMARY_R2_RETENTION_EXPECTATION",
}
# Names that MUST be present (secret credentials + minimal destination config).
_REQUIRED_CREDENTIAL_ROLES = ("access_key_id", "secret_access_key")
_REQUIRED_CONFIG_ROLES = ("endpoint", "bucket")

_NON_AUTHORISATION = (
    REAL_T2_EXECUTION_NOT_PERFORMED,
    PHASE_C1_RERUN_NOT_AUTHORISED,
    "BYTE_ADMISSIBILITY_NOT_APPROVED",
    "NEW_EPOCH_NOT_ADOPTED",
    "ML_STEP4_NOT_AUTHORISED",
    "PRODUCTION_READINESS_NOT_CLAIMED",
)


class ClientFactory(Protocol):
    """Constructs an :class:`R2Client` from config + credential values.

    Credential values are passed positionally at the last moment and must never
    be logged by any implementation.
    """

    def __call__(
        self,
        *,
        config: R2DestinationConfig,
        access_key_id: str,
        secret_access_key: str,
    ) -> R2Client: ...


# --------------------------------------------------------------------------- #
# Presence checks (NAMES only) and non-secret config
# --------------------------------------------------------------------------- #


def env_presence(env: Mapping[str, str]) -> dict[str, bool]:
    """Return {logical_role: name_present} — NAMES only, never values."""
    return {role: (name in env) for role, name in R2_ENV_VARS.items()}


def credentials_present(env: Mapping[str, str]) -> bool:
    return all(R2_ENV_VARS[r] in env for r in _REQUIRED_CREDENTIAL_ROLES)


def required_config_present(env: Mapping[str, str]) -> bool:
    return all(R2_ENV_VARS[r] in env for r in _REQUIRED_CONFIG_ROLES)


def config_from_env(env: Mapping[str, str]) -> R2DestinationConfig:
    """Build a NON-SECRET config from env. Reads bucket / endpoint / region /
    prefix / retention only — never the access key or secret."""
    return R2DestinationConfig(
        bucket=env.get(R2_ENV_VARS["bucket"]),
        endpoint=env.get(R2_ENV_VARS["endpoint"]),
        region=env.get(R2_ENV_VARS["region"]),
        object_prefix=env.get(R2_ENV_VARS["object_prefix"], T2_OBJECT_KEY_NAMESPACE),
        retention_expectation=env.get(R2_ENV_VARS["retention_expectation"], "object_lock_required"),
    )


# --------------------------------------------------------------------------- #
# Default client factory (lazy boto3; not a hard dependency)
# --------------------------------------------------------------------------- #


class _Boto3R2Client:
    """Adapts a boto3 S3 client to the :class:`R2Client` interface.

    Constructing this does NOT touch the network (boto3 client creation is
    lazy). Real object I/O only happens when deposit/restore are called — which
    this PR never does.
    """

    def __init__(self, s3: Any, bucket: str) -> None:
        self._s3 = s3
        self._bucket = bucket

    def put_object(self, key: str, local_path: Path) -> dict[str, Any]:
        with open(local_path, "rb") as fh:
            resp = self._s3.put_object(Bucket=self._bucket, Key=key, Body=fh)
        return {"etag": resp.get("ETag"), "size_bytes": Path(local_path).stat().st_size}

    def head_object(self, key: str) -> dict[str, Any]:
        resp = self._s3.head_object(Bucket=self._bucket, Key=key)
        return {
            "present": True,
            "size_bytes": resp.get("ContentLength"),
            "storage_class": resp.get("StorageClass", "STANDARD"),
            "retention_mode": resp.get("ObjectLockMode", "NONE"),
        }

    def get_object(self, key: str, dest_path: Path) -> None:
        self._s3.download_file(self._bucket, key, str(dest_path))

    def get_object_lock(self, key: str) -> dict[str, Any] | None:
        resp = self._s3.get_object_retention(Bucket=self._bucket, Key=key)
        ret = resp.get("Retention") if isinstance(resp, dict) else None
        if not ret:
            return None
        return {"mode": ret.get("Mode"), "retain_until": str(ret.get("RetainUntilDate"))}


def default_boto3_client_factory(
    *,
    config: R2DestinationConfig,
    access_key_id: str,
    secret_access_key: str,
) -> R2Client:
    """Build a boto3-backed R2 client. Lazy import; fail-closed if boto3 absent.

    Credential values are handed straight to boto3 and never logged here.
    """
    try:
        import boto3  # noqa: PLC0415 — lazy, optional, outside the guarded package
    except ImportError as exc:
        raise RuntimeError("boto3 not available for real R2 client construction") from exc
    s3 = boto3.client(
        "s3",
        endpoint_url=config.endpoint,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=config.region,
    )
    return _Boto3R2Client(s3, str(config.bucket))


# --------------------------------------------------------------------------- #
# Runtime client construction (reads credential VALUES at the last moment)
# --------------------------------------------------------------------------- #


def build_runtime_client(
    env: Mapping[str, str],
    *,
    config: R2DestinationConfig | None = None,
    client_factory: ClientFactory | None = None,
) -> R2Client | None:
    """Construct a runtime R2 client, or return None (fail-closed).

    Returns None if credentials/config are incomplete. Credential VALUES are
    read here at the last moment and passed straight to the factory; they are
    never logged or returned. Any factory error is scrubbed and raised as
    ``RuntimeError`` (caught by the readiness reporter).
    """
    if not credentials_present(env) or not required_config_present(env):
        return None
    cfg = config if config is not None else config_from_env(env)
    if not cfg.is_complete():
        return None
    factory = client_factory or default_boto3_client_factory
    access_key_id = env[R2_ENV_VARS["access_key_id"]]
    secret_access_key = env[R2_ENV_VARS["secret_access_key"]]
    try:
        return factory(
            config=cfg,
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
        )
    except Exception as exc:  # noqa: BLE001 — scrub then fail closed
        # Redact the exact credential values (a client error could echo them),
        # then apply the path/URL/token scrubber, before any message surfaces.
        msg = str(exc)
        for secret in (secret_access_key, access_key_id):
            if secret:
                msg = msg.replace(secret, "[REDACTED]")
        raise RuntimeError(scrub_error_text(msg)) from None


def resolve_phase_c1_destination(
    env: Mapping[str, str],
    *,
    config: R2DestinationConfig | None = None,
    client_factory: ClientFactory | None = None,
) -> Destination:
    """Integration point for a FUTURE authorised Phase C1 run.

    Builds config + runtime client and hands them to
    ``resolve_primary_destination``. Fail-closed to ``UnavailableR2Destination``
    when not ready. This function performs NO object I/O; a caller would still
    have to run the Phase C harness (deposit/restore) explicitly — which this PR
    does not do.
    """
    cfg = config if config is not None else config_from_env(env)
    try:
        client = build_runtime_client(env, config=cfg, client_factory=client_factory)
    except RuntimeError:
        return UnavailableR2Destination()
    if client is None:
        return UnavailableR2Destination()
    return resolve_primary_destination(config=cfg, client=client)


# --------------------------------------------------------------------------- #
# Dry-run readiness (touches NO objects)
# --------------------------------------------------------------------------- #


def readiness_report(
    env: Mapping[str, str],
    *,
    config: R2DestinationConfig | None = None,
    client_factory: ClientFactory | None = None,
) -> dict[str, Any]:
    """Report runtime readiness ONLY. Never uploads/downloads/mutates objects.

    Constructs the client (to prove construction succeeds) but calls no object
    operation. In an environment without credentials this short-circuits at
    ``T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT`` and constructs nothing.
    """
    presence = env_presence(env)
    base = {
        "env_var_presence": presence,
        "objects_touched": False,
        "deposit_performed": False,
        "restore_performed": False,
        "checksum_round_trip_performed": False,
        "non_authorisation": list(_NON_AUTHORISATION),
    }
    if not credentials_present(env):
        return {**base, "status": T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT}
    if not required_config_present(env):
        return {**base, "status": T2_PRIMARY_R2_CONFIG_INCOMPLETE}
    cfg = config if config is not None else config_from_env(env)
    if not cfg.is_complete():
        return {**base, "status": T2_PRIMARY_R2_CONFIG_INCOMPLETE}
    try:
        client = build_runtime_client(env, config=cfg, client_factory=client_factory)
    except RuntimeError as exc:
        # message already scrubbed by build_runtime_client
        return {
            **base,
            "status": T2_PRIMARY_R2_CLIENT_CONSTRUCTION_FAILED,
            "detail": scrub_error_text(str(exc)),
        }
    if client is None:
        return {**base, "status": T2_PRIMARY_R2_CLIENT_CONSTRUCTION_FAILED}
    return {
        **base,
        "status": T2_PRIMARY_R2_RUNTIME_CLIENT_READY,
        "dry_run": T2_PRIMARY_R2_DRY_RUN_READY_NO_OBJECTS_TOUCHED,
    }


# --------------------------------------------------------------------------- #
# CLI — dry-run readiness only
# --------------------------------------------------------------------------- #


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "T2_PRIMARY_R2 runtime readiness — DRY RUN ONLY. Reports readiness "
            "states; touches no objects; never deposits/restores; never prints "
            "credential values."
        )
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry-run readiness (the only supported mode).",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _parse_args(argv)
    # os.environ is consulted for NAME presence and non-secret config only; the
    # report never contains credential values (see readiness_report).
    report = readiness_report(os.environ)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
