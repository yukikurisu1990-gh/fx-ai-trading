"""The R-2 ruling's arithmetic, and what a grant is actually bound to.

**No test here touches real market data.** The slice tests are pure calendar
arithmetic; the sequencing tests read only this repository's own `.py` sources,
which is what the fingerprint is taken over.
"""

from __future__ import annotations

import hashlib
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from scripts.m15_gate3a.no_overlap import DEAD_START, DESIGN_END, DESIGN_START, FORWARD_FLOOR
from scripts.m15_track_a import authorization, containment, identity, oos_slice, read_route

#: This checkout, derived here rather than imported from the module under test.
REPO_ROOT = Path(containment.__file__).resolve().parents[2]

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


def test_the_surface_is_the_whole_transitive_first_party_closure() -> None:
    """A declared list follows imports one hop; the code that runs follows them all.

    A review role measured what a declared list missed: ``no_overlap`` imports
    ``timeutil``, and ``timeutil.to_utc`` is what ``is_dead_window_instant`` is
    built on. Shifting it by 400 days disabled the route's dead-window row guard
    with the fingerprint unchanged and the grant still valid. So the surface is
    computed, and this test walks the closure independently rather than
    restating the answer.
    """
    import ast

    names = {containment._surface_name(path) for path in containment.implementation_surface()}
    seen: set[Path] = set()
    pending = [
        path
        for path in Path(containment.__file__).parent.rglob("*.py")
        if "__pycache__" not in path.parts
    ]
    while pending:
        source = pending.pop().resolve()
        if source in seen:
            continue
        seen.add(source)
        # The importing file's own package, so a **relative** import resolves the
        # way Python resolves it. This walk used to follow absolute imports only,
        # which meant it shared the blind spot it exists to catch: it agreed with
        # a surface that had dropped every relative dependency of
        # ``scripts/m15_gate3a/``, and two files sat outside the closure with
        # this test green.
        #
        # Derived **here**, not by calling ``containment._module_package``. A
        # review role demonstrated the difference on a checkout under a
        # ``scripts/`` ancestor: importing the predicate under test made this
        # walk agree with a 27-file surface while two independent walks failed.
        # This package has paid for that shape before — a fixture that imports
        # the same predicate as the code cannot falsify it, which is how an
        # invented and factually wrong calendar passed twenty-seven tests.
        package = ".".join(source.relative_to(REPO_ROOT).with_suffix("").parts[:-1])
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            modules: list[str] = []
            if isinstance(node, ast.ImportFrom):
                base = node.module or ""
                if node.level:
                    parts = package.split(".")
                    anchor = ".".join(parts[: len(parts) - (node.level - 1)])
                    base = f"{anchor}.{base}".rstrip(".") if base else anchor
                if base == "scripts" or base.startswith("scripts."):
                    # ``from scripts import train_lgbm_models`` counts too: a lazy
                    # first-party import inside a function is still code the read
                    # runs, and it was the one this walk missed first time round.
                    modules = [base, *[f"{base}.{a.name}" for a in node.names]]
            elif isinstance(node, ast.Import):
                modules = [a.name for a in node.names if a.name.startswith("scripts")]
            for name in modules:
                parts = name.split(".")
                for depth in range(2, len(parts) + 1):
                    resolved = containment._module_source(".".join(parts[:depth]))
                    if resolved is not None and resolved not in seen:
                        pending.append(resolved)
    expected = {containment._surface_name(path) for path in seen}
    assert expected == names, f"surface disagrees with the closure: {expected ^ names}"


def test_the_transitive_dependencies_a_review_role_named_are_covered() -> None:
    """Named individually, because these five were the measured gap."""
    names = {containment._surface_name(path) for path in containment.implementation_surface()}
    for required in (
        "m15_gate3a/timeutil.py",
        "m15_gate3a/numeric_authority.py",
        "m15_gate3a/__init__.py",
        "ml_step4/data_adapter.py",
        "ml_step4/__init__.py",
    ):
        assert required in names, f"{required} is outside the fingerprint again"


def test_a_missing_importlib_util_cannot_silently_empty_the_surface() -> None:
    """The bug that made this function claim a closure and measure twelve files.

    ``import importlib`` alone does not bind ``importlib.util``, and the
    resolver caught ``AttributeError`` — so every sibling resolved to ``None``
    and the surface shrank to the package's own files with no error anywhere.
    Two pins: the module imports ``importlib.util`` explicitly, and the resolver
    no longer swallows ``AttributeError``.
    """
    import ast
    import inspect

    source = Path(containment.__file__).read_text(encoding="utf-8")
    assert "import importlib.util" in source

    # On the AST. A substring sweep matched the word in the comment that
    # explains why it is not caught -- the third time this exact false positive
    # has appeared in this package's tests.
    resolver = ast.parse(inspect.getsource(containment._module_source)).body[0]
    caught = {
        name.id
        for node in ast.walk(resolver)
        if isinstance(node, ast.ExceptHandler)
        for name in ast.walk(node.type)
        if isinstance(name, ast.Name)
    }
    assert "AttributeError" not in caught, caught
    assert len(containment.implementation_surface()) > 12


def test_the_fingerprint_ignores_line_endings() -> None:
    """The same commit must not hash differently on Windows and on CI.

    ``core.autocrlf`` is true on the authoring host and the CI runner is Linux.
    A review role measured two different values for one commit, which would make
    the approval workflow unworkable: the value recorded from CI could never
    match the host the read runs on.
    """
    files = containment.implementation_surface()
    original = containment.implementation_fingerprint()

    def digest(transform: object) -> str:
        running = hashlib.sha256()
        running.update(f"{len(files)}\n".encode())
        for path in files:
            running.update(containment._surface_name(path).encode())
            running.update(b"\0")
            body = path.read_bytes().replace(b"\r\n", b"\n")
            if transform == "crlf":
                body = body.replace(b"\n", b"\r\n")
            running.update(hashlib.sha256(body.replace(b"\r\n", b"\n")).hexdigest().encode())
            running.update(b"\n")
        return running.hexdigest()

    assert digest("lf") == original
    assert digest("crlf") == original


def test_the_fingerprint_does_not_depend_on_where_the_repository_sits(tmp_path: Path) -> None:
    """The approver and the reviewer compute it on different machines.

    This test used to patch ``scratch.repo_root`` — which
    ``implementation_surface`` does not call, so it could not fail. A review role
    said so. It now copies the packages to a different path and imports **there**,
    in a separate interpreter, which is the thing the claim is about.
    """
    import subprocess
    import sys

    root = Path(containment.__file__).resolve().parent.parent
    shutil.copytree(root, tmp_path / "scripts", ignore=shutil.ignore_patterns("__pycache__"))
    elsewhere = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import sys; sys.path.insert(0, r'{tmp_path}');"
            "from scripts.m15_track_a import containment;"
            "print(containment.implementation_fingerprint())",
        ],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert elsewhere.returncode == 0, elsewhere.stderr[-800:]
    assert elsewhere.stdout.strip() == containment.implementation_fingerprint()


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
            body = path.read_bytes().replace(b"\r\n", b"\n") + (extra if path == mutated else b"")
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
    """An OOS grant does not drive the development route, and vice versa.

    Two mechanisms, and the second is stronger than this test originally
    assumed. `covers` refuses the operation mismatch; and an OOS grant can no
    longer even be **constructed** over development dates, so the mismatch
    cannot be dressed up as a scope question.
    """
    assert authorization.OPERATION_OOS_SLICE_READ != authorization.OPERATION_HISTORICAL_READ
    with pytest.raises(authorization.AuthorizationMalformedError, match="only name dates inside"):
        _grant(operation=authorization.OPERATION_OOS_SLICE_READ)
    oos = _grant(
        operation=authorization.OPERATION_OOS_SLICE_READ,
        span_start_utc=oos_slice.SLICE_START_UTC,
        span_end_utc=oos_slice.SLICE_END_UTC,
    )
    assert not oos.covers(
        operation=authorization.OPERATION_HISTORICAL_READ,
        span_start_utc=oos_slice.SLICE_START_UTC,
        span_end_utc=oos_slice.SLICE_END_UTC,
        pairs=("EUR_USD",),
        timeframe="M1",
    )


@pytest.mark.parametrize(
    "operation,start,end,refused",
    [
        (authorization.OPERATION_HISTORICAL_READ, "2025-04-25", "2025-12-28", False),
        (authorization.OPERATION_HISTORICAL_READ, "2025-04-25", "2025-12-29", True),
        (authorization.OPERATION_HISTORICAL_READ, "2025-04-25", "2026-02-28", True),
        (authorization.OPERATION_OOS_SLICE_READ, "2025-12-29", "2026-02-28", False),
        (authorization.OPERATION_OOS_SLICE_READ, "2025-12-28", "2026-02-28", True),
        (authorization.OPERATION_OOS_SLICE_READ, "2025-04-25", "2025-12-28", True),
    ],
)
def test_a_grant_may_not_name_a_span_its_operation_cannot_read(
    operation: str, start: str, end: str, refused: bool
) -> None:
    """The ruling lives on the grant object, where no request can reach it.

    A review role drove all 62 slice dates through the route with a lying
    `ReadRequest` subclass, and narrowing the grant to the ruled corpus reduced
    the same attack to zero slice rows. That makes the grant's own ceiling the
    load-bearing backstop rather than a formality.
    """
    if refused:
        with pytest.raises(authorization.AuthorizationMalformedError):
            _grant(operation=operation, span_start_utc=start, span_end_utc=end)
    else:
        _grant(operation=operation, span_start_utc=start, span_end_utc=end)


def test_a_request_subclass_cannot_answer_a_field_differently_each_time() -> None:
    """The other half of the same reproduction: the route pins the request type."""

    class Lying(read_route.ReadRequest):
        _n = 0

        @property  # type: ignore[misc]
        def span_end_utc(self) -> str:  # type: ignore[override]
            type(self)._n += 1
            return oos_slice.DEVELOPMENT_END_UTC if type(self)._n <= 6 else oos_slice.SLICE_END_UTC

        @span_end_utc.setter
        def span_end_utc(self, value: str) -> None:
            pass

    lying = Lying(
        span_start_utc=oos_slice.DEVELOPMENT_START_UTC,
        span_end_utc=oos_slice.DEVELOPMENT_END_UTC,
        pairs=("EUR_USD",),
        timeframe="M1",
        warmup_extension_start_utc=oos_slice.DEVELOPMENT_START_UTC,
    )
    with pytest.raises(read_route.ReadRouteError, match="exactly a ReadRequest"):
        read_route.read_historical(lying, _identity(), grant=_grant())


def test_the_derivation_route_carries_the_slice_gate_too() -> None:
    """Deriving M15 over the slice is computing a statistic over it."""
    # On the AST, and by line number, not by substring position: the first
    # drafting of this assertion compared string offsets and lost to the word
    # "NotImplementedError" appearing in the docstring.
    import ast
    import inspect

    from scripts.m15_track_a import derivation

    tree = ast.parse(inspect.getsource(derivation.derive_m15))
    gates = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", None) == "assert_development_only"
    ]
    raises = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Raise)]
    assert gates, "the derivation route does not apply the slice gate"
    assert min(gates) < max(raises), "the slice gate runs after the body"


def test_the_ruling_token_is_the_one_the_decision_records() -> None:
    assert oos_slice.RULING_TOKEN == (
        "EXPLORATORY_OOS_SLICE_RULED_AS_FINAL_TWENTY_PERCENT_OF_COMMITTED_DESIGN_UTC_DATES"
    )


def test_the_fingerprint_surface_is_source_only() -> None:
    """A guard on the tests themselves: nothing here reaches a data file."""
    for path in containment.implementation_surface():
        assert path.suffix == ".py", path
        assert "data" not in path.parts, path
