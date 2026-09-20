# ruff: noqa: E501 -- feasibility prose
"""Signal-blind feasibility for the reranked top candidates. No alpha is looked at.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Authority: the Human + ChatGPT ruling of 2026-09-19, sections 19-22.

Everything here is computable before a single signal value is formed: what data
exists, how far back, how often it is stamped, how much a book of that cadence
would trade, what that costs, what Sharpe the span can separate from zero, and
what annual return the result could support. A candidate that cannot clear these
does not get an alpha backtest, because a test that can neither establish nor
close a hypothesis is worse than not running it — that is the lesson the ledger
records at H-005, H-012, H-020 and H-021.

**Reachability is the weakest part of this record, and it is flagged rather than
relied on.** This round made its own in-session requests and reported FRED
unreachable (three attempts) while CBOE, the EIA, Treasury, the Bundesbank, the
BoC and the SNB answered. **None of that went through the gated probe route and
none of it produced an artefact**, and the repo's committed probe of 2026-09-14
(`artifacts/research/edge_sources/public_data_availability.json`, written by
`scripts/research/public_data_probe/availability_check.py`) disagrees on **two**:
all seventeen FRED series at HTTP 200 - including the `BAMLH0A0HYM2` high-yield
OAS an earlier draft retired S07 for losing - and a 404 where this round found the
Treasury curve.

The Bundesbank and SNB rows are **not** contradictions, and an earlier version of
this module wrongly called them that. Those endpoints failed TLS certificate
verification in the probe, and the artefact's own note says such failures are
"unverified-from-this-environment, not unavailable" - a local trust-store problem,
not a statement about the publisher. One record reporting reachable and one
declining to say is `UNVERIFIED`, not `CONFLICTED`.

Two unreproduced observations five days apart do not settle each other, so this
module records the conflict instead of picking a winner. `REACHABILITY` below is
marked `UNRESOLVED_CONFLICTS_WITH_COMMITTED_PROBE` wherever the two disagree, no
candidate is retired on it, and the probe script is opt-in gated
(`EDGE_SOURCES_PROBE_APPROVED=1`) with "do not re-run without approval" in its own
docstring - so resolving this needs a human, not another session's afternoon.
"""

from __future__ import annotations

from typing import Any, Final

from scripts.research.continuous_portfolio import CHARGED_ONE_WAY_BP
from scripts.research.edge_sources import capacity
from scripts.research.edge_sources.rerank import (
    LONG_DECISION_DAYS,
    RECENT_DECISION_DAYS,
    TRADING_DAYS_PER_YEAR,
    detectable_sharpe,
    power_at,
)

#: The charged one-way cost convention, taken from the derived constant rather than
#: retyped. An earlier draft hard-coded 1.703 here and a mutation test then showed
#: that a stray 17.03 in this file changed every published number while the suite
#: stayed green.
ONE_WAY_BP: Final[float] = CHARGED_ONE_WAY_BP

#: Measured 2026-09-19 by direct request. Recorded because an unreachable source is
#: a finding about the design space, not an accident of the afternoon.
#: Status vocabulary for a host. The point of the third value is that this round's
#: observations were not reproducible, so a disagreement is recorded as a
#: disagreement rather than resolved by recency.
REACHABLE: Final[str] = "REACHABLE"
UNREACHABLE: Final[str] = "UNREACHABLE"
#: The two records say opposite things about the same observation.
CONFLICTED: Final[str] = "UNRESOLVED_CONFLICTS_WITH_COMMITTED_PROBE"
#: One record says reachable and the other declines to say. The committed probe's own
#: note reads "SSL/403 failures are unverified-from-this-environment, not unavailable",
#: so a TLS failure there is NOT evidence of unavailability and must not be cited as a
#: contradiction. An earlier version of this table called two such hosts CONFLICTED.
UNVERIFIED: Final[str] = "UNVERIFIED_NEITHER_RECORD_ESTABLISHES_AVAILABILITY"
#: Reachable on this round's ungated, artefact-free requests, and not covered by the
#: committed probe at all. Absence of contradiction is not corroboration, so this is a
#: weaker claim than REACHABLE and may not be leaned on.
THIS_ROUND_ONLY: Final[str] = "REPORTED_REACHABLE_THIS_ROUND_ONLY_NO_ARTEFACT"

#: `this_round` is what in-session requests reported on 2026-09-19 through an
#: ungated route that wrote no artefact. `committed_probe` is what
#: artifacts/research/edge_sources/public_data_availability.json records for
#: 2026-09-14, written by the opt-in-gated probe script. Where they differ, `status`
#: is CONFLICTED and nothing downstream may be decided on it.
REACHABILITY: Final[dict[str, dict[str, str]]] = {
    "fred.stlouisfed.org": {
        "status": CONFLICTED,
        "this_round": "UNREACHABLE - three attempts: one connection reset, two 45s timeouts",
        "committed_probe": "all 17 series HTTP 200, including BAMLH0A0HYM2, VIXCLS and DGS2/DGS10",
        "consequence": (
            "an earlier draft retired S07 on the unreachable reading. It may not be: the only "
            "recorded measurement of that exact series says 200. S07's data position is "
            "UNRESOLVED until the gated probe is re-run under approval"
        ),
    },
    "api.statistiken.bundesbank.de": {
        "status": UNVERIFIED,
        "this_round": "REACHABLE - 10y daily series, 200",
        "committed_probe": (
            "SSL: CERTIFICATE_VERIFY_FAILED, unable to get local issuer certificate - which "
            "that artefact's own note says is 'unverified-from-this-environment, not "
            "unavailable'. It is a local trust-store failure, not a contradiction"
        ),
        "consequence": (
            "the EUR long leg S02 needs is not established as obtainable - by one unreproduced "
            "report and one record that declines to say"
        ),
    },
    "data.snb.ch": {
        "status": UNVERIFIED,
        "this_round": "REACHABLE - rendoblid cube, 200",
        "committed_probe": (
            "SSL: CERTIFICATE_VERIFY_FAILED - the same local trust-store failure, which the "
            "artefact's note explicitly declines to read as unavailability"
        ),
        "consequence": "the CHF long leg is not established as obtainable, for the same reason",
    },
    "home.treasury.gov": {
        "status": CONFLICTED,
        "this_round": "REACHABLE - full daily curve, every year probed back to 1995",
        "committed_probe": (
            "HTTP 404 on the interest-rates resource centre page - a real status code, not a "
            "transport failure, so unlike the TLS rows this one is a genuine disagreement"
        ),
        "consequence": (
            "plausibly two different URLs rather than a real disagreement, but neither "
            "observation is reproducible from the record, so it is recorded as a conflict"
        ),
    },
    "cdn.cboe.com": {
        "status": THIS_ROUND_ONLY,
        "this_round": "REACHABLE - VIX_History.csv, 200",
        "committed_probe": "not in the probe's endpoint list",
        "consequence": (
            "the volatility series direct from the index provider. The 1990-01-02 start is "
            "independently corroborated by the committed probe's FRED VIXCLS declared range; "
            "the close COUNT this round reported is not corroborated by anything and is not "
            "used below"
        ),
    },
    "www.eia.gov": {
        "status": THIS_ROUND_ONLY,
        "this_round": "REACHABLE - RWTCd.xls, 200, the official US crude spot series",
        "committed_probe": "not in the probe's endpoint list",
        "consequence": (
            "oil direct from the government publisher, on this round's evidence alone. The "
            "series start an earlier draft gave as 1986 is not supported by anything in this "
            "repo: the only corroborated crude range is FRED's DCOILBRENTEU from 1987-05-20"
        ),
    },
    "www.bankofcanada.ca": {
        "status": REACHABLE,
        "this_round": "REACHABLE - Valet 10y benchmark, 200",
        "committed_probe": "Valet 2y series metadata, HTTP 200 - agrees",
        "consequence": "curve shape for CAD; the one long leg both records agree on",
    },
    "data-api.ecb.europa.eu": {
        "status": REACHABLE,
        "this_round": "REACHABLE - used throughout T-V",
        "committed_probe": (
            "a different host (data.ecb.europa.eu) failed TLS there; this one carried the whole "
            "T-V acquisition, which is the stronger evidence"
        ),
        "consequence": "the FX span itself",
    },
    "stats.bis.org": {
        "status": THIS_ROUND_ONLY,
        "this_round": "REACHABLE - policy rates, DSR and REER all 200",
        "committed_probe": "not in the probe's endpoint list; BIS was acquired successfully in T-V",
        "consequence": "slow macro-financial series if wanted later",
    },
    "query1.finance.yahoo.com": {
        "status": "REACHABLE_BUT_NOT_USED",
        "this_round": "v8 chart endpoint 200; the v7 download endpoint returns 401",
        "committed_probe": "not in the probe's endpoint list",
        "consequence": (
            "a redistributor with ambiguous terms for programmatic access and no stable "
            "versioning. The ruling's section 41 puts official and exchange publishers ahead of "
            "it, so there is no reason to take the licence question on"
        ),
    },
    "dataservices.imf.org": {
        "status": UNREACHABLE,
        "this_round": "UNREACHABLE - DNS failure",
        "committed_probe": "not in the probe's endpoint list",
        "consequence": "not needed by any ranked candidate",
    },
}

#: The FX history a track would be run against, if a read of it were authorised.
#: The gap between them is the protected fresh pool and stays shut.
#: Day counts come from committed records and years are days / 252 for both, so the
#: two spans sit on one basis. An earlier draft paired a counted calendar year for
#: the long span with a derived 252-day year for the recent one, and gave the recent
#: span 1182 days where `market_yields.prereg.DECISION_DAYS` records 1213.
FX_SPANS: Final[dict[str, dict[str, Any]]] = {
    "long": {
        "span": "1999-01-04 .. 2016-06-01",
        "trading_days": LONG_DECISION_DAYS,
        "years": round(LONG_DECISION_DAYS / TRADING_DAYS_PER_YEAR, 2),
        "days_provenance": "return_panel_days in artifacts/research/valuation/development.json",
        "source": "ECB euro reference rates, acquired for T-V, EXPLORATORY_SEEN_DEVELOPMENT_DATA",
    },
    "recent": {
        "span": "2021-04-27 .. 2025-12-26",
        "trading_days": RECENT_DECISION_DAYS,
        "years": round(RECENT_DECISION_DAYS / TRADING_DAYS_PER_YEAR, 2),
        "days_provenance": "DECISION_DAYS in scripts/research/market_yields/prereg.py",
        "source": "the three guarded OANDA M15 routes, EXPLORATORY_SEEN_DATA",
    },
}
TOTAL_YEARS: Final[float] = round(
    (LONG_DECISION_DAYS + RECENT_DECISION_DAYS) / TRADING_DAYS_PER_YEAR, 2
)

#: Seen-ness is not permission. Both spans were read under their own recorded acts;
#: running a new track against either is a fresh real-data read and needs its own
#: explicit human + ChatGPT authorisation naming operation, span, pairs, timeframe
#: and approved head. Nothing in this module supplies that.
RE_READ_REQUIRES: Final[str] = "EXPLICIT_HUMAN_AND_CHATGPT_AUTHORISATION_PER_READ"


def cost_drag(turnover_round_trips: float, vol_per_unit_gross: float | None = None) -> float:
    """Information-ratio drag from trading this much, at the charged convention.

    Turnover is round trips a year per unit of currency gross, so the annual cost is
    `2 * turnover * one_way`, and the drag on a Sharpe is that over the volatility a
    unit of gross carries.
    """
    if vol_per_unit_gross is None:
        vol_per_unit_gross = VOL_PER_UNIT_GROSS
    if turnover_round_trips < 0.0:
        raise ValueError("turnover cannot be negative")
    if vol_per_unit_gross <= 0.0:
        raise ValueError("a unit of gross must carry positive volatility")
    annual_cost = 2.0 * turnover_round_trips * ONE_WAY_BP / 10_000.0
    return annual_cost / vol_per_unit_gross


def required_daily_ic(*, half_life_days: float, breadth: float, target_net: float) -> float:
    """The daily IC a candidate needs to reach `target_net` after its own cost drag.

    Parameterised by half-life, not by turnover, because the band law maps one to
    the other and an earlier draft inverted it: it took `252 / turnover / 2`, which
    calls 8 round trips a year a 15.8-day book when `band_law(16)` itself says a
    16-day book turns over 21.1. Drag and capture were then read off two different
    books. This delegates to `capacity`, so there is one band law and one cost
    convention in the package rather than a second copy here.
    """
    return capacity.required_daily_ic(target_net, half_life_days, breadth)


def turnover_for(half_life_days: float) -> float:
    """Round trips a year for a book of this half-life, from the committed band law."""
    return capacity.band_law(half_life_days)["turnover"]


#: A unit of currency gross carries this much annualised volatility. Taken from
#: `capacity`, which derives it from a committed Track 1 record and re-derives it in
#: a test, rather than restated here. An earlier draft used 0.030 and described it as
#: "observed in every book this programme has run"; the four measured values are
#: 0.023288 (Track 1), 0.0261 (T-R2), 0.0324 (T-V) and 0.0257-0.0264 (T-R), so 0.030
#: was the top of the range, not its centre. Because drag = cost / vol, that
#: understated the hurdle by about 29% - in the flattering direction, on the one axis
#: that has decided every verdict in this programme so far.
VOL_PER_UNIT_GROSS: Final[float] = capacity.VOL_PER_UNIT_GROSS

#: The cost convention is a MEASUREMENT FROM ONE SPAN APPLIED TO BOTH, and that is an
#: assumption, not a fact. 1.703 bp is Track 3's measured OANDA round trip over
#: 2021-2025. The long span is ECB euro reference rates: a single daily fix with no
#: bid/ask at all, whose G10 crosses are triangulated from two EUR fixes. Whatever the
#: real 1999-2016 cost of trading G10 spot was, it is not this number, and a pooled
#: "net Sharpe over 22.5 years" therefore mixes one measured cost regime with one
#: assumed one - on the axis that has decided every verdict in this programme so far.
#: A pre-registration must either state a long-span cost assumption and stress it, or
#: report the two spans' net results separately. It may not quietly pool them.
COST_CONVENTION_IS_SPAN_LOCAL: Final[str] = (
    "CHARGED_COST_MEASURED_ON_2021_2025_OANDA_NOT_ESTABLISHED_FOR_THE_1999_2016_SPAN"
)

#: What the other books measured, kept so the choice above is visible and auditable.
VOL_PER_UNIT_GROSS_MEASURED: Final[dict[str, float]] = {
    "track_1_continuous_portfolio": 0.023288,
    "track_r2_slow_repricing": 0.026103,
    "track_v_valuation": 0.032375,
}

#: Decision-capability vocabulary. An earlier draft had only DECISION_CAPABLE and
#: stamped it on S05 and S02 — which does not survive the module's own criterion.
#: That criterion is "a span whose detectable Sharpe sits above a realistic 0.2-0.5
#: edge cannot decide it", and 22.5 years detects 0.59, so it fails the test it was
#: written to apply. Computed power over the pooled span is 0.16 / 0.30 / 0.66 at
#: true Sharpes of 0.2 / 0.3 / 0.5, and capacity.sample_years_needed(0.3, 0.8) is
#: 87.2 years two-sided - 68.7 on the one-sided convention `capacity` uses, and both
#: several times any span available. So the best available verdict is the one below,
#: and it is not a pass.
BEST_AVAILABLE_BUT_UNDERPOWERED: Final[str] = (
    "BEST_AVAILABLE_SPAN_STILL_UNDERPOWERED_FOR_A_REALISTIC_EDGE"
)
NARROW: Final[str] = "AS_ABOVE_AND_BREADTH_LIMITED"
DATA_UNRESOLVED: Final[str] = "DATA_POSITION_UNRESOLVED_PENDING_AN_APPROVED_PROBE_RE_RUN"
MARGINAL: Final[str] = "MARGINAL_MONTHLY_SAMPLING_CANNOT_CLOSE_A_NEGATIVE"

#: What the committed gate says about the same design space, re-run rather than
#: cited from memory. `scripts/research/feasibility/inventory.py` already carries
#: this round's power constant as `power_multiplier = 2.8016`. Re-assessed at a
#: 22.5-year panel, the cross-asset and curve plans (C10, C09, C11) stay
#: NO_DECISION_GRADE_PASS_REGION and their binding constraint moves from `horizon`
#: to `economic_net_under_stress` — a constraint length of span does not relieve.
#: Two event plans (C01, C05) do reach PASS_REGION_EXISTS at that panel length.
#: The C-identifiers are not a clean one-to-one map onto the S-identifiers here
#: (C10 is a conditioning hypothesis where S05 is a directional one, and C09 is the
#: yield-differential level that T-R already closed), so this is recorded as an
#: unreconciled tension for the pre-registration to resolve, not as a verdict.
COMMITTED_GATE_AT_THE_POOLED_PANEL: Final[dict[str, str]] = {
    "C01_central_bank_decision_response": "PASS_REGION_EXISTS (binding: economic_net_under_stress)",
    "C05_month_end_rebalancing_flow": "PASS_REGION_EXISTS (binding: event_floor)",
    "C09_yield_differential_change": "NO_DECISION_GRADE_PASS_REGION (binding: economic_net_under_stress)",
    "C10_equity_risk_regime_conditioning": "NO_DECISION_GRADE_PASS_REGION (binding: economic_net_under_stress)",
    "C11_commodity_link_response": "NO_DECISION_GRADE_PASS_REGION (binding: economic_net_under_stress)",
    "what_it_means": (
        "span was never the binding constraint for the two candidates selected here. This "
        "module's thesis is that span reorders the inventory; the committed gate says that for "
        "these plans the cost margin under stress does, and that margin does not move with "
        "panel length. The tension is real and is not resolved in this document"
    ),
}

ASSESSMENTS: Final[dict[str, dict[str, Any]]] = {
    "S05": {
        "name": "cross-asset risk repricing -> G10 FX",
        "data": "CBOE VIX daily closes, from the index provider, 1990-01-02 onward",
        "coverage": {
            "withdrawn": (
                "this round reported 9,276 total closes, 4,381 inside the long FX span and "
                "1,389 inside the recent one. The last is arithmetically impossible: "
                "2021-04-27 .. 2025-12-26 contains 1,219 weekdays, so a daily series cannot "
                "hold 1,389 observations in it, and the same dict recorded 1,213 decision days "
                "for the span. The count is consistent with an upper bound that was never "
                "applied - counting to the request date instead of the span end, across the "
                "calendar of the fresh pool, the OOS slice and the forward epoch. VIX is not "
                "protected data so no read boundary was crossed, but the numbers are wrong and "
                "none of the three was reproducible from any artefact, so all three are "
                "withdrawn rather than repaired"
            ),
            "what_stands": (
                "the 1990-01-02 series start, which the committed probe corroborates "
                "independently through FRED's declared range for VIXCLS"
            ),
            "what_the_prereg_must_establish": (
                "the actual overlap, counted inside an explicit upper bound, through an "
                "authorised acquisition route"
            ),
        },
        "timing_quality": (
            "a daily close from the index provider, stamped on its own trading day. The FX side "
            "is the ECB 14:15 CET fix on the long span and a UTC daily close on the recent one, "
            "so a US close cannot inform the same day's European fix and the lag must be one "
            "trading day. That is a rule, not an estimate, and it is what the prereg will freeze"
        ),
        "expected_turnover": "20-45 round trips a year on a 5-20 day state, from the band law",
        "breadth": 2.5,
        "sample": "5,671 decision days across two disjoint spans (4,458 + 1,213)",
        "decision_capability": BEST_AVAILABLE_BUT_UNDERPOWERED,
        "why": (
            "22.5 traded years separates a net Sharpe of 0.59 against 1.28 on the recent "
            "corpus alone, which is the largest power gain available to any candidate here - "
            "and still short of deciding a realistic 0.2-0.5 edge, at power 0.30 for a true "
            "0.3. What it adds beyond power is that the two spans are disjoint, so a frozen "
            "rule can be required to agree in sign on both. That is a period-robustness check "
            "no track here has had, and under the null a pre-specified direction passes it "
            "with probability 0.25, so it is a screen and not a test"
        ),
    },
    "S02": {
        "name": "sovereign curve slope / curvature -> G10 FX",
        "data": (
            "the 10-year and 2-year points of each official curve: US Treasury, Bundesbank, "
            "MOF Japan, Bank of Canada, SNB, and the BoE nominal spot curve"
        ),
        "coverage": {
            "us_treasury": "this round reported the full curve back to 1995; the committed probe recorded 404",
            "bundesbank": "this round reported the daily 10y series reachable; the committed probe recorded a TLS failure",
            "boc": "Valet 10y benchmark - the one leg both records agree answers",
            "snb": "this round reported the curve cube reachable; the committed probe recorded a TLS failure",
            "note": (
                "the 2-year leg is already acquired for T-R, so only the long leg is new - and "
                "three of its four publishers are CONFLICTED between the two records. The long "
                "leg is NOT established as obtainable"
            ),
        },
        "timing_quality": (
            "same as T-R's: no publisher states when the day's value becomes available, so the "
            "same conservative one-trading-day lag applies and is frozen"
        ),
        "expected_turnover": "8-18 round trips a year on a 20-60 day state",
        "breadth": 2.5,
        "sample": "5,671 decision days across the same two spans, universe permitting",
        "decision_capability": BEST_AVAILABLE_BUT_UNDERPOWERED,
        "why": (
            "the ruling's closure explicitly does not reach curve shape, the publishers are "
            "tier-one official, and the turnover is the lowest of any ranked candidate. Both "
            "the prior and the data position are weak: the prior because the level of this same "
            "information set failed twice, the data because the long leg's availability is "
            "unresolved between two unreproduced observations"
        ),
    },
    "S06": {
        "name": "commodity terms of trade -> commodity currencies",
        "data": "EIA official US crude spot series, reachable",
        "coverage": {"note": "daily from 1986; not probed day by day because it is not being run"},
        "timing_quality": "daily official publication, same one-day lag rule",
        "expected_turnover": "18-43 round trips a year",
        "breadth": 1.5,
        "sample": "as S05",
        "decision_capability": NARROW,
        "why": (
            "the span is fine and the data is official, but effective breadth of one and a half "
            "- three commodity currencies against the rest - raises the IC a given net Sharpe "
            "needs by about 30% over S05. It is the natural third track if either of the two "
            "selected ones is blocked, not a reason to run three"
        ),
    },
    "S07": {
        "name": "credit spread / funding stress -> USD, JPY, CHF",
        "data": (
            "ICE BofA high-yield OAS (BAMLH0A0HYM2) is a FRED series. This round reported FRED "
            "unreachable; the committed probe of 2026-09-14 records that exact series at HTTP 200"
        ),
        "coverage": {
            "note": (
                "no free PRIMARY publisher exists for this index - ICE licenses it - so the "
                "aggregator is the only free route and its status is CONFLICTED. An earlier "
                "draft retired the candidate on the unreachable reading alone"
            )
        },
        "timing_quality": "not assessed",
        "expected_turnover": "18-43 round trips a year",
        "breadth": 1.5,
        "sample": "not assessed",
        "decision_capability": DATA_UNRESOLVED,
        "why": (
            "unlike VIX and oil, this index has no free primary publisher to fall back to if "
            "the aggregator really is unreachable - which is why its data position turns "
            "entirely on a conflict this document cannot resolve. It measures the same risk "
            "axis as S05 in any case, so it is the declared robustness check for S05 rather "
            "than a direction of its own, and nothing here needs it decided today"
        ),
    },
    "S25": {
        "name": "central bank balance sheet / reserve flows",
        "data": "central bank publications, monthly to weekly",
        "coverage": {"note": "monthly over the long span is about 209 observations"},
        "timing_quality": "publication lags vary by bank and were never verified",
        "expected_turnover": "low",
        "breadth": 2.0,
        "sample": "about 209 monthly decisions on the long span, 56 on the recent one",
        "decision_capability": MARGINAL,
        "why": (
            "monthly sampling over the long span is workable, but the recent span alone gives "
            "56 observations, which cannot close a negative. It is ranked, not selected"
        ),
    },
    "S26": {
        "name": "international capital flow (TIC)",
        "data": "US Treasury TIC, monthly, about six weeks of publication lag",
        "coverage": {
            "note": "availability never probed; not probed here either, since it is not selected"
        },
        "timing_quality": "the six-week lag is the dominant design constraint and is knowable",
        "expected_turnover": "5-8 round trips a year",
        "breadth": 2.5,
        "sample": "monthly",
        "decision_capability": MARGINAL,
        "why": "same monthly power ceiling as S25, with a heavier acquisition and a US-centric view",
    },
}

#: Paid data, assessed by design only. Nothing is bought, and nothing here is a request.
PAID_DATA: Final[tuple[dict[str, Any], ...]] = (
    {
        "id": "S20",
        "what": "G10 FX option 25-delta risk reversals and implied volatility skew, daily",
        "provider": "Bloomberg, Refinitiv, or CME for its own listed options",
        "rough_cost": (
            "a Bloomberg or Refinitiv terminal is of the order of USD 20-30k a year; CME "
            "historical option data is sold per dataset, of the order of USD 1-5k for a "
            "multi-year FX option history. Both are order-of-magnitude figures from public "
            "price lists, not quotes, and neither was solicited"
        ),
        "coverage": "major pairs, generally 2000s onward; the long 1999 span is unlikely",
        "hypothesis_enabled": (
            "the risk reversal is the market's own price for asymmetry - what it costs to insure "
            "against a currency falling versus rising. That is a directional expectation "
            "expressed in a price, from an instrument this programme has never observed, and it "
            "is not derivable from spot. It is the only candidate whose signal is a market's "
            "explicit forward-looking view rather than a statistic computed from history"
        ),
        "why_public_substitute_insufficient": (
            "nothing free prices FX optionality. Realised skew from spot is a backward-looking "
            "statistic and is exactly the kind of price-derived quantity this programme has "
            "already closed several times"
        ),
        "expected_information_gain": (
            "high, and unusually so: it is the highest prior among everything unavailable, and a "
            "negative result would close a genuinely distinct information set rather than one "
            "more formulation"
        ),
    },
    {
        "id": "rates-implied",
        "what": "OIS curves and short rate futures histories for G10",
        "provider": "Bloomberg, Refinitiv, or the exchanges for their own contracts",
        "rough_cost": "terminal-class, or per-dataset from the exchanges; not solicited",
        "coverage": "generally 2000s onward for OIS across G10",
        "hypothesis_enabled": (
            "the market-implied policy path, which the 2026-09-19 closure explicitly leaves "
            "open. The closed family used the realised two-year yield; OIS prices the expected "
            "path directly and separates it from term premium"
        ),
        "why_public_substitute_insufficient": (
            "the two-year sovereign yield is the free proxy, and it is the thing that just "
            "closed. There is no free OIS history for G10"
        ),
        "expected_information_gain": (
            "moderate. It would put the rate direction back in play on a cleaner instrument, "
            "but the closed family's failure was monetisability at realistic cost, and OIS does "
            "not obviously change the turnover or the cost"
        ),
    },
    {
        "id": "S22",
        "what": "intraday index futures",
        "provider": "the exchanges, or a vendor",
        "rough_cost": "per-dataset from the exchanges, moderate; not solicited",
        "coverage": "deep, but intraday",
        "hypothesis_enabled": "session-to-session cross-market transmission",
        "why_public_substitute_insufficient": "the price-only version is C03 and H-002, both closed",
        "expected_information_gain": (
            "low relative to cost. The intraday horizon carries the turnover this programme has "
            "repeatedly found fatal, and the cost record argues against it before the data does"
        ),
    },
)

#: Named LEAD and SECOND rather than "Track A" and "Track B". In this repository
#: Track A is Exploratory and Track B is Formal Confirmation - one frozen candidate
#: run once on UNSEEN forward data - and both spans here are already seen. Neither
#: of these can ever be a Formal Confirmation, and an earlier draft's "Track B" for
#: S02 read as though one could.
SELECTED: Final[dict[str, str]] = {
    "lead": "S05",
    "second": "S02",
    "both_are": "EXPLORATORY_ON_SEEN_DATA_NEITHER_IS_A_FORMAL_CONFIRMATION",
    "why_only_two": (
        "the ruling allows at most two and does not require two. S06 would be a third and its "
        "narrow breadth makes it the weakest of the three; S07's data position is unresolved. "
        "Two is what the evidence supports"
    ),
    "why_these_two": (
        "among ranked candidates these two sit furthest from a closed family while reaching the "
        "longest span available, and they are independent of each other in information - an "
        "external asset's repricing against the shape of a rate curve - so neither needs the "
        "other's result to be frozen"
    ),
    "what_this_selection_is_not": (
        "it is not a finding that either can be decided. Both carry "
        "BEST_AVAILABLE_SPAN_STILL_UNDERPOWERED_FOR_A_REALISTIC_EDGE, S02's long data leg is "
        "not established as obtainable, and the committed gate re-run at this panel length "
        "keeps the comparable plans at NO_DECISION_GRADE_PASS_REGION on a cost constraint that "
        "span does not relieve. Pre-registering either means pre-registering a test that is "
        "likely to return UNRESOLVED, which is a choice a human should make knowingly"
    ),
}


def summary() -> dict[str, Any]:
    return {
        "total_years_available": round(TOTAL_YEARS, 2),
        "detectable_net_sharpe_at_80pct_power": round(detectable_sharpe(TOTAL_YEARS), 2),
        "power_at_true_sharpe": {
            f"{sr}": round(power_at(sr, TOTAL_YEARS), 2) for sr in (0.2, 0.3, 0.5)
        },
        "reachable": sorted(h for h, r in REACHABILITY.items() if r["status"] == REACHABLE),
        "reported_this_round_only": sorted(
            h for h, r in REACHABILITY.items() if r["status"] == THIS_ROUND_ONLY
        ),
        "unverified": sorted(h for h, r in REACHABILITY.items() if r["status"] == UNVERIFIED),
        "unreachable": sorted(h for h, r in REACHABILITY.items() if r["status"] == UNREACHABLE),
        "conflicted": sorted(h for h, r in REACHABILITY.items() if r["status"] == CONFLICTED),
        "best_available": sorted(
            cid
            for cid, a in ASSESSMENTS.items()
            if a["decision_capability"] == BEST_AVAILABLE_BUT_UNDERPOWERED
        ),
        "none_are_decision_capable": (
            "no candidate reaches a span that can decide a realistic 0.2-0.5 edge; the best "
            "available is 22.5 years at power 0.30 for a true 0.3"
        ),
        "selected": dict(SELECTED),
    }


__all__ = [
    "ASSESSMENTS",
    "BEST_AVAILABLE_BUT_UNDERPOWERED",
    "COMMITTED_GATE_AT_THE_POOLED_PANEL",
    "CONFLICTED",
    "DATA_UNRESOLVED",
    "MARGINAL",
    "NARROW",
    "REACHABLE",
    "RE_READ_REQUIRES",
    "THIS_ROUND_ONLY",
    "UNREACHABLE",
    "UNVERIFIED",
    "COST_CONVENTION_IS_SPAN_LOCAL",
    "VOL_PER_UNIT_GROSS_MEASURED",
    "turnover_for",
    "FX_SPANS",
    "ONE_WAY_BP",
    "PAID_DATA",
    "REACHABILITY",
    "SELECTED",
    "TOTAL_YEARS",
    "VOL_PER_UNIT_GROSS",
    "cost_drag",
    "required_daily_ic",
    "summary",
]
