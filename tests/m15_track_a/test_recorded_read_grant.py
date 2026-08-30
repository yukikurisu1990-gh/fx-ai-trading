"""The recorded `ReadGrant` still describes the implementation it was given for.

**No test here touches real market data.** Every case reads this repository's own
`.py` sources — which is what the fingerprint is taken over — or a synthetic copy
of them in a temporary tree.

**If `test_the_recorded_fingerprint_still_matches_the_implementation` fails, the
fix is not to update the number.** It means the read implementation changed
after the grant was approved, so the grant no longer covers what would run. The
grant needs re-approval by a human + ChatGPT decision, and the recorded value
follows from that decision — not the other way round. That is the whole point of
`READ_GRANT_BINDS_TO_APPROVED_IMPLEMENTATION_ANCESTRY_NOT_SELF_REFERENTIAL_EXECUTION_HEAD`:
the failure is the mechanism working.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_track_a import authorization, containment, oos_slice

GRANT_DOCUMENT = (
    Path(containment.__file__).resolve().parents[2]
    / "docs"
    / "governance"
    / "m15_track_a_r1_read_grant.md"
)


#: Every field the §1 table must carry.  Checked as a **set**, because the
#: failure this guards against is silent: the first drafting's pattern excluded
#: backticks from the value, so the two rows whose values contain one — `pairs`
#: and `approver_record` — were dropped, and no assertion noticed because no
#: assertion read them. Two review roles found it independently.
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


def _recorded() -> dict[str, str]:
    """The §1 table, parsed. Deliberately not imported from a Python constant.

    The grant lives in a document because it is a governance record, and because
    a `.py` file holding it would be **inside the fingerprint surface** — the
    act of recording the grant would then change the value the grant records.
    """
    text = GRANT_DOCUMENT.read_text(encoding="utf-8")
    rows: dict[str, str] = {}
    for name, value in re.findall(r"^\| \*\*(\w+)\*\* \| (.+?) \|$", text, re.MULTILINE):
        assert name not in rows, f"the §1 table names {name} twice"
        rows[name] = value.strip().strip("`")
    missing = REQUIRED_FIELDS - set(rows)
    assert not missing, (
        f"the grant document's §1 table did not yield {sorted(missing)}. Either a field was "
        "removed from the record or the table's formatting changed; both need a human to "
        "look, which is why this refuses rather than testing whatever it did parse."
    )
    return rows


def test_the_recorded_fingerprint_still_matches_the_implementation() -> None:
    """Read the module docstring above before changing this number."""
    recorded = _recorded()["approved_implementation_fingerprint"]
    measured = containment.implementation_fingerprint()
    assert recorded == measured, (
        "the recorded ReadGrant is bound to implementation "
        f"{recorded} and this tree hashes to {measured}. The read implementation "
        "changed after the grant was approved, so the grant no longer covers what "
        "would run. Do not edit the recorded value: the grant needs re-approval."
    )


def test_the_documents_pair_list_is_the_frozen_universe() -> None:
    """The twenty spellings a reader sees, against the authority.

    Unpinned until two review roles said so: the tests built their grants from
    `tuple(sorted(PAIRS_20))`, so the block a human actually reads could have
    drifted from the universe while the suite stayed green.
    """
    text = GRANT_DOCUMENT.read_text(encoding="utf-8")
    block = re.search(r"The list, canonical and complete:\n\n```\n(.+?)```", text, re.S)
    assert block, "the canonical pair block is not where the parser expects it"
    listed = block.group(1).split()
    assert len(listed) == len(set(listed)) == 20
    assert set(listed) == set(PAIRS_20)


def test_the_documents_grant_code_block_matches_the_table() -> None:
    """The copy-pasteable block is what someone will actually transcribe."""
    text = GRANT_DOCUMENT.read_text(encoding="utf-8")
    block = re.search(r"GRANT = ReadGrant\((.+?)\n\)", text, re.S)
    assert block, "the §1 grant code block is not where the parser expects it"
    body = block.group(1)
    recorded = _recorded()
    for field in ("span_start_utc", "span_end_utc", "timeframe", "approved_head_sha"):
        assert f'{field}="{recorded[field]}"' in body, field
    assert recorded["approved_implementation_fingerprint"] in body
    assert recorded["approver_record"] in body
    assert "OPERATION_HISTORICAL_READ" in body
    assert "tuple(sorted(PAIRS_20))" in body


def test_the_recorded_approver_record_names_an_external_identifier() -> None:
    """C-9: a ruling with no PR number is not citable authority.

    The first drafting's `approver_record` pointed at the document containing
    it. A review role cited C-9 by name.
    """
    record = _recorded()["approver_record"]
    assert re.search(r"PR #\d+", record), record
    assert re.search(r"\d{4}-\d{2}-\d{2}", record), record


def test_the_recorded_scope_is_the_ruled_scope() -> None:
    """Every field, against the authority it came from rather than a repeated literal."""
    recorded = _recorded()
    assert recorded["operation"] == authorization.OPERATION_HISTORICAL_READ
    assert recorded["span_start_utc"] == oos_slice.DEVELOPMENT_START_UTC
    assert recorded["span_end_utc"] == oos_slice.DEVELOPMENT_END_UTC
    assert recorded["timeframe"] == "M1"


def test_the_recorded_grant_constructs_and_is_accepted() -> None:
    """A grant that cannot be built is not a grant. This builds the recorded one."""
    recorded = _recorded()
    grant = authorization.ReadGrant(
        operation=recorded["operation"],
        span_start_utc=recorded["span_start_utc"],
        span_end_utc=recorded["span_end_utc"],
        pairs=tuple(sorted(PAIRS_20)),
        timeframe=recorded["timeframe"],
        approved_head_sha=recorded["approved_head_sha"],
        approved_implementation_fingerprint=recorded["approved_implementation_fingerprint"],
        approver_record=GRANT_DOCUMENT.name,
    )
    assert grant.covers(
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
        span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
        pairs=tuple(sorted(PAIRS_20)),
        timeframe="M1",
    )


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
def test_the_recorded_grant_does_not_cover_what_it_excludes(start: str, end: str) -> None:
    """§3's table, asserted rather than described."""
    recorded = _recorded()
    grant = authorization.ReadGrant(
        operation=recorded["operation"],
        span_start_utc=recorded["span_start_utc"],
        span_end_utc=recorded["span_end_utc"],
        pairs=tuple(sorted(PAIRS_20)),
        timeframe=recorded["timeframe"],
        approved_head_sha=recorded["approved_head_sha"],
        approved_implementation_fingerprint=recorded["approved_implementation_fingerprint"],
        approver_record=GRANT_DOCUMENT.name,
    )
    assert not grant.covers(
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc=start,
        span_end_utc=end,
        pairs=tuple(sorted(PAIRS_20)),
        timeframe="M1",
    )


def test_the_recorded_grant_does_not_cover_another_operation() -> None:
    recorded = _recorded()
    grant = authorization.ReadGrant(
        operation=recorded["operation"],
        span_start_utc=recorded["span_start_utc"],
        span_end_utc=recorded["span_end_utc"],
        pairs=tuple(sorted(PAIRS_20)),
        timeframe=recorded["timeframe"],
        approved_head_sha=recorded["approved_head_sha"],
        approved_implementation_fingerprint=recorded["approved_implementation_fingerprint"],
        approver_record=GRANT_DOCUMENT.name,
    )
    for other in (
        authorization.OPERATION_M15_DERIVATION,
        authorization.OPERATION_OOS_SLICE_READ,
    ):
        assert not grant.covers(
            operation=other,
            span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
            span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
            pairs=tuple(sorted(PAIRS_20)),
            timeframe="M1",
        )


def test_the_grant_document_is_outside_the_fingerprint_surface() -> None:
    """Recording an authorization must not invalidate the authorization.

    The structural reason the sequencing works: the surface is `.py` files, the
    grant is a document, so the commit that records it changes no covered byte.
    """
    surface = {path.resolve() for path in containment.implementation_surface()}
    # Non-empty first: ``all()`` over an empty set is True, so without this the
    # two assertions below would pass on a surface that had collapsed to
    # nothing — which is exactly how an earlier defect in this package hid.
    assert len(surface) > 12, len(surface)
    assert GRANT_DOCUMENT.resolve() not in surface
    assert all(path.suffix == ".py" for path in surface)


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
    tree = tmp_path_factory.mktemp("replica") / "repo"
    (tree).mkdir()
    shutil.copytree(
        root / "scripts", tree / "scripts", ignore=shutil.ignore_patterns("__pycache__")
    )
    return tree


def test_a_documentation_only_change_does_not_move_the_fingerprint(replica: Path) -> None:
    """§6's first requirement, measured on a copy rather than argued."""
    before = _fingerprint_in(replica)
    (replica / "docs").mkdir(exist_ok=True)
    (replica / "docs" / "a_governance_note.md").write_text("recorded\n", encoding="utf-8")
    (replica / "README.md").write_text("unrelated\n", encoding="utf-8")
    assert _fingerprint_in(replica) == before


@pytest.mark.parametrize(
    "relative",
    [
        "scripts/m15_track_a/read_route.py",
        "scripts/m15_track_a/isolation.py",
        "scripts/m15_track_a/authorization.py",
        "scripts/m15_gate3a/no_overlap.py",
        "scripts/m15_gate3a/timeutil.py",
        "scripts/ml_step4/data_adapter.py",
    ],
    ids=["read-route", "isolation", "authorization", "no-overlap", "timeutil", "data-adapter"],
)
def test_a_substantive_source_change_voids_the_recorded_grant(
    replica: Path, tmp_path: Path, relative: str
) -> None:
    """A covered byte, a protected source, and a transitive dependency alike.

    `timeutil` and `data_adapter` are in the list because a review role measured
    them **outside** an earlier surface: changing `timeutil.to_utc` disabled the
    route's dead-window row guard with the fingerprint unchanged and the grant
    still valid.
    """
    tree = tmp_path / "repo"
    shutil.copytree(replica, tree, ignore=shutil.ignore_patterns("__pycache__"))
    before = _fingerprint_in(tree)
    target = tree / relative
    target.write_text(target.read_text(encoding="utf-8") + "\n# substantive\n", encoding="utf-8")
    after = _fingerprint_in(tree)
    assert after != before
    assert after != _recorded()["approved_implementation_fingerprint"]


def test_a_new_module_in_the_closure_voids_the_recorded_grant(
    replica: Path, tmp_path: Path
) -> None:
    """A dependency-closure change, not only an edit to a file already covered."""
    tree = tmp_path / "repo"
    shutil.copytree(replica, tree, ignore=shutil.ignore_patterns("__pycache__"))
    before = _fingerprint_in(tree)
    (tree / "scripts" / "m15_track_a" / "helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert _fingerprint_in(tree) != before


def test_a_shadowed_dependency_voids_the_recorded_grant(replica: Path, tmp_path: Path) -> None:
    """`scripts` is a PEP 420 namespace package, so PYTHONPATH alone can swap a subpackage.

    Resolving the surface through `importlib` is what makes the shadow the thing
    that gets hashed; path arithmetic hashed the pristine file while the process
    ran the shadow, and left nothing in any diff.
    """
    tree = tmp_path / "repo"
    shutil.copytree(replica, tree, ignore=shutil.ignore_patterns("__pycache__"))
    shadow = tmp_path / "shadow"
    (shadow / "scripts").mkdir(parents=True)
    shutil.copytree(tree / "scripts" / "m15_gate3a", shadow / "scripts" / "m15_gate3a")
    victim = shadow / "scripts" / "m15_gate3a" / "no_overlap.py"
    victim.write_text(victim.read_text(encoding="utf-8") + "\n# shadowed\n", encoding="utf-8")
    out = subprocess.run(
        [
            sys.executable,
            "-B",
            "-c",
            f"import sys; sys.path.insert(0, r'{shadow}'); sys.path.append(r'{tree}');"
            "from scripts.m15_gate3a import no_overlap;"
            "from scripts.m15_track_a import containment;"
            "print(no_overlap.__file__);"
            "print(containment.implementation_fingerprint())",
        ],
        capture_output=True,
        text=True,
        cwd=str(tree),
    )
    assert out.returncode == 0, out.stderr[-800:]
    origin, fingerprint = out.stdout.strip().splitlines()
    assert "shadow" in origin, "the shadow was not the module actually loaded"
    assert fingerprint != _recorded()["approved_implementation_fingerprint"]
