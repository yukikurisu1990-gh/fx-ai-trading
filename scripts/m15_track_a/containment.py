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

1. **Behavioural probes** come first and carry the verdict. They arm the guards
   and then actually attempt the forbidden thing — a write into ``docs/``, a
   read under ``data/``, a remote engine, a subprocess — and require a refusal.
   A probe cannot be satisfied by a comment.
2. **Structural checks** come second and are advisory in exactly the way a
   source scan has to be. Their roster is **enumerated from the directory**, so
   a new module is scanned by existing.

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
STATUS_CONTAINED: Final[str] = "TRACK_A_EXECUTION_CONTAINMENT_VERIFIED_NO_UNGATED_ROUTE"
STATUS_BREACHED: Final[str] = "TRACK_A_EXECUTION_CONTAINMENT_BREACHED_UNGATED_ROUTE_FOUND"

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
}

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
# Behavioural probes — these carry the verdict
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


def _check_read_body_is_absent() -> CheckResult:
    """The route's own body, at source: no return, and it ends in a raise.

    **This is a source-level statement about this head, not a behavioural
    probe** — and an earlier drafting's docstring claimed it was "measured by
    driving the route to the end of its gate sequence", which it never did.
    Driving the route for real would need a grant and a ledger declaration, and
    would have this audit write to a governance record; so the honest scope is
    stated instead of overclaimed, and ``no_market_data_read`` is no longer
    licensed by this check alone (see :func:`audit`).

    Two conditions, both necessary: the function contains **no ``return``**, and
    its final statement **is** ``raise NotImplementedError(...)``.
    """
    tree = ast.parse(Path(read_route.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "read_historical":
            if any(isinstance(child, ast.Return) for child in ast.walk(node)):
                return CheckResult(  # pragma: no cover - true once a body is supplied
                    "read_body_absent",
                    False,
                    "read_historical returns a value — it has a body, and this audit no "
                    "longer establishes that nothing is read",
                )
            if _terminal_raise_is_not_implemented(node.body):
                return CheckResult(
                    "read_body_absent",
                    True,
                    "read_historical returns nothing and its last statement is "
                    "raise NotImplementedError; no read is implemented at this head",
                )
            return CheckResult(  # pragma: no cover
                "read_body_absent",
                False,
                "read_historical does not end in raise NotImplementedError",
            )
    return CheckResult("read_body_absent", False, "read_historical not found")  # pragma: no cover


# ---------------------------------------------------------------------------
# Structural checks — advisory, and labelled as such
# ---------------------------------------------------------------------------


def _check_single_read_route() -> CheckResult:
    """No module outside the declared openers contains a file-opening call.

    Advisory. A name set cannot be complete, and an alias defeats it; the
    behavioural probes above are what establish containment.
    """
    findings: list[str] = []
    for module_name in package_modules():
        if module_name in _PERMITTED_FILE_OPENERS:
            continue
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
            if name in _READER_NAMES:
                findings.append(f"{module_name}:{node.lineno} {name}()")
        for node in ast.walk(tree):
            # ``_reader = builtins.open`` then ``_reader(path)`` — the call site
            # carries a name the sweep has never heard of, so the *binding* is
            # what has to be caught. Still not completeness; see the docstring.
            if isinstance(node, ast.Assign):
                value = node.value
                bound = getattr(value, "id", None) or getattr(value, "attr", None)
                if bound in _READER_NAMES:
                    findings.append(f"{module_name}:{node.lineno} aliases {bound}")
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


CHECKS: Final[tuple[Any, ...]] = (
    _check_write_containment_enforced,
    _check_market_data_read_refused,
    _check_network,
    _check_subprocess,
    _check_database,
    _check_broker_and_live,
    _check_read_route_refuses_without_a_grant,
    _check_read_body_is_absent,
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
    # Two conditions, deliberately: the route has no body at this head **and**
    # the process actually refused a market-data read. Either alone has been
    # defeated in review — the source check by a dead-code decoy, and a
    # behavioural probe cannot see a body that was never called.
    no_read = bool(by_name.get("read_body_absent") and by_name.get("market_data_read_refused"))
    return {
        "status": STATUS_CONTAINED if passed else STATUS_BREACHED,
        "checks": [result.as_record() for result in results],
        "guards_installed_by_audit": installed_by_audit,
        "modules_scanned": list(package_modules()),
        # Derived, not asserted: True only when the route has no body at this
        # head AND the process refused a market-data read during this audit.
        "no_market_data_read": no_read,
        "scope": (
            "execution containment only — not a hostile-input audit, not mutation "
            "resistance, and not a substitute for the gate-6 source-contamination audit"
        ),
    }


def audit_report_path() -> Path:
    return scratch.scratch_root() / "track_a_containment_report.json"


__all__ = [
    "CHECKS",
    "DECLARED_DERIVATION_ROUTE_MODULE",
    "DECLARED_READ_ROUTE_MODULE",
    "STATUS_BREACHED",
    "STATUS_CONTAINED",
    "CheckResult",
    "audit",
    "audit_report_path",
    "package_modules",
]
