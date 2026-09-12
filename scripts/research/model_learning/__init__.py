"""Model-learning research over the seen FX history — spans, provenance, roles.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

What this package is, and what it deliberately is not
-----------------------------------------------------

The preceding phase ruled `CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED` for
**simple hypothesis testing**: on 1.996-year deciding panels, Gate v2's composite
needs 3.488 effective years, and `effective_years = panel_years x share` cannot
exceed the panel. That ruling stands and is not reopened here.

This package asks a different question about the same bytes. Pooling 4.674 years
to *certify that an effect exists* and using 4.674 years to *estimate a
conditional mapping* are different uses with different feasibility conditions,
and only the second is in scope. Nothing here pools panels for significance,
re-adjudicates a closed family, or produces decision-grade evidence: the best
outcome available to it is `DEVELOPMENT_MODEL_CANDIDATE`, whose independent
confirmation would be a one-shot read of data this package may not touch.

The two budgets
---------------

`budgets.py` derives the feasibility conditions, and they are denominated in
**years**, not in bars:

* capacity — `p_effective <= IR_annual^2 * train_years`
* search   — `z_max(M_effective) <= MRIE * sqrt(validation_years)`

Both are signal-blind: they are properties of a design, computable before a byte
of price is read, and they are what decides whether a development run is worth
starting.

Data
----

Three seen spans, each already read through its own guarded route, and each
carrying the exploratory history that was run against it. That history is not
decoration: 4.674 years that have been screened by roughly 1,200 configurations
is a different object from 4.674 years nobody has looked at, and a model selected
on it inherits that multiplicity.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum
from typing import Any, Final

from scripts.research.exploratory_m15 import PAIRS as ARCHIVE_PAIRS
from scripts.research.feasibility import MAX_PLAUSIBLE_GROSS_IR

STATUS_SIMPLE_TESTING_EXHAUSTED: Final[str] = (
    "CURRENT_SEEN_DATA_FX_RESEARCH_SPACE_EXHAUSTED_FOR_SIMPLE_HYPOTHESIS_TESTING"
)
STATUS_SURVIVES: Final[str] = "MODEL_LEARNING_CANDIDATE_SURVIVES_SEEN_DEVELOPMENT"
STATUS_NO_EDGE: Final[str] = "MODEL_LEARNING_RESEARCH_FAILED_TO_FIND_INCREMENTAL_EDGE"
STATUS_NOT_DECISION_GRADE: Final[str] = "MODEL_LEARNING_NOT_DECISION_GRADE_WITH_AVAILABLE_SEEN_DATA"

#: The strongest thing a seen-data run may conclude. Not an edge, not a
#: confirmation, and explicitly not production readiness.
DEVELOPMENT_CANDIDATE: Final[str] = "DEVELOPMENT_MODEL_CANDIDATE"


class ProtectedDataError(RuntimeError):
    """Raised when anything in this package is pointed at data it may not read."""


# --------------------------------------------------------------- the seen spans
#: Each span is already `EXPLORATORY_SEEN_DATA`. The route is the module that
#: owns its guard; this package never re-implements a bound, and the caches below
#: are the M15 derivations those routes already produced.
SEEN_SPANS: Final[dict[str, dict[str, Any]]] = {
    "momentum_2021_2023": {
        "start": "2021-04-26",
        "end": "2023-04-25",
        "route": "scripts.research.exploratory_m15.momentum",
        "cache": "artifacts/track_a_scratch/momentum_replication_b",
        "role_so_far": "deciding panel",
        #: Ledger ids from `scripts.research.round_a.ledger` that were evaluated
        #: against this span.
        "hypotheses_run_here": (
            "H-007",
            "H-008",
            "H-009",
            "H-010",
            "H-011",
            "H-012",
            "H-013",
            "H-014",
            "H-015",
            "H-016",
            "H-017",
            "H-018",
            "H-019",
            "H-020",
            "H-021",
        ),
        "prior_strategy_exposure": (
            "the mirrored multi-day momentum candidate, ten pre-registered cells; "
            "Round A/B' descriptive and variance-ratio families; carry, tick-volume, "
            "event-anchor, macro-surprise and COT families"
        ),
        "prior_labels_or_features_used": (
            "forward net PnL at 384/480/576 bars, sigma-normalised 1-bar returns, "
            "excursion anchors, ATR terciles, session and bloc splits, daily tick "
            "volume, BIS policy rates, scheduled central-bank dates, CFTC positioning"
        ),
        "known_exploratory_reuse": "high — a deciding panel in every round since Round A",
    },
    "supplemental_2023_2025": {
        "start": "2023-04-26",
        "end": "2025-04-24",
        "route": "scripts.research.exploratory_m15.supplemental",
        "cache": "artifacts/track_a_scratch/supplemental_replication",
        "role_so_far": "deciding panel",
        "hypotheses_run_here": (
            "H-006",
            "H-008",
            "H-009",
            "H-010",
            "H-011",
            "H-012",
            "H-013",
            "H-014",
            "H-015",
            "H-016",
            "H-017",
            "H-018",
            "H-019",
            "H-020",
            "H-021",
        ),
        "prior_strategy_exposure": (
            "the frozen multi-day reversal candidate, eleven cells; the same Round A, "
            "Round B', monetizability, economic-edge and exogenous families"
        ),
        "prior_labels_or_features_used": (
            "identical to the momentum panel — the two were always run as a pair"
        ),
        "known_exploratory_reuse": "high — a deciding panel in every round since Round A",
    },
    "development_2025": {
        "start": "2025-04-25",
        "end": "2025-12-28",
        "route": "scripts.research.exploratory_m15.bars",
        "cache": "artifacts/track_a_scratch/exploratory_round_1",
        "role_so_far": "screening surface, never a deciding vote since Round A",
        "hypotheses_run_here": (
            "H-001",
            "H-002",
            "H-003",
            "H-004",
            "H-005",
            "H-008",
            "H-009",
            "H-010",
            "H-011",
            "H-012",
            "H-013",
            #: H-014 is deliberately absent. The ledger records its population as
            #: "both deciding panels", and this span is explicitly not one of them.
            #: An earlier version listed it here, and the test meant to catch that
            #: only checked the id existed somewhere in the ledger rather than
            #: against the span it names.
            "H-015",
            "H-016",
            "H-017",
            "H-018",
            "H-019",
            "H-020",
            "H-021",
        ),
        "prior_strategy_exposure": (
            "Exploratory Round 1's 26 strategies and 1,078 conditional fits, Round 2's "
            "39 pre-registered cells, and the 57-variant LightGBM direction model this "
            "phase is forbidden to re-run"
        ),
        "prior_labels_or_features_used": (
            "forward return sign, y_beats_cost, ~50 price/volatility/session features, "
            "and everything the two deciding panels carry"
        ),
        "known_exploratory_reuse": (
            "very high — roughly 1,200 configurations, which is why Round A forbade it "
            "from being a deciding vote"
        ),
    },
}

#: Never read. Not for training, hyperparameters, features, model selection,
#: thresholds, early stopping, debugging, or a schema check.
PROTECTED_SPANS: Final[dict[str, dict[str, str]]] = {
    "fresh_pool": {
        "start": "2016-06-02",
        "end": "2021-04-25",
        "status": "never read",
        "reserved_for": "one-shot independent evaluation of a fully frozen candidate",
    },
    #: ⭐ NOT "never read", and the difference is a ruling rather than a nuance.
    #: `HISTORICAL_EXPLORATORY_OOS_PRISTINE_CLAIM_WITHDRAWN` (2026-09-05): the R1
    #: read decoded one row past each window, and for the final window those twenty
    #: rows are inside this slice. The adjudication is that this **is** a read, so
    #: "pristine", "untouched" and "never read" may not be claimed of it. The
    #: wording below is copied from `scripts.research.feasibility.inventory` rather
    #: than re-invented, because a second phrasing is how a withdrawn claim
    #: reappears.
    "historical_oos": {
        "start": "2025-12-29",
        "end": "(end of slice)",
        "status": "one decoded row per pair; no value reached an output",
        "reserved_for": "not this phase, and not readable from here",
    },
    "dead_window": {
        "start": "(after the OOS slice)",
        "end": "-",
        "status": "never read",
        "reserved_for": "not this phase",
    },
    "forward_epoch": {
        "start": "(future)",
        "end": "-",
        "status": "never read",
        "reserved_for": "Formal Confirmation",
    },
}

#: **Imported, not restated.** A first version of this file typed the twenty
#: pairs out by hand and got four of them wrong — CAD_JPY, NZD_CAD, and two
#: omissions — which the corpus loader caught only because the caches refused to
#: open. The archive's own tuple is the authority.
PAIRS_20: Final[tuple[str, ...]] = ARCHIVE_PAIRS
CURRENCIES_G10: Final[tuple[str, ...]] = (
    "AUD",
    "CAD",
    "CHF",
    "EUR",
    "GBP",
    "JPY",
    "NZD",
    "USD",
)


def _years(start: str, end: str) -> float:
    """Elapsed years, `(hi - lo).days / 365.25`.

    The interval count rather than the inclusive day count, matching
    `scripts.research.feasibility.inventory` exactly. The two conventions differ
    by one day — 4.674 against 4.676 — and two documents in one programme quoting
    two lengths for the same span is a defect a reader cannot resolve.
    """
    lo = dt.date.fromisoformat(start)
    hi = dt.date.fromisoformat(end)
    return (hi - lo).days / 365.25


#: The contiguous training corpus, measured from the spans rather than restated.
#: `2021-04-26 … 2025-12-28`, which the three routes partition exactly.
TRAIN_YEARS_TOTAL: Final[float] = round(
    _years(SEEN_SPANS["momentum_2021_2023"]["start"], SEEN_SPANS["development_2025"]["end"]),
    3,
)

#: Measured effective independent directions in `PAIRS_20`, reported by this
#: programme repeatedly as 3.2 to 6.5 depending on the window and the statistic.
#: The conservative end is used wherever a smaller number makes a design look
#: worse.
EFFECTIVE_INDEPENDENT_PAIRS: Final[tuple[float, float]] = (3.2, 6.5)

#: The corpus's **counted** M15 rows across all twenty pairs, kept because a
#: reader will ask and immediately qualified: neither feasibility budget in this
#: package depends on it. An earlier constant gave one pair's total (116,418, which
#: is AUD_CAD's) and a document multiplied it by twenty; per-pair counts actually
#: run 116,215 to 116,491, so the product was 44 rows wrong and, more to the point,
#: was labelled as something it had not counted.
M15_ROWS_IN_THE_CORPUS: Final[int] = 2_328_316


class ModelRole(StrEnum):
    """What the model is being asked to do. The feasibility gate depends on it."""

    DIRECTION_OR_RETURN = "direction_or_return_generator"
    RANKING = "cross_sectional_ranking"
    TRADE_SKIP = "trade_or_skip"
    HORIZON_SELECTION = "holding_period_selection"
    REGIME_REPRESENTATION = "regime_representation"
    PORTFOLIO_ALLOCATION = "portfolio_allocation"
    EXECUTION_MANAGEMENT = "execution_management"


def assert_not_protected(start: str, end: str) -> None:
    """Refuse a span that touches protected data, before anything is opened.

    The parse comes first, so the comparison is on `date` objects rather than on
    the caller's string — which is what closes the `str`-subclass bypass an audit
    found in the three reader routes. An earlier docstring here claimed the guard
    "refuses anything that is not an exact `YYYY-MM-DD`", and that is **false**:
    `date.fromisoformat` also accepts ISO basic (`20210426`) and week (`2025-W52-7`)
    forms. Those parse to the right day, so the bound semantics hold and no
    protected row becomes reachable — but the claim was wider than the code and is
    corrected rather than defended.

    ⭐ The boundaries come from `PROTECTED_SPANS`, not from `SEEN_SPANS`. Taking
    them from the dictionary being protected let one edit relax the guard and
    preserve the pre-registration hash in a single move, which a review
    demonstrated by moving the corpus start onto a fresh-pool day while keeping
    the span length — and therefore the hash — unchanged.
    """
    try:
        lo = dt.date.fromisoformat(start)
        hi = dt.date.fromisoformat(end)
    except (TypeError, ValueError) as error:
        raise ProtectedDataError(f"{start!r}..{end!r} is not a parsable ISO date span") from error
    first = dt.date.fromisoformat(PROTECTED_SPANS["fresh_pool"]["end"]) + dt.timedelta(days=1)
    last = dt.date.fromisoformat(PROTECTED_SPANS["historical_oos"]["start"]) - dt.timedelta(days=1)
    if lo < first:
        raise ProtectedDataError(
            f"{start} is before {first}. The fresh pool is reserved for a single "
            "independent evaluation and may not be read for any purpose, including "
            "training, feature selection, threshold calibration or a schema check."
        )
    if hi > last:
        raise ProtectedDataError(
            f"{end} is after {last}. That is the historical OOS slice, the dead window "
            "or the forward Formal Confirmation epoch, and none is readable here."
        )
    if hi < lo:
        raise ProtectedDataError(f"{start}..{end} is empty")


__all__ = [
    "CURRENCIES_G10",
    "DEVELOPMENT_CANDIDATE",
    "EFFECTIVE_INDEPENDENT_PAIRS",
    "M15_ROWS_IN_THE_CORPUS",
    "MAX_PLAUSIBLE_GROSS_IR",
    "PAIRS_20",
    "PROTECTED_SPANS",
    "SEEN_SPANS",
    "STATUS_NOT_DECISION_GRADE",
    "STATUS_NO_EDGE",
    "STATUS_SIMPLE_TESTING_EXHAUSTED",
    "STATUS_SURVIVES",
    "TRAIN_YEARS_TOTAL",
    "ModelRole",
    "ProtectedDataError",
    "assert_not_protected",
]
