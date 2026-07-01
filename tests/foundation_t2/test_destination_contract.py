"""Foundation T2 destination-interface tests (local-mock only, no cloud)."""

from __future__ import annotations

import pytest

from scripts.foundation_t2.constants import PRIMARY_DESTINATION_ALIAS
from scripts.foundation_t2.destination import (
    DestinationUnavailableError,
    LocalMockDestination,
    UnavailableR2Destination,
    resolve_primary_destination,
)


def test_local_mock_round_trips_bytes(tmp_path):
    store = tmp_path / "store"
    dest = LocalMockDestination(store)
    src = tmp_path / "src.bin"
    src.write_bytes(b"hello-mock")
    ref = dest.deposit(src, "src.bin")
    assert ref.startswith("mock://")
    obs = dest.observe(ref)
    assert obs["present"] is True and obs["size_bytes"] == len(b"hello-mock")
    restored = tmp_path / "restored.bin"
    dest.restore(ref, restored)
    assert restored.read_bytes() == b"hello-mock"


def test_unavailable_r2_raises_on_all_ops(tmp_path):
    dest = UnavailableR2Destination()
    assert dest.alias == PRIMARY_DESTINATION_ALIAS
    with pytest.raises(DestinationUnavailableError):
        dest.deposit(tmp_path / "x", "x")
    with pytest.raises(DestinationUnavailableError):
        dest.observe("mock://x/y")
    with pytest.raises(DestinationUnavailableError):
        dest.restore("mock://x/y", tmp_path / "z")


def test_resolve_primary_is_unavailable_here():
    dest = resolve_primary_destination()
    assert isinstance(dest, UnavailableR2Destination)
