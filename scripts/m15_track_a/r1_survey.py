"""Stage R1 — the read-only descriptive survey, and nothing beyond it.

The contract, quoted from `m15_minimum_research_gate.md` §7's stage table so
that what this module owes is not paraphrased:

    **R1** — Read-only descriptive survey over an approved local dataset —
    schema, date span, pair coverage, missingness, descriptive statistics, **the
    distribution of `barrier_distance / cost` on eligible bars and its median
    (T-3), the eligible-bar rate per pair and session, and the per-pair ×
    session spread distribution (median / p90 / p95)**. **No training**

Every one of those is produced here, from one entry point, and **nothing else
is**. There is no model, no label, no feature, no threshold, no `ev_min`, no
Sharpe and no candidate. R1 is a survey; the temptation to let a survey grow a
strategy in it is exactly what §6 of the enablement brief forbids.

Where each number comes from
----------------------------

* **spread** — per-bar quoted spread ``ask_c − bid_c`` (prereg §4), converted to
  pips by the committed ``to_pips``;
* **cost** — ``median_spread(pair, session) + 0.3 + 0.5`` pip, Ruling 5 FROZEN,
  with the constants taken from ``cost_schema`` rather than restated;
* **sessions** — Asia 00:00–07:59, Europe 08:00–15:59, US 16:00–23:59 UTC,
  Ruling 4 FROZEN, read from ``cost_schema.SESSIONS_UTC``;
* **eligibility** — ``1.5 × ATR14_M15 ≥ 2.0 × cost(pair, session)``, Ruling 6
  FROZEN, **and** Calendar B's event-eligibility exclusions (rollover, and the
  holiday list, which is empty and says so);
* **coverage / missingness** — set-difference against **Calendar A**'s expected
  slots. Never inferred from the data (PR #444 D-6);
* **ATR14_M15** — Wilder's 14-period ATR over the M15 true range. S-20a records
  that *which price series* ATR is computed on is an
  `UNREGISTERED_RESEARCH_CHOICE`; this uses the **bid** series and says so in the
  output, because a survey that hides which of two admissible choices it made is
  not a survey.

What T-3 does here
------------------

`T_3_IS_A_TRACK_A_R1_MEASUREMENT_OBLIGATION_ITS_CONSEQUENCE_BINDS_LATER_GATES`
— see `docs/governance/m15_track_a_t3_stage_ruling.md`. R1 **measures and
reports** the ratio distribution; R1 does not decide anything with it. The
numerator is the ruled one: the **pre-floor** barrier ``1.5 × ATR14_M15``,
because the post-floor barrier is defined as ``max(…, 3.0 × cost)`` and its
ratio to cost is therefore ``≥ 3.0`` identically — a test that cannot fail is
not the test the contract describes as "M15 must demonstrably escape the M1 cost
regime". Both alternatives are reported alongside it, so the ruling can be
re-read against the numbers rather than argued about in the abstract.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Final

from scripts.m15_gate3a.aggregation import to_pips
from scripts.m15_gate3a.calendar_build import (
    is_event_eligible,
    session_of,
    validate_calendar_b,
)
from scripts.m15_gate3a.cost_schema import (
    EXECUTION_PADDING_PIP,
    FLAT_SLIPPAGE_CELL_PIP,
    SESSIONS_UTC,
)
from scripts.m15_track_a.derivation import DerivedM15

#: Ruling 6, FROZEN. Restated as constants so a reader can see the arithmetic.
TP_ATR_MULTIPLE: Final[float] = 1.5
SL_ATR_MULTIPLE: Final[float] = 1.0
TP_COST_FLOOR_MULTIPLE: Final[float] = 3.0
SL_COST_FLOOR_MULTIPLE: Final[float] = 2.0
ELIGIBILITY_COST_MULTIPLE: Final[float] = 2.0

#: Ruling 6, FROZEN.
ATR_PERIOD: Final[int] = 14

#: T-3's threshold, and it is a **reporting** threshold here, not a decision.
T3_MEDIAN_RATIO_THRESHOLD: Final[float] = 3.0

#: S-20a: which price series ATR is computed on is unregistered. Named, not hidden.
ATR_PRICE_SERIES: Final[str] = "bid"
ATR_SERIES_STATUS: Final[str] = "ATR_PRICE_SERIES_IS_AN_UNREGISTERED_RESEARCH_CHOICE_S_20A"

#: The ruled numerator, and the two it was ruled against.
T3_NUMERATOR: Final[str] = "pre_floor_tp"
T3_NUMERATOR_VARIANTS: Final[tuple[str, ...]] = ("pre_floor_tp", "post_floor_tp", "post_floor_sl")

OUTPUT_CLASSIFICATION: Final[str] = "NON_DECISION_BEARING_EXPLORATORY_ONLY"
OUTPUT_CLASSIFICATION_SECONDARY: Final[str] = "RESEARCH_SCRATCH_NON_AUTHORITATIVE"


class R1SurveyError(RuntimeError):
    """Raised when the survey cannot be produced as specified."""


def _quantile(values: list[float], fraction: float) -> float | None:
    """The nearest-rank quantile of a non-empty sample, or None.

    Nearest-rank rather than an interpolating estimator: the p90/p95 numbers are
    reported as *observed* spreads, and an interpolated value is a spread that
    was never quoted.
    """
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(-(-len(ordered) * fraction // 1)) - 1))
    return ordered[index]


def _true_range(bar: dict[str, Any], previous_close: float | None, side: str) -> float:
    high = bar[f"{side}_h"]
    low = bar[f"{side}_l"]
    if previous_close is None:
        return high - low
    return max(high - low, abs(high - previous_close), abs(low - previous_close))


def wilder_atr(
    bars: list[dict[str, Any]], *, pair: str, side: str = ATR_PRICE_SERIES
) -> list[float | None]:
    """Wilder's 14-period ATR in **pips**, aligned to ``bars``, None until seeded.

    ``None`` for the first ``ATR_PERIOD`` bars rather than a partial average: a
    partial ATR is a different statistic wearing the same name, and the M1
    lineage's ``min_periods`` defect was exactly that.
    """
    atr: list[float | None] = []
    ranges: list[float] = []
    previous_close: float | None = None
    running: float | None = None
    for bar in bars:
        true_range = _true_range(bar, previous_close, side)
        previous_close = bar[f"{side}_c"]
        if running is None:
            ranges.append(true_range)
            if len(ranges) < ATR_PERIOD:
                atr.append(None)
                continue
            running = sum(ranges) / ATR_PERIOD
        else:
            running = (running * (ATR_PERIOD - 1) + true_range) / ATR_PERIOD
        atr.append(to_pips(running, pair))
    return atr


@dataclass(frozen=True)
class R1Survey:
    """Everything stage R1 owes, and its classification."""

    run_id: str
    epoch: str
    span_start_utc: str
    span_end_utc: str
    timeframe: str
    pairs: tuple[str, ...]
    schema: dict[str, Any]
    coverage: dict[str, Any]
    spread_distribution: dict[str, Any]
    cost_table: dict[str, Any]
    eligibility: dict[str, Any]
    barrier_cost_ratio: dict[str, Any]
    accounting: dict[str, Any]
    containment: dict[str, Any]
    notes: tuple[str, ...] = ()

    classification: str = OUTPUT_CLASSIFICATION
    classification_secondary: str = OUTPUT_CLASSIFICATION_SECONDARY
    required_outputs: tuple[str, ...] = field(
        default=(
            "schema",
            "span",
            "pair_coverage",
            "missingness",
            "descriptive_statistics",
            "barrier_cost_ratio_distribution_and_median_t3",
            "eligible_bar_rate_per_pair_and_session",
            "per_pair_session_spread_distribution",
        )
    )

    def as_record(self) -> dict[str, Any]:
        """The survey as a metadata record. Statistics only — never a bar."""
        return {
            "run_id": self.run_id,
            "epoch": self.epoch,
            "span_start_utc": self.span_start_utc,
            "span_end_utc": self.span_end_utc,
            "timeframe": self.timeframe,
            "pairs": list(self.pairs),
            "schema": self.schema,
            "coverage": self.coverage,
            "spread_distribution": self.spread_distribution,
            "cost_table": self.cost_table,
            "eligibility": self.eligibility,
            "barrier_cost_ratio": self.barrier_cost_ratio,
            "accounting": self.accounting,
            "containment": self.containment,
            "notes": list(self.notes),
            "required_outputs": list(self.required_outputs),
            "classification": self.classification,
            "classification_secondary": self.classification_secondary,
        }


def _session_spreads(
    bars: list[dict[str, Any]], *, pair: str, calendar_b: dict[str, Any]
) -> dict[str, list[float]]:
    by_session: dict[str, list[float]] = {name: [] for name in SESSIONS_UTC}
    for bar in bars:
        moment: datetime = bar["ts"]
        if not bar.get("complete_bucket"):
            # Ruling 3 FROZEN: "event/label eligibility requires a complete
            # bucket (n_source_bars == 15). Incomplete buckets are recorded for
            # gap diagnostics only -- they must not create labels or trade
            # events." The first drafting never looked at this flag, so
            # incomplete buckets entered the eligible population, the spread
            # median and the T-3 ratio. Measured by a review role.
            continue
        if not is_event_eligible(moment, calendar_b):
            continue
        by_session[session_of(moment)].append(to_pips(bar["ask_c"] - bar["bid_c"], pair))
    return by_session


def survey(
    derived: DerivedM15,
    *,
    calendar_b: dict[str, Any],
    calendar_a_authority: str | None = None,
    containment_status: str | None = None,
    breadth_k: int | None = None,
) -> R1Survey:
    """Produce stage R1's required outputs from an authorised derivation.

    Takes a :class:`DerivedM15` rather than raw rows: the survey measures what
    the **authorised** derivation produced, so there is no route by which it
    could measure bars that did not come through the gates.
    """
    if not isinstance(derived, DerivedM15):
        raise R1SurveyError(
            f"R1 survey refused: expected a DerivedM15 from the authorised derivation "
            f"route, got {type(derived).__name__}."
        )

    calendar_b = validate_calendar_b(calendar_b, expected_epoch=derived.epoch)
    pairs = tuple(sorted(derived.bars_by_pair))
    schema: dict[str, Any] = {}
    coverage: dict[str, Any] = {}
    spread_distribution: dict[str, Any] = {}
    cost_table: dict[str, Any] = {}
    eligibility: dict[str, Any] = {}
    ratios_by_variant: dict[str, list[float]] = {name: [] for name in T3_NUMERATOR_VARIANTS}
    per_pair_ratio_median: dict[str, float | None] = {}

    for pair in pairs:
        bars = derived.bars_by_pair[pair]
        report = derived.gap_reports.get(pair, {})

        schema[pair] = {
            "bars": len(bars),
            "keys": sorted(bars[0]) if bars else [],
            "first_ts": bars[0]["ts"].isoformat() if bars else None,
            "last_ts": bars[-1]["ts"].isoformat() if bars else None,
        }
        coverage[pair] = {
            "complete_buckets": sum(1 for bar in bars if bar.get("complete_bucket")),
            "incomplete_buckets": sum(1 for bar in bars if not bar.get("complete_bucket")),
            "gap_report": report,
        }

        session_spreads = _session_spreads(bars, pair=pair, calendar_b=calendar_b)
        spread_distribution[pair] = {
            session: {
                "n": len(values),
                "median_pip": statistics.median(values) if values else None,
                "p90_pip": _quantile(values, 0.90),
                "p95_pip": _quantile(values, 0.95),
            }
            for session, values in session_spreads.items()
        }
        cost_table[pair] = {
            session: (
                None
                if not values
                else statistics.median(values) + EXECUTION_PADDING_PIP + FLAT_SLIPPAGE_CELL_PIP
            )
            for session, values in session_spreads.items()
        }

        atr = wilder_atr(bars, pair=pair)
        seen = {name: 0 for name in SESSIONS_UTC}
        eligible = {name: 0 for name in SESSIONS_UTC}
        pair_ratios: list[float] = []
        for bar, atr_pips in zip(bars, atr, strict=True):
            moment: datetime = bar["ts"]
            # Ruling 3 FROZEN, as above. ATR still sees the bar -- the committed
            # manifest says incomplete buckets are "retained for indicator
            # history" -- which is why the flag is tested here, not in
            # ``wilder_atr``.
            if not bar.get("complete_bucket"):
                continue
            if not is_event_eligible(moment, calendar_b):
                continue
            session = session_of(moment)
            seen[session] += 1
            cost = cost_table[pair][session]
            if atr_pips is None or cost is None or cost <= 0:
                continue
            pre_floor_tp = TP_ATR_MULTIPLE * atr_pips
            if pre_floor_tp < ELIGIBILITY_COST_MULTIPLE * cost:
                continue
            eligible[session] += 1
            variants = {
                "pre_floor_tp": pre_floor_tp,
                "post_floor_tp": max(pre_floor_tp, TP_COST_FLOOR_MULTIPLE * cost),
                "post_floor_sl": max(SL_ATR_MULTIPLE * atr_pips, SL_COST_FLOOR_MULTIPLE * cost),
            }
            for name, numerator in variants.items():
                ratios_by_variant[name].append(numerator / cost)
            pair_ratios.append(variants[T3_NUMERATOR] / cost)

        eligibility[pair] = {
            session: {
                "bars_considered": seen[session],
                "eligible": eligible[session],
                "eligible_rate": (eligible[session] / seen[session]) if seen[session] else None,
            }
            for session in SESSIONS_UTC
        }
        per_pair_ratio_median[pair] = statistics.median(pair_ratios) if pair_ratios else None

    ruled = ratios_by_variant[T3_NUMERATOR]
    barrier_cost_ratio = {
        "numerator": T3_NUMERATOR,
        "numerator_basis": "docs/governance/m15_track_a_t3_stage_ruling.md",
        "threshold": T3_MEDIAN_RATIO_THRESHOLD,
        "n_eligible": len(ruled),
        "median": statistics.median(ruled) if ruled else None,
        "mean": statistics.fmean(ruled) if ruled else None,
        "p10": _quantile(ruled, 0.10),
        "p90": _quantile(ruled, 0.90),
        "median_by_pair": per_pair_ratio_median,
        "variants_reported_for_the_ruling": {
            name: {
                "n": len(values),
                "median": statistics.median(values) if values else None,
            }
            for name, values in ratios_by_variant.items()
        },
        "t3_status": _t3_status(ruled),
    }

    return R1Survey(
        run_id=derived.run_id,
        epoch=derived.epoch,
        span_start_utc=derived.span_start_utc,
        span_end_utc=derived.span_end_utc,
        timeframe="M15",
        pairs=pairs,
        schema=schema,
        coverage=coverage,
        spread_distribution=spread_distribution,
        cost_table=cost_table,
        eligibility=eligibility,
        barrier_cost_ratio=barrier_cost_ratio,
        accounting={
            "breadth_k": breadth_k,
            "calendar_a_authority": calendar_a_authority or derived.calendar_authority,
            "calendar_a_content_digest": derived.calendar_content_digest,
            "calendar_b_holiday_status": calendar_b.get("holiday_list_status"),
            "atr_price_series": ATR_PRICE_SERIES,
            "atr_price_series_status": ATR_SERIES_STATUS,
        },
        containment={"status": containment_status},
        notes=(
            "R1 measures; R1 decides nothing. The T-3 consequence binds a later gate.",
            "Calendar B's holiday list is empty, so the eligible-bar rate is OVERSTATED.",
            ATR_SERIES_STATUS,
        ),
    )


def _t3_status(ratios: list[float]) -> str:
    """A **reported** status, never a verdict this stage is entitled to reach."""
    if not ratios:
        return "T3_NOT_MEASURABLE_NO_ELIGIBLE_BARS"
    median = statistics.median(ratios)
    if median < T3_MEDIAN_RATIO_THRESHOLD:
        return "T3_MEDIAN_ELIGIBLE_BARRIER_COST_RATIO_BELOW_3_0_REPORTED_TO_THE_LATER_GATE"
    return "T3_MEDIAN_ELIGIBLE_BARRIER_COST_RATIO_AT_OR_ABOVE_3_0_REPORTED_TO_THE_LATER_GATE"


__all__ = [
    "ATR_PERIOD",
    "ATR_PRICE_SERIES",
    "ATR_SERIES_STATUS",
    "T3_MEDIAN_RATIO_THRESHOLD",
    "T3_NUMERATOR",
    "T3_NUMERATOR_VARIANTS",
    "R1Survey",
    "R1SurveyError",
    "survey",
    "wilder_atr",
]
