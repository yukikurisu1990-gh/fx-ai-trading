# NG#10 Relaxation Review (Phase 24 path β)

Doc-only audit of NG#10 (close-only execution) relaxation candidates,
per Phase 24 final synthesis §8 path β. **No code, no eval, no
implementation in this PR.** The deliverable is a written verdict per
candidate (ADOPT / DEFER / REJECT) plus a routing recommendation.

## §1. Purpose and routing

Phase 24 final synthesis (PR #274) closed Phase 24 with all three
exit-side mechanisms (24.0b trailing / 24.0c partial / 24.0d regime)
returning REJECT under NG#10 strict close-only execution. The β-PR
question is: **which NG#10 relaxations, if any, are clearly-bounded
and realistic-execution-compatible enough to admit an exit class
Phase 24 could not test?**

Routing post-merge of this β doc:

- **If ≥1 candidate verdicts ADOPT** → next PR is **NG#10 relaxation
  envelope confirmation** (also doc-only). That PR fixes the allowed
  relaxations, prohibitions, required data, and unit-test contract
  before any implementation begins. Implementation PRs follow only
  after envelope confirmation.
- **If all candidates verdict REJECT** → route to γ hard close.
- **If only DEFERs and no ADOPTs** → block on resolving the deferral
  prerequisites of the most-promising DEFER before progressing.

## §2. Scope

**In scope**: NG#10 only — when and how exit triggers fire relative
to M1 bar close, including same-bar ambiguity, latency, and OANDA
fill realism.

**Explicitly out of scope**:

- NG#11 (causal regime tags) — not under review.
- NG#1-9 — not under review.
- Phase 23 entry-axis revision (path α) — deferred until β concludes.
- Spread-cost model changes (spread is data, not NG#10).
- Frozen entry stream selection (still 24.0a top-3).

## §3. Decision matrix

Each candidate is scored on five axes, then mapped to a verdict via
the table below.

| Axis | What it measures |
|---|---|
| **A1 — Leakage risk** | HIGH / MEDIUM / LOW — does the relaxation use information unavailable at trigger time, or cherry-pick favorable intra-bar paths? |
| **A2 — Realistic executability under OANDA M1 BA** | YES / NO — does OANDA's order book and our `data/` pipeline support this fill model today? |
| **A3 — Asymmetry plausibility** | plausible / implausible / N/A — does the relaxation tilt EV asymmetrically without a matching real-world fill mechanism? |
| **A4 — Falsifiability** | est. LoC + sweep cell count for a 24.0b-analog implementation. |
| **A5 — Expected magnitude** | does the candidate plausibly produce **≥ +0.30 Sharpe lift** vs 24.0b best (-0.177)? Required margin: A1 threshold +0.082 → gap ≈ +0.26, **margin +0.04**. |

**Mapping to verdict** (per user direction; tightened from the
original §5):

| A1 (leakage) | A2 (executable) | A5 (lift sufficient ≥ +0.30) | Verdict |
|---|---|---|---|
| **HIGH** | any | any | **REJECT** |
| MEDIUM | any | any | **DEFER** (cannot ADOPT) |
| LOW | NO + data extension realistic | plausibly sufficient | **DEFER** |
| LOW | NO + data extension NOT realistic | any | **REJECT** |
| LOW | YES | **clearly insufficient** | **REJECT** |
| LOW | YES | plausibly sufficient | **ADOPT** |

**Rules**:

- **MEDIUM leakage MUST NOT ADOPT** (per user direction).
- **A5 clearly insufficient** auto-rejects regardless of A1/A2.
- **Data-gap candidates** (M1 high/low not in canonical pipeline) DEFER
  not auto-reject UNLESS A1=HIGH or A5 clearly insufficient.

## §4. Leakage-risk taxonomy

Each candidate is mapped to subsets of:

- **Lookahead** — uses bar `t`'s post-close information at trigger
  time `t`.
- **Path cherry-pick** — picks the best (favorable) intra-bar fill
  without modeling timing.
- **Implicit slippage waiver** — fills at the exact trigger price
  with no spread crossing or slippage.
- **Optimistic latency** — fills at trigger bar without modeling
  OANDA round-trip.
- **Asymmetric optimism** — TP-side relaxation without a matching
  SL-side relaxation (or vice-versa) absent a real fill mechanism
  justifying the asymmetry.

## §5. Realistic-executability constraints (OANDA M1 BA)

Per-candidate audit checks:

- **OANDA order types**: take-profit (limit) fills on touch; stop-loss
  (stop-market) fills on touch + slippage; both differ from "fill at
  bar close".
- **Available data in `data/`**: M1 bid/ask **close-only** is in the
  canonical pipeline. **M1 high/low is NOT** in canonical pipeline.
  Adding it requires a data-pipeline extension (feasible from OANDA
  candle history but NOT a one-line change).
- **Spread persistence**: M1 BA gives close-bar spread only;
  intra-bar spread excursion is not observed.
- **Order placement timing**: TP/SL must be placed at-or-before
  entry; no in-bar adjustments.

## §6. Per-candidate evaluation (C1 → C6)

### C1 — TP-side touch, SL-side close (asymmetric)

**Description**. Long: if `bid_high >= TP` during bar `t`, fill at TP;
SL still uses `bid_close <= SL`. Short: mirror with `ask_high` /
`ask_low` against TP and `ask_close` against SL.

**A1 (leakage) — MEDIUM**.

- Path cherry-pick on TP-side only (we count favorable touches).
- Asymmetric optimism: SL-side stays on close, but real OANDA stop-loss
  orders fill on touch + slippage. Means C1 **under-counts** SL hits
  vs reality. Combined with TP-side touch fill, EV is biased high.
- Implicit slippage waiver on TP-side (fill exactly at TP, no
  crossing).

**A2 (executable) — NO without data extension**. M1 high not in
canonical pipeline. Data extension is realistic (OANDA candle history
provides high/low) but not in this PR.

**A3 (asymmetry) — implausible without extra justification**. Real
OANDA SL is stop-market (touch fill); making C1 realistic would
require either:

- A custom "stop-on-close" SL order type (not standard OANDA), OR
- Acceptance that C1 is a **deliberately conservative SL model** that
  trades fidelity on the SL side for upside on the TP side — which
  itself requires writing down a clear policy reason.

**A4 (falsifiability)**: ~50 LoC variant on `stage24_0b._simulate_atr_long/short`. Sweep size 33 cells (3 frozen × 11 K values, parity with 24.0b).

**A5 (lift)**: Two competing effects:

- TP-side touch ADDS fills on touched-then-reverted bars (not caught
  by NG#10) — modest upside.
- SL-side conservative ADDS fills only at close (NG#10 already does
  this) — no change vs NG#10.
- Net: unconfirmed; **+0.30 lift is plausible only if asymmetry
  justification holds**, otherwise the lift is a leakage artifact.

**Verdict — DEFER**.

**Prerequisites for promotion to ADOPT**:

1. Data availability audit confirming OANDA M1 high/low can be
   integrated into the canonical pipeline.
2. Canonical M1 bid/ask **OHLC** extension feasibility study (full
   OHLC, not just HL).
3. Same-bar ambiguity policy for the TP-side touch (if `bid_high >=
   TP` AND `bid_close < TP`, default fill price = ?).
4. **OANDA order-fill realism audit**: explicit asymmetry
   justification — name the OANDA order type combination that
   produces "TP touch fill + SL close fill".

---

### C2 — Both-side touch (high/low symmetric)

**Description**. Long: TP at `bid_high >= TP`, SL at `bid_low <= SL`.
Symmetric. Same for short with ask path.

**A1 (leakage) — MEDIUM**.

- Path cherry-pick on both sides — but SYMMETRIC path cherry-pick
  is closer to OANDA reality (both order types fill on touch).
- The dangerous case is **same-bar both-hit**: bar has both `bid_high
  >= TP` AND `bid_low <= SL`. Without sub-minute data, the temporal
  order is unobservable. Path cherry-pick risk peaks here.
- Per user direction, **the only acceptable same-bar policy is
  "SL-first"**: if both hit in the same bar, fill at SL. This converts
  the worst-case path-pick into a conservative fill and is REQUIRED
  before any C2 ADOPT path opens.
- Implicit slippage waiver on both sides (no spread crossing modeled).

**A2 (executable) — NO without data extension**. M1 high/low needed.

**A3 (asymmetry) — N/A**. Symmetric.

**A4 (falsifiability)**: ~70 LoC variant (C2 + same-bar policy logic).
Sweep size 33 cells (parity with 24.0b).

**A5 (lift)**: More relaxation than C1 because both sides admit
touches. But the SL-first same-bar policy claws back the upside on
volatile bars (where touches concentrate). Net plausible lift: closer
to A5 sufficient than C1, but still gated by the same-bar policy.

**Verdict — DEFER**.

**Prerequisites for promotion to ADOPT**:

1. Data availability audit (M1 high/low integration).
2. Canonical M1 bid/ask OHLC extension feasibility.
3. **Same-bar ambiguity policy MUST be "SL-first"** — if same bar
   has both TP-touch and SL-touch, fill at SL. Documented as a
   non-negotiable invariant in the envelope-confirmation PR.
4. OANDA order-fill realism audit: confirm OANDA TP-limit and SL-stop
   fill semantics match the touch model under typical M1 spread
   conditions.

---

### C3 — Same trigger, next-bar-open execution

**Description**. NG#10's close-only trigger logic kept verbatim. Only
the FILL price changes: instead of filling at trigger bar `t` close,
fill at bar `t+1` open. Models OANDA round-trip latency.

**A1 (leakage) — LOW**. No new information at trigger time. Bar
`t+1` open is the price at which a fill issued on bar-`t`-close would
realistically execute; this is causally available.

**A2 (executable) — YES, no data extension**. M1 BA close-only
already in `data/`; "next-bar open" is `M1[t+1]` open which exists.

**A3 (asymmetry) — N/A**. Same shift on TP and SL.

**A4 (falsifiability)**: ~20 LoC. Sweep size 33 cells (parity with 24.0b).

**A5 (lift)**: Pure latency shift adds Brownian noise to fill prices.

- TP-side: fill price = next-bar open. Mean ≈ trigger close + drift over 1 minute. For mean-reverting bars, this is unfavorable; for trending bars, favorable. **Expected EV change ~ 0**.
- SL-side: same noise applied. Symmetric.
- Variance of fill price increases (1-bar drift std).
- Cannot plausibly produce +0.30 Sharpe lift; expected effect is small
  and possibly negative.

**Verdict — REJECT**.

**Reasoning**: A5 clearly insufficient. Pure 1-bar latency without an
intra-bar advantage is a fairness adjustment — it cannot generate the
+0.30 Sharpe lift required to clear A1. C3 may be useful as a
realism-stress test in a future audit, but is not a plausible
exit-class breakthrough.

---

### C4 — Same trigger, next-bar-close execution

**Description**. Trigger at bar `t` close; fill at bar `t+1` close.
1-bar latency, more conservative than C3.

**A1 (leakage) — LOW**. Same as C3.

**A2 (executable) — YES, no data extension**.

**A3 (asymmetry) — N/A**.

**A4 (falsifiability)**: ~20 LoC. Sweep size 33 cells.

**A5 (lift)**: Strictly worse than C3 in expected value:

- The trigger condition (bar-`t` close past TP) implies a favorable
  cross. 1 bar of additional drift on average reverts (mean reversion
  in M1 minor pairs); fills will be worse than NG#10's bar-`t` close
  fill on the TP side, and slightly better (less bad) on the SL side.
- Net Sharpe expected to be **worse than NG#10 strict close-only**,
  let alone +0.30 above.

**Verdict — REJECT**.

**Reasoning**: A5 clearly insufficient (likely negative). C4 is the
strictest latency model and is documented here for completeness; it
should never be confused with a "more realistic" model — it is just
a worse-fill model.

---

### C5 — Touch with worst-of-bar fills (anti-cherry-pick)

**Description**. Long TP fills at `min(TP, bid_close)` if
`bid_high >= TP`. Long SL fills at `min(SL, bid_low)` if
`bid_low <= SL`. I.e., admit touches but always fill at the worse of
{trigger price, close-of-bar}. Symmetric for short.

**A1 (leakage) — LOW**. Worst-of-bar fill is anti-cherry-pick. The
fill is no better than the close, which is observable and causal.

**A2 (executable) — NO without data extension**. M1 high/low needed.
Data extension realistic.

**A3 (asymmetry) — N/A**.

**A4 (falsifiability)**: ~60 LoC. Sweep size 33 cells.

**A5 (lift)**: Two effects, both small:

- On bars where NG#10 also triggers (close past TP): C5 fills at
  `min(TP, bid_close) = TP` while NG#10 fills at `bid_close ≥ TP`
  (more favorable). C5 strictly worse here.
- On bars where NG#10 does NOT trigger (touch then revert): C5 catches
  an extra exit at `bid_close` (inside the band, no realised TP
  capture). Whether this is favorable depends on subsequent path —
  closing at band-revert close locks in zero TP capture but releases
  capital. Mean effect ≈ 0.
- Net: **clearly insufficient** for +0.30 Sharpe lift.

**Verdict — REJECT**.

**Reasoning**: A5 clearly insufficient. C5 is a strictly more
conservative fill model than NG#10 close-only on the trigger bar;
the additional triggered exits on touched-then-reverted bars do not
plausibly close the +0.26 gap. Auto-rejected by A5 even though A1 is
LOW and A2 is data-extendable.

---

### C6 — Both-side touch + stale-quote / wide-spread gate

**Description**. C2 (both-side touch with SL-first same-bar policy)
plus a SKIP rule: if `(ask_close − bid_close) > K × ATR` at trigger
bar, do NOT fill — carry the position to the next bar. Filters out
exits placed during stale quotes / illiquid bars.

**A1 (leakage) — LOW**. Spread at trigger close is observable
causally. The K×ATR gate uses 24.0a-style causal ATR (NG#11
discipline). The gate is conservative — it removes fills, never adds
them.

**A2 (executable) — NO without data extension**. Inherits C2's M1
high/low requirement.

**A3 (asymmetry) — N/A** (C2-symmetric).

**A4 (falsifiability)**: ~80 LoC (C2 + gate). Sweep size 33 cells × K
parameter (e.g., K ∈ {1.0, 2.0, 3.0}) → 99 cells.

**A5 (lift)**: Marginal upside if stale-quote bars cluster on bad
fills. The gate also removes some good fills (it's symmetric in spread
terms, not in fill quality). Plausible lift uncertain; cannot rule out
≥ +0.30 because the gate is a filter on top of C2's already-relaxed
trigger model.

**Verdict — DEFER**.

**Prerequisites for promotion to ADOPT**:

1. All C2 prerequisites (data, OHLC extension, SL-first same-bar
   policy, OANDA fill audit).
2. K parameter design — single value? Sweep? Justification for
   chosen range.
3. Empirical sanity check on stale-quote-bar prevalence in `data/` —
   if rare, gate has no effect; if common, may overfilter.
4. Inherits C2's MEDIUM-leakage prerequisite — C6 is C2 + filter, so
   the underlying leakage profile is C2's MEDIUM, NOT LOW. **C6's
   real A1 is MEDIUM, demoted from LOW above** because the touch
   model is C2's. Verdict therefore stays at DEFER (cannot ADOPT
   under MEDIUM leakage rule) regardless of gate parameters.

(Note: I scored A1 LOW for the gate-only delta, but the composite
A1 inherits C2's MEDIUM. Accepting C6 ADOPT would require also
ADOPTing C2's relaxation envelope.)

---

## §7. Summary table

| # | Candidate | A1 (leakage) | A2 (executable) | A5 (lift ≥ +0.30) | Verdict |
|---|---|---|---|---|---|
| C1 | TP-side touch, SL conservative close | MEDIUM | NO (data ext realistic) | uncertain | **DEFER** |
| C2 | Both-side touch (symmetric, SL-first) | MEDIUM | NO (data ext realistic) | plausibly sufficient | **DEFER** |
| C3 | Next-bar-open execution | LOW | YES | clearly insufficient | **REJECT** |
| C4 | Next-bar-close execution | LOW | YES | clearly insufficient (likely negative) | **REJECT** |
| C5 | Worst-of-bar touch (anti-cherry-pick) | LOW | NO (data ext realistic) | clearly insufficient | **REJECT** |
| C6 | C2 + stale-quote gate | MEDIUM (inherits C2) | NO (data ext realistic) | uncertain | **DEFER** |

**Verdict counts**: 0 ADOPT / 3 DEFER (C1, C2, C6) / 3 REJECT (C3, C4, C5).

## §8. Most-promising DEFER and prerequisites

**Most-promising DEFER**: **C2** (both-side touch, symmetric, SL-first
same-bar policy). Reasons:

- A5 plausibility is highest among DEFERs (both sides admit touches,
  closest to OANDA reality).
- Asymmetry concern absent (vs C1).
- Filter logic absent (vs C6, which inherits C2's leakage anyway).
- Same-bar SL-first policy converts the dangerous path-pick case
  into a conservative fill.

**Prerequisites for C2 ADOPT** (carried into envelope-confirmation
PR if user accepts this routing):

1. **Data extension**: integrate OANDA M1 bid/ask OHLC into the
   canonical pipeline. Audit feasibility, storage cost, and impact
   on existing 22.x/23.x/24.x reproducibility (must NOT break frozen
   reports).
2. **Same-bar ambiguity policy**: SL-first is a hard non-negotiable
   invariant. Documented in the envelope-confirmation PR. Unit test
   contract REQUIRED to verify same-bar both-hit always fills SL.
3. **OANDA fill realism audit**: confirm both touch fills (TP limit,
   SL stop) match OANDA's typical M1 fill mechanics under realistic
   spread conditions.
4. **Leakage demotion path**: C2 starts at MEDIUM leakage; show that
   with the SL-first invariant + worst-of-bar slippage option, the
   composite A1 demotes to LOW. Without this demotion, C2 cannot
   ADOPT (MEDIUM is DEFER-ceiling per §3).

C1 and C6 are second-tier DEFERs with stricter prerequisites (asymmetry
justification for C1; K parameter design and inherited C2 prerequisites
for C6).

## §9. Routing recommendation

1. **No candidate verdicts ADOPT in this β PR.** Three DEFERs (C1, C2,
   C6) and three REJECTs (C3, C4, C5).
2. **Next step is NOT γ hard close** — three DEFERs are live with
   defined prerequisite paths.
3. **Recommended next PR**: **NG#10 relaxation envelope confirmation
   PR** (doc-only) that picks **C2 as the candidate to escalate** and
   formally writes:
   - the allowed relaxations (touch fills on TP and SL, symmetric);
   - the prohibited paths (no asymmetric optimism; no MEDIUM-leakage
     ADOPTs; no implicit slippage waivers without justification);
   - the required data (M1 OHLC extension specification);
   - the unit-test contract (same-bar SL-first invariant; touch
     trigger semantics; data-shape assertions).
4. After envelope confirmation merges, an implementation PR (analogous
   to 24.0b but on the relaxed envelope) becomes in scope.
5. **If envelope confirmation cannot demote C2's leakage from MEDIUM
   to LOW** under any acceptable real-OANDA fill mapping, C2 verdict
   permanently stays DEFER and routing reverts to γ hard close (since
   C1 and C6 inherit similar issues).

## §10. Phase 23 / Phase 24 envelope preserved

This β PR introduces no new code, no new test, no new data, no new
artifact. All Phase 22/23/24 frozen artifacts and verdicts are
unchanged. Production-readiness gating (Phase 22 frozen-OOS
discipline) remains intact. NG#11 (causal regime tags) is not
relaxed by this review.
