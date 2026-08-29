"""One test per defect the **post-fix re-verification** found.

The round before this one replaced route-dependent attribute patches with a
`sys.addaudithook`. A fresh audit context then defeated that rewrite four more
ways — every one of them created by the fix. This module pins each.

The shape worth remembering: closing a class of hole by moving to a stronger
mechanism does not close the class, because the *new* mechanism has its own
surface. The hook saw `open` and nothing else; it read the mode without the
flags; its prefix test did not match the directory that exists; and it imported
its own dependency from inside itself.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from scripts.m15_track_a import authorization, containment, identity, isolation, oos_budget, scratch

REPO = scratch.repo_root()


@pytest.fixture
def scratch_at(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "track_a_scratch"
    root.mkdir()
    monkeypatch.setattr(scratch, "scratch_root", lambda: root)
    return root


@pytest.fixture
def guards() -> object:
    isolation.install_all()
    try:
        yield
    finally:
        isolation.uninstall_all()


# ---------------------------------------------------------------------------
# The hook saw `open` and no other filesystem event
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "call"),
    [
        ("os.replace", lambda: os.replace("__nope__", str(REPO / "docs" / "x.md"))),
        ("os.rename", lambda: os.rename("__nope__", str(REPO / "docs" / "x.md"))),
        # ``Path.unlink`` raises the same ``os.remove`` audit event, and the
        # repository forbids the bare call in tests (Archiver rule).
        ("os.remove", lambda: (REPO / "docs" / "__nope__.md").unlink()),
        ("os.mkdir", lambda: os.mkdir(str(REPO / "docs" / "__nope_dir__"))),
        ("os.rmdir", lambda: os.rmdir(str(REPO / "docs" / "__nope_dir__"))),
        ("os.truncate", lambda: os.truncate(str(REPO / "docs" / "__nope__.md"), 0)),
        ("os.link", lambda: os.link(str(REPO / "docs" / "__n__.md"), str(REPO / "docs" / "l.md"))),
        ("os.chmod", lambda: os.chmod(str(REPO / "docs" / "__nope__.md"), 0o644)),
    ],
)
def test_every_mutating_filesystem_event_is_refused(
    guards: object, label: str, call: object
) -> None:
    """``os.rename`` of a candle file out of the repository was a complete escape."""
    with pytest.raises(isolation.IsolationError):
        call()  # type: ignore[operator]


def test_os_open_is_recognised_as_a_write(guards: object) -> None:
    """CPython passes ``mode=None`` for ``os.open`` and puts the flags in ``args[2]``."""
    with pytest.raises(isolation.IsolationError):
        os.open(str(REPO / "docs" / "__nope__x"), os.O_WRONLY | os.O_CREAT)


def test_path_touch_and_mkstemp_are_writes(guards: object) -> None:
    """Both go through ``os.open``, so both were classified as reads."""
    with pytest.raises(isolation.IsolationError):
        (REPO / "docs" / "__nope__.md").touch()
    with pytest.raises(isolation.IsolationError):
        tempfile.mkstemp(dir=str(REPO / "docs"))


def test_writes_outside_the_repository_are_still_permitted(guards: object) -> None:
    """The guard confines the repository; it is not a sandbox over the machine."""
    with tempfile.NamedTemporaryFile(delete=False) as handle:
        handle.write(b"ok")
    Path(handle.name).unlink()


# ---------------------------------------------------------------------------
# The market-data prefix test did not match the directory that exists
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "data/__nope__.jsonl",
        "DATA/__nope__.jsonl",
        "Data/__nope__.jsonl",
        "artifacts/oanda_archive_2026-05-31/__nope__",
        "artifacts/oanda_archive/__nope__",
    ],
)
def test_every_spelling_of_the_market_data_trees_refuses(guards: object, relative: str) -> None:
    """``"artifacts/oanda_archive_2026-05-31".startswith("artifacts/oanda_archive/")`` is False.

    The committed 10-year archive was readable from anywhere in the process.
    """
    with pytest.raises(isolation.IsolationError), open(REPO / relative, "rb"):  # noqa: PTH123
        pass


def test_an_extended_unc_spelling_refuses(guards: object) -> None:
    """``Path.resolve`` does not canonicalise ``\\\\?\\``; the guard strips it first."""
    target = "\\\\?\\" + str(REPO / "data" / "__nope__.jsonl")
    with pytest.raises(isolation.IsolationError), open(target, "rb"):  # noqa: PTH123
        pass


# ---------------------------------------------------------------------------
# The hook imported its own dependency from inside itself
# ---------------------------------------------------------------------------


def test_install_all_works_in_a_process_that_has_not_imported_scratch() -> None:
    """The documented entry point crashed on a cold import.

    The lazy ``from scripts.m15_track_a import scratch`` inside the hook ran its
    own ``open`` calls, which re-entered the hook against a half-initialised
    module. Every test file imports ``scratch`` at module top, so the suite
    never saw it — only a real caller did.
    """
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'"
            + str(REPO)
            + "');"
            + "from scripts.m15_track_a import isolation;"
            + "isolation.install_all();"
            + "print('OK', isolation.is_installed())",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "OK True" in result.stdout


# ---------------------------------------------------------------------------
# Two more lying-object shapes on the destination
# ---------------------------------------------------------------------------


def test_a_tuple_subclass_cannot_hide_the_destination_by_lying_about_its_length(
    guards: object,
) -> None:
    """The fix pinned ``tuple.__getitem__`` and missed ``tuple.__len__``."""

    class ZeroLength(tuple):  # noqa: SLOT001 - the lying override is the point
        def __len__(self) -> int:
            return 0

    with pytest.raises(isolation.IsolationError):
        isolation._check_destination(ZeroLength(("203.0.113.9", 80)), how="connect to")


def test_a_str_subclass_cannot_hide_the_host(guards: object) -> None:
    """``str(host_value)`` called a lying ``__str__``; CPython reads the real buffer."""

    class Innocent(str):
        def __str__(self) -> str:
            return "127.0.0.1"

    assert not isolation._is_loopback(Innocent("203.0.113.9"))
    with pytest.raises(isolation.IsolationError):
        isolation._check_destination((Innocent("203.0.113.9"), 80), how="connect to")


# ---------------------------------------------------------------------------
# Fail-closed, and the window's scope
# ---------------------------------------------------------------------------


def test_the_guard_fails_closed_when_it_cannot_resolve_its_own_roots(
    guards: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``None`` used to mean "outside the repository, therefore permitted"."""

    def explode() -> Path:
        raise OSError("the root is gone")

    monkeypatch.setattr(scratch, "repo_root", explode)
    with pytest.raises(isolation.IsolationError):
        isolation.assert_write_allowed(str(REPO / "docs" / "__nope__.md"))


def test_an_internal_failure_surfaces_as_an_isolation_error(
    guards: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A non-IsolationError used to escape the hook and break unrelated I/O."""

    def explode() -> Path:
        raise RuntimeError("boom")

    monkeypatch.setattr(scratch, "repo_root", explode)
    with pytest.raises(isolation.IsolationError):
        isolation.assert_write_allowed(str(REPO / "docs" / "__nope__.md"))


def test_the_read_window_is_thread_local(guards: object) -> None:
    """One thread's gated read must not open ``data/`` to every other thread."""
    other: list[object] = []

    def in_another_thread() -> None:
        try:
            with open(REPO / "data" / "__nope__.jsonl", "rb"):  # noqa: PTH123, SIM115
                other.append("opened")
        except isolation.IsolationError:
            other.append("refused")
        except OSError:
            other.append("reached-the-os")

    with isolation.gated_read_window():
        thread = threading.Thread(target=in_another_thread)
        thread.start()
        thread.join()
    assert other == ["refused"]


def test_the_read_window_is_reentrant(guards: object) -> None:
    """A nested window used to close the outer one on exit."""
    with isolation.gated_read_window():
        with isolation.gated_read_window():
            assert isolation.is_read_window_open()
        assert isolation.is_read_window_open(), "the inner exit closed the outer window"
    assert not isolation.is_read_window_open()


def test_a_partial_network_install_is_fully_reverted() -> None:
    """``uninstall_all`` reverted only ``if state.network``, which a partial install never sets."""
    isolation.uninstall_all()
    import socket

    original = socket.socket.connect
    state = isolation._ensure_state()
    state.patched.append((socket.socket, "connect", original))
    socket.socket.connect = lambda *a, **k: None  # type: ignore[method-assign]
    isolation.uninstall_all()
    assert socket.socket.connect is original


# ---------------------------------------------------------------------------
# The ledgers
# ---------------------------------------------------------------------------


def test_the_append_lock_holds_across_processes(tmp_path: Path) -> None:
    """``O_APPEND`` is emulated as seek-then-write by the Windows CRT.

    The previous round measured 105–113 of 120 lines with four processes while
    its docstring claimed atomicity "on both POSIX and Windows". With the lock,
    six measured rounds were 120/120.
    """
    root = tmp_path / "track_a_scratch"
    root.mkdir()
    worker = tmp_path / "worker.py"
    worker.write_text(
        "import sys, pathlib\n"
        f"sys.path.insert(0, r'{REPO}')\n"
        "from scripts.m15_track_a import scratch\n"
        f"scratch.scratch_root = lambda: pathlib.Path(r'{root}')\n"
        "path = scratch.scratch_root() / 'exploratory_seen_ledger.jsonl'\n"
        "for i in range(20):\n"
        '    scratch.append_line(path, \'{"w": "\' + sys.argv[1] + \'", "i": %d}\' % i)\n',
        encoding="utf-8",
    )
    procs = [
        subprocess.Popen(  # noqa: S603
            [sys.executable, str(worker), name], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        for name in ("a", "b", "c")
    ]
    for proc in procs:
        _, err = proc.communicate(timeout=180)
        assert proc.returncode == 0, err.decode("utf-8", "replace")

    lines = (root / "exploratory_seen_ledger.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 60, f"lost {60 - len(lines)} of 60 lines"
    assert all(json.loads(line) for line in lines), "a line was interleaved into another"


def test_the_budget_consults_the_ledger_as_well_as_the_claim_files(scratch_at: Path) -> None:
    """Counting claims alone was fail-open: the spend was recorded and never consulted."""
    observation = oos_budget.SliceObservation(
        run_id="reverify-run",
        slice_start_utc="2026-01-01",
        slice_end_utc="2026-01-31",
        purpose="probe",
    )
    run = identity.RunIdentity(
        run_id="reverify-run",
        code_sha="a" * 40,
        calendar_semantics=identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        started_at_utc="2026-01-01T00:00:00Z",
    )
    oos_budget.consume(observation, run)
    oos_budget.claim_path(1).unlink()
    assert oos_budget.observations_spent() == 1, "deleting the claim reset the budget"
    with pytest.raises(oos_budget.OosBudgetError):
        oos_budget.consume(observation, run)


# ---------------------------------------------------------------------------
# Authorization and the audit
# ---------------------------------------------------------------------------


def test_a_request_naming_no_pairs_is_refused() -> None:
    """``all(...)`` over an empty tuple is True, so an empty request matched every grant."""
    grant = authorization.ReadGrant(
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc="2025-06-01",
        span_end_utc="2025-06-30",
        pairs=("EUR_USD",),
        timeframe="M1",
        approved_head_sha="a" * 40,
        approver_record="PR #452 recorded approval",
    )
    with pytest.raises(authorization.AuthorizationMalformedError):
        authorization.grant_covers(
            grant,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc="2025-06-01",
            span_end_utc="2025-06-30",
            pairs=(),
            timeframe="M1",
        )


def test_the_identity_is_pinned_to_its_own_type() -> None:
    """A duck-typed head check accepts any object carrying the right attribute."""

    class Impostor:
        code_sha = "a" * 40

    grant = authorization.ReadGrant(
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc="2025-06-01",
        span_end_utc="2025-06-30",
        pairs=("EUR_USD",),
        timeframe="M1",
        approved_head_sha="a" * 40,
        approver_record="PR #452 recorded approval",
    )
    with pytest.raises(authorization.AuthorizationError, match="RunIdentity"):
        authorization.require_authorization(
            grant,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc="2025-06-01",
            span_end_utc="2025-06-30",
            pairs=("EUR_USD",),
            timeframe="M1",
            identity=Impostor(),
        )


def test_a_dead_raise_does_not_satisfy_the_read_body_check() -> None:
    """``if False: raise NotImplementedError`` above a live body defeated the first check."""
    import ast

    decoy = ast.parse(
        "def read_historical():\n"
        "    if False:\n"
        "        raise NotImplementedError('x')\n"
        "    return open('p', 'rb').read()\n"
    ).body[0]
    assert isinstance(decoy, ast.FunctionDef)
    assert not containment._terminal_raise_is_not_implemented(decoy.body)

    honest = ast.parse("def read_historical():\n    raise NotImplementedError('x')\n").body[0]
    assert isinstance(honest, ast.FunctionDef)
    assert containment._terminal_raise_is_not_implemented(honest.body)


def test_no_market_data_read_needs_both_the_source_and_the_behavioural_check() -> None:
    """Either alone has been defeated: the source check by a decoy, the probe by never calling."""
    report = containment.audit()
    by_name = {check["check"]: check["passed"] for check in report["checks"]}
    assert report["no_market_data_read"] is (
        by_name["read_body_absent"] and by_name["market_data_read_refused"]
    )
    assert report["no_market_data_read"] is True


def test_an_aliased_reader_is_caught_by_the_structural_sweep() -> None:
    """``_reader = builtins.open`` then ``_reader(path)`` hid the call from the name sweep."""
    assert "open" in containment._READER_NAMES
    assert "connect" not in containment._READER_NAMES, (
        "a database verb in the file-reader set made the sweep flag the isolation guard's "
        "own `real_connect = socket.socket.connect`"
    )
