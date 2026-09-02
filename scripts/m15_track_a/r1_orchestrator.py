"""The **one** formal entry point for Track A stage R1.

Why this module exists
----------------------

Every piece R1 needs has been built, reviewed and merged — the gated read, the
seen-data ledger, the derivation route, the row-scope layer, the breadth record,
the survey. What did not exist was a **route through them**. Playbook §5a said so
in as many words: "there is no R1 orchestrator in the repository …
``DerivationRequest(`` appears in no committed script and no module in
``scripts/m15_track_a/`` has a ``__main__``; the only read → derive → survey
composition is a pytest fixture."

A composition that lives only in a fixture is a composition nobody has reviewed
as the thing that will run. Worse, the fixture built its `ReadRequest` **twice**,
which is precisely the failure mode §5a warns a runner about: two objects that
agree today and can diverge tomorrow, on a route where one is gated and the
other is used.

So this module binds the order, and the order is the deliverable. It contains no
research logic. It re-implements no read, derivation or survey semantics; it
calls the committed ones and refuses to continue when any of them refuses.

What it is not
--------------

**It is not an authorisation.** Calling it with two valid grants is what an
authorised R1 run looks like; obtaining those grants is a human act recorded in
``docs/governance/``, and running it at all needs an explicit human + ChatGPT
execution command naming the operation, span, pairs, timeframe and head. This
module cannot supply any of that, and it does not try: it takes the grants as
arguments and verifies them, and it has **no default** for either.

**It stops at R1.** There is no R2 stage, no OOS read, no candidate selection, no
strategy search and no Formal Confirmation reachable from here, by construction
rather than by convention — `scripts/m15_track_a/oos_budget.py` is not imported,
and a test asserts the module's whole call surface against a declared list.

The sequence, and why it is this one
------------------------------------

::

    preflight                      no file is opened; every refusal costs 0 bytes
      -> declare the seen interval write-ahead, BEFORE the read
      -> read_historical           Grant A; the gated M1 read
      -> verify the read is what was authorised
      -> derive_m15                Grant B; the SAME ReadRequest object
      -> verify the derivation is what was authorised
      -> record breadth K          result_observed=False: R1 scores nothing
      -> r1_survey.survey          the committed survey, unmodified
      -> STOP

Three properties are load-bearing and each is a refusal rather than a
convention:

* **One `RunIdentity` reaches every stage.** It is taken once and passed down;
  nothing here constructs a second one. A run whose ledger entry, breadth entry
  and survey disagree about who ran is not one run.
* **One `ReadRequest` object** is built in `preflight` and handed to both the
  read and the derivation. Building it twice is what §5a told a runner not to do.
* **No stage runs after a failed stage.** There is no `try`/`except` anywhere in
  the sequence: a refusal from any committed guard propagates and the run ends
  where it failed. Nothing is retried, nothing is degraded, and no partial
  result is returned.

The timeframe pin, and the minimal diff
---------------------------------------

`DERIVATION_ROUTE_DOES_NOT_PIN_ITS_TIMEFRAME_TO_THE_COMMITTED_SOURCE_CONSTANT_REFERRED`
records that `derive_m15` compares its grant to its request and its request to
its read — three caller-supplied strings — while `read_historical` pins its grant
against the committed `SOURCE_TIMEFRAME`. That referral stays open, because
closing it means editing `derivation.py`.

It does not need to be closed for the **formal** route to be safe, and closing it
here would be the larger diff. `PLAN_TIMEFRAME` is `read_route.SOURCE_TIMEFRAME`,
`preflight` refuses a plan naming anything else, and the single `ReadRequest` it
builds is the object both routes see. A non-`M1` derivation is therefore
unreachable through this entry point — which is the property asked for — while
`derivation.py` keeps the semantics three reviews have already been through.
The referral remains for direct callers, and this module is why there should not
be any.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final

from scripts.m15_gate3a.pair_authority import PAIRS_20, PairAuthorityError, canonical_pair
from scripts.m15_track_a import (
    authorization,
    breadth,
    containment,
    derivation,
    isolation,
    r1_survey,
    read_route,
    scratch,
    seen_ledger,
)
from scripts.m15_track_a.identity import RunIdentity
from scripts.m15_track_a.oos_slice import DEVELOPMENT_END_UTC, DEVELOPMENT_START_UTC

#: The stage this route runs, and the only one.
STAGE: Final[str] = "R1"

#: The timeframe R1's input is, taken from the read route rather than restated.
PLAN_TIMEFRAME: Final[str] = read_route.SOURCE_TIMEFRAME

#: What a passed preflight establishes — and what it does not.
PREFLIGHT_PASSED: Final[str] = (
    "TRACK_A_R1_PREFLIGHT_PASSED_ON_THE_RECORDED_GRANTS_AND_THE_MEASURED_IMPLEMENTATION"
)

#: The terminal status. R1 produces a survey and stops.
R1_COMPLETE: Final[str] = "TRACK_A_R1_SURVEY_COMPLETE_STOP_NO_NEXT_STAGE_IS_REACHED_FROM_HERE"

#: Recorded on the breadth entry so `K` is explicit rather than absent.
BREADTH_NOTE: Final[str] = (
    "R1 is a survey, not a configuration: no model, no features, no threshold. "
    "Recorded with result_observed=False because nothing was scored."
)

#: The seen-data purpose written into the declaration.
SEEN_PURPOSE: Final[str] = "Track A stage R1 survey of the authorised development corpus"

#: The playbook checklist that must record 15 of 15 on the head being run, and
#: **why this module does not read it**.
#:
#: The first drafting of preflight opened the playbook and counted the boxes.
#: `containment.audit()` immediately reported
#: `TRACK_A_EXECUTION_CONTAINMENT_PROBE_FAILED`: `_check_single_read_route` sweeps
#: every module in this package for a file-opening call, and `read_text()` is one.
#: The fix that would have silenced it — adding this module to
#: `_PERMITTED_FILE_OPENERS` — widens the declared read surface, and that dict's
#: own comment records what a blanket exemption bought last time.
#:
#: So the checklist is a **gate-time obligation**, in the same category as the
#: ancestry check the grant record already handles that way: "git is unreachable
#: from inside a gated read". It is verified outside the gated surface — by CI, in
#: `tests/m15_track_a/test_r1_orchestrator.py::
#: test_the_playbook_checklist_is_complete_at_this_head`, which runs on every
#: push and fails the build if a box is outstanding — rather than by a module that
#: would have to open a file to do it.
#:
#: This is not a weakening: a run-time count read from inside the process could
#: only ever check the *record*, and a document cannot verify itself. §5a says in
#: the same section that 15 of 15 is not permission to read.
PLAYBOOK_RELATIVE: Final[str] = "docs/governance/m15_audit_playbook.md"
PREFLIGHT_CHECKLIST_HEADING: Final[str] = "## 5a."
PREFLIGHT_CHECKLIST_ITEMS: Final[int] = 15
PREFLIGHT_CHECKLIST_OBLIGATION: Final[str] = (
    "PLAYBOOK_5A_COMPLETENESS_IS_A_GATE_TIME_OBLIGATION_VERIFIED_IN_CI_NOT_FROM_INSIDE_THE_GATED_SURFACE"
)


class R1OrchestratorError(RuntimeError):
    """Raised when the formal R1 route refuses to start or to continue."""


@dataclass(frozen=True)
class R1Plan:
    """What one R1 run is asked to do.

    Deliberately tiny, and deliberately without defaults for the scope fields:
    a plan that filled itself in would let a caller run a differently-scoped R1
    by omitting an argument.
    """

    span_start_utc: str
    span_end_utc: str
    pairs: tuple[str, ...]
    timeframe: str = PLAN_TIMEFRAME
    purpose: str = SEEN_PURPOSE

    def __post_init__(self) -> None:
        for name, value in (
            ("span_start_utc", self.span_start_utc),
            ("span_end_utc", self.span_end_utc),
            ("timeframe", self.timeframe),
            ("purpose", self.purpose),
        ):
            if type(value) is not str or not value.strip():  # noqa: E721
                raise R1OrchestratorError(f"{name} must be a non-empty plain str")
        if type(self.pairs) is not tuple or not self.pairs:  # noqa: E721
            raise R1OrchestratorError("pairs must be a non-empty tuple")


@dataclass(frozen=True)
class PreflightReport:
    """What preflight established, item by item, before any file was opened."""

    status: str
    checks: tuple[tuple[str, str], ...]
    fingerprint: str
    request: read_route.ReadRequest

    def as_record(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "fingerprint": self.fingerprint,
            "checks": [{"check": name, "detail": detail} for name, detail in self.checks],
        }


@dataclass(frozen=True)
class R1Result:
    """One completed R1 run. The survey, and the fact that nothing follows it."""

    run_id: str
    status: str
    preflight: PreflightReport
    survey: r1_survey.R1Survey
    breadth_k: int
    seen_declaration: str
    next_stage: None = field(default=None)

    def as_record(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "stage": STAGE,
            "next_stage": self.next_stage,
            "breadth_k": self.breadth_k,
            "seen_declaration": self.seen_declaration,
            "preflight": self.preflight.as_record(),
            "survey": self.survey.as_record(),
        }


def _refuse(reason: str) -> None:
    raise R1OrchestratorError(f"Track A R1 refused: {reason}")


def _canonical_pairs(pairs: tuple[str, ...]) -> tuple[str, ...]:
    try:
        canonical = tuple(canonical_pair(pair) for pair in pairs)
    except PairAuthorityError as exc:
        _refuse(str(exc))
        raise  # unreachable; _refuse always raises
    if len(set(canonical)) != len(canonical):
        _refuse("the plan names one pair more than once")
    return canonical


def preflight(
    plan: R1Plan,
    identity: RunIdentity,
    *,
    read_grant: Any,
    derivation_grant: Any,
) -> PreflightReport:
    """Establish that an R1 run may start. **Opens no file and reads no data.**

    Every refusal below costs zero bytes, which is the point: the R1 execution
    command of 2026-08-31 was refused because six things nobody had checked
    turned out to be false, and the only reason that was cheap is that nobody
    had read anything yet.

    What this does **not** establish: that the grants it is handed were actually
    approved by a human. `ReadGrant` records an approval and enforces its scope;
    it does not verify that the approval happened, so constructing one is never
    the act of granting it. Nor does a complete §5a make a run permitted — the
    section says so itself.
    """
    checks: list[tuple[str, str]] = []

    def note(name: str, detail: str) -> None:
        checks.append((name, detail))

    if type(plan) is not R1Plan:  # noqa: E721
        _refuse(f"plan must be exactly an R1Plan, not a {type(plan).__name__}")
    if type(identity) is not RunIdentity:  # noqa: E721
        _refuse(f"identity must be exactly a RunIdentity, not a {type(identity).__name__}")

    # --- isolation and containment, before anything else ------------------
    if not isolation.is_installed():
        _refuse("the isolation guards are not installed")
    report = containment.audit()
    status = report.get("status") if isinstance(report, dict) else None
    if status != containment.STATUS_CONTAINED:
        _refuse(f"the containment audit reports {status!r}, not {containment.STATUS_CONTAINED}")
    note("isolation_and_containment", str(status))

    # --- the checklist, carried as an obligation rather than opened -------
    note("playbook_5a", PREFLIGHT_CHECKLIST_OBLIGATION)

    # --- the plan is the ruled scope, not a caller's idea of it -----------
    if plan.timeframe != PLAN_TIMEFRAME:
        _refuse(
            f"the plan names timeframe {plan.timeframe!r}; the formal R1 route reads "
            f"{PLAN_TIMEFRAME} source bars. This is the orchestrator-level pin that keeps a "
            "non-M1 derivation unreachable from here."
        )
    if (plan.span_start_utc, plan.span_end_utc) != (DEVELOPMENT_START_UTC, DEVELOPMENT_END_UTC):
        _refuse(
            f"the plan spans {plan.span_start_utc}..{plan.span_end_utc}; the authorised "
            f"development corpus is {DEVELOPMENT_START_UTC}..{DEVELOPMENT_END_UTC}. R1 surveys "
            "the corpus it is granted, not a slice of it chosen at run time."
        )
    canonical = _canonical_pairs(plan.pairs)
    if set(canonical) != set(PAIRS_20):
        missing = sorted(set(PAIRS_20) - set(canonical))
        extra = sorted(set(canonical) - set(PAIRS_20))
        _refuse(
            f"the plan's pairs are not the registered universe (missing {missing}, "
            f"extra {extra}). R1 surveys PAIRS_20."
        )
    note(
        "plan_scope",
        f"{plan.span_start_utc}..{plan.span_end_utc}, {len(canonical)} pairs, {plan.timeframe}",
    )

    # --- the single request object both routes will see -------------------
    request = read_route.ReadRequest(
        span_start_utc=plan.span_start_utc,
        span_end_utc=plan.span_end_utc,
        pairs=tuple(sorted(canonical)),
        timeframe=plan.timeframe,
        # No warm-up. A warm-up extension before ``DEVELOPMENT_START_UTC`` is
        # refused rather than trimmed, and there is nothing authorised before
        # it, so the formal route asks for none. The survey's ATR seeds inside
        # the corpus instead.
        warmup_extension_start_utc=plan.span_start_utc,
    )

    # --- the quarantines, on the declared interval, before any read -------
    read_route.assert_span_admissible(request)
    read_route.assert_development_only(request)
    note(
        "quarantines",
        "design bounds, dead window and EXPLORATORY_OOS_SLICE refused on the touched interval",
    )

    # --- the two grants ---------------------------------------------------
    fingerprint = containment.implementation_fingerprint()
    for label, grant, operation in (
        ("read", read_grant, authorization.OPERATION_HISTORICAL_READ),
        ("derivation", derivation_grant, authorization.OPERATION_M15_DERIVATION),
    ):
        if grant is None:
            _refuse(
                f"no {operation} grant was supplied. This route has no default and no fallback: "
                "a missing grant is a missing human decision."
            )
        if type(grant) is not authorization.ReadGrant:  # noqa: E721
            _refuse(f"the {label} grant must be exactly a ReadGrant, not a {type(grant).__name__}")
        if grant.operation != operation:
            _refuse(
                f"the {label} grant names {grant.operation!r}, not {operation!r}. A read grant "
                "does not authorise a derivation (policy §2.5), and neither covers the other."
            )
        if grant.approved_implementation_fingerprint != fingerprint:
            _refuse(
                f"the {label} grant was approved against implementation "
                f"{grant.approved_implementation_fingerprint[:8]}… and this tree hashes to "
                f"{fingerprint[:8]}…. The approval does not describe what would run."
            )
        # Re-checked here as well as inside each route, on purpose: this is the
        # last point at which a refusal costs nothing.
        if not grant.covers(
            operation=operation,
            span_start_utc=request.touched_start_utc,
            span_end_utc=request.span_end_utc,
            pairs=request.pairs,
            timeframe=request.timeframe,
        ):
            _refuse(f"the {label} grant does not cover the planned scope")
        note(f"grant_{label}", f"{grant.operation} {grant.span_start_utc}..{grant.span_end_utc}")

    if read_grant.approved_head_sha != derivation_grant.approved_head_sha:
        _refuse(
            f"the two grants name different approved heads "
            f"({read_grant.approved_head_sha[:8]}… and "
            f"{derivation_grant.approved_head_sha[:8]}…). One run, one approved implementation."
        )
    if identity.code_sha != read_grant.approved_head_sha:
        _refuse(
            f"the run identity names code_sha {identity.code_sha[:8]}… and the grants were "
            f"approved against {read_grant.approved_head_sha[:8]}…. Both are caller-asserted "
            "strings — the fingerprint above is what is measured — but they must at least agree "
            "about which head this run believes it is."
        )
    note("approved_head", read_grant.approved_head_sha)
    note("fingerprint", fingerprint)

    # --- the records this run will write ----------------------------------
    for name, path in (
        ("scratch_root", scratch.scratch_root()),
        ("ledger_root", scratch.ledger_root()),
    ):
        if not scratch.is_writable(path):
            _refuse(f"the {name} {path} is not writable by this run")
    seen_ledger.assert_writable(seen_ledger.ledger_path())
    seen_ledger.assert_writable(seen_ledger.grant_ledger_path())
    breadth.assert_writable(breadth.breadth_path())
    note("records", "seen ledger, grant ledger and breadth record are all writable")

    return PreflightReport(
        status=PREFLIGHT_PASSED,
        checks=tuple(checks),
        fingerprint=fingerprint,
        request=request,
    )


def run_r1(
    plan: R1Plan,
    identity: RunIdentity,
    *,
    read_grant: Any,
    derivation_grant: Any,
) -> R1Result:
    """Run stage R1 once, in order, and stop.

    **This is the formal Track A R1 route.** Calling the stages by hand is not,
    and the reason is the ordering below rather than a preference: the seen-data
    declaration is written *before* the read, the same request object reaches
    both gated routes, one identity reaches every record, and a refusal anywhere
    ends the run where it happened.

    There is no `try`/`except` in this function. A committed guard that refuses
    is the answer, not an exception to recover from.
    """
    report = preflight(plan, identity, read_grant=read_grant, derivation_grant=derivation_grant)
    request = report.request

    # 1. Write-ahead. The interval is declared **before** it is touched, so a
    #    run that dies mid-read still leaves the record that it was going to be
    #    read. `EXPLORATORY_SEEN_DATA` does not return, and a discarded run
    #    spends it just the same.
    declaration = seen_ledger.SeenDeclaration(
        run_id=identity.run_id,
        span_start_utc=request.touched_start_utc,
        span_end_utc=request.span_end_utc,
        pairs=request.pairs,
        timeframe=request.timeframe,
        purpose=plan.purpose,
    )
    declared_at = seen_ledger.declare(declaration, identity)

    # 2. The gated M1 read, under Grant A.
    read = read_route.read_historical(request, identity, grant=read_grant)
    if type(read) is not read_route.HistoricalRead:  # noqa: E721
        _refuse(f"the read route returned a {type(read).__name__}, not a HistoricalRead")
    if read.run_id != identity.run_id:
        _refuse(f"the read records run {read.run_id!r} and this run is {identity.run_id!r}")
    if read.timeframe != PLAN_TIMEFRAME:
        _refuse(f"the read returned {read.timeframe} bars, not {PLAN_TIMEFRAME}")
    if read.operation != authorization.OPERATION_HISTORICAL_READ:
        _refuse(f"the read records operation {read.operation!r}")

    # 3. The authorised derivation, under Grant B, on the **same** request
    #    object the read was gated with. Building a second one here is the
    #    failure mode playbook §5a names for a runner.
    derived = derivation.derive_m15(
        derivation.DerivationRequest(read_request=request, read=read),
        identity,
        grant=derivation_grant,
    )
    if type(derived) is not derivation.DerivedM15:  # noqa: E721
        _refuse(f"the derivation route returned a {type(derived).__name__}, not a DerivedM15")
    if derived.run_id != identity.run_id:
        _refuse(f"the derivation records run {derived.run_id!r}")
    if derived.operation != authorization.OPERATION_M15_DERIVATION:
        _refuse(f"the derivation records operation {derived.operation!r}")
    if tuple(sorted(derived.bars_by_pair)) != request.pairs:
        _refuse("the derivation covered a different pair set from the one that was gated")

    # 4. Breadth. `result_observed=False` because R1 scores nothing, so `K` is
    #    explicitly 0 rather than absent.
    breadth.record(
        breadth.ConfigurationEntry(
            run_id=identity.run_id,
            axes={axis: "r1_survey_no_configuration" for axis in breadth.CONFIGURATION_AXES},
            result_observed=False,
            note=BREADTH_NOTE,
        ),
        identity,
    )
    breadth_k = breadth.current_k()

    # 5. The committed survey, unmodified. No metric, threshold or strategy
    #    logic is added here; Route B and the declared-label coverage
    #    diagnostic are exactly what the survey already does.
    survey = r1_survey.survey(
        derived,
        containment_status=containment.STATUS_CONTAINED,
        breadth_k=breadth_k,
    )
    if survey.run_id != identity.run_id:
        _refuse(f"the survey records run {survey.run_id!r}")

    # 6. Stop. R1 has produced its outputs and this route reaches no further
    #    stage: no R2, no OOS read, no candidate selection, no strategy search,
    #    no Formal Confirmation. `next_stage` is None and stays None.
    return R1Result(
        run_id=identity.run_id,
        status=R1_COMPLETE,
        preflight=report,
        survey=survey,
        breadth_k=breadth_k,
        seen_declaration=str(declared_at),
    )


__all__ = [
    "BREADTH_NOTE",
    "PREFLIGHT_CHECKLIST_OBLIGATION",
    "PLAN_TIMEFRAME",
    "PREFLIGHT_CHECKLIST_ITEMS",
    "PREFLIGHT_PASSED",
    "R1_COMPLETE",
    "SEEN_PURPOSE",
    "STAGE",
    "PreflightReport",
    "R1OrchestratorError",
    "R1Plan",
    "R1Result",
    "preflight",
    "run_r1",
]
