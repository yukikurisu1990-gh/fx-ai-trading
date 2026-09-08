"""Exogenous Directional Information — frozen constants.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Every value here is fixed in
`docs/research/m15_exogenous_directional_information_plan.md`, committed **before
the first research statistic of this package was computed**. None may be changed
because of a result.

The package asks one question: can information that lives outside the price
series, is knowable **before** the fact, and has an economic reason to move an
exchange rate, produce a directional expected return that survives cost?

Ten price-derived families have failed. What survived the last package was an
*opportunity* structure anchored on days a policy rate changed — and whether a
rate changes is not knowable in advance. Everything here must be knowable in
advance; an outcome attribute may be a post-hoc split and never an entry
condition.
"""

from __future__ import annotations

from typing import Final

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

BASE_MASTER: Final[str] = "b7073d5aa460438bfe5220e39e841ef9a75d9cc5"

SEED: Final[int] = 20260908

# ------------------------------------------------------------ acquired banks
#: Plan §4.2. Four of eight, and the other four are a recorded coverage
#: limitation rather than a hand-written table: BoE, BoC, RBNZ and SNB return
#: 403/404/500 to every automated route tried, and inventing their meeting dates
#: would put unverified scope into an artifact.
SCHEDULED_BANKS: Final[dict[str, str]] = {
    "USD": "Federal Reserve (FOMC)",
    "EUR": "European Central Bank (Governing Council)",
    "JPY": "Bank of Japan (Monetary Policy Meeting)",
    "AUD": "Reserve Bank of Australia (Board)",
}
#: The four whose calendars could not be acquired without a login or a paid feed.
UNCOVERED_CURRENCIES: Final[tuple[str, ...]] = ("GBP", "CAD", "NZD", "CHF")

# --------------------------------------------------------- matching (plan §6)
#: Carried over from the Economic Edge package, where a session with fewer bars
#: than this turned out to be a Sunday and its 2.5 pip spread flipped a headline.
MIN_BARS_FOR_A_TRADING_DAY: Final[int] = 48
#: Event days are compared with control days inside the same weekday **and** the
#: same trailing-volatility tercile.
VOLATILITY_CONTEXT_DAYS: Final[int] = 60
VOLATILITY_TERCILES: Final[int] = 3

# ------------------------------------------------ publication time (plan §5)
#: US CPI prints at 08:30 America/New_York. Converted per date with the real
#: daylight rule; a fixed offset is a bug and is a mutation in plan §21.
BLS_RELEASE_LOCAL_TIME: Final[str] = "08:30"
BLS_RELEASE_TIMEZONE: Final[str] = "America/New_York"
#: COT is as-of Tuesday and published Friday 15:30 America/New_York. 20:30 UTC is
#: the *later* of the two daylight conversions and is used unconditionally, so
#: the conversion can never be optimistic.
COT_PUBLICATION_UTC_HOUR: Final[int] = 20
COT_PUBLICATION_UTC_MINUTE: Final[int] = 30
#: Plan amendment A-3. A federal holiday later in the report week delays the
#: release by one business day while the as-of date stays Tuesday, and the
#: report carries no release timestamp to detect that from. Waiting three
#: calendar days past the nominal Friday puts entry at or after every possible
#: publication. The Monday rule governs every COT verdict; the Friday numbers
#: are kept only as a timing-sensitivity diagnostic.
COT_PUBLICATION_SAFETY_DAYS: Final[int] = 3

# ------------------------------------------------------- macro (plan §7, §8)
#: The expanding, strictly backward-looking window used to scale a surprise.
SURPRISE_SCALE_RELEASES: Final[int] = 24
#: Plan §8. Three horizons, in M15 bars: one hour, four hours, one day.
MACRO_HORIZON_BARS: Final[dict[str, int]] = {"1h": 4, "4h": 16, "1d": 96}
#: Higher-than-expected US inflation is hawkish and appreciates the USD. Fixed
#: before any return was computed; a contradicting measurement drops the family
#: rather than inverting it.
MACRO_DIRECTION_SIGN: Final[int] = +1

# ---------------------------------------------------------- COT (plan §17)
COT_SIGNALS: Final[tuple[str, ...]] = (
    "net_level",
    "net_change",
    "net_percentile",
    "net_extreme",
)
#: Contrarian for the three positioning-level signals (crowded positioning has to
#: be unwound), momentum for the flow signal (a change in positioning is flow
#: that has not finished). Two different economic claims, each committed to one
#: sign here.
COT_SIGNS: Final[dict[str, int]] = {
    "net_level": -1,
    "net_change": +1,
    "net_percentile": -1,
    "net_extreme": -1,
}
COT_PERCENTILE_WEEKS: Final[int] = 104
COT_EXTREME_UPPER: Final[float] = 0.90
COT_EXTREME_LOWER: Final[float] = 0.10
#: Calendar days, not bars — plan amendment A-1. The FX week has no weekend
#: bars, so `7 * 96` bars is about nine and a half calendar days and `28 * 96`
#: is about five and a half weeks. A horizon named "1 week" that holds for nine
#: days is a misspecification, so the position is closed at the first bar at or
#: after `entry + N days`.
COT_HORIZON_DAYS: Final[dict[str, int]] = {"1w": 7, "4w": 28}

# ------------------------------------------------------ multiplicity (§12)
SCHEDULED_EVENT_CELLS: Final[int] = 6
MACRO_CELLS: Final[int] = 6
COT_CELLS: Final[int] = 8
TOTAL_CELLS: Final[int] = SCHEDULED_EVENT_CELLS + MACRO_CELLS + COT_CELLS

NULL_DRAWS: Final[int] = 200
FAMILYWISE_ALPHA: Final[float] = 0.05
TAIL_SHARE_CEILING: Final[float] = 0.50
#: Plan §13. Below this an event family is dropped for insufficient events.
MIN_EVENTS_PER_DECIDING_PANEL: Final[int] = 30
#: Plan §11, prerequisite 3.
ML_MIN_EVENTS_PER_DECIDING_PANEL: Final[int] = 100
#: Plan §6: the share of eligible pairs that must agree.
BREADTH_SHARE: Final[float] = 0.60
#: Plan §9. Broker financing must beat the research proxy by more than this, per
#: pair per panel, in the non-JPY bloc, before carry may be reopened at all.
CARRY_REOPEN_PIPS: Final[float] = 20.0

__all__ = [
    "BASE_MASTER",
    "BLS_RELEASE_LOCAL_TIME",
    "BLS_RELEASE_TIMEZONE",
    "BREADTH_SHARE",
    "CARRY_REOPEN_PIPS",
    "CLASSIFICATION",
    "CLASSIFICATION_SECONDARY",
    "COT_CELLS",
    "COT_EXTREME_LOWER",
    "COT_EXTREME_UPPER",
    "COT_HORIZON_DAYS",
    "COT_PERCENTILE_WEEKS",
    "COT_PUBLICATION_SAFETY_DAYS",
    "COT_PUBLICATION_UTC_HOUR",
    "COT_PUBLICATION_UTC_MINUTE",
    "COT_SIGNALS",
    "COT_SIGNS",
    "FAMILYWISE_ALPHA",
    "MACRO_CELLS",
    "MACRO_DIRECTION_SIGN",
    "MACRO_HORIZON_BARS",
    "MIN_BARS_FOR_A_TRADING_DAY",
    "MIN_EVENTS_PER_DECIDING_PANEL",
    "ML_MIN_EVENTS_PER_DECIDING_PANEL",
    "NULL_DRAWS",
    "SCHEDULED_BANKS",
    "SCHEDULED_EVENT_CELLS",
    "SEED",
    "SURPRISE_SCALE_RELEASES",
    "TAIL_SHARE_CEILING",
    "TOTAL_CELLS",
    "UNCOVERED_CURRENCIES",
    "VOLATILITY_CONTEXT_DAYS",
    "VOLATILITY_TERCILES",
]
