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
    {
        "id": "H-013",
        "round": "Monetizability/Stage 1A",
        "population": "excursion anchors on all three seen panels",
        "target": "sigma-level ABSOLUTE retrace against a matched sign-flip null",
        "condition_family": "none",
        "horizon_family": "k in {1.5, 2.0, 3.0} sigma",
        "configurations": "3 thresholds, pre-registered, 200 null draws",
        "prespecified": True,
        "result": (
            "RETRACE_GEOMETRY_FAMILY_DROPPED_AFTER_CLEAN_RETEST. No threshold "
            "reaches |z| >= 2 on any panel; the largest is +1.50 and a generated "
            "random walk reaches +1.74. The SELECTION was measured this time "
            "rather than inherited: real anchors form faster (z -14.11 at k=1.5), "
            "so their windows are shorter, and their excursions are smaller "
            "(z -4.88). Every statistic that reaches significance moves the way "
            "that mismatch predicts -- the fraction rises as its denominator "
            "shrinks (z +3.25..+5.05), the adverse extension falls as the window "
            "shortens (z -3.3..-3.9) -- and the sigma-level retrace, whose "
            "direction neither predicts, is the one that never does"
        ),
        "status": "CLOSED - the fraction's positive is a selection difference",
    },
    {
        "id": "H-014",
        "round": "Monetizability/Stage 1B",
        "population": "4 detector-free horizons and 3 anchor thresholds, both deciding panels",
        "target": "economic headroom: an in-sample linear selector's excess over a matched null",
        "condition_family": "8 past-only features, fixed",
        "horizon_family": "q in {1,4,12,48} bars and k in {1.5,2.0,3.0} sigma",
        "configurations": "7 populations x 2 cost levels, pre-registered",
        "prespecified": True,
        "result": (
            "PATH_STRUCTURE_STATISTICALLY_REAL_BUT_ECONOMICALLY_TOO_SMALL. The "
            "excess ranges -0.68 to +2.39 round trips per opportunity against a "
            "0.50 floor: the four horizon populations are 2-4 orders of magnitude "
            "short, the two lower anchor thresholds are short by 2-8x AND reverse "
            "sign between the deciding panels. The only population clearing the "
            "floor has 6-9 events per pair per year, z ~ 0.9, a top-ten-day share "
            "above 1, a take-all bloc reversal (JPY +17.30 vs non-JPY -3.96 on "
            "the second panel) and ONE PAIR AT 105% of that panel's net. A "
            "perfect-foresight oracle clears the round trip by 6-23x and earns "
            "+1.672 on a pure random walk, which is why the gate does not read it"
        ),
        "status": (
            "CLOSED for fixed-horizon entries held to window end under a linear "
            "selector on these features; barrier EXITS and non-linear selectors "
            "are not bounded by it"
        ),
    },
    {
        "id": "H-015",
        "round": "Monetizability/Stage 1C",
        "population": "tick volume over the three seen spans, 34,316,488 M1 rows",
        "target": "is volume a proxy for volatility, spread and session, or new information",
        "condition_family": "none",
        "horizon_family": "next bar",
        "configurations": "one regression and two forward targets, pre-registered",
        "prespecified": True,
        "result": (
            "TICK_VOLUME_INFORMATION_INCREMENTALLY_DISTINCT. Median R^2 against "
            "realised volatility, spread, the current move and the session is "
            "0.52 and 0.46 against a 0.80 redundancy threshold. The residual's "
            "Spearman with the next bar's ABSOLUTE return is +0.124 and +0.148, "
            "the same sign on 20 of 20 pairs on both deciding panels, z +10.1 and "
            "+17.0 against a block-shift null that keeps each series' own serial "
            "dependence. Against the next bar's SIGNED return it is -0.0014 and "
            "+0.0013, z -1.3 and +1.3, 12 and 13 pairs of 20"
        ),
        "status": (
            "OPEN - kept as a VOLATILITY feature candidate; it says nothing about direction"
        ),
    },
    {
        "id": "H-016",
        "round": "EconomicEdge/Stage 2",
        "population": "PAIRS_20 over the three seen panels, weekly to monthly rebalancing",
        "target": "carry economics from BIS policy rates, spot and interest kept apart",
        "condition_family": "3 families (pair level, cross-sectional k in {2,3}, carry change)",
        "horizon_family": "weekly, fortnightly, monthly",
        "configurations": "12 pre-registered cells -- the entire carry search",
        "prespecified": True,
        "result": (
            "CARRY_EDGE_NOT_SUPPORTED. Only cross_sectional_k3 clears gross, "
            "same-sign and net on both deciding panels, and in the textbook good "
            "shape: net +82 / +118 pips per pair with carry income +49 / +121 and "
            "spot +33 / -2, at 0.18-0.28 turnover a year and 0.5-0.9 pips of cost. "
            "It fails anyway: JPY pairs return +262 / +384 against non-JPY "
            "+4.2 / +4.0, a ratio of 63x and 95x, so it is a SHORT-YEN trade "
            "wearing a diversified label with 3.2-4.6 effective independent "
            "pairs; and the fourth sub-period of BOTH deciding panels is a large "
            "loss (-95.6 and -72.8 against +50 to +88 in the first three), which "
            "is the carry unwind. pair_level earned +218 / +522 of interest and "
            "gave it back on spot on one panel and not the other; carry_change "
            "reverses sign between panels at every frequency"
        ),
        "status": "CLOSED - over these panels the G10 carry premium IS the short-yen trade",
    },
    {
        "id": "H-017",
        "round": "EconomicEdge/Stage 3-4",
        "population": "daily tick-volume state, one carry rebalance ahead",
        "target": "does volume say WHEN a slow signal is worth holding",
        "condition_family": "5 representations",
        "horizon_family": "3 targets, none of them direction",
        "configurations": "15 pre-registered cells, plus 4 integration models",
        "prespecified": True,
        "result": (
            "Volume forecasts next-week realised volatility strongly -- rho +0.14 "
            "and +0.16, z +9.2 and +10.9, 20 of 20 pairs on both deciding panels "
            "-- and forecasts whether the move will exceed the round trip not at "
            "all: rho -0.027 to +0.019 with 9 to 13 pairs of 20, a coin flip. The "
            "spread widens with volume too, so the only target that pays for a "
            "trade is the one volume cannot see. As a filter it is WORSE than the "
            "unfiltered carry base in 15 of 15 cells across all three panels, "
            "turning +120.3 into -49.3 to -155.6 on the second deciding panel, "
            "because it removes 51-66% of the days and a carry position accrues "
            "its interest every day it is held. Time in the market is the return"
        ),
        "status": "CLOSED - volume is a volatility variable, not a timing one",
    },
    {
        "id": "H-018",
        "round": "EconomicEdge/Route C",
        "population": "days within +/-1 of a G10 policy-rate CHANGE, 108 changes",
        "target": "do scheduled events define an exogenous opportunity population",
        "condition_family": "none",
        "horizon_family": "one day",
        "configurations": "one comparison, event days against all others",
        "prespecified": False,
        "result": (
            "CALENDAR_EVENT_OPPORTUNITY_STRUCTURE_SUPPORTED, for the OPPORTUNITY "
            "layer only. Absolute move 1.55x and 1.31x larger AND the spread "
            "0.92x and 0.94x NARROWER, so move-net-of-cost is 1.60x and 1.35x "
            "with 19 of 19 and 18 of 20 pairs agreeing. That is the first "
            "opportunity variable in this programme whose cost works FOR it -- "
            "volume-selected busy days come with wider spreads because volume "
            "rises in thin conditions too, while scheduled decisions happen in "
            "the deepest liquidity. But the cost-clearing RATE rises only 1.04x, "
            "because 91% of ordinary days already move more than the round trip: "
            "magnitude was never the binding constraint, direction is, and "
            "nothing here addresses it. The population is rate CHANGES, not "
            "scheduled meetings, so it is biased toward surprises"
        ),
        "status": (
            "OPEN - a working opportunity anchor with no expected-return source to apply it to"
        ),
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
