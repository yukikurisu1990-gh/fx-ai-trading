"""The hypothesis ledger — what has already been asked of the seen panels.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

This is a **record, not a gate**. Nothing checks it, nothing fails because of it,
and it authorises nothing. It exists because the three seen panels are now being
reused deliberately as a screening surface, and the cost of that decision is
cumulative multiplicity that is otherwise invisible: each round corrects within
its own family and none of them can see the ones before.

Reading it honestly: by Round A something like **1,200 configurations** have been
fitted or evaluated against `2025-04-25 … 2025-12-28`, and a few dozen against
each 730-day panel. A cell that looks good on 2025 alone is competing against
that history, which is why the Round A plan forbids 2025 from being a deciding
vote and requires the two 730-day panels to agree.

Entries are appended by hand when a round completes. Keeping it accurate is a
research discipline, not something the code can enforce.
"""

from __future__ import annotations

from typing import Any, Final

LEDGER: Final[list[dict[str, Any]]] = [
    {
        "id": "H-001",
        "round": "Exploratory Round 1",
        "population": "all M15 bars, development 2025-04-25..2025-12-28",
        "target": "forward return sign / net PnL after cost",
        "condition_family": "none (unconditional)",
        "horizon_family": "1..192 bars",
        "configurations": "26 strategies + 8 features x 6 horizons IC scan",
        "prespecified": False,
        "result": "all 26 net-negative; trend/breakout gross-negative; every feature negative IC",
        "status": "CLOSED",
    },
    {
        "id": "H-002",
        "round": "Exploratory Round 1 (role D/E)",
        "population": "all M15 bars, development",
        "target": "net PnL after cost",
        "condition_family": "session / ATR / ADX / spread",
        "horizon_family": "24h..6d",
        "configurations": "1,078 fits, uncorrected",
        "prespecified": False,
        "result": "every gate lowered net; ADX separates nothing; session edge is first-half only",
        "status": "CLOSED",
    },
    {
        "id": "H-003",
        "round": "Exploratory Round 1 (role G)",
        "population": "cross-sectional, development",
        "target": "relative-value net PnL",
        "condition_family": "currency strength / dispersion",
        "horizon_family": "24h..5d",
        "configurations": "~40",
        "prespecified": False,
        "result": "96% of gross is net currency exposure; matched time-series control wins",
        "status": "CLOSED",
    },
    {
        "id": "H-004",
        "round": "Exploratory Round 1 (role H)",
        "population": "all M15 bars, development, Aug-Dec walk-forward",
        "target": "24h forward return (direction) and y_beats_cost",
        "condition_family": "~50 price/vol/session features",
        "horizon_family": "96 bars",
        "configurations": "57 variants",
        "prespecified": False,
        "result": "beaten by one raw feature; family-wise p = 0.699; incoherent ablation",
        "status": "CLOSED",
    },
    {
        "id": "H-005",
        "round": "Exploratory Round 2",
        "population": "all M15 bars, development",
        "target": "net PnL, multi-day reversal",
        "condition_family": "ATR tercile (secondary)",
        "horizon_family": "384/480/576 bars",
        "configurations": "39 pre-registered",
        "prespecified": True,
        "result": "MULTI_DAY_REVERSAL_UNRESOLVED_INSUFFICIENT_DETECTION_POWER; power 0.29",
        "status": "CLOSED",
    },
    {
        "id": "H-006",
        "round": "Supplemental Historical Replication",
        "population": "all M15 bars, supplemental 2023-04-26..2025-04-24",
        "target": "net PnL, frozen reversal candidate",
        "condition_family": "9-cell neighbourhood + ATR-high",
        "horizon_family": "384/480/576",
        "configurations": "11",
        "prespecified": True,
        "result": "MULTI_DAY_REVERSAL_FAILED_SUPPLEMENTAL_HISTORY_REPLICATION; gross -426.5",
        "status": "CLOSED — family dropped from active research",
    },
    {
        "id": "H-007",
        "round": "Momentum Hypothesis",
        "population": "all M15 bars, momentum panel 2021-04-26..2023-04-25",
        "target": "net PnL, mirrored candidate",
        "condition_family": "9-cell neighbourhood",
        "horizon_family": "384/480/576",
        "configurations": "10",
        "prespecified": True,
        "result": "MULTI_DAY_MOMENTUM_UNRESOLVED_IN_FRESH_EXPLORATORY_HISTORY;"
        " nothing separable from zero",
        "status": "CLOSED",
    },
    {
        "id": "H-008",
        "round": "Round A / T1",
        "population": "all three seen panels",
        "target": "forward excursion distribution (descriptive, no direction)",
        "condition_family": "ATR tercile x session x bloc",
        "horizon_family": "16/48/96/192/480",
        "configurations": "105 descriptive cells per panel, none selected",
        "prespecified": True,
        "result": "see m15_round_a_results.md",
        "status": "CLOSED — Round A",
    },
    {
        "id": "H-009",
        "round": "Round A / T2",
        "population": "all three seen panels",
        "target": "conditional forward drift under a per-family fixed direction",
        "condition_family": "ATR / vol expansion / D1 trend / range position / extreme move",
        "horizon_family": "48/192/480",
        "configurations": "39 pre-registered cells",
        "prespecified": True,
        "result": "see m15_round_a_results.md",
        "status": "CLOSED — Round A",
    },
    {
        "id": "H-010",
        "round": "Round B'/B'-1",
        "population": "all three seen panels, 1-bar sigma-normalised returns",
        "target": "variance ratio VR(q) against three matched nulls",
        "condition_family": "none (aggregate second moment)",
        "horizon_family": "q in {2,4,12,48,96,192,480}",
        "configurations": "7 horizons x 3 nulls, pre-registered",
        "prespecified": True,
        "result": (
            "VR < 1 at every horizon and panel, stable at q<=192 on both deciding "
            "panels (z -2.1 to -14.7), family-max p = 0.005 on all three. Carried "
            "by non-JPY at short horizons: the JPY bloc reaches |z|>=2 at 2 of 12 "
            "cells and crosses it with the OPPOSITE sign at q=192 on 2021-23. "
            "POST HOC: not a one-bar effect -- 20 and 17 of 100 lags sit outside a "
            "3sd null band against 0.27 expected -- and the best linear predictor "
            "over 96 bars of memory reaches 6-16% of break-even in-sample, at every "
            "horizon from 1 bar to 12 hours"
        ),
        "status": "CLOSED - real but unharvestable microstructure",
    },
    {
        "id": "H-011",
        "round": "Round B'/B'-2",
        "population": "excursion anchors on all three seen panels",
        "target": "retrace geometry against a matched sign-flip null",
        "condition_family": "2 HTF contexts x 2 states, plus unconditioned",
        "horizon_family": "k in {1.5, 2.0, 3.0} sigma",
        "configurations": "15 pre-registered cells",
        "prespecified": True,
        "result": (
            "k=2.0 and k=3.0 survive all five clauses on both deciding panels "
            "(+0.066/+0.093 and +0.147/+0.157, z 2.97 to 5.70) -- but ONLY after "
            "the primary null was corrected. The null had re-attached each real "
            "bar's high/low offsets to a sign-flipped return, and those offsets "
            "correlate -0.57 with the bar's own sign, so the null carried "
            "incoherent bars into the two columns the detector reads. The sign "
            "REVERSED on correction. POST HOC: the same statistic in sigma units, "
            "with no excursion in its denominator, is positive in all 9 cells and "
            "significant in none (z +0.18 to +1.96), and real anchors are smaller "
            "than null anchors (z -2.94), so the fraction is mostly a denominator "
            "effect. Against the secondary IID null the differences are 2-3x "
            "larger, so about two-thirds of the effect is volatility clustering"
        ),
        "status": (
            "OPEN - direction-consistent with H-010, not independently established; "
            "second look at the same data, and its family-wise p is pinned at the "
            "1/41 floor by 40 draws"
        ),
    },
    {
        "id": "H-012",
        "round": "Round B'/B'-4",
        "population": "all three seen panels",
        "target": "monthly TSMOM net PnL, cost-inclusive",
        "condition_family": "none",
        "horizon_family": "lookback {1,2,3} x hold {1,3} months",
        "configurations": "6 pre-registered cells",
        "prespecified": True,
        "result": (
            "MONTHLY_TSMOM_NOT_SUPPORTED_IN_EXISTING_PRICE_HISTORY; gross negative in "
            "11 of 12 cells across both deciding panels, the twelfth disagreeing in "
            "sign, family-max p = 0.32 / 0.31, every per-cell t in [-1.571, +0.104]. "
            "An underpowered null result -- about 7 non-overlapping observations per "
            "pair against 3.5-4.8 effective independent pairs -- not a refutation"
        ),
        "status": "CLOSED",
    },
]

#: Rough cumulative count of configurations evaluated against the 2025
#: development window, for the multiplicity note in the results document.
DEVELOPMENT_CONFIGURATIONS_APPROX: Final[int] = 1200


def summary() -> dict[str, Any]:
    return {
        "entries": len(LEDGER),
        "closed": sum(1 for e in LEDGER if e["status"].startswith("CLOSED")),
        "open": sum(1 for e in LEDGER if e["status"].startswith("OPEN")),
        "prespecified": sum(1 for e in LEDGER if e["prespecified"]),
        "post_hoc": sum(1 for e in LEDGER if not e["prespecified"]),
        "development_configurations_approx": DEVELOPMENT_CONFIGURATIONS_APPROX,
    }


__all__ = ["DEVELOPMENT_CONFIGURATIONS_APPROX", "LEDGER", "summary"]
