"""The defences a mutation survey found unfalsifiable, each given a killer.

A review role mutated twenty-one behaviours and ran the whole `m15` suite
against each. **Eight survived**: the code was right and nothing would have
noticed if it stopped being. Every case below exists to kill one of those
mutants, and each docstring names the mutation it answers so the pairing stays
legible if one is ever deleted.

**No test here touches real market data.** The provenance cases point
`scratch.repo_root` at a temporary tree and write synthetic JSONL into the
`data/` directory *inside it*, which is what exercises the real branch without
a real byte. `C:\\...\\fx-ai-trading\\data` is never opened.
"""

from __future__ import annotations

import asyncio
import json
import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.m15_gate3a import derivation_containment as dc
from scripts.m15_gate3a.aggregation import aggregate_m15
from scripts.m15_track_a import (
    authorization,
    containment,
    derivation,
    identity,
    isolation,
    r1_survey,
    read_route,
    scratch,
    seen_ledger,
)

PAIRS = ("EUR_USD", "USD_JPY")
SPAN_START = "2025-05-05"
SPAN_END = "2025-05-06"
APPROVED_SHA = "a" * 40
SIDE_KEYS = read_route.ROW_SIDE_KEYS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A whole fake repository root, so the **real** provenance branch runs.

    `is_committed_source` asks whether the source sits under `<repo>/data`. The
    E2E suite repoints `source_path_for` at a temp tree, so that predicate always
    answered False and the real branch — the one the entire containment module
    exists for — was never executed. Repointing `repo_root` instead means the
    file genuinely is under the data root, and no real byte is involved.
    """
    (tmp_path / "data").mkdir()
    (tmp_path / "artifacts" / "track_a_scratch" / "ledger").mkdir(parents=True)
    monkeypatch.setattr(scratch, "repo_root", lambda: tmp_path)
    return tmp_path


def _write(repo: Path, pair: str, *, minutes: int = 60, drop: set[int] = frozenset()) -> Path:
    path = (
        repo
        / "data"
        / read_route.SOURCE_FILENAME_TEMPLATE.format(pair=pair, epoch=read_route.SOURCE_EPOCH)
    )
    start = datetime.fromisoformat(SPAN_START).replace(tzinfo=UTC)
    with path.open("w", encoding="utf-8") as handle:
        for index in range(minutes):
            if index in drop:
                continue
            moment = start + timedelta(minutes=index)
            mid = 1.1000 + ((index % 40) - 20) * 0.0001
            row = {"time": moment.isoformat().replace("+00:00", "Z")}
            for key in SIDE_KEYS:
                offset = 0.0001 if key.startswith("ask") else -0.0001
                row[key] = mid + offset + (0.0003 if key.endswith("_h") else 0.0)
            handle.write(json.dumps(row) + "\n")
    return path


def _run(code_sha: str = APPROVED_SHA) -> identity.RunIdentity:
    return identity.RunIdentity(
        run_id="falsifiability",
        code_sha=code_sha,
        calendar_semantics=identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        started_at_utc="2026-08-31T00:00:00Z",
    )


def _grant(operation: str, **overrides: object) -> authorization.ReadGrant:
    fields: dict[str, object] = {
        "operation": operation,
        "span_start_utc": SPAN_START,
        "span_end_utc": SPAN_END,
        "pairs": PAIRS,
        "timeframe": "M1",
        "approved_head_sha": APPROVED_SHA,
        "approved_implementation_fingerprint": containment.implementation_fingerprint(),
        "approver_record": "synthetic falsifiability-regression grant",
    }
    fields.update(overrides)
    return authorization.ReadGrant(**fields)  # type: ignore[arg-type]


def _request(**overrides: object) -> read_route.ReadRequest:
    fields: dict[str, object] = {
        "span_start_utc": SPAN_START,
        "span_end_utc": SPAN_END,
        "pairs": PAIRS,
        "timeframe": "M1",
        "warmup_extension_start_utc": SPAN_START,
    }
    fields.update(overrides)
    return read_route.ReadRequest(**fields)  # type: ignore[arg-type]


def _declare(run: identity.RunIdentity, **overrides: object) -> None:
    fields: dict[str, object] = {
        "run_id": run.run_id,
        "span_start_utc": SPAN_START,
        "span_end_utc": SPAN_END,
        "pairs": PAIRS,
        "timeframe": "M1",
        "purpose": "falsifiability regression",
    }
    fields.update(overrides)
    seen_ledger.declare(seen_ledger.SeenDeclaration(**fields), run)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# B-2 — the provenance predicate had no test at all
# ---------------------------------------------------------------------------


def test_a_source_under_the_data_root_is_real(repo: Path) -> None:
    """Kills `P1`: `is_committed_source` forced to False.

    With it always False, no latch is set and no row is marked, so **both**
    containment mechanisms go dark — and the whole suite passed.
    """
    assert read_route.is_committed_source(read_route.source_path_for("EUR_USD"))


def test_a_source_outside_the_data_root_is_synthetic(tmp_path: Path) -> None:
    assert not read_route.is_committed_source(tmp_path / "candles_EUR_USD_M1_365d_BA.jsonl")


def test_an_unresolvable_source_is_treated_as_real() -> None:
    """Fail-closed: guessing "synthetic" leaves an unlatched process holding rows."""
    assert read_route.is_committed_source(Path("\0not-a-path"))


def test_reading_from_the_data_root_marks_the_rows_and_latches_the_process(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real branch, end to end, on synthetic bytes inside a fake data root."""
    monkeypatch.setattr(dc, "_real_rows_handed_out", False, raising=False)
    for pair in PAIRS:
        _write(repo, pair)
    run = _run()
    _declare(run)
    isolation.install_all()
    try:
        result = read_route.read_historical(
            _request(), run, grant=_grant(authorization.OPERATION_HISTORICAL_READ)
        )
    finally:
        isolation.uninstall_all()
    rows = result.rows_by_pair["EUR_USD"]
    assert rows and all(dc.is_real_row(row) for row in rows)
    assert dc.real_rows_handed_out()
    monkeypatch.setattr(dc, "_real_rows_handed_out", False, raising=False)


def test_the_latch_is_set_even_when_the_read_refuses_midway(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kills `P6`: the latch skipped, and the ordering defect it guards.

    A malformed row partway through refuses the read **after** earlier rows
    exist, and those rows are reachable from ``exc.__traceback__`` with the
    marker strippable by a dict copy. The latch must already be set.
    """
    monkeypatch.setattr(dc, "_real_rows_handed_out", False, raising=False)
    for pair in PAIRS:
        path = _write(repo, pair)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"time": "2025-05-05T02:00:00Z", "bid_o": "NOPE"}) + "\n")
    run = _run()
    _declare(run)
    isolation.install_all()
    try:
        with pytest.raises(read_route.ReadRouteError):
            read_route.read_historical(
                _request(), run, grant=_grant(authorization.OPERATION_HISTORICAL_READ)
            )
    finally:
        isolation.uninstall_all()
    assert dc.real_rows_handed_out(), "the read refused after real rows existed, unlatched"
    monkeypatch.setattr(dc, "_real_rows_handed_out", False, raising=False)


def test_a_lying_mapping_is_treated_as_real() -> None:
    """`is_real_row` fails closed; "raise from get" must not be the bypass."""

    class Lying(dict):
        def get(self, *args: object, **kwargs: object) -> object:
            raise RuntimeError("no")

    assert dc.is_real_row(Lying())


# ---------------------------------------------------------------------------
# B-3 — the window's thread/task scoping
# ---------------------------------------------------------------------------


def test_a_sibling_thread_does_not_inherit_the_derivation_window() -> None:
    """Kills `P4`: owner comparison replaced by a presence check."""
    row = dc.stamp_real_provenance({"ts": None})
    outcome: dict[str, str] = {}

    def worker() -> None:
        try:
            aggregate_m15([row], pair="EUR_USD")
            outcome["result"] = "aggregated"
        except dc.DerivationContainmentError:
            outcome["result"] = "refused"
        except Exception:  # noqa: BLE001 - any other refusal is still a refusal
            outcome["result"] = "refused"

    with dc.authorised_derivation_window():
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
    assert outcome["result"] == "refused"


def test_a_child_task_does_not_inherit_the_derivation_window() -> None:
    """A ``ContextVar`` is copied into a child ``Task`` — the owner must be compared."""
    row = dc.stamp_real_provenance({"ts": None})

    async def child() -> str:
        try:
            aggregate_m15([row], pair="EUR_USD")
            return "aggregated"
        except Exception:  # noqa: BLE001
            return "refused"

    async def parent() -> str:
        with dc.authorised_derivation_window():
            return await asyncio.create_task(child())

    assert asyncio.run(parent()) == "refused"


def test_the_window_does_admit_the_thread_that_opened_it() -> None:
    """Kills the vacuous version of this test: an empty list proves nothing.

    ``aggregate_m15([])`` returns ``[]`` **outside** the window too, so the
    original assertion held regardless. A real-provenance row does not.
    """
    row = dc.stamp_real_provenance({"ts": None})
    with pytest.raises(dc.DerivationContainmentError):
        aggregate_m15([row], pair="EUR_USD")
    with dc.authorised_derivation_window(), pytest.raises(Exception) as caught:
        aggregate_m15([row], pair="EUR_USD")
    assert not isinstance(caught.value, dc.DerivationContainmentError)


# ---------------------------------------------------------------------------
# B-3 — the derivation's grant/request intersection
# ---------------------------------------------------------------------------


def test_a_derivation_grant_wider_than_the_request_derives_only_the_request(
    repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Kills `P5`: the loop reverted to `checked.pairs`.

    The read route learned "narrowest wins" twice; the derivation inherited the
    original defect, and no test named a grant wider than its request.
    """
    monkeypatch.setattr(dc, "_real_rows_handed_out", False, raising=False)
    for pair in PAIRS:
        _write(repo, pair)
    run = _run()
    _declare(run, pairs=("EUR_USD",))
    isolation.install_all()
    try:
        read = read_route.read_historical(
            _request(pairs=("EUR_USD",)),
            run,
            grant=_grant(authorization.OPERATION_HISTORICAL_READ),
        )
        derived = derivation.derive_m15(
            derivation.DerivationRequest(read_request=_request(pairs=("EUR_USD",)), read=read),
            run,
            grant=_grant(authorization.OPERATION_M15_DERIVATION),
        )
    finally:
        isolation.uninstall_all()
    assert list(derived.bars_by_pair) == ["EUR_USD"]
    monkeypatch.setattr(dc, "_real_rows_handed_out", False, raising=False)


# ---------------------------------------------------------------------------
# B-3 — the ledger directory's move protection
# ---------------------------------------------------------------------------


def test_the_ledger_directory_cannot_be_renamed_away(repo: Path) -> None:
    """Kills `P7`: `_is_ledger_root_itself` removed.

    Renaming that one directory carried all four governance records out of the
    repository and let `ledger_root()` re-create an empty one.
    """
    scratch.append_line(seen_ledger.ledger_path(), '{"probe": 1}')
    isolation.install_all()
    try:
        with pytest.raises(isolation.IsolationError):
            os.rename(str(scratch.ledger_root()), str(repo / "ledger_moved"))
    finally:
        isolation.uninstall_all()
    assert seen_ledger.ledger_path().is_file()


def test_the_governance_ledgers_are_not_gitignored() -> None:
    """Kills the tautology: the old test compared `ledger_path()` to its own definition.

    "Committed" is a property of `.gitignore`, not of the path expression, and
    §8.13.5 item 5 asks for the former.
    """
    import subprocess

    root = Path(__file__).resolve().parents[2]
    ledger = "artifacts/track_a_scratch/ledger/exploratory_seen_ledger.jsonl"
    research = "artifacts/track_a_scratch/some_research_output.json"
    lock = "artifacts/track_a_scratch/ledger/exploratory_seen_ledger.jsonl.lock"

    def ignored(relative: str) -> bool:
        return (
            subprocess.run(
                ["git", "check-ignore", "-q", relative], cwd=root, capture_output=True
            ).returncode
            == 0
        )

    assert not ignored(ledger), "the seen ledger is gitignored; it must be committable"
    assert ignored(research), "research output is no longer ignored"
    assert ignored(lock), "a committed lock file blocks declarations for 120 s on checkout"


# ---------------------------------------------------------------------------
# B-1 / R-2 — Ruling 3 and the rollover, with a fixture that can fail
# ---------------------------------------------------------------------------


@pytest.fixture
def surveyed(repo: Path, monkeypatch: pytest.MonkeyPatch) -> r1_survey.R1Survey:
    """A survey over bars that include **incomplete** buckets and rollover bars.

    The E2E fixture writes every minute, so every bucket is complete and Ruling
    3 was never exercised: a review role removed both `complete_bucket` guards
    and the entire suite still passed.
    """
    monkeypatch.setattr(dc, "_real_rows_handed_out", False, raising=False)
    # 24 h, dropping three minutes from the 10:00 bucket of each pair.
    dropped = {10 * 60 + 1, 10 * 60 + 2, 10 * 60 + 3}
    for pair in PAIRS:
        _write(repo, pair, minutes=24 * 60, drop=dropped)
    run = _run()
    _declare(run)
    isolation.install_all()
    try:
        read = read_route.read_historical(
            _request(), run, grant=_grant(authorization.OPERATION_HISTORICAL_READ)
        )
        derived = derivation.derive_m15(
            derivation.DerivationRequest(read_request=_request(), read=read),
            run,
            grant=_grant(authorization.OPERATION_M15_DERIVATION),
        )
    finally:
        isolation.uninstall_all()
    monkeypatch.setattr(dc, "_real_rows_handed_out", False, raising=False)
    return r1_survey.survey(derived)


def test_the_fixture_actually_produces_incomplete_buckets(surveyed: r1_survey.R1Survey) -> None:
    """Without this, every assertion below is about a case that never occurs."""
    for pair in surveyed.pairs:
        assert surveyed.coverage[pair]["incomplete_buckets"] == 1
        assert surveyed.coverage[pair]["complete_buckets"] == 95


def test_ruling_3_excludes_incomplete_buckets_from_the_eligible_population(
    surveyed: r1_survey.R1Survey,
) -> None:
    """Kills `M11`: the eligibility guard removed.

    Ruling 3 FROZEN: incomplete buckets "must not create labels or trade
    events". 96 buckets a day, minus 1 incomplete, minus the 2 the rollover
    window overlaps.
    """
    for pair in surveyed.pairs:
        considered = sum(v["bars_considered"] for v in surveyed.eligibility[pair].values())
        assert considered == 96 - 1 - 2


def test_ruling_3_excludes_incomplete_buckets_from_the_spread_population(
    surveyed: r1_survey.R1Survey,
) -> None:
    """Kills `M10`: the `_session_spreads` guard removed.

    An incomplete bucket's closing spread would otherwise enter the median that
    the cost table — and therefore the eligibility hurdle — is built from.
    """
    for pair in surveyed.pairs:
        counted = sum(v["n"] for v in surveyed.spread_distribution[pair].values())
        assert counted == 96 - 1 - 2


def test_the_rollover_exclusion_is_by_overlap_end_to_end(
    surveyed: r1_survey.R1Survey,
) -> None:
    """Kills `M5` at the survey level and `M13` at the spread level.

    Exactly **two** buckets a day overlap 21:55–22:15 — 21:45 and 22:00. A
    start-only test excludes one, and the E2E's `counted < total` assertion
    could not tell the difference.
    """
    for pair in surveyed.pairs:
        considered = sum(v["bars_considered"] for v in surveyed.eligibility[pair].values())
        counted = sum(v["n"] for v in surveyed.spread_distribution[pair].values())
        # 96 buckets, 1 incomplete, 2 rollover: both populations agree at 93.
        assert considered == 93
        assert counted == 93


def test_the_us_session_loses_exactly_the_two_rollover_buckets(
    surveyed: r1_survey.R1Survey,
) -> None:
    """The two exclusions land in different sessions, and only there.

    32 buckets per session. The incomplete 10:00 bucket is in **Europe**
    (08:00-15:59); the 21:45 and 22:00 rollover buckets are in **US**
    (16:00-23:59). Asia keeps all 32, which is what makes this test able to
    fail: a guard applied to the wrong window would move a count.
    """
    for pair in surveyed.pairs:
        assert surveyed.eligibility[pair]["asia"]["bars_considered"] == 32
        assert surveyed.eligibility[pair]["europe"]["bars_considered"] == 31
        assert surveyed.eligibility[pair]["us"]["bars_considered"] == 30
