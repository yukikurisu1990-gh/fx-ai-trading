"""One test per defect the **second** post-fix re-verification found.

Round two moved the guard to a `sys.addaudithook` and closed the round-one
holes. A fresh context then found that the round-two fix had itself created two
blockers and left five path-spelling bypasses open. This module pins each.

The through-line across three rounds: **a path decision made on a string is a
decision about a spelling, not about a file.** On this machine `data/`,
`FX-AI-~1\\data`, `\\\\localhost\\C$\\…\\data`, `\\\\.\\C:\\…\\data`, `DATA/` and a
junction all name the same directory, and only two of the six were caught.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.m15_track_a import authorization, containment, identity, isolation, scratch

REPO = scratch.repo_root()
UNC = r"\\localhost\C$" + str(REPO)[2:]
SHORT_REPO = r"C:\Users\yukik\FX-AI-~1"

#: Every spelling below is a Win32 namespace form — an 8.3 short name, an
#: administrative share, the device namespace. On a POSIX filesystem they are
#: ordinary relative names that address nothing, so the property under test does
#: not exist there. The CI runner is Linux.
WINDOWS_ONLY = pytest.mark.skipif(sys.platform != "win32", reason="Win32 path namespaces")

#: Whether this filesystem ignores case (NTFS and APFS do; the CI runner's does
#: not). A case variant of a ledger name is the *same file* only where this
#: holds.
CASE_INSENSITIVE_FS = (REPO / "docs").is_dir() and (REPO / "DOCS").is_dir()


@pytest.fixture
def guards() -> object:
    isolation.install_all()
    try:
        yield
    finally:
        isolation.uninstall_all()


@pytest.fixture
def scratch_at(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "track_a_scratch"
    root.mkdir()
    monkeypatch.setattr(scratch, "scratch_root", lambda: root)
    return root


# ---------------------------------------------------------------------------
# A path decision on a string is a decision about a spelling
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "path"),
    [
        ("plain", str(REPO / "data" / "__nx__.jsonl")),
        ("8.3 repo root", SHORT_REPO + r"\data\__nx__.jsonl"),
        ("8.3 artifacts", str(REPO) + r"\ARTIFA~1\oanda_archive_2026-05-31\__nx__"),
        ("UNC share", UNC + r"\data\__nx__.jsonl"),
        ("extended UNC", r"\\?\UNC\localhost\C$" + str(REPO)[2:] + r"\data\__nx__.jsonl"),
        ("device namespace", r"\\.\\" + str(REPO) + r"\data\__nx__.jsonl"),
    ],
)
@WINDOWS_ONLY
def test_every_spelling_of_a_market_data_read_refuses(
    guards: object, label: str, path: str
) -> None:
    """Five of these six reached the filesystem before this round.

    ``realpath`` expands the 8.3 name and the device namespace; the UNC forms it
    does not touch, and those are caught by filesystem identity instead —
    measured, all of these report the same ``st_dev``/``st_ino``.
    """
    if label.startswith("8.3") and not Path(SHORT_REPO).exists():
        pytest.skip("8.3 short names are not enabled on this volume")
    with pytest.raises(isolation.IsolationError), open(path, "rb"):  # noqa: PTH123
        pass


@pytest.mark.parametrize(
    ("label", "call"),
    [
        ("UNC open r+", lambda: open(UNC + r"\docs\__nx__.md", "r+")),  # noqa: PTH123, SIM115
        ("UNC mkdir", lambda: os.mkdir(UNC + r"\docs\__nx_dir__")),
        ("UNC rename out", lambda: os.rename(UNC + r"\data\__nx__", r"C:\Windows\Temp\__nx__")),
        ("8.3 open r+", lambda: open(SHORT_REPO + r"\docs\__nx__.md", "r+")),  # noqa: PTH123, SIM115
    ],
)
@WINDOWS_ONLY
def test_every_spelling_of_a_repository_write_refuses(
    guards: object, label: str, call: object
) -> None:
    """``os.rename`` of a candle file out of the repo was still open via ``\\\\localhost\\C$``."""
    if label.startswith("8.3") and not Path(SHORT_REPO).exists():
        pytest.skip("8.3 short names are not enabled on this volume")
    with pytest.raises(isolation.IsolationError):
        call()  # type: ignore[operator]


def test_a_junction_into_the_data_tree_refuses(tmp_path: Path) -> None:
    """Reads used ``abspath``; only writes resolved links, so a junction read real bytes.

    The link is created **before** the guards are armed — creating it afterwards
    is itself refused, because ``os.symlink`` names ``data/`` as its source.
    """
    link = tmp_path / "link_to_data"
    try:
        link.symlink_to(REPO / "data", target_is_directory=True)
    except (OSError, NotImplementedError):
        # A symlink needs privilege on Windows; a **junction** does not, and a
        # junction is the form an attacker would actually use. Falling back
        # means the defence is exercised somewhere rather than always skipped.
        if sys.platform != "win32":
            pytest.skip("link creation is not permitted on this host")
        made = subprocess.run(  # noqa: S603
            ["cmd", "/c", "mklink", "/J", str(link), str(REPO / "data")],
            capture_output=True,
            timeout=60,
            check=False,
        )
        if made.returncode != 0 or not link.exists():
            pytest.skip("neither a symlink nor a junction could be created on this host")
    isolation.install_all()
    try:
        with pytest.raises(isolation.IsolationError), open(link / "__nx__.jsonl", "rb"):  # noqa: PTH123
            pass
    finally:
        isolation.uninstall_all()


# ---------------------------------------------------------------------------
# The fix that stopped the interpreter working
# ---------------------------------------------------------------------------


def test_an_already_open_descriptor_is_permitted(guards: object) -> None:
    """``_normalise`` returned ``None`` for an int and the fix made ``None`` fatal.

    CPython writes every ``.pyc`` through ``_io.FileIO(fd, "wb")``, so a Track A
    run died on its first uncached import — and ``containment.audit()`` died
    with it, because it imports every package module. The suite passed only
    because ``__pycache__`` happened to be warm.
    """
    fd = os.open(os.devnull, os.O_WRONLY)
    with os.fdopen(fd, "w") as handle:
        handle.write("ok")


def test_a_cold_bytecode_cache_does_not_break_a_guarded_run(tmp_path: Path) -> None:
    """The end-to-end version of the above, in a subprocess with an empty cache."""
    env = dict(os.environ, PYTHONPYCACHEPREFIX=str(tmp_path / "cold"))
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'"
            + str(REPO)
            + "');"
            + "from scripts.m15_track_a import isolation, containment;"
            + "isolation.install_all();"
            + "import fractions, difflib, statistics, csv, uuid;"
            + "r = containment.audit();"
            + "print('AUDIT', r['status'], r['declared_gate_sequence_matches_at_this_head'])",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert (
        "AUDIT TRACK_A_EXECUTION_CONTAINMENT_PROBES_PASSED_BOUNDED_ASSURANCE True" in result.stdout
    )


# ---------------------------------------------------------------------------
# The append-only ledger, by six spellings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "suffix",
    ["", ".", " ", "::$DATA"],
    ids=["plain", "trailing-dot", "trailing-space", "ntfs-stream"],
)
@WINDOWS_ONLY
def test_a_ledger_cannot_be_truncated_by_a_win32_name_variant(
    guards: object, scratch_at: Path, suffix: str
) -> None:
    """Windows opens all four as the same file; the check compared the raw basename."""
    path = scratch_at / "exploratory_seen_ledger.jsonl"
    scratch.append_line(path, '{"probe": 1}')
    before = path.read_bytes()
    with pytest.raises(isolation.IsolationError), open(str(path) + suffix, "w"):  # noqa: PTH123
        pass
    assert path.read_bytes() == before


@pytest.mark.parametrize("name", ["EXPLORATORY_SEEN_LEDGER.JSONL", "Exploratory_Seen_Ledger.Jsonl"])
def test_a_ledger_cannot_be_truncated_by_a_case_variant(
    guards: object, scratch_at: Path, name: str
) -> None:
    """A case variant is the same file only on a case-insensitive filesystem."""
    if not CASE_INSENSITIVE_FS:
        pytest.skip("this filesystem is case-sensitive; the variant names another file")
    path = scratch_at / "exploratory_seen_ledger.jsonl"
    scratch.append_line(path, '{"probe": 1}')
    before = path.read_bytes()
    with pytest.raises(isolation.IsolationError), open(scratch_at / name, "w"):  # noqa: PTH123
        pass
    assert path.read_bytes() == before


@WINDOWS_ONLY
def test_a_ledger_cannot_be_truncated_through_os_open(guards: object, scratch_at: Path) -> None:
    path = scratch_at / "exploratory_seen_ledger.jsonl"
    scratch.append_line(path, '{"probe": 1}')
    with pytest.raises(isolation.IsolationError):
        os.open(str(path) + ".", os.O_WRONLY | os.O_TRUNC)
    assert path.read_bytes()


def test_an_abandoned_lock_is_broken_rather_than_blocking_forever(scratch_at: Path) -> None:
    """A lock leaks on SIGKILL, and one killed writer halted every ledger permanently."""
    path = scratch_at / "exploratory_seen_ledger.jsonl"
    lock = path.with_name(path.name + ".lock")
    lock.touch()
    # Age the lock by rewriting its mtime relative to its own stat, rather than
    # to the wall clock: the repository forbids a bare ``time.time()`` in tests.
    stale = lock.stat().st_mtime - scratch.APPEND_LOCK_STALE_SECONDS - 5
    os.utime(lock, (stale, stale))

    scratch.append_line(path, '{"after": "a broken lock"}')
    assert path.read_text(encoding="utf-8").strip() == '{"after": "a broken lock"}'
    assert not lock.exists()


def test_a_fresh_lock_is_not_broken(scratch_at: Path) -> None:
    """Staleness must not race a live writer."""
    path = scratch_at / "exploratory_seen_ledger.jsonl"
    lock = path.with_name(path.name + ".lock")
    lock.touch()
    scratch._break_lock_if_abandoned(lock)
    assert lock.exists()


# ---------------------------------------------------------------------------
# The read window and coroutines
# ---------------------------------------------------------------------------


def test_the_read_window_does_not_leak_to_a_sibling_coroutine(guards: object) -> None:
    """A ``threading.local`` is shared by every task on the thread."""

    async def sibling() -> str:
        try:
            with open(REPO / "data" / "__nx__.jsonl", "rb"):  # noqa: PTH123, SIM115
                return "opened"
        except isolation.IsolationError:
            return "refused"
        except OSError:
            return "reached-the-os"

    async def holder() -> str:
        with isolation.gated_read_window():
            return await asyncio.create_task(sibling())

    assert asyncio.run(holder()) == "refused", (
        "a task created inside the window inherited it — a ContextVar is copied "
        "into a child task, so the window has to be pinned to the task that opened it"
    )


# ---------------------------------------------------------------------------
# The containment audit
# ---------------------------------------------------------------------------


def test_a_read_route_that_calls_anything_but_its_gates_is_a_finding() -> None:
    """A body using ``numpy.memmap`` and a module global passed every earlier check.

    No ``return``, a terminal ``raise NotImplementedError``, and a name no
    reader list contained — so the answer cannot be a longer reader list. The
    check is an **allowlist** over the calls the route may make.
    """
    assert "NotImplementedError" in containment._PERMITTED_READ_ROUTE_CALLS
    for gate in ("require_authorization", "assert_span_admissible", "assert_declared"):
        assert gate in containment._PERMITTED_READ_ROUTE_CALLS
    assert "memmap" not in containment._PERMITTED_READ_ROUTE_CALLS
    assert "read_bytes" not in containment._PERMITTED_READ_ROUTE_CALLS


@pytest.mark.parametrize(
    "source",
    [
        "_r = builtins.open",
        '_r = getattr(builtins, "open")',
        '_r = {"o": builtins.open}["o"]',
        "_r, _u = builtins.open, None",
        "_r: object = builtins.open",
        "from builtins import open as _r",
        "if (_r := builtins.open) is not None:\n    pass",
        '_r = getattr(_pd, "read_parquet")',
    ],
)
def test_every_binding_form_of_a_reader_is_caught(source: str) -> None:
    """Seven of eight forms slipped past an ``ast.Assign``-only detector."""
    import ast

    findings = containment._alias_findings("probe", ast.parse(source))
    assert findings, f"not caught: {source!r}"


def test_no_market_data_read_is_gated_on_the_overall_verdict() -> None:
    """A BREACHED report still carried ``no_market_data_read: True``, quotable on its own."""
    report = containment.audit()
    if report["status"] == containment.STATUS_BREACHED:  # pragma: no cover - green today
        assert report["declared_gate_sequence_matches_at_this_head"] is False
    assert report["declared_gate_sequence_matches_at_this_head"] is (
        report["status"] == containment.STATUS_CONTAINED
        and all(
            check["passed"]
            for check in report["checks"]
            if check["check"] in {"read_body_declared", "market_data_read_refused"}
        )
    )


def test_the_documented_check_list_matches_the_code() -> None:
    """§11 said "twelve" and named eleven; the code banner said eight probes."""
    doc = (REPO / "docs" / "design" / "m15_track_a_execution_gate.md").read_text(encoding="utf-8")
    section = doc.split("## 11.")[1].split("## 12.")[0]
    # From the report, not by calling the checks directly: ``_check_subprocess``
    # really does try to launch one.
    names = {check["check"] for check in containment.audit()["checks"]}
    missing = sorted(name for name in names if f"`{name}`" not in section)
    assert not missing, f"§11 does not name {missing}"
    assert len(containment.CHECKS) == 12


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def test_the_identity_is_a_required_argument() -> None:
    """It defaulted to ``None`` and skipped the head comparison silently."""
    grant = authorization.ReadGrant(
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc="2025-06-01",
        span_end_utc="2025-06-30",
        pairs=("EUR_USD",),
        timeframe="M1",
        approved_head_sha="a" * 40,
        approver_record="PR #452 recorded approval",
    )
    with pytest.raises(TypeError, match="identity"):
        authorization.require_authorization(  # type: ignore[call-arg]
            grant,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc="2025-06-01",
            span_end_utc="2025-06-30",
            pairs=("EUR_USD",),
            timeframe="M1",
        )
    assert (
        authorization.require_authorization(
            grant,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc="2025-06-01",
            span_end_utc="2025-06-30",
            pairs=("EUR_USD",),
            timeframe="M1",
            identity=identity.RunIdentity(
                run_id="round-three",
                code_sha="a" * 40,
                calendar_semantics=identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
                started_at_utc="2026-01-01T00:00:00Z",
            ),
        )
        is grant
    )
