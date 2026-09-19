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

**Reachability was measured, not assumed.** FRED, which #484's inventory named as
the source for most cross-asset candidates, is unreachable from this environment:
three attempts, connection reset and timeouts, while the ECB responded normally
throughout. That would have blocked the whole cross-asset direction had the
inventory's source list been taken at face value. It is not blocked, because the
primary publishers serve the same series directly — CBOE for its own index, the
EIA for its own price series — and a primary publisher is a better provenance
than the aggregator anyway.
"""

from __future__ import annotations

import math
from typing import Any, Final

from scripts.research.edge_sources import capacity
from scripts.research.edge_sources.rerank import detectable_sharpe

#: The charged one-way cost convention this programme has used throughout, in basis
#: points of the summed absolute traded delta.
ONE_WAY_BP: Final[float] = 1.703

#: Measured 2026-09-19 by direct request. Recorded because an unreachable source is
#: a finding about the design space, not an accident of the afternoon.
REACHABILITY: Final[dict[str, dict[str, str]]] = {
    "fred.stlouisfed.org": {
        "status": "UNREACHABLE",
        "evidence": "three attempts: one connection reset, two 45s timeouts",
        "consequence": (
            "#484 named FRED as the source for VIX, oil, credit spreads and breakevens. Taking "
            "that list at face value would have retired the entire cross-asset direction on an "
            "environment fault"
        ),
    },
    "cdn.cboe.com": {
        "status": "REACHABLE",
        "evidence": "VIX_History.csv, 200, 9276 daily closes 1990-01-02 onward",
        "consequence": "the volatility series direct from the index provider, better than FRED",
    },
    "www.eia.gov": {
        "status": "REACHABLE",
        "evidence": "RWTCd.xls, 200, the official US crude spot series",
        "consequence": "oil direct from the government publisher",
    },
    "home.treasury.gov": {
        "status": "REACHABLE",
        "evidence": "full daily yield curve including 2Yr and 10Yr, every year probed back to 1995",
        "consequence": "curve shape, not just the closed level, for USD",
    },
    "api.statistiken.bundesbank.de": {
        "status": "REACHABLE",
        "evidence": "10y daily series, 200",
        "consequence": "curve shape for EUR",
    },
    "www.bankofcanada.ca": {
        "status": "REACHABLE",
        "evidence": "Valet 10y benchmark, 200",
        "consequence": "curve shape for CAD",
    },
    "data.snb.ch": {
        "status": "REACHABLE",
        "evidence": "rendoblid cube, 200",
        "consequence": "curve shape for CHF",
    },
    "data-api.ecb.europa.eu": {
        "status": "REACHABLE",
        "evidence": "used throughout T-V",
        "consequence": "the FX span itself",
    },
    "stats.bis.org": {
        "status": "REACHABLE",
        "evidence": "policy rates, DSR and REER all 200",
        "consequence": "slow macro-financial series if wanted later",
    },
    "query1.finance.yahoo.com": {
        "status": "REACHABLE_BUT_NOT_USED",
        "evidence": "v8 chart endpoint 200; the v7 download endpoint now returns 401",
        "consequence": (
            "a redistributor with ambiguous terms for programmatic access and no stable "
            "versioning. The ruling's section 41 puts official and exchange publishers ahead of "
            "it, and both are reachable, so there is no reason to take the licence question on"
        ),
    },
    "dataservices.imf.org": {
        "status": "UNREACHABLE",
        "evidence": "DNS failure",
        "consequence": "not needed by any ranked candidate",
    },
}

#: The FX history a track may be run against. The gap between them is the protected
#: fresh pool and stays shut.
FX_SPANS: Final[dict[str, dict[str, Any]]] = {
    "long": {
        "span": "1999-01-04 .. 2016-06-01",
        "trading_days": 4458,
        "years": 17.41,
        "source": "ECB euro reference rates, acquired for T-V, EXPLORATORY_SEEN_DEVELOPMENT_DATA",
    },
    "recent": {
        "span": "2021-04-27 .. 2025-12-26",
        "trading_days": 1182,
        "years": 4.69,
        "source": "the three guarded OANDA M15 routes, EXPLORATORY_SEEN_DATA",
    },
}
TOTAL_YEARS: Final[float] = FX_SPANS["long"]["years"] + FX_SPANS["recent"]["years"]


def cost_drag(turnover_round_trips: float, vol_per_unit_gross: float) -> float:
    """Information-ratio drag from trading this much, at the charged convention.

    Turnover is round trips a year per unit of currency gross, so the annual cost is
    `2 * turnover * one_way`, and the drag on a Sharpe is that over the volatility a
    unit of gross carries.
    """
    annual_cost = 2.0 * turnover_round_trips * ONE_WAY_BP / 10_000.0
    return annual_cost / vol_per_unit_gross


def required_daily_ic(
    *, turnover_round_trips: float, vol_per_unit_gross: float, breadth: float, target_net: float
) -> float:
    """The daily IC a candidate needs to reach `target_net` after its own cost drag."""
    drag = cost_drag(turnover_round_trips, vol_per_unit_gross)
    half_life = max(252.0 / max(turnover_round_trips, 1e-9) / 2.0, 1.0)
    capture = capacity.band_law(round(half_life))["capture"]
    return (target_net + drag) / (
        capacity.TRANSFER_COEFFICIENT * capture * math.sqrt(breadth * 252.0)
    )


#: A unit of currency gross carried roughly this much annualised volatility in every
#: book this programme has run, across three different signals. Used signal-blind.
VOL_PER_UNIT_GROSS: Final[float] = 0.030

ASSESSMENTS: Final[dict[str, dict[str, Any]]] = {
    "S05": {
        "name": "cross-asset risk repricing -> G10 FX",
        "data": "CBOE VIX daily closes, from the index provider, 1990-01-02 onward",
        "coverage": {
            "total_daily_closes": 9276,
            "inside_the_long_fx_span": 4381,
            "inside_the_recent_fx_span": 1389,
            "alignment": "4381 of the long span's 4458 FX days, and the recent span is covered whole",
        },
        "timing_quality": (
            "a daily close from the index provider, stamped on its own trading day. The FX side "
            "is the ECB 14:15 CET fix on the long span and a UTC daily close on the recent one, "
            "so a US close cannot inform the same day's European fix and the lag must be one "
            "trading day. That is a rule, not an estimate, and it is what the prereg will freeze"
        ),
        "expected_turnover": "20-45 round trips a year on a 5-20 day state, from the band law",
        "breadth": 2.5,
        "sample": "about 5,560 decision days across two disjoint spans",
        "decision_capability": "DECISION_CAPABLE",
        "why": (
            "22.1 traded years separates a net Sharpe of 0.60, which sits under a realistic "
            "0.2-0.5 edge only at the low end rather than hopelessly above it as the 4.7-year "
            "corpus did at 1.29. Better, the two spans are disjoint and a frozen rule can be "
            "required to agree in sign on both - development evidence no track here has had"
        ),
    },
    "S02": {
        "name": "sovereign curve slope / curvature -> G10 FX",
        "data": (
            "the 10-year and 2-year points of each official curve: US Treasury, Bundesbank, "
            "MOF Japan, Bank of Canada, SNB, and the BoE nominal spot curve"
        ),
        "coverage": {
            "us_treasury": "full curve with 2Yr and 10Yr for every year probed back to 1995",
            "bundesbank": "daily 10y series reachable",
            "boc": "Valet 10y benchmark reachable",
            "snb": "curve cube reachable",
            "note": "the 2-year leg is already acquired for T-R; only the long leg is new",
        },
        "timing_quality": (
            "same as T-R's: no publisher states when the day's value becomes available, so the "
            "same conservative one-trading-day lag applies and is frozen"
        ),
        "expected_turnover": "8-18 round trips a year on a 20-60 day state",
        "breadth": 2.5,
        "sample": "about 5,560 decision days across the same two spans, universe permitting",
        "decision_capability": "DECISION_CAPABLE",
        "why": (
            "the ruling's closure explicitly does not reach curve shape, the data is tier-one "
            "official and reaches back past 1999, and the turnover is the lowest of any ranked "
            "candidate. The prior is the weak part, not the feasibility"
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
        "decision_capability": "DECISION_CAPABLE_BUT_NARROW",
        "why": (
            "the span is fine and the data is official, but effective breadth of one and a half "
            "- three commodity currencies against the rest - raises the IC a given net Sharpe "
            "needs by about 30% over S05. It is the natural third track if either of the two "
            "selected ones is blocked, not a reason to run three"
        ),
    },
    "S07": {
        "name": "credit spread / funding stress -> USD, JPY, CHF",
        "data": "ICE BofA high-yield OAS was a FRED series; FRED is unreachable",
        "coverage": {"note": "no primary publisher for this index is free - ICE licenses it"},
        "timing_quality": "not assessed",
        "expected_turnover": "18-43 round trips a year",
        "breadth": 1.5,
        "sample": "not assessed",
        "decision_capability": "DATA_UNAVAILABLE_WITH_CURRENT_FREE_SOURCES",
        "why": (
            "unlike VIX and oil, this index has no free primary publisher to fall back to when "
            "the aggregator is unreachable. It measures the same risk axis as S05 in any case, "
            "so its loss costs the ranking a robustness check rather than a direction"
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
        "decision_capability": "MARGINAL",
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
        "decision_capability": "MARGINAL",
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

SELECTED: Final[dict[str, str]] = {
    "track_a": "S05",
    "track_b": "S02",
    "why_only_two": (
        "the ruling allows at most two and does not require two. S06 would be a third and its "
        "narrow breadth makes it the weakest of the three; S07 lost its data. Two is what the "
        "evidence supports"
    ),
    "why_these_two": (
        "they are the only ranked candidates that are simultaneously decision-capable on a long "
        "span, served by a free primary publisher that answers, and outside every closed family. "
        "They are also independent of each other in information: one is an external asset's "
        "repricing, the other is the shape of a rate curve, and neither needs the other's result "
        "to be frozen"
    ),
}


def summary() -> dict[str, Any]:
    return {
        "total_years_available": round(TOTAL_YEARS, 2),
        "detectable_net_sharpe_at_80pct_power": round(detectable_sharpe(TOTAL_YEARS), 2),
        "reachable": sorted(h for h, r in REACHABILITY.items() if r["status"] == "REACHABLE"),
        "unreachable": sorted(h for h, r in REACHABILITY.items() if r["status"] == "UNREACHABLE"),
        "decision_capable": sorted(
            cid
            for cid, a in ASSESSMENTS.items()
            if a["decision_capability"].startswith("DECISION_CAPABLE")
        ),
        "selected": dict(SELECTED),
    }


__all__ = [
    "ASSESSMENTS",
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
