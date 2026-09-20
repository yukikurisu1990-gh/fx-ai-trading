# ruff: noqa: E501 -- reranking prose
"""The candidate inventory, reranked against everything learned since #484.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Authority: the Human + ChatGPT ruling of 2026-09-19, sections 10-18.

#484 ranked 28 candidates on a judgement with declared weights, before any of the
three proposed tracks had run. Three have now run and all three returned
NOT_SUPPORTED, and the ruling closed one family outright. The old ranking put S01
first and S13 second; both are now spent. This module records what the new
evidence does to every candidate, and why, rather than re-scoring the same
weights and hoping the order changes.

**The single most important thing learned is not about any candidate.** It is
about the span, and it cuts deeper than a reordering. Two-sided 5%, 80% power on
an annual Sharpe needs roughly `2.80 / sqrt(years)` — the same constant the
committed feasibility gate already carries as `power_multiplier = 2.8016`:

    4.81 years  (the seen M15 corpus, 1213 decision days)  ->  1.28
    17.69 years (ECB daily FX 1999-2016, 4458 days)        ->  0.67
    22.50 years (both, disjoint, 5671 days)                ->  0.59

A realistic single-source edge is a net Sharpe of 0.2-0.5, so on the 4.81-year
corpus none of that range is separable from zero — which is exactly what happened
to T-R and T-R2, both of which produced positive gross that settled nothing.

**But the long span does not fix that, and this module does not claim it does.**
The same criterion applied to 0.59 says the pooled 22.5 years cannot separate a
0.2-0.5 edge either. Computed directly, two-sided power over the pooled span is
0.16 at a true Sharpe of 0.2, **0.30** at 0.3 and 0.66 at 0.5. Every span this
programme may lawfully reach is underpowered against the effect it is looking
for. The long span is worth reaching because it moves the power at 0.3 from 0.10
to 0.30, and because two disjoint spans permit a sign-agreement check — not
because it makes a decisive test available.

**One convention, stated once.** Everything here is **two-sided** 5%, because the
direction is exactly what is in question. That is not the convention the earlier
records used: `capacity.sample_years_needed` is one-sided by its own docstring,
and the committed T-R records give **1.13** for the same 1213-day span where this
module gives 1.28. Neither is wrong - they answer different questions - but
quoting one alongside the other flatters whichever is cited. On the two-sided
convention used throughout this module, detecting a 0.3 Sharpe at 80% power needs
**87.2 years**; the one-sided figure is 68.7. Both are three to four times longer
than any span this programme can reach.


So the reordering below is by *least underpowered, and outside a closed family*.
That is a weaker basis than "this candidate can be decided", and no row here may
be read as the latter.
"""

from __future__ import annotations

import math
from typing import Any, Final

#: What the new evidence does to a candidate.
CLOSED_BY_EXECUTION: Final[str] = "closed_the_track_ran_and_returned_not_supported"
CLOSED_BY_FAMILY: Final[str] = "closed_inside_the_declared_family_boundary"
DEPENDS_ON_A_CLOSED_BASE: Final[str] = "excluded_its_own_rule_requires_a_base_that_is_now_closed"
EVENT_FILTER_ON_A_CLOSED_SIGNAL: Final[str] = "excluded_it_conditions_a_closed_signal_on_events"
STILL_EXCLUDED: Final[str] = "excluded_already_a_rename_rescue_suspension_or_infeasible"
BLOCKED_BY_DATA: Final[str] = "blocked_paid_or_authenticated_data"
PENALISED: Final[str] = "eligible_but_materially_weakened_by_the_new_evidence"
PROMOTED: Final[str] = "eligible_and_relatively_stronger_under_the_new_evidence"

#: Two-sided 5%, 80% power.
_Z: Final[float] = 1.959963985 + 0.841621234

#: One year is this many decision days, everywhere in this package.
TRADING_DAYS_PER_YEAR: Final[float] = 252.0

#: Decision-day counts, each taken from a committed record rather than recomputed
#: here: the recent span from `market_yields.prereg.DECISION_DAYS`, the long span
#: from T-V's `return_panel_days` in artifacts/research/valuation/development.json.
#: Years are days / 252 for both, so the two are on one basis - an earlier version
#: mixed a derived 252-day year against a counted calendar year.
RECENT_DECISION_DAYS: Final[int] = 1213
LONG_DECISION_DAYS: Final[int] = 4458


def detectable_sharpe(years: float) -> float:
    """The smallest annual Sharpe this many years can separate from zero.

    Two-sided 5% at 80% power, under the usual `se = 1/sqrt(years)` approximation
    for an annualised Sharpe. Dropping the `(1 + S^2/2)` term makes this the
    *best* case, so every span is at least this underpowered and never less.
    """
    return _Z / math.sqrt(years)


def power_at(true_sharpe: float, years: float) -> float:
    """Two-sided 5% power to reject zero when the true annual Sharpe is this.

    Stated because `detectable_sharpe` alone invites the reading that a span below
    the threshold is usable. These numbers are what say it is not.
    """
    se = 1.0 / math.sqrt(years)
    crit = 1.959963985 * se
    upper = 0.5 * math.erfc((crit - true_sharpe) / (se * math.sqrt(2.0)))
    lower = 0.5 * math.erfc((crit + true_sharpe) / (se * math.sqrt(2.0)))
    return upper + lower


def _span(days: int) -> float:
    return round(days / TRADING_DAYS_PER_YEAR, 2)


SPANS: Final[dict[str, dict[str, Any]]] = {
    "seen_m15_corpus": {
        "span": "2021-04-27 .. 2025-12-26",
        "decision_days": RECENT_DECISION_DAYS,
        "years": _span(RECENT_DECISION_DAYS),
        "source": "the three guarded OANDA M15 routes, EXPLORATORY_SEEN_DATA",
        "detectable_net_sharpe_at_80pct_power": round(
            detectable_sharpe(_span(RECENT_DECISION_DAYS)), 2
        ),
        "power_at_true_sharpe_0_3": round(power_at(0.3, _span(RECENT_DECISION_DAYS)), 2),
        "convention": (
            "two-sided 5%; the committed T-R records are one-sided and give 1.13 for this span"
        ),
    },
    "ecb_daily_fx": {
        "span": "1999-01-04 .. 2016-06-01",
        "decision_days": LONG_DECISION_DAYS,
        "years": _span(LONG_DECISION_DAYS),
        "source": "ECB euro reference rates, acquired for T-V, EXPLORATORY_SEEN_DEVELOPMENT_DATA",
        "detectable_net_sharpe_at_80pct_power": round(
            detectable_sharpe(_span(LONG_DECISION_DAYS)), 2
        ),
        "power_at_true_sharpe_0_3": round(power_at(0.3, _span(LONG_DECISION_DAYS)), 2),
    },
    "both_disjoint_spans": {
        "span": "1999-2016 and 2021-2025, separated by the protected fresh pool",
        "decision_days": RECENT_DECISION_DAYS + LONG_DECISION_DAYS,
        "years": _span(RECENT_DECISION_DAYS + LONG_DECISION_DAYS),
        "source": "the two above; the gap between them is forbidden and stays forbidden",
        "detectable_net_sharpe_at_80pct_power": round(
            detectable_sharpe(_span(RECENT_DECISION_DAYS + LONG_DECISION_DAYS)), 2
        ),
        "power_at_true_sharpe_0_3": round(
            power_at(0.3, _span(RECENT_DECISION_DAYS + LONG_DECISION_DAYS)), 2
        ),
        "why_it_matters": (
            "two disjoint seen spans either side of a protected window let a frozen rule be "
            "required to agree in sign on both, which is a period-robustness check no track "
            "in this programme has had"
        ),
        "what_it_does_not_buy": (
            "power. At 0.59 the pooled span still cannot separate a realistic 0.2-0.5 edge from "
            "zero - power is 0.16, 0.30 and 0.66 at true Sharpes of 0.2, 0.3 and 0.5. Two-"
            "sided, detecting 0.3 at 80% power needs 87.2 years; one-sided it is 68.7, and "
            "both are several times any span available. Sign agreement is also not "
            "free: under the null a pre-specified direction agrees on both spans with "
            "probability 0.25, so it is a weak screen and not a substitute for a declared "
            "primary statistic"
        ),
    },
}

#: The reassessment, candidate by candidate. `rank` is the new order among those
#: still eligible; `None` means it is not in the running.
REASSESSMENT: Final[dict[str, dict[str, Any]]] = {
    "S01": {
        "name": "front-end rate repricing -> currency relative return",
        "old_rank": 1,
        "disposition": CLOSED_BY_EXECUTION,
        "rank": None,
        "why": (
            "executed as T-R (fast, 5 day) and T-R2 (slow, 20 day). Both returned NOT_SUPPORTED "
            "and the 2026-09-19 ruling declared the scope-limited family boundary over public "
            "daily sovereign-yield data with simple fast and slow directional repricing. H-025, "
            "H-026"
        ),
    },
    "S13": {
        "name": "real exchange rate valuation",
        "old_rank": 2,
        "disposition": CLOSED_BY_EXECUTION,
        "rank": None,
        "why": (
            "executed as T-V. REAL_EXCHANGE_RATE_VALUATION_NOT_SUPPORTED_IN_DEVELOPMENT, and not "
            "on cost: the pre-registered incremental IC over the nominal control was -5.57 "
            "percentage points at Newey-West t -3.34, so the signal forecast the cross-section "
            "significantly worse than the price statistic it was meant to improve on. H-027"
        ),
    },
    "S02": {
        "name": "curve slope / curvature change",
        "old_rank": 3,
        "disposition": PENALISED,
        "rank": 4,
        "why": (
            "the ruling's closure explicitly does NOT reach curve shape, so this stays open and "
            "may not be excluded by paraphrase. But its prior falls: it is a second hypothesis "
            "on the same information set whose level just failed twice, the rate books' measured "
            "IC was negative at every horizon tested. Its data position is now SETTLED and "
            "good: the approved probe of 2026-09-20 reached every publisher the long leg needs "
            "- US Treasury, Bundesbank, Bank of Canada and the SNB all answered 200, with an "
            "artefact behind each, and the ECB curve is an independent second EUR route. The "
            "earlier TLS failures were local, as the committed probe's own note required them "
            "to be read. So what is weak here is the prior, not the feasibility"
        ),
        "what_would_raise_it": (
            "evidence that curve shape carries information the level does not - which is a claim "
            "about a different quantity, not a different lookback on the same one"
        ),
        "why_not_excluded_like_s28": (
            "both are differences of sovereign yields, so the distinction has to be named rather "
            "than assumed. The ruling's closure enumerates curve shape among the information "
            "sets it does NOT reach, and it does not enumerate breakevens; term structure is "
            "also a different quantity from a level or an inflation compensation, not a "
            "transformation of one. If a later reviewer judges that distinction too thin, the "
            "consistent resolution is to take S28 up again - not to close S02 by paraphrase"
        ),
    },
    "S03": {
        "name": "central bank meeting day repricing -> post-meeting drift (T-E primary)",
        "old_rank": 4,
        "disposition": EVENT_FILTER_ON_A_CLOSED_SIGNAL,
        "rank": None,
        "why": (
            "this is the reassessment the ruling's section 15 asked for, and it does not survive "
            "it. S03's directional information IS the two-year yield change - the same public "
            "daily sovereign-yield repricing measure the closure covers - restricted to meeting "
            "days. On free data the meeting-day measure is the daily change, so conditioning on "
            "the event selects a cleaner sample of the same closed quantity rather than "
            "supplying different information. The closure keeps intraday rate repricing open, "
            "but intraday rates are not obtainable free, so the version that would be genuinely "
            "new is the version we cannot build"
        ),
        "and_the_opportunity_layer_was_already_measured": (
            "H-018 and H-019 established that event days move 1.13-1.63x more, and in the same "
            "breath that the spread is 1.01-1.05x WIDER and that the event-to-ordinary RATIO of "
            "the share of days clearing the round trip is 1.00 - 1.0042 and 0.9958, unity. That "
            "is not a statement that every day clears; it is that cost-clearing does not move, "
            "because ordinary days already clear. The event population is an opportunity anchor "
            "with no cost advantage; "
            "H-019's own status is 'a forward-known opportunity anchor with nothing to point it "
            "at'. Pointing the closed rate signal at it does not change that"
        ),
        "power": (
            "34.4 events a year from the only four central banks obtainable without a login, so "
            "GBP, CAD, NZD and CHF have no anchor at all. Roughly 160 events over the seen "
            "corpus, needing about 12 bp per event for net 0.5"
        ),
        "what_this_exclusion_rests_on": (
            "A JUDGEMENT, NOT THE CLOSURE. The closure's FORBIDS list names lookback sweeps, "
            "EWMA half-life sweeps and threshold tuning; event conditioning is not in it, and "
            "the closure may not be widened by paraphrase - a rule this module states itself. "
            "So the accurate basis is: the direction source is a closed quantity, the cost "
            "advantage that would make the event population worth a slot was measured and is "
            "absent, and the power ceiling is 34.4 events a year across four of eight "
            "currencies. That is a decision not to spend a scarce test slot, and a later "
            "session may take it up again on new evidence without needing the closure reversed"
        ),
        "verdict_token": "EVENT_REPRICING_DATA_NOT_DECISION_GRADE",
    },
    "S04": {
        "name": "indicator release day repricing -> post-release drift (T-E secondary)",
        "old_rank": 6,
        "disposition": EVENT_FILTER_ON_A_CLOSED_SIGNAL,
        "rank": None,
        "why": (
            "same argument as S03, with a worse data position: no free official timestamped "
            "release calendar exists outside the US (C02), so the breadth that would make it "
            "decision-capable is the part that is missing. H-020 separately closed the US "
            "macro-surprise direction on a panel sign reversal at 24 events against a floor of 30"
        ),
    },
    "S05": {
        "name": "equity / volatility shock -> funding versus commodity currencies",
        "old_rank": 5,
        "disposition": PROMOTED,
        "rank": 1,
        "why": (
            "the information set has never been tested as a directional FX source in this "
            "programme - H-002 tested price-only session and ATR conditioning, not cross-asset "
            "state - and it is the candidate whose data most decisively fixes the power problem. "
            "VIX is daily and free from 1990-01-02 - a start date the committed probe of "
            "2026-09-14 corroborates independently - so it lines up against the ECB daily FX "
            "span 1999-2016 that T-V has already made seen, AND against the 2021-2025 corpus, "
            "with the protected pool untouched between them. That is 22.5 traded years across "
            "two disjoint spans: a detectable Sharpe of 0.59 instead of 1.28, and a frozen rule "
            "that can be required to agree in sign on both. It is the largest power improvement "
            "available to any candidate here, and it is still not enough to decide a 0.2-0.5 "
            "edge - see the module docstring"
        ),
        "weakness": (
            "breadth. A single risk axis maps to roughly two to three independent bets across "
            "the eight currencies, which raises the IC a given net Sharpe needs"
        ),
        "the_shape_has_failed_once_elsewhere": (
            "under-reaction to an external repricing is the same shape as T-R, on a different "
            "information set. The ruling's section 12 forbids generalising a rates result onto "
            "cross-asset, and section 17 lists cross-asset lead/lag as a candidate to evaluate, "
            "so this is permitted - but the prior should be held at the lower end, and the "
            "FX-momentum control that section 29 requires is what makes the test worth running"
        ),
    },
    "S06": {
        "name": "commodity prices -> commodity currencies (terms of trade)",
        "old_rank": 10,
        "disposition": PROMOTED,
        "rank": 2,
        "why": (
            "never tested - C11 was never run - free and daily from 1986 for WTI and Brent, so "
            "it has the same span advantage as S05, and its mechanism is currency-specific real "
            "income rather than a single global risk axis. That makes it a different economic "
            "claim from S05 even though oil and risk appetite co-move, and the co-movement is "
            "something a pre-registered control can measure rather than something that has to be "
            "assumed away"
        ),
        "weakness": (
            "effective breadth of one to two - CAD, AUD and NZD against the rest - and metals "
            "and dairy, which would widen it, are not free at daily frequency"
        ),
    },
    "S07": {
        "name": "credit spread / funding stress -> USD, JPY, CHF",
        "old_rank": 13,
        "disposition": PENALISED,
        "rank": 3,
        "why": (
            "untested, and it measures the same risk-appetite axis as S05 with a narrower "
            "currency map, so running it alongside S05 would be two measurements of one thing: "
            "it is the natural declared robustness check for S05 rather than a track of its "
            "own. Its data position is settled and it is bad: the approved probe of 2026-09-20 "
            "timed out on both the BAMLH0A0HYM2 series page and the FRED root, and no free "
            "primary publisher exists because ICE licenses the index. It keeps this rank as "
            "DESIGN_ONLY / NOT_EXECUTED - nothing about the hypothesis was tested, and the "
            "2026-09-14 record of HTTP 200 says the series is served, just not to us"
        ),
    },
    "S16": {
        "name": "rate repricing x volatility threshold effect",
        "old_rank": 9,
        "disposition": DEPENDS_ON_A_CLOSED_BASE,
        "rank": None,
        "why": (
            "declared as an increment of S01 and governed by its own ordering rule - not tested "
            "unless S01's linear baseline is positive. S01's baseline was run twice and was "
            "never positive after cost, and the family is now closed, so the precondition can no "
            "longer be met. Testing it anyway would be a threshold search on a closed family, "
            "which the closure names explicitly"
        ),
    },
    "S08": {
        "name": "rates volatility state x FX",
        "old_rank": 18,
        "disposition": DEPENDS_ON_A_CLOSED_BASE,
        "rank": None,
        "why": "same as S16: an increment of S01, whose base is closed",
    },
    "S17": {
        "name": "cross-asset co-movement on event days as a direction source",
        "old_rank": 15,
        "disposition": DEPENDS_ON_A_CLOSED_BASE,
        "rank": None,
        "why": (
            "an increment of S03 and S04, both of which are now excluded as event filters on a "
            "closed signal. The cross-asset part of it is S05, which is being tested on its own "
            "and on a far longer span"
        ),
    },
    "S28": {
        "name": "market inflation expectation (breakeven) repricing",
        "old_rank": 12,
        "disposition": CLOSED_BY_FAMILY,
        "rank": None,
        "why": (
            "a breakeven is a difference of a nominal and an index-linked public sovereign "
            "yield, and the rule proposed for it is simple directional repricing against "
            "subsequent G10 FX return - which is what the closure covers, by rule. Its own "
            "record already said the largest uncertainty was whether it is independent of S01 "
            "at all. Independently, the breadth is one to two currencies because non-US linker "
            "markets are thin"
        ),
    },
    "S14": {
        "name": "fast / medium / slow price state disagreement",
        "old_rank": 11,
        "disposition": PENALISED,
        "rank": 7,
        "why": (
            "price-only, and the closest thing to it that has been run is Track 1's linear "
            "combination of 5, 20 and 60 day states, which was gross-negative (H-023). H-024 "
            "additionally forbids reviving the 5/20/60 reversal benchmarks. What is left that is "
            "not already closed is narrow"
        ),
    },
    "S15": {
        "name": "volatility / trend regime transition",
        "old_rank": 17,
        "disposition": PENALISED,
        "rank": 8,
        "why": (
            "a conditioning variable, not a return source, by its own record. Conditioning "
            "cannot rescue a base that is not positive, and this programme currently has no "
            "positive base to condition. H-017 is the precedent: volume as a timing filter made "
            "the carry book worse in 15 of 15 cells"
        ),
    },
    "S10": {
        "name": "currency-complex lead-lag propagation",
        "old_rank": 16,
        "disposition": PENALISED,
        "rank": 6,
        "why": (
            "the ruling's section 31 requires showing it is not an H-003 or Track 1 rename, and "
            "its own record already overlaps H-010, H-003 and H-002. Its intraday form turns "
            "over more than 100 round trips a year, which the cost record makes hopeless, and "
            "its data is the seen M15 corpus only - the 4.7-year span that cannot decide"
        ),
    },
    "S12": {
        "name": "correlation breakdown / dispersion relative value",
        "old_rank": 19,
        "disposition": PENALISED,
        "rank": 9,
        "why": (
            "overlaps H-003 and H-024, and its own capacity note already put it structurally "
            "below 2% a year. Nothing in the new evidence raises it"
        ),
    },
    "S25": {
        "name": "central bank balance sheet / reserve flows",
        "old_rank": 7,
        "disposition": PENALISED,
        "rank": 5,
        "why": (
            "untested and free, which is worth something, but monthly. Over the seen corpus that "
            "is about 56 observations, and the ruling's section 22 is explicit that a sample too "
            "small to close a negative is not worth spending an alpha backtest on. It improves a "
            "lot if run over the 1999-2016 span instead, which is why it is ranked rather than "
            "dropped"
        ),
    },
    "S26": {
        "name": "international capital flow (TIC, balance of payments)",
        "old_rank": 8,
        "disposition": PENALISED,
        "rank": 10,
        "why": (
            "genuinely distinct from H-021 - securities flows are not futures speculators - and "
            "free, but monthly with a six-week publication lag, US-centric, and its availability "
            "was never probed. Same power problem as S25 with a heavier acquisition"
        ),
    },
    "S27": {
        "name": "central bank communication tone",
        "old_rank": 14,
        "disposition": PENALISED,
        "rank": 11,
        "why": (
            "the event count is S03's, so it inherits the same power ceiling and the same four "
            "obtainable central banks. Machine acquisition of timestamped historical text was "
            "never verified, and scoring it needs NLP, which section 33 keeps behind a Human "
            "decision. Its increment over the meeting-day repricing was always the question, and "
            "that repricing is now closed"
        ),
    },
    "S20": {
        "name": "FX option risk reversal / implied volatility skew",
        "old_rank": None,
        "disposition": BLOCKED_BY_DATA,
        "rank": None,
        "why": (
            "still the strongest prior among everything unavailable, and still paid. It is "
            "carried in the paid-data assessment rather than the ranking"
        ),
    },
    "S22": {
        "name": "session-to-session cross-market transmission",
        "old_rank": None,
        "disposition": BLOCKED_BY_DATA,
        "rank": None,
        "why": "intraday index futures are paid; the price-only version is C03 and H-002",
    },
    "S18": {
        "name": "retail positioning contrarian",
        "old_rank": None,
        "disposition": BLOCKED_BY_DATA,
        "rank": None,
        "why": "authenticated broker or account data, which is unapproved; no free history exists",
    },
    "S09": {
        "name": "triangular residual",
        "old_rank": None,
        "disposition": STILL_EXCLUDED,
        "rank": None,
        "why": "structurally inside the spread by no-arbitrage; not a rename, an impossibility",
    },
    "S11": {
        "name": "dynamic common factor residual reversal",
        "old_rank": None,
        "disposition": STILL_EXCLUDED,
        "rank": None,
        "why": "a renamed revival of H-024, which is explicitly prohibited from being revived",
    },
    "S19": {
        "name": "COT change x price interaction",
        "old_rank": None,
        "disposition": STILL_EXCLUDED,
        "rank": None,
        "why": "H-021 closed the tested cells; this is the same family under another name",
    },
    "S21": {
        "name": "month-end hedge rebalance flow",
        "old_rank": None,
        "disposition": STILL_EXCLUDED,
        "rank": None,
        "why": "belongs to a family suspended by decision (C04, C05, #475), and 12 events a year",
    },
    "S23": {
        "name": "ex-ante real rate differential level",
        "old_rank": None,
        "disposition": STILL_EXCLUDED,
        "rank": None,
        "why": "a recombination of H-016's carry, which closed as the short-yen trade",
    },
    "S24": {
        "name": "volatility-timed carry",
        "old_rank": None,
        "disposition": STILL_EXCLUDED,
        "rank": None,
        "why": "a volatility filter rescuing a NOT_SUPPORTED carry, which is the rescue shape",
    },
}

#: Where an exclusion rests on the declared closure and where it rests on judgement.
#: The distinction matters because the closure is scope-limited and this module states
#: that it may not be widened by paraphrase - so it may not quietly do the ranking's
#: work either. Only the first two entries below are closure applications.
EXCLUSION_BASIS: Final[dict[str, str]] = {
    "S01": "the closure, directly - it is the measure that was closed",
    "S28": "the closure, by rule - simple directional repricing of a sovereign yield difference",
    "S16": "its own declared ordering rule, whose precondition can no longer be met",
    "S08": "its own declared ordering rule, as S16",
    "S17": "its bases are excluded, and its cross-asset part is S05, which is being tested",
    "S03": "judgement: closed direction source, measured absence of cost advantage, power ceiling",
    "S04": "judgement, as S03, plus no free official timestamped calendar outside the US",
}

#: What the ruling forbids concluding from all of this.
NOT_GENERALISED: Final[tuple[str, ...]] = (
    "rates as a whole are hopeless - only the simple public daily sovereign-yield directional "
    "family is closed, and OIS, the market-implied policy path, rate futures, intraday rate "
    "repricing, curve shape, term premium, rates options and distributional policy-path "
    "information are all untouched",
    "valuation as a whole is hopeless - one spot-only formulation on one span failed",
    "non-price information as a whole is hopeless - most of it has never been acquired",
    "machine learning as a whole is hopeless - no stage 1 has yet produced a base to build on",
    "event information as a whole is hopeless - the opportunity structure is established and "
    "real; what is missing is a direction source that is not already closed",
    "cross-asset as a whole is hopeless - it has never been tested as a directional source",
    "cross-sectional construction as a whole is hopeless - H-023 falsified one linear "
    "architecture, explicitly not FX_HAS_NO_EDGE",
)


def eligible() -> list[tuple[int, str, str]]:
    """The reranked candidates still in the running, best first."""
    rows = [
        (row["rank"], cid, row["name"])
        for cid, row in REASSESSMENT.items()
        if row.get("rank") is not None
    ]
    return sorted(rows)


def removed() -> list[tuple[str, str, str]]:
    """Everything the new evidence takes out of the running, with the reason class."""
    return sorted(
        (cid, row["disposition"], row["name"])
        for cid, row in REASSESSMENT.items()
        if row.get("rank") is None
    )


__all__ = [
    "BLOCKED_BY_DATA",
    "EXCLUSION_BASIS",
    "LONG_DECISION_DAYS",
    "RECENT_DECISION_DAYS",
    "TRADING_DAYS_PER_YEAR",
    "CLOSED_BY_EXECUTION",
    "CLOSED_BY_FAMILY",
    "DEPENDS_ON_A_CLOSED_BASE",
    "EVENT_FILTER_ON_A_CLOSED_SIGNAL",
    "NOT_GENERALISED",
    "PENALISED",
    "PROMOTED",
    "REASSESSMENT",
    "SPANS",
    "STILL_EXCLUDED",
    "detectable_sharpe",
    "eligible",
    "power_at",
    "removed",
]
