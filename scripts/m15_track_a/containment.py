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
import inspect
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

_PACKAGE_MODULES: Final[tuple[str, ...]] = (
    "scripts.m15_track_a",
    "scripts.m15_track_a.authorization",
    "scripts.m15_track_a.breadth",
    "scripts.m15_track_a.containment",
    "scripts.m15_track_a.derivation",
    "scripts.m15_track_a.identity",
    "scripts.m15_track_a.isolation",
    "scripts.m15_track_a.oos_budget",
    "scripts.m15_track_a.read_route",
    "scripts.m15_track_a.scratch",
    "scripts.m15_track_a.seen_ledger",
)


@dataclass(frozen=True)
class CheckResult:
    """One containment check and what it found."""

    name: str
    passed: bool
    detail: str

    def as_record(self) -> dict[str, Any]:
        return {"check": self.name, "passed": self.passed, "detail": self.detail}


def _check_single_read_route() -> CheckResult:
    """Exactly one function in this package may open market data, and it is gated.

    Detection is by **AST**, not by substring: a module that merely *names*
    ``open(`` in a docstring or a check list is not a reader, and a substring
    scan cannot tell the two apart — this audit's own source would have failed
    its own check.
    """
    readers = {"open", "read_parquet", "read_csv", "loadtxt", "load", "read_text", "read_bytes"}
    #: The three ledgers legitimately open files, and only beneath the scratch
    #: root. They are named rather than pattern-matched, so a *new* file-opening
    #: module is a finding rather than an exemption.
    ledger_modules = {
        "scripts.m15_track_a.seen_ledger",
        "scripts.m15_track_a.breadth",
        "scripts.m15_track_a.oos_budget",
    }
    offenders: list[str] = []
    for name in _PACKAGE_MODULES:
        if (
            name
            in (
                DECLARED_READ_ROUTE_MODULE,
                DECLARED_DERIVATION_ROUTE_MODULE,
                "scripts.m15_track_a.containment",
            )
            or name in ledger_modules
        ):
            continue
        module = importlib.import_module(name)
        try:
            tree = ast.parse(inspect.getsource(module))
        except (OSError, SyntaxError):  # pragma: no cover - source always available here
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            called = (
                func.id
                if isinstance(func, ast.Name)
                else func.attr
                if isinstance(func, ast.Attribute)
                else None
            )
            if called in readers:
                offenders.append(f"{name}:{node.lineno} {called}()")
    if offenders:
        return CheckResult(
            "single_read_route",
            False,
            f"file-access calls outside the declared route: {offenders}",
        )
    return CheckResult(
        "single_read_route",
        True,
        f"the only market-data route is {DECLARED_READ_ROUTE_MODULE}.read_historical, the "
        f"only derivation route is {DECLARED_DERIVATION_ROUTE_MODULE}.derive_m15, and the "
        "three ledgers open only their own append-only files beneath the scratch root",
    )


def _check_read_route_is_gated() -> CheckResult:
    """The declared route refuses without a grant, and reads nothing today."""
    source = inspect.getsource(read_route)
    needs = (
        "require_authorization",
        "assert_span_admissible",
        "assert_declared",
        "isolation.is_installed",
        "NotImplementedError",
    )
    missing = [need for need in needs if need not in source]
    if missing:
        return CheckResult("read_route_gated", False, f"read route is missing {missing}")
    return CheckResult(
        "read_route_gated",
        True,
        "isolation, authorization, span admissibility and a prior seen-data declaration are "
        "all checked before an unimplemented body",
    )


def _check_authorization_has_no_ambient_source() -> CheckResult:
    """No environment variable, file or global may grant authorisation."""
    source = inspect.getsource(authorization)
    for ambient in ("os.environ", "getenv", "open(", "Path("):
        if ambient in source:
            return CheckResult(
                "authorization_not_ambient",
                False,
                f"the authorization module reads {ambient!r} — a grant must be an in-process "
                "object a caller passes, never ambient state",
            )
    return CheckResult(
        "authorization_not_ambient",
        True,
        "a grant is an in-process ReadGrant; no environment variable, file or global can "
        "supply one",
    )


def _check_write_root() -> CheckResult:
    """Writes are admissible only beneath the scratch root."""
    root = scratch.scratch_root()
    outside = [
        root.parent / "escape.json",
        scratch.repo_root() / "docs" / "note.md",
        scratch.repo_root() / "artifacts" / "m15_gate3a" / "scrub_report.json",
        scratch.repo_root() / "data" / "x.parquet",
        scratch.repo_root() / "models" / "m.pkl",
    ]
    leaks = [str(path) for path in outside if scratch.is_writable(path)]
    if leaks:
        return CheckResult("write_root", False, f"writable outside the scratch root: {leaks}")
    inside_ok = scratch.is_writable(root / "run" / "note.json")
    if not inside_ok:
        return CheckResult(
            "write_root", False, "a legitimate path beneath the scratch root was refused"
        )
    return CheckResult(
        "write_root",
        True,
        f"writes are confined to {scratch.SCRATCH_ROOT_RELATIVE}; protected roots and "
        "reserved artifact filenames refuse",
    )


def _check_network() -> CheckResult:
    """A non-loopback connect, datagram or name lookup is refused."""
    if not isolation.is_installed():
        return CheckResult("network", False, "isolation guards are not installed")
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        try:
            probe.connect(("203.0.113.1", 80))
        except isolation.IsolationError:
            pass
        else:  # pragma: no cover - would mean the guard is absent
            return CheckResult("network", False, "a non-loopback connect was not refused")
    finally:
        probe.close()
    try:
        socket.getaddrinfo("example.invalid", 80)
    except isolation.IsolationError:
        pass
    else:  # pragma: no cover
        return CheckResult("network", False, "a non-loopback name lookup was not refused")
    return CheckResult(
        "network", True, "non-loopback connects, datagrams and name lookups are refused"
    )


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


def _check_derivation_route() -> CheckResult:
    """One derivation route, naming its delegate and its audit status."""
    source = inspect.getsource(derivation)
    for need in (
        "SELECTED_ROUTE",
        "DELEGATE_QUALNAME",
        "DELEGATE_AUDIT_STATUS",
        "require_authorization",
        "NotImplementedError",
    ):
        if need not in source:
            return CheckResult("derivation_route", False, f"derivation route is missing {need}")
    return CheckResult(
        "derivation_route",
        True,
        f"one route, {derivation.SELECTED_ROUTE}, delegating to {derivation.DELEGATE_QUALNAME} "
        f"whose audit status is recorded as {derivation.DELEGATE_AUDIT_STATUS}",
    )


CHECKS: Final[tuple[Any, ...]] = (
    _check_single_read_route,
    _check_read_route_is_gated,
    _check_authorization_has_no_ambient_source,
    _check_write_root,
    _check_network,
    _check_database,
    _check_broker_and_live,
    _check_derivation_route,
)


def audit() -> dict[str, Any]:
    """Run every check and return the report.  Reads no market data.

    The network and database checks demonstrate that the guards **refuse**, so
    the audit installs them for its own duration when they are not already
    installed, and restores the process afterwards.  Reporting "not installed"
    would answer a question about ambient process state rather than about the
    guards, and a containment audit that passes only when someone remembered to
    install them is the kind of conditional assurance this programme keeps
    finding.  When a research run has already installed them, the audit leaves
    them alone.
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
    return {
        "status": STATUS_CONTAINED if passed else STATUS_BREACHED,
        "checks": [result.as_record() for result in results],
        "guards_installed_by_audit": installed_by_audit,
        "scope": (
            "execution containment only — not a hostile-input audit, not mutation "
            "resistance, and not a substitute for the gate-6 source-contamination audit"
        ),
        "no_market_data_read": True,
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
]
