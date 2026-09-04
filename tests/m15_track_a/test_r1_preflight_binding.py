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


@pytest.fixture
def full_shape_tree(sandbox: Path) -> Path:
    """A corpus whose **every** window carries rows, for all twenty pairs.

    `source_tree` puts two days in one of the eight windows, so a run over it
    makes 180 authorization calls. The number this work set out to reduce is the
    one a full corpus produces — 160 reads, 160 derivations and 321 calls — and a
    headline pinned on the sparse shape is not pinned. One hour per window keeps
    the fixture small while giving the run its real shape.
    """
    windows = streaming.iter_windows(SPAN_START, SPAN_END, window_days=31)
    for pair in PAIRS:
        path = sandbox / "data" / read_route.SOURCE_FILENAME_TEMPLATE.format(pair=pair, epoch=EPOCH)
        jpy = pair.endswith("_JPY")
        base = 150.0 if jpy else 1.1000
        tick = 0.01 if jpy else 0.0001
        with path.open("w", encoding="utf-8") as handle:
            index = 0
            for lo, _hi in windows:
                moment = datetime.fromisoformat(lo).replace(tzinfo=UTC)
                for _ in range(60):
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
    could try to fill in. The measured values are not fields at all now: they are
    read-only views onto a record this module seals when the verification runs,
    so building a context **is** the measurement.
    """
    import dataclasses

    fields = {f.name for f in dataclasses.fields(authorization.VerifiedRunContext)}
    assert fields == {"read_grant", "derivation_grant", "identity"}, fields
    for name in ("fingerprint", "approved_head_sha", "surface_stamp"):
        assert isinstance(getattr(authorization.VerifiedRunContext, name), property), name
    context = _context()
    assert context.fingerprint == containment.implementation_fingerprint()
    assert context.approved_head_sha == APPROVED_SHA
    assert len(context.surface_stamp) == len(containment.implementation_surface())
    with pytest.raises(TypeError):
        authorization.VerifiedRunContext(  # type: ignore[call-arg]
            read_grant=_grant(authorization.OPERATION_HISTORICAL_READ),
            derivation_grant=_grant(authorization.OPERATION_M15_DERIVATION),
            identity=_run(),
            fingerprint="0" * 64,
        )


def test_the_context_records_no_scope_at_all() -> None:
    """A span, a pair list and a timeframe are not this object's business.

    An earlier drafting kept the plan's scope here "for the record" and nothing
    read it, so a mutation writing `1970-01-01..2099-12-31 / ("XXX_YYY",) /
    NOT_A_TIMEFRAME` into it survived the whole suite and reached the R1 evidence
    record — the second fabricated span to travel into this programme's evidence
    that way. There is no field to fabricate now.
    """
    import dataclasses

    names = {f.name for f in dataclasses.fields(authorization.VerifiedRunContext)}
    for scope in ("span_start_utc", "span_end_utc", "pairs", "timeframe"):
        assert scope not in names, f"{scope} is back on the context"
        assert not hasattr(authorization.VerifiedRunContext, scope), scope
    record = _context().as_record()
    assert set(record) == {
        "fingerprint",
        "approved_head_sha",
        "surface_files",
        "read_grant",
        "derivation_grant",
    }, record


def test_the_context_is_frozen() -> None:
    import dataclasses

    context = _context()
    for name, value in (("fingerprint", "0" * 64), ("read_grant", None)):
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(context, name, value)


# ---------------------------------------------------------------------------
# The three routes that skip `__post_init__`
# ---------------------------------------------------------------------------


def test_a_context_that_never_ran_its_verification_is_refused() -> None:
    """`object.__new__` is the route `_revalidate` exists to close on a grant.

    A review role assembled a context this way around a grant approved against
    `"0" * 64` — an approval naming a tree that does not exist — and got sixty
    rows out of the gated read. The per-call measurement refused the same grant.
    The measurement is off the object now, so an object that never performed it
    reaches no record.
    """
    stale = _grant(
        authorization.OPERATION_HISTORICAL_READ, approved_implementation_fingerprint="0" * 64
    )
    forged = object.__new__(authorization.VerifiedRunContext)
    object.__setattr__(forged, "read_grant", stale)
    object.__setattr__(forged, "derivation_grant", _grant(authorization.OPERATION_M15_DERIVATION))
    object.__setattr__(forged, "identity", _run())
    assert type(forged) is authorization.VerifiedRunContext
    with pytest.raises(authorization.AuthorizationError, match="never ran its own verification"):
        authorization.require_authorization(
            stale,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            identity=forged.identity,
            context=forged,
        )
    #: and it cannot even describe itself
    for reader in (lambda: forged.fingerprint, lambda: forged.surface_stamp, forged.as_record):
        with pytest.raises(authorization.AuthorizationError):
            reader()


@pytest.mark.parametrize("clone", ["pickle", "deepcopy"])
def test_a_cloned_context_is_refused(clone: str) -> None:
    """Both routes rebuild the object without running `__init__`."""
    import copy
    import pickle

    context = _context()
    copied = pickle.loads(pickle.dumps(context)) if clone == "pickle" else copy.deepcopy(context)
    assert type(copied) is authorization.VerifiedRunContext
    assert copied == context, "the clone is equal, which is exactly the danger"
    with pytest.raises(authorization.AuthorizationError, match="never ran its own verification"):
        authorization.require_authorization(
            copied.read_grant,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            identity=copied.identity,
            context=copied,
        )


def test_setattr_after_construction_cannot_change_what_was_verified() -> None:
    """The third route: mutate a frozen field on a genuinely verified object."""
    context = _context()
    original = context.read_grant
    swapped = _grant(
        authorization.OPERATION_HISTORICAL_READ, approved_implementation_fingerprint="0" * 64
    )
    object.__setattr__(context, "read_grant", swapped)
    #: the measured values cannot be written by **any** route: a property is a
    #: data descriptor, so `object.__setattr__` does not reach them either
    for name in ("fingerprint", "approved_head_sha", "surface_stamp"):
        with pytest.raises(AttributeError, match="no setter"):
            object.__setattr__(context, name, "0" * 64)
    #: the object now says one thing and the sealed record says another
    assert context.read_grant is swapped
    assert context.grant_for(authorization.OPERATION_HISTORICAL_READ) is original
    assert context.fingerprint == containment.implementation_fingerprint()
    assert context.surface_stamp
    with pytest.raises(authorization.AuthorizationError, match="not the object this run"):
        authorization.require_authorization(
            swapped,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            identity=context.identity,
            context=context,
        )


@pytest.mark.parametrize(
    "field,value,match",
    [
        ("read_grant", None, "must be exactly a ReadGrant"),
        ("derivation_grant", "not a grant", "must be exactly a ReadGrant"),
        ("identity", "not an identity", "must be exactly a RunIdentity"),
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
    #: A tamper is **ineffective**, which is half the point: the window reads the
    #: sealed record, so a drift check the drifter supplies is not the one that
    #: runs — and the stamp is not writable on the object at all.
    with pytest.raises(AttributeError, match="no setter"):
        object.__setattr__(context, "surface_stamp", ())
    assert context.surface_stamp, "the object's claim beat the sealed record"

    #: The guards refuse an `os.utime` on a covered file, so the disk cannot be
    #: moved from inside a guarded test. Moving the sealed record instead
    #: exercises the same comparison against the same real files.
    record = authorization.sealed_binding(context)
    record["surface_stamp"] = tuple(
        (name, path, size + 1, mtime) for name, path, size, mtime in record["surface_stamp"]
    )
    with pytest.raises(containment.SurfaceDriftError, match="no longer that tree"):
        streaming.derive_streaming(
            request,
            context.identity,
            read_grant=context.read_grant,
            derivation_grant=context.derivation_grant,
            context=context,
            window_days=31,
        )


def test_an_equal_but_distinct_run_identity_is_refused() -> None:
    """`is`, not `==`, for the identity as well as the grant.

    The grant half was pinned with an equal twin; the identity half was pinned
    only with a *different* `run_id`, so `==` diverged too and a mutation from
    `is not` to `!=` survived the whole suite. A review role found it.
    """
    context = _context()
    twin = _run()
    assert twin == context.identity and twin is not context.identity
    with pytest.raises(authorization.AuthorizationError, match="not the one this context"):
        authorization.require_authorization(
            context.read_grant,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            identity=twin,
            context=context,
        )


def test_a_grant_mutated_before_the_context_is_built_is_refused() -> None:
    """`_revalidate` inside `__post_init__`, which nothing reached before.

    A grant whose frozen fields were rewritten after construction used to be
    caught only inside the read — after the irreversible declaration. The context
    re-runs the construction checks, so it is caught in preflight instead; a
    review role showed the guard was untested and a mutation deleting it
    survived.
    """
    tampered = _grant(authorization.OPERATION_HISTORICAL_READ)
    object.__setattr__(tampered, "span_end_utc", "not-a-date")
    with pytest.raises(authorization.AuthorizationMalformedError):
        _context(read_grant=tampered)


def test_the_reused_fingerprint_is_the_measured_one_not_the_grant_s_claim() -> None:
    """The comparison must not become a tautology.

    Rewriting `measured = record["fingerprint"]` to
    `measured = grant.approved_implementation_fingerprint` compares a value with
    itself and every equivalence test still passes. What catches it is a grant
    whose recorded fingerprint is changed *after* the context verified it: the
    format checks `_revalidate` runs cannot see the change, and only the
    comparison against the measured value can.
    """
    context = _context()
    grant = context.read_grant
    object.__setattr__(grant, "approved_implementation_fingerprint", "e" * 64)
    with pytest.raises(authorization.AuthorizationError, match="changed after the approval"):
        authorization.require_authorization(
            grant,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=SPAN_START,
            span_end_utc=SPAN_END,
            pairs=PAIRS,
            timeframe="M1",
            identity=context.identity,
            context=context,
        )


@pytest.mark.parametrize("bogus", ["not a context", 0, object()])
def test_the_streaming_route_type_pins_its_context(
    source_tree: Path, guards_installed: object, bogus: Any
) -> None:
    """A refusal with a name, not an `AttributeError` from a missing field."""
    request = read_route.ReadRequest(
        span_start_utc=SPAN_START,
        span_end_utc=SPAN_END,
        pairs=PAIRS,
        timeframe="M1",
        warmup_extension_start_utc=SPAN_START,
    )
    context = _context()
    with pytest.raises(authorization.AuthorizationError, match="exactly a VerifiedRunContext"):
        streaming.derive_streaming(
            request,
            context.identity,
            read_grant=context.read_grant,
            derivation_grant=context.derivation_grant,
            context=bogus,
            window_days=31,
        )


def test_measure_surface_is_the_two_functions_it_replaces() -> None:
    """One walk instead of two, and provably the same two values."""
    fingerprint, stamp = containment.measure_surface()
    assert fingerprint == containment.implementation_fingerprint()
    assert stamp == containment.surface_stamp()
    assert len(stamp) == len(containment.implementation_surface())


def test_the_fingerprint_algorithm_is_unchanged_by_the_split() -> None:
    """Recomputed independently, so a refactor of the shared helper cannot drift.

    `implementation_fingerprint` and `measure_surface` now share `_hash_over`.
    A test comparing them to each other would pass with both wrong; this one
    spells the algorithm out again — count, then per file the surface name, a NUL,
    the sha256 of the LF-normalised bytes, a newline.
    """
    import hashlib

    files = containment.implementation_surface()
    digest = hashlib.sha256()
    digest.update(f"{len(files)}\n".encode())
    for path in files:
        digest.update(containment._surface_name(path).encode())
        digest.update(b"\0")
        body = path.read_bytes().replace(b"\r\n", b"\n")
        digest.update(hashlib.sha256(body).hexdigest().encode())
        digest.update(b"\n")
    assert digest.hexdigest() == containment.implementation_fingerprint()


# ---------------------------------------------------------------------------
# The run: one measurement before the read, one after, none in between
# ---------------------------------------------------------------------------


def _trace_run(monkeypatch: pytest.MonkeyPatch, plan: Any) -> list[str]:
    """Run R1 and return the ordered event trace of the things that matter."""
    read_grant = _grant(authorization.OPERATION_HISTORICAL_READ)
    derivation_grant = _grant(authorization.OPERATION_M15_DERIVATION)
    order: list[str] = []
    real_fp = containment.implementation_fingerprint
    real_measure = containment.measure_surface
    real_declare = seen_ledger.declare
    real_auth = authorization.require_authorization
    real_read = read_route.read_historical

    def counting_fp() -> str:
        order.append("fingerprint")
        return real_fp()

    def counting_measure() -> Any:
        order.append("fingerprint")
        return real_measure()

    def noting_declare(*a: Any, **kw: Any) -> Any:
        order.append("declare")
        return real_declare(*a, **kw)

    def noting_auth(*a: Any, **kw: Any) -> Any:
        order.append("authorization")
        return real_auth(*a, **kw)

    def noting_read(*a: Any, **kw: Any) -> Any:
        order.append("read")
        return real_read(*a, **kw)

    monkeypatch.setattr(containment, "implementation_fingerprint", counting_fp)
    monkeypatch.setattr(containment, "measure_surface", counting_measure)
    monkeypatch.setattr(seen_ledger, "declare", noting_declare)
    monkeypatch.setattr(authorization, "require_authorization", noting_auth)
    monkeypatch.setattr(read_route, "read_historical", noting_read)
    r1_orchestrator.run_r1(plan, _run(), read_grant=read_grant, derivation_grant=derivation_grant)
    return order


def test_the_run_measures_the_fingerprint_twice_and_never_inside_the_read(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The headline, measured. 321 → 2, and neither of the two is a window's gate.

    Ordering matters as much as the count. The first measurement is before the
    write-ahead declaration, where a refusal costs nothing. The second is after
    the last window, closing the interval the per-window `stat` samples rather
    than proves — a completion check, not a gate a read can trip over. What is
    gone is the ~320 measurements that used to sit *between* the two, each one a
    refusal that would have cost the corpus.
    """
    order = _trace_run(monkeypatch, _plan())

    fingerprints = [i for i, name in enumerate(order) if name == "fingerprint"]
    declaration = order.index("declare")
    #: `containment.audit()` makes its own no-grant probe read before preflight
    #: measures anything; the corpus reads are the ones after the declaration
    windows = [i for i, name in enumerate(order) if name == "read" and i > declaration]
    assert len(fingerprints) == 2, f"{len(fingerprints)} full measurements in one run"
    assert fingerprints[0] < declaration, "the first measurement is after the declaration"
    assert fingerprints[1] > windows[-1], "the second measurement is not after the last read"
    assert not [i for i in fingerprints if windows[0] < i < windows[-1]], (
        "a measurement gates a window"
    )
    #: the scope check still runs on every call, which is the point of the split
    assert order.count("authorization") > 100, order.count("authorization")


def test_the_count_is_two_at_full_corpus_shape(
    full_shape_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The same claim where every window carries rows, not just one of eight.

    The sparse fixture above makes 180 authorization calls; a corpus whose every
    window has data makes 321, which is the number this work set out to reduce.
    A review role pointed out that pinning the claim on the sparse shape leaves
    the headline unpinned.
    """
    order = _trace_run(monkeypatch, _plan())

    declaration = order.index("declare")
    windows = [i for i, name in enumerate(order) if name == "read" and i > declaration]
    #: 20 pairs x 8 windows
    assert len(windows) == len(PAIRS) * 8 == 160, len(windows)
    #: one read + one derivation per window, plus `containment.audit`'s own
    #: no-grant probe: the 321 measurements this work set out to reduce
    assert order.count("authorization") == 321, order.count("authorization")
    assert order.count("fingerprint") == 2, order.count("fingerprint")


def test_a_tree_that_moves_during_the_run_cannot_certify_its_output(
    source_tree: Path, guards_installed: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The closing measurement, and why it is worth a second walk.

    A `stat` per window catches an edit, a replacement, a truncation or a
    removal, and misses one case: an edit preserving both size and mtime. A
    review role reproduced exactly that with an external editor — the per-call
    measurement refused the run and the stamp alone completed it. One
    cryptographic measurement at the far end covers every byte of the interval.
    """
    read_grant = _grant(authorization.OPERATION_HISTORICAL_READ)
    derivation_grant = _grant(authorization.OPERATION_M15_DERIVATION)
    real_fp = containment.implementation_fingerprint
    calls: list[int] = []

    def drifting_fp() -> str:
        calls.append(1)
        #: the first call is the closing one; before it, the run behaved
        return "f" * 64 if calls else real_fp()

    monkeypatch.setattr(containment, "implementation_fingerprint", drifting_fp)
    with pytest.raises(authorization.AuthorizationError, match="while the run was in progress"):
        r1_orchestrator.run_r1(
            _plan(), _run(), read_grant=read_grant, derivation_grant=derivation_grant
        )
    #: it fails at the far end, so the declaration and the read already happened:
    #: this protects the record's claim, it does not protect the corpus, and the
    #: docstring on `assert_implementation_unchanged` says so.
    assert seen_ledger.read_declarations()


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
            #: the head checks run in `preflight`, above the context, so this is
            #: the orchestrator's refusal and it names both SHAs
            r1_orchestrator.R1OrchestratorError,
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
    with pytest.raises(r1_orchestrator.R1OrchestratorError, match="names code_sha"):
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
