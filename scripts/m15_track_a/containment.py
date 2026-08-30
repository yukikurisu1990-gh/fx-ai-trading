"""The Track A containment audit — minimum, and deliberately not more.

`P_11_TRACK_A_CONTAINMENT_AUDIT_TEMPLATE_DOES_NOT_EXIST_AND_IS_NOT_CREATED_HERE`
recorded the gap: playbook §4 is the repository's only containment checklist,
it says it is "for **any future machinery audit**", and its items require
"**Real-data read routes** — none reachable" and "**Real M15 derivation
routes** — none enabled" — which Track A's code must, by construction, have.
So §4 read literally BLOCKS Track A forever, and read through §8.12.2's
(withdrawn) unsatisfiable-therefore-inapplicable move it covers Track A not at
all.

This module is the third option: **§4's items inverted for a stage that must
have a read route.**  Where §4 asks "is the route absent?", this asks "is the
route the single declared one, and is it gated?".  Everything §4 asks about
broker, network, DB, credentials and protected paths stays at **none**.

Behaviour first, structure second
---------------------------------

An earlier drafting of this module answered every question by reading source:
substring scans of ``inspect.getsource`` for the names of the gates, and an AST
sweep for a fixed set of reader names over a hand-written module roster.  An
independent review defeated all of it — a ``read_historical`` with **no gates**
whose *docstring* merely listed the gate names passed the "is it gated?" check,
an aliased ``_reader = builtins.open`` passed the reader sweep, and a new module
dropped into the package was never scanned at all because nobody had added it
to the roster.

The lesson is not "write a longer list of reader names". It is that a source
scan can only ever answer *did the author write the thing I thought to look
for*. So the checks below are ordered:

1. **Six behavioural probes** come first and carry the verdict
   (:data:`BEHAVIOURAL_CHECKS`). They arm the guards and then actually attempt
   the forbidden thing — a write into ``docs/``, a read under ``data/``, a
   remote engine, a subprocess, an ungranted read — and require a refusal. A
   probe cannot be satisfied by a comment.
2. **Six source checks** come second (:data:`SOURCE_CHECKS`) and are advisory
   in exactly the way a source scan has to be. ``broker_live_demo`` is one of
   them, not a probe: it iterates ``FORBIDDEN_OPERATIONS`` and calls
   ``assert_operation_allowed``, which raises **iff** the name is in that same
   dict, so it cannot fail and it attempts nothing.

Their roster is **enumerated from the directory**, so a new module is scanned by
existing. ``read_body_declared`` is a source check too, and it is an
**allowlist over the AST node types** the route may contain — three rounds of
allowlisting *call names* were each defeated by a way of reading that is not a
call: a ``numpy.memmap`` behind a module global, a ``Subscript`` callee, a
``Subscript`` that is not a callee at all, a bare-``Name`` decorator, and an
f-string format spec. The answer was never going to be a longer list of reader
names. Since R1's body landed, that check no longer asks whether the route is
*empty* — it asks whether the route is **the declared one**: one definition,
one ``open``, on a path from ``source_path_for``, inside the gated window.

Every probe is chosen so that a *failure of the guard* is still harmless: the
read probe names a file that does not exist, so if the hook were absent the
result is ``FileNotFoundError`` rather than a real read.

Scope, stated so it is not mistaken for the production audit
------------------------------------------------------------

This checks **execution containment** — what a Track A run can reach.  It is not
a hostile-input audit, not a mutation-resistance measurement, not a scrubber
probe, and not a substitute for the gate-6 source-contamination audit that
Track B still needs.  §8.13's instruction was a *minimum* containment check, and
widening it here would be the over-engineering §5 tests for.
"""

from __future__ import annotations

import ast
import importlib
import socket
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from scripts.m15_track_a import authorization, derivation, isolation, read_route, scratch

#: Final statuses this audit may report.  Closed set; anything else is a bug.
#: The verdict this audit is entitled to reach.
#:
#: It used to read ``…_VERIFIED_NO_UNGATED_ROUTE``, and that phrasing is the
#: defect this whole PR kept reproducing in new places: **the artefact claimed
#: more than the mechanism delivers.** Six independent audit contexts each found
#: a route the audit had certified against, and each time the fix went to the
#: specific route — never to the claim. No in-process audit can establish "no
#: ungated route": a C extension, a rewritten source file, a reflected reader
#: and a pre-seeded hardlink are all outside what it can see, and three of those
#: were demonstrated end to end **against a report that said VERIFIED**.
#:
#: So the status now names what the audit actually did: it ran its probes and
#: they passed. What that does and does not license is enumerated in
#: :data:`AUDIT_BOUNDS`, emitted with every report, so the verdict cannot be
#: picked up without the qualification.
STATUS_CONTAINED: Final[str] = "TRACK_A_EXECUTION_CONTAINMENT_PROBES_PASSED_BOUNDED_ASSURANCE"
STATUS_BREACHED: Final[str] = "TRACK_A_EXECUTION_CONTAINMENT_PROBE_FAILED"

#: What a passing report does **not** establish.  Emitted with every report.
AUDIT_BOUNDS: Final[tuple[str, ...]] = (
    "It does not establish that no route reads market data — R1 now HAS a read "
    "body, gated but present. It establishes that the probed boundaries refused, "
    "and that the committed source of read_historical at this head is the "
    "declared route: one definition, one open, on a path from source_path_for, "
    "inside the gated read window, with no other reader anywhere in its module.",
    "It does not establish that a read stays inside what was AUTHORISED, either. "
    "That is the route's own arithmetic, not this audit's: two review roles "
    "found the first drafting of the body reading the grant's span and pair list "
    "rather than the intersection with the request, so a grant wider than the "
    "request read undeclared data, on both axes, while every check here passed.",
    "The source checks are advisory. Seven audit rounds each defeated the "
    "then-current version with a way of reading it did not anticipate: a "
    "numpy.memmap behind a module global, a Subscript callee, a Subscript that "
    "is not a call, a bare-Name decorator, an f-string format spec, a shadowed "
    "permitted name, a default argument, a second definition of the route, and a "
    "covert read placed in a module helper rather than in the route itself.",
    "A C extension that calls the OS directly is invisible to the audit hook. "
    "The named ones are refused (isolation.NATIVE_REFUSED_TARGETS); the ones "
    "that cannot be are listed by isolation.unpatchable_native_targets().",
    "A hardlink pre-seeded into the working tree defeats every path test, and "
    "code running in this process can disarm any in-process guard.",
    "What this apparatus buys is that an accidental boundary crossing fails "
    "loudly, and a deliberate one has to appear in a diff. It is not a sandbox, "
    "and a passing report is not a substitute for reading the diff.",
)

#: The modules a Track A run is allowed to reach a read through.  A read route
#: appearing anywhere else in this package is a finding.
DECLARED_READ_ROUTE_MODULE: Final[str] = "scripts.m15_track_a.read_route"
DECLARED_DERIVATION_ROUTE_MODULE: Final[str] = "scripts.m15_track_a.derivation"

#: Modules permitted to open a file, and the one thing each may open.
#: A blanket exemption is what let the first drafting skip four of eleven
#: modules entirely; this names the file each is exempt *for*.
_PERMITTED_FILE_OPENERS: Final[dict[str, str]] = {
    "scripts.m15_track_a.scratch": "the single append_line writer, path-checked first",
    "scripts.m15_track_a.seen_ledger": "its own append-only ledgers beneath the scratch root",
    "scripts.m15_track_a.breadth": "its own append-only ledger beneath the scratch root",
    "scripts.m15_track_a.oos_budget": "its own append-only ledger and claim files",
    "scripts.m15_track_a.containment": "its own behavioural probes and the package sources "
    "it parses — and, like every other module, only where the audit hook permits",
    "scripts.m15_track_a.read_route": "the one declared market-data route. This entry "
    "exempts the module from the name sweep below, and a review role measured what that "
    "bought an attacker: four helpers in this module became the only code in the package "
    "that could open a file with no source check at all, and a covert read added to one of "
    "them kept the audit at PASS. So _check_read_body_is_declared now sweeps this module "
    "**whole** — every reader-name call in it must be the one open the body performs, on a "
    "path from source_path_for, inside the gated read window. The exemption is bounded by "
    "that check rather than by trust",
    "scripts.m15_track_a.isolation": "the enforcement layer itself: it names os.open in order "
    "to guard dir_fd, and patches third-party entry points by reflection. Its own file "
    "access is governed by the same audit hook as everything else",
}

#: The one module allowed to reflect.  Refusing a C-extension entry point means
#: resolving ``(module, attribute)`` pairs at run time, which is
#: ``getattr`` with a computed name by construction — and the reflection is the
#: guard being installed, not a reader being assembled. Its own file access is
#: governed by the same audit hook as every other module's.
_PERMITTED_REFLECTION: Final[frozenset[str]] = frozenset({"scripts.m15_track_a.isolation"})

#: Call names that open something.  Explicitly **not** a completeness claim —
#: see the module docstring.  A re-verification defeated this set with
#: ``pandas.read_feather`` and with an alias, so the alias *binding* is now
#: caught too; the set itself still cannot be complete, and the behavioural
#: probes are what carry the verdict.
#:
#: ``connect`` is deliberately **not** here. It is a database verb, not a file
#: one, and including it made the sweep flag ``real_connect =
#: socket.socket.connect`` in the isolation guard itself — the same
#: flags-its-own-source shape the substring version had. Database access is the
#: audit hook's ``sqlite3.connect`` limb and the engine guard, not this sweep's.
_READER_NAMES: Final[frozenset[str]] = frozenset(
    {
        "open",
        "read_text",
        "read_bytes",
        "read_csv",
        "read_parquet",
        "read_json",
        "read_feather",
        "read_pickle",
        "read_hdf",
        "read_sql",
        "read_table",
        "read_orc",
        "ParquetFile",
        "memory_map",
        "fromfile",
        "genfromtxt",
        "loadtxt",
        "load",
        "copyfile",
        "copy2",
        "FileIO",
        "ZipFile",
        "OSFile",
        "input_stream",
        "output_stream",
        "open_input_file",
        "open_input_stream",
        "open_output_stream",
        "LocalFileSystem",
        "Booster",
    }
)


@dataclass(frozen=True)
class CheckResult:
    """One containment check and what it found."""

    name: str
    passed: bool
    detail: str

    def as_record(self) -> dict[str, Any]:
        return {"check": self.name, "passed": self.passed, "detail": self.detail}


def package_modules() -> tuple[str, ...]:
    """Every module in the package, enumerated from the directory.

    A hand-maintained roster is scanned only if someone remembers to extend it,
    which is the "the roster is nine, not eight" defect this repository has
    already recorded once.
    """
    package_dir = Path(__file__).resolve().parent
    names = ["scripts.m15_track_a"]
    names.extend(
        f"scripts.m15_track_a.{path.stem}"
        for path in sorted(package_dir.glob("*.py"))
        if path.stem != "__init__"
    )
    return tuple(names)


# ---------------------------------------------------------------------------
# Behavioural probes (6) — these carry the verdict
# ---------------------------------------------------------------------------


def _check_write_containment_enforced() -> CheckResult:
    """A write outside the scratch root is refused **by the process**, not by a predicate."""
    if not isolation.is_installed():
        return CheckResult("write_containment_enforced", False, "guards are not installed")
    # "r+" is a write mode on a path that does not exist: a working guard raises
    # IsolationError, a broken one raises FileNotFoundError. Neither creates it.
    target = scratch.repo_root() / "docs" / "__track_a_write_probe_does_not_exist__.md"
    try:
        with open(target, "r+", encoding="utf-8"):  # noqa: SIM115, PTH123
            pass
    except isolation.IsolationError:
        return CheckResult(
            "write_containment_enforced",
            True,
            "a write into docs/ is refused by the audit hook, not merely by assert_writable",
        )
    except OSError:
        return CheckResult(
            "write_containment_enforced",
            False,
            "the audit hook did not refuse a write outside the scratch root",
        )
    return CheckResult(  # pragma: no cover - would mean the probe file exists
        "write_containment_enforced", False, "a write outside the scratch root succeeded"
    )


def _check_market_data_read_refused() -> CheckResult:
    """A read under ``data/`` outside the gated window is refused."""
    if not isolation.is_installed():
        return CheckResult("market_data_read_refused", False, "guards are not installed")
    if isolation.is_read_window_open():  # pragma: no cover - never true at audit time
        return CheckResult("market_data_read_refused", False, "the gated read window is open")
    target = scratch.repo_root() / "data" / "__track_a_read_probe_does_not_exist__.jsonl"
    try:
        with open(target, "rb"):  # noqa: SIM115, PTH123
            pass
    except isolation.IsolationError:
        return CheckResult(
            "market_data_read_refused",
            True,
            "a read under data/ outside the gated read window is refused process-wide",
        )
    except OSError:
        return CheckResult(
            "market_data_read_refused",
            False,
            "the audit hook did not refuse a read under data/ — the single read route is a "
            "property of one function, not of the process",
        )
    return CheckResult(  # pragma: no cover
        "market_data_read_refused", False, "a market-data read succeeded outside the route"
    )


def _check_network() -> CheckResult:
    """A non-loopback connect and a non-loopback name lookup are both refused."""
    if not isolation.is_installed():
        return CheckResult("network", False, "isolation guards are not installed")
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.connect(("203.0.113.1", 80))
    except isolation.IsolationError:
        pass
    except OSError as exc:
        return CheckResult("network", False, f"a non-loopback connect was not refused: {exc}")
    else:  # pragma: no cover - would mean the guard is absent and the host answered
        return CheckResult("network", False, "a non-loopback connect was not refused")
    finally:
        probe.close()
    try:
        socket.getaddrinfo("example.invalid", 80)
    except isolation.IsolationError:
        pass
    except OSError as exc:
        return CheckResult("network", False, f"a non-loopback lookup was not refused: {exc}")
    else:  # pragma: no cover
        return CheckResult("network", False, "a non-loopback name lookup was not refused")
    return CheckResult(
        "network", True, "non-loopback connects, datagrams and name lookups are refused"
    )


def _check_subprocess() -> CheckResult:
    """A subprocess escapes every in-process guard at once, so it is refused."""
    if not isolation.is_installed():
        return CheckResult("subprocess", False, "isolation guards are not installed")
    try:
        import subprocess

        subprocess.Popen(["cmd", "/c", "ver"])  # noqa: S603, S607
    except isolation.IsolationError:
        return CheckResult("subprocess", True, "launching a process is refused")
    except Exception as exc:  # pragma: no cover - a launch failure is not the guard
        return CheckResult("subprocess", False, f"the launch failed for another reason: {exc}")
    return CheckResult("subprocess", False, "a subprocess was launched")  # pragma: no cover


def _check_database() -> CheckResult:
    """A non-in-memory engine is refused, or SQLAlchemy is absent."""
    try:
        import sqlalchemy
    except ImportError:  # pragma: no cover - environment without SQLAlchemy
        return CheckResult("database", True, "SQLAlchemy is not installed; no engine is buildable")
    if not isolation.is_installed():
        return CheckResult("database", False, "isolation guards are not installed")
    try:
        sqlalchemy.create_engine("postgresql://user:pw@example.invalid/db")
    except isolation.IsolationError:
        return CheckResult("database", True, "a non-in-memory engine is refused")
    except Exception as exc:  # pragma: no cover - a driver error is not the guard
        return CheckResult("database", False, f"engine creation failed for another reason: {exc}")
    return CheckResult("database", False, "a remote database engine was built")  # pragma: no cover


def _check_broker_and_live() -> CheckResult:
    """Every named forbidden operation refuses."""
    unrefused: list[str] = []
    for operation in isolation.FORBIDDEN_OPERATIONS:
        try:
            isolation.assert_operation_allowed(operation)
        except isolation.IsolationError:
            continue
        unrefused.append(operation)  # pragma: no cover
    if unrefused:  # pragma: no cover
        return CheckResult("broker_live_demo", False, f"not refused: {unrefused}")
    return CheckResult(
        "broker_live_demo",
        True,
        f"all {len(isolation.FORBIDDEN_OPERATIONS)} named operations refuse: broker, order "
        "submission, live, demo, production deploy, external storage",
    )


def _check_read_route_refuses_without_a_grant() -> CheckResult:
    """The declared route itself refuses an ungranted request, and reads nothing."""
    if not isolation.is_installed():
        return CheckResult("read_route_gated", False, "guards are not installed")
    from scripts.m15_track_a.identity import CALENDAR_UTC_DATES_NO_MARKET_HOURS, RunIdentity

    request = read_route.ReadRequest(
        span_start_utc="2025-05-01",
        span_end_utc="2025-05-31",
        pairs=("EUR_USD",),
        timeframe="M1",
        warmup_extension_start_utc="2025-05-01",
    )
    identity = RunIdentity(
        run_id="containment-probe",
        code_sha="0" * 40,
        calendar_semantics=CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        started_at_utc="2026-01-01T00:00:00Z",
    )
    try:
        read_route.read_historical(request, identity, grant=None)
    except authorization.AuthorizationError:
        return CheckResult(
            "read_route_gated",
            True,
            "the declared route refuses a request with no grant, before anything is opened",
        )
    except Exception as exc:  # pragma: no cover
        return CheckResult("read_route_gated", False, f"refused for the wrong reason: {exc}")
    return CheckResult("read_route_gated", False, "an ungranted read was not refused")


def _terminal_raise_is_not_implemented(body: list[ast.stmt]) -> bool:
    """Whether the **last** statement of a body is ``raise NotImplementedError(...)``.

    Following the last statement, rather than asking whether such a raise exists
    *anywhere*, is the point. The first drafting asked the weaker question and a
    two-line decoy defeated it:

        if False:
            raise NotImplementedError("...")
        return open(path, "rb").read()

    A live body with a dead raise in it satisfied "there is a raise"; it does
    not satisfy "the function ends in one".
    """
    if not body:
        return False
    last = body[-1]
    if isinstance(last, ast.Raise):
        exc = last.exc
        func = getattr(exc, "func", None) if isinstance(exc, ast.Call) else exc
        return getattr(func, "id", None) == "NotImplementedError"
    if isinstance(last, ast.With):
        return _terminal_raise_is_not_implemented(last.body)
    if isinstance(last, ast.Try):
        return _terminal_raise_is_not_implemented(last.body)
    return False


#: The only calls ``read_historical`` may contain.  An allowlist, because the
#: question "does this function read?" cannot be answered by listing the ways to
#: read — a re-verification wrote a body using ``numpy.memmap`` and a module
#: global, with no ``return`` and a terminal ``raise NotImplementedError``, and
#: every check passed.  Any call that is not one of the declared gates is a
#: finding, whatever it is called.
#: Names that let a caller build any other name at runtime.  Their presence in
#: the read route is a finding on its own: a reader assembled from
#: ``getattr(builtins, "op" + "en")`` has no call name to compare.
_INDIRECTION_NAMES: Final[frozenset[str]] = frozenset(
    {
        "getattr",
        "__import__",
        "eval",
        "exec",
        "vars",
        "globals",
        "locals",
        "__builtins__",
        "__dict__",
        "__getattribute__",
    }
)

#: The AST node types ``read_historical`` may contain.
#:
#: An **allowlist over node types**, because three rounds of allowlisting over
#: *call names* kept losing to things that read without being a call the check
#: could name: a ``Subscript`` (``SLURP["path"]`` on an object whose
#: ``__getitem__`` reads), a bare-``Name`` decorator that reads at definition
#: time, and an f-string whose ``__format__`` reads. None of those is a
#: recognisable call, and no list of reader names reaches them.
#:
#: The permitted set is exactly what the declared gate sequence needs. Anything
#: else — a subscript, a lambda, a dict display, a comprehension, an ``await``,
#: an import — is a finding, and extending the set is a diff a reviewer sees.
_PERMITTED_READ_ROUTE_NODES: Final[frozenset[type[ast.AST]]] = frozenset(
    {
        ast.arg,
        ast.arguments,
        ast.Assign,
        ast.Attribute,
        ast.Call,
        ast.Constant,
        ast.Expr,
        ast.FormattedValue,
        ast.FunctionDef,
        ast.If,
        ast.JoinedStr,
        ast.keyword,
        ast.Load,
        ast.Name,
        ast.Not,
        ast.Raise,
        ast.Store,
        ast.UnaryOp,
        ast.With,
        ast.withitem,
        # Added with the body: a per-pair loop, a per-line loop, the bounds
        # comparisons, the dict it accumulates into, and the try/except that
        # turns a malformed line into a refusal.  The set is exactly what the
        # body uses and no more, so widening it is a diff a reviewer sees.
        ast.For,
        ast.Compare,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.NotEq,
        ast.IsNot,
        ast.BoolOp,
        ast.And,
        ast.Break,
        ast.Continue,
        ast.Dict,
        ast.Return,
        ast.Subscript,
        ast.Try,
        ast.ExceptHandler,
        ast.AnnAssign,
        ast.List,
        ast.Tuple,
    }
)

_PERMITTED_READ_ROUTE_CALLS: Final[frozenset[str]] = frozenset(
    {
        "is_installed",
        "ReadRouteError",
        "require_authorization",
        "assert_span_admissible",
        "assert_declared",
        "record_grant",
        "gated_read_window",
        # The body's own vocabulary, added in the diff that supplied the body.
        # Extending this set is a change a reviewer sees, which is the point.
        "source_path_for",
        "is_file",
        "open",
        "enumerate",
        "strip",
        "loads",
        "_source_timestamp",
        "_row_from_source",
        "_pairs_to_read",
        "is_dead_window_instant",
        "isoformat",
        "date",
        "append",
        "_as_instant",
        "max",
        "min",
        "HistoricalRead",
    }
)


# --- source checks -----------------------------------------------------------


def _module_level_bindings(tree: ast.AST) -> set[str]:
    """Every name bound at module level — assignments, defs, classes, imports.

    Wider than :func:`_module_level_rebindings`, and used for a different
    question: not "was a gate name shadowed" but "could this subscript be
    reaching a module object that reads".
    """
    names = set(_module_level_rebindings(tree))
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            names.update(alias.asname or alias.name.split(".")[0] for alias in node.names)
    return names


def _module_level_rebindings(tree: ast.AST) -> set[str]:
    """Names **assigned** at module level, which a name-based allowlist sees through.

    Only ``Assign`` and ``AnnAssign``. A ``def``, a ``class`` or an ``import``
    that binds one of these names *is* where the name comes from — that is the
    declared gate arriving, not a rebinding of it. ``gated_read_window =
    _Window`` is the shape that matters: it leaves the allowlist checking a
    name that now means something else.
    """
    names: set[str] = set()
    for node in getattr(tree, "body", []):
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        for target in targets:
            if isinstance(target, ast.Name):
                names.add(target.id)
            elif isinstance(target, ast.Tuple):
                names.update(e.id for e in target.elts if isinstance(e, ast.Name))
    return names


def _check_read_body_is_declared() -> CheckResult:
    """The route's body, at source: it is the declared route and nothing else.

    **A source-level statement about this head, not a behavioural probe.**

    Until the body existed this check asked whether it was *absent*, and the
    answer licensed a claim that nothing could be read. That question is gone —
    R1 has a body now — and pretending otherwise would be the overclaiming this
    package spent six rounds retiring. What replaces it is the question that
    still has a useful answer: **is the body the one route that was declared,
    reading only the one declared source?**

    Six conditions:

    1. exactly **one** ``read_historical``, so a second live definition cannot
       hide behind the first;
    2. **no module-level rebinding** of a permitted call name — the allowlist
       checks names, and a rebinding makes a name mean anything;
    3. no default argument that is a call or a subscript, since those run at
       import time, before any gate exists;
    4. every call in the body is on :data:`_PERMITTED_READ_ROUTE_CALLS`, and no
       call has a callee this check cannot name;
    5. every node type is on :data:`_PERMITTED_READ_ROUTE_NODES`, and the
       function carries no decorator;
    6. the body opens **exactly one** thing — a path obtained from
       ``source_path_for`` — and does so **inside** ``gated_read_window``;
    7. and **the module around it** contains no other reader at all.

    Conditions 1–5 are inherited from the absent-body check and each of them
    was added because the previous set had been defeated end to end. 6 is what
    "one route, no fallback" means once a route exists.

    7 exists because 1–6 read **one function** while
    :data:`_PERMITTED_FILE_OPENERS` exempts the **module**. A review role
    measured the gap: it added four lines to ``_row_from_source`` — a helper, so
    outside conditions 1–6 — read an undeclared market-data file from them, and
    the audit still returned ``PASS`` on every check. Its first attempt used
    ``globals()`` and ``_indirection_findings`` caught it; the second used no
    reflection and nothing did. So the name sweep the exemption removes is put
    back here with one pinned exception: the single open the body performs.
    """
    tree = ast.parse(Path(read_route.__file__).read_text(encoding="utf-8"))

    definitions = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "read_historical"
    ]
    if len(definitions) != 1:
        return CheckResult(
            "read_body_declared",
            False,
            f"{len(definitions)} definitions of read_historical; the route must be one function",
        )
    node = definitions[0]

    shadowed = sorted(_module_level_rebindings(tree) & _PERMITTED_READ_ROUTE_CALLS)
    if shadowed:
        return CheckResult(
            "read_body_declared",
            False,
            f"module-level rebinding of permitted call name(s) {shadowed}: the allowlist "
            "checks names, so rebinding one makes it mean anything",
        )

    defaults = [d for d in node.args.defaults + node.args.kw_defaults if d is not None]
    if any(isinstance(d, ast.Call | ast.Subscript) for d in defaults):
        return CheckResult(
            "read_body_declared",
            False,
            "a default argument is evaluated at import time, before any gate runs",
        )

    module_level_names = _module_level_bindings(tree)
    unexpected: set[str] = set()
    if node.decorator_list:
        unexpected.add("a decorator (it runs at definition time)")
    opens: list[ast.Call] = []
    for child in ast.walk(node):
        if isinstance(child, ast.FormattedValue) and child.format_spec is not None:
            unexpected.add(f"an f-string format spec at line {child.lineno}")
        if type(child) not in _PERMITTED_READ_ROUTE_NODES:
            unexpected.add(
                f"{type(child).__name__} node at line {child.lineno}"
                if hasattr(child, "lineno")
                else type(child).__name__
            )
        if isinstance(child, ast.Call):
            func = child.func
            if not isinstance(func, ast.Name | ast.Attribute):
                unexpected.add(f"<{type(func).__name__} callee at line {child.lineno}>")
                continue
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name == "open":
                opens.append(child)
            elif name is None or name not in _PERMITTED_READ_ROUTE_CALLS:
                unexpected.add(str(name))
        elif isinstance(child, ast.Name) and child.id in _INDIRECTION_NAMES:
            unexpected.add(f"{child.id} (indirection)")
        elif isinstance(child, ast.Subscript):
            # The body needs subscripts — ``row[key]``, ``rows[pair]`` — so the
            # node type is permitted. What is **not** permitted is a subscript
            # on a **module-level** name: ``SLURP["path"]``, where ``SLURP`` is
            # a module object whose ``__getitem__`` reads, is how a reader hides
            # behind something that is not a call. A subscript on a local is a
            # dict lookup; a subscript on a module global is a capability.
            base = child.value
            base_name = getattr(base, "id", None)
            if base_name is None or base_name in module_level_names:
                unexpected.add(
                    f"a subscript on {base_name or type(base).__name__!s} at line "
                    f"{child.lineno} — subscripting a module-level name can read"
                )
    if unexpected:
        return CheckResult(
            "read_body_declared",
            False,
            f"read_historical contains {sorted(unexpected)}, which are not among its "
            "declared gates and source access",
        )

    if len(opens) != 1:
        return CheckResult(
            "read_body_declared",
            False,
            f"read_historical opens {len(opens)} things; the declared route opens exactly "
            "one, the source file for the pair it is reading",
        )
    opened = opens[0].func
    if not (isinstance(opened, ast.Attribute) and getattr(opened.value, "id", None) == "path"):
        return CheckResult(
            "read_body_declared",
            False,
            "the one open is not on the `path` bound from source_path_for",
        )

    assigns_path_from_source = any(
        isinstance(child, ast.Assign)
        and any(getattr(t, "id", None) == "path" for t in child.targets)
        and isinstance(child.value, ast.Call)
        and (getattr(child.value.func, "id", None) == "source_path_for")
        for child in ast.walk(node)
    )
    if not assigns_path_from_source:
        return CheckResult(
            "read_body_declared",
            False,
            "`path` is not obtained from source_path_for, so the source is not the declared one",
        )

    inside_window = any(
        isinstance(child, ast.With)
        and any(
            getattr(getattr(item.context_expr, "func", None), "attr", None) == "gated_read_window"
            for item in child.items
        )
        and any(descendant is opens[0] for descendant in ast.walk(child))
        for child in ast.walk(node)
    )
    if not inside_window:
        return CheckResult(
            "read_body_declared",
            False,
            "the source open is not inside isolation.gated_read_window(), so the audit hook "
            "would refuse it — or worse, it is outside the window the hook keys on",
        )

    # The one open the body performs is the pinned exception, named by the
    # exact finding the sweep would raise for it and by nothing broader — a
    # line-number exemption would also swallow anything else written on that
    # line.
    pinned = f"{DECLARED_READ_ROUTE_MODULE}:{opened.lineno} references open"
    strays: list[str] = []
    for child in ast.walk(tree):
        if not isinstance(child, ast.Call) or child is opens[0]:
            continue
        callee = child.func
        reader = getattr(callee, "id", None) or getattr(callee, "attr", None)
        if reader in _READER_NAMES:
            strays.append(f"{reader} at line {child.lineno}")
    seen_pinned = False
    for finding in _alias_findings(DECLARED_READ_ROUTE_MODULE, tree):
        if finding == pinned and not seen_pinned:
            seen_pinned = True
            continue
        strays.append(finding)
    if strays:
        return CheckResult(
            "read_body_declared",
            False,
            f"the read route module reads outside its one declared open: {sorted(strays)}. "
            "Its exemption from the name sweep covers that one open and nothing else.",
        )

    return CheckResult(
        "read_body_declared",
        True,
        "read_historical is the only definition, no permitted call name is rebound, every "
        "node and call is on the declared list, it opens exactly one path — the one "
        "source_path_for returns — inside the gated read window, and no other code in the "
        "module opens anything",
    )


def _indirection_findings(module_name: str, tree: ast.AST) -> list[str]:
    """Names that let a caller build a reader the source never spells.

    Separate from :func:`_alias_findings` because it applies to **every**
    module, permitted openers included: ``getattr(builtins, "op" + "en")`` and
    ``builtins.__dict__["open"]`` produce a reader whose name appears nowhere,
    and a module allowed to call ``open`` in plain sight is not allowed to
    assemble one out of sight.
    """
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            direct = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if direct == "getattr":
                for argument in node.args[1:2]:
                    if not isinstance(argument, ast.Constant):
                        findings.append(
                            f"{module_name}:{node.lineno} getattr() with a computed name"
                        )
            elif direct in _INDIRECTION_NAMES and direct != "getattr":
                findings.append(f"{module_name}:{node.lineno} {direct}()")
        elif isinstance(node, ast.Attribute) and node.attr in {
            "__dict__",
            "__builtins__",
            "__getattribute__",
        }:
            findings.append(f"{module_name}:{node.lineno} reflects through {node.attr}")
    return findings


def _alias_findings(module_name: str, tree: ast.AST) -> list[str]:
    """Every *reference* to a reader name, not one binding form.

    An earlier drafting inspected ``ast.Assign`` whose value was a bare
    ``Name``/``Attribute``. A re-verification bound the same callable seven
    other ways — ``getattr(builtins, "open")``, a dict subscript, tuple
    unpacking, an annotated assignment, a walrus, ``from builtins import open
    as _r``, and ``getattr(_pd, "read_parquet")`` — and only the control was
    caught.

    So the rule is now: a reader name appearing **anywhere** in the module, as
    a name, an attribute, an import alias, or a string constant handed to
    ``getattr``, is a finding. That is noisier and it is the right polarity.
    """
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            direct = getattr(func, "id", None) or getattr(func, "attr", None)
            if direct == "getattr":
                for argument in node.args[1:2]:
                    if isinstance(argument, ast.Constant):
                        if argument.value in _READER_NAMES:
                            findings.append(
                                f"{module_name}:{node.lineno} getattr({argument.value!r})"
                            )
                    else:
                        # ``getattr(builtins, "op" + "en")`` — the name is not in
                        # the source, so no name-based sweep can see it.
                        findings.append(
                            f"{module_name}:{node.lineno} getattr() with a computed name"
                        )
            elif direct in _INDIRECTION_NAMES:
                findings.append(f"{module_name}:{node.lineno} {direct}()")
            continue
        if isinstance(node, ast.ImportFrom):
            findings.extend(
                f"{module_name}:{node.lineno} imports {alias.name}"
                for alias in node.names
                if alias.name in _READER_NAMES
            )
            continue
        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        if name in _READER_NAMES:
            findings.append(f"{module_name}:{node.lineno} references {name}")
    return findings


def _check_single_read_route() -> CheckResult:
    """No module outside the declared openers contains a file-opening call.

    Advisory. A name set cannot be complete, and an alias defeats it; the
    behavioural probes above are what establish containment.
    """
    findings: list[str] = []
    for module_name in package_modules():
        module = importlib.import_module(module_name)
        source_file = getattr(module, "__file__", None)
        if source_file is None:  # pragma: no cover
            continue
        tree = ast.parse(Path(source_file).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if name in _READER_NAMES and module_name not in _PERMITTED_FILE_OPENERS:
                findings.append(f"{module_name}:{node.lineno} {name}()")
        # The **indirection** sweep runs on every module, permitted openers
        # included. Skipping a module wholesale is what let a reader added to
        # one of the ledger modules go unscanned; the exemption those modules
        # carry is for calling ``open`` on their own ledger in plain sight, not
        # for assembling a reader by reflection.
        if module_name not in _PERMITTED_REFLECTION:
            findings.extend(_indirection_findings(module_name, tree))
        if module_name not in _PERMITTED_FILE_OPENERS:
            findings.extend(_alias_findings(module_name, tree))
    if findings:
        return CheckResult("single_read_route", False, f"file-access calls outside: {findings}")
    return CheckResult(
        "single_read_route",
        True,
        f"the only market-data route is {DECLARED_READ_ROUTE_MODULE}.read_historical, and "
        f"only {sorted(_PERMITTED_FILE_OPENERS)} open files at all (advisory: a name scan "
        "cannot be complete; the behavioural probes carry the verdict)",
    )


def _check_authorization_has_no_ambient_source() -> CheckResult:
    """No grant may come from the environment, a file, or a module global."""
    tree = ast.parse(Path(authorization.__file__).read_text(encoding="utf-8"))
    findings: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "environ":
            findings.append(f"environ at line {node.lineno}")
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name in {"getenv", "open", "read_text", "load", "loads"}:
                findings.append(f"{name}() at line {node.lineno}")
    if findings:  # pragma: no cover
        return CheckResult("authorization_not_ambient", False, f"ambient source: {findings}")
    return CheckResult(
        "authorization_not_ambient",
        True,
        "a grant is an in-process ReadGrant of exactly that type, re-validated at check "
        "time; no environment variable, file or global can supply one",
    )


def _check_write_root() -> CheckResult:
    """The write root is a constant and protected roots refuse."""
    if "{" in scratch.SCRATCH_ROOT_RELATIVE or "%" in scratch.SCRATCH_ROOT_RELATIVE:
        return CheckResult(  # pragma: no cover
            "write_root", False, "the scratch root carries a caller-supplied component"
        )
    refused = 0
    for relative in ("docs/x.md", "data/x.parquet", "artifacts/m15_gate3a/x.json", "src/x.py"):
        try:
            scratch.assert_writable(scratch.repo_root() / relative)
        except scratch.ScratchRootError:
            refused += 1
    if refused != 4:  # pragma: no cover
        return CheckResult("write_root", False, f"only {refused}/4 protected roots refused")
    return CheckResult(
        "write_root",
        True,
        f"writes are confined to {scratch.SCRATCH_ROOT_RELATIVE}; protected roots and "
        "reserved artifact filenames refuse, case-insensitively",
    )


def _check_derivation_route() -> CheckResult:
    """One derivation route, bound to the committed aggregator in this diff."""
    from scripts.m15_gate3a.aggregation import aggregate_m15

    if derivation.DELEGATE is not aggregate_m15:  # pragma: no cover
        return CheckResult("derivation_route", False, "the delegate binding is not the committed")
    return CheckResult(
        "derivation_route",
        True,
        f"one route, {derivation.SELECTED_ROUTE}, bound to {derivation.DELEGATE_QUALNAME} "
        f"whose audit status is recorded as {derivation.DELEGATE_AUDIT_STATUS}",
    )


#: The behavioural probes, in order.  Each arms the guards and attempts the
#: forbidden thing.  ``broker_live_demo`` is deliberately **not** here: it
#: iterates ``FORBIDDEN_OPERATIONS`` and calls ``assert_operation_allowed``,
#: which raises iff the name is in that same dict — it cannot fail and it
#: attempts nothing, so calling it a probe overstated it.
BEHAVIOURAL_CHECKS: Final[tuple[str, ...]] = (
    "write_containment_enforced",
    "market_data_read_refused",
    "network",
    "subprocess",
    "database",
    "read_route_gated",
)

SOURCE_CHECKS: Final[tuple[str, ...]] = (
    "broker_live_demo",
    "read_body_declared",
    "single_read_route",
    "authorization_not_ambient",
    "write_root",
    "derivation_route",
)

CHECKS: Final[tuple[Any, ...]] = (
    _check_write_containment_enforced,
    _check_market_data_read_refused,
    _check_network,
    _check_subprocess,
    _check_database,
    _check_broker_and_live,
    _check_read_route_refuses_without_a_grant,
    _check_read_body_is_declared,
    _check_single_read_route,
    _check_authorization_has_no_ambient_source,
    _check_write_root,
    _check_derivation_route,
)


def audit() -> dict[str, Any]:
    """Run every check and return the report.  Reads no market data.

    The audit installs the guards for its own duration when they are not
    already installed, and restores the process afterwards. Reporting "not
    installed" would answer a question about ambient process state rather than
    about the guards, and a containment audit that passes only when someone
    remembered to install them is conditional assurance.
    """
    installed_by_audit = not isolation.is_installed()
    if installed_by_audit:
        isolation.install_all()
    try:
        results = [check() for check in CHECKS]
    finally:
        if installed_by_audit:
            isolation.uninstall_all()
    passed = all(result.passed for result in results)
    by_name = {result.name: result.passed for result in results}
    # Three conditions, deliberately. The route has no body at this head, the
    # process actually refused a market-data read, and **the audit as a whole
    # passed** — an earlier drafting computed this field independently of the
    # verdict, so a BREACHED report still carried `no_market_data_read: True`
    # and the field could be quoted on its own.
    no_read = bool(
        passed and by_name.get("read_body_declared") and by_name.get("market_data_read_refused")
    )
    return {
        "status": STATUS_CONTAINED if passed else STATUS_BREACHED,
        "checks": [result.as_record() for result in results],
        "guards_installed_by_audit": installed_by_audit,
        "modules_scanned": list(package_modules()),
        "behavioural_checks": list(BEHAVIOURAL_CHECKS),
        "source_checks_advisory": list(SOURCE_CHECKS),
        "bounds": list(AUDIT_BOUNDS),
        # What it means is exactly what it checks: the committed source at this
        # head is the declared route, and the process refused the ungated
        # market-data read this audit attempted. It has never meant "nothing can
        # be read", and since the body landed it does not even mean "nothing is
        # read" — it means the reading is the one route that was declared.
        "declared_gate_sequence_matches_at_this_head": no_read,
        "scope": (
            "execution containment only — not a hostile-input audit, not mutation "
            "resistance, and not a substitute for the gate-6 source-contamination audit"
        ),
    }


def audit_report_path() -> Path:
    return scratch.scratch_root() / "track_a_containment_report.json"


__all__ = [
    "BEHAVIOURAL_CHECKS",
    "AUDIT_BOUNDS",
    "CHECKS",
    "SOURCE_CHECKS",
    "DECLARED_DERIVATION_ROUTE_MODULE",
    "DECLARED_READ_ROUTE_MODULE",
    "STATUS_BREACHED",
    "STATUS_CONTAINED",
    "CheckResult",
    "audit",
    "audit_report_path",
    "package_modules",
]
