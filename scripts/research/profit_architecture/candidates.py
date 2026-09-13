"""Twenty profit architectures, assessed on declared structural fields.

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`.

Each candidate is a different **profit-generation structure** — where the money
would come from, mechanically — not an indicator variant. Per the instruction,
each carries three frequencies stated separately (prediction, position update,
traded turnover), a capital-utilization figure, the economics implied by the
mechanics module, its overlap with the closed families, the evidence against
it, and declared burden scores.

Nothing here is a realised quantity. The expected-turnover figures come from
the signal-free mechanics simulations **where the basis field says so and are
declared judgments where it says that** — a first draft blurred the two; the
required-edge figures are arithmetic over the measured constants; the scores are
judgments, encoded transparently so a reviewer can attack them line by line.

⭐ The closed-family guard is **self-certified**: `assert_prospective` fires only
for a candidate that declares `gate_family`, and none of the twenty does — each
adjacency call is prose, argued in `prior_overlap` and attackable there. A test
exercises the mechanism with a synthetic declaring candidate so the guard cannot
rot, but no test can decide an adjacency judgment; the reviews decided the three
contested ones (A11/A06 redrawn on the instrument axis, A18 held adjacent and
unrun, A01 required to face C08 at prereg time).

Roles matter more than ranks
----------------------------

The catalogue separates four roles, because they are not competitors:

* **core** — holds the book and earns the base P&L;
* **overlay** — modulates the core's exposure or composition;
* **efficiency** — reduces cost or risk without forecasting returns;
* **evaluation** — buys uncontaminated evidence rather than P&L.

A ranking that mixed them would pit a cost-reduction layer against an alpha
engine, which is a category error the track selection below avoids by picking
at most one candidate per role.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Final

from scripts.research.feasibility import RetroactiveApplicationError, assert_prospective
from scripts.research.profit_architecture import (
    BASKET_ROUNDTRIP_BP,
    EFFECTIVE_CURRENCY_BREADTH_PER_DAY,
    TRADING_DAYS_PER_YEAR,
)
from scripts.research.profit_architecture.mechanics import ir_drag, required_gross_ir

#: Capacity classes per the instruction's §26 — explicit, not a threshold game.
CAPACITY_UNDER_2PCT: Final[str] = "structurally_under_2pct"
CAPACITY_2_TO_5PCT: Final[str] = "2_to_5pct_in_reach"
CAPACITY_5_TO_10PCT: Final[str] = "5_to_10pct_in_reach"
CAPACITY_ENABLER: Final[str] = "enabler_not_a_return_source"


@dataclass(frozen=True, slots=True)
class Architecture:
    """One profit architecture, declared in full."""

    candidate_id: str
    role: str
    mechanism: str
    edge_source: str
    target: str
    horizon: str
    #: The three frequencies the instruction requires be stated separately.
    prediction_frequency_per_year: float
    position_update_frequency_per_year: float
    expected_annual_turnover: float
    turnover_basis: str
    capital_utilization: str
    effective_breadth_per_day: float
    prior_overlap: str
    evidence_against: str
    expected_information_gain: str
    capacity_class: str
    #: Declared judgment scores, 0-3 each, attackable line by line.
    edge_plausibility: int
    robustness: int
    complexity_burden: int
    overfit_risk: int
    engineering_burden: int
    #: A closed adjudicated family this would reopen, when it would.
    gate_family: str | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


def _economics(architecture: Architecture) -> dict[str, Any]:
    """Required edge for 5% and 10% annual at a 10% vol target, from mechanics."""
    breadth_per_year = architecture.effective_breadth_per_day * TRADING_DAYS_PER_YEAR
    if architecture.capacity_class == CAPACITY_ENABLER:
        return {
            "ir_drag": round(ir_drag(architecture.expected_annual_turnover), 3),
            "note": "an enabler is judged by what it saves or protects, not by a return",
        }
    rows = {}
    for label, net in (("net_5pct_at_10vol", 0.5), ("net_10pct_at_10vol", 1.0)):
        gross = required_gross_ir(net, architecture.expected_annual_turnover)
        rows[label] = {
            "required_net_sharpe": net,
            "required_gross_ir": round(gross, 3),
            "required_daily_ic": round(gross / math.sqrt(breadth_per_year), 4),
        }
    return {
        "annual_cost_bp": round(architecture.expected_annual_turnover * BASKET_ROUNDTRIP_BP, 1),
        "ir_drag": round(ir_drag(architecture.expected_annual_turnover), 3),
        **rows,
    }


def catalogue() -> list[Architecture]:
    """Twenty structures. The first block is the continuum the instruction centres."""
    return [
        Architecture(
            candidate_id="A01_continuous_currency_portfolio",
            role="core",
            mechanism=(
                "estimate a continuous expected relative return per G10 currency, map "
                "to factor-neutral target weights, rebalance only the daily difference"
            ),
            edge_source="small persistent cross-sectional predictability, harvested wide",
            target="8-currency expected-return vector",
            horizon="1-10 days of target persistence, daily updates",
            prediction_frequency_per_year=252.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=34.5,
            turnover_basis="mechanics: 20d-half-life targets, daily update, no band",
            capital_utilization="~100% invested, gross ~ vol target / 3.78%",
            effective_breadth_per_day=EFFECTIVE_CURRENCY_BREADTH_PER_DAY,
            prior_overlap=(
                "the decision-grade inventory closed C08 — CURRENCY-level rank "
                "persistence — under the H-003 same-shape family, enforced by "
                "assert_prospective; a first draft called the closure pair-level only. "
                "What survives is multi-feature conditional estimation in which "
                "currency strength is one input the model may weight to zero, not the "
                "hypothesis that strength persists; any prereg for this track has to "
                "draw that line against C08 explicitly. The model-learning Track A ran "
                "one non-evidence development pass of a special case"
            ),
            evidence_against=(
                "no decision-grade evidence FOR it either: every prior test that could "
                "have seen a gross IR of 0.6-0.8 lacked the power to. The one "
                "development observation is contaminated, uncounted — and failed its "
                "own pre-registered rule: top-ten-day share 3.05, JPY +493 bp of a "
                "+92 bp book, 2 of 6 folds negative, net -0.08 at the 2x cost stress. "
                "The concentration shape is the H-016 short-yen recurrence, and it "
                "already trips the kill rule this track declares"
            ),
            expected_information_gain=(
                "whether the only unexcluded regime — small edge x full utilization x "
                "currency breadth x low realised turnover — exists at all"
            ),
            capacity_class=CAPACITY_5_TO_10PCT,
            edge_plausibility=2,
            robustness=2,
            complexity_burden=1,
            overfit_risk=2,
            engineering_burden=1,
        ),
        Architecture(
            candidate_id="A02_no_trade_band_rebalancing",
            role="efficiency",
            mechanism=(
                "hold the core's target but trade only when |target - held| exceeds a "
                "band; hysteresis converts prediction churn into zero trades"
            ),
            edge_source="none — it deletes cost rather than adding return",
            target="the core's own targets, executed lazily",
            horizon="same as the core",
            prediction_frequency_per_year=252.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=14.4,
            turnover_basis="mechanics: band 0.10 on 20d-half-life targets (34.5 -> 14.4)",
            capital_utilization="unchanged from the core",
            effective_breadth_per_day=EFFECTIVE_CURRENCY_BREADTH_PER_DAY,
            prior_overlap=(
                "NOT Track 3: that closed near-touch passive fills, which try to earn "
                "the spread. This avoids paying it by not trading, which Track 3's "
                "closure explicitly does not cover"
            ),
            evidence_against=(
                "a band leaves a mean tracking gap of 0.29 gross, and the gap is not "
                "free: the measured alpha capture of the banded book is 0.958 against "
                "a 20d target — about 4.2% of gross IR forfeited. A first draft said "
                "the gap costs nothing and called that measured; the capture ratio is "
                "now actually computed, and it is what the required-IC figures charge"
            ),
            expected_information_gain=(
                "IR drag 0.331 -> 0.130 at band 0.10; net of the 4.2% capture cost the "
                "saving is ~0.16 of gross IR, with no forecast required"
            ),
            capacity_class=CAPACITY_ENABLER,
            edge_plausibility=3,
            robustness=3,
            complexity_burden=0,
            overfit_risk=0,
            engineering_burden=0,
        ),
        Architecture(
            candidate_id="A03_multi_horizon_blend",
            role="core",
            mechanism=(
                "slow (D1+, half-life ~60d) plus medium (H4-D1) plus small fast "
                "components emit weight vectors; the position is their sum, so a fast "
                "disagreement trims the core instead of reversing it"
            ),
            edge_source="partially independent predictability at separated horizons",
            target="per-horizon currency weight vectors, blended",
            horizon="three, blended",
            prediction_frequency_per_year=252.0 * 3,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=27.7,
            turnover_basis="mechanics: 60d core + 20% fast share (19.9 -> 27.7)",
            capital_utilization="~100% invested",
            effective_breadth_per_day=EFFECTIVE_CURRENCY_BREADTH_PER_DAY * 1.5,
            prior_overlap=(
                "simple HTF sign conditioning is closed; this never gates on a sign — "
                "horizons contribute additively"
            ),
            evidence_against=(
                "horizon components may be too correlated to add breadth; the 1.5x "
                "breadth factor is an assumption and is flagged as one"
            ),
            expected_information_gain="whether horizon is a real breadth dimension",
            capacity_class=CAPACITY_5_TO_10PCT,
            edge_plausibility=2,
            robustness=2,
            complexity_burden=2,
            overfit_risk=2,
            engineering_burden=2,
        ),
        Architecture(
            candidate_id="A04_core_plus_event_overlay",
            role="overlay",
            mechanism=(
                "a persistent core book; scheduled central-bank events and volatility "
                "states scale exposure, concentration and rebalance timing — never "
                "direction"
            ),
            edge_source=(
                "the measured event structure: matched movement 1.58-1.63x on "
                "forward-known days with no cost disadvantage"
            ),
            target="exposure multiplier and rebalance schedule",
            horizon="event windows over a continuous core",
            prediction_frequency_per_year=40.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=5.0,
            turnover_basis="declared judgment: incremental gross scaling, not repositioning",
            capital_utilization="modulates the core's, does not idle it",
            #: ~40 forward-known decisions a year, one occasion each: 0.16/day,
            #: not the 0.5 a first draft declared against its own event count.
            effective_breadth_per_day=0.16,
            prior_overlap=(
                "H-018/H-019 are OPEN: 'an anchor with nothing to point it at'. This "
                "points it at exposure, which needs no direction"
            ),
            evidence_against=(
                "vol-scaling a mean-zero book earns nothing; the overlay only monetises "
                "if the core has edge, so it inherits the core's uncertainty"
            ),
            expected_information_gain="whether the one robust event finding is worth money",
            capacity_class=CAPACITY_2_TO_5PCT,
            edge_plausibility=2,
            robustness=2,
            complexity_burden=1,
            overfit_risk=1,
            engineering_burden=1,
        ),
        Architecture(
            candidate_id="A05_residual_factor_neutral_book",
            role="core",
            mechanism=(
                "project out dollar/risk/commodity factors and trade only the residual "
                "currency vector, so the book carries no common-factor exposure"
            ),
            edge_source="mean reversion / structure in the residual cross-section",
            target="residual expected-return vector",
            horizon="days",
            prediction_frequency_per_year=252.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=40.0,
            turnover_basis=(
                "declared judgment between the mechanics 10d row (48.0) and the 20d "
                "row (34.5): residual targets persist less than raw ones"
            ),
            capital_utilization="~100%",
            effective_breadth_per_day=3.0,
            prior_overlap="H-003 closed the PAIR-level version that was 96% common factor",
            evidence_against=(
                "the residual is the 4% H-003 left; its dispersion is small, so the "
                "same IC buys less gross return per unit of gross exposure"
            ),
            expected_information_gain="whether the non-factor cross-section is priced at all",
            capacity_class=CAPACITY_2_TO_5PCT,
            edge_plausibility=1,
            robustness=2,
            complexity_burden=2,
            overfit_risk=2,
            engineering_burden=1,
        ),
        Architecture(
            candidate_id="A06_cross_asset_repricing",
            role="core",
            mechanism=(
                "map same-day changes in yields, curves, equities and commodities to "
                "next-days currency expected returns — FX as the lagging repricer"
            ),
            edge_source="cross-asset lead-lag into FX",
            target="currency expected-return vector from external state",
            horizon="1-5 days",
            prediction_frequency_per_year=252.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=48.0,
            turnover_basis="mechanics: 10d-half-life targets",
            capital_utilization="~100%",
            effective_breadth_per_day=EFFECTIVE_CURRENCY_BREADTH_PER_DAY,
            prior_overlap=(
                "the closed carry search (H-016) tested BIS policy rates at LEVEL and "
                "CHANGE — carry_change reversed sign between panels at every frequency, "
                "which is adjacent adverse evidence for any rates input here. What was "
                "never acquired or tested is MARKET-traded yields and curve slopes; the "
                "boundary is the instrument, not level-versus-change"
            ),
            evidence_against=(
                "free daily cross-asset data is end-of-day and partially stale; the "
                "lead may live inside the day and be gone by the close"
            ),
            expected_information_gain="the only major information family never opened",
            capacity_class=CAPACITY_5_TO_10PCT,
            edge_plausibility=2,
            robustness=1,
            complexity_burden=2,
            overfit_risk=2,
            engineering_burden=2,
        ),
        Architecture(
            candidate_id="A07_regime_adaptive_exposure",
            role="overlay",
            mechanism=(
                "a regime state scales gross exposure, horizon mix and turnover budget "
                "— strategy selector, never a direction source"
            ),
            edge_source="conditional Sharpe differences across volatility regimes",
            target="exposure and blend multipliers",
            horizon="weeks",
            prediction_frequency_per_year=52.0,
            position_update_frequency_per_year=52.0,
            expected_annual_turnover=4.0,
            turnover_basis="incremental: scaling, not repositioning",
            capital_utilization="modulates the core's",
            effective_breadth_per_day=0.3,
            prior_overlap=(
                "simple HTF sign conditioning closed; the model-learning run showed a "
                "pure gain on a normalised book is a no-op, so this must act on GROSS "
                "exposure, which that run never tested"
            ),
            evidence_against=(
                "H-002: every conditional gate lowered net; regime edges have not "
                "replicated anywhere in this programme"
            ),
            expected_information_gain="whether regime information prices exposure",
            capacity_class=CAPACITY_2_TO_5PCT,
            edge_plausibility=1,
            robustness=1,
            complexity_burden=1,
            overfit_risk=2,
            engineering_burden=1,
        ),
        Architecture(
            candidate_id="A08_execution_vehicle_optimization",
            role="efficiency",
            mechanism=(
                "given a currency delta, choose WHICH pairs implement it at minimum "
                "spread — the 1.32 basket factor is an average, not a floor"
            ),
            edge_source="none — routing, not forecasting",
            target="pair decomposition of the net currency delta",
            horizon="per rebalance",
            prediction_frequency_per_year=0.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=0.0,
            turnover_basis="changes cost per unit turnover, not turnover",
            capital_utilization="unchanged",
            effective_breadth_per_day=0.0,
            prior_overlap="none — no phase optimised the vehicle",
            evidence_against=(
                "the measured rows price every pair at the average 2.58 bp round trip; "
                "minimum-notional routing leans on wider-spread crosses, so the "
                "realisable saving sits below the notional floor"
            ),
            expected_information_gain=(
                "measured, not guessed: the corpus's own equal-split netting already "
                "pays 1.99 bp per turnover unit against the 3.406 charged (factor "
                "1.71), and the minimum-notional floor is 1.43 (factor 2.38) — a first "
                "draft said 'perhaps 10-20%', understating its own audit"
            ),
            capacity_class=CAPACITY_ENABLER,
            edge_plausibility=3,
            robustness=3,
            complexity_burden=1,
            overfit_risk=0,
            engineering_burden=1,
        ),
        Architecture(
            candidate_id="A09_sparse_high_confidence_overlay",
            role="overlay",
            mechanism=(
                "on top of a persistent book, take concentrated positions only at "
                "extreme signal states; the base book keeps capital utilised between"
            ),
            edge_source="convexity of edge in signal strength, if it exists",
            target="occasional concentrated tilts",
            horizon="days, sparse",
            prediction_frequency_per_year=252.0,
            position_update_frequency_per_year=20.0,
            expected_annual_turnover=8.0,
            turnover_basis="sparse tilts on top of the core",
            capital_utilization="core solves the idle-capital problem; overlay adds tilt",
            effective_breadth_per_day=0.5,
            prior_overlap="H-014's only surviving population was ~6-9 events/pair/year",
            evidence_against=(
                "H-014's tail concentration and bloc reversal are exactly what a "
                "sparse concentrated book maximises exposure to"
            ),
            expected_information_gain="whether edge is convex in signal strength",
            capacity_class=CAPACITY_2_TO_5PCT,
            edge_plausibility=1,
            robustness=1,
            complexity_burden=1,
            overfit_risk=3,
            engineering_burden=1,
        ),
        Architecture(
            candidate_id="A10_turnover_penalized_optimizer",
            role="efficiency",
            mechanism=(
                "portfolio construction with an explicit transaction-cost term: "
                "maximise mu'w - lambda w'Sigma w - c|dw| instead of tracking targets"
            ),
            edge_source="none — spends the cost budget where the forecast is strongest",
            target="cost-aware weights",
            horizon="same as core",
            prediction_frequency_per_year=252.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=20.0,
            turnover_basis="between band-0.05 and band-0.10 mechanics, forecast-aware",
            capital_utilization="unchanged",
            effective_breadth_per_day=EFFECTIVE_CURRENCY_BREADTH_PER_DAY,
            prior_overlap="none",
            evidence_against=(
                "optimizers manufacture apparent edge from covariance estimation error; "
                "must be compared against the plain band, which is nearly free"
            ),
            expected_information_gain="a principled band; marginal over A02",
            capacity_class=CAPACITY_ENABLER,
            edge_plausibility=2,
            robustness=2,
            complexity_burden=2,
            overfit_risk=2,
            engineering_burden=2,
        ),
        Architecture(
            candidate_id="A11_yield_change_slow_component",
            role="core",
            mechanism=(
                "a slow currency tilt from yield CHANGES and curve repricing — the "
                "information carry-level tests never used — held for weeks"
            ),
            edge_source="delayed FX response to rate repricing",
            target="slow currency tilt vector",
            horizon="weeks",
            prediction_frequency_per_year=52.0,
            position_update_frequency_per_year=52.0,
            expected_annual_turnover=12.0,
            turnover_basis=(
                "declared judgment below the mechanics 60d daily row (20.2): weekly "
                "updates of a slow target trade less than daily ones, but no run in "
                "the mechanics module updates weekly and this figure is not from one"
            ),
            capital_utilization="~100%",
            effective_breadth_per_day=2.0,
            prior_overlap=(
                "the closed family (H-016) tested BIS policy rates at LEVEL and CHANGE "
                "both — a first draft claimed changes were untested, which the ledger "
                "contradicts, and carry_change reversed sign between panels at every "
                "frequency. The untested instrument is MARKET yields and curve "
                "repricing, and that is the only axis this candidate may claim"
            ),
            evidence_against=(
                "H-016's carry was a short-yen trade in disguise; any rates-based tilt "
                "must prove it is not the same concentration again"
            ),
            expected_information_gain="whether rate REPRICING, not level, prices FX",
            capacity_class=CAPACITY_2_TO_5PCT,
            edge_plausibility=2,
            robustness=2,
            complexity_burden=1,
            overfit_risk=1,
            engineering_burden=1,
        ),
        Architecture(
            candidate_id="A12_dispersion_relative_value",
            role="core",
            mechanism=(
                "trade the cross-sectional dispersion state itself: widen the book "
                "when dispersion is stretched, compress when it is tight"
            ),
            edge_source="mean reversion of cross-sectional dispersion",
            target="book width, plus which currencies stretched it",
            horizon="days-weeks",
            prediction_frequency_per_year=252.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=30.0,
            turnover_basis=(
                "declared judgment near the mechanics 20d row (34.5); not itself a simulated point"
            ),
            capital_utilization="~100%",
            effective_breadth_per_day=1.0,
            prior_overlap="none directly; adjacent to closed retrace geometry",
            evidence_against=(
                "H-013 showed the retrace family's positives were selection artefacts; "
                "dispersion reversion needs a null that hard to beat"
            ),
            expected_information_gain="a second-moment edge with first-moment payoff",
            capacity_class=CAPACITY_UNDER_2PCT,
            edge_plausibility=1,
            robustness=1,
            complexity_burden=2,
            overfit_risk=2,
            engineering_burden=1,
        ),
        Architecture(
            candidate_id="A13_event_portfolio_tilt",
            role="overlay",
            mechanism=(
                "around scheduled decisions, tilt the book's composition toward or "
                "away from the announcing currency — concentration timing, not "
                "direction prediction"
            ),
            edge_source="event-window risk premia, if any",
            target="temporary concentration changes",
            horizon="1-3 days around ~40 events/year",
            prediction_frequency_per_year=40.0,
            position_update_frequency_per_year=40.0,
            expected_annual_turnover=6.0,
            turnover_basis="small tilts, few events",
            capital_utilization="modulates the core's",
            effective_breadth_per_day=0.3,
            prior_overlap="H-019 open; USD-pooled consensus surprise closed",
            evidence_against=(
                "H-020 dropped the only directional event test on a sign reversal; "
                "a tilt without direction is exposure timing, already in A04"
            ),
            expected_information_gain="mostly duplicated by A04",
            capacity_class=CAPACITY_UNDER_2PCT,
            edge_plausibility=1,
            robustness=1,
            complexity_burden=1,
            overfit_risk=2,
            engineering_burden=1,
        ),
        Architecture(
            candidate_id="A14_volatility_conditioned_leverage",
            role="efficiency",
            mechanism=(
                "vol targeting as a dynamic: scale gross down when realised vol rises, "
                "up when it falls — stabilises realised Sharpe and drawdown"
            ),
            edge_source="none directly; improves the Sharpe->return translation",
            target="gross exposure path",
            horizon="continuous",
            prediction_frequency_per_year=252.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=6.0,
            turnover_basis="scaling turnover only",
            capital_utilization="stabilised at target",
            effective_breadth_per_day=0.0,
            prior_overlap="H-015/H-017: volume and vol forecast realised vol well",
            evidence_against=(
                "vol targeting adds no expected return to a mean-zero book; it is risk "
                "plumbing, and is costed as such"
            ),
            expected_information_gain="required plumbing for any leverage claim",
            capacity_class=CAPACITY_ENABLER,
            edge_plausibility=3,
            robustness=3,
            complexity_burden=0,
            overfit_risk=0,
            engineering_burden=0,
        ),
        Architecture(
            candidate_id="A15_horizon_ensemble_ml",
            role="core",
            mechanism=(
                "small models per horizon; a meta-layer sets blend weights by state — "
                "ML allocates across horizons rather than predicting direction"
            ),
            edge_source="time-varying relative value of horizons",
            target="blend weights over horizon components",
            horizon="ensemble",
            prediction_frequency_per_year=252.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=35.0,
            turnover_basis="close to A03 plus blend churn",
            capital_utilization="~100%",
            effective_breadth_per_day=EFFECTIVE_CURRENCY_BREADTH_PER_DAY * 1.5,
            prior_overlap="capacity budgets bound the meta-layer like everything else",
            evidence_against=(
                "a meta-layer on 4.7 seen years is exactly where the capacity budget "
                "said overfitting lives; needs A03 to work first"
            ),
            expected_information_gain="only meaningful after A03 exists",
            capacity_class=CAPACITY_5_TO_10PCT,
            edge_plausibility=1,
            robustness=1,
            complexity_burden=3,
            overfit_risk=3,
            engineering_burden=2,
        ),
        Architecture(
            candidate_id="A16_mr_timed_rebalancing",
            role="efficiency",
            mechanism=(
                "the book's rebalance trades execute WITH the measured short-horizon "
                "mean reversion: buy the currency that just underperformed intraday "
                "when the target already says buy — timing trades that happen anyway"
            ),
            edge_source=(
                "H-010's VR<1 is real; the 6-16%-of-break-even figure attached to it is "
                "the ledger's POST HOC, IN-SAMPLE best linear predictor — an optimistic "
                "bound, not a harvest. A rebalance pays no incremental cost, so whatever "
                "fraction survives out of sample would be saving rather than strategy; "
                "that transfer is an assumption until measured"
            ),
            target="execution timing of required deltas",
            horizon="hours",
            prediction_frequency_per_year=252.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=0.0,
            turnover_basis="retimes existing turnover; adds none",
            capital_utilization="unchanged",
            effective_breadth_per_day=0.0,
            prior_overlap=(
                "<=12h linear path harvesting is closed AS A STANDALONE — it could not "
                "pay full costs. Costless retiming of forced trades is outside that "
                "closure and is the one use H-010's magnitude supports"
            ),
            evidence_against=(
                "the harvestable fraction of 6-16% of one round trip per retimed trade "
                "is small in absolute bp; worth having, not worth building first"
            ),
            expected_information_gain="turns a 'real but unharvestable' finding into bp",
            capacity_class=CAPACITY_ENABLER,
            edge_plausibility=2,
            robustness=2,
            complexity_burden=1,
            overfit_risk=1,
            engineering_burden=1,
        ),
        Architecture(
            candidate_id="A17_session_aware_scheduling",
            role="efficiency",
            mechanism=(
                "schedule rebalances into the cheapest liquidity windows; the measured "
                "spread surface varies by session (Sunday ~2.5 pips vs weekday ~1.5)"
            ),
            edge_source="none — cost surface navigation",
            target="when in the day the deltas trade",
            horizon="intraday scheduling",
            prediction_frequency_per_year=0.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=0.0,
            turnover_basis="retimes turnover",
            capital_utilization="unchanged",
            effective_breadth_per_day=0.0,
            prior_overlap="the session spread structure is measured in H-018's correction",
            evidence_against="the saving is bounded by intra-day spread dispersion; modest",
            expected_information_gain="a few percent off realised cost, nearly free",
            capacity_class=CAPACITY_ENABLER,
            edge_plausibility=3,
            robustness=3,
            complexity_burden=0,
            overfit_risk=0,
            engineering_burden=0,
        ),
        Architecture(
            candidate_id="A18_weekly_currency_trend",
            role="core",
            mechanism=(
                "continuous cross-sectionally-demeaned currency momentum at 1-4 week "
                "horizons — between the closed multi-day family and closed monthly "
                "TSMOM, at the currency level with continuous weights"
            ),
            edge_source="medium-term currency trend, if any survives demeaning",
            target="slow tilt vector",
            horizon="1-4 weeks",
            prediction_frequency_per_year=52.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=20.0,
            turnover_basis="mechanics: 60d-half-life-equivalent persistence",
            capital_utilization="~100%",
            effective_breadth_per_day=3.0,
            prior_overlap=(
                "the 4-6d reversal/momentum family is closed; C08 closed currency-level "
                "rank persistence; H-012 closed monthly TSMOM as underpowered. The "
                "weekly continuous version sits between three closures, carries that "
                "adjacency as its main risk, and per the working rules a run of it "
                "would need a new instruction — no round licenses the next one"
            ),
            evidence_against=(
                "three spans of the multi-day family produced nothing separable from "
                "noise in either direction; adjacency is real even if the design is not "
                "identical"
            ),
            expected_information_gain="low — the neighbourhood is heavily surveyed",
            capacity_class=CAPACITY_2_TO_5PCT,
            edge_plausibility=1,
            robustness=1,
            complexity_burden=1,
            overfit_risk=2,
            engineering_burden=1,
        ),
        Architecture(
            candidate_id="A19_drawdown_governed_meta_risk",
            role="efficiency",
            mechanism=(
                "a meta-layer that de-risks on drawdown and re-risks on recovery, with "
                "declared thresholds — bounds the left tail the leverage tables assume"
            ),
            edge_source="none; protects the translation from Sharpe to return",
            target="risk multiplier path",
            horizon="continuous",
            prediction_frequency_per_year=252.0,
            position_update_frequency_per_year=252.0,
            expected_annual_turnover=3.0,
            turnover_basis="rare scaling events",
            capital_utilization="reduced only in drawdown",
            effective_breadth_per_day=0.0,
            prior_overlap="none",
            evidence_against=(
                "drawdown control lowers realised Sharpe slightly in exchange for tail "
                "control; it is insurance, priced as such"
            ),
            expected_information_gain="required for any deployment conversation",
            capacity_class=CAPACITY_ENABLER,
            edge_plausibility=3,
            robustness=3,
            complexity_burden=0,
            overfit_risk=1,
            engineering_burden=0,
        ),
        Architecture(
            candidate_id="A20_paper_forward_evaluation",
            role="evaluation",
            mechanism=(
                "freeze candidates and run them on the live OANDA paper stack the "
                "programme already built — every forward month is uncontaminated "
                "evaluation data that no seen-data reuse can produce"
            ),
            edge_source="none — it buys evidence, which is the scarcest input",
            target="frozen candidates, evaluated forward",
            horizon="years, accumulating",
            prediction_frequency_per_year=0.0,
            position_update_frequency_per_year=0.0,
            expected_annual_turnover=0.0,
            turnover_basis="paper",
            capital_utilization="none — no capital at risk",
            effective_breadth_per_day=0.0,
            prior_overlap="the M9/M10 paper infrastructure exists and is idle",
            evidence_against=(
                "slow by construction: at true net IR 0.5, even fresh pool + 3 paper "
                "years reaches only 40% one-shot power — it narrows uncertainty, it "
                "does not deliver proof on any near horizon"
            ),
            expected_information_gain=(
                "the only route to uncontaminated evidence that does not spend the fresh pool"
            ),
            capacity_class=CAPACITY_ENABLER,
            edge_plausibility=3,
            robustness=3,
            complexity_burden=1,
            overfit_risk=0,
            engineering_burden=1,
        ),
    ]


def assess_all() -> list[dict[str, Any]]:
    records = []
    for architecture in catalogue():
        record = asdict(architecture)
        record["notes"] = list(architecture.notes)
        if architecture.gate_family:
            try:
                assert_prospective(architecture.gate_family)
            except RetroactiveApplicationError as refusal:
                record["verdict"] = "PRIOR_FAMILY_CLOSED"
                record["reason"] = str(refusal)
                records.append(record)
                continue
        record["economics"] = _economics(architecture)
        record["score"] = score(architecture)
        records.append(record)
    return records


#: Ranking weights, declared once. The instruction's §44 objective, encoded as a
#: transparent linear score over the declared judgment fields — a judgment made
#: attackable, not a measurement.
SCORE_WEIGHTS: Final[dict[str, int]] = {
    "edge_plausibility": 3,
    "robustness": 2,
    "capacity": 3,
    "complexity_burden": -2,
    "overfit_risk": -2,
    "engineering_burden": -1,
}

_CAPACITY_POINTS: Final[dict[str, int]] = {
    CAPACITY_UNDER_2PCT: 0,
    CAPACITY_2_TO_5PCT: 1,
    CAPACITY_5_TO_10PCT: 2,
    CAPACITY_ENABLER: 1,
}


def score(architecture: Architecture) -> int:
    return (
        SCORE_WEIGHTS["edge_plausibility"] * architecture.edge_plausibility
        + SCORE_WEIGHTS["robustness"] * architecture.robustness
        + SCORE_WEIGHTS["capacity"] * _CAPACITY_POINTS[architecture.capacity_class]
        + SCORE_WEIGHTS["complexity_burden"] * architecture.complexity_burden
        + SCORE_WEIGHTS["overfit_risk"] * architecture.overfit_risk
        + SCORE_WEIGHTS["engineering_burden"] * architecture.engineering_burden
    )


def ranking() -> list[dict[str, Any]]:
    rows = [
        {
            "candidate_id": record["candidate_id"],
            "role": record["role"],
            "capacity_class": record["capacity_class"],
            "score": record["score"],
        }
        for record in assess_all()
        if "score" in record
    ]
    rows.sort(key=lambda row: (-row["score"], row["candidate_id"]))
    for position, row in enumerate(rows, start=1):
        row["rank"] = position
    return rows


#: Efficiency candidates at or above this score are one engineering track, not
#: competitors: a band, a vol target, a drawdown governor and cheap scheduling
#: compose, and every one of them is signal-free and testable without an alpha.
EFFICIENCY_BUNDLE_SCORE_FLOOR: Final[int] = 15


def selected_tracks() -> dict[str, Any]:
    """Three tracks: the best core, the efficiency bundle, the best overlay.

    Roles are not competitors, so the selection is per role rather than a single
    top-3 cut: a core without an efficiency layer pays avoidable cost, two cores
    compete for the same capital, and an overlay without a core has nothing to
    modulate. The efficiency role enters as a **bundle** — its members compose
    and are individually near-free — with the bundle membership set by a
    declared score floor. Evaluation (paper-forward) is recommended for every
    frozen candidate rather than occupying a slot.
    """
    rows = ranking()
    best_by_role: dict[str, dict[str, Any]] = {}
    for row in rows:
        best_by_role.setdefault(row["role"], row)
    bundle = [
        row["candidate_id"]
        for row in rows
        if row["role"] == "efficiency" and row["score"] >= EFFICIENCY_BUNDLE_SCORE_FLOOR
    ]
    deferred = [
        row["candidate_id"]
        for row in rows
        if row["role"] == "efficiency" and row["score"] < EFFICIENCY_BUNDLE_SCORE_FLOOR
    ]
    return {
        "track_1_core": best_by_role["core"],
        "track_2_efficiency_bundle": {
            "members": bundle,
            "score_floor": EFFICIENCY_BUNDLE_SCORE_FLOOR,
            "deferred_members": deferred,
            "why_a_bundle": (
                "the members compose, are signal-free, and are testable without any "
                "alpha existing; ranking them against a core is a category error"
            ),
        },
        "track_3_overlay": best_by_role["overlay"],
        "core_extension_when_track_1_stands": "A03_multi_horizon_blend",
        "paper_forward_recommended_for_all": True,
    }


__all__ = [
    "CAPACITY_2_TO_5PCT",
    "CAPACITY_5_TO_10PCT",
    "CAPACITY_ENABLER",
    "CAPACITY_UNDER_2PCT",
    "EFFICIENCY_BUNDLE_SCORE_FLOOR",
    "SCORE_WEIGHTS",
    "Architecture",
    "assess_all",
    "catalogue",
    "ranking",
    "score",
    "selected_tracks",
]
