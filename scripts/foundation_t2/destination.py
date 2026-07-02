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


def resolve_primary_destination() -> Destination:
    """Resolve the real primary destination for this environment.

    This PR never has real R2 credentials/config available and never accesses
    env-vars or the network, so the primary destination is always the
    unavailable stub. A future operator run wires a real adapter here under
    explicit authorisation.
    """
    return UnavailableR2Destination()
