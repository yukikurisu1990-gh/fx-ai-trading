"""Tests written against the **class** of defect, not the instance.

Six audit rounds produced the same diagnosis, stated most sharply by the last
one:

    every fix so far has been to the specific attack, and the regression test
    has been written to the specific attack too — until a round produces a
    defence whose *test* is written against the class rather than the instance,
    round six should be expected to look like round five.

Two of that round's findings are the proof. `.git/__pycache__/x.pyc` slipped
past a test that pinned the filename `x`, and a cold-import test set
`PYTHONPYCACHEPREFIX` outside the repository, certifying a configuration a real
run does not have. Both tests were correct about their instance and blind to
their class.

So the tests here enumerate their own inputs from the code, or sweep a space,
rather than naming the case that was found. Where a property cannot be tested
that way, the module says so instead of pretending.
"""

from __future__ import annotations

import ast
import importlib
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.m15_track_a import containment, isolation, scratch

REPO = scratch.repo_root()

#: Phrases that mark a mention of a retired name as historical rather than live.
_RETIREMENT_MARKERS: tuple[str, ...] = (
    "used to read",
    "formerly",
    "renamed",
    "retired",
    "no longer",
    "withdrawn",
    "an earlier drafting",
    "superseded",
    "stale",
)


@pytest.fixture
def guards() -> object:
    isolation.install_all()
    try:
        yield
    finally:
        isolation.uninstall_all()


# ---------------------------------------------------------------------------
# Class: "a listed target is reachable under another name"
# ---------------------------------------------------------------------------


def test_every_listed_native_target_is_actually_refused(guards: object) -> None:
    """Enumerated from the list, so a new entry is covered without a new test.

    Round five's list had three entries that did not refuse and one with a
    keyword hole, while §6 told a reviewer the list *was* the guarantee. This
    walks the list itself.
    """
    unreachable: list[str] = []
    for module_name, dotted in isolation.NATIVE_REFUSED_TARGETS:
        try:
            module = importlib.import_module(module_name)
        except Exception:  # noqa: BLE001 - optional dependency
            continue
        resolved = isolation._resolve_attribute(module, dotted)
        if resolved is None:
            continue
        owner, attribute = resolved
        target = getattr(owner, attribute)
        try:
            target("__nx__")
        except isolation.IsolationError:
            continue
        except Exception:  # noqa: BLE001
            unreachable.append(f"{module_name}.{dotted} raised something else")
            continue
        unreachable.append(f"{module_name}.{dotted} did NOT refuse")
    assert unreachable == [], unreachable


def test_no_listed_class_target_loses_its_type_identity(guards: object) -> None:
    """Replacing a class with a function broke `isinstance` twice, in two rounds.

    Swept over the list rather than over the seven classes that were found.
    """
    broken: list[str] = []
    for module_name, dotted in isolation.NATIVE_REFUSED_TARGETS:
        try:
            module = importlib.import_module(module_name)
        except Exception:  # noqa: BLE001
            continue
        resolved = isolation._resolve_attribute(module, dotted)
        if resolved is None:
            continue
        owner, attribute = resolved
        replacement = getattr(owner, attribute)
        original = next(
            (o for (t, a, o) in isolation._state.patched if t is owner and a == attribute),
            None,
        )
        if isinstance(original, type) and not isinstance(replacement, type):
            broken.append(f"{module_name}.{dotted}")
    assert broken == [], broken


def test_guarding_the_dependency_does_not_break_the_dependency(guards: object) -> None:
    """A guard that breaks what it guards is not an option.

    Subclassing `pyarrow._fs.FileSystem` broke `pyarrow._hdfs` on import; that
    is why the module is disclosed rather than patched. This sweeps the
    dependency's own import graph instead of naming `_hdfs`.
    """
    for name in ("pyarrow", "pyarrow.fs", "pyarrow.parquet", "pyarrow.dataset", "pandas"):
        try:
            importlib.import_module(name)
        except ImportError:
            continue
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"the guards broke `import {name}`: {exc!r}")


def test_anything_that_cannot_be_guarded_is_disclosed(guards: object) -> None:
    """The disclosure channel must be non-empty while a known gap exists.

    `unpatchable_native_targets()` returned `()` while `pyarrow._fs` was wide
    open and §6 pointed a reviewer at it.
    """
    disclosed = isolation.unpatchable_native_targets()
    assert disclosed, "the disclosure channel is empty; §6 tells a reviewer to read it"
    assert any("pyarrow._fs" in entry for entry in disclosed)


# ---------------------------------------------------------------------------
# Class: "the apparatus is not runnable"
# ---------------------------------------------------------------------------


def test_a_cold_import_of_every_first_party_package_survives(tmp_path: Path) -> None:
    """Swept over the packages on disk, and **without** `PYTHONPYCACHEPREFIX`.

    Setting that variable is what let a previous version of this test pass
    while every real import died: it moved the bytecode cache out of the
    repository, which is not the configuration a run has.
    """
    packages = sorted(
        {
            path.parent.name
            for path in (REPO / "src").rglob("__init__.py")
            if path.parent.parent.name == "src"
        }
    ) or ["fx_ai_trading"]
    modules = [*packages, "scripts.m15_gate3a", "scripts.m15_track_a", "json", "csv", "difflib"]
    result = subprocess.run(  # noqa: S603
        [
            sys.executable,
            "-c",
            "import sys, importlib; sys.path.insert(0, r'"
            + str(REPO)
            + "');"
            + "from scripts.m15_track_a import isolation; isolation.install_all();"
            + f"[importlib.import_module(m) for m in {modules!r}]; print('COLD OK')",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr[-2500:]
    assert "COLD OK" in result.stdout


def test_ordinary_tool_output_inside_the_repository_is_writable(guards: object) -> None:
    """Swept over what a run actually produces, not over the one path that failed."""
    for relative in (
        "__pycache__",
        "scripts/__pycache__",
        "src/fx_ai_trading/__pycache__",
        "src/fx_ai_trading/__pycache__/x.cpython-312.pyc",
        ".pytest_cache/v/cache/lastfailed",
        ".ruff_cache/x",
        ".coverage",
        "coverage.xml",
        "htmlcov/index.html",
        ".venv/Lib/site-packages/anything.py",
    ):
        isolation.assert_write_allowed(str(REPO / relative), what="mkdir")


def test_no_protected_tree_is_writable_through_a_cache_name(guards: object) -> None:
    """The mirror of the above, swept over the protected roots rather than one of them."""
    for root in (".git", "data", "models"):
        for tail in ("__pycache__", "__pycache__/x.pyc", ".pytest_cache/x"):
            with pytest.raises(isolation.IsolationError):
                isolation.assert_write_allowed(str(REPO / root / tail))


# ---------------------------------------------------------------------------
# Class: "the source check does not see this shape of read"
# ---------------------------------------------------------------------------


def test_the_read_route_contains_only_declared_shapes() -> None:
    """The property, stated once, over the whole function.

    Not "no `Subscript`", not "no decorator", not "no format spec" — those were
    three separate findings and three separate patches. The property is that
    **every node and every call in `read_historical` is on a declared list**,
    and a new way of reading has to get past that rather than past a name.
    """
    from scripts.m15_track_a import read_route

    tree = ast.parse(Path(read_route.__file__).read_text(encoding="utf-8"))
    functions = [
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "read_historical"
    ]
    assert len(functions) == 1
    function = functions[0]
    assert not function.decorator_list
    for child in ast.walk(function):
        assert type(child) in containment._PERMITTED_READ_ROUTE_NODES, type(child).__name__
        if isinstance(child, ast.Call):
            name = getattr(child.func, "id", None) or getattr(child.func, "attr", None)
            assert name in containment._PERMITTED_READ_ROUTE_CALLS, name
        if isinstance(child, ast.FormattedValue):
            assert child.format_spec is None


def test_no_permitted_call_name_is_rebound_at_module_level() -> None:
    """A name-based allowlist means nothing if the name can be made to mean anything.

    Checked over the whole allowlist rather than over `gated_read_window`,
    which is the one that was found.
    """
    from scripts.m15_track_a import read_route

    tree = ast.parse(Path(read_route.__file__).read_text(encoding="utf-8"))
    rebound = containment._module_level_rebindings(tree) & containment._PERMITTED_READ_ROUTE_CALLS
    assert rebound == set(), rebound


# ---------------------------------------------------------------------------
# Class: "the artefact claims more than the mechanism delivers"
# ---------------------------------------------------------------------------


def test_the_audit_status_does_not_claim_universality() -> None:
    """Six rounds defeated a report that said `VERIFIED_NO_UNGATED_ROUTE`.

    The status is the artefact a reviewer quotes. It must not say something no
    in-process audit can establish.
    """
    for forbidden in ("VERIFIED", "NO_UNGATED_ROUTE", "GUARANTEED", "PROVEN"):
        assert forbidden not in containment.STATUS_CONTAINED, containment.STATUS_CONTAINED


def test_every_report_carries_its_own_bounds() -> None:
    """The qualification travels with the verdict, so it cannot be dropped in quotation."""
    report = containment.audit()
    assert report["bounds"] == list(containment.AUDIT_BOUNDS)
    assert len(report["bounds"]) >= 4
    joined = " ".join(report["bounds"]).lower()
    for subject in ("c extension", "hardlink", "advisory", "not a sandbox"):
        assert subject in joined, subject


def test_the_report_separates_the_verdict_carrying_checks_from_the_advisory_ones() -> None:
    """A consumer could not tell which checks carried the verdict."""
    report = containment.audit()
    assert set(report["behavioural_checks"]) == set(containment.BEHAVIOURAL_CHECKS)
    assert set(report["source_checks_advisory"]) == set(containment.SOURCE_CHECKS)
    assert not set(report["behavioural_checks"]) & set(report["source_checks_advisory"])
    assert {c["check"] for c in report["checks"]} == set(containment.BEHAVIOURAL_CHECKS) | set(
        containment.SOURCE_CHECKS
    )


def test_the_gate_document_does_not_use_the_retired_status_or_field() -> None:
    """A renamed token left behind in prose is the drift this PR kept producing."""
    # The propagation **targets** are swept too. A review round found the
    # retired turnover token alive in `m15_minimum_research_gate.md` — a file
    # this test did not read — pointing at the very section that withdrew it.
    # A drift test that covers the source and not the places the source was
    # copied to is the same instance-not-class mistake this module exists for.
    retired = (
        "NATIVE_READER_TARGETS",
        "VERIFIED_NO_UNGATED_ROUTE",
        "TURNOVER_AXES_FIXED_AT_THE_COMMITTED_IMPLEMENTATION_MEAN_OVER_ACTIVE_DAYS",
    )
    for relative in (
        "docs/design/m15_track_a_execution_gate.md",
        "docs/governance/m15_audit_playbook.md",
        "docs/design/m15_minimum_research_gate.md",
        "docs/design/m15_first_cost_hurdle_aware_preregistration_design.md",
        "CLAUDE.md",
    ):
        lines = (REPO / relative).read_text(encoding="utf-8").splitlines()
        for number, line in enumerate(lines, 1):
            # A *sentence* saying the name is gone is the opposite of a live
            # use, and a sentence wraps across lines. Checking the line alone
            # failed a historical reference whose marker sat on the line above,
            # so the unit is the surrounding window rather than the line.
            window = " ".join(lines[max(0, number - 3) : number + 2]).lower()
            if any(marker in window for marker in _RETIREMENT_MARKERS):
                continue
            for name in retired:
                assert name not in line, f"{relative}:{number} still uses {name}"
    doc = (REPO / "docs" / "design" / "m15_track_a_execution_gate.md").read_text(encoding="utf-8")
    assert containment.STATUS_CONTAINED in doc


def test_the_ledger_is_protected_against_every_handled_mutating_event(
    guards: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Swept over the event table rather than over the routes that were found.

    Five separate rounds each added the destruction route that round's audit
    happened to try.
    """
    root = tmp_path / "track_a_scratch"
    root.mkdir()
    monkeypatch.setattr(scratch, "scratch_root", lambda: root)
    ledger = root / "exploratory_seen_ledger.jsonl"
    scratch.append_line(ledger, '{"probe": 1}')
    intact = ledger.read_bytes()

    decoy = root / "decoy.bin"
    decoy.write_bytes(b"x")
    attacks = {
        "os.truncate": lambda: os.truncate(ledger, 0),
        "unlink": lambda: ledger.unlink(),
        "rename": lambda: os.rename(ledger, str(ledger) + ".moved"),
        "replace": lambda: os.replace(decoy, ledger),
        "open w": lambda: open(ledger, "w").close(),  # noqa: PTH123, SIM115
        "os.open trunc": lambda: os.close(os.open(ledger, os.O_WRONLY | os.O_TRUNC)),
    }
    for label, attack in attacks.items():
        with pytest.raises(isolation.IsolationError):
            attack()
        assert ledger.read_bytes() == intact, label
