"""FB-8 — pin reader-freedom, the outbound import surface, and the reverse-caller set.

Contract §12.14 / D-11: *"Keep `scripts/m15_gate3a/**` reader-free; P and V live
outside it; **pin the import direction and the reverse-caller set with tests**."*

The fourth independent source-audit graded the missing half a **blocker**. The
source was correct — an AST sweep and a runtime `sys.addaudithook` trace both
found zero read primitives — and exactly one pin existed (an intra-package
direction probe). Reader-freedom itself was pinned by nothing, and the audit
demonstrated it by mutation: a module-scope `Path(__file__).read_bytes()`, a
public byte reader, an `import socket`, and an import of the repository's
real-data reader `Real365dBaProvider` were each added to the package and the
whole scoped suite stayed at **1100 passed, 1 skipped**. A non-test reverse
caller — including one under production `src/` — survived identically.

That is the property on which every "this package cannot touch real data"
statement in four audit records rests, and §15.4 places the byte-reading
producer/verifier at the *next* gate: the moment this pin most needs to already
exist.

**Why these tests read source rather than call functions.** §13 forbids tests
that assert on source *text* in place of behaviour. These do not: the property
under test *is* a property of the source and of the import graph — "this package
contains no reader" is not observable by calling anything, because a reader that
is never called still exists and can be called by the next caller. They are
written against the **AST** and the **live import graph**, never against text,
and each carries a non-vacuity floor so it cannot pass by scanning nothing.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.ml_step4.evidence import repo_root

PACKAGE_DIR = Path(__file__).resolve().parents[2] / "scripts" / "m15_gate3a"
PACKAGE = "scripts.m15_gate3a"

#: Every module of the package. The floor below stops a glob that finds nothing.
#: RECURSIVE. `glob("*.py")` covered only the package's top level, so a
#: subpackage - `scripts/m15_gate3a/io/__init__.py` carrying `import socket`,
#: `import subprocess` and `Path(p).read_bytes()` - left every AST test in this
#: file green. The property §12.14 states is over `scripts/m15_gate3a/**`.
MODULES: tuple[Path, ...] = tuple(sorted(PACKAGE_DIR.rglob("*.py")))
_MODULE_FLOOR = 15


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _called_names(tree: ast.Module) -> set[str]:
    """Every callee name, whether `f(...)` or `x.f(...)`."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
    return names


def _module_scope_imports(tree: ast.Module) -> set[str]:
    """Every import in the module, at any nesting depth.

    Reading ``tree.body`` was a defect, not an economy. An internal audit put
    ``import subprocess`` inside a function and ``try: import socket`` at module
    scope and both left this file green: the first is not in ``tree.body`` at all,
    and the second is inside a ``Try`` node whose body ``tree.body`` does not
    descend into. A capability is a capability wherever it is spelled — a
    function-local import still binds the module at first call — so the sweep
    walks the whole tree.
    """
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module)
    return out


def _referenced_names(tree: ast.Module) -> set[str]:
    """Every attribute and bare name the module *mentions*, not merely calls.

    ``_called_names`` looked only at ``ast.Call`` callees, which an audit defeated
    five ways at once: ``_R = Path.read_bytes`` then ``_R(p)``,
    ``getattr(p, "read" + "_bytes")()``, ``hashlib.file_digest(fh, ...)``,
    ``fileobj.read()`` on a caller-supplied handle, and ``subprocess.run`` behind
    a function-local import. Binding a read primitive to another name is not less
    of a read; the reference itself is the capability.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.Name):
            names.add(node.id)
    return names


def test_the_module_sweep_is_not_vacuous() -> None:
    """Non-vacuity floor: every test below iterates MODULES."""
    assert len(MODULES) >= _MODULE_FLOOR, MODULES
    assert (PACKAGE_DIR / "proof.py") in MODULES
    assert (PACKAGE_DIR / "coverage.py") in MODULES


# ---------------------------------------------------------------------------
# Reader-freedom
# ---------------------------------------------------------------------------

#: Primitives that read content, enumerate a directory, spawn, or reach a
#: network. A gate-3a module calling any of these is not reader-free.
FORBIDDEN_CALLS: frozenset[str] = frozenset(
    {
        "open",
        "read_text",
        "read_bytes",
        "read",
        "readall",
        "readinto",
        "readline",
        "readlines",
        "FileIO",
        "BufferedReader",
        "TextIOWrapper",
        "mmap",
        "file_digest",
        "run",
        "call",
        "communicate",
        "create_connection",
        "socket",
        "recv",
        "recv_into",
        "recvfrom",
        "send",
        "sendall",
        "urlretrieve",
        "request",
        "fdopen",
        "loadtxt",
        "memmap",
        "fromfile",
        "read_parquet",
        "read_csv",
        "read_json",
        "listdir",
        "scandir",
        "walk",
        "iterdir",
        "glob",
        "rglob",
        "iglob",
        "system",
        "popen",
        "Popen",
        "check_output",
        "check_call",
        "urlopen",
        "connect",
        "connect_ex",
        "sendto",
        "getaddrinfo",
        "gethostbyname",
        "import_module",
        "__import__",
        "eval",
        "exec",
        "compile",
    }
)

#: The only filesystem primitives the package legitimately uses, each with the
#: module that owns it. Anything else is a finding, and a primitive appearing in
#: a module that does not own it is also a finding.
PERMITTED_FS_CALLS: dict[str, frozenset[str]] = {
    "artifacts.py": frozenset({"mkdir", "write_text", "unlink", "rmdir", "exists"}),
    "path_authority.py": frozenset({"stat", "samestat", "resolve", "exists"}),
}


def _permitted_qualified(node: ast.Attribute) -> bool:
    """True for the two qualified names this package legitimately mentions.

    Structural, not textual. The predecessor exempted `compile` whenever the
    **file** contained the substring `"re.compile"` anywhere — which disabled the
    rule for every call in that module. Here the exemption is the shape of the
    node itself: `re.compile` and `json.loads`, and nothing else.
    """
    return isinstance(node.value, ast.Name) and (
        (node.value.id == "re" and node.attr == "compile")
        or (node.value.id == "json" and node.attr == "loads")
    )


#: The subset of `FORBIDDEN_CALLS` that is also forbidden as a **bare** name.
#: The rest are checked only as attributes, because words like `run`, `read`,
#: `call` and `send` are ordinary local-variable names — `aggregation.py` counts
#: a `run` of unusable minutes — and flagging those would be noise that a future
#: reader silences by weakening the rule. A capability reached as a bare name is
#: either a builtin or an imported module, and the import sweep owns the latter.
FORBIDDEN_BARE_NAMES: frozenset[str] = frozenset({"open", "eval", "exec", "compile", "__import__"})


def _forbidden_references(tree: ast.Module) -> set[str]:
    """Forbidden primitives *referenced* anywhere, with the two exemptions."""
    hits: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_CALLS:
            if not _permitted_qualified(node):
                hits.add(node.attr)
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_BARE_NAMES:
            hits.add(node.id)
    return hits


def _referenced_attributes(tree: ast.Module) -> set[str]:
    """Attribute names only. A filesystem primitive is always reached as one.

    Bare names are excluded here (unlike :func:`_referenced_names`) because a
    local variable called `stat` is not `os.stat`, and flagging it is the kind of
    noise that gets a rule relaxed rather than fixed.
    """
    return {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}


def _module_string_constants(tree: ast.Module) -> dict[str, frozenset[str]]:
    """Module-level names bound to a literal collection of strings."""
    out: dict[str, frozenset[str]] = {}
    for node in tree.body:
        if not (isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value is not None):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if isinstance(value, ast.Call) and value.args:
            value = value.args[0]
        if not isinstance(value, (ast.Tuple, ast.List, ast.Set)):
            continue
        if not all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in value.elts):
            continue
        for target in targets:
            if isinstance(target, ast.Name):
                out[target.id] = frozenset(e.value for e in value.elts)  # type: ignore[attr-defined]
    return out


def _loop_bindings(tree: ast.Module) -> dict[str, str]:
    """Loop variable -> the name of the iterable it walks, where both are plain."""
    out: dict[str, str] = {}
    for node in ast.walk(tree):
        pairs = []
        if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            pairs.append((node.target, node.iter))
        for target, iterable in pairs:
            if isinstance(target, ast.Name) and isinstance(iterable, ast.Name):
                out[target.id] = iterable.id
    return out


def _inline_loop_literals(tree: ast.Module) -> dict[str, frozenset[str]]:
    """Loop variable -> the string literals of an **inline** iterable.

    `for name in ("committed_artifact", "committed_revision"):` is as statically
    enumerable as a module constant; it just is not a name.
    """
    out: dict[str, frozenset[str]] = {}
    for node in ast.walk(tree):
        pairs = []
        if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
            pairs.append((node.target, node.iter))
        for target, iterable in pairs:
            if not (
                isinstance(target, ast.Name)
                and isinstance(iterable, (ast.Tuple, ast.List, ast.Set))
            ):
                continue
            if all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in iterable.elts):
                out[target.id] = frozenset(e.value for e in iterable.elts)  # type: ignore[attr-defined]
    return out


def test_no_gate3a_module_calls_a_read_network_or_subprocess_primitive() -> None:
    """FB-8: the property four audit records rest on, pinned at last.

    Mutations this kills, each of which previously left the suite green: a
    function-local `import subprocess` with `subprocess.run(...)`;
    `hashlib.file_digest(fh, "sha256")`; `_R = Path.read_bytes` then `_R(p)`;
    `io.FileIO(p).readall()`; `mmap.mmap(fd, 0)`;
    `socket.create_connection(...).sendall(...)`; `fileobj.read()` on a
    caller-supplied handle with no `open` anywhere in the module.

    The rule is over **references**, not calls, because binding a primitive to
    another name is not less of a read — which is exactly how four of those
    seven escaped a callee-name denylist.
    """
    offenders: list[str] = []
    for path in MODULES:
        for name in sorted(_forbidden_references(_tree(path))):
            offenders.append(f"{path.name}:{name}")
    assert offenders == [], (
        f"gate-3a must contain no read / network / subprocess primitive (§12.14); found {offenders}"
    )


def test_no_gate3a_module_computes_the_name_it_reaches_for() -> None:
    """`getattr(p, "read" + "_bytes")()` defeats every name-based rule above.

    `getattr` has legitimate uses here (`sealing` looks up `__post_init__`), so
    it is not forbidden — but its attribute argument must be a **literal**, which
    is what makes the reference sweep above complete rather than advisory.
    """
    offenders: list[str] = []
    for path in MODULES:
        tree = _tree(path)
        constants = _module_string_constants(tree)
        loops = _loop_bindings(tree)
        inline = _inline_loop_literals(tree)
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
                continue
            if node.func.id != "getattr" or len(node.args) < 2:
                continue
            attribute = node.args[1]
            if isinstance(attribute, ast.Constant) and isinstance(attribute.value, str):
                reachable = {attribute.value}
            elif isinstance(attribute, ast.Name):
                # The package's real use: iterate a module-level tuple of field
                # names. That set is statically enumerable, so the reachable
                # attribute names are still known and can still be checked.
                iterable = loops.get(attribute.id)
                reachable = inline.get(attribute.id) or constants.get(iterable or "", frozenset())
                if not reachable:
                    offenders.append(f"{path.name}:{node.lineno}:unresolvable")
                    continue
            else:
                offenders.append(f"{path.name}:{node.lineno}:computed")
                continue
            for reached in sorted(reachable & FORBIDDEN_CALLS):
                offenders.append(f"{path.name}:{node.lineno}:{reached}")
    assert offenders == [], (
        "a computed attribute name defeats every name-based reader-freedom rule; "
        f"getattr must take a literal that is not a forbidden primitive, but {offenders}"
    )


#: Every filesystem-touching name in `pathlib.Path` and `os` that is not already
#: in `FORBIDDEN_CALLS`. An ALLOWLIST complement, not a denylist of eight: the
#: predecessor's docstring claimed "the filesystem surface is exactly what the
#: docstrings claim it is" while checking eight names, so adding `write_bytes`,
#: `touch` or `rename` to `proof.py` - a module the tests say touches the
#: filesystem not at all - left the suite green.
FS_MUTATING_NAMES: frozenset[str] = frozenset(
    # Deliberately excludes names that collide with non-filesystem methods of
    # ordinary types - `replace` (`str`, `datetime`, `dataclasses`), `copy`
    # (`dict`), `move`, `truncate`, `link`. Those would be noise, and noise is
    # what gets a rule weakened later rather than fixed. Every name below is a
    # filesystem primitive and nothing else.
    {
        "mkdir",
        "makedirs",
        "write_text",
        "write_bytes",
        "touch",
        "unlink",
        "remove",
        "rmdir",
        "removedirs",
        "rmtree",
        "rename",
        "symlink_to",
        "hardlink_to",
        "symlink",
        "chmod",
        "chown",
        "copyfile",
        "copytree",
        "exists",
        "is_file",
        "is_dir",
        "stat",
        "lstat",
        "samestat",
        "samefile",
        "resolve",
    }
)


def test_only_the_two_writer_modules_touch_the_filesystem_at_all() -> None:
    """The filesystem surface is exactly what the docstrings claim it is."""
    offenders: list[str] = []
    for path in MODULES:
        permitted = PERMITTED_FS_CALLS.get(path.name, frozenset())
        for name in sorted(_referenced_attributes(_tree(path)) & FS_MUTATING_NAMES):
            if name not in permitted:
                offenders.append(f"{path.name}:{name}")
    assert offenders == [], (
        f"a filesystem primitive appeared outside the module that owns it: {offenders}"
    )


def test_no_gate3a_module_imports_a_capability_at_module_scope() -> None:
    """Importing the capability is enough — it need not be called to be reachable."""
    forbidden_modules = {
        "socket",
        "ssl",
        "subprocess",
        "urllib",
        "urllib.request",
        "requests",
        "http",
        "http.client",
        "ctypes",
        "mmap",
        "pickle",
        "shelve",
        "importlib",
        "pkgutil",
        "sqlalchemy",
        "psycopg",
        "dotenv",
        "boto3",
        "pandas",
        "numpy",
        "pyarrow",
        "joblib",
        "lightgbm",
        "sklearn",
    }
    offenders: list[str] = []
    for path in MODULES:
        for imported in sorted(_module_scope_imports(_tree(path))):
            root = imported.split(".")[0]
            if imported in forbidden_modules or root in forbidden_modules:
                offenders.append(f"{path.name}: {imported}")
    assert offenders == [], f"gate-3a imported a capability at module scope: {offenders}"


# ---------------------------------------------------------------------------
# The outbound import surface
# ---------------------------------------------------------------------------

#: The complete out-of-package module-scope import surface, and the exact names
#: taken from each. Named, not counted: the audit's FO-11 records that
#: `pair_authority` imports a module that also defines the repository's
#: real-data reader `Real365dBaProvider`, so what matters is which *names* the
#: package binds, not merely which modules it touches.
PERMITTED_OUTBOUND: dict[str, frozenset[str]] = {
    "scripts.ml_step4.data_adapter": frozenset({"pip_size_for"}),
    "scripts.ml_step4.evidence": frozenset({"repo_root", "scan_payload", "serialise"}),
    "scripts.ml_step4": frozenset({"evidence"}),
}


#: Every first-party top-level package in this repository. The outbound sweep
#: used to filter on ``scripts`` alone, which left the direction that matters
#: most — gate-3a importing **production code** under `src/fx_ai_trading` —
#: entirely unpinned; an audit added `import fx_ai_trading.config` to
#: `pair_authority.py` and this file stayed green.
FIRST_PARTY_ROOTS: frozenset[str] = frozenset(
    {"scripts", "src", "fx_ai_trading", "tools", "migrations", "tests"}
)


def _outbound_bindings() -> dict[str, set[str]]:
    """First-party imports leaving the package, from anywhere in the tree.

    ``.body`` missed function-local imports — including the one this pin's own
    docstring named as the mutation it kills, `from scripts.ml_step4.data_adapter
    import Real365dBaProvider` written inside a function.
    """
    bound: dict[str, set[str]] = {}
    for path in MODULES:
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                # The trailing dot is load-bearing: without it a sibling whose
                # dotted name merely begins with the package name - an audit
                # used `scripts.m15_gate3a_reader`, holding a `read_bytes`
                # helper - was treated as intra-package and dropped from the
                # outbound surface entirely. `_intra_edges` already got this
                # right; this did not.
                if node.module == PACKAGE or node.module.startswith(PACKAGE + "."):
                    continue
                if node.module.split(".")[0] not in FIRST_PARTY_ROOTS:
                    continue
                bound.setdefault(node.module, set()).update(a.name for a in node.names)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    inside = alias.name == PACKAGE or alias.name.startswith(PACKAGE + ".")
                    if root in FIRST_PARTY_ROOTS and not inside:
                        bound.setdefault(alias.name, set()).add("<module>")
    return bound


def test_the_first_party_outbound_surface_is_exactly_what_is_permitted() -> None:
    """A new first-party edge — or a new *name* on an existing edge — fails here.

    Mutation this kills: `from scripts.ml_step4.data_adapter import
    Real365dBaProvider` in `pair_authority`, which binds the repository's
    real-data reader into the package that contractually never reads.
    """
    bound = _outbound_bindings()
    assert bound, "non-vacuity: the package must have at least one first-party edge"
    unexpected_modules = sorted(set(bound) - set(PERMITTED_OUTBOUND))
    assert unexpected_modules == [], (
        f"gate-3a acquired a new first-party import edge: {unexpected_modules}"
    )
    for module, names in sorted(bound.items()):
        extra = sorted(names - PERMITTED_OUTBOUND[module])
        assert extra == [], f"gate-3a bound a new name from {module}: {extra}"


def test_importing_the_package_loads_no_third_party_module() -> None:
    """Runtime companion to the AST sweep, in a fresh interpreter."""
    probe = (
        "import sys, importlib, pathlib;"
        # EVERY module in the package. Importing four of sixteen left
        # `effective_n`, `warmup` and `__init__` outside the transitive closure,
        # so a capability import in any of them escaped this test as well as the
        # AST sweep that read only `tree.body`.
        "names=sorted(p.stem for p in pathlib.Path('scripts/m15_gate3a').glob('*.py'));"
        "[importlib.import_module('scripts.m15_gate3a.' + n)"
        " for n in names if n != '__init__'];"
        "assert len(names) >= 15, names;"
        "bad=[m for m in ('pandas','numpy','lightgbm','joblib','sklearn','sqlalchemy',"
        "'dotenv','requests','socket','subprocess','ssl','pyarrow') if m in sys.modules];"
        "print(','.join(bad))"
    )
    result = subprocess.run(  # noqa: S603 - fixed argv, no shell, repo-local probe
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        cwd=str(repo_root()),
        check=True,
    )
    assert result.stdout.strip() == "", (
        f"importing gate-3a loaded third-party capability modules: {result.stdout.strip()}"
    )


# ---------------------------------------------------------------------------
# The reverse-caller set
# ---------------------------------------------------------------------------

#: Trees permitted to import the package. Everything else — and `src/` above
#: all — is a forbidden reverse caller.
#: Trailing separators are load-bearing: without them a *sibling* whose name
#: merely begins with the package name — `scripts/m15_gate3a_continuation/`,
#: which is the name the suite's own fixtures use for the gate-4 byte-reading
#: producer, or `scripts/m15_gate3a_evil.py` — counted as "inside the package".
PERMITTED_CALLER_ROOTS: tuple[str, ...] = (
    "scripts/m15_gate3a/",
    "tests/m15_gate3a/",
    # Track A's R1 execution infrastructure imports this package's reader-free
    # authorities — the path authority, the span constants and the aggregation
    # bucket constants — rather than re-implementing them, which would make a
    # fourth path authority and a second set of span constants.  The permission
    # is narrow and is pinned by
    # ``test_track_a_imports_only_reader_free_names_from_this_package`` below:
    # this root may import the reader-free names on the allowlist and nothing
    # else.  Without that companion test this entry would weaken FB-8's pin
    # rather than scope it.
    "scripts/m15_track_a/",
    "tests/m15_track_a/",
)

#: What ``scripts/m15_track_a/`` may import from this package.  Every entry is
#: reader-free: a pure path predicate, a frozen span constant, a declaration
#: check that opens no file, or an integer.  ``proof``, ``artifacts``,
#: ``coverage`` and ``sealing`` are deliberately absent — they carry evidence
#: semantics Track A must not reach, and a Track A run is a future real-data
#: reader, so its import surface into this package is the one place a reader
#: could be introduced by the back door.
#:
#: ``calendar_authority`` is **not** here, and an earlier revision of the R1
#: enablement work that put it here has been reverted — see the note on
#: ``TRACK_A_FORBIDDEN_MODULES`` below for why that was wrong and what replaced
#: it. ``cost_schema``'s three frozen constants are a **proposed** narrowing,
#: recorded as a referral rather than as a ruling.
TRACK_A_PERMITTED_IMPORTS: dict[str, frozenset[str]] = {
    "scripts.m15_gate3a.path_authority": frozenset(
        {"PathAuthorityError", "is_within", "resolve_candidate"}
    ),
    # ``is_dead_window_instant`` joins the set with R1's read body: the body
    # refuses a **row** inside the dead window even when the declared interval
    # passed, because ``no_overlap`` checks metadata and says so
    # (``CALLER_DECLARED_METADATA_ONLY__NO_FILE_OPENED__NO_BYTE_MEASURED``). It
    # is a pure predicate over one parsed instant and opens nothing.
    #
    # ``FORWARD_FLOOR`` joins it for the row-level refusal beside that one: a
    # review role observed that nothing in the route stopped a forward-epoch row,
    # and that the committed files merely happen not to contain one — a property
    # of the data, not of the code. It is a frozen ``datetime`` constant.
    "scripts.m15_gate3a.no_overlap": frozenset(
        {
            "DESIGN_END",
            "DESIGN_START",
            "FORWARD_FLOOR",
            "assert_design_bounds",
            "assert_no_dead_window",
            "is_dead_window_instant",
        }
    ),
    # ``canonical_pair`` normalises and universe-checks a pair name before R1
    # builds a source path from it, so an unknown or non-canonical spelling
    # fails closed before any path exists. The module opens no file at all.
    # ``PairAuthorityError`` is its refusal type, imported so the read route can
    # re-raise an unknown pair as its own ``ReadRouteError`` instead of letting a
    # foreign exception type escape a documented boundary. A ``ValueError``
    # subclass reads nothing.
    "scripts.m15_gate3a.pair_authority": frozenset(
        {"PAIRS_20", "PairAuthorityError", "canonical_pair"}
    ),
    # The derivation-bypass containment. It exists precisely so that Track A's
    # aggregation cannot escape its authorised route, so Track A importing it is
    # the intended direction. stdlib-only by construction, and
    # ``test_derivation_containment_imports_nothing_first_party`` pins that —
    # an earlier revision claimed such a test existed when it did not.
    "scripts.m15_gate3a.derivation_containment": frozenset(
        {
            "DerivationContainmentError",
            "authorised_derivation_window",
            "is_real_row",
            "mark_real_rows_handed_out",
            "real_rows_handed_out",
            "stamp_real_provenance",
        }
    ),
    # Calendar A/B authoring and the two frozen predicates R1 needs to place a
    # bar in a session and to apply Ruling 4's rollover exclusion. Pure calendar
    # arithmetic; it reads no file and no price.
    # The two session predicates whose content is committed: Ruling 4's frozen
    # session partition and its frozen rollover window. The module that authored
    # a market calendar is deleted; this one adds no
    # market-hours claim, and a hand-written oracle test pins that it has not
    # grown one back.
    "scripts.m15_gate3a.session_windows": frozenset(
        {
            "COVERAGE_STATUS",
            "HOLIDAY_CONSEQUENCE",
            "HOLIDAY_STATUS",
            "ROLLOVER_CONSEQUENCE",
            "bucket_overlaps_rollover",
            "is_event_eligible_window",
            "session_of",
        }
    ),
    # Ruling 5's frozen cost constants and Ruling 4's frozen session partition.
    # Named symbols, not the module: ``validate_cost_table`` stays out of reach.
    "scripts.m15_gate3a.cost_schema": frozenset(
        {"EXECUTION_PADDING_PIP", "FLAT_SLIPPAGE_CELL_PIP", "SESSIONS_UTC"}
    ),
    # ``aggregate_m15`` is the derivation route's delegate, bound in the diff
    # because §8.12.10 condition 3 requires "an explicit committed caller"
    # rather than a decision a session reports having taken.  It is reader-free:
    # a pure function over row dicts, and ``scripts/m15_gate3a/aggregation.py``
    # opens no file anywhere.
    # The incremental accumulator. `aggregate_m15` computes its gap report over
    # a whole call, so a bounded-memory run that aggregates a pair in batches
    # has to combine the *inputs* — `_bucket_start`, `_plain_utc_minute`,
    # `_build_gap_report`, `_build_minute_accounting`. Those are this package's
    # privates and this list is named symbols, not modules, so the accumulation
    # was put in `scripts/m15_gate3a/incremental_m15.py` beside them and Track A
    # imports the one public class. That is one added name rather than four
    # private helpers crossing the boundary, and it keeps the aggregator's
    # internals inside the package that owns them. Reader-free: the module opens
    # nothing and its only file-touching import is the aggregator's own.
    "scripts.m15_gate3a.incremental_m15": frozenset({"IncrementalM15", "IncrementalM15Error"}),
    "scripts.m15_gate3a.aggregation": frozenset(
        {
            "BUCKET_MINUTES",
            "FULL_BUCKET_SOURCE_BARS",
            "aggregate_m15",
            # The committed pip-size conversion. R1 reports spreads in pips, and
            # the alternative is a second conversion authority -- the "pip
            # authority 100x JPY" defect this programme has already had once.
            "to_pips",
        }
    ),
}

#: What ``tests/m15_track_a/`` may import from this package.  Wider than the
#: production allowlist by exactly one module — a test that demonstrates a guard
#: does **not** reach a path has to be able to call that guard — and pinned all
#: the same, because a test root added to ``PERMITTED_CALLER_ROOTS`` with no pin
#: widens FB-8 through the back door just as a source root would.
TRACK_A_TEST_PERMITTED_MODULES: frozenset[str] = frozenset(
    set(TRACK_A_PERMITTED_IMPORTS) | {"scripts.m15_gate3a.guards"}
)

#: The sweep below covers ``scripts/m15_track_a/`` only.  Track A's *tests* may
#: import more — one of them probes ``guards.refuse_real_path`` to demonstrate
#: the gap NR-A leaves — because a test that proves a guard does not reach a
#: path must be able to call that guard.  Production Track A code may not, and
#: that is what this pin binds.

#: Modules Track A may not import from this package at all, named so the failure
#: message says why rather than only that.
#:
#: ⚠ **``calendar_authority`` was briefly removed from this set and has been put
#: back.** An earlier revision of the R1 enablement work took it out, citing
#: ``docs/governance/m15_track_a_r1_enablement_ruling.md`` §3 — **a file that did
#: not exist**. Two review roles found the dangling citation independently, and
#: a third pointed at the merged authority the justification contradicted:
#: ``m15_track_a_execution_gate.md`` §8 (`37edbb0`) says "requiring it of Track A
#: would **block exploration on an artefact that does not exist, for no leakage
#: reason**". The reasoning offered — that D-6 forces Track A to reach the
#: validator — was a rationalisation. The calendar itself is now **deleted**
#: (D-6: no market-hours time "may be added by an implementer"), so Track A
#: neither validates a calendar nor needs to: it passes ``expected_minutes=None``
#: and reports the coverage authority as absent.
#:
#: ``cost_schema`` stays out of this set. That narrowing **is** a change to a
#: committed restriction, and it is ruled — not assumed — in
#: ``docs/governance/m15_track_a_r1_enablement_referrals.md`` §4:
#: ``TRACK_A_COST_SCHEMA_IMPORT_NARROWING_IS_IMPLEMENTATION_ONLY_PERMITTED``.
#: What is permitted is three frozen constants — Ruling 5's two cost pads and
#: Ruling 4's session partition. ``validate_cost_table`` and everything else stay
#: unreachable, and no cost **decision** becomes available to Track A that was
#: not before.
TRACK_A_FORBIDDEN_MODULES: frozenset[str] = frozenset(
    {
        "scripts.m15_gate3a.proof",
        "scripts.m15_gate3a.artifacts",
        "scripts.m15_gate3a.coverage",
        "scripts.m15_gate3a.calendar_authority",
        "scripts.m15_gate3a.sealing",
        "scripts.m15_gate3a.effective_n",
    }
)


#: Directories that are not first-party source. Everything else in the repo is
#: swept, because enumerating the five directories that existed when the pin was
#: written meant a new top-level `apps/` — or a `.py` at the repo root — was an
#: unpinned home for a reverse caller.
NON_SOURCE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "build",
        "dist",
        "site-packages",
    }
)


def _repo_python_files() -> list[Path]:
    root = repo_root()
    return [
        path
        for path in root.rglob("*.py")
        if not (NON_SOURCE_DIRS & set(path.relative_to(root).parts))
    ]


def _imported_module_names(tree: ast.Module, rel: str) -> set[str]:
    """Every module name this file imports, **including relative and dynamic**.

    Three spellings previously escaped: `from . import m15_gate3a` and
    `from .m15_gate3a import proof` (relative — `node.module` is `None` or bare),
    `importlib.import_module("scripts.m15_gate3a.proof")` and
    `__import__("...")` (the name is a string literal, not an AST import at all).
    """
    package_parts = rel.split("/")[:-1]
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[: len(package_parts) - node.level + 1]
                prefix = ".".join([*base, node.module] if node.module else base)
            else:
                prefix = node.module or ""
            names.add(prefix)
            names.update(f"{prefix}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call):
            func = node.func
            dynamic = (isinstance(func, ast.Name) and func.id == "__import__") or (
                isinstance(func, ast.Attribute) and func.attr == "import_module"
            )
            if dynamic:
                names.update(
                    arg.value
                    for arg in node.args
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                )
    return names


def test_the_package_has_no_reverse_caller_outside_itself_and_its_own_tests() -> None:
    """FB-8's second half.

    Mutation this kills: a new `scripts/zz_caller.py`, or — the one that matters —
    a **production** importer under `src/fx_ai_trading/`. Both previously left the
    suite green.
    """
    files = _repo_python_files()
    assert len(files) >= 100, f"non-vacuity: only {len(files)} python files swept"
    root = repo_root()
    offenders: list[str] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        if rel.startswith(PERMITTED_CALLER_ROOTS):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - not our concern
            continue
        for name in _imported_module_names(tree, rel):
            if name == PACKAGE or name.startswith(PACKAGE + "."):
                offenders.append(f"{rel}:{name}")
    assert offenders == [], (
        "§12.14 pins the reverse-caller set: nothing outside the package and its own "
        f"tests may import it, but {offenders} does"
    )


def test_track_a_imports_only_reader_free_names_from_this_package() -> None:
    """The companion pin for ``scripts/m15_track_a/``'s entry in the permitted roots.

    Track A is a **future real-data reader**, so its import surface into this
    package is the one place a reader could enter by the back door: an import of
    ``proof`` or ``artifacts`` would give a reading stage the evidence semantics
    this package exists to keep away from one.  Adding Track A to
    ``PERMITTED_CALLER_ROOTS`` without this test would have widened FB-8's pin
    instead of scoping it.

    Mutation this kills: ``from scripts.m15_gate3a.proof import ...`` anywhere
    under ``scripts/m15_track_a/``, and a new symbol pulled from an otherwise
    permitted module.
    """
    root = repo_root()
    track_a = root / "scripts" / "m15_track_a"
    assert track_a.is_dir(), "non-vacuity: the Track A package must exist for this pin to bind"
    files = sorted(track_a.rglob("*.py"))
    assert files, "non-vacuity: no Track A source files were swept"

    offenders: list[str] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if not (module == PACKAGE or module.startswith(PACKAGE + ".")):
                    continue
                if module in TRACK_A_FORBIDDEN_MODULES:
                    offenders.append(f"{rel}: imports the forbidden module {module}")
                    continue
                permitted = TRACK_A_PERMITTED_IMPORTS.get(module)
                if permitted is None:
                    offenders.append(f"{rel}: imports {module}, which is not on the allowlist")
                    continue
                for alias in node.names:
                    if alias.name not in permitted:
                        offenders.append(f"{rel}: imports {module}.{alias.name}, not allowlisted")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.name
                    if name == PACKAGE or name.startswith(PACKAGE + "."):
                        offenders.append(
                            f"{rel}: `import {name}` — Track A imports named symbols from the "
                            "allowlist, never a whole module"
                        )

    assert offenders == [], (
        "Track A may import only the reader-free names on TRACK_A_PERMITTED_IMPORTS from "
        f"this package, but {offenders}"
    )


def test_track_a_tests_import_only_the_modules_their_own_pin_permits() -> None:
    """``tests/m15_track_a/`` was added to the permitted roots with no pin of its own.

    A test root is still a root. Without this, any module in this package —
    ``proof``, ``artifacts``, ``sealing`` — could be imported from a Track A
    test and the reverse-caller sweep would stay green, which is scoping the
    permission on the source side and widening it on the test side.

    Mutation this kills: ``from scripts.m15_gate3a.proof import ...`` under
    ``tests/m15_track_a/``.
    """
    root = repo_root()
    track_a_tests = root / "tests" / "m15_track_a"
    assert track_a_tests.is_dir(), "non-vacuity: the Track A test package must exist"
    files = sorted(track_a_tests.rglob("*.py"))
    assert files, "non-vacuity: no Track A test files were swept"

    offenders: list[str] = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom):
                # ``from scripts.m15_gate3a import guards`` names the submodule
                # in the alias, not in ``node.module`` — resolve it, or the pin
                # reads the package itself and misses what was actually pulled.
                modules = (
                    [f"{PACKAGE}.{alias.name}" for alias in node.names]
                    if node.module == PACKAGE
                    else [node.module or ""]
                )
            elif isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            for module in modules:
                if not (module == PACKAGE or module.startswith(PACKAGE + ".")):
                    continue
                if module in TRACK_A_FORBIDDEN_MODULES:
                    offenders.append(f"{rel}: imports the forbidden module {module}")
                elif module not in TRACK_A_TEST_PERMITTED_MODULES:
                    offenders.append(f"{rel}: imports {module}, not on the test allowlist")

    assert offenders == [], (
        "Track A tests may import only the modules on TRACK_A_TEST_PERMITTED_MODULES from "
        f"this package, but {offenders}"
    )


# ---------------------------------------------------------------------------
# Intra-package import direction
# ---------------------------------------------------------------------------

#: Edges that must never exist, in either the declaration or the authority
#: direction. The pre-existing pin covered one source module and three targets;
#: this covers the direction as a rule.
FORBIDDEN_EDGES: tuple[tuple[str, str], ...] = (
    ("no_overlap", "proof"),
    ("no_overlap", "coverage"),
    ("no_overlap", "calendar_authority"),
    ("coverage", "proof"),
    ("calendar_authority", "proof"),
    ("calendar_authority", "coverage"),
    ("timeutil", "proof"),
    ("pair_authority", "proof"),
    ("numeric_authority", "proof"),
    ("path_authority", "guards"),
    ("aggregation", "proof"),
)


#: Every module name in the package, so `from <package> import <submodule>` can
#: be told apart from `from <package> import <symbol>`.
_MODULE_NAMES: frozenset[str] = frozenset(p.stem for p in MODULES)


def _intra_edges() -> set[tuple[str, str]]:
    """Every intra-package edge, in all four spellings Python admits.

    The four matter because a pin that reads only one of them is defeated by
    writing the import a different way — which is exactly what happened when
    this test first ran: `from scripts.m15_gate3a import proof as _p` recorded
    the edge as `coverage -> m15_gate3a` and the forbidden-edge check never
    fired.
    """
    edges: set[tuple[str, str]] = set()
    for path in MODULES:
        src = path.stem
        for node in ast.walk(_tree(path)):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if node.level > 0 and module:
                    # `from .proof import X` / `from .sub.proof import X`
                    edges.add((src, module.rsplit(".", 1)[-1]))
                elif module == PACKAGE:
                    # `from scripts.m15_gate3a import proof` — the names are
                    # submodules, not symbols.
                    edges.update((src, a.name) for a in node.names if a.name in _MODULE_NAMES)
                elif module.startswith(PACKAGE + "."):
                    # `from scripts.m15_gate3a.proof import X`
                    edges.add((src, module.rsplit(".", 1)[-1]))
                elif node.level > 0:
                    # `from . import proof`
                    edges.update((src, a.name) for a in node.names if a.name in _MODULE_NAMES)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(PACKAGE + "."):
                        # `import scripts.m15_gate3a.proof`
                        edges.add((src, alias.name.rsplit(".", 1)[-1]))
    return edges


@pytest.mark.parametrize(("source", "target"), FORBIDDEN_EDGES)
def test_the_intra_package_import_direction_stays_one_way(source: str, target: str) -> None:
    """Each forbidden edge is pinned separately, so a failure names the edge."""
    edges = _intra_edges()
    assert len(edges) >= 10, f"non-vacuity: only {len(edges)} intra-package edges found"
    assert (source, target) not in edges, (
        f"forbidden import edge {source} -> {target}: the authority layers must not "
        "depend on the layers that consume them"
    )
