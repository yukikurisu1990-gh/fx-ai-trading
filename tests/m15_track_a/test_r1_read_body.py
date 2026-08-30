"""R1's minimal historical read body: it reads only what the grant covers.

**No test here touches real market data.** Every case either uses a synthetic
source file written into a temporary tree, or a path that does not exist. The
one committed epoch under `data/` is never opened: `source_path_for` is
repointed at the temporary tree, and the two tests that exercise a refusal use
a pair whose file is deliberately absent.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from scripts.m15_gate3a.no_overlap import DEAD_START, DESIGN_END
from scripts.m15_track_a import (
    authorization,
    containment,
    identity,
    isolation,
    read_route,
    scratch,
    seen_ledger,
)

APPROVED_SHA = "a" * 40
DEV_START = "2025-05-01"
DEV_END = "2025-05-31"


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A scratch root and a synthetic source tree, both outside the repository."""
    root = tmp_path / "track_a_scratch"
    root.mkdir()
    monkeypatch.setattr(scratch, "scratch_root", lambda: root)
    source = tmp_path / "data"
    source.mkdir()
    monkeypatch.setattr(
        read_route,
        "source_path_for",
        lambda pair: (
            source
            / read_route.SOURCE_FILENAME_TEMPLATE.format(pair=pair, epoch=read_route.SOURCE_EPOCH)
        ),
    )
    return source


@pytest.fixture
def guards() -> object:
    isolation.install_all()
    try:
        yield
    finally:
        isolation.uninstall_all()


def _run(code_sha: str = APPROVED_SHA) -> identity.RunIdentity:
    return identity.RunIdentity(
        run_id="r1-read-test",
        code_sha=code_sha,
        calendar_semantics=identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        started_at_utc="2026-01-01T00:00:00Z",
    )


def _grant(**overrides: object) -> authorization.ReadGrant:
    fields: dict[str, object] = {
        "operation": authorization.OPERATION_HISTORICAL_READ,
        "span_start_utc": DEV_START,
        "span_end_utc": DEV_END,
        "pairs": ("EUR_USD",),
        "timeframe": "M1",
        "approved_head_sha": APPROVED_SHA,
        "approver_record": "synthetic test grant",
    }
    fields.update(overrides)
    return authorization.ReadGrant(**fields)  # type: ignore[arg-type]


def _request(**overrides: object) -> read_route.ReadRequest:
    fields: dict[str, object] = {
        "span_start_utc": DEV_START,
        "span_end_utc": DEV_END,
        "pairs": ("EUR_USD",),
        "timeframe": "M1",
        "warmup_extension_start_utc": DEV_START,
    }
    fields.update(overrides)
    return read_route.ReadRequest(**fields)  # type: ignore[arg-type]


def _declare(run: identity.RunIdentity, **overrides: object) -> None:
    fields: dict[str, object] = {
        "run_id": run.run_id,
        "span_start_utc": DEV_START,
        "span_end_utc": DEV_END,
        "pairs": ("EUR_USD",),
        "timeframe": "M1",
        "purpose": "synthetic R1 read test",
    }
    fields.update(overrides)
    seen_ledger.declare(seen_ledger.SeenDeclaration(**fields), run)  # type: ignore[arg-type]


def _write_source(source: Path, pair: str, minutes: list[datetime]) -> Path:
    """A synthetic M1 bid/ask file in the committed shape. Never real data."""
    path = source / read_route.SOURCE_FILENAME_TEMPLATE.format(
        pair=pair, epoch=read_route.SOURCE_EPOCH
    )
    with path.open("w", encoding="utf-8") as handle:
        for index, minute in enumerate(minutes):
            bid = 1.1000 + index * 0.0001
            handle.write(
                json.dumps(
                    {
                        "time": minute.isoformat().replace("+00:00", "Z"),
                        "bid_o": bid,
                        "bid_h": bid + 0.0002,
                        "bid_l": bid - 0.0002,
                        "bid_c": bid + 0.0001,
                        "ask_o": bid + 0.0001,
                        "ask_h": bid + 0.0003,
                        "ask_l": bid - 0.0001,
                        "ask_c": bid + 0.0002,
                    }
                )
                + "\n"
            )
    return path


# ---------------------------------------------------------------------------
# Refusals — every one of these is a gate, and each fails closed
# ---------------------------------------------------------------------------


def test_no_grant_is_refused(sandbox: Path, guards: object) -> None:
    with pytest.raises(authorization.AuthorizationError, match=authorization.TOKEN):
        read_route.read_historical(_request(), _run(), grant=None)


def test_a_wrong_approved_head_sha_is_refused(sandbox: Path, guards: object) -> None:
    """An approval covers the head it names; a head change voids it."""
    with pytest.raises(authorization.AuthorizationError, match="head"):
        read_route.read_historical(_request(), _run(code_sha="c" * 40), grant=_grant())


def test_a_pair_outside_the_grant_is_refused(sandbox: Path, guards: object) -> None:
    run = _run()
    _declare(run, pairs=("EUR_USD", "USD_JPY"))
    with pytest.raises(authorization.AuthorizationError):
        read_route.read_historical(
            _request(pairs=("EUR_USD", "USD_JPY")), run, grant=_grant(pairs=("EUR_USD",))
        )


def test_a_timeframe_outside_the_grant_is_refused(sandbox: Path, guards: object) -> None:
    with pytest.raises(authorization.AuthorizationError):
        read_route.read_historical(_request(timeframe="M15"), _run(), grant=_grant())


def test_an_m15_grant_cannot_drive_the_m1_source_route(sandbox: Path, guards: object) -> None:
    """M15 does not exist until the derivation runs; a grant naming it describes nothing here."""
    run = _run()
    _declare(run, timeframe="M15")
    with pytest.raises(read_route.ReadRouteError, match="M15 does not exist"):
        read_route.read_historical(_request(timeframe="M15"), run, grant=_grant(timeframe="M15"))


@pytest.mark.parametrize(
    ("label", "start", "end"),
    [
        ("one day before the grant", "2025-04-30", DEV_END),
        ("one day after the grant", DEV_START, "2025-06-01"),
        ("wholly outside the grant", "2025-08-01", "2025-08-31"),
    ],
)
def test_a_span_escape_is_refused(
    sandbox: Path, guards: object, label: str, start: str, end: str
) -> None:
    """Coverage is containment, not overlap."""
    run = _run()
    _declare(run, span_start_utc=start, span_end_utc=end)
    with pytest.raises(authorization.AuthorizationError):
        read_route.read_historical(
            _request(span_start_utc=start, span_end_utc=end, warmup_extension_start_utc=start),
            run,
            grant=_grant(),
        )


def test_a_warmup_reaching_outside_the_grant_is_refused(sandbox: Path, guards: object) -> None:
    """Warm-up widens the interval a run touches, and the grant must cover the widened one."""
    run = _run()
    _declare(run, span_start_utc="2025-04-25")
    with pytest.raises(authorization.AuthorizationError):
        read_route.read_historical(
            _request(warmup_extension_start_utc="2025-04-25"), run, grant=_grant()
        )


def test_an_oos_slice_grant_does_not_authorise_a_development_read(
    sandbox: Path, guards: object
) -> None:
    """The slice is a separate operation, and Q7's `N = 1` accounts for it separately.

    R-2 quarantines the slice from R1 onward: no stage before R4 may read it.
    A grant for `track_a_exploratory_oos_slice_read` therefore cannot be spent
    on the development route, whatever span it names.
    """
    run = _run()
    _declare(run)
    slice_grant = _grant(operation=authorization.OPERATION_OOS_SLICE_READ)
    with pytest.raises(authorization.AuthorizationError):
        read_route.read_historical(_request(), run, grant=slice_grant)


def test_a_development_grant_does_not_authorise_a_derivation(sandbox: Path, guards: object) -> None:
    from scripts.m15_track_a import derivation

    run = _run()
    _declare(run)
    with pytest.raises(authorization.AuthorizationError):
        derivation.derive_m15(
            derivation.DerivationRequest(read_request=_request()), run, grant=_grant()
        )


@pytest.mark.parametrize(
    ("label", "start", "end"),
    [
        ("the forward epoch", "2026-04-25", "2026-05-31"),
        ("the dead window", "2026-03-10", "2026-03-20"),
        ("before the design span", "2025-01-01", "2025-02-01"),
    ],
)
def test_a_span_outside_the_design_window_is_refused(
    sandbox: Path, guards: object, label: str, start: str, end: str
) -> None:
    """`assert_span_admissible` refuses before the grant is even consulted for these."""
    run = _run()
    _declare(run, span_start_utc=start, span_end_utc=end)
    with pytest.raises((read_route.ReadRouteError, authorization.AuthorizationError)):
        read_route.read_historical(
            _request(span_start_utc=start, span_end_utc=end, warmup_extension_start_utc=start),
            run,
            grant=_grant(span_start_utc=start, span_end_utc=end),
        )


def test_an_undeclared_interval_is_refused(sandbox: Path, guards: object) -> None:
    """Write-ahead: the declaration must already be on the ledger at read time."""
    with pytest.raises(seen_ledger.SeenLedgerError):
        read_route.read_historical(_request(), _run(), grant=_grant())


def test_a_missing_source_file_is_a_refusal_not_a_substitution(
    sandbox: Path, guards: object
) -> None:
    """`train_lgbm_models.py` falls back to mid when the BA file is missing. This does not."""
    run = _run()
    _declare(run)
    with pytest.raises(read_route.ReadRouteError, match="not present under"):
        read_route.read_historical(_request(), run, grant=_grant())


def test_guards_must_be_installed(sandbox: Path) -> None:
    isolation.uninstall_all()
    with pytest.raises(read_route.ReadRouteError, match="isolation guards"):
        read_route.read_historical(_request(), _run(), grant=_grant())


# ---------------------------------------------------------------------------
# The read itself, on synthetic rows
# ---------------------------------------------------------------------------


def test_a_valid_request_reads_only_the_granted_span(sandbox: Path, guards: object) -> None:
    """Rows outside the grant are in the file and are not returned."""
    inside = datetime(2025, 5, 2, 12, 0, tzinfo=UTC)
    before = datetime(2025, 4, 20, 12, 0, tzinfo=UTC)
    after = datetime(2025, 7, 1, 12, 0, tzinfo=UTC)
    _write_source(
        sandbox,
        "EUR_USD",
        [before, inside, inside + timedelta(minutes=1), after],
    )
    run = _run()
    _declare(run)

    result = read_route.read_historical(_request(), run, grant=_grant())

    assert isinstance(result, read_route.HistoricalRead)
    assert result.row_count == 2, "only the two rows inside the granted span"
    stamps = [row["ts"] for row in result.rows_by_pair["EUR_USD"]]
    assert min(stamps) >= datetime(2025, 5, 1, tzinfo=UTC)
    assert max(stamps) <= datetime(2025, 5, 31, 23, 59, 59, tzinfo=UTC)


def test_the_returned_rows_are_the_shape_the_derivation_consumes(
    sandbox: Path, guards: object
) -> None:
    """One route feeds one derivation: the row keys are the aggregator's own."""
    _write_source(sandbox, "EUR_USD", [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)])
    run = _run()
    _declare(run)
    result = read_route.read_historical(_request(), run, grant=_grant())
    row = result.rows_by_pair["EUR_USD"][0]
    assert set(row) == {read_route.ROW_TIMESTAMP_KEY, *read_route.ROW_SIDE_KEYS}
    assert row["ts"].tzinfo is not None
    assert all(isinstance(row[key], float) for key in read_route.ROW_SIDE_KEYS)


def test_the_result_carries_both_track_a_classifications(sandbox: Path, guards: object) -> None:
    _write_source(sandbox, "EUR_USD", [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)])
    run = _run()
    _declare(run)
    result = read_route.read_historical(_request(), run, grant=_grant())
    assert result.classification == "NON_DECISION_BEARING_EXPLORATORY_ONLY"
    assert result.classification_secondary == "RESEARCH_SCRATCH_NON_AUTHORITATIVE"
    record = result.as_record()
    assert record["rows_by_pair"] == {"EUR_USD": 1}, "the summary carries counts, never bars"
    assert "bid_o" not in json.dumps(record)


def test_the_grant_is_recorded_before_anything_is_opened(sandbox: Path, guards: object) -> None:
    """An approval that leaves no trace of its exercised scope cannot be audited."""
    _write_source(sandbox, "EUR_USD", [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)])
    run = _run()
    _declare(run)
    read_route.read_historical(_request(), run, grant=_grant())
    entries = seen_ledger.grant_ledger_path().read_text(encoding="utf-8").splitlines()
    assert entries, "the exercised grant is on the record"
    recorded = json.loads(entries[-1])
    assert recorded["grant"]["span_start_utc"] == DEV_START
    assert recorded["route"] == read_route.ROUTE_ID


def test_a_dead_window_row_in_the_source_is_never_reached(sandbox: Path, guards: object) -> None:
    """The scan stops at the window; the dead window sits after every window.

    This test used to read `a row inside the dead window is refused even if
    declared`, and it passed a request ending at `DESIGN_END` together with a
    **grant** ending `2026-04-30`, as though that were an ordinary pairing. It
    was the defect: the read window came from the grant, so the route reached
    into the dead window and then refused what it found there. Refusing is not
    the guarantee worth having — **not reaching it** is.

    So the guarantee asserted now is the stronger one. The dead window and the
    forward epoch lie after `DESIGN_END`, every admissible window ends at or
    before `DESIGN_END`, and the scan stops at the first row past its window.
    The row-level refusals below it are unreachable through this route at this
    head, and they stay in as a backstop for a head where
    ``assert_span_admissible`` is weakened.
    """
    _write_source(
        sandbox,
        "EUR_USD",
        [datetime(2025, 5, 2, 12, 0, tzinfo=UTC), datetime(2026, 3, 10, 12, 0, tzinfo=UTC)],
    )
    run = _run()
    _declare(run, span_end_utc="2026-02-28")
    result = read_route.read_historical(
        _request(span_end_utc="2026-02-28"),
        run,
        grant=_grant(span_end_utc="2026-04-30"),
    )
    returned = [row[read_route.ROW_TIMESTAMP_KEY] for row in result.rows_by_pair["EUR_USD"]]
    assert returned == [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)]
    assert result.span_end_utc == "2026-02-28", "the wider grant does not widen the window"


def test_the_window_can_never_reach_the_dead_window(sandbox: Path, guards: object) -> None:
    """Why the row-level dead-window refusal is unreachable, asserted as a property.

    ``hi`` is the minimum of the grant's end and the request's end, and
    ``assert_span_admissible`` has already bounded the request at ``DESIGN_END``.
    ``DEAD_START`` is one second after ``DESIGN_END``, so no row the scan reaches
    can be in the dead window however wide the grant is.
    """
    assert DEAD_START > DESIGN_END
    assert (DEAD_START - DESIGN_END).total_seconds() == 1
    with pytest.raises(read_route.ReadRouteError, match="not admissible"):
        read_route.assert_span_admissible(_request(span_end_utc="2026-03-01"))


def test_a_row_past_the_window_is_not_even_parsed(sandbox: Path, guards: object) -> None:
    """Stopping at the window is measured, not asserted from the source.

    A review role measured the earlier ordering by putting a **malformed** row
    outside the granted span: the read failed on it, which proved every line in
    the file was being parsed in full, prices included. Here the same malformed
    row is past the window and the read succeeds — the only way it can is if the
    row was never parsed.
    """
    path = _write_source(sandbox, "EUR_USD", [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)])
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"time": "2026-03-15T12:00:00Z", "bid_c": "NOT_A_NUMBER"}) + "\n")
    run = _run()
    _declare(run)
    result = read_route.read_historical(_request(), run, grant=_grant())
    assert len(result.rows_by_pair["EUR_USD"]) == 1


def test_a_grant_wider_than_the_request_does_not_widen_the_read(
    sandbox: Path, guards: object
) -> None:
    """Coverage is containment, so a grant may be wider. The read may not be.

    Reproduced by two review roles independently. A one-month declaration and a
    one-month request with a full-design-span grant returned September and
    February rows: ten months would have become `EXPLORATORY_SEEN_DATA` with one
    month on the record, and seen-data is irreversible.
    """
    _write_source(
        sandbox,
        "EUR_USD",
        [
            datetime(2025, 5, 2, 12, 0, tzinfo=UTC),
            datetime(2025, 9, 2, 12, 0, tzinfo=UTC),
            datetime(2026, 2, 2, 12, 0, tzinfo=UTC),
        ],
    )
    run = _run()
    _declare(run, span_end_utc="2025-05-31")
    result = read_route.read_historical(
        _request(span_end_utc="2025-05-31"),
        run,
        grant=_grant(span_end_utc="2026-02-28"),
    )
    returned = [row[read_route.ROW_TIMESTAMP_KEY] for row in result.rows_by_pair["EUR_USD"]]
    assert returned == [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)]
    assert (result.span_start_utc, result.span_end_utc) == (DEV_START, "2025-05-31")


def test_a_grant_naming_more_pairs_than_the_request_opens_only_the_requested(
    sandbox: Path, guards: object
) -> None:
    """The same defect on the pair axis, which the first fix missed.

    A one-pair declaration with a two-pair grant opened **both** files. The
    second pair was authorised and undeclared, which is the combination the
    seen-data ledger exists to make impossible.
    """
    _write_source(sandbox, "EUR_USD", [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)])
    second = _write_source(sandbox, "USD_JPY", [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)])
    opened: list[str] = []
    real_open = Path.open

    def spy(self: Path, *args: object, **kwargs: object) -> object:
        opened.append(self.name)
        return real_open(self, *args, **kwargs)  # type: ignore[arg-type]

    run = _run()
    _declare(run)
    monkey = pytest.MonkeyPatch()
    monkey.setattr(Path, "open", spy)
    try:
        result = read_route.read_historical(
            _request(), run, grant=_grant(pairs=("EUR_USD", "USD_JPY"))
        )
    finally:
        monkey.undo()
    assert list(result.rows_by_pair) == ["EUR_USD"]
    assert second.name not in opened, "the undeclared pair's file was opened"


def test_a_pair_named_twice_is_refused_rather_than_folded(sandbox: Path, guards: object) -> None:
    """Two spellings would collapse into one result key, losing the request."""
    _write_source(sandbox, "EUR_USD", [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)])
    run = _run()
    _declare(run, pairs=("EUR_USD", "eurusd"))
    with pytest.raises(read_route.ReadRouteError, match="named twice"):
        read_route.read_historical(
            _request(pairs=("EUR_USD", "eurusd")),
            run,
            grant=_grant(pairs=("EUR_USD", "eurusd")),
        )


def test_an_out_of_order_source_is_refused_not_silently_truncated(
    sandbox: Path, guards: object
) -> None:
    """The stop is only sound on an ordered source, so the order is enforced.

    The alternative — assuming the order because OANDA writes it that way — would
    turn a source this route has never seen into a silently short read.
    """
    _write_source(
        sandbox,
        "EUR_USD",
        [datetime(2025, 5, 3, 12, 0, tzinfo=UTC), datetime(2025, 5, 2, 12, 0, tzinfo=UTC)],
    )
    run = _run()
    _declare(run)
    with pytest.raises(read_route.ReadRouteError, match="strictly increasing"):
        read_route.read_historical(_request(), run, grant=_grant())


def test_a_covert_read_in_a_read_route_helper_is_caught(tmp_path: Path) -> None:
    """The module's opener exemption covers one open, not the module.

    A review role measured the gap this closes: it added four lines to
    ``_row_from_source`` — a helper, so outside the body-only conditions — read
    an undeclared market-data file from them, and every audit check still
    returned PASS. Its first attempt used ``globals()`` and the indirection
    sweep caught it; the second used no reflection and nothing did.
    """
    source = Path(read_route.__file__).read_text(encoding="utf-8")
    marker = "    row: dict[str, Any] = {ROW_TIMESTAMP_KEY: timestamp}"
    assert marker in source, "the helper this test mutates has moved"
    covert = tmp_path / "read_route.py"
    covert.write_text(
        source.replace(
            marker,
            '    sidecar = Path("data/candles_USD_JPY_M1_365d_BA.jsonl")\n'
            "    if sidecar.is_file():\n"
            '        sidecar.read_text(encoding="utf-8")\n' + marker,
        ),
        encoding="utf-8",
    )
    monkey = pytest.MonkeyPatch()
    monkey.setattr(read_route, "__file__", str(covert))
    try:
        result = containment._check_read_body_is_declared()
    finally:
        monkey.undo()
    assert not result.passed
    assert "read_text" in result.detail
    assert containment._check_read_body_is_declared().passed, "the real source still passes"


def test_a_malformed_source_row_is_refused_never_dropped(sandbox: Path, guards: object) -> None:
    """Refuses rather than degrades, on the same footing as the aggregator it feeds."""
    path = _write_source(sandbox, "EUR_USD", [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)])
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"time": "2025-05-02T12:01:00Z", "bid_o": 1.1}) + "\n")
    run = _run()
    _declare(run)
    with pytest.raises(read_route.ReadRouteError, match="missing"):
        read_route.read_historical(_request(), run, grant=_grant())


# ---------------------------------------------------------------------------
# The boundaries the read must not move
# ---------------------------------------------------------------------------


def test_the_read_does_not_relax_network_db_or_broker(sandbox: Path, guards: object) -> None:
    import socket

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        with pytest.raises(isolation.IsolationError):
            probe.connect(("203.0.113.1", 80))
    finally:
        probe.close()
    with pytest.raises(isolation.IsolationError):
        socket.getaddrinfo("example.invalid", 80)
    for operation in isolation.FORBIDDEN_OPERATIONS:
        with pytest.raises(isolation.IsolationError):
            isolation.assert_operation_allowed(operation)


def test_the_read_does_not_widen_the_write_boundary(sandbox: Path, guards: object) -> None:
    _write_source(sandbox, "EUR_USD", [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)])
    run = _run()
    _declare(run)
    read_route.read_historical(_request(), run, grant=_grant())
    with pytest.raises(isolation.IsolationError):
        isolation.assert_write_allowed(str(scratch.repo_root() / "docs" / "__nx__.md"))
    with (
        pytest.raises(isolation.IsolationError),
        open(  # noqa: PTH123
            scratch.repo_root() / "data" / "__nx__.jsonl", "rb"
        ),
    ):
        pass


def test_the_read_window_closes_again_afterwards(sandbox: Path, guards: object) -> None:
    """The window is open for the read and for nothing else."""
    _write_source(sandbox, "EUR_USD", [datetime(2025, 5, 2, 12, 0, tzinfo=UTC)])
    run = _run()
    _declare(run)
    read_route.read_historical(_request(), run, grant=_grant())
    assert not isolation.is_read_window_open()


def test_the_source_is_one_committed_epoch_with_no_fallback() -> None:
    assert read_route.SOURCE_EPOCH == "365d_BA"
    assert read_route.SOURCE_TIMEFRAME == "M1"
    assert "{pair}" in read_route.SOURCE_FILENAME_TEMPLATE
    # Judged on the AST, not on the prose: the module *discusses* the mid
    # fallback in order to say it does not have one, and a substring test
    # cannot tell an explanation from an implementation.
    import ast

    tree = ast.parse(Path(read_route.__file__).read_text(encoding="utf-8"))
    body = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "read_historical"
    )
    opened = [
        child
        for child in ast.walk(body)
        if isinstance(child, ast.Call)
        and (getattr(child.func, "id", None) or getattr(child.func, "attr", None)) == "open"
    ]
    assert len(opened) == 1, "one route means one open"
    handlers = [child for child in ast.walk(body) if isinstance(child, ast.ExceptHandler)]
    for handler in handlers:
        raises = [n for n in ast.walk(handler) if isinstance(n, ast.Raise)]
        assert raises, "every except in the route re-raises; none substitutes a second source"
