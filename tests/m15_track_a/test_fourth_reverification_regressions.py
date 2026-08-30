"""One test per defect the **fourth** post-fix re-verification found.

Round four added a native-reader guard to close the C-extension finding, and
that guard became the largest hole in the head: a generic wrapper that guessed
which argument was a path and whether the call was a read or a write, applied
to fifteen APIs that do not share a signature. It opened a write route into
`docs/`, `src/` and the append-only ledger that had not existed before.

The lesson, and the reason round five looks different: **when a guard has to
understand its target's arguments to be correct, and the targets are
heterogeneous, refuse instead.** Track A R1 has no read body, so it has nothing
to parse and no reason to call any of them.
"""

from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.m15_track_a import containment, isolation, scratch, seen_ledger

REPO = scratch.repo_root()
WINDOWS_ONLY = pytest.mark.skipif(sys.platform != "win32", reason="Win32 path namespaces")


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
# The native guard refuses rather than classifies
# ---------------------------------------------------------------------------


def test_a_native_writer_with_no_mode_parameter_is_refused(guards: object) -> None:
    """`pa.output_stream` has no `mode`, so the wrapper called it a read.

    A "read" was refused only for market data, so it wrote into `docs/`, into
    `src/`, and truncated the append-only ledger — the exact route the previous
    head's documentation listed as closed.
    """
    pa = pytest.importorskip("pyarrow")
    with pytest.raises(isolation.IsolationError):
        pa.output_stream(str(REPO / "docs" / "__nx__.bin"))


def test_a_native_writer_whose_first_argument_is_not_a_path_is_refused(guards: object) -> None:
    """`pq.write_table(table, where)` — reading `args[0]` as a path was a guess."""
    pq = pytest.importorskip("pyarrow.parquet")
    with pytest.raises(isolation.IsolationError):
        pq.write_table(None, str(REPO / "docs" / "__nx__.parquet"))
    with pytest.raises(isolation.IsolationError):
        pq.write_table(table=None, where=str(REPO / "docs" / "__nx__.parquet"))


def test_the_keyword_spelling_of_a_listed_reader_is_refused(guards: object) -> None:
    """The wrapper looked for `path=`/`source=`; pyarrow names it `input_file`."""
    csv = pytest.importorskip("pyarrow.csv")
    with pytest.raises(isolation.IsolationError):
        csv.read_csv(input_file=str(REPO / "data" / "__nx__.csv"))


def test_a_listed_class_target_is_actually_guarded(guards: object) -> None:
    """`pa.fs.LocalFileSystem` is a class; wrapping the constructor checked nothing.

    It was on the list, so the document told a reviewer it was refused, and the
    instance methods were the unpatched originals.
    """
    fs = pytest.importorskip("pyarrow.fs")
    with pytest.raises(isolation.IsolationError):
        fs.LocalFileSystem().open_input_file(str(REPO / "data" / "__nx__.bin"))


def test_guarding_a_class_does_not_break_isinstance() -> None:
    """Binding a class name to a *function* made `isinstance` raise, process-wide.

    Twice: round four did it, round five's note claimed the list held no class
    targets — it held seven — and it came straight back. The refusal is a
    **subclass** now, so the name stays a type and an instance made before the
    guards were armed still satisfies `isinstance`.
    """
    fs = pytest.importorskip("pyarrow.fs")
    pa = pytest.importorskip("pyarrow")
    before = fs.LocalFileSystem()
    isolation.install_all()
    try:
        assert isinstance(fs.LocalFileSystem, type)
        assert isinstance(pa.OSFile, type)
        # The refusal is a subclass of the original, so `isinstance` keeps its
        # meaning in the direction that matters: the guarded name is still a
        # type, and it still stands for the same family.
        assert issubclass(fs.LocalFileSystem, type(before))
        with pytest.raises(isolation.IsolationError):
            fs.LocalFileSystem()
    finally:
        isolation.uninstall_all()


def test_uninstall_restores_the_native_targets() -> None:
    pa = pytest.importorskip("pyarrow")
    original = pa.OSFile
    isolation.install_all()
    assert pa.OSFile is not original
    isolation.uninstall_all()
    assert pa.OSFile is original


def test_a_target_that_cannot_be_patched_is_disclosed(guards: object) -> None:
    """An entry on the list that is not actually refused is worse than a missing one.

    `sqlite3.Connection` and `pyarrow`'s filesystem class are immutable
    extension types. Where a target cannot be replaced, it is recorded rather
    than silently skipped — §6 tells a reviewer the list is the guarantee.
    """
    assert isinstance(isolation.unpatchable_native_targets(), tuple)


def test_attach_cannot_create_a_file_in_the_protected_tree(guards: object) -> None:
    """`sqlite3.connect` is hooked; `ATTACH` raises no audit event and creates a file."""
    import sqlite3

    connection = sqlite3.connect(":memory:")
    try:
        with pytest.raises(isolation.IsolationError):
            connection.execute(f"ATTACH DATABASE '{REPO / 'data' / '__nx__.db'}' AS d")
        assert connection.execute("select 1").fetchone() == (1,)
    finally:
        connection.close()


# ---------------------------------------------------------------------------
# The classifier
# ---------------------------------------------------------------------------


@WINDOWS_ONLY
def test_a_volume_guid_path_is_refused_rather_than_mangled(guards: object) -> None:
    """Stripping the prefix unconditionally turned it into a *relative* path.

    `realpath` then anchored it under the cwd, the cheap string test succeeded
    on that wrong path, and the identity walk — which only runs when the string
    test *fails* — never ran. The read landed.
    """
    target = r"\\?\Volume{00000000-0000-0000-0000-000000000000}" + str(REPO)[2:] + r"\data\x"
    with pytest.raises(isolation.IsolationError), open(target, "rb"):  # noqa: PTH123
        pass


@WINDOWS_ONLY
def test_an_extended_drive_path_still_reduces(guards: object) -> None:
    """Only two forms reduce; the drive form is one of them and must keep working."""
    with (
        pytest.raises(isolation.IsolationError),
        open("\\\\?\\" + str(REPO / "data" / "__nx__.jsonl"), "rb"),  # noqa: PTH123
    ):
        pass


def test_a_cold_import_of_a_src_module_survives_the_guards(tmp_path: Path) -> None:
    """`_NEVER_EXEMPT_ROOTS` contained `src`, so writing its `.pyc` refused.

    `IsolationError` is a `RuntimeError`, and CPython's `except OSError` around
    `set_data` does not catch it — the import died. This is the same defect
    round three recorded as fixed, re-created for one subtree.
    """
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, r'"
            + str(REPO)
            + "');"
            + "from scripts.m15_track_a import isolation; isolation.install_all();"
            + "import fx_ai_trading.domain; print('COLD IMPORT OK')",
        ],
        capture_output=True,
        text=True,
        env=dict(os.environ, PYTHONPYCACHEPREFIX=str(tmp_path / "cold")),
        timeout=300,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert "COLD IMPORT OK" in result.stdout


@pytest.mark.parametrize(
    ("relative", "allowed"),
    [
        ("scripts/__pycache__/probe.cpython-312.pyc", True),
        ("scripts/__pycache__/probe.cpython-312.pyc.123456", True),
        ("src/fx_ai_trading/__pycache__/probe.cpython-312.pyc", True),
        ("scripts/__pycache__/probe.tmp", False),
        ("data/__pycache__/candles.jsonl", False),
        ("tests/__pycache__/__probe__z.pyc", True),
    ],
)
def test_the_cache_exemption_keys_on_the_file_not_the_directory(
    guards: object, relative: str, allowed: bool
) -> None:
    """Both broad versions broke something: one laundered `data/`, one killed `src/` imports."""
    target = str(REPO / relative)
    if allowed:
        isolation.assert_write_allowed(target)
    else:
        with pytest.raises(isolation.IsolationError):
            isolation.assert_write_allowed(target)


# ---------------------------------------------------------------------------
# The scratch root itself
# ---------------------------------------------------------------------------


def test_the_scratch_root_cannot_be_moved_away(guards: object, scratch_at: Path) -> None:
    """Source classified as `scratch`, destination as `outside`, both permitted.

    The whole `BINDING_GOVERNANCE_RECORD` tree left the repository in one call,
    and every per-file ledger check was handed a *directory*.
    """
    scratch.append_line(scratch_at / seen_ledger.LEDGER_FILENAME, '{"probe": 1}')
    with pytest.raises(isolation.IsolationError):
        os.rename(scratch_at, str(scratch_at) + "_moved")
    with pytest.raises(isolation.IsolationError):
        shutil.move(str(scratch_at), str(scratch_at.parent / "gone"))
    assert (scratch_at / seen_ledger.LEDGER_FILENAME).exists()


def test_creating_the_scratch_root_still_works(guards: object, tmp_path: Path) -> None:
    """`mkdir` is not destructive, and `append_line` creates the root on first use."""
    root = tmp_path / "fresh_scratch"
    isolation.assert_write_allowed(str(root), what="mkdir")


# ---------------------------------------------------------------------------
# The containment audit: a node-type allowlist
# ---------------------------------------------------------------------------


def _offenders(source: str) -> set[str]:
    """Mirror of the read-body check's shape rules, over a spliced route.

    ``ast.Subscript`` became a permitted node type when R1's body landed — the
    body does ``row[key]`` — so the bare-subscript defence moved rather than
    disappeared: a subscript on a **module-level** name is still a finding,
    because that is the shape ``SLURP["path"]`` needs.
    """
    tree = ast.parse(source)
    module_level = containment._module_level_bindings(tree)
    function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    found: set[str] = set()
    if function.decorator_list:
        found.add("decorator")
    for child in ast.walk(function):
        if isinstance(child, ast.FormattedValue) and child.format_spec is not None:
            found.add("format-spec")
        if type(child) not in containment._PERMITTED_READ_ROUTE_NODES:
            found.add(type(child).__name__)
        if isinstance(child, ast.Subscript):
            base = getattr(child.value, "id", None)
            if base is None or base in module_level:
                found.add("module-level subscript")
    return found


@pytest.mark.parametrize(
    ("label", "source"),
    [
        ("bare-Name decorator", "@DECORATOR"),
        ("f-string format spec", '    _ = f"{S:README.md}"'),
        ("lambda", "    f = lambda: 1"),
        ("comprehension", "    x = [n for n in ()]"),
    ],
)
def test_a_read_that_is_not_a_call_is_still_a_finding(label: str, source: str) -> None:
    """Three rounds of allowlisting *call names* lost to reads that are not calls.

    ``source`` is one line spliced into a minimal route: a decorator, or a
    statement in the body.
    """
    head = "def read_historical(r, i):"
    tail = "    raise NotImplementedError('x')"
    lines = [source, head, tail] if source.startswith("@") else [head, source, tail]
    assert _offenders("\n".join(lines) + "\n"), f"not caught: {label}"


def test_a_subscript_on_a_module_level_name_is_a_finding() -> None:
    """``SLURP["path"]`` — a module object whose ``__getitem__`` reads.

    ``ast.Subscript`` became a permitted node type when R1's body landed,
    since the body does ``row[key]``. The defence moved rather than
    disappeared: a subscript on a **local** is a dict lookup, a subscript on
    a **module-level name** is a capability, and only the second is a
    finding.
    """
    hostile = (
        "SLURP = _Reader()\n"
        "def read_historical(r, i):\n"
        '    sink = SLURP["p"]\n'
        "    raise NotImplementedError('x')\n"
    )
    assert _offenders(hostile), "a subscript on a module-level name must be a finding"

    benign = (
        "def read_historical(r, i, row=None):\n"
        '    value = row["bid_o"]\n'
        "    raise NotImplementedError('x')\n"
    )
    assert not _offenders(benign), "a subscript on a local must not be a finding"


def test_the_declared_body_passes_the_node_allowlist() -> None:
    """Non-vacuity: the real route must satisfy the set, or the set is untestable."""
    from scripts.m15_track_a import read_route

    source = Path(read_route.__file__).read_text(encoding="utf-8")
    function = next(
        n
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.FunctionDef) and n.name == "read_historical"
    )
    unexpected = {
        type(child).__name__
        for child in ast.walk(function)
        if type(child) not in containment._PERMITTED_READ_ROUTE_NODES
    }
    assert not unexpected, unexpected
    assert not function.decorator_list


def test_a_permitted_opener_may_not_assemble_a_reader_by_reflection() -> None:
    """Skipping a module wholesale let a reader added to a ledger module go unscanned."""
    findings = containment._indirection_findings(
        "scripts.m15_track_a.breadth", ast.parse('_r = _b.__dict__["open"]')
    )
    assert findings, "a reflected reader in a permitted opener must still be a finding"


def test_the_audit_is_contained_at_this_head() -> None:
    report = containment.audit()
    failed = [check for check in report["checks"] if not check["passed"]]
    assert failed == [], failed
    assert report["declared_gate_sequence_matches_at_this_head"] is True
