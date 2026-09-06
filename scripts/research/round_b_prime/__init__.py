"""Round B′ — is there path structure a matched null cannot produce?

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Nothing here builds a strategy, predicts a label or fits a model. It measures
distributions and compares them against nulls that were written down first.

Like `round_a`, this package contains **no reader, no archive path and no span
bound**: it loads the three M15 parquet caches through `round_a.panels`, each of
which goes through a route carrying its own span guard. It cannot open a
market-data file.

Why the nulls come first
------------------------

Round A's headline statistic — `median MFE / cost` — turned out to be
`1.1 · (σ/cost) · √H`, an identity an IID shuffle of the same bars scores
*higher* on. Every statistic in this package is therefore defined with its null
alongside it, and each null's docstring says **what it preserves and what it
destroys**. "The shuffle came out different" is not a finding until it is clear
which property the shuffle removed.
"""

from __future__ import annotations

from typing import Final

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

#: Fixed in the plan. The trailing window every sigma in this round is measured
#: over, in bars, strictly backward-looking.
RV_WINDOW: Final[int] = 480

#: B′-1: variance-ratio aggregation horizons, in bars. 30min .. 5 days.
VR_HORIZONS: Final[tuple[int, ...]] = (2, 4, 12, 48, 96, 192, 480)

#: B′-2: excursion thresholds in sigma, the observation window after an anchor,
#: and the timeout that bounds the search for one.
EXCURSION_SIGMAS: Final[tuple[float, ...]] = (1.5, 2.0, 3.0)
OBSERVATION_WINDOW: Final[int] = 480
ANCHOR_TIMEOUT: Final[int] = 960

#: B′-4: a month is 21 trading days of 96 M15 bars.
MONTH_BARS: Final[int] = 21 * 96
TSMOM_LOOKBACKS: Final[tuple[int, ...]] = (1, 2, 3)
TSMOM_HOLDS: Final[tuple[int, ...]] = (1, 3)

#: B′-HTF: the two context variables, two states each.
HTF_FAST: Final[int] = 96
HTF_SLOW: Final[int] = 480
HTF_RANGE_WINDOW: Final[int] = 1920

SEED: Final[int] = 20260907
NULL_DRAWS: Final[int] = 200
SIGN_FLIP_BLOCK_DAYS: Final[int] = 5

#: The economic floor from the plan: a median retrace-fraction difference under
#: this is negligible however significant it is.
RETRACE_DIFFERENCE_FLOOR: Final[float] = 0.05

__all__ = [
    "ANCHOR_TIMEOUT",
    "CLASSIFICATION",
    "CLASSIFICATION_SECONDARY",
    "EXCURSION_SIGMAS",
    "HTF_FAST",
    "HTF_RANGE_WINDOW",
    "HTF_SLOW",
    "MONTH_BARS",
    "NULL_DRAWS",
    "OBSERVATION_WINDOW",
    "RETRACE_DIFFERENCE_FLOOR",
    "RV_WINDOW",
    "SEED",
    "SIGN_FLIP_BLOCK_DAYS",
    "TSMOM_HOLDS",
    "TSMOM_LOOKBACKS",
    "VR_HORIZONS",
]
