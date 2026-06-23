"""Outcome resolver for PR-B.1 (plan §8, restricted to the B.1 surface).

Pure functions. PR-B.1 resolves outcomes from authority + raw inventory +
coverage + retention only. Dependency-inventory and pipeline-feasibility
gating (plan §8 steps 5-7) belong to PR-B.2 and are intentionally NOT applied
here. First-run PASS / construction-review is structurally unreachable: the
two PASS-enabling retention classifications are forbidden under first-run mode
and reaching them raises a HALT.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..authority import pair_universe as pu
from ..authority import schema as sa
from ..b1_constants import (
    OUTCOME_INSUFFICIENT,
    OUTCOME_PARTIAL,
    OUTCOME_RETENTION_UNRESOLVED,
    RETENTION_FORBIDDEN_FIRST_RUN,
    RETENTION_REQUIRES_PROBE,
    RETENTION_UNRESOLVED,
)


class GateP1IntegrityError(RuntimeError):
    """Raised when an inspection-integrity invariant is violated."""


@dataclass(frozen=True)
class CandidateOutcome:
    candidate_id: str
    outcome: str
    retention_substatus: str | None
    reason_codes: list[str] = field(default_factory=list)


def resolve_candidate(
    candidate_id: str,
    *,
    pair_outcome: str,
    schema_outcome: str,
    files: list[dict[str, object]],
    pairs: list[str],
    retention_classification: str,
    first_run_mode: bool,
) -> CandidateOutcome:
    """Resolve a single candidate's first-run outcome (PR-B.1 surface)."""
    if not first_run_mode:  # pragma: no cover - PR-B.1 hardcodes first-run
        raise GateP1IntegrityError("PR-B.1 resolver requires first_run_mode=True")

    # 1-2: authority HALTs.
    if schema_outcome == sa.OUTCOME_INTEGRITY_HALT_SCHEMA_AUTHORITY_DRIFT:
        raise GateP1IntegrityError("schema authority drift versus protocol §3.1")
    if schema_outcome == sa.OUTCOME_INTEGRITY_HALT_SOURCE_UNPARSEABLE:
        raise GateP1IntegrityError("schema authority source unparseable")
    if pair_outcome == pu.OUTCOME_INTEGRITY_HALT_CANONICAL_UNPARSEABLE:
        raise GateP1IntegrityError("canonical pair universe unparseable")

    # Forbidden retention classifications cannot occur on the first run.
    if retention_classification in RETENTION_FORBIDDEN_FIRST_RUN:
        raise GateP1IntegrityError(
            f"first-run-unreachable retention classification '{retention_classification}' reached"
        )

    reasons: list[str] = []
    outcome: str | None = None

    # 3: pair authority ambiguous -> PARTIAL (continue to retention substatus).
    if pair_outcome == pu.OUTCOME_AMBIGUOUS:
        outcome = OUTCOME_PARTIAL
        reasons.append("PAIR_UNIVERSE_AUTHORITY_AMBIGUOUS")

    # 4: raw inventory insufficient -> INSUFFICIENT.
    present_pairs = {f["pair"] for f in files if f.get("present") and f.get("schema_valid")}
    missing = [p for p in pairs if p not in present_pairs]
    if missing:
        outcome = OUTCOME_INSUFFICIENT
        reasons.append(f"RAW_INVENTORY_INSUFFICIENT_PAIRS:{','.join(sorted(missing)[:5])}")

    # (PR-B.2 dependency/pipeline gating intentionally omitted here.)

    # 9: retention classification.
    if retention_classification == RETENTION_REQUIRES_PROBE:
        substatus = RETENTION_REQUIRES_PROBE
        if outcome is None:
            outcome = OUTCOME_PARTIAL
            reasons.append("ALL_CHECKED_SUFFICIENT_RETENTION_PROBE_REQUIRED")
    elif retention_classification == RETENTION_UNRESOLVED:
        substatus = RETENTION_UNRESOLVED
        if outcome is None:
            outcome = OUTCOME_RETENTION_UNRESOLVED
            reasons.append("ALL_CHECKED_SUFFICIENT_RETENTION_UNRESOLVED")
    else:  # pragma: no cover - guarded above
        raise GateP1IntegrityError(
            f"unexpected retention classification '{retention_classification}'"
        )

    return CandidateOutcome(
        candidate_id=candidate_id,
        outcome=outcome,
        retention_substatus=substatus,
        reason_codes=reasons,
    )


def resolve_top_level(candidates: list[CandidateOutcome], *, first_run_mode: bool) -> str:
    """Resolve the top-level outcome by precedence (plan §9.2). PASS unreachable."""
    if not first_run_mode:  # pragma: no cover
        raise GateP1IntegrityError("PR-B.1 resolver requires first_run_mode=True")
    if not candidates:
        return OUTCOME_INSUFFICIENT

    outcomes = {c.outcome for c in candidates}
    if OUTCOME_PARTIAL in outcomes:
        return OUTCOME_PARTIAL
    if outcomes == {OUTCOME_RETENTION_UNRESOLVED}:
        return OUTCOME_RETENTION_UNRESOLVED
    if OUTCOME_RETENTION_UNRESOLVED in outcomes and OUTCOME_INSUFFICIENT in outcomes:
        # Some candidates retention-unresolved, some insufficient: not all
        # insufficient, so report the milder retention-unresolved precedence.
        return OUTCOME_RETENTION_UNRESOLVED
    return OUTCOME_INSUFFICIENT
