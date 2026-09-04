"""The two grants issued on the preflight-binding implementation — and valid.

**No test here touches real market data.** Every case reads this repository's
own `.py` sources — which is what the fingerprint is taken over — the grant
document, or synthetic bytes in a temporary tree.

Four grant records now exist and the suite asserts a different thing about each,
deliberately:

* `test_recorded_read_grant.py` — PR #454's grant, bound to `497e187b…`, **invalid**
* `test_recorded_dual_grants.py` — PR #456's pair, bound to `e43583e0…`, **invalid**
* `test_reissued_dual_grants.py` — PR #458's pair, bound to `64fbace9…`, **invalid**
* this file — PR #462's pair, bound to `e147542a…`, **valid at this head**

This is the first record whose assertions run in the positive direction, and
that is the whole difference: the three before it assert a refusal, this one
asserts that `require_authorization` **accepts** what the document records. If a
later change moves the fingerprint, these tests fail — which is the mechanism
working, not a flake, and the response is to re-issue rather than to relax the
test.

**Nothing here authorises a read.** These are assertions about a record. The
execution command is a separate human act, and no test can stand in for it.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_track_a import authorization, containment, identity, oos_slice

GRANT_DOCUMENT = (
    Path(containment.__file__).resolve().parents[2]
    / "docs"
    / "governance"
    / "m15_track_a_r1_dual_grants_final_preflight.md"
)

#: The head PR #461 merged as, which both grants name.
APPROVED_HEAD = "0bb987e775658db3532affdc3992cad94382faa3"

REQUIRED_FIELDS = frozenset(
    {
        "operation",
        "span_start_utc",
        "span_end_utc",
        "pairs",
        "pairs_explicit",
        "timeframe",
        "approved_head_sha",
        "approved_implementation_fingerprint",
        "approver_record",
    }
)

#: Parsed by section, never by a whole-file scan: two grants in one document
#: would otherwise merge silently, and the merge would look like a single
#: well-formed grant.
SECTIONS = {
    "read": "## 2. Grant A — the historical development read",
    "derivation": "## 3. Grant B — the M15 research derivation",
}

OPERATIONS = {
    "read": authorization.OPERATION_HISTORICAL_READ,
    "derivation": authorization.OPERATION_M15_DERIVATION,
}


def _section(name: str) -> str:
    text = GRANT_DOCUMENT.read_text(encoding="utf-8")
    heading = SECTIONS[name]
    assert text.count(heading) == 1, f"{heading!r} does not appear exactly once"
    body = text.split(heading, 1)[1]
    return re.split(r"^## ", body, maxsplit=1, flags=re.MULTILINE)[0]


def _recorded(name: str) -> dict[str, str]:
    """One grant's table, parsed from its own section.

    Deliberately not imported from a Python constant: a `.py` file holding the
    grant would be **inside the fingerprint surface**, so recording the grant
    would change the value the grant records.
    """
    rows: dict[str, str] = {}
    for field, value in re.findall(r"^\| \*\*(\w+)\*\* \| (.+?) \|$", _section(name), re.MULTILINE):
        assert field not in rows, f"the {name} table names {field} twice"
        rows[field] = value.strip().strip("`")
    missing = REQUIRED_FIELDS - set(rows)
    assert not missing, (
        f"the {name} grant's table did not yield {sorted(missing)}. Either a field was removed "
        "from the record or the table's formatting changed; both need a human to look, which is "
        "why this refuses rather than testing whatever it did parse."
    )
    return rows


def _recorded_pairs(name: str) -> tuple[str, ...]:
    """The pairs from the document, spelled out.

    The prose cell (``the registered `PAIRS_20`, all twenty``) is not machine
    readable, so an earlier draft built the grant from the **constant** and only
    checked the cell for the words "PAIRS_20" and "twenty". A review role
    narrowed the cell to "… except USD_JPY" and every test stayed green: the
    grant a reader would construct and the grant the tests exercised were
    different objects. The `pairs_explicit` row is what is parsed now.
    """
    cell = _recorded(name)["pairs_explicit"]
    pairs = tuple(cell.replace("`", "").split())
    assert pairs == tuple(sorted(pairs)), "the recorded pairs are not in canonical order"
    return pairs


def _grant(name: str) -> authorization.ReadGrant:
    recorded = _recorded(name)
    return authorization.ReadGrant(
        operation=recorded["operation"],
        span_start_utc=recorded["span_start_utc"],
        span_end_utc=recorded["span_end_utc"],
        pairs=_recorded_pairs(name),
        timeframe=recorded["timeframe"],
        approved_head_sha=recorded["approved_head_sha"],
        approved_implementation_fingerprint=recorded["approved_implementation_fingerprint"],
        approver_record=recorded["approver_record"],
    )


def _identity(name: str) -> identity.RunIdentity:
    return identity.RunIdentity(
        run_id=f"final-preflight-{name}-grant-check",
        code_sha=_recorded(name)["approved_head_sha"],
        calendar_semantics=identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        started_at_utc="2026-09-04T00:00:00Z",
    )


def _authorise(name: str, **overrides: object) -> authorization.ReadGrant:
    request: dict[str, object] = {
        "operation": OPERATIONS[name],
        "span_start_utc": oos_slice.DEVELOPMENT_START_UTC,
        "span_end_utc": oos_slice.DEVELOPMENT_END_UTC,
        "pairs": tuple(sorted(PAIRS_20)),
        "timeframe": "M1",
        "identity": _identity(name),
    }
    request.update(overrides)
    return authorization.require_authorization(_grant(name), **request)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# the record is this implementation's, and it is accepted
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_recorded_grant_names_the_measured_implementation(name: str) -> None:
    """The number in the document is the number the tree hashes to.

    Not "a plausible sha256" and not "the number the last document had": the
    grant is checked against a measurement, so the record has to be one too.
    """
    recorded = _recorded(name)["approved_implementation_fingerprint"]
    assert recorded == containment.implementation_fingerprint(), (
        "the recorded fingerprint is not this tree's. Either the implementation moved after the "
        "grants were written — in which case both are void and need re-issuing — or the record "
        "was copied from an earlier one."
    )
    assert len(containment.implementation_surface()) == 32


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_recorded_grant_is_accepted_at_this_head(name: str) -> None:
    """The positive assertion the three earlier records could not make.

    `require_authorization` measures the tree itself. A grant that parses, names
    the right scope and still gets refused is what the last three records were;
    this one has to be accepted, and being accepted is what "15 of 15" rests on.
    """
    assert _authorise(name) is not None


def test_the_two_grants_are_accepted_through_a_verified_run_context() -> None:
    """And accepted on the route that will actually run them.

    `run_r1` builds one `VerifiedRunContext` in preflight and every window reuses
    it. A grant accepted by the direct call and refused through the context would
    be a grant that authorises nothing on the formal route.
    """
    read_grant = _grant("read")
    derivation_grant = _grant("derivation")
    run = _identity("read")
    context = authorization.VerifiedRunContext(
        read_grant=read_grant,
        derivation_grant=derivation_grant,
        identity=run,
    )
    assert context.fingerprint == containment.implementation_fingerprint()
    assert context.approved_head_sha == APPROVED_HEAD
    for name, grant in (("read", read_grant), ("derivation", derivation_grant)):
        assert (
            authorization.require_authorization(
                grant,
                operation=OPERATIONS[name],
                span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
                span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
                pairs=tuple(sorted(PAIRS_20)),
                timeframe="M1",
                identity=run,
                context=context,
            )
            is grant
        )


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_recorded_head_is_the_pr_461_merge(name: str) -> None:
    assert _recorded(name)["approved_head_sha"] == APPROVED_HEAD


def test_the_two_grants_name_the_two_operations() -> None:
    assert _recorded("read")["operation"] == authorization.OPERATION_HISTORICAL_READ
    assert _recorded("derivation")["operation"] == authorization.OPERATION_M15_DERIVATION


# --------------------------------------------------------------------------
# the scope is the ruled scope
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_recorded_span_is_exactly_the_development_window(name: str) -> None:
    """Taken from the committed constants, not restated from the document.

    The 20% OOS slice is derived from the committed DESIGN dates, so the
    development window's two ends are facts about `oos_slice`, and a grant that
    named one day more would reach into the quarantine.
    """
    recorded = _recorded(name)
    assert recorded["span_start_utc"] == oos_slice.DEVELOPMENT_START_UTC == "2025-04-25"
    assert recorded["span_end_utc"] == oos_slice.DEVELOPMENT_END_UTC == "2025-12-28"
    assert oos_slice.SLICE_START_UTC == "2025-12-29"
    assert oos_slice.SLICE_END_UTC == "2026-02-28"


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_recorded_timeframe_is_the_source_timeframe(name: str) -> None:
    from scripts.m15_track_a import read_route

    assert _recorded(name)["timeframe"] == read_route.SOURCE_TIMEFRAME == "M1"


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_pairs_cell_names_the_registered_universe(name: str) -> None:
    #: **Exact**, not "contains". A review role narrowed the prose to
    #: "… all twenty (§3a) except USD_JPY" and everything stayed green: the
    #: machine-readable row below was still complete, so the document said one
    #: thing to a parser and another to the human who has to approve it. A
    #: substring check cannot catch a qualifier appended to the end.
    cell = _recorded(name)["pairs"]
    assert cell == "the registered `PAIRS_20`, all twenty (§3a)", cell
    assert len(PAIRS_20) == 20
    #: and the machine-readable row is the universe itself, exactly — set
    #: equality, so a dropped pair and an added one both fail
    assert set(_recorded_pairs(name)) == set(PAIRS_20)
    assert len(_recorded_pairs(name)) == 20


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_a_narrowed_pairs_row_would_not_cover_the_planned_universe(name: str) -> None:
    """The grant the document describes has to be the grant that gets checked.

    Dropping one pair from the record must stop the recorded grant covering the
    planned twenty — otherwise the record and the authorisation have come apart.
    """
    narrowed = tuple(pair for pair in _recorded_pairs(name) if pair != "USD_JPY")
    assert len(narrowed) == 19
    grant = _grant(name)
    assert not authorization.grant_covers(
        authorization.ReadGrant(
            operation=grant.operation,
            span_start_utc=grant.span_start_utc,
            span_end_utc=grant.span_end_utc,
            pairs=narrowed,
            timeframe=grant.timeframe,
            approved_head_sha=grant.approved_head_sha,
            approved_implementation_fingerprint=grant.approved_implementation_fingerprint,
            approver_record=grant.approver_record,
        ),
        operation=grant.operation,
        span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
        span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
        pairs=tuple(sorted(PAIRS_20)),
        timeframe="M1",
    )


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_recorded_approver_record_names_an_external_identifier(name: str) -> None:
    record = _recorded(name)["approver_record"]
    assert "PR #462" in record, record
    assert GRANT_DOCUMENT.name in record, record


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_code_block_matches_the_table(name: str) -> None:
    """A reader who copies the snippet must get the grant the table records."""
    block = _section(name)
    recorded = _recorded(name)
    for field in ("span_start_utc", "span_end_utc", "timeframe", "approved_head_sha"):
        assert f'{field}="{recorded[field]}"' in block, field
    assert f'"{recorded["approved_implementation_fingerprint"]}"' in block
    assert "tuple(sorted(PAIRS_20))" in block


# --------------------------------------------------------------------------
# what neither grant reaches
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SECTIONS))
@pytest.mark.parametrize(
    "start,end",
    [
        ("2025-12-29", "2026-02-28"),  # EXPLORATORY_OOS_SLICE
        ("2026-03-01", "2026-04-24"),  # dead window
        ("2026-04-25", "2026-05-31"),  # forward epoch
        ("2026-06-01", "2026-12-31"),  # future data
        ("2024-01-01", "2025-04-24"),  # pre-DESIGN
        ("2025-04-25", "2025-12-29"),  # one day past the ceiling
        ("2025-04-24", "2025-12-28"),  # one day before the floor
    ],
)
def test_neither_grant_covers_what_section_5_excludes(name: str, start: str, end: str) -> None:
    with pytest.raises(authorization.AuthorizationError):
        _authorise(name, span_start_utc=start, span_end_utc=end)


@pytest.mark.parametrize("name", sorted(SECTIONS))
@pytest.mark.parametrize("pair", ["XXX_YYY", "USD_XXX", "BTC_USD"])
def test_neither_grant_covers_an_unregistered_pair(name: str, pair: str) -> None:
    with pytest.raises(authorization.AuthorizationError):
        _authorise(name, pairs=(*sorted(PAIRS_20), pair))


@pytest.mark.parametrize("name", sorted(SECTIONS))
@pytest.mark.parametrize("timeframe", ["M5", "M15", "H1", "D", "m1"])
def test_neither_grant_covers_another_timeframe(name: str, timeframe: str) -> None:
    with pytest.raises(authorization.AuthorizationError):
        _authorise(name, timeframe=timeframe)


def test_neither_grant_covers_the_other_operation() -> None:
    """Policy §2.5: a read grant does not authorise a derivation."""
    with pytest.raises(authorization.AuthorizationError):
        _authorise("read", operation=authorization.OPERATION_M15_DERIVATION)
    with pytest.raises(authorization.AuthorizationError):
        _authorise("derivation", operation=authorization.OPERATION_HISTORICAL_READ)


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_neither_grant_covers_the_oos_slice_operation(name: str) -> None:
    with pytest.raises(authorization.AuthorizationError):
        _authorise(
            name,
            operation=authorization.OPERATION_OOS_SLICE_READ,
            span_start_utc=oos_slice.SLICE_START_UTC,
            span_end_utc=oos_slice.SLICE_END_UTC,
        )


def test_a_read_grant_cannot_even_be_constructed_over_the_slice() -> None:
    """The ceiling is on the grant object, where no request can reach it."""
    with pytest.raises(authorization.AuthorizationMalformedError):
        authorization.ReadGrant(
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
            span_end_utc=oos_slice.SLICE_END_UTC,
            pairs=tuple(sorted(PAIRS_20)),
            timeframe="M1",
            approved_head_sha=APPROVED_HEAD,
            approved_implementation_fingerprint=containment.implementation_fingerprint(),
            approver_record="a grant reaching the quarantine",
        )


def test_the_three_superseded_records_are_still_refused() -> None:
    """Re-issuing does not revive what came before it.

    Each earlier document is left exactly as a human approved it, and each is
    still refused by the gate. A record that is kept but silently starts working
    again is the failure mode this checks for.
    """
    #: Read out of the three records rather than restated here. A hand-copied
    #: constant is how this test would end up asserting a refusal of a value no
    #: document contains — which is a passing test about nothing.
    governance = GRANT_DOCUMENT.parent
    superseded: dict[str, str] = {}
    for filename, where in (
        ("m15_track_a_r1_read_grant.md", "PR #454"),
        ("m15_track_a_r1_dual_grants.md", "PR #456"),
        ("m15_track_a_r1_dual_grants_reissued.md", "PR #458"),
    ):
        text = (governance / filename).read_text(encoding="utf-8")
        found = re.findall(
            r"^\| \*\*approved_implementation_fingerprint\*\* \| `([0-9a-f]{64})` \|$",
            text,
            re.MULTILINE,
        )
        assert found, f"{filename} records no grant fingerprint any more"
        for value in set(found):
            superseded[value] = where
    assert len(superseded) == 3, superseded

    current = containment.implementation_fingerprint()
    for fingerprint, where in superseded.items():
        assert fingerprint != current, f"{where}'s fingerprint is this tree's"
        grant = authorization.ReadGrant(
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
            span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
            pairs=tuple(sorted(PAIRS_20)),
            timeframe="M1",
            approved_head_sha=APPROVED_HEAD,
            approved_implementation_fingerprint=fingerprint,
            approver_record=f"{where}, superseded",
        )
        with pytest.raises(authorization.AuthorizationError, match="changed after the approval"):
            authorization.require_authorization(
                grant,
                operation=authorization.OPERATION_HISTORICAL_READ,
                span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
                span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
                pairs=tuple(sorted(PAIRS_20)),
                timeframe="M1",
                identity=_identity("read"),
            )


# --------------------------------------------------------------------------
# recording a grant does not change what the grant records
# --------------------------------------------------------------------------


def test_the_repository_instructions_name_the_grants_in_force() -> None:
    """`CLAUDE.md` is read first by every session, so a stale claim there costs most.

    A review role rewrote it to say the superseded `64fbace9…` pair was in force
    and the whole suite stayed green. The fingerprint and the head it names are
    checked here against the record and the measurement.
    """
    instructions = (Path(containment.__file__).resolve().parents[2] / "CLAUDE.md").read_text(
        encoding="utf-8"
    )
    current = containment.implementation_fingerprint()
    assert current[:8] in instructions, (
        "CLAUDE.md does not name the fingerprint the grants in force are bound to"
    )
    assert APPROVED_HEAD[:8] in instructions, "CLAUDE.md does not name the approved head"
    assert GRANT_DOCUMENT.name in instructions, "CLAUDE.md does not point at the record in force"
    for superseded in ("497e187b", "e43583e0", "64fbace9", "1f1f0ed5", "c1e71fd3"):
        assert f"`{superseded}…`" in instructions, (
            f"CLAUDE.md stopped recording {superseded}… as superseded"
        )


def test_the_grant_document_is_outside_the_fingerprint_surface() -> None:
    surface = {path.name for path in containment.implementation_surface()}
    assert GRANT_DOCUMENT.name not in surface
    assert not any(path.suffix != ".py" for path in containment.implementation_surface())


@pytest.fixture
def replica(tmp_path: Path) -> Path:
    """A working copy of the repository, so nothing here edits the real tree."""
    root = Path(containment.__file__).resolve().parents[2]
    target = tmp_path / "repo"
    target.mkdir()
    for name in ("scripts", "src", "docs", "tests"):
        source = root / name
        if source.is_dir():
            shutil.copytree(source, target / name, ignore=shutil.ignore_patterns("__pycache__"))
    return target


def _fingerprint_in(root: Path) -> str:
    result = subprocess.run(  # noqa: S603 - a fixed argv into a temp replica
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, '.');"
            "from scripts.m15_track_a import containment;"
            "print(containment.implementation_fingerprint())",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_recording_a_governance_document_does_not_move_the_fingerprint(replica: Path) -> None:
    """Measured, not argued.

    This PR is authorization-only, and "authorization-only" is only meaningful
    if writing the authorisation cannot invalidate it. So: measure, write a
    governance document and a test, measure again.
    """
    before = _fingerprint_in(replica)
    assert before == containment.implementation_fingerprint()
    (replica / "docs" / "governance" / "a_new_authorisation_record.md").write_text(
        "# a governance record\n\nApproved by a human.\n", encoding="utf-8"
    )
    (replica / "tests" / "m15_track_a" / "test_a_new_assertion.py").write_text(
        "def test_nothing() -> None:\n    assert True\n", encoding="utf-8"
    )
    assert _fingerprint_in(replica) == before


def test_a_substantive_source_change_voids_both_grants(replica: Path) -> None:
    """The other direction, and the one that matters more."""
    before = _fingerprint_in(replica)
    target = replica / "scripts" / "m15_track_a" / "row_scope.py"
    target.write_text(target.read_text(encoding="utf-8") + "\n# a change\n", encoding="utf-8")
    after = _fingerprint_in(replica)
    assert after != before
    for name in sorted(SECTIONS):
        assert _recorded(name)["approved_implementation_fingerprint"] != after


@pytest.mark.parametrize(
    "relative",
    [
        "scripts/m15_track_a/row_scope.py",
        "scripts/m15_track_a/r1_orchestrator.py",
        "scripts/m15_track_a/authorization.py",
        "scripts/m15_track_a/streaming.py",
        "scripts/m15_gate3a/aggregation.py",
        "scripts/m15_gate3a/no_overlap.py",
    ],
)
def test_each_named_dependency_change_invalidates_the_grants(replica: Path, relative: str) -> None:
    """Every mechanism §7 of the instruction names, one file at a time.

    Row scope, the orchestrator, the `VerifiedRunContext` binding and the
    aggregation dependency are all on the surface, so a change to any of them
    moves the fingerprint and both grants stop being accepted. The gate3a files
    are here because the surface is the **transitive** closure, and a review
    role once found it was not.
    """
    before = _fingerprint_in(replica)
    target = replica / relative
    target.write_text(target.read_text(encoding="utf-8") + "\n# a change\n", encoding="utf-8")
    assert _fingerprint_in(replica) != before, f"{relative} is outside the surface"
