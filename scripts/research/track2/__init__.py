"""Track 2 — non-USD macro surprise, currency-level relative response.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Everything here is fixed in `docs/research/m15_track_2_non_usd_surprise_prereg.md`,
frozen at `8c4e171` before any signal or return existed. The Feasibility Gate v2
this Track is adjudicated by was frozen first, at `d2d35db`, and Track 2 is its
first prospective application.

Stage 0 comes first and can stop the Track
-------------------------------------------

The values come from a free calendar archive whose **timestamps are known to be
wrong** — sixteen to seventeen hours early on the rows an earlier stage checked.
A one-day study needs the release *date*, not the time, so the question is
whether the date survives. That is measurable against something official: the
ECB, the Bank of Japan and the Reserve Bank of Australia publish machine-readable
announcement dates, and `exogenous.calendars` already acquires them.

The correction allowed is **one constant**, estimated on **USD** rows against
ALFRED's vintage dates and then validated on **non-USD** rows. Estimating it on
the rows it will be judged by would be fitting the audit to its own answer.
"""

from __future__ import annotations

from typing import Final

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

GATE_V2_FREEZE: Final[str] = "d2d35db1d851e230155f0975e01427db6a0a1d48"
PREREG_FREEZE: Final[str] = "8c4e17100c9226d3fd20a85109dec023f9cec194"

#: The free archive, keyless. Fingerprinted on every acquisition: a different
#: digest is a different archive and the run says so rather than proceeding.
ARCHIVE_URL: Final[str] = (
    "https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar/"
    "resolve/main/forex_factory_cache.csv"
)
ARCHIVE_SHA256_PREFIX: Final[str] = "f4e92bca4168cfe6"
ARCHIVE_ROWS: Final[int] = 83427

#: The eight currencies `PAIRS_20` spans, and the seven this Track is about.
G10: Final[tuple[str, ...]] = ("USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD")
NON_USD: Final[tuple[str, ...]] = tuple(c for c in G10 if c != "USD")
#: Codes the archive carries that are outside the universe. Named so that P2 can
#: distinguish "a code we do not trade" from "a code nobody recognises".
KNOWN_NON_UNIVERSE_CODES: Final[frozenset[str]] = frozenset({"CNY", "All"})

#: The policy-decision rows each official calendar can adjudicate. One event name
#: per bank, taken from the archive's own vocabulary.
POLICY_EVENTS: Final[dict[str, str]] = {
    "EUR": "Main Refinancing Rate",
    "JPY": "BOJ Policy Rate",
    "AUD": "Cash Rate",
    "USD": "Federal Funds Rate",
}

#: The US series whose ALFRED vintage dates are the ground truth the single
#: offset is estimated from. CPI, because its vintages are the release dates.
OFFSET_TRAINING_SERIES: Final[str] = "CPIAUCSL"
OFFSET_TRAINING_EVENT: Final[str] = "CPI m/m"
#: Whole hours only, and a declared grid: an offset chosen off a continuum would
#: be a fit rather than a correction.
OFFSET_GRID_HOURS: Final[tuple[int, ...]] = tuple(range(0, 25))

# ------------------------------------------------------ Stage 0 acceptance
#: Pre-registration §3.2, frozen before the audit ran.
MIN_DATE_AGREEMENT: Final[float] = 0.95
MAX_FORECAST_EXACT_MATCH_SHARE: Final[float] = 0.25

#: The deciding panels, and the span the audit is taken over.
PANEL_SPANS: Final[dict[str, tuple[str, str]]] = {
    "momentum_2021_2023": ("2021-04-26", "2023-04-25"),
    "supplemental_2023_2025": ("2023-04-26", "2025-04-24"),
}

STATUS_SKIP: Final[str] = "NON_USD_SURPRISE_DATA_NOT_DECISION_GRADE_SKIP"
STATUS_CLOSED: Final[str] = "NON_USD_SURPRISE_RELATIVE_CLOSED"
STATUS_SUPPORTED: Final[str] = "NON_USD_SURPRISE_RELATIVE_EDGE_SUPPORTED_EXPLORATORY"

__all__ = [
    "ARCHIVE_ROWS",
    "ARCHIVE_SHA256_PREFIX",
    "ARCHIVE_URL",
    "CLASSIFICATION",
    "CLASSIFICATION_SECONDARY",
    "G10",
    "GATE_V2_FREEZE",
    "KNOWN_NON_UNIVERSE_CODES",
    "MAX_FORECAST_EXACT_MATCH_SHARE",
    "MIN_DATE_AGREEMENT",
    "NON_USD",
    "OFFSET_GRID_HOURS",
    "OFFSET_TRAINING_EVENT",
    "OFFSET_TRAINING_SERIES",
    "PANEL_SPANS",
    "POLICY_EVENTS",
    "PREREG_FREEZE",
    "STATUS_CLOSED",
    "STATUS_SKIP",
    "STATUS_SUPPORTED",
]
