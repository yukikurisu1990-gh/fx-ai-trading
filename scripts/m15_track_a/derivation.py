"""The **one** M1→M15 research derivation route for Track A.

`RESEARCH_SCRATCH_M15_DERIVATION_ROUTE_NOT_SELECTED` named three ways to obtain
M15 bars for Track A, each with a cost:

  (i)   run the **committed** ``scripts.m15_gate3a.aggregation.aggregate_m15`` on
        real rows — no code change and no refusal trips, because it is a pure
        function over row dicts and ``assert_synthetic_only`` has no caller
        outside its own test.  What has contained it is the absence of a reader
        and its BLOCKED source audit;
  (ii)  write a **second**, fenced research aggregator — the two-implementation
        structure that produced one identical weekend-gap defect twice;
  (iii) complete the source audit first — the cost the split exists to avoid.

**Arm (i) is selected**, and this module is where that selection becomes visible
in a diff rather than being a decision someone reports having taken.

Why (i) and not (ii)
--------------------

(ii) is the only arm that creates a *new* way to be wrong.  The committed
aggregator's defects are known, enumerated and audited — four re-check rounds
have gone through it — whereas a second aggregator starts at zero and diverges
silently, which is exactly what INV-1 and the weekend-gap defect were.  One
implementation with a BLOCKED audit is a known quantity; two implementations are
two unknown ones.

What selecting (i) costs, stated rather than absorbed
-----------------------------------------------------

The committed aggregator's source audit stands **BLOCKED**
(`M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES`),
so Track A would be giving an audit-blocked module its first real-data caller.
That is a real cost and it is **not** paid by this module: it is paid by the
authorisation, which names the operation and the head it is granted against, and
by the output being `NON_DECISION_BEARING_EXPLORATORY_ONLY` — a Track A
derivation is **not** the §4 artifact and may never be recorded as one.

Like the read route, the body is absent
---------------------------------------

The gates are written and tested; the derivation itself raises.  A future
implementing PR supplies the body and inherits every gate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final

from scripts.m15_gate3a.aggregation import BUCKET_MINUTES, FULL_BUCKET_SOURCE_BARS
from scripts.m15_track_a import authorization, isolation, seen_ledger
from scripts.m15_track_a.identity import RunIdentity
from scripts.m15_track_a.read_route import ReadRequest, assert_span_admissible

#: The selected arm, named so the choice is greppable.
SELECTED_ROUTE: Final[str] = "arm_i_committed_gate3a_aggregate_m15_on_research_scratch_output"

#: The committed callable this route delegates to.  Named as a string as well as
#: imported, so a containment audit can assert the binding without importing.
DELEGATE_QUALNAME: Final[str] = "scripts.m15_gate3a.aggregation.aggregate_m15"

#: What a Track A derivation is **not**.
NOT_THE_SECTION_4_ARTIFACT: Final[str] = (
    "A_TRACK_A_DERIVATION_IS_NOT_THE_SECTION_4_ARTIFACT_AND_MAY_NOT_BE_RECORDED_AS_ONE"
)

#: The audit status the selected arm inherits, restated so it is not forgotten.
DELEGATE_AUDIT_STATUS: Final[str] = (
    "M15_AGGREGATION_DATASET_MACHINERY_SOURCE_AUDIT_BLOCKED_PENDING_TARGETED_FIXES"
)

NOT_IMPLEMENTED_TOKEN: Final[str] = "TRACK_A_M15_DERIVATION_NOT_IMPLEMENTED_NO_DATA_IS_DERIVED"


class DerivationRouteError(RuntimeError):
    """Raised when a Track A derivation is refused."""


@dataclass(frozen=True)
class DerivationRequest:
    """One M1→M15 research derivation over a declared interval."""

    read_request: ReadRequest

    @property
    def bucket_minutes(self) -> int:
        """From the committed aggregator, never re-declared here."""
        return BUCKET_MINUTES

    @property
    def full_bucket_source_bars(self) -> int:
        """From the committed aggregator: an event needs ``n_source_bars == 15``."""
        return FULL_BUCKET_SOURCE_BARS


def derive_m15(
    request: DerivationRequest,
    identity: RunIdentity,
    *,
    grant: Any = None,
) -> object:
    """The single Track A derivation route.  Gates, then raises NotImplementedError.

    The gates are the read route's, with the operation changed: a derivation is
    a distinct authorisation from a read, so a grant for one does not cover the
    other.  playbook §2.5 forbids chaining irreversible stages, and this is the
    same principle inside Track A.
    """
    if not isolation.is_installed():
        raise DerivationRouteError(
            "Track A derivation refused: isolation guards are not installed."
        )

    read_request = request.read_request
    authorization.require_authorization(
        grant,
        operation=authorization.OPERATION_M15_DERIVATION,
        span_start_utc=read_request.touched_start_utc,
        span_end_utc=read_request.span_end_utc,
        pairs=read_request.pairs,
        timeframe=read_request.timeframe,
    )

    assert_span_admissible(read_request)

    seen_ledger.assert_declared(
        span_start_utc=read_request.touched_start_utc,
        span_end_utc=read_request.span_end_utc,
        pairs=read_request.pairs,
    )

    raise NotImplementedError(
        f"{NOT_IMPLEMENTED_TOKEN}: every gate passed and nothing was derived. The selected "
        f"route is {SELECTED_ROUTE!r}, delegating to {DELEGATE_QUALNAME} — whose audit status "
        f"is {DELEGATE_AUDIT_STATUS}. Its output is "
        f"NON_DECISION_BEARING_EXPLORATORY_ONLY and {NOT_THE_SECTION_4_ARTIFACT}. "
        f"Run {identity.run_id!r}."
    )


__all__ = [
    "DELEGATE_AUDIT_STATUS",
    "DELEGATE_QUALNAME",
    "NOT_IMPLEMENTED_TOKEN",
    "NOT_THE_SECTION_4_ARTIFACT",
    "SELECTED_ROUTE",
    "DerivationRequest",
    "DerivationRouteError",
    "derive_m15",
]
