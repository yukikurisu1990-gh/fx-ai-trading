"""The verified binding: measured once, before anything is read, then frozen.

`TRACK_A_R1_PREFLIGHT_BINDING_SINGLE_VERIFICATION_PASSED` is what this file
establishes.

**No test here touches real market data.** Every case reads this repository's
own `.py` sources — which is what the fingerprint is taken over — or writes
synthetic JSONL into a temporary tree with `source_path_for` repointed at it.

What the change is, and what it is not
--------------------------------------

`require_authorization` measured `implementation_fingerprint()` on every call.
Once the read and the derivation ran per window that was about **321**
measurements a run, each parsing and hashing thirty-two files, and roughly 320
of them sat *after* the irreversible seen-data declaration — where a refusal
costs the corpus instead of costing nothing.

`VerifiedRunContext` moves that to **one** measurement, in preflight. It is an
**implementation-identity** cache and nothing else: the data-scope validation —
`grant_covers`, the span, the pairs, the timeframe, every row's timestamp —
still runs on every call, and the tests below assert that separation rather than
assume it.
"""

from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from scripts.m15_gate3a.pair_authority import PAIRS_20
from scripts.m15_track_a import (
    authorization,
    containment,
    identity,
    isolation,
    oos_slice,
    r1_orchestrator,
    read_route,
    scratch,
    seen_ledger,
    streaming,
)

EPOCH = read_route.SOURCE_EPOCH
PAIRS = tuple(sorted(PAIRS_20))
SPAN_START = oos_slice.DEVELOPMENT_START_UTC
SPAN_END = oos_slice.DEVELOPMENT_END_UTC
FIXTURE_START = "2025-05-05"
FIXTURE_END = "2025-05-06"
APPROVED_SHA = "a" * 40


# ---------------------------------------------------------------------------
# Fixtures
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
def source_tree(sandbox: Path) -> Path:
    for pair in PAIRS:
        _write_minutes(sandbox, pair, start=FIXTURE_START, end=FIXTURE_END)
    return sandbox


def _run(**overrides: Any) -> identity.RunIdentity:
    fields: dict[str, Any] = {
        "run_id": "r1-preflight-binding",
        "code_sha": APPROVED_SHA,
        "calendar_semantics": identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        "started_at_utc": "2026-09-04T00:00:00Z",
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
        "approver_record": "synthetic binding probe, not a recorded approval",
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


def _context(**overrides: Any) -> authorization.VerifiedRunContext:
    fields: dict[str, Any] = {
        "read_grant": _grant(authorization.OPERATION_HISTORICAL_READ),
        "derivation_grant": _grant(authorization.OPERATION_M15_DERIVATION),
        "identity": _run(),
        "span_start_utc": SPAN_START,
        "span_end_utc": SPAN_END,
        "pairs": PAIRS,
        "timeframe": "M1",
    }
    fields.update(overrides)
    return authorization.VerifiedRunContext(**fields)


# ---------------------------------------------------------------------------
# The context is a measurement, not a claim
# ---------------------------------------------------------------------------


def test_the_context_measures_the_tree_rather_than_accepting_a_number() -> None:
    """There is nothing for a caller to assert, and that is the design.

    A first drafting took `fingerprint` as a constructor argument and
    re-measured it to check the claim — two measurements, and a field a caller
    could try to fill in. The measured fields are `init=False` now, so building
    a context **is** the measurement.
    """
    import dataclasses

    fields = {f.name: f for f in dataclasses.fields(authorization.VerifiedRunContext)}
    for name in ("fingerprint", "approved_head_sha", "surface_stamp"):
        assert not fields[name].init, f"{name} is caller-supplied"
    context = _context()
    assert context.fingerprint == containment.implementation_fingerprint()
    assert context.approved_head_sha == APPROVED_SHA
    assert len(context.surface_stamp) == len(containment.implementation_surface())
    with pytest.raises(TypeError):
        authorization.VerifiedRunContext(  # type: ignore[call-arg]
            read_grant=_grant(authorization.OPERATION_HISTORICAL_READ),
            derivation_grant=_grant(authorization.OPERATION_M15_DERIVATION),
            identity=_run(),
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            fingerprint="0" * 64,
        )


def test_the_context_is_frozen() -> None:
    import dataclasses

    context = _context()
    for name, value in (("fingerprint", "0" * 64), ("span_end_utc", "2099-12-31")):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(context, name, value)


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("read_grant", None, "must be exactly a ReadGrant"),
        ("derivation_grant", "not a grant", "must be exactly a ReadGrant"),
        ("identity", "not an identity", "must be exactly a RunIdentity"),
        ("pairs", (), "non-empty tuple"),
    ],
)
def test_a_malformed_context_cannot_be_built(field: str, value: Any, match: str) -> None:
    with pytest.raises(authorization.AuthorizationMalformedError, match=match):
        _context(**{field: value})


def test_a_context_whose_grants_do_not_match_the_tree_cannot_be_built() -> None:
    stale = _grant(
        authorization.OPERATION_HISTORICAL_READ, approved_implementation_fingerprint="0" * 64
    )
    with pytest.raises(
        authorization.AuthorizationMalformedError, match="changed after the approval"
    ):
        _context(read_grant=stale)


def test_a_context_with_swapped_operations_cannot_be_built() -> None:
    with pytest.raises(authorization.AuthorizationMalformedError, match="names"):
        _context(derivation_grant=_grant(authorization.OPERATION_HISTORICAL_READ))


def test_one_grant_object_cannot_be_both_authorisations() -> None:
    """Refused — by the operation check, which fires first.

    The `is` guard behind it is defence in depth: a grant naming one operation
    cannot pass as the other, so reaching it needs a grant that names both,
    which `ReadGrant` will not build. Asserted at the refusal that actually
    fires rather than at the one a first drafting expected.
    """
    shared = _grant(authorization.OPERATION_HISTORICAL_READ)
    with pytest.raises(authorization.AuthorizationMalformedError, match="names"):
        _context(read_grant=shared, derivation_grant=shared)


def test_grants_naming_different_heads_cannot_be_bound_together() -> None:
    with pytest.raises(authorization.AuthorizationMalformedError, match="different approved heads"):
        _context(
            derivation_grant=_grant(
                authorization.OPERATION_M15_DERIVATION, approved_head_sha="b" * 40
            )
        )


# ---------------------------------------------------------------------------
# Reusing an identity is not reusing a scope check
# ---------------------------------------------------------------------------


def test_the_context_does_not_let_a_grant_cover_a_scope_it_does_not() -> None:
    """The whole risk of caching a verification, tested directly.

    A context makes `require_authorization` skip the **measurement**. It must
    not make it skip `grant_covers`.
    """
    context = _context()
    for operation, grant in (
        (authorization.OPERATION_HISTORICAL_READ, context.read_grant),
        (authorization.OPERATION_M15_DERIVATION, context.derivation_grant),
    ):
        #: in scope: accepted
        authorization.require_authorization(
            grant,
            operation=operation,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            identity=context.identity,
            context=context,
        )
        #: out of scope: still refused, context or no context
        for span, pairs, timeframe in (
            ((oos_slice.SLICE_START_UTC, oos_slice.SLICE_END_UTC), PAIRS, "M1"),
            (("2026-04-25", "2026-05-31"), PAIRS, "M1"),
            (("2025-04-24", SPAN_END), PAIRS, "M1"),
            ((SPAN_START, SPAN_END), ("USD_TRY",), "M1"),
            ((SPAN_START, SPAN_END), PAIRS, "M15"),
        ):
            with pytest.raises(authorization.AuthorizationError):
                authorization.require_authorization(
                    grant,
                    operation=operation,
                    span_start_utc=span[0],
                    span_end_utc=span[1],
                    pairs=pairs,
                    timeframe=timeframe,
                    identity=context.identity,
                    context=context,
                )


def test_a_context_cannot_authorise_a_grant_it_did_not_verify() -> None:
    """Identity, not equality: an equal-looking grant is a different object."""
    context = _context()
    twin = _grant(authorization.OPERATION_HISTORICAL_READ)
    assert twin == context.read_grant
    assert twin is not context.read_grant
    with pytest.raises(authorization.AuthorizationError, match="not the object"):
        authorization.require_authorization(
            twin,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            identity=context.identity,
            context=context,
        )


def test_a_context_cannot_authorise_another_run_identity() -> None:
    context = _context()
    other = _run(run_id="a-different-run")
    with pytest.raises(authorization.AuthorizationError, match="not the one this context"):
        authorization.require_authorization(
            context.read_grant,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            identity=other,
            context=context,
        )


def test_a_fabricated_context_object_is_refused() -> None:
    """A duck-typed stand-in is not a verified binding."""

    class Fake:
        fingerprint = "0" * 64
        surface_stamp = ()
        identity = None

        def grant_for(self, operation: str) -> Any:  # pragma: no cover - never reached
            raise AssertionError("should not be consulted")

    with pytest.raises(authorization.AuthorizationError, match="exactly a VerifiedRunContext"):
        authorization.require_authorization(
            _grant(authorization.OPERATION_HISTORICAL_READ),
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            identity=_run(),
            context=Fake(),
        )


def test_a_context_subclass_is_refused() -> None:
    class Sneaky(authorization.VerifiedRunContext):
        pass

    context = _context()
    sneaky = Sneaky(
        read_grant=context.read_grant,
        derivation_grant=context.derivation_grant,
        identity=context.identity,
        span_start_utc=SPAN_START,
        span_end_utc=SPAN_END,
        pairs=PAIRS,
        timeframe="M1",
    )
    with pytest.raises(authorization.AuthorizationError, match="exactly a VerifiedRunContext"):
        authorization.require_authorization(
            context.read_grant,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            identity=context.identity,
            context=sneaky,
        )


def test_without_a_context_the_measurement_still_happens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The un-cached path is unchanged, so a direct caller loses nothing."""
    #: built **before** the counter is installed: `_grant` measures the
    #: fingerprint to fill the field, and counting that would count the fixture
    #: rather than the gate.
    grant = _grant(authorization.OPERATION_HISTORICAL_READ)
    calls = {"n": 0}
    real = containment.implementation_fingerprint

    def counting() -> str:
        calls["n"] += 1
        return real()

    monkeypatch.setattr(containment, "implementation_fingerprint", counting)
    authorization.require_authorization(
        grant,
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc=SPAN_START,
        span_end_utc=SPAN_END,
        pairs=PAIRS,
        timeframe="M1",
        identity=_run(),
    )
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# TOCTOU: the surface may not drift under a verified run
# ---------------------------------------------------------------------------


def test_surface_drift_is_refused(tmp_path: Path) -> None:
    """The invariant the R1 run model asserts, expressed as a check.

    A `stat` per covered file, not a rehash: 0.53 ms against 203 ms. What it
    establishes and what it does not is set out on
    `containment.assert_surface_unchanged`; the honest frame is that after
    preflight has imported and measured, disk drift cannot change what this
    process executes, so this is evidence rather than protection.
    """
    stamp = containment.surface_stamp()
    containment.assert_surface_unchanged(stamp)

    #: a size change is caught
    grown = tuple(
        (name, path, size + 1, mtime)
        if name.endswith("streaming.py")
        else (name, path, size, mtime)
        for name, path, size, mtime in stamp
    )
    with pytest.raises(containment.SurfaceDriftError, match="size"):
        containment.assert_surface_unchanged(grown)

    #: so is an mtime change
    touched = tuple(
        (name, path, size, mtime + 1)
        if name.endswith("streaming.py")
        else (name, path, size, mtime)
        for name, path, size, mtime in stamp
    )
    with pytest.raises(containment.SurfaceDriftError, match="mtime"):
        containment.assert_surface_unchanged(touched)

    #: and a file that has gone
    missing = tuple(
        (name, str(tmp_path / "gone.py"), size, mtime) if name.endswith("streaming.py") else entry
        for entry, (name, _path, size, mtime) in zip(stamp, stamp, strict=True)
    )
    with pytest.raises(containment.SurfaceDriftError, match="unreadable"):
        containment.assert_surface_unchanged(missing)

    for bad in ((), "not a tuple", (("only", "three", 1),)):
        with pytest.raises(containment.SurfaceDriftError):
            containment.assert_surface_unchanged(bad)  # type: ignore[arg-type]


def test_a_window_refuses_when_the_surface_drifts_mid_run(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Moving the measurement to preflight must not permit edit-then-read."""
    context = _context()
    request = read_route.ReadRequest(
        span_start_utc=SPAN_START,
        span_end_utc=SPAN_END,
        pairs=PAIRS,
        timeframe="M1",
        warmup_extension_start_utc=SPAN_START,
    )
    seen_ledger.declare(
        seen_ledger.SeenDeclaration(
            run_id=context.identity.run_id,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            purpose="synthetic drift probe",
        ),
        context.identity,
    )
    drifted = tuple(
        (name, path, size + 1, mtime) for name, path, size, mtime in context.surface_stamp
    )
    object.__setattr__(context, "surface_stamp", drifted)
    with pytest.raises(containment.SurfaceDriftError, match="no longer that tree"):
        streaming.derive_streaming(
            request,
            context.identity,
            read_grant=context.read_grant,
            derivation_grant=context.derivation_grant,
            context=context,
            window_days=31,
        )


# ---------------------------------------------------------------------------
# The run: one measurement, all of it before the declaration
# ---------------------------------------------------------------------------


def test_the_run_measures_the_fingerprint_exactly_once_and_before_the_declaration(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The headline, measured. 321 → 1, and the one is before anything is read.

    Ordering matters as much as the count: a measurement after the write-ahead
    declaration is a refusal that costs the corpus.
    """
    #: the grants are built first, for the same reason: `_grant` measures.
    read_grant = _grant(authorization.OPERATION_HISTORICAL_READ)
    derivation_grant = _grant(authorization.OPERATION_M15_DERIVATION)
    order: list[str] = []
    real_fp = containment.implementation_fingerprint
    real_declare = seen_ledger.declare
    real_auth = authorization.require_authorization

    def counting_fp() -> str:
        order.append("fingerprint")
        return real_fp()

    def noting_declare(*a: Any, **kw: Any) -> Any:
        order.append("declare")
        return real_declare(*a, **kw)

    def noting_auth(*a: Any, **kw: Any) -> Any:
        order.append("authorization")
        return real_auth(*a, **kw)

    monkeypatch.setattr(containment, "implementation_fingerprint", counting_fp)
    monkeypatch.setattr(seen_ledger, "declare", noting_declare)
    monkeypatch.setattr(authorization, "require_authorization", noting_auth)

    r1_orchestrator.run_r1(
        _plan(), _run(), read_grant=read_grant, derivation_grant=derivation_grant
    )

    fingerprints = [i for i, name in enumerate(order) if name == "fingerprint"]
    declaration = order.index("declare")
    assert len(fingerprints) == 1, f"{len(fingerprints)} full measurements in one run"
    assert fingerprints[0] < declaration, "the measurement happened after the declaration"
    #: the scope check still runs on every call, which is the point of the split
    assert order.count("authorization") > 100, order.count("authorization")


def test_the_preflight_report_records_the_binding(
    source_tree: Path, guards_installed: object
) -> None:
    report = r1_orchestrator.preflight(
        _plan(),
        _run(),
        read_grant=_grant(authorization.OPERATION_HISTORICAL_READ),
        derivation_grant=_grant(authorization.OPERATION_M15_DERIVATION),
    )
    assert type(report.context) is authorization.VerifiedRunContext
    record = report.as_record()["verified_binding"]
    assert record["fingerprint"] == containment.implementation_fingerprint()
    assert record["surface_files"] == len(containment.implementation_surface())
    assert record["read_grant"] == authorization.OPERATION_HISTORICAL_READ
    assert record["derivation_grant"] == authorization.OPERATION_M15_DERIVATION
    #: preflight opens no market-data file and declares nothing
    assert not seen_ledger.read_declarations()


def test_preflight_still_refuses_before_the_declaration(
    source_tree: Path, guards_installed: object
) -> None:
    """Every binding refusal costs zero data bytes and leaves no ledger entry."""
    cases: list[tuple[dict[str, Any], type[Exception]]] = [
        (
            {
                "read_grant": _grant(
                    authorization.OPERATION_HISTORICAL_READ,
                    approved_implementation_fingerprint="0" * 64,
                )
            },
            authorization.AuthorizationMalformedError,
        ),
        (
            {
                "derivation_grant": _grant(
                    authorization.OPERATION_M15_DERIVATION,
                    approved_implementation_fingerprint="0" * 64,
                )
            },
            authorization.AuthorizationMalformedError,
        ),
        (
            {
                "derivation_grant": _grant(
                    authorization.OPERATION_M15_DERIVATION, approved_head_sha="b" * 40
                )
            },
            authorization.AuthorizationMalformedError,
        ),
        ({"read_grant": None}, r1_orchestrator.R1OrchestratorError),
        ({"derivation_grant": None}, r1_orchestrator.R1OrchestratorError),
    ]
    for overrides, expected in cases:
        fields: dict[str, Any] = {
            "read_grant": _grant(authorization.OPERATION_HISTORICAL_READ),
            "derivation_grant": _grant(authorization.OPERATION_M15_DERIVATION),
        }
        fields.update(overrides)
        with pytest.raises(expected):
            r1_orchestrator.run_r1(_plan(), _run(), **fields)
        assert not seen_ledger.read_declarations(), overrides
    with pytest.raises(authorization.AuthorizationMalformedError):
        r1_orchestrator.run_r1(
            _plan(),
            _run(code_sha="c" * 40),
            read_grant=_grant(authorization.OPERATION_HISTORICAL_READ),
            derivation_grant=_grant(authorization.OPERATION_M15_DERIVATION),
        )
    assert not seen_ledger.read_declarations()


def test_a_request_mutated_after_preflight_is_still_caught_by_row_validation(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Caching the identity must not cache the data scope.

    The span is snapshotted inside `derive_streaming`, so a post-preflight
    widening changes neither the windows nor the recorded span — and if it
    somehow reached the rows, `row_scope` is what refuses them.
    """
    plan = _plan()
    run = _run()
    read_grant = _grant(authorization.OPERATION_HISTORICAL_READ)
    derivation_grant = _grant(authorization.OPERATION_M15_DERIVATION)
    report = r1_orchestrator.preflight(
        plan, run, read_grant=read_grant, derivation_grant=derivation_grant
    )
    request = report.request
    #: declared as a real run would, so the refusal below is the scope check and
    #: not simply "nothing was declared"
    seen_ledger.declare(
        seen_ledger.SeenDeclaration(
            run_id=report.context.identity.run_id,
            span_start_utc=request.touched_start_utc,
            span_end_utc=request.span_end_utc,
            pairs=request.pairs,
            timeframe=request.timeframe,
            purpose="synthetic post-preflight mutation probe",
        ),
        report.context.identity,
    )
    object.__setattr__(request, "span_end_utc", oos_slice.SLICE_END_UTC)
    with pytest.raises(Exception) as caught:  # noqa: PT011 - the refusal type is the finding
        streaming.derive_streaming(
            request,
            #: the context binds to preflight's **snapshot** of the identity, not
            #: to the object the caller passed in — which is itself the property
            #: `derive_m15` was fixed for, and is asserted here by using it.
            report.context.identity,
            read_grant=read_grant,
            derivation_grant=derivation_grant,
            context=report.context,
            window_days=31,
        )
    #: any of the data-scope refusals is the right answer; what must not happen
    #: is the widened span being honoured because the identity was cached.
    message = str(caught.value)
    assert any(
        marker in message
        for marker in ("EXPLORATORY_OOS_SLICE", "does not cover", "no prior seen-data declaration")
    ), message


def test_the_orchestrator_reaches_no_next_stage_after_a_binding_refusal(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    reached: list[str] = []
    monkeypatch.setattr(streaming, "derive_streaming", lambda *a, **kw: reached.append("derive"))
    with pytest.raises(authorization.AuthorizationMalformedError):
        r1_orchestrator.run_r1(
            _plan(),
            _run(),
            read_grant=_grant(
                authorization.OPERATION_HISTORICAL_READ,
                approved_implementation_fingerprint="0" * 64,
            ),
            derivation_grant=_grant(authorization.OPERATION_M15_DERIVATION),
        )
    assert not reached
    assert not seen_ledger.read_declarations()


def test_the_context_is_an_identity_cache_and_says_so_in_code() -> None:
    """The separation this change rests on, pinned on the AST.

    `require_authorization` must still call `grant_covers` on the context path.
    If a later edit moved that inside the `else`, the cache would start skipping
    scope checks and every equivalence test would still pass.
    """
    import inspect

    tree = ast.parse(inspect.getsource(authorization.require_authorization))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and (getattr(node.func, "id", None) or getattr(node.func, "attr", None)) == "grant_covers"
    ]
    assert len(calls) == 1, "grant_covers should be called once, outside any context branch"
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            branch = ast.unparse(node)
            if "context is not None" in branch.splitlines()[0]:
                assert "grant_covers" not in branch, (
                    "grant_covers moved inside the context branch: a cached identity would "
                    "start skipping the scope check"
                )
