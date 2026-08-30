"""The read/derivation routes refuse at every gate, and the records behave.

No test here reads market data. The two routes raise ``NotImplementedError``
*after* every gate passes, which is what lets a test prove the gates run in the
right order without any data existing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.m15_track_a import (
    authorization,
    breadth,
    containment,
    derivation,
    isolation,
    oos_budget,
    read_route,
    scratch,
    seen_ledger,
)
from scripts.m15_track_a.identity import RunIdentity, RunIdentityError

_SHA = "a" * 40


@pytest.fixture
def identity() -> RunIdentity:
    return RunIdentity(
        run_id="track-a-test-run",
        code_sha=_SHA,
        calendar_semantics="utc_calendar_dates_no_market_hours",
        started_at_utc="2026-08-29T00:00:00Z",
    )


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the scratch root at tmp_path so no test writes into the repository."""
    root = tmp_path / "track_a_scratch"
    monkeypatch.setattr(scratch, "scratch_root", lambda: root)
    monkeypatch.setattr(scratch, "repo_root", lambda: tmp_path)
    return root


@pytest.fixture
def guards() -> object:
    isolation.install_all()
    yield
    isolation.uninstall_all()


def _request(**overrides: object) -> read_route.ReadRequest:
    kwargs: dict[str, object] = {
        "span_start_utc": "2025-05-01",
        "span_end_utc": "2025-06-01",
        "pairs": ("EUR_USD",),
        "timeframe": "M1",
        "warmup_extension_start_utc": "2025-04-25",
    }
    kwargs.update(overrides)
    return read_route.ReadRequest(**kwargs)  # type: ignore[arg-type]


def _grant(**overrides: object) -> authorization.ReadGrant:
    kwargs: dict[str, object] = {
        "operation": authorization.OPERATION_HISTORICAL_READ,
        "span_start_utc": "2025-04-25",
        "span_end_utc": "2026-02-28",
        "pairs": ("EUR_USD",),
        "timeframe": "M1",
        "approved_head_sha": _SHA,
        "approver_record": "PR #451 approval record",
    }
    kwargs.update(overrides)
    return authorization.ReadGrant(**kwargs)  # type: ignore[arg-type]


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"run_id": "X"},  # too short, and uppercase
        {"code_sha": "a" * 12},
        {"calendar_semantics": "broker_market_hours"},  # Track A may not author market hours
        {"started_at_utc": "2026-08-29 00:00:00"},
    ],
)
def test_a_malformed_identity_refuses(overrides: dict[str, object]) -> None:
    kwargs: dict[str, object] = {
        "run_id": "track-a-test-run",
        "code_sha": _SHA,
        "calendar_semantics": "utc_calendar_dates_no_market_hours",
        "started_at_utc": "2026-08-29T00:00:00Z",
    }
    kwargs.update(overrides)
    with pytest.raises(RunIdentityError):
        RunIdentity(**kwargs)  # type: ignore[arg-type]


def test_identity_digest_is_stable(identity: RunIdentity) -> None:
    assert identity.digest == identity.digest
    assert len(identity.digest) == 64


# --------------------------------------------------------------------------
# The read route's gate order
# --------------------------------------------------------------------------


def test_read_refuses_when_isolation_is_not_installed(identity: RunIdentity) -> None:
    isolation.uninstall_all()
    with pytest.raises(read_route.ReadRouteError, match="isolation"):
        read_route.read_historical(_request(), identity, grant=_grant())


def test_read_refuses_without_a_grant(guards: object, identity: RunIdentity) -> None:
    with pytest.raises(authorization.AuthorizationError, match=authorization.TOKEN):
        read_route.read_historical(_request(), identity)


def test_read_refuses_a_span_reaching_the_dead_window(
    guards: object, identity: RunIdentity
) -> None:
    """DEAD_START is exactly one second after DESIGN_END; a slip pulls consumed bars in."""
    request = _request(span_end_utc="2026-03-01")
    grant = _grant(span_end_utc="2026-03-01")
    with pytest.raises(read_route.ReadRouteError):
        read_route.read_historical(request, identity, grant=grant)


def test_read_refuses_without_a_prior_seen_declaration(
    sandbox: Path, guards: object, identity: RunIdentity
) -> None:
    with pytest.raises(seen_ledger.SeenLedgerError, match="no prior seen-data declaration"):
        read_route.read_historical(_request(), identity, grant=_grant())


def test_read_reaches_the_declared_body_once_every_gate_passes(
    sandbox: Path, guards: object, identity: RunIdentity
) -> None:
    seen_ledger.declare(
        seen_ledger.SeenDeclaration(
            run_id=identity.run_id,
            span_start_utc="2025-04-25",
            span_end_utc="2026-02-28",
            pairs=("EUR_USD",),
            timeframe="M1",
            purpose="R1 descriptive survey",
        ),
        identity,
    )
    # Every gate passes, so control reaches the body. The body then refuses,
    # because the declared source file is not present in a test environment —
    # and a missing source is a **refusal**, never a substitution.
    with pytest.raises(read_route.ReadRouteError, match="not present under"):
        read_route.read_historical(_request(), identity, grant=_grant())


def test_warmup_widens_the_declared_interval() -> None:
    """A bar read only to initialise an indicator is seen (§8.11.4 rule 2)."""
    request = _request(warmup_extension_start_utc="2025-04-25", span_start_utc="2025-06-01")
    assert request.touched_start_utc == "2025-04-25"


def test_a_warmup_after_the_span_start_refuses() -> None:
    with pytest.raises(read_route.ReadRouteError):
        _request(warmup_extension_start_utc="2025-07-01", span_start_utc="2025-06-01")


# --------------------------------------------------------------------------
# The derivation route
# --------------------------------------------------------------------------


def test_derivation_needs_its_own_grant(
    sandbox: Path, guards: object, identity: RunIdentity
) -> None:
    """A read grant does not authorise a derivation — playbook §2.5, inside Track A."""
    seen_ledger.declare(
        seen_ledger.SeenDeclaration(
            run_id=identity.run_id,
            span_start_utc="2025-04-25",
            span_end_utc="2026-02-28",
            pairs=("EUR_USD",),
            timeframe="M1",
            purpose="derivation",
        ),
        identity,
    )
    request = derivation.DerivationRequest(read_request=_request())
    with pytest.raises(authorization.AuthorizationError):
        derivation.derive_m15(request, identity, grant=_grant())

    with pytest.raises(NotImplementedError, match=derivation.NOT_IMPLEMENTED_TOKEN):
        derivation.derive_m15(
            request,
            identity,
            grant=_grant(operation=authorization.OPERATION_M15_DERIVATION),
        )


def test_derivation_names_its_delegate_and_audit_status() -> None:
    assert derivation.DELEGATE_QUALNAME == "scripts.m15_gate3a.aggregation.aggregate_m15"
    assert "BLOCKED" in derivation.DELEGATE_AUDIT_STATUS


# --------------------------------------------------------------------------
# The seen-data ledger
# --------------------------------------------------------------------------


def test_the_ledger_is_write_ahead_and_append_only(sandbox: Path, identity: RunIdentity) -> None:
    first = seen_ledger.SeenDeclaration(
        run_id=identity.run_id,
        span_start_utc="2025-05-01",
        span_end_utc="2025-05-31",
        pairs=("EUR_USD",),
        timeframe="M1",
        purpose="one",
    )
    seen_ledger.declare(first, identity)
    seen_ledger.declare(
        seen_ledger.SeenDeclaration(
            run_id=identity.run_id,
            span_start_utc="2025-06-01",
            span_end_utc="2025-06-30",
            pairs=("USD_JPY",),
            timeframe="M15",
            purpose="two",
        ),
        identity,
    )
    assert len(seen_ledger.read_declarations()) == 2


def test_marking_reaches_every_timeframe_over_the_interval(
    sandbox: Path, identity: RunIdentity
) -> None:
    """Rule 4: declaring M15 declares the interval, not one resolution of it."""
    seen_ledger.declare(
        seen_ledger.SeenDeclaration(
            run_id=identity.run_id,
            span_start_utc="2025-05-01",
            span_end_utc="2025-05-31",
            pairs=("EUR_USD",),
            timeframe="M15",
            purpose="m15 survey",
        ),
        identity,
    )
    seen_ledger.assert_declared(
        span_start_utc="2025-05-02", span_end_utc="2025-05-03", pairs=("EUR_USD",)
    )


def test_a_stitched_pair_of_declarations_does_not_cover_a_wider_read(
    sandbox: Path, identity: RunIdentity
) -> None:
    """One declaration must cover the request — otherwise a widened read is recorded narrow."""
    for start, end in (("2025-05-01", "2025-05-15"), ("2025-05-16", "2025-05-31")):
        seen_ledger.declare(
            seen_ledger.SeenDeclaration(
                run_id=identity.run_id,
                span_start_utc=start,
                span_end_utc=end,
                pairs=("EUR_USD",),
                timeframe="M1",
                purpose="half",
            ),
            identity,
        )
    with pytest.raises(seen_ledger.SeenLedgerError):
        seen_ledger.assert_declared(
            span_start_utc="2025-05-01", span_end_utc="2025-05-31", pairs=("EUR_USD",)
        )


def test_a_declaration_must_attribute_to_its_own_run(sandbox: Path, identity: RunIdentity) -> None:
    other = seen_ledger.SeenDeclaration(
        run_id="someone-else",
        span_start_utc="2025-05-01",
        span_end_utc="2025-05-31",
        pairs=("EUR_USD",),
        timeframe="M1",
        purpose="x",
    )
    with pytest.raises(seen_ledger.SeenLedgerError):
        seen_ledger.declare(other, identity)


def test_the_ledger_cannot_be_written_outside_the_scratch_root(sandbox: Path) -> None:
    assert seen_ledger.ledger_path().parent == scratch.scratch_root()


# --------------------------------------------------------------------------
# K record
# --------------------------------------------------------------------------


def _axes(**overrides: str) -> dict[str, str]:
    axes = {
        "pair_set": "PAIRS_20",
        "feature_set": "v4_base",
        "model": "lightgbm_3class",
        "hyperparameters": "default",
        "threshold": "ev_min_0.25",
        "split": "expanding_1d",
    }
    axes.update(overrides)
    return axes


def test_k_counts_distinct_observed_configurations(sandbox: Path, identity: RunIdentity) -> None:
    breadth.record(
        breadth.ConfigurationEntry(run_id=identity.run_id, axes=_axes(), result_observed=True),
        identity,
    )
    # The same configuration again is one evaluation of it, not two.
    breadth.record(
        breadth.ConfigurationEntry(run_id=identity.run_id, axes=_axes(), result_observed=True),
        identity,
    )
    breadth.record(
        breadth.ConfigurationEntry(
            run_id=identity.run_id, axes=_axes(model="lstm"), result_observed=True
        ),
        identity,
    )
    # Recorded but unobserved does not add to K (R-7's own unit).
    breadth.record(
        breadth.ConfigurationEntry(
            run_id=identity.run_id, axes=_axes(model="tcn"), result_observed=False
        ),
        identity,
    )
    assert breadth.current_k() == 2


def test_an_entry_missing_an_axis_refuses(identity: RunIdentity) -> None:
    axes = _axes()
    del axes["split"]
    with pytest.raises(breadth.BreadthRecordError):
        breadth.ConfigurationEntry(run_id=identity.run_id, axes=axes, result_observed=True)


def test_an_entry_with_an_unknown_axis_refuses(identity: RunIdentity) -> None:
    with pytest.raises(breadth.BreadthRecordError):
        breadth.ConfigurationEntry(
            run_id=identity.run_id, axes=_axes(invented="x"), result_observed=True
        )


# --------------------------------------------------------------------------
# Q7's N = 1
# --------------------------------------------------------------------------


def test_the_oos_slice_is_consumed_once(sandbox: Path, identity: RunIdentity) -> None:
    observation = oos_budget.SliceObservation(
        run_id=identity.run_id,
        slice_start_utc="2026-01-01",
        slice_end_utc="2026-02-28",
        purpose="R4",
    )
    assert oos_budget.remaining() == 1
    oos_budget.consume(observation, identity)
    assert oos_budget.remaining() == 0
    with pytest.raises(oos_budget.OosBudgetError, match=oos_budget.BUDGET_EXHAUSTED_TOKEN):
        oos_budget.consume(observation, identity)


def test_the_budget_is_one_and_has_no_runtime_override() -> None:
    """Raising N is a human + ChatGPT loosening, so it must show up in a diff."""
    import inspect

    assert oos_budget.OOS_BUDGET_N == 1
    source = inspect.getsource(oos_budget)
    for ambient in ("os.environ", "getenv", "def set_budget"):
        assert ambient not in source


def test_k_and_n_are_different_budgets(sandbox: Path, identity: RunIdentity) -> None:
    """One slice read scoring twenty configurations spends N=1 and adds to K."""
    oos_budget.consume(
        oos_budget.SliceObservation(
            run_id=identity.run_id,
            slice_start_utc="2026-01-01",
            slice_end_utc="2026-02-28",
            purpose="R4",
        ),
        identity,
    )
    for index in range(3):
        breadth.record(
            breadth.ConfigurationEntry(
                run_id=identity.run_id,
                axes=_axes(threshold=f"ev_min_{index}"),
                result_observed=True,
            ),
            identity,
        )
    assert oos_budget.observations_spent() == 1
    assert breadth.current_k() == 3


# --------------------------------------------------------------------------
# Containment audit
# --------------------------------------------------------------------------


def test_the_containment_audit_reports_contained(guards: object) -> None:
    report = containment.audit()
    failed = [check for check in report["checks"] if not check["passed"]]
    assert failed == [], failed
    assert report["status"] == containment.STATUS_CONTAINED
    assert report["declared_gate_sequence_matches_at_this_head"] is True
    assert report["guards_installed_by_audit"] is False


def test_the_audit_installs_its_own_guards_and_restores_the_process() -> None:
    """A verdict that depends on someone having installed the guards is not a verdict."""
    isolation.uninstall_all()
    report = containment.audit()
    assert report["status"] == containment.STATUS_CONTAINED
    assert report["guards_installed_by_audit"] is True
    assert not isolation.is_installed(), "the audit left the process patched"


def test_the_audit_reports_breached_when_installation_silently_does_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Self-installing must not become self-certifying.

    The audit's own ``install_all`` is replaced by a no-op, so the guards it
    believes it installed are absent. The verdict has to come out BREACHED —
    if it did not, the audit would be reporting on its own bookkeeping.
    """
    isolation.uninstall_all()
    monkeypatch.setattr(isolation, "install_all", lambda: None)
    report = containment.audit()
    assert report["status"] == containment.STATUS_BREACHED
    failed = {check["check"] for check in report["checks"] if not check["passed"]}
    assert {"network", "database"} <= failed
