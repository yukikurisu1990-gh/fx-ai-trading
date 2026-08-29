"""One test per defect the independent review round found.

Every case here is a defence that a green suite already reported as working
before three separated audit roles broke it. They are kept together so the
shapes stay visible: an attribute patch that only some callers see, an
`isinstance` where the type matters, a validated field that is never compared,
a check-then-act that two processes run at once, and a case-sensitive
comparison on a case-insensitive filesystem.
"""

from __future__ import annotations

import copy
import json
import os
import pickle
import socket
import sqlite3
from pathlib import Path

import pytest

from scripts.m15_track_a import (
    authorization,
    breadth,
    containment,
    identity,
    isolation,
    oos_budget,
    read_route,
    scratch,
    seen_ledger,
)


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


def _identity(code_sha: str = "a" * 40) -> identity.RunIdentity:
    return identity.RunIdentity(
        run_id="regression-run",
        code_sha=code_sha,
        calendar_semantics=identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        started_at_utc="2026-01-01T00:00:00Z",
    )


def _grant(**overrides: object) -> authorization.ReadGrant:
    fields: dict[str, object] = {
        "operation": authorization.OPERATION_HISTORICAL_READ,
        "span_start_utc": "2025-06-01",
        "span_end_utc": "2025-06-30",
        "pairs": ("EUR_USD",),
        "timeframe": "M1",
        "approved_head_sha": "a" * 40,
        "approver_record": "PR #452 recorded approval",
    }
    fields.update(overrides)
    return authorization.ReadGrant(**fields)  # type: ignore[arg-type]


def _require(grant: object, **overrides: object) -> object:
    kwargs: dict[str, object] = {
        "operation": authorization.OPERATION_HISTORICAL_READ,
        "span_start_utc": "2025-06-01",
        "span_end_utc": "2025-06-30",
        "pairs": ("EUR_USD",),
        "timeframe": "M1",
        "identity": _identity(),
    }
    kwargs.update(overrides)
    return authorization.require_authorization(grant, **kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Isolation — the install order, and the routes an attribute patch cannot see
# ---------------------------------------------------------------------------


def test_installing_the_database_guard_first_does_not_disable_the_network_guard() -> None:
    """The database guard used to create the shared state the network guard checked.

    ``install_database_guard()`` then ``install_all()`` left every socket
    primitive unpatched while ``is_installed()`` — the only precondition either
    route checks — answered True.
    """
    isolation.uninstall_all()
    original_connect = socket.socket.connect
    try:
        isolation.install_database_guard()
        isolation.install_all()
        assert isolation.is_installed()
        assert socket.socket.connect is not original_connect
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with pytest.raises(isolation.IsolationError):
                probe.connect(("203.0.113.1", 80))
        finally:
            probe.close()
    finally:
        isolation.uninstall_all()


def test_is_installed_requires_every_limb() -> None:
    """ "Something was patched" is not the question a read route needs answered."""
    isolation.uninstall_all()
    try:
        isolation.install_network_guard()
        assert not isolation.is_installed(), "a network-only install is not an installation"
        isolation.install_audit_hook()
        isolation.install_database_guard()
        assert not isolation.is_installed(), "the native-reader limb is not up yet"
        isolation.install_native_reader_guard()
        assert isolation.is_installed()
    finally:
        isolation.uninstall_all()


def test_a_tuple_subclass_cannot_show_the_guard_a_different_destination(
    guards: object,
) -> None:
    """``address[0]`` calls ``__getitem__``; CPython reads the raw slot."""

    class TwoFaced(tuple):  # noqa: SLOT001 - the point is the lying override
        def __getitem__(self, index: object) -> object:
            return "127.0.0.1"

    address = TwoFaced(("203.0.113.9", 80))
    assert address[0] == "127.0.0.1"
    assert tuple.__getitem__(address, 0) == "203.0.113.9"
    with pytest.raises(isolation.IsolationError):
        isolation._check_destination(address, how="connect to")


def test_launching_a_process_is_refused(guards: object) -> None:
    """A subprocess escapes network, database and write containment at once."""
    import subprocess

    with pytest.raises(isolation.IsolationError):
        subprocess.Popen(["cmd", "/c", "ver"])  # noqa: S603, S607


def test_a_file_backed_sqlite_connection_is_refused(guards: object, tmp_path: Path) -> None:
    """A raw driver never touches ``sqlalchemy.create_engine``."""
    with pytest.raises(isolation.IsolationError):
        sqlite3.connect(str(tmp_path / "somewhere.db"))


def test_in_memory_sqlite_is_still_permitted(guards: object) -> None:
    connection = sqlite3.connect(":memory:")
    connection.close()


def test_a_write_into_the_repository_outside_the_scratch_root_is_refused(
    guards: object,
) -> None:
    """``assert_writable`` is a predicate; the hook is what confines the process."""
    target = scratch.repo_root() / "docs" / "__never_created__.md"
    with pytest.raises(isolation.IsolationError), open(target, "w", encoding="utf-8"):  # noqa: PTH123
        pass
    assert not target.exists()


def test_build_caches_inside_the_repository_stay_writable(guards: object, tmp_path: Path) -> None:
    """Blocking ``__pycache__`` would break imports, and it carries no research meaning."""
    relative = scratch.repo_root() / "scripts" / "__pycache__" / "__probe__.tmp"
    # Only the guard's verdict is under test; nothing is created.
    isolation._check_open((str(relative), "w"))


def test_a_read_under_the_data_tree_is_refused_outside_the_gated_window(
    guards: object,
) -> None:
    """This is what makes "one read route" a property of the process."""
    target = scratch.repo_root() / "data" / "__does_not_exist__.jsonl"
    with pytest.raises(isolation.IsolationError), open(target, "rb"):  # noqa: PTH123
        pass


def test_the_gated_window_permits_the_read_it_exists_for(guards: object) -> None:
    target = scratch.repo_root() / "data" / "__does_not_exist__.jsonl"
    with (
        isolation.gated_read_window(),
        pytest.raises(FileNotFoundError),
        open(target, "rb"),  # noqa: PTH123
    ):
        pass
    assert not isolation.is_read_window_open()


def test_the_read_window_cannot_be_opened_while_disarmed() -> None:
    isolation.uninstall_all()
    with pytest.raises(isolation.IsolationError), isolation.gated_read_window():
        pass


# ---------------------------------------------------------------------------
# Authorization — six shapes of forged grant
# ---------------------------------------------------------------------------


def test_a_readgrant_subclass_is_refused() -> None:
    class Wider(authorization.ReadGrant):
        def __post_init__(self) -> None:
            pass

        def covers(self, **_kwargs: object) -> bool:
            return True

    forged = Wider(
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc="1970-01-01",
        span_end_utc="2099-12-31",
        pairs=("EUR_USD",),
        timeframe="M1",
        approved_head_sha="not-a-sha",
        approver_record="x",
    )
    with pytest.raises(authorization.AuthorizationError):
        _require(forged)


def test_a_grant_that_never_ran_post_init_is_refused() -> None:
    """``object.__new__`` skips ``__init__``, so construction checks never ran."""
    forged = object.__new__(authorization.ReadGrant)
    for field, value in (
        ("operation", authorization.OPERATION_HISTORICAL_READ),
        ("span_start_utc", "1970-01-01"),
        ("span_end_utc", "2099-12-31"),
        ("pairs", ("EUR_USD",)),
        ("timeframe", "M1"),
        ("approved_head_sha", None),
        ("approver_record", ""),
    ):
        object.__setattr__(forged, field, value)
    with pytest.raises(authorization.AuthorizationError):
        _require(forged)


def test_a_genuine_grant_widened_after_construction_is_refused() -> None:
    """The governance-relevant forgery: a real approval, silently broadened."""
    grant = _grant()
    object.__setattr__(grant, "span_start_utc", "1970-1-1")
    object.__setattr__(grant, "pairs", ("EUR_USD", "USD_JPY"))
    with pytest.raises(authorization.AuthorizationError):
        _require(grant, span_start_utc="2025-01-01")


@pytest.mark.parametrize("clone", [pickle.loads, copy.deepcopy], ids=["pickle", "deepcopy"])
def test_a_clone_of_a_widened_grant_is_refused(clone: object) -> None:
    grant = _grant()
    object.__setattr__(grant, "approved_head_sha", "nope")
    revived = clone(pickle.dumps(grant)) if clone is pickle.loads else clone(grant)  # type: ignore[operator]
    with pytest.raises(authorization.AuthorizationError):
        _require(revived)


def test_an_unpadded_request_date_cannot_read_as_inside_the_grant() -> None:
    """``"2025-1-15" < "2025-06-01"`` is False, and 15 January is outside June."""
    grant = _grant()
    with pytest.raises(authorization.AuthorizationMalformedError):
        _require(grant, span_start_utc="2025-1-15")


def test_the_approved_head_must_equal_the_run_head() -> None:
    grant = _grant(approved_head_sha="a" * 40)
    assert _require(grant, identity=_identity("a" * 40)) is grant
    with pytest.raises(authorization.AuthorizationError, match="head"):
        _require(grant, identity=_identity("c" * 40))


# ---------------------------------------------------------------------------
# The request object — the one place a lying pair was not pinned
# ---------------------------------------------------------------------------


class LyingPair(str):
    """Content ``XAU_USD``; hashes and compares as whatever it was told to claim."""

    def __new__(cls, real: str, claim: str) -> LyingPair:
        obj = super().__new__(cls, real)
        obj._claim = claim  # type: ignore[attr-defined]
        return obj

    def __hash__(self) -> int:
        return hash(self._claim)  # type: ignore[attr-defined]

    def __eq__(self, other: object) -> bool:
        return self._claim == other or str.__eq__(self, other)  # type: ignore[attr-defined]


def test_a_lying_pair_cannot_enter_a_read_request() -> None:
    with pytest.raises(read_route.ReadRouteError):
        read_route.ReadRequest(
            span_start_utc="2025-06-01",
            span_end_utc="2025-06-30",
            pairs=(LyingPair("XAU_USD", "EUR_USD"),),
            timeframe="M1",
            warmup_extension_start_utc="2025-06-01",
        )


def test_a_lying_pair_cannot_satisfy_a_seen_declaration() -> None:
    declaration = seen_ledger.SeenDeclaration(
        run_id="regression-run",
        span_start_utc="2025-06-01",
        span_end_utc="2025-06-30",
        pairs=("EUR_USD",),
        timeframe="M1",
        purpose="probe",
    )
    with pytest.raises(seen_ledger.SeenLedgerError):
        declaration.covers(
            span_start_utc="2025-06-01",
            span_end_utc="2025-06-30",
            pairs=(LyingPair("XAU_USD", "EUR_USD"),),
        )


@pytest.mark.parametrize("bad", ["2025-6-1", "01-06-2025", "2025-06-01T00:00:00Z", "yesterday"])
def test_a_request_date_that_is_not_a_padded_iso_date_is_refused(bad: str) -> None:
    with pytest.raises(read_route.ReadRouteError):
        read_route.ReadRequest(
            span_start_utc=bad,
            span_end_utc="2025-06-30",
            pairs=("EUR_USD",),
            timeframe="M1",
            warmup_extension_start_utc="2025-06-01",
        )


def test_a_warmup_that_narrows_the_touched_interval_is_still_refused() -> None:
    with pytest.raises(read_route.ReadRouteError):
        read_route.ReadRequest(
            span_start_utc="2025-01-05",
            span_end_utc="2025-06-30",
            pairs=("EUR_USD",),
            timeframe="M1",
            warmup_extension_start_utc="2025-02-01",
        )


# ---------------------------------------------------------------------------
# The ledgers
# ---------------------------------------------------------------------------


def test_reserved_artifact_names_refuse_whatever_the_caller_typed(scratch_at: Path) -> None:
    """NTFS treats these as one file; a case-sensitive set refuses one spelling of it."""
    for spelling in ("scrub_report.json", "SCRUB_REPORT.JSON", "Scrub_Report.Json"):
        with pytest.raises(scratch.ScratchRootError):
            scratch.assert_writable(scratch_at / spelling)


def test_a_ledger_may_not_be_truncated(guards: object, scratch_at: Path) -> None:
    """An append-only API binds only its own callers; the hook binds the process."""
    path = scratch_at / "exploratory_seen_ledger.jsonl"
    scratch.append_line(path, '{"probe": 1}')
    with pytest.raises(isolation.IsolationError):
        path.write_text("", encoding="utf-8")
    assert path.read_text(encoding="utf-8").strip() == '{"probe": 1}'


def test_the_grant_a_route_ran_under_is_recorded(scratch_at: Path) -> None:
    path = seen_ledger.record_grant(_grant(), _identity(), route="probe-route")
    entry = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["grant"]["approver_record"] == "PR #452 recorded approval"
    assert entry["route"] == "probe-route"


def test_the_oos_budget_is_claimed_atomically_and_only_once(scratch_at: Path) -> None:
    observation = oos_budget.SliceObservation(
        run_id="regression-run",
        slice_start_utc="2026-01-01",
        slice_end_utc="2026-01-31",
        purpose="probe",
    )
    oos_budget.consume(observation, _identity())
    assert oos_budget.claim_path(1).exists(), "the claim file is what the OS arbitrated"
    assert oos_budget.observations_spent() == oos_budget.OOS_BUDGET_N
    with pytest.raises(oos_budget.OosBudgetError):
        oos_budget.consume(observation, _identity())


def test_a_claim_left_by_a_crashed_run_still_spends_the_budget(scratch_at: Path) -> None:
    """The claim lands before the ledger line, so a crash between them spends it."""
    os.close(os.open(oos_budget.claim_path(1), os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    assert oos_budget.observations_spent() == 1
    with pytest.raises(oos_budget.OosBudgetError):
        oos_budget.assert_budget_available()


def test_a_configuration_entrys_axes_cannot_be_changed_after_validation() -> None:
    entry = breadth.ConfigurationEntry(
        run_id="regression-run",
        axes=dict.fromkeys(breadth.CONFIGURATION_AXES, "v1"),
        result_observed=True,
        note="probe",
    )
    before = entry.configuration_key
    with pytest.raises(TypeError):
        entry.axes["model"] = "v2"  # type: ignore[index]
    assert entry.configuration_key == before


def test_a_ledger_line_whose_result_flag_is_not_a_bool_is_refused(scratch_at: Path) -> None:
    """The writer pinned the type and the reader coerced it, so ``0`` became ``False``."""
    payload = {
        "entry": {
            "run_id": "regression-run",
            "axes": dict.fromkeys(breadth.CONFIGURATION_AXES, "v1"),
            "result_observed": 0,
            "note": "probe",
            "classification": breadth.BREADTH_CLASSIFICATION,
        },
        "identity": _identity().as_record(),
    }
    scratch.append_line(
        breadth.breadth_path(), json.dumps(payload, sort_keys=True, separators=(",", ":"))
    )
    with pytest.raises(breadth.BreadthRecordError):
        breadth.read_entries()


# ---------------------------------------------------------------------------
# The containment audit
# ---------------------------------------------------------------------------


def test_the_audit_scans_every_module_on_disk() -> None:
    """A hand-maintained roster is scanned only if someone remembers to extend it."""
    on_disk = {
        f"scripts.m15_track_a.{path.stem}"
        for path in Path(containment.__file__).resolve().parent.glob("*.py")
        if path.stem != "__init__"
    }
    on_disk.add("scripts.m15_track_a")
    assert set(containment.package_modules()) == on_disk


def test_the_audit_measures_rather_than_asserts_that_nothing_is_read() -> None:
    report = containment.audit()
    body_absent = next(c for c in report["checks"] if c["check"] == "read_body_absent")
    assert body_absent["passed"] is True
    assert report["no_market_data_read"] is body_absent["passed"]


def test_the_audit_probes_behaviour_not_only_source() -> None:
    """Four of the twelve checks attempt the forbidden thing and require a refusal."""
    names = {check.__name__ for check in containment.CHECKS}
    assert {
        "_check_write_containment_enforced",
        "_check_market_data_read_refused",
        "_check_subprocess",
        "_check_read_route_refuses_without_a_grant",
    } <= names
