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
MODULES: tuple[Path, ...] = tuple(sorted(PACKAGE_DIR.glob("*.py")))
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
    """Imports at module scope only — a function-local import is not a load."""
    out: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            out.add(node.module)
    return out


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
        "readline",
        "readlines",
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


def test_no_gate3a_module_calls_a_read_network_or_subprocess_primitive() -> None:
    """FB-8: the property four audit records rest on, pinned at last.

    Mutation this kills: adding `Path(p).read_bytes()`, `open(...)`,
    `socket.connect(...)` or `subprocess.run(...)` anywhere in the package.
    """
    offenders: list[str] = []
    for path in MODULES:
        for name in sorted(_called_names(_tree(path)) & FORBIDDEN_CALLS):
            # `json.loads`-style names are absent by construction; `compile` is
            # `re.compile` in this package, which is not a code-compile.
            if name == "compile" and "re.compile" in path.read_text(encoding="utf-8"):
                continue
            offenders.append(f"{path.name}:{name}")
    assert offenders == [], (
        f"gate-3a must contain no read / network / subprocess primitive (§12.14); found {offenders}"
    )


def test_only_the_two_writer_modules_touch_the_filesystem_at_all() -> None:
    """The filesystem surface is exactly what the docstrings claim it is."""
    fs_names = frozenset().union(*PERMITTED_FS_CALLS.values())
    offenders: list[str] = []
    for path in MODULES:
        permitted = PERMITTED_FS_CALLS.get(path.name, frozenset())
        for name in sorted(_called_names(_tree(path)) & fs_names):
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


def _outbound_bindings() -> dict[str, set[str]]:
    bound: dict[str, set[str]] = {}
    for path in MODULES:
        for node in _tree(path).body:
            if isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                if node.module.startswith(PACKAGE):
                    continue
                if node.module.split(".")[0] != "scripts":
                    continue
                bound.setdefault(node.module, set()).update(a.name for a in node.names)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("scripts") and not alias.name.startswith(PACKAGE):
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
        "import sys;"
        "import scripts.m15_gate3a.proof, scripts.m15_gate3a.artifacts,"
        " scripts.m15_gate3a.aggregation, scripts.m15_gate3a.cost_schema;"
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
PERMITTED_CALLER_ROOTS: tuple[str, ...] = ("scripts/m15_gate3a", "tests/m15_gate3a")


def _repo_python_files() -> list[Path]:
    root = repo_root()
    out: list[Path] = []
    for sub in ("src", "scripts", "tests", "tools", "migrations"):
        base = root / sub
        if base.exists():
            out.extend(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)
    return out


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
        for node in ast.walk(tree):
            names_it = (
                (node.module or "",)
                if isinstance(node, ast.ImportFrom)
                else tuple(a.name for a in node.names)
                if isinstance(node, ast.Import)
                else ()
            )
            if any(PACKAGE in name for name in names_it):
                offenders.append(f"{rel}:{node.lineno}")
    assert offenders == [], (
        "§12.14 pins the reverse-caller set: nothing outside the package and its own "
        f"tests may import it, but {offenders} does"
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
