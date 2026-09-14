"""FX spot active-alpha research: the programme's authoritative status, and what reopens it.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

The Human + ChatGPT decision of 2026-09-14 accepted Track 1's Case C and paused
active-alpha research on FX spot. This module is the machine-readable copy of
`docs/research/m15_fx_spot_active_alpha_research_pause.md`; tests pin the two to
each other and to the hypothesis ledger, so a later session cannot read a
different state from one than from the other.

Nothing here reads data, and nothing here authorises anything. A status is a
record; resuming is an act, and only an explicit Human + ChatGPT decision is one.
"""

from __future__ import annotations

from typing import Final

from scripts.research.model_learning import PROTECTED_SPANS

PAUSE_DECISION_DATE: Final[str] = "2026-09-14"

#: The programme state. Paused is not closed and is not a claim about FX.
PROGRAMME_STATUS: Final[str] = "FX_SPOT_ACTIVE_ALPHA_RESEARCH_PAUSED"
NOT_CLAIMED: Final[tuple[str, ...]] = ("FX_HAS_NO_EDGE", "ALPHA_SUPPORTED")

#: Ruled statuses, each as the decision worded it.
STATUSES: Final[dict[str, str]] = {
    "track_1_continuous_currency_portfolio": (
        "CONTINUOUS_CURRENCY_PORTFOLIO_ARCHITECTURE_NOT_SUPPORTED_IN_SEEN_DEVELOPMENT"
    ),
    "efficiency_bundle": "TURNOVER_REDUCTION_MECHANISM_SUPPORTED",
    "track_3_event_volatility_overlay": "NOT_STARTED_BASE_EDGE_REQUIRED",
    "complex_ml": "NOT_AUTHORISED_NO_POSITIVE_BASE_EVIDENCE",
    "post_hoc_currency_reversal_observation": "POST_HOC_EXPLORATORY_NON_DECISION_BEARING",
}

#: Principles the decision made explicit.
PRINCIPLES: Final[tuple[str, ...]] = (
    "EFFICIENCY_CANNOT_RESCUE_NEGATIVE_EXPECTED_RETURN",
    "COMPLEXITY_REQUIRES_POSITIVE_BASE_EVIDENCE",
    "A_FAILED_RULE_IS_NOT_AN_INVERTED_RULE",
)

#: Ways a negative base result may not be rescued.
PROHIBITED_RESCUES: Final[tuple[str, ...]] = (
    "event filter",
    "volatility filter",
    "regime filter",
    "horizon change",
    "sign inversion of a closed or adjacent family",
    "re-pre-registration of the post-hoc currency reversal observation",
    "leverage or volatility-target changes",
    "turnover or cost-efficiency mechanisms offered as alpha",
)

COMPLEX_ML_NOT_AUTHORISED: Final[tuple[str, ...]] = (
    "LightGBM expansion",
    "non-linear ML",
    "HMM",
    "neural networks",
    "representation learning",
    "complex ensembles",
)

#: Prospective policy. Past pre-registrations and verdicts are not rewritten.
TAIL_POLICY: Final[str] = "TAIL_CONCENTRATION_HARD_KILL_DEMOTED_TO_ADVERSARIAL_DIAGNOSTIC"
TAIL_POLICY_SCOPE: Final[str] = "prospective only; no past pre-registration or verdict changes"

#: The minimum adversarial tail diagnostics a resumed study reports. The first
#: six are the decision's words; the rest complete an item list the decision
#: text was cut off in the middle of, and are marked as drafted.
TAIL_DIAGNOSTICS: Final[tuple[tuple[str, str], ...]] = (
    ("top 1 day contribution to net", "ruled"),
    ("top 5 days contribution to net", "ruled"),
    ("top 10 days contribution to net", "ruled"),
    ("largest loss days", "ruled"),
    ("sign of net once the top days are excluded", "ruled"),
    ("temporal concentration of the top days", "ruled (text truncated after 'temporal co')"),
    ("currency and pair concentration of the top and worst days", "drafted"),
    ("overlap of the top days with scheduled events", "drafted"),
    ("daily skewness and excess kurtosis", "drafted"),
    ("return of the days inside +/- 3 robust sigmas", "drafted"),
)

#: What reopens active-alpha research. `ruled` conditions follow from the
#: decision's §4-§8; `drafted` ones are proposed for Human + ChatGPT
#: confirmation because the decision text ends in §9.
RESUMPTION_CONDITIONS: Final[tuple[tuple[str, str, str], ...]] = (
    (
        "RC-1",
        "an explicit Human + ChatGPT decision to resume, naming the hypothesis, data, "
        "operation and approved head; no recorded status, gate or document supplies it",
        "drafted",
    ),
    (
        "RC-2",
        "a positive base expected-return source established first, in a pre-registered "
        "test, before any efficiency mechanism, overlay or added complexity is built on it",
        "ruled",
    ),
    (
        "RC-3",
        "Track 3 overlays only on a core with positive base edge, never as a rescue",
        "ruled",
    ),
    (
        "RC-4",
        "complex ML only with positive base evidence that a simple architecture works and "
        "a stated reason complexity would add to it",
        "ruled",
    ),
    (
        "RC-5",
        "a hypothesis outside every closed and adjacent family in the ledger, with the "
        "novelty boundary written before any outcome is seen; post-hoc observations are "
        "never promoted",
        "drafted",
    ),
    (
        "RC-6",
        "new information, not a new look at seen data: an independent source, forward "
        "data that has accrued, or the fresh pool used once for a fully frozen candidate "
        "under its own Red authorisation",
        "drafted",
    ),
    (
        "RC-7",
        "signal-blind feasibility (detection power, capacity, search budget) computed and "
        "passed before any outcome is read",
        "drafted",
    ),
    (
        "RC-8",
        "tail concentration reported as adversarial diagnostics, not hard kills",
        "ruled",
    ),
)

#: The protected data as it stands at the pause, copied from the one authority.
PROTECTED_DATA_AT_PAUSE: Final[dict[str, str]] = {
    name: block["status"] for name, block in PROTECTED_SPANS.items()
}

#: Merged records of the phases that led here.
MERGES: Final[dict[int, str]] = {
    478: "a0780e3",
    479: "3b4d0a9",
    480: "3bbb7f5",
    481: "e13dba2",
    482: "a98fbc6",
}

#: Research PRs whose results are not on master and so are not authoritative.
UNMERGED_RESEARCH_PRS: Final[dict[int, str]] = {
    473: "expectation benchmark (survey-consensus null) — open, not merged",
}

#: Ledger entries left OPEN when the programme paused. They are frozen as they
#: stand: not pursued, not closed, and not rewritten.
OPEN_LEDGER_ENTRIES_FROZEN_AT_PAUSE: Final[tuple[str, ...]] = ("H-011", "H-015", "H-018", "H-019")


def active_alpha_research_paused() -> bool:
    return PROGRAMME_STATUS == "FX_SPOT_ACTIVE_ALPHA_RESEARCH_PAUSED"


__all__ = [
    "COMPLEX_ML_NOT_AUTHORISED",
    "MERGES",
    "NOT_CLAIMED",
    "OPEN_LEDGER_ENTRIES_FROZEN_AT_PAUSE",
    "PAUSE_DECISION_DATE",
    "PRINCIPLES",
    "PROGRAMME_STATUS",
    "PROHIBITED_RESCUES",
    "PROTECTED_DATA_AT_PAUSE",
    "RESUMPTION_CONDITIONS",
    "STATUSES",
    "TAIL_DIAGNOSTICS",
    "TAIL_POLICY",
    "TAIL_POLICY_SCOPE",
    "UNMERGED_RESEARCH_PRS",
    "active_alpha_research_paused",
]
