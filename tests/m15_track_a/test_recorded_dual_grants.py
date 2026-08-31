"""The two recorded grants describe the implementation they were given for.

**No test here touches real market data.** Every case reads this repository's
own `.py` sources — which is what the fingerprint is taken over — the grant
document, or synthetic bytes in a temporary tree.

The companion file `test_recorded_read_grant.py` asserts the *previous* grant is
**invalid** at this head. This one asserts the two new ones are **valid**, and
the pair is deliberate: an implementation change has to break exactly one of the
two files, and if a change ever leaves both green the fingerprint stopped
covering something.

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
    / "m15_track_a_r1_dual_grants.md"
)

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

#: The section heading each grant's table lives under.  Parsing by section
#: rather than by field name is what makes two grants in one document safe: a
#: whole-file scan would silently merge them, and the merge would look like a
#: single well-formed grant.
SECTIONS = {
    "read": "## 2. Grant A — the historical development read",
    "derivation": "## 3. Grant B — the M15 research derivation",
}


def _section(name: str) -> str:
    text = GRANT_DOCUMENT.read_text(encoding="utf-8")
    heading = SECTIONS[name]
    assert text.count(heading) == 1, f"{heading!r} does not appear exactly once"
    body = text.split(heading, 1)[1]
    #: Stop at the next top-level heading so a field defined further down the
    #: document cannot be attributed to this grant.
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


# --------------------------------------------------------------------------
# the record is this implementation's
# --------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_recorded_fingerprint_is_this_implementation(name: str) -> None:
    """Measured, not transcribed.

    A number copied out of a previous session's report is not an authority, and
    this is the assertion that makes the difference observable.
    """
    recorded = _recorded(name)["approved_implementation_fingerprint"]
    assert re.fullmatch(r"[0-9a-f]{64}", recorded), recorded
    assert recorded == containment.implementation_fingerprint()


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_the_recorded_grant_is_accepted_by_the_gate(name: str) -> None:
    """Not merely equal — accepted, by `require_authorization`, on this tree."""
    recorded = _recorded(name)
    authorization.require_authorization(
        _grant(name),
        operation=recorded["operation"],
        span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
        span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
        pairs=tuple(sorted(PAIRS_20)),
        timeframe="M1",
        identity=identity.RunIdentity(
            run_id=f"recorded-{name}-grant-check",
            code_sha=recorded["approved_head_sha"],
            calendar_semantics=identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
            started_at_utc="2026-08-31T00:00:00Z",
        ),
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
    assert recorded["approved_head_sha"] == "fc3e0f881d424844ca6823ae2708b76839c313dc"


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


def test_the_documents_pair_list_is_the_frozen_universe() -> None:
    """The twenty spellings a human reads, against the authority.

    Guards the failure the read-grant document had: the tests built their grants
    from `PAIRS_20`, so the block a human actually approves could drift from the
    universe while the suite stayed green.
    """
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
def test_neither_grant_covers_an_unregistered_pair(name: str) -> None:
    assert not _grant(name).covers(
        operation=_recorded(name)["operation"],
        span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
        span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
        pairs=("USD_TRY",),
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


@pytest.mark.parametrize("name", sorted(SECTIONS))
def test_a_whitespace_padded_timeframe_raises_rather_than_returning_false(name: str) -> None:
    """`"M1 "` is refused harder than a wrong timeframe, and that is the point.

    A near-miss spelling is a malformed request, not a request outside the
    grant, so `grant_covers` raises instead of answering it. Asserted
    separately because a test that only checked `not covers(...)` would have
    passed on a route that silently stripped the padding.
    """
    with pytest.raises(authorization.AuthorizationMalformedError, match="whitespace"):
        _grant(name).covers(
            operation=_recorded(name)["operation"],
            span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
            span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
            pairs=tuple(sorted(PAIRS_20)),
            timeframe="M1 ",
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


def test_a_derivation_grant_over_the_slice_is_stopped_by_the_route() -> None:
    """Section 5a's asymmetry, pinned in both directions.

    An earlier revision of the grant document claimed `ReadGrant.__post_init__`
    refuses **either** operation over a slice date. It does not: only
    `track_a_historical_read` is constrained there, and `_assert_operation_span`
    says so on purpose. The derivation's protection is one layer further in, so
    this asserts the layer that is missing is missing and the layer that carries
    the weight carries it — a test that only checked the refusal would pass
    against either arrangement and tell a reviewer nothing.
    """
    from scripts.m15_track_a import read_route

    #: the layer that is NOT there
    over_the_slice = authorization.ReadGrant(
        operation=authorization.OPERATION_M15_DERIVATION,
        span_start_utc=oos_slice.SLICE_START_UTC,
        span_end_utc=oos_slice.SLICE_END_UTC,
        pairs=tuple(sorted(PAIRS_20)),
        timeframe="M1",
        approved_head_sha=_recorded("derivation")["approved_head_sha"],
        approved_implementation_fingerprint=containment.implementation_fingerprint(),
        approver_record="synthetic probe, not a recorded grant",
    )
    assert over_the_slice.span_start_utc == oos_slice.SLICE_START_UTC

    #: the same construction IS refused for the read operation
    with pytest.raises(authorization.AuthorizationMalformedError, match="EXPLORATORY_OOS_SLICE"):
        authorization.ReadGrant(
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=oos_slice.SLICE_START_UTC,
            span_end_utc=oos_slice.SLICE_END_UTC,
            pairs=tuple(sorted(PAIRS_20)),
            timeframe="M1",
            approved_head_sha=_recorded("read")["approved_head_sha"],
            approved_implementation_fingerprint=containment.implementation_fingerprint(),
            approver_record="synthetic probe, not a recorded grant",
        )

    #: the layer that DOES carry the weight, on the request the derivation consumes
    def request(start: str, end: str, warmup: str | None = None) -> read_route.ReadRequest:
        return read_route.ReadRequest(
            span_start_utc=start,
            span_end_utc=end,
            pairs=tuple(sorted(PAIRS_20)),
            timeframe="M1",
            warmup_extension_start_utc=warmup or start,
        )

    read_route.assert_development_only(
        request(oos_slice.DEVELOPMENT_START_UTC, oos_slice.DEVELOPMENT_END_UTC)
    )
    for start, end, warmup in (
        (oos_slice.SLICE_START_UTC, oos_slice.SLICE_END_UTC, None),
        (oos_slice.DEVELOPMENT_START_UTC, oos_slice.SLICE_START_UTC, None),
        ("2026-01-05", "2026-01-31", "2025-12-20"),
    ):
        with pytest.raises(read_route.ReadRouteError):
            read_route.assert_development_only(request(start, end, warmup))


def test_the_derivation_applies_the_development_gate_before_it_aggregates() -> None:
    """Order matters: a guard after `DELEGATE` would run on already-derived bars."""
    import inspect

    from scripts.m15_track_a import derivation

    source = inspect.getsource(derivation.derive_m15)
    calls = [
        name
        for name in re.findall(
            r"(require_authorization|assert_span_admissible|assert_development_only|DELEGATE)\(",
            source,
        )
    ]
    assert calls == [
        "require_authorization",
        "assert_span_admissible",
        "assert_development_only",
        "DELEGATE",
    ], calls


# --------------------------------------------------------------------------
# section 7: what invalidates them
# --------------------------------------------------------------------------


def test_the_grant_document_is_outside_the_fingerprint_surface() -> None:
    """Recording an authorization must not invalidate the authorization."""
    surface = {path.resolve() for path in containment.implementation_surface()}
    # Non-empty first: ``all()`` over an empty set is True, so without this the
    # assertions below would pass on a surface that had collapsed to nothing.
    assert len(surface) > 12, len(surface)
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
    """A copy of the source tree, so nothing below writes to the repository."""
    root = Path(containment.__file__).resolve().parents[2]
    tree = tmp_path_factory.mktemp("dual-replica") / "repo"
    tree.mkdir()
    shutil.copytree(
        root / "scripts", tree / "scripts", ignore=shutil.ignore_patterns("__pycache__")
    )
    return tree


def test_recording_a_governance_document_keeps_both_grants_valid(replica: Path) -> None:
    """Section 7's first claim, measured on a copy rather than argued."""
    before = _fingerprint_in(replica)
    (replica / "docs").mkdir(exist_ok=True)
    (replica / "docs" / "another_grant_record.md").write_text("recorded\n", encoding="utf-8")
    assert _fingerprint_in(replica) == before
    for name in SECTIONS:
        assert _recorded(name)["approved_implementation_fingerprint"] == before


@pytest.mark.parametrize(
    "relative",
    [
        "scripts/m15_track_a/read_route.py",
        "scripts/m15_track_a/derivation.py",
        "scripts/m15_track_a/r1_survey.py",
        "scripts/m15_track_a/authorization.py",
        "scripts/m15_gate3a/derivation_containment.py",
        "scripts/m15_gate3a/session_windows.py",
        "scripts/m15_gate3a/aggregation.py",
        "scripts/m15_gate3a/no_overlap.py",
        "scripts/m15_gate3a/timeutil.py",
        "scripts/ml_step4/data_adapter.py",
    ],
    ids=[
        "read-route",
        "derivation",
        "survey",
        "authorization",
        "containment",
        "session-windows",
        "aggregation",
        "no-overlap",
        "timeutil",
        "data-adapter",
    ],
)
def test_a_substantive_source_change_voids_both_grants(
    replica: Path, tmp_path: Path, relative: str
) -> None:
    """One parametrisation per surface the two grants actually depend on.

    `aggregation`, `derivation_containment` and `session_windows` are here
    because Grant B reaches them and Grant A's list did not name them; a
    fingerprint that covered the read route but not the aggregator would leave
    the derivation grant binding to nothing.
    """
    tree = tmp_path / "repo"
    shutil.copytree(replica, tree, ignore=shutil.ignore_patterns("__pycache__"))
    before = _fingerprint_in(tree)
    target = tree / relative
    assert target.exists(), relative
    target.write_text(target.read_text(encoding="utf-8") + "\n# substantive\n", encoding="utf-8")
    after = _fingerprint_in(tree)
    assert after != before
    for name in SECTIONS:
        assert after != _recorded(name)["approved_implementation_fingerprint"]
