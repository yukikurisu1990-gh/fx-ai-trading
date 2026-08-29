"""Track A (Exploratory M15 Research) execution infrastructure — R1 enablement.

This package exists to make **one** future operation safe: the first real-data
read of Track A's R1 descriptive survey.  It does **not** perform that read, and
nothing here becomes usable without an explicit human + ChatGPT authorisation
carried in-process (:mod:`scripts.m15_track_a.authorization`).

The governing contract is ``docs/design/m15_minimum_research_gate.md`` §8.11
(the two-track split), §8.12 (governance consistency) and §8.13 (the semantic
cleanup).  Those sections are ``RULED_AS_RECORDED`` on an unmerged PR and carry
``APPROVAL_IDENTIFIER_PENDING_UNTIL_MERGE``; this package is written against
them and is likewise **not** an authorisation.

What the modules are for
------------------------

* :mod:`~scripts.m15_track_a.authorization` — the single gate. Every route that
  could reach real data asks it first, and it refuses unless a caller has
  supplied a grant naming the operation, the span and the head SHA.
* :mod:`~scripts.m15_track_a.scratch` — the one write root (Q8). Everything
  Track A writes goes beneath it; everywhere else refuses.
* :mod:`~scripts.m15_track_a.identity` — run identity and the calendar
  semantics label a run declares.
* :mod:`~scripts.m15_track_a.seen_ledger` — the write-ahead
  ``EXPLORATORY_SEEN_DATA`` ledger. Intent is declared *before* a read.
* :mod:`~scripts.m15_track_a.breadth` — the ``K`` record, in R-7's unit.
* :mod:`~scripts.m15_track_a.oos_budget` — Q7's ``N = 1`` on the
  ``EXPLORATORY_OOS_SLICE``.
* :mod:`~scripts.m15_track_a.read_route` — the **single** historical read
  route, gated.
* :mod:`~scripts.m15_track_a.derivation` — the **single** M1→M15 research
  derivation route, gated.
* :mod:`~scripts.m15_track_a.isolation` — network / broker / external DB /
  live / demo / order submission, all refused.
* :mod:`~scripts.m15_track_a.containment` — the Track A containment audit.

What this package is not
------------------------

It computes no strategy metric, fits nothing, evaluates nothing, and reads no
market data.  It contains no formal-evidence writer and produces no artifact the
evidence tree would accept.  Every output it can produce is
``NON_DECISION_BEARING_EXPLORATORY_ONLY``.
"""

from __future__ import annotations

from typing import Final

#: The completion status this package targets.  It means the **apparatus** is
#: built — never that anything has been read, run or concluded.
#:
#: Read "PENDING" as naming the *last* outstanding condition, not the only one.
#: :data:`OUTSTANDING_CONDITIONS` is the full list, and every entry of it is
#: unmet at the head that introduced this constant.
INFRASTRUCTURE_STATUS: Final[str] = (
    "TRACK_A_R1_EXECUTION_INFRASTRUCTURE_READY_PENDING_EXPLICIT_DATA_READ_AUTHORISATION"
)

#: Everything that must happen before a Track A R1 read, in order.  Building
#: this package is none of them.
OUTSTANDING_CONDITIONS: Final[tuple[str, ...]] = (
    "PR #451 (the Two-Track contract) approved and merged — until then "
    "THE_TWO_TRACK_SECTIONS_ARE_RULED_AS_RECORDED_AND_NOT_YET_CITABLE_AS_AUTHORITY",
    "GOVERNANCE_PROPAGATION_COMPLETE as the P-1..P-15 predicate on a named master SHA",
    "the Minimum Research Execution Gate reviewed, approved and merged on a named head",
    "an explicit human + ChatGPT real-data read authorisation naming operation, span, "
    "pairs, timeframe and approved head SHA",
)

#: Classification stamped on every Track A output.
OUTPUT_CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"

#: Secondary classification.  §8.11.2 and §8.12.2 require **both** labels on
#: Track A output; carrying only the first is the shape that lets a scratch
#: file read as an ordinary research result.
OUTPUT_CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

#: Always binding, and repeated here so a reader of this package alone sees them.
PRODUCTION_NOT_CLAIMED: Final[str] = "PRODUCTION_READINESS_NOT_CLAIMED"
EXECUTION_NOT_PERFORMED: Final[str] = "NO_EXECUTION_PERFORMED"

#: The contract sections this package implements, cited so a reader can check it.
GOVERNING_SECTIONS: Final[tuple[str, ...]] = (
    "docs/design/m15_minimum_research_gate.md §8.11",
    "docs/design/m15_minimum_research_gate.md §8.12",
    "docs/design/m15_minimum_research_gate.md §8.13",
)

__all__ = [
    "EXECUTION_NOT_PERFORMED",
    "GOVERNING_SECTIONS",
    "INFRASTRUCTURE_STATUS",
    "OUTSTANDING_CONDITIONS",
    "OUTPUT_CLASSIFICATION",
    "OUTPUT_CLASSIFICATION_SECONDARY",
    "PRODUCTION_NOT_CLAIMED",
]
