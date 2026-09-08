"""Expectation Benchmark — frozen constants.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`.

Every value here is fixed in
`docs/research/m15_expectation_benchmark_plan.md`, committed **before any
relationship between an expectation and an FX return was computed**. None may be
changed because of a result.

The programme has measured realised quantities and timing for seventeen
families and never held the other half of a repricing: **the expectation the
market carried into the event**. This package tests `realised − expected`.

Decision-grade or skip
----------------------

A cheap underpowered test is worse than no test, because it turns an open
question into an ambiguous null that invites another purchase. Every threshold
below was set from a **design power curve** measured on the unconditional
dispersion of event-time returns, before any expectation data existed:

* the first version of that curve was built on **raw pair returns** and
  understated every entry by about three times. Amendment A-1 replaced it with
  USD-oriented returns, which is the quantity the test trades;
* measured correctly, at 89 release-times the 1h MDE is **6.16 / 6.04 pips**
  against a **4.27 / 4.09** break-even, so 89 events cannot decide and about
  **190** are needed;
* 4h needs 482-583 events, which no US release population reaches, so **4h, 12h
  and 1d are excluded a priori** and no number from them is reported as
  evidence.

A single-currency test can **kill** but never **promote**: killing needs power,
promotion needs breadth, and promotion spends the fresh pool.
"""

from __future__ import annotations

from typing import Final

CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"

BASE_MASTER: Final[str] = "941fd0eca21fda6436b5f33a6a71bb3f02ea98eb"

SEED: Final[int] = 20260909

# ------------------------------------------------- decision-grade thresholds
#: Plan §4.1, superseded as a sufficiency test by the measured figure below:
#: it remains the floor under which the test is not run at all.
MIN_RELEASES_PER_DECIDING_PANEL: Final[int] = 90
#: Amendment A-1, measured rather than assumed: at 89 events the 1h MDE is
#: 6.16/6.04 pips against a 4.27/4.09 break-even, so the design needs about
#: this many release-times before it can decide anything.
RELEASES_NEEDED_FOR_1H_POWER: Final[int] = 190
#: Plan §4.2. The free rates test needs this many usable days per panel.
MIN_DAYS_PER_DECIDING_PANEL: Final[int] = 400
#: Plan §2. One currency kills; four promote.
MIN_CURRENCIES_TO_KILL: Final[int] = 1
MIN_CURRENCIES_TO_PROMOTE: Final[int] = 4

# --------------------------------------------------------- horizons (plan §3)
#: In M15 bars. One horizon, by amendment A-1: everything longer needs an event
#: count no US release population reaches, and the economics agrees -- a
#: tradeable announcement effect lives in the hour after the print.
MACRO_HORIZON_BARS: Final[dict[str, int]] = {"1h": 4}
#: Excluded a priori, recorded so the omission is legible as a decision.
MACRO_HORIZONS_EXCLUDED_FOR_POWER: Final[dict[str, str]] = {
    "4h": (
        "amendment A-1: measured MDE 9.93/10.58 pips against a 4.1-4.3 break-even; "
        "needs 482-583 release-times per deciding panel, which no US population reaches"
    ),
    "12h": "wider still than 4h at the same event count",
    "1d": "wider still than 12h at the same event count",
}
#: The free rates lead test holds one day.
RATES_HORIZON_BARS: Final[int] = 96

# ----------------------------------------------------- release-time semantics
#: Plan §6 and amendment A-1. Every release family here prints at 08:30
#: America/New_York, a time fixed by rule and published a year ahead; that is
#: the mechanical criterion that admits them, together with ALFRED vintages and
#: an archive forecast.
RELEASE_LOCAL_TIME: Final[str] = "08:30"
RELEASE_TIMEZONE: Final[str] = "America/New_York"

#: Release family -> (ALFRED series that dates it, archive event names).
#: The archive supplies values only: its own timestamps are 16-17 hours early
#: (plan §5.4), so every release time comes from the ALFRED vintage date plus
#: the rule above, and the two are cross-checked.
RELEASE_FAMILIES: Final[dict[str, dict[str, object]]] = {
    "cpi": {"series": "CPIAUCSL", "events": ("CPI m/m", "Core CPI m/m")},
    "employment": {
        "series": "PAYEMS",
        "events": (
            "Non-Farm Employment Change",
            "Unemployment Rate",
            "Average Hourly Earnings m/m",
        ),
    },
    "retail": {"series": "RSAFS", "events": ("Retail Sales m/m", "Core Retail Sales m/m")},
    "ppi": {"series": "PPIFIS", "events": ("PPI m/m",)},
    #: Amendment A-1. Admitted by the mechanical rule -- a US federal statistical
    #: agency release at 08:30 America/New_York, carried by ALFRED with vintages,
    #: with both an actual and a forecast across the span -- and admitted to
    #: reach power, before any result existed. Regional Reserve Bank surveys are
    #: excluded by the same rule: they are not federal statistical agency
    #: releases.
    "claims": {"series": "ICSA", "events": ("Unemployment Claims",)},
    "durable_goods": {
        "series": "DGORDER",
        "events": ("Durable Goods Orders m/m", "Core Durable Goods Orders m/m"),
    },
    "housing": {"series": "HOUST", "events": ("Housing Starts", "Building Permits")},
    "trade": {"series": "BOPGSTB", "events": ("Trade Balance",)},
    "pce": {
        "series": "PCEPILFE",
        "events": ("Core PCE Price Index m/m", "Personal Spending m/m"),
    },
    "gdp": {"series": "GDPC1", "events": ("Advance GDP q/q", "Prelim GDP q/q")},
}

#: The archive's own impact label, used only to define the high-impact subset
#: reported beside the pooled cell. Not a weight and not a filter on the
#: primary.
HIGH_IMPACT_FAMILIES: Final[tuple[str, ...]] = ("cpi", "employment", "pce", "gdp")

#: Plan §6, fixed before any return was computed. Every one is the same
#: economics: a stronger or more inflationary print is hawkish for the Fed and
#: appreciates the USD. A measured effect in the opposite direction drops the
#: family; it is never inverted.
SIGNAL_SIGNS: Final[dict[str, int]] = {
    "CPI m/m": +1,
    #: amendment A-1 additions, the same economics throughout: a stronger or
    #: more inflationary print is hawkish and appreciates the USD. Jobless
    #: claims and the trade deficit are the two that carry a minus, because a
    #: larger number is a weaker economy in both.
    "Unemployment Claims": -1,
    "Durable Goods Orders m/m": +1,
    "Core Durable Goods Orders m/m": +1,
    "Housing Starts": +1,
    "Building Permits": +1,
    "Trade Balance": +1,
    "Core PCE Price Index m/m": +1,
    "Personal Spending m/m": +1,
    "Advance GDP q/q": +1,
    "Prelim GDP q/q": +1,
    "Core CPI m/m": +1,
    "Non-Farm Employment Change": +1,
    "Unemployment Rate": -1,
    "Average Hourly Earnings m/m": +1,
    "Retail Sales m/m": +1,
    "Core Retail Sales m/m": +1,
    "PPI m/m": +1,
}
#: Plan §8. A rise in the US 2-year yield appreciates the USD.
RATES_SIGN: Final[int] = +1

#: The expanding, strictly backward-looking window that scales a surprise.
SURPRISE_SCALE_RELEASES: Final[int] = 24

# ------------------------------------------------------ multiplicity (plan §6)
#: Amendment A-1: one horizon, so one primary. Secondaries are the ten families
#: plus the high-impact subset, each reported only if its own power clears its
#: own break-even.
MACRO_PRIMARY_CELLS: Final[int] = 1
MACRO_SECONDARY_CELLS: Final[int] = 11
MACRO_CELLS: Final[int] = MACRO_PRIMARY_CELLS + MACRO_SECONDARY_CELLS
RATES_CELLS: Final[int] = 2

NULL_DRAWS: Final[int] = 200
FAMILYWISE_ALPHA: Final[float] = 0.05
#: The plan's own clause: top ten events over **net**, negatives included.
TAIL_SHARE_CEILING: Final[float] = 0.50
#: z(0.975) + z(0.80): the multiplier that turns a null dispersion into a
#: minimum detectable effect at 80% power.
POWER_MULTIPLIER: Final[float] = 2.802

# ----------------------------------------------------------- the free archive
ARCHIVE_URL: Final[str] = (
    "https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar/"
    "resolve/main/forex_factory_cache.csv"
)
#: Measured at acquisition. A different digest means a different archive.
ARCHIVE_SHA256_PREFIX: Final[str] = "f4e92bca4168cfe6"
ARCHIVE_ROWS: Final[int] = 83427

__all__ = [
    "ARCHIVE_ROWS",
    "ARCHIVE_SHA256_PREFIX",
    "ARCHIVE_URL",
    "BASE_MASTER",
    "CLASSIFICATION",
    "CLASSIFICATION_SECONDARY",
    "FAMILYWISE_ALPHA",
    "MACRO_CELLS",
    "MACRO_HORIZONS_EXCLUDED_FOR_POWER",
    "HIGH_IMPACT_FAMILIES",
    "MACRO_HORIZON_BARS",
    "MACRO_PRIMARY_CELLS",
    "MACRO_SECONDARY_CELLS",
    "MIN_CURRENCIES_TO_KILL",
    "MIN_CURRENCIES_TO_PROMOTE",
    "MIN_DAYS_PER_DECIDING_PANEL",
    "MIN_RELEASES_PER_DECIDING_PANEL",
    "NULL_DRAWS",
    "POWER_MULTIPLIER",
    "RATES_CELLS",
    "RATES_HORIZON_BARS",
    "RATES_SIGN",
    "RELEASES_NEEDED_FOR_1H_POWER",
    "RELEASE_FAMILIES",
    "RELEASE_LOCAL_TIME",
    "RELEASE_TIMEZONE",
    "SEED",
    "SIGNAL_SIGNS",
    "SURPRISE_SCALE_RELEASES",
    "TAIL_SHARE_CEILING",
]
