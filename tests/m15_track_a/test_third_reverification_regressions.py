"""One test per defect the **third** post-fix re-verification found.

The heaviest finding in this whole PR is here: `sys.addaudithook` is route-
independent only for what goes through CPython's own I/O. `pyarrow`'s file
layer is C++ and raises no Python audit event, so it read `data/` and wrote
into `docs/` with every guard installed — and this repository already depends
on it. No in-process mechanism closes that class; the guarantee is bounded by
a named list, and the module says so.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from scripts.m15_track_a import containment, identity, isolation, scratch, seen_ledger

REPO = scratch.repo_root()


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


def _ledger(root: Path) -> Path:
    path = root / seen_ledger.LEDGER_FILENAME
    scratch.append_line(path, '{"probe": 1}')
    return path


# ---------------------------------------------------------------------------
# The class of hole an audit hook cannot see
# ---------------------------------------------------------------------------


def test_a_native_reader_cannot_read_the_market_data_tree(guards: object) -> None:
    """`pa.OSFile` is C++ and raises no audit event. It read `data/` regardless."""
    pa = pytest.importorskip("pyarrow")
    with pytest.raises(isolation.IsolationError):
        pa.OSFile(str(REPO / "data" / "__nx__.jsonl"), "rb")
    with pytest.raises(isolation.IsolationError):
        pa.memory_map(str(REPO / "data" / "__nx__.jsonl"), "r")


def test_a_native_reader_cannot_write_into_the_repository(guards: object) -> None:
    pa = pytest.importorskip("pyarrow")
    with pytest.raises(isolation.IsolationError):
        pa.OSFile(str(REPO / "docs" / "__nx__.bin"), "wb")


def test_the_repositorys_own_parquet_reader_is_guarded(guards: object) -> None:
    """`scripts/evaluate_ml_baseline.py` calls `pq.read_table`; the feature store is parquet."""
    pq = pytest.importorskip("pyarrow.parquet")
    with pytest.raises(isolation.IsolationError):
        pq.read_table(str(REPO / "data" / "__nx__.parquet"))


def test_a_native_reader_is_refused_everywhere_not_classified(guards: object) -> None:
    """The guard **refuses**; it does not try to work out which argument is a path.

    An earlier drafting wrapped each target and guessed. A re-verification took
    that apart four ways at once, because fifteen heterogeneous APIs do not
    share a signature: ``pa.output_stream`` has no ``mode``, so it was called a
    read and wrote into ``docs/``; ``pq.write_table``'s first argument is a
    Table, so every call was refused *including outside the repository*, while
    the keyword form was not checked at all.

    Refusing outright costs the use of pyarrow inside a Track A run — which R1
    does not need, because it has no read body — and buys a guard with no
    argument parsing to get wrong.
    """
    pa = pytest.importorskip("pyarrow")
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as handle:
        handle.write(b"payload")
    try:
        with pytest.raises(isolation.IsolationError):
            pa.OSFile(handle.name, "rb")
    finally:
        Path(handle.name).unlink()
    isolation.uninstall_all()
    with pa.OSFile(__file__, "rb") as stream:
        assert stream.read(1)  # unarmed, the dependency is untouched


def test_the_bounded_guarantee_is_stated_rather_than_implied() -> None:
    """A denylist of C entry points is the honest shape; it must not read as complete."""
    assert ("pyarrow", "OSFile") in isolation.NATIVE_REFUSED_TARGETS
    assert ("pyarrow.parquet", "read_table") in isolation.NATIVE_REFUSED_TARGETS
    source = Path(isolation.__file__).read_text(encoding="utf-8")
    assert "No in-process mechanism can close that class" in source


# ---------------------------------------------------------------------------
# Created by the round-three fix: the cache exemption laundered a protected tree
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "data/__pycache__/candles.jsonl",
        "data/.pytest_cache/candles.jsonl",
        "artifacts/oanda_archive_2026-05-31/__pycache__/x",
    ],
)
def test_a_cache_directory_inside_a_protected_tree_does_not_launder_it(
    guards: object, relative: str
) -> None:
    """Refused at the previous head, permitted at the next — the classifier reordered it.

    `any(part in caches for part in parts)` ran *before* the market-data test,
    so `data/__pycache__/candles.jsonl` classified as a build cache.
    """
    with pytest.raises(isolation.IsolationError), open(REPO / relative, "rb"):  # noqa: PTH123
        pass
    with pytest.raises(isolation.IsolationError):
        isolation.assert_write_allowed(str(REPO / relative))


def test_a_cache_directory_inside_dot_git_does_not_launder_it(guards: object) -> None:
    """`.git` was taken off the cache list and came back as `.git/__pycache__/…`."""
    with pytest.raises(isolation.IsolationError):
        isolation.assert_write_allowed(str(REPO / ".git" / "__pycache__" / "x"))


def test_a_real_bytecode_cache_is_still_writable(guards: object) -> None:
    """The exemption exists for `.pyc` files and must keep working."""
    isolation.assert_write_allowed(str(REPO / "scripts" / "__pycache__" / "x.pyc"))


def test_consumed_holdout_evidence_is_not_readable(guards: object) -> None:
    """Exploratory design tuned against a consumed-holdout figure is the same leakage."""
    with (
        pytest.raises(isolation.IsolationError),
        open(REPO / "artifacts" / "ml_step4" / "__nx__.json", "rb"),  # noqa: PTH123
    ):
        pass


# ---------------------------------------------------------------------------
# Created by the round-three fix: fail-open past the walk limit
# ---------------------------------------------------------------------------


@pytest.mark.skipif(sys.platform != "win32", reason="needs a second spelling of the volume")
def test_a_path_too_deep_to_classify_fails_closed(guards: object) -> None:
    """`return None` past the limit meant "outside the repository", i.e. permitted."""
    unc = r"\\localhost\C$" + str(REPO)[2:]
    deep = unc + "\\" + "\\".join(["d"] * 300) + r"\x"
    with pytest.raises(isolation.IsolationError), open(deep, "rb"):  # noqa: PTH123
        pass


# ---------------------------------------------------------------------------
# The ledger, from every mutating event rather than from `open` alone
# ---------------------------------------------------------------------------


def test_an_appending_descriptor_cannot_truncate_the_ledger(
    guards: object, scratch_at: Path
) -> None:
    """`file.truncate()` becomes `os.ftruncate`, and ints were skipped."""
    path = _ledger(scratch_at)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        with pytest.raises(isolation.IsolationError):
            os.ftruncate(fd, 0)
    finally:
        os.close(fd)
    assert path.read_bytes()


@pytest.mark.parametrize(
    ("label", "attack"),
    [
        ("os.truncate", lambda p: os.truncate(p, 0)),
        ("unlink", lambda p: p.unlink()),
        ("rename away", lambda p: os.rename(p, str(p) + ".stash")),
        ("replace over", lambda p: os.replace(str(p) + ".decoy", p)),
    ],
)
def test_the_ledger_survives_every_mutating_event(
    guards: object, scratch_at: Path, label: str, attack: object
) -> None:
    path = _ledger(scratch_at)
    (scratch_at / (path.name + ".decoy")).write_bytes(b"decoy")
    with pytest.raises(isolation.IsolationError):
        attack(path)  # type: ignore[operator]
    assert path.read_bytes() == b'{"probe": 1}\n'


def test_a_legitimate_append_still_works(guards: object, scratch_at: Path) -> None:
    path = _ledger(scratch_at)
    scratch.append_line(path, '{"probe": 2}')
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_the_append_lock_is_released_only_by_its_own_holder(scratch_at: Path) -> None:
    """A stalled holder used to delete a lock a second writer had since taken."""
    path = scratch_at / seen_ledger.LEDGER_FILENAME
    lock = path.with_name(path.name + ".lock")
    lock.write_bytes(b"somebody-else")
    scratch._break_lock_if_abandoned(lock)  # too fresh to break
    assert lock.read_bytes() == b"somebody-else"


# ---------------------------------------------------------------------------
# The read window
# ---------------------------------------------------------------------------


def test_reusing_one_window_object_does_not_raise_or_leak(guards: object) -> None:
    """One shared `_token` meant the outer `__exit__` reset a used Token — and raised."""
    window = isolation.gated_read_window()
    with window, window:
        assert isolation.is_read_window_open()
    assert not isolation.is_read_window_open()


def test_the_window_closes_even_if_its_token_is_unusable(guards: object) -> None:
    window = isolation.gated_read_window()
    window.__enter__()
    window._tokens.clear()
    window.__exit__()
    assert not isolation.is_read_window_open()


# ---------------------------------------------------------------------------
# The containment audit
# ---------------------------------------------------------------------------


def test_a_call_the_check_cannot_name_is_a_finding_not_an_exemption() -> None:
    """`_T["slurp"](path)` has a `Subscript` callee, so there was no name to compare."""
    tree = ast.parse(
        '_B = __import__("builtins")\n'
        '_G = getattr(_B, "g" + "etattr")\n'
        '_T = {"slurp": _G(_B, "open")}\n'
        "def read_historical(request, identity, *, grant=None):\n"
        "    if not is_installed():\n"
        '        raise ReadRouteError("isolation")\n'
        '    _CACHE["bytes"] = _T["slurp"]("p", "rb")\n'
        '    raise NotImplementedError("no data was read")\n'
    )
    function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    offenders: set[str] = set()
    for child in ast.walk(function):
        if isinstance(child, ast.Call) and not isinstance(child.func, ast.Name | ast.Attribute):
            offenders.add("subscript-callee")
    assert offenders, "a callee with no name must be a finding"
    assert containment._alias_findings("evil", tree), "the module sweep must see the indirection"


@pytest.mark.parametrize(
    "source",
    [
        '_r = getattr(builtins, "op" + "en")',
        '_r = __import__("builtins").open',
        '_b = vars(builtins)["open"]',
        '_e = eval("open")',
    ],
)
def test_a_runtime_constructed_reader_name_is_a_finding(source: str) -> None:
    assert containment._alias_findings("probe", ast.parse(source)), f"not caught: {source!r}"


def test_the_check_split_is_pinned_and_matches_the_document() -> None:
    """`broker_live_demo` attempts nothing — calling it a probe overstated it."""
    report = containment.audit()
    names = {check["check"] for check in report["checks"]}
    assert names == set(containment.BEHAVIOURAL_CHECKS) | set(containment.SOURCE_CHECKS)
    assert len(containment.BEHAVIOURAL_CHECKS) == 6
    assert len(containment.SOURCE_CHECKS) == 6
    assert "broker_live_demo" in containment.SOURCE_CHECKS

    doc = (REPO / "docs" / "design" / "m15_track_a_execution_gate.md").read_text(encoding="utf-8")
    section = doc.split("## 11.")[1].split("## 12.")[0]
    behavioural = section.split("source checks")[0]
    for name in containment.BEHAVIOURAL_CHECKS:
        assert f"`{name}`" in behavioural, f"§11 does not list {name} as behavioural"
    for name in containment.SOURCE_CHECKS:
        assert f"`{name}`" in section, f"§11 does not name {name}"


def test_a_cold_bytecode_cache_still_works_with_the_native_guard(tmp_path: Path) -> None:
    """The native guard imports optional dependencies; that must not break a cold run."""
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
            + "import fractions, difflib, csv;"
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


def test_a_directory_descriptor_open_is_refused(guards: object) -> None:
    """The `open` audit event does not carry `dir_fd`, so the path resolves wrongly."""
    if not os.supports_dir_fd:
        pytest.skip("dir_fd is unavailable on this platform")
    dir_fd = os.open(str(REPO / "docs"), os.O_RDONLY)
    try:
        with pytest.raises(isolation.IsolationError):
            os.open("__nx__.md", os.O_RDONLY, dir_fd=dir_fd)
    finally:
        os.close(dir_fd)


def test_the_run_identity_is_caller_asserted_and_says_so() -> None:
    """`code_sha` is never derived from the running tree; the docstring must not imply it is."""
    source = Path(identity.__file__).read_text(encoding="utf-8")
    assert "caller-supplied" in source or "caller-asserted" in source
