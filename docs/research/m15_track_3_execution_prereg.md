# Track 3 — offline execution frontier: pre-registration

`NON_DECISION_BEARING_EXPLORATORY_ONLY` · `RESEARCH_SCRATCH_NON_AUTHORITATIVE`
· `PRODUCTION_READINESS_NOT_CLAIMED`

Status at the time of writing: **`TRACK_3_PREREGISTERED_NOT_YET_EXECUTED`**.

This document is frozen **before** any execution measurement exists. Its commit
precedes the commit that produces `artifacts/research/execution_frontier/`, and
that ordering is the freeze: every rule, constant, cost definition and success
band below was fixed without a result to fit it to.

Authorised by the Human + ChatGPT sequencing decision that followed the unit
audit (PR #474, merged at `5231efe`), which ruled Track 3 ahead of Track 1 and
restricted it to **offline historical replay on already-seen data**.

---

## 1. The question

> Under realistic passive or improved execution, how far can the round-trip
> retail cost hurdle be lowered on the two deciding panels?

This is **not** alpha discovery. No signal is used anywhere in Track 3: trade
directions are drawn from a generator, so there is no signal-to-return relation
to find and no result that could be read as an edge. What is measured is a
property of *execution*, and its output is an input to the feasibility frontier.

## 2. What is authorised, and what is not

Authorised: offline historical replay over the two already-seen deciding panels,
`momentum_2021_2023` and `supplemental_2023_2025`.

Not authorised and not performed: OANDA login, any broker-authenticated
endpoint, demo execution, paper order submission, live execution, real orders,
production deployment. Also not authorised: the fresh pool
`2016-06-02 … 2021-04-25`, the historical OOS slice, the dead window, the
forward Formal Confirmation epoch, any paid data acquisition, and any M1
re-aggregation.

## 3. The unit

Basis points of the mid price at the moment of the decision, per observation,
through `scripts.research.fxunits`. Never pips, never a return fraction, never a
panel-wide conversion constant. `verify_unit_consistency` walks the finished
artifact and the run fails if a numeric field escaped conversion.

## 4. Cost definitions

Every leg is scored as **implementation shortfall** against the mid at the
moment the design says to trade:

    leg cost (bp) = direction * (fill price - decision mid) / decision mid * 1e4

with `direction = +1` for a buy and `-1` for a sell. A round trip is the entry
leg plus the exit leg, the exit taken in the opposite direction.

Shortfall is used rather than "half the quoted spread" because a passive order
does not transact at the moment of the decision. The delay is part of what
passive execution costs, and a metric that priced only the spread would credit
the saving and hide the drift.

**`C`** — baseline. Market order, executed immediately at the decision bar's own
quote: buy at `ask`, sell at `bid`, plus a slippage pad of
`SLIPPAGE_PAD_PIPS / 2 = 0.25` pip per leg, which keeps the round trip equal to
the `spread + 0.5 pip` convention every earlier stage of this programme used.

**`C'`** — simulated passive execution, policy **P2 (passive-then-cross)**: rest
a limit at the near touch for `WAIT_BARS` bars; if it has not filled, cross with
a market order. Every decision therefore results in a trade, so `C'` is a mean
over the **same population** as `C` and the comparison carries no selection.

**`C'_passive_only`** — policy **P1 (passive-only)**: rest the same limit and
cancel if unfilled. Reported as a **diagnostic only**. Its mean is conditional
on having filled, and a passive order fills precisely when the market came to
it, so this number is selected and is *not* the band metric. It is reported
beside its fill rate so the selection is visible rather than implied.

## 5. The fill rule — fixed here, before any measurement

Governing principle: **claim only what the available data can prove.** The bars
are M15 with per-side OHLC. There is no tick path, no depth, no queue.

1. **No touch-only fills.** A limit at `L` fills only if the opposing side
   traded strictly **through** it by at least `PENETRATION_PIPS`: for a buy,
   `min(ask_low) <= L - PENETRATION_PIPS * pip`; for a sell,
   `max(bid_high) >= L + PENETRATION_PIPS * pip`. Touching `L` is scored as no
   fill.
2. **No queue priority.** Penetration is the proxy for the queue at `L` having
   been consumed. Nothing assumes a place in it.
3. **No price improvement.** A fill is at `L` exactly, never better, even when
   the bar traded far through it.
4. **No favourable latency.** An order decided at a bar's *close* is live only
   from the next bar. An order decided at a bar's *open* is live during that bar,
   which uses no information from inside it.
5. **Same-bar ambiguity resolves against the order.** Where a bar's OHLC is
   consistent with both a fill and no fill — the touch case, and any ordering
   question inside a bar — the outcome is no fill.
6. **No fills across a gap.** Every bar from the decision to the crossing bar
   must be contiguous at 15 minutes. An order does not rest through a weekend or
   a session break; such an observation is dropped as unmeasurable, not scored.
7. **No partial-fill optimism.** All or nothing at full size. A partially filled
   order is not modelled as a proportional saving.
8. **Rollover excluded.** Decisions inside the 21:55–22:15 UTC rollover window
   are excluded from the primary population and reported separately.

### Fixed constants

| constant | value | why |
| --- | --- | --- |
| `WAIT_BARS` | 4 (one hour) | The window length every clock cell already uses. |
| `PENETRATION_PIPS` | 1.0 | One pip through the limit, not a touch. |
| `SLIPPAGE_PAD_PIPS` | 0.5 per round trip | Unchanged from every prior stage. |
| `DRIFT_BARS` | 4 (one hour) | Horizon for post-fill adverse movement. |

Declared **in advance** as sensitivities, to be reported whatever they show and
never substituted for the primary: `WAIT_BARS` in {1, 2, 4, 8} and
`PENETRATION_PIPS` in {0.5, 1.0, 2.0}. The primary cell is `(4, 1.0)`.

## 6. What is measured

Per panel, per population: baseline `C`, simulated `C'`, `C'/C`, spread capture,
fill opportunity rate, missed-trade rate, adverse price movement after a
hypothetical fill, and the distribution of each across pairs, sessions,
event/non-event and rollover. Two-panel consistency is reported for every
headline.

Populations are defined by **design**, never by outcome: all bars; each of the
five institutional moments; month-end and quarter-end subsets; the four
sessions; rollover; and the non-event complement.

## 7. Success bands — fixed here

Applied to `C'/C` on policy P2, the primary cell, pooled across the two deciding
panels, and reported per panel beside it.

| band | condition |
| --- | --- |
| **Strong** | `C' <= 0.60 C` |
| **Material** | `0.60 C < C' <= 0.70 C` |
| **Modest** | `0.70 C < C' <= 0.85 C` |
| **Weak** | `C' > 0.85 C` |

These are not adjusted after the result is seen. If the two panels fall in
different bands, the **worse** band governs and the disagreement is reported.

## 8. What may not be claimed

A simulated `C'` is not a broker-realizable `C'`.
**`BROKER_REALIZABLE_COST_REDUCTION_ESTABLISHED` is prohibited.** The strongest
status this stage may reach is
`SIMULATED_EXECUTION_COST_BOUND_ESTABLISHED` / `OFFLINE_EXECUTION_FRONTIER_ESTIMATED`,
because queue position, quote withdrawal, latency, broker-specific fill logic,
hidden liquidity, partial fills and adverse selection are not fully observable
in M15 bid/ask bars.

## 9. What happens next, decided now

The measured `C'` re-enters the feasibility frontier, which is recomputed over
the *same* design enumeration the unit audit used — one enumeration, one cost
model, the cost source swapped. For every cell: `N`, `C'`, the one-times and
two-times hurdles, the MDE, the implied minimum gross information ratio, and a
feasible / infeasible verdict.

Cell selection for any Track 1 v2 may use only: institutional mechanism, event
frequency, sample size, cost, MDE, execution feasibility. It may **not** use
observed alpha, observed gross return, observed sign, observed p-value or a
favourable pair result. Track 3 produces none of those, which is the point.

The adjudication is fixed here:

* **Case A** — several economically meaningful cells clear the MDE gate, the IR
  gate and the per-panel rule, giving `CLOCK_STRUCTURE_TRACK_V2_DESIGNABLE`; a
  pre-registration proposal is returned to Human + ChatGPT and no signal
  execution begins.
* **Case B** — one marginal cell, giving
  `CLOCK_STRUCTURE_TRACK_V2_NOT_ROBUSTLY_DESIGNABLE`; research to rescue a
  single thin cell is not started.
* **Case C** — no cell becomes decision-grade, giving
  `CLOCK_STRUCTURE_NOT_DECISION_GRADE_AT_CURRENT_EXECUTION_FRONTIER`; the family
  is suspended for research infeasibility and **not** recorded as a null.

`NOT_DECISION_GRADE` and `NOT_SUPPORTED` are different verdicts and this stage
may only reach the first.
