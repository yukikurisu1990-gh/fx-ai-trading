"""The write root confines Track A, and the isolation guards refuse everything else."""

from __future__ import annotations

import socket

import pytest

from scripts.m15_track_a import isolation, scratch
from scripts.m15_track_a.scratch import ScratchRootError, assert_writable, repo_root, scratch_root

# --------------------------------------------------------------------------
# Q8 — the scratch root
# --------------------------------------------------------------------------


def test_a_path_inside_the_scratch_root_is_writable() -> None:
    assert assert_writable(scratch_root() / "run-1" / "summary.json")


@pytest.mark.parametrize(
    "relative",
    [
        "docs/note.md",
        "data/candles.parquet",
        "models/model.pkl",
        "src/fx_ai_trading/x.py",
        "scripts/x.py",
        "tests/x.py",
        "artifacts/ml_step4/365d_ba_v1/report.json",
        "artifacts/gate_p1_pr_b/firstrun_365d_ba/x.json",
        "artifacts/oanda_archive_2026-05-31/x.json",
    ],
)
def test_protected_roots_refuse(relative: str) -> None:
    with pytest.raises(ScratchRootError):
        assert_writable(repo_root() / relative)


def test_artifacts_m15_gate3a_refuses_even_though_the_gate3a_guard_permits_it() -> None:
    """NR-A leaves this root out of ``guards._PROTECTED_PREFIXES``; §8.11.9 item 6 forbids it."""
    from scripts.m15_gate3a import guards

    target = repo_root() / "artifacts" / "m15_gate3a" / "design_m15_inventory.json"

    # The gate-3a guard does not refuse it — that is the gap this module closes.
    guards.refuse_real_path(target)

    with pytest.raises(ScratchRootError):
        assert_writable(target)


def test_a_sibling_of_the_scratch_root_is_not_inside_it() -> None:
    with pytest.raises(ScratchRootError):
        assert_writable(scratch_root().parent / "track_a_scratch_evil" / "x.json")


def test_traversal_out_of_the_scratch_root_refuses() -> None:
    with pytest.raises(ScratchRootError):
        assert_writable(scratch_root() / ".." / ".." / "docs" / "x.md")


@pytest.mark.parametrize("name", sorted(scratch.RESERVED_ARTIFACT_FILENAMES))
def test_a_committed_artifacts_canonical_filename_refuses_inside_the_root(name: str) -> None:
    """§8.12.13 G-9: a file that looks like evidence can be cited as evidence."""
    with pytest.raises(ScratchRootError):
        assert_writable(scratch_root() / name)


def test_a_relative_path_refuses() -> None:
    """``path_authority`` refuses relative spellings outright — the verdict is cwd-independent."""
    with pytest.raises(ScratchRootError):
        assert_writable("artifacts/track_a_scratch/x.json")


# --------------------------------------------------------------------------
# Isolation
# --------------------------------------------------------------------------


@pytest.fixture
def guards_installed() -> object:
    isolation.install_all()
    yield
    isolation.uninstall_all()


def test_guards_report_installed(guards_installed: object) -> None:
    assert isolation.is_installed()


def test_non_loopback_connect_refuses(guards_installed: object) -> None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(isolation.IsolationError):
            probe.connect(("203.0.113.1", 80))
    finally:
        probe.close()


def test_non_loopback_datagram_refuses(guards_installed: object) -> None:
    """A ``connect``-only guard misses ``sendto`` — the residual route FR-19 recorded."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        with pytest.raises(isolation.IsolationError):
            probe.sendto(b"x", ("203.0.113.1", 53))
    finally:
        probe.close()


def test_name_resolution_refuses(guards_installed: object) -> None:
    """A lookup reaches a resolver before any connect happens."""
    with pytest.raises(isolation.IsolationError):
        socket.getaddrinfo("example.invalid", 80)
    with pytest.raises(isolation.IsolationError):
        socket.gethostbyname("example.invalid")


@pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.2", "::1", "localhost", "LOCALHOST"])
def test_loopback_is_permitted(guards_installed: object, host: str) -> None:
    """The whole loopback range, not four spellings of it."""
    from scripts.m15_track_a.isolation import _is_loopback

    assert _is_loopback(host)


def test_a_bytes_host_is_handled(guards_installed: object) -> None:
    from scripts.m15_track_a.isolation import _is_loopback

    assert _is_loopback(b"127.0.0.1")
    assert not _is_loopback(b"203.0.113.1")


def test_remote_database_engine_refuses(guards_installed: object) -> None:
    sqlalchemy = pytest.importorskip("sqlalchemy")
    with pytest.raises(isolation.IsolationError):
        sqlalchemy.create_engine("postgresql://user:pw@example.invalid/db")


def test_in_memory_sqlite_is_permitted(guards_installed: object) -> None:
    sqlalchemy = pytest.importorskip("sqlalchemy")
    engine = sqlalchemy.create_engine("sqlite://")
    assert engine is not None


@pytest.mark.parametrize("operation", sorted(isolation.FORBIDDEN_OPERATIONS))
def test_named_forbidden_operations_refuse(operation: str) -> None:
    with pytest.raises(isolation.IsolationError):
        isolation.assert_operation_allowed(operation)


def test_uninstall_restores_the_primitives() -> None:
    original = socket.socket.connect
    isolation.install_all()
    assert socket.socket.connect is not original
    isolation.uninstall_all()
    assert socket.socket.connect is original
