"""Stage R1, end to end, on **synthetic data only**.

`TRACK_A_R1_END_TO_END_SYNTHETIC_DRY_RUN_PASSED` is what this file establishes,
and the reason it exists is that the first R1 execution command had to be
refused: the route had no derivation body, no calendar, no survey and no
committed ledger, and none of that was visible until someone tried to run it.
A dry run that exercises the **same control path** as the real thing is how that
stops being discoverable only at execution time.

**No test here touches real market data.** Every case writes synthetic JSONL
into a temporary tree and repoints `source_path_for` at it. `data/` is never
opened — and, since these rows come from a temp tree rather than the committed
data root, they carry no real-provenance marker and set no process latch, which
is the property that keeps the aggregation tests around them working.

The path exercised is the whole one:

    grant → read_historical → real/synthetic provenance decision
          → derive_m15 (authorised window) → aggregate_m15 + Calendar A
          → r1_survey.survey → Calendar B eligibility → T-3 → ledgers → K
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.m15_gate3a import derivation_containment as dc
from scripts.m15_track_a import (
    authorization,
    breadth,
    containment,
    derivation,
    identity,
    isolation,
    oos_slice,
    r1_survey,
    read_route,
    scratch,
    seen_ledger,
)

EPOCH = read_route.SOURCE_EPOCH
PAIRS = ("EUR_USD", "USD_JPY")
# A short window inside the authorised development corpus. Short on purpose:
# the dry run is about the control path, not about volume.
SPAN_START = "2025-05-05"  # a Monday
SPAN_END = "2025-05-09"  # the Friday of the same week
APPROVED_SHA = "a" * 40


# ---------------------------------------------------------------------------
# Fixtures — synthetic everything
# ---------------------------------------------------------------------------


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch root, a ledger root and a synthetic source tree, all temporary."""
    for name in ("track_a_scratch", "data"):
        (tmp_path / name).mkdir()
    # Only the scratch root is repointed. ``ledger_root()`` derives from it, so
    # patching both would let the two drift apart in the fixture and hide a
    # relocation bug in the code -- which is exactly what happened once.
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
def guards_installed() -> object:
    isolation.install_all()
    try:
        yield
    finally:
        isolation.uninstall_all()


def _write_minutes(sandbox: Path, pair: str, *, start: str, end: str) -> Path:
    """One M1 bid/ask row per minute across the span, in the committed shape.

    A gentle sawtooth so the ATR is non-degenerate: a flat series gives a zero
    true range, a zero ATR and no eligible bar, which would let the survey
    report "nothing eligible" for a reason that is an artefact of the fixture.

    **Every minute of the span is written, with no market-hours filter.** The
    first drafting filtered the fixture through the same ``in_fx_week``
    predicate the calendar used, so the two agreed by construction and could not
    disagree — which is how an invented and factually wrong week boundary passed
    twenty-seven tests. There is no calendar now, and no predicate to agree
    with: the fixture is minutes, and the session/rollover predicates are
    checked against a hand-written oracle in
    ``tests/m15_gate3a/test_session_windows_independent_oracle.py``.
    """
    path = sandbox / "data" / read_route.SOURCE_FILENAME_TEMPLATE.format(pair=pair, epoch=EPOCH)
    jpy = pair.endswith("_JPY")
    base = 150.0 if jpy else 1.1000
    tick = 0.01 if jpy else 0.0001
    moment = datetime.fromisoformat(start).replace(tzinfo=UTC)
    stop = datetime.fromisoformat(end).replace(tzinfo=UTC) + timedelta(days=1)
    index = 0
    with path.open("w", encoding="utf-8") as handle:
        while moment < stop:
            swing = (index % 40) - 20
            mid = base + swing * tick
            half = tick  # a 2-tick quoted spread
            row = {
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
            handle.write(json.dumps(row) + "\n")
            moment += timedelta(minutes=1)
            index += 1
    return path


def _run(code_sha: str = APPROVED_SHA) -> identity.RunIdentity:
    return identity.RunIdentity(
        run_id="r1-dry-run",
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
        "approver_record": "synthetic dry-run grant, not a recorded approval",
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
        "purpose": "synthetic R1 dry run",
    }
    fields.update(overrides)
    seen_ledger.declare(seen_ledger.SeenDeclaration(**fields), run)  # type: ignore[arg-type]


@pytest.fixture
def dry_run(sandbox: Path, guards_installed: object) -> dict:
    """The whole R1 control path, once, so the cases below can assert on it."""
    for pair in PAIRS:
        _write_minutes(sandbox, pair, start=SPAN_START, end=SPAN_END)
    run = _run()
    _declare(run)
    read = read_route.read_historical(
        _request(), run, grant=_grant(authorization.OPERATION_HISTORICAL_READ)
    )
    derived = derivation.derive_m15(
        derivation.DerivationRequest(read_request=_request(), read=read),
        run,
        grant=_grant(authorization.OPERATION_M15_DERIVATION),
    )
    breadth.record(
        breadth.ConfigurationEntry(
            run_id=run.run_id,
            axes={axis: "r1_survey_no_configuration" for axis in breadth.CONFIGURATION_AXES},
            result_observed=False,
            note=(
                "R1 is a survey, not a configuration: no model, no features, no "
                "threshold. Recorded so K is explicit rather than absent, and with "
                "result_observed=False because nothing was scored."
            ),
        ),
        run,
    )
    result = r1_survey.survey(
        derived,
        containment_status=containment.STATUS_CONTAINED,
        breadth_k=breadth.current_k(),
    )
    return {"read": read, "derived": derived, "survey": result, "run": run}


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_the_whole_path_completes(dry_run: dict) -> None:
    """grant -> read -> derivation -> Calendar A/B -> survey -> ledger -> K."""
    survey = dry_run["survey"]
    assert survey.pairs == tuple(sorted(PAIRS))
    assert survey.timeframe == "M15"
    assert survey.classification == "NON_DECISION_BEARING_EXPLORATORY_ONLY"
    assert survey.classification_secondary == "RESEARCH_SCRATCH_NON_AUTHORITATIVE"


def test_every_required_r1_output_is_present_and_populated(dry_run: dict) -> None:
    """§7's stage table, item by item, asserted rather than assumed."""
    survey = dry_run["survey"]
    record = survey.as_record()
    for pair in survey.pairs:
        assert record["schema"][pair]["bars"] > 0
        assert record["schema"][pair]["first_ts"] and record["schema"][pair]["last_ts"]
        assert "gap_report" in record["coverage"][pair]
        for session in ("asia", "europe", "us"):
            spread = record["spread_distribution"][pair][session]
            assert spread["n"] > 0
            assert spread["median_pip"] is not None
            assert spread["p90_pip"] is not None
            assert spread["p95_pip"] is not None
            assert record["cost_table"][pair][session] is not None
            assert record["eligibility"][pair][session]["eligible_rate"] is not None
    # All three barrier readings are reported, unranked, with no verdict.
    for name in ("pre_floor_tp", "post_floor_tp", "post_floor_sl"):
        variant = record["barrier_cost_ratio"]["variants"][name]
        assert variant["n"] > 0
        assert variant["median"] is not None
    # No calendar authority, so the calendar-derived accounting is absent --
    # reported as absent rather than filled in.
    # No calendar authority, so the calendar-derived fields are absent --
    # reported as absent rather than filled in. The observed fields are present.
    accounting = record["coverage"]["EUR_USD"]["gap_report"]["minute_accounting"]
    assert accounting["expected_source_minute_count"] is None
    assert accounting["absent_source_minute_count"] is None
    assert accounting["observed_source_minute_count"] > 0
    # K is **zero**, and that is the correct answer rather than a missing one.
    # `current_k` counts configurations "whose result was observed", and R1
    # observes no result: it measures the corpus, it scores nothing. The entry
    # is on the breadth ledger for the audit trail with result_observed=False,
    # so K is explicit at 0 rather than simply absent.
    assert record["accounting"]["breadth_k"] == 0
    assert breadth.read_entries(), "no breadth entry was recorded at all"


def test_the_derivation_records_that_coverage_has_no_authority(dry_run: dict) -> None:
    """No approved calendar exists, so the derivation says so rather than pretending.

    `PRE_CONTINUATION_CALENDAR_ARTIFACT_APPROVAL_REQUIRED` is open, D-6 forbids
    an implementer authoring a calendar, and omega-12 forbids Track A authoring
    market hours. The aggregator's calendar-derived accounting therefore comes
    back ``None`` -- and that is reported, not filled in.
    """
    derived = dry_run["derived"]
    assert derived.coverage_status == (
        "COVERAGE_AUTHORITY_ABSENT_R1_REPORTS_A_DECLARED_LABEL_DIAGNOSTIC"
    )
    for report in derived.gap_reports.values():
        assert report["minute_accounting"]["expected_source_minute_count"] is None


def test_the_survey_reaches_no_t3_verdict(dry_run: dict) -> None:
    """T-3 is a later-stage duty (D-3/D-4); R1 reports and does not decide."""
    ratio = dry_run["survey"].barrier_cost_ratio
    assert ratio["numerator_ruling"] == "UNRULED_ALL_THREE_READINGS_REPORTED"
    assert set(ratio["variants"]) == set(r1_survey.BARRIER_VARIANTS)
    assert "t3_status" not in ratio
    assert "threshold" not in ratio
    text = json.dumps(dry_run["survey"].as_record())
    assert "T3_MEDIAN" not in text, "R1 emitted a T-3 verdict"


def test_the_ledgers_are_written_under_the_committed_root(dry_run: dict) -> None:
    """§8.13.5 items 5 and 6: committed, not scratch."""
    assert seen_ledger.ledger_path().is_file()
    assert seen_ledger.grant_ledger_path().is_file()
    assert breadth.breadth_path().is_file()
    assert seen_ledger.ledger_path().parent == scratch.ledger_root()
    assert scratch.ledger_root() != scratch.scratch_root()


def test_the_declaration_precedes_the_read(dry_run: dict) -> None:
    entries = seen_ledger.read_declarations()
    assert entries, "nothing was declared"
    assert any(entry.span_start_utc == SPAN_START for entry in entries)


def test_rollover_bars_are_excluded_from_eligibility(dry_run: dict) -> None:
    """Ruling 4's 21:55-22:15 window, at the committed minimum."""
    # The predicate itself is checked against a hand-written oracle in
    # tests/m15_gate3a/test_session_windows_independent_oracle.py. Here we only
    # assert that the survey *applied* it.
    counted = sum(
        session["bars_considered"]
        for pair in dry_run["survey"].pairs
        for session in dry_run["survey"].eligibility[pair].values()
    )
    total = sum(len(bars) for bars in dry_run["derived"].bars_by_pair.values())
    assert counted < total, "no bar was excluded, so Calendar B did nothing"


def test_the_survey_record_carries_no_bar(dry_run: dict) -> None:
    """A metadata record: statistics travel, bars do not.

    Judged **structurally**. The first drafting asserted the string ``bid_o``
    was absent and failed on the schema section, which lists the key *names* —
    which R1 is required to report. A substring sweep cannot tell a column name
    from a price; walking the record can.
    """
    record = dry_run["survey"].as_record()

    def walk(node: object, path: str = "") -> None:
        if isinstance(node, dict):
            assert "ts" not in node, f"a bar-shaped object at {path}"
            for key, value in node.items():
                walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{path}[{index}]")

    walk(record)
    assert all(isinstance(k, str) for k in record["schema"]["EUR_USD"]["keys"])
    assert isinstance(record["schema"]["EUR_USD"]["bars"], int)


def test_no_real_data_was_read(dry_run: dict) -> None:
    """The dry run is synthetic, and the latch proves it."""
    assert not dc.real_rows_handed_out()
    for rows in dry_run["read"].rows_by_pair.values():
        assert not any(dc.is_real_row(row) for row in rows)


# ---------------------------------------------------------------------------
# The required negative tests
# ---------------------------------------------------------------------------


def test_a_derivation_without_its_own_grant_is_refused(
    sandbox: Path, guards_installed: object
) -> None:
    for pair in PAIRS:
        _write_minutes(sandbox, pair, start=SPAN_START, end=SPAN_END)
    run = _run()
    _declare(run)
    read = read_route.read_historical(
        _request(), run, grant=_grant(authorization.OPERATION_HISTORICAL_READ)
    )
    request = derivation.DerivationRequest(read_request=_request(), read=read)
    with pytest.raises(authorization.AuthorizationError):
        derivation.derive_m15(request, run, grant=_grant(authorization.OPERATION_HISTORICAL_READ))
    with pytest.raises(authorization.AuthorizationError):
        derivation.derive_m15(request, run, grant=None)


def test_a_direct_aggregate_m15_bypass_is_refused() -> None:
    """The measured hole: real rows aggregated without entering derive_m15."""
    from scripts.m15_gate3a.aggregation import aggregate_m15

    row = dc.stamp_real_provenance({"ts": None})
    with pytest.raises(dc.DerivationContainmentError):
        aggregate_m15([row], pair="EUR_USD")


def test_the_bypass_guard_does_not_block_the_authorised_route() -> None:
    """The same call, inside the window the authorised route opens."""
    from scripts.m15_gate3a.aggregation import aggregate_m15

    with dc.authorised_derivation_window():
        bars, _ = aggregate_m15([], pair="EUR_USD")
    assert bars == []


@pytest.mark.parametrize(
    "start,end",
    [
        (oos_slice.SLICE_START_UTC, oos_slice.SLICE_END_UTC),
        ("2026-03-01", "2026-03-05"),
        ("2026-04-25", "2026-04-30"),
    ],
    ids=["oos-slice", "dead-window", "forward-epoch"],
)
def test_a_span_outside_the_development_corpus_is_refused(start: str, end: str) -> None:
    with pytest.raises(authorization.AuthorizationMalformedError):
        _grant(authorization.OPERATION_HISTORICAL_READ, span_start_utc=start, span_end_utc=end)


def test_a_pair_outside_the_grant_is_refused(sandbox: Path, guards_installed: object) -> None:
    for pair in PAIRS:
        _write_minutes(sandbox, pair, start=SPAN_START, end=SPAN_END)
    run = _run()
    _declare(run, pairs=("EUR_USD", "GBP_USD"))
    with pytest.raises(authorization.AuthorizationError):
        read_route.read_historical(
            _request(pairs=("EUR_USD", "GBP_USD")),
            run,
            grant=_grant(authorization.OPERATION_HISTORICAL_READ),
        )


def test_a_timeframe_outside_the_route_is_refused(sandbox: Path, guards_installed: object) -> None:
    """M15 does not exist until the derivation runs; the read route says so."""
    for pair in PAIRS:
        _write_minutes(sandbox, pair, start=SPAN_START, end=SPAN_END)
    run = _run()
    _declare(run, timeframe="M15")
    with pytest.raises(read_route.ReadRouteError, match="M15 does not exist"):
        read_route.read_historical(
            _request(timeframe="M15"),
            run,
            grant=_grant(authorization.OPERATION_HISTORICAL_READ, timeframe="M15"),
        )


def test_an_undeclared_interval_is_refused(sandbox: Path, guards_installed: object) -> None:
    for pair in PAIRS:
        _write_minutes(sandbox, pair, start=SPAN_START, end=SPAN_END)
    with pytest.raises(seen_ledger.SeenLedgerError):
        read_route.read_historical(
            _request(), _run(), grant=_grant(authorization.OPERATION_HISTORICAL_READ)
        )


def test_a_fingerprint_mismatch_is_refused(sandbox: Path, guards_installed: object) -> None:
    for pair in PAIRS:
        _write_minutes(sandbox, pair, start=SPAN_START, end=SPAN_END)
    run = _run()
    _declare(run)
    with pytest.raises(authorization.AuthorizationError, match="implementation"):
        read_route.read_historical(
            _request(),
            run,
            grant=_grant(
                authorization.OPERATION_HISTORICAL_READ,
                approved_implementation_fingerprint="b" * 64,
            ),
        )


def test_a_write_outside_the_permitted_roots_is_refused() -> None:
    for forbidden in ("data/x.jsonl", "docs/x.md", "artifacts/m15_gate3a/x.json"):
        assert not scratch.is_writable(scratch.repo_root() / forbidden)
    assert scratch.is_writable(scratch.ledger_root() / "exploratory_seen_ledger.jsonl")


def test_the_survey_refuses_anything_but_an_authorised_derivation() -> None:
    """A dict of bars is not a DerivedM15, and the survey will not measure one."""
    with pytest.raises(r1_survey.R1SurveyError):
        r1_survey.survey({"EUR_USD": []})  # type: ignore[arg-type]


def test_the_guards_must_be_installed(sandbox: Path) -> None:
    with pytest.raises(read_route.ReadRouteError, match="isolation"):
        read_route.read_historical(
            _request(), _run(), grant=_grant(authorization.OPERATION_HISTORICAL_READ)
        )


def test_network_db_and_broker_stay_refused(guards_installed: object) -> None:
    """Unchanged by any of this, and asserted so a regression is loud."""
    import socket

    with pytest.raises(isolation.IsolationError):
        socket.socket().connect(("93.184.216.34", 80))
