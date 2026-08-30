"""The R-2 ruling's arithmetic, and what a grant is actually bound to.

**No test here touches real market data.** The slice tests are pure calendar
arithmetic; the sequencing tests read only this repository's own `.py` sources,
which is what the fingerprint is taken over.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from scripts.m15_gate3a.no_overlap import DEAD_START, DESIGN_END, DESIGN_START, FORWARD_FLOOR
from scripts.m15_track_a import authorization, containment, identity, oos_slice, read_route

APPROVED_FINGERPRINT = containment.implementation_fingerprint()


# ---------------------------------------------------------------------------
# R-2 — the slice is derived, not chosen
# ---------------------------------------------------------------------------


def test_the_slice_is_the_final_twenty_percent_of_the_committed_design_dates() -> None:
    """A human chose the fraction; the dates are a consequence of two constants."""
    assert DESIGN_START.date() == oos_slice.DESIGN_START_DATE
    assert DESIGN_END.date() == oos_slice.DESIGN_END_DATE
    assert oos_slice.DESIGN_DATE_COUNT == 310
    assert oos_slice.OOS_TAIL_DATE_COUNT == 62
    assert oos_slice.SLICE_START_UTC == "2025-12-29"
    assert oos_slice.SLICE_END_UTC == "2026-02-28"
    assert oos_slice.DEVELOPMENT_START_UTC == "2025-04-25"
    assert oos_slice.DEVELOPMENT_END_UTC == "2025-12-28"


def test_the_design_span_is_partitioned_exactly_once() -> None:
    """No date belongs to both parts, and none belongs to neither."""
    development = (oos_slice.DEVELOPMENT_END_DATE - oos_slice.DEVELOPMENT_START_DATE).days + 1
    assert development + oos_slice.OOS_TAIL_DATE_COUNT == oos_slice.DESIGN_DATE_COUNT
    assert oos_slice.DEVELOPMENT_END_DATE + timedelta(days=1) == oos_slice.SLICE_START_DATE
    assert oos_slice.SLICE_END_DATE == oos_slice.DESIGN_END_DATE


def test_the_tail_is_an_exact_integer_ceiling() -> None:
    """``ceil(0.20 * n)`` in binary floating point is not a boundary anyone can check."""
    for count in (1, 4, 5, 9, 10, 11, 99, 100, 101, 310, 1000):
        expected = -(-count * 20 // 100)
        ruled = -(-count * oos_slice.OOS_TAIL_NUMERATOR // oos_slice.OOS_TAIL_DENOMINATOR)
        assert ruled == expected
        assert expected >= 1


def test_the_slice_is_inside_the_design_span_and_clear_of_everything_after_it() -> None:
    """It is a *design-span internal* split: neither quarantine reaches it."""
    assert DESIGN_START.date() <= oos_slice.SLICE_START_DATE <= DESIGN_END.date()
    assert DEAD_START.date() > oos_slice.SLICE_END_DATE
    assert FORWARD_FLOOR.date() > oos_slice.SLICE_END_DATE


@pytest.mark.parametrize(
    "day,inside",
    [
        ("2025-12-27", False),
        ("2025-12-28", False),
        ("2025-12-29", True),
        ("2026-01-15", True),
        ("2026-02-28", True),
        ("2026-03-01", False),
    ],
)
def test_the_boundary_dates_are_inclusive_on_both_ends(day: str, inside: bool) -> None:
    assert oos_slice.is_slice_date(date.fromisoformat(day)) is inside


def test_a_naive_datetime_is_refused_rather_than_read_in_the_host_timezone() -> None:
    """``datetime`` is a ``date`` subclass, which is how F-1 happened once already."""
    with pytest.raises(oos_slice.OosSliceError, match="naive"):
        oos_slice.is_slice_date(datetime(2026, 1, 15, 12, 0))  # noqa: DTZ001


def test_nothing_in_the_ruling_module_reads_a_file() -> None:
    """The dates cannot drift with the data, the host or the clock.

    Judged on the **AST**, not on substrings. A substring sweep here matched the
    word "environment" inside the module's own prose explaining that it reads no
    environment variable — the same false positive a no-fallback test hit an
    earlier round, and the same fix.
    """
    import ast

    tree = ast.parse(Path(oos_slice.__file__).read_text(encoding="utf-8"))
    forbidden = {"open", "read_text", "read_bytes", "getenv", "now", "today", "system", "run"}
    called = {
        getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert not (called & forbidden), f"the slice arithmetic reached for {called & forbidden}"
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in node.names
    } | {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not (imported & {"os", "io", "pathlib", "subprocess", "time", "json"}), imported


# ---------------------------------------------------------------------------
# The slice is quarantined from the development route
# ---------------------------------------------------------------------------


def _request(**overrides: object) -> read_route.ReadRequest:
    fields: dict[str, object] = {
        "span_start_utc": oos_slice.DEVELOPMENT_START_UTC,
        "span_end_utc": oos_slice.DEVELOPMENT_END_UTC,
        "pairs": ("EUR_USD",),
        "timeframe": "M1",
        "warmup_extension_start_utc": oos_slice.DEVELOPMENT_START_UTC,
    }
    fields.update(overrides)
    return read_route.ReadRequest(**fields)  # type: ignore[arg-type]


def test_the_whole_development_span_is_admissible() -> None:
    """The span the ruling produces has to be readable, or the ruling is useless."""
    read_route.assert_span_admissible(_request())
    read_route.assert_development_only(_request())


@pytest.mark.parametrize(
    "overrides",
    [
        {"span_end_utc": "2025-12-29"},
        {"span_end_utc": "2026-02-28"},
        {
            "span_start_utc": "2026-01-02",
            "span_end_utc": "2026-01-31",
            "warmup_extension_start_utc": "2026-01-02",
        },
    ],
    ids=["first-slice-date", "last-slice-date", "wholly-inside"],
)
def test_a_development_read_touching_the_slice_is_refused(overrides: dict[str, str]) -> None:
    with pytest.raises(read_route.ReadRouteError, match="EXPLORATORY_OOS_SLICE"):
        read_route.assert_development_only(_request(**overrides))


def test_a_warmup_reaching_into_the_slice_is_refused() -> None:
    """A warm-up extension reads bars. What it was *for* does not change that."""
    with pytest.raises(read_route.ReadRouteError, match="EXPLORATORY_OOS_SLICE"):
        read_route.assert_development_only(
            _request(
                span_start_utc="2026-01-05",
                span_end_utc="2026-01-31",
                warmup_extension_start_utc="2026-01-05",
            )
        )


def test_the_refusal_is_a_refusal_and_not_a_silent_trim() -> None:
    """A read quietly shortened leaves the caller believing it got what it asked for."""
    with pytest.raises(read_route.ReadRouteError) as caught:
        read_route.assert_development_only(_request(span_end_utc="2026-01-31"))
    assert "stops at 2025-12-28" in str(caught.value)


def test_the_slice_gate_is_separate_from_the_design_span_gate() -> None:
    """Two authorities, two refusals — collapsing them would hide which one fired."""
    inside_design_inside_slice = _request(span_end_utc="2026-01-31")
    read_route.assert_span_admissible(inside_design_inside_slice)
    with pytest.raises(read_route.ReadRouteError, match="EXPLORATORY_OOS_SLICE"):
        read_route.assert_development_only(inside_design_inside_slice)


# ---------------------------------------------------------------------------
# What a grant is bound to
# ---------------------------------------------------------------------------


def _identity(code_sha: str = "a" * 40) -> identity.RunIdentity:
    return identity.RunIdentity(
        run_id="sequencing-test",
        code_sha=code_sha,
        calendar_semantics=identity.CALENDAR_UTC_DATES_NO_MARKET_HOURS,
        started_at_utc="2026-01-01T00:00:00Z",
    )


def _grant(**overrides: object) -> authorization.ReadGrant:
    fields: dict[str, object] = {
        "operation": authorization.OPERATION_HISTORICAL_READ,
        "span_start_utc": oos_slice.DEVELOPMENT_START_UTC,
        "span_end_utc": oos_slice.DEVELOPMENT_END_UTC,
        "pairs": ("EUR_USD",),
        "timeframe": "M1",
        "approved_head_sha": "a" * 40,
        "approved_implementation_fingerprint": APPROVED_FINGERPRINT,
        "approver_record": "synthetic sequencing test grant",
    }
    fields.update(overrides)
    return authorization.ReadGrant(**fields)  # type: ignore[arg-type]


def test_the_fingerprint_is_stable_and_covers_the_declared_surface() -> None:
    assert containment.implementation_fingerprint() == containment.implementation_fingerprint()
    names = {containment._surface_name(path) for path in containment.implementation_surface()}
    assert "m15_track_a/read_route.py" in names
    assert "m15_track_a/authorization.py" in names
    assert "m15_track_a/isolation.py" in names
    assert "m15_track_a/oos_slice.py" in names
    assert "m15_gate3a/no_overlap.py" in names
    assert "m15_gate3a/pair_authority.py" in names


def test_the_surface_covers_every_gate3a_module_the_package_imports() -> None:
    """The failure mode is a new import nobody adds to the declared list.

    A hand-maintained list of sibling files drifts the moment someone imports a
    fifth module, and a grant would then survive a change to it. So the list is
    checked against the imports rather than trusted.
    """
    import ast

    package = Path(containment.__file__).parent
    imported: set[str] = set()
    for source in package.rglob("*.py"):
        if "__pycache__" in source.parts:
            continue
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith(
                "scripts.m15_gate3a."
            ):
                imported.add(node.module.split(".")[2])
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("scripts.m15_gate3a."):
                        imported.add(alias.name.split(".")[2])
    declared = {
        entry.split("/")[1].removesuffix(".py")
        for entry in containment.IMPLEMENTATION_SURFACE_SIBLINGS
    }
    assert imported <= declared, f"imported but not fingerprinted: {sorted(imported - declared)}"


def test_a_module_in_a_subdirectory_would_be_covered() -> None:
    """``glob`` would not have found it; ``rglob`` does.

    There is no subdirectory in the package today. The point is that adding one
    cannot move the read logic outside what a grant is bound to.
    """
    import inspect

    source = inspect.getsource(containment.implementation_surface)
    assert ".rglob(" in source
    assert ".glob(" not in source.replace(".rglob(", "")


def test_the_fingerprint_does_not_depend_on_where_the_repository_sits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The approver and the reviewer compute it on different machines."""
    from scripts.m15_track_a import scratch

    before = containment.implementation_fingerprint()
    monkeypatch.setattr(scratch, "repo_root", lambda: tmp_path)
    assert containment.implementation_fingerprint() == before


def test_changing_one_covered_byte_changes_the_fingerprint(tmp_path: Path) -> None:
    """Measured, not asserted: the digest is recomputed over a mutated copy."""
    files = containment.implementation_surface()
    original = containment.implementation_fingerprint()

    def digest_with(mutated: Path, extra: bytes) -> str:
        running = hashlib.sha256()
        running.update(f"{len(files)}\n".encode())
        for path in files:
            running.update(containment._surface_name(path).encode())
            running.update(b"\0")
            body = path.read_bytes() + (extra if path == mutated else b"")
            running.update(hashlib.sha256(body).hexdigest().encode())
            running.update(b"\n")
        return running.hexdigest()

    route = next(p for p in files if p.name == "read_route.py")
    assert digest_with(route, b"") == original
    assert digest_with(route, b"\n# one comment\n") != original


def test_a_grant_without_a_fingerprint_cannot_be_constructed() -> None:
    with pytest.raises(TypeError):
        authorization.ReadGrant(  # type: ignore[call-arg]
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
            span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
            pairs=("EUR_USD",),
            timeframe="M1",
            approved_head_sha="a" * 40,
            approver_record="a grant missing the binding",
        )


@pytest.mark.parametrize("value", ["", "b" * 63, "b" * 65, "B" * 64, "g" * 64, "a" * 40, 0, None])
def test_a_malformed_fingerprint_is_refused_at_construction(value: object) -> None:
    with pytest.raises(authorization.AuthorizationMalformedError):
        _grant(approved_implementation_fingerprint=value)


def test_a_stale_fingerprint_is_refused_at_check_time() -> None:
    """The grant records what was approved; the gate measures what is running."""
    with pytest.raises(authorization.AuthorizationError, match="implementation"):
        authorization.require_authorization(
            _grant(approved_implementation_fingerprint="b" * 64),
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
            span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
            pairs=("EUR_USD",),
            timeframe="M1",
            identity=_identity(),
        )


def test_a_head_that_differs_from_the_approved_head_is_allowed() -> None:
    """Recording the grant moves HEAD. That must not invalidate the grant.

    `READ_GRANT_BINDS_TO_APPROVED_IMPLEMENTATION_ANCESTRY_NOT_SELF_REFERENTIAL_EXECUTION_HEAD`
    """
    grant = _grant(approved_head_sha="a" * 40)
    assert (
        authorization.require_authorization(
            grant,
            operation=authorization.OPERATION_HISTORICAL_READ,
            span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
            span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
            pairs=("EUR_USD",),
            timeframe="M1",
            identity=_identity("f" * 40),
        )
        is grant
    )


def test_the_exercised_grant_records_both_the_head_and_the_fingerprint() -> None:
    """An approval that leaves no trace of what it was bound to cannot be audited."""
    record = _grant().as_record()
    assert record["approved_head_sha"] == "a" * 40
    assert record["approved_implementation_fingerprint"] == APPROVED_FINGERPRINT


def test_the_development_grant_does_not_cover_the_slice() -> None:
    """Coverage is containment, so the grant's own span has to stop first."""
    grant = _grant()
    assert grant.covers(
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
        span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
        pairs=("EUR_USD",),
        timeframe="M1",
    )
    assert not grant.covers(
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
        span_end_utc=oos_slice.SLICE_START_UTC,
        pairs=("EUR_USD",),
        timeframe="M1",
    )


def test_reading_the_slice_stays_a_separate_operation() -> None:
    """An OOS grant does not drive the development route, and vice versa."""
    assert authorization.OPERATION_OOS_SLICE_READ != authorization.OPERATION_HISTORICAL_READ
    oos = _grant(operation=authorization.OPERATION_OOS_SLICE_READ)
    assert not oos.covers(
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
        span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
        pairs=("EUR_USD",),
        timeframe="M1",
    )


def test_the_ruling_token_is_the_one_the_decision_records() -> None:
    assert oos_slice.RULING_TOKEN == (
        "EXPLORATORY_OOS_SLICE_RULED_AS_FINAL_TWENTY_PERCENT_OF_COMMITTED_DESIGN_UTC_DATES"
    )


def test_the_fingerprint_surface_is_source_only() -> None:
    """A guard on the tests themselves: nothing here reaches a data file."""
    for path in containment.implementation_surface():
        assert path.suffix == ".py", path
        assert "data" not in path.parts, path
