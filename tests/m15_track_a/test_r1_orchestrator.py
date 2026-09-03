"""The formal R1 route, end to end, on **synthetic data only**.

`TRACK_A_R1_ORCHESTRATOR_SYNTHETIC_E2E_PASSED` is what this file establishes.

**No test here touches real market data.** Every case writes synthetic JSONL into
a temporary tree and repoints `source_path_for` at it; `data/` is never opened,
and the scratch and ledger roots are redirected so no real seen-data entry is
created.

**Every case drives `r1_orchestrator.run_r1` or `preflight`.** There is no
test-only composition of the stages — that is the whole point of the module, and
a test that reassembled the sequence itself would be testing a second route
nobody reviewed. The one thing the fixture does that a real run would not is
supply synthetic *inputs*: a temp source tree, a temp scratch root, and grants
bound to the measured fingerprint of this tree rather than to a recorded human
approval.

The negative cases are the substance. A route whose refusals are untested is a
route that refuses by accident.
"""

from __future__ import annotations

import ast
import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_track_a import (
    authorization,
    breadth,
    containment,
    derivation,
    identity,
    isolation,
    oos_slice,
    r1_orchestrator,
    r1_survey,
    read_route,
    scratch,
    seen_ledger,
    streaming,
)

EPOCH = read_route.SOURCE_EPOCH
PAIRS = tuple(sorted(PAIRS_20))
#: The formal route requires the whole authorised corpus, so the plan names it.
SPAN_START = oos_slice.DEVELOPMENT_START_UTC
SPAN_END = oos_slice.DEVELOPMENT_END_UTC
#: The fixture only *writes* a couple of days inside that span. A read returns
#: the rows the source actually holds; it does not require the file to fill the
#: window. Writing 248 days × 20 pairs of minutes would test the fixture's
#: patience, not the route.
FIXTURE_START = "2025-05-05"  # a Monday
FIXTURE_END = "2025-05-06"
APPROVED_SHA = "a" * 40


# ---------------------------------------------------------------------------
# Fixtures — synthetic everything
# ---------------------------------------------------------------------------


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("track_a_scratch", "data"):
        (tmp_path / name).mkdir()
    monkeypatch.setattr(scratch, "scratch_root", lambda: tmp_path / "track_a_scratch")
    monkeypatch.setattr(
        read_route,
        "source_path_for",
        lambda pair: (
            tmp_path / "data" / read_route.SOURCE_FILENAME_TEMPLATE.format(pair=pair, epoch=EPOCH)
        ),
    )
    return tmp_path


@pytest.fixture
def fast_fingerprint(monkeypatch: pytest.MonkeyPatch) -> str:
    """The **real** measured fingerprint, computed once instead of per check.

    `require_authorization` measures the tree on every check — deliberately, so
    a mid-run source change is caught — and the bounded-memory route checks once
    per window. A full-corpus run measures it 181 times, each parsing thirty
    source files: about 48 seconds a case, and this file has fifty-odd.

    This memoises the value, not the check. The comparison, every refusal and
    every negative case below are untouched, and
    `test_r1_streaming.py::test_the_fingerprint_is_measured_at_every_check_not_cached`
    runs unmemoised and asserts the per-check property this would otherwise
    hide.
    """
    measured = containment.implementation_fingerprint()
    monkeypatch.setattr(containment, "implementation_fingerprint", lambda: measured)
    return measured


@pytest.fixture
def guards_installed() -> object:
    isolation.install_all()
    try:
        yield
    finally:
        isolation.uninstall_all()


def _write_minutes(sandbox: Path, pair: str, *, start: str, end: str) -> None:
    """One M1 bid/ask row per minute, in the committed shape, no market-hours filter."""
    path = sandbox / "data" / read_route.SOURCE_FILENAME_TEMPLATE.format(pair=pair, epoch=EPOCH)
    jpy = pair.endswith("_JPY")
    base = 150.0 if jpy else 1.1000
    tick = 0.01 if jpy else 0.0001
    moment = datetime.fromisoformat(start).replace(tzinfo=UTC)
    stop = datetime.fromisoformat(end).replace(tzinfo=UTC) + timedelta(days=1)
    index = 0
    with path.open("w", encoding="utf-8") as handle:
        while moment < stop:
            mid = base + ((index % 40) - 20) * tick
            half = tick
            handle.write(
                json.dumps(
                    {
                        "time": moment.isoformat().replace("+00:00", "Z"),
                        "bid_o": mid - half,
                        "bid_h": mid - half + 3 * tick,
                        "bid_l": mid - half - 3 * tick,
                        "bid_c": mid - half + tick,
                        "ask_o": mid + half,
                        "ask_h": mid + half + 3 * tick,
                        "ask_l": mid + half - 3 * tick,
                        "ask_c": mid + half + tick,
                    }
                )
                + "\n"
            )
            moment += timedelta(minutes=1)
            index += 1


@pytest.fixture
def source_tree(sandbox: Path, fast_fingerprint: str) -> Path:
    for pair in PAIRS:
        _write_minutes(sandbox, pair, start=FIXTURE_START, end=FIXTURE_END)
    return sandbox


def _run(**overrides: Any) -> identity.RunIdentity:
    fields: dict[str, Any] = {
        "run_id": "r1-orchestrator-synthetic",
        "code_sha": APPROVED_SHA,
        "calendar_semantics": identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        "started_at_utc": "2026-09-02T00:00:00Z",
    }
    fields.update(overrides)
    return identity.RunIdentity(**fields)


def _grant(operation: str, **overrides: Any) -> authorization.ReadGrant:
    fields: dict[str, Any] = {
        "operation": operation,
        "span_start_utc": SPAN_START,
        "span_end_utc": SPAN_END,
        "pairs": PAIRS,
        "timeframe": "M1",
        "approved_head_sha": APPROVED_SHA,
        "approved_implementation_fingerprint": containment.implementation_fingerprint(),
        "approver_record": "synthetic dry-run grant, not a recorded approval",
    }
    fields.update(overrides)
    return authorization.ReadGrant(**fields)


def _plan(**overrides: Any) -> r1_orchestrator.R1Plan:
    fields: dict[str, Any] = {
        "span_start_utc": SPAN_START,
        "span_end_utc": SPAN_END,
        "pairs": PAIRS,
    }
    fields.update(overrides)
    return r1_orchestrator.R1Plan(**fields)


def _invoke(**overrides: Any) -> Any:
    """Always through the orchestrator. Never a hand-assembled sequence."""
    plan = overrides.pop("plan", None) or _plan()
    run = overrides.pop("identity", None) or _run()
    read_grant = overrides.pop("read_grant", _grant(authorization.OPERATION_HISTORICAL_READ))
    derivation_grant = overrides.pop(
        "derivation_grant", _grant(authorization.OPERATION_M15_DERIVATION)
    )
    assert not overrides, overrides
    return r1_orchestrator.run_r1(
        plan, run, read_grant=read_grant, derivation_grant=derivation_grant
    )


@pytest.fixture
def completed(source_tree: Path, guards_installed: object) -> Any:
    """One whole R1 run through the formal entry point, so the cases can assert on it."""
    return _invoke()


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_the_formal_route_completes_end_to_end(completed: Any) -> None:
    """preflight → declare → read → derive → K → survey → stop."""
    assert type(completed) is r1_orchestrator.R1Result
    assert completed.status == r1_orchestrator.R1_COMPLETE
    assert completed.preflight.status == r1_orchestrator.PREFLIGHT_PASSED
    assert type(completed.survey) is r1_survey.R1Survey


def test_every_stage_records_the_same_run_identity(completed: Any) -> None:
    """A run whose records disagree about who ran is not one run."""
    run_id = completed.run_id
    assert run_id == "r1-orchestrator-synthetic"
    assert completed.survey.run_id == run_id
    declarations = seen_ledger.read_declarations()
    assert declarations, "the seen interval was never declared"
    assert {entry.run_id for entry in declarations} == {run_id}
    assert {entry.run_id for entry in breadth.read_entries()} == {run_id}


def test_the_survey_is_populated_and_carries_both_track_a_labels(completed: Any) -> None:
    survey = completed.survey
    assert survey.timeframe == "M15"
    assert survey.pairs == PAIRS
    assert survey.classification == "NON_DECISION_BEARING_EXPLORATORY_ONLY"
    assert survey.classification_secondary == "RESEARCH_SCRATCH_NON_AUTHORITATIVE"
    record = survey.as_record()
    for pair in survey.pairs:
        assert record["schema"][pair]["bars"] > 0


def test_breadth_k_is_zero_and_explicit(completed: Any) -> None:
    """R1 scores nothing, so `K` is recorded as 0 rather than left absent."""
    assert completed.breadth_k == 0
    entries = breadth.read_entries()
    assert len(entries) == 1
    assert entries[0].result_observed is False


def test_the_declaration_precedes_the_read(source_tree: Path, guards_installed: object) -> None:
    """Write-ahead: a run that dies mid-read still leaves the record of the interval.

    Driven by making the **read** fail after preflight has passed, then checking
    the ledger. A route that declared afterwards would leave nothing here.
    """
    for pair in PAIRS:
        (
            source_tree
            / "data"
            / read_route.SOURCE_FILENAME_TEMPLATE.format(pair=pair, epoch=EPOCH)
        ).unlink()
    with pytest.raises(Exception):  # noqa: B017 - the read route's own refusal
        _invoke()
    declarations = seen_ledger.read_declarations()
    assert declarations, "the read was attempted with no seen-data declaration on record"
    assert declarations[0].span_start_utc == SPAN_START


def test_the_result_names_no_next_stage(completed: Any) -> None:
    """R1 produces a survey and stops."""
    assert completed.next_stage is None
    record = completed.as_record()
    assert record["stage"] == "R1"
    assert record["next_stage"] is None
    assert "STOP" in record["status"]


# ---------------------------------------------------------------------------
# Preflight refuses before a byte is read
# ---------------------------------------------------------------------------


@pytest.fixture
def opened_paths(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    """Every path opened through `Path.open` while a case runs.

    The first drafting's `_assert_nothing_read` looped over the source files and
    asserted `path.stat().st_atime is not None` — which is true of any file that
    exists. A review role pointed out that the helper on which every
    `..._stops_before_any_read` case rested asserted nothing about reading. This
    records the opens instead, so "no source file was touched" is measured.
    """
    recorded: list[Path] = []
    real_open = Path.open

    def spy(self: Path, *args: Any, **kwargs: Any) -> Any:
        recorded.append(Path(self))
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", spy)
    return recorded


def _assert_nothing_read(sandbox: Path, opened: list[Path] | None = None) -> None:
    """No source file was opened, and no seen interval was declared."""
    if opened is not None:
        source_root = (sandbox / "data").resolve()
        touched = [path for path in opened if path.resolve().is_relative_to(source_root)]
        assert not touched, f"a source file was opened before the refusal: {touched}"
    assert not seen_ledger.read_declarations(), (
        "a seen-data interval was declared even though preflight refused — the refusal did not "
        "cost zero data bytes"
    )
    assert not breadth.read_entries()


@pytest.mark.parametrize(
    "overrides,match",
    [
        ({"read_grant": None}, "no track_a_historical_read grant"),
        ({"derivation_grant": None}, "no track_a_m15_research_derivation grant"),
        (
            {"read_grant": "not a grant"},
            "read grant must be exactly a ReadGrant",
        ),
    ],
    ids=["no-grant-a", "no-grant-b", "grant-a-not-a-grant"],
)
def test_a_missing_or_malformed_grant_stops_before_any_read(
    source_tree: Path,
    guards_installed: object,
    opened_paths: list[Path],
    overrides: dict[str, Any],
    match: str,
) -> None:
    with pytest.raises(r1_orchestrator.R1OrchestratorError, match=match):
        _invoke(**overrides)
    _assert_nothing_read(source_tree, opened_paths)


@pytest.mark.parametrize("which", ["read_grant", "derivation_grant"])
def test_a_fingerprint_mismatch_stops_before_any_read(
    source_tree: Path, guards_installed: object, opened_paths: list[Path], which: str
) -> None:
    operation = (
        authorization.OPERATION_HISTORICAL_READ
        if which == "read_grant"
        else authorization.OPERATION_M15_DERIVATION
    )
    stale = _grant(operation, approved_implementation_fingerprint="0" * 64)
    #: `VerifiedRunContext.__post_init__` is what refuses now, and it refuses in
    #: its own type rather than being wrapped — `preflight` is pinned against
    #: `try`/`except`, and relabelling a refusal is not worth spending that on.
    with pytest.raises(
        authorization.AuthorizationMalformedError, match="changed after the approval"
    ):
        _invoke(**{which: stale})
    _assert_nothing_read(source_tree, opened_paths)


def test_the_two_grants_must_name_the_same_approved_head(
    source_tree: Path, guards_installed: object
) -> None:
    other = _grant(authorization.OPERATION_M15_DERIVATION, approved_head_sha="b" * 40)
    with pytest.raises(authorization.AuthorizationMalformedError, match="different approved heads"):
        _invoke(derivation_grant=other)
    _assert_nothing_read(source_tree)


def test_a_run_identity_naming_another_head_stops_before_any_read(
    source_tree: Path, guards_installed: object
) -> None:
    with pytest.raises(
        authorization.AuthorizationMalformedError, match="different head from the grants"
    ):
        _invoke(identity=_run(code_sha="c" * 40))
    _assert_nothing_read(source_tree)


@pytest.mark.parametrize("timeframe", ["M15", "M5", "H1", "m1"])
def test_a_plan_naming_another_timeframe_stops_before_any_read(
    source_tree: Path, guards_installed: object, timeframe: str
) -> None:
    """The orchestrator-level pin. `M15` is the natural wrong value here."""
    with pytest.raises(r1_orchestrator.R1OrchestratorError, match="formal R1 route reads M1"):
        _invoke(plan=_plan(timeframe=timeframe))
    _assert_nothing_read(source_tree)


@pytest.mark.parametrize(
    "span,label",
    [
        ((oos_slice.SLICE_START_UTC, oos_slice.SLICE_END_UTC), "oos-slice"),
        ((SPAN_START, oos_slice.SLICE_START_UTC), "into-the-slice"),
        (("2026-03-01", "2026-03-31"), "dead-window"),
        (("2026-04-25", "2026-05-31"), "forward-epoch"),
        (("2025-04-24", SPAN_END), "pre-design"),
        ((SPAN_START, "2025-06-30"), "narrower-than-the-corpus"),
    ],
)
def test_a_plan_outside_the_authorised_corpus_stops_before_any_read(
    source_tree: Path,
    guards_installed: object,
    opened_paths: list[Path],
    span: tuple[str, str],
    label: str,
) -> None:
    """The slice, the dead window and the forward epoch, measured to 0 data bytes."""
    start, end = span
    with pytest.raises(r1_orchestrator.R1OrchestratorError):
        _invoke(plan=_plan(span_start_utc=start, span_end_utc=end))
    _assert_nothing_read(source_tree, opened_paths)


@pytest.mark.parametrize(
    "pairs,label",
    [
        (("EUR_USD",), "one-pair"),
        (PAIRS[:-1], "nineteen"),
        ((*PAIRS, "USD_TRY"), "twenty-one-with-an-outsider"),
        ((*PAIRS[:-1], "EUR_USD"), "duplicate"),
    ],
)
def test_a_plan_whose_pairs_are_not_the_universe_stops_before_any_read(
    source_tree: Path, guards_installed: object, pairs: tuple[str, ...], label: str
) -> None:
    with pytest.raises(r1_orchestrator.R1OrchestratorError):
        _invoke(plan=_plan(pairs=pairs))
    _assert_nothing_read(source_tree)


def test_a_grant_that_does_not_cover_the_plan_stops_before_any_read(
    source_tree: Path, guards_installed: object
) -> None:
    narrow = _grant(authorization.OPERATION_HISTORICAL_READ, span_end_utc="2025-06-30")
    with pytest.raises(r1_orchestrator.R1OrchestratorError, match="does not cover"):
        _invoke(read_grant=narrow)
    _assert_nothing_read(source_tree)


def test_a_grant_for_the_wrong_operation_stops_before_any_read(
    source_tree: Path, guards_installed: object
) -> None:
    """A read grant does not authorise a derivation, and neither covers the other."""
    swapped = _grant(authorization.OPERATION_HISTORICAL_READ)
    with pytest.raises(r1_orchestrator.R1OrchestratorError, match="does not authorise a derivat"):
        _invoke(derivation_grant=swapped)
    _assert_nothing_read(source_tree)


def test_missing_isolation_stops_before_any_read(source_tree: Path) -> None:
    """No `guards_installed` fixture here: the guards are genuinely absent."""
    assert not isolation.is_installed()
    with pytest.raises(r1_orchestrator.R1OrchestratorError, match="isolation guards"):
        _invoke()
    _assert_nothing_read(source_tree)


def test_the_playbook_checklist_is_complete_at_this_head() -> None:
    """§5a's completeness, verified **outside** the gated surface.

    `preflight` deliberately does not open this file. The first drafting did, and
    `containment.audit()` reported `TRACK_A_EXECUTION_CONTAINMENT_PROBE_FAILED`
    at once: `_check_single_read_route` sweeps every module in the package for a
    file-opening call, and `read_text()` is one. Silencing it would have meant
    adding the orchestrator to `_PERMITTED_FILE_OPENERS` — widening the declared
    read surface to check a document.

    So the obligation lives here, where it costs no exemption and still fails the
    build. This is the same shape the grant record uses for the ancestry check:
    "a gate-time reviewer obligation, not an in-process check — git is
    unreachable from inside a gated read".
    """
    ticked, unticked = _checklist_counts()
    assert ticked + unticked == r1_orchestrator.PREFLIGHT_CHECKLIST_ITEMS, (ticked, unticked)


def _checklist_counts() -> tuple[int, int]:
    playbook = scratch.repo_root() / r1_orchestrator.PLAYBOOK_RELATIVE
    text = playbook.read_text(encoding="utf-8")
    assert text.count(r1_orchestrator.PREFLIGHT_CHECKLIST_HEADING) == 1
    after = text.split(r1_orchestrator.PREFLIGHT_CHECKLIST_HEADING, 1)[1]
    section = after.split("\n## ", 1)[0]
    return section.count("\n- [x] "), section.count("\n- [ ] ")


def test_the_two_grant_rows_are_ticked_only_when_the_grants_actually_validate() -> None:
    """The tick may not run ahead of the fact. This is the fix for a real defect.

    An earlier revision of this PR left §5a's two grant rows ticked and saying
    the grants were "currently in force" and "accepted by `require_authorization`
    on this tree", with the correction eighty lines below — while a review role
    measured a refusal. Worse, the CI check added alongside it counted tick marks
    and therefore *required* the false state: un-ticking to tell the truth broke
    the build.

    Counting ticks cannot detect that, so this ties the two rows to the thing
    they claim. **15 of 15 is permitted only when the recorded grants are
    actually accepted at this head**; while either is refused, exactly two rows
    must be outstanding. Whichever way the head moves, the record and the
    measurement have to agree before the build is green.
    """
    from scripts.m15_gate3a.pair_authority import PAIRS_20 as UNIVERSE
    from scripts.m15_track_a import oos_slice

    document = (
        scratch.repo_root() / "docs" / "governance" / "m15_track_a_r1_dual_grants_reissued.md"
    )
    pattern = r"^\| \*\*approved_implementation_fingerprint\*\* \| `([0-9a-f]{64})` \|$"
    recorded = re.findall(pattern, document.read_text(encoding="utf-8"), re.MULTILINE)
    assert len(recorded) == 2, recorded

    head = "c2cdea03186f2a6e0f7ee394a0a039a24ef1a903"
    operations = (
        authorization.OPERATION_HISTORICAL_READ,
        authorization.OPERATION_M15_DERIVATION,
    )
    accepted = 0
    for fingerprint, operation in zip(recorded, operations, strict=True):
        grant = authorization.ReadGrant(
            operation=operation,
            span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
            span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
            pairs=tuple(sorted(UNIVERSE)),
            timeframe="M1",
            approved_head_sha=head,
            approved_implementation_fingerprint=fingerprint,
            approver_record="checklist correspondence check",
        )
        try:
            authorization.require_authorization(
                grant,
                operation=operation,
                span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
                span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
                pairs=tuple(sorted(UNIVERSE)),
                timeframe="M1",
                identity=_run(code_sha=head),
            )
        except authorization.AuthorizationError:
            continue
        accepted += 1

    _, unticked = _checklist_counts()
    if accepted == 2:
        assert unticked == 0, (
            "both recorded grants validate at this head, so §5a's two grant rows should be "
            f"ticked, and {unticked} row(s) are outstanding."
        )
    else:
        assert unticked == 2, (
            f"{2 - accepted} recorded grant(s) are refused at this head, so §5a's two grant "
            f"rows must be outstanding — {unticked} are. A ticked row naming a grant that "
            "`require_authorization` refuses is the record running ahead of the fact."
        )


def test_the_recorded_reissue_fingerprint_is_the_measured_one() -> None:
    """The value a human is told to re-issue against must be the value that runs.

    Recorded in `m15_track_a_r1_dual_grants_reissued.md` so nobody has to
    rediscover it — and pinned here because a docstring edit to any surface file
    moves the fingerprint, which is exactly how the first attempt at recording it
    went stale within the same session.
    """
    document = (
        scratch.repo_root() / "docs" / "governance" / "m15_track_a_r1_dual_grants_reissued.md"
    )
    text = document.read_text(encoding="utf-8")
    match = re.search(r"The value to re-issue against.{0,200}?\*\*`([0-9a-f]{64})`\*\*", text, re.S)
    assert match, "the re-issue fingerprint is not where the parser expects it"
    assert match.group(1) == containment.implementation_fingerprint()


def test_the_orchestrator_module_opens_no_file() -> None:
    """The property that made the checklist an obligation rather than a check.

    Scoped to **this module's own AST**, and named that way after a review role
    pointed out that the earlier name — "preflight opens no file at all" —
    claimed more than the check establishes: `preflight` calls
    `containment.audit()` and `implementation_fingerprint()`, which parse and
    hash every file on the declared surface. No *market-data* file is opened,
    which is the property that matters and which `containment.audit()` enforces
    for the whole package.
    """
    tree = ast.parse(Path(r1_orchestrator.__file__).read_text(encoding="utf-8"))
    readers = {"open", "read_text", "read_bytes", "load", "loads", "iterdir", "glob", "rglob"}
    called = {
        getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert not (called & readers), sorted(called & readers)


def test_an_unwritable_ledger_root_stops_before_any_read(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A run that cannot record what it read must not read."""
    monkeypatch.setattr(scratch, "ledger_root", lambda: tmp_path / "nowhere" / "ledger")
    with pytest.raises(Exception):  # noqa: B017 - scratch or ledger refusal
        _invoke()
    _assert_nothing_read(source_tree)


# ---------------------------------------------------------------------------
# A failed stage stops the sequence
# ---------------------------------------------------------------------------


def test_a_failed_derivation_does_not_reach_the_survey(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    reached: list[str] = []
    monkeypatch.setattr(
        derivation,
        "derive_m15",
        lambda *a, **kw: (_ for _ in ()).throw(derivation.DerivationRouteError("refused")),
    )
    monkeypatch.setattr(
        r1_survey,
        "survey",
        lambda *a, **kw: reached.append("survey"),  # pragma: no cover
    )
    with pytest.raises(derivation.DerivationRouteError):
        _invoke()
    assert not reached, "the survey ran after the derivation refused"


def test_a_failed_survey_produces_no_result_and_no_next_stage(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        r1_survey,
        "survey",
        lambda *a, **kw: (_ for _ in ()).throw(r1_survey.R1SurveyError("refused")),
    )
    with pytest.raises(r1_survey.R1SurveyError):
        _invoke()


def test_a_failed_read_does_not_reach_the_derivation(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Driven by removing the source, not by swapping the read route.

    Replacing `read_route.read_historical` is itself refused — by
    `containment.audit()` in preflight, which is the stronger property and is
    asserted separately below. So the read is made to fail the way a real one
    would: the source is not there.
    """
    reached: list[str] = []
    for pair in PAIRS:
        (
            source_tree
            / "data"
            / read_route.SOURCE_FILENAME_TEMPLATE.format(pair=pair, epoch=EPOCH)
        ).unlink()
    monkeypatch.setattr(
        derivation,
        "derive_m15",
        lambda *a, **kw: reached.append("derive"),  # pragma: no cover
    )
    with pytest.raises(Exception):  # noqa: B017 - the read route's own refusal
        _invoke()
    assert not reached, "the derivation ran after the read refused"


def test_swapping_the_read_route_is_refused_by_the_containment_audit(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real defence against a substituted reader, found while writing these tests.

    A first drafting patched `read_historical` to simulate a failure and got a
    refusal from an unexpected direction: `containment.audit()` compares the
    package's declared read body against what is actually there, so a swapped
    route never reaches the read at all.
    """
    monkeypatch.setattr(
        read_route,
        "read_historical",
        lambda *a, **kw: (_ for _ in ()).throw(read_route.ReadRouteError("refused")),
    )
    with pytest.raises(r1_orchestrator.R1OrchestratorError, match="containment audit"):
        _invoke()
    _assert_nothing_read(source_tree)


def test_a_failed_breadth_record_does_not_reach_the_survey(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """K and the run identity are prerequisites of the survey, not decorations."""
    reached: list[str] = []
    monkeypatch.setattr(
        breadth,
        "record",
        lambda *a, **kw: (_ for _ in ()).throw(breadth.BreadthRecordError("refused")),
    )
    monkeypatch.setattr(
        r1_survey,
        "survey",
        lambda *a, **kw: reached.append("survey"),  # pragma: no cover
    )
    with pytest.raises(breadth.BreadthRecordError):
        _invoke()
    assert not reached


def test_a_derivation_recording_another_run_stops_the_run(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = streaming.derive_streaming

    def relabelled(*a: Any, **kw: Any) -> Any:
        result = real(*a, **kw)
        return derivation.DerivedM15(
            run_id="a-different-run",
            operation=result.operation,
            epoch=result.epoch,
            span_start_utc=result.span_start_utc,
            span_end_utc=result.span_end_utc,
            coverage_status=result.coverage_status,
            bars_by_pair=result.bars_by_pair,
            gap_reports=result.gap_reports,
        )

    monkeypatch.setattr(streaming, "derive_streaming", relabelled)
    with pytest.raises(r1_orchestrator.R1OrchestratorError, match="derivation records run"):
        _invoke()


# ---------------------------------------------------------------------------
# Structure: one request object, no bypass, no next stage
# ---------------------------------------------------------------------------


def test_each_window_hands_one_request_object_to_both_gated_routes(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Building it twice is the failure mode playbook §5a names for a runner.

    Since the bounded-memory route the orchestrator now calls cuts the plan's
    request into windows, the property moved down one level and got stricter:
    **every window** builds one `ReadRequest` and gives that object to both its
    read and its derivation. Asserted by identity, not equality — two equal
    objects are exactly what a later divergence starts from.
    """
    seen: list[int] = []
    real_read = read_route.read_historical
    real_derive = derivation.derive_m15

    def spy_read(request: Any, *a: Any, **kw: Any) -> Any:
        seen.append(("read", id(request)))
        return real_read(request, *a, **kw)

    def spy_derive(request: Any, *a: Any, **kw: Any) -> Any:
        seen.append(("derive", id(request.read_request)))
        return real_derive(request, *a, **kw)

    monkeypatch.setattr(read_route, "read_historical", spy_read)
    monkeypatch.setattr(derivation, "derive_m15", spy_derive)
    #: `containment.audit()` runs its own `grant=None` refusal probe through the
    #: read route, so the spy sees that request too — and the audit refuses a
    #: swapped route, which is asserted on its own elsewhere. Stubbed here to
    #: isolate the property under test: the orchestrator's own two calls are the
    #: last two, and they must be the same object.
    monkeypatch.setattr(containment, "audit", lambda: {"status": containment.STATUS_CONTAINED})
    _invoke()
    #: A window with no rows reads and does not derive, so the two streams are
    #: not one-to-one. Every derivation must be handed the object the read
    #: immediately before it was handed.
    derivations = [index for index, (kind, _) in enumerate(seen) if kind == "derive"]
    assert derivations, "no window derived anything"
    for index in derivations:
        assert seen[index - 1][0] == "read", seen[index - 2 : index + 1]
        assert seen[index][1] == seen[index - 1][1], (
            "a window handed its derivation a different ReadRequest from its read"
        )


def test_a_caller_thread_cannot_split_one_run_across_two_identities(
    source_tree: Path, guards_installed: object
) -> None:
    """R-1, and it needed no monkeypatch to find.

    A review role started a plain caller-side thread that flipped `run_id` once
    the ledger file appeared. The run completed and the **irreversible**
    seen-data entry said one run while the breadth entry, both grant-ledger rows,
    the survey and the result said another. The post-stage checks did not catch
    it because they compared against the mutated identity.

    Driven deterministically here — the mutation happens inside the delegate,
    the one point a caller regains control — because a timing race would test
    the scheduler instead of the snapshot.
    """
    run = _run()
    real_derive = derivation.derive_m15

    def rename_then_derive(*a: Any, **kw: Any) -> Any:
        #: after the seen declaration and the read, before the breadth record —
        #: the window in which the audit's repro split the run in two.
        object.__setattr__(run, "run_id", "a-different-run")
        return real_derive(*a, **kw)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(derivation, "derive_m15", rename_then_derive)
        result = _invoke(identity=run)

    assert result.run_id == "r1-orchestrator-synthetic"
    assert result.survey.run_id == "r1-orchestrator-synthetic"
    recorded = (
        {entry.run_id for entry in seen_ledger.read_declarations()}
        | {entry.run_id for entry in breadth.read_entries()}
        | {result.run_id, result.survey.run_id}
    )
    assert recorded == {"r1-orchestrator-synthetic"}, recorded


def test_the_survey_records_the_containment_status_that_was_measured(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Not a constant. A mutant replaced it with an arbitrary string and survived.

    `run_r1` passed `containment.STATUS_CONTAINED` rather than what
    `containment.audit()` returned, so the survey's containment field was a
    literal the run could not contradict.
    """
    measured = f"{containment.STATUS_CONTAINED}_MEASURED_HERE"
    monkeypatch.setattr(containment, "STATUS_CONTAINED", measured)
    monkeypatch.setattr(containment, "audit", lambda: {"status": measured})
    result = _invoke()
    assert result.preflight.containment_status == measured
    assert result.survey.containment == measured or measured in str(result.survey.containment)


def test_a_derivation_covering_other_pairs_stops_the_run(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The post-derivation scope check, which a mutation audit found unverified."""
    real = streaming.derive_streaming

    def narrowed(*a: Any, **kw: Any) -> Any:
        result = real(*a, **kw)
        bars = dict(result.bars_by_pair)
        bars.pop(PAIRS[0])
        return derivation.DerivedM15(
            run_id=result.run_id,
            operation=result.operation,
            epoch=result.epoch,
            span_start_utc=result.span_start_utc,
            span_end_utc=result.span_end_utc,
            coverage_status=result.coverage_status,
            bars_by_pair=bars,
            gap_reports=result.gap_reports,
        )

    monkeypatch.setattr(streaming, "derive_streaming", narrowed)
    with pytest.raises(r1_orchestrator.R1OrchestratorError, match="different pair set"):
        _invoke()


def test_a_survey_recording_another_run_stops_the_run(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = r1_survey.survey

    def relabelled(*a: Any, **kw: Any) -> Any:
        result = real(*a, **kw)
        object.__setattr__(result, "run_id", "a-different-run")
        return result

    monkeypatch.setattr(r1_survey, "survey", relabelled)
    with pytest.raises(r1_orchestrator.R1OrchestratorError, match="survey records run"):
        _invoke()


def test_a_refused_derivation_leaves_no_breadth_entry(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The breadth record's *position* in the sequence, which was unpinned.

    A mutant moved it above the derivation and survived: nothing observed that a
    refused derivation must leave `K` untouched.
    """
    monkeypatch.setattr(
        derivation,
        "derive_m15",
        lambda *a, **kw: (_ for _ in ()).throw(derivation.DerivationRouteError("refused")),
    )
    with pytest.raises(derivation.DerivationRouteError):
        _invoke()
    assert not breadth.read_entries(), "a refused derivation recorded breadth K"


def test_a_plan_subclass_is_refused(source_tree: Path, guards_installed: object) -> None:
    """The plan type pin, which a mutation audit found untested."""

    class Sneaky(r1_orchestrator.R1Plan):
        pass

    with pytest.raises(r1_orchestrator.R1OrchestratorError, match="exactly an R1Plan"):
        _invoke(plan=Sneaky(span_start_utc=SPAN_START, span_end_utc=SPAN_END, pairs=PAIRS))


def test_a_str_subclass_pair_is_refused_at_the_plan_boundary() -> None:
    """Every other boundary in this package pins `type(x) is str`; this one did not."""

    class Sneaky(str):
        pass

    with pytest.raises(r1_orchestrator.R1OrchestratorError, match="malformed pair"):
        r1_orchestrator.R1Plan(
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=(Sneaky("EUR_USD"), *PAIRS[1:]),
        )


def test_the_orchestrator_never_calls_the_aggregator_directly() -> None:
    """The bypass `derivation_containment` exists to close is not reopened here.

    Checked on the AST rather than by name-in-source: a module that imported the
    aggregator under an alias would pass a substring sweep.
    """
    tree = ast.parse(Path(r1_orchestrator.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    assert not any("aggregation" in name for name in imported), sorted(imported)
    assert not any("derivation_containment" in name for name in imported), sorted(imported)
    called = {
        getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert "aggregate_m15" not in called
    assert "authorised_derivation_window" not in called


def test_no_next_stage_is_reachable_from_the_orchestrator() -> None:
    """R2, the OOS read, strategy search and Formal Confirmation, by construction.

    `oos_budget` is the module a slice read would need; importing it is what
    "reaching R2" would look like in a diff.
    """
    tree = ast.parse(Path(r1_orchestrator.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            for alias in node.names:
                imported.add(f"{node.module}.{alias.name}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
    for forbidden in ("oos_budget", "train", "lgbm", "sklearn", "model", "strategy", "broker"):
        assert not any(forbidden in name for name in imported), (forbidden, sorted(imported))


def test_the_declared_call_surface_is_exactly_the_committed_stages() -> None:
    """Every first-party call the module makes, against a declared list.

    A new call to something outside this list is a new route, and a new route is
    what this module exists to prevent.
    """
    tree = ast.parse(Path(r1_orchestrator.__file__).read_text(encoding="utf-8"))
    permitted = {
        # the committed stages
        "derive_streaming",
        "survey",
        "declare",
        "record",
        "current_k",
        "audit",
        # scope and guards
        "assert_span_admissible",
        "assert_development_only",
        "assert_writable",
        "is_installed",
        "is_writable",
        "canonical_pair",
        #: the module-level function, never the overridable ``grant.covers`` method
        "grant_covers",
        # this module's own helpers and constructors
        "_refuse",
        "_canonical_pairs",
        "preflight",
        "note",
        "ReadRequest",
        "RunIdentity",
        "SeenDeclaration",
        "ConfigurationEntry",
        "VerifiedRunContext",
        "PreflightReport",
        "R1Result",
        "R1OrchestratorError",
        # plain builtins and stdlib
        "str",
        "type",
        "len",
        "set",
        "sorted",
        "tuple",
        "get",
        "strip",
        "ledger_path",
        "grant_ledger_path",
        "breadth_path",
        "scratch_root",
        "ledger_root",
        # dataclass machinery and plain builtins
        "dataclass",
        "field",
        "isinstance",
        "append",
        "as_record",
    }
    called = {
        getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    } - {None}
    unexpected = called - permitted
    assert not unexpected, f"the orchestrator calls something undeclared: {sorted(unexpected)}"
    #: And the allowlist must not out-live what it permits. A review role found
    #: it still authorising `read_text`, `is_file`, `repo_root` and a helper that
    #: no longer exists — leftovers from the draft that read the playbook — so an
    #: injected file read using only permitted names kept this test green.
    stale = permitted - called
    assert not stale, f"the allowlist permits names the module never calls: {sorted(stale)}"


def test_the_orchestrator_has_no_try_except_in_the_sequence() -> None:
    """A refusal is the answer, not an exception to recover from.

    A `try` around a stage is how "the read failed but we carried on" gets
    written, so the module carries none.
    """
    tree = ast.parse(Path(r1_orchestrator.__file__).read_text(encoding="utf-8"))
    for function in (r1_orchestrator.run_r1, r1_orchestrator.preflight):
        node = next(
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == function.__name__
        )
        assert not [n for n in ast.walk(node) if isinstance(n, ast.Try)], function.__name__


def test_preflight_opens_no_file_under_the_source_root(
    source_tree: Path, guards_installed: object
) -> None:
    """Preflight is the stage whose refusals are free, so it must stay free."""
    report = r1_orchestrator.preflight(
        _plan(),
        _run(),
        read_grant=_grant(authorization.OPERATION_HISTORICAL_READ),
        derivation_grant=_grant(authorization.OPERATION_M15_DERIVATION),
    )
    assert report.status == r1_orchestrator.PREFLIGHT_PASSED
    assert not seen_ledger.read_declarations()
    assert not breadth.read_entries()
    assert report.request.pairs == PAIRS
    assert report.request.timeframe == "M1"
    assert report.fingerprint == containment.implementation_fingerprint()
