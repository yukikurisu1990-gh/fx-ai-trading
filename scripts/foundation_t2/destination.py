"""Destination interface for the Foundation T2 harness.

An abstract Destination defines deposit -> observe -> restore. CI / tests use
``LocalMockDestination`` (filesystem-backed, in a temp dir) — no cloud, no
credentials, no network. ``UnavailableR2Destination`` represents the real
primary destination when it is NOT configured / credentialed in this
environment: it never reads env-vars or the network; it simply reports
unavailable so the harness stops before deposit.
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .constants import PRIMARY_DESTINATION_ALIAS, T2_CREDENTIALS_UNAVAILABLE


class DestinationUnavailableError(RuntimeError):
    """Raised when the real destination is not safely available in this context."""


class Destination(ABC):
    alias: str

    @abstractmethod
    def deposit(self, local_path: Path, logical_file_id: str) -> str:
        """Deposit bytes; return a non-secret logical remote reference."""

    @abstractmethod
    def observe(self, remote_ref: str) -> dict[str, Any]:
        """Return non-secret remote object metadata."""

    @abstractmethod
    def restore(self, remote_ref: str, dest_path: Path) -> None:
        """Restore bytes from the remote reference to ``dest_path``."""

    def observe_object_lock(self, remote_ref: str) -> dict[str, Any]:
        """Return a non-secret object-lock / retention observation.

        Default: object-lock is NOT observed (fail-closed for admissibility
        purposes). Real adapters override this. Never returns secrets.
        """
        return {
            "remote_logical_reference": remote_ref,
            "object_lock_observed": False,
            "status": "T2_PRIMARY_R2_OBJECT_LOCK_NOT_OBSERVED",
        }


class LocalMockDestination(Destination):
    """Filesystem-backed mock 'remote' store for CI / harness validation only."""

    alias = "T2_LOCAL_MOCK"

    def __init__(self, store_dir: Path) -> None:
        self._store = Path(store_dir)
        self._store.mkdir(parents=True, exist_ok=True)

    def deposit(self, local_path: Path, logical_file_id: str) -> str:
        target = self._store / logical_file_id
        shutil.copyfile(local_path, target)
        return f"mock://{self.alias}/{logical_file_id}"

    def observe(self, remote_ref: str) -> dict[str, Any]:
        name = remote_ref.rsplit("/", 1)[-1]
        obj = self._store / name
        return {
            "remote_logical_reference": remote_ref,
            "present": obj.exists(),
            "size_bytes": obj.stat().st_size if obj.exists() else None,
            "storage_class": "mock_standard",
            "retention_mode": "mock_not_applicable",
        }

    def restore(self, remote_ref: str, dest_path: Path) -> None:
        name = remote_ref.rsplit("/", 1)[-1]
        shutil.copyfile(self._store / name, dest_path)


class UnavailableR2Destination(Destination):
    """The real primary destination when not configured/credentialed here.

    It performs NO env-var / network / cloud access. Any operation reports
    unavailable so the harness stops before deposit (never fakes success).
    """

    alias = PRIMARY_DESTINATION_ALIAS

    def deposit(self, local_path: Path, logical_file_id: str) -> str:
        raise DestinationUnavailableError(T2_CREDENTIALS_UNAVAILABLE)

    def observe(self, remote_ref: str) -> dict[str, Any]:
        raise DestinationUnavailableError(T2_CREDENTIALS_UNAVAILABLE)

    def restore(self, remote_ref: str, dest_path: Path) -> None:
        raise DestinationUnavailableError(T2_CREDENTIALS_UNAVAILABLE)


def resolve_primary_destination(
    *,
    config: Any = None,
    client: Any = None,
) -> Destination:
    """Resolve the primary destination.

    Fail-closed by default: with no explicitly-injected ``config`` AND
    ``client``, this returns :class:`UnavailableR2Destination` — it never reads
    env-var values, never constructs a real cloud client, and never accesses the
    network. This is the state in the current environment (no operator
    credentials, no real adapter wired), so the no-argument call still returns
    the unavailable stub.

    A future, separately-authorised Phase C1 re-run supplies BOTH a validated
    :class:`~scripts.foundation_t2.r2_adapter.R2DestinationConfig` and a runtime
    R2 client (built from operator credentials outside this module) — only then
    is a real :class:`~scripts.foundation_t2.r2_adapter.R2Destination` returned.
    This module does not build that client.
    """
    if config is not None and client is not None:
        # Local import to avoid a hard dependency cycle; the adapter imports
        # nothing from the network / no cloud SDK.
        from .r2_adapter import R2Destination

        return R2Destination(config=config, client=client)
    return UnavailableR2Destination()
