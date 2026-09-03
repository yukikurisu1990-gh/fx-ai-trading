"""The re-issued grants describe the implementation they were given for.

**No test here touches real market data.** Every case reads this repository's
own `.py` sources — which is what the fingerprint is taken over — the grant
document, or synthetic bytes in a temporary tree.

Three grant records now exist and the suite asserts a different thing about
each, deliberately:

* `test_recorded_read_grant.py` — PR #454's grant, bound to `497e187b…`, **invalid**
* `test_recorded_dual_grants.py` — PR #456's pair, bound to `e43583e0…`, **invalid**
* this file — PR #458's pair, bound to `64fbace9…`, **now invalid too**

**The R1 orchestrator invalidated these.** Adding
`scripts/m15_track_a/r1_orchestrator.py` moved the declared surface from 29
files to 30, so the fingerprint moved and neither grant covers what would run —
expected, and required by §11 of the orchestrator brief, which forbids narrowing
the surface to preserve them. As with the two records before it, the numbers are
left exactly as a human approved them and the assertions are inverted instead.

What still holds, and is still tested here, is everything these grants said about
**scope**: the span, the pairs, the timeframe, the operations, and what neither
of them reaches. Those are facts about a ruling and did not change; only the
implementation they were bound to did.

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
    / "m15_track_a_r1_dual_grants_reissued.md"
)

#: The head PR #457 merged as, which both grants name.
APPROVED_HEAD = "c2cdea03186f2a6e0f7ee394a0a039a24ef1a903"

REQUIRED_FIELDS = frozenset(
    {
        "operation",
        "span_start_utc",
        "span_end_utc",
        "pairs",
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


def _grant(name: str) -> authorization.ReadGrant:
    recorded = _recorded(name)
    return authorization.ReadGrant(
        operation=recorded["operation"],
        span_start_utc=recorded["span_start_utc"],
        span_end_utc=recorded["span_end_utc"],
        pairs=tuple(sorted(PAIRS_20)),
        timeframe=recorded["timeframe"],
        approved_head_sha=recorded["approved_head_sha"],
        approved_implementation_fingerprint=recorded["approved_implementation_fingerprint"],
        approver_record=recorded["approver_record"],
    )


def _identity(name: str) -> identity.RunIdentity:
    return identity.RunIdentity(
        run_id=f"reissued-{name}-grant-check",
        code_sha=_recorded(name)["approved_head_sha"],
        calendar_semantics=identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        started_at_utc="2026-09-02T00:00:00Z",
    )


# --------------------------------------------------------------------------
# the record is this implementation's
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_recorded_grant_is_invalidated_by_the_orchestrator(name: str) -> None:
    """**Both re-issued grants are now INVALID, and this asserts it.**

    They were valid at `c2cdea0`. The R1 orchestrator added
    `scripts/m15_track_a/r1_orchestrator.py` to the declared surface — 29 files
    to 30 — so the fingerprint moved off `64fbace9…` and neither grant covers
    what would run.

    Expected before that work started, and required: §11 of the orchestrator
    brief says "orchestrator追加によってimplementation fingerprintが変わることを
    前提とする" and forbids narrowing the surface to preserve the grants. The
    surface got **wider**.

    Inverted rather than updated, and the recorded numbers left untouched:
    editing one would forge an approval nobody gave. This is the third time the
    binding has done this, and each time the record is kept and a new one issued.
    """
    recorded = _recorded(name)["approved_implementation_fingerprint"]
    assert re.fullmatch(r"[0-9a-f]{64}", recorded), recorded
    assert recorded == "64fbace9aa8e08d835ec36b8b7fca1562af6826341d3821987d2831aa7e15cc2", (
        "the recorded value changed. It is the number a human approved; a later session may "
        "not rewrite it, and re-issuing is not the same act as editing."
    )
    assert recorded != containment.implementation_fingerprint(), (
        "the recorded grant still matches this implementation. Either the orchestrator is "
        "outside the declared surface — which would mean the formal R1 route could be swapped "
        "under a valid grant — or the recorded value was edited. Both are defects."
    )


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_invalidated_grant_is_actually_refused_at_the_gate(name: str) -> None:
    """Not merely unequal — refused, by `require_authorization`, on this tree.

    An inequality between two strings would also hold if the fingerprint check
    had been removed from the gate. This runs the gate.
    """
    with pytest.raises(authorization.AuthorizationError, match="implementation"):
        authorization.require_authorization(
            _grant(name),
            operation=_recorded(name)["operation"],
            span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
            span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
            pairs=tuple(sorted(PAIRS_20)),
            timeframe="M1",
            identity=_identity(name),
        )


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_two_superseded_records_are_still_refused(name: str) -> None:
    """Re-issuing must not resurrect a number a human gave for other code.

    The previous two records stay bound to their own fingerprints, and both are
    refused at this head. Asserted here as well as in their own files so that a
    change which quietly re-validated one could not pass by touching only this
    grant's tests.
    """
    superseded = {
        "497e187bb9fcfbc51a348d59c486bccf8d0e7c27c6fbf52cc28908a8073a7018",
        "e43583e0d72b6f89a0cfe53b375b3b1d9df6062418423ec56a7db83c0d7bd752",
    }
    current = containment.implementation_fingerprint()
    assert current not in superseded
    for stale in superseded:
        with pytest.raises(authorization.AuthorizationError, match="implementation"):
            authorization.require_authorization(
                authorization.ReadGrant(
                    operation=_recorded(name)["operation"],
                    span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
                    span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
                    pairs=tuple(sorted(PAIRS_20)),
                    timeframe="M1",
                    approved_head_sha=APPROVED_HEAD,
                    approved_implementation_fingerprint=stale,
                    approver_record="a superseded record, asserted refused",
                ),
                operation=_recorded(name)["operation"],
                span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
                span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
                pairs=tuple(sorted(PAIRS_20)),
                timeframe="M1",
                identity=_identity(name),
            )


def test_the_two_grants_name_the_two_operations() -> None:
    assert _recorded("read")["operation"] == authorization.OPERATION_HISTORICAL_READ
    assert _recorded("derivation")["operation"] == authorization.OPERATION_M15_DERIVATION


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_recorded_scope_is_the_ruled_scope(name: str) -> None:
    """Every field against the authority it came from, never a repeated literal."""
    recorded = _recorded(name)
    assert recorded["span_start_utc"] == oos_slice.DEVELOPMENT_START_UTC
    assert recorded["span_end_utc"] == oos_slice.DEVELOPMENT_END_UTC
    assert recorded["timeframe"] == "M1"
    assert recorded["approved_head_sha"] == APPROVED_HEAD


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_recorded_approver_record_names_an_external_identifier(name: str) -> None:
    """C-9: a ruling with no PR number is not citable authority."""
    record = _recorded(name)["approver_record"]
    assert re.search(r"PR #\d+", record), record
    assert re.search(r"\d{4}-\d{2}-\d{2}", record), record


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_code_block_matches_the_table(name: str) -> None:
    """The copy-pasteable block is what someone will actually transcribe."""
    body = _section(name)
    block = re.search(r"_GRANT = ReadGrant\((.+?)\n\)", body, re.S)
    assert block, f"the {name} grant's code block is not where the parser expects it"
    code = block.group(1)
    recorded = _recorded(name)
    for field in ("span_start_utc", "span_end_utc", "timeframe", "approved_head_sha"):
        assert f'{field}="{recorded[field]}"' in code, field
    assert recorded["approved_implementation_fingerprint"] in code
    assert recorded["approver_record"] in code
    assert "tuple(sorted(PAIRS_20))" in code


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_pairs_cell_names_the_registered_universe(name: str) -> None:
    """The table row a human reads, not only the block below it.

    `_recorded()` required the `pairs` field to be present and then asserted
    nothing about its value, so a mutant that rewrote the cell to a single pair
    survived the whole file: the row a reviewer reads could contradict §3a and
    the code block while the suite stayed green.
    """
    cell = _recorded(name)["pairs"]
    assert "PAIRS_20" in cell, cell
    assert "twenty" in cell.lower() or "20" in cell, cell


def test_the_documents_pair_list_is_the_frozen_universe() -> None:
    """The twenty spellings a human reads, against the authority."""
    text = GRANT_DOCUMENT.read_text(encoding="utf-8")
    block = re.search(r"The list, canonical and complete:\n\n```\n(.+?)```", text, re.S)
    assert block, "the canonical pair block is not where the parser expects it"
    listed = block.group(1).split()
    assert len(listed) == len(set(listed)) == 20
    assert set(listed) == set(PAIRS_20)


def test_the_recorded_span_is_exactly_the_development_window() -> None:
    """248 dates, ending the day before the ruled slice — arithmetic, not a literal."""
    from datetime import date, timedelta

    start = date.fromisoformat(_recorded("read")["span_start_utc"])
    end = date.fromisoformat(_recorded("read")["span_end_utc"])
    assert (end - start).days + 1 == 248
    assert end + timedelta(days=1) == date.fromisoformat(oos_slice.SLICE_START_UTC)


# --------------------------------------------------------------------------
# section 5: what neither grant reaches
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SECTIONS))
@pytest.mark.parametrize(
    "start,end",
    [
        (oos_slice.SLICE_START_UTC, oos_slice.SLICE_END_UTC),
        (oos_slice.DEVELOPMENT_START_UTC, oos_slice.SLICE_START_UTC),
        ("2026-03-01", "2026-03-31"),
        ("2026-04-25", "2026-05-31"),
        ("2025-04-24", "2025-12-28"),
    ],
    ids=["oos-slice", "one-day-into-the-slice", "dead-window", "forward-epoch", "before-design"],
)
def test_neither_grant_covers_what_section_5_excludes(name: str, start: str, end: str) -> None:
    assert not _grant(name).covers(
        operation=_recorded(name)["operation"],
        span_start_utc=start,
        span_end_utc=end,
        pairs=tuple(sorted(PAIRS_20)),
        timeframe="M1",
    )


@pytest.mark.parametrize("name", sorted(SECTIONS))
@pytest.mark.parametrize(
    "requested",
    [
        ("USD_TRY",),
        #: **Mixed**: nineteen granted pairs and one that is not. A single
        #: ungranted pair is refused by `all()` and by `any()` alike, so the
        #: one-pair case alone let an `all`→`any` mutant survive the file.
        (*sorted(PAIRS_20)[:19], "USD_TRY"),
        ("EUR_USD", "USD_SGD"),
    ],
    ids=["only-unregistered", "nineteen-granted-plus-one", "one-granted-one-not"],
)
def test_neither_grant_covers_a_request_containing_an_unregistered_pair(
    name: str, requested: tuple[str, ...]
) -> None:
    """Coverage is over **every** requested pair, not any of them."""
    assert not _grant(name).covers(
        operation=_recorded(name)["operation"],
        span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
        span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
        pairs=requested,
        timeframe="M1",
    )


@pytest.mark.parametrize("name", sorted(SECTIONS))
@pytest.mark.parametrize("timeframe", ["M5", "M15", "H1", "m1"])
def test_neither_grant_covers_another_timeframe(name: str, timeframe: str) -> None:
    """`M15` included on purpose: the derivation's *output* is not its input."""
    assert not _grant(name).covers(
        operation=_recorded(name)["operation"],
        span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
        span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
        pairs=tuple(sorted(PAIRS_20)),
        timeframe=timeframe,
    )


def test_neither_grant_covers_the_other_operation() -> None:
    """Policy 2.5, asserted: a read grant is not a derivation grant, either way."""
    for name, other in (
        ("read", authorization.OPERATION_M15_DERIVATION),
        ("derivation", authorization.OPERATION_HISTORICAL_READ),
    ):
        assert not _grant(name).covers(
            operation=other,
            span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
            span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
            pairs=tuple(sorted(PAIRS_20)),
            timeframe="M1",
        )


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_neither_grant_covers_the_oos_slice_operation(name: str) -> None:
    assert not _grant(name).covers(
        operation=authorization.OPERATION_OOS_SLICE_READ,
        span_start_utc=oos_slice.SLICE_START_UTC,
        span_end_utc=oos_slice.SLICE_END_UTC,
        pairs=tuple(sorted(PAIRS_20)),
        timeframe="M1",
    )


def test_a_read_grant_cannot_even_be_constructed_over_the_slice() -> None:
    with pytest.raises(authorization.AuthorizationMalformedError, match="EXPLORATORY_OOS_SLICE"):
        authorization.ReadGrant(
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=oos_slice.SLICE_START_UTC,
            span_end_utc=oos_slice.SLICE_END_UTC,
            pairs=tuple(sorted(PAIRS_20)),
            timeframe="M1",
            approved_head_sha=APPROVED_HEAD,
            approved_implementation_fingerprint=containment.implementation_fingerprint(),
            approver_record="synthetic probe, not a recorded grant",
        )


# --------------------------------------------------------------------------
# section 7: the binding
# --------------------------------------------------------------------------


def test_the_grant_document_is_outside_the_fingerprint_surface() -> None:
    """Recording an authorization must not invalidate the authorization."""
    surface = {path.resolve() for path in containment.implementation_surface()}
    names = {path.name for path in surface}
    assert {
        "read_route.py",
        "derivation.py",
        "row_scope.py",
        "r1_survey.py",
        "authorization.py",
        "containment.py",
        "oos_slice.py",
        "derivation_containment.py",
        "session_windows.py",
        "aggregation.py",
        "no_overlap.py",
    } <= names, sorted(names)
    assert len(surface) >= 20, len(surface)
    assert GRANT_DOCUMENT.resolve() not in surface
    assert all(path.suffix == ".py" for path in surface)
    assert not any("tests" in path.parts for path in surface)


def _fingerprint_in(tree: Path) -> str:
    out = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            f"import sys; sys.path.insert(0, r'{tree}');"
            "from scripts.m15_track_a import containment;"
            "print(containment.implementation_fingerprint())",
        ],
        capture_output=True,
        text=True,
        cwd=str(tree),
    )
    assert out.returncode == 0, out.stderr[-800:]
    return out.stdout.strip()


@pytest.fixture(scope="module")
def replica(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = Path(containment.__file__).resolve().parents[2]
    tree = tmp_path_factory.mktemp("reissued-replica") / "repo"
    tree.mkdir()
    shutil.copytree(
        root / "scripts", tree / "scripts", ignore=shutil.ignore_patterns("__pycache__")
    )
    return tree


def test_recording_a_governance_document_does_not_move_the_fingerprint(replica: Path) -> None:
    """The property that lets an authorization record itself.

    Still load-bearing for the grants that will be re-issued against the
    orchestrator's fingerprint. Asserted on the value alone: the grants recorded
    in this document no longer match it, which is what
    `test_the_recorded_grant_is_invalidated_by_the_orchestrator` says.
    """
    before = _fingerprint_in(replica)
    (replica / "docs").mkdir(exist_ok=True)
    (replica / "docs" / "another_grant_record.md").write_text("recorded\n", encoding="utf-8")
    (replica / "README.md").write_text("unrelated\n", encoding="utf-8")
    assert _fingerprint_in(replica) == before


@pytest.mark.parametrize(
    "relative",
    [
        "m15_track_a/read_route.py",
        "m15_track_a/derivation.py",
        "m15_track_a/row_scope.py",
        "m15_track_a/r1_survey.py",
        "m15_track_a/authorization.py",
        "m15_track_a/oos_slice.py",
        "m15_gate3a/derivation_containment.py",
        "m15_gate3a/session_windows.py",
        "m15_gate3a/aggregation.py",
        "m15_gate3a/no_overlap.py",
        "m15_gate3a/timeutil.py",
        "ml_step4/data_adapter.py",
        "ml_step4/contract.py",
        "ml_step4/inventory.py",
    ],
    ids=lambda value: value.replace("/", "-").removesuffix(".py"),
)
def test_a_substantive_source_change_voids_both_grants(
    replica: Path, tmp_path: Path, relative: str
) -> None:
    """Each surface the two grants actually depend on, mutated on its own.

    `ml_step4/{contract,inventory}.py` are named because they were **outside**
    the surface until PR #457: the closure dropped them, so a change to what runs
    left a grant bound to it valid.
    """
    tree = tmp_path / "repo"
    shutil.copytree(replica, tree, ignore=shutil.ignore_patterns("__pycache__"))
    before = _fingerprint_in(tree)
    target = tree / "scripts" / relative
    assert target.exists(), relative
    target.write_text(target.read_text(encoding="utf-8") + "\n# substantive\n", encoding="utf-8")
    after = _fingerprint_in(tree)
    assert after != before
    for name in SECTIONS:
        assert after != _recorded(name)["approved_implementation_fingerprint"]


def test_the_surface_is_the_transitive_closure_the_record_claims(tmp_path: Path) -> None:
    """§7's claim, measured against a closure computed here.

    The package is derived locally rather than by calling
    `containment._module_package`: a test that imports the predicate it is
    testing cannot falsify it, and this repository has paid for that shape.
    """
    import ast
    import importlib.util

    root = Path(containment.__file__).resolve().parents[2]
    surface = {path.resolve() for path in containment.implementation_surface()}

    def resolve(name: str) -> Path | None:
        try:
            spec = importlib.util.find_spec(name)
        except Exception:  # noqa: BLE001
            return None
        if spec is None or not spec.origin or not spec.origin.endswith(".py"):
            return None
        return Path(spec.origin).resolve()

    seen: set[Path] = set()
    stack = list(surface)
    while stack:
        path = stack.pop()
        if path in seen:
            continue
        seen.add(path)
        package = ".".join(path.relative_to(root).with_suffix("").parts[:-1])
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("scripts"):
                        found = resolve(alias.name)
                        if found:
                            stack.append(found)
                continue
            if not isinstance(node, ast.ImportFrom):
                continue
            module = node.module or ""
            if node.level:
                parts = package.split(".")
                base = ".".join(parts[: len(parts) - (node.level - 1)])
                module = f"{base}.{module}".rstrip(".") if module else base
            if not module.startswith("scripts"):
                continue
            for candidate in (module, *(f"{module}.{a.name}" for a in node.names)):
                found = resolve(candidate)
                if found:
                    stack.append(found)

    assert not (seen - surface), sorted(str(p) for p in seen - surface)
    assert not (surface - seen), sorted(str(p) for p in surface - seen)


def test_only_the_read_route_pins_the_timeframe_to_the_source_constant() -> None:
    """Section 3's referral, pinned in both directions.

    The first drafting of the grant record said "a grant naming `M15` is
    refused". A review role measured a self-consistent non-`M1` derivation grant
    running to completion: `read_historical` compares its grant against the
    committed `SOURCE_TIMEFRAME`, and `derive_m15` compares it only against the
    request — two caller-supplied strings.

    Asserted as an **asymmetry**, not as a weakness to be tolerated quietly: the
    pin that exists must stay, and the one that does not must stay disclosed. If
    the referred fix lands, this fails and whoever lands it must update §3 in the
    same change — and re-issue the grants, because it moves the fingerprint.
    """
    import inspect

    from scripts.m15_track_a import derivation, read_route

    read_source = inspect.getsource(read_route.read_historical)
    assert "checked.timeframe != SOURCE_TIMEFRAME" in read_source

    derive_source = inspect.getsource(derivation)
    assert "SOURCE_TIMEFRAME" not in derive_source, (
        "derive_m15 now pins its timeframe to the committed source constant. That is the "
        "referred fix landing, which is good news — but section 3 of "
        "docs/governance/m15_track_a_r1_dual_grants_reissued.md still says the pin is absent, "
        "and the fingerprint moved, so both grants need re-issuing."
    )
    #: and the document says so, rather than claiming the refusal
    document = GRANT_DOCUMENT.read_text(encoding="utf-8")
    assert "DERIVATION_ROUTE_DOES_NOT_PIN_ITS_TIMEFRAME" in document


def test_a_slice_spanning_derivation_grant_constructs_but_the_route_refuses_it() -> None:
    """Section 5's first row, in both halves.

    `_assert_operation_span` bounds the read operation and deliberately not the
    derivation, so the construction-level ceiling is the read grant's alone. The
    record says so; this stops the claim drifting to "refused at the grant".
    """
    from scripts.m15_track_a import read_route

    over_the_slice = authorization.ReadGrant(
        operation=authorization.OPERATION_M15_DERIVATION,
        span_start_utc=oos_slice.SLICE_START_UTC,
        span_end_utc=oos_slice.SLICE_END_UTC,
        pairs=tuple(sorted(PAIRS_20)),
        timeframe="M1",
        approved_head_sha=APPROVED_HEAD,
        approved_implementation_fingerprint=containment.implementation_fingerprint(),
        approver_record="synthetic probe, not a recorded grant",
    )
    assert over_the_slice.span_start_utc == oos_slice.SLICE_START_UTC

    request = read_route.ReadRequest(
        span_start_utc=oos_slice.SLICE_START_UTC,
        span_end_utc=oos_slice.SLICE_END_UTC,
        pairs=tuple(sorted(PAIRS_20)),
        timeframe="M1",
        warmup_extension_start_utc=oos_slice.SLICE_START_UTC,
    )
    with pytest.raises(read_route.ReadRouteError, match="EXPLORATORY_OOS_SLICE"):
        read_route.assert_development_only(request)


def test_pair_authority_canonicalises_aliases_rather_than_refusing_them() -> None:
    """Section 5's alias row names the mechanism, not only the outcome.

    An earlier drafting attributed the refusal to `pair_authority`. It
    canonicalises `EURUSD` instead; what refuses an alias is `grant_covers` at
    the request level and `assert_batch_pairs_in_scope` at the batch level.
    """
    from scripts.m15_gate3a.pair_authority import PairAuthorityError, canonical_pair

    assert canonical_pair("EURUSD") == "EUR_USD"
    assert canonical_pair("eur/usd") == "EUR_USD"
    with pytest.raises(PairAuthorityError):
        canonical_pair("USD_SGD")
    for name in SECTIONS:
        assert not _grant(name).covers(
            operation=_recorded(name)["operation"],
            span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
            span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
            pairs=("EURUSD",),
            timeframe="M1",
        )


def test_no_first_party_dynamic_import_escapes_the_surface() -> None:
    """§7a, asserted rather than described.

    The standing instruction is to stop only if the R1 path actually depends on
    a first-party `importlib.import_module(".x", __package__)`. It does not, and
    this pins that: the only dynamic first-party import enumerates
    `scripts.m15_track_a`'s own modules, every one of which the package walk
    already covers.
    """
    import ast

    surface = containment.implementation_surface()
    covered = {containment._surface_name(path) for path in surface}
    dynamic: list[str] = []
    for path in surface:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
            #: All six names §7a claims were scanned. The first drafting
            #: checked four, so a later `eval`/`exec` would not have tripped the
            #: "if a third appears, a human looks" guard the document relies on.
            if name in {
                "import_module",
                "__import__",
                "exec_module",
                "module_from_spec",
                "eval",
                "exec",
            }:
                dynamic.append(f"{containment._surface_name(path)}:{node.lineno}")
    #: Two known sites; if a third appears, a human looks before a grant is
    #: issued. Pinned by **file**, not by line: the line numbers moved the first
    #: time anything was inserted above them, and a pin that breaks on an
    #: unrelated edit trains people to update it without reading it.
    assert sorted({site.split(":")[0] for site in dynamic}) == [
        "m15_track_a/containment.py",
        "m15_track_a/isolation.py",
    ], dynamic
    assert len(dynamic) == 2, dynamic
    #: and the first-party one reaches nothing outside the surface
    for module_name in containment.package_modules():
        source = containment._module_source(module_name)
        assert source is not None, module_name
        assert containment._surface_name(source) in covered, module_name
