"""The two authorization-integrity defects PR #456 disclosed, closed and pinned.

**No test here touches real market data.** Every case writes synthetic JSONL into
a temporary tree and repoints `source_path_for` at it, or mutates a copy of this
repository's own `.py` sources in a temp directory. `data/` is never opened.

Two defects, two halves of this file:

**Defect A — derivation input integrity.** `derive_m15` gated what a request
*declared* and never looked at what it was *handed*. A review role aggregated
hand-built slice, dead-window and forward rows under a valid derivation grant,
and widened a `ReadRequest` subclass after the gates had passed. The read route
has carried the equivalent row-level guards from the start, saying why in its own
comments: `no_overlap` "checks metadata and cannot see bytes".

**Defect B — fingerprint closure.** `containment._first_party_imports` resolved
every *relative* import against the fixed literal `scripts.m15_track_a` whatever
package the file was in, so `scripts/m15_gate3a/aggregation.py`'s four relative
imports resolved to modules that do not exist and were dropped.
`scripts/ml_step4/{contract,inventory}.py` sat outside a surface the grant record
called "the transitive first-party import closure".

The tests below are written to fail if either fix is reverted, not to describe
it. Where a claim is about *absence* — a guard that is not there, a file that is
not covered — it is asserted as absence, so the disclosure cannot go stale.
"""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts.m15_gate3a import derivation_containment as dc
from scripts.m15_gate3a.no_overlap import DEAD_START, FORWARD_FLOOR
from scripts.m15_track_a import (
    authorization,
    containment,
    derivation,
    identity,
    isolation,
    oos_slice,
    read_route,
    row_scope,
    scratch,
    seen_ledger,
)

EPOCH = read_route.SOURCE_EPOCH
PAIRS = ("EUR_USD", "USD_JPY")
SPAN_START = "2025-05-05"  # a Monday inside the authorised development corpus
SPAN_END = "2025-05-09"  # the Friday of the same week
APPROVED_SHA = "a" * 40


# ---------------------------------------------------------------------------
# Fixtures — synthetic everything, copied in shape from the R1 dry run
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
def guards_installed() -> object:
    isolation.install_all()
    try:
        yield
    finally:
        isolation.uninstall_all()


def _write_minutes(sandbox: Path, pair: str, *, start: str, end: str) -> None:
    """One M1 row per minute, in the committed shape. No market-hours filter."""
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


def _run() -> identity.RunIdentity:
    return identity.RunIdentity(
        run_id="authorization-integrity-check",
        code_sha=APPROVED_SHA,
        calendar_semantics=identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        started_at_utc="2026-09-01T00:00:00Z",
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
        "approver_record": "synthetic probe grant, not a recorded approval",
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


def _declare(run: identity.RunIdentity) -> None:
    seen_ledger.declare(
        seen_ledger.SeenDeclaration(
            run_id=run.run_id,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            purpose="synthetic authorization-integrity probe",
        ),
        run,
    )


@pytest.fixture
def authorised_read(sandbox: Path, guards_installed: object) -> dict[str, Any]:
    """One honest read, so every negative below differs from it in one way only."""
    for pair in PAIRS:
        _write_minutes(sandbox, pair, start=SPAN_START, end=SPAN_END)
    run = _run()
    _declare(run)
    read = read_route.read_historical(
        _request(), run, grant=_grant(authorization.OPERATION_HISTORICAL_READ)
    )
    return {"read": read, "run": run}


def _derive(read: read_route.HistoricalRead, run: identity.RunIdentity, **kw: Any) -> Any:
    request = kw.pop("request", derivation.DerivationRequest(read_request=_request(), read=read))
    grant = kw.pop("grant", _grant(authorization.OPERATION_M15_DERIVATION))
    return derivation.derive_m15(request, run, grant=grant)


def _with_rows(
    read: read_route.HistoricalRead, rows_by_pair: dict[str, Any]
) -> read_route.HistoricalRead:
    """The same read, carrying different rows.

    Built as a genuine `HistoricalRead` on purpose: `derive_m15` pins that exact
    type, so a batch arriving from anywhere other than the read route arrives
    looking exactly like this. The threat model is not "a caller who cannot
    build the dataclass".
    """
    return read_route.HistoricalRead(
        run_id=read.run_id,
        operation=read.operation,
        timeframe=read.timeframe,
        epoch=read.epoch,
        span_start_utc=read.span_start_utc,
        span_end_utc=read.span_end_utc,
        rows_by_pair=rows_by_pair,
    )


def _moved(row: dict[str, Any], when: datetime) -> dict[str, Any]:
    moved = dict(row)
    moved[read_route.ROW_TIMESTAMP_KEY] = when
    return moved


# ---------------------------------------------------------------------------
# Defect A — the happy path still completes
# ---------------------------------------------------------------------------


def test_the_authorised_derivation_still_completes(authorised_read: dict[str, Any]) -> None:
    """The fix is a refusal added to a path that must still work."""
    derived = _derive(authorised_read["read"], authorised_read["run"])
    assert derived.bar_count > 0
    assert set(derived.bars_by_pair) == set(PAIRS)
    assert derived.input_scope_status == row_scope.ROW_SCOPE_STATUS
    assert derived.as_record()["input_scope_status"] == row_scope.ROW_SCOPE_STATUS


def test_the_rows_that_are_validated_are_the_rows_that_are_aggregated(
    authorised_read: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The snapshot, not the caller's object, reaches the delegate.

    A mapping that answers one way when it is checked and another when it is read
    defeats any amount of checking — `aggregate_m15._snapshot_row` exists because
    an audit did exactly that. Asserted by identity rather than by argument.
    """
    read = authorised_read["read"]
    handed: list[Any] = []
    real_delegate = derivation.DELEGATE

    def spy(rows: Any, **kw: Any) -> Any:
        handed.append(rows)
        return real_delegate(rows, **kw)

    monkeypatch.setattr(derivation, "DELEGATE", spy)
    _derive(read, authorised_read["run"])
    assert handed, "the delegate was never called"
    for batch in handed:
        assert type(batch) is list
        for row in batch:
            assert type(row) is dict
    originals = {id(row) for rows in read.rows_by_pair.values() for row in rows}
    passed = {id(row) for batch in handed for row in batch}
    assert not (originals & passed), "the caller's own row objects reached the aggregator"


def test_the_provenance_marker_survives_the_snapshot() -> None:
    """Copying rows must not disarm the derivation-bypass guard.

    A "fix" that quietly removes a control is worse than the gap it closes: if
    the snapshot dropped `_track_a_provenance`, every real derivation would look
    synthetic to `assert_derivation_authorised`.
    """
    lo = datetime(2025, 5, 5, tzinfo=UTC)
    scope = row_scope.RowScope(lo=lo, hi=lo + timedelta(days=1), pairs=("EUR_USD",))
    marked = dc.stamp_real_provenance(
        {read_route.ROW_TIMESTAMP_KEY: lo, **{k: 1.0 for k in read_route.ROW_SIDE_KEYS}}
    )
    plain = {
        read_route.ROW_TIMESTAMP_KEY: lo + timedelta(minutes=1),
        **{k: 1.0 for k in read_route.ROW_SIDE_KEYS},
    }
    out = row_scope.rows_in_scope([marked, plain], pair="EUR_USD", scope=scope)
    assert dc.is_real_row(out[0]), "the real-provenance marker was dropped by the snapshot"
    assert not dc.is_real_row(out[1]), "a synthetic row was marked real"


# ---------------------------------------------------------------------------
# Defect A — actual-row scope violations, every one refused
# ---------------------------------------------------------------------------


def _day(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


#: Derived from the committed authorities, never restated as literals: a test
#: that hard-codes `2026-01-15` still passes after someone moves the slice.
OUT_OF_SCOPE_INSTANTS = [
    (_day(oos_slice.SLICE_START_UTC), "the EXPLORATORY_OOS_SLICE (first day)"),
    (_day(oos_slice.SLICE_END_UTC), "the EXPLORATORY_OOS_SLICE (last day)"),
    (DEAD_START, "the consumed dead window"),
    (FORWARD_FLOOR, "the forward-epoch floor"),
    (_day(SPAN_END) + timedelta(days=1), "one day after the declared span"),
    (_day(SPAN_START) - timedelta(days=1), "one day before the declared span"),
]


@pytest.mark.parametrize(
    "when,why",
    OUT_OF_SCOPE_INSTANTS,
    ids=["oos-first", "oos-last", "dead-window", "forward-floor", "after-span", "before-span"],
)
def test_a_row_outside_the_authorised_window_is_refused(
    authorised_read: dict[str, Any], when: datetime, why: str
) -> None:
    """The declaration is valid; one row is not. Every one of these derived before."""
    read = authorised_read["read"]
    rows = dict(read.rows_by_pair)
    tampered = list(rows["EUR_USD"])
    tampered[len(tampered) // 2] = _moved(tampered[len(tampered) // 2], when)
    rows["EUR_USD"] = tampered
    with pytest.raises(derivation.DerivationRouteError) as caught:
        _derive(_with_rows(read, rows), authorised_read["run"])
    assert row_scope.ROW_SCOPE_TOKEN in str(caught.value) or "SLICE" in str(caught.value).upper()


def test_an_undeclared_pair_in_the_batch_is_refused(authorised_read: dict[str, Any]) -> None:
    """Mixed-scope batch. The loop would never have derived it — that is not the point."""
    read = authorised_read["read"]
    rows = dict(read.rows_by_pair)
    rows["GBP_USD"] = list(rows["EUR_USD"])
    with pytest.raises(derivation.DerivationRouteError, match="not in the authorised pair set"):
        _derive(_with_rows(read, rows), authorised_read["run"])


def test_a_pair_outside_the_universe_in_the_batch_is_refused(
    authorised_read: dict[str, Any],
) -> None:
    read = authorised_read["read"]
    rows = dict(read.rows_by_pair)
    rows["USD_TRY"] = list(rows["EUR_USD"])
    with pytest.raises(derivation.DerivationRouteError):
        _derive(_with_rows(read, rows), authorised_read["run"])


def test_rows_wider_than_the_grant_are_refused_even_when_the_request_is_wider(
    authorised_read: dict[str, Any],
) -> None:
    """The window is the grant-request **intersection**, not either side alone.

    A request narrower than the grant and rows outside the request: validating
    against the grant alone would accept them.
    """
    read = authorised_read["read"]
    narrow = _request(span_end_utc="2025-05-07")
    #: The read's *declared* span is narrowed too, so the existing
    #: declaration-level gate — the read's span must sit inside the gated
    #: interval — passes, and the **rows** are the only thing out of scope.
    #: Without this the earlier gate fires first and the row layer is never
    #: reached, which would let this test pass against a build that has no row
    #: layer at all.
    honest_looking = read_route.HistoricalRead(
        run_id=read.run_id,
        operation=read.operation,
        timeframe=read.timeframe,
        epoch=read.epoch,
        span_start_utc=SPAN_START,
        span_end_utc="2025-05-07",
        rows_by_pair={pair: list(batch) for pair, batch in read.rows_by_pair.items()},
    )
    with pytest.raises(derivation.DerivationRouteError, match="outside the authorised window"):
        _derive(
            honest_looking,
            authorised_read["run"],
            request=derivation.DerivationRequest(read_request=narrow, read=honest_looking),
        )


def test_reordered_or_duplicated_rows_are_refused(authorised_read: dict[str, Any]) -> None:
    """The authorised read produces a strictly increasing series; this one does not."""
    read = authorised_read["read"]
    rows = dict(read.rows_by_pair)
    batch = list(rows["EUR_USD"])
    batch[3], batch[4] = batch[4], batch[3]
    rows["EUR_USD"] = batch
    with pytest.raises(derivation.DerivationRouteError, match="not after the previous row"):
        _derive(_with_rows(read, rows), authorised_read["run"])


@pytest.mark.parametrize(
    "make,match",
    [
        (lambda ts: ts.replace(tzinfo=None), "timezone-naive"),
        (lambda ts: ts.astimezone(UTC).replace(tzinfo=None).replace(tzinfo=None), "timezone-naive"),
    ],
    ids=["naive", "naive-twice"],
)
def test_a_naive_timestamp_is_refused(
    authorised_read: dict[str, Any], make: Any, match: str
) -> None:
    """`tzinfo is None` is not the test; a naive instant moves with the host's zone."""
    read = authorised_read["read"]
    rows = dict(read.rows_by_pair)
    batch = list(rows["EUR_USD"])
    batch[0] = _moved(batch[0], make(batch[0][read_route.ROW_TIMESTAMP_KEY]))
    rows["EUR_USD"] = batch
    with pytest.raises(derivation.DerivationRouteError, match=match):
        _derive(_with_rows(read, rows), authorised_read["run"])


def test_a_non_utc_offset_is_refused(authorised_read: dict[str, Any]) -> None:
    read = authorised_read["read"]
    rows = dict(read.rows_by_pair)
    batch = list(rows["EUR_USD"])
    original = batch[0][read_route.ROW_TIMESTAMP_KEY]
    batch[0] = _moved(batch[0], original.astimezone(UTC).replace(tzinfo=UTC) + timedelta(0))
    # a genuinely offset-carrying instant
    shifted = original.replace(tzinfo=UTC).astimezone(
        datetime(2025, 1, 1, tzinfo=UTC).tzinfo  # UTC, then rebind below
    )
    batch[0] = _moved(batch[0], shifted.replace(tzinfo=_plus_nine()))
    rows["EUR_USD"] = batch
    with pytest.raises(derivation.DerivationRouteError, match="UTC offset"):
        _derive(_with_rows(read, rows), authorised_read["run"])


def _plus_nine() -> Any:
    from datetime import timezone

    return timezone(timedelta(hours=9))


@pytest.mark.parametrize(
    "corrupt,match",
    [
        (lambda row: {k: v for k, v in row.items() if k != "bid_o"}, "missing side key"),
        (lambda row: {**row, "bid_o": 1}, "not a plain float"),
        (lambda row: {**row, "bid_o": float("nan")}, "not finite"),
        (lambda row: {k: v for k, v in row.items() if k != "ts"}, "has no 'ts'"),
    ],
    ids=["missing-side-key", "int-not-float", "nan", "no-timestamp"],
)
def test_a_malformed_row_is_refused(
    authorised_read: dict[str, Any], corrupt: Any, match: str
) -> None:
    read = authorised_read["read"]
    rows = dict(read.rows_by_pair)
    batch = list(rows["EUR_USD"])
    batch[1] = corrupt(batch[1])
    rows["EUR_USD"] = batch
    with pytest.raises(derivation.DerivationRouteError, match=match):
        _derive(_with_rows(read, rows), authorised_read["run"])


def test_a_two_faced_row_container_is_refused(authorised_read: dict[str, Any]) -> None:
    """A `list` subclass that yields different rows on a second iteration.

    This is the shape that defeated the per-row provenance marker: the object is
    iterated once by the containment check and once by the aggregation loop.
    """

    class TwoFaced(list):  # noqa: FURB189 - subclassing list is the attack
        def __init__(self, clean: list[Any], dirty: list[Any]) -> None:
            super().__init__(clean)
            self._dirty = dirty
            self._served = 0

        def __iter__(self) -> Any:
            self._served += 1
            return iter(super().__iter__() if self._served == 1 else self._dirty)

    read = authorised_read["read"]
    clean = list(read.rows_by_pair["EUR_USD"])
    dirty = [_moved(clean[0], datetime(2026, 1, 15, tzinfo=UTC))]
    rows = dict(read.rows_by_pair)
    rows["EUR_USD"] = TwoFaced(clean, dirty)
    with pytest.raises(derivation.DerivationRouteError, match="plain list"):
        _derive(_with_rows(read, rows), authorised_read["run"])


def test_a_lying_row_mapping_is_refused(authorised_read: dict[str, Any]) -> None:
    """A `dict` subclass whose lookups change between reads."""

    class Shifty(dict):
        def __getitem__(self, key: str) -> Any:
            if key == read_route.ROW_TIMESTAMP_KEY:
                return datetime(2026, 1, 15, tzinfo=UTC)
            return super().__getitem__(key)

    read = authorised_read["read"]
    rows = dict(read.rows_by_pair)
    batch = list(rows["EUR_USD"])
    batch[0] = Shifty(batch[0])
    rows["EUR_USD"] = batch
    with pytest.raises(derivation.DerivationRouteError, match="plain dict"):
        _derive(_with_rows(read, rows), authorised_read["run"])


def test_a_rows_by_pair_mapping_subclass_is_refused(authorised_read: dict[str, Any]) -> None:
    class Shifty(dict):
        def __iter__(self) -> Any:
            return iter([])

    read = authorised_read["read"]
    with pytest.raises(derivation.DerivationRouteError, match="plain dict"):
        _derive(_with_rows(read, Shifty(read.rows_by_pair)), authorised_read["run"])


# ---------------------------------------------------------------------------
# Defect A — request identity and post-gate mutation
# ---------------------------------------------------------------------------


def test_a_request_subclass_is_refused(authorised_read: dict[str, Any]) -> None:
    """Honest at the gate, widened afterwards — the exact shape the read route pins."""

    class Widening(read_route.ReadRequest):
        """Honest for the first few reads of `span_end_utc`, then wider.

        `__getattribute__` rather than a property: a frozen dataclass assigns
        its fields through `object.__setattr__`, and a property with no setter
        makes the subclass unconstructible — which would make this test pass for
        the wrong reason.
        """

        _reads = 0

        def __getattribute__(self, name: str) -> Any:
            if name == "span_end_utc":
                cls = type(self)
                cls._reads += 1
                if cls._reads > 3:
                    return "2026-02-28"
            return super().__getattribute__(name)

    read = authorised_read["read"]
    sneaky = Widening(
        span_start_utc=SPAN_START,
        span_end_utc=SPAN_END,
        pairs=PAIRS,
        timeframe="M1",
        warmup_extension_start_utc=SPAN_START,
    )
    with pytest.raises(derivation.DerivationRouteError, match="exactly a ReadRequest"):
        _derive(
            read,
            authorised_read["run"],
            request=derivation.DerivationRequest(read_request=sneaky, read=read),
        )


def test_a_derivation_request_subclass_is_refused(authorised_read: dict[str, Any]) -> None:
    class Sneaky(derivation.DerivationRequest):
        pass

    read = authorised_read["read"]
    with pytest.raises(derivation.DerivationRouteError, match="exactly a DerivationRequest"):
        _derive(
            read,
            authorised_read["run"],
            request=Sneaky(read_request=_request(), read=read),
        )


def test_mutating_the_request_after_the_gates_does_not_widen_the_derivation(
    authorised_read: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """`frozen=True` yields to `object.__setattr__`; the snapshot does not.

    The derivation re-reads the span to build its record, which is where a
    post-gate widening would land. The mutation happens while the delegate is
    running — the only point at which a caller could get control back.
    """
    read = authorised_read["read"]
    request = derivation.DerivationRequest(read_request=_request(), read=read)
    real_delegate = derivation.DELEGATE

    def widen_then_delegate(rows: Any, **kw: Any) -> Any:
        object.__setattr__(request.read_request, "span_end_utc", "2026-02-28")
        object.__setattr__(request.read_request, "pairs", (*PAIRS, "GBP_USD"))
        return real_delegate(rows, **kw)

    monkeypatch.setattr(derivation, "DELEGATE", widen_then_delegate)
    derived = _derive(read, authorised_read["run"], request=request)
    assert derived.span_end_utc == SPAN_END
    assert set(derived.bars_by_pair) == set(PAIRS)


def test_the_derivation_declares_its_own_boundaries_from_the_canonical_primitives() -> None:
    """One set of boundary definitions, two layers of checking.

    The second layer must not invent a second calendar: if `row_scope` grew its
    own dates, the two layers could disagree and the disagreement would be
    silent. It imports the committed primitives instead, and this asserts that
    on the AST rather than on the prose.
    """
    source = Path(row_scope.__file__).read_text(encoding="utf-8")
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported.add(f"{node.module}.{alias.name}")
    assert "scripts.m15_gate3a.no_overlap.FORWARD_FLOOR" in imported
    assert "scripts.m15_gate3a.no_overlap.is_dead_window_instant" in imported
    assert "scripts.m15_track_a.oos_slice.assert_clear_of_slice" in imported
    assert "scripts.m15_gate3a.pair_authority.canonical_pair" in imported
    #: and no date literal of its own
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            assert not node.value.strip().startswith(("2025-", "2026-")), node.value


def test_the_direct_aggregate_bypass_is_still_refused(authorised_read: dict[str, Any]) -> None:
    """The containment latch is untouched by this change."""
    read = authorised_read["read"]
    rows = [dc.stamp_real_provenance(dict(row)) for row in read.rows_by_pair["EUR_USD"][:20]]
    from scripts.m15_gate3a.aggregation import aggregate_m15

    with pytest.raises(dc.DerivationContainmentError):
        aggregate_m15(rows, pair="EUR_USD", expected_minutes=None)


# ---------------------------------------------------------------------------
# Defect B — the closure
# ---------------------------------------------------------------------------


def _closure_independently() -> set[Path]:
    """The closure computed here, not by the function under test."""
    root = Path(containment.__file__).resolve().parents[2]
    surface = {path.resolve() for path in containment.implementation_surface()}

    def resolve(name: str) -> Path | None:
        import importlib.util

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
    return seen


def test_the_surface_is_now_the_transitive_closure() -> None:
    """The defect, asserted closed against an independently computed closure.

    Not `== 29`: a count is satisfied by any twenty-nine files. What the grant
    record claims is a *property*, so the property is what is checked.
    """
    surface = {path.resolve() for path in containment.implementation_surface()}
    closure = _closure_independently()
    assert not (closure - surface), sorted(str(p) for p in closure - surface)
    assert not (surface - closure), sorted(str(p) for p in surface - closure)


def test_the_previously_missing_dependencies_are_covered() -> None:
    """The two files a review role measured outside the surface."""
    names = {containment._surface_name(path) for path in containment.implementation_surface()}
    assert "ml_step4/contract.py" in names
    assert "ml_step4/inventory.py" in names
    assert "m15_gate3a/aggregation.py" in names
    assert "m15_track_a/row_scope.py" in names


def test_relative_imports_resolve_against_the_importing_files_own_package() -> None:
    """The root cause, checked at the resolver rather than through its effects."""
    root = Path(containment.__file__).resolve().parents[2]
    aggregation = root / "scripts" / "m15_gate3a" / "aggregation.py"
    package = containment._module_package(aggregation)
    assert package == "scripts.m15_gate3a"
    names = containment._first_party_imports(
        ast.parse(aggregation.read_text(encoding="utf-8")), package=package
    )
    for sibling in ("derivation_containment", "numeric_authority", "pair_authority", "timeutil"):
        assert f"scripts.m15_gate3a.{sibling}" in names
        assert f"scripts.m15_track_a.{sibling}" not in names


def test_the_package_of_an_init_file_is_its_own_directory() -> None:
    root = Path(containment.__file__).resolve().parents[2]
    assert (
        containment._module_package(root / "scripts" / "m15_gate3a" / "__init__.py")
        == "scripts.m15_gate3a"
    )


# ---------------------------------------------------------------------------
# Defect B — dependency mutation moves the fingerprint, one file at a time
# ---------------------------------------------------------------------------


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
    tree = tmp_path_factory.mktemp("closure-replica") / "repo"
    tree.mkdir()
    shutil.copytree(
        root / "scripts", tree / "scripts", ignore=shutil.ignore_patterns("__pycache__")
    )
    return tree


@pytest.fixture(scope="module")
def surface_names() -> tuple[str, ...]:
    return tuple(containment._surface_name(p) for p in containment.implementation_surface())


def test_every_covered_dependency_moves_the_fingerprint_when_mutated(
    replica: Path, tmp_path: Path, surface_names: tuple[str, ...]
) -> None:
    """Not "28 files" — **each** file, mutated on its own.

    A count is a weak assertion: it is satisfied by any list of the right
    length, including one that names the wrong files. This mutates every member
    of the surface in turn and requires the fingerprint to move for each.
    """
    tree = tmp_path / "repo"
    shutil.copytree(replica, tree, ignore=shutil.ignore_patterns("__pycache__"))
    before = _fingerprint_in(tree)
    unmoved: list[str] = []
    for name in surface_names:
        target = tree / "scripts" / name
        assert target.exists(), name
        original = target.read_text(encoding="utf-8")
        target.write_text(original + "\n# substantive\n", encoding="utf-8")
        if _fingerprint_in(tree) == before:
            unmoved.append(name)
        target.write_text(original, encoding="utf-8")
    assert not unmoved, f"these covered files did not move the fingerprint: {unmoved}"
    assert _fingerprint_in(tree) == before, "restoring every file did not restore the value"


def test_the_dependency_the_old_resolver_dropped_now_invalidates_a_grant(
    replica: Path, tmp_path: Path
) -> None:
    """The exploit a review role demonstrated, re-run against the fix.

    A new module in `scripts/m15_gate3a/`, imported **relatively**, used to sit
    outside the surface — so rewriting it afterwards left the fingerprint, and
    every grant bound to it, unchanged.
    """
    tree = tmp_path / "repo"
    shutil.copytree(replica, tree, ignore=shutil.ignore_patterns("__pycache__"))
    leak = tree / "scripts" / "m15_gate3a" / "leak.py"
    leak.write_text("LEAK_FACTOR = 1\n", encoding="utf-8")
    victim = tree / "scripts" / "m15_gate3a" / "session_windows.py"
    victim.write_text(
        victim.read_text(encoding="utf-8") + "\nfrom .leak import LEAK_FACTOR  # noqa: E402\n",
        encoding="utf-8",
    )
    with_leak = _fingerprint_in(tree)
    leak.write_text("LEAK_FACTOR = 999999\n", encoding="utf-8")
    assert _fingerprint_in(tree) != with_leak, (
        "rewriting a relatively-imported module left the fingerprint unchanged — the closure "
        "defect is back, and every grant bound to it would survive a change to what runs"
    )


def test_a_relative_import_two_levels_up_is_followed(replica: Path, tmp_path: Path) -> None:
    """`from ..package import x`, which the fixed resolver has to place correctly."""
    tree = tmp_path / "repo"
    shutil.copytree(replica, tree, ignore=shutil.ignore_patterns("__pycache__"))
    (tree / "scripts" / "sibling_pkg").mkdir()
    (tree / "scripts" / "sibling_pkg" / "__init__.py").write_text("", encoding="utf-8")
    far = tree / "scripts" / "sibling_pkg" / "far.py"
    far.write_text("FAR = 1\n", encoding="utf-8")
    victim = tree / "scripts" / "m15_gate3a" / "session_windows.py"
    victim.write_text(
        victim.read_text(encoding="utf-8") + "\nfrom ..sibling_pkg.far import FAR  # noqa: E402\n",
        encoding="utf-8",
    )
    before = _fingerprint_in(tree)
    far.write_text("FAR = 2\n", encoding="utf-8")
    assert _fingerprint_in(tree) != before


# ---------------------------------------------------------------------------
# Defect B — what must NOT move the fingerprint
# ---------------------------------------------------------------------------


def test_a_governance_or_documentation_change_does_not_move_the_fingerprint(
    replica: Path,
) -> None:
    """Recording an authorization must still not invalidate the authorization."""
    before = _fingerprint_in(replica)
    (replica / "docs").mkdir(exist_ok=True)
    (replica / "docs" / "a_new_grant_record.md").write_text("recorded\n", encoding="utf-8")
    (replica / "README.md").write_text("unrelated\n", encoding="utf-8")
    (replica / "notes.txt").write_text("also unrelated\n", encoding="utf-8")
    assert _fingerprint_in(replica) == before


def test_an_uncovered_python_file_does_not_move_the_fingerprint(
    replica: Path, tmp_path: Path
) -> None:
    """The surface is a closure, not "every .py in the repository"."""
    tree = tmp_path / "repo"
    shutil.copytree(replica, tree, ignore=shutil.ignore_patterns("__pycache__"))
    before = _fingerprint_in(tree)
    (tree / "scripts" / "unimported_helper.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert _fingerprint_in(tree) == before


def test_line_ending_normalisation_is_unchanged(replica: Path, tmp_path: Path) -> None:
    """CRLF and LF over the same source hash the same. Existing spec, kept."""
    tree = tmp_path / "repo"
    shutil.copytree(replica, tree, ignore=shutil.ignore_patterns("__pycache__"))
    targets = [
        tree / "scripts" / name
        for name in (
            "m15_track_a/row_scope.py",
            "m15_gate3a/aggregation.py",
            "ml_step4/contract.py",
        )
    ]
    #: This repository is checked out with CRLF on Windows, so inserting a CR
    #: before every LF turns CRLF into CRCRLF — a real content change. Normalise
    #: to LF first, then convert to CRLF, and require the value to survive both.
    #: The first drafting skipped the normalisation and reported a normalisation
    #: bug that was an artefact of the test.
    for target in targets:
        target.write_bytes(target.read_bytes().replace(b"\r\n", b"\n"))
    as_lf = _fingerprint_in(tree)
    for target in targets:
        target.write_bytes(target.read_bytes().replace(b"\n", b"\r\n"))
    assert _fingerprint_in(tree) == as_lf, "CRLF and LF over the same source hashed differently"
