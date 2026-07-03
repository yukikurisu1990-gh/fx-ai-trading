"""T2_PRIMARY_R2 destination adapter — readiness-only (no real cloud here).

This module implements a real, safely-gated adapter path for the
``T2_PRIMARY_R2`` retention destination so that a LATER, explicitly-authorised
Phase C1 re-run can attempt the 365d_BA deposit/restore/checksum round-trip.

Hard boundaries enforced here:

- **No cloud SDK is imported and no network call is made.** All object I/O flows
  through an injected, duck-typed ``client`` (a fake in tests; a real R2 client
  built from operator credentials — outside this module — in a future run).
- **Credentials are checked by env-var NAME presence only.** This module never
  reads, prints, logs, or serialises a credential VALUE. If a runtime client
  needs values, the operator passes them straight to the client at construction,
  outside this module.
- **Fail-closed:** missing/partial credentials, missing/ambiguous config, or any
  client error → :class:`DestinationUnavailableError` with a scrubbed message.
- **No round-trip success is ever claimed here.** Readiness statuses top out at
  ``T2_PRIMARY_R2_ADAPTER_READY_WITH_MOCKS`` / ``T2_PRIMARY_R2_MOCK_ROUNDTRIP_TESTED``.

Statuses: T2_PRIMARY_R2_ADAPTER_WIRED_FOR_FUTURE_USE,
REAL_T2_EXECUTION_NOT_PERFORMED, PHASE_C1_RERUN_NOT_AUTHORISED,
BYTE_ADMISSIBILITY_NOT_APPROVED, NEW_EPOCH_NOT_ADOPTED, ML_STEP4_NOT_AUTHORISED,
PRODUCTION_READINESS_NOT_CLAIMED.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from .constants import (
    LOCAL_PATH_PATTERNS,
    PHASE_C1_ALLOWED_SPANS,
    R2_CONFIG_ENV_VARS,
    R2_CREDENTIAL_ENV_VARS,
    SECRET_VALUE_PATTERNS,
    T2_OBJECT_KEY_NAMESPACE,
    T2_PRIMARY_R2_ADAPTER_READY_WITH_MOCKS,
    T2_PRIMARY_R2_CONFIG_INCOMPLETE,
    T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT,
    T2_PRIMARY_R2_OBJECT_LOCK_NOT_OBSERVED,
    T2_PRIMARY_R2_OBJECT_LOCK_OBSERVED,
)
from .destination import Destination, DestinationUnavailableError

# Object-key components may contain only these characters after sanitising.
_SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._-]+$")


# --------------------------------------------------------------------------- #
# Config (non-secret)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class R2DestinationConfig:
    """Non-secret destination config. Contains NO access key / secret.

    ``bucket`` and ``endpoint`` are operational identifiers, not secrets, but
    are still supplied at runtime rather than hardcoded. ``object_prefix`` is the
    deterministic key root under which all Phase C1 objects live.
    """

    alias: str = "T2_PRIMARY_R2"
    bucket: str | None = None
    endpoint: str | None = None
    region: str | None = None
    object_prefix: str = T2_OBJECT_KEY_NAMESPACE
    retention_expectation: str = "object_lock_required"

    def is_complete(self) -> bool:
        return bool(self.bucket) and bool(self.object_prefix)


# --------------------------------------------------------------------------- #
# Credential / config readiness — NAME PRESENCE ONLY (never values)
# --------------------------------------------------------------------------- #


def credentials_present(env: Mapping[str, str]) -> bool:
    """True iff every required credential env-var NAME is present in ``env``.

    Presence-only: uses ``name in env`` and never reads ``env[name]``. This
    package NEVER reads the process environment itself — the caller (a future
    authorised runner, outside this package) injects ``env`` (the process
    environment mapping). Keeping the package env-free preserves the harness
    no-env / no-network invariant.
    """
    return all(name in env for name in R2_CREDENTIAL_ENV_VARS)


def config_env_present(env: Mapping[str, str]) -> bool:
    """True iff every required config env-var NAME is present (presence-only)."""
    return all(name in env for name in R2_CONFIG_ENV_VARS)


def readiness_status(
    *,
    env: Mapping[str, str],
    config: R2DestinationConfig | None = None,
    client: Any = None,
) -> str:
    """Return a precise, non-success readiness status.

    Never returns a round-trip success status. When a fake/mock client is
    injected alongside a complete config, reports ADAPTER_READY_WITH_MOCKS.
    """
    if not credentials_present(env=env):
        return T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT
    if config is None or not config.is_complete():
        if not config_env_present(env=env):
            return T2_PRIMARY_R2_CONFIG_INCOMPLETE
        return T2_PRIMARY_R2_CONFIG_INCOMPLETE
    if client is None:
        # Credentials + config present but no runtime client wired here — this
        # module never builds a real one. A future authorised run injects it.
        return T2_PRIMARY_R2_CONFIG_INCOMPLETE
    return T2_PRIMARY_R2_ADAPTER_READY_WITH_MOCKS


# --------------------------------------------------------------------------- #
# Deterministic object-key construction
# --------------------------------------------------------------------------- #


def _sanitize_component(value: str) -> str:
    """Reduce to a safe basename component or raise. No path escape possible.

    A raw value that looks like a local/personal absolute path (drive letter,
    ``/Users/``, ``/home/``, ``AppData``) is rejected fail-closed BEFORE basename
    reduction, so a personal path can never leak into a key even by reduction.
    Relative traversal (``../x``) is safely reduced to its basename.
    """
    raw = str(value)
    for pattern in LOCAL_PATH_PATTERNS:
        if pattern.search(raw):
            raise ValueError("object-key component contains a local/personal path")
    base = os.path.basename(raw.replace("\\", "/"))
    if not base or base in {".", ".."}:
        raise ValueError(f"unsafe object-key component: {value!r}")
    if not _SAFE_COMPONENT.match(base):
        raise ValueError(f"object-key component has unsafe characters: {base!r}")
    return base


def build_object_key(
    *,
    config: R2DestinationConfig,
    phase: str,
    span_id: str,
    logical_file_id: str,
    sha256_prefix: str | None = None,
    allow_expansion_spans: bool = False,
) -> str:
    """Build a deterministic, prefix-confined object key.

    For ``phase == "phase_c1"`` only ``365d_BA`` is permitted unless
    ``allow_expansion_spans`` is explicitly set (a later command). The key
    cannot escape ``config.object_prefix`` and contains no personal path or
    secret.
    """
    phase_c = _sanitize_component(phase)
    if (
        phase_c == "phase_c1"
        and not allow_expansion_spans
        and span_id not in PHASE_C1_ALLOWED_SPANS
    ):
        raise ValueError(
            f"span {span_id!r} is not in the Phase C1 pilot set "
            f"{PHASE_C1_ALLOWED_SPANS}; expansion spans require an explicit "
            "later command (allow_expansion_spans=True)"
        )
    span_c = _sanitize_component(span_id)
    file_c = _sanitize_component(logical_file_id)
    prefix = config.object_prefix.strip("/")
    if not prefix:
        raise ValueError("config.object_prefix must be non-empty")
    parts = [prefix, phase_c, span_c, file_c]
    if sha256_prefix:
        parts.append(_sanitize_component(sha256_prefix))
    key = "/".join(parts)
    if ".." in key.split("/") or key.startswith("/"):
        raise ValueError("constructed object key escapes its prefix")
    if not key.startswith(prefix + "/"):
        raise ValueError("constructed object key is outside the configured prefix")
    return key


# --------------------------------------------------------------------------- #
# Error scrubbing
# --------------------------------------------------------------------------- #


def scrub_error_text(text: str) -> str:
    """Redact any local path / signed-URL / token value from an error string.

    Secret-value patterns (signed URLs, bearer tokens) run FIRST — the
    drive-letter local-path pattern would otherwise match ``s:/`` inside
    ``https://`` and break the URL before its signed-URL pattern could redact
    the embedded signature.
    """
    scrubbed = str(text)
    for pattern in (*SECRET_VALUE_PATTERNS, *LOCAL_PATH_PATTERNS):
        scrubbed = pattern.sub("[REDACTED]", scrubbed)
    return scrubbed


# --------------------------------------------------------------------------- #
# Duck-typed runtime client (fake in tests; real R2 client in a future run)
# --------------------------------------------------------------------------- #


class R2Client(Protocol):
    """Minimal object-store client the adapter drives. No cloud SDK required.

    A real implementation would wrap an S3/R2 client (put/head/get/retention);
    it is constructed OUTSIDE this module from operator credentials and injected.
    """

    def put_object(self, key: str, local_path: Path) -> dict[str, Any]: ...

    def head_object(self, key: str) -> dict[str, Any]: ...

    def get_object(self, key: str, dest_path: Path) -> None: ...

    def get_object_lock(self, key: str) -> dict[str, Any] | None: ...


# --------------------------------------------------------------------------- #
# The adapter
# --------------------------------------------------------------------------- #


class R2Destination(Destination):
    """Real-shaped R2 destination driven by an injected client (fail-closed).

    Constructing this class does NOT access the network. It only becomes usable
    when handed a working client + complete config; in tests that client is a
    fake. All client errors are caught and re-raised as
    :class:`DestinationUnavailableError` with scrubbed messages.
    """

    alias = "T2_PRIMARY_R2"

    def __init__(
        self,
        *,
        config: R2DestinationConfig,
        client: R2Client,
        phase: str = "phase_c1",
        span_id: str = "365d_BA",
        allow_expansion_spans: bool = False,
    ) -> None:
        if not config.is_complete():
            raise DestinationUnavailableError(T2_PRIMARY_R2_CONFIG_INCOMPLETE)
        if client is None:
            raise DestinationUnavailableError(T2_PRIMARY_R2_CREDENTIALS_NOT_PRESENT)
        self._config = config
        self._client = client
        self._phase = phase
        self._span_id = span_id
        self._allow_expansion_spans = allow_expansion_spans

    def _key(self, logical_file_id: str) -> str:
        return build_object_key(
            config=self._config,
            phase=self._phase,
            span_id=self._span_id,
            logical_file_id=logical_file_id,
            allow_expansion_spans=self._allow_expansion_spans,
        )

    def deposit(self, local_path: Path, logical_file_id: str) -> str:
        key = self._key(logical_file_id)
        try:
            self._client.put_object(key, Path(local_path))
        except DestinationUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001 — scrub then fail closed
            raise DestinationUnavailableError(scrub_error_text(str(exc))) from None
        # The returned reference is the non-secret object key (no bucket/secret).
        return key

    def observe(self, remote_ref: str) -> dict[str, Any]:
        try:
            meta = self._client.head_object(remote_ref)
        except DestinationUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DestinationUnavailableError(scrub_error_text(str(exc))) from None
        return {
            "remote_logical_reference": remote_ref,
            "present": bool(meta.get("present", True)),
            "size_bytes": meta.get("size_bytes"),
            "storage_class": meta.get("storage_class", "unknown"),
            "retention_mode": meta.get("retention_mode", "unknown"),
        }

    def restore(self, remote_ref: str, dest_path: Path) -> None:
        try:
            self._client.get_object(remote_ref, Path(dest_path))
        except DestinationUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DestinationUnavailableError(scrub_error_text(str(exc))) from None

    def observe_object_lock(self, remote_ref: str) -> dict[str, Any]:
        try:
            lock = self._client.get_object_lock(remote_ref)
        except DestinationUnavailableError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise DestinationUnavailableError(scrub_error_text(str(exc))) from None
        if not lock:
            return {
                "remote_logical_reference": remote_ref,
                "object_lock_observed": False,
                "status": T2_PRIMARY_R2_OBJECT_LOCK_NOT_OBSERVED,
            }
        return {
            "remote_logical_reference": remote_ref,
            "object_lock_observed": True,
            "retention_mode": lock.get("mode", "unknown"),
            "retain_until": lock.get("retain_until"),
            "status": T2_PRIMARY_R2_OBJECT_LOCK_OBSERVED,
        }
